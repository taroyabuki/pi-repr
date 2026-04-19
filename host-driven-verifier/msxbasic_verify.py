#!/usr/bin/env python3

from __future__ import annotations

import argparse
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
import sys
from typing import Iterable


WORK_ROOT = Path(__file__).resolve().parents[2]
CLASSIC_BASIC_SRC = WORK_ROOT / "classic-basic" / "src"
if str(CLASSIC_BASIC_SRC) not in sys.path:
    sys.path.insert(0, str(CLASSIC_BASIC_SRC))

from msx_basic.bridge import OpenMSXBridge  # noqa: E402
from msx_basic.cli import _DEFAULT_ROM_DIR, _DEFAULT_ROM_FILE, _create_machine_config  # noqa: E402
from msx_basic.loop import (  # noqa: E402
    _BATCH_INPUT_TIMEOUT,
    _get_screen_state,
    _post_run_prompt_visible,
    _type_text_chunks,
    _wait_for_ok_prompt,
)


MSX_BEST = Fraction(31415926535898, 10**13)
MATCH_TOKEN = "MATCH"
MISS_TOKEN = "MISS"


@dataclass(frozen=True)
class CandidateResult:
    p: int
    q: int
    matched: bool
    output_lines: tuple[str, ...]


def round_half_up(value: Fraction) -> int:
    whole = value.numerator // value.denominator
    frac = value - whole
    if frac >= Fraction(1, 2):
        return whole + 1
    return whole


def offset_order(radius: int) -> list[int]:
    offsets = [0]
    for delta in range(1, radius + 1):
        offsets.append(delta)
        offsets.append(-delta)
    return offsets


def candidate_expr(p: int, q: int) -> str:
    return f"{p}#/{q}#"


class MsxBasicVerifier:
    def __init__(
        self,
        *,
        machine: str,
        extra_rom_path: str | None,
    ) -> None:
        self._bridge = OpenMSXBridge(machine=machine, extra_rom_path=extra_rom_path)

    def __enter__(self) -> "MsxBasicVerifier":
        self._bridge.start()
        self._bridge.command("set throttle off")
        if not self._bridge.wait_for_boot(timeout=10.0):
            raise RuntimeError("MSX-BASIC Ok prompt not detected within 10 seconds")
        if not _wait_for_ok_prompt(self._bridge, timeout=4.0):
            raise RuntimeError("MSX-BASIC prompt did not become ready")
        self.run_immediate("NEW")
        self.run_immediate("A#=4#*ATN(1#)")
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self._bridge.stop()

    def wait_for_prompt(self, *, timeout: float) -> bool:
        if _wait_for_ok_prompt(self._bridge, timeout=timeout):
            return True
        try:
            lines, cursor_row = _get_screen_state(self._bridge, timeout=1.0)
        except TimeoutError:
            return False
        return _post_run_prompt_visible(lines, cursor_row)

    def run_immediate(self, line: str) -> list[str]:
        if not self.wait_for_prompt(timeout=4.0):
            raise RuntimeError(f"prompt not ready before: {line}")
        initial_lines, initial_cursor_row = _get_screen_state(self._bridge, timeout=1.0)
        _type_text_chunks(self._bridge, line)
        self._bridge.type_text("\r", via_keybuf=True, timeout=_BATCH_INPUT_TIMEOUT)
        departed = False
        for _ in range(100):
            lines, cursor_row = _get_screen_state(self._bridge, timeout=1.0)
            if lines != initial_lines or cursor_row != initial_cursor_row:
                departed = True
                break
        if not departed:
            raise RuntimeError(f"command did not leave prompt state: {line}")
        if not self.wait_for_prompt(timeout=10.0):
            raise RuntimeError(f"prompt did not return after: {line}")
        lines, _ = _get_screen_state(self._bridge, timeout=1.0)
        visible = []
        for raw in lines:
            stripped = raw.strip()
            if not stripped or stripped == "Ok" or stripped == line.strip():
                continue
            if stripped == "color  auto   goto   list   run":
                continue
            visible.append(stripped)
        return visible

    def check_candidate(self, p: int, q: int) -> CandidateResult:
        self.run_immediate(f"P#={p}#")
        self.run_immediate(f"Q#={q}#")
        self.run_immediate("B#=P#/Q#")
        lines = self.run_immediate("PRINT B#=A#")
        truth = next((line.strip() for line in lines if line.strip() in {"-1", "0"}), None)
        if truth is None:
            raise RuntimeError(f"no boolean verdict for {p}/{q}")
        verdict = MATCH_TOKEN if truth == "-1" else MISS_TOKEN
        return CandidateResult(
            p=p,
            q=q,
            matched=(verdict == MATCH_TOKEN),
            output_lines=tuple(lines),
        )


