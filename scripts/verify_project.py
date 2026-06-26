#!/usr/bin/env python3
"""Run the repository's deterministic verification checks."""

from __future__ import annotations

import argparse
import html
import json
import shutil
import subprocess
import sys
import threading
from http.server import ThreadingHTTPServer
from urllib.parse import parse_qs, urlencode, urlparse
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import ProxyHandler, build_opener

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.lexicon_patch_contract_cases import LEXICON_PATCH_CONTRACT_CASES  # noqa: E402
from web.diagnostic_contract import (  # noqa: E402
    DIAGNOSTIC_FAILURE_STAGES,
    DIAGNOSTIC_REPAIR_PLAN_AUTOMATION_MODES,
    DIAGNOSTIC_RECOVERY_ACTION_KINDS,
    INSPECTION_ONLY_RECOVERY_ACTION_KINDS,
    REQUIRED_DIAGNOSTIC_FIXTURE_STAGES,
    SEMANTIC_READING_CONTRACT_FIELDS,
    recovery_action_automation_mode,
    recovery_action_can_auto_run,
)
PYCACHE = ROOT / ".pycache"
COQ_FILE = ROOT / "formalization" / "DependentTypeEventSemantics.v"
PACKAGE_WHEEL_DIR = ROOT / "work" / "verify_package_build"
ROCQ_ENV = Path(
    "/Applications/Rocq-Platform~9.0~2025.08.app/Contents/Resources/bin/coq-env.sh"
)
VALID_DIAGNOSTIC_FAILURE_STAGES = DIAGNOSTIC_FAILURE_STAGES
VALID_DIAGNOSTIC_RECOVERY_ACTION_KINDS = DIAGNOSTIC_RECOVERY_ACTION_KINDS
VALID_DIAGNOSTIC_REPAIR_PLAN_AUTOMATION_MODES = (
    DIAGNOSTIC_REPAIR_PLAN_AUTOMATION_MODES
)
VALID_INSPECTION_ONLY_RECOVERY_ACTION_KINDS = INSPECTION_ONLY_RECOVERY_ACTION_KINDS
VALID_LEXICON_WARNING_KINDS = {
    "derived_result_scale",
    "source_state_used_as_target",
    "unknown_result_source",
}
VALID_LEXICON_WARNING_ACTION_KINDS = {
    "add_state_prestate",
    "license_state_as_target",
    "register_state_lexicon_entry",
}
LEXICON_WARNING_EXPECTATIONS = {
    "derived_result_scale": (
        "register_state_lexicon_entry",
        "derived_scale_no_known_prestate",
    ),
    "source_state_used_as_target": (
        "license_state_as_target",
        "source_state_only",
    ),
    "unknown_result_source": (
        "add_state_prestate",
        "unknown_source_allowed",
    ),
}


def run(label: str, command: list[str]) -> None:
    print(f"==> {label}")
    subprocess.run(command, cwd=ROOT, check=True)


def run_optional_coq_check(require_coq: bool) -> None:
    if shutil.which("coqc"):
        run("optional Coq scaffold boundary check", ["coqc", str(COQ_FILE)])
        return

    if ROCQ_ENV.exists():
        run(
            "optional Coq scaffold boundary check",
            [
                "/bin/zsh",
                "-lc",
                f'eval "$({ROCQ_ENV})" && coqc "{COQ_FILE}"',
            ],
        )
        return

    message = "Coq scaffold boundary check skipped: coqc not found"
    if require_coq:
        raise SystemExit(message)
    print(f"==> {message}")


def check_python_docx_requirement(require_docx: bool) -> None:
    if not require_docx:
        return
    try:
        import docx  # noqa: F401
    except ImportError as exc:
        raise SystemExit(
            "python-docx is required by --require-docx. Run with the bundled "
            "Codex workspace Python runtime or install the project docx extra."
        ) from exc
    print("==> python-docx available")


def run_package_build_smoke_check() -> None:
    PACKAGE_WHEEL_DIR.mkdir(parents=True, exist_ok=True)
    for wheel in PACKAGE_WHEEL_DIR.glob("dependent_type_event_semantics-*.whl"):
        wheel.unlink()
    run(
        "package build smoke check",
        [
            sys.executable,
            "-m",
            "pip",
            "wheel",
            "--no-build-isolation",
            "--no-deps",
            "--wheel-dir",
            str(PACKAGE_WHEEL_DIR),
            ".",
        ],
    )
    if not any(PACKAGE_WHEEL_DIR.glob("dependent_type_event_semantics-*.whl")):
        raise SystemExit("package build smoke check failed: wheel was not created")


def run_lexicon_export_smoke_check() -> None:
    output_dir = ROOT / "work" / "verify_lexicon_patch_export"
    bundle_path = output_dir / "bundle" / "red.json"
    patch_path = output_dir / "patch" / "red.patch"
    run(
        "lexicon patch exporter smoke check",
        [
            sys.executable,
            "scripts/export_lexicon_patch_drafts.py",
            "--sentence",
            "Mary painted the door red",
            "--resolve-draft-id",
            "state-red--unknown_source_allowed",
            "--source-state",
            "not_red",
            "--out",
            str(bundle_path),
            "--patch-out",
            str(patch_path),
        ],
    )
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    patch_text = patch_path.read_text(encoding="utf-8")
    validate_lexicon_patch_bundle("resolved_red_bundle", bundle)
    if patch_text != bundle.get("patch_text_preview"):
        raise SystemExit("lexicon patch exporter smoke check failed: patch text drift")
    if not bundle.get("can_auto_apply"):
        raise SystemExit("lexicon patch exporter smoke check failed: bundle is not auto-applicable")
    if "patch_text_preview" not in bundle:
        raise SystemExit("lexicon patch exporter smoke check failed: missing patch_text_preview")
    if 'StateLexiconEntry("color_scale", default_source_state="not_red")' not in patch_text:
        raise SystemExit("lexicon patch exporter smoke check failed: patch text missing red entry")

    for case in LEXICON_PATCH_CONTRACT_CASES:
        name = case.name
        case_bundle_path = output_dir / "contract" / name / "bundle.json"
        case_patch_path = output_dir / "contract" / name / "state.patch"
        completed = subprocess.run(
            [
                sys.executable,
                "scripts/export_lexicon_patch_drafts.py",
                *case.cli_args(),
                "--out",
                str(case_bundle_path),
                "--patch-out",
                str(case_patch_path),
            ],
            cwd=ROOT,
            check=False,
        )
        if completed.returncode != case.expected_returncode:
            raise SystemExit(
                "lexicon patch exporter smoke check failed: "
                f"{name} returned {completed.returncode}"
            )
        case_bundle = json.loads(case_bundle_path.read_text(encoding="utf-8"))
        case_patch = case_patch_path.read_text(encoding="utf-8")
        expected_bundle = case.expected_bundle()
        if case_bundle != expected_bundle:
            raise SystemExit(
                "lexicon patch exporter smoke check failed: "
                f"{name} bundle drift"
            )
        if case_patch != case_bundle.get("patch_text_preview"):
            raise SystemExit(
                "lexicon patch exporter smoke check failed: "
                f"{name} patch text drift"
            )
        validate_lexicon_patch_bundle(f"cli_negative_{name}", case_bundle)
        contract_errors = case.validation_errors_for(case_bundle)
        if contract_errors:
            raise SystemExit(
                "lexicon patch exporter smoke check failed: "
                f"{name} validation-error contract drift: {'; '.join(contract_errors)}"
            )


def run_lexicon_warning_schema_check() -> None:
    from web.app import analyze_sentence

    print("==> semantic warning and lexicon patch schema check")
    warning_result = analyze_sentence("Mary painted the door red", require_coq=True)
    validate_lexicon_warning_response("mary_painted_red", warning_result)
    clean_result = analyze_sentence("John hammered the metal flat", require_coq=True)
    validate_lexicon_warning_response("john_hammered_flat", clean_result)


def validate_fixture_path(case: str, path: str, route: str, label: str) -> None:
    parsed = urlparse(path)
    if parsed.path != route:
        raise SystemExit(f"web route smoke check failed: {case} {label} path drift")
    if parse_qs(parsed.query, keep_blank_values=True) != {"case": [case]}:
        raise SystemExit(f"web route smoke check failed: {case} {label} case drift")


def artifact_token(value: str) -> str:
    return "".join(
        char if char.isalnum() or char in {"-", "_"} else "-" for char in value
    )


def recovery_action_artifact_filename(case: str, action_index: int) -> str:
    return f"diagnostic_recovery_action__{artifact_token(case)}__{action_index}.json"


def recovery_action_run_artifact_filename(case: str, action_index: int) -> str:
    return f"diagnostic_inspection_run__{artifact_token(case)}__{action_index}.json"


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


def validate_action_route_path(
    case: str,
    action_index: int,
    path: object,
    route: str,
    label: str,
    *,
    download: bool = False,
) -> None:
    if not isinstance(path, str):
        raise SystemExit(
            f"web route smoke check failed: {case} incomplete recovery action export metadata"
        )
    parsed = urlparse(path)
    if parsed.path != route:
        raise SystemExit(f"web route smoke check failed: {case} {label} path drift")
    expected_query = {"case": [case], "index": [str(action_index)]}
    if download:
        expected_query["download"] = ["1"]
    if parse_qs(parsed.query, keep_blank_values=True) != expected_query:
        raise SystemExit(f"web route smoke check failed: {case} {label} case/index drift")


def validate_recovery_action_export_manifest_entry(
    case: str,
    action_index: int,
    expected_stage: str,
    expected_kind: str,
    export_entry: object,
    expected_action: dict | None = None,
) -> None:
    if not isinstance(export_entry, dict):
        raise SystemExit(
            f"web route smoke check failed: {case} malformed recovery action export metadata"
        )
    expected_fields = {
        "schema_version": "diagnostic_recovery_action.v1",
        "case": case,
        "action_index": action_index,
        "kind": expected_kind,
        "failure_stage": expected_stage,
    }
    for field, expected_value in expected_fields.items():
        if export_entry.get(field) != expected_value:
            raise SystemExit(
                "web route smoke check failed: "
                f"{case} recovery action export manifest drift"
            )
    required_fields = [
        "api_path",
        "download_api_path",
        "download_filename",
        "automation_mode",
        "can_auto_run",
        "can_auto_apply",
        "target_fields",
        "inspection_run_api_path",
        "inspection_run_download_api_path",
        "inspection_run_download_filename",
    ]
    if any(field not in export_entry for field in required_fields):
        raise SystemExit(
            f"web route smoke check failed: {case} incomplete recovery action export metadata"
        )
    api_path = export_entry.get("api_path")
    download_api_path = export_entry.get("download_api_path")
    download_filename = export_entry.get("download_filename")
    validate_action_route_path(
        case,
        action_index,
        api_path,
        "/api/recovery-action",
        "recovery action export",
    )
    validate_action_route_path(
        case,
        action_index,
        download_api_path,
        "/api/recovery-action",
        "recovery action download",
        download=True,
    )
    if download_filename != recovery_action_artifact_filename(case, action_index):
        raise SystemExit(
            f"web route smoke check failed: {case} recovery action download filename drift"
        )
    automation_mode = export_entry.get("automation_mode")
    can_auto_run = export_entry.get("can_auto_run")
    can_auto_apply = export_entry.get("can_auto_apply")
    target_fields = export_entry.get("target_fields")
    inspection_run_api_path = export_entry.get("inspection_run_api_path")
    inspection_run_download_api_path = export_entry.get(
        "inspection_run_download_api_path"
    )
    inspection_run_download_filename = export_entry.get(
        "inspection_run_download_filename"
    )
    if automation_mode not in VALID_DIAGNOSTIC_REPAIR_PLAN_AUTOMATION_MODES:
        raise SystemExit(
            f"web route smoke check failed: {case} recovery action export automation drift"
        )
    if type(can_auto_run) is not bool or type(can_auto_apply) is not bool:
        raise SystemExit(
            f"web route smoke check failed: {case} recovery action export automation drift"
        )
    if not string_list(target_fields):
        raise SystemExit(
            f"web route smoke check failed: {case} recovery action export target drift"
        )
    expected_can_run = expected_kind in VALID_INSPECTION_ONLY_RECOVERY_ACTION_KINDS
    if can_auto_run != expected_can_run:
        raise SystemExit(
            f"web route smoke check failed: {case} recovery action export run drift"
        )
    if can_auto_run:
        validate_action_route_path(
            case,
            action_index,
            inspection_run_api_path,
            "/api/recovery-action-run",
            "recovery action run",
        )
        validate_action_route_path(
            case,
            action_index,
            inspection_run_download_api_path,
            "/api/recovery-action-run",
            "recovery action run download",
            download=True,
        )
        if inspection_run_download_filename != recovery_action_run_artifact_filename(
            case,
            action_index,
        ):
            raise SystemExit(
                f"web route smoke check failed: {case} recovery action run download filename drift"
            )
    elif inspection_run_api_path is not None:
        raise SystemExit(
            f"web route smoke check failed: {case} unsafe recovery action run metadata"
        )
    elif (
        inspection_run_download_api_path is not None
        or inspection_run_download_filename is not None
    ):
        raise SystemExit(
            f"web route smoke check failed: {case} unsafe recovery action run metadata"
        )
    if expected_action is not None:
        expected_plan = recovery_action_repair_plan_preview(
            case,
            action_index,
            expected_stage,
            expected_action,
        )
        expected_plan_fields = {
            "automation_mode": expected_plan.get("automation_mode"),
            "can_auto_run": expected_plan.get("can_auto_run"),
            "can_auto_apply": expected_plan.get("can_auto_apply"),
            "target_fields": expected_plan.get("target_fields"),
        }
        for field, expected_value in expected_plan_fields.items():
            if export_entry.get(field) != expected_value:
                raise SystemExit(
                    "web route smoke check failed: "
                    f"{case} recovery action export repair-plan drift"
                )


