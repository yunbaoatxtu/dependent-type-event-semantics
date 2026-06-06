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
    return f"{verb} : Pi n : N. {family}(n)"


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


def render_modifier(atom: Atom) -> str:
    rest = ", ".join(atom.args[1:])
    return f"{atom.pred}({rest})" if rest else atom.pred


def render_time_operator(atom: Atom, proposition: str) -> str:
    if len(atom.args) == 2:
        return f"{atom.pred}_T({atom.args[1]}, {proposition})"
    rest = ", ".join(atom.args[1:])
    return f"{atom.pred}_T(({rest}), {proposition})"


def application_term(verb: str, adverbs: list[str], args: list[str]) -> Term:
    return {
        "kind": "application",
        "function": verb,
        "adverb_count": len(adverbs),
        "modifiers": adverbs,
        "arguments": args,
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
            modifiers = current.get("modifiers")
            arguments = current.get("arguments")
            adverb_count = current.get("adverb_count")
            if not isinstance(current.get("function"), str) or not current["function"]:
                errors.append(f"{path}: application.function must be a non-empty string")
            if not isinstance(modifiers, list) or not all(isinstance(x, str) for x in modifiers):
                errors.append(f"{path}: application.modifiers must be a list of strings")
                modifiers = []
            if not isinstance(arguments, list) or not all(isinstance(x, str) for x in arguments):
                errors.append(f"{path}: application.arguments must be a list of strings")
            if not isinstance(adverb_count, int) or adverb_count < 0:
                errors.append(f"{path}: application.adverb_count must be a natural number")
            elif adverb_count != len(modifiers):
                errors.append(
                    f"{path}: application.adverb_count={adverb_count} "
                    f"does not match {len(modifiers)} modifier(s)"
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
            return "Transition"

        if kind == "cause":
            if not isinstance(current.get("causer"), str) or not current["causer"]:
                errors.append(f"{path}: cause.causer must be a non-empty string")
            effect = current.get("effect")
            if not isinstance(effect, dict):
                errors.append(f"{path}: cause.effect must be a term")
            else:
                effect_type = check(effect, f"{path}.effect")
                if effect_type != "Transition":
                    errors.append(
                        f"{path}: cause.effect must have type Transition, got {effect_type}"
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

    def emit(current: Term) -> str:
        kind = current["kind"]
        if kind == "application":
            parts = [
                export_atom(current["function"], target),
                str(current["adverb_count"]),
            ]
            parts.extend(export_atom(x, target) for x in current["modifiers"])
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


def export_module(results: list[dict[str, Any]], target: str) -> str:
    if target not in EXPORT_TARGETS:
        raise ValueError(f"Unsupported export target: {target!r}")
    for idx, result in enumerate(results):
        if not result.get("type_check", {}).get("ok"):
            raise ValueError(f"Cannot export result {idx}: type_check failed")

    if target == "lean":
        lines = [
            "-- Auto-generated shallow embedding for dependent-type event semantics.",
            "-- This file is an interface scaffold, not a complete proof development.",
            "",
            "constant Entity : Type",
            "constant Food : Type",
            "constant PropT : Type",
            "constant TransitionT : Type",
            "",
            "constant John : Entity",
            "constant toast : Entity",
            "constant vase : Entity",
            "constant noon : Entity",
            "constant broken : Entity",
            "constant unknown_state : Entity",
            "",
            "constant slowly : Entity",
            "constant in_bathroom : Entity",
            "",
            "constant butter : Nat -> Entity -> Entity -> Entity -> Entity -> PropT",
            "constant eat : Nat -> Entity -> Food -> Prop",
            "constant knock : Nat -> Entity -> PropT",
            "constant repeat : Nat -> PropT -> PropT",
            "constant at_T : Entity -> PropT -> PropT",
            "constant Transition : Entity -> Entity -> Entity -> TransitionT",
            "constant Cause : Entity -> TransitionT -> PropT",
            "",
        ]
        for idx, result in enumerate(results, 1):
            expr = result["exports"][target]
            annotation = "Prop" if expr.startswith("(Exists ") else "PropT"
            lines.append(f"def example_{idx} : {annotation} := {expr}")
        return "\n".join(lines) + "\n"

    lines = [
        "(* Auto-generated shallow embedding for dependent-type event semantics. *)",
        "(* This file is an interface scaffold, not a complete proof development. *)",
        "",
        "Parameter Entity : Type.",
        "Parameter Food : Type.",
        "Parameter PropT : Type.",
        "Parameter TransitionT : Type.",
        "",
        "Parameter John : Entity.",
        "Parameter toast : Entity.",
        "Parameter vase : Entity.",
        "Parameter noon : Entity.",
        "Parameter broken : Entity.",
        "Parameter unknown_state : Entity.",
        "",
        "Parameter slowly : Entity.",
        "Parameter in_bathroom : Entity.",
        "",
        "Parameter butter : nat -> Entity -> Entity -> Entity -> Entity -> PropT.",
        "Parameter eat : nat -> Entity -> Food -> Prop.",
        "Parameter knock : nat -> Entity -> PropT.",
        "Parameter repeat : nat -> PropT -> PropT.",
        "Parameter at_T : Entity -> PropT -> PropT.",
        "Parameter Transition : Entity -> Entity -> Entity -> TransitionT.",
        "Parameter Cause : Entity -> TransitionT -> PropT.",
        "",
    ]
    for idx, result in enumerate(results, 1):
        expr = result["exports"][target]
        annotation = "Prop" if expr.startswith("(exists ") else "PropT"
        lines.append(f"Definition example_{idx} : {annotation} := {expr}.")
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
    omitted_theme = infer_omitted_theme(analysis.verb, analysis.roles)
    if omitted_theme is not None:
        args = args + [omitted_theme[0]]
    n = len(analysis.adverbs)

    proposition_ast = application_term(analysis.verb, analysis.adverbs, args)
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
            family_name: f"{family_name}(n) = ADV^n -> " + " -> ".join([ENTITY] * arity + [PROP]),
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
