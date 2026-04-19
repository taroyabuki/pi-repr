#!/usr/bin/env python3

from __future__ import annotations

from fractions import Fraction


def continued_fraction(value: Fraction) -> list[int]:
    terms: list[int] = []
    n, d = value.numerator, value.denominator
    while d:
        a = n // d
        terms.append(a)
        n, d = d, n - a * d
    return terms


def ratio_from_hex_float(significand: str, frac_digits: int, exp2: int) -> Fraction:
    value = Fraction(int(significand, 16), 16**frac_digits)
    if exp2 >= 0:
        return value * (2**exp2)
    return value / (2 ** (-exp2))


FORMATS: list[tuple[str, Fraction, tuple[str, ...]]] = [
    ("small FP", Fraction(13176795, 2**22), ("6502 BASIC", "Grant BASIC")),
    ("BCD double", Fraction(31415926535898, 10**13), ("MSX-BASIC",)),
    ("MBF double", Fraction(28296951008113761, 2**53), ("BASIC-80", "N-BASIC", "N88-BASIC", "F-BASIC", "GW-BASIC")),
    ("double", Fraction(884279719003555, 2**48), ("double", "QBasic")),
    (
        "long double",
        ratio_from_hex_float("C90FDAA22168C235", 15, -2),
        ("long double",),
    ),
    (
        "__float128",
        ratio_from_hex_float("1921FB54442D18469898CC51701B8", 28, 1),
        ("__float128",),
    ),
    ("decimal64", Fraction(3141592653589793, 10**15), ("_Decimal64",)),
    (
        "decimal128",
        Fraction(31415926535897932384626433832795028, 10**34),
        ("_Decimal128",),
    ),
]


def main() -> int:
    for name, value, aliases in FORMATS:
        terms = continued_fraction(value)
        joined = ", ".join(str(term) for term in terms)
        print(f"[{name}]")
        print(f"exact = {value.numerator}/{value.denominator}")
        print(f"terms = [{joined}]")
        print(f"count = {len(terms)}")
        print(f"aliases = {', '.join(aliases)}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
