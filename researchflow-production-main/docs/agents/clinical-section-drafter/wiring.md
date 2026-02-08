# Clinical Section Drafter Agent — Wiring & Deployment Guide

**Agent Type:** LangSmith Cloud (via FastAPI Proxy)  
**Status:** ✅ Deployed (Proxy Architecture)  
**Last Updated:** 2026-02-08

---

## 🎯 Quick Reference

| Property | Value |
|----------|-------|
| **Compose Service** | `agent-section-drafter-proxy` |
| **Container Name** | `researchflow-agent-section-drafter-proxy` |
| **Internal URL** | `http://agent-section-drafter-proxy:8000` |
| **Router Task Type** | `CLINICAL_SECTION_DRAFT` |
| **Health Endpoints** | `/health`, `/health/ready` |
| **Networks** | `backend` (orchestrator), `frontend` (LangSmith API) |
| **Port** | 8000 (internal only) |

---

## 📦 Compose Service

Service is defined in `docker-compose.yml`. Key configuration:

```yaml
agent-section-drafter-proxy:
  build:
    context: .
    dockerfile: services/agents/agent-section-drafter-proxy/Dockerfile
  container_name: researchflow-agent-section-drafter-proxy
  environment:
    - LANGSMITH_API_KEY=${LANGSMITH_API_KEY:-}
    - LANGSMITH_AGENT_ID=${LANGSMITH_SECTION_DRAFTER_AGENT_ID:-}
    - LANGSMITH_TIMEOUT_SECONDS=${LANGSMITH_SECTION_DRAFTER_TIMEOUT_SECONDS:-180}
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

**Task Type:** `CLINICAL_SECTION_DRAFT` → `agent-clinical-section-drafter`

**AGENT_ENDPOINTS_JSON:**
```json
{
  "agent-clinical-section-drafter": "http://agent-section-drafter-proxy:8000"
}
```

---

## ⚙️ Required Environment Variables

```bash
# .env
LANGSMITH_API_KEY=lsv2_pt_...
LANGSMITH_SECTION_DRAFTER_AGENT_ID=<uuid>
LANGSMITH_SECTION_DRAFTER_TIMEOUT_SECONDS=180  # 3 minutes (optional)
```

---

## ✅ Validation

**Preflight:**
```bash
./scripts/hetzner-preflight.sh
```

**Smoke Test:**
```bash
CHECK_SECTION_DRAFTER=1 DEV_AUTH=true ./scripts/stagewise-smoke.sh
```

---

## 🚀 Deployment

```bash
# Build
docker compose build agent-section-drafter-proxy

# Start
docker compose up -d agent-section-drafter-proxy

# Verify
docker compose ps agent-section-drafter-proxy
docker compose exec agent-section-drafter-proxy curl -f http://localhost:8000/health
```

---

## 🔍 Common Issues

**503 Service Unavailable:** Missing `LANGSMITH_API_KEY` or `LANGSMITH_SECTION_DRAFTER_AGENT_ID`

**AGENT_NOT_CONFIGURED:** Missing from `AGENT_ENDPOINTS_JSON` in orchestrator

**Timeout:** Increase `LANGSMITH_SECTION_DRAFTER_TIMEOUT_SECONDS` to 300

---

**Wiring Status:** ✅ **COMPLETE**  
**Deployment Ready:** Yes
