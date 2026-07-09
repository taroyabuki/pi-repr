
# best の確定

## best の値

### 2進数

2 進浮動小数点では，値を
$$x=\pm m\times 2^e$$

の形に正規化して表します． $\pi$ については
$$\pi=11.001001000011111101101010100010001000010110100011\ldots{}_2$$

なので，
$$\pi=1.1001001000011111101101010100010001000010110100011\ldots{}_2\times 2^1$$

となります．したがって，2 進浮動小数点の形式ではまず指数は 1 に決まります．違いは，その後ろの 2 進小数列をどこまで仮数として持ち，残りをどう丸めるかです．

C では 16 進浮動小数点リテラル `0x...p...` でも 2 進浮動小数点数を直接書けます．`0x` の後ろが 16 進の仮数，`p` の後ろが 2 の指数です．たとえば `0x1.8p+1` は $1.8_{16}\times2^1=1.5\times2^1=3$ を表します．同じ値は `0x3p+0` や `0xCp-2` とも書けます．つまり，普通は正規化して `0x1.xxxp...` の形で書くことが多いだけで，同じ値を別の 16 進仮数と指数の組で書くこともできます．これは 10 進でも同じで，たとえば `3e0`, `30e-1`, `300e-2` はすべて同じ値です．

ただし，16 進浮動小数点リテラルはメモリ上の byte 列そのものではありません．正規化した数値の仮数 bit を 16 進で書く表記です．IEEE 754 binary 形式では先頭の `1` は通常格納されず，x87 80-bit extended precision ではその `1` も仮数に格納されます．

`x87 80-bit extended precision` だけは，正規化そのものは他の 2 進形式と同じですが，正規化後の先頭の `1` を省略せずに明示的に持ちます．他の IEEE 754 binary 形式では，この `1` は通常は省略されます．

### 10進数

10 進浮動小数点では，値を 10 進で正規化して，決まった桁数だけ仮数を持ちます．違いは，その有効桁数と丸め方です．たとえば $\pi$ は
$$0.31415926535897932\ldots\times10^1$$

と書けるので，decimal64 や decimal128，MSX-BASIC の BCD double では，この 10 進仮数をそれぞれの桁数に丸めて best を決めます．

主な形式について，指数部と仮数部の大きさ，best の byte 列，10進表現， $\pi$ と一致する小数桁数， $\pi$ との差をまとめると次のとおりです．byte 列はこのリポジトリの確認コードが表示する順で，メモリ上の順とは違う場合もあります．2 進形式の 10 進表現は， $\pi$ と一致する部分を太字にし，その右に 2 桁だけ残しています．10 進形式（`BCD double`, `decimal64`, `decimal128`）は有限小数で exact な値を書けるので，表でもその値を最後まで書いています．

| 形式 | 指数部 | 仮数部 | best のバイト表現 | best の10進表現 | 一致 | $\pi$ との差 |
| --- | --- | --- | --- | --- | --: | --- |
| small FP | `1 byte` | `3 byte` | `82 49 0F DB` | **3.141592**74 | 6 | `+8.74E-08` |
| BCD double | `1 byte` | `7 byte` | `41 31 41 59 26 53 58 98` | **3.141592653589**8 | 12 | `+6.76E-15` |
| decimal64 | `16 digits` | `16 digits` | `21 6D 25 0A 43 29 EB 2F` | **3.141592653589793** | 15 | `-2.38E-16` |
| double | `11 bit` | `52 bit` | `18 2D 44 54 FB 21 09 40` | **3.141592653589793**11 | 15 | `-1.22E-16` |
| MBF double | `1 byte` | `7 byte` | `C2 68 21 A2 DA 0F 49 82` | **3.1415926535897932**27 | 16 | `-1.14E-17` |
| long double | `15 bit` | `64 bit` | `35 C2 68 21 A2 DA 0F C9 00 40 00 00 00 00 00 00` | **3.141592653589793238**51 | 18 | `+5.02E-20` |
| `__float128` | `15 bit` | `112 bit` | `B8 01 17 C5 8C 89 69 84 D1 42 44 B5 1F 92 00 40` | **3.141592653589793238462643383279502**79 | 33 | `-8.67E-35` |
| decimal128 | `34 digits` | `34 digits` | `8F 9F F3 E6 64 55 BE BA A7 96 57 79 E4 9A FE 2F` | **3.1415926535897932384626433832795028** | 34 | `-8.42E-35` |

