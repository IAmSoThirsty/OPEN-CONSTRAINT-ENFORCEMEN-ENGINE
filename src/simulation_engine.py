"""
Deterministic Simulation Engine: Executes policy evaluation without mutating canonical state.
"""
import hashlib
import json
import copy
from typing import Any, Dict
from dataclasses import dataclass, asdict


@dataclass
class SimulationResult:
    """Result of a deterministic simulation."""
    allowed: bool
    violations: list
    simulation_hash: str
    context_snapshot: Dict[str, Any]


class DeterministicSimulationEngine:
    """
    Executes policy evaluations in a deterministic, immutable manner.
    Ensures that simulations do not mutate canonical state.
    """

    def __init__(self):
        pass

    def simulate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create an immutable copy of the context for simulation.
        Returns a deep copy to ensure no mutations affect the original.
        """
        return copy.deepcopy(context)

    def compute_hash(self, context: Dict[str, Any], evaluation_result: Dict[str, Any]) -> str:
        """
        Compute a deterministic SHA-256 hash of the simulation.
        This hash represents the entire evaluation state.
        """
        hash_input = {
            'context': self._normalize_for_hash(context),
            'result': self._normalize_for_hash(evaluation_result)
        }

        json_str = json.dumps(hash_input, sort_keys=True, separators=(',', ':'))

        hash_object = hashlib.sha256(json_str.encode('utf-8'))
        return hash_object.hexdigest()

    def _normalize_for_hash(self, obj: Any) -> Any:
        """
        Normalize objects for consistent hashing.
        Ensures deterministic serialization.
        """
        if isinstance(obj, dict):
            return {k: self._normalize_for_hash(v) for k, v in sorted(obj.items())}
        elif isinstance(obj, list):
            return [self._normalize_for_hash(item) for item in obj]
        elif isinstance(obj, (str, int, float, bool, type(None))):
            return obj
        else:
            return str(obj)

    def create_result(self, allowed: bool, violations: list, context: Dict[str, Any]) -> SimulationResult:
        """Create a simulation result with computed hash."""
        evaluation_result = {
            'allowed': allowed,
            'violations': violations
        }

        simulation_hash = self.compute_hash(context, evaluation_result)

        return SimulationResult(
            allowed=allowed,
            violations=violations,
            simulation_hash=simulation_hash,
            context_snapshot=self.simulate(context)
        )

    def verify_determinism(self, context: Dict[str, Any], result: SimulationResult) -> bool:
        """
        Verify that re-evaluation produces the same hash.
        This ensures deterministic behavior.
        """
        evaluation_result = {
            'allowed': result.allowed,
            'violations': result.violations
        }

        recomputed_hash = self.compute_hash(context, evaluation_result)
        return recomputed_hash == result.simulation_hash
