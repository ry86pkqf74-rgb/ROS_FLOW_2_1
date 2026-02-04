# Load Test Guide

This guide describes how to run load tests (k6 and Artillery), interpret results, and decide when to update performance baselines.

## Prerequisites

- A stable environment (staging or dedicated perf env)
- Representative seed data (projects, documents, users)
- Access to Grafana dashboards and logs

## k6

### Install

- macOS: `brew install k6`
- Linux: follow https://k6.io/docs/get-started/installation/

### Run (example)

Run against an environment URL:

- `BASE_URL=https://staging.example.com k6 run tests/performance/k6/baseline.js`

### What to collect

- HTTP request duration p95/p99
- Error rate (non-2xx)
- Throughput (req/min)

## Artillery

### Install

- `npm i -g artillery`

### Run (example)

- `BASE_URL=https://staging.example.com artillery run tests/performance/artillery/baseline.yml`

### What to collect

- Latency p95
- Error rate
- Requests per second / per minute

## Interpreting results

- **Pass**: p95 for each endpoint is at or below the target baseline and error rate is within expected bounds.
- **Regression**: p95 exceeds target by **>10%** for any tracked endpoint (or sustained error-rate increase).
- **Investigate**: regressions should be correlated with deploy SHAs, DB migrations, and infra changes.

## When to update baselines

Update `docs/performance/BASELINES.md` when:

- A deliberate performance improvement is shipped and validated.
- An accepted product change increases payload sizes and the new performance is the intended steady state.

Do **not** update baselines to “make the pipeline green” without an explicit decision.

## CI automation

The weekly benchmark workflow runs the baseline load test and compares results to baselines. If a regression >10% is detected, the workflow fails and alerts.
