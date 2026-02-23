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
