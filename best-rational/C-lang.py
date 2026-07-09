#!/usr/bin/env python3
"""
C言語の各浮動小数点型について、π の best と等しくなる有理数リテラル p/q のうち
文字列長が最短のものを探す。

手法: 区間 [best - half_ulp, best + half_ulp] の中で分母が最小の分数を求める
（Stern-Brocot 木を使った min_denom_in_interval）。

π ≈ 3.14 > 1 であるため、分母が k 桁のとき分子は必ず k+1 桁になり、
文字列長 = 2k+2 は分母の桁数 k だけで決まる。
よって「分母最小」=「文字列最短」が保証される。
"""

from __future__ import annotations

import math
import sys
from fractions import Fraction

sys.setrecursionlimit(100_000)


def min_denom_in_interval(lo: Fraction, hi: Fraction) -> Fraction:
    """[lo, hi] の中で分母が最小の分数を返す（分子も分母も正整数）。"""
    c = math.ceil(lo)
    if c <= hi:
        return Fraction(c)
    n = math.floor(lo)  # floor(lo) == floor(hi)（区間内に整数がないとき）
    sub = min_denom_in_interval(Fraction(1, hi - n), Fraction(1, lo - n))
    return Fraction(n) + Fraction(1, sub)


# ── 各型の target と half_ulp ─────────────────────────────────────────────────

# double (IEEE 754 binary64, 53-bit significand)
# best = 0x1.921fb54442d18p+1  (QBasic と同じ形式)
# π ∈ [2,4)  → ULP = 2^(1-52) = 2^-51, half_ulp = 2^-52
_n, _d = math.pi.as_integer_ratio()
TARGET_DOUBLE   = Fraction(_n, _d)
HALF_ULP_DOUBLE = Fraction(1, 2**52)

# long double (x87 80-bit extended, 64-bit explicit significand)
# best = 0x1.921fb54442d1846ap+1L = 0xC90FDAA22168C235 / 2^62
# ULP = 2^(1-63) = 2^-62, half_ulp = 2^-63
TARGET_LDOUBLE   = Fraction(int("C90FDAA22168C235", 16), 2**62)
HALF_ULP_LDOUBLE = Fraction(1, 2**63)

# _Decimal64 (16-digit decimal, coefficient × 10^-15)
# best = 3.141592653589793dd → coefficient 3141592653589793
# ULP = 10^-15, half_ulp = 5×10^-16 = 1/(2×10^15)
TARGET_D64   = Fraction(3141592653589793, 10**15)
HALF_ULP_D64 = Fraction(1, 2 * 10**15)

# _Decimal128 (34-digit decimal, coefficient × 10^-33)
# π を 34桁に丸める: 3.14159265358979323846264338327950288...
#   34桁目 = 2, 35桁目 = 8 → 切り上げ → 係数 = 3141592653589793238462643383279503
# ULP = 10^-33, half_ulp = 1/(2×10^33)
TARGET_D128   = Fraction(3141592653589793238462643383279503, 10**33)
HALF_ULP_D128 = Fraction(1, 2 * 10**33)

# __float128 (IEEE 754 binary128, 113-bit significand)
# best = 0x1.921FB54442D18469898CC51701B8p+1Q
# significand integer = 2^112 | 0x921FB54442D18469898CC51701B8
# value = sig_int / 2^111   (exponent=1, 112 fraction bits)
# ULP = 2^(1-112) = 2^-111, half_ulp = 2^-112
_sig_q = (1 << 112) | int("921FB54442D18469898CC51701B8", 16)
TARGET_Q128   = Fraction(_sig_q, 2**111)
HALF_ULP_Q128 = Fraction(1, 2**112)

# ── 既知の答え（C-lang.md より） ─────────────────────────────────────────────
KNOWN: dict[str, tuple[int, int]] = {
    "double":       (245850922,          78256779),
    "long double":  (8717442233,         2774848045),
    "_Decimal64":   (80143857,           25510582),
    "_Decimal128":  (66627445592888887,  21208174623389167),
    "__float128":   (363383500998180356, 115668560843798173),
}

CONFIGS = [
    ("double",      TARGET_DOUBLE,   HALF_ULP_DOUBLE),
    ("long double", TARGET_LDOUBLE,  HALF_ULP_LDOUBLE),
    ("_Decimal64",  TARGET_D64,      HALF_ULP_D64),
    ("_Decimal128", TARGET_D128,     HALF_ULP_D128),
    ("__float128",  TARGET_Q128,     HALF_ULP_Q128),
]

# ── 探索と表示 ────────────────────────────────────────────────────────────────
pi_exact = Fraction(*math.pi.as_integer_ratio())

print(f"{'型':<14} {'p/q':<38} {'len':>3}  {'match_known':>11}  {'p/q - π':>14}")
print("-" * 90)

all_ok = True
for name, target, half_ulp in CONFIGS:
    result = min_denom_in_interval(target - half_ulp, target + half_ulp)
    p, q   = result.numerator, result.denominator
    length = len(str(p)) + len(str(q)) + 1
    kp, kq = KNOWN[name]
    match  = (p == kp and q == kq)
    err    = float(result - pi_exact)
    flag   = "✓" if match else "✗ UNEXPECTED"
    if not match:
        all_ok = False
    print(f"{name:<14} {p}/{q:<37} {length:>3}  {flag:>11}  {err:+.4e}")

print()
if all_ok:
    print("すべて既知の答えと一致 → これらが最短の有理数リテラル")
else:
    print("※ 既知と異なる結果あり → 要確認")
