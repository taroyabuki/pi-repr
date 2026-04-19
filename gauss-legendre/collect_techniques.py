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
        (str(CLASSIC_BASIC / "6502.sh"), "--run", "--file", str(Path(__file__).with_name("6502-techniques.bas"))),
    ),
    RunnerConfig(
        "BASIC-80",
        (
            "timeout",
            "30s",
            str(CLASSIC_BASIC / "basic80.sh"),
            "--run",
            "--file",
            str(Path(__file__).with_name("basic80-techniques.bas")),
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
            str(Path(__file__).with_name("nbasic-techniques.bas")),
        ),
    ),
    RunnerConfig(
        "MSX-BASIC",
        (str(CLASSIC_BASIC / "msxbasic.sh"), "--run", "--file", str(Path(__file__).with_name("msxbasic-techniques.bas"))),
        timeout=120,
    ),
    RunnerConfig(
        "GW-BASIC",
        (str(CLASSIC_BASIC / "gwbasic.sh"), "--run", "--file", str(Path(__file__).with_name("gwbasic-techniques.bas"))),
        timeout=30,
    ),
    RunnerConfig(
        "QBasic",
        (str(CLASSIC_BASIC / "qbasic.sh"), "--run", "--file", str(Path(__file__).with_name("qbasic-techniques.bas"))),
        timeout=30,
    ),
)


@dataclass(frozen=True)
class VariantRow:
    n: str
    best: list[str]
    current: list[str]
    diff: str


def normalize_bytes(raw: str) -> list[str]:
    values = [int(part) for part in re.findall(r"\d+", raw)]
    return [f"{value:02X}" for value in values]


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


def parse_output(text: str) -> dict[str, VariantRow]:
    lines = [line.strip().rstrip("\x1a") for line in text.splitlines() if line.strip()]
    best_idx = lines.index("BEST")
    best = normalize_bytes(lines[best_idx + 1])
    rows: dict[str, VariantRow] = {}
    i = best_idx + 2
    while i + 2 < len(lines):
        match = re.fullmatch(r"(PLAIN|TSPLIT|FHALF|COMBO)\s+(\d+)", lines[i])
        if match is None:
            i += 1
            continue
        rows[match.group(1)] = VariantRow(
            n=match.group(2),
            best=best,
            current=normalize_bytes(lines[i + 1]),
            diff=lines[i + 2],
        )
        i += 3
    return rows


def format_cell(row: VariantRow) -> str:
    if row.best == row.current:
        return f"`best (N={row.n})`"
    return f"`N={row.n}, {row.diff}`"


def main() -> int:
    print("| BASIC | plain | t_split | final_half | combo |")
    print("| --- | --- | --- | --- | --- |")
    for config in RUNNER_CONFIGS:
        try:
            rows = parse_output(run_probe(config))
        except (RuntimeError, ValueError, subprocess.TimeoutExpired) as exc:
            print(f"| {config.name} | `{exc}` |  |  |  |")
            continue
        print(
            f"| {config.name} | {format_cell(rows['PLAIN'])} | {format_cell(rows['TSPLIT'])} | "
            f"{format_cell(rows['FHALF'])} | {format_cell(rows['COMBO'])} |"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
