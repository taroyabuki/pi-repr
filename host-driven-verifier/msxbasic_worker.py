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

WORKER_PROGRAM = [
    '10 A#=4#*ATN(1#):P#=1#:Q#=1#:B#=0#:F%=0:R%=0',
    '15 PRINT "VP";VARPTR(P#);VARPTR(Q#);VARPTR(F%);VARPTR(R%)',
    '20 IF F%=0 THEN 20',
    '30 B#=P#/Q#',
    '40 IF B#=A# THEN R%=-1 ELSE R%=0',
    '50 F%=0:GOTO 20',
]


def encode_positive_integer(value: int) -> list[int]:
    if value <= 0:
        raise ValueError(f"expected positive integer, got {value}")
    digits = str(value)
    if len(digits) > 14:
        raise ValueError(f"value too large for 14-digit MSX BCD double: {value}")
    exponent = 0x40 + len(digits)
    packed_digits = (digits + '0' * 14)[:14]
    result = [exponent]
    for start in range(0, 14, 2):
        result.append(int(packed_digits[start : start + 2], 16))
    return result


class MsxBasicWorker:
    def __init__(self, *, machine: str, extra_rom_path: str | None) -> None:
        self._verifier = base.MsxBasicVerifier(machine=machine, extra_rom_path=extra_rom_path)
        self._bridge = None
        self._p_addr = 0
        self._q_addr = 0
        self._f_addr = 0
        self._r_addr = 0

    def __enter__(self) -> "MsxBasicWorker":
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

    @property
    def addresses(self) -> tuple[int, int, int, int]:
        return self._p_addr, self._q_addr, self._f_addr, self._r_addr

    def check_candidate(self, p: int, q: int) -> bool:
        assert self._bridge is not None
        parts: list[str] = []
        for offset, byte in enumerate(encode_positive_integer(p)):
            parts.append(f'poke 0x{self._p_addr + offset:04X} 0x{byte:02X}')
        for offset, byte in enumerate(encode_positive_integer(q)):
            parts.append(f'poke 0x{self._q_addr + offset:04X} 0x{byte:02X}')
        parts.append(f'poke16 0x{self._r_addr:04X} 2')
        parts.append(f'poke16 0x{self._f_addr:04X} 1')
        self._bridge.command('; '.join(parts))
        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline:
            if self._bridge.peek16(self._f_addr) == 0:
                return self._bridge.peek16(self._r_addr) == 0xFFFF
            time.sleep(0.0005)
        raise RuntimeError(f'timed out waiting for worker result for {p}/{q}')


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Fast MSX-BASIC worker-based verifier.')
    source = parser.add_mutually_exclusive_group()
    source.add_argument('--rom', metavar='PATH', type=Path, default=base._DEFAULT_ROM_FILE if base._DEFAULT_ROM_FILE.is_file() else None)
    source.add_argument('--machine', metavar='NAME', default=None)
    parser.add_argument('--rom-dir', metavar='DIR', type=Path, default=base._DEFAULT_ROM_DIR)
    sub = parser.add_subparsers(dest='command', required=True)
    check = sub.add_parser('check')
    check.add_argument('p', type=int)
    check.add_argument('q', type=int)
    scan = sub.add_parser('scan')
    scan.add_argument('--q-start', type=int, required=True)
    scan.add_argument('--q-end', type=int, required=True)
    scan.add_argument('--radius', type=int, default=0)
    scan.add_argument('--stop-on-match', action='store_true')
    scan.add_argument('--progress-every', type=int, default=0)
    return parser


def run_check(worker: MsxBasicWorker, p: int, q: int) -> int:
    matched = worker.check_candidate(p, q)
    verdict = base.MATCH_TOKEN if matched else base.MISS_TOKEN
    print(f'{verdict} p={p} q={q} expr={base.candidate_expr(p, q)}')
    return 0 if matched else 1


def run_scan(worker: MsxBasicWorker, *, q_start: int, q_end: int, radius: int, stop_on_match: bool, progress_every: int) -> int:
    if q_end < q_start:
        raise SystemExit('error: --q-end must be >= --q-start')
    if radius < 0:
        raise SystemExit('error: --radius must be >= 0')
    matched_any = False
    offsets = base.offset_order(radius)
    for q in range(q_start, q_end + 1):
        if progress_every and (q - q_start) % progress_every == 0:
            print(f'PROGRESS q={q}', flush=True)
        center = base.round_half_up(base.MSX_BEST * q)
        for offset in offsets:
            p = center + offset
            if worker.check_candidate(p, q):
                matched_any = True
                print(f'{base.MATCH_TOKEN} q={q} p={p} d={offset} expr={base.candidate_expr(p, q)}', flush=True)
                if stop_on_match:
                    return 0
    if not matched_any:
        print(f'NO_MATCH q_start={q_start} q_end={q_end} radius={radius}', flush=True)
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    machine, extra_rom_path = base.resolve_msx_config(args)
    with MsxBasicWorker(machine=machine, extra_rom_path=extra_rom_path) as worker:
        if args.command == 'check':
            return run_check(worker, args.p, args.q)
        return run_scan(worker, q_start=args.q_start, q_end=args.q_end, radius=args.radius, stop_on_match=args.stop_on_match, progress_every=args.progress_every)


if __name__ == '__main__':
    raise SystemExit(main())
