"""
Analytics Database Integration
=============================

Database persistence layer for analytics data including:
- Historical metrics storage
- Prediction history
- Performance trends
- Long-term analytics data
"""

import asyncio
import asyncpg
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import asdict
import logging

from ..monitoring.real_time_monitor import SystemHealth, PerformanceMetric, OptimizationOperation
from ..predictive_modeling.size_predictor import SizePrediction, ManuscriptFeatures
from ...config import get_config

logger = logging.getLogger(__name__)


class AnalyticsDatabase:
    """Database integration for analytics data persistence."""
    
    def __init__(self, connection_url: Optional[str] = None):
        self.connection_url = connection_url or get_config().database_url
        self.connection_pool = None
        
    async def initialize(self):
        """Initialize database connection pool and create tables."""
        try:
            self.connection_pool = await asyncpg.create_pool(
                self.connection_url,
                min_size=5,
                max_size=20,
                command_timeout=30
            )
            
            await self._create_tables()
            logger.info("Analytics database initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize analytics database: {e}")
            raise
    
    async def close(self):
        """Close database connection pool."""
        if self.connection_pool:
            await self.connection_pool.close()
            logger.info("Analytics database connection closed")
    
    async def _create_tables(self):
        """Create analytics database tables if they don't exist."""
        async with self.connection_pool.acquire() as connection:
            # System health metrics table
            await connection.execute("""
                CREATE TABLE IF NOT EXISTS analytics_system_health (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
                    cpu_usage FLOAT NOT NULL,
                    memory_usage FLOAT NOT NULL,
                    disk_usage FLOAT NOT NULL,
                    active_operations INTEGER NOT NULL,
                    queue_length INTEGER NOT NULL,
                    response_time_avg FLOAT NOT NULL,
                    error_rate FLOAT NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
            """)
            
            # Performance metrics table
            await connection.execute("""
                CREATE TABLE IF NOT EXISTS analytics_performance_metrics (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
                    metric_name VARCHAR(255) NOT NULL,
                    value FLOAT NOT NULL,
                    unit VARCHAR(50),
                    operation_id VARCHAR(255),
                    component VARCHAR(255),
                    tags JSONB,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
            """)
            
            # Optimization operations table
            await connection.execute("""
                CREATE TABLE IF NOT EXISTS analytics_operations (
                    id SERIAL PRIMARY KEY,
                    operation_id VARCHAR(255) UNIQUE NOT NULL,
                    operation_type VARCHAR(100) NOT NULL,
                    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
                    end_time TIMESTAMP WITH TIME ZONE,
                    status VARCHAR(50) NOT NULL,
                    input_size BIGINT NOT NULL,
                    output_size BIGINT,
                    compression_ratio FLOAT,
                    processing_time FLOAT,
                    resource_usage JSONB,
                    error_message TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
            """)
            
            # Size predictions table
            await connection.execute("""
                CREATE TABLE IF NOT EXISTS analytics_size_predictions (
                    id SERIAL PRIMARY KEY,
                    prediction_id VARCHAR(255) UNIQUE NOT NULL,
                    manuscript_data JSONB NOT NULL,
                    predicted_size_bytes BIGINT NOT NULL,
                    confidence_score FLOAT NOT NULL,
                    predicted_compression_ratio FLOAT NOT NULL,
                    estimated_processing_time FLOAT NOT NULL,
                    recommended_compression_level VARCHAR(20) NOT NULL,
                    size_breakdown JSONB NOT NULL,
                    prediction_factors JSONB NOT NULL,
                    actual_size_bytes BIGINT,
                    actual_compression_ratio FLOAT,
                    actual_processing_time FLOAT,
                    accuracy_score FLOAT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
            """)
            
            # Create indexes for better query performance
            await connection.execute("""
                CREATE INDEX IF NOT EXISTS idx_system_health_timestamp 
                ON analytics_system_health (timestamp);
            """)
            
            await connection.execute("""
                CREATE INDEX IF NOT EXISTS idx_performance_metrics_timestamp_name 
                ON analytics_performance_metrics (timestamp, metric_name);
            """)
            
            await connection.execute("""
                CREATE INDEX IF NOT EXISTS idx_operations_start_time 
                ON analytics_operations (start_time);
            """)
            
            await connection.execute("""
                CREATE INDEX IF NOT EXISTS idx_operations_operation_type 
                ON analytics_operations (operation_type);
            """)
            
            await connection.execute("""
                CREATE INDEX IF NOT EXISTS idx_predictions_created_at 
                ON analytics_size_predictions (created_at);
            """)
    
    async def store_system_health(self, health: SystemHealth) -> int:
        """Store system health data."""
        async with self.connection_pool.acquire() as connection:
            result = await connection.fetchrow("""
                INSERT INTO analytics_system_health 
                (timestamp, cpu_usage, memory_usage, disk_usage, active_operations, 
                 queue_length, response_time_avg, error_rate)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING id
            """, health.timestamp, health.cpu_usage, health.memory_usage, 
                health.disk_usage, health.active_operations, health.queue_length,
                health.response_time_avg, health.error_rate)
            
            return result['id']
    
    async def store_performance_metric(self, metric: PerformanceMetric) -> int:
        """Store performance metric."""
        async with self.connection_pool.acquire() as connection:
            result = await connection.fetchrow("""
                INSERT INTO analytics_performance_metrics 
                (timestamp, metric_name, value, unit, operation_id, component, tags)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING id
            """, metric.timestamp, metric.metric_name, metric.value, metric.unit,
                metric.operation_id, metric.component, json.dumps(metric.tags) if metric.tags else None)
            
            return result['id']
    
    async def store_operation(self, operation: OptimizationOperation) -> int:
        """Store optimization operation."""
        async with self.connection_pool.acquire() as connection:
            result = await connection.fetchrow("""
                INSERT INTO analytics_operations 
                (operation_id, operation_type, start_time, end_time, status, input_size,
                 output_size, compression_ratio, processing_time, resource_usage, error_message)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                ON CONFLICT (operation_id) 
                DO UPDATE SET
                    end_time = EXCLUDED.end_time,
                    status = EXCLUDED.status,
                    output_size = EXCLUDED.output_size,
                    compression_ratio = EXCLUDED.compression_ratio,
                    processing_time = EXCLUDED.processing_time,
                    resource_usage = EXCLUDED.resource_usage,
                    error_message = EXCLUDED.error_message
                RETURNING id
            """, operation.operation_id, operation.operation_type, operation.start_time,
                operation.end_time, operation.status, operation.input_size,
                operation.output_size, operation.compression_ratio, operation.processing_time,
                json.dumps(operation.resource_usage), operation.error_message)
            
            return result['id']
    
    async def store_size_prediction(self, 
                                  prediction_id: str,
                                  manuscript_data: Dict[str, Any],
                                  prediction: SizePrediction) -> int:
        """Store size prediction."""
        async with self.connection_pool.acquire() as connection:
            result = await connection.fetchrow("""
                INSERT INTO analytics_size_predictions 
                (prediction_id, manuscript_data, predicted_size_bytes, confidence_score,
                 predicted_compression_ratio, estimated_processing_time, 
                 recommended_compression_level, size_breakdown, prediction_factors)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                RETURNING id
            """, prediction_id, json.dumps(manuscript_data), prediction.predicted_size_bytes,
                prediction.confidence_score, prediction.predicted_compression_ratio,
                prediction.estimated_processing_time, prediction.recommended_compression_level,
                json.dumps(prediction.size_breakdown), json.dumps(prediction.prediction_factors))
            
            return result['id']
    
    async def update_prediction_actual(self, 
                                     prediction_id: str,
                                     actual_size: int,
                                     actual_compression_ratio: float,
                                     actual_processing_time: float):
        """Update prediction with actual results and calculate accuracy."""
        async with self.connection_pool.acquire() as connection:
            # Get the original prediction
            prediction_row = await connection.fetchrow("""
                SELECT predicted_size_bytes, confidence_score 
                FROM analytics_size_predictions 
                WHERE prediction_id = $1
            """, prediction_id)
            
            if not prediction_row:
                raise ValueError(f"Prediction {prediction_id} not found")
            
            # Calculate accuracy score
            predicted_size = prediction_row['predicted_size_bytes']
            size_error = abs(predicted_size - actual_size) / actual_size
            accuracy_score = max(0, 1 - size_error)  # Simple accuracy metric
            
            # Update the prediction
            await connection.execute("""
                UPDATE analytics_size_predictions 
                SET actual_size_bytes = $2,
                    actual_compression_ratio = $3,
                    actual_processing_time = $4,
                    accuracy_score = $5
                WHERE prediction_id = $1
            """, prediction_id, actual_size, actual_compression_ratio, 
                actual_processing_time, accuracy_score)
    
    async def get_system_health_history(self, 
                                      start_time: datetime,
                                      end_time: datetime,
                                      interval_minutes: int = 5) -> List[Dict[str, Any]]:
        """Get system health history with optional aggregation."""
        async with self.connection_pool.acquire() as connection:
            if interval_minutes > 1:
                # Aggregate data by interval
                query = """
                    SELECT 
                        date_trunc('minute', timestamp - interval '%d minutes' * (extract(minute from timestamp)::integer %% %d)) as interval_start,
                        AVG(cpu_usage) as avg_cpu_usage,
                        AVG(memory_usage) as avg_memory_usage,
                        AVG(disk_usage) as avg_disk_usage,
                        AVG(active_operations) as avg_active_operations,
                        AVG(queue_length) as avg_queue_length,
                        AVG(response_time_avg) as avg_response_time,
                        AVG(error_rate) as avg_error_rate,
                        COUNT(*) as data_points
                    FROM analytics_system_health 
                    WHERE timestamp BETWEEN $1 AND $2
                    GROUP BY interval_start
                    ORDER BY interval_start
                """ % (interval_minutes, interval_minutes)
            else:
                # Return raw data
                query = """
                    SELECT * FROM analytics_system_health 
                    WHERE timestamp BETWEEN $1 AND $2
                    ORDER BY timestamp
                """
            
            rows = await connection.fetch(query, start_time, end_time)
            return [dict(row) for row in rows]
    
    async def get_operation_statistics(self, 
                                     start_time: datetime,
                                     end_time: datetime) -> Dict[str, Any]:
        """Get operation statistics for time period."""
        async with self.connection_pool.acquire() as connection:
            # Basic statistics
            basic_stats = await connection.fetchrow("""
                SELECT 
                    COUNT(*) as total_operations,
                    COUNT(*) FILTER (WHERE status = 'completed') as completed_operations,
                    COUNT(*) FILTER (WHERE status = 'failed') as failed_operations,
                    AVG(processing_time) FILTER (WHERE processing_time IS NOT NULL) as avg_processing_time,
                    AVG(compression_ratio) FILTER (WHERE compression_ratio IS NOT NULL) as avg_compression_ratio
                FROM analytics_operations 
                WHERE start_time BETWEEN $1 AND $2
            """, start_time, end_time)
            
            # Operations by type
            type_stats = await connection.fetch("""
                SELECT 
                    operation_type,
                    COUNT(*) as count,
                    COUNT(*) FILTER (WHERE status = 'completed') as completed,
                    AVG(processing_time) FILTER (WHERE processing_time IS NOT NULL) as avg_time
                FROM analytics_operations 
                WHERE start_time BETWEEN $1 AND $2
                GROUP BY operation_type
                ORDER BY count DESC
            """, start_time, end_time)
            
            # Hourly distribution
            hourly_stats = await connection.fetch("""
                SELECT 
                    date_trunc('hour', start_time) as hour,
                    COUNT(*) as operations,
                    AVG(processing_time) FILTER (WHERE processing_time IS NOT NULL) as avg_time
                FROM analytics_operations 
                WHERE start_time BETWEEN $1 AND $2
                GROUP BY hour
                ORDER BY hour
            """, start_time, end_time)
            
            return {
                "basic_stats": dict(basic_stats) if basic_stats else {},
                "by_type": [dict(row) for row in type_stats],
                "hourly_distribution": [dict(row) for row in hourly_stats]
            }
    
    async def get_prediction_analytics(self, 
                                     start_time: datetime,
                                     end_time: datetime) -> Dict[str, Any]:
        """Get prediction analytics and accuracy metrics."""
        async with self.connection_pool.acquire() as connection:
            # Basic prediction stats
            basic_stats = await connection.fetchrow("""
                SELECT 
                    COUNT(*) as total_predictions,
                    AVG(confidence_score) as avg_confidence,
                    AVG(accuracy_score) FILTER (WHERE accuracy_score IS NOT NULL) as avg_accuracy,
                    COUNT(*) FILTER (WHERE actual_size_bytes IS NOT NULL) as predictions_with_actuals
                FROM analytics_size_predictions 
                WHERE created_at BETWEEN $1 AND $2
            """, start_time, end_time)
            
            # Accuracy by confidence buckets
            accuracy_by_confidence = await connection.fetch("""
                SELECT 
                    CASE 
                        WHEN confidence_score >= 0.9 THEN 'high'
                        WHEN confidence_score >= 0.7 THEN 'medium'
                        ELSE 'low'
                    END as confidence_bucket,
                    COUNT(*) as predictions,
                    AVG(accuracy_score) FILTER (WHERE accuracy_score IS NOT NULL) as avg_accuracy
                FROM analytics_size_predictions 
                WHERE created_at BETWEEN $1 AND $2
                GROUP BY confidence_bucket
            """, start_time, end_time)
            
            # Size prediction distribution
            size_distribution = await connection.fetch("""
                SELECT 
                    CASE 
                        WHEN predicted_size_bytes < 1048576 THEN 'small'  -- < 1MB
                        WHEN predicted_size_bytes < 10485760 THEN 'medium'  -- < 10MB
                        ELSE 'large'  -- >= 10MB
                    END as size_bucket,
                    COUNT(*) as predictions,
                    AVG(accuracy_score) FILTER (WHERE accuracy_score IS NOT NULL) as avg_accuracy
                FROM analytics_size_predictions 
                WHERE created_at BETWEEN $1 AND $2
                GROUP BY size_bucket
            """, start_time, end_time)
            
            return {
                "basic_stats": dict(basic_stats) if basic_stats else {},
                "accuracy_by_confidence": [dict(row) for row in accuracy_by_confidence],
                "size_distribution": [dict(row) for row in size_distribution]
            }
    
    async def get_performance_trends(self, 
                                   metric_names: List[str],
                                   start_time: datetime,
                                   end_time: datetime,
                                   interval_minutes: int = 60) -> Dict[str, List[Dict[str, Any]]]:
        """Get performance trends for specific metrics."""
        async with self.connection_pool.acquire() as connection:
            trends = {}
            
            for metric_name in metric_names:
                query = """
                    SELECT 
                        date_trunc('minute', timestamp - interval '%d minutes' * (extract(minute from timestamp)::integer %% %d)) as interval_start,
                        AVG(value) as avg_value,
                        MIN(value) as min_value,
                        MAX(value) as max_value,
                        COUNT(*) as data_points
                    FROM analytics_performance_metrics 
                    WHERE metric_name = $1 AND timestamp BETWEEN $2 AND $3
                    GROUP BY interval_start
                    ORDER BY interval_start
                """ % (interval_minutes, interval_minutes)
                
                rows = await connection.fetch(query, metric_name, start_time, end_time)
                trends[metric_name] = [dict(row) for row in rows]
            
            return trends
    
    async def cleanup_old_data(self, retention_days: int = 90):
        """Clean up old analytics data beyond retention period."""
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        
        async with self.connection_pool.acquire() as connection:
            # Clean up old system health data
            health_deleted = await connection.fetchval("""
                DELETE FROM analytics_system_health 
                WHERE created_at < $1
                RETURNING COUNT(*)
            """, cutoff_date)
            
            # Clean up old performance metrics
            metrics_deleted = await connection.fetchval("""
                DELETE FROM analytics_performance_metrics 
                WHERE created_at < $1
                RETURNING COUNT(*)
            """, cutoff_date)
            
            # Clean up old operations (keep longer for analysis)
            operations_cutoff = datetime.now() - timedelta(days=retention_days * 2)
            operations_deleted = await connection.fetchval("""
                DELETE FROM analytics_operations 
                WHERE created_at < $1
                RETURNING COUNT(*)
            """, operations_cutoff)
            
            logger.info(f"Cleanup completed: {health_deleted} health records, "
                       f"{metrics_deleted} metric records, {operations_deleted} operations deleted")
    
    async def export_data(self, 
                         start_time: datetime,
                         end_time: datetime,
                         table_names: Optional[List[str]] = None) -> Dict[str, List[Dict[str, Any]]]:
        """Export analytics data for external analysis."""
        if table_names is None:
            table_names = [
                'analytics_system_health',
                'analytics_performance_metrics', 
                'analytics_operations',
                'analytics_size_predictions'
            ]
        
        export_data = {}
        
        async with self.connection_pool.acquire() as connection:
            for table_name in table_names:
                if table_name == 'analytics_system_health':
                    rows = await connection.fetch("""
                        SELECT * FROM analytics_system_health 
                        WHERE timestamp BETWEEN $1 AND $2
                        ORDER BY timestamp
                    """, start_time, end_time)
                
                elif table_name == 'analytics_performance_metrics':
                    rows = await connection.fetch("""
                        SELECT * FROM analytics_performance_metrics 
                        WHERE timestamp BETWEEN $1 AND $2
                        ORDER BY timestamp
                    """, start_time, end_time)
                
                elif table_name == 'analytics_operations':
                    rows = await connection.fetch("""
                        SELECT * FROM analytics_operations 
                        WHERE start_time BETWEEN $1 AND $2
                        ORDER BY start_time
                    """, start_time, end_time)
                
                elif table_name == 'analytics_size_predictions':
                    rows = await connection.fetch("""
                        SELECT * FROM analytics_size_predictions 
                        WHERE created_at BETWEEN $1 AND $2
                        ORDER BY created_at
                    """, start_time, end_time)
                
                export_data[table_name] = [dict(row) for row in rows]
        
        return export_data


