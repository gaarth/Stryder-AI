"""
STRYDER AI — Sovereign Orchestrator v7 :: GROQ BRAIN
=============================================
Architecture:
- Groq (Llama 3.3 70B) is the conversational brain.
- ML models (ETA, DELAY, CARRIER, HUB, CASCADE) run inference.
- Results are fed into Groq's system prompt as live context.
- Execution commands (fix, optimize, apply) stay deterministic.
- Everything else: Groq answers freely with full simulation awareness.
"""
import json
import re
import time
import uuid
from datetime import datetime
from typing import Optional

try:
    from groq import Groq
    HAS_GROQ = True
except ImportError:
    HAS_GROQ = False

from backend.agents.base_agent import Decision
from backend.agents.sentinel import SentinelAgent
from backend.agents.strategist import StrategistAgent
from backend.agents.actuary import ActuaryAgent
from backend.agents.executor import ExecutorAgent
from backend.agents.cascade import CascadeAgent
from backend.config import GROQ_API_KEY, GROQ_MODEL

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

        # ── CONTEXT TRACKING (conversation memory) ──
        self._active_shipment_id: Optional[int] = None
        self._previous_shipment_id: Optional[int] = None
        self._active_agent: Optional[str] = None
        self._last_optimize_id: Optional[int] = None
        self._last_recommendation: Optional[dict] = None
        self._discussed_ids: list[int] = []

        # ── CONVERSATION HISTORY for Groq ──
        self._chat_history: list[dict] = []
        self._max_history = 20

        # ── COMMAND STATE (permanent constraints) ──
        self._command_state: dict = {
            "priorities": [],
            "focus_locations": [],
            "carrier_bans": {},
        }

        # ── GROQ CLIENT ──
        self._groq = None
        if HAS_GROQ and GROQ_API_KEY:
            self._groq = Groq(api_key=GROQ_API_KEY)
            print(f"[STRYDER AI] Groq LLM connected: {GROQ_MODEL}")
        else:
            print("[STRYDER AI] Groq LLM not available — falling back to rule-based")

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

        # FIX_REQUEST — only direct action phrases, not complex analytical requests
        if re.search(r'apply\s+(option\s+)?\d+', msg):
            return "FIX_REQUEST"
        # Short direct fix commands only
        fix_direct = ["fix it", "fix this", "fix shipment", "reroute shipment", "switch carrier"]
        if any(f in msg for f in fix_direct):
            return "FIX_REQUEST"
        # "fix" or "execute" alone (short msg) = action. In long msg = let Groq handle
        if msg.strip() in ["fix", "fix it", "execute", "heal", "resolve"]:
            return "FIX_REQUEST"
        if re.search(r'\bfix\b.*#?\d+', msg) or re.search(r'\breroute\b.*#?\d+', msg):
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
        clean_msg = parsed["clean_message"]
        ship_ids = parsed["ship_ids"]
        target = parsed["target_agent"]
        subtag = parsed["subtag"]

        # ── CONVERSATION MEMORY ──
        msg_lower = message.lower()
        if not ship_ids and ("other one" in msg_lower or "that one" in msg_lower or "previous" in msg_lower):
            if self._previous_shipment_id:
                ship_ids = [self._previous_shipment_id]
        if ship_ids:
            if self._active_shipment_id and self._active_shipment_id != ship_ids[0]:
                self._previous_shipment_id = self._active_shipment_id
            self._active_shipment_id = ship_ids[0]
            if ship_ids[0] not in self._discussed_ids:
                self._discussed_ids.append(ship_ids[0])
                if len(self._discussed_ids) > 20:
                    self._discussed_ids = self._discussed_ids[-20:]
        elif self._active_shipment_id and intent in ("OPTIMIZATION_REQUEST", "FIX_REQUEST"):
            ship_ids = [self._active_shipment_id]

        # ====== DETERMINISTIC HANDLERS (state mutations) ======
        # These MUST stay rule-based because they change simulation state

        # Fix/Execute commands
        if intent == "FIX_REQUEST":
            return self._handle_fix(message, clean_msg, ship_ids, ops, target, subtag)

        # Optimization with options
        if intent == "OPTIMIZATION_REQUEST" and ship_ids:
            return self._handle_optimization(clean_msg, ship_ids, ops, target, subtag)

        # User commands (prioritize, never use, etc.)
        if intent == "COMMAND":
            return self._handle_command(message, ops)

        # ====== EVERYTHING ELSE: GROQ LLM ======
        return self._llm_respond(message, ops, ship_ids, parsed)

    # ========================================
    # GROQ LLM BRAIN
    # ========================================
    def _build_context(self, ops, ship_ids: list) -> str:
        """Build live simulation context for Groq system prompt."""
        try:
            return self._build_context_inner(ops, ship_ids)
        except Exception as e:
            print(f"[STRYDER AI] Context build error: {e}")
            import traceback; traceback.print_exc()
            stats = ops.get_snapshot().get("stats", {})
            return (f"=== LIVE SIMULATION STATE ===\n"
                    f"Total: {stats.get('total', '?')} | In transit: {stats.get('in_transit', '?')} | "
                    f"Delayed: {stats.get('delayed', '?')} | Disruptions: {stats.get('active_disruptions', '?')}")

    def _build_context_inner(self, ops, ship_ids: list) -> str:
        from backend.services.model_inference import infer_shipment
        stats = ops.get_snapshot().get("stats", {})

        lines = [
            "=== LIVE SIMULATION STATE ===",
            f"Total shipments: {stats.get('total', 0)}",
            f"In transit: {stats.get('in_transit', 0)} | Delayed: {stats.get('delayed', 0)} | Delivered: {stats.get('delivered', 0)}",
            f"Active disruptions: {stats.get('active_disruptions', 0)}",
            f"Strategy: {ops.agent_memory.get('global_strategy', 'balanced').upper()}",
        ]

        # ML inference on user-referenced shipments
        if ship_ids:
            for sid in ship_ids[:3]:
                ship = next((s for s in ops.shipments if s.get("id") == sid), None)
                if not ship:
                    continue
                lines.append(f"\n--- Shipment #{sid} ---")
                lines.append(f"Route: {ship.get('origin','?')} -> {ship.get('destination','?')}")
                lines.append(f"Status: {ship.get('status','?')} | Carrier: {ship.get('carrier','?')}")
                lines.append(f"ETA: {ship.get('eta_hours','?')}h | Cost: INR {round(ship.get('current_cost', 0)):,}")
                if ship.get("disrupted"):
                    lines.append(f"DISRUPTED (event: {ship.get('disruption_id')})")
                assessment = infer_shipment(ship) or {}
                eta = assessment.get("eta") or {}
                delay = assessment.get("delay") or {}
                carrier = assessment.get("carrier") or {}
                cascade = assessment.get("cascade") or {}
                lines.append(f"@ETA_AGENT: {eta.get('predicted_eta_days', 'N/A')} days")
                lines.append(f"@DELAY_AGENT: delay prob {delay.get('delay_probability', 'N/A')}")
                lines.append(f"@CARRIER_AGENT: tier {carrier.get('tier', 'N/A')}, variance {carrier.get('variance', 'N/A')}")
                lines.append(f"@CASCADE_MODEL: cascade {cascade.get('cascade_probability', 'N/A')}, severity {cascade.get('severity', 'N/A')}")

        # Top at-risk shipments
        at_risk = []
        for s in ops.shipments:
            if s.get("status") in ("IN_TRANSIT", "DELAYED"):
                try:
                    assessment = infer_shipment(s) or {}
                    cp = (assessment.get("cascade") or {}).get("cascade_probability", 0) or 0
                    dp = (assessment.get("delay") or {}).get("delay_probability", 0) or 0
                    risk = (cp * 2) + dp + (0.3 if s.get("disrupted") else 0)
                    if risk > 0.5:
                        at_risk.append((s, risk, cp, dp))
                except Exception:
                    continue
        at_risk.sort(key=lambda x: x[1], reverse=True)

        if at_risk:
            lines.append(f"\n=== TOP {min(len(at_risk), 5)} AT-RISK SHIPMENTS ===")
            for s, risk, cp, dp in at_risk[:5]:
                lines.append(f"  #{s['id']} {s.get('origin','?')}->{s.get('destination','?')} "
                             f"[{s.get('status','?')}] cascade={cp:.2f} delay={dp:.2f}")
        else:
            lines.append("\n=== RISK STATUS: ALL CLEAR ===")

        # Active disruptions
        for d in getattr(ops, 'disruptions', []):
            if not d.get("resolved"):
                lines.append(f"  DISRUPTION: {d.get('type', '?')} at {d.get('location', '?')} "
                             f"(severity: {d.get('severity', 'N/A')})")

        # User constraints
        if self._command_state.get("priorities"):
            lines.append(f"\nUser priorities: {', '.join(self._command_state['priorities'])}")
        if self._command_state.get("carrier_bans"):
            lines.append(f"Carrier bans: {json.dumps(self._command_state['carrier_bans'])}")

        # Recent learnings
        for log in (getattr(ops, 'learning_logs', None) or [])[-5:]:
            lines.append(f"  [{log.get('agent','?')}] {log.get('message','')}")

        # === INFRASTRUCTURE ===
        lines.append("\n=== PORT STATUS ===")
        for p in getattr(ops, 'port_states', []):
            if not p:
                continue
            pid = p.get('id', '')
            name = p.get('name', pid)
            util_pct = p.get('congestion_pct', p.get('utilization', p.get('congestion', 0)))
            if isinstance(util_pct, float) and util_pct <= 1.0:
                util_pct = round(util_pct * 100)
            incoming = len([s for s in ops.shipments if s.get('destination_id') == pid and s.get('status') == 'IN_TRANSIT'])
            outgoing = len([s for s in ops.shipments if s.get('origin_id') == pid and s.get('status') == 'IN_TRANSIT'])
            tp = p.get('throughput', 0)
            lines.append(f"  {name}: {util_pct}% congestion | throughput {tp} | {incoming} incoming, {outgoing} outgoing")

        lines.append("\n=== WAREHOUSE STATUS ===")
        for w in getattr(ops, 'wh_states', []):
            if not w:
                continue
            wid = w.get('id', '')
            name = w.get('name', wid)
            util_pct = w.get('utilization_pct', w.get('utilization', w.get('load', 0)))
            if isinstance(util_pct, float) and util_pct <= 1.0:
                util_pct = round(util_pct * 100)
            incoming = len([s for s in ops.shipments if s.get('destination_id') == wid and s.get('status') == 'IN_TRANSIT'])
            outgoing = len([s for s in ops.shipments if s.get('origin_id') == wid and s.get('status') == 'IN_TRANSIT'])
            cap = w.get('capacity', 0)
            curr = w.get('current_load', w.get('stock', 0))
            lines.append(f"  {name}: {util_pct}% utilized ({curr}/{cap}) | {incoming} incoming, {outgoing} outgoing")

        return "\n".join(lines)

    def _llm_respond(self, message: str, ops, ship_ids: list, parsed: dict) -> dict:
        """Send user message + live context to Groq and return natural response."""

        # Build context
        context = self._build_context(ops, ship_ids)

        system_prompt = f"""You are STRYDER SOVEREIGN, an advanced logistics AI managing a shipping network centered on Vishakhapatnam Port, India.

You have 5 ML sensor models feeding you real-time data:
- @ETA_AGENT: Physics-based arrival time prediction
- @DELAY_AGENT: Statistical delay probability
- @CARRIER_AGENT: Carrier reliability scoring
- @HUB_AGENT: Port/warehouse congestion forecasting
- @CASCADE_MODEL: Chain-reaction failure risk (0.0-1.0)

Below is the LIVE state of the simulation right now. Use this data to answer the user's questions accurately.

{context}

AVAILABLE EXECUTION COMMANDS (tell the user to type these to trigger real actions):
- "fix it" — auto-finds and fixes the most critical shipment
- "fix shipment #N" — fixes a specific shipment
- "optimize shipment #N" — shows optimization options for a specific shipment
- "apply option N" or "apply N" — executes a previously shown optimization option
- "switch carrier shipment #N" — switches carrier for a specific shipment
- "prioritize [location/rule]" — sets a permanent priority constraint
- "never use [carrier] for [location]" — sets a permanent carrier ban

RULES:
1. Be conversational, intelligent, and direct. You are an operations expert, not a chatbot.
2. When discussing shipments, reference the ML model outputs to support your analysis.
3. If the user asks about risk, anomalies, or problems — dig into the data and give them insight.
4. For complex operations (e.g. "reduce warehouse load", "rebalance the network"), ANALYZE the infrastructure data, identify which specific shipments to reroute, and tell the user the exact commands to run (e.g. "I recommend: optimize shipment #45, then fix shipment #67").
5. Don't dump raw JSON. Interpret the data like an analyst would.
6. You can discuss strategy, trade-offs, what-if scenarios, carrier performance — anything about the network.
7. Keep responses concise but thorough. No filler. No generic AI disclaimers.
8. When referencing ports or warehouses, use the utilization data to give concrete numbers.
9. For multi-step operations, break them down into specific executable steps the user can follow.
10. Do NOT use markdown formatting (no **, ##, etc). Plain text only."""

        # Add user message to history
        self._chat_history.append({"role": "user", "content": message})

        # Build messages for Groq
        messages = [{"role": "system", "content": system_prompt}]
        # Include conversation history (last N messages)
        for msg in self._chat_history[-self._max_history:]:
            messages.append(msg)

        if self._groq:
            try:
                response = self._groq.chat.completions.create(
                    model=GROQ_MODEL,
                    messages=messages,
                    temperature=0.6,
                    max_tokens=1024,
                )
                text = response.choices[0].message.content
            except Exception as e:
                print(f"[STRYDER AI] Groq error: {e}")
                text = self._fallback_response(message, ops, ship_ids, parsed)
        else:
            text = self._fallback_response(message, ops, ship_ids, parsed)

        # Strip markdown if Groq accidentally includes it
        text = text.replace("**", "").replace("##", "").replace("# ", "").replace("---", "")

        # Save to history
        self._chat_history.append({"role": "assistant", "content": text})
        if len(self._chat_history) > self._max_history * 2:
            self._chat_history = self._chat_history[-self._max_history:]

        return {
            "agent": parsed.get("target_agent") or "Sovereign",
            "subtag": parsed.get("subtag"),
            "response": text,
            "timestamp": datetime.now().isoformat(),
            "thinking": True,
            "models_used": ["ETA_AGENT", "DELAY_AGENT", "CARRIER_AGENT", "HUB_AGENT", "CASCADE_MODEL"],
        }

    def _fallback_response(self, message: str, ops, ship_ids: list, parsed: dict) -> str:
        """Rule-based fallback when Groq is unavailable."""
        stats = ops.get_snapshot()["stats"]
        if ship_ids:
            sid = ship_ids[0]
            ship = next((s for s in ops.shipments if s["id"] == sid), None)
            if ship:
                return (f"Shipment #{sid}: {ship['origin']} to {ship['destination']}, "
                        f"status {ship['status']}, carrier {ship['carrier']}, "
                        f"ETA {ship['eta_hours']}h, cost INR {round(ship['current_cost']):,}. "
                        f"Say 'fix shipment {sid}' to intervene or 'optimize shipment {sid}' for options.")
        return (f"Network: {stats['in_transit']} in transit, {stats['delayed']} delayed, "
                f"{stats['active_disruptions']} disruptions. "
                f"Ask me about any shipment, location, or say 'fix it' to intervene.")

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

        # Detect carrier ban: "never use X for Y"
        ban_match = re.search(r'never\s+use\s+(\w+[\w\s]*?)\s+for\s+(\w+)', msg)
        if ban_match:
            carrier = ban_match.group(1).strip().title()
            location = ban_match.group(2).strip().title()
            if location not in self._command_state["carrier_bans"]:
                self._command_state["carrier_bans"][location] = []
            if carrier not in self._command_state["carrier_bans"][location]:
                self._command_state["carrier_bans"][location].append(carrier)
            ops.agent_memory["user_commands"] = self._command_state
            ops.add_learning("System", f"Permanent constraint: {carrier} banned for {location}")
            return self._prose("System", None,
                f"Constraint absorbed. {carrier} is now permanently excluded from {location} routing. "
                f"All agents will enforce this in future decisions.")

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
            ops.add_learning("System", f"Command absorbed: {priority_text}")

            return self._prose("System", None,
                f"Absorbed. '{priority_text}' is now a standing order across all agents. "
                f"This will be enforced in every assessment from this point forward.")

        return self._prose("System", None, "Give me an instruction to absorb. For example: 'Prioritize Vishakhapatnam exports' or 'Never use FedEx for Kolkata.'")

    # ========================================
    # STATUS QUERY (anomaly-first, no data dumps)
    # ========================================
    def _handle_status(self, clean_msg, ship_ids, ops, target, subtag) -> dict:
        if ship_ids:
            sid = ship_ids[0]
            ship = next((s for s in ops.shipments if s["id"] == sid), None)
            if not ship:
                return self._prose(target or "System", subtag, "That shipment does not exist in the current simulation.")

            # Run ML inference INTERNALLY — scores are never shown raw
            from backend.services.model_inference import infer_shipment
            assessment = infer_shipment(ship)

            eta_info = assessment.get("eta", {})
            delay_info = assessment.get("delay", {})
            carrier_info = assessment.get("carrier", {})
            cascade_info = assessment.get("cascade", {})

            # COGNITIVE FILTER: interpret scores, don't dump them
            delay_prob = delay_info.get("delay_probability", 0) if delay_info else 0
            cascade_prob = cascade_info.get("cascade_probability", 0) if cascade_info else 0
            carrier_tier = carrier_info.get("tier", "STANDARD") if carrier_info else "STANDARD"
            eta_pred = eta_info.get("predicted_eta_days", ship["eta_hours"] / 24) if eta_info else ship["eta_hours"] / 24

            # Strategic conclusion, not a data dump
            status_word = "en route" if ship["status"] == "IN_TRANSIT" else ship["status"].lower()
            lines = [f"Shipment #{sid}: {ship['origin']} to {ship['destination']}, {status_word} via {ship['carrier']}."]

            # Only surface what MATTERS
            if cascade_prob > 0.7:
                lines.append(f"CRITICAL: This shipment is at high cascade risk. Immediate reroute recommended. Say 'fix it' to execute.")
            elif delay_prob > 0.5:
                lines.append(f"WARNING: Elevated delay risk detected. {carrier_tier}-tier carrier may be insufficient for this corridor.")
                lines.append(f"Recommended action: carrier switch or expedited routing. Say 'fix shipment {sid}' to intervene.")
            elif delay_prob > 0.3:
                lines.append(f"Moderate risk. Monitoring. ETA holds at {eta_pred:.1f} days but corridor pressure is building.")
            else:
                lines.append(f"On track. ETA holds at {eta_pred:.1f} days. No intervention needed.")

            if ship.get("disrupted"):
                lines.append(f"Note: this shipment was hit by a disruption event. Recovery is {'in progress' if ship['status'] == 'IN_TRANSIT' else 'stalled'}.")

            return self._prose(target or "Strategist", subtag, "\n".join(lines),
                               thinking=True, models=["ETA_AGENT", "DELAY_AGENT", "CARRIER_AGENT", "CASCADE_MODEL"])

        # Sentinel scan — ANOMALY FIRST, not a dashboard summary
        if target == "Sentinel" or "scan" in clean_msg.lower() or "monitor" in clean_msg.lower() or "anomal" in clean_msg.lower():
            alerts = ops.sentinel_scan()
            stats = ops.get_snapshot()["stats"]

            # Run cascade inference to find real threats
            from backend.services.model_inference import infer_shipment
            threats = []
            for s in ops.shipments:
                if s["status"] in ("IN_TRANSIT", "DELAYED"):
                    assessment = infer_shipment(s)
                    cascade_p = assessment.get("cascade", {}).get("cascade_probability", 0)
                    if cascade_p > 0.5:
                        threats.append((s, cascade_p))
            threats.sort(key=lambda x: x[1], reverse=True)

            if threats:
                lines = [f"{len(threats)} shipment{'s' if len(threats) > 1 else ''} flagged as cascade risk:"]
                for ship, prob in threats[:4]:
                    severity = "CRITICAL" if prob > 0.7 else "HIGH"
                    lines.append(f"  #{ship['id']} {ship['origin']} to {ship['destination']} [{severity}] — intervention recommended")
                lines.append(f"\n{stats['delayed']} delayed, {stats['active_disruptions']} active disruptions.")
                lines.append("Say 'fix it' and I will handle the most critical one.")
            elif stats["delayed"] > 0:
                lines = [f"{stats['delayed']} shipments delayed but cascade risk is contained."]
                if alerts:
                    for a in alerts[:3]:
                        lines.append(f"  {a}")
                lines.append("Monitoring. No autonomous action required yet.")
            else:
                lines = ["All clear. No anomalies, no cascade threats, no delays. Grid is stable."]

            # Priority watch
            if self._command_state["focus_locations"]:
                for loc_id in self._command_state["focus_locations"]:
                    from backend.simulation.ops_state import CITIES
                    loc = CITIES.get(loc_id, {})
                    loc_ships = [s for s in ops.shipments if s.get("destination_id") == loc_id and s["status"] == "IN_TRANSIT"]
                    if loc_ships:
                        lines.append(f"Priority watch: {loc.get('name', loc_id)} — {len(loc_ships)} inbound.")

            return self._prose("Sentinel", subtag, "\n".join(lines),
                               thinking=True, models=["CASCADE_MODEL", "DELAY_AGENT"])

        # General query — still anomaly-first
        stats = ops.get_snapshot()["stats"]
        if stats["delayed"] > 0 or stats["active_disruptions"] > 0:
            return self._prose("Sentinel", subtag,
                f"{stats['delayed']} delayed, {stats['active_disruptions']} disruptions active. "
                f"Say '@Sentinel scan' for threat assessment or 'fix it' for autonomous intervention.")
        return self._prose("Sentinel", subtag,
            f"Grid stable. {stats['in_transit']} in transit, 0 anomalies. Strategy: {ops.agent_memory.get('global_strategy', 'balanced').upper()}.")

    # ========================================
    # FIX REQUEST (KILLSWITCH: total execution autonomy)
    # ========================================
    def _handle_fix(self, message, clean_msg, ship_ids, ops, target, subtag) -> dict:
        # Apply a previously shown option
        apply_match = re.search(r'apply\s+option\s+(\d+)', message, re.IGNORECASE)
        if apply_match:
            opt_idx = int(apply_match.group(1))
            sid = self._last_optimize_id or (ship_ids[0] if ship_ids else None)
            if not sid:
                return self._prose("Executor", subtag, "No pending context. Say 'fix it' and I will find the target myself.")
            result = ops.apply_option(sid, opt_idx)
            if "error" in result:
                return self._prose("Executor", subtag, result["error"])
            ops.add_learning("Executor", f"Applied option {opt_idx} to #{sid}: {result['applied']}")
            return self._prose("Executor", subtag,
                f"Action complete. Shipment #{sid} rerouted: {result['applied']}. "
                f"ETA cut from {result['old_eta']}h to {result['new_eta']}h. Supply chain state healed.",
                thinking=True, models=["ETA_AGENT", "CARRIER_AGENT"])

        # ── KILLSWITCH: "fix it" / "execute" / "fix" ──
        fix_triggers = ["fix it", "fix this", "execute", "fix", "heal", "resolve"]
        is_fix_all = not ship_ids and any(t in clean_msg.lower().strip() for t in fix_triggers)

        if is_fix_all:
            # Step 1: IDENTIFY — rank ALL at-risk shipments by CASCADE score
            from backend.services.model_inference import infer_shipment
            candidates = [s for s in ops.shipments if s["status"] in ("IN_TRANSIT", "DELAYED")]
            if not candidates:
                return self._prose("Executor", subtag, "Grid is clean. All shipments delivered or on track. Nothing to kill.")

            scored = []
            for s in candidates:
                assessment = infer_shipment(s)
                cascade_p = assessment.get("cascade", {}).get("cascade_probability", 0)
                delay_p = assessment.get("delay", {}).get("delay_probability", 0)
                # Combined severity: cascade weighted 2x
                severity = (cascade_p * 2) + delay_p + (0.3 if s.get("disrupted") else 0)
                scored.append((s, severity, assessment))

            scored.sort(key=lambda x: x[1], reverse=True)
            worst, severity, assessment = scored[0]

            if severity < 0.2:
                return self._prose("Executor", subtag, "All shipments are within acceptable risk. No anomaly to kill.")

            sid = worst["id"]
            self._active_shipment_id = sid

            # Step 2: FILTER — compare reroute options internally using ETA + CARRIER
            result = ops.optimize_eta(sid)
            if "error" in result:
                return self._prose("Executor", subtag,
                    f"Target acquired: #{sid} ({worst['origin']} to {worst['destination']}). "
                    f"But: {result['error']}",
                    thinking=True, models=["CASCADE_MODEL", "ETA_AGENT"])

            # Step 3: ACT — auto-apply the best option (option 1)
            apply_result = ops.apply_option(sid, 1)
            if "error" in apply_result:
                self._last_optimize_id = sid
                return self._prose("Executor", subtag,
                    f"Target: #{sid} ({worst['origin']} to {worst['destination']}). "
                    f"Could not auto-execute. Best available: {result['options'][0]['description']}. "
                    f"Say 'apply option 1' to force.",
                    thinking=True, models=["CASCADE_MODEL", "ETA_AGENT", "CARRIER_AGENT"])

            # Step 4: CONFIRM — state healed
            ops.add_learning("Executor", f"KILLSWITCH: auto-healed #{sid} via {apply_result['applied']}")
            return self._prose("Executor", subtag,
                f"Action complete. Shipment #{sid} ({worst['origin']} to {worst['destination']}) rerouted. "
                f"{apply_result['applied']}. ETA: {apply_result['old_eta']}h down to {apply_result['new_eta']}h. "
                f"Supply chain state healed.",
                thinking=True, models=["CASCADE_MODEL", "ETA_AGENT", "DELAY_AGENT", "CARRIER_AGENT"])

        # Fix a specific shipment by ID
        if ship_ids:
            sid = ship_ids[0]
            ship = next((s for s in ops.shipments if s["id"] == sid), None)
            if not ship:
                return self._prose("Executor", subtag, "That shipment does not exist.")
            if ship["status"] == "DELIVERED":
                return self._prose("Executor", subtag, f"Shipment #{sid} already delivered. Nothing to fix.")

            if "carrier" in clean_msg.lower() or "switch" in clean_msg.lower():
                result = ops.execute_command("SWITCH_CARRIER", {"shipment_id": sid, "carrier": "BlueDart"})
                if result.get("ok"):
                    ops.add_learning("Executor", f"Carrier switch #{sid}: {result['old_carrier']} to {result['new_carrier']}")
                    return self._prose("Executor", subtag,
                        f"Done. Shipment #{sid} carrier switched from {result['old_carrier']} to {result['new_carrier']}. State updated.",
                        thinking=True, models=["CARRIER_AGENT"])

            # Auto-optimize and execute best option
            result = ops.optimize_eta(sid)
            if "error" not in result:
                apply_result = ops.apply_option(sid, 1)
                if "error" not in apply_result:
                    ops.add_learning("Executor", f"Auto-fixed #{sid}: {apply_result['applied']}")
                    return self._prose("Executor", subtag,
                        f"Action complete. Shipment #{sid} rerouted: {apply_result['applied']}. "
                        f"ETA cut from {apply_result['old_eta']}h to {apply_result['new_eta']}h. State healed.",
                        thinking=True, models=["ETA_AGENT", "CARRIER_AGENT"])
                # Fallback: show options
                self._last_optimize_id = sid
                best = result['options'][0]
                return self._prose("Executor", subtag,
                    f"Shipment #{sid}: best option is {best['description']} (saves {best['eta_saved']}h). "
                    f"Say 'apply option 1' to execute.",
                    thinking=True, models=["ETA_AGENT"])

        # No target given and not a fix-all command
        return self._prose("Executor", subtag, "Say 'fix it' and I will find and kill the worst anomaly. Or specify: 'fix shipment 13'.")

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
    # THINKING PROCESS (internal monologue)
    # ========================================
    def _build_thinking(self, models: list) -> str:
        """Concise thinking tag for the frontend animation."""
        if not models:
            return ""
        tags = ", ".join(f"@{m}" for m in models)
        return f"[Consulting {tags}]"

    # ========================================
    # OUTPUT :: COGNITIVE FILTER
    # No raw ML scores. No markdown. Strategic conclusions only.
    # ========================================
    def _prose(self, agent: str, subtag: Optional[str], response, thinking=False, models=None) -> dict:
        if isinstance(response, dict):
            text = response.get("response", str(response))
        else:
            text = str(response)

        # COGNITIVE FILTER: strip raw score patterns
        text = text.replace("**", "").replace("##", "").replace("# ", "").replace("---", "")
        # Kill patterns like "(0.342)" or "probability: 0.87" in output
        text = re.sub(r'\(\d+\.\d{2,}\)', '', text)
        text = re.sub(r'probability[: ]+\d+\.\d+', '', text)
        text = re.sub(r'score[: ]+\d+\.\d+', '', text)
        text = re.sub(r'\s{2,}', ' ', text).strip()

        # Prepend thinking tag (concise)
        thinking_block = self._build_thinking(models or [])
        if thinking_block:
            text = f"{thinking_block}\n{text}"

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
