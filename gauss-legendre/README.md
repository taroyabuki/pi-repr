# Gauss-Legendre（AGM）

Machin の公式の次の段階として，Gauss-Legendre 法（AGM）で $\pi$ を作るとどうなるかを調べます．ここで使う標準形は，初期値

$$
a_0=1,\quad b_0=\frac{1}{\sqrt{2}},\quad t_0=\frac14,\quad p_0=1
$$

から始めて，

$$
a_{n+1}=\frac{a_n+b_n}{2},\quad
b_{n+1}=\sqrt{a_n b_n},\quad
t_{n+1}=t_n-p_n(a_n-a_{n+1})^2,\quad
p_{n+1}=2p_n
$$

と更新し，最後に

$$
\pi_n=\frac{(a_n+b_n)^2}{4t_n}
$$

で $\pi$ の近似を得るものです．

ここでは各処理系について `N=0,1,2,...` を試し，`|π_N-best|` が最初に最小になる `N` を載せます．

## C言語（x86_64, GNU gcc）

確認コードは [C-agm.c](./C-agm.c)，collector は [collect_c.py](./collect_c.py) です．

```bash
cd /root/work/pi-repr
python3 gauss-legendre/collect_c.py
```

| 型 | 最初の最良 `N` | Gauss-Legendre | bestとの差 | メモ |
| --- | --- | --- | --- | --- |
| `_Decimal64` | `N=3` | best と不一致 | `-2.000e-15` | best の 2 ulp 下 |
| `double` | `N=3` | best と不一致 | `+8.882e-16` | best の 2 ulp 上 |
| `long double` | `N=3` | best と一致 | `+0.000e+00` | x87 80-bit では 3 回で best |
| `_Decimal128` | `N=4` | best と不一致 | `-1.156e-33` | best の 1 ulp 下 |
| `__float128` | `N=4` | best と不一致 | `+3.852e-34` | best の 1 ulp 上 |

標準形では `long double` だけが直接 best に届き，他の型は best の 1 ulp か 2 ulp ずれたところで止まります．補助実験として [C-agm-techniques.c](./C-agm-techniques.c) で，`t=t-p*d*d` を `t=t-(p*d)*d` に分ける，最後を `s=(a+b)/2, π=s*s/t` と書く，その両方を入れる，といった工夫も試しましたが，C では `_Decimal64` が少し良くなる程度で，ほとんど改善しませんでした．

## BASIC

確認コードは [`gauss-legendre/`](./) にあります．collector は [collect.py](./collect.py) です．

```bash
cd /root/work/pi-repr
python3 gauss-legendre/collect.py
```

| BASIC | 最初の最良 `N` | Gauss-Legendre | バイト列 | bestとの差 | メモ |
| --- | --- | --- | --- | --- | --- |
| 6502 BASIC | `N=2` | best と一致 | **82** **49** **0F** **DB** | `0` | small FP では 2 回で best |
| BASIC-80 | `N=3` | best と不一致 | 20 34 7A A5 **DA** **0F** **49** **82** | `3.116999880425908D-09` | MBF double ではかなり粗い |
| N-BASIC | `N=2` | best と不一致 | B4 8B 7B E4 DB **0F** **49** **82** | `3.002137837215813D-07` | native `SQR` では大きく外れる |
| N88-BASIC | `N=3` | best と一致 | **C2** **68** **21** **A2** **DA** **0F** **49** **82** | `0` | 標準形 AGM で直接 best |
| FM-7 F-BASIC | `N=2` | best と不一致 | B4 8B 7B E4 DB **0F** **49** **82** | `3.002137837215813D-07` | native `SQR` では N-BASIC と同じ |
| FM-11 F-BASIC | `N=3` | best と不一致 | C4 **68** **21** **A2** **DA** **0F** **49** **82** | `1.110223024625157D-16` | best の 1 ulp 上 |
| MSX-BASIC | `N=3` | best と不一致 | **41** **31** **41** **59** **26** **53** 59 02 | `4E-13` | BCD double でも best には届かない |
| GW-BASIC | `N=6` | best と不一致 | 6C 5D 31 B1 **DA** **0F** **49** **82** | `1.402788518678477D-08` | MBF double ではかなり粗い |
| QBasic | `N=3` | best と不一致 | 1A **2D** **44** **54** **FB** **21** **09** **40** | `8.881784197001252D-16` | best の 2 ulp 上 |
| Grant BASIC | `N=2` | best と一致 | **DB** **0F** **49** **82** | `0` | small FP では 2 回で best |

補足:

- 6502 BASIC と Grant BASIC は，small FP で標準形 AGM が `N=2` で直接 best に届きます．
- 再調査では，N-BASIC・N88-BASIC・FM-7 F-BASIC・FM-11 F-BASIC を built-in `SQR` で確認しました．それでも結果はそろわず，MBF double 系でも処理系ごとの差がそのまま出ます．
- MBF double 系で標準形 AGM が直接 best に届いたのは，確認できた範囲では N88-BASIC だけでした．FM-11 F-BASIC は best の 1 ulp 上，N-BASIC と FM-7 F-BASIC は `N=2` で大きく外れます．
- BASIC-80 と GW-BASIC でも `ATN` 直打ちよりは改善しますが，AGM の急速収束がそのまま best 到達には結びつきません．
- QBasic と C `double` / `__float128` は，急速に収束しても最後は best の 1 ulp か 2 ulp ずれたところで止まります．

