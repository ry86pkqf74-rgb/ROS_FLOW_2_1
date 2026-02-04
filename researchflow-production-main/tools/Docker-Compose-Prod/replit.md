# Fullstack JavaScript Application

## Overview

This is a fullstack JavaScript application built with Express.js (backend) and React with Vite (frontend). The application is containerized with Docker for production deployment.

## Project Structure

```
├── client/                 # Frontend React application
│   ├── src/
│   │   ├── components/    # UI components (Shadcn/UI)
│   │   ├── pages/         # Page components
│   │   ├── hooks/         # Custom React hooks
│   │   └── lib/           # Utilities and query client
│   └── index.html
├── server/                 # Backend Express application
│   ├── index.ts           # Server entry point
│   ├── routes.ts          # API routes
│   ├── storage.ts         # Data storage layer
│   └── vite.ts            # Vite dev server integration
├── shared/                 # Shared code between frontend/backend
│   └── schema.ts          # Database schema and types
├── nginx/                  # Nginx configuration for production
│   └── nginx.conf
├── Dockerfile             # Production Dockerfile
├── Dockerfile.dev         # Development Dockerfile
├── docker-compose.yml     # Production Docker Compose
├── docker-compose.dev.yml # Development Docker Compose override
└── Makefile               # Convenience commands
```

## Development

### Local Development (without Docker)

```bash
npm install
npm run dev
```

The app runs on http://localhost:5000

### Development with Docker

```bash
make dev
```

Or manually:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

## Production Deployment

### Prerequisites

1. Docker and Docker Compose installed
2. Create `.env` file from `.env.example`:

```bash
cp .env.example .env
# Edit .env with your production values
```

### Quick Start

```bash
# Build and start production services
make build
make up

# View logs
make logs

# Check health
make health
```

### With Nginx (SSL/Load Balancing)

1. Place SSL certificates in `nginx/ssl/`:
   - `cert.pem` - SSL certificate
   - `key.pem` - SSL private key

2. Start with nginx:

```bash
make up-nginx
```

### Database Management

```bash
# Access PostgreSQL shell
make db-shell

# Backup database
make db-backup

# Restore database
make db-restore FILE=backups/backup_20240101_120000.sql
```

### Maintenance

```bash
# View all commands
make help

# Restart services
make restart

# Clean up containers and volumes
make clean

# Remove all unused Docker resources
make prune
```

## API Endpoints

- `GET /api/health` - Health check endpoint for Docker and load balancers

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `POSTGRES_USER` | PostgreSQL username | Yes |
| `POSTGRES_PASSWORD` | PostgreSQL password | Yes |
| `POSTGRES_DB` | PostgreSQL database name | Yes |
| `SESSION_SECRET` | Session encryption secret | Yes |
| `APP_PORT` | Application port (default: 5000) | No |
| `DB_PORT` | Database port for local access | No |

## Recent Changes

- **Phase 8.1**: Added production Docker Compose configuration
  - Multi-stage Dockerfile for optimized production builds
  - Docker Compose with PostgreSQL and optional Nginx
  - Health check endpoints
  - Makefile for common operations
  - Development and production environment separation
