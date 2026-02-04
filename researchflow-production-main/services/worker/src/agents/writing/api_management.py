"""
External API Management System

Handles rate limiting, batching, and resilient API calls for external services
like PubMed, CrossRef, Semantic Scholar, etc.

Linear Issues: ROS-XXX
"""

import asyncio
import time
import logging
from typing import Dict, List, Optional, Any, Callable, TypeVar, Awaitable
from dataclasses import dataclass, field
from enum import Enum
import httpx
import random
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

T = TypeVar('T')


class APIProvider(str, Enum):
    """Supported external API providers."""
    PUBMED = "pubmed"
    CROSSREF = "crossref"
    SEMANTIC_SCHOLAR = "semantic_scholar"
    ARXIV = "arxiv"
    RETRACTION_WATCH = "retraction_watch"
    DIMENSIONS = "dimensions"


@dataclass
class RateLimit:
    """Rate limit configuration."""
    requests_per_second: float
    burst_capacity: int
    window_size_seconds: int = 60
    
    def __post_init__(self):
        self.tokens = self.burst_capacity
        self.last_refill = time.time()


@dataclass
class APIRequest:
    """API request wrapper."""
    provider: APIProvider
    endpoint: str
    method: str = "GET"
    params: Optional[Dict[str, Any]] = None
    headers: Optional[Dict[str, str]] = None
    data: Optional[Any] = None
    timeout: float = 30.0
    retry_count: int = 0
    max_retries: int = 3
    priority: int = 0  # Higher priority = processed first


@dataclass
class APIResponse:
    """API response wrapper."""
    request: APIRequest
    status_code: int
    data: Any
    headers: Dict[str, str]
    response_time: float
    from_cache: bool = False
    error: Optional[str] = None


class AsyncRateLimiter:
    """Token bucket rate limiter for async operations."""
    
    def __init__(self, requests_per_second: float, burst_capacity: int):
        """
        Initialize rate limiter.
        
        Args:
            requests_per_second: Sustained rate limit
            burst_capacity: Maximum burst size
        """
        self.rate = requests_per_second
        self.capacity = burst_capacity
        self.tokens = burst_capacity
        self.last_refill = time.time()
        self._lock = asyncio.Lock()
    
    async def acquire(self, tokens: int = 1) -> bool:
        """
        Acquire tokens from the bucket.
        
        Args:
            tokens: Number of tokens to acquire
            
        Returns:
            True if tokens acquired, False if would exceed rate limit
        """
        async with self._lock:
            now = time.time()
            elapsed = now - self.last_refill
            
            # Refill tokens based on elapsed time
            new_tokens = elapsed * self.rate
            self.tokens = min(self.capacity, self.tokens + new_tokens)
            self.last_refill = now
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            
            return False
    
    async def wait_for_tokens(self, tokens: int = 1) -> None:
        """Wait until tokens are available."""
        while not await self.acquire(tokens):
            # Calculate wait time
            wait_time = tokens / self.rate
            await asyncio.sleep(min(wait_time, 1.0))


class BatchProcessor:
    """Generic batch processor for API requests."""
    
    def __init__(
        self,
        batch_size: int,
        flush_interval: float,
        processor_func: Callable[[List[T]], Awaitable[Dict[T, Any]]]
    ):
        """
        Initialize batch processor.
        
        Args:
            batch_size: Maximum batch size
            flush_interval: Maximum time to wait before flushing batch
            processor_func: Function to process a batch of items
        """
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.processor_func = processor_func
        
        self._batch: List[T] = []
        self._pending_requests: Dict[T, asyncio.Future] = {}
        self._last_flush = time.time()
        self._flush_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
    
    async def process(self, item: T) -> Any:
        """
        Add item to batch and return result.
        
        Args:
            item: Item to process
            
        Returns:
            Processing result
        """
        async with self._lock:
            if item in self._pending_requests:
                # Already being processed
                return await self._pending_requests[item]
            
            # Create future for this request
            future = asyncio.Future()
            self._pending_requests[item] = future
            self._batch.append(item)
            
            # Start flush timer if needed
            if self._flush_task is None:
                self._flush_task = asyncio.create_task(self._auto_flush())
            
            # Flush if batch is full
            if len(self._batch) >= self.batch_size:
                await self._flush_batch()
        
        return await future
    
    async def _auto_flush(self) -> None:
        """Automatically flush batch after interval."""
        await asyncio.sleep(self.flush_interval)
        async with self._lock:
            if self._batch:
                await self._flush_batch()
            self._flush_task = None
    
    async def _flush_batch(self) -> None:
        """Flush current batch."""
        if not self._batch:
            return
        
        batch_to_process = self._batch.copy()
        futures_to_complete = {item: future for item, future in self._pending_requests.items() if item in batch_to_process}
        
        # Clear batch
        self._batch.clear()
        for item in batch_to_process:
            del self._pending_requests[item]
        
        try:
            # Process batch
            results = await self.processor_func(batch_to_process)
            
            # Complete futures
            for item, future in futures_to_complete.items():
                if item in results:
                    future.set_result(results[item])
                else:
                    future.set_exception(ValueError(f"No result for item: {item}"))
        
        except Exception as e:
            # Complete all futures with exception
            for future in futures_to_complete.values():
                future.set_exception(e)
    
    async def flush(self) -> None:
        """Manually flush all pending items."""
        async with self._lock:
            await self._flush_batch()


