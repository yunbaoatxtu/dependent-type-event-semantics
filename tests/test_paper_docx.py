import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

from scripts.check_paper_docx_sync import check_sync, format_sync_errors
from scripts.paper_markdown import (
    InlineSegment,
    markdown_inline_segments,
    markdown_text_blocks,
    normalize_markdown_inline,
)
from scripts.sync_paper_docx import build_docx


ROOT = Path(__file__).resolve().parents[1]
WORD_NAMESPACE = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


def write_minimal_docx(path: Path, paragraphs: list[str]) -> None:
    namespace = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    body = "".join(
        f"<w:p><w:r><w:t>{escape(paragraph)}</w:t></w:r></w:p>" for paragraph in paragraphs
    )
    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:document xmlns:w="{namespace}"><w:body>{body}</w:body></w:document>'
    )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("word/document.xml", document)


def python_docx_available() -> bool:
    try:
        import docx  # noqa: F401
    except ImportError:
        return False
    return True


def docx_run_styles(path: Path) -> list[tuple[str, bool, bool, bool]]:
    with zipfile.ZipFile(path) as archive:
        document_xml = archive.read("word/document.xml")
    root = ET.fromstring(document_xml)
    records: list[tuple[str, bool, bool, bool]] = []
    for run in root.findall(".//w:r", WORD_NAMESPACE):
        text = "".join(node.text or "" for node in run.findall(".//w:t", WORD_NAMESPACE))
        if text:
            run_properties = run.find("w:rPr", WORD_NAMESPACE)
            is_bold = (
                run_properties is not None
                and run_properties.find("w:b", WORD_NAMESPACE) is not None
            )
            is_italic = (
                run_properties is not None
                and run_properties.find("w:i", WORD_NAMESPACE) is not None
            )
            font_values = []
            if run_properties is not None:
                fonts = run_properties.find("w:rFonts", WORD_NAMESPACE)
                if fonts is not None:
                    font_values = list(fonts.attrib.values())
            records.append((text, is_bold, is_italic, "Courier New" in font_values))
    return records


def markdown_boundary_fixture() -> tuple[str, list[str]]:
    markdown = (
        "# **Title & Scope**\n\n"
        "_Manuscript <draft> & check_\n\n"
        "## **Section <A> & B**\n\n"
        "- **Bullet** with A < B & C\n\n"
        "| **Col <1>** | Col & 2 |\n"
        "| --- | --- |\n"
        "| **Cell A** | Cell <B> & C |\n"
        "\n"
        "Between tables.\n\n"
        "| Left | Right |\n"
        "| --- | --- |\n"
        "| More <left> | More & right |\n"
        "\n"
        "Inline `code`, *emphasis*, and [visible link](https://example.test).\n"
    )
    expected_blocks = [
        "Title & Scope",
        "Manuscript <draft> & check",
        "Section <A> & B",
        "Bullet with A < B & C",
        "Col <1>",
        "Col & 2",
        "Cell A",
        "Cell <B> & C",
        "Between tables.",
        "Left",
        "Right",
        "More <left>",
        "More & right",
        "Inline code, emphasis, and visible link.",
    ]
    return markdown, expected_blocks


