# Host-Driven Verifier

`best-rational/README.md` で使っている host-driven 検証系の実装置き場です．ここではファイルの役割と再現コマンドだけを簡潔に置きます．

2026-04-06 時点の rerun 方針:

- exact-q sweep は `--workers 6` まで
- 1 chunk の wall time 上限は既定で `3600s`
- 長時間 run は JSONL に記録し，`--results-path` と `--resume-from` で再開する

## MSX-BASIC

- [msxbasic_verify.py](msxbasic_verify.py)
  単発の `MATCH` / `MISS` 確認
- [msxbasic_worker.py](msxbasic_worker.py)
  常駐 worker を使う高速版
- [msxbasic_compare_worker.py](msxbasic_compare_worker.py)
  `LESS / EQUAL / GREATER` を返す tri-state worker
- [msxbasic_compare_parallel_pool.py](msxbasic_compare_parallel_pool.py)
  fixed-`q` の `first_ge_p` を二分探索して exact-q sweep を回す pool
- [msxbasic_bcd_model.py](msxbasic_bcd_model.py)
  naive な BCD nearest model が MSX-BASIC では足りないことを示す補助コード

例:

```bash
python3 host-driven-verifier/msxbasic_compare_worker.py compare 10838702 3450066
python3 host-driven-verifier/msxbasic_compare_worker.py locate 3450066
python3 host-driven-verifier/msxbasic_compare_parallel_pool.py \
  --q-start 3450000 --q-end 3450066 \
  --workers 6 --chunk-size 20 --startup-jobs 1 \
  --results-path host-driven-verifier/scan-results/msx-rerun.jsonl
python3 host-driven-verifier/msxbasic_compare_parallel_pool.py \
  --q-start 3450000 --q-end 3450066 \
  --workers 6 --chunk-size 20 --startup-jobs 1 \
  --results-path host-driven-verifier/scan-results/msx-rerun.jsonl \
  --resume-from host-driven-verifier/scan-results/msx-rerun.jsonl
python3 host-driven-verifier/msxbasic_bcd_model.py keycases
```

## MBF double 系

- [nbasic_compare_worker.py](nbasic_compare_worker.py)
  N-BASIC の tri-state compare worker
- [nbasic_compare_parallel_pool.py](nbasic_compare_parallel_pool.py)
  N-BASIC の small-range exact-q bench
- [nbasic_mbf_model.py](nbasic_mbf_model.py)
  N-BASIC の MBF nearest model と worker 照合
- [n88_runner_verify.py](n88_runner_verify.py)
  N88-BASIC の runner を使って `p#/q#` と shared MBF nearest model を照合
- [mbf_shared_model.py](mbf_shared_model.py)
  BASIC-80 / N-BASIC / GW-BASIC 共通の MBF double model
- [mbf_runner_verify.py](mbf_runner_verify.py)
  BASIC-80 / GW-BASIC の wrapper runner 経由の確認

例:

```bash
python3 host-driven-verifier/nbasic_compare_worker.py compare 657408909 209259755
python3 host-driven-verifier/nbasic_compare_parallel_pool.py \
  --q-start 209259700 --q-end 209259755 \
  --workers 6 --chunk-size 10 --startup-jobs 1 \
  --results-path host-driven-verifier/scan-results/nbasic-rerun.jsonl
python3 host-driven-verifier/nbasic_compare_parallel_pool.py \
  --q-start 209259700 --q-end 209259755 \
  --workers 6 --chunk-size 10 --startup-jobs 1 \
  --results-path host-driven-verifier/scan-results/nbasic-rerun.jsonl \
  --resume-from host-driven-verifier/scan-results/nbasic-rerun.jsonl
python3 host-driven-verifier/nbasic_mbf_model.py min-denom
python3 host-driven-verifier/nbasic_mbf_model.py verify-worker --samples 1000 --max-q 5000000 --seed 1
python3 host-driven-verifier/n88_runner_verify.py --hash-operands keycases
python3 host-driven-verifier/n88_runner_verify.py --hash-operands verify-random --samples 20 --max-q 5000000 --max-delta 4 --seed 1
python3 host-driven-verifier/mbf_runner_verify.py --runtime basic80 keycases
python3 host-driven-verifier/mbf_runner_verify.py --runtime gwbasic keycases
```

## 現状の使い分け

- MSX-BASIC
  exact-q sweep が proof の本体
- N-BASIC
  compare worker と exact-q sweep の両方を rerun に使う
- N88-BASIC
  runner 実測では generic な候補を `p#/q#` で与えて double 演算に固定し，shared MBF nearest model と照合する
- BASIC-80 / GW-BASIC
  現状は MBF nearest model を runner 経由で確認する

`msxbasic_verify.py check ...` は短い `MATCH` / `MISS` の spot check には使えますが，2026-04-06 rerun では画面取りこぼしを避けるため tri-state の `msxbasic_compare_worker.py` を正に使います．

最終的な結論は [best-rational/README.md](../best-rational/README.md) を参照してください．
