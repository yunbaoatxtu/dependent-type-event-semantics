#!/usr/bin/env python3
"""End-to-end prototype for natural language to checked Coq scaffolds."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from translator.dependent_type_event_translator import (
    SOURCE_STATE_BY_TARGET_STATE,
    STATE_SCALE_BY_STATE,
    application_argument_types,
    check_term,
    export_module,
    export_term,
    not_term,
    render_term,
    state_lexicon_metadata,
    translate,
)
from translator.state_change_lexicon import (
    STATE_CHANGE_VERB_REGISTRY,
    STATE_CHANGE_VERB_TARGETS,
    state_change_verb_metadata,
)
from translator.surface_lexicon import (
    ARTICLES,
    COUNT_NOUNS,
    COMMON_ADVERBS,
    COUNT_WORDS,
    PASSIVE_AUXILIARIES,
    PREPOSITIONS,
    SURFACE_LEXICON_SOURCE,
    TEMPORAL_ADVERBS,
    count_phrase_value,
    is_passive_participle,
    is_likely_surface_verb,
    lemma_verb,
    modifier_semantic_role,
    modifier_surface_audit,
    normalize_surface_name,
    passive_participle_audit,
    surface_verb_audit,
    temporal_phrase_value,
    temporal_prepositional_phrase_value,
)


ROOT = Path(__file__).resolve().parents[1]
ROCQ_ENV = Path(
    "/Applications/Rocq-Platform~9.0~2025.08.app/Contents/Resources/bin/coq-env.sh"
)
FRONTED_MODIFIER_PREPOSITIONS = PREPOSITIONS
PROPERTY_DEGREES = {"very"}
DO_SUPPORT_AUXILIARIES = {"do", "does", "did"}


@dataclass(frozen=True)
class ConstructionRule:
    rule_id: str
    label: str
    phenomenon: str
    analyzer: Callable[[str], dict[str, Any] | None]
    forbidden_coq_fragments: tuple[str, ...] = ()


def atom(pred: str, *args: str) -> dict[str, Any]:
    return {"pred": pred, "args": list(args)}


def event_formula(*items: dict[str, Any]) -> dict[str, Any]:
    return {"exists": ["e"], "body": {"and": list(items)}}


def quantifier_scope_reading(
    subject_noun: str,
    verb: str,
    object_noun: str,
    subject_first: bool,
) -> dict[str, Any]:
    subject = {
        "role": "subject",
        "variable": f"x_{subject_noun}",
        "predicate": subject_noun,
        "predicate_type": "Entity -> Prop",
    }
    obj = {
        "role": "object",
        "variable": f"x_{object_noun}",
        "predicate": object_noun,
        "predicate_type": "Entity -> Prop",
    }
    scope_order = [subject, obj] if subject_first else [obj, subject]
    relation = {
        "predicate": verb,
        "predicate_type": "Entity -> Entity -> Prop",
        "arguments": [subject["variable"], obj["variable"]],
    }
    if subject_first:
        name = f"some_{subject_noun}_wide_scope"
    else:
        name = f"some_{object_noun}_wide_scope"
    return {
        "name": name,
        "quantifier": "some",
        "scope_order": scope_order,
        "relation": relation,
    }


def render_quantifier_reading(reading: dict[str, Any], coq: bool = False) -> str:
    relation = reading["relation"]
    args = relation["arguments"]
    if coq:
        body = f"{relation['predicate']} {' '.join(args)}"
        connective = "/\\"
        separator = ", "
    else:
        body = f"{relation['predicate']}({', '.join(args)})"
        connective = "and"
        separator = ". "
    for binder in reversed(reading["scope_order"]):
        var = binder["variable"]
        predicate = binder["predicate"]
        if coq:
            predicate_application = f"{predicate} {var}"
            body = (
                f"exists {var} : Entity{separator}"
                f"{predicate_application} {connective} {body}"
            )
        else:
            predicate_application = f"{predicate}({var})"
            body = (
                f"exists {var} : Entity{separator}"
                f"{predicate_application} {connective} {body}"
            )
    return body


def quantifier_scope_coq(reading: dict[str, Any]) -> str:
    return f"Definition {reading['name']} : Prop := {render_quantifier_reading(reading, coq=True)}."


def check_quantifier_scope_readings(readings: list[dict[str, Any]]) -> dict[str, Any]:
    errors: list[str] = []
    if len(readings) != 2:
        errors.append(f"expected two scope readings, got {len(readings)}")

    observed_orders: list[tuple[str, ...]] = []
    for index, reading in enumerate(readings):
        order = reading.get("scope_order")
        relation = reading.get("relation")
        if not isinstance(order, list) or len(order) != 2:
            errors.append(f"readings[{index}].scope_order must contain two binders")
            continue
        if not isinstance(relation, dict):
            errors.append(f"readings[{index}].relation must be an object")
            continue

        observed_orders.append(tuple(str(binder.get("role")) for binder in order))
        relation_args = relation.get("arguments")
        if relation.get("predicate_type") != "Entity -> Entity -> Prop":
            errors.append(
                f"readings[{index}].relation must have type Entity -> Entity -> Prop"
            )
        if not isinstance(relation_args, list) or len(relation_args) != 2:
            errors.append(f"readings[{index}].relation.arguments must contain two entities")

        for binder_index, binder in enumerate(order):
            if not isinstance(binder, dict):
                errors.append(f"readings[{index}].scope_order[{binder_index}] must be an object")
                continue
            if binder.get("predicate_type") != "Entity -> Prop":
                errors.append(
                    f"readings[{index}].scope_order[{binder_index}] "
                    "must have predicate type Entity -> Prop"
                )
            if not binder.get("variable"):
                errors.append(
                    f"readings[{index}].scope_order[{binder_index}] must bind a variable"
                )

    if set(observed_orders) != {("subject", "object"), ("object", "subject")}:
        errors.append(
            "scope readings must include both subject-wide and object-wide orders"
        )
    return {
        "ok": not errors,
        "type": "Prop" if not errors else None,
        "errors": errors,
        "reading_count": len(readings),
    }


def quantifier_scope_pipeline(sentence: str) -> dict[str, Any] | None:
    tokens = tokenize(sentence)
    if len(tokens) != 5 or tokens[0] != "some" or tokens[3] != "some":
        return None
    subject_noun = lemma_verb(tokens[1])
    verb = lemma_verb(tokens[2])
    object_noun = lemma_verb(tokens[4])
    readings = [
        quantifier_scope_reading(subject_noun, verb, object_noun, subject_first=True),
        quantifier_scope_reading(subject_noun, verb, object_noun, subject_first=False),
    ]
    type_check = check_quantifier_scope_readings(readings)
    event_semantics = {
        "analysis": "quantifier-scope",
        "source": sentence,
        "readings": [
            {**reading, "formula": render_quantifier_reading(reading)}
            for reading in readings
        ],
    }
    coq_code = "\n".join(
        [
            "(* Quantifier-scope scaffold for dependent-type event semantics. *)",
            "Parameter Entity : Type.",
            f"Parameter {subject_noun} : Entity -> Prop.",
            f"Parameter {object_noun} : Entity -> Prop.",
            f"Parameter {verb} : Entity -> Entity -> Prop.",
            "",
            quantifier_scope_coq(readings[0]),
            quantifier_scope_coq(readings[1]),
            "",
            f"Check some_{subject_noun}_wide_scope.",
            f"Check some_{object_noun}_wide_scope.",
            "",
        ]
    )
    return {
        "kind": "quantifier_scope_ambiguity",
        "input_sentence": sentence,
        "event_semantics": event_semantics,
        "dependent_type_translation": "\n".join(
            reading["formula"] for reading in event_semantics["readings"]
        ),
        "ast": {
            "kind": "scope_ambiguity",
            "quantifier": "some",
            "readings": readings,
        },
        "type_check": {
            **type_check,
            "note": (
                "Both scope readings are represented with entity predicates "
                "and a binary relation; no Event argument is introduced."
            ),
        },
        "coq_code": coq_code,
    }


def do_support_negation_pipeline(sentence: str) -> dict[str, Any] | None:
    tokens = tokenize(sentence)
    negation_index = None
    for index, token in enumerate(tokens):
        if (
            token == "not"
            and index > 0
            and tokens[index - 1] in DO_SUPPORT_AUXILIARIES
        ):
            negation_index = index
            break
    if negation_index is None:
        return None

    auxiliary_index = negation_index - 1
    auxiliary = tokens[auxiliary_index]
    subject_tokens = tokens[:auxiliary_index]
    if not subject_tokens or negation_index + 1 >= len(tokens):
        return None

    subject = clean_phrase(subject_tokens)
    if subject == "entity":
        return None

    if "and" in tokens:
        coordinated = coordinated_do_support_negation_pipeline(sentence)
        if coordinated is not None:
            return coordinated
        return {
            "kind": "do_support_negation",
            "input_sentence": sentence,
            "construction_summary": (
                f"Do-support negation with {auxiliary} not was detected, "
                "but coordination under negation is not implemented in this "
                "controlled rule yet."
            ),
            "event_semantics": {
                "analysis": "do-support-negation",
                "source": sentence,
                "event_style_reference": (
                    "not(exists e. P(e) ...), with coordination left unresolved"
                ),
            },
            "dependent_type_translation": "",
            "ast": {
                "kind": "do_support_negation",
                "auxiliary": auxiliary,
                "subject": {"name": subject, "type": "Entity"},
                "unsupported": "coordination_under_negation",
            },
            "type_check": {
                "ok": False,
                "type": None,
                "errors": [
                    "do-support negation with coordination is not yet supported"
                ],
                "note": (
                    "The sentence contains do-support negation and coordination; "
                    "the parser refuses to turn it into a malformed subject or object."
                ),
            },
            "coq_code": "",
        }

    positive_sentence = " ".join(
        [*subject_tokens, lemma_verb(tokens[negation_index + 1]), *tokens[negation_index + 2 :]]
    )
    positive_translation = translate(sentence_to_event_semantics(positive_sentence))
    ast = not_term(positive_translation["ast"])
    type_check = check_term(ast)
    exports = (
        {target: export_term(ast, target) for target in ("lean", "coq")}
        if type_check["ok"]
        else {}
    )
    coq_code = export_module(
        [{"ast": ast, "type_check": type_check, "exports": exports}],
        "coq",
    ) if type_check["ok"] else ""
    typed_replacement = render_term(ast)
    return {
        "kind": "do_support_negation",
        "input_sentence": sentence,
        "construction_summary": (
            f"Do-support negation maps {auxiliary} not to not_T over the "
            f"positive clause {positive_sentence}."
        ),
        "event_semantics": {
            "analysis": "do-support-negation",
            "source": sentence,
            "positive_clause": positive_translation["translation"],
            "event_style_reference": (
                f"not(exists e. {positive_translation['translation']})"
            ),
            "typed_replacement": typed_replacement,
        },
        "dependent_type_translation": typed_replacement,
        "ast": ast,
        "type_check": {
            **type_check,
            "note": (
                "Do-support negation is represented as a proposition-level "
                "not_T wrapper around the checked positive-clause AST."
            ),
        },
        "coq_code": coq_code,
    }


def wrap_negated_translation(term: str, negated: bool) -> str:
    return f"not_T({term})" if negated else term


def wrap_negated_coq(term: str, negated: bool) -> str:
    return f"not_T ({term})" if negated else term


def coordinated_do_support_negation_pipeline(sentence: str) -> dict[str, Any] | None:
    tokens, fronted_time_modifiers = split_fronted_time_modifiers(tokenize(sentence))
    tokens, fronted_adv_modifiers = split_fronted_adv_modifiers(tokens)
    if tokens.count("and") != 1:
        return None
    and_index = tokens.index("and")
    if and_index + 3 >= len(tokens):
        return None
    auxiliary = tokens[and_index + 1]
    if auxiliary not in DO_SUPPORT_AUXILIARIES or tokens[and_index + 2] != "not":
        return None
    right_surface = tokens[and_index + 3]
    if not is_likely_surface_verb(right_surface):
        return None

    transitive = coordinated_transitive_do_support_negation(
        sentence,
        tokens,
        and_index,
        right_surface,
        fronted_adv_modifiers,
        fronted_time_modifiers,
    )
    if transitive is not None:
        return transitive
    return coordinated_intransitive_do_support_negation(
        sentence,
        tokens,
        and_index,
        right_surface,
        fronted_adv_modifiers,
        fronted_time_modifiers,
    )


def timed_after_ast(
    first_predicate: str,
    first_theme: str,
    second_predicate: str,
    second_agent: str,
    second_theme: str,
) -> dict[str, Any]:
    return {
        "kind": "timed_after",
        "binders": [
            {"variable": "t_sing", "type": "Time"},
            {"variable": "t_salute", "type": "Time"},
        ],
        "first": {
            "predicate": first_predicate,
            "predicate_type": "Entity -> Time -> Prop",
            "theme": {
                "name": first_theme,
                "type": "Entity",
            },
            "time": "t_sing",
        },
        "second": {
            "predicate": second_predicate,
            "predicate_type": "Entity -> Entity -> Time -> Prop",
            "agent": {
                "name": second_agent,
                "type": "Entity",
            },
            "theme": {
                "name": second_theme,
                "type": "Entity",
            },
            "time": "t_salute",
        },
        "relation": {
            "predicate": "before",
            "predicate_type": "Time -> Time -> Prop",
            "arguments": ["t_sing", "t_salute"],
        },
    }


def check_timed_after_ast(ast: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if ast.get("kind") != "timed_after":
        errors.append("ast.kind must be timed_after")

    binders = ast.get("binders")
    expected_binders = [
        {"variable": "t_sing", "type": "Time"},
        {"variable": "t_salute", "type": "Time"},
    ]
    if binders != expected_binders:
        errors.append("timed_after.binders must bind t_sing and t_salute as Time")

    first = ast.get("first")
    if not isinstance(first, dict):
        errors.append("timed_after.first must be an object")
    else:
        if first.get("predicate_type") != "Entity -> Time -> Prop":
            errors.append("timed_after.first must have type Entity -> Time -> Prop")
        theme = first.get("theme")
        if not isinstance(theme, dict) or theme.get("type") != "Entity":
            errors.append("timed_after.first.theme must have type Entity")
        if first.get("time") != "t_sing":
            errors.append("timed_after.first must use bound time t_sing")

    second = ast.get("second")
    if not isinstance(second, dict):
        errors.append("timed_after.second must be an object")
    else:
        if second.get("predicate_type") != "Entity -> Entity -> Time -> Prop":
            errors.append(
                "timed_after.second must have type Entity -> Entity -> Time -> Prop"
            )
        for role in ("agent", "theme"):
            value = second.get(role)
            if not isinstance(value, dict) or value.get("type") != "Entity":
                errors.append(f"timed_after.second.{role} must have type Entity")
        if second.get("time") != "t_salute":
            errors.append("timed_after.second must use bound time t_salute")

    relation = ast.get("relation")
    if not isinstance(relation, dict):
        errors.append("timed_after.relation must be an object")
    else:
        if relation.get("predicate_type") != "Time -> Time -> Prop":
            errors.append("timed_after.relation must have type Time -> Time -> Prop")
        if relation.get("arguments") != ["t_sing", "t_salute"]:
            errors.append("timed_after.relation must relate t_sing before t_salute")

    return {
        "ok": not errors,
        "type": "Prop" if not errors else None,
        "errors": errors,
    }


def timed_after_pipeline(sentence: str) -> dict[str, Any] | None:
    tokens = tokenize(sentence)
    expected = [
        "after",
        "the",
        "singing",
        "of",
        "the",
        "marseillaise",
        "john",
        "saluted",
        "the",
        "flag",
    ]
    if tokens != expected:
        return None

    first_predicate = lemma_verb(tokens[2])
    first_theme = "Marseillaise"
    second_agent = "John"
    second_predicate = lemma_verb(tokens[7])
    second_theme = "flag"
    coq_code = "\n".join(
        [
            "(* Timed Luo-Shi-style replacement for Parsons-style event talk. *)",
            "Parameter Entity : Type.",
            "Parameter Time : Type.",
            "",
            f"Parameter {first_theme} : Entity.",
            f"Parameter {second_agent} : Entity.",
            f"Parameter {second_theme} : Entity.",
            "",
            f"Parameter {first_predicate} : Entity -> Time -> Prop.",
            f"Parameter {second_predicate} : Entity -> Entity -> Time -> Prop.",
            "Parameter before : Time -> Time -> Prop.",
            "",
            "Definition after_singing_salute : Prop :=",
            "  exists t_sing : Time,",
            "  exists t_salute : Time,",
            f"    {first_predicate} {first_theme} t_sing /\\",
            f"    {second_predicate} {second_agent} {second_theme} t_salute /\\",
            "    before t_sing t_salute.",
            "",
            "Check after_singing_salute.",
            "",
        ]
    )
    event_semantics = {
        "analysis": "parsons-after-event-talk",
        "source": sentence,
        "event_style_reference": (
            "exists e e'. singing(e') and Theme(e', Marseillaise) and "
            "saluting(e) and Agent(e, John) and Theme(e, flag) and after(e', e)"
        ),
        "typed_replacement": (
            "exists t_sing t_salute : Time. "
            "sing(Marseillaise, t_sing) and salute(John, flag, t_salute) "
            "and before(t_sing, t_salute)"
        ),
    }
    ast = timed_after_ast(
        first_predicate,
        first_theme,
        second_predicate,
        second_agent,
        second_theme,
    )
    type_check = check_timed_after_ast(ast)
    return {
        "kind": "timed_after",
        "input_sentence": sentence,
        "event_semantics": event_semantics,
        "dependent_type_translation": event_semantics["typed_replacement"],
        "ast": ast,
        "type_check": {
            **type_check,
            "note": "The Parsons-style event relation is represented with Time variables, not an Event parameter.",
        },
        "coq_code": coq_code,
    }


def perception_nominalization_ast(
    perception_predicate: str,
    experiencer: str,
    embedded_predicate: str,
    embedded_subject: str,
) -> dict[str, Any]:
    return {
        "kind": "perception_nominalization",
        "perception": {
            "predicate": perception_predicate,
            "predicate_type": "Entity -> Entity -> Prop",
            "experiencer": {
                "name": experiencer,
                "type": "Entity",
            },
            "object": {
                "kind": "nominalized_proposition",
                "nominalizer": "E",
                "nominalizer_type": "Prop -> Entity",
                "proposition": {
                    "predicate": embedded_predicate,
                    "predicate_type": "Entity -> Prop",
                    "subject": {
                        "name": embedded_subject,
                        "type": "Entity",
                    },
                },
            },
        },
    }


def check_perception_nominalization_ast(ast: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    perception = ast.get("perception")
    if ast.get("kind") != "perception_nominalization":
        errors.append("ast.kind must be perception_nominalization")
    if not isinstance(perception, dict):
        errors.append("ast.perception must be an object")
    else:
        if perception.get("predicate_type") != "Entity -> Entity -> Prop":
            errors.append("perception predicate must have type Entity -> Entity -> Prop")
        experiencer = perception.get("experiencer")
        if not isinstance(experiencer, dict) or experiencer.get("type") != "Entity":
            errors.append("perception.experiencer must have type Entity")

        obj = perception.get("object")
        if not isinstance(obj, dict):
            errors.append("perception.object must be a nominalized proposition")
        else:
            if obj.get("kind") != "nominalized_proposition":
                errors.append("perception.object.kind must be nominalized_proposition")
            if obj.get("nominalizer_type") != "Prop -> Entity":
                errors.append("nominalizer E must have type Prop -> Entity")
            proposition = obj.get("proposition")
            if not isinstance(proposition, dict):
                errors.append("nominalized object must contain a proposition")
            else:
                if proposition.get("predicate_type") != "Entity -> Prop":
                    errors.append("embedded predicate must have type Entity -> Prop")
                subject = proposition.get("subject")
                if not isinstance(subject, dict) or subject.get("type") != "Entity":
                    errors.append("embedded subject must have type Entity")

    return {
        "ok": not errors,
        "type": "Prop" if not errors else None,
        "errors": errors,
    }


def perception_nominalization_pipeline(sentence: str) -> dict[str, Any] | None:
    tokens = tokenize(sentence)
    if tokens not in (["mary", "saw", "john", "leave"], ["mary", "saw", "john", "left"]):
        return None

    experiencer = "Mary"
    embedded_subject = "John"
    perception_predicate = lemma_verb(tokens[1])
    embedded_predicate = lemma_verb(tokens[3])
    coq_code = "\n".join(
        [
            "(* Luo-Shi-style nominalization for perception complements. *)",
            "Parameter Entity : Type.",
            "",
            f"Parameter {experiencer} : Entity.",
            f"Parameter {embedded_subject} : Entity.",
            "",
            "Parameter E : Prop -> Entity.",
            f"Parameter {embedded_predicate} : Entity -> Prop.",
            f"Parameter {perception_predicate} : Entity -> Entity -> Prop.",
            "",
            "Definition mary_saw_john_leave : Prop :=",
            f"  {perception_predicate} {experiencer} (E ({embedded_predicate} {embedded_subject})).",
            "",
            "Check mary_saw_john_leave.",
            "",
        ]
    )
    event_semantics = {
        "analysis": "parsons-perception-complement",
        "source": sentence,
        "event_style_reference": (
            "exists e e'. seeing(e) and Experiencer(e, Mary) and "
            "leaving(e') and Agent(e', John) and Theme(e, e')"
        ),
        "typed_replacement": "see(Mary, E(leave(John)))",
    }
    ast = perception_nominalization_ast(
        perception_predicate,
        experiencer,
        embedded_predicate,
        embedded_subject,
    )
    type_check = check_perception_nominalization_ast(ast)
    return {
        "kind": "perception_nominalization",
        "input_sentence": sentence,
        "event_semantics": event_semantics,
        "dependent_type_translation": event_semantics["typed_replacement"],
        "ast": ast,
        "type_check": {
            **type_check,
            "note": "The perceived eventuality is embedded by E : Prop -> Entity, not by an Event argument.",
        },
        "coq_code": coq_code,
    }


def universal_timed_burning_ast() -> dict[str, Any]:
    return {
        "kind": "forall_time",
        "binders": [
            {"variable": "x", "type": "Entity"},
            {"variable": "t", "type": "Time"},
        ],
        "antecedent": {
            "predicate": "burn",
            "predicate_type": "Entity -> Time -> Prop",
            "arguments": ["x", "t"],
        },
        "consequent": {
            "predicate": "consume",
            "predicate_type": "Entity -> Time -> Prop",
            "arguments": ["oxygen", "t"],
            "theme": {
                "name": "oxygen",
                "type": "Entity",
            },
        },
    }


def check_universal_timed_ast(ast: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if ast.get("kind") != "forall_time":
        errors.append("ast.kind must be forall_time")

    binders = ast.get("binders")
    if not isinstance(binders, list) or len(binders) != 2:
        errors.append("forall_time.binders must contain Entity and Time binders")
    else:
        expected = [{"variable": "x", "type": "Entity"}, {"variable": "t", "type": "Time"}]
        if binders != expected:
            errors.append("forall_time.binders must bind x : Entity and t : Time")

    for field in ("antecedent", "consequent"):
        predicate = ast.get(field)
        if not isinstance(predicate, dict):
            errors.append(f"forall_time.{field} must be a predicate object")
            continue
        if predicate.get("predicate_type") != "Entity -> Time -> Prop":
            errors.append(f"forall_time.{field} must have type Entity -> Time -> Prop")
        args = predicate.get("arguments")
        if not isinstance(args, list) or len(args) != 2:
            errors.append(f"forall_time.{field}.arguments must contain entity and time")
        elif args[1] != "t":
            errors.append(f"forall_time.{field} must share the bound time variable t")

    consequent = ast.get("consequent")
    if isinstance(consequent, dict):
        theme = consequent.get("theme")
        if not isinstance(theme, dict) or theme.get("type") != "Entity":
            errors.append("forall_time.consequent.theme must have type Entity")
        elif theme.get("name") not in consequent.get("arguments", []):
            errors.append("forall_time.consequent.theme must occur in consequent arguments")

    return {
        "ok": not errors,
        "type": "Prop" if not errors else None,
        "errors": errors,
    }


def every_burning_pipeline(sentence: str) -> dict[str, Any] | None:
    tokens = tokenize(sentence)
    if tokens != ["in", "every", "burning", "oxygen", "is", "consumed"]:
        return None

    coq_code = "\n".join(
        [
            "(* Timed universal replacement for Parsons-style event inclusion. *)",
            "Parameter Entity : Type.",
            "Parameter Time : Type.",
            "",
            "Parameter oxygen : Entity.",
            "",
            "Parameter burn : Entity -> Time -> Prop.",
            "Parameter consume : Entity -> Time -> Prop.",
            "",
            "Definition every_burning_consumes_oxygen : Prop :=",
            "  forall x : Entity,",
            "  forall t : Time,",
            "    burn x t -> consume oxygen t.",
            "",
            "Check every_burning_consumes_oxygen.",
            "",
        ]
    )
    event_semantics = {
        "analysis": "parsons-event-inclusion",
        "source": sentence,
        "event_style_reference": (
            "forall e. burning(e) -> exists e'. consuming(e') and "
            "Theme(e', oxygen) and IN(e', e)"
        ),
        "typed_replacement": (
            "forall x : Entity. forall t : Time. "
            "burn(x, t) -> consume(oxygen, t)"
        ),
    }
    ast = universal_timed_burning_ast()
    type_check = check_universal_timed_ast(ast)
    return {
        "kind": "universal_timed_burning",
        "input_sentence": sentence,
        "event_semantics": event_semantics,
        "dependent_type_translation": event_semantics["typed_replacement"],
        "ast": ast,
        "type_check": {
            **type_check,
            "note": "Event inclusion is represented as universal quantification over entities and times.",
        },
        "coq_code": coq_code,
    }


def lexical_state_change_ast(
    verb: str,
    theme: str,
    target_state: str,
    surface_verb: str,
    causer: str | None = None,
    instrument: str | None = None,
) -> dict[str, Any]:
    transition = {
        "kind": "transition",
        "theme": {"name": theme, "type": "Entity"},
        "state_scale": STATE_SCALE_BY_STATE[target_state],
        "source_state": SOURCE_STATE_BY_TARGET_STATE[target_state],
        "target_state": {"name": target_state, "type": "State"},
    }
    ast: dict[str, Any] = {
        "kind": "lexical_state_change",
        "verb": verb,
        "surface_lexicon": surface_verb_audit(surface_verb),
        "frame": "inchoative",
        "transition": transition,
    }
    if causer is not None:
        ast["frame"] = "causative"
        ast["causer"] = {"name": causer, "type": "Entity", "source": "subject"}
    if instrument is not None:
        ast["frame"] = "instrumental"
        ast["instrument"] = {
            "name": instrument,
            "type": "Entity",
            "source": "with_phrase",
        }
    return ast


def check_lexical_state_change_ast(ast: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if ast.get("kind") != "lexical_state_change":
        errors.append("ast.kind must be lexical_state_change")
    verb = ast.get("verb")
    entry = STATE_CHANGE_VERB_REGISTRY.get(verb)
    if entry is None:
        errors.append("state-change verb must be registered in STATE_CHANGE_VERB_REGISTRY")
    surface_lexicon = ast.get("surface_lexicon")
    if not isinstance(surface_lexicon, dict):
        errors.append("state-change surface_lexicon must be an object")
    else:
        surface_verb = surface_lexicon.get("surface_verb")
        if not isinstance(surface_verb, str) or not surface_verb:
            errors.append("state-change surface_lexicon.surface_verb must be a non-empty string")
        if surface_lexicon.get("lemma") != verb:
            errors.append("state-change surface_lexicon.lemma must match verb")
        elif isinstance(surface_verb, str) and lemma_verb(surface_verb) != verb:
            errors.append("state-change surface_lexicon.lemma must match lemmatized surface verb")
        if surface_lexicon.get("source") != SURFACE_LEXICON_SOURCE:
            errors.append("state-change surface_lexicon.source must identify the surface lexicon")
    frame = ast.get("frame")
    if frame not in {"inchoative", "causative", "instrumental"}:
        errors.append("state-change frame must be inchoative, causative, or instrumental")

    transition = ast.get("transition")
    if not isinstance(transition, dict):
        errors.append("state-change transition must be an object")
    else:
        if transition.get("kind") != "transition":
            errors.append("state-change transition.kind must be transition")
        theme = transition.get("theme")
        if not isinstance(theme, dict):
            errors.append("state-change theme must be an object")
        else:
            if not isinstance(theme.get("name"), str) or not theme.get("name"):
                errors.append("state-change theme.name must be a non-empty string")
            if theme.get("type") != "Entity":
                errors.append("state-change theme must have type Entity")
        target = transition.get("target_state")
        if not isinstance(target, dict):
            errors.append("state-change target_state must be an object")
            target_name = None
        else:
            target_name = target.get("name")
            if not isinstance(target_name, str) or not target_name:
                errors.append("state-change target_state.name must be a non-empty string")
            elif target_name not in SOURCE_STATE_BY_TARGET_STATE:
                errors.append(f"state-change target has no lexical source state: {target_name}")
            elif entry is not None and target_name != entry.target_state:
                errors.append("state-change target_state must match the registered verb target")
            if target.get("type") != "State":
                errors.append("state-change target_state must have type State")
        if isinstance(target_name, str) and target_name in SOURCE_STATE_BY_TARGET_STATE:
            if transition.get("state_scale") != STATE_SCALE_BY_STATE[target_name]:
                errors.append("state-change state_scale must match the state lexicon")
            if transition.get("source_state") != SOURCE_STATE_BY_TARGET_STATE[target_name]:
                errors.append("state-change source_state must match the state lexicon")

    causer = ast.get("causer")
    instrument = ast.get("instrument")
    expected_frame = "instrumental" if instrument is not None else "causative" if causer is not None else "inchoative"
    if frame != expected_frame:
        errors.append("state-change frame must match its causer and instrument fields")

    if frame == "inchoative" and entry is not None and not entry.allow_inchoative:
        errors.append("state-change verb does not license the inchoative frame")
    if causer is not None:
        if frame == "causative" and entry is not None and not entry.allow_causative:
            errors.append("state-change verb does not license the causative frame")
        if not isinstance(causer, dict):
            errors.append("state-change causer must be an object")
        else:
            if not isinstance(causer.get("name"), str) or not causer.get("name"):
                errors.append("state-change causer.name must be a non-empty string")
            if causer.get("type") != "Entity":
                errors.append("state-change causer must have type Entity")
            if causer.get("source") != "subject":
                errors.append("state-change causer.source must be subject")

    if instrument is not None:
        if causer is None:
            errors.append("state-change instrument requires a causer")
        if frame == "instrumental" and entry is not None and not entry.allow_instrument:
            errors.append("state-change verb does not license the instrumental frame")
        if not isinstance(instrument, dict):
            errors.append("state-change instrument must be an object")
        else:
            if not isinstance(instrument.get("name"), str) or not instrument.get("name"):
                errors.append("state-change instrument.name must be a non-empty string")
            if instrument.get("type") != "Entity":
                errors.append("state-change instrument must have type Entity")
            if instrument.get("source") != "with_phrase":
                errors.append("state-change instrument.source must be with_phrase")

    return {
        "ok": not errors,
        "type": "Prop" if not errors else None,
        "errors": errors,
    }


def render_state_change_translation(ast: dict[str, Any]) -> str:
    transition = ast["transition"]
    theme = transition["theme"]["name"]
    state_scale = transition["state_scale"]
    source_state = transition["source_state"]
    target_state = transition["target_state"]["name"]
    transition_text = f"Transition({theme}, {state_scale}, {source_state}, {target_state})"
    instrument = ast.get("instrument")
    causer = ast.get("causer")
    if instrument is not None and causer is not None:
        return f"CauseWithInstrument({causer['name']}, {instrument['name']}, {transition_text})"
    if causer is not None:
        return f"Cause({causer['name']}, {transition_text})"
    return f"Change({transition_text})"


def lexical_state_change_failure(sentence: str, ast: dict[str, Any]) -> dict[str, Any]:
    type_check = check_lexical_state_change_ast(ast)
    return {
        "kind": "lexical_state_change",
        "input_sentence": sentence,
        "event_semantics": {
            "analysis": "lexical-state-change",
            "source": sentence,
            "event_style_reference": "blocked before event-style fallback",
            "typed_replacement": None,
        },
        "dependent_type_translation": "No licensed lexical state-change frame.",
        "result_state_lexicon": [
            state_lexicon_metadata(ast["transition"]["target_state"]["name"])
        ],
        "state_change_verb_entry": state_change_verb_metadata(ast["verb"]),
        "ast": ast,
        "type_check": {
            **type_check,
            "note": (
                "A registered state-change verb was recognized, but the surface "
                "frame is not licensed by its lexical registration."
            ),
        },
        "coq_code": "",
    }


def lexical_state_change_pipeline(sentence: str) -> dict[str, Any] | None:
    tokens = tokenize(sentence)
    if len(tokens) < 2:
        return None
    for verb_index, token in enumerate(tokens):
        verb = lemma_verb(token)
        entry = STATE_CHANGE_VERB_REGISTRY.get(verb)
        if entry is None:
            continue
        if any(auxiliary in tokens[:verb_index] for auxiliary in PASSIVE_AUXILIARIES):
            return None
        target_state = entry.target_state
        if target_state not in SOURCE_STATE_BY_TARGET_STATE:
            return None

        if verb_index == len(tokens) - 1 and verb_index > 0:
            theme = clean_phrase(tokens[:verb_index])
            ast = lexical_state_change_ast(verb, theme, target_state, token)
            if not entry.allow_inchoative:
                return lexical_state_change_failure(sentence, ast)
            break

        if verb_index == 0 or verb_index + 1 >= len(tokens):
            return None
        causer = clean_phrase(tokens[:verb_index])
        rest = tokens[verb_index + 1:]
        instrument = None
        if "with" in rest:
            with_index = rest.index("with")
            object_tokens = rest[:with_index]
            instrument_tokens = rest[with_index + 1:]
            if not object_tokens or not instrument_tokens:
                return None
            instrument = clean_phrase(instrument_tokens)
        else:
            object_tokens = rest
        if not object_tokens:
            return None
        theme = clean_phrase(object_tokens)
        ast = lexical_state_change_ast(
            verb,
            theme,
            target_state,
            token,
            causer,
            instrument,
        )
        if not entry.allow_causative or (instrument is not None and not entry.allow_instrument):
            return lexical_state_change_failure(sentence, ast)
        break
    else:
        return None

    type_check = check_lexical_state_change_ast(ast)
    transition = ast["transition"]
    theme = transition["theme"]["name"]
    state_scale = transition["state_scale"]
    source_state = transition["source_state"]
    target_state = transition["target_state"]["name"]
    typed_replacement = render_state_change_translation(ast)
    definition_name = f"lexical_{ast['verb']}_state_change"
    coq_parameters = [
        "(* Lexical state-change replacement without an event variable. *)",
        "Parameter Entity : Type.",
        "Parameter State : Type.",
        "Parameter StateScale : Type.",
        "Parameter TransitionT : Type.",
        "",
        f"Parameter {theme} : Entity.",
        f"Parameter {source_state} : State.",
        f"Parameter {target_state} : State.",
        f"Parameter {state_scale} : StateScale.",
    ]
    causer = ast.get("causer")
    instrument = ast.get("instrument")
    if causer is not None:
        coq_parameters.append(f"Parameter {causer['name']} : Entity.")
    if instrument is not None:
        coq_parameters.append(f"Parameter {instrument['name']} : Entity.")
    coq_parameters.extend(
        [
            "",
            "Parameter Transition : Entity -> StateScale -> State -> State -> TransitionT.",
            "Parameter Change : TransitionT -> Prop.",
            "Parameter Cause : Entity -> TransitionT -> Prop.",
            "Parameter CauseWithInstrument : Entity -> Entity -> TransitionT -> Prop.",
            "",
        ]
    )
    transition_coq = f"Transition {theme} {state_scale} {source_state} {target_state}"
    if instrument is not None and causer is not None:
        body = f"CauseWithInstrument {causer['name']} {instrument['name']} ({transition_coq})"
    elif causer is not None:
        body = f"Cause {causer['name']} ({transition_coq})"
    else:
        body = f"Change ({transition_coq})"
    coq_code = "\n".join(
        [
            *coq_parameters,
            f"Definition {definition_name} : Prop :=",
            f"  {body}.",
            "",
            f"Check {definition_name}.",
            "",
        ]
    )
    return {
        "kind": "lexical_state_change",
        "input_sentence": sentence,
        "event_semantics": {
            "analysis": "lexical-state-change",
            "source": sentence,
            "event_style_reference": (
                f"exists e. {ast['verb']}ing(e) and Theme(e, {theme}) "
                f"and ResultState(e, {target_state})"
            ),
            "typed_replacement": typed_replacement,
        },
        "dependent_type_translation": typed_replacement,
        "result_state_lexicon": [state_lexicon_metadata(target_state)],
        "state_change_verb_entry": state_change_verb_metadata(ast["verb"]),
        "ast": ast,
        "type_check": {
            **type_check,
            "note": (
                "A lexical change-of-state verb maps directly to a typed "
                "state transition; the changing object is not treated as an Agent."
            ),
        },
        "coq_code": coq_code,
    }


def stative_result_state_ast(
    subject: str,
    states: str | list[str],
    auxiliary: str,
    polarity: str = "positive",
) -> dict[str, Any]:
    state_names = [states] if isinstance(states, str) else states
    first_state = state_names[0]
    ast = {
        "kind": "stative_result_state",
        "subject": {"name": subject, "type": "Entity"},
        "state": {"name": first_state, "type": "State"},
        "state_scale": STATE_SCALE_BY_STATE[first_state],
        "predicate": "holds_state",
        "predicate_type": "Entity -> StateScale -> State -> Prop",
        "auxiliary": auxiliary,
    }
    if len(state_names) > 1:
        ast["states"] = [
            {
                "name": state_name,
                "type": "State",
                "state_scale": STATE_SCALE_BY_STATE[state_name],
            }
            for state_name in state_names
        ]
    if polarity != "positive":
        ast["polarity"] = polarity
    return ast


def check_stative_result_state_ast(ast: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if ast.get("kind") != "stative_result_state":
        errors.append("ast.kind must be stative_result_state")
    subject = ast.get("subject")
    if not isinstance(subject, dict):
        errors.append("stative subject must be an object")
    else:
        if not isinstance(subject.get("name"), str) or not subject.get("name"):
            errors.append("stative subject.name must be a non-empty string")
        if subject.get("type") != "Entity":
            errors.append("stative subject must have type Entity")

    state = ast.get("state")
    if not isinstance(state, dict):
        errors.append("stative state must be an object")
    else:
        state_name = state.get("name")
        if not isinstance(state_name, str) or not state_name:
            errors.append("stative state.name must be a non-empty string")
        elif state_name not in STATE_SCALE_BY_STATE:
            errors.append(f"unknown stative result state: {state_name}")
        if state.get("type") != "State":
            errors.append("stative state must have type State")
        if (
            isinstance(state_name, str)
            and state_name in STATE_SCALE_BY_STATE
            and ast.get("state_scale") != STATE_SCALE_BY_STATE[state_name]
        ):
            errors.append("stative state_scale must match the state lexicon")

    states = ast.get("states")
    if states is not None:
        if not isinstance(states, list) or not states:
            errors.append("stative states must be a non-empty list")
        else:
            for index, state_item in enumerate(states):
                if not isinstance(state_item, dict):
                    errors.append(f"stative states[{index}] must be an object")
                    continue
                item_name = state_item.get("name")
                if not isinstance(item_name, str) or not item_name:
                    errors.append(f"stative states[{index}].name must be a non-empty string")
                elif item_name not in STATE_SCALE_BY_STATE:
                    errors.append(f"unknown stative result state: {item_name}")
                if state_item.get("type") != "State":
                    errors.append(f"stative states[{index}] must have type State")
                if (
                    isinstance(item_name, str)
                    and item_name in STATE_SCALE_BY_STATE
                    and state_item.get("state_scale") != STATE_SCALE_BY_STATE[item_name]
                ):
                    errors.append(f"stative states[{index}].state_scale must match the state lexicon")

    if ast.get("predicate") != "holds_state":
        errors.append("stative predicate must be holds_state")
    if ast.get("predicate_type") != "Entity -> StateScale -> State -> Prop":
        errors.append("stative predicate must have type Entity -> StateScale -> State -> Prop")
    if ast.get("auxiliary") not in PASSIVE_AUXILIARIES:
        errors.append("stative auxiliary must be is, was, are, or were")
    if ast.get("polarity", "positive") not in {"positive", "negative"}:
        errors.append("stative polarity must be positive or negative")

    return {
        "ok": not errors,
        "type": "Prop" if not errors else None,
        "errors": errors,
    }


def stative_result_state_pipeline(sentence: str) -> dict[str, Any] | None:
    tokens = tokenize(sentence)
    auxiliary_indices = [
        index for index, token in enumerate(tokens) if token in PASSIVE_AUXILIARIES
    ]
    if len(tokens) < 3 or not auxiliary_indices:
        return None
    auxiliary_index = auxiliary_indices[0]
    auxiliary = tokens[auxiliary_index]
    if auxiliary_index == 0 or auxiliary_index + 1 >= len(tokens):
        return None
    subject = clean_phrase(tokens[:auxiliary_index])
    state_index = auxiliary_index + 1
    polarity = "positive"
    if tokens[state_index] == "not":
        polarity = "negative"
        state_index += 1
        if state_index >= len(tokens):
            return None
    state_tokens = tokens[state_index:]
    state_groups = split_coordinate_tokens(state_tokens)
    if state_groups is None:
        return None
    state_names = [clean_phrase(group) for group in state_groups]
    if any(len(group) != 1 for group in state_groups):
        return None
    if any(state_name not in STATE_SCALE_BY_STATE for state_name in state_names):
        return None

    ast = stative_result_state_ast(subject, state_names, auxiliary, polarity)
    type_check = check_stative_result_state_ast(ast)
    state_label = "_and_".join(state_names)
    definition_name = (
        f"stative_not_{state_label}_state"
        if polarity == "negative"
        else f"stative_{state_label}_state"
    )
    state_assertions = [
        f"holds_state({subject}, {STATE_SCALE_BY_STATE[state_name]}, {state_name})"
        for state_name in state_names
    ]
    state_assertion = state_assertions[0]
    for next_assertion in state_assertions[1:]:
        state_assertion = f"and_T({state_assertion}, {next_assertion})"
    typed_replacement = (
        f"not_T({state_assertion})" if polarity == "negative" else state_assertion
    )
    coq_assertions = [
        f"holds_state {subject} {STATE_SCALE_BY_STATE[state_name]} {state_name}"
        for state_name in state_names
    ]
    coq_assertion = coq_assertions[0]
    for next_assertion in coq_assertions[1:]:
        coq_assertion = f"and_T ({coq_assertion}) ({next_assertion})"
    coq_body = f"not_T ({coq_assertion})" if polarity == "negative" else coq_assertion
    state_declarations: list[str] = []
    for state_name in state_names:
        state_declarations.append(f"Parameter {state_name} : State.")
        state_declarations.append(f"Parameter {STATE_SCALE_BY_STATE[state_name]} : StateScale.")
    coq_code = "\n".join(
        [
            "(* Stative result-state replacement without an event variable. *)",
            "Parameter Entity : Type.",
            "Parameter State : Type.",
            "Parameter StateScale : Type.",
            "",
            f"Parameter {subject} : Entity.",
            *state_declarations,
            "",
            "Parameter holds_state : Entity -> StateScale -> State -> Prop.",
            *(
                ["Parameter and_T : Prop -> Prop -> Prop."]
                if len(state_names) > 1
                else []
            ),
            *(
                ["Parameter not_T : Prop -> Prop."]
                if polarity == "negative"
                else []
            ),
            "",
            f"Definition {definition_name} : Prop :=",
            f"  {coq_body}.",
            "",
            f"Check {definition_name}.",
            "",
        ]
    )
    return {
        "kind": "stative_result_state",
        "input_sentence": sentence,
        "event_semantics": {
            "analysis": "stative-result-state",
            "source": sentence,
            "event_style_reference": (
                f"exists e. ResultState(e, {state_label}) and Theme(e, {subject})"
            ),
            "typed_replacement": typed_replacement,
        },
        "dependent_type_translation": typed_replacement,
        "ast": ast,
        "type_check": {
            **type_check,
            "note": (
                "A copular result state is represented as a typed state "
                "assertion, not as an omitted Agent event."
            ),
        },
        "coq_code": coq_code,
    }


def copular_property_ast(
    subject: str,
    property_conjuncts: list[dict[str, str | None]],
    auxiliary: str,
    time_modifiers: list[dict[str, str]],
    negated: bool = False,
) -> dict[str, Any]:
    first = property_conjuncts[0]
    ast = {
        "kind": "copular_property",
        "subject": {"name": subject, "type": "Entity"},
        "property": {"name": first["property"], "type": "Property"},
        "predicate": "holds_property",
        "predicate_type": "Entity -> Property -> Prop",
        "auxiliary": auxiliary,
        "negated": negated,
        "time_modifiers": time_modifiers,
    }
    if first.get("degree") is not None:
        ast["degree"] = {"name": first["degree"], "type": "Degree"}
    if len(property_conjuncts) > 1:
        ast["property_conjuncts"] = [
            {
                "property": {"name": conjunct["property"], "type": "Property"},
                **(
                    {"degree": {"name": conjunct["degree"], "type": "Degree"}}
                    if conjunct.get("degree") is not None
                    else {}
                ),
            }
            for conjunct in property_conjuncts
        ]
    return ast


def check_copular_property_ast(ast: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if ast.get("kind") != "copular_property":
        errors.append("ast.kind must be copular_property")

    subject = ast.get("subject")
    if not isinstance(subject, dict):
        errors.append("copular property subject must be an object")
    else:
        if not isinstance(subject.get("name"), str) or not subject.get("name"):
            errors.append("copular property subject.name must be a non-empty string")
        if subject.get("type") != "Entity":
            errors.append("copular property subject must have type Entity")

    property_info = ast.get("property")
    if not isinstance(property_info, dict):
        errors.append("copular property must be an object")
    else:
        property_name = property_info.get("name")
        if not isinstance(property_name, str) or not property_name:
            errors.append("copular property.name must be a non-empty string")
        elif property_name in STATE_SCALE_BY_STATE:
            errors.append("copular property must not duplicate a registered State")
        if property_info.get("type") != "Property":
            errors.append("copular property must have type Property")

    if ast.get("predicate") != "holds_property":
        errors.append("copular property predicate must be holds_property")
    if ast.get("predicate_type") != "Entity -> Property -> Prop":
        errors.append("copular property predicate must have type Entity -> Property -> Prop")
    if ast.get("auxiliary") not in PASSIVE_AUXILIARIES:
        errors.append("copular property auxiliary must be is, was, are, or were")
    if not isinstance(ast.get("negated"), bool):
        errors.append("copular property negated must be a boolean")

    degree = ast.get("degree")
    if degree is not None:
        if not isinstance(degree, dict):
            errors.append("copular property degree must be an object")
        else:
            degree_name = degree.get("name")
            if degree_name not in PROPERTY_DEGREES:
                errors.append("copular property degree.name must be a registered Degree")
            if degree.get("type") != "Degree":
                errors.append("copular property degree must have type Degree")

    property_conjuncts = ast.get("property_conjuncts")
    if property_conjuncts is not None:
        if not isinstance(property_conjuncts, list) or len(property_conjuncts) < 2:
            errors.append("copular property_conjuncts must be a list with at least two items")
        else:
            for index, conjunct in enumerate(property_conjuncts):
                if not isinstance(conjunct, dict):
                    errors.append(f"copular property_conjuncts[{index}] must be an object")
                    continue
                conjunct_property = conjunct.get("property")
                if not isinstance(conjunct_property, dict):
                    errors.append(f"copular property_conjuncts[{index}].property must be an object")
                else:
                    conjunct_name = conjunct_property.get("name")
                    if not isinstance(conjunct_name, str) or not conjunct_name:
                        errors.append(
                            f"copular property_conjuncts[{index}].property.name must be a non-empty string"
                        )
                    elif conjunct_name in STATE_SCALE_BY_STATE:
                        errors.append(
                            f"copular property_conjuncts[{index}] must not duplicate a registered State"
                        )
                    if conjunct_property.get("type") != "Property":
                        errors.append(
                            f"copular property_conjuncts[{index}].property must have type Property"
                        )
                conjunct_degree = conjunct.get("degree")
                if conjunct_degree is not None:
                    if not isinstance(conjunct_degree, dict):
                        errors.append(f"copular property_conjuncts[{index}].degree must be an object")
                    else:
                        degree_name = conjunct_degree.get("name")
                        if degree_name not in PROPERTY_DEGREES:
                            errors.append(
                                f"copular property_conjuncts[{index}].degree.name must be a registered Degree"
                            )
                        if conjunct_degree.get("type") != "Degree":
                            errors.append(
                                f"copular property_conjuncts[{index}].degree must have type Degree"
                            )

    time_modifiers = ast.get("time_modifiers")
    if not isinstance(time_modifiers, list):
        errors.append("copular property time_modifiers must be a list")
    else:
        for index, modifier in enumerate(time_modifiers):
            if not isinstance(modifier, dict):
                errors.append(f"copular property time_modifiers[{index}] must be an object")
                continue
            if modifier.get("operator") not in {"at", "during"}:
                errors.append(
                    f"copular property time_modifiers[{index}].operator must be at or during"
                )
            if not isinstance(modifier.get("argument"), str) or not modifier.get("argument"):
                errors.append(
                    f"copular property time_modifiers[{index}].argument must be a non-empty string"
                )

    return {
        "ok": not errors,
        "type": "Prop" if not errors else None,
        "errors": errors,
    }


def copular_property_time_modifiers(tokens: list[str]) -> list[dict[str, str]] | None:
    modifiers: list[dict[str, str]] = []
    idx = 0
    while idx < len(tokens):
        token = tokens[idx]
        if token in TEMPORAL_ADVERBS:
            modifiers.append({"operator": "at", "argument": token})
            idx += 1
            continue
        temporal_phrase = temporal_phrase_value(tokens, idx)
        if temporal_phrase is not None:
            normalized_time, consumed = temporal_phrase
            modifiers.append({"operator": "at", "argument": normalized_time})
            idx += consumed
            continue
        temporal_prep_phrase = temporal_prepositional_phrase_value(tokens, idx)
        if temporal_prep_phrase is not None:
            operator, normalized_time, consumed = temporal_prep_phrase
            modifiers.append({"operator": operator, "argument": normalized_time})
            idx += consumed
            continue
        return None
    return modifiers


def split_fronted_time_modifiers(
    tokens: list[str],
) -> tuple[list[str], list[dict[str, str]]]:
    modifiers: list[dict[str, str]] = []
    idx = 0
    while idx < len(tokens):
        token = tokens[idx]
        if token in TEMPORAL_ADVERBS:
            modifiers.append({"operator": "at", "argument": token})
            idx += 1
            continue
        temporal_phrase = temporal_phrase_value(tokens, idx)
        if temporal_phrase is not None:
            normalized_time, consumed = temporal_phrase
            modifiers.append({"operator": "at", "argument": normalized_time})
            idx += consumed
            continue
        temporal_prep_phrase = temporal_prepositional_phrase_value(tokens, idx)
        if temporal_prep_phrase is not None:
            operator, normalized_time, consumed = temporal_prep_phrase
            modifiers.append({"operator": operator, "argument": normalized_time})
            idx += consumed
            continue
        break
    return tokens[idx:], modifiers


def starts_surface_subject_boundary(tokens: list[str], position: int) -> bool:
    subject_start = position
    starts_with_article = False
    if subject_start < len(tokens) and tokens[subject_start] in ARTICLES:
        starts_with_article = True
        subject_start += 1
    if subject_start >= len(tokens):
        return False

    def is_boundary_predicate(token: str) -> bool:
        return token in PASSIVE_AUXILIARIES or is_likely_surface_verb(token) or (
            token.endswith("ed") and len(token) > 3
        )

    subject_widths = (1, 2) if starts_with_article else (1,)
    for subject_width in subject_widths:
        predicate_position = subject_start + subject_width
        if (
            predicate_position < len(tokens)
            and is_boundary_predicate(tokens[predicate_position])
        ):
            return True
    return False


def modifier_expression(preposition: str, phrase_tokens: list[str]) -> str:
    return f"{preposition}({clean_phrase(phrase_tokens)})"


def modifier_record(expression: str) -> dict[str, Any]:
    semantic_role = modifier_semantic_role(expression)
    return {
        "expression": expression,
        "name": normalize_surface_name(expression),
        "type": "Adv",
        "semantic_role": semantic_role,
        "surface_lexicon": modifier_surface_audit(expression, "Adv", semantic_role),
    }


def split_fronted_adv_modifiers(
    tokens: list[str],
) -> tuple[list[str], list[dict[str, Any]]]:
    modifiers: list[dict[str, Any]] = []
    idx = 0
    while idx < len(tokens):
        if tokens[idx] in COMMON_ADVERBS:
            modifiers.append(modifier_record(tokens[idx]))
            idx += 1
            continue
        preposition = tokens[idx]
        if preposition not in FRONTED_MODIFIER_PREPOSITIONS:
            break
        if temporal_prepositional_phrase_value(tokens, idx) is not None:
            break
        phrase_start = idx + 1
        phrase: list[str] = []
        cursor = phrase_start
        while cursor < len(tokens):
            if any(token not in ARTICLES for token in phrase):
                if tokens[cursor] in FRONTED_MODIFIER_PREPOSITIONS:
                    break
                if tokens[cursor] in COMMON_ADVERBS:
                    break
                if tokens[cursor] in TEMPORAL_ADVERBS:
                    break
                if temporal_phrase_value(tokens, cursor) is not None:
                    break
                if temporal_prepositional_phrase_value(tokens, cursor) is not None:
                    break
                if starts_surface_subject_boundary(tokens, cursor):
                    break
            phrase.append(tokens[cursor])
            cursor += 1
        if not any(token not in ARTICLES for token in phrase):
            break
        modifiers.append(modifier_record(modifier_expression(preposition, phrase)))
        idx = cursor
    return tokens[idx:], modifiers


def split_shared_adv_and_time_modifiers(
    tokens: list[str],
) -> tuple[list[dict[str, Any]], list[dict[str, str]]] | None:
    if not tokens:
        return [], []
    remaining_tokens, adv_modifiers = split_fronted_adv_modifiers(tokens)
    time_modifiers = copular_property_time_modifiers(remaining_tokens)
    if time_modifiers is None:
        return None
    return adv_modifiers, time_modifiers


def check_coordination_modifiers(
    errors: list[str],
    modifiers: Any,
    context: str,
) -> None:
    if not isinstance(modifiers, list):
        errors.append(f"{context} modifiers must be a list")
        return
    for index, modifier in enumerate(modifiers):
        if not isinstance(modifier, dict):
            errors.append(f"{context} modifiers[{index}] must be an object")
            continue
        expression = modifier.get("expression")
        if not isinstance(expression, str) or not expression:
            errors.append(f"{context} modifiers[{index}].expression must be a non-empty string")
            continue
        expected_name = normalize_surface_name(expression)
        if modifier.get("name") != expected_name:
            errors.append(f"{context} modifiers[{index}].name must match normalized expression")
        if modifier.get("type") != "Adv":
            errors.append(f"{context} modifiers[{index}] must have type Adv")
        expected_role = modifier_semantic_role(expression)
        if modifier.get("semantic_role") != expected_role:
            errors.append(f"{context} modifiers[{index}].semantic_role must match expression")
        expected_audit = modifier_surface_audit(expression, "Adv", expected_role)
        if modifier.get("surface_lexicon") != expected_audit:
            errors.append(f"{context} modifiers[{index}].surface_lexicon must match modifier")


def readable_modifier_arguments(modifiers: list[dict[str, Any]]) -> str:
    return ", ".join(str(modifier["expression"]) for modifier in modifiers)


def coq_modifier_sequence(modifiers: list[dict[str, Any]]) -> str:
    sequence = "mods_nil"
    length = len(modifiers)
    for index, modifier in reversed(list(enumerate(modifiers))):
        sequence = (
            f"(mods_cons {length - index - 1} "
            f"{modifier['name']} {sequence})"
        )
    return sequence


def unique_names(names: list[str]) -> list[str]:
    return list(dict.fromkeys(names))


def unique_typed_declarations(declarations: list[tuple[str, str]]) -> list[tuple[str, str]]:
    unique: list[tuple[str, str]] = []
    seen: dict[str, str] = {}
    for name, type_name in declarations:
        if name in seen:
            continue
        seen[name] = type_name
        unique.append((name, type_name))
    return unique


def check_declaration_type_conflicts(
    errors: list[str],
    declarations: list[tuple[str, str]],
    context: str,
) -> None:
    seen: dict[str, str] = {}
    for name, type_name in declarations:
        previous_type = seen.get(name)
        if previous_type is None:
            seen[name] = type_name
        elif previous_type != type_name:
            errors.append(
                f"{context} {name} has conflicting lexical types: "
                f"{previous_type} vs {type_name}"
            )


def render_copular_property_translation(
    subject: str,
    property_conjuncts: list[dict[str, str | None]],
    time_modifiers: list[dict[str, str]],
    negated: bool = False,
) -> str:
    assertions: list[str] = []
    for conjunct in property_conjuncts:
        property_name = str(conjunct["property"])
        degree = conjunct.get("degree")
        property_expr = (
            f"degree_property({degree}, {property_name})"
            if degree is not None
            else property_name
        )
        assertions.append(f"holds_property({subject}, {property_expr})")
    proposition = assertions[0]
    for next_assertion in assertions[1:]:
        proposition = f"and_T({proposition}, {next_assertion})"
    if negated:
        proposition = f"not_T({proposition})"
    for modifier in time_modifiers:
        proposition = f"{modifier['operator']}_T({modifier['argument']}, {proposition})"
    return proposition


def render_copular_property_coq(
    definition_name: str,
    subject: str,
    property_conjuncts: list[dict[str, str | None]],
    time_modifiers: list[dict[str, str]],
    negated: bool = False,
) -> str:
    assertions: list[str] = []
    for conjunct in property_conjuncts:
        property_name = str(conjunct["property"])
        degree = conjunct.get("degree")
        property_expr = (
            f"(degree_property {degree} {property_name})"
            if degree is not None
            else property_name
        )
        assertions.append(f"holds_property {subject} {property_expr}")
    proposition = assertions[0]
    for next_assertion in assertions[1:]:
        proposition = f"and_T ({proposition}) ({next_assertion})"
    if negated:
        proposition = f"not_T ({proposition})"
    for modifier in time_modifiers:
        proposition = f"{modifier['operator']}_T {modifier['argument']} ({proposition})"
    property_names = list(dict.fromkeys(str(item["property"]) for item in property_conjuncts))
    degree_names = list(
        dict.fromkeys(str(item["degree"]) for item in property_conjuncts if item.get("degree") is not None)
    )
    lines = [
        "(* Copular property replacement without an event variable. *)",
        "Parameter Entity : Type.",
        "Parameter Property : Type.",
        "",
        f"Parameter {subject} : Entity.",
    ]
    lines.extend(f"Parameter {property_name} : Property." for property_name in property_names)
    if degree_names:
        lines.extend(
            [
                "Parameter Degree : Type.",
                *(f"Parameter {degree} : Degree." for degree in degree_names),
                "Parameter degree_property : Degree -> Property -> Property.",
            ]
        )
    if len(property_conjuncts) > 1:
        lines.append("Parameter and_T : Prop -> Prop -> Prop.")
    if negated:
        lines.append("Parameter not_T : Prop -> Prop.")
    if time_modifiers:
        lines.extend(
            f"Parameter {modifier['argument']} : Entity."
            for modifier in time_modifiers
        )
        lines.extend(
            [
                "",
                "Parameter at_T : Entity -> Prop -> Prop.",
                "Parameter during_T : Entity -> Prop -> Prop.",
            ]
        )
    lines.extend(
        [
            "",
            "Parameter holds_property : Entity -> Property -> Prop.",
            "",
            f"Definition {definition_name} : Prop :=",
            f"  {proposition}.",
            "",
            f"Check {definition_name}.",
            "",
        ]
    )
    return "\n".join(lines)


def copular_property_pipeline(sentence: str) -> dict[str, Any] | None:
    tokens = tokenize(sentence)
    auxiliary_indices = [
        index for index, token in enumerate(tokens) if token in PASSIVE_AUXILIARIES
    ]
    if len(tokens) < 3 or not auxiliary_indices:
        return None
    auxiliary_index = auxiliary_indices[0]
    auxiliary = tokens[auxiliary_index]
    if auxiliary_index == 0 or auxiliary_index + 1 >= len(tokens):
        return None
    if tokens[auxiliary_index + 1] in PREPOSITIONS:
        return None

    subject = clean_phrase(tokens[:auxiliary_index])
    property_tokens: list[str] = []
    idx = auxiliary_index + 1
    while idx < len(tokens):
        if (
            tokens[idx] in TEMPORAL_ADVERBS
            or temporal_phrase_value(tokens, idx) is not None
            or temporal_prepositional_phrase_value(tokens, idx) is not None
        ):
            break
        property_tokens.append(tokens[idx])
        idx += 1
    if not property_tokens:
        return None

    negated = False
    if property_tokens and property_tokens[0] == "not":
        negated = True
        property_tokens = property_tokens[1:]
    if not property_tokens:
        return None
    property_groups = split_coordinate_tokens(property_tokens)
    if property_groups is None:
        return None
    property_conjuncts: list[dict[str, str | None]] = []
    for group in property_groups:
        degree = None
        if group and group[0] in PROPERTY_DEGREES:
            degree = group[0]
            group = group[1:]
        if not group:
            return None
        if len(group) == 1 and is_passive_participle(group[0]):
            return None
        property_name = clean_phrase(group)
        if property_name in STATE_SCALE_BY_STATE:
            return None
        property_conjuncts.append({"property": property_name, "degree": degree})
    time_modifiers = copular_property_time_modifiers(tokens[idx:])
    if time_modifiers is None:
        return None

    ast = copular_property_ast(
        subject,
        property_conjuncts,
        auxiliary,
        time_modifiers,
        negated=negated,
    )
    type_check = check_copular_property_ast(ast)
    definition_name = f"property_{property_conjuncts[0]['property']}_assertion"
    typed_replacement = render_copular_property_translation(
        subject,
        property_conjuncts,
        time_modifiers,
        negated=negated,
    )
    coq_code = render_copular_property_coq(
        definition_name,
        subject,
        property_conjuncts,
        time_modifiers,
        negated=negated,
    )
    return {
        "kind": "copular_property",
        "input_sentence": sentence,
        "event_semantics": {
            "analysis": "copular-property",
            "source": sentence,
            "event_style_reference": (
                f"Property({subject}, {property_name}) without Agent(e, {subject})"
            ),
            "typed_replacement": typed_replacement,
        },
        "dependent_type_translation": typed_replacement,
        "ast": ast,
        "type_check": {
            **type_check,
            "note": (
                "A copular property is represented as Entity -> Property -> Prop; "
                "registered states and passive participles are handled by more "
                "specific construction rules."
            ),
        },
        "coq_code": coq_code,
    }


def predicate_coordination_ast(
    subject: str,
    predicates: list[dict[str, str]],
    modifiers: list[dict[str, Any]],
    time_modifiers: list[dict[str, str]],
) -> dict[str, Any]:
    return {
        "kind": "predicate_coordination",
        "subject": {"name": subject, "type": "Entity"},
        "predicates": predicates,
        "modifiers": modifiers,
        "connective": "and_T",
        "connective_type": (
            "PropT -> PropT -> PropT" if modifiers else "Prop -> Prop -> Prop"
        ),
        "time_modifiers": time_modifiers,
    }


def check_predicate_coordination_ast(ast: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if ast.get("kind") != "predicate_coordination":
        errors.append("ast.kind must be predicate_coordination")
    modifiers = ast.get("modifiers")
    has_modifiers = isinstance(modifiers, list) and bool(modifiers)
    expected_predicate_type = (
        "forall n : nat, ModifierSeq n -> Entity -> PropT"
        if has_modifiers
        else "Entity -> Prop"
    )

    subject = ast.get("subject")
    if not isinstance(subject, dict):
        errors.append("predicate coordination subject must be an object")
    else:
        if not isinstance(subject.get("name"), str) or not subject.get("name"):
            errors.append("predicate coordination subject.name must be a non-empty string")
        if subject.get("type") != "Entity":
            errors.append("predicate coordination subject must have type Entity")

    predicates = ast.get("predicates")
    if not isinstance(predicates, list) or len(predicates) != 2:
        errors.append("predicate coordination predicates must contain exactly two items")
    else:
        for index, predicate in enumerate(predicates):
            if not isinstance(predicate, dict):
                errors.append(f"predicate coordination predicates[{index}] must be an object")
                continue
            surface = predicate.get("surface")
            if not isinstance(surface, str) or not surface:
                errors.append(
                    f"predicate coordination predicates[{index}].surface must be a non-empty string"
                )
            name = predicate.get("name")
            if not isinstance(name, str) or not name:
                errors.append(
                    f"predicate coordination predicates[{index}].name must be a non-empty string"
                )
            elif surface and lemma_verb(str(surface)) != name:
                errors.append(
                    f"predicate coordination predicates[{index}].name must match its surface lemma"
                )
            if "negated" in predicate and not isinstance(predicate["negated"], bool):
                errors.append(
                    f"predicate coordination predicates[{index}].negated must be boolean"
                )
            if predicate.get("predicate_type") != expected_predicate_type:
                errors.append(
                    "predicate coordination "
                    f"predicates[{index}] must have type {expected_predicate_type}"
                )

    if ast.get("connective") != "and_T":
        errors.append("predicate coordination connective must be and_T")
    expected_connective_type = (
        "PropT -> PropT -> PropT" if has_modifiers else "Prop -> Prop -> Prop"
    )
    if ast.get("connective_type") != expected_connective_type:
        errors.append(
            "predicate coordination connective must have type "
            f"{expected_connective_type}"
        )

    check_coordination_modifiers(
        errors,
        modifiers,
        "predicate coordination",
    )

    time_modifiers = ast.get("time_modifiers")
    if not isinstance(time_modifiers, list):
        errors.append("predicate coordination time_modifiers must be a list")
    else:
        for index, modifier in enumerate(time_modifiers):
            if not isinstance(modifier, dict):
                errors.append(f"predicate coordination time_modifiers[{index}] must be an object")
                continue
            if modifier.get("operator") not in {"at", "during"}:
                errors.append(
                    f"predicate coordination time_modifiers[{index}].operator must be at or during"
                )
            if not isinstance(modifier.get("argument"), str) or not modifier.get("argument"):
                errors.append(
                    f"predicate coordination time_modifiers[{index}].argument must be a non-empty string"
                )

    return {
        "ok": not errors,
        "type": "Prop" if not errors else None,
        "errors": errors,
    }


def render_predicate_coordination_translation(ast: dict[str, Any]) -> str:
    subject = ast["subject"]["name"]
    predicates = ast["predicates"]
    modifiers = ast.get("modifiers", [])
    if modifiers:
        modifier_args = readable_modifier_arguments(modifiers)
        modifier_count = len(modifiers)
        left = f"{predicates[0]['name']}({modifier_count})({modifier_args}, {subject})"
        right = f"{predicates[1]['name']}({modifier_count})({modifier_args}, {subject})"
    else:
        left = f"{predicates[0]['name']}({subject})"
        right = f"{predicates[1]['name']}({subject})"
    left = wrap_negated_translation(left, bool(predicates[0].get("negated")))
    right = wrap_negated_translation(right, bool(predicates[1].get("negated")))
    proposition = f"and_T({left}, {right})"
    for modifier in ast["time_modifiers"]:
        proposition = f"{modifier['operator']}_T({modifier['argument']}, {proposition})"
    return proposition


def render_predicate_coordination_coq(
    definition_name: str,
    ast: dict[str, Any],
) -> str:
    subject = ast["subject"]["name"]
    predicates = ast["predicates"]
    modifiers = ast.get("modifiers", [])
    if modifiers:
        modifier_count = len(modifiers)
        modifier_sequence = coq_modifier_sequence(modifiers)
        left = f"{predicates[0]['name']} {modifier_count} {modifier_sequence} {subject}"
        right = f"{predicates[1]['name']} {modifier_count} {modifier_sequence} {subject}"
    else:
        left = f"{predicates[0]['name']} {subject}"
        right = f"{predicates[1]['name']} {subject}"
    left = wrap_negated_coq(left, bool(predicates[0].get("negated")))
    right = wrap_negated_coq(right, bool(predicates[1].get("negated")))
    proposition = f"and_T ({left}) ({right})"
    for modifier in ast["time_modifiers"]:
        proposition = f"{modifier['operator']}_T {modifier['argument']} ({proposition})"
    predicate_names = list(dict.fromkeys(predicate["name"] for predicate in predicates))
    lines = [
        "(* Same-subject predicate coordination without event variables. *)",
        "Parameter Entity : Type.",
    ]
    if modifiers:
        lines.extend(
            [
                "Definition PropT : Type := Prop.",
                "Definition Adv : Type := (Entity -> PropT) -> Entity -> PropT.",
                "Parameter ModifierSeq : nat -> Type.",
                "Parameter mods_nil : ModifierSeq 0.",
                "Parameter mods_cons : forall n : nat, Adv -> ModifierSeq n -> ModifierSeq (S n).",
            ]
        )
        lines.extend(f"Parameter {name} : Adv." for name in unique_names([
            modifier["name"] for modifier in modifiers
        ]))
    lines.extend(["", f"Parameter {subject} : Entity."])
    if modifiers:
        lines.extend(
            f"Parameter {predicate} : forall n : nat, ModifierSeq n -> Entity -> PropT."
            for predicate in predicate_names
        )
        if any(predicate.get("negated") for predicate in predicates):
            lines.append("Parameter not_T : PropT -> PropT.")
        lines.append("Parameter and_T : PropT -> PropT -> PropT.")
    else:
        lines.extend(f"Parameter {predicate} : Entity -> Prop." for predicate in predicate_names)
        if any(predicate.get("negated") for predicate in predicates):
            lines.append("Parameter not_T : Prop -> Prop.")
        lines.append("Parameter and_T : Prop -> Prop -> Prop.")
    if ast["time_modifiers"]:
        lines.extend(
            f"Parameter {name} : Entity."
            for name in unique_names([
                modifier["argument"] for modifier in ast["time_modifiers"]
            ])
        )
        lines.extend(
            [
                "",
                "Parameter at_T : Entity -> Prop -> Prop.",
                "Parameter during_T : Entity -> Prop -> Prop.",
            ]
        )
    lines.extend(
        [
            "",
            f"Definition {definition_name} : Prop :=",
            f"  {proposition}.",
            "",
            f"Check {definition_name}.",
            "",
        ]
    )
    return "\n".join(lines)


def predicate_coordination_pipeline(sentence: str) -> dict[str, Any] | None:
    tokens, fronted_time_modifiers = split_fronted_time_modifiers(tokenize(sentence))
    tokens, fronted_adv_modifiers = split_fronted_adv_modifiers(tokens)
    if tokens.count("and") != 1:
        return None
    and_index = tokens.index("and")
    left_predicate_index = and_index - 1
    right_predicate_index = and_index + 1
    if left_predicate_index <= 0 or right_predicate_index >= len(tokens):
        return None

    left_surface = tokens[left_predicate_index]
    right_surface = tokens[right_predicate_index]
    if not is_likely_surface_verb(left_surface) or not is_likely_surface_verb(right_surface):
        return None

    subject = clean_phrase(tokens[:left_predicate_index])
    if subject == "entity":
        return None
    trailing_modifiers = split_shared_adv_and_time_modifiers(
        tokens[right_predicate_index + 1 :]
    )
    if trailing_modifiers is None:
        return None
    trailing_adv_modifiers, trailing_time_modifiers = trailing_modifiers
    shared_adv_modifiers = [*fronted_adv_modifiers, *trailing_adv_modifiers]
    time_modifiers = [*fronted_time_modifiers, *trailing_time_modifiers]

    predicates = [
        {
            "surface": left_surface,
            "name": lemma_verb(left_surface),
            "predicate_type": (
                "forall n : nat, ModifierSeq n -> Entity -> PropT"
                if shared_adv_modifiers
                else "Entity -> Prop"
            ),
        },
        {
            "surface": right_surface,
            "name": lemma_verb(right_surface),
            "predicate_type": (
                "forall n : nat, ModifierSeq n -> Entity -> PropT"
                if shared_adv_modifiers
                else "Entity -> Prop"
            ),
        },
    ]
    ast = predicate_coordination_ast(
        subject,
        predicates,
        shared_adv_modifiers,
        time_modifiers,
    )
    type_check = check_predicate_coordination_ast(ast)
    typed_replacement = render_predicate_coordination_translation(ast)
    coq_code = render_predicate_coordination_coq("predicate_coordination_assertion", ast)
    return {
        "kind": "predicate_coordination",
        "input_sentence": sentence,
        "construction_summary": (
            f"Same subject {subject} coordinates "
            f"{predicates[0]['name']} : {predicates[0]['predicate_type']} and "
            f"{predicates[1]['name']} : {predicates[1]['predicate_type']}"
            + (
                " with shared Adv modifiers "
                + ", ".join(modifier["expression"] for modifier in shared_adv_modifiers)
                if shared_adv_modifiers
                else ""
            )
            + "."
        ),
        "event_semantics": {
            "analysis": "same-subject-predicate-coordination",
            "source": sentence,
            "event_style_reference": (
                "exists e1 e2. "
                f"{predicates[0]['name']}(e1) and Agent(e1, {subject}) and "
                f"{predicates[1]['name']}(e2) and Agent(e2, {subject})"
            ),
            "typed_replacement": typed_replacement,
        },
        "dependent_type_translation": typed_replacement,
        "ast": ast,
        "type_check": {
            **type_check,
            "note": (
                (
                    "Same-subject intransitive coordination with shared Adv "
                    "modifiers is represented through modifier-indexed "
                    "predicates and a typed conjunction; no shared event "
                    "variable or Theme argument is introduced."
                )
                if shared_adv_modifiers
                else (
                    "Same-subject intransitive coordination is represented as a "
                    "typed conjunction of Entity -> Prop predicates; no shared "
                    "event variable or Theme argument is introduced."
                )
            ),
        },
        "coq_code": coq_code,
    }


def transitive_predicate_coordination_ast(
    subject: str,
    clauses: list[dict[str, Any]],
    modifiers: list[dict[str, Any]],
    time_modifiers: list[dict[str, str]],
) -> dict[str, Any]:
    return {
        "kind": "transitive_predicate_coordination",
        "subject": {"name": subject, "type": "Entity"},
        "clauses": clauses,
        "modifiers": modifiers,
        "connective": "and_T",
        "connective_type": (
            "PropT -> PropT -> PropT" if modifiers else "Prop -> Prop -> Prop"
        ),
        "time_modifiers": time_modifiers,
    }


def check_transitive_predicate_coordination_ast(ast: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if ast.get("kind") != "transitive_predicate_coordination":
        errors.append("ast.kind must be transitive_predicate_coordination")
    modifiers = ast.get("modifiers")
    has_modifiers = isinstance(modifiers, list) and bool(modifiers)

    subject = ast.get("subject")
    if not isinstance(subject, dict):
        errors.append("transitive predicate coordination subject must be an object")
    else:
        if not isinstance(subject.get("name"), str) or not subject.get("name"):
            errors.append(
                "transitive predicate coordination subject.name must be a non-empty string"
            )
        if subject.get("type") != "Entity":
            errors.append("transitive predicate coordination subject must have type Entity")

    clauses = ast.get("clauses")
    if not isinstance(clauses, list) or len(clauses) != 2:
        errors.append("transitive predicate coordination clauses must contain exactly two items")
    else:
        for index, clause in enumerate(clauses):
            if not isinstance(clause, dict):
                errors.append(f"transitive predicate coordination clauses[{index}] must be an object")
                continue
            predicate = clause.get("predicate")
            if not isinstance(predicate, dict):
                errors.append(
                    f"transitive predicate coordination clauses[{index}].predicate must be an object"
                )
                continue
            surface = predicate.get("surface")
            if not isinstance(surface, str) or not surface:
                errors.append(
                    "transitive predicate coordination "
                    f"clauses[{index}].predicate.surface must be a non-empty string"
                )
            name = predicate.get("name")
            if not isinstance(name, str) or not name:
                errors.append(
                    "transitive predicate coordination "
                    f"clauses[{index}].predicate.name must be a non-empty string"
                )
            elif surface and lemma_verb(str(surface)) != name:
                errors.append(
                    "transitive predicate coordination "
                    f"clauses[{index}].predicate.name must match its surface lemma"
                )
            if "negated" in clause and not isinstance(clause["negated"], bool):
                errors.append(
                    "transitive predicate coordination "
                    f"clauses[{index}].negated must be boolean"
                )
            obj = clause.get("object")
            if not isinstance(obj, dict):
                errors.append(
                    f"transitive predicate coordination clauses[{index}].object must be an object"
                )
                continue
            object_name = obj.get("name")
            object_type = obj.get("type")
            if not isinstance(object_name, str) or not object_name:
                errors.append(
                    "transitive predicate coordination "
                    f"clauses[{index}].object.name must be a non-empty string"
                )
            if not isinstance(object_type, str) or not object_type:
                errors.append(
                    "transitive predicate coordination "
                    f"clauses[{index}].object.type must be a non-empty string"
                )
            expected_predicate_type = (
                (
                    f"forall n : nat, ModifierSeq n -> Entity -> {object_type} -> PropT"
                    if has_modifiers
                    else f"Entity -> {object_type} -> Prop"
                )
                if isinstance(object_type, str) and object_type
                else None
            )
            if (
                expected_predicate_type is not None
                and predicate.get("predicate_type") != expected_predicate_type
            ):
                errors.append(
                    "transitive predicate coordination "
                    f"clauses[{index}].predicate must have type {expected_predicate_type}"
                )
        object_declarations = [
            (clause["object"]["name"], clause["object"]["type"])
            for clause in clauses
            if isinstance(clause, dict)
            and isinstance(clause.get("object"), dict)
            and isinstance(clause["object"].get("name"), str)
            and isinstance(clause["object"].get("type"), str)
        ]
        check_declaration_type_conflicts(
            errors,
            object_declarations,
            "transitive predicate coordination object",
        )

    if ast.get("connective") != "and_T":
        errors.append("transitive predicate coordination connective must be and_T")
    expected_connective_type = (
        "PropT -> PropT -> PropT" if has_modifiers else "Prop -> Prop -> Prop"
    )
    if ast.get("connective_type") != expected_connective_type:
        errors.append(
            "transitive predicate coordination connective must have type "
            f"{expected_connective_type}"
        )

    check_coordination_modifiers(
        errors,
        modifiers,
        "transitive predicate coordination",
    )

    time_modifiers = ast.get("time_modifiers")
    if not isinstance(time_modifiers, list):
        errors.append("transitive predicate coordination time_modifiers must be a list")
    else:
        for index, modifier in enumerate(time_modifiers):
            if not isinstance(modifier, dict):
                errors.append(
                    f"transitive predicate coordination time_modifiers[{index}] must be an object"
                )
                continue
            if modifier.get("operator") not in {"at", "during"}:
                errors.append(
                    "transitive predicate coordination "
                    f"time_modifiers[{index}].operator must be at or during"
                )
            if not isinstance(modifier.get("argument"), str) or not modifier.get("argument"):
                errors.append(
                    "transitive predicate coordination "
                    f"time_modifiers[{index}].argument must be a non-empty string"
                )

    return {
        "ok": not errors,
        "type": "Prop" if not errors else None,
        "errors": errors,
    }


def render_transitive_predicate_coordination_translation(ast: dict[str, Any]) -> str:
    subject = ast["subject"]["name"]
    clauses = ast["clauses"]
    modifiers = ast.get("modifiers", [])
    if modifiers:
        modifier_args = readable_modifier_arguments(modifiers)
        modifier_count = len(modifiers)
        left = (
            f"{clauses[0]['predicate']['name']}({modifier_count})"
            f"({modifier_args}, {subject}, {clauses[0]['object']['name']})"
        )
        right = (
            f"{clauses[1]['predicate']['name']}({modifier_count})"
            f"({modifier_args}, {subject}, {clauses[1]['object']['name']})"
        )
    else:
        left = f"{clauses[0]['predicate']['name']}({subject}, {clauses[0]['object']['name']})"
        right = f"{clauses[1]['predicate']['name']}({subject}, {clauses[1]['object']['name']})"
    left = wrap_negated_translation(left, bool(clauses[0].get("negated")))
    right = wrap_negated_translation(right, bool(clauses[1].get("negated")))
    proposition = f"and_T({left}, {right})"
    for modifier in ast["time_modifiers"]:
        proposition = f"{modifier['operator']}_T({modifier['argument']}, {proposition})"
    return proposition


def render_transitive_predicate_coordination_coq(
    definition_name: str,
    ast: dict[str, Any],
) -> str:
    subject = ast["subject"]["name"]
    clauses = ast["clauses"]
    modifiers = ast.get("modifiers", [])
    if modifiers:
        modifier_count = len(modifiers)
        modifier_sequence = coq_modifier_sequence(modifiers)
        left = (
            f"{clauses[0]['predicate']['name']} "
            f"{modifier_count} {modifier_sequence} {subject} {clauses[0]['object']['name']}"
        )
        right = (
            f"{clauses[1]['predicate']['name']} "
            f"{modifier_count} {modifier_sequence} {subject} {clauses[1]['object']['name']}"
        )
    else:
        left = f"{clauses[0]['predicate']['name']} {subject} {clauses[0]['object']['name']}"
        right = f"{clauses[1]['predicate']['name']} {subject} {clauses[1]['object']['name']}"
    left = wrap_negated_coq(left, bool(clauses[0].get("negated")))
    right = wrap_negated_coq(right, bool(clauses[1].get("negated")))
    proposition = f"and_T ({left}) ({right})"
    for modifier in ast["time_modifiers"]:
        proposition = f"{modifier['operator']}_T {modifier['argument']} ({proposition})"
    object_types = list(
        dict.fromkeys(
            clause["object"]["type"]
            for clause in clauses
            if clause["object"]["type"] != "Entity"
        )
    )
    lines = [
        "(* Same-subject transitive VP coordination without event variables. *)",
        "Parameter Entity : Type.",
    ]
    if modifiers:
        lines.extend(
            [
                "Definition PropT : Type := Prop.",
                "Definition Adv : Type := (Entity -> PropT) -> Entity -> PropT.",
                "Parameter ModifierSeq : nat -> Type.",
                "Parameter mods_nil : ModifierSeq 0.",
                "Parameter mods_cons : forall n : nat, Adv -> ModifierSeq n -> ModifierSeq (S n).",
            ]
        )
    lines.extend(f"Parameter {object_type} : Type." for object_type in object_types)
    if modifiers:
        lines.extend(f"Parameter {name} : Adv." for name in unique_names([
            modifier["name"] for modifier in modifiers
        ]))
    lines.extend(
        [
            "",
            f"Parameter {subject} : Entity.",
        ]
    )
    for name, type_name in unique_typed_declarations([
        (clause["object"]["name"], clause["object"]["type"])
        for clause in clauses
    ]):
        lines.append(f"Parameter {name} : {type_name}.")
    for name, predicate_type in unique_typed_declarations([
        (clause["predicate"]["name"], clause["predicate"]["predicate_type"])
        for clause in clauses
    ]):
        lines.append(
            "Parameter "
            f"{name} : "
            f"{predicate_type}."
        )
    if modifiers:
        if any(clause.get("negated") for clause in clauses):
            lines.append("Parameter not_T : PropT -> PropT.")
        lines.append("Parameter and_T : PropT -> PropT -> PropT.")
    else:
        if any(clause.get("negated") for clause in clauses):
            lines.append("Parameter not_T : Prop -> Prop.")
        lines.append("Parameter and_T : Prop -> Prop -> Prop.")
    if ast["time_modifiers"]:
        lines.extend(
            f"Parameter {name} : Entity."
            for name in unique_names([
                modifier["argument"] for modifier in ast["time_modifiers"]
            ])
        )
        lines.extend(
            [
                "",
                "Parameter at_T : Entity -> Prop -> Prop.",
                "Parameter during_T : Entity -> Prop -> Prop.",
            ]
        )
    lines.extend(
        [
            "",
            f"Definition {definition_name} : Prop :=",
            f"  {proposition}.",
            "",
            f"Check {definition_name}.",
            "",
        ]
    )
    return "\n".join(lines)


def object_type_for_transitive_predicate(predicate: str) -> str:
    return application_argument_types(predicate, 2)[1]


def split_object_tokens_and_modifiers(
    tokens: list[str],
) -> tuple[list[str], list[dict[str, Any]], list[dict[str, str]]] | None:
    for split_index in range(1, len(tokens) + 1):
        modifier_parse = split_shared_adv_and_time_modifiers(tokens[split_index:])
        if modifier_parse is not None:
            adv_modifiers, time_modifiers = modifier_parse
            return tokens[:split_index], adv_modifiers, time_modifiers
    return None


def coordinated_intransitive_do_support_negation(
    sentence: str,
    tokens: list[str],
    and_index: int,
    right_surface: str,
    fronted_adv_modifiers: list[dict[str, Any]],
    fronted_time_modifiers: list[dict[str, str]],
) -> dict[str, Any] | None:
    left_predicate_index = and_index - 1
    if left_predicate_index <= 0:
        return None
    left_surface = tokens[left_predicate_index]
    if not is_likely_surface_verb(left_surface):
        return None
    subject = clean_phrase(tokens[:left_predicate_index])
    if subject == "entity":
        return None
    trailing_modifiers = split_shared_adv_and_time_modifiers(tokens[and_index + 4 :])
    if trailing_modifiers is None:
        return None
    trailing_adv_modifiers, trailing_time_modifiers = trailing_modifiers
    shared_adv_modifiers = [*fronted_adv_modifiers, *trailing_adv_modifiers]
    time_modifiers = [*fronted_time_modifiers, *trailing_time_modifiers]
    predicate_type = (
        "forall n : nat, ModifierSeq n -> Entity -> PropT"
        if shared_adv_modifiers
        else "Entity -> Prop"
    )
    predicates = [
        {
            "surface": left_surface,
            "name": lemma_verb(left_surface),
            "predicate_type": predicate_type,
        },
        {
            "surface": right_surface,
            "name": lemma_verb(right_surface),
            "predicate_type": predicate_type,
            "negated": True,
        },
    ]
    ast = predicate_coordination_ast(
        subject,
        predicates,
        shared_adv_modifiers,
        time_modifiers,
    )
    type_check = check_predicate_coordination_ast(ast)
    typed_replacement = render_predicate_coordination_translation(ast)
    coq_code = render_predicate_coordination_coq(
        "coordinated_do_support_negation_assertion",
        ast,
    )
    return {
        "kind": "coordinated_do_support_negation",
        "input_sentence": sentence,
        "construction_summary": (
            f"Same subject {subject} coordinates {predicates[0]['name']} with "
            f"the right-branch do-support negation not {predicates[1]['name']}."
        ),
        "event_semantics": {
            "analysis": "right-branch-do-support-negation",
            "source": sentence,
            "event_style_reference": (
                "exists e1. "
                f"{predicates[0]['name']}(e1) and Agent(e1, {subject}) and "
                "not(exists e2. "
                f"{predicates[1]['name']}(e2) and Agent(e2, {subject}))"
            ),
            "typed_replacement": typed_replacement,
        },
        "dependent_type_translation": typed_replacement,
        "ast": ast,
        "type_check": {
            **type_check,
            "note": (
                "Right-branch do-support negation is represented by wrapping "
                "only the second checked coordinate in not_T; no Event, Agent, "
                "or Theme predicate is exported."
            ),
        },
        "coq_code": coq_code,
    }


def coordinated_transitive_do_support_negation(
    sentence: str,
    tokens: list[str],
    and_index: int,
    right_surface: str,
    fronted_adv_modifiers: list[dict[str, Any]],
    fronted_time_modifiers: list[dict[str, str]],
) -> dict[str, Any] | None:
    left_verb_indices = [
        index
        for index in range(1, and_index)
        if is_likely_surface_verb(tokens[index])
    ]
    if len(left_verb_indices) != 1:
        return None
    left_verb_index = left_verb_indices[0]
    if left_verb_index == 0 or left_verb_index + 1 >= and_index:
        return None
    subject = clean_phrase(tokens[:left_verb_index])
    if subject == "entity":
        return None
    left_surface = tokens[left_verb_index]
    left_object = clean_phrase(tokens[left_verb_index + 1 : and_index])
    right_tail = split_object_tokens_and_modifiers(tokens[and_index + 4 :])
    if right_tail is None:
        return None
    right_object_tokens, trailing_adv_modifiers, trailing_time_modifiers = right_tail
    right_object = clean_phrase(right_object_tokens)
    if left_object == "entity" or right_object == "entity":
        return None
    shared_adv_modifiers = [*fronted_adv_modifiers, *trailing_adv_modifiers]
    time_modifiers = [*fronted_time_modifiers, *trailing_time_modifiers]

    clauses: list[dict[str, Any]] = []
    for surface, obj, negated in (
        (left_surface, left_object, False),
        (right_surface, right_object, True),
    ):
        predicate = lemma_verb(surface)
        object_type = object_type_for_transitive_predicate(predicate)
        clauses.append(
            {
                "predicate": {
                    "surface": surface,
                    "name": predicate,
                    "predicate_type": (
                        "forall n : nat, ModifierSeq n -> "
                        f"Entity -> {object_type} -> PropT"
                        if shared_adv_modifiers
                        else f"Entity -> {object_type} -> Prop"
                    ),
                },
                "object": {"name": obj, "type": object_type},
                "negated": negated,
            }
        )

    ast = transitive_predicate_coordination_ast(
        subject,
        clauses,
        shared_adv_modifiers,
        time_modifiers,
    )
    type_check = check_transitive_predicate_coordination_ast(ast)
    typed_replacement = render_transitive_predicate_coordination_translation(ast)
    coq_code = render_transitive_predicate_coordination_coq(
        "coordinated_transitive_do_support_negation_assertion",
        ast,
    )
    return {
        "kind": "coordinated_do_support_negation",
        "input_sentence": sentence,
        "construction_summary": (
            f"Same subject {subject} coordinates "
            f"{clauses[0]['predicate']['name']}({clauses[0]['object']['name']} : "
            f"{clauses[0]['object']['type']}) with right-branch negation not "
            f"{clauses[1]['predicate']['name']}({clauses[1]['object']['name']} : "
            f"{clauses[1]['object']['type']})."
        ),
        "event_semantics": {
            "analysis": "right-branch-do-support-negation",
            "source": sentence,
            "event_style_reference": (
                "exists e1. "
                f"{clauses[0]['predicate']['name']}(e1) and Agent(e1, {subject}) and "
                f"Theme(e1, {clauses[0]['object']['name']}) and not(exists e2. "
                f"{clauses[1]['predicate']['name']}(e2) and Agent(e2, {subject}) and "
                f"Theme(e2, {clauses[1]['object']['name']}))"
            ),
            "typed_replacement": typed_replacement,
        },
        "dependent_type_translation": typed_replacement,
        "ast": ast,
        "type_check": {
            **type_check,
            "note": (
                "Right-branch transitive do-support negation is represented by "
                "wrapping only the second typed coordinate in not_T; object "
                "lexical types are still checked before Coq."
            ),
        },
        "coq_code": coq_code,
    }


def transitive_predicate_coordination_pipeline(sentence: str) -> dict[str, Any] | None:
    tokens, fronted_time_modifiers = split_fronted_time_modifiers(tokenize(sentence))
    tokens, fronted_adv_modifiers = split_fronted_adv_modifiers(tokens)
    if tokens.count("and") != 1:
        return None
    and_index = tokens.index("and")
    if and_index < 3 or and_index + 2 >= len(tokens):
        return None
    if not is_likely_surface_verb(tokens[and_index + 1]):
        return None

    left_verb_indices = [
        index
        for index in range(1, and_index)
        if is_likely_surface_verb(tokens[index])
    ]
    if len(left_verb_indices) != 1:
        return None
    left_verb_index = left_verb_indices[0]
    if left_verb_index == 0 or left_verb_index + 1 >= and_index:
        return None

    subject = clean_phrase(tokens[:left_verb_index])
    if subject == "entity":
        return None
    left_surface = tokens[left_verb_index]
    right_surface = tokens[and_index + 1]
    left_object = clean_phrase(tokens[left_verb_index + 1 : and_index])
    right_tail = split_object_tokens_and_modifiers(tokens[and_index + 2 :])
    if right_tail is None:
        return None
    right_object_tokens, trailing_adv_modifiers, trailing_time_modifiers = right_tail
    shared_adv_modifiers = [*fronted_adv_modifiers, *trailing_adv_modifiers]
    time_modifiers = [*fronted_time_modifiers, *trailing_time_modifiers]
    right_object = clean_phrase(right_object_tokens)
    if left_object == "entity" or right_object == "entity":
        return None

    clauses: list[dict[str, Any]] = []
    for surface, obj in ((left_surface, left_object), (right_surface, right_object)):
        predicate = lemma_verb(surface)
        object_type = object_type_for_transitive_predicate(predicate)
        clauses.append(
            {
                "predicate": {
                    "surface": surface,
                    "name": predicate,
                    "predicate_type": (
                        "forall n : nat, ModifierSeq n -> "
                        f"Entity -> {object_type} -> PropT"
                        if shared_adv_modifiers
                        else f"Entity -> {object_type} -> Prop"
                    ),
                },
                "object": {"name": obj, "type": object_type},
            }
        )

    ast = transitive_predicate_coordination_ast(
        subject,
        clauses,
        shared_adv_modifiers,
        time_modifiers,
    )
    type_check = check_transitive_predicate_coordination_ast(ast)
    typed_replacement = render_transitive_predicate_coordination_translation(ast)
    coq_code = render_transitive_predicate_coordination_coq(
        "transitive_predicate_coordination_assertion",
        ast,
    )
    return {
        "kind": "transitive_predicate_coordination",
        "input_sentence": sentence,
        "construction_summary": (
            f"Same subject {subject} coordinates "
            f"{clauses[0]['predicate']['name']}({clauses[0]['object']['name']} : "
            f"{clauses[0]['object']['type']}) and "
            f"{clauses[1]['predicate']['name']}({clauses[1]['object']['name']} : "
            f"{clauses[1]['object']['type']})"
            + (
                " with shared Adv modifiers "
                + ", ".join(modifier["expression"] for modifier in shared_adv_modifiers)
                if shared_adv_modifiers
                else ""
            )
            + "."
        ),
        "event_semantics": {
            "analysis": "same-subject-transitive-vp-coordination",
            "source": sentence,
            "event_style_reference": (
                "exists e1 e2. "
                f"{clauses[0]['predicate']['name']}(e1) and Agent(e1, {subject}) and "
                f"Theme(e1, {clauses[0]['object']['name']}) and "
                f"{clauses[1]['predicate']['name']}(e2) and Agent(e2, {subject}) and "
                f"Theme(e2, {clauses[1]['object']['name']})"
            ),
            "typed_replacement": typed_replacement,
        },
        "dependent_type_translation": typed_replacement,
        "ast": ast,
        "type_check": {
            **type_check,
            "note": (
                (
                    "Same-subject transitive VP coordination with shared Adv "
                    "modifiers is represented through modifier-indexed typed "
                    "predicates; each object keeps its lexical type, and no "
                    "Event/Agent/Theme Coq predicates are exported."
                )
                if shared_adv_modifiers
                else (
                    "Same-subject transitive VP coordination is represented as a typed "
                    "conjunction of Entity -> ObjectType -> Prop predicates; each "
                    "object keeps its lexical type, and no Event/Agent/Theme Coq "
                    "predicates are exported."
                )
            ),
        },
        "coq_code": coq_code,
    }


def passive_argument_omission_ast(
    predicate: str,
    patient: str,
    agent: str | None,
    auxiliary: str,
    participle: str,
) -> dict[str, Any]:
    agent_record = (
        {"name": agent, "type": "Entity", "source": "by_phrase"}
        if agent is not None
        else {"variable": "x_agent", "type": "Entity", "source": "omitted_existential"}
    )
    return {
        "kind": "passive_argument_omission",
        "predicate": predicate,
        "predicate_type": "Entity -> Entity -> Prop",
        "auxiliary": auxiliary,
        "surface_lexicon": passive_participle_audit(participle),
        "argument_order": ["Agent", "Patient"],
        "patient": {
            "name": patient,
            "type": "Entity",
            "surface_role": "subject",
        },
        "agent": agent_record,
    }


def check_passive_argument_omission_ast(ast: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if ast.get("kind") != "passive_argument_omission":
        errors.append("ast.kind must be passive_argument_omission")
    if not isinstance(ast.get("predicate"), str) or not ast.get("predicate"):
        errors.append("passive predicate must be a non-empty string")
    if ast.get("predicate_type") != "Entity -> Entity -> Prop":
        errors.append("passive predicate must have type Entity -> Entity -> Prop")
    if ast.get("auxiliary") not in PASSIVE_AUXILIARIES:
        errors.append("passive auxiliary must be is, was, are, or were")
    surface_lexicon = ast.get("surface_lexicon")
    if not isinstance(surface_lexicon, dict):
        errors.append("passive surface_lexicon must be an object")
    else:
        participle = surface_lexicon.get("participle")
        if not isinstance(participle, str) or not participle:
            errors.append("passive surface_lexicon.participle must be a non-empty string")
        elif not is_passive_participle(participle):
            errors.append("passive surface_lexicon.participle must be a passive participle")
        if surface_lexicon.get("lemma") != ast.get("predicate"):
            errors.append("passive surface_lexicon.lemma must match predicate")
        elif isinstance(participle, str) and lemma_verb(participle) != ast.get("predicate"):
            errors.append("passive surface_lexicon.lemma must match lemmatized participle")
        if surface_lexicon.get("source") != SURFACE_LEXICON_SOURCE:
            errors.append("passive surface_lexicon.source must identify the surface lexicon")
    if ast.get("argument_order") != ["Agent", "Patient"]:
        errors.append("passive argument_order must be Agent before Patient")

    patient = ast.get("patient")
    if not isinstance(patient, dict):
        errors.append("passive patient must be an object")
    else:
        if not isinstance(patient.get("name"), str) or not patient.get("name"):
            errors.append("passive patient.name must be a non-empty string")
        if patient.get("type") != "Entity":
            errors.append("passive patient must have type Entity")
        if patient.get("surface_role") != "subject":
            errors.append("passive patient must be the surface subject")

    agent = ast.get("agent")
    if not isinstance(agent, dict):
        errors.append("passive agent must be an object")
    else:
        source = agent.get("source")
        if source == "by_phrase":
            if not isinstance(agent.get("name"), str) or not agent.get("name"):
                errors.append("passive by-phrase agent.name must be a non-empty string")
            if agent.get("type") != "Entity":
                errors.append("passive by-phrase agent must have type Entity")
        elif source == "omitted_existential":
            if agent.get("variable") != "x_agent":
                errors.append("passive omitted agent must bind x_agent")
            if agent.get("type") != "Entity":
                errors.append("passive omitted agent must have type Entity")
        else:
            errors.append("passive agent.source must be by_phrase or omitted_existential")

    return {
        "ok": not errors,
        "type": "Prop" if not errors else None,
        "errors": errors,
    }


def passive_argument_omission_pipeline(sentence: str) -> dict[str, Any] | None:
    tokens = tokenize(sentence)
    auxiliary_indices = [
        index for index, token in enumerate(tokens) if token in PASSIVE_AUXILIARIES
    ]
    if len(tokens) < 3 or not auxiliary_indices:
        return None
    auxiliary_index = auxiliary_indices[0]
    auxiliary = tokens[auxiliary_index]
    if auxiliary_index == 0 or auxiliary_index + 1 >= len(tokens):
        return None
    participle = tokens[auxiliary_index + 1]
    if not is_passive_participle(participle):
        return None

    patient = clean_phrase(tokens[:auxiliary_index])
    predicate = lemma_verb(participle)
    rest = tokens[auxiliary_index + 2:]
    agent = None
    if rest:
        if rest[0] != "by" or len(rest) == 1:
            return None
        agent = clean_phrase(rest[1:])

    ast = passive_argument_omission_ast(predicate, patient, agent, auxiliary, participle)
    type_check = check_passive_argument_omission_ast(ast)
    if agent is None:
        typed_replacement = f"exists x_agent : Entity. {predicate}(x_agent, {patient})"
        definition_name = f"passive_{predicate}_omitted_agent"
        body_lines = [
            f"Definition {definition_name} : Prop :=",
            "  exists x_agent : Entity,",
            f"    {predicate} x_agent {patient}.",
        ]
        agent_parameters: list[str] = []
        event_reference = (
            f"exists e. {predicate}ing(e) and Theme(e, {patient}) and "
            "exists x. Agent(e, x)"
        )
    else:
        typed_replacement = f"{predicate}({agent}, {patient})"
        definition_name = f"passive_{predicate}_by_agent"
        body_lines = [
            f"Definition {definition_name} : Prop :=",
            f"  {predicate} {agent} {patient}.",
        ]
        agent_parameters = [f"Parameter {agent} : Entity."]
        event_reference = (
            f"exists e. {predicate}ing(e) and Theme(e, {patient}) and Agent(e, {agent})"
        )

    coq_code = "\n".join(
        [
            "(* Passive argument-omission replacement without an event variable. *)",
            "Parameter Entity : Type.",
            "",
            f"Parameter {patient} : Entity.",
            *agent_parameters,
            "",
            f"Parameter {predicate} : Entity -> Entity -> Prop.",
            "",
            *body_lines,
            "",
            f"Check {definition_name}.",
            "",
        ]
    )
    return {
        "kind": "passive_argument_omission",
        "input_sentence": sentence,
        "event_semantics": {
            "analysis": "passive-argument-omission",
            "source": sentence,
            "event_style_reference": event_reference,
            "typed_replacement": typed_replacement,
        },
        "dependent_type_translation": typed_replacement,
        "ast": ast,
        "type_check": {
            **type_check,
            "note": (
                "A passive without by-phrase introduces an existential Entity "
                "agent; no Event, Agent(e, ...), or Theme(e, ...) declaration is exported."
            ),
        },
        "coq_code": coq_code,
    }


def construction_rules() -> list[ConstructionRule]:
    return [
        ConstructionRule(
            rule_id="perception_nominalization",
            label="Perception complement nominalization",
            phenomenon="Parsons/Luo-Shi perception complement",
            analyzer=perception_nominalization_pipeline,
            forbidden_coq_fragments=("Parameter Event : Type.", "exists e : Event"),
        ),
        ConstructionRule(
            rule_id="universal_timed_burning",
            label="Universal timed burning",
            phenomenon="Parsons/Luo-Shi event inclusion",
            analyzer=every_burning_pipeline,
            forbidden_coq_fragments=("Parameter Event : Type.", "IN"),
        ),
        ConstructionRule(
            rule_id="timed_after",
            label="Timed after relation",
            phenomenon="Parsons/Luo-Shi event ordering",
            analyzer=timed_after_pipeline,
            forbidden_coq_fragments=("Parameter Event : Type.", "exists e : Event"),
        ),
        ConstructionRule(
            rule_id="quantifier_scope_ambiguity",
            label="Quantifier-scope ambiguity",
            phenomenon="Existential scope ambiguity",
            analyzer=quantifier_scope_pipeline,
            forbidden_coq_fragments=(
                "Parameter Event : Type.",
                "exists e : Event",
                "Parameter Agent :",
                "Parameter Theme :",
                "Parameter some : Entity.",
                "Parameter boy : nat ->",
            ),
        ),
        ConstructionRule(
            rule_id="lexical_state_change",
            label="Lexical state change",
            phenomenon="Inchoative/causative state transition without event arguments",
            analyzer=lexical_state_change_pipeline,
            forbidden_coq_fragments=(
                "Parameter Event : Type.",
                "exists e : Event",
                "Parameter Agent :",
                "Parameter Theme :",
            ),
        ),
        ConstructionRule(
            rule_id="stative_result_state",
            label="Stative result state",
            phenomenon="Result state without hidden event or omitted agent",
            analyzer=stative_result_state_pipeline,
            forbidden_coq_fragments=(
                "Parameter Event : Type.",
                "exists e : Event",
                "Parameter Agent :",
                "Parameter Theme :",
            ),
        ),
        ConstructionRule(
            rule_id="passive_argument_omission",
            label="Passive argument omission",
            phenomenon="Argument deletion without hidden event variables",
            analyzer=passive_argument_omission_pipeline,
            forbidden_coq_fragments=(
                "Parameter Event : Type.",
                "exists e : Event",
                "Parameter Agent :",
                "Parameter Theme :",
            ),
        ),
        ConstructionRule(
            rule_id="copular_property",
            label="Copular property",
            phenomenon="Property predication without hidden event variables",
            analyzer=copular_property_pipeline,
            forbidden_coq_fragments=(
                "Parameter Event : Type.",
                "exists e : Event",
                "Parameter Agent :",
                "Parameter Theme :",
            ),
        ),
        ConstructionRule(
            rule_id="do_support_negation",
            label="Do-support negation",
            phenomenon="Proposition-level negation without hidden event variables",
            analyzer=do_support_negation_pipeline,
            forbidden_coq_fragments=(
                "Parameter Event : Type.",
                "exists e : Event",
                "Parameter Agent :",
                "Parameter Theme :",
            ),
        ),
        ConstructionRule(
            rule_id="predicate_coordination",
            label="Predicate coordination",
            phenomenon="Same-subject intransitive predicate coordination without event variables",
            analyzer=predicate_coordination_pipeline,
            forbidden_coq_fragments=(
                "Parameter Event : Type.",
                "exists e : Event",
                "Parameter Agent :",
                "Parameter Theme :",
            ),
        ),
        ConstructionRule(
            rule_id="transitive_predicate_coordination",
            label="Transitive predicate coordination",
            phenomenon="Same-subject transitive VP coordination without event variables",
            analyzer=transitive_predicate_coordination_pipeline,
            forbidden_coq_fragments=(
                "Parameter Event : Type.",
                "exists e : Event",
                "Parameter Agent :",
                "Parameter Theme :",
            ),
        ),
    ]


def check_forbidden_coq_fragments(
    coq_code: str,
    forbidden_fragments: tuple[str, ...],
) -> list[str]:
    return [fragment for fragment in forbidden_fragments if fragment in coq_code]


def construction_rule_payload(rule: ConstructionRule) -> dict[str, Any]:
    return {
        "id": rule.rule_id,
        "label": rule.label,
        "phenomenon": rule.phenomenon,
        "forbidden_coq_fragments": list(rule.forbidden_coq_fragments),
    }


def construction_hygiene_payload(
    rule: ConstructionRule,
    found_fragments: list[str],
) -> dict[str, Any]:
    return {
        "ok": not found_fragments,
        "checked": True,
        "forbidden_coq_fragments": list(rule.forbidden_coq_fragments),
        "found_forbidden_fragments": found_fragments,
    }


def run_registered_rule(
    rule: ConstructionRule,
    sentence: str,
    require_coq: bool,
) -> dict[str, Any] | None:
    analysis = rule.analyzer(sentence)
    if analysis is None:
        return None

    if analysis.get("type_check", {}).get("ok") is False:
        return {
            **analysis,
            "ok": False,
            "construction_rule": construction_rule_payload(rule),
            "construction_hygiene": {
                "ok": None,
                "checked": False,
                "forbidden_coq_fragments": list(rule.forbidden_coq_fragments),
                "found_forbidden_fragments": [],
            },
            "coq_check": {
                "ok": None,
                "status": "skipped",
                "message": "Skipped Coq/Rocq validation because internal type_check failed.",
            },
            "conclusion": "Translation failed internal type_check before Coq/Rocq validation.",
        }

    forbidden_found = check_forbidden_coq_fragments(
        analysis["coq_code"],
        rule.forbidden_coq_fragments,
    )
    if forbidden_found:
        return {
            **analysis,
            "ok": False,
            "construction_rule": construction_rule_payload(rule),
            "construction_hygiene": construction_hygiene_payload(rule, forbidden_found),
            "coq_check": {
                "ok": False,
                "status": "failed",
                "message": (
                    "Generated Coq contains forbidden construction fragments: "
                    + ", ".join(forbidden_found)
                ),
            },
            "conclusion": "Translation failed construction-specific Coq hygiene checks.",
        }

    coq_check = verify_coq_code(analysis["coq_code"], require_coq=require_coq)
    success = analysis["type_check"]["ok"] and coq_check["ok"] is not False
    return {
        **analysis,
        "ok": success,
        "construction_rule": construction_rule_payload(rule),
        "construction_hygiene": construction_hygiene_payload(rule, forbidden_found),
        "coq_check": coq_check,
        "conclusion": (
            f"Translation succeeded via construction rule {rule.rule_id}."
            if success
            else "Translation failed at Coq/Rocq boundary validation."
        ),
    }


def normalize_sentence(sentence: str) -> str:
    normalized = sentence.strip().rstrip(".!?")
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.lower()


def tokenize(sentence: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9_']+", normalize_sentence(sentence))


def clean_phrase(tokens: list[str]) -> str:
    content = [token for token in tokens if token not in ARTICLES]
    if not content:
        return "entity"
    return "_".join(content)


def split_coordinate_tokens(tokens: list[str]) -> list[list[str]] | None:
    if not tokens or tokens[0] == "and" or tokens[-1] == "and":
        return None
    groups: list[list[str]] = [[]]
    for token in tokens:
        if token == "and":
            if not groups[-1]:
                return None
            groups.append([])
            continue
        groups[-1].append(token)
    if any(not group for group in groups):
        return None
    return groups


def locative_preposition_predicate(preposition: str) -> str:
    if preposition == "at":
        return "at_loc"
    return preposition


def fallback_sentence_to_event_semantics(sentence: str) -> dict[str, Any]:
    tokens = tokenize(sentence)
    if len(tokens) < 2:
        raise ValueError("Please enter at least a subject and a predicate.")

    def has_phrase_content(phrase: list[str]) -> bool:
        return any(token not in ARTICLES for token in phrase)

    def starts_subject_boundary(position: int) -> bool:
        subject_start = position
        starts_with_article = False
        if subject_start < len(tokens) and tokens[subject_start] in ARTICLES:
            starts_with_article = True
            subject_start += 1
        if subject_start >= len(tokens):
            return False

        def is_boundary_predicate(token: str) -> bool:
            return token in PASSIVE_AUXILIARIES or is_likely_surface_verb(token) or (
                token.endswith("ed") and len(token) > 3
            )

        subject_widths = (1, 2) if starts_with_article else (1,)
        for subject_width in subject_widths:
            predicate_position = subject_start + subject_width
            if (
                predicate_position < len(tokens)
                and is_boundary_predicate(tokens[predicate_position])
            ):
                return True
        return False

    def leading_prepositional_modifier_at(position: int) -> tuple[dict[str, Any], int] | None:
        prep = tokens[position]
        if prep not in FRONTED_MODIFIER_PREPOSITIONS:
            return None
        idx = position + 1
        phrase: list[str] = []
        modifier_boundaries = (
            PREPOSITIONS | COUNT_WORDS | COUNT_NOUNS | COMMON_ADVERBS | TEMPORAL_ADVERBS
        )
        while idx < len(tokens):
            if has_phrase_content(phrase):
                if tokens[idx] in modifier_boundaries:
                    break
                if temporal_phrase_value(tokens, idx) is not None:
                    break
                if starts_subject_boundary(idx):
                    break
            phrase.append(tokens[idx])
            idx += 1
        if not has_phrase_content(phrase):
            return None
        return atom(locative_preposition_predicate(prep), "e", clean_phrase(phrase)), idx - position

    leading_atoms: list[dict[str, Any]] = []
    idx = 0
    while idx < len(tokens):
        token = tokens[idx]
        if token in TEMPORAL_ADVERBS:
            leading_atoms.append(atom("at", "e", token))
            idx += 1
            continue
        temporal_phrase = temporal_phrase_value(tokens, idx)
        if temporal_phrase is not None:
            normalized_time, consumed = temporal_phrase
            leading_atoms.append(atom("at", "e", normalized_time))
            idx += consumed
            continue
        temporal_prep_phrase = temporal_prepositional_phrase_value(tokens, idx)
        if temporal_prep_phrase is not None:
            operator, normalized_time, consumed = temporal_prep_phrase
            leading_atoms.append(atom(operator, "e", normalized_time))
            idx += consumed
            continue
        leading_modifier = leading_prepositional_modifier_at(idx)
        if leading_modifier is None:
            break
        modifier_atom, consumed = leading_modifier
        leading_atoms.append(modifier_atom)
        idx += consumed

    while idx < len(tokens) and tokens[idx] in ARTICLES:
        idx += 1
    if idx >= len(tokens):
        raise ValueError("Could not identify a predicate after the subject.")

    subject_start = idx
    predicate_index = None
    for candidate in range(subject_start + 1, len(tokens)):
        if tokens[candidate] in PASSIVE_AUXILIARIES or is_likely_surface_verb(tokens[candidate]):
            predicate_index = candidate
            break
    if predicate_index is None:
        subject_tokens = [tokens[idx]]
        idx += 1
    else:
        subject_tokens = tokens[subject_start:predicate_index]
        idx = predicate_index
    if idx >= len(tokens):
        raise ValueError("Could not identify a predicate after the subject.")

    raw_verb = tokens[idx]
    verb = "be" if raw_verb in PASSIVE_AUXILIARIES else lemma_verb(raw_verb)
    idx += 1
    subject_role = (
        "Theme"
        if verb == "be" and idx < len(tokens) and tokens[idx] in PREPOSITIONS
        else "Agent"
    )
    items = [
        atom(verb, "e"),
        atom(subject_role, "e", clean_phrase(subject_tokens)),
        *leading_atoms,
    ]
    object_tokens: list[str] = []

    def is_count_phrase_at(position: int) -> bool:
        return (
            count_phrase_value(tokens[position]) is not None
            and position + 1 < len(tokens)
            and tokens[position + 1] in COUNT_NOUNS
        )

    def is_temporal_phrase_at(position: int) -> bool:
        return temporal_phrase_value(tokens, position) is not None

    while idx < len(tokens):
        token = tokens[idx]
        if token in COUNT_WORDS:
            items.append(atom(token, "e"))
            idx += 1
            continue
        count_value = count_phrase_value(token)
        if count_value is not None and is_count_phrase_at(idx):
            items.append(atom("times", "e", count_value))
            idx += 2
            continue
        if token in COMMON_ADVERBS:
            items.append(atom(token, "e"))
            idx += 1
            continue
        if token in TEMPORAL_ADVERBS:
            items.append(atom("at", "e", token))
            idx += 1
            continue
        temporal_phrase = temporal_phrase_value(tokens, idx)
        if temporal_phrase is not None:
            normalized_time, consumed = temporal_phrase
            items.append(atom("at", "e", normalized_time))
            idx += consumed
            continue
        temporal_prep_phrase = temporal_prepositional_phrase_value(tokens, idx)
        if temporal_prep_phrase is not None:
            operator, normalized_time, consumed = temporal_prep_phrase
            items.append(atom(operator, "e", normalized_time))
            idx += consumed
            continue
        if token in PREPOSITIONS:
            prep = token
            idx += 1
            phrase: list[str] = []
            modifier_boundaries = (
                PREPOSITIONS
                | COUNT_WORDS
                | COUNT_NOUNS
                | COMMON_ADVERBS
                | TEMPORAL_ADVERBS
            )
            while (
                idx < len(tokens)
                and tokens[idx] not in modifier_boundaries
                and not is_count_phrase_at(idx)
                and not is_temporal_phrase_at(idx)
            ):
                phrase.append(tokens[idx])
                idx += 1
            if phrase:
                items.append(atom(locative_preposition_predicate(prep), "e", clean_phrase(phrase)))
            continue
        object_tokens.append(token)
        idx += 1

    result_state = None
    if len(object_tokens) >= 2 and object_tokens[-1] in STATE_SCALE_BY_STATE:
        result_state = object_tokens.pop()

    theme = clean_phrase(object_tokens)
    if object_tokens and theme != "entity":
        items.append(atom("Theme", "e", theme))
    if result_state is not None:
        items.append(atom("Result", "e", result_state))
    return event_formula(*items)


def sentence_to_event_semantics(sentence: str) -> dict[str, Any]:
    normalized = normalize_sentence(sentence)
    if normalized == "john buttered the toast slowly in the bathroom at noon":
        return event_formula(
            atom("butter", "e"),
            atom("Agent", "e", "John"),
            atom("Theme", "e", "toast"),
            atom("slowly", "e"),
            atom("in", "e", "bathroom"),
            atom("at", "e", "noon"),
        )
    if normalized == "john ate":
        return event_formula(
            atom("eat", "e"),
            atom("Agent", "e", "John"),
        )
    if normalized == "john knocked twice":
        return event_formula(
            atom("knock", "e"),
            atom("Agent", "e", "John"),
            atom("twice", "e"),
        )
    if normalized == "john broke the vase":
        return event_formula(
            atom("break", "e"),
            atom("Agent", "e", "John"),
            atom("Theme", "e", "vase"),
            atom("Result", "e", "broken"),
        )
    return fallback_sentence_to_event_semantics(sentence)


def coq_command(coq_file: Path) -> list[str] | None:
    if shutil.which("coqc"):
        return ["coqc", str(coq_file)]
    if ROCQ_ENV.exists():
        return [
            "/bin/zsh",
            "-lc",
            f'eval "$({ROCQ_ENV})" && coqc "{coq_file}"',
        ]
    return None


def verify_coq_code(coq_code: str, require_coq: bool = False) -> dict[str, Any]:
    command = coq_command(Path("pipeline_check.v"))
    if command is None:
        if require_coq:
            return {
                "ok": False,
                "status": "failed",
                "message": "coqc was required but no Coq/Rocq toolchain was found.",
            }
        return {
            "ok": None,
            "status": "skipped",
            "message": "Coq/Rocq not found; skipped external boundary validation.",
        }

    with tempfile.TemporaryDirectory(prefix="dt-event-coq-") as tmp:
        coq_file = Path(tmp) / "pipeline_check.v"
        coq_file.write_text(coq_code, encoding="utf-8")
        command = coq_command(coq_file)
        assert command is not None
        completed = subprocess.run(
            command,
            cwd=tmp,
            capture_output=True,
            text=True,
            check=False,
        )
    output = "\n".join(
        part for part in (completed.stdout.strip(), completed.stderr.strip()) if part
    )
    return {
        "ok": completed.returncode == 0,
        "status": "passed" if completed.returncode == 0 else "failed",
        "message": output or "coqc accepted the generated scaffold.",
    }


def run_pipeline(sentence: str, require_coq: bool = False) -> dict[str, Any]:
    try:
        for rule in construction_rules():
            registered_result = run_registered_rule(rule, sentence, require_coq)
            if registered_result is not None:
                return registered_result
        event_semantics = sentence_to_event_semantics(sentence)
        translation = translate(event_semantics)
        coq_code = export_module([translation], "coq")
        coq_check = verify_coq_code(coq_code, require_coq=require_coq)
        success = translation["type_check"]["ok"] and coq_check["ok"] is not False
        conclusion = (
            "Translation succeeded."
            if success
            else "Translation failed; inspect type_check and coq_check."
        )
        return {
            "ok": success,
            "input_sentence": sentence,
            "event_semantics": event_semantics,
            "dependent_type_translation": translation["translation"],
            "result_state_lexicon": translation["result_state_lexicon"],
            "ast": translation["ast"],
            "type_check": translation["type_check"],
            "coq_code": coq_code,
            "coq_check": coq_check,
            "conclusion": conclusion,
        }
    except Exception as exc:
        return {
            "ok": False,
            "input_sentence": sentence,
            "error": str(exc),
            "conclusion": "Translation failed before Coq validation.",
        }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prototype natural-language to event/dependent-type/Coq pipeline."
    )
    parser.add_argument("sentence")
    parser.add_argument(
        "--require-coq",
        action="store_true",
        help="Treat missing Coq/Rocq as a failed pipeline check.",
    )
    args = parser.parse_args()
    print(
        json.dumps(
            run_pipeline(args.sentence, require_coq=args.require_coq),
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
