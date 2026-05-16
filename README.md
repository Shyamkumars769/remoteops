# Remote Systems Management and Diagnostics Platform

A minimal Python platform for registering remote agents, dispatching diagnostic tasks, collecting results, and viewing activity through an API, CLI, or simple Jinja web UI.

## What It Includes

- FastAPI backend with SQLite persistence via SQLModel.
- Remote polling agent that registers, receives work, executes supported tasks, and posts results.
- Operator CLI for listing agents and creating tasks.
- Simple server-rendered UI for viewing agents and sending tasks.
- Runtime logging to `logs/agent.log` and `logs/server.log`.
- Docker and Docker Compose setup.
- Sample logs and result JSON for portfolio demos.

## Project Layout

```text
agent/      Remote agent and task execution modules
server/     FastAPI backend, SQLModel storage, routes, templates
cli/        Operator CLI
web/        Thin optional web entrypoint
docs/       Sample logs and sample task results
logs/       Runtime log directory
db/         SQLite database directory
```

## Supported Task Types

- `system_info`: OS, hostname, CPU, memory, and network interface summary.
- `run_command`: Executes a shell command with timeout and captures stdout/stderr/return code.
- `list_files`: Lists names and directory flags for one directory.
- `kill_process`: Attempts to terminate a process by PID.
- `list_processes`: Available in the agent and API task creation, useful as a small extension.

## Local Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Start the server:

```bash
uvicorn server.main:app --reload --host 0.0.0.0 --port 8000
```

Start an agent in a second terminal:

```bash
python -m agent.agent
```

Open the web UI:

```text
http://localhost:8000
```

API docs are available at:

```text
http://localhost:8000/docs
```

## CLI Examples

List registered agents:

```bash
python -m cli.cli list-agents
```

Create a system information task:

```bash
python -m cli.cli system-info <agent_id> --wait
```

Run a command:

```bash
python -m cli.cli run-command <agent_id> whoami --wait
```

List files:

```bash
python -m cli.cli list-files <agent_id> . --wait
```

Kill a process:

```bash
python -m cli.cli kill-process <agent_id> 1234 --wait
```

## Docker

Build and run:

```bash
docker build -t remote-platform .
docker run -p 8000:8000 -v ./db:/app/db -v ./logs:/app/logs remote-platform
```

Or use Compose:

```bash
docker compose up --build
```

## Environment Variables

Agent:

- `SERVER_URL`, default `http://localhost:8000`
- `AGENT_HOSTNAME`, default current hostname

Server:

- `DATABASE_URL`, default `sqlite:///./db/db.sqlite`

## Security Notes

This is intentionally minimal and demo-oriented. Before using it outside a local lab, add operator authentication, encrypted transport, stricter task authorization, command allowlists, rate limits, audit retention, and a more robust agent identity lifecycle.
