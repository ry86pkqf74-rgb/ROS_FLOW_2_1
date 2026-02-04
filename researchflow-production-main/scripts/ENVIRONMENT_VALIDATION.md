# ResearchFlow Environment Variables Validation

## Overview

The `validate-environment.sh` script provides comprehensive validation of ResearchFlow environment variables, checks security requirements, and can generate secure values for optional configurations.

## Features

- Validates all required environment variables are set and non-empty
- Checks security requirements (JWT_SECRET minimum length, password strength)
- Validates port configurations for conflicts and valid ranges
- Supports environment-specific configurations (development, production, staging, test)
- Generates secure random values for missing security secrets
- Creates `.env.example` template for configuration reference
- Color-coded output with clear error, warning, and info messages
- Verbose mode for detailed validation information

## Usage

### Basic Validation

Run validation against the `.env` file in the current directory:

```bash
./validate-environment.sh
```

### Validate Specific File

Validate a specific environment file:

```bash
./validate-environment.sh /path/to/.env
```

### Generate Example Template

Create a `.env.example` template with all available configuration options:

```bash
./validate-environment.sh --generate-example
```

### Generate Missing Secrets

Generate secure random values for missing security secrets and save to `.env.generated`:

```bash
./validate-environment.sh --fix
```

### Verbose Output

Show detailed validation messages including optional variables:

```bash
./validate-environment.sh --verbose
```

### Combined Usage

Generate template and show detailed output:

```bash
./validate-environment.sh --generate-example --verbose
```

### Display Help

Show usage information and examples:

```bash
./validate-environment.sh --help
```

## Environment Variables

### PostgreSQL Configuration (REQUIRED)

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_HOST` | - | PostgreSQL server hostname or IP address |
| `POSTGRES_PORT` | 5432 | PostgreSQL server port |
| `POSTGRES_DB` | - | PostgreSQL database name |
| `POSTGRES_USER` | - | PostgreSQL user account |
| `POSTGRES_PASSWORD` | - | PostgreSQL password (min 12 chars) |

### Redis Configuration (OPTIONAL)

If any Redis variable is set, all are required except `REDIS_PASSWORD`:

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_HOST` | - | Redis server hostname or IP address |
| `REDIS_PORT` | 6379 | Redis server port |
| `REDIS_PASSWORD` | - | Redis password (optional for local Redis) |

### Security & Secrets Configuration (REQUIRED)

| Variable | Min Length | Description |
|----------|-----------|-------------|
| `JWT_SECRET` | 64 chars | JWT signing secret for token generation |
| `SESSION_SECRET` | - | Session secret for session management |
| `ENCRYPTION_KEY` | - | Encryption key for data encryption at rest |

Generate secure values with:
```bash
# Generate JWT secret (64+ characters)
openssl rand -base64 64

# Generate session/encryption keys (32+ characters)
openssl rand -hex 32
```

### Service Port Configuration (REQUIRED)

| Variable | Default | Description |
|----------|---------|-------------|
| `ORCHESTRATOR_PORT` | 3000 | Main orchestrator service port |
| `WORKER_PORT` | 3001 | Worker service port |
| `COLLAB_PORT` | 3002 | Collaboration service port |

Ports must be:
- Valid range: 1-65535
- Unique (no duplicates)
- Not in use by other services

### Environment & Logging (REQUIRED)

| Variable | Values | Description |
|----------|--------|-------------|
| `NODE_ENV` | development, production, test, staging | Node.js environment |
| `LOG_LEVEL` | debug, info, warn, error | Logging level (default: info) |
| `SENTRY_DSN` | - | Sentry error tracking URL (optional) |

### External AI APIs (OPTIONAL)

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | OpenAI API key (sk-...) |
| `ANTHROPIC_API_KEY` | Anthropic API key for Claude |

At least one AI provider is recommended for full functionality.

### Frontend Configuration (OPTIONAL)

| Variable | Example | Description |
|----------|---------|-------------|
| `VITE_API_URL` | http://localhost:3000/api | API server URL for frontend |
| `VITE_COLLAB_URL` | http://localhost:3002 | Collaboration server URL |

## Validation Rules

### Required Variables

All of the following must be set and non-empty:
- PostgreSQL configuration (5 variables)
- Security secrets (3 variables)
- Service ports (3 variables)
- `NODE_ENV`

### Optional Variables

These can be omitted:
- Redis configuration (not recommended for production)
- Log level and error tracking
- AI provider keys (though at least one is recommended)
- Frontend URLs
- Optional logging: `LOG_LEVEL`, `SENTRY_DSN`

### Security Requirements

- **JWT_SECRET**: Minimum 64 characters (recommended: 128+ for production)
- **Passwords**: Minimum 12 characters with complexity requirements:
  - At least 3 of: uppercase, lowercase, digits, special characters
  - Recommended: Mix of all four character types

- **Port Validation**:
  - Valid range: 1-65535
  - Must be unique (no port conflicts)
  - Default range 3000-3002 is recommended

