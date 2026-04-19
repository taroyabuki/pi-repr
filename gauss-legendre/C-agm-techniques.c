#include <math.h>
#include <quadmath.h>
#include <stdio.h>
#include <stdlib.h>

static void print_error(__float128 diff) {
    char buf[64];
    quadmath_snprintf(buf, sizeof(buf), "%+.3Qe", diff);
    fputs(buf, stdout);
}

#define DEFINE_NEWTON_SQRT(NAME, TYPE, ONE, TWO)                                 \
    static TYPE NAME##_sqrt_plain(TYPE x) {                                      \
        TYPE guess = x > (ONE) ? x : (ONE);                                      \
        for (int i = 0; i < 80; ++i) {                                           \
            TYPE next = (guess + x / guess) / (TWO);                             \
            if (next == guess) break;                                            \
            guess = next;                                                        \
        }                                                                        \
        return guess;                                                            \
    }                                                                            \
    static TYPE NAME##_sqrt_half(TYPE x) {                                       \
        TYPE guess = x / (TWO);                                                  \
        if (guess <= 0) guess = (ONE);                                           \
        for (int i = 0; i < 80; ++i) {                                           \
            TYPE next = (guess + x / guess) / (TWO);                             \
            if (next == guess) break;                                            \
            guess = next;                                                        \
        }                                                                        \
        return guess;                                                            \
    }

DEFINE_NEWTON_SQRT(decimal64, _Decimal64, 1.0dd, 2.0dd)
DEFINE_NEWTON_SQRT(decimal128, _Decimal128, 1.0dl, 2.0dl)

#define DEFINE_AGM_VARIANTS(NAME, TYPE, ONE, TWO, FOUR, BEST_EXPR, SQRTFUNC)     \
    static TYPE NAME##_plain(int n) {                                            \
        TYPE a = (ONE), b = (ONE) / SQRTFUNC((TWO));                             \
        TYPE t = (ONE) / (FOUR), p = (ONE);                                      \
        for (int i = 0; i < n; ++i) {                                            \
            TYPE a_next = (a + b) / (TWO);                                       \
            TYPE diff = a - a_next;                                              \
            TYPE b_next = SQRTFUNC(a * b);                                       \
            t = t - p * diff * diff;                                             \
            a = a_next;                                                          \
            b = b_next;                                                          \
            p = p * (TWO);                                                       \
        }                                                                        \
        return (a + b) * (a + b) / ((FOUR) * t);                                \
    }                                                                            \
    static TYPE NAME##_t_split(int n) {                                          \
        TYPE a = (ONE), b = (ONE) / SQRTFUNC((TWO));                             \
        TYPE t = (ONE) / (FOUR), p = (ONE);                                      \
        for (int i = 0; i < n; ++i) {                                            \
            TYPE a_next = (a + b) / (TWO);                                       \
            TYPE diff = a - a_next;                                              \
            TYPE prod = p * diff;                                                \
            TYPE b_next = SQRTFUNC(a * b);                                       \
            t = t - prod * diff;                                                 \
            a = a_next;                                                          \
            b = b_next;                                                          \
            p = p * (TWO);                                                       \
        }                                                                        \
        return (a + b) * (a + b) / ((FOUR) * t);                                \
    }                                                                            \
    static TYPE NAME##_final_half(int n) {                                       \
        TYPE a = (ONE), b = (ONE) / SQRTFUNC((TWO));                             \
        TYPE t = (ONE) / (FOUR), p = (ONE);                                      \
        for (int i = 0; i < n; ++i) {                                            \
            TYPE a_next = (a + b) / (TWO);                                       \
            TYPE diff = a - a_next;                                              \
            TYPE b_next = SQRTFUNC(a * b);                                       \
            t = t - p * diff * diff;                                             \
            a = a_next;                                                          \
            b = b_next;                                                          \
            p = p * (TWO);                                                       \
        }                                                                        \
        {                                                                        \
            TYPE s = (a + b) / (TWO);                                            \
            return s * s / t;                                                    \
        }                                                                        \
    }                                                                            \
    static TYPE NAME##_combo(int n) {                                            \
        TYPE a = (ONE), b = (ONE) / SQRTFUNC((TWO));                             \
        TYPE t = (ONE) / (FOUR), p = (ONE);                                      \
        for (int i = 0; i < n; ++i) {                                            \
            TYPE a_next = (a + b) / (TWO);                                       \
            TYPE diff = a - a_next;                                              \
            TYPE prod = p * diff;                                                \
            TYPE b_next = SQRTFUNC(a * b);                                       \
            t = t - prod * diff;                                                 \
            a = a_next;                                                          \
            b = b_next;                                                          \
            p = p * (TWO);                                                       \
        }                                                                        \
        {                                                                        \
            TYPE s = (a + b) / (TWO);                                            \
            return s * s / t;                                                    \
        }                                                                        \
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
        printf("%-10s: ", variant);                                              \
        if (hit >= 0) {                                                          \
            TYPE value = fn(hit);                                                \
            printf("N=%d で best, err=", hit);                                   \
            print_error((__float128)value - (__float128)best);                   \
        } else {                                                                 \
            printf("N<=%d では見つからず, err=", max_n);                         \
            print_error((__float128)last - (__float128)best);                    \
        }                                                                        \
        putchar('\n');                                                           \
    }

