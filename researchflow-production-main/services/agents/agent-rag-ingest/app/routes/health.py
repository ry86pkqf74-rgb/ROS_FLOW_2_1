import os
from fastapi import APIRouter

router = APIRouter()


def _check_chroma_ready() -> tuple[bool, str]:
    """Verify Chroma connectivity and auth. Returns (ok, detail)."""
    url = os.getenv("CHROMADB_URL", "http://localhost:8000").strip()
    token = os.getenv("CHROMADB_AUTH_TOKEN", "").strip() or None
    try:
        client = _get_chroma_http_client()
        # List collections to verify connectivity and auth
        client.list_collections()
        return True, "chroma_ok"
    except Exception as e:  # noqa: BLE001
        return False, str(e)[:200]


def _get_chroma_http_client():
    """One-off Chroma client for health check (no singleton)."""
    from urllib.parse import urlparse

    import chromadb
    from chromadb.config import Settings

    url = os.getenv("CHROMADB_URL", "http://localhost:8000").strip()
    token = os.getenv("CHROMADB_AUTH_TOKEN", "").strip() or None
    parsed = urlparse(url)
    host = parsed.hostname or "localhost"
    port = parsed.port or (443 if parsed.scheme == "https" else 8000)
    use_ssl = parsed.scheme == "https"

    kwargs = {"host": host, "port": port}
    if use_ssl:
        kwargs["ssl"] = True
    if token:
        kwargs["settings"] = Settings(
            chroma_client_auth_provider="chromadb.auth.token_authn.TokenAuthClientProvider",
            chroma_client_auth_credentials=token,
        )
    return chromadb.HttpClient(**kwargs)


@router.get("/health", summary="Liveness probe")
def health():
    return {"status": "ok", "service": "agent-rag-ingest"}


@router.get("/health/ready", summary="Readiness probe")
def ready():
    """Verify Chroma connectivity and auth."""
    chroma_ok, chroma_detail = _check_chroma_ready()
    status = "ready" if chroma_ok else "not_ready"
    return {
        "status": status,
        "service": "agent-rag-ingest",
        "chromadb_url": os.getenv("CHROMADB_URL", ""),
        "chroma_connected": chroma_ok,
        "chroma_detail": chroma_detail,
    }
