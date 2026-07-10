#include <math.h>
#include <quadmath.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>

static int gcd_int(int a, int b) {
    while (b != 0) {
        int t = a % b;
        a = b;
        b = t;
    }
    return a < 0 ? -a : a;
}

#define DEFINE_SERIES(NAME, TYPE, ONE, TWO)                                      \
    static TYPE NAME##_atan_series(int terms, TYPE x) {                          \
        TYPE y = (TYPE)0;                                                        \
        for (int i = terms; i >= 1; --i) {                                       \
            TYPE c = (i % 2 == 0) ? -(ONE) : (ONE);                              \
            y = c / ((TWO) * (TYPE)i - (ONE)) + x * x * y;                       \
        }                                                                        \
        return x * y;                                                            \
    }

DEFINE_SERIES(decimal64, _Decimal64, 1.0dd, 2.0dd)
DEFINE_SERIES(double64, double, 1.0, 2.0)
DEFINE_SERIES(longdouble, long double, 1.0L, 2.0L)
DEFINE_SERIES(decimal128, _Decimal128, 1.0dl, 2.0dl)
DEFINE_SERIES(float128, __float128, 1.0Q, 2.0Q)

#define FILL_VALUES(NAME, TYPE, CAST)                                            \
    do {                                                                         \
        TYPE x = (TYPE)(CAST(a)) / (TYPE)(CAST(b));                              \
        TYPE y = (TYPE)(CAST(b - a)) / (TYPE)(CAST(b + a));                      \
        for (int k = 1; k <= max_terms; ++k) {                                   \
            NAME##_u[k] = (TYPE)(CAST(4)) * NAME##_atan_series(k, x);            \
            NAME##_v[k] = (TYPE)(CAST(4)) * NAME##_atan_series(k, y);            \
        }                                                                        \
    } while (0)

int main(int argc, char **argv) {
    int max_den = 40;
    int max_terms = 140;
    int max_print = 200;
    if (argc >= 2) max_den = atoi(argv[1]);
    if (argc >= 3) max_terms = atoi(argv[2]);
    if (argc >= 4) max_print = atoi(argv[3]);
    if (max_den < 2) max_den = 2;
    if (max_terms < 1) max_terms = 1;

    _Decimal64 *decimal64_u = calloc((size_t)max_terms + 1, sizeof(*decimal64_u));
    _Decimal64 *decimal64_v = calloc((size_t)max_terms + 1, sizeof(*decimal64_v));
    double *double64_u = calloc((size_t)max_terms + 1, sizeof(*double64_u));
    double *double64_v = calloc((size_t)max_terms + 1, sizeof(*double64_v));
    long double *longdouble_u = calloc((size_t)max_terms + 1, sizeof(*longdouble_u));
    long double *longdouble_v = calloc((size_t)max_terms + 1, sizeof(*longdouble_v));
    _Decimal128 *decimal128_u = calloc((size_t)max_terms + 1, sizeof(*decimal128_u));
    _Decimal128 *decimal128_v = calloc((size_t)max_terms + 1, sizeof(*decimal128_v));
    __float128 *float128_u = calloc((size_t)max_terms + 1, sizeof(*float128_u));
    __float128 *float128_v = calloc((size_t)max_terms + 1, sizeof(*float128_v));
    if (decimal64_u == NULL || decimal64_v == NULL || double64_u == NULL ||
        double64_v == NULL || longdouble_u == NULL || longdouble_v == NULL ||
        decimal128_u == NULL || decimal128_v == NULL || float128_u == NULL ||
        float128_v == NULL) {
        fputs("allocation failed\n", stderr);
        return 2;
    }

    const _Decimal64 best_d64 = 3.141592653589793dd;
    const double best_d = M_PI;
    const long double best_ld = 4.0L * atanl(1.0L);
    const _Decimal128 best_d128 = 3.1415926535897932384626433832795028dl;
    const __float128 best_q = M_PIq;

    int printed = 0;
    for (int b = 2; b <= max_den; ++b) {
        for (int a = 1; a < b; ++a) {
            if (gcd_int(a, b) != 1) continue;

            FILL_VALUES(decimal64, _Decimal64, (_Decimal64));
            FILL_VALUES(double64, double, (double));
            FILL_VALUES(longdouble, long double, (long double));
            FILL_VALUES(decimal128, _Decimal128, (_Decimal128));
            FILL_VALUES(float128, __float128, (__float128));

            for (int m = 1; m <= max_terms; ++m) {
                for (int n = 1; n <= max_terms; ++n) {
                    if (decimal64_u[m] + decimal64_v[n] == best_d64 &&
                        double64_u[m] + double64_v[n] == best_d &&
                        longdouble_u[m] + longdouble_v[n] == best_ld &&
                        decimal128_u[m] + decimal128_v[n] == best_d128 &&
                        float128_u[m] + float128_v[n] == best_q) {
                        printf("a=%d b=%d c=%d d=%d m=%d n=%d\n", a, b, b - a,
                               b + a, m, n);
                        ++printed;
                        if (max_print > 0 && printed >= max_print) goto done;
                    }
                }
            }
        }
    }

done:
    fprintf(stderr, "printed %d candidates\n", printed);
    free(decimal64_u);
    free(decimal64_v);
    free(double64_u);
    free(double64_v);
    free(longdouble_u);
    free(longdouble_v);
    free(decimal128_u);
    free(decimal128_v);
    free(float128_u);
    free(float128_v);
    return printed == 0 ? 1 : 0;
}
