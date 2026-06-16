#!/usr/bin/env python3
"""Surface lexical resources for lightweight English analysis."""

from __future__ import annotations


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
COUNT_WORDS = {"once", "twice", "thrice"}
COMMON_ADVERBS = {
    "slowly",
    "quickly",
    "quietly",
    "loudly",
    "carefully",
    "happily",
    "sadly",
}
IRREGULAR_VERBS = {
    "admired": "admire",
    "ate": "eat",
    "eaten": "eat",
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
    "written": "write",
}

SURFACE_LEXICON_SOURCE = "translator/surface_lexicon.py"


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
        if len(stem) > 1 and stem[-1] == stem[-2]:
            return stem[:-1]
        return stem
    if token.endswith("ing") and len(token) > 4:
        stem = token[:-3]
        if len(stem) > 1 and stem[-1] == stem[-2]:
            return stem[:-1]
        return stem
    return token


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
