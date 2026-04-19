/* experiment.c
 * 分母 q を 1 から増やし、各 q で p0=round(target*q) の近傍を調べる。
 *
 * ここでは C で現実的に全探索できる 3 型だけを扱う:
 *   _Decimal64, double, long double
 *
 * 各 q で d=0, +/-1, ..., +/-6 を比較し、
 *   - d=0 より良い候補が現れたか
 *   - 最初に exact match が出る q
 * を記録する。
 *
 * コンパイル:
 *   gcc -O3 -std=gnu2x best-rational/experiment.c -lm -o /tmp/exp
 */
#include <math.h>
#include <stdio.h>

static void scan_decimal64(void) {
    const long long known_q = 25510582LL;
    const int max_d = 6;
    _Decimal64 target = (_Decimal64)M_PI;
    long long first_better_q = 0;
    int first_better_d = 0;
    long long first_exact_q = 0;
    int first_exact_d = 0;

    for (long long q = 1; q <= known_q; q++) {
        long long p0 = llround((double)target * (double)q);
        _Decimal64 e0 = (_Decimal64)p0 / (_Decimal64)q - target;
        if (e0 < 0.0dd) e0 = -e0;

        if (!first_exact_q && (_Decimal64)p0 / (_Decimal64)q == target) {
            first_exact_q = q;
            first_exact_d = 0;
        }

        for (int d = 1; d <= max_d; d++) {
            _Decimal64 ep = (_Decimal64)(p0 + d) / (_Decimal64)q - target;
            _Decimal64 en = (_Decimal64)(p0 - d) / (_Decimal64)q - target;
            if (ep < 0.0dd) ep = -ep;
            if (en < 0.0dd) en = -en;

            if (!first_better_q && ep < e0) {
                first_better_q = q;
                first_better_d = d;
            }
            if (!first_better_q && en < e0) {
                first_better_q = q;
                first_better_d = -d;
            }
            if (!first_exact_q && (_Decimal64)(p0 + d) / (_Decimal64)q == target) {
                first_exact_q = q;
                first_exact_d = d;
            }
            if (!first_exact_q && (_Decimal64)(p0 - d) / (_Decimal64)q == target) {
                first_exact_q = q;
                first_exact_d = -d;
            }
        }
    }

    printf("_Decimal64: q=1..%lld, d=0,+/-1..+/-%d\n", known_q, max_d);
    printf("  d=0 より良い候補: %s\n", first_better_q ? "あり" : "なし");
    if (first_better_q) {
        printf("  最初の例: q=%lld, d=%d\n", first_better_q, first_better_d);
    }
    printf("  最初の exact match: q=%lld, d=%d\n\n",
           first_exact_q, first_exact_d);
}

static void scan_double(void) {
    const long long known_q = 78256779LL;
    const int max_d = 6;
    double target = M_PI;
    long long first_better_q = 0;
    int first_better_d = 0;
    long long first_exact_q = 0;
    int first_exact_d = 0;

    for (long long q = 1; q <= known_q; q++) {
        long long p0 = llround(target * (double)q);
        double e0 = fabs((double)p0 / (double)q - target);

        if (!first_exact_q && (double)p0 / (double)q == target) {
            first_exact_q = q;
            first_exact_d = 0;
        }

        for (int d = 1; d <= max_d; d++) {
            double ep = fabs((double)(p0 + d) / (double)q - target);
            double en = fabs((double)(p0 - d) / (double)q - target);

            if (!first_better_q && ep < e0) {
                first_better_q = q;
                first_better_d = d;
            }
            if (!first_better_q && en < e0) {
                first_better_q = q;
                first_better_d = -d;
            }
            if (!first_exact_q && (double)(p0 + d) / (double)q == target) {
                first_exact_q = q;
                first_exact_d = d;
            }
            if (!first_exact_q && (double)(p0 - d) / (double)q == target) {
                first_exact_q = q;
                first_exact_d = -d;
            }
        }
    }

    printf("double: q=1..%lld, d=0,+/-1..+/-%d\n", known_q, max_d);
    printf("  d=0 より良い候補: %s\n", first_better_q ? "あり" : "なし");
    if (first_better_q) {
        printf("  最初の例: q=%lld, d=%d\n", first_better_q, first_better_d);
    }
    printf("  最初の exact match: q=%lld, d=%d\n\n",
           first_exact_q, first_exact_d);
}

static void scan_longdouble(void) {
    const long long known_q = 2774848045LL;
    const int max_d = 6;
    long double target = 4 * atanl(1);
    long long first_better_q = 0;
    int first_better_d = 0;
    long long first_exact_q = 0;
    int first_exact_d = 0;

    for (long long q = 1; q <= known_q; q++) {
        long long p0 = llroundl(target * (long double)q);
        long double e0 = fabsl((long double)p0 / (long double)q - target);

        if (!first_exact_q && (long double)p0 / (long double)q == target) {
            first_exact_q = q;
            first_exact_d = 0;
        }

        for (int d = 1; d <= max_d; d++) {
            long double ep = fabsl((long double)(p0 + d) / (long double)q - target);
            long double en = fabsl((long double)(p0 - d) / (long double)q - target);

            if (!first_better_q && ep < e0) {
                first_better_q = q;
                first_better_d = d;
            }
            if (!first_better_q && en < e0) {
                first_better_q = q;
                first_better_d = -d;
            }
            if (!first_exact_q && (long double)(p0 + d) / (long double)q == target) {
                first_exact_q = q;
                first_exact_d = d;
            }
            if (!first_exact_q && (long double)(p0 - d) / (long double)q == target) {
                first_exact_q = q;
                first_exact_d = -d;
            }
        }
    }

    printf("long double: q=1..%lld, d=0,+/-1..+/-%d\n", known_q, max_d);
    printf("  d=0 より良い候補: %s\n", first_better_q ? "あり" : "なし");
    if (first_better_q) {
        printf("  最初の例: q=%lld, d=%d\n", first_better_q, first_better_d);
    }
    printf("  最初の exact match: q=%lld, d=%d\n\n",
           first_exact_q, first_exact_d);
}

int main(void) {
    scan_decimal64();
    scan_double();
    scan_longdouble();
    return 0;
}