### N-BASIC，N88-BASIC，F-BASIC

以前の N-BASIC probe は，runner 側の古い制約を前提に Newton 反復で平方根を作っていました．その版では `N=3` で best の 1 ulp 下でしたが，native `SQR` に戻すと，N-BASIC は `N=2` の値 `B4 8B 7B E4 DB 0F 49 82` に落ちます．つまり，旧表の N-BASIC の値は current runner での標準形 AGM そのものではありませんでした．

FM-7 F-BASIC は N-BASIC と同じく `N=2` で `B4 8B 7B E4 DB 0F 49 82` に落ちます．一方で FM-11 F-BASIC は N-BASIC とも N88-BASIC とも一致せず，`N=3` で `C4 68 21 A2 DA 0F 49 82`，つまり best の 1 ulp 上です．したがって，「built-in `SQR` が使えるかどうか」だけでは N88-BASIC の挙動は説明できません．平方根の実装と途中の丸めが処理系ごとに違い，その差が AGM の最終値にそのまま現れています．

### MBF double と独自 `SQR`

「built-in `SQR` が単精度寄りに丸めて AGM を壊しているのではないか」を見るために，MBF double 系だけで `1/SQR(2)` と `SQR(A*C)` を Newton 反復の自前平方根に置き換えた補助実験も行いました．ここでは AGM の更新順はそのまま保ち，平方根の実装だけを変えています．Newton 反復は固定回数ではなく `Y_new=Y_old` で停止し，2-cycle の振動が起きた場合は `OSC` として数えるようにしました．collector は [collect_custom_sqrt.py](./collect_custom_sqrt.py) です．

```bash
cd /root/work/pi-repr
python3 gauss-legendre/collect_custom_sqrt.py
```

| BASIC | built-in `SQR` | custom `SQR` | メモ |
| --- | --- | --- | --- |
| BASIC-80 | `N=3, 3.116999880425908D-09` | `best (N=3)` | 自前平方根で best に届く |
| N-BASIC | `N=2, 3.002137837215813D-07` | `N=3, -1.110223024625157D-16` | 大きく改善するが best の 1 ulp 下 |
| N88-BASIC | `best (N=3)` | `best (N=3)` | もともと best で変化なし |
| FM-7 F-BASIC | `N=2, 3.002137837215813D-07` | `N=3, 1.110223024625157D-16` | 大きく改善するが best の 1 ulp 上 |
| FM-11 F-BASIC | `N=3, 1.110223024625157D-16` | `N=3, 1.110223024625157D-16` | 変化なし |
| GW-BASIC | `N=6, 1.402788518678477D-08` | `best (N=3)` | 自前平方根で best に届く |

この補助実験から，`SQR` の精度が実際に主因だったケースと，そうでないケースが分かれます．BASIC-80 と GW-BASIC では自前平方根だけで best に届くので，built-in `SQR` の丸めが支配的だったと見てよさそうです．一方で FM-11 F-BASIC は自前平方根でも全く変わらず，N-BASIC と FM-7 F-BASIC も大きく改善はするものの best には届きません．したがって，MBF double 系でも「`SQR` が単精度だからダメ」と一括りにはできず，平方根以外の中間丸めも無視できません．equality-stop の確認では，確認できた対象で `OSC 0` しか出ず，2-cycle 振動は観測しませんでした．

標準形を残したまま，同じ工夫を BASIC 側でも [collect_techniques.py](./collect_techniques.py) で試しましたが，MSX-BASIC が `4E-13` から `3E-13` へ少し良くなる程度で，やはりほとんど改善しませんでした．

## 見えたこと

- AGM は級数より収束がずっと速く，`N` 自体は 2 か 3 か 4 で十分です．
- それでも best に届くかどうかは別問題で，途中の平方根・乗算・減算の丸めが効きます．
- native `SQR` に揃えても，MBF double 系の AGM の終点は N-BASIC / FM-7 / FM-11 / N88 / BASIC-80 / GW-BASIC で大きく分かれます．確認できた範囲では，N88-BASIC だけが直接 best に届きました．
- ただし built-in `SQR` を自前の Newton 反復に置き換えると，BASIC-80 と GW-BASIC は best に届きます．この二つでは `SQR` の丸めが AGM の主因だった可能性が高いです．
- 逆に FM-11 F-BASIC は自前平方根でも変わらず，N-BASIC と FM-7 F-BASIC も 1 ulp までは詰まるものの best には届きません．平方根だけを直しても足りない処理系が残ります．
- 式変形で少し改善する例はありますが，今回の範囲では `_Decimal64` と MSX-BASIC でわずかに良くなる程度でした．
- 少なくともこの標準形とその近い変形の範囲では，C では `long double`，BASIC では 6502 BASIC・Grant BASIC・N88-BASIC 以外について「AGM なら必ず best に届く」とは言えません．
