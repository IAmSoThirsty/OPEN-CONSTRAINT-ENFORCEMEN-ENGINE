"""
Production-ready Flask API Server for the Constraint Enforcement Engine.
Includes observability, metrics, rate limiting, and proper error handling.
"""
import logging
import sys
import signal
from flask import Flask, request, jsonify, g
from dataclasses import asdict
from typing import Dict, Any
from pythonjsonlogger import jsonlogger
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import time
import threading

from src.policy_registry import PolicyRegistry
from src.runtime_gate import RuntimeGate, EvaluationRequest
from src.audit_logger import AuditLogger
from config import Config


# Validate configuration
Config.validate()

# Configure structured logging
def setup_logging():
    """Setup structured JSON logging."""
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, Config.LOG_LEVEL))

    # Remove default handlers
    logger.handlers = []

    handler = logging.StreamHandler(sys.stdout)

    if Config.LOG_FORMAT == 'json':
        formatter = jsonlogger.JsonFormatter(
            '%(asctime)s %(name)s %(levelname)s %(message)s',
            timestamp=True
        )
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger


logger = setup_logging()

# Create Flask app
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = Config.MAX_CONTENT_LENGTH

# Initialize components with thread-safe lock
_init_lock = threading.Lock()
_initialized = False
policy_registry = None
runtime_gate = None
audit_logger = None


def initialize_components():
    """Initialize application components in a thread-safe manner."""
    global _initialized, policy_registry, runtime_gate, audit_logger

    with _init_lock:
        if not _initialized:
            logger.info("Initializing application components", extra={
                'policies_dir': Config.POLICIES_DIR,
                'audit_log_dir': Config.AUDIT_LOG_DIR
            })

            policy_registry = PolicyRegistry(policies_dir=Config.POLICIES_DIR)
            runtime_gate = RuntimeGate(policy_registry)
            audit_logger = AuditLogger(log_dir=Config.AUDIT_LOG_DIR)

            _initialized = True
            logger.info("Application components initialized", extra={
                'policies_loaded': len(policy_registry.list_policies())
            })


# Initialize on startup
initialize_components()

# System context from configuration
def get_system_context() -> Dict[str, Any]:
    """Get system context from configuration."""
    return {
        'max_threshold': Config.MAX_THRESHOLD,
    }


# Prometheus metrics
if Config.METRICS_ENABLED:
    REQUEST_COUNT = Counter(
        'policy_evaluations_total',
        'Total number of policy evaluations',
        ['policy_id', 'allowed']
    )

    REQUEST_LATENCY = Histogram(
        'policy_evaluation_latency_seconds',
        'Policy evaluation latency in seconds',
        ['policy_id']
    )

    HTTP_REQUESTS = Counter(
        'http_requests_total',
        'Total HTTP requests',
        ['method', 'endpoint', 'status']
    )

# Rate limiting
limiter = None
if Config.RATE_LIMIT_ENABLED:
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=[Config.RATE_LIMIT_DEFAULT],
        storage_uri=Config.RATE_LIMIT_STORAGE_URL or 'memory://'
    )


@app.before_request
def before_request():
    """Record request start time."""
    g.start_time = time.time()


@app.after_request
def after_request(response):
    """Log request and record metrics."""
    if hasattr(g, 'start_time'):
        latency = time.time() - g.start_time

        logger.info("Request completed", extra={
            'method': request.method,
            'path': request.path,
            'status': response.status_code,
            'latency_ms': round(latency * 1000, 2),
            'remote_addr': request.remote_addr
        })

        if Config.METRICS_ENABLED:
            HTTP_REQUESTS.labels(
                method=request.method,
                endpoint=request.endpoint or 'unknown',
                status=response.status_code
            ).inc()

    return response


