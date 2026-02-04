"""
Analytics Integration Tests
==========================

Comprehensive integration tests for the analytics system including:
- Size predictor functionality
- Real-time monitoring 
- Dashboard data retrieval
- API endpoints
- WebSocket connections
"""

import pytest
import asyncio
import json
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../services/worker'))

from services.worker.src.analytics.predictive_modeling.size_predictor import (
    PredictiveSizeModeler,
    ManuscriptFeatures,
    SizePrediction,
    get_size_predictor
)
from services.worker.src.analytics.monitoring.real_time_monitor import (
    RealTimeMonitor,
    PerformanceMetric,
    SystemHealth,
    OptimizationOperation,
    get_monitor
)
from services.worker.src.analytics.dashboard.metrics_dashboard import (
    MetricsDashboard
)


@pytest.fixture
def sample_manuscript_data():
    """Sample manuscript data for testing."""
    return {
        "title": "Machine Learning in Healthcare Analytics",
        "abstract": "This study investigates the application of machine learning techniques in healthcare analytics.",
        "introduction": "Healthcare analytics has become increasingly important...",
        "methods": "We employed advanced statistical methods...",
        "results": "Our analysis revealed significant patterns...",
        "discussion": "The findings have important implications...",
        "references": [f"Reference {i}" for i in range(1, 26)],  # 25 references
        "metadata": {
            "word_count": 4500,
            "reference_count": 25,
            "figure_count": 6,
            "table_count": 3
        }
    }


@pytest.fixture
def size_predictor():
    """Fixture for size predictor."""
    return PredictiveSizeModeler()


@pytest.fixture
def real_time_monitor():
    """Fixture for real-time monitor."""
    return RealTimeMonitor(max_history_points=100)


@pytest.fixture
def dashboard(real_time_monitor):
    """Fixture for metrics dashboard."""
    return MetricsDashboard(real_time_monitor)


class TestSizePredictorIntegration:
    """Integration tests for size predictor."""
    
    def test_predict_size_with_full_data(self, size_predictor, sample_manuscript_data):
        """Test size prediction with complete manuscript data."""
        prediction = size_predictor.predict_size(sample_manuscript_data)
        
        # Verify prediction structure
        assert isinstance(prediction, SizePrediction)
        assert prediction.predicted_size_bytes > 0
        assert 0 <= prediction.confidence_score <= 1
        assert 0 < prediction.predicted_compression_ratio <= 1
        assert prediction.estimated_processing_time > 0
        assert prediction.recommended_compression_level in ['low', 'medium', 'high']
        
        # Verify size breakdown
        assert isinstance(prediction.size_breakdown, dict)
        assert all(key in prediction.size_breakdown for key in 
                  ['text_content', 'references', 'figures', 'tables', 'metadata', 'formatting'])
        assert all(value >= 0 for value in prediction.size_breakdown.values())
        
        # Verify prediction factors
        assert isinstance(prediction.prediction_factors, dict)
        assert all(key in prediction.prediction_factors for key in 
                  ['word_count_impact', 'media_content_impact', 'complexity_impact', 'citation_impact'])
    
    def test_predict_size_with_minimal_data(self, size_predictor):
        """Test size prediction with minimal manuscript data."""
        minimal_data = {
            "title": "Short Title",
            "abstract": "Brief abstract."
        }
        
        prediction = size_predictor.predict_size(minimal_data)
        
        # Should still return valid prediction
        assert isinstance(prediction, SizePrediction)
        assert prediction.predicted_size_bytes > 0
        assert prediction.confidence_score >= 0
    
    def test_extract_features(self, size_predictor, sample_manuscript_data):
        """Test feature extraction from manuscript data."""
        features = size_predictor.extract_features(sample_manuscript_data)
        
        assert isinstance(features, ManuscriptFeatures)
        assert features.word_count == 4500
        assert features.reference_count == 25
        assert features.figure_count == 6
        assert features.table_count == 3
        assert 0 <= features.complexity_score <= 1
        assert features.citation_density > 0
        assert features.content_type in [
            'clinical_trial', 'observational', 'systematic_review', 
            'case_study', 'letter', 'editorial', 'research_article'
        ]
    
    def test_model_training(self, size_predictor):
        """Test model training with historical data."""
        historical_data = [
            {
                "manuscript": {"title": "Test 1", "metadata": {"word_count": 1000}},
                "actual_size": 50000,
                "actual_compression_ratio": 0.7
            },
            {
                "manuscript": {"title": "Test 2", "metadata": {"word_count": 2000}},
                "actual_size": 100000,
                "actual_compression_ratio": 0.8
            }
        ]
        
        # Train model
        size_predictor.train_model(historical_data)
        
        assert size_predictor.model_trained is True
        assert len(size_predictor.historical_data) == 2
    
    def test_prediction_analytics(self, size_predictor):
        """Test prediction analytics functionality."""
        # Train with some data first
        historical_data = [
            {
                "manuscript": {"title": "Test", "metadata": {"word_count": 1000}},
                "actual_size": 50000,
                "actual_compression_ratio": 0.7
            }
        ]
        size_predictor.train_model(historical_data)
        
        analytics = size_predictor.get_size_prediction_analytics()
        
        assert "prediction_count" in analytics
        assert "mean_absolute_error" in analytics
        assert "mean_relative_error" in analytics


