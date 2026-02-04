# [ROS-102] Kubernetes Metrics Server + Resource Config - Phase 6.1

## Task Overview
Create Kubernetes configurations for metrics collection and resource management.

## Location
Create files in: `k8s/`

## Required Files

### 1. `k8s/metrics-server/deployment.yaml`
```yaml
# Metrics Server deployment for K8s cluster metrics
# - Image: registry.k8s.io/metrics-server/metrics-server:v0.6.4
# - Args: --kubelet-insecure-tls, --kubelet-preferred-address-types=InternalIP
# - Resources: 100m CPU, 200Mi memory
```

### 2. `k8s/metrics-server/service.yaml`
- ClusterIP service for metrics-server
- Port 443 targeting container port 4443

### 3. `k8s/metrics-server/rbac.yaml`
- ServiceAccount: metrics-server
- ClusterRole with permissions for nodes, pods, namespaces
- ClusterRoleBinding

### 4. `k8s/resource-quotas/namespace-quota.yaml`
```yaml
# Resource quota for researchflow namespace
# - requests.cpu: 4
# - requests.memory: 8Gi
# - limits.cpu: 8
# - limits.memory: 16Gi
# - pods: 20
```

### 5. `k8s/resource-quotas/limit-range.yaml`
```yaml
# Default limits for containers
# - default CPU: 500m
# - default memory: 512Mi
# - defaultRequest CPU: 100m
# - defaultRequest memory: 128Mi
# - max CPU: 2
# - max memory: 4Gi
```

### 6. `k8s/monitoring/pod-monitor.yaml`
- PodMonitor CRD for Prometheus scraping
- Match labels: app=researchflow
- Scrape interval: 30s

### 7. `k8s/monitoring/service-monitor.yaml`
- ServiceMonitor for API metrics
- Endpoints: /metrics on port 3000

### 8. `k8s/README.md`
Document deployment order and prerequisites

## Expected Output
- Complete metrics server deployment
- Resource quotas and limits
- Monitoring configurations
- Documentation

## GitHub Repository
https://github.com/ry86pkqf74-rgb/researchflow-production
