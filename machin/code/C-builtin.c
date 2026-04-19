#include <math.h>
#include <quadmath.h>
#include <stdio.h>

static void print_bytes(const void *ptr, size_t n) {
    const unsigned char *p = (const unsigned char *)ptr;
    for (size_t i = 0; i < n; ++i) {
        printf("%u%s", (unsigned)p[i], i + 1 == n ? "\n" : " ");
    }
}

int main(void) {
    double best_d = M_PI;
    double machin_d = 16.0 * atan(0.2) - 4.0 * atan(1.0 / 239.0);
    long double best_ld = 4.0L * atanl(1.0L);
    long double machin_ld = 16.0L * atanl(0.2L) - 4.0L * atanl(1.0L / 239.0L);
    __float128 best_q = M_PIq;
    __float128 machin_q = 16.0Q * atanq(0.2Q) - 4.0Q * atanq(1.0Q / 239.0Q);

    puts("[double]");
    puts("BEST");
    print_bytes(&best_d, sizeof(best_d));
    puts("MACHIN");
    print_bytes(&machin_d, sizeof(machin_d));
    printf("%.17e\n", machin_d - best_d);

    puts("[long double]");
    puts("BEST");
    print_bytes(&best_ld, sizeof(best_ld));
    puts("MACHIN");
    print_bytes(&machin_ld, sizeof(machin_ld));
    printf("%.21Le\n", machin_ld - best_ld);

    puts("[__float128]");
    puts("BEST");
    print_bytes(&best_q, sizeof(best_q));
    puts("MACHIN");
    print_bytes(&machin_q, sizeof(machin_q));
    char buf[128];
    quadmath_snprintf(buf, sizeof(buf), "%+.36Qe", machin_q - best_q);
    puts(buf);

    return 0;
}
