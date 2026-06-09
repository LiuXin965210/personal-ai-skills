#!/usr/bin/env python3
"""Validate PRD task breakdown constraints."""

from __future__ import annotations

import argparse
import re
import sys
from decimal import Decimal
from pathlib import Path


EFFORT_RE = re.compile(
    r"后端(?P<backend>\d+(?:\.\d+)?)天\s+前端(?P<frontend>\d+(?:\.\d+)?)天\s+测试(?P<test>\d+(?:\.\d+)?)天"
)
TOTAL_RE = re.compile(r"^\s*总计")
TITLE_RE = re.compile(r"^【[^】]+】(?P<desc>.+?)\s*$")
NUMBERED_RE = re.compile(r"^\s*(?P<num>\d+)\.\s+(?P<desc>.+?)(?:(?:：|:)\s*后端.*)?\s*$")
SUBTASK_RE = re.compile(r"^\s*[-*]\s+")


def dec(value: str) -> Decimal:
    return Decimal(value)


def chinese_len(text: str) -> int:
    return len(re.sub(r"\s+", "", text))


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate PRD task breakdown markdown.")
    parser.add_argument("markdown", type=Path)
    parser.add_argument("--backend", type=dec, required=True)
    parser.add_argument("--frontend", type=dec, required=True)
    parser.add_argument("--test", type=dec, required=True)
    parser.add_argument("--max-group", type=dec, default=Decimal("5"))
    parser.add_argument("--max-total", type=dec, default=Decimal("40"))
    parser.add_argument("--min-desc-len", type=int, default=15)
    parser.add_argument("--max-desc-len", type=int, default=20)
    parser.add_argument("--require-item-effort", action="store_true")
    args = parser.parse_args()

    text = args.markdown.read_text(encoding="utf-8")
    errors: list[str] = []
    totals = {"backend": Decimal("0"), "frontend": Decimal("0"), "test": Decimal("0")}
    item_effort_count = 0
    numbered_count = 0
    total_effort = None

    for line_no, line in enumerate(text.splitlines(), start=1):
        numbered_match = NUMBERED_RE.match(line)
        if numbered_match:
            numbered_count += 1
            desc = numbered_match.group("desc")
            desc = re.sub(r"(?:：|:)\s*后端.*$", "", desc).strip()
            length = chinese_len(desc)
            if length < args.min_desc_len:
                errors.append(f"line {line_no}: task description '{desc}' is {length} chars, below {args.min_desc_len}")
            if length > args.max_desc_len:
                errors.append(f"line {line_no}: task description '{desc}' is {length} chars")

        if SUBTASK_RE.match(line):
            errors.append(f"line {line_no}: subtask bullet is not allowed")

        title_match = TITLE_RE.match(line)
        if title_match:
            desc = title_match.group("desc")
            length = chinese_len(desc)
            if length < args.min_desc_len:
                errors.append(f"line {line_no}: task description '{desc}' is {length} chars, below {args.min_desc_len}")
            if length > args.max_desc_len:
                errors.append(f"line {line_no}: task description '{desc}' is {length} chars")

        effort_match = EFFORT_RE.search(line)
        if effort_match:
            backend = dec(effort_match.group("backend"))
            frontend = dec(effort_match.group("frontend"))
            test = dec(effort_match.group("test"))
            group_total = backend + frontend + test
            if TOTAL_RE.match(line):
                total_effort = {"backend": backend, "frontend": frontend, "test": test}
                continue
            item_effort_count += 1
            if group_total > args.max_group:
                errors.append(f"line {line_no}: group total {group_total} exceeds {args.max_group}")
            totals["backend"] += backend
            totals["frontend"] += frontend
            totals["test"] += test

    if total_effort is None:
        errors.append("no total effort line found")
        total_effort = totals
    if args.require_item_effort and item_effort_count == 0:
        errors.append("no item effort lines found")
    if numbered_count == 0:
        errors.append("no numbered task items found")
    if args.require_item_effort and numbered_count and numbered_count != item_effort_count:
        errors.append(f"numbered task count {numbered_count} does not match item effort line count {item_effort_count}")
    if not args.require_item_effort and item_effort_count:
        errors.append("item effort lines are not allowed by default; use --require-item-effort if intended")
    total = total_effort["backend"] + total_effort["frontend"] + total_effort["test"]
    if total > args.max_total:
        errors.append(f"overall total {total} exceeds {args.max_total}")

    expected = {"backend": args.backend, "frontend": args.frontend, "test": args.test}
    for key, label in [("backend", "后端"), ("frontend", "前端"), ("test", "测试")]:
        if total_effort[key] != expected[key]:
            errors.append(f"{label} total {total_effort[key]} does not match expected {expected[key]}")

    if errors:
        print("Validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(
        f"OK: {numbered_count} items, 后端{total_effort['backend']}天 前端{total_effort['frontend']}天 测试{total_effort['test']}天 合计{total}天"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
