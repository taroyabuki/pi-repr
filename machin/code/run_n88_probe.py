#!/usr/bin/env python3

from __future__ import annotations

import sys
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
CLASSIC_BASIC_SRC = REPO_ROOT.parent / "classic-basic" / "src"
sys.path.insert(0, str(CLASSIC_BASIC_SRC))

from n88basic_cli import N88BasicCLI, _load_program_source_lines
from run_control_bridge import RUN_ERR_OK, RUN_ERR_PROTOCOL, RUN_ERR_QUEUE_FULL, RunControlSession


def queue_token(session: RunControlSession, token: str, *, timeout: float = 5.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        ok, response = session.queue(token)
        if ok:
            return
        code = int(response.get("code", RUN_ERR_PROTOCOL))
        if code in (RUN_ERR_QUEUE_FULL, RUN_ERR_PROTOCOL):
            session.wait(100)
            time.sleep(0.05)
            continue
        raise RuntimeError(f"failed to queue {token!r}: {response}")
    raise TimeoutError(f"timed out queuing {token!r}")


def wait_for_stable_ready(cli: N88BasicCLI, session: RunControlSession, *, timeout: float) -> list[str]:
    deadline = time.monotonic() + timeout
    last_lines: list[str] | None = None
    stable_polls = 0
    while time.monotonic() < deadline:
        lines = cli._capture_interactive_screen_lines(session)
        if cli._screen_has_basic_ready(lines):
            if lines == last_lines:
                stable_polls += 1
            else:
                stable_polls = 1
            if stable_polls >= 3:
                return lines
        else:
            stable_polls = 0
        last_lines = lines
        session.wait(100)
        time.sleep(0.05)
    raise TimeoutError("timed out waiting for stable BASIC prompt")


def wait_for_stable_screen(cli: N88BasicCLI, session: RunControlSession, *, timeout: float) -> list[str]:
    deadline = time.monotonic() + timeout
    last_lines: list[str] | None = None
    stable_polls = 0
    while time.monotonic() < deadline:
        lines = cli._capture_interactive_screen_lines(session)
        if lines == last_lines:
            stable_polls += 1
        else:
            stable_polls = 1
        if stable_polls >= 3:
            return lines
        last_lines = lines
        session.wait(100)
        time.sleep(0.05)
    raise TimeoutError("timed out waiting for stable screen")


def queue_line(session: RunControlSession, line: str) -> None:
    for char in line:
        queue_token(session, char)
        session.wait(30)
        time.sleep(0.02)
    queue_token(session, "<CR>")


def run_program(path: Path, *, timeout_seconds: float = 300.0) -> str:
    cli = N88BasicCLI()
    session = RunControlSession()
    try:
        cli.start_quasi88_monitor()
        if not cli.ensure_run_bridge(session):
            raise RuntimeError("control bridge unavailable")
        ok, response = session.go()
        if not ok:
            raise RuntimeError(f"failed to start execution: {response}")
        if not cli._drive_run_startup(session, startup_timeout=5.0):
            raise TimeoutError("timed out waiting for BASIC startup")
        wait_for_stable_ready(cli, session, timeout=5.0)
        for line in _load_program_source_lines(path):
            queue_line(session, line)
            wait_for_stable_screen(cli, session, timeout=20.0)
        queue_token(session, "RUN")
        queue_token(session, "<CR>")
        completed, output_lines = cli._poll_run_completion(session, timeout_seconds=timeout_seconds)
        if not completed:
            raise TimeoutError("n88basic batch run timed out")
        if not output_lines:
            output_lines = list(cli._capture_run_screen_state(session)["output_lines"])
        return "\n".join(output_lines) + ("\n" if output_lines else "")
    finally:
        try:
            if cli.quasi88_proc is not None and session.socket:
                session.quit()
        except Exception:
            pass
        session.disconnect()
        cli.stop_quasi88()


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        print("usage: run_n88_probe.py PROGRAM.bas", file=sys.stderr)
        return 2
    path = Path(args[0]).resolve()
    try:
        sys.stdout.write(run_program(path))
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return RUN_ERR_OK


if __name__ == "__main__":
    raise SystemExit(main())
