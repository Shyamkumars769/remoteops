# Complete Setup Guide — Remote Systems Management Platform

> Step-by-step from zero: opening the folder, running the server and agent on your laptop, connecting another PC, and sending tasks.

---

## Table of Contents

1. [Part 1 — Your Laptop Setup](#part-1--your-laptop-setup)
2. [Part 2 — Other PC Setup](#part-2--other-pc-setup)
3. [Part 3 — Sending Tasks](#part-3--sending-tasks)
4. [Quick Reference — Task Commands](#quick-reference--task-commands)
5. [Troubleshooting](#troubleshooting)

---

## PART 1 — Your Laptop Setup

### Step 1 — Open the Project in VS Code

1. Open **VS Code**
2. Click **File → Open Folder**
3. Navigate to and select your `remoteops` folder
4. Click **Select Folder**

---

### Step 2 — Open Terminal 1 (for the Server)

1. In VS Code, press **Ctrl + `** (backtick) to open the terminal
2. Make sure it says **PowerShell** at the top right of the terminal panel
3. Run these commands one by one:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
```

> If it asks, type `Y` and press Enter.

```powershell
venv\Scripts\activate
```

You should now see `(venv)` at the start of your terminal line.

```powershell
venv\Scripts\python.exe -m uvicorn server.main:app --host 0.0.0.0 --port 8080
```

✅ **Server is running** when you see something like:

```
INFO:     Uvicorn running on http://0.0.0.0:8080
```

> **Leave this terminal running. Do not close it.**

---

### Step 3 — Open Terminal 2 (for the Agent on YOUR Laptop)

1. In VS Code, click the **+** icon in the terminal panel to open a second terminal
2. Run these commands one by one:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
```

```powershell
venv\Scripts\activate
```

```powershell
venv\Scripts\python.exe -m agent.agent
```

✅ **Agent is running** when you see something like:

```
Agent registered. Polling for tasks...
```

> **Leave this terminal running too. Do not close it.**

---

### Step 4 — Find Your Laptop's IP Address

Open a **third terminal** (or use any terminal temporarily) and run:

```powershell
ipconfig
```

Look for **IPv4 Address** under your **WiFi** or **Ethernet** section. It will look like:

```
IPv4 Address. . . . . . . : 10.24.1.243
```

📝 **Write this IP down** — you'll need it for the other PC.

---

### Step 5 — Allow Port 8080 Through Windows Firewall

Run this **once** in any terminal (you only ever need to do this one time):

```powershell
netsh advfirewall firewall add rule name="Remote Platform" dir=in action=allow protocol=TCP localport=8080
```

✅ You should see:

```
Ok.
```

---

### Step 6 — Open the Web UI

Open any browser on your laptop and go to:

```
http://localhost:8080
```

You should see the **Agents page** with your laptop's agent already registered.

---

## PART 2 — Other PC Setup

> Do everything below **on the other PC**.

---

### Step 7 — Copy the Agent Folder to the Other PC

From your laptop, copy the entire `agent/` folder to the other PC. You can do this via USB drive, shared folder on the same WiFi, or any file transfer method.

Place it somewhere simple like `C:\remoteagent\` so the structure looks like:

```
C:\remoteagent\
└── agent\
    ├── __init__.py
    ├── agent.py
    ├── config.py
    ├── logging.py
    └── modules\
        ├── __init__.py
        ├── system_info.py
        ├── executor.py
        ├── filesystem.py
        ├── process.py
        └── sniffer.py
```

---

### Step 8 — Create the Startup File on the Other PC

Inside `C:\remoteagent\` (right next to the `agent/` folder, **not inside it**), create a new file called `start_agent.py` and paste this inside — **replacing the IP with your laptop's actual IP from Step 4**:

```python
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from agent.agent import Agent
Agent(server_url="http://10.194.41.243:8080").run()
```

---

### Step 9 — Install Requirements on the Other PC

Open **PowerShell** or **Command Prompt** on the other PC and run:

```powershell
pip install requests psutil
```

If `pip` is not recognized, try:

```powershell
python -m pip install requests psutil
```

---

### Step 10 — Start the Agent on the Other PC

In the same terminal, navigate to the folder:

```powershell
cd C:\remoteagent
```

Then run:

```powershell
python start_agent.py
```

✅ **Agent is working** when you see:

```
Agent registered. Polling for tasks...
```

> **Leave this running. Do not close it.**

---

## PART 3 — Sending Tasks

### Step 11 — Open the Web UI from Any Device

From your laptop:
```
http://localhost:8080
```

From any other device on the same WiFi (phone, tablet, other PC):
```
http://10.194.41.243:8080
```
*(use your actual IP from Step 4)*

---

### Step 12 — Send a Task to the Other PC

1. Go to:
   ```
   http://localhost:8080/send_task
   ```
2. In the **Agent** dropdown, select the **other PC** (it will show its hostname)
3. In the **Task Type** box, type any command, for example:
   ```
   whoami
   ```
4. Click **Create Task**
5. **Wait about 6 seconds** for the agent to pick it up and run it
6. Go to:
   ```
   http://localhost:8080/tasks
   ```
7. Find your task and click **View** to see the result

---

## Quick Reference — Task Commands

| Type this in Task Type box | What it does |
|---|---|
| `system_info` | Full OS, CPU, RAM, network info |
| `list_processes` | All running processes |
| `whoami` | Current logged-in user |
| `ipconfig` | Network configuration |
| `hostname` | PC name |
| `tasklist` | All running programs |
| `systeminfo` | Full Windows system info |
| `netstat -an` | All network connections |
| `dir` | Current directory listing |
| `wmic cpu get name` | CPU model name |
| `net user` | All Windows user accounts |
| `ping google.com` | Test internet connection |

> For `list_files`, fill in the **Path** field (e.g. `C:\Users`).  
> For `run_command`, fill in the **Command** field.  
> For `kill_process`, fill in the **PID** field.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Server terminal shows error | Stop it with `Ctrl+C` and re-run the uvicorn command |
| Task stays `pending` forever | Agent is not running — check Terminal 2 |
| Can't reach `localhost:8080` | Server not running — check Terminal 1 |
| Other PC can't connect | Check the IP in `start_agent.py` matches Step 4, and that the Step 5 firewall rule was applied |
| `cannot load Activate.ps1` | Run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned` first |
| `No module named jinja2` | Run `venv\Scripts\python.exe -m pip install jinja2` |
| Agent re-registers with new ID after restart | Normal — just select the new agent ID in the UI |
| Need to fully reset | Run `Stop-Process -Name python -Force`, delete `db\db.sqlite`, then restart both terminals |

### Windows PowerShell Specific Fixes

```powershell
# Instead of touch
New-Item filename.py -ItemType File

# Instead of pip
venv\Scripts\python.exe -m pip install package_name

# Kill all Python processes
Stop-Process -Name python -Force

# Wait 3 seconds
Start-Sleep -Seconds 3

# Delete a file
Remove-Item filename -Force
```

---

*Guide based on the Remote Systems Management Platform project documentation.*