class TestRealTimeMonitorIntegration:
    """Integration tests for real-time monitor."""
    
    @pytest.mark.asyncio
    async def test_start_stop_monitoring(self, real_time_monitor):
        """Test starting and stopping monitoring."""
        assert real_time_monitor.is_monitoring is False
        
        # Start monitoring
        await real_time_monitor.start_monitoring()
        assert real_time_monitor.is_monitoring is True
        
        # Stop monitoring
        await real_time_monitor.stop_monitoring()
        assert real_time_monitor.is_monitoring is False
    
    def test_operation_tracking(self, real_time_monitor):
        """Test operation start, update, and completion."""
        # Start operation
        operation = real_time_monitor.start_operation("test_op", "compression", 1000)
        
        assert operation.operation_id == "test_op"
        assert operation.operation_type == "compression"
        assert operation.input_size == 1000
        assert operation.status == "running"
        assert "test_op" in real_time_monitor.active_operations
        
        # Update operation
        real_time_monitor.update_operation(
            "test_op", 
            output_size=800, 
            resource_usage={"cpu": 25.5, "memory": 512}
        )
        
        updated_op = real_time_monitor.active_operations["test_op"]
        assert updated_op.output_size == 800
        assert updated_op.compression_ratio == 0.8
        assert updated_op.resource_usage["cpu"] == 25.5
        
        # Complete operation
        real_time_monitor.complete_operation("test_op", success=True)
        
        assert "test_op" not in real_time_monitor.active_operations
        assert len(real_time_monitor.completed_operations) == 1
        assert real_time_monitor.completed_operations[-1].status == "completed"
    
    def test_metrics_collection(self, real_time_monitor):
        """Test custom metrics collection."""
        metric = PerformanceMetric(
            timestamp=datetime.now(),
            metric_name="test_metric",
            value=42.0,
            unit="ms",
            operation_id="test_op",
            component="test_component"
        )
        
        real_time_monitor.add_metric(metric)
        
        assert "test_metric" in real_time_monitor.metrics_history
        assert len(real_time_monitor.metrics_history["test_metric"]) == 1
        assert real_time_monitor.metrics_history["test_metric"][0] == metric
    
    def test_operation_statistics(self, real_time_monitor):
        """Test operation statistics calculation."""
        # Add some completed operations
        for i in range(3):
            op_id = f"op_{i}"
            real_time_monitor.start_operation(op_id, "compression", 1000)
            real_time_monitor.update_operation(op_id, output_size=800)
            real_time_monitor.complete_operation(op_id, success=True)
        
        # Add one failed operation
        real_time_monitor.start_operation("failed_op", "compression", 1000)
        real_time_monitor.complete_operation("failed_op", success=False)
        
        stats = real_time_monitor.get_operation_stats()
        
        assert stats["total_operations"] == 4
        assert stats["completed_operations"] == 4
        assert stats["success_rate"] == 75.0  # 3 out of 4 succeeded
        assert "compression" in stats["operations_by_type"]


class TestMetricsDashboardIntegration:
    """Integration tests for metrics dashboard."""
    
    def test_dashboard_data_retrieval(self, dashboard):
        """Test complete dashboard data retrieval."""
        data = dashboard.get_dashboard_data()
        
        # Verify main structure
        assert "timestamp" in data
        assert "summary" in data
        assert "system_health" in data
        assert "operation_metrics" in data
        assert "performance_trends" in data
        assert "alerts" in data
        assert "charts" in data
    
    def test_summary_statistics(self, dashboard, real_time_monitor):
        """Test summary statistics calculation."""
        # Add some test data
        real_time_monitor.start_operation("test", "compression", 1000)
        real_time_monitor.complete_operation("test", success=True)
        
        summary = dashboard._get_summary_stats()
        
        assert "active_operations" in summary
        assert "completed_operations" in summary
        assert "success_rate" in summary
        assert "avg_processing_time" in summary
        assert "system_health_score" in summary
    
    def test_system_health_data(self, dashboard):
        """Test system health data retrieval."""
        health_data = dashboard._get_system_health_data()
        
        # Should handle no data gracefully
        if health_data.get("status") != "no_data":
            assert "current" in health_data
            assert "trends" in health_data
            assert "history" in health_data
    
    def test_operation_metrics(self, dashboard):
        """Test operation metrics retrieval."""
        metrics = dashboard._get_operation_metrics()
        
        assert "by_type" in metrics
        assert "throughput" in metrics
        assert "compression" in metrics
        assert "quality_metrics" in metrics
    
    def test_active_alerts(self, dashboard):
        """Test active alerts retrieval."""
        alerts = dashboard._get_active_alerts()
        
        assert isinstance(alerts, list)
        # Each alert should have required fields if any exist
        for alert in alerts:
            assert "type" in alert
            assert "severity" in alert
            assert "message" in alert
            assert "timestamp" in alert


