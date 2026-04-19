#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path
import re
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
MACHIN_DIR = Path(__file__).resolve().parents[1]
BAS_DIR = MACHIN_DIR / "bas"
CLASSIC_BASIC_SRC = REPO_ROOT.parent / "classic-basic" / "src"
sys.path.insert(0, str(CLASSIC_BASIC_SRC))

from grants_basic.machine import DEFAULT_ROM_PATH, GrantSearleConfig, GrantSearleMachine


PROGRAM_PATH = BAS_DIR / "grantsbasic-pow.bas"
ENTRY_SIZE = 6
LABELS = ("X", "Y", "Z", "W", "V")


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


def parse_output(text: str) -> list[tuple[str, str, str]]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    rows: list[tuple[str, str, str]] = []
    index = 0
    while index < len(lines):
        match = re.fullmatch(r"(TERMLOW|TERMHIGH|SPLITLOW|SPLITHIGH)\s+(\d+)", lines[index])
        if match is None:
            index += 1
            continue
        if index + 1 >= len(lines):
            raise RuntimeError(f"missing diff line after {lines[index]!r}")
        rows.append((match.group(1), match.group(2), lines[index + 1]))
        index += 2
    if len(rows) != 4:
        raise RuntimeError(f"expected 4 mode rows, found {len(rows)}")
    return rows


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
    rows = parse_output(output)
    result_map = {
        "TERMLOW": values["Y"],
        "TERMHIGH": values["Z"],
        "SPLITLOW": values["W"],
        "SPLITHIGH": values["V"],
    }

    print("BEST")
    print(" ".join(str(value) for value in values["X"]))
    for label, n_value, diff in rows:
        print(f"{label} {n_value}")
        print(" ".join(str(value) for value in result_map[label]))
        print(diff)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
