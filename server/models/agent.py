from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Agent(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    agent_id: str = Field(unique=True, index=True)
    hostname: str = Field(index=True)
    ip: Optional[str] = None
    token: str = Field(index=True)
    version: Optional[str] = None
    tags: Optional[str] = None  # comma-separated
    last_seen: Optional[datetime] = None
    created_at: datetime = Field(default_factory=utcnow)
    is_revoked: bool = Field(default=False)
