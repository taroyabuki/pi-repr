#!/usr/bin/env python3

from __future__ import annotations

import argparse
from fractions import Fraction

import msxbasic_verify as base
from msxbasic_compare_worker import (
    EQUAL,
    GREATER,
    LESS,
    MsxBasicCompareWorker,
    compare_label,
    locate_first_ge as worker_locate_first_ge,
)

BEST = Fraction(31415926535898, 10**13)
HALF_ULP = Fraction(1, 2 * 10**13)


def interval() -> tuple[Fraction, Fraction]:
    return BEST - HALF_ULP, BEST + HALF_ULP


def compare_fraction_to_target(value: Fraction) -> int:
    lo, hi = interval()
    if value < lo:
        return LESS
    if value >= hi:
        return GREATER
    return EQUAL


def ceil_fraction(value: Fraction) -> int:
    return -(-value.numerator // value.denominator)


def locate_first_ge(q: int) -> tuple[int, int]:
    if q <= 0:
        raise ValueError(f"expected positive q, got {q}")
    lo, _ = interval()
    p = ceil_fraction(lo * q)
    return p, compare_fraction_to_target(Fraction(p, q))


def run_compare(args: argparse.Namespace) -> int:
    result = compare_fraction_to_target(Fraction(args.p, args.q))
    print(f"{compare_label(result)} p={args.p} q={args.q} expr={base.candidate_expr(args.p, args.q)}")
    return 0 if result == EQUAL else 1


def run_locate(args: argparse.Namespace) -> int:
    p, result = locate_first_ge(args.q)
    verdict = base.MATCH_TOKEN if result == EQUAL else base.MISS_TOKEN
    print(f"{verdict} q={args.q} first_ge_p={p} compare={compare_label(result)} expr={base.candidate_expr(p, args.q)}")
    return 0 if result == EQUAL else 1


def run_keycases(args: argparse.Namespace) -> int:
    machine, extra_rom_path = base.resolve_msx_config(args)
    cases = [
        (5419351, 1725033),
        (10838702, 3450066),
        (31369698, 9985285),
    ]
    with MsxBasicCompareWorker(machine=machine, extra_rom_path=extra_rom_path) as worker:
        for p, q in cases:
            model_result = compare_fraction_to_target(Fraction(p, q))
            actual_result = worker.compare_candidate(p, q)
            print(
                f"CASE p={p} q={q} expr={base.candidate_expr(p, q)} "
                f"model={compare_label(model_result)} actual={compare_label(actual_result)}"
            )
    return 0


def run_locate_compare(args: argparse.Namespace) -> int:
    machine, extra_rom_path = base.resolve_msx_config(args)
    model_p, model_result = locate_first_ge(args.q)
    with MsxBasicCompareWorker(machine=machine, extra_rom_path=extra_rom_path) as worker:
        actual_p, actual_result = worker_locate_first_ge(worker, args.q)
    print(
        f"MODEL q={args.q} first_ge_p={model_p} compare={compare_label(model_result)} "
        f"expr={base.candidate_expr(model_p, args.q)}"
    )
    print(
        f"ACTUAL q={args.q} first_ge_p={actual_p} compare={compare_label(actual_result)} "
        f"expr={base.candidate_expr(actual_p, args.q)}"
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Naive BCD half-ulp model for MSX-BASIC, for contrast with actual worker results.")
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--rom", metavar="PATH", type=base.Path, default=base._DEFAULT_ROM_FILE if base._DEFAULT_ROM_FILE.is_file() else None)
    source.add_argument("--machine", metavar="NAME", default=None)
    parser.add_argument("--rom-dir", metavar="DIR", type=base.Path, default=base._DEFAULT_ROM_DIR)
    sub = parser.add_subparsers(dest="command", required=True)

    compare = sub.add_parser("compare")
    compare.add_argument("p", type=int)
    compare.add_argument("q", type=int)

    locate = sub.add_parser("locate")
    locate.add_argument("q", type=int)

    sub.add_parser("keycases")

    locate_compare = sub.add_parser("locate-compare")
    locate_compare.add_argument("q", type=int)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "compare":
        return run_compare(args)
    if args.command == "locate":
        return run_locate(args)
    if args.command == "keycases":
        return run_keycases(args)
    return run_locate_compare(args)


if __name__ == "__main__":
    raise SystemExit(main())