@app.route('/evaluate', methods=['POST'])
def evaluate():
    """
    POST /evaluate
    Evaluate an action against a policy.

    Input:
    {
        "actor_id": "string",
        "action_type": "string",
        "payload": {...},
        "policy_id": "string"
    }

    Output:
    {
        "allowed": true/false,
        "violations": ["string"],
        "simulation_hash": "sha256",
        "latency_ms": number,
        "evaluation_id": "string"
    }
    """
    try:
        data = request.get_json()

        if not data:
            logger.warning("Invalid JSON payload received")
            return jsonify({
                'error': 'Invalid JSON payload'
            }), 400

        required_fields = ['actor_id', 'action_type', 'payload', 'policy_id']
        missing_fields = [field for field in required_fields if field not in data]

        if missing_fields:
            logger.warning("Missing required fields", extra={
                'missing_fields': missing_fields
            })
            return jsonify({
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }), 400

        policy_id = data['policy_id']

        eval_request = EvaluationRequest(
            actor_id=data['actor_id'],
            action_type=data['action_type'],
            payload=data['payload'],
            policy_id=policy_id
        )

        start_eval = time.time()
        response = runtime_gate.evaluate(eval_request, get_system_context())
        eval_latency = time.time() - start_eval

        evaluation_id = audit_logger.log_evaluation(eval_request, response)

        result = asdict(response)
        result['evaluation_id'] = evaluation_id

        # Record metrics
        if Config.METRICS_ENABLED:
            REQUEST_COUNT.labels(
                policy_id=policy_id,
                allowed=str(response.allowed).lower()
            ).inc()

            REQUEST_LATENCY.labels(policy_id=policy_id).observe(eval_latency)

        logger.info("Policy evaluation completed", extra={
            'policy_id': policy_id,
            'actor_id': data['actor_id'],
            'allowed': response.allowed,
            'violations': response.violations,
            'latency_ms': response.latency_ms,
            'evaluation_id': evaluation_id
        })

        return jsonify(result), 200

    except ValueError as e:
        logger.error("Policy validation error", extra={
            'error': str(e),
            'error_type': 'InvalidPolicy'
        })
        return jsonify({
            'error': str(e),
            'error_type': 'InvalidPolicy'
        }), 400

    except KeyError as e:
        logger.error("Missing context binding", extra={
            'error': str(e),
            'error_type': 'MissingContextBinding'
        })
        return jsonify({
            'error': str(e),
            'error_type': 'MissingContextBinding'
        }), 400

    except RuntimeError as e:
        error_msg = str(e)
        if 'infinite loop' in error_msg.lower() or 'maximum' in error_msg.lower():
            logger.error("Infinite evaluation loop detected", extra={
                'error': error_msg
            })
            return jsonify({
                'error': error_msg,
                'error_type': 'InfiniteEvaluationLoop'
            }), 500

        logger.error("Evaluation runtime error", extra={
            'error': error_msg
        })
        return jsonify({
            'error': error_msg,
            'error_type': 'EvaluationError'
        }), 500

    except Exception as e:
        logger.exception("Unexpected error during evaluation")
        return jsonify({
            'error': 'Internal server error',
            'error_type': 'InternalError',
            'details': str(e)
        }), 500


@app.route('/health', methods=['GET'])
def health():
    """Liveness probe - checks if the application is alive."""
    return jsonify({
        'status': 'healthy'
    }), 200


@app.route('/ready', methods=['GET'])
def ready():
    """
    Readiness probe - checks if the application is ready to serve traffic.
    Validates that policy registry is loaded and compiler is warmed.
    """
    try:
        if not _initialized:
            return jsonify({
                'status': 'not_ready',
                'reason': 'Components not initialized'
            }), 503

        policies = policy_registry.list_policies()

        if len(policies) == 0:
            logger.warning("No policies loaded")
            return jsonify({
                'status': 'not_ready',
                'reason': 'No policies loaded'
            }), 503

        return jsonify({
            'status': 'ready',
            'policies_loaded': len(policies),
            'policies': policies
        }), 200

    except Exception as e:
        logger.exception("Readiness check failed")
        return jsonify({
            'status': 'not_ready',
            'reason': str(e)
        }), 503


@app.route('/metrics', methods=['GET'])
def metrics():
    """Prometheus metrics endpoint."""
    if not Config.METRICS_ENABLED:
        return jsonify({'error': 'Metrics disabled'}), 404

    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}


@app.route('/policies', methods=['GET'])
def list_policies():
    """List all available policies."""
    policies = policy_registry.list_policies()
    return jsonify({
        'policies': policies
    }), 200


def handle_shutdown(signum, frame):
    """Handle graceful shutdown."""
    logger.info("Received shutdown signal", extra={'signal': signum})
    sys.exit(0)


# Register signal handlers
signal.signal(signal.SIGTERM, handle_shutdown)
signal.signal(signal.SIGINT, handle_shutdown)


if __name__ == '__main__':
    logger.info("Starting application in development mode", extra={
        'host': Config.HOST,
        'port': Config.PORT
    })
    app.run(host=Config.HOST, port=Config.PORT, debug=False)
