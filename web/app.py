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
    CONSTRUCTION_RULE_DRAFT_SCHEMA,
    check_semantic_readings,
    construction_fragment_manifest,
    exported_prop_definition_names,
    failure_verification_scope,
    run_pipeline,
    semantic_reading_failure_kinds,
    semantic_reading_failure_summary,
    semantic_readings_check_payload,
    semantic_readings_repair_details,
)
from translator.surface_type_contracts import (
    modified_transitive_surface_type_contract_registry,
    surface_type_contract_diagnostic_report,
)
from web.diagnostic_contract import (
    DIAGNOSTIC_FAILURE_STAGES,
    DIAGNOSTIC_REPAIR_PLAN_AUTOMATION_MODES,
    DIAGNOSTIC_RECOVERY_ACTION_KINDS,
    DiagnosticFixtureSpec,
    INSPECTION_ONLY_RECOVERY_ACTION_KINDS,
    REQUIRED_DIAGNOSTIC_FIXTURE_STAGES,
    SEMANTIC_READING_CONTRACT_FIELDS,
    recovery_action_automation_mode,
    recovery_action_can_auto_run,
)


DEFAULT_SENTENCE = "John knocked twice"
ANALYZE_RESPONSE_SCHEMA = "analyze.v1"
LEXICON_PATCH_DRAFTS_SCHEMA = "lexicon_patch_drafts.v1"
CONSTRUCTION_RULE_DRAFT_RESPONSE_SCHEMA = "construction_rule_draft_response.v1"
CERTIFIED_FRAGMENT_SCHEMA = "certified_fragment.v1"
DIAGNOSTIC_CONTRACT_SCHEMA = "diagnostic_contract.v1"
DIAGNOSTIC_FIXTURES_SCHEMA = "diagnostic_fixtures.v1"
RECOVERY_ACTION_SCHEMA = "diagnostic_recovery_action.v1"
RECOVERY_REPAIR_PLAN_SCHEMA = "diagnostic_repair_plan.v1"
RECOVERY_INSPECTION_RUN_SCHEMA = "diagnostic_inspection_run.v1"
LEXICON_SOURCE_PLACEHOLDER = "<choose_source_state>"
DEFAULT_DIAGNOSTIC_FIXTURE_CASE = "semantic_readings_missing_export"
DIAGNOSTIC_FIXTURE_SPECS = (
    DiagnosticFixtureSpec(
        case="construction_hygiene_failure",
        label="Construction Hygiene",
        failure_stage="construction_hygiene",
        recovery_action_kinds=("inspect_coq",),
    ),
    DiagnosticFixtureSpec(
        case="coq_check_failure",
        label="Coq/Rocq Check",
        failure_stage="coq_check",
        recovery_action_kinds=("inspect_coq",),
    ),
    DiagnosticFixtureSpec(
        case="semantic_readings_export_count_mismatch",
        label="Reading Export Count",
        failure_stage="semantic_readings_check",
        recovery_action_kinds=("normalize_reading_exports", "inspect_readings"),
    ),
    DiagnosticFixtureSpec(
        case="semantic_readings_malformed",
        label="Malformed Readings",
        failure_stage="semantic_readings_check",
        recovery_action_kinds=(
            "fix_malformed_readings",
            "fix_reading_type_checks",
            "inspect_readings",
        ),
    ),
    DiagnosticFixtureSpec(
        case="semantic_readings_missing_export",
        label="Missing Reading Export",
        failure_stage="semantic_readings_check",
        recovery_action_kinds=("add_missing_coq_definitions", "inspect_readings"),
    ),
    DiagnosticFixtureSpec(
        case="type_check_failure",
        label="Type Check",
        failure_stage="type_check",
        recovery_action_kinds=("inspect_ast",),
    ),
)
DIAGNOSTIC_FIXTURE_CASES = frozenset(spec.case for spec in DIAGNOSTIC_FIXTURE_SPECS)
DIAGNOSTIC_FIXTURE_LABELS = {
    spec.case: spec.label for spec in DIAGNOSTIC_FIXTURE_SPECS
}
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
            "verification_scope": failure_verification_scope("empty input"),
            "conclusion": "Translation failed before parsing.",
        }
        return add_diagnostics(result)
    return add_diagnostics(run_pipeline(sentence, require_coq=require_coq))


def surface_type_contract_diagnostics_context() -> dict[str, Any]:
    registry = modified_transitive_surface_type_contract_registry()
    report = surface_type_contract_diagnostic_report(registry)
    categories = [
        item
        for item in report.get("categories", [])
        if isinstance(item, dict)
    ]
    category_ids = [
        str(item.get("category", ""))
        for item in categories
        if isinstance(item.get("category"), str)
    ]
    return {
        "schema_version": report.get("schema_version"),
        "registry_schema": registry.get("schema_version"),
        "registry_id": registry.get("registry_id"),
        "source": registry.get("source"),
        "ok": report.get("ok"),
        "error_count": report.get("error_count"),
        "category_count": len(categories),
        "category_ids": category_ids,
        "categories": categories,
    }


def surface_type_contract_diagnostic_category_text(context: dict[str, Any]) -> str:
    category_ids = context.get("category_ids")
    if not isinstance(category_ids, list):
        return ""
    return ",".join(
        str(category_id)
        for category_id in category_ids
        if isinstance(category_id, str)
    )


def diagnostic_fixture_result(case: str = DEFAULT_DIAGNOSTIC_FIXTURE_CASE) -> dict[str, Any]:
    case = case.strip() or DEFAULT_DIAGNOSTIC_FIXTURE_CASE
    if case not in DIAGNOSTIC_FIXTURE_CASES:
        return add_diagnostics(
            {
                "ok": False,
                "input_sentence": f"diagnostic fixture: {case}",
                "error": f"Unknown diagnostic fixture {case!r}.",
                "available_diagnostic_fixtures": sorted(DIAGNOSTIC_FIXTURE_CASES),
                "conclusion": "Diagnostic fixture failed before analysis.",
            }
        )

    passing_coq_code = "Definition fixture_reading : Prop := True.\n"
    passing_semantic_readings = [
        {
            "name": "fixture_reading",
            "source": "diagnostic_fixture",
            "scope": "diagnostic_fixture",
            "dependent_type_translation": "fixture_reading : Prop",
            "coq_definition": "fixture_reading",
            "attachment_summary": {
                "kind": "diagnostic_fixture",
                "typed_modifiers": [],
                "typed_np_restrictors": [],
                "typed_time_modifiers": [],
                "relative_objects": [],
            },
            "reading_explanation": (
                "Diagnostic fixture reading fixture_reading is an already "
                "well-formed Prop export used to exercise later failure stages."
            ),
            "type_check": {"ok": True, "type": "Prop", "errors": []},
        }
    ]

    coq_code = "Definition other_reading : Prop := True.\n"
    semantic_readings: list[dict[str, Any]] = [
        {
            "name": "missing_reading",
            "source": "diagnostic_fixture",
            "scope": "diagnostic_fixture",
            "dependent_type_translation": "missing_reading : PropT",
            "coq_definition": "missing_reading",
            "attachment_summary": {
                "kind": "diagnostic_fixture",
                "typed_modifiers": [],
                "typed_np_restrictors": [],
                "typed_time_modifiers": [],
                "relative_objects": [],
            },
            "reading_explanation": (
                "Diagnostic fixture reading missing_reading is well-formed but "
                "intentionally absent from the exported Coq/Rocq definitions."
            ),
            "type_check": {"ok": True, "type": "PropT", "errors": []},
        }
    ]
    semantic_readings_check = check_semantic_readings(semantic_readings, coq_code)
    dependent_type_translation = "diagnostic fixture for semantic_readings_check"
    ast = {"kind": "diagnostic_fixture", "case": case}
    type_check = {"ok": True, "type": "Prop", "errors": []}
    construction_hygiene = {"ok": None, "checked": False}
    coq_check = {
        "ok": None,
        "status": "skipped",
        "message": "Skipped Coq/Rocq validation because semantic_readings_check failed.",
    }
    conclusion = "Diagnostic fixture: semantic readings audit failed before Coq/Rocq validation."

    if case == "semantic_readings_export_count_mismatch":
        coq_code = (
            "Definition first_reading : Prop := True.\n"
            "Definition second_reading : Prop := True.\n"
        )
        semantic_readings = []
        semantic_readings_check = semantic_readings_check_payload(
            checked=True,
            ok=False,
            reading_count=0,
            errors=[
                (
                    "registered construction outputs without explicit semantic_readings "
                    "must export exactly one Prop/PropT definition"
                )
            ],
            repair_details=semantic_readings_repair_details(
                exported_definitions=["first_reading", "second_reading"],
                expected_export_count=1,
                observed_export_count=2,
            ),
        )
    elif case == "semantic_readings_malformed":
        coq_code = "Definition bad_type : Prop := True.\n"
        semantic_readings = [
            {
                "name": "bad_type",
                "source": "diagnostic_fixture",
                "scope": "diagnostic_fixture",
                "dependent_type_translation": "bad_type : Prop",
                "coq_definition": "bad_type",
                "attachment_summary": {
                    "kind": "diagnostic_fixture",
                    "typed_modifiers": [],
                    "typed_np_restrictors": [],
                    "typed_time_modifiers": [],
                    "relative_objects": [],
                },
                "reading_explanation": (
                    "Diagnostic fixture reading bad_type is structurally complete "
                    "but intentionally carries a failing reading-local type check."
                ),
                "type_check": {
                    "ok": False,
                    "type": None,
                    "errors": ["synthetic reading-local type error"],
                },
            },
            {
                "name": "",
                "source": "diagnostic_fixture",
                "dependent_type_translation": "",
                "coq_definition": "",
            },
        ]
        semantic_readings_check = check_semantic_readings(semantic_readings, coq_code)
    elif case == "type_check_failure":
        coq_code = passing_coq_code
        semantic_readings = passing_semantic_readings
        semantic_readings_check = check_semantic_readings(semantic_readings, coq_code)
        dependent_type_translation = "bad_type_fixture : Prop"
        ast = {
            "kind": "diagnostic_fixture",
            "case": case,
            "node": {"kind": "application", "function": "bad_type_fixture"},
        }
        type_check = {
            "ok": False,
            "type": None,
            "errors": ["diagnostic fixture type_check failure"],
        }
        coq_check = {
            "ok": None,
            "status": "skipped",
            "message": "Skipped Coq/Rocq validation because internal type_check failed.",
        }
        conclusion = "Diagnostic fixture: dependent-type checking failed before Coq/Rocq validation."
    elif case == "construction_hygiene_failure":
        coq_code = "Parameter Event : Type.\nDefinition fixture_reading : Prop := True.\n"
        semantic_readings = passing_semantic_readings
        semantic_readings_check = check_semantic_readings(semantic_readings, coq_code)
        dependent_type_translation = "fixture_reading : Prop"
        construction_hygiene = {
            "ok": False,
            "checked": True,
            "forbidden_coq_fragments": ["Parameter Event : Type."],
            "found_forbidden_fragments": ["Parameter Event : Type."],
        }
        coq_check = {
            "ok": False,
            "status": "failed",
            "message": (
                "Generated Coq contains forbidden construction fragments: "
                "Parameter Event : Type."
            ),
        }
        conclusion = "Diagnostic fixture: construction hygiene failed before Coq/Rocq validation."
    elif case == "coq_check_failure":
        coq_code = (
            "Definition fixture_reading : Prop := True.\n"
            "Definition broken_coq_fixture : Prop := missing_constant.\n"
        )
        semantic_readings = passing_semantic_readings
        semantic_readings_check = check_semantic_readings(semantic_readings, coq_code)
        dependent_type_translation = "fixture_reading : Prop"
        construction_hygiene = {
            "ok": True,
            "checked": True,
            "forbidden_coq_fragments": ["Parameter Event : Type."],
            "found_forbidden_fragments": [],
        }
        coq_check = {
            "ok": False,
            "status": "failed",
            "message": "Diagnostic fixture Coq/Rocq validation failure.",
        }
        conclusion = "Diagnostic fixture: Coq/Rocq validation failed."

    result = {
        "ok": False,
        "input_sentence": f"diagnostic fixture: {case}",
        "event_semantics": {
            "kind": "diagnostic_fixture",
            "case": case,
            "semantic_readings": semantic_readings,
            "semantic_readings_check": semantic_readings_check,
        },
        "dependent_type_translation": dependent_type_translation,
        "semantic_readings": semantic_readings,
        "semantic_readings_check": semantic_readings_check,
        "ast": ast,
        "type_check": type_check,
        "construction_hygiene": construction_hygiene,
        "coq_code": coq_code,
        "coq_check": coq_check,
        "surface_type_contract_diagnostics": surface_type_contract_diagnostics_context(),
        "diagnostic_fixture": {"case": case, "available_cases": sorted(DIAGNOSTIC_FIXTURE_CASES)},
        "conclusion": conclusion,
    }
    return add_diagnostics(result)


