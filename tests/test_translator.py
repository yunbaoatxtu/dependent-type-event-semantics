import json
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
from translator.dependent_type_event_translator import (
    check_term,
    export_module,
    export_term,
    translate,
)
from translator.natural_language_pipeline import (
    ConstructionRule,
    construction_rules,
    run_registered_rule,
    run_pipeline,
    sentence_to_event_semantics,
)
from web.app import PipelineHandler, analyze_sentence, build_diagnostics, render_page


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "translator" / "examples"
WORD_NAMESPACE = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


def load_example(name: str) -> dict:
    return json.loads((EXAMPLES / name).read_text(encoding="utf-8"))


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


class TranslatorTests(unittest.TestCase):
    def test_variable_polyadicity_and_time(self) -> None:
        result = translate(load_example("example_butter.json"))
        self.assertEqual(result["adverb_count"], 2)
        self.assertEqual(
            result["translation"],
            "at_T(noon, butter(2)(slowly, in(bathroom), John, toast))",
        )
        self.assertEqual(result["ast"]["kind"], "time")
        self.assertEqual(result["ast"]["body"]["kind"], "application")
        self.assertEqual(result["ast"]["body"]["modifiers"], ["slowly", "in(bathroom)"])
        self.assertEqual(result["type_check"], {"ok": True, "type": "t", "errors": []})
        self.assertEqual(
            result["exports"]["lean"],
            "(at_T noon (butter 2 slowly in_bathroom John toast))",
        )
        self.assertEqual(
            result["exports"]["coq"],
            "(at_T noon (butter 2 slowly in_bathroom John toast))",
        )
        self.assertEqual(result["residual_atoms_not_translated"], [])
        coq_module = export_module([result], "coq")
        self.assertIn(
            "Definition Adv : Type := (Entity -> PropT) -> Entity -> PropT.",
            coq_module,
        )
        self.assertIn("Parameter slowly : Adv.", coq_module)
        self.assertIn("Parameter in_bathroom : Adv.", coq_module)
        self.assertIn(
            "Parameter butter : nat -> Adv -> Adv -> Entity -> Entity -> PropT.",
            coq_module,
        )

    def test_argument_omission_introduces_sigma_witness(self) -> None:
        result = translate(load_example("example_eat_omission.json"))
        self.assertEqual(
            result["translation"],
            "Sigma x_theme : Food. eat(0)(John, x_theme)",
        )
        self.assertEqual(
            result["omitted_arguments"],
            [{"role": "Theme", "witness": "x_theme", "type": "Food"}],
        )
        self.assertEqual(result["ast"]["kind"], "sigma")
        self.assertEqual(result["ast"]["body"]["kind"], "application")
        self.assertEqual(result["ast"]["body"]["arguments"], ["John", "x_theme"])
        self.assertTrue(result["type_check"]["ok"])
        self.assertEqual(
            result["exports"]["lean"],
            "(Exists fun x_theme : Food => (eat 0 John x_theme))",
        )
        self.assertEqual(
            result["exports"]["coq"],
            "(exists x_theme : Food, (eat 0 John x_theme))",
        )

    def test_event_counting_wraps_proposition(self) -> None:
        result = translate(load_example("example_knock_twice.json"))
        self.assertEqual(result["counts"], ["2"])
        self.assertEqual(result["translation"], "repeat(2, knock(0)(John))")
        self.assertEqual(result["ast"]["kind"], "repeat")
        self.assertEqual(result["ast"]["body"]["function"], "knock")
        self.assertTrue(result["type_check"]["ok"])
        self.assertEqual(result["exports"]["lean"], "(repeat 2 (knock 0 John))")

    def test_resultative_becomes_causal_transition(self) -> None:
        result = translate(load_example("example_break_result.json"))
        self.assertEqual(result["result_states"], ["broken"])
        self.assertEqual(
            result["translation"],
            "Cause(John, Transition(vase, _, broken))",
        )
        self.assertEqual(result["ast"]["kind"], "cause")
        self.assertEqual(result["ast"]["effect"]["kind"], "transition")
        self.assertEqual(result["ast"]["activity"]["function"], "break")
        self.assertTrue(result["type_check"]["ok"])
        self.assertEqual(
            result["exports"]["coq"],
            "(Cause John (Transition vase unknown_state broken))",
        )

    def test_type_checker_rejects_bad_adverb_count(self) -> None:
        result = check_term(
            {
                "kind": "application",
                "function": "butter",
                "adverb_count": 1,
                "modifiers": ["slowly", "carefully"],
                "arguments": ["John", "toast"],
            }
        )
        self.assertFalse(result["ok"])
        self.assertIn("does not match", result["errors"][0])

    def test_type_checker_rejects_bad_cause_effect(self) -> None:
        result = check_term(
            {
                "kind": "cause",
                "causer": "John",
                "effect": {
                    "kind": "application",
                    "function": "break",
                    "adverb_count": 0,
                    "modifiers": [],
                    "arguments": ["John", "vase"],
                },
            }
        )
        self.assertFalse(result["ok"])
        self.assertIn("cause.effect must have type Transition", result["errors"][0])

    def test_export_rejects_ill_typed_ast(self) -> None:
        bad = {
            "kind": "application",
            "function": "butter",
            "adverb_count": 3,
            "modifiers": ["slowly"],
            "arguments": ["John", "toast"],
        }
        with self.assertRaisesRegex(ValueError, "Cannot export ill-typed AST"):
            export_term(bad, "lean")

    def test_export_module_contains_declarations_and_examples(self) -> None:
        results = [
            translate(load_example("example_eat_omission.json")),
            translate(load_example("example_break_result.json")),
        ]
        lean_module = export_module(results, "lean")
        coq_module = export_module(results, "coq")
        self.assertIn("constant Entity : Type", lean_module)
        self.assertIn(
            "def example_1 : Prop := (Exists fun x_theme : Food => (eat 0 John x_theme))",
            lean_module,
        )
        self.assertIn(
            "def example_2 : PropT := (Cause John (Transition vase unknown_state broken))",
            lean_module,
        )
        self.assertIn("#check example_2", lean_module)
        self.assertIn("Parameter Entity : Type.", coq_module)
        self.assertIn(
            "Definition example_1 : Prop := (exists x_theme : Food, (eat 0 John x_theme)).",
            coq_module,
        )
        self.assertIn("Check example_2.", coq_module)

    def test_single_example_module_checks_only_defined_example(self) -> None:
        result = translate(load_example("example_eat_omission.json"))
        coq_module = export_module([result], "coq")
        self.assertIn("Definition example_1 : Prop :=", coq_module)
        self.assertIn("Check example_1.", coq_module)
        self.assertNotIn("Check example_2.", coq_module)

    def test_rule_based_sentence_to_event_semantics(self) -> None:
        formula = sentence_to_event_semantics("John knocked twice.")
        self.assertEqual(formula["exists"], ["e"])
        atoms = formula["body"]["and"]
        self.assertEqual(atoms[-1], {"pred": "twice", "args": ["e"]})

    def test_fallback_sentence_to_event_semantics(self) -> None:
        formula = sentence_to_event_semantics("a cat sits on a mat")
        atoms = formula["body"]["and"]
        self.assertIn({"pred": "sit", "args": ["e"]}, atoms)
        self.assertIn({"pred": "Agent", "args": ["e", "cat"]}, atoms)
        self.assertIn({"pred": "on", "args": ["e", "mat"]}, atoms)

    def test_natural_language_pipeline_success(self) -> None:
        result = run_pipeline("John ate")
        self.assertTrue(result["ok"])
        self.assertEqual(
            result["dependent_type_translation"],
            "Sigma x_theme : Food. eat(0)(John, x_theme)",
        )
        self.assertIn("Definition example_1", result["coq_code"])
        self.assertIn("Check example_1.", result["coq_code"])

    def test_natural_language_pipeline_handles_unlisted_sentence(self) -> None:
        result = run_pipeline("Mary admired the painting")
        self.assertTrue(result["ok"])
        self.assertEqual(
            result["dependent_type_translation"],
            "admire(0)(mary, painting)",
        )

    def test_natural_language_pipeline_handles_cat_on_mat(self) -> None:
        result = run_pipeline("a cat sits on a mat", require_coq=True)
        self.assertTrue(result["ok"])
        self.assertEqual(
            result["dependent_type_translation"],
            "sit(1)(on(mat), cat)",
        )
        self.assertIn("Parameter cat : Entity.", result["coq_code"])
        self.assertIn("Parameter on_mat : Adv.", result["coq_code"])
        self.assertIn("Parameter sit : nat -> Adv -> Entity -> PropT.", result["coq_code"])
        self.assertEqual(result["coq_check"]["status"], "passed")

    def test_luo_shi_modifier_types_for_classic_sentence(self) -> None:
        result = run_pipeline(
            "john buttered the toast in the bathroom with a knife",
            require_coq=True,
        )
        self.assertTrue(result["ok"])
        self.assertEqual(
            result["dependent_type_translation"],
            "butter(2)(in(bathroom), with(knife), john, toast)",
        )
        self.assertIn("Parameter in_bathroom : Adv.", result["coq_code"])
        self.assertIn("Parameter with_knife : Adv.", result["coq_code"])
        self.assertIn("Parameter john : Entity.", result["coq_code"])
        self.assertIn("Parameter toast : Entity.", result["coq_code"])
        self.assertIn(
            "Parameter butter : nat -> Adv -> Adv -> Entity -> Entity -> PropT.",
            result["coq_code"],
        )
        self.assertNotIn("Parameter in_bathroom : Entity.", result["coq_code"])
        self.assertNotIn("Parameter with_knife : Entity.", result["coq_code"])
        self.assertEqual(result["coq_check"]["status"], "passed")

    def test_parsons_after_singing_uses_time_not_event(self) -> None:
        result = run_pipeline(
            "after the singing of the Marseillaise, John saluted the flag",
            require_coq=True,
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["kind"], "timed_after")
        self.assertEqual(result["construction_rule"]["id"], "timed_after")
        self.assertEqual(result["type_check"]["type"], "Prop")
        self.assertIn("Parameter Time : Type.", result["coq_code"])
        self.assertIn("Parameter Marseillaise : Entity.", result["coq_code"])
        self.assertIn("Parameter John : Entity.", result["coq_code"])
        self.assertIn("Parameter flag : Entity.", result["coq_code"])
        self.assertIn("Parameter sing : Entity -> Time -> Prop.", result["coq_code"])
        self.assertIn(
            "Parameter salute : Entity -> Entity -> Time -> Prop.",
            result["coq_code"],
        )
        self.assertIn("Parameter before : Time -> Time -> Prop.", result["coq_code"])
        self.assertIn("Definition after_singing_salute : Prop :=", result["coq_code"])
        self.assertNotIn("Parameter Event : Type.", result["coq_code"])
        self.assertNotIn("exists e : Event", result["coq_code"])
        self.assertEqual(result["coq_check"]["status"], "passed")

    def test_parsons_perception_complement_uses_nominalizer_not_event(self) -> None:
        result = run_pipeline("Mary saw John leave", require_coq=True)
        self.assertTrue(result["ok"])
        self.assertEqual(result["kind"], "perception_nominalization")
        self.assertEqual(
            result["construction_rule"]["id"],
            "perception_nominalization",
        )
        self.assertIn("Parameter E : Prop -> Entity.", result["coq_code"])
        self.assertIn("Parameter leave : Entity -> Prop.", result["coq_code"])
        self.assertIn("Parameter see : Entity -> Entity -> Prop.", result["coq_code"])
        self.assertIn(
            "see Mary (E (leave John))",
            result["coq_code"],
        )
        self.assertNotIn("Parameter Event : Type.", result["coq_code"])
        self.assertNotIn("exists e : Event", result["coq_code"])
        self.assertEqual(result["coq_check"]["status"], "passed")

    def test_parsons_every_burning_uses_universal_time_not_inclusion(self) -> None:
        result = run_pipeline("In every burning, oxygen is consumed", require_coq=True)
        self.assertTrue(result["ok"])
        self.assertEqual(result["kind"], "universal_timed_burning")
        self.assertEqual(result["construction_rule"]["id"], "universal_timed_burning")
        self.assertIn("Parameter Time : Type.", result["coq_code"])
        self.assertIn("Parameter oxygen : Entity.", result["coq_code"])
        self.assertIn("Parameter burn : Entity -> Time -> Prop.", result["coq_code"])
        self.assertIn("Parameter consume : Entity -> Time -> Prop.", result["coq_code"])
        self.assertIn("forall x : Entity", result["coq_code"])
        self.assertIn("forall t : Time", result["coq_code"])
        self.assertIn("burn x t -> consume oxygen t", result["coq_code"])
        self.assertNotIn("Parameter Event : Type.", result["coq_code"])
        self.assertNotIn("IN", result["coq_code"])
        self.assertEqual(result["coq_check"]["status"], "passed")

    def test_quantifier_scope_ambiguity_some_boy_loves_some_girl(self) -> None:
        result = run_pipeline("some boy loves some girl", require_coq=True)
        self.assertTrue(result["ok"])
        self.assertEqual(result["kind"], "quantifier_scope_ambiguity")
        self.assertEqual(result["construction_rule"]["id"], "quantifier_scope_ambiguity")
        self.assertIn("some_boy_wide_scope", result["coq_code"])
        self.assertIn("some_girl_wide_scope", result["coq_code"])
        self.assertIn("Parameter boy : Entity -> Prop.", result["coq_code"])
        self.assertIn("Parameter girl : Entity -> Prop.", result["coq_code"])
        self.assertIn("Parameter love : Event -> Prop.", result["coq_code"])
        self.assertIn("Parameter Agent : Event -> Entity -> Prop.", result["coq_code"])
        self.assertNotIn("Parameter some : Entity.", result["coq_code"])
        self.assertNotIn("Parameter boy : nat ->", result["coq_code"])
        self.assertEqual(result["coq_check"]["status"], "passed")

    def test_registered_construction_rules_have_coq_hygiene_guards(self) -> None:
        rules = {rule.rule_id: rule for rule in construction_rules()}
        expected = {
            "timed_after",
            "perception_nominalization",
            "universal_timed_burning",
            "quantifier_scope_ambiguity",
        }
        self.assertTrue(expected.issubset(rules))
        self.assertIn("Parameter Event : Type.", rules["timed_after"].forbidden_coq_fragments)
        self.assertIn("Parameter Event : Type.", rules["perception_nominalization"].forbidden_coq_fragments)
        self.assertIn("IN", rules["universal_timed_burning"].forbidden_coq_fragments)
        self.assertIn("Parameter some : Entity.", rules["quantifier_scope_ambiguity"].forbidden_coq_fragments)

    def test_registered_rule_outputs_do_not_contain_forbidden_coq_fragments(self) -> None:
        examples = {
            "timed_after": "after the singing of the Marseillaise, John saluted the flag",
            "perception_nominalization": "Mary saw John leave",
            "universal_timed_burning": "In every burning, oxygen is consumed",
            "quantifier_scope_ambiguity": "some boy loves some girl",
        }
        for rule in construction_rules():
            with self.subTest(rule=rule.rule_id):
                result = run_pipeline(examples[rule.rule_id], require_coq=True)
                self.assertTrue(result["ok"])
                self.assertTrue(result["construction_hygiene"]["ok"])
                self.assertEqual(result["construction_hygiene"]["found_forbidden_fragments"], [])
                for fragment in rule.forbidden_coq_fragments:
                    self.assertNotIn(fragment, result["coq_code"])

    def test_web_analyze_sentence_success(self) -> None:
        result = analyze_sentence("John broke the vase")
        self.assertTrue(result["ok"])
        self.assertIn("Cause(John, Transition(vase, _, broken))", result["dependent_type_translation"])
        self.assertEqual(result["coq_check"]["status"], "passed")
        self.assertEqual(result["diagnostics"]["summary"], "translation verified")
        self.assertIsNone(result["diagnostics"]["failure_stage"])
        self.assertIsNone(result["diagnostics"]["recovery_hint"])
        self.assertEqual(result["diagnostics"]["recovery_actions"], [])
        self.assertEqual(result["diagnostics"]["stages"]["type_check"], "passed")
        self.assertEqual(result["diagnostics"]["stages"]["coq_check"], "passed")

    def test_web_analyze_sentence_empty_input(self) -> None:
        result = analyze_sentence("  ")
        self.assertFalse(result["ok"])
        self.assertIn("Please enter a sentence", result["error"])
        self.assertEqual(result["diagnostics"]["summary"], "translation failed")
        self.assertEqual(result["diagnostics"]["failure_stage"], "input")
        self.assertEqual(result["diagnostics"]["recovery_hint"], "Enter a non-empty sentence.")
        self.assertEqual(result["diagnostics"]["recovery_actions"][0]["kind"], "edit_input")
        self.assertEqual(result["diagnostics"]["recovery_actions"][0]["label"], "Enter a sentence")
        self.assertEqual(result["diagnostics"]["stages"]["type_check"], "not_applicable")

    def test_web_analyze_sentence_reports_parser_failure_stage(self) -> None:
        result = analyze_sentence("John")
        self.assertFalse(result["ok"])
        self.assertIn("at least a subject and a predicate", result["error"])
        self.assertEqual(result["diagnostics"]["summary"], "translation failed")
        self.assertEqual(result["diagnostics"]["failure_stage"], "parsing")
        self.assertEqual(
            result["diagnostics"]["recovery_hint"],
            "Try a sentence with at least a subject and a predicate.",
        )
        self.assertEqual(result["diagnostics"]["recovery_actions"][0]["kind"], "revise_sentence")
        self.assertEqual(
            result["diagnostics"]["recovery_actions"][0]["label"],
            "Add subject and predicate",
        )
        self.assertEqual(result["diagnostics"]["stages"]["type_check"], "not_applicable")

    def test_api_analyze_response_contains_diagnostics(self) -> None:
        handler = object.__new__(PipelineHandler)
        result = PipelineHandler.handle_api(
            handler,
            "sentence=Mary+saw+John+leave&require_coq=1",
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["construction_rule"]["id"], "perception_nominalization")
        self.assertEqual(result["diagnostics"]["summary"], "translation verified")
        self.assertIsNone(result["diagnostics"]["failure_stage"])
        self.assertIsNone(result["diagnostics"]["recovery_hint"])
        self.assertEqual(result["diagnostics"]["recovery_actions"], [])
        self.assertEqual(result["diagnostics"]["stages"]["type_check"], "passed")
        self.assertEqual(result["diagnostics"]["stages"]["construction_hygiene"], "passed")
        self.assertEqual(result["diagnostics"]["stages"]["coq_check"], "passed")

    def test_api_analyze_response_reports_empty_input(self) -> None:
        handler = object.__new__(PipelineHandler)
        result = PipelineHandler.handle_api(handler, "sentence=%20%20&require_coq=1")
        self.assertFalse(result["ok"])
        self.assertIn("Please enter a sentence", result["error"])
        self.assertEqual(result["diagnostics"]["summary"], "translation failed")
        self.assertEqual(result["diagnostics"]["failure_stage"], "input")
        self.assertEqual(result["diagnostics"]["recovery_hint"], "Enter a non-empty sentence.")
        self.assertEqual(result["diagnostics"]["recovery_actions"][0]["kind"], "edit_input")

    def test_web_page_contains_pipeline_panels(self) -> None:
        page = render_page("John knocked twice")
        self.assertIn("Event Semantics", page)
        self.assertIn("Dependent-Type Translation", page)
        self.assertIn("Diagnostics", page)
        self.assertIn("Next Steps", page)
        self.assertIn("No recovery actions needed.", page)
        self.assertIn("Construction Rule", page)
        self.assertIn("Generated Coq", page)
        self.assertIn("repeat(2, knock(0)(John))", page)

    def test_web_page_shows_registered_construction_rule_metadata(self) -> None:
        page = render_page("Mary saw John leave", require_coq=True)
        self.assertIn("Construction Rule", page)
        self.assertIn("id: perception_nominalization", page)
        self.assertIn("phenomenon: Parsons/Luo-Shi perception complement", page)
        self.assertIn("hygiene: passed", page)
        self.assertIn("hygiene policy:", page)
        self.assertNotIn("forbidden Coq fragments:", page)
        self.assertIn("- Parameter Event : Type.", page)
        self.assertIn("found forbidden fragments:", page)
        self.assertIn("- none", page)

    def test_web_page_marks_fallback_when_no_registered_rule_matched(self) -> None:
        page = render_page("a cat sits on a mat", require_coq=True)
        self.assertIn("Construction Rule", page)
        self.assertIn("No registered construction rule matched", page)

    def test_web_page_status_shows_parser_failure_stage(self) -> None:
        page = render_page("John")
        self.assertIn("Needs attention", page)
        self.assertIn("Failure stage: natural-language parsing.", page)
        self.assertIn("Suggested next step: Try a sentence with at least a subject and a predicate.", page)
        self.assertIn("Next Steps", page)
        self.assertIn('class="next-step next-step--revise_sentence"', page)
        self.assertIn('data-action-kind="revise_sentence"', page)
        self.assertIn("<strong>Add subject and predicate</strong>", page)
        self.assertIn("<code>revise_sentence</code>", page)
        self.assertIn("Use a sentence with at least a recognizable subject and predicate.", page)

    def test_web_page_status_shows_empty_input_failure_stage(self) -> None:
        page = render_page("  ")
        self.assertIn("Needs attention", page)
        self.assertIn("Failure stage: empty input.", page)
        self.assertIn("Suggested next step: Enter a non-empty sentence.", page)
        self.assertIn("Next Steps", page)
        self.assertIn('class="next-step next-step--edit_input"', page)
        self.assertIn('data-action-kind="edit_input"', page)
        self.assertIn("<strong>Enter a sentence</strong>", page)
        self.assertIn("<code>edit_input</code>", page)
        self.assertIn("Type a non-empty natural-language sentence before analyzing.", page)

    def test_web_diagnostics_reports_construction_hygiene_failure(self) -> None:
        diagnostics = build_diagnostics(
            {
                "ok": False,
                "type_check": {"ok": True},
                "construction_hygiene": {"ok": False},
                "coq_check": {"ok": False},
            }
        )
        self.assertEqual(diagnostics["summary"], "construction hygiene failed")
        self.assertEqual(diagnostics["failure_stage"], "construction_hygiene")
        self.assertEqual(
            diagnostics["recovery_hint"],
            "Remove forbidden construction fragments from generated Coq.",
        )
        self.assertEqual(diagnostics["recovery_actions"][0]["kind"], "inspect_coq")
        self.assertEqual(diagnostics["recovery_actions"][0]["label"], "Remove forbidden fragments")
        self.assertEqual(diagnostics["stages"]["type_check"], "passed")
        self.assertEqual(diagnostics["stages"]["construction_hygiene"], "failed")
        self.assertEqual(diagnostics["stages"]["coq_check"], "failed")

    def test_web_diagnostics_reports_type_check_failure_stage(self) -> None:
        diagnostics = build_diagnostics(
            {
                "ok": False,
                "input_sentence": "bad typed sentence",
                "type_check": {"ok": False},
                "coq_check": {"ok": None},
            }
        )
        self.assertEqual(diagnostics["summary"], "type check failed")
        self.assertEqual(diagnostics["failure_stage"], "type_check")
        self.assertEqual(
            diagnostics["recovery_hint"],
            "Inspect the dependent-type AST and type-check errors.",
        )
        self.assertEqual(diagnostics["recovery_actions"][0]["kind"], "inspect_ast")
        self.assertEqual(diagnostics["recovery_actions"][0]["label"], "Inspect typed AST")
        self.assertEqual(diagnostics["stages"]["type_check"], "failed")
        self.assertEqual(diagnostics["stages"]["coq_check"], "skipped")

    def test_pipeline_reports_construction_hygiene_separately(self) -> None:
        result = run_pipeline("In every burning, oxygen is consumed", require_coq=True)
        self.assertTrue(result["ok"])
        self.assertEqual(result["construction_rule"]["id"], "universal_timed_burning")
        self.assertEqual(
            result["construction_hygiene"],
            {
                "ok": True,
                "checked": True,
                "forbidden_coq_fragments": ["Parameter Event : Type.", "IN"],
                "found_forbidden_fragments": [],
            },
        )

    def test_registered_rule_fails_before_coq_when_forbidden_fragment_is_generated(self) -> None:
        def bad_analyzer(sentence: str) -> dict:
            return {
                "kind": "bad_rule",
                "input_sentence": sentence,
                "event_semantics": {},
                "dependent_type_translation": "bad",
                "ast": {},
                "type_check": {"ok": True, "type": "Prop", "errors": []},
                "coq_code": "Parameter Event : Type.\nDefinition bad : Prop := True.\n",
            }

        rule = ConstructionRule(
            rule_id="bad_event_reintroduction",
            label="Bad event reintroduction",
            phenomenon="negative hygiene test",
            analyzer=bad_analyzer,
            forbidden_coq_fragments=("Parameter Event : Type.",),
        )
        result = run_registered_rule(rule, "bad sentence", require_coq=True)
        self.assertIsNotNone(result)
        assert result is not None
        self.assertFalse(result["ok"])
        self.assertFalse(result["construction_hygiene"]["ok"])
        self.assertEqual(
            result["construction_hygiene"]["found_forbidden_fragments"],
            ["Parameter Event : Type."],
        )
        self.assertEqual(result["coq_check"]["status"], "failed")
        self.assertIn("forbidden construction fragments", result["coq_check"]["message"])

    def test_docs_explain_construction_hygiene_policy_vs_actual_findings(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        web_design = (ROOT / "docs" / "web_pipeline_design.md").read_text(encoding="utf-8")
        self.assertIn("`forbidden_coq_fragments` is the policy list", readme)
        self.assertIn("`found_forbidden_fragments`", readme)
        self.assertIn('"found_forbidden_fragments": []', readme)
        self.assertIn("must distinguish a rule's policy from an actual", web_design)
        self.assertIn("found forbidden fragments: none", web_design)

    def test_docs_explain_web_diagnostics_summary(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        web_design = (ROOT / "docs" / "web_pipeline_design.md").read_text(encoding="utf-8")
        self.assertIn('"summary": "translation verified"', readme)
        self.assertIn('"failure_stage": null', readme)
        self.assertIn('"recovery_hint": null', readme)
        self.assertIn('"recovery_actions": []', readme)
        self.assertIn('"type_check": "passed"', readme)
        self.assertIn('"construction_hygiene": "passed"', readme)
        self.assertIn('"coq_check": "passed"', readme)
        self.assertIn("`diagnostics.failure_stage` distinguishes", readme)
        self.assertIn("`diagnostics.recovery_hint` gives a short next-step suggestion", readme)
        self.assertIn("`diagnostics.recovery_actions` exposes the same advice", readme)
        self.assertIn("separate `Next Steps`", readme)
        self.assertIn("stable `data-action-kind`", readme)
        self.assertIn("`next-step--<kind>` CSS class", readme)
        self.assertIn("python3 scripts/sync_paper_docx.py", readme)
        self.assertIn("python3 scripts/check_paper_docx_sync.py", readme)
        self.assertIn("the compact diagnostics summary", web_design)
        self.assertIn("construction-specific hygiene", web_design)
        self.assertIn("`diagnostics.failure_stage` is the machine-readable failure locator", web_design)
        self.assertIn("`diagnostics.recovery_hint` is `null` on success", web_design)
        self.assertIn("`diagnostics.recovery_actions` is an array", web_design)
        self.assertIn("`kind`, `label`, and `detail` fields", web_design)
        self.assertIn("render the same actions in a `Next Steps` panel", web_design)
        self.assertIn("`data-action-kind`", web_design)
        self.assertIn("`next-step--<kind>`", web_design)
        self.assertIn("one of `input`, `parsing`,", web_design)

    def test_docs_explain_api_contract(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        web_design = (ROOT / "docs" / "web_pipeline_design.md").read_text(encoding="utf-8")
        self.assertIn("/api/analyze?sentence=Mary+saw+John+leave&require_coq=1", readme)
        self.assertIn("`sentence` parameter carries the natural-language input", readme)
        self.assertIn("`construction_rule`", readme)
        self.assertIn("## API Contract", web_design)
        self.assertIn("`sentence`: required natural-language input", web_design)
        self.assertIn("`require_coq`: optional flag", web_design)
        self.assertIn("`dependent_type_translation`", web_design)
        self.assertIn("`construction_hygiene`", web_design)
        self.assertIn("failure, it must still return `ok: false`", web_design)
        self.assertIn("The separate `failure_stage` field distinguishes", web_design)
        self.assertIn("The web status line should surface `recovery_hint` directly", web_design)
        self.assertIn("Machine clients should prefer `recovery_actions`", web_design)

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