def nonempty_string_list(value: object) -> bool:
    return isinstance(value, list) and bool(value) and all(
        isinstance(item, str) and item for item in value
    )


def integer_list(value: object) -> bool:
    return isinstance(value, list) and all(type(item) is int for item in value)


def string_list(value: object) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def nonempty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value)


def validate_lexicon_patch_draft(case: str, draft: object) -> None:
    if not isinstance(draft, dict):
        raise SystemExit(f"web warning smoke check failed: {case} malformed lexicon patch draft")
    string_fields = [
        "draft_id",
        "state",
        "scale",
        "default_source_state",
        "current_source_policy",
        "source_policy_after_update",
        "state_lexicon_patch_line",
    ]
    bool_fields = [
        "allow_unknown_source",
        "requires_human_choice",
        "can_auto_apply",
    ]
    required_fields = [*string_fields, *bool_fields, "placeholder_fields"]
    missing_fields = [field for field in required_fields if field not in draft]
    if missing_fields:
        raise SystemExit(
            "web warning smoke check failed: "
            f"{case} incomplete lexicon patch draft"
        )
    for field in string_fields:
        if not nonempty_string(draft.get(field)):
            raise SystemExit(
                "web warning smoke check failed: "
                f"{case} invalid lexicon patch draft {field}"
            )
    for field in bool_fields:
        if type(draft.get(field)) is not bool:
            raise SystemExit(
                "web warning smoke check failed: "
                f"{case} invalid lexicon patch draft {field}"
            )
    if not string_list(draft.get("placeholder_fields")):
        raise SystemExit(
            "web warning smoke check failed: "
            f"{case} invalid lexicon patch draft placeholder_fields"
        )
    if draft.get("source_policy_after_update") != "lexical_prestate":
        raise SystemExit(
            "web warning smoke check failed: "
            f"{case} invalid lexicon patch draft source_policy_after_update"
        )
    if "StateLexiconEntry" not in str(draft.get("state_lexicon_patch_line", "")):
        raise SystemExit(
            "web warning smoke check failed: "
            f"{case} invalid lexicon patch draft state_lexicon_patch_line"
        )


def lexicon_patch_draft_key(draft: dict) -> tuple[object, object, object, object]:
    return (
        draft.get("state"),
        draft.get("scale"),
        draft.get("current_source_policy"),
        draft.get("source_policy_after_update"),
    )


def validate_semantic_warning(case: str, warning: object) -> dict:
    if not isinstance(warning, dict):
        raise SystemExit(f"web warning smoke check failed: {case} malformed semantic warning")
    kind = warning.get("kind")
    if kind not in VALID_LEXICON_WARNING_KINDS:
        raise SystemExit(f"web warning smoke check failed: {case} unknown semantic warning kind")
    for field in ["state", "scale", "message"]:
        if not nonempty_string(warning.get(field)):
            raise SystemExit(
                "web warning smoke check failed: "
                f"{case} incomplete semantic warning metadata"
            )
    action = warning.get("suggested_action")
    if not isinstance(action, dict):
        raise SystemExit(f"web warning smoke check failed: {case} malformed warning action")
    action_kind = action.get("kind")
    expected_action_kind, expected_source_policy = LEXICON_WARNING_EXPECTATIONS[kind]
    if action_kind not in VALID_LEXICON_WARNING_ACTION_KINDS:
        raise SystemExit(f"web warning smoke check failed: {case} unknown warning action kind")
    if action_kind != expected_action_kind:
        raise SystemExit(f"web warning smoke check failed: {case} warning action drift")
    for field in ["label", "detail"]:
        if not nonempty_string(action.get(field)):
            raise SystemExit(
                "web warning smoke check failed: "
                f"{case} incomplete warning action metadata"
            )
    draft = action.get("lexicon_entry_draft")
    validate_lexicon_patch_draft(case, draft)
    assert isinstance(draft, dict)
    if draft.get("state") != warning.get("state") or draft.get("scale") != warning.get("scale"):
        raise SystemExit(f"web warning smoke check failed: {case} warning/draft drift")
    if draft.get("current_source_policy") != expected_source_policy:
        raise SystemExit(f"web warning smoke check failed: {case} warning/draft drift")
    return draft


def validate_lexicon_warning_response(case: str, result: object) -> None:
    if not isinstance(result, dict):
        raise SystemExit(f"web warning smoke check failed: {case} malformed result")
    diagnostics = result.get("diagnostics")
    if not isinstance(diagnostics, dict):
        raise SystemExit(f"web warning smoke check failed: {case} missing diagnostics")
    warnings = diagnostics.get("warnings")
    if not isinstance(warnings, list):
        raise SystemExit(f"web warning smoke check failed: {case} malformed semantic warnings")
    observed_drafts = result.get("lexicon_patch_drafts")
    if not isinstance(observed_drafts, list):
        raise SystemExit(f"web warning smoke check failed: {case} malformed lexicon patch drafts")

    expected_drafts = []
    seen = set()
    for warning in warnings:
        draft = validate_semantic_warning(case, warning)
        key = lexicon_patch_draft_key(draft)
        if key not in seen:
            seen.add(key)
            expected_drafts.append(draft)
    for draft in observed_drafts:
        validate_lexicon_patch_draft(case, draft)
    if observed_drafts != expected_drafts:
        raise SystemExit(f"web warning smoke check failed: {case} warning/draft drift")
    if diagnostics.get("lexicon_patch_draft_count") != len(observed_drafts):
        raise SystemExit(f"web warning smoke check failed: {case} lexicon patch draft count drift")
    manual_required = any(
        isinstance(draft, dict) and draft.get("requires_human_choice")
        for draft in observed_drafts
    )
    if diagnostics.get("manual_repair_required") != manual_required:
        raise SystemExit(f"web warning smoke check failed: {case} manual repair drift")
    patch_text = result.get("patch_text_preview")
    if observed_drafts and not isinstance(patch_text, str):
        raise SystemExit(f"web warning smoke check failed: {case} malformed patch text preview")
    if isinstance(patch_text, str):
        for draft in observed_drafts:
            draft_id = draft.get("draft_id") if isinstance(draft, dict) else None
            if isinstance(draft_id, str) and draft_id and draft_id not in patch_text:
                raise SystemExit(f"web warning smoke check failed: {case} patch text drift")


def validate_lexicon_patch_bundle(case: str, bundle: object) -> None:
    if not isinstance(bundle, dict):
        raise SystemExit(f"lexicon patch bundle check failed: {case} malformed bundle")
    if bundle.get("schema_version") != "lexicon_patch_drafts.v1":
        raise SystemExit(f"lexicon patch bundle check failed: {case} wrong schema")
    diagnostics = bundle.get("diagnostics")
    drafts = bundle.get("lexicon_patch_drafts")
    validation_errors = bundle.get("validation_errors")
    patch_text = bundle.get("patch_text_preview")
    if not isinstance(diagnostics, dict):
        raise SystemExit(f"lexicon patch bundle check failed: {case} malformed diagnostics")
    if not isinstance(drafts, list):
        raise SystemExit(f"lexicon patch bundle check failed: {case} malformed drafts")
    if not string_list(validation_errors):
        raise SystemExit(f"lexicon patch bundle check failed: {case} malformed validation errors")
    if not isinstance(patch_text, str) or not patch_text:
        raise SystemExit(f"lexicon patch bundle check failed: {case} malformed patch text")
    if not isinstance(bundle.get("input_sentence"), str):
        raise SystemExit(f"lexicon patch bundle check failed: {case} malformed input sentence")
    if type(bundle.get("ok")) is not bool:
        raise SystemExit(f"lexicon patch bundle check failed: {case} malformed ok flag")
    for field in ["requires_human_choice", "can_auto_apply"]:
        if type(bundle.get(field)) is not bool:
            raise SystemExit(f"lexicon patch bundle check failed: {case} malformed {field}")
    if type(bundle.get("resolved_patch_count")) is not int:
        raise SystemExit(
            f"lexicon patch bundle check failed: {case} malformed resolved_patch_count"
        )
    if type(diagnostics.get("manual_repair_required")) is not bool:
        raise SystemExit(
            f"lexicon patch bundle check failed: {case} malformed manual repair flag"
        )
    if type(diagnostics.get("lexicon_patch_draft_count")) is not int:
        raise SystemExit(f"lexicon patch bundle check failed: {case} malformed draft count")
    if diagnostics.get("lexicon_patch_draft_count") != len(drafts):
        raise SystemExit(f"lexicon patch bundle check failed: {case} draft count drift")

    for draft in drafts:
        validate_lexicon_patch_draft(case, draft)
    requires_choice = any(
        isinstance(draft, dict) and draft.get("requires_human_choice")
        for draft in drafts
    )
    resolved_count = sum(
        1 for draft in drafts if isinstance(draft, dict) and draft.get("can_auto_apply")
    )
    expected_auto_apply = bool(drafts) and not validation_errors and resolved_count == len(drafts)
    if bundle.get("requires_human_choice") != requires_choice:
        raise SystemExit(f"lexicon patch bundle check failed: {case} human-choice drift")
    if bundle.get("resolved_patch_count") != resolved_count:
        raise SystemExit(f"lexicon patch bundle check failed: {case} resolved count drift")
    if bundle.get("can_auto_apply") != expected_auto_apply:
        raise SystemExit(f"lexicon patch bundle check failed: {case} auto-apply drift")
    if validation_errors:
        if "# Validation errors:" not in patch_text:
            raise SystemExit(f"lexicon patch bundle check failed: {case} validation text drift")
        for error in validation_errors:
            if error not in patch_text:
                raise SystemExit(f"lexicon patch bundle check failed: {case} validation text drift")
        if "# Candidate replacement/addition lines:" in patch_text:
            raise SystemExit(f"lexicon patch bundle check failed: {case} unsafe patch text")
        if "# Resolve validation errors before copying any candidate line." not in patch_text:
            raise SystemExit(f"lexicon patch bundle check failed: {case} validation guard drift")
    elif bundle.get("can_auto_apply"):
        if "# Candidate replacement/addition lines:" not in patch_text:
            raise SystemExit(f"lexicon patch bundle check failed: {case} candidate text drift")
    elif not drafts and "# No auto-applicable patch lines." not in patch_text:
        raise SystemExit(f"lexicon patch bundle check failed: {case} empty patch text drift")

    for draft in drafts:
        assert isinstance(draft, dict)
        draft_auto = draft.get("can_auto_apply")
        if draft_auto and draft.get("requires_human_choice"):
            raise SystemExit(f"lexicon patch bundle check failed: {case} draft state drift")
        if draft_auto and draft.get("placeholder_fields"):
            raise SystemExit(f"lexicon patch bundle check failed: {case} draft state drift")
        if draft_auto and draft.get("default_source_state") == "<choose_source_state>":
            raise SystemExit(f"lexicon patch bundle check failed: {case} draft state drift")
        if not draft_auto and not draft.get("requires_human_choice"):
            raise SystemExit(f"lexicon patch bundle check failed: {case} draft state drift")
        if not draft_auto and not draft.get("placeholder_fields"):
            raise SystemExit(f"lexicon patch bundle check failed: {case} draft state drift")
        if draft_auto and not validation_errors:
            state = str(draft.get("state"))
            source = str(draft.get("default_source_state"))
            if state not in patch_text or source not in patch_text:
                raise SystemExit(f"lexicon patch bundle check failed: {case} candidate text drift")
        if not draft_auto:
            draft_id = str(draft.get("draft_id"))
            if draft_id not in patch_text:
                raise SystemExit(f"lexicon patch bundle check failed: {case} pending text drift")


