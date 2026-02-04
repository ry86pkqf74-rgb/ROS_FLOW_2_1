# Quick Start Guide - ResearchFlow Docker Deployment

## 5-Minute Setup

### Step 1: Prerequisites Check (1 min)
```bash
# Verify Docker is installed and running
docker --version
docker-compose --version
docker ps  # Should show Docker daemon is running
```

### Step 2: Configure Environment (1 min)
```bash
# Copy environment template
cp .env.example .env

# Edit with your values (use secure passwords!)
nano .env
# Minimum required:
# POSTGRES_PASSWORD=secure-password
# REDIS_PASSWORD=secure-password
# JWT_SECRET=long-random-string
```

### Step 3: Deploy (3 min)
```bash
# Make script executable
chmod +x deploy-docker-stack.sh

# Run deployment
./deploy-docker-stack.sh deploy

# Wait for "Deployment Successful" message
```

## Verify Deployment

```bash
# Check all services are running
./deploy-docker-stack.sh status

# Run health checks
./deploy-docker-stack.sh health

# Test endpoints
curl http://localhost:3001/health    # Orchestrator
curl http://localhost:8000/health    # Worker
curl http://localhost:5173           # Web UI
```

## Access Services

- **Web UI:** http://localhost:5173
- **API:** http://localhost:3001
- **Worker:** http://localhost:8000
- **Guidelines:** http://localhost:8001
- **Collaboration:** http://localhost:1234

## Common Tasks

### View Logs
```bash
# Orchestrator logs
./deploy-docker-stack.sh logs orchestrator

# All services
docker-compose logs -f

# Specific lines
docker-compose logs --tail=50
```

### Stop Services
```bash
./deploy-docker-stack.sh stop
```

### Restart Services
```bash
./deploy-docker-stack.sh start
```

### Troubleshoot Issues
```bash
./deploy-docker-stack.sh diagnose
```

### Clean Up (Remove Everything)
```bash
./deploy-docker-stack.sh clean
```

## Next Steps

1. **Configure** - Update environment variables for your deployment
2. **Test** - Verify API connectivity and health checks
3. **Monitor** - Set up logging and monitoring
4. **Secure** - Implement HTTPS and authentication
5. **Backup** - Configure automated backups

For detailed documentation, see DEPLOYMENT.md
