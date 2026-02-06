# ChromaDB startup in offline/DNS-broken environments

When the container has no working DNS (e.g. internal-only network), the ChromaDB image `chromadb/chroma:0.4.22` still attempts a runtime `pip install chroma-hnswlib` for architecture compatibility. That fails after retries (~60–90s) but is non-fatal; ChromaDB then starts Uvicorn. The delay causes slow and flaky health on restarts.

## Approach taken: Option A — DNS in Compose

We add `dns: [1.1.1.1, 8.8.8.8]` to the `chromadb` service in:

- `docker-compose.yml`
- `docker-compose.chromadb.yml`

So the container can resolve PyPI; the optional pip step succeeds or fails quickly, and time-to-healthy drops from ~3 minutes to ~30 seconds.

### Tradeoffs

| Option | Pros | Cons |
|--------|------|------|
| **A: DNS (1.1.1.1, 8.8.8.8)** | Minimal change; no image upgrade; works in air-gapped setups that allow outbound DNS to these IPs. | Container uses external DNS; in strictly offline environments you may need host DNS or a local mirror. |
| **B: Newer Chroma image** | Removes runtime pip dependency; no external DNS needed if image is self-contained. | Requires picking a chromadb image that no longer does runtime pip installs; needs version/regression testing; deferred until after M2. |

**Recommendation:** Keep Option A for M2. Revisit Option B (pin a newer chromadb image that doesn’t do runtime pip installs) if you need fully offline startup or want to remove external DNS.

## Verification

1. **Restart ChromaDB**
   ```bash
   docker compose rm -sf chromadb
   docker compose up -d chromadb
   ```

2. **Time to healthy**
   - With DNS: chromadb should report `(healthy)` within ~30–60s.
   - Without DNS (revert `dns`): expect ~2–3 minutes and possible flakiness.

3. **Check health**
   ```bash
   docker compose ps chromadb
   ./scripts/doctor.sh
   ```

4. **Optional — confirm heartbeat**
   ```bash
   docker compose exec chromadb curl -fsS http://localhost:8000/api/v1/heartbeat
   ```
