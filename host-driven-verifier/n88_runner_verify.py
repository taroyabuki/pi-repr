#!/usr/bin/env python3

from __future__ import annotations

import argparse
import random
import re
import subprocess
import tempfile
from fractions import Fraction
from pathlib import Path

from mbf_shared_model import (
    BEST_BYTES,
    EQUAL,
    GREATER,
    LESS,
    compare_fraction_to_target,
    encode_positive_fraction_nearest,
    locate_first_ge,
)

WORK_ROOT = Path(__file__).resolve().parents[2]
CLASSIC_BASIC_ROOT = WORK_ROOT / "classic-basic"
RUNNER = CLASSIC_BASIC_ROOT / "run" / "n88basic.sh"


def compare_label(result: int) -> str:
    return {LESS: "LESS", EQUAL: "EQUAL", GREATER: "GREATER"}[result]


def candidate_expr(p: int, q: int, *, hash_operands: bool) -> str:
    if hash_operands:
        return f"{p}#/{q}#"
    return f"{p}/{q}"


def build_program(expr: str) -> str:
    return "\n".join(
        [
            "10 DEFDBL A-Z",
            "20 T=657408909/209259755",
            f"30 A={expr}",
            "40 FOR I%=0 TO 7:PRINT PEEK(VARPTR(A)+I%);:NEXT I%:PRINT",
            '50 IF A=T THEN PRINT "EQUAL":END',
            '60 IF A<T THEN PRINT "LESS":END',
            '70 PRINT "GREATER"',
            "",
        ]
    )


def run_program(source: str) -> tuple[tuple[int, ...], str]:
    with tempfile.NamedTemporaryFile("w", encoding="ascii", suffix=".bas", delete=False) as fh:
        fh.write(source)
        temp_path = Path(fh.name)
    try:
        result = subprocess.run(
            ["bash", str(RUNNER), "--run", "--file", str(temp_path)],
            cwd=CLASSIC_BASIC_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    finally:
        temp_path.unlink(missing_ok=True)

    byte_lines: list[tuple[int, ...]] = []
    compare: str | None = None
    for raw_line in result.stdout.splitlines():
        line = raw_line.strip()
        numbers = [int(token) for token in re.findall(r"-?\d+", line)]
        if len(numbers) == 8 and all(0 <= value <= 255 for value in numbers):
            byte_lines.append(tuple(numbers))
        if line in {"LESS", "EQUAL", "GREATER"}:
            compare = line
    if not byte_lines or compare is None:
        raise RuntimeError(f"failed to parse N88 output:\n{result.stdout}")
    return byte_lines[0], compare


def run_check(args: argparse.Namespace) -> int:
    expr = candidate_expr(args.p, args.q, hash_operands=args.hash_operands)
    actual_bytes, actual_compare = run_program(build_program(expr))
    value = Fraction(args.p, args.q)
    expect_bytes = encode_positive_fraction_nearest(value)
    expect_compare = compare_label(compare_fraction_to_target(value, target_bytes=BEST_BYTES))
    print(f"EXPR {expr}")
    print(f"ACTUAL_BYTES {' '.join(str(v) for v in actual_bytes)}")
    print(f"EXPECT_BYTES {' '.join(str(v) for v in expect_bytes)}")
    print(f"ACTUAL_COMPARE {actual_compare}")
    print(f"EXPECT_COMPARE {expect_compare}")
    ok = actual_bytes == expect_bytes and actual_compare == expect_compare
    print(f"MATCH {int(ok)}")
    return 0 if ok else 1


def run_keycases(args: argparse.Namespace) -> int:
    cases = [
        (657408909, 209259755),
        (411557987, 131002976),
        (245850922, 78256779),
        (657408908, 209259755),
        (657408910, 209259755),
    ]
    failed = False
    for p, q in cases:
        actual_bytes, actual_compare = run_program(
            build_program(candidate_expr(p, q, hash_operands=args.hash_operands))
        )
        value = Fraction(p, q)
        expect_bytes = encode_positive_fraction_nearest(value)
        expect_compare = compare_label(compare_fraction_to_target(value, target_bytes=BEST_BYTES))
        ok = actual_bytes == expect_bytes and actual_compare == expect_compare
        failed = failed or not ok
        print(
            f"CASE p={p} q={q} expr={candidate_expr(p, q, hash_operands=args.hash_operands)} "
            f"actual_compare={actual_compare} expect_compare={expect_compare} "
            f"actual_match={int(actual_bytes == expect_bytes)} ok={int(ok)}"
        )
    return 1 if failed else 0


def run_verify_random(args: argparse.Namespace) -> int:
    rng = random.Random(args.seed)
    failed = False
    for index in range(1, args.samples + 1):
        q = rng.randint(1, args.max_q)
        p0, _ = locate_first_ge(q, target_bytes=BEST_BYTES)
        delta = rng.randint(-args.max_delta, args.max_delta)
        p = max(1, p0 + delta)
        actual_bytes, actual_compare = run_program(
            build_program(candidate_expr(p, q, hash_operands=args.hash_operands))
        )
        value = Fraction(p, q)
        expect_bytes = encode_positive_fraction_nearest(value)
        expect_compare = compare_label(compare_fraction_to_target(value, target_bytes=BEST_BYTES))
        ok = actual_bytes == expect_bytes and actual_compare == expect_compare
        failed = failed or not ok
        print(
            f"SAMPLE {index} p={p} q={q} expr={candidate_expr(p, q, hash_operands=args.hash_operands)} "
            f"delta={delta} actual_compare={actual_compare} "
            f"expect_compare={expect_compare} actual_match={int(actual_bytes == expect_bytes)} ok={int(ok)}"
        )
        if not ok:
            break
    return 1 if failed else 0


def run_locate(args: argparse.Namespace) -> int:
    p, result = locate_first_ge(args.q, target_bytes=BEST_BYTES)
    print(f"MODEL q={args.q} first_ge_p={p} compare={compare_label(result)}")
    return 0 if result == EQUAL else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Verify shared MBF-nearest model against the N88-BASIC runner.")
    parser.add_argument(
        "--hash-operands",
        action="store_true",
        help="Use p#/q# instead of plain p/q so the candidate is forced through double arithmetic.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    check = sub.add_parser("check")
    check.add_argument("p", type=int)
    check.add_argument("q", type=int)

    sub.add_parser("keycases")

    verify_random = sub.add_parser("verify-random")
    verify_random.add_argument("--samples", type=int, default=20)
    verify_random.add_argument("--max-q", type=int, default=5_000_000)
    verify_random.add_argument("--max-delta", type=int, default=4)
    verify_random.add_argument("--seed", type=int, default=1)

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
    if args.command == "verify-random":
        return run_verify_random(args)
    return run_locate(args)


if __name__ == "__main__":
    raise SystemExit(main())
