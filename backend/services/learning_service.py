"""
STRYDER AI - Learning Service
================================
Tracks agent learning metrics: model accuracy trends,
decision success rates, confidence calibration, and
feedback loops for the Agent Learning Hub.
"""

from datetime import datetime
from typing import Optional
import threading


class LearningService:
    """Tracks agent learning and improvement metrics."""

    def __init__(self):
        self.learning_entries: list[dict] = []
        self.model_metrics: dict = {}
        self._lock = threading.Lock()

        # Initialize model baselines
        self.model_metrics = {
            "eta_prediction": {"accuracy": 0.9998, "samples": 0, "trend": "stable"},
            "delay_risk": {"accuracy": 1.00, "samples": 0, "trend": "stable"},
            "carrier_reliability": {"accuracy": 0.918, "samples": 0, "trend": "stable"},
            "hub_congestion": {"accuracy": 1.00, "samples": 0, "trend": "stable"},
            "cascade_failure": {"accuracy": 1.00, "samples": 0, "trend": "stable"},
        }

    def record_learning(self, agent_name: str, decision_id: str,
                        outcome: str, feedback: str = "",
                        confidence_was: float = 0, accuracy: float = 0):
        """Record a learning event from a decision outcome."""
        entry = {
            "id": len(self.learning_entries) + 1,
            "timestamp": datetime.now().isoformat(),
            "agent": agent_name,
            "decision_id": decision_id,
            "outcome": outcome,
            "feedback": feedback,
            "confidence_was": confidence_was,
            "accuracy": accuracy,
        }
        with self._lock:
            self.learning_entries.append(entry)
        return entry

    def update_model_metric(self, model_name: str, accuracy: float, samples: int = 1):
        """Update a model's accuracy metric."""
        with self._lock:
            if model_name in self.model_metrics:
                old = self.model_metrics[model_name]["accuracy"]
                self.model_metrics[model_name]["accuracy"] = accuracy
                self.model_metrics[model_name]["samples"] += samples
                self.model_metrics[model_name]["trend"] = (
                    "improving" if accuracy > old
                    else "declining" if accuracy < old
                    else "stable"
                )

    def get_agent_performance(self, agent_name: Optional[str] = None) -> dict:
        """Get performance metrics for agents."""
        with self._lock:
            entries = self.learning_entries
            if agent_name:
                entries = [e for e in entries if e["agent"] == agent_name]
            if not entries:
                return {"total": 0, "success_rate": 0}
            successes = sum(1 for e in entries if e["outcome"] == "SUCCESS")
            return {
                "total": len(entries),
                "success_rate": round(successes / len(entries), 3) if entries else 0,
                "avg_accuracy": round(
                    sum(e.get("accuracy", 0) for e in entries) / len(entries), 3
                ) if entries else 0,
            }

    def get_model_metrics(self) -> dict:
        """Get all model metrics for the Learning Hub."""
        with self._lock:
            return dict(self.model_metrics)

    def get_learning_summary(self) -> dict:
        """Summary for the Learning Hub dashboard."""
        with self._lock:
            return {
                "total_learning_events": len(self.learning_entries),
                "model_metrics": dict(self.model_metrics),
                "agent_performance": {
                    name: self.get_agent_performance(name)
                    for name in set(e["agent"] for e in self.learning_entries)
                } if self.learning_entries else {},
                "recent_events": self.learning_entries[-5:],
            }


# Singleton
_service: Optional[LearningService] = None

def get_learning_service() -> LearningService:
    global _service
    if _service is None:
        _service = LearningService()
    return _service
