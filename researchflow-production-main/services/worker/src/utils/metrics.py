"""
Prometheus metrics for workflow stage execution and worker health.

Phase 3: App Integration & Monitoring.
Uses prometheus_client. Export format compatible with Prometheus scraping.
"""

from __future__ import annotations

import os
from typing import Optional

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    CollectorRegistry,
    generate_latest,
    REGISTRY,
)

# Optional: separate registry for workflow metrics to avoid conflicts with existing src.metrics
# Using default REGISTRY so /metrics exposes all; worker can mount this module's output.

STAGE_DURATION = Histogram(
    "researchflow_workflow_stage_duration_seconds",
    "Stage execution duration in seconds",
    ["stage_id", "status"],
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0),
    registry=REGISTRY,
)

STAGE_TOTAL = Counter(
    "researchflow_workflow_stage_total",
    "Total stage executions by stage_id and status",
    ["stage_id", "status"],
    registry=REGISTRY,
)

QUEUE_DEPTH = Gauge(
    "researchflow_workflow_queue_depth",
    "Current depth of the job queue (pending + processing)",
    registry=REGISTRY,
)

MEMORY_BYTES = Gauge(
    "researchflow_worker_memory_bytes",
    "Process memory usage in bytes (RSS)",
    registry=REGISTRY,
)


def record_stage(stage_id: int, status: str, duration_seconds: float) -> None:
    """Record a stage execution for metrics."""
    stage_label = str(stage_id)
    STAGE_TOTAL.labels(stage_id=stage_label, status=status).inc()
    STAGE_DURATION.labels(stage_id=stage_label, status=status).observe(
        duration_seconds
    )


def set_queue_depth(value: float) -> None:
    """Set the current queue depth (pending + processing)."""
    QUEUE_DEPTH.set(value)


def update_memory_metric() -> None:
    """Update the memory gauge with current process RSS (if psutil available)."""
    try:
        import psutil
        process = psutil.Process(os.getpid())
        MEMORY_BYTES.set(float(process.memory_info().rss))
    except Exception:
        pass


def get_metrics_output() -> bytes:
    """Return Prometheus text format for the default registry."""
    update_memory_metric()
    return generate_latest(REGISTRY)


def get_metrics_content_type() -> str:
    """Return the content type for Prometheus scrape response."""
    return CONTENT_TYPE_LATEST


ACTIVE_WORKFLOWS = Gauge(
    'researchflow_active_workflows',
    'Number of workflows currently executing',
    registry=REGISTRY,
)


STAGE_ERRORS = Counter(
    'researchflow_stage_errors_total',
    'Total stage errors by stage_id',
    ['stage_id'],
    registry=REGISTRY,
)
