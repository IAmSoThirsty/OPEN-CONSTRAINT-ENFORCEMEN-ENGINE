#!/usr/bin/env python3
"""
Example usage script for the Constraint Enforcement Engine.
"""
import json
from src.policy_registry import PolicyRegistry
from src.runtime_gate import RuntimeGate, EvaluationRequest
from src.audit_logger import AuditLogger


def main():
    print("=== Constraint Enforcement Engine Demo ===\n")

    registry = PolicyRegistry()
    gate = RuntimeGate(registry)
    logger = AuditLogger()

    print(f"Loaded policies: {registry.list_policies()}\n")

    system_context = {'max_threshold': 1000}

    print("--- Test 1: Successful evaluation ---")
    request1 = EvaluationRequest(
        actor_id='user123',
        action_type='mutation',
        payload={
            'actor': {'max_role': 10},
            'request': {'role': 5, 'value': 500}
        },
        policy_id='mutation_policy_v1'
    )

    response1 = gate.evaluate(request1, system_context)
    eval_id1 = logger.log_evaluation(request1, response1)

    print(f"Allowed: {response1.allowed}")
    print(f"Violations: {response1.violations}")
    print(f"Hash: {response1.simulation_hash}")
    print(f"Latency: {response1.latency_ms}ms")
    print(f"Evaluation ID: {eval_id1}\n")

    print("--- Test 2: Privilege escalation violation ---")
    request2 = EvaluationRequest(
        actor_id='user456',
        action_type='mutation',
        payload={
            'actor': {'max_role': 5},
            'request': {'role': 10, 'value': 300}
        },
        policy_id='mutation_policy_v1'
    )

    response2 = gate.evaluate(request2, system_context)
    eval_id2 = logger.log_evaluation(request2, response2)

    print(f"Allowed: {response2.allowed}")
    print(f"Violations: {response2.violations}")
    print(f"Hash: {response2.simulation_hash}")
    print(f"Latency: {response2.latency_ms}ms")
    print(f"Evaluation ID: {eval_id2}\n")

    print("--- Test 3: Multiple violations ---")
    request3 = EvaluationRequest(
        actor_id='user789',
        action_type='mutation',
        payload={
            'actor': {'max_role': 3},
            'request': {'role': 10, 'value': 2000}
        },
        policy_id='mutation_policy_v1'
    )

    response3 = gate.evaluate(request3, system_context)
    eval_id3 = logger.log_evaluation(request3, response3)

    print(f"Allowed: {response3.allowed}")
    print(f"Violations: {response3.violations}")
    print(f"Hash: {response3.simulation_hash}")
    print(f"Latency: {response3.latency_ms}ms")
    print(f"Evaluation ID: {eval_id3}\n")

    print("--- Audit Log Query ---")
    logs = logger.query_logs(policy_id='mutation_policy_v1', limit=10)
    print(f"Found {len(logs)} audit log entries for mutation_policy_v1")

    print("\n=== Demo Complete ===")


if __name__ == '__main__':
    main()