# Global database instance
_analytics_db: Optional[AnalyticsDatabase] = None


async def get_analytics_db() -> AnalyticsDatabase:
    """Get global analytics database instance."""
    global _analytics_db
    if _analytics_db is None:
        _analytics_db = AnalyticsDatabase()
        await _analytics_db.initialize()
    return _analytics_db


async def close_analytics_db():
    """Close global analytics database connection."""
    global _analytics_db
    if _analytics_db:
        await _analytics_db.close()
        _analytics_db = None


# Context manager for database operations
class AnalyticsDBContext:
    """Context manager for analytics database operations."""
    
    def __init__(self):
        self.db = None
    
    async def __aenter__(self) -> AnalyticsDatabase:
        self.db = await get_analytics_db()
        return self.db
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Don't close the global connection, just release
        pass


if __name__ == "__main__":
    # Example usage
    import asyncio
    
    async def main():
        db = AnalyticsDatabase()
        await db.initialize()
        
        # Example system health storage
        health = SystemHealth(
            timestamp=datetime.now(),
            cpu_usage=45.2,
            memory_usage=68.7,
            disk_usage=23.1,
            active_operations=5,
            queue_length=2,
            response_time_avg=1.2,
            error_rate=0.5
        )
        
        health_id = await db.store_system_health(health)
        print(f"Stored system health with ID: {health_id}")
        
        # Get recent health history
        start_time = datetime.now() - timedelta(hours=1)
        end_time = datetime.now()
        
        history = await db.get_system_health_history(start_time, end_time)
        print(f"Retrieved {len(history)} health records")
        
        await db.close()
    
    asyncio.run(main())