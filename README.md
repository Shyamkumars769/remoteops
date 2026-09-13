# RemoteOps Full Access Platform v2

Industrial-style remote systems management **plus unrestricted interactive control**.

## Features

### Agent Registration & Task System
- Agent registration with enrollment key + token authentication
- Task types: `system_info`, `run_command` (unrestricted shell), `list_files`, `list_processes`, `kill_process`
- Free-form shell commands
- Task audit fields, cancellation, timeouts, result size limits
- Persistent agent identity on disk with backoff on network errors

### Operator Authentication
- JWT auth with roles: `admin` / `operator` / `viewer`
- Access + refresh tokens
- User management (admin-only)

### Interactive Full Access
- Open a live session on any agent
- Real PTY shell (Unix) or subprocess shell (Windows) — type anything, it runs on the remote machine
- File browser: list, download, upload, delete
- Session bridge over WebSocket
- Browser terminal (xterm.js)
- Session list + force close

### Infrastructure
- FastAPI backend with SQLite persistence (SQLModel)
- Web UI (Jinja2 templates, dark theme)
- CLI operator tool
- Docker + Docker Compose support
- Health/readiness endpoints (`/healthz`, `/readyz`)
- Configurable CORS via environment variables

---

## Project Layout

```
remoteops/
├── agent/               Core agent code (polling, task execution, sessions)
│   ├── agent.py         Main agent loop (register, poll, execute, report)
│   ├── config.py        Agent configuration from environment
│   ├── logging.py       Logging setup
│   ├── session_handler.py  PTY shell + file operations for interactive sessions
│   └── modules/
│       ├── executor.py      Shell command execution
│       ├── filesystem.py    Directory listing, file read
│       ├── process.py       Process listing, kill (psutil)
│       └── system_info.py   OS, CPU, memory, disk, network info
│
├── server/              FastAPI backend
│   ├── main.py          App entrypoint, lifespan, routes, health endpoints
│   ├── config.py        Settings from environment/.env
│   ├── storage.py       SQLModel engine + session factory
│   ├── logging.py       Server loggers
│   ├── auth/            JWT + password utilities, FastAPI dependencies
│   │   ├── security.py  bcrypt hashing, JWT create/decode
│   │   └── deps.py      Role-based auth dependencies
│   ├── models/          SQLModel table definitions
│   │   ├── user.py      User (admin/operator/viewer)
│   │   ├── agent.py     Agent (registration, token, revocation)
│   │   ├── task.py      Task (create, dispatch, result, audit)
│   │   └── session.py   InteractiveSession (pending/active/closed)
│   ├── routes/          API route handlers
│   │   ├── auth.py      Login, refresh, user management
│   │   ├── agents.py    Register, list, revoke agents
│   │   ├── tasks.py     Create, poll, cancel, submit results
│   │   └── sessions.py  Interactive sessions + WebSocket bridge
│   └── templates/       Jinja2 HTML templates
│       ├── base.html    Dark-themed base layout
│       ├── index.html   Agents list + "Open Session" button
│       ├── login.html   Login form
│       ├── sessions.html  Session list
│       └── terminal.html  xterm.js terminal + file browser
│
├── cli/                 Operator CLI tool
│   └── cli.py           List agents, create tasks, login, sessions
│
├── windows-agent/       Standalone deployable agent for remote PCs
│   ├── agent/           Same agent code as core (for standalone deployment)
│   ├── CONFIG.txt       Server URL + enrollment key (edit before setup)
│   ├── SETUP.bat        One-click venv + dependency setup
│   ├── START-AGENT.bat  Launch agent (run every time)
│   ├── BUILD-EXE.bat    Build standalone .exe with PyInstaller
│   └── README.txt       Quick deployment instructions
│
├── db/                  SQLite database (created at runtime)
├── logs/                Runtime logs (agent.log, server.log)
├── docs/                Documentation / sample data
├── scripts/             Utility scripts
├── .env.example         Environment variable template
├── .gitignore           Git ignore rules
├── Dockerfile           Container image definition
├── docker-compose.yml   Compose service definition
└── requirements.txt     Python dependencies
```

