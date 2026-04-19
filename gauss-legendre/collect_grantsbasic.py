#!/usr/bin/env python3

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLASSIC_BASIC_SRC = ROOT.parent / "classic-basic" / "src"
sys.path.insert(0, str(CLASSIC_BASIC_SRC))

from grants_basic.machine import DEFAULT_ROM_PATH, GrantSearleConfig, GrantSearleMachine


PROGRAM_PATH = Path(__file__).with_name("grantsbasic.bas")
BEST_LABEL = ord("X")
RESULT_LABEL = ord("Z")
ENTRY_SIZE = 6


def read_scalar_pair(memory: bytes) -> tuple[list[int], list[int]]:
    matches: list[tuple[list[int], list[int]]] = []
    for index in range(len(memory) - (2 * ENTRY_SIZE) + 1):
        if memory[index] != BEST_LABEL or memory[index + 5] != 0:
            continue
        if memory[index + 6] != RESULT_LABEL or memory[index + 11] != 0:
            continue
        best = list(memory[index + 1 : index + 5])
        current = list(memory[index + 7 : index + 11])
        matches.append((best, current))
    if len(matches) != 1:
        raise RuntimeError(f"expected exactly one X/Z scalar pair, found {len(matches)}")
    return matches[0]


def parse_output(text: str) -> tuple[str, str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    agm_line = next((line for line in lines if re.fullmatch(r"AGM\s+\d+", line)), None)
    if agm_line is None:
        raise RuntimeError("missing AGM line")
    agm_index = lines.index(agm_line)
    if agm_index + 1 >= len(lines):
        raise RuntimeError("missing diff line")
    return agm_line, lines[agm_index + 1]


def main() -> int:
    machine = GrantSearleMachine(
        GrantSearleConfig(
            rom_path=DEFAULT_ROM_PATH,
            max_steps=200_000,
            boot_step_budget=10_000_000,
            prompt_step_budget=10_000_000,
        )
    )
    machine.boot()
    output = machine.run_program_file(PROGRAM_PATH)
    memory = bytes(machine.memory.read_byte(index) for index in range(0x10000))
    best, current = read_scalar_pair(memory)
    agm_line, diff = parse_output(output)

    print("BEST")
    print(" ".join(str(value) for value in best))
    print(agm_line)
    print(" ".join(str(value) for value in current))
    print(diff)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
