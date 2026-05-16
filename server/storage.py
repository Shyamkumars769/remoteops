import os
from collections.abc import Generator
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

from server.models import Agent, Task  # noqa: F401

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./db/db.sqlite")

if DATABASE_URL.startswith("sqlite:///"):
    db_path = DATABASE_URL.replace("sqlite:///", "", 1)
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
