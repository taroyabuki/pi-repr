# exact best の有限連分数

ここでは， $\pi$ の連分数ではなく，各処理系の **exact best** を有理数とみなしたときの有限連分数を使います．

つまり，stage 1 の `best` が

$$
x_\mathrm{best} = \frac{r}{s}
$$

と書けるなら，その有限連分数

$$
x_\mathrm{best} = [a_0; a_1, \ldots, a_N]
$$

を作り，まず有限連分数を有理数 `p/q` に直し，その後で `p/q` を評価して，「exact best がどこで再現されるか」を調べます．

ここで finite な連分数を使っているので，最後まで評価すれば数学的には必ず exact best です．したがって，この節で見ているのは

- 何項目まで進めると `p/q` の評価結果が best に戻るか

です．比較対象として見るべき有理数は exact best そのものではなく，「その最小の `N` に対応する有限連分数の値」です．分母最小の有理数探索は，ここでは扱わず [best-rational/README.md](../best-rational/README.md) に分けます．

## 連分数とは何か

実数 $x$ を

$$
x = [a_0; a_1, a_2, \ldots]
$$

の形に書いたものを連分数と呼びます．ここで $a_0$ は整数， $a_1, a_2, \ldots$ は正の整数です．係数は，整数部分を取り，残りの小数部分の逆数を取り，その整数部分をまた取る，という操作を繰り返すと得られます．つまり

$$
x_0=x,\quad a_n=\lfloor x_n \rfloor,\quad x_{n+1}=\frac{1}{x_n-a_n}
$$

です．

有限打ち切り

$$
[a_0;a_1,\ldots,a_N]
$$

は，逆順に

$$
a_0+\cfrac{1}{a_1+\cfrac{1}{a_2+\cfrac{1}{\ddots+\cfrac{1}{a_N}}}}
$$

と評価できます．こうして得られる

$$
[a_0;a_1,\ldots,a_n]=\frac{p_n}{q_n}
$$

を収束子と呼びます．収束子 $p_n/q_n$ を前から作るなら

$$
p_n=a_n p_{n-1}+p_{n-2},\qquad q_n=a_n q_{n-1}+q_{n-2}
$$

を使います．初期値は

$$
p_{-2}=0,\quad p_{-1}=1,\qquad q_{-2}=1,\quad q_{-1}=0
$$

です．

例えば

$$
[3;7,15,1,292]
=3+\cfrac{1}{7+\cfrac{1}{15+\cfrac{1}{1+\cfrac{1}{292}}}}
$$

で，この有限連分数の最後の収束子は `103993/33102` です．

## 係数列

係数列は [exact_best_terms.py](exact_best_terms.py) で確認できます．

```bash
python3 continued-fractions/exact_best_terms.py
```

主な形式の exact best と有限連分数の項数は次のとおりです．

| 形式 | exact best | 項数 | 主な処理系 |
| --- | --- | ---: | --- |
| small FP | `13176795/4194304` | 10 | 6502 BASIC, Grant BASIC |
| BCD double | `31415926535898/10^13` | 25 | MSX-BASIC |
| MBF double | `28296951008113761/2^53` | 31 | BASIC-80, N-BASIC, N88-BASIC, F-BASIC, GW-BASIC |
| IEEE 754 binary64 | `884279719003555/2^48` | 27 | C `double`, QBasic |
| x87 80-bit | `14488038916154245685/2^62` | 36 | C `long double` |
| `__float128` | `1019505104126898525104217885171767/324518553658426726783156020576256` | 56 | C `__float128` |
| `_Decimal64` | `3141592653589793/10^15` | 28 | C `_Decimal64` |
| `_Decimal128` | `31415926535897932384626433832795028/10^34` | 69 | C `_Decimal128` |

最初の数項は多くの形式で $\pi$ の連分数と一致しますが，どこかで finite な末尾に切り替わります．例えば

- small FP: `[3;7,15,1,435,1,2,1,6,3]`
- MBF double: `[3;7,15,1,292,1,1,1,2,1,3,1,14,2,1,1,1,3,2,2,274,2,1,1,5,4,2,1,1,1,7]`
- QBasic / `double`: `[3;7,15,1,292,1,1,1,2,1,3,1,14,3,3,2,1,3,3,7,2,1,1,3,2,42,2]`

となります．

## 調査結果

### C言語（x86_64, GNU gcc）

[C-fourops.c](C-fourops.c) は，各型の exact best の有限連分数から収束子 `p/q` を作り，`p/q` を直接評価して，最初に best に戻る `N` を調べます．

| 型 | finite CF の項数 | `p/q` 評価で最初に best になる `N` | そのときの有理数 |
| --- | ---: | ---: | --- |
| `_Decimal64` | 28 | 12 | `80143857/25510582` |
| `double` | 27 | 13 | `245850922/78256779` |
| `long double` | 36 | 19 | `8717442233/2774848045` |
| `_Decimal128` | 69 | 30 | `66627445592888887/21208174623389167` |
| `__float128` | 56 | 31 | `563265837776847017/179293084713965674` |

`double` は exact best の連分数自体は 27 項ありますが，`p/q` 評価では `N=13` で既に `245850922/78256779` に当たります．`_Decimal128` も同様に `N=30` で `66627445592888887/21208174623389167` に当たります．

