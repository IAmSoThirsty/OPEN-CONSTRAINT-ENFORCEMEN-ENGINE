"""
Audit + Replay Layer: Logs all evaluations for audit and replay purposes.
"""
import json
import os
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict

from .runtime_gate import EvaluationRequest, EvaluationResponse


@dataclass
class AuditLogEntry:
    """A single audit log entry."""
    timestamp: str
    request: Dict[str, Any]
    response: Dict[str, Any]
    evaluation_id: str


class AuditLogger:
    """
    Logs all policy evaluations for audit and replay.
    Supports querying and replaying past evaluations.
    """

    def __init__(self, log_dir: str = "audit_logs"):
        self.log_dir = log_dir
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

    def log_evaluation(self, request: EvaluationRequest, response: EvaluationResponse) -> str:
        """
        Log an evaluation request and response.

        Returns:
            evaluation_id: Unique identifier for this evaluation
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        evaluation_id = f"{request.policy_id}_{request.actor_id}_{response.simulation_hash[:8]}"

        entry = AuditLogEntry(
            timestamp=timestamp,
            request=asdict(request),
            response=asdict(response),
            evaluation_id=evaluation_id
        )

        log_filename = self._get_log_filename()
        with open(log_filename, 'a') as f:
            f.write(json.dumps(asdict(entry)) + '\n')

        return evaluation_id

    def _get_log_filename(self) -> str:
        """Get the current log filename based on date."""
        date_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        return os.path.join(self.log_dir, f'audit_{date_str}.jsonl')

    def query_logs(self, policy_id: Optional[str] = None,
                   actor_id: Optional[str] = None,
                   start_date: Optional[str] = None,
                   end_date: Optional[str] = None,
                   limit: int = 100) -> List[AuditLogEntry]:
        """
        Query audit logs with optional filters.

        Args:
            policy_id: Filter by policy ID
            actor_id: Filter by actor ID
            start_date: Filter by start date (ISO format)
            end_date: Filter by end date (ISO format)
            limit: Maximum number of results

        Returns:
            List of matching audit log entries
        """
        results = []

        for filename in sorted(os.listdir(self.log_dir)):
            if not filename.endswith('.jsonl'):
                continue

            filepath = os.path.join(self.log_dir, filename)
            with open(filepath, 'r') as f:
                for line in f:
                    if len(results) >= limit:
                        break

                    try:
                        entry_dict = json.loads(line.strip())
                        entry = AuditLogEntry(**entry_dict)

                        if self._matches_filters(entry, policy_id, actor_id, start_date, end_date):
                            results.append(entry)
                    except Exception:
                        continue

            if len(results) >= limit:
                break

        return results[:limit]

    def _matches_filters(self, entry: AuditLogEntry,
                        policy_id: Optional[str],
                        actor_id: Optional[str],
                        start_date: Optional[str],
                        end_date: Optional[str]) -> bool:
        """Check if an entry matches the specified filters."""
        if policy_id and entry.request.get('policy_id') != policy_id:
            return False

        if actor_id and entry.request.get('actor_id') != actor_id:
            return False

        if start_date and entry.timestamp < start_date:
            return False

        if end_date and entry.timestamp > end_date:
            return False

        return True

    def replay_evaluation(self, evaluation_id: str) -> Optional[AuditLogEntry]:
        """
        Retrieve a specific evaluation by its ID for replay.

        Returns:
            The audit log entry if found, None otherwise
        """
        for filename in os.listdir(self.log_dir):
            if not filename.endswith('.jsonl'):
                continue

            filepath = os.path.join(self.log_dir, filename)
            with open(filepath, 'r') as f:
                for line in f:
                    try:
                        entry_dict = json.loads(line.strip())
                        entry = AuditLogEntry(**entry_dict)
                        if entry.evaluation_id == evaluation_id:
                            return entry
                    except Exception:
                        continue

        return None
