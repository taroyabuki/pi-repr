#include <math.h>
#include <quadmath.h>
#include <stdio.h>
#include <stdlib.h>

static void print_error(__float128 diff) {
    char buf[64];
    quadmath_snprintf(buf, sizeof(buf), "%+.3Qe", diff);
    fputs(buf, stdout);
}

#define DEFINE_POW_PROBE(NAME, TYPE, BEST_EXPR, X1, X2, POWFN)                   \
    static TYPE NAME##_term_low(int n) {                                         \
        TYPE x1 = (X1);                                                          \
        TYPE x2 = (X2);                                                          \
        TYPE sum = 0;                                                            \
        for (int k = 0; k <= n; ++k) {                                           \
            int exp = 2 * k + 1;                                                 \
            TYPE den = (TYPE)exp;                                                \
            TYPE term1 = POWFN(x1, exp);                                         \
            TYPE term2 = POWFN(x2, exp);                                         \
            if (k & 1) {                                                         \
                term1 = -term1;                                                  \
                term2 = -term2;                                                  \
            }                                                                    \
            sum += (TYPE)16 * term1 / den - (TYPE)4 * term2 / den;              \
        }                                                                        \
        return sum;                                                              \
    }                                                                            \
    static TYPE NAME##_term_high(int n) {                                        \
        TYPE *terms = malloc((size_t)(n + 1) * sizeof(TYPE));                    \
        if (terms == NULL) {                                                     \
            fprintf(stderr, "allocation failed\n");                              \
            exit(1);                                                             \
        }                                                                        \
        TYPE x1 = (X1);                                                          \
        TYPE x2 = (X2);                                                          \
        for (int k = 0; k <= n; ++k) {                                           \
            int exp = 2 * k + 1;                                                 \
            TYPE den = (TYPE)exp;                                                \
            TYPE term1 = POWFN(x1, exp);                                         \
            TYPE term2 = POWFN(x2, exp);                                         \
            if (k & 1) {                                                         \
                term1 = -term1;                                                  \
                term2 = -term2;                                                  \
            }                                                                    \
            terms[k] = (TYPE)16 * term1 / den - (TYPE)4 * term2 / den;          \
        }                                                                        \
        TYPE sum = 0;                                                            \
        for (int k = n; k >= 0; --k) {                                           \
            sum += terms[k];                                                     \
        }                                                                        \
        free(terms);                                                             \
        return sum;                                                              \
    }                                                                            \
    static TYPE NAME##_split_low(int n) {                                        \
        TYPE x1 = (X1);                                                          \
        TYPE x2 = (X2);                                                          \
        TYPE sum1 = 0;                                                           \
        TYPE sum2 = 0;                                                           \
        for (int k = 0; k <= n; ++k) {                                           \
            int exp = 2 * k + 1;                                                 \
            TYPE den = (TYPE)exp;                                                \
            TYPE term1 = POWFN(x1, exp);                                         \
            TYPE term2 = POWFN(x2, exp);                                         \
            if (k & 1) {                                                         \
                term1 = -term1;                                                  \
                term2 = -term2;                                                  \
            }                                                                    \
            sum1 += term1 / den;                                                 \
            sum2 += term2 / den;                                                 \
        }                                                                        \
        return (TYPE)16 * sum1 - (TYPE)4 * sum2;                                 \
    }                                                                            \
    static TYPE NAME##_split_high(int n) {                                       \
        TYPE *terms1 = malloc((size_t)(n + 1) * sizeof(TYPE));                   \
        TYPE *terms2 = malloc((size_t)(n + 1) * sizeof(TYPE));                   \
        if (terms1 == NULL || terms2 == NULL) {                                  \
            fprintf(stderr, "allocation failed\n");                              \
            free(terms1);                                                        \
            free(terms2);                                                        \
            exit(1);                                                             \
        }                                                                        \
        TYPE x1 = (X1);                                                          \
        TYPE x2 = (X2);                                                          \
        for (int k = 0; k <= n; ++k) {                                           \
            int exp = 2 * k + 1;                                                 \
            TYPE den = (TYPE)exp;                                                \
            TYPE term1 = POWFN(x1, exp);                                         \
            TYPE term2 = POWFN(x2, exp);                                         \
            if (k & 1) {                                                         \
                term1 = -term1;                                                  \
                term2 = -term2;                                                  \
            }                                                                    \
            terms1[k] = term1 / den;                                             \
            terms2[k] = term2 / den;                                             \
        }                                                                        \
        TYPE sum1 = 0;                                                           \
        TYPE sum2 = 0;                                                           \
        for (int k = n; k >= 0; --k) {                                           \
            sum1 += terms1[k];                                                   \
            sum2 += terms2[k];                                                   \
        }                                                                        \
        free(terms1);                                                            \
        free(terms2);                                                            \
        return (TYPE)16 * sum1 - (TYPE)4 * sum2;                                 \
    }                                                                            \
    static void NAME##_report(const char *tag, TYPE (*fn)(int), TYPE best,       \
                              int max_n) {                                       \
        TYPE last = fn(0);                                                       \
        int hit = -1;                                                            \
        for (int n = 0; n <= max_n; ++n) {                                       \
            TYPE current = fn(n);                                                \
            if (hit < 0 && current == best) hit = n;                             \
            last = current;                                                      \
        }                                                                        \
        if (hit >= 0) {                                                          \
            TYPE current = fn(hit);                                              \
            printf("%-9s: N=%d で best, err=", tag, hit);                        \
            print_error((__float128)current - (__float128)best);                 \
            putchar('\n');                                                       \
        } else {                                                                 \
            printf("%-9s: N<=%d では見つからず, err=", tag, max_n);               \
            print_error((__float128)last - (__float128)best);                    \
            putchar('\n');                                                       \
        }                                                                        \
    }                                                                            \
    static void probe_##NAME(const char *label, int max_n) {                     \
        TYPE best = (BEST_EXPR);                                                 \
        printf("[%s]\n", label);                                                 \
        NAME##_report("TERMLOW", NAME##_term_low, best, max_n);                  \
        NAME##_report("TERMHIGH", NAME##_term_high, best, max_n);                \
        NAME##_report("SPLITLOW", NAME##_split_low, best, max_n);                \
        NAME##_report("SPLITHIGH", NAME##_split_high, best, max_n);              \
        puts("");                                                                \
    }

DEFINE_POW_PROBE(double64, double, 4 * atan(1.0), 0.2, 1.0 / 239.0, pow)
DEFINE_POW_PROBE(longdouble, long double, 4 * atanl(1.0L), 0.2L, 1.0L / 239.0L,
                 powl)
DEFINE_POW_PROBE(float128, __float128, 4 * atanq(1.0Q), 0.2Q, 1.0Q / 239.0Q,
                 powq)

int main(int argc, char **argv) {
    int max_n = 40;
    if (argc >= 2) {
        max_n = atoi(argv[1]);
        if (max_n < 0) max_n = 0;
    }
    probe_double64("double", max_n);
    probe_longdouble("long double", max_n);
    probe_float128("__float128", max_n);
    return 0;
}
