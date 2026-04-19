#include <math.h>
#include <quadmath.h>
#include <stdio.h>

static const unsigned decimal64_terms[] = {
    3, 7, 15, 1, 292, 1, 1, 1, 2, 1, 3, 1, 14, 4, 2, 3, 1, 12, 5, 1,
    5, 20, 1, 11, 1, 1, 1, 2,
};

static const unsigned double_terms[] = {
    3, 7, 15, 1, 292, 1, 1, 1, 2, 1, 3, 1, 14, 3, 3, 2, 1, 3, 3, 7,
    2, 1, 1, 3, 2, 42, 2,
};

static const unsigned longdouble_terms[] = {
    3, 7, 15, 1, 292, 1, 1, 1, 2, 1, 3, 1, 14, 2, 1, 1, 2, 2, 2, 1,
    1, 1, 1, 3, 3, 2, 4, 15, 10, 1, 16, 1, 1, 28, 1, 17,
};

static const unsigned decimal128_terms[] = {
    3, 7, 15, 1, 292, 1, 1, 1, 2, 1, 3, 1, 14, 2, 1, 1, 2, 2, 2, 2,
    1, 84, 2, 1, 1, 15, 3, 13, 1, 4, 2, 8, 2, 1, 1, 1, 1, 1, 2, 1,
    2, 1, 7, 1, 2, 1, 1, 1, 1, 1, 1, 4, 1, 77, 1, 2, 1, 7, 32, 1,
    1, 9, 1, 3, 13, 5, 2, 10, 2,
};

static const unsigned float128_terms[] = {
    3, 7, 15, 1, 292, 1, 1, 1, 2, 1, 3, 1, 14, 2, 1, 1, 2, 2, 2, 2,
    1, 84, 2, 1, 1, 15, 3, 13, 1, 4, 2, 8, 2, 8, 7, 1, 1, 47, 20, 10,
    2, 28, 3, 3, 5, 5, 9, 1, 1, 1, 1, 1, 1, 53, 1, 5,
};

static void print_error(__float128 diff) {
    char buf[64];
    quadmath_snprintf(buf, sizeof(buf), "%+.3Qe", diff);
    fputs(buf, stdout);
}

#define DEFINE_FOUROPS_PROBE(NAME, TYPE, BEST_EXPR, TERMS)                       \
    static void probe_##NAME(const char *title) {                                \
        TYPE best = (BEST_EXPR);                                                 \
        unsigned long long p_nm2 = 0, p_nm1 = 1;                                 \
        unsigned long long q_nm2 = 1, q_nm1 = 0;                                 \
        int limit = (int)(sizeof(TERMS) / sizeof(TERMS[0]));                     \
        int hit = -1;                                                            \
        unsigned long long hit_p = 0, hit_q = 0;                                 \
        TYPE last = 0;                                                           \
        for (int n = 0; n < limit; ++n) {                                        \
            unsigned long long a = TERMS[n];                                     \
            unsigned long long p = a * p_nm1 + p_nm2;                            \
            unsigned long long q = a * q_nm1 + q_nm2;                            \
            TYPE value = (TYPE)p / (TYPE)q;                                      \
            if (hit < 0 && value == best) {                                      \
                hit = n;                                                         \
                hit_p = p;                                                       \
                hit_q = q;                                                       \
                last = value;                                                    \
                break;                                                           \
            }                                                                    \
            last = value;                                                        \
            p_nm2 = p_nm1;                                                       \
            p_nm1 = p;                                                           \
            q_nm2 = q_nm1;                                                       \
            q_nm1 = q;                                                           \
        }                                                                        \
        printf("[%s]\n", title);                                                 \
        if (hit >= 0) {                                                          \
            printf("N=%d で best, %llu/%llu, err=", hit, hit_p, hit_q);          \
            print_error((__float128)((TYPE)hit_p / (TYPE)hit_q) -                \
                        (__float128)best);                                       \
        } else {                                                                 \
            printf("N<%d では見つからず, err=", limit);                           \
            print_error((__float128)last - (__float128)best);                    \
        }                                                                        \
        putchar('\n');                                                           \
        puts("");                                                                \
    }

DEFINE_FOUROPS_PROBE(decimal64, _Decimal64, 3.141592653589793dd, decimal64_terms)
DEFINE_FOUROPS_PROBE(double64, double, 4 * atan(1.0), double_terms)
DEFINE_FOUROPS_PROBE(longdouble, long double, 4 * atanl(1.0L), longdouble_terms)
DEFINE_FOUROPS_PROBE(
    decimal128,
    _Decimal128,
    3.1415926535897932384626433832795028dl,
    decimal128_terms
)
DEFINE_FOUROPS_PROBE(float128, __float128, 4 * atanq(1.0Q), float128_terms)

int main(void) {
    probe_decimal64("_Decimal64");
    probe_double64("double");
    probe_longdouble("long double");
    probe_decimal128("_Decimal128");
    probe_float128("__float128");
    return 0;
}
