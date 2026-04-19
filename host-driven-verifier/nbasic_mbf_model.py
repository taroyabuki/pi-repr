#!/usr/bin/env python3

from __future__ import annotations

import argparse
import random
from fractions import Fraction

from mbf_shared_model import (
    BEST_BYTES,
    EQUAL,
    GREATER,
    LESS,
    compare_fraction_to_target,
    decode_positive_mbf,
    encode_positive_fraction_nearest,
    locate_first_ge,
    min_denom_in_interval,
    rounding_interval,
)
from nbasic_compare_worker import MATCH_TOKEN, MISS_TOKEN, NBasicCompareWorker, candidate_expr, resolve_nbasic_rom_path


def compare_label(result: int) -> str:
    return {LESS: "LESS", EQUAL: "EQUAL", GREATER: "GREATER"}[result]


def run_compare(args: argparse.Namespace) -> int:
    value = Fraction(args.p, args.q)
    result = compare_fraction_to_target(value)
    print(f"{compare_label(result)} p={args.p} q={args.q} expr={candidate_expr(args.p, args.q)}")
    return 0 if result == EQUAL else 1


def run_locate(args: argparse.Namespace) -> int:
    p, result = locate_first_ge(args.q)
    verdict = MATCH_TOKEN if result == EQUAL else MISS_TOKEN
    print(f"{verdict} q={args.q} first_ge_p={p} compare={compare_label(result)} expr={candidate_expr(p, args.q)}")
    return 0 if result == EQUAL else 1


def run_min_denom() -> int:
    lo, hi = rounding_interval(BEST_BYTES)
    result = min_denom_in_interval(lo, hi)
    print(f"TARGET bytes={' '.join(f'{value:02X}' for value in BEST_BYTES)}")
    print(f"BEST {decode_positive_mbf(BEST_BYTES)}")
    print(f"INTERVAL_LO {lo}")
    print(f"INTERVAL_HI {hi}")
    print(f"MIN_DENOM {result.numerator}/{result.denominator}")
    return 0


def run_verify_worker(args: argparse.Namespace) -> int:
    random.seed(args.seed)
    cases: list[tuple[int, int]] = []
    for _ in range(args.samples):
        q = random.randint(1, args.max_q)
        p = random.randint(1, 4 * q)
        cases.append((p, q))
    for q in [7, 113, 1000, 10000, 131002976, 209259755]:
        center = round(float(decode_positive_mbf(BEST_BYTES)) * q)
        for delta in range(-2, 3):
            p = max(1, center + delta)
            cases.append((p, q))

    mismatches: list[tuple[int, int, tuple[int, ...], tuple[int, ...]]] = []
    with NBasicCompareWorker(
        rom_path=resolve_nbasic_rom_path(args.rom),
        max_steps=args.max_steps,
        batch_rounds=args.batch_rounds,
        slice_steps=args.slice_steps,
    ) as worker:
        for p, q in cases:
            worker.compare_candidate(p, q)
            actual = worker.read_current_quotient_bytes()
            expect = encode_positive_fraction_nearest(Fraction(p, q))
            if actual != expect:
                mismatches.append((p, q, actual, expect))

    print(f"CASES {len(cases)}")
    print(f"MISMATCHES {len(mismatches)}")
    for p, q, actual, expect in mismatches[:10]:
        print(f"MISMATCH p={p} q={q} actual={actual} expect={expect}")
    return 0 if not mismatches else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Host-side MBF-nearest model for N-BASIC p#/q# division.")
    sub = parser.add_subparsers(dest="command", required=True)

    compare = sub.add_parser("compare")
    compare.add_argument("p", type=int)
    compare.add_argument("q", type=int)

    locate = sub.add_parser("locate")
    locate.add_argument("q", type=int)

    sub.add_parser("min-denom")

    verify = sub.add_parser("verify-worker")
    verify.add_argument("--rom", metavar="PATH", default=None)
    verify.add_argument("--samples", type=int, default=60)
    verify.add_argument("--max-q", type=int, default=1_000_000)
    verify.add_argument("--seed", type=int, default=0)
    verify.add_argument("--max-steps", type=int, default=100_000)
    verify.add_argument("--batch-rounds", type=int, default=32)
    verify.add_argument("--slice-steps", type=int, default=1_000)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "compare":
        return run_compare(args)
    if args.command == "locate":
        return run_locate(args)
    if args.command == "min-denom":
        return run_min_denom()
    return run_verify_worker(args)


if __name__ == "__main__":
    raise SystemExit(main())
