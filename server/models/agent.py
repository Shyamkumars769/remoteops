from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Agent(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    agent_id: str = Field(unique=True, index=True)
    hostname: str
    ip: Optional[str] = None
    token: str
    last_seen: datetime = Field(default_factory=utcnow)
    created_at: datetime = Field(default_factory=utcnow)
