#!/usr/bin/env python3
"""Small stdlib web demo for the translation verification pipeline."""

from __future__ import annotations

import argparse
import html
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse

from translator.dependent_type_event_translator import STATE_LEXICON
from translator.natural_language_pipeline import (
    exported_prop_definition_names,
    run_pipeline,
    semantic_reading_failure_kinds,
    semantic_reading_failure_summary,
)


DEFAULT_SENTENCE = "John knocked twice"
ANALYZE_RESPONSE_SCHEMA = "analyze.v1"
LEXICON_PATCH_DRAFTS_SCHEMA = "lexicon_patch_drafts.v1"
LEXICON_SOURCE_PLACEHOLDER = "<choose_source_state>"
FAILURE_STAGE_LABELS = {
    "input": "empty input",
    "parsing": "natural-language parsing",
    "type_check": "dependent-type checking",
    "semantic_readings_check": "semantic readings audit",
    "construction_hygiene": "construction hygiene",
    "coq_check": "Coq/Rocq validation",
}
FAILURE_STAGE_HINTS = {
    "input": "Enter a non-empty sentence.",
    "parsing": "Try a sentence with at least a subject and a predicate.",
    "type_check": "Inspect the dependent-type AST and type-check errors.",
    "semantic_readings_check": "Inspect semantic readings and exported Coq definition names.",
    "construction_hygiene": "Remove forbidden construction fragments from generated Coq.",
    "coq_check": "Check the generated Coq scaffold and local Coq/Rocq toolchain.",
}
FAILURE_STAGE_ACTIONS = {
    "input": [
        {
            "kind": "edit_input",
            "label": "Enter a sentence",
            "detail": "Type a non-empty natural-language sentence before analyzing.",
        }
    ],
    "parsing": [
        {
            "kind": "revise_sentence",
            "label": "Add subject and predicate",
            "detail": "Use a sentence with at least a recognizable subject and predicate.",
        }
    ],
    "type_check": [
        {
            "kind": "inspect_ast",
            "label": "Inspect typed AST",
            "detail": "Compare the generated AST with the dependent-type checker errors.",
        }
    ],
    "semantic_readings_check": [
        {
            "kind": "inspect_readings",
            "label": "Inspect semantic readings",
            "detail": "Check reading names, formulas, type checks, and exported Coq definitions.",
        }
    ],
    "construction_hygiene": [
        {
            "kind": "inspect_coq",
            "label": "Remove forbidden fragments",
            "detail": "Regenerate Coq without fragments banned by the matched construction rule.",
        }
    ],
    "coq_check": [
        {
            "kind": "inspect_coq",
            "label": "Check Coq/Rocq scaffold",
            "detail": "Inspect declarations and verify the local Coq/Rocq toolchain is available.",
        }
    ],
}

SEMANTIC_READING_FAILURE_HINTS = {
    "duplicate_reading_name": "Rename duplicate semantic readings so each reading has a stable unique name.",
    "export_count_mismatch": "Supply explicit semantic_readings or export exactly one Prop/PropT definition.",
    "malformed_readings": "Fix malformed semantic_readings fields before export.",
    "missing_coq_export": "Export a matching Coq/Rocq Definition for every semantic reading.",
    "missing_readings": "Add normalized semantic_readings before Coq/Rocq validation.",
    "reading_type_check_failed": "Fix the reading-local type_check before Coq/Rocq validation.",
    "unknown_reading_error": "Inspect semantic readings, formulas, and exported Coq definitions.",
}


def analyze_sentence(sentence: str, require_coq: bool = False) -> dict[str, Any]:
    sentence = sentence.strip()
    if not sentence:
        result = {
            "ok": False,
            "input_sentence": sentence,
            "error": "Please enter a sentence.",
            "conclusion": "Translation failed before parsing.",
        }
        return add_diagnostics(result)
    return add_diagnostics(run_pipeline(sentence, require_coq=require_coq))


def parse_patch_resolution_items(items: list[str]) -> tuple[dict[str, str], list[str]]:
    resolutions = {}
    errors = []
    for item in items:
        if "=" not in item:
            errors.append(f"Malformed resolution {item!r}; expected draft_id=source_state.")
            continue
        draft_id, source_state = item.split("=", 1)
        draft_id = draft_id.strip()
        source_state = source_state.strip()
        if not draft_id or not source_state:
            errors.append(f"Malformed resolution {item!r}; draft_id and source_state are required.")
            continue
        if draft_id in resolutions and resolutions[draft_id] != source_state:
            errors.append(
                f"Conflicting resolution for {draft_id!r}: "
                f"{resolutions[draft_id]!r} vs {source_state!r}."
            )
            continue
        resolutions[draft_id] = source_state
    return resolutions, errors


def parse_patch_resolution_params(params: dict[str, list[str]]) -> tuple[dict[str, str], list[str]]:
    resolution_items = list(params.get("resolve", []))
    errors = []
    draft_ids = params.get("resolve_draft_id", [])
    source_states = params.get("source_state", [])
    if draft_ids or source_states:
        if len(draft_ids) != len(source_states):
            errors.append(
                "Malformed structured resolution; resolve_draft_id and source_state counts differ."
            )
        else:
            resolution_items.extend(
                f"{draft_id}={source_state}" for draft_id, source_state in zip(draft_ids, source_states)
            )
    resolutions, item_errors = parse_patch_resolution_items(resolution_items)
    errors.extend(item_errors)
    return resolutions, errors


def validate_patch_resolution(draft: dict[str, Any], source_state: str) -> list[str]:
    errors = []
    draft_id = str(draft.get("draft_id", ""))
    target_state = str(draft.get("state", ""))
    scale = str(draft.get("scale", ""))
    if source_state == LEXICON_SOURCE_PLACEHOLDER:
        errors.append(f"{draft_id}: source_state is still the placeholder.")
    if source_state == target_state:
        errors.append(f"{draft_id}: source_state must differ from target state {target_state!r}.")
    source_entry = STATE_LEXICON.get(source_state)
    if source_entry is not None and source_entry.scale != scale:
        errors.append(
            f"{draft_id}: source_state {source_state!r} has scale "
            f"{source_entry.scale!r}, expected {scale!r}."
        )
    return errors


def resolve_lexicon_patch_drafts(
    drafts: list[dict[str, Any]],
    resolutions: dict[str, str],
) -> tuple[list[dict[str, Any]], list[str]]:
    if not resolutions:
        return [dict(draft) for draft in drafts], []
    resolved = []
    errors = []
    seen_draft_ids = set()
    for draft in drafts:
        draft_copy = dict(draft)
        draft_id = str(draft_copy.get("draft_id", ""))
        if draft_id in resolutions:
            seen_draft_ids.add(draft_id)
            source_state = resolutions[draft_id]
            resolution_errors = validate_patch_resolution(draft_copy, source_state)
            if resolution_errors:
                errors.extend(resolution_errors)
            else:
                draft_copy["default_source_state"] = source_state
                draft_copy["requires_human_choice"] = False
                draft_copy["placeholder_fields"] = []
                draft_copy["can_auto_apply"] = True
                draft_copy["state_lexicon_patch_line"] = state_lexicon_patch_line(
                    str(draft_copy.get("state", "")),
                    str(draft_copy.get("scale", "")),
                    source_state,
                )
        resolved.append(draft_copy)
    for draft_id in sorted(set(resolutions) - seen_draft_ids):
        errors.append(f"{draft_id}: no matching lexicon patch draft.")
    return resolved, errors


