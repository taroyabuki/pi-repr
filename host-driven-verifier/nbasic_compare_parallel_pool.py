#!/usr/bin/env python3

from __future__ import annotations

import argparse
import random
import threading
import time
from pathlib import Path

from nbasic_compare_worker import EQUAL, MATCH_TOKEN, NBasicCompareWorker, candidate_expr, locate_first_ge, resolve_nbasic_rom_path
from scan_pool_common import (
    DEFAULT_MAX_CHUNK_SECONDS,
    DEFAULT_WORKERS,
    RESULTS_DIR,
    append_result,
    completed_chunks_from_paths,
    resolve_result_path,
    validate_chunk_size,
    validate_max_chunk_seconds,
    validate_q_range,
    validate_startup_jobs,
    validate_worker_count,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a persistent-worker parallel binary-search N-BASIC scan.")
    parser.add_argument("--rom", metavar="PATH", type=Path, default=None)
    parser.add_argument("--max-steps", type=int, default=100_000)
    parser.add_argument("--batch-rounds", type=int, default=32)
    parser.add_argument("--slice-steps", type=int, default=1_000)
    parser.add_argument("--q-start", type=int, required=True)
    parser.add_argument("--q-end", type=int, required=True)
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    parser.add_argument("--chunk-size", type=int, default=100)
    parser.add_argument(
        "--max-chunk-seconds",
        type=float,
        default=DEFAULT_MAX_CHUNK_SECONDS,
        help="Mark a chunk as failed if one worker spends longer than this on it.",
    )
    parser.add_argument("--worker-retries", type=int, default=6)
    parser.add_argument("--retry-delay", type=float, default=3.0)
    parser.add_argument("--startup-stagger", type=float, default=0.5)
    parser.add_argument(
        "--startup-jobs",
        type=int,
        default=1,
        help="Maximum number of workers allowed to bootstrap the ROM scaffold at once.",
    )
    parser.add_argument("--results-dir", type=Path, default=RESULTS_DIR)
    parser.add_argument(
        "--results-path",
        type=Path,
        default=None,
        help="Write new records to this JSONL file instead of creating a timestamped one.",
    )
    parser.add_argument(
        "--resume-from",
        action="append",
        type=Path,
        default=[],
        help="Existing JSONL result file to reuse. May be passed multiple times.",
    )
    parser.add_argument("--tag", default=None)
    return parser.parse_args(argv)


class ChunkStream:
    def __init__(
        self,
        q_start: int,
        q_end: int,
        chunk_size: int,
        *,
        skipped_chunks: set[tuple[int, int]] | None = None,
    ) -> None:
        self._next_q = q_start
        self._q_end = q_end
        self._chunk_size = chunk_size
        self._skipped_chunks = skipped_chunks or set()
        self._lock = threading.Lock()
        self.total_chunks = ((q_end - q_start) // chunk_size) + 1

    def next_chunk(self) -> tuple[int, int] | None:
        with self._lock:
            while self._next_q <= self._q_end:
                start = self._next_q
                end = min(start + self._chunk_size - 1, self._q_end)
                self._next_q = end + 1
                chunk = (start, end)
                if chunk in self._skipped_chunks:
                    continue
                return chunk
            return None

def scan_chunk(worker: NBasicCompareWorker, q_start: int, q_end: int) -> list[str]:
    matches: list[str] = []
    for q in range(q_start, q_end + 1):
        p, result = locate_first_ge(worker, q)
        if result == EQUAL:
            matches.append(f"{MATCH_TOKEN} q={q} p={p} expr={candidate_expr(p, q)}")
    return matches


def worker_loop(
    worker_id: int,
    rom_path: Path,
    max_steps: int,
    batch_rounds: int,
    slice_steps: int,
    chunk_stream: ChunkStream,
    result_queue: "queue.Queue[dict[str, object]]",
    stop_event: threading.Event,
    startup_semaphore: threading.Semaphore,
    max_chunk_seconds: float,
    worker_retries: int,
    retry_delay: float,
    startup_stagger: float,
) -> None:
    import queue

    worker: NBasicCompareWorker | None = None
    if startup_stagger > 0:
        time.sleep(worker_id * startup_stagger)
    try:
        while not stop_event.is_set():
            chunk = chunk_stream.next_chunk()
            if chunk is None:
                return
            q_start, q_end = chunk
            attempts = 0
            while not stop_event.is_set():
                started = time.time()
                try:
                    if worker is None:
                        with startup_semaphore:
                            worker = NBasicCompareWorker(
                                rom_path=rom_path,
                                max_steps=max_steps,
                                batch_rounds=batch_rounds,
                                slice_steps=slice_steps,
                            )
                            worker.__enter__()
                    matches = scan_chunk(worker, q_start, q_end)
                    elapsed = time.time() - started
                    if elapsed > max_chunk_seconds:
                        raise TimeoutError(
                            f"chunk {q_start}-{q_end} exceeded {max_chunk_seconds:.1f}s "
                            f"(actual {elapsed:.1f}s)"
                        )
                    result_queue.put(
                        {
                            "worker_id": worker_id,
                            "q_start": q_start,
                            "q_end": q_end,
                            "elapsed": elapsed,
                            "attempt": attempts + 1,
                            "matches": matches,
                            "no_match": not matches,
                            "ok": True,
                            "error": None,
                        }
                    )
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
                        result_queue.put(
                            {
                                "worker_id": worker_id,
                                "q_start": q_start,
                                "q_end": q_end,
                                "elapsed": time.time() - started,
                                "attempt": attempts,
                                "matches": [],
                                "no_match": False,
                                "ok": False,
                                "error": f"{type(exc).__name__}: {exc}",
                            }
                        )
                        stop_event.set()
                        break
                    time.sleep(retry_delay + random.random())
    finally:
        if worker is not None:
            worker.__exit__(None, None, None)


def main(argv: list[str] | None = None) -> int:
    import queue

    args = parse_args(argv)
    validate_q_range(args.q_start, args.q_end)
    validate_chunk_size(args.chunk_size)
    validate_worker_count(args.workers)
    validate_startup_jobs(args.startup_jobs)
    validate_max_chunk_seconds(args.max_chunk_seconds)

    rom_path = resolve_nbasic_rom_path(args.rom)
    resume_paths = list(args.resume_from)
    if args.results_path is not None:
        resume_paths.append(args.results_path)
    completed_chunks = completed_chunks_from_paths(resume_paths)
    chunk_stream = ChunkStream(
        args.q_start,
        args.q_end,
        args.chunk_size,
        skipped_chunks=completed_chunks,
    )
    result_path = resolve_result_path(
        results_dir=args.results_dir,
        results_path=args.results_path,
        prefix="nbasic-compare-parallel-pool",
        tag=args.tag,
    )
    already_done = len(completed_chunks)

    result_queue: queue.Queue[dict[str, object]] = queue.Queue()
    stop_event = threading.Event()
    startup_semaphore = threading.Semaphore(args.startup_jobs)

    print(
        f"START chunks={chunk_stream.total_chunks} resumed={already_done} workers={args.workers} "
        f"startup_jobs={args.startup_jobs} q_start={args.q_start} q_end={args.q_end} "
        f"chunk_size={args.chunk_size} max_chunk_seconds={args.max_chunk_seconds:.1f} "
        f"results={result_path}",
        flush=True,
    )
    if already_done >= chunk_stream.total_chunks:
        print("COMPLETE nothing to do; all chunks already covered by previous result file(s)", flush=True)
        print(f"RESULTS {result_path}", flush=True)
        return 0
    started = time.time()
    threads = [
        threading.Thread(
            target=worker_loop,
            args=(
                worker_id,
                rom_path,
                args.max_steps,
                args.batch_rounds,
                args.slice_steps,
                chunk_stream,
                result_queue,
                stop_event,
                startup_semaphore,
                args.max_chunk_seconds,
                args.worker_retries,
                args.retry_delay,
                args.startup_stagger,
            ),
            daemon=True,
            name=f"nbasic-compare-worker-{worker_id}",
        )
        for worker_id in range(args.workers)
    ]
    for thread in threads:
        thread.start()

    completed = already_done
    matches: list[str] = []
    while completed < chunk_stream.total_chunks:
        record = result_queue.get()
        chunk_key = (record["q_start"], record["q_end"])
        if chunk_key in completed_chunks:
            continue
        append_result(result_path, record)
        completed_chunks.add(chunk_key)
        completed += 1
        elapsed = time.time() - started
        rate = completed / elapsed if elapsed > 0 else 0.0
        prefix = "ERROR" if not record["ok"] else ("MATCH" if record["matches"] else "NO_MATCH")
        if record["matches"]:
            matches.extend(record["matches"])
        print(
            f'{prefix} chunk={record["q_start"]}-{record["q_end"]} worker={record["worker_id"]} '
            f'attempt={record["attempt"]} completed={completed}/{chunk_stream.total_chunks} '
            f'elapsed={record["elapsed"]:.1f}s rate={rate:.3f} chunks/s',
            flush=True,
        )
        if not record["ok"]:
            print(f'ERROR chunk={record["q_start"]}-{record["q_end"]} {record["error"]}', flush=True)
            stop_event.set()
            break

    for thread in threads:
        thread.join()

    total_elapsed = time.time() - started
    if matches:
        print(f"FOUND {len(matches)} match-lines in {total_elapsed:.1f}s", flush=True)
        for line in matches:
            print(line, flush=True)
        print(f"RESULTS {result_path}", flush=True)
        return 0
    if stop_event.is_set() and completed < chunk_stream.total_chunks:
        print(f"ABORT after {completed}/{chunk_stream.total_chunks} chunks in {total_elapsed:.1f}s", flush=True)
        print(f"RESULTS {result_path}", flush=True)
        return 2
    print(f"COMPLETE no matches in {total_elapsed:.1f}s (resumed={already_done})", flush=True)
    print(f"RESULTS {result_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