def validate_semantic_readings_repair_details(case: str, details: object) -> None:
    if not isinstance(details, dict):
        raise SystemExit(f"web route smoke check failed: {case} malformed repair details")
    string_list_fields = [
        "exported_definitions",
        "expected_coq_definitions",
        "missing_coq_definitions",
        "duplicate_reading_names",
    ]
    integer_list_fields = [
        "malformed_reading_indices",
        "failed_type_check_indices",
    ]
    required_fields = [
        *string_list_fields,
        *integer_list_fields,
        "expected_export_count",
        "observed_export_count",
    ]
    missing_fields = [field for field in required_fields if field not in details]
    if missing_fields:
        raise SystemExit(
            "web route smoke check failed: "
            f"{case} incomplete semantic readings repair details"
        )
    for field in string_list_fields:
        if not string_list(details.get(field)):
            raise SystemExit(
                "web route smoke check failed: "
                f"{case} invalid semantic readings repair details {field}"
            )
    for field in integer_list_fields:
        if not integer_list(details.get(field)):
            raise SystemExit(
                "web route smoke check failed: "
                f"{case} invalid semantic readings repair details {field}"
            )
    expected = details.get("expected_export_count")
    observed = details.get("observed_export_count")
    if expected is not None and type(expected) is not int:
        raise SystemExit(
            "web route smoke check failed: "
            f"{case} invalid semantic readings repair details expected_export_count"
        )
    if type(observed) is not int:
        raise SystemExit(
            "web route smoke check failed: "
            f"{case} invalid semantic readings repair details observed_export_count"
        )


def validate_diagnostic_recovery_action(case: str, action: object) -> None:
    if not isinstance(action, dict):
        raise SystemExit(f"web route smoke check failed: {case} malformed recovery action")
    kind = action.get("kind")
    if kind not in VALID_DIAGNOSTIC_RECOVERY_ACTION_KINDS:
        raise SystemExit(f"web route smoke check failed: {case} unknown recovery action kind")
    for field in ["label", "detail"]:
        if not isinstance(action.get(field), str) or not action.get(field):
            raise SystemExit(
                f"web route smoke check failed: {case} incomplete recovery action metadata"
            )
    if kind == "add_missing_coq_definitions" and not nonempty_string_list(
        action.get("target_definitions")
    ):
        raise SystemExit(
            f"web route smoke check failed: {case} invalid recovery action target_definitions"
        )
    if kind == "rename_duplicate_readings" and not nonempty_string_list(
        action.get("duplicate_reading_names")
    ):
        raise SystemExit(
            f"web route smoke check failed: {case} invalid recovery action duplicate_reading_names"
        )
    if kind in {"fix_malformed_readings", "fix_reading_type_checks"} and not integer_list(
        action.get("reading_indices")
    ):
        raise SystemExit(
            f"web route smoke check failed: {case} invalid recovery action reading_indices"
        )
    if kind == "normalize_reading_exports":
        expected = action.get("expected_export_count")
        observed = action.get("observed_export_count")
        exported = action.get("exported_definitions")
        if type(expected) is not int or type(observed) is not int:
            raise SystemExit(
                f"web route smoke check failed: {case} invalid recovery action export counts"
            )
        if not isinstance(exported, list) or not all(
            isinstance(item, str) and item for item in exported
        ):
            raise SystemExit(
                f"web route smoke check failed: {case} invalid recovery action exported_definitions"
            )


def validate_recovery_action_matches_repair_details(
    case: str,
    action: dict,
    details: dict,
) -> None:
    kind = action.get("kind")
    checks = {
        "add_missing_coq_definitions": (
            "target_definitions",
            "missing_coq_definitions",
        ),
        "rename_duplicate_readings": (
            "duplicate_reading_names",
            "duplicate_reading_names",
        ),
        "fix_malformed_readings": (
            "reading_indices",
            "malformed_reading_indices",
        ),
        "fix_reading_type_checks": (
            "reading_indices",
            "failed_type_check_indices",
        ),
    }
    if kind in checks:
        action_field, detail_field = checks[kind]
        if action.get(action_field) != details.get(detail_field):
            raise SystemExit(
                "web route smoke check failed: "
                f"{case} recovery action repair detail drift"
            )
    if kind == "normalize_reading_exports":
        if (
            action.get("expected_export_count") != details.get("expected_export_count")
            or action.get("observed_export_count") != details.get("observed_export_count")
            or action.get("exported_definitions") != details.get("exported_definitions")
        ):
            raise SystemExit(
                "web route smoke check failed: "
                f"{case} recovery action repair detail drift"
            )


def validate_recovery_action_export_bundle(
    case: str,
    action_index: int,
    expected_action: dict,
    bundle: dict,
) -> None:
    if bundle.get("schema_version") != "diagnostic_recovery_action.v1":
        raise SystemExit(f"web route smoke check failed: {case} recovery action schema drift")
    if bundle.get("case") != case:
        raise SystemExit(f"web route smoke check failed: {case} recovery action case drift")
    if bundle.get("action_index") != action_index:
        raise SystemExit(f"web route smoke check failed: {case} recovery action index drift")
    if bundle.get("action") != expected_action:
        raise SystemExit(f"web route smoke check failed: {case} recovery action payload drift")
    repair_plan = bundle.get("repair_plan")
    expected_repair_plan = recovery_action_repair_plan_preview(
        case,
        action_index,
        str(bundle.get("failure_stage")),
        expected_action,
    )
    if repair_plan != expected_repair_plan:
        raise SystemExit(f"web route smoke check failed: {case} recovery action repair-plan drift")
    if not isinstance(bundle.get("failure_stage"), str):
        raise SystemExit(f"web route smoke check failed: {case} recovery action stage drift")
    contract = bundle.get("contract")
    if not isinstance(contract, dict):
        raise SystemExit(f"web route smoke check failed: {case} recovery action contract drift")
    validate_diagnostic_contract_manifest(contract)


def nested_field_value(payload: dict, path: str) -> object:
    current: object = payload
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def validate_recovery_action_inspection_run_bundle(
    case: str,
    action_index: int,
    expected_action_bundle: dict,
    fixture_payload: dict,
    run_bundle: dict,
) -> None:
    repair_plan = expected_action_bundle.get("repair_plan", {})
    expected_action = expected_action_bundle.get("action", {})
    if run_bundle.get("schema_version") != "diagnostic_inspection_run.v1":
        raise SystemExit(f"web route smoke check failed: {case} inspection run schema drift")
    if run_bundle.get("ok") is not True:
        raise SystemExit(f"web route smoke check failed: {case} inspection run ok drift")
    if run_bundle.get("case") != case:
        raise SystemExit(f"web route smoke check failed: {case} inspection run case drift")
    if run_bundle.get("action_index") != action_index:
        raise SystemExit(f"web route smoke check failed: {case} inspection run index drift")
    if run_bundle.get("action_kind") != expected_action.get("kind"):
        raise SystemExit(f"web route smoke check failed: {case} inspection run kind drift")
    if run_bundle.get("failure_stage") != expected_action_bundle.get("failure_stage"):
        raise SystemExit(f"web route smoke check failed: {case} inspection run stage drift")
    if run_bundle.get("automation_mode") != repair_plan.get("automation_mode"):
        raise SystemExit(f"web route smoke check failed: {case} inspection run automation drift")
    if run_bundle.get("can_auto_run") is not True:
        raise SystemExit(f"web route smoke check failed: {case} inspection run auto-run drift")
    if run_bundle.get("can_auto_apply") is not False:
        raise SystemExit(f"web route smoke check failed: {case} inspection run apply drift")
    expected_fields = repair_plan.get("target_fields")
    if run_bundle.get("target_fields") != expected_fields:
        raise SystemExit(f"web route smoke check failed: {case} inspection run field drift")
    inspection_results = run_bundle.get("inspection_results")
    if not isinstance(inspection_results, dict):
        raise SystemExit(f"web route smoke check failed: {case} inspection run result drift")
    for field in expected_fields:
        if inspection_results.get(field) != nested_field_value(fixture_payload, field):
            raise SystemExit(
                "web route smoke check failed: "
                f"{case} inspection run {field} value drift"
            )
    if run_bundle.get("repair_plan") != repair_plan:
        raise SystemExit(f"web route smoke check failed: {case} inspection run plan drift")
    contract = run_bundle.get("contract")
    if not isinstance(contract, dict):
        raise SystemExit(f"web route smoke check failed: {case} inspection run contract drift")
    validate_diagnostic_contract_manifest(contract)


def validate_recovery_action_inspection_run_rejection(
    case: str,
    action_index: int,
    expected_action_bundle: dict,
    run_bundle: dict,
) -> None:
    repair_plan = expected_action_bundle.get("repair_plan", {})
    expected_action = expected_action_bundle.get("action", {})
    if run_bundle.get("schema_version") != "diagnostic_inspection_run.v1":
        raise SystemExit(f"web route smoke check failed: {case} inspection rejection schema drift")
    if run_bundle.get("ok") is not False:
        raise SystemExit(f"web route smoke check failed: {case} inspection rejection ok drift")
    if run_bundle.get("case") != case:
        raise SystemExit(f"web route smoke check failed: {case} inspection rejection case drift")
    if run_bundle.get("action_index") != action_index:
        raise SystemExit(f"web route smoke check failed: {case} inspection rejection index drift")
    if run_bundle.get("action_kind") != expected_action.get("kind"):
        raise SystemExit(f"web route smoke check failed: {case} inspection rejection kind drift")
    if run_bundle.get("automation_mode") != repair_plan.get("automation_mode"):
        raise SystemExit(
            f"web route smoke check failed: {case} inspection rejection automation drift"
        )
    if run_bundle.get("can_auto_run") is not False:
        raise SystemExit(f"web route smoke check failed: {case} inspection rejection run drift")
    if "requires human review" not in str(run_bundle.get("error", "")):
        raise SystemExit(f"web route smoke check failed: {case} inspection rejection error drift")


def diagnostic_contract_bundle_for_recovery_action() -> dict:
    return {
        "schema_version": "diagnostic_contract.v1",
        "failure_stages": sorted(VALID_DIAGNOSTIC_FAILURE_STAGES),
        "required_fixture_stages": sorted(REQUIRED_DIAGNOSTIC_FIXTURE_STAGES),
        "recovery_action_kinds": sorted(VALID_DIAGNOSTIC_RECOVERY_ACTION_KINDS),
        "repair_plan_automation_modes": sorted(
            VALID_DIAGNOSTIC_REPAIR_PLAN_AUTOMATION_MODES
        ),
        "inspection_only_recovery_action_kinds": sorted(
            VALID_INSPECTION_ONLY_RECOVERY_ACTION_KINDS
        ),
        "semantic_reading_fields": sorted(SEMANTIC_READING_CONTRACT_FIELDS),
    }


def recovery_action_string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item]


def recovery_action_integer_list(value: object) -> list[int]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, int)]


def recovery_action_patch_preview(action: dict) -> str:
    kind = str(action.get("kind", ""))
    if kind == "add_missing_coq_definitions":
        definitions = recovery_action_string_list(action.get("target_definitions"))
        lines = ["(* candidate Coq/Rocq exports; review formulas before applying *)"]
        lines.extend(
            f"Definition {name} : PropT := (* TODO: checked semantic reading formula *)."
            for name in definitions
        )
        return "\n".join(lines)
    if kind == "rename_duplicate_readings":
        names = ", ".join(recovery_action_string_list(action.get("duplicate_reading_names")))
        return f"# rename duplicate semantic_readings entries: {names}"
    if kind == "fix_malformed_readings":
        indices = ", ".join(
            str(index) for index in recovery_action_integer_list(action.get("reading_indices"))
        )
        return f"# repair malformed semantic_readings record indices: {indices}"
    if kind == "fix_reading_type_checks":
        indices = ", ".join(
            str(index) for index in recovery_action_integer_list(action.get("reading_indices"))
        )
        return f"# repair reading-local type_check failures at indices: {indices}"
    if kind == "normalize_reading_exports":
        expected = action.get("expected_export_count")
        observed = action.get("observed_export_count")
        definitions = (
            ", ".join(recovery_action_string_list(action.get("exported_definitions")))
            or "none"
        )
        return (
            "# normalize Prop/PropT exports\n"
            f"# expected_export_count={expected}; observed_export_count={observed}\n"
            f"# exported_definitions={definitions}"
        )
    if kind == "add_semantic_readings":
        return "# emit at least one semantic_readings record before Coq/Rocq export"
    return ""


def recovery_action_repair_plan_preview(
    case: str,
    action_index: int,
    expected_stage: str,
    expected_action: dict,
) -> dict:
    kind = str(expected_action.get("kind", ""))
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
    detail = str(expected_action.get("detail") or "Inspect the failing diagnostic stage.")
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
    return {
        "schema_version": "diagnostic_repair_plan.v1",
        "case": case,
        "action_index": action_index,
        "action_kind": kind,
        "failure_stage": expected_stage,
        "automation_mode": automation_mode,
        "can_auto_run": recovery_action_can_auto_run(kind),
        "can_auto_apply": False,
        "target_fields": target_fields_by_kind.get(kind, []),
        "steps": [
            detail,
            action_step,
            "Re-run deterministic verification after the repair.",
        ],
        "patch_text_preview": recovery_action_patch_preview(expected_action),
        "verification_commands": [
            "python3 scripts/verify_project.py --require-coq --require-docx",
        ],
    }


