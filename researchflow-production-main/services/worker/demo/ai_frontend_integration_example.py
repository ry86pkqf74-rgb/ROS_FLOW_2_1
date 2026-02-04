#!/usr/bin/env python3
"""
AI Frontend Integration Example
=====================================

This script demonstrates how to use the ResearchFlow AI-enhanced endpoints
for semantic search, embeddings generation, and entity extraction.

It provides practical examples that frontend developers can use to integrate
AI functionality into the ResearchFlow web application.

Usage:
    python3 demo/ai_frontend_integration_example.py

Requirements:
    - Worker API running on http://localhost:8000
    - AI packages installed (run install-ai-packages.sh first)
"""

import asyncio
import json
import time
from typing import Dict, List, Any
import httpx
import sys
from pathlib import Path

# Add src to path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Configuration
API_BASE_URL = "http://localhost:8000"
TIMEOUT = 30.0

# Sample research data for testing
SAMPLE_LITERATURE = [
    {
        "title": "Machine Learning in Clinical Decision Support",
        "abstract": "This study explores the application of machine learning algorithms in clinical decision support systems. We evaluated various ML models for predicting patient outcomes and found significant improvements in diagnostic accuracy.",
        "authors": ["Smith, J.", "Johnson, M.", "Brown, K."],
        "journal": "Journal of Medical Informatics",
        "year": 2023,
        "pmid": "12345678"
    },
    {
        "title": "Deep Learning for Medical Image Analysis",
        "abstract": "We present a deep learning approach for automated medical image analysis. Our convolutional neural network achieved 94% accuracy in detecting abnormalities in chest X-rays.",
        "authors": ["Davis, L.", "Wilson, R.", "Taylor, S."],
        "journal": "Medical Image Analysis",
        "year": 2023,
        "pmid": "23456789"
    },
    {
        "title": "Natural Language Processing in Healthcare",
        "abstract": "This paper reviews the application of natural language processing techniques in healthcare settings. We discuss methods for extracting clinical insights from electronic health records.",
        "authors": ["Anderson, P.", "Martin, C.", "Thompson, D."],
        "journal": "Healthcare Informatics Research",
        "year": 2022,
        "pmid": "34567890"
    },
    {
        "title": "Predictive Analytics for Hospital Readmissions",
        "abstract": "We developed a predictive model to identify patients at high risk of hospital readmission. The model incorporates demographic, clinical, and social determinants of health.",
        "authors": ["Garcia, M.", "Rodriguez, A.", "Lopez, C."],
        "journal": "Health Services Research",
        "year": 2023,
        "pmid": "45678901"
    }
]

SAMPLE_CLINICAL_TEXT = """
Patient: John Smith, 65-year-old male
Chief Complaint: Chest pain and shortness of breath
History: Patient presents with 3-day history of chest pain radiating to left arm. Past medical history significant for diabetes mellitus type 2, hypertension, and hyperlipidemia. Current medications include metformin 1000mg BID, lisinopril 10mg daily, and atorvastatin 40mg daily.
Physical Exam: Vital signs stable. Cardiac exam reveals regular rate and rhythm with no murmurs. Lungs clear bilaterally.
Assessment: Rule out myocardial infarction. Order EKG, troponin levels, and chest X-ray.
Plan: Admit to cardiology service for further evaluation and management.
"""

