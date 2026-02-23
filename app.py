"""
Flask API Server for the Constraint Enforcement Engine.
"""
from flask import Flask, request, jsonify
from dataclasses import asdict
from typing import Dict, Any

from src.policy_registry import PolicyRegistry
from src.runtime_gate import RuntimeGate, EvaluationRequest
from src.audit_logger import AuditLogger


app = Flask(__name__)

policy_registry = PolicyRegistry()
runtime_gate = RuntimeGate(policy_registry)
audit_logger = AuditLogger()

system_context = {
    'max_threshold': 1000,
}


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
        "latency_ms": number
    }
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({
                'error': 'Invalid JSON payload'
            }), 400

        required_fields = ['actor_id', 'action_type', 'payload', 'policy_id']
        missing_fields = [field for field in required_fields if field not in data]

        if missing_fields:
            return jsonify({
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }), 400

        eval_request = EvaluationRequest(
            actor_id=data['actor_id'],
            action_type=data['action_type'],
            payload=data['payload'],
            policy_id=data['policy_id']
        )

        response = runtime_gate.evaluate(eval_request, system_context)

        evaluation_id = audit_logger.log_evaluation(eval_request, response)

        result = asdict(response)
        result['evaluation_id'] = evaluation_id

        return jsonify(result), 200

    except ValueError as e:
        return jsonify({
            'error': str(e),
            'error_type': 'InvalidPolicy'
        }), 400

    except KeyError as e:
        return jsonify({
            'error': str(e),
            'error_type': 'MissingContextBinding'
        }), 400

    except RuntimeError as e:
        error_msg = str(e)
        if 'infinite loop' in error_msg.lower() or 'maximum' in error_msg.lower():
            return jsonify({
                'error': error_msg,
                'error_type': 'InfiniteEvaluationLoop'
            }), 500
        return jsonify({
            'error': error_msg,
            'error_type': 'EvaluationError'
        }), 500

    except Exception as e:
        return jsonify({
            'error': 'Internal server error',
            'error_type': 'InternalError',
            'details': str(e)
        }), 500


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'policies_loaded': len(policy_registry.list_policies())
    }), 200


@app.route('/policies', methods=['GET'])
def list_policies():
    """List all available policies."""
    return jsonify({
        'policies': policy_registry.list_policies()
    }), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
