import json
import unittest
from pathlib import Path

from translator.dependent_type_event_translator import (
    SOURCE_STATE_BY_TARGET_STATE,
    STATE_LEXICON,
    STATE_SCALE_BY_STATE,
    check_term,
    export_module,
    export_term,
    modifier_vector,
    role_frame,
    state_lexicon_metadata,
    translate,
)
from translator.natural_language_pipeline import (
    ConstructionRule,
    check_perception_nominalization_ast,
    check_quantifier_scope_readings,
    check_timed_after_ast,
    check_universal_timed_ast,
    construction_rules,
    run_registered_rule,
    run_pipeline,
    sentence_to_event_semantics,
    verify_coq_code,
)
from web.app import PipelineHandler, analyze_sentence, build_diagnostics, render_page


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "translator" / "examples"


def load_example(name: str) -> dict:
    return json.loads((EXAMPLES / name).read_text(encoding="utf-8"))


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
        self.assertEqual(
            result["ast"]["body"]["role_frame"],
            {
                "kind": "role_frame",
                "roles": [
                    {"role": "Agent", "value": "John", "type": "Entity", "source": "explicit"},
                    {"role": "Theme", "value": "toast", "type": "Entity", "source": "explicit"},
                ],
            },
        )
        self.assertEqual(
            result["ast"]["body"]["modifier_vector"],
            {
                "kind": "modifier_vector",
                "length": 2,
                "items": [
                    {"modifier": "slowly", "tail_length": 1},
                    {"modifier": "in(bathroom)", "tail_length": 0},
                ],
            },
        )
        self.assertEqual(result["type_check"], {"ok": True, "type": "t", "errors": []})
        self.assertEqual(
            result["exports"]["lean"],
            "(at_T noon (butter 2 (mods_cons 1 slowly (mods_cons 0 in_bathroom mods_nil)) John toast))",
        )
        self.assertEqual(
            result["exports"]["coq"],
            "(at_T noon (butter 2 (mods_cons 1 slowly (mods_cons 0 in_bathroom mods_nil)) John toast))",
        )
        self.assertEqual(result["residual_atoms_not_translated"], [])
        coq_module = export_module([result], "coq")
        self.assertIn("Definition PropT : Type := Prop.", coq_module)
        self.assertIn(
            "Definition Adv : Type := (Entity -> PropT) -> Entity -> PropT.",
            coq_module,
        )
        self.assertIn("Parameter ModifierSeq : nat -> Type.", coq_module)
        self.assertIn("Parameter mods_nil : ModifierSeq 0.", coq_module)
        self.assertIn(
            "Parameter mods_cons : forall n : nat, Adv -> ModifierSeq n -> ModifierSeq (S n).",
            coq_module,
        )
        self.assertIn("Parameter slowly : Adv.", coq_module)
        self.assertIn("Parameter in_bathroom : Adv.", coq_module)
        self.assertIn(
            "Parameter butter : forall n : nat, ModifierSeq n -> Entity -> Entity -> PropT.",
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
        self.assertEqual(
            result["ast"]["body"]["role_frame"],
            {
                "kind": "role_frame",
                "roles": [
                    {"role": "Agent", "value": "John", "type": "Entity", "source": "explicit"},
                    {"role": "Theme", "value": "x_theme", "type": "Food", "source": "omitted"},
                ],
            },
        )
        self.assertTrue(result["type_check"]["ok"])
        self.assertEqual(
            result["exports"]["lean"],
            "(Exists fun x_theme : Food => (eat 0 mods_nil John x_theme))",
        )
        self.assertEqual(
            result["exports"]["coq"],
            "(exists x_theme : Food, (eat 0 mods_nil John x_theme))",
        )

    def test_event_counting_wraps_proposition(self) -> None:
        result = translate(load_example("example_knock_twice.json"))
        self.assertEqual(result["counts"], ["2"])
        self.assertEqual(result["translation"], "repeat(2, knock(0)(John))")
        self.assertEqual(result["ast"]["kind"], "repeat")
        self.assertEqual(result["ast"]["body"]["function"], "knock")
        self.assertTrue(result["type_check"]["ok"])
        self.assertEqual(result["exports"]["lean"], "(repeat 2 (knock 0 mods_nil John))")

    def test_resultative_becomes_causal_transition(self) -> None:
        result = translate(load_example("example_break_result.json"))
        self.assertEqual(result["result_states"], ["broken"])
        self.assertEqual(
            result["result_state_lexicon"],
            [
                {
                    "state": "broken",
                    "scale": "integrity_scale",
                    "default_source_state": "intact",
                    "source_policy": "lexical_prestate",
                }
            ],
        )
        self.assertEqual(
            result["translation"],
            "Cause(John, Transition(vase, integrity_scale, intact, broken))",
        )
        self.assertEqual(result["ast"]["kind"], "cause")
        self.assertEqual(result["ast"]["effect"]["kind"], "transition")
        self.assertEqual(result["ast"]["effect"]["state_scale"], "integrity_scale")
        self.assertEqual(result["ast"]["effect"]["source_state"], "intact")
        self.assertEqual(result["ast"]["activity"]["function"], "break")
        self.assertEqual(
            result["ast"]["activity"]["role_frame"]["roles"],
            [
                {"role": "Agent", "value": "John", "type": "Entity", "source": "explicit"},
                {"role": "Theme", "value": "vase", "type": "Entity", "source": "explicit"},
            ],
        )
        self.assertTrue(result["type_check"]["ok"])
        self.assertEqual(
            result["exports"]["coq"],
            "(Cause John (Transition vase integrity_scale intact broken))",
        )
        coq_module = export_module([result], "coq")
        self.assertIn("Parameter State : Type.", coq_module)
        self.assertIn("Parameter StateScale : Type.", coq_module)
        self.assertIn("Parameter vase : Entity.", coq_module)
        self.assertIn("Parameter integrity_scale : StateScale.", coq_module)
        self.assertIn("Parameter broken : State.", coq_module)
        self.assertIn("Parameter intact : State.", coq_module)
        self.assertIn(
            "Parameter Transition : Entity -> StateScale -> State -> State -> TransitionT.",
            coq_module,
        )
        self.assertNotIn(
            "Parameter Transition : Entity -> State -> State -> TransitionT.",
            coq_module,
        )

    def test_state_lexicon_is_structured_and_consistent(self) -> None:
        self.assertEqual(STATE_LEXICON["broken"].scale, "integrity_scale")
        self.assertEqual(STATE_LEXICON["broken"].default_source_state, "intact")
        self.assertEqual(STATE_SCALE_BY_STATE["flat"], "shape_scale")
        self.assertEqual(SOURCE_STATE_BY_TARGET_STATE["flat"], "not_flat")
        self.assertNotIn("red", SOURCE_STATE_BY_TARGET_STATE)
        self.assertEqual(
            state_lexicon_metadata("red"),
            {
                "state": "red",
                "scale": "color_scale",
                "default_source_state": None,
                "source_policy": "unknown_source_allowed",
            },
        )

        for target_state, source_state in SOURCE_STATE_BY_TARGET_STATE.items():
            with self.subTest(target_state=target_state):
                self.assertIn(source_state, STATE_LEXICON)
                self.assertEqual(
                    STATE_LEXICON[source_state].scale,
                    STATE_LEXICON[target_state].scale,
                )

    def test_fallback_resultative_phrase_uses_state_scale_lexicon(self) -> None:
        formula = sentence_to_event_semantics("John hammered the metal flat")
        self.assertIn({"pred": "Theme", "args": ["e", "metal"]}, formula["body"]["and"])
        self.assertIn({"pred": "Result", "args": ["e", "flat"]}, formula["body"]["and"])

        result = run_pipeline("John hammered the metal flat", require_coq=True)
        self.assertTrue(result["ok"])
        self.assertEqual(
            result["dependent_type_translation"],
            "Cause(john, Transition(metal, shape_scale, not_flat, flat))",
        )
        self.assertEqual(
            result["result_state_lexicon"],
            [
                {
                    "state": "flat",
                    "scale": "shape_scale",
                    "default_source_state": "not_flat",
                    "source_policy": "lexical_prestate",
                }
            ],
        )
        self.assertEqual(result["ast"]["effect"]["state_scale"], "shape_scale")
        self.assertEqual(result["ast"]["effect"]["source_state"], "not_flat")
        self.assertIn("Parameter metal : Entity.", result["coq_code"])
        self.assertIn("Parameter shape_scale : StateScale.", result["coq_code"])
        self.assertIn("Parameter not_flat : State.", result["coq_code"])
        self.assertIn("Parameter flat : State.", result["coq_code"])
        self.assertIn(
            "Definition example_1 : PropT := (Cause john (Transition metal shape_scale not_flat flat)).",
            result["coq_code"],
        )
        self.assertEqual(result["coq_check"]["status"], "passed")

        painted = run_pipeline("Mary painted the door red", require_coq=True)
        self.assertTrue(painted["ok"])
        self.assertEqual(
            painted["dependent_type_translation"],
            "Cause(mary, Transition(door, color_scale, _, red))",
        )
        self.assertEqual(
            painted["result_state_lexicon"],
            [
                {
                    "state": "red",
                    "scale": "color_scale",
                    "default_source_state": None,
                    "source_policy": "unknown_source_allowed",
                }
            ],
        )
        self.assertEqual(painted["ast"]["effect"]["source_state"], "_")
        self.assertIn("Parameter color_scale : StateScale.", painted["coq_code"])
        self.assertIn("Parameter red : State.", painted["coq_code"])
        self.assertIn(
            "Definition example_1 : PropT := (Cause mary (Transition door color_scale unknown_state red)).",
            painted["coq_code"],
        )
        self.assertEqual(painted["coq_check"]["status"], "passed")

    def test_type_checker_rejects_bad_adverb_count(self) -> None:
        result = check_term(
            {
                "kind": "application",
                "function": "butter",
                "adverb_count": 1,
                "modifiers": ["slowly", "carefully"],
                "modifier_vector": modifier_vector(["slowly", "carefully"]),
                "arguments": ["John", "toast"],
                "role_frame": role_frame(
                    [
                        {"role": "Agent", "value": "John", "type": "Entity", "source": "explicit"},
                        {"role": "Theme", "value": "toast", "type": "Entity", "source": "explicit"},
                    ]
                ),
            }
        )
        self.assertFalse(result["ok"])
        self.assertIn("does not match", result["errors"][0])

    def test_type_checker_rejects_bad_modifier_vector_tail_length(self) -> None:
        result = check_term(
            {
                "kind": "application",
                "function": "butter",
                "adverb_count": 2,
                "modifiers": ["slowly", "carefully"],
                "modifier_vector": {
                    "kind": "modifier_vector",
                    "length": 2,
                    "items": [
                        {"modifier": "slowly", "tail_length": 0},
                        {"modifier": "carefully", "tail_length": 0},
                    ],
                },
                "arguments": ["John", "toast"],
                "role_frame": role_frame(
                    [
                        {"role": "Agent", "value": "John", "type": "Entity", "source": "explicit"},
                        {"role": "Theme", "value": "toast", "type": "Entity", "source": "explicit"},
                    ]
                ),
            }
        )
        self.assertFalse(result["ok"])
        self.assertIn("tail_length=0 does not match expected tail length 1", result["errors"][0])

    def test_type_checker_rejects_role_frame_argument_mismatch(self) -> None:
        result = check_term(
            {
                "kind": "application",
                "function": "butter",
                "adverb_count": 0,
                "modifiers": [],
                "modifier_vector": modifier_vector([]),
                "arguments": ["John", "toast"],
                "role_frame": role_frame(
                    [
                        {"role": "Agent", "value": "toast", "type": "Entity", "source": "explicit"},
                        {"role": "Theme", "value": "John", "type": "Entity", "source": "explicit"},
                    ]
                ),
            }
        )
        self.assertFalse(result["ok"])
        self.assertIn(
            "ast: application.role_frame values do not match application.arguments",
            result["errors"],
        )

    def test_type_checker_rejects_role_frame_label_order_mismatch(self) -> None:
        result = check_term(
            {
                "kind": "application",
                "function": "butter",
                "adverb_count": 0,
                "modifiers": [],
                "modifier_vector": modifier_vector([]),
                "arguments": ["John", "toast"],
                "role_frame": role_frame(
                    [
                        {"role": "Theme", "value": "John", "type": "Entity", "source": "explicit"},
                        {"role": "Agent", "value": "toast", "type": "Entity", "source": "explicit"},
                    ]
                ),
            }
        )
        self.assertFalse(result["ok"])
        self.assertIn(
            "ast: application.role_frame roles must follow canonical thematic order",
            result["errors"],
        )

    def test_type_checker_rejects_role_frame_type_mismatch(self) -> None:
        result = check_term(
            {
                "kind": "application",
                "function": "read",
                "adverb_count": 0,
                "modifiers": [],
                "modifier_vector": modifier_vector([]),
                "arguments": ["John", "book"],
                "role_frame": role_frame(
                    [
                        {"role": "Agent", "value": "John", "type": "Entity", "source": "explicit"},
                        {"role": "Theme", "value": "book", "type": "Entity", "source": "explicit"},
                    ]
                ),
            }
        )
        self.assertFalse(result["ok"])
        self.assertIn(
            "ast: application.role_frame role types do not match function argument types",
            result["errors"],
        )

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
                    "modifier_vector": modifier_vector([]),
                    "arguments": ["John", "vase"],
                    "role_frame": role_frame(
                        [
                            {"role": "Agent", "value": "John", "type": "Entity", "source": "explicit"},
                            {"role": "Theme", "value": "vase", "type": "Entity", "source": "explicit"},
                        ]
                    ),
                },
            }
        )
        self.assertFalse(result["ok"])
        self.assertIn("cause.effect must have type TransitionT", result["errors"][0])

    def test_type_checker_rejects_trivial_known_transition(self) -> None:
        result = check_term(
            {
                "kind": "transition",
                "theme": "vase",
                "state_scale": "integrity_scale",
                "source_state": "broken",
                "target_state": "broken",
            }
        )
        self.assertFalse(result["ok"])
        self.assertIn(
            "ast: transition.source_state and target_state must differ when both are known",
            result["errors"],
        )

    def test_type_checker_allows_unknown_transition_source(self) -> None:
        result = check_term(
            {
                "kind": "transition",
                "theme": "vase",
                "state_scale": "integrity_scale",
                "source_state": "_",
                "target_state": "broken",
            }
        )
        self.assertEqual(result, {"ok": True, "type": "TransitionT", "errors": []})

    def test_type_checker_rejects_unknown_transition_target(self) -> None:
        result = check_term(
            {
                "kind": "transition",
                "theme": "vase",
                "state_scale": "integrity_scale",
                "source_state": "intact",
                "target_state": "_",
            }
        )
        self.assertFalse(result["ok"])
        self.assertIn(
            "ast: transition.target_state must be known",
            result["errors"],
        )

    def test_type_checker_rejects_transition_scale_mismatch(self) -> None:
        result = check_term(
            {
                "kind": "transition",
                "theme": "vase",
                "state_scale": "shape_scale",
                "source_state": "intact",
                "target_state": "broken",
            }
        )
        self.assertFalse(result["ok"])
        self.assertIn(
            "ast: transition.state_scale='shape_scale' does not match target state scale 'integrity_scale'",
            result["errors"],
        )
        self.assertIn(
            "ast: transition.source_state scale 'integrity_scale' does not match transition.state_scale 'shape_scale'",
            result["errors"],
        )

    def test_export_rejects_ill_typed_ast(self) -> None:
        bad = {
            "kind": "application",
            "function": "butter",
            "adverb_count": 3,
            "modifiers": ["slowly"],
            "modifier_vector": modifier_vector(["slowly"]),
            "arguments": ["John", "toast"],
            "role_frame": role_frame(
                [
                    {"role": "Agent", "value": "John", "type": "Entity", "source": "explicit"},
                    {"role": "Theme", "value": "toast", "type": "Entity", "source": "explicit"},
                ]
            ),
        }
        with self.assertRaisesRegex(ValueError, "Cannot export ill-typed AST"):
            export_term(bad, "lean")

    def test_export_rejects_conflicting_constant_types(self) -> None:
        read_book = translate(sentence_to_event_semantics("Mary read the book"))
        book_sits = translate(sentence_to_event_semantics("book sits"))
        with self.assertRaisesRegex(
            ValueError,
            "Conflicting export types for constant book: Readable vs Entity",
        ):
            export_module([read_book, book_sits], "coq")

    def test_export_rejects_entity_state_constant_conflicts(self) -> None:
        break_result = translate(sentence_to_event_semantics("John broke the vase"))
        broken_sits = translate(sentence_to_event_semantics("broken sits"))
        with self.assertRaisesRegex(
            ValueError,
            "Conflicting export types for constant broken: State vs Entity",
        ):
            export_module([break_result, broken_sits], "coq")

    def test_export_allows_mixed_modifier_counts_with_modifier_sequence(self) -> None:
        two_modifier_butter = translate(
            sentence_to_event_semantics("john buttered the toast in the bathroom with a knife")
        )
        three_modifier_butter = translate(
            sentence_to_event_semantics(
                "john buttered the toast slowly in the bathroom with a knife"
            )
        )
        coq_module = export_module([two_modifier_butter, three_modifier_butter], "coq")
        self.assertIn(
            "Parameter butter : forall n : nat, ModifierSeq n -> Entity -> Entity -> PropT.",
            coq_module,
        )
        self.assertIn(
            "Definition example_1 : PropT := (butter 2 (mods_cons 1 in_bathroom (mods_cons 0 with_knife mods_nil)) john toast).",
            coq_module,
        )
        self.assertIn(
            "Definition example_2 : PropT := (butter 3 (mods_cons 2 slowly (mods_cons 1 in_bathroom (mods_cons 0 with_knife mods_nil))) john toast).",
            coq_module,
        )
        coq_check = verify_coq_code(coq_module, require_coq=True)
        self.assertEqual(coq_check["status"], "passed", coq_check["message"])

    def test_indexed_modifier_sequence_rejects_wrong_length_in_coq(self) -> None:
        result = translate(load_example("example_butter.json"))
        coq_module = export_module([result], "coq")
        broken_module = coq_module.replace(
            "butter 2 (mods_cons 1 slowly",
            "butter 2 (mods_cons 0 slowly",
        )
        coq_check = verify_coq_code(broken_module, require_coq=True)
        self.assertEqual(coq_check["status"], "failed")
        self.assertIn("ModifierSeq", coq_check["message"])

    def test_export_module_contains_declarations_and_examples(self) -> None:
        results = [
            translate(load_example("example_eat_omission.json")),
            translate(load_example("example_break_result.json")),
        ]
        lean_module = export_module(results, "lean")
        coq_module = export_module(results, "coq")
        self.assertIn("constant Entity : Type", lean_module)
        self.assertIn(
            "def example_1 : Prop := (Exists fun x_theme : Food => (eat 0 mods_nil John x_theme))",
            lean_module,
        )
        self.assertIn(
            "def example_2 : PropT := (Cause John (Transition vase integrity_scale intact broken))",
            lean_module,
        )
        self.assertIn("#check example_2", lean_module)
        self.assertIn("Parameter Entity : Type.", coq_module)
        self.assertIn(
            "Definition example_1 : Prop := (exists x_theme : Food, (eat 0 mods_nil John x_theme)).",
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

    def test_omission_exports_lexical_witness_types(self) -> None:
        read_result = run_pipeline("John read", require_coq=True)
        self.assertTrue(read_result["ok"])
        self.assertEqual(
            read_result["dependent_type_translation"],
            "Sigma x_theme : Readable. read(0)(john, x_theme)",
        )
        self.assertIn("Parameter Readable : Type.", read_result["coq_code"])
        self.assertIn(
            "Parameter read : forall n : nat, ModifierSeq n -> Entity -> Readable -> Prop.",
            read_result["coq_code"],
        )
        self.assertIn("exists x_theme : Readable", read_result["coq_code"])
        self.assertNotIn("Parameter x_theme", read_result["coq_code"])
        self.assertEqual(read_result["coq_check"]["status"], "passed")

        drink_result = run_pipeline("John drank", require_coq=True)
        self.assertTrue(drink_result["ok"])
        self.assertEqual(
            drink_result["dependent_type_translation"],
            "Sigma x_theme : Drinkable. drink(0)(john, x_theme)",
        )
        self.assertIn("Parameter Drinkable : Type.", drink_result["coq_code"])
        self.assertIn(
            "Parameter drink : forall n : nat, ModifierSeq n -> Entity -> Drinkable -> Prop.",
            drink_result["coq_code"],
        )
        self.assertIn("exists x_theme : Drinkable", drink_result["coq_code"])
        self.assertEqual(drink_result["coq_check"]["status"], "passed")

    def test_explicit_lexical_theme_uses_matching_result_annotation(self) -> None:
        read_result = run_pipeline("Mary read the book", require_coq=True)
        self.assertTrue(read_result["ok"])
        self.assertEqual(read_result["dependent_type_translation"], "read(0)(mary, book)")
        self.assertEqual(
            read_result["ast"]["role_frame"]["roles"],
            [
                {"role": "Agent", "value": "mary", "type": "Entity", "source": "explicit"},
                {"role": "Theme", "value": "book", "type": "Readable", "source": "explicit"},
            ],
        )
        self.assertIn("Parameter book : Readable.", read_result["coq_code"])
        self.assertIn(
            "Parameter read : forall n : nat, ModifierSeq n -> Entity -> Readable -> Prop.",
            read_result["coq_code"],
        )
        self.assertIn(
            "Definition example_1 : Prop := (read 0 mods_nil mary book).",
            read_result["coq_code"],
        )
        self.assertEqual(read_result["coq_check"]["status"], "passed")

        drink_result = run_pipeline("John drank water", require_coq=True)
        self.assertTrue(drink_result["ok"])
        self.assertEqual(
            drink_result["ast"]["role_frame"]["roles"][1],
            {"role": "Theme", "value": "water", "type": "Drinkable", "source": "explicit"},
        )
        self.assertIn("Parameter water : Drinkable.", drink_result["coq_code"])
        self.assertIn(
            "Definition example_1 : Prop := (drink 0 mods_nil john water).",
            drink_result["coq_code"],
        )
        self.assertEqual(drink_result["coq_check"]["status"], "passed")

    def test_dependent_signature_records_refined_argument_types(self) -> None:
        read_translation = translate(sentence_to_event_semantics("Mary read the book"))
        self.assertEqual(
            read_translation["lexical_signature"],
            "read : Pi n : N. TV-ADV(n); TV-ADV(n) = ADV^n -> e -> Readable -> t",
        )
        self.assertEqual(
            read_translation["dependent_type_principle"]["TV-ADV"],
            "TV-ADV(n) = ADV^n -> e -> Readable -> t",
        )

        eat_translation = translate(sentence_to_event_semantics("John ate"))
        self.assertEqual(
            eat_translation["lexical_signature"],
            "eat : Pi n : N. TV-ADV(n); TV-ADV(n) = ADV^n -> e -> Food -> t",
        )
        self.assertEqual(
            eat_translation["dependent_type_principle"]["TV-ADV"],
            "TV-ADV(n) = ADV^n -> e -> Food -> t",
        )

    def test_time_can_scope_over_lexical_prop_outputs(self) -> None:
        omitted_result = run_pipeline("John read at noon", require_coq=True)
        self.assertTrue(omitted_result["ok"])
        self.assertEqual(
            omitted_result["dependent_type_translation"],
            "at_T(noon, Sigma x_theme : Readable. read(0)(john, x_theme))",
        )
        self.assertIn("Definition PropT : Type := Prop.", omitted_result["coq_code"])
        self.assertIn(
            "Definition example_1 : PropT := (at_T noon (exists x_theme : Readable, (read 0 mods_nil john x_theme))).",
            omitted_result["coq_code"],
        )
        self.assertEqual(omitted_result["coq_check"]["status"], "passed")

        explicit_result = run_pipeline("Mary read the book at noon", require_coq=True)
        self.assertTrue(explicit_result["ok"])
        self.assertEqual(
            explicit_result["dependent_type_translation"],
            "at_T(noon, read(0)(mary, book))",
        )
        self.assertIn("Parameter book : Readable.", explicit_result["coq_code"])
        self.assertEqual(explicit_result["coq_check"]["status"], "passed")

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
        self.assertIn(
            "Parameter sit : forall n : nat, ModifierSeq n -> Entity -> PropT.",
            result["coq_code"],
        )
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
            "Parameter butter : forall n : nat, ModifierSeq n -> Entity -> Entity -> PropT.",
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
        self.assertEqual(
            result["ast"]["binders"],
            [
                {"variable": "t_sing", "type": "Time"},
                {"variable": "t_salute", "type": "Time"},
            ],
        )
        self.assertEqual(result["ast"]["first"]["predicate_type"], "Entity -> Time -> Prop")
        self.assertEqual(
            result["ast"]["second"]["predicate_type"],
            "Entity -> Entity -> Time -> Prop",
        )
        self.assertEqual(
            result["ast"]["relation"],
            {
                "predicate": "before",
                "predicate_type": "Time -> Time -> Prop",
                "arguments": ["t_sing", "t_salute"],
            },
        )
        self.assertEqual(result["coq_check"]["status"], "passed")

    def test_timed_after_rejects_reversed_before_relation(self) -> None:
        result = run_pipeline(
            "after the singing of the Marseillaise, John saluted the flag",
            require_coq=False,
        )
        ast = result["ast"]
        ast["relation"]["arguments"] = ["t_salute", "t_sing"]
        type_check = check_timed_after_ast(ast)
        self.assertFalse(type_check["ok"])
        self.assertIn(
            "timed_after.relation must relate t_sing before t_salute",
            type_check["errors"],
        )

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
        perception = result["ast"]["perception"]
        self.assertEqual(perception["predicate"], "see")
        self.assertEqual(perception["predicate_type"], "Entity -> Entity -> Prop")
        self.assertEqual(perception["experiencer"], {"name": "Mary", "type": "Entity"})
        nominalized = perception["object"]
        self.assertEqual(nominalized["kind"], "nominalized_proposition")
        self.assertEqual(nominalized["nominalizer"], "E")
        self.assertEqual(nominalized["nominalizer_type"], "Prop -> Entity")
        self.assertEqual(
            nominalized["proposition"],
            {
                "predicate": "leave",
                "predicate_type": "Entity -> Prop",
                "subject": {"name": "John", "type": "Entity"},
            },
        )
        self.assertTrue(result["type_check"]["ok"])
        self.assertEqual(result["coq_check"]["status"], "passed")

    def test_perception_nominalization_rejects_bad_nominalizer_type(self) -> None:
        result = run_pipeline("Mary saw John leave", require_coq=False)
        ast = result["ast"]
        ast["perception"]["object"]["nominalizer_type"] = "Entity -> Entity"
        type_check = check_perception_nominalization_ast(ast)
        self.assertFalse(type_check["ok"])
        self.assertIn("nominalizer E must have type Prop -> Entity", type_check["errors"])

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
        self.assertEqual(
            result["ast"]["binders"],
            [{"variable": "x", "type": "Entity"}, {"variable": "t", "type": "Time"}],
        )
        self.assertEqual(
            result["ast"]["antecedent"],
            {
                "predicate": "burn",
                "predicate_type": "Entity -> Time -> Prop",
                "arguments": ["x", "t"],
            },
        )
        self.assertEqual(
            result["ast"]["consequent"],
            {
                "predicate": "consume",
                "predicate_type": "Entity -> Time -> Prop",
                "arguments": ["oxygen", "t"],
                "theme": {"name": "oxygen", "type": "Entity"},
            },
        )
        self.assertTrue(result["type_check"]["ok"])
        self.assertEqual(result["coq_check"]["status"], "passed")

    def test_universal_timed_burning_rejects_unshared_time_variable(self) -> None:
        result = run_pipeline("In every burning, oxygen is consumed", require_coq=False)
        ast = result["ast"]
        ast["consequent"]["arguments"] = ["oxygen", "t2"]
        type_check = check_universal_timed_ast(ast)
        self.assertFalse(type_check["ok"])
        self.assertIn(
            "forall_time.consequent must share the bound time variable t",
            type_check["errors"],
        )

    def test_quantifier_scope_ambiguity_some_boy_loves_some_girl(self) -> None:
        result = run_pipeline("some boy loves some girl", require_coq=True)
        self.assertTrue(result["ok"])
        self.assertEqual(result["kind"], "quantifier_scope_ambiguity")
        self.assertEqual(result["construction_rule"]["id"], "quantifier_scope_ambiguity")
        self.assertIn("some_boy_wide_scope", result["coq_code"])
        self.assertIn("some_girl_wide_scope", result["coq_code"])
        self.assertIn("Parameter boy : Entity -> Prop.", result["coq_code"])
        self.assertIn("Parameter girl : Entity -> Prop.", result["coq_code"])
        self.assertIn("Parameter love : Entity -> Entity -> Prop.", result["coq_code"])
        self.assertIn("love x_boy x_girl", result["coq_code"])
        self.assertNotIn("Parameter Event : Type.", result["coq_code"])
        self.assertNotIn("exists e : Event", result["coq_code"])
        self.assertNotIn("Parameter Agent :", result["coq_code"])
        self.assertNotIn("Parameter Theme :", result["coq_code"])
        self.assertNotIn("Parameter some : Entity.", result["coq_code"])
        self.assertNotIn("Parameter boy : nat ->", result["coq_code"])
        self.assertEqual(result["type_check"]["reading_count"], 2)
        self.assertIn("no Event argument is introduced", result["type_check"]["note"])
        readings = result["ast"]["readings"]
        self.assertEqual(
            [binder["role"] for binder in readings[0]["scope_order"]],
            ["subject", "object"],
        )
        self.assertEqual(
            [binder["role"] for binder in readings[1]["scope_order"]],
            ["object", "subject"],
        )
        for reading in readings:
            self.assertEqual(
                reading["relation"]["predicate_type"],
                "Entity -> Entity -> Prop",
            )
            self.assertEqual(
                reading["relation"]["arguments"],
                ["x_boy", "x_girl"],
            )
            for binder in reading["scope_order"]:
                self.assertEqual(binder["predicate_type"], "Entity -> Prop")
        self.assertEqual(result["coq_check"]["status"], "passed")

    def test_quantifier_scope_rejects_duplicate_scope_order(self) -> None:
        result = run_pipeline("some boy loves some girl", require_coq=False)
        readings = result["ast"]["readings"]
        readings[1]["scope_order"] = list(readings[0]["scope_order"])
        type_check = check_quantifier_scope_readings(readings)
        self.assertFalse(type_check["ok"])
        self.assertIn(
            "scope readings must include both subject-wide and object-wide orders",
            type_check["errors"],
        )

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
        self.assertIn("Parameter Event : Type.", rules["quantifier_scope_ambiguity"].forbidden_coq_fragments)
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
        self.assertIn(
            "Cause(John, Transition(vase, integrity_scale, intact, broken))",
            result["dependent_type_translation"],
        )
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
        self.assertEqual(result["result_state_lexicon"], [])
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
        self.assertIn("Result State Lexicon", page)
        self.assertIn("No result states detected.", page)
        self.assertIn("Diagnostics", page)
        self.assertIn("Next Steps", page)
        self.assertIn("No recovery actions needed.", page)
        self.assertIn("Construction Rule", page)
        self.assertIn("Generated Coq", page)
        self.assertIn("repeat(2, knock(0)(John))", page)

    def test_web_page_shows_result_state_lexicon_panel(self) -> None:
        page = render_page("John hammered the metal flat", require_coq=True)
        self.assertIn("Result State Lexicon", page)
        self.assertIn("flat", page)
        self.assertIn("shape_scale", page)
        self.assertIn("not_flat", page)
        self.assertIn("lexical_prestate", page)
        self.assertIn("Result State Lexicon JSON", page)

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

    def test_registered_rule_skips_coq_when_internal_type_check_fails(self) -> None:
        def bad_type_analyzer(sentence: str) -> dict:
            return {
                "kind": "bad_type_rule",
                "input_sentence": sentence,
                "event_semantics": {},
                "dependent_type_translation": "bad",
                "ast": {"kind": "bad"},
                "type_check": {
                    "ok": False,
                    "type": None,
                    "errors": ["synthetic type error"],
                },
                "coq_code": "Definition bad : Prop := True.\n",
            }

        rule = ConstructionRule(
            rule_id="bad_type_rule",
            label="Bad type rule",
            phenomenon="negative type-check test",
            analyzer=bad_type_analyzer,
            forbidden_coq_fragments=("Parameter Event : Type.",),
        )
        result = run_registered_rule(rule, "bad typed sentence", require_coq=True)
        self.assertIsNotNone(result)
        assert result is not None
        self.assertFalse(result["ok"])
        self.assertIsNone(result["construction_hygiene"]["ok"])
        self.assertFalse(result["construction_hygiene"]["checked"])
        self.assertEqual(result["coq_check"]["status"], "skipped")
        self.assertIn("internal type_check failed", result["coq_check"]["message"])
        diagnostics = build_diagnostics(result)
        self.assertEqual(diagnostics["failure_stage"], "type_check")
        self.assertEqual(diagnostics["stages"]["construction_hygiene"], "skipped")
        self.assertEqual(diagnostics["stages"]["coq_check"], "skipped")

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
        self.assertIn("`--require-docx`", readme)
        self.assertIn('python3 -m pip install ".[docx]"', readme)
        self.assertIn("python3 scripts/verify_project.py --skip-coq --require-docx", readme)
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
        self.assertIn("`result_state_lexicon`", readme)
        self.assertIn("Result State Lexicon panel", readme)
        self.assertIn("`construction_rule`", readme)
        self.assertIn("## API Contract", web_design)
        self.assertIn("`sentence`: required natural-language input", web_design)
        self.assertIn("`require_coq`: optional flag", web_design)
        self.assertIn("`dependent_type_translation`", web_design)
        self.assertIn("`result_state_lexicon`", web_design)
        self.assertIn("`source_policy`", web_design)
        self.assertIn("Result State Lexicon panel", web_design)
        self.assertIn("`construction_hygiene`", web_design)
        self.assertIn("failure, it must still return `ok: false`", web_design)
        self.assertIn("The separate `failure_stage` field distinguishes", web_design)
        self.assertIn("The web status line should surface `recovery_hint` directly", web_design)
        self.assertIn("Machine clients should prefer `recovery_actions`", web_design)

if __name__ == "__main__":
    unittest.main()
