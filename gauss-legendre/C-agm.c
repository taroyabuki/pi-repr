#include <math.h>
#include <quadmath.h>
#include <stdio.h>
#include <stdlib.h>

static void print_bytes(const void *ptr, size_t n) {
    const unsigned char *p = (const unsigned char *)ptr;
    for (size_t i = 0; i < n; ++i) {
        printf("%u%s", (unsigned)p[i], i + 1 == n ? "\n" : " ");
    }
}

static void print_error(__float128 diff) {
    char buf[64];
    quadmath_snprintf(buf, sizeof(buf), "%+.3Qe", diff);
    fputs(buf, stdout);
}

static __float128 absq(__float128 x) {
    return x < 0 ? -x : x;
}

#define DEFINE_NEWTON_SQRT(NAME, TYPE, ONE, TWO)                                 \
    static TYPE NAME##_sqrt(TYPE x) {                                            \
        TYPE guess = x > (ONE) ? x : (ONE);                                      \
        for (int i = 0; i < 80; ++i) {                                           \
            TYPE next = (guess + x / guess) / (TWO);                             \
            if (next == guess) break;                                            \
            guess = next;                                                        \
        }                                                                        \
        return guess;                                                            \
    }

DEFINE_NEWTON_SQRT(decimal64, _Decimal64, 1.0dd, 2.0dd)
DEFINE_NEWTON_SQRT(decimal128, _Decimal128, 1.0dl, 2.0dl)

#define DEFINE_AGM_PROBE(NAME, TYPE, ONE, TWO, FOUR, BEST_EXPR, SQRTFUNC)        \
    static TYPE NAME##_pi(int n) {                                               \
        TYPE a = (ONE);                                                          \
        TYPE b = (ONE) / SQRTFUNC((TWO));                                        \
        TYPE t = (ONE) / (FOUR);                                                 \
        TYPE p = (ONE);                                                          \
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
            TYPE s = a + b;                                                      \
            return s * s / ((FOUR) * t);                                         \
        }                                                                        \
    }                                                                            \
    static void probe_##NAME(const char *label, int max_n) {                     \
        TYPE best = (BEST_EXPR);                                                 \
        TYPE chosen = NAME##_pi(0);                                              \
        int chosen_n = 0;                                                        \
        __float128 best_abs = absq((__float128)chosen - (__float128)best);       \
        for (int n = 1; n <= max_n; ++n) {                                       \
            TYPE value = NAME##_pi(n);                                           \
            __float128 diff = (__float128)value - (__float128)best;              \
            __float128 current_abs = absq(diff);                                 \
            if (current_abs < best_abs) {                                        \
                chosen = value;                                                  \
                chosen_n = n;                                                    \
                best_abs = current_abs;                                          \
            }                                                                    \
        }                                                                        \
        printf("[%s]\n", label);                                                 \
        puts("BEST");                                                            \
        print_bytes(&best, sizeof(best));                                        \
        printf("AGM %d\n", chosen_n);                                            \
        print_bytes(&chosen, sizeof(chosen));                                    \
        print_error((__float128)chosen - (__float128)best);                      \
        putchar('\n');                                                           \
        puts("");                                                                \
    }

DEFINE_AGM_PROBE(decimal64, _Decimal64, 1.0dd, 2.0dd, 4.0dd, 3.141592653589793dd,
                 decimal64_sqrt)
DEFINE_AGM_PROBE(double64, double, 1.0, 2.0, 4.0, 4 * atan(1.0), sqrt)
DEFINE_AGM_PROBE(longdouble, long double, 1.0L, 2.0L, 4.0L, 4 * atanl(1.0L), sqrtl)
DEFINE_AGM_PROBE(decimal128, _Decimal128, 1.0dl, 2.0dl, 4.0dl,
                 3.141592653589793238462643383279503dl, decimal128_sqrt)
DEFINE_AGM_PROBE(float128, __float128, 1.0Q, 2.0Q, 4.0Q, 4 * atanq(1.0Q), sqrtq)

int main(int argc, char **argv) {
    int max_n = 8;
    if (argc >= 2) {
        max_n = atoi(argv[1]);
        if (max_n < 0) max_n = 0;
    }
    probe_decimal64("_Decimal64", max_n);
    probe_double64("double", max_n);
    probe_longdouble("long double", max_n);
    probe_decimal128("_Decimal128", max_n);
    probe_float128("__float128", max_n);
    return 0;
}
