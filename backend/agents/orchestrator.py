"""
STRYDER AI — Central Agent Orchestrator v3
=============================================
Pipeline: User Query → Intent Classifier → Agent Router → Domain Agent → Executor
All outputs structured. No hallucination. Real state only.
"""
import re
import time
import uuid
from datetime import datetime
from typing import Optional

from backend.agents.base_agent import Decision
from backend.agents.sentinel import SentinelAgent
from backend.agents.strategist import StrategistAgent
from backend.agents.actuary import ActuaryAgent
from backend.agents.executor import ExecutorAgent
from backend.agents.cascade import CascadeAgent

# ────────────────────────────────────────────
# INTENT TYPES
# ────────────────────────────────────────────
INTENTS = [
    "STATUS_QUERY",
    "OPTIMIZATION_REQUEST",
    "FIX_REQUEST",
    "ANALYSIS_REQUEST",
    "SCENARIO_REQUEST",
    "SYSTEM_QUERY",
]


class AgentOrchestrator:
    """
    Central coordination engine.
    All user input passes through: Intent Classifier → Agent Router → Domain Handler.
    """

    def __init__(self):
        self.sentinel = SentinelAgent()
        self.strategist = StrategistAgent()
        self.actuary = ActuaryAgent()
        self.executor = ExecutorAgent()
        self.cascade = CascadeAgent()

        self.agents = {
            "Sentinel": self.sentinel,
            "Strategist": self.strategist,
            "Actuary": self.actuary,
            "Executor": self.executor,
            "Cascade": self.cascade,
        }

        self.auto_mode = True
        self.decision_log: list[dict] = []
        self.loop_history: list[dict] = []
        self.max_log_size = 200

        # ── CONTEXT TRACKING ──
        self._active_shipment_id: Optional[int] = None
        self._active_agent: Optional[str] = None
        self._last_optimize_id: Optional[int] = None
        self._last_recommendation: Optional[dict] = None

    # ========================================
    # AGENT MANAGEMENT
    # ========================================
    def get_agent(self, name: str):
        return self.agents.get(name) or self.agents.get(name.capitalize())

    def get_all_statuses(self) -> list:
        return [agent.get_status() for agent in self.agents.values()]

    def set_auto_mode(self, enabled: bool):
        self.auto_mode = enabled
        self.executor.auto_mode = enabled

    # ========================================
    # INTENT CLASSIFICATION (deterministic)
    # ========================================
    def _classify_intent(self, message: str) -> str:
        msg = message.lower().strip()

        # FIX_REQUEST — highest priority
        if re.search(r'apply\s+option\s+\d+', msg):
            return "FIX_REQUEST"
        if any(w in msg for w in ["apply", "fix", "reroute", "switch carrier", "execute"]):
            return "FIX_REQUEST"

        # SCENARIO_REQUEST
        if any(w in msg for w in ["trigger", "inject", "scenario", "congestion scenario", "strike scenario"]):
            return "SCENARIO_REQUEST"

        # OPTIMIZATION_REQUEST
        if any(w in msg for w in ["optimize", "reduce eta", "reduce cost", "improve", "speed up", "expedite", "cheapest", "fastest"]):
            return "OPTIMIZATION_REQUEST"

        # ANALYSIS_REQUEST — includes monitoring, cost analysis, learning
        if any(w in msg for w in ["scan", "monitor", "anomal", "risk", "predict", "cascade",
                                   "analyze", "impact", "estimate", "what risks", "what learned",
                                   "what have", "learning", "memory", "overview", "fleet"]):
            return "ANALYSIS_REQUEST"

        # SYSTEM_QUERY
        if any(w in msg for w in ["strategy", "priority", "agents", "help", "mode", "system"]):
            return "SYSTEM_QUERY"

        # STATUS_QUERY (only when a specific shipment is referenced)
        if re.search(r'(?:shipment|ship|#)\s*\d+', msg):
            return "STATUS_QUERY"
        if any(w in msg for w in ["eta", "cost", "where", "track", "carrier"]):
            return "STATUS_QUERY"

        return "STATUS_QUERY"

    # ========================================
    # PARSE @TAG AND SHIPMENT ID
    # ========================================
    def _parse_message(self, message: str) -> dict:
        """Extract @agent tag, :subtag, shipment IDs, and clean message."""
        target_agent = None
        subtag = None
        clean = message

        for name in self.agents:
            tag = f"@{name}"
            if tag.lower() in message.lower():
                target_agent = name
                idx = message.lower().index(tag.lower())
                after = message[idx + len(tag):]
                if after.startswith(":"):
                    parts = after[1:].split(" ", 1)
                    subtag = parts[0].upper()
                    clean = message[:idx] + (parts[1] if len(parts) > 1 else "")
                else:
                    clean = message[:idx] + after
                break

        # Extract shipment IDs (only explicit references)
        ship_ids = [int(x) for x in re.findall(r'(?:shipment|ship|#)\s*(\d+)', clean, re.IGNORECASE)]

        return {
            "target_agent": target_agent,
            "subtag": subtag,
            "clean_message": clean.strip(),
            "ship_ids": ship_ids,
        }

    # ========================================
    # MAIN ROUTE (Pipeline entry point)
    # ========================================
    def route_message(self, message: str, context: Optional[dict] = None) -> dict:
        from backend.simulation.ops_state import get_ops_state
        ops = get_ops_state()

        parsed = self._parse_message(message)
        intent = self._classify_intent(message)
        target = parsed["target_agent"]
        subtag = parsed["subtag"]
        clean_msg = parsed["clean_message"]
        ship_ids = parsed["ship_ids"]

        # Context tracking: remember active shipment
        if ship_ids:
            self._active_shipment_id = ship_ids[0]
        elif self._active_shipment_id and intent in ("OPTIMIZATION_REQUEST", "FIX_REQUEST"):
            # Only inject context for targeted actions, NOT for system-wide queries
            ship_ids = [self._active_shipment_id]

        # ── DOMAIN ROUTING BY SUBTAG ──
        SUBTAG_DOMAIN = {
            "ETA_AGENT": "Strategist", "DELAY_AGENT": "Strategist",
            "CARRIER_AGENT": "Strategist", "HUB_AGENT": "Strategist",
            "COST_AGENT": "Actuary", "CASCADE_MODEL": "Cascade",
        }
        if subtag and subtag in SUBTAG_DOMAIN:
            target = SUBTAG_DOMAIN[subtag]

        # ── INTENT-BASED DISPATCH ──

        # ──────── FIX_REQUEST ────────
        if intent == "FIX_REQUEST":
            apply_match = re.search(r'apply\s+option\s+(\d+)', message, re.IGNORECASE)
            if apply_match:
                opt_idx = int(apply_match.group(1))
                sid = self._last_optimize_id or (ship_ids[0] if ship_ids else None)
                if not sid:
                    return self._out("Executor", subtag, "No pending optimization. Use @Strategist:ETA_AGENT optimize shipment <id> first.")
                result = ops.apply_option(sid, opt_idx)
                if "error" in result:
                    return self._out("Executor", subtag, result["error"])
                ops.add_learning("Executor", f"Applied option {opt_idx} to shipment #{sid}: {result['applied']}")
                return self._out("Executor", subtag,
                    f"Executor\n\n"
                    f"• Applied: {result['applied']}\n"
                    f"• Shipment #{sid}\n"
                    f"• ETA: {result['old_eta']}h → {result['new_eta']}h\n"
                    f"• Cost: ₹{result['old_cost']:,} → ₹{result['new_cost']:,}")

            # Generic fix (reroute, switch carrier)
            if ship_ids:
                sid = ship_ids[0]
                ship = next((s for s in ops.shipments if s["id"] == sid), None)
                if not ship:
                    return self._out("Executor", subtag, "Data not available in current simulation state.")
                if "carrier" in clean_msg.lower() or "switch" in clean_msg.lower():
                    result = ops.execute_command("SWITCH_CARRIER", {"shipment_id": sid, "carrier": "BlueDart"})
                    if result.get("ok"):
                        ops.add_learning("Executor", f"Switched carrier for #{sid}: {result['old_carrier']} → {result['new_carrier']}")
                        return self._out("Executor", subtag,
                            f"Executor\n\n"
                            f"• Applied carrier switch for shipment #{sid}\n"
                            f"• Old carrier: {result['old_carrier']}\n"
                            f"• New carrier: {result['new_carrier']}")
            return self._out("Executor", subtag, "Specify a shipment and action. Example: Apply option 1, or switch carrier for shipment #13")

        # ──────── STATUS_QUERY ────────
        if intent == "STATUS_QUERY":
            if ship_ids:
                sid = ship_ids[0]
                ship = next((s for s in ops.shipments if s["id"] == sid), None)
                if not ship:
                    return self._out(target or "System", subtag, "Data not available in current simulation state.")

                # Domain-locked status
                agent_name = target or "System"
                if subtag == "CARRIER_AGENT" or (target == "Strategist" and "carrier" in clean_msg.lower()):
                    agent_name = "Carrier Agent"
                    from backend.simulation.ops_state import CARRIER_MAP
                    c_info = CARRIER_MAP.get(ship["carrier"], {})
                    return self._out(agent_name, subtag,
                        f"Carrier Agent\n\nShipment #{sid} Carrier Status\n\n"
                        f"• Current carrier: {ship['carrier']}\n"
                        f"• Speed factor: {c_info.get('speed_factor', 'N/A')}\n"
                        f"• Base rate: ₹{c_info.get('base_rate', 'N/A')}\n"
                        f"• Status: {ship['status']}\n"
                        f"• ETA: {ship['eta_hours']}h")

                if subtag == "DELAY_AGENT" or "delay" in clean_msg.lower():
                    agent_name = "Delay Agent"
                    is_delayed = ship["status"] == "DELAYED"
                    penalty = round(ship["current_cost"] - ship["base_cost"])
                    return self._out(agent_name, subtag,
                        f"Delay Agent\n\nShipment #{sid} Delay Analysis\n\n"
                        f"• Status: {ship['status']}\n"
                        f"• Currently delayed: {'Yes' if is_delayed else 'No'}\n"
                        f"• ETA: {ship['eta_hours']}h\n"
                        f"• Penalty accrued: ₹{penalty:,}\n"
                        f"• Delay penalty rate: ₹{ship['delay_penalty_per_hour']:,.0f}/hour")

                if subtag == "HUB_AGENT" or "hub" in clean_msg.lower() or "warehouse" in clean_msg.lower():
                    agent_name = "Hub Agent"
                    dest = ship["destination"]
                    nearby_wh = [w for w in ops.wh_states if w["name"].replace(" Warehouse", "") == dest]
                    wh_info = nearby_wh[0] if nearby_wh else None
                    lines = [
                        f"Hub Agent\n\nShipment #{sid} Hub Analysis\n",
                        f"• Route: {ship['origin']} → {ship['destination']}",
                        f"• Status: {ship['status']}",
                    ]
                    if wh_info:
                        lines.extend([
                            f"• Destination hub: {wh_info['name']}",
                            f"• Hub utilization: {wh_info['utilization_pct']}%",
                            f"• Hub capacity: {wh_info['capacity']}",
                        ])
                    return self._out(agent_name, subtag, "\n".join(lines))

                # Default status (ETA Agent or general)
                return self._out(target or "ETA Agent", subtag,
                    f"Shipment #{sid}\n\n"
                    f"• Route: {ship['origin']} → {ship['destination']}\n"
                    f"• ETA: {ship['eta_hours']}h\n"
                    f"• Carrier: {ship['carrier']}\n"
                    f"• Cost: ₹{round(ship['current_cost']):,}\n"
                    f"• Status: {ship['status']}\n"
                    f"• Cargo: {ship['cargo']}\n"
                    f"• Risk: {ship['risk']}")

            # Sentinel system scan
            if target == "Sentinel" or "scan" in clean_msg.lower() or "monitor" in clean_msg.lower() or "anomal" in clean_msg.lower():
                alerts = ops.sentinel_scan()
                stats = ops.get_snapshot()["stats"]
                lines = [
                    "Sentinel\n\nSystem Scan Results\n",
                    f"• {stats['total']} total shipments",
                    f"• {stats['in_transit']} in transit",
                    f"• {stats['delayed']} delayed",
                    f"• {stats['delivered']} delivered",
                    f"• {stats['active_disruptions']} active disruptions",
                ]
                if alerts:
                    lines.append("\nAnomalies:")
                    for a in alerts[:5]:
                        lines.append(f"• {a}")
                else:
                    lines.append("\n• All systems nominal")
                return self._out("Sentinel", subtag, "\n".join(lines))

            # General status
            stats = ops.get_snapshot()["stats"]
            return self._out("System", subtag,
                f"System Status\n\n"
                f"• Total: {stats['total']} shipments\n"
                f"• In transit: {stats['in_transit']}\n"
                f"• Delayed: {stats['delayed']}\n"
                f"• Delivered: {stats['delivered']}\n"
                f"• Active disruptions: {stats['active_disruptions']}\n"
                f"• Strategy: {ops.agent_memory['global_strategy'].upper()}")

        # ──────── OPTIMIZATION_REQUEST ────────
        if intent == "OPTIMIZATION_REQUEST":
            if not ship_ids:
                return self._out("Strategist", subtag, "Specify a shipment to optimize. Example: @Strategist:ETA_AGENT optimize shipment 13")

            sid = ship_ids[0]
            self._active_shipment_id = sid
            ship = next((s for s in ops.shipments if s["id"] == sid), None)
            if not ship:
                return self._out("Strategist", subtag, "Data not available in current simulation state.")
            if ship["status"] == "DELIVERED":
                return self._out("Strategist", subtag, f"Shipment #{sid} already delivered.")

            # Domain-specific optimization
            if subtag == "CARRIER_AGENT" or "carrier" in clean_msg.lower():
                from backend.simulation.ops_state import CARRIERS, CARRIER_MAP
                current = CARRIER_MAP.get(ship["carrier"], {})
                lines = [f"Carrier Agent\n\nShipment #{sid} Carrier Optimization\n"]
                lines.append(f"• Current carrier: {ship['carrier']}")
                lines.append(f"• Speed factor: {current.get('speed_factor', 'N/A')}")
                for c in CARRIERS:
                    if c["name"] != ship["carrier"]:
                        eta_diff = round((current.get("speed_factor", 1.0) - c["speed_factor"]) * ship["eta_hours"] / current.get("speed_factor", 1.0))
                        cost_diff = round((c["base_rate"] - current.get("base_rate", 300)) * ship["eta_hours"] / 10)
                        lines.append(f"\nAlternative: {c['name']}")
                        lines.append(f"  ETA change: {'+' if eta_diff > 0 else ''}{-eta_diff}h")
                        lines.append(f"  Cost change: {'₹+' if cost_diff > 0 else '-₹'}{abs(cost_diff):,}")
                        if len(lines) > 15:
                            break
                return self._out("Carrier Agent", subtag, "\n".join(lines))

            # Default ETA optimization
            result = ops.optimize_eta(sid)
            if "error" in result:
                return self._out("Strategist", subtag, result["error"])
            self._last_optimize_id = sid
            ops.add_learning("Strategist", f"Generated ETA optimization options for shipment #{sid}")

            lines = [
                f"ETA Optimization for Shipment #{sid}\n",
                f"Route: {result['origin']} → {result['destination']}",
                f"Current: ETA {result['current_eta']}h | Cost ₹{result['current_cost']:,} | Carrier {result['current_carrier']}",
                "",
            ]
            for opt in result["options"]:
                lines.append(f"Option {opt['index']}: {opt['description']}")
                lines.append(f"  ETA: {opt['eta']}h (saves {opt['eta_saved']}h)")
                lines.append(f"  Cost: +₹{opt['cost_increase']:,} (total ₹{opt['new_cost']:,})")
                if opt.get("carrier") != result["current_carrier"]:
                    lines.append(f"  Carrier: {opt['carrier']}")
                lines.append("")
            lines.append("Say 'Apply option 1/2/3' to execute.")
            return self._out("Strategist", "ETA_AGENT", "\n".join(lines))

        # ──────── ANALYSIS_REQUEST ────────
        if intent == "ANALYSIS_REQUEST":
            # Sentinel scan / monitoring
            if target == "Sentinel" or "scan" in clean_msg.lower() or "monitor" in clean_msg.lower() or "anomal" in clean_msg.lower():
                alerts = ops.sentinel_scan()
                stats = ops.get_snapshot()["stats"]
                lines = [
                    "Sentinel\n\nSystem Scan Results\n",
                    f"• {stats['total']} total shipments",
                    f"• {stats['in_transit']} in transit",
                    f"• {stats['delayed']} delayed",
                    f"• {stats['delivered']} delivered",
                    f"• {stats['active_disruptions']} active disruptions",
                ]
                if alerts:
                    lines.append("\nAnomalies:")
                    for a in alerts[:5]:
                        lines.append(f"• {a}")
                else:
                    lines.append("\n• All systems nominal")
                return self._out("Sentinel", subtag, "\n".join(lines))

            # Cascade risk
            if target == "Cascade" or "risk" in clean_msg.lower() or "predict" in clean_msg.lower() or "cascade" in clean_msg.lower():
                alerts = ops.cascade_predict()
                if alerts:
                    lines = [f"Cascade\n\nRisk Analysis — {len(alerts)} predictions\n"]
                    for a in alerts[:5]:
                        lines.append(f"• {a['location']}: {a['type'].replace('_', ' ')} (confidence {a['confidence']}%)")
                        lines.append(f"  {a['impact_count']} shipments at risk — {a['suggestion']}")
                    return self._out("Cascade", subtag, "\n".join(lines))
                return self._out("Cascade", subtag, "Cascade\n\n• No cascade risks predicted\n• System is stable")

            # Actuary cost/impact
            if target == "Actuary" or "cost" in clean_msg.lower() or "impact" in clean_msg.lower():
                if ship_ids:
                    sid = ship_ids[0]
                    ship = next((s for s in ops.shipments if s["id"] == sid), None)
                    if ship:
                        penalty = round(ship["current_cost"] - ship["base_cost"])
                        return self._out("Actuary", subtag,
                            f"Actuary\n\nCost Analysis — Shipment #{sid}\n\n"
                            f"• Base cost: ₹{ship['base_cost']:,.0f}\n"
                            f"• Current cost: ₹{round(ship['current_cost']):,}\n"
                            f"• Delay penalty: ₹{ship['delay_penalty_per_hour']:,.0f}/hour\n"
                            f"• Penalty accrued: ₹{penalty:,}\n"
                            f"• Status: {ship['status']}")

                total_base = sum(s["base_cost"] for s in ops.shipments)
                total_current = sum(s["current_cost"] for s in ops.shipments)
                penalty = round(total_current - total_base)
                delayed = sum(1 for s in ops.shipments if s["status"] == "DELAYED")
                return self._out("Actuary", subtag,
                    f"Actuary\n\nFleet Cost Overview\n\n"
                    f"• Total base cost: ₹{total_base:,.0f}\n"
                    f"• Total current cost: ₹{round(total_current):,}\n"
                    f"• Penalties accrued: ₹{penalty:,}\n"
                    f"• {delayed} shipments delayed")

            # What have you learned
            if "learn" in clean_msg.lower() or "memory" in clean_msg.lower() or "what have" in clean_msg.lower():
                learn = ops.agent_memory["agent_learnings"]
                recent_logs = ops.learning_logs[-5:] if ops.learning_logs else []
                lines = [
                    "System\n\nSystem Learning Summary\n",
                    f"• Total hours saved: {learn['total_hours_saved']}h",
                    f"• Total cost saved: ₹{learn['total_cost_saved']:,}",
                    f"• Sentinel detections: {learn['sentinel_detections']}",
                    f"• Strategist optimizations: {learn['strategist_optimizations']}",
                    f"• Executor executions: {learn['executor_executions']}",
                ]
                if recent_logs:
                    lines.append("\nRecent learnings:")
                    for log in recent_logs:
                        lines.append(f"• [{log['ts']}] {log['agent']}: {log['message']}")
                if ops.agent_memory["global_strategy"] != "balanced":
                    lines.append(f"\n• User preference: {ops.agent_memory['global_strategy'].upper()}")
                return self._out("System", subtag, "\n".join(lines))

            return self._out("System", subtag, "Specify what to analyze. Examples:\n• @Cascade analyze system risk\n• @Actuary estimate cost impact\n• What have you learned?")

        # ──────── SCENARIO_REQUEST ────────
        if intent == "SCENARIO_REQUEST":
            return self._out("System", subtag,
                "System\n\nUse the Scenario panel to inject events.\n"
                "Available: PORT_CONGESTION, CARRIER_STRIKE, WEATHER_DISRUPTION,\n"
                "WAREHOUSE_OVERFLOW, CUSTOMS_DELAY, ROUTE_BLOCKAGE")

        # ──────── SYSTEM_QUERY ────────
        if intent == "SYSTEM_QUERY":
            msg = clean_msg.lower()
            if "strategy" in msg:
                if "cost" in msg:
                    ops.execute_command("SET_STRATEGY", {"strategy": "cost"})
                    ops.add_learning("System", "User set global strategy to COST_OPTIMIZED")
                    return self._out("System", subtag, "System\n\n✓ Strategy set to: COST_OPTIMIZED\n• Agents will prioritize lowest cost")
                elif "speed" in msg or "time" in msg or "fast" in msg:
                    ops.execute_command("SET_STRATEGY", {"strategy": "speed"})
                    ops.add_learning("System", "User set global strategy to TIME_OPTIMIZED")
                    return self._out("System", subtag, "System\n\n✓ Strategy set to: TIME_OPTIMIZED\n• Agents will prioritize fastest delivery")
                elif "balanced" in msg:
                    ops.execute_command("SET_STRATEGY", {"strategy": "balanced"})
                    return self._out("System", subtag, "System\n\n✓ Strategy set to: BALANCED\n• Agents balance cost and speed")
                return self._out("System", subtag,
                    f"System\n\nCurrent strategy: {ops.agent_memory['global_strategy'].upper()}\n\n"
                    "Set strategy:\n• /strategy cost\n• /strategy speed\n• /strategy balanced")

            if "help" in msg:
                return self._out("System", subtag,
                    "System\n\nCommands:\n"
                    "• /help — this message\n"
                    "• /status — system overview\n"
                    "• /shipment <id> — view shipment\n"
                    "• /strategy <cost|speed|balanced>\n"
                    "• /reset — reset simulation\n\n"
                    "Agent commands:\n"
                    "• @Sentinel scan\n"
                    "• @Strategist:ETA_AGENT optimize shipment 13\n"
                    "• @Strategist:CARRIER_AGENT shipment 13\n"
                    "• @Actuary estimate cost impact\n"
                    "• @Cascade analyze risk\n"
                    "• Apply option 1/2/3")

            if "agent" in msg:
                return self._out("System", subtag,
                    "System\n\nActive Agents:\n\n"
                    "• Sentinel — anomaly detection, system monitoring\n"
                    "• Strategist — ETA optimization, carrier evaluation, routing\n"
                    "  Subtags: :ETA_AGENT :CARRIER_AGENT :DELAY_AGENT :HUB_AGENT\n"
                    "• Actuary — cost/risk analysis\n"
                    "  Subtag: :COST_AGENT\n"
                    "• Executor — applies fixes to simulation state\n"
                    "• Cascade — predicts secondary failures")

            stats = ops.get_snapshot()["stats"]
            return self._out("System", subtag,
                f"System\n\nSystem Status\n\n"
                f"• Shipments: {stats['total']}\n"
                f"• In transit: {stats['in_transit']}\n"
                f"• Delayed: {stats['delayed']}\n"
                f"• Strategy: {ops.agent_memory['global_strategy'].upper()}")

        # Fallback
        return self._out("System", subtag, "Data not available in current simulation state.")

    # ========================================
    # OUTPUT FORMATTER
    # ========================================
    def _out(self, agent: str, subtag: Optional[str], response) -> dict:
        if isinstance(response, dict):
            text = response.get("response", str(response))
        else:
            text = str(response)
        return {
            "agent": agent,
            "subtag": subtag,
            "response": text,
            "timestamp": datetime.now().isoformat(),
        }

    # ========================================
    # FULL LOOP EXECUTION (for disruptions)
    # ========================================
    def run_full_loop(self, world_state: dict) -> dict:
        loop_id = str(uuid.uuid4())[:8]
        start = time.time()
        trace = {
            "loop_id": loop_id,
            "started": datetime.now().isoformat(),
            "auto_mode": self.auto_mode,
            "phases": {},
            "decisions": [],
        }
        sentinel_trace = self.sentinel.run_loop(world_state)
        trace["phases"]["sentinel"] = sentinel_trace
        alerts = sentinel_trace.get("phases", {}).get("observe", {}).get("alerts", [])
        trace["decisions"].append(sentinel_trace.get("phases", {}).get("decide", {}))
        enriched = {**world_state, "alerts": alerts}

        strategist_trace = self.strategist.run_loop(enriched)
        trace["phases"]["strategist"] = strategist_trace
        trace["decisions"].append(strategist_trace.get("phases", {}).get("decide", {}))

        actuary_trace = self.actuary.run_loop(enriched)
        trace["phases"]["actuary"] = actuary_trace
        trace["decisions"].append(actuary_trace.get("phases", {}).get("decide", {}))

        cascade_trace = self.cascade.run_loop(enriched)
        trace["phases"]["cascade"] = cascade_trace
        trace["decisions"].append(cascade_trace.get("phases", {}).get("decide", {}))

        pending = [d.get("action") for d in trace["decisions"] if isinstance(d, dict) and d.get("action")]
        executor_trace = self.executor.run_loop({**enriched, "pending_actions": pending})
        trace["phases"]["executor"] = executor_trace
        trace["decisions"].append(executor_trace.get("phases", {}).get("decide", {}))

        trace["duration_ms"] = round((time.time() - start) * 1000, 1)
        trace["finished"] = datetime.now().isoformat()
        trace["success"] = all(t.get("success", False) for t in trace["phases"].values())
        self.loop_history.append(trace)
        if len(self.loop_history) > self.max_log_size:
            self.loop_history = self.loop_history[-self.max_log_size:]
        for d in trace["decisions"]:
            if isinstance(d, dict):
                self.decision_log.append(d)
        return trace

    def run_agent(self, agent_name: str, world_state: dict) -> dict:
        agent = self.get_agent(agent_name)
        if not agent:
            return {"error": f"Agent not found: {agent_name}"}
        return agent.run_loop(world_state)

    def get_decision_log(self, limit: int = 20) -> list:
        return self.decision_log[-limit:]

    def get_loop_history(self, limit: int = 10) -> list:
        return self.loop_history[-limit:]

    def get_summary(self) -> dict:
        return {
            "agents": self.get_all_statuses(),
            "auto_mode": self.auto_mode,
            "total_loops": len(self.loop_history),
            "total_decisions": len(self.decision_log),
            "last_loop": self.loop_history[-1] if self.loop_history else None,
        }


# ============================================================
# MODULE-LEVEL SINGLETON
# ============================================================
_orchestrator: Optional[AgentOrchestrator] = None

def get_orchestrator() -> AgentOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = AgentOrchestrator()
    return _orchestrator
