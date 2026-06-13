#!/usr/bin/env python3
"""Regenerate the manuscript DOCX from the Markdown source."""

from __future__ import annotations

import argparse
from pathlib import Path

try:
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Inches, Pt, RGBColor
except ImportError as exc:  # pragma: no cover - depends on local document tooling.
    raise SystemExit(
        "python-docx is required. Run this script with the bundled Codex "
        "workspace Python runtime or install python-docx."
    ) from exc


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MARKDOWN = ROOT / "paper" / "dependent_type_replacement_for_event_semantics_sci_manuscript.md"
DEFAULT_DOCX = ROOT / "paper" / "dependent_type_replacement_for_event_semantics_sci_manuscript.docx"


def split_table_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def is_table_separator(line: str) -> bool:
    cells = split_table_row(line)
    return bool(cells) and all(set(cell) <= {"-", ":", " "} and "-" in cell for cell in cells)


def apply_base_styles(document: Document) -> None:
    styles = document.styles
    normal = styles["Normal"]
    normal.font.name = "Arial"
    normal.font.size = Pt(10.5)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.12

    for name, size in [("Heading 1", 15), ("Heading 2", 12.5)]:
        style = styles[name]
        style.font.name = "Arial"
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = RGBColor(43, 110, 171)
        style.paragraph_format.space_before = Pt(12)
        style.paragraph_format.space_after = Pt(6)

    title = styles["Title"]
    title.font.name = "Arial"
    title.font.size = Pt(16)
    title.font.bold = True
    title.font.color.rgb = RGBColor(31, 78, 121)
    title.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.paragraph_format.space_after = Pt(4)


def add_keywords(document: Document, line: str) -> None:
    paragraph = document.add_paragraph()
    prefix = "**Keywords:**"
    if line.startswith(prefix):
        run = paragraph.add_run("Keywords:")
        run.bold = True
        paragraph.add_run(line[len(prefix) :])
    else:
        paragraph.add_run(line)


def add_markdown_table(document: Document, rows: list[list[str]]) -> None:
    if not rows:
        return
    table = document.add_table(rows=1, cols=len(rows[0]))
    table.style = "Table Grid"
    table.autofit = True
    header_cells = table.rows[0].cells
    for index, value in enumerate(rows[0]):
        header_cells[index].text = value
        for paragraph in header_cells[index].paragraphs:
            for run in paragraph.runs:
                run.bold = True

    for row in rows[1:]:
        cells = table.add_row().cells
        for index, value in enumerate(row):
            cells[index].text = value

    for row in table.rows:
        for cell in row.cells:
            for paragraph in cell.paragraphs:
                paragraph.paragraph_format.space_after = Pt(2)


def build_docx(markdown_path: Path, docx_path: Path) -> None:
    document = Document()
    section = document.sections[0]
    section.top_margin = Inches(0.9)
    section.bottom_margin = Inches(0.75)
    section.left_margin = Inches(0.9)
    section.right_margin = Inches(0.9)
    apply_base_styles(document)

    lines = markdown_path.read_text(encoding="utf-8").splitlines()
    index = 0
    while index < len(lines):
        line = lines[index].strip()
        if not line:
            index += 1
            continue

        if line.startswith("# "):
            document.add_paragraph(line[2:].strip(), style="Title")
            index += 1
            continue

        if line.startswith("_") and line.endswith("_") and len(line) > 1:
            paragraph = document.add_paragraph()
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = paragraph.add_run(line.strip("_"))
            run.italic = True
            run.font.color.rgb = RGBColor(91, 107, 120)
            index += 1
            continue

        if line.startswith("## "):
            heading = line[3:].strip()
            if heading == "Functional replacement map":
                document.add_page_break()
            document.add_paragraph(heading, style="Heading 1")
            index += 1
            continue

        if line.startswith("|"):
            table_rows: list[list[str]] = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                current = lines[index].strip()
                if not is_table_separator(current):
                    table_rows.append(split_table_row(current))
                index += 1
            add_markdown_table(document, table_rows)
            continue

        if line.startswith("- "):
            document.add_paragraph(line[2:].strip(), style="List Bullet")
            index += 1
            continue

        if line.startswith("**Keywords:**"):
            add_keywords(document, line)
            index += 1
            continue

        document.add_paragraph(line)
        index += 1

    footer = document.sections[0].footer.paragraphs[0]
    footer.text = "Manuscript draft"
    footer.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    docx_path.parent.mkdir(parents=True, exist_ok=True)
    document.save(docx_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Synchronize the paper DOCX from Markdown.")
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    parser.add_argument("--docx", type=Path, default=DEFAULT_DOCX)
    args = parser.parse_args()
    build_docx(args.markdown, args.docx)
    print(f"wrote {args.docx}")


if __name__ == "__main__":
    main()
