# Microservice Deployment Guide

## Overview

The Constraint Enforcement Engine is now a production-ready microservice with all enterprise features:

✅ **Containerization**
- Multi-stage Dockerfile with Python 3.12-slim base
- Non-root runtime (UID 1000)
- Reproducible builds
- Built-in health checks

✅ **12-Factor Configuration**
- All config via environment variables
- No hardcoded values
- Externalized secrets support
- Policy directory mount strategy

✅ **Observability**
- Prometheus metrics at `/metrics`
- Structured JSON logging
- Request counters by policy and result
- Evaluation latency histograms

✅ **Health & Readiness**
- Liveness probe: `/health`
- Readiness probe: `/ready` (validates policies loaded)

✅ **Concurrency**
- Thread-safe component initialization
- Gunicorn WSGI server with configurable workers
- Deterministic behavior under parallel load

✅ **Failure Isolation**
- Rate limiting (Flask-Limiter)
- Request body size limits (1MB default)
- HTTP layer timeouts (30s default)
- Simulation CPU bounds (depth limiting)

✅ **Kubernetes Deployment**
- Complete K8s manifests
- Resource requests/limits
- Network policies
- Service account with minimal permissions
- 3 replicas with rolling updates

✅ **Determinism Verification**
- Hash consistency across replicas (verified in tests)
- Clock-independent evaluation
- No timestamps in context
- No dict ordering issues (sorted keys)

## Quick Start

### Local Development
```bash
pip install -r requirements.txt
python app_production.py
```

### Docker
```bash
./build-docker.sh
docker run -p 5000:5000 -v $(pwd)/policies:/app/policies:ro constraint-enforcement-engine:latest
```

### Kubernetes
```bash
./deploy-k8s.sh
```

## Architecture

```
┌─────────────────────────────────────────┐
│         Load Balancer / Ingress         │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│      K8s Service (ClusterIP)            │
└─────────────────┬───────────────────────┘
                  │
      ┌───────────┼───────────┐
      │           │           │
┌─────▼────┐ ┌───▼─────┐ ┌──▼──────┐
│ Pod 1    │ │ Pod 2   │ │ Pod 3   │
│ (replica)│ │(replica)│ │(replica)│
└──────────┘ └─────────┘ └─────────┘
      │           │           │
      └───────────┼───────────┘
                  │
        ┌─────────▼──────────┐
        │  ConfigMap         │
        │  (Policies)        │
        └────────────────────┘
```

## Metrics

All metrics follow Prometheus best practices:

**Counters:**
- `policy_evaluations_total{policy_id, allowed}` - Total evaluations
- `http_requests_total{method, endpoint, status}` - HTTP requests

**Histograms:**
- `policy_evaluation_latency_seconds{policy_id}` - Latency distribution

## Logging

Structured JSON logs include:
- Timestamp (ISO 8601 with timezone)
- Log level
- Request details (method, path, remote_addr)
- Evaluation details (policy_id, allowed, violations)
- Latency metrics

## Security

- Non-root container (UID 1000)
- Read-only policy mounts
- Network policies restrict ingress/egress
- No privilege escalation
- Secure defaults for timeouts and limits
- Input validation and sanitization

## Monitoring Queries

### Prometheus Queries

```promql
# Request rate
rate(http_requests_total[5m])

# Success rate
rate(policy_evaluations_total{allowed="true"}[5m]) /
rate(policy_evaluations_total[5m])

# P95 latency
histogram_quantile(0.95, rate(policy_evaluation_latency_seconds_bucket[5m]))

# Error rate
rate(http_requests_total{status=~"5.."}[5m])
```

## Production Checklist

- [ ] Configure external Redis for rate limiting
- [ ] Set up log aggregation (ELK, Splunk, etc.)
- [ ] Configure Prometheus scraping
- [ ] Set up alerting rules
- [ ] Configure horizontal pod autoscaling
- [ ] Set up ingress with TLS
- [ ] Configure resource quotas
- [ ] Set up backup for audit logs
- [ ] Configure pod disruption budgets
- [ ] Enable pod security policies

## Troubleshooting

### Pod not ready
```bash
kubectl logs -n constraint-enforcement -l app=constraint-enforcement-engine
kubectl describe pod -n constraint-enforcement <pod-name>
```

### Check policies loaded
```bash
curl http://service-url/ready
```

### View metrics
```bash
curl http://service-url/metrics
```

### Test evaluation
```bash
curl -X POST http://service-url/evaluate \
  -H "Content-Type: application/json" \
  -d '{"actor_id":"test","action_type":"test","payload":{"actor":{"max_role":10},"request":{"role":5,"value":500}},"policy_id":"mutation_policy_v1"}'
```