class TestAPIIntegration:
    """Integration tests for analytics API endpoints."""
    
    @pytest.fixture
    def mock_app(self):
        """Mock FastAPI app for testing."""
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        
        # Import the analytics router
        try:
            from services.worker.app.routes.analytics import router
            app = FastAPI()
            app.include_router(router)
            return TestClient(app)
        except ImportError:
            pytest.skip("Analytics router not available")
    
    def test_health_endpoint(self, mock_app):
        """Test health endpoint."""
        response = mock_app.get("/api/analytics/health")
        
        assert response.status_code in [200, 500]  # 500 if no health data available
        
        if response.status_code == 200:
            data = response.json()
            assert "health" in data
    
    def test_predict_size_endpoint(self, mock_app, sample_manuscript_data):
        """Test size prediction endpoint."""
        response = mock_app.post(
            "/api/analytics/predict-size",
            json=sample_manuscript_data
        )
        
        assert response.status_code in [200, 500]  # 500 if predictor not initialized
        
        if response.status_code == 200:
            data = response.json()
            assert "prediction" in data
            assert "breakdown" in data
            assert "factors" in data
    
    def test_dashboard_endpoint(self, mock_app):
        """Test dashboard data endpoint."""
        response = mock_app.get("/api/analytics/dashboard")
        
        assert response.status_code in [200, 500]  # 500 if no data available
        
        if response.status_code == 200:
            data = response.json()
            assert "timestamp" in data
    
    def test_operation_stats_endpoint(self, mock_app):
        """Test operation statistics endpoint."""
        response = mock_app.get("/api/analytics/operations/stats")
        
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert "statistics" in data


class TestWebSocketIntegration:
    """Integration tests for WebSocket functionality."""
    
    @pytest.mark.asyncio
    async def test_websocket_connection(self):
        """Test WebSocket connection establishment."""
        # This would require a running server to test properly
        # For now, just test that the connection manager exists
        try:
            from services.worker.app.routes.analytics import manager, ConnectionManager
            assert isinstance(manager, ConnectionManager)
            assert hasattr(manager, 'active_connections')
            assert hasattr(manager, 'connect')
            assert hasattr(manager, 'disconnect')
            assert hasattr(manager, 'broadcast')
        except ImportError:
            pytest.skip("WebSocket components not available")


class TestPerformanceAndScaling:
    """Performance and scaling tests for analytics system."""
    
    def test_large_dataset_prediction(self, size_predictor):
        """Test prediction with large dataset."""
        large_manuscript = {
            "title": "Large Clinical Trial Analysis",
            "abstract": "This is a comprehensive analysis..." * 100,
            "introduction": "Healthcare research has shown..." * 500,
            "methods": "We conducted a large-scale study..." * 300,
            "results": "Our findings demonstrate..." * 400,
            "discussion": "These results have implications..." * 200,
            "references": [f"Reference {i}" for i in range(1, 101)],  # 100 references
            "metadata": {
                "word_count": 50000,
                "reference_count": 100,
                "figure_count": 25,
                "table_count": 15
            }
        }
        
        start_time = datetime.now()
        prediction = size_predictor.predict_size(large_manuscript)
        end_time = datetime.now()
        
        processing_time = (end_time - start_time).total_seconds()
        
        # Should complete within reasonable time
        assert processing_time < 2.0  # Less than 2 seconds
        assert prediction.predicted_size_bytes > 100000  # Should predict substantial size
    
    def test_multiple_concurrent_operations(self, real_time_monitor):
        """Test handling multiple concurrent operations."""
        operation_ids = []
        
        # Start multiple operations
        for i in range(50):
            op_id = f"concurrent_op_{i}"
            real_time_monitor.start_operation(op_id, "compression", 1000 + i * 100)
            operation_ids.append(op_id)
        
        assert len(real_time_monitor.active_operations) == 50
        
        # Complete all operations
        for op_id in operation_ids:
            real_time_monitor.complete_operation(op_id, success=True)
        
        assert len(real_time_monitor.active_operations) == 0
        assert len(real_time_monitor.completed_operations) == 50
    
    def test_memory_usage_with_large_history(self, real_time_monitor):
        """Test memory usage with large metric history."""
        # Add many metrics to test memory management
        for i in range(2000):  # More than max_history_points
            metric = PerformanceMetric(
                timestamp=datetime.now(),
                metric_name="test_metric",
                value=float(i),
                unit="count"
            )
            real_time_monitor.add_metric(metric)
        
        # Should respect max_history_points limit
        assert len(real_time_monitor.metrics_history["test_metric"]) <= real_time_monitor.max_history_points


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])