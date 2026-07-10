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


PROGRAM_PATH = BAS_DIR / "grantsbasic-horner.bas"
ENTRY_SIZE = 6
LABELS = ("X", "Y", "Z", "W")


def read_scalar_block(memory: bytes, labels: tuple[str, ...]) -> dict[str, list[int]]:
    block_size = ENTRY_SIZE * len(labels)
    matches: list[dict[str, list[int]]] = []
    for index in range(len(memory) - block_size + 1):
        values: dict[str, list[int]] = {}
        for offset, label in enumerate(labels):
            base = index + (offset * ENTRY_SIZE)
            if memory[base] != ord(label) or memory[base + 5] != 0:
                break
            values[label] = list(memory[base + 1 : base + 5])
        else:
            matches.append(values)
    if len(matches) != 1:
        raise RuntimeError(f"expected exactly one scalar block, found {len(matches)}")
    return matches[0]


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
    values = read_scalar_block(memory, LABELS)

    print(output.rstrip())
    print("BEST")
    print(" ".join(f"{value:02X}" for value in values["X"]))
    print("ASYMMETRIC")
    print(" ".join(f"{value:02X}" for value in values["Y"]))
    print("RATIONAL2")
    print(" ".join(f"{value:02X}" for value in values["Z"]))
    print("RATIONAL2ALL")
    print(" ".join(f"{value:02X}" for value in values["W"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