class AIClientDemo:
    """
    Demo client for ResearchFlow AI endpoints
    """
    
    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=TIMEOUT)
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def health_check(self) -> Dict[str, Any]:
        """Check if AI services are healthy"""
        print("🏥 Checking AI service health...")
        try:
            response = await self.client.get(f"{self.base_url}/api/v1/ai/health")
            response.raise_for_status()
            result = response.json()
            
            status = result.get("status", "unknown")
            if status == "healthy":
                print("✅ AI services are healthy and ready")
            else:
                print(f"⚠️  AI services status: {status}")
                
            return result
        except Exception as e:
            print(f"❌ Health check failed: {e}")
            return {"status": "error", "message": str(e)}
    
    async def get_model_info(self) -> Dict[str, Any]:
        """Get information about loaded AI models"""
        print("🤖 Getting AI model information...")
        try:
            response = await self.client.get(f"{self.base_url}/api/v1/ai/models")
            response.raise_for_status()
            result = response.json()
            
            print(f"✅ AI packages available: {result.get('ai_packages_available')}")
            print(f"✅ Models initialized: {result.get('initialized')}")
            print(f"✅ Loaded models: {', '.join(result.get('loaded_models', []))}")
            
            return result
        except Exception as e:
            print(f"❌ Model info failed: {e}")
            return {}
    
    async def generate_embeddings(self, texts: List[str]) -> Dict[str, Any]:
        """Generate embeddings for text list"""
        print(f"🔢 Generating embeddings for {len(texts)} texts...")
        
        start_time = time.time()
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/ai/embeddings",
                json={"texts": texts}
            )
            response.raise_for_status()
            result = response.json()
            
            duration = time.time() - start_time
            embeddings = result.get("embeddings", [])
            
            print(f"✅ Generated {len(embeddings)} embeddings")
            if embeddings:
                print(f"   - Embedding dimension: {len(embeddings[0])}")
                print(f"   - Model used: {result.get('model_name')}")
                print(f"   - Processing time: {duration:.2f}s")
            
            return result
        except Exception as e:
            print(f"❌ Embedding generation failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def semantic_search(self, query: str, documents: List[str], top_k: int = 3) -> Dict[str, Any]:
        """Perform semantic search on documents"""
        print(f"🔍 Searching for '{query}' in {len(documents)} documents...")
        
        start_time = time.time()
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/ai/search",
                json={
                    "query": query,
                    "documents": documents,
                    "top_k": top_k,
                    "similarity_threshold": 0.3
                }
            )
            response.raise_for_status()
            result = response.json()
            
            duration = time.time() - start_time
            matches = result.get("matches", [])
            
            print(f"✅ Found {len(matches)} relevant matches")
            for i, match in enumerate(matches[:3]):
                score = match.get("score", 0)
                doc_preview = match.get("document", "")[:100] + "..."
                print(f"   {i+1}. Score: {score:.3f} - {doc_preview}")
            
            print(f"   - Processing time: {duration:.2f}s")
            return result
        except Exception as e:
            print(f"❌ Semantic search failed: {e}")
            return {"matches": [], "error": str(e)}
    
    async def extract_entities(self, text: str) -> Dict[str, Any]:
        """Extract named entities from text"""
        print("🏷️  Extracting entities from clinical text...")
        
        start_time = time.time()
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/ai/entities",
                json={"text": text}
            )
            response.raise_for_status()
            result = response.json()
            
            duration = time.time() - start_time
            entities = result.get("entities", [])
            
            print(f"✅ Extracted {len(entities)} entities")
            for entity in entities[:10]:  # Show first 10
                print(f"   - {entity.get('text')}: {entity.get('label')} (confidence: {entity.get('confidence', 0):.3f})")
            
            print(f"   - Processing time: {duration:.2f}s")
            return result
        except Exception as e:
            print(f"❌ Entity extraction failed: {e}")
            return {"entities": [], "error": str(e)}
    
    async def literature_matching(self, query: str, literature: List[Dict]) -> Dict[str, Any]:
        """Match query against literature database"""
        print(f"📚 Matching query against {len(literature)} literature entries...")
        
        start_time = time.time()
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/ai/literature/match",
                json={
                    "query": query,
                    "literature_database": literature,
                    "top_k": 5
                }
            )
            response.raise_for_status()
            result = response.json()
            
            duration = time.time() - start_time
            matches = result.get("matches", [])
            
            print(f"✅ Found {len(matches)} relevant literature matches")
            for i, match in enumerate(matches):
                title = match.get("title", "Unknown")
                score = match.get("similarity_score", 0)
                year = match.get("year", "N/A")
                print(f"   {i+1}. {title} ({year}) - Score: {score:.3f}")
            
            print(f"   - Processing time: {duration:.2f}s")
            return result
        except Exception as e:
            print(f"❌ Literature matching failed: {e}")
            return {"matches": [], "error": str(e)}

async def demo_basic_functionality():
    """Demo basic AI functionality"""
    print("\n" + "="*60)
    print("🚀 DEMO 1: Basic AI Functionality")
    print("="*60)
    
    async with AIClientDemo() as client:
        # Health check
        health = await client.health_check()
        if health.get("status") != "healthy":
            print("❌ AI services not healthy. Please check installation.")
            return
        
        # Model info
        await client.get_model_info()
        
        # Test embeddings
        test_texts = [
            "Machine learning in healthcare",
            "Deep learning for medical diagnosis", 
            "Natural language processing for clinical notes"
        ]
        await client.generate_embeddings(test_texts)

async def demo_semantic_search():
    """Demo semantic search functionality"""
    print("\n" + "="*60)
    print("🔍 DEMO 2: Semantic Search")
    print("="*60)
    
    async with AIClientDemo() as client:
        # Prepare documents from literature
        documents = [f"{lit['title']}. {lit['abstract']}" for lit in SAMPLE_LITERATURE]
        
        # Test various search queries
        queries = [
            "machine learning clinical decision",
            "deep learning medical images", 
            "natural language processing healthcare",
            "predictive analytics readmissions"
        ]
        
        for query in queries:
            print(f"\n📋 Query: '{query}'")
            await client.semantic_search(query, documents, top_k=2)

async def demo_entity_extraction():
    """Demo entity extraction from clinical text"""
    print("\n" + "="*60)
    print("🏷️  DEMO 3: Clinical Entity Extraction")
    print("="*60)
    
    async with AIClientDemo() as client:
        await client.extract_entities(SAMPLE_CLINICAL_TEXT)

async def demo_literature_matching():
    """Demo literature matching functionality"""
    print("\n" + "="*60)
    print("📚 DEMO 4: Literature Matching")
    print("="*60)
    
    async with AIClientDemo() as client:
        queries = [
            "How effective is machine learning for clinical decision support?",
            "What are the best methods for medical image analysis?",
            "Can NLP help extract insights from patient records?",
            "How do you predict hospital readmissions?"
        ]
        
        for query in queries:
            print(f"\n❓ Research Question: '{query}'")
            await client.literature_matching(query, SAMPLE_LITERATURE)

