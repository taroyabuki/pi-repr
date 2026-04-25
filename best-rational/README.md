# best と一致する有理数

ここでは，best と一致する有理数のうち，分母が最小のものをどう見つけるかを扱います．

再調査メモ:

- 結論表は「全分母実測で再確認できたもの」だけを最終値として残す方針で見直し中です
- 長時間の exact-q sweep は [host-driven-verifier/README.md](../host-driven-verifier/README.md) の JSONL resume 付き worker を使います
- rerun の既定は `--workers 6`，`--max-chunk-seconds 3600` です

[continued-fractions/README.md](../continued-fractions/README.md) では，各処理系の exact best の有限連分数を有理数 `p/q` に直し，その `p/q` がどこで best に戻るかを調べています．

ここではそれとは別に，best と一致する有理数のうち分母が最小のものを探します．整理の方針は，

- MBF double / IEEE 754 系では half-ulp 区間から分母最小を求める
- MSX-BASIC では分母順の host-driven 検証を行う

という形です．

## BASIC

### 考え方

探索の上界 `Q` として，各系で既知の candidate denominator を置きます．その上で，

```text
q = 1, 2, ..., Q
```

を順に調べます．各分母 `q` では，

```text
p0 = round(target*q)
```

を中心に，

```text
p0, p0+1, p0-1, p0+2, p0-2, ...
```

の順で候補を試します．差が悪化してもすぐには止めず，さらに 2 段だけ調べます．

この方法は全ての分子を調べるわけではありません．

### half-ulp 区間で足りる系統

数学的な区間 `[target-half_ulp, target+half_ulp]` だけを見るなら，`Q*half_ulp<1/2` であれば，各 `q<=Q` についてその区間に入る `p/q` は高々 1 個です．したがって，この場合は

```text
p = round(target*q)
```

だけを見れば足ります．確認用のコードは [min-denom.py](min-denom.py) です．

```bash
python3 best-rational/min-denom.py
```

結果:

| BASIC | `Q*half_ulp` | 数学的な区間での分母最小 | 実際に BASIC で見つかった分母最小 |
| --- | --- | --- | --- |
| 6502 BASIC | `3.542E-03` | `93343/29712` | `93343/29712` |
| BASIC-80 | `5.808E-09` | `657408909/209259755` | `657408909/209259755` |
| N-BASIC | `5.808E-09` | `657408909/209259755` | `657408909/209259755` |
| N88-BASIC | `5.808E-09` | `657408909/209259755` | `657408909/209259755` |
| F-BASIC | `5.808E-09` | `657408909/209259755` | `657408909/209259755` |
| MSX-BASIC | `4.993E-07` | `5419351/1725033` | `31369698/9985285` |
| GW-BASIC | `5.808E-09` | `657408909/209259755` | `657408909/209259755` |
| QBasic | `1.738E-08` | `245850922/78256779` | `245850922/78256779` |
| Grant BASIC | `3.542E-03` | `93343/29712` | `93343/29712` |

6502 BASIC，Grant BASIC，MBF double 系（BASIC-80 / N-BASIC / F-BASIC / GW-BASIC），QBasic では，この half-ulp 区間の方針で実際の結果まで説明できます．

N-BASIC については [host-driven-verifier/nbasic_mbf_model.py](../host-driven-verifier/nbasic_mbf_model.py) で

- `p#/q#` の結果が「有理数 `p/q` を MBF double に nearest round したもの」と一致するか
- worker が返す `LESS / EQUAL / GREATER` とその model が一致するか

を確認しています．現時点では，`locate(209259755)` が `first_ge_p=657408909` を返し，worker とのランダム照合でも不一致は出ていません．

FM-7 F-BASIC と FM-11 F-BASIC は，まとめず別に追っています．少なくとも

- FM-11 `best/fm11basic.bas` が `MATCH OK` / `ATN GT`
- FM-11 `decimal-literals/fm11basic.bas` が `30 LT`, `31 LT`, `32 GT`, `33 GT`

を実測できました．FM-7 でも同じ境界を確認しています．

N88-BASIC は，次の確認で

- `best/n88basic.bas` が `MATCH OK` / `ATN GT`
- `decimal-literals/n88basic.bas` が N-BASIC と同じ境界
- `continued-fractions/n88basic-fourops.bas` が `FOUND 16`
- `best-rational/probe-n88basic-keycases.bas` で
  `657408909/209259755` が `EQUAL`，
  `411557987/131002976` が `GREATER`，
  `245850922/78256779` が `LESS`，
  さらに `q=209259755` では
  `657408908/209259755` が `LESS`，
  `657408910/209259755` が `GREATER`