best の確定方法を，small FP・BCD double・MBF double を例に説明します．他の形式も，基本的な考え方は同じです．

### small FP

6502 BASIC と Grant BASIC で使っている small FP は，表のとおり指数部 1 byte，仮数部 3 byte の 4-byte float です． $\pi$ では指数は 1 で，best の仮数は
$$1.10010010000111111011011{}_2$$

です．よって best の値は
$$1.10010010000111111011011{}_2\times 2^1=\dfrac{13176795}{2^{22}}$$

となります．これは約 **3.141592**74 で， $\pi$ と小数第6位まで一致します．

### BCD double

MSX-BASIC で使っている BCD double は，表のとおり指数部 1 byte，仮数部 7 byte の 8-byte float です．

$\pi$ を正規化形式 $0.31415926535897932...\times 10^1$ で書いたとき，14 桁の仮数に丸めると
$$0.31415926535898 \times 10^1$$

となります（15 桁目が 9 なので切り上げ）．よって best の値は
$$\dfrac{31415926535898}{10^{13}} = 3.1415926535898$$

となります．これは約 **3.141592653589**80 で， $\pi$ と小数第12位まで一致します．

### MBF double

BASIC-80・N-BASIC・N88-BASIC・F-BASIC・GW-BASIC で使っている MBF double は，表のとおり指数部 1 byte，仮数部 7 byte の 8-byte float です．

MBF double は IEEE 754 binary 形式と違って，正規化した値を
$$x=\pm 0.1b_1b_2\ldots b_{55}{}_2\times 2^e$$

の形で持ちます．つまり，先頭の `1` は小数点の左ではなく，`2^{-1}` の桁に明示的に入ります．

$\pi$ は
$$\pi=0.110010010000111111011010101000100010000101101000110001\ldots{}_2\times 2^2$$

と書けるので，MBF double では指数は 2 に決まります．16 進では
$$\pi=0.\mathrm{C90FDAA22168C23}\ldots_{16}\times 2^2$$

ですから，56 bit の仮数に丸めた best は
$$0.\mathrm{C90FDAA22168C2}_{16}\times 2^2$$

となります（次の 16 進桁が `3` なので切り上げは起こらない）．表の byte 列 `C2 68 21 A2 DA 0F 49 82` は，この仮数 `C90FDAA22168C2` を下位 byte から並べ，最後に指数 byte `82` を付けたものです．

よって best の値は
$$0.\mathrm{C90FDAA22168C2}_{16}\times 2^2=\dfrac{28296951008113761}{2^{53}}$$

となります．これは約 **3.1415926535897932**27 で， $\pi$ と小数第16位まで一致します．

他の形式で特に注意が必要なのは次です．

- `BCD double`: 2 進ではなく 10 進の仮数を持つので， $\pi$ も 10 進で正規化して丸めます．
- `MBF double`: IEEE 754 binary と違って，正規化した仮数は `0.1..._2\times 2^e` の形で持ちます． $\pi$ の best は `0.C90FDAA22168C2_{16}\times 2^2` です．
- `double`: C では 16 進浮動小数点リテラル `0x1.921fb54442d18p+1` でも best を直接書けます．
- `long double`: x87 80-bit では正規化後の先頭の `1` を省略せずに明示的に持ちます．C では正規化表記 `0x1.921fb54442d1846ap+1L` や，読みやすい表記 `0x3.243f6a8885a308d4p+0L` でも best を直接書けます．
- `__float128`: C では `0x1.921FB54442D18469898CC51701B8p+1Q` でも best を直接書けます．
- `decimal64`, `decimal128`: 2 進ではなく 10 進で正規化して，有効桁数に丸めます．

## best の値を得る方法

### C言語（x86_64, GNU gcc）

