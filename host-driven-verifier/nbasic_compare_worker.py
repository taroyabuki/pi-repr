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

from pc8001_terminal.cli import DEFAULT_ROM_PATH  # noqa: E402
from pc8001_terminal.machine import PC8001Config, PC8001Machine, RomSpec  # noqa: E402

MATCH_TOKEN = "MATCH"
MISS_TOKEN = "MISS"

LESS = -1
EQUAL = 0
GREATER = 1

WORKER_PROGRAM = [
    "10 DEFDBL A-Z",
    "20 A#=3.14159265358979#:POKE VARPTR(A#),194",
    "30 P#=1#:Q#=1#:B#=0#:F%=0:R%=0",
    '40 PRINT "VP";VARPTR(A#);VARPTR(P#);VARPTR(Q#);VARPTR(F%);VARPTR(R%)',
    "50 IF F%=0 THEN 50",
    "60 B#=P#/Q#",
    "70 R%=SGN(B#-A#)",
    "80 F%=0:GOTO 50",
]


def resolve_nbasic_rom_path(path: Path | None) -> Path:
    rom_path = path if path is not None else DEFAULT_ROM_PATH
    resolved = rom_path.expanduser().resolve()
    if not resolved.is_file():
        raise SystemExit(
            f"error: N-BASIC ROM not found: {resolved}. "
            "Run ../classic-basic/setup/nbasic.sh or pass --rom PATH."
        )
    return resolved


def candidate_expr(p: int, q: int) -> str:
    return f"{p}#/{q}#"


def encode_positive_integer(value: int) -> list[int]:
    if value <= 0:
        raise ValueError(f"expected positive integer, got {value}")
    exponent = value.bit_length()
    if exponent > 56:
        raise ValueError(f"value too large for exact MBF double integer encoding: {value}")
    fraction = (value << (56 - exponent)) - (1 << 55)
    return [(fraction >> (8 * index)) & 0xFF for index in range(7)] + [exponent + 128]


class NBasicCompareWorker:
    def __init__(self, *, rom_path: Path, max_steps: int = 100_000, batch_rounds: int = 32, slice_steps: int = 1_000) -> None:
        self._rom_path = rom_path
        self._max_steps = max_steps
        self._batch_rounds = batch_rounds
        self._slice_steps = slice_steps
        self._machine: PC8001Machine | None = None
        self._a_addr = 0
        self._p_addr = 0
        self._q_addr = 0
        self._b_addr = 0
        self._f_addr = 0
        self._r_addr = 0

    def __enter__(self) -> "NBasicCompareWorker":
        self._machine = PC8001Machine(
            PC8001Config(
                roms=(RomSpec(path=self._rom_path, start=0x0000, name=self._rom_path.name),),
                entry_point=0x0000,
                max_steps=self._max_steps,
                batch_rounds=self._batch_rounds,
            )
        )
        self._machine.load_roms()
        self._machine.boot_demo()
        self._machine.consume_console_output()
        for line in WORKER_PROGRAM:
            self._machine.inject_keys([ord(char) for char in line] + [0x0D])
            self._machine._run_host_basic_until_settled()
            self._machine.consume_console_output()
        self._machine.inject_keys([ord(char) for char in "RUN"] + [0x0D])
        self._discover_addresses()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self._machine = None

    def _discover_addresses(self) -> None:
        assert self._machine is not None
        output = ""
        deadline = time.monotonic() + 10.0
        while time.monotonic() < deadline:
            result = self._machine.run_firmware(max_steps=self._slice_steps)
            output += self._machine.consume_console_output()
            match = re.search(r"VP(-?\d+) (-?\d+) (-?\d+) (-?\d+) (-?\d+)", output)
            if match is not None:
                addresses = [int(value) % 65536 for value in match.groups()]
                self._a_addr, self._p_addr, self._q_addr, self._f_addr, self._r_addr = addresses
                # A#, P#, Q#, B# are allocated contiguously in this program and
                # P#/Q# are the same MBF-double type.
                self._b_addr = self._q_addr + (self._q_addr - self._p_addr)
                return
            if result.reason == "input_wait":
                raise RuntimeError(f"worker returned to prompt before addresses were discovered: {output!r}")
        raise RuntimeError(f"worker did not print VARPTR addresses: {output!r}")

    @property
    def addresses(self) -> tuple[int, int, int, int, int, int]:
        return self._a_addr, self._p_addr, self._q_addr, self._b_addr, self._f_addr, self._r_addr

    def read_current_quotient_bytes(self) -> tuple[int, ...]:
        assert self._machine is not None
        return tuple(self._machine.memory.slice(self._b_addr, 8))

    def _write_double(self, address: int, value: int) -> None:
        assert self._machine is not None
        for offset, byte in enumerate(encode_positive_integer(value)):
            self._machine.memory.write_byte(address + offset, byte)

    def _read_signed_word(self, address: int) -> int:
        assert self._machine is not None
        raw = self._machine.memory.read_word(address)
        if raw >= 0x8000:
            raw -= 0x10000
        return raw

    def compare_candidate(self, p: int, q: int) -> int:
        assert self._machine is not None
        self._write_double(self._p_addr, p)
        self._write_double(self._q_addr, q)
        self._machine.memory.write_word(self._r_addr, 0x1234)
        self._machine.memory.write_word(self._f_addr, 1)
        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline:
            result = self._machine.run_firmware(max_steps=self._slice_steps)
            if self._machine.memory.read_word(self._f_addr) == 0:
                compare_result = self._read_signed_word(self._r_addr)
                if compare_result not in (LESS, EQUAL, GREATER):
                    raise RuntimeError(f"unexpected compare result {compare_result} for {p}/{q}")
                return compare_result
            if result.reason == "input_wait":
                raise RuntimeError(
                    f"worker returned to prompt while waiting for compare result for {p}/{q}: "
                    f"{self._machine.format_state_summary()}"
                )
        raise RuntimeError(f"timed out waiting for compare result for {p}/{q}")


