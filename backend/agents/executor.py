"""
STRYDER AI - Executor Agent (Action Engine)
=============================================
@Executor — The Operator

Role: Takes action on agent decisions.
Handles shipment rerouting, carrier reassignment,
warehouse load balancing, and SLA recovery operations.
"""

import json
from backend.agents.base_agent import BaseAgent, Decision, AgentStatus


class ExecutorAgent(BaseAgent):
    """
    The Executor takes action based on strategy and risk analysis.
    It modifies world state: reroutes shipments, swaps carriers,
    adjusts warehouse allocations, and triggers recovery procedures.
    """

    def __init__(self):
        super().__init__(
            name="Executor",
            role="Action Engine & Operations Controller",
            description="Executes logistics actions: shipment rerouting, "
                        "carrier reassignment, hub load balancing, SLA recovery. "
                        "Modifies live world state based on strategic decisions.",
            avatar_emoji="⚡",
            color="#10b981",
        )
        self.actions_executed = []
        self.auto_mode = True  # If False, requires human approval

    def observe(self, world_state: dict) -> dict:
        """Identify actionable items from pending decisions."""
        self.status = AgentStatus.OBSERVING

        pending_actions = world_state.get("pending_actions", [])
        shipments = world_state.get("shipments", [])
        carriers = world_state.get("carriers", [])

        # Find shipments needing intervention
        actionable = []
        for s in shipments:
            if s.get("has_disruption") and s.get("status") == "IN_TRANSIT":
                actionable.append({
                    "shipment_id": s.get("shipment_id"),
                    "action_type": "REROUTE_OR_REASSIGN",
                    "urgency": "HIGH" if s.get("sla_breached") else "MEDIUM",
                    "current_carrier": s.get("carrier_name"),
                    "disruption": s.get("disruption_type"),
                })

        # Find carriers to swap
        low_reliability = [c for c in carriers if c.get("reliability_score", 1) < 0.5]

        return {
            "pending_actions": pending_actions,
            "actionable_shipments": actionable,
            "available_carriers": [c for c in carriers if c.get("reliability_score", 1) > 0.7],
            "low_reliability_carriers": low_reliability,
        }

    def reason(self, observations: dict) -> dict:
        """Determine the best action plan."""
        self.status = AgentStatus.REASONING

        actionable = observations.get("actionable_shipments", [])
        available_carriers = observations.get("available_carriers", [])

        if not actionable:
            return {"action_plan": [], "summary": "No actions needed."}

        system = """You are the Executor agent in STRYDER AI.
You take direct action on logistics operations.
For each actionable item, decide the specific action to take.
Consider: carrier availability, route options, cost, urgency."""

        user = f"""Actionable items ({len(actionable)}):
{json.dumps(actionable[:5], default=str)}

Available carriers for reassignment: {len(available_carriers)}
Auto-mode: {self.auto_mode}

Provide JSON with: action_plan (list of specific actions),
requires_human_approval (bool), estimated_impact"""

        analysis = self.call_llm_json(system, user)
        analysis["actionable_count"] = len(actionable)
        return analysis

    def decide(self, analysis: dict) -> Decision:
        """Create execution decision."""
        plan = analysis.get("action_plan", [])
        needs_approval = analysis.get("requires_human_approval", False)

        action = {
            "action_plan": plan,
            "auto_execute": self.auto_mode and not needs_approval,
            "actions_count": len(plan),
            "human_approval_required": needs_approval,
        }

        return Decision(
            agent_name=self.name,
            decision_type="EXECUTION_PLAN",
            context=analysis,
            reasoning=analysis.get("summary", f"{len(plan)} actions planned."),
            action=action,
            confidence=0.75,
            priority=2,
        )

    def act(self, decision: Decision) -> dict:
        """Execute the action plan (modify world state)."""
        self.status = AgentStatus.ACTING
        plan = decision.action.get("action_plan", [])
        executed = []

        for action_item in plan:
            # In real system, this modifies world state
            # For now, log the action
            result = {
                "action": action_item,
                "status": "EXECUTED" if decision.action.get("auto_execute") else "PENDING_APPROVAL",
                "timestamp": self.last_activity,
            }
            executed.append(result)
            self.actions_executed.append(result)

        return {
            "success": True,
            "action": "PLAN_EXECUTED",
            "executed_count": len(executed),
            "pending_approval": not decision.action.get("auto_execute"),
            "results": executed,
        }
