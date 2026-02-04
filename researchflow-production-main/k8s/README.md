# ResearchFlow Kubernetes Configuration

Phase 6.1: Kubernetes Metrics & Resource Management
Linear Issue: ROS-102

## Directory Structure

```
k8s/
├── metrics-server/          # Kubernetes Metrics Server
│   ├── deployment.yaml      # Metrics server deployment
│   ├── service.yaml         # ClusterIP service + APIService
│   └── rbac.yaml           # ServiceAccount, ClusterRole, bindings
├── resource-quotas/         # Resource Management
│   ├── namespace-quota.yaml # ResourceQuota for namespaces
│   └── limit-range.yaml     # Default container limits
├── monitoring/              # Prometheus Monitoring
│   ├── pod-monitor.yaml     # PodMonitor CRDs
│   └── service-monitor.yaml # ServiceMonitor CRDs
└── README.md               # This file
```

## Prerequisites

1. **Kubernetes Cluster**: v1.24+
2. **kubectl**: Configured with cluster access
3. **Prometheus Operator** (for monitoring): Install via Helm
   ```bash
   helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
   helm install prometheus prometheus-community/kube-prometheus-stack -n monitoring
   ```

## Deployment Order

Deploy in the following order to ensure dependencies are met:

### 1. Create Namespaces
```bash
kubectl create namespace researchflow
kubectl create namespace researchflow-dev
```

### 2. Deploy Metrics Server
```bash
kubectl apply -f k8s/metrics-server/rbac.yaml
kubectl apply -f k8s/metrics-server/service.yaml
kubectl apply -f k8s/metrics-server/deployment.yaml
```

Verify metrics server is running:
```bash
kubectl top nodes
kubectl top pods -n researchflow
```

### 3. Apply Resource Quotas
```bash
kubectl apply -f k8s/resource-quotas/namespace-quota.yaml
kubectl apply -f k8s/resource-quotas/limit-range.yaml
```

Verify quotas:
```bash
kubectl describe resourcequota researchflow-quota -n researchflow
kubectl describe limitrange researchflow-limits -n researchflow
```

### 4. Deploy Monitoring (requires Prometheus Operator)
```bash
kubectl apply -f k8s/monitoring/pod-monitor.yaml
kubectl apply -f k8s/monitoring/service-monitor.yaml
```

Verify monitors are detected:
```bash
kubectl get podmonitor -n researchflow
kubectl get servicemonitor -n researchflow
```

## Resource Allocation

### Production Namespace (`researchflow`)
| Resource | Request | Limit |
|----------|---------|-------|
| CPU | 4 cores | 8 cores |
| Memory | 8Gi | 16Gi |
| Storage | - | 100Gi |
| Pods | - | 20 |
| GPUs | 2 | 2 |

### Development Namespace (`researchflow-dev`)
| Resource | Request | Limit |
|----------|---------|-------|
| CPU | 2 cores | 4 cores |
| Memory | 4Gi | 8Gi |
| Pods | - | 10 |

### Default Container Limits
| Resource | Default Request | Default Limit | Max |
|----------|----------------|---------------|-----|
| CPU | 100m | 500m | 2 |
| Memory | 128Mi | 512Mi | 4Gi |

## Monitoring Endpoints

Services expose metrics at `/metrics`:

| Service | Port | Path |
|---------|------|------|
| Orchestrator | 3001 | /metrics |
| Worker | 8000 | /metrics |
| Guideline Engine | 8001 | /metrics |
| Ollama | 11434 | /api/metrics |

## Troubleshooting

### Metrics Server Issues
```bash
# Check metrics server logs
kubectl logs -n kube-system -l app=metrics-server

# Verify API service
kubectl get apiservice v1beta1.metrics.k8s.io -o yaml
```

### Resource Quota Exceeded
```bash
# Check current usage
kubectl describe resourcequota -n researchflow

# List pods consuming most resources
kubectl top pods -n researchflow --sort-by=memory
```

### ServiceMonitor Not Working
```bash
# Check Prometheus Operator is running
kubectl get pods -n monitoring | grep prometheus-operator

# Verify ServiceMonitor is being picked up
kubectl get servicemonitor -n researchflow -o yaml
```

## Cleanup

```bash
# Remove monitoring
kubectl delete -f k8s/monitoring/

# Remove resource quotas
kubectl delete -f k8s/resource-quotas/

# Remove metrics server
kubectl delete -f k8s/metrics-server/
```
