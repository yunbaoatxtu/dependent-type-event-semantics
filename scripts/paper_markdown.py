#!/usr/bin/env python3
"""Shared Markdown parsing helpers for the paper DOCX pipeline."""

from __future__ import annotations

from pathlib import Path


def split_table_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def is_table_separator(line: str) -> bool:
    cells = split_table_row(line)
    return bool(cells) and all(set(cell) <= {"-", ":", " "} and "-" in cell for cell in cells)


def normalize_markdown_inline(text: str) -> str:
    return text.replace("**", "")


def markdown_inline_segments(text: str) -> list[tuple[str, bool]]:
    if "**" not in text:
        return [(text, False)] if text else []

    parts = text.split("**")
    if len(parts) % 2 == 0:
        return [(text, False)]

    return [(part, index % 2 == 1) for index, part in enumerate(parts) if part]


def markdown_text_blocks(path: Path) -> list[str]:
    blocks: list[str] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("|"):
            cells = split_table_row(line)
            if is_table_separator(line):
                continue
            blocks.extend(normalize_markdown_inline(cell) for cell in cells if cell)
            continue
        if line.startswith("# "):
            blocks.append(normalize_markdown_inline(line[2:].strip()))
            continue
        if line.startswith("## "):
            blocks.append(normalize_markdown_inline(line[3:].strip()))
            continue
        if line.startswith("- "):
            blocks.append(normalize_markdown_inline(line[2:].strip()))
            continue
        if line.startswith("_") and line.endswith("_"):
            blocks.append(normalize_markdown_inline(line.strip("_")))
            continue
        blocks.append(normalize_markdown_inline(line))
    return blocks