async def demo_batch_processing():
    """Demo batch processing capabilities"""
    print("\n" + "="*60)
    print("⚡ DEMO 5: Batch Processing Performance")
    print("="*60)
    
    async with AIClientDemo() as client:
        # Create larger text dataset
        batch_texts = []
        for i in range(50):
            batch_texts.extend([
                f"Clinical study #{i}: Machine learning applications in healthcare",
                f"Research paper #{i}: Deep learning for medical diagnosis",
                f"Analysis #{i}: Natural language processing in clinical settings"
            ])
        
        print(f"📊 Processing {len(batch_texts)} texts in batch...")
        
        start_time = time.time()
        result = await client.generate_embeddings(batch_texts)
        total_time = time.time() - start_time
        
        if result.get("success"):
            embeddings_count = len(result.get("embeddings", []))
            throughput = embeddings_count / total_time if total_time > 0 else 0
            
            print(f"✅ Batch processing complete:")
            print(f"   - Processed: {embeddings_count} texts")
            print(f"   - Total time: {total_time:.2f}s")
            print(f"   - Throughput: {throughput:.1f} texts/second")
            print(f"   - Average per text: {(total_time/embeddings_count)*1000:.1f}ms")

async def demo_frontend_integration_patterns():
    """Demo integration patterns for frontend developers"""
    print("\n" + "="*60)
    print("🌐 DEMO 6: Frontend Integration Patterns")
    print("="*60)
    
    print("📋 JavaScript/TypeScript Integration Examples:")
    print("""
// Example 1: Search Literature with Semantic Matching
async function searchLiterature(query: string): Promise<LiteratureResult[]> {
  const response = await fetch('/api/v1/ai/literature/match', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query,
      literature_database: literatureData,
      top_k: 10
    })
  });
  
  const result = await response.json();
  return result.matches;
}

// Example 2: Real-time Entity Extraction
async function extractClinicalEntities(text: string): Promise<Entity[]> {
  const response = await fetch('/api/v1/ai/entities', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text })
  });
  
  const result = await response.json();
  return result.entities;
}

// Example 3: Semantic Search in Research Data
async function semanticSearch(query: string, documents: string[]): Promise<SearchResult[]> {
  const response = await fetch('/api/v1/ai/search', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query,
      documents,
      top_k: 5,
      similarity_threshold: 0.7
    })
  });
  
  const result = await response.json();
  return result.matches;
}
""")
    
    print("⚡ React Component Example:")
    print("""
// SearchComponent.tsx
import { useState, useCallback } from 'react';

interface SearchComponentProps {
  onResults: (results: any[]) => void;
}

export function SemanticSearchComponent({ onResults }: SearchComponentProps) {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  
  const handleSearch = useCallback(async () => {
    if (!query.trim()) return;
    
    setLoading(true);
    try {
      const response = await fetch('/api/v1/ai/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query,
          documents: documentDatabase,
          top_k: 10
        })
      });
      
      const result = await response.json();
      onResults(result.matches);
    } catch (error) {
      console.error('Search failed:', error);
    } finally {
      setLoading(false);
    }
  }, [query, onResults]);
  
  return (
    <div className="search-component">
      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Enter research query..."
        onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
      />
      <button onClick={handleSearch} disabled={loading}>
        {loading ? 'Searching...' : 'Search'}
      </button>
    </div>
  );
}
""")

async def run_comprehensive_demo():
    """Run all demo scenarios"""
    print("🚀 ResearchFlow AI Integration Demo")
    print("==================================")
    print("This demo showcases the AI-enhanced functionality available in ResearchFlow.")
    print("Make sure the worker API is running on http://localhost:8000\n")
    
    try:
        # Run all demos
        await demo_basic_functionality()
        await demo_semantic_search()
        await demo_entity_extraction()  
        await demo_literature_matching()
        await demo_batch_processing()
        await demo_frontend_integration_patterns()
        
        print("\n" + "="*60)
        print("✅ DEMO COMPLETE - All AI Features Working!")
        print("="*60)
        print("\n🎯 Next Steps for Frontend Integration:")
        print("1. Use the JavaScript examples above in your React components")
        print("2. Implement error handling and loading states")
        print("3. Add user feedback for AI processing status")
        print("4. Consider caching frequently used embeddings")
        print("5. Implement progressive enhancement for AI features")
        print("\n📚 For more details, see the API documentation at:")
        print("   http://localhost:8000/docs")
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Demo interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Demo failed with error: {e}")
        print("Please ensure:")
        print("1. Worker API is running: python3 src/main.py")
        print("2. AI packages are installed: ./install-ai-packages.sh")
        print("3. Models are downloaded and cached")

if __name__ == "__main__":
    print("Starting ResearchFlow AI Demo...")
    asyncio.run(run_comprehensive_demo())