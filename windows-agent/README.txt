RemoteOps Agent - Other PC setup
================================

ON THE SERVER PC (this machine where RemoteOps UI runs)
1. Note your IP:  ipconfig   (IPv4 address, e.g. 192.168.1.42)
2. Allow firewall port 8000
3. Keep uvicorn running

ON THE OTHER PC
1. Copy this whole "windows-agent" folder to the other PC
2. Edit CONFIG.txt  - set SERVER_URL to the server IP, e.g.
     SERVER_URL=http://192.168.1.42:8000
     ENROLLMENT_KEY=change-me-enrollment-key
   (ENROLLMENT_KEY must match the server .env)
3. Double-click SETUP.bat  (once)
4. Double-click START-AGENT.bat  (every time you want to connect)

Requirements on other PC: Python 3 installed with "Add to PATH".
If Python is missing, SETUP.bat will tell you.

After START-AGENT.bat runs, the agent appears on the server Agents page.
Open Session for full control.
