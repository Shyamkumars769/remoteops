from datetime import datetime, timezone
from secrets import token_urlsafe
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlmodel import Session, select

from server.logging import agents_logger
from server.models.agent import Agent
from server.storage import get_session

router = APIRouter(prefix="/api", tags=["agents"])


class RegisterRequest(BaseModel):
    hostname: str
    ip: Optional[str] = None


@router.post("/register")
def register_agent(payload: RegisterRequest, request: Request, session: Session = Depends(get_session)) -> dict:
    hostname = payload.hostname.strip()
    if not hostname:
        agents_logger.warning("Rejected registration with empty hostname")
        raise HTTPException(status_code=400, detail="hostname is required")

    agent = Agent(
        agent_id=str(uuid4()),
        hostname=hostname,
        ip=payload.ip or request.client.host if request.client else payload.ip,
        token=token_urlsafe(32),
        last_seen=datetime.now(timezone.utc),
    )
    session.add(agent)
    session.commit()
    session.refresh(agent)
    agents_logger.info("Registered agent_id=%s hostname=%s ip=%s", agent.agent_id, agent.hostname, agent.ip)
    return {"agent_id": agent.agent_id, "token": agent.token}


@router.get("/agents")
def list_agents(session: Session = Depends(get_session)) -> list[dict]:
    agents = session.exec(select(Agent).order_by(Agent.created_at.desc())).all()
    return [
        {
            "id": agent.id,
            "agent_id": agent.agent_id,
            "hostname": agent.hostname,
            "ip": agent.ip,
            "last_seen": agent.last_seen,
            "created_at": agent.created_at,
        }
        for agent in agents
    ]


@router.delete("/agents/{agent_id}")
def delete_agent(agent_id: str, session: Session = Depends(get_session)):
    agent = session.exec(select(Agent).where(Agent.agent_id == agent_id)).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    session.delete(agent)
    session.commit()
    agents_logger.info("Deleted agent_id=%s", agent_id)
    return {"ok": True}