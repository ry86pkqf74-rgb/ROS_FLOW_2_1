# Documents API

> Base path: `/api`
>
> Authentication: **Bearer token**
>
> Header: `Authorization: Bearer <access_token>`

## Data Model (Artifacts-backed)

These endpoints are backed by the **artifacts** table. A "document" is a document-type artifact (e.g., `docx`, `report`, `export`) associated with a workflow and owned by the authenticated user.

### Document Object (response)

| Field | Type | Notes |
|------|------|------|
| `id` | string | Artifact/document ID |
| `workflowId` | string | Owning workflow |
| `type` | string | e.g. `docx`, `report`, `export`, `draft` |
| `name` | string | Display name |
| `mimeType` | string | e.g. `application/vnd.openxmlformats-officedocument.wordprocessingml.document` |
| `sizeBytes` | number | Optional if tracked |
| `createdAt` | string | ISO 8601 |
| `updatedAt` | string | ISO 8601 |
| `downloadUrl` | string | Optional; can be pre-signed |
| `metadata` | object | Arbitrary JSON metadata |

## GET `/api/documents`

List documents for the authenticated user.

### Query Parameters

- `workflowId` (optional, string): filter documents to a workflow
- `type` (optional, string): filter by artifact type (`docx`, `pdf`, etc.)
- `limit` (optional, integer, default 50, max 200)
- `cursor` (optional, string): pagination cursor

### Responses

- `200 OK` — returns a list of documents
- `401 Unauthorized` — missing/invalid token
- `500 Internal Server Error`

### Example Response (200)

```json
{
  "data": [
    {
      "id": "doc_123",
      "workflowId": "wf_456",
      "type": "docx",
      "name": "Research Report.docx",
      "mimeType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      "sizeBytes": 182044,
      "createdAt": "2026-02-02T19:00:00Z",
      "updatedAt": "2026-02-02T19:00:00Z",
      "downloadUrl": "https://example.com/presigned/...",
      "metadata": {
        "stage": 20,
        "exportFormat": "docx"
      }
    }
  ],
  "nextCursor": null
}
```

## GET `/api/documents/:id`

Get a specific document by ID.

### Path Parameters

- `id` (required, string): document/artifact ID

### Responses

- `200 OK` — document details
- `401 Unauthorized`
- `404 Not Found` — document not found or not owned by user
- `500 Internal Server Error`

### Example Response (200)

```json
{
  "data": {
    "id": "doc_123",
    "workflowId": "wf_456",
    "type": "docx",
    "name": "Research Report.docx",
    "mimeType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "sizeBytes": 182044,
    "createdAt": "2026-02-02T19:00:00Z",
    "updatedAt": "2026-02-02T19:00:00Z",
    "downloadUrl": "https://example.com/presigned/...",
    "metadata": {
      "stage": 20,
      "exportFormat": "docx"
    }
  }
}
```

## POST `/api/documents/:id/export`

Export a document to DOCX or PDF.

> Note: Depending on implementation, this may:
> - return a binary stream directly, or
> - return a JSON response containing an export artifact and `downloadUrl`.
>
> This spec documents the **JSON response** pattern for consistency.

### Path Parameters

- `id` (required, string): document/artifact ID

### Request Body

- `format` (required): `docx` | `pdf`

### Responses

- `200 OK` — export created
- `401 Unauthorized`
- `404 Not Found`
- `500 Internal Server Error`

### Example Request

```json
{
  "format": "docx"
}
```

### Example Response (200)

```json
{
  "data": {
    "exportId": "exp_789",
    "format": "docx",
    "mimeType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "downloadUrl": "https://example.com/presigned/...",
    "createdAt": "2026-02-02T19:05:00Z"
  }
}
```

## Error Shape

All endpoints SHOULD return a consistent error object.

```json
{
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Missing or invalid token",
    "requestId": "req_abc123"
  }
}
```