- [host-driven-verifier/n88_runner_verify.py](../host-driven-verifier/n88_runner_verify.py) の
  `--hash-operands keycases` で
  `657408909#/209259755#`，
  `411557987#/131002976#`，
  `245850922#/78256779#`，
  `657408908#/209259755#`，
  `657408910#/209259755#`
  の bytes と `LESS / EQUAL / GREATER` が shared MBF nearest model と一致
- `--hash-operands verify-random --samples 20 --max-q 5000000 --max-delta 4 --seed 1`
  でも 20 件すべて一致
- 逆に `3540978/1127129` は
  `0 0 0 0 210 15 73 130` を返して `LESS`，
  `3540978#/1127129#` は
  `254 67 160 127 210 15 73 130` を返して model と一致

まで実測できました．つまり，N88-BASIC では generic な候補検証には `p#/q#` を使って double 演算に固定する必要がありますが，その条件では shared MBF nearest model が runner と一致します．known best の `657408909/209259755` 自体は，`#` なしでも `#` 付きでも同じ best に入ります．したがって，この文書では N88-BASIC も N-BASIC と同じ MBF nearest model を採用します．

BASIC-80 については [host-driven-verifier/mbf_runner_verify.py](../host-driven-verifier/mbf_runner_verify.py) で，少なくとも

- `657408909/209259755` は MBF nearest model の byte 列と一致
- `411557987/131002976` は model 上 `GREATER`
- `245850922/78256779` は model 上 `LESS`

を確認しています．

GW-BASIC についても [host-driven-verifier/mbf_runner_verify.py](../host-driven-verifier/mbf_runner_verify.py) で同じ確認を実行し，

- `657408909/209259755` は MBF nearest model の byte 列と一致
- `411557987/131002976` は model 上 `GREATER`
- `245850922/78256779` は model 上 `LESS`

を確認しました．

QBasic も同様に，ここでは式の直接比較を扱わず，変数に入った後の値どうしの一致だけを対象にしているので，IEEE 754 binary64 の half-ulp 区間で考えてよいです．したがって，QBasic の結論は `245850922/78256779` です．

Grant BASIC については，少なくとも

- `best/grantsbasic.bas` が `RAT MATCH` / `ATN GT`
- `decimal-literals/grantsbasic.bas` で `3.1415927` が `EQ`，`3.14159265358979` が `GT`
- `continued-fractions/grantsbasic-fourops.bas` が `FOUND 4`
- `best-rational/probe-grantsbasic-roundonly.bas` を Grant runtime 直結で `q=1..29712` まで回し，
  `q=29712` で最初の exact match `93343/29712` を確認
- `best-rational/probe-grantsbasic.bas` を同じく Grant runtime 直結で `q=1..29712` まで回し，
  `ANOM` なし，最初の exact match は `q=29712`, `d=0` を確認

を実測しました．したがって Grant BASIC も 6502 BASIC と同様に，half-ulp 区間の方針と実際の分母順 full probe が一致しています．

### Host-Driven Verifier と実行コスト

長い BASIC probe のままでは，1 本のプログラムの中に

- 候補生成
- 数値評価
- 進捗表示
- 異常判定

が混ざります．これは仮説を探るには便利ですが，

- 長時間 run が必要になる
- batch 入力や画面取り込みの不安定さが結果に混ざる
- 候補生成のヒューリスティックがそのまま証明にはならない

という問題があります．そこで [host-driven-verifier/README.md](../host-driven-verifier/README.md) では方針を逆にし，候補生成は host 側で行い，BASIC 側には

- この候補 `p/q` が target と一致するか
- 固定した `q` で `p/q` が target より `LESS / EQUAL / GREATER` のどれか

だけを返させます．つまり，

1. host 側で候補 `(p, q)` を選ぶ
2. 短い command だけを BASIC に送る
3. `MATCH` / `MISS` や `LESS / EQUAL / GREATER` だけを受け取る
4. 探索順や探索範囲の正当化は host 側で管理する

という分離です．特に compare worker を使うと，固定した `q` について `first_ge_p` を二分探索できるので，MSX-BASIC や N-BASIC ではこれを exact-q sweep の実行方式として使えます．

長時間 run の運用は次に揃えています．

- 1 chunk の wall time 上限は `3600s`
- 並列数は `6` 以下
- 結果は JSONL に追記し，`--results-path` と `--resume-from` で再開する

この方式が実際にどこまで有効だったかをまとめると次のとおりです．