def recovery_action_artifact_filename(case: str, action_index: int) -> str:
    return f"diagnostic_recovery_action__{stable_token(case)}__{action_index}.json"


def recovery_action_run_artifact_filename(case: str, action_index: int) -> str:
    return f"diagnostic_inspection_run__{stable_token(case)}__{action_index}.json"


def construction_rule_draft_artifact_filename(candidate_rule_id: str) -> str:
    token = stable_token(candidate_rule_id or "fallback_candidate")
    return f"construction_rule_draft__{token}.json"


def recovery_action_api_path(
    case: str,
    action_index: int,
    *,
    download: bool = False,
) -> str:
    params = {"case": case, "index": str(action_index)}
    if download:
        params["download"] = "1"
    return f"/api/recovery-action?{urlencode(params)}"


def recovery_action_run_api_path(
    case: str,
    action_index: int,
    *,
    download: bool = False,
) -> str:
    params = {"case": case, "index": str(action_index)}
    if download:
        params["download"] = "1"
    return f"/api/recovery-action-run?{urlencode(params)}"


def construction_rule_draft_api_path(
    sentence: str,
    require_coq: bool,
    *,
    download: bool = False,
) -> str:
    params = {"sentence": sentence}
    if require_coq:
        params["require_coq"] = "1"
    if download:
        params["download"] = "1"
    return f"/api/construction-rule-draft?{urlencode(params)}"


def request_wants_download(query: str) -> bool:
    params = parse_qs(query)
    value = params.get("download", ["0"])[0].strip().lower()
    return value in {"1", "true", "yes"}


def diagnostic_fixture_manifest() -> dict[str, Any]:
    cases = []
    for spec in sorted(DIAGNOSTIC_FIXTURE_SPECS, key=lambda item: item.case):
        case = spec.case
        result = diagnostic_fixture_result(case)
        diagnostics = result.get("diagnostics", {})
        recovery_actions = diagnostics.get("recovery_actions", [])
        observed_action_kinds = [
            action.get("kind")
            for action in recovery_actions
            if isinstance(action, dict) and action.get("kind")
        ]
        expected_stage = spec.failure_stage
        expected_action_kinds = list(spec.recovery_action_kinds)
        if diagnostics.get("failure_stage") != expected_stage:
            raise RuntimeError(
                f"Diagnostic fixture {case!r} stage drift: "
                f"{diagnostics.get('failure_stage')!r} != {expected_stage!r}"
            )
        if observed_action_kinds != expected_action_kinds:
            raise RuntimeError(
                f"Diagnostic fixture {case!r} action drift: "
                f"{observed_action_kinds!r} != {expected_action_kinds!r}"
            )
        recovery_action_exports = []
        for index, action in enumerate(recovery_actions):
            if not isinstance(action, dict):
                continue
            kind = str(action.get("kind", ""))
            repair_plan = recovery_action_repair_plan(
                case,
                index,
                expected_stage,
                action,
            )
            can_auto_run = bool(repair_plan.get("can_auto_run"))
            recovery_action_exports.append(
                {
                    "schema_version": RECOVERY_ACTION_SCHEMA,
                    "case": case,
                    "action_index": index,
                    "kind": kind,
                    "failure_stage": expected_stage,
                    "api_path": recovery_action_api_path(case, index),
                    "download_api_path": recovery_action_api_path(case, index, download=True),
                    "download_filename": recovery_action_artifact_filename(case, index),
                    "automation_mode": repair_plan.get("automation_mode"),
                    "can_auto_run": can_auto_run,
                    "can_auto_apply": bool(repair_plan.get("can_auto_apply")),
                    "target_fields": [
                        str(field)
                        for field in repair_plan.get("target_fields", [])
                        if isinstance(field, str)
                    ],
                    "inspection_run_api_path": (
                        recovery_action_run_api_path(case, index)
                        if can_auto_run
                        else None
                    ),
                    "inspection_run_download_api_path": (
                        recovery_action_run_api_path(case, index, download=True)
                        if can_auto_run
                        else None
                    ),
                    "inspection_run_download_filename": (
                        recovery_action_run_artifact_filename(case, index)
                        if can_auto_run
                        else None
                    ),
                }
            )
        cases.append(
            {
                "case": case,
                "label": spec.label,
                "api_path": f"/api/diagnostic-fixture?{urlencode({'case': case})}",
                "html_path": f"/diagnostic-fixture?{urlencode({'case': case})}",
                "failure_stage": expected_stage,
                "recovery_action_kinds": expected_action_kinds,
                "recovery_action_exports": recovery_action_exports,
            }
        )
    return {
        "schema_version": DIAGNOSTIC_FIXTURES_SCHEMA,
        "default_case": DEFAULT_DIAGNOSTIC_FIXTURE_CASE,
        "cases": cases,
    }


def diagnostic_contract_manifest() -> dict[str, Any]:
    return {
        "schema_version": DIAGNOSTIC_CONTRACT_SCHEMA,
        "failure_stages": sorted(DIAGNOSTIC_FAILURE_STAGES),
        "required_fixture_stages": sorted(REQUIRED_DIAGNOSTIC_FIXTURE_STAGES),
        "recovery_action_kinds": sorted(DIAGNOSTIC_RECOVERY_ACTION_KINDS),
        "repair_plan_automation_modes": sorted(DIAGNOSTIC_REPAIR_PLAN_AUTOMATION_MODES),
        "inspection_only_recovery_action_kinds": sorted(
            INSPECTION_ONLY_RECOVERY_ACTION_KINDS
        ),
        "semantic_reading_fields": sorted(SEMANTIC_READING_CONTRACT_FIELDS),
    }


def recovery_action_export_bundle(case: str, action_index: int) -> dict[str, Any]:
    result = diagnostic_fixture_result(case)
    diagnostics = result.get("diagnostics", {})
    actions = diagnostics.get("recovery_actions", [])
    action = actions[action_index]
    failure_stage = diagnostics.get("failure_stage")
    return {
        "schema_version": RECOVERY_ACTION_SCHEMA,
        "case": case,
        "action_index": action_index,
        "failure_stage": failure_stage,
        "action": action,
        "repair_plan": recovery_action_repair_plan(
            case,
            action_index,
            str(failure_stage),
            action,
        ),
        "contract": diagnostic_contract_manifest(),
        "surface_type_contract_diagnostics": result.get(
            "surface_type_contract_diagnostics",
            surface_type_contract_diagnostics_context(),
        ),
    }


def nested_field_value(payload: dict[str, Any], path: str) -> Any:
    current: Any = payload
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def recovery_action_inspection_run_bundle(case: str, action_index: int) -> dict[str, Any]:
    result = diagnostic_fixture_result(case)
    export_bundle = recovery_action_export_bundle(case, action_index)
    repair_plan = export_bundle["repair_plan"]
    target_fields = string_list(repair_plan.get("target_fields"))
    inspection_results = {
        field: nested_field_value(result, field)
        for field in target_fields
    }
    return {
        "schema_version": RECOVERY_INSPECTION_RUN_SCHEMA,
        "ok": True,
        "case": case,
        "action_index": action_index,
        "action_kind": export_bundle["action"].get("kind"),
        "failure_stage": export_bundle["failure_stage"],
        "automation_mode": repair_plan.get("automation_mode"),
        "can_auto_run": repair_plan.get("can_auto_run"),
        "can_auto_apply": repair_plan.get("can_auto_apply"),
        "target_fields": target_fields,
        "inspection_results": inspection_results,
        "repair_plan": repair_plan,
        "contract": diagnostic_contract_manifest(),
    }


def recovery_action_patch_preview(action: dict[str, Any]) -> str:
    kind = str(action.get("kind", ""))
    if kind == "add_missing_coq_definitions":
        definitions = string_list(action.get("target_definitions"))
        lines = ["(* candidate Coq/Rocq exports; review formulas before applying *)"]
        lines.extend(
            f"Definition {name} : PropT := (* TODO: checked semantic reading formula *)."
            for name in definitions
        )
        return "\n".join(lines)
    if kind == "rename_duplicate_readings":
        names = ", ".join(string_list(action.get("duplicate_reading_names")))
        return f"# rename duplicate semantic_readings entries: {names}"
    if kind == "fix_malformed_readings":
        indices = ", ".join(str(index) for index in int_list(action.get("reading_indices")))
        return f"# repair malformed semantic_readings record indices: {indices}"
    if kind == "fix_reading_type_checks":
        indices = ", ".join(str(index) for index in int_list(action.get("reading_indices")))
        return f"# repair reading-local type_check failures at indices: {indices}"
    if kind == "normalize_reading_exports":
        expected = action.get("expected_export_count")
        observed = action.get("observed_export_count")
        definitions = ", ".join(string_list(action.get("exported_definitions"))) or "none"
        return (
            "# normalize Prop/PropT exports\n"
            f"# expected_export_count={expected}; observed_export_count={observed}\n"
            f"# exported_definitions={definitions}"
        )
    if kind == "add_semantic_readings":
        return "# emit at least one semantic_readings record before Coq/Rocq export"
    return ""


def recovery_action_repair_plan(
    case: str,
    action_index: int,
    failure_stage: str,
    action: dict[str, Any],
) -> dict[str, Any]:
    kind = str(action.get("kind", ""))
    target_fields_by_kind = {
        "add_missing_coq_definitions": ["coq_code", "semantic_readings"],
        "add_semantic_readings": ["semantic_readings"],
        "edit_input": ["input_sentence"],
        "fix_malformed_readings": ["semantic_readings"],
        "fix_reading_type_checks": ["semantic_readings.type_check"],
        "inspect_ast": ["ast", "type_check"],
        "inspect_coq": ["coq_code", "coq_check"],
        "inspect_readings": ["semantic_readings", "semantic_readings_check", "coq_code"],
        "normalize_reading_exports": ["coq_code", "semantic_readings_check"],
        "rename_duplicate_readings": ["semantic_readings.name"],
        "revise_sentence": ["input_sentence"],
    }
    detail = str(action.get("detail") or "Inspect the failing diagnostic stage.")
    automation_mode = recovery_action_automation_mode(kind)
    if automation_mode == "inspection_only":
        action_step = (
            "Inspect the listed diagnostic field(s); this action is read-only and "
            "does not mutate semantic readings or Coq/Rocq output."
        )
    else:
        action_step = (
            "Apply the repair to the listed target field(s) without changing "
            "unrelated pipeline stages."
        )
    steps = [
        detail,
        action_step,
        "Re-run deterministic verification after the repair.",
    ]
    return {
        "schema_version": RECOVERY_REPAIR_PLAN_SCHEMA,
        "case": case,
        "action_index": action_index,
        "action_kind": kind,
        "failure_stage": failure_stage,
        "automation_mode": automation_mode,
        "can_auto_run": recovery_action_can_auto_run(kind),
        "can_auto_apply": False,
        "target_fields": target_fields_by_kind.get(kind, []),
        "steps": steps,
        "patch_text_preview": recovery_action_patch_preview(action),
        "verification_commands": [
            "python3 scripts/verify_project.py --require-coq --require-docx",
        ],
    }


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
    all_errors = list(resolution_errors or [])
    if not sentence.strip():
        all_errors.append("sentence is required for lexicon patch drafts.")
    drafts, validation_errors = resolve_lexicon_patch_drafts(
        result.get("lexicon_patch_drafts", []),
        resolutions or {},
    )
    all_errors.extend(validation_errors)
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


