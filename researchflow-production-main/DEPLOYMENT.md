# ResearchFlow Phase 9 AI Deployment Guide

This guide covers the deployment, configuration, and management of ResearchFlow's AI infrastructure for Phase 9 production deployment.

## Overview

Phase 9 introduces comprehensive AI capabilities with:
- **Ollama**: Open-source LLM serving with GPU acceleration
- **Triton Inference Server**: High-performance model inference
- **FAISS**: Vector database for semantic search
- **Redis**: Caching layer for inference results
- **Prometheus + Grafana**: Complete monitoring stack

## Directory Structure

```
researchflow-production/
├── docker-compose.ai.yml          # AI services configuration
├── .github/workflows/
│   └── ai-deploy.yml              # GitHub Actions CI/CD pipeline
├── deploy/
│   ├── feature-rollout.sh          # Feature flag rollout script
│   ├── prometheus.yml              # Prometheus scrape config
│   ├── alert-rules.yml             # Alert rules and thresholds
│   ├── ai-monitoring.yml           # Monitoring definitions
│   ├── feature-flags.json          # Feature flag configuration
│   ├── grafana-datasources.yml     # Grafana datasource config
│   └── grafana-dashboards/         # Grafana dashboard files
└── DEPLOYMENT.md                   # This file
```

## Prerequisites

### System Requirements

**Hardware:**
- Minimum 8 CPU cores (16+ recommended)
- 32GB RAM (64GB+ for production)
- NVIDIA GPU with 8GB+ VRAM (for GPU acceleration)
- 500GB+ SSD storage (for model cache and indices)

**Software:**
- Docker 20.10+
- Docker Compose 2.0+
- NVIDIA Docker Runtime (for GPU support)
- curl, jq, bash 4.0+

### Environment Variables

Create a `.env` file in the project root:

```bash
# Ollama Configuration
OLLAMA_NUM_PARALLEL=4
OLLAMA_NUM_THREAD=8

# FAISS Configuration
FAISS_INDEX_TYPE=IVF,PQ
FAISS_CACHE_SIZE=10GB
FAISS_NUM_WORKERS=8

# Redis Configuration
REDIS_PASSWORD=your-secure-password-here

# Grafana Configuration
GRAFANA_ADMIN_PASSWORD=your-grafana-password-here
GRAFANA_ADMIN_USER=admin

# Service Configuration
PROMETHEUS_URL=http://localhost:9090
FEATURE_FLAG_SERVICE=http://localhost:8080

# Deployment Settings
ENVIRONMENT=production
LOG_LEVEL=info
```

## Deployment Steps

### 1. Initial Deployment to Staging

```bash
# Pull latest configurations
git pull origin develop

# Validate configuration
docker-compose -f docker-compose.ai.yml config

# Start AI services in staging
export ENVIRONMENT=staging
docker-compose -f docker-compose.ai.yml up -d

# Wait for services to initialize
sleep 60

# Run health checks
curl -f http://localhost:11434/api/tags     # Ollama
curl -f http://localhost:8000/v2/health/ready  # Triton
curl -f http://localhost:5000/health        # FAISS
```

### 2. Verify Metrics Collection

```bash
# Check Prometheus scrape targets
curl http://localhost:9090/api/v1/targets

# Query sample metrics
curl 'http://localhost:9090/api/v1/query?query=up'
```

### 3. Deploy to Production with Canary Rollout

The GitHub Actions workflow automatically handles:
1. Validation of configurations
2. Health checks
3. Canary deployment (10% traffic)
4. Gradual promotion (10% → 50% → 100%)
5. Automatic rollback on failure

Push to `main` branch to trigger:

```bash
git push origin develop:main
```

## Feature Flag Rollout

### Basic Rollout

Gradually roll out the `ai_inference` feature to 100%:

```bash
./deploy/feature-rollout.sh \
  --feature ai_inference \
  --target-percentage 100
```

### Canary Rollout

Test with limited percentage:

```bash
./deploy/feature-rollout.sh \
  --feature vector_search \
  --target-percentage 25
```

### Dry Run (Simulation)

Preview what would happen without making changes:

```bash
./deploy/feature-rollout.sh \
  --feature semantic_cache \
  --target-percentage 100 \
  --dry-run
```

### Rollback Feature

Return to previous state:

