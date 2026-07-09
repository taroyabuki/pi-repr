#include <math.h>
#include <quadmath.h>
#include <stdio.h>
#include <string.h>

union ld_repr {
    long double value;
    unsigned char bytes[sizeof(long double)];
};

static void print_bytes(const void *ptr, size_t n) {
    const unsigned char *p = (const unsigned char *)ptr;
    for (size_t i = 0; i < n; ++i) {
        printf("%u%s", (unsigned)p[i], i + 1 == n ? "\n" : " ");
    }
}

int main(void) {
    _Decimal64 d64_best = (_Decimal64)M_PI;
    _Decimal64 d64_short = 3.14159265358979dd;
    _Decimal64 d64_lit = 3.141592653589793dd;
    printf("[_Decimal64 short]\n");
    print_bytes(&d64_short, sizeof(d64_short));
    printf("%d\n", d64_short == d64_best);
    printf("[_Decimal64]\n");
    print_bytes(&d64_lit, sizeof(d64_lit));
    printf("%d\n\n", d64_lit == d64_best);

    double d_best = M_PI;
    double d_short = 3.14159265358979;
    double d_lit = 3.141592653589793;
    printf("[double short]\n");
    print_bytes(&d_short, sizeof(d_short));
    printf("%d\n", d_short == d_best);
    printf("[double]\n");
    print_bytes(&d_lit, sizeof(d_lit));
    printf("%d\n\n", d_lit == d_best);

    long double ld_best = 4 * atanl(1);
    union ld_repr ld_short18;
    union ld_repr ld_short19;
    union ld_repr ld_round;
    union ld_repr ld_lit;
    memset(&ld_short18, 0, sizeof(ld_short18));
    memset(&ld_short19, 0, sizeof(ld_short19));
    memset(&ld_round, 0, sizeof(ld_round));
    memset(&ld_lit, 0, sizeof(ld_lit));
    ld_short18.value = 3.141592653589793238L;
    ld_short19.value = 3.1415926535897932384L;
    ld_round.value = 3.1415926535897932385L;
    ld_lit.value = 3.14159265358979323846L;
    printf("[long double short18]\n");
    print_bytes(ld_short18.bytes, sizeof(ld_short18.bytes));
    printf("%d\n", ld_short18.value == ld_best);
    printf("[long double short19]\n");
    print_bytes(ld_short19.bytes, sizeof(ld_short19.bytes));
    printf("%d\n", ld_short19.value == ld_best);
    printf("[long double rounded]\n");
    print_bytes(ld_round.bytes, sizeof(ld_round.bytes));
    printf("%d\n", ld_round.value == ld_best);
    printf("[long double literal]\n");
    print_bytes(ld_lit.bytes, sizeof(ld_lit.bytes));
    printf("%d\n\n", ld_lit.value == ld_best);

    _Decimal128 d128_best = 3.1415926535897932384626433832795028dl;
    _Decimal128 d128_cut32 = 3.14159265358979323846264338327950dl;
    _Decimal128 d128_cut33 = 3.141592653589793238462643383279502dl;
    _Decimal128 d128_round33 = 3.141592653589793238462643383279503dl;
    _Decimal128 d128_pi34 = 3.1415926535897932384626433832795028dl;
    printf("[_Decimal128 cut32]\n");
    print_bytes(&d128_cut32, sizeof(d128_cut32));
    printf("%d\n", d128_cut32 == d128_best);
    printf("[_Decimal128 cut33]\n");
    print_bytes(&d128_cut33, sizeof(d128_cut33));
    printf("%d\n", d128_cut33 == d128_best);
    printf("[_Decimal128 round33]\n");
    print_bytes(&d128_round33, sizeof(d128_round33));
    printf("%d\n", d128_round33 == d128_best);
    printf("[_Decimal128 pi34]\n");
    print_bytes(&d128_pi34, sizeof(d128_pi34));
    printf("%d\n\n", d128_pi34 == d128_best);

    __float128 q_best = M_PIq;
    __float128 q_cut33 = 3.141592653589793238462643383279502Q;
    __float128 q_round33 = 3.141592653589793238462643383279503Q;
    __float128 q_lit = 3.1415926535897932384626433832795028Q;
    printf("[__float128 cut33]\n");
    print_bytes(&q_cut33, sizeof(q_cut33));
    printf("%d\n", q_cut33 == q_best);
    printf("[__float128 round33]\n");
    print_bytes(&q_round33, sizeof(q_round33));
    printf("%d\n", q_round33 == q_best);
    printf("[__float128]\n");
    print_bytes(&q_lit, sizeof(q_lit));
    printf("%d\n", q_lit == q_best);
    return 0;
}
