#include <math.h>
#include <quadmath.h>
#include <stdio.h>

static void print_error(__float128 diff) {
    char buf[64];
    quadmath_snprintf(buf, sizeof(buf), "%+.3Qe", diff);
    fputs(buf, stdout);
}

#define DEFINE_HORNER_PROBE(NAME, TYPE, BEST_EXPR, ONE, TWO, THREE, FOUR, FIVE,  \
                            EIGHT, ELEVEN, SIXTEEN, TWO_THIRTY_NINE)           \
    static TYPE NAME##_atan_series(int terms, TYPE x) {                         \
        TYPE y = (TYPE)0;                                                       \
        for (int i = terms; i >= 1; --i) {                                      \
            TYPE c = (i % 2 == 0) ? -(ONE) : (ONE);                             \
            y = c / ((TWO) * (TYPE)i - (ONE)) + x * x * y;                      \
        }                                                                       \
        return x * y;                                                           \
    }                                                                           \
    static TYPE NAME##_machin_asymmetric(void) {                                \
        return (SIXTEEN) * NAME##_atan_series(12, (ONE) / (FIVE)) -             \
               (FOUR) * NAME##_atan_series(3, (ONE) / (TWO_THIRTY_NINE));       \
    }                                                                           \
    static TYPE NAME##_rational2(void) {                                        \
        return (FOUR) * NAME##_atan_series(23, (FIVE) / (ELEVEN)) +             \
               (FOUR) * NAME##_atan_series(18, (THREE) / (EIGHT));             \
    }                                                                           \
    static TYPE NAME##_rational2_all(void) {                                    \
        return (FOUR) * NAME##_atan_series(23, (TYPE)11 / (TYPE)54) +           \
               (FOUR) * NAME##_atan_series(89, (TYPE)43 / (TYPE)65);           \
    }                                                                           \
    static void probe_##NAME(const char *label) {                               \
        TYPE best = (BEST_EXPR);                                                \
        TYPE machin = NAME##_machin_asymmetric();                               \
        TYPE rational2 = NAME##_rational2();                                    \
        TYPE rational2_all = NAME##_rational2_all();                            \
        printf("[%s]\n", label);                                                \
        printf("asymmetric: %s, err=", machin == best ? "best" : "not-best");   \
        print_error((__float128)machin - (__float128)best);                     \
        putchar('\n');                                                          \
        printf("rational2 : %s, err=", rational2 == best ? "best" : "not-best");\
        print_error((__float128)rational2 - (__float128)best);                  \
        putchar('\n');                                                          \
        printf("rational2-all: %s, err=",                                      \
               rational2_all == best ? "best" : "not-best");                   \
        print_error((__float128)rational2_all - (__float128)best);              \
        putchar('\n');                                                          \
        puts("");                                                              \
    }

DEFINE_HORNER_PROBE(decimal64, _Decimal64, 3.141592653589793dd, 1.0dd, 2.0dd,
                    3.0dd, 4.0dd, 5.0dd, 8.0dd, 11.0dd, 16.0dd, 239.0dd)
DEFINE_HORNER_PROBE(double64, double, M_PI, 1.0, 2.0, 3.0, 4.0, 5.0, 8.0, 11.0,
                    16.0, 239.0)
DEFINE_HORNER_PROBE(longdouble, long double, 4.0L * atanl(1.0L), 1.0L, 2.0L,
                    3.0L, 4.0L, 5.0L, 8.0L, 11.0L, 16.0L, 239.0L)
DEFINE_HORNER_PROBE(decimal128, _Decimal128,
                    3.1415926535897932384626433832795028dl, 1.0dl, 2.0dl,
                    3.0dl, 4.0dl, 5.0dl, 8.0dl, 11.0dl, 16.0dl, 239.0dl)
DEFINE_HORNER_PROBE(float128, __float128, M_PIq, 1.0Q, 2.0Q, 3.0Q, 4.0Q, 5.0Q,
                    8.0Q, 11.0Q, 16.0Q, 239.0Q)

int main(void) {
    probe_decimal64("_Decimal64");
    probe_double64("double");
    probe_longdouble("long double");
    probe_decimal128("_Decimal128");
    probe_float128("__float128");
    return 0;
}