```bash
./deploy/feature-rollout.sh \
  --feature ai_inference \
  --rollback
```

### Script Options

```
--feature FEATURE_NAME              Feature to rollout (required)
--target-percentage PERCENT         Target rollout percentage (0-100)
--dry-run                           Simulate without changes
--force                             Skip confirmation prompts
--rollback                          Rollback to previous version
--verbose                           Enable verbose logging
```

## Monitoring and Observability

### Access Grafana

1. Open http://localhost:3000
2. Default credentials: `admin` / `$GRAFANA_ADMIN_PASSWORD`
3. Navigate to "Dashboards" to view pre-built dashboards:
   - **AI Overview**: High-level service status and performance
   - **Ollama Detail**: LLM-specific metrics
   - **Triton Detail**: Inference server performance
   - **FAISS Detail**: Vector search metrics
   - **Cost Analysis**: GPU hours and inference costs
   - **Infrastructure Health**: System resource usage

### Key Metrics to Monitor

**Performance Metrics:**
- Request rate: `rate(ai_inference_requests_total[5m])`
- Error rate: `rate(ai_inference_errors_total[5m])`
- P95 latency: `histogram_quantile(0.95, rate(ai_inference_duration_ms_bucket[5m]))`
- P99 latency: `histogram_quantile(0.99, rate(ai_inference_duration_ms_bucket[5m]))`

**Resource Metrics:**
- GPU utilization: `nvidia_smi_gpu_core_utilization`
- GPU memory: `nv_gpu_memory_used_mb / nv_gpu_memory_total_mb`
- System memory: `1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)`

**Cost Metrics:**
- GPU hours: `sum(rate(nvidia_smi_gpu_core_utilization[24h])) * 24`
- Inference cost: `sum(rate(ai_inference_requests_total[24h])) * 0.0001`

### Alert Rules

Critical alerts are automatically configured in `alert-rules.yml`:

| Alert | Threshold | Duration |
|-------|-----------|----------|
| High Inference Latency | P95 > 5000ms | 2 minutes |
| Critical Inference Latency | P99 > 10000ms | 1 minute |
| High Error Rate | > 5% | 5 minutes |
| Critical Error Rate | > 10% | 1 minute |
| Service Down | 0 uptime | 1 minute |
| Memory Pressure | > 90% | 5 minutes |
| Disk Space Low | > 85% | 10 minutes |

## Performance Tuning

### Ollama Optimization

```bash
# Increase parallel inference
export OLLAMA_NUM_PARALLEL=8

# Increase thread count
export OLLAMA_NUM_THREAD=16

# Adjust keep-alive timeout
export OLLAMA_KEEP_ALIVE=10m
```

### Triton Optimization

```bash
# Increase model instances
docker-compose -f docker-compose.ai.yml up -d --scale triton=2

# Check instance status
curl http://localhost:8000/v2/models/*/instances
```

### FAISS Index Optimization

```bash
# Rebuild FAISS index for better performance
# After rebuilding, restart the service:
docker-compose -f docker-compose.ai.yml restart faiss-server
```

### Redis Cache Optimization

```bash
# Monitor cache hit rate
redis-cli info stats | grep hits

# Adjust max memory policy
redis-cli CONFIG SET maxmemory-policy allkeys-lru
```

## Troubleshooting

### Service Not Starting

```bash
# Check service logs
docker-compose -f docker-compose.ai.yml logs <service-name>

# Validate docker-compose syntax
docker-compose -f docker-compose.ai.yml config

# Check resource availability
free -h  # Memory
df -h    # Disk
nvidia-smi  # GPU
```

### High Latency

1. Check GPU utilization: `nvidia-smi`
2. Monitor queue depth: `curl http://localhost:8000/metrics | grep queue`
3. Review model load times: Check Prometheus metrics
4. Scale services: `docker-compose -f docker-compose.ai.yml up -d --scale ollama=2`

### Memory Issues

```bash
# Check container memory usage
docker stats

# Reduce cache size
export FAISS_CACHE_SIZE=5GB

# Restart services
docker-compose -f docker-compose.ai.yml restart
```

### Feature Rollout Issues

```bash
# Check rollout status
cat deploy/feature-flags.json | jq '.flags[] | select(.name == "ai_inference")'

# Review rollout logs
tail -f logs/feature-rollout-*.log

# Manually rollback
./deploy/feature-rollout.sh --feature ai_inference --rollback
```