| 型 | best になる書き方（文字数の少ない順） |
| --- | --- |
| `_Decimal64` | `(_Decimal64)M_PI`<br>`3.141592653589793dd`<br>`80143857.dd/25510582`<br>`(_Decimal64)(4*atan(1))` |
| `double` | `M_PI`<br>`4*atan(1)`<br>`3.141592653589793`<br>`245850922./78256779`<br>`0x1.921fb54442d18p+1` |
| `long double` | `4*atanl(1)`<br>`3.1415926535897932385L`（小数第20位を四捨五入）<br>`3.14159265358979323846L`<br>`0x1.921fb54442d1846ap+1L`<br>`8717442233.L/2774848045` |
| `__float128` | `M_PIq`<br>`4*atanq(1)`<br>`0x1.921FB54442D18469898CC51701B8p+1Q`<br>`3.1415926535897932384626433832795028Q`<br>`363383500998180356.Q/115668560843798173` |
| `_Decimal128` | `3.141592653589793238462643383279503dl`（小数第34位を四捨五入）<br>`3.1415926535897932384626433832795028dl`<br>`66627445592888887.dl/21208174623389167` |

確認:

```bash
gcc -std=gnu2x best/C-lang.c -lm -lquadmath -o /tmp/verify-best-c
/tmp/verify-best-c
```

### BASIC

| BASIC | best になる書き方（文字数の少ない順） |
| --- | --- |
| 6502 BASIC | `4*ATN(1)`<br>`3.1415927`（小数第8位を四捨五入）<br>`93343/29712` |
| BASIC-80 | `657408909/209259755`<br>`A#=3.14159265358979#:POKE VARPTR(A#),&HC2` |
| N-BASIC | `657408909#/209259755#`（分母・分子の両方に `#` が必要）<br>`A#=3.14159265358979#:POKE VARPTR(A#),&HC2` |
| N88-BASIC | `657408909/209259755`<br>`A=3.14159265358979#:POKE VARPTR(A),&HC2` |
| F-BASIC | `657408909/209259755`<br>`A=3.14159265358979#:POKE VARPTR(A)+7,&HC2` |
| MSX-BASIC | `4*ATN(1)`<br>`3.1415926535898`（小数第14位を四捨五入）<br>`3.14159265358979`<br>`10838702/3450066`（約分した `5419351/1725033` は不可） |
| GW-BASIC | `3.1415926535897932#`<br>`657408909/209259755` |
| QBasic | `4*ATN(1)`<br>`3.141592653589793`<br>`245850922/78256779` |
| Grant BASIC | `3.1415927`（小数第8位を四捨五入）<br>`93343/29712` |

補足:

- BASIC-80・N-BASIC・N88-BASIC・F-BASIC では，10 進リテラルだけでは best を直接書けません．
- N-BASIC では `DEFDBL A-Z` なしでも `A#` のように `#` 付き変数を使えます．小数や分数の両辺に `#` を明示した方が安全です．
- F-BASIC の `PEEK(VARPTR(...)+offset)` は MBF double の表示順と逆向きで，ここで書き換えている `+7` はメモリ上の最後の byte です．
- FM-7 BASIC と FM-11 BASIC は F-BASIC にまとめています．`best/fm7basic.bas` と `best/fm11basic.bas` はどちらも `MATCH OK` / `ATN GT` を返します．
- QBasic では，候補をいったん `C#` に代入してから比較します．
- Grant BASIC は，`4*ATN(1)` が `DC 0F 49 82` でした（best なら最初が `DB`）．`VARPTR` は使い物にならず，byte 列は host-side inspection で確認しました．

確認:

```bash
timeout 60s ../classic-basic/run/6502.sh --run --file best/6502.bas
timeout 60s ../classic-basic/run/basic80.sh --run --file best/basic80.bas
timeout 60s ../classic-basic/run/nbasic.sh --run --file best/nbasic.bas
timeout 60s ../classic-basic/run/n88basic.sh --run --file best/n88basic.bas
timeout 60s ../classic-basic/run/fm7basic.sh --run --file best/fm7basic.bas
timeout 60s ../classic-basic/run/fm11basic.sh --run --file best/fm11basic.bas
timeout 60s ../classic-basic/run/msxbasic.sh --run --file best/msxbasic.bas
timeout 60s ../classic-basic/run/gwbasic.sh --run --file best/gwbasic.bas
timeout 60s ../classic-basic/run/qbasic.sh --run --file best/qbasic.bas
timeout 60s ../classic-basic/run/grantsbasic.sh --run --file best/grantsbasic.bas
```
