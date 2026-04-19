#!/usr/bin/env python3

from __future__ import annotations

import math
from fractions import Fraction

BEST_BYTES = (0xC2, 0x68, 0x21, 0xA2, 0xDA, 0x0F, 0x49, 0x82)

LESS = -1
EQUAL = 0
GREATER = 1


def decode_positive_mbf(raw: tuple[int, ...] | list[int]) -> Fraction:
    if len(raw) != 8:
        raise ValueError(f"expected 8 bytes, got {len(raw)}")
    mantissa_fraction = sum((raw[index] & 0xFF) << (8 * index) for index in range(7))
    exponent = (raw[7] & 0xFF) - 128
    return Fraction((1 << 55) + mantissa_fraction, 1 << 56) * (1 << exponent)


def encode_positive_fraction_nearest(value: Fraction) -> tuple[int, ...]:
    if value <= 0:
        raise ValueError(f"expected positive value, got {value}")
    exponent = 0
    normalized = value
    while normalized >= 1:
        normalized /= 2
        exponent += 1
    while normalized < Fraction(1, 2):
        normalized *= 2
        exponent -= 1
    fraction_bits = normalized - Fraction(1, 2)
    scaled = fraction_bits * (1 << 56)
    mantissa = scaled.numerator // scaled.denominator
    remainder = scaled - mantissa
    if remainder >= Fraction(1, 2):
        mantissa += 1
    if mantissa >= 1 << 55:
        mantissa = 0
        exponent += 1
    return tuple((mantissa >> (8 * index)) & 0xFF for index in range(7)) + (exponent + 128,)


def half_ulp_for_bytes(raw: tuple[int, ...] | list[int]) -> Fraction:
    exponent = (raw[7] & 0xFF) - 128
    return Fraction(1 << exponent, 1 << 57)


def rounding_interval(raw: tuple[int, ...] | list[int]) -> tuple[Fraction, Fraction]:
    value = decode_positive_mbf(raw)
    half_ulp = half_ulp_for_bytes(raw)
    return value - half_ulp, value + half_ulp


def compare_fraction_to_target(value: Fraction, *, target_bytes: tuple[int, ...] = BEST_BYTES) -> int:
    lo, hi = rounding_interval(target_bytes)
    if value < lo:
        return LESS
    if value >= hi:
        return GREATER
    return EQUAL


def ceil_fraction(value: Fraction) -> int:
    return -(-value.numerator // value.denominator)


def locate_first_ge(q: int, *, target_bytes: tuple[int, ...] = BEST_BYTES) -> tuple[int, int]:
    if q <= 0:
        raise ValueError(f"expected positive q, got {q}")
    lo, _ = rounding_interval(target_bytes)
    p = ceil_fraction(lo * q)
    return p, compare_fraction_to_target(Fraction(p, q), target_bytes=target_bytes)


def min_denom_in_interval(lo: Fraction, hi: Fraction) -> Fraction:
    integer_ceiling = math.ceil(lo)
    if integer_ceiling < hi:
        return Fraction(integer_ceiling)
    integer_floor = math.floor(lo)
    sub = min_denom_in_interval(Fraction(1, hi - integer_floor), Fraction(1, lo - integer_floor))
    return Fraction(integer_floor) + Fraction(1, sub)
