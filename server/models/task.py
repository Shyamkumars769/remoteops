from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import Column
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Task(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    task_id: str = Field(unique=True, index=True)
    agent_id: str = Field(index=True)
    type: str
    payload: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    status: str = Field(default="pending", index=True)
    created_at: datetime = Field(default_factory=utcnow)
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    result: Optional[dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    latency_ms: Optional[int] = None
    created_by: Optional[str] = None
    source_ip: Optional[str] = None
    idempotency_key: Optional[str] = Field(default=None, index=True)
    timeout_seconds: int = Field(default=300)
