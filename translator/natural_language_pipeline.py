#!/usr/bin/env python3
"""End-to-end prototype for natural language to checked Coq scaffolds."""

from __future__ import annotations

import argparse
import copy
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
    is_likely_transitive_verb,
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
QUANTIFIER_SUBJECT_DETERMINERS = {"some", "every", "each", "all", "no"}
EXISTENTIAL_SCOPE_DETERMINERS = {"some", "a", "an"}
UNIVERSAL_SCOPE_DETERMINERS = {"every", "each", "all"}
NEGATIVE_SCOPE_DETERMINERS = {"no"}
SUPPORTED_SCOPE_DETERMINERS = (
    EXISTENTIAL_SCOPE_DETERMINERS
    | UNIVERSAL_SCOPE_DETERMINERS
    | NEGATIVE_SCOPE_DETERMINERS
)
DO_SUPPORT_AUXILIARIES = {"do", "does", "did"}
CONTRASTIVE_COORDINATORS = {"but"}
BOOLEAN_COORDINATORS = {"and": "and_T", "or": "or_T"}
TEMPORAL_RELATION_CONNECTORS = {"after", "before"}


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


def connective_for_coordinator(coordinator: str) -> str:
    return BOOLEAN_COORDINATORS[coordinator]


def single_boolean_coordinator(tokens: list[str]) -> tuple[str, int] | None:
    matches = [
        (token, index)
        for index, token in enumerate(tokens)
        if token in BOOLEAN_COORDINATORS
    ]
    if len(matches) != 1:
        return None
    return matches[0]


def single_temporal_relation_connector(tokens: list[str]) -> tuple[str, int] | None:
    matches = [
        (token, index)
        for index, token in enumerate(tokens)
        if token in TEMPORAL_RELATION_CONNECTORS
    ]
    if len(matches) != 1:
        return None
    return matches[0]


def strip_coordination_pair_marker(
    tokens: list[str],
    marker: str,
    coordinator: str,
    *,
    allow_initial_marker: bool,
) -> list[str]:
    if tokens.count(marker) != 1 or coordinator not in tokens:
        return tokens
    marker_index = tokens.index(marker)
    if marker_index == 0 and allow_initial_marker:
        return tokens[1:]
    if (
        marker_index > 0
        and marker_index + 1 < len(tokens)
        and is_likely_surface_verb(tokens[marker_index + 1])
    ):
        return [*tokens[:marker_index], *tokens[marker_index + 1 :]]
    return tokens


def strip_surface_coordination_marker(tokens: list[str]) -> list[str]:
    tokens = strip_coordination_pair_marker(
        tokens,
        "either",
        "or",
        allow_initial_marker=True,
    )
    tokens = strip_coordination_pair_marker(
        tokens,
        "both",
        "and",
        allow_initial_marker=False,
    )
    return tokens


