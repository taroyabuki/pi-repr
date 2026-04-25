#!/usr/bin/env python3

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MACHIN_DIR = Path(__file__).resolve().parents[1]
BAS_DIR = MACHIN_DIR / "bas"
CLASSIC_BASIC = REPO_ROOT.parent / "classic-basic" / "run"
C_SOURCE = Path(__file__).with_name("C-builtin.c")
C_OUTPUT = Path("/tmp/machin-c-builtin")


@dataclass(frozen=True)
class RunnerConfig:
    name: str
    command: tuple[str, ...]
    allow_returncodes: tuple[int, ...] = (0,)
    timeout: int = 180


BASIC_CONFIGS = (
    RunnerConfig(
        "6502 BASIC",
        (str(CLASSIC_BASIC / "6502.sh"), "--run", "--file", str(BAS_DIR / "6502-builtin.bas")),
    ),
    RunnerConfig(
        "BASIC-80",
        (
            "timeout",
            "30s",
            str(CLASSIC_BASIC / "basic80.sh"),
            "--run",
            "--file",
            str(BAS_DIR / "basic80-builtin.bas"),
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
            str(BAS_DIR / "nbasic-builtin.bas"),
        ),
        timeout=180,
    ),
    RunnerConfig(
        "N88-BASIC",
        ("python3", str(Path(__file__).with_name("run_n88_probe.py")), str(BAS_DIR / "n88basic-builtin.bas")),
        timeout=180,
    ),
    RunnerConfig(
        "MSX-BASIC",
        (str(CLASSIC_BASIC / "msxbasic.sh"), "--run", "--file", str(BAS_DIR / "msxbasic-builtin.bas")),
    ),
    RunnerConfig(
        "GW-BASIC",
        (str(CLASSIC_BASIC / "gwbasic.sh"), "--run", "--file", str(BAS_DIR / "gwbasic-builtin.bas")),
        timeout=30,
    ),
    RunnerConfig(
        "QBasic",
        (str(CLASSIC_BASIC / "qbasic.sh"), "--run", "--file", str(BAS_DIR / "qbasic-builtin.bas")),
        timeout=30,
    ),
    RunnerConfig(
        "Grant BASIC",
        ("python3", str(Path(__file__).with_name("collect_grantsbasic_builtin.py"))),
        timeout=180,
    ),
)


def normalize_bytes(raw: str) -> list[str]:
    values = [int(part) for part in re.findall(r"\d+", raw)]
    return [f"{value:02X}" for value in values]


def read_bytes_after(lines: list[str], index: int, *, count: int = 8) -> tuple[list[str], int]:
    values: list[int] = []
    pos = index + 1
    while pos < len(lines) and len(values) < count:
        found = [int(part) for part in re.findall(r"\d+", lines[pos])]
        if len(found) < 2 or any(value < 0 or value > 255 for value in found):
            break
        values.extend(found)
        pos += 1
    return [f"{value:02X}" for value in values[:count]], pos


def parse_basic_output(text: str) -> tuple[list[str], list[str], str]:
    lines = [line.strip().rstrip("\x1a") for line in text.splitlines() if line.strip()]
    best_idx = max(i for i, line in enumerate(lines) if line == "BEST")
    machin_idx = max(i for i, line in enumerate(lines) if line == "MACHIN")
    best, _ = read_bytes_after(lines, best_idx)
    machin, diff_idx = read_bytes_after(lines, machin_idx)
    diff = lines[diff_idx]
    return best, machin, diff


def parse_c_output(text: str) -> list[tuple[str, list[str], list[str], str]]:
    rows: list[tuple[str, list[str], list[str], str]] = []
    current_name: str | None = None
    current_best: list[str] | None = None
    current_machin: list[str] | None = None
    expecting: str | None = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            current_name = line[1:-1]
            current_best = None
            current_machin = None
            expecting = None
            continue
        if line == "BEST":
            expecting = "best"
            continue
        if line == "MACHIN":
            expecting = "machin"
            continue
        if expecting == "best":
            current_best = normalize_bytes(line)
            expecting = None
            continue
        if expecting == "machin":
            current_machin = normalize_bytes(line)
            expecting = None
            continue
        if current_name is not None and current_best is not None and current_machin is not None:
            rows.append((current_name, current_best, current_machin, line))
            current_name = None
    return rows


def format_bytes(best: list[str], current: list[str]) -> str:
    parts = []
    for best_byte, current_byte in zip(best, current):
        if best_byte == current_byte:
            parts.append(f"**{current_byte}**")
        else:
            parts.append(current_byte)
    return " ".join(parts)


def run_probe(config: RunnerConfig) -> str:
    proc = subprocess.run(
        config.command,
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        timeout=config.timeout,
        check=False,
    )
    if proc.returncode not in config.allow_returncodes:
        raise RuntimeError(f"{config.name}: runner exited with {proc.returncode}")
    return proc.stdout + ("\n" + proc.stderr if proc.stderr else "")


def run_c_probe() -> str:
    subprocess.run(
        ("gcc", "-std=gnu2x", str(C_SOURCE), "-lm", "-lquadmath", "-o", str(C_OUTPUT)),
        cwd=REPO_ROOT,
        check=True,
        text=True,
    )
    proc = subprocess.run(
        (str(C_OUTPUT),),
        cwd=REPO_ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    return proc.stdout


def main() -> int:
    print("### C")
    print()
    print("| 型 | Machin の builtin arctan | バイト列 | bestとの差 |")
    print("| --- | --- | --- | --- |")
    for name, best, machin, diff in parse_c_output(run_c_probe()):
        status = "best と一致" if best == machin else "best と不一致"
        print(f"| `{name}` | {status} | {format_bytes(best, machin)} | `{diff}` |")
    print("| `_Decimal64` | 対応する `atan` がないので省略 |  |  |")
    print("| `_Decimal128` | 対応する `atan` がないので省略 |  |  |")
    print()

    print("### BASIC")
    print()
    print("| BASIC | Machin の `ATN` | バイト列 | bestとの差 |")
    print("| --- | --- | --- | --- |")
    for config in BASIC_CONFIGS:
        try:
            best, machin, diff = parse_basic_output(run_probe(config))
        except (RuntimeError, ValueError, subprocess.TimeoutExpired) as exc:
            print(f"| {config.name} | skipped |  | `{exc}` |")
            continue
        if config.name == "N-BASIC" and all(byte == "00" for byte in machin):
            print("| N-BASIC | 現在の runner では `ATN` probe が 0 を返すので保留 |  |  |")
            continue
        status = "best と一致" if best == machin else "best と不一致"
        print(f"| {config.name} | {status} | {format_bytes(best, machin)} | `{diff}` |")
    return 0


if __name__ == "__main__":
    sys.exit(main())