def resolve_msx_config(args: argparse.Namespace) -> tuple[str, str | None]:
    if args.machine:
        extra_rom_path = str(args.rom_dir) if args.rom_dir.is_dir() else None
        return args.machine, extra_rom_path

    rom_path = args.rom
    if rom_path is None:
        if _DEFAULT_ROM_FILE.is_file():
            rom_path = _DEFAULT_ROM_FILE
        else:
            raise SystemExit(
                "error: no ROM available. Run ../classic-basic/setup/msxbasic.sh or pass --rom PATH."
            )

    resolved_rom = rom_path.expanduser().resolve()
    if not resolved_rom.is_file():
        raise SystemExit(f"error: ROM file not found: {resolved_rom}")
    machine, _ = _create_machine_config(resolved_rom)
    return machine, None


def iter_scan_candidates(q_start: int, q_end: int, radius: int) -> Iterable[tuple[int, int, int]]:
    offsets = offset_order(radius)
    for q in range(q_start, q_end + 1):
        center = round_half_up(MSX_BEST * q)
        for offset in offsets:
            yield q, center + offset, offset


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Host-driven verifier for MSX-BASIC rational candidates.",
    )
    source = parser.add_mutually_exclusive_group()
    source.add_argument(
        "--rom",
        metavar="PATH",
        type=Path,
        default=_DEFAULT_ROM_FILE if _DEFAULT_ROM_FILE.is_file() else None,
        help=f"Path to a 32 KB MSX1 BIOS+BASIC ROM. Default: {_DEFAULT_ROM_FILE}",
    )
    source.add_argument(
        "--machine",
        metavar="NAME",
        default=None,
        help="openMSX machine name to use instead of a ROM path.",
    )
    parser.add_argument(
        "--rom-dir",
        metavar="DIR",
        type=Path,
        default=_DEFAULT_ROM_DIR,
        help=f"Extra ROM search path for openMSX. Default: {_DEFAULT_ROM_DIR}",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    check_parser = subparsers.add_parser("check", help="Check one candidate p/q.")
    check_parser.add_argument("p", type=int)
    check_parser.add_argument("q", type=int)

    scan_parser = subparsers.add_parser(
        "scan",
        help="Check round(best*q) and nearby candidates for q in a range.",
    )
    scan_parser.add_argument("--q-start", type=int, required=True)
    scan_parser.add_argument("--q-end", type=int, required=True)
    scan_parser.add_argument("--radius", type=int, default=2)
    scan_parser.add_argument(
        "--stop-on-match",
        action="store_true",
        help="Exit immediately after the first MATCH.",
    )
    scan_parser.add_argument(
        "--progress-every",
        type=int,
        default=0,
        help="Print progress every N denominators. 0 disables progress lines.",
    )

    return parser


def run_check(verifier: MsxBasicVerifier, p: int, q: int) -> int:
    result = verifier.check_candidate(p, q)
    verdict = MATCH_TOKEN if result.matched else MISS_TOKEN
    print(f"{verdict} p={result.p} q={result.q} expr={candidate_expr(result.p, result.q)}")
    return 0 if result.matched else 1


def run_scan(
    *,
    machine: str,
    extra_rom_path: str | None,
    q_start: int,
    q_end: int,
    radius: int,
    stop_on_match: bool,
    progress_every: int,
) -> int:
    if q_end < q_start:
        raise SystemExit("error: --q-end must be >= --q-start")
    if radius < 0:
        raise SystemExit("error: --radius must be >= 0")

    matched_any = False
    offsets = offset_order(radius)
    for q in range(q_start, q_end + 1):
        if progress_every and (q - q_start) % progress_every == 0:
            print(f"PROGRESS q={q}", flush=True)
        center = round_half_up(MSX_BEST * q)
        with MsxBasicVerifier(machine=machine, extra_rom_path=extra_rom_path) as verifier:
            for offset in offsets:
                p = center + offset
                result = verifier.check_candidate(p, q)
                if result.matched:
                    matched_any = True
                    print(
                        f"{MATCH_TOKEN} q={q} p={p} d={offset} expr={candidate_expr(p, q)}",
                        flush=True,
                    )
                    if stop_on_match:
                        return 0

    if not matched_any:
        print(f"NO_MATCH q_start={q_start} q_end={q_end} radius={radius}", flush=True)
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    machine, extra_rom_path = resolve_msx_config(args)

    if args.command == "check":
        with MsxBasicVerifier(machine=machine, extra_rom_path=extra_rom_path) as verifier:
            return run_check(verifier, args.p, args.q)
    if args.command == "scan":
        return run_scan(
            machine=machine,
            extra_rom_path=extra_rom_path,
            q_start=args.q_start,
            q_end=args.q_end,
            radius=args.radius,
            stop_on_match=args.stop_on_match,
            progress_every=args.progress_every,
        )
    raise AssertionError("unreachable")


if __name__ == "__main__":
    raise SystemExit(main())
