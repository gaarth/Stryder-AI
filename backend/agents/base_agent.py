"""
STRYDER AI - Base Agent
========================
Abstract base class for all STRYDER agents.
Provides Groq LLM integration, structured reasoning,
decision logging, and the Observe->Reason->Decide->Act->Learn lifecycle.
"""

import json
import time
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

try:
    from groq import Groq
    HAS_GROQ = True
except ImportError:
    HAS_GROQ = False

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from backend.config import GROQ_API_KEY, GROQ_MODEL


# ============================================================
# AGENT STATUS ENUM
# ============================================================
class AgentStatus:
    IDLE = "IDLE"
    OBSERVING = "OBSERVING"
    REASONING = "REASONING"
    DECIDING = "DECIDING"
    ACTING = "ACTING"
    LEARNING = "LEARNING"
    ERROR = "ERROR"


# ============================================================
# DECISION RECORD
# ============================================================
class Decision:
    """Structured record of an agent decision."""

    def __init__(self, agent_name: str, decision_type: str,
                 context: dict, reasoning: str, action: dict,
                 confidence: float, priority: int = 3):
        self.id = str(uuid.uuid4())[:8]
        self.timestamp = datetime.now().isoformat()
        self.agent_name = agent_name
        self.decision_type = decision_type
        self.context = context
        self.reasoning = reasoning
        self.action = action
        self.confidence = confidence
        self.priority = priority  # 1=critical, 5=routine
        self.outcome = None
        self.feedback = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "agent": self.agent_name,
            "type": self.decision_type,
            "context": self.context,
            "reasoning": self.reasoning,
            "action": self.action,
            "confidence": self.confidence,
            "priority": self.priority,
            "outcome": self.outcome,
            "feedback": self.feedback,
        }