---

## Prerequisites

- **Python 3.9+** (3.11+ recommended)
- **pip** (comes with Python)
- **Git** (for cloning)
- **PyInstaller** (optional, only for building standalone .exe)

---

## Quick Start (Local Development)

### 1. Clone the repository

```bash
git clone https://github.com/Shyamkumars769/remoteops.git
cd remoteops
```

### 2. Create a virtual environment and install dependencies

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and set at minimum:

```ini
SECRET_KEY=<any-long-random-string>
ENROLLMENT_KEY=<any-secret-key-for-agent-registration>
ADMIN_PASSWORD=<your-secure-password>
```

> **Important:** Change `SECRET_KEY`, `ENROLLMENT_KEY`, and `ADMIN_PASSWORD` before any real use.

### 4. Start the server

```bash
uvicorn server.main:app --reload --host 0.0.0.0 --port 8000
```

The server creates the SQLite database and bootstraps an admin user on first start.

### 5. Start an agent (on the same machine)

In a **second terminal** (with the venv activated):

```bash
export SERVER_URL=http://localhost:8000
export ENROLLMENT_KEY=<same-key-from-.env>
python -m agent.agent
```

On Windows (cmd):
```cmd
set SERVER_URL=http://localhost:8000
set ENROLLMENT_KEY=<same-key-from-.env>
python -m agent.agent
```

### 6. Open the web UI

Navigate to: **http://localhost:8000**

- **Login:** `admin` / `<your ADMIN_PASSWORD from .env>`
- The Agents page shows all registered agents
- Click **Open Session** on any agent to get a live terminal + file browser

### 7. API documentation

Interactive API docs available at: **http://localhost:8000/docs**

---

## Deploying Agent on Another PC (Windows)

The `windows-agent/` folder is a self-contained package for deploying agents on remote Windows machines.

### Server PC Setup

1. Find your server's local IP:
   ```cmd
   ipconfig
   ```
   Look for the IPv4 address (e.g., `192.168.1.42`).

2. Allow port 8000 through Windows Firewall:
   ```cmd
   netsh advfirewall firewall add rule name="RemoteOps" dir=in action=allow protocol=TCP localport=8000
   ```

3. Keep the server running (`uvicorn server.main:app ...`).

### Remote PC Setup

1. **Copy** the entire `windows-agent/` folder to the remote PC.

2. **Edit `CONFIG.txt`** with your server's IP and enrollment key:
   ```
   SERVER_URL=http://192.168.1.42:8000
   ENROLLMENT_KEY=change-me-enrollment-key
   ```
   > `ENROLLMENT_KEY` must match the server's `.env` `ENROLLMENT_KEY` value.

3. **Double-click `SETUP.bat`** (run once). This will:
   - Check Python is installed
   - Create a virtual environment
   - Install required packages (requests, psutil, websockets, etc.)
   - Test connection to the server

4. **Double-click `START-AGENT.bat`** (every time you want the agent to connect).

The agent will appear on the server's Agents page. Open a Session for full control.

### Building a Standalone .exe (Optional)

On the remote PC, double-click `BUILD-EXE.bat` to create `dist/remoteops-agent.exe` — a single-file executable that doesn't need Python installed.

---

## CLI Usage

With the server running and venv activated:

```bash
# Login (stores token locally)
python -m cli.cli login admin <password>

# List registered agents
python -m cli.cli list-agents

# Get system info from an agent
python -m cli.cli system-info <agent_id> --wait

# Run a command on an agent
python -m cli.cli run-command <agent_id> whoami --wait

# List files on an agent
python -m cli.cli list-files <agent_id> . --wait

# Kill a process on an agent
python -m cli.cli kill-process <agent_id> 1234 --wait
```

---

## Docker

### Build and run with Docker Compose

```bash
docker compose up --build
```

### Or build manually

```bash
docker build -t remoteops .
docker run -p 8000:8000 -v ./db:/app/db -v ./logs:/app/logs remoteops
```

> Agents still run on target hosts (not inside the server container by default).

---

