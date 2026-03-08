"""
STRYDER AI - Chat Router
==========================
Agent chat endpoints with @tag routing, ML inference, and thinking signals.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from backend.agents.orchestrator import get_orchestrator

router = APIRouter(prefix="/api/chat", tags=["Chat"])


class ChatMessage(BaseModel):
    message: str
    context: Optional[dict] = None


class ChatResponse(BaseModel):
    agent: str
    subtag: Optional[str] = None
    response: str
    timestamp: str
    thinking: bool = False
    models_used: list[str] = []


@router.post("/send", response_model=ChatResponse)
async def send_message(msg: ChatMessage):
    """Send a message to agents. Use @AgentName to target specific agents."""
    orch = get_orchestrator()
    result = orch.route_message(msg.message, msg.context)
    return ChatResponse(**result)


@router.get("/agents")
async def list_agents():
    """List all available agents and their current status."""
    orch = get_orchestrator()
    return {"agents": orch.get_all_statuses()}