def recovery_action_export_preview_json(
    case: str,
    action_index: int,
    expected_stage: str,
    expected_action: dict,
) -> str:
    return json.dumps(
        {
            "schema_version": "diagnostic_recovery_action.v1",
            "case": case,
            "action_index": action_index,
            "failure_stage": expected_stage,
            "action": expected_action,
            "repair_plan": recovery_action_repair_plan_preview(
                case,
                action_index,
                expected_stage,
                expected_action,
            ),
            "contract": diagnostic_contract_bundle_for_recovery_action(),
        },
        ensure_ascii=False,
        indent=2,
    )


def recovery_action_inspection_run_preview_json(
    case: str,
    action_index: int,
    expected_stage: str,
    expected_action: dict,
    fixture_payload: dict,
) -> str:
    repair_plan = recovery_action_repair_plan_preview(
        case,
        action_index,
        expected_stage,
        expected_action,
    )
    target_fields = repair_plan.get("target_fields")
    inspection_results = {
        field: nested_field_value(fixture_payload, field)
        for field in target_fields
    }
    return json.dumps(
        {
            "schema_version": "diagnostic_inspection_run.v1",
            "ok": True,
            "case": case,
            "action_index": action_index,
            "action_kind": expected_action.get("kind"),
            "failure_stage": expected_stage,
            "automation_mode": repair_plan.get("automation_mode"),
            "can_auto_run": repair_plan.get("can_auto_run"),
            "can_auto_apply": repair_plan.get("can_auto_apply"),
            "target_fields": target_fields,
            "inspection_results": inspection_results,
            "repair_plan": repair_plan,
            "contract": diagnostic_contract_bundle_for_recovery_action(),
        },
        ensure_ascii=False,
        indent=2,
    )


def html_list_item_block(page: str, marker: str, context: str) -> str:
    marker_start = page.find(marker)
    if marker_start < 0:
        raise SystemExit(f"web route smoke check failed: {context} missing {marker}")
    start = page.rfind("<li", 0, marker_start)
    if start < 0:
        raise SystemExit(f"web route smoke check failed: {context} missing list item start")
    end = page.find("</li>", marker_start)
    if end < 0:
        raise SystemExit(f"web route smoke check failed: {context} missing closing list item")
    return page[start : end + len("</li>")]


def require_html_fragments(block: str, fragments: list[str], context: str) -> None:
    for fragment in fragments:
        if fragment not in block:
            raise SystemExit(f"web route smoke check failed: {context} missing {fragment}")


def validate_successful_semantic_reading_contract(
    case: str,
    payload: dict,
    page: str,
) -> None:
    check = payload.get("semantic_readings_check")
    if not isinstance(check, dict) or check.get("ok") is not True:
        return
    readings = payload.get("semantic_readings")
    if not isinstance(readings, list) or not readings:
        raise SystemExit(
            f"web route smoke check failed: {case} missing successful semantic readings"
        )
    for index, reading in enumerate(readings):
        if not isinstance(reading, dict):
            raise SystemExit(
                f"web route smoke check failed: {case} malformed semantic reading {index}"
            )
        missing_fields = sorted(
            field
            for field in SEMANTIC_READING_CONTRACT_FIELDS
            if field not in reading
        )
        if missing_fields:
            raise SystemExit(
                f"web route smoke check failed: {case} semantic reading {index} "
                "missing contract fields "
                + ", ".join(missing_fields)
            )
        explanation = reading.get("reading_explanation")
        if not isinstance(explanation, str) or not explanation.strip():
            raise SystemExit(
                f"web route smoke check failed: {case} semantic reading {index} "
                "missing reading_explanation"
            )
        expected_interpretation = (
            "<dt>interpretation</dt><dd>"
            + html.escape(explanation)
            + "</dd>"
        )
        if expected_interpretation not in page:
            raise SystemExit(
                f"web route smoke check failed: {case} semantic reading {index} "
                "reading_explanation HTML drift"
            )


def validate_analyze_success_envelope(
    payload: dict,
    sentence: str,
    label: str,
    required_stages: list[str],
) -> dict:
    if payload.get("schema_version") != "analyze.v1":
        raise SystemExit(f"web route smoke check failed: {label} analyze schema drift")
    if payload.get("ok") is not True:
        raise SystemExit(f"web route smoke check failed: {label} analyze did not verify")
    if payload.get("input_sentence") != sentence:
        raise SystemExit(f"web route smoke check failed: {label} analyze input drift")
    diagnostics = payload.get("diagnostics")
    if not isinstance(diagnostics, dict):
        raise SystemExit(f"web route smoke check failed: {label} diagnostics missing")
    if diagnostics.get("summary") != "translation verified":
        raise SystemExit(f"web route smoke check failed: {label} diagnostics summary drift")
    if diagnostics.get("failure_stage") is not None:
        raise SystemExit(f"web route smoke check failed: {label} diagnostics stage drift")
    if diagnostics.get("recovery_actions") != []:
        raise SystemExit(f"web route smoke check failed: {label} recovery action drift")
    stages = diagnostics.get("stages")
    if not isinstance(stages, dict):
        raise SystemExit(f"web route smoke check failed: {label} stage map missing")
    for stage in required_stages:
        if stages.get(stage) != "passed":
            raise SystemExit(f"web route smoke check failed: {label} stage drift")
    return diagnostics


def validate_verification_scope(
    payload: dict,
    page: str,
    label: str,
    expected_kind: str,
    expected_level: str,
    expected_rule_id: str | None,
) -> None:
    scope = payload.get("verification_scope")
    if not isinstance(scope, dict):
        raise SystemExit(f"web route smoke check failed: {label} verification scope missing")
    if scope.get("kind") != expected_kind:
        raise SystemExit(f"web route smoke check failed: {label} verification scope kind drift")
    if scope.get("certification_level") != expected_level:
        raise SystemExit(f"web route smoke check failed: {label} verification scope level drift")
    if scope.get("rule_id") != expected_rule_id:
        raise SystemExit(f"web route smoke check failed: {label} verification scope rule drift")
    if not isinstance(scope.get("guarantees"), list) or not isinstance(
        scope.get("limitations"),
        list,
    ):
        raise SystemExit(f"web route smoke check failed: {label} verification scope shape drift")
    require_text_fragments(
        page,
        [
            "Verification Scope",
            f'data-verification-scope-kind="{expected_kind}"',
            f'data-verification-level="{expected_level}"',
            f"<dt>kind</dt><dd>{expected_kind}</dd>",
            f"<dt>level</dt><dd>{expected_level}</dd>",
            f"<dt>rule</dt><dd>{expected_rule_id or 'none'}</dd>",
        ],
        f"{label} verification scope HTML",
    )


def require_text_fragments(text: str, fragments: list[str], label: str) -> None:
    for fragment in fragments:
        if fragment not in text:
            raise SystemExit(f"web route smoke check failed: {label} drift")


def forbid_text_fragments(text: str, fragments: list[str], label: str) -> None:
    for fragment in fragments:
        if fragment in text:
            raise SystemExit(f"web route smoke check failed: {label} drift")


def validate_semantic_reading_summary(
    reading: dict,
    expected_fields: dict[str, str],
    attachment_kind: str,
    label: str,
    expected_type: str | None = "Prop",
) -> None:
    if not isinstance(reading, dict):
        raise SystemExit(f"web route smoke check failed: {label} semantic reading malformed")
    for field, expected in expected_fields.items():
        if reading.get(field) != expected:
            raise SystemExit(f"web route smoke check failed: {label} semantic reading drift")
    attachment = reading.get("attachment_summary")
    if not isinstance(attachment, dict) or attachment.get("kind") != attachment_kind:
        raise SystemExit(f"web route smoke check failed: {label} attachment drift")
    if expected_type is None:
        return
    local_type = reading.get("type_check")
    if (
        not isinstance(local_type, dict)
        or local_type.get("ok") is not True
        or local_type.get("type") != expected_type
    ):
        raise SystemExit(f"web route smoke check failed: {label} reading type drift")


def validate_analyze_fallback_success(payload: dict, page: str, sentence: str) -> None:
    case = "analyze_fallback_success"
    validate_analyze_success_envelope(
        payload,
        sentence,
        "fallback",
        ["semantic_readings_check"],
    )
    validate_verification_scope(
        payload,
        page,
        "fallback",
        "fallback_shallow",
        "shallow_scaffold",
        None,
    )
    readings = payload.get("semantic_readings")
    if not isinstance(readings, list) or len(readings) != 1:
        raise SystemExit("web route smoke check failed: fallback semantic reading count drift")
    validate_semantic_reading_summary(
        readings[0],
        {
            "name": "fallback_single_reading",
            "scope": "fallback_single_reading",
            "source": "fallback_event_semantics",
            "coq_definition": "example_1",
        },
        "none",
        "fallback",
        expected_type=None,
    )
    coq_code = payload.get("coq_code")
    if not isinstance(coq_code, str) or "Definition example_1" not in coq_code:
        raise SystemExit("web route smoke check failed: fallback Coq export drift")
    validate_successful_semantic_reading_contract(case, payload, page)
    expected_page_fragments = [
        "Semantic Readings Check",
        'data-reading-name="fallback_single_reading"',
        'data-coq-definition="example_1"',
        "<dt>source</dt><dd>fallback_event_semantics</dd>",
        "<dt>coq</dt><dd>example_1</dd>",
        "<dt>attachment</dt><dd>none</dd>",
    ]
    require_text_fragments(page, expected_page_fragments, "fallback HTML")
    if html.escape(sentence, quote=True) not in page:
        raise SystemExit("web route smoke check failed: fallback page input drift")


def validate_analyze_quantifier_scope_success(
    payload: dict,
    page: str,
    sentence: str,
) -> None:
    case = "analyze_quantifier_scope_success"
    validate_analyze_success_envelope(
        payload,
        sentence,
        "quantifier",
        ["semantic_readings_check", "construction_hygiene", "coq_check"],
    )
    validate_verification_scope(
        payload,
        page,
        "quantifier",
        "registered_construction",
        "construction_rule",
        "quantifier_scope_ambiguity",
    )
    check = payload.get("semantic_readings_check")
    if (
        not isinstance(check, dict)
        or check.get("ok") is not True
        or check.get("reading_count") != 2
    ):
        raise SystemExit("web route smoke check failed: quantifier reading-count drift")
    expected_readings = [
        ("some_boy_wide_scope", "subject_then_object"),
        ("some_girl_wide_scope", "object_then_subject"),
    ]
    readings = payload.get("semantic_readings")
    if not isinstance(readings, list) or len(readings) != len(expected_readings):
        raise SystemExit("web route smoke check failed: quantifier semantic reading drift")
    coq_code = payload.get("coq_code")
    if not isinstance(coq_code, str):
        raise SystemExit("web route smoke check failed: quantifier Coq export missing")
    for reading, (name, scope) in zip(readings, expected_readings):
        validate_semantic_reading_summary(
            reading,
            {
                "name": name,
                "scope": scope,
                "source": "quantifier_scope",
                "coq_definition": name,
            },
            "plain",
            "quantifier",
        )
        require_text_fragments(
            coq_code,
            [f"Definition {name} : Prop :=", f"Check {name}."],
            "quantifier Coq export",
        )
        expected_page_fragments = [
            f'data-reading-name="{name}"',
            f'data-coq-definition="{name}"',
            f"<dt>scope</dt><dd>{scope}</dd>",
            "<dt>source</dt><dd>quantifier_scope</dd>",
            "<dt>attachment</dt><dd>plain</dd>",
            f"<dt>coq</dt><dd>{name}</dd>",
        ]
        require_text_fragments(page, expected_page_fragments, "quantifier HTML")
    validate_successful_semantic_reading_contract(case, payload, page)
    if html.escape(sentence, quote=True) not in page:
        raise SystemExit("web route smoke check failed: quantifier page input drift")