| BASIC | 実行方式 | 実測 | この節での役割 |
| --- | --- | --- | --- |
| 6502 BASIC | probe による分母順探索 | `q=1..29712` で `ANOM` なし．最初の exact match は `q=29712`, `d=0` | 既知の最小分母まで実際に到達できる |
| BASIC-80 | probe による分母順探索 | `q=1..11800000` で `ANOM` なし，exact match なし．完走には 1 日以上かかる見込み | full sweep は見送り，MBF model の確認へ切り替え |
| N-BASIC | host-driven compare worker の small bench | 4 worker で `q=209259700..209259755` の 56 個に `64.8s` | full exact-q sweep は非現実的なので，MBF model と worker 照合で結論を出す |
| N88-BASIC | runner + shared MBF model spot check | `best` / `decimal-literals` / `continued-fractions` に加え，`p#/q#` の keycase 5 件と random 20 件で bytes と `LESS/GREATER/EQUAL` が model と一致 | generic 候補では `#` を付けて double 演算に固定し，N-BASIC と同じ MBF nearest model を採用する |
| F-BASIC | best / continued fractions / decimal literals の結果を併用 | FM-7 F-BASIC / FM-11 F-BASIC は `657408909/209259755` が best，`continued-fractions` は `FOUND 16`，decimal-literal 境界は N-BASIC と一致 | N-BASIC と同じ MBF model を採用 |
| MSX-BASIC | host-driven exact-q sweep | compare worker 4 並列で `q=1..3450066` を `40604.6s` で完走 | half-ulp では足りないので，この方式で `10838702/3450066` を確定 |
| GW-BASIC | wrapper 経由の分母順探索 | `q=1..209259755` で `ANOM` なし．最初の exact match は `q=209259755`, `d=0` | 既知の最小分母まで実際に到達できる |
| Grant BASIC | probe による分母順探索 | `q=1..29712` で `ANOM` なし．最初の exact match は `q=29712`, `d=0` | 既知の最小分母まで実際に到達できる |

つまり，host-driven verifier は単なる高速化ではなく，「full sweep で押し切れる系統」と「model に切り替えるべき系統」を見分けるための実行方式です．MSX-BASIC ではこれが final proof の本体になり，N-BASIC では逆に「この方式では遅すぎる」こと自体が MBF model へ移る根拠になりました．

ここでの要点だけを言い直すと，結論は次の 3 つです．

- MSX-BASIC では half-ulp 区間も naive な nearest model も足りないので，固定した `q` に対する `p` 全域探索を二分探索で圧縮した exact-q sweep が要る
- N-BASIC は同じ方式では遅すぎるので，compare worker で裏付けた MBF nearest model に切り替える
- BASIC-80，F-BASIC，GW-BASIC も同じ MBF nearest model で説明できる

実装ファイルの一覧や再現コマンドは [host-driven-verifier/README.md](../host-driven-verifier/README.md) に分けてあります．

### MSX-BASIC の旧ヒューリスティック

MSX-BASIC では，次のような短いプログラムでも実際には最小分母 `10838702/3450066` に到達します．

```basic
100 REM ***** Fraction.
105 DEFDBL A-Z
110 A=4*ATN(1)
120 N=1:D=1
130 L=A*N
140 M=INT(L)
150 IF M+1-L<L-M THEN M=M+1
160 E=ABS(A-M/N)
170 IF E>=D GOTO 200
180 PRINT M;"/";N,M/N
185 IF E=0 THEN END
190 D=E
200 N=N+1
210 GOTO 130
```

このコードがやっているのは，各分母 `N` について `M=round(A*N)` だけを試し，それまでの最良誤差を更新したときだけ表示することです．今回の MSX-BASIC ではこのヒューリスティックで実際に `10838702/3450066` に着きます．しかし，このコードだけでは「各 `N` で `round(A*N)` 以外を見なくてよい」とは言えません．つまり，探索には使えても，取りこぼしがないことの証明にはなりません．

さらに MSX-BASIC では，その正当化に使えそうな naive な丸めモデル自体が壊れています．数学的には同じ値である `5419351/1725033` は `MISS` なのに，`10838702/3450066` は `MATCH` です．したがって，「`p/q` を数学的な有理数として見て，その nearest rounding を追えば十分」という説明もここでは使えません．そのため最終的には host-driven exact-q sweep で，固定した `q` に対する `p` 全域を compare worker で調べました．

## 注意

- ここで欲しいのは「数学的に最も近い比」ではなく，「その BASIC で `target = p/q` が真になる分母最小の有理数」です．
- 6502 BASIC，MBF double 系，QBasic では，この条件を half-ulp 区間で言い換えられます．
- MSX-BASIC だけはその言い換えが失敗するので，分母順の exact-q 検証が別に必要です．

### 以上の整理

以上をまとめると，この節で得られる最終的な分母最小は次のとおりです．

