# Enhanced Reference Management System

A comprehensive reference management system for academic manuscript writing with advanced features including DOI validation, duplicate detection, quality assessment, and multi-style citation formatting.

## Features

### 🔍 **Citation Extraction**
- Automatic detection of citation needs from manuscript text
- Support for multiple citation marker formats ([1], [citation needed], etc.)
- Intelligent claim classification (statistical facts, prior research, methodology, etc.)

### 📚 **Reference Processing**
- Literature search result integration
- DOI validation and metadata enrichment via CrossRef API
- Automatic duplicate detection and intelligent merging
- Support for 10+ citation styles (AMA, APA, Vancouver, Nature, etc.)

### ⚡ **Quality Assessment**
- AI-powered reference quality scoring
- Multi-dimensional assessment (credibility, recency, relevance, impact, methodology)
- Automatic flagging of problematic references (retracted papers, predatory journals)
- Field-specific quality criteria

### 🚀 **Performance & Reliability**
- Redis-based caching with intelligent TTL management
- Rate-limited external API calls with exponential backoff
- Batch processing for improved performance
- Comprehensive error handling and recovery

### 📊 **Analytics & Insights**
- Reference pattern analysis
- Citation strategy optimization recommendations
- Quality distribution metrics
- Performance monitoring and statistics

## Quick Start

### Basic Usage

```python
from agents.writing import ReferenceManagementService, ReferenceState, CitationStyle

# Initialize service
service = await ReferenceManagementService().initialize()

# Create processing state
state = ReferenceState(
    study_id="my_manuscript",
    manuscript_text="Studies show that intervention is effective [citation needed].",
    literature_results=[
        {
            "id": "study_1",
            "title": "Intervention Effectiveness Study",
            "authors": ["Smith, J.", "Doe, A."],
            "year": 2023,
            "journal": "Medical Journal",
            "doi": "10.1234/med.2023.001"
        }
    ],
    target_style=CitationStyle.AMA,
    enable_quality_assessment=True
)

# Process references
result = await service.process_references(state)

print(f"Processed {result.total_references} references")
print(f"Bibliography:\n{result.bibliography}")
```

### Integration with Stage 17

The system automatically enhances Stage 17 (Citation Generation) when available:

```python
# Stage 17 input with enhanced features
stage_data = {
    "inputs": {
        "sources": [...],
        "manuscript_text": "Full manuscript content...",
        "citationStyle": "ama",
        "enable_doi_validation": True,
        "enable_quality_assessment": True,
        "research_field": "medical"
    }
}

result = await stage17.process("workflow_id", stage_data)
# Returns enhanced output with quality scores, warnings, etc.
```

## Architecture

### Core Components

```
ReferenceManagementService (main orchestrator)
├── ReferenceCache (Redis-based caching)
├── DOIValidator (CrossRef API integration)
├── PaperDeduplicator (duplicate detection)
├── ReferenceQualityAssessor (quality scoring)
├── ExternalAPIManager (rate limiting & batching)
└── CitationFormatterFactory (multi-style formatting)
```

### Data Flow

1. **Citation Extraction** → Identify citation needs from manuscript
2. **Literature Matching** → Match needs to search results
3. **Metadata Enrichment** → Validate DOIs and fetch metadata
4. **Duplicate Detection** → Find and merge duplicate references
5. **Quality Assessment** → Score and flag problematic references
6. **Citation Formatting** → Format in target style
7. **Bibliography Generation** → Create final reference list

## Configuration

### Environment Variables

```bash
# Redis Configuration
REDIS_URL=redis://localhost:6379

# API Keys
NCBI_API_KEY=your_pubmed_key
CROSSREF_EMAIL=your_email@institution.edu

# Performance Settings
REF_CACHE_TTL_DAYS=7
REF_API_RATE_LIMIT=50
REF_BATCH_SIZE=25
```

### Quality Assessment Settings

```python
# Customize quality thresholds
quality_settings = {
    "minimum_credibility": 0.6,
    "recent_years_threshold": 5,
    "high_impact_threshold": 0.8,
    "enable_retraction_check": True
}
```

## Citation Styles Supported

