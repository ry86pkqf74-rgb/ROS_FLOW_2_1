"""
Worker and workflow configuration.

Single env-based config for the worker service: stages, bridge URLs,
timeouts, and feature flags. Aligns with workflow_engine.bridge.BridgeConfig.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


def _parse_bool(value: Optional[str], default: bool) -> bool:
    if value is None:
        return default
    v = value.strip().lower()
    if v in {"1", "true", "t", "yes", "y", "on"}:
        return True
    if v in {"0", "false", "f", "no", "n", "off"}:
        return False
    return default


def _parse_int(value: Optional[str], default: int) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _parse_float(value: Optional[str], default: float) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


@dataclass
class WorkerConfig:
    """Environment-based worker and workflow configuration."""

    # Environment / logging
    log_level: str = "INFO"
    log_format: str = "console"  # "console" or "json"
    governance_mode: str = "DEMO"

    # Paths
    artifact_path: str = "/data/artifacts"
    log_path: str = "/data/logs"

    # Orchestrator / bridge (align with workflow_engine.bridge.BridgeConfig)
    orchestrator_url: str = "http://orchestrator:3001"
    bridge_timeout: float = 30.0

    # Redis
    redis_url: str = "redis://localhost:6379"

    # Timeouts
    stage_timeout_seconds: float = 300.0
    stage_timeout_overrides: Dict[int, float] = field(default_factory=dict)

    # Feature flags: enabled stage IDs (empty = all registered stages enabled)
    enabled_stages: Optional[List[int]] = None
    
    # Stage 1 Protocol Design Agent feature flag
    enable_new_stage_1: bool = False

    @classmethod
    def from_env(cls) -> "WorkerConfig":
        """Load configuration from environment variables."""
        log_format = (os.getenv("LOG_FORMAT") or "console").strip().lower()
        if log_format == "json":
            log_fmt = "json"
        else:
            log_fmt = "console"

        # Optional per-stage timeout overrides via env prefix STAGE_N_TIMEOUT_SECONDS
        overrides: Dict[int, float] = {}
        for key, val in os.environ.items():
            if key.startswith("STAGE_") and key.endswith("_TIMEOUT_SECONDS"):
                try:
                    stage_num = int(key.split("_")[1])
                    if 1 <= stage_num <= 20:
                        overrides[stage_num] = float(val)
                except (ValueError, IndexError):
                    pass

        # Optional list of enabled stages (comma-separated); empty/unset = all
        enabled_stages_list: Optional[List[int]] = None
        raw = os.getenv("ENABLED_STAGES")
        if raw and raw.strip():
            try:
                enabled_stages_list = [
                    int(x.strip()) for x in raw.split(",") if x.strip()
                ]
            except ValueError:
                enabled_stages_list = None

        return cls(
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
            log_format=log_fmt,
            governance_mode=os.getenv("GOVERNANCE_MODE", "DEMO"),
            artifact_path=os.getenv("ARTIFACTS_PATH") or os.getenv("ARTIFACT_PATH", "/data/artifacts"),
            log_path=os.getenv("LOG_PATH", "/data/logs"),
            orchestrator_url=os.getenv("ORCHESTRATOR_URL", "http://orchestrator:3001"),
            bridge_timeout=_parse_float(os.getenv("BRIDGE_TIMEOUT"), 30.0),
            redis_url=os.getenv("REDIS_URL", "redis://localhost:6379"),
            stage_timeout_seconds=_parse_float(
                os.getenv("STAGE_TIMEOUT_SECONDS"), 300.0
            ),
            stage_timeout_overrides=overrides,
            enabled_stages=enabled_stages_list,
            enable_new_stage_1=_parse_bool(os.getenv("ENABLE_NEW_STAGE_1"), False),
        )

    def get_stage_timeout(self, stage_id: int) -> float:
        """Return timeout in seconds for a given stage (override or global)."""
        return self.stage_timeout_overrides.get(
            stage_id, self.stage_timeout_seconds
        )

    def is_stage_enabled(self, stage_id: int) -> bool:
        """Return True if the stage is enabled (no filter = all enabled)."""
        if self.enabled_stages is None or len(self.enabled_stages) == 0:
            return True
        return stage_id in self.enabled_stages


# Singleton instance; load once at import
_config: Optional[WorkerConfig] = None


def get_config() -> WorkerConfig:
    """Return the worker config singleton (loads from env on first call)."""
    global _config
    if _config is None:
        _config = WorkerConfig.from_env()
    return _config


def reset_config() -> None:
    """Reset config (for tests)."""
    global _config
    _config = None
