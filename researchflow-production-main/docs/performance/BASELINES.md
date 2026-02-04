# Performance Baselines

These baselines define the current performance targets for key user-facing API endpoints.

## Latency targets (p95)

| Endpoint | Target p95 |
|----------|------------|
| GET /api/projects | <100ms |
| POST /api/workflow/stage | <500ms |
| GET /api/documents/:id | <50ms |
| POST /api/auth/login | <200ms |

## Throughput targets

- Sustained: **1000 req/min**
- Burst: **5000 req/min for 30s**

## Notes

- Targets are measured at the API boundary (ingress / gateway), excluding client-side rendering.
- Use consistent environment and dataset size when updating baselines.
