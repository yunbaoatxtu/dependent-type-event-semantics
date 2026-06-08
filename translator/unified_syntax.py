"""Unified syntax scaffolding for later MLTT, UTT, and TDTT stages."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Union


class Sort(str, Enum):
    ENTITY = "Entity"
    PROP = "Prop"
    TYPE = "Type"
    NAT = "Nat"
    TIME = "Time"
    ADV = "Adv"
    TRANSITION = "Transition"


class RuleStage(str, Enum):
    UNIFIED_SYNTAX = "unified-syntax"
    MLTT = "mltt"
    UTT = "utt"
    TDTT = "tdtt"
    SYSTEM_TRANSLATION = "system-translation"
    METATHEORY = "metatheory"


@dataclass(frozen=True)
class Variable:
    name: str
    sort: Sort


@dataclass(frozen=True)
class Constant:
    name: str
    sort: Sort


@dataclass(frozen=True)
class Application:
    function: str
    arguments: tuple[str, ...]
    result_sort: Sort


@dataclass(frozen=True)
class Lambda:
    variable: Variable
    body: "Term"


@dataclass(frozen=True)
class Pi:
    variable: Variable
    body_sort: Sort


@dataclass(frozen=True)
class Sigma:
    variable: Variable
    body: "Term"


Term = Union[Variable, Constant, Application, Lambda, Pi, Sigma]


def term_sort(term: Term) -> Sort:
    if isinstance(term, (Variable, Constant)):
        return term.sort
    if isinstance(term, Application):
        return term.result_sort
    if isinstance(term, (Lambda, Pi)):
        return Sort.TYPE
    if isinstance(term, Sigma):
        return Sort.PROP
    raise TypeError(f"Unsupported unified syntax term: {term!r}")


def stage_order() -> tuple[RuleStage, ...]:
    return (
        RuleStage.UNIFIED_SYNTAX,
        RuleStage.MLTT,
        RuleStage.UTT,
        RuleStage.TDTT,
        RuleStage.SYSTEM_TRANSLATION,
        RuleStage.METATHEORY,
    )


def validate_stage_order(stages: tuple[RuleStage, ...] = stage_order()) -> list[str]:
    expected = stage_order()
    errors: list[str] = []
    if stages != expected:
        errors.append(
            "stage order must be: " + " -> ".join(stage.value for stage in expected)
        )
    return errors


def coq_identifier(name: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in name)
    cleaned = cleaned.strip("_")
    if not cleaned:
        raise ValueError("Cannot create a Coq identifier from an empty name")
    if cleaned[0].isdigit():
        cleaned = "x_" + cleaned
    return cleaned


def render_term(term: Term) -> str:
    if isinstance(term, (Variable, Constant)):
        return coq_identifier(term.name)
    if isinstance(term, Application):
        parts = [coq_identifier(term.function)]
        parts.extend(coq_identifier(argument) for argument in term.arguments)
        return "(" + " ".join(parts) + ")"
    if isinstance(term, Lambda):
        return f"(fun {coq_identifier(term.variable.name)} => {render_term(term.body)})"
    if isinstance(term, Pi):
        return (
            f"(forall {coq_identifier(term.variable.name)} : "
            f"{term.variable.sort.value}, {term.body_sort.value})"
        )
    if isinstance(term, Sigma):
        return (
            f"(exists {coq_identifier(term.variable.name)} : "
            f"{term.variable.sort.value}, {render_term(term.body)})"
        )
    raise TypeError(f"Unsupported unified syntax term: {term!r}")
