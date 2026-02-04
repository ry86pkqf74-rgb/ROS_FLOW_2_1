#!/usr/bin/env python3
"""
Tests for Error Tracking & APM Integration

Tests cover:
- Error tracking functionality
- Distributed tracing spans
- Sentry integration (mocked)
- Error statistics and monitoring
- Context management
- Decorator functionality
"""

import asyncio
import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

from agents.utils.error_tracking import (
    ErrorTracker,
    ErrorStats,
    SpanContext,
    TraceContext,
    initialize_error_tracking,
    track_error,
    create_span,
    get_error_stats,
    manual_track_error,
    get_active_traces,
    clear_old_errors,
    get_error_tracker,
    check_error_health,
    _error_tracker
)


class TestErrorTracker:
    """Test the ErrorTracker class"""
    
    def test_initialization(self):
        """Test error tracker initialization"""
        tracker = ErrorTracker()
        assert not tracker.enabled
        assert not tracker.sentry_initialized
        assert tracker.error_history == []
        assert tracker.active_spans == {}
        
    @patch('agents.utils.error_tracking.SENTRY_AVAILABLE', False)
    def test_initialize_sentry_unavailable(self):
        """Test Sentry initialization when SDK not available"""
        tracker = ErrorTracker()
        tracker.initialize_sentry(dsn="test-dsn")
        
        assert tracker.enabled
        assert not tracker.sentry_initialized
        
    def test_initialize_sentry_no_dsn(self):
        """Test Sentry initialization without DSN"""
        tracker = ErrorTracker()
        tracker.initialize_sentry()  # No DSN provided
        
        assert tracker.enabled
        assert not tracker.sentry_initialized
        
    @patch('agents.utils.error_tracking.sentry_sdk')
    def test_initialize_sentry_success(self, mock_sentry):
        """Test successful Sentry initialization"""
        tracker = ErrorTracker()
        tracker.initialize_sentry(
            dsn="https://test@example.com/1",
            environment="test",
            sample_rate=0.5
        )
        
        assert tracker.enabled
        assert tracker.sentry_initialized
        mock_sentry.init.assert_called_once()
        
    @patch('agents.utils.error_tracking.sentry_sdk')
    def test_initialize_sentry_failure(self, mock_sentry):
        """Test Sentry initialization failure"""
        mock_sentry.init.side_effect = Exception("Init failed")
        
        tracker = ErrorTracker()
        tracker.initialize_sentry(dsn="https://test@example.com/1")
        
        assert tracker.enabled
        assert not tracker.sentry_initialized
        
    def test_trace_and_span_id_generation(self):
        """Test trace and span ID generation"""
        tracker = ErrorTracker()
        
        trace_id = tracker.create_trace_id()
        span_id = tracker.create_span_id()
        
        assert isinstance(trace_id, str)
        assert isinstance(span_id, str)
        assert len(span_id) == 16
        assert trace_id != span_id
        
        # Test uniqueness
        assert tracker.create_trace_id() != trace_id
        assert tracker.create_span_id() != span_id
        

