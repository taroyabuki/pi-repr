#include <math.h>
#include <quadmath.h>
#include <stdio.h>
#include <stdlib.h>

static void print_error(__float128 diff) {
    char buf[64];
    quadmath_snprintf(buf, sizeof(buf), "%+.3Qe", diff);
    fputs(buf, stdout);
}

#define DEFINE_PROBE(NAME, TYPE, BEST_EXPR, X1, X2)                              \
    static TYPE NAME##_plain(int n) {                                            \
        TYPE x1 = (X1), x2 = (X2);                                               \
        TYPE xx1 = x1 * x1, xx2 = x2 * x2;                                       \
        TYPE term1 = x1, term2 = x2;                                             \
        TYPE a1 = term1, a2 = term2;                                             \
        for (int k = 1; k <= n; ++k) {                                           \
            TYPE num = (TYPE)(2 * k - 1), den = (TYPE)(2 * k + 1);               \
            term1 = -term1 * xx1 * num / den;                                    \
            term2 = -term2 * xx2 * num / den;                                    \
            a1 += term1;                                                         \
            a2 += term2;                                                         \
        }                                                                        \
        return (TYPE)16 * a1 - (TYPE)4 * a2;                                     \
    }                                                                            \
    static TYPE NAME##_scaled(int n) {                                           \
        TYPE x1 = (X1), x2 = (X2);                                               \
        TYPE xx1 = x1 * x1, xx2 = x2 * x2;                                       \
        TYPE term1 = x1, term2 = x2;                                             \
        TYPE a1 = term1, a2 = term2;                                             \
        for (int k = 1; k <= n; ++k) {                                           \
            TYPE num = (TYPE)(2 * k - 1), den = (TYPE)(2 * k + 1);               \
            term1 = -term1 * xx1 * num / den;                                    \
            term2 = -term2 * xx2 * num / den;                                    \
            a1 += term1;                                                         \
            a2 += term2;                                                         \
        }                                                                        \
        return (TYPE)4 * ((TYPE)4 * a1 - a2);                                    \
    }                                                                            \
    static TYPE NAME##_kahan(int n) {                                            \
        TYPE x1 = (X1), x2 = (X2);                                               \
        TYPE xx1 = x1 * x1, xx2 = x2 * x2;                                       \
        TYPE term1 = x1, term2 = x2;                                             \
        TYPE a1 = term1, a2 = term2;                                             \
        TYPE c1 = 0, c2 = 0;                                                     \
        for (int k = 1; k <= n; ++k) {                                           \
            TYPE num = (TYPE)(2 * k - 1), den = (TYPE)(2 * k + 1);               \
            TYPE y1, y2, t1, t2;                                                 \
            term1 = -term1 * xx1 * num / den;                                    \
            term2 = -term2 * xx2 * num / den;                                    \
            y1 = term1 - c1;                                                     \
            t1 = a1 + y1;                                                        \
            c1 = (t1 - a1) - y1;                                                 \
            a1 = t1;                                                             \
            y2 = term2 - c2;                                                     \
            t2 = a2 + y2;                                                        \
            c2 = (t2 - a2) - y2;                                                 \
            a2 = t2;                                                             \
        }                                                                        \
        return (TYPE)16 * a1 - (TYPE)4 * a2;                                     \
    }                                                                            \
    static TYPE NAME##_split(int n) {                                            \
        TYPE x1 = (X1), x2 = (X2);                                               \
        TYPE xx1 = x1 * x1, xx2 = x2 * x2;                                       \
        TYPE term1 = x1, term2 = x2;                                             \
        TYPE pos1 = x1, neg1 = 0, pos2 = x2, neg2 = 0;                           \
        for (int k = 1; k <= n; ++k) {                                           \
            TYPE num = (TYPE)(2 * k - 1), den = (TYPE)(2 * k + 1);               \
            term1 = -term1 * xx1 * num / den;                                    \
            term2 = -term2 * xx2 * num / den;                                    \
            if (term1 >= 0) pos1 += term1; else neg1 -= term1;                   \
            if (term2 >= 0) pos2 += term2; else neg2 -= term2;                   \
        }                                                                        \
        return (TYPE)16 * (pos1 - neg1) - (TYPE)4 * (pos2 - neg2);               \
    }                                                                            \
    static void NAME##_report(const char *variant, TYPE (*fn)(int), int max_n) { \
        TYPE best = (BEST_EXPR);                                                 \
        TYPE last = fn(0);                                                       \
        int hit = -1;                                                            \
        for (int n = 0; n <= max_n; ++n) {                                       \
            TYPE value = fn(n);                                                  \
            if (hit < 0 && value == best) hit = n;                               \
            last = value;                                                        \
        }                                                                        \
        printf("%-8s: ", variant);                                               \
        if (hit >= 0) {                                                          \
            TYPE value = fn(hit);                                                \
            printf("N=%d で best, err=", hit);                                   \
            print_error((__float128)value - (__float128)best);                   \
        } else {                                                                 \
            printf("N<=%d では見つからず, err=", max_n);                         \
            print_error((__float128)last - (__float128)best);                    \
        }                                                                        \
        putchar('\n');                                                           \
    }                                                                            \
    static void probe_##NAME(int max_n) {                                        \
        puts("[" #TYPE "]");                                                     \
        NAME##_report("plain", NAME##_plain, max_n);                             \
        NAME##_report("scaled", NAME##_scaled, max_n);                           \
        NAME##_report("kahan", NAME##_kahan, max_n);                             \
        NAME##_report("split", NAME##_split, max_n);                             \
        puts("");                                                                \
    }

