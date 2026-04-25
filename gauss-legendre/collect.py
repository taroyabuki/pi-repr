#!/usr/bin/env python3

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLASSIC_BASIC = ROOT.parent / "classic-basic" / "run"


@dataclass(frozen=True)
class RunnerConfig:
    name: str
    command: tuple[str, ...]
    allow_returncodes: tuple[int, ...] = (0,)
    timeout: int = 180


RUNNER_CONFIGS = (
    RunnerConfig(
        "6502 BASIC",
        (str(CLASSIC_BASIC / "6502.sh"), "--run", "--file", str(Path(__file__).with_name("6502.bas"))),
    ),
    RunnerConfig(
        "BASIC-80",
        (
            "timeout",
            "30s",
            str(CLASSIC_BASIC / "basic80.sh"),
            "--run",
            "--file",
            str(Path(__file__).with_name("basic80.bas")),
        ),
        allow_returncodes=(0, 124),
    ),
    RunnerConfig(
        "N-BASIC",
        (
            str(CLASSIC_BASIC / "nbasic.sh"),
            "--max-steps",
            "1000000",
            "--max-rounds",
            "128",
            "--run",
            "--file",
            str(Path(__file__).with_name("nbasic.bas")),
        ),
        timeout=180,
    ),
    RunnerConfig(
        "N88-BASIC",
        (str(CLASSIC_BASIC / "n88basic.sh"), "--run", "--file", str(Path(__file__).with_name("n88basic.bas"))),
        timeout=180,
    ),
    RunnerConfig(
        "FM-7 F-BASIC",
        (str(CLASSIC_BASIC / "fm7basic.sh"), "--run", "--timeout", "120s", "--file", str(Path(__file__).with_name("fm7basic.bas"))),
        timeout=180,
    ),
    RunnerConfig(
        "FM-11 F-BASIC",
        (str(CLASSIC_BASIC / "fm11basic.sh"), "--run", "--timeout", "120s", "--file", str(Path(__file__).with_name("fm11basic.bas"))),
        timeout=180,
    ),
    RunnerConfig(
        "MSX-BASIC",
        (str(CLASSIC_BASIC / "msxbasic.sh"), "--run", "--file", str(Path(__file__).with_name("msxbasic.bas"))),
        timeout=120,
    ),
    RunnerConfig(
        "GW-BASIC",
        (str(CLASSIC_BASIC / "gwbasic.sh"), "--run", "--file", str(Path(__file__).with_name("gwbasic.bas"))),
        timeout=30,
    ),
    RunnerConfig(
        "QBasic",
        (str(CLASSIC_BASIC / "qbasic.sh"), "--run", "--file", str(Path(__file__).with_name("qbasic.bas"))),
        timeout=30,
    ),
    RunnerConfig(
        "Grant BASIC",
        ("python3", str(Path(__file__).with_name("collect_grantsbasic.py"))),
        timeout=180,
    ),
)


@dataclass(frozen=True)
class Row:
    name: str
    n: str
    best: list[str]
    current: list[str]
    diff: str


def normalize_bytes(raw: str) -> list[str]:
    values = [int(part) for part in re.findall(r"\d+", raw)]
    return [f"{value:02X}" for value in values]


def read_bytes_from(lines: list[str], index: int, *, count: int = 8) -> tuple[list[str], int]:
    values: list[int] = []
    pos = index
    while pos < len(lines) and len(values) < count:
        found = [int(part) for part in re.findall(r"\d+", lines[pos])]
        if len(found) < 2 or any(value < 0 or value > 255 for value in found):
            break
        values.extend(found)
        pos += 1
    return [f"{value:02X}" for value in values[:count]], pos


def format_bytes(best: list[str], current: list[str]) -> str:
    parts = []
    for best_byte, current_byte in zip(best, current):
        if best_byte == current_byte:
            parts.append(f"**{current_byte}**")
        else:
            parts.append(current_byte)
    return " ".join(parts)


def parse_output(text: str) -> Row:
    lines = [line.strip().rstrip("\x1a") for line in text.splitlines() if line.strip()]
    best_idx = lines.index("BEST")
    best, next_i = read_bytes_from(lines, best_idx + 1)
    match = re.fullmatch(r"AGM\s+(\d+)", lines[next_i])
    if match is None:
        raise ValueError("missing AGM line")
    current, diff_i = read_bytes_from(lines, next_i + 1)
    diff = lines[diff_i]
    if diff.startswith("DIFF"):
        diff = diff[4:].strip()
    return Row(
        name="",
        n=match.group(1),
        best=best,
        current=current,
        diff=diff,
    )


def run_probe(config: RunnerConfig) -> str:
    proc = subprocess.run(
        config.command,
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=config.timeout,
        check=False,
    )
    if proc.returncode not in config.allow_returncodes:
        raise RuntimeError(f"runner exited with {proc.returncode}")
    return proc.stdout + ("\n" + proc.stderr if proc.stderr else "")


def main() -> int:
    print("| BASIC | 最初の最良 `N` | Gauss-Legendre | バイト列 | bestとの差 |")
    print("| --- | --- | --- | --- | --- |")
    for config in RUNNER_CONFIGS:
        try:
            row = parse_output(run_probe(config))
        except (RuntimeError, ValueError, subprocess.TimeoutExpired) as exc:
            print(f"| {config.name} | skipped |  |  | `{exc}` |")
            continue
        status = "best と一致" if row.best == row.current else "best と不一致"
        print(f"| {config.name} | `N={row.n}` | {status} | {format_bytes(row.best, row.current)} | `{row.diff}` |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
