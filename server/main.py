from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import Depends, FastAPI, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from server.logging import server_logger
from server.models.agent import Agent
from server.models.task import Task
from server.routes import agents, tasks
from server.storage import create_db_and_tables, get_session

app = FastAPI(
    title="Remote Systems Management Platform",
    description="Minimal FastAPI backend for remote agent registration, task dispatch, and diagnostics results.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agents.router)
app.include_router(tasks.router)

templates = Jinja2Templates(directory="server/templates")


@app.on_event("startup")
def on_startup() -> None:
    create_db_and_tables()
    server_logger.info("Server started and database tables are ready")


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}


# ------------------------------------------------------------------ #
#  HOME — Registered Agents
# ------------------------------------------------------------------ #
@app.get("/", response_class=HTMLResponse)
def home(request: Request, session: Session = Depends(get_session)) -> HTMLResponse:
    all_agents = session.exec(select(Agent).order_by(Agent.created_at.desc())).all()
    cutoff     = datetime.now(timezone.utc) - timedelta(seconds=30)
    agent_rows = []

    for a in all_agents:
        try:
            last_seen = a.last_seen
            if isinstance(last_seen, str):
                last_seen = datetime.fromisoformat(last_seen)
            if last_seen and last_seen.tzinfo is None:
                last_seen = last_seen.replace(tzinfo=timezone.utc)
            online        = bool(last_seen and last_seen >= cutoff)
            last_seen_str = last_seen.strftime("%Y-%m-%d %H:%M:%S") if last_seen else "Never"
        except Exception:
            online        = False
            last_seen_str = "Never"

        agent_rows.append({
            "agent_id" : str(a.agent_id),
            "hostname" : str(a.hostname),
            "ip"       : str(a.ip) if a.ip else "N/A",
            "last_seen": last_seen_str,
            "online"   : online
        })

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"agents": agent_rows}
    )


# ------------------------------------------------------------------ #
#  SEND TASK — GET
# ------------------------------------------------------------------ #
@app.get("/send_task", response_class=HTMLResponse)
def send_task_page(request: Request, session: Session = Depends(get_session)) -> HTMLResponse:
    all_agents  = session.exec(select(Agent).order_by(Agent.hostname.asc())).all()
    agents_list = [
        {
            "agent_id": str(a.agent_id),
            "hostname": str(a.hostname)
        }
        for a in all_agents
    ]
    return templates.TemplateResponse(
        request=request,
        name="send_task.html",
        context={"agents": agents_list}
    )


# ------------------------------------------------------------------ #
#  SEND TASK — POST
# ------------------------------------------------------------------ #
@app.post("/send_task")
def create_task_from_form(
    agent_id  : str = Form(...),
    task_type : str = Form(...),
    command   : str = Form(""),
    path      : str = Form(""),
    pid       : str = Form(""),
    session   : Session = Depends(get_session),
) -> RedirectResponse:

    known_types = ["system_info", "list_processes"]

    payload: dict = {}
    if task_type == "run_command":
        payload = {"command": command}
    elif task_type == "list_files":
        payload = {"path": path or "."}
    elif task_type == "kill_process":
        payload = {"pid": int(pid) if pid.strip().isdigit() else 0}
    elif task_type not in known_types:
        # free form — use command if provided otherwise use task_type as command
        payload = {"command": command.strip() if command.strip() else task_type}

    task = Task(
        task_id  = str(uuid4()),
        agent_id = agent_id,
        type     = task_type,
        payload  = payload
    )
    session.add(task)
    session.commit()
    server_logger.info(
        "Created task from web form task_id=%s agent_id=%s type=%s",
        task.task_id, agent_id, task_type
    )
    return RedirectResponse(url="/send_task?created=1", status_code=303)


# ------------------------------------------------------------------ #
#  TASKS PAGE
# ------------------------------------------------------------------ #
@app.get("/tasks", response_class=HTMLResponse)
def tasks_page(request: Request, session: Session = Depends(get_session)) -> HTMLResponse:
    all_tasks = session.exec(select(Task).order_by(Task.created_at.desc())).all()
    task_rows = []

    for t in all_tasks:
        task_rows.append({
            "task_id"    : str(t.task_id),
            "agent_id"   : str(t.agent_id),
            "type"       : str(t.type),
            "status"     : str(t.status),
            "latency_ms" : t.latency_ms or 0,
            "created_at" : str(t.created_at)[:19] if t.created_at else "N/A",
            "finished_at": str(t.finished_at)[:19] if t.finished_at else "N/A",
            "result"     : t.result or {}
        })

    return templates.TemplateResponse(
        request=request,
        name="tasks.html",
        context={"tasks": task_rows}
    )