def validate_analyze_perception_success(payload: dict, page: str, sentence: str) -> None:
    case = "analyze_perception_success"
    validate_analyze_success_envelope(
        payload,
        sentence,
        "perception",
        ["type_check", "semantic_readings_check", "construction_hygiene", "coq_check"],
    )
    validate_verification_scope(
        payload,
        page,
        "perception",
        "registered_construction",
        "construction_rule",
        "perception_nominalization",
    )
    event_semantics = payload.get("event_semantics")
    if not isinstance(event_semantics, dict):
        raise SystemExit("web route smoke check failed: perception event semantics missing")
    if event_semantics.get("analysis") != "parsons-perception-complement":
        raise SystemExit("web route smoke check failed: perception analysis drift")
    if event_semantics.get("typed_replacement") != "see(Mary, E(leave(John)))":
        raise SystemExit("web route smoke check failed: perception typed replacement drift")
    if payload.get("dependent_type_translation") != "see(Mary, E(leave(John)))":
        raise SystemExit("web route smoke check failed: perception translation drift")
    check = payload.get("semantic_readings_check")
    if (
        not isinstance(check, dict)
        or check.get("ok") is not True
        or check.get("reading_count") != 1
    ):
        raise SystemExit("web route smoke check failed: perception reading-count drift")
    readings = payload.get("semantic_readings")
    if not isinstance(readings, list) or len(readings) != 1:
        raise SystemExit("web route smoke check failed: perception semantic reading drift")
    validate_semantic_reading_summary(
        readings[0],
        {
            "name": "primary",
            "scope": "unspecified",
            "source": "perception_nominalization",
            "dependent_type_translation": "see(Mary, E(leave(John)))",
            "coq_definition": "mary_saw_john_leave",
        },
        "none",
        "perception",
    )
    coq_code = payload.get("coq_code")
    if not isinstance(coq_code, str):
        raise SystemExit("web route smoke check failed: perception Coq export missing")
    expected_coq_fragments = [
        "Parameter E : Prop -> Entity.",
        "Definition mary_saw_john_leave : Prop :=",
        "see Mary (E (leave John)).",
        "Check mary_saw_john_leave.",
    ]
    require_text_fragments(coq_code, expected_coq_fragments, "perception Coq export")
    forbid_text_fragments(coq_code, ["Parameter Event", "Agent", "Theme"], "perception event export")
    expected_page_fragments = [
        "parsons-perception-complement",
        "see(Mary, E(leave(John)))",
        'data-reading-name="primary"',
        'data-coq-definition="mary_saw_john_leave"',
        "<dt>scope</dt><dd>unspecified</dd>",
        "<dt>source</dt><dd>perception_nominalization</dd>",
        "<dt>attachment</dt><dd>none</dd>",
        "<dt>coq</dt><dd>mary_saw_john_leave</dd>",
    ]
    require_text_fragments(page, expected_page_fragments, "perception HTML")
    validate_successful_semantic_reading_contract(case, payload, page)
    if html.escape(sentence, quote=True) not in page:
        raise SystemExit("web route smoke check failed: perception page input drift")


def validate_analyze_timed_after_success(payload: dict, page: str, sentence: str) -> None:
    case = "analyze_timed_after_success"
    expected_translation = (
        "exists t_sing t_salute : Time. sing(Marseillaise, t_sing) and "
        "salute(John, flag, t_salute) and before(t_sing, t_salute)"
    )
    validate_analyze_success_envelope(
        payload,
        sentence,
        "timed-after",
        ["type_check", "semantic_readings_check", "construction_hygiene", "coq_check"],
    )
    validate_verification_scope(
        payload,
        page,
        "timed-after",
        "registered_construction",
        "construction_rule",
        "timed_after",
    )
    if payload.get("kind") != "timed_after":
        raise SystemExit("web route smoke check failed: timed-after kind drift")
    construction_rule = payload.get("construction_rule")
    if not isinstance(construction_rule, dict):
        raise SystemExit("web route smoke check failed: timed-after construction rule missing")
    if construction_rule.get("id") != "timed_after":
        raise SystemExit("web route smoke check failed: timed-after construction rule drift")
    forbidden = construction_rule.get("forbidden_coq_fragments")
    if (
        not isinstance(forbidden, list)
        or "Parameter Event : Type." not in forbidden
        or "exists e : Event" not in forbidden
    ):
        raise SystemExit("web route smoke check failed: timed-after hygiene policy drift")
    event_semantics = payload.get("event_semantics")
    if not isinstance(event_semantics, dict):
        raise SystemExit("web route smoke check failed: timed-after event semantics missing")
    if event_semantics.get("analysis") != "parsons-after-event-talk":
        raise SystemExit("web route smoke check failed: timed-after analysis drift")
    if event_semantics.get("typed_replacement") != expected_translation:
        raise SystemExit("web route smoke check failed: timed-after typed replacement drift")
    if payload.get("dependent_type_translation") != expected_translation:
        raise SystemExit("web route smoke check failed: timed-after translation drift")
    ast = payload.get("ast")
    if not isinstance(ast, dict) or ast.get("kind") != "timed_after":
        raise SystemExit("web route smoke check failed: timed-after AST kind drift")
    if ast.get("binders") != [
        {"variable": "t_sing", "type": "Time"},
        {"variable": "t_salute", "type": "Time"},
    ]:
        raise SystemExit("web route smoke check failed: timed-after binder drift")
    if ast.get("relation") != {
        "predicate": "before",
        "predicate_type": "Time -> Time -> Prop",
        "arguments": ["t_sing", "t_salute"],
    }:
        raise SystemExit("web route smoke check failed: timed-after relation drift")
    if ast.get("first") != {
        "predicate": "sing",
        "predicate_type": "Entity -> Time -> Prop",
        "theme": {"name": "Marseillaise", "type": "Entity"},
        "time": "t_sing",
    }:
        raise SystemExit("web route smoke check failed: timed-after first clause drift")
    if ast.get("second") != {
        "predicate": "salute",
        "predicate_type": "Entity -> Entity -> Time -> Prop",
        "agent": {"name": "John", "type": "Entity"},
        "theme": {"name": "flag", "type": "Entity"},
        "time": "t_salute",
    }:
        raise SystemExit("web route smoke check failed: timed-after second clause drift")
    type_check = payload.get("type_check")
    if (
        not isinstance(type_check, dict)
        or type_check.get("ok") is not True
        or type_check.get("type") != "Prop"
    ):
        raise SystemExit("web route smoke check failed: timed-after type-check drift")
    check = payload.get("semantic_readings_check")
    if (
        not isinstance(check, dict)
        or check.get("ok") is not True
        or check.get("reading_count") != 1
    ):
        raise SystemExit("web route smoke check failed: timed-after reading-count drift")
    repair = check.get("repair_details")
    if (
        not isinstance(repair, dict)
        or repair.get("expected_coq_definitions") != ["after_singing_salute"]
        or repair.get("exported_definitions") != ["after_singing_salute"]
        or repair.get("observed_export_count") != 1
    ):
        raise SystemExit("web route smoke check failed: timed-after repair-detail drift")
    readings = payload.get("semantic_readings")
    if not isinstance(readings, list) or len(readings) != 1:
        raise SystemExit("web route smoke check failed: timed-after semantic reading drift")
    validate_semantic_reading_summary(
        readings[0],
        {
            "name": "timed_after_singing_salute",
            "scope": "time_before_salute",
            "source": "timed_after",
            "dependent_type_translation": expected_translation,
            "coq_definition": "after_singing_salute",
        },
        "none",
        "timed-after",
    )
    coq_code = payload.get("coq_code")
    if not isinstance(coq_code, str):
        raise SystemExit("web route smoke check failed: timed-after Coq export missing")
    expected_coq_fragments = [
        "Parameter Time : Type.",
        "Parameter Marseillaise : Entity.",
        "Parameter John : Entity.",
        "Parameter flag : Entity.",
        "Parameter sing : Entity -> Time -> Prop.",
        "Parameter salute : Entity -> Entity -> Time -> Prop.",
        "Parameter before : Time -> Time -> Prop.",
        "Definition after_singing_salute : Prop :=",
        "exists t_sing : Time,",
        "exists t_salute : Time,",
        "sing Marseillaise t_sing /\\",
        "salute John flag t_salute /\\",
        "before t_sing t_salute.",
        "Check after_singing_salute.",
    ]
    require_text_fragments(coq_code, expected_coq_fragments, "timed-after Coq export")
    forbid_text_fragments(
        coq_code,
        ["Parameter Event : Type.", "exists e : Event", "Agent", "Theme"],
        "timed-after event export",
    )
    expected_page_fragments = [
        "timed_after",
        "parsons-after-event-talk",
        html.escape(expected_translation, quote=True),
        'data-reading-name="timed_after_singing_salute"',
        'data-coq-definition="after_singing_salute"',
        "<dt>scope</dt><dd>time_before_salute</dd>",
        "<dt>source</dt><dd>timed_after</dd>",
        "<dt>attachment</dt><dd>none</dd>",
        "<dt>coq</dt><dd>after_singing_salute</dd>",
    ]
    require_text_fragments(page, expected_page_fragments, "timed-after HTML")
    validate_successful_semantic_reading_contract(case, payload, page)
    if html.escape(sentence, quote=True) not in page:
        raise SystemExit("web route smoke check failed: timed-after page input drift")


def validate_analyze_universal_timed_burning_success(
    payload: dict,
    page: str,
    sentence: str,
) -> None:
    case = "analyze_universal_timed_burning_success"
    expected_translation = (
        "forall x : Entity. forall t : Time. burn(x, t) -> consume(oxygen, t)"
    )
    validate_analyze_success_envelope(
        payload,
        sentence,
        "burning",
        ["type_check", "semantic_readings_check", "construction_hygiene", "coq_check"],
    )
    validate_verification_scope(
        payload,
        page,
        "burning",
        "registered_construction",
        "construction_rule",
        "universal_timed_burning",
    )
    if payload.get("kind") != "universal_timed_burning":
        raise SystemExit("web route smoke check failed: burning kind drift")
    construction_rule = payload.get("construction_rule")
    if not isinstance(construction_rule, dict):
        raise SystemExit("web route smoke check failed: burning construction rule missing")
    if construction_rule.get("id") != "universal_timed_burning":
        raise SystemExit("web route smoke check failed: burning construction rule drift")
    forbidden = construction_rule.get("forbidden_coq_fragments")
    if not isinstance(forbidden, list) or "Parameter Event : Type." not in forbidden or "IN" not in forbidden:
        raise SystemExit("web route smoke check failed: burning hygiene policy drift")
    event_semantics = payload.get("event_semantics")
    if not isinstance(event_semantics, dict):
        raise SystemExit("web route smoke check failed: burning event semantics missing")
    if event_semantics.get("analysis") != "parsons-event-inclusion":
        raise SystemExit("web route smoke check failed: burning analysis drift")
    if event_semantics.get("typed_replacement") != expected_translation:
        raise SystemExit("web route smoke check failed: burning typed replacement drift")
    if payload.get("dependent_type_translation") != expected_translation:
        raise SystemExit("web route smoke check failed: burning translation drift")
    ast = payload.get("ast")
    if not isinstance(ast, dict) or ast.get("kind") != "forall_time":
        raise SystemExit("web route smoke check failed: burning AST kind drift")
    if ast.get("binders") != [
        {"variable": "x", "type": "Entity"},
        {"variable": "t", "type": "Time"},
    ]:
        raise SystemExit("web route smoke check failed: burning binder drift")
    if ast.get("antecedent") != {
        "predicate": "burn",
        "predicate_type": "Entity -> Time -> Prop",
        "arguments": ["x", "t"],
    }:
        raise SystemExit("web route smoke check failed: burning antecedent drift")
    if ast.get("consequent") != {
        "predicate": "consume",
        "predicate_type": "Entity -> Time -> Prop",
        "arguments": ["oxygen", "t"],
        "theme": {"name": "oxygen", "type": "Entity"},
    }:
        raise SystemExit("web route smoke check failed: burning consequent drift")
    type_check = payload.get("type_check")
    if (
        not isinstance(type_check, dict)
        or type_check.get("ok") is not True
        or type_check.get("type") != "Prop"
    ):
        raise SystemExit("web route smoke check failed: burning type-check drift")
    check = payload.get("semantic_readings_check")
    if (
        not isinstance(check, dict)
        or check.get("ok") is not True
        or check.get("reading_count") != 1
    ):
        raise SystemExit("web route smoke check failed: burning reading-count drift")
    repair = check.get("repair_details")
    if (
        not isinstance(repair, dict)
        or repair.get("expected_coq_definitions") != ["every_burning_consumes_oxygen"]
        or repair.get("exported_definitions") != ["every_burning_consumes_oxygen"]
        or repair.get("observed_export_count") != 1
    ):
        raise SystemExit("web route smoke check failed: burning repair-detail drift")
    readings = payload.get("semantic_readings")
    if not isinstance(readings, list) or len(readings) != 1:
        raise SystemExit("web route smoke check failed: burning semantic reading drift")
    validate_semantic_reading_summary(
        readings[0],
        {
            "name": "universal_timed_burning",
            "scope": "forall_entity_time",
            "source": "universal_timed_burning",
            "dependent_type_translation": expected_translation,
            "coq_definition": "every_burning_consumes_oxygen",
        },
        "none",
        "burning",
    )
    coq_code = payload.get("coq_code")
    if not isinstance(coq_code, str):
        raise SystemExit("web route smoke check failed: burning Coq export missing")
    expected_coq_fragments = [
        "Parameter Time : Type.",
        "Parameter oxygen : Entity.",
        "Parameter burn : Entity -> Time -> Prop.",
        "Parameter consume : Entity -> Time -> Prop.",
        "Definition every_burning_consumes_oxygen : Prop :=",
        "forall x : Entity,",
        "forall t : Time,",
        "burn x t -> consume oxygen t.",
        "Check every_burning_consumes_oxygen.",
    ]
    require_text_fragments(coq_code, expected_coq_fragments, "burning Coq export")
    forbid_text_fragments(
        coq_code,
        ["Parameter Event : Type.", "IN", "Agent", "Theme"],
        "burning event export",
    )
    expected_page_fragments = [
        "universal_timed_burning",
        "parsons-event-inclusion",
        html.escape(expected_translation, quote=True),
        'data-reading-name="universal_timed_burning"',
        'data-coq-definition="every_burning_consumes_oxygen"',
        "<dt>scope</dt><dd>forall_entity_time</dd>",
        "<dt>source</dt><dd>universal_timed_burning</dd>",
        "<dt>attachment</dt><dd>none</dd>",
        "<dt>coq</dt><dd>every_burning_consumes_oxygen</dd>",
    ]
    require_text_fragments(page, expected_page_fragments, "burning HTML")
    validate_successful_semantic_reading_contract(case, payload, page)
    if html.escape(sentence, quote=True) not in page:
        raise SystemExit("web route smoke check failed: burning page input drift")


