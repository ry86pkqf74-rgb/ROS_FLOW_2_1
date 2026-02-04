"""
Real-Time WebSocket Service
===========================

Advanced WebSocket service for real-time analytics data streaming.
Features:
- Multiple subscription channels
- Data filtering and aggregation
- Connection management
- Authentication and rate limiting
- Automatic reconnection support
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set, Callable, Union
from dataclasses import dataclass, asdict
import weakref
from enum import Enum
import time
import uuid

from fastapi import WebSocket, WebSocketDisconnect
from ..monitoring.real_time_monitor import get_monitor, SystemHealth, PerformanceMetric
from ..dashboard.metrics_dashboard import MetricsDashboard
from ..storage.analytics_db import get_analytics_db, AnalyticsDBContext

logger = logging.getLogger(__name__)


class SubscriptionChannel(Enum):
    """Available subscription channels."""
    SYSTEM_HEALTH = "system_health"
    OPERATION_METRICS = "operation_metrics"
    PREDICTIONS = "predictions"
    ALERTS = "alerts"
    PERFORMANCE_TRENDS = "performance_trends"
    CUSTOM_METRICS = "custom_metrics"
    ALL = "all"


@dataclass
class ClientSubscription:
    """Client subscription configuration."""
    client_id: str
    channels: Set[SubscriptionChannel]
    filters: Dict[str, Any]
    last_update: datetime
    connection_time: datetime
    message_count: int = 0
    rate_limit_window: datetime = None
    rate_limit_count: int = 0


@dataclass
class WebSocketMessage:
    """WebSocket message structure."""
    type: str
    channel: str
    data: Any
    timestamp: datetime
    client_id: Optional[str] = None
    message_id: Optional[str] = None


class RateLimiter:
    """Rate limiting for WebSocket connections."""
    
    def __init__(self, max_messages: int = 100, window_seconds: int = 60):
        self.max_messages = max_messages
        self.window_seconds = window_seconds
        
    def is_allowed(self, subscription: ClientSubscription) -> bool:
        """Check if client is within rate limits."""
        now = datetime.now()
        
        # Reset window if expired
        if (subscription.rate_limit_window is None or 
            now - subscription.rate_limit_window > timedelta(seconds=self.window_seconds)):
            subscription.rate_limit_window = now
            subscription.rate_limit_count = 0
        
        # Check limit
        if subscription.rate_limit_count >= self.max_messages:
            return False
        
        subscription.rate_limit_count += 1
        return True


class RealtimeWebSocketService:
    """Real-time WebSocket service for analytics data."""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.subscriptions: Dict[str, ClientSubscription] = {}
        self.message_handlers: Dict[str, Callable] = {}
        self.rate_limiter = RateLimiter()
        
        # Monitoring components
        self.monitor = get_monitor()
        self.dashboard = MetricsDashboard(self.monitor)
        
        # Background tasks
        self.broadcast_task = None
        self.cleanup_task = None
        self.is_running = False
        
        # Message queues for reliable delivery
        self.message_queues: Dict[str, List[WebSocketMessage]] = {}
        
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup message handlers."""
        self.message_handlers = {
            "subscribe": self._handle_subscribe,
            "unsubscribe": self._handle_unsubscribe,
            "get_data": self._handle_get_data,
            "ping": self._handle_ping,
            "set_filters": self._handle_set_filters
        }
    
    async def start_service(self):
        """Start the WebSocket service background tasks."""
        if self.is_running:
            return
        
        self.is_running = True
        self.broadcast_task = asyncio.create_task(self._broadcast_loop())
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        # Register callbacks with monitor
        await self.monitor.register_alert_callback(self._handle_alert)
        await self.monitor.register_metric_callback(self._handle_metric_update)
        
        logger.info("Real-time WebSocket service started")
    
    async def stop_service(self):
        """Stop the WebSocket service."""
        self.is_running = False
        
        if self.broadcast_task:
            self.broadcast_task.cancel()
        
        if self.cleanup_task:
            self.cleanup_task.cancel()
        
        # Close all connections
        for client_id, websocket in list(self.active_connections.items()):
            try:
                await websocket.close()
            except:
                pass
        
        self.active_connections.clear()
        self.subscriptions.clear()
        
        logger.info("Real-time WebSocket service stopped")
    
    async def connect_client(self, websocket: WebSocket, client_id: Optional[str] = None) -> str:
        """Connect a new WebSocket client."""
        await websocket.accept()
        
        if client_id is None:
            client_id = str(uuid.uuid4())
        
        self.active_connections[client_id] = websocket
        self.message_queues[client_id] = []
        
        # Create default subscription
        subscription = ClientSubscription(
            client_id=client_id,
            channels={SubscriptionChannel.SYSTEM_HEALTH},
            filters={},
            last_update=datetime.now(),
            connection_time=datetime.now()
        )
        self.subscriptions[client_id] = subscription
        
        # Send welcome message
        welcome_message = WebSocketMessage(
            type="connected",
            channel="system",
            data={
                "client_id": client_id,
                "server_time": datetime.now().isoformat(),
                "available_channels": [channel.value for channel in SubscriptionChannel],
                "rate_limit": {
                    "max_messages": self.rate_limiter.max_messages,
                    "window_seconds": self.rate_limiter.window_seconds
                }
            },
            timestamp=datetime.now(),
            client_id=client_id,
            message_id=str(uuid.uuid4())
        )
        
        await self._send_message(client_id, welcome_message)
        
        logger.info(f"WebSocket client {client_id} connected")
        return client_id
    
    async def disconnect_client(self, client_id: str):
        """Disconnect a WebSocket client."""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        
        if client_id in self.subscriptions:
            del self.subscriptions[client_id]
        
        if client_id in self.message_queues:
            del self.message_queues[client_id]
        
        logger.info(f"WebSocket client {client_id} disconnected")
    
    async def handle_message(self, client_id: str, message: dict):
        """Handle incoming WebSocket message."""
        try:
            message_type = message.get("type")
            if message_type not in self.message_handlers:
                await self._send_error(client_id, f"Unknown message type: {message_type}")
                return
            
            # Rate limiting check
            subscription = self.subscriptions.get(client_id)
            if subscription and not self.rate_limiter.is_allowed(subscription):
                await self._send_error(client_id, "Rate limit exceeded")
                return
            
            # Handle message
            handler = self.message_handlers[message_type]
            await handler(client_id, message)
            
        except Exception as e:
            logger.error(f"Error handling message from {client_id}: {e}")
            await self._send_error(client_id, "Internal server error")
    
    async def _handle_subscribe(self, client_id: str, message: dict):
        """Handle subscription request."""
        channels = message.get("channels", [])
        filters = message.get("filters", {})
        
        subscription = self.subscriptions.get(client_id)
        if not subscription:
            return
        
        # Parse channels
        parsed_channels = set()
        for channel in channels:
            try:
                parsed_channels.add(SubscriptionChannel(channel))
            except ValueError:
                await self._send_error(client_id, f"Invalid channel: {channel}")
                return
        
        # Update subscription
        subscription.channels = parsed_channels
        subscription.filters = filters
        subscription.last_update = datetime.now()
        
        # Send confirmation
        response = WebSocketMessage(
            type="subscribed",
            channel="system",
            data={
                "channels": [channel.value for channel in parsed_channels],
                "filters": filters
            },
            timestamp=datetime.now(),
            client_id=client_id
        )
        
        await self._send_message(client_id, response)
        
        # Send initial data for subscribed channels
        await self._send_initial_data(client_id, parsed_channels)
    
    async def _handle_unsubscribe(self, client_id: str, message: dict):
        """Handle unsubscription request."""
        channels = message.get("channels", [])
        
        subscription = self.subscriptions.get(client_id)
        if not subscription:
            return
        
        # Remove channels
        for channel in channels:
            try:
                channel_enum = SubscriptionChannel(channel)
                subscription.channels.discard(channel_enum)
            except ValueError:
                pass
        
        response = WebSocketMessage(
            type="unsubscribed",
            channel="system",
            data={"channels": channels},
            timestamp=datetime.now(),
            client_id=client_id
        )
        
        await self._send_message(client_id, response)
    
    async def _handle_get_data(self, client_id: str, message: dict):
        """Handle data request."""
        channel = message.get("channel")
        timeframe = message.get("timeframe", "1h")
        
        try:
            channel_enum = SubscriptionChannel(channel)
        except ValueError:
            await self._send_error(client_id, f"Invalid channel: {channel}")
            return
        
        data = await self._get_channel_data(channel_enum, timeframe)
        
        response = WebSocketMessage(
            type="data_response",
            channel=channel,
            data=data,
            timestamp=datetime.now(),
            client_id=client_id
        )
        
        await self._send_message(client_id, response)
    
    async def _handle_ping(self, client_id: str, message: dict):
        """Handle ping request."""
        response = WebSocketMessage(
            type="pong",
            channel="system",
            data={
                "server_time": datetime.now().isoformat(),
                "client_time": message.get("client_time")
            },
            timestamp=datetime.now(),
            client_id=client_id
        )
        
        await self._send_message(client_id, response)
    
    async def _handle_set_filters(self, client_id: str, message: dict):
        """Handle filter update."""
        filters = message.get("filters", {})
        
        subscription = self.subscriptions.get(client_id)
        if subscription:
            subscription.filters = filters
        
        response = WebSocketMessage(
            type="filters_updated",
            channel="system",
            data={"filters": filters},
            timestamp=datetime.now(),
            client_id=client_id
        )
        
        await self._send_message(client_id, response)
    
    async def _send_initial_data(self, client_id: str, channels: Set[SubscriptionChannel]):
        """Send initial data for subscribed channels."""
        for channel in channels:
            data = await self._get_channel_data(channel)
            
            message = WebSocketMessage(
                type="initial_data",
                channel=channel.value,
                data=data,
                timestamp=datetime.now(),
                client_id=client_id
            )
            
            await self._send_message(client_id, message)
    
    async def _get_channel_data(self, channel: SubscriptionChannel, timeframe: str = "1h") -> Dict[str, Any]:
        """Get data for specific channel."""
        if channel == SubscriptionChannel.SYSTEM_HEALTH:
            health = self.monitor.get_current_health()
            history = self.monitor.get_health_history(minutes=self._parse_timeframe(timeframe))
            
            return {
                "current": asdict(health) if health else None,
                "history": [asdict(h) for h in history]
            }
        
        elif channel == SubscriptionChannel.OPERATION_METRICS:
            stats = self.monitor.get_operation_stats()
            return {"statistics": stats}
        
        elif channel == SubscriptionChannel.ALERTS:
            alerts = self.dashboard._get_active_alerts()
            return {"alerts": alerts}
        
        elif channel == SubscriptionChannel.PERFORMANCE_TRENDS:
            trends = self.dashboard._get_performance_trends()
            return {"trends": trends}
        
        elif channel == SubscriptionChannel.ALL:
            # Get data from all channels
            all_data = {}
            for ch in [SubscriptionChannel.SYSTEM_HEALTH, SubscriptionChannel.OPERATION_METRICS, 
                      SubscriptionChannel.ALERTS, SubscriptionChannel.PERFORMANCE_TRENDS]:
                all_data[ch.value] = await self._get_channel_data(ch, timeframe)
            return all_data
        
        return {}
    
    def _parse_timeframe(self, timeframe: str) -> int:
        """Parse timeframe string to minutes."""
        if timeframe.endswith('m'):
            return int(timeframe[:-1])
        elif timeframe.endswith('h'):
            return int(timeframe[:-1]) * 60
        elif timeframe.endswith('d'):
            return int(timeframe[:-1]) * 1440
        else:
            return 60  # Default 1 hour
    
    async def _broadcast_loop(self):
        """Main broadcast loop for real-time updates."""
        while self.is_running:
            try:
                # Get current data
                current_health = self.monitor.get_current_health()
                current_stats = self.monitor.get_operation_stats()
                
                if current_health:
                    # Broadcast system health updates
                    await self._broadcast_to_channel(
                        SubscriptionChannel.SYSTEM_HEALTH,
                        "health_update",
                        {
                            "timestamp": current_health.timestamp.isoformat(),
                            "cpu_usage": current_health.cpu_usage,
                            "memory_usage": current_health.memory_usage,
                            "disk_usage": current_health.disk_usage,
                            "active_operations": current_health.active_operations,
                            "queue_length": current_health.queue_length,
                            "response_time_avg": current_health.response_time_avg,
                            "error_rate": current_health.error_rate
                        }
                    )
                
                # Broadcast operation metrics
                await self._broadcast_to_channel(
                    SubscriptionChannel.OPERATION_METRICS,
                    "metrics_update",
                    current_stats
                )
                
                await asyncio.sleep(5)  # Broadcast every 5 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in broadcast loop: {e}")
                await asyncio.sleep(5)
    
    async def _cleanup_loop(self):
        """Cleanup loop for inactive connections."""
        while self.is_running:
            try:
                now = datetime.now()
                inactive_clients = []
                
                for client_id, subscription in self.subscriptions.items():
                    # Check if connection is still alive
                    if client_id not in self.active_connections:
                        inactive_clients.append(client_id)
                        continue
                    
                    # Check for inactive connections (no updates for 5 minutes)
                    if now - subscription.last_update > timedelta(minutes=5):
                        try:
                            websocket = self.active_connections[client_id]
                            await websocket.ping()
                        except:
                            inactive_clients.append(client_id)
                
                # Clean up inactive clients
                for client_id in inactive_clients:
                    await self.disconnect_client(client_id)
                
                await asyncio.sleep(60)  # Check every minute
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(60)
    
    async def _broadcast_to_channel(self, channel: SubscriptionChannel, message_type: str, data: Any):
        """Broadcast message to all clients subscribed to channel."""
        message = WebSocketMessage(
            type=message_type,
            channel=channel.value,
            data=data,
            timestamp=datetime.now(),
            message_id=str(uuid.uuid4())
        )
        
        # Find subscribers
        subscribers = [
            client_id for client_id, subscription in self.subscriptions.items()
            if (channel in subscription.channels or SubscriptionChannel.ALL in subscription.channels)
        ]
        
        # Apply filters and send
        for client_id in subscribers:
            subscription = self.subscriptions[client_id]
            
            # Apply filters
            if self._should_send_message(subscription, message):
                await self._send_message(client_id, message)
    
    def _should_send_message(self, subscription: ClientSubscription, message: WebSocketMessage) -> bool:
        """Check if message should be sent based on filters."""
        filters = subscription.filters
        
        if not filters:
            return True
        
        # Apply various filters
        if "min_cpu_threshold" in filters:
            if (message.channel == "system_health" and 
                isinstance(message.data, dict) and 
                message.data.get("cpu_usage", 0) < filters["min_cpu_threshold"]):
                return False
        
        if "operation_types" in filters:
            if (message.channel == "operation_metrics" and 
                isinstance(message.data, dict)):
                # Filter based on operation types
                allowed_types = set(filters["operation_types"])
                ops_by_type = message.data.get("operations_by_type", {})
                if not any(op_type in allowed_types for op_type in ops_by_type.keys()):
                    return False
        
        if "alert_severity" in filters:
            if (message.channel == "alerts" and 
                isinstance(message.data, dict)):
                min_severity = filters["alert_severity"]
                severity_order = {"info": 0, "warning": 1, "critical": 2}
                alerts = message.data.get("alerts", [])
                
                # Filter alerts by minimum severity
                filtered_alerts = [
                    alert for alert in alerts
                    if severity_order.get(alert.get("severity", "info"), 0) >= severity_order.get(min_severity, 0)
                ]
                
                if not filtered_alerts:
                    return False
                
                # Update message data with filtered alerts
                message.data = {**message.data, "alerts": filtered_alerts}
        
        return True
    
    async def _send_message(self, client_id: str, message: WebSocketMessage):
        """Send message to specific client."""
        if client_id not in self.active_connections:
            return
        
        websocket = self.active_connections[client_id]
        subscription = self.subscriptions.get(client_id)
        
        try:
            # Rate limiting check
            if subscription and not self.rate_limiter.is_allowed(subscription):
                return
            
            message_dict = {
                "type": message.type,
                "channel": message.channel,
                "data": message.data,
                "timestamp": message.timestamp.isoformat(),
                "message_id": message.message_id
            }
            
            await websocket.send_text(json.dumps(message_dict, default=str))
            
            if subscription:
                subscription.message_count += 1
                subscription.last_update = datetime.now()
            
        except Exception as e:
            logger.error(f"Error sending message to {client_id}: {e}")
            await self.disconnect_client(client_id)
    
    async def _send_error(self, client_id: str, error_message: str):
        """Send error message to client."""
        error_msg = WebSocketMessage(
            type="error",
            channel="system",
            data={"error": error_message},
            timestamp=datetime.now(),
            client_id=client_id
        )
        
        await self._send_message(client_id, error_msg)
    
    async def _handle_alert(self, alert: Dict[str, Any]):
        """Handle alert from monitoring system."""
        await self._broadcast_to_channel(
            SubscriptionChannel.ALERTS,
            "new_alert",
            alert
        )
    
    async def _handle_metric_update(self, health: SystemHealth):
        """Handle metric update from monitoring system."""
        await self._broadcast_to_channel(
            SubscriptionChannel.SYSTEM_HEALTH,
            "metric_update",
            asdict(health)
        )
    
    def get_service_stats(self) -> Dict[str, Any]:
        """Get service statistics."""
        now = datetime.now()
        
        return {
            "active_connections": len(self.active_connections),
            "total_subscriptions": len(self.subscriptions),
            "is_running": self.is_running,
            "connections_by_channel": {
                channel.value: len([
                    s for s in self.subscriptions.values()
                    if channel in s.channels or SubscriptionChannel.ALL in s.channels
                ])
                for channel in SubscriptionChannel
            },
            "average_connection_time": (
                sum((now - s.connection_time).total_seconds() for s in self.subscriptions.values()) /
                max(len(self.subscriptions), 1)
            ),
            "total_messages_sent": sum(s.message_count for s in self.subscriptions.values()),
            "rate_limit_config": {
                "max_messages": self.rate_limiter.max_messages,
                "window_seconds": self.rate_limiter.window_seconds
            }
        }


# Global service instance
_realtime_service: Optional[RealtimeWebSocketService] = None


def get_realtime_service() -> RealtimeWebSocketService:
    """Get global real-time WebSocket service instance."""
    global _realtime_service
    if _realtime_service is None:
        _realtime_service = RealtimeWebSocketService()
    return _realtime_service


async def start_realtime_service():
    """Start global real-time service."""
    service = get_realtime_service()
    await service.start_service()


async def stop_realtime_service():
    """Stop global real-time service."""
    global _realtime_service
    if _realtime_service:
        await _realtime_service.stop_service()
        _realtime_service = None


if __name__ == "__main__":
    # Example usage
    async def main():
        service = RealtimeWebSocketService()
        await service.start_service()
        
        print("WebSocket service started")
        print(f"Service stats: {service.get_service_stats()}")
        
        # Keep running
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            await service.stop_service()
            print("Service stopped")
    
    asyncio.run(main())