## Health Checks

### Manual Health Verification

```bash
# Check all services
docker-compose -f docker-compose.ai.yml ps

# Verify each service
# Ollama
curl -f http://localhost:11434/api/tags

# Triton
curl -f http://localhost:8000/v2/health/ready

# FAISS
curl -f http://localhost:5000/health

# Redis
redis-cli -a $REDIS_PASSWORD ping

# Prometheus
curl -f http://localhost:9090/-/healthy

# Grafana
curl -f http://localhost:3000/api/health
```

### Automated Health Checks

The feature rollout script automatically performs:
- Service uptime checks
- Metrics collection verification
- Error rate monitoring
- Latency threshold validation

## Scaling

### Horizontal Scaling

Scale individual services:

```bash
# Scale Ollama instances
docker-compose -f docker-compose.ai.yml up -d --scale ollama=4

# Scale Triton instances
docker-compose -f docker-compose.ai.yml up -d --scale triton=2
```

### Load Balancing

For multi-instance deployments, use a load balancer:

```yaml
# Example with Nginx
upstream ollama {
  server ollama-1:11434;
  server ollama-2:11434;
  server ollama-3:11434;
}
```

## Backup and Recovery

### Backup FAISS Indices

```bash
# Backup vector indices
tar -czf faiss-indices-backup.tar.gz \
  -v volumes/faiss-indices/

# Store in S3
aws s3 cp faiss-indices-backup.tar.gz \
  s3://researchflow-backups/ai/
```

### Restore from Backup

```bash
# Download backup
aws s3 cp s3://researchflow-backups/ai/faiss-indices-backup.tar.gz .

# Extract to volume
tar -xzf faiss-indices-backup.tar.gz -C volumes/faiss-indices/

# Restart service
docker-compose -f docker-compose.ai.yml restart faiss-server
```

## Cost Optimization

### Monitor Costs

Use the Cost Analysis Grafana dashboard to track:
- GPU utilization hours
- Model loading frequency
- Inference request count
- Resource efficiency

### Reduce Costs

1. **Enable Semantic Caching**: Cache inference results to reduce duplicate computations
2. **Batch Processing**: Group requests for better GPU utilization
3. **Model Selection**: Use smaller models for non-critical tasks
4. **Schedule-based Scaling**: Scale down during off-peak hours

## Security

### Network Security

- Expose services only on internal networks
- Use authentication for external APIs
- Enable TLS for inter-service communication

### Data Security

- Encrypt sensitive data at rest
- Use secure Redis password configuration
- Regularly backup important data
- Review access logs in Prometheus

### Secret Management

Store sensitive values in environment variables:

```bash
# Use .env file (not in git)
export REDIS_PASSWORD=$(openssl rand -base64 32)
export GRAFANA_ADMIN_PASSWORD=$(openssl rand -base64 32)

# Use Docker secrets for production
docker secret create redis_password -
docker secret create grafana_password -
```

## Maintenance

### Regular Updates

```bash
# Check for image updates
docker-compose -f docker-compose.ai.yml pull

# Update and restart
docker-compose -f docker-compose.ai.yml up -d
```

### Log Rotation

Configure log rotation in `deploy/logrotate.conf`:

```
/var/log/researchflow-ai/*.log {
  daily
  rotate 30
  compress
  delaycompress
  notifempty
  create 0640 nobody nobody
  sharedscripts
}
```

### Prometheus Data Retention

Default retention is 30 days. Adjust in `docker-compose.ai.yml`:

```yaml
command:
  - '--storage.tsdb.retention.time=60d'
```

## Support and Documentation

- **Prometheus Documentation**: https://prometheus.io/docs/
- **Grafana Documentation**: https://grafana.com/docs/
- **Ollama Documentation**: https://ollama.ai/
- **Triton Documentation**: https://docs.nvidia.com/deeplearning/triton/
- **FAISS Documentation**: https://github.com/facebookresearch/faiss/wiki

## Changelog

### Version 1.0.0 (Phase 9)
- Initial production deployment
- AI inference with Ollama and Triton
- Vector search with FAISS
- Complete monitoring stack
- Feature flag rollout system
- Canary deployment support