def build_lexicon_patch_bundle(
    sentence: str,
    require_coq: bool = False,
    resolutions: dict[str, str] | None = None,
    resolution_errors: list[str] | None = None,
) -> dict[str, Any]:
    result = analyze_sentence(sentence, require_coq=require_coq)
    diagnostics = result.get("diagnostics", {})
    drafts, validation_errors = resolve_lexicon_patch_drafts(
        result.get("lexicon_patch_drafts", []),
        resolutions or {},
    )
    all_errors = [*(resolution_errors or []), *validation_errors]
    bundle = {
        "schema_version": LEXICON_PATCH_DRAFTS_SCHEMA,
        "input_sentence": result.get("input_sentence", sentence.strip()),
        "ok": bool(result.get("ok")),
        "diagnostics": {
            "summary": diagnostics.get("summary"),
            "failure_stage": diagnostics.get("failure_stage"),
            "manual_repair_required": diagnostics.get("manual_repair_required", False),
            "lexicon_patch_draft_count": diagnostics.get("lexicon_patch_draft_count", 0),
        },
        "requires_human_choice": any(
            draft.get("requires_human_choice") for draft in drafts
        ),
        "can_auto_apply": bool(drafts)
        and not all_errors
        and all(draft.get("can_auto_apply") for draft in drafts),
        "resolved_patch_count": sum(1 for draft in drafts if draft.get("can_auto_apply")),
        "validation_errors": all_errors,
        "lexicon_patch_drafts": drafts,
        "conclusion": result.get("conclusion", ""),
        "error": result.get("error"),
    }
    bundle["patch_text_preview"] = render_lexicon_patch_text(bundle)
    return bundle


def check_status(ok: Any) -> str:
    if ok is True:
        return "passed"
    if ok is None:
        return "skipped"
    return "failed"


def recovery_actions_for(failure_stage: str | None) -> list[dict[str, str]]:
    return [dict(action) for action in FAILURE_STAGE_ACTIONS.get(failure_stage, [])]


def semantic_readings_failure_kinds_for(check: dict[str, Any]) -> list[str]:
    kinds = check.get("failure_kinds")
    if isinstance(kinds, list) and all(isinstance(kind, str) for kind in kinds):
        return sorted(set(kinds))
    errors = check.get("errors", [])
    if isinstance(errors, list) and all(isinstance(error, str) for error in errors):
        return semantic_reading_failure_kinds(errors)
    return []


def semantic_readings_failure_hint(check: dict[str, Any]) -> str:
    kinds = semantic_readings_failure_kinds_for(check)
    if not kinds:
        return FAILURE_STAGE_HINTS["semantic_readings_check"]
    return SEMANTIC_READING_FAILURE_HINTS.get(
        kinds[0],
        FAILURE_STAGE_HINTS["semantic_readings_check"],
    )


def semantic_readings_repair_details_for(check: dict[str, Any]) -> dict[str, Any]:
    details = check.get("repair_details")
    return details if isinstance(details, dict) else {}


def string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item]


def int_list(value: Any) -> list[int]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, int)]


def semantic_readings_recovery_actions(check: dict[str, Any]) -> list[dict[str, Any]]:
    details = semantic_readings_repair_details_for(check)
    kinds = semantic_readings_failure_kinds_for(check)
    actions: list[dict[str, Any]] = []
    missing_definitions = string_list(details.get("missing_coq_definitions"))
    if missing_definitions:
        actions.append(
            {
                "kind": "add_missing_coq_definitions",
                "label": "Export missing readings",
                "detail": (
                    "Add Coq/Rocq Definition(s) for: "
                    + ", ".join(missing_definitions)
                    + "."
                ),
                "target_definitions": missing_definitions,
            }
        )
    duplicate_names = string_list(details.get("duplicate_reading_names"))
    if duplicate_names:
        actions.append(
            {
                "kind": "rename_duplicate_readings",
                "label": "Rename duplicate readings",
                "detail": (
                    "Give each semantic reading a unique name; duplicates: "
                    + ", ".join(duplicate_names)
                    + "."
                ),
                "duplicate_reading_names": duplicate_names,
            }
        )
    malformed_indices = int_list(details.get("malformed_reading_indices"))
    if malformed_indices:
        actions.append(
            {
                "kind": "fix_malformed_readings",
                "label": "Fix malformed reading records",
                "detail": (
                    "Repair semantic_readings record(s) at index: "
                    + ", ".join(str(index) for index in malformed_indices)
                    + "."
                ),
                "reading_indices": malformed_indices,
            }
        )
    failed_type_indices = int_list(details.get("failed_type_check_indices"))
    if failed_type_indices:
        actions.append(
            {
                "kind": "fix_reading_type_checks",
                "label": "Fix reading type checks",
                "detail": (
                    "Repair reading-local type_check result(s) at index: "
                    + ", ".join(str(index) for index in failed_type_indices)
                    + "."
                ),
                "reading_indices": failed_type_indices,
            }
        )
    expected_count = details.get("expected_export_count")
    observed_count = details.get("observed_export_count")
    exported_definitions = string_list(details.get("exported_definitions"))
    if expected_count is not None and observed_count != expected_count:
        actions.append(
            {
                "kind": "normalize_reading_exports",
                "label": "Normalize reading exports",
                "detail": (
                    "Registered construction output should expose "
                    f"{expected_count} Prop/PropT definition(s), but exposes "
                    f"{observed_count}."
                ),
                "expected_export_count": expected_count,
                "observed_export_count": observed_count,
                "exported_definitions": exported_definitions,
            }
        )
    if "missing_readings" in kinds:
        actions.append(
            {
                "kind": "add_semantic_readings",
                "label": "Add semantic readings",
                "detail": "Emit at least one normalized semantic_readings record before export.",
            }
        )
    if "unknown_reading_error" in kinds:
        actions.append(
            {
                "kind": "inspect_readings",
                "label": "Inspect semantic readings",
                "detail": "Inspect semantic readings, formulas, and exported Coq definitions.",
            }
        )
    generic = recovery_actions_for("semantic_readings_check")[0]
    if not actions:
        return [generic]
    if all(action.get("kind") != generic["kind"] for action in actions):
        actions.append(generic)
    return actions


def stable_token(value: str) -> str:
    return "".join(char if char.isalnum() or char in {"-", "_"} else "-" for char in value)


def state_lexicon_patch_line(state: str, scale: str, default_source_state: str) -> str:
    return (
        f"{state!r}: StateLexiconEntry("
        f"{scale!r}, default_source_state={default_source_state!r}),"
    )


def state_lexicon_source_line(draft: dict[str, Any]) -> str:
    state = str(draft.get("state", ""))
    scale = str(draft.get("scale", ""))
    source_state = str(draft.get("default_source_state", ""))
    return (
        f'    "{state}": StateLexiconEntry('
        f'"{scale}", default_source_state="{source_state}"),'
    )


def render_lexicon_patch_text(bundle: dict[str, Any]) -> str:
    lines = [
        "# Candidate STATE_LEXICON patch",
        f"# schema_version: {bundle.get('schema_version', LEXICON_PATCH_DRAFTS_SCHEMA)}",
        f"# input_sentence: {bundle.get('input_sentence', '')}",
        "# Review before applying. This file is not applied automatically.",
        "# Target: translator/dependent_type_event_translator.py::STATE_LEXICON",
        "",
    ]
    validation_errors = bundle.get("validation_errors", [])
    if validation_errors:
        lines.append("# Validation errors:")
        lines.extend(f"# - {error}" for error in validation_errors)
        lines.append("")
    drafts = bundle.get("lexicon_patch_drafts", [])
    patch_lines = [
        state_lexicon_source_line(draft)
        for draft in drafts
        if draft.get("can_auto_apply") and not validation_errors
    ]
    pending_drafts = [
        draft
        for draft in drafts
        if not draft.get("can_auto_apply") and draft.get("state_lexicon_patch_line")
    ]
    if not patch_lines:
        lines.append("# No auto-applicable patch lines.")
        if validation_errors:
            lines.append("# Resolve validation errors before copying any candidate line.")
    else:
        lines.append("# Candidate replacement/addition lines:")
        lines.extend(patch_lines)
    if pending_drafts:
        lines.append("")
        lines.append("# Pending human choices:")
        for draft in pending_drafts:
            placeholders = ", ".join(map(str, draft.get("placeholder_fields", []))) or "none"
            lines.append(f"# draft_id: {draft.get('draft_id', '')}")
            lines.append(f"# placeholders: {placeholders}")
            lines.append(f"# preview: {draft.get('state_lexicon_patch_line', '')}")
    return "\n".join(lines) + "\n"


