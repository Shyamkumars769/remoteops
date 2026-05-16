from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field as PydanticField
from sqlmodel import Session, select

from server.logging import tasks_logger
from server.models.agent import Agent
from server.models.task import Task
from server.storage import get_session

router = APIRouter(prefix="/api", tags=["tasks"])


class TaskCreateRequest(BaseModel):
    agent_id: str
    type: str
    payload: dict[str, Any] = PydanticField(default_factory=dict)


class ResultRequest(BaseModel):
    task_id: str
    agent_id: str
    status: str
    type: Optional[str] = None
    latency_ms: Optional[int] = None
    result: dict[str, Any] = PydanticField(default_factory=dict)


def _find_agent(session: Session, agent_id: str) -> Agent | None:
    return session.exec(select(Agent).where(Agent.agent_id == agent_id)).first()


@router.post("/tasks")
def create_task(payload: TaskCreateRequest, session: Session = Depends(get_session)) -> dict:
    if not _find_agent(session, payload.agent_id):
        raise HTTPException(status_code=404, detail="agent not found")

    task = Task(
        task_id  = str(uuid4()),
        agent_id = payload.agent_id,
        type     = payload.type,
        payload  = payload.payload,
        status   = "pending",
    )
    session.add(task)
    session.commit()
    session.refresh(task)
    tasks_logger.info("Created task_id=%s agent_id=%s type=%s", task.task_id, task.agent_id, task.type)
    return {"task_id": task.task_id, "status": task.status}


@router.post("/results")
def save_result(payload: ResultRequest, session: Session = Depends(get_session)) -> dict:
    task = session.exec(select(Task).where(Task.task_id == payload.task_id)).first()
    if not task:
        tasks_logger.warning("Result for unknown task_id=%s", payload.task_id)
        raise HTTPException(status_code=404, detail="task not found")
    if task.agent_id != payload.agent_id:
        tasks_logger.warning("Result agent mismatch task_id=%s agent_id=%s", payload.task_id, payload.agent_id)
        raise HTTPException(status_code=403, detail="agent does not own task")

    task.result      = payload.result
    task.status      = "completed" if payload.status == "success" else "failed"
    task.finished_at = datetime.now(timezone.utc)
    task.latency_ms  = payload.latency_ms or payload.result.get("latency_ms")
    session.add(task)
    session.commit()
    tasks_logger.info("Saved result task_id=%s status=%s", task.task_id, task.status)
    return {"ok": True}


@router.get("/tasks")
def list_tasks(session: Session = Depends(get_session)) -> list[dict]:
    tasks = session.exec(select(Task).order_by(Task.created_at.desc())).all()
    return [
        {
            "task_id"    : task.task_id,
            "agent_id"   : task.agent_id,
            "type"       : task.type,
            "status"     : task.status,
            "latency_ms" : task.latency_ms,
            "created_at" : task.created_at,
            "started_at" : task.started_at,
            "finished_at": task.finished_at,
            "result"     : task.result,
        }
        for task in tasks
    ]


@router.delete("/tasks/{task_id}")
def delete_task(task_id: str, session: Session = Depends(get_session)):
    task = session.exec(select(Task).where(Task.task_id == task_id)).first()
    if not task:
        raise HTTPException(status_code=404, detail="task not found")
    session.delete(task)
    session.commit()
    tasks_logger.info("Deleted task_id=%s", task_id)
    return {"ok": True}


@router.get("/tasks/{agent_id}")
def get_next_task(agent_id: str, token: str, session: Session = Depends(get_session)) -> dict:
    agent = _find_agent(session, agent_id)
    if not agent or agent.token != token:
        tasks_logger.warning("Unauthorized task poll agent_id=%s", agent_id)
        raise HTTPException(status_code=401, detail="invalid agent token")

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

    task.status = "in_progress"
    task.started_at = datetime.now(timezone.utc)
    session.add(agent)
    session.add(task)
    session.commit()
    tasks_logger.info("Dispatched task_id=%s agent_id=%s type=%s", task.task_id, agent_id, task.type)
    return {"task_id": task.task_id, "type": task.type, "payload": task.payload}