class TestDistributedTracing:
    """Test distributed tracing functionality"""
    
    @pytest.fixture
    def tracker(self):
        """Create enabled error tracker for testing"""
        tracker = ErrorTracker()
        tracker.enabled = True
        return tracker
        
    @pytest.mark.asyncio
    async def test_start_span(self, tracker):
        """Test starting a span"""
        span_id = await tracker.start_span(
            operation="test_op",
            component="TestComponent",
            tags={"key": "value"}
        )
        
        assert span_id
        assert span_id in tracker.active_spans
        
        span = tracker.active_spans[span_id]
        assert span.operation == "test_op"
        assert span.component == "TestComponent"
        assert span.tags == {"key": "value"}
        assert not span.finished
        
    @pytest.mark.asyncio
    async def test_finish_span(self, tracker):
        """Test finishing a span"""
        span_id = await tracker.start_span("test_op", "TestComponent")
        
        # Let some time pass
        await asyncio.sleep(0.01)
        
        await tracker.finish_span(span_id, tags={"result": "success"})
        
        assert span_id not in tracker.active_spans
        
    @pytest.mark.asyncio
    async def test_finish_unknown_span(self, tracker):
        """Test finishing an unknown span"""
        # Should not raise exception
        await tracker.finish_span("unknown_span_id")
        
    @pytest.mark.asyncio
    async def test_span_with_error(self, tracker):
        """Test span with error"""
        span_id = await tracker.start_span("test_op", "TestComponent")
        
        error = ValueError("Test error")
        await tracker.finish_span(span_id, error=error)
        
        assert span_id not in tracker.active_spans
        
    @pytest.mark.asyncio
    async def test_nested_spans(self, tracker):
        """Test nested span creation"""
        # Start parent span
        parent_span_id = await tracker.start_span("parent_op", "ParentComponent")
        
        # Start child span
        child_span_id = await tracker.start_span(
            "child_op", 
            "ChildComponent",
            parent_span_id=parent_span_id
        )
        
        child_span = tracker.active_spans[child_span_id]
        assert child_span.parent_span_id == parent_span_id
        
        await tracker.finish_span(child_span_id)
        await tracker.finish_span(parent_span_id)
        

class TestErrorTracking:
    """Test error tracking functionality"""
    
    @pytest.fixture
    def tracker(self):
        """Create enabled error tracker for testing"""
        tracker = ErrorTracker()
        tracker.enabled = True
        return tracker
        
    @pytest.mark.asyncio
    async def test_track_error(self, tracker):
        """Test error tracking"""
        error = ValueError("Test error")
        
        await tracker.track_error(
            error=error,
            component="TestComponent",
            operation="test_operation",
            context={"key": "value"},
            severity="error"
        )
        
        assert len(tracker.error_history) == 1
        error_data = tracker.error_history[0]
        
        assert error_data["component"] == "TestComponent"
        assert error_data["operation"] == "test_operation"
        assert error_data["error_type"] == "ValueError"
        assert error_data["error_message"] == "Test error"
        assert error_data["context"] == {"key": "value"}
        assert error_data["severity"] == "error"
        
    @pytest.mark.asyncio
    async def test_error_history_limit(self, tracker):
        """Test error history size limit"""
        # Add more than 1000 errors
        for i in range(1100):
            await tracker.track_error(
                error=RuntimeError(f"Error {i}"),
                component="TestComponent"
            )
        
        # Should keep only last 1000
        assert len(tracker.error_history) == 1000
        
        # Should have most recent errors
        last_error = tracker.error_history[-1]
        assert "Error 1099" in last_error["error_message"]
        
    @pytest.mark.asyncio
    @patch('agents.utils.error_tracking.sentry_sdk')
    def test_track_error_with_sentry(self, mock_sentry, tracker):
        """Test error tracking with Sentry integration"""
        tracker.sentry_initialized = True
        
        error = ValueError("Test error")
        await tracker.track_error(error, "TestComponent")
        
        # Should capture exception in Sentry
        mock_sentry.capture_exception.assert_called_once_with(error)
        