def lexicon_entry_draft(policy: str, state: str, scale: str) -> dict[str, Any]:
    default_source_state = LEXICON_SOURCE_PLACEHOLDER
    return {
        "draft_id": f"state-{stable_token(state)}--{stable_token(policy)}",
        "state": state,
        "scale": scale,
        "default_source_state": default_source_state,
        "allow_unknown_source": False,
        "current_source_policy": policy,
        "source_policy_after_update": "lexical_prestate",
        "requires_human_choice": True,
        "placeholder_fields": ["default_source_state"],
        "can_auto_apply": False,
        "state_lexicon_patch_line": state_lexicon_patch_line(
            state,
            scale,
            default_source_state,
        ),
    }


def warning_action_for_entry(policy: str, state: str, scale: str) -> dict[str, Any] | None:
    if policy == "unknown_source_allowed":
        return {
            "kind": "add_state_prestate",
            "label": "Add lexical pre-state",
            "detail": (
                f"Choose a contextually justified source state for {state} on {scale}, "
                "or keep unknown_state when the source is genuinely underspecified."
            ),
            "lexicon_entry_draft": lexicon_entry_draft(policy, state, scale),
        }
    if policy == "derived_scale_no_known_prestate":
        return {
            "kind": "register_state_lexicon_entry",
            "label": "Register result state",
            "detail": (
                f"Add {state} to STATE_LEXICON with a stable scale and, if justified, "
                "a default_source_state."
            ),
            "lexicon_entry_draft": lexicon_entry_draft(policy, state, scale),
        }
    if policy == "source_state_only":
        return {
            "kind": "license_state_as_target",
            "label": "License target state",
            "detail": (
                f"Decide whether {state} can be a result target on {scale}; if so, "
                "add a default source state."
            ),
            "lexicon_entry_draft": lexicon_entry_draft(policy, state, scale),
        }
    return None


def result_state_warning_for_entry(entry: dict[str, Any]) -> dict[str, Any] | None:
    policy = str(entry.get("source_policy", ""))
    state = str(entry.get("state", ""))
    scale = str(entry.get("scale", ""))
    if policy == "unknown_source_allowed":
        return {
            "kind": "unknown_result_source",
            "state": state,
            "scale": scale,
            "message": (
                f"Result state {state} has no unique lexical pre-state; "
                "source remains unknown_state."
            ),
            "suggested_action": warning_action_for_entry(policy, state, scale),
        }
    if policy == "derived_scale_no_known_prestate":
        return {
            "kind": "derived_result_scale",
            "state": state,
            "scale": scale,
            "message": (
                f"Result state {state} uses a derived scale without a known lexical "
                "pre-state; source remains unknown_state."
            ),
            "suggested_action": warning_action_for_entry(policy, state, scale),
        }
    if policy == "source_state_only":
        return {
            "kind": "source_state_used_as_target",
            "state": state,
            "scale": scale,
            "message": (
                f"Result state {state} is currently licensed only as a source state; "
                "source remains unknown_state."
            ),
            "suggested_action": warning_action_for_entry(policy, state, scale),
        }
    return None


def result_state_warnings(result: dict[str, Any]) -> list[dict[str, Any]]:
    warnings = []
    for entry in result.get("result_state_lexicon", []):
        warning = result_state_warning_for_entry(entry)
        if warning is not None:
            warnings.append(warning)
    return warnings


def lexicon_patch_drafts(result: dict[str, Any]) -> list[dict[str, Any]]:
    diagnostics = result.get("diagnostics", {})
    warnings = diagnostics.get("warnings") or result_state_warnings(result)
    drafts = []
    seen = set()
    for warning in warnings:
        action = warning.get("suggested_action") or {}
        draft = action.get("lexicon_entry_draft")
        if not draft:
            continue
        key = (
            draft.get("state"),
            draft.get("scale"),
            draft.get("current_source_policy"),
            draft.get("source_policy_after_update"),
        )
        if key in seen:
            continue
        seen.add(key)
        drafts.append(dict(draft))
    return drafts


def build_diagnostics(result: dict[str, Any]) -> dict[str, Any]:
    type_check = result.get("type_check", {})
    semantic_readings_check = result.get("semantic_readings_check", {})
    semantic_failure_kinds = (
        semantic_readings_failure_kinds_for(semantic_readings_check)
        if isinstance(semantic_readings_check, dict)
        else []
    )
    semantic_failure_summary = semantic_reading_failure_summary(semantic_failure_kinds)
    semantic_repair_details = (
        semantic_readings_repair_details_for(semantic_readings_check)
        if isinstance(semantic_readings_check, dict)
        else {}
    )
    construction_hygiene = result.get("construction_hygiene", {})
    coq_check = result.get("coq_check", {})
    warnings = result_state_warnings(result)
    drafts = lexicon_patch_drafts({"diagnostics": {"warnings": warnings}})
    stages = {
        "type_check": check_status(type_check.get("ok")) if type_check else "not_applicable",
        "semantic_readings_check": (
            check_status(semantic_readings_check.get("ok"))
            if semantic_readings_check
            else "not_applicable"
        ),
        "construction_hygiene": (
            check_status(construction_hygiene.get("ok"))
            if construction_hygiene
            else "not_applicable"
        ),
        "coq_check": check_status(coq_check.get("ok")) if coq_check else "not_applicable",
    }
    if result.get("ok"):
        summary = "translation verified"
        failure_stage = None
    elif (
        semantic_readings_check
        and semantic_readings_check.get("ok") is False
    ):
        summary = "semantic readings check failed"
        failure_stage = "semantic_readings_check"
    elif construction_hygiene and construction_hygiene.get("ok") is False:
        summary = "construction hygiene failed"
        failure_stage = "construction_hygiene"
    elif coq_check and coq_check.get("ok") is False:
        summary = "coq validation failed"
        failure_stage = "coq_check"
    elif type_check and type_check.get("ok") is False:
        summary = "type check failed"
        failure_stage = "type_check"
    elif not result.get("input_sentence", "").strip():
        summary = "translation failed"
        failure_stage = "input"
    else:
        summary = "translation failed"
        failure_stage = "parsing"
    if failure_stage == "semantic_readings_check" and isinstance(
        semantic_readings_check, dict
    ):
        recovery_hint = semantic_readings_failure_hint(semantic_readings_check)
    else:
        recovery_hint = FAILURE_STAGE_HINTS.get(failure_stage) if failure_stage else None
    if failure_stage == "semantic_readings_check" and isinstance(
        semantic_readings_check, dict
    ):
        recovery_actions = semantic_readings_recovery_actions(semantic_readings_check)
    else:
        recovery_actions = recovery_actions_for(failure_stage)
    return {
        "summary": summary,
        "failure_stage": failure_stage,
        "recovery_hint": recovery_hint,
        "recovery_actions": recovery_actions,
        "stages": stages,
        "semantic_readings_failure_kinds": semantic_failure_kinds,
        "semantic_readings_failure_summary": semantic_failure_summary,
        "semantic_readings_repair_details": semantic_repair_details,
        "warnings": warnings,
        "manual_repair_required": any(
            draft.get("requires_human_choice") for draft in drafts
        ),
        "lexicon_patch_draft_count": len(drafts),
    }


