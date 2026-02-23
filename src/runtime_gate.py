"""
Runtime Gate: Evaluates actions against policy invariants.
"""
import time
from typing import Dict, Any, List
from dataclasses import dataclass, asdict

from .policy_registry import PolicyRegistry, Policy
from .invariant_compiler import InvariantCompiler
from .simulation_engine import DeterministicSimulationEngine, SimulationResult


@dataclass
class EvaluationRequest:
    """Request to evaluate an action against a policy."""
    actor_id: str
    action_type: str
    payload: Dict[str, Any]
    policy_id: str


@dataclass
class EvaluationResponse:
    """Response from policy evaluation."""
    allowed: bool
    violations: List[str]
    simulation_hash: str
    latency_ms: float


class RuntimeGate:
    """
    Main runtime gate for policy evaluation.
    Coordinates policy lookup, invariant evaluation, and simulation.
    """

    def __init__(self, policy_registry: PolicyRegistry):
        self.policy_registry = policy_registry
        self.compiler = InvariantCompiler()
        self.simulation_engine = DeterministicSimulationEngine()

    def evaluate(self, request: EvaluationRequest, system_context: Dict[str, Any] = None) -> EvaluationResponse:
        """
        Evaluate a request against a policy.

        Args:
            request: The evaluation request
            system_context: Additional system context (e.g., max_threshold)

        Returns:
            EvaluationResponse with result and metrics
        """
        start_time = time.time()

        policy = self.policy_registry.get_policy(request.policy_id)
        if not policy:
            raise ValueError(f"Policy not found: {request.policy_id}")

        context = self._build_context(request, system_context or {})

        simulated_context = self.simulation_engine.simulate(context)

        violations = []
        for invariant in policy.invariants:
            try:
                compiled = self.compiler.compile(invariant.condition)
                result = self.compiler.evaluate(compiled, simulated_context)

                if not result:
                    violations.append(invariant.id)

            except KeyError as e:
                raise ValueError(f"Missing context for invariant {invariant.id}: {str(e)}")
            except RuntimeError as e:
                raise RuntimeError(f"Evaluation failed for invariant {invariant.id}: {str(e)}")

        allowed = len(violations) == 0

        simulation_result = self.simulation_engine.create_result(
            allowed=allowed,
            violations=violations,
            context=simulated_context
        )

        end_time = time.time()
        latency_ms = (end_time - start_time) * 1000

        return EvaluationResponse(
            allowed=allowed,
            violations=violations,
            simulation_hash=simulation_result.simulation_hash,
            latency_ms=round(latency_ms, 2)
        )

    def _build_context(self, request: EvaluationRequest, system_context: Dict[str, Any]) -> Dict[str, Any]:
        """Build the evaluation context from request and system state."""
        return {
            'actor': {
                'id': request.actor_id,
                **request.payload.get('actor', {})
            },
            'request': {
                'action_type': request.action_type,
                **request.payload.get('request', {})
            },
            'system': system_context,
            'payload': request.payload
        }
