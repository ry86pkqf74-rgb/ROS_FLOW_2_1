"""
Analytics API Routes
==================

API endpoints for analytics, monitoring, and predictive modeling services.
Provides access to:
- Size prediction for manuscripts
- Real-time monitoring data
- Performance dashboards
- System health metrics
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from fastapi.responses import JSONResponse
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime

from ...src.analytics.predictive_modeling.size_predictor import (
    get_size_predictor,
    SizePrediction,
    ManuscriptFeatures
)
from ...src.analytics.monitoring.real_time_monitor import (
    get_monitor,
    PerformanceMetric,
    SystemHealth
)
from ...src.analytics.dashboard.metrics_dashboard import MetricsDashboard

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/analytics", tags=["analytics"])

# Initialize services
size_predictor = get_size_predictor()
monitor = get_monitor()
dashboard = MetricsDashboard(monitor)


# ============================================================================
# Size Prediction Endpoints
# ============================================================================

@router.post("/predict-size")
async def predict_manuscript_size(manuscript_data: Dict[str, Any]) -> JSONResponse:
    """
    Predict manuscript package size and compression characteristics.
    
    Args:
        manuscript_data: Manuscript content and metadata
        
    Returns:
        Size prediction with confidence metrics
    """
    try:
        prediction = size_predictor.predict_size(manuscript_data)
        
        response_data = {
            "prediction": {
                "predicted_size_bytes": prediction.predicted_size_bytes,
                "confidence_score": prediction.confidence_score,
                "predicted_compression_ratio": prediction.predicted_compression_ratio,
                "estimated_processing_time": prediction.estimated_processing_time,
                "recommended_compression_level": prediction.recommended_compression_level
            },
            "breakdown": prediction.size_breakdown,
            "factors": prediction.prediction_factors,
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"Size prediction completed: {prediction.predicted_size_bytes:,} bytes")
        return JSONResponse(content=response_data)
        
    except Exception as e:
        logger.error(f"Size prediction failed: {e}")
        raise HTTPException(status_code=500, detail=f"Size prediction failed: {str(e)}")


@router.get("/prediction-analytics")
async def get_prediction_analytics() -> JSONResponse:
    """Get analytics on size prediction performance."""
    try:
        analytics = size_predictor.get_size_prediction_analytics()
        return JSONResponse(content={
            "analytics": analytics,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Failed to get prediction analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/train-predictor")
async def train_size_predictor(
    background_tasks: BackgroundTasks,
    historical_data: List[Dict[str, Any]]
) -> JSONResponse:
    """
    Train the size predictor with historical data.
    
    Args:
        historical_data: List of historical manuscript and size data
        
    Returns:
        Training status
    """
    try:
        def train_model():
            size_predictor.train_model(historical_data)
            size_predictor.save_model()
        
        background_tasks.add_task(train_model)
        
        return JSONResponse(content={
            "status": "training_started",
            "data_points": len(historical_data),
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Model training failed: {e}")
        raise HTTPException(status_code=500, detail=f"Training failed: {str(e)}")


# ============================================================================
# Monitoring Endpoints
# ============================================================================

@router.get("/health")
async def get_system_health() -> JSONResponse:
    """Get current system health metrics."""
    try:
        health = monitor.get_current_health()
        
        if not health:
            return JSONResponse(content={"status": "no_data"})
        
        return JSONResponse(content={
            "health": {
                "timestamp": health.timestamp.isoformat(),
                "cpu_usage": health.cpu_usage,
                "memory_usage": health.memory_usage,
                "disk_usage": health.disk_usage,
                "active_operations": health.active_operations,
                "queue_length": health.queue_length,
                "response_time_avg": health.response_time_avg,
                "error_rate": health.error_rate
            }
        })
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health/history")
async def get_health_history(minutes: int = Query(60, ge=1, le=1440)) -> JSONResponse:
    """Get system health history for specified time period."""
    try:
        history = monitor.get_health_history(minutes=minutes)
        
        history_data = [
            {
                "timestamp": h.timestamp.isoformat(),
                "cpu_usage": h.cpu_usage,
                "memory_usage": h.memory_usage,
                "disk_usage": h.disk_usage,
                "active_operations": h.active_operations,
                "queue_length": h.queue_length,
                "response_time_avg": h.response_time_avg,
                "error_rate": h.error_rate
            }
            for h in history
        ]
        
        return JSONResponse(content={
            "history": history_data,
            "time_range_minutes": minutes,
            "data_points": len(history_data)
        })
        
    except Exception as e:
        logger.error(f"Health history retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/operations/stats")
async def get_operation_statistics() -> JSONResponse:
    """Get operation statistics and performance metrics."""
    try:
        stats = monitor.get_operation_stats()
        return JSONResponse(content={
            "statistics": stats,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Operation stats retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/operations/start")
async def start_operation_monitoring(
    operation_type: str,
    input_size: int,
    operation_id: Optional[str] = None
) -> JSONResponse:
    """Start monitoring an optimization operation."""
    try:
        if not operation_id:
            operation_id = f"{operation_type}_{int(datetime.now().timestamp() * 1000)}"
        
        operation = monitor.start_operation(operation_id, operation_type, input_size)
        
        return JSONResponse(content={
            "operation_id": operation_id,
            "status": "monitoring_started",
            "start_time": operation.start_time.isoformat()
        })
        
    except Exception as e:
        logger.error(f"Operation monitoring start failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/operations/{operation_id}/update")
async def update_operation(
    operation_id: str,
    status: Optional[str] = None,
    output_size: Optional[int] = None,
    resource_usage: Optional[Dict[str, float]] = None,
    error_message: Optional[str] = None
) -> JSONResponse:
    """Update operation status and metrics."""
    try:
        monitor.update_operation(
            operation_id=operation_id,
            status=status,
            output_size=output_size,
            resource_usage=resource_usage,
            error_message=error_message
        )
        
        return JSONResponse(content={
            "operation_id": operation_id,
            "status": "updated",
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Operation update failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/operations/{operation_id}/complete")
async def complete_operation(operation_id: str, success: bool = True) -> JSONResponse:
    """Mark operation as completed."""
    try:
        monitor.complete_operation(operation_id, success)
        
        return JSONResponse(content={
            "operation_id": operation_id,
            "status": "completed" if success else "failed",
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Operation completion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Dashboard Endpoints
# ============================================================================

@router.get("/dashboard")
async def get_dashboard_data() -> JSONResponse:
    """Get complete dashboard data for frontend rendering."""
    try:
        data = dashboard.get_dashboard_data()
        return JSONResponse(content=data)
    except Exception as e:
        logger.error(f"Dashboard data retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard/summary")
async def get_dashboard_summary() -> JSONResponse:
    """Get dashboard summary statistics."""
    try:
        summary = dashboard._get_summary_stats()
        return JSONResponse(content={
            "summary": summary,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Dashboard summary retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard/alerts")
async def get_active_alerts() -> JSONResponse:
    """Get currently active system alerts."""
    try:
        alerts = dashboard._get_active_alerts()
        return JSONResponse(content={
            "alerts": alerts,
            "count": len(alerts),
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Alerts retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard/trends")
async def get_performance_trends() -> JSONResponse:
    """Get performance trend analysis."""
    try:
        trends = dashboard._get_performance_trends()
        return JSONResponse(content={
            "trends": trends,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Trends retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard/export")
async def export_dashboard_data(format: str = "json") -> JSONResponse:
    """Export dashboard data in specified format."""
    try:
        export_data = dashboard.export_dashboard_data(format)
        
        return JSONResponse(content={
            "export_data": export_data,
            "format": format,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Dashboard export failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Custom Metrics Endpoints
# ============================================================================

@router.post("/metrics/custom")
async def add_custom_metric(
    metric_name: str,
    value: float,
    unit: str,
    operation_id: Optional[str] = None,
    component: Optional[str] = None,
    tags: Optional[Dict[str, str]] = None
) -> JSONResponse:
    """Add a custom performance metric."""
    try:
        metric = PerformanceMetric(
            timestamp=datetime.now(),
            metric_name=metric_name,
            value=value,
            unit=unit,
            operation_id=operation_id,
            component=component,
            tags=tags
        )
        
        monitor.add_metric(metric)
        
        return JSONResponse(content={
            "status": "metric_added",
            "metric_name": metric_name,
            "value": value,
            "timestamp": metric.timestamp.isoformat()
        })
        
    except Exception as e:
        logger.error(f"Custom metric addition failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics/custom/{metric_name}")
async def get_custom_metrics(
    metric_name: str,
    time_range_hours: int = Query(1, ge=1, le=24)
) -> JSONResponse:
    """Get custom metrics for specific analysis."""
    try:
        custom_data = dashboard.get_custom_metrics([metric_name], time_range_hours)
        
        return JSONResponse(content={
            "metrics": custom_data,
            "metric_name": metric_name,
            "time_range_hours": time_range_hours,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Custom metrics retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Monitoring Control Endpoints  
# ============================================================================

@router.post("/monitoring/start")
async def start_monitoring() -> JSONResponse:
    """Start real-time monitoring system."""
    try:
        await monitor.start_monitoring()
        
        return JSONResponse(content={
            "status": "monitoring_started",
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Monitoring start failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/monitoring/stop")
async def stop_monitoring() -> JSONResponse:
    """Stop real-time monitoring system."""
    try:
        await monitor.stop_monitoring()
        
        return JSONResponse(content={
            "status": "monitoring_stopped",
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Monitoring stop failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/monitoring/status")
async def get_monitoring_status() -> JSONResponse:
    """Get current monitoring system status."""
    try:
        return JSONResponse(content={
            "is_monitoring": monitor.is_monitoring,
            "metrics_interval": monitor.metrics_interval,
            "max_history_points": monitor.max_history_points,
            "active_operations": len(monitor.active_operations),
            "completed_operations": len(monitor.completed_operations),
            "system_health_points": len(monitor.system_health_history),
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Monitoring status failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Health Check & Info Endpoints
# ============================================================================

@router.get("/info")
async def get_analytics_info() -> JSONResponse:
    """Get analytics system information."""
    try:
        return JSONResponse(content={
            "system": "ResearchFlow Analytics",
            "version": "2.0.0",
            "components": {
                "size_predictor": {
                    "model_trained": size_predictor.model_trained,
                    "feature_weights_count": len(size_predictor.feature_weights),
                    "historical_data_points": len(size_predictor.historical_data)
                },
                "monitor": {
                    "is_active": monitor.is_monitoring,
                    "metrics_interval": monitor.metrics_interval,
                    "alert_callbacks": len(monitor.alert_callbacks),
                    "metric_callbacks": len(monitor.metric_callbacks)
                },
                "dashboard": {
                    "refresh_interval": dashboard.dashboard_config["refresh_interval"],
                    "history_window": dashboard.dashboard_config["history_window"],
                    "chart_types": len(dashboard.dashboard_config["chart_types"])
                }
            },
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Analytics info retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# WebSocket Support (for real-time updates)
# ============================================================================

try:
    from fastapi import WebSocket, WebSocketDisconnect
    import asyncio
    import json
    
    class ConnectionManager:
        """WebSocket connection manager for real-time analytics."""
        
        def __init__(self):
            self.active_connections: List[WebSocket] = []
        
        async def connect(self, websocket: WebSocket):
            await websocket.accept()
            self.active_connections.append(websocket)
        
        def disconnect(self, websocket: WebSocket):
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
        
        async def send_personal_message(self, message: dict, websocket: WebSocket):
            try:
                await websocket.send_text(json.dumps(message, default=str))
            except:
                self.disconnect(websocket)
        
        async def broadcast(self, message: dict):
            disconnected = []
            for connection in self.active_connections:
                try:
                    await connection.send_text(json.dumps(message, default=str))
                except:
                    disconnected.append(connection)
            
            # Clean up disconnected connections
            for conn in disconnected:
                self.disconnect(conn)
    
    
    manager = ConnectionManager()
    
    
    @router.websocket("/ws/realtime")
    async def websocket_realtime_analytics(websocket: WebSocket):
        """WebSocket endpoint for real-time analytics updates."""
        await manager.connect(websocket)
        
        try:
            # Send initial data
            initial_data = {
                "type": "initial",
                "data": dashboard.get_dashboard_data(),
                "timestamp": datetime.now().isoformat()
            }
            await manager.send_personal_message(initial_data, websocket)
            
            # Keep connection alive and send periodic updates
            while True:
                await asyncio.sleep(5)  # Update every 5 seconds
                
                # Get current health
                health = monitor.get_current_health()
                if health:
                    update_data = {
                        "type": "health_update",
                        "data": {
                            "timestamp": health.timestamp.isoformat(),
                            "cpu_usage": health.cpu_usage,
                            "memory_usage": health.memory_usage,
                            "disk_usage": health.disk_usage,
                            "active_operations": health.active_operations,
                            "queue_length": health.queue_length,
                            "response_time_avg": health.response_time_avg,
                            "error_rate": health.error_rate
                        }
                    }
                    await manager.send_personal_message(update_data, websocket)
                
        except WebSocketDisconnect:
            manager.disconnect(websocket)
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            manager.disconnect(websocket)
    
    
    # Register alert callback to broadcast alerts via WebSocket
    async def broadcast_alert(alert: Dict[str, Any]):
        """Broadcast alert to all WebSocket connections."""
        await manager.broadcast({
            "type": "alert",
            "data": alert,
            "timestamp": datetime.now().isoformat()
        })
    
    
    # Register callback with monitor
    monitor.register_alert_callback(broadcast_alert)

except ImportError:
    logger.warning("WebSocket support not available - skipping real-time features")


# Export router
__all__ = ["router"]