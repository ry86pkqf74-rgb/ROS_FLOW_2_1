#!/usr/bin/env python3
"""
Protocol Generation API Client Demo

Demonstrates how to use the Protocol Generation REST API endpoints.
Shows all API capabilities including single generation, batch processing,
template management, and validation.

Usage:
    python demo/api_client_demo.py
    python demo/api_client_demo.py --host localhost --port 8002

Author: Enhancement Team
"""

import asyncio
import json
import argparse
from typing import Dict, List, Any
from datetime import datetime

# Try importing aiohttp, fallback to urllib if not available
try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    print("⚠️ aiohttp not available, using urllib for basic HTTP requests")
    import urllib.request
    import urllib.parse
    AIOHTTP_AVAILABLE = False


class ProtocolAPIClient:
    """Client for the Protocol Generation API."""
    
    def __init__(self, base_url: str = "http://localhost:8002"):
        self.base_url = base_url.rstrip('/')
        self.api_base = f"{self.base_url}/api/v1/protocols"
    
    async def health_check(self) -> Dict[str, Any]:
        """Check API health."""
        if not AIOHTTP_AVAILABLE:
            return {"status": "unavailable", "message": "aiohttp not available for testing"}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_base}/health") as response:
                    return await response.json()
        except Exception as e:
            return {"status": "error", "message": f"Connection failed: {str(e)}"}
    
    async def get_templates(self) -> Dict[str, Any]:
        """Get available templates."""
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.api_base}/templates") as response:
                return await response.json()
    
    async def generate_protocol(self,
                              template_id: str,
                              study_data: Dict[str, Any],
                              output_format: str = "markdown") -> Dict[str, Any]:
        """Generate a single protocol."""
        request_data = {
            "template_id": template_id,
            "study_data": study_data,
            "output_format": output_format
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.api_base}/generate",
                json=request_data
            ) as response:
                return await response.json()
    
    async def validate_variables(self,
                               template_id: str,
                               variables: Dict[str, Any]) -> Dict[str, Any]:
        """Validate template variables."""
        request_data = {
            "template_id": template_id,
            "variables": variables
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.api_base}/validate",
                json=request_data
            ) as response:
                return await response.json()
    
    async def batch_generate(self, requests: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate multiple protocols in batch."""
        request_data = {
            "requests": requests,
            "parallel_processing": True
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.api_base}/batch",
                json=request_data
            ) as response:
                return await response.json()


async def demo_api_capabilities():
    """Demonstrate all API capabilities."""
    print("🚀 PROTOCOL GENERATION API CLIENT DEMO")
    print("=" * 45)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    client = ProtocolAPIClient()
    
    try:
        # Health check
        print("🔍 1. API HEALTH CHECK")
        health_result = await client.health_check()
        print(f"   Status: {health_result['status']}")
        print(f"   Templates Loaded: {health_result['templates_loaded']}")
        print(f"   Version: {health_result['version']}")
        print()
        
        # Get available templates
        print("📋 2. AVAILABLE TEMPLATES")
        templates_result = await client.get_templates()
        print(f"   Total Templates: {templates_result['total_count']}")
        
        for template in templates_result['templates']:
            print(f"   🔹 {template['template_id']}")
            print(f"      Name: {template['name']}")
            print(f"      Type: {template['type']}")
            print(f"      Required Variables: {len(template['required_variables'])}")
        print()
        
        # Demo single protocol generation
        if templates_result['templates']:
            template = templates_result['templates'][0]
            template_id = template['template_id']
            
            print(f"🔧 3. SINGLE PROTOCOL GENERATION - {template_id}")
            
            # Sample study data
            study_data = {
                "study_title": "API Demo Clinical Trial",
                "protocol_number": "API-DEMO-001",
                "principal_investigator": "Dr. API Demo",
                "primary_objective": "To demonstrate API-driven protocol generation",
                "design_description": "Randomized, double-blind, placebo-controlled trial",
                "estimated_sample_size": 200,
                "target_population_description": "Adults with diabetes mellitus type 2"
            }
            
            # Validate variables first
            validation_result = await client.validate_variables(template_id, study_data)
            print(f"   Variables Valid: {validation_result['valid']}")
            if validation_result['missing_variables']:
                print(f"   Missing Variables: {validation_result['missing_variables']}")
            
            # Generate protocol
            generation_result = await client.generate_protocol(
                template_id, study_data, "markdown"
            )
            
            if generation_result['success']:
                print(f"   ✅ Success! Generated {generation_result['content_length']} characters")
                print(f"   📊 Metadata: {generation_result['metadata']['sections_count']} sections")
            else:
                print(f"   ❌ Failed: {generation_result['error']}")
            print()
        
        # Demo batch processing
        print("⚡ 4. BATCH PROCESSING DEMO")
        if len(templates_result['templates']) >= 2:
            batch_requests = []
            
            for i, template in enumerate(templates_result['templates'][:2]):
                batch_requests.append({
                    "template_id": template['template_id'],
                    "study_data": {
                        "study_title": f"Batch Study {i+1}",
                        "principal_investigator": f"Dr. Batch Demo {i+1}",
                        "primary_objective": f"Batch objective {i+1}",
                        "design_description": f"Batch design {i+1}",
                        "estimated_sample_size": 100 + i*50,
                        "target_population_description": f"Batch population {i+1}"
                    },
                    "output_format": "markdown"
                })
            
            batch_result = await client.batch_generate(batch_requests)
            print(f"   Total Requests: {batch_result['total_requests']}")
            print(f"   Successful: {batch_result['successful_requests']}")
            print(f"   Failed: {batch_result['failed_requests']}")
            print(f"   Processing Time: {batch_result['processing_time_seconds']:.2f} seconds")
        else:
            print("   Skipped - need at least 2 templates for batch demo")
        
        print("\n✅ API DEMO COMPLETED SUCCESSFULLY!")
        print("The Protocol Generation API is ready for integration!")
        
    except aiohttp.ClientError as e:
        print(f"❌ API Connection Error: {str(e)}")
        print("Make sure the API server is running on localhost:8002")
        print("Start it with: cd services/worker && python src/api/protocol_api.py")
    
    except Exception as e:
        print(f"❌ Demo failed: {str(e)}")


async def demo_specific_endpoint(endpoint: str, **kwargs):
    """Demo a specific API endpoint."""
    client = ProtocolAPIClient()
    
    if endpoint == "health":
        result = await client.health_check()
        print(json.dumps(result, indent=2))
    elif endpoint == "templates":
        result = await client.get_templates()
        print(json.dumps(result, indent=2))
    else:
        print(f"Unknown endpoint: {endpoint}")


def main():
    """Main function with argument parsing."""
    parser = argparse.ArgumentParser(description="Protocol Generation API Client Demo")
    parser.add_argument("--host", default="localhost", help="API host")
    parser.add_argument("--port", type=int, default=8002, help="API port")
    parser.add_argument("--endpoint", help="Demo specific endpoint (health, templates)")
    
    args = parser.parse_args()
    
    if args.endpoint:
        asyncio.run(demo_specific_endpoint(args.endpoint))
    else:
        asyncio.run(demo_api_capabilities())


if __name__ == "__main__":
    main()