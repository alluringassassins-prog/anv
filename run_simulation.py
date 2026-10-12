"""Start the complete simulation from one terminal.

The launcher keeps the existing components as separate processes so a failure
in one service does not corrupt the others.  It owns their lifetime and stops
all children when the Ground Station exits or Ctrl+C is pressed.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import socket
import subprocess
import sys
import time
import runpy
from multiprocessing import freeze_support


ROOT = Path(__file__).resolve().parent


def wait_for_port(host: str, port: int, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    last_error: OSError | None = None
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.25):
                return
        except OSError as error:
            last_error = error
            time.sleep(0.1)
    detail = f": {last_error}" if last_error else ""
    raise RuntimeError(f"service {host}:{port} did not become ready{detail}")


def start_process(command: list[str], *, stdin=None) -> subprocess.Popen:
    return subprocess.Popen(command, cwd=ROOT, stdin=stdin)


def component_command(role: str, args: argparse.Namespace) -> list[str]:
    """Return a source or frozen-executable command for one component."""
    frozen = getattr(sys, "frozen", False)
    if frozen:
        command = [sys.executable, "--component", role]
    else:
        scripts = {
            "bus": "serverSocket.py",
            "environment": "-m",
            "ground-station": "GroundStation/CommandCLI.py",
        }
        command = [sys.executable, scripts[role]]
        if role == "environment":
            command.append("uvicorn")

    if role == "bus":
        command.extend(["--headless", "--host", args.host, "--port", str(args.bus_port)])
    elif role == "environment":
        command.extend(
            [
                *([] if frozen else ["Environment.EnvironmentCreator:app"]),
                "--host", args.host,
                "--port", str(args.environment_port),
            ]
        )
    return command


def run_component(role: str, args: argparse.Namespace) -> int:
    """Run one component inside a frozen executable child process."""
    original_argv = sys.argv
    try:
        if role == "bus":
            sys.argv = [sys.argv[0], "--headless", "--host", args.host, "--port", str(args.bus_port)]
            runpy.run_module("serverSocket", run_name="__main__")
            return 0
        if role == "ground-station":
            sys.argv = [sys.argv[0]]
            runpy.run_module("GroundStation.CommandCLI", run_name="__main__")
            return 0
        import uvicorn

        uvicorn.run("Environment.EnvironmentCreator:app", host=args.host, port=args.environment_port)
        return 0
    finally:
        sys.argv = original_argv


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the multi-agent simulation")
    parser.add_argument("--host", default="127.0.0.1", help="local service host")
    parser.add_argument("--environment-port", type=int, default=8000)
    parser.add_argument("--bus-port", type=int, default=7106)
    parser.add_argument("--no-ground-station", action="store_true")
    parser.add_argument("--startup-timeout", type=float, default=15.0)
    parser.add_argument("--component", choices=["bus", "environment", "ground-station"], help=argparse.SUPPRESS)
    args = parser.parse_args()

    if args.component:
        if args.component in {"bus", "ground-station"}:
            return run_component(args.component, args)
        import uvicorn

        uvicorn.run(
            "Environment.EnvironmentCreator:app",
            host=args.host,
            port=args.environment_port,
            log_level="info",
        )
        return 0

    python = sys.executable
    children: list[subprocess.Popen] = []

    bus_command = component_command("bus", args)
    environment_command = component_command("environment", args)

    try:
        children.append(start_process(bus_command, stdin=subprocess.DEVNULL))
        wait_for_port(args.host, args.bus_port, args.startup_timeout)

        children.append(start_process(environment_command, stdin=subprocess.DEVNULL))
        wait_for_port(args.host, args.environment_port, args.startup_timeout)

        if args.no_ground_station:
            print("Simulation services are running. Press Ctrl+C to stop.", flush=True)
            while True:
                time.sleep(1)

        ground_station = start_process(component_command("ground-station", args))
        children.append(ground_station)
        return ground_station.wait()
    except KeyboardInterrupt:
        return 130
    except (OSError, RuntimeError) as error:
        print(f"Unable to start simulation: {error}", file=sys.stderr)
        return 1
    finally:
        for child in reversed(children):
            if child.poll() is None:
                child.terminate()
        for child in reversed(children):
            try:
                child.wait(timeout=3)
            except subprocess.TimeoutExpired:
                child.kill()


if __name__ == "__main__":
    freeze_support()
    raise SystemExit(main())
