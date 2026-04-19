#!/usr/bin/env python3

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
C_SOURCE = Path(__file__).with_name("C-agm.c")
C_OUTPUT = Path("/tmp/gauss-legendre-c-agm")


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


def format_bytes(best: list[str], current: list[str]) -> str:
    parts = []
    for best_byte, current_byte in zip(best, current):
        if best_byte == current_byte:
            parts.append(f"**{current_byte}**")
        else:
            parts.append(current_byte)
    return " ".join(parts)


def parse_output(text: str) -> list[Row]:
    lines = [line.strip().rstrip("\x1a") for line in text.splitlines() if line.strip()]
    rows: list[Row] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if not (line.startswith("[") and line.endswith("]")):
            i += 1
            continue
        name = line[1:-1]
        if i + 5 >= len(lines):
            raise ValueError(f"incomplete block for {name}")
        if lines[i + 1] != "BEST":
            raise ValueError(f"missing BEST for {name}")
        match = re.fullmatch(r"AGM\s+(\d+)", lines[i + 3])
        if match is None:
            raise ValueError(f"missing AGM line for {name}")
        rows.append(
            Row(
                name=name,
                n=match.group(1),
                best=normalize_bytes(lines[i + 2]),
                current=normalize_bytes(lines[i + 4]),
                diff=lines[i + 5],
            )
        )
        i += 6
    return rows


def run_probe() -> str:
    subprocess.run(
        ("gcc", "-std=gnu2x", str(C_SOURCE), "-lm", "-lquadmath", "-o", str(C_OUTPUT)),
        cwd=ROOT,
        check=True,
        text=True,
    )
    proc = subprocess.run(
        (str(C_OUTPUT),),
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    return proc.stdout


def main() -> int:
    print("| 型 | 最初の最良 `N` | Gauss-Legendre | bestとの差 |")
    print("| --- | --- | --- | --- |")
    for row in parse_output(run_probe()):
        status = "best と一致" if row.diff in ("+0.000e+00", "-0.000e+00") else "best と不一致"
        print(f"| `{row.name}` | `N={row.n}` | {status} | `{row.diff}` |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
