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
    residuals: list[Atom]


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
    residuals: list[Atom] = []

    for atom in atoms:
        if atom == verb_atoms[0]:
            continue
        if atom.pred in ROLE_PREDS and len(atom.args) == 2 and atom.args[0] == event_var:
            roles[atom.pred] = atom.args[1]
        elif atom.pred in TIME_PREDS and len(atom.args) >= 2 and atom.args[0] == event_var:
            times.append(atom)
        elif atom.args == (event_var,):
            adverbs.append(atom.pred)
        elif len(atom.args) >= 1 and atom.args[0] == event_var:
            adverbs.append(render_modifier(atom))
        else:
            residuals.append(atom)

    return EventAnalysis(event_var, verb, roles, adverbs, times, residuals)


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


def translate(data: dict[str, Any]) -> dict[str, Any]:
    analysis = analyze_event_formula(data)
    args = ordered_arguments(analysis.roles)
    n = len(analysis.adverbs)
    app_args = analysis.adverbs + args
    application = f"{analysis.verb}({n})"
    if app_args:
        application += "(" + ", ".join(app_args) + ")"

    proposition = application
    for time_atom in analysis.times:
        proposition = render_time_operator(time_atom, proposition)

    arity = len(args)
    family_name = "IV-ADV" if arity == 1 else "TV-ADV" if arity == 2 else f"V{arity}-ADV"
    return {
        "source_event_variable": analysis.event_var,
        "dependent_type_principle": {
            "N": "natural numbers count adverbial modifiers",
            "ADV": "(e -> t) -> (e -> t)",
            family_name: f"{family_name}(n) = ADV^n -> " + " -> ".join([ENTITY] * arity + [PROP]),
            "Time": "temporal predicates become proposition-level operators, not event entities",
        },
        "lexical_signature": dependent_signature(analysis.verb, arity),
        "adverb_count": n,
        "ordered_roles": analysis.roles,
        "adverbs": analysis.adverbs,
        "time_operators": [atom.pred for atom in analysis.times],
        "translation": proposition,
        "residual_atoms_not_translated": [
            {"pred": atom.pred, "args": list(atom.args)} for atom in analysis.residuals
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Translate event semantics JSON into a dependent-type rendering.")
    parser.add_argument("json_file", type=Path)
    parser.add_argument("--pretty", action="store_true", help="Print explanatory text.")
    args = parser.parse_args()
    data = json.loads(args.json_file.read_text(encoding="utf-8"))
    result = translate(data)
    if args.pretty:
        print(f"Lexical type: {result['lexical_signature']}")
        print(f"Translation:  {result['translation']}")
        print()
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
