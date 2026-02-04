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
            self.deployment_status['warnings'].append("Journal intelligence features unavailable")
    
    async def _deploy_monitoring(self, config: Dict[str, Any]):
        """Deploy monitoring system."""
        logger.info("Deploying monitoring system...")
        
        try:
            monitor = await get_system_monitor()
            health_status = await monitor.comprehensive_health_check()
            
            self.deployment_status['components']['monitoring'] = {
                'status': 'deployed',
                'health_status': health_status['overall_status'],
                'features': ['health_checks', 'performance_tracking', 'alerting']
            }
            
            logger.info("✅ Monitoring system deployed successfully")
            
        except Exception as e:
            logger.warning(f"⚠️ Monitoring deployment failed (non-critical): {e}")
            self.deployment_status['components']['monitoring'] = {
                'status': 'failed',
                'error': str(e)
            }
            self.deployment_status['warnings'].append("System monitoring unavailable")
    
    async def _validate_deployment(self) -> Dict[str, Any]:
        """Validate complete system deployment."""
        logger.info("Validating system deployment...")
        
        validation_results = {
            'overall_status': 'unknown',
            'critical_components': [],
            'optional_components': [],
            'integration_tests': []
        }
        
        try:
            # Test critical components
            critical_tests = [
                ('cache_system', self._test_cache_integration),
                ('api_management', self._test_api_integration),
                ('reference_service', self._test_reference_service_integration)
            ]
            
            for component_name, test_func in critical_tests:
                try:
                    test_result = await test_func()
                    validation_results['critical_components'].append({
                        'component': component_name,
                        'status': 'passed',
                        'result': test_result
                    })
                except Exception as e:
                    validation_results['critical_components'].append({
                        'component': component_name,
                        'status': 'failed',
                        'error': str(e)
                    })
            
            # Test optional components
            optional_tests = [
                ('ai_matching', self._test_ai_matching_integration),
                ('collaboration', self._test_collaboration_integration),
                ('journal_intelligence', self._test_journal_intelligence_integration),
                ('monitoring', self._test_monitoring_integration)
            ]
            
            for component_name, test_func in optional_tests:
                try:
                    test_result = await test_func()
                    validation_results['optional_components'].append({
                        'component': component_name,
                        'status': 'passed',
                        'result': test_result
                    })
                except Exception as e:
                    validation_results['optional_components'].append({
                        'component': component_name,
                        'status': 'failed',
                        'error': str(e)
                    })
            
            # Integration tests
            integration_test_result = await self._test_end_to_end_integration()
            validation_results['integration_tests'].append({
                'test': 'end_to_end_reference_processing',
                'status': 'passed' if integration_test_result['success'] else 'failed',
                'result': integration_test_result
            })
            
            # Determine overall status
            critical_failures = [c for c in validation_results['critical_components'] if c['status'] == 'failed']
            if critical_failures:
                validation_results['overall_status'] = 'failed'
            else:
                validation_results['overall_status'] = 'passed'
            
            logger.info(f"✅ Deployment validation completed: {validation_results['overall_status']}")
            
        except Exception as e:
            logger.error(f"❌ Deployment validation failed: {e}")
            validation_results['overall_status'] = 'error'
            validation_results['validation_error'] = str(e)
        
        return validation_results
    
    async def _test_cache_integration(self) -> Dict[str, Any]:
        """Test cache system integration."""
        cache = await get_cache()
        
        # Test read/write operations
        test_key = f"integration_test_{int(datetime.utcnow().timestamp())}"
        test_data = {'test': True, 'timestamp': datetime.utcnow().isoformat()}
        
        await cache.set('api_responses', test_key, test_data, ttl_override=60)
        retrieved_data = await cache.get('api_responses', test_key)
        
        if retrieved_data != test_data:
            raise Exception("Cache read/write test failed")
        
        await cache.delete('api_responses', test_key)
        
        stats = await cache.get_stats()
        
        return {
            'read_write_test': 'passed',
            'stats': stats
        }
    
    async def _test_api_integration(self) -> Dict[str, Any]:
        """Test API management integration."""
        api_manager = await get_api_manager()
        stats = await api_manager.get_stats()
        
        return {
            'api_manager_ready': True,
            'stats': stats
        }
    
    async def _test_reference_service_integration(self) -> Dict[str, Any]:
        """Test reference service integration."""
        ref_service = await get_reference_service()
        stats = await ref_service.get_stats()
        
        return {
            'service_ready': True,
            'stats': stats
        }
    
    async def _test_ai_matching_integration(self) -> Dict[str, Any]:
        """Test AI matching integration."""
        try:
            ai_matcher = await get_ai_matcher()
            return {
                'ai_matching_ready': True,
                'fallback_available': True
            }
        except Exception as e:
            raise Exception(f"AI matching test failed: {e}")
    
    async def _test_collaboration_integration(self) -> Dict[str, Any]:
        """Test collaboration features integration."""
        try:
            collab_manager = await get_collaborative_manager()
            return {
                'collaboration_ready': True
            }
        except Exception as e:
            raise Exception(f"Collaboration test failed: {e}")
    
    async def _test_journal_intelligence_integration(self) -> Dict[str, Any]:
        """Test journal intelligence integration."""
        try:
            journal_intel = await get_journal_intelligence()
            stats = await journal_intel.get_stats()
            return {
                'journal_intelligence_ready': True,
                'stats': stats
            }
        except Exception as e:
            raise Exception(f"Journal intelligence test failed: {e}")
    
    async def _test_monitoring_integration(self) -> Dict[str, Any]:
        """Test monitoring system integration."""
        try:
            monitor = await get_system_monitor()
            status = await monitor.get_system_status_summary()
            return {
                'monitoring_ready': True,
                'system_status': status
            }
        except Exception as e:
            raise Exception(f"Monitoring test failed: {e}")
    
    async def _test_end_to_end_integration(self) -> Dict[str, Any]:
        """Test complete end-to-end reference processing."""
        try:
            from .reference_types import ReferenceState, CitationStyle, Reference
            
            # Create test reference state
            test_state = ReferenceState(
                study_id="deployment_test",
                manuscript_text="This is a test manuscript with citations needed.",
                literature_results=[
                    {
                        'id': 'test_ref_1',
                        'title': 'Test Reference Article',
                        'authors': ['Test Author'],
                        'year': 2024,
                        'journal': 'Test Journal'
                    }
                ],
                target_style=CitationStyle.AMA,
                enable_doi_validation=False,  # Skip external API calls in test
                enable_duplicate_detection=True,
                enable_quality_assessment=True
            )
            
            # Process references
            ref_service = await get_reference_service()
            result = await ref_service.process_references(test_state)
            
            return {
                'success': True,
                'references_processed': result.total_references,
                'citations_generated': len(result.citations),
                'processing_time_seconds': result.processing_time_seconds,
                'style_compliance_score': result.style_compliance_score
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    async def cleanup_deployment(self) -> Dict[str, Any]:
        """Clean up deployment resources."""
        logger.info("Cleaning up deployment resources...")
        
        cleanup_results = {
            'components_cleaned': [],
            'cleanup_errors': []
        }
        
        cleanup_functions = [
            ('reference_service', close_reference_service),
            ('cache', close_cache),
            ('api_manager', close_api_manager),
            ('ai_matcher', close_ai_matcher),
            ('collaborative_manager', close_collaborative_manager),
            ('journal_intelligence', close_journal_intelligence),
            ('system_monitor', close_system_monitor)
        ]
        
        for component_name, cleanup_func in cleanup_functions:
            try:
                await cleanup_func()
                cleanup_results['components_cleaned'].append(component_name)
                logger.info(f"✅ Cleaned up {component_name}")
            except Exception as e:
                cleanup_results['cleanup_errors'].append({
                    'component': component_name,
                    'error': str(e)
                })
                logger.warning(f"⚠️ Cleanup failed for {component_name}: {e}")
        
        return cleanup_results


# Deployment utilities
async def deploy_enhanced_reference_system(config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Deploy the enhanced reference management system."""
    deployment = EnhancedReferenceSystemDeployment()
    return await deployment.deploy_system(config)


async def validate_system_deployment() -> Dict[str, Any]:
    """Validate that the system is properly deployed."""
    deployment = EnhancedReferenceSystemDeployment()
    return await deployment._validate_deployment()


async def cleanup_system_deployment() -> Dict[str, Any]:
    """Clean up deployment resources."""
    deployment = EnhancedReferenceSystemDeployment()
    return await deployment.cleanup_deployment()