#include <stdio.h>
#include <math.h>
#include <quadmath.h>

static int failures = 0;

static void report(const char *label, int ok) {
    printf("%-16s : %s\n", label, ok ? "OK" : "NG");
    if (!ok) {
        failures = 1;
    }
}

static void print_bytes(const void *ptr, size_t n) {
    const unsigned char *p = (const unsigned char *)ptr;
    for (size_t i = 0; i < n; ++i) {
        printf("%u%s", (unsigned)p[i], i + 1 == n ? "\n" : " ");
    }
}

int main(void) {
    _Decimal64 a_d64 = (_Decimal64)M_PI;
    printf("[_Decimal64] bytes: ");
    print_bytes(&a_d64, sizeof(a_d64));
    report("d64 literal", a_d64 == 3.141592653589793dd);
    report("d64 atan", a_d64 == (_Decimal64)(4 * atan(1)));
    report("d64 rational", a_d64 == 80143857.dd / 25510582);
    puts("");

    double a_double = M_PI;
    printf("[double] bytes: ");
    print_bytes(&a_double, sizeof(a_double));
    report("double atan", a_double == 4 * atan(1));
    report("double literal", a_double == 3.141592653589793);
    report("double hex", a_double == 0x1.921fb54442d18p+1);
    report("double rational", a_double == 245850922. / 78256779);
    puts("");

    long double a_ld = 4 * atanl(1);
    printf("[long double] bytes: ");
    print_bytes(&a_ld, sizeof(a_ld));
    report("ld hex", a_ld == 0xC.90FDAA22168C235p-2L);
    report("ld rounded", a_ld == 3.1415926535897932385L);
    report("ld literal", a_ld == 3.14159265358979323846L);
    report("ld rational", a_ld == 8717442233.L / 2774848045);
    puts("");

    _Decimal128 a_d128 = 3.1415926535897932384626433832795028dl;
    printf("[_Decimal128] bytes: ");
    print_bytes(&a_d128, sizeof(a_d128));
    report(
        "d128 rounded",
        a_d128 == 3.141592653589793238462643383279503dl
    );
    report(
        "d128 rational",
        a_d128 == 66627445592888887.dl / 21208174623389167
    );
    puts("");

    __float128 a_q = M_PIq;
    printf("[__float128] bytes: ");
    print_bytes(&a_q, sizeof(a_q));
    report("q atan", a_q == 4 * atanq(1));
    report("q hex", a_q == 0x1.921FB54442D18469898CC51701B8p+1Q);
    report("q literal", a_q == 3.1415926535897932384626433832795028Q);
    report("q rational", a_q == 363383500998180356.Q / 115668560843798173);

    return failures;
}