| Style | Description | Common Fields |
|-------|-------------|---------------|
| **AMA** | American Medical Association | Author. Title. Journal. Year;Vol(Issue):Pages. |
| **APA** | American Psychological Association | Author (Year). Title. Journal, Vol(Issue), Pages. |
| **Vancouver** | ICMJE style for medical journals | Author. Title. Journal Year;Vol:Pages. |
| **Harvard** | Author-date format | Author, Year. Title. Journal, Vol(Issue), pp.Pages. |
| **Nature** | Nature journal style | Author. Title. Journal vol, pages (year). |
| **Chicago** | Chicago Manual of Style | Author. "Title." Journal Vol, no. Issue (Year): Pages. |
| **MLA** | Modern Language Association | Author. "Title." Journal, vol. Vol, no. Issue, Year, pp. Pages. |
| **IEEE** | Institute of Electrical Engineers | [1] Author, "Title," Journal, vol. Vol, no. Issue, pp. Pages, Year. |

## Quality Assessment Criteria

### Scoring Dimensions (0.0 - 1.0)

- **Credibility** (30%): Journal reputation, retraction status, metadata completeness
- **Recency** (20%): Publication age relative to field norms  
- **Relevance** (25%): Topic similarity to manuscript content
- **Impact** (15%): Citation count, journal impact factor
- **Methodology** (10%): Study design rigor, methodology indicators

### Quality Levels

| Level | Score Range | Description |
|-------|-------------|-------------|
| **Excellent** | 0.90+ | High-quality, highly relevant references |
| **Good** | 0.75-0.89 | Solid references with minor issues |
| **Acceptable** | 0.60-0.74 | Usable references with some limitations |
| **Poor** | 0.40-0.59 | References with significant issues |
| **Problematic** | <0.40 | References requiring attention/replacement |

### Warning Types

- **Retracted Paper**: Paper has been formally retracted
- **Predatory Journal**: Published in known predatory journal
- **Very Old**: Reference is >25 years old
- **Preprint Misuse**: Old preprint that may have been published
- **Incomplete Metadata**: Missing essential citation information
- **Broken Link**: URL no longer accessible
- **Duplicate Reference**: Potential duplicate detected

## Performance Characteristics

### Benchmarks

| Operation | 10 refs | 50 refs | 100 refs |
|-----------|---------|---------|----------|
| **Citation Extraction** | <0.1s | <0.5s | <1.0s |
| **Duplicate Detection** | <0.2s | <1.0s | <3.0s |
| **Quality Assessment** | <0.5s | <2.0s | <5.0s |
| **DOI Validation** | <1.0s | <3.0s | <8.0s |
| **Total Processing** | <2.0s | <7.0s | <18.0s |

### Caching Benefits

- **Cache Hit Rate**: 60-80% typical
- **Performance Improvement**: 3-5x faster with warm cache
- **API Call Reduction**: 70-90% fewer external requests

## API Reference

### ReferenceManagementService

#### Main Methods

```python
async def process_references(state: ReferenceState) -> ReferenceResult:
    """Main processing workflow."""
    
async def extract_citations(manuscript_text: str) -> List[CitationNeed]:
    """Extract citation needs from text."""
    
async def assess_quality(references: List[Reference], context: str) -> List[QualityScore]:
    """Assess reference quality."""
    
async def get_analytics(references: List[Reference]) -> ReferenceAnalytics:
    """Generate reference analytics."""
```

### DOIValidator

```python
async def validate_doi(doi: str, fetch_metadata: bool = True) -> DOIValidationResult:
    """Validate single DOI."""
    
async def validate_dois_batch(dois: List[str]) -> Dict[str, DOIValidationResult]:
    """Validate multiple DOIs."""
    
async def enrich_reference_with_doi(reference: Reference) -> Reference:
    """Enrich reference with DOI metadata."""
```

### PaperDeduplicator

```python
async def find_duplicates(references: List[Reference]) -> List[DuplicateGroup]:
    """Find duplicate references."""
    
async def merge_duplicates(references: List[Reference], groups: List[DuplicateGroup]) -> List[Reference]:
    """Merge duplicate references."""
```

## Error Handling

