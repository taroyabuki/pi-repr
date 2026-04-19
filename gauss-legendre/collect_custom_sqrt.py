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
    command: tuple[str, ...] | None = None
    builtin_command: tuple[str, ...] | None = None
    newton_command: tuple[str, ...] | None = None
    allow_returncodes: tuple[int, ...] = (0,)
    timeout: int = 180


RUNNER_CONFIGS = (
    RunnerConfig(
        "BASIC-80",
        (
            "timeout",
            "30s",
            str(CLASSIC_BASIC / "basic80.sh"),
            "--run",
            "--file",
            str(Path(__file__).with_name("basic80-custom-sqrt.bas")),
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
            str(Path(__file__).with_name("nbasic-custom-sqrt.bas")),
        ),
        timeout=180,
    ),
    RunnerConfig(
        "N88-BASIC",
        (
            str(CLASSIC_BASIC / "n88basic.sh"),
            "--run",
            "--file",
            str(Path(__file__).with_name("n88basic-custom-sqrt.bas")),
        ),
        timeout=180,
    ),
    RunnerConfig(
        "FM-7 F-BASIC",
        (
            str(CLASSIC_BASIC / "fm7basic.sh"),
            "--run",
            "--timeout",
            "120s",
            "--file",
            str(Path(__file__).with_name("fm7basic-custom-sqrt.bas")),
        ),
        timeout=180,
    ),
    RunnerConfig(
        "FM-11 F-BASIC",
        builtin_command=(
            str(CLASSIC_BASIC / "fm11basic.sh"),
            "--run",
            "--timeout",
            "120s",
            "--file",
            str(Path(__file__).with_name("fm11basic-custom-sqrt.bas")),
        ),
        newton_command=(
            str(CLASSIC_BASIC / "fm11basic.sh"),
            "--run",
            "--timeout",
            "120s",
            "--file",
            str(Path(__file__).with_name("fm11basic-custom-newton.bas")),
        ),
        timeout=180,
    ),
    RunnerConfig(
        "GW-BASIC",
        (
            str(CLASSIC_BASIC / "gwbasic.sh"),
            "--run",
            "--file",
            str(Path(__file__).with_name("gwbasic-custom-sqrt.bas")),
        ),
        timeout=30,
    ),
)


@dataclass(frozen=True)
class VariantRow:
    n: str
    best: list[str]
    current: list[str]
    diff: str
    osc: int = 0


def normalize_bytes(raw: str) -> list[str]:
    values = [int(part) for part in re.findall(r"\d+", raw)]
    return [f"{value:02X}" for value in values]


def run_probe(config: RunnerConfig, command: tuple[str, ...]) -> str:
    proc = subprocess.run(
        command,
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
        match = re.fullmatch(r"(BUILTIN|NEWTON)\s+(\d+)", lines[i])
        if match is None:
            i += 1
            continue
        current = normalize_bytes(lines[i + 1])
        diff = lines[i + 2]
        if diff.startswith("DIFF"):
            diff = diff[4:].strip()
        osc = 0
        step = 3
        if i + 3 < len(lines):
            osc_match = re.fullmatch(r"OSC\s+(\d+)", lines[i + 3])
            if osc_match is not None:
                osc = int(osc_match.group(1))
                step = 4
        rows[match.group(1)] = VariantRow(
            n=match.group(2),
            best=best,
            current=current,
            diff=diff,
            osc=osc,
        )
        i += step
    return rows


def parse_single_variant(text: str, label: str) -> VariantRow:
    lines = [line.strip().rstrip("\x1a") for line in text.splitlines() if line.strip()]
    best_idx = lines.index("BEST")
    match = re.fullmatch(rf"{label}\s+(\d+)", lines[best_idx + 2])
    if match is None:
        raise ValueError(f"missing {label} line")
    diff = lines[best_idx + 4]
    if diff.startswith("DIFF"):
        diff = diff[4:].strip()
    osc = 0
    if best_idx + 5 < len(lines):
        osc_match = re.fullmatch(r"OSC\s+(\d+)", lines[best_idx + 5])
        if osc_match is not None:
            osc = int(osc_match.group(1))
    return VariantRow(
        n=match.group(1),
        best=normalize_bytes(lines[best_idx + 1]),
        current=normalize_bytes(lines[best_idx + 3]),
        diff=diff,
        osc=osc,
    )


def format_cell(row: VariantRow) -> str:
    if row.best == row.current:
        text = f"best (N={row.n})"
    else:
        text = f"N={row.n}, {row.diff}"
    if row.osc:
        text += f", osc={row.osc}"
    return f"`{text}`"


def main() -> int:
    print("| BASIC | built-in `SQR` | custom `SQR` |")
    print("| --- | --- | --- |")
    for config in RUNNER_CONFIGS:
        try:
            if config.command is not None:
                rows = parse_output(run_probe(config, config.command))
            else:
                assert config.builtin_command is not None
                assert config.newton_command is not None
                rows = {
                    "BUILTIN": parse_single_variant(run_probe(config, config.builtin_command), "BUILTIN"),
                    "NEWTON": parse_single_variant(run_probe(config, config.newton_command), "NEWTON"),
                }
        except (RuntimeError, ValueError, subprocess.TimeoutExpired) as exc:
            print(f"| {config.name} | `{exc}` |  |")
            continue
        print(f"| {config.name} | {format_cell(rows['BUILTIN'])} | {format_cell(rows['NEWTON'])} |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
