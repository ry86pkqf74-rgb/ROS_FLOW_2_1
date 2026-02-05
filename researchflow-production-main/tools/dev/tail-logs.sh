#!/usr/bin/env bash
docker compose logs -f --tail=100 orchestrator worker agent-stage2-lit 2>&1 | grep -v "healthcheck"
