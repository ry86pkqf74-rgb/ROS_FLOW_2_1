# Clinical Manuscript Writer Agent — Wiring & Deployment Guide

**Agent Type:** LangSmith Cloud (via FastAPI Proxy)  
**Status:** ✅ Deployed (Proxy Architecture)  
**Last Updated:** 2026-02-08

---

## 🎯 Quick Reference

| Property | Value |
|----------|-------|
| **Compose Service** | `agent-clinical-manuscript-proxy` |
| **Container Name** | `researchflow-agent-clinical-manuscript-proxy` |
| **Internal URL** | `http://agent-clinical-manuscript-proxy:8000` |
| **Router Task Type** | `CLINICAL_MANUSCRIPT_WRITE` |
| **Health Endpoints** | `/health`, `/health/ready` |
| **Networks** | `backend` (orchestrator), `frontend` (LangSmith API) |
| **Port** | 8000 (internal only) |

---

## 📦 Compose Service

Service is defined in `docker-compose.yml`. Key configuration:

```yaml
agent-clinical-manuscript-proxy:
  build:
    context: .
    dockerfile: services/agents/agent-clinical-manuscript-proxy/Dockerfile
  container_name: researchflow-agent-clinical-manuscript-proxy
  environment:
    - LANGSMITH_API_KEY=${LANGSMITH_API_KEY:-}
    - LANGSMITH_AGENT_ID=${LANGSMITH_MANUSCRIPT_AGENT_ID:-}
    - LANGSMITH_TIMEOUT_SECONDS=${LANGSMITH_MANUSCRIPT_TIMEOUT_SECONDS:-300}
  expose:
    - "8000"
  networks:
    - backend
    - frontend
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
```

---

## 🔀 Router Configuration

**Task Type:** `CLINICAL_MANUSCRIPT_WRITE` → `agent-clinical-manuscript`

**AGENT_ENDPOINTS_JSON:**
```json
{
  "agent-clinical-manuscript": "http://agent-clinical-manuscript-proxy:8000"
}
```

---

## ⚙️ Required Environment Variables

```bash
# .env
LANGSMITH_API_KEY=lsv2_pt_...
LANGSMITH_MANUSCRIPT_AGENT_ID=<uuid>
LANGSMITH_MANUSCRIPT_TIMEOUT_SECONDS=300  # 5 minutes (optional)
```

---

## ✅ Validation

**Preflight:**
```bash
./scripts/hetzner-preflight.sh
```

**Smoke Test:**
```bash
CHECK_MANUSCRIPT_WRITER=1 DEV_AUTH=true ./scripts/stagewise-smoke.sh
```

---

## 🚀 Deployment

```bash
# Build
docker compose build agent-clinical-manuscript-proxy

# Start
docker compose up -d agent-clinical-manuscript-proxy

# Verify
docker compose ps agent-clinical-manuscript-proxy
docker compose exec agent-clinical-manuscript-proxy curl -f http://localhost:8000/health
```

---

## 🔍 Common Issues

**503 Service Unavailable:** Missing `LANGSMITH_API_KEY` or `LANGSMITH_MANUSCRIPT_AGENT_ID`

**AGENT_NOT_CONFIGURED:** Missing from `AGENT_ENDPOINTS_JSON` in orchestrator

**Timeout:** Increase `LANGSMITH_MANUSCRIPT_TIMEOUT_SECONDS` to 600

---

**Wiring Status:** ✅ **COMPLETE**  
**Deployment Ready:** Yes
