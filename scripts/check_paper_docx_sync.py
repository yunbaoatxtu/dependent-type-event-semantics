#!/usr/bin/env python3
"""Check that the manuscript DOCX text follows the Markdown source order."""

from __future__ import annotations

import argparse
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

try:
    from scripts.paper_markdown import markdown_text_blocks
except ModuleNotFoundError:  # pragma: no cover - used when run as scripts/check_paper_docx_sync.py.
    from paper_markdown import markdown_text_blocks


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MARKDOWN = ROOT / "paper" / "dependent_type_replacement_for_event_semantics_sci_manuscript.md"
DEFAULT_DOCX = ROOT / "paper" / "dependent_type_replacement_for_event_semantics_sci_manuscript.docx"
WORD_NAMESPACE = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


def docx_text(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        document_xml = archive.read("word/document.xml")
    root = ET.fromstring(document_xml)
    paragraphs = []
    for paragraph in root.findall(".//w:p", WORD_NAMESPACE):
        text = "".join(node.text or "" for node in paragraph.findall(".//w:t", WORD_NAMESPACE))
        if text:
            paragraphs.append(text)
    return "\n".join(paragraphs)


def check_sync(markdown_path: Path, docx_path: Path) -> list[str]:
    rendered_text = docx_text(docx_path)
    cursor = 0
    missing: list[str] = []
    for block in markdown_text_blocks(markdown_path):
        position = rendered_text.find(block, cursor)
        if position == -1:
            missing.append(block)
            continue
        cursor = position + len(block)
    return missing


def format_sync_errors(missing: list[str]) -> str:
    lines = [
        "DOCX is not synchronized with Markdown.",
        "Missing or out-of-order blocks:",
    ]
    for index, block in enumerate(missing, start=1):
        lines.append(f"{index}. {block}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Check that the paper DOCX matches Markdown order.")
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    parser.add_argument("--docx", type=Path, default=DEFAULT_DOCX)
    args = parser.parse_args()

    missing = check_sync(args.markdown, args.docx)
    if missing:
        print(format_sync_errors(missing))
        raise SystemExit(1)
    print("paper DOCX is synchronized with Markdown")


if __name__ == "__main__":
    main()
