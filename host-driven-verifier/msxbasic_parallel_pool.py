#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import queue
import random
import threading
import time
from pathlib import Path

import msxbasic_verify as base
from msxbasic_worker import MsxBasicWorker

RESULTS_DIR = Path(__file__).resolve().parent / "scan-results"
DEFAULT_WORKERS = min(4, max(1, (os.cpu_count() or 1) // 2))


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a persistent-worker parallel MSX-BASIC scan.")
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--rom", metavar="PATH", type=Path, default=None)
    source.add_argument("--machine", metavar="NAME", default=None)
    parser.add_argument("--rom-dir", metavar="DIR", type=Path, default=base._DEFAULT_ROM_DIR)
    parser.add_argument("--q-start", type=int, required=True)
    parser.add_argument("--q-end", type=int, required=True)
    parser.add_argument("--radius", type=int, default=0)
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    parser.add_argument("--chunk-size", type=int, default=1000)
    parser.add_argument("--worker-retries", type=int, default=6)
    parser.add_argument("--retry-delay", type=float, default=3.0)
    parser.add_argument("--startup-stagger", type=float, default=0.5)
    parser.add_argument(
        "--startup-jobs",
        type=int,
        default=1,
        help="Maximum number of workers allowed to enter openMSX startup at once.",
    )
    parser.add_argument("--results-dir", type=Path, default=RESULTS_DIR)
    parser.add_argument("--tag", default=None)
    return parser.parse_args(argv)


def build_chunks(q_start: int, q_end: int, chunk_size: int) -> list[tuple[int, int]]:
    chunks: list[tuple[int, int]] = []
    start = q_start
    while start <= q_end:
        end = min(start + chunk_size - 1, q_end)
        chunks.append((start, end))
        start = end + 1
    return chunks


def append_result(path: Path, record: dict[str, object]) -> None:
    with path.open('a', encoding='utf-8') as fh:
        fh.write(json.dumps(record, ensure_ascii=True) + '\n')


def scan_chunk(worker: MsxBasicWorker, q_start: int, q_end: int, radius: int) -> list[str]:
    matches: list[str] = []
    offsets = base.offset_order(radius)
    for q in range(q_start, q_end + 1):
        center = base.round_half_up(base.MSX_BEST * q)
        for offset in offsets:
            p = center + offset
            if worker.check_candidate(p, q):
                matches.append(f'{base.MATCH_TOKEN} q={q} p={p} d={offset} expr={base.candidate_expr(p, q)}')
    return matches


def worker_loop(
    worker_id: int,
    machine: str,
    extra_rom_path: str | None,
    radius: int,
    task_queue: queue.Queue[tuple[int, int]],
    result_queue: queue.Queue[dict[str, object]],
    stop_event: threading.Event,
    startup_semaphore: threading.Semaphore,
    worker_retries: int,
    retry_delay: float,
    startup_stagger: float,
) -> None:
    worker: MsxBasicWorker | None = None
    if startup_stagger > 0:
        time.sleep(worker_id * startup_stagger)
    try:
        while not stop_event.is_set():
            try:
                q_start, q_end = task_queue.get_nowait()
            except queue.Empty:
                return
            attempts = 0
            while not stop_event.is_set():
                started = time.time()
                try:
                    if worker is None:
                        with startup_semaphore:
                            worker = MsxBasicWorker(machine=machine, extra_rom_path=extra_rom_path)
                            worker.__enter__()
                    matches = scan_chunk(worker, q_start, q_end, radius)
                    result_queue.put({
                        'worker_id': worker_id,
                        'q_start': q_start,
                        'q_end': q_end,
                        'elapsed': time.time() - started,
                        'attempt': attempts + 1,
                        'matches': matches,
                        'no_match': not matches,
                        'ok': True,
                        'error': None,
                    })
                    break
                except Exception as exc:  # noqa: BLE001
                    attempts += 1
                    if worker is not None:
                        try:
                            worker.__exit__(type(exc), exc, exc.__traceback__)
                        except Exception:
                            pass
                        worker = None
                    if attempts > worker_retries:
                        result_queue.put({
                            'worker_id': worker_id,
                            'q_start': q_start,
                            'q_end': q_end,
                            'elapsed': time.time() - started,
                            'attempt': attempts,
                            'matches': [],
                            'no_match': False,
                            'ok': False,
                            'error': f'{type(exc).__name__}: {exc}',
                        })
                        stop_event.set()
                        break
                    time.sleep(retry_delay + random.random())
            task_queue.task_done()
    finally:
        if worker is not None:
            worker.__exit__(None, None, None)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.q_end < args.q_start:
        raise SystemExit('error: --q-end must be >= --q-start')
    if args.chunk_size <= 0:
        raise SystemExit('error: --chunk-size must be > 0')
    if args.workers <= 0:
        raise SystemExit('error: --workers must be > 0')
    if args.startup_jobs <= 0:
        raise SystemExit('error: --startup-jobs must be > 0')

    machine, extra_rom_path = base.resolve_msx_config(args)
    chunks = build_chunks(args.q_start, args.q_end, args.chunk_size)
    args.results_dir.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime('%Y%m%d-%H%M%S', time.gmtime())
    tag = f'-{args.tag}' if args.tag else ''
    result_path = args.results_dir / f'msxbasic-parallel-pool-{timestamp}{tag}.jsonl'

    task_queue: queue.Queue[tuple[int, int]] = queue.Queue()
    for chunk in chunks:
        task_queue.put(chunk)
    result_queue: queue.Queue[dict[str, object]] = queue.Queue()
    stop_event = threading.Event()
    startup_semaphore = threading.Semaphore(args.startup_jobs)

    print(
        f'START chunks={len(chunks)} workers={args.workers} startup_jobs={args.startup_jobs} q_start={args.q_start} q_end={args.q_end} radius={args.radius} chunk_size={args.chunk_size} results={result_path}',
        flush=True,
    )
    started = time.time()
    threads = [
        threading.Thread(
            target=worker_loop,
            args=(
                worker_id,
                machine,
                extra_rom_path,
                args.radius,
                task_queue,
                result_queue,
                stop_event,
                startup_semaphore,
                args.worker_retries,
                args.retry_delay,
                args.startup_stagger,
            ),
            daemon=True,
            name=f'msx-worker-{worker_id}',
        )
        for worker_id in range(args.workers)
    ]
    for thread in threads:
        thread.start()

    completed = 0
    matches: list[str] = []
    while completed < len(chunks):
        record = result_queue.get()
        append_result(result_path, record)
        completed += 1
        elapsed = time.time() - started
        rate = completed / elapsed if elapsed > 0 else 0.0
        if not record['ok']:
            prefix = 'ERROR'
        elif record['matches']:
            prefix = 'MATCH'
        else:
            prefix = 'NO_MATCH'
        if record['matches']:
            matches.extend(record['matches'])
        print(
            f'{prefix} chunk={record["q_start"]}-{record["q_end"]} worker={record["worker_id"]} attempt={record["attempt"]} completed={completed}/{len(chunks)} elapsed={record["elapsed"]:.1f}s rate={rate:.3f} chunks/s',
            flush=True,
        )
        if not record['ok']:
            print(f'ERROR chunk={record["q_start"]}-{record["q_end"]} {record["error"]}', flush=True)
            stop_event.set()
            break

    for thread in threads:
        thread.join()

    total_elapsed = time.time() - started
    if matches:
        print(f'FOUND {len(matches)} match-lines in {total_elapsed:.1f}s', flush=True)
        for line in matches:
            print(line, flush=True)
        print(f'RESULTS {result_path}', flush=True)
        return 0
    if stop_event.is_set() and completed < len(chunks):
        print(f'ABORT after {completed}/{len(chunks)} chunks in {total_elapsed:.1f}s', flush=True)
        print(f'RESULTS {result_path}', flush=True)
        return 2
    print(f'COMPLETE no matches in {total_elapsed:.1f}s', flush=True)
    print(f'RESULTS {result_path}', flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
