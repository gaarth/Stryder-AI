"""
STRYDER AI - Strategist Agent (Reasoning + Model Access)
=========================================================
@Strategist — The Thinker

Role: Analysis engine with direct access to all 5 ML models.
Generates strategic recommendations using LLM + ML model outputs.
Subtags: @Strategist:ETA_AGENT, @Strategist:DELAY_AGENT, etc.
"""

import json
from pathlib import Path
from backend.agents.base_agent import BaseAgent, Decision, AgentStatus

# ML model imports (lazy loaded)
MODELS_DIR = Path(__file__).resolve().parent.parent / "ml_models" / "saved_models"


class StrategistAgent(BaseAgent):
    """
    The Strategist reasons about logistics problems using ML models + LLM.
    It receives alerts from Sentinel and produces actionable recommendations.
    """

    def __init__(self):
        super().__init__(
            name="Strategist",
            role="Analysis & Strategy Engine",
            description="Combines 5 ML models (ETA, Delay Risk, Carrier Reliability, "
                        "Hub Congestion, Cascade Failure) with LLM reasoning to generate "
                        "strategic recommendations for logistics operations.",
            avatar_emoji="🧠",
            color="#8b5cf6",
        )
        self._models_loaded = False
        self._eta_model = None
        self._delay_model = None
        self._carrier_model = None
        self._hub_model = None
        self._cascade_model = None

    def _load_models(self):
        """Lazy-load ML models on first use."""
        if self._models_loaded:
            return
        try:
            from backend.ml_models.eta_model import predict as eta_predict
            from backend.ml_models.delay_model import predict as delay_predict
            from backend.ml_models.carrier_model import predict as carrier_predict
            from backend.ml_models.hub_congestion_model import predict as hub_predict
            from backend.ml_models.cascade_model import predict as cascade_predict

            self._eta_model = eta_predict
            self._delay_model = delay_predict
            self._carrier_model = carrier_predict
            self._hub_model = hub_predict
            self._cascade_model = cascade_predict
            self._models_loaded = True
        except Exception as e:
            self.errors.append({"error": f"Model load failed: {e}"})

    def run_model(self, model_name: str, input_data: dict) -> dict:
        """Run a specific ML model by name (subtag dispatch)."""
        self._load_models()
        model_map = {
            "ETA_AGENT": self._eta_model,
            "DELAY_AGENT": self._delay_model,
            "CARRIER_AGENT": self._carrier_model,
            "HUB_AGENT": self._hub_model,
            "CASCADE_MODEL": self._cascade_model,
        }
        model_fn = model_map.get(model_name)
        if model_fn:
            try:
                return model_fn(input_data)
            except Exception as e:
                return {"error": str(e)}
        return {"error": f"Unknown model: {model_name}"}

    def observe(self, world_state: dict) -> dict:
        """Gather data relevant for strategic analysis."""
        self.status = AgentStatus.OBSERVING

        alerts = world_state.get("alerts", [])
        shipments = world_state.get("shipments", [])
        carriers = world_state.get("carriers", [])

        # Summarize strategic picture
        in_transit = [s for s in shipments if s.get("status") == "IN_TRANSIT"]
        delayed = [s for s in shipments if s.get("has_disruption")]
        sla_at_risk = [s for s in shipments if s.get("sla_breached")]

        return {
            "alerts": alerts,
            "in_transit_count": len(in_transit),
            "delayed_count": len(delayed),
            "sla_at_risk_count": len(sla_at_risk),
            "total_shipments": len(shipments),
            "carrier_count": len(carriers),
            "top_delayed": delayed[:5],
            "top_sla_risks": sla_at_risk[:5],
        }

    def reason(self, observations: dict) -> dict:
        """Use ML models + LLM to analyze the situation."""
        self.status = AgentStatus.REASONING
        self._load_models()

        analysis = {
            "model_predictions": {},
            "risk_assessment": {},
        }

        # Run ML models on top-priority items
        for ship in observations.get("top_delayed", [])[:3]:
            ship_id = ship.get("shipment_id", "unknown")
            try:
                if self._eta_model:
                    eta = self._eta_model({
                        "days_for_shipment_scheduled": ship.get("sla_max_days", 5),
                        "distance_miles": ship.get("route_distance_km", 500) * 0.621,
                        "shipping_mode_encoded": 1,
                    })
                    analysis["model_predictions"][f"eta_{ship_id}"] = eta
            except Exception:
                pass

            try:
                if self._delay_model:
                    delay = self._delay_model({
                        "days_for_shipping_real": ship.get("actual_hours", 48) / 24,
                        "days_for_shipment_scheduled": ship.get("sla_max_days", 5),
                    })
                    analysis["model_predictions"][f"delay_{ship_id}"] = delay
            except Exception:
                pass

        # LLM strategic analysis
        system = """You are the Strategist agent in STRYDER AI.
You have access to ML model outputs and logistics data.
Provide strategic recommendations for the operations team.
Focus on actionable, prioritized recommendations."""

        user = f"""Current situation:
- {observations.get('in_transit_count', 0)} shipments in transit
- {observations.get('delayed_count', 0)} shipments delayed
- {observations.get('sla_at_risk_count', 0)} SLA breaches active
- {len(observations.get('alerts', []))} alerts pending

ML model predictions: {json.dumps(analysis.get('model_predictions', {}), default=str)}

Provide JSON with: risk_assessment, strategic_options (list), recommended_action, priority"""

        llm_analysis = self.call_llm_json(system, user)
        analysis.update(llm_analysis)

        return analysis

    def decide(self, analysis: dict) -> Decision:
        """Choose the best strategic option."""
        options = analysis.get("strategic_options", [])
        if not isinstance(options, list):
            options = []
        recommended = analysis.get("recommended_action", "Monitor and reassess")
        if not isinstance(recommended, str):
            recommended = str(recommended)
        risk = analysis.get("risk_assessment", {})
        if not isinstance(risk, dict):
            risk = {}

        action = {
            "recommended_action": recommended,
            "options_considered": len(options),
            "model_guided": bool(analysis.get("model_predictions")),
            "delegate_to": [],
        }

        # Determine delegation
        delayed = analysis.get("delayed_count", 0)
        if isinstance(delayed, (int, float)) and delayed > 5:
            action["delegate_to"].append("Executor")
        cascade_risk = risk.get("cascade_risk", "LOW") if isinstance(risk, dict) else "LOW"
        if cascade_risk in ("HIGH", "CRITICAL"):
            action["delegate_to"].append("Cascade")

        confidence = 0.85 if analysis.get("model_predictions") else 0.6
        sla_count = analysis.get("sla_at_risk_count", 0)
        priority = 1 if isinstance(sla_count, (int, float)) and sla_count > 0 else 3

        return Decision(
            agent_name=self.name,
            decision_type="STRATEGIC_RECOMMENDATION",
            context=analysis,
            reasoning=analysis.get("summary", recommended) if isinstance(analysis.get("summary"), str) else recommended,
            action=action,
            confidence=confidence,
            priority=priority,
        )

    def act(self, decision: Decision) -> dict:
        """Publish strategy to the orchestrator for execution."""
        return {
            "success": True,
            "action": "STRATEGY_PUBLISHED",
            "recommendation": decision.action.get("recommended_action"),
            "delegated_to": decision.action.get("delegate_to", []),
        }
