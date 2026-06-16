#!/usr/bin/env python3
"""Lexical registrations for change-of-state verb alternations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class StateChangeVerbEntry:
    target_state: str
    allow_inchoative: bool = True
    allow_causative: bool = True
    allow_instrument: bool = True


STATE_CHANGE_VERB_REGISTRY = {
    "clean": StateChangeVerbEntry("clean"),
    "die": StateChangeVerbEntry("dead", allow_causative=False, allow_instrument=False),
    "dirty": StateChangeVerbEntry("dirty"),
    "dry": StateChangeVerbEntry("dry"),
    "empty": StateChangeVerbEntry("empty"),
    "fill": StateChangeVerbEntry("full"),
    "freeze": StateChangeVerbEntry("frozen"),
    "kill": StateChangeVerbEntry("dead", allow_inchoative=False),
    "melt": StateChangeVerbEntry("melted"),
    "open": StateChangeVerbEntry("open"),
    "close": StateChangeVerbEntry("closed"),
    "wet": StateChangeVerbEntry("wet"),
}

STATE_CHANGE_VERB_TARGETS = {
    verb: entry.target_state for verb, entry in STATE_CHANGE_VERB_REGISTRY.items()
}


def state_change_verb_metadata(verb: str) -> dict[str, Any]:
    entry = STATE_CHANGE_VERB_REGISTRY[verb]
    return {
        "verb": verb,
        "target_state": entry.target_state,
        "allow_inchoative": entry.allow_inchoative,
        "allow_causative": entry.allow_causative,
        "allow_instrument": entry.allow_instrument,
    }