class PaperDocxTests(unittest.TestCase):
    def test_paper_mentions_diagnostic_recovery_actions(self) -> None:
        manuscript = (
            ROOT / "paper" / "dependent_type_replacement_for_event_semantics_sci_manuscript.md"
        ).read_text(encoding="utf-8")
        self.assertIn("machine-readable failure_stage field", manuscript)
        self.assertIn("structured recovery_actions", manuscript)
        self.assertIn("Next Steps panel", manuscript)
        self.assertIn("data-action-kind", manuscript)
        self.assertIn("stage-local diagnostics", manuscript)

    def test_paper_docx_is_synchronized_with_markdown_order(self) -> None:
        markdown_path = ROOT / "paper" / "dependent_type_replacement_for_event_semantics_sci_manuscript.md"
        docx_path = ROOT / "paper" / "dependent_type_replacement_for_event_semantics_sci_manuscript.docx"
        self.assertEqual(check_sync(markdown_path, docx_path), [])

    def test_paper_docx_sync_reports_missing_paragraph(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            markdown_path = temp / "paper.md"
            docx_path = temp / "paper.docx"
            markdown_path.write_text(
                "# Title\n\nFirst paragraph.\n\nSecond paragraph.\n",
                encoding="utf-8",
            )
            write_minimal_docx(docx_path, ["Title", "First paragraph."])

            missing = check_sync(markdown_path, docx_path)
            self.assertEqual(missing, ["Second paragraph."])
            self.assertIn("1. Second paragraph.", format_sync_errors(missing))

    def test_paper_docx_sync_reports_out_of_order_block(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            markdown_path = temp / "paper.md"
            docx_path = temp / "paper.docx"
            markdown_path.write_text(
                "# Title\n\nFirst block.\n\nSecond block.\n\nThird block.\n",
                encoding="utf-8",
            )
            write_minimal_docx(
                docx_path,
                ["Title", "First block.", "Third block.", "Second block."],
            )

            missing = check_sync(markdown_path, docx_path)
            self.assertEqual(missing, ["Third block."])
            self.assertIn("1. Third block.", format_sync_errors(missing))

    def test_paper_docx_sync_reports_missing_table_cell(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            markdown_path = temp / "paper.md"
            docx_path = temp / "paper.docx"
            markdown_path.write_text(
                (
                    "# Title\n\n"
                    "| Event-semantic function | Dependent-type replacement | Canonical constructor |\n"
                    "| --- | --- | --- |\n"
                    "| Variable polyadicity | Natural-number-indexed verb families | V : Pi n : Nat. Vk-ADV(n) |\n"
                ),
                encoding="utf-8",
            )
            write_minimal_docx(
                docx_path,
                [
                    "Title",
                    "Event-semantic function",
                    "Dependent-type replacement",
                    "Canonical constructor",
                    "Variable polyadicity",
                    "V : Pi n : Nat. Vk-ADV(n)",
                ],
            )

            missing = check_sync(markdown_path, docx_path)
            self.assertEqual(missing, ["Natural-number-indexed verb families"])
            self.assertIn(
                "1. Natural-number-indexed verb families",
                format_sync_errors(missing),
            )

    def test_paper_docx_sync_extracts_markdown_boundary_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            markdown_path = Path(directory) / "paper.md"
            markdown, expected_blocks = markdown_boundary_fixture()
            markdown_path.write_text(markdown, encoding="utf-8")

            self.assertEqual(markdown_text_blocks(markdown_path), expected_blocks)

    def test_paper_docx_sync_matches_boundary_blocks_in_docx_text(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            markdown_path = temp / "paper.md"
            docx_path = temp / "paper.docx"
            markdown, expected_blocks = markdown_boundary_fixture()
            markdown_path.write_text(markdown, encoding="utf-8")
            write_minimal_docx(docx_path, expected_blocks)

            self.assertEqual(check_sync(markdown_path, docx_path), [])

    def test_sync_paper_docx_splits_inline_bold_segments(self) -> None:
        self.assertEqual(
            markdown_inline_segments("Plain **bold** tail"),
            [
                InlineSegment("Plain "),
                InlineSegment("bold", bold=True),
                InlineSegment(" tail"),
            ],
        )
        self.assertEqual(
            markdown_inline_segments("**A** and **B**"),
            [
                InlineSegment("A", bold=True),
                InlineSegment(" and "),
                InlineSegment("B", bold=True),
            ],
        )
        self.assertEqual(
            markdown_inline_segments("Unclosed **bold"),
            [InlineSegment("Unclosed **bold")],
        )

    def test_paper_markdown_normalizes_code_italic_and_link_text(self) -> None:
        text = "Use `code` and *emphasis* plus [visible link](https://example.test)."
        self.assertEqual(
            markdown_inline_segments(text),
            [
                InlineSegment("Use "),
                InlineSegment("code", code=True),
                InlineSegment(" and "),
                InlineSegment("emphasis", italic=True),
                InlineSegment(" plus visible link."),
            ],
        )
        self.assertEqual(
            normalize_markdown_inline(text),
            "Use code and emphasis plus visible link.",
        )

    @unittest.skipUnless(python_docx_available(), "python-docx is not available")
    def test_sync_paper_docx_renders_inline_bold_runs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            markdown_path = temp / "paper.md"
            docx_path = temp / "paper.docx"
            markdown_path.write_text(
                (
                    "# **Title** Plain\n\n"
                    "_Italic **subtitle**_\n\n"
                    "## Heading **Bold**\n\n"
                    "Regular **bold paragraph** tail.\n\n"
                    "Use `code span` and *italic span*.\n\n"
                    "- List **bold item** tail\n\n"
                    "| Header **One** | Header Two |\n"
                    "| --- | --- |\n"
                    "| Body **bold cell** tail | Plain |\n\n"
                    "**Keywords:** alpha **beta**\n"
                ),
                encoding="utf-8",
            )

            build_docx(markdown_path, docx_path)

            records = docx_run_styles(docx_path)
            self.assertIn(("Regular ", False, False, False), records)
            self.assertIn(("bold paragraph", True, False, False), records)
            self.assertIn(("code span", False, False, True), records)
            self.assertIn(("italic span", False, True, False), records)
            self.assertIn(("List ", False, False, False), records)
            self.assertIn(("bold item", True, False, False), records)
            self.assertIn(("Header ", True, False, False), records)
            self.assertIn(("One", True, False, False), records)
            self.assertIn(("Body ", False, False, False), records)
            self.assertIn(("bold cell", True, False, False), records)
            self.assertIn(("Keywords:", True, False, False), records)
            self.assertIn((" alpha ", False, False, False), records)
            self.assertIn(("beta", True, False, False), records)

    @unittest.skipUnless(python_docx_available(), "python-docx is not available")
    def test_paper_docx_pipeline_round_trips_rich_markdown_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            markdown_path = temp / "paper.md"
            docx_path = temp / "paper.docx"
            markdown, expected_blocks = markdown_boundary_fixture()
            markdown_path.write_text(markdown, encoding="utf-8")

            build_docx(markdown_path, docx_path)

            self.assertEqual(markdown_text_blocks(markdown_path), expected_blocks)
            self.assertEqual(check_sync(markdown_path, docx_path), [])

            records = docx_run_styles(docx_path)
            self.assertIn(("Title & Scope", True, False, False), records)
            self.assertIn(("Manuscript <draft> & check", False, True, False), records)
            self.assertIn(("Section <A> & B", True, False, False), records)
            self.assertIn(("Bullet", True, False, False), records)
            self.assertIn(("Col <1>", True, False, False), records)
            self.assertIn(("Cell A", True, False, False), records)
            self.assertIn(("code", False, False, True), records)
            self.assertIn(("emphasis", False, True, False), records)
            self.assertIn((", and visible link.", False, False, False), records)


if __name__ == "__main__":
    unittest.main()
