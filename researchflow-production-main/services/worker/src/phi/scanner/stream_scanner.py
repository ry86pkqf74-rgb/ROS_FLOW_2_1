"""Streaming PHI scan for large inputs.

This scanner processes large strings by chunking and scanning incrementally.
For true file streaming, callers should provide chunk iterators.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from src.phi.scanner.batch_scanner import HybridDetector


class StreamScanConfig(BaseModel):
    sensitivity: str = Field(default="high")
    allowlist: List[str] = Field(default_factory=list)
    chunk_size: int = Field(default=1024 * 256, ge=4096)  # 256KB
    overlap: int = Field(default=256, ge=0, le=8192)


class StreamScanResult(BaseModel):
    total_bytes: int
    chunks: int
    flagged_chunks: int
    kinds: List[str]


class StreamScanner:
    def __init__(self):
        self._detector = HybridDetector()

    async def scan_text(self, text: str, config: StreamScanConfig) -> StreamScanResult:
        b = text.encode("utf-8", errors="ignore")
        total_bytes = len(b)
        if total_bytes == 0:
            return StreamScanResult(total_bytes=0, chunks=0, flagged_chunks=0, kinds=[])

        step = max(1, config.chunk_size - config.overlap)
        chunks = int(math.ceil(total_bytes / step))
        flagged_chunks = 0
        kinds_set = set()

        # operate on string slices by byte offsets (approx: decode each chunk)
        for i in range(0, total_bytes, step):
            chunk_b = b[i : i + config.chunk_size]
            chunk = chunk_b.decode("utf-8", errors="ignore")
            dets = await self._detector.detect(chunk, sensitivity=config.sensitivity, allowlist=config.allowlist)
            if dets:
                flagged_chunks += 1
                kinds_set.update(d.kind for d in dets)

        return StreamScanResult(
            total_bytes=total_bytes,
            chunks=chunks,
            flagged_chunks=flagged_chunks,
            kinds=sorted(kinds_set),
        )
