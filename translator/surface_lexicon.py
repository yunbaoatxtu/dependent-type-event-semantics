#!/usr/bin/env python3
"""Surface lexical resources for lightweight English analysis."""

from __future__ import annotations

import re


ARTICLES = {"a", "an", "the"}
PASSIVE_AUXILIARIES = {"is", "was", "are", "were"}
PASSIVE_PARTICIPLE_FORMS = {
    "broken",
    "eaten",
    "drunk",
    "seen",
    "known",
    "left",
    "written",
    "read",
}
PREPOSITIONS = {
    "at",
    "in",
    "on",
    "under",
    "over",
    "near",
    "beside",
    "with",
    "from",
    "to",
    "into",
}
MODIFIER_ROLE_BY_PREDICATE = {
    "at": "Location",
    "with": "Instrument",
    "in": "Location",
    "on": "Location",
    "under": "Location",
    "over": "Location",
    "near": "Location",
    "beside": "Location",
    "from": "Source",
    "to": "Goal",
    "into": "Goal",
}
COUNT_WORDS = {"once", "twice", "thrice"}
COUNT_PHRASE_WORDS = {
    "one": "1",
    "two": "2",
    "three": "3",
}
COUNT_NOUNS = {"time", "times"}
COMMON_ADVERBS = {
    "slowly",
    "quickly",
    "quietly",
    "loudly",
    "carefully",
    "happily",
    "sadly",
}
COMMON_VERB_LEMMAS = {
    "admire",
    "break",
    "butter",
    "chase",
    "drink",
    "eat",
    "fly",
    "go",
    "knock",
    "love",
    "jump",
    "read",
    "run",
    "sit",
    "sleep",
    "talk",
    "visit",
    "walk",
}
TEMPORAL_ADVERBS = {
    "today",
    "tomorrow",
    "yesterday",
}
TEMPORAL_PHRASES = {
    ("last", "night"): "last_night",
    ("this", "morning"): "this_morning",
}
TEMPORAL_PREPOSITION_OPERATORS = {
    "at": "at",
    "on": "at",
    "in": "during",
}
TEMPORAL_PREPOSITION_NOUNS = {
    "afternoon",
    "evening",
    "monday",
    "morning",
    "night",
    "noon",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
}
IRREGULAR_VERBS = {
    "admired": "admire",
    "ate": "eat",
    "eaten": "eat",
    "flew": "fly",
    "saw": "see",
    "seen": "see",
    "sat": "sit",
    "saluted": "salute",
    "loves": "love",
    "broke": "break",
    "broken": "break",
    "died": "die",
    "dried": "dry",
    "emptied": "empty",
    "filled": "fill",
    "froze": "freeze",
    "frozen": "freeze",
    "melted": "melt",
    "closed": "close",
    "drank": "drink",
    "drunk": "drink",
    "went": "go",
    "ran": "run",
    "left": "leave",
    "known": "know",
    "killed": "kill",
    "slept": "sleep",
    "written": "write",
}

SURFACE_LEXICON_SOURCE = "translator/surface_lexicon.py"


def count_phrase_value(token: str) -> str | None:
    if token in COUNT_PHRASE_WORDS:
        return COUNT_PHRASE_WORDS[token]
    if re.fullmatch(r"[0-9]+", token):
        return str(int(token))
    return None


def temporal_phrase_value(tokens: list[str] | tuple[str, ...], position: int) -> tuple[str, int] | None:
    for phrase, normalized in TEMPORAL_PHRASES.items():
        end = position + len(phrase)
        if tuple(tokens[position:end]) == phrase:
            return normalized, len(phrase)
    return None


def temporal_prepositional_phrase_value(
    tokens: list[str] | tuple[str, ...],
    position: int,
) -> tuple[str, str, int] | None:
    if position >= len(tokens):
        return None
    operator = TEMPORAL_PREPOSITION_OPERATORS.get(tokens[position])
    if operator is None:
        return None
    idx = position + 1
    phrase_tokens: list[str] = []
    while idx < len(tokens) and tokens[idx] in ARTICLES:
        idx += 1
    if idx >= len(tokens) or tokens[idx] not in TEMPORAL_PREPOSITION_NOUNS:
        return None
    phrase_tokens.append(tokens[idx])
    idx += 1
    return operator, "_".join(phrase_tokens), idx - position


def lemma_verb(token: str) -> str:
    if token in IRREGULAR_VERBS:
        return IRREGULAR_VERBS[token]
    if token.endswith("ies") and len(token) > 3:
        return token[:-3] + "y"
    if token.endswith("es") and len(token) > 3:
        return token[:-2]
    if token.endswith("s") and len(token) > 2:
        return token[:-1]
    if token.endswith("ed") and len(token) > 3:
        stem = token[:-2]
        if len(stem) > 1 and stem[-1] == stem[-2] and not stem.endswith("ss"):
            return stem[:-1]
        if token.endswith("sed") and not stem.endswith("ss"):
            return stem + "e"
        return stem
    if token.endswith("ing") and len(token) > 4:
        stem = token[:-3]
        if len(stem) > 1 and stem[-1] == stem[-2]:
            return stem[:-1]
        return stem
    return token


def is_likely_surface_verb(token: str) -> bool:
    return lemma_verb(token) in COMMON_VERB_LEMMAS


def is_passive_participle(token: str) -> bool:
    return token.endswith("ed") or token in PASSIVE_PARTICIPLE_FORMS


def surface_verb_audit(surface_verb: str) -> dict[str, str]:
    return {
        "surface_verb": surface_verb,
        "lemma": lemma_verb(surface_verb),
        "source": SURFACE_LEXICON_SOURCE,
    }


def passive_participle_audit(participle: str) -> dict[str, str]:
    return {
        "participle": participle,
        "lemma": lemma_verb(participle),
        "source": SURFACE_LEXICON_SOURCE,
    }


def normalize_surface_name(name: str) -> str:
    normalized = re.sub(r"[^0-9A-Za-z_]+", "_", name).strip("_")
    if not normalized:
        return "unnamed"
    if normalized[0].isdigit():
        normalized = "x_" + normalized
    return normalized


def modifier_predicate(modifier: str) -> str:
    return modifier.split("(", 1)[0]


def modifier_semantic_role(modifier: str) -> str:
    return MODIFIER_ROLE_BY_PREDICATE.get(modifier_predicate(modifier), "Manner")


def modifier_surface_audit(
    modifier: str,
    modifier_type: str,
    semantic_role: str,
) -> dict[str, str]:
    return {
        "surface_modifier": modifier,
        "normalized_modifier": normalize_surface_name(modifier),
        "type": modifier_type,
        "semantic_role": semantic_role,
        "source": SURFACE_LEXICON_SOURCE,
    }
