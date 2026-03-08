"""
STRYDER AI - Cascade Agent (Failure Prediction)
=================================================
@Cascade — The Predictor

Role: Predicts cascading failures across the supply chain.
Analyzes dependency graphs, delay propagation, and systemic risks.
Warns before small disruptions become large-scale failures.
"""

import json
from backend.agents.base_agent import BaseAgent, Decision, AgentStatus


class CascadeAgent(BaseAgent):
    """
    The Cascade agent predicts systemic failure cascades.
    It models how a single disruption can propagate across
    the supply chain through shared routes, carriers, and hubs.
    """

    def __init__(self):
        super().__init__(
            name="Cascade",
            role="Cascade Failure Predictor",
            description="Predicts how disruptions cascade across the supply chain. "
                        "Models dependency graphs between shipments, carriers, and hubs. "
                        "Provides early warning before small delays become systemic failures.",
            avatar_emoji="🌊",
            color="#06b6d4",
        )
        self._cascade_model = None

    def _load_model(self):
        """Lazy-load the cascade ML model."""
        if self._cascade_model is None:
            try:
                from backend.ml_models.cascade_model import predict
                self._cascade_model = predict
            except Exception:
                pass

    def observe(self, world_state: dict) -> dict:
        """Identify cascade risk factors in the supply chain."""
        self.status = AgentStatus.OBSERVING

        shipments = world_state.get("shipments", [])
        warehouses = world_state.get("warehouses", [])

        # Find disrupted shipments and their shared dependencies
        disrupted = [s for s in shipments if s.get("has_disruption")]
        affected_hubs = set()
        affected_carriers = set()
        affected_routes = set()

        for s in disrupted:
            if s.get("origin_hub"):
                affected_hubs.add(s["origin_hub"])
            if s.get("destination_hub"):
                affected_hubs.add(s["destination_hub"])
            if s.get("carrier_id"):
                affected_carriers.add(s["carrier_id"])
            if s.get("route_path"):
                for hub in s["route_path"].split(","):
                    affected_routes.add(hub)

        # Find other shipments sharing these dependencies (cascade candidates)
        cascade_candidates = []
        for s in shipments:
            if s in disrupted:
                continue
            shared = 0
            if s.get("origin_hub") in affected_hubs:
                shared += 1
            if s.get("destination_hub") in affected_hubs:
                shared += 1
            if s.get("carrier_id") in affected_carriers:
                shared += 1
            if s.get("route_path"):
                for hub in s["route_path"].split(","):
                    if hub in affected_routes:
                        shared += 1
                        break
            if shared > 0:
                cascade_candidates.append({
                    "shipment_id": s.get("shipment_id"),
                    "shared_dependencies": shared,
                    "carrier": s.get("carrier_name"),
                    "route": s.get("route_path"),
                })

        # Sort by exposure
        cascade_candidates.sort(key=lambda x: x["shared_dependencies"], reverse=True)

        return {
            "disrupted_count": len(disrupted),
            "affected_hubs": list(affected_hubs),
            "affected_carriers": list(affected_carriers),
            "cascade_candidates": cascade_candidates[:10],
            "total_cascade_exposure": len(cascade_candidates),
            "congested_hubs": [w for w in warehouses if w.get("congestion_level") == "HIGH"],
        }

    def reason(self, observations: dict) -> dict:
        """Predict cascade probability and impact."""
        self.status = AgentStatus.REASONING
        self._load_model()

        # Run ML model if available
        ml_predictions = {}
        if self._cascade_model:
            try:
                result = self._cascade_model({
                    "delay_minutes": observations.get("disrupted_count", 0) * 60,
                    "is_delayed": 1 if observations.get("disrupted_count", 0) > 0 else 0,
                    "delay_rate": min(1.0, observations.get("disrupted_count", 0) / max(1, observations.get("total_cascade_exposure", 1))),
                })
                ml_predictions["cascade_model"] = result
            except Exception:
                pass

        system = """You are the Cascade agent in STRYDER AI.
You predict how disruptions cascade through the supply chain.
Analyze dependency graphs and estimate propagation probability.
Think about: shared carriers, shared routes, hub bottlenecks."""

        user = f"""Current disruption state:
- {observations['disrupted_count']} active disruptions
- Affected hubs: {observations['affected_hubs']}
- Affected carriers: {observations['affected_carriers']}
- {observations['total_cascade_exposure']} shipments at cascade risk
- Top cascade candidates: {json.dumps(observations['cascade_candidates'][:5], default=str)}
- ML model prediction: {json.dumps(ml_predictions, default=str)}

Provide JSON with: cascade_probability (0-1), estimated_affected_shipments,
propagation_paths (list), mitigation_actions, time_to_cascade_hours"""

        analysis = self.call_llm_json(system, user)
        analysis["ml_predictions"] = ml_predictions
        analysis["raw_observations"] = observations
        return analysis

    def decide(self, analysis: dict) -> Decision:
        """Decide on cascade prevention measures."""
        cascade_prob = analysis.get("cascade_probability", 0)
        observations = analysis.get("raw_observations", {})

        action = {
            "cascade_probability": cascade_prob,
            "estimated_affected": analysis.get("estimated_affected_shipments", 0),
            "preventive_actions": analysis.get("mitigation_actions", []),
            "isolate_hubs": observations.get("affected_hubs", []),
            "warn_agents": ["Executor", "Sentinel"] if cascade_prob > 0.5 else [],
        }

        confidence = 0.8 if analysis.get("ml_predictions") else 0.6
        priority = 1 if cascade_prob > 0.7 else 2 if cascade_prob > 0.4 else 3

        return Decision(
            agent_name=self.name,
            decision_type="CASCADE_PREDICTION",
            context=analysis,
            reasoning=f"Cascade probability: {cascade_prob:.0%}. "
                      f"{observations.get('total_cascade_exposure', 0)} shipments at risk.",
            action=action,
            confidence=confidence,
            priority=priority,
        )

    def act(self, decision: Decision) -> dict:
        """Publish cascade warning and preventive measures."""
        return {
            "success": True,
            "action": "CASCADE_WARNING_PUBLISHED",
            "cascade_probability": decision.action.get("cascade_probability"),
            "preventive_actions_count": len(decision.action.get("preventive_actions", [])),
            "agents_warned": decision.action.get("warn_agents", []),
        }
