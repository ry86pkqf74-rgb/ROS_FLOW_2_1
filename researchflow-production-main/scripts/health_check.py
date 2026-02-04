#!/usr/bin/env python3
"""
Analytics Health Check Script
============================

Comprehensive health check for analytics services including:
- API endpoint availability
- Database connectivity
- WebSocket service status
- ML model availability
- System resource usage
"""

import asyncio
import aiohttp
import asyncpg
import json
import sys
import os
import time
from datetime import datetime
from typing import Dict, Any, List


class HealthChecker:
    """Comprehensive health checker for analytics services."""
    
    def __init__(self):
        self.base_url = os.getenv("ANALYTICS_BASE_URL", "http://localhost:8000")
        self.db_url = os.getenv("ANALYTICS_DATABASE_URL")
        self.websocket_url = os.getenv("ANALYTICS_WEBSOCKET_URL", "ws://localhost:8080")
        self.timeout = int(os.getenv("HEALTH_CHECK_TIMEOUT", "10"))
        
    async def check_api_health(self) -> Dict[str, Any]:
        """Check API endpoint health."""
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                # Check main health endpoint
                async with session.get(f"{self.base_url}/health") as response:
                    if response.status != 200:
                        return {"status": "error", "message": f"Health endpoint returned {response.status}"}
                    
                    health_data = await response.json()
                
                # Check analytics-specific health
                async with session.get(f"{self.base_url}/api/analytics/health") as response:
                    if response.status == 200:
                        analytics_data = await response.json()
                    else:
                        analytics_data = {"status": "unavailable"}
                
                # Check info endpoint
                async with session.get(f"{self.base_url}/api/analytics/info") as response:
                    if response.status == 200:
                        info_data = await response.json()
                    else:
                        info_data = {"status": "unavailable"}
                
                return {
                    "status": "healthy",
                    "api_health": health_data,
                    "analytics_health": analytics_data,
                    "system_info": info_data,
                    "response_time_ms": 0  # Would measure actual response time
                }
                
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    async def check_database_health(self) -> Dict[str, Any]:
        """Check database connectivity and performance."""
        if not self.db_url:
            return {"status": "skipped", "message": "No database URL configured"}
        
        try:
            start_time = time.time()
            
            # Test connection
            conn = await asyncpg.connect(self.db_url)
            
            # Test query
            result = await conn.fetchval("SELECT 1")
            if result != 1:
                await conn.close()
                return {"status": "error", "message": "Database query failed"}
            
            # Check analytics tables exist
            tables_query = """
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name LIKE 'analytics_%'
            """
            analytics_tables = await conn.fetch(tables_query)
            
            # Get connection count
            connections_query = "SELECT count(*) FROM pg_stat_activity"
            connection_count = await conn.fetchval(connections_query)
            
            await conn.close()
            
            response_time = (time.time() - start_time) * 1000
            
            return {
                "status": "healthy",
                "response_time_ms": round(response_time, 2),
                "analytics_tables": len(analytics_tables),
                "connection_count": connection_count,
                "tables": [row['table_name'] for row in analytics_tables]
            }
            
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    async def check_websocket_health(self) -> Dict[str, Any]:
        """Check WebSocket service health."""
        try:
            import websockets
            
            start_time = time.time()
            
            # Test WebSocket connection
            uri = self.websocket_url + "/api/analytics/ws/realtime"
            async with websockets.connect(uri, timeout=self.timeout) as websocket:
                # Send ping message
                ping_message = {
                    "type": "ping",
                    "client_time": datetime.now().isoformat()
                }
                await websocket.send(json.dumps(ping_message))
                
                # Wait for response
                response = await websockets.wait_for(websocket.recv(), timeout=5.0)
                response_data = json.loads(response)
                
                response_time = (time.time() - start_time) * 1000
                
                if response_data.get("type") == "pong":
                    return {
                        "status": "healthy",
                        "response_time_ms": round(response_time, 2),
                        "ping_successful": True
                    }
                else:
                    return {
                        "status": "error",
                        "message": f"Unexpected response: {response_data.get('type')}"
                    }
        
        except ImportError:
            return {"status": "skipped", "message": "websockets library not available"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    async def check_model_health(self) -> Dict[str, Any]:
        """Check ML model availability."""
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                # Test prediction endpoint with minimal data
                test_manuscript = {
                    "title": "Health Check Test",
                    "abstract": "Test manuscript for health check",
                    "metadata": {
                        "word_count": 100,
                        "reference_count": 5,
                        "figure_count": 1,
                        "table_count": 0
                    }
                }
                
                start_time = time.time()
                
                async with session.post(
                    f"{self.base_url}/api/analytics/predict-size",
                    json=test_manuscript
                ) as response:
                    response_time = (time.time() - start_time) * 1000
                    
                    if response.status == 200:
                        prediction_data = await response.json()
                        return {
                            "status": "healthy",
                            "response_time_ms": round(response_time, 2),
                            "prediction_successful": True,
                            "predicted_size": prediction_data.get("prediction", {}).get("predicted_size_bytes"),
                            "confidence": prediction_data.get("prediction", {}).get("confidence_score")
                        }
                    else:
                        return {
                            "status": "error",
                            "message": f"Prediction endpoint returned {response.status}"
                        }
        
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    async def check_system_resources(self) -> Dict[str, Any]:
        """Check system resource usage."""
        try:
            import psutil
            
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            
            # Disk usage
            disk = psutil.disk_usage('/')
            
            # Process count
            process_count = len(psutil.pids())
            
            return {
                "status": "healthy",
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available_mb": memory.available // 1024 // 1024,
                "disk_percent": disk.percent,
                "disk_free_gb": disk.free // 1024 // 1024 // 1024,
                "process_count": process_count
            }
            
        except ImportError:
            return {"status": "skipped", "message": "psutil not available"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    async def run_comprehensive_check(self) -> Dict[str, Any]:
        """Run all health checks."""
        start_time = time.time()
        
        checks = {
            "api": await self.check_api_health(),
            "database": await self.check_database_health(),
            "websocket": await self.check_websocket_health(),
            "model": await self.check_model_health(),
            "system": await self.check_system_resources()
        }
        
        total_time = (time.time() - start_time) * 1000
        
        # Determine overall status
        overall_status = "healthy"
        critical_failures = []
        warnings = []
        
        for check_name, check_result in checks.items():
            status = check_result.get("status")
            
            if status == "error":
                if check_name in ["api", "database"]:  # Critical services
                    critical_failures.append(f"{check_name}: {check_result.get('message', 'Unknown error')}")
                    overall_status = "unhealthy"
                else:  # Non-critical services
                    warnings.append(f"{check_name}: {check_result.get('message', 'Unknown error')}")
                    if overall_status == "healthy":
                        overall_status = "degraded"
        
        return {
            "timestamp": datetime.now().isoformat(),
            "overall_status": overall_status,
            "total_check_time_ms": round(total_time, 2),
            "checks": checks,
            "critical_failures": critical_failures,
            "warnings": warnings,
            "healthy_services": [name for name, result in checks.items() if result.get("status") == "healthy"],
            "service_count": {
                "total": len(checks),
                "healthy": len([r for r in checks.values() if r.get("status") == "healthy"]),
                "error": len([r for r in checks.values() if r.get("status") == "error"]),
                "skipped": len([r for r in checks.values() if r.get("status") == "skipped"])
            }
        }


async def main():
    """Main health check function."""
    checker = HealthChecker()
    
    try:
        results = await checker.run_comprehensive_check()
        
        # Output results
        print(json.dumps(results, indent=2))
        
        # Exit with appropriate code
        if results["overall_status"] == "healthy":
            sys.exit(0)
        elif results["overall_status"] == "degraded":
            sys.exit(1)  # Warning state
        else:
            sys.exit(2)  # Critical failure
    
    except Exception as e:
        error_result = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": "error",
            "error": str(e)
        }
        print(json.dumps(error_result, indent=2))
        sys.exit(3)


if __name__ == "__main__":
    # Simple health check for Docker
    if len(sys.argv) > 1 and sys.argv[1] == "--simple":
        # Quick API check only
        import requests
        try:
            response = requests.get("http://localhost:8000/health", timeout=5)
            if response.status_code == 200:
                print("OK")
                sys.exit(0)
            else:
                print(f"ERROR: {response.status_code}")
                sys.exit(1)
        except Exception as e:
            print(f"ERROR: {e}")
            sys.exit(1)
    else:
        # Comprehensive check
        asyncio.run(main())