## Environment Variables

### Server

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | `dev-secret-change-me-in-production` | JWT signing secret |
| `DATABASE_URL` | `sqlite:///./db/db.sqlite` | Database connection string |
| `ENROLLMENT_KEY` | `dev-enrollment-key` | Key agents must provide to register |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | JWT access token lifetime |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | JWT refresh token lifetime |
| `CORS_ORIGINS` | `http://localhost:8000,http://127.0.0.1:8000` | Comma-separated allowed origins |
| `LOG_LEVEL` | `INFO` | Logging level |
| `ADMIN_USERNAME` | `admin` | Default admin username (created on first start) |
| `ADMIN_PASSWORD` | `admin123` | Default admin password |
| `MAX_RESULT_BYTES` | `2000000` | Max task result size in bytes |
| `SESSION_IDLE_TIMEOUT` | `1800` | Session idle timeout in seconds |

### Agent

| Variable | Default | Description |
|---|---|---|
| `SERVER_URL` | `http://localhost:8000` | Server URL to connect to |
| `AGENT_HOSTNAME` | *(system hostname)* | Override reported hostname |
| `ENROLLMENT_KEY` | `dev-enrollment-key` | Must match server's enrollment key |
| `POLL_INTERVAL` | `5` | Seconds between task polls |
| `SESSION_ENABLED` | `true` | Enable interactive session support |

---

## Supported Task Types

| Type | Description | Payload |
|---|---|---|
| `system_info` | OS, CPU, memory, disk, network info | `{}` |
| `run_command` | Execute shell command with timeout | `{"command": "whoami", "timeout": 30}` |
| `list_files` | List directory contents | `{"path": "/tmp"}` |
| `list_processes` | List running processes | `{}` |
| `kill_process` | Terminate process by PID | `{"pid": 1234}` |
| *(free-form)* | Any unknown type runs as shell command | `{"command": "..."}` |

---

## API Endpoints

### Authentication
| Method | Path | Description |
|---|---|---|
| POST | `/api/auth/login` | Login (form-encoded username/password) |
| POST | `/api/auth/refresh` | Refresh access token |
| GET | `/api/auth/me` | Get current user info |
| POST | `/api/auth/users` | Create user (admin only) |

### Agents
| Method | Path | Description |
|---|---|---|
| POST | `/api/register` | Register new agent (enrollment key required) |
| GET | `/api/agents` | List all active agents (viewer+) |
| DELETE | `/api/agents/{agent_id}` | Revoke agent (admin only) |

### Tasks
| Method | Path | Description |
|---|---|---|
| POST | `/api/tasks` | Create task (operator+) |
| GET | `/api/tasks` | List recent tasks (viewer+) |
| GET | `/api/tasks/{agent_id}` | Agent polls for next task |
| POST | `/api/results` | Agent submits task result |
| POST | `/api/tasks/{task_id}/cancel` | Cancel task (operator+) |

### Sessions
| Method | Path | Description |
|---|---|---|
| POST | `/api/sessions` | Create interactive session (operator+) |
| GET | `/api/sessions` | List sessions (viewer+) |
| POST | `/api/sessions/{session_id}/close` | Close session (operator+) |
| GET | `/api/sessions/pending/{agent_id}` | Agent polls for pending sessions |
| WS | `/api/ws/session/operator/{session_id}` | Operator WebSocket bridge |
| WS | `/api/ws/session/agent/{session_id}` | Agent WebSocket bridge |

### Health
| Method | Path | Description |
|---|---|---|
| GET | `/healthz` | Health check |
| GET | `/readyz` | Readiness check (verifies DB) |

---

## Security Notes

This platform is designed for **lab / internal admin / authorized red-team** use.

- Unrestricted shell and file access are **intentional**.
- **Use TLS** in production — protect the server with a reverse proxy (nginx, Caddy).
- **Change all default secrets** before any deployment.
- Restrict who has `operator` / `admin` roles.
- Only enroll agents you control.
- Session activity should be treated as **highly privileged**.

---

## Version

**2.0.1** — Full interactive access + industrial auth baseline.