class TestErrorStatistics:
    """Test error statistics functionality"""
    
    @pytest.fixture
    def tracker_with_errors(self):
        """Create tracker with some error history"""
        tracker = ErrorTracker()
        tracker.enabled = True
        
        # Add some test errors
        now = datetime.utcnow()
        
        tracker.error_history = [
            {
                "timestamp": now - timedelta(minutes=5),
                "error_type": "ValueError",
                "component": "TestComponent"
            },
            {
                "timestamp": now - timedelta(minutes=10),
                "error_type": "RuntimeError",
                "component": "TestComponent"
            },
            {
                "timestamp": now - timedelta(minutes=20),  # Too old
                "error_type": "KeyError",
                "component": "OtherComponent"
            }
        ]
        
        return tracker
        
    @pytest.mark.asyncio
    async def test_get_error_stats(self, tracker_with_errors):
        """Test getting error statistics"""
        stats = await tracker_with_errors.get_error_stats(last_minutes=15)
        
        assert stats.total_errors == 2  # Only errors from last 15 minutes
        assert stats.error_rate == 2 / 15  # errors per minute
        assert stats.error_types == {"ValueError": 1, "RuntimeError": 1}
        assert stats.time_window_minutes == 15
        
    @pytest.mark.asyncio
    async def test_get_error_stats_empty(self):
        """Test getting error statistics with no errors"""
        tracker = ErrorTracker()
        tracker.enabled = True
        
        stats = await tracker.get_error_stats()
        
        assert stats.total_errors == 0
        assert stats.error_rate == 0.0
        assert stats.error_types == {}
        assert stats.last_error_time is None
        
    @pytest.mark.asyncio
    async def test_clear_old_errors(self, tracker_with_errors):
        """Test clearing old errors"""
        await tracker_with_errors.clear_old_errors(hours=0.25)  # 15 minutes
        
        # Should keep only errors from last 15 minutes
        assert len(tracker_with_errors.error_history) == 2
        
        # Oldest error should be removed
        for error in tracker_with_errors.error_history:
            assert error["error_type"] != "KeyError"
            

class TestTraceContext:
    """Test TraceContext context manager"""
    
    @pytest.mark.asyncio
    async def test_trace_context_success(self):
        """Test successful trace context"""
        _error_tracker.enabled = True
        
        async with TraceContext("test_operation", "TestComponent") as ctx:
            assert ctx.operation == "test_operation"
            assert ctx.component == "TestComponent"
            # Span should be active
            assert ctx.span_id is not None
            
        # Span should be finished and cleaned up
        assert ctx.span_id not in _error_tracker.active_spans
        
    @pytest.mark.asyncio
    async def test_trace_context_with_error(self):
        """Test trace context with error"""
        _error_tracker.enabled = True
        
        with pytest.raises(ValueError):
            async with TraceContext("test_operation", "TestComponent") as ctx:
                span_id = ctx.span_id
                raise ValueError("Test error")
                
        # Span should still be cleaned up
        assert span_id not in _error_tracker.active_spans
        

class TestDecorators:
    """Test error tracking and tracing decorators"""
    
    @pytest.mark.asyncio
    async def test_track_error_decorator_async(self):
        """Test track_error decorator with async function"""
        _error_tracker.enabled = True
        _error_tracker.error_history.clear()
        
        @track_error(component="TestComponent", operation="test_op")
        async def failing_function():
            raise ValueError("Test error")
            
        with pytest.raises(ValueError):
            await failing_function()
            
        # Error should be tracked
        assert len(_error_tracker.error_history) == 1
        error_data = _error_tracker.error_history[0]
        assert error_data["component"] == "TestComponent"
        assert error_data["operation"] == "test_op"
        
    def test_track_error_decorator_sync(self):
        """Test track_error decorator with sync function"""
        _error_tracker.enabled = True
        _error_tracker.error_history.clear()
        
        @track_error(component="TestComponent")
        def failing_function():
            raise RuntimeError("Sync error")
            
        with pytest.raises(RuntimeError):
            failing_function()
            
        # Note: Sync functions create async tasks for error tracking
        # In real usage, this would work with an event loop
        
    @pytest.mark.asyncio
    async def test_create_span_decorator_async(self):
        """Test create_span decorator with async function"""
        _error_tracker.enabled = True
        _error_tracker.active_spans.clear()
        
        @create_span("test_operation", "TestComponent")
        async def test_function():
            # Check that span is active during execution
            active_traces = get_active_traces()
            assert len(active_traces) == 1
            assert active_traces[0]["operation"] == "test_operation"
            return "success"
            
        result = await test_function()
        assert result == "success"
        
        # Span should be cleaned up
        assert len(_error_tracker.active_spans) == 0
        
    def test_create_span_decorator_sync(self):
        """Test create_span decorator with sync function"""
        @create_span("test_operation", "TestComponent")
        def test_function():
            return "success"
            
        # Should work without errors (uses basic logging for sync)
        result = test_function()
        assert result == "success"
        

