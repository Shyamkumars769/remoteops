# RemoteOps Full Access Platform

Remote systems management **plus full interactive control**.

One machine runs the **server** (web UI + API).  
Other machines run the **agent** and connect to that server.

From the web UI you can:
- Run tasks (`system_info`, shell commands, files, processes)
- Open a **live interactive session** (real shell + file browser) on any online agent

---

## What is in this repository

GitHub contains one package:

```text
remoteops server&agent.zip
├── remoteops-server.zip    → full server project (extract on the server PC)
└── remoteops-agent.zip     → Windows agent pack (extract on each agent PC)
```

You must **download and extract** these zips. The source is not checked out as loose folders on GitHub.

---

## Requirements

| Role | Need |
|------|------|
| Server PC | Python 3.10+ (3.11 recommended), network reachable by agents |
| Agent PC (Windows pack) | Python 3.10+ with **Add to PATH** checked during install |
| Network | Same LAN (or VPN). Server port **8000** reachable from agents |

---

# PART A — Server PC (control machine)

Do everything in this section **only on the machine that will host RemoteOps**.

### A1. Download and extract

1. Open: https://github.com/Shyamkumars769/remoteops  
2. Download `remoteops server&agent.zip`  
3. Extract it. Inside you will see:
   - `remoteops-server.zip`
   - `remoteops-agent.zip`
4. Extract **`remoteops-server.zip`**  
   You should get a folder named `remoteops-full` (or similar) with `server/`, `agent/`, `requirements.txt`, `.env.example`, etc.

### A2. Open a terminal in the server project folder

```bat
cd path\to\remoteops-full
```

Example:

```bat
cd C:\Users\admin\Desktop\remoteops-full
```

### A3. Create virtual environment and install packages

**Windows:**

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

**Linux / macOS:**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### A4. Create `.env`

**Windows:**

```bat
copy .env.example .env
```

**Linux / macOS:**

```bash
cp .env.example .env
```

Open `.env` and set at least:

```env
SECRET_KEY=some-long-random-string
ENROLLMENT_KEY=change-me-enrollment-key
ADMIN_USERNAME=admin
ADMIN_PASSWORD=change-me-admin-password
CORS_ORIGINS=http://localhost:8000,http://127.0.0.1:8000
```

**Important:**  
- Login password = whatever you put in `ADMIN_PASSWORD`  
- Agents must use the **same** `ENROLLMENT_KEY` later  

If `.env.example` already has those values and you keep them, login is:

- Username: `admin`  
- Password: `change-me-admin-password`

### A5. Start the server

```bat
uvicorn server.main:app --reload --host 0.0.0.0 --port 8000
```

Leave this window open.

You should see something like:

```text
Uvicorn running on http://0.0.0.0:8000
Bootstrap admin user created: admin
RemoteOps server started
```

### A6. Open the UI on the server

Browser:

```text
http://localhost:8000/login
```

Login with the admin user from `.env`.

### A7. Get this PC’s LAN IP (for agents)

**Windows (Command Prompt):**

```bat
ipconfig
```

Look for **IPv4 Address**, for example `192.168.1.42`.

Agents will use:

```text
http://192.168.1.42:8000
```

### A8. Allow port 8000 through Windows Firewall (server only)

Run **once** in **Administrator** Command Prompt on the **server**:

```bat
netsh advfirewall firewall add rule name="RemoteOps" dir=in action=allow protocol=TCP localport=8000
```

Not required for localhost-only use. Required for other PCs on the network.

### A9. Quick health check

On the server:

```text
http://localhost:8000/healthz
```

Should show: `{"status":"ok"}`

From another PC on the same network:

```text
http://SERVER_IP:8000/healthz
```

If that fails, fix IP / firewall before starting agents.

### A10. If login fails after changing `.env`

Admin is created only when the database is first created. Reset it:

**Windows:**

```bat
del db\db.sqlite
```

**Linux / macOS:**

```bash
rm -f db/db.sqlite
```

Restart the server, then login again with the password from the current `.env`.

---

# PART B — Agent PC (other machine)

Do this on each machine you want to control.

### B1. Copy the agent pack

From the same `remoteops server&agent.zip` package, take **`remoteops-agent.zip`** to the other PC and extract it.

You should see a folder like `windows-agent` with:

```text
CONFIG.txt
SETUP.bat
START-AGENT.bat
agent\
README.txt
```

### B2. Edit CONFIG.txt

Open `CONFIG.txt` in Notepad and set:

```text
SERVER_URL=http://192.168.1.42:8000
ENROLLMENT_KEY=change-me-enrollment-key
```

Rules:
- `SERVER_URL` = server LAN IP from step A7 (not `localhost` unless agent runs on the same PC)
- `ENROLLMENT_KEY` = **exactly** the same value as in the server `.env`

### B3. Run SETUP.bat (once)

Double-click **`SETUP.bat`**.

It will:
- Create a local `.venv`
- Install required Python packages
- Prepare `START-AGENT.bat`

Needs Python installed on that PC with PATH enabled.

### B4. Run START-AGENT.bat (every time)

Double-click **`START-AGENT.bat`**.

Leave the window open. You should see it connecting to the server URL.

### B5. Confirm on the server UI

On the server browser:

1. Go to **Agents**
2. The other machine’s hostname should appear
3. Click **Open Session** for full interactive control (shell + files)

---

# PART C — Same PC (server + agent together)

Useful for a quick local test.

Terminal 1 (server):

```bat
cd path\to\remoteops-full
.venv\Scripts\activate
uvicorn server.main:app --reload --host 0.0.0.0 --port 8000
```

Terminal 2 (agent):

```bat
cd path\to\remoteops-full
.venv\Scripts\activate
set SERVER_URL=http://127.0.0.1:8000
set ENROLLMENT_KEY=change-me-enrollment-key
python -m agent.agent
```

(Use the same enrollment key as in `.env`.)

Then open http://localhost:8000/login

---

# PART D — Using the platform

### Web UI
1. Login  
2. **Agents** — see online agents  
3. **Open Session** — live terminal + file panel  
4. **Sessions** — list / close sessions  

### CLI (from server project folder, venv active)

```bat
python -m cli.cli login admin change-me-admin-password
python -m cli.cli list-agents
python -m cli.cli system-info <agent_id> --wait
python -m cli.cli run-command <agent_id> whoami --wait
python -m cli.cli open-session <agent_id>
```

Use your real admin password from `.env`.

---

## Troubleshooting

| Problem | What to do |
|---------|------------|
| Login failed | Password must match `.env` `ADMIN_PASSWORD`. Delete `db\db.sqlite` and restart server if you changed it after first start. |
| Agent does not appear | Same `ENROLLMENT_KEY`; server running; `SERVER_URL` uses server LAN IP; firewall allows 8000 on server. |
| Other PC cannot open `/healthz` | Wrong IP, or firewall not opened on server. |
| `source` not recognized | You are on Windows — use `.venv\Scripts\activate`, not `source`. |
| `cp` not recognized | On Windows use `copy .env.example .env`. |
| SETUP.bat says Python not found | Install Python 3 and enable **Add Python to PATH**, then retry. |
| Session opens but weak shell on Windows | Full PTY is strongest on Linux/macOS; task commands still work via `run_command`. |

---

## Security notes

For lab / internal / authorized use only.

- Unrestricted shell and file access are intentional once a session is open.
- Change `SECRET_KEY`, `ENROLLMENT_KEY`, and admin password before any real deployment.
- Prefer HTTPS behind a reverse proxy for production.
- Only enroll machines you control.

---

## Version

Full interactive access + industrial auth baseline.
