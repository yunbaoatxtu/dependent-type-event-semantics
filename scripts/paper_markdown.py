#!/usr/bin/env python3
"""Shared Markdown parsing helpers for the paper DOCX pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class InlineSegment:
    text: str
    bold: bool = False
    italic: bool = False
    code: bool = False


def split_table_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def is_table_separator(line: str) -> bool:
    cells = split_table_row(line)
    return bool(cells) and all(set(cell) <= {"-", ":", " "} and "-" in cell for cell in cells)


def normalize_markdown_inline(text: str) -> str:
    return "".join(segment.text for segment in markdown_inline_segments(text))


def markdown_inline_segments(text: str) -> list[InlineSegment]:
    return _merge_inline_segments(_parse_inline(text))


def _merge_inline_segments(segments: list[InlineSegment]) -> list[InlineSegment]:
    merged: list[InlineSegment] = []
    for segment in segments:
        if not segment.text:
            continue
        if (
            merged
            and merged[-1].bold == segment.bold
            and merged[-1].italic == segment.italic
            and merged[-1].code == segment.code
        ):
            previous = merged[-1]
            merged[-1] = InlineSegment(
                previous.text + segment.text,
                bold=previous.bold,
                italic=previous.italic,
                code=previous.code,
            )
            continue
        merged.append(segment)
    return merged


def _parse_inline(
    text: str,
    *,
    bold: bool = False,
    italic: bool = False,
    code: bool = False,
) -> list[InlineSegment]:
    segments: list[InlineSegment] = []
    index = 0
    while index < len(text):
        if text.startswith("`", index):
            end = text.find("`", index + 1)
            if end == -1:
                segments.append(InlineSegment(text[index:], bold=bold, italic=italic, code=code))
                break
            segments.append(InlineSegment(text[index + 1 : end], bold=bold, italic=italic, code=True))
            index = end + 1
            continue

        if text.startswith("[", index):
            close_bracket = text.find("]", index + 1)
            if (
                close_bracket != -1
                and close_bracket + 1 < len(text)
                and text[close_bracket + 1] == "("
            ):
                close_paren = text.find(")", close_bracket + 2)
                if close_paren != -1:
                    segments.extend(
                        _parse_inline(
                            text[index + 1 : close_bracket],
                            bold=bold,
                            italic=italic,
                            code=code,
                        )
                    )
                    index = close_paren + 1
                    continue

        if text.startswith("**", index):
            end = text.find("**", index + 2)
            if end == -1:
                segments.append(InlineSegment(text[index:], bold=bold, italic=italic, code=code))
                break
            segments.extend(
                _parse_inline(text[index + 2 : end], bold=True, italic=italic, code=code)
            )
            index = end + 2
            continue

        if text.startswith("*", index):
            end = text.find("*", index + 1)
            if end == -1:
                segments.append(InlineSegment(text[index:], bold=bold, italic=italic, code=code))
                break
            segments.extend(
                _parse_inline(text[index + 1 : end], bold=bold, italic=True, code=code)
            )
            index = end + 1
            continue

        next_index = _next_inline_marker(text, index)
        segments.append(InlineSegment(text[index:next_index], bold=bold, italic=italic, code=code))
        index = next_index
    return segments


def _next_inline_marker(text: str, start: int) -> int:
    candidates = [position for marker in ("`", "[", "*") if (position := text.find(marker, start)) != -1]
    return min(candidates) if candidates else len(text)


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
