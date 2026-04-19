#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def extract_rows(path: Path, headings: tuple[str, ...]) -> list[list[str]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    level = 0
    table: list[list[str]] = []
    for line in lines:
        if level < len(headings) and line == headings[level]:
            level += 1
            continue
        if level < len(headings):
            continue
        if line.startswith("## ") or line.startswith("### "):
            break
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        parts = [part.strip() for part in stripped.strip("|").split("|")]
        if len(parts) >= 3:
            table.append(parts)
    return table


def main() -> int:
    machin = REPO_ROOT / "machin/README.md"
    print("| 系統 | 方式 | 処理系 / 型 | 低次から足す | bestとの差 | 高次から足す | bestとの差 |")
    print("| --- | --- | --- | --- | --- | --- | --- |")
    for mode in ("TERM", "SPLIT"):
        basic = extract_rows(machin, ("## BASIC", f"### {mode}"))
        c_rows = extract_rows(machin, ("## C言語（x86_64, GNU gcc）", f"### {mode}"))
        for row in basic[2:]:
            print(f"| BASIC | {mode} | {row[0]} | {row[2]} | {row[4]} | {row[5]} | {row[7]} |")
        for row in c_rows[2:]:
            print(f"| C | {mode} | {row[0]} | {row[2]} | {row[3]} | {row[4]} | {row[5]} |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
