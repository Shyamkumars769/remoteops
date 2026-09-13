from datetime import datetime, timezone
from secrets import token_urlsafe
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel
from sqlmodel import Session, select

from server.auth.deps import RequireAdmin, RequireOperator, RequireViewer
from server.config import settings
from server.logging import agents_logger
from server.models.agent import Agent
from server.storage import get_session

router = APIRouter(prefix="/api", tags=["agents"])


class RegisterRequest(BaseModel):
    hostname: str
    ip: Optional[str] = None
    version: Optional[str] = None
    enrollment_key: str


@router.post("/register")
def register_agent(
    payload: RegisterRequest,
    request: Request,
    session: Session = Depends(get_session),
):
    if payload.enrollment_key != settings.ENROLLMENT_KEY:
        agents_logger.warning("Rejected registration: bad enrollment key hostname=%s", payload.hostname)
        raise HTTPException(status_code=403, detail="Invalid enrollment key")

    hostname = payload.hostname.strip()
    if not hostname:
        raise HTTPException(status_code=400, detail="hostname required")

    agent = Agent(
        agent_id=str(uuid4()),
        hostname=hostname,
        ip=payload.ip or (request.client.host if request.client else None),
        token=token_urlsafe(32),
        version=payload.version,
        last_seen=datetime.now(timezone.utc),
    )
    session.add(agent)
    session.commit()
    session.refresh(agent)
    agents_logger.info("Registered agent_id=%s hostname=%s", agent.agent_id, agent.hostname)
    return {"agent_id": agent.agent_id, "token": agent.token}


@router.get("/agents")
def list_agents(user: RequireViewer, session: Session = Depends(get_session)):
    agents = session.exec(select(Agent).where(Agent.is_revoked == False).order_by(Agent.created_at.desc())).all()
    return [
        {
            "agent_id": a.agent_id,
            "hostname": a.hostname,
            "ip": a.ip,
            "version": a.version,
            "tags": a.tags,
            "last_seen": a.last_seen,
            "created_at": a.created_at,
        }
        for a in agents
    ]


@router.delete("/agents/{agent_id}")
def delete_agent(agent_id: str, user: RequireAdmin, session: Session = Depends(get_session)):
    agent = session.exec(select(Agent).where(Agent.agent_id == agent_id)).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    agent.is_revoked = True
    session.add(agent)
    session.commit()
    agents_logger.info("Revoked agent_id=%s by=%s", agent_id, user.username)
    return {"ok": True}


def verify_agent_token(agent_id: str, token: str, session: Session) -> Agent:
    agent = session.exec(select(Agent).where(Agent.agent_id == agent_id)).first()
    if not agent or agent.is_revoked or agent.token != token:
        raise HTTPException(status_code=401, detail="Invalid agent token")
    return agent
