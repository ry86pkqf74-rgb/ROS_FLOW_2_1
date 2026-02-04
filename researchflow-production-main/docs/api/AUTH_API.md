# Auth API

> Base path: `/api/auth`
>
> Token: **Bearer access token**
>
> Client storage: `localStorage["access_token"]`
>
> Header: `Authorization: Bearer <access_token>`

## POST `/api/auth/login`

Authenticate a user and return an access token.

### Request Body

| Field | Type | Required |
|------|------|----------|
| `email` | string | yes |
| `password` | string | yes |

### Responses

- `200 OK` — login success
- `401 Unauthorized` — invalid credentials
- `500 Internal Server Error`

### Example Request

```json
{
  "email": "user@example.com",
  "password": "********"
}
```

### Example Response (200)

```json
{
  "data": {
    "accessToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }
}
```

## POST `/api/auth/refresh`

Refresh an access token.

> The refresh mechanism (cookie vs refresh token) is implementation-specific. This endpoint is expected to return a **new** access token.

### Request Body

- Usually empty, or may include a refresh token depending on implementation.

### Responses

- `200 OK` — returns a new access token
- `401 Unauthorized` — refresh invalid/expired
- `500 Internal Server Error`

### Example Response (200)

```json
{
  "data": {
    "accessToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }
}
```

## Token format and storage

### Format

- Header: `Authorization: Bearer <token>`
- Token is expected to be a JWT or JWT-like opaque string.

### Storage

- Client stores token at: `localStorage["access_token"]`

### Recommended client behavior

- On successful login or refresh:
  - write `localStorage.setItem("access_token", accessToken)`
- On logout or refresh failure:
  - clear token: `localStorage.removeItem("access_token")`

## Error Shape (recommended)

```json
{
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Invalid credentials",
    "requestId": "req_abc123"
  }
}
```
