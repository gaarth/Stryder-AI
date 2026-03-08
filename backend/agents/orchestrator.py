"""
STRYDER AI — Central Agent Orchestrator v4
=============================================
Pipeline: User Query → Intent Classifier → Location Detector → ML Inference → Prose Synthesis
All responses backed by real data + 5 ML models. No boilerplate.
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
    "LOCATION_QUERY",
    "COMMAND",
]

# Location name variants for detection
LOCATION_NAMES = {
    "mumbai": "PRT-MUM", "chennai": "PRT-CHE", "vishakhapatnam": "PRT-VIZ",
    "vizag": "PRT-VIZ", "kolkata": "PRT-KOL", "kochi": "PRT-KOC",
    "kandla": "PRT-KAN", "tuticorin": "PRT-TUT", "goa": "PRT-GOA",
    "delhi": "WH-DEL", "bhopal": "WH-BHO", "nagpur": "WH-NAG",
    "ahmedabad": "WH-AHM", "jaipur": "WH-JAI", "hyderabad": "WH-HYD",
    "bengaluru": "WH-BEN", "bangalore": "WH-BEN", "lucknow": "WH-LUC",
}


class AgentOrchestrator:
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

        # ── COMMAND STATE ──
        self._command_state: dict = {
            "priorities": [],       # e.g. ["Vishakhapatnam exports"]
            "focus_locations": [],   # location IDs to highlight
        }

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
    # INTENT CLASSIFICATION
    # ========================================
    def _classify_intent(self, message: str) -> str:
        msg = message.lower().strip()

        # COMMAND — user giving instructions
        if any(w in msg for w in ["prioritize", "focus on", "always", "remember", "from now on"]):
            return "COMMAND"

        # FIX_REQUEST
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

        # LOCATION_QUERY — check if message contains a known location
        for loc_name in LOCATION_NAMES:
            if loc_name in msg:
                return "LOCATION_QUERY"

        # ANALYSIS_REQUEST
        if any(w in msg for w in ["scan", "monitor", "anomal", "risk", "predict", "cascade",
                                   "analyze", "impact", "estimate", "what risks", "what learned",
                                   "what have", "learning", "memory", "overview", "fleet"]):
            return "ANALYSIS_REQUEST"

        # SYSTEM_QUERY
        if any(w in msg for w in ["strategy", "priority", "agents", "help", "mode", "system"]):
            return "SYSTEM_QUERY"

        # STATUS_QUERY
        if re.search(r'(?:shipment|ship|#)\s*\d+', msg):
            return "STATUS_QUERY"
        if any(w in msg for w in ["eta", "cost", "where", "track", "carrier", "status"]):
            return "STATUS_QUERY"

        return "STATUS_QUERY"

    # ========================================
    # PARSE @TAG, LOCATION, AND SHIPMENT ID
    # ========================================
    def _parse_message(self, message: str) -> dict:
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

        ship_ids = [int(x) for x in re.findall(r'(?:shipment|ship|#)\s*(\d+)', clean, re.IGNORECASE)]

        # Detect location
        detected_location = None
        detected_loc_id = None
        msg_lower = clean.lower()
        for loc_name, loc_id in LOCATION_NAMES.items():
            if loc_name in msg_lower:
                detected_location = loc_name.capitalize()
                detected_loc_id = loc_id
                break

        return {
            "target_agent": target_agent,
            "subtag": subtag,
            "clean_message": clean.strip(),
            "ship_ids": ship_ids,
            "location": detected_location,
            "location_id": detected_loc_id,
        }

    # ========================================
    # MAIN ROUTE
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
        location = parsed["location"]
        location_id = parsed["location_id"]

        # Context tracking
        if ship_ids:
            self._active_shipment_id = ship_ids[0]
        elif self._active_shipment_id and intent in ("OPTIMIZATION_REQUEST", "FIX_REQUEST"):
            ship_ids = [self._active_shipment_id]

        # Subtag domain routing
        SUBTAG_DOMAIN = {
            "ETA_AGENT": "Strategist", "DELAY_AGENT": "Strategist",
            "CARRIER_AGENT": "Strategist", "HUB_AGENT": "Strategist",
            "COST_AGENT": "Actuary", "CASCADE_MODEL": "Cascade",
        }
        if subtag and subtag in SUBTAG_DOMAIN:
            target = SUBTAG_DOMAIN[subtag]

        # ──────── COMMAND ────────
        if intent == "COMMAND":
            return self._handle_command(message, ops)

        # ──────── LOCATION_QUERY ────────
        if intent == "LOCATION_QUERY" and location_id:
            return self._handle_location_query(location, location_id, ops, target, subtag)

        # ──────── FIX_REQUEST ────────
        if intent == "FIX_REQUEST":
            return self._handle_fix(message, clean_msg, ship_ids, ops, target, subtag)

        # ──────── STATUS_QUERY ────────
        if intent == "STATUS_QUERY":
            return self._handle_status(clean_msg, ship_ids, ops, target, subtag)

        # ──────── OPTIMIZATION_REQUEST ────────
        if intent == "OPTIMIZATION_REQUEST":
            return self._handle_optimization(clean_msg, ship_ids, ops, target, subtag)

        # ──────── ANALYSIS_REQUEST ────────
        if intent == "ANALYSIS_REQUEST":
            return self._handle_analysis(clean_msg, ship_ids, ops, target, subtag)

        # ──────── SCENARIO_REQUEST ────────
        if intent == "SCENARIO_REQUEST":
            return self._prose("System", subtag,
                "Use the Scenario panel to inject events. "
                "Available: PORT_CONGESTION, CARRIER_STRIKE, WEATHER_DISRUPTION, "
                "WAREHOUSE_OVERFLOW, CUSTOMS_DELAY, ROUTE_BLOCKAGE")

        # ──────── SYSTEM_QUERY ────────
        if intent == "SYSTEM_QUERY":
            return self._handle_system(clean_msg, ops, target, subtag)

        return self._prose("System", subtag, "Data not available in current simulation state.")

    # ========================================
    # LOCATION QUERY (ML-backed)
    # ========================================
    def _handle_location_query(self, location: str, loc_id: str, ops, target, subtag) -> dict:
        from backend.services.model_inference import infer_location
        from backend.simulation.ops_state import CITIES

        loc_data = CITIES.get(loc_id, {})
        loc_full_name = loc_data.get("name", location)
        loc_type = loc_data.get("type", "location")

        # Find matching shipments
        matching = [s for s in ops.shipments if (
            s.get("origin_id") == loc_id or s.get("destination_id") == loc_id
            or location.lower() in s.get("origin", "").lower()
            or location.lower() in s.get("destination", "").lower()
        )]

        transit = [s for s in matching if s["status"] == "IN_TRANSIT"]
        delayed = [s for s in matching if s["status"] == "DELAYED"]

        if not matching:
            return self._prose(target or "System", subtag,
                f"No shipments currently routing through {loc_full_name}.")

        # Find port/warehouse state
        infra = None
        for p in ops.port_states:
            if p["id"] == loc_id:
                infra = p
                break
        if not infra:
            for w in ops.wh_states:
                if w["id"] == loc_id:
                    infra = w
                    break

        # Run ML inference
        assessment = infer_location(loc_full_name, transit or matching, infra)

        # Build prose response
        lines = []

        # Opening summary
        lines.append(f"{len(matching)} shipments routing through {loc_full_name} "
                      f"({len(transit)} in transit, {len(delayed)} delayed).")

        # Hub status
        hub = assessment.get("hub", {})
        cong_pct = infra.get("congestion_pct", 0) if infra else 0
        cong_level = hub.get("congestion_level", infra.get("congestion_level", "LOW") if infra else "LOW")
        if cong_level in ("CRITICAL", "HIGH"):
            lines.append(f"@HUB_AGENT reports {cong_level} congestion at {cong_pct}% capacity.")
        else:
            lines.append(f"@HUB_AGENT: {cong_level} congestion ({cong_pct}%).")

        # Delay assessment
        delay = assessment.get("delay_summary", {})
        if delay.get("high_risk_count", 0) > 0:
            ids_str = ", ".join(f"#{i}" for i in delay["high_risk_ids"][:5])
            lines.append(f"@DELAY_AGENT flags {delay['high_risk_count']} shipments at elevated delay risk ({ids_str}).")
        else:
            lines.append(f"@DELAY_AGENT: delay risk is manageable (avg {delay.get('avg_probability', 0):.0%}).")

        # Cascade
        cascade = assessment.get("cascade_summary", {})
        if cascade.get("severity") in ("CRITICAL", "HIGH"):
            lines.append(f"@CASCADE_MODEL warns of {cascade['severity']} secondary failure risk "
                          f"(probability {cascade.get('avg_probability', 0):.0%}).")
        elif cascade.get("avg_probability", 0) > 0.15:
            lines.append(f"@CASCADE_MODEL: moderate cascade risk ({cascade.get('avg_probability', 0):.0%}).")

        # Carrier summary
        carrier = assessment.get("carrier_summary", {})
        lines.append(f"@CARRIER_AGENT: fleet reliability {carrier.get('tier', 'STANDARD')} "
                      f"(avg score {carrier.get('avg_reliability', 0):.0%}).")

        # Top shipment details (first 3)
        per_ship = assessment.get("per_shipment", [])
        if per_ship:
            lines.append("")
            lines.append("Key shipments:")
            for sr in per_ship[:3]:
                sid = sr.get("shipment_id")
                ship = next((s for s in matching if s["id"] == sid), None)
                if ship:
                    eta_info = sr.get("eta", {})
                    delay_info = sr.get("delay", {})
                    eta_days = eta_info.get("predicted_eta_days", ship["eta_hours"] / 24) if eta_info else ship["eta_hours"] / 24
                    delay_pct = delay_info.get("delay_probability", 0) if delay_info else 0
                    risk_tag = f" [RISK: {delay_info.get('risk_level', 'LOW')}]" if delay_pct > 0.4 else ""
                    lines.append(f"  #{sid}: {ship['origin']} to {ship['destination']}, "
                                  f"ETA {ship['eta_hours']}h (@ETA_AGENT: {eta_days:.1f}d), "
                                  f"{ship['carrier']}{risk_tag}")

        # Command state context
        if self._command_state["priorities"]:
            relevant = [p for p in self._command_state["priorities"] if location.lower() in p.lower()]
            if relevant:
                lines.append(f"\nNote: user priority active for {', '.join(relevant)}.")

        return self._prose(target or "Sentinel", subtag, "\n".join(lines),
                           thinking=True, models=assessment.get("models_used", []))

    # ========================================
    # COMMAND HANDLER
    # ========================================
    def _handle_command(self, message: str, ops) -> dict:
        msg = message.lower()
        # Extract what to prioritize
        priority_text = message.strip()
        for prefix in ["prioritize", "focus on", "always", "remember", "from now on"]:
            if prefix in msg:
                idx = msg.index(prefix) + len(prefix)
                priority_text = message[idx:].strip().strip(".").strip(",")
                break

        if priority_text:
            self._command_state["priorities"].append(priority_text)
            # Check if it references a location
            for loc_name, loc_id in LOCATION_NAMES.items():
                if loc_name in msg:
                    if loc_id not in self._command_state["focus_locations"]:
                        self._command_state["focus_locations"].append(loc_id)

            # Save to agent memory
            ops.agent_memory["user_commands"] = self._command_state
            ops.add_learning("System", f"User command absorbed: {priority_text}")

            return self._prose("System", None,
                f"Understood. I will {priority_text.lower()} in all future assessments. "
                f"This preference is now active across all agents.")

        return self._prose("System", None, "What would you like me to prioritize or remember?")

    # ========================================
    # STATUS QUERY
    # ========================================
    def _handle_status(self, clean_msg, ship_ids, ops, target, subtag) -> dict:
        if ship_ids:
            sid = ship_ids[0]
            ship = next((s for s in ops.shipments if s["id"] == sid), None)
            if not ship:
                return self._prose(target or "System", subtag, "Data not available in current simulation state.")

            # Run ML inference on this shipment
            from backend.services.model_inference import infer_shipment
            assessment = infer_shipment(ship)

            eta_info = assessment.get("eta", {})
            delay_info = assessment.get("delay", {})
            carrier_info = assessment.get("carrier", {})
            cascade_info = assessment.get("cascade", {})

            eta_pred = eta_info.get("predicted_eta_days", ship["eta_hours"] / 24) if eta_info else ship["eta_hours"] / 24
            delay_prob = delay_info.get("delay_probability", 0) if delay_info else 0
            carrier_tier = carrier_info.get("tier", "STANDARD") if carrier_info else "STANDARD"

            # Build prose
            status_word = "en route" if ship["status"] == "IN_TRANSIT" else ship["status"].lower()
            lines = [
                f"Shipment #{sid} is {status_word} from {ship['origin']} to {ship['destination']} "
                f"via {ship['carrier']} ({carrier_tier} tier)."
            ]

            lines.append(f"@ETA_AGENT predicts {eta_pred:.1f} days ({ship['eta_hours']}h remaining). "
                          f"Current cost: INR {round(ship['current_cost']):,}.")

            if delay_prob > 0.5:
                lines.append(f"@DELAY_AGENT flags elevated risk ({delay_prob:.0%} delay probability). "
                              f"Penalty rate: INR {ship['delay_penalty_per_hour']:,.0f}/hr.")
            elif delay_prob > 0.3:
                lines.append(f"@DELAY_AGENT: moderate delay risk ({delay_prob:.0%}).")
            else:
                lines.append(f"@DELAY_AGENT: delay risk is low ({delay_prob:.0%}).")

            if cascade_info and cascade_info.get("severity") in ("HIGH", "CRITICAL"):
                lines.append(f"@CASCADE_MODEL: {cascade_info['severity']} cascade risk detected.")

            if ship.get("disrupted"):
                lines.append(f"This shipment was affected by a disruption (ID: {ship.get('disruption_id')}).")

            return self._prose(target or "ETA Agent", subtag, "\n".join(lines),
                               thinking=True, models=["ETA_AGENT", "DELAY_AGENT", "CARRIER_AGENT", "CASCADE_MODEL"])

        # Sentinel scan / general status
        if target == "Sentinel" or "scan" in clean_msg.lower() or "monitor" in clean_msg.lower():
            alerts = ops.sentinel_scan()
            stats = ops.get_snapshot()["stats"]
            disruptions = stats["active_disruptions"]

            summary = f"{stats['in_transit']} shipments in transit, {stats['delayed']} delayed"
            if disruptions:
                summary += f" across {disruptions} active disruption{'s' if disruptions > 1 else ''}"
            summary += "."

            lines = [summary]

            if alerts:
                lines.append("Anomalies detected:")
                for a in alerts[:4]:
                    lines.append(f"  {a}")
            else:
                lines.append("All systems nominal. No anomalies detected.")

            # Check command state priorities
            if self._command_state["focus_locations"]:
                for loc_id in self._command_state["focus_locations"]:
                    from backend.simulation.ops_state import CITIES
                    loc = CITIES.get(loc_id, {})
                    loc_ships = [s for s in ops.shipments if s.get("destination_id") == loc_id and s["status"] == "IN_TRANSIT"]
                    if loc_ships:
                        lines.append(f"Priority watch: {loc.get('name', loc_id)} has {len(loc_ships)} incoming shipments.")

            return self._prose("Sentinel", subtag, "\n".join(lines))

        # General overview
        stats = ops.get_snapshot()["stats"]
        strategy = ops.agent_memory.get("global_strategy", "balanced").upper()
        lines = [
            f"{stats['total']} total shipments: {stats['in_transit']} in transit, "
            f"{stats['delayed']} delayed, {stats['delivered']} delivered.",
            f"Active disruptions: {stats['active_disruptions']}. Strategy: {strategy}.",
        ]
        return self._prose("System", subtag, "\n".join(lines))

    # ========================================
    # FIX REQUEST
    # ========================================
    def _handle_fix(self, message, clean_msg, ship_ids, ops, target, subtag) -> dict:
        apply_match = re.search(r'apply\s+option\s+(\d+)', message, re.IGNORECASE)
        if apply_match:
            opt_idx = int(apply_match.group(1))
            sid = self._last_optimize_id or (ship_ids[0] if ship_ids else None)
            if not sid:
                return self._prose("Executor", subtag, "No pending optimization. Use @Strategist:ETA_AGENT optimize shipment <id> first.")
            result = ops.apply_option(sid, opt_idx)
            if "error" in result:
                return self._prose("Executor", subtag, result["error"])
            ops.add_learning("Executor", f"Applied option {opt_idx} to shipment #{sid}: {result['applied']}")
            return self._prose("Executor", subtag,
                f"@Executor applied {result['applied']} to shipment #{sid}. "
                f"ETA: {result['old_eta']}h down to {result['new_eta']}h. "
                f"Cost: INR {result['old_cost']:,} to INR {result['new_cost']:,}.")

        if ship_ids:
            sid = ship_ids[0]
            ship = next((s for s in ops.shipments if s["id"] == sid), None)
            if not ship:
                return self._prose("Executor", subtag, "Data not available in current simulation state.")
            if "carrier" in clean_msg.lower() or "switch" in clean_msg.lower():
                result = ops.execute_command("SWITCH_CARRIER", {"shipment_id": sid, "carrier": "BlueDart"})
                if result.get("ok"):
                    ops.add_learning("Executor", f"Switched carrier for #{sid}: {result['old_carrier']} to {result['new_carrier']}")
                    return self._prose("Executor", subtag,
                        f"@Executor switched carrier for shipment #{sid} from {result['old_carrier']} to {result['new_carrier']}.")
        return self._prose("Executor", subtag, "Specify a shipment and action. Example: Apply option 1, or switch carrier for shipment #13")

    # ========================================
    # OPTIMIZATION REQUEST (ML-backed)
    # ========================================
    def _handle_optimization(self, clean_msg, ship_ids, ops, target, subtag) -> dict:
        if not ship_ids:
            return self._prose("Strategist", subtag, "Specify a shipment to optimize. Example: optimize shipment 13")

        sid = ship_ids[0]
        self._active_shipment_id = sid
        ship = next((s for s in ops.shipments if s["id"] == sid), None)
        if not ship:
            return self._prose("Strategist", subtag, "Data not available in current simulation state.")
        if ship["status"] == "DELIVERED":
            return self._prose("Strategist", subtag, f"Shipment #{sid} already delivered.")

        # Carrier-specific optimization
        if subtag == "CARRIER_AGENT" or "carrier" in clean_msg.lower():
            from backend.simulation.ops_state import CARRIERS, CARRIER_MAP
            current = CARRIER_MAP.get(ship["carrier"], {})
            lines = [f"Carrier analysis for shipment #{sid} (currently {ship['carrier']}, "
                      f"speed factor {current.get('speed_factor', 'N/A')}):"]
            for c in CARRIERS:
                if c["name"] != ship["carrier"]:
                    eta_diff = round((current.get("speed_factor", 1.0) - c["speed_factor"]) * ship["eta_hours"] / current.get("speed_factor", 1.0))
                    cost_diff = round((c["base_rate"] - current.get("base_rate", 300)) * ship["eta_hours"] / 10)
                    sign_eta = "+" if eta_diff > 0 else ""
                    sign_cost = "+" if cost_diff > 0 else ""
                    lines.append(f"  {c['name']}: ETA {sign_eta}{-eta_diff}h, cost {sign_cost}INR {cost_diff:,}")
                    if len(lines) > 8:
                        break
            return self._prose("Carrier Agent", subtag, "\n".join(lines), thinking=True, models=["CARRIER_AGENT"])

        # Default ETA optimization
        result = ops.optimize_eta(sid)
        if "error" in result:
            return self._prose("Strategist", subtag, result["error"])
        self._last_optimize_id = sid
        ops.add_learning("Strategist", f"Generated ETA optimization options for shipment #{sid}")

        lines = [
            f"@ETA_AGENT optimization for shipment #{sid} ({result['origin']} to {result['destination']}).",
            f"Current: {result['current_eta']}h, INR {result['current_cost']:,}, {result['current_carrier']}.",
            ""
        ]
        for opt in result["options"]:
            lines.append(f"Option {opt['index']}: {opt['description']}")
            lines.append(f"  ETA: {opt['eta']}h (saves {opt['eta_saved']}h), cost +INR {opt['cost_increase']:,}")
            if opt.get("carrier") != result["current_carrier"]:
                lines.append(f"  Carrier: {opt['carrier']}")
            lines.append("")
        lines.append("Say 'Apply option 1/2/3' to execute.")
        return self._prose("Strategist", "ETA_AGENT", "\n".join(lines), thinking=True, models=["ETA_AGENT"])

    # ========================================
    # ANALYSIS REQUEST (ML-backed)
    # ========================================
    def _handle_analysis(self, clean_msg, ship_ids, ops, target, subtag) -> dict:
        msg = clean_msg.lower()

        # Sentinel scan
        if target == "Sentinel" or "scan" in msg or "monitor" in msg or "anomal" in msg:
            return self._handle_status(clean_msg, [], ops, "Sentinel", subtag)

        # Cascade risk
        if target == "Cascade" or "risk" in msg or "predict" in msg or "cascade" in msg:
            alerts = ops.cascade_predict()
            if alerts:
                lines = [f"{len(alerts)} cascade risk predictions detected:"]
                for a in alerts[:5]:
                    lines.append(f"  {a['location']}: {a['type'].replace('_', ' ')} "
                                  f"(confidence {a['confidence']}%, {a['impact_count']} shipments at risk)")
                    lines.append(f"  Suggested: {a['suggestion']}")
                return self._prose("Cascade", subtag, "\n".join(lines), thinking=True, models=["CASCADE_MODEL"])
            return self._prose("Cascade", subtag, "No cascade risks predicted. System is stable.")

        # Actuary cost analysis
        if target == "Actuary" or "cost" in msg or "impact" in msg:
            if ship_ids:
                sid = ship_ids[0]
                ship = next((s for s in ops.shipments if s["id"] == sid), None)
                if ship:
                    penalty = round(ship["current_cost"] - ship["base_cost"])
                    return self._prose("Actuary", subtag,
                        f"Shipment #{sid} cost breakdown: base INR {ship['base_cost']:,.0f}, "
                        f"current INR {round(ship['current_cost']):,}, "
                        f"penalty accrued INR {penalty:,} (rate: INR {ship['delay_penalty_per_hour']:,.0f}/hr). "
                        f"Status: {ship['status']}.")

            total_base = sum(s["base_cost"] for s in ops.shipments)
            total_current = sum(s["current_cost"] for s in ops.shipments)
            penalty = round(total_current - total_base)
            delayed = sum(1 for s in ops.shipments if s["status"] == "DELAYED")
            return self._prose("Actuary", subtag,
                f"Fleet overview: base cost INR {total_base:,.0f}, current INR {round(total_current):,}, "
                f"total penalties INR {penalty:,}. {delayed} shipments delayed.")

        # Learning summary
        if "learn" in msg or "memory" in msg or "what have" in msg:
            learn = ops.agent_memory["agent_learnings"]
            recent = ops.learning_logs[-5:] if ops.learning_logs else []
            lines = [
                f"Hours saved: {learn['total_hours_saved']}h. Cost saved: INR {learn['total_cost_saved']:,}. "
                f"{learn['sentinel_detections']} detections, {learn['strategist_optimizations']} optimizations, "
                f"{learn['executor_executions']} executions."
            ]
            if recent:
                lines.append("Recent learnings:")
                for log in recent:
                    lines.append(f"  [{log['ts']}] {log['agent']}: {log['message']}")
            if self._command_state["priorities"]:
                lines.append(f"Active user commands: {', '.join(self._command_state['priorities'])}")
            return self._prose("System", subtag, "\n".join(lines))

        return self._prose("System", subtag, "Specify what to analyze. Try: @Cascade analyze risk, @Actuary estimate cost, or ask about a specific location.")

    # ========================================
    # SYSTEM QUERY
    # ========================================
    def _handle_system(self, clean_msg, ops, target, subtag) -> dict:
        msg = clean_msg.lower()
        if "strategy" in msg:
            if "cost" in msg:
                ops.execute_command("SET_STRATEGY", {"strategy": "cost"})
                ops.add_learning("System", "User set global strategy to COST_OPTIMIZED")
                return self._prose("System", subtag, "Strategy set to COST_OPTIMIZED. All agents will now prioritize lowest cost.")
            elif "speed" in msg or "time" in msg or "fast" in msg:
                ops.execute_command("SET_STRATEGY", {"strategy": "speed"})
                ops.add_learning("System", "User set global strategy to TIME_OPTIMIZED")
                return self._prose("System", subtag, "Strategy set to TIME_OPTIMIZED. All agents will now prioritize fastest delivery.")
            elif "balanced" in msg:
                ops.execute_command("SET_STRATEGY", {"strategy": "balanced"})
                return self._prose("System", subtag, "Strategy set to BALANCED. Agents balance cost and speed.")
            return self._prose("System", subtag,
                f"Current strategy: {ops.agent_memory['global_strategy'].upper()}. "
                "Set with: strategy cost, strategy speed, or strategy balanced.")

        if "help" in msg:
            return self._prose("System", subtag,
                "Commands: shipment <id>, strategy <cost/speed/balanced>, optimize shipment <id>, "
                "@Sentinel scan, @Cascade analyze risk, @Actuary cost, or ask about any location by name (e.g. Vishakhapatnam).")

        if "agent" in msg:
            return self._prose("System", subtag,
                "Active agents: Sentinel (anomaly detection), Strategist (ETA/carrier optimization), "
                "Actuary (cost analysis), Executor (applies fixes), Cascade (secondary failure prediction). "
                "ML models: @ETA_AGENT, @DELAY_AGENT, @CARRIER_AGENT, @HUB_AGENT, @CASCADE_MODEL.")

        stats = ops.get_snapshot()["stats"]
        return self._prose("System", subtag,
            f"{stats['total']} shipments, {stats['in_transit']} in transit, {stats['delayed']} delayed. "
            f"Strategy: {ops.agent_memory['global_strategy'].upper()}.")

    # ========================================
    # OUTPUT (prose, no markdown)
    # ========================================
    def _prose(self, agent: str, subtag: Optional[str], response, thinking=False, models=None) -> dict:
        if isinstance(response, dict):
            text = response.get("response", str(response))
        else:
            text = str(response)
        # Strip any markdown artifacts
        text = text.replace("**", "").replace("##", "").replace("# ", "")
        return {
            "agent": agent,
            "subtag": subtag,
            "response": text,
            "timestamp": datetime.now().isoformat(),
            "thinking": thinking,
            "models_used": models or [],
        }

    # Keep old _out for backward compat
    def _out(self, agent, subtag, response):
        return self._prose(agent, subtag, response)

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