#define DEFINE_AGM_FMA(NAME, TYPE, ONE, TWO, FOUR, BEST_EXPR, SQRTFUNC, FMAFUNC) \
    static TYPE NAME##_fma_t(int n) {                                            \
        TYPE a = (ONE), b = (ONE) / SQRTFUNC((TWO));                             \
        TYPE t = (ONE) / (FOUR), p = (ONE);                                      \
        for (int i = 0; i < n; ++i) {                                            \
            TYPE a_next = (a + b) / (TWO);                                       \
            TYPE diff = a - a_next;                                              \
            TYPE b_next = SQRTFUNC(a * b);                                       \
            t = FMAFUNC(-(p * diff), diff, t);                                   \
            a = a_next;                                                          \
            b = b_next;                                                          \
            p = p * (TWO);                                                       \
        }                                                                        \
        return (a + b) * (a + b) / ((FOUR) * t);                                \
    }                                                                            \
    static void NAME##_report_fma(int max_n) {                                   \
        TYPE best = (BEST_EXPR);                                                 \
        TYPE last = NAME##_fma_t(0);                                             \
        int hit = -1;                                                            \
        for (int n = 0; n <= max_n; ++n) {                                       \
            TYPE value = NAME##_fma_t(n);                                        \
            if (hit < 0 && value == best) hit = n;                               \
            last = value;                                                        \
        }                                                                        \
        printf("%-10s: ", "fma_t");                                              \
        if (hit >= 0) {                                                          \
            TYPE value = NAME##_fma_t(hit);                                      \
            printf("N=%d で best, err=", hit);                                   \
            print_error((__float128)value - (__float128)best);                   \
        } else {                                                                 \
            printf("N<=%d では見つからず, err=", max_n);                         \
            print_error((__float128)last - (__float128)best);                    \
        }                                                                        \
        putchar('\n');                                                           \
    }

#define DEFINE_AGM_PLAIN_ONLY(NAME, TYPE, ONE, TWO, FOUR, BEST_EXPR, SQRTFUNC)   \
    static TYPE NAME##_plain(int n) {                                            \
        TYPE a = (ONE), b = (ONE) / SQRTFUNC((TWO));                             \
        TYPE t = (ONE) / (FOUR), p = (ONE);                                      \
        for (int i = 0; i < n; ++i) {                                            \
            TYPE a_next = (a + b) / (TWO);                                       \
            TYPE diff = a - a_next;                                              \
            TYPE b_next = SQRTFUNC(a * b);                                       \
            t = t - p * diff * diff;                                             \
            a = a_next;                                                          \
            b = b_next;                                                          \
            p = p * (TWO);                                                       \
        }                                                                        \
        return (a + b) * (a + b) / ((FOUR) * t);                                \
    }                                                                            \
    static void NAME##_report(const char *variant, int max_n) {                  \
        TYPE best = (BEST_EXPR);                                                 \
        TYPE last = NAME##_plain(0);                                             \
        int hit = -1;                                                            \
        for (int n = 0; n <= max_n; ++n) {                                       \
            TYPE value = NAME##_plain(n);                                        \
            if (hit < 0 && value == best) hit = n;                               \
            last = value;                                                        \
        }                                                                        \
        printf("%-10s: ", variant);                                              \
        if (hit >= 0) {                                                          \
            TYPE value = NAME##_plain(hit);                                      \
            printf("N=%d で best, err=", hit);                                   \
            print_error((__float128)value - (__float128)best);                   \
        } else {                                                                 \
            printf("N<=%d では見つからず, err=", max_n);                         \
            print_error((__float128)last - (__float128)best);                    \
        }                                                                        \
        putchar('\n');                                                           \
    }