def add_diagnostics(result: dict[str, Any]) -> dict[str, Any]:
    enriched = {**result}
    enriched.setdefault("schema_version", ANALYZE_RESPONSE_SCHEMA)
    enriched.setdefault("result_state_lexicon", [])
    enriched["modifier_role_audit"] = modifier_role_audit(enriched.get("ast", {}))
    enriched["diagnostics"] = build_diagnostics(enriched)
    enriched["lexicon_patch_drafts"] = lexicon_patch_drafts(enriched)
    enriched["patch_text_preview"] = lexicon_patch_text_preview_for_result(enriched)
    return enriched


def modifier_role_audit(ast: Any) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []

    def visit(node: Any, path: str) -> None:
        if isinstance(node, dict):
            if node.get("kind") == "application":
                modifier_roles = node.get("modifier_roles", {})
                if isinstance(modifier_roles, dict):
                    roles = modifier_roles.get("roles", [])
                    if isinstance(roles, list):
                        for entry in roles:
                            if isinstance(entry, dict):
                                records.append(
                                    {
                                        "path": path,
                                        "function": node.get("function", ""),
                                        **entry,
                                    }
                                )
            for key, value in node.items():
                visit(value, f"{path}.{key}")
        elif isinstance(node, list):
            for index, value in enumerate(node):
                visit(value, f"{path}[{index}]")

    visit(ast, "ast")
    return records


def compact_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def status_label(result: dict[str, Any]) -> str:
    if result.get("ok"):
        warnings = result.get("diagnostics", {}).get("warnings", [])
        coq = result.get("coq_check", {})
        if coq.get("status") == "skipped":
            if warnings:
                return "Internally checked with warnings; Coq/Rocq skipped"
            return "Internally checked; Coq/Rocq skipped"
        if warnings:
            return "Translation verified with warnings"
        return "Translation verified"
    return "Needs attention"


def status_detail(result: dict[str, Any]) -> str:
    diagnostics = result.get("diagnostics", {})
    warnings = diagnostics.get("warnings", [])
    failure_stage = diagnostics.get("failure_stage")
    if not failure_stage:
        conclusion = result.get("conclusion", "")
        if warnings:
            warning_text = "; ".join(warning["message"] for warning in warnings)
            repair_count = diagnostics.get("lexicon_patch_draft_count", 0)
            repair_text = (
                f" Manual lexicon repair drafts: {repair_count}."
                if repair_count
                else ""
            )
            if conclusion:
                return f"{conclusion} Warnings: {warning_text}{repair_text}"
            return f"Warnings: {warning_text}{repair_text}"
        return conclusion
    label = FAILURE_STAGE_LABELS.get(failure_stage, failure_stage)
    conclusion = result.get("conclusion", "")
    hint = result.get("diagnostics", {}).get("recovery_hint")
    suffix = f" Suggested next step: {hint}" if hint else ""
    if conclusion:
        return f"{conclusion} Failure stage: {label}.{suffix}"
    return f"Failure stage: {label}.{suffix}"


def construction_rule_summary(result: dict[str, Any]) -> str:
    rule = result.get("construction_rule")
    if not rule:
        return "No registered construction rule matched; fallback or general translator path was used."
    hygiene = result.get("construction_hygiene", {})
    forbidden = rule.get("forbidden_coq_fragments", [])
    hygiene_status = check_status(hygiene.get("ok")) if hygiene else "not_applicable"
    lines = [
        f"id: {rule.get('id', '')}",
        f"label: {rule.get('label', '')}",
        f"phenomenon: {rule.get('phenomenon', '')}",
        f"hygiene: {hygiene_status}",
    ]
    summary = result.get("construction_summary")
    if summary:
        lines.extend(["instance summary:", str(summary)])
    lines.append("hygiene policy:")
    if forbidden:
        lines.extend(f"- {fragment}" for fragment in forbidden)
    else:
        lines.append("- none")
    found = hygiene.get("found_forbidden_fragments", [])
    lines.append("found forbidden fragments:")
    if found:
        lines.extend(f"- {fragment}" for fragment in found)
    else:
        lines.append("- none")
    return "\n".join(lines)


def css_token(value: str) -> str:
    return stable_token(value)


def recovery_action_detail_rows(action: dict[str, Any]) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    list_fields = [
        ("target_definitions", "target definitions"),
        ("duplicate_reading_names", "duplicate readings"),
        ("reading_indices", "reading indices"),
        ("exported_definitions", "exported definitions"),
    ]
    for key, label in list_fields:
        value = action.get(key)
        if isinstance(value, list) and value:
            rows.append((label, ", ".join(str(item) for item in value)))
    expected_count = action.get("expected_export_count")
    observed_count = action.get("observed_export_count")
    if expected_count is not None or observed_count is not None:
        rows.append(
            (
                "export count",
                f"expected {expected_count}; observed {observed_count}",
            )
        )
    return rows


def next_steps_panel(result: dict[str, Any]) -> str:
    actions = result.get("diagnostics", {}).get("recovery_actions", [])
    if not actions:
        body = '<p class="next-step-empty">No recovery actions needed.</p>'
    else:
        items = []
        for action in actions:
            kind = action.get("kind", "")
            label = action.get("label", "")
            detail = action.get("detail", "")
            kind_class = css_token(kind)
            rows = recovery_action_detail_rows(action)
            details_html = ""
            if rows:
                details_html = (
                    '<dl class="next-step-details">'
                    + "".join(
                        f"<dt>{html.escape(label_text)}</dt><dd>{html.escape(value)}</dd>"
                        for label_text, value in rows
                    )
                    + "</dl>"
                )
            items.append(
                '<li '
                f'class="next-step next-step--{html.escape(kind_class)}" '
                f'data-action-kind="{html.escape(kind)}">'
                f'<strong>{html.escape(label)}</strong>'
                f'<code>{html.escape(kind)}</code>'
                f'<p>{html.escape(detail)}</p>'
                f"{details_html}"
                "</li>"
            )
        body = '<ul class="next-step-list">' + "".join(items) + "</ul>"
    return (
        '<section class="panel next-steps-panel">'
        "<h2>Next Steps</h2>"
        f'<div class="next-steps">{body}</div>'
        "</section>"
    )


def semantic_warnings_panel(result: dict[str, Any]) -> str:
    warnings = result.get("diagnostics", {}).get("warnings", [])
    if not warnings:
        body = '<p class="semantic-warning-empty">No semantic warnings.</p>'
    else:
        items = []
        for warning in warnings:
            kind = str(warning.get("kind", ""))
            state = str(warning.get("state", ""))
            scale = str(warning.get("scale", ""))
            message = str(warning.get("message", ""))
            action = warning.get("suggested_action") or {}
            action_kind = str(action.get("kind", ""))
            action_label = str(action.get("label", ""))
            action_detail = str(action.get("detail", ""))
            draft = action.get("lexicon_entry_draft") or {}
            draft_html = ""
            if draft:
                draft_html = (
                    '<dl class="semantic-warning-draft">'
                    f'<dt>draft state</dt><dd>{html.escape(str(draft.get("state", "")))}</dd>'
                    f'<dt>draft scale</dt><dd>{html.escape(str(draft.get("scale", "")))}</dd>'
                    '<dt>draft source</dt>'
                    f'<dd>{html.escape(str(draft.get("default_source_state", "")))}</dd>'
                    '<dt>after policy</dt>'
                    f'<dd>{html.escape(str(draft.get("source_policy_after_update", "")))}</dd>'
                    '</dl>'
                )
            action_html = ""
            if action_kind or action_label or action_detail:
                action_class = css_token(action_kind)
                action_html = (
                    '<div '
                    f'class="semantic-warning-action semantic-warning-action--{html.escape(action_class)}" '
                    f'data-warning-action-kind="{html.escape(action_kind)}">'
                    f'<strong>{html.escape(action_label)}</strong>'
                    f'<code>{html.escape(action_kind)}</code>'
                    f'<p>{html.escape(action_detail)}</p>'
                    f"{draft_html}"
                    '</div>'
                )
            kind_class = css_token(kind)
            items.append(
                '<li '
                f'class="semantic-warning semantic-warning--{html.escape(kind_class)}" '
                f'data-warning-kind="{html.escape(kind)}">'
                f'<strong>{html.escape(kind)}</strong>'
                '<dl>'
                f'<dt>state</dt><dd>{html.escape(state)}</dd>'
                f'<dt>scale</dt><dd>{html.escape(scale)}</dd>'
                '</dl>'
                f'<p>{html.escape(message)}</p>'
                f"{action_html}"
                "</li>"
            )
        body = '<ul class="semantic-warning-list">' + "".join(items) + "</ul>"
    return (
        '<section class="panel semantic-warnings-panel">'
        "<h2>Semantic Warnings</h2>"
        f'<div class="semantic-warnings">{body}</div>'
        "</section>"
    )


