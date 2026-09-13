"""Interactive full-access session management + WebSocket bridge."""
from datetime import datetime, timezone
from typing import Dict
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlmodel import Session, select

from server.auth.deps import RequireOperator, RequireAdmin, RequireViewer
from server.auth.security import decode_token
from server.logging import sessions_logger
from server.models.agent import Agent
from server.models.session import InteractiveSession
from server.routes.agents import verify_agent_token
from server.storage import get_session, engine

router = APIRouter(prefix="/api", tags=["sessions"])

# In-memory live bridges: session_id -> {"operator": ws, "agent": ws}
LIVE: Dict[str, dict] = {}


class SessionCreate(BaseModel):
    agent_id: str


@router.post("/sessions")
def create_session(body: SessionCreate, user: RequireOperator, session: Session = Depends(get_session)):
    agent = session.exec(
        select(Agent).where(Agent.agent_id == body.agent_id, Agent.is_revoked == False)
    ).first()
    if not agent:
        raise HTTPException(status_code=404, detail="agent not found")

    sid = str(uuid4())
    row = InteractiveSession(
        session_id=sid,
        agent_id=body.agent_id,
        operator=user.username,
        status="pending",
    )
    session.add(row)
    session.commit()
    sessions_logger.info("Session created session_id=%s agent_id=%s by=%s", sid, body.agent_id, user.username)
    return {"session_id": sid, "status": "pending"}


@router.get("/sessions")
def list_sessions(user: RequireViewer, session: Session = Depends(get_session)):
    rows = session.exec(select(InteractiveSession).order_by(InteractiveSession.created_at.desc()).limit(200)).all()
    return [
        {
            "session_id": r.session_id,
            "agent_id": r.agent_id,
            "operator": r.operator,
            "status": r.status,
            "created_at": r.created_at,
            "started_at": r.started_at,
            "closed_at": r.closed_at,
        }
        for r in rows
    ]


@router.post("/sessions/{session_id}/close")
def close_session(session_id: str, user: RequireOperator, session: Session = Depends(get_session)):
    row = session.exec(select(InteractiveSession).where(InteractiveSession.session_id == session_id)).first()
    if not row:
        raise HTTPException(status_code=404, detail="session not found")
    row.status = "closed"
    row.closed_at = datetime.now(timezone.utc)
    session.add(row)
    session.commit()

    # Notify live sockets
    bridge = LIVE.pop(session_id, None)
    if bridge:
        for side in ("operator", "agent"):
            ws = bridge.get(side)
            if ws:
                try:
                    import asyncio
                    asyncio.create_task(ws.send_json({"type": "session_closed"}))
                except Exception:
                    pass
    sessions_logger.info("Session closed session_id=%s by=%s", session_id, user.username)
    return {"ok": True}


@router.get("/sessions/pending/{agent_id}")
def agent_pending_session(agent_id: str, token: str, session: Session = Depends(get_session)):
    """Agent polls for pending interactive sessions."""
    verify_agent_token(agent_id, token, session)
    row = session.exec(
        select(InteractiveSession)
        .where(
            InteractiveSession.agent_id == agent_id,
            InteractiveSession.status == "pending",
        )
        .order_by(InteractiveSession.created_at.asc())
    ).first()
    if not row:
        return {}
    return {"session_id": row.session_id}


# ---------- WebSocket endpoints ----------

async def _mark_active(session_id: str):
    with Session(engine) as s:
        row = s.exec(select(InteractiveSession).where(InteractiveSession.session_id == session_id)).first()
        if row and row.status == "pending":
            row.status = "active"
            row.started_at = datetime.now(timezone.utc)
            s.add(row)
            s.commit()


async def _mark_closed(session_id: str):
    with Session(engine) as s:
        row = s.exec(select(InteractiveSession).where(InteractiveSession.session_id == session_id)).first()
        if row and row.status != "closed":
            row.status = "closed"
            row.closed_at = datetime.now(timezone.utc)
            s.add(row)
            s.commit()
    LIVE.pop(session_id, None)


@router.websocket("/ws/session/operator/{session_id}")
async def ws_operator(websocket: WebSocket, session_id: str, token: str):
    """Operator connects with JWT access token as query param ?token=..."""
    payload = decode_token(token)
    if not payload or payload.type != "access":
        await websocket.close(code=4401)
        return
    if payload.role not in {"admin", "operator"}:
        await websocket.close(code=4403)
        return

    await websocket.accept()
    bridge = LIVE.setdefault(session_id, {})
    bridge["operator"] = websocket
    await _mark_active(session_id)
    sessions_logger.info("Operator joined session_id=%s user=%s", session_id, payload.sub)

    try:
        while True:
            data = await websocket.receive_json()
            # Forward to agent
            agent_ws = bridge.get("agent")
            if agent_ws:
                await agent_ws.send_json(data)
            else:
                await websocket.send_json({"type": "status", "message": "waiting_for_agent"})
    except WebSocketDisconnect:
        sessions_logger.info("Operator disconnected session_id=%s", session_id)
    finally:
        await _mark_closed(session_id)


@router.websocket("/ws/session/agent/{session_id}")
async def ws_agent(websocket: WebSocket, session_id: str, agent_id: str, token: str):
    """Agent connects with its agent token."""
    with Session(engine) as s:
        try:
            verify_agent_token(agent_id, token, s)
        except HTTPException:
            await websocket.close(code=4401)
            return
        row = s.exec(select(InteractiveSession).where(InteractiveSession.session_id == session_id)).first()
        if not row or row.agent_id != agent_id:
            await websocket.close(code=4404)
            return

    await websocket.accept()
    bridge = LIVE.setdefault(session_id, {})
    bridge["agent"] = websocket
    await _mark_active(session_id)
    sessions_logger.info("Agent joined session_id=%s agent_id=%s", session_id, agent_id)

    # Notify operator that agent is ready
    op_ws = bridge.get("operator")
    if op_ws:
        await op_ws.send_json({"type": "agent_ready"})

    try:
        while True:
            data = await websocket.receive_json()
            op_ws = bridge.get("operator")
            if op_ws:
                await op_ws.send_json(data)
    except WebSocketDisconnect:
        sessions_logger.info("Agent disconnected session_id=%s", session_id)
    finally:
        await _mark_closed(session_id)