class TestConvenienceFunctions:
    """Test convenience functions"""
    
    @pytest.mark.asyncio
    async def test_get_error_stats(self):
        """Test get_error_stats convenience function"""
        _error_tracker.enabled = True
        
        stats = await get_error_stats(last_minutes=15)
        assert isinstance(stats, ErrorStats)
        
    @pytest.mark.asyncio
    async def test_manual_track_error(self):
        """Test manual_track_error convenience function"""
        _error_tracker.enabled = True
        _error_tracker.error_history.clear()
        
        error = ValueError("Manual error")
        await manual_track_error(
            error=error,
            component="TestComponent",
            operation="manual_op",
            context={"manual": True}
        )
        
        assert len(_error_tracker.error_history) == 1
        error_data = _error_tracker.error_history[0]
        assert error_data["operation"] == "manual_op"
        assert error_data["context"]["manual"] is True
        
    def test_get_active_traces(self):
        """Test get_active_traces convenience function"""
        traces = get_active_traces()
        assert isinstance(traces, list)
        
    @pytest.mark.asyncio
    async def test_clear_old_errors_function(self):
        """Test clear_old_errors convenience function"""
        # Should not raise errors
        await clear_old_errors(hours=1)
        
    def test_get_error_tracker(self):
        """Test get_error_tracker convenience function"""
        tracker = get_error_tracker()
        assert isinstance(tracker, ErrorTracker)
        assert tracker is _error_tracker
        
    @pytest.mark.asyncio
    async def test_check_error_health(self):
        """Test check_error_health function"""
        _error_tracker.enabled = True
        
        health = await check_error_health(error_rate_threshold=0.1)
        
        assert isinstance(health, dict)
        assert "healthy" in health
        assert "error_rate" in health
        assert "total_errors" in health
        assert "threshold" in health
        
    @pytest.mark.asyncio
    async def test_check_error_health_unhealthy(self):
        """Test check_error_health with high error rate"""
        _error_tracker.enabled = True
        _error_tracker.error_history.clear()
        
        # Add recent errors
        now = datetime.utcnow()
        for i in range(10):
            _error_tracker.error_history.append({
                "timestamp": now - timedelta(minutes=i),
                "error_type": "TestError",
                "component": "TestComponent"
            })
            
        health = await check_error_health(error_rate_threshold=0.1)
        
        assert not health["healthy"]
        assert health["error_rate"] > 0.1
        

class TestIntegration:
    """Integration tests for error tracking"""
    
    @pytest.mark.asyncio
    async def test_full_workflow(self):
        """Test complete error tracking workflow"""
        # Initialize tracking
        initialize_error_tracking(
            environment="test",
            sample_rate=1.0
        )
        
        # Clear state
        _error_tracker.error_history.clear()
        _error_tracker.active_spans.clear()
        
        # Create span and track error
        async with TraceContext("integration_test", "IntegrationComponent"):
            try:
                raise RuntimeError("Integration test error")
            except Exception as e:
                await manual_track_error(
                    error=e,
                    component="IntegrationComponent",
                    operation="integration_test"
                )
                
        # Verify results
        stats = await get_error_stats()
        assert stats.total_errors == 1
        assert "RuntimeError" in stats.error_types
        
        health = await check_error_health()
        assert "healthy" in health
        
    @pytest.mark.asyncio
    async def test_decorator_integration(self):
        """Test decorator integration"""
        _error_tracker.enabled = True
        _error_tracker.error_history.clear()
        
        @track_error(component="DecoratorTest")
        @create_span("decorator_operation")
        async def test_function():
            await asyncio.sleep(0.01)
            return "success"
            
        result = await test_function()
        assert result == "success"
        
        # No errors should be tracked for successful execution
        assert len(_error_tracker.error_history) == 0
        
        @track_error(component="DecoratorTest")
        @create_span("failing_operation")
        async def failing_function():
            raise ValueError("Decorator test error")
            
        with pytest.raises(ValueError):
            await failing_function()
            
        # Error should be tracked
        assert len(_error_tracker.error_history) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])