def semantic_readings_check_panel(result: dict[str, Any]) -> str:
    check = result.get("semantic_readings_check") or {}
    readings = result.get("semantic_readings") or []
    repair_details = semantic_readings_repair_details_for(check)
    exported_definitions = repair_details.get("exported_definitions")
    if not isinstance(exported_definitions, list):
        exported_definitions = exported_prop_definition_names(result.get("coq_code", ""))
    exported_definition_names = [
        str(name) for name in exported_definitions if isinstance(name, str)
    ]
    if not check:
        body = '<p class="semantic-reading-empty">No semantic readings check available.</p>'
    else:
        status = check_status(check.get("ok"))
        count = check.get("reading_count", 0)
        summary = (
            '<p '
            f'class="semantic-readings-check-summary semantic-readings-check-summary--{html.escape(css_token(status))}" '
            f'data-semantic-readings-status="{html.escape(status)}">'
            f'{html.escape(status)}: {html.escape(str(count))} reading(s)'
            '</p>'
        )
        failure_kinds = semantic_readings_failure_kinds_for(check)
        failure_summary = str(
            check.get("failure_summary") or semantic_reading_failure_summary(failure_kinds)
        )
        if failure_kinds:
            failure_kinds_html = (
                '<ul class="semantic-reading-kind-list">'
                + "".join(
                    '<li '
                    f'class="semantic-reading-kind semantic-reading-kind--{html.escape(css_token(kind))}" '
                    f'data-semantic-reading-kind="{html.escape(kind, quote=True)}">'
                    f'{html.escape(kind)}</li>'
                    for kind in failure_kinds
                )
                + "</ul>"
            )
        else:
            failure_kinds_html = '<p class="semantic-reading-empty">No semantic reading failure kinds.</p>'
        failure_summary_html = (
            '<p class="semantic-reading-failure-summary">'
            f'{html.escape(failure_summary)}'
            '</p>'
        )
        expected_definitions = repair_details.get("expected_coq_definitions", [])
        missing_definitions = repair_details.get("missing_coq_definitions", [])
        duplicate_names = repair_details.get("duplicate_reading_names", [])
        malformed_indices = repair_details.get("malformed_reading_indices", [])
        failed_type_indices = repair_details.get("failed_type_check_indices", [])
        expected_export_count = repair_details.get("expected_export_count")
        observed_export_count = repair_details.get("observed_export_count")
        detail_rows = []
        if isinstance(expected_definitions, list) and expected_definitions:
            detail_rows.append(
                (
                    "expected Coq/Rocq definitions",
                    ", ".join(str(definition) for definition in expected_definitions),
                )
            )
        if isinstance(missing_definitions, list) and missing_definitions:
            detail_rows.append(
                (
                    "missing Coq/Rocq definitions",
                    ", ".join(str(definition) for definition in missing_definitions),
                )
            )
        if isinstance(duplicate_names, list) and duplicate_names:
            detail_rows.append(
                ("duplicate reading names", ", ".join(str(name) for name in duplicate_names))
            )
        if isinstance(malformed_indices, list) and malformed_indices:
            detail_rows.append(
                (
                    "malformed reading indices",
                    ", ".join(str(index) for index in malformed_indices),
                )
            )
        if isinstance(failed_type_indices, list) and failed_type_indices:
            detail_rows.append(
                (
                    "failed type-check indices",
                    ", ".join(str(index) for index in failed_type_indices),
                )
            )
        if expected_export_count is not None:
            expected_text = str(expected_export_count)
            observed_text = "none" if observed_export_count is None else str(observed_export_count)
            detail_rows.append(
                ("export count", f"expected {expected_text}; observed {observed_text}")
            )
        if detail_rows:
            repair_details_html = (
                '<dl class="semantic-reading-repair-details">'
                + "".join(
                    f"<dt>{html.escape(label)}</dt><dd>{html.escape(value)}</dd>"
                    for label, value in detail_rows
                )
                + "</dl>"
            )
        else:
            repair_details_html = (
                '<p class="semantic-reading-empty">No semantic reading repair details.</p>'
            )
        rows = []
        for index, reading in enumerate(readings if isinstance(readings, list) else []):
            if not isinstance(reading, dict):
                continue
            name = str(reading.get("name", f"reading_{index + 1}"))
            scope = str(reading.get("scope", ""))
            source = str(reading.get("source", ""))
            coq_definition = str(reading.get("coq_definition", ""))
            type_check = reading.get("type_check") or {}
            type_status = (
                check_status(type_check.get("ok"))
                if isinstance(type_check, dict)
                else "not_applicable"
            )
            exported = bool(coq_definition and coq_definition in exported_definition_names)
            exported_status = "yes" if exported else "no"
            row_status = "passed" if type_status == "passed" and (exported or not coq_definition) else "failed"
            rows.append(
                '<li '
                f'class="semantic-reading-audit semantic-reading-audit--{html.escape(row_status)}" '
                f'data-reading-name="{html.escape(name, quote=True)}" '
                f'data-coq-definition="{html.escape(coq_definition, quote=True)}" '
                f'data-coq-exported="{html.escape(exported_status, quote=True)}">'
                f'<strong>{html.escape(name)}</strong>'
                '<dl>'
                f'<dt>scope</dt><dd>{html.escape(scope or "none")}</dd>'
                f'<dt>source</dt><dd>{html.escape(source or "none")}</dd>'
                f'<dt>coq</dt><dd>{html.escape(coq_definition or "none")}</dd>'
                f'<dt>exported</dt><dd>{html.escape(exported_status)}</dd>'
                f'<dt>type check</dt><dd>{html.escape(type_status)}</dd>'
                '</dl>'
                '</li>'
            )
        readings_html = (
            '<ul class="semantic-reading-audit-list">' + "".join(rows) + "</ul>"
            if rows
            else '<p class="semantic-reading-empty">No normalized readings were emitted.</p>'
        )
        errors = check.get("errors") if isinstance(check, dict) else []
        if isinstance(errors, list) and errors:
            errors_html = (
                '<ul class="semantic-reading-error-list">'
                + "".join(
                    f'<li data-semantic-reading-error="{html.escape(str(error), quote=True)}">'
                    f'{html.escape(str(error))}</li>'
                    for error in errors
                )
                + "</ul>"
            )
        else:
            errors_html = '<p class="semantic-reading-empty">No semantic reading errors.</p>'
        definitions_html = (
            '<p class="semantic-reading-export-summary">'
            "exported Prop/PropT definitions: "
            f'{html.escape(", ".join(exported_definition_names) or "none")}'
            '</p>'
        )
        raw_json = html.escape(compact_json(check))
        body = (
            summary
            + failure_summary_html
            + failure_kinds_html
            + definitions_html
            + repair_details_html
            + readings_html
            + errors_html
            + '<details class="semantic-reading-raw"><summary>Raw check JSON</summary>'
            f'<pre>{raw_json}</pre>'
            '</details>'
        )
    return (
        '<section class="panel semantic-readings-check-panel">'
        "<h2>Semantic Readings Check</h2>"
        f'<div class="semantic-readings-check">{body}</div>'
        "</section>"
    )


