from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from server.auth.security import hash_password
from server.config import settings
from server.logging import server_logger
from server.models.user import User
from server.routes import agents, auth, sessions, tasks
from server.storage import create_db_and_tables, engine

templates = Jinja2Templates(directory="server/templates")


def ensure_admin() -> None:
    with Session(engine) as session:
        existing = session.exec(select(User).where(User.username == settings.ADMIN_USERNAME)).first()
        if not existing:
            admin = User(
                username=settings.ADMIN_USERNAME,
                hashed_password=hash_password(settings.ADMIN_PASSWORD),
                role="admin",
            )
            session.add(admin)
            session.commit()
            server_logger.info("Bootstrap admin user created: %s", settings.ADMIN_USERNAME)


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    ensure_admin()
    server_logger.info("RemoteOps server started")
    yield
    server_logger.info("RemoteOps server stopped")


app = FastAPI(
    title="RemoteOps Full Access Platform",
    description="Industrial remote diagnostics + full interactive control",
    version="2.0.1",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(agents.router)
app.include_router(tasks.router)
app.include_router(sessions.router)


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/readyz")
def readyz():
    try:
        with Session(engine) as s:
            s.exec(select(User).limit(1)).first()
        return {"status": "ready"}
    except Exception as e:
        return {"status": "not_ready", "error": str(e)}


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/sessions", response_class=HTMLResponse)
def sessions_page(request: Request):
    return templates.TemplateResponse("sessions.html", {"request": request})


@app.get("/terminal/{session_id}", response_class=HTMLResponse)
def terminal_page(request: Request, session_id: str):
    return templates.TemplateResponse(
        "terminal.html",
        {"request": request, "session_id": session_id},
    )
