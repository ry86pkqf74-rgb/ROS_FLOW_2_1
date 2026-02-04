"""
AI Frontend Integration Example
Demonstrates how to integrate the enhanced AI functionality with frontend applications.
Provides examples of API calls, WebSocket integration, and real-time processing.
"""

import asyncio
import aiohttp
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import time

@dataclass
class AIIntegrationConfig:
    """Configuration for AI integration"""
    base_url: str = "http://localhost:8000"
    api_version: str = "v1"
    timeout: int = 30
    max_retries: int = 3

class AIFrontendClient:
    """Client for integrating with ResearchFlow AI APIs"""
    
    def __init__(self, config: AIIntegrationConfig = None):
        self.config = config or AIIntegrationConfig()
        self.base_url = f"{self.config.base_url}/api/{self.config.api_version}/ai"
        self.session = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.config.timeout)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def check_health(self) -> Dict[str, Any]:
        """Check if AI services are available"""
        try:
            async with self.session.get(f"{self.base_url}/health") as response:
                return await response.json()
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    async def get_embeddings(self, texts: List[str]) -> Dict[str, Any]:
        """Get text embeddings from AI service"""
        payload = {"texts": texts}
        
        try:
            async with self.session.post(
                f"{self.base_url}/embeddings",
                json=payload
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error = await response.text()
                    return {"success": False, "error": error}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def semantic_search(self, query: str, documents: List[str], 
                            top_k: int = 5, threshold: float = 0.7) -> Dict[str, Any]:
        """Perform semantic search"""
        payload = {
            "query": query,
            "documents": documents,
            "top_k": top_k,
            "similarity_threshold": threshold
        }
        
        try:
            async with self.session.post(
                f"{self.base_url}/search",
                json=payload
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error = await response.text()
                    return {"success": False, "error": error}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def extract_entities(self, text: str) -> Dict[str, Any]:
        """Extract named entities from text"""
        payload = {"text": text}
        
        try:
            async with self.session.post(
                f"{self.base_url}/entities",
                json=payload
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error = await response.text()
                    return {"success": False, "error": error}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def match_literature(self, query: str, literature: List[Dict], 
                              top_k: int = 10) -> Dict[str, Any]:
        """Match literature using AI"""
        payload = {
            "query": query,
            "literature_database": literature,
            "top_k": top_k
        }
        
        try:
            async with self.session.post(
                f"{self.base_url}/literature/match",
                json=payload
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error = await response.text()
                    return {"success": False, "error": error}
        except Exception as e:
            return {"success": False, "error": str(e)}

# React/JavaScript Integration Examples (Python representations)
def generate_react_integration_examples():
    """Generate JavaScript/React integration examples"""
    
    javascript_examples = {
        "api_client": """
// AI API Client for React/JavaScript frontend
class AIClient {
    constructor(baseUrl = 'http://localhost:8000/api/v1/ai') {
        this.baseUrl = baseUrl;
    }

    async checkHealth() {
        try {
            const response = await fetch(`${this.baseUrl}/health`);
            return await response.json();
        } catch (error) {
            console.error('AI health check failed:', error);
            return { status: 'error', message: error.message };
        }
    }

    async getEmbeddings(texts) {
        try {
            const response = await fetch(`${this.baseUrl}/embeddings`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ texts })
            });
            return await response.json();
        } catch (error) {
            console.error('Embedding generation failed:', error);
            throw error;
        }
    }

    async semanticSearch(query, documents, topK = 5, threshold = 0.7) {
        try {
            const response = await fetch(`${this.baseUrl}/search`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    query,
                    documents,
                    top_k: topK,
                    similarity_threshold: threshold
                })
            });
            return await response.json();
        } catch (error) {
            console.error('Semantic search failed:', error);
            throw error;
        }
    }
}

export default AIClient;
""",
        
        "react_hook": """
// React Hook for AI functionality
import { useState, useCallback } from 'react';
import AIClient from './AIClient';

export const useAI = () => {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const aiClient = new AIClient();

    const performSemanticSearch = useCallback(async (query, documents, options = {}) => {
        setLoading(true);
        setError(null);
        
        try {
            const result = await aiClient.semanticSearch(
                query, 
                documents, 
                options.topK || 5,
                options.threshold || 0.7
            );
            return result;
        } catch (err) {
            setError(err.message);
            throw err;
        } finally {
            setLoading(false);
        }
    }, []);

    const extractEntities = useCallback(async (text) => {
        setLoading(true);
        setError(null);
        
        try {
            const response = await fetch('/api/v1/ai/entities', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text })
            });
            return await response.json();
        } catch (err) {
            setError(err.message);
            throw err;
        } finally {
            setLoading(false);
        }
    }, []);

    return {
        loading,
        error,
        performSemanticSearch,
        extractEntities,
        clearError: () => setError(null)
    };
};
""",
        
        "react_component": """
// React Component using AI functionality
import React, { useState, useEffect } from 'react';
import { useAI } from './hooks/useAI';

const SmartLiteratureSearch = ({ literature }) => {
    const [query, setQuery] = useState('');
    const [results, setResults] = useState([]);
    const { performSemanticSearch, loading, error } = useAI();

    const handleSearch = async () => {
        if (!query.trim()) return;
        
        try {
            const documents = literature.map(item => 
                `${item.title} ${item.abstract || ''}`.trim()
            );
            
            const searchResults = await performSemanticSearch(query, documents);
            setResults(searchResults.matches || []);
        } catch (err) {
            console.error('Search failed:', err);
        }
    };

    return (
        <div className="smart-literature-search">
            <div className="search-input">
                <input
                    type="text"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder="Enter research query..."
                    disabled={loading}
                />
                <button 
                    onClick={handleSearch}
                    disabled={loading || !query.trim()}
                >
                    {loading ? 'Searching...' : 'AI Search'}
                </button>
            </div>
            
            {error && (
                <div className="error-message">
                    Error: {error}
                </div>
            )}
            
            <div className="search-results">
                {results.map((match, index) => (
                    <div key={index} className="result-item">
                        <div className="similarity-score">
                            Similarity: {(match.score * 100).toFixed(1)}%
                        </div>
                        <div className="document-preview">
                            {match.document.substring(0, 200)}...
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};

export default SmartLiteratureSearch;
"""
    }
    
    return javascript_examples

# Demo functions
async def demo_basic_functionality():
    """Demonstrate basic AI functionality"""
    print("🚀 AI Frontend Integration Demo")
    print("=" * 50)
    
    async with AIFrontendClient() as client:
        # Health check
        print("\n1. Health Check")
        health = await client.check_health()
        print(f"Status: {health.get('status', 'unknown')}")
        
        if health.get('status') != 'healthy':
            print("⚠️  AI services not available. Please start the AI-enabled worker.")
            return
        
        # Text embeddings
        print("\n2. Text Embeddings Demo")
        sample_texts = [
            "Clinical trial for cardiovascular disease",
            "Machine learning in medical diagnosis",
            "Patient safety and quality improvement"
        ]
        
        embeddings_result = await client.get_embeddings(sample_texts)
        if embeddings_result.get('success'):
            print(f"Generated embeddings for {len(sample_texts)} texts")
            print(f"Embedding dimension: {len(embeddings_result['embeddings'][0])}")
        else:
            print(f"Embedding failed: {embeddings_result.get('error')}")
        
        # Semantic search
        print("\n3. Semantic Search Demo")
        documents = [
            "A randomized controlled trial investigating the efficacy of new cardiac medications",
            "Systematic review of machine learning applications in radiology",
            "Patient outcomes following minimally invasive surgical procedures",
            "Economic analysis of healthcare interventions in primary care",
            "Quality metrics for hospital performance evaluation"
        ]
        
        search_query = "cardiac treatment effectiveness"
        search_result = await client.semantic_search(search_query, documents, top_k=3)
        
        if 'matches' in search_result:
            print(f"Found {len(search_result['matches'])} relevant matches:")
            for i, match in enumerate(search_result['matches'], 1):
                print(f"  {i}. Score: {match['score']:.3f}")
                print(f"     Text: {match['document'][:80]}...")
        else:
            print(f"Search failed: {search_result.get('error')}")
        
        # Entity extraction
        print("\n4. Entity Extraction Demo")
        sample_text = "Dr. John Smith conducted a study at Mayo Clinic involving 200 patients with diabetes."
        entities_result = await client.extract_entities(sample_text)
        
        if entities_result.get('success'):
            print(f"Extracted {len(entities_result['entities'])} entities:")
            for entity in entities_result['entities']:
                print(f"  - {entity['text']} ({entity['label']}, {entity['confidence']:.2f})")
        else:
            print(f"Entity extraction failed: {entities_result.get('error')}")

async def demo_literature_matching():
    """Demonstrate literature matching functionality"""
    print("\n5. Literature Matching Demo")
    print("-" * 30)
    
    # Sample literature database
    literature_db = [
        {
            "id": 1,
            "title": "Efficacy of Novel Cardiac Interventions",
            "abstract": "This study examines the effectiveness of new minimally invasive cardiac procedures in reducing patient mortality and improving quality of life outcomes.",
            "authors": ["Smith, J.", "Johnson, M."],
            "journal": "Cardiology Today",
            "year": 2023
        },
        {
            "id": 2,
            "title": "Machine Learning in Diagnostic Imaging",
            "abstract": "We present a comprehensive analysis of machine learning algorithms applied to medical imaging for improved diagnostic accuracy.",
            "authors": ["Brown, K.", "Davis, L."],
            "journal": "AI in Medicine",
            "year": 2023
        },
        {
            "id": 3,
            "title": "Patient Safety in Surgical Environments",
            "abstract": "A systematic review of patient safety protocols and their impact on surgical outcomes across multiple hospital systems.",
            "authors": ["Wilson, R.", "Taylor, S."],
            "journal": "Surgery & Safety",
            "year": 2022
        }
    ]
    
    async with AIFrontendClient() as client:
        query = "cardiac surgery outcomes and patient safety"
        
        match_result = await client.match_literature(query, literature_db, top_k=3)
        
        if 'matches' in match_result:
            print(f"Literature matches for: '{query}'")
            for i, match in enumerate(match_result['matches'], 1):
                print(f"\n{i}. {match['title']}")
                print(f"   Authors: {', '.join(match['authors'])}")
                print(f"   Journal: {match['journal']} ({match['year']})")
                print(f"   Similarity: {match['similarity_score']:.3f}")
                print(f"   Abstract: {match['abstract'][:150]}...")
        else:
            print(f"Literature matching failed: {match_result.get('error')}")

def print_integration_examples():
    """Print frontend integration examples"""
    print("\n" + "=" * 60)
    print("FRONTEND INTEGRATION EXAMPLES")
    print("=" * 60)
    
    examples = generate_react_integration_examples()
    
    for name, code in examples.items():
        print(f"\n📄 {name.replace('_', ' ').title()}")
        print("-" * 40)
        print(code)

async def main():
    """Main demo function"""
    try:
        await demo_basic_functionality()
        await demo_literature_matching()
        print_integration_examples()
        
        print("\n" + "=" * 60)
        print("🎉 AI INTEGRATION DEMO COMPLETE")
        print("=" * 60)
        print("\nNext Steps:")
        print("1. Install AI packages: pip install -r requirements-ai-enhanced.txt")
        print("2. Start the AI-enabled worker service")
        print("3. Integrate the provided JavaScript/React examples")
        print("4. Test the API endpoints with your frontend application")
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        print("\nPlease ensure:")
        print("- AI packages are installed")
        print("- Worker service is running")
        print("- Network connectivity is available")

if __name__ == "__main__":
    asyncio.run(main())