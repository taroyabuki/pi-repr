#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
MACHIN_DIR = Path(__file__).resolve().parents[1]
BAS_DIR = MACHIN_DIR / "bas"
CLASSIC_BASIC_SRC = REPO_ROOT.parent / "classic-basic" / "src"
sys.path.insert(0, str(CLASSIC_BASIC_SRC))

from grants_basic.machine import DEFAULT_ROM_PATH, GrantSearleConfig, GrantSearleMachine


PROGRAM_PATH = BAS_DIR / "grantsbasic-builtin.bas"
ENTRY_SIZE = 6


def read_adjacent_pair(memory: bytes, first_label: int, second_label: int) -> tuple[list[int], list[int]]:
    matches: list[tuple[list[int], list[int]]] = []
    for index in range(len(memory) - (2 * ENTRY_SIZE) + 1):
        if memory[index] != first_label or memory[index + 5] != 0:
            continue
        if memory[index + 6] != second_label or memory[index + 11] != 0:
            continue
        first = list(memory[index + 1 : index + 5])
        second = list(memory[index + 7 : index + 11])
        matches.append((first, second))
    if len(matches) != 1:
        raise RuntimeError(f"expected exactly one adjacent pair, found {len(matches)}")
    return matches[0]


def extract_diff(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    marker = lines.index("MACHIN")
    return lines[marker + 1]


def main() -> int:
    machine = GrantSearleMachine(
        GrantSearleConfig(
            rom_path=DEFAULT_ROM_PATH,
            max_steps=500_000,
            boot_step_budget=10_000_000,
            prompt_step_budget=50_000_000,
        )
    )
    machine.boot()
    output = machine.run_program_file(PROGRAM_PATH)
    memory = bytes(machine.memory.read_byte(index) for index in range(0x10000))
    best, machin = read_adjacent_pair(memory, ord("X"), ord("Z"))
    diff = extract_diff(output)

    print("BEST")
    print(" ".join(str(value) for value in best))
    print("MACHIN")
    print(" ".join(str(value) for value in machin))
    print(diff)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
