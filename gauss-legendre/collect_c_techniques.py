#!/usr/bin/env python3

from __future__ import annotations

import math
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
C_SOURCE = Path(__file__).with_name("C-agm-techniques.c")
C_OUTPUT = Path("/tmp/gauss-legendre-c-agm-tech")


@dataclass(frozen=True)
class Variant:
    name: str
    hit: bool
    n: int | None
    diff: str

    def abs_error(self) -> float:
        return abs(float(self.diff))


def run_probe() -> str:
    subprocess.run(
        ("gcc", "-std=gnu2x", str(C_SOURCE), "-lm", "-lquadmath", "-o", str(C_OUTPUT)),
        cwd=ROOT,
        check=True,
        text=True,
    )
    proc = subprocess.run(
        (str(C_OUTPUT), "8"),
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    return proc.stdout


def parse_output(text: str) -> dict[str, list[Variant]]:
    blocks: dict[str, list[Variant]] = {}
    current = ""
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            current = line[1:-1]
            blocks[current] = []
            continue
        match = re.fullmatch(r"([a-z_0-9]+)\s*:\s*N=(\d+) で best, err=([+-]\d+\.\d+e[+-]\d+)", line)
        if match is not None:
            blocks[current].append(Variant(match.group(1), True, int(match.group(2)), match.group(3)))
            continue
        match = re.fullmatch(r"([a-z_0-9]+)\s*:\s*N<=\d+ では見つからず, err=([+-]\d+\.\d+e[+-]\d+)", line)
        if match is not None:
            blocks[current].append(Variant(match.group(1), False, None, match.group(2)))
    return blocks


def choose_best(variants: list[Variant]) -> Variant:
    def key(v: Variant) -> tuple[int, int, float, int]:
        return (
            0 if v.hit else 1,
            v.n if v.n is not None else math.inf,
            v.abs_error(),
            0 if v.name == "plain" else 1,
        )

    return min(variants, key=key)


def format_variant(v: Variant) -> str:
    if v.hit:
        return f"`{v.name}, best (N={v.n})`"
    return f"`{v.name}, {v.diff}`"


def main() -> int:
    print("| 型 | plain | 工夫して最良 |")
    print("| --- | --- | --- |")
    for name, variants in parse_output(run_probe()).items():
        plain = next(v for v in variants if v.name == "plain")
        best = choose_best(variants)
        print(f"| `{name}` | {format_variant(plain)} | {format_variant(best)} |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
