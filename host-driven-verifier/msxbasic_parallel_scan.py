#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import random
import subprocess
import sys
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
WORKER_SCRIPT = THIS_DIR / "msxbasic_worker.py"
RESULTS_DIR = THIS_DIR / "scan-results"
DEFAULT_WORKERS = min(4, max(1, (os.cpu_count() or 1) // 2))


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run chunked parallel MSX-BASIC worker scans.")
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--rom", metavar="PATH", type=Path, default=None)
    source.add_argument("--machine", metavar="NAME", default=None)
    parser.add_argument("--rom-dir", metavar="DIR", type=Path, default=None)
    parser.add_argument("--q-start", type=int, required=True)
    parser.add_argument("--q-end", type=int, required=True)
    parser.add_argument("--radius", type=int, default=0)
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    parser.add_argument("--chunk-size", type=int, default=10000)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--retry-delay", type=float, default=2.0)
    parser.add_argument("--results-dir", type=Path, default=RESULTS_DIR)
    parser.add_argument("--tag", default=None, help="Optional suffix for the JSONL result file name.")
    return parser.parse_args(argv)


def build_chunks(q_start: int, q_end: int, chunk_size: int) -> list[tuple[int, int]]:
    chunks: list[tuple[int, int]] = []
    start = q_start
    while start <= q_end:
        end = min(start + chunk_size - 1, q_end)
        chunks.append((start, end))
        start = end + 1
    return chunks


def build_command(args: argparse.Namespace, q_start: int, q_end: int) -> list[str]:
    cmd = [
        sys.executable,
        str(WORKER_SCRIPT),
    ]
    if args.rom is not None:
        cmd.extend(["--rom", str(args.rom)])
    elif args.machine is not None:
        cmd.extend(["--machine", args.machine])
    if args.rom_dir is not None:
        cmd.extend(["--rom-dir", str(args.rom_dir)])
    cmd.extend(
        [
            "scan",
            "--q-start",
            str(q_start),
            "--q-end",
            str(q_end),
            "--radius",
            str(args.radius),
        ]
    )
    return cmd


def run_chunk(args: argparse.Namespace, q_start: int, q_end: int) -> dict[str, object]:
    cmd = build_command(args, q_start, q_end)
    last_record: dict[str, object] | None = None
    for attempt in range(1, args.retries + 2):
        started = time.time()
        proc = subprocess.run(cmd, capture_output=True, text=True)
        elapsed = time.time() - started
        stdout_lines = [line for line in proc.stdout.splitlines() if line.strip()]
        stderr_lines = [line for line in proc.stderr.splitlines() if line.strip()]
        match_lines = [line for line in stdout_lines if line.startswith('MATCH ')]
        no_match = any(line.startswith('NO_MATCH ') for line in stdout_lines)
        ok = proc.returncode in (0, 1) and (match_lines or no_match)
        last_record = {
            'q_start': q_start,
            'q_end': q_end,
            'returncode': proc.returncode,
            'elapsed': elapsed,
            'attempt': attempt,
            'matches': match_lines,
            'no_match': no_match,
            'ok': ok,
            'stdout_tail': stdout_lines[-10:],
            'stderr_tail': stderr_lines[-10:],
        }
        if ok:
            return last_record
        if attempt <= args.retries:
            time.sleep(args.retry_delay + random.random())
    assert last_record is not None
    return last_record


def append_result(path: Path, record: dict[str, object]) -> None:
    with path.open('a', encoding='utf-8') as fh:
        fh.write(json.dumps(record, ensure_ascii=True) + '\n')


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.q_end < args.q_start:
        raise SystemExit('error: --q-end must be >= --q-start')
    if args.chunk_size <= 0:
        raise SystemExit('error: --chunk-size must be > 0')
    if args.workers <= 0:
        raise SystemExit('error: --workers must be > 0')

    chunks = build_chunks(args.q_start, args.q_end, args.chunk_size)
    args.results_dir.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime('%Y%m%d-%H%M%S', time.gmtime())
    tag = f'-{args.tag}' if args.tag else ''
    result_path = args.results_dir / f'msxbasic-parallel-scan-{timestamp}{tag}.jsonl'

    started = time.time()
    print(
        f'START chunks={len(chunks)} workers={args.workers} q_start={args.q_start} q_end={args.q_end} radius={args.radius} chunk_size={args.chunk_size} results={result_path}',
        flush=True,
    )
    completed = 0
    matches: list[str] = []

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        pending = {executor.submit(run_chunk, args, q0, q1): (q0, q1) for q0, q1 in chunks}
        while pending:
            done, _ = wait(pending, return_when=FIRST_COMPLETED)
            for future in done:
                q0, q1 = pending.pop(future)
                record = future.result()
                append_result(result_path, record)
                completed += 1
                elapsed = time.time() - started
                rate = completed / elapsed if elapsed > 0 else 0.0
                prefix = 'MATCH' if record['matches'] else 'NO_MATCH'
                if record['matches']:
                    matches.extend(record['matches'])
                print(
                    f'{prefix} chunk={q0}-{q1} completed={completed}/{len(chunks)} elapsed={record["elapsed"]:.1f}s rate={rate:.3f} chunks/s',
                    flush=True,
                )
                if not record['ok']:
                    print(f'ERROR chunk={q0}-{q1} attempt={record["attempt"]} returncode={record["returncode"]}', flush=True)
                    for line in record['stdout_tail']:
                        print(f'STDOUT {line}', flush=True)
                    for line in record['stderr_tail']:
                        print(f'STDERR {line}', flush=True)
                    return 2

    total_elapsed = time.time() - started
    if matches:
        print(f'FOUND {len(matches)} match-lines in {total_elapsed:.1f}s', flush=True)
        for line in matches:
            print(line, flush=True)
        print(f'RESULTS {result_path}', flush=True)
        return 0
    print(f'COMPLETE no matches in {total_elapsed:.1f}s', flush=True)
    print(f'RESULTS {result_path}', flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
