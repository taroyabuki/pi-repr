#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import tempfile
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP, getcontext
from pathlib import Path


PI = "3.1415926535897932384626433832795028841971693993751"
SCRIPT_DIR = Path(__file__).resolve().parent
CLASSIC_BASIC_DIR = SCRIPT_DIR.parent.parent / "classic-basic"
RUNNERS = {
    "fm7": CLASSIC_BASIC_DIR / "run" / "fm7basic.sh",
    "fm11": CLASSIC_BASIC_DIR / "run" / "fm11basic.sh",
}
MAX_DIGITS = {
    "fm11": 17,
}


@dataclass(frozen=True)
class ProbeResult:
    digits: int
    trunc_literal: str
    trunc_result: str
    round_literal: str
    round_result: str


def build_literals(start_digits: int, end_digits: int) -> list[tuple[int, str, str]]:
    frac = PI.split(".")[1]
    getcontext().prec = 80
    x = Decimal(PI)
    rows: list[tuple[int, str, str]] = []
    for digits in range(start_digits, end_digits + 1):
        trunc = "3." + frac[:digits]
        quant = Decimal(f"1e-{digits}")
        rounded = format(x.quantize(quant, rounding=ROUND_HALF_UP), "f")
        rows.append((digits, trunc, rounded))
    return rows


def run_probe(runner: str, timeout_seconds: int, literal: str) -> str:
    program = "\n".join(
        (
            "10 DEFDBL A-Z",
            "20 A=657408909#/209259755#",
            f"30 B={literal}#",
            '40 IF B=A THEN PRINT "EQ"',
            '50 IF B<A THEN PRINT "LT"',
            '60 IF B>A THEN PRINT "GT"',
            "70 END",
        )
    )
    with tempfile.NamedTemporaryFile("w", suffix=".bas", delete=True) as handle:
        handle.write(program)
        handle.flush()
        completed = subprocess.run(
            [
                "timeout",
                str(timeout_seconds),
                str(RUNNERS[runner]),
                "--run",
                "--file",
                handle.name,
            ],
            capture_output=True,
            text=True,
            check=False,
        )
    lines = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    if completed.returncode != 0:
        stderr = completed.stderr.strip()
        stdout = completed.stdout.strip()
        raise RuntimeError(
            f"{runner} literal {literal} failed with exit {completed.returncode}: {stderr or stdout}"
        )
    if not lines:
        raise RuntimeError(f"{runner} literal {literal} produced no output")
    result = lines[-1]
    if result not in {"EQ", "LT", "GT"}:
        raise RuntimeError(f"{runner} literal {literal} returned unexpected output: {result!r}")
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scan F-BASIC decimal literal boundaries")
    parser.add_argument("runtime", choices=sorted(RUNNERS))
    parser.add_argument("--start-digits", type=int, default=13)
    parser.add_argument("--end-digits", type=int, default=17)
    parser.add_argument("--timeout", type=int, default=300)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    max_digits = MAX_DIGITS.get(args.runtime)
    if max_digits is not None and args.end_digits > max_digits:
        raise SystemExit(
            f"error: {args.runtime} supports at most {max_digits} fractional digits in this probe "
            "because of the BASIC source line-length limit"
        )
    rows: list[ProbeResult] = []
    for digits, trunc, rounded in build_literals(args.start_digits, args.end_digits):
        rows.append(
            ProbeResult(
                digits=digits,
                trunc_literal=trunc,
                trunc_result=run_probe(args.runtime, args.timeout, trunc),
                round_literal=rounded,
                round_result=run_probe(args.runtime, args.timeout, rounded),
            )
        )

    print(
        "digits | trunc literal          | trunc vs best | rounded literal        | rounded vs best"
    )
    print(
        "-------+------------------------+---------------+------------------------+----------------"
    )
    for row in rows:
        print(
            f"{row.digits:>6} | "
            f"{row.trunc_literal:<22} | "
            f"{row.trunc_result:<13} | "
            f"{row.round_literal:<22} | "
            f"{row.round_result:<14}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