def validate_diagnostic_fixture_routes(
    manifest: dict,
    fixture_payloads: dict[str, dict],
    fixture_pages: dict[str, str],
) -> None:
    manifest_cases = manifest.get("cases", [])
    if not isinstance(manifest_cases, list) or not manifest_cases:
        raise SystemExit("web route smoke check failed: missing fixture cases")
    fixture_count = len(manifest_cases)
    for fixture in manifest_cases:
        if not isinstance(fixture, dict):
            raise SystemExit("web route smoke check failed: malformed fixture case")
        case = fixture.get("case")
        label = fixture.get("label")
        api_path = fixture.get("api_path")
        html_path = fixture.get("html_path")
        failure_stage = fixture.get("failure_stage")
        recovery_actions = fixture.get("recovery_action_kinds")
        recovery_action_exports = fixture.get("recovery_action_exports")
        if not all(
            isinstance(value, str)
            for value in [case, label, api_path, html_path, failure_stage]
        ):
            raise SystemExit("web route smoke check failed: incomplete fixture case metadata")
        if not isinstance(recovery_actions, list) or not all(
            isinstance(action, str) for action in recovery_actions
        ):
            raise SystemExit("web route smoke check failed: incomplete fixture case metadata")
        if (
            not isinstance(recovery_action_exports, list)
            or len(recovery_action_exports) != len(recovery_actions)
        ):
            raise SystemExit("web route smoke check failed: incomplete fixture case metadata")
        if failure_stage not in VALID_DIAGNOSTIC_FAILURE_STAGES:
            raise SystemExit(f"web route smoke check failed: {case} unknown fixture failure stage")
        for action_index, action_kind in enumerate(recovery_actions):
            validate_recovery_action_export_manifest_entry(
                case,
                action_index,
                failure_stage,
                action_kind,
                recovery_action_exports[action_index],
            )

    if manifest.get("schema_version") != "diagnostic_fixtures.v1":
        raise SystemExit("web route smoke check failed: wrong diagnostic fixture schema")
    if manifest.get("default_case") != "semantic_readings_missing_export":
        raise SystemExit("web route smoke check failed: wrong default fixture case")
    cases = {fixture.get("case"): fixture for fixture in manifest_cases}
    if len(cases) != fixture_count:
        raise SystemExit("web route smoke check failed: duplicate fixture cases")
    covered_stages = {fixture.get("failure_stage") for fixture in manifest_cases}
    missing_stages = sorted(REQUIRED_DIAGNOSTIC_FIXTURE_STAGES - covered_stages)
    if missing_stages:
        raise SystemExit(
            "web route smoke check failed: missing diagnostic fixture stages "
            + ", ".join(missing_stages)
        )
    missing = cases.get("semantic_readings_missing_export")
    if not missing:
        raise SystemExit("web route smoke check failed: missing semantic readings fixture")
    if missing.get("failure_stage") != "semantic_readings_check":
        raise SystemExit("web route smoke check failed: wrong semantic readings failure stage")
    for case, fixture in cases.items():
        validate_fixture_path(
            case,
            fixture.get("api_path", ""),
            "/api/diagnostic-fixture",
            "API",
        )
        validate_fixture_path(
            case,
            fixture.get("html_path", ""),
            "/diagnostic-fixture",
            "HTML",
        )
        expected_label = fixture.get("label")
        expected_stage = fixture.get("failure_stage")
        expected_actions = fixture.get("recovery_action_kinds", [])
        expected_action_exports = fixture.get("recovery_action_exports", [])
        payload = fixture_payloads.get(case, {})
        diagnostics = payload.get("diagnostics", {}) if isinstance(payload, dict) else {}
        if not isinstance(diagnostics, dict):
            raise SystemExit(f"web route smoke check failed: {case} missing diagnostics")
        if diagnostics.get("failure_stage") != expected_stage:
            raise SystemExit(f"web route smoke check failed: {case} stage drift")
        repair_details = diagnostics.get("semantic_readings_repair_details")
        validate_semantic_readings_repair_details(case, repair_details)
        payload_actions = diagnostics.get("recovery_actions", [])
        if not isinstance(payload_actions, list):
            raise SystemExit(f"web route smoke check failed: {case} missing recovery actions")
        for action in payload_actions:
            validate_diagnostic_recovery_action(case, action)
            validate_recovery_action_matches_repair_details(case, action, repair_details)
        observed_actions = [
            action.get("kind")
            for action in payload_actions
            if isinstance(action, dict) and isinstance(action.get("kind"), str)
        ]
        if observed_actions != expected_actions:
            raise SystemExit(f"web route smoke check failed: {case} recovery action drift")
        payload_fixture = payload.get("diagnostic_fixture", {}) if isinstance(payload, dict) else {}
        if not isinstance(payload_fixture, dict) or payload_fixture.get("case") != case:
            raise SystemExit(f"web route smoke check failed: {case} payload case drift")
        fixture_page = fixture_pages.get(case, "")
        validate_successful_semantic_reading_contract(case, payload, fixture_page)
        recovery_action_text = ", ".join(
            str(action) for action in expected_actions if isinstance(action, str)
        )
        inspection_run_count = sum(
            1
            for export in expected_action_exports
            if isinstance(export, dict) and export.get("can_auto_run") is True
        )
        expected_fragments = [
            'class="diagnostic-fixture-form"',
            'action="/diagnostic-fixture"',
            f'data-current-fixture="{case}"',
            'data-fixtures-schema="diagnostic_fixtures.v1"',
            'data-fixtures-api="/api/diagnostic-fixtures"',
            'data-diagnostic-contract-api="/api/diagnostic-contract"',
            f'data-fixture-count="{fixture_count}"',
            f'value="{case}" selected',
            f'data-failure-stage="{expected_stage}"',
            f'data-recovery-action-kinds="{recovery_action_text}"',
            f'data-inspection-run-count="{inspection_run_count}"',
        ]
        expected_selected_option = (
            f'value="{html.escape(case, quote=True)}" selected '
            f'data-failure-stage="{html.escape(str(expected_stage), quote=True)}" '
            f'data-recovery-action-kinds="{html.escape(recovery_action_text, quote=True)}" '
            f'data-inspection-run-count="{inspection_run_count}">'
            f'{html.escape(str(expected_label))}</option>'
        )
        if not isinstance(expected_label, str) or expected_selected_option not in fixture_page:
            raise SystemExit(f"web route smoke check failed: {case} label drift")
        for action_index, action_kind in enumerate(expected_actions):
            export_path = expected_action_exports[action_index].get("api_path", "")
            export_download_path = expected_action_exports[action_index].get(
                "download_api_path",
                "",
            )
            export_download_filename = expected_action_exports[action_index].get(
                "download_filename",
                "",
            )
            inspection_run_path = expected_action_exports[action_index].get(
                "inspection_run_api_path"
            )
            inspection_run_download_path = expected_action_exports[action_index].get(
                "inspection_run_download_api_path"
            )
            inspection_run_download_filename = expected_action_exports[action_index].get(
                "inspection_run_download_filename"
            )
            if action_index < len(payload_actions) and isinstance(
                payload_actions[action_index], dict
            ):
                validate_recovery_action_export_manifest_entry(
                    case,
                    action_index,
                    str(expected_stage),
                    str(action_kind),
                    expected_action_exports[action_index],
                    payload_actions[action_index],
                )
            expected_fragments.extend(
                [
                    f'id="recovery-action-{action_index}"',
                    f'data-action-kind="{action_kind}"',
                    f'data-action-index="{action_index}"',
                    'data-action-contract-api="/api/diagnostic-contract"',
                    f'data-action-contract-kind="{action_kind}"',
                    (
                        'href="'
                        + html.escape(str(export_path), quote=True)
                        + '"'
                    ),
                    'data-action-export="json"',
                ]
            )
            next_step_block = html_list_item_block(
                fixture_page,
                f'id="recovery-action-{action_index}"',
                f"{case} next-step action {action_index}",
            )
            require_html_fragments(
                next_step_block,
                [
                    'class="next-step-action-download-link"',
                    'href="'
                    + html.escape(str(export_download_path), quote=True)
                    + '"',
                    'download="'
                    + html.escape(str(export_download_filename), quote=True)
                    + '"',
                    'data-action-download="json"',
                ],
                f"{case} next-step action download",
            )
            if isinstance(inspection_run_path, str):
                expected_run_json = html.escape(
                    recovery_action_inspection_run_preview_json(
                        case,
                        action_index,
                        str(expected_stage),
                        payload_actions[action_index],
                        payload,
                    )
                )
                require_html_fragments(
                    next_step_block,
                    [
                        'href="'
                        + html.escape(str(inspection_run_path), quote=True)
                        + '"',
                        'class="next-step-inspection-download-link"',
                        'href="'
                        + html.escape(str(inspection_run_download_path), quote=True)
                        + '"',
                        'download="'
                        + html.escape(str(inspection_run_download_filename), quote=True)
                        + '"',
                        'data-inspection-download="json"',
                        'class="next-step-inspection-run-json"',
                        'data-inspection-json-schema="diagnostic_inspection_run.v1"',
                        "<summary>Inspection Run JSON</summary>",
                        expected_run_json,
                    ],
                    f"{case} next-step inspection run preview",
                )
        for fragment in expected_fragments:
            if fragment not in fixture_page:
                raise SystemExit(
                    "web route smoke check failed: diagnostic fixture page missing "
                    f"{fragment} for {case}"
                )
        validate_diagnostic_contract_html_panel(fixture_page)
        validate_recovery_action_exports_html_panel(
            fixture_page,
            case,
            str(expected_stage),
            expected_actions,
            payload_actions,
            expected_action_exports,
            payload,
        )


def validate_diagnostic_contract_manifest(contract: dict) -> None:
    if contract.get("schema_version") != "diagnostic_contract.v1":
        raise SystemExit("web route smoke check failed: wrong diagnostic contract schema")
    if contract.get("failure_stages") != sorted(VALID_DIAGNOSTIC_FAILURE_STAGES):
        raise SystemExit("web route smoke check failed: diagnostic failure-stage drift")
    if contract.get("required_fixture_stages") != sorted(REQUIRED_DIAGNOSTIC_FIXTURE_STAGES):
        raise SystemExit("web route smoke check failed: diagnostic fixture-stage drift")
    if contract.get("recovery_action_kinds") != sorted(
        VALID_DIAGNOSTIC_RECOVERY_ACTION_KINDS
    ):
        raise SystemExit("web route smoke check failed: diagnostic recovery-action drift")
    if contract.get("repair_plan_automation_modes") != sorted(
        VALID_DIAGNOSTIC_REPAIR_PLAN_AUTOMATION_MODES
    ):
        raise SystemExit(
            "web route smoke check failed: diagnostic repair-plan automation drift"
        )
    if contract.get("inspection_only_recovery_action_kinds") != sorted(
        VALID_INSPECTION_ONLY_RECOVERY_ACTION_KINDS
    ):
        raise SystemExit(
            "web route smoke check failed: diagnostic inspection-only action drift"
        )
    if contract.get("semantic_reading_fields") != sorted(
        SEMANTIC_READING_CONTRACT_FIELDS
    ):
        raise SystemExit(
            "web route smoke check failed: diagnostic semantic-reading field drift"
        )