def result_state_lexicon_panel(result: dict[str, Any]) -> str:
    entries = result.get("result_state_lexicon", [])
    if not entries:
        body = '<p class="lexicon-empty">No result states detected.</p>'
    else:
        rows = []
        for entry in entries:
            state = str(entry.get("state", ""))
            scale = str(entry.get("scale", ""))
            source = entry.get("default_source_state")
            source_text = str(source) if source is not None else "unknown_state"
            policy = str(entry.get("source_policy", ""))
            warning = result_state_warning_for_entry(entry)
            warning_html = (
                f'<p class="lexicon-warning">{html.escape(warning["message"])}</p>'
                if warning
                else ""
            )
            item_class = "lexicon-entry lexicon-entry--warning" if warning else "lexicon-entry"
            rows.append(
                f'<li class="{item_class}">'
                f'<strong>{html.escape(state)}</strong>'
                '<dl>'
                f'<dt>scale</dt><dd>{html.escape(scale)}</dd>'
                f'<dt>source</dt><dd>{html.escape(source_text)}</dd>'
                f'<dt>policy</dt><dd>{html.escape(policy)}</dd>'
                '</dl>'
                f"{warning_html}"
                '</li>'
            )
        body = '<ul class="lexicon-list">' + "".join(rows) + "</ul>"
    return (
        '<section class="panel result-lexicon-panel">'
        "<h2>Result State Lexicon</h2>"
        f'<div class="result-lexicon">{body}</div>'
        "</section>"
    )


def hidden_input(name: str, value: str) -> str:
    return (
        f'<input type="hidden" name="{html.escape(name, quote=True)}" '
        f'value="{html.escape(value, quote=True)}">'
    )


def lexicon_resolve_form(draft: dict[str, Any], sentence: str, require_coq: bool) -> str:
    if not draft.get("requires_human_choice"):
        return ""
    draft_id = str(draft.get("draft_id", ""))
    hidden_fields = [
        hidden_input("sentence", sentence),
        hidden_input("format", "patch"),
        hidden_input("resolve_draft_id", draft_id),
    ]
    if require_coq:
        hidden_fields.append(hidden_input("require_coq", "1"))
    return (
        '<form class="lexicon-resolve-form" method="get" '
        'action="/api/lexicon-patch-drafts" '
        f'data-resolve-draft-id="{html.escape(draft_id, quote=True)}">'
        f"{''.join(hidden_fields)}"
        '<input name="source_state" type="text" '
        'placeholder="source state" aria-label="Source state">'
        '<button type="submit">Preview resolved patch</button>'
        "</form>"
    )


def lexicon_patch_drafts_panel(
    result: dict[str, Any],
    sentence: str = "",
    require_coq: bool = False,
) -> str:
    drafts = result.get("lexicon_patch_drafts", [])
    if not drafts:
        body = '<p class="lexicon-draft-empty">No lexicon patch drafts.</p>'
    else:
        rows = []
        for draft in drafts:
            state = str(draft.get("state", ""))
            scale = str(draft.get("scale", ""))
            source = str(draft.get("default_source_state", ""))
            current_policy = str(draft.get("current_source_policy", ""))
            next_policy = str(draft.get("source_policy_after_update", ""))
            patch_line = str(draft.get("state_lexicon_patch_line", ""))
            auto_apply = "yes" if draft.get("can_auto_apply") else "no"
            placeholders = ", ".join(map(str, draft.get("placeholder_fields", []))) or "none"
            rows.append(
                '<li '
                'class="lexicon-draft" '
                f'data-draft-id="{html.escape(str(draft.get("draft_id", "")))}" '
                f'data-draft-state="{html.escape(state)}" '
                f'data-draft-current-policy="{html.escape(current_policy)}">'
                f'<strong>{html.escape(state)}</strong>'
                '<dl>'
                f'<dt>scale</dt><dd>{html.escape(scale)}</dd>'
                f'<dt>source</dt><dd>{html.escape(source)}</dd>'
                f'<dt>current</dt><dd>{html.escape(current_policy)}</dd>'
                f'<dt>after</dt><dd>{html.escape(next_policy)}</dd>'
                f'<dt>auto apply</dt><dd>{html.escape(auto_apply)}</dd>'
                f'<dt>placeholders</dt><dd>{html.escape(placeholders)}</dd>'
                f'<dt>entry</dt><dd>{html.escape(patch_line)}</dd>'
                '</dl>'
                f"{lexicon_resolve_form(draft, sentence, require_coq)}"
                '</li>'
            )
        body = '<ul class="lexicon-draft-list">' + "".join(rows) + "</ul>"
    return (
        '<section class="panel lexicon-drafts-panel">'
        "<h2>Lexicon Patch Drafts</h2>"
        f'<div class="lexicon-drafts">{body}</div>'
        "</section>"
    )


def panel(title: str, body: str) -> str:
    return (
        '<section class="panel">'
        f"<h2>{html.escape(title)}</h2>"
        f"<pre>{html.escape(body)}</pre>"
        "</section>"
    )


def patch_text_api_href(sentence: str, require_coq: bool) -> str:
    params = {"sentence": sentence, "format": "patch"}
    if require_coq:
        params["require_coq"] = "1"
    return f"/api/lexicon-patch-drafts?{urlencode(params)}"


def patch_text_panel(body: str, href: str) -> str:
    escaped_href = html.escape(href, quote=True)
    return (
        '<section class="panel patch-text-panel">'
        "<h2>Lexicon Patch Text Preview</h2>"
        '<div class="panel-action">'
        f'<a class="patch-text-link" href="{escaped_href}" '
        'data-patch-format="text" download="state_lexicon.patch">'
        "Open patch text"
        "</a>"
        "</div>"
        f"<pre>{html.escape(body)}</pre>"
        "</section>"
    )


def lexicon_patch_text_preview_for_result(result: dict[str, Any]) -> str:
    return render_lexicon_patch_text(
        {
            "schema_version": LEXICON_PATCH_DRAFTS_SCHEMA,
            "input_sentence": result.get("input_sentence", ""),
            "validation_errors": [],
            "lexicon_patch_drafts": result.get("lexicon_patch_drafts", []),
        }
    )