def diagnostic_fixture_case_for_result(result: dict[str, Any]) -> str | None:
    fixture = result.get("diagnostic_fixture")
    if not isinstance(fixture, dict):
        return None
    case = fixture.get("case")
    if isinstance(case, str) and case in DIAGNOSTIC_FIXTURE_CASES:
        return case
    return None


def next_steps_panel(result: dict[str, Any]) -> str:
    actions = result.get("diagnostics", {}).get("recovery_actions", [])
    if not actions:
        body = '<p class="next-step-empty">No recovery actions needed.</p>'
    else:
        items = []
        fixture_case = diagnostic_fixture_case_for_result(result)
        for index, action in enumerate(actions):
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
            action_link = ""
            run_link = ""
            inspection_preview = ""
            automation_mode = ""
            can_auto_run = False
            if fixture_case:
                href = recovery_action_api_path(fixture_case, index)
                download_href = recovery_action_api_path(
                    fixture_case,
                    index,
                    download=True,
                )
                download_filename = recovery_action_artifact_filename(fixture_case, index)
                export_bundle = recovery_action_export_bundle(fixture_case, index)
                repair_plan = export_bundle.get("repair_plan", {})
                if isinstance(repair_plan, dict):
                    automation_mode = str(repair_plan.get("automation_mode", ""))
                    can_auto_run = repair_plan.get("can_auto_run") is True
                action_link = (
                    '<a class="next-step-action-link" '
                    f'href="{html.escape(href, quote=True)}" '
                    'data-action-export="json">Open action JSON</a>'
                )
                action_link += (
                    '<a class="next-step-action-download-link" '
                    f'href="{html.escape(download_href, quote=True)}" '
                    f'download="{html.escape(download_filename, quote=True)}" '
                    'data-action-download="json">Download action JSON</a>'
                )
                if can_auto_run:
                    run_href = recovery_action_run_api_path(fixture_case, index)
                    run_download_href = recovery_action_run_api_path(
                        fixture_case,
                        index,
                        download=True,
                    )
                    run_download_filename = recovery_action_run_artifact_filename(
                        fixture_case,
                        index,
                    )
                    run_json = html.escape(
                        compact_json(
                            recovery_action_inspection_run_bundle(fixture_case, index)
                        )
                    )
                    run_link = (
                        '<a class="next-step-action-run-link" '
                        f'href="{html.escape(run_href, quote=True)}" '
                        'data-action-run="inspection">Run inspection</a>'
                    )
                    run_link += (
                        '<a class="next-step-inspection-download-link" '
                        f'href="{html.escape(run_download_href, quote=True)}" '
                        f'download="{html.escape(run_download_filename, quote=True)}" '
                        'data-inspection-download="json">Download inspection JSON</a>'
                    )
                    inspection_preview = (
                        '<details class="next-step-inspection-run-json" '
                        f'data-inspection-json-schema="{RECOVERY_INSPECTION_RUN_SCHEMA}">'
                        "<summary>Inspection Run JSON</summary>"
                        f"<pre>{run_json}</pre>"
                        "</details>"
                    )
            items.append(
                '<li '
                f'id="recovery-action-{index}" '
                f'class="next-step next-step--{html.escape(kind_class)}" '
                f'data-action-kind="{html.escape(kind)}" '
                f'data-action-index="{index}" '
                f'data-action-automation-mode="{html.escape(automation_mode, quote=True)}" '
                f'data-action-can-auto-run="{str(can_auto_run).lower()}" '
                'data-action-contract-api="/api/diagnostic-contract" '
                f'data-action-contract-kind="{html.escape(kind)}">'
                f'<strong>{html.escape(label)}</strong>'
                f'<code>{html.escape(kind)}</code>'
                f'<p>{html.escape(detail)}</p>'
                f"{details_html}"
                f"{action_link}"
                f"{run_link}"
                f"{inspection_preview}"
                "</li>"
            )
        body = '<ul class="next-step-list">' + "".join(items) + "</ul>"
    return (
        '<section class="panel next-steps-panel">'
        "<h2>Next Steps</h2>"
        f'<div class="next-steps">{body}</div>'
        "</section>"
    )


