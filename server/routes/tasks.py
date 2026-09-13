from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field as PydanticField
from sqlmodel import Session, select

from server.auth.deps import RequireOperator, RequireViewer
from server.config import settings
from server.logging import tasks_logger
from server.models.agent import Agent
from server.models.task import Task
from server.routes.agents import verify_agent_token
from server.storage import get_session

router = APIRouter(prefix="/api", tags=["tasks"])


class TaskCreateRequest(BaseModel):
    agent_id: str
    type: str
    payload: dict[str, Any] = PydanticField(default_factory=dict)
    timeout_seconds: int = 300
    idempotency_key: Optional[str] = None


class ResultRequest(BaseModel):
    task_id: str
    agent_id: str
    status: str
    type: Optional[str] = None
    latency_ms: Optional[int] = None
    result: dict[str, Any] = PydanticField(default_factory=dict)


def _find_agent(session: Session, agent_id: str) -> Agent | None:
    return session.exec(select(Agent).where(Agent.agent_id == agent_id, Agent.is_revoked == False)).first()


@router.post("/tasks")
def create_task(
    payload: TaskCreateRequest,
    request: Request,
    user: RequireOperator,
    session: Session = Depends(get_session),
):
    if not _find_agent(session, payload.agent_id):
        raise HTTPException(status_code=404, detail="agent not found")

    if payload.idempotency_key:
        existing = session.exec(
            select(Task).where(Task.idempotency_key == payload.idempotency_key)
        ).first()
        if existing:
            return {"task_id": existing.task_id, "status": existing.status}

    task = Task(
        task_id=str(uuid4()),
        agent_id=payload.agent_id,
        type=payload.type,
        payload=payload.payload,
        status="pending",
        created_by=user.username,
        source_ip=request.client.host if request.client else None,
        idempotency_key=payload.idempotency_key,
        timeout_seconds=payload.timeout_seconds,
    )
    session.add(task)
    session.commit()
    session.refresh(task)
    tasks_logger.info(
        "Created task_id=%s agent_id=%s type=%s by=%s",
        task.task_id, task.agent_id, task.type, user.username,
    )
    return {"task_id": task.task_id, "status": task.status}


@router.post("/results")
def save_result(payload: ResultRequest, session: Session = Depends(get_session)):
    # Agent-authenticated path: token checked via query in production; simplified here by agent_id match
    task = session.exec(select(Task).where(Task.task_id == payload.task_id)).first()
    if not task:
        raise HTTPException(status_code=404, detail="task not found")
    if task.agent_id != payload.agent_id:
        raise HTTPException(status_code=403, detail="agent does not own task")

    # Truncate large results
    result = payload.result or {}
    raw = str(result)
    if len(raw) > settings.MAX_RESULT_BYTES:
        result = {"truncated": True, "preview": raw[: settings.MAX_RESULT_BYTES // 2]}

    task.result = result
    task.status = "completed" if payload.status == "success" else "failed"
    task.finished_at = datetime.now(timezone.utc)
    task.latency_ms = payload.latency_ms or result.get("latency_ms")
    session.add(task)
    session.commit()
    tasks_logger.info("Saved result task_id=%s status=%s", task.task_id, task.status)
    return {"ok": True}


@router.get("/tasks")
def list_tasks(user: RequireViewer, session: Session = Depends(get_session)):
    tasks = session.exec(select(Task).order_by(Task.created_at.desc()).limit(500)).all()
    return [
        {
            "task_id": t.task_id,
            "agent_id": t.agent_id,
            "type": t.type,
            "status": t.status,
            "latency_ms": t.latency_ms,
            "created_at": t.created_at,
            "started_at": t.started_at,
            "finished_at": t.finished_at,
            "created_by": t.created_by,
            "result": t.result,
        }
        for t in tasks
    ]


@router.get("/tasks/{agent_id}")
def get_next_task(agent_id: str, token: str, session: Session = Depends(get_session)):
    agent = verify_agent_token(agent_id, token, session)
    agent.last_seen = datetime.now(timezone.utc)

    task = session.exec(
        select(Task)
        .where(Task.agent_id == agent_id, Task.status == "pending")
        .order_by(Task.created_at.asc())
    ).first()

    if not task:
        session.add(agent)
        session.commit()
        return {}

    task.status = "running"
    task.started_at = datetime.now(timezone.utc)
    session.add(agent)
    session.add(task)
    session.commit()
    tasks_logger.info("Dispatched task_id=%s agent_id=%s type=%s", task.task_id, agent_id, task.type)
    return {
        "task_id": task.task_id,
        "type": task.type,
        "payload": task.payload,
        "timeout_seconds": task.timeout_seconds,
    }


@router.post("/tasks/{task_id}/cancel")
def cancel_task(task_id: str, user: RequireOperator, session: Session = Depends(get_session)):
    task = session.exec(select(Task).where(Task.task_id == task_id)).first()
    if not task:
        raise HTTPException(status_code=404, detail="task not found")
    if task.status not in {"pending", "running"}:
        raise HTTPException(status_code=400, detail="task not cancellable")
    task.status = "cancelled"
    task.finished_at = datetime.now(timezone.utc)
    session.add(task)
    session.commit()
    return {"ok": True}