def render_page(sentence: str = DEFAULT_SENTENCE, require_coq: bool = False) -> str:
    result = analyze_sentence(sentence, require_coq=require_coq)
    event_semantics = compact_json(result.get("event_semantics", result.get("error", "")))
    dependent = result.get("dependent_type_translation", result.get("error", ""))
    ast = compact_json(result.get("ast", {}))
    type_check = compact_json(result.get("type_check", {}))
    semantic_readings = compact_json(result.get("semantic_readings", []))
    modifier_roles = compact_json(result.get("modifier_role_audit", []))
    result_lexicon = compact_json(result.get("result_state_lexicon", []))
    patch_drafts = compact_json(result.get("lexicon_patch_drafts", []))
    patch_text_preview = result.get("patch_text_preview") or lexicon_patch_text_preview_for_result(result)
    patch_text_href = patch_text_api_href(sentence, require_coq)
    construction = construction_rule_summary(result)
    diagnostics = compact_json(result.get("diagnostics", {}))
    conclusion = result.get("conclusion", "")
    api_contract = compact_json(
        {
            "schema_version": result.get("schema_version", ANALYZE_RESPONSE_SCHEMA),
            "response_kind": "analysis",
            "endpoint": "/api/analyze",
        }
    )
    coq_code = result.get("coq_code", "")
    coq_check = compact_json(result.get("coq_check", {}))
    checked = " checked" if require_coq else ""
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Dependent-Type Event Semantics</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #17212b;
      --muted: #5d6b78;
      --line: #d8dee6;
      --surface: #f7f9fb;
      --accent: #0f766e;
      --accent-soft: #e6f3f1;
      --warning: #92400e;
      --warning-soft: #fffbeb;
      --error: #9f1239;
      --error-soft: #fff1f2;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: var(--ink);
      background: #ffffff;
    }}
    main {{
      max-width: 1180px;
      margin: 0 auto;
      padding: 28px 20px 40px;
    }}
    header {{
      display: flex;
      justify-content: space-between;
      gap: 20px;
      align-items: end;
      border-bottom: 1px solid var(--line);
      padding-bottom: 16px;
      margin-bottom: 20px;
    }}
    h1 {{
      font-size: 24px;
      line-height: 1.2;
      margin: 0 0 6px;
      letter-spacing: 0;
    }}
    p {{
      margin: 0;
      color: var(--muted);
      line-height: 1.45;
    }}
    .analysis-form {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto auto;
      gap: 10px;
      align-items: center;
      margin: 20px 0;
    }}
    input[type="text"] {{
      width: 100%;
      min-height: 42px;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 9px 11px;
      font-size: 15px;
    }}
    label {{
      display: inline-flex;
      gap: 7px;
      align-items: center;
      color: var(--muted);
      white-space: nowrap;
      font-size: 14px;
    }}
    button {{
      min-height: 42px;
      border: 0;
      border-radius: 6px;
      background: var(--accent);
      color: white;
      padding: 0 16px;
      font-weight: 650;
      cursor: pointer;
    }}
    .status {{
      border: 1px solid {('#fecdd3' if not result.get('ok') else '#b7ded8')};
      background: {('var(--error-soft)' if not result.get('ok') else 'var(--accent-soft)')};
      color: {('var(--error)' if not result.get('ok') else '#115e59')};
      border-radius: 6px;
      padding: 12px 14px;
      margin-bottom: 18px;
      font-weight: 650;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 14px;
    }}
    .panel {{
      border: 1px solid var(--line);
      border-radius: 6px;
      background: var(--surface);
      min-width: 0;
      overflow: hidden;
    }}
    .next-steps {{
      padding: 12px;
    }}
    .result-lexicon {{
      padding: 12px;
    }}
    .semantic-warnings {{
      padding: 12px;
    }}
    .lexicon-drafts {{
      padding: 12px;
    }}
    .panel-action {{
      border-bottom: 1px solid var(--line);
      background: #ffffff;
      padding: 9px 12px;
    }}
    .patch-text-link {{
      display: inline-flex;
      align-items: center;
      min-height: 32px;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 0 10px;
      color: var(--accent);
      background: #ffffff;
      font-size: 13px;
      font-weight: 650;
      text-decoration: none;
    }}
    .patch-text-link:focus,
    .patch-text-link:hover {{
      background: var(--accent-soft);
    }}
    .next-step-list {{
      list-style: none;
      margin: 0;
      padding: 0;
      display: grid;
      gap: 10px;
    }}
    .semantic-warning-list {{
      list-style: none;
      margin: 0;
      padding: 0;
      display: grid;
      gap: 10px;
    }}
    .lexicon-draft-list {{
      list-style: none;
      margin: 0;
      padding: 0;
      display: grid;
      gap: 10px;
    }}
    .next-step {{
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #ffffff;
      padding: 10px;
      display: grid;
      gap: 6px;
    }}
    .next-step strong {{
      font-size: 14px;
    }}
    .next-step code {{
      width: fit-content;
      color: var(--muted);
      font: 12px/1.35 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    }}
    .next-step p,
    .next-step-empty,
    .semantic-warning-empty,
    .lexicon-empty,
    .lexicon-draft-empty {{
      margin: 0;
      color: var(--muted);
      line-height: 1.45;
    }}
    .next-step-details {{
      display: grid;
      grid-template-columns: minmax(120px, auto) minmax(0, 1fr);
      gap: 4px 10px;
      margin: 0;
      color: var(--muted);
      font-size: 12px;
    }}
    .next-step-details dd {{
      margin: 0;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      word-break: break-word;
    }}
    .semantic-warning {{
      border-left: 3px solid var(--warning);
      background: var(--warning-soft);
      padding: 9px 10px;
      display: grid;
      gap: 6px;
    }}
    .semantic-warning strong {{
      font-size: 13px;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    }}
    .semantic-warning dl {{
      display: grid;
      grid-template-columns: minmax(56px, auto) minmax(0, 1fr);
      gap: 4px 10px;
      margin: 0;
      font-size: 13px;
    }}
    .semantic-warning dt {{
      color: var(--muted);
    }}
    .semantic-warning dd {{
      margin: 0;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      word-break: break-word;
    }}
    .semantic-warning p {{
      margin: 0;
      color: var(--warning);
      line-height: 1.45;
      font-size: 13px;
    }}
    .semantic-warning-action {{
      border-top: 1px solid #fde68a;
      padding-top: 7px;
      display: grid;
      gap: 4px;
    }}
    .semantic-warning-action strong {{
      font-size: 13px;
      font-family: inherit;
    }}
    .semantic-warning-action code {{
      width: fit-content;
      color: var(--muted);
      font: 12px/1.35 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    }}
    .semantic-warning-action p {{
      color: var(--muted);
    }}
    .semantic-warning-action .semantic-warning-draft {{
      margin-top: 2px;
    }}
    .semantic-readings-check {{
      padding: 12px;
      display: grid;
      gap: 10px;
    }}
    .semantic-readings-check-summary {{
      margin: 0;
      width: fit-content;
      border-radius: 4px;
      padding: 5px 8px;
      font: 13px/1.35 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      background: var(--accent-soft);
      color: var(--accent);
    }}
    .semantic-readings-check-summary--failed {{
      background: var(--error-soft);
      color: var(--error);
    }}
    .semantic-reading-export-summary,
    .semantic-reading-failure-summary,
    .semantic-reading-empty {{
      margin: 0;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.45;
    }}
    .semantic-reading-kind-list {{
      list-style: none;
      margin: 0;
      padding: 0;
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }}
    .semantic-reading-kind {{
      border: 1px solid var(--line);
      border-radius: 999px;
      background: #ffffff;
      color: var(--muted);
      padding: 3px 8px;
      font: 12px/1.3 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    }}
    .semantic-reading-repair-details {{
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #ffffff;
      display: grid;
      grid-template-columns: minmax(150px, auto) minmax(0, 1fr);
      gap: 5px 10px;
      margin: 0;
      padding: 9px 10px;
      font-size: 13px;
    }}
    .semantic-reading-repair-details dt {{
      color: var(--muted);
    }}
    .semantic-reading-repair-details dd {{
      margin: 0;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      word-break: break-word;
    }}
    .semantic-reading-audit-list,
    .semantic-reading-error-list {{
      list-style: none;
      margin: 0;
      padding: 0;
      display: grid;
      gap: 8px;
    }}
    .semantic-reading-audit {{
      border-left: 3px solid var(--accent);
      background: #ffffff;
      padding: 9px 10px;
      display: grid;
      gap: 6px;
    }}
    .semantic-reading-audit--failed {{
      border-left-color: var(--error);
      background: var(--error-soft);
    }}
    .semantic-reading-audit strong {{
      font-size: 13px;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    }}
    .semantic-reading-audit dl {{
      display: grid;
      grid-template-columns: minmax(78px, auto) minmax(0, 1fr);
      gap: 4px 10px;
      margin: 0;
      font-size: 13px;
    }}
    .semantic-reading-audit dt {{
      color: var(--muted);
    }}
    .semantic-reading-audit dd {{
      margin: 0;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      word-break: break-word;
    }}
    .semantic-reading-error-list li {{
      border-left: 3px solid var(--error);
      background: var(--error-soft);
      color: var(--error);
      padding: 8px 10px;
      font-size: 13px;
      line-height: 1.45;
    }}
    .semantic-reading-raw summary {{
      cursor: pointer;
      color: var(--muted);
      font-size: 13px;
    }}
    .semantic-reading-raw pre {{
      margin-top: 8px;
      min-height: 0;
    }}
    .lexicon-list {{
      list-style: none;
      margin: 0;
      padding: 0;
      display: grid;
      gap: 10px;
    }}
    .lexicon-entry {{
      border-left: 3px solid var(--accent);
      background: #ffffff;
      padding: 9px 10px;
    }}
    .lexicon-entry--warning {{
      border-left-color: var(--warning);
      background: var(--warning-soft);
    }}
    .lexicon-entry strong {{
      display: block;
      margin-bottom: 6px;
      font-size: 14px;
    }}
    .lexicon-entry dl {{
      display: grid;
      grid-template-columns: minmax(72px, auto) minmax(0, 1fr);
      gap: 4px 10px;
      margin: 0;
      font-size: 13px;
    }}
    .lexicon-entry dt {{
      color: var(--muted);
    }}
    .lexicon-entry dd {{
      margin: 0;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      word-break: break-word;
    }}
    .lexicon-warning {{
      margin-top: 8px;
      color: var(--warning);
      font-size: 13px;
    }}
    .lexicon-draft {{
      border-left: 3px solid var(--warning);
      background: #ffffff;
      padding: 9px 10px;
    }}
    .lexicon-draft strong {{
      display: block;
      margin-bottom: 6px;
      font-size: 14px;
    }}
    .lexicon-draft dl {{
      display: grid;
      grid-template-columns: minmax(72px, auto) minmax(0, 1fr);
      gap: 4px 10px;
      margin: 0;
      font-size: 13px;
    }}
    .lexicon-draft dt {{
      color: var(--muted);
    }}
    .lexicon-draft dd {{
      margin: 0;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      word-break: break-word;
    }}
    .lexicon-resolve-form {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 8px;
      margin-top: 10px;
    }}
    .lexicon-resolve-form input[type="text"] {{
      min-height: 34px;
      font-size: 13px;
      padding: 7px 9px;
    }}
    .lexicon-resolve-form button {{
      min-height: 34px;
      font-size: 13px;
      padding: 0 10px;
    }}
    h2 {{
      font-size: 14px;
      margin: 0;
      padding: 10px 12px;
      border-bottom: 1px solid var(--line);
      background: #ffffff;
      letter-spacing: 0;
    }}
    pre {{
      margin: 0;
      padding: 12px;
      min-height: 132px;
      max-height: 360px;
      overflow: auto;
      white-space: pre-wrap;
      word-break: break-word;
      font: 13px/1.45 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    }}
    @media (max-width: 760px) {{
      header, .analysis-form, .grid {{ grid-template-columns: 1fr; display: grid; }}
      .lexicon-resolve-form {{ grid-template-columns: 1fr; }}
      label {{ white-space: normal; }}
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <div>
        <h1>Dependent-Type Event Semantics</h1>
        <p>Natural-language input to event semantics, dependent-type translation, and Coq/Rocq validation.</p>
      </div>
    </header>
    <form class="analysis-form" method="get" action="/">
      <input name="sentence" type="text" value="{html.escape(sentence)}" aria-label="Sentence">
      <label><input name="require_coq" type="checkbox" value="1"{checked}> require Coq/Rocq</label>
      <button type="submit">Analyze</button>
    </form>
    <div class="status">{html.escape(status_label(result))}: {html.escape(status_detail(result))}</div>
    <div class="grid">
      {panel("Event Semantics", event_semantics)}
      {panel("Dependent-Type Translation", dependent)}
      {result_state_lexicon_panel(result)}
      {panel("Diagnostics", diagnostics)}
      {panel("API Contract", api_contract)}
      {panel("Conclusion", conclusion)}
      {semantic_warnings_panel(result)}
      {lexicon_patch_drafts_panel(result, sentence, require_coq)}
      {next_steps_panel(result)}
      {panel("Construction Rule", construction)}
      {panel("Modifier Role Audit", modifier_roles)}
      {panel("Semantic Readings", semantic_readings)}
      {semantic_readings_check_panel(result)}
      {panel("AST", ast)}
      {panel("Type Check", type_check)}
      {panel("Result State Lexicon JSON", result_lexicon)}
      {panel("Lexicon Patch Drafts JSON", patch_drafts)}
      {patch_text_panel(patch_text_preview, patch_text_href)}
      {panel("Coq/Rocq Check", coq_check)}
      {panel("Generated Coq", coq_code)}
    </div>
  </main>
</body>
</html>
"""


class PipelineHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/analyze":
            self.write_json_response(self.handle_api(parsed.query))
            return
        if parsed.path == "/api/lexicon-patch-drafts":
            if self.patch_response_format(parsed.query) == "patch":
                self.write_text_response(self.handle_patch_text_api(parsed.query))
                return
            self.write_json_response(self.handle_patch_api(parsed.query))
            return
        if parsed.path not in {"/", ""}:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        params = parse_qs(parsed.query)
        sentence = params.get("sentence", [DEFAULT_SENTENCE])[0]
        require_coq = params.get("require_coq", ["0"])[0] == "1"
        self.write_html_response(render_page(sentence, require_coq=require_coq))

    def handle_api(self, query: str) -> dict[str, Any]:
        params = parse_qs(query)
        sentence = params.get("sentence", [""])[0]
        require_coq = params.get("require_coq", ["0"])[0] == "1"
        return analyze_sentence(sentence, require_coq=require_coq)

    def handle_patch_api(self, query: str) -> dict[str, Any]:
        params = parse_qs(query)
        sentence = params.get("sentence", [""])[0]
        require_coq = params.get("require_coq", ["0"])[0] == "1"
        resolutions, resolution_errors = parse_patch_resolution_params(params)
        return build_lexicon_patch_bundle(
            sentence,
            require_coq=require_coq,
            resolutions=resolutions,
            resolution_errors=resolution_errors,
        )

    def handle_patch_text_api(self, query: str) -> str:
        return str(self.handle_patch_api(query).get("patch_text_preview", ""))

    def patch_response_format(self, query: str) -> str:
        params = parse_qs(query)
        return params.get("format", ["json"])[0]

    def write_html_response(self, content: str) -> None:
        encoded = content.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def write_text_response(self, content: str) -> None:
        encoded = content.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def write_json_response(self, content: dict[str, Any]) -> None:
        encoded = compact_json(content).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local web demo.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument(
        "--render-static",
        type=Path,
        help="Write a static HTML preview instead of starting a server.",
    )
    parser.add_argument(
        "--sentence",
        default=DEFAULT_SENTENCE,
        help="Sentence used for --render-static output.",
    )
    args = parser.parse_args()
    if args.render_static:
        args.render_static.write_text(render_page(args.sentence), encoding="utf-8")
        print(f"Wrote {args.render_static}")
        return
    server = ThreadingHTTPServer((args.host, args.port), PipelineHandler)
    print(f"Serving http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
