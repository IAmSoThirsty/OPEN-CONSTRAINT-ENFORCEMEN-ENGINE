"""
Policy Registry: Loads and manages YAML policy definitions.
"""
import yaml
import os
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class Invariant:
    """Represents a single invariant rule."""
    id: str
    condition: str


@dataclass
class Policy:
    """Represents a complete policy with its invariants."""
    policy_id: str
    invariants: List[Invariant]


class PolicyRegistry:
    """Manages loading and retrieval of policy definitions."""

    def __init__(self, policies_dir: str = "policies"):
        self.policies_dir = policies_dir
        self.policies: Dict[str, Policy] = {}
        self._load_policies()

    def _load_policies(self) -> None:
        """Load all YAML policies from the policies directory."""
        if not os.path.exists(self.policies_dir):
            os.makedirs(self.policies_dir)
            return

        for filename in os.listdir(self.policies_dir):
            if filename.endswith(('.yaml', '.yml')):
                filepath = os.path.join(self.policies_dir, filename)
                try:
                    self._load_policy_file(filepath)
                except Exception as e:
                    raise ValueError(f"Failed to load policy {filename}: {str(e)}")

    def _load_policy_file(self, filepath: str) -> None:
        """Load a single policy file."""
        with open(filepath, 'r') as f:
            data = yaml.safe_load(f)

        if not data:
            raise ValueError(f"Empty policy file: {filepath}")

        if 'policy_id' not in data:
            raise ValueError(f"Missing policy_id in {filepath}")

        if 'invariants' not in data or not isinstance(data['invariants'], list):
            raise ValueError(f"Missing or invalid invariants in {filepath}")

        invariants = []
        for inv_data in data['invariants']:
            if 'id' not in inv_data or 'condition' not in inv_data:
                raise ValueError(f"Invalid invariant format in {filepath}")
            invariants.append(Invariant(
                id=inv_data['id'],
                condition=inv_data['condition']
            ))

        policy = Policy(
            policy_id=data['policy_id'],
            invariants=invariants
        )

        self.policies[policy.policy_id] = policy

    def get_policy(self, policy_id: str) -> Optional[Policy]:
        """Retrieve a policy by its ID."""
        return self.policies.get(policy_id)

    def list_policies(self) -> List[str]:
        """List all available policy IDs."""
        return list(self.policies.keys())
