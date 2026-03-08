"""
STRYDER AI - Decision Logger
==============================
Logs all agent decisions for the Decision Replay system.
Provides queryable history with filtering and analytics.
"""

from datetime import datetime
from typing import Optional
import threading


class DecisionLogger:
    """Thread-safe decision logger for agent audit trail."""

    def __init__(self, max_entries: int = 500):
        self.entries: list[dict] = []
        self.max_entries = max_entries
        self._lock = threading.Lock()

    def log(self, agent_name: str, decision_type: str, reasoning: str,
            action: dict, confidence: float, context: Optional[dict] = None,
            priority: int = 3, loop_id: Optional[str] = None) -> dict:
        """Log a decision entry."""
        entry = {
            "id": len(self.entries) + 1,
            "timestamp": datetime.now().isoformat(),
            "agent": agent_name,
            "type": decision_type,
            "reasoning": reasoning,
            "action": action,
            "confidence": confidence,
            "priority": priority,
            "context": context or {},
            "loop_id": loop_id,
            "outcome": None,
        }

        with self._lock:
            self.entries.append(entry)
            if len(self.entries) > self.max_entries:
                self.entries = self.entries[-self.max_entries:]

        return entry

    def log_from_trace(self, loop_trace: dict):
        """Extract and log all decisions from a full loop trace."""
        loop_id = loop_trace.get("loop_id")
        decisions = loop_trace.get("decisions", [])
        for d in decisions:
            if isinstance(d, dict) and d.get("agent"):
                self.log(
                    agent_name=d.get("agent", "Unknown"),
                    decision_type=d.get("type", "UNKNOWN"),
                    reasoning=d.get("reasoning", ""),
                    action=d.get("action", {}),
                    confidence=d.get("confidence", 0),
                    priority=d.get("priority", 3),
                    context=d.get("context", {}),
                    loop_id=loop_id,
                )

    def get_recent(self, limit: int = 20) -> list:
        """Get most recent decisions."""
        with self._lock:
            return self.entries[-limit:]

    def get_by_agent(self, agent_name: str, limit: int = 20) -> list:
        """Get decisions by a specific agent."""
        with self._lock:
            filtered = [e for e in self.entries if e["agent"] == agent_name]
            return filtered[-limit:]

    def get_by_type(self, decision_type: str, limit: int = 20) -> list:
        """Get decisions by type."""
        with self._lock:
            filtered = [e for e in self.entries if e["type"] == decision_type]
            return filtered[-limit:]

    def get_by_loop(self, loop_id: str) -> list:
        """Get all decisions from a specific loop execution."""
        with self._lock:
            return [e for e in self.entries if e.get("loop_id") == loop_id]

    def get_stats(self) -> dict:
        """Get decision statistics."""
        with self._lock:
            if not self.entries:
                return {"total": 0}
            agent_counts = {}
            type_counts = {}
            avg_confidence = 0
            for e in self.entries:
                agent_counts[e["agent"]] = agent_counts.get(e["agent"], 0) + 1
                type_counts[e["type"]] = type_counts.get(e["type"], 0) + 1
                avg_confidence += e.get("confidence", 0)
            avg_confidence /= len(self.entries)
            return {
                "total": len(self.entries),
                "by_agent": agent_counts,
                "by_type": type_counts,
                "avg_confidence": round(avg_confidence, 3),
            }


# Singleton
_logger: Optional[DecisionLogger] = None

def get_decision_logger() -> DecisionLogger:
    global _logger
    if _logger is None:
        _logger = DecisionLogger()
    return _logger