def recovery_action_exports_panel(result: dict[str, Any]) -> str:
    fixture_case = diagnostic_fixture_case_for_result(result)
    if not fixture_case:
        return ""
    diagnostics = result.get("diagnostics", {})
    actions = diagnostics.get("recovery_actions", [])
    if not isinstance(actions, list):
        actions = []
    failure_stage = str(diagnostics.get("failure_stage", ""))
    type_contract_diagnostics = result.get("surface_type_contract_diagnostics")
    if not isinstance(type_contract_diagnostics, dict):
        type_contract_diagnostics = surface_type_contract_diagnostics_context()
    type_contract_categories = surface_type_contract_diagnostic_category_text(
        type_contract_diagnostics
    )
    type_contract_schema = str(
        type_contract_diagnostics.get("schema_version", "")
    )
    type_contract_registry_id = str(
        type_contract_diagnostics.get("registry_id", "")
    )
    type_contract_category_count = str(
        type_contract_diagnostics.get("category_count", "")
    )
    items = []
    for index, action in enumerate(actions):
        if not isinstance(action, dict):
            continue
        kind = str(action.get("kind", ""))
        href = recovery_action_api_path(fixture_case, index)
        download_href = recovery_action_api_path(fixture_case, index, download=True)
        download_filename = recovery_action_artifact_filename(fixture_case, index)
        run_href = recovery_action_run_api_path(fixture_case, index)
        export_bundle = recovery_action_export_bundle(fixture_case, index)
        export_json = html.escape(compact_json(export_bundle))
        repair_plan = export_bundle.get("repair_plan", {})
        automation_mode = (
            str(repair_plan.get("automation_mode", ""))
            if isinstance(repair_plan, dict)
            else ""
        )
        can_auto_run = (
            repair_plan.get("can_auto_run") is True
            if isinstance(repair_plan, dict)
            else False
        )
        run_link = ""
        inspection_preview = ""
        if can_auto_run:
            run_download_href = recovery_action_run_api_path(
                fixture_case,
                index,
                download=True,
            )
            run_download_filename = recovery_action_run_artifact_filename(
                fixture_case,
                index,
            )
            run_json = html.escape(
                compact_json(
                    recovery_action_inspection_run_bundle(fixture_case, index)
                )
            )
            run_link = (
                '<a class="recovery-action-run-link" '
                f'href="{html.escape(run_href, quote=True)}" '
                'data-action-run="inspection">Run inspection</a>'
            )
            run_link += (
                '<a class="recovery-action-inspection-download-link" '
                f'href="{html.escape(run_download_href, quote=True)}" '
                f'download="{html.escape(run_download_filename, quote=True)}" '
                'data-inspection-download="json">Download inspection JSON</a>'
            )
            inspection_preview = (
                '<details class="recovery-action-inspection-run-json" '
                f'data-inspection-json-schema="{RECOVERY_INSPECTION_RUN_SCHEMA}">'
                "<summary>Inspection Run JSON</summary>"
                f"<pre>{run_json}</pre>"
                "</details>"
            )
        items.append(
            '<li class="recovery-action-export" '
            f'data-export-schema="{RECOVERY_ACTION_SCHEMA}" '
            f'data-export-case="{html.escape(fixture_case, quote=True)}" '
            f'data-export-action-index="{index}" '
            f'data-export-action-kind="{html.escape(kind, quote=True)}" '
            f'data-export-automation-mode="{html.escape(automation_mode, quote=True)}" '
            f'data-export-can-auto-run="{str(can_auto_run).lower()}" '
            f'data-export-failure-stage="{html.escape(failure_stage, quote=True)}">'
            f'<a href="{html.escape(href, quote=True)}">{html.escape(href)}</a>'
            '<a class="recovery-action-download-link" '
            f'href="{html.escape(download_href, quote=True)}" '
            f'download="{html.escape(download_filename, quote=True)}" '
            'data-action-download="json">Download action JSON</a>'
            f"{run_link}"
            "<dl>"
            f"<dt>schema</dt><dd><code>{RECOVERY_ACTION_SCHEMA}</code></dd>"
            f"<dt>case</dt><dd><code>{html.escape(fixture_case)}</code></dd>"
            f"<dt>index</dt><dd><code>{index}</code></dd>"
            f"<dt>kind</dt><dd><code>{html.escape(kind)}</code></dd>"
            f"<dt>automation</dt><dd><code>{html.escape(automation_mode)}</code></dd>"
            f"<dt>can auto-run</dt><dd><code>{str(can_auto_run).lower()}</code></dd>"
            f"<dt>stage</dt><dd><code>{html.escape(failure_stage)}</code></dd>"
            f"<dt>type contract</dt><dd><code>{html.escape(type_contract_schema)}</code></dd>"
            f"<dt>type contract categories</dt><dd><code>{html.escape(type_contract_categories)}</code></dd>"
            "</dl>"
            '<details class="recovery-action-export-json" '
            f'data-export-json-schema="{RECOVERY_ACTION_SCHEMA}">'
            "<summary>Action JSON</summary>"
            f"<pre>{export_json}</pre>"
            "</details>"
            f"{inspection_preview}"
            "</li>"
        )
    body = (
        '<ul class="recovery-action-export-list">' + "".join(items) + "</ul>"
        if items
        else '<p class="recovery-action-export-empty">No recovery action exports.</p>'
    )
    return (
        '<section class="panel recovery-action-exports-panel" '
        f'data-export-schema="{RECOVERY_ACTION_SCHEMA}" '
        f'data-export-case="{html.escape(fixture_case, quote=True)}" '
        f'data-export-count="{len(items)}" '
        f'data-surface-type-contract-diagnostic-schema="{html.escape(type_contract_schema, quote=True)}" '
        f'data-surface-type-contract-diagnostic-count="{html.escape(type_contract_category_count, quote=True)}" '
        f'data-surface-type-contract-diagnostic-categories="{html.escape(type_contract_categories, quote=True)}" '
        f'data-surface-type-contract-registry-id="{html.escape(type_contract_registry_id, quote=True)}">'
        "<h2>Recovery Action Exports</h2>"
        f'<div class="recovery-action-exports">{body}</div>'
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


def semantic_reading_typed_modifier_text(value: Any) -> str:
    if not isinstance(value, list):
        return "none"
    items = []
    for entry in value:
        if not isinstance(entry, dict):
            continue
        name = str(entry.get("name", ""))
        modifier_type = str(entry.get("type", "Adv"))
        site = str(entry.get("site", ""))
        if not name:
            continue
        prefix = f"{site}: " if site else ""
        items.append(f"{prefix}{name} : {modifier_type}")
    return "; ".join(items) or "none"


def semantic_reading_typed_time_modifier_text(value: Any) -> str:
    if not isinstance(value, list):
        return "none"
    items = []
    for entry in value:
        if not isinstance(entry, dict):
            continue
        operator = str(entry.get("operator", ""))
        argument = str(entry.get("argument", ""))
        modifier_type = str(entry.get("type", "Time"))
        site = str(entry.get("site", ""))
        if not operator or not argument:
            continue
        prefix = f"{site}: " if site else ""
        items.append(f"{prefix}{operator}_T({argument}) : {modifier_type}")
    return "; ".join(items) or "none"


def semantic_reading_typed_np_restrictor_text(value: Any) -> str:
    if not isinstance(value, list):
        return "none"
    items = []
    for entry in value:
        if not isinstance(entry, dict):
            continue
        predicate = str(entry.get("predicate", ""))
        predicate_type = str(entry.get("predicate_type", "Entity -> Prop"))
        site = str(entry.get("site", ""))
        if not predicate:
            continue
        prefix = f"{site}: " if site else ""
        items.append(f"{prefix}{predicate} : {predicate_type}")
    return "; ".join(items) or "none"


def semantic_reading_relative_object_text(value: Any) -> str:
    if not isinstance(value, list):
        return "none"
    items = []
    for entry in value:
        if not isinstance(entry, dict):
            continue
        name = str(entry.get("name", ""))
        object_type = str(entry.get("type", "Entity"))
        site = str(entry.get("site", ""))
        if not name:
            continue
        prefix = f"{site}: " if site else ""
        items.append(f"{prefix}{name} : {object_type}")
    return "; ".join(items) or "none"


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
            attachment_summary = reading.get("attachment_summary") or {}
            if not isinstance(attachment_summary, dict):
                attachment_summary = {}
            attachment_kind = str(attachment_summary.get("kind", "none"))
            reading_explanation = str(
                reading.get("reading_explanation") or "No reading explanation emitted."
            )
            typed_modifiers = semantic_reading_typed_modifier_text(
                attachment_summary.get("typed_modifiers"),
            )
            typed_np_restrictors = semantic_reading_typed_np_restrictor_text(
                attachment_summary.get("typed_np_restrictors"),
            )
            typed_time_modifiers = semantic_reading_typed_time_modifier_text(
                attachment_summary.get("typed_time_modifiers"),
            )
            relative_objects = semantic_reading_relative_object_text(
                attachment_summary.get("relative_objects"),
            )
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
                f'data-coq-exported="{html.escape(exported_status, quote=True)}" '
                f'data-reading-attachment-kind="{html.escape(attachment_kind, quote=True)}">'
                f'<strong>{html.escape(name)}</strong>'
                '<dl>'
                f'<dt>scope</dt><dd>{html.escape(scope or "none")}</dd>'
                f'<dt>source</dt><dd>{html.escape(source or "none")}</dd>'
                f'<dt>interpretation</dt><dd>{html.escape(reading_explanation)}</dd>'
                f'<dt>attachment</dt><dd>{html.escape(attachment_kind)}</dd>'
                f'<dt>typed Adv modifiers</dt><dd>{html.escape(typed_modifiers)}</dd>'
                f'<dt>typed NP restrictors</dt><dd>{html.escape(typed_np_restrictors)}</dd>'
                f'<dt>typed time modifiers</dt><dd>{html.escape(typed_time_modifiers)}</dd>'
                f'<dt>relative objects</dt><dd>{html.escape(relative_objects)}</dd>'
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


def verification_scope_panel(result: dict[str, Any]) -> str:
    scope = result.get("verification_scope")
    if not isinstance(scope, dict):
        body = '<p class="verification-scope-empty">No verification scope emitted.</p>'
        return (
            '<section class="panel verification-scope" '
            'data-verification-scope-kind="missing" '
            'data-verification-level="missing">'
            "<h2>Verification Scope</h2>"
            f'<div class="verification-scope-body">{body}</div>'
            "</section>"
        )
    kind = str(scope.get("kind", ""))
    level = str(scope.get("certification_level", ""))
    rows = [
        ("kind", kind),
        ("level", level),
        ("label", str(scope.get("label", ""))),
        ("rule", str(scope.get("rule_id") or "none")),
        ("phenomenon", str(scope.get("phenomenon", ""))),
        ("summary", str(scope.get("summary", ""))),
    ]
    guarantees = scope.get("guarantees", [])
    limitations = scope.get("limitations", [])
    certification_gaps = scope.get("certification_gaps", [])
    guarantee_items = (
        "".join(f"<li>{html.escape(str(item))}</li>" for item in guarantees)
        if isinstance(guarantees, list) and guarantees
        else "<li>none</li>"
    )
    limitation_items = (
        "".join(f"<li>{html.escape(str(item))}</li>" for item in limitations)
        if isinstance(limitations, list) and limitations
        else "<li>none</li>"
    )
    if isinstance(certification_gaps, (list, tuple)) and certification_gaps:
        gap_items = "".join(
            (
                '<li '
                f'data-certification-gap-id="{html.escape(str(gap.get("id", "")), quote=True)}" '
                f'data-certification-gap-artifact="{html.escape(str(gap.get("required_artifact", "")), quote=True)}">'
                f'<strong>{html.escape(str(gap.get("label", "")))}</strong>'
                '<dl>'
                f'<dt>detail</dt><dd>{html.escape(str(gap.get("detail", "")))}</dd>'
                f'<dt>artifact</dt><dd>{html.escape(str(gap.get("required_artifact", "")))}</dd>'
                '</dl>'
                '</li>'
            )
            for gap in certification_gaps
            if isinstance(gap, dict)
        )
    else:
        gap_items = "<li>none</li>"
    body = (
        '<dl class="verification-scope-details">'
        + "".join(
            f"<dt>{html.escape(label)}</dt><dd>{html.escape(value)}</dd>"
            for label, value in rows
        )
        + "</dl>"
        '<div class="verification-scope-list"><strong>guarantees</strong>'
        f"<ul>{guarantee_items}</ul></div>"
        '<div class="verification-scope-list"><strong>limitations</strong>'
        f"<ul>{limitation_items}</ul></div>"
        '<div class="verification-scope-list verification-scope-gaps">'
        "<strong>certification gaps</strong>"
        f"<ul>{gap_items}</ul></div>"
    )
    return (
        '<section class="panel verification-scope" '
        f'data-verification-scope-kind="{html.escape(kind, quote=True)}" '
        f'data-verification-level="{html.escape(level, quote=True)}">'
        "<h2>Verification Scope</h2>"
        f'<div class="verification-scope-body">{body}</div>'
        "</section>"
    )


def certification_upgrade_plan_panel(result: dict[str, Any]) -> str:
    plan = result.get("certification_upgrade_plan")
    if not isinstance(plan, dict):
        return ""
    schema = str(plan.get("schema_version", ""))
    source_scope = str(plan.get("source_verification_scope", ""))
    target_level = str(plan.get("target_certification_level", ""))
    candidate_rule_id = str(plan.get("candidate_rule_id", ""))
    automation_mode = str(plan.get("automation_mode", ""))
    can_auto_apply = plan.get("can_auto_apply") is True
    rows = [
        ("schema", schema),
        ("source", source_scope),
        ("target", target_level),
        ("candidate rule", candidate_rule_id),
        ("automation", automation_mode),
        ("auto apply", "yes" if can_auto_apply else "no"),
    ]
    step_items = []
    for step in plan.get("steps", []):
        if not isinstance(step, dict):
            continue
        step_items.append(
            '<li '
            f'data-upgrade-gap-id="{html.escape(str(step.get("gap_id", "")), quote=True)}" '
            f'data-upgrade-action-kind="{html.escape(str(step.get("action_kind", "")), quote=True)}" '
            f'data-upgrade-target-artifact="{html.escape(str(step.get("target_artifact", "")), quote=True)}">'
            f'<strong>{html.escape(str(step.get("label", "")))}</strong>'
            '<dl>'
            f'<dt>action</dt><dd>{html.escape(str(step.get("action_kind", "")))}</dd>'
            f'<dt>artifact</dt><dd>{html.escape(str(step.get("target_artifact", "")))}</dd>'
            f'<dt>required</dt><dd>{html.escape(str(step.get("required_artifact", "")))}</dd>'
            f'<dt>verification</dt><dd>{html.escape(str(step.get("verification", "")))}</dd>'
            '</dl>'
            '</li>'
        )
    steps_html = (
        '<ul class="certification-upgrade-steps">' + "".join(step_items) + "</ul>"
        if step_items
        else '<p class="certification-upgrade-empty">No upgrade steps emitted.</p>'
    )
    commands = plan.get("verification_commands", [])
    commands_html = (
        "".join(f"<li><code>{html.escape(str(command))}</code></li>" for command in commands)
        if isinstance(commands, list) and commands
        else "<li>none</li>"
    )
    raw_json = html.escape(compact_json(plan))
    body = (
        '<dl class="certification-upgrade-details">'
        + "".join(
            f"<dt>{html.escape(label)}</dt><dd>{html.escape(value)}</dd>"
            for label, value in rows
        )
        + "</dl>"
        f"{steps_html}"
        '<div class="certification-upgrade-commands"><strong>verification commands</strong>'
        f"<ul>{commands_html}</ul></div>"
        '<details class="certification-upgrade-raw"><summary>Raw upgrade JSON</summary>'
        f"<pre>{raw_json}</pre>"
        "</details>"
    )
    return (
        '<section class="panel certification-upgrade-plan-panel" '
        f'data-upgrade-plan-schema="{html.escape(schema, quote=True)}" '
        f'data-upgrade-source-scope="{html.escape(source_scope, quote=True)}" '
        f'data-upgrade-target-level="{html.escape(target_level, quote=True)}" '
        f'data-upgrade-candidate-rule-id="{html.escape(candidate_rule_id, quote=True)}" '
        f'data-upgrade-can-auto-apply="{str(can_auto_apply).lower()}">'
        "<h2>Certification Upgrade Plan</h2>"
        f'<div class="certification-upgrade-plan">{body}</div>'
        "</section>"
    )


def construction_rule_draft_panel(
    result: dict[str, Any],
    sentence: str,
    require_coq: bool,
) -> str:
    draft = result.get("construction_rule_draft")
    if not isinstance(draft, dict):
        return ""
    schema = str(draft.get("schema_version", ""))
    source_scope = str(draft.get("source_verification_scope", ""))
    candidate_rule_id = str(draft.get("candidate_rule_id", ""))
    analyzer = str(draft.get("candidate_analyzer", ""))
    automation_mode = str(draft.get("automation_mode", ""))
    can_auto_apply = draft.get("can_auto_apply") is True
    readings = draft.get("semantic_reading_drafts", [])
    hygiene = draft.get("hygiene_policy_draft", {})
    forbidden_fragments = []
    if isinstance(hygiene, dict):
        forbidden_fragments = [
            str(fragment)
            for fragment in hygiene.get("forbidden_coq_fragments", [])
        ]
    reading_items = []
    reading_source = readings if isinstance(readings, list) else []
    for reading in reading_source:
        if not isinstance(reading, dict):
            continue
        reading_items.append(
            '<li '
            f'data-rule-draft-reading="{html.escape(str(reading.get("name", "")), quote=True)}" '
            f'data-rule-draft-reading-source="{html.escape(str(reading.get("source", "")), quote=True)}">'
            f'<strong>{html.escape(str(reading.get("name", "")))}</strong>'
            '<dl>'
            f'<dt>source</dt><dd>{html.escape(str(reading.get("source", "")))}</dd>'
            f'<dt>scope</dt><dd>{html.escape(str(reading.get("scope", "")))}</dd>'
            f'<dt>coq</dt><dd>{html.escape(str(reading.get("coq_definition", "")))}</dd>'
            f'<dt>translation</dt><dd><code>{html.escape(str(reading.get("dependent_type_translation", "")))}</code></dd>'
            '</dl>'
            '</li>'
        )
    reading_html = (
        '<ul class="construction-rule-draft-readings">' + "".join(reading_items) + "</ul>"
        if reading_items
        else '<p class="construction-rule-draft-empty">No reading drafts emitted.</p>'
    )
    forbidden_html = (
        "".join(
            f'<li data-rule-draft-forbidden-fragment="{html.escape(fragment, quote=True)}">'
            f"<code>{html.escape(fragment)}</code></li>"
            for fragment in forbidden_fragments
        )
        if forbidden_fragments
        else "<li>none</li>"
    )
    commands = draft.get("verification_commands", [])
    commands_html = (
        "".join(f"<li><code>{html.escape(str(command))}</code></li>" for command in commands)
        if isinstance(commands, list) and commands
        else "<li>none</li>"
    )
    download_href = construction_rule_draft_api_path(sentence, require_coq, download=True)
    raw_json = html.escape(compact_json(draft))
    rows = [
        ("schema", schema),
        ("source", source_scope),
        ("candidate rule", candidate_rule_id),
        ("candidate analyzer", analyzer),
        ("automation", automation_mode),
        ("auto apply", "yes" if can_auto_apply else "no"),
    ]
    body = (
        '<dl class="construction-rule-draft-details">'
        + "".join(
            f"<dt>{html.escape(label)}</dt><dd>{html.escape(value)}</dd>"
            for label, value in rows
        )
        + "</dl>"
        '<div class="panel-action">'
        f'<a class="construction-rule-draft-link" href="{html.escape(download_href, quote=True)}" '
        'data-rule-draft-format="json" download="construction_rule_draft.json">'
        "Download draft JSON"
        "</a>"
        "</div>"
        '<div class="construction-rule-draft-section"><strong>reading drafts</strong>'
        f"{reading_html}</div>"
        '<div class="construction-rule-draft-section"><strong>forbidden Coq/Rocq fragments</strong>'
        f"<ul>{forbidden_html}</ul></div>"
        '<div class="construction-rule-draft-section"><strong>verification commands</strong>'
        f"<ul>{commands_html}</ul></div>"
        '<details class="construction-rule-draft-raw"><summary>Raw draft JSON</summary>'
        f"<pre>{raw_json}</pre>"
        "</details>"
    )
    return (
        '<section class="panel construction-rule-draft-panel" '
        f'data-rule-draft-schema="{html.escape(schema, quote=True)}" '
        f'data-rule-draft-source-scope="{html.escape(source_scope, quote=True)}" '
        f'data-rule-draft-id="{html.escape(candidate_rule_id, quote=True)}" '
        f'data-rule-draft-analyzer="{html.escape(analyzer, quote=True)}" '
        f'data-rule-draft-can-auto-apply="{str(can_auto_apply).lower()}">'
        "<h2>Construction Rule Draft</h2>"
        f'<div class="construction-rule-draft">{body}</div>'
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


def diagnostic_fixture_form(result: dict[str, Any]) -> str:
    manifest = diagnostic_fixture_manifest()
    manifest_cases = [
        fixture
        for fixture in manifest.get("cases", [])
        if isinstance(fixture, dict) and isinstance(fixture.get("case"), str)
    ]
    available_cases = {str(fixture["case"]) for fixture in manifest_cases}
    fixture = result.get("diagnostic_fixture", {})
    current_case = fixture.get("case") if isinstance(fixture, dict) else None
    default_case = str(manifest.get("default_case", DEFAULT_DIAGNOSTIC_FIXTURE_CASE))
    selected_case = (
        current_case
        if isinstance(current_case, str)
        and current_case in available_cases
        else default_case
    )
    if selected_case not in available_cases:
        selected_case = DEFAULT_DIAGNOSTIC_FIXTURE_CASE
    options = []
    for fixture_case in manifest_cases:
        case = str(fixture_case["case"])
        selected = " selected" if case == selected_case else ""
        recovery_actions = fixture_case.get("recovery_action_kinds", [])
        recovery_action_text = ", ".join(
            str(action) for action in recovery_actions if isinstance(action, str)
        )
        recovery_action_exports = fixture_case.get("recovery_action_exports", [])
        inspection_run_count = sum(
            1
            for export in recovery_action_exports
            if isinstance(export, dict) and export.get("can_auto_run") is True
        )
        options.append(
            f'<option value="{html.escape(case, quote=True)}"{selected} '
            f'data-failure-stage="{html.escape(str(fixture_case.get("failure_stage", "")), quote=True)}" '
            f'data-recovery-action-kinds="{html.escape(recovery_action_text, quote=True)}" '
            f'data-inspection-run-count="{inspection_run_count}">'
            f"{html.escape(str(fixture_case.get('label', case)))}</option>"
        )
    return (
        '<form class="diagnostic-fixture-form" method="get" action="/diagnostic-fixture" '
        f'data-current-fixture="{html.escape(selected_case, quote=True)}" '
        f'data-fixtures-schema="{html.escape(str(manifest.get("schema_version", "")), quote=True)}" '
        f'data-fixtures-api="/api/diagnostic-fixtures" '
        f'data-diagnostic-contract-api="/api/diagnostic-contract" '
        f'data-fixture-count="{len(manifest_cases)}">'
        '<label for="diagnostic-fixture-case">Diagnostics</label>'
        '<select id="diagnostic-fixture-case" name="case">'
        f"{''.join(options)}"
        "</select>"
        '<button type="submit">Open</button>'
        "</form>"
    )


def diagnostic_contract_panel() -> str:
    contract = diagnostic_contract_manifest()
    schema = str(contract.get("schema_version", ""))
    sections = [
        ("Failure Stages", "failure_stages"),
        ("Required Fixture Stages", "required_fixture_stages"),
        ("Recovery Actions", "recovery_action_kinds"),
        ("Repair Plan Automation Modes", "repair_plan_automation_modes"),
        ("Inspection-Only Actions", "inspection_only_recovery_action_kinds"),
        ("Semantic Reading Fields", "semantic_reading_fields"),
    ]
    vocabularies = []
    for label, field in sections:
        values = [
            str(value)
            for value in contract.get(field, [])
            if isinstance(value, str)
        ]
        items = "".join(
            '<li '
            f'data-contract-field="{html.escape(field, quote=True)}" '
            f'data-contract-token="{html.escape(value, quote=True)}">'
            f"<code>{html.escape(value)}</code>"
            "</li>"
            for value in values
        )
        vocabularies.append(
            '<div class="diagnostic-contract-vocabulary" '
            f'data-contract-field="{html.escape(field, quote=True)}" '
            f'data-contract-count="{len(values)}">'
            f"<strong>{html.escape(label)}</strong>"
            f"<ul>{items}</ul>"
            "</div>"
        )
    return (
        '<section class="panel diagnostic-contract-panel" '
        f'data-contract-schema="{html.escape(schema, quote=True)}" '
        'data-contract-api="/api/diagnostic-contract">'
        "<h2>Diagnostic Contract</h2>"
        '<div class="diagnostic-contract">'
        "<dl>"
        f"<dt>schema</dt><dd><code>{html.escape(schema)}</code></dd>"
        "<dt>api</dt><dd><code>/api/diagnostic-contract</code></dd>"
        "</dl>"
        f"{''.join(vocabularies)}"
        "</div>"
        "</section>"
    )


def certified_fragment_panel() -> str:
    manifest = construction_fragment_manifest()
    schema = str(manifest.get("schema_version", ""))
    registered = [
        item
        for item in manifest.get("registered_constructions", [])
        if isinstance(item, dict)
    ]
    fallback = manifest.get("fallback", {})
    fallback_level = (
        str(fallback.get("certification_level", ""))
        if isinstance(fallback, dict)
        else ""
    )
    coverage = manifest.get("coverage_matrix", {})
    counts = manifest.get("coverage_matrix_counts", {})
    semantic_snapshots = [
        item
        for item in manifest.get("semantic_snapshots", [])
        if isinstance(item, dict)
    ]
    semantic_snapshot_count = str(manifest.get("semantic_snapshot_count", ""))
    registered_case_count = str(
        counts.get("registered_success_cases", "")
        if isinstance(counts, dict)
        else ""
    )
    registered_variant_case_count = str(
        counts.get("registered_variant_success_cases", "")
        if isinstance(counts, dict)
        else ""
    )
    fallback_case_count = str(
        counts.get("fallback_success_cases", "")
        if isinstance(counts, dict)
        else ""
    )
    rejected_case_count = str(
        counts.get("rejected_unsupported_cases", "")
        if isinstance(counts, dict)
        else ""
    )
    surface_parser_coverage = manifest.get("surface_parser_coverage", {})
    modified_surface = (
        surface_parser_coverage.get("modified_transitive_adv_sequence", {})
        if isinstance(surface_parser_coverage, dict)
        else {}
    )
    if not isinstance(modified_surface, dict):
        modified_surface = {}

    def count_list_attribute(value: object) -> str:
        if not isinstance(value, list):
            return ""
        return ",".join(str(item) for item in value if isinstance(item, int))

    surface_verified_counts = count_list_attribute(
        modified_surface.get("verified_modifier_counts"),
    )
    surface_timed_counts = count_list_attribute(
        modified_surface.get("verified_timed_modifier_counts"),
    )
    surface_untimed_counts = count_list_attribute(
        modified_surface.get("verified_untimed_modifier_counts"),
    )
    surface_verified_example_count = str(
        modified_surface.get("verified_example_count", ""),
    )
    surface_generation_spec = modified_surface.get("witness_generation_spec")
    if not isinstance(surface_generation_spec, dict):
        surface_generation_spec = {}
    surface_generator_schema = str(surface_generation_spec.get("schema_version", ""))
    surface_generator_kind = str(surface_generation_spec.get("generator", ""))
    surface_generator_time_suffix = str(surface_generation_spec.get("time_suffix", ""))
    surface_generator_modifier_count = str(
        len(surface_generation_spec.get("modifiers", []))
        if isinstance(surface_generation_spec.get("modifiers"), list)
        else "",
    )
    surface_slot_probes = modified_surface.get("slot_probe_examples")
    if not isinstance(surface_slot_probes, dict):
        surface_slot_probes = {}
    surface_slot_probe_schema = str(surface_slot_probes.get("schema_version", ""))
    surface_slot_probe_count = str(surface_slot_probes.get("probe_count", ""))
    surface_slot_probe_generation_spec = surface_slot_probes.get(
        "probe_generation_spec",
    )
    if not isinstance(surface_slot_probe_generation_spec, dict):
        surface_slot_probe_generation_spec = {}
    surface_slot_probe_generator_schema = str(
        surface_slot_probe_generation_spec.get("schema_version", ""),
    )
    surface_slot_probe_generator_kind = str(
        surface_slot_probe_generation_spec.get("generator", ""),
    )
    surface_slot_probe_matrix_count = str(
        surface_slot_probes.get("matrix_example_count", ""),
    )
    surface_slot_probe_matrix_generation_spec = surface_slot_probes.get(
        "matrix_generation_spec",
    )
    if not isinstance(surface_slot_probe_matrix_generation_spec, dict):
        surface_slot_probe_matrix_generation_spec = {}
    surface_slot_probe_matrix_generator_schema = str(
        surface_slot_probe_matrix_generation_spec.get("schema_version", ""),
    )
    surface_slot_probe_matrix_generator_kind = str(
        surface_slot_probe_matrix_generation_spec.get("generator", ""),
    )
    surface_slot_probe_matrix_type_contract_registry = (
        surface_slot_probe_matrix_generation_spec.get("type_contract_registry")
    )
    if not isinstance(surface_slot_probe_matrix_type_contract_registry, dict):
        surface_slot_probe_matrix_type_contract_registry = {}
    surface_slot_probe_matrix_type_contract_schema = str(
        surface_slot_probe_matrix_type_contract_registry.get("schema_version", ""),
    )
    surface_slot_probe_matrix_type_contract_entry_schema = str(
        surface_slot_probe_matrix_type_contract_registry.get("entry_schema", ""),
    )
    surface_slot_probe_matrix_type_contract_entry_count = str(
        surface_slot_probe_matrix_type_contract_registry.get("entry_count", ""),
    )
    surface_slot_probe_matrix_type_contract_diagnostic_schema = str(
        surface_slot_probe_matrix_type_contract_registry.get("diagnostic_schema", ""),
    )
    diagnostic_categories = (
        surface_slot_probe_matrix_type_contract_registry.get("diagnostic_categories")
    )
    if not isinstance(diagnostic_categories, list):
        diagnostic_categories = []
    diagnostic_category_items = [
        item
        for item in diagnostic_categories
        if isinstance(item, dict)
    ]
    surface_slot_probe_matrix_type_contract_diagnostic_count = str(
        len(diagnostic_category_items),
    )
    surface_slot_probe_matrix_type_contract_diagnostic_categories = ",".join(
        str(item.get("category", ""))
        for item in diagnostic_category_items
        if item.get("category")
    )
    surface_slot_probe_matrix_type_contract_source = str(
        surface_slot_probe_matrix_type_contract_registry.get("source", ""),
    )
    surface_slot_probe_matrix_type_contract_registry_id = str(
        surface_slot_probe_matrix_type_contract_registry.get("registry_id", ""),
    )

    def surface_parser_example_items(item: dict[str, object]) -> str:
        examples = item.get("verified_examples")
        if not isinstance(examples, list):
            return ""
        return "".join(
            (
                '<li '
                f'data-surface-example-variant-id="{html.escape(str(example.get("variant_id", "")), quote=True)}" '
                f'data-surface-example-sentence="{html.escape(str(example.get("sentence", "")), quote=True)}" '
                f'data-surface-example-modifier-count="{html.escape(str(example.get("modifier_count", "")), quote=True)}" '
                f'data-surface-example-time-wrapped="{str(example.get("time_wrapped") is True).lower()}" '
                f'data-surface-example-source="{html.escape(str(example.get("source", "")), quote=True)}" '
                f'data-surface-example-analysis="{html.escape(str(example.get("expected_event_analysis", "")), quote=True)}" '
                f'data-surface-example-ast-kind="{html.escape(str(example.get("expected_ast_kind", "")), quote=True)}" '
                f'data-surface-example-fragment-count="{len(example.get("expected_dependent_type_fragments", [])) if isinstance(example.get("expected_dependent_type_fragments"), list) else 0}">'
                f"{html.escape(str(example.get('sentence', '')))}"
                "</li>"
            )
            for example in examples
            if isinstance(example, dict)
        )

    def surface_slot_probe_items(item: dict[str, object]) -> str:
        slot_probes = item.get("slot_probe_examples")
        if not isinstance(slot_probes, dict):
            return ""
        probes = slot_probes.get("probes")
        if not isinstance(probes, list):
            return ""
        return "".join(
            (
                '<li '
                f'data-surface-slot-probe-id="{html.escape(str(probe.get("probe_id", "")), quote=True)}" '
                f'data-surface-slot-probe-slot="{html.escape(str(probe.get("slot", "")), quote=True)}" '
                f'data-surface-slot-probe-sentence="{html.escape(str(probe.get("sentence", "")), quote=True)}" '
                f'data-surface-slot-probe-modifier-count="{html.escape(str(probe.get("modifier_count", "")), quote=True)}" '
                f'data-surface-slot-probe-time-wrapped="{str(probe.get("time_wrapped") is True).lower()}">'
                f"{html.escape(str(probe.get('sentence', '')))}"
                "</li>"
            )
            for probe in probes
            if isinstance(probe, dict)
        )

    def surface_slot_probe_matrix_items(item: dict[str, object]) -> str:
        slot_probes = item.get("slot_probe_examples")
        if not isinstance(slot_probes, dict):
            return ""
        examples = slot_probes.get("matrix_examples")
        if not isinstance(examples, list):
            return ""
        return "".join(
            (
                '<li '
                f'data-surface-slot-matrix-id="{html.escape(str(example.get("matrix_id", "")), quote=True)}" '
                f'data-surface-slot-matrix-profile="{html.escape(str(example.get("profile_id", "")), quote=True)}" '
                f'data-surface-slot-matrix-agent="{html.escape(str((example.get("agent") or {}).get("semantic", "")) if isinstance(example.get("agent"), dict) else "", quote=True)}" '
                f'data-surface-slot-matrix-agent-type="{html.escape(str((example.get("type_contract") or {}).get("agent_dependent_type", "")) if isinstance(example.get("type_contract"), dict) else "", quote=True)}" '
                f'data-surface-slot-matrix-predicate="{html.escape(str((example.get("predicate") or {}).get("semantic", "")) if isinstance(example.get("predicate"), dict) else "", quote=True)}" '
                f'data-surface-slot-matrix-predicate-type="{html.escape(str((example.get("type_contract") or {}).get("predicate_dependent_type", "")) if isinstance(example.get("type_contract"), dict) else "", quote=True)}" '
                f'data-surface-slot-matrix-theme="{html.escape(str((example.get("theme") or {}).get("semantic", "")) if isinstance(example.get("theme"), dict) else "", quote=True)}" '
                f'data-surface-slot-matrix-theme-type="{html.escape(str((example.get("type_contract") or {}).get("theme_dependent_type", "")) if isinstance(example.get("type_contract"), dict) else "", quote=True)}" '
                f'data-surface-slot-matrix-modifier-type="{html.escape(str((example.get("type_contract") or {}).get("modifier_dependent_type", "")) if isinstance(example.get("type_contract"), dict) else "", quote=True)}" '
                f'data-surface-slot-matrix-time-type="{html.escape(str((example.get("type_contract") or {}).get("time_argument_type", "")) if isinstance(example.get("type_contract"), dict) else "", quote=True)}" '
                f'data-surface-slot-matrix-modifier-count="{html.escape(str(example.get("modifier_count", "")), quote=True)}" '
                f'data-surface-slot-matrix-time-wrapped="{str(example.get("time_wrapped") is True).lower()}">'
                f"{html.escape(str(example.get('sentence', '')))}"
                "</li>"
            )
            for example in examples
            if isinstance(example, dict)
        )
    rule_items = "".join(
        '<li '
        f'data-certified-rule-id="{html.escape(str(item.get("id", "")), quote=True)}" '
        f'data-certified-level="{html.escape(str(item.get("certification_level", "")), quote=True)}" '
        f'data-certified-example="{html.escape(str(item.get("example", "")), quote=True)}" '
        f'data-boundary-status="{html.escape(str(item.get("boundary_status", "")), quote=True)}">'
        f'<code>{html.escape(str(item.get("id", "")))}</code>'
        f'<span>{html.escape(str(item.get("label", "")))}</span>'
        "</li>"
        for item in registered
    )
    marker_items = "".join(
        f"<li><code>{html.escape(str(marker))}</code></li>"
        for marker in manifest.get("rejected_fragment_markers", [])
        if isinstance(marker, str)
    )
    fallback_items = ""
    registered_variant_items = ""
    fallback_gap_items = ""
    rejected_items = ""
    if isinstance(coverage, dict):
        registered_variant_items = "".join(
            '<li '
            f'data-coverage-kind="registered_variant_success" '
            f'data-coverage-rule-id="{html.escape(str(item.get("rule_id", "")), quote=True)}" '
            f'data-coverage-variant-id="{html.escape(str(item.get("variant_id", "")), quote=True)}" '
            f'data-coverage-sentence="{html.escape(str(item.get("sentence", "")), quote=True)}" '
            f'data-coverage-level="{html.escape(str(item.get("expected_certification_level", "")), quote=True)}">'
            f"{html.escape(str(item.get('sentence', '')))}"
            "</li>"
            for item in coverage.get("registered_variant_success_cases", [])
            if isinstance(item, dict)
        )
        fallback_items = "".join(
            '<li '
            f'data-coverage-kind="fallback_success" '
            f'data-coverage-sentence="{html.escape(str(item.get("sentence", "")), quote=True)}" '
            f'data-coverage-level="{html.escape(str(item.get("expected_certification_level", "")), quote=True)}">'
            f"{html.escape(str(item.get('sentence', '')))}"
            "</li>"
            for item in coverage.get("fallback_success_cases", [])
            if isinstance(item, dict)
        )
        rejected_items = "".join(
            '<li '
            f'data-coverage-kind="rejected_unsupported" '
            f'data-coverage-marker="{html.escape(str(item.get("marker", "")), quote=True)}" '
            f'data-coverage-sentence="{html.escape(str(item.get("sentence", "")), quote=True)}">'
            f"{html.escape(str(item.get('sentence', '')))}"
            "</li>"
            for item in coverage.get("rejected_unsupported_cases", [])
            if isinstance(item, dict)
        )
    if isinstance(fallback, dict):
        fallback_gap_items = "".join(
            (
                '<li '
                f'data-fallback-gap-id="{html.escape(str(item.get("id", "")), quote=True)}" '
                f'data-fallback-gap-artifact="{html.escape(str(item.get("required_artifact", "")), quote=True)}">'
                f'{html.escape(str(item.get("label", "")))}'
                "</li>"
            )
            for item in fallback.get("certification_gaps", [])
            if isinstance(item, dict)
        )
    semantic_snapshot_items = "".join(
        (
        '<li '
        f'data-semantic-snapshot-rule-id="{html.escape(str(item.get("rule_id", "")), quote=True)}" '
        f'data-semantic-snapshot-analysis="{html.escape(str(item.get("expected_event_analysis", "")), quote=True)}" '
        f'data-semantic-snapshot-ast-kind="{html.escape(str((item.get("expected_ast_summary") or {}).get("kind", "")), quote=True)}" '
        f'data-semantic-snapshot-reading-count="{len(item.get("expected_reading_names", [])) if isinstance(item.get("expected_reading_names"), list) else 0}">'
        f'<code>{html.escape(str(item.get("rule_id", "")))}</code>'
        f'<span>{html.escape(str(item.get("expected_event_analysis", "")))}</span>'
        "</li>"
        )
        for item in semantic_snapshots
    )
    surface_parser_items = "".join(
        (
            '<li '
            f'data-surface-parser-family="{html.escape(str(family), quote=True)}" '
            f'data-surface-parser-rule-id="{html.escape(str(item.get("rule_id", "")), quote=True)}" '
            f'data-surface-type-principle="{html.escape(str(item.get("type_principle", "")), quote=True)}" '
            f'data-surface-type-level-open-ended="{str(item.get("type_level_open_ended") is True).lower()}" '
            f'data-surface-parser-claim="{html.escape(str(item.get("surface_parser_claim", "")), quote=True)}" '
            f'data-surface-full-certification="{str(item.get("full_surface_parser_certification") is True).lower()}" '
            f'data-surface-verified-counts="{html.escape(count_list_attribute(item.get("verified_modifier_counts")), quote=True)}" '
            f'data-surface-timed-counts="{html.escape(count_list_attribute(item.get("verified_timed_modifier_counts")), quote=True)}" '
            f'data-surface-untimed-counts="{html.escape(count_list_attribute(item.get("verified_untimed_modifier_counts")), quote=True)}" '
            f'data-surface-max-verified-count="{html.escape(str(item.get("max_verified_modifier_count", "")), quote=True)}" '
            f'data-surface-verified-example-count="{html.escape(str(item.get("verified_example_count", "")), quote=True)}" '
            f'data-surface-generator-schema="{html.escape(str((item.get("witness_generation_spec") or {}).get("schema_version", "")) if isinstance(item.get("witness_generation_spec"), dict) else "", quote=True)}" '
            f'data-surface-generator-kind="{html.escape(str((item.get("witness_generation_spec") or {}).get("generator", "")) if isinstance(item.get("witness_generation_spec"), dict) else "", quote=True)}" '
            f'data-surface-slot-probe-generation-schema="{html.escape(str(((item.get("slot_probe_examples") or {}).get("probe_generation_spec") or {}).get("schema_version", "")) if isinstance(item.get("slot_probe_examples"), dict) and isinstance((item.get("slot_probe_examples") or {}).get("probe_generation_spec"), dict) else "", quote=True)}" '
            f'data-surface-slot-probe-generation-kind="{html.escape(str(((item.get("slot_probe_examples") or {}).get("probe_generation_spec") or {}).get("generator", "")) if isinstance(item.get("slot_probe_examples"), dict) and isinstance((item.get("slot_probe_examples") or {}).get("probe_generation_spec"), dict) else "", quote=True)}" '
            f'data-surface-slot-probe-matrix-count="{html.escape(str((item.get("slot_probe_examples") or {}).get("matrix_example_count", "")) if isinstance(item.get("slot_probe_examples"), dict) else "", quote=True)}" '
            f'data-surface-slot-probe-matrix-generation-schema="{html.escape(str(((item.get("slot_probe_examples") or {}).get("matrix_generation_spec") or {}).get("schema_version", "")) if isinstance(item.get("slot_probe_examples"), dict) and isinstance((item.get("slot_probe_examples") or {}).get("matrix_generation_spec"), dict) else "", quote=True)}" '
            f'data-surface-slot-probe-matrix-generation-kind="{html.escape(str(((item.get("slot_probe_examples") or {}).get("matrix_generation_spec") or {}).get("generator", "")) if isinstance(item.get("slot_probe_examples"), dict) and isinstance((item.get("slot_probe_examples") or {}).get("matrix_generation_spec"), dict) else "", quote=True)}">'
            f'<code>{html.escape(str(family))}</code>'
            f'<span>{html.escape(str(item.get("boundary_note", "")))}</span>'
            f"<ul>{surface_parser_example_items(item)}</ul>"
            f"<ul>{surface_slot_probe_items(item)}</ul>"
            f"<ul>{surface_slot_probe_matrix_items(item)}</ul>"
            "</li>"
        )
        for family, item in (
            surface_parser_coverage.items()
            if isinstance(surface_parser_coverage, dict)
            else []
        )
        if isinstance(item, dict)
    )
    return (
        '<section class="panel certified-fragment-panel" '
        f'data-certified-fragment-schema="{html.escape(schema, quote=True)}" '
        'data-certified-fragment-api="/api/certified-fragment" '
        f'data-registered-construction-count="{len(registered)}" '
        f'data-semantic-snapshot-count="{html.escape(semantic_snapshot_count, quote=True)}" '
        f'data-coverage-registered-success-count="{html.escape(registered_case_count, quote=True)}" '
        f'data-coverage-registered-variant-success-count="{html.escape(registered_variant_case_count, quote=True)}" '
        f'data-coverage-fallback-success-count="{html.escape(fallback_case_count, quote=True)}" '
        f'data-coverage-rejected-unsupported-count="{html.escape(rejected_case_count, quote=True)}" '
        'data-surface-parser-family="modified_transitive_adv_sequence" '
        f'data-surface-type-level-open-ended="{str(modified_surface.get("type_level_open_ended") is True).lower()}" '
        f'data-surface-parser-claim="{html.escape(str(modified_surface.get("surface_parser_claim", "")), quote=True)}" '
        f'data-surface-full-certification="{str(modified_surface.get("full_surface_parser_certification") is True).lower()}" '
        f'data-surface-verified-counts="{html.escape(surface_verified_counts, quote=True)}" '
        f'data-surface-timed-counts="{html.escape(surface_timed_counts, quote=True)}" '
        f'data-surface-untimed-counts="{html.escape(surface_untimed_counts, quote=True)}" '
        f'data-surface-max-verified-count="{html.escape(str(modified_surface.get("max_verified_modifier_count", "")), quote=True)}" '
        f'data-surface-verified-example-count="{html.escape(surface_verified_example_count, quote=True)}" '
        f'data-surface-generator-schema="{html.escape(surface_generator_schema, quote=True)}" '
        f'data-surface-generator-kind="{html.escape(surface_generator_kind, quote=True)}" '
        f'data-surface-generator-modifier-count="{html.escape(surface_generator_modifier_count, quote=True)}" '
        f'data-surface-generator-time-suffix="{html.escape(surface_generator_time_suffix, quote=True)}" '
        f'data-surface-slot-probe-schema="{html.escape(surface_slot_probe_schema, quote=True)}" '
        f'data-surface-slot-probe-count="{html.escape(surface_slot_probe_count, quote=True)}" '
        f'data-surface-slot-probe-generation-schema="{html.escape(surface_slot_probe_generator_schema, quote=True)}" '
        f'data-surface-slot-probe-generation-kind="{html.escape(surface_slot_probe_generator_kind, quote=True)}" '
        f'data-surface-slot-probe-matrix-count="{html.escape(surface_slot_probe_matrix_count, quote=True)}" '
        f'data-surface-slot-probe-matrix-generation-schema="{html.escape(surface_slot_probe_matrix_generator_schema, quote=True)}" '
        f'data-surface-slot-probe-matrix-generation-kind="{html.escape(surface_slot_probe_matrix_generator_kind, quote=True)}" '
        f'data-surface-slot-probe-matrix-type-contract-schema="{html.escape(surface_slot_probe_matrix_type_contract_schema, quote=True)}" '
        f'data-surface-slot-probe-matrix-type-contract-entry-schema="{html.escape(surface_slot_probe_matrix_type_contract_entry_schema, quote=True)}" '
        f'data-surface-slot-probe-matrix-type-contract-entry-count="{html.escape(surface_slot_probe_matrix_type_contract_entry_count, quote=True)}" '
        f'data-surface-slot-probe-matrix-type-contract-diagnostic-schema="{html.escape(surface_slot_probe_matrix_type_contract_diagnostic_schema, quote=True)}" '
        f'data-surface-slot-probe-matrix-type-contract-diagnostic-count="{html.escape(surface_slot_probe_matrix_type_contract_diagnostic_count, quote=True)}" '
        f'data-surface-slot-probe-matrix-type-contract-diagnostic-categories="{html.escape(surface_slot_probe_matrix_type_contract_diagnostic_categories, quote=True)}" '
        f'data-surface-slot-probe-matrix-type-contract-source="{html.escape(surface_slot_probe_matrix_type_contract_source, quote=True)}" '
        f'data-surface-slot-probe-matrix-type-contract-registry-id="{html.escape(surface_slot_probe_matrix_type_contract_registry_id, quote=True)}" '
        f'data-full-natural-language-certification="{str(bool(manifest.get("full_natural_language_certification"))).lower()}" '
        f'data-fallback-certification-level="{html.escape(fallback_level, quote=True)}">'
        "<h2>Certified Fragment</h2>"
        '<div class="certified-fragment">'
        "<dl>"
        f"<dt>schema</dt><dd><code>{html.escape(schema)}</code></dd>"
        "<dt>api</dt><dd><code>/api/certified-fragment</code></dd>"
        f"<dt>full NL</dt><dd>{str(bool(manifest.get('full_natural_language_certification'))).lower()}</dd>"
        f"<dt>registered rules</dt><dd>{len(registered)}</dd>"
        f"<dt>semantic snapshots</dt><dd>{html.escape(semantic_snapshot_count)}</dd>"
        f"<dt>registered cases</dt><dd>{html.escape(registered_case_count)}</dd>"
        f"<dt>registered variants</dt><dd>{html.escape(registered_variant_case_count)}</dd>"
        f"<dt>fallback cases</dt><dd>{html.escape(fallback_case_count)}</dd>"
        f"<dt>rejected cases</dt><dd>{html.escape(rejected_case_count)}</dd>"
        f"<dt>surface parser claim</dt><dd><code>{html.escape(str(modified_surface.get('surface_parser_claim', '')))}</code></dd>"
        f"<dt>verified Adv counts</dt><dd><code>{html.escape(surface_verified_counts)}</code></dd>"
        f"<dt>surface generator</dt><dd><code>{html.escape(surface_generator_kind)}</code></dd>"
        f"<dt>slot probes</dt><dd><code>{html.escape(surface_slot_probe_count)}</code></dd>"
        f"<dt>slot probe generator</dt><dd><code>{html.escape(surface_slot_probe_generator_kind)}</code></dd>"
        f"<dt>slot matrix</dt><dd><code>{html.escape(surface_slot_probe_matrix_count)}</code></dd>"
        f"<dt>type diagnostics</dt><dd><code>{html.escape(surface_slot_probe_matrix_type_contract_diagnostic_categories)}</code></dd>"
        f"<dt>fallback level</dt><dd><code>{html.escape(fallback_level)}</code></dd>"
        "</dl>"
        f"<p>{html.escape(str(manifest.get('methodological_guard', '')))}</p>"
        '<div class="certified-fragment-rules"><strong>registered constructions</strong>'
        f"<ul>{rule_items}</ul></div>"
        '<div class="certified-fragment-coverage"><strong>registered variants</strong>'
        f"<ul>{registered_variant_items}</ul></div>"
        '<div class="certified-fragment-coverage"><strong>fallback coverage</strong>'
        f"<ul>{fallback_items}</ul></div>"
        '<div class="certified-fragment-coverage"><strong>fallback certification gaps</strong>'
        f"<ul>{fallback_gap_items}</ul></div>"
        '<div class="certified-fragment-coverage"><strong>rejected coverage</strong>'
        f"<ul>{rejected_items}</ul></div>"
        '<div class="certified-fragment-surface-parser"><strong>surface parser coverage</strong>'
        f"<ul>{surface_parser_items}</ul></div>"
        '<div class="certified-fragment-snapshots"><strong>semantic snapshots</strong>'
        f"<ul>{semantic_snapshot_items}</ul></div>"
        '<div class="certified-fragment-markers"><strong>rejected markers</strong>'
        f"<ul>{marker_items}</ul></div>"
        "</div>"
        "</section>"
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


def render_page(
    sentence: str = DEFAULT_SENTENCE,
    require_coq: bool = False,
    result: dict[str, Any] | None = None,
    endpoint: str = "/api/analyze",
) -> str:
    result = result or analyze_sentence(sentence, require_coq=require_coq)
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
            "endpoint": endpoint,
            "verification_scope": result.get("verification_scope", {}),
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
    .next-step-action-link {{
      width: fit-content;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 5px 8px;
      color: var(--accent);
      background: var(--accent-soft);
      font-size: 12px;
      font-weight: 650;
      text-decoration: none;
    }}
    .next-step-action-link:focus,
    .next-step-action-link:hover {{
      background: #ffffff;
    }}
    .recovery-action-exports {{
      padding: 12px;
    }}
    .recovery-action-export-list {{
      list-style: none;
      margin: 0;
      padding: 0;
      display: grid;
      gap: 10px;
    }}
    .recovery-action-export {{
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #ffffff;
      padding: 10px;
      display: grid;
      gap: 8px;
    }}
    .recovery-action-export a {{
      color: var(--accent);
      font: 12px/1.35 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      overflow-wrap: anywhere;
    }}
    .recovery-action-export dl {{
      display: grid;
      grid-template-columns: minmax(70px, auto) minmax(0, 1fr);
      gap: 4px 10px;
      margin: 0;
      color: var(--muted);
      font-size: 12px;
    }}
    .recovery-action-export dd {{
      margin: 0;
      word-break: break-word;
    }}
    .recovery-action-export-json summary {{
      cursor: pointer;
      color: var(--muted);
      font-size: 12px;
    }}
    .recovery-action-export-json pre {{
      margin-top: 8px;
      min-height: 0;
      max-height: 260px;
      background: var(--surface);
    }}
    .recovery-action-export-empty {{
      margin: 0;
      color: var(--muted);
      line-height: 1.45;
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
    .verification-scope-body {{
      padding: 12px;
      display: grid;
      gap: 10px;
    }}
    .verification-scope-details {{
      display: grid;
      grid-template-columns: minmax(86px, auto) minmax(0, 1fr);
      gap: 5px 10px;
      margin: 0;
      font-size: 13px;
    }}
    .verification-scope-details dt {{
      color: var(--muted);
    }}
    .verification-scope-details dd {{
      margin: 0;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      word-break: break-word;
    }}
    .verification-scope-list {{
      border-top: 1px solid var(--line);
      padding-top: 8px;
      display: grid;
      gap: 6px;
    }}
    .verification-scope-list strong {{
      font-size: 13px;
    }}
    .verification-scope-list ul {{
      margin: 0;
      padding-left: 18px;
      color: var(--muted);
      line-height: 1.45;
      font-size: 13px;
    }}
    .verification-scope-empty {{
      margin: 0;
      color: var(--muted);
      line-height: 1.45;
    }}
    .certification-upgrade-plan {{
      padding: 12px;
      display: grid;
      gap: 10px;
    }}
    .certification-upgrade-details {{
      display: grid;
      grid-template-columns: minmax(86px, auto) minmax(0, 1fr);
      gap: 5px 10px;
      margin: 0;
      font-size: 13px;
    }}
    .certification-upgrade-details dt,
    .certification-upgrade-steps dt {{
      color: var(--muted);
    }}
    .certification-upgrade-details dd,
    .certification-upgrade-steps dd {{
      margin: 0;
      word-break: break-word;
    }}
    .certification-upgrade-steps {{
      margin: 0;
      padding-left: 18px;
      display: grid;
      gap: 8px;
      font-size: 13px;
    }}
    .certification-upgrade-steps dl {{
      display: grid;
      grid-template-columns: auto minmax(0, 1fr);
      gap: 4px 10px;
      margin: 4px 0 0;
    }}
    .certification-upgrade-commands {{
      border-top: 1px solid var(--line);
      padding-top: 8px;
      display: grid;
      gap: 6px;
      font-size: 13px;
    }}
    .certification-upgrade-commands ul {{
      margin: 0;
      padding-left: 18px;
    }}
    .certification-upgrade-raw pre {{
      min-height: 80px;
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
    .diagnostic-fixture-form {{
      display: grid;
      grid-template-columns: auto minmax(190px, 260px) auto;
      gap: 8px;
      align-items: center;
      margin-top: 12px;
      color: var(--muted);
      font-size: 13px;
    }}
    .diagnostic-fixture-form select {{
      min-height: 34px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #ffffff;
      padding: 0 8px;
      font-size: 13px;
    }}
    .diagnostic-fixture-form button {{
      min-height: 34px;
      padding: 0 10px;
      font-size: 13px;
    }}
    .diagnostic-contract {{
      padding: 12px;
      display: grid;
      gap: 12px;
    }}
    .certified-fragment {{
      padding: 12px;
      display: grid;
      gap: 12px;
    }}
    .diagnostic-contract dl {{
      display: grid;
      grid-template-columns: auto minmax(0, 1fr);
      gap: 4px 10px;
      margin: 0;
      font-size: 13px;
    }}
    .certified-fragment dl {{
      display: grid;
      grid-template-columns: auto minmax(0, 1fr);
      gap: 4px 10px;
      margin: 0;
      font-size: 13px;
    }}
    .diagnostic-contract dt {{
      color: var(--muted);
    }}
    .certified-fragment dt {{
      color: var(--muted);
    }}
    .diagnostic-contract dd {{
      margin: 0;
      word-break: break-word;
    }}
    .certified-fragment dd {{
      margin: 0;
      word-break: break-word;
    }}
    .diagnostic-contract-vocabulary {{
      border-top: 1px solid var(--line);
      padding-top: 10px;
    }}
    .certified-fragment-rules,
    .certified-fragment-coverage,
    .certified-fragment-snapshots,
    .certified-fragment-markers {{
      border-top: 1px solid var(--line);
      padding-top: 10px;
    }}
    .diagnostic-contract-vocabulary strong {{
      display: block;
      margin-bottom: 8px;
      font-size: 13px;
    }}
    .certified-fragment-rules strong,
    .certified-fragment-coverage strong,
    .certified-fragment-snapshots strong,
    .certified-fragment-markers strong {{
      display: block;
      margin-bottom: 8px;
      font-size: 13px;
    }}
    .diagnostic-contract-vocabulary ul {{
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      list-style: none;
      margin: 0;
      padding: 0;
    }}
    .certified-fragment-rules ul,
    .certified-fragment-coverage ul,
    .certified-fragment-snapshots ul,
    .certified-fragment-markers ul {{
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      list-style: none;
      margin: 0;
      padding: 0;
    }}
    .diagnostic-contract-vocabulary li {{
      border: 1px solid var(--line);
      border-radius: 6px;
      background: var(--surface);
      padding: 4px 7px;
      font-size: 12px;
    }}
    .certified-fragment-rules li,
    .certified-fragment-coverage li,
    .certified-fragment-snapshots li,
    .certified-fragment-markers li {{
      border: 1px solid var(--line);
      border-radius: 6px;
      background: var(--surface);
      padding: 4px 7px;
      font-size: 12px;
      display: inline-flex;
      gap: 6px;
      align-items: center;
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
      .diagnostic-fixture-form {{ grid-template-columns: 1fr; }}
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
    {diagnostic_fixture_form(result)}
    <div class="status">{html.escape(status_label(result))}: {html.escape(status_detail(result))}</div>
    <div class="grid">
      {panel("Event Semantics", event_semantics)}
      {panel("Dependent-Type Translation", dependent)}
      {result_state_lexicon_panel(result)}
      {panel("Diagnostics", diagnostics)}
      {panel("API Contract", api_contract)}
      {verification_scope_panel(result)}
      {certification_upgrade_plan_panel(result)}
      {construction_rule_draft_panel(result, sentence, require_coq)}
      {certified_fragment_panel()}
      {diagnostic_contract_panel()}
      {panel("Conclusion", conclusion)}
      {semantic_warnings_panel(result)}
      {lexicon_patch_drafts_panel(result, sentence, require_coq)}
      {next_steps_panel(result)}
      {recovery_action_exports_panel(result)}
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
        if parsed.path == "/api/construction-rule-draft":
            payload, status = self.handle_construction_rule_draft_api(parsed.query)
            download_filename = None
            draft = payload.get("construction_rule_draft")
            if (
                status == HTTPStatus.OK
                and request_wants_download(parsed.query)
                and isinstance(draft, dict)
            ):
                download_filename = construction_rule_draft_artifact_filename(
                    str(draft.get("candidate_rule_id", ""))
                )
            self.write_json_response(
                payload,
                status=status,
                download_filename=download_filename,
            )
            return
        if parsed.path == "/api/diagnostic-fixture":
            self.write_json_response(self.handle_diagnostic_fixture_api(parsed.query))
            return
        if parsed.path == "/api/diagnostic-fixtures":
            self.write_json_response(self.handle_diagnostic_fixtures_api())
            return
        if parsed.path == "/api/diagnostic-contract":
            self.write_json_response(self.handle_diagnostic_contract_api())
            return
        if parsed.path == "/api/certified-fragment":
            self.write_json_response(self.handle_certified_fragment_api())
            return
        if parsed.path == "/api/recovery-action":
            payload, status = self.handle_recovery_action_api(parsed.query)
            download_filename = None
            if status == HTTPStatus.OK and request_wants_download(parsed.query):
                download_filename = recovery_action_artifact_filename(
                    str(payload.get("case", "")),
                    int(payload.get("action_index", 0)),
                )
            self.write_json_response(
                payload,
                status=status,
                download_filename=download_filename,
            )
            return
        if parsed.path == "/api/recovery-action-run":
            payload, status = self.handle_recovery_action_run_api(parsed.query)
            download_filename = None
            if status == HTTPStatus.OK and request_wants_download(parsed.query):
                download_filename = recovery_action_run_artifact_filename(
                    str(payload.get("case", "")),
                    int(payload.get("action_index", 0)),
                )
            self.write_json_response(
                payload,
                status=status,
                download_filename=download_filename,
            )
            return
        if parsed.path == "/api/lexicon-patch-drafts":
            response_format = self.patch_response_format(parsed.query)
            if response_format == "patch":
                self.write_text_response(self.handle_patch_text_api(parsed.query))
                return
            if response_format not in {"json", ""}:
                self.write_json_response(
                    {
                        "schema_version": LEXICON_PATCH_DRAFTS_SCHEMA,
                        "ok": False,
                        "error": (
                            "Unsupported lexicon patch response format "
                            f"{response_format!r}; expected 'json' or 'patch'."
                        ),
                        "allowed_formats": ["json", "patch"],
                    },
                    status=HTTPStatus.BAD_REQUEST,
                )
                return
            self.write_json_response(self.handle_patch_api(parsed.query))
            return
        if parsed.path == "/diagnostic-fixture":
            params = parse_qs(parsed.query)
            case = params.get("case", [DEFAULT_DIAGNOSTIC_FIXTURE_CASE])[0]
            result = diagnostic_fixture_result(case)
            self.write_html_response(
                render_page(
                    result.get("input_sentence", f"diagnostic fixture: {case}"),
                    require_coq=False,
                    result=result,
                    endpoint="/api/diagnostic-fixture",
                )
            )
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

    def handle_construction_rule_draft_api(
        self,
        query: str,
    ) -> tuple[dict[str, Any], HTTPStatus]:
        params = parse_qs(query)
        sentence = params.get("sentence", [""])[0]
        require_coq = params.get("require_coq", ["0"])[0] == "1"
        result = analyze_sentence(sentence, require_coq=require_coq)
        draft = result.get("construction_rule_draft")
        if not isinstance(draft, dict):
            return (
                {
                    "schema_version": CONSTRUCTION_RULE_DRAFT_RESPONSE_SCHEMA,
                    "ok": False,
                    "input_sentence": sentence,
                    "error": "No construction rule draft is available for this analysis.",
                    "verification_scope": result.get("verification_scope", {}),
                    "diagnostics": result.get("diagnostics", {}),
                },
                HTTPStatus.BAD_REQUEST,
            )
        return (
            {
                "schema_version": CONSTRUCTION_RULE_DRAFT_RESPONSE_SCHEMA,
                "ok": True,
                "input_sentence": sentence,
                "draft_schema_version": CONSTRUCTION_RULE_DRAFT_SCHEMA,
                "construction_rule_draft": draft,
                "verification_scope": result.get("verification_scope", {}),
                "diagnostics": result.get("diagnostics", {}),
            },
            HTTPStatus.OK,
        )

    def handle_diagnostic_fixture_api(self, query: str) -> dict[str, Any]:
        params = parse_qs(query)
        case = params.get("case", [DEFAULT_DIAGNOSTIC_FIXTURE_CASE])[0]
        return diagnostic_fixture_result(case)

    def handle_diagnostic_fixtures_api(self) -> dict[str, Any]:
        return diagnostic_fixture_manifest()

    def handle_diagnostic_contract_api(self) -> dict[str, Any]:
        return diagnostic_contract_manifest()

    def handle_certified_fragment_api(self) -> dict[str, Any]:
        return construction_fragment_manifest()

    def handle_recovery_action_api(self, query: str) -> tuple[dict[str, Any], HTTPStatus]:
        params = parse_qs(query)
        case = params.get("case", [DEFAULT_DIAGNOSTIC_FIXTURE_CASE])[0].strip()
        index_text = params.get("index", ["0"])[0].strip()
        if not case or case not in DIAGNOSTIC_FIXTURE_CASES:
            return (
                {
                    "schema_version": RECOVERY_ACTION_SCHEMA,
                    "ok": False,
                    "error": f"Unknown diagnostic fixture {case!r}.",
                    "available_diagnostic_fixtures": sorted(DIAGNOSTIC_FIXTURE_CASES),
                },
                HTTPStatus.BAD_REQUEST,
            )
        try:
            action_index = int(index_text)
        except ValueError:
            return (
                {
                    "schema_version": RECOVERY_ACTION_SCHEMA,
                    "ok": False,
                    "case": case,
                    "error": f"Invalid recovery action index {index_text!r}.",
                },
                HTTPStatus.BAD_REQUEST,
            )
        result = diagnostic_fixture_result(case)
        actions = result.get("diagnostics", {}).get("recovery_actions", [])
        if action_index < 0 or action_index >= len(actions):
            return (
                {
                    "schema_version": RECOVERY_ACTION_SCHEMA,
                    "ok": False,
                    "case": case,
                    "error": f"Recovery action index {action_index} is out of range.",
                    "available_action_count": len(actions),
                },
                HTTPStatus.BAD_REQUEST,
            )
        return recovery_action_export_bundle(case, action_index), HTTPStatus.OK

    def handle_recovery_action_run_api(self, query: str) -> tuple[dict[str, Any], HTTPStatus]:
        payload, status = self.handle_recovery_action_api(query)
        if status != HTTPStatus.OK:
            payload = dict(payload)
            payload["schema_version"] = RECOVERY_INSPECTION_RUN_SCHEMA
            return payload, status
        repair_plan = payload.get("repair_plan", {})
        if not isinstance(repair_plan, dict) or repair_plan.get("can_auto_run") is not True:
            return (
                {
                    "schema_version": RECOVERY_INSPECTION_RUN_SCHEMA,
                    "ok": False,
                    "case": payload.get("case"),
                    "action_index": payload.get("action_index"),
                    "action_kind": payload.get("action", {}).get("kind")
                    if isinstance(payload.get("action"), dict)
                    else None,
                    "automation_mode": repair_plan.get("automation_mode")
                    if isinstance(repair_plan, dict)
                    else None,
                    "can_auto_run": False,
                    "error": "Recovery action requires human review and cannot be auto-run.",
                },
                HTTPStatus.BAD_REQUEST,
            )
        return (
            recovery_action_inspection_run_bundle(
                str(payload["case"]),
                int(payload["action_index"]),
            ),
            HTTPStatus.OK,
        )

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
        return params.get("format", ["json"])[0].strip().lower()

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

    def write_json_response(
        self,
        content: dict[str, Any],
        status: HTTPStatus = HTTPStatus.OK,
        download_filename: str | None = None,
    ) -> None:
        encoded = compact_json(content).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        if download_filename:
            self.send_header(
                "Content-Disposition",
                f'attachment; filename="{download_filename}"',
            )
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