## Output Interpretation

### Validation Summary

The script displays a summary with three counters:

```
Errors:     0
Warnings:   2
Info:       1
```

- **Errors**: Critical issues that must be fixed (validation fails if > 0)
- **Warnings**: Non-critical issues (e.g., weak password complexity, missing optional AI keys)
- **Info**: Informational messages (optional variables not set, Redis not configured)

### Exit Codes

- `0`: All validations passed successfully
- `1`: One or more critical validations failed

## Examples

### Typical Development Setup

1. Copy the template:
```bash
cp .env.example .env
```

2. Edit `.env` with your local development values:
```bash
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=researchflow_dev
POSTGRES_USER=dev_user
POSTGRES_PASSWORD=***REDACTED***

NODE_ENV=development
```

3. Generate security secrets:
```bash
./scripts/validate-environment.sh --fix
```

4. Append generated secrets to `.env`:
```bash
cat .env.generated >> .env
```

5. Validate the configuration:
```bash
./scripts/validate-environment.sh
```

### Production Deployment

1. Start with template:
```bash
cp .env.example .env
```

2. Set all required variables with strong, unique values:
```bash
# Use secure password generation
openssl rand -hex 32  # For secrets
openssl rand -base64 64  # For JWT_SECRET
```

3. Configure for production:
```bash
NODE_ENV=production
LOG_LEVEL=warn
POSTGRES_PASSWORD=<strong_password>
```

4. Validate:
```bash
./scripts/validate-environment.sh --verbose
```

5. Verify no errors:
```bash
./scripts/validate-environment.sh && echo "Configuration valid!"
```

### With Docker

Use validation as part of container initialization:

```dockerfile
# Validate before starting app
RUN ./scripts/validate-environment.sh || exit 1

# Start application
CMD ["npm", "start"]
```

## Troubleshooting

### "Configuration file not found" warning

This is normal if the `.env` file doesn't exist yet. The script will use system environment variables if available.

Solution:
```bash
./scripts/validate-environment.sh --generate-example
cp .env.example .env
# Edit .env with your values
./scripts/validate-environment.sh
```

### "PASSWORD_VAR is too weak"

Password must be at least 12 characters and preferably include uppercase, lowercase, digits, and special characters.

Solution:
```bash
# Generate strong password
openssl rand -hex 16  # 32 character hex string
# Or use a password manager
```

### "JWT_SECRET is too short"

JWT_SECRET must be at least 64 characters (recommended: 128+).

Solution:
```bash
openssl rand -base64 64  # Generate secure JWT secret
```

### Port already in use

One of the configured ports is already in use by another service.

Solution:
1. Find which process is using the port:
```bash
lsof -i :3000  # Check port 3000
```

2. Either stop that process or use different ports:
```bash
ORCHESTRATOR_PORT=4000
WORKER_PORT=4001
COLLAB_PORT=4002
```

### NODE_ENV invalid value

NODE_ENV must be one of: `development`, `production`, `test`, or `staging`.

Solution:
```bash
# In .env file
NODE_ENV=production  # Instead of "prod" or "prod-env"
```

## Security Best Practices

1. **Never commit .env file to version control**
   - Add `.env` to `.gitignore`
   - Store secrets in secure vaults for production

2. **Use strong, unique passwords**
   - Minimum 12 characters
   - Mix of uppercase, lowercase, digits, special characters
   - Generate with cryptographic tools: `openssl rand`

3. **Rotate secrets periodically**
   - Change JWT_SECRET, SESSION_SECRET, ENCRYPTION_KEY regularly
   - Use secret management systems in production

4. **Different values for each environment**
   - Development: Less strict requirements
   - Production: Maximum security with strong values

5. **Monitor access**
   - Track who has access to .env files
   - Audit environment variable usage
   - Restrict file permissions: `chmod 600 .env`

## Integration with CI/CD

Add validation to your CI/CD pipeline:

```yaml
# GitHub Actions example
- name: Validate Environment
  run: ./scripts/validate-environment.sh --verbose
  
- name: Check for Errors
  run: |
    ./scripts/validate-environment.sh > /tmp/validation.txt
    ! grep "ERROR" /tmp/validation.txt || exit 1
```

## Requirements

- Bash 4.0 or later
- Common Unix utilities:
  - `head`: File reading
  - `base64`: Base64 encoding
  - `cut`: String manipulation
  - `tr`: Character translation
  - `grep`: Pattern matching (for validation)

Check system compatibility:
```bash
bash --version
which head base64 cut tr grep
```

## Support

For issues or questions about environment validation:

1. Check the output message carefully - it includes specific guidance
2. Run with `--verbose` flag for detailed information
3. Review this documentation for your specific variable
4. Check `.env.example` for template values

## See Also

- `.env.example`: Configuration template
- `.env.generated`: Auto-generated secure values (if using --fix)
- ResearchFlow documentation: Main configuration guide