| BASIC | 比較に使う値 | この節で得られる分母最小 | メモ |
| --- | --- | --- | --- |
| 6502 BASIC | `4*ATN(1)` | `93343/29712` |  |
| BASIC-80 | `POKE` で作った best | `657408909/209259755` |  |
| N-BASIC | `POKE` で作った best | `657408909#/209259755#` | 分母・分子の両方に `#` が要る．MBF nearest model と worker 照合で裏付け済み |
| N88-BASIC | `POKE` で作った best | `657408909#/209259755#` | generic な候補比較では分母・分子の両方に `#` を付ける．known best の `657408909/209259755` 自体は `#` なしでも一致 |
| F-BASIC | `POKE` で作った best | `657408909/209259755` | 分母・分子に `#` は不要．N-BASIC と同じ MBF nearest model を採用 |
| MSX-BASIC | `4*ATN(1)` | `10838702/3450066` | half-ulp 区間だけなら `31369698/9985285` までだが，この節の exact-q sweep まで含めるとここまで下がる |
| GW-BASIC | `3.1415926535897932#` | `657408909/209259755` |  |
| QBasic | `4*ATN(1)` | `245850922/78256779` | half-ulp 区間から得た値．候補は変数に代入して比較 |
| Grant BASIC | `3.1415927` | `93343/29712` | `4*ATN(1)` は best の 1 ulp 上なので，best 自体を比較値に使う |

## C言語（x86_64, GNU gcc）

この節では x86_64 Linux 上の GNU gcc を前提に，BASIC と同じ方針で分母順探索を考えます．

### 前提

- 環境: x86_64 Linux, GCC 13, `-std=gnu2x`
- 対象の型: `double`, `long double`, `_Decimal64`, `_Decimal128`, `__float128`
- 確認コード: [experiment.c](experiment.c)

コンパイルと実行:

```bash
gcc -std=gnu2x best-rational/experiment.c -lm -lquadmath -o /tmp/exp
/tmp/exp
```

### half-ulp 区間を使う方針

`double`, `long double`, `__float128` では，`p/q` をその型で評価した結果は，数学的な `p/q` をその型に丸めたものと見なせます．したがって，これらの型では

```text
(T)p/q == best
```

を調べるかわりに，

```text
p/q が best の half-ulp 区間に入るか
```

を調べれば足ります．

`_Decimal64`, `_Decimal128` については，C 標準の強い保証としては使いません．ただし，ここでは x86_64 Linux 上の GNU gcc を前提にし，この環境では decimal float は GCC 拡張として実装され，`__DECIMAL_BID_FORMAT__` も立っています．さらに GCC の decimal runtime は IEEE 754-2008 decimal arithmetic を実装するものとして説明されているので，この文書では decimal についても同じ half-ulp 区間の方針を採用します．

この方針で求めた分母最小の有理数は次のとおりです．

| 型 | 比較に使う値 | half-ulp 区間で求めた分母最小 | メモ |
| --- | --- | --- | --- |
| `_Decimal64` | `(_Decimal64)M_PI` | `80143857/25510582` | half-ulp 区間から得た値 |
| `double` | `M_PI` | `245850922/78256779` |  |
| `long double` | `4*atanl(1)` | `8717442233/2774848045` |  |
| `_Decimal128` | `3.141592653589793238462643383279503dl` | `66627445592888887/21208174623389167` | half-ulp 区間から得た値 |
| `__float128` | `M_PIq` | `363383500998180356/115668560843798173` |  |

### 分母順探索の実験

[experiment.c](experiment.c) は，上で述べた分母順探索を `_Decimal64`, `double`, `long double` について実際に走らせます．ここで記録するのは

- `d=0` より良い候補が現れたか
- 最初に exact match が現れる `q`

です．

```bash
gcc -O3 -std=gnu2x best-rational/experiment.c -lm -o /tmp/exp
/tmp/exp
```

結果:

| 型 | 調べた範囲 | `d=0` より良い候補 | 最初の exact match |
| --- | --- | --- | --- |
| `_Decimal64` | `q=1..25510582`, `d=0, ±1, ..., ±6` | なし | `q=25510582`, `d=0` |
| `double` | `q=1..78256779`, `d=0, ±1, ..., ±6` | なし | `q=78256779`, `d=0` |
| `long double` | `q=1..2774848045`, `d=0, ±1, ..., ±6` | なし | `q=2774848045`, `d=0` |

少なくともこの 3 型では，`q` を増やしながら探索しても `d=0` より良い候補は現れませんでした．したがって，これらについては「`p0=round(target*q)` から始め，悪化後さらに少しだけ見る」という方針は実験結果と矛盾していません．

`_Decimal128` と `__float128` については `known_q` が大きすぎるので，同じ全探索はまだ行っていません．

## 注意

- C でも評価過程の差を避けるため，ここでは変数に入った後の値どうしの一致だけを対象にします．
- `_Decimal64`, `double`, `long double` については，上の範囲で実際に分母順探索も行いました．
- `_Decimal128`, `__float128` については，half-ulp 区間の方針で結論を出し，同じ全探索はまだしていません．
