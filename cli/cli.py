#!/usr/bin/env python3
"""Operator CLI for RemoteOps Full Access."""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import requests

TOKEN_FILE = Path.home() / ".remoteops_token"


def _base(args: argparse.Namespace) -> str:
    return args.server_url.rstrip("/")


def _headers(args: argparse.Namespace) -> dict[str, str]:
    token = args.token or (TOKEN_FILE.read_text().strip() if TOKEN_FILE.exists() else "")
    if not token:
        print("Not logged in. Run: remoteops login", file=sys.stderr)
        sys.exit(1)
    return {"Authorization": f"Bearer {token}"}


def cmd_login(args: argparse.Namespace) -> None:
    r = requests.post(
        f"{_base(args)}/api/auth/login",
        data={"username": args.username, "password": args.password},
        timeout=15,
    )
    r.raise_for_status()
    data = r.json()
    TOKEN_FILE.write_text(data["access_token"])
    print(f"Logged in as role={data['role']}")


def cmd_list_agents(args: argparse.Namespace) -> None:
    r = requests.get(f"{_base(args)}/api/agents", headers=_headers(args), timeout=15)
    r.raise_for_status()
    rows = r.json()
    if args.json:
        print(json.dumps(rows, indent=2, default=str))
        return
    if not rows:
        print("No agents.")
        return
    print(f"{'AGENT_ID':<38} {'HOSTNAME':<20} {'IP':<16} {'LAST_SEEN'}")
    for a in rows:
        print(f"{a['agent_id']:<38} {a.get('hostname',''):<20} {str(a.get('ip') or ''):<16} {a.get('last_seen')}")


def cmd_run(args: argparse.Namespace) -> None:
    payload = {"command": " ".join(args.command)}
    body = {"agent_id": args.agent_id, "type": "run_command", "payload": payload}
    r = requests.post(f"{_base(args)}/api/tasks", headers=_headers(args), json=body, timeout=15)
    r.raise_for_status()
    task_id = r.json()["task_id"]
    print(f"Created task {task_id}")
    if args.wait:
        _wait_task(args, task_id)


def cmd_system_info(args: argparse.Namespace) -> None:
    body = {"agent_id": args.agent_id, "type": "system_info", "payload": {}}
    r = requests.post(f"{_base(args)}/api/tasks", headers=_headers(args), json=body, timeout=15)
    r.raise_for_status()
    task_id = r.json()["task_id"]
    print(f"Created task {task_id}")
    if args.wait:
        _wait_task(args, task_id)


def cmd_session(args: argparse.Namespace) -> None:
    r = requests.post(
        f"{_base(args)}/api/sessions",
        headers=_headers(args),
        json={"agent_id": args.agent_id},
        timeout=15,
    )
    r.raise_for_status()
    sid = r.json()["session_id"]
    print(f"Session created: {sid}")
    print(f"Open terminal at: {_base(args)}/terminal/{sid}")
    print("Or connect via WebSocket with your access token.")


def _wait_task(args: argparse.Namespace, task_id: str) -> None:
    deadline = time.time() + args.timeout
    while time.time() < deadline:
        r = requests.get(f"{_base(args)}/api/tasks", headers=_headers(args), timeout=15)
        r.raise_for_status()
        for t in r.json():
            if t["task_id"] == task_id and t["status"] in {"completed", "failed", "cancelled"}:
                print(json.dumps(t, indent=2, default=str))
                return
        time.sleep(2)
    print("Timed out waiting for result.")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="RemoteOps operator CLI")
    p.add_argument("--server-url", default=os.getenv("SERVER_URL", "http://localhost:8000"))
    p.add_argument("--token", default=None)
    sub = p.add_subparsers(required=True)

    login = sub.add_parser("login")
    login.add_argument("username")
    login.add_argument("password")
    login.set_defaults(func=cmd_login)

    la = sub.add_parser("list-agents")
    la.add_argument("--json", action="store_true")
    la.set_defaults(func=cmd_list_agents)

    run = sub.add_parser("run-command")
    run.add_argument("agent_id")
    run.add_argument("command", nargs="+")
    run.add_argument("--wait", action="store_true")
    run.add_argument("--timeout", type=int, default=120)
    run.set_defaults(func=cmd_run)

    si = sub.add_parser("system-info")
    si.add_argument("agent_id")
    si.add_argument("--wait", action="store_true")
    si.add_argument("--timeout", type=int, default=60)
    si.set_defaults(func=cmd_system_info)

    sess = sub.add_parser("open-session")
    sess.add_argument("agent_id")
    sess.set_defaults(func=cmd_session)

    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
