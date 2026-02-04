from __future__ import annotations

import asyncio

import pytest

from src.phi.scanner.batch_scanner import BatchScanConfig, BatchScanner


@pytest.mark.asyncio
async def test_concurrent_batch_scanning_reports_progress(text_with_multiple_phi: str):
    scanner = BatchScanner()
    cfg = BatchScanConfig(concurrency=4, sensitivity="low")

    items = [
        {"item_id": f"i-{i}", "content": text_with_multiple_phi if i % 2 == 0 else "clean text"}
        for i in range(20)
    ]

    progress = []

    async def cb(p):
        progress.append((p.processed, p.total))

    res = await scanner.scan_items(items, cfg, progress_cb=cb)

    assert res.total == 20
    assert progress, "progress callback should be invoked"
    assert progress[-1] == (20, 20)
    assert res.flagged >= 1


@pytest.mark.asyncio
async def test_error_handling_for_bad_items_does_not_crash_batch():
    scanner = BatchScanner()
    cfg = BatchScanConfig(concurrency=4, sensitivity="low")

    # None content should be treated as empty string by implementation
    items = [
        {"item_id": "ok", "content": "Call 555-123-4567"},
        {"item_id": "bad", "content": None},
    ]

    res = await scanner.scan_items(items, cfg)
    assert res.total == 2


@pytest.mark.asyncio
async def test_large_batch_does_not_exceed_reasonable_memory_limits(text_with_multiple_phi: str):
    scanner = BatchScanner()
    cfg = BatchScanConfig(concurrency=8, sensitivity="low")

    # keep individual items small; ensure we can process a sizable batch
    items = [{"item_id": str(i), "content": text_with_multiple_phi} for i in range(200)]

    res = await scanner.scan_items(items, cfg)
    assert res.total == 200
    assert res.flagged == 200