実は，`__float128` には，ここで最初に見つかるものよりよい有理数があります．それは [best-rational/README.md](../best-rational/README.md) で扱います．

### BASIC

まず，`p/q` 評価だけを各処理系で調べると次のとおりです．

| BASIC | finite CF の項数 | `p/q` 評価で最初に best になる `N` | そのときの有理数 |
| --- | ---: | ---: | --- |
| 6502 BASIC | 10 | 4 | `154758/49261` |
| BASIC-80 | 31 | 16 | `657408909/209259755` |
| N-BASIC | 31 | 16 | `657408909/209259755` |
| N88-BASIC | 31 | 16 | `657408909/209259755` |
| FM-7 F-BASIC | 31 | 16 | `657408909/209259755` |
| FM-11 BASIC | 31 | 16 | `657408909/209259755` |
| MSX-BASIC | 25 | 13 | `2012767689/640683854` |
| GW-BASIC | 31 | 16 | `657408909/209259755` |
| QBasic | 27 | 13 | `245850922/78256779` |
| Grant BASIC | 10 | 4 | `154758/49261` |

small FP と MBF double では，finite CF 全体はそれぞれ 10 項，31 項ありますが，実際の計算ではかなり早い段階で exact best に戻ります．MSX-BASIC では，入れ子評価で出ていた `5419351/1725033` ではなく，`p/q` 評価では `2012767689/640683854` が最初に best に入ります．

実は，6502，MSX，Grant には，ここで最初に見つかるものよりよい有理数があります．それらは [best-rational/README.md](../best-rational/README.md) で扱います．

## $\pi$ の既知の連分数をそのまま使うと

ここまでは，各処理系の exact best を有理数と見たときの **finite CF** を使っていました．これに対して，既知の

$$
\pi=[3;7,15,1,292,1,1,1,2,1,3,1,14,2,1,1,2,2,2,2,1,84,\ldots]
$$

の収束子

$$
\frac{p_n}{q_n}=[a_0;a_1,\ldots,a_n]
$$

をそのまま評価すると，「最後まで行けば必ず exact best」という保証はもうありません．この場合に見るのは，

- 真の $\pi$ の収束子 `p_n/q_n` を評価したとき，最初に best に入る `N` があるか

だけです．

C と，half-ulp / nearest model で説明できる BASIC 系では次のとおりです．

| 対象 | $\pi$ CF で最初に best になる `N` | その収束子 |
| --- | ---: | --- |
| small FP（6502 BASIC, Grant BASIC） | 4 | `103993/33102` |
| MBF double（BASIC-80, N-BASIC, N88-BASIC, FM-7 F-BASIC, FM-11 BASIC, GW-BASIC） | 16 | `1068966896/340262731` |
| IEEE 754 binary64（C `double`, QBasic） | 14 | `245850922/78256779` |
| x87 80-bit（C `long double`） | 19 | `14885392687/4738167652` |
| C `_Decimal64` | 12 | `80143857/25510582` |
| C `_Decimal128` | 30 | `66627445592888887/21208174623389167` |
| C `__float128` | 31 | `430010946591069243/136876735467187340` |

`_Decimal64` と `_Decimal128` は，best に当たる `N` が， $\pi$ の係数列と exact best の finite CF がまだ一致している範囲にあるので，結果は前節と同じです．一方，small FP，MBF double，`double` / QBasic，`long double`，`__float128` では， $\pi$ の収束子をそのまま使うと，最初に当たる有理数が前節とは変わります．

MSX-BASIC だけは別です．naive な BCD half-ulp では `N=11` の `5419351/1725033` が候補になりますが，actual にはこれは `MISS` です．したがって MSX-BASIC では， $\pi$ の既知収束子をそのまま使うだけでは，この README で使っている simple な nearest-rounding の説明では best 到達を扱えません．この点は [best/README.md](../best/README.md) と [best-rational/README.md](../best-rational/README.md) のとおりです．

## 確認

```bash
python3 continued-fractions/exact_best_terms.py

gcc -std=gnu2x continued-fractions/C-fourops.c -lm -lquadmath -o /tmp/cf
timeout 300 /tmp/cf

timeout 300 ../classic-basic/run/6502.sh --run --file continued-fractions/6502-fourops.bas
timeout 300 ../classic-basic/run/basic80.sh --run --file continued-fractions/basic80-fourops.bas
timeout 300 ../classic-basic/run/nbasic.sh --run --file continued-fractions/nbasic-fourops.bas
timeout 300 ../classic-basic/run/n88basic.sh --run --file continued-fractions/n88basic-fourops.bas
timeout 300 ../classic-basic/run/n88basic.sh --run --file continued-fractions/mbf-nested.bas
timeout 300 ../classic-basic/run/fm7basic.sh --run --file continued-fractions/fm-mbf-nested.bas
timeout 600 ../classic-basic/run/fm11basic.sh --run --file continued-fractions/fm11basic-fourops.bas
timeout 300 ../classic-basic/run/msxbasic.sh --run --file continued-fractions/msxbasic-fourops.bas
timeout 300 ../classic-basic/run/gwbasic.sh --run --file continued-fractions/gwbasic-fourops.bas
timeout 300 ../classic-basic/run/qbasic.sh --run --file continued-fractions/qbasic-fourops.bas
timeout 300 ../classic-basic/run/grantsbasic.sh --run --file continued-fractions/grantsbasic-fourops.bas
```
