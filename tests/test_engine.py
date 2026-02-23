"""
Test suite for the Constraint Enforcement Engine.
"""
import unittest
import json
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.policy_registry import PolicyRegistry, Policy, Invariant
from src.invariant_compiler import InvariantCompiler
from src.simulation_engine import DeterministicSimulationEngine
from src.runtime_gate import RuntimeGate, EvaluationRequest
from src.audit_logger import AuditLogger


class TestPolicyRegistry(unittest.TestCase):
    """Test the Policy Registry."""

    def test_load_policy(self):
        """Test loading a policy from YAML."""
        registry = PolicyRegistry()
        policy = registry.get_policy('mutation_policy_v1')
        self.assertIsNotNone(policy)
        self.assertEqual(policy.policy_id, 'mutation_policy_v1')
        self.assertEqual(len(policy.invariants), 2)

    def test_missing_policy(self):
        """Test retrieving a non-existent policy."""
        registry = PolicyRegistry()
        policy = registry.get_policy('nonexistent_policy')
        self.assertIsNone(policy)


class TestInvariantCompiler(unittest.TestCase):
    """Test the Invariant Compiler."""

    def setUp(self):
        self.compiler = InvariantCompiler()

    def test_compile_simple_condition(self):
        """Test compiling a simple condition."""
        compiled = self.compiler.compile('actor.role <= 5')
        self.assertIsNotNone(compiled)
        self.assertIn('actor.role', compiled.variables)

    def test_dangerous_pattern_rejection(self):
        """Test that dangerous patterns are rejected."""
        with self.assertRaises(ValueError):
            self.compiler.compile('import os')

        with self.assertRaises(ValueError):
            self.compiler.compile('__import__("os")')

    def test_evaluate_condition(self):
        """Test evaluating a compiled condition."""
        compiled = self.compiler.compile('actor.role <= 5')
        context = {'actor': {'role': 3}}
        result = self.compiler.evaluate(compiled, context)
        self.assertTrue(result)

        context = {'actor': {'role': 10}}
        result = self.compiler.evaluate(compiled, context)
        self.assertFalse(result)

    def test_missing_context_binding(self):
        """Test that missing context raises an error."""
        compiled = self.compiler.compile('actor.role <= 5')
        context = {}
        with self.assertRaises(KeyError):
            self.compiler.evaluate(compiled, context)


class TestDeterministicSimulationEngine(unittest.TestCase):
    """Test the Deterministic Simulation Engine."""

    def setUp(self):
        self.engine = DeterministicSimulationEngine()

    def test_immutable_copy(self):
        """Test that simulation creates immutable copy."""
        original = {'actor': {'role': 5}}
        simulated = self.engine.simulate(original)

        simulated['actor']['role'] = 10

        self.assertEqual(original['actor']['role'], 5)

    def test_deterministic_hash(self):
        """Test that hash is deterministic."""
        context = {'actor': {'role': 5}}
        result = {'allowed': True, 'violations': []}

        hash1 = self.engine.compute_hash(context, result)
        hash2 = self.engine.compute_hash(context, result)

        self.assertEqual(hash1, hash2)

    def test_different_inputs_different_hash(self):
        """Test that different inputs produce different hashes."""
        context1 = {'actor': {'role': 5}}
        context2 = {'actor': {'role': 6}}
        result = {'allowed': True, 'violations': []}

        hash1 = self.engine.compute_hash(context1, result)
        hash2 = self.engine.compute_hash(context2, result)

        self.assertNotEqual(hash1, hash2)


class TestRuntimeGate(unittest.TestCase):
    """Test the Runtime Gate."""

    def setUp(self):
        self.registry = PolicyRegistry()
        self.gate = RuntimeGate(self.registry)

    def test_successful_evaluation(self):
        """Test successful policy evaluation."""
        request = EvaluationRequest(
            actor_id='user123',
            action_type='mutation',
            payload={
                'actor': {'max_role': 10},
                'request': {'role': 5, 'value': 500}
            },
            policy_id='mutation_policy_v1'
        )

        system_context = {'max_threshold': 1000}
        response = self.gate.evaluate(request, system_context)

        self.assertTrue(response.allowed)
        self.assertEqual(len(response.violations), 0)
        self.assertIsNotNone(response.simulation_hash)
        self.assertGreater(response.latency_ms, 0)

    def test_policy_violation(self):
        """Test policy violation detection."""
        request = EvaluationRequest(
            actor_id='user123',
            action_type='mutation',
            payload={
                'actor': {'max_role': 5},
                'request': {'role': 10, 'value': 500}
            },
            policy_id='mutation_policy_v1'
        )

        system_context = {'max_threshold': 1000}
        response = self.gate.evaluate(request, system_context)

        self.assertFalse(response.allowed)
        self.assertIn('no_privilege_escalation', response.violations)

    def test_multiple_violations(self):
        """Test multiple policy violations."""
        request = EvaluationRequest(
            actor_id='user123',
            action_type='mutation',
            payload={
                'actor': {'max_role': 5},
                'request': {'role': 10, 'value': 2000}
            },
            policy_id='mutation_policy_v1'
        )

        system_context = {'max_threshold': 1000}
        response = self.gate.evaluate(request, system_context)

        self.assertFalse(response.allowed)
        self.assertEqual(len(response.violations), 2)

    def test_nonexistent_policy(self):
        """Test evaluation with nonexistent policy."""
        request = EvaluationRequest(
            actor_id='user123',
            action_type='mutation',
            payload={},
            policy_id='nonexistent_policy'
        )

        with self.assertRaises(ValueError):
            self.gate.evaluate(request, {})


class TestAuditLogger(unittest.TestCase):
    """Test the Audit Logger."""

    def setUp(self):
        self.logger = AuditLogger(log_dir='/tmp/test_audit_logs')

    def tearDown(self):
        import shutil
        if os.path.exists('/tmp/test_audit_logs'):
            shutil.rmtree('/tmp/test_audit_logs')

    def test_log_evaluation(self):
        """Test logging an evaluation."""
        from src.runtime_gate import EvaluationRequest, EvaluationResponse

        request = EvaluationRequest(
            actor_id='user123',
            action_type='mutation',
            payload={},
            policy_id='test_policy'
        )

        response = EvaluationResponse(
            allowed=True,
            violations=[],
            simulation_hash='abc123',
            latency_ms=1.5
        )

        evaluation_id = self.logger.log_evaluation(request, response)
        self.assertIsNotNone(evaluation_id)

    def test_query_logs(self):
        """Test querying audit logs."""
        from src.runtime_gate import EvaluationRequest, EvaluationResponse

        request = EvaluationRequest(
            actor_id='user123',
            action_type='mutation',
            payload={},
            policy_id='test_policy'
        )

        response = EvaluationResponse(
            allowed=True,
            violations=[],
            simulation_hash='abc123',
            latency_ms=1.5
        )

        self.logger.log_evaluation(request, response)

        logs = self.logger.query_logs(policy_id='test_policy')
        self.assertGreater(len(logs), 0)


if __name__ == '__main__':
    unittest.main()