DEFINE_AGM_VARIANTS(decimal64, _Decimal64, 1.0dd, 2.0dd, 4.0dd, 3.141592653589793dd,
                    decimal64_sqrt_plain)
DEFINE_AGM_VARIANTS(double64, double, 1.0, 2.0, 4.0, 4 * atan(1.0), sqrt)
DEFINE_AGM_VARIANTS(longdouble, long double, 1.0L, 2.0L, 4.0L, 4 * atanl(1.0L), sqrtl)
DEFINE_AGM_VARIANTS(decimal128, _Decimal128, 1.0dl, 2.0dl, 4.0dl,
                    3.1415926535897932384626433832795028dl, decimal128_sqrt_plain)
DEFINE_AGM_PLAIN_ONLY(decimal64_half, _Decimal64, 1.0dd, 2.0dd, 4.0dd, 3.141592653589793dd,
                      decimal64_sqrt_half)
DEFINE_AGM_PLAIN_ONLY(decimal128_half, _Decimal128, 1.0dl, 2.0dl, 4.0dl,
                      3.1415926535897932384626433832795028dl, decimal128_sqrt_half)
DEFINE_AGM_VARIANTS(float128, __float128, 1.0Q, 2.0Q, 4.0Q, 4 * atanq(1.0Q), sqrtq)

DEFINE_AGM_FMA(double64, double, 1.0, 2.0, 4.0, 4 * atan(1.0), sqrt, fma)
DEFINE_AGM_FMA(longdouble, long double, 1.0L, 2.0L, 4.0L, 4 * atanl(1.0L), sqrtl, fmal)
DEFINE_AGM_FMA(float128, __float128, 1.0Q, 2.0Q, 4.0Q, 4 * atanq(1.0Q), sqrtq, fmaq)

static void probe_decimal64(int max_n) {
    puts("[_Decimal64]");
    decimal64_report("plain", decimal64_plain, max_n);
    decimal64_report("t_split", decimal64_t_split, max_n);
    decimal64_report("final_half", decimal64_final_half, max_n);
    decimal64_report("combo", decimal64_combo, max_n);
    decimal64_half_report("sqrt_half", max_n);
    puts("");
}

static void probe_double(int max_n) {
    puts("[double]");
    double64_report("plain", double64_plain, max_n);
    double64_report("t_split", double64_t_split, max_n);
    double64_report("final_half", double64_final_half, max_n);
    double64_report("combo", double64_combo, max_n);
    double64_report_fma(max_n);
    puts("");
}

static void probe_longdouble(int max_n) {
    puts("[long double]");
    longdouble_report("plain", longdouble_plain, max_n);
    longdouble_report("t_split", longdouble_t_split, max_n);
    longdouble_report("final_half", longdouble_final_half, max_n);
    longdouble_report("combo", longdouble_combo, max_n);
    longdouble_report_fma(max_n);
    puts("");
}

static void probe_decimal128(int max_n) {
    puts("[_Decimal128]");
    decimal128_report("plain", decimal128_plain, max_n);
    decimal128_report("t_split", decimal128_t_split, max_n);
    decimal128_report("final_half", decimal128_final_half, max_n);
    decimal128_report("combo", decimal128_combo, max_n);
    decimal128_half_report("sqrt_half", max_n);
    puts("");
}

static void probe_float128(int max_n) {
    puts("[__float128]");
    float128_report("plain", float128_plain, max_n);
    float128_report("t_split", float128_t_split, max_n);
    float128_report("final_half", float128_final_half, max_n);
    float128_report("combo", float128_combo, max_n);
    float128_report_fma(max_n);
    puts("");
}

int main(int argc, char **argv) {
    int max_n = 20;
    if (argc >= 2) {
        max_n = atoi(argv[1]);
        if (max_n < 0) max_n = 0;
    }
    probe_decimal64(max_n);
    probe_double(max_n);
    probe_longdouble(max_n);
    probe_decimal128(max_n);
    probe_float128(max_n);
    return 0;
}
