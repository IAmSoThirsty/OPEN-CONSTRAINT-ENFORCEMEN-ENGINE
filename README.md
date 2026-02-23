# OPEN-CONSTRAINT-ENFORCEMENT-ENGINE

Evaluate actions against formally declared invariants before execution.

## Core Responsibilities

- **Policy ingestion**: Load and manage YAML-based policy definitions
- **Static invariant validation**: Compile and validate policy conditions
- **Runtime evaluation**: Evaluate actions against policy invariants
- **Deterministic simulation**: Execute evaluations without mutating canonical state
- **Audit logging**: Record all evaluations for compliance and replay

## Architecture

The engine consists of five main components:

1. **Policy Registry**: Loads and manages YAML policy definitions
2. **Invariant Compiler**: Parses and validates policy condition expressions
3. **Deterministic Simulation Engine**: Executes evaluations in an immutable context
4. **Runtime Gate**: Coordinates policy evaluation workflow
5. **Audit + Replay Layer**: Logs all evaluations for audit and replay

## Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

## Usage

### Starting the Server

```bash
python app.py
```

The server will start on `http://localhost:5000`.

### API Endpoints

#### POST /evaluate

Evaluate an action against a policy.

**Request:**
```json
{
  "actor_id": "user123",
  "action_type": "mutation",
  "payload": {
    "actor": {
      "max_role": 10
    },
    "request": {
      "role": 5,
      "value": 500
    }
  },
  "policy_id": "mutation_policy_v1"
}
```

**Response:**
```json
{
  "allowed": true,
  "violations": [],
  "simulation_hash": "abc123...",
  "latency_ms": 1.23,
  "evaluation_id": "mutation_policy_v1_user123_abc12345"
}
```

#### GET /health

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "policies_loaded": 2
}
```

#### GET /policies

List all available policies.

**Response:**
```json
{
  "policies": ["mutation_policy_v1", "data_access_policy"]
}
```

## Policy Definition

Policies are defined in YAML format and placed in the `policies/` directory.

**Example:**
```yaml
policy_id: mutation_policy_v1
invariants:
  - id: no_privilege_escalation
    condition: request.role <= actor.max_role
  - id: state_bounds
    condition: request.value <= system.max_threshold
```

## Invariants

Policy evaluation is **deterministic** and **immutable**:

- Policy evaluation must be deterministic (same input → same output)
- Simulation must not mutate canonical state
- All evaluations are auditable

## Failure Modes

The engine handles three main failure modes:

1. **Invalid policy grammar**: Returns 400 error with validation details
2. **Infinite evaluation loops**: Detects and prevents with depth limiting
3. **Missing context bindings**: Returns 400 error identifying missing variables

## Testing

Run the test suite:

```bash
python -m pytest tests/
# or
python -m unittest discover tests
```

## Example Request

```bash
curl -X POST http://localhost:5000/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "actor_id": "user123",
    "action_type": "mutation",
    "payload": {
      "actor": {"max_role": 10},
      "request": {"role": 5, "value": 500}
    },
    "policy_id": "mutation_policy_v1"
  }'
```

## Audit Logs

All evaluations are logged to `audit_logs/` directory in JSONL format, organized by date.

Logs include:
- Request details
- Response details
- Timestamp
- Unique evaluation ID

## Production Deployment

### Docker

Build and run with Docker:

```bash
# Build image
./build-docker.sh

# Run locally
docker run -p 5000:5000 \
  -v $(pwd)/policies:/app/policies:ro \
  -e LOG_FORMAT=json \
  -e METRICS_ENABLED=true \
  constraint-enforcement-engine:latest
```

**Features:**
- Minimal Python 3.12-slim base image
- Non-root runtime (user 1000)
- Multi-stage build for smaller image size
- Reproducible builds
- Health checks built-in

### Kubernetes

Deploy to Kubernetes:

```bash
# Deploy all manifests
./deploy-k8s.sh

# Or manually
kubectl apply -f k8s/
```

**Deployment includes:**
- 3 replicas with rolling updates
- Resource requests/limits (CPU: 250m-1000m, Memory: 256Mi-512Mi)
- Liveness and readiness probes
- Network policies for ingress/egress control
- Service account with minimal permissions
- ConfigMaps for policies and configuration
- Prometheus metrics scraping annotations

### Configuration

All configuration is environment-driven (12-factor compliant):

```bash
# Copy example configuration
cp .env.example .env

# Edit as needed
vim .env
```

**Key environment variables:**
- `WORKERS`: Number of Gunicorn workers (default: 4)
- `LOG_FORMAT`: Logging format - json or text (default: json)
- `METRICS_ENABLED`: Enable Prometheus metrics (default: true)
- `RATE_LIMIT_ENABLED`: Enable rate limiting (default: true)
- `MAX_CONTENT_LENGTH`: Max request size in bytes (default: 1MB)
- `REQUEST_TIMEOUT`: Request timeout in seconds (default: 30)

See `.env.example` for complete configuration options.

### Observability

#### Metrics Endpoint

Prometheus metrics available at `/metrics`:

```bash
curl http://localhost:5000/metrics
```

**Metrics exposed:**
- `policy_evaluations_total`: Counter for evaluations by policy and result
- `policy_evaluation_latency_seconds`: Histogram of evaluation latency
- `http_requests_total`: Counter for all HTTP requests

#### Structured Logging

All logs output as JSON when `LOG_FORMAT=json`:

```json
{
  "asctime": "2026-02-23T10:00:00.000Z",
  "name": "root",
  "levelname": "INFO",
  "message": "Policy evaluation completed",
  "policy_id": "mutation_policy_v1",
  "allowed": true,
  "latency_ms": 1.23
}
```

### Health Checks

#### Liveness Probe

`GET /health` - Checks if application is alive

```bash
curl http://localhost:5000/health
```

#### Readiness Probe

`GET /ready` - Checks if application is ready (policies loaded, compiler warmed)

```bash
curl http://localhost:5000/ready
```

### Concurrency & Performance

- **Thread-safe**: All components use proper locking
- **Worker model**: Gunicorn with configurable sync workers
- **Deterministic**: Hash consistency across all replicas
- **Clock-independent**: No timestamps in evaluation context

### Security & Failure Isolation

- **Rate limiting**: Configurable per-endpoint limits
- **Request size limits**: Configurable max content length
- **Timeouts**: HTTP layer and simulation timeouts
- **CPU bounds**: Evaluation depth limits prevent infinite loops
- **Non-root runtime**: Container runs as UID 1000
- **Read-only filesystem**: Policies mounted read-only
- **Network policies**: Ingress/egress restrictions
