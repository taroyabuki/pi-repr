#!/usr/bin/env python3

from __future__ import annotations

import argparse
import re
import subprocess
import tempfile
from fractions import Fraction
from pathlib import Path

from mbf_shared_model import BEST_BYTES, EQUAL, GREATER, LESS, compare_fraction_to_target, decode_positive_mbf, encode_positive_fraction_nearest, locate_first_ge

WORK_ROOT = Path(__file__).resolve().parents[2]
CLASSIC_BASIC_ROOT = WORK_ROOT / "classic-basic"
RUNNERS = {
    "basic80": CLASSIC_BASIC_ROOT / "run" / "basic80.sh",
    "gwbasic": CLASSIC_BASIC_ROOT / "run" / "gwbasic.sh",
}


def compare_label(result: int) -> str:
    return {LESS: "LESS", EQUAL: "EQUAL", GREATER: "GREATER"}[result]


def candidate_expr(runtime: str, p: int, q: int) -> str:
    if runtime == "gwbasic":
        return f"{p}#/{q}#"
    return f"{p}/{q}"


def build_program(runtime: str, expr: str) -> str:
    return "\n".join(
        [
            f"10 A#={expr}",
            '20 T$=MKD$(A#)',
            '30 FOR I=1 TO 8:PRINT ASC(MID$(T$,I,1));:NEXT I:PRINT',
            '40 SYSTEM',
            "",
        ]
    )


def run_program(runtime: str, source: str) -> tuple[int, ...]:
    runner = RUNNERS[runtime]
    with tempfile.NamedTemporaryFile("w", encoding="ascii", suffix=".bas", delete=False) as fh:
        fh.write(source)
        temp_path = Path(fh.name)
    try:
        result = subprocess.run(
            ["bash", str(runner), "--run", "--file", str(temp_path)],
            cwd=CLASSIC_BASIC_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    finally:
        temp_path.unlink(missing_ok=True)

    byte_lines: list[tuple[int, ...]] = []
    for line in result.stdout.splitlines():
        numbers = [int(token) for token in re.findall(r"-?\d+", line)]
        if len(numbers) == 8 and all(0 <= value <= 255 for value in numbers):
            byte_lines.append(tuple(numbers))
    if not byte_lines:
        raise RuntimeError(f"failed to parse MKD$ bytes from {runtime} output:\n{result.stdout}")
    return byte_lines[0]


def run_check(args: argparse.Namespace) -> int:
    expr = candidate_expr(args.runtime, args.p, args.q)
    actual = run_program(args.runtime, build_program(args.runtime, expr))
    expect = encode_positive_fraction_nearest(Fraction(args.p, args.q))
    print(f"RUNTIME {args.runtime}")
    print(f"EXPR {expr}")
    print(f"ACTUAL {' '.join(str(value) for value in actual)}")
    print(f"EXPECT {' '.join(str(value) for value in expect)}")
    print(f"MATCH {int(actual == expect)}")
    return 0 if actual == expect else 1


def run_keycases(args: argparse.Namespace) -> int:
    cases = [
        (657408909, 209259755),
        (411557987, 131002976),
        (245850922, 78256779),
    ]
    for p, q in cases:
        expr = candidate_expr(args.runtime, p, q)
        actual = run_program(args.runtime, build_program(args.runtime, expr))
        expect = encode_positive_fraction_nearest(Fraction(p, q))
        verdict = compare_fraction_to_target(Fraction(p, q), target_bytes=BEST_BYTES)
        print(
            f"CASE runtime={args.runtime} p={p} q={q} expr={expr} "
            f"compare={compare_label(verdict)} actual_match={int(actual == expect)}"
        )
    return 0


def run_locate(args: argparse.Namespace) -> int:
    p, result = locate_first_ge(args.q, target_bytes=BEST_BYTES)
    print(f"MODEL q={args.q} first_ge_p={p} compare={compare_label(result)}")
    return 0 if result == EQUAL else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Verify shared MBF-nearest model against BASIC-80 or GW-BASIC runners.")
    parser.add_argument("--runtime", choices=("basic80", "gwbasic"), required=True)
    sub = parser.add_subparsers(dest="command", required=True)

    check = sub.add_parser("check")
    check.add_argument("p", type=int)
    check.add_argument("q", type=int)

    sub.add_parser("keycases")

    locate = sub.add_parser("locate")
    locate.add_argument("q", type=int)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "check":
        return run_check(args)
    if args.command == "keycases":
        return run_keycases(args)
    return run_locate(args)


if __name__ == "__main__":
    raise SystemExit(main())
