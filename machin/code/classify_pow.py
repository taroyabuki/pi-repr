#!/usr/bin/env python3

from __future__ import annotations

from decimal import Decimal

import collect
import collect_pow


def parse_diff(text: str) -> Decimal:
    return Decimal(text.replace("D", "E"))


def best_mode(parsed: dict[str, tuple[str, list[str], str] | list[str]]) -> tuple[str, str]:
    modes = ("TERMLOW", "TERMHIGH", "SPLITLOW", "SPLITHIGH")
    best_label = modes[0]
    best_diff = parsed[best_label][2]  # type: ignore[index]
    best_abs = abs(parse_diff(best_diff))
    for label in modes[1:]:
        diff = parsed[label][2]  # type: ignore[index]
        current_abs = abs(parse_diff(diff))
        if current_abs < best_abs:
            best_label = label
            best_diff = diff
            best_abs = current_abs
    return best_label, best_diff


def main() -> int:
    loop_rows: dict[str, tuple[str, str]] = {}
    pow_rows: dict[str, tuple[str, str]] = {}

    for config in collect.RUNNER_CONFIGS:
        try:
            loop_rows[config.name] = best_mode(collect.parse_output(collect.run_probe(config)))
        except Exception:
            continue

    for config in collect_pow.RUNNER_CONFIGS:
        try:
            pow_rows[config.name] = best_mode(collect_pow.parse_output(collect_pow.run_probe(config)))
        except Exception:
            continue

    print("| BASIC | `^` の最良 | `^` の bestとの差 | loop の最良 | loop の bestとの差 | 採用 |")
    print("| --- | --- | --- | --- | --- | --- |")
    names = list(pow_rows)
    for name in loop_rows:
        if name not in pow_rows:
            names.append(name)

    for name in names:
        pow_entry = pow_rows.get(name)
        loop_entry = loop_rows.get(name)

        if pow_entry is None and loop_entry is not None:
            print(f"| {name} | skipped | skipped | `{loop_entry[0]}` | `{loop_entry[1]}` | `loop` |")
            continue
        if pow_entry is not None and loop_entry is None:
            print(f"| {name} | `{pow_entry[0]}` | `{pow_entry[1]}` | skipped | skipped | `^` |")
            continue

        assert pow_entry is not None
        assert loop_entry is not None
        pow_label, pow_diff = pow_entry
        loop_label, loop_diff = loop_entry
        use_loop = abs(parse_diff(loop_diff)) < abs(parse_diff(pow_diff))
        adopted = "loop" if use_loop else "^"
        print(
            f"| {name} | `{pow_label}` | `{pow_diff}` | `{loop_label}` | `{loop_diff}` | `{adopted}` |"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