# ============================================================
# BASE AGENT
# ============================================================
class BaseAgent(ABC):
    """
    Abstract base class for STRYDER AI agents.

    Every agent follows the lifecycle:
      Observe -> Reason -> Decide -> Act -> Learn

    Subclasses implement each phase. The base provides:
    - Groq LLM calls (llama-3.3-70b)
    - Decision logging
    - Status tracking
    - Memory (recent decisions + context)
    """

    def __init__(self, name: str, role: str, description: str,
                 avatar_emoji: str = "🤖", color: str = "#6366f1"):
        self.name = name
        self.role = role
        self.description = description
        self.avatar_emoji = avatar_emoji
        self.color = color

        # State
        self.status = AgentStatus.IDLE
        self.last_activity = None
        self.decision_count = 0
        self.errors = []

        # Memory
        self.memory: list[Decision] = []
        self.max_memory = 50
        self.context_window: dict = {}

        # Groq LLM client
        self._llm_client = None
        if HAS_GROQ and GROQ_API_KEY:
            self._llm_client = Groq(api_key=GROQ_API_KEY)

    # ========================================
    # LLM INTERFACE
    # ========================================
    def call_llm(self, system_prompt: str, user_prompt: str,
                 temperature: float = 0.3, max_tokens: int = 1024) -> str:
        """Call Groq LLM with structured prompt."""
        if not self._llm_client:
            return self._fallback_reasoning(user_prompt)

        try:
            response = self._llm_client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content
        except Exception as e:
            self.errors.append({"time": datetime.now().isoformat(), "error": str(e)})
            return self._fallback_reasoning(user_prompt)

    def call_llm_json(self, system_prompt: str, user_prompt: str,
                      temperature: float = 0.2, max_tokens: int = 1024) -> dict:
        """Call LLM expecting JSON response."""
        system_prompt += "\n\nYou MUST respond with valid JSON only. No markdown, no explanation, just JSON."
        raw = self.call_llm(system_prompt, user_prompt, temperature, max_tokens)

        # Try to extract JSON from response
        try:
            # Strip markdown code blocks if present
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1]
                cleaned = cleaned.rsplit("```", 1)[0]
            return json.loads(cleaned)
        except json.JSONDecodeError:
            # Try to find JSON object in response
            try:
                start = raw.index("{")
                end = raw.rindex("}") + 1
                return json.loads(raw[start:end])
            except (ValueError, json.JSONDecodeError):
                return {"raw_response": raw, "parse_error": True}

    def _fallback_reasoning(self, prompt: str) -> str:
        """Rule-based fallback when LLM is unavailable."""
        return f"[{self.name} FALLBACK] Analyzing: {prompt[:200]}..."

    # ========================================
    # LIFECYCLE: Observe -> Reason -> Decide -> Act -> Learn
    # ========================================
    @abstractmethod
    def observe(self, world_state: dict) -> dict:
        """
        OBSERVE: Scan world state for relevant signals.
        Returns dict of observations/anomalies detected.
        """
        pass

    @abstractmethod
    def reason(self, observations: dict) -> dict:
        """
        REASON: Analyze observations using LLM + models.
        Returns dict with analysis, risk assessment, options.
        """
        pass

    @abstractmethod
    def decide(self, analysis: dict) -> Decision:
        """
        DECIDE: Choose an action based on reasoning.
        Returns a Decision object.
        """
        pass

    @abstractmethod
    def act(self, decision: Decision) -> dict:
        """
        ACT: Execute the decided action.
        Returns dict with action result.
        """
        pass

    def learn(self, decision: Decision, outcome: dict) -> dict:
        """
        LEARN: Record outcome and update agent memory.
        Default implementation; can be overridden.
        """
        self.status = AgentStatus.LEARNING
        decision.outcome = outcome

        # Store in memory
        self.memory.append(decision)
        if len(self.memory) > self.max_memory:
            self.memory = self.memory[-self.max_memory:]

        self.decision_count += 1
        success = outcome.get("success", True)

        return {
            "agent": self.name,
            "decision_id": decision.id,
            "success": success,
            "total_decisions": self.decision_count,
            "memory_size": len(self.memory),
        }

    # ========================================
    # FULL LOOP
    # ========================================
    def run_loop(self, world_state: dict) -> dict:
        """
        Execute the full Observe -> Reason -> Decide -> Act -> Learn loop.
        Returns a complete trace of the loop execution.
        """
        loop_id = str(uuid.uuid4())[:8]
        start_time = time.time()
        trace = {
            "loop_id": loop_id,
            "agent": self.name,
            "started": datetime.now().isoformat(),
            "phases": {},
        }

        try:
            # 1. OBSERVE
            self.status = AgentStatus.OBSERVING
            observations = self.observe(world_state)
            trace["phases"]["observe"] = observations

            # 2. REASON
            self.status = AgentStatus.REASONING
            analysis = self.reason(observations)
            trace["phases"]["reason"] = analysis

            # 3. DECIDE
            self.status = AgentStatus.DECIDING
            decision = self.decide(analysis)
            trace["phases"]["decide"] = decision.to_dict()

            # 4. ACT
            self.status = AgentStatus.ACTING
            result = self.act(decision)
            trace["phases"]["act"] = result

            # 5. LEARN
            learn_result = self.learn(decision, result)
            trace["phases"]["learn"] = learn_result

            trace["success"] = True
        except Exception as e:
            self.status = AgentStatus.ERROR
            self.errors.append({"time": datetime.now().isoformat(), "error": str(e)})
            trace["success"] = False
            trace["error"] = str(e)

        self.status = AgentStatus.IDLE
        self.last_activity = datetime.now().isoformat()
        trace["duration_ms"] = round((time.time() - start_time) * 1000, 1)
        trace["finished"] = datetime.now().isoformat()

        return trace

    # ========================================
    # CHAT INTERFACE
    # ========================================
    def handle_chat(self, message: str, context: Optional[dict] = None) -> str:
        """Handle a direct @tag chat message from the user."""
        system = f"""You are {self.name}, the {self.role} in STRYDER AI logistics platform.
Your specialty: {self.description}

Recent decisions: {json.dumps([d.to_dict() for d in self.memory[-3:]], default=str)}

Respond helpfully, concisely, and in character. Use logistics terminology.
If asked about data, provide specific numbers when possible."""

        user_msg = message
        if context:
            user_msg += f"\n\nCurrent context: {json.dumps(context, default=str)}"

        return self.call_llm(system, user_msg, temperature=0.5, max_tokens=512)

    # ========================================
    # STATUS / INFO
    # ========================================
    def get_status(self) -> dict:
        """Get agent status for dashboard display."""
        return {
            "name": self.name,
            "role": self.role,
            "description": self.description,
            "avatar_emoji": self.avatar_emoji,
            "color": self.color,
            "status": self.status,
            "last_activity": self.last_activity,
            "decision_count": self.decision_count,
            "memory_size": len(self.memory),
            "recent_errors": self.errors[-3:] if self.errors else [],
        }
