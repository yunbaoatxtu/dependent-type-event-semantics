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


def transition_term(theme: str, source_state: str, target_state: str) -> Term:
    return {
        "kind": "transition",
        "theme": theme,
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
    if kind == "transition":
        return (
            f"Transition({term['theme']}, {term['source_state']}, "
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

        if kind == "transition":
            for field in ("theme", "source_state", "target_state"):
                if not isinstance(current.get(field), str) or not current[field]:
                    errors.append(f"{path}: transition.{field} must be a non-empty string")
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


def export_term(term: Term, target: str) -> str:
    type_check = check_term(term)
    if not type_check["ok"]:
        errors = "; ".join(type_check["errors"])
        raise ValueError(f"Cannot export ill-typed AST: {errors}")
    if target not in EXPORT_TARGETS:
        raise ValueError(f"Unsupported export target: {target!r}")

    def emit_modifier_sequence(vector: Term) -> str:
        sequence = "mods_nil"
        for item in reversed(vector["items"]):
            sequence = (
                f"(mods_cons {item['tail_length']} "
                f"{export_atom(item['modifier'], target)} {sequence})"
            )
        return sequence

    def emit(current: Term) -> str:
        kind = current["kind"]
        if kind == "application":
            parts = [
                export_atom(current["function"], target),
                str(current["adverb_count"]),
                emit_modifier_sequence(current["modifier_vector"]),
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
        if kind == "transition":
            return (
                "(Transition "
                + " ".join(
                    export_atom(current[field], target)
                    for field in ("theme", "source_state", "target_state")
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
    if kind in {"repeat", "time", "cause"}:
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
            {**bound_types, witness: witness_type},
        )
        return
    if kind == "repeat":
        collect_term_declarations(
            term["body"], target, functions, constants, modifiers, types, bound_types
        )
        return
    if kind == "time":
        for value in term["arguments"]:
            exported = export_atom(value, target)
            if exported not in bound_types:
                add_constant_declaration(constants, exported, "Entity")
        collect_term_declarations(
            term["body"], target, functions, constants, modifiers, types, bound_types
        )
        return
    if kind == "transition":
        theme = export_atom(term["theme"], target)
        if theme not in bound_types:
            add_constant_declaration(constants, theme, "Entity")
        for field in ("source_state", "target_state"):
            exported = export_atom(term[field], target)
            if exported not in bound_types:
                add_constant_declaration(constants, exported, "State")
        return
    if kind == "cause":
        causer = export_atom(term["causer"], target)
        if causer not in bound_types:
            add_constant_declaration(constants, causer, "Entity")
        collect_term_declarations(
            term["effect"], target, functions, constants, modifiers, types, bound_types
        )
        activity = term.get("activity")
        if activity is not None:
            collect_term_declarations(
                activity, target, functions, constants, modifiers, types, bound_types
            )
        return
    raise ValueError(f"Unknown term kind: {kind!r}")


def module_declarations(results: list[dict[str, Any]], target: str) -> dict[str, Any]:
    functions: dict[str, tuple[list[str], str]] = {}
    constants: dict[str, str] = {}
    modifiers: set[str] = set()
    types = {"Entity", "Food", "State", "TransitionT"}
    for result in results:
        collect_term_declarations(
            result["ast"], target, functions, constants, modifiers, types
        )
    return {
        "types": sorted(types),
        "constants": sorted(constants.items()),
        "modifiers": sorted(modifiers),
        "functions": functions,
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
                "constant repeat : Nat -> PropT -> PropT",
                "constant at_T : Entity -> PropT -> PropT",
                "constant during_T : Entity -> PropT -> PropT",
                "constant before_T : Entity -> PropT -> PropT",
                "constant after_T : Entity -> PropT -> PropT",
                "constant until_T : Entity -> PropT -> PropT",
                "constant since_T : Entity -> PropT -> PropT",
                "constant Transition : Entity -> State -> State -> TransitionT",
                "constant Cause : Entity -> TransitionT -> PropT",
            ]
        )
        for name, (arg_types, result_type) in sorted(declarations["functions"].items()):
            signature = " -> ".join(arg_types + [result_type])
            lines.append(f"constant {name} : {signature}")
        lines.append("")
        for idx, result in enumerate(results, 1):
            expr = result["exports"][target]
            annotation = export_result_type(result["ast"])
            lines.append(f"def example_{idx} : {annotation} := {expr}")
        lines.append("")
        for idx in range(1, len(results) + 1):
            lines.append(f"#check example_{idx}")
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
            "Parameter repeat : nat -> PropT -> PropT.",
            "Parameter at_T : Entity -> PropT -> PropT.",
            "Parameter during_T : Entity -> PropT -> PropT.",
            "Parameter before_T : Entity -> PropT -> PropT.",
            "Parameter after_T : Entity -> PropT -> PropT.",
            "Parameter until_T : Entity -> PropT -> PropT.",
            "Parameter since_T : Entity -> PropT -> PropT.",
            "Parameter Transition : Entity -> State -> State -> TransitionT.",
            "Parameter Cause : Entity -> TransitionT -> PropT.",
        ]
    )
    for name, (arg_types, result_type) in sorted(declarations["functions"].items()):
        signature = " -> ".join(arg_types + [result_type])
        lines.append(f"Parameter {name} : {signature}.")
    lines.append("")
    for idx, result in enumerate(results, 1):
        expr = result["exports"][target]
        annotation = export_result_type(result["ast"])
        lines.append(f"Definition example_{idx} : {annotation} := {expr}.")
    lines.append("")
    for idx in range(1, len(results) + 1):
        lines.append(f"Check example_{idx}.")
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
        transition_term(theme, "_", result_state),
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