def validate_diagnostic_contract_html_panel(page: str) -> None:
    expected_fields = {
        "failure_stages": sorted(VALID_DIAGNOSTIC_FAILURE_STAGES),
        "required_fixture_stages": sorted(REQUIRED_DIAGNOSTIC_FIXTURE_STAGES),
        "recovery_action_kinds": sorted(VALID_DIAGNOSTIC_RECOVERY_ACTION_KINDS),
        "repair_plan_automation_modes": sorted(
            VALID_DIAGNOSTIC_REPAIR_PLAN_AUTOMATION_MODES
        ),
        "inspection_only_recovery_action_kinds": sorted(
            VALID_INSPECTION_ONLY_RECOVERY_ACTION_KINDS
        ),
        "semantic_reading_fields": sorted(SEMANTIC_READING_CONTRACT_FIELDS),
    }
    expected_fragments = [
        'class="panel diagnostic-contract-panel"',
        'data-contract-schema="diagnostic_contract.v1"',
        'data-contract-api="/api/diagnostic-contract"',
        "<h2>Diagnostic Contract</h2>",
    ]
    for field, values in expected_fields.items():
        expected_fragments.extend(
            [
                f'data-contract-field="{field}"',
                f'data-contract-count="{len(values)}"',
            ]
        )
        expected_fragments.extend(
            f'data-contract-token="{html.escape(value, quote=True)}"'
            for value in values
        )
    for fragment in expected_fragments:
        if fragment not in page:
            raise SystemExit(
                "web route smoke check failed: diagnostic contract panel missing "
                f"{fragment}"
            )


