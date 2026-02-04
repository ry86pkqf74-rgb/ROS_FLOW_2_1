# Security Checklist

This checklist is used for security reviews, audit readiness, and release gates.

## Authentication & Authorization Review

- [ ] **AuthN is centralized** (single source of truth) and uses strong, modern standards (OIDC/OAuth2 where applicable).
- [ ] **MFA enforced** for administrative accounts.
- [ ] **Password storage** uses strong hashing (Argon2id or bcrypt with appropriate cost) and per-user salt.
- [ ] **Session management**
  - [ ] Secure cookies (`HttpOnly`, `Secure`, `SameSite=Lax/Strict` as appropriate).
  - [ ] Session rotation on privilege change and login.
  - [ ] Reasonable idle/absolute session timeouts.
- [ ] **Authorization**
  - [ ] Role-based or attribute-based access is explicit and tested.
  - [ ] Every privileged endpoint has server-side authorization checks (not only UI gating).
  - [ ] Object-level authorization (IDOR prevention) verified for all resource fetch/update/delete.
- [ ] **API tokens/keys**
  - [ ] Stored only in secret managers; never committed.
  - [ ] Scoped to least privilege and rotated regularly.

## Input Validation Requirements

- [ ] Validate **all external inputs** (HTTP params/body, files, webhooks, background job payloads).
- [ ] Apply **allow-list validation** for structured fields (enums, ids, types).
- [ ] Enforce **size limits** (request body, file uploads, pagination bounds).
- [ ] Protect against **injection**:
  - [ ] SQL injection: parameterized queries/ORM safety.
  - [ ] Command injection: never pass unsanitized input to shell.
  - [ ] SSRF: validate/deny private IP ranges and metadata endpoints.
  - [ ] XSS: output encoding + CSP; sanitize rich text.
- [ ] Handle **deserialization** safely (no unsafe pickle/yaml load for untrusted input).

## Logging & Monitoring Requirements

- [ ] **Security-relevant events are logged** (auth success/failure, privilege changes, access denials, key admin actions).
- [ ] Logs contain **request correlation IDs** and user/account identifiers (avoid PHI/PII when possible).
- [ ] Logs do **not** contain secrets (tokens, passwords, full credit card numbers, PHI).
- [ ] **Alerting** on:
  - [ ] repeated auth failures / brute force indicators
  - [ ] suspicious token usage
  - [ ] unusual access patterns to sensitive resources
- [ ] **Retention & access controls** on logs meet compliance requirements.

## OWASP Top 10 (Mitigations)

- [ ] **A01: Broken Access Control** — server-side authz checks; test for IDOR; enforce least privilege.
- [ ] **A02: Cryptographic Failures** — TLS everywhere; encrypt secrets at rest; avoid weak ciphers.
- [ ] **A03: Injection** — parameterize queries; validate input; escape output.
- [ ] **A04: Insecure Design** — threat modeling; abuse cases; secure defaults.
- [ ] **A05: Security Misconfiguration** — hardened configs; disable debug; secure headers.
- [ ] **A06: Vulnerable and Outdated Components** — dependency scanning; patch cadence; SBOM.
- [ ] **A07: Identification and Authentication Failures** — MFA; strong session mgmt; rate limiting.
- [ ] **A08: Software and Data Integrity Failures** — signed builds; CI protections; verify artifacts.
- [ ] **A09: Security Logging and Monitoring Failures** — centralized logging; alerts; incident runbooks.
- [ ] **A10: Server-Side Request Forgery (SSRF)** — egress controls; URL validation; metadata blocking.

## HIPAA Compliance Controls (Technical Safeguards)

> This section focuses on technical controls that commonly map to the HIPAA Security Rule.

- [ ] **Access Control (45 CFR §164.312(a))**
  - [ ] Unique user identification.
  - [ ] Emergency access procedure documented.
  - [ ] Automatic logoff / session timeout.
  - [ ] Encryption/decryption mechanisms for ePHI where applicable.
- [ ] **Audit Controls (45 CFR §164.312(b))**
  - [ ] Systems record and examine activity in systems containing ePHI.
  - [ ] Audit logs are tamper-resistant and access-controlled.
- [ ] **Integrity (45 CFR §164.312(c))**
  - [ ] Mechanisms to authenticate ePHI integrity (hashing/signing where appropriate).
  - [ ] Change control and approvals for code/config impacting ePHI.
- [ ] **Person or Entity Authentication (45 CFR §164.312(d))**
  - [ ] Strong authentication for workforce members.
  - [ ] MFA for admins and privileged operations.
- [ ] **Transmission Security (45 CFR §164.312(e))**
  - [ ] TLS enforced for all network transmissions.
  - [ ] No ePHI in URLs.
  - [ ] Secure email/messaging or de-identify before sending.

## Dependency Scanning & CI/CD Controls

- [ ] Automated scans on push/PR and scheduled runs.
- [ ] SARIF uploaded to GitHub Security for centralized visibility.
- [ ] Pre-commit hooks prevent common secret leaks.
- [ ] Build provenance and artifact integrity checks (where feasible).

## Release Gate

- [ ] No **CRITICAL** vulnerabilities without documented risk acceptance.
- [ ] No secrets detected.
- [ ] Security review sign-off recorded.