#define DEFINE_FMA_PROBE(NAME, TYPE, BEST_EXPR, X1, X2, FMAFUNC)                 \
    static TYPE NAME##_fma(int n) {                                              \
        TYPE x1 = (X1), x2 = (X2);                                               \
        TYPE xx1 = x1 * x1, xx2 = x2 * x2;                                       \
        TYPE term1 = x1, term2 = x2;                                             \
        TYPE a1 = term1, a2 = term2;                                             \
        for (int k = 1; k <= n; ++k) {                                           \
            TYPE num = (TYPE)(2 * k - 1), den = (TYPE)(2 * k + 1);               \
            term1 = -term1 * xx1 * num / den;                                    \
            term2 = -term2 * xx2 * num / den;                                    \
            a1 = FMAFUNC((TYPE)1, term1, a1);                                    \
            a2 = FMAFUNC((TYPE)1, term2, a2);                                    \
        }                                                                        \
        return FMAFUNC((TYPE)-4, a2, (TYPE)16 * a1);                             \
    }                                                                            \
    static void probe_##NAME##_fma(int max_n) {                                  \
        TYPE best = (BEST_EXPR);                                                 \
        TYPE last = NAME##_fma(0);                                               \
        int hit = -1;                                                            \
        for (int n = 0; n <= max_n; ++n) {                                       \
            TYPE value = NAME##_fma(n);                                          \
            if (hit < 0 && value == best) hit = n;                               \
            last = value;                                                        \
        }                                                                        \
        printf("%-8s: ", "fma");                                                 \
        if (hit >= 0) {                                                          \
            TYPE value = NAME##_fma(hit);                                        \
            printf("N=%d で best, err=", hit);                                   \
            print_error((__float128)value - (__float128)best);                   \
        } else {                                                                 \
            printf("N<=%d では見つからず, err=", max_n);                         \
            print_error((__float128)last - (__float128)best);                    \
        }                                                                        \
        putchar('\n');                                                           \
    }

DEFINE_PROBE(decimal64, _Decimal64, 3.141592653589793dd, 0.2dd, 1.0dd / 239.0dd)
DEFINE_PROBE(double64, double, 4 * atan(1.0), 0.2, 1.0 / 239.0)
DEFINE_PROBE(longdouble, long double, 4 * atanl(1.0L), 0.2L, 1.0L / 239.0L)
DEFINE_PROBE(decimal128, _Decimal128, 3.1415926535897932384626433832795028dl, 0.2dl,
             1.0dl / 239.0dl)
DEFINE_PROBE(float128, __float128, 4 * atanq(1.0Q), 0.2Q, 1.0Q / 239.0Q)

DEFINE_FMA_PROBE(double64, double, 4 * atan(1.0), 0.2, 1.0 / 239.0, fma)
DEFINE_FMA_PROBE(longdouble, long double, 4 * atanl(1.0L), 0.2L, 1.0L / 239.0L, fmal)
DEFINE_FMA_PROBE(float128, __float128, 4 * atanq(1.0Q), 0.2Q, 1.0Q / 239.0Q, fmaq)

int main(int argc, char **argv) {
    int max_n = 120;
    if (argc >= 2) {
        max_n = atoi(argv[1]);
        if (max_n < 0) max_n = 0;
    }
    probe_decimal64(max_n);
    probe_double64(max_n);
    probe_double64_fma(max_n);
    puts("");
    probe_longdouble(max_n);
    probe_longdouble_fma(max_n);
    puts("");
    probe_decimal128(max_n);
    probe_float128(max_n);
    probe_float128_fma(max_n);
    return 0;
}
