#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import time
from pathlib import Path


RESULTS_DIR = Path(__file__).resolve().parent / "scan-results"
MAX_WORKERS = 6
DEFAULT_WORKERS = min(MAX_WORKERS, max(1, (os.cpu_count() or 1) // 2))
DEFAULT_MAX_CHUNK_SECONDS = 3600.0


def validate_worker_count(workers: int) -> None:
    if workers <= 0:
        raise SystemExit("error: --workers must be > 0")
    if workers > MAX_WORKERS:
        raise SystemExit(f"error: --workers must be <= {MAX_WORKERS}")


def validate_chunk_size(chunk_size: int) -> None:
    if chunk_size <= 0:
        raise SystemExit("error: --chunk-size must be > 0")


def validate_q_range(q_start: int, q_end: int) -> None:
    if q_end < q_start:
        raise SystemExit("error: --q-end must be >= --q-start")


def validate_startup_jobs(startup_jobs: int) -> None:
    if startup_jobs <= 0:
        raise SystemExit("error: --startup-jobs must be > 0")


def validate_max_chunk_seconds(max_chunk_seconds: float) -> None:
    if max_chunk_seconds <= 0:
        raise SystemExit("error: --max-chunk-seconds must be > 0")


def build_chunks(q_start: int, q_end: int, chunk_size: int) -> list[tuple[int, int]]:
    chunks: list[tuple[int, int]] = []
    start = q_start
    while start <= q_end:
        end = min(start + chunk_size - 1, q_end)
        chunks.append((start, end))
        start = end + 1
    return chunks


def append_result(path: Path, record: dict[str, object]) -> None:
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=True) + "\n")


def completed_chunks_from_paths(paths: list[Path]) -> set[tuple[int, int]]:
    completed: set[tuple[int, int]] = set()
    for path in paths:
        if not path.exists():
            continue
        with path.open(encoding="utf-8") as fh:
            for raw_line in fh:
                raw_line = raw_line.strip()
                if not raw_line:
                    continue
                try:
                    record = json.loads(raw_line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(record, dict):
                    continue
                if not record.get("ok"):
                    continue
                q_start = record.get("q_start")
                q_end = record.get("q_end")
                if not isinstance(q_start, int) or not isinstance(q_end, int):
                    continue
                completed.add((q_start, q_end))
    return completed


def pending_chunks(
    *,
    q_start: int,
    q_end: int,
    chunk_size: int,
    resume_paths: list[Path],
) -> tuple[list[tuple[int, int]], set[tuple[int, int]]]:
    chunks = build_chunks(q_start, q_end, chunk_size)
    completed = completed_chunks_from_paths(resume_paths)
    remaining = [chunk for chunk in chunks if chunk not in completed]
    return remaining, completed


def resolve_result_path(
    *,
    results_dir: Path,
    results_path: Path | None,
    prefix: str,
    tag: str | None,
) -> Path:
    if results_path is not None:
        results_path.parent.mkdir(parents=True, exist_ok=True)
        return results_path
    results_dir.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
    suffix = f"-{tag}" if tag else ""
    return results_dir / f"{prefix}-{timestamp}{suffix}.jsonl"
