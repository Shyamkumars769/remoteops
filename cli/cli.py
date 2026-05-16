import argparse
import json
import time
from typing import Any

import requests


def _base_url(args: argparse.Namespace) -> str:
    return args.server_url.rstrip("/")


def _print_table(rows: list[dict[str, Any]], columns: list[str]) -> None:
    if not rows:
        print("No records.")
        return
    widths = {column: max(len(column), *(len(str(row.get(column, ""))) for row in rows)) for column in columns}
    print("  ".join(column.ljust(widths[column]) for column in columns))
    print("  ".join("-" * widths[column] for column in columns))
    for row in rows:
        print("  ".join(str(row.get(column, "")).ljust(widths[column]) for column in columns))


def list_agents(args: argparse.Namespace) -> None:
    response = requests.get(f"{_base_url(args)}/api/agents", timeout=10)
    response.raise_for_status()
    rows = response.json()
    _print_table(rows, ["agent_id", "hostname", "ip", "last_seen"])


def create_task(args: argparse.Namespace, task_type: str, payload: dict[str, Any]) -> str:
    response = requests.post(
        f"{_base_url(args)}/api/tasks",
        json={"agent_id": args.agent_id, "type": task_type, "payload": payload},
        timeout=10,
    )
    response.raise_for_status()
    data = response.json()
    print(f"Created task {data['task_id']} ({data['status']})")
    return data["task_id"]


def maybe_poll_result(args: argparse.Namespace, task_id: str) -> None:
    if not args.wait:
        return
    deadline = time.time() + args.timeout
    while time.time() < deadline:
        response = requests.get(f"{_base_url(args)}/api/tasks", timeout=10)
        response.raise_for_status()
        for task in response.json():
            if task["task_id"] == task_id and task["status"] in {"completed", "failed"}:
                print(json.dumps(task, indent=2, default=str))
                return
        time.sleep(2)
    print("Timed out waiting for result.")


def task_system_info(args: argparse.Namespace) -> None:
    maybe_poll_result(args, create_task(args, "system_info", {}))


def task_run_command(args: argparse.Namespace) -> None:
    maybe_poll_result(args, create_task(args, "run_command", {"command": " ".join(args.command_words)}))


def task_list_files(args: argparse.Namespace) -> None:
    maybe_poll_result(args, create_task(args, "list_files", {"path": args.path}))


def task_kill_process(args: argparse.Namespace) -> None:
    maybe_poll_result(args, create_task(args, "kill_process", {"pid": int(args.pid)}))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Operator CLI for the remote systems platform.")
    parser.add_argument("--server-url", default="http://localhost:8000")
    subparsers = parser.add_subparsers(required=True)

    agents_parser = subparsers.add_parser("list-agents")
    agents_parser.set_defaults(func=list_agents)

    def add_task_common(task_parser: argparse.ArgumentParser) -> None:
        task_parser.add_argument("agent_id")
        task_parser.add_argument("--wait", action="store_true")
        task_parser.add_argument("--timeout", type=int, default=60)

    system_parser = subparsers.add_parser("system-info")
    add_task_common(system_parser)
    system_parser.set_defaults(func=task_system_info)

    command_parser = subparsers.add_parser("run-command")
    add_task_common(command_parser)
    command_parser.add_argument("command_words", nargs="+")
    command_parser.set_defaults(func=task_run_command)

    files_parser = subparsers.add_parser("list-files")
    add_task_common(files_parser)
    files_parser.add_argument("path")
    files_parser.set_defaults(func=task_list_files)

    kill_parser = subparsers.add_parser("kill-process")
    add_task_common(kill_parser)
    kill_parser.add_argument("pid")
    kill_parser.set_defaults(func=task_kill_process)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
