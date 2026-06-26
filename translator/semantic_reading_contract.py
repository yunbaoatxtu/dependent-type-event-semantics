"""Shared contract for normalized semantic-reading records."""

from __future__ import annotations

from typing import Any


SEMANTIC_READING_CONTRACT_FIELDS = frozenset(
    {
        "attachment_summary",
        "coq_definition",
        "dependent_type_translation",
        "name",
        "reading_explanation",
        "scope",
        "source",
        "type_check",
    }
)
SEMANTIC_READING_ATTACHMENT_FIELDS = frozenset(
    {
        "kind",
        "relative_objects",
        "typed_modifiers",
        "typed_np_restrictors",
        "typed_time_modifiers",
    }
)


def empty_attachment_summary(kind: str = "none") -> dict[str, Any]:
    return {
        "kind": kind,
        "typed_modifiers": [],
        "typed_np_restrictors": [],
        "typed_time_modifiers": [],
        "relative_objects": [],
    }


def semantic_reading_default_explanation(
    *,
    name: str,
    source: str,
    scope: str,
    attachment_summary: dict[str, Any],
) -> str:
    attachment_kind = str(attachment_summary.get("kind") or "none")
    if attachment_kind == "none":
        attachment_clause = "No additional PP, temporal, or relative-clause attachment is active."
    else:
        attachment_clause = f"Attachment kind {attachment_kind} is recorded in the typed attachment summary."
    return (
        f"Semantic reading {name} is a normalized {source} proposition "
        f"with scope {scope}. {attachment_clause}"
    )