def upper_bound_for_q(q: int) -> int:
    if q <= 0:
        raise ValueError(f"expected positive q, got {q}")
    return q * 4


def locate_first_ge(worker: NBasicCompareWorker, q: int) -> tuple[int, int]:
    lo = 1
    hi = upper_bound_for_q(q)
    hi_cmp = worker.compare_candidate(hi, q)
    if hi_cmp == LESS:
        raise RuntimeError(f"upper bound too low for q={q}: p={hi} still less than target")
    while lo < hi:
        mid = (lo + hi) // 2
        cmp_result = worker.compare_candidate(mid, q)
        if cmp_result == LESS:
            lo = mid + 1
        else:
            hi = mid
    return lo, worker.compare_candidate(lo, q)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Tri-state N-BASIC worker with exact compare and binary search helpers.")
    parser.add_argument("--rom", metavar="PATH", type=Path, default=DEFAULT_ROM_PATH if DEFAULT_ROM_PATH.is_file() else None)
    parser.add_argument("--max-steps", type=int, default=100_000)
    parser.add_argument("--batch-rounds", type=int, default=32)
    parser.add_argument("--slice-steps", type=int, default=1_000)
    sub = parser.add_subparsers(dest="command", required=True)

    compare = sub.add_parser("compare")
    compare.add_argument("p", type=int)
    compare.add_argument("q", type=int)

    locate = sub.add_parser("locate")
    locate.add_argument("q", type=int)

    scan = sub.add_parser("scan")
    scan.add_argument("--q-start", type=int, required=True)
    scan.add_argument("--q-end", type=int, required=True)
    scan.add_argument("--stop-on-match", action="store_true")
    scan.add_argument("--progress-every", type=int, default=0)
    return parser


def compare_label(result: int) -> str:
    return {LESS: "LESS", EQUAL: "EQUAL", GREATER: "GREATER"}[result]


def run_compare(worker: NBasicCompareWorker, p: int, q: int) -> int:
    result = worker.compare_candidate(p, q)
    print(f"{compare_label(result)} p={p} q={q} expr={candidate_expr(p, q)}")
    return 0 if result == EQUAL else 1


def run_locate(worker: NBasicCompareWorker, q: int) -> int:
    p, result = locate_first_ge(worker, q)
    verdict = MATCH_TOKEN if result == EQUAL else MISS_TOKEN
    print(f"{verdict} q={q} first_ge_p={p} compare={compare_label(result)} expr={candidate_expr(p, q)}")
    return 0 if result == EQUAL else 1


def run_scan(worker: NBasicCompareWorker, *, q_start: int, q_end: int, stop_on_match: bool, progress_every: int) -> int:
    if q_end < q_start:
        raise SystemExit("error: --q-end must be >= --q-start")
    matched_any = False
    for q in range(q_start, q_end + 1):
        if progress_every and (q - q_start) % progress_every == 0:
            print(f"PROGRESS q={q}", flush=True)
        p, result = locate_first_ge(worker, q)
        if result == EQUAL:
            matched_any = True
            print(f"{MATCH_TOKEN} q={q} p={p} expr={candidate_expr(p, q)}", flush=True)
            if stop_on_match:
                return 0
    if not matched_any:
        print(f"NO_MATCH q_start={q_start} q_end={q_end}", flush=True)
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    rom_path = resolve_nbasic_rom_path(args.rom)
    with NBasicCompareWorker(
        rom_path=rom_path,
        max_steps=args.max_steps,
        batch_rounds=args.batch_rounds,
        slice_steps=args.slice_steps,
    ) as worker:
        if args.command == "compare":
            return run_compare(worker, args.p, args.q)
        if args.command == "locate":
            return run_locate(worker, args.q)
        return run_scan(
            worker,
            q_start=args.q_start,
            q_end=args.q_end,
            stop_on_match=args.stop_on_match,
            progress_every=args.progress_every,
        )


if __name__ == "__main__":
    raise SystemExit(main())
