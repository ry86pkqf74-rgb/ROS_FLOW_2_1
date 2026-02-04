"""Shared utility modules used across Research Operating System Template."""

from .template_loader import (
    load_draft_outline_config,
    get_draft_types,
    get_sections_for_type,
    get_required_elements,
    generate_section_prompt,
    RUO_DRAFT_DISCLAIMER,
)

from .keyword_extraction import (
    extract_keywords_tfidf,
    extract_keywords_rake,
    extract_keywords_from_abstracts,
    KeywordResult,
)

# Phase 3: App Integration & Monitoring
from .logging import (
    get_logger,
    bind_context,
    unbind_context,
    log_stage_start,
    log_stage_end,
    configure_logging,
)
from .metrics import (
    record_stage,
    set_queue_depth,
    get_metrics_output,
    get_metrics_content_type,
)
from .error_handler import (
    WorkflowError,
    StageExecutionError,
    StageTimeoutError,
    BridgeUnavailableError,
    RecoverableError,
    push_dlq,
    push_to_dlq,
    get_dlq_snapshot,
    retry_async,
    retry_async_await,
)

__all__ = [
    "load_draft_outline_config",
    "get_draft_types",
    "get_sections_for_type",
    "get_required_elements",
    "generate_section_prompt",
    "RUO_DRAFT_DISCLAIMER",
    # Keyword extraction
    "extract_keywords_tfidf",
    "extract_keywords_rake",
    "extract_keywords_from_abstracts",
    "KeywordResult",
    # Phase 3: logging
    "get_logger",
    "bind_context",
    "unbind_context",
    "log_stage_start",
    "log_stage_end",
    "configure_logging",
    # Phase 3: metrics
    "record_stage",
    "set_queue_depth",
    "get_metrics_output",
    "get_metrics_content_type",
    # Phase 3: error_handler
    "WorkflowError",
    "StageExecutionError",
    "StageTimeoutError",
    "BridgeUnavailableError",
    "RecoverableError",
    "push_dlq",
    "push_to_dlq",
    "get_dlq_snapshot",
    "retry_async",
    "retry_async_await",
]
