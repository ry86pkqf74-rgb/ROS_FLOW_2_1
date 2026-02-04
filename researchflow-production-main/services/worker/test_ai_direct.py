#!/usr/bin/env python3
"""
Direct test of AI functionality without the API server.
Expanded to cover all major EnhancedAIProcessor methods.
"""

import asyncio
import sys
from pathlib import Path
import logging  # Added for audit logging simulation

sys.path.insert(0, str(Path(__file__).parent / "src"))

from ai.enhanced_processing import get_ai_processor

# Simulate audit log (per ResearchFlow Rules)
def audit_log(message: str):
    logging.info(f"AUDIT: {message}")

async def test_ai():
    print("🧪 Testing AI processor directly...")
    
    processor = get_ai_processor()
    print(f"📋 Model info: {processor.get_model_info()}")
    
    print("🔄 Ensuring initialization...")
    await processor._ensure_initialized()
    
    print(f"✅ Ready status: {processor.is_ready()}")
    print(f"📋 Updated model info: {processor.get_model_info()}")
    
    if not processor.is_ready():
        print("❌ AI processor not ready - skipping tests")
        return

    audit_log("Starting AI tests")  # Audit trail

    # Existing: Test embeddings
    print("🧪 Testing embeddings...")
    results = await processor.get_embeddings(["Test sentence for embedding", "Another test"])
    for res in results:
        print(f"✅ Embedding success: {res.success}, Shape: {res.embedding.shape}")
    
    # New: Test semantic search
    print("🧪 Testing semantic search...")
    search_res = await processor.semantic_search(
        "Test query", ["Doc1: Similar content", "Doc2: Different content"], top_k=2
    )
    print(f"✅ Matches found: {len(search_res.matches)}, Top score: {search_res.scores[0] if search_res.scores else 'N/A'}")
    
    # New: Test entity extraction
    print("🧪 Testing entity extraction...")
    entities = await processor.extract_entities("Patient has diabetes and hypertension.")
    print(f"✅ Entities extracted: {entities['count'] if entities['success'] else 'Failed'}")
    
    # New: Test literature matching
    print("🧪 Testing literature matching...")
    literature_db = [{"title": "Study on AI", "abstract": "AI in healthcare"}]
    match_res = await processor.enhanced_literature_matching("AI applications", literature_db)
    print(f"✅ Matches: {match_res['total']}")
    
    # Edge case: Empty inputs
    print("🧪 Testing edge cases...")
    empty_emb = await processor.get_embeddings([])
    print(f"✅ Empty embeddings handled: {len(empty_emb) == 0}")
    
    audit_log("AI tests completed")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)  # Setup logging
    asyncio.run(test_ai())