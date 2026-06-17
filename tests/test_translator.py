import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.export_lexicon_patch_drafts import build_patch_bundle, write_output_file
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
    check_lexical_state_change_ast,
    check_passive_argument_omission_ast,
    check_perception_nominalization_ast,
    check_quantifier_scope_readings,
    check_stative_result_state_ast,
    check_timed_after_ast,
    check_universal_timed_ast,
    construction_rules,
    run_registered_rule,
    run_pipeline,
    sentence_to_event_semantics,
    state_change_verb_metadata,
    verify_coq_code,
)
from translator.state_change_lexicon import (
    STATE_CHANGE_VERB_REGISTRY,
    STATE_CHANGE_VERB_TARGETS,
)
from translator.surface_lexicon import (
    MODIFIER_ROLE_BY_PREDICATE,
    PASSIVE_AUXILIARIES,
    modifier_predicate,
    modifier_semantic_role,
    modifier_surface_audit,
    passive_participle_audit,
    is_passive_participle,
    lemma_verb,
    surface_verb_audit,
)
from web.app import (
    ANALYZE_RESPONSE_SCHEMA,
    PipelineHandler,
    analyze_sentence,
    build_diagnostics,
    modifier_role_audit,
    parse_patch_resolution_params,
    render_page,
    render_lexicon_patch_text,
    result_state_warning_for_entry,
    result_state_warnings,
)


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
        self.assertEqual(
            result["ast"]["body"]["modifier_roles"],
            {
                "kind": "modifier_roles",
                "roles": [
                    {
                        "modifier": "slowly",
                        "type": "Adv",
                        "semantic_role": "Manner",
                        "source": "modifier",
                        "surface_lexicon": modifier_surface_audit("slowly", "Adv", "Manner"),
                    },
                    {
                        "modifier": "in(bathroom)",
                        "type": "Adv",
                        "semantic_role": "Location",
                        "source": "modifier",
                        "surface_lexicon": modifier_surface_audit(
                            "in(bathroom)", "Adv", "Location"
                        ),
                    },
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

    def test_state_change_verb_registry_is_external_and_consistent(self) -> None:
        self.assertEqual(STATE_CHANGE_VERB_TARGETS["die"], "dead")
        self.assertEqual(STATE_CHANGE_VERB_TARGETS["kill"], "dead")
        self.assertFalse(STATE_CHANGE_VERB_REGISTRY["die"].allow_causative)
        self.assertFalse(STATE_CHANGE_VERB_REGISTRY["die"].allow_instrument)
        self.assertFalse(STATE_CHANGE_VERB_REGISTRY["kill"].allow_inchoative)
        self.assertEqual(
            state_change_verb_metadata("kill"),
            {
                "verb": "kill",
                "target_state": "dead",
                "allow_inchoative": False,
                "allow_causative": True,
                "allow_instrument": True,
            },
        )
        for verb, target_state in STATE_CHANGE_VERB_TARGETS.items():
            with self.subTest(verb=verb):
                self.assertIn(target_state, SOURCE_STATE_BY_TARGET_STATE)
                self.assertIn(SOURCE_STATE_BY_TARGET_STATE[target_state], STATE_LEXICON)

    def test_surface_lexicon_normalizes_irregular_passives(self) -> None:
        self.assertEqual(PASSIVE_AUXILIARIES, {"is", "was", "are", "were"})
        self.assertTrue(is_passive_participle("seen"))
        self.assertTrue(is_passive_participle("written"))
        self.assertTrue(is_passive_participle("opened"))
        self.assertFalse(is_passive_participle("opening"))
        self.assertEqual(lemma_verb("seen"), "see")
        self.assertEqual(lemma_verb("written"), "write")
        self.assertEqual(lemma_verb("died"), "die")
        self.assertEqual(lemma_verb("opened"), "open")
        self.assertEqual(lemma_verb("froze"), "freeze")
        self.assertEqual(
            passive_participle_audit("written"),
            {
                "participle": "written",
                "lemma": "write",
                "source": "translator/surface_lexicon.py",
            },
        )
        self.assertEqual(
            surface_verb_audit("froze"),
            {
                "surface_verb": "froze",
                "lemma": "freeze",
                "source": "translator/surface_lexicon.py",
            },
        )
        self.assertEqual(
            modifier_surface_audit("in(bathroom)", "Adv", "Location"),
            {
                "surface_modifier": "in(bathroom)",
                "normalized_modifier": "in_bathroom",
                "type": "Adv",
                "semantic_role": "Location",
                "source": "translator/surface_lexicon.py",
            },
        )
        self.assertEqual(
            modifier_surface_audit("with(knife)", "Adv", "Instrument"),
            {
                "surface_modifier": "with(knife)",
                "normalized_modifier": "with_knife",
                "type": "Adv",
                "semantic_role": "Instrument",
                "source": "translator/surface_lexicon.py",
            },
        )
        self.assertEqual(MODIFIER_ROLE_BY_PREDICATE["with"], "Instrument")
        self.assertEqual(modifier_predicate("in(bathroom)"), "in")
        self.assertEqual(modifier_semantic_role("in(bathroom)"), "Location")
        self.assertEqual(modifier_semantic_role("on(mat)"), "Location")
        self.assertEqual(modifier_semantic_role("with(knife)"), "Instrument")
        self.assertEqual(modifier_semantic_role("from(home)"), "Source")
        self.assertEqual(modifier_semantic_role("to(school)"), "Goal")
        self.assertEqual(modifier_semantic_role("slowly"), "Manner")

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

        flat_api = analyze_sentence("John hammered the metal flat", require_coq=True)
        self.assertTrue(flat_api["ok"])
        self.assertEqual(flat_api["diagnostics"]["warnings"], [])

        painted_api = analyze_sentence("Mary painted the door red", require_coq=True)
        self.assertTrue(painted_api["ok"])
        self.assertEqual(painted_api["diagnostics"]["summary"], "translation verified")
        self.assertEqual(
            painted_api["diagnostics"]["warnings"],
            [
                {
                    "kind": "unknown_result_source",
                    "state": "red",
                    "scale": "color_scale",
                    "message": (
                        "Result state red has no unique lexical pre-state; "
                        "source remains unknown_state."
                    ),
                    "suggested_action": {
                        "kind": "add_state_prestate",
                        "label": "Add lexical pre-state",
                        "detail": (
                            "Choose a contextually justified source state for red on "
                            "color_scale, or keep unknown_state when the source is "
                            "genuinely underspecified."
                        ),
                        "lexicon_entry_draft": {
                            "draft_id": "state-red--unknown_source_allowed",
                            "state": "red",
                            "scale": "color_scale",
                            "default_source_state": "<choose_source_state>",
                            "allow_unknown_source": False,
                            "current_source_policy": "unknown_source_allowed",
                            "source_policy_after_update": "lexical_prestate",
                            "requires_human_choice": True,
                            "placeholder_fields": ["default_source_state"],
                            "can_auto_apply": False,
                            "state_lexicon_patch_line": (
                                "'red': StateLexiconEntry('color_scale', "
                                "default_source_state='<choose_source_state>'),"
                            ),
                        },
                    },
                }
            ],
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

    def test_type_checker_rejects_bad_modifier_role_metadata(self) -> None:
        result = check_term(
            {
                "kind": "application",
                "function": "butter",
                "adverb_count": 1,
                "modifiers": ["with(knife)"],
                "modifier_vector": modifier_vector(["with(knife)"]),
                "modifier_roles": {
                    "kind": "modifier_roles",
                    "roles": [
                        {
                            "modifier": "in(bathroom)",
                            "type": "Entity",
                            "semantic_role": "",
                            "source": "entity",
                        },
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
        self.assertTrue(
            any("application.modifier_roles.roles[0].modifier" in error for error in result["errors"])
        )
        self.assertTrue(
            any(
                "application.modifier_roles.roles[0].type must be Adv" in error
                for error in result["errors"]
            )
        )

        wrong_role = check_term(
            {
                "kind": "application",
                "function": "butter",
                "adverb_count": 1,
                "modifiers": ["with(knife)"],
                "modifier_vector": modifier_vector(["with(knife)"]),
                "modifier_roles": {
                    "kind": "modifier_roles",
                    "roles": [
                        {
                            "modifier": "with(knife)",
                            "type": "Adv",
                            "semantic_role": "Location",
                            "source": "modifier",
                        },
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
        self.assertFalse(wrong_role["ok"])
        self.assertTrue(
            any("must be Instrument for with(knife)" in error for error in wrong_role["errors"])
        )

    def test_type_checker_rejects_bad_modifier_surface_lexicon_audit(self) -> None:
        result = run_pipeline(
            "john buttered the toast in the bathroom with a knife",
            require_coq=False,
        )
        cases = [
            (
                "surface_modifier",
                "in(room)",
                "ast: application.modifier_roles.roles[0].surface_lexicon.surface_modifier "
                "must match modifier",
            ),
            (
                "normalized_modifier",
                "bathroom",
                "ast: application.modifier_roles.roles[0].surface_lexicon.normalized_modifier "
                "must be in_bathroom",
            ),
            (
                "type",
                "Entity",
                "ast: application.modifier_roles.roles[0].surface_lexicon.type "
                "must match modifier type",
            ),
            (
                "semantic_role",
                "Instrument",
                "ast: application.modifier_roles.roles[0].surface_lexicon.semantic_role "
                "must match semantic_role",
            ),
            (
                "source",
                "local",
                "ast: application.modifier_roles.roles[0].surface_lexicon.source "
                "must identify the surface lexicon",
            ),
        ]
        for field, bad_value, expected_error in cases:
            with self.subTest(field=field):
                ast = json.loads(json.dumps(result["ast"]))
                ast["modifier_roles"]["roles"][0]["surface_lexicon"][field] = bad_value
                type_check = check_term(ast)
                self.assertFalse(type_check["ok"])
                self.assertIn(expected_error, type_check["errors"])

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

    def test_packaged_cli_exports_coq_module(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "translator.dependent_type_event_translator",
                str(EXAMPLES / "example_eat_omission.json"),
                "--export-module",
                "coq",
            ],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn("Parameter Food : Type.", completed.stdout)
        self.assertIn("Definition example_1 : Prop :=", completed.stdout)
        self.assertIn("Check example_1.", completed.stdout)

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

    def test_directional_modifiers_use_source_goal_adv_roles(self) -> None:
        result = run_pipeline("John went from home to school", require_coq=True)
        self.assertTrue(result["ok"])
        self.assertEqual(
            result["dependent_type_translation"],
            "go(2)(from(home), to(school), john)",
        )
        self.assertEqual(
            result["ast"]["modifier_roles"]["roles"],
            [
                {
                    "modifier": "from(home)",
                    "type": "Adv",
                    "semantic_role": "Source",
                    "source": "modifier",
                    "surface_lexicon": modifier_surface_audit(
                        "from(home)", "Adv", "Source"
                    ),
                },
                {
                    "modifier": "to(school)",
                    "type": "Adv",
                    "semantic_role": "Goal",
                    "source": "modifier",
                    "surface_lexicon": modifier_surface_audit(
                        "to(school)", "Adv", "Goal"
                    ),
                },
            ],
        )
        self.assertIn("Parameter from_home : Adv.", result["coq_code"])
        self.assertIn("Parameter to_school : Adv.", result["coq_code"])
        self.assertNotIn("Parameter from_home : Entity.", result["coq_code"])
        self.assertNotIn("Parameter to_school : Entity.", result["coq_code"])
        self.assertEqual(result["coq_check"]["status"], "passed")

        page_result = analyze_sentence(
            "John went from home to school",
            require_coq=True,
        )
        self.assertEqual(
            page_result["modifier_role_audit"],
            [
                {
                    "path": "ast",
                    "function": "go",
                    "modifier": "from(home)",
                    "type": "Adv",
                    "semantic_role": "Source",
                    "source": "modifier",
                    "surface_lexicon": modifier_surface_audit(
                        "from(home)", "Adv", "Source"
                    ),
                },
                {
                    "path": "ast",
                    "function": "go",
                    "modifier": "to(school)",
                    "type": "Adv",
                    "semantic_role": "Goal",
                    "source": "modifier",
                    "surface_lexicon": modifier_surface_audit(
                        "to(school)", "Adv", "Goal"
                    ),
                },
            ],
        )
        page = render_page("John went from home to school", require_coq=True)
        self.assertIn("&quot;semantic_role&quot;: &quot;Source&quot;", page)
        self.assertIn("&quot;semantic_role&quot;: &quot;Goal&quot;", page)
        self.assertIn("&quot;normalized_modifier&quot;: &quot;from_home&quot;", page)
        self.assertIn("&quot;normalized_modifier&quot;: &quot;to_school&quot;", page)

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
        self.assertEqual(
            result["ast"]["modifier_roles"]["roles"],
            [
                {
                    "modifier": "in(bathroom)",
                    "type": "Adv",
                    "semantic_role": "Location",
                    "source": "modifier",
                    "surface_lexicon": modifier_surface_audit(
                        "in(bathroom)", "Adv", "Location"
                    ),
                },
                {
                    "modifier": "with(knife)",
                    "type": "Adv",
                    "semantic_role": "Instrument",
                    "source": "modifier",
                    "surface_lexicon": modifier_surface_audit(
                        "with(knife)", "Adv", "Instrument"
                    ),
                },
            ],
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

    def test_modifier_role_audit_is_exposed_for_api_and_page(self) -> None:
        result = analyze_sentence(
            "john buttered the toast in the bathroom with a knife",
            require_coq=True,
        )
        self.assertTrue(result["ok"])
        self.assertEqual(
            result["modifier_role_audit"],
            [
                {
                    "path": "ast",
                    "function": "butter",
                    "modifier": "in(bathroom)",
                    "type": "Adv",
                    "semantic_role": "Location",
                    "source": "modifier",
                    "surface_lexicon": modifier_surface_audit(
                        "in(bathroom)", "Adv", "Location"
                    ),
                },
                {
                    "path": "ast",
                    "function": "butter",
                    "modifier": "with(knife)",
                    "type": "Adv",
                    "semantic_role": "Instrument",
                    "source": "modifier",
                    "surface_lexicon": modifier_surface_audit(
                        "with(knife)", "Adv", "Instrument"
                    ),
                },
            ],
        )
        self.assertEqual(modifier_role_audit(result["ast"]), result["modifier_role_audit"])

        page = render_page(
            "john buttered the toast in the bathroom with a knife",
            require_coq=True,
        )
        self.assertIn("Modifier Role Audit", page)
        self.assertIn("&quot;semantic_role&quot;: &quot;Location&quot;", page)
        self.assertIn("&quot;semantic_role&quot;: &quot;Instrument&quot;", page)
        self.assertIn("&quot;normalized_modifier&quot;: &quot;in_bathroom&quot;", page)
        self.assertIn("&quot;normalized_modifier&quot;: &quot;with_knife&quot;", page)

    def test_modifier_role_audit_recurses_into_nested_applications(self) -> None:
        result = translate(load_example("example_butter.json"))
        self.assertEqual(result["ast"]["kind"], "time")
        self.assertEqual(
            modifier_role_audit(result["ast"]),
            [
                {
                    "path": "ast.body",
                    "function": "butter",
                    "modifier": "slowly",
                    "type": "Adv",
                    "semantic_role": "Manner",
                    "source": "modifier",
                    "surface_lexicon": modifier_surface_audit("slowly", "Adv", "Manner"),
                },
                {
                    "path": "ast.body",
                    "function": "butter",
                    "modifier": "in(bathroom)",
                    "type": "Adv",
                    "semantic_role": "Location",
                    "source": "modifier",
                    "surface_lexicon": modifier_surface_audit(
                        "in(bathroom)", "Adv", "Location"
                    ),
                },
            ],
        )

    def test_lexical_state_change_distinguishes_inchoative_and_causative(self) -> None:
        inchoative = run_pipeline("the door opened", require_coq=True)
        self.assertTrue(inchoative["ok"])
        self.assertEqual(inchoative["kind"], "lexical_state_change")
        self.assertEqual(inchoative["construction_rule"]["id"], "lexical_state_change")
        self.assertEqual(
            inchoative["dependent_type_translation"],
            "Change(Transition(door, access_scale, closed, open))",
        )
        self.assertEqual(
            inchoative["ast"],
            {
                "kind": "lexical_state_change",
                "verb": "open",
                "surface_lexicon": {
                    "surface_verb": "opened",
                    "lemma": "open",
                    "source": "translator/surface_lexicon.py",
                },
                "frame": "inchoative",
                "transition": {
                    "kind": "transition",
                    "theme": {"name": "door", "type": "Entity"},
                    "state_scale": "access_scale",
                    "source_state": "closed",
                    "target_state": {"name": "open", "type": "State"},
                },
            },
        )
        self.assertEqual(
            inchoative["result_state_lexicon"],
            [
                {
                    "state": "open",
                    "scale": "access_scale",
                    "default_source_state": "closed",
                    "source_policy": "lexical_prestate",
                }
            ],
        )
        self.assertIn("Parameter Change : TransitionT -> Prop.", inchoative["coq_code"])
        self.assertIn("Change (Transition door access_scale closed open).", inchoative["coq_code"])
        self.assertNotIn("Parameter Event : Type.", inchoative["coq_code"])
        self.assertNotIn("Parameter Agent :", inchoative["coq_code"])
        self.assertNotIn("Parameter Theme :", inchoative["coq_code"])
        self.assertEqual(inchoative["coq_check"]["status"], "passed")

        causative = run_pipeline("John opened the door", require_coq=True)
        self.assertTrue(causative["ok"])
        self.assertEqual(causative["kind"], "lexical_state_change")
        self.assertEqual(
            causative["dependent_type_translation"],
            "Cause(john, Transition(door, access_scale, closed, open))",
        )
        self.assertEqual(causative["ast"]["frame"], "causative")
        self.assertEqual(
            causative["ast"]["causer"],
            {"name": "john", "type": "Entity", "source": "subject"},
        )
        self.assertIn("Cause john (Transition door access_scale closed open).", causative["coq_code"])
        self.assertEqual(causative["coq_check"]["status"], "passed")

        instrumental = run_pipeline("John opened the door with a key", require_coq=True)
        self.assertTrue(instrumental["ok"])
        self.assertEqual(
            instrumental["dependent_type_translation"],
            "CauseWithInstrument(john, key, Transition(door, access_scale, closed, open))",
        )
        self.assertEqual(instrumental["ast"]["frame"], "instrumental")
        self.assertEqual(
            instrumental["ast"]["instrument"],
            {"name": "key", "type": "Entity", "source": "with_phrase"},
        )
        self.assertIn(
            "Parameter CauseWithInstrument : Entity -> Entity -> TransitionT -> Prop.",
            instrumental["coq_code"],
        )
        self.assertIn(
            "CauseWithInstrument john key (Transition door access_scale closed open).",
            instrumental["coq_code"],
        )
        self.assertEqual(instrumental["coq_check"]["status"], "passed")

        closed = run_pipeline("the door closed", require_coq=True)
        self.assertTrue(closed["ok"])
        self.assertEqual(
            closed["dependent_type_translation"],
            "Change(Transition(door, access_scale, open, closed))",
        )
        self.assertEqual(closed["coq_check"]["status"], "passed")

    def test_lexical_state_change_uses_extended_state_verb_lexicon(self) -> None:
        dried = run_pipeline("the clothes dried", require_coq=True)
        self.assertTrue(dried["ok"])
        self.assertEqual(dried["kind"], "lexical_state_change")
        self.assertEqual(
            dried["dependent_type_translation"],
            "Change(Transition(clothes, moisture_scale, wet, dry))",
        )
        self.assertEqual(dried["ast"]["transition"]["theme"]["name"], "clothes")
        self.assertEqual(dried["ast"]["transition"]["state_scale"], "moisture_scale")
        self.assertEqual(dried["ast"]["transition"]["source_state"], "wet")
        self.assertEqual(dried["ast"]["transition"]["target_state"]["name"], "dry")
        self.assertEqual(dried["ast"]["frame"], "inchoative")
        self.assertEqual(
            dried["ast"]["surface_lexicon"],
            {
                "surface_verb": "dried",
                "lemma": "dry",
                "source": "translator/surface_lexicon.py",
            },
        )
        self.assertEqual(
            dried["result_state_lexicon"],
            [
                {
                    "state": "dry",
                    "scale": "moisture_scale",
                    "default_source_state": "wet",
                    "source_policy": "lexical_prestate",
                }
            ],
        )
        self.assertEqual(
            dried["state_change_verb_entry"],
            {
                "verb": "dry",
                "target_state": "dry",
                "allow_inchoative": True,
                "allow_causative": True,
                "allow_instrument": True,
            },
        )
        self.assertEqual(dried["state_change_verb_entry"], state_change_verb_metadata("dry"))
        self.assertEqual(dried["coq_check"]["status"], "passed")

        instrumental = run_pipeline("John dried the clothes with a towel", require_coq=True)
        self.assertTrue(instrumental["ok"])
        self.assertEqual(instrumental["ast"]["frame"], "instrumental")
        self.assertEqual(
            instrumental["dependent_type_translation"],
            "CauseWithInstrument(john, towel, Transition(clothes, moisture_scale, wet, dry))",
        )
        self.assertEqual(
            instrumental["ast"]["causer"],
            {"name": "john", "type": "Entity", "source": "subject"},
        )
        self.assertEqual(
            instrumental["ast"]["instrument"],
            {"name": "towel", "type": "Entity", "source": "with_phrase"},
        )
        self.assertEqual(instrumental["coq_check"]["status"], "passed")

        froze = run_pipeline("the water froze", require_coq=True)
        self.assertTrue(froze["ok"])
        self.assertEqual(
            froze["dependent_type_translation"],
            "Change(Transition(water, phase_scale, liquid, frozen))",
        )
        self.assertEqual(froze["ast"]["transition"]["target_state"]["name"], "frozen")
        self.assertEqual(
            froze["ast"]["surface_lexicon"],
            {
                "surface_verb": "froze",
                "lemma": "freeze",
                "source": "translator/surface_lexicon.py",
            },
        )
        self.assertEqual(froze["coq_check"]["status"], "passed")

        melted = run_pipeline("John melted the ice", require_coq=True)
        self.assertTrue(melted["ok"])
        self.assertEqual(
            melted["dependent_type_translation"],
            "Cause(john, Transition(ice, phase_scale, solid, melted))",
        )
        self.assertEqual(melted["coq_check"]["status"], "passed")

        cleaned = run_pipeline("Mary cleaned the room", require_coq=True)
        self.assertTrue(cleaned["ok"])
        self.assertEqual(
            cleaned["dependent_type_translation"],
            "Cause(mary, Transition(room, cleanliness_scale, dirty, clean))",
        )
        self.assertEqual(cleaned["coq_check"]["status"], "passed")

        emptied = run_pipeline("the tank emptied", require_coq=True)
        self.assertTrue(emptied["ok"])
        self.assertEqual(
            emptied["dependent_type_translation"],
            "Change(Transition(tank, content_scale, full, empty))",
        )
        self.assertEqual(emptied["coq_check"]["status"], "passed")

        filled = run_pipeline("John filled the glass", require_coq=True)
        self.assertTrue(filled["ok"])
        self.assertEqual(
            filled["dependent_type_translation"],
            "Cause(john, Transition(glass, content_scale, empty, full))",
        )
        self.assertEqual(filled["coq_check"]["status"], "passed")

    def test_lexical_state_change_enforces_frame_licensing(self) -> None:
        died = run_pipeline("John died", require_coq=True)
        self.assertTrue(died["ok"])
        self.assertEqual(died["ast"]["frame"], "inchoative")
        self.assertEqual(
            died["ast"]["surface_lexicon"],
            {
                "surface_verb": "died",
                "lemma": "die",
                "source": "translator/surface_lexicon.py",
            },
        )
        self.assertEqual(
            died["dependent_type_translation"],
            "Change(Transition(john, life_scale, alive, dead))",
        )
        self.assertEqual(
            died["state_change_verb_entry"],
            {
                "verb": "die",
                "target_state": "dead",
                "allow_inchoative": True,
                "allow_causative": False,
                "allow_instrument": False,
            },
        )
        self.assertEqual(died["coq_check"]["status"], "passed")

        killed = run_pipeline("Mary killed the plant", require_coq=True)
        self.assertTrue(killed["ok"])
        self.assertEqual(killed["ast"]["frame"], "causative")
        self.assertEqual(
            killed["ast"]["surface_lexicon"],
            {
                "surface_verb": "killed",
                "lemma": "kill",
                "source": "translator/surface_lexicon.py",
            },
        )
        self.assertEqual(
            killed["dependent_type_translation"],
            "Cause(mary, Transition(plant, life_scale, alive, dead))",
        )
        self.assertEqual(
            killed["state_change_verb_entry"],
            {
                "verb": "kill",
                "target_state": "dead",
                "allow_inchoative": False,
                "allow_causative": True,
                "allow_instrument": True,
            },
        )
        self.assertEqual(killed["coq_check"]["status"], "passed")

        killed_with = run_pipeline("Mary killed the plant with poison", require_coq=True)
        self.assertTrue(killed_with["ok"])
        self.assertEqual(killed_with["ast"]["frame"], "instrumental")
        self.assertEqual(
            killed_with["dependent_type_translation"],
            "CauseWithInstrument(mary, poison, Transition(plant, life_scale, alive, dead))",
        )
        self.assertEqual(killed_with["coq_check"]["status"], "passed")

        unlicensed_inchoative = run_pipeline("the plant killed", require_coq=False)
        self.assertFalse(unlicensed_inchoative["ok"])
        self.assertEqual(unlicensed_inchoative["kind"], "lexical_state_change")
        self.assertEqual(unlicensed_inchoative["ast"]["frame"], "inchoative")
        self.assertIn(
            "state-change verb does not license the inchoative frame",
            unlicensed_inchoative["type_check"]["errors"],
        )
        self.assertEqual(unlicensed_inchoative["coq_check"]["status"], "skipped")

        unlicensed_causative = run_pipeline("Mary died the plant", require_coq=False)
        self.assertFalse(unlicensed_causative["ok"])
        self.assertEqual(unlicensed_causative["kind"], "lexical_state_change")
        self.assertEqual(unlicensed_causative["ast"]["frame"], "causative")
        self.assertIn(
            "state-change verb does not license the causative frame",
            unlicensed_causative["type_check"]["errors"],
        )
        self.assertEqual(unlicensed_causative["coq_check"]["status"], "skipped")

    def test_lexical_state_change_rejects_bad_source_state(self) -> None:
        result = run_pipeline("the door opened", require_coq=False)
        ast = result["ast"]
        ast["transition"]["source_state"] = "open"
        type_check = check_lexical_state_change_ast(ast)
        self.assertFalse(type_check["ok"])
        self.assertIn("state-change source_state must match the state lexicon", type_check["errors"])

    def test_lexical_state_change_rejects_registered_target_mismatch(self) -> None:
        result = run_pipeline("the door opened", require_coq=False)
        ast = result["ast"]
        ast["transition"]["source_state"] = "open"
        ast["transition"]["target_state"]["name"] = "closed"
        type_check = check_lexical_state_change_ast(ast)
        self.assertFalse(type_check["ok"])
        self.assertIn(
            "state-change target_state must match the registered verb target",
            type_check["errors"],
        )

    def test_lexical_state_change_rejects_frame_mismatch_and_unlicensed_frames(self) -> None:
        result = run_pipeline("the door opened", require_coq=False)
        ast = result["ast"]
        ast["frame"] = "causative"
        type_check = check_lexical_state_change_ast(ast)
        self.assertFalse(type_check["ok"])
        self.assertIn(
            "state-change frame must match its causer and instrument fields",
            type_check["errors"],
        )

        killed = run_pipeline("Mary killed the plant", require_coq=False)
        killed_ast = killed["ast"]
        killed_ast["frame"] = "inchoative"
        killed_ast.pop("causer")
        type_check = check_lexical_state_change_ast(killed_ast)
        self.assertFalse(type_check["ok"])
        self.assertIn(
            "state-change verb does not license the inchoative frame",
            type_check["errors"],
        )

        died = run_pipeline("John died", require_coq=False)
        died_ast = died["ast"]
        died_ast["frame"] = "causative"
        died_ast["causer"] = {"name": "mary", "type": "Entity", "source": "subject"}
        type_check = check_lexical_state_change_ast(died_ast)
        self.assertFalse(type_check["ok"])
        self.assertIn(
            "state-change verb does not license the causative frame",
            type_check["errors"],
        )

    def test_lexical_state_change_rejects_bad_surface_lexicon_audit(self) -> None:
        result = run_pipeline("the water froze", require_coq=False)
        ast = result["ast"]
        ast["surface_lexicon"]["lemma"] = "frost"
        type_check = check_lexical_state_change_ast(ast)
        self.assertFalse(type_check["ok"])
        self.assertIn(
            "state-change surface_lexicon.lemma must match verb",
            type_check["errors"],
        )

    def test_stative_result_state_uses_state_not_omitted_agent(self) -> None:
        broken = run_pipeline("the vase is broken", require_coq=True)
        self.assertTrue(broken["ok"])
        self.assertEqual(broken["kind"], "stative_result_state")
        self.assertEqual(broken["construction_rule"]["id"], "stative_result_state")
        self.assertEqual(
            broken["dependent_type_translation"],
            "holds_state(vase, integrity_scale, broken)",
        )
        self.assertEqual(
            broken["ast"],
            {
                "kind": "stative_result_state",
                "subject": {"name": "vase", "type": "Entity"},
                "state": {"name": "broken", "type": "State"},
                "state_scale": "integrity_scale",
                "predicate": "holds_state",
                "predicate_type": "Entity -> StateScale -> State -> Prop",
                "auxiliary": "is",
            },
        )
        self.assertIn("Parameter broken : State.", broken["coq_code"])
        self.assertIn("Parameter integrity_scale : StateScale.", broken["coq_code"])
        self.assertIn(
            "Parameter holds_state : Entity -> StateScale -> State -> Prop.",
            broken["coq_code"],
        )
        self.assertIn("holds_state vase integrity_scale broken.", broken["coq_code"])
        self.assertNotIn("exists x_agent", broken["coq_code"])
        self.assertNotIn("Parameter Event : Type.", broken["coq_code"])
        self.assertNotIn("Parameter Agent :", broken["coq_code"])
        self.assertNotIn("Parameter Theme :", broken["coq_code"])
        self.assertEqual(broken["coq_check"]["status"], "passed")

        open_state = run_pipeline("the door is open", require_coq=True)
        self.assertTrue(open_state["ok"])
        self.assertEqual(open_state["kind"], "stative_result_state")
        self.assertEqual(
            open_state["dependent_type_translation"],
            "holds_state(door, access_scale, open)",
        )
        self.assertIn("Parameter open : State.", open_state["coq_code"])
        self.assertEqual(open_state["coq_check"]["status"], "passed")

        agentive = run_pipeline("the vase was broken by John", require_coq=True)
        self.assertTrue(agentive["ok"])
        self.assertEqual(agentive["kind"], "passive_argument_omission")
        self.assertEqual(agentive["dependent_type_translation"], "break(john, vase)")

    def test_stative_result_state_rejects_bad_scale(self) -> None:
        result = run_pipeline("the vase is broken", require_coq=False)
        ast = result["ast"]
        ast["state_scale"] = "access_scale"
        type_check = check_stative_result_state_ast(ast)
        self.assertFalse(type_check["ok"])
        self.assertIn("stative state_scale must match the state lexicon", type_check["errors"])

    def test_passive_argument_omission_uses_existential_agent_not_event(self) -> None:
        explicit = run_pipeline("the toast was buttered by John", require_coq=True)
        self.assertTrue(explicit["ok"])
        self.assertEqual(explicit["kind"], "passive_argument_omission")
        self.assertEqual(explicit["construction_rule"]["id"], "passive_argument_omission")
        self.assertEqual(explicit["dependent_type_translation"], "butter(john, toast)")
        self.assertEqual(
            explicit["ast"],
            {
                "kind": "passive_argument_omission",
                "predicate": "butter",
                "predicate_type": "Entity -> Entity -> Prop",
                "auxiliary": "was",
                "surface_lexicon": {
                    "participle": "buttered",
                    "lemma": "butter",
                    "source": "translator/surface_lexicon.py",
                },
                "argument_order": ["Agent", "Patient"],
                "patient": {"name": "toast", "type": "Entity", "surface_role": "subject"},
                "agent": {"name": "john", "type": "Entity", "source": "by_phrase"},
            },
        )
        self.assertIn("Parameter toast : Entity.", explicit["coq_code"])
        self.assertIn("Parameter john : Entity.", explicit["coq_code"])
        self.assertIn("Parameter butter : Entity -> Entity -> Prop.", explicit["coq_code"])
        self.assertIn("Definition passive_butter_by_agent : Prop :=", explicit["coq_code"])
        self.assertIn("butter john toast.", explicit["coq_code"])
        self.assertNotIn("Parameter Event : Type.", explicit["coq_code"])
        self.assertNotIn("Parameter Agent :", explicit["coq_code"])
        self.assertNotIn("Parameter Theme :", explicit["coq_code"])
        self.assertEqual(explicit["coq_check"]["status"], "passed")

        omitted = run_pipeline("the toast was buttered", require_coq=True)
        self.assertTrue(omitted["ok"])
        self.assertEqual(
            omitted["dependent_type_translation"],
            "exists x_agent : Entity. butter(x_agent, toast)",
        )
        self.assertEqual(
            omitted["ast"]["agent"],
            {"variable": "x_agent", "type": "Entity", "source": "omitted_existential"},
        )
        self.assertIn("exists x_agent : Entity", omitted["coq_code"])
        self.assertIn("butter x_agent toast.", omitted["coq_code"])
        self.assertNotIn("Parameter Event : Type.", omitted["coq_code"])
        self.assertNotIn("Parameter Agent :", omitted["coq_code"])
        self.assertNotIn("Parameter Theme :", omitted["coq_code"])
        self.assertEqual(omitted["coq_check"]["status"], "passed")

        present = run_pipeline("the toast is buttered", require_coq=True)
        self.assertTrue(present["ok"])
        self.assertEqual(present["kind"], "passive_argument_omission")
        self.assertEqual(present["ast"]["auxiliary"], "is")
        self.assertEqual(
            present["dependent_type_translation"],
            "exists x_agent : Entity. butter(x_agent, toast)",
        )
        self.assertIn("Definition passive_butter_omitted_agent : Prop :=", present["coq_code"])
        self.assertEqual(present["coq_check"]["status"], "passed")

        plural_auxiliary = run_pipeline("the doors were opened by John", require_coq=True)
        self.assertTrue(plural_auxiliary["ok"])
        self.assertEqual(plural_auxiliary["kind"], "passive_argument_omission")
        self.assertEqual(plural_auxiliary["ast"]["auxiliary"], "were")
        self.assertEqual(plural_auxiliary["dependent_type_translation"], "open(john, doors)")
        self.assertIn("Parameter doors : Entity.", plural_auxiliary["coq_code"])
        self.assertIn("Parameter open : Entity -> Entity -> Prop.", plural_auxiliary["coq_code"])
        self.assertEqual(plural_auxiliary["coq_check"]["status"], "passed")

        irregular_participle = run_pipeline("John was seen by Mary", require_coq=True)
        self.assertTrue(irregular_participle["ok"])
        self.assertEqual(irregular_participle["kind"], "passive_argument_omission")
        self.assertEqual(irregular_participle["ast"]["predicate"], "see")
        self.assertEqual(irregular_participle["dependent_type_translation"], "see(mary, john)")
        self.assertIn("Parameter see : Entity -> Entity -> Prop.", irregular_participle["coq_code"])
        self.assertEqual(irregular_participle["coq_check"]["status"], "passed")

        omitted_irregular = run_pipeline("the letter was written", require_coq=True)
        self.assertTrue(omitted_irregular["ok"])
        self.assertEqual(omitted_irregular["ast"]["predicate"], "write")
        self.assertEqual(
            omitted_irregular["ast"]["surface_lexicon"],
            {
                "participle": "written",
                "lemma": "write",
                "source": "translator/surface_lexicon.py",
            },
        )
        self.assertEqual(
            omitted_irregular["dependent_type_translation"],
            "exists x_agent : Entity. write(x_agent, letter)",
        )
        self.assertIn("Parameter write : Entity -> Entity -> Prop.", omitted_irregular["coq_code"])
        self.assertEqual(omitted_irregular["coq_check"]["status"], "passed")

    def test_passive_argument_omission_rejects_bad_agent_source(self) -> None:
        result = run_pipeline("the toast was buttered", require_coq=False)
        ast = result["ast"]
        ast["agent"]["source"] = "event_role"
        type_check = check_passive_argument_omission_ast(ast)
        self.assertFalse(type_check["ok"])
        self.assertIn(
            "passive agent.source must be by_phrase or omitted_existential",
            type_check["errors"],
        )

    def test_passive_argument_omission_rejects_bad_auxiliary(self) -> None:
        result = run_pipeline("the toast was buttered", require_coq=False)
        ast = result["ast"]
        ast["auxiliary"] = "did"
        type_check = check_passive_argument_omission_ast(ast)
        self.assertFalse(type_check["ok"])
        self.assertIn(
            "passive auxiliary must be is, was, are, or were",
            type_check["errors"],
        )

    def test_passive_argument_omission_rejects_bad_surface_lexicon_audit(self) -> None:
        result = run_pipeline("John was seen by Mary", require_coq=False)
        ast = result["ast"]
        ast["surface_lexicon"]["lemma"] = "watch"
        type_check = check_passive_argument_omission_ast(ast)
        self.assertFalse(type_check["ok"])
        self.assertIn(
            "passive surface_lexicon.lemma must match predicate",
            type_check["errors"],
        )

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
            "passive_argument_omission",
            "lexical_state_change",
            "stative_result_state",
            "timed_after",
            "perception_nominalization",
            "universal_timed_burning",
            "quantifier_scope_ambiguity",
        }
        self.assertTrue(expected.issubset(rules))
        self.assertIn("Parameter Event : Type.", rules["passive_argument_omission"].forbidden_coq_fragments)
        self.assertIn("Parameter Agent :", rules["passive_argument_omission"].forbidden_coq_fragments)
        self.assertIn("Parameter Event : Type.", rules["lexical_state_change"].forbidden_coq_fragments)
        self.assertIn("Parameter Agent :", rules["lexical_state_change"].forbidden_coq_fragments)
        self.assertIn("Parameter Event : Type.", rules["stative_result_state"].forbidden_coq_fragments)
        self.assertIn("Parameter Agent :", rules["stative_result_state"].forbidden_coq_fragments)
        self.assertIn("Parameter Event : Type.", rules["timed_after"].forbidden_coq_fragments)
        self.assertIn("Parameter Event : Type.", rules["perception_nominalization"].forbidden_coq_fragments)
        self.assertIn("IN", rules["universal_timed_burning"].forbidden_coq_fragments)
        self.assertIn("Parameter Event : Type.", rules["quantifier_scope_ambiguity"].forbidden_coq_fragments)
        self.assertIn("Parameter some : Entity.", rules["quantifier_scope_ambiguity"].forbidden_coq_fragments)

    def test_registered_rule_outputs_do_not_contain_forbidden_coq_fragments(self) -> None:
        examples = {
            "passive_argument_omission": "the toast was buttered",
            "lexical_state_change": "the door opened",
            "stative_result_state": "the vase is broken",
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

    def test_web_api_and_page_expose_surface_lexicon_audits(self) -> None:
        passive = analyze_sentence("John was seen by Mary", require_coq=True)
        self.assertTrue(passive["ok"])
        self.assertEqual(
            passive["ast"]["surface_lexicon"],
            {
                "participle": "seen",
                "lemma": "see",
                "source": "translator/surface_lexicon.py",
            },
        )

        state_change = analyze_sentence("the water froze", require_coq=True)
        self.assertTrue(state_change["ok"])
        self.assertEqual(
            state_change["ast"]["surface_lexicon"],
            {
                "surface_verb": "froze",
                "lemma": "freeze",
                "source": "translator/surface_lexicon.py",
            },
        )

        passive_page = render_page("John was seen by Mary", require_coq=True)
        self.assertIn("&quot;participle&quot;: &quot;seen&quot;", passive_page)
        self.assertIn("&quot;lemma&quot;: &quot;see&quot;", passive_page)
        self.assertIn("translator/surface_lexicon.py", passive_page)

        state_page = render_page("the water froze", require_coq=True)
        self.assertIn("&quot;surface_verb&quot;: &quot;froze&quot;", state_page)
        self.assertIn("&quot;lemma&quot;: &quot;freeze&quot;", state_page)
        self.assertIn("translator/surface_lexicon.py", state_page)

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
        self.assertEqual(result["schema_version"], ANALYZE_RESPONSE_SCHEMA)
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
        self.assertFalse(result["diagnostics"]["manual_repair_required"])
        self.assertEqual(result["diagnostics"]["lexicon_patch_draft_count"], 0)
        self.assertEqual(result["lexicon_patch_drafts"], [])

    def test_api_analyze_response_contract_for_modifier_audit(self) -> None:
        handler = object.__new__(PipelineHandler)
        result = PipelineHandler.handle_api(
            handler,
            "sentence=john+buttered+the+toast+in+the+bathroom+with+a+knife&require_coq=1",
        )
        self.assertEqual(result["schema_version"], ANALYZE_RESPONSE_SCHEMA)
        self.assertTrue(result["ok"])
        self.assertIsInstance(result["event_semantics"], dict)
        self.assertIsInstance(result["ast"], dict)
        self.assertEqual(result["type_check"]["ok"], True)
        self.assertEqual(result["type_check"]["errors"], [])
        self.assertEqual(result["coq_check"]["status"], "passed")
        self.assertEqual(result["diagnostics"]["stages"]["type_check"], "passed")
        self.assertEqual(
            result["modifier_role_audit"],
            [
                {
                    "path": "ast",
                    "function": "butter",
                    "modifier": "in(bathroom)",
                    "type": "Adv",
                    "semantic_role": "Location",
                    "source": "modifier",
                    "surface_lexicon": modifier_surface_audit(
                        "in(bathroom)", "Adv", "Location"
                    ),
                },
                {
                    "path": "ast",
                    "function": "butter",
                    "modifier": "with(knife)",
                    "type": "Adv",
                    "semantic_role": "Instrument",
                    "source": "modifier",
                    "surface_lexicon": modifier_surface_audit(
                        "with(knife)", "Adv", "Instrument"
                    ),
                },
            ],
        )
        for audit in result["modifier_role_audit"]:
            self.assertEqual(
                set(audit["surface_lexicon"]),
                {
                    "surface_modifier",
                    "normalized_modifier",
                    "type",
                    "semantic_role",
                    "source",
                },
            )
            self.assertEqual(audit["type"], "Adv")
            self.assertEqual(audit["surface_lexicon"]["type"], "Adv")
            self.assertEqual(
                audit["surface_lexicon"]["semantic_role"],
                audit["semantic_role"],
            )

    def test_api_analyze_response_contains_result_state_warnings(self) -> None:
        handler = object.__new__(PipelineHandler)
        result = PipelineHandler.handle_api(
            handler,
            "sentence=Mary+painted+the+door+red&require_coq=1",
        )
        self.assertEqual(result["schema_version"], ANALYZE_RESPONSE_SCHEMA)
        self.assertTrue(result["ok"])
        self.assertEqual(result["diagnostics"]["summary"], "translation verified")
        self.assertIsNone(result["diagnostics"]["failure_stage"])
        self.assertEqual(
            result["diagnostics"]["warnings"],
            [
                {
                    "kind": "unknown_result_source",
                    "state": "red",
                    "scale": "color_scale",
                    "message": (
                        "Result state red has no unique lexical pre-state; "
                        "source remains unknown_state."
                    ),
                    "suggested_action": {
                        "kind": "add_state_prestate",
                        "label": "Add lexical pre-state",
                        "detail": (
                            "Choose a contextually justified source state for red on "
                            "color_scale, or keep unknown_state when the source is "
                            "genuinely underspecified."
                        ),
                        "lexicon_entry_draft": {
                            "draft_id": "state-red--unknown_source_allowed",
                            "state": "red",
                            "scale": "color_scale",
                            "default_source_state": "<choose_source_state>",
                            "allow_unknown_source": False,
                            "current_source_policy": "unknown_source_allowed",
                            "source_policy_after_update": "lexical_prestate",
                            "requires_human_choice": True,
                            "placeholder_fields": ["default_source_state"],
                            "can_auto_apply": False,
                            "state_lexicon_patch_line": (
                                "'red': StateLexiconEntry('color_scale', "
                                "default_source_state='<choose_source_state>'),"
                            ),
                        },
                    },
                }
            ],
        )
        self.assertEqual(
            result["lexicon_patch_drafts"],
            [
                {
                    "draft_id": "state-red--unknown_source_allowed",
                    "state": "red",
                    "scale": "color_scale",
                    "default_source_state": "<choose_source_state>",
                    "allow_unknown_source": False,
                    "current_source_policy": "unknown_source_allowed",
                    "source_policy_after_update": "lexical_prestate",
                    "requires_human_choice": True,
                    "placeholder_fields": ["default_source_state"],
                    "can_auto_apply": False,
                    "state_lexicon_patch_line": (
                        "'red': StateLexiconEntry('color_scale', "
                        "default_source_state='<choose_source_state>'),"
                    ),
                }
            ],
        )
        self.assertTrue(result["diagnostics"]["manual_repair_required"])
        self.assertEqual(result["diagnostics"]["lexicon_patch_draft_count"], 1)
        self.assertEqual(
            result["result_state_lexicon"][0]["source_policy"],
            "unknown_source_allowed",
        )
        self.assertIn("# Pending human choices:", result["patch_text_preview"])
        self.assertIn("# placeholders: default_source_state", result["patch_text_preview"])
        self.assertIn("unknown_state", result["coq_code"])

    def test_export_lexicon_patch_drafts_bundle(self) -> None:
        bundle = build_patch_bundle("Mary painted the door red", require_coq=True)
        self.assertEqual(bundle["schema_version"], "lexicon_patch_drafts.v1")
        self.assertTrue(bundle["ok"])
        self.assertEqual(bundle["input_sentence"], "Mary painted the door red")
        self.assertTrue(bundle["diagnostics"]["manual_repair_required"])
        self.assertEqual(bundle["diagnostics"]["lexicon_patch_draft_count"], 1)
        self.assertTrue(bundle["requires_human_choice"])
        self.assertFalse(bundle["can_auto_apply"])
        self.assertEqual(
            bundle["lexicon_patch_drafts"][0]["draft_id"],
            "state-red--unknown_source_allowed",
        )
        self.assertIn(
            "StateLexiconEntry",
            bundle["lexicon_patch_drafts"][0]["state_lexicon_patch_line"],
        )
        self.assertIn("# Pending human choices:", bundle["patch_text_preview"])
        self.assertIn("# draft_id: state-red--unknown_source_allowed", bundle["patch_text_preview"])
        self.assertIn("default_source_state='<choose_source_state>'", bundle["patch_text_preview"])

        empty_bundle = build_patch_bundle("John hammered the metal flat", require_coq=True)
        self.assertTrue(empty_bundle["ok"])
        self.assertFalse(empty_bundle["diagnostics"]["manual_repair_required"])
        self.assertEqual(empty_bundle["diagnostics"]["lexicon_patch_draft_count"], 0)
        self.assertFalse(empty_bundle["requires_human_choice"])
        self.assertFalse(empty_bundle["can_auto_apply"])
        self.assertEqual(empty_bundle["lexicon_patch_drafts"], [])

        resolved_bundle = build_patch_bundle(
            "Mary painted the door red",
            require_coq=True,
            resolution_items=["state-red--unknown_source_allowed=not_red"],
        )
        self.assertTrue(resolved_bundle["ok"])
        self.assertFalse(resolved_bundle["requires_human_choice"])
        self.assertTrue(resolved_bundle["can_auto_apply"])
        self.assertEqual(resolved_bundle["resolved_patch_count"], 1)
        self.assertEqual(resolved_bundle["validation_errors"], [])
        self.assertIn(
            '"red": StateLexiconEntry("color_scale", default_source_state="not_red"),',
            resolved_bundle["patch_text_preview"],
        )
        self.assertEqual(
            resolved_bundle["lexicon_patch_drafts"][0]["default_source_state"],
            "not_red",
        )
        self.assertEqual(resolved_bundle["lexicon_patch_drafts"][0]["placeholder_fields"], [])
        self.assertIn(
            "default_source_state='not_red'",
            resolved_bundle["lexicon_patch_drafts"][0]["state_lexicon_patch_line"],
        )
        patch_text = render_lexicon_patch_text(resolved_bundle)
        self.assertIn("# Candidate STATE_LEXICON patch", patch_text)
        self.assertIn("# Review before applying. This file is not applied automatically.", patch_text)
        self.assertIn(
            '"red": StateLexiconEntry("color_scale", default_source_state="not_red"),',
            patch_text,
        )

        structured_resolved_bundle = build_patch_bundle(
            "Mary painted the door red",
            require_coq=True,
            resolve_draft_ids=["state-red--unknown_source_allowed"],
            source_states=["not_red"],
        )
        self.assertTrue(structured_resolved_bundle["can_auto_apply"])
        self.assertEqual(structured_resolved_bundle["validation_errors"], [])
        self.assertEqual(structured_resolved_bundle["resolved_patch_count"], 1)
        self.assertEqual(
            structured_resolved_bundle["lexicon_patch_drafts"][0]["default_source_state"],
            "not_red",
        )

        mismatched_structured_bundle = build_patch_bundle(
            "Mary painted the door red",
            require_coq=True,
            resolve_draft_ids=["state-red--unknown_source_allowed"],
            source_states=[],
        )
        self.assertFalse(mismatched_structured_bundle["can_auto_apply"])
        self.assertIn(
            "resolve_draft_id and source_state counts differ",
            mismatched_structured_bundle["validation_errors"][0],
        )

        invalid_bundle = build_patch_bundle(
            "Mary painted the door red",
            require_coq=True,
            resolution_items=["state-red--unknown_source_allowed=intact"],
        )
        self.assertFalse(invalid_bundle["can_auto_apply"])
        self.assertTrue(invalid_bundle["requires_human_choice"])
        self.assertIn("expected 'color_scale'", invalid_bundle["validation_errors"][0])
        self.assertIn("# Validation errors:", invalid_bundle["patch_text_preview"])
        self.assertIn("# No auto-applicable patch lines.", invalid_bundle["patch_text_preview"])
        self.assertIn("# Pending human choices:", invalid_bundle["patch_text_preview"])
        invalid_patch_text = render_lexicon_patch_text(invalid_bundle)
        self.assertIn("# Validation errors:", invalid_patch_text)
        self.assertIn("# No auto-applicable patch lines.", invalid_patch_text)
        self.assertIn("# Pending human choices:", invalid_patch_text)

    def test_export_lexicon_patch_drafts_creates_output_parent_dirs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "nested" / "review" / "patch.txt"
            write_output_file(output_path, "candidate patch\n")
            self.assertEqual(output_path.read_text(encoding="utf-8"), "candidate patch\n")

    def test_api_lexicon_patch_drafts_endpoint(self) -> None:
        handler = object.__new__(PipelineHandler)
        bundle = PipelineHandler.handle_patch_api(
            handler,
            "sentence=Mary+painted+the+door+red&require_coq=1",
        )
        self.assertEqual(bundle["schema_version"], "lexicon_patch_drafts.v1")
        self.assertTrue(bundle["ok"])
        self.assertTrue(bundle["requires_human_choice"])
        self.assertFalse(bundle["can_auto_apply"])
        self.assertEqual(bundle["diagnostics"]["lexicon_patch_draft_count"], 1)
        self.assertEqual(
            bundle["lexicon_patch_drafts"][0]["draft_id"],
            "state-red--unknown_source_allowed",
        )

        resolved_bundle = PipelineHandler.handle_patch_api(
            handler,
            (
                "sentence=Mary+painted+the+door+red&require_coq=1"
                "&resolve=state-red--unknown_source_allowed=not_red"
            ),
        )
        self.assertTrue(resolved_bundle["can_auto_apply"])
        self.assertEqual(resolved_bundle["resolved_patch_count"], 1)
        self.assertEqual(resolved_bundle["validation_errors"], [])
        self.assertIn(
            '"red": StateLexiconEntry("color_scale", default_source_state="not_red"),',
            resolved_bundle["patch_text_preview"],
        )
        self.assertEqual(
            resolved_bundle["lexicon_patch_drafts"][0]["default_source_state"],
            "not_red",
        )

        structured_bundle = PipelineHandler.handle_patch_api(
            handler,
            (
                "sentence=Mary+painted+the+door+red&require_coq=1"
                "&resolve_draft_id=state-red--unknown_source_allowed"
                "&source_state=not_red"
            ),
        )
        self.assertTrue(structured_bundle["can_auto_apply"])
        self.assertEqual(structured_bundle["validation_errors"], [])
        self.assertEqual(
            structured_bundle["lexicon_patch_drafts"][0]["default_source_state"],
            "not_red",
        )

        no_draft_bundle = PipelineHandler.handle_patch_api(
            handler,
            "sentence=John+hammered+the+metal+flat&require_coq=1",
        )
        self.assertTrue(no_draft_bundle["ok"])
        self.assertFalse(no_draft_bundle["requires_human_choice"])
        self.assertEqual(no_draft_bundle["lexicon_patch_drafts"], [])

    def test_api_lexicon_patch_drafts_patch_format(self) -> None:
        handler = object.__new__(PipelineHandler)
        pending_text = PipelineHandler.handle_patch_text_api(
            handler,
            "sentence=Mary+painted+the+door+red&require_coq=1&format=patch",
        )
        self.assertIn("# Candidate STATE_LEXICON patch", pending_text)
        self.assertIn("# Pending human choices:", pending_text)
        self.assertIn("# placeholders: default_source_state", pending_text)

        resolved_text = PipelineHandler.handle_patch_text_api(
            handler,
            (
                "sentence=Mary+painted+the+door+red&require_coq=1&format=patch"
                "&resolve=state-red--unknown_source_allowed=not_red"
            ),
        )
        self.assertIn("# Candidate replacement/addition lines:", resolved_text)
        self.assertIn(
            '"red": StateLexiconEntry("color_scale", default_source_state="not_red"),',
            resolved_text,
        )

        structured_resolved_text = PipelineHandler.handle_patch_text_api(
            handler,
            (
                "sentence=Mary+painted+the+door+red&require_coq=1&format=patch"
                "&resolve_draft_id=state-red--unknown_source_allowed"
                "&source_state=not_red"
            ),
        )
        self.assertIn(
            '"red": StateLexiconEntry("color_scale", default_source_state="not_red"),',
            structured_resolved_text,
        )

    def test_api_lexicon_patch_drafts_rejects_mismatched_structured_resolution(self) -> None:
        resolutions, errors = parse_patch_resolution_params(
            {
                "resolve_draft_id": ["state-red--unknown_source_allowed"],
                "source_state": [],
            }
        )
        self.assertEqual(resolutions, {})
        self.assertIn("resolve_draft_id and source_state counts differ", errors[0])

    def test_api_lexicon_patch_drafts_rejects_conflicting_resolution_values(self) -> None:
        resolutions, errors = parse_patch_resolution_params(
            {
                "resolve": ["state-red--unknown_source_allowed=not_red"],
                "resolve_draft_id": ["state-red--unknown_source_allowed"],
                "source_state": ["dry"],
            }
        )
        self.assertEqual(resolutions, {"state-red--unknown_source_allowed": "not_red"})
        self.assertIn("Conflicting resolution", errors[0])
        self.assertIn("not_red", errors[0])
        self.assertIn("dry", errors[0])

        handler = object.__new__(PipelineHandler)
        bundle = PipelineHandler.handle_patch_api(
            handler,
            (
                "sentence=Mary+painted+the+door+red&require_coq=1"
                "&resolve=state-red--unknown_source_allowed=not_red"
                "&resolve_draft_id=state-red--unknown_source_allowed"
                "&source_state=dry"
            ),
        )
        self.assertFalse(bundle["can_auto_apply"])
        self.assertFalse(bundle["requires_human_choice"])
        self.assertIn("Conflicting resolution", bundle["validation_errors"][0])
        self.assertIn("# No auto-applicable patch lines.", bundle["patch_text_preview"])
        self.assertIn(
            "# Resolve validation errors before copying any candidate line.",
            bundle["patch_text_preview"],
        )
        self.assertNotIn(
            '"red": StateLexiconEntry("color_scale", default_source_state="not_red"),',
            bundle["patch_text_preview"],
        )

    def test_api_analyze_response_reports_empty_input(self) -> None:
        handler = object.__new__(PipelineHandler)
        result = PipelineHandler.handle_api(handler, "sentence=%20%20&require_coq=1")
        self.assertEqual(result["schema_version"], ANALYZE_RESPONSE_SCHEMA)
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
        self.assertIn("API Contract", page)
        self.assertIn("&quot;schema_version&quot;: &quot;analyze.v1&quot;", page)
        self.assertIn("&quot;endpoint&quot;: &quot;/api/analyze&quot;", page)
        self.assertIn("Conclusion", page)
        self.assertIn("Translation succeeded.", page)
        self.assertIn("Semantic Warnings", page)
        self.assertIn("No semantic warnings.", page)
        self.assertIn("Lexicon Patch Drafts", page)
        self.assertIn("No lexicon patch drafts.", page)
        self.assertIn("Next Steps", page)
        self.assertIn("No recovery actions needed.", page)
        self.assertIn("Construction Rule", page)
        self.assertIn("Type Check", page)
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

        warning_page = render_page("Mary painted the door red", require_coq=True)
        self.assertIn("red", warning_page)
        self.assertIn("color_scale", warning_page)
        self.assertIn("unknown_source_allowed", warning_page)
        self.assertIn("source remains unknown_state", warning_page)
        self.assertIn("lexicon-entry--warning", warning_page)
        self.assertIn("Translation verified with warnings", warning_page)
        self.assertIn("Warnings: Result state red has no unique lexical pre-state", warning_page)
        self.assertIn("Manual lexicon repair drafts: 1.", warning_page)
        self.assertIn("Semantic Warnings", warning_page)
        self.assertIn('class="semantic-warning semantic-warning--unknown_result_source"', warning_page)
        self.assertIn('data-warning-kind="unknown_result_source"', warning_page)
        self.assertIn('data-warning-action-kind="add_state_prestate"', warning_page)
        self.assertIn("<strong>Add lexical pre-state</strong>", warning_page)
        self.assertIn("<dt>state</dt><dd>red</dd>", warning_page)
        self.assertIn("<dt>draft source</dt><dd>&lt;choose_source_state&gt;</dd>", warning_page)
        self.assertIn("<dt>after policy</dt><dd>lexical_prestate</dd>", warning_page)
        self.assertIn("Lexicon Patch Drafts", warning_page)
        self.assertIn(
            'class="lexicon-draft" data-draft-id="state-red--unknown_source_allowed" '
            'data-draft-state="red"',
            warning_page,
        )
        self.assertIn("<dt>current</dt><dd>unknown_source_allowed</dd>", warning_page)
        self.assertIn("<dt>auto apply</dt><dd>no</dd>", warning_page)
        self.assertIn("<dt>placeholders</dt><dd>default_source_state</dd>", warning_page)
        self.assertIn(
            "<dt>entry</dt><dd>&#x27;red&#x27;: StateLexiconEntry(&#x27;color_scale&#x27;, "
            "default_source_state=&#x27;&lt;choose_source_state&gt;&#x27;),</dd>",
            warning_page,
        )
        self.assertIn(
            (
                '<form class="lexicon-resolve-form" method="get" '
                'action="/api/lexicon-patch-drafts" '
                'data-resolve-draft-id="state-red--unknown_source_allowed">'
            ),
            warning_page,
        )
        self.assertIn('name="resolve_draft_id" value="state-red--unknown_source_allowed"', warning_page)
        self.assertIn('name="source_state" type="text"', warning_page)
        self.assertIn('name="format" value="patch"', warning_page)
        self.assertIn('name="require_coq" value="1"', warning_page)
        self.assertIn("Preview resolved patch", warning_page)
        self.assertIn("Lexicon Patch Drafts JSON", warning_page)
        self.assertIn("Lexicon Patch Text Preview", warning_page)
        self.assertIn("# Pending human choices:", warning_page)
        self.assertIn("# placeholders: default_source_state", warning_page)
        self.assertIn('data-patch-format="text"', warning_page)
        self.assertIn('download="state_lexicon.patch"', warning_page)
        self.assertIn(
            (
                'href="/api/lexicon-patch-drafts?sentence=Mary+painted+the+door+red'
                '&amp;format=patch&amp;require_coq=1"'
            ),
            warning_page,
        )

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

    def test_web_result_state_warnings_cover_nonlexical_source_policies(self) -> None:
        derived_entry = state_lexicon_metadata("cerulean")
        source_only_entry = state_lexicon_metadata("intact")
        lexical_entry = state_lexicon_metadata("broken")

        self.assertEqual(derived_entry["source_policy"], "derived_scale_no_known_prestate")
        self.assertEqual(source_only_entry["source_policy"], "source_state_only")
        self.assertEqual(lexical_entry["source_policy"], "lexical_prestate")

        self.assertEqual(
            result_state_warning_for_entry(derived_entry),
            {
                "kind": "derived_result_scale",
                "state": "cerulean",
                "scale": "cerulean_scale",
                "message": (
                    "Result state cerulean uses a derived scale without a known lexical "
                    "pre-state; source remains unknown_state."
                ),
                "suggested_action": {
                    "kind": "register_state_lexicon_entry",
                    "label": "Register result state",
                    "detail": (
                        "Add cerulean to STATE_LEXICON with a stable scale and, "
                        "if justified, a default_source_state."
                    ),
                    "lexicon_entry_draft": {
                        "draft_id": "state-cerulean--derived_scale_no_known_prestate",
                        "state": "cerulean",
                        "scale": "cerulean_scale",
                        "default_source_state": "<choose_source_state>",
                        "allow_unknown_source": False,
                        "current_source_policy": "derived_scale_no_known_prestate",
                        "source_policy_after_update": "lexical_prestate",
                        "requires_human_choice": True,
                        "placeholder_fields": ["default_source_state"],
                        "can_auto_apply": False,
                        "state_lexicon_patch_line": (
                            "'cerulean': StateLexiconEntry('cerulean_scale', "
                            "default_source_state='<choose_source_state>'),"
                        ),
                    },
                },
            },
        )
        self.assertEqual(
            result_state_warning_for_entry(source_only_entry),
            {
                "kind": "source_state_used_as_target",
                "state": "intact",
                "scale": "integrity_scale",
                "message": (
                    "Result state intact is currently licensed only as a source state; "
                    "source remains unknown_state."
                ),
                "suggested_action": {
                    "kind": "license_state_as_target",
                    "label": "License target state",
                    "detail": (
                        "Decide whether intact can be a result target on integrity_scale; "
                        "if so, add a default source state."
                    ),
                    "lexicon_entry_draft": {
                        "draft_id": "state-intact--source_state_only",
                        "state": "intact",
                        "scale": "integrity_scale",
                        "default_source_state": "<choose_source_state>",
                        "allow_unknown_source": False,
                        "current_source_policy": "source_state_only",
                        "source_policy_after_update": "lexical_prestate",
                        "requires_human_choice": True,
                        "placeholder_fields": ["default_source_state"],
                        "can_auto_apply": False,
                        "state_lexicon_patch_line": (
                            "'intact': StateLexiconEntry('integrity_scale', "
                            "default_source_state='<choose_source_state>'),"
                        ),
                    },
                },
            },
        )
        self.assertIsNone(result_state_warning_for_entry(lexical_entry))

        self.assertEqual(
            [
                warning["kind"]
                for warning in result_state_warnings(
                    {"result_state_lexicon": [derived_entry, source_only_entry, lexical_entry]}
                )
            ],
            ["derived_result_scale", "source_state_used_as_target"],
        )

        diagnostics = build_diagnostics(
            {
                "ok": True,
                "input_sentence": "synthetic result-state audit",
                "type_check": {"ok": True},
                "construction_hygiene": {"ok": True},
                "coq_check": {"ok": True},
                "result_state_lexicon": [derived_entry, source_only_entry, lexical_entry],
            }
        )
        self.assertEqual(diagnostics["summary"], "translation verified")
        self.assertIsNone(diagnostics["failure_stage"])
        self.assertEqual(
            [warning["kind"] for warning in diagnostics["warnings"]],
            ["derived_result_scale", "source_state_used_as_target"],
        )
        self.assertEqual(
            [warning["suggested_action"]["kind"] for warning in diagnostics["warnings"]],
            ["register_state_lexicon_entry", "license_state_as_target"],
        )
        self.assertTrue(diagnostics["manual_repair_required"])
        self.assertEqual(diagnostics["lexicon_patch_draft_count"], 2)
        self.assertEqual(
            [
                warning["suggested_action"]["lexicon_entry_draft"]["state"]
                for warning in diagnostics["warnings"]
            ],
            ["cerulean", "intact"],
        )

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

    def test_web_analyze_sentence_reports_unlicensed_state_change_frame(self) -> None:
        result = analyze_sentence("the plant killed", require_coq=True)
        self.assertFalse(result["ok"])
        self.assertEqual(result["kind"], "lexical_state_change")
        self.assertEqual(result["ast"]["frame"], "inchoative")
        self.assertIn(
            "state-change verb does not license the inchoative frame",
            result["type_check"]["errors"],
        )
        self.assertEqual(result["diagnostics"]["failure_stage"], "type_check")
        self.assertEqual(result["coq_check"]["status"], "skipped")

        page = render_page("the plant killed", require_coq=True)
        self.assertIn("Needs attention", page)
        self.assertIn("Failure stage: dependent-type checking.", page)
        self.assertIn("Type Check", page)
        self.assertIn("state-change verb does not license the inchoative frame", page)
        self.assertNotIn("No registered construction rule matched", page)

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
        self.assertIn("passive argument-omission slice", web_design)
        self.assertIn("`exists x_agent : Entity. butter(x_agent, toast)`", web_design)
        self.assertIn("`Event`, `Agent`, and `Theme` declarations", web_design)
        self.assertIn("finite passive auxiliaries", web_design)
        self.assertIn("Copular result-state clauses", web_design)
        self.assertIn("`holds_state(vase, integrity_scale, broken)`", web_design)
        self.assertIn("Lexical change-of-state verbs", web_design)
        self.assertIn("`Change(Transition(door, access_scale, closed, open))`", web_design)

    def test_docs_explain_web_diagnostics_summary(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        web_design = (ROOT / "docs" / "web_pipeline_design.md").read_text(encoding="utf-8")
        ast_docs = (ROOT / "docs" / "ast_intermediate_representation.md").read_text(
            encoding="utf-8"
        )
        self.assertIn('"summary": "translation verified"', readme)
        self.assertIn('"failure_stage": null', readme)
        self.assertIn('"recovery_hint": null', readme)
        self.assertIn('"recovery_actions": []', readme)
        self.assertIn('"warnings": []', readme)
        self.assertIn('"type_check": "passed"', readme)
        self.assertIn('"construction_hygiene": "passed"', readme)
        self.assertIn('"coq_check": "passed"', readme)
        self.assertIn("`diagnostics.failure_stage` distinguishes", readme)
        self.assertIn("`diagnostics.recovery_hint` gives a short next-step suggestion", readme)
        self.assertIn("`diagnostics.recovery_actions` exposes the same advice", readme)
        self.assertIn("`diagnostics.warnings` records non-fatal semantic audit notices", readme)
        self.assertIn("`Type Check` panel", readme)
        self.assertIn("`manual_repair_required`", readme)
        self.assertIn("`lexicon_patch_draft_count`", readme)
        self.assertIn("`Translation verified with warnings`", readme)
        self.assertIn("`modifier_role_audit`", readme)
        self.assertIn("`Modifier Role Audit` panel", readme)
        self.assertIn("`normalized_modifier`", readme)
        self.assertIn("`in_bathroom`", readme)
        self.assertIn("`with_knife`", readme)
        self.assertIn("`MODIFIER_ROLE_BY_PREDICATE`", readme)
        self.assertIn("`John went from home to school`", readme)
        self.assertIn("`from_home : Adv`", readme)
        self.assertIn("`to_school : Adv`", readme)
        self.assertIn("paths like `ast.body`", readme)
        self.assertIn("the toast was buttered by John", readme)
        self.assertIn("the doors were opened by John", readme)
        self.assertIn("John was seen by Mary", readme)
        self.assertIn("the vase is broken", readme)
        self.assertIn("holds_state(vase, integrity_scale, broken)", readme)
        self.assertIn("the vase was broken by John", readme)
        self.assertIn("the door opened", readme)
        self.assertIn("John opened the door with a key", readme)
        self.assertIn("the clothes dried", readme)
        self.assertIn("John dried the clothes with a towel", readme)
        self.assertIn("the water froze", readme)
        self.assertIn("Mary cleaned the room", readme)
        self.assertIn("the tank emptied", readme)
        self.assertIn("John filled the glass", readme)
        self.assertIn("John died", readme)
        self.assertIn("Mary killed the plant with poison", readme)
        self.assertIn("StateChangeVerbEntry", readme)
        self.assertIn("translator/state_change_lexicon.py", readme)
        self.assertIn("`surface_lexicon` audit object for the", readme)
        self.assertIn("`died`, `killed`, `dried`, and `froze`", readme)
        self.assertIn("state_change_verb_entry", readme)
        self.assertIn("explicit `frame`", readme)
        self.assertIn("Change(Transition(door, access_scale, closed, open))", readme)
        self.assertIn("Change(Transition(clothes, moisture_scale, wet, dry))", readme)
        self.assertIn("Change(Transition(water, phase_scale, liquid, frozen))", readme)
        self.assertIn("Change(Transition(john, life_scale, alive, dead))", readme)
        self.assertIn("Cause(mary, Transition(room, cleanliness_scale, dirty, clean))", readme)
        self.assertIn("CauseWithInstrument(mary, poison, Transition", readme)
        self.assertIn("CauseWithInstrument(john, key, Transition", readme)
        self.assertIn("exists x_agent : Entity. butter(x_agent, toast)", readme)
        self.assertIn("passive argument omission with an existential typed agent", readme)
        self.assertIn("the passive auxiliary (`is`, `was`, `are`, or `were`)", readme)
        self.assertIn("Irregular passive participles are normalized", readme)
        self.assertIn("translator/surface_lexicon.py", readme)
        self.assertIn("`surface_lexicon` audit object", readme)
        self.assertIn("stative_result_state", ast_docs)
        self.assertIn('"predicate": "holds_state"', ast_docs)
        self.assertIn("lexical_state_change", ast_docs)
        self.assertIn("CauseWithInstrument(causer, instrument, Transition(...))", ast_docs)
        self.assertIn("moisture_scale", ast_docs)
        self.assertIn("phase_scale", ast_docs)
        self.assertIn("cleanliness_scale", ast_docs)
        self.assertIn("content_scale", ast_docs)
        self.assertIn('"state_change_verb_entry"', ast_docs)
        self.assertIn("translator/state_change_lexicon.py", ast_docs)
        self.assertIn("translator/surface_lexicon.py", ast_docs)
        self.assertIn('"surface_verb": "opened"', ast_docs)
        self.assertIn("`died` or `froze`", ast_docs)
        self.assertIn('"surface_lexicon"', ast_docs)
        self.assertIn('"surface_modifier": "in(bathroom)"', ast_docs)
        self.assertIn('"normalized_modifier": "in_bathroom"', ast_docs)
        self.assertIn('"participle": "buttered"', ast_docs)
        self.assertIn('"lemma": "butter"', ast_docs)
        self.assertIn('"frame": "inchoative"', ast_docs)
        self.assertIn("causative `die` frame", ast_docs)
        self.assertIn("inchoative `kill` frame", ast_docs)
        self.assertIn("registered_verb_target_state_mismatch", ast_docs)
        self.assertIn("state_change_verb_entry", web_design)
        self.assertIn("translator/state_change_lexicon.py", web_design)
        self.assertIn("translator/surface_lexicon.py", web_design)
        self.assertIn("surface verb and selected lemma", web_design)
        self.assertIn("`surface_lexicon` audit object", web_design)
        self.assertIn("`normalized_modifier`", web_design)
        self.assertIn("`in_bathroom`", web_design)
        self.assertIn("`with_knife`", web_design)
        self.assertIn("AST `frame` field", web_design)
        self.assertIn("`the plant killed` is not accepted", web_design)
        self.assertIn("Type Check panel", web_design)
        self.assertIn("passive_argument_omission", ast_docs)
        self.assertIn('"auxiliary": "was"', ast_docs)
        self.assertIn('"source": "omitted_existential"', ast_docs)
        self.assertIn("`derived_scale_no_known_prestate`", readme)
        self.assertIn("`source_state_only`", readme)
        self.assertIn("`Semantic Warnings` panel", readme)
        self.assertIn("`data-warning-kind`", readme)
        self.assertIn("`suggested_action`", readme)
        self.assertIn("`add_state_prestate`", readme)
        self.assertIn("`lexicon_entry_draft`", readme)
        self.assertIn("`lexicon_patch_drafts`", readme)
        self.assertIn("`patch_text_preview`", readme)
        self.assertIn("`draft_id`", readme)
        self.assertIn("`source_policy_after_update`", readme)
        self.assertIn("`state_lexicon_patch_line`", readme)
        self.assertIn("`requires_human_choice`", readme)
        self.assertIn("`can_auto_apply`", readme)
        self.assertIn("scripts/export_lexicon_patch_drafts.py", readme)
        self.assertIn("--resolve-draft-id state-red--unknown_source_allowed", readme)
        self.assertIn("--source-state not_red", readme)
        self.assertIn("--resolve state-red--unknown_source_allowed=not_red", readme)
        self.assertIn("conflicting source-state choice", readme)
        self.assertIn("review patch text suppresses", readme)
        self.assertIn("candidate replacement lines until", readme)
        self.assertIn("--patch-out", readme)
        self.assertIn("`format=patch`", readme)
        self.assertIn("`resolved_patch_count`", readme)
        self.assertIn("`validation_errors`", readme)
        self.assertIn("`Lexicon Patch Text Preview` panel", readme)
        self.assertIn("`Open patch text` link", readme)
        self.assertIn("`resolve_draft_id`", readme)
        self.assertIn("`source_state`", readme)
        self.assertIn("pending human-choice lines", readme)
        self.assertIn("create missing parent directories", readme)
        self.assertIn("/api/lexicon-patch-drafts", readme)
        self.assertIn("separate `Next Steps`", readme)
        self.assertIn("stable `data-action-kind`", readme)
        self.assertIn("`next-step--<kind>` CSS class", readme)
        self.assertIn("python3 scripts/sync_paper_docx.py", readme)
        self.assertIn("python3 scripts/check_paper_docx_sync.py", readme)
        self.assertIn("smoke check for the lexicon patch exporter", readme)
        self.assertIn("`--require-docx`", readme)
        self.assertIn('python3 -m pip install ".[docx]"', readme)
        self.assertIn("python3 scripts/verify_project.py --skip-coq --require-docx", readme)
        self.assertIn("the compact diagnostics summary", web_design)
        self.assertIn("construction-specific hygiene", web_design)
        self.assertIn("`diagnostics.failure_stage` is the machine-readable failure locator", web_design)
        self.assertIn("`diagnostics.recovery_hint` is `null` on success", web_design)
        self.assertIn("`diagnostics.recovery_actions` is an array", web_design)
        self.assertIn("`diagnostics.warnings` is an array", web_design)
        self.assertIn("`manual_repair_required`", web_design)
        self.assertIn("`lexicon_patch_draft_count`", web_design)
        self.assertIn("`modifier_role_audit`", web_design)
        self.assertIn("`Modifier Role Audit` panel", web_design)
        self.assertIn("verified with warnings", web_design)
        self.assertIn("`derived_result_scale`", web_design)
        self.assertIn("`source_state_used_as_target`", web_design)
        self.assertIn("`kind`, `label`, and `detail` fields", web_design)
        self.assertIn("render the same actions in a `Next Steps` panel", web_design)
        self.assertIn("`data-action-kind`", web_design)
        self.assertIn("`next-step--<kind>`", web_design)
        self.assertIn("`Semantic Warnings` panel", web_design)
        self.assertIn("`data-warning-kind`", web_design)
        self.assertIn("`semantic-warning--<kind>`", web_design)
        self.assertIn("`suggested_action`", web_design)
        self.assertIn("`register_state_lexicon_entry`", web_design)
        self.assertIn("`license_state_as_target`", web_design)
        self.assertIn("`data-warning-action-kind`", web_design)
        self.assertIn("`lexicon_entry_draft`", web_design)
        self.assertIn("`lexicon_patch_drafts`", web_design)
        self.assertIn("`patch_text_preview`", web_design)
        self.assertIn("`draft_id`", web_design)
        self.assertIn("`current_source_policy`", web_design)
        self.assertIn("`data-draft-id`", web_design)
        self.assertIn("`state_lexicon_patch_line`", web_design)
        self.assertIn("`placeholder_fields`", web_design)
        self.assertIn("`can_auto_apply`", web_design)
        self.assertIn("scripts/export_lexicon_patch_drafts.py", web_design)
        self.assertIn("--resolve-draft-id state-red--unknown_source_allowed", web_design)
        self.assertIn("--source-state not_red", web_design)
        self.assertIn("--resolve state-red--unknown_source_allowed=not_red", web_design)
        self.assertIn("conflicting source-state choices", web_design)
        self.assertIn("suppresses candidate replacement", web_design)
        self.assertIn("--patch-out", web_design)
        self.assertIn("`format=patch`", web_design)
        self.assertIn("`text/plain`", web_design)
        self.assertIn("/api/lexicon-patch-drafts", web_design)
        self.assertIn("`lexicon_patch_drafts.v1`", web_design)
        self.assertIn("`resolved_patch_count`", web_design)
        self.assertIn("`validation_errors`", web_design)
        self.assertIn("`Lexicon Patch Text Preview`", web_design)
        self.assertIn("`Open patch text` link", web_design)
        self.assertIn('`data-patch-format="text"`', web_design)
        self.assertIn("`data-resolve-draft-id`", web_design)
        self.assertIn("`resolve_draft_id`", web_design)
        self.assertIn("`source_state`", web_design)
        self.assertIn("pending patch line as a comment", web_design)
        self.assertIn("create missing parent directories", web_design)
        self.assertIn("smoke check for this exporter", web_design)
        self.assertIn("one of `input`, `parsing`,", web_design)
        self.assertIn("`modifier_roles`", readme)
        self.assertIn("Instrument-like `Adv`", readme)
        self.assertIn("cannot be mislabeled as a", readme)
        self.assertIn("`modifier_roles`", ast_docs)
        self.assertIn('`semantic_role: "Location"`', ast_docs)
        self.assertIn('`semantic_role: "Instrument"`', ast_docs)
        self.assertIn("cannot be labeled as", ast_docs)
        self.assertIn("`surface_lexicon` audit", ast_docs)
        self.assertIn("`normalized_modifier` records", ast_docs)
        self.assertIn("`MODIFIER_ROLE_BY_PREDICATE`", ast_docs)
        self.assertIn("Location/Instrument/Source/Goal/Manner", ast_docs)
        self.assertIn("`from(home)` is a Source-like `Adv`", ast_docs)
        self.assertIn("`to(school)` is a Goal-like `Adv`", ast_docs)
        self.assertIn("`MODIFIER_ROLE_BY_PREDICATE` table", web_design)
        self.assertIn("`from(home)` normalizes", web_design)
        self.assertIn("`to(school)` normalizes", web_design)
        self.assertIn("nested path such as `ast.body`", web_design)
        self.assertIn("`derived_scale_no_known_prestate`", ast_docs)
        self.assertIn("`source_state_only`", ast_docs)

    def test_docs_explain_api_contract(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        web_design = (ROOT / "docs" / "web_pipeline_design.md").read_text(encoding="utf-8")
        self.assertIn("/api/analyze?sentence=Mary+saw+John+leave&require_coq=1", readme)
        self.assertIn("`sentence` parameter carries the natural-language input", readme)
        self.assertIn('`schema_version: "analyze.v1"`', readme)
        self.assertIn("`result_state_lexicon`", readme)
        self.assertIn("Result State Lexicon panel", readme)
        self.assertIn("`Conclusion` panel", readme)
        self.assertIn("`construction_rule`", readme)
        self.assertIn("## API Contract", web_design)
        self.assertIn("`sentence`: required natural-language input", web_design)
        self.assertIn("`require_coq`: optional flag", web_design)
        self.assertIn("`dependent_type_translation`", web_design)
        self.assertIn('`schema_version: "analyze.v1"`', web_design)
        self.assertIn("`result_state_lexicon`", web_design)
        self.assertIn("`source_policy`", web_design)
        self.assertIn("Result State Lexicon panel", web_design)
        self.assertIn("dedicated `Conclusion` panel", web_design)
        self.assertIn("`construction_hygiene`", web_design)
        self.assertIn("failure, it must still return `ok: false`", web_design)
        self.assertIn("The separate `failure_stage` field distinguishes", web_design)
        self.assertIn("The web status line should surface `recovery_hint` directly", web_design)
        self.assertIn("Machine clients should prefer `recovery_actions`", web_design)

    def test_python_packaging_limits_top_level_package_discovery(self) -> None:
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn("[tool.setuptools.packages.find]", pyproject)
        self.assertIn('include = ["translator*", "web*"]', pyproject)
        self.assertIn('license = "MIT"', pyproject)

if __name__ == "__main__":
    unittest.main()