### Common Issues & Solutions

#### DOI Validation Failures
```python
# Graceful handling of API failures
try:
    result = await validator.validate_doi(doi)
except APIException as e:
    logger.warning(f"DOI validation failed: {e}")
    # Continue with available metadata
```

#### Rate Limit Exceeded
```python
# Automatic retry with exponential backoff
# Rate limiter prevents hitting API limits
# Batch processing reduces total API calls
```

#### Cache Unavailable
```python
# System continues without cache
# Performance degraded but functionality intact
# Automatic fallback to in-memory caching
```

## Testing

### Running Tests

```bash
# Run all tests
pytest services/worker/src/agents/writing/test_reference_management.py -v

# Run specific test categories
pytest -k "test_doi" -v  # DOI validation tests
pytest -k "test_duplicate" -v  # Duplicate detection tests
pytest -k "test_quality" -v  # Quality assessment tests

# Run performance tests
pytest -k "test_performance" -v --benchmark
```

### Test Coverage

- **Unit Tests**: Individual component testing
- **Integration Tests**: End-to-end workflow testing  
- **Performance Tests**: Load and speed testing
- **Error Handling Tests**: Failure scenario testing

## Examples

See `examples.py` for comprehensive usage examples:

1. **Basic Processing**: Simple manuscript with citations
2. **Quality Assessment**: Advanced quality filtering
3. **Duplicate Detection**: Handling duplicate references
4. **Style Comparison**: Multi-style formatting
5. **Performance Benchmark**: Load testing

```bash
# Run examples
python services/worker/src/agents/writing/examples.py
```

## Monitoring & Analytics

### Built-in Statistics

```python
# Service-level stats
stats = await service.get_stats()
print(f"Cache hit rate: {stats['cache']['hit_rate']:.1%}")
print(f"Average processing time: {stats['average_processing_time_seconds']:.2f}s")

# Component-specific stats
doi_stats = await doi_validator.get_stats()
quality_stats = await quality_assessor.get_stats()
```

### Performance Monitoring

- Processing time per manuscript
- API call frequency and success rates
- Cache performance metrics
- Quality score distributions
- Warning frequency by type

## Troubleshooting

### Common Issues

#### Slow Performance
1. Check Redis connectivity
2. Monitor API rate limits
3. Review batch sizes
4. Enable performance logging

#### Low Quality Scores
1. Verify literature search quality
2. Check field-specific thresholds
3. Review journal reputation data
4. Validate DOI resolution

#### Missing Citations
1. Improve citation extraction patterns
2. Enhance literature matching algorithms
3. Review manuscript text formatting
4. Check claim classification accuracy

### Debug Mode

```python
# Enable detailed logging
import logging
logging.getLogger('agents.writing').setLevel(logging.DEBUG)

# Service statistics
service = await get_reference_service()
stats = await service.get_stats()
print(json.dumps(stats, indent=2))
```

## Roadmap

### Planned Features

- **Machine Learning Enhancement**: Semantic similarity for relevance scoring
- **Multi-language Support**: Non-English reference handling
- **Integration APIs**: Direct journal submission system integration
- **Advanced Analytics**: Citation network analysis
- **Collaborative Features**: Team reference management

### Version History

- **v1.0**: Initial release with core functionality
- **v1.1**: Enhanced quality assessment and caching
- **v1.2**: Batch processing and performance improvements
- **v1.3**: Advanced duplicate detection algorithms

## Contributing

### Development Setup

```bash
# Clone repository
git clone https://github.com/your-org/research-workflow.git
cd research-workflow

# Install dependencies
pip install -r services/worker/requirements.txt

# Run tests
pytest services/worker/src/agents/writing/
```

### Code Standards

- Follow PEP 8 style guidelines
- Add comprehensive docstrings
- Include type hints
- Write unit tests for new features
- Update this README for new functionality

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For questions and support:

- **Documentation**: This README and inline code documentation
- **Examples**: See `examples.py` for practical usage patterns
- **Issues**: GitHub Issues for bug reports and feature requests
- **Discussions**: GitHub Discussions for questions and ideas

---

*Enhanced Reference Management System - Making academic writing more efficient and reliable.*