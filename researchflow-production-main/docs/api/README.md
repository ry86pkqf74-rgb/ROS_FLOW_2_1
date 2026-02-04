# ResearchFlow API

This directory contains a generated OpenAPI specification and a Postman collection for the ResearchFlow orchestrator API.

## Files

- `openapi.yaml` — OpenAPI 3.0 specification
- `researchflow.postman_collection.json` — Postman collection

## Base URL

All paths below are relative to `{{baseUrl}}` (e.g. `http://localhost:3001`).

## Authentication

- Uses **Bearer JWT**: `Authorization: Bearer {{token}}`
- Auth endpoints under `/api/auth/*` are documented as unauthenticated.

## Rate limiting

Rate limiting is recommended. If enabled, clients should handle `429 Too Many Requests` and respect `Retry-After`.

## Error format

Errors are returned as JSON. Typical shape (may vary by route):

- `error`: short error string
- `code`: optional machine-readable code
- `message`: optional human-readable message

## Endpoint overview (first 200)

| Method | Path | Source |
|---|---|---|
| `GET` | `/api/ai/agent-proxy/health` | `ai-agent-proxy.ts` |
| `POST` | `/api/ai/agent-proxy/` | `ai-agent-proxy.ts` |
| `POST` | `/api/ai/agent-proxy/estimate` | `ai-agent-proxy.ts` |
| `GET` | `/api/ai/agent-proxy/task-types` | `ai-agent-proxy.ts` |

## Examples

### cURL

```bash
curl -sS "$BASE_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\": \"user@example.com\", \"password\": \"...\"}"
```

### Python (requests)

```python
import requests

base_url = "http://localhost:3001"
token = "..."

r = requests.get(f"{base_url}/api/analytics/summary", headers={"Authorization": f"Bearer {token}"})
print(r.status_code, r.json())
```

### JavaScript (fetch)

```javascript
const baseUrl = "http://localhost:3001";
const token = "...";

const res = await fetch(`${baseUrl}/api/analytics/summary`, {
  headers: { Authorization: `Bearer ${token}` },
});
console.log(res.status, await res.json());
```
