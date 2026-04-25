#!/usr/bin/env python3

from __future__ import annotations

import re
from pathlib import Path

from run_n88_probe import run_program


MACHIN_DIR = Path(__file__).resolve().parents[1]
BAS_DIR = MACHIN_DIR / "bas"
PROGRAMS = (
    ("TERMLOW", BAS_DIR / "n88basic-termlow.bas"),
    ("TERMHIGH", BAS_DIR / "n88basic-termhigh.bas"),
    ("SPLITLOW", BAS_DIR / "n88basic-splitlow.bas"),
    ("SPLITHIGH", BAS_DIR / "n88basic-splithigh.bas"),
)


def parse_mode_output(text: str, label: str) -> tuple[list[str], str, list[str], str]:
    lines = [line.strip().rstrip("\x1a") for line in text.splitlines() if line.strip()]
    best_idx = lines.index("BEST")
    best, next_i = read_bytes_from(lines, best_idx + 1)
    match = re.fullmatch(rf"{label}\s+(\d+)", lines[next_i])
    if match is None:
        raise RuntimeError(f"missing {label} line")
    current, diff_i = read_bytes_from(lines, next_i + 1)
    diff = lines[diff_i]
    return best, match.group(1), current, diff


def read_bytes_from(lines: list[str], index: int, *, count: int = 8) -> tuple[list[str], int]:
    values: list[str] = []
    pos = index
    while pos < len(lines) and len(values) < count:
        found = re.findall(r"\d+", lines[pos])
        if len(found) < 2 or any(int(value) < 0 or int(value) > 255 for value in found):
            break
        values.extend(found)
        pos += 1
    return values[:count], pos


def main() -> int:
    best_bytes: list[str] | None = None
    rows: list[tuple[str, str, list[str], str]] = []
    for label, path in PROGRAMS:
        best, n_value, current, diff = parse_mode_output(run_program(path), label)
        if best_bytes is None:
            best_bytes = best
        elif best_bytes != best:
            raise RuntimeError("BEST bytes differ between N88 probes")
        rows.append((label, n_value, current, diff))
    assert best_bytes is not None
    print("BEST")
    print(" ".join(best_bytes))
    for label, n_value, current, diff in rows:
        print(f"{label} {n_value}")
        print(" ".join(current))
        print(diff)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