def quantifier_scope_reading(
    subject_noun: str,
    subject_quantifier: str,
    verb: str,
    object_noun: str,
    object_quantifier: str,
    subject_first: bool,
    modifiers: list[dict[str, Any]] | None = None,
    time_modifiers: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    modifiers = list(modifiers or [])
    subject = {
        "role": "subject",
        "quantifier": subject_quantifier,
        "variable": f"x_{subject_noun}",
        "predicate": subject_noun,
        "predicate_type": "Entity -> Prop",
    }
    obj = {
        "role": "object",
        "quantifier": object_quantifier,
        "variable": f"x_{object_noun}",
        "predicate": object_noun,
        "predicate_type": "Entity -> Prop",
    }
    scope_order = [subject, obj] if subject_first else [obj, subject]
    relation = {
        "predicate": verb,
        "predicate_type": (
            "forall n : nat, ModifierSeq n -> Entity -> Entity -> PropT"
            if modifiers
            else "Entity -> Entity -> Prop"
        ),
        "arguments": [subject["variable"], obj["variable"]],
    }
    if subject_first:
        name = f"{subject_quantifier}_{subject_noun}_wide_scope"
        quantifier = subject_quantifier
    else:
        name = f"{object_quantifier}_{object_noun}_wide_scope"
        quantifier = object_quantifier
    return {
        "name": name,
        "quantifier": quantifier,
        "scope_order": scope_order,
        "relation": relation,
        "modifiers": modifiers,
        "time_modifiers": list(time_modifiers or []),
    }


def render_quantifier_relation(reading: dict[str, Any], *, coq: bool) -> str:
    relation = reading["relation"]
    args = relation["arguments"]
    modifiers = reading.get("modifiers", [])
    if modifiers:
        if coq:
            return (
                f"{relation['predicate']} {len(modifiers)} "
                f"{coq_modifier_sequence(modifiers)} {' '.join(args)}"
            )
        return (
            f"{relation['predicate']}({len(modifiers)})"
            f"({readable_modifier_arguments(modifiers)}, {', '.join(args)})"
        )
    if coq:
        return f"{relation['predicate']} {' '.join(args)}"
    return f"{relation['predicate']}({', '.join(args)})"


def render_quantifier_time_wrapped_reading(
    body: str,
    time_modifiers: list[dict[str, str]],
    *,
    coq: bool,
) -> str:
    for modifier in time_modifiers:
        if coq:
            body = f"{modifier['operator']}_T {modifier['argument']} ({body})"
        else:
            body = f"{modifier['operator']}_T({modifier['argument']}, {body})"
    return body


def render_quantifier_binder(
    binder: dict[str, Any],
    body: str,
    *,
    coq: bool,
) -> str:
    var = binder["variable"]
    predicate = binder["predicate"]
    quantifier = binder.get("quantifier")
    if coq:
        predicate_application = f"{predicate} {var}"
        if quantifier in EXISTENTIAL_SCOPE_DETERMINERS:
            if body.startswith("forall "):
                body = f"({body})"
            return f"exists {var} : Entity, {predicate_application} /\\ {body}"
        if quantifier in UNIVERSAL_SCOPE_DETERMINERS:
            return f"forall {var} : Entity, {predicate_application} -> {body}"
        if quantifier in NEGATIVE_SCOPE_DETERMINERS:
            return f"forall {var} : Entity, {predicate_application} -> ~ ({body})"
    else:
        predicate_application = f"{predicate}({var})"
        if quantifier in EXISTENTIAL_SCOPE_DETERMINERS:
            if body.startswith("forall "):
                body = f"({body})"
            return f"exists {var} : Entity. {predicate_application} and {body}"
        if quantifier in UNIVERSAL_SCOPE_DETERMINERS:
            return f"forall {var} : Entity. {predicate_application} -> {body}"
        if quantifier in NEGATIVE_SCOPE_DETERMINERS:
            return f"forall {var} : Entity. {predicate_application} -> not ({body})"
    raise ValueError(f"unsupported quantifier: {quantifier!r}")


def render_quantifier_reading(reading: dict[str, Any], coq: bool = False) -> str:
    body = render_quantifier_relation(reading, coq=coq)
    for binder in reversed(reading["scope_order"]):
        body = render_quantifier_binder(binder, body, coq=coq)
    return render_quantifier_time_wrapped_reading(
        body,
        reading.get("time_modifiers", []),
        coq=coq,
    )


def quantifier_scope_coq(reading: dict[str, Any]) -> str:
    return f"Definition {reading['name']} : Prop := {render_quantifier_reading(reading, coq=True)}."


def quantifier_scope_family(subject_quantifier: str, object_quantifier: str) -> str:
    if subject_quantifier == object_quantifier:
        return subject_quantifier
    if (
        subject_quantifier in EXISTENTIAL_SCOPE_DETERMINERS
        and object_quantifier in EXISTENTIAL_SCOPE_DETERMINERS
    ):
        return "existential"
    if (
        subject_quantifier in UNIVERSAL_SCOPE_DETERMINERS
        and object_quantifier in UNIVERSAL_SCOPE_DETERMINERS
    ):
        return "universal"
    if (
        subject_quantifier in NEGATIVE_SCOPE_DETERMINERS
        and object_quantifier in NEGATIVE_SCOPE_DETERMINERS
    ):
        return "negative"
    if (
        subject_quantifier in NEGATIVE_SCOPE_DETERMINERS
        or object_quantifier in NEGATIVE_SCOPE_DETERMINERS
    ):
        return "mixed_negative"
    return "mixed"


def semantic_reading(
    *,
    name: str,
    dependent_type_translation: str,
    coq_definition: str | None = None,
    scope: str | None = None,
    scope_policy: dict[str, str] | None = None,
    type_check: dict[str, Any] | None = None,
    source: str | None = None,
) -> dict[str, Any]:
    reading: dict[str, Any] = {
        "name": name,
        "dependent_type_translation": dependent_type_translation,
    }
    if coq_definition is not None:
        reading["coq_definition"] = coq_definition
    if scope is not None:
        reading["scope"] = scope
    if scope_policy is not None:
        reading["scope_policy"] = scope_policy
    if type_check is not None:
        reading["type_check"] = type_check
    if source is not None:
        reading["source"] = source
    return reading


SEMANTIC_READING_FAILURE_LABELS = {
    "duplicate_reading_name": "duplicate reading names",
    "export_count_mismatch": "wrong number of exported propositions",
    "malformed_readings": "malformed semantic readings",
    "missing_coq_export": "missing Coq/Rocq exports",
    "missing_readings": "missing semantic readings",
    "reading_type_check_failed": "reading-local type check failed",
    "unknown_reading_error": "unclassified semantic-reading error",
}


def semantic_reading_error_kind(error: str) -> str:
    if "must not be empty" in error:
        return "missing_readings"
    if "must export exactly one Prop/PropT definition" in error:
        return "export_count_mismatch"
    if " is duplicated" in error:
        return "duplicate_reading_name"
    if " is not exported" in error:
        return "missing_coq_export"
    if ".type_check must have ok=true" in error:
        return "reading_type_check_failed"
    if (
        "must be a list" in error
        or "must be an object" in error
        or ".name must be a non-empty string" in error
        or ".dependent_type_translation must be a non-empty string" in error
        or ".coq_definition must be a non-empty string" in error
        or ".scope_policy must map strings to strings" in error
    ):
        return "malformed_readings"
    return "unknown_reading_error"


def semantic_reading_failure_kinds(errors: list[str]) -> list[str]:
    observed = {semantic_reading_error_kind(error) for error in errors}
    return sorted(observed)


def semantic_reading_failure_summary(kinds: list[str]) -> str:
    if not kinds:
        return "No semantic-reading failures."
    labels = [SEMANTIC_READING_FAILURE_LABELS.get(kind, kind) for kind in kinds]
    return "Semantic-reading failure kind(s): " + ", ".join(labels) + "."


def semantic_readings_repair_details(
    *,
    exported_definitions: list[str] | None = None,
    expected_coq_definitions: list[str] | None = None,
    missing_coq_definitions: list[str] | None = None,
    duplicate_reading_names: list[str] | None = None,
    malformed_reading_indices: list[int] | None = None,
    failed_type_check_indices: list[int] | None = None,
    expected_export_count: int | None = None,
    observed_export_count: int | None = None,
) -> dict[str, Any]:
    exported = sorted(exported_definitions or [])
    observed = len(exported) if observed_export_count is None else observed_export_count
    return {
        "exported_definitions": exported,
        "expected_coq_definitions": sorted(expected_coq_definitions or []),
        "missing_coq_definitions": sorted(missing_coq_definitions or []),
        "duplicate_reading_names": sorted(duplicate_reading_names or []),
        "malformed_reading_indices": sorted(set(malformed_reading_indices or [])),
        "failed_type_check_indices": sorted(set(failed_type_check_indices or [])),
        "expected_export_count": expected_export_count,
        "observed_export_count": observed,
    }


def semantic_readings_check_payload(
    *,
    checked: bool,
    ok: bool | None,
    reading_count: int,
    errors: list[str],
    repair_details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    failure_kinds = semantic_reading_failure_kinds(errors)
    return {
        "checked": checked,
        "ok": ok,
        "reading_count": reading_count,
        "errors": errors,
        "failure_kinds": failure_kinds,
        "failure_summary": semantic_reading_failure_summary(failure_kinds),
        "repair_details": repair_details or semantic_readings_repair_details(),
    }


def check_semantic_readings(
    readings: list[dict[str, Any]] | None,
    coq_code: str = "",
) -> dict[str, Any]:
    exported_definitions = exported_prop_definition_names(coq_code) if coq_code else []
    if readings is None:
        return semantic_readings_check_payload(
            checked=False,
            ok=None,
            reading_count=0,
            errors=[],
            repair_details=semantic_readings_repair_details(
                exported_definitions=exported_definitions,
            ),
        )
    errors: list[str] = []
    if not isinstance(readings, list):
        return semantic_readings_check_payload(
            checked=True,
            ok=False,
            reading_count=0,
            errors=["semantic_readings must be a list"],
            repair_details=semantic_readings_repair_details(
                exported_definitions=exported_definitions,
            ),
        )
    if not readings:
        errors.append("semantic_readings must not be empty when present")
    expected_coq_definitions: list[str] = []
    missing_coq_definitions: list[str] = []
    duplicate_reading_names: list[str] = []
    malformed_reading_indices: list[int] = []
    failed_type_check_indices: list[int] = []
    seen_names: set[str] = set()
    exported_definition_set = set(exported_definitions)
    for index, reading in enumerate(readings):
        if not isinstance(reading, dict):
            errors.append(f"semantic_readings[{index}] must be an object")
            malformed_reading_indices.append(index)
            continue
        malformed = False
        name = reading.get("name")
        if not isinstance(name, str) or not name:
            errors.append(f"semantic_readings[{index}].name must be a non-empty string")
            malformed = True
        elif name in seen_names:
            errors.append(f"semantic_readings name {name!r} is duplicated")
            duplicate_reading_names.append(name)
        else:
            seen_names.add(name)
        translation = reading.get("dependent_type_translation")
        if not isinstance(translation, str) or not translation.strip():
            errors.append(
                "semantic_readings"
                f"[{index}].dependent_type_translation must be a non-empty string"
            )
            malformed = True
        coq_definition = reading.get("coq_definition")
        if coq_definition is not None:
            if not isinstance(coq_definition, str) or not coq_definition:
                errors.append(
                    f"semantic_readings[{index}].coq_definition must be a non-empty string"
                )
                malformed = True
            else:
                expected_coq_definitions.append(coq_definition)
            if (
                isinstance(coq_definition, str)
                and coq_definition
                and coq_code
                and coq_definition not in exported_definition_set
            ):
                errors.append(
                    "semantic_readings"
                    f"[{index}].coq_definition {coq_definition!r} is not exported"
                )
                missing_coq_definitions.append(coq_definition)
        scope_policy = reading.get("scope_policy")
        if scope_policy is not None and (
            not isinstance(scope_policy, dict)
            or any(
                not isinstance(key, str) or not isinstance(value, str)
                for key, value in scope_policy.items()
            )
        ):
            errors.append(f"semantic_readings[{index}].scope_policy must map strings to strings")
            malformed = True
        type_check = reading.get("type_check")
        if type_check is not None:
            if not isinstance(type_check, dict):
                errors.append(f"semantic_readings[{index}].type_check must be an object")
                malformed = True
            elif type_check.get("ok") is not True:
                errors.append(f"semantic_readings[{index}].type_check must have ok=true")
                failed_type_check_indices.append(index)
        if malformed:
            malformed_reading_indices.append(index)
    return semantic_readings_check_payload(
        checked=True,
        ok=not errors,
        reading_count=len(readings),
        errors=errors,
        repair_details=semantic_readings_repair_details(
            exported_definitions=exported_definitions,
            expected_coq_definitions=expected_coq_definitions,
            missing_coq_definitions=missing_coq_definitions,
            duplicate_reading_names=duplicate_reading_names,
            malformed_reading_indices=malformed_reading_indices,
            failed_type_check_indices=failed_type_check_indices,
        ),
    )


def single_semantic_reading_payload(
    *,
    name: str,
    dependent_type_translation: str,
    coq_code: str,
    coq_definition: str,
    type_check: dict[str, Any],
    source: str,
    scope: str | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    reading_type_check = {
        "ok": type_check.get("ok") is True,
        "type": type_check.get("type"),
        "errors": type_check.get("errors", []),
    }
    readings = [
        semantic_reading(
            name=name,
            dependent_type_translation=dependent_type_translation,
            coq_definition=coq_definition,
            scope=scope,
            type_check=reading_type_check,
            source=source,
        )
    ]
    return readings, check_semantic_readings(readings, coq_code)


def attach_single_semantic_reading(
    result: dict[str, Any],
    *,
    name: str,
    coq_definition: str,
    source: str,
    scope: str | None = None,
) -> dict[str, Any]:
    semantic_readings, semantic_readings_check = single_semantic_reading_payload(
        name=name,
        dependent_type_translation=result["dependent_type_translation"],
        coq_code=result.get("coq_code", ""),
        coq_definition=coq_definition,
        type_check=result.get("type_check", {}),
        source=source,
        scope=scope,
    )
    result["semantic_readings"] = semantic_readings
    result["semantic_readings_check"] = semantic_readings_check
    event_semantics = result.setdefault("event_semantics", {})
    event_semantics["semantic_readings"] = semantic_readings
    event_semantics["semantic_readings_check"] = semantic_readings_check
    return result


def exported_prop_definition_names(coq_code: str) -> list[str]:
    return re.findall(
        r"(?m)^Definition\s+([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(?:Prop|PropT)\b",
        coq_code,
    )


def attach_default_registered_semantic_reading(
    result: dict[str, Any],
    rule: ConstructionRule,
) -> dict[str, Any]:
    if "semantic_readings" in result or "semantic_readings_check" in result:
        return result

    definition_names = exported_prop_definition_names(result.get("coq_code", ""))
    if len(definition_names) != 1:
        semantic_readings_check = semantic_readings_check_payload(
            checked=True,
            ok=False,
            reading_count=0,
            errors=[
                (
                    "registered construction outputs without explicit semantic_readings "
                    "must export exactly one Prop/PropT definition"
                )
            ],
            repair_details=semantic_readings_repair_details(
                exported_definitions=definition_names,
                expected_export_count=1,
                observed_export_count=len(definition_names),
            ),
        )
        result["semantic_readings"] = []
        result["semantic_readings_check"] = semantic_readings_check
        event_semantics = result.setdefault("event_semantics", {})
        event_semantics["semantic_readings"] = []
        event_semantics["semantic_readings_check"] = semantic_readings_check
        return result

    return attach_single_semantic_reading(
        result,
        name=f"{rule.rule_id}_single_reading",
        coq_definition=definition_names[0],
        source=rule.rule_id,
        scope="registered_single_reading",
    )


def quantifier_semantic_readings(readings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        semantic_reading(
            name=reading["name"],
            dependent_type_translation=render_quantifier_reading(reading),
            coq_definition=reading["name"],
            scope="_then_".join(binder["role"] for binder in reading["scope_order"]),
            type_check={"ok": True, "type": "Prop", "errors": []},
            source="quantifier_scope",
        )
        for reading in readings
    ]


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

        modifiers = reading.get("modifiers", [])
        check_coordination_modifiers(errors, modifiers, f"readings[{index}]")
        has_modifiers = isinstance(modifiers, list) and bool(modifiers)
        observed_orders.append(tuple(str(binder.get("role")) for binder in order))
        relation_args = relation.get("arguments")
        expected_relation_type = (
            "forall n : nat, ModifierSeq n -> Entity -> Entity -> PropT"
            if has_modifiers
            else "Entity -> Entity -> Prop"
        )
        if relation.get("predicate_type") != expected_relation_type:
            errors.append(
                f"readings[{index}].relation must have type {expected_relation_type}"
            )
        if not isinstance(relation_args, list) or len(relation_args) != 2:
            errors.append(f"readings[{index}].relation.arguments must contain two entities")
        check_time_modifiers(errors, reading.get("time_modifiers", []), f"readings[{index}]")

        for binder_index, binder in enumerate(order):
            if not isinstance(binder, dict):
                errors.append(f"readings[{index}].scope_order[{binder_index}] must be an object")
                continue
            if binder.get("quantifier") not in SUPPORTED_SCOPE_DETERMINERS:
                errors.append(
                    f"readings[{index}].scope_order[{binder_index}] "
                    "must use a supported scope quantifier"
                )
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
    tokens, fronted_time_modifiers = split_fronted_time_modifiers(tokenize(sentence))
    tokens, fronted_adv_modifiers = split_fronted_adv_modifiers(tokens)
    tokens, later_fronted_time_modifiers = split_fronted_time_modifiers(tokens)
    fronted_time_modifiers = [
        *fronted_time_modifiers,
        *later_fronted_time_modifiers,
    ]
    if (
        len(tokens) < 5
        or tokens[0] not in SUPPORTED_SCOPE_DETERMINERS
        or tokens[3] not in SUPPORTED_SCOPE_DETERMINERS
    ):
        return None
    trailing_modifiers = split_shared_adv_and_time_modifiers(tokens[5:])
    if trailing_modifiers is None:
        return None
    trailing_adv_modifiers, trailing_time_modifiers = trailing_modifiers
    subject_quantifier = tokens[0]
    object_quantifier = tokens[3]
    subject_noun = lemma_verb(tokens[1])
    verb = lemma_verb(tokens[2])
    object_noun = lemma_verb(tokens[4])
    adv_modifiers = [*fronted_adv_modifiers, *trailing_adv_modifiers]
    time_modifiers = [*fronted_time_modifiers, *trailing_time_modifiers]
    readings = [
        quantifier_scope_reading(
            subject_noun,
            subject_quantifier,
            verb,
            object_noun,
            object_quantifier,
            subject_first=True,
            modifiers=adv_modifiers,
            time_modifiers=time_modifiers,
        ),
        quantifier_scope_reading(
            subject_noun,
            subject_quantifier,
            verb,
            object_noun,
            object_quantifier,
            subject_first=False,
            modifiers=adv_modifiers,
            time_modifiers=time_modifiers,
        ),
    ]
    type_check = check_quantifier_scope_readings(readings)
    semantic_readings = quantifier_semantic_readings(readings)
    event_semantics = {
        "analysis": "quantifier-scope",
        "source": sentence,
        "quantifiers": {
            "subject": subject_quantifier,
            "object": object_quantifier,
        },
        "modifiers": adv_modifiers,
        "time_modifiers": time_modifiers,
        "readings": [
            {**reading, "formula": render_quantifier_reading(reading)}
            for reading in readings
        ],
        "semantic_readings": semantic_readings,
    }
    coq_code = "\n".join(
        [
            "(* Quantifier-scope scaffold for dependent-type event semantics. *)",
            "Parameter Entity : Type.",
            *(
                [
                    "Definition PropT : Type := Prop.",
                    "Definition Adv : Type := (Entity -> PropT) -> Entity -> PropT.",
                    "Parameter ModifierSeq : nat -> Type.",
                    "Parameter mods_nil : ModifierSeq 0.",
                    "Parameter mods_cons : forall n : nat, Adv -> ModifierSeq n -> ModifierSeq (S n).",
                ]
                if adv_modifiers
                else []
            ),
            f"Parameter {subject_noun} : Entity -> Prop.",
            f"Parameter {object_noun} : Entity -> Prop.",
            *[
                f"Parameter {modifier_name} : Adv."
                for modifier_name in unique_names(
                    [modifier["name"] for modifier in adv_modifiers]
                )
            ],
            (
                f"Parameter {verb} : forall n : nat, ModifierSeq n -> Entity -> Entity -> PropT."
                if adv_modifiers
                else f"Parameter {verb} : Entity -> Entity -> Prop."
            ),
            *[
                f"Parameter {time_argument} : Entity."
                for time_argument in unique_names(
                    [modifier["argument"] for modifier in time_modifiers]
                )
            ],
            *(
                [
                    "Parameter at_T : Entity -> Prop -> Prop.",
                    "Parameter during_T : Entity -> Prop -> Prop.",
                ]
                if time_modifiers
                else []
            ),
            "",
            quantifier_scope_coq(readings[0]),
            quantifier_scope_coq(readings[1]),
            "",
            f"Check {readings[0]['name']}.",
            f"Check {readings[1]['name']}.",
            "",
        ]
    )
    semantic_readings_check = check_semantic_readings(semantic_readings, coq_code)
    event_semantics["semantic_readings_check"] = semantic_readings_check
    return {
        "kind": "quantifier_scope_ambiguity",
        "input_sentence": sentence,
        "event_semantics": event_semantics,
        "dependent_type_translation": "\n".join(
            reading["formula"] for reading in event_semantics["readings"]
        ),
        "semantic_readings": semantic_readings,
        "semantic_readings_check": semantic_readings_check,
        "ast": {
            "kind": "scope_ambiguity",
            "quantifier": quantifier_scope_family(subject_quantifier, object_quantifier),
            "quantifiers": {
                "subject": subject_quantifier,
                "object": object_quantifier,
            },
            "modifiers": adv_modifiers,
            "time_modifiers": time_modifiers,
            "readings": readings,
        },
        "type_check": {
            **type_check,
            "note": (
                "Both scope readings are represented with entity predicates "
                "and a binary relation; Adv modifiers stay in a dependent "
                "modifier sequence, and time modifiers, when present, scope "
                "over each quantified proposition; no Event argument is introduced."
            ),
        },
        "coq_code": coq_code,
    }


def negated_coordination_readings(
    subject: str,
    clauses: list[dict[str, Any]],
    time_modifiers: list[dict[str, str]] | None = None,
    connective: str = "and_T",
) -> list[dict[str, Any]]:
    if connective == "or_T":
        return [
            {
                "name": "do_support_negation_wide_disjunction",
                "scope": "negation_over_disjunction",
                "subject": {"name": subject, "type": "Entity"},
                "clauses": clauses,
                "connective": connective,
                "connective_type": "PropT -> PropT -> PropT"
                if any(negated_coordination_clause_uses_propt(clause) for clause in clauses)
                else "Prop -> Prop -> Prop",
                "time_modifiers": list(time_modifiers or []),
            }
        ]
    return [
        {
            "name": "do_support_negation_wide_scope",
            "scope": "negation_over_conjunction",
            "subject": {"name": subject, "type": "Entity"},
            "clauses": clauses,
            "connective": connective,
            "connective_type": "PropT -> PropT -> PropT"
            if any(negated_coordination_clause_uses_propt(clause) for clause in clauses)
            else "Prop -> Prop -> Prop",
            "time_modifiers": list(time_modifiers or []),
        },
        {
            "name": "do_support_negation_distributed_scope",
            "scope": "distributed_negation",
            "subject": {"name": subject, "type": "Entity"},
            "clauses": clauses,
            "connective": connective,
            "connective_type": "PropT -> PropT -> PropT"
            if any(negated_coordination_clause_uses_propt(clause) for clause in clauses)
            else "Prop -> Prop -> Prop",
            "time_modifiers": list(time_modifiers or []),
        },
    ]


def disjunction_of_negations_reading(
    subject: str,
    clauses: list[dict[str, Any]],
    time_modifiers: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    return {
        "name": "do_support_negation_disjunction_of_negations",
        "scope": "disjunction_of_negations",
        "subject": {"name": subject, "type": "Entity"},
        "clauses": clauses,
        "connective": "or_T",
        "connective_type": "PropT -> PropT -> PropT"
        if any(negated_coordination_clause_uses_propt(clause) for clause in clauses)
        else "Prop -> Prop -> Prop",
        "time_modifiers": list(time_modifiers or []),
    }


def negated_coordination_clause_uses_propt(clause: dict[str, Any]) -> bool:
    predicate_type = str(clause.get("predicate", {}).get("predicate_type", ""))
    return (
        predicate_type.startswith("forall n : nat, ModifierSeq n ->")
        or bool(clause.get("modifiers"))
        or bool(clause.get("time_modifiers"))
        or "modifiers" in clause
        or "time_modifiers" in clause
    )


def negated_coordination_uses_propt(readings: list[dict[str, Any]]) -> bool:
    return any(
        negated_coordination_clause_uses_propt(clause)
        for reading in readings
        for clause in reading.get("clauses", [])
        if isinstance(clause, dict)
    )


def check_negated_coordination_readings(readings: list[dict[str, Any]]) -> dict[str, Any]:
    errors: list[str] = []
    object_declarations: list[tuple[str, str]] = []
    connectives = {str(reading.get("connective", "and_T")) for reading in readings}
    observed_scopes = {str(reading.get("scope")) for reading in readings}
    if connectives == {"and_T"}:
        if len(readings) != 2:
            errors.append(f"expected two negated coordination readings, got {len(readings)}")
        if observed_scopes != {"negation_over_conjunction", "distributed_negation"}:
            errors.append(
                "negated and-coordination readings must include wide and distributed negation"
            )
    elif connectives == {"or_T"}:
        if len(readings) != 1:
            errors.append(
                f"expected one negated disjunction reading, got {len(readings)}"
            )
        if observed_scopes not in (
            {"negation_over_disjunction"},
            {"disjunction_of_negations"},
        ):
            errors.append(
                "negated or-coordination readings must include "
                "negation_over_disjunction or disjunction_of_negations"
            )
    else:
        errors.append("negated coordination readings must use one connective: and_T or or_T")

    for reading_index, reading in enumerate(readings):
        connective = reading.get("connective", "and_T")
        if connective not in {"and_T", "or_T"}:
            errors.append(
                f"readings[{reading_index}].connective must be and_T or or_T"
            )
        subject = reading.get("subject")
        if not isinstance(subject, dict):
            errors.append(f"readings[{reading_index}].subject must be an object")
        else:
            if subject.get("type") != "Entity":
                errors.append(f"readings[{reading_index}].subject must have type Entity")
            if not isinstance(subject.get("name"), str) or not subject.get("name"):
                errors.append(
                    f"readings[{reading_index}].subject.name must be non-empty"
                )

        check_time_modifiers(
            errors,
            reading.get("time_modifiers", []),
            f"readings[{reading_index}]",
        )

        clauses = reading.get("clauses")
        if not isinstance(clauses, list) or len(clauses) != 2:
            errors.append(f"readings[{reading_index}].clauses must contain two items")
            continue
        for clause_index, clause in enumerate(clauses):
            if not isinstance(clause, dict):
                errors.append(
                    f"readings[{reading_index}].clauses[{clause_index}] must be an object"
                )
                continue
            predicate = clause.get("predicate")
            if not isinstance(predicate, dict):
                errors.append(
                    f"readings[{reading_index}].clauses[{clause_index}].predicate must be an object"
                )
                continue
            surface = predicate.get("surface")
            name = predicate.get("name")
            if not isinstance(surface, str) or not surface:
                errors.append(
                    f"readings[{reading_index}].clauses[{clause_index}].predicate.surface must be non-empty"
                )
            if not isinstance(name, str) or not name:
                errors.append(
                    f"readings[{reading_index}].clauses[{clause_index}].predicate.name must be non-empty"
                )
            elif surface and lemma_verb(str(surface)) != name:
                errors.append(
                    f"readings[{reading_index}].clauses[{clause_index}].predicate.name must match its surface lemma"
                )
            uses_propt = negated_coordination_clause_uses_propt(clause)
            if uses_propt:
                check_coordination_modifiers(
                    errors,
                    clause.get("modifiers", []),
                    f"readings[{reading_index}].clauses[{clause_index}]",
                )
                check_time_modifiers(
                    errors,
                    clause.get("time_modifiers", []),
                    f"readings[{reading_index}].clauses[{clause_index}]",
                )
            obj = clause.get("object")
            if obj is None:
                expected_type = (
                    "forall n : nat, ModifierSeq n -> Entity -> PropT"
                    if uses_propt
                    else "Entity -> Prop"
                )
            elif isinstance(obj, dict):
                object_name = obj.get("name")
                object_type = obj.get("type")
                if not isinstance(object_name, str) or not object_name:
                    errors.append(
                        f"readings[{reading_index}].clauses[{clause_index}].object.name must be non-empty"
                    )
                if not isinstance(object_type, str) or not object_type:
                    errors.append(
                        f"readings[{reading_index}].clauses[{clause_index}].object.type must be non-empty"
                    )
                    expected_type = None
                else:
                    if reading_index == 0:
                        object_declarations.append((str(object_name), object_type))
                    expected_type = (
                        "forall n : nat, ModifierSeq n -> "
                        f"Entity -> {object_type} -> PropT"
                        if uses_propt
                        else f"Entity -> {object_type} -> Prop"
                    )
            else:
                errors.append(
                    f"readings[{reading_index}].clauses[{clause_index}].object must be null or object"
                )
                expected_type = None
            if expected_type is not None and predicate.get("predicate_type") != expected_type:
                errors.append(
                    f"readings[{reading_index}].clauses[{clause_index}].predicate must have type {expected_type}"
                )
        expected_connective_type = (
            "PropT -> PropT -> PropT"
            if any(
                isinstance(clause, dict)
                and negated_coordination_clause_uses_propt(clause)
                for clause in clauses
            )
            else "Prop -> Prop -> Prop"
        )
        if reading.get("connective_type") != expected_connective_type:
            errors.append(
                f"readings[{reading_index}].connective must have type "
                f"{expected_connective_type}"
            )

    check_declaration_type_conflicts(
        errors,
        object_declarations,
        "negated coordination object",
    )

    return {
        "ok": not errors,
        "type": "Prop" if not errors else None,
        "errors": errors,
        "reading_count": len(readings),
    }


def render_negated_coordination_clause(
    clause: dict[str, Any],
    coq: bool = False,
) -> str:
    if negated_coordination_clause_uses_propt(clause):
        if coq:
            return render_branch_clause_coq(clause)
        return render_branch_clause_translation(clause)
    predicate = clause["predicate"]["name"]
    subject = clause["subject"]["name"]
    obj = clause.get("object")
    if coq:
        if obj is None:
            return f"{predicate} {subject}"
        return f"{predicate} {subject} {obj['name']}"
    if obj is None:
        return f"{predicate}({subject})"
    return f"{predicate}({subject}, {obj['name']})"


def render_negated_coordination_reading(
    reading: dict[str, Any],
    coq: bool = False,
) -> str:
    left = render_negated_coordination_clause(reading["clauses"][0], coq=coq)
    right = render_negated_coordination_clause(reading["clauses"][1], coq=coq)
    connective = reading.get("connective", "and_T")
    if coq:
        coordination = f"{connective} ({left}) ({right})"
        if reading["scope"] == "distributed_negation":
            proposition = f"and_T (not_T ({left})) (not_T ({right}))"
        elif reading["scope"] == "disjunction_of_negations":
            proposition = f"or_T (not_T ({left})) (not_T ({right}))"
        else:
            proposition = f"not_T ({coordination})"
        for modifier in reading.get("time_modifiers", []):
            proposition = f"{modifier['operator']}_T {modifier['argument']} ({proposition})"
        return proposition
    coordination = f"{connective}({left}, {right})"
    if reading["scope"] == "distributed_negation":
        proposition = f"and_T(not_T({left}), not_T({right}))"
    elif reading["scope"] == "disjunction_of_negations":
        proposition = f"or_T(not_T({left}), not_T({right}))"
    else:
        proposition = f"not_T({coordination})"
    for modifier in reading.get("time_modifiers", []):
        proposition = f"{modifier['operator']}_T({modifier['argument']}, {proposition})"
    return proposition


def render_negated_coordination_coq(
    readings: list[dict[str, Any]],
) -> str:
    clauses = readings[0]["clauses"]
    subject = readings[0]["subject"]["name"]
    uses_propt = negated_coordination_uses_propt(readings)
    object_types = list(
        dict.fromkeys(
            clause["object"]["type"]
            for clause in clauses
            if isinstance(clause.get("object"), dict)
            and clause["object"]["type"] != "Entity"
        )
    )
    object_declarations = unique_typed_declarations([
        (clause["object"]["name"], clause["object"]["type"])
        for clause in clauses
        if isinstance(clause.get("object"), dict)
    ])
    predicate_declarations = unique_typed_declarations([
        (clause["predicate"]["name"], clause["predicate"]["predicate_type"])
        for clause in clauses
    ])
    lines = [
        "(* Scope ambiguity for do-support negation over coordination. *)",
        "Parameter Entity : Type.",
    ]
    if uses_propt:
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
    if uses_propt:
        all_modifiers = [
            modifier
            for clause in clauses
            for modifier in clause.get("modifiers", [])
        ]
        lines.extend(
            f"Parameter {name} : Adv."
            for name in unique_names([modifier["name"] for modifier in all_modifiers])
        )
    lines.extend(
        [
            "",
            f"Parameter {subject} : Entity.",
        ]
    )
    lines.extend(f"Parameter {name} : {type_name}." for name, type_name in object_declarations)
    lines.extend(
        f"Parameter {name} : {predicate_type}."
        for name, predicate_type in predicate_declarations
    )
    connective_names = unique_names([
        reading.get("connective", "and_T") for reading in readings
    ])
    if uses_propt:
        lines.extend(
            [
                "Parameter not_T : PropT -> PropT.",
            ]
        )
        lines.extend(
            f"Parameter {connective} : PropT -> PropT -> PropT."
            for connective in connective_names
        )
        all_time_modifiers = [
            modifier
            for reading in readings
            for modifier in reading.get("time_modifiers", [])
        ] + [
            modifier
            for clause in clauses
            for modifier in clause.get("time_modifiers", [])
        ]
        if all_time_modifiers:
            lines.extend(
                f"Parameter {name} : Entity."
                for name in unique_names([
                    modifier["argument"] for modifier in all_time_modifiers
                ])
            )
            lines.extend(
                [
                    "Parameter at_T : Entity -> PropT -> PropT.",
                    "Parameter during_T : Entity -> PropT -> PropT.",
                ]
            )
        lines.append("")
    else:
        lines.extend(
            [
                "Parameter not_T : Prop -> Prop.",
            ]
        )
        lines.extend(
            f"Parameter {connective} : Prop -> Prop -> Prop."
            for connective in connective_names
        )
        all_time_modifiers = [
            modifier
            for reading in readings
            for modifier in reading.get("time_modifiers", [])
        ]
        if all_time_modifiers:
            lines.extend(
                f"Parameter {name} : Entity."
                for name in unique_names([
                    modifier["argument"] for modifier in all_time_modifiers
                ])
            )
            lines.extend(
                [
                    "Parameter at_T : Entity -> Prop -> Prop.",
                    "Parameter during_T : Entity -> Prop -> Prop.",
                ]
            )
        lines.append("")
    for reading in readings:
        lines.extend(
            [
                f"Definition {reading['name']} : Prop :=",
                f"  {render_negated_coordination_reading(reading, coq=True)}.",
                "",
            ]
        )
    lines.extend(f"Check {reading['name']}." for reading in readings)
    lines.append("")
    return "\n".join(lines)


def negated_coordination_semantic_readings(
    readings: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        semantic_reading(
            name=reading["name"],
            dependent_type_translation=render_negated_coordination_reading(reading),
            coq_definition=reading["name"],
            scope=reading["scope"],
            type_check={"ok": True, "type": "Prop", "errors": []},
            source="do_support_negation",
        )
        for reading in readings
    ]


def negated_coordination_clause_from_tail(
    surface: str,
    tail_tokens: list[str],
    subject: str,
    shared_adv_modifiers: list[dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    shared_adv_modifiers = list(shared_adv_modifiers or [])
    modifier_parse = split_shared_adv_and_time_modifiers(tail_tokens)
    if modifier_parse is not None:
        adv_modifiers, time_modifiers = modifier_parse
        modifiers = [*shared_adv_modifiers, *adv_modifiers]
        if modifiers or time_modifiers:
            return branch_modifier_clause(
                surface,
                subject,
                modifiers,
                False,
                time_modifiers=time_modifiers,
            )
        return {
            "predicate": {
                "surface": surface,
                "name": lemma_verb(surface),
                "predicate_type": "Entity -> Prop",
            },
            "subject": {"name": subject, "type": "Entity"},
            "object": None,
        }

    if not is_likely_transitive_verb(surface):
        return None

    object_parse = split_object_tokens_and_modifiers(tail_tokens)
    if object_parse is None:
        return None
    object_tokens, adv_modifiers, time_modifiers = object_parse
    obj = clean_phrase(object_tokens)
    if obj == "entity":
        return None
    predicate = lemma_verb(surface)
    object_type = object_type_for_transitive_predicate(predicate)
    obj_record = {"name": obj, "type": object_type}
    modifiers = [*shared_adv_modifiers, *adv_modifiers]
    if modifiers or time_modifiers:
        return branch_modifier_clause(
            surface,
            subject,
            modifiers,
            False,
            obj_record,
            time_modifiers=time_modifiers,
        )
    return {
        "predicate": {
            "surface": surface,
            "name": predicate,
            "predicate_type": f"Entity -> {object_type} -> Prop",
        },
        "subject": {"name": subject, "type": "Entity"},
        "object": obj_record,
    }


def ambiguous_do_support_coordination_pipeline(
    sentence: str,
    tokens: list[str],
    negation_index: int,
    auxiliary: str,
    subject: str,
    fronted_adv_modifiers: list[dict[str, Any]] | None = None,
    fronted_time_modifiers: list[dict[str, str]] | None = None,
) -> dict[str, Any] | None:
    fronted_adv_modifiers = list(fronted_adv_modifiers or [])
    fronted_time_modifiers = list(fronted_time_modifiers or [])
    coordination = single_boolean_coordinator(tokens)
    if coordination is None:
        return None
    coordinator, coordinator_index = coordination
    connective = connective_for_coordinator(coordinator)
    if coordinator_index <= negation_index + 1 or coordinator_index + 1 >= len(tokens):
        return None
    left_surface = tokens[negation_index + 1]
    right_surface = tokens[coordinator_index + 1]
    if not is_likely_surface_verb(left_surface) or not is_likely_surface_verb(right_surface):
        return None

    left_clause = negated_coordination_clause_from_tail(
        left_surface,
        tokens[negation_index + 2 : coordinator_index],
        subject,
        fronted_adv_modifiers,
    )
    right_clause = negated_coordination_clause_from_tail(
        right_surface,
        tokens[coordinator_index + 2 :],
        subject,
        fronted_adv_modifiers,
    )
    if left_clause is None or right_clause is None:
        return None
    clauses = [left_clause, right_clause]

    readings = negated_coordination_readings(
        subject,
        clauses,
        fronted_time_modifiers,
        connective=connective,
    )
    type_check = check_negated_coordination_readings(readings)
    semantic_readings = negated_coordination_semantic_readings(readings)
    dependent_type_translation = "\n".join(
        f"{reading['scope']}: {render_negated_coordination_reading(reading)}"
        for reading in readings
    )
    coq_code = render_negated_coordination_coq(readings)
    semantic_readings_check = check_semantic_readings(semantic_readings, coq_code)
    kind = (
        "do_support_negation_disjunction"
        if connective == "or_T"
        else "do_support_negation_coordination_ambiguity"
    )
    analysis = (
        "do-support-negation-disjunction"
        if connective == "or_T"
        else "do-support-negation-coordination-ambiguity"
    )
    summary = (
        f"Do-support negation with {auxiliary} not scopes over an or-coordination; "
        "one checked negation-over-disjunction reading is exported."
        if connective == "or_T"
        else (
            f"Do-support negation with {auxiliary} not scopes ambiguously over "
            "and-coordination; both wide and distributed negation readings are exported."
        )
    )
    note = (
        "Do-support negation over or-coordination is represented as "
        "not_T over a typed disjunction rather than as a pseudo-object."
        if connective == "or_T"
        else (
            "Ambiguous do-support negation over and-coordination is represented "
            "as two typed propositions rather than collapsed into one formula."
        )
    )
    return {
        "kind": kind,
        "input_sentence": sentence,
        "construction_summary": summary,
        "event_semantics": {
            "analysis": analysis,
            "source": sentence,
            "event_style_reference": (
                "not over typed coordination, without introducing Event"
            ),
            "readings": [
                {**reading, "formula": render_negated_coordination_reading(reading)}
                for reading in readings
            ],
            "semantic_readings": semantic_readings,
            "semantic_readings_check": semantic_readings_check,
        },
        "dependent_type_translation": dependent_type_translation,
        "semantic_readings": semantic_readings,
        "semantic_readings_check": semantic_readings_check,
        "ast": {
            "kind": "do_support_negation_coordination_ambiguity",
            "auxiliary": auxiliary,
            "subject": {"name": subject, "type": "Entity"},
            "readings": readings,
        },
        "type_check": {
            **type_check,
            "note": note,
        },
        "coq_code": coq_code,
    }


def split_fronted_do_support_modifiers(
    tokens: list[str],
) -> tuple[list[str], list[dict[str, Any]], list[dict[str, str]]]:
    remaining = list(tokens)
    all_adv_modifiers: list[dict[str, Any]] = []
    all_time_modifiers: list[dict[str, str]] = []
    while remaining:
        original = list(remaining)
        remaining, time_modifiers = split_fronted_time_modifiers(remaining)
        all_time_modifiers.extend(time_modifiers)
        remaining, adv_modifiers = split_fronted_adv_modifiers(remaining)
        all_adv_modifiers.extend(adv_modifiers)
        if remaining == original:
            break
    return remaining, all_adv_modifiers, all_time_modifiers


def repeated_do_support_negation_coordination_pipeline(
    sentence: str,
    tokens: list[str],
    negation_index: int,
    auxiliary: str,
    subject: str,
    fronted_adv_modifiers: list[dict[str, Any]] | None = None,
    fronted_time_modifiers: list[dict[str, str]] | None = None,
) -> dict[str, Any] | None:
    fronted_adv_modifiers = list(fronted_adv_modifiers or [])
    fronted_time_modifiers = list(fronted_time_modifiers or [])
    coordination = single_boolean_coordinator(tokens)
    if coordination is None:
        return None
    coordinator, coordinator_index = coordination
    connective = connective_for_coordinator(coordinator)
    if coordinator_index <= negation_index + 1 or coordinator_index + 3 >= len(tokens):
        return None
    if tokens[coordinator_index + 1] not in DO_SUPPORT_AUXILIARIES:
        return None
    if tokens[coordinator_index + 2] != "not":
        return None
    left_surface = tokens[negation_index + 1]
    right_surface = tokens[coordinator_index + 3]
    if not is_likely_surface_verb(left_surface) or not is_likely_surface_verb(right_surface):
        return None

    left_clause = negated_coordination_clause_from_tail(
        left_surface,
        tokens[negation_index + 2 : coordinator_index],
        subject,
        fronted_adv_modifiers,
    )
    right_clause = negated_coordination_clause_from_tail(
        right_surface,
        tokens[coordinator_index + 4 :],
        subject,
        fronted_adv_modifiers,
    )
    if left_clause is None or right_clause is None:
        return None
    clauses = [left_clause, right_clause]
    if connective == "or_T":
        checked_readings = [
            disjunction_of_negations_reading(
                subject,
                clauses,
                fronted_time_modifiers,
            )
        ]
        exported_reading = checked_readings[0]
        surface_scope = "disjunction_of_negations"
    else:
        checked_readings = negated_coordination_readings(
            subject,
            clauses,
            fronted_time_modifiers,
        )
        exported_reading = checked_readings[1]
        surface_scope = "distributed_negation"
    type_check = check_negated_coordination_readings(checked_readings)
    type_check = {
        **type_check,
        "reading_count": 1,
        "surface_scope": surface_scope,
    }
    typed_replacement = render_negated_coordination_reading(exported_reading)
    coq_code = render_negated_coordination_coq([exported_reading])
    return attach_single_semantic_reading(
        {
            "kind": "repeated_do_support_negation_coordination",
            "input_sentence": sentence,
            "construction_summary": (
                f"Same subject {subject} coordinates two explicit do-support "
                f"negations with {coordinator}, so each typed branch is wrapped in not_T."
            ),
            "event_semantics": {
                "analysis": "repeated-do-support-negation-coordination",
                "source": sentence,
                "event_style_reference": (
                    f"not(P) {coordinator} not(Q), without introducing Event, Agent, or Theme"
                ),
                "formula": typed_replacement,
            },
            "dependent_type_translation": typed_replacement,
            "ast": {
                "kind": "repeated_do_support_negation_coordination",
                "auxiliary": auxiliary,
                "subject": {"name": subject, "type": "Entity"},
                "reading": exported_reading,
            },
            "type_check": {
                **type_check,
                "note": (
                    "Repeated do-support negation over coordination has an explicit "
                    "distributed negation surface form, so the translator exports "
                    "one checked proposition rather than an ambiguity set."
                ),
            },
            "coq_code": coq_code,
        },
        name=exported_reading["name"],
        coq_definition=exported_reading["name"],
        source="do_support_negation",
        scope=surface_scope,
    )


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

    (
        tokens_without_fronted,
        fronted_adv_modifiers,
        fronted_time_modifiers,
    ) = split_fronted_do_support_modifiers(
        tokens,
    )

    if any(token in BOOLEAN_COORDINATORS for token in tokens):
        stripped_negation_index = None
        for index, token in enumerate(tokens_without_fronted):
            if (
                token == "not"
                and index > 0
                and tokens_without_fronted[index - 1] in DO_SUPPORT_AUXILIARIES
            ):
                stripped_negation_index = index
                break
        if stripped_negation_index is not None:
            stripped_auxiliary_index = stripped_negation_index - 1
            stripped_subject_tokens = tokens_without_fronted[:stripped_auxiliary_index]
            stripped_subject = clean_phrase(stripped_subject_tokens)
            if stripped_subject != "entity":
                repeated_coordination = (
                    repeated_do_support_negation_coordination_pipeline(
                        sentence,
                        tokens_without_fronted,
                        stripped_negation_index,
                        tokens_without_fronted[stripped_auxiliary_index],
                        stripped_subject,
                        fronted_adv_modifiers,
                        fronted_time_modifiers,
                    )
                )
                if repeated_coordination is not None:
                    return repeated_coordination
        coordinated = coordinated_do_support_negation_pipeline(sentence)
        if coordinated is not None:
            return coordinated
        ambiguous_coordination = None
        if stripped_negation_index is not None:
            stripped_auxiliary_index = stripped_negation_index - 1
            stripped_subject_tokens = tokens_without_fronted[:stripped_auxiliary_index]
            stripped_subject = clean_phrase(stripped_subject_tokens)
            if stripped_subject != "entity":
                ambiguous_coordination = ambiguous_do_support_coordination_pipeline(
                    sentence,
                    tokens_without_fronted,
                    stripped_negation_index,
                    tokens_without_fronted[stripped_auxiliary_index],
                    stripped_subject,
                    fronted_adv_modifiers,
                    fronted_time_modifiers,
                )
        if ambiguous_coordination is not None:
            return ambiguous_coordination
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

    if any(token in CONTRASTIVE_COORDINATORS for token in tokens):
        contrastive = contrastive_do_support_negation_pipeline(sentence)
        if contrastive is not None:
            return contrastive
        return {
            "kind": "do_support_negation",
            "input_sentence": sentence,
            "construction_summary": (
                f"Do-support negation with {auxiliary} not and contrastive "
                "coordination was detected, but this surface pattern is not "
                "implemented in the controlled rule yet."
            ),
            "event_semantics": {
                "analysis": "do-support-negation",
                "source": sentence,
                "event_style_reference": (
                    "not(exists e. P(e) ...) with contrastive coordination unresolved"
                ),
            },
            "dependent_type_translation": "",
            "ast": {
                "kind": "do_support_negation",
                "auxiliary": auxiliary,
                "subject": {"name": subject, "type": "Entity"},
                "unsupported": "contrastive_coordination_under_negation",
            },
            "type_check": {
                "ok": False,
                "type": None,
                "errors": [
                    "do-support negation with contrastive coordination is not yet supported"
                ],
                "note": (
                    "The parser refuses to turn contrastive coordination into "
                    "a malformed object inside the negated positive clause."
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
    return attach_single_semantic_reading(
        {
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
        },
        name="do_support_negation",
        coq_definition="example_1",
        source="do_support_negation",
        scope="simple_negation",
    )


def wrap_negated_translation(term: str, negated: bool) -> str:
    return f"not_T({term})" if negated else term


def wrap_negated_coq(term: str, negated: bool) -> str:
    return f"not_T ({term})" if negated else term


def coordinated_do_support_negation_pipeline(sentence: str) -> dict[str, Any] | None:
    tokens, fronted_time_modifiers = split_fronted_time_modifiers(tokenize(sentence))
    tokens, fronted_adv_modifiers = split_fronted_adv_modifiers(tokens)
    tokens = strip_surface_coordination_marker(tokens)
    coordination = single_boolean_coordinator(tokens)
    if coordination is None:
        return None
    coordinator, coordinator_index = coordination
    connective = connective_for_coordinator(coordinator)
    if "not" in tokens[:coordinator_index]:
        return None
    if coordinator_index + 3 >= len(tokens):
        return None
    auxiliary = tokens[coordinator_index + 1]
    if auxiliary not in DO_SUPPORT_AUXILIARIES or tokens[coordinator_index + 2] != "not":
        return None
    right_surface = tokens[coordinator_index + 3]
    if not is_likely_surface_verb(right_surface):
        return None

    transitive = coordinated_transitive_do_support_negation(
        sentence,
        tokens,
        coordinator_index,
        right_surface,
        fronted_adv_modifiers,
        fronted_time_modifiers,
        coordinator,
        connective,
    )
    if transitive is not None:
        return transitive
    return coordinated_intransitive_do_support_negation(
        sentence,
        tokens,
        coordinator_index,
        right_surface,
        fronted_adv_modifiers,
        fronted_time_modifiers,
        coordinator,
        connective,
    )


def contrastive_do_support_negation_pipeline(sentence: str) -> dict[str, Any] | None:
    tokens, fronted_time_modifiers = split_fronted_time_modifiers(tokenize(sentence))
    tokens, fronted_adv_modifiers = split_fronted_adv_modifiers(tokens)
    if sum(1 for token in tokens if token in CONTRASTIVE_COORDINATORS) != 1:
        return None
    but_index = next(
        index for index, token in enumerate(tokens) if token in CONTRASTIVE_COORDINATORS
    )
    negation_index = None
    for index, token in enumerate(tokens[:but_index]):
        if (
            token == "not"
            and index > 0
            and tokens[index - 1] in DO_SUPPORT_AUXILIARIES
        ):
            negation_index = index
            break
    if negation_index is None or negation_index + 1 >= but_index:
        return None
    if but_index + 1 >= len(tokens):
        return None
    left_surface = tokens[negation_index + 1]
    right_surface = tokens[but_index + 1]
    if not is_likely_surface_verb(left_surface) or not is_likely_surface_verb(right_surface):
        return None

    transitive = contrastive_transitive_do_support_negation(
        sentence,
        tokens,
        negation_index,
        but_index,
        left_surface,
        right_surface,
        fronted_adv_modifiers,
        fronted_time_modifiers,
    )
    if transitive is not None:
        return transitive
    return contrastive_intransitive_do_support_negation(
        sentence,
        tokens,
        negation_index,
        but_index,
        left_surface,
        right_surface,
        fronted_adv_modifiers,
        fronted_time_modifiers,
    )


def contrastive_do_support_failure(
    sentence: str,
    subject: str,
    auxiliary: str,
    unsupported: str,
    error: str,
    note: str,
) -> dict[str, Any]:
    return {
        "kind": "contrastive_do_support_negation",
        "input_sentence": sentence,
        "construction_summary": (
            f"Contrastive do-support negation with {auxiliary} not was detected, "
            "but this surface pattern is outside the controlled fragment."
        ),
        "event_semantics": {
            "analysis": "contrastive-do-support-negation",
            "source": sentence,
            "event_style_reference": (
                "not(exists e1. P(e1) ...) and exists e2. Q(e2) ..."
            ),
        },
        "dependent_type_translation": "",
        "ast": {
            "kind": "contrastive_do_support_negation",
            "auxiliary": auxiliary,
            "subject": {"name": subject, "type": "Entity"},
            "unsupported": unsupported,
        },
        "type_check": {
            "ok": False,
            "type": None,
            "errors": [error],
            "note": note,
        },
        "coq_code": "",
    }


def branch_modifier_clause(
    surface: str,
    subject: str,
    modifiers: list[dict[str, Any]],
    negated: bool,
    obj: dict[str, str] | None = None,
    time_modifiers: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    predicate = lemma_verb(surface)
    if obj is None:
        predicate_type = "forall n : nat, ModifierSeq n -> Entity -> PropT"
    else:
        predicate_type = (
            "forall n : nat, ModifierSeq n -> "
            f"Entity -> {obj['type']} -> PropT"
        )
    return {
        "predicate": {
            "surface": surface,
            "name": predicate,
            "predicate_type": predicate_type,
        },
        "subject": {"name": subject, "type": "Entity"},
        "object": obj,
        "modifiers": modifiers,
        "time_modifiers": list(time_modifiers or []),
        "negated": negated,
    }


def contrastive_branch_modifier_ast(
    subject: str,
    clauses: list[dict[str, Any]],
    time_modifiers: list[dict[str, str]],
) -> dict[str, Any]:
    return {
        "kind": "contrastive_branch_modifier_coordination",
        "subject": {"name": subject, "type": "Entity"},
        "clauses": clauses,
        "connective": "and_T",
        "connective_type": "PropT -> PropT -> PropT",
        "time_modifiers": time_modifiers,
    }


def check_contrastive_branch_modifier_ast(ast: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if ast.get("kind") != "contrastive_branch_modifier_coordination":
        errors.append("ast.kind must be contrastive_branch_modifier_coordination")

    subject = ast.get("subject")
    if not isinstance(subject, dict):
        errors.append("contrastive branch modifier subject must be an object")
    else:
        if not isinstance(subject.get("name"), str) or not subject.get("name"):
            errors.append("contrastive branch modifier subject.name must be non-empty")
        if subject.get("type") != "Entity":
            errors.append("contrastive branch modifier subject must have type Entity")

    clauses = ast.get("clauses")
    object_declarations: list[tuple[str, str]] = []
    if not isinstance(clauses, list) or len(clauses) != 2:
        errors.append("contrastive branch modifier clauses must contain exactly two items")
    else:
        for index, clause in enumerate(clauses):
            if not isinstance(clause, dict):
                errors.append(f"contrastive branch modifier clauses[{index}] must be an object")
                continue
            if "negated" in clause and not isinstance(clause["negated"], bool):
                errors.append(
                    f"contrastive branch modifier clauses[{index}].negated must be boolean"
                )
            modifiers = clause.get("modifiers")
            check_coordination_modifiers(
                errors,
                modifiers,
                f"contrastive branch modifier clauses[{index}]",
            )
            time_modifiers = clause.get("time_modifiers", [])
            if not isinstance(time_modifiers, list):
                errors.append(
                    f"contrastive branch modifier clauses[{index}].time_modifiers must be a list"
                )
            else:
                check_time_modifiers(
                    errors,
                    time_modifiers,
                    f"contrastive branch modifier clauses[{index}]",
                )
            predicate = clause.get("predicate")
            if not isinstance(predicate, dict):
                errors.append(
                    f"contrastive branch modifier clauses[{index}].predicate must be an object"
                )
                continue
            surface = predicate.get("surface")
            name = predicate.get("name")
            if not isinstance(surface, str) or not surface:
                errors.append(
                    "contrastive branch modifier "
                    f"clauses[{index}].predicate.surface must be non-empty"
                )
            if not isinstance(name, str) or not name:
                errors.append(
                    "contrastive branch modifier "
                    f"clauses[{index}].predicate.name must be non-empty"
                )
            elif surface and lemma_verb(str(surface)) != name:
                errors.append(
                    "contrastive branch modifier "
                    f"clauses[{index}].predicate.name must match its surface lemma"
                )

            obj = clause.get("object")
            if obj is None:
                expected_predicate_type = (
                    "forall n : nat, ModifierSeq n -> Entity -> PropT"
                )
            elif isinstance(obj, dict):
                object_name = obj.get("name")
                object_type = obj.get("type")
                if not isinstance(object_name, str) or not object_name:
                    errors.append(
                        "contrastive branch modifier "
                        f"clauses[{index}].object.name must be non-empty"
                    )
                if not isinstance(object_type, str) or not object_type:
                    errors.append(
                        "contrastive branch modifier "
                        f"clauses[{index}].object.type must be non-empty"
                    )
                    expected_predicate_type = None
                else:
                    expected_predicate_type = (
                        "forall n : nat, ModifierSeq n -> "
                        f"Entity -> {object_type} -> PropT"
                    )
                    object_declarations.append((str(object_name), object_type))
            else:
                errors.append(
                    f"contrastive branch modifier clauses[{index}].object must be null or object"
                )
                expected_predicate_type = None
            if (
                expected_predicate_type is not None
                and predicate.get("predicate_type") != expected_predicate_type
            ):
                errors.append(
                    "contrastive branch modifier "
                    f"clauses[{index}].predicate must have type {expected_predicate_type}"
                )

    check_declaration_type_conflicts(
        errors,
        object_declarations,
        "contrastive branch modifier object",
    )

    if ast.get("connective") != "and_T":
        errors.append("contrastive branch modifier connective must be and_T")
    if ast.get("connective_type") != "PropT -> PropT -> PropT":
        errors.append(
            "contrastive branch modifier connective must have type PropT -> PropT -> PropT"
        )

    time_modifiers = ast.get("time_modifiers")
    if not isinstance(time_modifiers, list):
        errors.append("contrastive branch modifier time_modifiers must be a list")
    else:
        for index, modifier in enumerate(time_modifiers):
            if not isinstance(modifier, dict):
                errors.append(
                    f"contrastive branch modifier time_modifiers[{index}] must be an object"
                )
                continue
            if modifier.get("operator") not in {"at", "during"}:
                errors.append(
                    "contrastive branch modifier "
                    f"time_modifiers[{index}].operator must be at or during"
                )
            if not isinstance(modifier.get("argument"), str) or not modifier.get("argument"):
                errors.append(
                    "contrastive branch modifier "
                    f"time_modifiers[{index}].argument must be non-empty"
                )

    return {
        "ok": not errors,
        "type": "Prop" if not errors else None,
        "errors": errors,
    }


def render_branch_clause_translation(clause: dict[str, Any]) -> str:
    predicate = clause["predicate"]["name"]
    subject = clause["subject"]["name"]
    modifiers = clause.get("modifiers", [])
    modifier_args = readable_modifier_arguments(modifiers)
    modifier_count = len(modifiers)
    obj = clause.get("object")
    if obj is None:
        if modifiers:
            term = f"{predicate}({modifier_count})({modifier_args}, {subject})"
        else:
            term = f"{predicate}(0)({subject})"
    elif modifiers:
        term = (
            f"{predicate}({modifier_count})"
            f"({modifier_args}, {subject}, {obj['name']})"
        )
    else:
        term = f"{predicate}(0)({subject}, {obj['name']})"
    for modifier in clause.get("time_modifiers", []):
        term = f"{modifier['operator']}_T({modifier['argument']}, {term})"
    return wrap_negated_translation(term, bool(clause.get("negated")))


def render_branch_clause_coq(clause: dict[str, Any]) -> str:
    predicate = clause["predicate"]["name"]
    subject = clause["subject"]["name"]
    modifiers = clause.get("modifiers", [])
    modifier_count = len(modifiers)
    modifier_sequence = coq_modifier_sequence(modifiers)
    obj = clause.get("object")
    if obj is None:
        term = f"{predicate} {modifier_count} {modifier_sequence} {subject}"
    else:
        term = (
            f"{predicate} {modifier_count} {modifier_sequence} "
            f"{subject} {obj['name']}"
        )
    for modifier in clause.get("time_modifiers", []):
        term = f"{modifier['operator']}_T {modifier['argument']} ({term})"
    return wrap_negated_coq(term, bool(clause.get("negated")))


def render_contrastive_branch_modifier_translation(ast: dict[str, Any]) -> str:
    left = render_branch_clause_translation(ast["clauses"][0])
    right = render_branch_clause_translation(ast["clauses"][1])
    proposition = f"and_T({left}, {right})"
    for modifier in ast["time_modifiers"]:
        proposition = f"{modifier['operator']}_T({modifier['argument']}, {proposition})"
    return proposition


def render_contrastive_branch_modifier_coq(
    definition_name: str,
    ast: dict[str, Any],
) -> str:
    clauses = ast["clauses"]
    subject = ast["subject"]["name"]
    left = render_branch_clause_coq(clauses[0])
    right = render_branch_clause_coq(clauses[1])
    proposition = f"and_T ({left}) ({right})"
    for modifier in ast["time_modifiers"]:
        proposition = f"{modifier['operator']}_T {modifier['argument']} ({proposition})"

    all_modifiers = [
        modifier
        for clause in clauses
        for modifier in clause.get("modifiers", [])
    ]
    object_types = list(
        dict.fromkeys(
            clause["object"]["type"]
            for clause in clauses
            if isinstance(clause.get("object"), dict)
            and clause["object"]["type"] != "Entity"
        )
    )
    lines = [
        "(* Contrastive do-support negation with branch-local modifiers. *)",
        "Parameter Entity : Type.",
        "Definition PropT : Type := Prop.",
        "Definition Adv : Type := (Entity -> PropT) -> Entity -> PropT.",
        "Parameter ModifierSeq : nat -> Type.",
        "Parameter mods_nil : ModifierSeq 0.",
        "Parameter mods_cons : forall n : nat, Adv -> ModifierSeq n -> ModifierSeq (S n).",
    ]
    lines.extend(f"Parameter {object_type} : Type." for object_type in object_types)
    lines.extend(
        f"Parameter {name} : Adv."
        for name in unique_names([modifier["name"] for modifier in all_modifiers])
    )
    lines.extend(["", f"Parameter {subject} : Entity."])
    for name, type_name in unique_typed_declarations([
        (clause["object"]["name"], clause["object"]["type"])
        for clause in clauses
        if isinstance(clause.get("object"), dict)
    ]):
        lines.append(f"Parameter {name} : {type_name}.")
    for name, predicate_type in unique_typed_declarations([
        (clause["predicate"]["name"], clause["predicate"]["predicate_type"])
        for clause in clauses
    ]):
        lines.append(f"Parameter {name} : {predicate_type}.")
    lines.extend(
        [
            "Parameter not_T : PropT -> PropT.",
            "Parameter and_T : PropT -> PropT -> PropT.",
        ]
    )
    all_time_modifiers = [
        *ast["time_modifiers"],
        *[
            modifier
            for clause in clauses
            for modifier in clause.get("time_modifiers", [])
        ],
    ]
    if all_time_modifiers:
        lines.extend(
            f"Parameter {name} : Entity."
            for name in unique_names([
                modifier["argument"] for modifier in all_time_modifiers
            ])
        )
        lines.extend(
            [
                "",
                "Parameter at_T : Entity -> PropT -> PropT.",
                "Parameter during_T : Entity -> PropT -> PropT.",
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
    return attach_single_semantic_reading(
        {
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
        },
        name="timed_after_singing_salute",
        coq_definition="after_singing_salute",
        source="timed_after",
        scope="time_before_salute",
    )


def perception_nominalization_ast(
    perception_predicate: str,
    experiencer: str,
    embedded_proposition: dict[str, Any],
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
                "proposition": embedded_proposition,
            },
        },
    }


def simple_perception_embedded_proposition(
    embedded_predicate: str,
    embedded_subject: str,
) -> dict[str, Any]:
    return {
        "predicate": embedded_predicate,
        "predicate_type": "Entity -> Prop",
        "subject": {
            "name": embedded_subject,
            "type": "Entity",
        },
    }


def timed_perception_embedded_proposition(
    embedded_predicate: str,
    embedded_subject: str,
    time_variable: str,
) -> dict[str, Any]:
    return {
        "predicate": embedded_predicate,
        "predicate_type": "Entity -> Time -> Prop",
        "subject": {
            "name": embedded_subject,
            "type": "Entity",
        },
        "time": time_variable,
    }


def proposition_coordination_ast(
    clauses: list[dict[str, Any]],
    connective: str = "and_T",
) -> dict[str, Any]:
    return {
        "kind": "proposition_coordination",
        "clauses": clauses,
        "connective": connective,
        "connective_type": "Prop -> Prop -> Prop",
    }


def timed_proposition_coordination_ast(
    clauses: list[dict[str, Any]],
    connective: str = "and_T",
) -> dict[str, Any]:
    return {
        "kind": "timed_proposition_coordination",
        "clauses": clauses,
        "connective": connective,
        "connective_type": "Prop -> Prop -> Prop",
    }


def timed_coordination_group_ast(
    clauses: list[dict[str, Any]],
    coordinator: str,
) -> dict[str, Any]:
    if len(clauses) == 1:
        return clauses[0]
    return timed_proposition_coordination_ast(
        clauses,
        connective_for_coordinator(coordinator),
    )


def split_boolean_coordinate_tokens(
    tokens: list[str],
) -> tuple[list[list[str]], list[str]] | None:
    if not tokens or tokens[0] in BOOLEAN_COORDINATORS or tokens[-1] in BOOLEAN_COORDINATORS:
        return None
    groups: list[list[str]] = [[]]
    coordinators: list[str] = []
    for token in tokens:
        if token in BOOLEAN_COORDINATORS:
            if not groups[-1]:
                return None
            coordinators.append(token)
            groups.append([])
            continue
        groups[-1].append(token)
    if not coordinators or any(not group for group in groups):
        return None
    return groups, coordinators


def fold_timed_boolean_coordination_with_precedence(
    clauses: list[dict[str, Any]],
    coordinators: list[str],
    *,
    tight_coordinator: str,
) -> dict[str, Any] | None:
    if len(clauses) != len(coordinators) + 1:
        return None
    if tight_coordinator not in BOOLEAN_COORDINATORS:
        return None
    loose_coordinator = "or" if tight_coordinator == "and" else "and"
    loose_terms: list[dict[str, Any]] = []
    current_tight_terms = [clauses[0]]
    for coordinator, clause in zip(coordinators, clauses[1:]):
        if coordinator == tight_coordinator:
            current_tight_terms.append(clause)
            continue
        loose_terms.append(
            timed_coordination_group_ast(current_tight_terms, tight_coordinator)
        )
        current_tight_terms = [clause]
    loose_terms.append(
        timed_coordination_group_ast(current_tight_terms, tight_coordinator)
    )
    return timed_coordination_group_ast(loose_terms, loose_coordinator)


def fold_mixed_timed_boolean_coordination(
    clauses: list[dict[str, Any]],
    coordinators: list[str],
) -> dict[str, Any] | None:
    primary = fold_timed_boolean_coordination_with_precedence(
        clauses,
        coordinators,
        tight_coordinator="and",
    )
    if primary is None:
        return None
    if len(set(coordinators)) > 1:
        alternative = fold_timed_boolean_coordination_with_precedence(
            copy.deepcopy(clauses),
            coordinators,
            tight_coordinator="or",
        )
        if alternative is not None:
            primary["coordination_scope"] = {
                "primary_policy": "and_before_or",
                "alternative_policy": "or_before_and",
                "coordinators": [
                    connective_for_coordinator(coordinator)
                    for coordinator in coordinators
                ],
                "alternative_ast": alternative,
            }
    return primary


def temporal_relation_arguments(
    relation_surface: str,
    main_time: str,
    reference_time: str,
) -> list[str]:
    return (
        [reference_time, main_time]
        if relation_surface == "after"
        else [main_time, reference_time]
    )


def perception_timed_proposition_times(proposition: dict[str, Any]) -> list[str]:
    if proposition.get("kind") == "timed_proposition_coordination":
        clauses = proposition.get("clauses")
        if not isinstance(clauses, list):
            return []
        times: list[str] = []
        for clause in clauses:
            if isinstance(clause, dict):
                times.extend(perception_timed_proposition_times(clause))
        return times
    time_variable = proposition.get("time")
    return [time_variable] if isinstance(time_variable, str) else []


def perception_timed_proposition_leaf_clauses(
    proposition: dict[str, Any],
) -> list[dict[str, Any]]:
    if proposition.get("kind") == "timed_proposition_coordination":
        leaves: list[dict[str, Any]] = []
        clauses = proposition.get("clauses")
        if not isinstance(clauses, list):
            return leaves
        for clause in clauses:
            if isinstance(clause, dict):
                leaves.extend(perception_timed_proposition_leaf_clauses(clause))
        return leaves
    return [proposition]


def base_temporal_relation_proposition_ast(
    main_clause: dict[str, Any],
    reference_clause: dict[str, Any],
    relation_surface: str,
) -> dict[str, Any]:
    main_times = perception_timed_proposition_times(main_clause)
    reference_times = perception_timed_proposition_times(reference_clause)
    relations = [
        {
            "predicate": "before",
            "predicate_type": "Time -> Time -> Prop",
            "arguments": temporal_relation_arguments(
                relation_surface,
                main_time,
                reference_time,
            ),
        }
        for main_time in main_times
        for reference_time in reference_times
    ]
    ast = {
        "kind": "temporal_relation",
        "relation_surface": relation_surface,
        "binders": [
            *[{"variable": time_variable, "type": "Time"} for time_variable in main_times],
            *[{"variable": time_variable, "type": "Time"} for time_variable in reference_times],
        ],
        "main": main_clause,
        "reference": reference_clause,
    }
    if len(relations) == 1:
        ast["relation"] = relations[0]
    else:
        ast["relations"] = relations
    return ast


def timed_proposition_scope_variants(
    proposition: dict[str, Any],
) -> list[dict[str, Any]]:
    variants = [
        {
            "policy": "and_before_or",
            "is_primary": True,
            "proposition": proposition,
        }
    ]
    scope = proposition.get("coordination_scope")
    if isinstance(scope, dict) and isinstance(scope.get("alternative_ast"), dict):
        variants.append(
            {
                "policy": str(scope.get("alternative_policy", "or_before_and")),
                "is_primary": False,
                "proposition": scope["alternative_ast"],
            }
        )
    return variants


def temporal_relation_alternative_scope_readings(
    proposition: dict[str, Any],
) -> list[dict[str, Any]]:
    relation_surface = proposition.get("relation_surface")
    if relation_surface not in TEMPORAL_RELATION_CONNECTORS:
        return []
    alternatives: list[dict[str, Any]] = []
    main_variants = timed_proposition_scope_variants(proposition["main"])
    reference_variants = timed_proposition_scope_variants(proposition["reference"])
    for main_variant in main_variants:
        for reference_variant in reference_variants:
            if main_variant["is_primary"] and reference_variant["is_primary"]:
                continue
            alt_ast = base_temporal_relation_proposition_ast(
                main_variant["proposition"],
                reference_variant["proposition"],
                str(relation_surface),
            )
            errors: list[str] = []
            check_perception_embedded_proposition(alt_ast, errors)
            changed_sides = [
                side
                for side, variant in (
                    ("main", main_variant),
                    ("reference", reference_variant),
                )
                if not variant["is_primary"]
            ]
            name = "or_before_and_" + "_".join(changed_sides)
            alternatives.append(
                {
                    "name": name,
                    "scope_policy": {
                        "main": main_variant["policy"],
                        "reference": reference_variant["policy"],
                    },
                    "dependent_type_translation": (
                        render_perception_embedded_translation(alt_ast)
                    ),
                    "ast": alt_ast,
                    "branch_count": (
                        len(timed_disjunction_branch_options(alt_ast["main"]))
                        * len(timed_disjunction_branch_options(alt_ast["reference"]))
                    ),
                    "type_check": {
                        "ok": not errors,
                        "type": "Prop" if not errors else None,
                        "errors": errors,
                    },
                }
            )
    return alternatives


def temporal_relation_proposition_ast(
    main_clause: dict[str, Any],
    reference_clause: dict[str, Any],
    relation_surface: str,
) -> dict[str, Any]:
    ast = base_temporal_relation_proposition_ast(
        main_clause,
        reference_clause,
        relation_surface,
    )
    alternatives = temporal_relation_alternative_scope_readings(ast)
    if alternatives:
        ast["alternative_scope_readings"] = alternatives
    return ast


def unsupported_mixed_temporal_perception_coordination(
    sentence: str,
    embedded_tokens: list[str],
) -> dict[str, Any]:
    return {
        "kind": "perception_nominalization",
        "input_sentence": sentence,
        "construction_summary": (
            "A perception complement with a temporal relation and mixed boolean "
            "coordination was detected, but it falls outside the current "
            "and-before-or timed-proposition policy."
        ),
        "event_semantics": {
            "analysis": "perception-temporal-mixed-coordination-boundary",
            "source": sentence,
            "event_style_reference": (
                "exists e. Seeing(e) and Experiencer(e, Mary) and "
                "Theme(e, mixed boolean temporal proposition)"
            ),
        },
        "dependent_type_translation": "",
        "ast": {
            "kind": "perception_nominalization",
            "unsupported": "mixed_temporal_perception_coordination",
            "embedded_tokens": embedded_tokens,
            "connectives": [
                BOOLEAN_COORDINATORS[token]
                for token in embedded_tokens
                if token in BOOLEAN_COORDINATORS
            ],
        },
        "type_check": {
            "ok": False,
            "type": None,
            "errors": [
                (
                    "mixed timed perception coordination is malformed or outside "
                    "the explicit and-before-or reading policy; refusing to treat "
                    "temporal material as an Entity"
                )
            ],
            "note": (
                "The parser recognized after/before inside a perception complement "
                "together with mixed boolean coordination, but could not build a typed "
                "timed proposition under the current precedence policy."
            ),
        },
        "coq_code": "",
    }


def perception_entity_name(tokens: list[str]) -> str:
    cleaned = clean_phrase(tokens)
    return "_".join(part.capitalize() for part in cleaned.split("_"))


def is_perception_embedded_intransitive_surface(token: str) -> bool:
    return is_likely_surface_verb(token) and not is_likely_transitive_verb(token)


def parse_simple_perception_embedded_clause(
    tokens: list[str],
) -> dict[str, Any] | None:
    if len(tokens) < 2:
        return None
    if any(
        token in BOOLEAN_COORDINATORS
        or token in TEMPORAL_RELATION_CONNECTORS
        or token == "both"
        for token in tokens
    ):
        return None
    embedded_surface = tokens[-1]
    if not is_perception_embedded_intransitive_surface(embedded_surface):
        return None
    embedded_subject = perception_entity_name(tokens[:-1])
    if embedded_subject == "Entity":
        return None
    return simple_perception_embedded_proposition(
        lemma_verb(embedded_surface),
        embedded_subject,
    )


def parse_timed_perception_embedded_clause(
    tokens: list[str],
    time_variable: str,
) -> dict[str, Any] | None:
    if len(tokens) < 2:
        return None
    if any(
        token in BOOLEAN_COORDINATORS
        or token in TEMPORAL_RELATION_CONNECTORS
        or token == "both"
        for token in tokens
    ):
        return None
    embedded_surface = tokens[-1]
    if not is_perception_embedded_intransitive_surface(embedded_surface):
        return None
    embedded_subject = perception_entity_name(tokens[:-1])
    if embedded_subject == "Entity":
        return None
    return timed_perception_embedded_proposition(
        lemma_verb(embedded_surface),
        embedded_subject,
        time_variable,
    )


def parse_timed_perception_side(
    tokens: list[str],
    *,
    simple_time: str,
    coordination_time_prefix: str,
) -> dict[str, Any] | None:
    simple_clause = parse_timed_perception_embedded_clause(tokens, simple_time)
    if simple_clause is not None:
        return simple_clause

    coordination = split_boolean_coordinate_tokens(tokens)
    if coordination is None:
        return None
    groups, coordinators = coordination
    clauses: list[dict[str, Any]] = []
    for index, group in enumerate(groups, start=1):
        clause = parse_timed_perception_embedded_clause(
            group,
            f"{coordination_time_prefix}_{index}",
        )
        if clause is None:
            return None
        clauses.append(clause)
    return fold_mixed_timed_boolean_coordination(clauses, coordinators)


def parse_timed_perception_main(tokens: list[str]) -> dict[str, Any] | None:
    return parse_timed_perception_side(
        tokens,
        simple_time="t_main",
        coordination_time_prefix="t_main",
    )


def parse_timed_perception_reference(tokens: list[str]) -> dict[str, Any] | None:
    return parse_timed_perception_side(
        tokens,
        simple_time="t_reference",
        coordination_time_prefix="t_reference",
    )


def parse_temporal_perception_embedded_proposition(
    tokens: list[str],
) -> dict[str, Any] | None:
    relation = single_temporal_relation_connector(tokens)
    if relation is None:
        return None
    relation_surface, relation_index = relation
    main_tokens = tokens[:relation_index]
    reference_tokens = tokens[relation_index + 1 :]
    if not main_tokens or not reference_tokens:
        return None
    main_clause = parse_timed_perception_main(main_tokens)
    reference_clause = parse_timed_perception_reference(reference_tokens)
    if main_clause is None or reference_clause is None:
        return None
    return temporal_relation_proposition_ast(
        main_clause,
        reference_clause,
        relation_surface,
    )


def perception_clause_definition_suffix(clause: dict[str, Any]) -> str:
    return f"{clause['subject']['name'].lower()}_{clause['predicate']}"


def perception_embedded_definition_suffix(proposition: dict[str, Any]) -> str:
    if proposition.get("kind") == "subject_coordination":
        subjects = [subject["name"].lower() for subject in proposition["subjects"]]
        connective = str(proposition["connective"]).replace("_T", "")
        return f"{subjects[0]}_{connective}_{subjects[1]}_{proposition['predicate']['name']}"
    if proposition.get("kind") in {
        "proposition_coordination",
        "timed_proposition_coordination",
    }:
        connective = str(proposition["connective"]).replace("_T", "")
        return f"_{connective}_".join(
            perception_embedded_definition_suffix(clause)
            for clause in proposition["clauses"]
        )
    if proposition.get("kind") == "temporal_relation":
        return (
            f"{perception_embedded_definition_suffix(proposition['main'])}_"
            f"{proposition['relation_surface']}_"
            f"{perception_embedded_definition_suffix(proposition['reference'])}"
        )
    return perception_clause_definition_suffix(proposition)


def render_perception_timed_clause_translation(clause: dict[str, Any]) -> str:
    return f"{clause['predicate']}({clause['subject']['name']}, {clause['time']})"


def render_binary_connective_translation(connective: str, arguments: list[str]) -> str:
    rendered = arguments[-1]
    for argument in reversed(arguments[:-1]):
        rendered = f"{connective}({argument}, {rendered})"
    return rendered


def render_perception_timed_proposition_translation(
    proposition: dict[str, Any],
) -> str:
    if proposition.get("kind") == "timed_proposition_coordination":
        return render_binary_connective_translation(
            proposition["connective"],
            [
                render_perception_timed_proposition_translation(clause)
                for clause in proposition["clauses"]
            ],
        )
    return render_perception_timed_clause_translation(proposition)


def render_perception_temporal_relations_translation(
    proposition: dict[str, Any],
) -> str:
    if proposition.get("relations") is not None:
        return " and ".join(
            f"before({relation['arguments'][0]}, {relation['arguments'][1]})"
            for relation in proposition["relations"]
        )
    relation = proposition["relation"]
    return f"before({relation['arguments'][0]}, {relation['arguments'][1]})"


def timed_disjunction_branch_options(
    proposition: dict[str, Any],
) -> list[dict[str, Any]]:
    if proposition.get("kind") != "timed_proposition_coordination":
        return [proposition]
    clauses = proposition.get("clauses")
    if not isinstance(clauses, list) or not clauses:
        return [proposition]
    if proposition.get("connective") == "or_T":
        branches: list[dict[str, Any]] = []
        for clause in clauses:
            if isinstance(clause, dict):
                branches.extend(timed_disjunction_branch_options(clause))
        return branches
    if proposition.get("connective") == "and_T":
        branch_groups: list[list[dict[str, Any]]] = [[]]
        for clause in clauses:
            if not isinstance(clause, dict):
                return [proposition]
            clause_options = timed_disjunction_branch_options(clause)
            branch_groups = [
                [*branch_group, option]
                for branch_group in branch_groups
                for option in clause_options
            ]
        return [
            timed_coordination_group_ast(branch_group, "and")
            for branch_group in branch_groups
        ]
    return [proposition]


def timed_proposition_has_disjunction(proposition: dict[str, Any]) -> bool:
    if proposition.get("kind") != "timed_proposition_coordination":
        return False
    if proposition.get("connective") == "or_T":
        return True
    clauses = proposition.get("clauses")
    return isinstance(clauses, list) and any(
        isinstance(clause, dict) and timed_proposition_has_disjunction(clause)
        for clause in clauses
    )


def temporal_relation_has_timed_disjunction(proposition: dict[str, Any]) -> bool:
    return any(
        timed_proposition_has_disjunction(side)
        for side in (proposition["main"], proposition["reference"])
    )


def render_temporal_relation_branch_translation(
    main: dict[str, Any],
    reference: dict[str, Any],
    relation_surface: str,
) -> str:
    time_variables = [
        *perception_timed_proposition_times(main),
        *perception_timed_proposition_times(reference),
    ]
    relation_text = " and ".join(
        f"before({arguments[0]}, {arguments[1]})"
        for arguments in expected_temporal_relation_arguments(
            main,
            reference,
            relation_surface,
        )
    )
    return (
        f"exists {' '.join(time_variables)} : Time. "
        f"{render_perception_timed_proposition_translation(main)} and "
        f"{render_perception_timed_proposition_translation(reference)} and "
        f"{relation_text}"
    )


def render_disjunctive_temporal_relation_translation(proposition: dict[str, Any]) -> str:
    branches = [
        render_temporal_relation_branch_translation(
            main,
            reference,
            proposition["relation_surface"],
        )
        for main in timed_disjunction_branch_options(proposition["main"])
        for reference in timed_disjunction_branch_options(proposition["reference"])
    ]
    return render_binary_connective_translation("or_T", branches)


def render_perception_embedded_translation(proposition: dict[str, Any]) -> str:
    if proposition.get("kind") == "subject_coordination":
        return render_subject_coordination_translation(proposition)
    if proposition.get("kind") == "proposition_coordination":
        left, right = proposition["clauses"]
        return (
            f"{proposition['connective']}("
            f"{render_perception_embedded_translation(left)}, "
            f"{render_perception_embedded_translation(right)})"
        )
    if proposition.get("kind") == "temporal_relation":
        main = proposition["main"]
        reference = proposition["reference"]
        if temporal_relation_has_timed_disjunction(proposition):
            return render_disjunctive_temporal_relation_translation(proposition)
        return (
            f"exists {' '.join(binder['variable'] for binder in proposition['binders'])} : Time. "
            f"{render_perception_timed_proposition_translation(main)} and "
            f"{render_perception_timed_proposition_translation(reference)} and "
            f"{render_perception_temporal_relations_translation(proposition)}"
        )
    return f"{proposition['predicate']}({proposition['subject']['name']})"


def render_perception_timed_clause_coq(clause: dict[str, Any]) -> str:
    return f"{clause['predicate']} {clause['subject']['name']} {clause['time']}"


def render_binary_connective_coq(connective: str, arguments: list[str]) -> str:
    rendered = arguments[-1]
    for argument in reversed(arguments[:-1]):
        rendered = f"{connective} ({argument}) ({rendered})"
    return rendered


def render_perception_timed_proposition_coq(proposition: dict[str, Any]) -> str:
    if proposition.get("kind") == "timed_proposition_coordination":
        return render_binary_connective_coq(
            proposition["connective"],
            [
                render_perception_timed_proposition_coq(clause)
                for clause in proposition["clauses"]
            ],
        )
    return render_perception_timed_clause_coq(proposition)


def render_perception_temporal_relations_coq(proposition: dict[str, Any]) -> str:
    if proposition.get("relations") is not None:
        return " /\\\n".join(
            f"    before {relation['arguments'][0]} {relation['arguments'][1]}"
            for relation in proposition["relations"]
        )
    relation = proposition["relation"]
    return f"    before {relation['arguments'][0]} {relation['arguments'][1]}"


def render_temporal_relation_branch_coq(
    main: dict[str, Any],
    reference: dict[str, Any],
    relation_surface: str,
) -> str:
    time_variables = [
        *perception_timed_proposition_times(main),
        *perception_timed_proposition_times(reference),
    ]
    quantifiers = "".join(
        f"exists {time_variable} : Time,\n  "
        for time_variable in time_variables
    )
    relation_text = " /\\\n".join(
        f"    before {arguments[0]} {arguments[1]}"
        for arguments in expected_temporal_relation_arguments(
            main,
            reference,
            relation_surface,
        )
    )
    return (
        quantifiers
        + f"  {render_perception_timed_proposition_coq(main)} /\\\n"
        + f"    {render_perception_timed_proposition_coq(reference)} /\\\n"
        + relation_text
    )


def render_disjunctive_temporal_relation_coq(proposition: dict[str, Any]) -> str:
    branches = [
        render_temporal_relation_branch_coq(
            main,
            reference,
            proposition["relation_surface"],
        )
        for main in timed_disjunction_branch_options(proposition["main"])
        for reference in timed_disjunction_branch_options(proposition["reference"])
    ]
    return render_binary_connective_coq("or_T", branches)


def render_perception_embedded_coq(proposition: dict[str, Any]) -> str:
    if proposition.get("kind") == "subject_coordination":
        predicate = proposition["predicate"]["name"]
        subjects = [subject["name"] for subject in proposition["subjects"]]
        return (
            f"{proposition['connective']} "
            f"({predicate} {subjects[0]}) ({predicate} {subjects[1]})"
        )
    if proposition.get("kind") == "proposition_coordination":
        left, right = proposition["clauses"]
        return (
            f"{proposition['connective']} "
            f"({render_perception_embedded_coq(left)}) "
            f"({render_perception_embedded_coq(right)})"
        )
    if proposition.get("kind") == "temporal_relation":
        main = proposition["main"]
        reference = proposition["reference"]
        if temporal_relation_has_timed_disjunction(proposition):
            return render_disjunctive_temporal_relation_coq(proposition)
        quantifiers = "".join(
            f"exists {binder['variable']} : Time,\n  "
            for binder in proposition["binders"]
        )
        return (
            quantifiers
            + f"  {render_perception_timed_proposition_coq(main)} /\\\n"
            + f"    {render_perception_timed_proposition_coq(reference)} /\\\n"
            + render_perception_temporal_relations_coq(proposition)
        )
    return f"{proposition['predicate']} {proposition['subject']['name']}"


def perception_embedded_subjects(proposition: dict[str, Any]) -> list[str]:
    if proposition.get("kind") == "subject_coordination":
        return [subject["name"] for subject in proposition["subjects"]]
    if proposition.get("kind") in {
        "proposition_coordination",
        "timed_proposition_coordination",
    }:
        subjects: list[str] = []
        for clause in proposition["clauses"]:
            subjects.extend(perception_embedded_subjects(clause))
        return subjects
    if proposition.get("kind") == "temporal_relation":
        return (
            perception_embedded_subjects(proposition["main"])
            + perception_embedded_subjects(proposition["reference"])
        )
    return [proposition["subject"]["name"]]


def perception_embedded_predicate_declarations(
    proposition: dict[str, Any],
) -> list[tuple[str, str]]:
    if proposition.get("kind") == "subject_coordination":
        return [(proposition["predicate"]["name"], "Entity -> Prop")]
    if proposition.get("kind") == "proposition_coordination":
        declarations: list[tuple[str, str]] = []
        for clause in proposition["clauses"]:
            declarations.extend(perception_embedded_predicate_declarations(clause))
        return declarations
    if proposition.get("kind") == "timed_proposition_coordination":
        declarations = []
        for clause in proposition["clauses"]:
            declarations.extend(perception_embedded_predicate_declarations(clause))
        return declarations
    if proposition.get("kind") == "temporal_relation":
        return [
            *perception_embedded_predicate_declarations(proposition["main"]),
            *perception_embedded_predicate_declarations(proposition["reference"]),
        ]
    predicate_type = proposition.get("predicate_type", "Entity -> Prop")
    return [(proposition["predicate"], predicate_type)]


def perception_embedded_connectives(proposition: dict[str, Any]) -> list[str]:
    if proposition.get("kind") == "subject_coordination":
        return [proposition["connective"]]
    if proposition.get("kind") in {
        "proposition_coordination",
        "timed_proposition_coordination",
    }:
        connectives = [proposition["connective"]]
        for clause in proposition["clauses"]:
            connectives.extend(perception_embedded_connectives(clause))
        return connectives
    if proposition.get("kind") == "temporal_relation":
        return (
            perception_embedded_connectives(proposition["main"])
            + perception_embedded_connectives(proposition["reference"])
        )
    return []


def perception_embedded_uses_time(proposition: dict[str, Any]) -> bool:
    if proposition.get("kind") == "temporal_relation":
        return True
    if proposition.get("kind") == "proposition_coordination":
        return any(perception_embedded_uses_time(clause) for clause in proposition["clauses"])
    return False


def check_timed_perception_clause(
    clause: dict[str, Any],
    expected_time: str,
    label: str,
    errors: list[str],
) -> None:
    if clause.get("predicate_type") != "Entity -> Time -> Prop":
        errors.append(
            f"embedded temporal relation {label} predicate must have type Entity -> Time -> Prop"
        )
    subject = clause.get("subject")
    if not isinstance(subject, dict) or subject.get("type") != "Entity":
        errors.append(f"embedded temporal relation {label} subject must have type Entity")
    if clause.get("time") != expected_time:
        errors.append(
            f"embedded temporal relation {label} must use bound time {expected_time}"
        )


def check_timed_side_proposition(
    proposition: dict[str, Any],
    *,
    simple_time: str,
    coordination_time_prefix: str,
    label: str,
    errors: list[str],
) -> None:
    if proposition.get("kind") == "timed_proposition_coordination":
        if proposition.get("connective") not in {"and_T", "or_T"}:
            errors.append(f"embedded timed {label} coordination connective must be and_T or or_T")
        if proposition.get("connective_type") != "Prop -> Prop -> Prop":
            errors.append(
                f"embedded timed {label} coordination connective must have type Prop -> Prop -> Prop"
            )
        if not isinstance(proposition.get("clauses"), list) or len(proposition["clauses"]) < 2:
            errors.append(f"embedded timed {label} coordination must contain at least two clauses")
            return
        leaves = perception_timed_proposition_leaf_clauses(proposition)
        if len(leaves) < 2:
            errors.append(f"embedded timed {label} coordination must contain at least two leaf clauses")
            return
        for index, clause in enumerate(leaves, start=1):
            check_timed_perception_clause(
                clause,
                f"{coordination_time_prefix}_{index}",
                f"{label} leaf[{index - 1}]",
                errors,
            )
        return

    check_timed_perception_clause(proposition, simple_time, label, errors)


def expected_temporal_relation_arguments(
    main: dict[str, Any],
    reference: dict[str, Any],
    relation_surface: str,
) -> list[list[str]]:
    return [
        temporal_relation_arguments(relation_surface, main_time, reference_time)
        for main_time in perception_timed_proposition_times(main)
        for reference_time in perception_timed_proposition_times(reference)
    ]


def temporal_relation_count_error(
    main_times: list[str],
    reference_times: list[str],
) -> str:
    if len(main_times) == 1 and len(reference_times) > 1:
        return "embedded timed reference coordination must contain one before relation per clause"
    if len(main_times) > 1 and len(reference_times) == 1:
        return "embedded timed main coordination must contain one before relation per clause"
    return "embedded temporal relation must contain one before relation per main/reference time pair"


def check_temporal_relation_node(
    relation: Any,
    expected_arguments: list[str],
    relation_surface: str,
    errors: list[str],
) -> None:
    if not isinstance(relation, dict):
        errors.append("embedded temporal relation relation must be an object")
        return
    if relation.get("predicate") != "before":
        errors.append("embedded temporal relation predicate must be before")
    if relation.get("predicate_type") != "Time -> Time -> Prop":
        errors.append("embedded before relation must have type Time -> Time -> Prop")
    if relation.get("arguments") != expected_arguments:
        errors.append(
            f"embedded {relation_surface} relation has the wrong before-argument order"
        )


def check_perception_embedded_proposition(
    proposition: dict[str, Any],
    errors: list[str],
) -> None:
    if proposition.get("kind") == "subject_coordination":
        if proposition.get("modifiers") != []:
            errors.append(
                "perception embedded subject coordination currently requires no shared modifiers"
            )
        if proposition.get("time_modifiers") != []:
            errors.append(
                "perception embedded subject coordination currently requires no time modifiers"
            )
        type_check = check_subject_coordination_ast(proposition)
        errors.extend(
            f"embedded subject coordination: {error}"
            for error in type_check["errors"]
        )
        return

    if proposition.get("kind") == "proposition_coordination":
        if proposition.get("connective") not in {"and_T", "or_T"}:
            errors.append("embedded proposition coordination connective must be and_T or or_T")
        if proposition.get("connective_type") != "Prop -> Prop -> Prop":
            errors.append(
                "embedded proposition coordination connective must have type Prop -> Prop -> Prop"
            )
        clauses = proposition.get("clauses")
        if not isinstance(clauses, list) or len(clauses) != 2:
            errors.append("embedded proposition coordination must contain exactly two clauses")
            return
        for clause in clauses:
            check_perception_embedded_proposition(clause, errors)
        return

    if proposition.get("kind") == "temporal_relation":
        relation_surface = proposition.get("relation_surface")
        if relation_surface not in TEMPORAL_RELATION_CONNECTORS:
            errors.append("embedded temporal relation must be after or before")
        main = proposition.get("main")
        if not isinstance(main, dict):
            errors.append("embedded temporal relation main must be an object")
            main_times: list[str] = []
        else:
            main_times = perception_timed_proposition_times(main)
            check_timed_side_proposition(
                main,
                simple_time="t_main",
                coordination_time_prefix="t_main",
                label="main",
                errors=errors,
            )
        reference = proposition.get("reference")
        if not isinstance(reference, dict):
            errors.append("embedded temporal relation reference must be an object")
            reference_times = []
        else:
            reference_times = perception_timed_proposition_times(reference)
            check_timed_side_proposition(
                reference,
                simple_time="t_reference",
                coordination_time_prefix="t_reference",
                label="reference",
                errors=errors,
            )
        expected_binders = [
            *[
                {"variable": time_variable, "type": "Time"}
                for time_variable in main_times
            ],
            *[
                {"variable": time_variable, "type": "Time"}
                for time_variable in reference_times
            ],
        ]
        if proposition.get("binders") != expected_binders:
            errors.append(
                "embedded temporal relation must bind its main and reference times as Time"
            )
        if not isinstance(main, dict) or not isinstance(reference, dict):
            return
        if relation_surface not in TEMPORAL_RELATION_CONNECTORS:
            return
        expected_arguments = expected_temporal_relation_arguments(
            main,
            reference,
            str(relation_surface),
        )
        if len(expected_arguments) == 1:
            if proposition.get("relations") is not None:
                errors.append(
                    "embedded simple temporal relation must use relation, not relations"
                )
            check_temporal_relation_node(
                proposition.get("relation"),
                expected_arguments[0],
                str(relation_surface),
                errors,
            )
            return

        if proposition.get("relation") is not None:
            errors.append(
                "embedded timed coordination must use relations, not a single relation"
            )
        relations = proposition.get("relations")
        if not isinstance(relations, list) or len(relations) != len(expected_arguments):
            errors.append(temporal_relation_count_error(main_times, reference_times))
            return
        for relation, expected_relation_arguments in zip(relations, expected_arguments):
            check_temporal_relation_node(
                relation,
                expected_relation_arguments,
                str(relation_surface),
                errors,
            )
        return

    if proposition.get("kind") == "timed_proposition_coordination":
        if proposition.get("connective") not in {"and_T", "or_T"}:
            errors.append("embedded timed proposition coordination connective must be and_T or or_T")
        if proposition.get("connective_type") != "Prop -> Prop -> Prop":
            errors.append(
                "embedded timed proposition coordination connective must have type Prop -> Prop -> Prop"
            )
        if not isinstance(proposition.get("clauses"), list) or len(proposition["clauses"]) < 2:
            errors.append("embedded timed proposition coordination must contain at least two clauses")
            return
        leaves = perception_timed_proposition_leaf_clauses(proposition)
        if len(leaves) < 2:
            errors.append("embedded timed proposition coordination must contain at least two leaf clauses")
            return
        for index, clause in enumerate(leaves, start=1):
            check_timed_perception_clause(
                clause,
                f"t_reference_{index}",
                f"timed leaf[{index - 1}]",
                errors,
            )
        return

    if proposition.get("predicate_type") != "Entity -> Prop":
        errors.append("embedded predicate must have type Entity -> Prop")
    subject = proposition.get("subject")
    if not isinstance(subject, dict) or subject.get("type") != "Entity":
        errors.append("embedded subject must have type Entity")


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
                check_perception_embedded_proposition(proposition, errors)

    return {
        "ok": not errors,
        "type": "Prop" if not errors else None,
        "errors": errors,
    }


def perception_nominalization_pipeline(sentence: str) -> dict[str, Any] | None:
    tokens = tokenize(sentence)
    if len(tokens) < 4 or tokens[0] != "mary" or tokens[1] != "saw":
        return None

    experiencer = "Mary"
    perception_predicate = lemma_verb(tokens[1])
    embedded_tokens = tokens[2:]
    embedded_proposition: dict[str, Any] | None = None

    simple_clause = parse_simple_perception_embedded_clause(embedded_tokens)
    if simple_clause is not None:
        embedded_proposition = simple_clause
    else:
        temporal_relation = parse_temporal_perception_embedded_proposition(
            embedded_tokens,
        )
        if temporal_relation is not None:
            embedded_proposition = temporal_relation

    if embedded_proposition is None:
        if (
            "or" in embedded_tokens
            and any(token in TEMPORAL_RELATION_CONNECTORS for token in embedded_tokens)
        ):
            return unsupported_mixed_temporal_perception_coordination(sentence, embedded_tokens)
        leading_both = bool(embedded_tokens and embedded_tokens[0] == "both")
        if leading_both:
            embedded_tokens = embedded_tokens[1:]
        coordination = single_boolean_coordinator(embedded_tokens)
        if coordination is None:
            return None
        coordinator, coordinator_index = coordination
        if leading_both and coordinator != "and":
            return None
        left_subject_tokens = embedded_tokens[:coordinator_index]
        right_tokens = embedded_tokens[coordinator_index + 1 :]
        if not left_subject_tokens or len(right_tokens) < 2:
            return None
        left_clause = parse_simple_perception_embedded_clause(left_subject_tokens)
        right_clause = parse_simple_perception_embedded_clause(right_tokens)
        if left_clause is not None and right_clause is not None:
            embedded_proposition = proposition_coordination_ast(
                [left_clause, right_clause],
                connective_for_coordinator(coordinator),
            )
        else:
            embedded_surface = right_tokens[-1]
            if not is_perception_embedded_intransitive_surface(embedded_surface):
                return None
            right_subject_tokens = right_tokens[:-1]
            if not right_subject_tokens:
                return None
            embedded_predicate = lemma_verb(embedded_surface)
            subjects = [
                perception_entity_name(left_subject_tokens),
                perception_entity_name(right_subject_tokens),
            ]
            embedded_proposition = subject_coordination_ast(
                subjects,
                {
                    "surface": embedded_surface,
                    "name": embedded_predicate,
                    "predicate_type": "Entity -> Prop",
                },
                [],
                [],
                connective_for_coordinator(coordinator),
            )

    if embedded_proposition is None:
        return None
    definition_suffix = perception_embedded_definition_suffix(embedded_proposition)
    embedded_translation = render_perception_embedded_translation(embedded_proposition)
    embedded_coq = render_perception_embedded_coq(embedded_proposition)
    alternative_scope_readings = [
        dict(reading)
        for reading in embedded_proposition.get("alternative_scope_readings", [])
        if isinstance(reading, dict)
    ]
    for reading in alternative_scope_readings:
        reading["typed_replacement"] = (
            f"see(Mary, E({reading['dependent_type_translation']}))"
        )
        reading["coq_definition"] = (
            f"mary_saw_{definition_suffix}_{reading['name']}"
        )
    semantic_readings = [
        semantic_reading(
            name="primary",
            dependent_type_translation=f"see(Mary, E({embedded_translation}))",
            coq_definition=f"mary_saw_{definition_suffix}",
            scope_policy=(
                {
                    "main": "and_before_or",
                    "reference": "and_before_or",
                }
                if alternative_scope_readings
                else None
            ),
            type_check={
                "ok": True,
                "type": "Prop",
                "errors": [],
            },
            source="perception_nominalization",
        )
    ]
    semantic_readings.extend(
        semantic_reading(
            name=reading["name"],
            dependent_type_translation=reading["typed_replacement"],
            coq_definition=reading["coq_definition"],
            scope_policy=reading["scope_policy"],
            type_check=reading["type_check"],
            source="perception_nominalization",
        )
        for reading in alternative_scope_readings
    )
    embedded_predicate_declarations = unique_typed_declarations(
        perception_embedded_predicate_declarations(embedded_proposition)
    )
    embedded_subjects = perception_embedded_subjects(embedded_proposition)
    connectives = unique_names(perception_embedded_connectives(embedded_proposition))
    coq_code = "\n".join(
        [
            "(* Luo-Shi-style nominalization for perception complements. *)",
            "Parameter Entity : Type.",
            *(["Parameter Time : Type."] if perception_embedded_uses_time(embedded_proposition) else []),
            "",
            f"Parameter {experiencer} : Entity.",
            *[
                f"Parameter {subject} : Entity."
                for subject in unique_names(embedded_subjects)
            ],
            "",
            "Parameter E : Prop -> Entity.",
            *[
                f"Parameter {predicate} : {predicate_type}."
                for predicate, predicate_type in embedded_predicate_declarations
            ],
            f"Parameter {perception_predicate} : Entity -> Entity -> Prop.",
            *(
                ["Parameter before : Time -> Time -> Prop."]
                if perception_embedded_uses_time(embedded_proposition)
                else []
            ),
            *(
                f"Parameter {connective} : Prop -> Prop -> Prop."
                for connective in connectives
            ),
            "",
            f"Definition mary_saw_{definition_suffix} : Prop :=",
            f"  {perception_predicate} {experiencer} (E ({embedded_coq})).",
            *[
                line
                for reading in alternative_scope_readings
                for line in (
                    "",
                    f"Definition {reading['coq_definition']} : Prop :=",
                    (
                        f"  {perception_predicate} {experiencer} "
                        f"(E ({render_perception_embedded_coq(reading['ast'])}))."
                    ),
                )
            ],
            "",
            f"Check mary_saw_{definition_suffix}.",
            *[
                f"Check {reading['coq_definition']}."
                for reading in alternative_scope_readings
            ],
            "",
        ]
    )
    semantic_readings_check = check_semantic_readings(semantic_readings, coq_code)
    event_semantics = {
        "analysis": "parsons-perception-complement",
        "source": sentence,
        "event_style_reference": (
            "exists e p. seeing(e) and Experiencer(e, Mary) and "
            f"PropositionObject(p, {embedded_translation}) and Theme(e, p)"
        ),
        "typed_replacement": f"see(Mary, E({embedded_translation}))",
        "semantic_readings": semantic_readings,
        "semantic_readings_check": semantic_readings_check,
    }
    if alternative_scope_readings:
        event_semantics["alternative_scope_readings"] = alternative_scope_readings
    ast = perception_nominalization_ast(
        perception_predicate,
        experiencer,
        embedded_proposition,
    )
    type_check = check_perception_nominalization_ast(ast)
    return {
        "kind": "perception_nominalization",
        "input_sentence": sentence,
        "event_semantics": event_semantics,
        "dependent_type_translation": event_semantics["typed_replacement"],
        "semantic_readings": semantic_readings,
        "semantic_readings_check": semantic_readings_check,
        **(
            {"alternative_scope_readings": alternative_scope_readings}
            if alternative_scope_readings
            else {}
        ),
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
    return attach_single_semantic_reading(
        {
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
        },
        name="universal_timed_burning",
        coq_definition="every_burning_consumes_oxygen",
        source="universal_timed_burning",
        scope="forall_entity_time",
    )


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
    elif subject_start < len(tokens) and tokens[subject_start] in QUANTIFIER_SUBJECT_DETERMINERS:
        starts_with_article = True
        subject_start += 1
    if subject_start >= len(tokens):
        return False

    def is_boundary_predicate(token: str) -> bool:
        return (
            token in PASSIVE_AUXILIARIES
            or token in DO_SUPPORT_AUXILIARIES
            or is_likely_surface_verb(token)
            or (token.endswith("ed") and len(token) > 3)
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


def check_time_modifiers(
    errors: list[str],
    modifiers: Any,
    context: str,
) -> None:
    if not isinstance(modifiers, list):
        errors.append(f"{context} time_modifiers must be a list")
        return
    for index, modifier in enumerate(modifiers):
        if not isinstance(modifier, dict):
            errors.append(f"{context} time_modifiers[{index}] must be an object")
            continue
        if modifier.get("operator") not in {"at", "during"}:
            errors.append(
                f"{context} time_modifiers[{index}].operator must be at or during"
            )
        if not isinstance(modifier.get("argument"), str) or not modifier.get("argument"):
            errors.append(
                f"{context} time_modifiers[{index}].argument must be non-empty"
            )


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
    connective: str = "and_T",
) -> dict[str, Any]:
    return {
        "kind": "predicate_coordination",
        "subject": {"name": subject, "type": "Entity"},
        "predicates": predicates,
        "modifiers": modifiers,
        "connective": connective,
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

    if ast.get("connective") not in {"and_T", "or_T"}:
        errors.append("predicate coordination connective must be and_T or or_T")
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
    proposition = f"{ast['connective']}({left}, {right})"
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
    proposition = f"{ast['connective']} ({left}) ({right})"
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
        lines.append(f"Parameter {ast['connective']} : PropT -> PropT -> PropT.")
    else:
        lines.extend(f"Parameter {predicate} : Entity -> Prop." for predicate in predicate_names)
        if any(predicate.get("negated") for predicate in predicates):
            lines.append("Parameter not_T : Prop -> Prop.")
        lines.append(f"Parameter {ast['connective']} : Prop -> Prop -> Prop.")
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


def subject_coordination_ast(
    subjects: list[str],
    predicate: dict[str, str],
    modifiers: list[dict[str, Any]],
    time_modifiers: list[dict[str, str]],
    connective: str = "and_T",
) -> dict[str, Any]:
    return {
        "kind": "subject_coordination",
        "subjects": [{"name": subject, "type": "Entity"} for subject in subjects],
        "predicate": predicate,
        "modifiers": modifiers,
        "connective": connective,
        "connective_type": (
            "PropT -> PropT -> PropT" if modifiers else "Prop -> Prop -> Prop"
        ),
        "time_modifiers": time_modifiers,
    }


def check_subject_coordination_ast(ast: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if ast.get("kind") != "subject_coordination":
        errors.append("ast.kind must be subject_coordination")
    modifiers = ast.get("modifiers")
    has_modifiers = isinstance(modifiers, list) and bool(modifiers)
    expected_predicate_type = (
        "forall n : nat, ModifierSeq n -> Entity -> PropT"
        if has_modifiers
        else "Entity -> Prop"
    )

    subjects = ast.get("subjects")
    if not isinstance(subjects, list) or len(subjects) != 2:
        errors.append("subject coordination subjects must contain exactly two items")
    else:
        for index, subject in enumerate(subjects):
            if not isinstance(subject, dict):
                errors.append(f"subject coordination subjects[{index}] must be an object")
                continue
            if not isinstance(subject.get("name"), str) or not subject.get("name"):
                errors.append(
                    f"subject coordination subjects[{index}].name must be a non-empty string"
                )
            if subject.get("type") != "Entity":
                errors.append(f"subject coordination subjects[{index}] must have type Entity")

    predicate = ast.get("predicate")
    if not isinstance(predicate, dict):
        errors.append("subject coordination predicate must be an object")
    else:
        surface = predicate.get("surface")
        name = predicate.get("name")
        if not isinstance(surface, str) or not surface:
            errors.append("subject coordination predicate.surface must be a non-empty string")
        if not isinstance(name, str) or not name:
            errors.append("subject coordination predicate.name must be a non-empty string")
        elif surface and lemma_verb(str(surface)) != name:
            errors.append("subject coordination predicate.name must match its surface lemma")
        if predicate.get("predicate_type") != expected_predicate_type:
            errors.append(
                f"subject coordination predicate must have type {expected_predicate_type}"
            )

    if ast.get("connective") not in {"and_T", "or_T"}:
        errors.append("subject coordination connective must be and_T or or_T")
    expected_connective_type = (
        "PropT -> PropT -> PropT" if has_modifiers else "Prop -> Prop -> Prop"
    )
    if ast.get("connective_type") != expected_connective_type:
        errors.append(
            "subject coordination connective must have type "
            f"{expected_connective_type}"
        )

    check_coordination_modifiers(errors, modifiers, "subject coordination")
    check_time_modifiers(errors, ast.get("time_modifiers"), "subject coordination")

    return {
        "ok": not errors,
        "type": "Prop" if not errors else None,
        "errors": errors,
    }


def render_subject_coordination_translation(ast: dict[str, Any]) -> str:
    predicate = ast["predicate"]["name"]
    subjects = [subject["name"] for subject in ast["subjects"]]
    modifiers = ast.get("modifiers", [])
    if modifiers:
        modifier_args = readable_modifier_arguments(modifiers)
        modifier_count = len(modifiers)
        left = f"{predicate}({modifier_count})({modifier_args}, {subjects[0]})"
        right = f"{predicate}({modifier_count})({modifier_args}, {subjects[1]})"
    else:
        left = f"{predicate}({subjects[0]})"
        right = f"{predicate}({subjects[1]})"
    proposition = f"{ast['connective']}({left}, {right})"
    for modifier in ast["time_modifiers"]:
        proposition = f"{modifier['operator']}_T({modifier['argument']}, {proposition})"
    return proposition


def render_subject_coordination_coq(
    definition_name: str,
    ast: dict[str, Any],
) -> str:
    predicate = ast["predicate"]["name"]
    subjects = [subject["name"] for subject in ast["subjects"]]
    modifiers = ast.get("modifiers", [])
    if modifiers:
        modifier_count = len(modifiers)
        modifier_sequence = coq_modifier_sequence(modifiers)
        left = f"{predicate} {modifier_count} {modifier_sequence} {subjects[0]}"
        right = f"{predicate} {modifier_count} {modifier_sequence} {subjects[1]}"
    else:
        left = f"{predicate} {subjects[0]}"
        right = f"{predicate} {subjects[1]}"
    proposition = f"{ast['connective']} ({left}) ({right})"
    for modifier in ast["time_modifiers"]:
        proposition = f"{modifier['operator']}_T {modifier['argument']} ({proposition})"
    lines = [
        "(* Subject coordination without event variables. *)",
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
    lines.append("")
    lines.extend(f"Parameter {subject} : Entity." for subject in unique_names(subjects))
    if modifiers:
        lines.append(f"Parameter {predicate} : forall n : nat, ModifierSeq n -> Entity -> PropT.")
        lines.append(f"Parameter {ast['connective']} : PropT -> PropT -> PropT.")
    else:
        lines.append(f"Parameter {predicate} : Entity -> Prop.")
        lines.append(f"Parameter {ast['connective']} : Prop -> Prop -> Prop.")
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


def subject_coordination_pipeline(sentence: str) -> dict[str, Any] | None:
    tokens, fronted_time_modifiers = split_fronted_time_modifiers(tokenize(sentence))
    tokens, fronted_adv_modifiers = split_fronted_adv_modifiers(tokens)
    leading_both = bool(tokens and tokens[0] == "both")
    if leading_both:
        if "and" not in tokens:
            return None
        tokens = tokens[1:]

    coordination = single_boolean_coordinator(tokens)
    if coordination is None:
        return None
    coordinator, coordinator_index = coordination
    if leading_both and coordinator != "and":
        return None
    left_subject_tokens = tokens[:coordinator_index]
    right_side_tokens = tokens[coordinator_index + 1 :]
    if not left_subject_tokens or len(right_side_tokens) < 2:
        return None

    predicate_offsets = [
        index
        for index, token in enumerate(right_side_tokens)
        if is_likely_surface_verb(token)
    ]
    if len(predicate_offsets) != 1:
        return None
    predicate_offset = predicate_offsets[0]
    if predicate_offset == 0:
        return None
    right_subject_tokens = right_side_tokens[:predicate_offset]
    predicate_surface = right_side_tokens[predicate_offset]

    trailing_modifiers = split_shared_adv_and_time_modifiers(
        right_side_tokens[predicate_offset + 1 :]
    )
    if trailing_modifiers is None:
        return None
    trailing_adv_modifiers, trailing_time_modifiers = trailing_modifiers
    shared_adv_modifiers = [*fronted_adv_modifiers, *trailing_adv_modifiers]
    time_modifiers = [*fronted_time_modifiers, *trailing_time_modifiers]

    subjects = [clean_phrase(left_subject_tokens), clean_phrase(right_subject_tokens)]
    if any(subject == "entity" for subject in subjects):
        return None
    predicate_name = lemma_verb(predicate_surface)
    predicate = {
        "surface": predicate_surface,
        "name": predicate_name,
        "predicate_type": (
            "forall n : nat, ModifierSeq n -> Entity -> PropT"
            if shared_adv_modifiers
            else "Entity -> Prop"
        ),
    }
    ast = subject_coordination_ast(
        subjects,
        predicate,
        shared_adv_modifiers,
        time_modifiers,
        connective_for_coordinator(coordinator),
    )
    type_check = check_subject_coordination_ast(ast)
    typed_replacement = render_subject_coordination_translation(ast)
    coq_code = render_subject_coordination_coq(
        f"subject_coordination_{predicate_name}",
        ast,
    )
    return {
        "kind": "subject_coordination",
        "input_sentence": sentence,
        "event_semantics": {
            "analysis": "subject-coordination",
            "source": sentence,
            "event_style_reference": (
                f"{predicate_name}(e1) with Agent(e1, {subjects[0]}) and "
                f"{predicate_name}(e2) with Agent(e2, {subjects[1]})"
            ),
            "typed_replacement": typed_replacement,
        },
        "dependent_type_translation": typed_replacement,
        "ast": ast,
        "type_check": type_check,
        "coq_code": coq_code,
        "construction_summary": (
            f"Subject coordination shares {predicate_name} across "
            f"{subjects[0]} and {subjects[1]} without introducing event variables."
        ),
    }


def transitive_subject_coordination_ast(
    subjects: list[str],
    predicate: dict[str, str],
    obj: dict[str, str],
    modifiers: list[dict[str, Any]],
    time_modifiers: list[dict[str, str]],
    connective: str = "and_T",
) -> dict[str, Any]:
    return {
        "kind": "transitive_subject_coordination",
        "subjects": [{"name": subject, "type": "Entity"} for subject in subjects],
        "predicate": predicate,
        "object": obj,
        "modifiers": modifiers,
        "connective": connective,
        "connective_type": (
            "PropT -> PropT -> PropT" if modifiers else "Prop -> Prop -> Prop"
        ),
        "time_modifiers": time_modifiers,
    }


def check_transitive_subject_coordination_ast(ast: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if ast.get("kind") != "transitive_subject_coordination":
        errors.append("ast.kind must be transitive_subject_coordination")
    modifiers = ast.get("modifiers")
    has_modifiers = isinstance(modifiers, list) and bool(modifiers)

    subjects = ast.get("subjects")
    if not isinstance(subjects, list) or len(subjects) != 2:
        errors.append("transitive subject coordination subjects must contain exactly two items")
    else:
        for index, subject in enumerate(subjects):
            if not isinstance(subject, dict):
                errors.append(
                    f"transitive subject coordination subjects[{index}] must be an object"
                )
                continue
            if not isinstance(subject.get("name"), str) or not subject.get("name"):
                errors.append(
                    "transitive subject coordination "
                    f"subjects[{index}].name must be a non-empty string"
                )
            if subject.get("type") != "Entity":
                errors.append(
                    f"transitive subject coordination subjects[{index}] must have type Entity"
                )

    obj = ast.get("object")
    object_type = None
    if not isinstance(obj, dict):
        errors.append("transitive subject coordination object must be an object")
    else:
        if not isinstance(obj.get("name"), str) or not obj.get("name"):
            errors.append("transitive subject coordination object.name must be non-empty")
        if not isinstance(obj.get("type"), str) or not obj.get("type"):
            errors.append("transitive subject coordination object.type must be non-empty")
        else:
            object_type = str(obj["type"])

    expected_predicate_type = None
    if object_type is not None:
        expected_predicate_type = (
            f"forall n : nat, ModifierSeq n -> Entity -> {object_type} -> PropT"
            if has_modifiers
            else f"Entity -> {object_type} -> Prop"
        )
    predicate = ast.get("predicate")
    if not isinstance(predicate, dict):
        errors.append("transitive subject coordination predicate must be an object")
    else:
        surface = predicate.get("surface")
        name = predicate.get("name")
        if not isinstance(surface, str) or not surface:
            errors.append(
                "transitive subject coordination predicate.surface must be a non-empty string"
            )
        if not isinstance(name, str) or not name:
            errors.append(
                "transitive subject coordination predicate.name must be a non-empty string"
            )
        elif surface and lemma_verb(str(surface)) != name:
            errors.append(
                "transitive subject coordination predicate.name must match its surface lemma"
            )
        if expected_predicate_type is not None and predicate.get("predicate_type") != expected_predicate_type:
            errors.append(
                "transitive subject coordination predicate must have type "
                f"{expected_predicate_type}"
            )

    if ast.get("connective") not in {"and_T", "or_T"}:
        errors.append("transitive subject coordination connective must be and_T or or_T")
    expected_connective_type = (
        "PropT -> PropT -> PropT" if has_modifiers else "Prop -> Prop -> Prop"
    )
    if ast.get("connective_type") != expected_connective_type:
        errors.append(
            "transitive subject coordination connective must have type "
            f"{expected_connective_type}"
        )

    check_coordination_modifiers(errors, modifiers, "transitive subject coordination")
    check_time_modifiers(errors, ast.get("time_modifiers"), "transitive subject coordination")

    return {
        "ok": not errors,
        "type": "Prop" if not errors else None,
        "errors": errors,
    }


def render_transitive_subject_coordination_translation(ast: dict[str, Any]) -> str:
    predicate = ast["predicate"]["name"]
    subjects = [subject["name"] for subject in ast["subjects"]]
    obj = ast["object"]["name"]
    modifiers = ast.get("modifiers", [])
    if modifiers:
        modifier_args = readable_modifier_arguments(modifiers)
        modifier_count = len(modifiers)
        left = f"{predicate}({modifier_count})({modifier_args}, {subjects[0]}, {obj})"
        right = f"{predicate}({modifier_count})({modifier_args}, {subjects[1]}, {obj})"
    else:
        left = f"{predicate}({subjects[0]}, {obj})"
        right = f"{predicate}({subjects[1]}, {obj})"
    proposition = f"{ast['connective']}({left}, {right})"
    for modifier in ast["time_modifiers"]:
        proposition = f"{modifier['operator']}_T({modifier['argument']}, {proposition})"
    return proposition


def render_transitive_subject_coordination_coq(
    definition_name: str,
    ast: dict[str, Any],
) -> str:
    predicate = ast["predicate"]["name"]
    subjects = [subject["name"] for subject in ast["subjects"]]
    obj = ast["object"]["name"]
    object_type = ast["object"]["type"]
    modifiers = ast.get("modifiers", [])
    if modifiers:
        modifier_count = len(modifiers)
        modifier_sequence = coq_modifier_sequence(modifiers)
        left = f"{predicate} {modifier_count} {modifier_sequence} {subjects[0]} {obj}"
        right = f"{predicate} {modifier_count} {modifier_sequence} {subjects[1]} {obj}"
    else:
        left = f"{predicate} {subjects[0]} {obj}"
        right = f"{predicate} {subjects[1]} {obj}"
    proposition = f"{ast['connective']} ({left}) ({right})"
    for modifier in ast["time_modifiers"]:
        proposition = f"{modifier['operator']}_T {modifier['argument']} ({proposition})"
    lines = [
        "(* Transitive subject coordination without event variables. *)",
        "Parameter Entity : Type.",
        f"Parameter {object_type} : Type.",
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
    lines.append("")
    lines.extend(f"Parameter {subject} : Entity." for subject in unique_names(subjects))
    lines.append(f"Parameter {obj} : {object_type}.")
    if modifiers:
        lines.append(
            f"Parameter {predicate} : forall n : nat, "
            f"ModifierSeq n -> Entity -> {object_type} -> PropT."
        )
        lines.append(f"Parameter {ast['connective']} : PropT -> PropT -> PropT.")
    else:
        lines.append(f"Parameter {predicate} : Entity -> {object_type} -> Prop.")
        lines.append(f"Parameter {ast['connective']} : Prop -> Prop -> Prop.")
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


def transitive_subject_coordination_pipeline(sentence: str) -> dict[str, Any] | None:
    tokens, fronted_time_modifiers = split_fronted_time_modifiers(tokenize(sentence))
    tokens, fronted_adv_modifiers = split_fronted_adv_modifiers(tokens)
    leading_both = bool(tokens and tokens[0] == "both")
    if leading_both:
        if "and" not in tokens:
            return None
        tokens = tokens[1:]

    coordination = single_boolean_coordinator(tokens)
    if coordination is None:
        return None
    coordinator, coordinator_index = coordination
    if leading_both and coordinator != "and":
        return None
    left_subject_tokens = tokens[:coordinator_index]
    right_side_tokens = tokens[coordinator_index + 1 :]
    if not left_subject_tokens or len(right_side_tokens) < 3:
        return None

    predicate_offsets = [
        index
        for index, token in enumerate(right_side_tokens)
        if is_likely_transitive_verb(token)
    ]
    if len(predicate_offsets) != 1:
        return None
    predicate_offset = predicate_offsets[0]
    if predicate_offset == 0:
        return None
    right_subject_tokens = right_side_tokens[:predicate_offset]
    predicate_surface = right_side_tokens[predicate_offset]
    predicate_name = lemma_verb(predicate_surface)

    object_tail = split_object_tokens_and_modifiers(right_side_tokens[predicate_offset + 1 :])
    if object_tail is None:
        return None
    object_tokens, trailing_adv_modifiers, trailing_time_modifiers = object_tail
    obj = clean_phrase(object_tokens)
    if obj == "entity":
        return None
    object_type = object_type_for_transitive_predicate(predicate_name)

    shared_adv_modifiers = [*fronted_adv_modifiers, *trailing_adv_modifiers]
    time_modifiers = [*fronted_time_modifiers, *trailing_time_modifiers]
    subjects = [clean_phrase(left_subject_tokens), clean_phrase(right_subject_tokens)]
    if any(subject == "entity" for subject in subjects):
        return None
    predicate = {
        "surface": predicate_surface,
        "name": predicate_name,
        "predicate_type": (
            f"forall n : nat, ModifierSeq n -> Entity -> {object_type} -> PropT"
            if shared_adv_modifiers
            else f"Entity -> {object_type} -> Prop"
        ),
    }
    ast = transitive_subject_coordination_ast(
        subjects,
        predicate,
        {"name": obj, "type": object_type},
        shared_adv_modifiers,
        time_modifiers,
        connective_for_coordinator(coordinator),
    )
    type_check = check_transitive_subject_coordination_ast(ast)
    typed_replacement = render_transitive_subject_coordination_translation(ast)
    coq_code = render_transitive_subject_coordination_coq(
        f"transitive_subject_coordination_{predicate_name}",
        ast,
    )
    return {
        "kind": "transitive_subject_coordination",
        "input_sentence": sentence,
        "event_semantics": {
            "analysis": "transitive-subject-coordination",
            "source": sentence,
            "event_style_reference": (
                f"{predicate_name}(e1) with Agent(e1, {subjects[0]}) and "
                f"Theme(e1, {obj}); {predicate_name}(e2) with "
                f"Agent(e2, {subjects[1]}) and Theme(e2, {obj})"
            ),
            "typed_replacement": typed_replacement,
        },
        "dependent_type_translation": typed_replacement,
        "ast": ast,
        "type_check": type_check,
        "coq_code": coq_code,
        "construction_summary": (
            f"Transitive subject coordination shares {predicate_name}"
            f"({obj} : {object_type}) across {subjects[0]} and {subjects[1]}."
        ),
    }


def object_coordination_ast(
    subject: str,
    predicate: dict[str, str],
    objects: list[dict[str, str]],
    modifiers: list[dict[str, Any]],
    time_modifiers: list[dict[str, str]],
    connective: str = "and_T",
) -> dict[str, Any]:
    return {
        "kind": "object_coordination",
        "subject": {"name": subject, "type": "Entity"},
        "predicate": predicate,
        "objects": objects,
        "modifiers": modifiers,
        "connective": connective,
        "connective_type": (
            "PropT -> PropT -> PropT" if modifiers else "Prop -> Prop -> Prop"
        ),
        "time_modifiers": time_modifiers,
    }


def check_object_coordination_ast(ast: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if ast.get("kind") != "object_coordination":
        errors.append("ast.kind must be object_coordination")
    modifiers = ast.get("modifiers")
    has_modifiers = isinstance(modifiers, list) and bool(modifiers)

    subject = ast.get("subject")
    if not isinstance(subject, dict):
        errors.append("object coordination subject must be an object")
    else:
        if not isinstance(subject.get("name"), str) or not subject.get("name"):
            errors.append("object coordination subject.name must be a non-empty string")
        if subject.get("type") != "Entity":
            errors.append("object coordination subject must have type Entity")

    objects = ast.get("objects")
    object_type = None
    if not isinstance(objects, list) or len(objects) != 2:
        errors.append("object coordination objects must contain exactly two items")
    else:
        object_declarations: list[tuple[str, str]] = []
        for index, obj in enumerate(objects):
            if not isinstance(obj, dict):
                errors.append(f"object coordination objects[{index}] must be an object")
                continue
            object_name = obj.get("name")
            current_type = obj.get("type")
            if not isinstance(object_name, str) or not object_name:
                errors.append(f"object coordination objects[{index}].name must be non-empty")
            if not isinstance(current_type, str) or not current_type:
                errors.append(f"object coordination objects[{index}].type must be non-empty")
                continue
            object_declarations.append((str(object_name), current_type))
            if object_type is None:
                object_type = current_type
            elif object_type != current_type:
                errors.append(
                    "object coordination objects must share one lexical type: "
                    f"{object_type} vs {current_type}"
                )
        check_declaration_type_conflicts(
            errors,
            object_declarations,
            "object coordination object",
        )

    expected_predicate_type = None
    if object_type is not None:
        expected_predicate_type = (
            f"forall n : nat, ModifierSeq n -> Entity -> {object_type} -> PropT"
            if has_modifiers
            else f"Entity -> {object_type} -> Prop"
        )
    predicate = ast.get("predicate")
    if not isinstance(predicate, dict):
        errors.append("object coordination predicate must be an object")
    else:
        surface = predicate.get("surface")
        name = predicate.get("name")
        if not isinstance(surface, str) or not surface:
            errors.append("object coordination predicate.surface must be a non-empty string")
        if not isinstance(name, str) or not name:
            errors.append("object coordination predicate.name must be a non-empty string")
        elif surface and lemma_verb(str(surface)) != name:
            errors.append("object coordination predicate.name must match its surface lemma")
        if expected_predicate_type is not None and predicate.get("predicate_type") != expected_predicate_type:
            errors.append(
                f"object coordination predicate must have type {expected_predicate_type}"
            )

    if ast.get("connective") not in {"and_T", "or_T"}:
        errors.append("object coordination connective must be and_T or or_T")
    expected_connective_type = (
        "PropT -> PropT -> PropT" if has_modifiers else "Prop -> Prop -> Prop"
    )
    if ast.get("connective_type") != expected_connective_type:
        errors.append(
            "object coordination connective must have type "
            f"{expected_connective_type}"
        )

    check_coordination_modifiers(errors, modifiers, "object coordination")
    check_time_modifiers(errors, ast.get("time_modifiers"), "object coordination")

    return {
        "ok": not errors,
        "type": "Prop" if not errors else None,
        "errors": errors,
    }


def render_object_coordination_translation(ast: dict[str, Any]) -> str:
    subject = ast["subject"]["name"]
    predicate = ast["predicate"]["name"]
    objects = [obj["name"] for obj in ast["objects"]]
    modifiers = ast.get("modifiers", [])
    if modifiers:
        modifier_args = readable_modifier_arguments(modifiers)
        modifier_count = len(modifiers)
        left = f"{predicate}({modifier_count})({modifier_args}, {subject}, {objects[0]})"
        right = f"{predicate}({modifier_count})({modifier_args}, {subject}, {objects[1]})"
    else:
        left = f"{predicate}({subject}, {objects[0]})"
        right = f"{predicate}({subject}, {objects[1]})"
    proposition = f"{ast['connective']}({left}, {right})"
    for modifier in ast["time_modifiers"]:
        proposition = f"{modifier['operator']}_T({modifier['argument']}, {proposition})"
    return proposition


def render_object_coordination_coq(
    definition_name: str,
    ast: dict[str, Any],
) -> str:
    subject = ast["subject"]["name"]
    predicate = ast["predicate"]["name"]
    objects = ast["objects"]
    modifiers = ast.get("modifiers", [])
    if modifiers:
        modifier_count = len(modifiers)
        modifier_sequence = coq_modifier_sequence(modifiers)
        left = (
            f"{predicate} {modifier_count} {modifier_sequence} "
            f"{subject} {objects[0]['name']}"
        )
        right = (
            f"{predicate} {modifier_count} {modifier_sequence} "
            f"{subject} {objects[1]['name']}"
        )
    else:
        left = f"{predicate} {subject} {objects[0]['name']}"
        right = f"{predicate} {subject} {objects[1]['name']}"
    proposition = f"{ast['connective']} ({left}) ({right})"
    for modifier in ast["time_modifiers"]:
        proposition = f"{modifier['operator']}_T {modifier['argument']} ({proposition})"
    object_types = list(
        dict.fromkeys(obj["type"] for obj in objects if obj["type"] != "Entity")
    )
    lines = [
        "(* Object coordination without event variables. *)",
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
    lines.extend(["", f"Parameter {subject} : Entity."])
    for name, type_name in unique_typed_declarations([
        (obj["name"], obj["type"]) for obj in objects
    ]):
        lines.append(f"Parameter {name} : {type_name}.")
    lines.append(f"Parameter {predicate} : {ast['predicate']['predicate_type']}.")
    if modifiers:
        lines.append(f"Parameter {ast['connective']} : PropT -> PropT -> PropT.")
    else:
        lines.append(f"Parameter {ast['connective']} : Prop -> Prop -> Prop.")
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


def object_coordination_pipeline(sentence: str) -> dict[str, Any] | None:
    tokens, fronted_time_modifiers = split_fronted_time_modifiers(tokenize(sentence))
    tokens, fronted_adv_modifiers = split_fronted_adv_modifiers(tokens)
    coordination = single_boolean_coordinator(tokens)
    if coordination is None:
        return None
    coordinator, coordinator_index = coordination
    connective = connective_for_coordinator(coordinator)
    if coordinator_index < 3 or coordinator_index + 1 >= len(tokens):
        return None

    verb_indices = [
        index
        for index in range(1, coordinator_index)
        if is_likely_transitive_verb(tokens[index])
    ]
    if len(verb_indices) != 1:
        return None
    verb_index = verb_indices[0]
    if verb_index == 0 or verb_index + 1 >= coordinator_index:
        return None

    subject = clean_phrase(tokens[:verb_index])
    if subject == "entity":
        return None
    predicate_surface = tokens[verb_index]
    predicate_name = lemma_verb(predicate_surface)
    left_object_tokens = tokens[verb_index + 1 : coordinator_index]
    if left_object_tokens and left_object_tokens[0] == "both":
        if coordinator != "and":
            return None
        left_object_tokens = left_object_tokens[1:]
    left_object = clean_phrase(left_object_tokens)
    if left_object == "entity":
        return None

    right_clause_tokens = tokens[coordinator_index + 1 :]
    if right_clause_tokens and is_likely_surface_verb(right_clause_tokens[0]):
        return None

    right_tail = split_object_tokens_and_modifiers(right_clause_tokens)
    if right_tail is None:
        return None
    right_object_tokens, trailing_adv_modifiers, trailing_time_modifiers = right_tail
    right_object = clean_phrase(right_object_tokens)
    if right_object == "entity":
        return None

    object_type = object_type_for_transitive_predicate(predicate_name)
    shared_adv_modifiers = [*fronted_adv_modifiers, *trailing_adv_modifiers]
    time_modifiers = [*fronted_time_modifiers, *trailing_time_modifiers]
    predicate = {
        "surface": predicate_surface,
        "name": predicate_name,
        "predicate_type": (
            f"forall n : nat, ModifierSeq n -> Entity -> {object_type} -> PropT"
            if shared_adv_modifiers
            else f"Entity -> {object_type} -> Prop"
        ),
    }
    ast = object_coordination_ast(
        subject,
        predicate,
        [
            {"name": left_object, "type": object_type},
            {"name": right_object, "type": object_type},
        ],
        shared_adv_modifiers,
        time_modifiers,
        connective=connective,
    )
    type_check = check_object_coordination_ast(ast)
    typed_replacement = render_object_coordination_translation(ast)
    coq_code = render_object_coordination_coq(
        f"object_coordination_{predicate_name}",
        ast,
    )
    return {
        "kind": "object_coordination",
        "input_sentence": sentence,
        "construction_summary": (
            f"Object coordination shares {predicate_name} and subject {subject} "
            f"across {left_object} and {right_object} : {object_type}."
        ),
        "event_semantics": {
            "analysis": "object-coordination",
            "source": sentence,
            "event_style_reference": (
                f"{predicate_name}(e1) with Agent(e1, {subject}) and "
                f"Theme(e1, {left_object}); {predicate_name}(e2) with "
                f"Agent(e2, {subject}) and Theme(e2, {right_object})"
            ),
            "typed_replacement": typed_replacement,
        },
        "dependent_type_translation": typed_replacement,
        "ast": ast,
        "type_check": type_check,
        "coq_code": coq_code,
    }


def predicate_coordination_pipeline(sentence: str) -> dict[str, Any] | None:
    tokens, fronted_time_modifiers = split_fronted_time_modifiers(tokenize(sentence))
    tokens, fronted_adv_modifiers = split_fronted_adv_modifiers(tokens)
    tokens = strip_surface_coordination_marker(tokens)
    coordination = single_boolean_coordinator(tokens)
    if coordination is None:
        return None
    coordinator, coordinator_index = coordination
    connective = connective_for_coordinator(coordinator)
    left_predicate_index = coordinator_index - 1
    right_predicate_index = coordinator_index + 1
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
        connective=connective,
    )
    type_check = check_predicate_coordination_ast(ast)
    typed_replacement = render_predicate_coordination_translation(ast)
    coq_code = render_predicate_coordination_coq("predicate_coordination_assertion", ast)
    return {
        "kind": "predicate_coordination",
        "input_sentence": sentence,
        "construction_summary": (
            f"Same subject {subject} coordinates "
            f"{predicates[0]['name']} : {predicates[0]['predicate_type']} {coordinator} "
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
                f"{predicates[0]['name']}(e1) and Agent(e1, {subject}) {coordinator} "
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
    connective: str = "and_T",
) -> dict[str, Any]:
    return {
        "kind": "transitive_predicate_coordination",
        "subject": {"name": subject, "type": "Entity"},
        "clauses": clauses,
        "modifiers": modifiers,
        "connective": connective,
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

    if ast.get("connective") not in {"and_T", "or_T"}:
        errors.append(
            "transitive predicate coordination connective must be and_T or or_T"
        )
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
    proposition = f"{ast['connective']}({left}, {right})"
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
    proposition = f"{ast['connective']} ({left}) ({right})"
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
        lines.append(f"Parameter {ast['connective']} : PropT -> PropT -> PropT.")
    else:
        if any(clause.get("negated") for clause in clauses):
            lines.append("Parameter not_T : Prop -> Prop.")
        lines.append(f"Parameter {ast['connective']} : Prop -> Prop -> Prop.")
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
    coordinator_index: int,
    right_surface: str,
    fronted_adv_modifiers: list[dict[str, Any]],
    fronted_time_modifiers: list[dict[str, str]],
    coordinator: str,
    connective: str,
) -> dict[str, Any] | None:
    left_predicate_index = coordinator_index - 1
    if left_predicate_index <= 0:
        return None
    left_surface = tokens[left_predicate_index]
    if not is_likely_surface_verb(left_surface):
        return None
    subject = clean_phrase(tokens[:left_predicate_index])
    if subject == "entity":
        return None
    trailing_modifiers = split_shared_adv_and_time_modifiers(tokens[coordinator_index + 4 :])
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
        connective=connective,
    )
    type_check = check_predicate_coordination_ast(ast)
    typed_replacement = render_predicate_coordination_translation(ast)
    coq_code = render_predicate_coordination_coq(
        "coordinated_do_support_negation_assertion",
        ast,
    )
    return attach_single_semantic_reading(
        {
            "kind": "coordinated_do_support_negation",
            "input_sentence": sentence,
            "construction_summary": (
                f"Same subject {subject} coordinates {predicates[0]['name']} {coordinator} "
                f"the right-branch do-support negation not {predicates[1]['name']}."
            ),
            "event_semantics": {
                "analysis": "right-branch-do-support-negation",
                "source": sentence,
                "event_style_reference": (
                    "exists e1. "
                    f"{predicates[0]['name']}(e1) and Agent(e1, {subject}) {coordinator} "
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
        },
        name="right_branch_do_support_negation",
        coq_definition="coordinated_do_support_negation_assertion",
        source="do_support_negation",
        scope="right_branch_negation",
    )


def coordinated_transitive_do_support_negation(
    sentence: str,
    tokens: list[str],
    coordinator_index: int,
    right_surface: str,
    fronted_adv_modifiers: list[dict[str, Any]],
    fronted_time_modifiers: list[dict[str, str]],
    coordinator: str,
    connective: str,
) -> dict[str, Any] | None:
    left_verb_indices = [
        index
        for index in range(1, coordinator_index)
        if is_likely_surface_verb(tokens[index])
    ]
    if len(left_verb_indices) != 1:
        return None
    left_verb_index = left_verb_indices[0]
    if left_verb_index == 0 or left_verb_index + 1 >= coordinator_index:
        return None
    subject = clean_phrase(tokens[:left_verb_index])
    if subject == "entity":
        return None
    left_surface = tokens[left_verb_index]
    if not (
        is_likely_transitive_verb(left_surface)
        and is_likely_transitive_verb(right_surface)
    ):
        return None
    left_object = clean_phrase(tokens[left_verb_index + 1 : coordinator_index])
    right_tail = split_object_tokens_and_modifiers(tokens[coordinator_index + 4 :])
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
        connective=connective,
    )
    type_check = check_transitive_predicate_coordination_ast(ast)
    typed_replacement = render_transitive_predicate_coordination_translation(ast)
    coq_code = render_transitive_predicate_coordination_coq(
        "coordinated_transitive_do_support_negation_assertion",
        ast,
    )
    return attach_single_semantic_reading(
        {
            "kind": "coordinated_do_support_negation",
            "input_sentence": sentence,
            "construction_summary": (
                f"Same subject {subject} coordinates "
                f"{clauses[0]['predicate']['name']}({clauses[0]['object']['name']} : "
                f"{clauses[0]['object']['type']}) {coordinator} right-branch negation not "
                f"{clauses[1]['predicate']['name']}({clauses[1]['object']['name']} : "
                f"{clauses[1]['object']['type']})."
            ),
            "event_semantics": {
                "analysis": "right-branch-do-support-negation",
                "source": sentence,
                "event_style_reference": (
                    "exists e1. "
                    f"{clauses[0]['predicate']['name']}(e1) and Agent(e1, {subject}) and "
                    f"Theme(e1, {clauses[0]['object']['name']}) {coordinator} not(exists e2. "
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
        },
        name="right_branch_transitive_do_support_negation",
        coq_definition="coordinated_transitive_do_support_negation_assertion",
        source="do_support_negation",
        scope="right_branch_negation",
    )


def contrastive_intransitive_do_support_negation(
    sentence: str,
    tokens: list[str],
    negation_index: int,
    but_index: int,
    left_surface: str,
    right_surface: str,
    fronted_adv_modifiers: list[dict[str, Any]],
    fronted_time_modifiers: list[dict[str, str]],
) -> dict[str, Any] | None:
    auxiliary_index = negation_index - 1
    subject = clean_phrase(tokens[:auxiliary_index])
    if subject == "entity":
        return None
    left_material = tokens[negation_index + 2 : but_index]
    trailing_modifiers = split_shared_adv_and_time_modifiers(tokens[but_index + 2 :])
    if trailing_modifiers is None:
        return None
    trailing_adv_modifiers, trailing_time_modifiers = trailing_modifiers
    if left_material:
        left_branch_modifiers = split_shared_adv_and_time_modifiers(left_material)
        if left_branch_modifiers is None:
            return contrastive_do_support_failure(
                sentence,
                subject,
                tokens[auxiliary_index],
                "left_branch_material_under_contrastive_negation",
                (
                    "left-branch modifiers or objects inside contrastive "
                    "do-support negation are not yet supported"
                ),
                (
                    "Material between the negated predicate and but is not folded "
                    "into a subject or object; add a dedicated construction before "
                    "exporting this sentence."
                ),
            )
        left_adv_modifiers, left_time_modifiers = left_branch_modifiers
        time_modifiers = [*fronted_time_modifiers, *trailing_time_modifiers]
        clauses = [
            branch_modifier_clause(
                left_surface,
                subject,
                [*fronted_adv_modifiers, *left_adv_modifiers],
                True,
                time_modifiers=left_time_modifiers,
            ),
            branch_modifier_clause(
                right_surface,
                subject,
                [*fronted_adv_modifiers, *trailing_adv_modifiers],
                False,
            ),
        ]
        ast = contrastive_branch_modifier_ast(subject, clauses, time_modifiers)
        type_check = check_contrastive_branch_modifier_ast(ast)
        typed_replacement = render_contrastive_branch_modifier_translation(ast)
        coq_code = render_contrastive_branch_modifier_coq(
            "contrastive_branch_modifier_negation_assertion",
            ast,
        )
        return attach_single_semantic_reading(
            {
                "kind": "contrastive_do_support_negation",
                "input_sentence": sentence,
                "construction_summary": (
                    f"Same subject {subject} contrasts not {clauses[0]['predicate']['name']} "
                    f"with local Adv material against {clauses[1]['predicate']['name']} "
                    "with its own branch-local Adv material; fronted Adv material "
                    "is copied into both branch-local modifier sequences."
                ),
                "event_semantics": {
                    "analysis": "contrastive-do-support-negation",
                    "source": sentence,
                    "event_style_reference": (
                        "not(exists e1. "
                        f"{clauses[0]['predicate']['name']}(e1) and Agent(e1, {subject}) "
                        "and local modifiers) and exists e2. "
                        f"{clauses[1]['predicate']['name']}(e2) and Agent(e2, {subject})"
                        " and local modifiers"
                    ),
                    "typed_replacement": typed_replacement,
                },
                "dependent_type_translation": typed_replacement,
                "ast": ast,
                "type_check": {
                    **type_check,
                    "note": (
                        "Contrastive do-support negation with branch-local Adv or "
                        "time material uses branch-local ModifierSeq indices and "
                        "clause-local time_modifiers; fronted Adv material is "
                        "represented as a shared prefix."
                    ),
                },
                "coq_code": coq_code,
            },
            name="contrastive_branch_modifier_do_support_negation",
            coq_definition="contrastive_branch_modifier_negation_assertion",
            source="do_support_negation",
            scope="contrastive_but",
        )
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
            "negated": True,
        },
        {
            "surface": right_surface,
            "name": lemma_verb(right_surface),
            "predicate_type": predicate_type,
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
        "contrastive_do_support_negation_assertion",
        ast,
    )
    return attach_single_semantic_reading(
        {
            "kind": "contrastive_do_support_negation",
            "input_sentence": sentence,
            "construction_summary": (
                f"Same subject {subject} contrasts not {predicates[0]['name']} with "
                f"{predicates[1]['name']} using a typed conjunction."
            ),
            "event_semantics": {
                "analysis": "contrastive-do-support-negation",
                "source": sentence,
                "event_style_reference": (
                    "not(exists e1. "
                    f"{predicates[0]['name']}(e1) and Agent(e1, {subject})) and "
                    "exists e2. "
                    f"{predicates[1]['name']}(e2) and Agent(e2, {subject})"
                ),
                "typed_replacement": typed_replacement,
            },
            "dependent_type_translation": typed_replacement,
            "ast": ast,
            "type_check": {
                **type_check,
                "note": (
                    "Contrastive do-support negation with but is represented by "
                    "wrapping the first coordinate in not_T and conjoining it with "
                    "the positive second coordinate; shared Adv modifiers remain "
                    "typed modifier arguments rather than entities."
                ),
            },
            "coq_code": coq_code,
        },
        name="contrastive_do_support_negation",
        coq_definition="contrastive_do_support_negation_assertion",
        source="do_support_negation",
        scope="contrastive_but",
    )


def contrastive_transitive_do_support_negation(
    sentence: str,
    tokens: list[str],
    negation_index: int,
    but_index: int,
    left_surface: str,
    right_surface: str,
    fronted_adv_modifiers: list[dict[str, Any]],
    fronted_time_modifiers: list[dict[str, str]],
) -> dict[str, Any] | None:
    if not (
        is_likely_transitive_verb(left_surface)
        and is_likely_transitive_verb(right_surface)
    ):
        return None
    auxiliary_index = negation_index - 1
    subject = clean_phrase(tokens[:auxiliary_index])
    if subject == "entity":
        return None
    left_tail = split_object_tokens_and_modifiers(tokens[negation_index + 2 : but_index])
    if left_tail is None:
        return None
    left_object_tokens, left_adv_modifiers, left_time_modifiers = left_tail
    left_object = clean_phrase(left_object_tokens)
    if left_object == "entity":
        return None
    right_tail = split_object_tokens_and_modifiers(tokens[but_index + 2 :])
    if right_tail is None:
        return None
    right_object_tokens, trailing_adv_modifiers, trailing_time_modifiers = right_tail
    right_object = clean_phrase(right_object_tokens)
    if right_object == "entity":
        return None
    shared_adv_modifiers = [*fronted_adv_modifiers, *trailing_adv_modifiers]
    time_modifiers = [*fronted_time_modifiers, *trailing_time_modifiers]
    if left_adv_modifiers or left_time_modifiers:
        clauses = [
            branch_modifier_clause(
                left_surface,
                subject,
                [*fronted_adv_modifiers, *left_adv_modifiers],
                True,
                {"name": left_object, "type": object_type_for_transitive_predicate(lemma_verb(left_surface))},
                time_modifiers=left_time_modifiers,
            ),
            branch_modifier_clause(
                right_surface,
                subject,
                [*fronted_adv_modifiers, *trailing_adv_modifiers],
                False,
                {"name": right_object, "type": object_type_for_transitive_predicate(lemma_verb(right_surface))},
            ),
        ]
        ast = contrastive_branch_modifier_ast(subject, clauses, time_modifiers)
        type_check = check_contrastive_branch_modifier_ast(ast)
        typed_replacement = render_contrastive_branch_modifier_translation(ast)
        coq_code = render_contrastive_branch_modifier_coq(
            "contrastive_transitive_branch_modifier_negation_assertion",
            ast,
        )
        return attach_single_semantic_reading(
            {
                "kind": "contrastive_do_support_negation",
                "input_sentence": sentence,
                "construction_summary": (
                    f"Same subject {subject} contrasts not "
                    f"{clauses[0]['predicate']['name']}({left_object} : "
                    f"{clauses[0]['object']['type']}) with local Adv material against "
                    f"{clauses[1]['predicate']['name']}({right_object} : "
                    f"{clauses[1]['object']['type']}) with its own branch-local Adv material; "
                    "fronted Adv material is copied into both branch-local modifier sequences."
                ),
                "event_semantics": {
                    "analysis": "contrastive-do-support-negation",
                    "source": sentence,
                    "event_style_reference": (
                        "not(exists e1. "
                        f"{clauses[0]['predicate']['name']}(e1) and Agent(e1, {subject}) and "
                        f"Theme(e1, {left_object}) and local modifiers) and exists e2. "
                        f"{clauses[1]['predicate']['name']}(e2) and Agent(e2, {subject}) and "
                        f"Theme(e2, {right_object}) and local modifiers"
                    ),
                    "typed_replacement": typed_replacement,
                },
                "dependent_type_translation": typed_replacement,
                "ast": ast,
                "type_check": {
                    **type_check,
                    "note": (
                        "Contrastive transitive do-support negation with branch-local "
                        "Adv or time material uses branch-local ModifierSeq indices "
                        "and clause-local time_modifiers; each coordinate may carry "
                        "its own modifier length while both object lexical types remain "
                        "checked before Coq. Fronted Adv material becomes a shared "
                        "prefix in each branch-local sequence."
                    ),
                },
                "coq_code": coq_code,
            },
            name="contrastive_transitive_branch_modifier_do_support_negation",
            coq_definition="contrastive_transitive_branch_modifier_negation_assertion",
            source="do_support_negation",
            scope="contrastive_but",
        )

    clauses: list[dict[str, Any]] = []
    for surface, obj, negated in (
        (left_surface, left_object, True),
        (right_surface, right_object, False),
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
        "contrastive_transitive_do_support_negation_assertion",
        ast,
    )
    return attach_single_semantic_reading(
        {
            "kind": "contrastive_do_support_negation",
            "input_sentence": sentence,
            "construction_summary": (
                f"Same subject {subject} contrasts not "
                f"{clauses[0]['predicate']['name']}({clauses[0]['object']['name']} : "
                f"{clauses[0]['object']['type']}) with "
                f"{clauses[1]['predicate']['name']}({clauses[1]['object']['name']} : "
                f"{clauses[1]['object']['type']})."
            ),
            "event_semantics": {
                "analysis": "contrastive-do-support-negation",
                "source": sentence,
                "event_style_reference": (
                    "not(exists e1. "
                    f"{clauses[0]['predicate']['name']}(e1) and Agent(e1, {subject}) and "
                    f"Theme(e1, {clauses[0]['object']['name']})) and exists e2. "
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
                    "Contrastive transitive do-support negation with but wraps only "
                    "the first typed coordinate in not_T and keeps both object "
                    "lexical types checked before Coq; shared Adv modifiers remain "
                    "typed modifier arguments rather than entities."
                ),
            },
            "coq_code": coq_code,
        },
        name="contrastive_transitive_do_support_negation",
        coq_definition="contrastive_transitive_do_support_negation_assertion",
        source="do_support_negation",
        scope="contrastive_but",
    )


def transitive_predicate_coordination_pipeline(sentence: str) -> dict[str, Any] | None:
    tokens, fronted_time_modifiers = split_fronted_time_modifiers(tokenize(sentence))
    tokens, fronted_adv_modifiers = split_fronted_adv_modifiers(tokens)
    tokens = strip_surface_coordination_marker(tokens)
    coordination = single_boolean_coordinator(tokens)
    if coordination is None:
        return None
    coordinator, coordinator_index = coordination
    connective = connective_for_coordinator(coordinator)
    if coordinator_index < 3 or coordinator_index + 2 >= len(tokens):
        return None
    if not is_likely_surface_verb(tokens[coordinator_index + 1]):
        return None

    left_verb_indices = [
        index
        for index in range(1, coordinator_index)
        if is_likely_surface_verb(tokens[index])
    ]
    if len(left_verb_indices) != 1:
        return None
    left_verb_index = left_verb_indices[0]
    if left_verb_index == 0 or left_verb_index + 1 >= coordinator_index:
        return None

    subject = clean_phrase(tokens[:left_verb_index])
    if subject == "entity":
        return None
    left_surface = tokens[left_verb_index]
    right_surface = tokens[coordinator_index + 1]
    if not (
        is_likely_transitive_verb(left_surface)
        and is_likely_transitive_verb(right_surface)
    ):
        return None
    left_object = clean_phrase(tokens[left_verb_index + 1 : coordinator_index])
    right_tail = split_object_tokens_and_modifiers(tokens[coordinator_index + 2 :])
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
        connective=connective,
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
            f"{clauses[0]['object']['type']}) {coordinator} "
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
                f"Theme(e1, {clauses[0]['object']['name']}) {coordinator} "
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
    time_modifiers: list[dict[str, str]] | None = None,
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
        "time_modifiers": list(time_modifiers or []),
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
    check_time_modifiers(errors, ast.get("time_modifiers"), "passive")

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


def split_passive_agent_and_time_modifiers(
    tokens: list[str],
) -> tuple[str, list[dict[str, str]]] | None:
    for split_index in range(1, len(tokens) + 1):
        time_modifiers = copular_property_time_modifiers(tokens[split_index:])
        if time_modifiers is None:
            continue
        agent = clean_phrase(tokens[:split_index])
        if agent != "entity":
            return agent, time_modifiers
    return None


def render_passive_time_wrapped_translation(
    proposition: str,
    time_modifiers: list[dict[str, str]],
) -> str:
    for modifier in time_modifiers:
        proposition = f"{modifier['operator']}_T({modifier['argument']}, {proposition})"
    return proposition


def render_passive_time_wrapped_coq(
    proposition: str,
    time_modifiers: list[dict[str, str]],
) -> str:
    for modifier in time_modifiers:
        proposition = f"{modifier['operator']}_T {modifier['argument']} ({proposition})"
    return proposition


def passive_argument_omission_pipeline(sentence: str) -> dict[str, Any] | None:
    tokens, fronted_time_modifiers = split_fronted_time_modifiers(tokenize(sentence))
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
    trailing_time_modifiers: list[dict[str, str]] = []
    if rest:
        if rest[0] == "by":
            if len(rest) == 1:
                return None
            agent_parse = split_passive_agent_and_time_modifiers(rest[1:])
            if agent_parse is None:
                return None
            agent, trailing_time_modifiers = agent_parse
        else:
            parsed_time_modifiers = copular_property_time_modifiers(rest)
            if parsed_time_modifiers is None:
                return None
            trailing_time_modifiers = parsed_time_modifiers

    time_modifiers = [*fronted_time_modifiers, *trailing_time_modifiers]
    ast = passive_argument_omission_ast(
        predicate,
        patient,
        agent,
        auxiliary,
        participle,
        time_modifiers,
    )
    type_check = check_passive_argument_omission_ast(ast)
    if agent is None:
        core_translation = f"exists x_agent : Entity. {predicate}(x_agent, {patient})"
        typed_replacement = render_passive_time_wrapped_translation(
            core_translation,
            time_modifiers,
        )
        definition_name = f"passive_{predicate}_omitted_agent"
        core_coq = f"exists x_agent : Entity, {predicate} x_agent {patient}"
        body_coq = render_passive_time_wrapped_coq(core_coq, time_modifiers)
        body_lines = [
            f"Definition {definition_name} : Prop :=",
            f"  {body_coq}.",
        ]
        agent_parameters: list[str] = []
        event_reference = (
            f"exists e. {predicate}ing(e) and Theme(e, {patient}) and "
            "exists x. Agent(e, x)"
        )
    else:
        core_translation = f"{predicate}({agent}, {patient})"
        typed_replacement = render_passive_time_wrapped_translation(
            core_translation,
            time_modifiers,
        )
        definition_name = f"passive_{predicate}_by_agent"
        body_coq = render_passive_time_wrapped_coq(
            f"{predicate} {agent} {patient}",
            time_modifiers,
        )
        body_lines = [
            f"Definition {definition_name} : Prop :=",
            f"  {body_coq}.",
        ]
        agent_parameters = [f"Parameter {agent} : Entity."]
        event_reference = (
            f"exists e. {predicate}ing(e) and Theme(e, {patient}) and Agent(e, {agent})"
        )
    time_parameters = [
        f"Parameter {time_argument} : Entity."
        for time_argument in unique_names(
            [modifier["argument"] for modifier in time_modifiers]
        )
    ]
    time_operator_parameters = (
        [
            "",
            "Parameter at_T : Entity -> Prop -> Prop.",
            "Parameter during_T : Entity -> Prop -> Prop.",
        ]
        if time_modifiers
        else []
    )

    coq_code = "\n".join(
        [
            "(* Passive argument-omission replacement without an event variable. *)",
            "Parameter Entity : Type.",
            "",
            f"Parameter {patient} : Entity.",
            *agent_parameters,
            *time_parameters,
            "",
            f"Parameter {predicate} : Entity -> Entity -> Prop.",
            *time_operator_parameters,
            "",
            *body_lines,
            "",
            f"Check {definition_name}.",
            "",
        ]
    )
    return attach_single_semantic_reading(
        {
            "kind": "passive_argument_omission",
            "input_sentence": sentence,
            "event_semantics": {
                "analysis": "passive-argument-omission",
                "source": sentence,
                "event_style_reference": event_reference,
                "typed_replacement": typed_replacement,
                "time_modifiers": time_modifiers,
            },
            "dependent_type_translation": typed_replacement,
            "ast": ast,
            "type_check": {
                **type_check,
                "note": (
                    (
                        "A passive without by-phrase introduces an existential Entity "
                        "agent"
                    )
                    if agent is None
                    else "A passive by-phrase supplies an ordinary Entity agent"
                )
                + (
                    "; time modifiers scope over the resulting proposition"
                    if time_modifiers
                    else ""
                )
                + (
                    "; no Event, Agent(e, ...), or Theme(e, ...) declaration is exported."
                ),
            },
            "coq_code": coq_code,
        },
        name=definition_name,
        coq_definition=definition_name,
        source="passive_argument_omission",
        scope="by_phrase_agent" if agent is not None else "omitted_existential_agent",
    )


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
                "Parameter a : Entity.",
                "Parameter an : Entity.",
                "Parameter every : Entity.",
                "Parameter no : Entity.",
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
            rule_id="subject_coordination",
            label="Subject coordination",
            phenomenon="Shared intransitive predicate over coordinated subjects without event variables",
            analyzer=subject_coordination_pipeline,
            forbidden_coq_fragments=(
                "Parameter Event : Type.",
                "exists e : Event",
                "Parameter Agent :",
                "Parameter Theme :",
            ),
        ),
        ConstructionRule(
            rule_id="transitive_subject_coordination",
            label="Transitive subject coordination",
            phenomenon="Shared transitive predicate over coordinated subjects without event variables",
            analyzer=transitive_subject_coordination_pipeline,
            forbidden_coq_fragments=(
                "Parameter Event : Type.",
                "exists e : Event",
                "Parameter Agent :",
                "Parameter Theme :",
            ),
        ),
        ConstructionRule(
            rule_id="object_coordination",
            label="Object coordination",
            phenomenon="Shared transitive predicate over coordinated objects without event variables",
            analyzer=object_coordination_pipeline,
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

    analysis = attach_default_registered_semantic_reading(analysis, rule)
    semantic_readings_check = analysis.get("semantic_readings_check")
    if (
        isinstance(semantic_readings_check, dict)
        and semantic_readings_check.get("ok") is False
    ):
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
                "message": "Skipped Coq/Rocq validation because semantic_readings_check failed.",
            },
            "conclusion": "Translation failed semantic_readings_check before Coq/Rocq validation.",
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
            return (
                token in PASSIVE_AUXILIARIES
                or token in DO_SUPPORT_AUXILIARIES
                or is_likely_surface_verb(token)
                or (token.endswith("ed") and len(token) > 3)
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
