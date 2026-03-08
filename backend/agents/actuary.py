"""
STRYDER AI - Actuary Agent (Risk Evaluator)
=============================================
@Actuary — The Risk Calculator

Role: Quantifies risk across all logistics dimensions.
Evaluates financial exposure, SLA penalty forecasts,
carrier risk scores, and insurance-grade probability assessments.
"""

import json
from backend.agents.base_agent import BaseAgent, Decision, AgentStatus


class ActuaryAgent(BaseAgent):
    """
    The Actuary evaluates and quantifies risk across the supply chain.
    Specializes in financial impact analysis and probability assessment.
    """

    def __init__(self):
        super().__init__(
            name="Actuary",
            role="Risk Evaluator & Financial Analyst",
            description="Quantifies financial exposure from SLA penalties, "
                        "carrier risk, shipment value at risk, insurance costs. "
                        "Provides probability-weighted impact analysis.",
            avatar_emoji="📊",
            color="#f59e0b",
        )

    def observe(self, world_state: dict) -> dict:
        """Gather risk-relevant data from world state."""
        self.status = AgentStatus.OBSERVING

        shipments = world_state.get("shipments", [])
        carriers = world_state.get("carriers", [])

        # Calculate financial exposure
        total_value_at_risk = 0
        total_sla_penalties = 0
        risk_buckets = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}

        for s in shipments:
            if s.get("sla_breached"):
                penalty = s.get("sla_penalty_per_day", 500) * max(s.get("delay_days", 0), 1)
                total_sla_penalties += penalty
                total_value_at_risk += s.get("shipment_value", 0)
                risk_buckets["CRITICAL"] += 1
            elif s.get("has_disruption"):
                total_value_at_risk += s.get("shipment_value", 0) * 0.3  # partial risk
                risk_buckets["HIGH"] += 1
            elif s.get("status") == "IN_TRANSIT":
                risk_buckets["MEDIUM"] += 1
            else:
                risk_buckets["LOW"] += 1

        # Carrier risk profile
        at_risk_carriers = [c for c in carriers if c.get("reliability_score", 1) < 0.7]

        return {
            "total_value_at_risk": round(total_value_at_risk, 2),
            "total_sla_penalties": round(total_sla_penalties, 2),
            "risk_buckets": risk_buckets,
            "at_risk_carriers": len(at_risk_carriers),
            "total_shipments": len(shipments),
            "breached_shipments": risk_buckets["CRITICAL"],
            "disrupted_shipments": risk_buckets["HIGH"],
        }

    def reason(self, observations: dict) -> dict:
        """Quantitative risk analysis using LLM."""
        self.status = AgentStatus.REASONING

        system = """You are the Actuary agent in STRYDER AI.
You specialize in quantitative risk assessment for logistics.
Provide precise financial impact analysis with probability estimates.
Think like an insurance actuary: calculate expected losses."""

        user = f"""Risk metrics:
- Value at risk: INR {observations['total_value_at_risk']:,.0f}
- SLA penalties accrued: INR {observations['total_sla_penalties']:,.0f}
- Risk buckets: {observations['risk_buckets']}
- At-risk carriers: {observations['at_risk_carriers']}
- Breached SLAs: {observations['breached_shipments']}
- Active disruptions: {observations['disrupted_shipments']}

Provide JSON with: overall_risk_score (0-100), financial_forecast,
risk_mitigation_options (list with cost-benefit), recommended_action"""

        analysis = self.call_llm_json(system, user)
        analysis["raw_metrics"] = observations
        return analysis

    def decide(self, analysis: dict) -> Decision:
        """Decide on risk mitigation strategy."""
        risk_score = analysis.get("overall_risk_score", 50)
        metrics = analysis.get("raw_metrics", {})

        action = {
            "risk_score": risk_score,
            "mitigation_strategy": analysis.get("recommended_action", "Monitor"),
            "cost_benefit": analysis.get("risk_mitigation_options", []),
            "escalate_to_human": risk_score > 80,
            "financial_summary": {
                "value_at_risk": metrics.get("total_value_at_risk", 0),
                "penalties": metrics.get("total_sla_penalties", 0),
            },
        }

        confidence = 0.8 if risk_score < 50 else 0.65
        priority = 1 if risk_score > 80 else 2 if risk_score > 50 else 4

        return Decision(
            agent_name=self.name,
            decision_type="RISK_ASSESSMENT",
            context=analysis,
            reasoning=f"Overall risk score: {risk_score}/100. "
                      f"INR {metrics.get('total_sla_penalties', 0):,.0f} in penalties.",
            action=action,
            confidence=confidence,
            priority=priority,
        )

    def act(self, decision: Decision) -> dict:
        """Publish risk report and mitigation recommendations."""
        return {
            "success": True,
            "action": "RISK_REPORT_PUBLISHED",
            "risk_score": decision.action.get("risk_score"),
            "escalated_to_human": decision.action.get("escalate_to_human", False),
            "mitigation_strategy": decision.action.get("mitigation_strategy"),
        }
