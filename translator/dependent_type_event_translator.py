#!/usr/bin/env python3
"""
Prototype translator from Davidsonian event semantics to a dependent-type
rendering without event variables.

Run:
  python3 dependent_type_event_translator.py example.json --pretty
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from translator.surface_lexicon import (
    SURFACE_LEXICON_SOURCE,
    modifier_semantic_role,
    modifier_surface_audit,
)

ENTITY = "e"
PROP = "t"
ADV = "ADV"

ROLE_ORDER = [
    "Agent", "Actor", "Experiencer", "Theme", "Patient", "Object",
    "Recipient", "Goal", "Source", "Instrument", "Location",
]
TIME_PREDS = {"at", "during", "before", "after", "until", "since"}
ROLE_PREDS = set(ROLE_ORDER)
RESULT_PREDS = {"Result", "ResultState"}
COUNT_PREDS = {"count", "times"}
COUNT_WORDS = {
    "once": 1,
    "twice": 2,
    "thrice": 3,
}
OMITTED_THEME_TYPES = {
    "eat": "Food",
    "read": "Readable",
    "drink": "Drinkable",
}


@dataclass(frozen=True)
class StateLexiconEntry:
    scale: str
    default_source_state: str | None = None
    allow_unknown_source: bool = False


STATE_LEXICON = {
    "alive": StateLexiconEntry("life_scale", default_source_state="dead"),
    "broken": StateLexiconEntry("integrity_scale", default_source_state="intact"),
    "clean": StateLexiconEntry("cleanliness_scale", default_source_state="dirty"),
    "closed": StateLexiconEntry("access_scale", default_source_state="open"),
    "dead": StateLexiconEntry("life_scale", default_source_state="alive"),
    "dirty": StateLexiconEntry("cleanliness_scale", default_source_state="clean"),
    "dry": StateLexiconEntry("moisture_scale", default_source_state="wet"),
    "empty": StateLexiconEntry("content_scale", default_source_state="full"),
    "flat": StateLexiconEntry("shape_scale", default_source_state="not_flat"),
    "frozen": StateLexiconEntry("phase_scale", default_source_state="liquid"),
    "full": StateLexiconEntry("content_scale", default_source_state="empty"),
    "intact": StateLexiconEntry("integrity_scale"),
    "liquid": StateLexiconEntry("phase_scale", default_source_state="solid"),
    "melted": StateLexiconEntry("phase_scale", default_source_state="solid"),
    "not_flat": StateLexiconEntry("shape_scale", default_source_state="flat"),
    "open": StateLexiconEntry("access_scale", default_source_state="closed"),
    "red": StateLexiconEntry("color_scale", allow_unknown_source=True),
    "round": StateLexiconEntry("shape_scale", allow_unknown_source=True),
    "solid": StateLexiconEntry("phase_scale", default_source_state="liquid"),
    "straight": StateLexiconEntry("shape_scale", allow_unknown_source=True),
    "wet": StateLexiconEntry("moisture_scale", default_source_state="dry"),
}
STATE_SCALE_BY_STATE = {
    state: entry.scale for state, entry in STATE_LEXICON.items()
}
SOURCE_STATE_BY_TARGET_STATE = {
    state: entry.default_source_state
    for state, entry in STATE_LEXICON.items()
    if entry.default_source_state is not None
}
INCOMPATIBLE_STATE_PAIRS = frozenset(
    frozenset((state, source_state))
    for state, source_state in SOURCE_STATE_BY_TARGET_STATE.items()
    if (
        source_state in STATE_LEXICON
        and STATE_LEXICON[state].scale == STATE_LEXICON[source_state].scale
        and state != source_state
    )
)


@dataclass(frozen=True)
class Atom:
    pred: str
    args: tuple[str, ...]


@dataclass
class EventAnalysis:
    event_var: str
    verb: str
    roles: dict[str, str]
    adverbs: list[str]
    times: list[Atom]
    results: list[Atom]
    counts: list[str]
    residuals: list[Atom]


Term = dict[str, Any]
TypeCheck = dict[str, Any]
EXPORT_TARGETS = ("lean", "coq")
LexicalApplicationSchema = tuple[
    str,
    str,
    int,
    str,
    tuple[str, ...],
    tuple[str, ...],
    tuple[tuple[str, str], ...],
]


def flatten_conjunction(expr: dict[str, Any]) -> list[Atom]:
    if "and" in expr:
        atoms: list[Atom] = []
        for item in expr["and"]:
            atoms.extend(flatten_conjunction(item))
        return atoms
    if "pred" in expr and "args" in expr:
        return [Atom(str(expr["pred"]), tuple(map(str, expr["args"])))]
    raise ValueError(f"Unsupported formula fragment: {expr!r}")


def dependent_signature(verb: str, arity: int) -> str:
    if arity == 1:
        family = "IV-ADV"
    elif arity == 2:
        family = "TV-ADV"
    else:
        family = f"V{arity}-ADV"
    signature = " -> ".join(dependent_argument_types(verb, arity) + [PROP])
    return f"{verb} : Pi n : N. {family}(n); {family}(n) = ADV^n -> {signature}"


def dependent_argument_types(verb: str, arity: int) -> list[str]:
    return [
        ENTITY if argument_type == "Entity" else argument_type
        for argument_type in application_argument_types(verb, arity)
    ]


def analyze_event_formula(data: dict[str, Any]) -> EventAnalysis:
    event_vars = data.get("exists", [])
    if not event_vars:
        raise ValueError("Expected an existentially bound event variable in 'exists'.")
    event_var = str(event_vars[0])
    atoms = flatten_conjunction(data["body"])

    verb_atoms = [
        atom for atom in atoms
        if atom.args == (event_var,)
        and atom.pred not in TIME_PREDS
        and atom.pred not in ROLE_PREDS
        and atom.pred[:1].islower()
    ]
    if not verb_atoms:
        raise ValueError("Could not identify the core event predicate, e.g. butter(e).")
    verb = verb_atoms[0].pred

    roles: dict[str, str] = {}
    adverbs: list[str] = []
    times: list[Atom] = []
    results: list[Atom] = []
    counts: list[str] = []
    residuals: list[Atom] = []

    for atom in atoms:
        if atom == verb_atoms[0]:
            continue
        if atom.pred in ROLE_PREDS and len(atom.args) == 2 and atom.args[0] == event_var:
            roles[atom.pred] = atom.args[1]
        elif atom.pred in TIME_PREDS and len(atom.args) >= 2 and atom.args[0] == event_var:
            times.append(atom)
        elif atom.pred in RESULT_PREDS and len(atom.args) >= 2 and atom.args[0] == event_var:
            results.append(atom)
        elif atom.pred in COUNT_PREDS and len(atom.args) == 2 and atom.args[0] == event_var:
            counts.append(atom.args[1])
        elif atom.pred in COUNT_WORDS and atom.args == (event_var,):
            counts.append(str(COUNT_WORDS[atom.pred]))
        elif atom.args == (event_var,):
            adverbs.append(atom.pred)
        elif len(atom.args) >= 1 and atom.args[0] == event_var:
            adverbs.append(render_modifier(atom))
        else:
            residuals.append(atom)

    return EventAnalysis(event_var, verb, roles, adverbs, times, results, counts, residuals)


def ordered_arguments(roles: dict[str, str]) -> list[str]:
    args: list[str] = []
    for role in ROLE_ORDER:
        if role in roles:
            args.append(roles[role])
    for role in sorted(set(roles) - set(ROLE_ORDER)):
        args.append(roles[role])
    return args


def lexical_role_type(verb: str, role: str) -> str:
    if verb in OMITTED_THEME_TYPES and role in {"Theme", "Patient", "Object"}:
        return OMITTED_THEME_TYPES[verb]
    return "Entity"


def ordered_role_entries(roles: dict[str, str], verb: str = "") -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    for role in ROLE_ORDER:
        if role in roles:
            entries.append(
                {
                    "role": role,
                    "value": roles[role],
                    "type": lexical_role_type(verb, role),
                    "source": "explicit",
                }
            )
    for role in sorted(set(roles) - set(ROLE_ORDER)):
        entries.append(
            {
                "role": role,
                "value": roles[role],
                "type": lexical_role_type(verb, role),
                "source": "explicit",
            }
        )
    return entries


def render_modifier(atom: Atom) -> str:
    rest = ", ".join(atom.args[1:])
    if atom.pred == "at_loc":
        return f"at({rest})" if rest else "at"
    return f"{atom.pred}({rest})" if rest else atom.pred


def render_time_operator(atom: Atom, proposition: str) -> str:
    if len(atom.args) == 2:
        return f"{atom.pred}_T({atom.args[1]}, {proposition})"
    rest = ", ".join(atom.args[1:])
    return f"{atom.pred}_T(({rest}), {proposition})"


def modifier_vector(adverbs: list[str]) -> Term:
    length = len(adverbs)
    return {
        "kind": "modifier_vector",
        "length": length,
        "items": [
            {
                "modifier": modifier,
                "tail_length": length - index - 1,
            }
            for index, modifier in enumerate(adverbs)
        ],
    }


def modifier_roles(modifiers: list[str]) -> Term:
    def entry_for(modifier: str) -> dict[str, Any]:
        semantic_role = modifier_semantic_role(modifier)
        return {
            "modifier": modifier,
            "type": "Adv",
            "semantic_role": semantic_role,
            "source": "modifier",
            "surface_lexicon": modifier_surface_audit(
                modifier,
                "Adv",
                semantic_role,
            ),
        }

    return {
        "kind": "modifier_roles",
        "roles": [entry_for(modifier) for modifier in modifiers],
    }


def role_frame(entries: list[dict[str, str]]) -> Term:
    return {
        "kind": "role_frame",
        "roles": entries,
    }


def role_order_key(role: str) -> tuple[int, int | str]:
    if role in ROLE_ORDER:
        return (0, ROLE_ORDER.index(role))
    return (1, role)


def application_term(
    verb: str,
    adverbs: list[str],
    args: list[str],
    role_entries: list[dict[str, str]],
) -> Term:
    return {
        "kind": "application",
        "function": verb,
        "adverb_count": len(adverbs),
        "modifiers": adverbs,
        "modifier_vector": modifier_vector(adverbs),
        "modifier_roles": modifier_roles(adverbs),
        "arguments": args,
        "role_frame": role_frame(role_entries),
    }


def sigma_term(witness: str, witness_type: str, body: Term) -> Term:
    return {
        "kind": "sigma",
        "witness": witness,
        "type": witness_type,
        "body": body,
    }


def repeat_term(count: str, body: Term) -> Term:
    return {
        "kind": "repeat",
        "count": count,
        "body": body,
    }


def time_term(atom: Atom, body: Term) -> Term:
    return {
        "kind": "time",
        "operator": atom.pred,
        "arguments": list(atom.args[1:]),
        "body": body,
    }


def not_term(body: Term) -> Term:
    return {
        "kind": "not",
        "body": body,
    }


def infer_state_scale(state: str) -> str:
    if state == "_":
        return "unknown_scale"
    entry = STATE_LEXICON.get(state)
    if entry is not None:
        return entry.scale
    return f"{state}_scale"


def infer_source_state(target_state: str) -> str:
    entry = STATE_LEXICON.get(target_state)
    if entry is None or entry.default_source_state is None:
        return "_"
    return entry.default_source_state


def state_lexicon_metadata(state: str) -> dict[str, Any]:
    entry = STATE_LEXICON.get(state)
    if entry is None:
        return {
            "state": state,
            "scale": infer_state_scale(state),
            "default_source_state": None,
            "source_policy": "derived_scale_no_known_prestate",
        }
    if entry.default_source_state is not None:
        return {
            "state": state,
            "scale": entry.scale,
            "default_source_state": entry.default_source_state,
            "source_policy": "lexical_prestate",
        }
    return {
        "state": state,
        "scale": entry.scale,
        "default_source_state": None,
        "source_policy": (
            "unknown_source_allowed"
            if entry.allow_unknown_source
            else "source_state_only"
        ),
    }


def transition_term(theme: str, source_state: str, target_state: str) -> Term:
    return {
        "kind": "transition",
        "theme": theme,
        "state_scale": infer_state_scale(target_state),
        "source_state": source_state,
        "target_state": target_state,
    }


def cause_term(causer: str, effect: Term, activity: Term | None = None) -> Term:
    term: Term = {
        "kind": "cause",
        "causer": causer,
        "effect": effect,
    }
    if activity is not None:
        term["activity"] = activity
    return term


def render_term(term: Term) -> str:
    kind = term["kind"]
    if kind == "application":
        rendered = f"{term['function']}({term['adverb_count']})"
        args = term["modifiers"] + term["arguments"]
        if args:
            rendered += "(" + ", ".join(args) + ")"
        return rendered
    if kind == "sigma":
        return f"Sigma {term['witness']} : {term['type']}. {render_term(term['body'])}"
    if kind == "repeat":
        return f"repeat({term['count']}, {render_term(term['body'])})"
    if kind == "time":
        args = term["arguments"]
        rendered_args = args[0] if len(args) == 1 else "(" + ", ".join(args) + ")"
        return f"{term['operator']}_T({rendered_args}, {render_term(term['body'])})"
    if kind == "not":
        return f"not_T({render_term(term['body'])})"
    if kind == "transition":
        return (
            f"Transition({term['theme']}, {term['state_scale']}, {term['source_state']}, "
            f"{term['target_state']})"
        )
    if kind == "cause":
        return f"Cause({term['causer']}, {render_term(term['effect'])})"
    raise ValueError(f"Unknown term kind: {kind!r}")


def check_term(term: Term) -> TypeCheck:
    errors: list[str] = []

    def check(current: Term, path: str) -> str:
        kind = current.get("kind")
        if kind == "application":
            function = current.get("function")
            modifiers = current.get("modifiers")
            vector = current.get("modifier_vector")
            modifier_role_info = current.get("modifier_roles")
            arguments = current.get("arguments")
            frame = current.get("role_frame")
            adverb_count = current.get("adverb_count")
            if not isinstance(function, str) or not function:
                errors.append(f"{path}: application.function must be a non-empty string")
            if not isinstance(modifiers, list) or not all(isinstance(x, str) for x in modifiers):
                errors.append(f"{path}: application.modifiers must be a list of strings")
                modifiers = []
            vector_items: list[dict[str, Any]] = []
            vector_length: int | None = None
            if not isinstance(vector, dict):
                errors.append(f"{path}: application.modifier_vector must be a vector object")
            else:
                if vector.get("kind") != "modifier_vector":
                    errors.append(
                        f"{path}: application.modifier_vector.kind must be modifier_vector"
                    )
                length = vector.get("length")
                items = vector.get("items")
                if not isinstance(length, int) or length < 0:
                    errors.append(
                        f"{path}: application.modifier_vector.length must be a natural number"
                    )
                else:
                    vector_length = length
                if not isinstance(items, list):
                    errors.append(f"{path}: application.modifier_vector.items must be a list")
                else:
                    for index, item in enumerate(items):
                        if not isinstance(item, dict):
                            errors.append(
                                f"{path}: application.modifier_vector.items[{index}] must be an object"
                            )
                            continue
                        modifier = item.get("modifier")
                        tail_length = item.get("tail_length")
                        if not isinstance(modifier, str) or not modifier:
                            errors.append(
                                f"{path}: application.modifier_vector.items[{index}].modifier "
                                "must be a non-empty string"
                            )
                        if not isinstance(tail_length, int) or tail_length < 0:
                            errors.append(
                                f"{path}: application.modifier_vector.items[{index}].tail_length "
                                "must be a natural number"
                            )
                        vector_items.append(item)
                    if vector_length is not None and vector_length != len(items):
                        errors.append(
                            f"{path}: application.modifier_vector.length={vector_length} "
                            f"does not match {len(items)} vector item(s)"
                        )
            vector_modifiers = [
                item.get("modifier")
                for item in vector_items
                if isinstance(item.get("modifier"), str)
            ]
            if vector_modifiers and vector_modifiers != modifiers:
                errors.append(
                    f"{path}: application.modifier_vector modifiers do not match "
                    "application.modifiers"
                )
            if vector_length is not None:
                if vector_length != len(modifiers):
                    errors.append(
                        f"{path}: application.modifier_vector.length={vector_length} "
                        f"does not match {len(modifiers)} modifier(s)"
                    )
                for index, item in enumerate(vector_items):
                    expected_tail = vector_length - index - 1
                    if item.get("tail_length") != expected_tail:
                        errors.append(
                            f"{path}: application.modifier_vector.items[{index}].tail_length="
                            f"{item.get('tail_length')} does not match expected "
                            f"tail length {expected_tail}"
                        )
            if modifier_role_info is not None:
                if not isinstance(modifier_role_info, dict):
                    errors.append(f"{path}: application.modifier_roles must be an object")
                else:
                    if modifier_role_info.get("kind") != "modifier_roles":
                        errors.append(
                            f"{path}: application.modifier_roles.kind must be modifier_roles"
                        )
                    modifier_role_entries = modifier_role_info.get("roles")
                    if not isinstance(modifier_role_entries, list):
                        errors.append(
                            f"{path}: application.modifier_roles.roles must be a list"
                        )
                    else:
                        if len(modifier_role_entries) != len(modifiers):
                            errors.append(
                                f"{path}: application.modifier_roles has "
                                f"{len(modifier_role_entries)} role(s) for {len(modifiers)} modifier(s)"
                            )
                        for index, entry in enumerate(modifier_role_entries):
                            if not isinstance(entry, dict):
                                errors.append(
                                    f"{path}: application.modifier_roles.roles[{index}] "
                                    "must be an object"
                                )
                                continue
                            modifier = entry.get("modifier")
                            modifier_type = entry.get("type")
                            semantic_role = entry.get("semantic_role")
                            source = entry.get("source")
                            if not isinstance(modifier, str) or not modifier:
                                errors.append(
                                    f"{path}: application.modifier_roles.roles[{index}].modifier "
                                    "must be a non-empty string"
                                )
                            elif index < len(modifiers) and modifier != modifiers[index]:
                                errors.append(
                                    f"{path}: application.modifier_roles.roles[{index}].modifier "
                                    "does not match application.modifiers"
                                )
                            if modifier_type != "Adv":
                                errors.append(
                                    f"{path}: application.modifier_roles.roles[{index}].type "
                                    "must be Adv"
                                )
                            if not isinstance(semantic_role, str) or not semantic_role:
                                errors.append(
                                    f"{path}: application.modifier_roles.roles[{index}].semantic_role "
                                    "must be a non-empty string"
                                )
                            elif isinstance(modifier, str) and modifier:
                                expected_role = modifier_semantic_role(modifier)
                                if semantic_role != expected_role:
                                    errors.append(
                                        f"{path}: application.modifier_roles.roles[{index}].semantic_role "
                                        f"must be {expected_role} for {modifier}"
                                    )
                            if source != "modifier":
                                errors.append(
                                    f"{path}: application.modifier_roles.roles[{index}].source "
                                    "must be modifier"
                                )
                            surface_lexicon = entry.get("surface_lexicon")
                            if not isinstance(surface_lexicon, dict):
                                errors.append(
                                    f"{path}: application.modifier_roles.roles[{index}].surface_lexicon "
                                    "must be an object"
                                )
                            else:
                                if surface_lexicon.get("surface_modifier") != modifier:
                                    errors.append(
                                        f"{path}: application.modifier_roles.roles[{index}].surface_lexicon.surface_modifier "
                                        "must match modifier"
                                    )
                                if isinstance(modifier, str) and modifier:
                                    expected_normalized = export_atom(modifier, "coq")
                                    if surface_lexicon.get("normalized_modifier") != expected_normalized:
                                        errors.append(
                                            f"{path}: application.modifier_roles.roles[{index}].surface_lexicon.normalized_modifier "
                                            f"must be {expected_normalized}"
                                        )
                                if surface_lexicon.get("type") != modifier_type:
                                    errors.append(
                                        f"{path}: application.modifier_roles.roles[{index}].surface_lexicon.type "
                                        "must match modifier type"
                                    )
                                if surface_lexicon.get("semantic_role") != semantic_role:
                                    errors.append(
                                        f"{path}: application.modifier_roles.roles[{index}].surface_lexicon.semantic_role "
                                        "must match semantic_role"
                                    )
                                if surface_lexicon.get("source") != SURFACE_LEXICON_SOURCE:
                                    errors.append(
                                        f"{path}: application.modifier_roles.roles[{index}].surface_lexicon.source "
                                        "must identify the surface lexicon"
                                    )
            valid_arguments = isinstance(arguments, list) and all(
                isinstance(x, str) for x in arguments
            )
            if not valid_arguments:
                errors.append(f"{path}: application.arguments must be a list of strings")
                arguments = []
            frame_values: list[str] = []
            if not isinstance(frame, dict):
                errors.append(f"{path}: application.role_frame must be a role_frame object")
            else:
                if frame.get("kind") != "role_frame":
                    errors.append(f"{path}: application.role_frame.kind must be role_frame")
                roles = frame.get("roles")
                if not isinstance(roles, list):
                    errors.append(f"{path}: application.role_frame.roles must be a list")
                else:
                    seen_roles: set[str] = set()
                    role_labels: list[str] = []
                    role_types: list[str] = []
                    for index, role_entry in enumerate(roles):
                        if not isinstance(role_entry, dict):
                            errors.append(
                                f"{path}: application.role_frame.roles[{index}] must be an object"
                            )
                            continue
                        role = role_entry.get("role")
                        value = role_entry.get("value")
                        role_type = role_entry.get("type")
                        source = role_entry.get("source", "explicit")
                        if not isinstance(role, str) or not role:
                            errors.append(
                                f"{path}: application.role_frame.roles[{index}].role "
                                "must be a non-empty string"
                            )
                        elif role in seen_roles:
                            errors.append(
                                f"{path}: application.role_frame has duplicate role {role}"
                            )
                        else:
                            seen_roles.add(role)
                            role_labels.append(role)
                        if not isinstance(value, str) or not value:
                            errors.append(
                                f"{path}: application.role_frame.roles[{index}].value "
                                "must be a non-empty string"
                            )
                        else:
                            frame_values.append(value)
                        if not isinstance(role_type, str) or not role_type:
                            errors.append(
                                f"{path}: application.role_frame.roles[{index}].type "
                                "must be a non-empty string"
                            )
                        else:
                            role_types.append(role_type)
                        if source not in {"explicit", "omitted"}:
                            errors.append(
                                f"{path}: application.role_frame.roles[{index}].source "
                                "must be explicit or omitted"
                            )
                    if valid_arguments and frame_values != arguments:
                        errors.append(
                            f"{path}: application.role_frame values do not match "
                            "application.arguments"
                        )
                    expected_role_labels = sorted(role_labels, key=role_order_key)
                    if role_labels != expected_role_labels:
                        errors.append(
                            f"{path}: application.role_frame roles must follow canonical "
                            "thematic order"
                        )
                    if (
                        valid_arguments
                        and isinstance(function, str)
                        and function
                        and len(role_types) == len(arguments)
                    ):
                        expected_role_types = application_argument_types(
                            function,
                            len(arguments),
                        )
                        if role_types != expected_role_types:
                            errors.append(
                                f"{path}: application.role_frame role types do not "
                                "match function argument types"
                            )
            if not isinstance(adverb_count, int) or adverb_count < 0:
                errors.append(f"{path}: application.adverb_count must be a natural number")
            elif adverb_count != len(modifiers):
                errors.append(
                    f"{path}: application.adverb_count={adverb_count} "
                    f"does not match {len(modifiers)} modifier(s)"
                )
            elif vector_length is not None and adverb_count != vector_length:
                errors.append(
                    f"{path}: application.adverb_count={adverb_count} "
                    f"does not match modifier_vector.length={vector_length}"
                )
            return PROP

        if kind == "sigma":
            if not isinstance(current.get("witness"), str) or not current["witness"]:
                errors.append(f"{path}: sigma.witness must be a non-empty string")
            if not isinstance(current.get("type"), str) or not current["type"]:
                errors.append(f"{path}: sigma.type must be a non-empty string")
            body = current.get("body")
            if not isinstance(body, dict):
                errors.append(f"{path}: sigma.body must be a term")
                return PROP
            body_type = check(body, f"{path}.body")
            if body_type != PROP:
                errors.append(f"{path}: sigma.body must have type {PROP}, got {body_type}")
            return PROP

        if kind == "repeat":
            count = current.get("count")
            if not isinstance(count, str) or not count.isdigit() or int(count) < 1:
                errors.append(f"{path}: repeat.count must be a positive natural number")
            body = current.get("body")
            if not isinstance(body, dict):
                errors.append(f"{path}: repeat.body must be a term")
                return PROP
            body_type = check(body, f"{path}.body")
            if body_type != PROP:
                errors.append(f"{path}: repeat.body must have type {PROP}, got {body_type}")
            return PROP

        if kind == "time":
            operator = current.get("operator")
            arguments = current.get("arguments")
            if operator not in TIME_PREDS:
                errors.append(f"{path}: time.operator must be one of {sorted(TIME_PREDS)}")
            if not isinstance(arguments, list) or not arguments:
                errors.append(f"{path}: time.arguments must be a non-empty list")
            elif not all(isinstance(x, str) and x for x in arguments):
                errors.append(f"{path}: time.arguments must contain non-empty strings")
            body = current.get("body")
            if not isinstance(body, dict):
                errors.append(f"{path}: time.body must be a term")
                return PROP
            body_type = check(body, f"{path}.body")
            if body_type != PROP:
                errors.append(f"{path}: time.body must have type {PROP}, got {body_type}")
            return PROP

        if kind == "not":
            body = current.get("body")
            if not isinstance(body, dict):
                errors.append(f"{path}: not.body must be a term")
                return PROP
            body_type = check(body, f"{path}.body")
            if body_type != PROP:
                errors.append(f"{path}: not.body must have type {PROP}, got {body_type}")
            return PROP

        if kind == "transition":
            for field in ("theme", "source_state", "target_state"):
                if not isinstance(current.get(field), str) or not current[field]:
                    errors.append(f"{path}: transition.{field} must be a non-empty string")
            state_scale = current.get("state_scale")
            if not isinstance(state_scale, str) or not state_scale:
                errors.append(f"{path}: transition.state_scale must be a non-empty string")
            source_state = current.get("source_state")
            target_state = current.get("target_state")
            if target_state == "_":
                errors.append(f"{path}: transition.target_state must be known")
            if isinstance(target_state, str) and target_state != "_":
                expected_scale = infer_state_scale(target_state)
                if state_scale != expected_scale:
                    errors.append(
                        f"{path}: transition.state_scale={state_scale!r} does not "
                        f"match target state scale {expected_scale!r}"
                    )
            if isinstance(source_state, str) and source_state in STATE_SCALE_BY_STATE:
                source_scale = infer_state_scale(source_state)
                if isinstance(state_scale, str) and state_scale != source_scale:
                    errors.append(
                        f"{path}: transition.source_state scale {source_scale!r} "
                        f"does not match transition.state_scale {state_scale!r}"
                    )
            if (
                isinstance(source_state, str)
                and isinstance(target_state, str)
                and source_state != "_"
                and target_state != "_"
                and source_state == target_state
            ):
                errors.append(
                    f"{path}: transition.source_state and target_state must differ "
                    "when both are known"
                )
            return "TransitionT"

        if kind == "cause":
            if not isinstance(current.get("causer"), str) or not current["causer"]:
                errors.append(f"{path}: cause.causer must be a non-empty string")
            effect = current.get("effect")
            if not isinstance(effect, dict):
                errors.append(f"{path}: cause.effect must be a term")
            else:
                effect_type = check(effect, f"{path}.effect")
                if effect_type != "TransitionT":
                    errors.append(
                        f"{path}: cause.effect must have type TransitionT, got {effect_type}"
                    )
            activity = current.get("activity")
            if activity is not None:
                if not isinstance(activity, dict):
                    errors.append(f"{path}: cause.activity must be a term when present")
                else:
                    activity_type = check(activity, f"{path}.activity")
                    if activity_type != PROP:
                        errors.append(
                            f"{path}: cause.activity must have type {PROP}, got {activity_type}"
                        )
            return PROP

        errors.append(f"{path}: unknown term kind {kind!r}")
        return "Unknown"

    inferred_type = check(term, "ast")
    return {
        "ok": not errors,
        "type": inferred_type if not errors else "Invalid",
        "errors": errors,
    }


def export_atom(name: str, target: str) -> str:
    if target not in EXPORT_TARGETS:
        raise ValueError(f"Unsupported export target: {target!r}")
    if name == "_":
        return "unknown_state"
    sanitized = re.sub(r"[^0-9A-Za-z_]+", "_", name).strip("_")
    if not sanitized:
        raise ValueError(f"Cannot export empty atom from {name!r}")
    if sanitized[0].isdigit():
        sanitized = "x_" + sanitized
    return sanitized


def export_type_name(name: str, target: str) -> str:
    return export_atom(name, target)


def export_modifier_sequence(vector: Term, target: str) -> str:
    sequence = "mods_nil"
    for item in reversed(vector["items"]):
        sequence = (
            f"(mods_cons {item['tail_length']} "
            f"{export_atom(item['modifier'], target)} {sequence})"
        )
    return sequence


def export_term(term: Term, target: str) -> str:
    type_check = check_term(term)
    if not type_check["ok"]:
        errors = "; ".join(type_check["errors"])
        raise ValueError(f"Cannot export ill-typed AST: {errors}")
    if target not in EXPORT_TARGETS:
        raise ValueError(f"Unsupported export target: {target!r}")

    def emit(current: Term) -> str:
        kind = current["kind"]
        if kind == "application":
            parts = [
                export_atom(current["function"], target),
                str(current["adverb_count"]),
                export_modifier_sequence(current["modifier_vector"], target),
            ]
            parts.extend(export_atom(x, target) for x in current["arguments"])
            return "(" + " ".join(parts) + ")"
        if kind == "sigma":
            witness = export_atom(current["witness"], target)
            witness_type = export_type_name(current["type"], target)
            body = emit(current["body"])
            if target == "lean":
                return f"(Exists fun {witness} : {witness_type} => {body})"
            return f"(exists {witness} : {witness_type}, {body})"
        if kind == "repeat":
            return f"(repeat {current['count']} {emit(current['body'])})"
        if kind == "time":
            op = export_atom(current["operator"] + "_T", target)
            args = [export_atom(x, target) for x in current["arguments"]]
            args.append(emit(current["body"]))
            return "(" + " ".join([op] + args) + ")"
        if kind == "not":
            return f"(not_T {emit(current['body'])})"
        if kind == "transition":
            return (
                "(Transition "
                + " ".join(
                    export_atom(current[field], target)
                    for field in ("theme", "state_scale", "source_state", "target_state")
                )
                + ")"
            )
        if kind == "cause":
            return (
                "(Cause "
                + export_atom(current["causer"], target)
                + " "
                + emit(current["effect"])
                + ")"
            )
        raise ValueError(f"Unknown term kind: {kind!r}")

    return emit(term)


def export_result_type(term: Term) -> str:
    kind = term["kind"]
    if kind == "application":
        return application_result_type(term["function"])
    if kind == "sigma":
        return "Prop"
    if kind in {"repeat", "time", "not", "cause"}:
        return "PropT"
    if kind == "transition":
        return "TransitionT"
    raise ValueError(f"Unknown term kind: {kind!r}")


def application_result_type(function: str) -> str:
    return "Prop" if function in OMITTED_THEME_TYPES else "PropT"


def application_argument_types(function: str, argument_count: int) -> list[str]:
    if function in OMITTED_THEME_TYPES and argument_count >= 2:
        return ["Entity"] * (argument_count - 1) + [OMITTED_THEME_TYPES[function]]
    return ["Entity"] * argument_count


def preservation_application_constructor(function: str) -> str:
    return f"preserve_{function}_application"


def preservation_sigma_constructor(type_name: str) -> str:
    return f"preserve_sigma_{type_name}"


def model_application_constructor(function: str) -> str:
    return f"model_{function}_application"


def model_sigma_constructor(type_name: str) -> str:
    return f"model_sigma_{type_name}"


def syntax_truth_application_constructor(function: str) -> str:
    return f"syntax_truth_{function}_application"


def syntax_truth_sigma_constructor(type_name: str) -> str:
    return f"syntax_truth_sigma_{type_name}"


def denotation_application_field(function: str) -> str:
    return f"denote_{function}_application"


def denotation_sigma_field(type_name: str) -> str:
    return f"denote_sigma_{type_name}"


def truth_application_field(function: str) -> str:
    return f"truth_{function}_application"


def truth_sigma_field(type_name: str) -> str:
    return f"truth_sigma_{type_name}"


def concrete_kernel_application_field(function: str) -> str:
    return f"lexical_truth_{function}_application"


def concrete_kernel_sigma_field(type_name: str) -> str:
    return f"quantifier_truth_sigma_{type_name}"


def independent_obligation_application_field(function: str) -> str:
    return f"ledger_lexical_truth_{function}_obligation"


def independent_obligation_sigma_field(type_name: str) -> str:
    return f"ledger_quantifier_truth_sigma_{type_name}_obligation"


def evidence_source_application_field(function: str) -> str:
    return f"evidence_lexical_truth_{function}_application"


def evidence_source_sigma_field(type_name: str) -> str:
    return f"evidence_quantifier_truth_sigma_{type_name}"


def primitive_truth_application_field(function: str) -> str:
    return f"primitive_lexical_truth_{function}_application"


def primitive_truth_sigma_field(type_name: str) -> str:
    return f"primitive_quantifier_truth_sigma_{type_name}"


def atomic_truth_application_field(function: str) -> str:
    return f"atomic_lexical_truth_{function}_application"


def atomic_valuation_application_field(function: str) -> str:
    return f"valuation_lexical_truth_{function}_application"


def lexical_atom_truth_application_field(function: str) -> str:
    return f"lexical_atom_truth_{function}_application"


def lexical_transition_model_application_field(function: str) -> str:
    return f"model_lexical_truth_{function}_application"


def atomic_base_truth_application_constructor(function: str) -> str:
    return f"atomic_base_truth_{function}_application"


def atomic_closure_application_constructor(function: str) -> str:
    return f"atomic_closure_truth_{function}_application"


def atomic_closure_sigma_constructor(type_name: str) -> str:
    return f"atomic_closure_truth_sigma_{type_name}"


def registered_state_transition_constructor(
    theme: str,
    scale: str,
    source: str,
    target: str,
) -> str:
    return f"registered_transition_{theme}_{scale}_{source}_to_{target}"


def transition_refined_application_constructor(function: str) -> str:
    return f"transition_refined_truth_{function}_application"


def transition_refined_sigma_constructor(type_name: str) -> str:
    return f"transition_refined_truth_sigma_{type_name}"


def registered_truth_application_field(function: str) -> str:
    return f"registered_truth_{function}_application"


def registered_truth_sigma_field(type_name: str) -> str:
    return f"registered_truth_sigma_{type_name}"


def _coq_function_preservation_constructor(
    name: str,
    arg_types: list[str],
    result_type: str,
) -> list[str]:
    binders = ["forall n : nat", "forall mods : ModifierSeq n"]
    application_args = ["n", "mods"]
    remaining_arg_types = arg_types[1:] if arg_types else []
    for index, arg_type in enumerate(remaining_arg_types, 1):
        arg_name = f"arg{index}"
        binders.append(f"forall {arg_name} : {arg_type}")
        application_args.append(arg_name)
    return [
        f"  | {preservation_application_constructor(name)} : "
        + ", ".join(binders)
        + ",",
        "      "
        + f"SemanticPreservation {result_type} "
        + f"({name} {' '.join(application_args)})",
    ]


def _lean_function_preservation_constructor(
    name: str,
    arg_types: list[str],
    result_type: str,
) -> str:
    binders = ["(n : Nat)", "(mods : ModifierSeq n)"]
    application_args = ["n", "mods"]
    remaining_arg_types = arg_types[2:] if arg_types[:2] == ["(n : Nat)", "ModifierSeq n"] else arg_types
    for index, arg_type in enumerate(remaining_arg_types, 1):
        arg_name = f"arg{index}"
        binders.append(f"({arg_name} : {arg_type})")
        application_args.append(arg_name)
    return (
        f"  | {preservation_application_constructor(name)} : "
        + " -> ".join(binders + [
            f"SemanticPreservation {result_type} ({name} {' '.join(application_args)})"
        ])
    )


def _coq_function_model_constructor(
    name: str,
    arg_types: list[str],
    result_type: str,
) -> list[str]:
    binders = ["forall n : nat", "forall mods : ModifierSeq n"]
    application_args = ["n", "mods"]
    remaining_arg_types = arg_types[1:] if arg_types else []
    for index, arg_type in enumerate(remaining_arg_types, 1):
        arg_name = f"arg{index}"
        binders.append(f"forall {arg_name} : {arg_type}")
        application_args.append(arg_name)
    return [
        f"  | {model_application_constructor(name)} : "
        + ", ".join(binders)
        + ",",
        "      "
        + f"ModelInterpretable {result_type} "
        + f"({name} {' '.join(application_args)})",
    ]


def _lean_function_model_constructor(
    name: str,
    arg_types: list[str],
    result_type: str,
) -> str:
    binders = ["(n : Nat)", "(mods : ModifierSeq n)"]
    application_args = ["n", "mods"]
    remaining_arg_types = arg_types[2:] if arg_types[:2] == ["(n : Nat)", "ModifierSeq n"] else arg_types
    for index, arg_type in enumerate(remaining_arg_types, 1):
        arg_name = f"arg{index}"
        binders.append(f"({arg_name} : {arg_type})")
        application_args.append(arg_name)
    return (
        f"  | {model_application_constructor(name)} : "
        + " -> ".join(binders + [
            f"ModelInterpretable {result_type} ({name} {' '.join(application_args)})"
        ])
    )


def _coq_function_syntax_truth_constructor(
    name: str,
    arg_types: list[str],
    result_type: str,
) -> list[str]:
    binders = ["forall n : nat", "forall mods : ModifierSeq n"]
    application_args = ["n", "mods"]
    remaining_arg_types = arg_types[1:] if arg_types else []
    for index, arg_type in enumerate(remaining_arg_types, 1):
        arg_name = f"arg{index}"
        binders.append(f"forall {arg_name} : {arg_type}")
        application_args.append(arg_name)
    return [
        f"  | {syntax_truth_application_constructor(name)} : "
        + ", ".join(binders)
        + ",",
        "      "
        + f"SyntaxDirectedTruth {result_type} "
        + f"({name} {' '.join(application_args)})",
    ]


def _lean_function_syntax_truth_constructor(
    name: str,
    arg_types: list[str],
    result_type: str,
) -> str:
    binders = ["(n : Nat)", "(mods : ModifierSeq n)"]
    application_args = ["n", "mods"]
    remaining_arg_types = arg_types[2:] if arg_types[:2] == ["(n : Nat)", "ModifierSeq n"] else arg_types
    for index, arg_type in enumerate(remaining_arg_types, 1):
        arg_name = f"arg{index}"
        binders.append(f"({arg_name} : {arg_type})")
        application_args.append(arg_name)
    return (
        f"  | {syntax_truth_application_constructor(name)} : "
        + " -> ".join(binders + [
            f"SyntaxDirectedTruth {result_type} ({name} {' '.join(application_args)})"
        ])
    )


def _coq_function_denotation_field(
    name: str,
    arg_types: list[str],
    result_type: str,
) -> list[str]:
    binders = ["forall n : nat", "forall mods : ModifierSeq n"]
    application_args = ["n", "mods"]
    remaining_arg_types = arg_types[1:] if arg_types else []
    for index, arg_type in enumerate(remaining_arg_types, 1):
        arg_name = f"arg{index}"
        binders.append(f"forall {arg_name} : {arg_type}")
        application_args.append(arg_name)
    return [
        f"  {denotation_application_field(name)} : "
        + ", ".join(binders)
        + ",",
        "      "
        + f"model_denotes {result_type} "
        + f"({name} {' '.join(application_args)});",
    ]


def _lean_function_denotation_field(
    name: str,
    arg_types: list[str],
    result_type: str,
) -> str:
    binders = ["(n : Nat)", "(mods : ModifierSeq n)"]
    application_args = ["n", "mods"]
    remaining_arg_types = arg_types[2:] if arg_types[:2] == ["(n : Nat)", "ModifierSeq n"] else arg_types
    for index, arg_type in enumerate(remaining_arg_types, 1):
        arg_name = f"arg{index}"
        binders.append(f"({arg_name} : {arg_type})")
        application_args.append(arg_name)
    return (
        f"  {denotation_application_field(name)} : "
        + " -> ".join(
            binders
            + [f"model_denotes {result_type} ({name} {' '.join(application_args)})"]
        )
    )


def _coq_function_truth_field(
    name: str,
    arg_types: list[str],
    result_type: str,
) -> list[str]:
    binders = ["forall n : nat", "forall mods : ModifierSeq n"]
    application_args = ["n", "mods"]
    remaining_arg_types = arg_types[1:] if arg_types else []
    for index, arg_type in enumerate(remaining_arg_types, 1):
        arg_name = f"arg{index}"
        binders.append(f"forall {arg_name} : {arg_type}")
        application_args.append(arg_name)
    return [
        f"  {truth_application_field(name)} : "
        + ", ".join(binders)
        + ",",
        "      "
        + f"truth_denotes {result_type} "
        + f"({name} {' '.join(application_args)});",
    ]


def _lean_function_truth_field(
    name: str,
    arg_types: list[str],
    result_type: str,
) -> str:
    binders = ["(n : Nat)", "(mods : ModifierSeq n)"]
    application_args = ["n", "mods"]
    remaining_arg_types = arg_types[2:] if arg_types[:2] == ["(n : Nat)", "ModifierSeq n"] else arg_types
    for index, arg_type in enumerate(remaining_arg_types, 1):
        arg_name = f"arg{index}"
        binders.append(f"({arg_name} : {arg_type})")
        application_args.append(arg_name)
    return (
        f"  {truth_application_field(name)} : "
        + " -> ".join(
            binders
            + [f"truth_denotes {result_type} ({name} {' '.join(application_args)})"]
        )
    )


def _coq_function_concrete_kernel_field(
    name: str,
    arg_types: list[str],
    result_type: str,
) -> list[str]:
    binders = ["forall n : nat", "forall mods : ModifierSeq n"]
    application_args = ["n", "mods"]
    remaining_arg_types = arg_types[1:] if arg_types else []
    for index, arg_type in enumerate(remaining_arg_types, 1):
        arg_name = f"arg{index}"
        binders.append(f"forall {arg_name} : {arg_type}")
        application_args.append(arg_name)
    return [
        f"  {concrete_kernel_application_field(name)} : "
        + ", ".join(binders)
        + ",",
        "      "
        + f"kernel_denotes {result_type} "
        + f"({name} {' '.join(application_args)});",
    ]


def _lean_function_concrete_kernel_field(
    name: str,
    arg_types: list[str],
    result_type: str,
) -> str:
    binders = ["(n : Nat)", "(mods : ModifierSeq n)"]
    application_args = ["n", "mods"]
    remaining_arg_types = arg_types[2:] if arg_types[:2] == ["(n : Nat)", "ModifierSeq n"] else arg_types
    for index, arg_type in enumerate(remaining_arg_types, 1):
        arg_name = f"arg{index}"
        binders.append(f"({arg_name} : {arg_type})")
        application_args.append(arg_name)
    return (
        f"  {concrete_kernel_application_field(name)} : "
        + " -> ".join(
            binders
            + [f"kernel_denotes {result_type} ({name} {' '.join(application_args)})"]
        )
    )


def _coq_function_independent_obligation_field(
    name: str,
    arg_types: list[str],
    result_type: str,
) -> list[str]:
    binders = ["forall n : nat", "forall mods : ModifierSeq n"]
    application_args = ["n", "mods"]
    remaining_arg_types = arg_types[1:] if arg_types else []
    for index, arg_type in enumerate(remaining_arg_types, 1):
        arg_name = f"arg{index}"
        binders.append(f"forall {arg_name} : {arg_type}")
        application_args.append(arg_name)
    return [
        f"  {independent_obligation_application_field(name)} : "
        + ", ".join(binders)
        + ",",
        "      "
        + f"ledger_denotes {result_type} "
        + f"({name} {' '.join(application_args)});",
    ]


def _lean_function_independent_obligation_field(
    name: str,
    arg_types: list[str],
    result_type: str,
) -> str:
    binders = ["(n : Nat)", "(mods : ModifierSeq n)"]
    application_args = ["n", "mods"]
    remaining_arg_types = arg_types[2:] if arg_types[:2] == ["(n : Nat)", "ModifierSeq n"] else arg_types
    for index, arg_type in enumerate(remaining_arg_types, 1):
        arg_name = f"arg{index}"
        binders.append(f"({arg_name} : {arg_type})")
        application_args.append(arg_name)
    return (
        f"  {independent_obligation_application_field(name)} : "
        + " -> ".join(
            binders
            + [f"ledger_denotes {result_type} ({name} {' '.join(application_args)})"]
        )
    )


def _coq_function_evidence_source_field(
    name: str,
    arg_types: list[str],
    result_type: str,
) -> list[str]:
    binders = ["forall n : nat", "forall mods : ModifierSeq n"]
    application_args = ["n", "mods"]
    remaining_arg_types = arg_types[1:] if arg_types else []
    for index, arg_type in enumerate(remaining_arg_types, 1):
        arg_name = f"arg{index}"
        binders.append(f"forall {arg_name} : {arg_type}")
        application_args.append(arg_name)
    return [
        f"  {evidence_source_application_field(name)} : "
        + ", ".join(binders)
        + ",",
        "      TruthEvidence (evidence_denotes "
        + f"{result_type} ({name} {' '.join(application_args)}));",
    ]


def _lean_function_evidence_source_field(
    name: str,
    arg_types: list[str],
    result_type: str,
) -> str:
    binders = ["(n : Nat)", "(mods : ModifierSeq n)"]
    application_args = ["n", "mods"]
    remaining_arg_types = (
        arg_types[2:]
        if arg_types[:2] == ["(n : Nat)", "ModifierSeq n"]
        else arg_types
    )
    for index, arg_type in enumerate(remaining_arg_types, 1):
        arg_name = f"arg{index}"
        binders.append(f"({arg_name} : {arg_type})")
        application_args.append(arg_name)
    return (
        f"  {evidence_source_application_field(name)} : "
        + " -> ".join(
            binders
            + [
                "TruthEvidence "
                f"(evidence_denotes {result_type} "
                f"({name} {' '.join(application_args)}))"
            ]
        )
    )


def _coq_function_evidence_kernel_assignment(
    name: str,
    arg_types: list[str],
    result_type: str,
) -> tuple[str, list[str]]:
    ordinary_arg_types = arg_types[1:] if arg_types else []
    lambda_args = ["n", "mods"] + [
        f"arg{index}" for index, _arg_type in enumerate(ordinary_arg_types, 1)
    ]
    term = f"{name} {' '.join(lambda_args)}"
    lines = [
        f"  {concrete_kernel_application_field(name)} := "
        f"fun {' '.join(lambda_args)} =>",
        "      truth_evidence_sound",
        f"        (evidence_denotes S {result_type} ({term}))",
        f"        ({evidence_source_application_field(name)} "
        f"S {' '.join(lambda_args)})",
    ]
    return concrete_kernel_application_field(name), lines


def _lean_function_evidence_kernel_assignment(
    name: str,
    arg_types: list[str],
    result_type: str,
) -> tuple[str, list[str]]:
    ordinary_arg_types = (
        arg_types[2:]
        if arg_types[:2] == ["(n : Nat)", "ModifierSeq n"]
        else arg_types
    )
    lambda_args = ["n", "mods"] + [
        f"arg{index}" for index, _arg_type in enumerate(ordinary_arg_types, 1)
    ]
    term = f"{name} {' '.join(lambda_args)}"
    lines = [
        f"  {concrete_kernel_application_field(name)} := "
        f"fun {' '.join(lambda_args)} =>",
        "      truth_evidence_sound",
        f"        (S.evidence_denotes {result_type} ({term}))",
        f"        (S.{evidence_source_application_field(name)} "
        f"{' '.join(lambda_args)})",
    ]
    return concrete_kernel_application_field(name), lines


def _coq_function_primitive_truth_field(
    name: str,
    arg_types: list[str],
    result_type: str,
) -> list[str]:
    binders = ["forall n : nat", "forall mods : ModifierSeq n"]
    application_args = ["n", "mods"]
    remaining_arg_types = arg_types[1:] if arg_types else []
    for index, arg_type in enumerate(remaining_arg_types, 1):
        arg_name = f"arg{index}"
        binders.append(f"forall {arg_name} : {arg_type}")
        application_args.append(arg_name)
    return [
        f"  {primitive_truth_application_field(name)} : "
        + ", ".join(binders)
        + ",",
        "      "
        + f"primitive_denotes {result_type} "
        + f"({name} {' '.join(application_args)});",
    ]


def _lean_function_primitive_truth_field(
    name: str,
    arg_types: list[str],
    result_type: str,
) -> str:
    binders = ["(n : Nat)", "(mods : ModifierSeq n)"]
    application_args = ["n", "mods"]
    remaining_arg_types = arg_types[2:] if arg_types[:2] == ["(n : Nat)", "ModifierSeq n"] else arg_types
    for index, arg_type in enumerate(remaining_arg_types, 1):
        arg_name = f"arg{index}"
        binders.append(f"({arg_name} : {arg_type})")
        application_args.append(arg_name)
    return (
        f"  {primitive_truth_application_field(name)} : "
        + " -> ".join(
            binders
            + [f"primitive_denotes {result_type} ({name} {' '.join(application_args)})"]
        )
    )


def _coq_function_atomic_truth_field(
    name: str,
    arg_types: list[str],
    result_type: str,
) -> list[str]:
    binders = ["forall n : nat", "forall mods : ModifierSeq n"]
    application_args = ["n", "mods"]
    remaining_arg_types = arg_types[1:] if arg_types else []
    for index, arg_type in enumerate(remaining_arg_types, 1):
        arg_name = f"arg{index}"
        binders.append(f"forall {arg_name} : {arg_type}")
        application_args.append(arg_name)
    return [
        f"  {atomic_truth_application_field(name)} : "
        + ", ".join(binders)
        + ",",
        "      "
        + f"AtomicBaseTruth {result_type} "
        + f"({name} {' '.join(application_args)});",
    ]


def _lean_function_atomic_truth_field(
    name: str,
    arg_types: list[str],
    result_type: str,
) -> str:
    binders = ["(n : Nat)", "(mods : ModifierSeq n)"]
    application_args = ["n", "mods"]
    remaining_arg_types = arg_types[2:] if arg_types[:2] == ["(n : Nat)", "ModifierSeq n"] else arg_types
    for index, arg_type in enumerate(remaining_arg_types, 1):
        arg_name = f"arg{index}"
        binders.append(f"({arg_name} : {arg_type})")
        application_args.append(arg_name)
    return (
        f"  {atomic_truth_application_field(name)} : "
        + " -> ".join(
            binders
            + [
                f"AtomicBaseTruth {result_type} "
                f"({name} {' '.join(application_args)})"
            ]
        )
    )


def _coq_function_atomic_valuation_field(
    name: str,
    arg_types: list[str],
    result_type: str,
) -> list[str]:
    binders = ["forall n : nat", "forall mods : ModifierSeq n"]
    application_args = ["n", "mods"]
    remaining_arg_types = arg_types[1:] if arg_types else []
    for index, arg_type in enumerate(remaining_arg_types, 1):
        arg_name = f"arg{index}"
        binders.append(f"forall {arg_name} : {arg_type}")
        application_args.append(arg_name)
    return [
        f"  {atomic_valuation_application_field(name)} : "
        + ", ".join(binders)
        + ",",
        "      "
        + f"atomic_valuation_denotes {result_type} "
        + f"({name} {' '.join(application_args)});",
    ]


def _lean_function_atomic_valuation_field(
    name: str,
    arg_types: list[str],
    result_type: str,
) -> str:
    binders = ["(n : Nat)", "(mods : ModifierSeq n)"]
    application_args = ["n", "mods"]
    remaining_arg_types = arg_types[2:] if arg_types[:2] == ["(n : Nat)", "ModifierSeq n"] else arg_types
    for index, arg_type in enumerate(remaining_arg_types, 1):
        arg_name = f"arg{index}"
        binders.append(f"({arg_name} : {arg_type})")
        application_args.append(arg_name)
    return (
        f"  {atomic_valuation_application_field(name)} : "
        + " -> ".join(
            binders
            + [
                f"atomic_valuation_denotes {result_type} "
                f"({name} {' '.join(application_args)})"
            ]
        )
    )


def _coq_function_lexical_atom_truth_assumption_field(
    name: str,
    arg_types: list[str],
    result_type: str,
) -> list[str]:
    binders = ["forall n : nat", "forall mods : ModifierSeq n"]
    application_args = ["n", "mods"]
    remaining_arg_types = arg_types[1:] if arg_types else []
    for index, arg_type in enumerate(remaining_arg_types, 1):
        arg_name = f"arg{index}"
        binders.append(f"forall {arg_name} : {arg_type}")
        application_args.append(arg_name)
    return [
        f"  {lexical_atom_truth_application_field(name)} : "
        + ", ".join(binders)
        + ",",
        "      "
        + f"D {result_type} "
        + f"({name} {' '.join(application_args)});",
    ]


def _lean_function_lexical_atom_truth_assumption_field(
    name: str,
    arg_types: list[str],
    result_type: str,
) -> str:
    binders = ["(n : Nat)", "(mods : ModifierSeq n)"]
    application_args = ["n", "mods"]
    remaining_arg_types = arg_types[2:] if arg_types[:2] == ["(n : Nat)", "ModifierSeq n"] else arg_types
    for index, arg_type in enumerate(remaining_arg_types, 1):
        arg_name = f"arg{index}"
        binders.append(f"({arg_name} : {arg_type})")
        application_args.append(arg_name)
    return (
        f"  {lexical_atom_truth_application_field(name)} : "
        + " -> ".join(
            binders
            + [
                f"D {result_type} "
                f"({name} {' '.join(application_args)})"
            ]
        )
    )


def _coq_function_lexical_transition_model_field(
    name: str,
    arg_types: list[str],
    result_type: str,
) -> list[str]:
    binders = ["forall n : nat", "forall mods : ModifierSeq n"]
    application_args = ["n", "mods"]
    remaining_arg_types = arg_types[1:] if arg_types else []
    for index, arg_type in enumerate(remaining_arg_types, 1):
        arg_name = f"arg{index}"
        binders.append(f"forall {arg_name} : {arg_type}")
        application_args.append(arg_name)
    return [
        f"  {lexical_transition_model_application_field(name)} : "
        + ", ".join(binders)
        + ",",
        "      "
        + f"atom_model_denotes {result_type} "
        + f"({name} {' '.join(application_args)});",
    ]


def _lean_function_lexical_transition_model_field(
    name: str,
    arg_types: list[str],
    result_type: str,
) -> str:
    binders = ["(n : Nat)", "(mods : ModifierSeq n)"]
    application_args = ["n", "mods"]
    remaining_arg_types = arg_types[2:] if arg_types[:2] == ["(n : Nat)", "ModifierSeq n"] else arg_types
    for index, arg_type in enumerate(remaining_arg_types, 1):
        arg_name = f"arg{index}"
        binders.append(f"({arg_name} : {arg_type})")
        application_args.append(arg_name)
    return (
        f"  {lexical_transition_model_application_field(name)} : "
        + " -> ".join(
            binders
            + [
                f"atom_model_denotes {result_type} "
                f"({name} {' '.join(application_args)})"
            ]
        )
    )


def _coq_function_atomic_base_constructor(
    name: str,
    arg_types: list[str],
    result_type: str,
) -> list[str]:
    binders = ["forall n : nat", "forall mods : ModifierSeq n"]
    application_args = ["n", "mods"]
    remaining_arg_types = arg_types[1:] if arg_types else []
    for index, arg_type in enumerate(remaining_arg_types, 1):
        arg_name = f"arg{index}"
        binders.append(f"forall {arg_name} : {arg_type}")
        application_args.append(arg_name)
    return [
        f"  | {atomic_base_truth_application_constructor(name)} : "
        + ", ".join(binders)
        + ",",
        "      "
        + f"AtomicBaseTruth {result_type} "
        + f"({name} {' '.join(application_args)})",
    ]


def _lean_function_atomic_base_constructor(
    name: str,
    arg_types: list[str],
    result_type: str,
) -> str:
    binders = ["(n : Nat)", "(mods : ModifierSeq n)"]
    application_args = ["n", "mods"]
    remaining_arg_types = arg_types[2:] if arg_types[:2] == ["(n : Nat)", "ModifierSeq n"] else arg_types
    for index, arg_type in enumerate(remaining_arg_types, 1):
        arg_name = f"arg{index}"
        binders.append(f"({arg_name} : {arg_type})")
        application_args.append(arg_name)
    return (
        f"  | {atomic_base_truth_application_constructor(name)} : "
        + " -> ".join(
            binders
            + [
                f"AtomicBaseTruth {result_type} "
                f"({name} {' '.join(application_args)})"
            ]
        )
    )


def _coq_function_atomic_closure_constructor(
    name: str,
    arg_types: list[str],
    result_type: str,
) -> list[str]:
    binders = ["forall n : nat", "forall mods : ModifierSeq n"]
    application_args = ["n", "mods"]
    remaining_arg_types = arg_types[1:] if arg_types else []
    for index, arg_type in enumerate(remaining_arg_types, 1):
        arg_name = f"arg{index}"
        binders.append(f"forall {arg_name} : {arg_type}")
        application_args.append(arg_name)
    fact = f"AtomicBaseTruth {result_type} ({name} {' '.join(application_args)})"
    return [
        f"  | {atomic_closure_application_constructor(name)} : "
        + ", ".join(binders)
        + ",",
        f"      {fact} ->",
        "      "
        + f"AtomicClosureTruth {result_type} "
        + f"({name} {' '.join(application_args)})",
    ]


def _lean_function_atomic_closure_constructor(
    name: str,
    arg_types: list[str],
    result_type: str,
) -> str:
    binders = ["(n : Nat)", "(mods : ModifierSeq n)"]
    application_args = ["n", "mods"]
    remaining_arg_types = arg_types[2:] if arg_types[:2] == ["(n : Nat)", "ModifierSeq n"] else arg_types
    for index, arg_type in enumerate(remaining_arg_types, 1):
        arg_name = f"arg{index}"
        binders.append(f"({arg_name} : {arg_type})")
        application_args.append(arg_name)
    fact = f"AtomicBaseTruth {result_type} ({name} {' '.join(application_args)})"
    return (
        f"  | {atomic_closure_application_constructor(name)} : "
        + " -> ".join(
            binders
            + [
                fact,
                f"AtomicClosureTruth {result_type} ({name} {' '.join(application_args)})",
            ]
        )
    )


def _coq_function_transition_refined_constructor(
    name: str,
    arg_types: list[str],
    result_type: str,
) -> list[str]:
    binders = ["forall n : nat", "forall mods : ModifierSeq n"]
    application_args = ["n", "mods"]
    remaining_arg_types = arg_types[1:] if arg_types else []
    for index, arg_type in enumerate(remaining_arg_types, 1):
        arg_name = f"arg{index}"
        binders.append(f"forall {arg_name} : {arg_type}")
        application_args.append(arg_name)
    fact = f"AtomicBaseTruth {result_type} ({name} {' '.join(application_args)})"
    return [
        f"  | {transition_refined_application_constructor(name)} : "
        + ", ".join(binders)
        + ",",
        f"      {fact} ->",
        "      "
        + f"TransitionRefinedAtomicClosureTruth {result_type} "
        + f"({name} {' '.join(application_args)})",
    ]


def _lean_function_transition_refined_constructor(
    name: str,
    arg_types: list[str],
    result_type: str,
) -> str:
    binders = ["(n : Nat)", "(mods : ModifierSeq n)"]
    application_args = ["n", "mods"]
    remaining_arg_types = (
        arg_types[2:]
        if arg_types[:2] == ["(n : Nat)", "ModifierSeq n"]
        else arg_types
    )
    for index, arg_type in enumerate(remaining_arg_types, 1):
        arg_name = f"arg{index}"
        binders.append(f"({arg_name} : {arg_type})")
        application_args.append(arg_name)
    fact = f"AtomicBaseTruth {result_type} ({name} {' '.join(application_args)})"
    return (
        f"  | {transition_refined_application_constructor(name)} : "
        + " -> ".join(
            binders
            + [
                fact,
                "TransitionRefinedAtomicClosureTruth "
                f"{result_type} ({name} {' '.join(application_args)})",
            ]
        )
    )


def _coq_function_registered_truth_field(
    name: str,
    arg_types: list[str],
    result_type: str,
) -> list[str]:
    binders = ["forall n : nat", "forall mods : ModifierSeq n"]
    application_args = ["n", "mods"]
    remaining_arg_types = arg_types[1:] if arg_types else []
    for index, arg_type in enumerate(remaining_arg_types, 1):
        arg_name = f"arg{index}"
        binders.append(f"forall {arg_name} : {arg_type}")
        application_args.append(arg_name)
    return [
        f"  {registered_truth_application_field(name)} : "
        + ", ".join(binders)
        + ",",
        "      "
        + f"registered_truth_denotes {result_type} "
        + f"({name} {' '.join(application_args)});",
    ]


def _lean_function_registered_truth_field(
    name: str,
    arg_types: list[str],
    result_type: str,
) -> str:
    binders = ["(n : Nat)", "(mods : ModifierSeq n)"]
    application_args = ["n", "mods"]
    remaining_arg_types = (
        arg_types[2:]
        if arg_types[:2] == ["(n : Nat)", "ModifierSeq n"]
        else arg_types
    )
    for index, arg_type in enumerate(remaining_arg_types, 1):
        arg_name = f"arg{index}"
        binders.append(f"({arg_name} : {arg_type})")
        application_args.append(arg_name)
    return (
        f"  {registered_truth_application_field(name)} : "
        + " -> ".join(
            binders
            + [
                "registered_truth_denotes "
                f"{result_type} ({name} {' '.join(application_args)})"
            ]
        )
    )


def semantic_preservation_relation_lines(
    declarations: dict[str, Any],
    target: str,
) -> list[str]:
    if target == "lean":
        lines = ["inductive SemanticPreservation : (A : Type) -> A -> Prop where"]
        for name, (arg_types, result_type) in sorted(declarations["functions"].items()):
            lines.append(
                _lean_function_preservation_constructor(name, arg_types, result_type)
            )
        for type_name in declarations["types"]:
            lines.append(
                f"  | {preservation_sigma_constructor(type_name)} : "
                f"(P : {type_name} -> Prop) -> "
                f"((x : {type_name}) -> SemanticPreservation Prop (P x)) -> "
                f"SemanticPreservation Prop (Exists fun x : {type_name} => P x)"
            )
        lines.extend(
            [
                "  | preserve_repeat : (n : Nat) -> (body : PropT) -> "
                "SemanticPreservation PropT body -> "
                "SemanticPreservation PropT (repeat n body)",
                "  | preserve_at_T : (marker : Entity) -> (body : PropT) -> "
                "SemanticPreservation PropT body -> "
                "SemanticPreservation PropT (at_T marker body)",
                "  | preserve_during_T : (marker : Entity) -> (body : PropT) -> "
                "SemanticPreservation PropT body -> "
                "SemanticPreservation PropT (during_T marker body)",
                "  | preserve_before_T : (marker : Entity) -> (body : PropT) -> "
                "SemanticPreservation PropT body -> "
                "SemanticPreservation PropT (before_T marker body)",
                "  | preserve_after_T : (marker : Entity) -> (body : PropT) -> "
                "SemanticPreservation PropT body -> "
                "SemanticPreservation PropT (after_T marker body)",
                "  | preserve_until_T : (marker : Entity) -> (body : PropT) -> "
                "SemanticPreservation PropT body -> "
                "SemanticPreservation PropT (until_T marker body)",
                "  | preserve_since_T : (marker : Entity) -> (body : PropT) -> "
                "SemanticPreservation PropT body -> "
                "SemanticPreservation PropT (since_T marker body)",
                "  | preserve_not_T : (body : PropT) -> "
                "SemanticPreservation PropT body -> "
                "SemanticPreservation PropT (not_T body)",
                "  | preserve_transition : (theme : Entity) -> "
                "(scale : StateScale) -> (source : State) -> (target : State) -> "
                "SemanticPreservation TransitionT "
                "(Transition theme scale source target)",
                "  | preserve_cause : (causer : Entity) -> (effect : TransitionT) -> "
                "SemanticPreservation TransitionT effect -> "
                "SemanticPreservation PropT (Cause causer effect)",
            ]
        )
        return lines

    lines = ["Inductive SemanticPreservation : forall A : Type, A -> Prop :="]
    constructors: list[str] = []
    for name, (arg_types, result_type) in sorted(declarations["functions"].items()):
        constructors.extend(
            _coq_function_preservation_constructor(name, arg_types, result_type)
        )
    for type_name in declarations["types"]:
        constructors.extend(
            [
                f"  | {preservation_sigma_constructor(type_name)} : "
                f"forall P : {type_name} -> Prop,",
                f"      (forall x : {type_name}, SemanticPreservation Prop (P x)) ->",
                f"      SemanticPreservation Prop (exists x : {type_name}, P x)",
            ]
        )
    constructors.extend(
        [
            "  | preserve_repeat : forall n : nat, forall body : PropT,",
            "      SemanticPreservation PropT body ->",
            "      SemanticPreservation PropT (repeat n body)",
            "  | preserve_at_T : forall marker : Entity, forall body : PropT,",
            "      SemanticPreservation PropT body ->",
            "      SemanticPreservation PropT (at_T marker body)",
            "  | preserve_during_T : forall marker : Entity, forall body : PropT,",
            "      SemanticPreservation PropT body ->",
            "      SemanticPreservation PropT (during_T marker body)",
            "  | preserve_before_T : forall marker : Entity, forall body : PropT,",
            "      SemanticPreservation PropT body ->",
            "      SemanticPreservation PropT (before_T marker body)",
            "  | preserve_after_T : forall marker : Entity, forall body : PropT,",
            "      SemanticPreservation PropT body ->",
            "      SemanticPreservation PropT (after_T marker body)",
            "  | preserve_until_T : forall marker : Entity, forall body : PropT,",
            "      SemanticPreservation PropT body ->",
            "      SemanticPreservation PropT (until_T marker body)",
            "  | preserve_since_T : forall marker : Entity, forall body : PropT,",
            "      SemanticPreservation PropT body ->",
            "      SemanticPreservation PropT (since_T marker body)",
            "  | preserve_not_T : forall body : PropT,",
            "      SemanticPreservation PropT body ->",
            "      SemanticPreservation PropT (not_T body)",
            "  | preserve_transition : "
            "forall theme : Entity, forall scale : StateScale, "
            "forall source : State, forall target : State,",
            "      SemanticPreservation TransitionT "
            "(Transition theme scale source target)",
            "  | preserve_cause : "
            "forall causer : Entity, forall effect : TransitionT,",
            "      SemanticPreservation TransitionT effect ->",
            "      SemanticPreservation PropT (Cause causer effect)",
        ]
    )
    if not constructors:
        raise ValueError("Cannot emit an empty SemanticPreservation relation")
    constructors[-1] += "."
    return lines + constructors


def model_interpretability_relation_lines(
    declarations: dict[str, Any],
    target: str,
) -> list[str]:
    if target == "lean":
        lines = ["inductive ModelInterpretable : (A : Type) -> A -> Prop where"]
        for name, (arg_types, result_type) in sorted(declarations["functions"].items()):
            lines.append(_lean_function_model_constructor(name, arg_types, result_type))
        for type_name in declarations["types"]:
            lines.append(
                f"  | {model_sigma_constructor(type_name)} : "
                f"(P : {type_name} -> Prop) -> "
                f"((x : {type_name}) -> ModelInterpretable Prop (P x)) -> "
                f"ModelInterpretable Prop (Exists fun x : {type_name} => P x)"
            )
        lines.extend(
            [
                "  | model_repeat : (n : Nat) -> (body : PropT) -> "
                "ModelInterpretable PropT body -> "
                "ModelInterpretable PropT (repeat n body)",
                "  | model_at_T : (marker : Entity) -> (body : PropT) -> "
                "ModelInterpretable PropT body -> "
                "ModelInterpretable PropT (at_T marker body)",
                "  | model_during_T : (marker : Entity) -> (body : PropT) -> "
                "ModelInterpretable PropT body -> "
                "ModelInterpretable PropT (during_T marker body)",
                "  | model_before_T : (marker : Entity) -> (body : PropT) -> "
                "ModelInterpretable PropT body -> "
                "ModelInterpretable PropT (before_T marker body)",
                "  | model_after_T : (marker : Entity) -> (body : PropT) -> "
                "ModelInterpretable PropT body -> "
                "ModelInterpretable PropT (after_T marker body)",
                "  | model_until_T : (marker : Entity) -> (body : PropT) -> "
                "ModelInterpretable PropT body -> "
                "ModelInterpretable PropT (until_T marker body)",
                "  | model_since_T : (marker : Entity) -> (body : PropT) -> "
                "ModelInterpretable PropT body -> "
                "ModelInterpretable PropT (since_T marker body)",
                "  | model_not_T : (body : PropT) -> "
                "ModelInterpretable PropT body -> "
                "ModelInterpretable PropT (not_T body)",
                "  | model_transition : (theme : Entity) -> "
                "(scale : StateScale) -> (source : State) -> (target : State) -> "
                "ModelInterpretable TransitionT "
                "(Transition theme scale source target)",
                "  | model_cause : (causer : Entity) -> (effect : TransitionT) -> "
                "ModelInterpretable TransitionT effect -> "
                "ModelInterpretable PropT (Cause causer effect)",
            ]
        )
        return lines

    lines = ["Inductive ModelInterpretable : forall A : Type, A -> Prop :="]
    constructors: list[str] = []
    for name, (arg_types, result_type) in sorted(declarations["functions"].items()):
        constructors.extend(_coq_function_model_constructor(name, arg_types, result_type))
    for type_name in declarations["types"]:
        constructors.extend(
            [
                f"  | {model_sigma_constructor(type_name)} : "
                f"forall P : {type_name} -> Prop,",
                f"      (forall x : {type_name}, ModelInterpretable Prop (P x)) ->",
                f"      ModelInterpretable Prop (exists x : {type_name}, P x)",
            ]
        )
    constructors.extend(
        [
            "  | model_repeat : forall n : nat, forall body : PropT,",
            "      ModelInterpretable PropT body ->",
            "      ModelInterpretable PropT (repeat n body)",
            "  | model_at_T : forall marker : Entity, forall body : PropT,",
            "      ModelInterpretable PropT body ->",
            "      ModelInterpretable PropT (at_T marker body)",
            "  | model_during_T : forall marker : Entity, forall body : PropT,",
            "      ModelInterpretable PropT body ->",
            "      ModelInterpretable PropT (during_T marker body)",
            "  | model_before_T : forall marker : Entity, forall body : PropT,",
            "      ModelInterpretable PropT body ->",
            "      ModelInterpretable PropT (before_T marker body)",
            "  | model_after_T : forall marker : Entity, forall body : PropT,",
            "      ModelInterpretable PropT body ->",
            "      ModelInterpretable PropT (after_T marker body)",
            "  | model_until_T : forall marker : Entity, forall body : PropT,",
            "      ModelInterpretable PropT body ->",
            "      ModelInterpretable PropT (until_T marker body)",
            "  | model_since_T : forall marker : Entity, forall body : PropT,",
            "      ModelInterpretable PropT body ->",
            "      ModelInterpretable PropT (since_T marker body)",
            "  | model_not_T : forall body : PropT,",
            "      ModelInterpretable PropT body ->",
            "      ModelInterpretable PropT (not_T body)",
            "  | model_transition : "
            "forall theme : Entity, forall scale : StateScale, "
            "forall source : State, forall target : State,",
            "      ModelInterpretable TransitionT "
            "(Transition theme scale source target)",
            "  | model_cause : "
            "forall causer : Entity, forall effect : TransitionT,",
            "      ModelInterpretable TransitionT effect ->",
            "      ModelInterpretable PropT (Cause causer effect)",
        ]
    )
    if not constructors:
        raise ValueError("Cannot emit an empty ModelInterpretable relation")
    constructors[-1] += "."
    return lines + constructors


def syntax_directed_truth_relation_lines(
    declarations: dict[str, Any],
    target: str,
) -> list[str]:
    if target == "lean":
        lines = ["inductive SyntaxDirectedTruth : (A : Type) -> A -> Prop where"]
        for name, (arg_types, result_type) in sorted(declarations["functions"].items()):
            lines.append(
                _lean_function_syntax_truth_constructor(name, arg_types, result_type)
            )
        for type_name in declarations["types"]:
            lines.append(
                f"  | {syntax_truth_sigma_constructor(type_name)} : "
                f"(P : {type_name} -> Prop) -> "
                f"((x : {type_name}) -> SyntaxDirectedTruth Prop (P x)) -> "
                f"SyntaxDirectedTruth Prop (Exists fun x : {type_name} => P x)"
            )
        lines.extend(
            [
                "  | syntax_truth_repeat : (n : Nat) -> (body : PropT) -> "
                "SyntaxDirectedTruth PropT body -> "
                "SyntaxDirectedTruth PropT (repeat n body)",
                "  | syntax_truth_at_T : (marker : Entity) -> (body : PropT) -> "
                "SyntaxDirectedTruth PropT body -> "
                "SyntaxDirectedTruth PropT (at_T marker body)",
                "  | syntax_truth_during_T : (marker : Entity) -> (body : PropT) -> "
                "SyntaxDirectedTruth PropT body -> "
                "SyntaxDirectedTruth PropT (during_T marker body)",
                "  | syntax_truth_before_T : (marker : Entity) -> (body : PropT) -> "
                "SyntaxDirectedTruth PropT body -> "
                "SyntaxDirectedTruth PropT (before_T marker body)",
                "  | syntax_truth_after_T : (marker : Entity) -> (body : PropT) -> "
                "SyntaxDirectedTruth PropT body -> "
                "SyntaxDirectedTruth PropT (after_T marker body)",
                "  | syntax_truth_until_T : (marker : Entity) -> (body : PropT) -> "
                "SyntaxDirectedTruth PropT body -> "
                "SyntaxDirectedTruth PropT (until_T marker body)",
                "  | syntax_truth_since_T : (marker : Entity) -> (body : PropT) -> "
                "SyntaxDirectedTruth PropT body -> "
                "SyntaxDirectedTruth PropT (since_T marker body)",
                "  | syntax_truth_not_T : (body : PropT) -> "
                "SyntaxDirectedTruth PropT body -> "
                "SyntaxDirectedTruth PropT (not_T body)",
                "  | syntax_truth_transition : (theme : Entity) -> "
                "(scale : StateScale) -> (source : State) -> (target : State) -> "
                "SyntaxDirectedTruth TransitionT "
                "(Transition theme scale source target)",
                "  | syntax_truth_cause : (causer : Entity) -> (effect : TransitionT) -> "
                "SyntaxDirectedTruth TransitionT effect -> "
                "SyntaxDirectedTruth PropT (Cause causer effect)",
            ]
        )
        return lines

    lines = ["Inductive SyntaxDirectedTruth : forall A : Type, A -> Prop :="]
    constructors: list[str] = []
    for name, (arg_types, result_type) in sorted(declarations["functions"].items()):
        constructors.extend(
            _coq_function_syntax_truth_constructor(name, arg_types, result_type)
        )
    for type_name in declarations["types"]:
        constructors.extend(
            [
                f"  | {syntax_truth_sigma_constructor(type_name)} : "
                f"forall P : {type_name} -> Prop,",
                f"      (forall x : {type_name}, SyntaxDirectedTruth Prop (P x)) ->",
                f"      SyntaxDirectedTruth Prop (exists x : {type_name}, P x)",
            ]
        )
    constructors.extend(
        [
            "  | syntax_truth_repeat : forall n : nat, forall body : PropT,",
            "      SyntaxDirectedTruth PropT body ->",
            "      SyntaxDirectedTruth PropT (repeat n body)",
            "  | syntax_truth_at_T : forall marker : Entity, forall body : PropT,",
            "      SyntaxDirectedTruth PropT body ->",
            "      SyntaxDirectedTruth PropT (at_T marker body)",
            "  | syntax_truth_during_T : forall marker : Entity, forall body : PropT,",
            "      SyntaxDirectedTruth PropT body ->",
            "      SyntaxDirectedTruth PropT (during_T marker body)",
            "  | syntax_truth_before_T : forall marker : Entity, forall body : PropT,",
            "      SyntaxDirectedTruth PropT body ->",
            "      SyntaxDirectedTruth PropT (before_T marker body)",
            "  | syntax_truth_after_T : forall marker : Entity, forall body : PropT,",
            "      SyntaxDirectedTruth PropT body ->",
            "      SyntaxDirectedTruth PropT (after_T marker body)",
            "  | syntax_truth_until_T : forall marker : Entity, forall body : PropT,",
            "      SyntaxDirectedTruth PropT body ->",
            "      SyntaxDirectedTruth PropT (until_T marker body)",
            "  | syntax_truth_since_T : forall marker : Entity, forall body : PropT,",
            "      SyntaxDirectedTruth PropT body ->",
            "      SyntaxDirectedTruth PropT (since_T marker body)",
            "  | syntax_truth_not_T : forall body : PropT,",
            "      SyntaxDirectedTruth PropT body ->",
            "      SyntaxDirectedTruth PropT (not_T body)",
            "  | syntax_truth_transition : "
            "forall theme : Entity, forall scale : StateScale, "
            "forall source : State, forall target : State,",
            "      SyntaxDirectedTruth TransitionT "
            "(Transition theme scale source target)",
            "  | syntax_truth_cause : "
            "forall causer : Entity, forall effect : TransitionT,",
            "      SyntaxDirectedTruth TransitionT effect ->",
            "      SyntaxDirectedTruth PropT (Cause causer effect)",
        ]
    )
    if not constructors:
        raise ValueError("Cannot emit an empty SyntaxDirectedTruth relation")
    constructors[-1] += "."
    return lines + constructors


def semantic_model_record_lines(
    declarations: dict[str, Any],
    target: str,
) -> list[str]:
    if target == "lean":
        lines = [
            "structure SemanticModel : Type where",
            "  model_denotes : (A : Type) -> A -> Prop",
        ]
        for name, (arg_types, result_type) in sorted(declarations["functions"].items()):
            lines.append(_lean_function_denotation_field(name, arg_types, result_type))
        for type_name in declarations["types"]:
            lines.append(
                f"  {denotation_sigma_field(type_name)} : "
                f"(P : {type_name} -> Prop) -> "
                f"((x : {type_name}) -> model_denotes Prop (P x)) -> "
                f"model_denotes Prop (Exists fun x : {type_name} => P x)"
            )
        lines.extend(
            [
                "  denote_repeat : (n : Nat) -> (body : PropT) -> "
                "model_denotes PropT body -> model_denotes PropT (repeat n body)",
                "  denote_at_T : (marker : Entity) -> (body : PropT) -> "
                "model_denotes PropT body -> model_denotes PropT (at_T marker body)",
                "  denote_during_T : (marker : Entity) -> (body : PropT) -> "
                "model_denotes PropT body -> model_denotes PropT (during_T marker body)",
                "  denote_before_T : (marker : Entity) -> (body : PropT) -> "
                "model_denotes PropT body -> model_denotes PropT (before_T marker body)",
                "  denote_after_T : (marker : Entity) -> (body : PropT) -> "
                "model_denotes PropT body -> model_denotes PropT (after_T marker body)",
                "  denote_until_T : (marker : Entity) -> (body : PropT) -> "
                "model_denotes PropT body -> model_denotes PropT (until_T marker body)",
                "  denote_since_T : (marker : Entity) -> (body : PropT) -> "
                "model_denotes PropT body -> model_denotes PropT (since_T marker body)",
                "  denote_not_T : (body : PropT) -> "
                "model_denotes PropT body -> model_denotes PropT (not_T body)",
                "  denote_transition : (theme : Entity) -> (scale : StateScale) -> "
                "(source : State) -> (target : State) -> "
                "model_denotes TransitionT (Transition theme scale source target)",
                "  denote_cause : (causer : Entity) -> (effect : TransitionT) -> "
                "model_denotes TransitionT effect -> model_denotes PropT (Cause causer effect)",
            ]
        )
        return lines

    lines = [
        "Record SemanticModel : Type := {",
        "  model_denotes : forall A : Type, A -> Prop;",
    ]
    for name, (arg_types, result_type) in sorted(declarations["functions"].items()):
        lines.extend(_coq_function_denotation_field(name, arg_types, result_type))
    for type_name in declarations["types"]:
        lines.extend(
            [
                f"  {denotation_sigma_field(type_name)} : "
                f"forall P : {type_name} -> Prop,",
                f"      (forall x : {type_name}, model_denotes Prop (P x)) ->",
                f"      model_denotes Prop (exists x : {type_name}, P x);",
            ]
        )
    lines.extend(
        [
            "  denote_repeat : forall n : nat, forall body : PropT,",
            "      model_denotes PropT body ->",
            "      model_denotes PropT (repeat n body);",
            "  denote_at_T : forall marker : Entity, forall body : PropT,",
            "      model_denotes PropT body ->",
            "      model_denotes PropT (at_T marker body);",
            "  denote_during_T : forall marker : Entity, forall body : PropT,",
            "      model_denotes PropT body ->",
            "      model_denotes PropT (during_T marker body);",
            "  denote_before_T : forall marker : Entity, forall body : PropT,",
            "      model_denotes PropT body ->",
            "      model_denotes PropT (before_T marker body);",
            "  denote_after_T : forall marker : Entity, forall body : PropT,",
            "      model_denotes PropT body ->",
            "      model_denotes PropT (after_T marker body);",
            "  denote_until_T : forall marker : Entity, forall body : PropT,",
            "      model_denotes PropT body ->",
            "      model_denotes PropT (until_T marker body);",
            "  denote_since_T : forall marker : Entity, forall body : PropT,",
            "      model_denotes PropT body ->",
            "      model_denotes PropT (since_T marker body);",
            "  denote_not_T : forall body : PropT,",
            "      model_denotes PropT body ->",
            "      model_denotes PropT (not_T body);",
            "  denote_transition : "
            "forall theme : Entity, forall scale : StateScale, "
            "forall source : State, forall target : State,",
            "      model_denotes TransitionT "
            "(Transition theme scale source target);",
            "  denote_cause : "
            "forall causer : Entity, forall effect : TransitionT,",
            "      model_denotes TransitionT effect ->",
            "      model_denotes PropT (Cause causer effect)",
            "}.",
        ]
    )
    return lines


def denotation_soundness_projection_names(declarations: dict[str, Any]) -> list[str]:
    names = [
        denotation_application_field(name)
        for name in sorted(declarations["functions"])
    ]
    names.extend(
        denotation_sigma_field(type_name)
        for type_name in declarations["types"]
    )
    names.extend(
        [
            "denote_repeat",
            "denote_at_T",
            "denote_during_T",
            "denote_before_T",
            "denote_after_T",
            "denote_until_T",
            "denote_since_T",
            "denote_not_T",
            "denote_transition",
            "denote_cause",
        ]
    )
    return names


def truth_condition_spec_record_lines(
    declarations: dict[str, Any],
    target: str,
) -> list[str]:
    if target == "lean":
        lines = [
            "structure TruthConditionSpec : Type where",
            "  truth_denotes : (A : Type) -> A -> Prop",
        ]
        for name, (arg_types, result_type) in sorted(declarations["functions"].items()):
            lines.append(_lean_function_truth_field(name, arg_types, result_type))
        for type_name in declarations["types"]:
            lines.append(
                f"  {truth_sigma_field(type_name)} : "
                f"(P : {type_name} -> Prop) -> "
                f"((x : {type_name}) -> truth_denotes Prop (P x)) -> "
                f"truth_denotes Prop (Exists fun x : {type_name} => P x)"
            )
        lines.extend(
            [
                "  truth_repeat : (n : Nat) -> (body : PropT) -> "
                "truth_denotes PropT body -> truth_denotes PropT (repeat n body)",
                "  truth_at_T : (marker : Entity) -> (body : PropT) -> "
                "truth_denotes PropT body -> truth_denotes PropT (at_T marker body)",
                "  truth_during_T : (marker : Entity) -> (body : PropT) -> "
                "truth_denotes PropT body -> truth_denotes PropT (during_T marker body)",
                "  truth_before_T : (marker : Entity) -> (body : PropT) -> "
                "truth_denotes PropT body -> truth_denotes PropT (before_T marker body)",
                "  truth_after_T : (marker : Entity) -> (body : PropT) -> "
                "truth_denotes PropT body -> truth_denotes PropT (after_T marker body)",
                "  truth_until_T : (marker : Entity) -> (body : PropT) -> "
                "truth_denotes PropT body -> truth_denotes PropT (until_T marker body)",
                "  truth_since_T : (marker : Entity) -> (body : PropT) -> "
                "truth_denotes PropT body -> truth_denotes PropT (since_T marker body)",
                "  truth_not_T : (body : PropT) -> "
                "truth_denotes PropT body -> truth_denotes PropT (not_T body)",
                "  truth_transition : (theme : Entity) -> (scale : StateScale) -> "
                "(source : State) -> (target : State) -> "
                "truth_denotes TransitionT (Transition theme scale source target)",
                "  truth_cause : (causer : Entity) -> (effect : TransitionT) -> "
                "truth_denotes TransitionT effect -> truth_denotes PropT (Cause causer effect)",
            ]
        )
        return lines

    lines = [
        "Record TruthConditionSpec : Type := {",
        "  truth_denotes : forall A : Type, A -> Prop;",
    ]
    for name, (arg_types, result_type) in sorted(declarations["functions"].items()):
        lines.extend(_coq_function_truth_field(name, arg_types, result_type))
    for type_name in declarations["types"]:
        lines.extend(
            [
                f"  {truth_sigma_field(type_name)} : "
                f"forall P : {type_name} -> Prop,",
                f"      (forall x : {type_name}, truth_denotes Prop (P x)) ->",
                f"      truth_denotes Prop (exists x : {type_name}, P x);",
            ]
        )
    lines.extend(
        [
            "  truth_repeat : forall n : nat, forall body : PropT,",
            "      truth_denotes PropT body ->",
            "      truth_denotes PropT (repeat n body);",
            "  truth_at_T : forall marker : Entity, forall body : PropT,",
            "      truth_denotes PropT body ->",
            "      truth_denotes PropT (at_T marker body);",
            "  truth_during_T : forall marker : Entity, forall body : PropT,",
            "      truth_denotes PropT body ->",
            "      truth_denotes PropT (during_T marker body);",
            "  truth_before_T : forall marker : Entity, forall body : PropT,",
            "      truth_denotes PropT body ->",
            "      truth_denotes PropT (before_T marker body);",
            "  truth_after_T : forall marker : Entity, forall body : PropT,",
            "      truth_denotes PropT body ->",
            "      truth_denotes PropT (after_T marker body);",
            "  truth_until_T : forall marker : Entity, forall body : PropT,",
            "      truth_denotes PropT body ->",
            "      truth_denotes PropT (until_T marker body);",
            "  truth_since_T : forall marker : Entity, forall body : PropT,",
            "      truth_denotes PropT body ->",
            "      truth_denotes PropT (since_T marker body);",
            "  truth_not_T : forall body : PropT,",
            "      truth_denotes PropT body ->",
            "      truth_denotes PropT (not_T body);",
            "  truth_transition : "
            "forall theme : Entity, forall scale : StateScale, "
            "forall source : State, forall target : State,",
            "      truth_denotes TransitionT "
            "(Transition theme scale source target);",
            "  truth_cause : "
            "forall causer : Entity, forall effect : TransitionT,",
            "      truth_denotes TransitionT effect ->",
            "      truth_denotes PropT (Cause causer effect)",
            "}.",
        ]
    )
    return lines


def concrete_truth_condition_kernel_lines(
    declarations: dict[str, Any],
    target: str,
) -> list[str]:
    if target == "lean":
        lines = [
            "structure ConcreteTruthConditionKernel : Type where",
            "  kernel_denotes : (A : Type) -> A -> Prop",
        ]
        for name, (arg_types, result_type) in sorted(declarations["functions"].items()):
            lines.append(
                _lean_function_concrete_kernel_field(name, arg_types, result_type)
            )
        for type_name in declarations["types"]:
            lines.append(
                f"  {concrete_kernel_sigma_field(type_name)} : "
                f"(P : {type_name} -> Prop) -> "
                f"((x : {type_name}) -> kernel_denotes Prop (P x)) -> "
                f"kernel_denotes Prop (Exists fun x : {type_name} => P x)"
            )
        lines.extend(
            [
                "  repetition_truth : (n : Nat) -> (body : PropT) -> "
                "kernel_denotes PropT body -> kernel_denotes PropT (repeat n body)",
                "  temporal_truth_at_T : (marker : Entity) -> (body : PropT) -> "
                "kernel_denotes PropT body -> kernel_denotes PropT (at_T marker body)",
                "  temporal_truth_during_T : (marker : Entity) -> (body : PropT) -> "
                "kernel_denotes PropT body -> kernel_denotes PropT (during_T marker body)",
                "  temporal_truth_before_T : (marker : Entity) -> (body : PropT) -> "
                "kernel_denotes PropT body -> kernel_denotes PropT (before_T marker body)",
                "  temporal_truth_after_T : (marker : Entity) -> (body : PropT) -> "
                "kernel_denotes PropT body -> kernel_denotes PropT (after_T marker body)",
                "  temporal_truth_until_T : (marker : Entity) -> (body : PropT) -> "
                "kernel_denotes PropT body -> kernel_denotes PropT (until_T marker body)",
                "  temporal_truth_since_T : (marker : Entity) -> (body : PropT) -> "
                "kernel_denotes PropT body -> kernel_denotes PropT (since_T marker body)",
                "  polarity_truth_not_T : (body : PropT) -> "
                "kernel_denotes PropT body -> kernel_denotes PropT (not_T body)",
                "  transition_truth : (theme : Entity) -> (scale : StateScale) -> "
                "(source : State) -> (target : State) -> "
                "kernel_denotes TransitionT (Transition theme scale source target)",
                "  cause_truth : (causer : Entity) -> (effect : TransitionT) -> "
                "kernel_denotes TransitionT effect -> kernel_denotes PropT (Cause causer effect)",
            ]
        )

        field_pairs = [
            ("truth_denotes", "kernel_denotes"),
            *(
                (truth_application_field(name), concrete_kernel_application_field(name))
                for name in sorted(declarations["functions"])
            ),
            *(
                (truth_sigma_field(type_name), concrete_kernel_sigma_field(type_name))
                for type_name in declarations["types"]
            ),
            ("truth_repeat", "repetition_truth"),
            ("truth_at_T", "temporal_truth_at_T"),
            ("truth_during_T", "temporal_truth_during_T"),
            ("truth_before_T", "temporal_truth_before_T"),
            ("truth_after_T", "temporal_truth_after_T"),
            ("truth_until_T", "temporal_truth_until_T"),
            ("truth_since_T", "temporal_truth_since_T"),
            ("truth_not_T", "polarity_truth_not_T"),
            ("truth_transition", "transition_truth"),
            ("truth_cause", "cause_truth"),
        ]
        lines.extend(
            [
                "",
                "def truth_conditions_from_concrete_kernel "
                "(K : ConcreteTruthConditionKernel) : TruthConditionSpec := {",
            ]
        )
        for index, (truth_field, kernel_field) in enumerate(field_pairs):
            suffix = "," if index < len(field_pairs) - 1 else ""
            lines.append(f"  {truth_field} := K.{kernel_field}{suffix}")
        lines.extend(
            [
                "}",
                "",
                "theorem concrete_kernel_truth_condition_spec_exists :",
                "    (K : ConcreteTruthConditionKernel) -> "
                "Exists (fun T : TruthConditionSpec => "
                "T = truth_conditions_from_concrete_kernel K) := by",
                "  intro K",
                "  exact Exists.intro (truth_conditions_from_concrete_kernel K) rfl",
                "",
                "theorem concrete_kernel_induces_truth_condition_soundness :",
                "    (K : ConcreteTruthConditionKernel) -> "
                "(A : Type) -> (term : A) -> ModelInterpretable A term -> "
                "(truth_conditions_from_concrete_kernel K).truth_denotes A term := by",
                "  intro K A term h",
                "  apply truth_conditions_induce_denotational_soundness",
                "  exact h",
            ]
        )
        return lines

    lines = [
        "Record ConcreteTruthConditionKernel : Type := {",
        "  kernel_denotes : forall A : Type, A -> Prop;",
    ]
    for name, (arg_types, result_type) in sorted(declarations["functions"].items()):
        lines.extend(_coq_function_concrete_kernel_field(name, arg_types, result_type))
    for type_name in declarations["types"]:
        lines.extend(
            [
                f"  {concrete_kernel_sigma_field(type_name)} : "
                f"forall P : {type_name} -> Prop,",
                f"      (forall x : {type_name}, kernel_denotes Prop (P x)) ->",
                f"      kernel_denotes Prop (exists x : {type_name}, P x);",
            ]
        )
    lines.extend(
        [
            "  repetition_truth : forall n : nat, forall body : PropT,",
            "      kernel_denotes PropT body ->",
            "      kernel_denotes PropT (repeat n body);",
            "  temporal_truth_at_T : forall marker : Entity, forall body : PropT,",
            "      kernel_denotes PropT body ->",
            "      kernel_denotes PropT (at_T marker body);",
            "  temporal_truth_during_T : forall marker : Entity, forall body : PropT,",
            "      kernel_denotes PropT body ->",
            "      kernel_denotes PropT (during_T marker body);",
            "  temporal_truth_before_T : forall marker : Entity, forall body : PropT,",
            "      kernel_denotes PropT body ->",
            "      kernel_denotes PropT (before_T marker body);",
            "  temporal_truth_after_T : forall marker : Entity, forall body : PropT,",
            "      kernel_denotes PropT body ->",
            "      kernel_denotes PropT (after_T marker body);",
            "  temporal_truth_until_T : forall marker : Entity, forall body : PropT,",
            "      kernel_denotes PropT body ->",
            "      kernel_denotes PropT (until_T marker body);",
            "  temporal_truth_since_T : forall marker : Entity, forall body : PropT,",
            "      kernel_denotes PropT body ->",
            "      kernel_denotes PropT (since_T marker body);",
            "  polarity_truth_not_T : forall body : PropT,",
            "      kernel_denotes PropT body ->",
            "      kernel_denotes PropT (not_T body);",
            "  transition_truth : "
            "forall theme : Entity, forall scale : StateScale, "
            "forall source : State, forall target : State,",
            "      kernel_denotes TransitionT "
            "(Transition theme scale source target);",
            "  cause_truth : "
            "forall causer : Entity, forall effect : TransitionT,",
            "      kernel_denotes TransitionT effect ->",
            "      kernel_denotes PropT (Cause causer effect)",
            "}.",
            "",
        ]
    )
    field_pairs = [
        ("truth_denotes", "kernel_denotes"),
        *(
            (truth_application_field(name), concrete_kernel_application_field(name))
            for name in sorted(declarations["functions"])
        ),
        *(
            (truth_sigma_field(type_name), concrete_kernel_sigma_field(type_name))
            for type_name in declarations["types"]
        ),
        ("truth_repeat", "repetition_truth"),
        ("truth_at_T", "temporal_truth_at_T"),
        ("truth_during_T", "temporal_truth_during_T"),
        ("truth_before_T", "temporal_truth_before_T"),
        ("truth_after_T", "temporal_truth_after_T"),
        ("truth_until_T", "temporal_truth_until_T"),
        ("truth_since_T", "temporal_truth_since_T"),
        ("truth_not_T", "polarity_truth_not_T"),
        ("truth_transition", "transition_truth"),
        ("truth_cause", "cause_truth"),
    ]
    lines.append(
        "Definition truth_conditions_from_concrete_kernel "
        "(K : ConcreteTruthConditionKernel) : TruthConditionSpec := {|"
    )
    for index, (truth_field, kernel_field) in enumerate(field_pairs):
        suffix = ";" if index < len(field_pairs) - 1 else ""
        lines.append(f"  {truth_field} := {kernel_field} K{suffix}")
    lines.extend(
        [
            "|}.",
            "",
            "Theorem concrete_kernel_truth_condition_spec_exists :",
            "  forall K : ConcreteTruthConditionKernel,",
            "    exists T : TruthConditionSpec,",
            "      T = truth_conditions_from_concrete_kernel K.",
            "Proof.",
            "  intro K. exists (truth_conditions_from_concrete_kernel K).",
            "  reflexivity.",
            "Qed.",
            "",
            "Theorem concrete_kernel_induces_truth_condition_soundness :",
            "  forall K : ConcreteTruthConditionKernel,",
            "  forall A : Type, forall term : A,",
            "    ModelInterpretable A term ->",
            "    truth_denotes (truth_conditions_from_concrete_kernel K) A term.",
            "Proof.",
            "  intros K A term H.",
            "  apply truth_conditions_induce_denotational_soundness.",
            "  exact H.",
            "Qed.",
        ]
    )
    return lines


def independent_truth_condition_obligation_ledger_lines(
    declarations: dict[str, Any],
    target: str,
) -> list[str]:
    if target == "lean":
        lines = [
            "structure IndependentTruthConditionObligationLedger : Type where",
            "  ledger_denotes : (A : Type) -> A -> Prop",
            "  ledger_kernel : ConcreteTruthConditionKernel",
            "  ledger_denotes_matches_kernel : "
            "(A : Type) -> (term : A) -> "
            "ledger_denotes A term = ledger_kernel.kernel_denotes A term",
            "  ledger_truth_conditions : TruthConditionSpec",
            "  ledger_truth_conditions_match_kernel : "
            "ledger_truth_conditions = "
            "truth_conditions_from_concrete_kernel ledger_kernel",
        ]
        for name, (arg_types, result_type) in sorted(declarations["functions"].items()):
            lines.append(
                _lean_function_independent_obligation_field(
                    name,
                    arg_types,
                    result_type,
                )
            )
        for type_name in declarations["types"]:
            lines.append(
                f"  {independent_obligation_sigma_field(type_name)} : "
                f"(P : {type_name} -> Prop) -> "
                f"((x : {type_name}) -> ledger_denotes Prop (P x)) -> "
                f"ledger_denotes Prop (Exists fun x : {type_name} => P x)"
            )
        lines.extend(
            [
                "  ledger_repetition_truth_obligation : "
                "(n : Nat) -> (body : PropT) -> "
                "ledger_denotes PropT body -> ledger_denotes PropT (repeat n body)",
                "  ledger_temporal_truth_at_T_obligation : "
                "(marker : Entity) -> (body : PropT) -> "
                "ledger_denotes PropT body -> ledger_denotes PropT (at_T marker body)",
                "  ledger_temporal_truth_during_T_obligation : "
                "(marker : Entity) -> (body : PropT) -> "
                "ledger_denotes PropT body -> ledger_denotes PropT (during_T marker body)",
                "  ledger_temporal_truth_before_T_obligation : "
                "(marker : Entity) -> (body : PropT) -> "
                "ledger_denotes PropT body -> ledger_denotes PropT (before_T marker body)",
                "  ledger_temporal_truth_after_T_obligation : "
                "(marker : Entity) -> (body : PropT) -> "
                "ledger_denotes PropT body -> ledger_denotes PropT (after_T marker body)",
                "  ledger_temporal_truth_until_T_obligation : "
                "(marker : Entity) -> (body : PropT) -> "
                "ledger_denotes PropT body -> ledger_denotes PropT (until_T marker body)",
                "  ledger_temporal_truth_since_T_obligation : "
                "(marker : Entity) -> (body : PropT) -> "
                "ledger_denotes PropT body -> ledger_denotes PropT (since_T marker body)",
                "  ledger_polarity_truth_not_T_obligation : (body : PropT) -> "
                "ledger_denotes PropT body -> ledger_denotes PropT (not_T body)",
                "  ledger_transition_truth_obligation : "
                "(theme : Entity) -> (scale : StateScale) -> "
                "(source : State) -> (target : State) -> "
                "ledger_denotes TransitionT (Transition theme scale source target)",
                "  ledger_cause_truth_obligation : "
                "(causer : Entity) -> (effect : TransitionT) -> "
                "ledger_denotes TransitionT effect -> "
                "ledger_denotes PropT (Cause causer effect)",
                "",
                "def independent_truth_condition_obligation_ledger "
                "(K : ConcreteTruthConditionKernel) : "
                "IndependentTruthConditionObligationLedger := {",
                "  ledger_denotes := K.kernel_denotes,",
                "  ledger_kernel := K,",
                "  ledger_denotes_matches_kernel := fun A term => rfl,",
                "  ledger_truth_conditions := "
                "truth_conditions_from_concrete_kernel K,",
                "  ledger_truth_conditions_match_kernel := rfl,",
            ]
        )
        ledger_fields: list[tuple[str, str]] = []
        for name in sorted(declarations["functions"]):
            ledger_fields.append(
                (
                    independent_obligation_application_field(name),
                    f"K.{concrete_kernel_application_field(name)}",
                )
            )
        for type_name in declarations["types"]:
            ledger_fields.append(
                (
                    independent_obligation_sigma_field(type_name),
                    f"K.{concrete_kernel_sigma_field(type_name)}",
                )
            )
        ledger_fields.extend(
            [
                ("ledger_repetition_truth_obligation", "K.repetition_truth"),
                ("ledger_temporal_truth_at_T_obligation", "K.temporal_truth_at_T"),
                (
                    "ledger_temporal_truth_during_T_obligation",
                    "K.temporal_truth_during_T",
                ),
                (
                    "ledger_temporal_truth_before_T_obligation",
                    "K.temporal_truth_before_T",
                ),
                (
                    "ledger_temporal_truth_after_T_obligation",
                    "K.temporal_truth_after_T",
                ),
                (
                    "ledger_temporal_truth_until_T_obligation",
                    "K.temporal_truth_until_T",
                ),
                (
                    "ledger_temporal_truth_since_T_obligation",
                    "K.temporal_truth_since_T",
                ),
                ("ledger_polarity_truth_not_T_obligation", "K.polarity_truth_not_T"),
                ("ledger_transition_truth_obligation", "K.transition_truth"),
                ("ledger_cause_truth_obligation", "K.cause_truth"),
            ]
        )
        for index, (field, value) in enumerate(ledger_fields):
            suffix = "," if index < len(ledger_fields) - 1 else ""
            lines.append(f"  {field} := {value}{suffix}")
        lines.extend(
            [
                "}",
                "",
                "theorem independent_truth_condition_obligation_ledger_exists :",
                "    (K : ConcreteTruthConditionKernel) -> "
                "Exists (fun L : IndependentTruthConditionObligationLedger => "
                "L.ledger_kernel = K) := by",
                "  intro K",
                "  exact Exists.intro "
                "(independent_truth_condition_obligation_ledger K) rfl",
                "",
                "theorem "
                "independent_truth_condition_obligation_ledger_induces_truth_conditions :",
                "    (K : ConcreteTruthConditionKernel) -> "
                "(independent_truth_condition_obligation_ledger K)."
                "ledger_truth_conditions = "
                "truth_conditions_from_concrete_kernel K := by",
                "  intro K",
                "  rfl",
                "",
                "theorem "
                "independent_truth_condition_obligation_ledger_truth_conditions_sound :",
                "    (K : ConcreteTruthConditionKernel) -> "
                "(A : Type) -> (term : A) -> ModelInterpretable A term -> "
                "(independent_truth_condition_obligation_ledger K)."
                "ledger_truth_conditions.truth_denotes A term := by",
                "  intro K A term h",
                "  apply concrete_kernel_induces_truth_condition_soundness",
                "  exact h",
            ]
        )
        return lines

    lines = [
        "Record IndependentTruthConditionObligationLedger : Type := {",
        "  ledger_denotes : forall A : Type, A -> Prop;",
        "  ledger_kernel : ConcreteTruthConditionKernel;",
        "  ledger_denotes_matches_kernel : "
        "forall A : Type, forall term : A,",
        "      ledger_denotes A term = "
        "kernel_denotes ledger_kernel A term;",
        "  ledger_truth_conditions : TruthConditionSpec;",
        "  ledger_truth_conditions_match_kernel :",
        "      ledger_truth_conditions = "
        "truth_conditions_from_concrete_kernel ledger_kernel;",
    ]
    for name, (arg_types, result_type) in sorted(declarations["functions"].items()):
        lines.extend(
            _coq_function_independent_obligation_field(name, arg_types, result_type)
        )
    for type_name in declarations["types"]:
        lines.extend(
            [
                f"  {independent_obligation_sigma_field(type_name)} : "
                f"forall P : {type_name} -> Prop,",
                f"      (forall x : {type_name}, ledger_denotes Prop (P x)) ->",
                f"      ledger_denotes Prop (exists x : {type_name}, P x);",
            ]
        )
    lines.extend(
        [
            "  ledger_repetition_truth_obligation : "
            "forall n : nat, forall body : PropT,",
            "      ledger_denotes PropT body ->",
            "      ledger_denotes PropT (repeat n body);",
            "  ledger_temporal_truth_at_T_obligation : "
            "forall marker : Entity, forall body : PropT,",
            "      ledger_denotes PropT body ->",
            "      ledger_denotes PropT (at_T marker body);",
            "  ledger_temporal_truth_during_T_obligation : "
            "forall marker : Entity, forall body : PropT,",
            "      ledger_denotes PropT body ->",
            "      ledger_denotes PropT (during_T marker body);",
            "  ledger_temporal_truth_before_T_obligation : "
            "forall marker : Entity, forall body : PropT,",
            "      ledger_denotes PropT body ->",
            "      ledger_denotes PropT (before_T marker body);",
            "  ledger_temporal_truth_after_T_obligation : "
            "forall marker : Entity, forall body : PropT,",
            "      ledger_denotes PropT body ->",
            "      ledger_denotes PropT (after_T marker body);",
            "  ledger_temporal_truth_until_T_obligation : "
            "forall marker : Entity, forall body : PropT,",
            "      ledger_denotes PropT body ->",
            "      ledger_denotes PropT (until_T marker body);",
            "  ledger_temporal_truth_since_T_obligation : "
            "forall marker : Entity, forall body : PropT,",
            "      ledger_denotes PropT body ->",
            "      ledger_denotes PropT (since_T marker body);",
            "  ledger_polarity_truth_not_T_obligation : forall body : PropT,",
            "      ledger_denotes PropT body ->",
            "      ledger_denotes PropT (not_T body);",
            "  ledger_transition_truth_obligation : "
            "forall theme : Entity, forall scale : StateScale,",
            "forall source : State, forall target : State,",
            "      ledger_denotes TransitionT "
            "(Transition theme scale source target);",
            "  ledger_cause_truth_obligation : "
            "forall causer : Entity, forall effect : TransitionT,",
            "      ledger_denotes TransitionT effect ->",
            "      ledger_denotes PropT (Cause causer effect)",
            "}.",
            "",
            "Definition independent_truth_condition_obligation_ledger",
            "  (K : ConcreteTruthConditionKernel) :",
            "  IndependentTruthConditionObligationLedger := {|",
            "  ledger_denotes := kernel_denotes K;",
            "  ledger_kernel := K;",
            "  ledger_denotes_matches_kernel := fun A term => eq_refl;",
            "  ledger_truth_conditions := truth_conditions_from_concrete_kernel K;",
            "  ledger_truth_conditions_match_kernel := eq_refl;",
        ]
    )
    ledger_fields: list[tuple[str, str]] = []
    for name in sorted(declarations["functions"]):
        ledger_fields.append(
            (
                independent_obligation_application_field(name),
                f"{concrete_kernel_application_field(name)} K",
            )
        )
    for type_name in declarations["types"]:
        ledger_fields.append(
            (
                independent_obligation_sigma_field(type_name),
                f"{concrete_kernel_sigma_field(type_name)} K",
            )
        )
    ledger_fields.extend(
        [
            ("ledger_repetition_truth_obligation", "repetition_truth K"),
            ("ledger_temporal_truth_at_T_obligation", "temporal_truth_at_T K"),
            ("ledger_temporal_truth_during_T_obligation", "temporal_truth_during_T K"),
            ("ledger_temporal_truth_before_T_obligation", "temporal_truth_before_T K"),
            ("ledger_temporal_truth_after_T_obligation", "temporal_truth_after_T K"),
            ("ledger_temporal_truth_until_T_obligation", "temporal_truth_until_T K"),
            ("ledger_temporal_truth_since_T_obligation", "temporal_truth_since_T K"),
            ("ledger_polarity_truth_not_T_obligation", "polarity_truth_not_T K"),
            ("ledger_transition_truth_obligation", "transition_truth K"),
            ("ledger_cause_truth_obligation", "cause_truth K"),
        ]
    )
    for index, (field, value) in enumerate(ledger_fields):
        suffix = ";" if index < len(ledger_fields) - 1 else ""
        lines.append(f"  {field} := {value}{suffix}")
    lines.extend(
        [
            "|}.",
            "",
            "Theorem independent_truth_condition_obligation_ledger_exists :",
            "  forall K : ConcreteTruthConditionKernel,",
            "    exists L : IndependentTruthConditionObligationLedger,",
            "      ledger_kernel L = K.",
            "Proof.",
            "  intro K.",
            "  exists (independent_truth_condition_obligation_ledger K).",
            "  reflexivity.",
            "Qed.",
            "",
            "Theorem "
            "independent_truth_condition_obligation_ledger_induces_truth_conditions :",
            "  forall K : ConcreteTruthConditionKernel,",
            "    ledger_truth_conditions",
            "      (independent_truth_condition_obligation_ledger K) =",
            "    truth_conditions_from_concrete_kernel K.",
            "Proof.",
            "  intro K. reflexivity.",
            "Qed.",
            "",
            "Theorem "
            "independent_truth_condition_obligation_ledger_truth_conditions_sound :",
            "  forall K : ConcreteTruthConditionKernel,",
            "  forall A : Type, forall term : A,",
            "    ModelInterpretable A term ->",
            "    truth_denotes",
            "      (ledger_truth_conditions",
            "        (independent_truth_condition_obligation_ledger K))",
            "      A term.",
            "Proof.",
            "  intros K A term H.",
            "  apply concrete_kernel_induces_truth_condition_soundness.",
            "  exact H.",
            "Qed.",
        ]
    )
    return lines


def evidence_backed_truth_condition_source_lines(
    declarations: dict[str, Any],
    target: str,
) -> list[str]:
    if target == "lean":
        lines = [
            "constant TruthEvidence : Prop -> Type",
            "constant truth_evidence_sound : "
            "(P : Prop) -> TruthEvidence P -> P",
            "constant truth_evidence_intro : "
            "(P : Prop) -> P -> TruthEvidence P",
            "",
            "structure EvidenceBackedTruthConditionSources : Type where",
            "  evidence_denotes : (A : Type) -> A -> Prop",
        ]
        for name, (arg_types, result_type) in sorted(declarations["functions"].items()):
            lines.append(
                _lean_function_evidence_source_field(name, arg_types, result_type)
            )
        for type_name in declarations["types"]:
            lines.append(
                f"  {evidence_source_sigma_field(type_name)} : "
                f"(P : {type_name} -> Prop) -> "
                f"((x : {type_name}) -> evidence_denotes Prop (P x)) -> "
                "TruthEvidence "
                f"(evidence_denotes Prop (Exists fun x : {type_name} => P x))"
            )
        lines.extend(
            [
                "  evidence_repetition_truth : (n : Nat) -> (body : PropT) -> "
                "evidence_denotes PropT body -> "
                "TruthEvidence (evidence_denotes PropT (repeat n body))",
                "  evidence_temporal_truth_at_T : "
                "(marker : Entity) -> (body : PropT) -> "
                "evidence_denotes PropT body -> "
                "TruthEvidence (evidence_denotes PropT (at_T marker body))",
                "  evidence_temporal_truth_during_T : "
                "(marker : Entity) -> (body : PropT) -> "
                "evidence_denotes PropT body -> "
                "TruthEvidence (evidence_denotes PropT (during_T marker body))",
                "  evidence_temporal_truth_before_T : "
                "(marker : Entity) -> (body : PropT) -> "
                "evidence_denotes PropT body -> "
                "TruthEvidence (evidence_denotes PropT (before_T marker body))",
                "  evidence_temporal_truth_after_T : "
                "(marker : Entity) -> (body : PropT) -> "
                "evidence_denotes PropT body -> "
                "TruthEvidence (evidence_denotes PropT (after_T marker body))",
                "  evidence_temporal_truth_until_T : "
                "(marker : Entity) -> (body : PropT) -> "
                "evidence_denotes PropT body -> "
                "TruthEvidence (evidence_denotes PropT (until_T marker body))",
                "  evidence_temporal_truth_since_T : "
                "(marker : Entity) -> (body : PropT) -> "
                "evidence_denotes PropT body -> "
                "TruthEvidence (evidence_denotes PropT (since_T marker body))",
                "  evidence_polarity_truth_not_T : (body : PropT) -> "
                "evidence_denotes PropT body -> "
                "TruthEvidence (evidence_denotes PropT (not_T body))",
                "  evidence_transition_truth : "
                "(theme : Entity) -> (scale : StateScale) -> "
                "(source : State) -> (target : State) -> "
                "TruthEvidence "
                "(evidence_denotes TransitionT "
                "(Transition theme scale source target))",
                "  evidence_cause_truth : "
                "(causer : Entity) -> (effect : TransitionT) -> "
                "evidence_denotes TransitionT effect -> "
                "TruthEvidence "
                "(evidence_denotes PropT (Cause causer effect))",
                "",
                "def concrete_kernel_from_evidence_sources "
                "(S : EvidenceBackedTruthConditionSources) : "
                "ConcreteTruthConditionKernel := {",
                "  kernel_denotes := S.evidence_denotes,",
            ]
        )
        assignment_groups: list[list[str]] = []
        for name, (arg_types, result_type) in sorted(declarations["functions"].items()):
            _field, group = _lean_function_evidence_kernel_assignment(
                name,
                arg_types,
                result_type,
            )
            assignment_groups.append(group)
        for type_name in declarations["types"]:
            assignment_groups.append(
                [
                    f"  {concrete_kernel_sigma_field(type_name)} := fun P h =>",
                    "      truth_evidence_sound",
                    "        "
                    f"(S.evidence_denotes Prop "
                    f"(Exists fun x : {type_name} => P x))",
                    f"        (S.{evidence_source_sigma_field(type_name)} P h)",
                ]
            )
        assignment_groups.extend(
            [
                [
                    "  repetition_truth := fun n body h =>",
                    "      truth_evidence_sound",
                    "        (S.evidence_denotes PropT (repeat n body))",
                    "        (S.evidence_repetition_truth n body h)",
                ],
                [
                    "  temporal_truth_at_T := fun marker body h =>",
                    "      truth_evidence_sound",
                    "        (S.evidence_denotes PropT (at_T marker body))",
                    "        (S.evidence_temporal_truth_at_T marker body h)",
                ],
                [
                    "  temporal_truth_during_T := fun marker body h =>",
                    "      truth_evidence_sound",
                    "        (S.evidence_denotes PropT (during_T marker body))",
                    "        (S.evidence_temporal_truth_during_T marker body h)",
                ],
                [
                    "  temporal_truth_before_T := fun marker body h =>",
                    "      truth_evidence_sound",
                    "        (S.evidence_denotes PropT (before_T marker body))",
                    "        (S.evidence_temporal_truth_before_T marker body h)",
                ],
                [
                    "  temporal_truth_after_T := fun marker body h =>",
                    "      truth_evidence_sound",
                    "        (S.evidence_denotes PropT (after_T marker body))",
                    "        (S.evidence_temporal_truth_after_T marker body h)",
                ],
                [
                    "  temporal_truth_until_T := fun marker body h =>",
                    "      truth_evidence_sound",
                    "        (S.evidence_denotes PropT (until_T marker body))",
                    "        (S.evidence_temporal_truth_until_T marker body h)",
                ],
                [
                    "  temporal_truth_since_T := fun marker body h =>",
                    "      truth_evidence_sound",
                    "        (S.evidence_denotes PropT (since_T marker body))",
                    "        (S.evidence_temporal_truth_since_T marker body h)",
                ],
                [
                    "  polarity_truth_not_T := fun body h =>",
                    "      truth_evidence_sound",
                    "        (S.evidence_denotes PropT (not_T body))",
                    "        (S.evidence_polarity_truth_not_T body h)",
                ],
                [
                    "  transition_truth := fun theme scale source target =>",
                    "      truth_evidence_sound",
                    "        (S.evidence_denotes TransitionT "
                    "(Transition theme scale source target))",
                    "        (S.evidence_transition_truth theme scale source target)",
                ],
                [
                    "  cause_truth := fun causer effect h =>",
                    "      truth_evidence_sound",
                    "        (S.evidence_denotes PropT (Cause causer effect))",
                    "        (S.evidence_cause_truth causer effect h)",
                ],
            ]
        )
        for index, group in enumerate(assignment_groups):
            suffix = "," if index < len(assignment_groups) - 1 else ""
            for line_index, line in enumerate(group):
                if line_index == len(group) - 1:
                    lines.append(line + suffix)
                else:
                    lines.append(line)
        lines.extend(
            [
                "}",
                "",
                "def evidence_backed_truth_condition_ledger "
                "(S : EvidenceBackedTruthConditionSources) : "
                "IndependentTruthConditionObligationLedger :=",
                "  independent_truth_condition_obligation_ledger "
                "(concrete_kernel_from_evidence_sources S)",
                "",
                "theorem evidence_backed_truth_condition_sources_induce_kernel :",
                "    (S : EvidenceBackedTruthConditionSources) -> "
                "Exists (fun K : ConcreteTruthConditionKernel => "
                "K = concrete_kernel_from_evidence_sources S) := by",
                "  intro S",
                "  exact Exists.intro (concrete_kernel_from_evidence_sources S) rfl",
                "",
                "theorem "
                "evidence_backed_truth_condition_sources_induce_truth_conditions :",
                "    (S : EvidenceBackedTruthConditionSources) -> "
                "(evidence_backed_truth_condition_ledger S).ledger_truth_conditions = "
                "truth_conditions_from_concrete_kernel "
                "(concrete_kernel_from_evidence_sources S) := by",
                "  intro S",
                "  rfl",
                "",
                "theorem evidence_backed_truth_condition_sources_sound :",
                "    (S : EvidenceBackedTruthConditionSources) -> "
                "(A : Type) -> (term : A) -> ModelInterpretable A term -> "
                "(evidence_backed_truth_condition_ledger S)."
                "ledger_truth_conditions.truth_denotes A term := by",
                "  intro S A term h",
                "  exact "
                "independent_truth_condition_obligation_ledger_truth_conditions_sound "
                "(concrete_kernel_from_evidence_sources S) A term h",
            ]
        )
        return lines

    lines = [
        "Parameter TruthEvidence : Prop -> Type.",
        "Parameter truth_evidence_sound : "
        "forall P : Prop, TruthEvidence P -> P.",
        "Parameter truth_evidence_intro : "
        "forall P : Prop, P -> TruthEvidence P.",
        "",
        "Record EvidenceBackedTruthConditionSources : Type := {",
        "  evidence_denotes : forall A : Type, A -> Prop;",
    ]
    for name, (arg_types, result_type) in sorted(declarations["functions"].items()):
        lines.extend(
            _coq_function_evidence_source_field(name, arg_types, result_type)
        )
    for type_name in declarations["types"]:
        lines.extend(
            [
                f"  {evidence_source_sigma_field(type_name)} : "
                f"forall P : {type_name} -> Prop,",
                f"      (forall x : {type_name}, evidence_denotes Prop (P x)) ->",
                "      TruthEvidence "
                f"(evidence_denotes Prop (exists x : {type_name}, P x));",
            ]
        )
    lines.extend(
        [
            "  evidence_repetition_truth : "
            "forall n : nat, forall body : PropT,",
            "      evidence_denotes PropT body ->",
            "      TruthEvidence (evidence_denotes PropT (repeat n body));",
            "  evidence_temporal_truth_at_T : "
            "forall marker : Entity, forall body : PropT,",
            "      evidence_denotes PropT body ->",
            "      TruthEvidence (evidence_denotes PropT (at_T marker body));",
            "  evidence_temporal_truth_during_T : "
            "forall marker : Entity, forall body : PropT,",
            "      evidence_denotes PropT body ->",
            "      TruthEvidence (evidence_denotes PropT (during_T marker body));",
            "  evidence_temporal_truth_before_T : "
            "forall marker : Entity, forall body : PropT,",
            "      evidence_denotes PropT body ->",
            "      TruthEvidence (evidence_denotes PropT (before_T marker body));",
            "  evidence_temporal_truth_after_T : "
            "forall marker : Entity, forall body : PropT,",
            "      evidence_denotes PropT body ->",
            "      TruthEvidence (evidence_denotes PropT (after_T marker body));",
            "  evidence_temporal_truth_until_T : "
            "forall marker : Entity, forall body : PropT,",
            "      evidence_denotes PropT body ->",
            "      TruthEvidence (evidence_denotes PropT (until_T marker body));",
            "  evidence_temporal_truth_since_T : "
            "forall marker : Entity, forall body : PropT,",
            "      evidence_denotes PropT body ->",
            "      TruthEvidence (evidence_denotes PropT (since_T marker body));",
            "  evidence_polarity_truth_not_T : forall body : PropT,",
            "      evidence_denotes PropT body ->",
            "      TruthEvidence (evidence_denotes PropT (not_T body));",
            "  evidence_transition_truth : "
            "forall theme : Entity, forall scale : StateScale,",
            "forall source : State, forall target : State,",
            "      TruthEvidence "
            "(evidence_denotes TransitionT "
            "(Transition theme scale source target));",
            "  evidence_cause_truth : "
            "forall causer : Entity, forall effect : TransitionT,",
            "      evidence_denotes TransitionT effect ->",
            "      TruthEvidence "
            "(evidence_denotes PropT (Cause causer effect))",
            "}.",
            "",
            "Definition concrete_kernel_from_evidence_sources",
            "  (S : EvidenceBackedTruthConditionSources) :",
            "  ConcreteTruthConditionKernel := {|",
            "  kernel_denotes := evidence_denotes S;",
        ]
    )
    assignment_groups: list[list[str]] = []
    for name, (arg_types, result_type) in sorted(declarations["functions"].items()):
        _field, group = _coq_function_evidence_kernel_assignment(
            name,
            arg_types,
            result_type,
        )
        assignment_groups.append(group)
    for type_name in declarations["types"]:
        assignment_groups.append(
            [
                f"  {concrete_kernel_sigma_field(type_name)} := fun P h =>",
                "      truth_evidence_sound",
                f"        (evidence_denotes S Prop "
                f"(exists x : {type_name}, P x))",
                f"        ({evidence_source_sigma_field(type_name)} S P h)",
            ]
        )
    assignment_groups.extend(
        [
            [
                "  repetition_truth := fun n body h =>",
                "      truth_evidence_sound",
                "        (evidence_denotes S PropT (repeat n body))",
                "        (evidence_repetition_truth S n body h)",
            ],
            [
                "  temporal_truth_at_T := fun marker body h =>",
                "      truth_evidence_sound",
                "        (evidence_denotes S PropT (at_T marker body))",
                "        (evidence_temporal_truth_at_T S marker body h)",
            ],
            [
                "  temporal_truth_during_T := fun marker body h =>",
                "      truth_evidence_sound",
                "        (evidence_denotes S PropT (during_T marker body))",
                "        (evidence_temporal_truth_during_T S marker body h)",
            ],
            [
                "  temporal_truth_before_T := fun marker body h =>",
                "      truth_evidence_sound",
                "        (evidence_denotes S PropT (before_T marker body))",
                "        (evidence_temporal_truth_before_T S marker body h)",
            ],
            [
                "  temporal_truth_after_T := fun marker body h =>",
                "      truth_evidence_sound",
                "        (evidence_denotes S PropT (after_T marker body))",
                "        (evidence_temporal_truth_after_T S marker body h)",
            ],
            [
                "  temporal_truth_until_T := fun marker body h =>",
                "      truth_evidence_sound",
                "        (evidence_denotes S PropT (until_T marker body))",
                "        (evidence_temporal_truth_until_T S marker body h)",
            ],
            [
                "  temporal_truth_since_T := fun marker body h =>",
                "      truth_evidence_sound",
                "        (evidence_denotes S PropT (since_T marker body))",
                "        (evidence_temporal_truth_since_T S marker body h)",
            ],
            [
                "  polarity_truth_not_T := fun body h =>",
                "      truth_evidence_sound",
                "        (evidence_denotes S PropT (not_T body))",
                "        (evidence_polarity_truth_not_T S body h)",
            ],
            [
                "  transition_truth := fun theme scale source target =>",
                "      truth_evidence_sound",
                "        (evidence_denotes S TransitionT "
                "(Transition theme scale source target))",
                "        (evidence_transition_truth S theme scale source target)",
            ],
            [
                "  cause_truth := fun causer effect h =>",
                "      truth_evidence_sound",
                "        (evidence_denotes S PropT (Cause causer effect))",
                "        (evidence_cause_truth S causer effect h)",
            ],
        ]
    )
    for index, group in enumerate(assignment_groups):
        suffix = ";" if index < len(assignment_groups) - 1 else ""
        for line_index, line in enumerate(group):
            if line_index == len(group) - 1:
                lines.append(line + suffix)
            else:
                lines.append(line)
    lines.extend(
        [
            "|}.",
            "",
            "Definition evidence_backed_truth_condition_ledger",
            "  (S : EvidenceBackedTruthConditionSources) :",
            "  IndependentTruthConditionObligationLedger :=",
            "  independent_truth_condition_obligation_ledger",
            "    (concrete_kernel_from_evidence_sources S).",
            "",
            "Theorem evidence_backed_truth_condition_sources_induce_kernel :",
            "  forall S : EvidenceBackedTruthConditionSources,",
            "    exists K : ConcreteTruthConditionKernel,",
            "      K = concrete_kernel_from_evidence_sources S.",
            "Proof.",
            "  intro S.",
            "  exists (concrete_kernel_from_evidence_sources S).",
            "  reflexivity.",
            "Qed.",
            "",
            "Theorem "
            "evidence_backed_truth_condition_sources_induce_truth_conditions :",
            "  forall S : EvidenceBackedTruthConditionSources,",
            "    ledger_truth_conditions",
            "      (evidence_backed_truth_condition_ledger S) =",
            "    truth_conditions_from_concrete_kernel",
            "      (concrete_kernel_from_evidence_sources S).",
            "Proof.",
            "  intro S. reflexivity.",
            "Qed.",
            "",
            "Theorem evidence_backed_truth_condition_sources_sound :",
            "  forall S : EvidenceBackedTruthConditionSources,",
            "  forall A : Type, forall term : A,",
            "    ModelInterpretable A term ->",
            "    truth_denotes",
            "      (ledger_truth_conditions",
            "        (evidence_backed_truth_condition_ledger S))",
            "      A term.",
            "Proof.",
            "  intros S A term H.",
            "  exact",
            "    (independent_truth_condition_obligation_ledger_truth_conditions_sound",
            "      (concrete_kernel_from_evidence_sources S) A term H).",
            "Qed.",
        ]
    )
    return lines


def primitive_truth_assumption_kernel_lines(
    declarations: dict[str, Any],
    target: str,
) -> list[str]:
    if target == "lean":
        lines = [
            "structure PrimitiveTruthAssumptions : Type where",
            "  primitive_denotes : (A : Type) -> A -> Prop",
        ]
        for name, (arg_types, result_type) in sorted(declarations["functions"].items()):
            lines.append(_lean_function_primitive_truth_field(name, arg_types, result_type))
        for type_name in declarations["types"]:
            lines.append(
                f"  {primitive_truth_sigma_field(type_name)} : "
                f"(P : {type_name} -> Prop) -> "
                f"((x : {type_name}) -> primitive_denotes Prop (P x)) -> "
                f"primitive_denotes Prop (Exists fun x : {type_name} => P x)"
            )
        lines.extend(
            [
                "  primitive_repetition_truth : (n : Nat) -> (body : PropT) -> "
                "primitive_denotes PropT body -> primitive_denotes PropT (repeat n body)",
                "  primitive_temporal_truth_at_T : (marker : Entity) -> (body : PropT) -> "
                "primitive_denotes PropT body -> primitive_denotes PropT (at_T marker body)",
                "  primitive_temporal_truth_during_T : (marker : Entity) -> (body : PropT) -> "
                "primitive_denotes PropT body -> primitive_denotes PropT (during_T marker body)",
                "  primitive_temporal_truth_before_T : (marker : Entity) -> (body : PropT) -> "
                "primitive_denotes PropT body -> primitive_denotes PropT (before_T marker body)",
                "  primitive_temporal_truth_after_T : (marker : Entity) -> (body : PropT) -> "
                "primitive_denotes PropT body -> primitive_denotes PropT (after_T marker body)",
                "  primitive_temporal_truth_until_T : (marker : Entity) -> (body : PropT) -> "
                "primitive_denotes PropT body -> primitive_denotes PropT (until_T marker body)",
                "  primitive_temporal_truth_since_T : (marker : Entity) -> (body : PropT) -> "
                "primitive_denotes PropT body -> primitive_denotes PropT (since_T marker body)",
                "  primitive_polarity_truth_not_T : (body : PropT) -> "
                "primitive_denotes PropT body -> primitive_denotes PropT (not_T body)",
                "  primitive_transition_truth : (theme : Entity) -> (scale : StateScale) -> "
                "(source : State) -> (target : State) -> "
                "primitive_denotes TransitionT (Transition theme scale source target)",
                "  primitive_cause_truth : (causer : Entity) -> (effect : TransitionT) -> "
                "primitive_denotes TransitionT effect -> primitive_denotes PropT (Cause causer effect)",
                "",
                "constant primitive_truth_assumptions : PrimitiveTruthAssumptions",
                "",
                "def primitive_truth_kernel : ConcreteTruthConditionKernel := {",
                "  kernel_denotes := primitive_truth_assumptions.primitive_denotes,",
            ]
        )
        kernel_fields: list[tuple[str, str]] = []
        for name in sorted(declarations["functions"]):
            kernel_fields.append(
                (
                    concrete_kernel_application_field(name),
                    f"primitive_truth_assumptions.{primitive_truth_application_field(name)}",
                )
            )
        for type_name in declarations["types"]:
            kernel_fields.append(
                (
                    concrete_kernel_sigma_field(type_name),
                    f"primitive_truth_assumptions.{primitive_truth_sigma_field(type_name)}",
                )
            )
        kernel_fields.extend(
            [
                ("repetition_truth", "primitive_truth_assumptions.primitive_repetition_truth"),
                ("temporal_truth_at_T", "primitive_truth_assumptions.primitive_temporal_truth_at_T"),
                ("temporal_truth_during_T", "primitive_truth_assumptions.primitive_temporal_truth_during_T"),
                ("temporal_truth_before_T", "primitive_truth_assumptions.primitive_temporal_truth_before_T"),
                ("temporal_truth_after_T", "primitive_truth_assumptions.primitive_temporal_truth_after_T"),
                ("temporal_truth_until_T", "primitive_truth_assumptions.primitive_temporal_truth_until_T"),
                ("temporal_truth_since_T", "primitive_truth_assumptions.primitive_temporal_truth_since_T"),
                ("polarity_truth_not_T", "primitive_truth_assumptions.primitive_polarity_truth_not_T"),
                ("transition_truth", "primitive_truth_assumptions.primitive_transition_truth"),
                ("cause_truth", "primitive_truth_assumptions.primitive_cause_truth"),
            ]
        )
        for index, (field, value) in enumerate(kernel_fields):
            suffix = "," if index < len(kernel_fields) - 1 else ""
            lines.append(f"  {field} := {value}{suffix}")
        lines.extend(
            [
                "}",
                "",
                "def primitive_truth_conditions_from_kernel : TruthConditionSpec :=",
                "  truth_conditions_from_concrete_kernel primitive_truth_kernel",
                "",
                "theorem primitive_truth_kernel_exists :",
                "    Exists (fun K : ConcreteTruthConditionKernel => "
                "K = primitive_truth_kernel) := by",
                "  exact Exists.intro primitive_truth_kernel rfl",
                "",
                "theorem primitive_truth_kernel_denotes_primitive_assumptions :",
                "    (A : Type) -> (term : A) -> "
                "primitive_truth_assumptions.primitive_denotes A term -> "
                "(truth_conditions_from_concrete_kernel "
                "primitive_truth_kernel).truth_denotes A term := by",
                "  intro A term h",
                "  exact h",
                "",
                "theorem primitive_truth_kernel_denotes_model_interpretable :",
                "    (A : Type) -> (term : A) -> ModelInterpretable A term -> "
                "(truth_conditions_from_concrete_kernel "
                "primitive_truth_kernel).truth_denotes A term := by",
                "  intro A term h",
                "  apply concrete_kernel_induces_truth_condition_soundness",
                "  exact h",
            ]
        )
        return lines

    lines = [
        "Record PrimitiveTruthAssumptions : Type := {",
        "  primitive_denotes : forall A : Type, A -> Prop;",
    ]
    for name, (arg_types, result_type) in sorted(declarations["functions"].items()):
        lines.extend(_coq_function_primitive_truth_field(name, arg_types, result_type))
    for type_name in declarations["types"]:
        lines.extend(
            [
                f"  {primitive_truth_sigma_field(type_name)} : "
                f"forall P : {type_name} -> Prop,",
                f"      (forall x : {type_name}, primitive_denotes Prop (P x)) ->",
                f"      primitive_denotes Prop (exists x : {type_name}, P x);",
            ]
        )
    lines.extend(
        [
            "  primitive_repetition_truth : forall n : nat, forall body : PropT,",
            "      primitive_denotes PropT body ->",
            "      primitive_denotes PropT (repeat n body);",
            "  primitive_temporal_truth_at_T : forall marker : Entity, forall body : PropT,",
            "      primitive_denotes PropT body ->",
            "      primitive_denotes PropT (at_T marker body);",
            "  primitive_temporal_truth_during_T : forall marker : Entity, forall body : PropT,",
            "      primitive_denotes PropT body ->",
            "      primitive_denotes PropT (during_T marker body);",
            "  primitive_temporal_truth_before_T : forall marker : Entity, forall body : PropT,",
            "      primitive_denotes PropT body ->",
            "      primitive_denotes PropT (before_T marker body);",
            "  primitive_temporal_truth_after_T : forall marker : Entity, forall body : PropT,",
            "      primitive_denotes PropT body ->",
            "      primitive_denotes PropT (after_T marker body);",
            "  primitive_temporal_truth_until_T : forall marker : Entity, forall body : PropT,",
            "      primitive_denotes PropT body ->",
            "      primitive_denotes PropT (until_T marker body);",
            "  primitive_temporal_truth_since_T : forall marker : Entity, forall body : PropT,",
            "      primitive_denotes PropT body ->",
            "      primitive_denotes PropT (since_T marker body);",
            "  primitive_polarity_truth_not_T : forall body : PropT,",
            "      primitive_denotes PropT body ->",
            "      primitive_denotes PropT (not_T body);",
            "  primitive_transition_truth : "
            "forall theme : Entity, forall scale : StateScale, "
            "forall source : State, forall target : State,",
            "      primitive_denotes TransitionT "
            "(Transition theme scale source target);",
            "  primitive_cause_truth : "
            "forall causer : Entity, forall effect : TransitionT,",
            "      primitive_denotes TransitionT effect ->",
            "      primitive_denotes PropT (Cause causer effect)",
            "}.",
            "",
            "Parameter primitive_truth_assumptions : PrimitiveTruthAssumptions.",
            "",
            "Definition primitive_truth_kernel : ConcreteTruthConditionKernel := {|",
            "  kernel_denotes := primitive_denotes primitive_truth_assumptions;",
        ]
    )
    kernel_fields: list[tuple[str, str]] = []
    for name in sorted(declarations["functions"]):
        kernel_fields.append(
            (
                concrete_kernel_application_field(name),
                f"{primitive_truth_application_field(name)} primitive_truth_assumptions",
            )
        )
    for type_name in declarations["types"]:
        kernel_fields.append(
            (
                concrete_kernel_sigma_field(type_name),
                f"{primitive_truth_sigma_field(type_name)} primitive_truth_assumptions",
            )
        )
    kernel_fields.extend(
        [
            ("repetition_truth", "primitive_repetition_truth primitive_truth_assumptions"),
            ("temporal_truth_at_T", "primitive_temporal_truth_at_T primitive_truth_assumptions"),
            ("temporal_truth_during_T", "primitive_temporal_truth_during_T primitive_truth_assumptions"),
            ("temporal_truth_before_T", "primitive_temporal_truth_before_T primitive_truth_assumptions"),
            ("temporal_truth_after_T", "primitive_temporal_truth_after_T primitive_truth_assumptions"),
            ("temporal_truth_until_T", "primitive_temporal_truth_until_T primitive_truth_assumptions"),
            ("temporal_truth_since_T", "primitive_temporal_truth_since_T primitive_truth_assumptions"),
            ("polarity_truth_not_T", "primitive_polarity_truth_not_T primitive_truth_assumptions"),
            ("transition_truth", "primitive_transition_truth primitive_truth_assumptions"),
            ("cause_truth", "primitive_cause_truth primitive_truth_assumptions"),
        ]
    )
    for index, (field, value) in enumerate(kernel_fields):
        suffix = ";" if index < len(kernel_fields) - 1 else ""
        lines.append(f"  {field} := {value}{suffix}")
    lines.extend(
        [
            "|}.",
            "",
            "Definition primitive_truth_conditions_from_kernel : TruthConditionSpec :=",
            "  truth_conditions_from_concrete_kernel primitive_truth_kernel.",
            "",
            "Theorem primitive_truth_kernel_exists :",
            "  exists K : ConcreteTruthConditionKernel,",
            "    K = primitive_truth_kernel.",
            "Proof.",
            "  exists primitive_truth_kernel. reflexivity.",
            "Qed.",
            "",
            "Theorem primitive_truth_kernel_denotes_primitive_assumptions :",
            "  forall A : Type, forall term : A,",
            "    primitive_denotes primitive_truth_assumptions A term ->",
            "    truth_denotes (truth_conditions_from_concrete_kernel",
            "      primitive_truth_kernel) A term.",
            "Proof.",
            "  intros A term H.",
            "  exact H.",
            "Qed.",
            "",
            "Theorem primitive_truth_kernel_denotes_model_interpretable :",
            "  forall A : Type, forall term : A,",
            "    ModelInterpretable A term ->",
            "    truth_denotes (truth_conditions_from_concrete_kernel",
            "      primitive_truth_kernel) A term.",
            "Proof.",
            "  intros A term H.",
            "  apply concrete_kernel_induces_truth_condition_soundness.",
            "  exact H.",
            "Qed.",
        ]
    )
    return lines


def atomic_closure_truth_kernel_lines(
    declarations: dict[str, Any],
    target: str,
) -> list[str]:
    if target == "lean":
        lines = [
            "inductive AtomicBaseTruth : (A : Type) -> A -> Prop where",
        ]
        for name, (arg_types, result_type) in sorted(declarations["functions"].items()):
            lines.append(
                _lean_function_atomic_base_constructor(name, arg_types, result_type)
            )
        lines.extend(
            [
                "  | atomic_base_truth_transition : (theme : Entity) -> "
                "(scale : StateScale) -> (source : State) -> (target : State) -> "
                "AtomicBaseTruth TransitionT (Transition theme scale source target)",
                "",
                "structure LexicalAtomTruthAssumptions "
                "(D : (A : Type) -> A -> Prop) : Type where",
            ]
        )
        for name, (arg_types, result_type) in sorted(declarations["functions"].items()):
            lines.append(
                _lean_function_lexical_atom_truth_assumption_field(
                    name, arg_types, result_type
                )
            )
        lines.extend(
            [
                "",
                "structure TransitionAtomTruthAssumptions "
                "(D : (A : Type) -> A -> Prop) : Type where",
                "  transition_atom_truth : (theme : Entity) -> "
                "(scale : StateScale) -> (source : State) -> (target : State) -> "
                "D TransitionT (Transition theme scale source target)",
                "",
                "structure LexicalTransitionTruthAssumptions : Type where",
                "  atom_assumption_denotes : (A : Type) -> A -> Prop",
                "  lexical_atom_assumptions : "
                "LexicalAtomTruthAssumptions atom_assumption_denotes",
                "  transition_atom_assumptions : "
                "TransitionAtomTruthAssumptions atom_assumption_denotes",
                "",
                "def lexical_atom_truth_assumptions_from_atomic_base : "
                "LexicalAtomTruthAssumptions AtomicBaseTruth := {",
            ]
        )
        lexical_assumption_fields: list[tuple[str, str]] = []
        for name, (arg_types, _result_type) in sorted(declarations["functions"].items()):
            remaining_arg_types = (
                arg_types[2:]
                if arg_types[:2] == ["(n : Nat)", "ModifierSeq n"]
                else arg_types
            )
            ordinary_args = [
                f"arg{index}"
                for index, _arg_type in enumerate(remaining_arg_types, 1)
            ]
            binders = " ".join(["n", "mods", *ordinary_args])
            constructor_args = " ".join(["n", "mods", *ordinary_args])
            lexical_assumption_fields.append(
                (
                    lexical_atom_truth_application_field(name),
                    (
                        f"fun {binders} => "
                        f"AtomicBaseTruth.{atomic_base_truth_application_constructor(name)} "
                        f"{constructor_args}"
                    ),
                )
            )
        for index, (field, value) in enumerate(lexical_assumption_fields):
            suffix = "," if index < len(lexical_assumption_fields) - 1 else ""
            lines.append(f"  {field} := {value}{suffix}")
        lines.extend(
            [
                "}",
                "",
                "def transition_atom_truth_assumptions_from_atomic_base : "
                "TransitionAtomTruthAssumptions AtomicBaseTruth := {",
                "  transition_atom_truth := fun theme scale source target => "
                "AtomicBaseTruth.atomic_base_truth_transition theme scale source target",
                "}",
                "",
                "def lexical_transition_truth_assumptions_from_atomic_base : "
                "LexicalTransitionTruthAssumptions := {",
                "  atom_assumption_denotes := AtomicBaseTruth,",
                "  lexical_atom_assumptions := "
                "lexical_atom_truth_assumptions_from_atomic_base,",
                "  transition_atom_assumptions := "
                "transition_atom_truth_assumptions_from_atomic_base",
                "}",
                "",
                "theorem lexical_atom_truth_assumptions_from_atomic_base_exists :",
                "    Exists (fun L : LexicalAtomTruthAssumptions AtomicBaseTruth => "
                "L = lexical_atom_truth_assumptions_from_atomic_base) := by",
                "  exact Exists.intro lexical_atom_truth_assumptions_from_atomic_base rfl",
                "",
                "theorem transition_atom_truth_assumptions_from_atomic_base_exists :",
                "    Exists (fun T : TransitionAtomTruthAssumptions AtomicBaseTruth => "
                "T = transition_atom_truth_assumptions_from_atomic_base) := by",
                "  exact Exists.intro transition_atom_truth_assumptions_from_atomic_base rfl",
                "",
                "theorem lexical_transition_truth_assumptions_from_atomic_base_exists :",
                "    Exists (fun A : LexicalTransitionTruthAssumptions => "
                "A = lexical_transition_truth_assumptions_from_atomic_base) := by",
                "  exact Exists.intro lexical_transition_truth_assumptions_from_atomic_base rfl",
                "",
                "structure LexicalTransitionTruthModel : Type where",
                "  atom_model_denotes : (A : Type) -> A -> Prop",
            ]
        )
        for name, (arg_types, result_type) in sorted(declarations["functions"].items()):
            lines.append(
                _lean_function_lexical_transition_model_field(
                    name, arg_types, result_type
                )
            )
        lines.extend(
            [
                "  model_transition_truth : (theme : Entity) -> "
                "(scale : StateScale) -> (source : State) -> (target : State) -> "
                "atom_model_denotes TransitionT "
                "(Transition theme scale source target)",
                "",
                "def lexical_transition_truth_model_from_assumptions "
                "(assumptions : LexicalTransitionTruthAssumptions) : "
                "LexicalTransitionTruthModel := {",
                "  atom_model_denotes := assumptions.atom_assumption_denotes,",
            ]
        )
        model_fields: list[tuple[str, str]] = []
        for name in sorted(declarations["functions"]):
            model_fields.append(
                (
                    lexical_transition_model_application_field(name),
                    (
                        "assumptions.lexical_atom_assumptions."
                        f"{lexical_atom_truth_application_field(name)}"
                    ),
                )
            )
        model_fields.append(
            (
                "model_transition_truth",
                "assumptions.transition_atom_assumptions.transition_atom_truth",
            )
        )
        for index, (field, value) in enumerate(model_fields):
            suffix = "," if index < len(model_fields) - 1 else ""
            lines.append(f"  {field} := {value}{suffix}")
        lines.extend(
            [
                "}",
                "",
                "def lexical_transition_truth_model : LexicalTransitionTruthModel :=",
                "  lexical_transition_truth_model_from_assumptions "
                "lexical_transition_truth_assumptions_from_atomic_base",
                "",
                "theorem lexical_transition_truth_model_from_assumptions_exists :",
                "    Exists (fun M : LexicalTransitionTruthModel => "
                "M = lexical_transition_truth_model_from_assumptions "
                "lexical_transition_truth_assumptions_from_atomic_base) := by",
                "  exact Exists.intro "
                "(lexical_transition_truth_model_from_assumptions "
                "lexical_transition_truth_assumptions_from_atomic_base) rfl",
                "",
                "theorem lexical_transition_truth_model_exists :",
                "    Exists (fun M : LexicalTransitionTruthModel => "
                "M = lexical_transition_truth_model) := by",
                "  exact Exists.intro lexical_transition_truth_model rfl",
                "",
                "theorem lexical_transition_truth_model_denotes_atomic_base_truth :",
                "    (A : Type) -> (term : A) -> AtomicBaseTruth A term -> "
                "lexical_transition_truth_model.atom_model_denotes A term := by",
                "  intro A term h",
                "  exact h",
                "",
                "structure AtomicValuationSpec : Type where",
                "  atomic_valuation_denotes : (A : Type) -> A -> Prop",
            ]
        )
        for name, (arg_types, result_type) in sorted(declarations["functions"].items()):
            lines.append(
                _lean_function_atomic_valuation_field(name, arg_types, result_type)
            )
        lines.extend(
            [
                "  valuation_transition_truth : (theme : Entity) -> "
                "(scale : StateScale) -> (source : State) -> (target : State) -> "
                "atomic_valuation_denotes TransitionT "
                "(Transition theme scale source target)",
                "",
                "def atomic_valuation_spec_from_lexical_transition_model : "
                "AtomicValuationSpec := {",
                "  atomic_valuation_denotes := "
                "lexical_transition_truth_model.atom_model_denotes,",
            ]
        )
        valuation_fields: list[tuple[str, str]] = []
        for name in sorted(declarations["functions"]):
            valuation_fields.append(
                (
                    atomic_valuation_application_field(name),
                    (
                        "lexical_transition_truth_model."
                        f"{lexical_transition_model_application_field(name)}"
                    ),
                )
            )
        valuation_fields.append(
            (
                "valuation_transition_truth",
                "lexical_transition_truth_model.model_transition_truth",
            )
        )
        for index, (field, value) in enumerate(valuation_fields):
            suffix = "," if index < len(valuation_fields) - 1 else ""
            lines.append(f"  {field} := {value}{suffix}")
        lines.extend(
            [
                "}",
                "",
                "def atomic_base_valuation_spec : AtomicValuationSpec :=",
                "  atomic_valuation_spec_from_lexical_transition_model",
                "",
                "theorem atomic_valuation_spec_from_lexical_transition_model_exists :",
                "    Exists (fun V : AtomicValuationSpec => "
                "V = atomic_valuation_spec_from_lexical_transition_model) := by",
                "  exact Exists.intro atomic_valuation_spec_from_lexical_transition_model rfl",
            ]
        )
        lines.extend(
            [
                "",
                "theorem atomic_base_valuation_spec_exists :",
                "    Exists (fun V : AtomicValuationSpec => "
                "V = atomic_base_valuation_spec) := by",
                "  exact Exists.intro atomic_base_valuation_spec rfl",
                "",
                "theorem atomic_base_valuation_denotes_atomic_base_truth :",
                "    (A : Type) -> (term : A) -> AtomicBaseTruth A term -> "
                "atomic_base_valuation_spec.atomic_valuation_denotes A term := by",
                "  intro A term h",
                "  exact h",
                "",
                "structure AtomicTruthFacts : Type where",
            ]
        )
        for name, (arg_types, result_type) in sorted(declarations["functions"].items()):
            lines.append(_lean_function_atomic_truth_field(name, arg_types, result_type))
        lines.extend(
            [
                "  atomic_transition_truth : (theme : Entity) -> "
                "(scale : StateScale) -> (source : State) -> (target : State) -> "
                "AtomicBaseTruth TransitionT (Transition theme scale source target)",
                "",
                "def atomic_truth_facts_from_atomic_base_valuation : AtomicTruthFacts := {",
            ]
        )
        atomic_fact_fields: list[tuple[str, str]] = []
        for name, (arg_types, _result_type) in sorted(declarations["functions"].items()):
            remaining_arg_types = (
                arg_types[2:]
                if arg_types[:2] == ["(n : Nat)", "ModifierSeq n"]
                else arg_types
            )
            ordinary_args = [
                f"arg{index}"
                for index, _arg_type in enumerate(remaining_arg_types, 1)
            ]
            binders = " ".join(["n", "mods", *ordinary_args])
            constructor_args = " ".join(["n", "mods", *ordinary_args])
            atomic_fact_fields.append(
                (
                    atomic_truth_application_field(name),
                    (
                        f"fun {binders} => "
                        f"atomic_base_valuation_spec.{atomic_valuation_application_field(name)} "
                        f"{constructor_args}"
                    ),
                )
            )
        atomic_fact_fields.append(
            (
                "atomic_transition_truth",
                "fun theme scale source target => "
                "atomic_base_valuation_spec.valuation_transition_truth theme scale source target",
            )
        )
        for index, (field, value) in enumerate(atomic_fact_fields):
            suffix = "," if index < len(atomic_fact_fields) - 1 else ""
            lines.append(f"  {field} := {value}{suffix}")
        lines.extend(
            [
                "}",
                "",
                "def atomic_truth_facts : AtomicTruthFacts :=",
                "  atomic_truth_facts_from_atomic_base_valuation",
                "",
                "theorem atomic_truth_facts_from_atomic_base_valuation_exists :",
                "    Exists (fun F : AtomicTruthFacts => "
                "F = atomic_truth_facts_from_atomic_base_valuation) := by",
                "  exact Exists.intro atomic_truth_facts_from_atomic_base_valuation rfl",
            "",
                "inductive AtomicClosureTruth : (A : Type) -> A -> Prop where",
            ]
        )
        for name, (arg_types, result_type) in sorted(declarations["functions"].items()):
            lines.append(
                _lean_function_atomic_closure_constructor(name, arg_types, result_type)
            )
        for type_name in declarations["types"]:
            lines.append(
                f"  | {atomic_closure_sigma_constructor(type_name)} : "
                f"(P : {type_name} -> Prop) -> "
                f"((x : {type_name}) -> AtomicClosureTruth Prop (P x)) -> "
                f"AtomicClosureTruth Prop (Exists fun x : {type_name} => P x)"
            )
        lines.extend(
            [
                "  | atomic_closure_truth_repeat : (n : Nat) -> (body : PropT) -> "
                "AtomicClosureTruth PropT body -> AtomicClosureTruth PropT (repeat n body)",
                "  | atomic_closure_truth_at_T : (marker : Entity) -> (body : PropT) -> "
                "AtomicClosureTruth PropT body -> AtomicClosureTruth PropT (at_T marker body)",
                "  | atomic_closure_truth_during_T : (marker : Entity) -> (body : PropT) -> "
                "AtomicClosureTruth PropT body -> AtomicClosureTruth PropT (during_T marker body)",
                "  | atomic_closure_truth_before_T : (marker : Entity) -> (body : PropT) -> "
                "AtomicClosureTruth PropT body -> AtomicClosureTruth PropT (before_T marker body)",
                "  | atomic_closure_truth_after_T : (marker : Entity) -> (body : PropT) -> "
                "AtomicClosureTruth PropT body -> AtomicClosureTruth PropT (after_T marker body)",
                "  | atomic_closure_truth_until_T : (marker : Entity) -> (body : PropT) -> "
                "AtomicClosureTruth PropT body -> AtomicClosureTruth PropT (until_T marker body)",
                "  | atomic_closure_truth_since_T : (marker : Entity) -> (body : PropT) -> "
                "AtomicClosureTruth PropT body -> AtomicClosureTruth PropT (since_T marker body)",
                "  | atomic_closure_truth_not_T : (body : PropT) -> "
                "AtomicClosureTruth PropT body -> AtomicClosureTruth PropT (not_T body)",
                "  | atomic_closure_truth_transition : (theme : Entity) -> "
                "(scale : StateScale) -> (source : State) -> (target : State) -> "
                "AtomicBaseTruth TransitionT (Transition theme scale source target) -> "
                "AtomicClosureTruth TransitionT (Transition theme scale source target)",
                "  | atomic_closure_truth_cause : (causer : Entity) -> (effect : TransitionT) -> "
                "AtomicClosureTruth TransitionT effect -> AtomicClosureTruth PropT (Cause causer effect)",
                "",
                "theorem model_interpretable_atomic_closure_truth :",
                "    (A : Type) -> (term : A) -> ModelInterpretable A term -> "
                "AtomicClosureTruth A term := by",
                "  intro A term h",
                "  induction h",
            ]
        )
        for name, (arg_types, _result_type) in sorted(declarations["functions"].items()):
            constructor = model_application_constructor(name)
            atomic_constructor = atomic_closure_application_constructor(name)
            remaining_arg_types = (
                arg_types[2:]
                if arg_types[:2] == ["(n : Nat)", "ModifierSeq n"]
                else arg_types
            )
            ordinary_args = [
                f"arg{index}"
                for index, _arg_type in enumerate(remaining_arg_types, 1)
            ]
            pattern_args = " ".join(["n", "mods", *ordinary_args])
            lines.append(f"  | {constructor} {pattern_args} =>")
            lines.append(f"      apply AtomicClosureTruth.{atomic_constructor}")
            lines.append(
                f"      exact atomic_truth_facts.{atomic_truth_application_field(name)} "
                f"{pattern_args}"
            )
        for type_name in declarations["types"]:
            lines.append(
                f"  | {model_sigma_constructor(type_name)} P h ih => "
                f"exact AtomicClosureTruth.{atomic_closure_sigma_constructor(type_name)} P ih"
            )
        lines.extend(
            [
                "  | model_repeat n body h ih => exact AtomicClosureTruth.atomic_closure_truth_repeat n body ih",
                "  | model_at_T marker body h ih => exact AtomicClosureTruth.atomic_closure_truth_at_T marker body ih",
                "  | model_during_T marker body h ih => exact AtomicClosureTruth.atomic_closure_truth_during_T marker body ih",
                "  | model_before_T marker body h ih => exact AtomicClosureTruth.atomic_closure_truth_before_T marker body ih",
                "  | model_after_T marker body h ih => exact AtomicClosureTruth.atomic_closure_truth_after_T marker body ih",
                "  | model_until_T marker body h ih => exact AtomicClosureTruth.atomic_closure_truth_until_T marker body ih",
                "  | model_since_T marker body h ih => exact AtomicClosureTruth.atomic_closure_truth_since_T marker body ih",
                "  | model_not_T body h ih => exact AtomicClosureTruth.atomic_closure_truth_not_T body ih",
                "  | model_transition theme scale source target =>",
                "      apply AtomicClosureTruth.atomic_closure_truth_transition",
                "      exact atomic_truth_facts.atomic_transition_truth theme scale source target",
                "  | model_cause causer effect h ih => exact AtomicClosureTruth.atomic_closure_truth_cause causer effect ih",
                "",
                "def atomic_closure_truth_kernel_denotes : (A : Type) -> A -> Prop :=",
                "  AtomicClosureTruth",
                "",
                "def atomic_closure_truth_kernel : ConcreteTruthConditionKernel := {",
                "  kernel_denotes := atomic_closure_truth_kernel_denotes,",
            ]
        )
        kernel_fields: list[tuple[str, str]] = []
        for name, (arg_types, _result_type) in sorted(declarations["functions"].items()):
            remaining_arg_types = (
                arg_types[2:]
                if arg_types[:2] == ["(n : Nat)", "ModifierSeq n"]
                else arg_types
            )
            ordinary_args = [
                f"arg{index}"
                for index, _arg_type in enumerate(remaining_arg_types, 1)
            ]
            binders = " ".join(["n", "mods", *ordinary_args])
            constructor_args = " ".join(["n", "mods", *ordinary_args])
            kernel_fields.append(
                (
                    concrete_kernel_application_field(name),
                    (
                        f"fun {binders} => "
                        f"AtomicClosureTruth.{atomic_closure_application_constructor(name)} "
                        f"{constructor_args} "
                        f"(atomic_truth_facts.{atomic_truth_application_field(name)} "
                        f"{constructor_args})"
                    ),
                )
            )
        for type_name in declarations["types"]:
            kernel_fields.append(
                (
                    concrete_kernel_sigma_field(type_name),
                    f"fun P h => AtomicClosureTruth.{atomic_closure_sigma_constructor(type_name)} P h",
                )
            )
        kernel_fields.extend(
            [
                ("repetition_truth", "fun n body h => AtomicClosureTruth.atomic_closure_truth_repeat n body h"),
                ("temporal_truth_at_T", "fun marker body h => AtomicClosureTruth.atomic_closure_truth_at_T marker body h"),
                ("temporal_truth_during_T", "fun marker body h => AtomicClosureTruth.atomic_closure_truth_during_T marker body h"),
                ("temporal_truth_before_T", "fun marker body h => AtomicClosureTruth.atomic_closure_truth_before_T marker body h"),
                ("temporal_truth_after_T", "fun marker body h => AtomicClosureTruth.atomic_closure_truth_after_T marker body h"),
                ("temporal_truth_until_T", "fun marker body h => AtomicClosureTruth.atomic_closure_truth_until_T marker body h"),
                ("temporal_truth_since_T", "fun marker body h => AtomicClosureTruth.atomic_closure_truth_since_T marker body h"),
                ("polarity_truth_not_T", "fun body h => AtomicClosureTruth.atomic_closure_truth_not_T body h"),
                (
                    "transition_truth",
                    "fun theme scale source target => "
                    "AtomicClosureTruth.atomic_closure_truth_transition theme scale source target "
                    "(atomic_truth_facts.atomic_transition_truth theme scale source target)",
                ),
                ("cause_truth", "fun causer effect h => AtomicClosureTruth.atomic_closure_truth_cause causer effect h"),
            ]
        )
        for index, (field, value) in enumerate(kernel_fields):
            suffix = "," if index < len(kernel_fields) - 1 else ""
            lines.append(f"  {field} := {value}{suffix}")
        lines.extend(
            [
                "}",
                "",
                "def atomic_closure_truth_conditions_from_kernel : TruthConditionSpec :=",
                "  truth_conditions_from_concrete_kernel atomic_closure_truth_kernel",
                "",
                "theorem atomic_closure_truth_kernel_exists :",
                "    Exists (fun K : ConcreteTruthConditionKernel => "
                "K = atomic_closure_truth_kernel) := by",
                "  exact Exists.intro atomic_closure_truth_kernel rfl",
                "",
                "theorem atomic_closure_truth_kernel_denotes_atomic_closure_truth :",
                "    (A : Type) -> (term : A) -> AtomicClosureTruth A term -> "
                "(truth_conditions_from_concrete_kernel "
                "atomic_closure_truth_kernel).truth_denotes A term := by",
                "  intro A term h",
                "  exact h",
                "",
                "def atomic_closure_truth_conditions : TruthConditionSpec :=",
                "  atomic_closure_truth_conditions_from_kernel",
                "",
                "theorem atomic_closure_truth_conditions_exists :",
                "    Exists (fun T : TruthConditionSpec => "
                "T = atomic_closure_truth_conditions) := by",
                "  exact Exists.intro atomic_closure_truth_conditions rfl",
                "",
                "theorem atomic_closure_truth_conditions_denote_atomic_closure_truth :",
                "    (A : Type) -> (term : A) -> AtomicClosureTruth A term -> "
                "atomic_closure_truth_conditions.truth_denotes A term := by",
                "  intro A term h",
                "  exact h",
            ]
        )
        return lines

    lines = [
        "Inductive AtomicBaseTruth : forall A : Type, A -> Prop :=",
    ]
    atomic_base_constructors: list[str] = []
    for name, (arg_types, result_type) in sorted(declarations["functions"].items()):
        atomic_base_constructors.extend(
            _coq_function_atomic_base_constructor(name, arg_types, result_type)
        )
    atomic_base_constructors.extend(
        [
            "  | atomic_base_truth_transition : "
            "forall theme : Entity, forall scale : StateScale, "
            "forall source : State, forall target : State,",
            "      AtomicBaseTruth TransitionT "
            "(Transition theme scale source target)",
        ]
    )
    if not atomic_base_constructors:
        raise ValueError("Cannot emit an empty AtomicBaseTruth relation")
    atomic_base_constructors[-1] += "."
    lines.extend(atomic_base_constructors)
    lines.extend(
        [
            "",
            "Record LexicalAtomTruthAssumptions "
            "(D : forall A : Type, A -> Prop) : Type := {",
        ]
    )
    for name, (arg_types, result_type) in sorted(declarations["functions"].items()):
        lines.extend(
            _coq_function_lexical_atom_truth_assumption_field(
                name, arg_types, result_type
            )
        )
    lines.extend(
        [
            "}.",
            "",
            "Record TransitionAtomTruthAssumptions "
            "(D : forall A : Type, A -> Prop) : Type := {",
            "  transition_atom_truth : "
            "forall theme : Entity, forall scale : StateScale, "
            "forall source : State, forall target : State,",
            "      D TransitionT (Transition theme scale source target)",
            "}.",
            "",
            "Record LexicalTransitionTruthAssumptions : Type := {",
            "  atom_assumption_denotes : forall A : Type, A -> Prop;",
            "  lexical_atom_assumptions : "
            "LexicalAtomTruthAssumptions atom_assumption_denotes;",
            "  transition_atom_assumptions : "
            "TransitionAtomTruthAssumptions atom_assumption_denotes",
            "}.",
            "",
            "Definition lexical_atom_truth_assumptions_from_atomic_base :",
            "  LexicalAtomTruthAssumptions AtomicBaseTruth := {|",
        ]
    )
    lexical_assumption_fields = []
    for name, (arg_types, _result_type) in sorted(declarations["functions"].items()):
        remaining_arg_types = arg_types[1:] if arg_types else []
        ordinary_args = [
            f"arg{index}"
            for index, _arg_type in enumerate(remaining_arg_types, 1)
        ]
        binders = " ".join(["n", "mods", *ordinary_args])
        constructor_args = " ".join(["n", "mods", *ordinary_args])
        lexical_assumption_fields.append(
            (
                lexical_atom_truth_application_field(name),
                (
                    f"fun {binders} => "
                    f"{atomic_base_truth_application_constructor(name)} "
                    f"{constructor_args}"
                ),
            )
        )
    for index, (field, value) in enumerate(lexical_assumption_fields):
        suffix = ";" if index < len(lexical_assumption_fields) - 1 else ""
        lines.append(f"  {field} := {value}{suffix}")
    lines.extend(
        [
            "|}.",
            "",
            "Definition transition_atom_truth_assumptions_from_atomic_base :",
            "  TransitionAtomTruthAssumptions AtomicBaseTruth := {|",
            "  transition_atom_truth := fun theme scale source target =>",
            "    atomic_base_truth_transition theme scale source target",
            "|}.",
            "",
            "Definition lexical_transition_truth_assumptions_from_atomic_base :",
            "  LexicalTransitionTruthAssumptions := {|",
            "  atom_assumption_denotes := AtomicBaseTruth;",
            "  lexical_atom_assumptions := "
            "lexical_atom_truth_assumptions_from_atomic_base;",
            "  transition_atom_assumptions := "
            "transition_atom_truth_assumptions_from_atomic_base",
            "|}.",
            "",
            "Theorem lexical_atom_truth_assumptions_from_atomic_base_exists :",
            "  exists L : LexicalAtomTruthAssumptions AtomicBaseTruth,",
            "    L = lexical_atom_truth_assumptions_from_atomic_base.",
            "Proof.",
            "  exists lexical_atom_truth_assumptions_from_atomic_base. reflexivity.",
            "Qed.",
            "",
            "Theorem transition_atom_truth_assumptions_from_atomic_base_exists :",
            "  exists T : TransitionAtomTruthAssumptions AtomicBaseTruth,",
            "    T = transition_atom_truth_assumptions_from_atomic_base.",
            "Proof.",
            "  exists transition_atom_truth_assumptions_from_atomic_base. reflexivity.",
            "Qed.",
            "",
            "Theorem lexical_transition_truth_assumptions_from_atomic_base_exists :",
            "  exists A : LexicalTransitionTruthAssumptions,",
            "    A = lexical_transition_truth_assumptions_from_atomic_base.",
            "Proof.",
            "  exists lexical_transition_truth_assumptions_from_atomic_base.",
            "  reflexivity.",
            "Qed.",
            "",
            "Record LexicalTransitionTruthModel : Type := {",
            "  atom_model_denotes : forall A : Type, A -> Prop;",
        ]
    )
    for name, (arg_types, result_type) in sorted(declarations["functions"].items()):
        lines.extend(
            _coq_function_lexical_transition_model_field(
                name, arg_types, result_type
            )
        )
    lines.extend(
        [
            "  model_transition_truth : "
            "forall theme : Entity, forall scale : StateScale, "
            "forall source : State, forall target : State,",
            "      atom_model_denotes TransitionT "
            "(Transition theme scale source target)",
            "}.",
            "",
            "Definition lexical_transition_truth_model_from_assumptions",
            "  (assumptions : LexicalTransitionTruthAssumptions) :",
            "  LexicalTransitionTruthModel := {|",
            "  atom_model_denotes := atom_assumption_denotes assumptions;",
        ]
    )
    model_fields = []
    for name in sorted(declarations["functions"]):
        model_fields.append(
            (
                lexical_transition_model_application_field(name),
                (
                    f"@{lexical_atom_truth_application_field(name)} "
                    "(atom_assumption_denotes assumptions) "
                    "(lexical_atom_assumptions assumptions)"
                ),
            )
        )
    model_fields.append(
        (
            "model_transition_truth",
            "@transition_atom_truth (atom_assumption_denotes assumptions) "
            "(transition_atom_assumptions assumptions)",
        )
    )
    for index, (field, value) in enumerate(model_fields):
        suffix = ";" if index < len(model_fields) - 1 else ""
        lines.append(f"  {field} := {value}{suffix}")
    lines.extend(
        [
            "|}.",
            "",
            "Definition lexical_transition_truth_model : LexicalTransitionTruthModel :=",
            "  lexical_transition_truth_model_from_assumptions",
            "    lexical_transition_truth_assumptions_from_atomic_base.",
            "",
            "Theorem lexical_transition_truth_model_from_assumptions_exists :",
            "  exists M : LexicalTransitionTruthModel,",
            "    M = lexical_transition_truth_model_from_assumptions",
            "      lexical_transition_truth_assumptions_from_atomic_base.",
            "Proof.",
            "  exists (lexical_transition_truth_model_from_assumptions",
            "    lexical_transition_truth_assumptions_from_atomic_base).",
            "  reflexivity.",
            "Qed.",
            "",
            "Theorem lexical_transition_truth_model_exists :",
            "  exists M : LexicalTransitionTruthModel,",
            "    M = lexical_transition_truth_model.",
            "Proof.",
            "  exists lexical_transition_truth_model. reflexivity.",
            "Qed.",
            "",
            "Theorem lexical_transition_truth_model_denotes_atomic_base_truth :",
            "  forall A : Type, forall term : A,",
            "    AtomicBaseTruth A term ->",
            "    atom_model_denotes lexical_transition_truth_model A term.",
            "Proof.",
            "  intros A term H.",
            "  exact H.",
            "Qed.",
            "",
        "Record AtomicValuationSpec : Type := {",
        "  atomic_valuation_denotes : forall A : Type, A -> Prop;",
        ]
    )
    for name, (arg_types, result_type) in sorted(declarations["functions"].items()):
        lines.extend(_coq_function_atomic_valuation_field(name, arg_types, result_type))
    lines.extend(
        [
            "  valuation_transition_truth : "
            "forall theme : Entity, forall scale : StateScale, "
            "forall source : State, forall target : State,",
            "      atomic_valuation_denotes TransitionT "
            "(Transition theme scale source target)",
            "}.",
            "",
            "Definition atomic_valuation_spec_from_lexical_transition_model : "
            "AtomicValuationSpec := {|",
            "  atomic_valuation_denotes := "
            "atom_model_denotes lexical_transition_truth_model;",
        ]
    )
    valuation_fields = []
    for name in sorted(declarations["functions"]):
        valuation_fields.append(
            (
                atomic_valuation_application_field(name),
                f"{lexical_transition_model_application_field(name)} "
                "lexical_transition_truth_model",
            )
        )
    valuation_fields.append(
        (
            "valuation_transition_truth",
            "model_transition_truth lexical_transition_truth_model",
        )
    )
    for index, (field, value) in enumerate(valuation_fields):
        suffix = ";" if index < len(valuation_fields) - 1 else ""
        lines.append(f"  {field} := {value}{suffix}")
    lines.extend(
        [
            "|}.",
            "",
            "Definition atomic_base_valuation_spec : AtomicValuationSpec :=",
            "  atomic_valuation_spec_from_lexical_transition_model.",
            "",
            "Theorem atomic_valuation_spec_from_lexical_transition_model_exists :",
            "  exists V : AtomicValuationSpec,",
            "    V = atomic_valuation_spec_from_lexical_transition_model.",
            "Proof.",
            "  exists atomic_valuation_spec_from_lexical_transition_model.",
            "  reflexivity.",
            "Qed.",
            "",
            "Theorem atomic_base_valuation_spec_exists :",
            "  exists V : AtomicValuationSpec,",
            "    V = atomic_base_valuation_spec.",
            "Proof.",
            "  exists atomic_base_valuation_spec. reflexivity.",
            "Qed.",
            "",
            "Theorem atomic_base_valuation_denotes_atomic_base_truth :",
            "  forall A : Type, forall term : A,",
            "    AtomicBaseTruth A term ->",
            "    atomic_valuation_denotes atomic_base_valuation_spec A term.",
            "Proof.",
            "  intros A term H.",
            "  exact H.",
            "Qed.",
            "",
        "Record AtomicTruthFacts : Type := {",
        ]
    )
    for name, (arg_types, result_type) in sorted(declarations["functions"].items()):
        lines.extend(_coq_function_atomic_truth_field(name, arg_types, result_type))
    lines.extend(
        [
            "  atomic_transition_truth : "
            "forall theme : Entity, forall scale : StateScale, "
            "forall source : State, forall target : State,",
            "      AtomicBaseTruth TransitionT "
            "(Transition theme scale source target)",
            "}.",
            "",
            "Definition atomic_truth_facts_from_atomic_base_valuation : AtomicTruthFacts := {|",
        ]
    )
    atomic_fact_fields = []
    for name, (arg_types, _result_type) in sorted(declarations["functions"].items()):
        remaining_arg_types = arg_types[1:] if arg_types else []
        ordinary_args = [
            f"arg{index}"
            for index, _arg_type in enumerate(remaining_arg_types, 1)
        ]
        binders = " ".join(["n", "mods", *ordinary_args])
        constructor_args = " ".join(["n", "mods", *ordinary_args])
        atomic_fact_fields.append(
            (
                atomic_truth_application_field(name),
                (
                    f"fun {binders} => "
                    f"{atomic_valuation_application_field(name)} atomic_base_valuation_spec "
                    f"{constructor_args}"
                ),
            )
        )
    atomic_fact_fields.append(
            (
                "atomic_transition_truth",
                "fun theme scale source target => "
                "valuation_transition_truth atomic_base_valuation_spec theme scale source target",
            )
        )
    for index, (field, value) in enumerate(atomic_fact_fields):
        suffix = ";" if index < len(atomic_fact_fields) - 1 else ""
        lines.append(f"  {field} := {value}{suffix}")
    lines.extend(
        [
            "|}.",
            "",
            "Definition atomic_truth_facts : AtomicTruthFacts :=",
            "  atomic_truth_facts_from_atomic_base_valuation.",
            "",
            "Theorem atomic_truth_facts_from_atomic_base_valuation_exists :",
            "  exists F : AtomicTruthFacts,",
            "    F = atomic_truth_facts_from_atomic_base_valuation.",
            "Proof.",
            "  exists atomic_truth_facts_from_atomic_base_valuation. reflexivity.",
            "Qed.",
            "",
            "Inductive AtomicClosureTruth : forall A : Type, A -> Prop :=",
        ]
    )
    for name, (arg_types, result_type) in sorted(declarations["functions"].items()):
        lines.extend(_coq_function_atomic_closure_constructor(name, arg_types, result_type))
    for type_name in declarations["types"]:
        lines.extend(
            [
                f"  | {atomic_closure_sigma_constructor(type_name)} : "
                f"forall P : {type_name} -> Prop,",
                f"      (forall x : {type_name}, AtomicClosureTruth Prop (P x)) ->",
                f"      AtomicClosureTruth Prop (exists x : {type_name}, P x)",
            ]
        )
    lines.extend(
        [
            "  | atomic_closure_truth_repeat : forall n : nat, forall body : PropT,",
            "      AtomicClosureTruth PropT body ->",
            "      AtomicClosureTruth PropT (repeat n body)",
            "  | atomic_closure_truth_at_T : forall marker : Entity, forall body : PropT,",
            "      AtomicClosureTruth PropT body ->",
            "      AtomicClosureTruth PropT (at_T marker body)",
            "  | atomic_closure_truth_during_T : forall marker : Entity, forall body : PropT,",
            "      AtomicClosureTruth PropT body ->",
            "      AtomicClosureTruth PropT (during_T marker body)",
            "  | atomic_closure_truth_before_T : forall marker : Entity, forall body : PropT,",
            "      AtomicClosureTruth PropT body ->",
            "      AtomicClosureTruth PropT (before_T marker body)",
            "  | atomic_closure_truth_after_T : forall marker : Entity, forall body : PropT,",
            "      AtomicClosureTruth PropT body ->",
            "      AtomicClosureTruth PropT (after_T marker body)",
            "  | atomic_closure_truth_until_T : forall marker : Entity, forall body : PropT,",
            "      AtomicClosureTruth PropT body ->",
            "      AtomicClosureTruth PropT (until_T marker body)",
            "  | atomic_closure_truth_since_T : forall marker : Entity, forall body : PropT,",
            "      AtomicClosureTruth PropT body ->",
            "      AtomicClosureTruth PropT (since_T marker body)",
            "  | atomic_closure_truth_not_T : forall body : PropT,",
            "      AtomicClosureTruth PropT body ->",
            "      AtomicClosureTruth PropT (not_T body)",
            "  | atomic_closure_truth_transition : "
            "forall theme : Entity, forall scale : StateScale, "
            "forall source : State, forall target : State,",
            "      AtomicBaseTruth TransitionT "
            "(Transition theme scale source target) ->",
            "      AtomicClosureTruth TransitionT "
            "(Transition theme scale source target)",
            "  | atomic_closure_truth_cause : "
            "forall causer : Entity, forall effect : TransitionT,",
            "      AtomicClosureTruth TransitionT effect ->",
            "      AtomicClosureTruth PropT (Cause causer effect).",
            "",
            "Theorem model_interpretable_atomic_closure_truth :",
            "  forall A : Type, forall term : A,",
            "    ModelInterpretable A term -> AtomicClosureTruth A term.",
            "Proof.",
            "  intros A term H.",
        ]
    )
    lines.append("  induction H.")
    for name in sorted(declarations["functions"]):
        lines.append(f"  - apply {atomic_closure_application_constructor(name)}.")
        lines.append(
            f"    apply ({atomic_truth_application_field(name)} atomic_truth_facts)."
        )
    for type_name in declarations["types"]:
        lines.append(f"  - apply {atomic_closure_sigma_constructor(type_name)}.")
        lines.append("    assumption.")
    lines.extend(
        [
            "  - apply atomic_closure_truth_repeat. assumption.",
            "  - apply atomic_closure_truth_at_T. assumption.",
            "  - apply atomic_closure_truth_during_T. assumption.",
            "  - apply atomic_closure_truth_before_T. assumption.",
            "  - apply atomic_closure_truth_after_T. assumption.",
            "  - apply atomic_closure_truth_until_T. assumption.",
            "  - apply atomic_closure_truth_since_T. assumption.",
            "  - apply atomic_closure_truth_not_T. assumption.",
            "  - apply atomic_closure_truth_transition.",
            "    apply (atomic_transition_truth atomic_truth_facts).",
            "  - apply atomic_closure_truth_cause. assumption.",
        ]
    )
    lines.extend(
        [
            "Qed.",
            "",
            "Definition atomic_closure_truth_kernel_denotes : forall A : Type, A -> Prop :=",
            "  AtomicClosureTruth.",
            "",
            "Definition atomic_closure_truth_kernel : ConcreteTruthConditionKernel := {|",
            "  kernel_denotes := atomic_closure_truth_kernel_denotes;",
        ]
    )
    kernel_fields: list[tuple[str, str]] = []
    for name, (arg_types, _result_type) in sorted(declarations["functions"].items()):
        remaining_arg_types = arg_types[1:] if arg_types else []
        ordinary_args = [
            f"arg{index}"
            for index, _arg_type in enumerate(remaining_arg_types, 1)
        ]
        binders = " ".join(["n", "mods", *ordinary_args])
        constructor_args = " ".join(["n", "mods", *ordinary_args])
        kernel_fields.append(
            (
                concrete_kernel_application_field(name),
                (
                    f"fun {binders} => "
                    f"{atomic_closure_application_constructor(name)} "
                    f"{constructor_args} "
                    f"({atomic_truth_application_field(name)} atomic_truth_facts "
                    f"{constructor_args})"
                ),
            )
        )
    for type_name in declarations["types"]:
        kernel_fields.append(
            (
                concrete_kernel_sigma_field(type_name),
                f"fun P h => {atomic_closure_sigma_constructor(type_name)} P h",
            )
        )
    kernel_fields.extend(
        [
            ("repetition_truth", "fun n body h => atomic_closure_truth_repeat n body h"),
            ("temporal_truth_at_T", "fun marker body h => atomic_closure_truth_at_T marker body h"),
            ("temporal_truth_during_T", "fun marker body h => atomic_closure_truth_during_T marker body h"),
            ("temporal_truth_before_T", "fun marker body h => atomic_closure_truth_before_T marker body h"),
            ("temporal_truth_after_T", "fun marker body h => atomic_closure_truth_after_T marker body h"),
            ("temporal_truth_until_T", "fun marker body h => atomic_closure_truth_until_T marker body h"),
            ("temporal_truth_since_T", "fun marker body h => atomic_closure_truth_since_T marker body h"),
            ("polarity_truth_not_T", "fun body h => atomic_closure_truth_not_T body h"),
            (
                "transition_truth",
                "fun theme scale source target => "
                "atomic_closure_truth_transition theme scale source target "
                "(atomic_transition_truth atomic_truth_facts theme scale source target)",
            ),
            ("cause_truth", "fun causer effect h => atomic_closure_truth_cause causer effect h"),
        ]
    )
    for index, (field, value) in enumerate(kernel_fields):
        suffix = ";" if index < len(kernel_fields) - 1 else ""
        lines.append(f"  {field} := {value}{suffix}")
    lines.extend(
        [
            "|}.",
            "",
            "Definition atomic_closure_truth_conditions_from_kernel : TruthConditionSpec :=",
            "  truth_conditions_from_concrete_kernel atomic_closure_truth_kernel.",
            "",
            "Theorem atomic_closure_truth_kernel_exists :",
            "  exists K : ConcreteTruthConditionKernel,",
            "    K = atomic_closure_truth_kernel.",
            "Proof.",
            "  exists atomic_closure_truth_kernel. reflexivity.",
            "Qed.",
            "",
            "Theorem atomic_closure_truth_kernel_denotes_atomic_closure_truth :",
            "  forall A : Type, forall term : A,",
            "    AtomicClosureTruth A term ->",
            "    truth_denotes (truth_conditions_from_concrete_kernel",
            "      atomic_closure_truth_kernel) A term.",
            "Proof.",
            "  intros A term H.",
            "  exact H.",
            "Qed.",
            "",
            "Definition atomic_closure_truth_conditions : TruthConditionSpec :=",
            "  atomic_closure_truth_conditions_from_kernel.",
            "",
            "Theorem atomic_closure_truth_conditions_exists :",
            "  exists T : TruthConditionSpec,",
            "    T = atomic_closure_truth_conditions.",
            "Proof.",
            "  exists atomic_closure_truth_conditions. reflexivity.",
            "Qed.",
            "",
            "Theorem atomic_closure_truth_conditions_denote_atomic_closure_truth :",
            "  forall A : Type, forall term : A,",
            "    AtomicClosureTruth A term ->",
            "    truth_denotes atomic_closure_truth_conditions A term.",
            "Proof.",
            "  intros A term H.",
            "  exact H.",
            "Qed.",
        ]
    )
    return lines


def atomic_closure_evidence_backed_truth_source_lines(
    declarations: dict[str, Any],
    target: str,
) -> list[str]:
    if target == "lean":
        lines = [
            "def atomic_closure_evidence_backed_truth_sources : "
            "EvidenceBackedTruthConditionSources := {",
            "  evidence_denotes := AtomicClosureTruth,",
        ]
        assignment_groups: list[list[str]] = []
        for name, (arg_types, result_type) in sorted(declarations["functions"].items()):
            remaining_arg_types = (
                arg_types[2:]
                if arg_types[:2] == ["(n : Nat)", "ModifierSeq n"]
                else arg_types
            )
            ordinary_args = [
                f"arg{index}"
                for index, _arg_type in enumerate(remaining_arg_types, 1)
            ]
            lambda_args = ["n", "mods", *ordinary_args]
            application_args = " ".join(lambda_args)
            term = f"{name} {application_args}"
            proof = (
                f"AtomicClosureTruth.{atomic_closure_application_constructor(name)} "
                f"{application_args} "
                f"(atomic_truth_facts.{atomic_truth_application_field(name)} "
                f"{application_args})"
            )
            assignment_groups.append(
                [
                    f"  {evidence_source_application_field(name)} := "
                    f"fun {' '.join(lambda_args)} =>",
                    "      truth_evidence_intro",
                    f"        (AtomicClosureTruth {result_type} ({term}))",
                    f"        ({proof})",
                ]
            )
        for type_name in declarations["types"]:
            assignment_groups.append(
                [
                    f"  {evidence_source_sigma_field(type_name)} := fun P h =>",
                    "      truth_evidence_intro",
                    "        "
                    f"(AtomicClosureTruth Prop "
                    f"(Exists fun x : {type_name} => P x))",
                    "        "
                    f"(AtomicClosureTruth.{atomic_closure_sigma_constructor(type_name)} "
                    "P h)",
                ]
            )
        assignment_groups.extend(
            [
                [
                    "  evidence_repetition_truth := fun n body h =>",
                    "      truth_evidence_intro",
                    "        (AtomicClosureTruth PropT (repeat n body))",
                    "        (AtomicClosureTruth.atomic_closure_truth_repeat n body h)",
                ],
                [
                    "  evidence_temporal_truth_at_T := fun marker body h =>",
                    "      truth_evidence_intro",
                    "        (AtomicClosureTruth PropT (at_T marker body))",
                    "        (AtomicClosureTruth.atomic_closure_truth_at_T marker body h)",
                ],
                [
                    "  evidence_temporal_truth_during_T := fun marker body h =>",
                    "      truth_evidence_intro",
                    "        (AtomicClosureTruth PropT (during_T marker body))",
                    "        (AtomicClosureTruth.atomic_closure_truth_during_T marker body h)",
                ],
                [
                    "  evidence_temporal_truth_before_T := fun marker body h =>",
                    "      truth_evidence_intro",
                    "        (AtomicClosureTruth PropT (before_T marker body))",
                    "        (AtomicClosureTruth.atomic_closure_truth_before_T marker body h)",
                ],
                [
                    "  evidence_temporal_truth_after_T := fun marker body h =>",
                    "      truth_evidence_intro",
                    "        (AtomicClosureTruth PropT (after_T marker body))",
                    "        (AtomicClosureTruth.atomic_closure_truth_after_T marker body h)",
                ],
                [
                    "  evidence_temporal_truth_until_T := fun marker body h =>",
                    "      truth_evidence_intro",
                    "        (AtomicClosureTruth PropT (until_T marker body))",
                    "        (AtomicClosureTruth.atomic_closure_truth_until_T marker body h)",
                ],
                [
                    "  evidence_temporal_truth_since_T := fun marker body h =>",
                    "      truth_evidence_intro",
                    "        (AtomicClosureTruth PropT (since_T marker body))",
                    "        (AtomicClosureTruth.atomic_closure_truth_since_T marker body h)",
                ],
                [
                    "  evidence_polarity_truth_not_T := fun body h =>",
                    "      truth_evidence_intro",
                    "        (AtomicClosureTruth PropT (not_T body))",
                    "        (AtomicClosureTruth.atomic_closure_truth_not_T body h)",
                ],
                [
                    "  evidence_transition_truth := fun theme scale source target =>",
                    "      truth_evidence_intro",
                    "        (AtomicClosureTruth TransitionT "
                    "(Transition theme scale source target))",
                    "        (AtomicClosureTruth.atomic_closure_truth_transition "
                    "theme scale source target "
                    "(atomic_truth_facts.atomic_transition_truth "
                    "theme scale source target))",
                ],
                [
                    "  evidence_cause_truth := fun causer effect h =>",
                    "      truth_evidence_intro",
                    "        (AtomicClosureTruth PropT (Cause causer effect))",
                    "        (AtomicClosureTruth.atomic_closure_truth_cause causer effect h)",
                ],
            ]
        )
        for index, group in enumerate(assignment_groups):
            suffix = "," if index < len(assignment_groups) - 1 else ""
            for line_index, line in enumerate(group):
                if line_index == len(group) - 1:
                    lines.append(line + suffix)
                else:
                    lines.append(line)
        lines.extend(
            [
                "}",
                "",
                "def atomic_closure_evidence_backed_truth_kernel : "
                "ConcreteTruthConditionKernel :=",
                "  concrete_kernel_from_evidence_sources "
                "atomic_closure_evidence_backed_truth_sources",
                "",
                "def atomic_closure_evidence_backed_truth_ledger : "
                "IndependentTruthConditionObligationLedger :=",
                "  evidence_backed_truth_condition_ledger "
                "atomic_closure_evidence_backed_truth_sources",
                "",
                "theorem atomic_closure_evidence_backed_truth_sources_exist :",
                "    Exists (fun S : EvidenceBackedTruthConditionSources => "
                "S = atomic_closure_evidence_backed_truth_sources) := by",
                "  exact Exists.intro "
                "atomic_closure_evidence_backed_truth_sources rfl",
                "",
                "theorem atomic_closure_evidence_backed_truth_kernel_exists :",
                "    Exists (fun K : ConcreteTruthConditionKernel => "
                "K = atomic_closure_evidence_backed_truth_kernel) := by",
                "  exact Exists.intro "
                "atomic_closure_evidence_backed_truth_kernel rfl",
                "",
                "theorem atomic_closure_evidence_backed_truth_ledger_exists :",
                "    Exists (fun L : IndependentTruthConditionObligationLedger => "
                "L = atomic_closure_evidence_backed_truth_ledger) := by",
                "  exact Exists.intro "
                "atomic_closure_evidence_backed_truth_ledger rfl",
                "",
                "theorem atomic_closure_evidence_backed_truth_sources_sound :",
                "    (A : Type) -> (term : A) -> ModelInterpretable A term -> "
                "atomic_closure_evidence_backed_truth_ledger."
                "ledger_truth_conditions.truth_denotes A term := by",
                "  intro A term h",
                "  exact evidence_backed_truth_condition_sources_sound "
                "atomic_closure_evidence_backed_truth_sources A term h",
            ]
        )
        return lines

    lines = [
        "Definition atomic_closure_evidence_backed_truth_sources :",
        "  EvidenceBackedTruthConditionSources := {|",
        "  evidence_denotes := AtomicClosureTruth;",
    ]
    assignment_groups: list[list[str]] = []
    for name, (arg_types, result_type) in sorted(declarations["functions"].items()):
        remaining_arg_types = arg_types[1:] if arg_types else []
        ordinary_args = [
            f"arg{index}"
            for index, _arg_type in enumerate(remaining_arg_types, 1)
        ]
        lambda_args = ["n", "mods", *ordinary_args]
        application_args = " ".join(lambda_args)
        term = f"{name} {application_args}"
        proof = (
            f"{atomic_closure_application_constructor(name)} "
            f"{application_args} "
            f"({atomic_truth_application_field(name)} atomic_truth_facts "
            f"{application_args})"
        )
        assignment_groups.append(
            [
                f"  {evidence_source_application_field(name)} := "
                f"fun {' '.join(lambda_args)} =>",
                "      truth_evidence_intro",
                f"        (AtomicClosureTruth {result_type} ({term}))",
                f"        ({proof})",
            ]
        )
    for type_name in declarations["types"]:
        assignment_groups.append(
            [
                f"  {evidence_source_sigma_field(type_name)} := fun P h =>",
                "      truth_evidence_intro",
                f"        (AtomicClosureTruth Prop (exists x : {type_name}, P x))",
                f"        ({atomic_closure_sigma_constructor(type_name)} P h)",
            ]
        )
    assignment_groups.extend(
        [
            [
                "  evidence_repetition_truth := fun n body h =>",
                "      truth_evidence_intro",
                "        (AtomicClosureTruth PropT (repeat n body))",
                "        (atomic_closure_truth_repeat n body h)",
            ],
            [
                "  evidence_temporal_truth_at_T := fun marker body h =>",
                "      truth_evidence_intro",
                "        (AtomicClosureTruth PropT (at_T marker body))",
                "        (atomic_closure_truth_at_T marker body h)",
            ],
            [
                "  evidence_temporal_truth_during_T := fun marker body h =>",
                "      truth_evidence_intro",
                "        (AtomicClosureTruth PropT (during_T marker body))",
                "        (atomic_closure_truth_during_T marker body h)",
            ],
            [
                "  evidence_temporal_truth_before_T := fun marker body h =>",
                "      truth_evidence_intro",
                "        (AtomicClosureTruth PropT (before_T marker body))",
                "        (atomic_closure_truth_before_T marker body h)",
            ],
            [
                "  evidence_temporal_truth_after_T := fun marker body h =>",
                "      truth_evidence_intro",
                "        (AtomicClosureTruth PropT (after_T marker body))",
                "        (atomic_closure_truth_after_T marker body h)",
            ],
            [
                "  evidence_temporal_truth_until_T := fun marker body h =>",
                "      truth_evidence_intro",
                "        (AtomicClosureTruth PropT (until_T marker body))",
                "        (atomic_closure_truth_until_T marker body h)",
            ],
            [
                "  evidence_temporal_truth_since_T := fun marker body h =>",
                "      truth_evidence_intro",
                "        (AtomicClosureTruth PropT (since_T marker body))",
                "        (atomic_closure_truth_since_T marker body h)",
            ],
            [
                "  evidence_polarity_truth_not_T := fun body h =>",
                "      truth_evidence_intro",
                "        (AtomicClosureTruth PropT (not_T body))",
                "        (atomic_closure_truth_not_T body h)",
            ],
            [
                "  evidence_transition_truth := fun theme scale source target =>",
                "      truth_evidence_intro",
                "        (AtomicClosureTruth TransitionT "
                "(Transition theme scale source target))",
                "        (atomic_closure_truth_transition "
                "theme scale source target "
                "(atomic_transition_truth atomic_truth_facts "
                "theme scale source target))",
            ],
            [
                "  evidence_cause_truth := fun causer effect h =>",
                "      truth_evidence_intro",
                "        (AtomicClosureTruth PropT (Cause causer effect))",
                "        (atomic_closure_truth_cause causer effect h)",
            ],
        ]
    )
    for index, group in enumerate(assignment_groups):
        suffix = ";" if index < len(assignment_groups) - 1 else ""
        for line_index, line in enumerate(group):
            if line_index == len(group) - 1:
                lines.append(line + suffix)
            else:
                lines.append(line)
    lines.extend(
        [
            "|}.",
            "",
            "Definition atomic_closure_evidence_backed_truth_kernel :",
            "  ConcreteTruthConditionKernel :=",
            "  concrete_kernel_from_evidence_sources",
            "    atomic_closure_evidence_backed_truth_sources.",
            "",
            "Definition atomic_closure_evidence_backed_truth_ledger :",
            "  IndependentTruthConditionObligationLedger :=",
            "  evidence_backed_truth_condition_ledger",
            "    atomic_closure_evidence_backed_truth_sources.",
            "",
            "Theorem atomic_closure_evidence_backed_truth_sources_exist :",
            "  exists S : EvidenceBackedTruthConditionSources,",
            "    S = atomic_closure_evidence_backed_truth_sources.",
            "Proof.",
            "  exists atomic_closure_evidence_backed_truth_sources.",
            "  reflexivity.",
            "Qed.",
            "",
            "Theorem atomic_closure_evidence_backed_truth_kernel_exists :",
            "  exists K : ConcreteTruthConditionKernel,",
            "    K = atomic_closure_evidence_backed_truth_kernel.",
            "Proof.",
            "  exists atomic_closure_evidence_backed_truth_kernel.",
            "  reflexivity.",
            "Qed.",
            "",
            "Theorem atomic_closure_evidence_backed_truth_ledger_exists :",
            "  exists L : IndependentTruthConditionObligationLedger,",
            "    L = atomic_closure_evidence_backed_truth_ledger.",
            "Proof.",
            "  exists atomic_closure_evidence_backed_truth_ledger.",
            "  reflexivity.",
            "Qed.",
            "",
            "Theorem atomic_closure_evidence_backed_truth_sources_sound :",
            "  forall A : Type, forall term : A,",
            "    ModelInterpretable A term ->",
            "    truth_denotes",
            "      (ledger_truth_conditions",
            "        atomic_closure_evidence_backed_truth_ledger)",
            "      A term.",
            "Proof.",
            "  intros A term H.",
            "  exact",
            "    (evidence_backed_truth_condition_sources_sound",
            "      atomic_closure_evidence_backed_truth_sources A term H).",
            "Qed.",
        ]
    )
    return lines


def transition_refined_atomic_closure_truth_lines(
    declarations: dict[str, Any],
    target: str,
) -> list[str]:
    transitions: list[tuple[str, str, str, str]] = declarations["transitions"]
    if target == "lean":
        lines = [
            "inductive RegisteredStateTransitionTruth : "
            "Entity -> StateScale -> State -> State -> Prop where",
        ]
        for theme, scale, source, target_state in transitions:
            lines.append(
                f"  | {registered_state_transition_constructor(theme, scale, source, target_state)} : "
                "RegisteredStateTransitionTruth "
                f"{theme} {scale} {source} {target_state}"
            )
        lines.extend(
            [
                "",
                "theorem registered_state_transition_atomic_base_truth :",
                "    (theme : Entity) -> (scale : StateScale) -> "
                "(source : State) -> (target : State) ->",
                "    RegisteredStateTransitionTruth theme scale source target ->",
                "    AtomicBaseTruth TransitionT "
                "(Transition theme scale source target) := by",
                "  intro theme scale source target h",
            ]
        )
        if transitions:
            lines.append("  induction h")
            for theme, scale, source, target_state in transitions:
                lines.append(
                    f"  | {registered_state_transition_constructor(theme, scale, source, target_state)} =>"
                )
                lines.append(
                    "      exact AtomicBaseTruth.atomic_base_truth_transition "
                    f"{theme} {scale} {source} {target_state}"
                )
        else:
            lines.append("  cases h")
        lines.extend(
            [
                "",
                "inductive TransitionRefinedAtomicClosureTruth : "
                "(A : Type) -> A -> Prop where",
            ]
        )
        for name, (arg_types, result_type) in sorted(declarations["functions"].items()):
            lines.append(
                _lean_function_transition_refined_constructor(
                    name, arg_types, result_type
                )
            )
        for type_name in declarations["types"]:
            lines.append(
                f"  | {transition_refined_sigma_constructor(type_name)} : "
                f"(P : {type_name} -> Prop) -> "
                "((x : "
                f"{type_name}) -> TransitionRefinedAtomicClosureTruth Prop (P x)) -> "
                "TransitionRefinedAtomicClosureTruth Prop "
                f"(Exists fun x : {type_name} => P x)"
            )
        lines.extend(
            [
                "  | transition_refined_truth_repeat : (n : Nat) -> (body : PropT) -> "
                "TransitionRefinedAtomicClosureTruth PropT body -> "
                "TransitionRefinedAtomicClosureTruth PropT (repeat n body)",
                "  | transition_refined_truth_at_T : (marker : Entity) -> (body : PropT) -> "
                "TransitionRefinedAtomicClosureTruth PropT body -> "
                "TransitionRefinedAtomicClosureTruth PropT (at_T marker body)",
                "  | transition_refined_truth_during_T : (marker : Entity) -> (body : PropT) -> "
                "TransitionRefinedAtomicClosureTruth PropT body -> "
                "TransitionRefinedAtomicClosureTruth PropT (during_T marker body)",
                "  | transition_refined_truth_before_T : (marker : Entity) -> (body : PropT) -> "
                "TransitionRefinedAtomicClosureTruth PropT body -> "
                "TransitionRefinedAtomicClosureTruth PropT (before_T marker body)",
                "  | transition_refined_truth_after_T : (marker : Entity) -> (body : PropT) -> "
                "TransitionRefinedAtomicClosureTruth PropT body -> "
                "TransitionRefinedAtomicClosureTruth PropT (after_T marker body)",
                "  | transition_refined_truth_until_T : (marker : Entity) -> (body : PropT) -> "
                "TransitionRefinedAtomicClosureTruth PropT body -> "
                "TransitionRefinedAtomicClosureTruth PropT (until_T marker body)",
                "  | transition_refined_truth_since_T : (marker : Entity) -> (body : PropT) -> "
                "TransitionRefinedAtomicClosureTruth PropT body -> "
                "TransitionRefinedAtomicClosureTruth PropT (since_T marker body)",
                "  | transition_refined_truth_not_T : (body : PropT) -> "
                "TransitionRefinedAtomicClosureTruth PropT body -> "
                "TransitionRefinedAtomicClosureTruth PropT (not_T body)",
                "  | transition_refined_truth_transition : (theme : Entity) -> "
                "(scale : StateScale) -> (source : State) -> (target : State) -> "
                "RegisteredStateTransitionTruth theme scale source target -> "
                "TransitionRefinedAtomicClosureTruth TransitionT "
                "(Transition theme scale source target)",
                "  | transition_refined_truth_cause : (causer : Entity) -> "
                "(effect : TransitionT) -> "
                "TransitionRefinedAtomicClosureTruth TransitionT effect -> "
                "TransitionRefinedAtomicClosureTruth PropT (Cause causer effect)",
                "",
                "theorem transition_refined_atomic_closure_truth_implies_atomic_closure_truth :",
                "    (A : Type) -> (term : A) -> "
                "TransitionRefinedAtomicClosureTruth A term -> "
                "AtomicClosureTruth A term := by",
                "  intro A term h",
                "  induction h",
            ]
        )
        for name, (arg_types, _result_type) in sorted(declarations["functions"].items()):
            remaining_arg_types = (
                arg_types[2:]
                if arg_types[:2] == ["(n : Nat)", "ModifierSeq n"]
                else arg_types
            )
            ordinary_args = [
                f"arg{index}"
                for index, _arg_type in enumerate(remaining_arg_types, 1)
            ]
            pattern_args = " ".join(["n", "mods", *ordinary_args])
            lines.append(
                f"  | {transition_refined_application_constructor(name)} {pattern_args} hbase =>"
            )
            lines.append(
                f"      apply AtomicClosureTruth.{atomic_closure_application_constructor(name)}"
            )
            lines.append("      exact hbase")
        for type_name in declarations["types"]:
            lines.append(
                f"  | {transition_refined_sigma_constructor(type_name)} P h ih => "
                f"exact AtomicClosureTruth.{atomic_closure_sigma_constructor(type_name)} P ih"
            )
        lines.extend(
            [
                "  | transition_refined_truth_repeat n body h ih => "
                "exact AtomicClosureTruth.atomic_closure_truth_repeat n body ih",
                "  | transition_refined_truth_at_T marker body h ih => "
                "exact AtomicClosureTruth.atomic_closure_truth_at_T marker body ih",
                "  | transition_refined_truth_during_T marker body h ih => "
                "exact AtomicClosureTruth.atomic_closure_truth_during_T marker body ih",
                "  | transition_refined_truth_before_T marker body h ih => "
                "exact AtomicClosureTruth.atomic_closure_truth_before_T marker body ih",
                "  | transition_refined_truth_after_T marker body h ih => "
                "exact AtomicClosureTruth.atomic_closure_truth_after_T marker body ih",
                "  | transition_refined_truth_until_T marker body h ih => "
                "exact AtomicClosureTruth.atomic_closure_truth_until_T marker body ih",
                "  | transition_refined_truth_since_T marker body h ih => "
                "exact AtomicClosureTruth.atomic_closure_truth_since_T marker body ih",
                "  | transition_refined_truth_not_T body h ih => "
                "exact AtomicClosureTruth.atomic_closure_truth_not_T body ih",
                "  | transition_refined_truth_transition theme scale source target hreg =>",
                "      apply AtomicClosureTruth.atomic_closure_truth_transition",
                "      exact registered_state_transition_atomic_base_truth "
                "theme scale source target hreg",
                "  | transition_refined_truth_cause causer effect h ih => "
                "exact AtomicClosureTruth.atomic_closure_truth_cause causer effect ih",
            ]
        )
        return lines

    if transitions:
        lines = [
            "Inductive RegisteredStateTransitionTruth : "
            "Entity -> StateScale -> State -> State -> Prop :=",
        ]
        transition_constructors: list[str] = []
        for theme, scale, source, target_state in transitions:
            transition_constructors.extend(
                [
                    "  | "
                    f"{registered_state_transition_constructor(theme, scale, source, target_state)} :",
                    "      RegisteredStateTransitionTruth "
                    f"{theme} {scale} {source} {target_state}",
                ]
            )
        transition_constructors[-1] += "."
        lines.extend(transition_constructors)
    else:
        lines = [
            "Inductive RegisteredStateTransitionTruth : "
            "Entity -> StateScale -> State -> State -> Prop := .",
        ]
    lines.extend(
        [
            "",
            "Theorem registered_state_transition_atomic_base_truth :",
            "  forall theme : Entity, forall scale : StateScale,",
            "  forall source : State, forall target : State,",
            "    RegisteredStateTransitionTruth theme scale source target ->",
            "    AtomicBaseTruth TransitionT (Transition theme scale source target).",
            "Proof.",
            "  intros theme scale source target H.",
            "  induction H.",
        ]
    )
    for _transition in transitions:
        lines.append("  - apply atomic_base_truth_transition.")
    lines.extend(
        [
            "Qed.",
            "",
            "Inductive TransitionRefinedAtomicClosureTruth : "
            "forall A : Type, A -> Prop :=",
        ]
    )
    constructors: list[str] = []
    for name, (arg_types, result_type) in sorted(declarations["functions"].items()):
        constructors.extend(
            _coq_function_transition_refined_constructor(
                name, arg_types, result_type
            )
        )
    for type_name in declarations["types"]:
        constructors.extend(
            [
                f"  | {transition_refined_sigma_constructor(type_name)} : "
                f"forall P : {type_name} -> Prop,",
                f"      (forall x : {type_name}, "
                "TransitionRefinedAtomicClosureTruth Prop (P x)) ->",
                "      TransitionRefinedAtomicClosureTruth Prop "
                f"(exists x : {type_name}, P x)",
            ]
        )
    constructors.extend(
        [
            "  | transition_refined_truth_repeat : "
            "forall n : nat, forall body : PropT,",
            "      TransitionRefinedAtomicClosureTruth PropT body ->",
            "      TransitionRefinedAtomicClosureTruth PropT (repeat n body)",
            "  | transition_refined_truth_at_T : "
            "forall marker : Entity, forall body : PropT,",
            "      TransitionRefinedAtomicClosureTruth PropT body ->",
            "      TransitionRefinedAtomicClosureTruth PropT (at_T marker body)",
            "  | transition_refined_truth_during_T : "
            "forall marker : Entity, forall body : PropT,",
            "      TransitionRefinedAtomicClosureTruth PropT body ->",
            "      TransitionRefinedAtomicClosureTruth PropT (during_T marker body)",
            "  | transition_refined_truth_before_T : "
            "forall marker : Entity, forall body : PropT,",
            "      TransitionRefinedAtomicClosureTruth PropT body ->",
            "      TransitionRefinedAtomicClosureTruth PropT (before_T marker body)",
            "  | transition_refined_truth_after_T : "
            "forall marker : Entity, forall body : PropT,",
            "      TransitionRefinedAtomicClosureTruth PropT body ->",
            "      TransitionRefinedAtomicClosureTruth PropT (after_T marker body)",
            "  | transition_refined_truth_until_T : "
            "forall marker : Entity, forall body : PropT,",
            "      TransitionRefinedAtomicClosureTruth PropT body ->",
            "      TransitionRefinedAtomicClosureTruth PropT (until_T marker body)",
            "  | transition_refined_truth_since_T : "
            "forall marker : Entity, forall body : PropT,",
            "      TransitionRefinedAtomicClosureTruth PropT body ->",
            "      TransitionRefinedAtomicClosureTruth PropT (since_T marker body)",
            "  | transition_refined_truth_not_T : forall body : PropT,",
            "      TransitionRefinedAtomicClosureTruth PropT body ->",
            "      TransitionRefinedAtomicClosureTruth PropT (not_T body)",
            "  | transition_refined_truth_transition : "
            "forall theme : Entity, forall scale : StateScale,",
            "      forall source : State, forall target : State,",
            "      RegisteredStateTransitionTruth theme scale source target ->",
            "      TransitionRefinedAtomicClosureTruth TransitionT "
            "(Transition theme scale source target)",
            "  | transition_refined_truth_cause : "
            "forall causer : Entity, forall effect : TransitionT,",
            "      TransitionRefinedAtomicClosureTruth TransitionT effect ->",
            "      TransitionRefinedAtomicClosureTruth PropT (Cause causer effect)",
        ]
    )
    constructors[-1] += "."
    lines.extend(constructors)
    lines.extend(
        [
            "",
            "Theorem transition_refined_atomic_closure_truth_implies_atomic_closure_truth :",
            "  forall A : Type, forall term : A,",
            "    TransitionRefinedAtomicClosureTruth A term ->",
            "    AtomicClosureTruth A term.",
            "Proof.",
            "  intros A term H.",
            "  induction H.",
        ]
    )
    for name in sorted(declarations["functions"]):
        lines.append(f"  - apply {atomic_closure_application_constructor(name)}.")
        lines.append("    assumption.")
    for type_name in declarations["types"]:
        lines.append(f"  - apply {atomic_closure_sigma_constructor(type_name)}.")
        lines.append("    assumption.")
    lines.extend(
        [
            "  - apply atomic_closure_truth_repeat. assumption.",
            "  - apply atomic_closure_truth_at_T. assumption.",
            "  - apply atomic_closure_truth_during_T. assumption.",
            "  - apply atomic_closure_truth_before_T. assumption.",
            "  - apply atomic_closure_truth_after_T. assumption.",
            "  - apply atomic_closure_truth_until_T. assumption.",
            "  - apply atomic_closure_truth_since_T. assumption.",
            "  - apply atomic_closure_truth_not_T. assumption.",
            "  - apply atomic_closure_truth_transition.",
            "    apply registered_state_transition_atomic_base_truth.",
            "    assumption.",
            "  - apply atomic_closure_truth_cause. assumption.",
            "Qed.",
        ]
    )
    return lines


def registered_truth_condition_spec_lines(
    declarations: dict[str, Any],
    target: str,
) -> list[str]:
    if target == "lean":
        lines = [
            "structure RegisteredTruthConditionSpec : Type where",
            "  registered_truth_denotes : (A : Type) -> A -> Prop",
        ]
        for name, (arg_types, result_type) in sorted(declarations["functions"].items()):
            lines.append(
                _lean_function_registered_truth_field(name, arg_types, result_type)
            )
        for type_name in declarations["types"]:
            lines.append(
                f"  {registered_truth_sigma_field(type_name)} : "
                f"(P : {type_name} -> Prop) -> "
                f"((x : {type_name}) -> registered_truth_denotes Prop (P x)) -> "
                f"registered_truth_denotes Prop (Exists fun x : {type_name} => P x)"
            )
        lines.extend(
            [
                "  registered_truth_repeat : (n : Nat) -> (body : PropT) -> "
                "registered_truth_denotes PropT body -> "
                "registered_truth_denotes PropT (repeat n body)",
                "  registered_truth_at_T : (marker : Entity) -> (body : PropT) -> "
                "registered_truth_denotes PropT body -> "
                "registered_truth_denotes PropT (at_T marker body)",
                "  registered_truth_during_T : (marker : Entity) -> (body : PropT) -> "
                "registered_truth_denotes PropT body -> "
                "registered_truth_denotes PropT (during_T marker body)",
                "  registered_truth_before_T : (marker : Entity) -> (body : PropT) -> "
                "registered_truth_denotes PropT body -> "
                "registered_truth_denotes PropT (before_T marker body)",
                "  registered_truth_after_T : (marker : Entity) -> (body : PropT) -> "
                "registered_truth_denotes PropT body -> "
                "registered_truth_denotes PropT (after_T marker body)",
                "  registered_truth_until_T : (marker : Entity) -> (body : PropT) -> "
                "registered_truth_denotes PropT body -> "
                "registered_truth_denotes PropT (until_T marker body)",
                "  registered_truth_since_T : (marker : Entity) -> (body : PropT) -> "
                "registered_truth_denotes PropT body -> "
                "registered_truth_denotes PropT (since_T marker body)",
                "  registered_truth_not_T : (body : PropT) -> "
                "registered_truth_denotes PropT body -> "
                "registered_truth_denotes PropT (not_T body)",
                "  registered_truth_transition : (theme : Entity) -> "
                "(scale : StateScale) -> (source : State) -> (target : State) -> "
                "RegisteredStateTransitionTruth theme scale source target -> "
                "registered_truth_denotes TransitionT "
                "(Transition theme scale source target)",
                "  registered_truth_cause : (causer : Entity) -> "
                "(effect : TransitionT) -> "
                "registered_truth_denotes TransitionT effect -> "
                "registered_truth_denotes PropT (Cause causer effect)",
                "",
                "def transition_refined_registered_truth_denotes : "
                "(A : Type) -> A -> Prop :=",
                "  TransitionRefinedAtomicClosureTruth",
                "",
                "def transition_refined_registered_truth_conditions : "
                "RegisteredTruthConditionSpec := {",
                "  registered_truth_denotes := "
                "transition_refined_registered_truth_denotes,",
            ]
        )
        fields: list[tuple[str, str]] = []
        for name, (arg_types, _result_type) in sorted(declarations["functions"].items()):
            remaining_arg_types = (
                arg_types[2:]
                if arg_types[:2] == ["(n : Nat)", "ModifierSeq n"]
                else arg_types
            )
            ordinary_args = [
                f"arg{index}"
                for index, _arg_type in enumerate(remaining_arg_types, 1)
            ]
            binders = " ".join(["n", "mods", *ordinary_args])
            constructor_args = " ".join(["n", "mods", *ordinary_args])
            fields.append(
                (
                    registered_truth_application_field(name),
                    (
                        f"fun {binders} => "
                        "TransitionRefinedAtomicClosureTruth."
                        f"{transition_refined_application_constructor(name)} "
                        f"{constructor_args} "
                        f"(AtomicBaseTruth.{atomic_base_truth_application_constructor(name)} "
                        f"{constructor_args})"
                    ),
                )
            )
        for type_name in declarations["types"]:
            fields.append(
                (
                    registered_truth_sigma_field(type_name),
                    (
                        "fun P h => TransitionRefinedAtomicClosureTruth."
                        f"{transition_refined_sigma_constructor(type_name)} P h"
                    ),
                )
            )
        fields.extend(
            [
                (
                    "registered_truth_repeat",
                    "fun n body h => "
                    "TransitionRefinedAtomicClosureTruth."
                    "transition_refined_truth_repeat n body h",
                ),
                (
                    "registered_truth_at_T",
                    "fun marker body h => "
                    "TransitionRefinedAtomicClosureTruth."
                    "transition_refined_truth_at_T marker body h",
                ),
                (
                    "registered_truth_during_T",
                    "fun marker body h => "
                    "TransitionRefinedAtomicClosureTruth."
                    "transition_refined_truth_during_T marker body h",
                ),
                (
                    "registered_truth_before_T",
                    "fun marker body h => "
                    "TransitionRefinedAtomicClosureTruth."
                    "transition_refined_truth_before_T marker body h",
                ),
                (
                    "registered_truth_after_T",
                    "fun marker body h => "
                    "TransitionRefinedAtomicClosureTruth."
                    "transition_refined_truth_after_T marker body h",
                ),
                (
                    "registered_truth_until_T",
                    "fun marker body h => "
                    "TransitionRefinedAtomicClosureTruth."
                    "transition_refined_truth_until_T marker body h",
                ),
                (
                    "registered_truth_since_T",
                    "fun marker body h => "
                    "TransitionRefinedAtomicClosureTruth."
                    "transition_refined_truth_since_T marker body h",
                ),
                (
                    "registered_truth_not_T",
                    "fun body h => "
                    "TransitionRefinedAtomicClosureTruth."
                    "transition_refined_truth_not_T body h",
                ),
                (
                    "registered_truth_transition",
                    "fun theme scale source target h => "
                    "TransitionRefinedAtomicClosureTruth."
                    "transition_refined_truth_transition "
                    "theme scale source target h",
                ),
                (
                    "registered_truth_cause",
                    "fun causer effect h => "
                    "TransitionRefinedAtomicClosureTruth."
                    "transition_refined_truth_cause causer effect h",
                ),
            ]
        )
        for index, (field, value) in enumerate(fields):
            suffix = "," if index < len(fields) - 1 else ""
            lines.append(f"  {field} := {value}{suffix}")
        lines.extend(
            [
                "}",
                "",
                "theorem transition_refined_registered_truth_condition_spec_exists :",
                "    Exists (fun R : RegisteredTruthConditionSpec => "
                "R = transition_refined_registered_truth_conditions) := by",
                "  exact Exists.intro transition_refined_registered_truth_conditions rfl",
                "",
                "theorem transition_refined_registered_truth_conditions_denote_transition_refined :",
                "    (A : Type) -> (term : A) -> "
                "TransitionRefinedAtomicClosureTruth A term -> "
                "transition_refined_registered_truth_conditions."
                "registered_truth_denotes A term := by",
                "  intro A term h",
                "  exact h",
                "",
                "theorem transition_refined_registered_truth_conditions_imply_atomic_closure :",
                "    (A : Type) -> (term : A) -> "
                "transition_refined_registered_truth_conditions."
                "registered_truth_denotes A term -> "
                "AtomicClosureTruth A term := by",
                "  intro A term h",
                "  apply transition_refined_atomic_closure_truth_implies_atomic_closure_truth",
                "  exact h",
            ]
        )
        return lines

    lines = [
        "Record RegisteredTruthConditionSpec : Type := {",
        "  registered_truth_denotes : forall A : Type, A -> Prop;",
    ]
    for name, (arg_types, result_type) in sorted(declarations["functions"].items()):
        lines.extend(_coq_function_registered_truth_field(name, arg_types, result_type))
    for type_name in declarations["types"]:
        lines.extend(
            [
                f"  {registered_truth_sigma_field(type_name)} : "
                f"forall P : {type_name} -> Prop,",
                f"      (forall x : {type_name}, registered_truth_denotes Prop (P x)) ->",
                f"      registered_truth_denotes Prop (exists x : {type_name}, P x);",
            ]
        )
    lines.extend(
        [
            "  registered_truth_repeat : forall n : nat, forall body : PropT,",
            "      registered_truth_denotes PropT body ->",
            "      registered_truth_denotes PropT (repeat n body);",
            "  registered_truth_at_T : forall marker : Entity, forall body : PropT,",
            "      registered_truth_denotes PropT body ->",
            "      registered_truth_denotes PropT (at_T marker body);",
            "  registered_truth_during_T : forall marker : Entity, forall body : PropT,",
            "      registered_truth_denotes PropT body ->",
            "      registered_truth_denotes PropT (during_T marker body);",
            "  registered_truth_before_T : forall marker : Entity, forall body : PropT,",
            "      registered_truth_denotes PropT body ->",
            "      registered_truth_denotes PropT (before_T marker body);",
            "  registered_truth_after_T : forall marker : Entity, forall body : PropT,",
            "      registered_truth_denotes PropT body ->",
            "      registered_truth_denotes PropT (after_T marker body);",
            "  registered_truth_until_T : forall marker : Entity, forall body : PropT,",
            "      registered_truth_denotes PropT body ->",
            "      registered_truth_denotes PropT (until_T marker body);",
            "  registered_truth_since_T : forall marker : Entity, forall body : PropT,",
            "      registered_truth_denotes PropT body ->",
            "      registered_truth_denotes PropT (since_T marker body);",
            "  registered_truth_not_T : forall body : PropT,",
            "      registered_truth_denotes PropT body ->",
            "      registered_truth_denotes PropT (not_T body);",
            "  registered_truth_transition : "
            "forall theme : Entity, forall scale : StateScale, "
            "forall source : State, forall target : State,",
            "      RegisteredStateTransitionTruth theme scale source target ->",
            "      registered_truth_denotes TransitionT "
            "(Transition theme scale source target);",
            "  registered_truth_cause : "
            "forall causer : Entity, forall effect : TransitionT,",
            "      registered_truth_denotes TransitionT effect ->",
            "      registered_truth_denotes PropT (Cause causer effect)",
            "}.",
            "",
            "Definition transition_refined_registered_truth_denotes : "
            "forall A : Type, A -> Prop :=",
            "  TransitionRefinedAtomicClosureTruth.",
            "",
            "Definition transition_refined_registered_truth_conditions : "
            "RegisteredTruthConditionSpec := {|",
            "  registered_truth_denotes := "
            "transition_refined_registered_truth_denotes;",
        ]
    )
    fields: list[tuple[str, str]] = []
    for name, (arg_types, _result_type) in sorted(declarations["functions"].items()):
        remaining_arg_types = arg_types[1:] if arg_types else []
        ordinary_args = [
            f"arg{index}"
            for index, _arg_type in enumerate(remaining_arg_types, 1)
        ]
        binders = " ".join(["n", "mods", *ordinary_args])
        constructor_args = " ".join(["n", "mods", *ordinary_args])
        fields.append(
            (
                registered_truth_application_field(name),
                (
                    f"fun {binders} => "
                    f"{transition_refined_application_constructor(name)} "
                    f"{constructor_args} "
                    f"({atomic_base_truth_application_constructor(name)} "
                    f"{constructor_args})"
                ),
            )
        )
    for type_name in declarations["types"]:
        fields.append(
            (
                registered_truth_sigma_field(type_name),
                f"fun P h => {transition_refined_sigma_constructor(type_name)} P h",
            )
        )
    fields.extend(
        [
            ("registered_truth_repeat", "fun n body h => transition_refined_truth_repeat n body h"),
            ("registered_truth_at_T", "fun marker body h => transition_refined_truth_at_T marker body h"),
            ("registered_truth_during_T", "fun marker body h => transition_refined_truth_during_T marker body h"),
            ("registered_truth_before_T", "fun marker body h => transition_refined_truth_before_T marker body h"),
            ("registered_truth_after_T", "fun marker body h => transition_refined_truth_after_T marker body h"),
            ("registered_truth_until_T", "fun marker body h => transition_refined_truth_until_T marker body h"),
            ("registered_truth_since_T", "fun marker body h => transition_refined_truth_since_T marker body h"),
            ("registered_truth_not_T", "fun body h => transition_refined_truth_not_T body h"),
            (
                "registered_truth_transition",
                "fun theme scale source target h => "
                "transition_refined_truth_transition theme scale source target h",
            ),
            (
                "registered_truth_cause",
                "fun causer effect h => transition_refined_truth_cause causer effect h",
            ),
        ]
    )
    for index, (field, value) in enumerate(fields):
        suffix = ";" if index < len(fields) - 1 else ""
        lines.append(f"  {field} := {value}{suffix}")
    lines.extend(
        [
            "|}.",
            "",
            "Theorem transition_refined_registered_truth_condition_spec_exists :",
            "  exists R : RegisteredTruthConditionSpec,",
            "    R = transition_refined_registered_truth_conditions.",
            "Proof.",
            "  exists transition_refined_registered_truth_conditions. reflexivity.",
            "Qed.",
            "",
            "Theorem transition_refined_registered_truth_conditions_denote_transition_refined :",
            "  forall A : Type, forall term : A,",
            "    TransitionRefinedAtomicClosureTruth A term ->",
            "    registered_truth_denotes transition_refined_registered_truth_conditions A term.",
            "Proof.",
            "  intros A term H.",
            "  exact H.",
            "Qed.",
            "",
            "Theorem transition_refined_registered_truth_conditions_imply_atomic_closure :",
            "  forall A : Type, forall term : A,",
            "    registered_truth_denotes transition_refined_registered_truth_conditions A term ->",
            "    AtomicClosureTruth A term.",
            "Proof.",
            "  intros A term H.",
            "  apply transition_refined_atomic_closure_truth_implies_atomic_closure_truth.",
            "  exact H.",
            "Qed.",
        ]
    )
    return lines


def registered_lexical_truth_condition_spec_lines(
    declarations: dict[str, Any],
    target: str,
) -> list[str]:
    schemas: list[LexicalApplicationSchema] = declarations["lexical_applications"]
    if target == "lean":
        lines = [
            "inductive RegisteredLexicalApplicationTruth : "
            "(A : Type) -> A -> Prop where",
        ]
        if not schemas:
            lines.append("")
            return lines
        for schema in schemas:
            constructor = registered_lexical_application_constructor_from_schema(schema)
            _function, result_type, _adverb_count, _modifier_term, _modifiers, _arguments, binders = schema
            application = lexical_application_term(schema)
            binder_prefix = " -> ".join(
                f"({name} : {type_name})" for name, type_name in binders
            )
            conclusion = (
                f"RegisteredLexicalApplicationTruth {result_type} "
                f"({application})"
            )
            if binder_prefix:
                lines.append(f"  | {constructor} : {binder_prefix} -> {conclusion}")
            else:
                lines.append(f"  | {constructor} : {conclusion}")
        lines.extend(
            [
                "",
                "theorem registered_lexical_application_atomic_base_truth :",
                "    (A : Type) -> (term : A) -> "
                "RegisteredLexicalApplicationTruth A term -> "
                "AtomicBaseTruth A term := by",
                "  intro A term h",
                "  induction h",
            ]
        )
        for schema in schemas:
            constructor = registered_lexical_application_constructor_from_schema(schema)
            function, _result_type, _adverb_count, _modifier_term, _modifiers, _arguments, binders = schema
            pattern_args = " ".join(name for name, _type_name in binders)
            pattern = f"{constructor} {pattern_args}".rstrip()
            lines.append(f"  | {pattern} =>")
            lines.append(
                "      apply AtomicBaseTruth."
                f"{atomic_base_truth_application_constructor(function)}"
            )
        lines.extend(
            [
                "",
                "theorem registered_lexical_application_atomic_closure_truth :",
                "    (A : Type) -> (term : A) -> "
                "RegisteredLexicalApplicationTruth A term -> "
                "AtomicClosureTruth A term := by",
                "  intro A term h",
                "  induction h",
            ]
        )
        for schema in schemas:
            constructor = registered_lexical_application_constructor_from_schema(schema)
            function, _result_type, _adverb_count, _modifier_term, _modifiers, _arguments, binders = schema
            pattern_args = " ".join(name for name, _type_name in binders)
            pattern = f"{constructor} {pattern_args}".rstrip()
            lines.append(f"  | {pattern} =>")
            lines.append(
                "      apply AtomicClosureTruth."
                f"{atomic_closure_application_constructor(function)}"
            )
            lines.append(
                "      apply AtomicBaseTruth."
                f"{atomic_base_truth_application_constructor(function)}"
            )
        lines.extend(
            [
                "",
                "inductive FullyRegisteredAtomicClosureTruth : "
                "(A : Type) -> A -> Prop where",
                "  | fully_registered_atomic_truth_lexical_application : "
                "(A : Type) -> (term : A) -> "
                "RegisteredLexicalApplicationTruth A term -> "
                "FullyRegisteredAtomicClosureTruth A term",
            ]
        )
        for type_name in declarations["types"]:
            lines.append(
                f"  | fully_registered_atomic_truth_sigma_{type_name} : "
                f"(P : {type_name} -> Prop) -> "
                f"((x : {type_name}) -> FullyRegisteredAtomicClosureTruth Prop (P x)) -> "
                f"FullyRegisteredAtomicClosureTruth Prop (Exists fun x : {type_name} => P x)"
            )
        lines.extend(
            [
                "  | fully_registered_atomic_truth_repeat : (n : Nat) -> "
                "(body : PropT) -> FullyRegisteredAtomicClosureTruth PropT body -> "
                "FullyRegisteredAtomicClosureTruth PropT (repeat n body)",
                "  | fully_registered_atomic_truth_at_T : (marker : Entity) -> "
                "(body : PropT) -> FullyRegisteredAtomicClosureTruth PropT body -> "
                "FullyRegisteredAtomicClosureTruth PropT (at_T marker body)",
                "  | fully_registered_atomic_truth_during_T : (marker : Entity) -> "
                "(body : PropT) -> FullyRegisteredAtomicClosureTruth PropT body -> "
                "FullyRegisteredAtomicClosureTruth PropT (during_T marker body)",
                "  | fully_registered_atomic_truth_before_T : (marker : Entity) -> "
                "(body : PropT) -> FullyRegisteredAtomicClosureTruth PropT body -> "
                "FullyRegisteredAtomicClosureTruth PropT (before_T marker body)",
                "  | fully_registered_atomic_truth_after_T : (marker : Entity) -> "
                "(body : PropT) -> FullyRegisteredAtomicClosureTruth PropT body -> "
                "FullyRegisteredAtomicClosureTruth PropT (after_T marker body)",
                "  | fully_registered_atomic_truth_until_T : (marker : Entity) -> "
                "(body : PropT) -> FullyRegisteredAtomicClosureTruth PropT body -> "
                "FullyRegisteredAtomicClosureTruth PropT (until_T marker body)",
                "  | fully_registered_atomic_truth_since_T : (marker : Entity) -> "
                "(body : PropT) -> FullyRegisteredAtomicClosureTruth PropT body -> "
                "FullyRegisteredAtomicClosureTruth PropT (since_T marker body)",
                "  | fully_registered_atomic_truth_not_T : (body : PropT) -> "
                "FullyRegisteredAtomicClosureTruth PropT body -> "
                "FullyRegisteredAtomicClosureTruth PropT (not_T body)",
                "  | fully_registered_atomic_truth_transition : (theme : Entity) -> "
                "(scale : StateScale) -> (source : State) -> (target : State) -> "
                "RegisteredStateTransitionTruth theme scale source target -> "
                "FullyRegisteredAtomicClosureTruth TransitionT "
                "(Transition theme scale source target)",
                "  | fully_registered_atomic_truth_cause : (causer : Entity) -> "
                "(effect : TransitionT) -> "
                "FullyRegisteredAtomicClosureTruth TransitionT effect -> "
                "FullyRegisteredAtomicClosureTruth PropT (Cause causer effect)",
                "",
                "theorem fully_registered_atomic_closure_truth_implies_atomic_closure_truth :",
                "    (A : Type) -> (term : A) -> "
                "FullyRegisteredAtomicClosureTruth A term -> AtomicClosureTruth A term := by",
                "  intro A term h",
                "  induction h",
                "  | fully_registered_atomic_truth_lexical_application A term hreg =>",
                "      apply registered_lexical_application_atomic_closure_truth",
                "      exact hreg",
            ]
        )
        for type_name in declarations["types"]:
            lines.append(
                f"  | fully_registered_atomic_truth_sigma_{type_name} P h ih => "
                f"exact AtomicClosureTruth.{atomic_closure_sigma_constructor(type_name)} P ih"
            )
        lines.extend(
            [
                "  | fully_registered_atomic_truth_repeat n body h ih => "
                "exact AtomicClosureTruth.atomic_closure_truth_repeat n body ih",
                "  | fully_registered_atomic_truth_at_T marker body h ih => "
                "exact AtomicClosureTruth.atomic_closure_truth_at_T marker body ih",
                "  | fully_registered_atomic_truth_during_T marker body h ih => "
                "exact AtomicClosureTruth.atomic_closure_truth_during_T marker body ih",
                "  | fully_registered_atomic_truth_before_T marker body h ih => "
                "exact AtomicClosureTruth.atomic_closure_truth_before_T marker body ih",
                "  | fully_registered_atomic_truth_after_T marker body h ih => "
                "exact AtomicClosureTruth.atomic_closure_truth_after_T marker body ih",
                "  | fully_registered_atomic_truth_until_T marker body h ih => "
                "exact AtomicClosureTruth.atomic_closure_truth_until_T marker body ih",
                "  | fully_registered_atomic_truth_since_T marker body h ih => "
                "exact AtomicClosureTruth.atomic_closure_truth_since_T marker body ih",
                "  | fully_registered_atomic_truth_not_T body h ih => "
                "exact AtomicClosureTruth.atomic_closure_truth_not_T body ih",
                "  | fully_registered_atomic_truth_transition theme scale source target hreg =>",
                "      apply AtomicClosureTruth.atomic_closure_truth_transition",
                "      exact registered_state_transition_atomic_base_truth "
                "theme scale source target hreg",
                "  | fully_registered_atomic_truth_cause causer effect h ih => "
                "exact AtomicClosureTruth.atomic_closure_truth_cause causer effect ih",
                "",
                "structure FullyRegisteredTruthConditionSpec : Type where",
                "  fully_registered_truth_denotes : (A : Type) -> A -> Prop",
                "  fully_registered_truth_lexical_application : "
                "(A : Type) -> (term : A) -> "
                "RegisteredLexicalApplicationTruth A term -> "
                "fully_registered_truth_denotes A term",
            ]
        )
        for type_name in declarations["types"]:
            lines.append(
                f"  fully_registered_truth_sigma_{type_name} : "
                f"(P : {type_name} -> Prop) -> "
                f"((x : {type_name}) -> fully_registered_truth_denotes Prop (P x)) -> "
                f"fully_registered_truth_denotes Prop (Exists fun x : {type_name} => P x)"
            )
        lines.extend(
            [
                "  fully_registered_truth_repeat : (n : Nat) -> (body : PropT) -> "
                "fully_registered_truth_denotes PropT body -> "
                "fully_registered_truth_denotes PropT (repeat n body)",
                "  fully_registered_truth_at_T : (marker : Entity) -> (body : PropT) -> "
                "fully_registered_truth_denotes PropT body -> "
                "fully_registered_truth_denotes PropT (at_T marker body)",
                "  fully_registered_truth_during_T : (marker : Entity) -> (body : PropT) -> "
                "fully_registered_truth_denotes PropT body -> "
                "fully_registered_truth_denotes PropT (during_T marker body)",
                "  fully_registered_truth_before_T : (marker : Entity) -> (body : PropT) -> "
                "fully_registered_truth_denotes PropT body -> "
                "fully_registered_truth_denotes PropT (before_T marker body)",
                "  fully_registered_truth_after_T : (marker : Entity) -> (body : PropT) -> "
                "fully_registered_truth_denotes PropT body -> "
                "fully_registered_truth_denotes PropT (after_T marker body)",
                "  fully_registered_truth_until_T : (marker : Entity) -> (body : PropT) -> "
                "fully_registered_truth_denotes PropT body -> "
                "fully_registered_truth_denotes PropT (until_T marker body)",
                "  fully_registered_truth_since_T : (marker : Entity) -> (body : PropT) -> "
                "fully_registered_truth_denotes PropT body -> "
                "fully_registered_truth_denotes PropT (since_T marker body)",
                "  fully_registered_truth_not_T : (body : PropT) -> "
                "fully_registered_truth_denotes PropT body -> "
                "fully_registered_truth_denotes PropT (not_T body)",
                "  fully_registered_truth_transition : (theme : Entity) -> "
                "(scale : StateScale) -> (source : State) -> (target : State) -> "
                "RegisteredStateTransitionTruth theme scale source target -> "
                "fully_registered_truth_denotes TransitionT "
                "(Transition theme scale source target)",
                "  fully_registered_truth_cause : (causer : Entity) -> "
                "(effect : TransitionT) -> "
                "fully_registered_truth_denotes TransitionT effect -> "
                "fully_registered_truth_denotes PropT (Cause causer effect)",
                "",
                "def fully_registered_atomic_truth_denotes : (A : Type) -> A -> Prop :=",
                "  FullyRegisteredAtomicClosureTruth",
                "",
                "def fully_registered_truth_conditions : FullyRegisteredTruthConditionSpec := {",
                "  fully_registered_truth_denotes := fully_registered_atomic_truth_denotes,",
                "  fully_registered_truth_lexical_application := "
                "fun A term h => FullyRegisteredAtomicClosureTruth."
                "fully_registered_atomic_truth_lexical_application A term h,",
            ]
        )
        fields: list[tuple[str, str]] = []
        for type_name in declarations["types"]:
            fields.append(
                (
                    f"fully_registered_truth_sigma_{type_name}",
                    "fun P h => FullyRegisteredAtomicClosureTruth."
                    f"fully_registered_atomic_truth_sigma_{type_name} P h",
                )
            )
        fields.extend(
            [
                ("fully_registered_truth_repeat", "fun n body h => FullyRegisteredAtomicClosureTruth.fully_registered_atomic_truth_repeat n body h"),
                ("fully_registered_truth_at_T", "fun marker body h => FullyRegisteredAtomicClosureTruth.fully_registered_atomic_truth_at_T marker body h"),
                ("fully_registered_truth_during_T", "fun marker body h => FullyRegisteredAtomicClosureTruth.fully_registered_atomic_truth_during_T marker body h"),
                ("fully_registered_truth_before_T", "fun marker body h => FullyRegisteredAtomicClosureTruth.fully_registered_atomic_truth_before_T marker body h"),
                ("fully_registered_truth_after_T", "fun marker body h => FullyRegisteredAtomicClosureTruth.fully_registered_atomic_truth_after_T marker body h"),
                ("fully_registered_truth_until_T", "fun marker body h => FullyRegisteredAtomicClosureTruth.fully_registered_atomic_truth_until_T marker body h"),
                ("fully_registered_truth_since_T", "fun marker body h => FullyRegisteredAtomicClosureTruth.fully_registered_atomic_truth_since_T marker body h"),
                ("fully_registered_truth_not_T", "fun body h => FullyRegisteredAtomicClosureTruth.fully_registered_atomic_truth_not_T body h"),
                ("fully_registered_truth_transition", "fun theme scale source target h => FullyRegisteredAtomicClosureTruth.fully_registered_atomic_truth_transition theme scale source target h"),
                ("fully_registered_truth_cause", "fun causer effect h => FullyRegisteredAtomicClosureTruth.fully_registered_atomic_truth_cause causer effect h"),
            ]
        )
        for index, (field, value) in enumerate(fields):
            suffix = "," if index < len(fields) - 1 else ""
            lines.append(f"  {field} := {value}{suffix}")
        lines.extend(
            [
                "}",
                "",
                "theorem fully_registered_truth_condition_spec_exists :",
                "    Exists (fun F : FullyRegisteredTruthConditionSpec => "
                "F = fully_registered_truth_conditions) := by",
                "  exact Exists.intro fully_registered_truth_conditions rfl",
                "",
                "theorem fully_registered_truth_conditions_denote_fully_registered :",
                "    (A : Type) -> (term : A) -> "
                "FullyRegisteredAtomicClosureTruth A term -> "
                "fully_registered_truth_conditions."
                "fully_registered_truth_denotes A term := by",
                "  intro A term h",
                "  exact h",
                "",
                "theorem fully_registered_truth_conditions_imply_atomic_closure :",
                "    (A : Type) -> (term : A) -> "
                "fully_registered_truth_conditions."
                "fully_registered_truth_denotes A term -> "
                "AtomicClosureTruth A term := by",
                "  intro A term h",
                "  apply fully_registered_atomic_closure_truth_implies_atomic_closure_truth",
                "  exact h",
            ]
        )
        return lines

    lines = ["Inductive RegisteredLexicalApplicationTruth : forall A : Type, A -> Prop :="]
    if not schemas:
        lines[-1] += " ."
        return lines
    constructors: list[str] = []
    for schema in schemas:
        constructor = registered_lexical_application_constructor_from_schema(schema)
        _function, result_type, _adverb_count, _modifier_term, _modifiers, _arguments, binders = schema
        application = lexical_application_term(schema)
        if binders:
            binder_text = ", ".join(
                f"forall {name} : {type_name}" for name, type_name in binders
            )
            constructors.extend(
                [
                    f"  | {constructor} : {binder_text},",
                    "      RegisteredLexicalApplicationTruth "
                    f"{result_type} ({application})",
                ]
            )
        else:
            constructors.extend(
                [
                    f"  | {constructor} :",
                    "      RegisteredLexicalApplicationTruth "
                    f"{result_type} ({application})",
                ]
            )
    constructors[-1] += "."
    lines.extend(constructors)
    lines.extend(
        [
            "",
            "Theorem registered_lexical_application_atomic_base_truth :",
            "  forall A : Type, forall term : A,",
            "    RegisteredLexicalApplicationTruth A term -> AtomicBaseTruth A term.",
            "Proof.",
            "  intros A term H.",
            "  induction H.",
        ]
    )
    for schema in schemas:
        function = schema[0]
        lines.append(
            f"  - apply {atomic_base_truth_application_constructor(function)}."
        )
    lines.extend(
        [
            "Qed.",
            "",
            "Theorem registered_lexical_application_atomic_closure_truth :",
            "  forall A : Type, forall term : A,",
            "    RegisteredLexicalApplicationTruth A term -> AtomicClosureTruth A term.",
            "Proof.",
            "  intros A term H.",
            "  induction H.",
        ]
    )
    for schema in schemas:
        function = schema[0]
        lines.append(
            f"  - apply {atomic_closure_application_constructor(function)}."
        )
        lines.append(
            f"    apply {atomic_base_truth_application_constructor(function)}."
        )
    lines.extend(
        [
            "Qed.",
            "",
            "Inductive FullyRegisteredAtomicClosureTruth : forall A : Type, A -> Prop :=",
            "  | fully_registered_atomic_truth_lexical_application :",
            "      forall A : Type, forall term : A,",
            "      RegisteredLexicalApplicationTruth A term ->",
            "      FullyRegisteredAtomicClosureTruth A term",
        ]
    )
    for type_name in declarations["types"]:
        lines.extend(
            [
                f"  | fully_registered_atomic_truth_sigma_{type_name} : "
                f"forall P : {type_name} -> Prop,",
                f"      (forall x : {type_name}, "
                "FullyRegisteredAtomicClosureTruth Prop (P x)) ->",
                "      FullyRegisteredAtomicClosureTruth Prop "
                f"(exists x : {type_name}, P x)",
            ]
        )
    lines.extend(
        [
            "  | fully_registered_atomic_truth_repeat : "
            "forall n : nat, forall body : PropT,",
            "      FullyRegisteredAtomicClosureTruth PropT body ->",
            "      FullyRegisteredAtomicClosureTruth PropT (repeat n body)",
            "  | fully_registered_atomic_truth_at_T : "
            "forall marker : Entity, forall body : PropT,",
            "      FullyRegisteredAtomicClosureTruth PropT body ->",
            "      FullyRegisteredAtomicClosureTruth PropT (at_T marker body)",
            "  | fully_registered_atomic_truth_during_T : "
            "forall marker : Entity, forall body : PropT,",
            "      FullyRegisteredAtomicClosureTruth PropT body ->",
            "      FullyRegisteredAtomicClosureTruth PropT (during_T marker body)",
            "  | fully_registered_atomic_truth_before_T : "
            "forall marker : Entity, forall body : PropT,",
            "      FullyRegisteredAtomicClosureTruth PropT body ->",
            "      FullyRegisteredAtomicClosureTruth PropT (before_T marker body)",
            "  | fully_registered_atomic_truth_after_T : "
            "forall marker : Entity, forall body : PropT,",
            "      FullyRegisteredAtomicClosureTruth PropT body ->",
            "      FullyRegisteredAtomicClosureTruth PropT (after_T marker body)",
            "  | fully_registered_atomic_truth_until_T : "
            "forall marker : Entity, forall body : PropT,",
            "      FullyRegisteredAtomicClosureTruth PropT body ->",
            "      FullyRegisteredAtomicClosureTruth PropT (until_T marker body)",
            "  | fully_registered_atomic_truth_since_T : "
            "forall marker : Entity, forall body : PropT,",
            "      FullyRegisteredAtomicClosureTruth PropT body ->",
            "      FullyRegisteredAtomicClosureTruth PropT (since_T marker body)",
            "  | fully_registered_atomic_truth_not_T : forall body : PropT,",
            "      FullyRegisteredAtomicClosureTruth PropT body ->",
            "      FullyRegisteredAtomicClosureTruth PropT (not_T body)",
            "  | fully_registered_atomic_truth_transition : "
            "forall theme : Entity, forall scale : StateScale,",
            "      forall source : State, forall target : State,",
            "      RegisteredStateTransitionTruth theme scale source target ->",
            "      FullyRegisteredAtomicClosureTruth TransitionT "
            "(Transition theme scale source target)",
            "  | fully_registered_atomic_truth_cause : "
            "forall causer : Entity, forall effect : TransitionT,",
            "      FullyRegisteredAtomicClosureTruth TransitionT effect ->",
            "      FullyRegisteredAtomicClosureTruth PropT (Cause causer effect).",
            "",
            "Theorem fully_registered_atomic_closure_truth_implies_atomic_closure_truth :",
            "  forall A : Type, forall term : A,",
            "    FullyRegisteredAtomicClosureTruth A term -> AtomicClosureTruth A term.",
            "Proof.",
            "  intros A term H.",
            "  induction H.",
            "  - apply registered_lexical_application_atomic_closure_truth.",
            "    assumption.",
        ]
    )
    for type_name in declarations["types"]:
        lines.append(f"  - apply {atomic_closure_sigma_constructor(type_name)}.")
        lines.append("    assumption.")
    lines.extend(
        [
            "  - apply atomic_closure_truth_repeat. assumption.",
            "  - apply atomic_closure_truth_at_T. assumption.",
            "  - apply atomic_closure_truth_during_T. assumption.",
            "  - apply atomic_closure_truth_before_T. assumption.",
            "  - apply atomic_closure_truth_after_T. assumption.",
            "  - apply atomic_closure_truth_until_T. assumption.",
            "  - apply atomic_closure_truth_since_T. assumption.",
            "  - apply atomic_closure_truth_not_T. assumption.",
            "  - apply atomic_closure_truth_transition.",
            "    apply registered_state_transition_atomic_base_truth.",
            "    assumption.",
            "  - apply atomic_closure_truth_cause. assumption.",
            "Qed.",
            "",
            "Record FullyRegisteredTruthConditionSpec : Type := {",
            "  fully_registered_truth_denotes : forall A : Type, A -> Prop;",
            "  fully_registered_truth_lexical_application :",
            "      forall A : Type, forall term : A,",
            "      RegisteredLexicalApplicationTruth A term ->",
            "      fully_registered_truth_denotes A term;",
        ]
    )
    for type_name in declarations["types"]:
        lines.extend(
            [
                f"  fully_registered_truth_sigma_{type_name} : "
                f"forall P : {type_name} -> Prop,",
                f"      (forall x : {type_name}, "
                "fully_registered_truth_denotes Prop (P x)) ->",
                "      fully_registered_truth_denotes Prop "
                f"(exists x : {type_name}, P x);",
            ]
        )
    lines.extend(
        [
            "  fully_registered_truth_repeat : forall n : nat, forall body : PropT,",
            "      fully_registered_truth_denotes PropT body ->",
            "      fully_registered_truth_denotes PropT (repeat n body);",
            "  fully_registered_truth_at_T : forall marker : Entity, forall body : PropT,",
            "      fully_registered_truth_denotes PropT body ->",
            "      fully_registered_truth_denotes PropT (at_T marker body);",
            "  fully_registered_truth_during_T : forall marker : Entity, forall body : PropT,",
            "      fully_registered_truth_denotes PropT body ->",
            "      fully_registered_truth_denotes PropT (during_T marker body);",
            "  fully_registered_truth_before_T : forall marker : Entity, forall body : PropT,",
            "      fully_registered_truth_denotes PropT body ->",
            "      fully_registered_truth_denotes PropT (before_T marker body);",
            "  fully_registered_truth_after_T : forall marker : Entity, forall body : PropT,",
            "      fully_registered_truth_denotes PropT body ->",
            "      fully_registered_truth_denotes PropT (after_T marker body);",
            "  fully_registered_truth_until_T : forall marker : Entity, forall body : PropT,",
            "      fully_registered_truth_denotes PropT body ->",
            "      fully_registered_truth_denotes PropT (until_T marker body);",
            "  fully_registered_truth_since_T : forall marker : Entity, forall body : PropT,",
            "      fully_registered_truth_denotes PropT body ->",
            "      fully_registered_truth_denotes PropT (since_T marker body);",
            "  fully_registered_truth_not_T : forall body : PropT,",
            "      fully_registered_truth_denotes PropT body ->",
            "      fully_registered_truth_denotes PropT (not_T body);",
            "  fully_registered_truth_transition : "
            "forall theme : Entity, forall scale : StateScale,",
            "      forall source : State, forall target : State,",
            "      RegisteredStateTransitionTruth theme scale source target ->",
            "      fully_registered_truth_denotes TransitionT "
            "(Transition theme scale source target);",
            "  fully_registered_truth_cause : "
            "forall causer : Entity, forall effect : TransitionT,",
            "      fully_registered_truth_denotes TransitionT effect ->",
            "      fully_registered_truth_denotes PropT (Cause causer effect)",
            "}.",
            "",
            "Definition fully_registered_atomic_truth_denotes : forall A : Type, A -> Prop :=",
            "  FullyRegisteredAtomicClosureTruth.",
            "",
            "Definition fully_registered_truth_conditions : FullyRegisteredTruthConditionSpec := {|",
            "  fully_registered_truth_denotes := fully_registered_atomic_truth_denotes;",
            "  fully_registered_truth_lexical_application := "
            "fun A term h => fully_registered_atomic_truth_lexical_application A term h;",
        ]
    )
    fields: list[tuple[str, str]] = []
    for type_name in declarations["types"]:
        fields.append(
            (
                f"fully_registered_truth_sigma_{type_name}",
                f"fun P h => fully_registered_atomic_truth_sigma_{type_name} P h",
            )
        )
    fields.extend(
        [
            ("fully_registered_truth_repeat", "fun n body h => fully_registered_atomic_truth_repeat n body h"),
            ("fully_registered_truth_at_T", "fun marker body h => fully_registered_atomic_truth_at_T marker body h"),
            ("fully_registered_truth_during_T", "fun marker body h => fully_registered_atomic_truth_during_T marker body h"),
            ("fully_registered_truth_before_T", "fun marker body h => fully_registered_atomic_truth_before_T marker body h"),
            ("fully_registered_truth_after_T", "fun marker body h => fully_registered_atomic_truth_after_T marker body h"),
            ("fully_registered_truth_until_T", "fun marker body h => fully_registered_atomic_truth_until_T marker body h"),
            ("fully_registered_truth_since_T", "fun marker body h => fully_registered_atomic_truth_since_T marker body h"),
            ("fully_registered_truth_not_T", "fun body h => fully_registered_atomic_truth_not_T body h"),
            ("fully_registered_truth_transition", "fun theme scale source target h => fully_registered_atomic_truth_transition theme scale source target h"),
            ("fully_registered_truth_cause", "fun causer effect h => fully_registered_atomic_truth_cause causer effect h"),
        ]
    )
    for index, (field, value) in enumerate(fields):
        suffix = ";" if index < len(fields) - 1 else ""
        lines.append(f"  {field} := {value}{suffix}")
    lines.extend(
        [
            "|}.",
            "",
            "Theorem fully_registered_truth_condition_spec_exists :",
            "  exists F : FullyRegisteredTruthConditionSpec,",
            "    F = fully_registered_truth_conditions.",
            "Proof.",
            "  exists fully_registered_truth_conditions. reflexivity.",
            "Qed.",
            "",
            "Theorem fully_registered_truth_conditions_denote_fully_registered :",
            "  forall A : Type, forall term : A,",
            "    FullyRegisteredAtomicClosureTruth A term ->",
            "    fully_registered_truth_denotes fully_registered_truth_conditions A term.",
            "Proof.",
            "  intros A term H.",
            "  exact H.",
            "Qed.",
            "",
            "Theorem fully_registered_truth_conditions_imply_atomic_closure :",
            "  forall A : Type, forall term : A,",
            "    fully_registered_truth_denotes fully_registered_truth_conditions A term ->",
            "    AtomicClosureTruth A term.",
            "Proof.",
            "  intros A term H.",
            "  apply fully_registered_atomic_closure_truth_implies_atomic_closure_truth.",
            "  exact H.",
            "Qed.",
        ]
    )
    return lines


def concrete_truth_condition_kernel_instance_lines(
    declarations: dict[str, Any],
    target: str,
) -> list[str]:
    if target == "lean":
        kernel_fields: list[tuple[str, str]] = [
            ("kernel_denotes", "model_interpretable_truth_kernel_denotes"),
        ]
        for name, (arg_types, _result_type) in sorted(declarations["functions"].items()):
            remaining_arg_types = (
                arg_types[2:]
                if arg_types[:2] == ["(n : Nat)", "ModifierSeq n"]
                else arg_types
            )
            ordinary_args = [
                f"arg{index}"
                for index, _arg_type in enumerate(remaining_arg_types, 1)
            ]
            binders = " ".join(["n", "mods", *ordinary_args])
            constructor_args = " ".join(["n", "mods", *ordinary_args])
            kernel_fields.append(
                (
                    concrete_kernel_application_field(name),
                    (
                        f"fun {binders} => "
                        f"ModelInterpretable.{model_application_constructor(name)} "
                        f"{constructor_args}"
                    ),
                )
            )
        for type_name in declarations["types"]:
            kernel_fields.append(
                (
                    concrete_kernel_sigma_field(type_name),
                    f"fun P h => ModelInterpretable.{model_sigma_constructor(type_name)} P h",
                )
            )
        kernel_fields.extend(
            [
                (
                    "repetition_truth",
                    "fun n body h => ModelInterpretable.model_repeat n body h",
                ),
                (
                    "temporal_truth_at_T",
                    "fun marker body h => ModelInterpretable.model_at_T marker body h",
                ),
                (
                    "temporal_truth_during_T",
                    "fun marker body h => ModelInterpretable.model_during_T marker body h",
                ),
                (
                    "temporal_truth_before_T",
                    "fun marker body h => ModelInterpretable.model_before_T marker body h",
                ),
                (
                    "temporal_truth_after_T",
                    "fun marker body h => ModelInterpretable.model_after_T marker body h",
                ),
                (
                    "temporal_truth_until_T",
                    "fun marker body h => ModelInterpretable.model_until_T marker body h",
                ),
                (
                    "temporal_truth_since_T",
                    "fun marker body h => ModelInterpretable.model_since_T marker body h",
                ),
                (
                    "polarity_truth_not_T",
                    "fun body h => ModelInterpretable.model_not_T body h",
                ),
                (
                    "transition_truth",
                    "fun theme scale source target => "
                    "ModelInterpretable.model_transition theme scale source target",
                ),
                (
                    "cause_truth",
                    "fun causer effect h => ModelInterpretable.model_cause causer effect h",
                ),
            ]
        )
        lines = [
            "def model_interpretable_truth_kernel_denotes : (A : Type) -> A -> Prop :=",
            "  ModelInterpretable",
            "",
            "def model_interpretable_truth_kernel : ConcreteTruthConditionKernel := {",
        ]
        for index, (field, value) in enumerate(kernel_fields):
            suffix = "," if index < len(kernel_fields) - 1 else ""
            lines.append(f"  {field} := {value}{suffix}")
        lines.extend(
            [
                "}",
                "",
                "def model_interpretable_truth_conditions_from_kernel : TruthConditionSpec :=",
                "  truth_conditions_from_concrete_kernel model_interpretable_truth_kernel",
                "",
                "theorem model_interpretable_truth_kernel_exists :",
                "    Exists (fun K : ConcreteTruthConditionKernel => "
                "K = model_interpretable_truth_kernel) := by",
                "  exact Exists.intro model_interpretable_truth_kernel rfl",
                "",
                "theorem model_interpretable_truth_kernel_denotes_model_interpretable :",
                "    (A : Type) -> (term : A) -> ModelInterpretable A term -> "
                "(truth_conditions_from_concrete_kernel "
                "model_interpretable_truth_kernel).truth_denotes A term := by",
                "  intro A term h",
                "  apply concrete_kernel_induces_truth_condition_soundness",
                "  exact h",
            ]
        )
        return lines

    kernel_fields: list[tuple[str, str]] = [
        ("kernel_denotes", "model_interpretable_truth_kernel_denotes"),
    ]
    for name, (arg_types, _result_type) in sorted(declarations["functions"].items()):
        remaining_arg_types = arg_types[1:] if arg_types else []
        ordinary_args = [
            f"arg{index}"
            for index, _arg_type in enumerate(remaining_arg_types, 1)
        ]
        binders = " ".join(["n", "mods", *ordinary_args])
        constructor_args = " ".join(["n", "mods", *ordinary_args])
        kernel_fields.append(
            (
                concrete_kernel_application_field(name),
                f"fun {binders} => {model_application_constructor(name)} {constructor_args}",
            )
        )
    for type_name in declarations["types"]:
        kernel_fields.append(
            (
                concrete_kernel_sigma_field(type_name),
                f"fun P h => {model_sigma_constructor(type_name)} P h",
            )
        )
    kernel_fields.extend(
        [
            ("repetition_truth", "fun n body h => model_repeat n body h"),
            ("temporal_truth_at_T", "fun marker body h => model_at_T marker body h"),
            ("temporal_truth_during_T", "fun marker body h => model_during_T marker body h"),
            ("temporal_truth_before_T", "fun marker body h => model_before_T marker body h"),
            ("temporal_truth_after_T", "fun marker body h => model_after_T marker body h"),
            ("temporal_truth_until_T", "fun marker body h => model_until_T marker body h"),
            ("temporal_truth_since_T", "fun marker body h => model_since_T marker body h"),
            ("polarity_truth_not_T", "fun body h => model_not_T body h"),
            (
                "transition_truth",
                "fun theme scale source target => "
                "model_transition theme scale source target",
            ),
            ("cause_truth", "fun causer effect h => model_cause causer effect h"),
        ]
    )
    lines = [
        "Definition model_interpretable_truth_kernel_denotes : forall A : Type, A -> Prop :=",
        "  ModelInterpretable.",
        "",
        "Definition model_interpretable_truth_kernel : ConcreteTruthConditionKernel := {|",
    ]
    for index, (field, value) in enumerate(kernel_fields):
        suffix = ";" if index < len(kernel_fields) - 1 else ""
        lines.append(f"  {field} := {value}{suffix}")
    lines.extend(
        [
            "|}.",
            "",
            "Definition model_interpretable_truth_conditions_from_kernel : TruthConditionSpec :=",
            "  truth_conditions_from_concrete_kernel model_interpretable_truth_kernel.",
            "",
            "Theorem model_interpretable_truth_kernel_exists :",
            "  exists K : ConcreteTruthConditionKernel,",
            "    K = model_interpretable_truth_kernel.",
            "Proof.",
            "  exists model_interpretable_truth_kernel. reflexivity.",
            "Qed.",
            "",
            "Theorem model_interpretable_truth_kernel_denotes_model_interpretable :",
            "  forall A : Type, forall term : A,",
            "    ModelInterpretable A term ->",
            "    truth_denotes (truth_conditions_from_concrete_kernel",
            "      model_interpretable_truth_kernel) A term.",
            "Proof.",
            "  intros A term H.",
            "  apply concrete_kernel_induces_truth_condition_soundness.",
            "  exact H.",
            "Qed.",
        ]
    )
    return lines


def syntax_directed_truth_kernel_instance_lines(
    declarations: dict[str, Any],
    target: str,
) -> list[str]:
    if target == "lean":
        kernel_fields: list[tuple[str, str]] = [
            ("kernel_denotes", "syntax_directed_truth_kernel_denotes"),
        ]
        for name, (arg_types, _result_type) in sorted(declarations["functions"].items()):
            remaining_arg_types = (
                arg_types[2:]
                if arg_types[:2] == ["(n : Nat)", "ModifierSeq n"]
                else arg_types
            )
            ordinary_args = [
                f"arg{index}"
                for index, _arg_type in enumerate(remaining_arg_types, 1)
            ]
            binders = " ".join(["n", "mods", *ordinary_args])
            constructor_args = " ".join(["n", "mods", *ordinary_args])
            kernel_fields.append(
                (
                    concrete_kernel_application_field(name),
                    (
                        f"fun {binders} => "
                        f"SyntaxDirectedTruth.{syntax_truth_application_constructor(name)} "
                        f"{constructor_args}"
                    ),
                )
            )
        for type_name in declarations["types"]:
            kernel_fields.append(
                (
                    concrete_kernel_sigma_field(type_name),
                    f"fun P h => SyntaxDirectedTruth.{syntax_truth_sigma_constructor(type_name)} P h",
                )
            )
        kernel_fields.extend(
            [
                (
                    "repetition_truth",
                    "fun n body h => SyntaxDirectedTruth.syntax_truth_repeat n body h",
                ),
                (
                    "temporal_truth_at_T",
                    "fun marker body h => SyntaxDirectedTruth.syntax_truth_at_T marker body h",
                ),
                (
                    "temporal_truth_during_T",
                    "fun marker body h => SyntaxDirectedTruth.syntax_truth_during_T marker body h",
                ),
                (
                    "temporal_truth_before_T",
                    "fun marker body h => SyntaxDirectedTruth.syntax_truth_before_T marker body h",
                ),
                (
                    "temporal_truth_after_T",
                    "fun marker body h => SyntaxDirectedTruth.syntax_truth_after_T marker body h",
                ),
                (
                    "temporal_truth_until_T",
                    "fun marker body h => SyntaxDirectedTruth.syntax_truth_until_T marker body h",
                ),
                (
                    "temporal_truth_since_T",
                    "fun marker body h => SyntaxDirectedTruth.syntax_truth_since_T marker body h",
                ),
                (
                    "polarity_truth_not_T",
                    "fun body h => SyntaxDirectedTruth.syntax_truth_not_T body h",
                ),
                (
                    "transition_truth",
                    "fun theme scale source target => "
                    "SyntaxDirectedTruth.syntax_truth_transition theme scale source target",
                ),
                (
                    "cause_truth",
                    "fun causer effect h => SyntaxDirectedTruth.syntax_truth_cause causer effect h",
                ),
            ]
        )
        lines = [
            "def syntax_directed_truth_kernel_denotes : (A : Type) -> A -> Prop :=",
            "  SyntaxDirectedTruth",
            "",
            "def syntax_directed_truth_kernel : ConcreteTruthConditionKernel := {",
        ]
        for index, (field, value) in enumerate(kernel_fields):
            suffix = "," if index < len(kernel_fields) - 1 else ""
            lines.append(f"  {field} := {value}{suffix}")
        lines.extend(
            [
                "}",
                "",
                "def syntax_directed_truth_conditions_from_kernel : TruthConditionSpec :=",
                "  truth_conditions_from_concrete_kernel syntax_directed_truth_kernel",
                "",
                "theorem syntax_directed_truth_kernel_exists :",
                "    Exists (fun K : ConcreteTruthConditionKernel => "
                "K = syntax_directed_truth_kernel) := by",
                "  exact Exists.intro syntax_directed_truth_kernel rfl",
                "",
                "theorem syntax_directed_truth_kernel_denotes_syntax_directed_truth :",
                "    (A : Type) -> (term : A) -> SyntaxDirectedTruth A term -> "
                "(truth_conditions_from_concrete_kernel "
                "syntax_directed_truth_kernel).truth_denotes A term := by",
                "  intro A term h",
                "  exact h",
            ]
        )
        return lines

    kernel_fields: list[tuple[str, str]] = [
        ("kernel_denotes", "syntax_directed_truth_kernel_denotes"),
    ]
    for name, (arg_types, _result_type) in sorted(declarations["functions"].items()):
        remaining_arg_types = arg_types[1:] if arg_types else []
        ordinary_args = [
            f"arg{index}"
            for index, _arg_type in enumerate(remaining_arg_types, 1)
        ]
        binders = " ".join(["n", "mods", *ordinary_args])
        constructor_args = " ".join(["n", "mods", *ordinary_args])
        kernel_fields.append(
            (
                concrete_kernel_application_field(name),
                f"fun {binders} => {syntax_truth_application_constructor(name)} {constructor_args}",
            )
        )
    for type_name in declarations["types"]:
        kernel_fields.append(
            (
                concrete_kernel_sigma_field(type_name),
                f"fun P h => {syntax_truth_sigma_constructor(type_name)} P h",
            )
        )
    kernel_fields.extend(
        [
            ("repetition_truth", "fun n body h => syntax_truth_repeat n body h"),
            ("temporal_truth_at_T", "fun marker body h => syntax_truth_at_T marker body h"),
            ("temporal_truth_during_T", "fun marker body h => syntax_truth_during_T marker body h"),
            ("temporal_truth_before_T", "fun marker body h => syntax_truth_before_T marker body h"),
            ("temporal_truth_after_T", "fun marker body h => syntax_truth_after_T marker body h"),
            ("temporal_truth_until_T", "fun marker body h => syntax_truth_until_T marker body h"),
            ("temporal_truth_since_T", "fun marker body h => syntax_truth_since_T marker body h"),
            ("polarity_truth_not_T", "fun body h => syntax_truth_not_T body h"),
            (
                "transition_truth",
                "fun theme scale source target => "
                "syntax_truth_transition theme scale source target",
            ),
            ("cause_truth", "fun causer effect h => syntax_truth_cause causer effect h"),
        ]
    )
    lines = [
        "Definition syntax_directed_truth_kernel_denotes : forall A : Type, A -> Prop :=",
        "  SyntaxDirectedTruth.",
        "",
        "Definition syntax_directed_truth_kernel : ConcreteTruthConditionKernel := {|",
    ]
    for index, (field, value) in enumerate(kernel_fields):
        suffix = ";" if index < len(kernel_fields) - 1 else ""
        lines.append(f"  {field} := {value}{suffix}")
    lines.extend(
        [
            "|}.",
            "",
            "Definition syntax_directed_truth_conditions_from_kernel : TruthConditionSpec :=",
            "  truth_conditions_from_concrete_kernel syntax_directed_truth_kernel.",
            "",
            "Theorem syntax_directed_truth_kernel_exists :",
            "  exists K : ConcreteTruthConditionKernel,",
            "    K = syntax_directed_truth_kernel.",
            "Proof.",
            "  exists syntax_directed_truth_kernel. reflexivity.",
            "Qed.",
            "",
            "Theorem syntax_directed_truth_kernel_denotes_syntax_directed_truth :",
            "  forall A : Type, forall term : A,",
            "    SyntaxDirectedTruth A term ->",
            "    truth_denotes (truth_conditions_from_concrete_kernel",
            "      syntax_directed_truth_kernel) A term.",
            "Proof.",
            "  intros A term H.",
            "  exact H.",
            "Qed.",
        ]
    )
    return lines


def semantic_model_from_truth_conditions_lines(
    declarations: dict[str, Any],
    target: str,
) -> list[str]:
    field_pairs = [
        ("model_denotes", "truth_denotes"),
        *(
            (denotation_application_field(name), truth_application_field(name))
            for name in sorted(declarations["functions"])
        ),
        *(
            (denotation_sigma_field(type_name), truth_sigma_field(type_name))
            for type_name in declarations["types"]
        ),
        ("denote_repeat", "truth_repeat"),
        ("denote_at_T", "truth_at_T"),
        ("denote_during_T", "truth_during_T"),
        ("denote_before_T", "truth_before_T"),
        ("denote_after_T", "truth_after_T"),
        ("denote_until_T", "truth_until_T"),
        ("denote_since_T", "truth_since_T"),
        ("denote_not_T", "truth_not_T"),
        ("denote_transition", "truth_transition"),
        ("denote_cause", "truth_cause"),
    ]
    if target == "lean":
        lines = [
            "def semantic_model_from_truth_conditions (T : TruthConditionSpec) : SemanticModel := {",
        ]
        for index, (model_field, truth_field) in enumerate(field_pairs):
            suffix = "," if index < len(field_pairs) - 1 else ""
            lines.append(f"  {model_field} := T.{truth_field}{suffix}")
        lines.append("}")
        lines.extend(
            [
                "",
                "theorem truth_conditions_induce_denotational_soundness :",
                "    (T : TruthConditionSpec) -> (A : Type) -> (term : A) -> "
                "ModelInterpretable A term -> T.truth_denotes A term := by",
                "  intro T A term h",
                "  exact model_interpretable_denotational_sound "
                "(semantic_model_from_truth_conditions T) A term h",
            ]
        )
        return lines

    lines = [
        "Definition semantic_model_from_truth_conditions "
        "(T : TruthConditionSpec) : SemanticModel := {|",
    ]
    for index, (model_field, truth_field) in enumerate(field_pairs):
        suffix = ";" if index < len(field_pairs) - 1 else ""
        lines.append(f"  {model_field} := {truth_field} T{suffix}")
    lines.append("|}.")
    lines.extend(
        [
            "",
            "Theorem truth_conditions_induce_denotational_soundness :",
            "  forall T : TruthConditionSpec, forall A : Type, forall term : A,",
            "    ModelInterpretable A term -> truth_denotes T A term.",
            "Proof.",
            "  intros T A term H.",
            "  exact (model_interpretable_denotational_sound",
            "    (semantic_model_from_truth_conditions T) A term H).",
            "Qed.",
        ]
    )
    return lines


def truth_condition_instance_lines(
    declarations: dict[str, Any],
    target: str,
) -> list[str]:
    if target == "lean":
        fields: list[tuple[str, str]] = [
            ("truth_denotes", "tautological_truth_denotes"),
        ]
        for name, (arg_types, _result_type) in sorted(declarations["functions"].items()):
            remaining_arg_types = (
                arg_types[2:]
                if arg_types[:2] == ["(n : Nat)", "ModifierSeq n"]
                else arg_types
            )
            ordinary_args = [
                f"arg{index}"
                for index, _arg_type in enumerate(remaining_arg_types, 1)
            ]
            binders = " ".join(["n", "mods", *ordinary_args])
            fields.append(
                (
                    truth_application_field(name),
                    f"fun {binders} => True.intro",
                )
            )
        for type_name in declarations["types"]:
            fields.append(
                (
                    truth_sigma_field(type_name),
                    "fun P h => True.intro",
                )
            )
        fields.extend(
            [
                ("truth_repeat", "fun n body h => True.intro"),
                ("truth_at_T", "fun marker body h => True.intro"),
                ("truth_during_T", "fun marker body h => True.intro"),
                ("truth_before_T", "fun marker body h => True.intro"),
                ("truth_after_T", "fun marker body h => True.intro"),
                ("truth_until_T", "fun marker body h => True.intro"),
                ("truth_since_T", "fun marker body h => True.intro"),
                ("truth_not_T", "fun body h => True.intro"),
                ("truth_transition", "fun theme scale source target => True.intro"),
                ("truth_cause", "fun causer effect h => True.intro"),
            ]
        )
        lines = [
            "def tautological_truth_denotes : (A : Type) -> A -> Prop :=",
            "  fun _ _ => True",
            "",
            "def tautological_truth_conditions : TruthConditionSpec := {",
        ]
        for index, (field, value) in enumerate(fields):
            suffix = "," if index < len(fields) - 1 else ""
            lines.append(f"  {field} := {value}{suffix}")
        lines.extend(
            [
                "}",
                "",
                "def tautological_semantic_model : SemanticModel :=",
                "  semantic_model_from_truth_conditions tautological_truth_conditions",
                "",
                "theorem tautological_truth_condition_spec_exists :",
                "    Exists (fun T : TruthConditionSpec => T = tautological_truth_conditions) := by",
                "  exact Exists.intro tautological_truth_conditions rfl",
                "",
                "theorem tautological_truth_conditions_denote_model_interpretable :",
                "    (A : Type) -> (term : A) -> "
                "ModelInterpretable A term -> "
                "tautological_truth_conditions.truth_denotes A term := by",
                "  intro A term h",
                "  apply truth_conditions_induce_denotational_soundness",
                "  exact h",
            ]
        )
        lines.append("")
        structural_fields: list[tuple[str, str]] = [
            ("truth_denotes", "structural_truth_denotes"),
        ]
        for name, (arg_types, _result_type) in sorted(declarations["functions"].items()):
            remaining_arg_types = (
                arg_types[2:]
                if arg_types[:2] == ["(n : Nat)", "ModifierSeq n"]
                else arg_types
            )
            ordinary_args = [
                f"arg{index}"
                for index, _arg_type in enumerate(remaining_arg_types, 1)
            ]
            binders = " ".join(["n", "mods", *ordinary_args])
            constructor_args = " ".join(["n", "mods", *ordinary_args])
            structural_fields.append(
                (
                    truth_application_field(name),
                    (
                        f"fun {binders} => "
                        f"ModelInterpretable.{model_application_constructor(name)} "
                        f"{constructor_args}"
                    ),
                )
            )
        for type_name in declarations["types"]:
            structural_fields.append(
                (
                    truth_sigma_field(type_name),
                    f"fun P h => ModelInterpretable.{model_sigma_constructor(type_name)} P h",
                )
            )
        structural_fields.extend(
            [
                (
                    "truth_repeat",
                    "fun n body h => ModelInterpretable.model_repeat n body h",
                ),
                (
                    "truth_at_T",
                    "fun marker body h => ModelInterpretable.model_at_T marker body h",
                ),
                (
                    "truth_during_T",
                    "fun marker body h => ModelInterpretable.model_during_T marker body h",
                ),
                (
                    "truth_before_T",
                    "fun marker body h => ModelInterpretable.model_before_T marker body h",
                ),
                (
                    "truth_after_T",
                    "fun marker body h => ModelInterpretable.model_after_T marker body h",
                ),
                (
                    "truth_until_T",
                    "fun marker body h => ModelInterpretable.model_until_T marker body h",
                ),
                (
                    "truth_since_T",
                    "fun marker body h => ModelInterpretable.model_since_T marker body h",
                ),
                (
                    "truth_not_T",
                    "fun body h => ModelInterpretable.model_not_T body h",
                ),
                (
                    "truth_transition",
                    "fun theme scale source target => "
                    "ModelInterpretable.model_transition theme scale source target",
                ),
                (
                    "truth_cause",
                    "fun causer effect h => ModelInterpretable.model_cause causer effect h",
                ),
            ]
        )
        lines.extend(
            [
                "def structural_truth_denotes : (A : Type) -> A -> Prop :=",
                "  ModelInterpretable",
                "",
                "def structural_truth_conditions : TruthConditionSpec := {",
            ]
        )
        for index, (field, value) in enumerate(structural_fields):
            suffix = "," if index < len(structural_fields) - 1 else ""
            lines.append(f"  {field} := {value}{suffix}")
        lines.extend(
            [
                "}",
                "",
                "def structural_semantic_model : SemanticModel :=",
                "  semantic_model_from_truth_conditions structural_truth_conditions",
                "",
                "theorem structural_truth_condition_spec_exists :",
                "    Exists (fun T : TruthConditionSpec => T = structural_truth_conditions) := by",
                "  exact Exists.intro structural_truth_conditions rfl",
                "",
                "theorem structural_truth_conditions_denote_model_interpretable :",
                "    (A : Type) -> (term : A) -> "
                "ModelInterpretable A term -> "
                "structural_truth_conditions.truth_denotes A term := by",
                "  intro A term h",
                "  exact h",
            ]
        )
        return lines

    fields: list[tuple[str, str]] = [
        ("truth_denotes", "tautological_truth_denotes"),
    ]
    for name, (arg_types, _result_type) in sorted(declarations["functions"].items()):
        remaining_arg_types = arg_types[1:] if arg_types else []
        ordinary_args = [
            f"arg{index}"
            for index, _arg_type in enumerate(remaining_arg_types, 1)
        ]
        binders = " ".join(["n", "mods", *ordinary_args])
        fields.append((truth_application_field(name), f"fun {binders} => I"))
    for type_name in declarations["types"]:
        fields.append((truth_sigma_field(type_name), "fun P h => I"))
    fields.extend(
        [
            ("truth_repeat", "fun n body h => I"),
            ("truth_at_T", "fun marker body h => I"),
            ("truth_during_T", "fun marker body h => I"),
            ("truth_before_T", "fun marker body h => I"),
            ("truth_after_T", "fun marker body h => I"),
            ("truth_until_T", "fun marker body h => I"),
            ("truth_since_T", "fun marker body h => I"),
            ("truth_not_T", "fun body h => I"),
            ("truth_transition", "fun theme scale source target => I"),
            ("truth_cause", "fun causer effect h => I"),
        ]
    )
    lines = [
        "Definition tautological_truth_denotes : forall A : Type, A -> Prop :=",
        "  fun A term => True.",
        "",
        "Definition tautological_truth_conditions : TruthConditionSpec := {|",
    ]
    for index, (field, value) in enumerate(fields):
        suffix = ";" if index < len(fields) - 1 else ""
        lines.append(f"  {field} := {value}{suffix}")
    lines.extend(
        [
            "|}.",
            "",
            "Definition tautological_semantic_model : SemanticModel :=",
            "  semantic_model_from_truth_conditions tautological_truth_conditions.",
            "",
            "Theorem tautological_truth_condition_spec_exists :",
            "  exists T : TruthConditionSpec, T = tautological_truth_conditions.",
            "Proof.",
            "  exists tautological_truth_conditions. reflexivity.",
            "Qed.",
            "",
            "Theorem tautological_truth_conditions_denote_model_interpretable :",
            "  forall A : Type, forall term : A,",
            "    ModelInterpretable A term ->",
            "    truth_denotes tautological_truth_conditions A term.",
            "Proof.",
            "  intros A term H.",
            "  apply truth_conditions_induce_denotational_soundness.",
            "  exact H.",
            "Qed.",
        ]
    )
    lines.append("")
    structural_fields: list[tuple[str, str]] = [
        ("truth_denotes", "structural_truth_denotes"),
    ]
    for name, (arg_types, _result_type) in sorted(declarations["functions"].items()):
        remaining_arg_types = arg_types[1:] if arg_types else []
        ordinary_args = [
            f"arg{index}"
            for index, _arg_type in enumerate(remaining_arg_types, 1)
        ]
        binders = " ".join(["n", "mods", *ordinary_args])
        constructor_args = " ".join(["n", "mods", *ordinary_args])
        structural_fields.append(
            (
                truth_application_field(name),
                f"fun {binders} => {model_application_constructor(name)} {constructor_args}",
            )
        )
    for type_name in declarations["types"]:
        structural_fields.append(
            (
                truth_sigma_field(type_name),
                f"fun P h => {model_sigma_constructor(type_name)} P h",
            )
        )
    structural_fields.extend(
        [
            ("truth_repeat", "fun n body h => model_repeat n body h"),
            ("truth_at_T", "fun marker body h => model_at_T marker body h"),
            ("truth_during_T", "fun marker body h => model_during_T marker body h"),
            ("truth_before_T", "fun marker body h => model_before_T marker body h"),
            ("truth_after_T", "fun marker body h => model_after_T marker body h"),
            ("truth_until_T", "fun marker body h => model_until_T marker body h"),
            ("truth_since_T", "fun marker body h => model_since_T marker body h"),
            ("truth_not_T", "fun body h => model_not_T body h"),
            (
                "truth_transition",
                "fun theme scale source target => "
                "model_transition theme scale source target",
            ),
            ("truth_cause", "fun causer effect h => model_cause causer effect h"),
        ]
    )
    lines.extend(
        [
            "Definition structural_truth_denotes : forall A : Type, A -> Prop :=",
            "  ModelInterpretable.",
            "",
            "Definition structural_truth_conditions : TruthConditionSpec := {|",
        ]
    )
    for index, (field, value) in enumerate(structural_fields):
        suffix = ";" if index < len(structural_fields) - 1 else ""
        lines.append(f"  {field} := {value}{suffix}")
    lines.extend(
        [
            "|}.",
            "",
            "Definition structural_semantic_model : SemanticModel :=",
            "  semantic_model_from_truth_conditions structural_truth_conditions.",
            "",
            "Theorem structural_truth_condition_spec_exists :",
            "  exists T : TruthConditionSpec, T = structural_truth_conditions.",
            "Proof.",
            "  exists structural_truth_conditions. reflexivity.",
            "Qed.",
            "",
            "Theorem structural_truth_conditions_denote_model_interpretable :",
            "  forall A : Type, forall term : A,",
            "    ModelInterpretable A term ->",
            "    truth_denotes structural_truth_conditions A term.",
            "Proof.",
            "  intros A term H.",
            "  exact H.",
            "Qed.",
        ]
    )
    return lines


def semantic_preservation_proof_steps(term: Term, target: str) -> list[str]:
    prefix = "SemanticPreservation." if target == "lean" else ""
    suffix = "" if target == "lean" else "."

    def apply_constructor(name: str) -> str:
        return f"  apply {prefix}{name}{suffix}"

    def prove(current: Term) -> list[str]:
        kind = current["kind"]
        if kind == "application":
            function = export_atom(current["function"], target)
            return [apply_constructor(preservation_application_constructor(function))]
        if kind == "sigma":
            witness = export_atom(current["witness"], target)
            witness_type = export_type_name(current["type"], target)
            return [
                apply_constructor(preservation_sigma_constructor(witness_type)),
                f"  intro {witness}{suffix}",
                *prove(current["body"]),
            ]
        if kind == "repeat":
            return [apply_constructor("preserve_repeat"), *prove(current["body"])]
        if kind == "time":
            operator = export_atom(current["operator"] + "_T", target)
            return [apply_constructor(f"preserve_{operator}"), *prove(current["body"])]
        if kind == "not":
            return [apply_constructor("preserve_not_T"), *prove(current["body"])]
        if kind == "transition":
            return [apply_constructor("preserve_transition")]
        if kind == "cause":
            return [apply_constructor("preserve_cause"), *prove(current["effect"])]
        raise ValueError(f"Unknown term kind: {kind!r}")

    return prove(term)


def transition_refined_atomic_closure_proof_steps(
    term: Term,
    target: str,
) -> list[str]:
    prefix = "TransitionRefinedAtomicClosureTruth." if target == "lean" else ""
    suffix = "" if target == "lean" else "."

    def apply_constructor(name: str) -> str:
        return f"  apply {prefix}{name}{suffix}"

    def prove(current: Term) -> list[str]:
        kind = current["kind"]
        if kind == "application":
            function = export_atom(current["function"], target)
            constructor = transition_refined_application_constructor(function)
            base_constructor = atomic_base_truth_application_constructor(function)
            if target == "lean":
                args = [
                    str(current["adverb_count"]),
                    export_modifier_sequence(current["modifier_vector"], target),
                    *[export_atom(value, target) for value in current["arguments"]],
                ]
                return [
                    apply_constructor(constructor),
                    "  exact AtomicBaseTruth."
                    f"{base_constructor} {' '.join(args)}",
                ]
            return [
                apply_constructor(constructor),
                f"  apply {base_constructor}.",
            ]
        if kind == "sigma":
            witness = export_atom(current["witness"], target)
            witness_type = export_type_name(current["type"], target)
            return [
                apply_constructor(transition_refined_sigma_constructor(witness_type)),
                f"  intro {witness}{suffix}",
                *prove(current["body"]),
            ]
        if kind == "repeat":
            return [
                apply_constructor("transition_refined_truth_repeat"),
                *prove(current["body"]),
            ]
        if kind == "time":
            operator = export_atom(current["operator"] + "_T", target)
            return [
                apply_constructor(f"transition_refined_truth_{operator}"),
                *prove(current["body"]),
            ]
        if kind == "not":
            return [
                apply_constructor("transition_refined_truth_not_T"),
                *prove(current["body"]),
            ]
        if kind == "transition":
            theme = export_atom(current["theme"], target)
            scale = export_atom(current["state_scale"], target)
            source = export_atom(current["source_state"], target)
            target_state = export_atom(current["target_state"], target)
            registered_constructor = registered_state_transition_constructor(
                theme,
                scale,
                source,
                target_state,
            )
            if target == "lean":
                return [
                    apply_constructor("transition_refined_truth_transition"),
                    "  exact RegisteredStateTransitionTruth."
                    f"{registered_constructor}",
                ]
            return [
                apply_constructor("transition_refined_truth_transition"),
                f"  apply {registered_constructor}.",
            ]
        if kind == "cause":
            return [
                apply_constructor("transition_refined_truth_cause"),
                *prove(current["effect"]),
            ]
        raise ValueError(f"Unknown term kind: {kind!r}")

    return prove(term)


def fully_registered_atomic_closure_proof_steps(
    term: Term,
    target: str,
) -> list[str]:
    prefix = "FullyRegisteredAtomicClosureTruth." if target == "lean" else ""
    suffix = "" if target == "lean" else "."

    def apply_constructor(name: str) -> str:
        return f"  apply {prefix}{name}{suffix}"

    def prove(current: Term, bound_types: dict[str, str]) -> list[str]:
        kind = current["kind"]
        if kind == "application":
            schema = lexical_application_schema(current, target, bound_types)
            constructor = registered_lexical_application_constructor_from_schema(schema)
            if target == "lean":
                binder_args = " ".join(name for name, _type_name in schema[-1])
                constructor_term = (
                    f"RegisteredLexicalApplicationTruth.{constructor}"
                    + (f" {binder_args}" if binder_args else "")
                )
                return [
                    apply_constructor(
                        "fully_registered_atomic_truth_lexical_application"
                    ),
                    f"  exact {constructor_term}",
                ]
            return [
                apply_constructor(
                    "fully_registered_atomic_truth_lexical_application"
                ),
                f"  apply {constructor}.",
            ]
        if kind == "sigma":
            witness = export_atom(current["witness"], target)
            witness_type = export_type_name(current["type"], target)
            return [
                apply_constructor(
                    f"fully_registered_atomic_truth_sigma_{witness_type}"
                ),
                f"  intro {witness}{suffix}",
                *prove(current["body"], {**bound_types, witness: witness_type}),
            ]
        if kind == "repeat":
            return [
                apply_constructor("fully_registered_atomic_truth_repeat"),
                *prove(current["body"], bound_types),
            ]
        if kind == "time":
            operator = export_atom(current["operator"] + "_T", target)
            return [
                apply_constructor(f"fully_registered_atomic_truth_{operator}"),
                *prove(current["body"], bound_types),
            ]
        if kind == "not":
            return [
                apply_constructor("fully_registered_atomic_truth_not_T"),
                *prove(current["body"], bound_types),
            ]
        if kind == "transition":
            theme = export_atom(current["theme"], target)
            scale = export_atom(current["state_scale"], target)
            source = export_atom(current["source_state"], target)
            target_state = export_atom(current["target_state"], target)
            registered_constructor = registered_state_transition_constructor(
                theme,
                scale,
                source,
                target_state,
            )
            if target == "lean":
                return [
                    apply_constructor("fully_registered_atomic_truth_transition"),
                    "  exact RegisteredStateTransitionTruth."
                    f"{registered_constructor}",
                ]
            return [
                apply_constructor("fully_registered_atomic_truth_transition"),
                f"  apply {registered_constructor}.",
            ]
        if kind == "cause":
            return [
                apply_constructor("fully_registered_atomic_truth_cause"),
                *prove(current["effect"], bound_types),
            ]
        raise ValueError(f"Unknown term kind: {kind!r}")

    return prove(term, {})


def registered_lexical_truth_model_lines(
    declarations: dict[str, Any],
    target: str,
) -> list[str]:
    if target == "lean":
        lines = [
            "structure RegisteredLexicalTruthModel : Type where",
            "  registered_lexical_model_denotes : (A : Type) -> A -> Prop",
            "  registered_lexical_model_lexical_application : "
            "(A : Type) -> (term : A) -> "
            "RegisteredLexicalApplicationTruth A term -> "
            "registered_lexical_model_denotes A term",
        ]
        for type_name in declarations["types"]:
            lines.append(
                f"  registered_lexical_model_sigma_{type_name} : "
                f"(P : {type_name} -> Prop) -> "
                f"((x : {type_name}) -> "
                "registered_lexical_model_denotes Prop (P x)) -> "
                f"registered_lexical_model_denotes Prop "
                f"(Exists fun x : {type_name} => P x)"
            )
        lines.extend(
            [
                "  registered_lexical_model_repeat : (n : Nat) -> "
                "(body : PropT) -> registered_lexical_model_denotes PropT body -> "
                "registered_lexical_model_denotes PropT (repeat n body)",
                "  registered_lexical_model_at_T : (marker : Entity) -> "
                "(body : PropT) -> registered_lexical_model_denotes PropT body -> "
                "registered_lexical_model_denotes PropT (at_T marker body)",
                "  registered_lexical_model_during_T : (marker : Entity) -> "
                "(body : PropT) -> registered_lexical_model_denotes PropT body -> "
                "registered_lexical_model_denotes PropT (during_T marker body)",
                "  registered_lexical_model_before_T : (marker : Entity) -> "
                "(body : PropT) -> registered_lexical_model_denotes PropT body -> "
                "registered_lexical_model_denotes PropT (before_T marker body)",
                "  registered_lexical_model_after_T : (marker : Entity) -> "
                "(body : PropT) -> registered_lexical_model_denotes PropT body -> "
                "registered_lexical_model_denotes PropT (after_T marker body)",
                "  registered_lexical_model_until_T : (marker : Entity) -> "
                "(body : PropT) -> registered_lexical_model_denotes PropT body -> "
                "registered_lexical_model_denotes PropT (until_T marker body)",
                "  registered_lexical_model_since_T : (marker : Entity) -> "
                "(body : PropT) -> registered_lexical_model_denotes PropT body -> "
                "registered_lexical_model_denotes PropT (since_T marker body)",
                "  registered_lexical_model_not_T : (body : PropT) -> "
                "registered_lexical_model_denotes PropT body -> "
                "registered_lexical_model_denotes PropT (not_T body)",
                "  registered_lexical_model_transition : (theme : Entity) -> "
                "(scale : StateScale) -> (source : State) -> (target : State) -> "
                "RegisteredStateTransitionTruth theme scale source target -> "
                "registered_lexical_model_denotes TransitionT "
                "(Transition theme scale source target)",
                "  registered_lexical_model_cause : (causer : Entity) -> "
                "(effect : TransitionT) -> "
                "registered_lexical_model_denotes TransitionT effect -> "
                "registered_lexical_model_denotes PropT (Cause causer effect)",
                "",
                "def fully_registered_truth_conditions_from_registered_lexical_model "
                "(M : RegisteredLexicalTruthModel) : "
                "FullyRegisteredTruthConditionSpec := {",
                "  fully_registered_truth_denotes := "
                "M.registered_lexical_model_denotes,",
                "  fully_registered_truth_lexical_application := "
                "M.registered_lexical_model_lexical_application,",
            ]
        )
        bridge_fields: list[tuple[str, str]] = []
        for type_name in declarations["types"]:
            bridge_fields.append(
                (
                    f"fully_registered_truth_sigma_{type_name}",
                    f"M.registered_lexical_model_sigma_{type_name}",
                )
            )
        bridge_fields.extend(
            [
                ("fully_registered_truth_repeat", "M.registered_lexical_model_repeat"),
                ("fully_registered_truth_at_T", "M.registered_lexical_model_at_T"),
                ("fully_registered_truth_during_T", "M.registered_lexical_model_during_T"),
                ("fully_registered_truth_before_T", "M.registered_lexical_model_before_T"),
                ("fully_registered_truth_after_T", "M.registered_lexical_model_after_T"),
                ("fully_registered_truth_until_T", "M.registered_lexical_model_until_T"),
                ("fully_registered_truth_since_T", "M.registered_lexical_model_since_T"),
                ("fully_registered_truth_not_T", "M.registered_lexical_model_not_T"),
                ("fully_registered_truth_transition", "M.registered_lexical_model_transition"),
                ("fully_registered_truth_cause", "M.registered_lexical_model_cause"),
            ]
        )
        for index, (field, value) in enumerate(bridge_fields):
            suffix = "," if index < len(bridge_fields) - 1 else ""
            lines.append(f"  {field} := {value}{suffix}")
        lines.extend(
            [
                "}",
                "",
                "def registered_lexical_truth_model_denotes : "
                "(A : Type) -> A -> Prop :=",
                "  FullyRegisteredAtomicClosureTruth",
                "",
                "def registered_lexical_truth_model : "
                "RegisteredLexicalTruthModel := {",
                "  registered_lexical_model_denotes := "
                "registered_lexical_truth_model_denotes,",
                "  registered_lexical_model_lexical_application := "
                "fun A term h => FullyRegisteredAtomicClosureTruth."
                "fully_registered_atomic_truth_lexical_application A term h,",
            ]
        )
        model_fields: list[tuple[str, str]] = []
        for type_name in declarations["types"]:
            model_fields.append(
                (
                    f"registered_lexical_model_sigma_{type_name}",
                    "fun P h => FullyRegisteredAtomicClosureTruth."
                    f"fully_registered_atomic_truth_sigma_{type_name} P h",
                )
            )
        model_fields.extend(
            [
                ("registered_lexical_model_repeat", "fun n body h => FullyRegisteredAtomicClosureTruth.fully_registered_atomic_truth_repeat n body h"),
                ("registered_lexical_model_at_T", "fun marker body h => FullyRegisteredAtomicClosureTruth.fully_registered_atomic_truth_at_T marker body h"),
                ("registered_lexical_model_during_T", "fun marker body h => FullyRegisteredAtomicClosureTruth.fully_registered_atomic_truth_during_T marker body h"),
                ("registered_lexical_model_before_T", "fun marker body h => FullyRegisteredAtomicClosureTruth.fully_registered_atomic_truth_before_T marker body h"),
                ("registered_lexical_model_after_T", "fun marker body h => FullyRegisteredAtomicClosureTruth.fully_registered_atomic_truth_after_T marker body h"),
                ("registered_lexical_model_until_T", "fun marker body h => FullyRegisteredAtomicClosureTruth.fully_registered_atomic_truth_until_T marker body h"),
                ("registered_lexical_model_since_T", "fun marker body h => FullyRegisteredAtomicClosureTruth.fully_registered_atomic_truth_since_T marker body h"),
                ("registered_lexical_model_not_T", "fun body h => FullyRegisteredAtomicClosureTruth.fully_registered_atomic_truth_not_T body h"),
                ("registered_lexical_model_transition", "fun theme scale source target h => FullyRegisteredAtomicClosureTruth.fully_registered_atomic_truth_transition theme scale source target h"),
                ("registered_lexical_model_cause", "fun causer effect h => FullyRegisteredAtomicClosureTruth.fully_registered_atomic_truth_cause causer effect h"),
            ]
        )
        for index, (field, value) in enumerate(model_fields):
            suffix = "," if index < len(model_fields) - 1 else ""
            lines.append(f"  {field} := {value}{suffix}")
        lines.extend(
            [
                "}",
                "",
                "def registered_lexical_truth_conditions_from_model : "
                "FullyRegisteredTruthConditionSpec :=",
                "  fully_registered_truth_conditions_from_registered_lexical_model "
                "registered_lexical_truth_model",
                "",
                "theorem registered_lexical_truth_model_exists :",
                "    Exists (fun M : RegisteredLexicalTruthModel => "
                "M = registered_lexical_truth_model) := by",
                "  exact Exists.intro registered_lexical_truth_model rfl",
                "",
                "theorem registered_lexical_truth_conditions_from_model_exists :",
                "    Exists (fun F : FullyRegisteredTruthConditionSpec => "
                "F = registered_lexical_truth_conditions_from_model) := by",
                "  exact Exists.intro registered_lexical_truth_conditions_from_model rfl",
                "",
                "theorem registered_lexical_truth_model_denotes_fully_registered :",
                "    (A : Type) -> (term : A) -> "
                "FullyRegisteredAtomicClosureTruth A term -> "
                "registered_lexical_truth_model."
                "registered_lexical_model_denotes A term := by",
                "  intro A term h",
                "  exact h",
                "",
                "theorem "
                "registered_lexical_truth_conditions_from_model_denote_fully_registered :",
                "    (A : Type) -> (term : A) -> "
                "FullyRegisteredAtomicClosureTruth A term -> "
                "registered_lexical_truth_conditions_from_model."
                "fully_registered_truth_denotes A term := by",
                "  intro A term h",
                "  exact h",
                "",
                "theorem "
                "registered_lexical_truth_conditions_from_model_imply_atomic_closure :",
                "    (A : Type) -> (term : A) -> "
                "registered_lexical_truth_conditions_from_model."
                "fully_registered_truth_denotes A term -> "
                "AtomicClosureTruth A term := by",
                "  intro A term h",
                "  apply fully_registered_atomic_closure_truth_implies_atomic_closure_truth",
                "  exact h",
            ]
        )
        return lines

    lines = [
        "Record RegisteredLexicalTruthModel : Type := {",
        "  registered_lexical_model_denotes : forall A : Type, A -> Prop;",
        "  registered_lexical_model_lexical_application :",
        "      forall A : Type, forall term : A,",
        "      RegisteredLexicalApplicationTruth A term ->",
        "      registered_lexical_model_denotes A term;",
    ]
    for type_name in declarations["types"]:
        lines.extend(
            [
                f"  registered_lexical_model_sigma_{type_name} : "
                f"forall P : {type_name} -> Prop,",
                f"      (forall x : {type_name}, "
                "registered_lexical_model_denotes Prop (P x)) ->",
                "      registered_lexical_model_denotes Prop "
                f"(exists x : {type_name}, P x);",
            ]
        )
    lines.extend(
        [
            "  registered_lexical_model_repeat : "
            "forall n : nat, forall body : PropT,",
            "      registered_lexical_model_denotes PropT body ->",
            "      registered_lexical_model_denotes PropT (repeat n body);",
            "  registered_lexical_model_at_T : "
            "forall marker : Entity, forall body : PropT,",
            "      registered_lexical_model_denotes PropT body ->",
            "      registered_lexical_model_denotes PropT (at_T marker body);",
            "  registered_lexical_model_during_T : "
            "forall marker : Entity, forall body : PropT,",
            "      registered_lexical_model_denotes PropT body ->",
            "      registered_lexical_model_denotes PropT (during_T marker body);",
            "  registered_lexical_model_before_T : "
            "forall marker : Entity, forall body : PropT,",
            "      registered_lexical_model_denotes PropT body ->",
            "      registered_lexical_model_denotes PropT (before_T marker body);",
            "  registered_lexical_model_after_T : "
            "forall marker : Entity, forall body : PropT,",
            "      registered_lexical_model_denotes PropT body ->",
            "      registered_lexical_model_denotes PropT (after_T marker body);",
            "  registered_lexical_model_until_T : "
            "forall marker : Entity, forall body : PropT,",
            "      registered_lexical_model_denotes PropT body ->",
            "      registered_lexical_model_denotes PropT (until_T marker body);",
            "  registered_lexical_model_since_T : "
            "forall marker : Entity, forall body : PropT,",
            "      registered_lexical_model_denotes PropT body ->",
            "      registered_lexical_model_denotes PropT (since_T marker body);",
            "  registered_lexical_model_not_T : forall body : PropT,",
            "      registered_lexical_model_denotes PropT body ->",
            "      registered_lexical_model_denotes PropT (not_T body);",
            "  registered_lexical_model_transition : "
            "forall theme : Entity, forall scale : StateScale,",
            "      forall source : State, forall target : State,",
            "      RegisteredStateTransitionTruth theme scale source target ->",
            "      registered_lexical_model_denotes TransitionT "
            "(Transition theme scale source target);",
            "  registered_lexical_model_cause : "
            "forall causer : Entity, forall effect : TransitionT,",
            "      registered_lexical_model_denotes TransitionT effect ->",
            "      registered_lexical_model_denotes PropT (Cause causer effect)",
            "}.",
            "",
            "Definition fully_registered_truth_conditions_from_registered_lexical_model",
            "  (M : RegisteredLexicalTruthModel) : FullyRegisteredTruthConditionSpec := {|",
            "  fully_registered_truth_denotes := registered_lexical_model_denotes M;",
            "  fully_registered_truth_lexical_application := "
            "registered_lexical_model_lexical_application M;",
        ]
    )
    bridge_fields = [
        (f"fully_registered_truth_sigma_{type_name}", f"registered_lexical_model_sigma_{type_name} M")
        for type_name in declarations["types"]
    ]
    bridge_fields.extend(
        [
            ("fully_registered_truth_repeat", "registered_lexical_model_repeat M"),
            ("fully_registered_truth_at_T", "registered_lexical_model_at_T M"),
            ("fully_registered_truth_during_T", "registered_lexical_model_during_T M"),
            ("fully_registered_truth_before_T", "registered_lexical_model_before_T M"),
            ("fully_registered_truth_after_T", "registered_lexical_model_after_T M"),
            ("fully_registered_truth_until_T", "registered_lexical_model_until_T M"),
            ("fully_registered_truth_since_T", "registered_lexical_model_since_T M"),
            ("fully_registered_truth_not_T", "registered_lexical_model_not_T M"),
            ("fully_registered_truth_transition", "registered_lexical_model_transition M"),
            ("fully_registered_truth_cause", "registered_lexical_model_cause M"),
        ]
    )
    for index, (field, value) in enumerate(bridge_fields):
        suffix = ";" if index < len(bridge_fields) - 1 else ""
        lines.append(f"  {field} := {value}{suffix}")
    lines.extend(
        [
            "|}.",
            "",
            "Definition registered_lexical_truth_model_denotes : "
            "forall A : Type, A -> Prop :=",
            "  FullyRegisteredAtomicClosureTruth.",
            "",
            "Definition registered_lexical_truth_model : "
            "RegisteredLexicalTruthModel := {|",
            "  registered_lexical_model_denotes := "
            "registered_lexical_truth_model_denotes;",
            "  registered_lexical_model_lexical_application := "
            "fun A term h => "
            "fully_registered_atomic_truth_lexical_application A term h;",
        ]
    )
    model_fields = [
        (
            f"registered_lexical_model_sigma_{type_name}",
            f"fun P h => fully_registered_atomic_truth_sigma_{type_name} P h",
        )
        for type_name in declarations["types"]
    ]
    model_fields.extend(
        [
            ("registered_lexical_model_repeat", "fun n body h => fully_registered_atomic_truth_repeat n body h"),
            ("registered_lexical_model_at_T", "fun marker body h => fully_registered_atomic_truth_at_T marker body h"),
            ("registered_lexical_model_during_T", "fun marker body h => fully_registered_atomic_truth_during_T marker body h"),
            ("registered_lexical_model_before_T", "fun marker body h => fully_registered_atomic_truth_before_T marker body h"),
            ("registered_lexical_model_after_T", "fun marker body h => fully_registered_atomic_truth_after_T marker body h"),
            ("registered_lexical_model_until_T", "fun marker body h => fully_registered_atomic_truth_until_T marker body h"),
            ("registered_lexical_model_since_T", "fun marker body h => fully_registered_atomic_truth_since_T marker body h"),
            ("registered_lexical_model_not_T", "fun body h => fully_registered_atomic_truth_not_T body h"),
            ("registered_lexical_model_transition", "fun theme scale source target h => fully_registered_atomic_truth_transition theme scale source target h"),
            ("registered_lexical_model_cause", "fun causer effect h => fully_registered_atomic_truth_cause causer effect h"),
        ]
    )
    for index, (field, value) in enumerate(model_fields):
        suffix = ";" if index < len(model_fields) - 1 else ""
        lines.append(f"  {field} := {value}{suffix}")
    lines.extend(
        [
            "|}.",
            "",
            "Definition registered_lexical_truth_conditions_from_model :",
            "  FullyRegisteredTruthConditionSpec :=",
            "  fully_registered_truth_conditions_from_registered_lexical_model",
            "    registered_lexical_truth_model.",
            "",
            "Theorem registered_lexical_truth_model_exists :",
            "  exists M : RegisteredLexicalTruthModel,",
            "    M = registered_lexical_truth_model.",
            "Proof.",
            "  exists registered_lexical_truth_model. reflexivity.",
            "Qed.",
            "",
            "Theorem registered_lexical_truth_conditions_from_model_exists :",
            "  exists F : FullyRegisteredTruthConditionSpec,",
            "    F = registered_lexical_truth_conditions_from_model.",
            "Proof.",
            "  exists registered_lexical_truth_conditions_from_model. reflexivity.",
            "Qed.",
            "",
            "Theorem registered_lexical_truth_model_denotes_fully_registered :",
            "  forall A : Type, forall term : A,",
            "    FullyRegisteredAtomicClosureTruth A term ->",
            "    registered_lexical_model_denotes registered_lexical_truth_model A term.",
            "Proof.",
            "  intros A term H.",
            "  exact H.",
            "Qed.",
            "",
            "Theorem registered_lexical_truth_conditions_from_model_denote_fully_registered :",
            "  forall A : Type, forall term : A,",
            "    FullyRegisteredAtomicClosureTruth A term ->",
            "    fully_registered_truth_denotes "
            "registered_lexical_truth_conditions_from_model A term.",
            "Proof.",
            "  intros A term H.",
            "  exact H.",
            "Qed.",
            "",
            "Theorem registered_lexical_truth_conditions_from_model_imply_atomic_closure :",
            "  forall A : Type, forall term : A,",
            "    fully_registered_truth_denotes "
            "registered_lexical_truth_conditions_from_model A term ->",
            "    AtomicClosureTruth A term.",
            "Proof.",
            "  intros A term H.",
            "  apply fully_registered_atomic_closure_truth_implies_atomic_closure_truth.",
            "  exact H.",
            "Qed.",
        ]
    )
    return lines


def registered_lexical_truth_model_example_lines(
    results: list[dict[str, Any]],
    target: str,
) -> list[str]:
    lines: list[str] = []
    if target == "lean":
        for idx, result in enumerate(results, 1):
            annotation = export_result_type(result["ast"])
            lines.extend(
                [
                    "theorem "
                    f"example_{idx}_registered_lexical_truth_model_sound : "
                    "registered_lexical_truth_model."
                    "registered_lexical_model_denotes "
                    f"{annotation} example_{idx} := by",
                    "  apply registered_lexical_truth_model_denotes_fully_registered",
                    f"  exact example_{idx}_fully_registered_atomic_closure_truth",
                    "",
                    "theorem "
                    f"example_{idx}_registered_lexical_truth_conditions_from_model_sound : "
                    "registered_lexical_truth_conditions_from_model."
                    "fully_registered_truth_denotes "
                    f"{annotation} example_{idx} := by",
                    "  apply "
                    "registered_lexical_truth_conditions_from_model_denote_fully_registered",
                    f"  exact example_{idx}_fully_registered_atomic_closure_truth",
                    "",
                ]
            )
        if lines:
            lines.pop()
        return lines

    for idx, result in enumerate(results, 1):
        annotation = export_result_type(result["ast"])
        lines.extend(
            [
                "Theorem "
                f"example_{idx}_registered_lexical_truth_model_sound :",
                "  registered_lexical_model_denotes registered_lexical_truth_model "
                f"{annotation} example_{idx}.",
                "Proof.",
                "  apply registered_lexical_truth_model_denotes_fully_registered.",
                f"  exact example_{idx}_fully_registered_atomic_closure_truth.",
                "Qed.",
                "",
                "Theorem "
                f"example_{idx}_registered_lexical_truth_conditions_from_model_sound :",
                "  fully_registered_truth_denotes "
                "registered_lexical_truth_conditions_from_model "
                f"{annotation} example_{idx}.",
                "Proof.",
                "  apply registered_lexical_truth_conditions_from_model_denote_fully_registered.",
                f"  exact example_{idx}_fully_registered_atomic_closure_truth.",
                "Qed.",
                "",
            ]
        )
    if lines:
        lines.pop()
    return lines


def concrete_registered_compositional_model_lines(
    declarations: dict[str, Any],
    target: str,
) -> list[str]:
    if target == "lean":
        lines = [
            "structure ConcreteRegisteredCompositionalModel : Type where",
            "  concrete_registered_composition_denotes : (A : Type) -> A -> Prop",
            "  concrete_registered_composition_atomic : "
            "(A : Type) -> (term : A) -> "
            "ConcreteRegisteredAtomicTruth A term -> "
            "concrete_registered_composition_denotes A term",
        ]
        for type_name in declarations["types"]:
            lines.append(
                f"  concrete_registered_composition_sigma_{type_name} : "
                f"(P : {type_name} -> Prop) -> "
                f"((x : {type_name}) -> "
                "concrete_registered_composition_denotes Prop (P x)) -> "
                "concrete_registered_composition_denotes Prop "
                f"(Exists fun x : {type_name} => P x)"
            )
        lines.extend(
            [
                "  concrete_registered_composition_repeat : "
                "(n : Nat) -> (body : PropT) -> "
                "concrete_registered_composition_denotes PropT body -> "
                "concrete_registered_composition_denotes PropT (repeat n body)",
                "  concrete_registered_composition_at_T : "
                "(marker : Entity) -> (body : PropT) -> "
                "concrete_registered_composition_denotes PropT body -> "
                "concrete_registered_composition_denotes PropT (at_T marker body)",
                "  concrete_registered_composition_during_T : "
                "(marker : Entity) -> (body : PropT) -> "
                "concrete_registered_composition_denotes PropT body -> "
                "concrete_registered_composition_denotes PropT "
                "(during_T marker body)",
                "  concrete_registered_composition_before_T : "
                "(marker : Entity) -> (body : PropT) -> "
                "concrete_registered_composition_denotes PropT body -> "
                "concrete_registered_composition_denotes PropT "
                "(before_T marker body)",
                "  concrete_registered_composition_after_T : "
                "(marker : Entity) -> (body : PropT) -> "
                "concrete_registered_composition_denotes PropT body -> "
                "concrete_registered_composition_denotes PropT "
                "(after_T marker body)",
                "  concrete_registered_composition_until_T : "
                "(marker : Entity) -> (body : PropT) -> "
                "concrete_registered_composition_denotes PropT body -> "
                "concrete_registered_composition_denotes PropT "
                "(until_T marker body)",
                "  concrete_registered_composition_since_T : "
                "(marker : Entity) -> (body : PropT) -> "
                "concrete_registered_composition_denotes PropT body -> "
                "concrete_registered_composition_denotes PropT "
                "(since_T marker body)",
                "  concrete_registered_composition_not_T : (body : PropT) -> "
                "concrete_registered_composition_denotes PropT body -> "
                "concrete_registered_composition_denotes PropT (not_T body)",
                "  concrete_registered_composition_cause : "
                "(causer : Entity) -> (effect : TransitionT) -> "
                "concrete_registered_composition_denotes TransitionT effect -> "
                "concrete_registered_composition_denotes PropT "
                "(Cause causer effect)",
                "  concrete_registered_composition_sound : "
                "(A : Type) -> (term : A) -> "
                "concrete_registered_composition_denotes A term -> "
                "AtomicClosureTruth A term",
                "",
                "def concrete_registered_compositional_model : "
                "ConcreteRegisteredCompositionalModel := {",
                "  concrete_registered_composition_denotes := ConcreteRegisteredTruth,",
                "  concrete_registered_composition_atomic := "
                "fun A term h => ConcreteRegisteredTruth."
                "concrete_registered_truth_atomic A term h,",
            ]
        )
        model_fields: list[tuple[str, str]] = []
        for type_name in declarations["types"]:
            model_fields.append(
                (
                    f"concrete_registered_composition_sigma_{type_name}",
                    "fun P h => ConcreteRegisteredTruth."
                    f"concrete_registered_truth_sigma_{type_name} P h",
                )
            )
        model_fields.extend(
            [
                (
                    "concrete_registered_composition_repeat",
                    "fun n body h => ConcreteRegisteredTruth."
                    "concrete_registered_truth_repeat n body h",
                ),
                (
                    "concrete_registered_composition_at_T",
                    "fun marker body h => ConcreteRegisteredTruth."
                    "concrete_registered_truth_at_T marker body h",
                ),
                (
                    "concrete_registered_composition_during_T",
                    "fun marker body h => ConcreteRegisteredTruth."
                    "concrete_registered_truth_during_T marker body h",
                ),
                (
                    "concrete_registered_composition_before_T",
                    "fun marker body h => ConcreteRegisteredTruth."
                    "concrete_registered_truth_before_T marker body h",
                ),
                (
                    "concrete_registered_composition_after_T",
                    "fun marker body h => ConcreteRegisteredTruth."
                    "concrete_registered_truth_after_T marker body h",
                ),
                (
                    "concrete_registered_composition_until_T",
                    "fun marker body h => ConcreteRegisteredTruth."
                    "concrete_registered_truth_until_T marker body h",
                ),
                (
                    "concrete_registered_composition_since_T",
                    "fun marker body h => ConcreteRegisteredTruth."
                    "concrete_registered_truth_since_T marker body h",
                ),
                (
                    "concrete_registered_composition_not_T",
                    "fun body h => ConcreteRegisteredTruth."
                    "concrete_registered_truth_not_T body h",
                ),
                (
                    "concrete_registered_composition_cause",
                    "fun causer effect h => ConcreteRegisteredTruth."
                    "concrete_registered_truth_cause causer effect h",
                ),
                (
                    "concrete_registered_composition_sound",
                    "concrete_registered_truth_implies_atomic_closure",
                ),
            ]
        )
        for index, (field, value) in enumerate(model_fields):
            suffix = "," if index < len(model_fields) - 1 else ""
            lines.append(f"  {field} := {value}{suffix}")
        lines.extend(
            [
                "}",
                "",
                "theorem concrete_registered_compositional_model_exists :",
                "    Exists (fun M : ConcreteRegisteredCompositionalModel => "
                "M = concrete_registered_compositional_model) := by",
                "  exact Exists.intro concrete_registered_compositional_model rfl",
                "",
                "theorem "
                "concrete_registered_compositional_model_denotes_concrete_registered :",
                "    (A : Type) -> (term : A) -> ConcreteRegisteredTruth A term -> "
                "concrete_registered_compositional_model."
                "concrete_registered_composition_denotes A term := by",
                "  intro A term h",
                "  exact h",
                "",
                "theorem "
                "concrete_registered_compositional_model_imply_atomic_closure :",
                "    (A : Type) -> (term : A) -> "
                "concrete_registered_compositional_model."
                "concrete_registered_composition_denotes A term -> "
                "AtomicClosureTruth A term := by",
                "  intro A term h",
                "  exact concrete_registered_compositional_model."
                "concrete_registered_composition_sound A term h",
                "",
                "theorem concrete_registered_compositional_model_repeat_clause :",
                "    (n : Nat) -> (body : PropT) -> "
                "concrete_registered_compositional_model."
                "concrete_registered_composition_denotes PropT body -> "
                "concrete_registered_compositional_model."
                "concrete_registered_composition_denotes PropT "
                "(repeat n body) := by",
                "  intro n body h",
                "  exact concrete_registered_compositional_model."
                "concrete_registered_composition_repeat n body h",
                "",
                "theorem concrete_registered_compositional_model_at_T_clause :",
                "    (marker : Entity) -> (body : PropT) -> "
                "concrete_registered_compositional_model."
                "concrete_registered_composition_denotes PropT body -> "
                "concrete_registered_compositional_model."
                "concrete_registered_composition_denotes PropT "
                "(at_T marker body) := by",
                "  intro marker body h",
                "  exact concrete_registered_compositional_model."
                "concrete_registered_composition_at_T marker body h",
                "",
                "theorem concrete_registered_compositional_model_cause_clause :",
                "    (causer : Entity) -> (effect : TransitionT) -> "
                "concrete_registered_compositional_model."
                "concrete_registered_composition_denotes TransitionT effect -> "
                "concrete_registered_compositional_model."
                "concrete_registered_composition_denotes PropT "
                "(Cause causer effect) := by",
                "  intro causer effect h",
                "  exact concrete_registered_compositional_model."
                "concrete_registered_composition_cause causer effect h",
            ]
        )
        for type_name in declarations["types"]:
            lines.extend(
                [
                    "",
                    "theorem "
                    f"concrete_registered_compositional_model_sigma_{type_name}_clause :",
                    f"    (P : {type_name} -> Prop) -> "
                    f"((x : {type_name}) -> "
                    "concrete_registered_compositional_model."
                    "concrete_registered_composition_denotes Prop (P x)) -> "
                    "concrete_registered_compositional_model."
                    "concrete_registered_composition_denotes Prop "
                    f"(Exists fun x : {type_name} => P x) := by",
                    "  intro P h",
                    "  exact concrete_registered_compositional_model."
                    f"concrete_registered_composition_sigma_{type_name} P h",
                ]
            )
        return lines

    record_fields: list[str] = [
        "  concrete_registered_composition_denotes : forall A : Type, A -> Prop;",
        "  concrete_registered_composition_atomic :",
        "      forall A : Type, forall term : A,",
        "      ConcreteRegisteredAtomicTruth A term ->",
        "      concrete_registered_composition_denotes A term;",
    ]
    for type_name in declarations["types"]:
        record_fields.extend(
            [
                f"  concrete_registered_composition_sigma_{type_name} :",
                f"      forall P : {type_name} -> Prop,",
                f"      (forall x : {type_name},",
                "        concrete_registered_composition_denotes Prop (P x)) ->",
                "      concrete_registered_composition_denotes Prop",
                f"        (exists x : {type_name}, P x);",
            ]
        )
    record_fields.extend(
        [
            "  concrete_registered_composition_repeat :",
            "      forall n : nat, forall body : PropT,",
            "      concrete_registered_composition_denotes PropT body ->",
            "      concrete_registered_composition_denotes PropT (repeat n body);",
            "  concrete_registered_composition_at_T :",
            "      forall marker : Entity, forall body : PropT,",
            "      concrete_registered_composition_denotes PropT body ->",
            "      concrete_registered_composition_denotes PropT (at_T marker body);",
            "  concrete_registered_composition_during_T :",
            "      forall marker : Entity, forall body : PropT,",
            "      concrete_registered_composition_denotes PropT body ->",
            "      concrete_registered_composition_denotes PropT (during_T marker body);",
            "  concrete_registered_composition_before_T :",
            "      forall marker : Entity, forall body : PropT,",
            "      concrete_registered_composition_denotes PropT body ->",
            "      concrete_registered_composition_denotes PropT (before_T marker body);",
            "  concrete_registered_composition_after_T :",
            "      forall marker : Entity, forall body : PropT,",
            "      concrete_registered_composition_denotes PropT body ->",
            "      concrete_registered_composition_denotes PropT (after_T marker body);",
            "  concrete_registered_composition_until_T :",
            "      forall marker : Entity, forall body : PropT,",
            "      concrete_registered_composition_denotes PropT body ->",
            "      concrete_registered_composition_denotes PropT (until_T marker body);",
            "  concrete_registered_composition_since_T :",
            "      forall marker : Entity, forall body : PropT,",
            "      concrete_registered_composition_denotes PropT body ->",
            "      concrete_registered_composition_denotes PropT (since_T marker body);",
            "  concrete_registered_composition_not_T :",
            "      forall body : PropT,",
            "      concrete_registered_composition_denotes PropT body ->",
            "      concrete_registered_composition_denotes PropT (not_T body);",
            "  concrete_registered_composition_cause :",
            "      forall causer : Entity, forall effect : TransitionT,",
            "      concrete_registered_composition_denotes TransitionT effect ->",
            "      concrete_registered_composition_denotes PropT (Cause causer effect);",
            "  concrete_registered_composition_sound :",
            "      forall A : Type, forall term : A,",
            "      concrete_registered_composition_denotes A term ->",
            "      AtomicClosureTruth A term",
        ]
    )
    lines = [
        "Record ConcreteRegisteredCompositionalModel : Type := {",
        *record_fields,
        "}.",
        "",
        "Definition concrete_registered_compositional_model :",
        "  ConcreteRegisteredCompositionalModel := {|",
        "  concrete_registered_composition_denotes := ConcreteRegisteredTruth;",
        "  concrete_registered_composition_atomic :=",
        "    fun A term h => concrete_registered_truth_atomic A term h;",
    ]
    model_fields = [
        (
            f"concrete_registered_composition_sigma_{type_name}",
            f"fun P h => concrete_registered_truth_sigma_{type_name} P h",
        )
        for type_name in declarations["types"]
    ]
    model_fields.extend(
        [
            (
                "concrete_registered_composition_repeat",
                "fun n body h => concrete_registered_truth_repeat n body h",
            ),
            (
                "concrete_registered_composition_at_T",
                "fun marker body h => concrete_registered_truth_at_T marker body h",
            ),
            (
                "concrete_registered_composition_during_T",
                "fun marker body h => concrete_registered_truth_during_T marker body h",
            ),
            (
                "concrete_registered_composition_before_T",
                "fun marker body h => concrete_registered_truth_before_T marker body h",
            ),
            (
                "concrete_registered_composition_after_T",
                "fun marker body h => concrete_registered_truth_after_T marker body h",
            ),
            (
                "concrete_registered_composition_until_T",
                "fun marker body h => concrete_registered_truth_until_T marker body h",
            ),
            (
                "concrete_registered_composition_since_T",
                "fun marker body h => concrete_registered_truth_since_T marker body h",
            ),
            (
                "concrete_registered_composition_not_T",
                "fun body h => concrete_registered_truth_not_T body h",
            ),
            (
                "concrete_registered_composition_cause",
                "fun causer effect h => concrete_registered_truth_cause causer effect h",
            ),
            (
                "concrete_registered_composition_sound",
                "concrete_registered_truth_implies_atomic_closure",
            ),
        ]
    )
    for index, (field, value) in enumerate(model_fields):
        suffix = ";" if index < len(model_fields) - 1 else ""
        lines.append(f"  {field} := {value}{suffix}")
    lines.extend(
        [
            "|}.",
            "",
            "Theorem concrete_registered_compositional_model_exists :",
            "  exists M : ConcreteRegisteredCompositionalModel,",
            "    M = concrete_registered_compositional_model.",
            "Proof.",
            "  exists concrete_registered_compositional_model. reflexivity.",
            "Qed.",
            "",
            "Theorem concrete_registered_compositional_model_denotes_concrete_registered :",
            "  forall A : Type, forall term : A,",
            "    ConcreteRegisteredTruth A term ->",
            "    concrete_registered_composition_denotes",
            "      concrete_registered_compositional_model A term.",
            "Proof.",
            "  intros A term H.",
            "  exact H.",
            "Qed.",
            "",
            "Theorem concrete_registered_compositional_model_imply_atomic_closure :",
            "  forall A : Type, forall term : A,",
            "    concrete_registered_composition_denotes",
            "      concrete_registered_compositional_model A term ->",
            "    AtomicClosureTruth A term.",
            "Proof.",
            "  intros A term H.",
            "  exact (concrete_registered_composition_sound",
            "    concrete_registered_compositional_model A term H).",
            "Qed.",
            "",
            "Theorem concrete_registered_compositional_model_repeat_clause :",
            "  forall n : nat, forall body : PropT,",
            "    concrete_registered_composition_denotes",
            "      concrete_registered_compositional_model PropT body ->",
            "    concrete_registered_composition_denotes",
            "      concrete_registered_compositional_model PropT (repeat n body).",
            "Proof.",
            "  intros n body H.",
            "  exact (concrete_registered_composition_repeat",
            "    concrete_registered_compositional_model n body H).",
            "Qed.",
            "",
            "Theorem concrete_registered_compositional_model_at_T_clause :",
            "  forall marker : Entity, forall body : PropT,",
            "    concrete_registered_composition_denotes",
            "      concrete_registered_compositional_model PropT body ->",
            "    concrete_registered_composition_denotes",
            "      concrete_registered_compositional_model PropT (at_T marker body).",
            "Proof.",
            "  intros marker body H.",
            "  exact (concrete_registered_composition_at_T",
            "    concrete_registered_compositional_model marker body H).",
            "Qed.",
            "",
            "Theorem concrete_registered_compositional_model_cause_clause :",
            "  forall causer : Entity, forall effect : TransitionT,",
            "    concrete_registered_composition_denotes",
            "      concrete_registered_compositional_model TransitionT effect ->",
            "    concrete_registered_composition_denotes",
            "      concrete_registered_compositional_model PropT (Cause causer effect).",
            "Proof.",
            "  intros causer effect H.",
            "  exact (concrete_registered_composition_cause",
            "    concrete_registered_compositional_model causer effect H).",
            "Qed.",
        ]
    )
    for type_name in declarations["types"]:
        lines.extend(
            [
                "",
                "Theorem "
                f"concrete_registered_compositional_model_sigma_{type_name}_clause :",
                f"  forall P : {type_name} -> Prop,",
                f"    (forall x : {type_name},",
                "      concrete_registered_composition_denotes",
                "        concrete_registered_compositional_model Prop (P x)) ->",
                "    concrete_registered_composition_denotes",
                "      concrete_registered_compositional_model Prop",
                f"      (exists x : {type_name}, P x).",
                "Proof.",
                "  intros P H.",
                "  exact ("
                f"concrete_registered_composition_sigma_{type_name} "
                "concrete_registered_compositional_model P H).",
                "Qed.",
            ]
        )
    return lines


def concrete_registered_truth_condition_instance_lines(
    declarations: dict[str, Any],
    target: str,
) -> list[str]:
    if target == "lean":
        lines = [
            "inductive ConcreteRegisteredAtomicTruth : (A : Type) -> A -> Prop where",
            "  | concrete_registered_atomic_truth_lexical_application : "
            "(A : Type) -> (term : A) -> "
            "RegisteredLexicalApplicationTruth A term -> "
            "ConcreteRegisteredAtomicTruth A term",
            "  | concrete_registered_atomic_truth_transition : "
            "(theme : Entity) -> (scale : StateScale) -> "
            "(source : State) -> (target : State) -> "
            "RegisteredStateTransitionTruth theme scale source target -> "
            "ConcreteRegisteredAtomicTruth TransitionT "
            "(Transition theme scale source target)",
            "",
            "structure ConcreteRegisteredTruthBasis : Type where",
            "  concrete_registered_basis_denotes : (A : Type) -> A -> Prop",
            "  concrete_registered_basis_lexical_application : "
            "(A : Type) -> (term : A) -> "
            "RegisteredLexicalApplicationTruth A term -> "
            "concrete_registered_basis_denotes A term",
            "  concrete_registered_basis_transition : "
            "(theme : Entity) -> (scale : StateScale) -> "
            "(source : State) -> (target : State) -> "
            "RegisteredStateTransitionTruth theme scale source target -> "
            "concrete_registered_basis_denotes TransitionT "
            "(Transition theme scale source target)",
            "",
            "def concrete_registered_truth_basis : ConcreteRegisteredTruthBasis := {",
            "  concrete_registered_basis_denotes := ConcreteRegisteredAtomicTruth,",
            "  concrete_registered_basis_lexical_application := "
            "fun A term h => ConcreteRegisteredAtomicTruth."
            "concrete_registered_atomic_truth_lexical_application A term h,",
            "  concrete_registered_basis_transition := "
            "fun theme scale source target h => ConcreteRegisteredAtomicTruth."
            "concrete_registered_atomic_truth_transition "
            "theme scale source target h",
            "}",
            "",
            "theorem concrete_registered_truth_basis_exists :",
            "    Exists (fun B : ConcreteRegisteredTruthBasis => "
            "B = concrete_registered_truth_basis) := by",
            "  exact Exists.intro concrete_registered_truth_basis rfl",
            "",
            "theorem concrete_registered_atomic_truth_implies_atomic_base_truth :",
            "    (A : Type) -> (term : A) -> "
            "ConcreteRegisteredAtomicTruth A term -> AtomicBaseTruth A term := by",
            "  intro A term h",
            "  induction h",
            "  | concrete_registered_atomic_truth_lexical_application A term hreg =>",
            "      apply registered_lexical_application_atomic_base_truth",
            "      exact hreg",
            "  | concrete_registered_atomic_truth_transition theme scale source target hreg =>",
            "      apply registered_state_transition_atomic_base_truth",
            "      exact hreg",
            "",
            "structure ConcreteRegisteredAtomicModel : Type where",
            "  concrete_registered_atom_model_denotes : (A : Type) -> A -> Prop",
            "  concrete_registered_atom_model_lexical_application : "
            "(A : Type) -> (term : A) -> "
            "RegisteredLexicalApplicationTruth A term -> "
            "concrete_registered_atom_model_denotes A term",
            "  concrete_registered_atom_model_transition : "
            "(theme : Entity) -> (scale : StateScale) -> "
            "(source : State) -> (target : State) -> "
            "RegisteredStateTransitionTruth theme scale source target -> "
            "concrete_registered_atom_model_denotes TransitionT "
            "(Transition theme scale source target)",
            "  concrete_registered_atom_model_sound : "
            "(A : Type) -> (term : A) -> "
            "concrete_registered_atom_model_denotes A term -> "
            "AtomicBaseTruth A term",
            "",
            "def concrete_registered_atomic_model : "
            "ConcreteRegisteredAtomicModel := {",
            "  concrete_registered_atom_model_denotes := "
            "ConcreteRegisteredAtomicTruth,",
            "  concrete_registered_atom_model_lexical_application := "
            "fun A term h => ConcreteRegisteredAtomicTruth."
            "concrete_registered_atomic_truth_lexical_application A term h,",
            "  concrete_registered_atom_model_transition := "
            "fun theme scale source target h => ConcreteRegisteredAtomicTruth."
            "concrete_registered_atomic_truth_transition "
            "theme scale source target h,",
            "  concrete_registered_atom_model_sound := "
            "concrete_registered_atomic_truth_implies_atomic_base_truth",
            "}",
            "",
            "theorem concrete_registered_atomic_model_exists :",
            "    Exists (fun M : ConcreteRegisteredAtomicModel => "
            "M = concrete_registered_atomic_model) := by",
            "  exact Exists.intro concrete_registered_atomic_model rfl",
            "",
            "theorem concrete_registered_atomic_model_denotes_atomic_base_truth :",
            "    (A : Type) -> (term : A) -> "
            "concrete_registered_atomic_model."
            "concrete_registered_atom_model_denotes A term -> "
            "AtomicBaseTruth A term := by",
            "  intro A term h",
            "  exact concrete_registered_atomic_model."
            "concrete_registered_atom_model_sound A term h",
            "",
            "theorem concrete_registered_truth_basis_denotes_atomic_base_truth :",
            "    (A : Type) -> (term : A) -> "
            "concrete_registered_truth_basis."
            "concrete_registered_basis_denotes A term -> "
            "AtomicBaseTruth A term := by",
            "  intro A term h",
            "  exact concrete_registered_atomic_truth_implies_atomic_base_truth A term h",
            "",
            "inductive ConcreteRegisteredTruth : (A : Type) -> A -> Prop where",
            "  | concrete_registered_truth_atomic : "
            "(A : Type) -> (term : A) -> "
            "ConcreteRegisteredAtomicTruth A term -> ConcreteRegisteredTruth A term",
        ]
        for type_name in declarations["types"]:
            lines.append(
                f"  | concrete_registered_truth_sigma_{type_name} : "
                f"(P : {type_name} -> Prop) -> "
                f"((x : {type_name}) -> ConcreteRegisteredTruth Prop (P x)) -> "
                f"ConcreteRegisteredTruth Prop (Exists fun x : {type_name} => P x)"
            )
        lines.extend(
            [
                "  | concrete_registered_truth_repeat : (n : Nat) -> "
                "(body : PropT) -> ConcreteRegisteredTruth PropT body -> "
                "ConcreteRegisteredTruth PropT (repeat n body)",
                "  | concrete_registered_truth_at_T : (marker : Entity) -> "
                "(body : PropT) -> ConcreteRegisteredTruth PropT body -> "
                "ConcreteRegisteredTruth PropT (at_T marker body)",
                "  | concrete_registered_truth_during_T : (marker : Entity) -> "
                "(body : PropT) -> ConcreteRegisteredTruth PropT body -> "
                "ConcreteRegisteredTruth PropT (during_T marker body)",
                "  | concrete_registered_truth_before_T : (marker : Entity) -> "
                "(body : PropT) -> ConcreteRegisteredTruth PropT body -> "
                "ConcreteRegisteredTruth PropT (before_T marker body)",
                "  | concrete_registered_truth_after_T : (marker : Entity) -> "
                "(body : PropT) -> ConcreteRegisteredTruth PropT body -> "
                "ConcreteRegisteredTruth PropT (after_T marker body)",
                "  | concrete_registered_truth_until_T : (marker : Entity) -> "
                "(body : PropT) -> ConcreteRegisteredTruth PropT body -> "
                "ConcreteRegisteredTruth PropT (until_T marker body)",
                "  | concrete_registered_truth_since_T : (marker : Entity) -> "
                "(body : PropT) -> ConcreteRegisteredTruth PropT body -> "
                "ConcreteRegisteredTruth PropT (since_T marker body)",
                "  | concrete_registered_truth_not_T : (body : PropT) -> "
                "ConcreteRegisteredTruth PropT body -> "
                "ConcreteRegisteredTruth PropT (not_T body)",
                "  | concrete_registered_truth_cause : (causer : Entity) -> "
                "(effect : TransitionT) -> "
                "ConcreteRegisteredTruth TransitionT effect -> "
                "ConcreteRegisteredTruth PropT (Cause causer effect)",
                "",
                "theorem concrete_registered_truth_implies_fully_registered :",
                "    (A : Type) -> (term : A) -> ConcreteRegisteredTruth A term -> "
                "FullyRegisteredAtomicClosureTruth A term := by",
                "  intro A term h",
                "  induction h",
                "  | concrete_registered_truth_atomic A term hatom =>",
                "      induction hatom",
                "      | concrete_registered_atomic_truth_lexical_application A term hreg =>",
                "          apply FullyRegisteredAtomicClosureTruth."
                "fully_registered_atomic_truth_lexical_application",
                "          exact hreg",
                "      | concrete_registered_atomic_truth_transition theme scale source target hreg =>",
                "          apply FullyRegisteredAtomicClosureTruth."
                "fully_registered_atomic_truth_transition",
                "          exact hreg",
            ]
        )
        for type_name in declarations["types"]:
            lines.append(
                f"  | concrete_registered_truth_sigma_{type_name} P h ih => "
                "exact FullyRegisteredAtomicClosureTruth."
                f"fully_registered_atomic_truth_sigma_{type_name} P ih"
            )
        lines.extend(
            [
                "  | concrete_registered_truth_repeat n body h ih => "
                "exact FullyRegisteredAtomicClosureTruth."
                "fully_registered_atomic_truth_repeat n body ih",
                "  | concrete_registered_truth_at_T marker body h ih => "
                "exact FullyRegisteredAtomicClosureTruth."
                "fully_registered_atomic_truth_at_T marker body ih",
                "  | concrete_registered_truth_during_T marker body h ih => "
                "exact FullyRegisteredAtomicClosureTruth."
                "fully_registered_atomic_truth_during_T marker body ih",
                "  | concrete_registered_truth_before_T marker body h ih => "
                "exact FullyRegisteredAtomicClosureTruth."
                "fully_registered_atomic_truth_before_T marker body ih",
                "  | concrete_registered_truth_after_T marker body h ih => "
                "exact FullyRegisteredAtomicClosureTruth."
                "fully_registered_atomic_truth_after_T marker body ih",
                "  | concrete_registered_truth_until_T marker body h ih => "
                "exact FullyRegisteredAtomicClosureTruth."
                "fully_registered_atomic_truth_until_T marker body ih",
                "  | concrete_registered_truth_since_T marker body h ih => "
                "exact FullyRegisteredAtomicClosureTruth."
                "fully_registered_atomic_truth_since_T marker body ih",
                "  | concrete_registered_truth_not_T body h ih => "
                "exact FullyRegisteredAtomicClosureTruth."
                "fully_registered_atomic_truth_not_T body ih",
                "  | concrete_registered_truth_cause causer effect h ih => "
                "exact FullyRegisteredAtomicClosureTruth."
                "fully_registered_atomic_truth_cause causer effect ih",
                "",
                "theorem concrete_registered_truth_implies_atomic_closure :",
                "    (A : Type) -> (term : A) -> ConcreteRegisteredTruth A term -> "
                "AtomicClosureTruth A term := by",
                "  intro A term h",
                "  apply fully_registered_atomic_closure_truth_implies_atomic_closure_truth",
                "  apply concrete_registered_truth_implies_fully_registered",
                "  exact h",
                "",
                "def concrete_registered_truth_denotes : (A : Type) -> A -> Prop :=",
                "  ConcreteRegisteredTruth",
                "",
                "def concrete_registered_truth_conditions : "
                "FullyRegisteredTruthConditionSpec := {",
                "  fully_registered_truth_denotes := concrete_registered_truth_denotes,",
                "  fully_registered_truth_lexical_application := "
                "fun A term h => ConcreteRegisteredTruth."
                "concrete_registered_truth_atomic A term "
                "(ConcreteRegisteredAtomicTruth."
                "concrete_registered_atomic_truth_lexical_application A term h),",
            ]
        )
        fields: list[tuple[str, str]] = []
        for type_name in declarations["types"]:
            fields.append(
                (
                    f"fully_registered_truth_sigma_{type_name}",
                    "fun P h => ConcreteRegisteredTruth."
                    f"concrete_registered_truth_sigma_{type_name} P h",
                )
            )
        fields.extend(
            [
                ("fully_registered_truth_repeat", "fun n body h => ConcreteRegisteredTruth.concrete_registered_truth_repeat n body h"),
                ("fully_registered_truth_at_T", "fun marker body h => ConcreteRegisteredTruth.concrete_registered_truth_at_T marker body h"),
                ("fully_registered_truth_during_T", "fun marker body h => ConcreteRegisteredTruth.concrete_registered_truth_during_T marker body h"),
                ("fully_registered_truth_before_T", "fun marker body h => ConcreteRegisteredTruth.concrete_registered_truth_before_T marker body h"),
                ("fully_registered_truth_after_T", "fun marker body h => ConcreteRegisteredTruth.concrete_registered_truth_after_T marker body h"),
                ("fully_registered_truth_until_T", "fun marker body h => ConcreteRegisteredTruth.concrete_registered_truth_until_T marker body h"),
                ("fully_registered_truth_since_T", "fun marker body h => ConcreteRegisteredTruth.concrete_registered_truth_since_T marker body h"),
                ("fully_registered_truth_not_T", "fun body h => ConcreteRegisteredTruth.concrete_registered_truth_not_T body h"),
                (
                    "fully_registered_truth_transition",
                    "fun theme scale source target h => ConcreteRegisteredTruth."
                    "concrete_registered_truth_atomic TransitionT "
                    "(Transition theme scale source target) "
                    "(ConcreteRegisteredAtomicTruth."
                    "concrete_registered_atomic_truth_transition "
                    "theme scale source target h)",
                ),
                ("fully_registered_truth_cause", "fun causer effect h => ConcreteRegisteredTruth.concrete_registered_truth_cause causer effect h"),
            ]
        )
        for index, (field, value) in enumerate(fields):
            suffix = "," if index < len(fields) - 1 else ""
            lines.append(f"  {field} := {value}{suffix}")
        lines.extend(
            [
                "}",
                "",
                "theorem concrete_registered_truth_condition_spec_exists :",
                "    Exists (fun F : FullyRegisteredTruthConditionSpec => "
                "F = concrete_registered_truth_conditions) := by",
                "  exact Exists.intro concrete_registered_truth_conditions rfl",
                "",
                "theorem concrete_registered_truth_conditions_denote_concrete_registered :",
                "    (A : Type) -> (term : A) -> ConcreteRegisteredTruth A term -> "
                "concrete_registered_truth_conditions."
                "fully_registered_truth_denotes A term := by",
                "  intro A term h",
                "  exact h",
                "",
                "theorem concrete_registered_truth_conditions_imply_fully_registered :",
                "    (A : Type) -> (term : A) -> "
                "concrete_registered_truth_conditions."
                "fully_registered_truth_denotes A term -> "
                "FullyRegisteredAtomicClosureTruth A term := by",
                "  intro A term h",
                "  apply concrete_registered_truth_implies_fully_registered",
                "  exact h",
                "",
                "theorem concrete_registered_truth_conditions_imply_atomic_closure :",
                "    (A : Type) -> (term : A) -> "
                "concrete_registered_truth_conditions."
                "fully_registered_truth_denotes A term -> AtomicClosureTruth A term := by",
                "  intro A term h",
                "  apply concrete_registered_truth_implies_atomic_closure",
                "  exact h",
                "",
            ]
        )
        lines.extend(concrete_registered_compositional_model_lines(declarations, target))
        lines.extend(
            [
                "structure ConcreteRegisteredTruthConditionModel : Type where",
                "  concrete_registered_model_denotes : (A : Type) -> A -> Prop",
                "  concrete_registered_model_spec : FullyRegisteredTruthConditionSpec",
                "  concrete_registered_model_denote_spec : "
                "(A : Type) -> (term : A) -> "
                "concrete_registered_model_denotes A term -> "
                "concrete_registered_model_spec."
                "fully_registered_truth_denotes A term",
                "  concrete_registered_model_sound : "
                "(A : Type) -> (term : A) -> "
                "concrete_registered_model_denotes A term -> "
                "AtomicClosureTruth A term",
                "",
                "def concrete_registered_truth_condition_model : "
                "ConcreteRegisteredTruthConditionModel := {",
                "  concrete_registered_model_denotes := ConcreteRegisteredTruth,",
                "  concrete_registered_model_spec := concrete_registered_truth_conditions,",
                "  concrete_registered_model_denote_spec := fun A term h => h,",
                "  concrete_registered_model_sound := "
                "concrete_registered_truth_implies_atomic_closure,",
                "}",
                "",
                "theorem concrete_registered_truth_condition_model_exists :",
                "    Exists (fun M : ConcreteRegisteredTruthConditionModel => "
                "M = concrete_registered_truth_condition_model) := by",
                "  exact Exists.intro concrete_registered_truth_condition_model rfl",
                "",
                "theorem concrete_registered_truth_condition_model_denote_spec :",
                "    (A : Type) -> (term : A) -> "
                "concrete_registered_truth_condition_model."
                "concrete_registered_model_denotes A term -> "
                "concrete_registered_truth_condition_model."
                "concrete_registered_model_spec."
                "fully_registered_truth_denotes A term := by",
                "  intro A term h",
                "  exact concrete_registered_truth_condition_model."
                "concrete_registered_model_denote_spec A term h",
                "",
                "theorem concrete_registered_truth_condition_model_imply_atomic_closure :",
                "    (A : Type) -> (term : A) -> "
                "concrete_registered_truth_condition_model."
                "concrete_registered_model_denotes A term -> "
                "AtomicClosureTruth A term := by",
                "  intro A term h",
                "  exact concrete_registered_truth_condition_model."
                "concrete_registered_model_sound A term h",
                "",
                "theorem "
                "concrete_registered_truth_condition_model_spec_imply_atomic_closure :",
                "    (A : Type) -> (term : A) -> "
                "concrete_registered_truth_condition_model."
                "concrete_registered_model_spec."
                "fully_registered_truth_denotes A term -> "
                "AtomicClosureTruth A term := by",
                "  intro A term h",
                "  apply concrete_registered_truth_conditions_imply_atomic_closure",
                "  exact h",
            ]
        )
        return lines

    lines = [
        "Inductive ConcreteRegisteredAtomicTruth : forall A : Type, A -> Prop :=",
        "  | concrete_registered_atomic_truth_lexical_application :",
        "      forall A : Type, forall term : A,",
        "      RegisteredLexicalApplicationTruth A term ->",
        "      ConcreteRegisteredAtomicTruth A term",
        "  | concrete_registered_atomic_truth_transition :",
        "      forall theme : Entity, forall scale : StateScale,",
        "      forall source : State, forall target : State,",
        "      RegisteredStateTransitionTruth theme scale source target ->",
        "      ConcreteRegisteredAtomicTruth TransitionT",
        "        (Transition theme scale source target).",
        "",
        "Record ConcreteRegisteredTruthBasis : Type := {",
        "  concrete_registered_basis_denotes : forall A : Type, A -> Prop;",
        "  concrete_registered_basis_lexical_application :",
        "      forall A : Type, forall term : A,",
        "      RegisteredLexicalApplicationTruth A term ->",
        "      concrete_registered_basis_denotes A term;",
        "  concrete_registered_basis_transition :",
        "      forall theme : Entity, forall scale : StateScale,",
        "      forall source : State, forall target : State,",
        "      RegisteredStateTransitionTruth theme scale source target ->",
        "      concrete_registered_basis_denotes TransitionT",
        "        (Transition theme scale source target)",
        "}.",
        "",
        "Definition concrete_registered_truth_basis :",
        "  ConcreteRegisteredTruthBasis := {|",
        "  concrete_registered_basis_denotes := ConcreteRegisteredAtomicTruth;",
        "  concrete_registered_basis_lexical_application :=",
        "    fun A term h =>",
        "      concrete_registered_atomic_truth_lexical_application A term h;",
        "  concrete_registered_basis_transition :=",
        "    fun theme scale source target h =>",
        "      concrete_registered_atomic_truth_transition theme scale source target h",
        "|}.",
        "",
        "Theorem concrete_registered_truth_basis_exists :",
        "  exists B : ConcreteRegisteredTruthBasis,",
        "    B = concrete_registered_truth_basis.",
        "Proof.",
        "  exists concrete_registered_truth_basis. reflexivity.",
        "Qed.",
        "",
        "Theorem concrete_registered_atomic_truth_implies_atomic_base_truth :",
        "  forall A : Type, forall term : A,",
        "    ConcreteRegisteredAtomicTruth A term -> AtomicBaseTruth A term.",
        "Proof.",
        "  intros A term H.",
        "  induction H.",
        "  - apply registered_lexical_application_atomic_base_truth.",
        "    assumption.",
        "  - apply registered_state_transition_atomic_base_truth.",
        "    assumption.",
        "Qed.",
        "",
        "Record ConcreteRegisteredAtomicModel : Type := {",
        "  concrete_registered_atom_model_denotes : forall A : Type, A -> Prop;",
        "  concrete_registered_atom_model_lexical_application :",
        "      forall A : Type, forall term : A,",
        "      RegisteredLexicalApplicationTruth A term ->",
        "      concrete_registered_atom_model_denotes A term;",
        "  concrete_registered_atom_model_transition :",
        "      forall theme : Entity, forall scale : StateScale,",
        "      forall source : State, forall target : State,",
        "      RegisteredStateTransitionTruth theme scale source target ->",
        "      concrete_registered_atom_model_denotes TransitionT",
        "        (Transition theme scale source target);",
        "  concrete_registered_atom_model_sound :",
        "      forall A : Type, forall term : A,",
        "      concrete_registered_atom_model_denotes A term ->",
        "      AtomicBaseTruth A term",
        "}.",
        "",
        "Definition concrete_registered_atomic_model :",
        "  ConcreteRegisteredAtomicModel := {|",
        "  concrete_registered_atom_model_denotes := ConcreteRegisteredAtomicTruth;",
        "  concrete_registered_atom_model_lexical_application :=",
        "    fun A term h =>",
        "      concrete_registered_atomic_truth_lexical_application A term h;",
        "  concrete_registered_atom_model_transition :=",
        "    fun theme scale source target h =>",
        "      concrete_registered_atomic_truth_transition theme scale source target h;",
        "  concrete_registered_atom_model_sound :=",
        "    concrete_registered_atomic_truth_implies_atomic_base_truth",
        "|}.",
        "",
        "Theorem concrete_registered_atomic_model_exists :",
        "  exists M : ConcreteRegisteredAtomicModel,",
        "    M = concrete_registered_atomic_model.",
        "Proof.",
        "  exists concrete_registered_atomic_model. reflexivity.",
        "Qed.",
        "",
        "Theorem concrete_registered_atomic_model_denotes_atomic_base_truth :",
        "  forall A : Type, forall term : A,",
        "    concrete_registered_atom_model_denotes",
        "      concrete_registered_atomic_model A term ->",
        "    AtomicBaseTruth A term.",
        "Proof.",
        "  intros A term H.",
        "  exact (concrete_registered_atom_model_sound",
        "    concrete_registered_atomic_model A term H).",
        "Qed.",
        "",
        "Theorem concrete_registered_truth_basis_denotes_atomic_base_truth :",
        "  forall A : Type, forall term : A,",
        "    concrete_registered_basis_denotes concrete_registered_truth_basis A term ->",
        "    AtomicBaseTruth A term.",
        "Proof.",
        "  intros A term H.",
        "  apply concrete_registered_atomic_truth_implies_atomic_base_truth.",
        "  exact H.",
        "Qed.",
        "",
        "Inductive ConcreteRegisteredTruth : forall A : Type, A -> Prop :=",
        "  | concrete_registered_truth_atomic :",
        "      forall A : Type, forall term : A,",
        "      ConcreteRegisteredAtomicTruth A term ->",
        "      ConcreteRegisteredTruth A term",
    ]
    for type_name in declarations["types"]:
        lines.extend(
            [
                f"  | concrete_registered_truth_sigma_{type_name} : "
                f"forall P : {type_name} -> Prop,",
                f"      (forall x : {type_name}, "
                "ConcreteRegisteredTruth Prop (P x)) ->",
                "      ConcreteRegisteredTruth Prop "
                f"(exists x : {type_name}, P x)",
            ]
        )
    lines.extend(
        [
            "  | concrete_registered_truth_repeat : "
            "forall n : nat, forall body : PropT,",
            "      ConcreteRegisteredTruth PropT body ->",
            "      ConcreteRegisteredTruth PropT (repeat n body)",
            "  | concrete_registered_truth_at_T : "
            "forall marker : Entity, forall body : PropT,",
            "      ConcreteRegisteredTruth PropT body ->",
            "      ConcreteRegisteredTruth PropT (at_T marker body)",
            "  | concrete_registered_truth_during_T : "
            "forall marker : Entity, forall body : PropT,",
            "      ConcreteRegisteredTruth PropT body ->",
            "      ConcreteRegisteredTruth PropT (during_T marker body)",
            "  | concrete_registered_truth_before_T : "
            "forall marker : Entity, forall body : PropT,",
            "      ConcreteRegisteredTruth PropT body ->",
            "      ConcreteRegisteredTruth PropT (before_T marker body)",
            "  | concrete_registered_truth_after_T : "
            "forall marker : Entity, forall body : PropT,",
            "      ConcreteRegisteredTruth PropT body ->",
            "      ConcreteRegisteredTruth PropT (after_T marker body)",
            "  | concrete_registered_truth_until_T : "
            "forall marker : Entity, forall body : PropT,",
            "      ConcreteRegisteredTruth PropT body ->",
            "      ConcreteRegisteredTruth PropT (until_T marker body)",
            "  | concrete_registered_truth_since_T : "
            "forall marker : Entity, forall body : PropT,",
            "      ConcreteRegisteredTruth PropT body ->",
            "      ConcreteRegisteredTruth PropT (since_T marker body)",
            "  | concrete_registered_truth_not_T : forall body : PropT,",
            "      ConcreteRegisteredTruth PropT body ->",
            "      ConcreteRegisteredTruth PropT (not_T body)",
            "  | concrete_registered_truth_cause :",
            "      forall causer : Entity, forall effect : TransitionT,",
            "      ConcreteRegisteredTruth TransitionT effect ->",
            "      ConcreteRegisteredTruth PropT (Cause causer effect).",
            "",
            "Theorem concrete_registered_truth_implies_fully_registered :",
            "  forall A : Type, forall term : A,",
            "    ConcreteRegisteredTruth A term ->",
            "    FullyRegisteredAtomicClosureTruth A term.",
            "Proof.",
            "  intros A term H.",
            "  induction H.",
            "  - induction H.",
            "    + apply fully_registered_atomic_truth_lexical_application.",
            "      assumption.",
            "    + apply fully_registered_atomic_truth_transition.",
            "      assumption.",
        ]
    )
    for type_name in declarations["types"]:
        lines.append(f"  - apply fully_registered_atomic_truth_sigma_{type_name}.")
        lines.append("    assumption.")
    lines.extend(
        [
            "  - apply fully_registered_atomic_truth_repeat. assumption.",
            "  - apply fully_registered_atomic_truth_at_T. assumption.",
            "  - apply fully_registered_atomic_truth_during_T. assumption.",
            "  - apply fully_registered_atomic_truth_before_T. assumption.",
            "  - apply fully_registered_atomic_truth_after_T. assumption.",
            "  - apply fully_registered_atomic_truth_until_T. assumption.",
            "  - apply fully_registered_atomic_truth_since_T. assumption.",
            "  - apply fully_registered_atomic_truth_not_T. assumption.",
            "  - apply fully_registered_atomic_truth_cause. assumption.",
            "Qed.",
            "",
            "Theorem concrete_registered_truth_implies_atomic_closure :",
            "  forall A : Type, forall term : A,",
            "    ConcreteRegisteredTruth A term -> AtomicClosureTruth A term.",
            "Proof.",
            "  intros A term H.",
            "  apply fully_registered_atomic_closure_truth_implies_atomic_closure_truth.",
            "  apply concrete_registered_truth_implies_fully_registered.",
            "  exact H.",
            "Qed.",
            "",
            "Definition concrete_registered_truth_denotes : "
            "forall A : Type, A -> Prop :=",
            "  ConcreteRegisteredTruth.",
            "",
            "Definition concrete_registered_truth_conditions : "
            "FullyRegisteredTruthConditionSpec := {|",
            "  fully_registered_truth_denotes := "
            "concrete_registered_truth_denotes;",
            "  fully_registered_truth_lexical_application :=",
            "    fun A term h => concrete_registered_truth_atomic A term",
            "      (concrete_registered_atomic_truth_lexical_application A term h);",
        ]
    )
    fields: list[tuple[str, str]] = []
    for type_name in declarations["types"]:
        fields.append(
            (
                f"fully_registered_truth_sigma_{type_name}",
                f"fun P h => concrete_registered_truth_sigma_{type_name} P h",
            )
        )
    fields.extend(
        [
            ("fully_registered_truth_repeat", "fun n body h => concrete_registered_truth_repeat n body h"),
            ("fully_registered_truth_at_T", "fun marker body h => concrete_registered_truth_at_T marker body h"),
            ("fully_registered_truth_during_T", "fun marker body h => concrete_registered_truth_during_T marker body h"),
            ("fully_registered_truth_before_T", "fun marker body h => concrete_registered_truth_before_T marker body h"),
            ("fully_registered_truth_after_T", "fun marker body h => concrete_registered_truth_after_T marker body h"),
            ("fully_registered_truth_until_T", "fun marker body h => concrete_registered_truth_until_T marker body h"),
            ("fully_registered_truth_since_T", "fun marker body h => concrete_registered_truth_since_T marker body h"),
            ("fully_registered_truth_not_T", "fun body h => concrete_registered_truth_not_T body h"),
            (
                "fully_registered_truth_transition",
                "fun theme scale source target h => "
                "concrete_registered_truth_atomic TransitionT "
                "(Transition theme scale source target) "
                "(concrete_registered_atomic_truth_transition "
                "theme scale source target h)",
            ),
            ("fully_registered_truth_cause", "fun causer effect h => concrete_registered_truth_cause causer effect h"),
        ]
    )
    for index, (field, value) in enumerate(fields):
        suffix = ";" if index < len(fields) - 1 else ""
        lines.append(f"  {field} := {value}{suffix}")
    lines.extend(
        [
            "|}.",
            "",
            "Theorem concrete_registered_truth_condition_spec_exists :",
            "  exists F : FullyRegisteredTruthConditionSpec,",
            "    F = concrete_registered_truth_conditions.",
            "Proof.",
            "  exists concrete_registered_truth_conditions. reflexivity.",
            "Qed.",
            "",
            "Theorem concrete_registered_truth_conditions_denote_concrete_registered :",
            "  forall A : Type, forall term : A,",
            "    ConcreteRegisteredTruth A term ->",
            "    fully_registered_truth_denotes "
            "concrete_registered_truth_conditions A term.",
            "Proof.",
            "  intros A term H.",
            "  exact H.",
            "Qed.",
            "",
            "Theorem concrete_registered_truth_conditions_imply_fully_registered :",
            "  forall A : Type, forall term : A,",
            "    fully_registered_truth_denotes "
            "concrete_registered_truth_conditions A term ->",
            "    FullyRegisteredAtomicClosureTruth A term.",
            "Proof.",
            "  intros A term H.",
            "  apply concrete_registered_truth_implies_fully_registered.",
            "  exact H.",
            "Qed.",
            "",
            "Theorem concrete_registered_truth_conditions_imply_atomic_closure :",
            "  forall A : Type, forall term : A,",
            "    fully_registered_truth_denotes "
            "concrete_registered_truth_conditions A term ->",
            "    AtomicClosureTruth A term.",
            "Proof.",
            "  intros A term H.",
            "  apply concrete_registered_truth_implies_atomic_closure.",
            "  exact H.",
            "Qed.",
            "",
        ]
    )
    lines.extend(concrete_registered_compositional_model_lines(declarations, target))
    lines.extend(
        [
            "Record ConcreteRegisteredTruthConditionModel : Type := {",
            "  concrete_registered_model_denotes : forall A : Type, A -> Prop;",
            "  concrete_registered_model_spec : FullyRegisteredTruthConditionSpec;",
            "  concrete_registered_model_denote_spec :",
            "      forall A : Type, forall term : A,",
            "      concrete_registered_model_denotes A term ->",
            "      fully_registered_truth_denotes",
            "        concrete_registered_model_spec A term;",
            "  concrete_registered_model_sound :",
            "      forall A : Type, forall term : A,",
            "      concrete_registered_model_denotes A term ->",
            "      AtomicClosureTruth A term",
            "}.",
            "",
            "Definition concrete_registered_truth_condition_model :",
            "  ConcreteRegisteredTruthConditionModel := {|",
            "  concrete_registered_model_denotes := ConcreteRegisteredTruth;",
            "  concrete_registered_model_spec := concrete_registered_truth_conditions;",
            "  concrete_registered_model_denote_spec := fun A term h => h;",
            "  concrete_registered_model_sound :=",
            "    concrete_registered_truth_implies_atomic_closure",
            "|}.",
            "",
            "Theorem concrete_registered_truth_condition_model_exists :",
            "  exists M : ConcreteRegisteredTruthConditionModel,",
            "    M = concrete_registered_truth_condition_model.",
            "Proof.",
            "  exists concrete_registered_truth_condition_model. reflexivity.",
            "Qed.",
            "",
            "Theorem concrete_registered_truth_condition_model_denote_spec :",
            "  forall A : Type, forall term : A,",
            "    concrete_registered_model_denotes",
            "      concrete_registered_truth_condition_model A term ->",
            "    fully_registered_truth_denotes",
            "      (concrete_registered_model_spec",
            "        concrete_registered_truth_condition_model) A term.",
            "Proof.",
            "  intros A term H.",
            "  exact (concrete_registered_model_denote_spec",
            "    concrete_registered_truth_condition_model A term H).",
            "Qed.",
            "",
            "Theorem concrete_registered_truth_condition_model_imply_atomic_closure :",
            "  forall A : Type, forall term : A,",
            "    concrete_registered_model_denotes",
            "      concrete_registered_truth_condition_model A term ->",
            "    AtomicClosureTruth A term.",
            "Proof.",
            "  intros A term H.",
            "  exact (concrete_registered_model_sound",
            "    concrete_registered_truth_condition_model A term H).",
            "Qed.",
            "",
            "Theorem concrete_registered_truth_condition_model_spec_imply_atomic_closure :",
            "  forall A : Type, forall term : A,",
            "    fully_registered_truth_denotes",
            "      (concrete_registered_model_spec",
            "        concrete_registered_truth_condition_model) A term ->",
            "    AtomicClosureTruth A term.",
            "Proof.",
            "  intros A term H.",
            "  apply concrete_registered_truth_conditions_imply_atomic_closure.",
            "  exact H.",
            "Qed.",
        ]
    )
    return lines


def registered_evidence_backed_truth_condition_source_lines(
    declarations: dict[str, Any],
    target: str,
) -> list[str]:
    if target == "lean":
        lines = [
            "structure RegisteredEvidenceBackedTruthConditionSources : Type where",
            "  registered_evidence_denotes : (A : Type) -> A -> Prop",
            "  registered_evidence_lexical_application : "
            "(A : Type) -> (term : A) -> "
            "RegisteredLexicalApplicationTruth A term -> "
            "TruthEvidence (registered_evidence_denotes A term)",
        ]
        for type_name in declarations["types"]:
            lines.append(
                f"  registered_evidence_sigma_{type_name} : "
                f"(P : {type_name} -> Prop) -> "
                f"((x : {type_name}) -> registered_evidence_denotes Prop (P x)) -> "
                "TruthEvidence "
                f"(registered_evidence_denotes Prop (Exists fun x : {type_name} => P x))"
            )
        lines.extend(
            [
                "  registered_evidence_repeat : (n : Nat) -> (body : PropT) -> "
                "registered_evidence_denotes PropT body -> "
                "TruthEvidence (registered_evidence_denotes PropT (repeat n body))",
                "  registered_evidence_at_T : (marker : Entity) -> (body : PropT) -> "
                "registered_evidence_denotes PropT body -> "
                "TruthEvidence (registered_evidence_denotes PropT (at_T marker body))",
                "  registered_evidence_during_T : (marker : Entity) -> (body : PropT) -> "
                "registered_evidence_denotes PropT body -> "
                "TruthEvidence (registered_evidence_denotes PropT (during_T marker body))",
                "  registered_evidence_before_T : (marker : Entity) -> (body : PropT) -> "
                "registered_evidence_denotes PropT body -> "
                "TruthEvidence (registered_evidence_denotes PropT (before_T marker body))",
                "  registered_evidence_after_T : (marker : Entity) -> (body : PropT) -> "
                "registered_evidence_denotes PropT body -> "
                "TruthEvidence (registered_evidence_denotes PropT (after_T marker body))",
                "  registered_evidence_until_T : (marker : Entity) -> (body : PropT) -> "
                "registered_evidence_denotes PropT body -> "
                "TruthEvidence (registered_evidence_denotes PropT (until_T marker body))",
                "  registered_evidence_since_T : (marker : Entity) -> (body : PropT) -> "
                "registered_evidence_denotes PropT body -> "
                "TruthEvidence (registered_evidence_denotes PropT (since_T marker body))",
                "  registered_evidence_not_T : (body : PropT) -> "
                "registered_evidence_denotes PropT body -> "
                "TruthEvidence (registered_evidence_denotes PropT (not_T body))",
                "  registered_evidence_transition : "
                "(theme : Entity) -> (scale : StateScale) -> "
                "(source : State) -> (target : State) -> "
                "RegisteredStateTransitionTruth theme scale source target -> "
                "TruthEvidence (registered_evidence_denotes TransitionT "
                "(Transition theme scale source target))",
                "  registered_evidence_cause : (causer : Entity) -> "
                "(effect : TransitionT) -> "
                "registered_evidence_denotes TransitionT effect -> "
                "TruthEvidence (registered_evidence_denotes PropT (Cause causer effect))",
                "",
                "def fully_registered_truth_conditions_from_registered_evidence_sources "
                "(S : RegisteredEvidenceBackedTruthConditionSources) : "
                "FullyRegisteredTruthConditionSpec := {",
                "  fully_registered_truth_denotes := S.registered_evidence_denotes,",
                "  fully_registered_truth_lexical_application := fun A term h =>",
                "      truth_evidence_sound",
                "        (S.registered_evidence_denotes A term)",
                "        (S.registered_evidence_lexical_application A term h),",
            ]
        )
        bridge_fields: list[list[str]] = []
        for type_name in declarations["types"]:
            bridge_fields.append(
                [
                    f"  fully_registered_truth_sigma_{type_name} := fun P h =>",
                    "      truth_evidence_sound",
                    "        "
                    f"(S.registered_evidence_denotes Prop "
                    f"(Exists fun x : {type_name} => P x))",
                    f"        (S.registered_evidence_sigma_{type_name} P h)",
                ]
            )
        bridge_fields.extend(
            [
                [
                    "  fully_registered_truth_repeat := fun n body h =>",
                    "      truth_evidence_sound",
                    "        (S.registered_evidence_denotes PropT (repeat n body))",
                    "        (S.registered_evidence_repeat n body h)",
                ],
                [
                    "  fully_registered_truth_at_T := fun marker body h =>",
                    "      truth_evidence_sound",
                    "        (S.registered_evidence_denotes PropT (at_T marker body))",
                    "        (S.registered_evidence_at_T marker body h)",
                ],
                [
                    "  fully_registered_truth_during_T := fun marker body h =>",
                    "      truth_evidence_sound",
                    "        (S.registered_evidence_denotes PropT (during_T marker body))",
                    "        (S.registered_evidence_during_T marker body h)",
                ],
                [
                    "  fully_registered_truth_before_T := fun marker body h =>",
                    "      truth_evidence_sound",
                    "        (S.registered_evidence_denotes PropT (before_T marker body))",
                    "        (S.registered_evidence_before_T marker body h)",
                ],
                [
                    "  fully_registered_truth_after_T := fun marker body h =>",
                    "      truth_evidence_sound",
                    "        (S.registered_evidence_denotes PropT (after_T marker body))",
                    "        (S.registered_evidence_after_T marker body h)",
                ],
                [
                    "  fully_registered_truth_until_T := fun marker body h =>",
                    "      truth_evidence_sound",
                    "        (S.registered_evidence_denotes PropT (until_T marker body))",
                    "        (S.registered_evidence_until_T marker body h)",
                ],
                [
                    "  fully_registered_truth_since_T := fun marker body h =>",
                    "      truth_evidence_sound",
                    "        (S.registered_evidence_denotes PropT (since_T marker body))",
                    "        (S.registered_evidence_since_T marker body h)",
                ],
                [
                    "  fully_registered_truth_not_T := fun body h =>",
                    "      truth_evidence_sound",
                    "        (S.registered_evidence_denotes PropT (not_T body))",
                    "        (S.registered_evidence_not_T body h)",
                ],
                [
                    "  fully_registered_truth_transition := fun theme scale source target h =>",
                    "      truth_evidence_sound",
                    "        (S.registered_evidence_denotes TransitionT "
                    "(Transition theme scale source target))",
                    "        (S.registered_evidence_transition theme scale source target h)",
                ],
                [
                    "  fully_registered_truth_cause := fun causer effect h =>",
                    "      truth_evidence_sound",
                    "        (S.registered_evidence_denotes PropT (Cause causer effect))",
                    "        (S.registered_evidence_cause causer effect h)",
                ],
            ]
        )
        for index, group in enumerate(bridge_fields):
            suffix = "," if index < len(bridge_fields) - 1 else ""
            for line_index, line in enumerate(group):
                if line_index == len(group) - 1:
                    lines.append(line + suffix)
                else:
                    lines.append(line)
        lines.extend(
            [
                "}",
                "",
                "theorem "
                "registered_evidence_backed_truth_condition_sources_induce_fully_registered_truth_conditions :",
                "    (S : RegisteredEvidenceBackedTruthConditionSources) -> "
                "Exists (fun F : FullyRegisteredTruthConditionSpec => "
                "F = fully_registered_truth_conditions_from_registered_evidence_sources S) := by",
                "  intro S",
                "  exact Exists.intro "
                "(fully_registered_truth_conditions_from_registered_evidence_sources S) rfl",
                "",
                "def concrete_registered_evidence_backed_truth_sources : "
                "RegisteredEvidenceBackedTruthConditionSources := {",
                "  registered_evidence_denotes := ConcreteRegisteredTruth,",
                "  registered_evidence_lexical_application := fun A term h =>",
                "      truth_evidence_intro",
                "        (ConcreteRegisteredTruth A term)",
                "        (ConcreteRegisteredTruth.concrete_registered_truth_atomic A term "
                "(ConcreteRegisteredAtomicTruth."
                "concrete_registered_atomic_truth_lexical_application A term h)),",
            ]
        )
        source_fields: list[list[str]] = []
        for type_name in declarations["types"]:
            source_fields.append(
                [
                    f"  registered_evidence_sigma_{type_name} := fun P h =>",
                    "      truth_evidence_intro",
                    "        "
                    f"(ConcreteRegisteredTruth Prop "
                    f"(Exists fun x : {type_name} => P x))",
                    "        "
                    f"(ConcreteRegisteredTruth.concrete_registered_truth_sigma_{type_name} P h)",
                ]
            )
        source_fields.extend(
            [
                [
                    "  registered_evidence_repeat := fun n body h =>",
                    "      truth_evidence_intro",
                    "        (ConcreteRegisteredTruth PropT (repeat n body))",
                    "        (ConcreteRegisteredTruth.concrete_registered_truth_repeat n body h)",
                ],
                [
                    "  registered_evidence_at_T := fun marker body h =>",
                    "      truth_evidence_intro",
                    "        (ConcreteRegisteredTruth PropT (at_T marker body))",
                    "        (ConcreteRegisteredTruth.concrete_registered_truth_at_T marker body h)",
                ],
                [
                    "  registered_evidence_during_T := fun marker body h =>",
                    "      truth_evidence_intro",
                    "        (ConcreteRegisteredTruth PropT (during_T marker body))",
                    "        (ConcreteRegisteredTruth.concrete_registered_truth_during_T marker body h)",
                ],
                [
                    "  registered_evidence_before_T := fun marker body h =>",
                    "      truth_evidence_intro",
                    "        (ConcreteRegisteredTruth PropT (before_T marker body))",
                    "        (ConcreteRegisteredTruth.concrete_registered_truth_before_T marker body h)",
                ],
                [
                    "  registered_evidence_after_T := fun marker body h =>",
                    "      truth_evidence_intro",
                    "        (ConcreteRegisteredTruth PropT (after_T marker body))",
                    "        (ConcreteRegisteredTruth.concrete_registered_truth_after_T marker body h)",
                ],
                [
                    "  registered_evidence_until_T := fun marker body h =>",
                    "      truth_evidence_intro",
                    "        (ConcreteRegisteredTruth PropT (until_T marker body))",
                    "        (ConcreteRegisteredTruth.concrete_registered_truth_until_T marker body h)",
                ],
                [
                    "  registered_evidence_since_T := fun marker body h =>",
                    "      truth_evidence_intro",
                    "        (ConcreteRegisteredTruth PropT (since_T marker body))",
                    "        (ConcreteRegisteredTruth.concrete_registered_truth_since_T marker body h)",
                ],
                [
                    "  registered_evidence_not_T := fun body h =>",
                    "      truth_evidence_intro",
                    "        (ConcreteRegisteredTruth PropT (not_T body))",
                    "        (ConcreteRegisteredTruth.concrete_registered_truth_not_T body h)",
                ],
                [
                    "  registered_evidence_transition := fun theme scale source target h =>",
                    "      truth_evidence_intro",
                    "        (ConcreteRegisteredTruth TransitionT "
                    "(Transition theme scale source target))",
                    "        (ConcreteRegisteredTruth.concrete_registered_truth_atomic "
                    "TransitionT (Transition theme scale source target) "
                    "(ConcreteRegisteredAtomicTruth."
                    "concrete_registered_atomic_truth_transition "
                    "theme scale source target h))",
                ],
                [
                    "  registered_evidence_cause := fun causer effect h =>",
                    "      truth_evidence_intro",
                    "        (ConcreteRegisteredTruth PropT (Cause causer effect))",
                    "        (ConcreteRegisteredTruth.concrete_registered_truth_cause causer effect h)",
                ],
            ]
        )
        for index, group in enumerate(source_fields):
            suffix = "," if index < len(source_fields) - 1 else ""
            for line_index, line in enumerate(group):
                if line_index == len(group) - 1:
                    lines.append(line + suffix)
                else:
                    lines.append(line)
        lines.extend(
            [
                "}",
                "",
                "def concrete_registered_evidence_backed_truth_conditions : "
                "FullyRegisteredTruthConditionSpec :=",
                "  fully_registered_truth_conditions_from_registered_evidence_sources "
                "concrete_registered_evidence_backed_truth_sources",
                "",
                "theorem concrete_registered_evidence_backed_truth_sources_exist :",
                "    Exists (fun S : RegisteredEvidenceBackedTruthConditionSources => "
                "S = concrete_registered_evidence_backed_truth_sources) := by",
                "  exact Exists.intro concrete_registered_evidence_backed_truth_sources rfl",
                "",
                "theorem concrete_registered_evidence_backed_truth_conditions_exists :",
                "    Exists (fun F : FullyRegisteredTruthConditionSpec => "
                "F = concrete_registered_evidence_backed_truth_conditions) := by",
                "  exact Exists.intro concrete_registered_evidence_backed_truth_conditions rfl",
                "",
                "theorem "
                "concrete_registered_evidence_backed_truth_conditions_denote_concrete_registered :",
                "    (A : Type) -> (term : A) -> ConcreteRegisteredTruth A term -> "
                "concrete_registered_evidence_backed_truth_conditions."
                "fully_registered_truth_denotes A term := by",
                "  intro A term h",
                "  exact h",
                "",
                "theorem "
                "concrete_registered_evidence_backed_truth_conditions_imply_atomic_closure :",
                "    (A : Type) -> (term : A) -> "
                "concrete_registered_evidence_backed_truth_conditions."
                "fully_registered_truth_denotes A term -> AtomicClosureTruth A term := by",
                "  intro A term h",
                "  apply concrete_registered_truth_implies_atomic_closure",
                "  exact h",
            ]
        )
        return lines

    lines = [
        "Record RegisteredEvidenceBackedTruthConditionSources : Type := {",
        "  registered_evidence_denotes : forall A : Type, A -> Prop;",
        "  registered_evidence_lexical_application :",
        "      forall A : Type, forall term : A,",
        "      RegisteredLexicalApplicationTruth A term ->",
        "      TruthEvidence (registered_evidence_denotes A term);",
    ]
    for type_name in declarations["types"]:
        lines.extend(
            [
                f"  registered_evidence_sigma_{type_name} : "
                f"forall P : {type_name} -> Prop,",
                f"      (forall x : {type_name}, "
                "registered_evidence_denotes Prop (P x)) ->",
                "      TruthEvidence (registered_evidence_denotes Prop "
                f"(exists x : {type_name}, P x));",
            ]
        )
    lines.extend(
        [
            "  registered_evidence_repeat : forall n : nat, forall body : PropT,",
            "      registered_evidence_denotes PropT body ->",
            "      TruthEvidence (registered_evidence_denotes PropT (repeat n body));",
            "  registered_evidence_at_T : forall marker : Entity, forall body : PropT,",
            "      registered_evidence_denotes PropT body ->",
            "      TruthEvidence (registered_evidence_denotes PropT (at_T marker body));",
            "  registered_evidence_during_T : forall marker : Entity, forall body : PropT,",
            "      registered_evidence_denotes PropT body ->",
            "      TruthEvidence (registered_evidence_denotes PropT (during_T marker body));",
            "  registered_evidence_before_T : forall marker : Entity, forall body : PropT,",
            "      registered_evidence_denotes PropT body ->",
            "      TruthEvidence (registered_evidence_denotes PropT (before_T marker body));",
            "  registered_evidence_after_T : forall marker : Entity, forall body : PropT,",
            "      registered_evidence_denotes PropT body ->",
            "      TruthEvidence (registered_evidence_denotes PropT (after_T marker body));",
            "  registered_evidence_until_T : forall marker : Entity, forall body : PropT,",
            "      registered_evidence_denotes PropT body ->",
            "      TruthEvidence (registered_evidence_denotes PropT (until_T marker body));",
            "  registered_evidence_since_T : forall marker : Entity, forall body : PropT,",
            "      registered_evidence_denotes PropT body ->",
            "      TruthEvidence (registered_evidence_denotes PropT (since_T marker body));",
            "  registered_evidence_not_T : forall body : PropT,",
            "      registered_evidence_denotes PropT body ->",
            "      TruthEvidence (registered_evidence_denotes PropT (not_T body));",
            "  registered_evidence_transition :",
            "      forall theme : Entity, forall scale : StateScale,",
            "      forall source : State, forall target : State,",
            "      RegisteredStateTransitionTruth theme scale source target ->",
            "      TruthEvidence (registered_evidence_denotes TransitionT",
            "        (Transition theme scale source target));",
            "  registered_evidence_cause :",
            "      forall causer : Entity, forall effect : TransitionT,",
            "      registered_evidence_denotes TransitionT effect ->",
            "      TruthEvidence (registered_evidence_denotes PropT (Cause causer effect))",
            "}.",
            "",
            "Definition fully_registered_truth_conditions_from_registered_evidence_sources",
            "  (S : RegisteredEvidenceBackedTruthConditionSources) :",
            "  FullyRegisteredTruthConditionSpec := {|",
            "  fully_registered_truth_denotes := registered_evidence_denotes S;",
            "  fully_registered_truth_lexical_application :=",
            "    fun A term h => truth_evidence_sound",
            "      (registered_evidence_denotes S A term)",
            "      (registered_evidence_lexical_application S A term h);",
        ]
    )
    bridge_fields = [
        (
            f"fully_registered_truth_sigma_{type_name}",
            [
                f"fun P h => truth_evidence_sound",
                "      (registered_evidence_denotes S Prop",
                f"        (exists x : {type_name}, P x))",
                f"      (registered_evidence_sigma_{type_name} S P h)",
            ],
        )
        for type_name in declarations["types"]
    ]
    bridge_fields.extend(
        [
            (
                "fully_registered_truth_repeat",
                [
                    "fun n body h => truth_evidence_sound",
                    "      (registered_evidence_denotes S PropT (repeat n body))",
                    "      (registered_evidence_repeat S n body h)",
                ],
            ),
            (
                "fully_registered_truth_at_T",
                [
                    "fun marker body h => truth_evidence_sound",
                    "      (registered_evidence_denotes S PropT (at_T marker body))",
                    "      (registered_evidence_at_T S marker body h)",
                ],
            ),
            (
                "fully_registered_truth_during_T",
                [
                    "fun marker body h => truth_evidence_sound",
                    "      (registered_evidence_denotes S PropT (during_T marker body))",
                    "      (registered_evidence_during_T S marker body h)",
                ],
            ),
            (
                "fully_registered_truth_before_T",
                [
                    "fun marker body h => truth_evidence_sound",
                    "      (registered_evidence_denotes S PropT (before_T marker body))",
                    "      (registered_evidence_before_T S marker body h)",
                ],
            ),
            (
                "fully_registered_truth_after_T",
                [
                    "fun marker body h => truth_evidence_sound",
                    "      (registered_evidence_denotes S PropT (after_T marker body))",
                    "      (registered_evidence_after_T S marker body h)",
                ],
            ),
            (
                "fully_registered_truth_until_T",
                [
                    "fun marker body h => truth_evidence_sound",
                    "      (registered_evidence_denotes S PropT (until_T marker body))",
                    "      (registered_evidence_until_T S marker body h)",
                ],
            ),
            (
                "fully_registered_truth_since_T",
                [
                    "fun marker body h => truth_evidence_sound",
                    "      (registered_evidence_denotes S PropT (since_T marker body))",
                    "      (registered_evidence_since_T S marker body h)",
                ],
            ),
            (
                "fully_registered_truth_not_T",
                [
                    "fun body h => truth_evidence_sound",
                    "      (registered_evidence_denotes S PropT (not_T body))",
                    "      (registered_evidence_not_T S body h)",
                ],
            ),
            (
                "fully_registered_truth_transition",
                [
                    "fun theme scale source target h => truth_evidence_sound",
                    "      (registered_evidence_denotes S TransitionT",
                    "        (Transition theme scale source target))",
                    "      (registered_evidence_transition S theme scale source target h)",
                ],
            ),
            (
                "fully_registered_truth_cause",
                [
                    "fun causer effect h => truth_evidence_sound",
                    "      (registered_evidence_denotes S PropT (Cause causer effect))",
                    "      (registered_evidence_cause S causer effect h)",
                ],
            ),
        ]
    )
    for index, (field, value_lines) in enumerate(bridge_fields):
        suffix = ";" if index < len(bridge_fields) - 1 else ""
        lines.append(f"  {field} :=")
        for line_index, line in enumerate(value_lines):
            if line_index == len(value_lines) - 1:
                lines.append(f"    {line}{suffix}")
            else:
                lines.append(f"    {line}")
    lines.extend(
        [
            "|}.",
            "",
            "Theorem registered_evidence_backed_truth_condition_sources_induce_fully_registered_truth_conditions :",
            "  forall S : RegisteredEvidenceBackedTruthConditionSources,",
            "    exists F : FullyRegisteredTruthConditionSpec,",
            "      F = fully_registered_truth_conditions_from_registered_evidence_sources S.",
            "Proof.",
            "  intro S.",
            "  exists (fully_registered_truth_conditions_from_registered_evidence_sources S).",
            "  reflexivity.",
            "Qed.",
            "",
            "Definition concrete_registered_evidence_backed_truth_sources :",
            "  RegisteredEvidenceBackedTruthConditionSources := {|",
            "  registered_evidence_denotes := ConcreteRegisteredTruth;",
            "  registered_evidence_lexical_application :=",
            "    fun A term h => truth_evidence_intro",
            "      (ConcreteRegisteredTruth A term)",
            "      (concrete_registered_truth_atomic A term",
            "        (concrete_registered_atomic_truth_lexical_application A term h));",
        ]
    )
    source_fields = [
        (
            f"registered_evidence_sigma_{type_name}",
            [
                "fun P h => truth_evidence_intro",
                f"      (ConcreteRegisteredTruth Prop (exists x : {type_name}, P x))",
                f"      (concrete_registered_truth_sigma_{type_name} P h)",
            ],
        )
        for type_name in declarations["types"]
    ]
    source_fields.extend(
        [
            (
                "registered_evidence_repeat",
                [
                    "fun n body h => truth_evidence_intro",
                    "      (ConcreteRegisteredTruth PropT (repeat n body))",
                    "      (concrete_registered_truth_repeat n body h)",
                ],
            ),
            (
                "registered_evidence_at_T",
                [
                    "fun marker body h => truth_evidence_intro",
                    "      (ConcreteRegisteredTruth PropT (at_T marker body))",
                    "      (concrete_registered_truth_at_T marker body h)",
                ],
            ),
            (
                "registered_evidence_during_T",
                [
                    "fun marker body h => truth_evidence_intro",
                    "      (ConcreteRegisteredTruth PropT (during_T marker body))",
                    "      (concrete_registered_truth_during_T marker body h)",
                ],
            ),
            (
                "registered_evidence_before_T",
                [
                    "fun marker body h => truth_evidence_intro",
                    "      (ConcreteRegisteredTruth PropT (before_T marker body))",
                    "      (concrete_registered_truth_before_T marker body h)",
                ],
            ),
            (
                "registered_evidence_after_T",
                [
                    "fun marker body h => truth_evidence_intro",
                    "      (ConcreteRegisteredTruth PropT (after_T marker body))",
                    "      (concrete_registered_truth_after_T marker body h)",
                ],
            ),
            (
                "registered_evidence_until_T",
                [
                    "fun marker body h => truth_evidence_intro",
                    "      (ConcreteRegisteredTruth PropT (until_T marker body))",
                    "      (concrete_registered_truth_until_T marker body h)",
                ],
            ),
            (
                "registered_evidence_since_T",
                [
                    "fun marker body h => truth_evidence_intro",
                    "      (ConcreteRegisteredTruth PropT (since_T marker body))",
                    "      (concrete_registered_truth_since_T marker body h)",
                ],
            ),
            (
                "registered_evidence_not_T",
                [
                    "fun body h => truth_evidence_intro",
                    "      (ConcreteRegisteredTruth PropT (not_T body))",
                    "      (concrete_registered_truth_not_T body h)",
                ],
            ),
            (
                "registered_evidence_transition",
                [
                    "fun theme scale source target h => truth_evidence_intro",
                    "      (ConcreteRegisteredTruth TransitionT",
                    "        (Transition theme scale source target))",
                    "      (concrete_registered_truth_atomic TransitionT",
                    "        (Transition theme scale source target)",
                    "        (concrete_registered_atomic_truth_transition",
                    "          theme scale source target h))",
                ],
            ),
            (
                "registered_evidence_cause",
                [
                    "fun causer effect h => truth_evidence_intro",
                    "      (ConcreteRegisteredTruth PropT (Cause causer effect))",
                    "      (concrete_registered_truth_cause causer effect h)",
                ],
            ),
        ]
    )
    for index, (field, value_lines) in enumerate(source_fields):
        suffix = ";" if index < len(source_fields) - 1 else ""
        lines.append(f"  {field} :=")
        for line_index, line in enumerate(value_lines):
            if line_index == len(value_lines) - 1:
                lines.append(f"    {line}{suffix}")
            else:
                lines.append(f"    {line}")
    lines.extend(
        [
            "|}.",
            "",
            "Definition concrete_registered_evidence_backed_truth_conditions :",
            "  FullyRegisteredTruthConditionSpec :=",
            "  fully_registered_truth_conditions_from_registered_evidence_sources",
            "    concrete_registered_evidence_backed_truth_sources.",
            "",
            "Theorem concrete_registered_evidence_backed_truth_sources_exist :",
            "  exists S : RegisteredEvidenceBackedTruthConditionSources,",
            "    S = concrete_registered_evidence_backed_truth_sources.",
            "Proof.",
            "  exists concrete_registered_evidence_backed_truth_sources. reflexivity.",
            "Qed.",
            "",
            "Theorem concrete_registered_evidence_backed_truth_conditions_exists :",
            "  exists F : FullyRegisteredTruthConditionSpec,",
            "    F = concrete_registered_evidence_backed_truth_conditions.",
            "Proof.",
            "  exists concrete_registered_evidence_backed_truth_conditions. reflexivity.",
            "Qed.",
            "",
            "Theorem concrete_registered_evidence_backed_truth_conditions_denote_concrete_registered :",
            "  forall A : Type, forall term : A,",
            "    ConcreteRegisteredTruth A term ->",
            "    fully_registered_truth_denotes",
            "      concrete_registered_evidence_backed_truth_conditions A term.",
            "Proof.",
            "  intros A term H.",
            "  exact H.",
            "Qed.",
            "",
            "Theorem concrete_registered_evidence_backed_truth_conditions_imply_atomic_closure :",
            "  forall A : Type, forall term : A,",
            "    fully_registered_truth_denotes",
            "      concrete_registered_evidence_backed_truth_conditions A term ->",
            "    AtomicClosureTruth A term.",
            "Proof.",
            "  intros A term H.",
            "  apply concrete_registered_truth_implies_atomic_closure.",
            "  exact H.",
            "Qed.",
        ]
    )
    return lines


def concrete_registered_evidence_backed_truth_condition_model_lines(
    target: str,
) -> list[str]:
    """Package the registered evidence-backed truth spec as a model bridge."""

    if target == "lean":
        return [
            "structure ConcreteRegisteredEvidenceBackedTruthConditionModel : Type where",
            "  concrete_registered_evidence_backed_model_denotes : "
            "(A : Type) -> A -> Prop",
            "  concrete_registered_evidence_backed_model_spec : "
            "FullyRegisteredTruthConditionSpec",
            "  concrete_registered_evidence_backed_model_denote_spec : "
            "(A : Type) -> (term : A) -> "
            "concrete_registered_evidence_backed_model_denotes A term -> "
            "concrete_registered_evidence_backed_model_spec."
            "fully_registered_truth_denotes A term",
            "  concrete_registered_evidence_backed_model_sound : "
            "(A : Type) -> (term : A) -> "
            "concrete_registered_evidence_backed_model_denotes A term -> "
            "AtomicClosureTruth A term",
            "",
            "def concrete_registered_evidence_backed_truth_condition_model : "
            "ConcreteRegisteredEvidenceBackedTruthConditionModel := {",
            "  concrete_registered_evidence_backed_model_denotes := "
            "ConcreteRegisteredTruth,",
            "  concrete_registered_evidence_backed_model_spec := "
            "concrete_registered_evidence_backed_truth_conditions,",
            "  concrete_registered_evidence_backed_model_denote_spec := "
            "concrete_registered_evidence_backed_truth_conditions_denote_concrete_registered,",
            "  concrete_registered_evidence_backed_model_sound := "
            "concrete_registered_truth_implies_atomic_closure,",
            "}",
            "",
            "theorem concrete_registered_evidence_backed_truth_condition_model_exists :",
            "    Exists (fun M : ConcreteRegisteredEvidenceBackedTruthConditionModel => "
            "M = concrete_registered_evidence_backed_truth_condition_model) := by",
            "  exact Exists.intro "
            "concrete_registered_evidence_backed_truth_condition_model rfl",
            "",
            "theorem "
            "concrete_registered_evidence_backed_truth_condition_model_denote_spec :",
            "    (A : Type) -> (term : A) -> "
            "concrete_registered_evidence_backed_truth_condition_model."
            "concrete_registered_evidence_backed_model_denotes A term -> "
            "concrete_registered_evidence_backed_truth_condition_model."
            "concrete_registered_evidence_backed_model_spec."
            "fully_registered_truth_denotes A term := by",
            "  intro A term h",
            "  exact concrete_registered_evidence_backed_truth_condition_model."
            "concrete_registered_evidence_backed_model_denote_spec A term h",
            "",
            "theorem "
            "concrete_registered_evidence_backed_truth_condition_model_imply_atomic_closure :",
            "    (A : Type) -> (term : A) -> "
            "concrete_registered_evidence_backed_truth_condition_model."
            "concrete_registered_evidence_backed_model_denotes A term -> "
            "AtomicClosureTruth A term := by",
            "  intro A term h",
            "  exact concrete_registered_evidence_backed_truth_condition_model."
            "concrete_registered_evidence_backed_model_sound A term h",
            "",
            "theorem "
            "concrete_registered_evidence_backed_truth_condition_model_spec_imply_atomic_closure :",
            "    (A : Type) -> (term : A) -> "
            "concrete_registered_evidence_backed_truth_condition_model."
            "concrete_registered_evidence_backed_model_spec."
            "fully_registered_truth_denotes A term -> "
            "AtomicClosureTruth A term := by",
            "  intro A term h",
            "  apply concrete_registered_evidence_backed_truth_conditions_imply_atomic_closure",
            "  exact h",
        ]

    return [
        "Record ConcreteRegisteredEvidenceBackedTruthConditionModel : Type := {",
        "  concrete_registered_evidence_backed_model_denotes : "
        "forall A : Type, A -> Prop;",
        "  concrete_registered_evidence_backed_model_spec : "
        "FullyRegisteredTruthConditionSpec;",
        "  concrete_registered_evidence_backed_model_denote_spec :",
        "      forall A : Type, forall term : A,",
        "      concrete_registered_evidence_backed_model_denotes A term ->",
        "      fully_registered_truth_denotes",
        "        concrete_registered_evidence_backed_model_spec A term;",
        "  concrete_registered_evidence_backed_model_sound :",
        "      forall A : Type, forall term : A,",
        "      concrete_registered_evidence_backed_model_denotes A term ->",
        "      AtomicClosureTruth A term",
        "}.",
        "",
        "Definition concrete_registered_evidence_backed_truth_condition_model :",
        "  ConcreteRegisteredEvidenceBackedTruthConditionModel := {|",
        "  concrete_registered_evidence_backed_model_denotes := "
        "ConcreteRegisteredTruth;",
        "  concrete_registered_evidence_backed_model_spec := "
        "concrete_registered_evidence_backed_truth_conditions;",
        "  concrete_registered_evidence_backed_model_denote_spec :=",
        "    concrete_registered_evidence_backed_truth_conditions_denote_concrete_registered;",
        "  concrete_registered_evidence_backed_model_sound :=",
        "    concrete_registered_truth_implies_atomic_closure",
        "|}.",
        "",
        "Theorem concrete_registered_evidence_backed_truth_condition_model_exists :",
        "  exists M : ConcreteRegisteredEvidenceBackedTruthConditionModel,",
        "    M = concrete_registered_evidence_backed_truth_condition_model.",
        "Proof.",
        "  exists concrete_registered_evidence_backed_truth_condition_model.",
        "  reflexivity.",
        "Qed.",
        "",
        "Theorem concrete_registered_evidence_backed_truth_condition_model_denote_spec :",
        "  forall A : Type, forall term : A,",
        "    concrete_registered_evidence_backed_model_denotes",
        "      concrete_registered_evidence_backed_truth_condition_model A term ->",
        "    fully_registered_truth_denotes",
        "      (concrete_registered_evidence_backed_model_spec",
        "        concrete_registered_evidence_backed_truth_condition_model) A term.",
        "Proof.",
        "  intros A term H.",
        "  exact (concrete_registered_evidence_backed_model_denote_spec",
        "    concrete_registered_evidence_backed_truth_condition_model A term H).",
        "Qed.",
        "",
        "Theorem concrete_registered_evidence_backed_truth_condition_model_imply_atomic_closure :",
        "  forall A : Type, forall term : A,",
        "    concrete_registered_evidence_backed_model_denotes",
        "      concrete_registered_evidence_backed_truth_condition_model A term ->",
        "    AtomicClosureTruth A term.",
        "Proof.",
        "  intros A term H.",
        "  exact (concrete_registered_evidence_backed_model_sound",
        "    concrete_registered_evidence_backed_truth_condition_model A term H).",
        "Qed.",
        "",
        "Theorem concrete_registered_evidence_backed_truth_condition_model_spec_imply_atomic_closure :",
        "  forall A : Type, forall term : A,",
        "    fully_registered_truth_denotes",
        "      (concrete_registered_evidence_backed_model_spec",
        "        concrete_registered_evidence_backed_truth_condition_model) A term ->",
        "    AtomicClosureTruth A term.",
        "Proof.",
        "  intros A term H.",
        "  apply concrete_registered_evidence_backed_truth_conditions_imply_atomic_closure.",
        "  exact H.",
        "Qed.",
    ]


def concrete_registered_truth_kernel_lines(
    declarations: dict[str, Any],
    target: str,
) -> list[str]:
    if target == "lean":
        lines = [
            "structure ConcreteRegisteredTruthKernel : Type where",
            "  concrete_registered_kernel_denotes : (A : Type) -> A -> Prop",
            "  concrete_registered_kernel_lexical_application : "
            "(A : Type) -> (term : A) -> "
            "RegisteredLexicalApplicationTruth A term -> "
            "concrete_registered_kernel_denotes A term",
        ]
        for type_name in declarations["types"]:
            lines.append(
                f"  concrete_registered_kernel_sigma_{type_name} : "
                f"(P : {type_name} -> Prop) -> "
                f"((x : {type_name}) -> "
                "concrete_registered_kernel_denotes Prop (P x)) -> "
                "concrete_registered_kernel_denotes Prop "
                f"(Exists fun x : {type_name} => P x)"
            )
        lines.extend(
            [
                "  concrete_registered_kernel_repeat : "
                "(n : Nat) -> (body : PropT) -> "
                "concrete_registered_kernel_denotes PropT body -> "
                "concrete_registered_kernel_denotes PropT (repeat n body)",
                "  concrete_registered_kernel_at_T : "
                "(marker : Entity) -> (body : PropT) -> "
                "concrete_registered_kernel_denotes PropT body -> "
                "concrete_registered_kernel_denotes PropT (at_T marker body)",
                "  concrete_registered_kernel_during_T : "
                "(marker : Entity) -> (body : PropT) -> "
                "concrete_registered_kernel_denotes PropT body -> "
                "concrete_registered_kernel_denotes PropT (during_T marker body)",
                "  concrete_registered_kernel_before_T : "
                "(marker : Entity) -> (body : PropT) -> "
                "concrete_registered_kernel_denotes PropT body -> "
                "concrete_registered_kernel_denotes PropT (before_T marker body)",
                "  concrete_registered_kernel_after_T : "
                "(marker : Entity) -> (body : PropT) -> "
                "concrete_registered_kernel_denotes PropT body -> "
                "concrete_registered_kernel_denotes PropT (after_T marker body)",
                "  concrete_registered_kernel_until_T : "
                "(marker : Entity) -> (body : PropT) -> "
                "concrete_registered_kernel_denotes PropT body -> "
                "concrete_registered_kernel_denotes PropT (until_T marker body)",
                "  concrete_registered_kernel_since_T : "
                "(marker : Entity) -> (body : PropT) -> "
                "concrete_registered_kernel_denotes PropT body -> "
                "concrete_registered_kernel_denotes PropT (since_T marker body)",
                "  concrete_registered_kernel_not_T : (body : PropT) -> "
                "concrete_registered_kernel_denotes PropT body -> "
                "concrete_registered_kernel_denotes PropT (not_T body)",
                "  concrete_registered_kernel_transition : "
                "(theme : Entity) -> (scale : StateScale) -> "
                "(source : State) -> (target : State) -> "
                "RegisteredStateTransitionTruth theme scale source target -> "
                "concrete_registered_kernel_denotes TransitionT "
                "(Transition theme scale source target)",
                "  concrete_registered_kernel_cause : "
                "(causer : Entity) -> (effect : TransitionT) -> "
                "concrete_registered_kernel_denotes TransitionT effect -> "
                "concrete_registered_kernel_denotes PropT (Cause causer effect)",
                "",
                "def fully_registered_truth_conditions_from_concrete_registered_kernel "
                "(K : ConcreteRegisteredTruthKernel) : "
                "FullyRegisteredTruthConditionSpec := {",
                "  fully_registered_truth_denotes := "
                "K.concrete_registered_kernel_denotes,",
                "  fully_registered_truth_lexical_application := "
                "K.concrete_registered_kernel_lexical_application,",
            ]
        )
        bridge_fields: list[tuple[str, str]] = []
        for type_name in declarations["types"]:
            bridge_fields.append(
                (
                    f"fully_registered_truth_sigma_{type_name}",
                    f"K.concrete_registered_kernel_sigma_{type_name}",
                )
            )
        bridge_fields.extend(
            [
                ("fully_registered_truth_repeat", "K.concrete_registered_kernel_repeat"),
                ("fully_registered_truth_at_T", "K.concrete_registered_kernel_at_T"),
                ("fully_registered_truth_during_T", "K.concrete_registered_kernel_during_T"),
                ("fully_registered_truth_before_T", "K.concrete_registered_kernel_before_T"),
                ("fully_registered_truth_after_T", "K.concrete_registered_kernel_after_T"),
                ("fully_registered_truth_until_T", "K.concrete_registered_kernel_until_T"),
                ("fully_registered_truth_since_T", "K.concrete_registered_kernel_since_T"),
                ("fully_registered_truth_not_T", "K.concrete_registered_kernel_not_T"),
                ("fully_registered_truth_transition", "K.concrete_registered_kernel_transition"),
                ("fully_registered_truth_cause", "K.concrete_registered_kernel_cause"),
            ]
        )
        for index, (field, value) in enumerate(bridge_fields):
            suffix = "," if index < len(bridge_fields) - 1 else ""
            lines.append(f"  {field} := {value}{suffix}")
        lines.extend(
            [
                "}",
                "",
                "def concrete_registered_truth_kernel_denotes : "
                "(A : Type) -> A -> Prop :=",
                "  ConcreteRegisteredTruth",
                "",
                "def concrete_registered_truth_kernel : "
                "ConcreteRegisteredTruthKernel := {",
                "  concrete_registered_kernel_denotes := "
                "concrete_registered_truth_kernel_denotes,",
                "  concrete_registered_kernel_lexical_application := "
                "fun A term h => ConcreteRegisteredTruth."
                "concrete_registered_truth_atomic A term "
                "(ConcreteRegisteredAtomicTruth."
                "concrete_registered_atomic_truth_lexical_application A term h),",
            ]
        )
        model_fields: list[tuple[str, str]] = []
        for type_name in declarations["types"]:
            model_fields.append(
                (
                    f"concrete_registered_kernel_sigma_{type_name}",
                    "fun P h => ConcreteRegisteredTruth."
                    f"concrete_registered_truth_sigma_{type_name} P h",
                )
            )
        model_fields.extend(
            [
                ("concrete_registered_kernel_repeat", "fun n body h => ConcreteRegisteredTruth.concrete_registered_truth_repeat n body h"),
                ("concrete_registered_kernel_at_T", "fun marker body h => ConcreteRegisteredTruth.concrete_registered_truth_at_T marker body h"),
                ("concrete_registered_kernel_during_T", "fun marker body h => ConcreteRegisteredTruth.concrete_registered_truth_during_T marker body h"),
                ("concrete_registered_kernel_before_T", "fun marker body h => ConcreteRegisteredTruth.concrete_registered_truth_before_T marker body h"),
                ("concrete_registered_kernel_after_T", "fun marker body h => ConcreteRegisteredTruth.concrete_registered_truth_after_T marker body h"),
                ("concrete_registered_kernel_until_T", "fun marker body h => ConcreteRegisteredTruth.concrete_registered_truth_until_T marker body h"),
                ("concrete_registered_kernel_since_T", "fun marker body h => ConcreteRegisteredTruth.concrete_registered_truth_since_T marker body h"),
                ("concrete_registered_kernel_not_T", "fun body h => ConcreteRegisteredTruth.concrete_registered_truth_not_T body h"),
                (
                    "concrete_registered_kernel_transition",
                    "fun theme scale source target h => ConcreteRegisteredTruth."
                    "concrete_registered_truth_atomic TransitionT "
                    "(Transition theme scale source target) "
                    "(ConcreteRegisteredAtomicTruth."
                    "concrete_registered_atomic_truth_transition "
                    "theme scale source target h)",
                ),
                ("concrete_registered_kernel_cause", "fun causer effect h => ConcreteRegisteredTruth.concrete_registered_truth_cause causer effect h"),
            ]
        )
        for index, (field, value) in enumerate(model_fields):
            suffix = "," if index < len(model_fields) - 1 else ""
            lines.append(f"  {field} := {value}{suffix}")
        lines.extend(
            [
                "}",
                "",
                "def concrete_registered_truth_conditions_from_kernel : "
                "FullyRegisteredTruthConditionSpec :=",
                "  fully_registered_truth_conditions_from_concrete_registered_kernel "
                "concrete_registered_truth_kernel",
                "",
                "theorem concrete_registered_truth_kernel_exists :",
                "    Exists (fun K : ConcreteRegisteredTruthKernel => "
                "K = concrete_registered_truth_kernel) := by",
                "  exact Exists.intro concrete_registered_truth_kernel rfl",
                "",
                "theorem concrete_registered_truth_conditions_from_kernel_exists :",
                "    Exists (fun F : FullyRegisteredTruthConditionSpec => "
                "F = concrete_registered_truth_conditions_from_kernel) := by",
                "  exact Exists.intro concrete_registered_truth_conditions_from_kernel rfl",
                "",
                "theorem concrete_registered_truth_kernel_denotes_concrete_registered :",
                "    (A : Type) -> (term : A) -> ConcreteRegisteredTruth A term -> "
                "concrete_registered_truth_kernel."
                "concrete_registered_kernel_denotes A term := by",
                "  intro A term h",
                "  exact h",
                "",
                "theorem "
                "concrete_registered_truth_conditions_from_kernel_denote_concrete_registered :",
                "    (A : Type) -> (term : A) -> ConcreteRegisteredTruth A term -> "
                "concrete_registered_truth_conditions_from_kernel."
                "fully_registered_truth_denotes A term := by",
                "  intro A term h",
                "  exact h",
                "",
                "theorem "
                "concrete_registered_truth_conditions_from_kernel_imply_atomic_closure :",
                "    (A : Type) -> (term : A) -> "
                "concrete_registered_truth_conditions_from_kernel."
                "fully_registered_truth_denotes A term -> "
                "AtomicClosureTruth A term := by",
                "  intro A term h",
                "  apply concrete_registered_truth_implies_atomic_closure",
                "  exact h",
            ]
        )
        return lines

    lines = [
        "Record ConcreteRegisteredTruthKernel : Type := {",
        "  concrete_registered_kernel_denotes : forall A : Type, A -> Prop;",
        "  concrete_registered_kernel_lexical_application :",
        "      forall A : Type, forall term : A,",
        "      RegisteredLexicalApplicationTruth A term ->",
        "      concrete_registered_kernel_denotes A term;",
    ]
    for type_name in declarations["types"]:
        lines.extend(
            [
                f"  concrete_registered_kernel_sigma_{type_name} : "
                f"forall P : {type_name} -> Prop,",
                f"      (forall x : {type_name}, "
                "concrete_registered_kernel_denotes Prop (P x)) ->",
                "      concrete_registered_kernel_denotes Prop "
                f"(exists x : {type_name}, P x);",
            ]
        )
    lines.extend(
        [
            "  concrete_registered_kernel_repeat : "
            "forall n : nat, forall body : PropT,",
            "      concrete_registered_kernel_denotes PropT body ->",
            "      concrete_registered_kernel_denotes PropT (repeat n body);",
            "  concrete_registered_kernel_at_T : "
            "forall marker : Entity, forall body : PropT,",
            "      concrete_registered_kernel_denotes PropT body ->",
            "      concrete_registered_kernel_denotes PropT (at_T marker body);",
            "  concrete_registered_kernel_during_T : "
            "forall marker : Entity, forall body : PropT,",
            "      concrete_registered_kernel_denotes PropT body ->",
            "      concrete_registered_kernel_denotes PropT (during_T marker body);",
            "  concrete_registered_kernel_before_T : "
            "forall marker : Entity, forall body : PropT,",
            "      concrete_registered_kernel_denotes PropT body ->",
            "      concrete_registered_kernel_denotes PropT (before_T marker body);",
            "  concrete_registered_kernel_after_T : "
            "forall marker : Entity, forall body : PropT,",
            "      concrete_registered_kernel_denotes PropT body ->",
            "      concrete_registered_kernel_denotes PropT (after_T marker body);",
            "  concrete_registered_kernel_until_T : "
            "forall marker : Entity, forall body : PropT,",
            "      concrete_registered_kernel_denotes PropT body ->",
            "      concrete_registered_kernel_denotes PropT (until_T marker body);",
            "  concrete_registered_kernel_since_T : "
            "forall marker : Entity, forall body : PropT,",
            "      concrete_registered_kernel_denotes PropT body ->",
            "      concrete_registered_kernel_denotes PropT (since_T marker body);",
            "  concrete_registered_kernel_not_T : forall body : PropT,",
            "      concrete_registered_kernel_denotes PropT body ->",
            "      concrete_registered_kernel_denotes PropT (not_T body);",
            "  concrete_registered_kernel_transition : "
            "forall theme : Entity, forall scale : StateScale,",
            "      forall source : State, forall target : State,",
            "      RegisteredStateTransitionTruth theme scale source target ->",
            "      concrete_registered_kernel_denotes TransitionT "
            "(Transition theme scale source target);",
            "  concrete_registered_kernel_cause : "
            "forall causer : Entity, forall effect : TransitionT,",
            "      concrete_registered_kernel_denotes TransitionT effect ->",
            "      concrete_registered_kernel_denotes PropT (Cause causer effect)",
            "}.",
            "",
            "Definition fully_registered_truth_conditions_from_concrete_registered_kernel",
            "  (K : ConcreteRegisteredTruthKernel) : FullyRegisteredTruthConditionSpec := {|",
            "  fully_registered_truth_denotes := concrete_registered_kernel_denotes K;",
            "  fully_registered_truth_lexical_application := "
            "concrete_registered_kernel_lexical_application K;",
        ]
    )
    bridge_fields = [
        (
            f"fully_registered_truth_sigma_{type_name}",
            f"concrete_registered_kernel_sigma_{type_name} K",
        )
        for type_name in declarations["types"]
    ]
    bridge_fields.extend(
        [
            ("fully_registered_truth_repeat", "concrete_registered_kernel_repeat K"),
            ("fully_registered_truth_at_T", "concrete_registered_kernel_at_T K"),
            ("fully_registered_truth_during_T", "concrete_registered_kernel_during_T K"),
            ("fully_registered_truth_before_T", "concrete_registered_kernel_before_T K"),
            ("fully_registered_truth_after_T", "concrete_registered_kernel_after_T K"),
            ("fully_registered_truth_until_T", "concrete_registered_kernel_until_T K"),
            ("fully_registered_truth_since_T", "concrete_registered_kernel_since_T K"),
            ("fully_registered_truth_not_T", "concrete_registered_kernel_not_T K"),
            ("fully_registered_truth_transition", "concrete_registered_kernel_transition K"),
            ("fully_registered_truth_cause", "concrete_registered_kernel_cause K"),
        ]
    )
    for index, (field, value) in enumerate(bridge_fields):
        suffix = ";" if index < len(bridge_fields) - 1 else ""
        lines.append(f"  {field} := {value}{suffix}")
    lines.extend(
        [
            "|}.",
            "",
            "Definition concrete_registered_truth_kernel_denotes : "
            "forall A : Type, A -> Prop :=",
            "  ConcreteRegisteredTruth.",
            "",
            "Definition concrete_registered_truth_kernel : "
            "ConcreteRegisteredTruthKernel := {|",
            "  concrete_registered_kernel_denotes := "
            "concrete_registered_truth_kernel_denotes;",
            "  concrete_registered_kernel_lexical_application :=",
            "    fun A term h => concrete_registered_truth_atomic A term",
            "      (concrete_registered_atomic_truth_lexical_application A term h);",
        ]
    )
    model_fields = [
        (
            f"concrete_registered_kernel_sigma_{type_name}",
            f"fun P h => concrete_registered_truth_sigma_{type_name} P h",
        )
        for type_name in declarations["types"]
    ]
    model_fields.extend(
        [
            ("concrete_registered_kernel_repeat", "fun n body h => concrete_registered_truth_repeat n body h"),
            ("concrete_registered_kernel_at_T", "fun marker body h => concrete_registered_truth_at_T marker body h"),
            ("concrete_registered_kernel_during_T", "fun marker body h => concrete_registered_truth_during_T marker body h"),
            ("concrete_registered_kernel_before_T", "fun marker body h => concrete_registered_truth_before_T marker body h"),
            ("concrete_registered_kernel_after_T", "fun marker body h => concrete_registered_truth_after_T marker body h"),
            ("concrete_registered_kernel_until_T", "fun marker body h => concrete_registered_truth_until_T marker body h"),
            ("concrete_registered_kernel_since_T", "fun marker body h => concrete_registered_truth_since_T marker body h"),
            ("concrete_registered_kernel_not_T", "fun body h => concrete_registered_truth_not_T body h"),
            (
                "concrete_registered_kernel_transition",
                "fun theme scale source target h => "
                "concrete_registered_truth_atomic TransitionT "
                "(Transition theme scale source target) "
                "(concrete_registered_atomic_truth_transition "
                "theme scale source target h)",
            ),
            ("concrete_registered_kernel_cause", "fun causer effect h => concrete_registered_truth_cause causer effect h"),
        ]
    )
    for index, (field, value) in enumerate(model_fields):
        suffix = ";" if index < len(model_fields) - 1 else ""
        lines.append(f"  {field} := {value}{suffix}")
    lines.extend(
        [
            "|}.",
            "",
            "Definition concrete_registered_truth_conditions_from_kernel :",
            "  FullyRegisteredTruthConditionSpec :=",
            "  fully_registered_truth_conditions_from_concrete_registered_kernel",
            "    concrete_registered_truth_kernel.",
            "",
            "Theorem concrete_registered_truth_kernel_exists :",
            "  exists K : ConcreteRegisteredTruthKernel,",
            "    K = concrete_registered_truth_kernel.",
            "Proof.",
            "  exists concrete_registered_truth_kernel. reflexivity.",
            "Qed.",
            "",
            "Theorem concrete_registered_truth_conditions_from_kernel_exists :",
            "  exists F : FullyRegisteredTruthConditionSpec,",
            "    F = concrete_registered_truth_conditions_from_kernel.",
            "Proof.",
            "  exists concrete_registered_truth_conditions_from_kernel. reflexivity.",
            "Qed.",
            "",
            "Theorem concrete_registered_truth_kernel_denotes_concrete_registered :",
            "  forall A : Type, forall term : A,",
            "    ConcreteRegisteredTruth A term ->",
            "    concrete_registered_kernel_denotes "
            "concrete_registered_truth_kernel A term.",
            "Proof.",
            "  intros A term H.",
            "  exact H.",
            "Qed.",
            "",
            "Theorem concrete_registered_truth_conditions_from_kernel_denote_concrete_registered :",
            "  forall A : Type, forall term : A,",
            "    ConcreteRegisteredTruth A term ->",
            "    fully_registered_truth_denotes "
            "concrete_registered_truth_conditions_from_kernel A term.",
            "Proof.",
            "  intros A term H.",
            "  exact H.",
            "Qed.",
            "",
            "Theorem concrete_registered_truth_conditions_from_kernel_imply_atomic_closure :",
            "  forall A : Type, forall term : A,",
            "    fully_registered_truth_denotes "
            "concrete_registered_truth_conditions_from_kernel A term ->",
            "    AtomicClosureTruth A term.",
            "Proof.",
            "  intros A term H.",
            "  apply concrete_registered_truth_implies_atomic_closure.",
            "  exact H.",
            "Qed.",
        ]
    )
    return lines


def concrete_registered_truth_proof_steps(
    term: Term,
    target: str,
) -> list[str]:
    prefix = "ConcreteRegisteredTruth." if target == "lean" else ""
    atomic_prefix = "ConcreteRegisteredAtomicTruth." if target == "lean" else ""
    suffix = "" if target == "lean" else "."

    def apply_constructor(name: str) -> str:
        return f"  apply {prefix}{name}{suffix}"

    def prove(current: Term, bound_types: dict[str, str]) -> list[str]:
        kind = current["kind"]
        if kind == "application":
            schema = lexical_application_schema(current, target, bound_types)
            constructor = registered_lexical_application_constructor_from_schema(schema)
            if target == "lean":
                binder_args = " ".join(name for name, _type_name in schema[-1])
                registered_term = (
                    f"RegisteredLexicalApplicationTruth.{constructor}"
                    + (f" {binder_args}" if binder_args else "")
                )
                return [
                    apply_constructor("concrete_registered_truth_atomic"),
                    "  exact "
                    f"{atomic_prefix}concrete_registered_atomic_truth_lexical_application "
                    f"_ _ {registered_term}",
                ]
            return [
                apply_constructor("concrete_registered_truth_atomic"),
                "  apply concrete_registered_atomic_truth_lexical_application.",
                f"  apply {constructor}.",
            ]
        if kind == "sigma":
            witness = export_atom(current["witness"], target)
            witness_type = export_type_name(current["type"], target)
            return [
                apply_constructor(f"concrete_registered_truth_sigma_{witness_type}"),
                f"  intro {witness}{suffix}",
                *prove(current["body"], {**bound_types, witness: witness_type}),
            ]
        if kind == "repeat":
            return [
                apply_constructor("concrete_registered_truth_repeat"),
                *prove(current["body"], bound_types),
            ]
        if kind == "time":
            operator = export_atom(current["operator"] + "_T", target)
            return [
                apply_constructor(f"concrete_registered_truth_{operator}"),
                *prove(current["body"], bound_types),
            ]
        if kind == "not":
            return [
                apply_constructor("concrete_registered_truth_not_T"),
                *prove(current["body"], bound_types),
            ]
        if kind == "transition":
            theme = export_atom(current["theme"], target)
            scale = export_atom(current["state_scale"], target)
            source = export_atom(current["source_state"], target)
            target_state = export_atom(current["target_state"], target)
            registered_constructor = registered_state_transition_constructor(
                theme,
                scale,
                source,
                target_state,
            )
            if target == "lean":
                return [
                    apply_constructor("concrete_registered_truth_atomic"),
                    "  exact "
                    f"{atomic_prefix}concrete_registered_atomic_truth_transition "
                    f"{theme} {scale} {source} {target_state} "
                    f"RegisteredStateTransitionTruth.{registered_constructor}",
                ]
            return [
                apply_constructor("concrete_registered_truth_atomic"),
                "  apply concrete_registered_atomic_truth_transition.",
                f"  apply {registered_constructor}.",
            ]
        if kind == "cause":
            return [
                apply_constructor("concrete_registered_truth_cause"),
                *prove(current["effect"], bound_types),
            ]
        raise ValueError(f"Unknown term kind: {kind!r}")

    return prove(term, {})


def registered_example_truth_instance_lines(
    results: list[dict[str, Any]],
    target: str,
) -> list[str]:
    """Package the exported examples' fully registered truth proofs."""

    if target == "lean":
        lines = ["structure RegisteredExampleTruthInstances : Type where"]
        for idx, result in enumerate(results, 1):
            annotation = export_result_type(result["ast"])
            lines.append(
                f"  example_{idx}_truth_instance : "
                "fully_registered_truth_conditions."
                f"fully_registered_truth_denotes {annotation} example_{idx}"
            )
        lines.extend(
            [
                "",
                "def registered_example_truth_instances : "
                "RegisteredExampleTruthInstances := {",
            ]
        )
        for idx in range(1, len(results) + 1):
            suffix = "," if idx < len(results) else ""
            lines.append(
                f"  example_{idx}_truth_instance := "
                f"example_{idx}_fully_registered_truth_condition_sound{suffix}"
            )
        lines.extend(
            [
                "}",
                "",
                "theorem registered_example_truth_instances_exists :",
                "    Exists (fun I : RegisteredExampleTruthInstances => "
                "I = registered_example_truth_instances) := by",
                "  exact Exists.intro registered_example_truth_instances rfl",
            ]
        )
        for idx, result in enumerate(results, 1):
            annotation = export_result_type(result["ast"])
            lines.extend(
                [
                    "",
                    "theorem "
                    f"registered_example_{idx}_truth_instance_atomic_sound : "
                    f"AtomicClosureTruth {annotation} example_{idx} := by",
                    "  apply fully_registered_truth_conditions_imply_atomic_closure",
                    "  exact registered_example_truth_instances."
                    f"example_{idx}_truth_instance",
                ]
            )
        return lines

    lines = ["Record RegisteredExampleTruthInstances : Type := {"]
    for idx, result in enumerate(results, 1):
        annotation = export_result_type(result["ast"])
        suffix = ";" if idx < len(results) else ""
        lines.extend(
            [
                f"  example_{idx}_truth_instance :",
                "      fully_registered_truth_denotes "
                "fully_registered_truth_conditions "
                f"{annotation} example_{idx}{suffix}",
            ]
        )
    lines.extend(
        [
            "}.",
            "",
            "Definition registered_example_truth_instances : "
            "RegisteredExampleTruthInstances := {|",
        ]
    )
    for idx in range(1, len(results) + 1):
        suffix = ";" if idx < len(results) else ""
        lines.append(
            f"  example_{idx}_truth_instance := "
            f"example_{idx}_fully_registered_truth_condition_sound{suffix}"
        )
    lines.extend(
        [
            "|}.",
            "",
            "Theorem registered_example_truth_instances_exists :",
            "  exists I : RegisteredExampleTruthInstances,",
            "    I = registered_example_truth_instances.",
            "Proof.",
            "  exists registered_example_truth_instances. reflexivity.",
            "Qed.",
        ]
    )
    for idx, result in enumerate(results, 1):
        annotation = export_result_type(result["ast"])
        lines.extend(
            [
                "",
                "Theorem "
                f"registered_example_{idx}_truth_instance_atomic_sound : "
                f"AtomicClosureTruth {annotation} example_{idx}.",
                "Proof.",
                "  apply fully_registered_truth_conditions_imply_atomic_closure.",
                "  exact (example_"
                f"{idx}_truth_instance registered_example_truth_instances).",
                "Qed.",
            ]
        )
    return lines


def finite_registered_truth_condition_instance_ledger_lines(
    results: list[dict[str, Any]],
    target: str,
) -> list[str]:
    """Gather the finite registered truth-condition routes in one ledger."""

    if target == "lean":
        lines = [
            "structure FiniteRegisteredTruthConditionInstanceLedger : Type where",
            "  finite_registered_ledger_route : ConcreteRegisteredTruthConditionRoute",
            "  finite_registered_ledger_route_eq :",
            "      finite_registered_ledger_route = concrete_registered_truth_condition_route",
            "  finite_registered_ledger_sources : IndependentRegisteredTruthConditionSources",
            "  finite_registered_ledger_sources_eq :",
            "      finite_registered_ledger_sources = "
            "independent_registered_truth_condition_sources",
            "  finite_registered_ledger_suite : "
            "IndependentRegisteredTruthConditionInstanceSuite",
            "  finite_registered_ledger_suite_eq :",
            "      finite_registered_ledger_suite = "
            "independent_registered_truth_condition_instance_suite",
            "  finite_registered_ledger_suite_examples :",
            "      IndependentRegisteredTruthConditionInstanceSuiteExamplePackage",
            "  finite_registered_ledger_suite_examples_eq :",
            "      finite_registered_ledger_suite_examples =",
            "        independent_registered_truth_condition_instance_suite_example_package",
            "  finite_registered_ledger_registered_examples : "
            "RegisteredExampleTruthInstances",
            "  finite_registered_ledger_registered_examples_eq :",
            "      finite_registered_ledger_registered_examples = "
            "registered_example_truth_instances",
            "  finite_registered_ledger_concrete_examples : "
            "ConcreteRegisteredExampleTruthInstances",
            "  finite_registered_ledger_concrete_examples_eq :",
            "      finite_registered_ledger_concrete_examples = "
            "concrete_registered_example_truth_instances",
            "  finite_registered_ledger_kernel_examples : "
            "ConcreteRegisteredKernelExampleTruthInstances",
            "  finite_registered_ledger_kernel_examples_eq :",
            "      finite_registered_ledger_kernel_examples = "
            "concrete_registered_kernel_example_truth_instances",
            "",
            "def finite_registered_truth_condition_instance_ledger :",
            "    FiniteRegisteredTruthConditionInstanceLedger := {",
            "  finite_registered_ledger_route := "
            "concrete_registered_truth_condition_route,",
            "  finite_registered_ledger_route_eq := rfl,",
            "  finite_registered_ledger_sources := "
            "independent_registered_truth_condition_sources,",
            "  finite_registered_ledger_sources_eq := rfl,",
            "  finite_registered_ledger_suite := "
            "independent_registered_truth_condition_instance_suite,",
            "  finite_registered_ledger_suite_eq := rfl,",
            "  finite_registered_ledger_suite_examples :=",
            "    independent_registered_truth_condition_instance_suite_example_package,",
            "  finite_registered_ledger_suite_examples_eq := rfl,",
            "  finite_registered_ledger_registered_examples := "
            "registered_example_truth_instances,",
            "  finite_registered_ledger_registered_examples_eq := rfl,",
            "  finite_registered_ledger_concrete_examples := "
            "concrete_registered_example_truth_instances,",
            "  finite_registered_ledger_concrete_examples_eq := rfl,",
            "  finite_registered_ledger_kernel_examples := "
            "concrete_registered_kernel_example_truth_instances,",
            "  finite_registered_ledger_kernel_examples_eq := rfl",
            "}",
            "",
            "theorem finite_registered_truth_condition_instance_ledger_exists :",
            "    Exists (fun L : FiniteRegisteredTruthConditionInstanceLedger => "
            "L = finite_registered_truth_condition_instance_ledger) := by",
            "  exact Exists.intro finite_registered_truth_condition_instance_ledger rfl",
        ]
        for field, target_name in (
            ("route", "concrete_registered_truth_condition_route"),
            ("sources", "independent_registered_truth_condition_sources"),
            ("suite", "independent_registered_truth_condition_instance_suite"),
            (
                "suite_examples",
                "independent_registered_truth_condition_instance_suite_example_package",
            ),
            ("registered_examples", "registered_example_truth_instances"),
            ("concrete_examples", "concrete_registered_example_truth_instances"),
            ("kernel_examples", "concrete_registered_kernel_example_truth_instances"),
        ):
            lines.extend(
                [
                    "",
                    "theorem "
                    f"finite_registered_truth_condition_instance_ledger_{field}_matches :",
                    "    finite_registered_truth_condition_instance_ledger."
                    f"finite_registered_ledger_{field} =",
                    f"      {target_name} := by",
                    "  exact finite_registered_truth_condition_instance_ledger."
                    f"finite_registered_ledger_{field}_eq",
                ]
            )
        for idx, result in enumerate(results, 1):
            annotation = export_result_type(result["ast"])
            lines.extend(
                [
                    "",
                    "theorem "
                    f"finite_registered_truth_condition_ledger_example_{idx}_suite_atomic_sound :",
                    f"    AtomicClosureTruth {annotation} example_{idx} := by",
                    "  exact finite_registered_truth_condition_instance_ledger."
                    "finite_registered_ledger_suite_examples."
                    f"example_{idx}_suite_atomic_sound",
                    "",
                    "theorem "
                    f"finite_registered_truth_condition_ledger_example_{idx}_registered_atomic_sound :",
                    f"    AtomicClosureTruth {annotation} example_{idx} := by",
                    "  apply fully_registered_truth_conditions_imply_atomic_closure",
                    "  exact finite_registered_truth_condition_instance_ledger."
                    "finite_registered_ledger_registered_examples."
                    f"example_{idx}_truth_instance",
                    "",
                    "theorem "
                    f"finite_registered_truth_condition_ledger_example_{idx}_concrete_atomic_sound :",
                    f"    AtomicClosureTruth {annotation} example_{idx} := by",
                    "  apply concrete_registered_truth_conditions_imply_atomic_closure",
                    "  exact finite_registered_truth_condition_instance_ledger."
                    "finite_registered_ledger_concrete_examples."
                    f"example_{idx}_concrete_truth_instance",
                    "",
                    "theorem "
                    f"finite_registered_truth_condition_ledger_example_{idx}_kernel_atomic_sound :",
                    f"    AtomicClosureTruth {annotation} example_{idx} := by",
                    "  apply "
                    "concrete_registered_truth_conditions_from_kernel_imply_atomic_closure",
                    "  exact finite_registered_truth_condition_instance_ledger."
                    "finite_registered_ledger_kernel_examples."
                    f"example_{idx}_kernel_truth_instance",
                ]
            )
        return lines

    lines = [
        "Record FiniteRegisteredTruthConditionInstanceLedger : Type := {",
        "  finite_registered_ledger_route : ConcreteRegisteredTruthConditionRoute;",
        "  finite_registered_ledger_route_eq :",
        "      finite_registered_ledger_route = concrete_registered_truth_condition_route;",
        "  finite_registered_ledger_sources : IndependentRegisteredTruthConditionSources;",
        "  finite_registered_ledger_sources_eq :",
        "      finite_registered_ledger_sources = "
        "independent_registered_truth_condition_sources;",
        "  finite_registered_ledger_suite : "
        "IndependentRegisteredTruthConditionInstanceSuite;",
        "  finite_registered_ledger_suite_eq :",
        "      finite_registered_ledger_suite = "
        "independent_registered_truth_condition_instance_suite;",
        "  finite_registered_ledger_suite_examples :",
        "      IndependentRegisteredTruthConditionInstanceSuiteExamplePackage;",
        "  finite_registered_ledger_suite_examples_eq :",
        "      finite_registered_ledger_suite_examples =",
        "        independent_registered_truth_condition_instance_suite_example_package;",
        "  finite_registered_ledger_registered_examples : "
        "RegisteredExampleTruthInstances;",
        "  finite_registered_ledger_registered_examples_eq :",
        "      finite_registered_ledger_registered_examples = "
        "registered_example_truth_instances;",
        "  finite_registered_ledger_concrete_examples : "
        "ConcreteRegisteredExampleTruthInstances;",
        "  finite_registered_ledger_concrete_examples_eq :",
        "      finite_registered_ledger_concrete_examples = "
        "concrete_registered_example_truth_instances;",
        "  finite_registered_ledger_kernel_examples : "
        "ConcreteRegisteredKernelExampleTruthInstances;",
        "  finite_registered_ledger_kernel_examples_eq :",
        "      finite_registered_ledger_kernel_examples = "
        "concrete_registered_kernel_example_truth_instances",
        "}.",
        "",
        "Definition finite_registered_truth_condition_instance_ledger :",
        "  FiniteRegisteredTruthConditionInstanceLedger := {|",
        "  finite_registered_ledger_route := concrete_registered_truth_condition_route;",
        "  finite_registered_ledger_route_eq := eq_refl;",
        "  finite_registered_ledger_sources := independent_registered_truth_condition_sources;",
        "  finite_registered_ledger_sources_eq := eq_refl;",
        "  finite_registered_ledger_suite := "
        "independent_registered_truth_condition_instance_suite;",
        "  finite_registered_ledger_suite_eq := eq_refl;",
        "  finite_registered_ledger_suite_examples :=",
        "    independent_registered_truth_condition_instance_suite_example_package;",
        "  finite_registered_ledger_suite_examples_eq := eq_refl;",
        "  finite_registered_ledger_registered_examples := registered_example_truth_instances;",
        "  finite_registered_ledger_registered_examples_eq := eq_refl;",
        "  finite_registered_ledger_concrete_examples := concrete_registered_example_truth_instances;",
        "  finite_registered_ledger_concrete_examples_eq := eq_refl;",
        "  finite_registered_ledger_kernel_examples := concrete_registered_kernel_example_truth_instances;",
        "  finite_registered_ledger_kernel_examples_eq := eq_refl",
        "|}.",
        "",
        "Theorem finite_registered_truth_condition_instance_ledger_exists :",
        "  exists L : FiniteRegisteredTruthConditionInstanceLedger,",
        "    L = finite_registered_truth_condition_instance_ledger.",
        "Proof.",
        "  exists finite_registered_truth_condition_instance_ledger.",
        "  reflexivity.",
        "Qed.",
    ]
    for field, target_name in (
        ("route", "concrete_registered_truth_condition_route"),
        ("sources", "independent_registered_truth_condition_sources"),
        ("suite", "independent_registered_truth_condition_instance_suite"),
        (
            "suite_examples",
            "independent_registered_truth_condition_instance_suite_example_package",
        ),
        ("registered_examples", "registered_example_truth_instances"),
        ("concrete_examples", "concrete_registered_example_truth_instances"),
        ("kernel_examples", "concrete_registered_kernel_example_truth_instances"),
    ):
        lines.extend(
            [
                "",
                "Theorem "
                f"finite_registered_truth_condition_instance_ledger_{field}_matches :",
                f"  finite_registered_ledger_{field}",
                "    finite_registered_truth_condition_instance_ledger =",
                f"  {target_name}.",
                "Proof.",
                f"  exact (finite_registered_ledger_{field}_eq",
                "    finite_registered_truth_condition_instance_ledger).",
                "Qed.",
            ]
        )
    for idx, result in enumerate(results, 1):
        annotation = export_result_type(result["ast"])
        lines.extend(
            [
                "",
                "Theorem "
                f"finite_registered_truth_condition_ledger_example_{idx}_suite_atomic_sound :",
                f"  AtomicClosureTruth {annotation} example_{idx}.",
                "Proof.",
                f"  exact (example_{idx}_suite_atomic_sound",
                "    (finite_registered_ledger_suite_examples",
                "      finite_registered_truth_condition_instance_ledger)).",
                "Qed.",
                "",
                "Theorem "
                f"finite_registered_truth_condition_ledger_example_{idx}_registered_atomic_sound :",
                f"  AtomicClosureTruth {annotation} example_{idx}.",
                "Proof.",
                "  apply fully_registered_truth_conditions_imply_atomic_closure.",
                f"  exact (example_{idx}_truth_instance",
                "    (finite_registered_ledger_registered_examples",
                "      finite_registered_truth_condition_instance_ledger)).",
                "Qed.",
                "",
                "Theorem "
                f"finite_registered_truth_condition_ledger_example_{idx}_concrete_atomic_sound :",
                f"  AtomicClosureTruth {annotation} example_{idx}.",
                "Proof.",
                "  apply concrete_registered_truth_conditions_imply_atomic_closure.",
                f"  exact (example_{idx}_concrete_truth_instance",
                "    (finite_registered_ledger_concrete_examples",
                "      finite_registered_truth_condition_instance_ledger)).",
                "Qed.",
                "",
                "Theorem "
                f"finite_registered_truth_condition_ledger_example_{idx}_kernel_atomic_sound :",
                f"  AtomicClosureTruth {annotation} example_{idx}.",
                "Proof.",
                "  apply "
                "concrete_registered_truth_conditions_from_kernel_imply_atomic_closure.",
                f"  exact (example_{idx}_kernel_truth_instance",
                "    (finite_registered_ledger_kernel_examples",
                "      finite_registered_truth_condition_instance_ledger)).",
                "Qed.",
            ]
        )
    return lines


def finite_registered_truth_condition_completion_certificate_lines(
    results: list[dict[str, Any]],
    target: str,
) -> list[str]:
    """Certify that the finite registered routes share atomic closure."""

    if target == "lean":
        lines = [
            "structure FiniteRegisteredTruthConditionCompletionCertificate : "
            "Type where",
            "  finite_registered_completion_ledger : "
            "FiniteRegisteredTruthConditionInstanceLedger",
            "  finite_registered_completion_ledger_eq :",
            "      finite_registered_completion_ledger = "
            "finite_registered_truth_condition_instance_ledger",
            "  finite_registered_completion_registered_sound :",
            "      (A : Type) -> (term : A) ->",
            "      fully_registered_truth_conditions."
            "fully_registered_truth_denotes A term ->",
            "      AtomicClosureTruth A term",
            "  finite_registered_completion_direct_sound :",
            "      (A : Type) -> (term : A) ->",
            "      finite_registered_completion_ledger."
            "finite_registered_ledger_route."
            "concrete_registered_route_direct_spec."
            "fully_registered_truth_denotes A term ->",
            "      AtomicClosureTruth A term",
            "  finite_registered_completion_evidence_sound :",
            "      (A : Type) -> (term : A) ->",
            "      finite_registered_completion_ledger."
            "finite_registered_ledger_route."
            "concrete_registered_route_evidence_spec."
            "fully_registered_truth_denotes A term ->",
            "      AtomicClosureTruth A term",
            "  finite_registered_completion_kernel_sound :",
            "      (A : Type) -> (term : A) ->",
            "      finite_registered_completion_ledger."
            "finite_registered_ledger_route."
            "concrete_registered_route_kernel_spec."
            "fully_registered_truth_denotes A term ->",
            "      AtomicClosureTruth A term",
            "  finite_registered_completion_source_sound :",
            "      (A : Type) -> (term : A) ->",
            "      finite_registered_completion_ledger."
            "finite_registered_ledger_sources."
            "independent_registered_truth_condition_spec."
            "fully_registered_truth_denotes A term ->",
            "      AtomicClosureTruth A term",
            "  finite_registered_completion_suite_sound :",
            "      (A : Type) -> (term : A) ->",
            "      independent_registered_truth_condition_clause_instances."
            "independent_registered_clause_spec."
            "fully_registered_truth_denotes A term ->",
            "      AtomicClosureTruth A term",
            "",
            "def finite_registered_truth_condition_completion_certificate :",
            "    FiniteRegisteredTruthConditionCompletionCertificate := {",
            "  finite_registered_completion_ledger := "
            "finite_registered_truth_condition_instance_ledger,",
            "  finite_registered_completion_ledger_eq := rfl,",
            "  finite_registered_completion_registered_sound := by",
            "    intro A term h",
            "    apply fully_registered_truth_conditions_imply_atomic_closure",
            "    exact h,",
            "  finite_registered_completion_direct_sound := by",
            "    intro A term h",
            "    apply concrete_registered_truth_condition_route_direct_spec_sound",
            "    exact h,",
            "  finite_registered_completion_evidence_sound := by",
            "    intro A term h",
            "    apply concrete_registered_truth_condition_route_evidence_spec_sound",
            "    exact h,",
            "  finite_registered_completion_kernel_sound := by",
            "    intro A term h",
            "    apply concrete_registered_truth_condition_route_kernel_spec_sound",
            "    exact h,",
            "  finite_registered_completion_source_sound := by",
            "    intro A term h",
            "    apply independent_registered_truth_condition_sources_spec_sound",
            "    exact h,",
            "  finite_registered_completion_suite_sound := by",
            "    intro A term h",
            "    exact finite_registered_truth_condition_instance_ledger."
            "finite_registered_ledger_suite."
            "independent_registered_suite_spec_sound A term h",
            "}",
            "",
            "theorem finite_registered_truth_condition_completion_certificate_exists :",
            "    Exists (fun C : "
            "FiniteRegisteredTruthConditionCompletionCertificate => "
            "C = finite_registered_truth_condition_completion_certificate) := by",
            "  exact Exists.intro "
            "finite_registered_truth_condition_completion_certificate rfl",
            "",
            "theorem finite_registered_truth_condition_completion_ledger_matches :",
            "    finite_registered_truth_condition_completion_certificate."
            "finite_registered_completion_ledger =",
            "      finite_registered_truth_condition_instance_ledger := by",
            "  exact finite_registered_truth_condition_completion_certificate."
            "finite_registered_completion_ledger_eq",
        ]
        sound_theorems = [
            (
                "registered_spec",
                "fully_registered_truth_conditions."
                "fully_registered_truth_denotes A term",
                "finite_registered_completion_registered_sound",
            ),
            (
                "direct_spec",
                "finite_registered_truth_condition_completion_certificate."
                "finite_registered_completion_ledger."
                "finite_registered_ledger_route."
                "concrete_registered_route_direct_spec."
                "fully_registered_truth_denotes A term",
                "finite_registered_completion_direct_sound",
            ),
            (
                "evidence_spec",
                "finite_registered_truth_condition_completion_certificate."
                "finite_registered_completion_ledger."
                "finite_registered_ledger_route."
                "concrete_registered_route_evidence_spec."
                "fully_registered_truth_denotes A term",
                "finite_registered_completion_evidence_sound",
            ),
            (
                "kernel_spec",
                "finite_registered_truth_condition_completion_certificate."
                "finite_registered_completion_ledger."
                "finite_registered_ledger_route."
                "concrete_registered_route_kernel_spec."
                "fully_registered_truth_denotes A term",
                "finite_registered_completion_kernel_sound",
            ),
            (
                "source_spec",
                "finite_registered_truth_condition_completion_certificate."
                "finite_registered_completion_ledger."
                "finite_registered_ledger_sources."
                "independent_registered_truth_condition_spec."
                "fully_registered_truth_denotes A term",
                "finite_registered_completion_source_sound",
            ),
            (
                "suite_spec",
                "independent_registered_truth_condition_clause_instances."
                "independent_registered_clause_spec."
                "fully_registered_truth_denotes A term",
                "finite_registered_completion_suite_sound",
            ),
        ]
        for name, premise, field_name in sound_theorems:
            lines.extend(
                [
                    "",
                    "theorem "
                    f"finite_registered_truth_condition_completion_{name}_sound :",
                    "    (A : Type) -> (term : A) ->",
                    f"    {premise} ->",
                    "    AtomicClosureTruth A term := by",
                    "  intro A term h",
                    "  exact finite_registered_truth_condition_completion_certificate."
                    f"{field_name} A term h",
                ]
            )
        for idx, result in enumerate(results, 1):
            annotation = export_result_type(result["ast"])
            lines.extend(
                [
                    "",
                    "theorem "
                    f"finite_registered_truth_condition_completion_example_{idx}_registered_atomic_sound :",
                    f"    AtomicClosureTruth {annotation} example_{idx} := by",
                    "  apply "
                    "finite_registered_truth_condition_completion_registered_spec_sound",
                    "  exact finite_registered_truth_condition_completion_certificate."
                    "finite_registered_completion_ledger."
                    "finite_registered_ledger_registered_examples."
                    f"example_{idx}_truth_instance",
                    "",
                    "theorem "
                    f"finite_registered_truth_condition_completion_example_{idx}_direct_atomic_sound :",
                    f"    AtomicClosureTruth {annotation} example_{idx} := by",
                    "  apply "
                    "finite_registered_truth_condition_completion_direct_spec_sound",
                    "  exact finite_registered_truth_condition_completion_certificate."
                    "finite_registered_completion_ledger."
                    "finite_registered_ledger_route."
                    "concrete_registered_route_direct_examples."
                    f"example_{idx}_concrete_truth_instance",
                    "",
                    "theorem "
                    f"finite_registered_truth_condition_completion_example_{idx}_evidence_atomic_sound :",
                    f"    AtomicClosureTruth {annotation} example_{idx} := by",
                    "  apply "
                    "finite_registered_truth_condition_completion_evidence_spec_sound",
                    "  exact finite_registered_truth_condition_completion_certificate."
                    "finite_registered_completion_ledger."
                    "finite_registered_ledger_route."
                    "concrete_registered_route_evidence_examples."
                    f"example_{idx}_evidence_backed_truth_instance",
                    "",
                    "theorem "
                    f"finite_registered_truth_condition_completion_example_{idx}_kernel_atomic_sound :",
                    f"    AtomicClosureTruth {annotation} example_{idx} := by",
                    "  apply "
                    "finite_registered_truth_condition_completion_kernel_spec_sound",
                    "  exact finite_registered_truth_condition_completion_certificate."
                    "finite_registered_completion_ledger."
                    "finite_registered_ledger_route."
                    "concrete_registered_route_kernel_examples."
                    f"example_{idx}_kernel_truth_instance",
                    "",
                    "theorem "
                    f"finite_registered_truth_condition_completion_example_{idx}_source_atomic_sound :",
                    f"    AtomicClosureTruth {annotation} example_{idx} := by",
                    "  apply "
                    "finite_registered_truth_condition_completion_source_spec_sound",
                    "  exact finite_registered_truth_condition_completion_certificate."
                    "finite_registered_completion_ledger."
                    "finite_registered_ledger_sources."
                    "independent_registered_truth_condition_examples."
                    f"example_{idx}_concrete_truth_instance",
                    "",
                    "theorem "
                    f"finite_registered_truth_condition_completion_example_{idx}_suite_atomic_sound :",
                    f"    AtomicClosureTruth {annotation} example_{idx} := by",
                    "  exact finite_registered_truth_condition_completion_certificate."
                    "finite_registered_completion_ledger."
                    "finite_registered_ledger_suite_examples."
                    f"example_{idx}_suite_atomic_sound",
                ]
            )
        return lines

    lines = [
        "Record FiniteRegisteredTruthConditionCompletionCertificate : Type := {",
        "  finite_registered_completion_ledger : "
        "FiniteRegisteredTruthConditionInstanceLedger;",
        "  finite_registered_completion_ledger_eq :",
        "      finite_registered_completion_ledger = "
        "finite_registered_truth_condition_instance_ledger;",
        "  finite_registered_completion_registered_sound :",
        "      forall A : Type, forall term : A,",
        "      fully_registered_truth_denotes fully_registered_truth_conditions A term ->",
        "      AtomicClosureTruth A term;",
        "  finite_registered_completion_direct_sound :",
        "      forall A : Type, forall term : A,",
        "      fully_registered_truth_denotes",
        "        (concrete_registered_route_direct_spec",
        "          (finite_registered_ledger_route finite_registered_completion_ledger))",
        "        A term ->",
        "      AtomicClosureTruth A term;",
        "  finite_registered_completion_evidence_sound :",
        "      forall A : Type, forall term : A,",
        "      fully_registered_truth_denotes",
        "        (concrete_registered_route_evidence_spec",
        "          (finite_registered_ledger_route finite_registered_completion_ledger))",
        "        A term ->",
        "      AtomicClosureTruth A term;",
        "  finite_registered_completion_kernel_sound :",
        "      forall A : Type, forall term : A,",
        "      fully_registered_truth_denotes",
        "        (concrete_registered_route_kernel_spec",
        "          (finite_registered_ledger_route finite_registered_completion_ledger))",
        "        A term ->",
        "      AtomicClosureTruth A term;",
        "  finite_registered_completion_source_sound :",
        "      forall A : Type, forall term : A,",
        "      fully_registered_truth_denotes",
        "        (independent_registered_truth_condition_spec",
        "          (finite_registered_ledger_sources finite_registered_completion_ledger))",
        "        A term ->",
        "      AtomicClosureTruth A term;",
        "  finite_registered_completion_suite_sound :",
        "      forall A : Type, forall term : A,",
        "      fully_registered_truth_denotes",
        "        (independent_registered_clause_spec",
        "          independent_registered_truth_condition_clause_instances) A term ->",
        "      AtomicClosureTruth A term",
        "}.",
        "",
        "Definition finite_registered_truth_condition_completion_certificate :",
        "  FiniteRegisteredTruthConditionCompletionCertificate := {|",
        "  finite_registered_completion_ledger := "
        "finite_registered_truth_condition_instance_ledger;",
        "  finite_registered_completion_ledger_eq := eq_refl;",
        "  finite_registered_completion_registered_sound :=",
        "    fun A term H =>",
        "      fully_registered_truth_conditions_imply_atomic_closure A term H;",
        "  finite_registered_completion_direct_sound :=",
        "    fun A term H =>",
        "      concrete_registered_truth_condition_route_direct_spec_sound A term H;",
        "  finite_registered_completion_evidence_sound :=",
        "    fun A term H =>",
        "      concrete_registered_truth_condition_route_evidence_spec_sound A term H;",
        "  finite_registered_completion_kernel_sound :=",
        "    fun A term H =>",
        "      concrete_registered_truth_condition_route_kernel_spec_sound A term H;",
        "  finite_registered_completion_source_sound :=",
        "    fun A term H =>",
        "      independent_registered_truth_condition_sources_spec_sound A term H;",
        "  finite_registered_completion_suite_sound :=",
        "    fun A term H =>",
        "      independent_registered_suite_spec_sound",
        "        (finite_registered_ledger_suite",
        "          finite_registered_truth_condition_instance_ledger) A term H",
        "|}.",
        "",
        "Theorem finite_registered_truth_condition_completion_certificate_exists :",
        "  exists C : FiniteRegisteredTruthConditionCompletionCertificate,",
        "    C = finite_registered_truth_condition_completion_certificate.",
        "Proof.",
        "  exists finite_registered_truth_condition_completion_certificate.",
        "  reflexivity.",
        "Qed.",
        "",
        "Theorem finite_registered_truth_condition_completion_ledger_matches :",
        "  finite_registered_completion_ledger",
        "    finite_registered_truth_condition_completion_certificate =",
        "  finite_registered_truth_condition_instance_ledger.",
        "Proof.",
        "  exact (finite_registered_completion_ledger_eq",
        "    finite_registered_truth_condition_completion_certificate).",
        "Qed.",
    ]
    sound_theorems = [
        (
            "registered_spec",
            [
                "fully_registered_truth_denotes "
                "fully_registered_truth_conditions A term",
            ],
            "finite_registered_completion_registered_sound",
        ),
        (
            "direct_spec",
            [
                "fully_registered_truth_denotes",
                "      (concrete_registered_route_direct_spec",
                "        (finite_registered_ledger_route",
                "          (finite_registered_completion_ledger",
                "            finite_registered_truth_condition_completion_certificate)))",
                "      A term",
            ],
            "finite_registered_completion_direct_sound",
        ),
        (
            "evidence_spec",
            [
                "fully_registered_truth_denotes",
                "      (concrete_registered_route_evidence_spec",
                "        (finite_registered_ledger_route",
                "          (finite_registered_completion_ledger",
                "            finite_registered_truth_condition_completion_certificate)))",
                "      A term",
            ],
            "finite_registered_completion_evidence_sound",
        ),
        (
            "kernel_spec",
            [
                "fully_registered_truth_denotes",
                "      (concrete_registered_route_kernel_spec",
                "        (finite_registered_ledger_route",
                "          (finite_registered_completion_ledger",
                "            finite_registered_truth_condition_completion_certificate)))",
                "      A term",
            ],
            "finite_registered_completion_kernel_sound",
        ),
        (
            "source_spec",
            [
                "fully_registered_truth_denotes",
                "      (independent_registered_truth_condition_spec",
                "        (finite_registered_ledger_sources",
                "          (finite_registered_completion_ledger",
                "            finite_registered_truth_condition_completion_certificate)))",
                "      A term",
            ],
            "finite_registered_completion_source_sound",
        ),
        (
            "suite_spec",
            [
                "fully_registered_truth_denotes",
                "      (independent_registered_clause_spec",
                "        independent_registered_truth_condition_clause_instances)",
                "      A term",
            ],
            "finite_registered_completion_suite_sound",
        ),
    ]
    for name, premise_lines, field_name in sound_theorems:
        lines.extend(
            [
                "",
                "Theorem "
                f"finite_registered_truth_condition_completion_{name}_sound :",
                "  forall A : Type, forall term : A,",
            ]
        )
        for line_index, line in enumerate(premise_lines):
            suffix = " ->" if line_index == len(premise_lines) - 1 else ""
            lines.append(f"    {line}{suffix}")
        lines.extend(
            [
                "    AtomicClosureTruth A term.",
                "Proof.",
                "  intros A term H.",
                f"  exact ({field_name}",
                "    finite_registered_truth_condition_completion_certificate A term H).",
                "Qed.",
            ]
        )
    for idx, result in enumerate(results, 1):
        annotation = export_result_type(result["ast"])
        lines.extend(
            [
                "",
                "Theorem "
                f"finite_registered_truth_condition_completion_example_{idx}_registered_atomic_sound :",
                f"  AtomicClosureTruth {annotation} example_{idx}.",
                "Proof.",
                "  apply "
                "finite_registered_truth_condition_completion_registered_spec_sound.",
                f"  exact (example_{idx}_truth_instance",
                "    (finite_registered_ledger_registered_examples",
                "      (finite_registered_completion_ledger",
                "        finite_registered_truth_condition_completion_certificate))).",
                "Qed.",
                "",
                "Theorem "
                f"finite_registered_truth_condition_completion_example_{idx}_direct_atomic_sound :",
                f"  AtomicClosureTruth {annotation} example_{idx}.",
                "Proof.",
                "  apply "
                "finite_registered_truth_condition_completion_direct_spec_sound.",
                f"  exact (example_{idx}_concrete_truth_instance",
                "    (concrete_registered_route_direct_examples",
                "      (finite_registered_ledger_route",
                "        (finite_registered_completion_ledger",
                "          finite_registered_truth_condition_completion_certificate)))).",
                "Qed.",
                "",
                "Theorem "
                f"finite_registered_truth_condition_completion_example_{idx}_evidence_atomic_sound :",
                f"  AtomicClosureTruth {annotation} example_{idx}.",
                "Proof.",
                "  apply "
                "finite_registered_truth_condition_completion_evidence_spec_sound.",
                f"  exact (example_{idx}_evidence_backed_truth_instance",
                "    (concrete_registered_route_evidence_examples",
                "      (finite_registered_ledger_route",
                "        (finite_registered_completion_ledger",
                "          finite_registered_truth_condition_completion_certificate)))).",
                "Qed.",
                "",
                "Theorem "
                f"finite_registered_truth_condition_completion_example_{idx}_kernel_atomic_sound :",
                f"  AtomicClosureTruth {annotation} example_{idx}.",
                "Proof.",
                "  apply "
                "finite_registered_truth_condition_completion_kernel_spec_sound.",
                f"  exact (example_{idx}_kernel_truth_instance",
                "    (concrete_registered_route_kernel_examples",
                "      (finite_registered_ledger_route",
                "        (finite_registered_completion_ledger",
                "          finite_registered_truth_condition_completion_certificate)))).",
                "Qed.",
                "",
                "Theorem "
                f"finite_registered_truth_condition_completion_example_{idx}_source_atomic_sound :",
                f"  AtomicClosureTruth {annotation} example_{idx}.",
                "Proof.",
                "  apply "
                "finite_registered_truth_condition_completion_source_spec_sound.",
                f"  exact (example_{idx}_concrete_truth_instance",
                "    (independent_registered_truth_condition_examples",
                "      (finite_registered_ledger_sources",
                "        (finite_registered_completion_ledger",
                "          finite_registered_truth_condition_completion_certificate)))).",
                "Qed.",
                "",
                "Theorem "
                f"finite_registered_truth_condition_completion_example_{idx}_suite_atomic_sound :",
                f"  AtomicClosureTruth {annotation} example_{idx}.",
                "Proof.",
                f"  exact (example_{idx}_suite_atomic_sound",
                "    (finite_registered_ledger_suite_examples",
                "      (finite_registered_completion_ledger",
                "        finite_registered_truth_condition_completion_certificate))).",
                "Qed.",
            ]
        )
    return lines


def finite_registered_truth_condition_component_coverage_certificate_lines(
    results: list[dict[str, Any]],
    target: str,
) -> list[str]:
    """Package the finite registered truth-condition component witnesses."""

    packages = [
        (
            "lexical",
            "IndependentRegisteredLexicalTruthConditionInstances",
            "independent_registered_lexical_truth_condition_instances",
            "independent_registered_lexical_truth_condition_spec_sound",
        ),
        (
            "temporal",
            "IndependentRegisteredTemporalTruthConditionInstances",
            "independent_registered_temporal_truth_condition_instances",
            "independent_registered_temporal_truth_condition_spec_sound",
        ),
        (
            "sigma",
            "IndependentRegisteredSigmaTruthConditionInstances",
            "independent_registered_sigma_truth_condition_instances",
            "independent_registered_sigma_truth_condition_spec_sound",
        ),
        (
            "repeat",
            "IndependentRegisteredRepeatTruthConditionInstances",
            "independent_registered_repeat_truth_condition_instances",
            "independent_registered_repeat_truth_condition_spec_sound",
        ),
        (
            "polarity",
            "IndependentRegisteredPolarityTruthConditionInstances",
            "independent_registered_polarity_truth_condition_instances",
            "independent_registered_polarity_truth_condition_spec_sound",
        ),
        (
            "transition_cause",
            "IndependentRegisteredTransitionCauseTruthConditionInstances",
            "independent_registered_transition_cause_truth_condition_instances",
            "independent_registered_transition_cause_truth_condition_spec_sound",
        ),
        (
            "suite",
            "IndependentRegisteredTruthConditionInstanceSuite",
            "independent_registered_truth_condition_instance_suite",
            "independent_registered_truth_condition_instance_suite_spec_sound",
        ),
    ]

    if target == "lean":
        lines = [
            "structure "
            "FiniteRegisteredTruthConditionComponentCoverageCertificate : "
            "Type where",
            "  finite_registered_component_completion : "
            "FiniteRegisteredTruthConditionCompletionCertificate",
            "  finite_registered_component_completion_eq :",
            "      finite_registered_component_completion = "
            "finite_registered_truth_condition_completion_certificate",
        ]
        for field, type_name, instance, _sound in packages:
            lines.extend(
                [
                    f"  finite_registered_component_{field} : {type_name}",
                    f"  finite_registered_component_{field}_eq :",
                    f"      finite_registered_component_{field} = {instance}",
                    f"  finite_registered_component_{field}_sound :",
                    "      (A : Type) -> (term : A) ->",
                    "      independent_registered_truth_condition_clause_instances.",
                    "      independent_registered_clause_spec.",
                    "      fully_registered_truth_denotes A term ->",
                    "      AtomicClosureTruth A term",
                ]
            )
        lines.extend(
            [
                "",
                "def finite_registered_truth_condition_component_coverage_certificate :",
                "    FiniteRegisteredTruthConditionComponentCoverageCertificate := {",
                "  finite_registered_component_completion := "
                "finite_registered_truth_condition_completion_certificate,",
                "  finite_registered_component_completion_eq := rfl,",
            ]
        )
        for field, _type_name, instance, sound in packages:
            lines.extend(
                [
                    f"  finite_registered_component_{field} := {instance},",
                    f"  finite_registered_component_{field}_eq := rfl,",
                    f"  finite_registered_component_{field}_sound := {sound},",
                ]
            )
        lines[-1] = lines[-1].rstrip(",")
        lines.extend(
            [
                "}",
                "",
                "theorem "
                "finite_registered_truth_condition_component_coverage_certificate_exists :",
                "    Exists (fun C : "
                "FiniteRegisteredTruthConditionComponentCoverageCertificate => "
                "C = finite_registered_truth_condition_component_coverage_certificate) "
                ":= by",
                "  exact Exists.intro "
                "finite_registered_truth_condition_component_coverage_certificate rfl",
                "",
                "theorem "
                "finite_registered_truth_condition_component_completion_matches :",
                "    finite_registered_truth_condition_component_coverage_certificate."
                "finite_registered_component_completion =",
                "      finite_registered_truth_condition_completion_certificate := by",
                "  exact "
                "finite_registered_truth_condition_component_coverage_certificate."
                "finite_registered_component_completion_eq",
            ]
        )
        for field, _type_name, instance, _sound in packages:
            lines.extend(
                [
                    "",
                    "theorem "
                    f"finite_registered_truth_condition_component_{field}_matches :",
                    "    finite_registered_truth_condition_component_coverage_certificate."
                    f"finite_registered_component_{field} =",
                    f"      {instance} := by",
                    "  exact "
                    "finite_registered_truth_condition_component_coverage_certificate."
                    f"finite_registered_component_{field}_eq",
                ]
            )
        for field, _type_name, _instance, _sound in packages:
            lines.extend(
                [
                    "",
                    "theorem "
                    f"finite_registered_truth_condition_component_{field}_spec_sound :",
                    "    (A : Type) -> (term : A) ->",
                    "    independent_registered_truth_condition_clause_instances.",
                    "    independent_registered_clause_spec.",
                    "    fully_registered_truth_denotes A term ->",
                    "    AtomicClosureTruth A term := by",
                    "  exact "
                    "finite_registered_truth_condition_component_coverage_certificate."
                    f"finite_registered_component_{field}_sound",
                ]
            )
        for idx, result in enumerate(results, 1):
            annotation = export_result_type(result["ast"])
            lines.extend(
                [
                    "",
                    "theorem "
                    f"finite_registered_truth_condition_component_coverage_example_{idx}_atomic_sound :",
                    f"    AtomicClosureTruth {annotation} example_{idx} := by",
                    "  exact "
                    "finite_registered_truth_condition_component_coverage_certificate."
                    "finite_registered_component_completion."
                    "finite_registered_completion_ledger."
                    "finite_registered_ledger_suite_examples."
                    f"example_{idx}_suite_atomic_sound",
                ]
            )
        return lines

    lines = [
        "Record "
        "FiniteRegisteredTruthConditionComponentCoverageCertificate : Type := {",
        "  finite_registered_component_completion : "
        "FiniteRegisteredTruthConditionCompletionCertificate;",
        "  finite_registered_component_completion_eq :",
        "      finite_registered_component_completion = "
        "finite_registered_truth_condition_completion_certificate;",
    ]
    for field, type_name, instance, _sound in packages:
        lines.extend(
            [
                f"  finite_registered_component_{field} : {type_name};",
                f"  finite_registered_component_{field}_eq :",
                f"      finite_registered_component_{field} = {instance};",
                f"  finite_registered_component_{field}_sound :",
                "      forall A : Type, forall term : A,",
                "      fully_registered_truth_denotes",
                "        (independent_registered_clause_spec",
                "          independent_registered_truth_condition_clause_instances)",
                "        A term ->",
                "      AtomicClosureTruth A term;",
            ]
        )
    lines[-1] = lines[-1].rstrip(";")
    lines.extend(
        [
            "}.",
            "",
            "Definition "
            "finite_registered_truth_condition_component_coverage_certificate :",
            "  FiniteRegisteredTruthConditionComponentCoverageCertificate := {|",
            "  finite_registered_component_completion := "
            "finite_registered_truth_condition_completion_certificate;",
            "  finite_registered_component_completion_eq := eq_refl;",
        ]
    )
    for field, _type_name, instance, sound in packages:
        lines.extend(
            [
                f"  finite_registered_component_{field} := {instance};",
                f"  finite_registered_component_{field}_eq := eq_refl;",
                f"  finite_registered_component_{field}_sound := {sound};",
            ]
        )
    lines[-1] = lines[-1].rstrip(";")
    lines.extend(
        [
            "|}.",
            "",
            "Theorem "
            "finite_registered_truth_condition_component_coverage_certificate_exists :",
            "  exists C : "
            "FiniteRegisteredTruthConditionComponentCoverageCertificate,",
            "    C = finite_registered_truth_condition_component_coverage_certificate.",
            "Proof.",
            "  exists finite_registered_truth_condition_component_coverage_certificate.",
            "  reflexivity.",
            "Qed.",
            "",
            "Theorem "
            "finite_registered_truth_condition_component_completion_matches :",
            "  finite_registered_component_completion",
            "    finite_registered_truth_condition_component_coverage_certificate =",
            "  finite_registered_truth_condition_completion_certificate.",
            "Proof.",
            "  exact (finite_registered_component_completion_eq",
            "    finite_registered_truth_condition_component_coverage_certificate).",
            "Qed.",
        ]
    )
    for field, _type_name, instance, _sound in packages:
        lines.extend(
            [
                "",
                "Theorem "
                f"finite_registered_truth_condition_component_{field}_matches :",
                f"  finite_registered_component_{field}",
                "    finite_registered_truth_condition_component_coverage_certificate =",
                f"  {instance}.",
                "Proof.",
                f"  exact (finite_registered_component_{field}_eq",
                "    finite_registered_truth_condition_component_coverage_certificate).",
                "Qed.",
            ]
        )
    for field, _type_name, _instance, _sound in packages:
        lines.extend(
            [
                "",
                "Theorem "
                f"finite_registered_truth_condition_component_{field}_spec_sound :",
                "  forall A : Type, forall term : A,",
                "    fully_registered_truth_denotes",
                "      (independent_registered_clause_spec",
                "        independent_registered_truth_condition_clause_instances)",
                "      A term ->",
                "    AtomicClosureTruth A term.",
                "Proof.",
                f"  exact (finite_registered_component_{field}_sound",
                "    finite_registered_truth_condition_component_coverage_certificate).",
                "Qed.",
            ]
        )
    for idx, result in enumerate(results, 1):
        annotation = export_result_type(result["ast"])
        lines.extend(
            [
                "",
                "Theorem "
                f"finite_registered_truth_condition_component_coverage_example_{idx}_atomic_sound :",
                f"  AtomicClosureTruth {annotation} example_{idx}.",
                "Proof.",
                f"  exact (example_{idx}_suite_atomic_sound",
                "    (finite_registered_ledger_suite_examples",
                "      (finite_registered_completion_ledger",
                "        (finite_registered_component_completion",
                "          finite_registered_truth_condition_component_coverage_certificate)))).",
                "Qed.",
            ]
        )
    return lines


def finite_registered_atomic_witness_certificate_lines(
    declarations: dict[str, Any],
    target: str,
) -> list[str]:
    """Expose each finite registered atom as a concrete witness."""

    schemas: list[LexicalApplicationSchema] = declarations["lexical_applications"]
    transitions: list[tuple[str, str, str, str]] = declarations["transitions"]

    def lean_schema_type(schema: LexicalApplicationSchema, sort: str) -> str:
        _function, result_type, _count, _modifier_term, _modifiers, _args, binders = schema
        application = lexical_application_term(schema)
        conclusion = {
            "concrete": (
                f"ConcreteRegisteredAtomicTruth {result_type} ({application})"
            ),
            "base": f"AtomicBaseTruth {result_type} ({application})",
            "closure": f"AtomicClosureTruth {result_type} ({application})",
        }[sort]
        binder_parts = [f"({name} : {type_name})" for name, type_name in binders]
        return " -> ".join([*binder_parts, conclusion])

    def lean_schema_value(schema: LexicalApplicationSchema, sort: str) -> str:
        constructor = registered_lexical_application_constructor_from_schema(schema)
        _function, result_type, _count, _modifier_term, _modifiers, _args, binders = schema
        application = lexical_application_term(schema)
        binder_names = [name for name, _type_name in binders]
        registered = "RegisteredLexicalApplicationTruth." + constructor
        if binder_names:
            registered += " " + " ".join(binder_names)
        registered = f"({registered})"
        values = {
            "concrete": (
                "ConcreteRegisteredAtomicTruth."
                "concrete_registered_atomic_truth_lexical_application "
                f"{result_type} ({application}) {registered}"
            ),
            "base": (
                "registered_lexical_application_atomic_base_truth "
                f"{result_type} ({application}) {registered}"
            ),
            "closure": (
                "registered_lexical_application_atomic_closure_truth "
                f"{result_type} ({application}) {registered}"
            ),
        }
        value = values[sort]
        if binder_names:
            return f"fun {' '.join(binder_names)} => {value}"
        return value

    def lean_transition_type(
        transition: tuple[str, str, str, str],
        sort: str,
    ) -> str:
        theme, scale, source, target_state = transition
        term = f"(Transition {theme} {scale} {source} {target_state})"
        return {
            "concrete": f"ConcreteRegisteredAtomicTruth TransitionT {term}",
            "base": f"AtomicBaseTruth TransitionT {term}",
            "closure": f"AtomicClosureTruth TransitionT {term}",
        }[sort]

    def lean_transition_value(
        transition: tuple[str, str, str, str],
        sort: str,
    ) -> str:
        theme, scale, source, target_state = transition
        constructor = registered_state_transition_constructor(
            theme,
            scale,
            source,
            target_state,
        )
        registered = f"RegisteredStateTransitionTruth.{constructor}"
        base = (
            "registered_state_transition_atomic_base_truth "
            f"{theme} {scale} {source} {target_state} {registered}"
        )
        return {
            "concrete": (
                "ConcreteRegisteredAtomicTruth."
                "concrete_registered_atomic_truth_transition "
                f"{theme} {scale} {source} {target_state} {registered}"
            ),
            "base": base,
            "closure": (
                "AtomicClosureTruth.atomic_closure_truth_transition "
                f"{theme} {scale} {source} {target_state} ({base})"
            ),
        }[sort]

    def coq_schema_type(schema: LexicalApplicationSchema, sort: str) -> list[str]:
        _function, result_type, _count, _modifier_term, _modifiers, _args, binders = schema
        application = lexical_application_term(schema)
        conclusion = {
            "concrete": (
                f"ConcreteRegisteredAtomicTruth {result_type} ({application})"
            ),
            "base": f"AtomicBaseTruth {result_type} ({application})",
            "closure": f"AtomicClosureTruth {result_type} ({application})",
        }[sort]
        if not binders:
            return [conclusion]
        binder_text = ", ".join(
            f"forall {name} : {type_name}" for name, type_name in binders
        )
        return [f"{binder_text},", f"      {conclusion}"]

    def coq_schema_value(schema: LexicalApplicationSchema, sort: str) -> str:
        constructor = registered_lexical_application_constructor_from_schema(schema)
        _function, result_type, _count, _modifier_term, _modifiers, _args, binders = schema
        application = lexical_application_term(schema)
        binder_names = [name for name, _type_name in binders]
        registered = constructor
        if binder_names:
            registered += " " + " ".join(binder_names)
        registered = f"({registered})"
        values = {
            "concrete": (
                "concrete_registered_atomic_truth_lexical_application "
                f"{result_type} ({application}) {registered}"
            ),
            "base": (
                "registered_lexical_application_atomic_base_truth "
                f"{result_type} ({application}) {registered}"
            ),
            "closure": (
                "registered_lexical_application_atomic_closure_truth "
                f"{result_type} ({application}) {registered}"
            ),
        }
        value = values[sort]
        if binder_names:
            return f"fun {' '.join(binder_names)} => {value}"
        return value

    def coq_transition_type(
        transition: tuple[str, str, str, str],
        sort: str,
    ) -> str:
        theme, scale, source, target_state = transition
        term = f"(Transition {theme} {scale} {source} {target_state})"
        return {
            "concrete": f"ConcreteRegisteredAtomicTruth TransitionT {term}",
            "base": f"AtomicBaseTruth TransitionT {term}",
            "closure": f"AtomicClosureTruth TransitionT {term}",
        }[sort]

    def coq_transition_value(
        transition: tuple[str, str, str, str],
        sort: str,
    ) -> str:
        theme, scale, source, target_state = transition
        constructor = registered_state_transition_constructor(
            theme,
            scale,
            source,
            target_state,
        )
        registered = constructor
        base = (
            "registered_state_transition_atomic_base_truth "
            f"{theme} {scale} {source} {target_state} {registered}"
        )
        return {
            "concrete": (
                "concrete_registered_atomic_truth_transition "
                f"{theme} {scale} {source} {target_state} {registered}"
            ),
            "base": base,
            "closure": (
                "atomic_closure_truth_transition "
                f"{theme} {scale} {source} {target_state} ({base})"
            ),
        }[sort]

    if target == "lean":
        lines = [
            "structure FiniteRegisteredAtomicWitnessCertificate : Type where",
            "  finite_registered_atomic_witness_basis : "
            "ConcreteRegisteredTruthBasis",
            "  finite_registered_atomic_witness_basis_eq :",
            "      finite_registered_atomic_witness_basis = "
            "concrete_registered_truth_basis",
        ]
        for index, schema in enumerate(schemas, 1):
            for sort in ("concrete", "base", "closure"):
                lines.append(
                    f"  finite_registered_atomic_witness_lexical_{index}_{sort} : "
                    f"{lean_schema_type(schema, sort)}"
                )
        for index, transition in enumerate(transitions, 1):
            for sort in ("concrete", "base", "closure"):
                lines.append(
                    f"  finite_registered_atomic_witness_transition_{index}_{sort} : "
                    f"{lean_transition_type(transition, sort)}"
                )
        lines.extend(
            [
                "",
                "def finite_registered_atomic_witness_certificate :",
                "    FiniteRegisteredAtomicWitnessCertificate := {",
                "  finite_registered_atomic_witness_basis := "
                "concrete_registered_truth_basis,",
                "  finite_registered_atomic_witness_basis_eq := rfl,",
            ]
        )
        assignments: list[tuple[str, str]] = []
        for index, schema in enumerate(schemas, 1):
            for sort in ("concrete", "base", "closure"):
                assignments.append(
                    (
                        f"finite_registered_atomic_witness_lexical_{index}_{sort}",
                        lean_schema_value(schema, sort),
                    )
                )
        for index, transition in enumerate(transitions, 1):
            for sort in ("concrete", "base", "closure"):
                assignments.append(
                    (
                        f"finite_registered_atomic_witness_transition_{index}_{sort}",
                        lean_transition_value(transition, sort),
                    )
                )
        for index, (field, value) in enumerate(assignments):
            suffix = "," if index < len(assignments) - 1 else ""
            lines.append(f"  {field} := {value}{suffix}")
        lines.extend(
            [
                "}",
                "",
                "theorem finite_registered_atomic_witness_certificate_exists :",
                "    Exists (fun C : FiniteRegisteredAtomicWitnessCertificate => "
                "C = finite_registered_atomic_witness_certificate) := by",
                "  exact Exists.intro finite_registered_atomic_witness_certificate rfl",
                "",
                "theorem finite_registered_atomic_witness_basis_matches :",
                "    finite_registered_atomic_witness_certificate."
                "finite_registered_atomic_witness_basis =",
                "      concrete_registered_truth_basis := by",
                "  exact finite_registered_atomic_witness_certificate."
                "finite_registered_atomic_witness_basis_eq",
            ]
        )
        for index, schema in enumerate(schemas, 1):
            for sort in ("concrete", "base", "closure"):
                lines.extend(
                    [
                        "",
                        "theorem "
                        f"finite_registered_atomic_witness_lexical_{index}_{sort}_projected :",
                        f"    {lean_schema_type(schema, sort)} := by",
                        "  exact finite_registered_atomic_witness_certificate."
                        f"finite_registered_atomic_witness_lexical_{index}_{sort}",
                    ]
                )
        for index, transition in enumerate(transitions, 1):
            for sort in ("concrete", "base", "closure"):
                lines.extend(
                    [
                        "",
                        "theorem "
                        f"finite_registered_atomic_witness_transition_{index}_{sort}_projected :",
                        f"    {lean_transition_type(transition, sort)} := by",
                        "  exact finite_registered_atomic_witness_certificate."
                        f"finite_registered_atomic_witness_transition_{index}_{sort}",
                    ]
                )
        return lines

    lines = [
        "Record FiniteRegisteredAtomicWitnessCertificate : Type := {",
        "  finite_registered_atomic_witness_basis : "
        "ConcreteRegisteredTruthBasis;",
        "  finite_registered_atomic_witness_basis_eq :",
        "      finite_registered_atomic_witness_basis = "
        "concrete_registered_truth_basis;",
    ]
    for index, schema in enumerate(schemas, 1):
        for sort in ("concrete", "base", "closure"):
            type_lines = coq_schema_type(schema, sort)
            lines.append(
                f"  finite_registered_atomic_witness_lexical_{index}_{sort} : "
                + type_lines[0]
            )
            lines.extend(type_lines[1:])
            lines[-1] += ";"
    for index, transition in enumerate(transitions, 1):
        for sort in ("concrete", "base", "closure"):
            lines.append(
                f"  finite_registered_atomic_witness_transition_{index}_{sort} : "
                f"{coq_transition_type(transition, sort)};"
            )
    lines[-1] = lines[-1].rstrip(";")
    lines.extend(
        [
            "}.",
            "",
            "Definition finite_registered_atomic_witness_certificate :",
            "  FiniteRegisteredAtomicWitnessCertificate := {|",
            "  finite_registered_atomic_witness_basis := "
            "concrete_registered_truth_basis;",
            "  finite_registered_atomic_witness_basis_eq := eq_refl;",
        ]
    )
    assignments = []
    for index, schema in enumerate(schemas, 1):
        for sort in ("concrete", "base", "closure"):
            assignments.append(
                (
                    f"finite_registered_atomic_witness_lexical_{index}_{sort}",
                    coq_schema_value(schema, sort),
                )
            )
    for index, transition in enumerate(transitions, 1):
        for sort in ("concrete", "base", "closure"):
            assignments.append(
                (
                    f"finite_registered_atomic_witness_transition_{index}_{sort}",
                    coq_transition_value(transition, sort),
                )
            )
    for index, (field, value) in enumerate(assignments):
        suffix = ";" if index < len(assignments) - 1 else ""
        lines.append(f"  {field} := {value}{suffix}")
    lines.extend(
        [
            "|}.",
            "",
            "Theorem finite_registered_atomic_witness_certificate_exists :",
            "  exists C : FiniteRegisteredAtomicWitnessCertificate,",
            "    C = finite_registered_atomic_witness_certificate.",
            "Proof.",
            "  exists finite_registered_atomic_witness_certificate.",
            "  reflexivity.",
            "Qed.",
            "",
            "Theorem finite_registered_atomic_witness_basis_matches :",
            "  finite_registered_atomic_witness_basis",
            "    finite_registered_atomic_witness_certificate =",
            "  concrete_registered_truth_basis.",
            "Proof.",
            "  exact (finite_registered_atomic_witness_basis_eq",
            "    finite_registered_atomic_witness_certificate).",
            "Qed.",
        ]
    )
    for index, schema in enumerate(schemas, 1):
        for sort in ("concrete", "base", "closure"):
            type_lines = coq_schema_type(schema, sort)
            lines.extend(
                [
                    "",
                    "Theorem "
                    f"finite_registered_atomic_witness_lexical_{index}_{sort}_projected :",
                    f"  {type_lines[0]}",
                ]
            )
            lines.extend(type_lines[1:])
            lines[-1] += "."
            lines.extend(
                [
                    "Proof.",
                    "  exact ("
                    f"finite_registered_atomic_witness_lexical_{index}_{sort}",
                    "    finite_registered_atomic_witness_certificate).",
                    "Qed.",
                ]
            )
    for index, transition in enumerate(transitions, 1):
        for sort in ("concrete", "base", "closure"):
            lines.extend(
                [
                    "",
                    "Theorem "
                    f"finite_registered_atomic_witness_transition_{index}_{sort}_projected :",
                    f"  {coq_transition_type(transition, sort)}.",
                    "Proof.",
                    "  exact ("
                    f"finite_registered_atomic_witness_transition_{index}_{sort}",
                    "    finite_registered_atomic_witness_certificate).",
                    "Qed.",
                ]
            )
    return lines


def finite_registered_atomic_source_discipline_certificate_lines(
    declarations: dict[str, Any],
    target: str,
) -> list[str]:
    """Record the registered evidence source behind each finite atom witness."""

    schemas: list[LexicalApplicationSchema] = declarations["lexical_applications"]
    transitions: list[tuple[str, str, str, str]] = declarations["transitions"]

    def schema_application(schema: LexicalApplicationSchema) -> tuple[str, str, list[tuple[str, str]]]:
        _function, result_type, _count, _modifier_term, _modifiers, _args, binders = schema
        return result_type, lexical_application_term(schema), binders

    def lean_schema_registered_type(schema: LexicalApplicationSchema) -> str:
        result_type, application, binders = schema_application(schema)
        conclusion = f"RegisteredLexicalApplicationTruth {result_type} ({application})"
        binder_parts = [f"({name} : {type_name})" for name, type_name in binders]
        return " -> ".join([*binder_parts, conclusion])

    def lean_schema_from_source_type(
        schema: LexicalApplicationSchema,
        sort: str,
    ) -> str:
        result_type, application, binders = schema_application(schema)
        source = f"RegisteredLexicalApplicationTruth {result_type} ({application})"
        conclusion = {
            "concrete": (
                f"ConcreteRegisteredAtomicTruth {result_type} ({application})"
            ),
            "base": f"AtomicBaseTruth {result_type} ({application})",
            "closure": f"AtomicClosureTruth {result_type} ({application})",
        }[sort]
        binder_parts = [f"({name} : {type_name})" for name, type_name in binders]
        return " -> ".join([*binder_parts, source, conclusion])

    def lean_schema_registered_value(schema: LexicalApplicationSchema) -> str:
        constructor = registered_lexical_application_constructor_from_schema(schema)
        result_type, application, binders = schema_application(schema)
        del result_type, application
        binder_names = [name for name, _type_name in binders]
        value = "RegisteredLexicalApplicationTruth." + constructor
        if binder_names:
            value += " " + " ".join(binder_names)
            return f"fun {' '.join(binder_names)} => {value}"
        return value

    def lean_schema_from_source_value(
        schema: LexicalApplicationSchema,
        sort: str,
    ) -> str:
        result_type, application, binders = schema_application(schema)
        binder_names = [name for name, _type_name in binders]
        h_name = "h_source"
        value = {
            "concrete": (
                "ConcreteRegisteredAtomicTruth."
                "concrete_registered_atomic_truth_lexical_application "
                f"{result_type} ({application}) {h_name}"
            ),
            "base": (
                "registered_lexical_application_atomic_base_truth "
                f"{result_type} ({application}) {h_name}"
            ),
            "closure": (
                "registered_lexical_application_atomic_closure_truth "
                f"{result_type} ({application}) {h_name}"
            ),
        }[sort]
        args = [*binder_names, h_name]
        return f"fun {' '.join(args)} => {value}"

    def transition_term_parts(
        transition: tuple[str, str, str, str],
    ) -> tuple[str, str, str, str, str]:
        theme, scale, source, target_state = transition
        return theme, scale, source, target_state, (
            f"(Transition {theme} {scale} {source} {target_state})"
        )

    def lean_transition_source_type(
        transition: tuple[str, str, str, str],
    ) -> str:
        theme, scale, source, target_state, _term = transition_term_parts(transition)
        return (
            "RegisteredStateTransitionTruth "
            f"{theme} {scale} {source} {target_state}"
        )

    def lean_transition_from_source_type(
        transition: tuple[str, str, str, str],
        sort: str,
    ) -> str:
        source_type = lean_transition_source_type(transition)
        _theme, _scale, _source, _target_state, term = transition_term_parts(transition)
        conclusion = {
            "concrete": f"ConcreteRegisteredAtomicTruth TransitionT {term}",
            "base": f"AtomicBaseTruth TransitionT {term}",
            "closure": f"AtomicClosureTruth TransitionT {term}",
        }[sort]
        return f"{source_type} -> {conclusion}"

    def lean_transition_source_value(
        transition: tuple[str, str, str, str],
    ) -> str:
        theme, scale, source, target_state, _term = transition_term_parts(transition)
        constructor = registered_state_transition_constructor(
            theme,
            scale,
            source,
            target_state,
        )
        return "RegisteredStateTransitionTruth." + constructor

    def lean_transition_from_source_value(
        transition: tuple[str, str, str, str],
        sort: str,
    ) -> str:
        theme, scale, source, target_state, _term = transition_term_parts(transition)
        h_name = "h_source"
        base = (
            "registered_state_transition_atomic_base_truth "
            f"{theme} {scale} {source} {target_state} {h_name}"
        )
        value = {
            "concrete": (
                "ConcreteRegisteredAtomicTruth."
                "concrete_registered_atomic_truth_transition "
                f"{theme} {scale} {source} {target_state} {h_name}"
            ),
            "base": base,
            "closure": (
                "AtomicClosureTruth.atomic_closure_truth_transition "
                f"{theme} {scale} {source} {target_state} ({base})"
            ),
        }[sort]
        return f"fun {h_name} => {value}"

    def coq_schema_registered_type(schema: LexicalApplicationSchema) -> list[str]:
        result_type, application, binders = schema_application(schema)
        conclusion = f"RegisteredLexicalApplicationTruth {result_type} ({application})"
        if not binders:
            return [conclusion]
        binder_text = ", ".join(
            f"forall {name} : {type_name}" for name, type_name in binders
        )
        return [f"{binder_text},", f"      {conclusion}"]

    def coq_schema_from_source_type(
        schema: LexicalApplicationSchema,
        sort: str,
    ) -> list[str]:
        result_type, application, binders = schema_application(schema)
        source_type = f"RegisteredLexicalApplicationTruth {result_type} ({application})"
        conclusion = {
            "concrete": (
                f"ConcreteRegisteredAtomicTruth {result_type} ({application})"
            ),
            "base": f"AtomicBaseTruth {result_type} ({application})",
            "closure": f"AtomicClosureTruth {result_type} ({application})",
        }[sort]
        if not binders:
            return [f"{source_type} ->", f"      {conclusion}"]
        binder_text = ", ".join(
            f"forall {name} : {type_name}" for name, type_name in binders
        )
        return [f"{binder_text},", f"      {source_type} ->", f"      {conclusion}"]

    def coq_schema_registered_value(schema: LexicalApplicationSchema) -> str:
        constructor = registered_lexical_application_constructor_from_schema(schema)
        _result_type, _application, binders = schema_application(schema)
        binder_names = [name for name, _type_name in binders]
        value = constructor
        if binder_names:
            value += " " + " ".join(binder_names)
            return f"fun {' '.join(binder_names)} => {value}"
        return value

    def coq_schema_from_source_value(
        schema: LexicalApplicationSchema,
        sort: str,
    ) -> str:
        result_type, application, binders = schema_application(schema)
        binder_names = [name for name, _type_name in binders]
        h_name = "h_source"
        value = {
            "concrete": (
                "concrete_registered_atomic_truth_lexical_application "
                f"{result_type} ({application}) {h_name}"
            ),
            "base": (
                "registered_lexical_application_atomic_base_truth "
                f"{result_type} ({application}) {h_name}"
            ),
            "closure": (
                "registered_lexical_application_atomic_closure_truth "
                f"{result_type} ({application}) {h_name}"
            ),
        }[sort]
        return f"fun {' '.join([*binder_names, h_name])} => {value}"

    def coq_transition_source_type(
        transition: tuple[str, str, str, str],
    ) -> str:
        theme, scale, source, target_state, _term = transition_term_parts(transition)
        return (
            "RegisteredStateTransitionTruth "
            f"{theme} {scale} {source} {target_state}"
        )

    def coq_transition_from_source_type(
        transition: tuple[str, str, str, str],
        sort: str,
    ) -> list[str]:
        source_type = coq_transition_source_type(transition)
        _theme, _scale, _source, _target_state, term = transition_term_parts(transition)
        conclusion = {
            "concrete": f"ConcreteRegisteredAtomicTruth TransitionT {term}",
            "base": f"AtomicBaseTruth TransitionT {term}",
            "closure": f"AtomicClosureTruth TransitionT {term}",
        }[sort]
        return [f"{source_type} ->", f"      {conclusion}"]

    def coq_transition_source_value(
        transition: tuple[str, str, str, str],
    ) -> str:
        theme, scale, source, target_state, _term = transition_term_parts(transition)
        return registered_state_transition_constructor(
            theme,
            scale,
            source,
            target_state,
        )

    def coq_transition_from_source_value(
        transition: tuple[str, str, str, str],
        sort: str,
    ) -> str:
        theme, scale, source, target_state, _term = transition_term_parts(transition)
        h_name = "h_source"
        base = (
            "registered_state_transition_atomic_base_truth "
            f"{theme} {scale} {source} {target_state} {h_name}"
        )
        value = {
            "concrete": (
                "concrete_registered_atomic_truth_transition "
                f"{theme} {scale} {source} {target_state} {h_name}"
            ),
            "base": base,
            "closure": (
                "atomic_closure_truth_transition "
                f"{theme} {scale} {source} {target_state} ({base})"
            ),
        }[sort]
        return f"fun {h_name} => {value}"

    if target == "lean":
        lines = [
            "structure FiniteRegisteredAtomicSourceDisciplineCertificate : Type where",
            "  finite_registered_atomic_source_witness : "
            "FiniteRegisteredAtomicWitnessCertificate",
            "  finite_registered_atomic_source_witness_eq :",
            "      finite_registered_atomic_source_witness = "
            "finite_registered_atomic_witness_certificate",
        ]
        for index, schema in enumerate(schemas, 1):
            lines.append(
                f"  finite_registered_atomic_source_lexical_{index}_source : "
                f"{lean_schema_registered_type(schema)}"
            )
            for sort in ("concrete", "base", "closure"):
                lines.append(
                    "  "
                    f"finite_registered_atomic_source_lexical_{index}_{sort}_from_source : "
                    f"{lean_schema_from_source_type(schema, sort)}"
                )
        for index, transition in enumerate(transitions, 1):
            lines.append(
                f"  finite_registered_atomic_source_transition_{index}_source : "
                f"{lean_transition_source_type(transition)}"
            )
            for sort in ("concrete", "base", "closure"):
                lines.append(
                    "  "
                    f"finite_registered_atomic_source_transition_{index}_{sort}_from_source : "
                    f"{lean_transition_from_source_type(transition, sort)}"
                )
        lines.extend(
            [
                "",
                "def finite_registered_atomic_source_discipline_certificate :",
                "    FiniteRegisteredAtomicSourceDisciplineCertificate := {",
                "  finite_registered_atomic_source_witness := "
                "finite_registered_atomic_witness_certificate,",
                "  finite_registered_atomic_source_witness_eq := rfl,",
            ]
        )
        assignments: list[tuple[str, str]] = []
        for index, schema in enumerate(schemas, 1):
            assignments.append(
                (
                    f"finite_registered_atomic_source_lexical_{index}_source",
                    lean_schema_registered_value(schema),
                )
            )
            for sort in ("concrete", "base", "closure"):
                assignments.append(
                    (
                        f"finite_registered_atomic_source_lexical_{index}_{sort}_from_source",
                        lean_schema_from_source_value(schema, sort),
                    )
                )
        for index, transition in enumerate(transitions, 1):
            assignments.append(
                (
                    f"finite_registered_atomic_source_transition_{index}_source",
                    lean_transition_source_value(transition),
                )
            )
            for sort in ("concrete", "base", "closure"):
                assignments.append(
                    (
                        f"finite_registered_atomic_source_transition_{index}_{sort}_from_source",
                        lean_transition_from_source_value(transition, sort),
                    )
                )
        for index, (field, value) in enumerate(assignments):
            suffix = "," if index < len(assignments) - 1 else ""
            lines.append(f"  {field} := {value}{suffix}")
        lines.extend(
            [
                "}",
                "",
                "theorem finite_registered_atomic_source_discipline_certificate_exists :",
                "    Exists (fun C : "
                "FiniteRegisteredAtomicSourceDisciplineCertificate => "
                "C = finite_registered_atomic_source_discipline_certificate) := by",
                "  exact Exists.intro "
                "finite_registered_atomic_source_discipline_certificate rfl",
                "",
                "theorem finite_registered_atomic_source_witness_matches :",
                "    finite_registered_atomic_source_discipline_certificate."
                "finite_registered_atomic_source_witness =",
                "      finite_registered_atomic_witness_certificate := by",
                "  exact finite_registered_atomic_source_discipline_certificate."
                "finite_registered_atomic_source_witness_eq",
            ]
        )
        for index, schema in enumerate(schemas, 1):
            lines.extend(
                [
                    "",
                    "theorem "
                    f"finite_registered_atomic_source_lexical_{index}_source_projected :",
                    f"    {lean_schema_registered_type(schema)} := by",
                    "  exact finite_registered_atomic_source_discipline_certificate."
                    f"finite_registered_atomic_source_lexical_{index}_source",
                ]
            )
            for sort in ("concrete", "base", "closure"):
                lines.extend(
                    [
                        "",
                        "theorem "
                        f"finite_registered_atomic_source_lexical_{index}_{sort}_from_source_projected :",
                        f"    {lean_schema_from_source_type(schema, sort)} := by",
                        "  exact finite_registered_atomic_source_discipline_certificate."
                        f"finite_registered_atomic_source_lexical_{index}_{sort}_from_source",
                    ]
                )
        for index, transition in enumerate(transitions, 1):
            lines.extend(
                [
                    "",
                    "theorem "
                    f"finite_registered_atomic_source_transition_{index}_source_projected :",
                    f"    {lean_transition_source_type(transition)} := by",
                    "  exact finite_registered_atomic_source_discipline_certificate."
                    f"finite_registered_atomic_source_transition_{index}_source",
                ]
            )
            for sort in ("concrete", "base", "closure"):
                lines.extend(
                    [
                        "",
                        "theorem "
                        f"finite_registered_atomic_source_transition_{index}_{sort}_from_source_projected :",
                        f"    {lean_transition_from_source_type(transition, sort)} := by",
                        "  exact finite_registered_atomic_source_discipline_certificate."
                        f"finite_registered_atomic_source_transition_{index}_{sort}_from_source",
                    ]
                )
        return lines

    lines = [
        "Record FiniteRegisteredAtomicSourceDisciplineCertificate : Type := {",
        "  finite_registered_atomic_source_witness : "
        "FiniteRegisteredAtomicWitnessCertificate;",
        "  finite_registered_atomic_source_witness_eq :",
        "      finite_registered_atomic_source_witness = "
        "finite_registered_atomic_witness_certificate;",
    ]
    for index, schema in enumerate(schemas, 1):
        source_type = coq_schema_registered_type(schema)
        lines.append(
            f"  finite_registered_atomic_source_lexical_{index}_source : "
            + source_type[0]
        )
        lines.extend(source_type[1:])
        lines[-1] += ";"
        for sort in ("concrete", "base", "closure"):
            type_lines = coq_schema_from_source_type(schema, sort)
            lines.append(
                "  "
                f"finite_registered_atomic_source_lexical_{index}_{sort}_from_source : "
                + type_lines[0]
            )
            lines.extend(type_lines[1:])
            lines[-1] += ";"
    for index, transition in enumerate(transitions, 1):
        lines.append(
            f"  finite_registered_atomic_source_transition_{index}_source : "
            f"{coq_transition_source_type(transition)};"
        )
        for sort in ("concrete", "base", "closure"):
            type_lines = coq_transition_from_source_type(transition, sort)
            lines.append(
                "  "
                f"finite_registered_atomic_source_transition_{index}_{sort}_from_source : "
                + type_lines[0]
            )
            lines.extend(type_lines[1:])
            lines[-1] += ";"
    lines[-1] = lines[-1].rstrip(";")
    lines.extend(
        [
            "}.",
            "",
            "Definition finite_registered_atomic_source_discipline_certificate :",
            "  FiniteRegisteredAtomicSourceDisciplineCertificate := {|",
            "  finite_registered_atomic_source_witness := "
            "finite_registered_atomic_witness_certificate;",
            "  finite_registered_atomic_source_witness_eq := eq_refl;",
        ]
    )
    assignments = []
    for index, schema in enumerate(schemas, 1):
        assignments.append(
            (
                f"finite_registered_atomic_source_lexical_{index}_source",
                coq_schema_registered_value(schema),
            )
        )
        for sort in ("concrete", "base", "closure"):
            assignments.append(
                (
                    f"finite_registered_atomic_source_lexical_{index}_{sort}_from_source",
                    coq_schema_from_source_value(schema, sort),
                )
            )
    for index, transition in enumerate(transitions, 1):
        assignments.append(
            (
                f"finite_registered_atomic_source_transition_{index}_source",
                coq_transition_source_value(transition),
            )
        )
        for sort in ("concrete", "base", "closure"):
            assignments.append(
                (
                    f"finite_registered_atomic_source_transition_{index}_{sort}_from_source",
                    coq_transition_from_source_value(transition, sort),
                )
            )
    for index, (field, value) in enumerate(assignments):
        suffix = ";" if index < len(assignments) - 1 else ""
        lines.append(f"  {field} := {value}{suffix}")
    lines.extend(
        [
            "|}.",
            "",
            "Theorem finite_registered_atomic_source_discipline_certificate_exists :",
            "  exists C : FiniteRegisteredAtomicSourceDisciplineCertificate,",
            "    C = finite_registered_atomic_source_discipline_certificate.",
            "Proof.",
            "  exists finite_registered_atomic_source_discipline_certificate.",
            "  reflexivity.",
            "Qed.",
            "",
            "Theorem finite_registered_atomic_source_witness_matches :",
            "  finite_registered_atomic_source_witness",
            "    finite_registered_atomic_source_discipline_certificate =",
            "  finite_registered_atomic_witness_certificate.",
            "Proof.",
            "  exact (finite_registered_atomic_source_witness_eq",
            "    finite_registered_atomic_source_discipline_certificate).",
            "Qed.",
        ]
    )
    for index, schema in enumerate(schemas, 1):
        source_type = coq_schema_registered_type(schema)
        lines.extend(
            [
                "",
                "Theorem "
                f"finite_registered_atomic_source_lexical_{index}_source_projected :",
                f"  {source_type[0]}",
            ]
        )
        lines.extend(source_type[1:])
        lines[-1] += "."
        lines.extend(
            [
                "Proof.",
                "  exact ("
                f"finite_registered_atomic_source_lexical_{index}_source",
                "    finite_registered_atomic_source_discipline_certificate).",
                "Qed.",
            ]
        )
        for sort in ("concrete", "base", "closure"):
            type_lines = coq_schema_from_source_type(schema, sort)
            lines.extend(
                [
                    "",
                    "Theorem "
                    f"finite_registered_atomic_source_lexical_{index}_{sort}_from_source_projected :",
                    f"  {type_lines[0]}",
                ]
            )
            lines.extend(type_lines[1:])
            lines[-1] += "."
            lines.extend(
                [
                    "Proof.",
                    "  exact ("
                    f"finite_registered_atomic_source_lexical_{index}_{sort}_from_source",
                    "    finite_registered_atomic_source_discipline_certificate).",
                    "Qed.",
                ]
            )
    for index, transition in enumerate(transitions, 1):
        lines.extend(
            [
                "",
                "Theorem "
                f"finite_registered_atomic_source_transition_{index}_source_projected :",
                f"  {coq_transition_source_type(transition)}.",
                "Proof.",
                "  exact ("
                f"finite_registered_atomic_source_transition_{index}_source",
                "    finite_registered_atomic_source_discipline_certificate).",
                "Qed.",
            ]
        )
        for sort in ("concrete", "base", "closure"):
            type_lines = coq_transition_from_source_type(transition, sort)
            lines.extend(
                [
                    "",
                    "Theorem "
                    f"finite_registered_atomic_source_transition_{index}_{sort}_from_source_projected :",
                    f"  {type_lines[0]}",
                ]
            )
            lines.extend(type_lines[1:])
            lines[-1] += "."
            lines.extend(
                [
                    "Proof.",
                    "  exact ("
                    f"finite_registered_atomic_source_transition_{index}_{sort}_from_source",
                    "    finite_registered_atomic_source_discipline_certificate).",
                    "Qed.",
                ]
            )
    return lines


def finite_registered_atomic_kernel_alignment_certificate_lines(
    declarations: dict[str, Any],
    target: str,
) -> list[str]:
    """Align finite registered atom sources with the concrete truth kernel."""

    schemas: list[LexicalApplicationSchema] = declarations["lexical_applications"]
    transitions: list[tuple[str, str, str, str]] = declarations["transitions"]

    def schema_parts(
        schema: LexicalApplicationSchema,
    ) -> tuple[str, str, list[tuple[str, str]], list[str]]:
        _function, result_type, _count, _modifier_term, _modifiers, _args, binders = schema
        binder_names = [name for name, _type_name in binders]
        return result_type, lexical_application_term(schema), binders, binder_names

    def lean_schema_kernel_type(schema: LexicalApplicationSchema) -> str:
        result_type, application, binders, _binder_names = schema_parts(schema)
        source = f"RegisteredLexicalApplicationTruth {result_type} ({application})"
        conclusion = (
            "concrete_registered_truth_kernel."
            f"concrete_registered_kernel_denotes {result_type} ({application})"
        )
        binder_parts = [f"({name} : {type_name})" for name, type_name in binders]
        return " -> ".join([*binder_parts, source, conclusion])

    def lean_schema_kernel_value(schema: LexicalApplicationSchema) -> str:
        result_type, application, _binders, binder_names = schema_parts(schema)
        h_name = "h_source"
        args = [*binder_names, h_name]
        value = (
            "concrete_registered_truth_kernel."
            "concrete_registered_kernel_lexical_application "
            f"{result_type} ({application}) {h_name}"
        )
        return f"fun {' '.join(args)} => {value}"

    def lean_schema_atomic_type(schema: LexicalApplicationSchema) -> str:
        result_type, application, binders, _binder_names = schema_parts(schema)
        conclusion = f"AtomicClosureTruth {result_type} ({application})"
        binder_parts = [f"({name} : {type_name})" for name, type_name in binders]
        return " -> ".join([*binder_parts, conclusion])

    def lean_schema_source_call(index: int, binder_names: list[str]) -> str:
        call = f"finite_registered_atomic_source_lexical_{index}_source_projected"
        if binder_names:
            call += " " + " ".join(binder_names)
        return call

    def lean_schema_kernel_call(index: int, binder_names: list[str]) -> str:
        call = (
            "finite_registered_atomic_kernel_alignment_certificate."
            f"finite_registered_atomic_kernel_alignment_lexical_{index}_source_to_kernel"
        )
        if binder_names:
            call += " " + " ".join(binder_names)
        return call

    def transition_parts(
        transition: tuple[str, str, str, str],
    ) -> tuple[str, str, str, str, str]:
        theme, scale, source, target_state = transition
        return theme, scale, source, target_state, (
            f"(Transition {theme} {scale} {source} {target_state})"
        )

    def lean_transition_kernel_type(
        transition: tuple[str, str, str, str],
    ) -> str:
        theme, scale, source, target_state, term = transition_parts(transition)
        return (
            "RegisteredStateTransitionTruth "
            f"{theme} {scale} {source} {target_state} -> "
            "concrete_registered_truth_kernel."
            f"concrete_registered_kernel_denotes TransitionT {term}"
        )

    def lean_transition_kernel_value(
        transition: tuple[str, str, str, str],
    ) -> str:
        theme, scale, source, target_state, _term = transition_parts(transition)
        return (
            "fun h_source => concrete_registered_truth_kernel."
            "concrete_registered_kernel_transition "
            f"{theme} {scale} {source} {target_state} h_source"
        )

    def lean_transition_atomic_type(
        transition: tuple[str, str, str, str],
    ) -> str:
        _theme, _scale, _source, _target_state, term = transition_parts(transition)
        return f"AtomicClosureTruth TransitionT {term}"

    def coq_schema_kernel_type(schema: LexicalApplicationSchema) -> list[str]:
        result_type, application, binders, _binder_names = schema_parts(schema)
        source = f"RegisteredLexicalApplicationTruth {result_type} ({application})"
        conclusion = (
            "concrete_registered_kernel_denotes concrete_registered_truth_kernel "
            f"{result_type} ({application})"
        )
        if not binders:
            return [f"{source} ->", f"      {conclusion}"]
        binder_text = ", ".join(
            f"forall {name} : {type_name}" for name, type_name in binders
        )
        return [f"{binder_text},", f"      {source} ->", f"      {conclusion}"]

    def coq_schema_kernel_value(schema: LexicalApplicationSchema) -> str:
        result_type, application, _binders, binder_names = schema_parts(schema)
        h_name = "h_source"
        value = (
            "concrete_registered_kernel_lexical_application "
            f"concrete_registered_truth_kernel {result_type} "
            f"({application}) {h_name}"
        )
        return f"fun {' '.join([*binder_names, h_name])} => {value}"

    def coq_schema_atomic_type(schema: LexicalApplicationSchema) -> list[str]:
        result_type, application, binders, _binder_names = schema_parts(schema)
        conclusion = f"AtomicClosureTruth {result_type} ({application})"
        if not binders:
            return [conclusion]
        binder_text = ", ".join(
            f"forall {name} : {type_name}" for name, type_name in binders
        )
        return [f"{binder_text},", f"      {conclusion}"]

    def coq_transition_kernel_type(
        transition: tuple[str, str, str, str],
    ) -> list[str]:
        theme, scale, source, target_state, term = transition_parts(transition)
        return [
            "RegisteredStateTransitionTruth "
            f"{theme} {scale} {source} {target_state} ->",
            "      concrete_registered_kernel_denotes concrete_registered_truth_kernel "
            f"TransitionT {term}",
        ]

    def coq_transition_kernel_value(
        transition: tuple[str, str, str, str],
    ) -> str:
        theme, scale, source, target_state, _term = transition_parts(transition)
        return (
            "fun h_source => concrete_registered_kernel_transition "
            f"concrete_registered_truth_kernel {theme} {scale} "
            f"{source} {target_state} h_source"
        )

    def coq_transition_atomic_type(
        transition: tuple[str, str, str, str],
    ) -> str:
        _theme, _scale, _source, _target_state, term = transition_parts(transition)
        return f"AtomicClosureTruth TransitionT {term}"

    if target == "lean":
        lines = [
            "theorem finite_registered_atomic_kernel_denotes_imply_atomic_closure :",
            "    (A : Type) -> (term : A) ->",
            "    concrete_registered_truth_kernel."
            "concrete_registered_kernel_denotes A term ->",
            "    AtomicClosureTruth A term := by",
            "  intro A term h",
            "  apply concrete_registered_truth_conditions_from_kernel_imply_atomic_closure",
            "  exact h",
            "",
            "structure FiniteRegisteredAtomicKernelAlignmentCertificate : Type where",
            "  finite_registered_atomic_kernel_alignment_source : "
            "FiniteRegisteredAtomicSourceDisciplineCertificate",
            "  finite_registered_atomic_kernel_alignment_source_eq :",
            "      finite_registered_atomic_kernel_alignment_source = "
            "finite_registered_atomic_source_discipline_certificate",
            "  finite_registered_atomic_kernel_alignment_kernel : "
            "ConcreteRegisteredTruthKernel",
            "  finite_registered_atomic_kernel_alignment_kernel_eq :",
            "      finite_registered_atomic_kernel_alignment_kernel = "
            "concrete_registered_truth_kernel",
            "  finite_registered_atomic_kernel_alignment_sound :",
            "      (A : Type) -> (term : A) ->",
            "      concrete_registered_truth_kernel."
            "concrete_registered_kernel_denotes A term ->",
            "      AtomicClosureTruth A term",
        ]
        for index, schema in enumerate(schemas, 1):
            lines.append(
                "  "
                f"finite_registered_atomic_kernel_alignment_lexical_{index}_source_to_kernel : "
                f"{lean_schema_kernel_type(schema)}"
            )
        for index, transition in enumerate(transitions, 1):
            lines.append(
                "  "
                f"finite_registered_atomic_kernel_alignment_transition_{index}_source_to_kernel : "
                f"{lean_transition_kernel_type(transition)}"
            )
        lines.extend(
            [
                "",
                "def finite_registered_atomic_kernel_alignment_certificate :",
                "    FiniteRegisteredAtomicKernelAlignmentCertificate := {",
                "  finite_registered_atomic_kernel_alignment_source := "
                "finite_registered_atomic_source_discipline_certificate,",
                "  finite_registered_atomic_kernel_alignment_source_eq := rfl,",
                "  finite_registered_atomic_kernel_alignment_kernel := "
                "concrete_registered_truth_kernel,",
                "  finite_registered_atomic_kernel_alignment_kernel_eq := rfl,",
                "  finite_registered_atomic_kernel_alignment_sound := "
                "finite_registered_atomic_kernel_denotes_imply_atomic_closure,",
            ]
        )
        assignments: list[tuple[str, str]] = []
        for index, schema in enumerate(schemas, 1):
            assignments.append(
                (
                    f"finite_registered_atomic_kernel_alignment_lexical_{index}_source_to_kernel",
                    lean_schema_kernel_value(schema),
                )
            )
        for index, transition in enumerate(transitions, 1):
            assignments.append(
                (
                    f"finite_registered_atomic_kernel_alignment_transition_{index}_source_to_kernel",
                    lean_transition_kernel_value(transition),
                )
            )
        for index, (field, value) in enumerate(assignments):
            suffix = "," if index < len(assignments) - 1 else ""
            lines.append(f"  {field} := {value}{suffix}")
        lines.extend(
            [
                "}",
                "",
                "theorem finite_registered_atomic_kernel_alignment_certificate_exists :",
                "    Exists (fun C : "
                "FiniteRegisteredAtomicKernelAlignmentCertificate => "
                "C = finite_registered_atomic_kernel_alignment_certificate) := by",
                "  exact Exists.intro "
                "finite_registered_atomic_kernel_alignment_certificate rfl",
                "",
                "theorem finite_registered_atomic_kernel_alignment_source_matches :",
                "    finite_registered_atomic_kernel_alignment_certificate."
                "finite_registered_atomic_kernel_alignment_source =",
                "      finite_registered_atomic_source_discipline_certificate := by",
                "  exact finite_registered_atomic_kernel_alignment_certificate."
                "finite_registered_atomic_kernel_alignment_source_eq",
                "",
                "theorem finite_registered_atomic_kernel_alignment_kernel_matches :",
                "    finite_registered_atomic_kernel_alignment_certificate."
                "finite_registered_atomic_kernel_alignment_kernel =",
                "      concrete_registered_truth_kernel := by",
                "  exact finite_registered_atomic_kernel_alignment_certificate."
                "finite_registered_atomic_kernel_alignment_kernel_eq",
                "",
                "theorem finite_registered_atomic_kernel_alignment_sound_projected :",
                "    (A : Type) -> (term : A) ->",
                "    concrete_registered_truth_kernel."
                "concrete_registered_kernel_denotes A term ->",
                "    AtomicClosureTruth A term := by",
                "  exact finite_registered_atomic_kernel_alignment_certificate."
                "finite_registered_atomic_kernel_alignment_sound",
            ]
        )
        for index, schema in enumerate(schemas, 1):
            result_type, application, _binders, binder_names = schema_parts(schema)
            del result_type, application
            lines.extend(
                [
                    "",
                    "theorem "
                    f"finite_registered_atomic_kernel_alignment_lexical_{index}_source_to_kernel_projected :",
                    f"    {lean_schema_kernel_type(schema)} := by",
                    "  exact finite_registered_atomic_kernel_alignment_certificate."
                    f"finite_registered_atomic_kernel_alignment_lexical_{index}_source_to_kernel",
                    "",
                    "theorem "
                    f"finite_registered_atomic_kernel_alignment_lexical_{index}_atomic_projected :",
                    f"    {lean_schema_atomic_type(schema)} := by",
                ]
            )
            if binder_names:
                lines.append(f"  intro {' '.join(binder_names)}")
            lines.extend(
                [
                    "  apply finite_registered_atomic_kernel_denotes_imply_atomic_closure",
                    "  exact "
                    f"{lean_schema_kernel_call(index, binder_names)} "
                    f"({lean_schema_source_call(index, binder_names)})",
                ]
            )
        for index, transition in enumerate(transitions, 1):
            lines.extend(
                [
                    "",
                    "theorem "
                    f"finite_registered_atomic_kernel_alignment_transition_{index}_source_to_kernel_projected :",
                    f"    {lean_transition_kernel_type(transition)} := by",
                    "  exact finite_registered_atomic_kernel_alignment_certificate."
                    f"finite_registered_atomic_kernel_alignment_transition_{index}_source_to_kernel",
                    "",
                    "theorem "
                    f"finite_registered_atomic_kernel_alignment_transition_{index}_atomic_projected :",
                    f"    {lean_transition_atomic_type(transition)} := by",
                    "  apply finite_registered_atomic_kernel_denotes_imply_atomic_closure",
                    "  exact finite_registered_atomic_kernel_alignment_certificate."
                    f"finite_registered_atomic_kernel_alignment_transition_{index}_source_to_kernel "
                    f"(finite_registered_atomic_source_transition_{index}_source_projected)",
                ]
            )
        return lines

    lines = [
        "Theorem finite_registered_atomic_kernel_denotes_imply_atomic_closure :",
        "  forall A : Type, forall term : A,",
        "    concrete_registered_kernel_denotes concrete_registered_truth_kernel A term ->",
        "    AtomicClosureTruth A term.",
        "Proof.",
        "  intros A term H.",
        "  apply concrete_registered_truth_conditions_from_kernel_imply_atomic_closure.",
        "  exact H.",
        "Qed.",
        "",
        "Record FiniteRegisteredAtomicKernelAlignmentCertificate : Type := {",
        "  finite_registered_atomic_kernel_alignment_source : "
        "FiniteRegisteredAtomicSourceDisciplineCertificate;",
        "  finite_registered_atomic_kernel_alignment_source_eq :",
        "      finite_registered_atomic_kernel_alignment_source = "
        "finite_registered_atomic_source_discipline_certificate;",
        "  finite_registered_atomic_kernel_alignment_kernel : "
        "ConcreteRegisteredTruthKernel;",
        "  finite_registered_atomic_kernel_alignment_kernel_eq :",
        "      finite_registered_atomic_kernel_alignment_kernel = "
        "concrete_registered_truth_kernel;",
        "  finite_registered_atomic_kernel_alignment_sound :",
        "      forall A : Type, forall term : A,",
        "      concrete_registered_kernel_denotes concrete_registered_truth_kernel A term ->",
        "      AtomicClosureTruth A term;",
    ]
    for index, schema in enumerate(schemas, 1):
        type_lines = coq_schema_kernel_type(schema)
        lines.append(
            "  "
            f"finite_registered_atomic_kernel_alignment_lexical_{index}_source_to_kernel : "
            + type_lines[0]
        )
        lines.extend(type_lines[1:])
        lines[-1] += ";"
    for index, transition in enumerate(transitions, 1):
        type_lines = coq_transition_kernel_type(transition)
        lines.append(
            "  "
            f"finite_registered_atomic_kernel_alignment_transition_{index}_source_to_kernel : "
            + type_lines[0]
        )
        lines.extend(type_lines[1:])
        lines[-1] += ";"
    lines[-1] = lines[-1].rstrip(";")
    lines.extend(
        [
            "}.",
            "",
            "Definition finite_registered_atomic_kernel_alignment_certificate :",
            "  FiniteRegisteredAtomicKernelAlignmentCertificate := {|",
            "  finite_registered_atomic_kernel_alignment_source := "
            "finite_registered_atomic_source_discipline_certificate;",
            "  finite_registered_atomic_kernel_alignment_source_eq := eq_refl;",
            "  finite_registered_atomic_kernel_alignment_kernel := "
            "concrete_registered_truth_kernel;",
            "  finite_registered_atomic_kernel_alignment_kernel_eq := eq_refl;",
            "  finite_registered_atomic_kernel_alignment_sound := "
            "finite_registered_atomic_kernel_denotes_imply_atomic_closure;",
        ]
    )
    assignments = []
    for index, schema in enumerate(schemas, 1):
        assignments.append(
            (
                f"finite_registered_atomic_kernel_alignment_lexical_{index}_source_to_kernel",
                coq_schema_kernel_value(schema),
            )
        )
    for index, transition in enumerate(transitions, 1):
        assignments.append(
            (
                f"finite_registered_atomic_kernel_alignment_transition_{index}_source_to_kernel",
                coq_transition_kernel_value(transition),
            )
        )
    for index, (field, value) in enumerate(assignments):
        suffix = ";" if index < len(assignments) - 1 else ""
        lines.append(f"  {field} := {value}{suffix}")
    lines.extend(
        [
            "|}.",
            "",
            "Theorem finite_registered_atomic_kernel_alignment_certificate_exists :",
            "  exists C : FiniteRegisteredAtomicKernelAlignmentCertificate,",
            "    C = finite_registered_atomic_kernel_alignment_certificate.",
            "Proof.",
            "  exists finite_registered_atomic_kernel_alignment_certificate.",
            "  reflexivity.",
            "Qed.",
            "",
            "Theorem finite_registered_atomic_kernel_alignment_source_matches :",
            "  finite_registered_atomic_kernel_alignment_source",
            "    finite_registered_atomic_kernel_alignment_certificate =",
            "  finite_registered_atomic_source_discipline_certificate.",
            "Proof.",
            "  exact (finite_registered_atomic_kernel_alignment_source_eq",
            "    finite_registered_atomic_kernel_alignment_certificate).",
            "Qed.",
            "",
            "Theorem finite_registered_atomic_kernel_alignment_kernel_matches :",
            "  finite_registered_atomic_kernel_alignment_kernel",
            "    finite_registered_atomic_kernel_alignment_certificate =",
            "  concrete_registered_truth_kernel.",
            "Proof.",
            "  exact (finite_registered_atomic_kernel_alignment_kernel_eq",
            "    finite_registered_atomic_kernel_alignment_certificate).",
            "Qed.",
            "",
            "Theorem finite_registered_atomic_kernel_alignment_sound_projected :",
            "  forall A : Type, forall term : A,",
            "    concrete_registered_kernel_denotes concrete_registered_truth_kernel A term ->",
            "    AtomicClosureTruth A term.",
            "Proof.",
            "  exact (finite_registered_atomic_kernel_alignment_sound",
            "    finite_registered_atomic_kernel_alignment_certificate).",
            "Qed.",
        ]
    )
    for index, schema in enumerate(schemas, 1):
        _result_type, _application, _binders, binder_names = schema_parts(schema)
        type_lines = coq_schema_kernel_type(schema)
        lines.extend(
            [
                "",
                "Theorem "
                f"finite_registered_atomic_kernel_alignment_lexical_{index}_source_to_kernel_projected :",
                f"  {type_lines[0]}",
            ]
        )
        lines.extend(type_lines[1:])
        lines[-1] += "."
        lines.extend(
            [
                "Proof.",
                "  exact ("
                f"finite_registered_atomic_kernel_alignment_lexical_{index}_source_to_kernel",
                "    finite_registered_atomic_kernel_alignment_certificate).",
                "Qed.",
                "",
                "Theorem "
                f"finite_registered_atomic_kernel_alignment_lexical_{index}_atomic_projected :",
            ]
        )
        atomic_type_lines = coq_schema_atomic_type(schema)
        lines.append(f"  {atomic_type_lines[0]}")
        lines.extend(atomic_type_lines[1:])
        lines[-1] += "."
        lines.append("Proof.")
        if binder_names:
            lines.append(f"  intros {' '.join(binder_names)}.")
        lines.extend(
            [
                "  apply finite_registered_atomic_kernel_denotes_imply_atomic_closure.",
                "  exact ("
                f"finite_registered_atomic_kernel_alignment_lexical_{index}_source_to_kernel",
                "    finite_registered_atomic_kernel_alignment_certificate",
            ]
        )
        if binder_names:
            lines.append(f"    {' '.join(binder_names)}")
        source_call = f"finite_registered_atomic_source_lexical_{index}_source_projected"
        if binder_names:
            source_call += " " + " ".join(binder_names)
        lines.extend(
            [
                f"    ({source_call})).",
                "Qed.",
            ]
        )
    for index, transition in enumerate(transitions, 1):
        type_lines = coq_transition_kernel_type(transition)
        lines.extend(
            [
                "",
                "Theorem "
                f"finite_registered_atomic_kernel_alignment_transition_{index}_source_to_kernel_projected :",
                f"  {type_lines[0]}",
            ]
        )
        lines.extend(type_lines[1:])
        lines[-1] += "."
        lines.extend(
            [
                "Proof.",
                "  exact ("
                f"finite_registered_atomic_kernel_alignment_transition_{index}_source_to_kernel",
                "    finite_registered_atomic_kernel_alignment_certificate).",
                "Qed.",
                "",
                "Theorem "
                f"finite_registered_atomic_kernel_alignment_transition_{index}_atomic_projected :",
                f"  {coq_transition_atomic_type(transition)}.",
                "Proof.",
                "  apply finite_registered_atomic_kernel_denotes_imply_atomic_closure.",
                "  exact ("
                f"finite_registered_atomic_kernel_alignment_transition_{index}_source_to_kernel",
                "    finite_registered_atomic_kernel_alignment_certificate",
                f"    (finite_registered_atomic_source_transition_{index}_source_projected)).",
                "Qed.",
            ]
        )
    return lines


def finite_registered_atomic_truth_condition_source_certificate_lines(
    declarations: dict[str, Any],
    target: str,
) -> list[str]:
    """Expose finite registered atom sources as concrete truth-condition inputs."""

    schemas: list[LexicalApplicationSchema] = declarations["lexical_applications"]
    transitions: list[tuple[str, str, str, str]] = declarations["transitions"]

    def schema_parts(
        schema: LexicalApplicationSchema,
    ) -> tuple[str, str, list[tuple[str, str]], list[str]]:
        _function, result_type, _count, _modifier_term, _modifiers, _args, binders = schema
        binder_names = [name for name, _type_name in binders]
        return result_type, lexical_application_term(schema), binders, binder_names

    def transition_parts(
        transition: tuple[str, str, str, str],
    ) -> tuple[str, str, str, str, str]:
        theme, scale, source, target_state = transition
        return theme, scale, source, target_state, (
            f"(Transition {theme} {scale} {source} {target_state})"
        )

    def lean_schema_source_type(schema: LexicalApplicationSchema) -> str:
        result_type, application, binders, _binder_names = schema_parts(schema)
        source = f"RegisteredLexicalApplicationTruth {result_type} ({application})"
        conclusion = (
            "concrete_registered_truth_conditions."
            f"fully_registered_truth_denotes {result_type} ({application})"
        )
        binder_parts = [f"({name} : {type_name})" for name, type_name in binders]
        return " -> ".join([*binder_parts, source, conclusion])

    def lean_schema_kernel_type(schema: LexicalApplicationSchema) -> str:
        result_type, application, binders, _binder_names = schema_parts(schema)
        source = f"RegisteredLexicalApplicationTruth {result_type} ({application})"
        conclusion = (
            "concrete_registered_truth_kernel."
            f"concrete_registered_kernel_denotes {result_type} ({application})"
        )
        binder_parts = [f"({name} : {type_name})" for name, type_name in binders]
        return " -> ".join([*binder_parts, source, conclusion])

    def lean_schema_source_value(schema: LexicalApplicationSchema) -> str:
        result_type, application, _binders, binder_names = schema_parts(schema)
        h_name = "h_source"
        args = [*binder_names, h_name]
        value = (
            "concrete_registered_truth_conditions."
            "fully_registered_truth_lexical_application "
            f"{result_type} ({application}) {h_name}"
        )
        return f"fun {' '.join(args)} => {value}"

    def lean_schema_atomic_type(schema: LexicalApplicationSchema) -> str:
        result_type, application, binders, _binder_names = schema_parts(schema)
        conclusion = f"AtomicClosureTruth {result_type} ({application})"
        binder_parts = [f"({name} : {type_name})" for name, type_name in binders]
        return " -> ".join([*binder_parts, conclusion])

    def lean_schema_source_call(index: int, binder_names: list[str]) -> str:
        call = f"finite_registered_atomic_source_lexical_{index}_source_projected"
        if binder_names:
            call += " " + " ".join(binder_names)
        return call

    def lean_truth_condition_source_call(index: int, binder_names: list[str]) -> str:
        call = (
            "finite_registered_atomic_truth_condition_source_certificate."
            f"finite_registered_atomic_truth_condition_source_lexical_{index}_source_to_spec"
        )
        if binder_names:
            call += " " + " ".join(binder_names)
        return call

    def lean_transition_source_type(
        transition: tuple[str, str, str, str],
    ) -> str:
        theme, scale, source, target_state, term = transition_parts(transition)
        return (
            "RegisteredStateTransitionTruth "
            f"{theme} {scale} {source} {target_state} -> "
            "concrete_registered_truth_conditions."
            f"fully_registered_truth_denotes TransitionT {term}"
        )

    def lean_transition_kernel_type(
        transition: tuple[str, str, str, str],
    ) -> str:
        theme, scale, source, target_state, term = transition_parts(transition)
        return (
            "RegisteredStateTransitionTruth "
            f"{theme} {scale} {source} {target_state} -> "
            "concrete_registered_truth_kernel."
            f"concrete_registered_kernel_denotes TransitionT {term}"
        )

    def lean_transition_source_value(
        transition: tuple[str, str, str, str],
    ) -> str:
        theme, scale, source, target_state, _term = transition_parts(transition)
        return (
            "fun h_source => concrete_registered_truth_conditions."
            "fully_registered_truth_transition "
            f"{theme} {scale} {source} {target_state} h_source"
        )

    def lean_transition_atomic_type(
        transition: tuple[str, str, str, str],
    ) -> str:
        _theme, _scale, _source, _target_state, term = transition_parts(transition)
        return f"AtomicClosureTruth TransitionT {term}"

    def coq_schema_source_type(schema: LexicalApplicationSchema) -> list[str]:
        result_type, application, binders, _binder_names = schema_parts(schema)
        source = f"RegisteredLexicalApplicationTruth {result_type} ({application})"
        conclusion = (
            "fully_registered_truth_denotes concrete_registered_truth_conditions "
            f"{result_type} ({application})"
        )
        if not binders:
            return [f"{source} ->", f"      {conclusion}"]
        binder_text = ", ".join(
            f"forall {name} : {type_name}" for name, type_name in binders
        )
        return [f"{binder_text},", f"      {source} ->", f"      {conclusion}"]

    def coq_schema_kernel_type(schema: LexicalApplicationSchema) -> list[str]:
        result_type, application, binders, _binder_names = schema_parts(schema)
        source = f"RegisteredLexicalApplicationTruth {result_type} ({application})"
        conclusion = (
            "concrete_registered_kernel_denotes concrete_registered_truth_kernel "
            f"{result_type} ({application})"
        )
        if not binders:
            return [f"{source} ->", f"      {conclusion}"]
        binder_text = ", ".join(
            f"forall {name} : {type_name}" for name, type_name in binders
        )
        return [f"{binder_text},", f"      {source} ->", f"      {conclusion}"]

    def coq_schema_source_value(schema: LexicalApplicationSchema) -> str:
        result_type, application, _binders, binder_names = schema_parts(schema)
        h_name = "h_source"
        value = (
            "fully_registered_truth_lexical_application "
            f"concrete_registered_truth_conditions {result_type} "
            f"({application}) {h_name}"
        )
        return f"fun {' '.join([*binder_names, h_name])} => {value}"

    def coq_schema_atomic_type(schema: LexicalApplicationSchema) -> list[str]:
        result_type, application, binders, _binder_names = schema_parts(schema)
        conclusion = f"AtomicClosureTruth {result_type} ({application})"
        if not binders:
            return [conclusion]
        binder_text = ", ".join(
            f"forall {name} : {type_name}" for name, type_name in binders
        )
        return [f"{binder_text},", f"      {conclusion}"]

    def coq_transition_source_type(
        transition: tuple[str, str, str, str],
    ) -> list[str]:
        theme, scale, source, target_state, term = transition_parts(transition)
        return [
            "RegisteredStateTransitionTruth "
            f"{theme} {scale} {source} {target_state} ->",
            "      fully_registered_truth_denotes concrete_registered_truth_conditions "
            f"TransitionT {term}",
        ]

    def coq_transition_kernel_type(
        transition: tuple[str, str, str, str],
    ) -> list[str]:
        theme, scale, source, target_state, term = transition_parts(transition)
        return [
            "RegisteredStateTransitionTruth "
            f"{theme} {scale} {source} {target_state} ->",
            "      concrete_registered_kernel_denotes concrete_registered_truth_kernel "
            f"TransitionT {term}",
        ]

    def coq_transition_source_value(
        transition: tuple[str, str, str, str],
    ) -> str:
        theme, scale, source, target_state, _term = transition_parts(transition)
        return (
            "fun h_source => fully_registered_truth_transition "
            f"concrete_registered_truth_conditions {theme} {scale} "
            f"{source} {target_state} h_source"
        )

    def coq_transition_atomic_type(
        transition: tuple[str, str, str, str],
    ) -> str:
        _theme, _scale, _source, _target_state, term = transition_parts(transition)
        return f"AtomicClosureTruth TransitionT {term}"

    if target == "lean":
        lines = [
            "structure FiniteRegisteredAtomicTruthConditionSourceCertificate : Type where",
            "  finite_registered_atomic_truth_condition_source_alignment : "
            "FiniteRegisteredAtomicKernelAlignmentCertificate",
            "  finite_registered_atomic_truth_condition_source_alignment_eq :",
            "      finite_registered_atomic_truth_condition_source_alignment = "
            "finite_registered_atomic_kernel_alignment_certificate",
            "  finite_registered_atomic_truth_condition_source_spec : "
            "FullyRegisteredTruthConditionSpec",
            "  finite_registered_atomic_truth_condition_source_spec_eq :",
            "      finite_registered_atomic_truth_condition_source_spec = "
            "concrete_registered_truth_conditions",
            "  finite_registered_atomic_truth_condition_source_sound :",
            "      (A : Type) -> (term : A) ->",
            "      concrete_registered_truth_conditions."
            "fully_registered_truth_denotes A term ->",
            "      AtomicClosureTruth A term",
        ]
        for index, schema in enumerate(schemas, 1):
            lines.append(
                "  "
                f"finite_registered_atomic_truth_condition_source_lexical_{index}_source_to_spec : "
                f"{lean_schema_source_type(schema)}"
            )
        for index, transition in enumerate(transitions, 1):
            lines.append(
                "  "
                f"finite_registered_atomic_truth_condition_source_transition_{index}_source_to_spec : "
                f"{lean_transition_source_type(transition)}"
            )
        lines.extend(
            [
                "",
                "def finite_registered_atomic_truth_condition_source_certificate :",
                "    FiniteRegisteredAtomicTruthConditionSourceCertificate := {",
                "  finite_registered_atomic_truth_condition_source_alignment := "
                "finite_registered_atomic_kernel_alignment_certificate,",
                "  finite_registered_atomic_truth_condition_source_alignment_eq := rfl,",
                "  finite_registered_atomic_truth_condition_source_spec := "
                "concrete_registered_truth_conditions,",
                "  finite_registered_atomic_truth_condition_source_spec_eq := rfl,",
                "  finite_registered_atomic_truth_condition_source_sound := "
                "concrete_registered_truth_conditions_imply_atomic_closure,",
            ]
        )
        assignments: list[tuple[str, str]] = []
        for index, schema in enumerate(schemas, 1):
            assignments.append(
                (
                    f"finite_registered_atomic_truth_condition_source_lexical_{index}_source_to_spec",
                    lean_schema_source_value(schema),
                )
            )
        for index, transition in enumerate(transitions, 1):
            assignments.append(
                (
                    f"finite_registered_atomic_truth_condition_source_transition_{index}_source_to_spec",
                    lean_transition_source_value(transition),
                )
            )
        for index, (field, value) in enumerate(assignments):
            suffix = "," if index < len(assignments) - 1 else ""
            lines.append(f"  {field} := {value}{suffix}")
        lines.extend(
            [
                "}",
                "",
                "theorem finite_registered_atomic_truth_condition_source_certificate_exists :",
                "    Exists (fun C : "
                "FiniteRegisteredAtomicTruthConditionSourceCertificate => "
                "C = finite_registered_atomic_truth_condition_source_certificate) := by",
                "  exact Exists.intro "
                "finite_registered_atomic_truth_condition_source_certificate rfl",
                "",
                "theorem finite_registered_atomic_truth_condition_source_alignment_matches :",
                "    finite_registered_atomic_truth_condition_source_certificate."
                "finite_registered_atomic_truth_condition_source_alignment =",
                "      finite_registered_atomic_kernel_alignment_certificate := by",
                "  exact finite_registered_atomic_truth_condition_source_certificate."
                "finite_registered_atomic_truth_condition_source_alignment_eq",
                "",
                "theorem finite_registered_atomic_truth_condition_source_spec_matches :",
                "    finite_registered_atomic_truth_condition_source_certificate."
                "finite_registered_atomic_truth_condition_source_spec =",
                "      concrete_registered_truth_conditions := by",
                "  exact finite_registered_atomic_truth_condition_source_certificate."
                "finite_registered_atomic_truth_condition_source_spec_eq",
                "",
                "theorem finite_registered_atomic_truth_condition_source_sound_projected :",
                "    (A : Type) -> (term : A) ->",
                "    concrete_registered_truth_conditions."
                "fully_registered_truth_denotes A term ->",
                "    AtomicClosureTruth A term := by",
                "  exact finite_registered_atomic_truth_condition_source_certificate."
                "finite_registered_atomic_truth_condition_source_sound",
            ]
        )
        for index, schema in enumerate(schemas, 1):
            _result_type, _application, _binders, binder_names = schema_parts(schema)
            lines.extend(
                [
                    "",
                    "theorem "
                    f"finite_registered_atomic_truth_condition_source_lexical_{index}_source_to_spec_projected :",
                    f"    {lean_schema_source_type(schema)} := by",
                    "  exact finite_registered_atomic_truth_condition_source_certificate."
                    f"finite_registered_atomic_truth_condition_source_lexical_{index}_source_to_spec",
                    "",
                    "theorem "
                    f"finite_registered_atomic_truth_condition_source_lexical_{index}_source_to_kernel_projected :",
                    f"    {lean_schema_kernel_type(schema)} := by",
                    "  exact finite_registered_atomic_truth_condition_source_certificate."
                    "finite_registered_atomic_truth_condition_source_alignment."
                    f"finite_registered_atomic_kernel_alignment_lexical_{index}_source_to_kernel",
                    "",
                    "theorem "
                    f"finite_registered_atomic_truth_condition_source_lexical_{index}_atomic_projected :",
                    f"    {lean_schema_atomic_type(schema)} := by",
                ]
            )
            if binder_names:
                lines.append(f"  intro {' '.join(binder_names)}")
            lines.extend(
                [
                    "  apply concrete_registered_truth_conditions_imply_atomic_closure",
                    "  exact "
                    f"{lean_truth_condition_source_call(index, binder_names)} "
                    f"({lean_schema_source_call(index, binder_names)})",
                ]
            )
        for index, transition in enumerate(transitions, 1):
            lines.extend(
                [
                    "",
                    "theorem "
                    f"finite_registered_atomic_truth_condition_source_transition_{index}_source_to_spec_projected :",
                    f"    {lean_transition_source_type(transition)} := by",
                    "  exact finite_registered_atomic_truth_condition_source_certificate."
                    f"finite_registered_atomic_truth_condition_source_transition_{index}_source_to_spec",
                    "",
                    "theorem "
                    f"finite_registered_atomic_truth_condition_source_transition_{index}_source_to_kernel_projected :",
                    f"    {lean_transition_kernel_type(transition)} := by",
                    "  exact finite_registered_atomic_truth_condition_source_certificate."
                    "finite_registered_atomic_truth_condition_source_alignment."
                    f"finite_registered_atomic_kernel_alignment_transition_{index}_source_to_kernel",
                    "",
                    "theorem "
                    f"finite_registered_atomic_truth_condition_source_transition_{index}_atomic_projected :",
                    f"    {lean_transition_atomic_type(transition)} := by",
                    "  apply concrete_registered_truth_conditions_imply_atomic_closure",
                    "  exact finite_registered_atomic_truth_condition_source_certificate."
                    f"finite_registered_atomic_truth_condition_source_transition_{index}_source_to_spec "
                    f"(finite_registered_atomic_source_transition_{index}_source_projected)",
                ]
            )
        return lines

    lines = [
        "Record FiniteRegisteredAtomicTruthConditionSourceCertificate : Type := {",
        "  finite_registered_atomic_truth_condition_source_alignment : "
        "FiniteRegisteredAtomicKernelAlignmentCertificate;",
        "  finite_registered_atomic_truth_condition_source_alignment_eq :",
        "      finite_registered_atomic_truth_condition_source_alignment = "
        "finite_registered_atomic_kernel_alignment_certificate;",
        "  finite_registered_atomic_truth_condition_source_spec : "
        "FullyRegisteredTruthConditionSpec;",
        "  finite_registered_atomic_truth_condition_source_spec_eq :",
        "      finite_registered_atomic_truth_condition_source_spec = "
        "concrete_registered_truth_conditions;",
        "  finite_registered_atomic_truth_condition_source_sound :",
        "      forall A : Type, forall term : A,",
        "      fully_registered_truth_denotes concrete_registered_truth_conditions A term ->",
        "      AtomicClosureTruth A term;",
    ]
    for index, schema in enumerate(schemas, 1):
        type_lines = coq_schema_source_type(schema)
        lines.append(
            "  "
            f"finite_registered_atomic_truth_condition_source_lexical_{index}_source_to_spec : "
            + type_lines[0]
        )
        lines.extend(type_lines[1:])
        lines[-1] += ";"
    for index, transition in enumerate(transitions, 1):
        type_lines = coq_transition_source_type(transition)
        lines.append(
            "  "
            f"finite_registered_atomic_truth_condition_source_transition_{index}_source_to_spec : "
            + type_lines[0]
        )
        lines.extend(type_lines[1:])
        lines[-1] += ";"
    lines[-1] = lines[-1].rstrip(";")
    lines.extend(
        [
            "}.",
            "",
            "Definition finite_registered_atomic_truth_condition_source_certificate :",
            "  FiniteRegisteredAtomicTruthConditionSourceCertificate := {|",
            "  finite_registered_atomic_truth_condition_source_alignment := "
            "finite_registered_atomic_kernel_alignment_certificate;",
            "  finite_registered_atomic_truth_condition_source_alignment_eq := eq_refl;",
            "  finite_registered_atomic_truth_condition_source_spec := "
            "concrete_registered_truth_conditions;",
            "  finite_registered_atomic_truth_condition_source_spec_eq := eq_refl;",
            "  finite_registered_atomic_truth_condition_source_sound := "
            "concrete_registered_truth_conditions_imply_atomic_closure;",
        ]
    )
    assignments = []
    for index, schema in enumerate(schemas, 1):
        assignments.append(
            (
                f"finite_registered_atomic_truth_condition_source_lexical_{index}_source_to_spec",
                coq_schema_source_value(schema),
            )
        )
    for index, transition in enumerate(transitions, 1):
        assignments.append(
            (
                f"finite_registered_atomic_truth_condition_source_transition_{index}_source_to_spec",
                coq_transition_source_value(transition),
            )
        )
    for index, (field, value) in enumerate(assignments):
        suffix = ";" if index < len(assignments) - 1 else ""
        lines.append(f"  {field} := {value}{suffix}")
    lines.extend(
        [
            "|}.",
            "",
            "Theorem finite_registered_atomic_truth_condition_source_certificate_exists :",
            "  exists C : FiniteRegisteredAtomicTruthConditionSourceCertificate,",
            "    C = finite_registered_atomic_truth_condition_source_certificate.",
            "Proof.",
            "  exists finite_registered_atomic_truth_condition_source_certificate.",
            "  reflexivity.",
            "Qed.",
            "",
            "Theorem finite_registered_atomic_truth_condition_source_alignment_matches :",
            "  finite_registered_atomic_truth_condition_source_alignment",
            "    finite_registered_atomic_truth_condition_source_certificate =",
            "  finite_registered_atomic_kernel_alignment_certificate.",
            "Proof.",
            "  exact (finite_registered_atomic_truth_condition_source_alignment_eq",
            "    finite_registered_atomic_truth_condition_source_certificate).",
            "Qed.",
            "",
            "Theorem finite_registered_atomic_truth_condition_source_spec_matches :",
            "  finite_registered_atomic_truth_condition_source_spec",
            "    finite_registered_atomic_truth_condition_source_certificate =",
            "  concrete_registered_truth_conditions.",
            "Proof.",
            "  exact (finite_registered_atomic_truth_condition_source_spec_eq",
            "    finite_registered_atomic_truth_condition_source_certificate).",
            "Qed.",
            "",
            "Theorem finite_registered_atomic_truth_condition_source_sound_projected :",
            "  forall A : Type, forall term : A,",
            "    fully_registered_truth_denotes concrete_registered_truth_conditions A term ->",
            "    AtomicClosureTruth A term.",
            "Proof.",
            "  exact (finite_registered_atomic_truth_condition_source_sound",
            "    finite_registered_atomic_truth_condition_source_certificate).",
            "Qed.",
        ]
    )
    for index, schema in enumerate(schemas, 1):
        _result_type, _application, _binders, binder_names = schema_parts(schema)
        type_lines = coq_schema_source_type(schema)
        lines.extend(
            [
                "",
                "Theorem "
                f"finite_registered_atomic_truth_condition_source_lexical_{index}_source_to_spec_projected :",
                f"  {type_lines[0]}",
            ]
        )
        lines.extend(type_lines[1:])
        lines[-1] += "."
        lines.extend(
            [
                "Proof.",
                "  exact ("
                f"finite_registered_atomic_truth_condition_source_lexical_{index}_source_to_spec",
                "    finite_registered_atomic_truth_condition_source_certificate).",
                "Qed.",
                "",
                "Theorem "
                f"finite_registered_atomic_truth_condition_source_lexical_{index}_source_to_kernel_projected :",
            ]
        )
        kernel_type_lines = coq_schema_kernel_type(schema)
        lines.append(f"  {kernel_type_lines[0]}")
        lines.extend(kernel_type_lines[1:])
        lines[-1] += "."
        lines.extend(
            [
                "Proof.",
                "  exact ("
                f"finite_registered_atomic_kernel_alignment_lexical_{index}_source_to_kernel",
                "    (finite_registered_atomic_truth_condition_source_alignment",
                "      finite_registered_atomic_truth_condition_source_certificate)).",
                "Qed.",
                "",
                "Theorem "
                f"finite_registered_atomic_truth_condition_source_lexical_{index}_atomic_projected :",
            ]
        )
        atomic_type_lines = coq_schema_atomic_type(schema)
        lines.append(f"  {atomic_type_lines[0]}")
        lines.extend(atomic_type_lines[1:])
        lines[-1] += "."
        lines.append("Proof.")
        if binder_names:
            lines.append(f"  intros {' '.join(binder_names)}.")
        lines.extend(
            [
                "  apply concrete_registered_truth_conditions_imply_atomic_closure.",
                "  exact ("
                f"finite_registered_atomic_truth_condition_source_lexical_{index}_source_to_spec",
                "    finite_registered_atomic_truth_condition_source_certificate",
            ]
        )
        if binder_names:
            lines.append(f"    {' '.join(binder_names)}")
        source_call = f"finite_registered_atomic_source_lexical_{index}_source_projected"
        if binder_names:
            source_call += " " + " ".join(binder_names)
        lines.extend(
            [
                f"    ({source_call})).",
                "Qed.",
            ]
        )
    for index, transition in enumerate(transitions, 1):
        type_lines = coq_transition_source_type(transition)
        lines.extend(
            [
                "",
                "Theorem "
                f"finite_registered_atomic_truth_condition_source_transition_{index}_source_to_spec_projected :",
                f"  {type_lines[0]}",
            ]
        )
        lines.extend(type_lines[1:])
        lines[-1] += "."
        lines.extend(
            [
                "Proof.",
                "  exact ("
                f"finite_registered_atomic_truth_condition_source_transition_{index}_source_to_spec",
                "    finite_registered_atomic_truth_condition_source_certificate).",
                "Qed.",
                "",
                "Theorem "
                f"finite_registered_atomic_truth_condition_source_transition_{index}_source_to_kernel_projected :",
            ]
        )
        kernel_type_lines = coq_transition_kernel_type(transition)
        lines.append(f"  {kernel_type_lines[0]}")
        lines.extend(kernel_type_lines[1:])
        lines[-1] += "."
        lines.extend(
            [
                "Proof.",
                "  exact ("
                f"finite_registered_atomic_kernel_alignment_transition_{index}_source_to_kernel",
                "    (finite_registered_atomic_truth_condition_source_alignment",
                "      finite_registered_atomic_truth_condition_source_certificate)).",
                "Qed.",
                "",
                "Theorem "
                f"finite_registered_atomic_truth_condition_source_transition_{index}_atomic_projected :",
                f"  {coq_transition_atomic_type(transition)}.",
                "Proof.",
                "  apply concrete_registered_truth_conditions_imply_atomic_closure.",
                "  exact ("
                f"finite_registered_atomic_truth_condition_source_transition_{index}_source_to_spec",
                "    finite_registered_atomic_truth_condition_source_certificate",
                f"    (finite_registered_atomic_source_transition_{index}_source_projected)).",
                "Qed.",
            ]
        )
    return lines


def concrete_registered_example_truth_instance_lines(
    results: list[dict[str, Any]],
    target: str,
) -> list[str]:
    """Package the exported examples' concrete registered truth proofs."""

    if target == "lean":
        lines = ["structure ConcreteRegisteredExampleTruthInstances : Type where"]
        for idx, result in enumerate(results, 1):
            annotation = export_result_type(result["ast"])
            lines.append(
                f"  example_{idx}_concrete_truth_instance : "
                "concrete_registered_truth_conditions."
                f"fully_registered_truth_denotes {annotation} example_{idx}"
            )
        lines.extend(
            [
                "",
                "def concrete_registered_example_truth_instances : "
                "ConcreteRegisteredExampleTruthInstances := {",
            ]
        )
        for idx in range(1, len(results) + 1):
            suffix = "," if idx < len(results) else ""
            lines.append(
                f"  example_{idx}_concrete_truth_instance := "
                f"example_{idx}_concrete_registered_truth_condition_sound{suffix}"
            )
        lines.extend(
            [
                "}",
                "",
                "theorem concrete_registered_example_truth_instances_exists :",
                "    Exists (fun I : ConcreteRegisteredExampleTruthInstances => "
                "I = concrete_registered_example_truth_instances) := by",
                "  exact Exists.intro concrete_registered_example_truth_instances rfl",
            ]
        )
        for idx, result in enumerate(results, 1):
            annotation = export_result_type(result["ast"])
            lines.extend(
                [
                    "",
                    "theorem "
                    f"concrete_registered_example_{idx}_truth_instance_atomic_sound : "
                    f"AtomicClosureTruth {annotation} example_{idx} := by",
                    "  apply concrete_registered_truth_conditions_imply_atomic_closure",
                    "  exact concrete_registered_example_truth_instances."
                    f"example_{idx}_concrete_truth_instance",
                ]
            )
        return lines

    lines = ["Record ConcreteRegisteredExampleTruthInstances : Type := {"]
    for idx, result in enumerate(results, 1):
        annotation = export_result_type(result["ast"])
        suffix = ";" if idx < len(results) else ""
        lines.extend(
            [
                f"  example_{idx}_concrete_truth_instance :",
                "      fully_registered_truth_denotes "
                "concrete_registered_truth_conditions "
                f"{annotation} example_{idx}{suffix}",
            ]
        )
    lines.extend(
        [
            "}.",
            "",
            "Definition concrete_registered_example_truth_instances : "
            "ConcreteRegisteredExampleTruthInstances := {|",
        ]
    )
    for idx in range(1, len(results) + 1):
        suffix = ";" if idx < len(results) else ""
        lines.append(
            f"  example_{idx}_concrete_truth_instance := "
            f"example_{idx}_concrete_registered_truth_condition_sound{suffix}"
        )
    lines.extend(
        [
            "|}.",
            "",
            "Theorem concrete_registered_example_truth_instances_exists :",
            "  exists I : ConcreteRegisteredExampleTruthInstances,",
            "    I = concrete_registered_example_truth_instances.",
            "Proof.",
            "  exists concrete_registered_example_truth_instances. reflexivity.",
            "Qed.",
        ]
    )
    for idx, result in enumerate(results, 1):
        annotation = export_result_type(result["ast"])
        lines.extend(
            [
                "",
                "Theorem "
                f"concrete_registered_example_{idx}_truth_instance_atomic_sound : "
                f"AtomicClosureTruth {annotation} example_{idx}.",
                "Proof.",
                "  apply concrete_registered_truth_conditions_imply_atomic_closure.",
                "  exact (example_"
                f"{idx}_concrete_truth_instance "
                "concrete_registered_example_truth_instances).",
                "Qed.",
            ]
        )
    return lines


def concrete_registered_evidence_backed_example_truth_instance_lines(
    results: list[dict[str, Any]],
    target: str,
) -> list[str]:
    """Package truth proofs induced by registered evidence-backed sources."""

    if target == "lean":
        lines = [
            "structure ConcreteRegisteredEvidenceBackedExampleTruthInstances : Type where"
        ]
        for idx, result in enumerate(results, 1):
            annotation = export_result_type(result["ast"])
            lines.append(
                f"  example_{idx}_evidence_backed_truth_instance : "
                "concrete_registered_evidence_backed_truth_conditions."
                f"fully_registered_truth_denotes {annotation} example_{idx}"
            )
        lines.extend(
            [
                "",
                "def concrete_registered_evidence_backed_example_truth_instances : "
                "ConcreteRegisteredEvidenceBackedExampleTruthInstances := {",
            ]
        )
        for idx in range(1, len(results) + 1):
            suffix = "," if idx < len(results) else ""
            lines.append(
                f"  example_{idx}_evidence_backed_truth_instance := "
                f"example_{idx}_concrete_registered_evidence_backed_truth_condition_sound"
                f"{suffix}"
            )
        lines.extend(
            [
                "}",
                "",
                "theorem concrete_registered_evidence_backed_example_truth_instances_exists :",
                "    Exists (fun I : ConcreteRegisteredEvidenceBackedExampleTruthInstances => "
                "I = concrete_registered_evidence_backed_example_truth_instances) := by",
                "  exact Exists.intro "
                "concrete_registered_evidence_backed_example_truth_instances rfl",
            ]
        )
        for idx, result in enumerate(results, 1):
            annotation = export_result_type(result["ast"])
            lines.extend(
                [
                    "",
                    "theorem "
                    f"concrete_registered_evidence_backed_example_{idx}_truth_instance_atomic_sound : "
                    f"AtomicClosureTruth {annotation} example_{idx} := by",
                    "  apply "
                    "concrete_registered_evidence_backed_truth_conditions_imply_atomic_closure",
                    "  exact concrete_registered_evidence_backed_example_truth_instances."
                    f"example_{idx}_evidence_backed_truth_instance",
                ]
            )
        return lines

    lines = [
        "Record ConcreteRegisteredEvidenceBackedExampleTruthInstances : Type := {"
    ]
    for idx, result in enumerate(results, 1):
        annotation = export_result_type(result["ast"])
        suffix = ";" if idx < len(results) else ""
        lines.extend(
            [
                f"  example_{idx}_evidence_backed_truth_instance :",
                "      fully_registered_truth_denotes "
                "concrete_registered_evidence_backed_truth_conditions "
                f"{annotation} example_{idx}{suffix}",
            ]
        )
    lines.extend(
        [
            "}.",
            "",
            "Definition concrete_registered_evidence_backed_example_truth_instances : "
            "ConcreteRegisteredEvidenceBackedExampleTruthInstances := {|",
        ]
    )
    for idx in range(1, len(results) + 1):
        suffix = ";" if idx < len(results) else ""
        lines.append(
            f"  example_{idx}_evidence_backed_truth_instance := "
            f"example_{idx}_concrete_registered_evidence_backed_truth_condition_sound"
            f"{suffix}"
        )
    lines.extend(
        [
            "|}.",
            "",
            "Theorem concrete_registered_evidence_backed_example_truth_instances_exists :",
            "  exists I : ConcreteRegisteredEvidenceBackedExampleTruthInstances,",
            "    I = concrete_registered_evidence_backed_example_truth_instances.",
            "Proof.",
            "  exists concrete_registered_evidence_backed_example_truth_instances.",
            "  reflexivity.",
            "Qed.",
        ]
    )
    for idx, result in enumerate(results, 1):
        annotation = export_result_type(result["ast"])
        lines.extend(
            [
                "",
                "Theorem "
                f"concrete_registered_evidence_backed_example_{idx}_truth_instance_atomic_sound : "
                f"AtomicClosureTruth {annotation} example_{idx}.",
                "Proof.",
                "  apply "
                "concrete_registered_evidence_backed_truth_conditions_imply_atomic_closure.",
                "  exact (example_"
                f"{idx}_evidence_backed_truth_instance "
                "concrete_registered_evidence_backed_example_truth_instances).",
                "Qed.",
            ]
        )
    return lines


def concrete_registered_kernel_example_truth_instance_lines(
    results: list[dict[str, Any]],
    target: str,
) -> list[str]:
    """Package truth proofs induced by the concrete registered kernel."""

    if target == "lean":
        lines = ["structure ConcreteRegisteredKernelExampleTruthInstances : Type where"]
        for idx, result in enumerate(results, 1):
            annotation = export_result_type(result["ast"])
            lines.append(
                f"  example_{idx}_kernel_truth_instance : "
                "concrete_registered_truth_conditions_from_kernel."
                f"fully_registered_truth_denotes {annotation} example_{idx}"
            )
        lines.extend(
            [
                "",
                "def concrete_registered_kernel_example_truth_instances : "
                "ConcreteRegisteredKernelExampleTruthInstances := {",
            ]
        )
        for idx in range(1, len(results) + 1):
            suffix = "," if idx < len(results) else ""
            lines.append(
                f"  example_{idx}_kernel_truth_instance := "
                f"example_{idx}_concrete_registered_truth_conditions_from_kernel_sound"
                f"{suffix}"
            )
        lines.extend(
            [
                "}",
                "",
                "theorem concrete_registered_kernel_example_truth_instances_exists :",
                "    Exists (fun I : ConcreteRegisteredKernelExampleTruthInstances => "
                "I = concrete_registered_kernel_example_truth_instances) := by",
                "  exact Exists.intro "
                "concrete_registered_kernel_example_truth_instances rfl",
            ]
        )
        for idx, result in enumerate(results, 1):
            annotation = export_result_type(result["ast"])
            lines.extend(
                [
                    "",
                    "theorem "
                    f"concrete_registered_kernel_example_{idx}_truth_instance_atomic_sound : "
                    f"AtomicClosureTruth {annotation} example_{idx} := by",
                    "  apply "
                    "concrete_registered_truth_conditions_from_kernel_imply_atomic_closure",
                    "  exact concrete_registered_kernel_example_truth_instances."
                    f"example_{idx}_kernel_truth_instance",
                ]
            )
        return lines

    lines = ["Record ConcreteRegisteredKernelExampleTruthInstances : Type := {"]
    for idx, result in enumerate(results, 1):
        annotation = export_result_type(result["ast"])
        suffix = ";" if idx < len(results) else ""
        lines.extend(
            [
                f"  example_{idx}_kernel_truth_instance :",
                "      fully_registered_truth_denotes "
                "concrete_registered_truth_conditions_from_kernel "
                f"{annotation} example_{idx}{suffix}",
            ]
        )
    lines.extend(
        [
            "}.",
            "",
            "Definition concrete_registered_kernel_example_truth_instances : "
            "ConcreteRegisteredKernelExampleTruthInstances := {|",
        ]
    )
    for idx in range(1, len(results) + 1):
        suffix = ";" if idx < len(results) else ""
        lines.append(
            f"  example_{idx}_kernel_truth_instance := "
            f"example_{idx}_concrete_registered_truth_conditions_from_kernel_sound"
            f"{suffix}"
        )
    lines.extend(
        [
            "|}.",
            "",
            "Theorem concrete_registered_kernel_example_truth_instances_exists :",
            "  exists I : ConcreteRegisteredKernelExampleTruthInstances,",
            "    I = concrete_registered_kernel_example_truth_instances.",
            "Proof.",
            "  exists concrete_registered_kernel_example_truth_instances. reflexivity.",
            "Qed.",
        ]
    )
    for idx, result in enumerate(results, 1):
        annotation = export_result_type(result["ast"])
        lines.extend(
            [
                "",
                "Theorem "
                f"concrete_registered_kernel_example_{idx}_truth_instance_atomic_sound : "
                f"AtomicClosureTruth {annotation} example_{idx}.",
                "Proof.",
                "  apply "
                "concrete_registered_truth_conditions_from_kernel_imply_atomic_closure.",
                "  exact (example_"
                f"{idx}_kernel_truth_instance "
                "concrete_registered_kernel_example_truth_instances).",
                "Qed.",
            ]
        )
    return lines


def concrete_registered_truth_condition_route_lines(
    results: list[dict[str, Any]],
    target: str,
) -> list[str]:
    """Package the concrete registered truth-condition routes together."""

    if target == "lean":
        lines = [
            "structure ConcreteRegisteredTruthConditionRoute : Type where",
            "  concrete_registered_route_direct_model : "
            "ConcreteRegisteredTruthConditionModel",
            "  concrete_registered_route_evidence_sources : "
            "RegisteredEvidenceBackedTruthConditionSources",
            "  concrete_registered_route_evidence_model : "
            "ConcreteRegisteredEvidenceBackedTruthConditionModel",
            "  concrete_registered_route_kernel : ConcreteRegisteredTruthKernel",
            "  concrete_registered_route_direct_spec : "
            "FullyRegisteredTruthConditionSpec",
            "  concrete_registered_route_evidence_spec : "
            "FullyRegisteredTruthConditionSpec",
            "  concrete_registered_route_kernel_spec : "
            "FullyRegisteredTruthConditionSpec",
            "  concrete_registered_route_direct_examples : "
            "ConcreteRegisteredExampleTruthInstances",
            "  concrete_registered_route_evidence_examples : "
            "ConcreteRegisteredEvidenceBackedExampleTruthInstances",
            "  concrete_registered_route_kernel_examples : "
            "ConcreteRegisteredKernelExampleTruthInstances",
            "",
            "def concrete_registered_truth_condition_route : "
            "ConcreteRegisteredTruthConditionRoute := {",
            "  concrete_registered_route_direct_model := "
            "concrete_registered_truth_condition_model,",
            "  concrete_registered_route_evidence_sources := "
            "concrete_registered_evidence_backed_truth_sources,",
            "  concrete_registered_route_evidence_model := "
            "concrete_registered_evidence_backed_truth_condition_model,",
            "  concrete_registered_route_kernel := concrete_registered_truth_kernel,",
            "  concrete_registered_route_direct_spec := "
            "concrete_registered_truth_conditions,",
            "  concrete_registered_route_evidence_spec := "
            "concrete_registered_evidence_backed_truth_conditions,",
            "  concrete_registered_route_kernel_spec := "
            "concrete_registered_truth_conditions_from_kernel,",
            "  concrete_registered_route_direct_examples := "
            "concrete_registered_example_truth_instances,",
            "  concrete_registered_route_evidence_examples := "
            "concrete_registered_evidence_backed_example_truth_instances,",
            "  concrete_registered_route_kernel_examples := "
            "concrete_registered_kernel_example_truth_instances",
            "}",
            "",
            "theorem concrete_registered_truth_condition_route_exists :",
            "    Exists (fun R : ConcreteRegisteredTruthConditionRoute => "
            "R = concrete_registered_truth_condition_route) := by",
            "  exact Exists.intro concrete_registered_truth_condition_route rfl",
            "",
            "theorem "
            "concrete_registered_truth_condition_route_direct_spec_matches_model :",
            "    concrete_registered_truth_condition_route."
            "concrete_registered_route_direct_spec =",
            "      concrete_registered_truth_condition_route."
            "concrete_registered_route_direct_model."
            "concrete_registered_model_spec := by",
            "  rfl",
            "",
            "theorem "
            "concrete_registered_truth_condition_route_evidence_spec_matches_model :",
            "    concrete_registered_truth_condition_route."
            "concrete_registered_route_evidence_spec =",
            "      concrete_registered_truth_condition_route."
            "concrete_registered_route_evidence_model."
            "concrete_registered_evidence_backed_model_spec := by",
            "  rfl",
            "",
            "theorem "
            "concrete_registered_truth_condition_route_kernel_spec_matches_kernel :",
            "    concrete_registered_truth_condition_route."
            "concrete_registered_route_kernel_spec =",
            "      fully_registered_truth_conditions_from_concrete_registered_kernel",
            "        concrete_registered_truth_condition_route."
            "concrete_registered_route_kernel := by",
            "  rfl",
            "",
            "theorem concrete_registered_truth_condition_route_direct_spec_sound :",
            "    (A : Type) -> (term : A) -> "
            "concrete_registered_truth_condition_route."
            "concrete_registered_route_direct_spec."
            "fully_registered_truth_denotes A term -> "
            "AtomicClosureTruth A term := by",
            "  intro A term h",
            "  apply concrete_registered_truth_conditions_imply_atomic_closure",
            "  exact h",
            "",
            "theorem concrete_registered_truth_condition_route_evidence_spec_sound :",
            "    (A : Type) -> (term : A) -> "
            "concrete_registered_truth_condition_route."
            "concrete_registered_route_evidence_spec."
            "fully_registered_truth_denotes A term -> "
            "AtomicClosureTruth A term := by",
            "  intro A term h",
            "  apply "
            "concrete_registered_evidence_backed_truth_conditions_imply_atomic_closure",
            "  exact h",
            "",
            "theorem concrete_registered_truth_condition_route_kernel_spec_sound :",
            "    (A : Type) -> (term : A) -> "
            "concrete_registered_truth_condition_route."
            "concrete_registered_route_kernel_spec."
            "fully_registered_truth_denotes A term -> "
            "AtomicClosureTruth A term := by",
            "  intro A term h",
            "  apply "
            "concrete_registered_truth_conditions_from_kernel_imply_atomic_closure",
            "  exact h",
        ]
        for idx, result in enumerate(results, 1):
            annotation = export_result_type(result["ast"])
            lines.extend(
                [
                    "",
                    "theorem "
                    f"concrete_registered_truth_condition_route_example_{idx}_direct_atomic_sound : "
                    f"AtomicClosureTruth {annotation} example_{idx} := by",
                    "  apply concrete_registered_truth_condition_route_direct_spec_sound",
                    "  exact concrete_registered_truth_condition_route."
                    "concrete_registered_route_direct_examples."
                    f"example_{idx}_concrete_truth_instance",
                    "",
                    "theorem "
                    f"concrete_registered_truth_condition_route_example_{idx}_evidence_atomic_sound : "
                    f"AtomicClosureTruth {annotation} example_{idx} := by",
                    "  apply concrete_registered_truth_condition_route_evidence_spec_sound",
                    "  exact concrete_registered_truth_condition_route."
                    "concrete_registered_route_evidence_examples."
                    f"example_{idx}_evidence_backed_truth_instance",
                    "",
                    "theorem "
                    f"concrete_registered_truth_condition_route_example_{idx}_kernel_atomic_sound : "
                    f"AtomicClosureTruth {annotation} example_{idx} := by",
                    "  apply concrete_registered_truth_condition_route_kernel_spec_sound",
                    "  exact concrete_registered_truth_condition_route."
                    "concrete_registered_route_kernel_examples."
                    f"example_{idx}_kernel_truth_instance",
                ]
            )
        return lines

    lines = [
        "Record ConcreteRegisteredTruthConditionRoute : Type := {",
        "  concrete_registered_route_direct_model : "
        "ConcreteRegisteredTruthConditionModel;",
        "  concrete_registered_route_evidence_sources : "
        "RegisteredEvidenceBackedTruthConditionSources;",
        "  concrete_registered_route_evidence_model : "
        "ConcreteRegisteredEvidenceBackedTruthConditionModel;",
        "  concrete_registered_route_kernel : ConcreteRegisteredTruthKernel;",
        "  concrete_registered_route_direct_spec : "
        "FullyRegisteredTruthConditionSpec;",
        "  concrete_registered_route_evidence_spec : "
        "FullyRegisteredTruthConditionSpec;",
        "  concrete_registered_route_kernel_spec : "
        "FullyRegisteredTruthConditionSpec;",
        "  concrete_registered_route_direct_examples : "
        "ConcreteRegisteredExampleTruthInstances;",
        "  concrete_registered_route_evidence_examples : "
        "ConcreteRegisteredEvidenceBackedExampleTruthInstances;",
        "  concrete_registered_route_kernel_examples : "
        "ConcreteRegisteredKernelExampleTruthInstances",
        "}.",
        "",
        "Definition concrete_registered_truth_condition_route :",
        "  ConcreteRegisteredTruthConditionRoute := {|",
        "  concrete_registered_route_direct_model := "
        "concrete_registered_truth_condition_model;",
        "  concrete_registered_route_evidence_sources := "
        "concrete_registered_evidence_backed_truth_sources;",
        "  concrete_registered_route_evidence_model := "
        "concrete_registered_evidence_backed_truth_condition_model;",
        "  concrete_registered_route_kernel := concrete_registered_truth_kernel;",
        "  concrete_registered_route_direct_spec := "
        "concrete_registered_truth_conditions;",
        "  concrete_registered_route_evidence_spec := "
        "concrete_registered_evidence_backed_truth_conditions;",
        "  concrete_registered_route_kernel_spec := "
        "concrete_registered_truth_conditions_from_kernel;",
        "  concrete_registered_route_direct_examples := "
        "concrete_registered_example_truth_instances;",
        "  concrete_registered_route_evidence_examples := "
        "concrete_registered_evidence_backed_example_truth_instances;",
        "  concrete_registered_route_kernel_examples := "
        "concrete_registered_kernel_example_truth_instances",
        "|}.",
        "",
        "Theorem concrete_registered_truth_condition_route_exists :",
        "  exists R : ConcreteRegisteredTruthConditionRoute,",
        "    R = concrete_registered_truth_condition_route.",
        "Proof.",
        "  exists concrete_registered_truth_condition_route. reflexivity.",
        "Qed.",
        "",
        "Theorem concrete_registered_truth_condition_route_direct_spec_matches_model :",
        "  concrete_registered_route_direct_spec "
        "concrete_registered_truth_condition_route =",
        "    concrete_registered_model_spec",
        "      (concrete_registered_route_direct_model",
        "        concrete_registered_truth_condition_route).",
        "Proof. reflexivity. Qed.",
        "",
        "Theorem concrete_registered_truth_condition_route_evidence_spec_matches_model :",
        "  concrete_registered_route_evidence_spec "
        "concrete_registered_truth_condition_route =",
        "    concrete_registered_evidence_backed_model_spec",
        "      (concrete_registered_route_evidence_model",
        "        concrete_registered_truth_condition_route).",
        "Proof. reflexivity. Qed.",
        "",
        "Theorem concrete_registered_truth_condition_route_kernel_spec_matches_kernel :",
        "  concrete_registered_route_kernel_spec "
        "concrete_registered_truth_condition_route =",
        "    fully_registered_truth_conditions_from_concrete_registered_kernel",
        "      (concrete_registered_route_kernel",
        "        concrete_registered_truth_condition_route).",
        "Proof. reflexivity. Qed.",
        "",
        "Theorem concrete_registered_truth_condition_route_direct_spec_sound :",
        "  forall A : Type, forall term : A,",
        "    fully_registered_truth_denotes",
        "      (concrete_registered_route_direct_spec",
        "        concrete_registered_truth_condition_route) A term ->",
        "    AtomicClosureTruth A term.",
        "Proof.",
        "  intros A term H.",
        "  apply concrete_registered_truth_conditions_imply_atomic_closure.",
        "  exact H.",
        "Qed.",
        "",
        "Theorem concrete_registered_truth_condition_route_evidence_spec_sound :",
        "  forall A : Type, forall term : A,",
        "    fully_registered_truth_denotes",
        "      (concrete_registered_route_evidence_spec",
        "        concrete_registered_truth_condition_route) A term ->",
        "    AtomicClosureTruth A term.",
        "Proof.",
        "  intros A term H.",
        "  apply "
        "concrete_registered_evidence_backed_truth_conditions_imply_atomic_closure.",
        "  exact H.",
        "Qed.",
        "",
        "Theorem concrete_registered_truth_condition_route_kernel_spec_sound :",
        "  forall A : Type, forall term : A,",
        "    fully_registered_truth_denotes",
        "      (concrete_registered_route_kernel_spec",
        "        concrete_registered_truth_condition_route) A term ->",
        "    AtomicClosureTruth A term.",
        "Proof.",
        "  intros A term H.",
        "  apply "
        "concrete_registered_truth_conditions_from_kernel_imply_atomic_closure.",
        "  exact H.",
        "Qed.",
    ]
    for idx, result in enumerate(results, 1):
        annotation = export_result_type(result["ast"])
        lines.extend(
            [
                "",
                "Theorem "
                f"concrete_registered_truth_condition_route_example_{idx}_direct_atomic_sound : "
                f"AtomicClosureTruth {annotation} example_{idx}.",
                "Proof.",
                "  apply concrete_registered_truth_condition_route_direct_spec_sound.",
                "  exact (example_"
                f"{idx}_concrete_truth_instance",
                "    (concrete_registered_route_direct_examples",
                "      concrete_registered_truth_condition_route)).",
                "Qed.",
                "",
                "Theorem "
                f"concrete_registered_truth_condition_route_example_{idx}_evidence_atomic_sound : "
                f"AtomicClosureTruth {annotation} example_{idx}.",
                "Proof.",
                "  apply concrete_registered_truth_condition_route_evidence_spec_sound.",
                "  exact (example_"
                f"{idx}_evidence_backed_truth_instance",
                "    (concrete_registered_route_evidence_examples",
                "      concrete_registered_truth_condition_route)).",
                "Qed.",
                "",
                "Theorem "
                f"concrete_registered_truth_condition_route_example_{idx}_kernel_atomic_sound : "
                f"AtomicClosureTruth {annotation} example_{idx}.",
                "Proof.",
                "  apply concrete_registered_truth_condition_route_kernel_spec_sound.",
                "  exact (example_"
                f"{idx}_kernel_truth_instance",
                "    (concrete_registered_route_kernel_examples",
                "      concrete_registered_truth_condition_route)).",
                "Qed.",
            ]
        )
    return lines


def concrete_registered_truth_condition_route_example_agreement_lines(
    results: list[dict[str, Any]],
    target: str,
) -> list[str]:
    """Package per-example agreement among the concrete registered routes."""

    if target == "lean":
        lines = [
            "structure ConcreteRegisteredTruthConditionRouteExampleAgreement : "
            "Type where",
            "  concrete_registered_route_agreement_route : "
            "ConcreteRegisteredTruthConditionRoute",
        ]
        for idx, result in enumerate(results, 1):
            annotation = export_result_type(result["ast"])
            lines.extend(
                [
                    f"  concrete_registered_route_agreement_example_{idx}_direct_atomic : "
                    f"AtomicClosureTruth {annotation} example_{idx}",
                    f"  concrete_registered_route_agreement_example_{idx}_evidence_atomic : "
                    f"AtomicClosureTruth {annotation} example_{idx}",
                    f"  concrete_registered_route_agreement_example_{idx}_kernel_atomic : "
                    f"AtomicClosureTruth {annotation} example_{idx}",
                ]
            )
        lines.extend(
            [
                "",
                "def concrete_registered_truth_condition_route_example_agreement : "
                "ConcreteRegisteredTruthConditionRouteExampleAgreement := {",
                "  concrete_registered_route_agreement_route := "
                "concrete_registered_truth_condition_route,",
            ]
        )
        for idx in range(1, len(results) + 1):
            suffix = "," if idx < len(results) else ""
            lines.extend(
                [
                    f"  concrete_registered_route_agreement_example_{idx}_direct_atomic := "
                    f"concrete_registered_truth_condition_route_example_{idx}_direct_atomic_sound,",
                    f"  concrete_registered_route_agreement_example_{idx}_evidence_atomic := "
                    f"concrete_registered_truth_condition_route_example_{idx}_evidence_atomic_sound,",
                    f"  concrete_registered_route_agreement_example_{idx}_kernel_atomic := "
                    f"concrete_registered_truth_condition_route_example_{idx}_kernel_atomic_sound"
                    f"{suffix}",
                ]
            )
        lines.extend(
            [
                "}",
                "",
                "theorem concrete_registered_truth_condition_route_example_agreement_exists :",
                "    Exists (fun A : "
                "ConcreteRegisteredTruthConditionRouteExampleAgreement => "
                "A = concrete_registered_truth_condition_route_example_agreement) := by",
                "  exact Exists.intro "
                "concrete_registered_truth_condition_route_example_agreement rfl",
                "",
                "theorem "
                "concrete_registered_truth_condition_route_example_agreement_route_matches :",
                "    concrete_registered_truth_condition_route_example_agreement."
                "concrete_registered_route_agreement_route = "
                "concrete_registered_truth_condition_route := by",
                "  rfl",
            ]
        )
        for idx, result in enumerate(results, 1):
            annotation = export_result_type(result["ast"])
            lines.extend(
                [
                    "",
                    "theorem "
                    f"concrete_registered_truth_condition_route_example_{idx}_agreement_direct_atomic_sound : "
                    f"AtomicClosureTruth {annotation} example_{idx} := by",
                    "  exact "
                    "concrete_registered_truth_condition_route_example_agreement."
                    f"concrete_registered_route_agreement_example_{idx}_direct_atomic",
                    "",
                    "theorem "
                    f"concrete_registered_truth_condition_route_example_{idx}_agreement_evidence_atomic_sound : "
                    f"AtomicClosureTruth {annotation} example_{idx} := by",
                    "  exact "
                    "concrete_registered_truth_condition_route_example_agreement."
                    f"concrete_registered_route_agreement_example_{idx}_evidence_atomic",
                    "",
                    "theorem "
                    f"concrete_registered_truth_condition_route_example_{idx}_agreement_kernel_atomic_sound : "
                    f"AtomicClosureTruth {annotation} example_{idx} := by",
                    "  exact "
                    "concrete_registered_truth_condition_route_example_agreement."
                    f"concrete_registered_route_agreement_example_{idx}_kernel_atomic",
                ]
            )
        return lines

    lines = [
        "Record ConcreteRegisteredTruthConditionRouteExampleAgreement : Type := {",
        "  concrete_registered_route_agreement_route : "
        "ConcreteRegisteredTruthConditionRoute;",
    ]
    for idx, result in enumerate(results, 1):
        annotation = export_result_type(result["ast"])
        suffix = ";" if idx < len(results) else ""
        lines.extend(
            [
                f"  concrete_registered_route_agreement_example_{idx}_direct_atomic :",
                f"      AtomicClosureTruth {annotation} example_{idx};",
                f"  concrete_registered_route_agreement_example_{idx}_evidence_atomic :",
                f"      AtomicClosureTruth {annotation} example_{idx};",
                f"  concrete_registered_route_agreement_example_{idx}_kernel_atomic :",
                f"      AtomicClosureTruth {annotation} example_{idx}{suffix}",
            ]
        )
    lines.extend(
        [
            "}.",
            "",
            "Definition concrete_registered_truth_condition_route_example_agreement :",
            "  ConcreteRegisteredTruthConditionRouteExampleAgreement := {|",
            "  concrete_registered_route_agreement_route := "
            "concrete_registered_truth_condition_route;",
        ]
    )
    for idx in range(1, len(results) + 1):
        suffix = ";" if idx < len(results) else ""
        lines.extend(
            [
                f"  concrete_registered_route_agreement_example_{idx}_direct_atomic := "
                f"concrete_registered_truth_condition_route_example_{idx}_direct_atomic_sound;",
                f"  concrete_registered_route_agreement_example_{idx}_evidence_atomic := "
                f"concrete_registered_truth_condition_route_example_{idx}_evidence_atomic_sound;",
                f"  concrete_registered_route_agreement_example_{idx}_kernel_atomic := "
                f"concrete_registered_truth_condition_route_example_{idx}_kernel_atomic_sound"
                f"{suffix}",
            ]
        )
    lines.extend(
        [
            "|}.",
            "",
            "Theorem concrete_registered_truth_condition_route_example_agreement_exists :",
            "  exists A : ConcreteRegisteredTruthConditionRouteExampleAgreement,",
            "    A = concrete_registered_truth_condition_route_example_agreement.",
            "Proof.",
            "  exists concrete_registered_truth_condition_route_example_agreement.",
            "  reflexivity.",
            "Qed.",
            "",
            "Theorem "
            "concrete_registered_truth_condition_route_example_agreement_route_matches :",
            "  concrete_registered_route_agreement_route",
            "    concrete_registered_truth_condition_route_example_agreement =",
            "  concrete_registered_truth_condition_route.",
            "Proof. reflexivity. Qed.",
        ]
    )
    for idx, result in enumerate(results, 1):
        annotation = export_result_type(result["ast"])
        lines.extend(
            [
                "",
                "Theorem "
                f"concrete_registered_truth_condition_route_example_{idx}_agreement_direct_atomic_sound : "
                f"AtomicClosureTruth {annotation} example_{idx}.",
                "Proof.",
                "  exact (concrete_registered_route_agreement_example_"
                f"{idx}_direct_atomic "
                "concrete_registered_truth_condition_route_example_agreement).",
                "Qed.",
                "",
                "Theorem "
                f"concrete_registered_truth_condition_route_example_{idx}_agreement_evidence_atomic_sound : "
                f"AtomicClosureTruth {annotation} example_{idx}.",
                "Proof.",
                "  exact (concrete_registered_route_agreement_example_"
                f"{idx}_evidence_atomic "
                "concrete_registered_truth_condition_route_example_agreement).",
                "Qed.",
                "",
                "Theorem "
                f"concrete_registered_truth_condition_route_example_{idx}_agreement_kernel_atomic_sound : "
                f"AtomicClosureTruth {annotation} example_{idx}.",
                "Proof.",
                "  exact (concrete_registered_route_agreement_example_"
                f"{idx}_kernel_atomic "
                "concrete_registered_truth_condition_route_example_agreement).",
                "Qed.",
            ]
        )
    return lines


def independent_registered_truth_condition_source_lines(
    results: list[dict[str, Any]],
    target: str,
) -> list[str]:
    """Expose a named source boundary for the finite registered truth route."""

    if target == "lean":
        lines = [
            "structure IndependentRegisteredTruthConditionSources : Type where",
            "  independent_registered_truth_condition_route : "
            "ConcreteRegisteredTruthConditionRoute",
            "  independent_registered_truth_condition_agreement : "
            "ConcreteRegisteredTruthConditionRouteExampleAgreement",
            "  independent_registered_truth_condition_spec : "
            "FullyRegisteredTruthConditionSpec",
            "  independent_registered_truth_condition_spec_route_eq :",
            "      independent_registered_truth_condition_spec =",
            "        independent_registered_truth_condition_route."
            "concrete_registered_route_direct_spec",
            "  independent_registered_truth_condition_agreement_route_eq :",
            "      independent_registered_truth_condition_agreement."
            "concrete_registered_route_agreement_route =",
            "        independent_registered_truth_condition_route",
            "  independent_registered_truth_condition_examples : "
            "ConcreteRegisteredExampleTruthInstances",
            "",
            "def independent_registered_truth_condition_sources : "
            "IndependentRegisteredTruthConditionSources := {",
            "  independent_registered_truth_condition_route := "
            "concrete_registered_truth_condition_route,",
            "  independent_registered_truth_condition_agreement := "
            "concrete_registered_truth_condition_route_example_agreement,",
            "  independent_registered_truth_condition_spec := "
            "concrete_registered_truth_conditions,",
            "  independent_registered_truth_condition_spec_route_eq := rfl,",
            "  independent_registered_truth_condition_agreement_route_eq := rfl,",
            "  independent_registered_truth_condition_examples := "
            "concrete_registered_example_truth_instances",
            "}",
            "",
            "theorem independent_registered_truth_condition_sources_exist :",
            "    Exists (fun S : IndependentRegisteredTruthConditionSources => "
            "S = independent_registered_truth_condition_sources) := by",
            "  exact Exists.intro independent_registered_truth_condition_sources rfl",
            "",
            "theorem "
            "independent_registered_truth_condition_sources_spec_matches_route :",
            "    independent_registered_truth_condition_sources."
            "independent_registered_truth_condition_spec =",
            "      independent_registered_truth_condition_sources."
            "independent_registered_truth_condition_route."
            "concrete_registered_route_direct_spec := by",
            "  exact independent_registered_truth_condition_sources."
            "independent_registered_truth_condition_spec_route_eq",
            "",
            "theorem "
            "independent_registered_truth_condition_sources_agreement_matches_route :",
            "    independent_registered_truth_condition_sources."
            "independent_registered_truth_condition_agreement."
            "concrete_registered_route_agreement_route =",
            "      independent_registered_truth_condition_sources."
            "independent_registered_truth_condition_route := by",
            "  exact independent_registered_truth_condition_sources."
            "independent_registered_truth_condition_agreement_route_eq",
            "",
            "theorem independent_registered_truth_condition_sources_spec_sound :",
            "    (A : Type) -> (term : A) -> "
            "independent_registered_truth_condition_sources."
            "independent_registered_truth_condition_spec."
            "fully_registered_truth_denotes A term -> "
            "AtomicClosureTruth A term := by",
            "  intro A term h",
            "  apply concrete_registered_truth_condition_route_direct_spec_sound",
            "  exact h",
        ]
        for idx, result in enumerate(results, 1):
            annotation = export_result_type(result["ast"])
            lines.extend(
                [
                    "",
                    "theorem "
                    f"independent_registered_truth_condition_sources_example_{idx}_atomic_sound : "
                    f"AtomicClosureTruth {annotation} example_{idx} := by",
                    "  exact independent_registered_truth_condition_sources."
                    "independent_registered_truth_condition_agreement."
                    f"concrete_registered_route_agreement_example_{idx}_direct_atomic",
                ]
            )
        return lines

    lines = [
        "Record IndependentRegisteredTruthConditionSources : Type := {",
        "  independent_registered_truth_condition_route : "
        "ConcreteRegisteredTruthConditionRoute;",
        "  independent_registered_truth_condition_agreement : "
        "ConcreteRegisteredTruthConditionRouteExampleAgreement;",
        "  independent_registered_truth_condition_spec : "
        "FullyRegisteredTruthConditionSpec;",
        "  independent_registered_truth_condition_spec_route_eq :",
        "      independent_registered_truth_condition_spec =",
        "        concrete_registered_route_direct_spec",
        "          independent_registered_truth_condition_route;",
        "  independent_registered_truth_condition_agreement_route_eq :",
        "      concrete_registered_route_agreement_route",
        "        independent_registered_truth_condition_agreement =",
        "        independent_registered_truth_condition_route;",
        "  independent_registered_truth_condition_examples : "
        "ConcreteRegisteredExampleTruthInstances",
        "}.",
        "",
        "Definition independent_registered_truth_condition_sources :",
        "  IndependentRegisteredTruthConditionSources := {|",
        "  independent_registered_truth_condition_route := "
        "concrete_registered_truth_condition_route;",
        "  independent_registered_truth_condition_agreement := "
        "concrete_registered_truth_condition_route_example_agreement;",
        "  independent_registered_truth_condition_spec := "
        "concrete_registered_truth_conditions;",
        "  independent_registered_truth_condition_spec_route_eq := eq_refl;",
        "  independent_registered_truth_condition_agreement_route_eq := eq_refl;",
        "  independent_registered_truth_condition_examples := "
        "concrete_registered_example_truth_instances",
        "|}.",
        "",
        "Theorem independent_registered_truth_condition_sources_exist :",
        "  exists S : IndependentRegisteredTruthConditionSources,",
        "    S = independent_registered_truth_condition_sources.",
        "Proof.",
        "  exists independent_registered_truth_condition_sources. reflexivity.",
        "Qed.",
        "",
        "Theorem "
        "independent_registered_truth_condition_sources_spec_matches_route :",
        "  independent_registered_truth_condition_spec",
        "    independent_registered_truth_condition_sources =",
        "  concrete_registered_route_direct_spec",
        "    (independent_registered_truth_condition_route",
        "      independent_registered_truth_condition_sources).",
        "Proof.",
        "  exact (independent_registered_truth_condition_spec_route_eq",
        "    independent_registered_truth_condition_sources).",
        "Qed.",
        "",
        "Theorem "
        "independent_registered_truth_condition_sources_agreement_matches_route :",
        "  concrete_registered_route_agreement_route",
        "    (independent_registered_truth_condition_agreement",
        "      independent_registered_truth_condition_sources) =",
        "  independent_registered_truth_condition_route",
        "    independent_registered_truth_condition_sources.",
        "Proof.",
        "  exact (independent_registered_truth_condition_agreement_route_eq",
        "    independent_registered_truth_condition_sources).",
        "Qed.",
        "",
        "Theorem independent_registered_truth_condition_sources_spec_sound :",
        "  forall A : Type, forall term : A,",
        "    fully_registered_truth_denotes",
        "      (independent_registered_truth_condition_spec",
        "        independent_registered_truth_condition_sources) A term ->",
        "    AtomicClosureTruth A term.",
        "Proof.",
        "  intros A term H.",
        "  apply concrete_registered_truth_condition_route_direct_spec_sound.",
        "  exact H.",
        "Qed.",
    ]
    for idx, result in enumerate(results, 1):
        annotation = export_result_type(result["ast"])
        lines.extend(
            [
                "",
                "Theorem "
                f"independent_registered_truth_condition_sources_example_{idx}_atomic_sound : "
                f"AtomicClosureTruth {annotation} example_{idx}.",
                "Proof.",
                "  exact (concrete_registered_route_agreement_example_"
                f"{idx}_direct_atomic",
                "    (independent_registered_truth_condition_agreement",
                "      independent_registered_truth_condition_sources)).",
                "Qed.",
            ]
        )
    return lines


def independent_registered_truth_condition_clause_instance_lines(
    declarations: dict[str, Any],
    results: list[dict[str, Any]],
    target: str,
) -> list[str]:
    """Project constructor-level instances from the independent source spec."""

    if target == "lean":
        lines = [
            "structure IndependentRegisteredTruthConditionClauseInstances : Type where",
            "  independent_registered_clause_source : "
            "IndependentRegisteredTruthConditionSources",
            "  independent_registered_clause_spec : "
            "FullyRegisteredTruthConditionSpec",
            "  independent_registered_clause_spec_eq :",
            "      independent_registered_clause_spec =",
            "        independent_registered_clause_source."
            "independent_registered_truth_condition_spec",
            "",
            "def independent_registered_truth_condition_clause_instances : "
            "IndependentRegisteredTruthConditionClauseInstances := {",
            "  independent_registered_clause_source := "
            "independent_registered_truth_condition_sources,",
            "  independent_registered_clause_spec := "
            "independent_registered_truth_condition_sources."
            "independent_registered_truth_condition_spec,",
            "  independent_registered_clause_spec_eq := rfl",
            "}",
            "",
            "theorem independent_registered_truth_condition_clause_instances_exists :",
            "    Exists (fun C : "
            "IndependentRegisteredTruthConditionClauseInstances => "
            "C = independent_registered_truth_condition_clause_instances) := by",
            "  exact Exists.intro "
            "independent_registered_truth_condition_clause_instances rfl",
            "",
            "theorem "
            "independent_registered_truth_condition_clause_spec_matches_source :",
            "    independent_registered_truth_condition_clause_instances."
            "independent_registered_clause_spec =",
            "      independent_registered_truth_condition_clause_instances."
            "independent_registered_clause_source."
            "independent_registered_truth_condition_spec := by",
            "  exact independent_registered_truth_condition_clause_instances."
            "independent_registered_clause_spec_eq",
            "",
            "theorem "
            "independent_registered_truth_condition_clause_lexical_application_instance :",
            "    (A : Type) -> (term : A) -> "
            "RegisteredLexicalApplicationTruth A term -> "
            "independent_registered_truth_condition_clause_instances."
            "independent_registered_clause_spec."
            "fully_registered_truth_denotes A term := by",
            "  intro A term h",
            "  exact independent_registered_truth_condition_clause_instances."
            "independent_registered_clause_spec."
            "fully_registered_truth_lexical_application A term h",
        ]
        for type_name in declarations["types"]:
            lines.extend(
                [
                    "",
                    "theorem "
                    f"independent_registered_truth_condition_clause_sigma_{type_name}_instance :",
                    f"    (P : {type_name} -> Prop) -> "
                    f"((x : {type_name}) -> "
                    "independent_registered_truth_condition_clause_instances."
                    "independent_registered_clause_spec."
                    "fully_registered_truth_denotes Prop (P x)) -> "
                    "independent_registered_truth_condition_clause_instances."
                    "independent_registered_clause_spec."
                    "fully_registered_truth_denotes Prop "
                    f"(Exists fun x : {type_name} => P x) := by",
                    "  intro P h",
                    "  exact independent_registered_truth_condition_clause_instances."
                    "independent_registered_clause_spec."
                    f"fully_registered_truth_sigma_{type_name} P h",
                ]
            )
        clause_specs = [
            (
                "repeat",
                "(n : Nat) -> (body : PropT) -> ",
                "n body ",
                "PropT body",
                "PropT (repeat n body)",
            ),
            (
                "at_T",
                "(marker : Entity) -> (body : PropT) -> ",
                "marker body ",
                "PropT body",
                "PropT (at_T marker body)",
            ),
            (
                "during_T",
                "(marker : Entity) -> (body : PropT) -> ",
                "marker body ",
                "PropT body",
                "PropT (during_T marker body)",
            ),
            (
                "before_T",
                "(marker : Entity) -> (body : PropT) -> ",
                "marker body ",
                "PropT body",
                "PropT (before_T marker body)",
            ),
            (
                "after_T",
                "(marker : Entity) -> (body : PropT) -> ",
                "marker body ",
                "PropT body",
                "PropT (after_T marker body)",
            ),
            (
                "until_T",
                "(marker : Entity) -> (body : PropT) -> ",
                "marker body ",
                "PropT body",
                "PropT (until_T marker body)",
            ),
            (
                "since_T",
                "(marker : Entity) -> (body : PropT) -> ",
                "marker body ",
                "PropT body",
                "PropT (since_T marker body)",
            ),
            (
                "not_T",
                "(body : PropT) -> ",
                "body ",
                "PropT body",
                "PropT (not_T body)",
            ),
        ]
        for name, binders, args, premise, conclusion in clause_specs:
            lines.extend(
                [
                    "",
                    "theorem "
                    f"independent_registered_truth_condition_clause_{name}_instance :",
                    f"    {binders}"
                    "independent_registered_truth_condition_clause_instances."
                    "independent_registered_clause_spec."
                    f"fully_registered_truth_denotes {premise} -> "
                    "independent_registered_truth_condition_clause_instances."
                    "independent_registered_clause_spec."
                    f"fully_registered_truth_denotes {conclusion} := by",
                    "  intro " + " ".join(
                        token.split(" : ")[0].strip("()")
                        for token in binders.split(" -> ")[:-1]
                        if token
                    ) + " h",
                    "  exact independent_registered_truth_condition_clause_instances."
                    "independent_registered_clause_spec."
                    f"fully_registered_truth_{name} {args}h",
                ]
            )
        lines.extend(
            [
                "",
                "theorem "
                "independent_registered_truth_condition_clause_transition_instance :",
                "    (theme : Entity) -> (scale : StateScale) -> "
                "(source : State) -> (target : State) -> "
                "RegisteredStateTransitionTruth theme scale source target -> "
                "independent_registered_truth_condition_clause_instances."
                "independent_registered_clause_spec."
                "fully_registered_truth_denotes TransitionT "
                "(Transition theme scale source target) := by",
                "  intro theme scale source target h",
                "  exact independent_registered_truth_condition_clause_instances."
                "independent_registered_clause_spec."
                "fully_registered_truth_transition theme scale source target h",
                "",
                "theorem "
                "independent_registered_truth_condition_clause_cause_instance :",
                "    (causer : Entity) -> (effect : TransitionT) -> "
                "independent_registered_truth_condition_clause_instances."
                "independent_registered_clause_spec."
                "fully_registered_truth_denotes TransitionT effect -> "
                "independent_registered_truth_condition_clause_instances."
                "independent_registered_clause_spec."
                "fully_registered_truth_denotes PropT (Cause causer effect) := by",
                "  intro causer effect h",
                "  exact independent_registered_truth_condition_clause_instances."
                "independent_registered_clause_spec."
                "fully_registered_truth_cause causer effect h",
                "",
                "theorem "
                "independent_registered_truth_condition_clause_spec_sound :",
                "    (A : Type) -> (term : A) -> "
                "independent_registered_truth_condition_clause_instances."
                "independent_registered_clause_spec."
                "fully_registered_truth_denotes A term -> "
                "AtomicClosureTruth A term := by",
                "  intro A term h",
                "  apply independent_registered_truth_condition_sources_spec_sound",
                "  exact h",
            ]
        )
        for idx, result in enumerate(results, 1):
            annotation = export_result_type(result["ast"])
            lines.extend(
                [
                    "",
                    "theorem "
                    f"independent_registered_truth_condition_clause_example_{idx}_atomic_sound : "
                    f"AtomicClosureTruth {annotation} example_{idx} := by",
                    "  apply independent_registered_truth_condition_clause_spec_sound",
                    "  exact independent_registered_truth_condition_clause_instances."
                    "independent_registered_clause_source."
                    "independent_registered_truth_condition_examples."
                    f"example_{idx}_concrete_truth_instance",
                ]
            )
        return lines

    lines = [
        "Record IndependentRegisteredTruthConditionClauseInstances : Type := {",
        "  independent_registered_clause_source : "
        "IndependentRegisteredTruthConditionSources;",
        "  independent_registered_clause_spec : FullyRegisteredTruthConditionSpec;",
        "  independent_registered_clause_spec_eq :",
        "      independent_registered_clause_spec =",
        "        independent_registered_truth_condition_spec",
        "          independent_registered_clause_source",
        "}.",
        "",
        "Definition independent_registered_truth_condition_clause_instances :",
        "  IndependentRegisteredTruthConditionClauseInstances := {|",
        "  independent_registered_clause_source := "
        "independent_registered_truth_condition_sources;",
        "  independent_registered_clause_spec := "
        "independent_registered_truth_condition_spec",
        "    independent_registered_truth_condition_sources;",
        "  independent_registered_clause_spec_eq := eq_refl",
        "|}.",
        "",
        "Theorem independent_registered_truth_condition_clause_instances_exists :",
        "  exists C : IndependentRegisteredTruthConditionClauseInstances,",
        "    C = independent_registered_truth_condition_clause_instances.",
        "Proof.",
        "  exists independent_registered_truth_condition_clause_instances.",
        "  reflexivity.",
        "Qed.",
        "",
        "Theorem independent_registered_truth_condition_clause_spec_matches_source :",
        "  independent_registered_clause_spec",
        "    independent_registered_truth_condition_clause_instances =",
        "  independent_registered_truth_condition_spec",
        "    (independent_registered_clause_source",
        "      independent_registered_truth_condition_clause_instances).",
        "Proof.",
        "  exact (independent_registered_clause_spec_eq",
        "    independent_registered_truth_condition_clause_instances).",
        "Qed.",
        "",
        "Theorem "
        "independent_registered_truth_condition_clause_lexical_application_instance :",
        "  forall A : Type, forall term : A,",
        "    RegisteredLexicalApplicationTruth A term ->",
        "    fully_registered_truth_denotes",
        "      (independent_registered_clause_spec",
        "        independent_registered_truth_condition_clause_instances) A term.",
        "Proof.",
        "  intros A term H.",
        "  exact (fully_registered_truth_lexical_application",
        "    (independent_registered_clause_spec",
        "      independent_registered_truth_condition_clause_instances) A term H).",
        "Qed.",
    ]
    for type_name in declarations["types"]:
        lines.extend(
            [
                "",
                "Theorem "
                f"independent_registered_truth_condition_clause_sigma_{type_name}_instance :",
                f"  forall P : {type_name} -> Prop,",
                f"    (forall x : {type_name},",
                "      fully_registered_truth_denotes",
                "        (independent_registered_clause_spec",
                "          independent_registered_truth_condition_clause_instances)",
                "        Prop (P x)) ->",
                "    fully_registered_truth_denotes",
                "      (independent_registered_clause_spec",
                "        independent_registered_truth_condition_clause_instances)",
                f"      Prop (exists x : {type_name}, P x).",
                "Proof.",
                "  intros P H.",
                f"  exact (fully_registered_truth_sigma_{type_name}",
                "    (independent_registered_clause_spec",
                "      independent_registered_truth_condition_clause_instances)",
                "    P H).",
                "Qed.",
            ]
        )
    clause_specs = [
        (
            "repeat",
            "forall n : nat, forall body : PropT,",
            "n body",
            "PropT body",
            "PropT (repeat n body)",
            "intros n body H.",
        ),
        (
            "at_T",
            "forall marker : Entity, forall body : PropT,",
            "marker body",
            "PropT body",
            "PropT (at_T marker body)",
            "intros marker body H.",
        ),
        (
            "during_T",
            "forall marker : Entity, forall body : PropT,",
            "marker body",
            "PropT body",
            "PropT (during_T marker body)",
            "intros marker body H.",
        ),
        (
            "before_T",
            "forall marker : Entity, forall body : PropT,",
            "marker body",
            "PropT body",
            "PropT (before_T marker body)",
            "intros marker body H.",
        ),
        (
            "after_T",
            "forall marker : Entity, forall body : PropT,",
            "marker body",
            "PropT body",
            "PropT (after_T marker body)",
            "intros marker body H.",
        ),
        (
            "until_T",
            "forall marker : Entity, forall body : PropT,",
            "marker body",
            "PropT body",
            "PropT (until_T marker body)",
            "intros marker body H.",
        ),
        (
            "since_T",
            "forall marker : Entity, forall body : PropT,",
            "marker body",
            "PropT body",
            "PropT (since_T marker body)",
            "intros marker body H.",
        ),
        (
            "not_T",
            "forall body : PropT,",
            "body",
            "PropT body",
            "PropT (not_T body)",
            "intros body H.",
        ),
    ]
    for name, binders, args, premise, conclusion, intro_line in clause_specs:
        lines.extend(
            [
                "",
                "Theorem "
                f"independent_registered_truth_condition_clause_{name}_instance :",
                f"  {binders}",
                "    fully_registered_truth_denotes",
                "      (independent_registered_clause_spec",
                "        independent_registered_truth_condition_clause_instances)",
                f"      {premise} ->",
                "    fully_registered_truth_denotes",
                "      (independent_registered_clause_spec",
                "        independent_registered_truth_condition_clause_instances)",
                f"      {conclusion}.",
                "Proof.",
                f"  {intro_line}",
                f"  exact (fully_registered_truth_{name}",
                "    (independent_registered_clause_spec",
                "      independent_registered_truth_condition_clause_instances)",
                f"    {args} H).",
                "Qed.",
            ]
        )
    lines.extend(
        [
            "",
            "Theorem "
            "independent_registered_truth_condition_clause_transition_instance :",
            "  forall theme : Entity, forall scale : StateScale,",
            "  forall source : State, forall target : State,",
            "    RegisteredStateTransitionTruth theme scale source target ->",
            "    fully_registered_truth_denotes",
            "      (independent_registered_clause_spec",
            "        independent_registered_truth_condition_clause_instances)",
            "      TransitionT (Transition theme scale source target).",
            "Proof.",
            "  intros theme scale source target H.",
            "  exact (fully_registered_truth_transition",
            "    (independent_registered_clause_spec",
            "      independent_registered_truth_condition_clause_instances)",
            "    theme scale source target H).",
            "Qed.",
            "",
            "Theorem "
            "independent_registered_truth_condition_clause_cause_instance :",
            "  forall causer : Entity, forall effect : TransitionT,",
            "    fully_registered_truth_denotes",
            "      (independent_registered_clause_spec",
            "        independent_registered_truth_condition_clause_instances)",
            "      TransitionT effect ->",
            "    fully_registered_truth_denotes",
            "      (independent_registered_clause_spec",
            "        independent_registered_truth_condition_clause_instances)",
            "      PropT (Cause causer effect).",
            "Proof.",
            "  intros causer effect H.",
            "  exact (fully_registered_truth_cause",
            "    (independent_registered_clause_spec",
            "      independent_registered_truth_condition_clause_instances)",
            "    causer effect H).",
            "Qed.",
            "",
            "Theorem independent_registered_truth_condition_clause_spec_sound :",
            "  forall A : Type, forall term : A,",
            "    fully_registered_truth_denotes",
            "      (independent_registered_clause_spec",
            "        independent_registered_truth_condition_clause_instances) A term ->",
            "    AtomicClosureTruth A term.",
            "Proof.",
            "  intros A term H.",
            "  apply independent_registered_truth_condition_sources_spec_sound.",
            "  exact H.",
            "Qed.",
        ]
    )
    for idx, result in enumerate(results, 1):
        annotation = export_result_type(result["ast"])
        lines.extend(
            [
                "",
                "Theorem "
                f"independent_registered_truth_condition_clause_example_{idx}_atomic_sound : "
                f"AtomicClosureTruth {annotation} example_{idx}.",
                "Proof.",
                "  apply independent_registered_truth_condition_clause_spec_sound.",
                "  exact (example_"
                f"{idx}_concrete_truth_instance",
                "    (independent_registered_truth_condition_examples",
                "      (independent_registered_clause_source",
                "        independent_registered_truth_condition_clause_instances))).",
                "Qed.",
            ]
        )
    return lines


def independent_registered_truth_condition_clause_coverage_lines(
    declarations: dict[str, Any],
    results: list[dict[str, Any]],
    target: str,
) -> list[str]:
    """Package all registered independent clause projections as one ledger."""

    time_and_polarity_clauses = [
        (
            "repeat",
            "(n : Nat) -> (body : PropT) -> ",
            "forall n : nat, forall body : PropT,",
            "PropT body",
            "PropT (repeat n body)",
        ),
        (
            "at_T",
            "(marker : Entity) -> (body : PropT) -> ",
            "forall marker : Entity, forall body : PropT,",
            "PropT body",
            "PropT (at_T marker body)",
        ),
        (
            "during_T",
            "(marker : Entity) -> (body : PropT) -> ",
            "forall marker : Entity, forall body : PropT,",
            "PropT body",
            "PropT (during_T marker body)",
        ),
        (
            "before_T",
            "(marker : Entity) -> (body : PropT) -> ",
            "forall marker : Entity, forall body : PropT,",
            "PropT body",
            "PropT (before_T marker body)",
        ),
        (
            "after_T",
            "(marker : Entity) -> (body : PropT) -> ",
            "forall marker : Entity, forall body : PropT,",
            "PropT body",
            "PropT (after_T marker body)",
        ),
        (
            "until_T",
            "(marker : Entity) -> (body : PropT) -> ",
            "forall marker : Entity, forall body : PropT,",
            "PropT body",
            "PropT (until_T marker body)",
        ),
        (
            "since_T",
            "(marker : Entity) -> (body : PropT) -> ",
            "forall marker : Entity, forall body : PropT,",
            "PropT body",
            "PropT (since_T marker body)",
        ),
        (
            "not_T",
            "(body : PropT) -> ",
            "forall body : PropT,",
            "PropT body",
            "PropT (not_T body)",
        ),
    ]

    if target == "lean":
        lines = [
            "structure IndependentRegisteredTruthConditionClauseCoverage : Type where",
            "  independent_registered_clause_coverage_instances :",
            "      IndependentRegisteredTruthConditionClauseInstances",
            "  independent_registered_clause_coverage_instances_eq :",
            "      independent_registered_clause_coverage_instances =",
            "        independent_registered_truth_condition_clause_instances",
            "  independent_registered_clause_coverage_lexical_application :",
            "      (A : Type) -> (term : A) ->",
            "      RegisteredLexicalApplicationTruth A term ->",
            "      independent_registered_truth_condition_clause_instances.",
            "      independent_registered_clause_spec.",
            "      fully_registered_truth_denotes A term",
        ]
        for type_name in declarations["types"]:
            lines.extend(
                [
                    f"  independent_registered_clause_coverage_sigma_{type_name} :",
                    f"      (P : {type_name} -> Prop) ->",
                    f"      ((x : {type_name}) ->",
                    "        independent_registered_truth_condition_clause_instances.",
                    "        independent_registered_clause_spec.",
                    "        fully_registered_truth_denotes Prop (P x)) ->",
                    "      independent_registered_truth_condition_clause_instances.",
                    "      independent_registered_clause_spec.",
                    "      fully_registered_truth_denotes Prop "
                    f"(Exists fun x : {type_name} => P x)",
                ]
            )
        for name, lean_binders, _coq_binders, premise, conclusion in (
            time_and_polarity_clauses
        ):
            lines.extend(
                [
                    f"  independent_registered_clause_coverage_{name} :",
                    f"      {lean_binders}"
                    "independent_registered_truth_condition_clause_instances.",
                    "      independent_registered_clause_spec.",
                    f"      fully_registered_truth_denotes {premise} ->",
                    "      independent_registered_truth_condition_clause_instances.",
                    "      independent_registered_clause_spec.",
                    f"      fully_registered_truth_denotes {conclusion}",
                ]
            )
        lines.extend(
            [
                "  independent_registered_clause_coverage_transition :",
                "      (theme : Entity) -> (scale : StateScale) ->",
                "      (source : State) -> (target : State) ->",
                "      RegisteredStateTransitionTruth theme scale source target ->",
                "      independent_registered_truth_condition_clause_instances.",
                "      independent_registered_clause_spec.",
                "      fully_registered_truth_denotes TransitionT "
                "(Transition theme scale source target)",
                "  independent_registered_clause_coverage_cause :",
                "      (causer : Entity) -> (effect : TransitionT) ->",
                "      independent_registered_truth_condition_clause_instances.",
                "      independent_registered_clause_spec.",
                "      fully_registered_truth_denotes TransitionT effect ->",
                "      independent_registered_truth_condition_clause_instances.",
                "      independent_registered_clause_spec.",
                "      fully_registered_truth_denotes PropT (Cause causer effect)",
                "  independent_registered_clause_coverage_spec_sound :",
                "      (A : Type) -> (term : A) ->",
                "      independent_registered_truth_condition_clause_instances.",
                "      independent_registered_clause_spec.",
                "      fully_registered_truth_denotes A term ->",
                "      AtomicClosureTruth A term",
            ]
        )
        for idx, result in enumerate(results, 1):
            annotation = export_result_type(result["ast"])
            lines.extend(
                [
                    f"  independent_registered_clause_coverage_example_{idx} :",
                    f"      AtomicClosureTruth {annotation} example_{idx}",
                ]
            )

        assignments = [
            (
                "independent_registered_clause_coverage_instances",
                "independent_registered_truth_condition_clause_instances",
            ),
            ("independent_registered_clause_coverage_instances_eq", "rfl"),
            (
                "independent_registered_clause_coverage_lexical_application",
                "independent_registered_truth_condition_clause_lexical_application_instance",
            ),
        ]
        assignments.extend(
            (
                f"independent_registered_clause_coverage_sigma_{type_name}",
                f"independent_registered_truth_condition_clause_sigma_{type_name}_instance",
            )
            for type_name in declarations["types"]
        )
        assignments.extend(
            (
                f"independent_registered_clause_coverage_{name}",
                f"independent_registered_truth_condition_clause_{name}_instance",
            )
            for name, _lean_binders, _coq_binders, _premise, _conclusion in (
                time_and_polarity_clauses
            )
        )
        assignments.extend(
            [
                (
                    "independent_registered_clause_coverage_transition",
                    "independent_registered_truth_condition_clause_transition_instance",
                ),
                (
                    "independent_registered_clause_coverage_cause",
                    "independent_registered_truth_condition_clause_cause_instance",
                ),
                (
                    "independent_registered_clause_coverage_spec_sound",
                    "independent_registered_truth_condition_clause_spec_sound",
                ),
            ]
        )
        assignments.extend(
            (
                f"independent_registered_clause_coverage_example_{idx}",
                f"independent_registered_truth_condition_clause_example_{idx}_atomic_sound",
            )
            for idx in range(1, len(results) + 1)
        )

        lines.extend(
            [
                "",
                "def independent_registered_truth_condition_clause_coverage :",
                "    IndependentRegisteredTruthConditionClauseCoverage := {",
            ]
        )
        for idx, (field, value) in enumerate(assignments):
            suffix = "," if idx < len(assignments) - 1 else ""
            lines.append(f"  {field} := {value}{suffix}")
        lines.extend(
            [
                "}",
                "",
                "theorem independent_registered_truth_condition_clause_coverage_exists :",
                "    Exists (fun C : "
                "IndependentRegisteredTruthConditionClauseCoverage => "
                "C = independent_registered_truth_condition_clause_coverage) := by",
                "  exact Exists.intro "
                "independent_registered_truth_condition_clause_coverage rfl",
                "",
                "theorem "
                "independent_registered_truth_condition_clause_coverage_instances_match :",
                "    independent_registered_truth_condition_clause_coverage.",
                "      independent_registered_clause_coverage_instances =",
                "        independent_registered_truth_condition_clause_instances := by",
                "  exact independent_registered_truth_condition_clause_coverage.",
                "    independent_registered_clause_coverage_instances_eq",
                "",
                "theorem "
                "independent_registered_truth_condition_clause_coverage_spec_sound :",
                "    (A : Type) -> (term : A) ->",
                "    independent_registered_truth_condition_clause_instances.",
                "    independent_registered_clause_spec.",
                "    fully_registered_truth_denotes A term ->",
                "    AtomicClosureTruth A term := by",
                "  exact independent_registered_truth_condition_clause_coverage.",
                "    independent_registered_clause_coverage_spec_sound",
            ]
        )
        for idx, result in enumerate(results, 1):
            annotation = export_result_type(result["ast"])
            lines.extend(
                [
                    "",
                    "theorem "
                    f"independent_registered_truth_condition_clause_coverage_example_{idx}_atomic_sound : "
                    f"AtomicClosureTruth {annotation} example_{idx} := by",
                    "  exact independent_registered_truth_condition_clause_coverage."
                    f"independent_registered_clause_coverage_example_{idx}",
                ]
            )
        return lines

    fields: list[list[str]] = [
        [
            "  independent_registered_clause_coverage_instances :",
            "      IndependentRegisteredTruthConditionClauseInstances",
        ],
        [
            "  independent_registered_clause_coverage_instances_eq :",
            "      independent_registered_clause_coverage_instances =",
            "        independent_registered_truth_condition_clause_instances",
        ],
        [
            "  independent_registered_clause_coverage_lexical_application :",
            "    forall A : Type, forall term : A,",
            "      RegisteredLexicalApplicationTruth A term ->",
            "      fully_registered_truth_denotes",
            "        (independent_registered_clause_spec",
            "          independent_registered_truth_condition_clause_instances) A term",
        ],
    ]
    for type_name in declarations["types"]:
        fields.append(
            [
                f"  independent_registered_clause_coverage_sigma_{type_name} :",
                f"    forall P : {type_name} -> Prop,",
                f"      (forall x : {type_name},",
                "        fully_registered_truth_denotes",
                "          (independent_registered_clause_spec",
                "            independent_registered_truth_condition_clause_instances)",
                "          Prop (P x)) ->",
                "      fully_registered_truth_denotes",
                "        (independent_registered_clause_spec",
                "          independent_registered_truth_condition_clause_instances)",
                f"        Prop (exists x : {type_name}, P x)",
            ]
        )
    for name, _lean_binders, coq_binders, premise, conclusion in (
        time_and_polarity_clauses
    ):
        fields.append(
            [
                f"  independent_registered_clause_coverage_{name} :",
                f"    {coq_binders}",
                "      fully_registered_truth_denotes",
                "        (independent_registered_clause_spec",
                "          independent_registered_truth_condition_clause_instances)",
                f"        {premise} ->",
                "      fully_registered_truth_denotes",
                "        (independent_registered_clause_spec",
                "          independent_registered_truth_condition_clause_instances)",
                f"        {conclusion}",
            ]
        )
    fields.extend(
        [
            [
                "  independent_registered_clause_coverage_transition :",
                "    forall theme : Entity, forall scale : StateScale,",
                "    forall source : State, forall target : State,",
                "      RegisteredStateTransitionTruth theme scale source target ->",
                "      fully_registered_truth_denotes",
                "        (independent_registered_clause_spec",
                "          independent_registered_truth_condition_clause_instances)",
                "        TransitionT (Transition theme scale source target)",
            ],
            [
                "  independent_registered_clause_coverage_cause :",
                "    forall causer : Entity, forall effect : TransitionT,",
                "      fully_registered_truth_denotes",
                "        (independent_registered_clause_spec",
                "          independent_registered_truth_condition_clause_instances)",
                "        TransitionT effect ->",
                "      fully_registered_truth_denotes",
                "        (independent_registered_clause_spec",
                "          independent_registered_truth_condition_clause_instances)",
                "        PropT (Cause causer effect)",
            ],
            [
                "  independent_registered_clause_coverage_spec_sound :",
                "    forall A : Type, forall term : A,",
                "      fully_registered_truth_denotes",
                "        (independent_registered_clause_spec",
                "          independent_registered_truth_condition_clause_instances) A term ->",
                "      AtomicClosureTruth A term",
            ],
        ]
    )
    for idx, result in enumerate(results, 1):
        annotation = export_result_type(result["ast"])
        fields.append(
            [
                f"  independent_registered_clause_coverage_example_{idx} :",
                f"      AtomicClosureTruth {annotation} example_{idx}",
            ]
        )

    lines = ["Record IndependentRegisteredTruthConditionClauseCoverage : Type := {"]
    for idx, field_lines in enumerate(fields):
        is_last = idx == len(fields) - 1
        for field_idx, field_line in enumerate(field_lines):
            if field_idx == len(field_lines) - 1 and not is_last:
                lines.append(f"{field_line};")
            else:
                lines.append(field_line)
    lines.append("}.")

    assignments = [
        (
            "independent_registered_clause_coverage_instances",
            "independent_registered_truth_condition_clause_instances",
        ),
        ("independent_registered_clause_coverage_instances_eq", "eq_refl"),
        (
            "independent_registered_clause_coverage_lexical_application",
            "independent_registered_truth_condition_clause_lexical_application_instance",
        ),
    ]
    assignments.extend(
        (
            f"independent_registered_clause_coverage_sigma_{type_name}",
            f"independent_registered_truth_condition_clause_sigma_{type_name}_instance",
        )
        for type_name in declarations["types"]
    )
    assignments.extend(
        (
            f"independent_registered_clause_coverage_{name}",
            f"independent_registered_truth_condition_clause_{name}_instance",
        )
        for name, _lean_binders, _coq_binders, _premise, _conclusion in (
            time_and_polarity_clauses
        )
    )
    assignments.extend(
        [
            (
                "independent_registered_clause_coverage_transition",
                "independent_registered_truth_condition_clause_transition_instance",
            ),
            (
                "independent_registered_clause_coverage_cause",
                "independent_registered_truth_condition_clause_cause_instance",
            ),
            (
                "independent_registered_clause_coverage_spec_sound",
                "independent_registered_truth_condition_clause_spec_sound",
            ),
        ]
    )
    assignments.extend(
        (
            f"independent_registered_clause_coverage_example_{idx}",
            f"independent_registered_truth_condition_clause_example_{idx}_atomic_sound",
        )
        for idx in range(1, len(results) + 1)
    )
    lines.extend(
        [
            "",
            "Definition independent_registered_truth_condition_clause_coverage :",
            "  IndependentRegisteredTruthConditionClauseCoverage := {|",
        ]
    )
    for idx, (field, value) in enumerate(assignments):
        suffix = ";" if idx < len(assignments) - 1 else ""
        lines.append(f"  {field} := {value}{suffix}")
    lines.extend(
        [
            "|}.",
            "",
            "Theorem independent_registered_truth_condition_clause_coverage_exists :",
            "  exists C : IndependentRegisteredTruthConditionClauseCoverage,",
            "    C = independent_registered_truth_condition_clause_coverage.",
            "Proof.",
            "  exists independent_registered_truth_condition_clause_coverage.",
            "  reflexivity.",
            "Qed.",
            "",
            "Theorem "
            "independent_registered_truth_condition_clause_coverage_instances_match :",
            "  independent_registered_clause_coverage_instances",
            "    independent_registered_truth_condition_clause_coverage =",
            "  independent_registered_truth_condition_clause_instances.",
            "Proof.",
            "  exact (independent_registered_clause_coverage_instances_eq",
            "    independent_registered_truth_condition_clause_coverage).",
            "Qed.",
            "",
            "Theorem independent_registered_truth_condition_clause_coverage_spec_sound :",
            "  forall A : Type, forall term : A,",
            "    fully_registered_truth_denotes",
            "      (independent_registered_clause_spec",
            "        independent_registered_truth_condition_clause_instances) A term ->",
            "    AtomicClosureTruth A term.",
            "Proof.",
            "  exact (independent_registered_clause_coverage_spec_sound",
            "    independent_registered_truth_condition_clause_coverage).",
            "Qed.",
        ]
    )
    for idx, result in enumerate(results, 1):
        annotation = export_result_type(result["ast"])
        lines.extend(
            [
                "",
                "Theorem "
                f"independent_registered_truth_condition_clause_coverage_example_{idx}_atomic_sound : "
                f"AtomicClosureTruth {annotation} example_{idx}.",
                "Proof.",
                "  exact (independent_registered_clause_coverage_example_"
                f"{idx}",
                "    independent_registered_truth_condition_clause_coverage).",
                "Qed.",
            ]
        )
    return lines


def independent_registered_lexical_truth_condition_instance_lines(
    target: str,
) -> list[str]:
    """Expose registered lexical-application clauses as a subpackage."""

    if target == "lean":
        return [
            "structure IndependentRegisteredLexicalTruthConditionInstances : Type where",
            "  independent_registered_lexical_clause_coverage :",
            "      IndependentRegisteredTruthConditionClauseCoverage",
            "  independent_registered_lexical_clause_coverage_eq :",
            "      independent_registered_lexical_clause_coverage =",
            "        independent_registered_truth_condition_clause_coverage",
            "  independent_registered_lexical_application_instance :",
            "      (A : Type) -> (term : A) ->",
            "      RegisteredLexicalApplicationTruth A term ->",
            "      independent_registered_truth_condition_clause_instances.",
            "      independent_registered_clause_spec.",
            "      fully_registered_truth_denotes A term",
            "  independent_registered_lexical_spec_sound :",
            "      (A : Type) -> (term : A) ->",
            "      independent_registered_truth_condition_clause_instances.",
            "      independent_registered_clause_spec.",
            "      fully_registered_truth_denotes A term ->",
            "      AtomicClosureTruth A term",
            "",
            "def independent_registered_lexical_truth_condition_instances :",
            "    IndependentRegisteredLexicalTruthConditionInstances := {",
            "  independent_registered_lexical_clause_coverage :=",
            "    independent_registered_truth_condition_clause_coverage,",
            "  independent_registered_lexical_clause_coverage_eq := rfl,",
            "  independent_registered_lexical_application_instance :=",
            "    independent_registered_truth_condition_clause_lexical_application_instance,",
            "  independent_registered_lexical_spec_sound :=",
            "    independent_registered_truth_condition_clause_coverage."
            "independent_registered_clause_coverage_spec_sound",
            "}",
            "",
            "theorem independent_registered_lexical_truth_condition_instances_exists :",
            "    Exists (fun L : "
            "IndependentRegisteredLexicalTruthConditionInstances => "
            "L = independent_registered_lexical_truth_condition_instances) := by",
            "  exact Exists.intro "
            "independent_registered_lexical_truth_condition_instances rfl",
            "",
            "theorem "
            "independent_registered_lexical_truth_condition_coverage_matches :",
            "    independent_registered_lexical_truth_condition_instances.",
            "      independent_registered_lexical_clause_coverage =",
            "        independent_registered_truth_condition_clause_coverage := by",
            "  exact independent_registered_lexical_truth_condition_instances.",
            "    independent_registered_lexical_clause_coverage_eq",
            "",
            "theorem "
            "independent_registered_lexical_truth_condition_application_instance :",
            "    (A : Type) -> (term : A) ->",
            "    RegisteredLexicalApplicationTruth A term ->",
            "    independent_registered_truth_condition_clause_instances.",
            "    independent_registered_clause_spec.",
            "    fully_registered_truth_denotes A term := by",
            "  exact independent_registered_lexical_truth_condition_instances.",
            "    independent_registered_lexical_application_instance",
            "",
            "theorem independent_registered_lexical_truth_condition_spec_sound :",
            "    (A : Type) -> (term : A) ->",
            "    independent_registered_truth_condition_clause_instances.",
            "    independent_registered_clause_spec.",
            "    fully_registered_truth_denotes A term ->",
            "    AtomicClosureTruth A term := by",
            "  exact independent_registered_lexical_truth_condition_instances.",
            "    independent_registered_lexical_spec_sound",
        ]

    return [
        "Record IndependentRegisteredLexicalTruthConditionInstances : Type := {",
        "  independent_registered_lexical_clause_coverage :",
        "      IndependentRegisteredTruthConditionClauseCoverage;",
        "  independent_registered_lexical_clause_coverage_eq :",
        "      independent_registered_lexical_clause_coverage =",
        "        independent_registered_truth_condition_clause_coverage;",
        "  independent_registered_lexical_application_instance :",
        "    forall A : Type, forall term : A,",
        "      RegisteredLexicalApplicationTruth A term ->",
        "      fully_registered_truth_denotes",
        "        (independent_registered_clause_spec",
        "          independent_registered_truth_condition_clause_instances) A term;",
        "  independent_registered_lexical_spec_sound :",
        "    forall A : Type, forall term : A,",
        "      fully_registered_truth_denotes",
        "        (independent_registered_clause_spec",
        "          independent_registered_truth_condition_clause_instances) A term ->",
        "      AtomicClosureTruth A term",
        "}.",
        "",
        "Definition independent_registered_lexical_truth_condition_instances :",
        "  IndependentRegisteredLexicalTruthConditionInstances := {|",
        "  independent_registered_lexical_clause_coverage :=",
        "    independent_registered_truth_condition_clause_coverage;",
        "  independent_registered_lexical_clause_coverage_eq := eq_refl;",
        "  independent_registered_lexical_application_instance :=",
        "    independent_registered_truth_condition_clause_lexical_application_instance;",
        "  independent_registered_lexical_spec_sound :=",
        "    independent_registered_clause_coverage_spec_sound",
        "      independent_registered_truth_condition_clause_coverage",
        "|}.",
        "",
        "Theorem independent_registered_lexical_truth_condition_instances_exists :",
        "  exists L : IndependentRegisteredLexicalTruthConditionInstances,",
        "    L = independent_registered_lexical_truth_condition_instances.",
        "Proof.",
        "  exists independent_registered_lexical_truth_condition_instances.",
        "  reflexivity.",
        "Qed.",
        "",
        "Theorem independent_registered_lexical_truth_condition_coverage_matches :",
        "  independent_registered_lexical_clause_coverage",
        "    independent_registered_lexical_truth_condition_instances =",
        "  independent_registered_truth_condition_clause_coverage.",
        "Proof.",
        "  exact (independent_registered_lexical_clause_coverage_eq",
        "    independent_registered_lexical_truth_condition_instances).",
        "Qed.",
        "",
        "Theorem independent_registered_lexical_truth_condition_application_instance :",
        "  forall A : Type, forall term : A,",
        "    RegisteredLexicalApplicationTruth A term ->",
        "    fully_registered_truth_denotes",
        "      (independent_registered_clause_spec",
        "        independent_registered_truth_condition_clause_instances) A term.",
        "Proof.",
        "  exact (independent_registered_lexical_application_instance",
        "    independent_registered_lexical_truth_condition_instances).",
        "Qed.",
        "",
        "Theorem independent_registered_lexical_truth_condition_spec_sound :",
        "  forall A : Type, forall term : A,",
        "    fully_registered_truth_denotes",
        "      (independent_registered_clause_spec",
        "        independent_registered_truth_condition_clause_instances) A term ->",
        "    AtomicClosureTruth A term.",
        "Proof.",
        "  exact (independent_registered_lexical_spec_sound",
        "    independent_registered_lexical_truth_condition_instances).",
        "Qed.",
    ]


def independent_registered_temporal_truth_condition_instance_lines(
    target: str,
) -> list[str]:
    """Expose the registered temporal truth-condition clauses as a subpackage."""

    temporal_clauses = [
        ("at_T", "PropT (at_T marker body)"),
        ("during_T", "PropT (during_T marker body)"),
        ("before_T", "PropT (before_T marker body)"),
        ("after_T", "PropT (after_T marker body)"),
        ("until_T", "PropT (until_T marker body)"),
        ("since_T", "PropT (since_T marker body)"),
    ]

    if target == "lean":
        lines = [
            "structure IndependentRegisteredTemporalTruthConditionInstances : Type where",
            "  independent_registered_temporal_clause_coverage :",
            "      IndependentRegisteredTruthConditionClauseCoverage",
            "  independent_registered_temporal_clause_coverage_eq :",
            "      independent_registered_temporal_clause_coverage =",
            "        independent_registered_truth_condition_clause_coverage",
        ]
        for name, conclusion in temporal_clauses:
            lines.extend(
                [
                    f"  independent_registered_temporal_{name}_instance :",
                    "      (marker : Entity) -> (body : PropT) ->",
                    "      independent_registered_truth_condition_clause_instances.",
                    "      independent_registered_clause_spec.",
                    "      fully_registered_truth_denotes PropT body ->",
                    "      independent_registered_truth_condition_clause_instances.",
                    "      independent_registered_clause_spec.",
                    f"      fully_registered_truth_denotes {conclusion}",
                ]
            )
        lines.extend(
            [
                "  independent_registered_temporal_spec_sound :",
                "      (A : Type) -> (term : A) ->",
                "      independent_registered_truth_condition_clause_instances.",
                "      independent_registered_clause_spec.",
                "      fully_registered_truth_denotes A term ->",
                "      AtomicClosureTruth A term",
                "",
                "def independent_registered_temporal_truth_condition_instances :",
                "    IndependentRegisteredTemporalTruthConditionInstances := {",
                "  independent_registered_temporal_clause_coverage :=",
                "    independent_registered_truth_condition_clause_coverage,",
                "  independent_registered_temporal_clause_coverage_eq := rfl,",
            ]
        )
        for idx, (name, _conclusion) in enumerate(temporal_clauses):
            suffix = "," if idx < len(temporal_clauses) - 1 else ","
            lines.append(
                f"  independent_registered_temporal_{name}_instance := "
                f"independent_registered_truth_condition_clause_{name}_instance{suffix}"
            )
        lines.extend(
            [
                "  independent_registered_temporal_spec_sound :=",
                "    independent_registered_truth_condition_clause_coverage."
                "independent_registered_clause_coverage_spec_sound",
                "}",
                "",
                "theorem independent_registered_temporal_truth_condition_instances_exists :",
                "    Exists (fun T : "
                "IndependentRegisteredTemporalTruthConditionInstances => "
                "T = independent_registered_temporal_truth_condition_instances) := by",
                "  exact Exists.intro "
                "independent_registered_temporal_truth_condition_instances rfl",
                "",
                "theorem "
                "independent_registered_temporal_truth_condition_coverage_matches :",
                "    independent_registered_temporal_truth_condition_instances.",
                "      independent_registered_temporal_clause_coverage =",
                "        independent_registered_truth_condition_clause_coverage := by",
                "  exact independent_registered_temporal_truth_condition_instances.",
                "    independent_registered_temporal_clause_coverage_eq",
            ]
        )
        for name, conclusion in temporal_clauses:
            lines.extend(
                [
                    "",
                    "theorem "
                    f"independent_registered_temporal_truth_condition_{name}_instance :",
                    "    (marker : Entity) -> (body : PropT) ->",
                    "    independent_registered_truth_condition_clause_instances.",
                    "    independent_registered_clause_spec.",
                    "    fully_registered_truth_denotes PropT body ->",
                    "    independent_registered_truth_condition_clause_instances.",
                    "    independent_registered_clause_spec.",
                    f"    fully_registered_truth_denotes {conclusion} := by",
                    "  exact independent_registered_temporal_truth_condition_instances.",
                    f"    independent_registered_temporal_{name}_instance",
                ]
            )
        lines.extend(
            [
                "",
                "theorem "
                "independent_registered_temporal_truth_condition_spec_sound :",
                "    (A : Type) -> (term : A) ->",
                "    independent_registered_truth_condition_clause_instances.",
                "    independent_registered_clause_spec.",
                "    fully_registered_truth_denotes A term ->",
                "    AtomicClosureTruth A term := by",
                "  exact independent_registered_temporal_truth_condition_instances.",
                "    independent_registered_temporal_spec_sound",
            ]
        )
        return lines

    fields: list[list[str]] = [
        [
            "  independent_registered_temporal_clause_coverage :",
            "      IndependentRegisteredTruthConditionClauseCoverage",
        ],
        [
            "  independent_registered_temporal_clause_coverage_eq :",
            "      independent_registered_temporal_clause_coverage =",
            "        independent_registered_truth_condition_clause_coverage",
        ],
    ]
    for name, conclusion in temporal_clauses:
        fields.append(
            [
                f"  independent_registered_temporal_{name}_instance :",
                "    forall marker : Entity, forall body : PropT,",
                "      fully_registered_truth_denotes",
                "        (independent_registered_clause_spec",
                "          independent_registered_truth_condition_clause_instances)",
                "        PropT body ->",
                "      fully_registered_truth_denotes",
                "        (independent_registered_clause_spec",
                "          independent_registered_truth_condition_clause_instances)",
                f"        {conclusion}",
            ]
        )
    fields.append(
        [
            "  independent_registered_temporal_spec_sound :",
            "    forall A : Type, forall term : A,",
            "      fully_registered_truth_denotes",
            "        (independent_registered_clause_spec",
            "          independent_registered_truth_condition_clause_instances) A term ->",
            "      AtomicClosureTruth A term",
        ]
    )

    lines = ["Record IndependentRegisteredTemporalTruthConditionInstances : Type := {"]
    for idx, field_lines in enumerate(fields):
        is_last = idx == len(fields) - 1
        for field_idx, field_line in enumerate(field_lines):
            if field_idx == len(field_lines) - 1 and not is_last:
                lines.append(f"{field_line};")
            else:
                lines.append(field_line)
    lines.extend(
        [
            "}.",
            "",
            "Definition independent_registered_temporal_truth_condition_instances :",
            "  IndependentRegisteredTemporalTruthConditionInstances := {|",
            "  independent_registered_temporal_clause_coverage :=",
            "    independent_registered_truth_condition_clause_coverage;",
            "  independent_registered_temporal_clause_coverage_eq := eq_refl;",
        ]
    )
    for name, _conclusion in temporal_clauses:
        lines.append(
            f"  independent_registered_temporal_{name}_instance := "
            f"independent_registered_truth_condition_clause_{name}_instance;"
        )
    lines.extend(
        [
            "  independent_registered_temporal_spec_sound :=",
            "    independent_registered_clause_coverage_spec_sound",
            "      independent_registered_truth_condition_clause_coverage",
            "|}.",
            "",
            "Theorem independent_registered_temporal_truth_condition_instances_exists :",
            "  exists T : IndependentRegisteredTemporalTruthConditionInstances,",
            "    T = independent_registered_temporal_truth_condition_instances.",
            "Proof.",
            "  exists independent_registered_temporal_truth_condition_instances.",
            "  reflexivity.",
            "Qed.",
            "",
            "Theorem independent_registered_temporal_truth_condition_coverage_matches :",
            "  independent_registered_temporal_clause_coverage",
            "    independent_registered_temporal_truth_condition_instances =",
            "  independent_registered_truth_condition_clause_coverage.",
            "Proof.",
            "  exact (independent_registered_temporal_clause_coverage_eq",
            "    independent_registered_temporal_truth_condition_instances).",
            "Qed.",
        ]
    )
    for name, conclusion in temporal_clauses:
        lines.extend(
            [
                "",
                "Theorem "
                f"independent_registered_temporal_truth_condition_{name}_instance :",
                "  forall marker : Entity, forall body : PropT,",
                "    fully_registered_truth_denotes",
                "      (independent_registered_clause_spec",
                "        independent_registered_truth_condition_clause_instances)",
                "      PropT body ->",
                "    fully_registered_truth_denotes",
                "      (independent_registered_clause_spec",
                "        independent_registered_truth_condition_clause_instances)",
                f"      {conclusion}.",
                "Proof.",
                "  exact (independent_registered_temporal_"
                f"{name}_instance",
                "    independent_registered_temporal_truth_condition_instances).",
                "Qed.",
            ]
        )
    lines.extend(
        [
            "",
            "Theorem independent_registered_temporal_truth_condition_spec_sound :",
            "  forall A : Type, forall term : A,",
            "    fully_registered_truth_denotes",
            "      (independent_registered_clause_spec",
            "        independent_registered_truth_condition_clause_instances) A term ->",
            "    AtomicClosureTruth A term.",
            "Proof.",
            "  exact (independent_registered_temporal_spec_sound",
            "    independent_registered_temporal_truth_condition_instances).",
            "Qed.",
        ]
    )
    return lines


def independent_registered_sigma_truth_condition_instance_lines(
    declarations: dict[str, Any],
    target: str,
) -> list[str]:
    """Expose registered dependent existential clauses as a subpackage."""

    sigma_types = declarations["types"]

    if target == "lean":
        lines = [
            "structure IndependentRegisteredSigmaTruthConditionInstances : Type where",
            "  independent_registered_sigma_clause_coverage :",
            "      IndependentRegisteredTruthConditionClauseCoverage",
            "  independent_registered_sigma_clause_coverage_eq :",
            "      independent_registered_sigma_clause_coverage =",
            "        independent_registered_truth_condition_clause_coverage",
        ]
        for type_name in sigma_types:
            lines.extend(
                [
                    f"  independent_registered_sigma_{type_name}_instance :",
                    f"      (P : {type_name} -> Prop) ->",
                    f"      ((x : {type_name}) ->",
                    "        independent_registered_truth_condition_clause_instances.",
                    "        independent_registered_clause_spec.",
                    "        fully_registered_truth_denotes Prop (P x)) ->",
                    "      independent_registered_truth_condition_clause_instances.",
                    "      independent_registered_clause_spec.",
                    "      fully_registered_truth_denotes Prop",
                    f"        (Exists fun x : {type_name} => P x)",
                ]
            )
        lines.extend(
            [
                "  independent_registered_sigma_spec_sound :",
                "      (A : Type) -> (term : A) ->",
                "      independent_registered_truth_condition_clause_instances.",
                "      independent_registered_clause_spec.",
                "      fully_registered_truth_denotes A term ->",
                "      AtomicClosureTruth A term",
                "",
                "def independent_registered_sigma_truth_condition_instances :",
                "    IndependentRegisteredSigmaTruthConditionInstances := {",
                "  independent_registered_sigma_clause_coverage :=",
                "    independent_registered_truth_condition_clause_coverage,",
                "  independent_registered_sigma_clause_coverage_eq := rfl,",
            ]
        )
        for type_name in sigma_types:
            lines.append(
                f"  independent_registered_sigma_{type_name}_instance := "
                "independent_registered_truth_condition_clause_sigma_"
                f"{type_name}_instance,"
            )
        lines.extend(
            [
                "  independent_registered_sigma_spec_sound :=",
                "    independent_registered_truth_condition_clause_coverage."
                "independent_registered_clause_coverage_spec_sound",
                "}",
                "",
                "theorem independent_registered_sigma_truth_condition_instances_exists :",
                "    Exists (fun S : "
                "IndependentRegisteredSigmaTruthConditionInstances => "
                "S = independent_registered_sigma_truth_condition_instances) := by",
                "  exact Exists.intro "
                "independent_registered_sigma_truth_condition_instances rfl",
                "",
                "theorem "
                "independent_registered_sigma_truth_condition_coverage_matches :",
                "    independent_registered_sigma_truth_condition_instances.",
                "      independent_registered_sigma_clause_coverage =",
                "        independent_registered_truth_condition_clause_coverage := by",
                "  exact independent_registered_sigma_truth_condition_instances.",
                "    independent_registered_sigma_clause_coverage_eq",
            ]
        )
        for type_name in sigma_types:
            lines.extend(
                [
                    "",
                    "theorem "
                    f"independent_registered_sigma_truth_condition_sigma_{type_name}_instance :",
                    f"    (P : {type_name} -> Prop) ->",
                    f"    ((x : {type_name}) ->",
                    "      independent_registered_truth_condition_clause_instances.",
                    "      independent_registered_clause_spec.",
                    "      fully_registered_truth_denotes Prop (P x)) ->",
                    "    independent_registered_truth_condition_clause_instances.",
                    "    independent_registered_clause_spec.",
                    "    fully_registered_truth_denotes Prop",
                    f"      (Exists fun x : {type_name} => P x) := by",
                    "  exact independent_registered_sigma_truth_condition_instances.",
                    f"    independent_registered_sigma_{type_name}_instance",
                ]
            )
        lines.extend(
            [
                "",
                "theorem "
                "independent_registered_sigma_truth_condition_spec_sound :",
                "    (A : Type) -> (term : A) ->",
                "    independent_registered_truth_condition_clause_instances.",
                "    independent_registered_clause_spec.",
                "    fully_registered_truth_denotes A term ->",
                "    AtomicClosureTruth A term := by",
                "  exact independent_registered_sigma_truth_condition_instances.",
                "    independent_registered_sigma_spec_sound",
            ]
        )
        return lines

    fields: list[list[str]] = [
        [
            "  independent_registered_sigma_clause_coverage :",
            "      IndependentRegisteredTruthConditionClauseCoverage",
        ],
        [
            "  independent_registered_sigma_clause_coverage_eq :",
            "      independent_registered_sigma_clause_coverage =",
            "        independent_registered_truth_condition_clause_coverage",
        ],
    ]
    for type_name in sigma_types:
        fields.append(
            [
                f"  independent_registered_sigma_{type_name}_instance :",
                f"    forall P : {type_name} -> Prop,",
                f"      (forall x : {type_name},",
                "        fully_registered_truth_denotes",
                "          (independent_registered_clause_spec",
                "            independent_registered_truth_condition_clause_instances)",
                "          Prop (P x)) ->",
                "      fully_registered_truth_denotes",
                "        (independent_registered_clause_spec",
                "          independent_registered_truth_condition_clause_instances)",
                f"        Prop (exists x : {type_name}, P x)",
            ]
        )
    fields.append(
        [
            "  independent_registered_sigma_spec_sound :",
            "    forall A : Type, forall term : A,",
            "      fully_registered_truth_denotes",
            "        (independent_registered_clause_spec",
            "          independent_registered_truth_condition_clause_instances) A term ->",
            "      AtomicClosureTruth A term",
        ]
    )

    lines = ["Record IndependentRegisteredSigmaTruthConditionInstances : Type := {"]
    for idx, field_lines in enumerate(fields):
        is_last = idx == len(fields) - 1
        for field_idx, field_line in enumerate(field_lines):
            if field_idx == len(field_lines) - 1 and not is_last:
                lines.append(f"{field_line};")
            else:
                lines.append(field_line)
    lines.extend(
        [
            "}.",
            "",
            "Definition independent_registered_sigma_truth_condition_instances :",
            "  IndependentRegisteredSigmaTruthConditionInstances := {|",
            "  independent_registered_sigma_clause_coverage :=",
            "    independent_registered_truth_condition_clause_coverage;",
            "  independent_registered_sigma_clause_coverage_eq := eq_refl;",
        ]
    )
    for type_name in sigma_types:
        lines.append(
            f"  independent_registered_sigma_{type_name}_instance := "
            "independent_registered_truth_condition_clause_sigma_"
            f"{type_name}_instance;"
        )
    lines.extend(
        [
            "  independent_registered_sigma_spec_sound :=",
            "    independent_registered_clause_coverage_spec_sound",
            "      independent_registered_truth_condition_clause_coverage",
            "|}.",
            "",
            "Theorem independent_registered_sigma_truth_condition_instances_exists :",
            "  exists S : IndependentRegisteredSigmaTruthConditionInstances,",
            "    S = independent_registered_sigma_truth_condition_instances.",
            "Proof.",
            "  exists independent_registered_sigma_truth_condition_instances.",
            "  reflexivity.",
            "Qed.",
            "",
            "Theorem independent_registered_sigma_truth_condition_coverage_matches :",
            "  independent_registered_sigma_clause_coverage",
            "    independent_registered_sigma_truth_condition_instances =",
            "  independent_registered_truth_condition_clause_coverage.",
            "Proof.",
            "  exact (independent_registered_sigma_clause_coverage_eq",
            "    independent_registered_sigma_truth_condition_instances).",
            "Qed.",
        ]
    )
    for type_name in sigma_types:
        lines.extend(
            [
                "",
                "Theorem "
                f"independent_registered_sigma_truth_condition_sigma_{type_name}_instance :",
                f"  forall P : {type_name} -> Prop,",
                f"    (forall x : {type_name},",
                "      fully_registered_truth_denotes",
                "        (independent_registered_clause_spec",
                "          independent_registered_truth_condition_clause_instances)",
                "        Prop (P x)) ->",
                "    fully_registered_truth_denotes",
                "      (independent_registered_clause_spec",
                "        independent_registered_truth_condition_clause_instances)",
                f"      Prop (exists x : {type_name}, P x).",
                "Proof.",
                "  exact (independent_registered_sigma_"
                f"{type_name}_instance",
                "    independent_registered_sigma_truth_condition_instances).",
                "Qed.",
            ]
        )
    lines.extend(
        [
            "",
            "Theorem independent_registered_sigma_truth_condition_spec_sound :",
            "  forall A : Type, forall term : A,",
            "    fully_registered_truth_denotes",
            "      (independent_registered_clause_spec",
            "        independent_registered_truth_condition_clause_instances) A term ->",
            "    AtomicClosureTruth A term.",
            "Proof.",
            "  exact (independent_registered_sigma_spec_sound",
            "    independent_registered_sigma_truth_condition_instances).",
            "Qed.",
        ]
    )
    return lines


def independent_registered_repeat_truth_condition_instance_lines(
    target: str,
) -> list[str]:
    """Expose the registered repetition/event-counting clause as a subpackage."""

    if target == "lean":
        return [
            "structure IndependentRegisteredRepeatTruthConditionInstances : Type where",
            "  independent_registered_repeat_clause_coverage :",
            "      IndependentRegisteredTruthConditionClauseCoverage",
            "  independent_registered_repeat_clause_coverage_eq :",
            "      independent_registered_repeat_clause_coverage =",
            "        independent_registered_truth_condition_clause_coverage",
            "  independent_registered_repeat_instance :",
            "      (n : Nat) -> (body : PropT) ->",
            "      independent_registered_truth_condition_clause_instances.",
            "      independent_registered_clause_spec.",
            "      fully_registered_truth_denotes PropT body ->",
            "      independent_registered_truth_condition_clause_instances.",
            "      independent_registered_clause_spec.",
            "      fully_registered_truth_denotes PropT (repeat n body)",
            "  independent_registered_repeat_spec_sound :",
            "      (A : Type) -> (term : A) ->",
            "      independent_registered_truth_condition_clause_instances.",
            "      independent_registered_clause_spec.",
            "      fully_registered_truth_denotes A term ->",
            "      AtomicClosureTruth A term",
            "",
            "def independent_registered_repeat_truth_condition_instances :",
            "    IndependentRegisteredRepeatTruthConditionInstances := {",
            "  independent_registered_repeat_clause_coverage :=",
            "    independent_registered_truth_condition_clause_coverage,",
            "  independent_registered_repeat_clause_coverage_eq := rfl,",
            "  independent_registered_repeat_instance :=",
            "    independent_registered_truth_condition_clause_repeat_instance,",
            "  independent_registered_repeat_spec_sound :=",
            "    independent_registered_truth_condition_clause_coverage."
            "independent_registered_clause_coverage_spec_sound",
            "}",
            "",
            "theorem independent_registered_repeat_truth_condition_instances_exists :",
            "    Exists (fun R : "
            "IndependentRegisteredRepeatTruthConditionInstances => "
            "R = independent_registered_repeat_truth_condition_instances) := by",
            "  exact Exists.intro "
            "independent_registered_repeat_truth_condition_instances rfl",
            "",
            "theorem "
            "independent_registered_repeat_truth_condition_coverage_matches :",
            "    independent_registered_repeat_truth_condition_instances.",
            "      independent_registered_repeat_clause_coverage =",
            "        independent_registered_truth_condition_clause_coverage := by",
            "  exact independent_registered_repeat_truth_condition_instances.",
            "    independent_registered_repeat_clause_coverage_eq",
            "",
            "theorem independent_registered_repeat_truth_condition_repeat_instance :",
            "    (n : Nat) -> (body : PropT) ->",
            "    independent_registered_truth_condition_clause_instances.",
            "    independent_registered_clause_spec.",
            "    fully_registered_truth_denotes PropT body ->",
            "    independent_registered_truth_condition_clause_instances.",
            "    independent_registered_clause_spec.",
            "    fully_registered_truth_denotes PropT (repeat n body) := by",
            "  exact independent_registered_repeat_truth_condition_instances.",
            "    independent_registered_repeat_instance",
            "",
            "theorem independent_registered_repeat_truth_condition_spec_sound :",
            "    (A : Type) -> (term : A) ->",
            "    independent_registered_truth_condition_clause_instances.",
            "    independent_registered_clause_spec.",
            "    fully_registered_truth_denotes A term ->",
            "    AtomicClosureTruth A term := by",
            "  exact independent_registered_repeat_truth_condition_instances.",
            "    independent_registered_repeat_spec_sound",
        ]

    return [
        "Record IndependentRegisteredRepeatTruthConditionInstances : Type := {",
        "  independent_registered_repeat_clause_coverage :",
        "      IndependentRegisteredTruthConditionClauseCoverage;",
        "  independent_registered_repeat_clause_coverage_eq :",
        "      independent_registered_repeat_clause_coverage =",
        "        independent_registered_truth_condition_clause_coverage;",
        "  independent_registered_repeat_instance :",
        "    forall n : nat, forall body : PropT,",
        "      fully_registered_truth_denotes",
        "        (independent_registered_clause_spec",
        "          independent_registered_truth_condition_clause_instances)",
        "        PropT body ->",
        "      fully_registered_truth_denotes",
        "        (independent_registered_clause_spec",
        "          independent_registered_truth_condition_clause_instances)",
        "        PropT (repeat n body);",
        "  independent_registered_repeat_spec_sound :",
        "    forall A : Type, forall term : A,",
        "      fully_registered_truth_denotes",
        "        (independent_registered_clause_spec",
        "          independent_registered_truth_condition_clause_instances) A term ->",
        "      AtomicClosureTruth A term",
        "}.",
        "",
        "Definition independent_registered_repeat_truth_condition_instances :",
        "  IndependentRegisteredRepeatTruthConditionInstances := {|",
        "  independent_registered_repeat_clause_coverage :=",
        "    independent_registered_truth_condition_clause_coverage;",
        "  independent_registered_repeat_clause_coverage_eq := eq_refl;",
        "  independent_registered_repeat_instance :=",
        "    independent_registered_truth_condition_clause_repeat_instance;",
        "  independent_registered_repeat_spec_sound :=",
        "    independent_registered_clause_coverage_spec_sound",
        "      independent_registered_truth_condition_clause_coverage",
        "|}.",
        "",
        "Theorem independent_registered_repeat_truth_condition_instances_exists :",
        "  exists R : IndependentRegisteredRepeatTruthConditionInstances,",
        "    R = independent_registered_repeat_truth_condition_instances.",
        "Proof.",
        "  exists independent_registered_repeat_truth_condition_instances.",
        "  reflexivity.",
        "Qed.",
        "",
        "Theorem independent_registered_repeat_truth_condition_coverage_matches :",
        "  independent_registered_repeat_clause_coverage",
        "    independent_registered_repeat_truth_condition_instances =",
        "  independent_registered_truth_condition_clause_coverage.",
        "Proof.",
        "  exact (independent_registered_repeat_clause_coverage_eq",
        "    independent_registered_repeat_truth_condition_instances).",
        "Qed.",
        "",
        "Theorem independent_registered_repeat_truth_condition_repeat_instance :",
        "  forall n : nat, forall body : PropT,",
        "    fully_registered_truth_denotes",
        "      (independent_registered_clause_spec",
        "        independent_registered_truth_condition_clause_instances)",
        "      PropT body ->",
        "    fully_registered_truth_denotes",
        "      (independent_registered_clause_spec",
        "        independent_registered_truth_condition_clause_instances)",
        "      PropT (repeat n body).",
        "Proof.",
        "  exact (independent_registered_repeat_instance",
        "    independent_registered_repeat_truth_condition_instances).",
        "Qed.",
        "",
        "Theorem independent_registered_repeat_truth_condition_spec_sound :",
        "  forall A : Type, forall term : A,",
        "    fully_registered_truth_denotes",
        "      (independent_registered_clause_spec",
        "        independent_registered_truth_condition_clause_instances) A term ->",
        "    AtomicClosureTruth A term.",
        "Proof.",
        "  exact (independent_registered_repeat_spec_sound",
        "    independent_registered_repeat_truth_condition_instances).",
        "Qed.",
    ]


def independent_registered_polarity_truth_condition_instance_lines(
    target: str,
) -> list[str]:
    """Expose the registered polarity/negation clause as a subpackage."""

    if target == "lean":
        return [
            "structure IndependentRegisteredPolarityTruthConditionInstances : Type where",
            "  independent_registered_polarity_clause_coverage :",
            "      IndependentRegisteredTruthConditionClauseCoverage",
            "  independent_registered_polarity_clause_coverage_eq :",
            "      independent_registered_polarity_clause_coverage =",
            "        independent_registered_truth_condition_clause_coverage",
            "  independent_registered_polarity_instance :",
            "      (body : PropT) ->",
            "      independent_registered_truth_condition_clause_instances.",
            "      independent_registered_clause_spec.",
            "      fully_registered_truth_denotes PropT body ->",
            "      independent_registered_truth_condition_clause_instances.",
            "      independent_registered_clause_spec.",
            "      fully_registered_truth_denotes PropT (not_T body)",
            "  independent_registered_polarity_spec_sound :",
            "      (A : Type) -> (term : A) ->",
            "      independent_registered_truth_condition_clause_instances.",
            "      independent_registered_clause_spec.",
            "      fully_registered_truth_denotes A term ->",
            "      AtomicClosureTruth A term",
            "",
            "def independent_registered_polarity_truth_condition_instances :",
            "    IndependentRegisteredPolarityTruthConditionInstances := {",
            "  independent_registered_polarity_clause_coverage :=",
            "    independent_registered_truth_condition_clause_coverage,",
            "  independent_registered_polarity_clause_coverage_eq := rfl,",
            "  independent_registered_polarity_instance :=",
            "    independent_registered_truth_condition_clause_not_T_instance,",
            "  independent_registered_polarity_spec_sound :=",
            "    independent_registered_truth_condition_clause_coverage."
            "independent_registered_clause_coverage_spec_sound",
            "}",
            "",
            "theorem independent_registered_polarity_truth_condition_instances_exists :",
            "    Exists (fun P : "
            "IndependentRegisteredPolarityTruthConditionInstances => "
            "P = independent_registered_polarity_truth_condition_instances) := by",
            "  exact Exists.intro "
            "independent_registered_polarity_truth_condition_instances rfl",
            "",
            "theorem "
            "independent_registered_polarity_truth_condition_coverage_matches :",
            "    independent_registered_polarity_truth_condition_instances.",
            "      independent_registered_polarity_clause_coverage =",
            "        independent_registered_truth_condition_clause_coverage := by",
            "  exact independent_registered_polarity_truth_condition_instances.",
            "    independent_registered_polarity_clause_coverage_eq",
            "",
            "theorem independent_registered_polarity_truth_condition_not_T_instance :",
            "    (body : PropT) ->",
            "    independent_registered_truth_condition_clause_instances.",
            "    independent_registered_clause_spec.",
            "    fully_registered_truth_denotes PropT body ->",
            "    independent_registered_truth_condition_clause_instances.",
            "    independent_registered_clause_spec.",
            "    fully_registered_truth_denotes PropT (not_T body) := by",
            "  exact independent_registered_polarity_truth_condition_instances.",
            "    independent_registered_polarity_instance",
            "",
            "theorem independent_registered_polarity_truth_condition_spec_sound :",
            "    (A : Type) -> (term : A) ->",
            "    independent_registered_truth_condition_clause_instances.",
            "    independent_registered_clause_spec.",
            "    fully_registered_truth_denotes A term ->",
            "    AtomicClosureTruth A term := by",
            "  exact independent_registered_polarity_truth_condition_instances.",
            "    independent_registered_polarity_spec_sound",
        ]

    return [
        "Record IndependentRegisteredPolarityTruthConditionInstances : Type := {",
        "  independent_registered_polarity_clause_coverage :",
        "      IndependentRegisteredTruthConditionClauseCoverage;",
        "  independent_registered_polarity_clause_coverage_eq :",
        "      independent_registered_polarity_clause_coverage =",
        "        independent_registered_truth_condition_clause_coverage;",
        "  independent_registered_polarity_instance :",
        "    forall body : PropT,",
        "      fully_registered_truth_denotes",
        "        (independent_registered_clause_spec",
        "          independent_registered_truth_condition_clause_instances)",
        "        PropT body ->",
        "      fully_registered_truth_denotes",
        "        (independent_registered_clause_spec",
        "          independent_registered_truth_condition_clause_instances)",
        "        PropT (not_T body);",
        "  independent_registered_polarity_spec_sound :",
        "    forall A : Type, forall term : A,",
        "      fully_registered_truth_denotes",
        "        (independent_registered_clause_spec",
        "          independent_registered_truth_condition_clause_instances) A term ->",
        "      AtomicClosureTruth A term",
        "}.",
        "",
        "Definition independent_registered_polarity_truth_condition_instances :",
        "  IndependentRegisteredPolarityTruthConditionInstances := {|",
        "  independent_registered_polarity_clause_coverage :=",
        "    independent_registered_truth_condition_clause_coverage;",
        "  independent_registered_polarity_clause_coverage_eq := eq_refl;",
        "  independent_registered_polarity_instance :=",
        "    independent_registered_truth_condition_clause_not_T_instance;",
        "  independent_registered_polarity_spec_sound :=",
        "    independent_registered_clause_coverage_spec_sound",
        "      independent_registered_truth_condition_clause_coverage",
        "|}.",
        "",
        "Theorem independent_registered_polarity_truth_condition_instances_exists :",
        "  exists P : IndependentRegisteredPolarityTruthConditionInstances,",
        "    P = independent_registered_polarity_truth_condition_instances.",
        "Proof.",
        "  exists independent_registered_polarity_truth_condition_instances.",
        "  reflexivity.",
        "Qed.",
        "",
        "Theorem independent_registered_polarity_truth_condition_coverage_matches :",
        "  independent_registered_polarity_clause_coverage",
        "    independent_registered_polarity_truth_condition_instances =",
        "  independent_registered_truth_condition_clause_coverage.",
        "Proof.",
        "  exact (independent_registered_polarity_clause_coverage_eq",
        "    independent_registered_polarity_truth_condition_instances).",
        "Qed.",
        "",
        "Theorem independent_registered_polarity_truth_condition_not_T_instance :",
        "  forall body : PropT,",
        "    fully_registered_truth_denotes",
        "      (independent_registered_clause_spec",
        "        independent_registered_truth_condition_clause_instances)",
        "      PropT body ->",
        "    fully_registered_truth_denotes",
        "      (independent_registered_clause_spec",
        "        independent_registered_truth_condition_clause_instances)",
        "      PropT (not_T body).",
        "Proof.",
        "  exact (independent_registered_polarity_instance",
        "    independent_registered_polarity_truth_condition_instances).",
        "Qed.",
        "",
        "Theorem independent_registered_polarity_truth_condition_spec_sound :",
        "  forall A : Type, forall term : A,",
        "    fully_registered_truth_denotes",
        "      (independent_registered_clause_spec",
        "        independent_registered_truth_condition_clause_instances) A term ->",
        "    AtomicClosureTruth A term.",
        "Proof.",
        "  exact (independent_registered_polarity_spec_sound",
        "    independent_registered_polarity_truth_condition_instances).",
        "Qed.",
    ]


def independent_registered_transition_cause_truth_condition_instance_lines(
    target: str,
) -> list[str]:
    """Expose registered state-transition and Cause clauses as a subpackage."""

    if target == "lean":
        return [
            "structure IndependentRegisteredTransitionCauseTruthConditionInstances : Type where",
            "  independent_registered_transition_cause_clause_coverage :",
            "      IndependentRegisteredTruthConditionClauseCoverage",
            "  independent_registered_transition_cause_clause_coverage_eq :",
            "      independent_registered_transition_cause_clause_coverage =",
            "        independent_registered_truth_condition_clause_coverage",
            "  independent_registered_transition_cause_transition_instance :",
            "      (theme : Entity) -> (scale : StateScale) ->",
            "      (source : State) -> (target : State) ->",
            "      RegisteredStateTransitionTruth theme scale source target ->",
            "      independent_registered_truth_condition_clause_instances.",
            "      independent_registered_clause_spec.",
            "      fully_registered_truth_denotes TransitionT",
            "        (Transition theme scale source target)",
            "  independent_registered_transition_cause_cause_instance :",
            "      (causer : Entity) -> (effect : TransitionT) ->",
            "      independent_registered_truth_condition_clause_instances.",
            "      independent_registered_clause_spec.",
            "      fully_registered_truth_denotes TransitionT effect ->",
            "      independent_registered_truth_condition_clause_instances.",
            "      independent_registered_clause_spec.",
            "      fully_registered_truth_denotes PropT (Cause causer effect)",
            "  independent_registered_transition_cause_spec_sound :",
            "      (A : Type) -> (term : A) ->",
            "      independent_registered_truth_condition_clause_instances.",
            "      independent_registered_clause_spec.",
            "      fully_registered_truth_denotes A term ->",
            "      AtomicClosureTruth A term",
            "",
            "def independent_registered_transition_cause_truth_condition_instances :",
            "    IndependentRegisteredTransitionCauseTruthConditionInstances := {",
            "  independent_registered_transition_cause_clause_coverage :=",
            "    independent_registered_truth_condition_clause_coverage,",
            "  independent_registered_transition_cause_clause_coverage_eq := rfl,",
            "  independent_registered_transition_cause_transition_instance :=",
            "    independent_registered_truth_condition_clause_transition_instance,",
            "  independent_registered_transition_cause_cause_instance :=",
            "    independent_registered_truth_condition_clause_cause_instance,",
            "  independent_registered_transition_cause_spec_sound :=",
            "    independent_registered_truth_condition_clause_coverage."
            "independent_registered_clause_coverage_spec_sound",
            "}",
            "",
            "theorem "
            "independent_registered_transition_cause_truth_condition_instances_exists :",
            "    Exists (fun TC : "
            "IndependentRegisteredTransitionCauseTruthConditionInstances => "
            "TC = independent_registered_transition_cause_truth_condition_instances) "
            ":= by",
            "  exact Exists.intro "
            "independent_registered_transition_cause_truth_condition_instances rfl",
            "",
            "theorem "
            "independent_registered_transition_cause_truth_condition_coverage_matches :",
            "    independent_registered_transition_cause_truth_condition_instances.",
            "      independent_registered_transition_cause_clause_coverage =",
            "        independent_registered_truth_condition_clause_coverage := by",
            "  exact independent_registered_transition_cause_truth_condition_instances.",
            "    independent_registered_transition_cause_clause_coverage_eq",
            "",
            "theorem "
            "independent_registered_transition_cause_truth_condition_transition_instance :",
            "    (theme : Entity) -> (scale : StateScale) ->",
            "    (source : State) -> (target : State) ->",
            "    RegisteredStateTransitionTruth theme scale source target ->",
            "    independent_registered_truth_condition_clause_instances.",
            "    independent_registered_clause_spec.",
            "    fully_registered_truth_denotes TransitionT",
            "      (Transition theme scale source target) := by",
            "  exact independent_registered_transition_cause_truth_condition_instances.",
            "    independent_registered_transition_cause_transition_instance",
            "",
            "theorem "
            "independent_registered_transition_cause_truth_condition_cause_instance :",
            "    (causer : Entity) -> (effect : TransitionT) ->",
            "    independent_registered_truth_condition_clause_instances.",
            "    independent_registered_clause_spec.",
            "    fully_registered_truth_denotes TransitionT effect ->",
            "    independent_registered_truth_condition_clause_instances.",
            "    independent_registered_clause_spec.",
            "    fully_registered_truth_denotes PropT (Cause causer effect) := by",
            "  exact independent_registered_transition_cause_truth_condition_instances.",
            "    independent_registered_transition_cause_cause_instance",
            "",
            "theorem "
            "independent_registered_transition_cause_truth_condition_spec_sound :",
            "    (A : Type) -> (term : A) ->",
            "    independent_registered_truth_condition_clause_instances.",
            "    independent_registered_clause_spec.",
            "    fully_registered_truth_denotes A term ->",
            "    AtomicClosureTruth A term := by",
            "  exact independent_registered_transition_cause_truth_condition_instances.",
            "    independent_registered_transition_cause_spec_sound",
        ]

    return [
        "Record IndependentRegisteredTransitionCauseTruthConditionInstances : Type := {",
        "  independent_registered_transition_cause_clause_coverage :",
        "      IndependentRegisteredTruthConditionClauseCoverage;",
        "  independent_registered_transition_cause_clause_coverage_eq :",
        "      independent_registered_transition_cause_clause_coverage =",
        "        independent_registered_truth_condition_clause_coverage;",
        "  independent_registered_transition_cause_transition_instance :",
        "    forall theme : Entity, forall scale : StateScale,",
        "    forall source : State, forall target : State,",
        "      RegisteredStateTransitionTruth theme scale source target ->",
        "      fully_registered_truth_denotes",
        "        (independent_registered_clause_spec",
        "          independent_registered_truth_condition_clause_instances)",
        "        TransitionT (Transition theme scale source target);",
        "  independent_registered_transition_cause_cause_instance :",
        "    forall causer : Entity, forall effect : TransitionT,",
        "      fully_registered_truth_denotes",
        "        (independent_registered_clause_spec",
        "          independent_registered_truth_condition_clause_instances)",
        "        TransitionT effect ->",
        "      fully_registered_truth_denotes",
        "        (independent_registered_clause_spec",
        "          independent_registered_truth_condition_clause_instances)",
        "        PropT (Cause causer effect);",
        "  independent_registered_transition_cause_spec_sound :",
        "    forall A : Type, forall term : A,",
        "      fully_registered_truth_denotes",
        "        (independent_registered_clause_spec",
        "          independent_registered_truth_condition_clause_instances) A term ->",
        "      AtomicClosureTruth A term",
        "}.",
        "",
        "Definition independent_registered_transition_cause_truth_condition_instances :",
        "  IndependentRegisteredTransitionCauseTruthConditionInstances := {|",
        "  independent_registered_transition_cause_clause_coverage :=",
        "    independent_registered_truth_condition_clause_coverage;",
        "  independent_registered_transition_cause_clause_coverage_eq := eq_refl;",
        "  independent_registered_transition_cause_transition_instance :=",
        "    independent_registered_truth_condition_clause_transition_instance;",
        "  independent_registered_transition_cause_cause_instance :=",
        "    independent_registered_truth_condition_clause_cause_instance;",
        "  independent_registered_transition_cause_spec_sound :=",
        "    independent_registered_clause_coverage_spec_sound",
        "      independent_registered_truth_condition_clause_coverage",
        "|}.",
        "",
        "Theorem independent_registered_transition_cause_truth_condition_instances_exists :",
        "  exists TC : IndependentRegisteredTransitionCauseTruthConditionInstances,",
        "    TC = independent_registered_transition_cause_truth_condition_instances.",
        "Proof.",
        "  exists independent_registered_transition_cause_truth_condition_instances.",
        "  reflexivity.",
        "Qed.",
        "",
        "Theorem independent_registered_transition_cause_truth_condition_coverage_matches :",
        "  independent_registered_transition_cause_clause_coverage",
        "    independent_registered_transition_cause_truth_condition_instances =",
        "  independent_registered_truth_condition_clause_coverage.",
        "Proof.",
        "  exact (independent_registered_transition_cause_clause_coverage_eq",
        "    independent_registered_transition_cause_truth_condition_instances).",
        "Qed.",
        "",
        "Theorem independent_registered_transition_cause_truth_condition_transition_instance :",
        "  forall theme : Entity, forall scale : StateScale,",
        "  forall source : State, forall target : State,",
        "    RegisteredStateTransitionTruth theme scale source target ->",
        "    fully_registered_truth_denotes",
        "      (independent_registered_clause_spec",
        "        independent_registered_truth_condition_clause_instances)",
        "      TransitionT (Transition theme scale source target).",
        "Proof.",
        "  exact (independent_registered_transition_cause_transition_instance",
        "    independent_registered_transition_cause_truth_condition_instances).",
        "Qed.",
        "",
        "Theorem independent_registered_transition_cause_truth_condition_cause_instance :",
        "  forall causer : Entity, forall effect : TransitionT,",
        "    fully_registered_truth_denotes",
        "      (independent_registered_clause_spec",
        "        independent_registered_truth_condition_clause_instances)",
        "      TransitionT effect ->",
        "    fully_registered_truth_denotes",
        "      (independent_registered_clause_spec",
        "        independent_registered_truth_condition_clause_instances)",
        "      PropT (Cause causer effect).",
        "Proof.",
        "  exact (independent_registered_transition_cause_cause_instance",
        "    independent_registered_transition_cause_truth_condition_instances).",
        "Qed.",
        "",
        "Theorem independent_registered_transition_cause_truth_condition_spec_sound :",
        "  forall A : Type, forall term : A,",
        "    fully_registered_truth_denotes",
        "      (independent_registered_clause_spec",
        "        independent_registered_truth_condition_clause_instances) A term ->",
        "    AtomicClosureTruth A term.",
        "Proof.",
        "  exact (independent_registered_transition_cause_spec_sound",
        "    independent_registered_transition_cause_truth_condition_instances).",
        "Qed.",
    ]


def independent_registered_truth_condition_instance_suite_lines(
    target: str,
) -> list[str]:
    """Gather the independent registered truth-condition subpackages."""

    packages = [
        (
            "lexical",
            "IndependentRegisteredLexicalTruthConditionInstances",
            "independent_registered_lexical_truth_condition_instances",
        ),
        (
            "temporal",
            "IndependentRegisteredTemporalTruthConditionInstances",
            "independent_registered_temporal_truth_condition_instances",
        ),
        (
            "sigma",
            "IndependentRegisteredSigmaTruthConditionInstances",
            "independent_registered_sigma_truth_condition_instances",
        ),
        (
            "repeat",
            "IndependentRegisteredRepeatTruthConditionInstances",
            "independent_registered_repeat_truth_condition_instances",
        ),
        (
            "polarity",
            "IndependentRegisteredPolarityTruthConditionInstances",
            "independent_registered_polarity_truth_condition_instances",
        ),
        (
            "transition_cause",
            "IndependentRegisteredTransitionCauseTruthConditionInstances",
            "independent_registered_transition_cause_truth_condition_instances",
        ),
    ]

    if target == "lean":
        lines = ["structure IndependentRegisteredTruthConditionInstanceSuite : Type where"]
        for field, type_name, _instance in packages:
            lines.extend(
                [
                    f"  independent_registered_suite_{field} :",
                    f"      {type_name}",
                ]
            )
        for field, _type_name, instance in packages:
            lines.extend(
                [
                    f"  independent_registered_suite_{field}_eq :",
                    f"      independent_registered_suite_{field} =",
                    f"        {instance}",
                ]
            )
        lines.extend(
            [
                "  independent_registered_suite_spec_sound :",
                "      (A : Type) -> (term : A) ->",
                "      independent_registered_truth_condition_clause_instances.",
                "      independent_registered_clause_spec.",
                "      fully_registered_truth_denotes A term ->",
                "      AtomicClosureTruth A term",
                "",
                "def independent_registered_truth_condition_instance_suite :",
                "    IndependentRegisteredTruthConditionInstanceSuite := {",
            ]
        )
        for field, _type_name, instance in packages:
            lines.extend(
                [
                    f"  independent_registered_suite_{field} :=",
                    f"    {instance},",
                ]
            )
        for field, _type_name, _instance in packages:
            lines.append(f"  independent_registered_suite_{field}_eq := rfl,")
        lines.extend(
            [
                "  independent_registered_suite_spec_sound :=",
                "    independent_registered_truth_condition_clause_coverage."
                "independent_registered_clause_coverage_spec_sound",
                "}",
                "",
                "theorem independent_registered_truth_condition_instance_suite_exists :",
                "    Exists (fun S : "
                "IndependentRegisteredTruthConditionInstanceSuite => "
                "S = independent_registered_truth_condition_instance_suite) := by",
                "  exact Exists.intro "
                "independent_registered_truth_condition_instance_suite rfl",
            ]
        )
        for field, _type_name, instance in packages:
            lines.extend(
                [
                    "",
                    "theorem "
                    f"independent_registered_truth_condition_instance_suite_{field}_matches :",
                    "    independent_registered_truth_condition_instance_suite.",
                    f"      independent_registered_suite_{field} =",
                    f"        {instance} := by",
                    "  exact independent_registered_truth_condition_instance_suite.",
                    f"    independent_registered_suite_{field}_eq",
                ]
            )
        lines.extend(
            [
                "",
                "theorem "
                "independent_registered_truth_condition_instance_suite_spec_sound :",
                "    (A : Type) -> (term : A) ->",
                "    independent_registered_truth_condition_clause_instances.",
                "    independent_registered_clause_spec.",
                "    fully_registered_truth_denotes A term ->",
                "    AtomicClosureTruth A term := by",
                "  exact independent_registered_truth_condition_instance_suite.",
                "    independent_registered_suite_spec_sound",
            ]
        )
        return lines

    lines = ["Record IndependentRegisteredTruthConditionInstanceSuite : Type := {"]
    fields: list[list[str]] = []
    for field, type_name, _instance in packages:
        fields.append(
            [
                f"  independent_registered_suite_{field} :",
                f"      {type_name}",
            ]
        )
    for field, _type_name, instance in packages:
        fields.append(
            [
                f"  independent_registered_suite_{field}_eq :",
                f"      independent_registered_suite_{field} =",
                f"        {instance}",
            ]
        )
    fields.append(
        [
            "  independent_registered_suite_spec_sound :",
            "    forall A : Type, forall term : A,",
            "      fully_registered_truth_denotes",
            "        (independent_registered_clause_spec",
            "          independent_registered_truth_condition_clause_instances) A term ->",
            "      AtomicClosureTruth A term",
        ]
    )
    for idx, field_lines in enumerate(fields):
        is_last = idx == len(fields) - 1
        for field_idx, field_line in enumerate(field_lines):
            if field_idx == len(field_lines) - 1 and not is_last:
                lines.append(f"{field_line};")
            else:
                lines.append(field_line)
    lines.extend(
        [
            "}.",
            "",
            "Definition independent_registered_truth_condition_instance_suite :",
            "  IndependentRegisteredTruthConditionInstanceSuite := {|",
        ]
    )
    for field, _type_name, instance in packages:
        lines.extend(
            [
                f"  independent_registered_suite_{field} :=",
                f"    {instance};",
            ]
        )
    for field, _type_name, _instance in packages:
        lines.append(f"  independent_registered_suite_{field}_eq := eq_refl;")
    lines.extend(
        [
            "  independent_registered_suite_spec_sound :=",
            "    independent_registered_clause_coverage_spec_sound",
            "      independent_registered_truth_condition_clause_coverage",
            "|}.",
            "",
            "Theorem independent_registered_truth_condition_instance_suite_exists :",
            "  exists S : IndependentRegisteredTruthConditionInstanceSuite,",
            "    S = independent_registered_truth_condition_instance_suite.",
            "Proof.",
            "  exists independent_registered_truth_condition_instance_suite.",
            "  reflexivity.",
            "Qed.",
        ]
    )
    for field, _type_name, instance in packages:
        lines.extend(
            [
                "",
                "Theorem "
                f"independent_registered_truth_condition_instance_suite_{field}_matches :",
                f"  independent_registered_suite_{field}",
                "    independent_registered_truth_condition_instance_suite =",
                f"  {instance}.",
                "Proof.",
                f"  exact (independent_registered_suite_{field}_eq",
                "    independent_registered_truth_condition_instance_suite).",
                "Qed.",
            ]
        )
    lines.extend(
        [
            "",
            "Theorem independent_registered_truth_condition_instance_suite_spec_sound :",
            "  forall A : Type, forall term : A,",
            "    fully_registered_truth_denotes",
            "      (independent_registered_clause_spec",
            "        independent_registered_truth_condition_clause_instances) A term ->",
            "    AtomicClosureTruth A term.",
            "Proof.",
            "  exact (independent_registered_suite_spec_sound",
            "    independent_registered_truth_condition_instance_suite).",
            "Qed.",
        ]
    )
    return lines


def independent_registered_truth_condition_instance_suite_example_package_lines(
    results: list[dict[str, Any]],
    target: str,
) -> list[str]:
    """Package suite-level atomic projections for exported examples."""

    if target == "lean":
        lines = [
            "structure "
            "IndependentRegisteredTruthConditionInstanceSuiteExamplePackage : "
            "Type where",
            "  independent_registered_suite_example_suite :",
            "      IndependentRegisteredTruthConditionInstanceSuite",
            "  independent_registered_suite_example_suite_eq :",
            "      independent_registered_suite_example_suite =",
            "        independent_registered_truth_condition_instance_suite",
        ]
        for idx, result in enumerate(results, 1):
            annotation = export_result_type(result["ast"])
            lines.append(
                f"  example_{idx}_suite_atomic_sound : "
                f"AtomicClosureTruth {annotation} example_{idx}"
            )
        lines.extend(
            [
                "",
                "def independent_registered_truth_condition_instance_suite_example_package :",
                "    IndependentRegisteredTruthConditionInstanceSuiteExamplePackage := {",
                "  independent_registered_suite_example_suite :=",
                "    independent_registered_truth_condition_instance_suite,",
                "  independent_registered_suite_example_suite_eq := rfl,",
            ]
        )
        for idx in range(1, len(results) + 1):
            suffix = "," if idx < len(results) else ""
            lines.append(
                f"  example_{idx}_suite_atomic_sound :="
                " independent_registered_truth_condition_clause_coverage_example_"
                f"{idx}_atomic_sound{suffix}"
            )
        lines.extend(
            [
                "}",
                "",
                "theorem "
                "independent_registered_truth_condition_instance_suite_example_package_exists :",
                "    Exists (fun P : "
                "IndependentRegisteredTruthConditionInstanceSuiteExamplePackage =>",
                "      P = "
                "independent_registered_truth_condition_instance_suite_example_package)"
                " := by",
                "  exact Exists.intro "
                "independent_registered_truth_condition_instance_suite_example_package "
                "rfl",
                "",
                "theorem "
                "independent_registered_truth_condition_instance_suite_example_package_suite_matches :",
                "    independent_registered_truth_condition_instance_suite_example_package.",
                "      independent_registered_suite_example_suite =",
                "        independent_registered_truth_condition_instance_suite := by",
                "  exact "
                "independent_registered_truth_condition_instance_suite_example_package.",
                "    independent_registered_suite_example_suite_eq",
            ]
        )
        for idx, result in enumerate(results, 1):
            annotation = export_result_type(result["ast"])
            lines.extend(
                [
                    "",
                    "theorem "
                    f"independent_registered_truth_condition_instance_suite_example_{idx}_atomic_sound :",
                    f"    AtomicClosureTruth {annotation} example_{idx} := by",
                    "  exact "
                    "independent_registered_truth_condition_instance_suite_example_package.",
                    f"    example_{idx}_suite_atomic_sound",
                ]
            )
        return lines

    lines = [
        "Record IndependentRegisteredTruthConditionInstanceSuiteExamplePackage : "
        "Type := {",
        "  independent_registered_suite_example_suite :",
        "      IndependentRegisteredTruthConditionInstanceSuite;",
        "  independent_registered_suite_example_suite_eq :",
        "      independent_registered_suite_example_suite =",
        "        independent_registered_truth_condition_instance_suite;",
    ]
    for idx, result in enumerate(results, 1):
        annotation = export_result_type(result["ast"])
        suffix = ";" if idx < len(results) else ""
        lines.extend(
            [
                f"  example_{idx}_suite_atomic_sound :",
                f"      AtomicClosureTruth {annotation} example_{idx}{suffix}",
            ]
        )
    lines.extend(
        [
            "}.",
            "",
            "Definition "
            "independent_registered_truth_condition_instance_suite_example_package :",
            "  IndependentRegisteredTruthConditionInstanceSuiteExamplePackage := {|",
            "  independent_registered_suite_example_suite :=",
            "    independent_registered_truth_condition_instance_suite;",
            "  independent_registered_suite_example_suite_eq := eq_refl;",
        ]
    )
    for idx in range(1, len(results) + 1):
        suffix = ";" if idx < len(results) else ""
        lines.append(
            f"  example_{idx}_suite_atomic_sound :="
            " independent_registered_truth_condition_clause_coverage_example_"
            f"{idx}_atomic_sound{suffix}"
        )
    lines.extend(
        [
            "|}.",
            "",
            "Theorem "
            "independent_registered_truth_condition_instance_suite_example_package_exists :",
            "  exists P : "
            "IndependentRegisteredTruthConditionInstanceSuiteExamplePackage,",
            "    P = "
            "independent_registered_truth_condition_instance_suite_example_package.",
            "Proof.",
            "  exists "
            "independent_registered_truth_condition_instance_suite_example_package.",
            "  reflexivity.",
            "Qed.",
            "",
            "Theorem "
            "independent_registered_truth_condition_instance_suite_example_package_suite_matches :",
            "  independent_registered_suite_example_suite",
            "    independent_registered_truth_condition_instance_suite_example_package =",
            "  independent_registered_truth_condition_instance_suite.",
            "Proof.",
            "  exact (independent_registered_suite_example_suite_eq",
            "    independent_registered_truth_condition_instance_suite_example_package).",
            "Qed.",
        ]
    )
    for idx, result in enumerate(results, 1):
        annotation = export_result_type(result["ast"])
        lines.extend(
            [
                "",
                "Theorem "
                f"independent_registered_truth_condition_instance_suite_example_{idx}_atomic_sound :",
                f"  AtomicClosureTruth {annotation} example_{idx}.",
                "Proof.",
                f"  exact (example_{idx}_suite_atomic_sound",
                "    independent_registered_truth_condition_instance_suite_example_package).",
                "Qed.",
            ]
        )
    return lines


def typed_application_argument_types(
    function: str,
    arguments: list[str],
    target: str,
    bound_types: dict[str, str],
) -> list[str]:
    if function in OMITTED_THEME_TYPES and len(arguments) >= 2:
        types = ["Entity"] * len(arguments)
        types[-1] = export_type_name(OMITTED_THEME_TYPES[function], target)
    else:
        types = ["Entity"] * len(arguments)
    return [
        bound_types.get(export_atom(argument, target), argument_type)
        for argument, argument_type in zip(arguments, types)
    ]


def modifier_type() -> str:
    return "Adv"


def add_constant_declaration(constants: dict[str, str], name: str, type_name: str) -> None:
    existing = constants.get(name)
    if existing is not None and existing != type_name:
        raise ValueError(
            f"Conflicting export types for constant {name}: {existing} vs {type_name}"
        )
    constants[name] = type_name


def add_function_declaration(
    functions: dict[str, tuple[list[str], str]],
    name: str,
    signature: tuple[list[str], str],
) -> None:
    existing = functions.get(name)
    if existing is not None and existing != signature:
        raise ValueError(
            f"Conflicting export signatures for function {name}: {existing} vs {signature}"
        )
    functions[name] = signature


def _identifier_fragment(value: str) -> str:
    fragment = re.sub(r"[^0-9A-Za-z_]+", "_", value).strip("_")
    if not fragment:
        fragment = "anon"
    return fragment


def registered_lexical_application_constructor_from_schema(
    schema: LexicalApplicationSchema,
) -> str:
    function, _result_type, adverb_count, _modifier_term, modifiers, arguments, _binders = schema
    fragments = [function, str(adverb_count), *modifiers, *arguments]
    return "registered_lexical_" + "_".join(
        _identifier_fragment(fragment) for fragment in fragments
    )


def lexical_application_term(schema: LexicalApplicationSchema) -> str:
    function, _result_type, adverb_count, modifier_term, _modifiers, arguments, _binders = schema
    return " ".join([function, str(adverb_count), modifier_term, *arguments])


def lexical_application_schema(
    term: Term,
    target: str,
    bound_types: dict[str, str],
) -> LexicalApplicationSchema:
    function = export_atom(term["function"], target)
    modifiers = tuple(export_atom(value, target) for value in term["modifiers"])
    arguments = tuple(export_atom(value, target) for value in term["arguments"])
    binders: list[tuple[str, str]] = []
    seen_binders: set[str] = set()
    for argument in arguments:
        if argument in bound_types and argument not in seen_binders:
            binders.append((argument, bound_types[argument]))
            seen_binders.add(argument)
    return (
        function,
        application_result_type(function),
        int(term["adverb_count"]),
        export_modifier_sequence(term["modifier_vector"], target),
        modifiers,
        arguments,
        tuple(binders),
    )


def collect_term_declarations(
    term: Term,
    target: str,
    functions: dict[str, tuple[list[str], str]],
    constants: dict[str, str],
    modifiers: set[str],
    types: set[str],
    transitions: set[tuple[str, str, str, str]],
    lexical_applications: set[LexicalApplicationSchema],
    bound_types: dict[str, str] | None = None,
) -> None:
    bound_types = {} if bound_types is None else bound_types
    kind = term["kind"]
    if kind == "application":
        function = export_atom(term["function"], target)
        argument_types = typed_application_argument_types(
            function,
            term["arguments"],
            target,
            bound_types,
        )
        types.update(argument_type for argument_type in argument_types if argument_type != "Entity")
        add_function_declaration(
            functions,
            function,
            (
                (
                    ["forall n : nat, ModifierSeq n"]
                    if target == "coq"
                    else ["(n : Nat)", "ModifierSeq n"]
                )
                + argument_types,
                application_result_type(function),
            ),
        )
        for value in term["modifiers"]:
            exported = export_atom(value, target)
            if exported not in bound_types:
                modifiers.add(exported)
        for value, argument_type in zip(term["arguments"], argument_types):
            exported = export_atom(value, target)
            if exported not in bound_types:
                add_constant_declaration(constants, exported, argument_type)
        lexical_applications.add(
            lexical_application_schema(term, target, bound_types)
        )
        return
    if kind == "sigma":
        witness = export_atom(term["witness"], target)
        witness_type = export_type_name(term["type"], target)
        types.add(witness_type)
        collect_term_declarations(
            term["body"],
            target,
            functions,
            constants,
            modifiers,
            types,
            transitions,
            lexical_applications,
            {**bound_types, witness: witness_type},
        )
        return
    if kind == "repeat":
        collect_term_declarations(
            term["body"],
            target,
            functions,
            constants,
            modifiers,
            types,
            transitions,
            lexical_applications,
            bound_types,
        )
        return
    if kind == "time":
        for value in term["arguments"]:
            exported = export_atom(value, target)
            if exported not in bound_types:
                add_constant_declaration(constants, exported, "Entity")
        collect_term_declarations(
            term["body"],
            target,
            functions,
            constants,
            modifiers,
            types,
            transitions,
            lexical_applications,
            bound_types,
        )
        return
    if kind == "not":
        collect_term_declarations(
            term["body"],
            target,
            functions,
            constants,
            modifiers,
            types,
            transitions,
            lexical_applications,
            bound_types,
        )
        return
    if kind == "transition":
        theme = export_atom(term["theme"], target)
        if theme not in bound_types:
            add_constant_declaration(constants, theme, "Entity")
        state_scale = export_atom(term["state_scale"], target)
        if state_scale not in bound_types:
            add_constant_declaration(constants, state_scale, "StateScale")
        for field in ("source_state", "target_state"):
            exported = export_atom(term[field], target)
            if exported not in bound_types:
                add_constant_declaration(constants, exported, "State")
        transitions.add(
            (
                theme,
                state_scale,
                export_atom(term["source_state"], target),
                export_atom(term["target_state"], target),
            )
        )
        return
    if kind == "cause":
        causer = export_atom(term["causer"], target)
        if causer not in bound_types:
            add_constant_declaration(constants, causer, "Entity")
        collect_term_declarations(
            term["effect"],
            target,
            functions,
            constants,
            modifiers,
            types,
            transitions,
            lexical_applications,
            bound_types,
        )
        activity = term.get("activity")
        if activity is not None:
            collect_term_declarations(
                activity,
                target,
                functions,
                constants,
                modifiers,
                types,
                transitions,
                lexical_applications,
                bound_types,
            )
        return
    raise ValueError(f"Unknown term kind: {kind!r}")


def module_declarations(results: list[dict[str, Any]], target: str) -> dict[str, Any]:
    functions: dict[str, tuple[list[str], str]] = {}
    constants: dict[str, str] = {}
    modifiers: set[str] = set()
    transitions: set[tuple[str, str, str, str]] = set()
    lexical_applications: set[LexicalApplicationSchema] = set()
    types = {"Entity", "Food", "State", "StateScale", "TransitionT"}
    for result in results:
        collect_term_declarations(
            result["ast"],
            target,
            functions,
            constants,
            modifiers,
            types,
            transitions,
            lexical_applications,
        )
    return {
        "types": sorted(types),
        "constants": sorted(constants.items()),
        "modifiers": sorted(modifiers),
        "functions": functions,
        "transitions": sorted(transitions),
        "lexical_applications": sorted(lexical_applications),
    }


def export_module(results: list[dict[str, Any]], target: str) -> str:
    if target not in EXPORT_TARGETS:
        raise ValueError(f"Unsupported export target: {target!r}")
    for idx, result in enumerate(results):
        if not result.get("type_check", {}).get("ok"):
            raise ValueError(f"Cannot export result {idx}: type_check failed")

    declarations = module_declarations(results, target)

    if target == "lean":
        lines = [
            "-- Auto-generated shallow embedding for dependent-type event semantics.",
            "-- This file is an interface scaffold, not a complete proof development.",
            "",
        ]
        lines.extend(f"constant {name} : Type" for name in declarations["types"])
        lines.append("abbrev PropT : Type := Prop")
        lines.append("def Adv : Type := (Entity -> PropT) -> Entity -> PropT")
        lines.append("constant ModifierSeq : Nat -> Type")
        lines.append("constant mods_nil : ModifierSeq 0")
        lines.append(
            "constant mods_cons : (n : Nat) -> Adv -> ModifierSeq n -> ModifierSeq (Nat.succ n)"
        )
        lines.append("")
        lines.extend(
            f"constant {name} : {type_name}" for name, type_name in declarations["constants"]
        )
        lines.extend(
            f"constant {name} : Adv" for name in declarations["modifiers"]
        )
        lines.extend(
            [
                "",
                "inductive ObligationStatus : Type",
                "  | pending",
                "  | shallow_checked",
                "  | proved",
                "",
                "structure SemanticPreservationObligation : Type where",
                "  obligation_statement : Prop",
                "  obligation_status : ObligationStatus",
                "",
                "constant repeat : Nat -> PropT -> PropT",
                "constant at_T : Entity -> PropT -> PropT",
                "constant during_T : Entity -> PropT -> PropT",
                "constant before_T : Entity -> PropT -> PropT",
                "constant after_T : Entity -> PropT -> PropT",
                "constant until_T : Entity -> PropT -> PropT",
                "constant since_T : Entity -> PropT -> PropT",
                "constant not_T : PropT -> PropT",
                "constant Transition : Entity -> StateScale -> State -> State -> TransitionT",
                "constant Cause : Entity -> TransitionT -> PropT",
            ]
        )
        for name, (arg_types, result_type) in sorted(declarations["functions"].items()):
            signature = " -> ".join(arg_types + [result_type])
            lines.append(f"constant {name} : {signature}")
        lines.append("")
        lines.extend(semantic_preservation_relation_lines(declarations, target))
        lines.append("")
        lines.extend(model_interpretability_relation_lines(declarations, target))
        lines.append("")
        lines.extend(syntax_directed_truth_relation_lines(declarations, target))
        lines.extend(
            [
                "",
                "theorem semantic_preservation_model_interpretable :",
                "    (A : Type) -> (term : A) -> "
                "SemanticPreservation A term -> ModelInterpretable A term := by",
                "  intro A term h",
                "  induction h <;> constructor <;> assumption",
                "",
                "theorem semantic_preservation_syntax_directed_truth :",
                "    (A : Type) -> (term : A) -> "
                "SemanticPreservation A term -> SyntaxDirectedTruth A term := by",
                "  intro A term h",
                "  induction h <;> constructor <;> assumption",
                "",
            ]
        )
        lines.extend(semantic_model_record_lines(declarations, target))
        lines.extend(
            [
                "",
                "theorem model_interpretable_denotational_sound :",
                "    (M : SemanticModel) -> (A : Type) -> (term : A) -> "
                "ModelInterpretable A term -> M.model_denotes A term := by",
                "  intro M A term h",
                "  induction h",
            ]
        )
        for name, (arg_types, _result_type) in sorted(declarations["functions"].items()):
            constructor = model_application_constructor(name)
            projection = denotation_application_field(name)
            remaining_arg_types = (
                arg_types[2:]
                if arg_types[:2] == ["(n : Nat)", "ModifierSeq n"]
                else arg_types
            )
            ordinary_args = [
                f"arg{index}"
                for index, _arg_type in enumerate(remaining_arg_types, 1)
            ]
            pattern_args = " ".join(["n", "mods", *ordinary_args])
            projection_args = " ".join(["n", "mods", *ordinary_args])
            lines.append(
                f"  | {constructor} {pattern_args} "
                f"=> exact M.{projection} {projection_args}"
            )
        for type_name in declarations["types"]:
            constructor = model_sigma_constructor(type_name)
            projection = denotation_sigma_field(type_name)
            lines.append(
                f"  | {constructor} P h ih => exact M.{projection} P ih"
            )
        lines.extend(
            [
                "  | model_repeat n body h ih => exact M.denote_repeat n body ih",
                "  | model_at_T marker body h ih => exact M.denote_at_T marker body ih",
                "  | model_during_T marker body h ih => exact M.denote_during_T marker body ih",
                "  | model_before_T marker body h ih => exact M.denote_before_T marker body ih",
                "  | model_after_T marker body h ih => exact M.denote_after_T marker body ih",
                "  | model_until_T marker body h ih => exact M.denote_until_T marker body ih",
                "  | model_since_T marker body h ih => exact M.denote_since_T marker body ih",
                "  | model_not_T body h ih => exact M.denote_not_T body ih",
                "  | model_transition theme scale source target => exact M.denote_transition theme scale source target",
                "  | model_cause causer effect h ih => exact M.denote_cause causer effect ih",
                "",
            ]
        )
        lines.extend(truth_condition_spec_record_lines(declarations, target))
        lines.append("")
        lines.extend(semantic_model_from_truth_conditions_lines(declarations, target))
        lines.append("")
        lines.extend(concrete_truth_condition_kernel_lines(declarations, target))
        lines.append("")
        lines.extend(
            independent_truth_condition_obligation_ledger_lines(declarations, target)
        )
        lines.append("")
        lines.extend(evidence_backed_truth_condition_source_lines(declarations, target))
        lines.append("")
        lines.extend(primitive_truth_assumption_kernel_lines(declarations, target))
        lines.append("")
        lines.extend(atomic_closure_truth_kernel_lines(declarations, target))
        lines.append("")
        lines.extend(
            atomic_closure_evidence_backed_truth_source_lines(declarations, target)
        )
        lines.append("")
        lines.extend(transition_refined_atomic_closure_truth_lines(declarations, target))
        lines.append("")
        lines.extend(registered_truth_condition_spec_lines(declarations, target))
        lines.append("")
        lines.extend(registered_lexical_truth_condition_spec_lines(declarations, target))
        lines.append("")
        lines.extend(registered_lexical_truth_model_lines(declarations, target))
        lines.append("")
        lines.extend(concrete_registered_truth_condition_instance_lines(declarations, target))
        lines.append("")
        lines.extend(
            registered_evidence_backed_truth_condition_source_lines(
                declarations,
                target,
            )
        )
        lines.append("")
        lines.extend(
            concrete_registered_evidence_backed_truth_condition_model_lines(target)
        )
        lines.append("")
        lines.extend(concrete_registered_truth_kernel_lines(declarations, target))
        lines.append("")
        lines.extend(concrete_truth_condition_kernel_instance_lines(declarations, target))
        lines.append("")
        lines.extend(syntax_directed_truth_kernel_instance_lines(declarations, target))
        lines.append("")
        lines.extend(truth_condition_instance_lines(declarations, target))
        lines.append("")
        lines.append(
            "def PreservationTargetMatches (A : Type) (term : A) (target : SemanticPreservationObligation) : Prop :="
        )
        lines.append("  target.obligation_statement = SemanticPreservation A term")
        lines.append("")
        for idx, result in enumerate(results, 1):
            expr = result["exports"][target]
            annotation = export_result_type(result["ast"])
            lines.append(f"def example_{idx} : {annotation} := {expr}")
        lines.append("")
        for idx, result in enumerate(results, 1):
            annotation = export_result_type(result["ast"])
            lines.append(
                "def "
                f"example_{idx}_semantic_preservation_obligation : Prop := "
                f"SemanticPreservation {annotation} example_{idx}"
            )
        lines.append("")
        for idx in range(1, len(results) + 1):
            lines.append(
                "def "
                f"example_{idx}_semantic_preservation_obligation_record : "
                "SemanticPreservationObligation := {"
            )
            lines.append(
                "  obligation_statement := "
                f"example_{idx}_semantic_preservation_obligation,"
            )
            lines.append(
                "  obligation_status := ObligationStatus.proved"
            )
            lines.append("}")
        lines.append("")
        for idx in range(1, len(results) + 1):
            lines.append(
                "theorem "
                f"example_{idx}_semantic_preservation_obligation_is_prop :"
            )
            lines.append(
                "    Exists (fun P : Prop => "
                f"P = example_{idx}_semantic_preservation_obligation) := by"
            )
            lines.append(
                "  exact Exists.intro "
                f"example_{idx}_semantic_preservation_obligation rfl"
            )
        lines.append("")
        for idx, result in enumerate(results, 1):
            annotation = export_result_type(result["ast"])
            lines.append(
                "theorem "
                f"example_{idx}_semantic_preservation_target_matches :"
            )
            lines.append(
                "    PreservationTargetMatches "
                f"{annotation} example_{idx} "
                f"example_{idx}_semantic_preservation_obligation_record := by"
            )
            lines.append("  rfl")
        lines.append("")
        for idx, result in enumerate(results, 1):
            lines.append(
                "theorem "
                f"example_{idx}_semantic_preservation_proved : "
                f"example_{idx}_semantic_preservation_obligation := by"
            )
            lines.append(f"  unfold example_{idx}_semantic_preservation_obligation")
            lines.append(f"  unfold example_{idx}")
            lines.extend(semantic_preservation_proof_steps(result["ast"], target))
        lines.append("")
        for idx, result in enumerate(results, 1):
            annotation = export_result_type(result["ast"])
            lines.append(
                "theorem "
                f"example_{idx}_model_interpretable : "
                f"ModelInterpretable {annotation} example_{idx} := by"
            )
            lines.append("  apply semantic_preservation_model_interpretable")
            lines.append(f"  exact example_{idx}_semantic_preservation_proved")
        lines.append("")
        for idx, result in enumerate(results, 1):
            annotation = export_result_type(result["ast"])
            lines.append(
                "theorem "
                f"example_{idx}_syntax_directed_truth : "
                f"SyntaxDirectedTruth {annotation} example_{idx} := by"
            )
            lines.append("  apply semantic_preservation_syntax_directed_truth")
            lines.append(f"  exact example_{idx}_semantic_preservation_proved")
        lines.append("")
        for idx, result in enumerate(results, 1):
            annotation = export_result_type(result["ast"])
            lines.append(
                "theorem "
                f"example_{idx}_denotationally_sound : "
                f"(M : SemanticModel) -> M.model_denotes {annotation} example_{idx} := by"
            )
            lines.append("  intro M")
            lines.append("  apply model_interpretable_denotational_sound")
            lines.append(f"  exact example_{idx}_model_interpretable")
        lines.append("")
        for idx, result in enumerate(results, 1):
            annotation = export_result_type(result["ast"])
            lines.append(
                "theorem "
                f"example_{idx}_truth_condition_sound : "
                f"(T : TruthConditionSpec) -> T.truth_denotes {annotation} example_{idx} := by"
            )
            lines.append("  intro T")
            lines.append("  apply truth_conditions_induce_denotational_soundness")
            lines.append(f"  exact example_{idx}_model_interpretable")
        lines.append("")
        for idx, result in enumerate(results, 1):
            annotation = export_result_type(result["ast"])
            lines.append(
                "theorem "
                f"example_{idx}_tautological_truth_condition_sound : "
                f"tautological_truth_conditions.truth_denotes {annotation} example_{idx} := by"
            )
            lines.append("  apply tautological_truth_conditions_denote_model_interpretable")
            lines.append(f"  exact example_{idx}_model_interpretable")
        lines.append("")
        for idx, result in enumerate(results, 1):
            annotation = export_result_type(result["ast"])
            lines.append(
                "theorem "
                f"example_{idx}_structural_truth_condition_sound : "
                f"structural_truth_conditions.truth_denotes {annotation} example_{idx} := by"
            )
            lines.append("  apply structural_truth_conditions_denote_model_interpretable")
            lines.append(f"  exact example_{idx}_model_interpretable")
        lines.append("")
        for idx, result in enumerate(results, 1):
            annotation = export_result_type(result["ast"])
            lines.append(
                "theorem "
                f"example_{idx}_concrete_kernel_truth_condition_sound : "
                f"(K : ConcreteTruthConditionKernel) -> "
                f"(truth_conditions_from_concrete_kernel K).truth_denotes "
                f"{annotation} example_{idx} := by"
            )
            lines.append("  intro K")
            lines.append("  apply concrete_kernel_induces_truth_condition_soundness")
            lines.append(f"  exact example_{idx}_model_interpretable")
        lines.append("")
        for idx, result in enumerate(results, 1):
            annotation = export_result_type(result["ast"])
            lines.append(
                "theorem "
                f"example_{idx}_model_interpretable_truth_kernel_sound : "
                "(truth_conditions_from_concrete_kernel "
                f"model_interpretable_truth_kernel).truth_denotes "
                f"{annotation} example_{idx} := by"
            )
            lines.append("  apply model_interpretable_truth_kernel_denotes_model_interpretable")
            lines.append(f"  exact example_{idx}_model_interpretable")
        lines.append("")
        for idx, result in enumerate(results, 1):
            annotation = export_result_type(result["ast"])
            lines.append(
                "theorem "
                f"example_{idx}_syntax_directed_truth_kernel_sound : "
                "(truth_conditions_from_concrete_kernel "
                f"syntax_directed_truth_kernel).truth_denotes "
                f"{annotation} example_{idx} := by"
            )
            lines.append("  apply syntax_directed_truth_kernel_denotes_syntax_directed_truth")
            lines.append(f"  exact example_{idx}_syntax_directed_truth")
        lines.append("")
        for idx, result in enumerate(results, 1):
            annotation = export_result_type(result["ast"])
            lines.append(
                "theorem "
                f"example_{idx}_primitive_truth_kernel_sound : "
                "(truth_conditions_from_concrete_kernel "
                f"primitive_truth_kernel).truth_denotes "
                f"{annotation} example_{idx} := by"
            )
            lines.append("  apply primitive_truth_kernel_denotes_model_interpretable")
            lines.append(f"  exact example_{idx}_model_interpretable")
        lines.append("")
        for idx, result in enumerate(results, 1):
            annotation = export_result_type(result["ast"])
            lines.append(
                "theorem "
                f"example_{idx}_atomic_closure_truth : "
                f"AtomicClosureTruth {annotation} example_{idx} := by"
            )
            lines.append("  apply model_interpretable_atomic_closure_truth")
            lines.append(f"  exact example_{idx}_model_interpretable")
        lines.append("")
        for idx, result in enumerate(results, 1):
            annotation = export_result_type(result["ast"])
            lines.append(
                "theorem "
                f"example_{idx}_atomic_closure_truth_kernel_sound : "
                "(truth_conditions_from_concrete_kernel "
                f"atomic_closure_truth_kernel).truth_denotes "
                f"{annotation} example_{idx} := by"
            )
            lines.append("  apply atomic_closure_truth_kernel_denotes_atomic_closure_truth")
            lines.append(f"  exact example_{idx}_atomic_closure_truth")
        lines.append("")
        for idx, result in enumerate(results, 1):
            annotation = export_result_type(result["ast"])
            lines.append(
                "theorem "
                f"example_{idx}_atomic_closure_truth_condition_sound : "
                "atomic_closure_truth_conditions.truth_denotes "
                f"{annotation} example_{idx} := by"
            )
            lines.append("  apply atomic_closure_truth_conditions_denote_atomic_closure_truth")
            lines.append(f"  exact example_{idx}_atomic_closure_truth")
        lines.append("")
        for idx, result in enumerate(results, 1):
            annotation = export_result_type(result["ast"])
            lines.append(
                "theorem "
                f"example_{idx}_atomic_closure_evidence_backed_truth_condition_sound : "
                "atomic_closure_evidence_backed_truth_ledger."
                "ledger_truth_conditions.truth_denotes "
                f"{annotation} example_{idx} := by"
            )
            lines.append(
                "  apply atomic_closure_evidence_backed_truth_sources_sound"
            )
            lines.append(f"  exact example_{idx}_model_interpretable")
        lines.append("")
        for idx, result in enumerate(results, 1):
            annotation = export_result_type(result["ast"])
            lines.append(
                "theorem "
                f"example_{idx}_transition_refined_atomic_closure_truth : "
                f"TransitionRefinedAtomicClosureTruth {annotation} example_{idx} := by"
            )
            lines.append(f"  unfold example_{idx}")
            lines.extend(
                transition_refined_atomic_closure_proof_steps(
                    result["ast"],
                    target,
                )
            )
        lines.append("")
        for idx, result in enumerate(results, 1):
            annotation = export_result_type(result["ast"])
            lines.append(
                "theorem "
                f"example_{idx}_transition_refined_atomic_closure_sound : "
                f"AtomicClosureTruth {annotation} example_{idx} := by"
            )
            lines.append(
                "  apply "
                "transition_refined_atomic_closure_truth_implies_atomic_closure_truth"
            )
            lines.append(
                f"  exact example_{idx}_transition_refined_atomic_closure_truth"
            )
        lines.append("")
        for idx, result in enumerate(results, 1):
            annotation = export_result_type(result["ast"])
            lines.append(
                "theorem "
                f"example_{idx}_transition_refined_registered_truth_condition_sound : "
                "transition_refined_registered_truth_conditions."
                "registered_truth_denotes "
                f"{annotation} example_{idx} := by"
            )
            lines.append(
                "  apply "
                "transition_refined_registered_truth_conditions_denote_transition_refined"
            )
            lines.append(
                f"  exact example_{idx}_transition_refined_atomic_closure_truth"
            )
        lines.append("")
        for idx, result in enumerate(results, 1):
            annotation = export_result_type(result["ast"])
            lines.append(
                "theorem "
                f"example_{idx}_transition_refined_registered_truth_condition_atomic_sound : "
                f"AtomicClosureTruth {annotation} example_{idx} := by"
            )
            lines.append(
                "  apply "
                "transition_refined_registered_truth_conditions_imply_atomic_closure"
            )
            lines.append(
                f"  exact example_{idx}_transition_refined_registered_truth_condition_sound"
            )
        lines.append("")
        for idx, result in enumerate(results, 1):
            annotation = export_result_type(result["ast"])
            lines.append(
                "theorem "
                f"example_{idx}_fully_registered_atomic_closure_truth : "
                f"FullyRegisteredAtomicClosureTruth {annotation} example_{idx} := by"
            )
            lines.append(f"  unfold example_{idx}")
            lines.extend(
                fully_registered_atomic_closure_proof_steps(
                    result["ast"],
                    target,
                )
            )
        lines.append("")
        for idx, result in enumerate(results, 1):
            annotation = export_result_type(result["ast"])
            lines.append(
                "theorem "
                f"example_{idx}_fully_registered_truth_condition_sound : "
                "fully_registered_truth_conditions."
                "fully_registered_truth_denotes "
                f"{annotation} example_{idx} := by"
            )
            lines.append(
                "  apply "
                "fully_registered_truth_conditions_denote_fully_registered"
            )
            lines.append(
                f"  exact example_{idx}_fully_registered_atomic_closure_truth"
            )
        lines.append("")
        lines.extend(registered_lexical_truth_model_example_lines(results, target))
        lines.append("")
        for idx, result in enumerate(results, 1):
            annotation = export_result_type(result["ast"])
            lines.append(
                "theorem "
                f"example_{idx}_concrete_registered_truth : "
                f"ConcreteRegisteredTruth {annotation} example_{idx} := by"
            )
            lines.append(f"  unfold example_{idx}")
            lines.extend(
                concrete_registered_truth_proof_steps(
                    result["ast"],
                    target,
                )
            )
        lines.append("")
        for idx, result in enumerate(results, 1):
            annotation = export_result_type(result["ast"])
            lines.append(
                "theorem "
                f"example_{idx}_concrete_registered_truth_kernel_sound : "
                "concrete_registered_truth_kernel."
                "concrete_registered_kernel_denotes "
                f"{annotation} example_{idx} := by"
            )
            lines.append(
                "  apply "
                "concrete_registered_truth_kernel_denotes_concrete_registered"
            )
            lines.append(f"  exact example_{idx}_concrete_registered_truth")
            lines.append("")
            lines.append(
                "theorem "
                f"example_{idx}_concrete_registered_truth_conditions_from_kernel_sound : "
                "concrete_registered_truth_conditions_from_kernel."
                "fully_registered_truth_denotes "
                f"{annotation} example_{idx} := by"
            )
            lines.append(
                "  apply "
                "concrete_registered_truth_conditions_from_kernel_denote_concrete_registered"
            )
            lines.append(f"  exact example_{idx}_concrete_registered_truth")
            lines.append("")
            lines.append(
                "theorem "
                f"example_{idx}_concrete_registered_truth_conditions_from_kernel_atomic_sound : "
                f"AtomicClosureTruth {annotation} example_{idx} := by"
            )
            lines.append(
                "  apply "
                "concrete_registered_truth_conditions_from_kernel_imply_atomic_closure"
            )
            lines.append(
                f"  exact "
                f"example_{idx}_concrete_registered_truth_conditions_from_kernel_sound"
            )
            lines.append("")
        for idx, result in enumerate(results, 1):
            annotation = export_result_type(result["ast"])
            lines.append(
                "theorem "
                f"example_{idx}_concrete_registered_truth_condition_sound : "
                "concrete_registered_truth_conditions."
                "fully_registered_truth_denotes "
                f"{annotation} example_{idx} := by"
            )
            lines.append(
                "  apply "
                "concrete_registered_truth_conditions_denote_concrete_registered"
            )
            lines.append(f"  exact example_{idx}_concrete_registered_truth")
        lines.append("")
        for idx, result in enumerate(results, 1):
            annotation = export_result_type(result["ast"])
            lines.append(
                "theorem "
                f"example_{idx}_concrete_registered_truth_condition_atomic_sound : "
                f"AtomicClosureTruth {annotation} example_{idx} := by"
            )
            lines.append(
                "  apply concrete_registered_truth_conditions_imply_atomic_closure"
            )
            lines.append(
                f"  exact example_{idx}_concrete_registered_truth_condition_sound"
            )
        lines.append("")
        for idx, result in enumerate(results, 1):
            annotation = export_result_type(result["ast"])
            lines.append(
                "theorem "
                f"example_{idx}_concrete_registered_evidence_backed_truth_condition_sound : "
                "concrete_registered_evidence_backed_truth_conditions."
                "fully_registered_truth_denotes "
                f"{annotation} example_{idx} := by"
            )
            lines.append(
                "  apply "
                "concrete_registered_evidence_backed_truth_conditions_denote_concrete_registered"
            )
            lines.append(f"  exact example_{idx}_concrete_registered_truth")
            lines.append("")
            lines.append(
                "theorem "
                f"example_{idx}_concrete_registered_evidence_backed_truth_condition_atomic_sound : "
                f"AtomicClosureTruth {annotation} example_{idx} := by"
            )
            lines.append(
                "  apply "
                "concrete_registered_evidence_backed_truth_conditions_imply_atomic_closure"
            )
            lines.append(
                f"  exact "
                f"example_{idx}_concrete_registered_evidence_backed_truth_condition_sound"
            )
            lines.append("")
        lines.extend(
            concrete_registered_evidence_backed_example_truth_instance_lines(
                results,
                target,
            )
        )
        lines.append("")
        lines.extend(concrete_registered_example_truth_instance_lines(results, target))
        lines.append("")
        lines.extend(
            concrete_registered_kernel_example_truth_instance_lines(results, target)
        )
        lines.append("")
        lines.extend(
            concrete_registered_truth_condition_route_lines(results, target)
        )
        lines.append("")
        lines.extend(
            concrete_registered_truth_condition_route_example_agreement_lines(
                results,
                target,
            )
        )
        lines.append("")
        lines.extend(
            independent_registered_truth_condition_source_lines(results, target)
        )
        lines.append("")
        lines.extend(
            independent_registered_truth_condition_clause_instance_lines(
                declarations,
                results,
                target,
            )
        )
        lines.append("")
        lines.extend(
            independent_registered_truth_condition_clause_coverage_lines(
                declarations,
                results,
                target,
            )
        )
        lines.append("")
        lines.extend(independent_registered_lexical_truth_condition_instance_lines(target))
        lines.append("")
        lines.extend(independent_registered_temporal_truth_condition_instance_lines(target))
        lines.append("")
        lines.extend(
            independent_registered_sigma_truth_condition_instance_lines(
                declarations,
                target,
            )
        )
        lines.append("")
        lines.extend(independent_registered_repeat_truth_condition_instance_lines(target))
        lines.append("")
        lines.extend(independent_registered_polarity_truth_condition_instance_lines(target))
        lines.append("")
        lines.extend(
            independent_registered_transition_cause_truth_condition_instance_lines(target)
        )
        lines.append("")
        lines.extend(independent_registered_truth_condition_instance_suite_lines(target))
        lines.append("")
        lines.extend(
            independent_registered_truth_condition_instance_suite_example_package_lines(
                results,
                target,
            )
        )
        lines.append("")
        for idx, result in enumerate(results, 1):
            annotation = export_result_type(result["ast"])
            lines.append(
                "theorem "
                f"example_{idx}_fully_registered_truth_condition_atomic_sound : "
                f"AtomicClosureTruth {annotation} example_{idx} := by"
            )
            lines.append(
                "  apply fully_registered_truth_conditions_imply_atomic_closure"
            )
            lines.append(
                f"  exact example_{idx}_fully_registered_truth_condition_sound"
            )
        lines.append("")
        lines.extend(registered_example_truth_instance_lines(results, target))
        lines.append("")
        lines.extend(
            finite_registered_truth_condition_instance_ledger_lines(results, target)
        )
        lines.append("")
        lines.extend(
            finite_registered_truth_condition_completion_certificate_lines(
                results,
                target,
            )
        )
        lines.append("")
        lines.extend(
            finite_registered_truth_condition_component_coverage_certificate_lines(
                results,
                target,
            )
        )
        lines.append("")
        lines.extend(
            finite_registered_atomic_witness_certificate_lines(
                declarations,
                target,
            )
        )
        lines.append("")
        lines.extend(
            finite_registered_atomic_source_discipline_certificate_lines(
                declarations,
                target,
            )
        )
        lines.append("")
        lines.extend(
            finite_registered_atomic_kernel_alignment_certificate_lines(
                declarations,
                target,
            )
        )
        lines.append("")
        lines.extend(
            finite_registered_atomic_truth_condition_source_certificate_lines(
                declarations,
                target,
            )
        )
        lines.append("")
        for idx in range(1, len(results) + 1):
            lines.append(f"#check example_{idx}")
            lines.append(f"#check example_{idx}_semantic_preservation_obligation")
            lines.append(f"#check example_{idx}_semantic_preservation_obligation_record")
            lines.append(f"#check example_{idx}_semantic_preservation_obligation_is_prop")
            lines.append(f"#check example_{idx}_semantic_preservation_target_matches")
            lines.append(f"#check example_{idx}_semantic_preservation_proved")
            lines.append(f"#check example_{idx}_model_interpretable")
            lines.append(f"#check example_{idx}_syntax_directed_truth")
            lines.append(f"#check example_{idx}_denotationally_sound")
            lines.append(f"#check example_{idx}_truth_condition_sound")
            lines.append(f"#check example_{idx}_tautological_truth_condition_sound")
            lines.append(f"#check example_{idx}_structural_truth_condition_sound")
            lines.append(f"#check example_{idx}_concrete_kernel_truth_condition_sound")
            lines.append(f"#check example_{idx}_model_interpretable_truth_kernel_sound")
            lines.append(f"#check example_{idx}_syntax_directed_truth_kernel_sound")
            lines.append(f"#check example_{idx}_primitive_truth_kernel_sound")
            lines.append(f"#check example_{idx}_atomic_closure_truth")
            lines.append(f"#check example_{idx}_atomic_closure_truth_kernel_sound")
            lines.append(f"#check example_{idx}_atomic_closure_truth_condition_sound")
            lines.append(
                "#check "
                f"example_{idx}_atomic_closure_evidence_backed_truth_condition_sound"
            )
            lines.append(
                f"#check example_{idx}_transition_refined_atomic_closure_truth"
            )
            lines.append(
                f"#check example_{idx}_transition_refined_atomic_closure_sound"
            )
            lines.append(
                "#check "
                f"example_{idx}_transition_refined_registered_truth_condition_sound"
            )
            lines.append(
                "#check "
                f"example_{idx}_transition_refined_registered_truth_condition_atomic_sound"
            )
            lines.append(
                f"#check example_{idx}_fully_registered_atomic_closure_truth"
            )
            lines.append(
                f"#check example_{idx}_fully_registered_truth_condition_sound"
            )
            lines.append(
                "#check "
                f"example_{idx}_registered_lexical_truth_model_sound"
            )
            lines.append(
                "#check "
                f"example_{idx}_registered_lexical_truth_conditions_from_model_sound"
            )
            lines.append(
                f"#check example_{idx}_concrete_registered_truth"
            )
            lines.append(
                "#check "
                f"example_{idx}_concrete_registered_truth_kernel_sound"
            )
            lines.append(
                "#check "
                f"example_{idx}_concrete_registered_truth_conditions_from_kernel_sound"
            )
            lines.append(
                "#check "
                f"example_{idx}_concrete_registered_truth_conditions_from_kernel_atomic_sound"
            )
            lines.append(
                "#check "
                f"example_{idx}_concrete_registered_truth_condition_sound"
            )
            lines.append(
                "#check "
                f"example_{idx}_concrete_registered_truth_condition_atomic_sound"
            )
            lines.append(
                "#check "
                f"example_{idx}_concrete_registered_evidence_backed_truth_condition_sound"
            )
            lines.append(
                "#check "
                f"example_{idx}_concrete_registered_evidence_backed_truth_condition_atomic_sound"
            )
            lines.append(
                "#check "
                f"concrete_registered_evidence_backed_example_{idx}_truth_instance_atomic_sound"
            )
            lines.append(
                "#check "
                f"concrete_registered_example_{idx}_truth_instance_atomic_sound"
            )
            lines.append(
                "#check "
                f"concrete_registered_kernel_example_{idx}_truth_instance_atomic_sound"
            )
            lines.append(
                "#check "
                f"concrete_registered_truth_condition_route_example_{idx}_direct_atomic_sound"
            )
            lines.append(
                "#check "
                f"concrete_registered_truth_condition_route_example_{idx}_evidence_atomic_sound"
            )
            lines.append(
                "#check "
                f"concrete_registered_truth_condition_route_example_{idx}_kernel_atomic_sound"
            )
            lines.append(
                "#check "
                f"concrete_registered_truth_condition_route_example_{idx}_agreement_direct_atomic_sound"
            )
            lines.append(
                "#check "
                f"concrete_registered_truth_condition_route_example_{idx}_agreement_evidence_atomic_sound"
            )
            lines.append(
                "#check "
                f"concrete_registered_truth_condition_route_example_{idx}_agreement_kernel_atomic_sound"
            )
            lines.append(
                "#check "
                f"independent_registered_truth_condition_sources_example_{idx}_atomic_sound"
            )
            lines.append(
                "#check "
                f"independent_registered_truth_condition_clause_example_{idx}_atomic_sound"
            )
            lines.append(
                "#check "
                f"independent_registered_truth_condition_clause_coverage_example_{idx}_atomic_sound"
            )
            lines.append(
                "#check "
                f"example_{idx}_fully_registered_truth_condition_atomic_sound"
            )
            lines.append(
                "#check "
                f"registered_example_{idx}_truth_instance_atomic_sound"
            )
            lines.append(
                "#check "
                f"finite_registered_truth_condition_ledger_example_{idx}_suite_atomic_sound"
            )
            lines.append(
                "#check "
                f"finite_registered_truth_condition_ledger_example_{idx}_registered_atomic_sound"
            )
            lines.append(
                "#check "
                f"finite_registered_truth_condition_ledger_example_{idx}_concrete_atomic_sound"
            )
            lines.append(
                "#check "
                f"finite_registered_truth_condition_ledger_example_{idx}_kernel_atomic_sound"
            )
            for route in (
                "registered",
                "direct",
                "evidence",
                "kernel",
                "source",
                "suite",
            ):
                lines.append(
                    "#check "
                    "finite_registered_truth_condition_completion_example_"
                    f"{idx}_{route}_atomic_sound"
                )
            lines.append(
                "#check "
                "finite_registered_truth_condition_component_coverage_example_"
                f"{idx}_atomic_sound"
            )
        lines.append("#check independent_truth_condition_obligation_ledger")
        lines.append("#check independent_truth_condition_obligation_ledger_exists")
        lines.append(
            "#check "
            "independent_truth_condition_obligation_ledger_induces_truth_conditions"
        )
        lines.append(
            "#check "
            "independent_truth_condition_obligation_ledger_truth_conditions_sound"
        )
        lines.append("#check TruthEvidence")
        lines.append("#check truth_evidence_sound")
        lines.append("#check truth_evidence_intro")
        lines.append("#check EvidenceBackedTruthConditionSources")
        lines.append("#check concrete_kernel_from_evidence_sources")
        lines.append("#check evidence_backed_truth_condition_ledger")
        lines.append("#check evidence_backed_truth_condition_sources_induce_kernel")
        lines.append(
            "#check "
            "evidence_backed_truth_condition_sources_induce_truth_conditions"
        )
        lines.append("#check evidence_backed_truth_condition_sources_sound")
        lines.append("#check atomic_closure_evidence_backed_truth_sources")
        lines.append("#check atomic_closure_evidence_backed_truth_kernel")
        lines.append("#check atomic_closure_evidence_backed_truth_ledger")
        lines.append("#check atomic_closure_evidence_backed_truth_sources_exist")
        lines.append("#check atomic_closure_evidence_backed_truth_kernel_exists")
        lines.append("#check atomic_closure_evidence_backed_truth_ledger_exists")
        lines.append("#check atomic_closure_evidence_backed_truth_sources_sound")
        lines.append("#check registered_lexical_truth_model")
        lines.append("#check registered_lexical_truth_model_exists")
        lines.append("#check registered_lexical_truth_conditions_from_model")
        lines.append("#check registered_lexical_truth_conditions_from_model_exists")
        lines.append("#check concrete_registered_truth_basis")
        lines.append("#check concrete_registered_truth_basis_exists")
        lines.append("#check concrete_registered_atomic_model")
        lines.append("#check concrete_registered_atomic_model_exists")
        lines.append("#check concrete_registered_atomic_model_denotes_atomic_base_truth")
        lines.append("#check concrete_registered_truth_basis_denotes_atomic_base_truth")
        lines.append("#check concrete_registered_truth_conditions")
        lines.append("#check concrete_registered_truth_condition_spec_exists")
        lines.append("#check RegisteredEvidenceBackedTruthConditionSources")
        lines.append(
            "#check "
            "fully_registered_truth_conditions_from_registered_evidence_sources"
        )
        lines.append(
            "#check "
            "registered_evidence_backed_truth_condition_sources_induce_fully_registered_truth_conditions"
        )
        lines.append("#check concrete_registered_evidence_backed_truth_sources")
        lines.append("#check concrete_registered_evidence_backed_truth_conditions")
        lines.append("#check concrete_registered_evidence_backed_truth_sources_exist")
        lines.append(
            "#check concrete_registered_evidence_backed_truth_conditions_exists"
        )
        lines.append(
            "#check "
            "concrete_registered_evidence_backed_truth_conditions_denote_concrete_registered"
        )
        lines.append(
            "#check "
            "concrete_registered_evidence_backed_truth_conditions_imply_atomic_closure"
        )
        lines.append(
            "#check "
            "concrete_registered_evidence_backed_truth_condition_model"
        )
        lines.append(
            "#check "
            "concrete_registered_evidence_backed_truth_condition_model_exists"
        )
        lines.append(
            "#check "
            "concrete_registered_evidence_backed_truth_condition_model_denote_spec"
        )
        lines.append(
            "#check "
            "concrete_registered_evidence_backed_truth_condition_model_spec_imply_atomic_closure"
        )
        lines.append("#check concrete_registered_evidence_backed_example_truth_instances")
        lines.append(
            "#check "
            "concrete_registered_evidence_backed_example_truth_instances_exists"
        )
        lines.append("#check concrete_registered_compositional_model")
        lines.append("#check concrete_registered_compositional_model_exists")
        lines.append(
            "#check "
            "concrete_registered_compositional_model_denotes_concrete_registered"
        )
        lines.append(
            "#check concrete_registered_compositional_model_imply_atomic_closure"
        )
        lines.append("#check concrete_registered_compositional_model_repeat_clause")
        lines.append("#check concrete_registered_compositional_model_at_T_clause")
        lines.append("#check concrete_registered_compositional_model_cause_clause")
        lines.append("#check concrete_registered_truth_condition_model")
        lines.append("#check concrete_registered_truth_condition_model_exists")
        lines.append("#check concrete_registered_truth_condition_model_denote_spec")
        lines.append(
            "#check concrete_registered_truth_condition_model_imply_atomic_closure"
        )
        lines.append(
            "#check "
            "concrete_registered_truth_condition_model_spec_imply_atomic_closure"
        )
        lines.append("#check concrete_registered_truth_kernel")
        lines.append("#check concrete_registered_truth_kernel_exists")
        lines.append("#check concrete_registered_truth_conditions_from_kernel")
        lines.append("#check concrete_registered_truth_conditions_from_kernel_exists")
        lines.append("#check concrete_registered_example_truth_instances")
        lines.append("#check concrete_registered_example_truth_instances_exists")
        lines.append("#check concrete_registered_kernel_example_truth_instances")
        lines.append(
            "#check concrete_registered_kernel_example_truth_instances_exists"
        )
        lines.append("#check concrete_registered_truth_condition_route")
        lines.append("#check concrete_registered_truth_condition_route_exists")
        lines.append(
            "#check concrete_registered_truth_condition_route_direct_spec_matches_model"
        )
        lines.append(
            "#check concrete_registered_truth_condition_route_evidence_spec_matches_model"
        )
        lines.append(
            "#check concrete_registered_truth_condition_route_kernel_spec_matches_kernel"
        )
        lines.append("#check concrete_registered_truth_condition_route_direct_spec_sound")
        lines.append("#check concrete_registered_truth_condition_route_evidence_spec_sound")
        lines.append("#check concrete_registered_truth_condition_route_kernel_spec_sound")
        lines.append(
            "#check concrete_registered_truth_condition_route_example_agreement"
        )
        lines.append(
            "#check concrete_registered_truth_condition_route_example_agreement_exists"
        )
        lines.append(
            "#check "
            "concrete_registered_truth_condition_route_example_agreement_route_matches"
        )
        lines.append("#check IndependentRegisteredTruthConditionSources")
        lines.append("#check independent_registered_truth_condition_sources")
        lines.append("#check independent_registered_truth_condition_sources_exist")
        lines.append(
            "#check "
            "independent_registered_truth_condition_sources_spec_matches_route"
        )
        lines.append(
            "#check "
            "independent_registered_truth_condition_sources_agreement_matches_route"
        )
        lines.append("#check independent_registered_truth_condition_sources_spec_sound")
        lines.append("#check IndependentRegisteredTruthConditionClauseInstances")
        lines.append("#check independent_registered_truth_condition_clause_instances")
        lines.append(
            "#check independent_registered_truth_condition_clause_instances_exists"
        )
        lines.append(
            "#check "
            "independent_registered_truth_condition_clause_spec_matches_source"
        )
        lines.append(
            "#check "
            "independent_registered_truth_condition_clause_lexical_application_instance"
        )
        lines.append(
            "#check independent_registered_truth_condition_clause_sigma_Entity_instance"
        )
        lines.append(
            "#check independent_registered_truth_condition_clause_repeat_instance"
        )
        lines.append(
            "#check independent_registered_truth_condition_clause_at_T_instance"
        )
        lines.append(
            "#check independent_registered_truth_condition_clause_not_T_instance"
        )
        lines.append(
            "#check independent_registered_truth_condition_clause_transition_instance"
        )
        lines.append(
            "#check independent_registered_truth_condition_clause_cause_instance"
        )
        lines.append("#check independent_registered_truth_condition_clause_spec_sound")
        lines.append("#check IndependentRegisteredTruthConditionClauseCoverage")
        lines.append("#check independent_registered_truth_condition_clause_coverage")
        lines.append(
            "#check independent_registered_truth_condition_clause_coverage_exists"
        )
        lines.append(
            "#check "
            "independent_registered_truth_condition_clause_coverage_instances_match"
        )
        lines.append(
            "#check independent_registered_truth_condition_clause_coverage_spec_sound"
        )
        lines.append("#check IndependentRegisteredLexicalTruthConditionInstances")
        lines.append("#check independent_registered_lexical_truth_condition_instances")
        lines.append(
            "#check independent_registered_lexical_truth_condition_instances_exists"
        )
        lines.append(
            "#check independent_registered_lexical_truth_condition_coverage_matches"
        )
        lines.append(
            "#check independent_registered_lexical_truth_condition_application_instance"
        )
        lines.append("#check independent_registered_lexical_truth_condition_spec_sound")
        lines.append("#check IndependentRegisteredTemporalTruthConditionInstances")
        lines.append("#check independent_registered_temporal_truth_condition_instances")
        lines.append(
            "#check independent_registered_temporal_truth_condition_instances_exists"
        )
        lines.append(
            "#check independent_registered_temporal_truth_condition_coverage_matches"
        )
        lines.append("#check independent_registered_temporal_truth_condition_at_T_instance")
        lines.append(
            "#check independent_registered_temporal_truth_condition_during_T_instance"
        )
        lines.append(
            "#check independent_registered_temporal_truth_condition_before_T_instance"
        )
        lines.append(
            "#check independent_registered_temporal_truth_condition_after_T_instance"
        )
        lines.append(
            "#check independent_registered_temporal_truth_condition_until_T_instance"
        )
        lines.append(
            "#check independent_registered_temporal_truth_condition_since_T_instance"
        )
        lines.append("#check independent_registered_temporal_truth_condition_spec_sound")
        lines.append("#check IndependentRegisteredSigmaTruthConditionInstances")
        lines.append("#check independent_registered_sigma_truth_condition_instances")
        lines.append(
            "#check independent_registered_sigma_truth_condition_instances_exists"
        )
        lines.append(
            "#check independent_registered_sigma_truth_condition_coverage_matches"
        )
        lines.append(
            "#check independent_registered_sigma_truth_condition_sigma_Entity_instance"
        )
        lines.append("#check independent_registered_sigma_truth_condition_spec_sound")
        lines.append("#check IndependentRegisteredRepeatTruthConditionInstances")
        lines.append("#check independent_registered_repeat_truth_condition_instances")
        lines.append(
            "#check independent_registered_repeat_truth_condition_instances_exists"
        )
        lines.append(
            "#check independent_registered_repeat_truth_condition_coverage_matches"
        )
        lines.append(
            "#check independent_registered_repeat_truth_condition_repeat_instance"
        )
        lines.append("#check independent_registered_repeat_truth_condition_spec_sound")
        lines.append("#check IndependentRegisteredPolarityTruthConditionInstances")
        lines.append("#check independent_registered_polarity_truth_condition_instances")
        lines.append(
            "#check independent_registered_polarity_truth_condition_instances_exists"
        )
        lines.append(
            "#check independent_registered_polarity_truth_condition_coverage_matches"
        )
        lines.append(
            "#check independent_registered_polarity_truth_condition_not_T_instance"
        )
        lines.append("#check independent_registered_polarity_truth_condition_spec_sound")
        lines.append(
            "#check IndependentRegisteredTransitionCauseTruthConditionInstances"
        )
        lines.append(
            "#check independent_registered_transition_cause_truth_condition_instances"
        )
        lines.append(
            "#check independent_registered_transition_cause_truth_condition_instances_exists"
        )
        lines.append(
            "#check independent_registered_transition_cause_truth_condition_coverage_matches"
        )
        lines.append(
            "#check independent_registered_transition_cause_truth_condition_transition_instance"
        )
        lines.append(
            "#check independent_registered_transition_cause_truth_condition_cause_instance"
        )
        lines.append(
            "#check independent_registered_transition_cause_truth_condition_spec_sound"
        )
        lines.append("#check IndependentRegisteredTruthConditionInstanceSuite")
        lines.append("#check independent_registered_truth_condition_instance_suite")
        lines.append(
            "#check independent_registered_truth_condition_instance_suite_exists"
        )
        for field in (
            "lexical",
            "temporal",
            "sigma",
            "repeat",
            "polarity",
            "transition_cause",
        ):
            lines.append(
                "#check "
                f"independent_registered_truth_condition_instance_suite_{field}_matches"
            )
        lines.append(
            "#check independent_registered_truth_condition_instance_suite_spec_sound"
        )
        lines.append(
            "#check IndependentRegisteredTruthConditionInstanceSuiteExamplePackage"
        )
        lines.append(
            "#check "
            "independent_registered_truth_condition_instance_suite_example_package"
        )
        lines.append(
            "#check "
            "independent_registered_truth_condition_instance_suite_example_package_exists"
        )
        lines.append(
            "#check "
            "independent_registered_truth_condition_instance_suite_example_package_suite_matches"
        )
        for idx in range(1, len(results) + 1):
            lines.append(
                "#check "
                "independent_registered_truth_condition_instance_suite_example_"
                f"{idx}_atomic_sound"
            )
        lines.append("#check registered_example_truth_instances")
        lines.append("#check registered_example_truth_instances_exists")
        lines.append("#check FiniteRegisteredTruthConditionInstanceLedger")
        lines.append("#check finite_registered_truth_condition_instance_ledger")
        lines.append(
            "#check finite_registered_truth_condition_instance_ledger_exists"
        )
        for field in (
            "route",
            "sources",
            "suite",
            "suite_examples",
            "registered_examples",
            "concrete_examples",
            "kernel_examples",
        ):
            lines.append(
                "#check "
                f"finite_registered_truth_condition_instance_ledger_{field}_matches"
            )
        lines.append("#check FiniteRegisteredTruthConditionCompletionCertificate")
        lines.append(
            "#check finite_registered_truth_condition_completion_certificate"
        )
        lines.append(
            "#check finite_registered_truth_condition_completion_certificate_exists"
        )
        lines.append("#check finite_registered_truth_condition_completion_ledger_matches")
        for route in (
            "registered_spec",
            "direct_spec",
            "evidence_spec",
            "kernel_spec",
            "source_spec",
            "suite_spec",
        ):
            lines.append(
                "#check "
                f"finite_registered_truth_condition_completion_{route}_sound"
            )
        lines.append(
            "#check "
            "FiniteRegisteredTruthConditionComponentCoverageCertificate"
        )
        lines.append(
            "#check "
            "finite_registered_truth_condition_component_coverage_certificate"
        )
        lines.append(
            "#check "
            "finite_registered_truth_condition_component_coverage_certificate_exists"
        )
        lines.append(
            "#check finite_registered_truth_condition_component_completion_matches"
        )
        for component in (
            "lexical",
            "temporal",
            "sigma",
            "repeat",
            "polarity",
            "transition_cause",
            "suite",
        ):
            lines.append(
                "#check "
                f"finite_registered_truth_condition_component_{component}_matches"
            )
            lines.append(
                "#check "
                f"finite_registered_truth_condition_component_{component}_spec_sound"
            )
        lines.append("#check FiniteRegisteredAtomicWitnessCertificate")
        lines.append("#check finite_registered_atomic_witness_certificate")
        lines.append("#check finite_registered_atomic_witness_certificate_exists")
        lines.append("#check finite_registered_atomic_witness_basis_matches")
        for index in range(1, len(declarations["lexical_applications"]) + 1):
            for sort in ("concrete", "base", "closure"):
                lines.append(
                    "#check "
                    f"finite_registered_atomic_witness_lexical_{index}_{sort}_projected"
                )
        for index in range(1, len(declarations["transitions"]) + 1):
            for sort in ("concrete", "base", "closure"):
                lines.append(
                    "#check "
                    f"finite_registered_atomic_witness_transition_{index}_{sort}_projected"
                )
        lines.append("#check FiniteRegisteredAtomicSourceDisciplineCertificate")
        lines.append("#check finite_registered_atomic_source_discipline_certificate")
        lines.append(
            "#check finite_registered_atomic_source_discipline_certificate_exists"
        )
        lines.append("#check finite_registered_atomic_source_witness_matches")
        for index in range(1, len(declarations["lexical_applications"]) + 1):
            lines.append(
                "#check "
                f"finite_registered_atomic_source_lexical_{index}_source_projected"
            )
            for sort in ("concrete", "base", "closure"):
                lines.append(
                    "#check "
                    "finite_registered_atomic_source_"
                    f"lexical_{index}_{sort}_from_source_projected"
                )
        for index in range(1, len(declarations["transitions"]) + 1):
            lines.append(
                "#check "
                f"finite_registered_atomic_source_transition_{index}_source_projected"
            )
            for sort in ("concrete", "base", "closure"):
                lines.append(
                    "#check "
                    "finite_registered_atomic_source_"
                    f"transition_{index}_{sort}_from_source_projected"
                )
        lines.append("#check finite_registered_atomic_kernel_denotes_imply_atomic_closure")
        lines.append("#check FiniteRegisteredAtomicKernelAlignmentCertificate")
        lines.append("#check finite_registered_atomic_kernel_alignment_certificate")
        lines.append(
            "#check finite_registered_atomic_kernel_alignment_certificate_exists"
        )
        lines.append("#check finite_registered_atomic_kernel_alignment_source_matches")
        lines.append("#check finite_registered_atomic_kernel_alignment_kernel_matches")
        lines.append("#check finite_registered_atomic_kernel_alignment_sound_projected")
        for index in range(1, len(declarations["lexical_applications"]) + 1):
            lines.append(
                "#check "
                "finite_registered_atomic_kernel_alignment_"
                f"lexical_{index}_source_to_kernel_projected"
            )
            lines.append(
                "#check "
                f"finite_registered_atomic_kernel_alignment_lexical_{index}_atomic_projected"
            )
        for index in range(1, len(declarations["transitions"]) + 1):
            lines.append(
                "#check "
                "finite_registered_atomic_kernel_alignment_"
                f"transition_{index}_source_to_kernel_projected"
            )
            lines.append(
                "#check "
                "finite_registered_atomic_kernel_alignment_"
                f"transition_{index}_atomic_projected"
            )
        lines.append("#check FiniteRegisteredAtomicTruthConditionSourceCertificate")
        lines.append(
            "#check finite_registered_atomic_truth_condition_source_certificate"
        )
        lines.append(
            "#check "
            "finite_registered_atomic_truth_condition_source_certificate_exists"
        )
        lines.append(
            "#check "
            "finite_registered_atomic_truth_condition_source_alignment_matches"
        )
        lines.append(
            "#check finite_registered_atomic_truth_condition_source_spec_matches"
        )
        lines.append(
            "#check finite_registered_atomic_truth_condition_source_sound_projected"
        )
        for index in range(1, len(declarations["lexical_applications"]) + 1):
            lines.append(
                "#check "
                "finite_registered_atomic_truth_condition_source_"
                f"lexical_{index}_source_to_spec_projected"
            )
            lines.append(
                "#check "
                "finite_registered_atomic_truth_condition_source_"
                f"lexical_{index}_source_to_kernel_projected"
            )
            lines.append(
                "#check "
                "finite_registered_atomic_truth_condition_source_"
                f"lexical_{index}_atomic_projected"
            )
        for index in range(1, len(declarations["transitions"]) + 1):
            lines.append(
                "#check "
                "finite_registered_atomic_truth_condition_source_"
                f"transition_{index}_source_to_spec_projected"
            )
            lines.append(
                "#check "
                "finite_registered_atomic_truth_condition_source_"
                f"transition_{index}_source_to_kernel_projected"
            )
            lines.append(
                "#check "
                "finite_registered_atomic_truth_condition_source_"
                f"transition_{index}_atomic_projected"
            )
        return "\n".join(lines) + "\n"

    lines = [
        "(* Auto-generated shallow embedding for dependent-type event semantics. *)",
        "(* This file is an interface scaffold, not a complete proof development. *)",
        "",
    ]
    lines.extend(f"Parameter {name} : Type." for name in declarations["types"])
    lines.append("Definition PropT : Type := Prop.")
    lines.append("Definition Adv : Type := (Entity -> PropT) -> Entity -> PropT.")
    lines.append("Parameter ModifierSeq : nat -> Type.")
    lines.append("Parameter mods_nil : ModifierSeq 0.")
    lines.append(
        "Parameter mods_cons : forall n : nat, Adv -> ModifierSeq n -> ModifierSeq (S n)."
    )
    lines.append("")
    lines.extend(
        f"Parameter {name} : {type_name}." for name, type_name in declarations["constants"]
    )
    lines.extend(
        f"Parameter {name} : Adv." for name in declarations["modifiers"]
    )
    lines.extend(
        [
            "",
            "Inductive ObligationStatus : Type :=",
            "  | pending",
            "  | shallow_checked",
            "  | proved.",
            "",
            "Record SemanticPreservationObligation : Type := {",
            "  obligation_statement : Prop;",
            "  obligation_status : ObligationStatus",
            "}.",
            "",
            "Parameter repeat : nat -> PropT -> PropT.",
            "Parameter at_T : Entity -> PropT -> PropT.",
            "Parameter during_T : Entity -> PropT -> PropT.",
            "Parameter before_T : Entity -> PropT -> PropT.",
            "Parameter after_T : Entity -> PropT -> PropT.",
            "Parameter until_T : Entity -> PropT -> PropT.",
            "Parameter since_T : Entity -> PropT -> PropT.",
            "Parameter not_T : PropT -> PropT.",
            "Parameter Transition : Entity -> StateScale -> State -> State -> TransitionT.",
            "Parameter Cause : Entity -> TransitionT -> PropT.",
        ]
    )
    for name, (arg_types, result_type) in sorted(declarations["functions"].items()):
        signature = " -> ".join(arg_types + [result_type])
        lines.append(f"Parameter {name} : {signature}.")
    lines.append("")
    lines.extend(semantic_preservation_relation_lines(declarations, target))
    lines.append("")
    lines.extend(model_interpretability_relation_lines(declarations, target))
    lines.append("")
    lines.extend(syntax_directed_truth_relation_lines(declarations, target))
    lines.extend(
        [
            "",
            "Theorem semantic_preservation_model_interpretable :",
            "  forall A : Type, forall term : A,",
            "    SemanticPreservation A term -> ModelInterpretable A term.",
            "Proof.",
            "  intros A term H.",
            "  induction H; constructor; assumption.",
            "Qed.",
            "",
            "Theorem semantic_preservation_syntax_directed_truth :",
            "  forall A : Type, forall term : A,",
            "    SemanticPreservation A term -> SyntaxDirectedTruth A term.",
            "Proof.",
            "  intros A term H.",
            "  induction H; constructor; assumption.",
            "Qed.",
        ]
    )
    lines.append("")
    lines.extend(semantic_model_record_lines(declarations, target))
    lines.extend(
        [
            "",
            "Theorem model_interpretable_denotational_sound :",
            "  forall M : SemanticModel, forall A : Type, forall term : A,",
            "    ModelInterpretable A term -> model_denotes M A term.",
            "Proof.",
            "  intros M A term H.",
            "  induction H; eauto using",
        ]
    )
    projection_names = denotation_soundness_projection_names(declarations)
    for index, projection in enumerate(projection_names):
        suffix = "." if index == len(projection_names) - 1 else ","
        lines.append(f"    {projection}{suffix}")
    lines.append("Qed.")
    lines.append("")
    lines.extend(truth_condition_spec_record_lines(declarations, target))
    lines.append("")
    lines.extend(semantic_model_from_truth_conditions_lines(declarations, target))
    lines.append("")
    lines.extend(concrete_truth_condition_kernel_lines(declarations, target))
    lines.append("")
    lines.extend(independent_truth_condition_obligation_ledger_lines(declarations, target))
    lines.append("")
    lines.extend(evidence_backed_truth_condition_source_lines(declarations, target))
    lines.append("")
    lines.extend(primitive_truth_assumption_kernel_lines(declarations, target))
    lines.append("")
    lines.extend(atomic_closure_truth_kernel_lines(declarations, target))
    lines.append("")
    lines.extend(atomic_closure_evidence_backed_truth_source_lines(declarations, target))
    lines.append("")
    lines.extend(transition_refined_atomic_closure_truth_lines(declarations, target))
    lines.append("")
    lines.extend(registered_truth_condition_spec_lines(declarations, target))
    lines.append("")
    lines.extend(registered_lexical_truth_condition_spec_lines(declarations, target))
    lines.append("")
    lines.extend(registered_lexical_truth_model_lines(declarations, target))
    lines.append("")
    lines.extend(concrete_registered_truth_condition_instance_lines(declarations, target))
    lines.append("")
    lines.extend(
        registered_evidence_backed_truth_condition_source_lines(
            declarations,
            target,
        )
    )
    lines.append("")
    lines.extend(concrete_registered_evidence_backed_truth_condition_model_lines(target))
    lines.append("")
    lines.extend(concrete_registered_truth_kernel_lines(declarations, target))
    lines.append("")
    lines.extend(concrete_truth_condition_kernel_instance_lines(declarations, target))
    lines.append("")
    lines.extend(syntax_directed_truth_kernel_instance_lines(declarations, target))
    lines.append("")
    lines.extend(truth_condition_instance_lines(declarations, target))
    lines.append("")
    lines.append("Definition PreservationTargetMatches")
    lines.append(
        "  (A : Type) (term : A) (target : SemanticPreservationObligation) : Prop :="
    )
    lines.append("  obligation_statement target = SemanticPreservation A term.")
    lines.append("")
    for idx, result in enumerate(results, 1):
        expr = result["exports"][target]
        annotation = export_result_type(result["ast"])
        lines.append(f"Definition example_{idx} : {annotation} := {expr}.")
    lines.append("")
    for idx, result in enumerate(results, 1):
        annotation = export_result_type(result["ast"])
        lines.append(
            "Definition "
            f"example_{idx}_semantic_preservation_obligation : Prop := "
            f"SemanticPreservation {annotation} example_{idx}."
        )
    lines.append("")
    for idx in range(1, len(results) + 1):
        lines.append(
            "Definition "
            f"example_{idx}_semantic_preservation_obligation_record : "
            "SemanticPreservationObligation := {|"
        )
        lines.append(
            "  obligation_statement := "
            f"example_{idx}_semantic_preservation_obligation;"
        )
        lines.append("  obligation_status := proved")
        lines.append("|}.")
    lines.append("")
    for idx in range(1, len(results) + 1):
        lines.append(
            "Theorem "
            f"example_{idx}_semantic_preservation_obligation_is_prop : "
            "exists P : Prop, "
            f"P = example_{idx}_semantic_preservation_obligation."
        )
        lines.append(
            "Proof. exists "
            f"example_{idx}_semantic_preservation_obligation. reflexivity. Qed."
        )
    lines.append("")
    for idx, result in enumerate(results, 1):
        annotation = export_result_type(result["ast"])
        lines.append(
            "Theorem "
            f"example_{idx}_semantic_preservation_target_matches : "
            f"PreservationTargetMatches {annotation} example_{idx} "
            f"example_{idx}_semantic_preservation_obligation_record."
        )
        lines.append("Proof. reflexivity. Qed.")
    lines.append("")
    for idx, result in enumerate(results, 1):
        lines.append(
            "Theorem "
            f"example_{idx}_semantic_preservation_proved : "
            f"example_{idx}_semantic_preservation_obligation."
        )
        lines.append("Proof.")
        lines.append(f"  unfold example_{idx}_semantic_preservation_obligation.")
        lines.append(f"  unfold example_{idx}.")
        lines.extend(semantic_preservation_proof_steps(result["ast"], target))
        lines.append("Qed.")
    lines.append("")
    for idx, result in enumerate(results, 1):
        annotation = export_result_type(result["ast"])
        lines.append(
            "Theorem "
            f"example_{idx}_model_interpretable : "
            f"ModelInterpretable {annotation} example_{idx}."
        )
        lines.append("Proof.")
        lines.append("  apply semantic_preservation_model_interpretable.")
        lines.append(f"  exact example_{idx}_semantic_preservation_proved.")
        lines.append("Qed.")
    lines.append("")
    for idx, result in enumerate(results, 1):
        annotation = export_result_type(result["ast"])
        lines.append(
            "Theorem "
            f"example_{idx}_syntax_directed_truth : "
            f"SyntaxDirectedTruth {annotation} example_{idx}."
        )
        lines.append("Proof.")
        lines.append("  apply semantic_preservation_syntax_directed_truth.")
        lines.append(f"  exact example_{idx}_semantic_preservation_proved.")
        lines.append("Qed.")
    lines.append("")
    for idx, result in enumerate(results, 1):
        annotation = export_result_type(result["ast"])
        lines.append(
            "Theorem "
            f"example_{idx}_denotationally_sound : "
            f"forall M : SemanticModel, model_denotes M {annotation} example_{idx}."
        )
        lines.append("Proof.")
        lines.append("  intro M.")
        lines.append("  apply model_interpretable_denotational_sound.")
        lines.append(f"  exact example_{idx}_model_interpretable.")
        lines.append("Qed.")
    lines.append("")
    for idx, result in enumerate(results, 1):
        annotation = export_result_type(result["ast"])
        lines.append(
            "Theorem "
            f"example_{idx}_truth_condition_sound : "
            f"forall T : TruthConditionSpec, truth_denotes T {annotation} example_{idx}."
        )
        lines.append("Proof.")
        lines.append("  intro T.")
        lines.append("  apply truth_conditions_induce_denotational_soundness.")
        lines.append(f"  exact example_{idx}_model_interpretable.")
        lines.append("Qed.")
    lines.append("")
    for idx, result in enumerate(results, 1):
        annotation = export_result_type(result["ast"])
        lines.append(
            "Theorem "
            f"example_{idx}_tautological_truth_condition_sound : "
            f"truth_denotes tautological_truth_conditions {annotation} example_{idx}."
        )
        lines.append("Proof.")
        lines.append("  apply tautological_truth_conditions_denote_model_interpretable.")
        lines.append(f"  exact example_{idx}_model_interpretable.")
        lines.append("Qed.")
    lines.append("")
    for idx, result in enumerate(results, 1):
        annotation = export_result_type(result["ast"])
        lines.append(
            "Theorem "
            f"example_{idx}_structural_truth_condition_sound : "
            f"truth_denotes structural_truth_conditions {annotation} example_{idx}."
        )
        lines.append("Proof.")
        lines.append("  apply structural_truth_conditions_denote_model_interpretable.")
        lines.append(f"  exact example_{idx}_model_interpretable.")
        lines.append("Qed.")
    lines.append("")
    for idx, result in enumerate(results, 1):
        annotation = export_result_type(result["ast"])
        lines.append(
            "Theorem "
            f"example_{idx}_concrete_kernel_truth_condition_sound : "
            f"forall K : ConcreteTruthConditionKernel, "
            "truth_denotes (truth_conditions_from_concrete_kernel K) "
            f"{annotation} example_{idx}."
        )
        lines.append("Proof.")
        lines.append("  intro K.")
        lines.append("  apply concrete_kernel_induces_truth_condition_soundness.")
        lines.append(f"  exact example_{idx}_model_interpretable.")
        lines.append("Qed.")
    lines.append("")
    for idx, result in enumerate(results, 1):
        annotation = export_result_type(result["ast"])
        lines.append(
            "Theorem "
            f"example_{idx}_model_interpretable_truth_kernel_sound : "
            "truth_denotes (truth_conditions_from_concrete_kernel "
            f"model_interpretable_truth_kernel) {annotation} example_{idx}."
        )
        lines.append("Proof.")
        lines.append("  apply model_interpretable_truth_kernel_denotes_model_interpretable.")
        lines.append(f"  exact example_{idx}_model_interpretable.")
        lines.append("Qed.")
    lines.append("")
    for idx, result in enumerate(results, 1):
        annotation = export_result_type(result["ast"])
        lines.append(
            "Theorem "
            f"example_{idx}_syntax_directed_truth_kernel_sound : "
            "truth_denotes (truth_conditions_from_concrete_kernel "
            f"syntax_directed_truth_kernel) {annotation} example_{idx}."
        )
        lines.append("Proof.")
        lines.append("  apply syntax_directed_truth_kernel_denotes_syntax_directed_truth.")
        lines.append(f"  exact example_{idx}_syntax_directed_truth.")
        lines.append("Qed.")
    lines.append("")
    for idx, result in enumerate(results, 1):
        annotation = export_result_type(result["ast"])
        lines.append(
            "Theorem "
            f"example_{idx}_primitive_truth_kernel_sound : "
            "truth_denotes (truth_conditions_from_concrete_kernel "
            f"primitive_truth_kernel) {annotation} example_{idx}."
        )
        lines.append("Proof.")
        lines.append("  apply primitive_truth_kernel_denotes_model_interpretable.")
        lines.append(f"  exact example_{idx}_model_interpretable.")
        lines.append("Qed.")
    lines.append("")
    for idx, result in enumerate(results, 1):
        annotation = export_result_type(result["ast"])
        lines.append(
            "Theorem "
            f"example_{idx}_atomic_closure_truth : "
            f"AtomicClosureTruth {annotation} example_{idx}."
        )
        lines.append("Proof.")
        lines.append("  apply model_interpretable_atomic_closure_truth.")
        lines.append(f"  exact example_{idx}_model_interpretable.")
        lines.append("Qed.")
    lines.append("")
    for idx, result in enumerate(results, 1):
        annotation = export_result_type(result["ast"])
        lines.append(
            "Theorem "
            f"example_{idx}_atomic_closure_truth_kernel_sound : "
            "truth_denotes (truth_conditions_from_concrete_kernel "
            f"atomic_closure_truth_kernel) {annotation} example_{idx}."
        )
        lines.append("Proof.")
        lines.append("  apply atomic_closure_truth_kernel_denotes_atomic_closure_truth.")
        lines.append(f"  exact example_{idx}_atomic_closure_truth.")
        lines.append("Qed.")
    lines.append("")
    for idx, result in enumerate(results, 1):
        annotation = export_result_type(result["ast"])
        lines.append(
            "Theorem "
            f"example_{idx}_atomic_closure_truth_condition_sound : "
            "truth_denotes atomic_closure_truth_conditions "
            f"{annotation} example_{idx}."
        )
        lines.append("Proof.")
        lines.append("  apply atomic_closure_truth_conditions_denote_atomic_closure_truth.")
        lines.append(f"  exact example_{idx}_atomic_closure_truth.")
        lines.append("Qed.")
    lines.append("")
    for idx, result in enumerate(results, 1):
        annotation = export_result_type(result["ast"])
        lines.append(
            "Theorem "
            f"example_{idx}_atomic_closure_evidence_backed_truth_condition_sound :"
        )
        lines.append(
            "  truth_denotes"
            " (ledger_truth_conditions atomic_closure_evidence_backed_truth_ledger)"
            f" {annotation} example_{idx}."
        )
        lines.append("Proof.")
        lines.append("  apply atomic_closure_evidence_backed_truth_sources_sound.")
        lines.append(f"  exact example_{idx}_model_interpretable.")
        lines.append("Qed.")
    lines.append("")
    for idx, result in enumerate(results, 1):
        annotation = export_result_type(result["ast"])
        lines.append(
            "Theorem "
            f"example_{idx}_transition_refined_atomic_closure_truth : "
            f"TransitionRefinedAtomicClosureTruth {annotation} example_{idx}."
        )
        lines.append("Proof.")
        lines.append(f"  unfold example_{idx}.")
        lines.extend(
            transition_refined_atomic_closure_proof_steps(
                result["ast"],
                target,
            )
        )
        lines.append("Qed.")
    lines.append("")
    for idx, result in enumerate(results, 1):
        annotation = export_result_type(result["ast"])
        lines.append(
            "Theorem "
            f"example_{idx}_transition_refined_atomic_closure_sound : "
            f"AtomicClosureTruth {annotation} example_{idx}."
        )
        lines.append("Proof.")
        lines.append(
            "  apply transition_refined_atomic_closure_truth_implies_atomic_closure_truth."
        )
        lines.append(f"  exact example_{idx}_transition_refined_atomic_closure_truth.")
        lines.append("Qed.")
    lines.append("")
    for idx, result in enumerate(results, 1):
        annotation = export_result_type(result["ast"])
        lines.append(
            "Theorem "
            f"example_{idx}_transition_refined_registered_truth_condition_sound : "
            "registered_truth_denotes "
            "transition_refined_registered_truth_conditions "
            f"{annotation} example_{idx}."
        )
        lines.append("Proof.")
        lines.append(
            "  apply "
            "transition_refined_registered_truth_conditions_denote_transition_refined."
        )
        lines.append(f"  exact example_{idx}_transition_refined_atomic_closure_truth.")
        lines.append("Qed.")
    lines.append("")
    for idx, result in enumerate(results, 1):
        annotation = export_result_type(result["ast"])
        lines.append(
            "Theorem "
            f"example_{idx}_transition_refined_registered_truth_condition_atomic_sound : "
            f"AtomicClosureTruth {annotation} example_{idx}."
        )
        lines.append("Proof.")
        lines.append(
            "  apply "
            "transition_refined_registered_truth_conditions_imply_atomic_closure."
        )
        lines.append(
            f"  exact example_{idx}_transition_refined_registered_truth_condition_sound."
        )
        lines.append("Qed.")
    lines.append("")
    for idx, result in enumerate(results, 1):
        annotation = export_result_type(result["ast"])
        lines.append(
            "Theorem "
            f"example_{idx}_fully_registered_atomic_closure_truth : "
            f"FullyRegisteredAtomicClosureTruth {annotation} example_{idx}."
        )
        lines.append("Proof.")
        lines.append(f"  unfold example_{idx}.")
        lines.extend(
            fully_registered_atomic_closure_proof_steps(
                result["ast"],
                target,
            )
        )
        lines.append("Qed.")
    lines.append("")
    for idx, result in enumerate(results, 1):
        annotation = export_result_type(result["ast"])
        lines.append(
            "Theorem "
            f"example_{idx}_fully_registered_truth_condition_sound : "
            "fully_registered_truth_denotes fully_registered_truth_conditions "
            f"{annotation} example_{idx}."
        )
        lines.append("Proof.")
        lines.append("  apply fully_registered_truth_conditions_denote_fully_registered.")
        lines.append(f"  exact example_{idx}_fully_registered_atomic_closure_truth.")
        lines.append("Qed.")
    lines.append("")
    lines.extend(registered_lexical_truth_model_example_lines(results, target))
    lines.append("")
    for idx, result in enumerate(results, 1):
        annotation = export_result_type(result["ast"])
        lines.append(
            "Theorem "
            f"example_{idx}_concrete_registered_truth : "
            f"ConcreteRegisteredTruth {annotation} example_{idx}."
        )
        lines.append("Proof.")
        lines.append(f"  unfold example_{idx}.")
        lines.extend(
            concrete_registered_truth_proof_steps(
                result["ast"],
                target,
            )
        )
        lines.append("Qed.")
    lines.append("")
    for idx, result in enumerate(results, 1):
        annotation = export_result_type(result["ast"])
        lines.append(
            "Theorem "
            f"example_{idx}_concrete_registered_truth_kernel_sound :"
        )
        lines.append(
            "  concrete_registered_kernel_denotes "
            "concrete_registered_truth_kernel "
            f"{annotation} example_{idx}."
        )
        lines.append("Proof.")
        lines.append(
            "  apply concrete_registered_truth_kernel_denotes_concrete_registered."
        )
        lines.append(f"  exact example_{idx}_concrete_registered_truth.")
        lines.append("Qed.")
        lines.append("")
        lines.append(
            "Theorem "
            f"example_{idx}_concrete_registered_truth_conditions_from_kernel_sound :"
        )
        lines.append(
            "  fully_registered_truth_denotes "
            "concrete_registered_truth_conditions_from_kernel "
            f"{annotation} example_{idx}."
        )
        lines.append("Proof.")
        lines.append(
            "  apply "
            "concrete_registered_truth_conditions_from_kernel_denote_concrete_registered."
        )
        lines.append(f"  exact example_{idx}_concrete_registered_truth.")
        lines.append("Qed.")
        lines.append("")
        lines.append(
            "Theorem "
            f"example_{idx}_concrete_registered_truth_conditions_from_kernel_atomic_sound :"
        )
        lines.append(f"  AtomicClosureTruth {annotation} example_{idx}.")
        lines.append("Proof.")
        lines.append(
            "  apply "
            "concrete_registered_truth_conditions_from_kernel_imply_atomic_closure."
        )
        lines.append(
            f"  exact "
            f"example_{idx}_concrete_registered_truth_conditions_from_kernel_sound."
        )
        lines.append("Qed.")
        lines.append("")
    for idx, result in enumerate(results, 1):
        annotation = export_result_type(result["ast"])
        lines.append(
            "Theorem "
            f"example_{idx}_concrete_registered_truth_condition_sound : "
            "fully_registered_truth_denotes "
            "concrete_registered_truth_conditions "
            f"{annotation} example_{idx}."
        )
        lines.append("Proof.")
        lines.append(
            "  apply "
            "concrete_registered_truth_conditions_denote_concrete_registered."
        )
        lines.append(f"  exact example_{idx}_concrete_registered_truth.")
        lines.append("Qed.")
    lines.append("")
    for idx, result in enumerate(results, 1):
        annotation = export_result_type(result["ast"])
        lines.append(
            "Theorem "
            f"example_{idx}_concrete_registered_truth_condition_atomic_sound : "
            f"AtomicClosureTruth {annotation} example_{idx}."
        )
        lines.append("Proof.")
        lines.append(
            "  apply concrete_registered_truth_conditions_imply_atomic_closure."
        )
        lines.append(
            f"  exact example_{idx}_concrete_registered_truth_condition_sound."
        )
        lines.append("Qed.")
    lines.append("")
    for idx, result in enumerate(results, 1):
        annotation = export_result_type(result["ast"])
        lines.append(
            "Theorem "
            f"example_{idx}_concrete_registered_evidence_backed_truth_condition_sound : "
            "fully_registered_truth_denotes "
            "concrete_registered_evidence_backed_truth_conditions "
            f"{annotation} example_{idx}."
        )
        lines.append("Proof.")
        lines.append(
            "  apply "
            "concrete_registered_evidence_backed_truth_conditions_denote_concrete_registered."
        )
        lines.append(f"  exact example_{idx}_concrete_registered_truth.")
        lines.append("Qed.")
        lines.append("")
        lines.append(
            "Theorem "
            f"example_{idx}_concrete_registered_evidence_backed_truth_condition_atomic_sound : "
            f"AtomicClosureTruth {annotation} example_{idx}."
        )
        lines.append("Proof.")
        lines.append(
            "  apply "
            "concrete_registered_evidence_backed_truth_conditions_imply_atomic_closure."
        )
        lines.append(
            f"  exact "
            f"example_{idx}_concrete_registered_evidence_backed_truth_condition_sound."
        )
        lines.append("Qed.")
        lines.append("")
    lines.extend(
        concrete_registered_evidence_backed_example_truth_instance_lines(
            results,
            target,
        )
    )
    lines.append("")
    lines.extend(concrete_registered_example_truth_instance_lines(results, target))
    lines.append("")
    lines.extend(concrete_registered_kernel_example_truth_instance_lines(results, target))
    lines.append("")
    lines.extend(concrete_registered_truth_condition_route_lines(results, target))
    lines.append("")
    lines.extend(
        concrete_registered_truth_condition_route_example_agreement_lines(
            results,
            target,
        )
    )
    lines.append("")
    lines.extend(independent_registered_truth_condition_source_lines(results, target))
    lines.append("")
    lines.extend(
        independent_registered_truth_condition_clause_instance_lines(
            declarations,
            results,
            target,
        )
    )
    lines.append("")
    lines.extend(
        independent_registered_truth_condition_clause_coverage_lines(
            declarations,
            results,
            target,
        )
    )
    lines.append("")
    lines.extend(independent_registered_lexical_truth_condition_instance_lines(target))
    lines.append("")
    lines.extend(independent_registered_temporal_truth_condition_instance_lines(target))
    lines.append("")
    lines.extend(
        independent_registered_sigma_truth_condition_instance_lines(
            declarations,
            target,
        )
    )
    lines.append("")
    lines.extend(independent_registered_repeat_truth_condition_instance_lines(target))
    lines.append("")
    lines.extend(independent_registered_polarity_truth_condition_instance_lines(target))
    lines.append("")
    lines.extend(
        independent_registered_transition_cause_truth_condition_instance_lines(target)
    )
    lines.append("")
    lines.extend(independent_registered_truth_condition_instance_suite_lines(target))
    lines.append("")
    lines.extend(
        independent_registered_truth_condition_instance_suite_example_package_lines(
            results,
            target,
        )
    )
    lines.append("")
    for idx, result in enumerate(results, 1):
        annotation = export_result_type(result["ast"])
        lines.append(
            "Theorem "
            f"example_{idx}_fully_registered_truth_condition_atomic_sound : "
            f"AtomicClosureTruth {annotation} example_{idx}."
        )
        lines.append("Proof.")
        lines.append("  apply fully_registered_truth_conditions_imply_atomic_closure.")
        lines.append(f"  exact example_{idx}_fully_registered_truth_condition_sound.")
        lines.append("Qed.")
    lines.append("")
    lines.extend(registered_example_truth_instance_lines(results, target))
    lines.append("")
    lines.extend(
        finite_registered_truth_condition_instance_ledger_lines(results, target)
    )
    lines.append("")
    lines.extend(
        finite_registered_truth_condition_completion_certificate_lines(
            results,
            target,
        )
    )
    lines.append("")
    lines.extend(
        finite_registered_truth_condition_component_coverage_certificate_lines(
            results,
            target,
        )
    )
    lines.append("")
    lines.extend(
        finite_registered_atomic_witness_certificate_lines(
            declarations,
            target,
        )
    )
    lines.append("")
    lines.extend(
        finite_registered_atomic_source_discipline_certificate_lines(
            declarations,
            target,
        )
    )
    lines.append("")
    lines.extend(
        finite_registered_atomic_kernel_alignment_certificate_lines(
            declarations,
            target,
        )
    )
    lines.append("")
    lines.extend(
        finite_registered_atomic_truth_condition_source_certificate_lines(
            declarations,
            target,
        )
    )
    lines.append("")
    for idx in range(1, len(results) + 1):
        lines.append(f"Check example_{idx}.")
        lines.append(f"Check example_{idx}_semantic_preservation_obligation.")
        lines.append(f"Check example_{idx}_semantic_preservation_obligation_record.")
        lines.append(f"Check example_{idx}_semantic_preservation_obligation_is_prop.")
        lines.append(f"Check example_{idx}_semantic_preservation_target_matches.")
        lines.append(f"Check example_{idx}_semantic_preservation_proved.")
        lines.append(f"Check example_{idx}_model_interpretable.")
        lines.append(f"Check example_{idx}_syntax_directed_truth.")
        lines.append(f"Check example_{idx}_denotationally_sound.")
        lines.append(f"Check example_{idx}_truth_condition_sound.")
        lines.append(f"Check example_{idx}_tautological_truth_condition_sound.")
        lines.append(f"Check example_{idx}_structural_truth_condition_sound.")
        lines.append(f"Check example_{idx}_concrete_kernel_truth_condition_sound.")
        lines.append(f"Check example_{idx}_model_interpretable_truth_kernel_sound.")
        lines.append(f"Check example_{idx}_syntax_directed_truth_kernel_sound.")
        lines.append(f"Check example_{idx}_primitive_truth_kernel_sound.")
        lines.append(f"Check example_{idx}_atomic_closure_truth.")
        lines.append(f"Check example_{idx}_atomic_closure_truth_kernel_sound.")
        lines.append(f"Check example_{idx}_atomic_closure_truth_condition_sound.")
        lines.append(
            "Check "
            f"example_{idx}_atomic_closure_evidence_backed_truth_condition_sound."
        )
        lines.append(f"Check example_{idx}_transition_refined_atomic_closure_truth.")
        lines.append(f"Check example_{idx}_transition_refined_atomic_closure_sound.")
        lines.append(
            "Check "
            f"example_{idx}_transition_refined_registered_truth_condition_sound."
        )
        lines.append(
            "Check "
            f"example_{idx}_transition_refined_registered_truth_condition_atomic_sound."
        )
        lines.append(f"Check example_{idx}_fully_registered_atomic_closure_truth.")
        lines.append(f"Check example_{idx}_fully_registered_truth_condition_sound.")
        lines.append(
            "Check "
            f"example_{idx}_registered_lexical_truth_model_sound."
        )
        lines.append(
            "Check "
            f"example_{idx}_registered_lexical_truth_conditions_from_model_sound."
        )
        lines.append(f"Check example_{idx}_concrete_registered_truth.")
        lines.append(
            "Check "
            f"example_{idx}_concrete_registered_truth_kernel_sound."
        )
        lines.append(
            "Check "
            f"example_{idx}_concrete_registered_truth_conditions_from_kernel_sound."
        )
        lines.append(
            "Check "
            f"example_{idx}_concrete_registered_truth_conditions_from_kernel_atomic_sound."
        )
        lines.append(
            "Check "
            f"example_{idx}_concrete_registered_truth_condition_sound."
        )
        lines.append(
            "Check "
            f"example_{idx}_concrete_registered_truth_condition_atomic_sound."
        )
        lines.append(
            "Check "
            f"example_{idx}_concrete_registered_evidence_backed_truth_condition_sound."
        )
        lines.append(
            "Check "
            f"example_{idx}_concrete_registered_evidence_backed_truth_condition_atomic_sound."
        )
        lines.append(
            "Check "
            f"concrete_registered_evidence_backed_example_{idx}_truth_instance_atomic_sound."
        )
        lines.append(
            "Check "
            f"concrete_registered_example_{idx}_truth_instance_atomic_sound."
        )
        lines.append(
            "Check "
            f"concrete_registered_kernel_example_{idx}_truth_instance_atomic_sound."
        )
        lines.append(
            "Check "
            f"concrete_registered_truth_condition_route_example_{idx}_direct_atomic_sound."
        )
        lines.append(
            "Check "
            f"concrete_registered_truth_condition_route_example_{idx}_evidence_atomic_sound."
        )
        lines.append(
            "Check "
            f"concrete_registered_truth_condition_route_example_{idx}_kernel_atomic_sound."
        )
        lines.append(
            "Check "
            f"concrete_registered_truth_condition_route_example_{idx}_agreement_direct_atomic_sound."
        )
        lines.append(
            "Check "
            f"concrete_registered_truth_condition_route_example_{idx}_agreement_evidence_atomic_sound."
        )
        lines.append(
            "Check "
            f"concrete_registered_truth_condition_route_example_{idx}_agreement_kernel_atomic_sound."
        )
        lines.append(
            "Check "
            f"independent_registered_truth_condition_sources_example_{idx}_atomic_sound."
        )
        lines.append(
            "Check "
            f"independent_registered_truth_condition_clause_example_{idx}_atomic_sound."
        )
        lines.append(
            "Check "
            f"independent_registered_truth_condition_clause_coverage_example_{idx}_atomic_sound."
        )
        lines.append(
            "Check "
            f"example_{idx}_fully_registered_truth_condition_atomic_sound."
        )
        lines.append(
            "Check "
            f"registered_example_{idx}_truth_instance_atomic_sound."
        )
        lines.append(
            "Check "
            f"finite_registered_truth_condition_ledger_example_{idx}_suite_atomic_sound."
        )
        lines.append(
            "Check "
            f"finite_registered_truth_condition_ledger_example_{idx}_registered_atomic_sound."
        )
        lines.append(
            "Check "
            f"finite_registered_truth_condition_ledger_example_{idx}_concrete_atomic_sound."
        )
        lines.append(
            "Check "
            f"finite_registered_truth_condition_ledger_example_{idx}_kernel_atomic_sound."
        )
        for route in (
            "registered",
            "direct",
            "evidence",
            "kernel",
            "source",
            "suite",
        ):
            lines.append(
                "Check "
                "finite_registered_truth_condition_completion_example_"
                f"{idx}_{route}_atomic_sound."
            )
        lines.append(
            "Check "
            "finite_registered_truth_condition_component_coverage_example_"
            f"{idx}_atomic_sound."
        )
    lines.append("Check independent_truth_condition_obligation_ledger.")
    lines.append("Check independent_truth_condition_obligation_ledger_exists.")
    lines.append(
        "Check "
        "independent_truth_condition_obligation_ledger_induces_truth_conditions."
    )
    lines.append(
        "Check "
        "independent_truth_condition_obligation_ledger_truth_conditions_sound."
    )
    lines.append("Check TruthEvidence.")
    lines.append("Check truth_evidence_sound.")
    lines.append("Check truth_evidence_intro.")
    lines.append("Check EvidenceBackedTruthConditionSources.")
    lines.append("Check concrete_kernel_from_evidence_sources.")
    lines.append("Check evidence_backed_truth_condition_ledger.")
    lines.append("Check evidence_backed_truth_condition_sources_induce_kernel.")
    lines.append(
        "Check evidence_backed_truth_condition_sources_induce_truth_conditions."
    )
    lines.append("Check evidence_backed_truth_condition_sources_sound.")
    lines.append("Check atomic_closure_evidence_backed_truth_sources.")
    lines.append("Check atomic_closure_evidence_backed_truth_kernel.")
    lines.append("Check atomic_closure_evidence_backed_truth_ledger.")
    lines.append("Check atomic_closure_evidence_backed_truth_sources_exist.")
    lines.append("Check atomic_closure_evidence_backed_truth_kernel_exists.")
    lines.append("Check atomic_closure_evidence_backed_truth_ledger_exists.")
    lines.append("Check atomic_closure_evidence_backed_truth_sources_sound.")
    lines.append("Check registered_lexical_truth_model.")
    lines.append("Check registered_lexical_truth_model_exists.")
    lines.append("Check registered_lexical_truth_conditions_from_model.")
    lines.append("Check registered_lexical_truth_conditions_from_model_exists.")
    lines.append("Check concrete_registered_truth_basis.")
    lines.append("Check concrete_registered_truth_basis_exists.")
    lines.append("Check concrete_registered_atomic_model.")
    lines.append("Check concrete_registered_atomic_model_exists.")
    lines.append("Check concrete_registered_atomic_model_denotes_atomic_base_truth.")
    lines.append("Check concrete_registered_truth_basis_denotes_atomic_base_truth.")
    lines.append("Check concrete_registered_truth_conditions.")
    lines.append("Check concrete_registered_truth_condition_spec_exists.")
    lines.append("Check RegisteredEvidenceBackedTruthConditionSources.")
    lines.append(
        "Check fully_registered_truth_conditions_from_registered_evidence_sources."
    )
    lines.append(
        "Check "
        "registered_evidence_backed_truth_condition_sources_induce_fully_registered_truth_conditions."
    )
    lines.append("Check concrete_registered_evidence_backed_truth_sources.")
    lines.append("Check concrete_registered_evidence_backed_truth_conditions.")
    lines.append("Check concrete_registered_evidence_backed_truth_sources_exist.")
    lines.append("Check concrete_registered_evidence_backed_truth_conditions_exists.")
    lines.append(
        "Check "
        "concrete_registered_evidence_backed_truth_conditions_denote_concrete_registered."
    )
    lines.append(
        "Check "
        "concrete_registered_evidence_backed_truth_conditions_imply_atomic_closure."
    )
    lines.append("Check concrete_registered_evidence_backed_truth_condition_model.")
    lines.append("Check concrete_registered_evidence_backed_truth_condition_model_exists.")
    lines.append(
        "Check "
        "concrete_registered_evidence_backed_truth_condition_model_denote_spec."
    )
    lines.append(
        "Check "
        "concrete_registered_evidence_backed_truth_condition_model_spec_imply_atomic_closure."
    )
    lines.append("Check concrete_registered_evidence_backed_example_truth_instances.")
    lines.append(
        "Check "
        "concrete_registered_evidence_backed_example_truth_instances_exists."
    )
    lines.append("Check concrete_registered_compositional_model.")
    lines.append("Check concrete_registered_compositional_model_exists.")
    lines.append(
        "Check concrete_registered_compositional_model_denotes_concrete_registered."
    )
    lines.append("Check concrete_registered_compositional_model_imply_atomic_closure.")
    lines.append("Check concrete_registered_compositional_model_repeat_clause.")
    lines.append("Check concrete_registered_compositional_model_at_T_clause.")
    lines.append("Check concrete_registered_compositional_model_cause_clause.")
    lines.append("Check concrete_registered_truth_condition_model.")
    lines.append("Check concrete_registered_truth_condition_model_exists.")
    lines.append("Check concrete_registered_truth_condition_model_denote_spec.")
    lines.append("Check concrete_registered_truth_condition_model_imply_atomic_closure.")
    lines.append(
        "Check concrete_registered_truth_condition_model_spec_imply_atomic_closure."
    )
    lines.append("Check concrete_registered_truth_kernel.")
    lines.append("Check concrete_registered_truth_kernel_exists.")
    lines.append("Check concrete_registered_truth_conditions_from_kernel.")
    lines.append("Check concrete_registered_truth_conditions_from_kernel_exists.")
    lines.append("Check concrete_registered_example_truth_instances.")
    lines.append("Check concrete_registered_example_truth_instances_exists.")
    lines.append("Check concrete_registered_kernel_example_truth_instances.")
    lines.append("Check concrete_registered_kernel_example_truth_instances_exists.")
    lines.append("Check concrete_registered_truth_condition_route.")
    lines.append("Check concrete_registered_truth_condition_route_exists.")
    lines.append(
        "Check concrete_registered_truth_condition_route_direct_spec_matches_model."
    )
    lines.append(
        "Check concrete_registered_truth_condition_route_evidence_spec_matches_model."
    )
    lines.append(
        "Check concrete_registered_truth_condition_route_kernel_spec_matches_kernel."
    )
    lines.append("Check concrete_registered_truth_condition_route_direct_spec_sound.")
    lines.append("Check concrete_registered_truth_condition_route_evidence_spec_sound.")
    lines.append("Check concrete_registered_truth_condition_route_kernel_spec_sound.")
    lines.append("Check concrete_registered_truth_condition_route_example_agreement.")
    lines.append("Check concrete_registered_truth_condition_route_example_agreement_exists.")
    lines.append(
        "Check "
        "concrete_registered_truth_condition_route_example_agreement_route_matches."
    )
    lines.append("Check IndependentRegisteredTruthConditionSources.")
    lines.append("Check independent_registered_truth_condition_sources.")
    lines.append("Check independent_registered_truth_condition_sources_exist.")
    lines.append(
        "Check "
        "independent_registered_truth_condition_sources_spec_matches_route."
    )
    lines.append(
        "Check "
        "independent_registered_truth_condition_sources_agreement_matches_route."
    )
    lines.append("Check independent_registered_truth_condition_sources_spec_sound.")
    lines.append("Check IndependentRegisteredTruthConditionClauseInstances.")
    lines.append("Check independent_registered_truth_condition_clause_instances.")
    lines.append(
        "Check independent_registered_truth_condition_clause_instances_exists."
    )
    lines.append(
        "Check independent_registered_truth_condition_clause_spec_matches_source."
    )
    lines.append(
        "Check "
        "independent_registered_truth_condition_clause_lexical_application_instance."
    )
    lines.append(
        "Check independent_registered_truth_condition_clause_sigma_Entity_instance."
    )
    lines.append("Check independent_registered_truth_condition_clause_repeat_instance.")
    lines.append("Check independent_registered_truth_condition_clause_at_T_instance.")
    lines.append("Check independent_registered_truth_condition_clause_not_T_instance.")
    lines.append(
        "Check independent_registered_truth_condition_clause_transition_instance."
    )
    lines.append("Check independent_registered_truth_condition_clause_cause_instance.")
    lines.append("Check independent_registered_truth_condition_clause_spec_sound.")
    lines.append("Check IndependentRegisteredTruthConditionClauseCoverage.")
    lines.append("Check independent_registered_truth_condition_clause_coverage.")
    lines.append("Check independent_registered_truth_condition_clause_coverage_exists.")
    lines.append(
        "Check "
        "independent_registered_truth_condition_clause_coverage_instances_match."
    )
    lines.append("Check independent_registered_truth_condition_clause_coverage_spec_sound.")
    lines.append("Check IndependentRegisteredLexicalTruthConditionInstances.")
    lines.append("Check independent_registered_lexical_truth_condition_instances.")
    lines.append("Check independent_registered_lexical_truth_condition_instances_exists.")
    lines.append("Check independent_registered_lexical_truth_condition_coverage_matches.")
    lines.append(
        "Check independent_registered_lexical_truth_condition_application_instance."
    )
    lines.append("Check independent_registered_lexical_truth_condition_spec_sound.")
    lines.append("Check IndependentRegisteredTemporalTruthConditionInstances.")
    lines.append("Check independent_registered_temporal_truth_condition_instances.")
    lines.append("Check independent_registered_temporal_truth_condition_instances_exists.")
    lines.append("Check independent_registered_temporal_truth_condition_coverage_matches.")
    lines.append("Check independent_registered_temporal_truth_condition_at_T_instance.")
    lines.append("Check independent_registered_temporal_truth_condition_during_T_instance.")
    lines.append("Check independent_registered_temporal_truth_condition_before_T_instance.")
    lines.append("Check independent_registered_temporal_truth_condition_after_T_instance.")
    lines.append("Check independent_registered_temporal_truth_condition_until_T_instance.")
    lines.append("Check independent_registered_temporal_truth_condition_since_T_instance.")
    lines.append("Check independent_registered_temporal_truth_condition_spec_sound.")
    lines.append("Check IndependentRegisteredSigmaTruthConditionInstances.")
    lines.append("Check independent_registered_sigma_truth_condition_instances.")
    lines.append("Check independent_registered_sigma_truth_condition_instances_exists.")
    lines.append("Check independent_registered_sigma_truth_condition_coverage_matches.")
    lines.append("Check independent_registered_sigma_truth_condition_sigma_Entity_instance.")
    lines.append("Check independent_registered_sigma_truth_condition_spec_sound.")
    lines.append("Check IndependentRegisteredRepeatTruthConditionInstances.")
    lines.append("Check independent_registered_repeat_truth_condition_instances.")
    lines.append("Check independent_registered_repeat_truth_condition_instances_exists.")
    lines.append("Check independent_registered_repeat_truth_condition_coverage_matches.")
    lines.append("Check independent_registered_repeat_truth_condition_repeat_instance.")
    lines.append("Check independent_registered_repeat_truth_condition_spec_sound.")
    lines.append("Check IndependentRegisteredPolarityTruthConditionInstances.")
    lines.append("Check independent_registered_polarity_truth_condition_instances.")
    lines.append("Check independent_registered_polarity_truth_condition_instances_exists.")
    lines.append("Check independent_registered_polarity_truth_condition_coverage_matches.")
    lines.append("Check independent_registered_polarity_truth_condition_not_T_instance.")
    lines.append("Check independent_registered_polarity_truth_condition_spec_sound.")
    lines.append("Check IndependentRegisteredTransitionCauseTruthConditionInstances.")
    lines.append("Check independent_registered_transition_cause_truth_condition_instances.")
    lines.append(
        "Check independent_registered_transition_cause_truth_condition_instances_exists."
    )
    lines.append(
        "Check independent_registered_transition_cause_truth_condition_coverage_matches."
    )
    lines.append(
        "Check independent_registered_transition_cause_truth_condition_transition_instance."
    )
    lines.append(
        "Check independent_registered_transition_cause_truth_condition_cause_instance."
    )
    lines.append("Check independent_registered_transition_cause_truth_condition_spec_sound.")
    lines.append("Check IndependentRegisteredTruthConditionInstanceSuite.")
    lines.append("Check independent_registered_truth_condition_instance_suite.")
    lines.append("Check independent_registered_truth_condition_instance_suite_exists.")
    for field in (
        "lexical",
        "temporal",
        "sigma",
        "repeat",
        "polarity",
        "transition_cause",
    ):
        lines.append(
            "Check "
            f"independent_registered_truth_condition_instance_suite_{field}_matches."
        )
    lines.append("Check independent_registered_truth_condition_instance_suite_spec_sound.")
    lines.append("Check IndependentRegisteredTruthConditionInstanceSuiteExamplePackage.")
    lines.append(
        "Check independent_registered_truth_condition_instance_suite_example_package."
    )
    lines.append(
        "Check "
        "independent_registered_truth_condition_instance_suite_example_package_exists."
    )
    lines.append(
        "Check "
        "independent_registered_truth_condition_instance_suite_example_package_suite_matches."
    )
    for idx in range(1, len(results) + 1):
        lines.append(
            "Check "
            "independent_registered_truth_condition_instance_suite_example_"
            f"{idx}_atomic_sound."
        )
    lines.append("Check registered_example_truth_instances.")
    lines.append("Check registered_example_truth_instances_exists.")
    lines.append("Check FiniteRegisteredTruthConditionInstanceLedger.")
    lines.append("Check finite_registered_truth_condition_instance_ledger.")
    lines.append("Check finite_registered_truth_condition_instance_ledger_exists.")
    for field in (
        "route",
        "sources",
        "suite",
        "suite_examples",
        "registered_examples",
        "concrete_examples",
        "kernel_examples",
    ):
        lines.append(
            "Check "
            f"finite_registered_truth_condition_instance_ledger_{field}_matches."
        )
    lines.append("Check FiniteRegisteredTruthConditionCompletionCertificate.")
    lines.append("Check finite_registered_truth_condition_completion_certificate.")
    lines.append(
        "Check finite_registered_truth_condition_completion_certificate_exists."
    )
    lines.append("Check finite_registered_truth_condition_completion_ledger_matches.")
    for route in (
        "registered_spec",
        "direct_spec",
        "evidence_spec",
        "kernel_spec",
        "source_spec",
        "suite_spec",
    ):
        lines.append(
            "Check "
            f"finite_registered_truth_condition_completion_{route}_sound."
        )
    lines.append("Check FiniteRegisteredTruthConditionComponentCoverageCertificate.")
    lines.append(
        "Check finite_registered_truth_condition_component_coverage_certificate."
    )
    lines.append(
        "Check "
        "finite_registered_truth_condition_component_coverage_certificate_exists."
    )
    lines.append("Check finite_registered_truth_condition_component_completion_matches.")
    for component in (
        "lexical",
        "temporal",
        "sigma",
        "repeat",
        "polarity",
        "transition_cause",
        "suite",
    ):
        lines.append(
            "Check "
            f"finite_registered_truth_condition_component_{component}_matches."
        )
        lines.append(
            "Check "
            f"finite_registered_truth_condition_component_{component}_spec_sound."
        )
    lines.append("Check FiniteRegisteredAtomicWitnessCertificate.")
    lines.append("Check finite_registered_atomic_witness_certificate.")
    lines.append("Check finite_registered_atomic_witness_certificate_exists.")
    lines.append("Check finite_registered_atomic_witness_basis_matches.")
    for index in range(1, len(declarations["lexical_applications"]) + 1):
        for sort in ("concrete", "base", "closure"):
            lines.append(
                "Check "
                f"finite_registered_atomic_witness_lexical_{index}_{sort}_projected."
            )
    for index in range(1, len(declarations["transitions"]) + 1):
        for sort in ("concrete", "base", "closure"):
            lines.append(
                "Check "
                f"finite_registered_atomic_witness_transition_{index}_{sort}_projected."
            )
    lines.append("Check FiniteRegisteredAtomicSourceDisciplineCertificate.")
    lines.append("Check finite_registered_atomic_source_discipline_certificate.")
    lines.append("Check finite_registered_atomic_source_discipline_certificate_exists.")
    lines.append("Check finite_registered_atomic_source_witness_matches.")
    for index in range(1, len(declarations["lexical_applications"]) + 1):
        lines.append(
            "Check "
            f"finite_registered_atomic_source_lexical_{index}_source_projected."
        )
        for sort in ("concrete", "base", "closure"):
            lines.append(
                "Check "
                "finite_registered_atomic_source_"
                f"lexical_{index}_{sort}_from_source_projected."
            )
    for index in range(1, len(declarations["transitions"]) + 1):
        lines.append(
            "Check "
            f"finite_registered_atomic_source_transition_{index}_source_projected."
        )
        for sort in ("concrete", "base", "closure"):
            lines.append(
                "Check "
                "finite_registered_atomic_source_"
                f"transition_{index}_{sort}_from_source_projected."
            )
    lines.append("Check finite_registered_atomic_kernel_denotes_imply_atomic_closure.")
    lines.append("Check FiniteRegisteredAtomicKernelAlignmentCertificate.")
    lines.append("Check finite_registered_atomic_kernel_alignment_certificate.")
    lines.append("Check finite_registered_atomic_kernel_alignment_certificate_exists.")
    lines.append("Check finite_registered_atomic_kernel_alignment_source_matches.")
    lines.append("Check finite_registered_atomic_kernel_alignment_kernel_matches.")
    lines.append("Check finite_registered_atomic_kernel_alignment_sound_projected.")
    for index in range(1, len(declarations["lexical_applications"]) + 1):
        lines.append(
            "Check "
            "finite_registered_atomic_kernel_alignment_"
            f"lexical_{index}_source_to_kernel_projected."
        )
        lines.append(
            "Check "
            f"finite_registered_atomic_kernel_alignment_lexical_{index}_atomic_projected."
        )
    for index in range(1, len(declarations["transitions"]) + 1):
        lines.append(
            "Check "
            "finite_registered_atomic_kernel_alignment_"
            f"transition_{index}_source_to_kernel_projected."
        )
        lines.append(
            "Check "
            f"finite_registered_atomic_kernel_alignment_transition_{index}_atomic_projected."
        )
    lines.append("Check FiniteRegisteredAtomicTruthConditionSourceCertificate.")
    lines.append("Check finite_registered_atomic_truth_condition_source_certificate.")
    lines.append(
        "Check finite_registered_atomic_truth_condition_source_certificate_exists."
    )
    lines.append("Check finite_registered_atomic_truth_condition_source_alignment_matches.")
    lines.append("Check finite_registered_atomic_truth_condition_source_spec_matches.")
    lines.append("Check finite_registered_atomic_truth_condition_source_sound_projected.")
    for index in range(1, len(declarations["lexical_applications"]) + 1):
        lines.append(
            "Check "
            "finite_registered_atomic_truth_condition_source_"
            f"lexical_{index}_source_to_spec_projected."
        )
        lines.append(
            "Check "
            "finite_registered_atomic_truth_condition_source_"
            f"lexical_{index}_source_to_kernel_projected."
        )
        lines.append(
            "Check "
            "finite_registered_atomic_truth_condition_source_"
            f"lexical_{index}_atomic_projected."
        )
    for index in range(1, len(declarations["transitions"]) + 1):
        lines.append(
            "Check "
            "finite_registered_atomic_truth_condition_source_"
            f"transition_{index}_source_to_spec_projected."
        )
        lines.append(
            "Check "
            "finite_registered_atomic_truth_condition_source_"
            f"transition_{index}_source_to_kernel_projected."
        )
        lines.append(
            "Check "
            "finite_registered_atomic_truth_condition_source_"
            f"transition_{index}_atomic_projected."
        )
    return "\n".join(lines) + "\n"


def infer_omitted_theme(verb: str, roles: dict[str, str]) -> tuple[str, str] | None:
    has_theme = any(role in roles for role in ("Theme", "Patient", "Object"))
    if has_theme or verb not in OMITTED_THEME_TYPES:
        return None
    return ("x_theme", OMITTED_THEME_TYPES[verb])


def resultative_term(analysis: EventAnalysis, base_activity: Term) -> Term:
    if not analysis.results:
        return base_activity
    result_state = analysis.results[-1].args[1]
    agent = analysis.roles.get("Agent") or analysis.roles.get("Actor") or "causer"
    theme = (
        analysis.roles.get("Theme")
        or analysis.roles.get("Patient")
        or analysis.roles.get("Object")
        or "theme"
    )
    return cause_term(
        agent,
        transition_term(theme, infer_source_state(result_state), result_state),
        activity=base_activity,
    )


def translate(data: dict[str, Any]) -> dict[str, Any]:
    analysis = analyze_event_formula(data)
    args = ordered_arguments(analysis.roles)
    role_entries = ordered_role_entries(analysis.roles, analysis.verb)
    omitted_theme = infer_omitted_theme(analysis.verb, analysis.roles)
    if omitted_theme is not None:
        args = args + [omitted_theme[0]]
        role_entries = role_entries + [
            {
                "role": "Theme",
                "value": omitted_theme[0],
                "type": omitted_theme[1],
                "source": "omitted",
            }
        ]
    n = len(analysis.adverbs)

    proposition_ast = application_term(analysis.verb, analysis.adverbs, args, role_entries)
    proposition_ast = resultative_term(analysis, proposition_ast)
    if omitted_theme is not None:
        witness, witness_type = omitted_theme
        proposition_ast = sigma_term(witness, witness_type, proposition_ast)
    for count in analysis.counts:
        proposition_ast = repeat_term(count, proposition_ast)
    for time_atom in analysis.times:
        proposition_ast = time_term(time_atom, proposition_ast)
    type_check = check_term(proposition_ast)
    proposition = render_term(proposition_ast)

    arity = len(args)
    family_name = "IV-ADV" if arity == 1 else "TV-ADV" if arity == 2 else f"V{arity}-ADV"
    return {
        "source_event_variable": analysis.event_var,
        "dependent_type_principle": {
            "N": "natural numbers count adverbial modifiers",
            "ADV": "(e -> t) -> (e -> t)",
            family_name: (
                f"{family_name}(n) = ADV^n -> "
                + " -> ".join(dependent_argument_types(analysis.verb, arity) + [PROP])
            ),
            "Time": "temporal predicates become proposition-level operators, not event entities",
            "Omission": "licensed implicit arguments become Sigma witnesses",
            "Counting": "event-count expressions become repeat/count operators over propositions",
            "Result": "result predicates become typed causal state transitions",
        },
        "lexical_signature": dependent_signature(analysis.verb, arity),
        "adverb_count": n,
        "ordered_roles": analysis.roles,
        "adverbs": analysis.adverbs,
        "time_operators": [atom.pred for atom in analysis.times],
        "result_states": [atom.args[1] for atom in analysis.results],
        "result_state_lexicon": [
            state_lexicon_metadata(atom.args[1]) for atom in analysis.results
        ],
        "counts": analysis.counts,
        "omitted_arguments": (
            [{"role": "Theme", "witness": omitted_theme[0], "type": omitted_theme[1]}]
            if omitted_theme is not None
            else []
        ),
        "ast": proposition_ast,
        "type_check": type_check,
        "exports": (
            {
                target: export_term(proposition_ast, target)
                for target in EXPORT_TARGETS
            }
            if type_check["ok"]
            else {}
        ),
        "translation": proposition,
        "residual_atoms_not_translated": [
            {"pred": atom.pred, "args": list(atom.args)} for atom in analysis.residuals
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Translate event semantics JSON into a dependent-type rendering.")
    parser.add_argument("json_file", type=Path)
    parser.add_argument("--pretty", action="store_true", help="Print explanatory text.")
    parser.add_argument(
        "--export",
        choices=EXPORT_TARGETS,
        help="Print only a Lean- or Coq-style shallow embedding.",
    )
    parser.add_argument(
        "--export-module",
        choices=EXPORT_TARGETS,
        help="Print a Lean- or Coq-style module scaffold for the input example.",
    )
    args = parser.parse_args()
    data = json.loads(args.json_file.read_text(encoding="utf-8"))
    result = translate(data)
    if args.export and args.export_module:
        parser.error("--export and --export-module cannot be used together")
    if args.export:
        print(result["exports"][args.export])
        return
    if args.export_module:
        print(export_module([result], args.export_module), end="")
        return
    if args.pretty:
        print(f"Lexical type: {result['lexical_signature']}")
        print(f"Translation:  {result['translation']}")
        print()
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
