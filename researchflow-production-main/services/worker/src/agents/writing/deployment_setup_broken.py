"""
Enhanced Reference Management System Deployment Setup

Automated deployment and configuration for production reference management system.

Linear Issues: ROS-XXX
"""

import asyncio
import logging
import os
from typing import Dict, List, Optional, Any
from datetime import datetime
import json

from .reference_management_service import get_reference_service, close_reference_service
from .reference_cache import get_cache, close_cache
from .api_management import get_api_manager, close_api_manager
from .ai_enhanced_matching import get_ai_matcher, close_ai_matcher
from .collaborative_references import get_collaborative_manager, close_collaborative_manager
from .journal_intelligence import get_journal_intelligence, close_journal_intelligence
from .monitoring import get_system_monitor, close_system_monitor

logger = logging.getLogger(__name__)

class EnhancedReferenceSystemDeployment:
    """Handles deployment and configuration of enhanced reference system."""
    
    def __init__(self):
        self.deployment_status = {
            'started_at': None,
            'completed_at': None,
            'status': 'not_started',
            'components': {},
            'errors': [],
            'warnings': []
        }
    
    async def deploy_system(self, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Deploy the complete enhanced reference management system.
        
        Args:
            config: Optional deployment configuration
            
        Returns:
            Deployment status and results
        """
        logger.info("Starting enhanced reference management system deployment")
        self.deployment_status['started_at'] = datetime.utcnow().isoformat()
        self.deployment_status['status'] = 'deploying'
        
        # Default configuration
        default_config = {
            'redis_url': os.getenv('REDIS_URL', 'redis://localhost:6379'),
            'enable_ai_matching': True,
            'enable_monitoring': True,
            'enable_collaboration': True,
            'enable_journal_intelligence': True,
            'cache_ttl_hours': 24,
            'api_rate_limits': {
                'pubmed': {'requests_per_second': 10, 'burst_capacity': 50},
                'crossref': {'requests_per_second': 50, 'burst_capacity': 200},
                'semantic_scholar': {'requests_per_second': 100, 'burst_capacity': 500}
            }
        }
        
        # Merge with provided config
        deployment_config = {**default_config, **(config or {})}
        
        try:
            # 1. Deploy Redis Cache System
            await self._deploy_cache_system(deployment_config)
            
            # 2. Deploy API Management
            await self._deploy_api_management(deployment_config)
            
            # 3. Deploy Core Reference Service
            await self._deploy_reference_service(deployment_config)
            
            # 4. Deploy AI-Enhanced Matching (if enabled)
            if deployment_config['enable_ai_matching']:
                await self._deploy_ai_matching(deployment_config)
            
            # 5. Deploy Collaborative Features (if enabled)
            if deployment_config['enable_collaboration']:
                await self._deploy_collaboration(deployment_config)
            
            # 6. Deploy Journal Intelligence (if enabled) 
            if deployment_config['enable_journal_intelligence']:
                await self._deploy_journal_intelligence(deployment_config)
            
            # 7. Deploy Monitoring System (if enabled)
            if deployment_config['enable_monitoring']:
                await self._deploy_monitoring(deployment_config)
            
            # 8. Validate Deployment
            validation_results = await self._validate_deployment()
            
            self.deployment_status['status'] = 'completed'
            self.deployment_status['completed_at'] = datetime.utcnow().isoformat()
            
            logger.info("Enhanced reference management system deployment completed successfully")
            
            return {
                'success': True,
                'deployment_status': self.deployment_status,
                'validation_results': validation_results,
                'config_used': deployment_config
            }
            
        except Exception as e:
            logger.error(f"Deployment failed: {e}", exc_info=True)
            self.deployment_status['status'] = 'failed'
            self.deployment_status['errors'].append(str(e))
            
            return {
                'success': False,
                'deployment_status': self.deployment_status,
                'error': str(e)
            }
    
    async def _deploy_cache_system(self, config: Dict[str, Any]):
        """Deploy Redis cache system."""
        logger.info("Deploying cache system...")
        
        try:
            cache = await get_cache()
            
            # Test cache operations
            test_key = f"deployment_test_{int(datetime.utcnow().timestamp())}"
            await cache.set('api_responses', test_key, {'deployment': 'test'}, ttl_override=60)
            test_result = await cache.get('api_responses', test_key)
            
            if test_result is None:
                raise Exception("Cache read/write test failed")
            
            await cache.delete('api_responses', test_key)
            
            self.deployment_status['components']['cache_system'] = {
                'status': 'deployed',
                'redis_url': config['redis_url'],
                'test_passed': True
            }
            
            logger.info("✅ Cache system deployed successfully")
            
        except Exception as e:
            logger.error(f"❌ Cache system deployment failed: {e}")
            self.deployment_status['components']['cache_system'] = {
                'status': 'failed',
                'error': str(e)
            }
            raise
    
    async def _deploy_api_management(self, config: Dict[str, Any]):
        """Deploy API management system."""
        logger.info("Deploying API management system...")
        
        try:
            api_manager = await get_api_manager()
            stats = await api_manager.get_stats()
            
            self.deployment_status['components']['api_management'] = {
                'status': 'deployed',
                'rate_limits': config['api_rate_limits'],
                'stats': stats
            }
            
            logger.info("✅ API management system deployed successfully")
            
        except Exception as e:
            logger.error(f"❌ API management deployment failed: {e}")
            self.deployment_status['components']['api_management'] = {
                'status': 'failed',
                'error': str(e)
            }
            raise
    
    async def _deploy_reference_service(self, config: Dict[str, Any]):
        """Deploy core reference management service."""
        logger.info("Deploying reference management service...")
        
        try:
            ref_service = await get_reference_service()
            stats = await ref_service.get_stats()
            
            self.deployment_status['components']['reference_service'] = {
                'status': 'deployed',
                'stats': stats
            }
            
            logger.info("✅ Reference management service deployed successfully")
            
        except Exception as e:
            logger.error(f"❌ Reference service deployment failed: {e}")
            self.deployment_status['components']['reference_service'] = {
                'status': 'failed',
                'error': str(e)
            }
            raise
    
    async def _deploy_ai_matching(self, config: Dict[str, Any]):
        """Deploy AI-enhanced matching system."""
        logger.info("Deploying AI-enhanced matching...")
        
        try:
            ai_matcher = await get_ai_matcher()
            
            self.deployment_status['components']['ai_matching'] = {
                'status': 'deployed',
                'features': ['semantic_similarity', 'fallback_text_matching']
            }
            
            logger.info("✅ AI-enhanced matching deployed successfully")
            
        except Exception as e:
            logger.warning(f"⚠️ AI matching deployment failed (non-critical): {e}")
            self.deployment_status['components']['ai_matching'] = {
                'status': 'failed',
                'error': str(e),
                'fallback_available': True
            }
            self.deployment_status['warnings'].append("AI matching failed, using fallback text matching")
    
    async def _deploy_collaboration(self, config: Dict[str, Any]):
        """Deploy collaborative reference management."""
        logger.info("Deploying collaborative features...")
        
        try:
            collab_manager = await get_collaborative_manager()
            
            self.deployment_status['components']['collaboration'] = {
                'status': 'deployed',
                'features': ['real_time_editing', 'conflict_resolution', 'edit_history']
            }
            
            logger.info("✅ Collaborative features deployed successfully")
            
        except Exception as e:
            logger.warning(f"⚠️ Collaboration deployment failed (non-critical): {e}")
            self.deployment_status['components']['collaboration'] = {
                'status': 'failed',
                'error': str(e)
            }
            self.deployment_status['warnings'].append("Collaborative features unavailable")
    
    async def _deploy_journal_intelligence(self, config: Dict[str, Any]):
        """Deploy journal intelligence system."""
        logger.info("Deploying journal intelligence...")
        
        try:
            journal_intel = await get_journal_intelligence()
            
            self.deployment_status['components']['journal_intelligence'] = {
                'status': 'deployed',
                'features': ['journal_recommendations', 'impact_analysis', 'compatibility_scoring']
            }
            
            logger.info("✅ Journal intelligence deployed successfully")
            
        except Exception as e:
            logger.warning(f"⚠️ Journal intelligence deployment failed (non-critical): {e}")
            self.deployment_status['components']['journal_intelligence'] = {
                'status': 'failed',
                'error': str(e)
            }
            self.deployment_status['warnings'].append("Journal intelligence features unavailable")\n    \n    async def _deploy_monitoring(self, config: Dict[str, Any]):\n        \"\"\"Deploy monitoring system.\"\"\"\n        logger.info(\"Deploying monitoring system...\")\n        \n        try:\n            monitor = await get_system_monitor()\n            health_status = await monitor.comprehensive_health_check()\n            \n            self.deployment_status['components']['monitoring'] = {\n                'status': 'deployed',\n                'health_status': health_status['overall_status'],\n                'features': ['health_checks', 'performance_tracking', 'alerting']\n            }\n            \n            logger.info(\"✅ Monitoring system deployed successfully\")\n            \n        except Exception as e:\n            logger.warning(f\"⚠️ Monitoring deployment failed (non-critical): {e}\")\n            self.deployment_status['components']['monitoring'] = {\n                'status': 'failed',\n                'error': str(e)\n            }\n            self.deployment_status['warnings'].append(\"System monitoring unavailable\")\n    \n    async def _validate_deployment(self) -> Dict[str, Any]:\n        \"\"\"Validate complete system deployment.\"\"\"\n        logger.info(\"Validating system deployment...\")\n        \n        validation_results = {\n            'overall_status': 'unknown',\n            'critical_components': [],\n            'optional_components': [],\n            'integration_tests': []\n        }\n        \n        try:\n            # Test critical components\n            critical_tests = [\n                ('cache_system', self._test_cache_integration),\n                ('api_management', self._test_api_integration),\n                ('reference_service', self._test_reference_service_integration)\n            ]\n            \n            for component_name, test_func in critical_tests:\n                try:\n                    test_result = await test_func()\n                    validation_results['critical_components'].append({\n                        'component': component_name,\n                        'status': 'passed',\n                        'result': test_result\n                    })\n                except Exception as e:\n                    validation_results['critical_components'].append({\n                        'component': component_name,\n                        'status': 'failed',\n                        'error': str(e)\n                    })\n            \n            # Test optional components\n            optional_tests = [\n                ('ai_matching', self._test_ai_matching_integration),\n                ('collaboration', self._test_collaboration_integration),\n                ('journal_intelligence', self._test_journal_intelligence_integration),\n                ('monitoring', self._test_monitoring_integration)\n            ]\n            \n            for component_name, test_func in optional_tests:\n                try:\n                    test_result = await test_func()\n                    validation_results['optional_components'].append({\n                        'component': component_name,\n                        'status': 'passed',\n                        'result': test_result\n                    })\n                except Exception as e:\n                    validation_results['optional_components'].append({\n                        'component': component_name,\n                        'status': 'failed',\n                        'error': str(e)\n                    })\n            \n            # Integration tests\n            integration_test_result = await self._test_end_to_end_integration()\n            validation_results['integration_tests'].append({\n                'test': 'end_to_end_reference_processing',\n                'status': 'passed' if integration_test_result['success'] else 'failed',\n                'result': integration_test_result\n            })\n            \n            # Determine overall status\n            critical_failures = [c for c in validation_results['critical_components'] if c['status'] == 'failed']\n            if critical_failures:\n                validation_results['overall_status'] = 'failed'\n            else:\n                validation_results['overall_status'] = 'passed'\n            \n            logger.info(f\"✅ Deployment validation completed: {validation_results['overall_status']}\")\n            \n        except Exception as e:\n            logger.error(f\"❌ Deployment validation failed: {e}\")\n            validation_results['overall_status'] = 'error'\n            validation_results['validation_error'] = str(e)\n        \n        return validation_results\n    \n    async def _test_cache_integration(self) -> Dict[str, Any]:\n        \"\"\"Test cache system integration.\"\"\"\n        cache = await get_cache()\n        \n        # Test read/write operations\n        test_key = f\"integration_test_{int(datetime.utcnow().timestamp())}\"\n        test_data = {'test': True, 'timestamp': datetime.utcnow().isoformat()}\n        \n        await cache.set('api_responses', test_key, test_data, ttl_override=60)\n        retrieved_data = await cache.get('api_responses', test_key)\n        \n        if retrieved_data != test_data:\n            raise Exception(\"Cache read/write test failed\")\n        \n        await cache.delete('api_responses', test_key)\n        \n        stats = await cache.get_stats()\n        \n        return {\n            'read_write_test': 'passed',\n            'stats': stats\n        }\n    \n    async def _test_api_integration(self) -> Dict[str, Any]:\n        \"\"\"Test API management integration.\"\"\"\n        api_manager = await get_api_manager()\n        stats = await api_manager.get_stats()\n        \n        return {\n            'api_manager_ready': True,\n            'stats': stats\n        }\n    \n    async def _test_reference_service_integration(self) -> Dict[str, Any]:\n        \"\"\"Test reference service integration.\"\"\"\n        ref_service = await get_reference_service()\n        stats = await ref_service.get_stats()\n        \n        return {\n            'service_ready': True,\n            'stats': stats\n        }\n    \n    async def _test_ai_matching_integration(self) -> Dict[str, Any]:\n        \"\"\"Test AI matching integration.\"\"\"\n        try:\n            ai_matcher = await get_ai_matcher()\n            return {\n                'ai_matching_ready': True,\n                'fallback_available': True\n            }\n        except Exception as e:\n            raise Exception(f\"AI matching test failed: {e}\")\n    \n    async def _test_collaboration_integration(self) -> Dict[str, Any]:\n        \"\"\"Test collaboration features integration.\"\"\"\n        try:\n            collab_manager = await get_collaborative_manager()\n            return {\n                'collaboration_ready': True\n            }\n        except Exception as e:\n            raise Exception(f\"Collaboration test failed: {e}\")\n    \n    async def _test_journal_intelligence_integration(self) -> Dict[str, Any]:\n        \"\"\"Test journal intelligence integration.\"\"\"\n        try:\n            journal_intel = await get_journal_intelligence()\n            stats = await journal_intel.get_stats()\n            return {\n                'journal_intelligence_ready': True,\n                'stats': stats\n            }\n        except Exception as e:\n            raise Exception(f\"Journal intelligence test failed: {e}\")\n    \n    async def _test_monitoring_integration(self) -> Dict[str, Any]:\n        \"\"\"Test monitoring system integration.\"\"\"\n        try:\n            monitor = await get_system_monitor()\n            status = await monitor.get_system_status_summary()\n            return {\n                'monitoring_ready': True,\n                'system_status': status\n            }\n        except Exception as e:\n            raise Exception(f\"Monitoring test failed: {e}\")\n    \n    async def _test_end_to_end_integration(self) -> Dict[str, Any]:\n        \"\"\"Test complete end-to-end reference processing.\"\"\"\n        try:\n            from .reference_types import ReferenceState, CitationStyle, Reference\n            \n            # Create test reference state\n            test_state = ReferenceState(\n                study_id=\"deployment_test\",\n                manuscript_text=\"This is a test manuscript with citations needed.\",\n                literature_results=[\n                    {\n                        'id': 'test_ref_1',\n                        'title': 'Test Reference Article',\n                        'authors': ['Test Author'],\n                        'year': 2024,\n                        'journal': 'Test Journal'\n                    }\n                ],\n                target_style=CitationStyle.AMA,\n                enable_doi_validation=False,  # Skip external API calls in test\n                enable_duplicate_detection=True,\n                enable_quality_assessment=True\n            )\n            \n            # Process references\n            ref_service = await get_reference_service()\n            result = await ref_service.process_references(test_state)\n            \n            return {\n                'success': True,\n                'references_processed': result.total_references,\n                'citations_generated': len(result.citations),\n                'processing_time_seconds': result.processing_time_seconds,\n                'style_compliance_score': result.style_compliance_score\n            }\n            \n        except Exception as e:\n            return {\n                'success': False,\n                'error': str(e)\n            }\n    \n    async def cleanup_deployment(self) -> Dict[str, Any]:\n        \"\"\"Clean up deployment resources.\"\"\"\n        logger.info(\"Cleaning up deployment resources...\")\n        \n        cleanup_results = {\n            'components_cleaned': [],\n            'cleanup_errors': []\n        }\n        \n        cleanup_functions = [\n            ('reference_service', close_reference_service),\n            ('cache', close_cache),\n            ('api_manager', close_api_manager),\n            ('ai_matcher', close_ai_matcher),\n            ('collaborative_manager', close_collaborative_manager),\n            ('journal_intelligence', close_journal_intelligence),\n            ('system_monitor', close_system_monitor)\n        ]\n        \n        for component_name, cleanup_func in cleanup_functions:\n            try:\n                await cleanup_func()\n                cleanup_results['components_cleaned'].append(component_name)\n                logger.info(f\"✅ Cleaned up {component_name}\")\n            except Exception as e:\n                cleanup_results['cleanup_errors'].append({\n                    'component': component_name,\n                    'error': str(e)\n                })\n                logger.warning(f\"⚠️ Cleanup failed for {component_name}: {e}\")\n        \n        return cleanup_results\n\n\n# Deployment utilities\nasync def deploy_enhanced_reference_system(config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:\n    \"\"\"Deploy the enhanced reference management system.\"\"\"\n    deployment = EnhancedReferenceSystemDeployment()\n    return await deployment.deploy_system(config)\n\n\nasync def validate_system_deployment() -> Dict[str, Any]:\n    \"\"\"Validate that the system is properly deployed.\"\"\"\n    deployment = EnhancedReferenceSystemDeployment()\n    return await deployment._validate_deployment()\n\n\nasync def cleanup_system_deployment() -> Dict[str, Any]:\n    \"\"\"Clean up deployment resources.\"\"\"\n    deployment = EnhancedReferenceSystemDeployment()\n    return await deployment.cleanup_deployment()