class ExternalAPIManager:
    """Centralized manager for external API calls with rate limiting and batching."""
    
    # Default rate limits per provider
    DEFAULT_RATE_LIMITS = {
        APIProvider.PUBMED: RateLimit(requests_per_second=10, burst_capacity=50),
        APIProvider.CROSSREF: RateLimit(requests_per_second=50, burst_capacity=200), 
        APIProvider.SEMANTIC_SCHOLAR: RateLimit(requests_per_second=100, burst_capacity=500),
        APIProvider.ARXIV: RateLimit(requests_per_second=1, burst_capacity=5),
        APIProvider.RETRACTION_WATCH: RateLimit(requests_per_second=1, burst_capacity=3),
        APIProvider.DIMENSIONS: RateLimit(requests_per_second=5, burst_capacity=20),
    }
    
    # Base URLs for providers
    BASE_URLS = {
        APIProvider.PUBMED: "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/",
        APIProvider.CROSSREF: "https://api.crossref.org/",
        APIProvider.SEMANTIC_SCHOLAR: "https://api.semanticscholar.org/",
        APIProvider.ARXIV: "https://export.arxiv.org/api/",
        APIProvider.RETRACTION_WATCH: "http://retractiondatabase.org/",
        APIProvider.DIMENSIONS: "https://app.dimensions.ai/api/",
    }
    
    def __init__(self, custom_rate_limits: Optional[Dict[APIProvider, RateLimit]] = None):
        """
        Initialize API manager.
        
        Args:
            custom_rate_limits: Optional custom rate limits per provider
        """
        self.rate_limits = {**self.DEFAULT_RATE_LIMITS}
        if custom_rate_limits:
            self.rate_limits.update(custom_rate_limits)
        
        self.rate_limiters = {
            provider: AsyncRateLimiter(limit.requests_per_second, limit.burst_capacity)
            for provider, limit in self.rate_limits.items()
        }
        
        self.batch_processors: Dict[str, BatchProcessor] = {}
        self._http_client: Optional[httpx.AsyncClient] = None
        
        self.stats = {
            'requests_made': 0,
            'requests_cached': 0,
            'requests_failed': 0,
            'rate_limited': 0,
            'batch_processed': 0,
        }
    
    async def initialize(self) -> None:
        """Initialize HTTP client and batch processors."""
        self._http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
            headers={'User-Agent': 'ResearchFlow Reference Manager/1.0'}
        )
        
        # Initialize batch processors
        self.batch_processors.update({
            'doi_batch': BatchProcessor(
                batch_size=50,
                flush_interval=2.0,
                processor_func=self._batch_doi_lookup
            ),
            'pubmed_batch': BatchProcessor(
                batch_size=25,
                flush_interval=3.0,
                processor_func=self._batch_pubmed_lookup
            ),
        })
    
    async def close(self) -> None:
        """Close HTTP client and flush batches."""
        # Flush all pending batches
        for processor in self.batch_processors.values():
            await processor.flush()
        
        if self._http_client:
            await self._http_client.aclose()
    
    async def make_request(self, request: APIRequest) -> APIResponse:
        """
        Make a single API request with rate limiting.
        
        Args:
            request: API request to make
            
        Returns:
            API response
        """
        # Apply rate limiting
        if request.provider in self.rate_limiters:
            rate_limiter = self.rate_limiters[request.provider]
            if not await rate_limiter.acquire():
                self.stats['rate_limited'] += 1
                await rate_limiter.wait_for_tokens()
        
        start_time = time.time()
        
        try:
            # Construct full URL
            base_url = self.BASE_URLS.get(request.provider, "")
            url = f"{base_url.rstrip('/')}/{request.endpoint.lstrip('/')}" if base_url else request.endpoint
            
            # Make HTTP request
            if not self._http_client:
                await self.initialize()
            
            response = await self._http_client.request(
                method=request.method,
                url=url,
                params=request.params,
                headers=request.headers,
                json=request.data if request.method != "GET" else None,
                timeout=request.timeout
            )
            
            response_time = time.time() - start_time
            self.stats['requests_made'] += 1
            
            # Parse response
            try:
                data = response.json() if response.content else {}
            except:
                data = response.text if response.content else ""
            
            return APIResponse(
                request=request,
                status_code=response.status_code,
                data=data,
                headers=dict(response.headers),
                response_time=response_time,
                error=None if response.is_success else f"HTTP {response.status_code}"
            )
        
        except Exception as e:
            response_time = time.time() - start_time
            self.stats['requests_failed'] += 1
            
            return APIResponse(
                request=request,
                status_code=0,
                data=None,
                headers={},
                response_time=response_time,
                error=str(e)
            )
    
    async def make_request_with_retry(self, request: APIRequest) -> APIResponse:
        """
        Make API request with exponential backoff retry.
        
        Args:
            request: API request to make
            
        Returns:
            API response
        """
        last_response = None
        
        for attempt in range(request.max_retries + 1):
            response = await self.make_request(request)
            last_response = response
            
            # Success
            if response.status_code == 200:
                return response
            
            # Don't retry certain errors
            if response.status_code in [400, 401, 403, 404]:
                return response
            
            # Last attempt
            if attempt == request.max_retries:
                return response
            
            # Calculate backoff delay
            delay = min(2 ** attempt + random.uniform(0, 1), 30)
            logger.warning(f"API request failed, retrying in {delay:.1f}s (attempt {attempt + 1}/{request.max_retries + 1})")
            await asyncio.sleep(delay)
        
        return last_response
    
    async def batch_doi_lookups(self, dois: List[str]) -> Dict[str, Any]:
        """
        Batch DOI metadata lookups.
        
        Args:
            dois: List of DOIs to look up
            
        Returns:
            Dictionary mapping DOI to metadata
        """
        processor = self.batch_processors.get('doi_batch')
        if not processor:
            # Fall back to individual requests
            results = {}
            for doi in dois:
                metadata = await self.lookup_doi_metadata(doi)
                if metadata:
                    results[doi] = metadata
            return results
        
        results = {}
        tasks = [processor.process(doi) for doi in dois]
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for doi, result in zip(dois, batch_results):
            if not isinstance(result, Exception) and result:
                results[doi] = result
        
        return results
    
    async def _batch_doi_lookup(self, dois: List[str]) -> Dict[str, Any]:
        """Internal batch DOI lookup implementation."""
        results = {}
        
        # Chunk DOIs for CrossRef API (max 50 per request)
        chunk_size = 50
        for i in range(0, len(dois), chunk_size):
            chunk = dois[i:i + chunk_size]
            
            try:
                # Use CrossRef API for batch lookup
                request = APIRequest(
                    provider=APIProvider.CROSSREF,
                    endpoint="works",
                    params={
                        'ids': ','.join(chunk),
                        'mailto': 'research@researchflow.ai'  # Be a good citizen
                    }
                )
                
                response = await self.make_request_with_retry(request)
                
                if response.status_code == 200 and response.data:
                    items = response.data.get('message', {}).get('items', [])
                    for item in items:
                        doi = item.get('DOI', '').lower()
                        if doi in chunk:
                            results[doi] = item
                
                self.stats['batch_processed'] += len(chunk)
                
            except Exception as e:
                logger.warning(f"Batch DOI lookup failed for chunk: {e}")
        
        return results
    
    async def _batch_pubmed_lookup(self, pmids: List[str]) -> Dict[str, Any]:
        """Internal batch PubMed lookup implementation."""
        results = {}
        
        try:
            # Use PubMed efetch API for batch lookup
            request = APIRequest(
                provider=APIProvider.PUBMED,
                endpoint="efetch.fcgi",
                params={
                    'db': 'pubmed',
                    'id': ','.join(pmids),
                    'retmode': 'xml',
                    'rettype': 'abstract'
                }
            )
            
            response = await self.make_request_with_retry(request)
            
            if response.status_code == 200 and response.data:
                # Parse XML response (simplified)
                # In practice, you'd use xml.etree.ElementTree or similar
                for pmid in pmids:
                    # This is a placeholder - real implementation would parse XML
                    results[pmid] = {'pmid': pmid, 'title': f'Article {pmid}'}
            
            self.stats['batch_processed'] += len(pmids)
            
        except Exception as e:
            logger.warning(f"Batch PubMed lookup failed: {e}")
        
        return results
    
    async def lookup_doi_metadata(self, doi: str) -> Optional[Dict[str, Any]]:
        """
        Look up metadata for a single DOI.
        
        Args:
            doi: DOI to look up
            
        Returns:
            Metadata dictionary or None if not found
        """
        if not doi:
            return None
        
        # Clean DOI
        clean_doi = doi.lower().replace('doi:', '').replace('DOI:', '')
        if not clean_doi.startswith('10.'):
            return None
        
        request = APIRequest(
            provider=APIProvider.CROSSREF,
            endpoint=f"works/{clean_doi}",
            headers={'Accept': 'application/json'},
            params={'mailto': 'research@researchflow.ai'}
        )
        
        response = await self.make_request_with_retry(request)
        
        if response.status_code == 200 and response.data:
            return response.data.get('message')
        
        return None
    
    async def search_pubmed(self, query: str, max_results: int = 20) -> List[Dict[str, Any]]:
        """
        Search PubMed with a query.
        
        Args:
            query: Search query
            max_results: Maximum number of results
            
        Returns:
            List of search results
        """
        # First, search for PMIDs
        search_request = APIRequest(
            provider=APIProvider.PUBMED,
            endpoint="esearch.fcgi",
            params={
                'db': 'pubmed',
                'term': query,
                'retmax': max_results,
                'retmode': 'json'
            }
        )
        
        search_response = await self.make_request_with_retry(search_request)
        
        if search_response.status_code != 200 or not search_response.data:
            return []
        
        pmids = search_response.data.get('esearchresult', {}).get('idlist', [])
        if not pmids:
            return []
        
        # Then fetch details for PMIDs
        fetch_request = APIRequest(
            provider=APIProvider.PUBMED,
            endpoint="efetch.fcgi",
            params={
                'db': 'pubmed',
                'id': ','.join(pmids),
                'retmode': 'xml',
                'rettype': 'abstract'
            }
        )
        
        fetch_response = await self.make_request_with_retry(fetch_request)
        
        if fetch_response.status_code == 200:
            # Parse XML and return structured data
            # This is simplified - real implementation would parse XML properly
            return [{'pmid': pmid, 'title': f'Article {pmid}'} for pmid in pmids]
        
        return []
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get API manager statistics."""
        return {
            **self.stats,
            'rate_limiters': {
                provider.value: {
                    'tokens_remaining': limiter.tokens,
                    'requests_per_second': self.rate_limits[provider].requests_per_second,
                    'burst_capacity': self.rate_limits[provider].burst_capacity,
                }
                for provider, limiter in self.rate_limiters.items()
            },
            'batch_processors': {
                name: len(processor._batch)
                for name, processor in self.batch_processors.items()
            }
        }


# Global API manager instance
_api_manager_instance: Optional[ExternalAPIManager] = None


async def get_api_manager() -> ExternalAPIManager:
    """Get global API manager instance."""
    global _api_manager_instance
    if _api_manager_instance is None:
        _api_manager_instance = ExternalAPIManager()
        await _api_manager_instance.initialize()
    return _api_manager_instance


async def close_api_manager() -> None:
    """Close global API manager instance."""
    global _api_manager_instance
    if _api_manager_instance:
        await _api_manager_instance.close()
        _api_manager_instance = None