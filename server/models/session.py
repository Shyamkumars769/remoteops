from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class InteractiveSession(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str = Field(unique=True, index=True)
    agent_id: str = Field(index=True)
    operator: str = Field(index=True)
    status: str = Field(default="pending", index=True)  # pending | active | closed
    created_at: datetime = Field(default_factory=utcnow)
    started_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    recording_path: Optional[str] = None
