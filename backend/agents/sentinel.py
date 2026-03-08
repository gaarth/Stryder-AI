"""
STRYDER AI - Sentinel Agent (Observer)
=======================================
@Sentinel — The Watchguard

Role: Continuously monitors the logistics world state.
Detects anomalies, SLA risks, disruptions, and unusual patterns.
Triggers alerts for other agents to act on.
"""

from backend.agents.base_agent import BaseAgent, Decision, AgentStatus


class SentinelAgent(BaseAgent):
    """
    The Sentinel observes the world state and detects anomalies.
    It is the first agent in the Observe->Reason->Decide->Act->Learn loop.
    """

    # Alert thresholds
    DELAY_THRESHOLD_HOURS = 4.0
    SLA_RISK_THRESHOLD = 0.7
    CONGESTION_THRESHOLD = 0.8
    CARRIER_RELIABILITY_FLOOR = 0.6

    def __init__(self):
        super().__init__(
            name="Sentinel",
            role="Observer & Anomaly Detector",
            description="Monitors all logistics operations in real-time. "
                        "Detects SLA risks, shipment delays, carrier degradation, "
                        "warehouse congestion, and emerging disruption patterns.",
            avatar_emoji="🛡️",
            color="#ef4444",
        )

    def observe(self, world_state: dict) -> dict:
        """Scan world state for anomalies and risks."""
        self.status = AgentStatus.OBSERVING
        alerts = []
        metrics = {
            "shipments_scanned": 0,
            "carriers_scanned": 0,
            "warehouses_scanned": 0,
            "alerts_raised": 0,
        }

        # --- Scan Shipments ---
        shipments = world_state.get("shipments", [])
        metrics["shipments_scanned"] = len(shipments)

        for s in shipments:
            # Delayed shipments
            if s.get("status") == "IN_TRANSIT":
                delay_hours = s.get("disruption_delay_hours", 0)
                if delay_hours > self.DELAY_THRESHOLD_HOURS:
                    alerts.append({
                        "type": "SHIPMENT_DELAYED",
                        "severity": "HIGH" if delay_hours > 12 else "MEDIUM",
                        "entity_id": s.get("shipment_id"),
                        "detail": f"Shipment {s['shipment_id']} delayed by {delay_hours:.1f}h",
                        "data": {"delay_hours": delay_hours, "carrier": s.get("carrier_name")},
                    })

            # SLA breach risk
            if s.get("sla_breached"):
                alerts.append({
                    "type": "SLA_BREACH",
                    "severity": "CRITICAL",
                    "entity_id": s.get("shipment_id"),
                    "detail": f"SLA breached: {s['shipment_id']} ({s.get('sla_tier')} tier, +{s.get('delay_days', 0):.1f}d)",
                    "data": {"tier": s.get("sla_tier"), "delay_days": s.get("delay_days")},
                })

            # Active disruption
            if s.get("has_disruption") and s.get("status") == "IN_TRANSIT":
                alerts.append({
                    "type": "DISRUPTION_ACTIVE",
                    "severity": "HIGH",
                    "entity_id": s.get("shipment_id"),
                    "detail": f"Active disruption: {s.get('disruption_type')} on {s['shipment_id']}",
                    "data": {"disruption_type": s.get("disruption_type")},
                })

        # --- Scan Carriers ---
        carriers = world_state.get("carriers", [])
        metrics["carriers_scanned"] = len(carriers)

        for c in carriers:
            if c.get("reliability_score", 1.0) < self.CARRIER_RELIABILITY_FLOOR:
                alerts.append({
                    "type": "CARRIER_DEGRADED",
                    "severity": "MEDIUM",
                    "entity_id": c.get("carrier_id"),
                    "detail": f"Carrier {c['name']} reliability dropped to {c['reliability_score']:.2f}",
                    "data": {"reliability": c.get("reliability_score")},
                })

        # --- Scan Warehouses ---
        warehouses = world_state.get("warehouses", [])
        metrics["warehouses_scanned"] = len(warehouses)

        for w in warehouses:
            util = w.get("utilization_pct", 0) / 100
            if util > self.CONGESTION_THRESHOLD:
                alerts.append({
                    "type": "WAREHOUSE_CONGESTED",
                    "severity": "HIGH" if util > 0.9 else "MEDIUM",
                    "entity_id": w.get("warehouse_id"),
                    "detail": f"Hub {w['name']} at {util*100:.0f}% capacity",
                    "data": {"utilization": util, "queue": w.get("queue_length")},
                })

        # Sort by severity
        severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        alerts.sort(key=lambda a: severity_order.get(a["severity"], 4))
        metrics["alerts_raised"] = len(alerts)

        return {"alerts": alerts, "metrics": metrics}

    def reason(self, observations: dict) -> dict:
        """Analyze detected alerts using LLM for pattern recognition."""
        alerts = observations.get("alerts", [])

        if not alerts:
            return {"risk_level": "LOW", "summary": "No anomalies detected.", "recommendations": []}

        # Build LLM prompt for reasoning
        alert_summary = "\n".join([
            f"- [{a['severity']}] {a['type']}: {a['detail']}"
            for a in alerts[:10]  # Cap at 10 for token efficiency
        ])

        system = f"""You are the Sentinel agent in STRYDER AI, a logistics intelligence platform.
You have detected {len(alerts)} alerts across the supply chain.
Analyze these alerts and identify:
1. The overall risk level (LOW/MEDIUM/HIGH/CRITICAL)
2. Pattern connections between alerts
3. Root cause hypotheses
4. Priority ranking of which alerts need immediate action"""

        user = f"""Detected alerts:
{alert_summary}

Metrics: {observations.get('metrics', {})}

Provide your analysis as JSON with keys: risk_level, summary, patterns, root_causes, recommendations"""

        analysis = self.call_llm_json(system, user)

        # Ensure required fields
        if "risk_level" not in analysis:
            critical_count = sum(1 for a in alerts if a["severity"] == "CRITICAL")
            high_count = sum(1 for a in alerts if a["severity"] == "HIGH")
            analysis["risk_level"] = (
                "CRITICAL" if critical_count > 0
                else "HIGH" if high_count > 2
                else "MEDIUM" if alerts
                else "LOW"
            )

        analysis["alert_count"] = len(alerts)
        analysis["top_alerts"] = alerts[:5]
        return analysis

    def decide(self, analysis: dict) -> Decision:
        """Decide which alerts to escalate to the orchestrator."""
        risk = analysis.get("risk_level", "LOW")
        alerts = analysis.get("top_alerts", [])

        action = {
            "escalate": risk in ("HIGH", "CRITICAL"),
            "alert_ids": [a.get("entity_id") for a in alerts],
            "recommended_agents": [],
        }

        # Determine which agents to notify
        for alert in alerts:
            atype = alert.get("type", "")
            if "DELAY" in atype or "SLA" in atype:
                action["recommended_agents"].append("Strategist")
            if "CARRIER" in atype:
                action["recommended_agents"].append("Actuary")
            if "CONGESTION" in atype:
                action["recommended_agents"].append("Strategist")
            if "DISRUPTION" in atype:
                action["recommended_agents"].extend(["Cascade", "Executor"])

        action["recommended_agents"] = list(set(action["recommended_agents"]))

        confidence = 0.9 if risk in ("CRITICAL", "HIGH") else 0.7
        priority = 1 if risk == "CRITICAL" else 2 if risk == "HIGH" else 3

        return Decision(
            agent_name=self.name,
            decision_type="ALERT_ESCALATION",
            context=analysis,
            reasoning=analysis.get("summary", "Alerts detected requiring attention."),
            action=action,
            confidence=confidence,
            priority=priority,
        )

    def act(self, decision: Decision) -> dict:
        """Execute: Publish alerts to the orchestrator pipeline."""
        return {
            "success": True,
            "action": "ALERTS_PUBLISHED",
            "escalated": decision.action.get("escalate", False),
            "agents_notified": decision.action.get("recommended_agents", []),
            "alert_count": len(decision.action.get("alert_ids", [])),
        }
