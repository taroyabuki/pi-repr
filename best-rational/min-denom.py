#!/usr/bin/env python3

from __future__ import annotations

from fractions import Fraction
import math
import sys


sys.setrecursionlimit(100_000)


def min_denom_in_interval(lo: Fraction, hi: Fraction) -> Fraction:
    c = math.ceil(lo)
    if c < hi:
        return Fraction(c)
    n = math.floor(lo)
    sub = min_denom_in_interval(Fraction(1, hi - n), Fraction(1, lo - n))
    return Fraction(n) + Fraction(1, sub)


def round_nearest(x: Fraction) -> int:
    n = x.numerator // x.denominator
    frac = x - n
    if frac > Fraction(1, 2):
        return n + 1
    if frac < Fraction(1, 2):
        return n
    return n + 1


BASIC_CONFIGS = [
    (
        "6502 BASIC",
        Fraction(13176795, 4194304),
        Fraction(1, 2**23),
        29712,
        Fraction(93343, 29712),
    ),
    (
        "BASIC-80",
        Fraction(28296951008113761, 9007199254740992),
        Fraction(1, 2**55),
        209259755,
        Fraction(657408909, 209259755),
    ),
    (
        "N-BASIC",
        Fraction(28296951008113761, 9007199254740992),
        Fraction(1, 2**55),
        209259755,
        Fraction(657408909, 209259755),
    ),
    (
        "MSX-BASIC",
        Fraction(31415926535898, 10**13),
        Fraction(1, 2 * 10**13),
        9985285,
        Fraction(31369698, 9985285),
    ),
    (
        "GW-BASIC",
        Fraction(28296951008113761, 9007199254740992),
        Fraction(1, 2**55),
        209259755,
        Fraction(657408909, 209259755),
    ),
    (
        "QBasic",
        Fraction(884279719003555, 281474976710656),
        Fraction(1, 2**52),
        78256779,
        Fraction(245850922, 78256779),
    ),
]


def main() -> None:
    print(
        f"{'BASIC':<12} {'Q':>10} {'Q*half_ulp':>14} {'<1/2':>5} "
        f"{'min_denom':>24} {'match':>7} {'delta p':>7}"
    )
    print("-" * 92)
    for name, target, half_ulp, upper_q, known in BASIC_CONFIGS:
        exact = min_denom_in_interval(target - half_ulp, target + half_ulp)
        nearest_p = round_nearest(target * known.denominator)
        delta_p = known.numerator - nearest_p
        prod = upper_q * half_ulp
        match = exact == known
        print(
            f"{name:<12} {upper_q:>10} {float(prod):>14.3E} "
            f"{('yes' if prod < Fraction(1, 2) else 'no'):>5} "
            f"{str(exact.numerator) + '/' + str(exact.denominator):>24} "
            f"{('yes' if match else 'NO'):>7} {delta_p:>7}"
        )


if __name__ == "__main__":
    main()
