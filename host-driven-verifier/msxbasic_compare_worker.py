#!/usr/bin/env python3

from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path

WORK_ROOT = Path(__file__).resolve().parents[2]
CLASSIC_BASIC_SRC = WORK_ROOT / "classic-basic" / "src"
if str(CLASSIC_BASIC_SRC) not in sys.path:
    sys.path.insert(0, str(CLASSIC_BASIC_SRC))

from msx_basic.loop import _BATCH_INPUT_TIMEOUT, _get_screen_state, _type_text_chunks  # noqa: E402
import msxbasic_verify as base  # noqa: E402
from msxbasic_worker import encode_positive_integer  # noqa: E402

WORKER_PROGRAM = [
    '10 A#=4#*ATN(1#):P#=1#:Q#=1#:B#=0#:F%=0:R%=0',
    '15 PRINT "VP";VARPTR(P#);VARPTR(Q#);VARPTR(F%);VARPTR(R%)',
    '20 IF F%=0 THEN 20',
    '30 B#=P#/Q#',
    '40 R%=SGN(B#-A#)',
    '50 F%=0:GOTO 20',
]

LESS = -1
EQUAL = 0
GREATER = 1


class MsxBasicCompareWorker:
    def __init__(self, *, machine: str, extra_rom_path: str | None) -> None:
        self._verifier = base.MsxBasicVerifier(machine=machine, extra_rom_path=extra_rom_path)
        self._bridge = None
        self._p_addr = 0
        self._q_addr = 0
        self._f_addr = 0
        self._r_addr = 0

    def __enter__(self) -> "MsxBasicCompareWorker":
        self._verifier.__enter__()
        self._bridge = self._verifier._bridge
        for line in WORKER_PROGRAM:
            self._verifier.run_immediate(line)
        _type_text_chunks(self._bridge, 'RUN')
        self._bridge.type_text("\r", via_keybuf=True, timeout=_BATCH_INPUT_TIMEOUT)
        self._discover_addresses()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self._verifier.__exit__(exc_type, exc, tb)

    def _discover_addresses(self) -> None:
        assert self._bridge is not None
        deadline = time.monotonic() + 10.0
        while time.monotonic() < deadline:
            lines, _ = _get_screen_state(self._bridge, timeout=1.0)
            text = ' | '.join(line.strip() for line in lines if line.strip())
            match = re.search(r'VP(-?\d+) (-?\d+) (-?\d+) (-?\d+)', text)
            if match:
                self._p_addr, self._q_addr, self._f_addr, self._r_addr = [int(x) % 65536 for x in match.groups()]
                return
            time.sleep(0.05)
        raise RuntimeError('worker did not print VARPTR addresses')

    def compare_candidate(self, p: int, q: int) -> int:
        assert self._bridge is not None
        parts: list[str] = []
        for offset, byte in enumerate(encode_positive_integer(p)):
            parts.append(f'poke 0x{self._p_addr + offset:04X} 0x{byte:02X}')
        for offset, byte in enumerate(encode_positive_integer(q)):
            parts.append(f'poke 0x{self._q_addr + offset:04X} 0x{byte:02X}')
        parts.append(f'poke16 0x{self._r_addr:04X} 0x1234')
        parts.append(f'poke16 0x{self._f_addr:04X} 1')
        self._bridge.command('; '.join(parts))
        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline:
            if self._bridge.peek16(self._f_addr) == 0:
                raw = self._bridge.peek16(self._r_addr)
                if raw >= 0x8000:
                    raw -= 0x10000
                if raw not in (LESS, EQUAL, GREATER):
                    raise RuntimeError(f'unexpected compare result {raw} for {p}/{q}')
                return raw
            time.sleep(0.0005)
        raise RuntimeError(f'timed out waiting for compare result for {p}/{q}')


def upper_bound_for_q(q: int) -> int:
    if q <= 0:
        raise ValueError(f'expected positive q, got {q}')
    return q * 4


def locate_first_ge(worker: MsxBasicCompareWorker, q: int) -> tuple[int, int]:
    lo = 1
    hi = upper_bound_for_q(q)
    hi_cmp = worker.compare_candidate(hi, q)
    if hi_cmp == LESS:
        raise RuntimeError(f'upper bound too low for q={q}: p={hi} still less than target')
    while lo < hi:
        mid = (lo + hi) // 2
        cmp_result = worker.compare_candidate(mid, q)
        if cmp_result == LESS:
            lo = mid + 1
        else:
            hi = mid
    return lo, worker.compare_candidate(lo, q)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Tri-state MSX-BASIC worker with exact compare and binary search helpers.')
    source = parser.add_mutually_exclusive_group()
    source.add_argument('--rom', metavar='PATH', type=Path, default=base._DEFAULT_ROM_FILE if base._DEFAULT_ROM_FILE.is_file() else None)
    source.add_argument('--machine', metavar='NAME', default=None)
    parser.add_argument('--rom-dir', metavar='DIR', type=Path, default=base._DEFAULT_ROM_DIR)
    sub = parser.add_subparsers(dest='command', required=True)

    compare = sub.add_parser('compare')
    compare.add_argument('p', type=int)
    compare.add_argument('q', type=int)

    locate = sub.add_parser('locate')
    locate.add_argument('q', type=int)

    scan = sub.add_parser('scan')
    scan.add_argument('--q-start', type=int, required=True)
    scan.add_argument('--q-end', type=int, required=True)
    scan.add_argument('--stop-on-match', action='store_true')
    scan.add_argument('--progress-every', type=int, default=0)
    return parser


def compare_label(result: int) -> str:
    return {LESS: 'LESS', EQUAL: 'EQUAL', GREATER: 'GREATER'}[result]


def run_compare(worker: MsxBasicCompareWorker, p: int, q: int) -> int:
    result = worker.compare_candidate(p, q)
    print(f'{compare_label(result)} p={p} q={q} expr={base.candidate_expr(p, q)}')
    return 0 if result == EQUAL else 1


def run_locate(worker: MsxBasicCompareWorker, q: int) -> int:
    p, result = locate_first_ge(worker, q)
    verdict = base.MATCH_TOKEN if result == EQUAL else base.MISS_TOKEN
    print(f'{verdict} q={q} first_ge_p={p} compare={compare_label(result)} expr={base.candidate_expr(p, q)}')
    return 0 if result == EQUAL else 1


def run_scan(worker: MsxBasicCompareWorker, *, q_start: int, q_end: int, stop_on_match: bool, progress_every: int) -> int:
    if q_end < q_start:
        raise SystemExit('error: --q-end must be >= --q-start')
    matched_any = False
    for q in range(q_start, q_end + 1):
        if progress_every and (q - q_start) % progress_every == 0:
            print(f'PROGRESS q={q}', flush=True)
        p, result = locate_first_ge(worker, q)
        if result == EQUAL:
            matched_any = True
            print(f'{base.MATCH_TOKEN} q={q} p={p} expr={base.candidate_expr(p, q)}', flush=True)
            if stop_on_match:
                return 0
    if not matched_any:
        print(f'NO_MATCH q_start={q_start} q_end={q_end}', flush=True)
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    machine, extra_rom_path = base.resolve_msx_config(args)
    with MsxBasicCompareWorker(machine=machine, extra_rom_path=extra_rom_path) as worker:
        if args.command == 'compare':
            return run_compare(worker, args.p, args.q)
        if args.command == 'locate':
            return run_locate(worker, args.q)
        return run_scan(worker, q_start=args.q_start, q_end=args.q_end, stop_on_match=args.stop_on_match, progress_every=args.progress_every)


if __name__ == '__main__':
    raise SystemExit(main())
