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


def collect_term_declarations(
    term: Term,
    target: str,
    functions: dict[str, tuple[list[str], str]],
    constants: dict[str, str],
    modifiers: set[str],
    types: set[str],
    transitions: set[tuple[str, str, str, str]],
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
                bound_types,
            )
        return
    raise ValueError(f"Unknown term kind: {kind!r}")


def module_declarations(results: list[dict[str, Any]], target: str) -> dict[str, Any]:
    functions: dict[str, tuple[list[str], str]] = {}
    constants: dict[str, str] = {}
    modifiers: set[str] = set()
    transitions: set[tuple[str, str, str, str]] = set()
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
        )
    return {
        "types": sorted(types),
        "constants": sorted(constants.items()),
        "modifiers": sorted(modifiers),
        "functions": functions,
        "transitions": sorted(transitions),
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
        lines.extend(primitive_truth_assumption_kernel_lines(declarations, target))
        lines.append("")
        lines.extend(atomic_closure_truth_kernel_lines(declarations, target))
        lines.append("")
        lines.extend(transition_refined_atomic_closure_truth_lines(declarations, target))
        lines.append("")
        lines.extend(registered_truth_condition_spec_lines(declarations, target))
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
    lines.extend(primitive_truth_assumption_kernel_lines(declarations, target))
    lines.append("")
    lines.extend(atomic_closure_truth_kernel_lines(declarations, target))
    lines.append("")
    lines.extend(transition_refined_atomic_closure_truth_lines(declarations, target))
    lines.append("")
    lines.extend(registered_truth_condition_spec_lines(declarations, target))
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
