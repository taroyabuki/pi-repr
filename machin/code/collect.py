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


@dataclass(frozen=True)
class RunnerConfig:
    name: str
    command: tuple[str, ...]
    allow_returncodes: tuple[int, ...] = (0,)
    timeout: int = 180


RUNNER_CONFIGS = (
    RunnerConfig(
        "6502 BASIC",
        (str(CLASSIC_BASIC / "6502.sh"), "--run", "--file", str(BAS_DIR / "6502.bas")),
    ),
    RunnerConfig(
        "BASIC-80",
        (
            "timeout",
            "30s",
            str(CLASSIC_BASIC / "basic80.sh"),
            "--run",
            "--file",
            str(BAS_DIR / "basic80.bas"),
        ),
        allow_returncodes=(0, 124),
    ),
    RunnerConfig(
        "N-BASIC",
        (
            str(CLASSIC_BASIC / "nbasic.sh"),
            "--max-steps",
            "2000000",
            "--max-rounds",
            "128",
            "--run",
            "--file",
            str(BAS_DIR / "nbasic.bas"),
        ),
        timeout=600,
    ),
    RunnerConfig(
        "N88-BASIC",
        ("python3", str(Path(__file__).with_name("collect_n88basic.py"))),
        timeout=1200,
    ),
    RunnerConfig(
        "FM-7 F-BASIC",
        (str(CLASSIC_BASIC / "fm7basic.sh"), "--run", "--timeout", "120s", "--file", str(BAS_DIR / "fm7basic.bas")),
        timeout=180,
    ),
    RunnerConfig(
        "FM-11 F-BASIC",
        (
            "timeout",
            "600s",
            str(CLASSIC_BASIC / "fm11basic.sh"),
            "--run",
            "--file",
            str(BAS_DIR / "fm11basic.bas"),
        ),
        allow_returncodes=(0, 124),
        timeout=620,
    ),
    RunnerConfig(
        "MSX-BASIC",
        (str(CLASSIC_BASIC / "msxbasic.sh"), "--run", "--file", str(BAS_DIR / "msxbasic.bas")),
        timeout=180,
    ),
    RunnerConfig(
        "GW-BASIC",
        (str(CLASSIC_BASIC / "gwbasic.sh"), "--run", "--file", str(BAS_DIR / "gwbasic.bas")),
        timeout=30,
    ),
    RunnerConfig(
        "QBasic",
        (str(CLASSIC_BASIC / "qbasic.sh"), "--run", "--file", str(BAS_DIR / "qbasic.bas")),
        timeout=30,
    ),
    RunnerConfig(
        "Grant BASIC",
        ("python3", str(Path(__file__).with_name("collect_grantsbasic.py"))),
        timeout=180,
    ),
)


def normalize_bytes(raw: str) -> list[str]:
    values = [int(part) for part in re.findall(r"\d+", raw)]
    return [f"{value:02X}" for value in values]


def _looks_like_diff(raw: str) -> bool:
    text = raw.strip()
    return re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[DE][+-]?\d+)?", text) is not None


def parse_output(text: str) -> dict[str, tuple[str, list[str], str] | list[str]]:
    lines = [line.strip().rstrip("\x1a") for line in text.splitlines()]
    result: dict[str, tuple[str, list[str], str] | list[str]] = {}
    i = 0
    while i < len(lines):
        line = lines[i]
        if line == "BEST":
            if i + 1 >= len(lines):
                i += 1
                continue
            best = normalize_bytes(lines[i + 1])
            if len(best) >= 4:
                result["BEST"] = best
            i += 2
            continue
        match = re.fullmatch(r"(TERMLOW|TERMHIGH|SPLITLOW|SPLITHIGH)\s+(\d+)", line)
        if match:
            label = match.group(1)
            if i + 2 >= len(lines):
                i += 1
                continue
            current = normalize_bytes(lines[i + 1])
            diff = lines[i + 2].strip()
            if len(current) >= 4 and _looks_like_diff(diff):
                result[label] = (match.group(2), current, diff)
            i += 3
            continue
        i += 1
    for key in ("BEST", "TERMLOW", "TERMHIGH", "SPLITLOW", "SPLITHIGH"):
        if key not in result:
            raise ValueError(f"missing {key} in output")
    return result


def format_bytes(best: list[str], current: list[str]) -> str:
    parts = []
    for best_byte, current_byte in zip(best, current):
        if best_byte == current_byte:
            parts.append(f"**{current_byte}**")
        else:
            parts.append(current_byte)
    return " ".join(parts)


def run_probe(config: RunnerConfig) -> str:
    try:
        proc = subprocess.run(
            config.command,
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            timeout=config.timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"timeout after {config.timeout}s") from exc
    if proc.returncode not in config.allow_returncodes:
        raise RuntimeError(f"runner exited with {proc.returncode}")
    return proc.stdout + ("\n" + proc.stderr if proc.stderr else "")


def row_from_output(name: str, text: str, mode: str) -> tuple[str, str, str, str, str, str, str]:
    parsed = parse_output(text)
    best = parsed["BEST"]
    assert isinstance(best, list)
    low = parsed[f"{mode}LOW"]
    high = parsed[f"{mode}HIGH"]
    assert isinstance(low, tuple)
    assert isinstance(high, tuple)
    return (
        name,
        f"`N={low[0]}`",
        format_bytes(best, low[1]),
        f"`{low[2]}`",
        f"`N={high[0]}`",
        format_bytes(best, high[1]),
        f"`{high[2]}`",
    )


def main() -> int:
    outputs: list[tuple[str, str]] = []
    for config in RUNNER_CONFIGS:
        try:
            outputs.append((config.name, run_probe(config)))
        except (RuntimeError, ValueError) as exc:
            print(f"{config.name}: skipped ({exc})", file=sys.stderr)

    for mode in ("TERM", "SPLIT"):
        print(f"### {mode}")
        print()
        print("| BASIC | 低次から足す | バイト列 | bestとの差 | 高次から足す | バイト列 | bestとの差 |")
        print("| --- | --- | --- | --- | --- | --- | --- |")
        for name, text in outputs:
            print("| " + " | ".join(row_from_output(name, text, mode)) + " |")
        if mode != "SPLIT":
            print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
