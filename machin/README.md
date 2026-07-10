# Machin の公式

ここでは Machin の公式

$$
\pi=16\arctan\left(\frac{1}{5}\right)-4\arctan\left(\frac{1}{239}\right)
$$

で，計算だけから各処理系の best に届くかを調べます．結論は次のとおりです．

- 組み込み `arctan` / `ATN` をそのまま使うだけでは，best に届く処理系と届かない処理系がある．
- 両方の `arctan` を同じ項数まで計算する方法は，[以前の記事](https://taroyabuki.github.io/2024/04/12/digits-of-pi-to-memorize/) の FM-11 F-BASIC の例や，FM-7 F-BASIC で `^` をループ計算に置き換える例ではうまく行く．しかし一般にはかなり脆い．
- Machin の左右で項数を変える非対称な打ち切りにすると，small FP，MBF double，BCD double の BASIC ではかなりうまく行く．ただし，QBasic と C `double` の binary64 では best の 1 ulp 上に外れる．
- C `double` まで同じ形で best に落とすなら，別の 2 項 arctan 公式を使う方が安定する．`long double`，`_Decimal128`，`__float128` まで含めるなら，さらに項数と有理数を選び直す必要がある．

C 言語については，ここでの結果は x86_64-linux-gnu，GCC 13.3.0（Ubuntu 13.3.0-6ubuntu2~24.04.1），glibc 2.39 で確認した実装上の挙動です．この環境の `long double` は，格納サイズ 16 バイト，仮数精度 64 ビットの x87 extended precision です．C 言語仕様そのものが `double` や `long double` を IEEE 754 の特定形式にすることを一般に要求しているわけではありません．また，浮動小数点形式，丸め，数学ライブラリ関数の挙動は，アーキテクチャ，ABI，実装，コンパイルオプションに依存します．ARM など別のアーキテクチャでは，特に `long double` や `__float128` の扱いが同じになるとは限りません．

## 組み込み `arctan`

まず，Machin の公式を組み込み `arctan` / `ATN` でそのまま評価すると次のようになります．確認コードは [C-builtin.c](./code/C-builtin.c) と [bas/](./bas/) の `*-builtin.bas` で，collector は [collect_builtin.py](./code/collect_builtin.py) です．

```bash
cd /root/work/pi-repr
python3 machin/code/collect_builtin.py
```

| 処理系 | 結果 | メモ |
| --- | --- | --- |
| C `double` | best と不一致 | best の 1 ulp 上 |
| C `long double` | best と一致 | x87 80-bit では直接届く |
| C `__float128` | best と不一致 | best の 1 ulp 上 |
| C `_Decimal64` | 対象外 | 対応する `atan` がない |
| C `_Decimal128` | 対象外 | 対応する `atan` がない |
| 6502 BASIC | best と一致 | small FP では直接届く |
| BASIC-80 | best と不一致 | `ATN` の精度が足りない |
| N-BASIC | best と不一致 | `ATN` が単精度 |
| N88-BASIC | best と不一致 | N-BASIC と同じ側に落ちる |
| F-BASIC | best と不一致 | FM-7 / FM-11 とも不一致 |
| MSX-BASIC | best と一致 | BCD double では直接届く |
| GW-BASIC | best と不一致 | `ATN` の精度が足りない |
| QBasic | best と不一致 | best の 1 ulp 上 |
| Grant BASIC | best と一致 | small FP では直接届く |

Machin の公式そのものは良い公式ですが，「組み込み関数を呼ぶだけ」で best に届くとは限りません．以下では `arctan` を Maclaurin 展開に置き換えます．

以下の BASIC コード例は，特に断らない限り `DEFDBL` と `#` 付き double literal が使える BASIC-80，N-BASIC，N88-BASIC，FM-7 F-BASIC，FM-11 F-BASIC，MSX-BASIC，GW-BASIC，QBasic 向けの形で書きます．6502 BASIC と Grant BASIC には `DEFDBL` や `#` 付き double literal がないため，`DEFDBL` を削除し，`#` を外し，`MOD` を使う偶奇判定を `I/2=INT(I/2)` のように直す修正が必要です．

## 共通項数

`arctan(x)` の Maclaurin 展開の先頭 `K` 項を

$$
A_K(x)=\sum_{k=0}^{K-1}\frac{(-1)^k x^{2k+1}}{2k+1}
$$

と書くと，もっとも素直な打ち切りは

$$
16A_K\left(\frac15\right)-4A_K\left(\frac{1}{239}\right)
$$

です．`arctan(1/5)` と `arctan(1/239)` の両方を同じ項数まで計算するので，ここではこれを「共通項数」と呼びます．

共通項数の実験では，次の 4 通りの評価形を区別します．

$$
a_k=\frac{(-1)^k(1/5)^{2k+1}}{2k+1},\qquad
b_k=\frac{(-1)^k(1/239)^{2k+1}}{2k+1}
\quad(0\le k<K)
$$

とします．`TERM` は同じ次数の項をその場で合成してから足します．

$$
16a_k-4b_k
$$

を各 $k$ で作って，それを合計する形です．一方，`SPLIT` は左右の arctan を別々に合計してから，最後に

$$
16\sum a_k-4\sum b_k
$$

を作る形です．`LOW` と `HIGH` は加算順序を表します．`LOW` は `k=0,1,...,K-1` の低次側から足し，`HIGH` は `k=K-1,K-2,...,0` の高次側から足します．したがって `SPLITLOW` は「左右を別々に，それぞれ低次から足して，最後に `16S-4T` を作る」方式です．同様に `TERMLOW`，`TERMHIGH`，`SPLITHIGH` も，評価形と加算順序を組み合わせた名前です．

交代級数の次項評価を使うと，tail がその型の 1 ulp 程度より小さくなる項数を見積もれます．たとえば MBF double ではおおむね `K=12`，binary64 ではおおむね `K=11` です．この見積もりは，打ち切り誤差だけを見るには有用です．しかし途中の丸め，べき乗 `^` の精度，加算順序は含みません．

この方法は成功例もあります．[以前の記事](https://taroyabuki.github.io/2024/04/12/digits-of-pi-to-memorize/) の「④ 木村本（マチンの公式＋マクローリン展開）」では，木村本の `PAI 1986.9.1` のコードを，`K=12`，`X=1/239#`，`FOR I=K TO 1 STEP -1` に直すと FM-11 F-BASIC で best に届くことを確認しています．ここでも，その修正版の形を使います．

このコードは，`GOSUB 190` で `arctan(X)` の Maclaurin 展開を 12 項計算し，最初の結果を `Z` に退避してから，最後に `16*Z-4*Y` を作ります．`FOR I=K TO 1 STEP -1` なので，高次の項から低次の項へ足す `SPLITHIGH` 型の計算です．FM-11 F-BASIC と MSX-BASIC では，次の同じコードで best に届きます．確認用のファイルは [common-count-pow-common.bas](./bas/common-count-pow-common.bas) です．

```basic
100 REM ***** PAI 1986.9.1
110 DEFDBL X,Y,Z
120 K=12
130 X=.2#
140 GOSUB 190
150 Z=Y
160 X=1/239#
170 GOSUB 190
180 PRINT 16*Z-4*Y
185 END
190 REM *** arctan
200 Y=0
210 FOR I=K TO 1 STEP -1
220 J=2*I-1
222 IF I MOD 2 =0 GOTO 235
230 Y=Y+X^J/J:GOTO 240
235 Y=Y-X^J/J
240 NEXT I
250 RETURN
```

FM-7 F-BASIC と N-BASIC では `^` の精度が足りないため，このままでは best に届きません．同じ木村本コードの構造を保ったまま `X^J` だけを掛け算ループに置き換えると，両方で同じソースを実行できます．ただし，この移植版は FM-7 F-BASIC では best になる一方，N-BASIC では best になりません．したがって FM-7 F-BASIC と N-BASIC の共通 best コードにはなりません．確認用のファイルは [common-count-loop-port.bas](./bas/common-count-loop-port.bas) です．

```basic
100 REM ***** PAI 1986.9.1
110 DEFDBL P,X,Y,Z
120 K=12
130 X=.2#
140 GOSUB 190
150 Z=Y
160 X=1/239#
170 GOSUB 190
180 PRINT 16*Z-4*Y
185 END
190 REM *** arctan
200 Y=0
210 FOR I=K TO 1 STEP -1
220 J=2*I-1
222 GOSUB 260
224 IF I MOD 2 =0 GOTO 235
230 Y=Y+P/J:GOTO 240
235 Y=Y-P/J
240 NEXT I
250 RETURN
260 P=1#
270 FOR L=1 TO J
280 P=P*X
290 NEXT L
300 RETURN
```

一方で，この方法は処理系をまたいだ共通解にはなりません．このリポジトリの probe では，次のような結果になりました．

| 系統 | 共通項数での状況 |
| --- | --- |
| FM-11 F-BASIC | `^` を使う高次側の和で best に届く |
| FM-7 F-BASIC | `^` を避けてループでべき乗を作ると best に届く |
| MSX-BASIC | 高次側の和で best に届く |
| N88-BASIC | 高次側の和で best に届く |
| 6502 BASIC / Grant BASIC | `SPLITLOW` で best に届く |
| BASIC-80 / N-BASIC / GW-BASIC | 近くまでは行くが best には届かない |
| QBasic / C `double` | binary64 の best には届かない |

## 非対称 Machin

そこで，左右の項数を変えます．

$$
16A_{12}\left(\frac15\right)-4A_3\left(\frac{1}{239}\right)
$$

を Horner 形で評価し，BASIC コードではその近似値を変数 `A` に入れます．ここでいう Horner 形とは，$A_K(x)$ を $x^2$ の多項式として入れ子に評価する書き方です．

$$
A_K(x)=x\left(c_1+x^2\left(c_2+x^2\left(\cdots+x^2c_K\right)\right)\right),
\qquad
c_i=\frac{(-1)^{i-1}}{2i-1}
$$

つまり，次の漸化式を後ろから計算します．

$$
Y_{K+1}=0,\qquad
Y_i=c_i+x^2Y_{i+1}\quad(i=K,K-1,\ldots,1),\qquad
A_K(x)=xY_1
$$

この形にすると，`x^3`, `x^5`, ... を `^` で直接作らず，`X*X*Y` の繰り返しだけで済みます．ただし，実数としては同じ有限和でも，有限精度では「低次から足す」「高次から足す」「べき乗を作って足す」と丸め経路が違います．この違いが最後の 1 ulp に効くことがあります．

BASIC では次の形です．

```basic
10 DEFDBL A-H,N-Z
20 K=12:X=1#/5#:GOSUB 200:U=Y
30 K=3:X=1#/239#:GOSUB 200:V=Y
40 A=16#*U-4#*V
50 PRINT A
60 END
200 Y=0
210 FOR I=K TO 1 STEP -1
220 C=1#:IF I MOD 2=0 THEN C=-1#
230 Y=C/(2#*I-1#)+X*X*Y
240 NEXT I
250 Y=X*Y
260 RETURN
```

このコードは，BASIC-80，N-BASIC，N88-BASIC，FM-7 F-BASIC，FM-11 F-BASIC，MSX-BASIC，GW-BASIC，QBasic ではそのまま実行できます．ただし，QBasic では実行はできますが best にはならず，結果は best の 1 ulp 上になります．

この形は，確認した BASIC では次のようになりました．small FP，MBF double，BCD double では best に届きますが，QBasic の binary64 では 1 ulp 上に外れます．

| 処理系 | 形式 | 非対称 Machin |
| --- | --- | --- |
| 6502 BASIC | small FP | best と一致 |
| BASIC-80 | MBF double | best と一致 |
| N-BASIC | MBF double | best と一致 |
| N88-BASIC | MBF double | best と一致 |
| FM-7 F-BASIC | MBF double | best と一致 |
| FM-11 F-BASIC | MBF double | best と一致 |
| MSX-BASIC | BCD double | best と一致 |
| GW-BASIC | MBF double | best と一致 |
| QBasic | IEEE 754 binary64 | best と不一致，1 ulp 上 |
| Grant BASIC | small FP | best と一致 |

補足すると，N-BASIC ではこの非対称 Machin で best に届きますが，これを理解するには Maclaurin 展開，Horner 形，打ち切り誤差，途中丸めをまとめて考える必要があります．中学生・高校生くらいなら，むしろ「正解の値がどのバイト列になるかを理解し，リテラルとして入力した値がどのバイト列になるかを調べ，必要ならそのバイト列を書き換える」という手順の方が見通しやすいかもしれません．

確認には [generic-horner.bas](./bas/generic-horner.bas)，[fbasic-horner.bas](./bas/fbasic-horner.bas)，[n88basic-horner.bas](./bas/n88basic-horner.bas)，[6502-horner.bas](./bas/6502-horner.bas)，[qbasic-horner.bas](./bas/qbasic-horner.bas)，[grantsbasic-horner.bas](./bas/grantsbasic-horner.bas) を使いました．Grant BASIC の byte 列確認は [collect_grantsbasic_horner.py](./code/collect_grantsbasic_horner.py) で host 側から変数領域を見ています．

なぜ `A_3(1/239)` で止めるのが効くかというと，この問題で欲しいのは「実数として最も $\pi$ に近い有限和」ではなく，「各処理系の丸め経路を通ったあと best に落ちる値」だからです．N-BASIC の MBF double を例にすると，target を \(T\) としたとき，実数としての有限和は次の位置にあります．

| 左の項数 | 右の項数 | \((A-T)/\operatorname{ulp}\) | N-BASIC の先頭 byte |
| ---: | ---: | ---: | --- |
| 11 | 3 | `+0.989` | `C5` |
| 12 | 3 | `-0.0623` | `C2` |
| 12 | 4 | `+0.169` | `C4` |
| 13 | 3 | `-0.0236` | `C2` |

右側を 4 項に増やすと実数としては $\pi$ に近づきます．しかし MBF の丸め経路では target の上側へ出てしまい，`C2` ではなく `C4` になります．項数を増やせば必ず良くなるわけではありません．

## binary64への対応

QBasic の binary64 でも best にしたいなら，Machin の公式そのものではなく，次の 2 項 arctan 公式を使います．

$$
\arctan\frac{5}{11}+\arctan\frac{3}{8}=\arctan 1=\frac{\pi}{4}
$$

実際，

$$
\frac{\frac{5}{11}+\frac{3}{8}}{1-\frac{5}{11}\frac{3}{8}}=1
$$

なので，

$$
\pi=4\arctan\frac{5}{11}+4\arctan\frac{3}{8}
$$

です．Horner 形で

$$
4A_{23}\left(\frac5{11}\right)+4A_{18}\left(\frac38\right)
$$

を計算すると，確認した BASIC では QBasic まで含めて best に一致しました．BASIC-80，N-BASIC，N88-BASIC，FM-7 F-BASIC，FM-11 F-BASIC，MSX-BASIC，GW-BASIC，QBasic では，次の同じコードを実行できます．確認用のファイルは [binary64-common.bas](./bas/binary64-common.bas) です．

```basic
10 DEFDBL A-H,N-Z
20 K=23:X=5#/11#:GOSUB 200:U=Y
30 K=18:X=3#/8#:GOSUB 200:V=Y
40 A=4#*U+4#*V
50 PRINT A
60 END
200 Y=0
210 FOR I=K TO 1 STEP -1
220 C=1#:IF I MOD 2=0 THEN C=-1#
230 Y=C/(2#*I-1#)+X*X*Y
240 NEXT I
250 Y=X*Y
260 RETURN
```

| 処理系 | 2 項 arctan 公式 |
| --- | --- |
| 6502 BASIC | best と一致 |
| BASIC-80 | best と一致 |
| N-BASIC | best と一致 |
| N88-BASIC | best と一致 |
| FM-7 F-BASIC | best と一致 |
| FM-11 F-BASIC | best と一致 |
| MSX-BASIC | best と一致 |
| GW-BASIC | best と一致 |
| QBasic | best と一致 |
| Grant BASIC | best と一致 |

C では `_Decimal64` と `double` で best に一致します．一方，`long double`，`_Decimal128`，`__float128` ではこの項数では足りず，best には届きません．

| C の型 | 2 項 arctan 公式 | bestとの差 |
| --- | --- | --- |
| `_Decimal64` | best と一致 | `+0.000e+00` |
| `double` | best と一致 | `+0.000e+00` |
| `long double` | best と不一致 | `-1.063e-17` |
| `_Decimal128` | best と不一致 | `-1.082e-17` |
| `__float128` | best と不一致 | `-1.082e-17` |

## 全対象を含める場合

`long double`，`_Decimal128`，`__float128` まで含めるなら，`5/11` と `3/8` のまま項数を増やすだけでは BASIC-80 や N-BASIC の丸め経路で外れます．そこで，同じ 2 項 arctan 公式の範囲で有理数も探し直します．

使う式は

$$
\arctan\frac{11}{54}+\arctan\frac{43}{65}=\arctan 1=\frac{\pi}{4}
$$

です．実際，

$$
\frac{\frac{11}{54}+\frac{43}{65}}{1-\frac{11}{54}\frac{43}{65}}=1
$$

なので，

$$
\pi=4\arctan\frac{11}{54}+4\arctan\frac{43}{65}
$$

です．Horner 形で

$$
4A_{23}\left(\frac{11}{54}\right)+4A_{89}\left(\frac{43}{65}\right)
$$

を計算すると，ここで扱っているすべての BASIC と C の型で best に一致しました．BASIC-80，N-BASIC，N88-BASIC，FM-7 F-BASIC，FM-11 F-BASIC，MSX-BASIC，GW-BASIC，QBasic では，次の同じコードを実行できます．確認用のファイルは [all-targets-common.bas](./bas/all-targets-common.bas) です．

```basic
10 DEFDBL A-H,N-Z
20 K=23:X=11#/54#:GOSUB 200:U=Y
30 K=89:X=43#/65#:GOSUB 200:V=Y
40 A=4#*U+4#*V
50 PRINT A
60 END
200 Y=0
210 FOR I=K TO 1 STEP -1
220 C=1#:IF I MOD 2=0 THEN C=-1#
230 Y=C/(2#*I-1#)+X*X*Y
240 NEXT I
250 Y=X*Y
260 RETURN
```

Horner 形を使わず，Maclaurin 展開の項をそのまま足す素朴な方法も探しましたが，QBasic 以外の BASIC で同じ式・同じ評価順・そのままコピペできる共通コードとして使えるものは見つかりませんでした．たとえば small FP では低次側から左右を別々に足す形が当たりやすい一方，MBF double や BCD double では高次側から足す形や同じ次数の項を合成する形が当たりやすく，丸め経路の相性がそろいませんでした．したがって，ここでは共通解として Horner 形を採用します．

| 系統 | 全対象用 2 項 arctan 公式 |
| --- | --- |
| 6502 BASIC | best と一致 |
| BASIC-80 | best と一致 |
| N-BASIC | best と一致 |
| N88-BASIC | best と一致 |
| FM-7 F-BASIC | best と一致 |
| FM-11 F-BASIC | best と一致 |
| MSX-BASIC | best と一致 |
| GW-BASIC | best と一致 |
| QBasic | best と一致 |
| Grant BASIC | best と一致 |
| C `_Decimal64` | best と一致 |
| C `double` | best と一致 |
| C `long double` | best と一致 |
| C `_Decimal128` | best と一致 |
| C `__float128` | best と一致 |

確認コードは [C-horner.c](./code/C-horner.c) と各 `*-horner.bas` の `RATIONAL2ALL` です．C 側の候補探索には [C-rational2-search.c](./code/C-rational2-search.c) を使いました．

この結果は，「項数を増やすと悪くなる」という話と矛盾しません．悪くなるのは，項数が多いこと自体ではなく，実数としての有限和が各形式の best の丸め区間から外れること，または途中丸めで外れることです．Machin の非対称打ち切りでは，右側を 3 項から 4 項へ増やすだけで有限和が MBF の target の上側へ動き，結果の先頭 byte が `C2` から `C4` に変わりました．

一方，全対象用の式では，`long double`，`_Decimal128`，`__float128` まで見るために，高精度側の ulp に合わせて tail を小さくする必要があります．そのため項数は `23` と `89` まで増えます．実数としての

$$
4A_{23}\left(\frac{11}{54}\right)+4A_{89}\left(\frac{43}{65}\right)
$$

は $\pi$ より約 `3.9e-34` 大きい値です．これは small FP，MBF double，BCD double，binary64 から見ると十分に小さい差です．高精度の C 型では丸め区間と同じ桁の差になりますが，この候補は実数近似だけで選んだのではなく，各型の Horner 評価の途中丸めまで含めて best へ落ちるものを探索した結果です．

したがって，ここで効いているのは「項数を多くすれば必ず良い」ではなく，「必要な精度まで tail を小さくしたうえで，丸め経路込みで best の側に落ちる公式と項数を選ぶ」ということです．低精度の BASIC にとって `89` 項は過剰ですが，この式ではその過剰な項が target の丸め区間から押し出す方向には働きません．

この節の結論は，Machin 型の公式が悪いということではありません．むしろ，有限精度で best を狙うときは，数学的な収束の速さだけでなく，処理系ごとの丸め経路まで込みで式を選ぶ必要がある，ということです．