def validate_certified_fragment_manifest(manifest: dict) -> None:
    from translator.natural_language_pipeline import construction_rules

    if manifest.get("schema_version") != "certified_fragment.v1":
        raise SystemExit("web route smoke check failed: wrong certified fragment schema")
    if manifest.get("full_natural_language_certification") is not False:
        raise SystemExit(
            "web route smoke check failed: certified fragment full-NL boundary drift"
        )
    registered = manifest.get("registered_constructions")
    if not isinstance(registered, list) or not registered:
        raise SystemExit("web route smoke check failed: missing certified rules")
    rules = {rule.rule_id: rule for rule in construction_rules()}
    registered_by_id = {
        item.get("id"): item
        for item in registered
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    if set(registered_by_id) != set(rules):
        raise SystemExit("web route smoke check failed: certified rule id drift")
    if manifest.get("registered_construction_count") != len(rules):
        raise SystemExit("web route smoke check failed: certified rule count drift")
    coverage = manifest.get("coverage_matrix")
    counts = manifest.get("coverage_matrix_counts")
    if not isinstance(coverage, dict) or not isinstance(counts, dict):
        raise SystemExit("web route smoke check failed: certified coverage matrix missing")
    registered_cases = coverage.get("registered_success_cases")
    fallback_cases = coverage.get("fallback_success_cases")
    rejected_cases = coverage.get("rejected_unsupported_cases")
    if (
        not isinstance(registered_cases, list)
        or not isinstance(fallback_cases, list)
        or not isinstance(rejected_cases, list)
    ):
        raise SystemExit("web route smoke check failed: certified coverage case drift")
    if counts.get("registered_success_cases") != len(registered_cases):
        raise SystemExit("web route smoke check failed: certified registered coverage count drift")
    if counts.get("fallback_success_cases") != len(fallback_cases):
        raise SystemExit("web route smoke check failed: certified fallback coverage count drift")
    if counts.get("rejected_unsupported_cases") != len(rejected_cases):
        raise SystemExit("web route smoke check failed: certified rejected coverage count drift")
    registered_case_by_id = {
        item.get("rule_id"): item
        for item in registered_cases
        if isinstance(item, dict) and isinstance(item.get("rule_id"), str)
    }
    if set(registered_case_by_id) != set(rules):
        raise SystemExit("web route smoke check failed: certified registered coverage id drift")
    for rule_id, rule in rules.items():
        item = registered_by_id[rule_id]
        if item.get("label") != rule.label or item.get("phenomenon") != rule.phenomenon:
            raise SystemExit(
                f"web route smoke check failed: certified rule {rule_id} metadata drift"
            )
        if item.get("verification_scope_kind") != "registered_construction":
            raise SystemExit(
                f"web route smoke check failed: certified rule {rule_id} scope drift"
            )
        if item.get("certification_level") != "construction_rule":
            raise SystemExit(
                f"web route smoke check failed: certified rule {rule_id} level drift"
            )
        if item.get("forbidden_coq_fragments") != list(rule.forbidden_coq_fragments):
            raise SystemExit(
                f"web route smoke check failed: certified rule {rule_id} hygiene drift"
            )
        if not isinstance(item.get("accepted_examples"), list) or not item.get("example"):
            raise SystemExit(
                f"web route smoke check failed: certified rule {rule_id} example drift"
            )
        case = registered_case_by_id[rule_id]
        if (
            case.get("sentence") != item.get("example")
            or case.get("expected_verification_scope_kind") != "registered_construction"
            or case.get("expected_certification_level") != "construction_rule"
            or case.get("boundary_status") != "registered_primary_example"
        ):
            raise SystemExit(
                f"web route smoke check failed: certified rule {rule_id} coverage drift"
            )
    fallback = manifest.get("fallback")
    if (
        not isinstance(fallback, dict)
        or fallback.get("verification_scope_kind") != "fallback_shallow"
        or fallback.get("certification_level") != "shallow_scaffold"
    ):
        raise SystemExit("web route smoke check failed: certified fallback drift")
    for case in fallback_cases:
        if (
            not isinstance(case, dict)
            or case.get("expected_verification_scope_kind") != "fallback_shallow"
            or case.get("expected_certification_level") != "shallow_scaffold"
            or not isinstance(case.get("sentence"), str)
        ):
            raise SystemExit("web route smoke check failed: certified fallback coverage drift")
    for case in rejected_cases:
        if (
            not isinstance(case, dict)
            or case.get("expected_verification_scope_kind")
            != "rejected_unsupported_fragment"
            or case.get("expected_certification_level") != "none"
            or case.get("marker") not in manifest.get("rejected_fragment_markers", [])
            or not isinstance(case.get("sentence"), str)
        ):
            raise SystemExit("web route smoke check failed: certified rejected coverage drift")
    if "who" not in manifest.get("rejected_fragment_markers", []):
        raise SystemExit("web route smoke check failed: certified marker drift")


def validate_certified_fragment_html_panel(page: str, manifest: dict) -> None:
    registered = [
        item for item in manifest.get("registered_constructions", [])
        if isinstance(item, dict)
    ]
    expected_fragments = [
        'class="panel certified-fragment-panel"',
        'data-certified-fragment-schema="certified_fragment.v1"',
        'data-certified-fragment-api="/api/certified-fragment"',
        'data-full-natural-language-certification="false"',
        'data-fallback-certification-level="shallow_scaffold"',
        f'data-registered-construction-count="{len(registered)}"',
        (
            'data-coverage-registered-success-count="'
            f'{manifest.get("coverage_matrix_counts", {}).get("registered_success_cases")}"'
        ),
        (
            'data-coverage-fallback-success-count="'
            f'{manifest.get("coverage_matrix_counts", {}).get("fallback_success_cases")}"'
        ),
        (
            'data-coverage-rejected-unsupported-count="'
            f'{manifest.get("coverage_matrix_counts", {}).get("rejected_unsupported_cases")}"'
        ),
        "<h2>Certified Fragment</h2>",
    ]
    expected_fragments.extend(
        f'data-certified-rule-id="{html.escape(str(item.get("id", "")), quote=True)}"'
        for item in registered
    )
    expected_fragments.extend(
        f'data-certified-example="{html.escape(str(item.get("example", "")), quote=True)}"'
        for item in registered
    )
    coverage = manifest.get("coverage_matrix", {})
    if isinstance(coverage, dict):
        expected_fragments.extend(
            f'data-coverage-marker="{html.escape(str(item.get("marker", "")), quote=True)}"'
            for item in coverage.get("rejected_unsupported_cases", [])
            if isinstance(item, dict)
        )
    for fragment in expected_fragments:
        if fragment not in page:
            raise SystemExit(
                "web route smoke check failed: certified fragment panel missing "
                f"{fragment}"
            )


def validate_recovery_action_exports_html_panel(
    page: str,
    case: str,
    expected_stage: str,
    expected_actions: list[str],
    expected_action_payloads: list[dict],
    expected_action_exports: list[dict],
    fixture_payload: dict,
) -> None:
    require_html_fragments(
        page,
        [
            'class="panel recovery-action-exports-panel"',
            'data-export-schema="diagnostic_recovery_action.v1"',
            f'data-export-case="{html.escape(case, quote=True)}"',
            f'data-export-count="{len(expected_actions)}"',
            "<h2>Recovery Action Exports</h2>",
        ],
        f"{case} recovery action exports panel",
    )
    for action_index, action_kind in enumerate(expected_actions):
        if action_index >= len(expected_action_payloads) or not isinstance(
            expected_action_payloads[action_index],
            dict,
        ):
            raise SystemExit(
                "web route smoke check failed: recovery action exports panel missing "
                f"payload for {case} action {action_index}"
            )
        row = html_list_item_block(
            page,
            f'data-export-action-index="{action_index}"',
            f"{case} recovery action export row {action_index}",
        )
        expected_json = html.escape(
            recovery_action_export_preview_json(
                case,
                action_index,
                expected_stage,
                expected_action_payloads[action_index],
            )
        )
        expected_plan = recovery_action_repair_plan_preview(
            case,
            action_index,
            expected_stage,
            expected_action_payloads[action_index],
        )
        automation_mode = str(expected_plan.get("automation_mode", ""))
        can_auto_run = expected_plan.get("can_auto_run") is True
        export_path = expected_action_exports[action_index].get("api_path", "")
        export_download_path = expected_action_exports[action_index].get(
            "download_api_path",
            "",
        )
        export_download_filename = expected_action_exports[action_index].get(
            "download_filename",
            "",
        )
        run_path = "/api/recovery-action-run?" + urlencode(
            {"case": case, "index": str(action_index)}
        )
        expected_fragments = [
            'class="recovery-action-export"',
            f'data-export-action-index="{action_index}"',
            f'data-export-action-kind="{html.escape(action_kind, quote=True)}"',
            (
                'data-export-automation-mode="'
                + html.escape(automation_mode, quote=True)
                + '"'
            ),
            f'data-export-can-auto-run="{str(can_auto_run).lower()}"',
            f'data-export-failure-stage="{html.escape(expected_stage, quote=True)}"',
            f'data-export-json-schema="diagnostic_recovery_action.v1"',
            "<summary>Action JSON</summary>",
            (
                'href="'
                + html.escape(str(export_path), quote=True)
                + '"'
            ),
            expected_json,
            'class="recovery-action-download-link"',
            'href="'
            + html.escape(str(export_download_path), quote=True)
            + '"',
            'download="'
            + html.escape(str(export_download_filename), quote=True)
            + '"',
            'data-action-download="json"',
        ]
        if can_auto_run:
            run_download_path = expected_action_exports[action_index].get(
                "inspection_run_download_api_path",
                "",
            )
            run_download_filename = expected_action_exports[action_index].get(
                "inspection_run_download_filename",
                "",
            )
            expected_run_json = html.escape(
                recovery_action_inspection_run_preview_json(
                    case,
                    action_index,
                    expected_stage,
                    expected_action_payloads[action_index],
                    fixture_payload,
                )
            )
            expected_fragments.extend(
                [
                    'class="recovery-action-run-link"',
                    'data-action-run="inspection"',
                    'href="' + html.escape(run_path, quote=True) + '"',
                    'class="recovery-action-inspection-download-link"',
                    'href="' + html.escape(str(run_download_path), quote=True) + '"',
                    'download="'
                    + html.escape(str(run_download_filename), quote=True)
                    + '"',
                    'data-inspection-download="json"',
                    'class="recovery-action-inspection-run-json"',
                    'data-inspection-json-schema="diagnostic_inspection_run.v1"',
                    "<summary>Inspection Run JSON</summary>",
                    expected_run_json,
                ]
            )
        require_html_fragments(
            row,
            expected_fragments,
            f"{case} recovery action export row {action_index}",
        )


def validate_lexicon_patch_http_routes(port: int, opener) -> None:
    for contract_case in LEXICON_PATCH_CONTRACT_CASES:
        case = f"{contract_case.name}_bundle"
        query = contract_case.query(require_coq=True)
        expected_bundle = contract_case.expected_bundle(require_coq=True)
        with opener.open(
            f"http://127.0.0.1:{port}/api/lexicon-patch-drafts?{query}",
            timeout=5,
        ) as response:
            raw = response.read()
            if response.status != 200:
                raise SystemExit(f"web route smoke check failed: {case} JSON status drift")
            if response.headers.get_content_type() != "application/json":
                raise SystemExit(f"web route smoke check failed: {case} JSON content type drift")
            if "charset=utf-8" not in response.headers.get("Content-Type", ""):
                raise SystemExit(f"web route smoke check failed: {case} JSON charset drift")
            if response.headers.get("Content-Length") != str(len(raw)):
                raise SystemExit(f"web route smoke check failed: {case} JSON length drift")
        observed_bundle = json.loads(raw.decode("utf-8"))
        if observed_bundle != expected_bundle:
            raise SystemExit(f"web route smoke check failed: {case} JSON bundle drift")
        validate_lexicon_patch_bundle(case, observed_bundle)
        contract_errors = contract_case.validation_errors_for(observed_bundle)
        if contract_errors:
            raise SystemExit(
                "web route smoke check failed: "
                f"{case} validation-error contract drift: {'; '.join(contract_errors)}"
            )

        with opener.open(
            f"http://127.0.0.1:{port}/api/lexicon-patch-drafts?{query}&format=patch",
            timeout=5,
        ) as response:
            raw = response.read()
            if response.status != 200:
                raise SystemExit(f"web route smoke check failed: {case} patch status drift")
            if response.headers.get_content_type() != "text/plain":
                raise SystemExit(f"web route smoke check failed: {case} patch content type drift")
            if "charset=utf-8" not in response.headers.get("Content-Type", ""):
                raise SystemExit(f"web route smoke check failed: {case} patch charset drift")
            if response.headers.get("Content-Length") != str(len(raw)):
                raise SystemExit(f"web route smoke check failed: {case} patch length drift")
        observed_patch = raw.decode("utf-8")
        if observed_patch != observed_bundle.get("patch_text_preview"):
            raise SystemExit(f"web route smoke check failed: {case} patch preview drift")

    unknown_format_url = (
        f"http://127.0.0.1:{port}/api/lexicon-patch-drafts?"
        + urlencode(
            {
                "sentence": "Mary painted the door red",
                "require_coq": "1",
                "format": "zip",
            }
        )
    )
    try:
        opener.open(unknown_format_url, timeout=5)
    except HTTPError as exc:
        raw = exc.read()
        if exc.code != 400:
            raise SystemExit("web route smoke check failed: unknown format status drift")
        if exc.headers.get_content_type() != "application/json":
            raise SystemExit("web route smoke check failed: unknown format content type drift")
        if exc.headers.get("Content-Length") != str(len(raw)):
            raise SystemExit("web route smoke check failed: unknown format length drift")
        payload = json.loads(raw.decode("utf-8"))
    else:
        raise SystemExit("web route smoke check failed: unknown format was accepted")
    if payload.get("schema_version") != "lexicon_patch_drafts.v1":
        raise SystemExit("web route smoke check failed: unknown format schema drift")
    if payload.get("ok") is not False:
        raise SystemExit("web route smoke check failed: unknown format ok drift")
    if payload.get("allowed_formats") != ["json", "patch"]:
        raise SystemExit("web route smoke check failed: unknown format allowed formats drift")
    if "Unsupported lexicon patch response format" not in str(payload.get("error", "")):
        raise SystemExit("web route smoke check failed: unknown format error drift")


def validate_json_download_http_response(
    case: str,
    label: str,
    response,
    expected_payload: dict,
    expected_filename: object,
) -> None:
    raw = response.read()
    if response.status != 200:
        raise SystemExit(
            f"web route smoke check failed: {case} {label} download status drift"
        )
    if response.headers.get_content_type() != "application/json":
        raise SystemExit(
            f"web route smoke check failed: {case} {label} download content type drift"
        )
    if response.headers.get("Content-Length") != str(len(raw)):
        raise SystemExit(
            f"web route smoke check failed: {case} {label} download length drift"
        )
    expected_disposition = f'attachment; filename="{expected_filename}"'
    if response.headers.get("Content-Disposition") != expected_disposition:
        raise SystemExit(
            f"web route smoke check failed: {case} {label} download filename drift"
        )
    observed_payload = json.loads(raw.decode("utf-8"))
    if observed_payload != expected_payload:
        raise SystemExit(
            f"web route smoke check failed: {case} {label} download payload drift"
        )


def run_web_route_smoke_check() -> None:
    from web.app import PipelineHandler

    print("==> web route smoke check")
    server = ThreadingHTTPServer(("127.0.0.1", 0), PipelineHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        base_url = f"http://127.0.0.1:{port}"
        opener = build_opener(ProxyHandler({}))
        fallback_sentence = "John knocked twice"
        fallback_query = urlencode({"sentence": fallback_sentence, "require_coq": "1"})
        with opener.open(f"{base_url}/api/analyze?{fallback_query}", timeout=5) as response:
            fallback_payload = json.load(response)
        with opener.open(f"{base_url}/?{fallback_query}", timeout=5) as response:
            fallback_page = response.read().decode("utf-8")
        validate_analyze_fallback_success(
            fallback_payload,
            fallback_page,
            fallback_sentence,
        )
        quantifier_sentence = "some boy loves some girl"
        quantifier_query = urlencode({"sentence": quantifier_sentence, "require_coq": "1"})
        with opener.open(f"{base_url}/api/analyze?{quantifier_query}", timeout=5) as response:
            quantifier_payload = json.load(response)
        with opener.open(f"{base_url}/?{quantifier_query}", timeout=5) as response:
            quantifier_page = response.read().decode("utf-8")
        validate_analyze_quantifier_scope_success(
            quantifier_payload,
            quantifier_page,
            quantifier_sentence,
        )
        perception_sentence = "Mary saw John leave"
        perception_query = urlencode({"sentence": perception_sentence, "require_coq": "1"})
        with opener.open(f"{base_url}/api/analyze?{perception_query}", timeout=5) as response:
            perception_payload = json.load(response)
        with opener.open(f"{base_url}/?{perception_query}", timeout=5) as response:
            perception_page = response.read().decode("utf-8")
        validate_analyze_perception_success(
            perception_payload,
            perception_page,
            perception_sentence,
        )
        timed_after_sentence = "after the singing of the Marseillaise, John saluted the flag"
        timed_after_query = urlencode({"sentence": timed_after_sentence, "require_coq": "1"})
        with opener.open(f"{base_url}/api/analyze?{timed_after_query}", timeout=5) as response:
            timed_after_payload = json.load(response)
        with opener.open(f"{base_url}/?{timed_after_query}", timeout=5) as response:
            timed_after_page = response.read().decode("utf-8")
        validate_analyze_timed_after_success(
            timed_after_payload,
            timed_after_page,
            timed_after_sentence,
        )
        burning_sentence = "In every burning, oxygen is consumed"
        burning_query = urlencode({"sentence": burning_sentence, "require_coq": "1"})
        with opener.open(f"{base_url}/api/analyze?{burning_query}", timeout=5) as response:
            burning_payload = json.load(response)
        with opener.open(f"{base_url}/?{burning_query}", timeout=5) as response:
            burning_page = response.read().decode("utf-8")
        validate_analyze_universal_timed_burning_success(
            burning_payload,
            burning_page,
            burning_sentence,
        )
        with opener.open(f"{base_url}/api/diagnostic-contract", timeout=5) as response:
            validate_diagnostic_contract_manifest(json.load(response))
        with opener.open(f"{base_url}/api/certified-fragment", timeout=5) as response:
            certified_fragment_manifest = json.load(response)
        validate_certified_fragment_manifest(certified_fragment_manifest)
        validate_certified_fragment_html_panel(
            fallback_page,
            certified_fragment_manifest,
        )
        with opener.open(f"{base_url}/api/diagnostic-fixtures", timeout=5) as response:
            manifest = json.load(response)
        manifest_cases = manifest.get("cases", [])
        if not isinstance(manifest_cases, list):
            raise SystemExit("web route smoke check failed: missing fixture cases")
        fixture_payloads = {}
        fixture_pages = {}
        for fixture in manifest_cases:
            if not isinstance(fixture, dict):
                raise SystemExit("web route smoke check failed: malformed fixture case")
            case = fixture.get("case")
            api_path = fixture.get("api_path")
            html_path = fixture.get("html_path")
            if not all(isinstance(value, str) for value in [case, api_path, html_path]):
                raise SystemExit("web route smoke check failed: incomplete fixture case metadata")
            with opener.open(f"{base_url}{api_path}", timeout=5) as response:
                fixture_payloads[case] = json.load(response)
            actions = fixture_payloads[case].get("diagnostics", {}).get("recovery_actions", [])
            if not isinstance(actions, list):
                raise SystemExit(f"web route smoke check failed: {case} missing recovery actions")
            action_exports = fixture.get("recovery_action_exports", [])
            if not isinstance(action_exports, list):
                raise SystemExit(
                    f"web route smoke check failed: {case} missing recovery action exports"
                )
            for action_index, action in enumerate(actions):
                if action_index >= len(action_exports) or not isinstance(
                    action_exports[action_index],
                    dict,
                ):
                    raise SystemExit(
                        "web route smoke check failed: "
                        f"{case} missing recovery action export metadata"
                    )
                action_export = action_exports[action_index]
                query = urlencode({"case": case, "index": str(action_index)})
                with opener.open(
                    f"{base_url}/api/recovery-action?{query}",
                    timeout=5,
                ) as response:
                    action_bundle = json.load(response)
                    validate_recovery_action_export_bundle(
                        case,
                        action_index,
                        action,
                        action_bundle,
                    )
                download_path = action_export.get("download_api_path")
                if not isinstance(download_path, str):
                    raise SystemExit(
                        "web route smoke check failed: "
                        f"{case} missing recovery action download metadata"
                    )
                with opener.open(
                    f"{base_url}{download_path}",
                    timeout=5,
                ) as response:
                    validate_json_download_http_response(
                        str(case),
                        "recovery action",
                        response,
                        action_bundle,
                        action_export.get("download_filename"),
                    )
                run_url = f"{base_url}/api/recovery-action-run?{query}"
                if action_bundle.get("repair_plan", {}).get("can_auto_run") is True:
                    with opener.open(run_url, timeout=5) as response:
                        run_payload = json.load(response)
                        validate_recovery_action_inspection_run_bundle(
                            case,
                            action_index,
                            action_bundle,
                            fixture_payloads[case],
                            run_payload,
                        )
                    run_download_path = action_export.get(
                        "inspection_run_download_api_path"
                    )
                    if not isinstance(run_download_path, str):
                        raise SystemExit(
                            "web route smoke check failed: "
                            f"{case} missing recovery action run download metadata"
                        )
                    with opener.open(
                        f"{base_url}{run_download_path}",
                        timeout=5,
                    ) as response:
                        validate_json_download_http_response(
                            str(case),
                            "recovery action run",
                            response,
                            run_payload,
                            action_export.get("inspection_run_download_filename"),
                        )
                else:
                    try:
                        opener.open(run_url, timeout=5)
                    except HTTPError as error:
                        if error.code != 400:
                            raise SystemExit(
                                "web route smoke check failed: "
                                f"{case} inspection rejection status drift"
                            ) from error
                        validate_recovery_action_inspection_run_rejection(
                            case,
                            action_index,
                            action_bundle,
                            json.loads(error.read().decode("utf-8")),
                        )
                    else:
                        raise SystemExit(
                            "web route smoke check failed: "
                            f"{case} inspection run accepted human-review action"
                        )
            with opener.open(f"{base_url}{html_path}", timeout=5) as response:
                fixture_pages[case] = response.read().decode("utf-8")
        validate_lexicon_patch_http_routes(port, opener)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    validate_diagnostic_fixture_routes(manifest, fixture_payloads, fixture_pages)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run translator, scaffold, and optional proof-assistant checks."
    )
    coq_group = parser.add_mutually_exclusive_group()
    coq_group.add_argument(
        "--skip-coq",
        action="store_true",
        help="Skip the optional Coq/Rocq scaffold boundary check.",
    )
    coq_group.add_argument(
        "--require-coq",
        action="store_true",
        help="Fail if the Coq/Rocq scaffold boundary check cannot be run.",
    )
    parser.add_argument(
        "--require-docx",
        action="store_true",
        help="Fail if python-docx is unavailable, so Word-generation tests cannot be skipped.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    check_python_docx_requirement(args.require_docx)
    run("unit tests", [sys.executable, "-m", "unittest", "discover", "-v"])
    run(
        "python compile check",
        [
            sys.executable,
            "-X",
            f"pycache_prefix={PYCACHE}",
            "-m",
            "py_compile",
            "translator/dependent_type_event_translator.py",
            "translator/natural_language_pipeline.py",
            "tests/test_paper_docx.py",
            "tests/test_translator.py",
            "scripts/generate_formalization.py",
            "scripts/check_formalization.py",
            "scripts/paper_markdown.py",
            "scripts/check_paper_docx_sync.py",
            "scripts/export_lexicon_patch_drafts.py",
            "scripts/sync_paper_docx.py",
            "scripts/verify_project.py",
            "web/app.py",
        ],
    )
    run_package_build_smoke_check()
    run("formalization consistency", [sys.executable, "scripts/check_formalization.py"])
    run("paper DOCX sync", [sys.executable, "scripts/check_paper_docx_sync.py"])
    run_lexicon_export_smoke_check()
    run_lexicon_warning_schema_check()
    run_web_route_smoke_check()
    if args.skip_coq:
        print("==> Coq scaffold boundary check skipped by --skip-coq")
    else:
        run_optional_coq_check(args.require_coq)
    print("all deterministic checks passed")


if __name__ == "__main__":
    main()
