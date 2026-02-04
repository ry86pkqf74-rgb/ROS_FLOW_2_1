"""
Production Health Check for Enhanced Reference Management System

Comprehensive health checks for all system components including AI engines.

Linear Issues: ROS-XXX
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import traceback

# Import all system components
from .integration_hub import get_integration_hub
from .reference_management_service import get_reference_service
from .journal_intelligence import get_journal_intelligence
from .monitoring import get_system_monitor

logger = logging.getLogger(__name__)

class ProductionHealthChecker:
    """Comprehensive health checker for production systems."""
    
    def __init__(self):
        self.health_results = {}
    
    async def check_core_services(self) -> Dict[str, Any]:
        """Check core reference management services."""
        core_health = {}
        
        # Reference Management Service
        try:
            ref_service = await get_reference_service()
            stats = await ref_service.get_stats()
            core_health["reference_service"] = {
                "status": "healthy",
                "stats": stats,
                "last_check": datetime.utcnow().isoformat()
            }
        except Exception as e:
            core_health["reference_service"] = {
                "status": "unhealthy",
                "error": str(e),
                "last_check": datetime.utcnow().isoformat()
            }
        
        # Journal Intelligence
        try:
            journal_intel = await get_journal_intelligence()
            stats = await journal_intel.get_stats()
            core_health["journal_intelligence"] = {
                "status": "healthy", 
                "stats": stats,
                "last_check": datetime.utcnow().isoformat()
            }
        except Exception as e:
            core_health["journal_intelligence"] = {
                "status": "unhealthy",
                "error": str(e),
                "last_check": datetime.utcnow().isoformat()
            }
        
        # System Monitor
        try:
            monitor = await get_system_monitor()
            status = await monitor.get_system_status_summary()
            core_health["system_monitor"] = {
                "status": "healthy",
                "system_status": status,
                "last_check": datetime.utcnow().isoformat()
            }
        except Exception as e:
            core_health["system_monitor"] = {
                "status": "unhealthy", 
                "error": str(e),
                "last_check": datetime.utcnow().isoformat()
            }
        
        return core_health
    
    async def check_ai_engines(self) -> Dict[str, Any]:
        """Check AI engine health through Integration Hub."""
        ai_health = {}
        
        try:
            # Integration Hub main check
            integration_hub = await get_integration_hub()
            ai_health["integration_hub"] = {
                "status": "healthy",
                "last_check": datetime.utcnow().isoformat()
            }
            
            # Get detailed stats for each engine
            try:
                hub_stats = await integration_hub.get_integration_stats()
                ai_health["engine_stats"] = hub_stats
                
                # Analyze individual engine health
                engine_health = {}
                for engine_name, engine_stats in hub_stats.items():
                    if isinstance(engine_stats, dict):
                        if "error" in engine_stats:
                            engine_health[engine_name] = {
                                "status": "unhealthy",
                                "error": engine_stats["error"]
                            }
                        else:
                            engine_health[engine_name] = {
                                "status": "healthy",
                                "stats_available": True
                            }
                    else:
                        engine_health[engine_name] = {
                            "status": "unknown",
                            "note": "Stats format unexpected"
                        }
                
                ai_health["individual_engines"] = engine_health
                
            except Exception as stats_error:
                ai_health["stats_error"] = str(stats_error)
        
        except Exception as e:
            ai_health["integration_hub"] = {
                "status": "unhealthy",
                "error": str(e),
                "traceback": traceback.format_exc()[-500:],  # Last 500 chars of traceback
                "last_check": datetime.utcnow().isoformat()
            }
        
        return ai_health
    
    async def test_basic_functionality(self) -> Dict[str, Any]:
        """Test basic functionality with minimal data."""
        functionality_tests = {}
        
        # Test basic reference processing
        try:
            ref_service = await get_reference_service()
            
            # Create minimal test data
            from .reference_types import ReferenceState, CitationStyle, Reference
            
            test_state = ReferenceState(
                study_id="health_check_test",
                manuscript_text="This is a test manuscript [citation needed].",
                literature_results=[],
                existing_references=[
                    Reference(
                        id="test_ref_1",
                        title="Test Reference",
                        authors=["Test Author"],
                        year=2023,
                        journal="Test Journal"
                    )
                ],
                target_style=CitationStyle.AMA,
                enable_doi_validation=False,
                enable_duplicate_detection=False,
                enable_quality_assessment=False
            )
            
            # Quick processing test
            result = await ref_service.process_references(test_state)
            
            functionality_tests["basic_processing"] = {
                "status": "working",
                "references_processed": len(result.references),
                "citations_generated": len(result.citations),
                "processing_time": result.processing_time_seconds
            }
            
        except Exception as e:
            functionality_tests["basic_processing"] = {
                "status": "failed",
                "error": str(e)
            }
        
        # Test AI Integration Hub (if available)
        try:
            integration_hub = await get_integration_hub()
            
            # Test with minimal request
            test_reference = Reference(
                id="test_ai_ref",
                title="AI Test Reference",
                authors=["AI Test"],
                year=2023
            )
            
            insights = await integration_hub.get_reference_insights(
                test_reference,
                context="This is a test context.",
                research_field="general"
            )
            
            functionality_tests["ai_integration"] = {
                "status": "working",
                "insights_generated": bool(insights),
                "insights_keys": list(insights.keys()) if insights else []
            }
            
        except Exception as e:
            functionality_tests["ai_integration"] = {
                "status": "failed",
                "error": str(e)
            }
        
        return functionality_tests
    
    async def comprehensive_health_check(self) -> Dict[str, Any]:
        """Run comprehensive health check."""
        start_time = datetime.utcnow()
        
        health_report = {
            "timestamp": start_time.isoformat(),
            "overall_status": "unknown",
            "checks_performed": []
        }
        
        # Check core services
        print("Checking core services...")
        core_health = await self.check_core_services()
        health_report["core_services"] = core_health
        health_report["checks_performed"].append("core_services")
        
        # Check AI engines
        print("Checking AI engines...")
        ai_health = await self.check_ai_engines()
        health_report["ai_engines"] = ai_health
        health_report["checks_performed"].append("ai_engines")
        
        # Test functionality
        print("Testing basic functionality...")
        functionality_tests = await self.test_basic_functionality()
        health_report["functionality_tests"] = functionality_tests
        health_report["checks_performed"].append("functionality_tests")
        
        # Determine overall status
        health_report["overall_status"] = self._determine_overall_status(
            core_health, ai_health, functionality_tests
        )
        
        # Add timing
        end_time = datetime.utcnow()
        health_report["check_duration_seconds"] = (end_time - start_time).total_seconds()
        health_report["completed_at"] = end_time.isoformat()
        
        return health_report
    
    def _determine_overall_status(
        self, 
        core_health: Dict[str, Any],
        ai_health: Dict[str, Any],
        functionality_tests: Dict[str, Any]
    ) -> str:
        """Determine overall system status."""
        
        # Check core services
        core_healthy = all(
            service.get("status") == "healthy" 
            for service in core_health.values()
        )
        
        # Check basic functionality
        basic_working = functionality_tests.get("basic_processing", {}).get("status") == "working"
        
        # AI is considered optional for basic operation
        ai_working = ai_health.get("integration_hub", {}).get("status") == "healthy"
        
        if core_healthy and basic_working and ai_working:
            return "fully_operational"
        elif core_healthy and basic_working:
            return "operational_basic"  # Core works, AI may be degraded
        elif basic_working:
            return "minimal_operational"  # Basic function only
        else:
            return "degraded"
    
    async def quick_health_check(self) -> Dict[str, Any]:
        """Quick health check for load balancer/monitoring."""
        try:
            # Test reference service only
            ref_service = await get_reference_service()
            stats = await ref_service.get_stats()
            
            return {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "basic_stats": {
                    "processings_performed": stats.get("processings_performed", 0)
                }
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

# Global health checker instance
_health_checker_instance: Optional[ProductionHealthChecker] = None

async def get_health_checker() -> ProductionHealthChecker:
    """Get global health checker instance."""
    global _health_checker_instance
    if _health_checker_instance is None:
        _health_checker_instance = ProductionHealthChecker()
    return _health_checker_instance

# Direct execution for manual health checks
async def run_manual_health_check():
    """Run manual health check from command line."""
    print("\\n" + "="*60)
    print("🏥 PRODUCTION HEALTH CHECK")
    print("="*60)
    
    checker = await get_health_checker()
    health_report = await checker.comprehensive_health_check()
    
    print(f"\\n📊 Health Check Results:")
    print(f"   Overall Status: {health_report['overall_status'].upper()}")
    print(f"   Check Duration: {health_report['check_duration_seconds']:.2f}s")
    print(f"   Timestamp: {health_report['timestamp']}")
    
    # Core Services
    print(f"\\n🔧 Core Services:")
    for service, status in health_report['core_services'].items():
        status_icon = "✅" if status['status'] == 'healthy' else "❌"
        print(f"   {status_icon} {service}: {status['status']}")
        if status['status'] != 'healthy':
            print(f"      Error: {status.get('error', 'Unknown')}")
    
    # AI Engines
    print(f"\\n🤖 AI Engines:")
    ai_health = health_report['ai_engines']
    hub_status = ai_health.get('integration_hub', {}).get('status', 'unknown')
    hub_icon = "✅" if hub_status == 'healthy' else "❌"
    print(f"   {hub_icon} Integration Hub: {hub_status}")
    
    if hub_status != 'healthy':
        error = ai_health.get('integration_hub', {}).get('error', 'Unknown')
        print(f"      Error: {error[:100]}...")
    
    if 'individual_engines' in ai_health:
        for engine, status in ai_health['individual_engines'].items():
            engine_icon = "✅" if status['status'] == 'healthy' else "❌"
            print(f"   {engine_icon} {engine}: {status['status']}")
    
    # Functionality Tests
    print(f"\\n🧪 Functionality Tests:")
    for test, result in health_report['functionality_tests'].items():
        test_icon = "✅" if result['status'] == 'working' else "❌"
        print(f"   {test_icon} {test}: {result['status']}")
        if result['status'] != 'working':
            print(f"      Error: {result.get('error', 'Unknown')}")
    
    print(f"\\n" + "="*60)
    
    return health_report

if __name__ == "__main__":
    asyncio.run(run_manual_health_check())