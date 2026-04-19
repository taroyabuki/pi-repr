#!/usr/bin/env python3

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
CHECK = Path(__file__).with_name("C-pow.c")
OUTPUT = Path("/tmp/check-c-machin-pow")


@dataclass(frozen=True)
class Row:
    name: str
    results: dict[str, tuple[str, str]]


def describe(status: str, limit: int) -> str:
    if status == "none":
        return f"`N<={limit}` では見つからず"
    return f"`N={status}` で best"


def parse_output(text: str, limit: int) -> list[Row]:
    rows: list[Row] = []
    current_name: str | None = None
    current: dict[str, tuple[str, str]] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            if current_name is not None:
                rows.append(Row(current_name, current))
            current_name = line[1:-1]
            current = {}
            continue
        match = re.fullmatch(
            r"(TERMLOW|TERMHIGH|SPLITLOW|SPLITHIGH)\s*:\s*N(?:<=(\d+)|=(\d+))\s+.*,\s+err=([+-]\d+\.\d+e[+-]\d+)",
            line,
        )
        if not match:
            continue
        label = match.group(1)
        found = match.group(3)
        current[label] = (
            describe(found if found is not None else "none", limit),
            f"`{match.group(4)}`",
        )
    if current_name is not None:
        rows.append(Row(current_name, current))
    return rows


def run_probe(limit: int) -> str:
    subprocess.run(
        ("gcc", "-std=gnu2x", str(CHECK), "-lm", "-lquadmath", "-o", str(OUTPUT)),
        cwd=REPO_ROOT,
        check=True,
        text=True,
    )
    proc = subprocess.run(
        (str(OUTPUT), str(limit)),
        cwd=REPO_ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    return proc.stdout


def main() -> int:
    limit = 120
    rows = parse_output(run_probe(limit), limit)
    for mode in ("TERM", "SPLIT"):
        print(f"### {mode}")
        print()
        print("| C の型 | 低次から足す | bestとの差 | 高次から足す | bestとの差 |")
        print("| --- | --- | --- | --- | --- |")
        for row in rows:
            low, low_err = row.results[f"{mode}LOW"]
            high, high_err = row.results[f"{mode}HIGH"]
            print(f"| {row.name} | {low} | {low_err} | {high} | {high_err} |")
        if mode != "SPLIT":
            print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
