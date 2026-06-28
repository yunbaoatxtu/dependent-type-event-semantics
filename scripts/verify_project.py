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
from collections import Counter
from http.server import ThreadingHTTPServer
from urllib.parse import parse_qs, urlencode, urlparse
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import ProxyHandler, build_opener

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.lexicon_patch_contract_cases import LEXICON_PATCH_CONTRACT_CASES  # noqa: E402
from translator.surface_type_contracts import (  # noqa: E402
    modified_transitive_surface_type_contract_registry,
    surface_type_contract_diagnostic_report,
)
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


def construction_rule_draft_artifact_filename(candidate_rule_id: str) -> str:
    return f"construction_rule_draft__{artifact_token(candidate_rule_id)}.json"


def recovery_action_artifact_filename(case: str, action_index: int) -> str:
    return f"diagnostic_recovery_action__{artifact_token(case)}__{action_index}.json"


def recovery_action_run_artifact_filename(case: str, action_index: int) -> str:
    return f"diagnostic_inspection_run__{artifact_token(case)}__{action_index}.json"


def analyze_action_artifact_filename(sentence: str, action_index: int) -> str:
    token = artifact_token(sentence.strip() or "empty-input")
    return f"analyze_recovery_action__{token}__{action_index}.json"


def analyze_action_run_artifact_filename(sentence: str, action_index: int) -> str:
    token = artifact_token(sentence.strip() or "empty-input")
    return f"analyze_inspection_run__{token}__{action_index}.json"


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


def analyze_action_api_path(
    sentence: str,
    action_index: int,
    *,
    require_coq: bool = False,
    download: bool = False,
) -> str:
    params = {"sentence": sentence, "index": str(action_index)}
    if require_coq:
        params["require_coq"] = "1"
    if download:
        params["download"] = "1"
    return f"/api/analyze-action?{urlencode(params)}"


def analyze_action_run_api_path(
    sentence: str,
    action_index: int,
    *,
    require_coq: bool = False,
    download: bool = False,
) -> str:
    params = {"sentence": sentence, "index": str(action_index)}
    if require_coq:
        params["require_coq"] = "1"
    if download:
        params["download"] = "1"
    return f"/api/analyze-action-run?{urlencode(params)}"


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


def validate_state_opposition_diagnostic(
    case: str,
    diagnostic: object,
    *,
    context: str,
) -> None:
    if not isinstance(diagnostic, dict):
        raise SystemExit(
            "web route smoke check failed: "
            f"{case} malformed state opposition diagnostic"
        )
    required_fields = [
        "state_scale",
        "left_state",
        "right_state",
        "states",
        "relation",
        "source",
    ]
    missing_fields = [field for field in required_fields if field not in diagnostic]
    if missing_fields:
        raise SystemExit(
            "web route smoke check failed: "
            f"{case} incomplete state opposition diagnostic"
        )
    for field in required_fields:
        if not nonempty_string(diagnostic.get(field)):
            raise SystemExit(
                "web route smoke check failed: "
                f"{case} invalid state opposition diagnostic {context}.{field}"
            )
    for field in ["clause", "path"]:
        if field in diagnostic and not nonempty_string(diagnostic.get(field)):
            raise SystemExit(
                "web route smoke check failed: "
                f"{case} invalid state opposition diagnostic {context}.{field}"
            )


def validate_reading_type_check_diagnostics(
    case: str,
    diagnostics: object,
    *,
    expected_count: object | None = None,
) -> None:
    if not isinstance(diagnostics, list):
        raise SystemExit(
            "web route smoke check failed: "
            f"{case} malformed reading type-check diagnostics"
        )
    if expected_count is not None:
        if type(expected_count) is not int:
            raise SystemExit(
                "web route smoke check failed: "
                f"{case} invalid reading type-check diagnostic count"
            )
        if expected_count != len(diagnostics):
            raise SystemExit(
                "web route smoke check failed: "
                f"{case} reading type-check diagnostic count drift"
            )
    required_fields = [
        "reading_index",
        "reading_name",
        "source",
        "scope",
        "coq_definition",
        "path",
        "error_count",
        "errors",
        "state_opposition_count",
        "state_opposition_diagnostics",
    ]
    for index, diagnostic in enumerate(diagnostics):
        if not isinstance(diagnostic, dict):
            raise SystemExit(
                "web route smoke check failed: "
                f"{case} malformed reading type-check diagnostic"
            )
        missing_fields = [
            field for field in required_fields if field not in diagnostic
        ]
        if missing_fields:
            raise SystemExit(
                "web route smoke check failed: "
                f"{case} incomplete reading type-check diagnostic"
            )
        reading_index = diagnostic.get("reading_index")
        if type(reading_index) is not int or reading_index < 0:
            raise SystemExit(
                "web route smoke check failed: "
                f"{case} invalid reading type-check diagnostic reading_index"
            )
        for field in ["reading_name", "source", "scope", "coq_definition", "path"]:
            if not nonempty_string(diagnostic.get(field)):
                raise SystemExit(
                    "web route smoke check failed: "
                    f"{case} invalid reading type-check diagnostic {field}"
                )
        expected_path = f"semantic_readings[{reading_index}].type_check"
        if diagnostic.get("path") != expected_path:
            raise SystemExit(
                "web route smoke check failed: "
                f"{case} reading type-check diagnostic path drift"
            )
        errors = diagnostic.get("errors")
        if not nonempty_string_list(errors):
            raise SystemExit(
                "web route smoke check failed: "
                f"{case} invalid reading type-check diagnostic errors"
            )
        if diagnostic.get("error_count") != len(errors):
            raise SystemExit(
                "web route smoke check failed: "
                f"{case} reading type-check diagnostic error count drift"
            )
        state_diagnostics = diagnostic.get("state_opposition_diagnostics")
        if not isinstance(state_diagnostics, list):
            raise SystemExit(
                "web route smoke check failed: "
                f"{case} invalid reading type-check diagnostic state oppositions"
            )
        if diagnostic.get("state_opposition_count") != len(state_diagnostics):
            raise SystemExit(
                "web route smoke check failed: "
                f"{case} reading type-check diagnostic state opposition count drift"
            )
        for state_index, state_diagnostic in enumerate(state_diagnostics):
            validate_state_opposition_diagnostic(
                case,
                state_diagnostic,
                context=f"reading_type_check_diagnostics[{index}]"
                f".state_opposition_diagnostics[{state_index}]",
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


def validate_reading_type_check_recovery_alignment(
    case: str,
    diagnostics: object,
) -> None:
    if not isinstance(diagnostics, dict):
        raise SystemExit(f"web route smoke check failed: {case} diagnostics missing")
    reading_diagnostics = diagnostics.get("reading_type_check_diagnostics")
    validate_reading_type_check_diagnostics(
        case,
        reading_diagnostics,
        expected_count=diagnostics.get("reading_type_check_failure_count"),
    )
    assert isinstance(reading_diagnostics, list)
    diagnostic_indices = [
        diagnostic.get("reading_index")
        for diagnostic in reading_diagnostics
        if isinstance(diagnostic, dict)
    ]
    repair_details = diagnostics.get("semantic_readings_repair_details", {})
    if not isinstance(repair_details, dict):
        raise SystemExit(
            "web route smoke check failed: "
            f"{case} malformed semantic readings repair details"
        )
    failed_indices = repair_details.get("failed_type_check_indices", [])
    if not integer_list(failed_indices):
        raise SystemExit(
            "web route smoke check failed: "
            f"{case} invalid semantic readings repair details failed_type_check_indices"
        )
    if failed_indices != diagnostic_indices:
        raise SystemExit(
            "web route smoke check failed: "
            f"{case} reading type-check diagnostic repair-detail drift"
        )
    failure_kinds = diagnostics.get("semantic_readings_failure_kinds", [])
    if not isinstance(failure_kinds, list):
        raise SystemExit(
            "web route smoke check failed: "
            f"{case} reading type-check diagnostic failure-kind drift"
        )
    has_failure_kind = "reading_type_check_failed" in failure_kinds
    if bool(diagnostic_indices) is not has_failure_kind:
        raise SystemExit(
            "web route smoke check failed: "
            f"{case} reading type-check diagnostic failure-kind drift"
        )
    actions = diagnostics.get("recovery_actions")
    if not isinstance(actions, list):
        raise SystemExit(f"web route smoke check failed: {case} missing recovery actions")
    fix_actions = [
        action
        for action in actions
        if isinstance(action, dict) and action.get("kind") == "fix_reading_type_checks"
    ]
    if diagnostic_indices and len(fix_actions) != 1:
        raise SystemExit(
            "web route smoke check failed: "
            f"{case} reading type-check recovery action drift"
        )
    if not diagnostic_indices and fix_actions:
        raise SystemExit(
            "web route smoke check failed: "
            f"{case} reading type-check recovery action drift"
        )
    if not fix_actions:
        return
    action = fix_actions[0]
    if action.get("reading_indices") != diagnostic_indices:
        raise SystemExit(
            "web route smoke check failed: "
            f"{case} reading type-check recovery action index drift"
        )
    target_fields = action.get("target_fields")
    if isinstance(target_fields, list) and "semantic_readings.type_check" not in target_fields:
        raise SystemExit(
            "web route smoke check failed: "
            f"{case} reading type-check recovery action target drift"
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
    validate_surface_type_contract_diagnostics_context(
        case,
        bundle.get("surface_type_contract_diagnostics"),
    )


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


def validate_analyze_action_inspection_run_bundle(
    label: str,
    sentence: str,
    action_index: int,
    analyze_payload: dict,
    run_bundle: dict,
) -> None:
    diagnostics = analyze_payload.get("diagnostics")
    if not isinstance(diagnostics, dict):
        raise SystemExit(f"web route smoke check failed: {label} analyze diagnostics drift")
    actions = diagnostics.get("recovery_actions")
    if not isinstance(actions, list) or action_index >= len(actions):
        raise SystemExit(f"web route smoke check failed: {label} analyze action drift")
    expected_action = actions[action_index]
    if not isinstance(expected_action, dict):
        raise SystemExit(f"web route smoke check failed: {label} analyze action shape drift")
    expected_repair_plan = recovery_action_repair_plan_preview(
        "ordinary_analyze_failure",
        action_index,
        str(diagnostics.get("failure_stage") or ""),
        expected_action,
    )
    expected_repair_plan["source"] = "analyze"
    expected_repair_plan["input_sentence"] = sentence
    if run_bundle.get("schema_version") != "diagnostic_inspection_run.v1":
        raise SystemExit(f"web route smoke check failed: {label} analyze run schema drift")
    if run_bundle.get("ok") is not True:
        raise SystemExit(f"web route smoke check failed: {label} analyze run ok drift")
    if run_bundle.get("source") != "analyze":
        raise SystemExit(f"web route smoke check failed: {label} analyze run source drift")
    if run_bundle.get("input_sentence") != sentence:
        raise SystemExit(f"web route smoke check failed: {label} analyze run input drift")
    if run_bundle.get("action_index") != action_index:
        raise SystemExit(f"web route smoke check failed: {label} analyze run index drift")
    if run_bundle.get("action_kind") != expected_action.get("kind"):
        raise SystemExit(f"web route smoke check failed: {label} analyze run kind drift")
    if run_bundle.get("failure_stage") != diagnostics.get("failure_stage"):
        raise SystemExit(f"web route smoke check failed: {label} analyze run stage drift")
    if run_bundle.get("automation_mode") != expected_repair_plan.get("automation_mode"):
        raise SystemExit(f"web route smoke check failed: {label} analyze run mode drift")
    if run_bundle.get("can_auto_run") is not True:
        raise SystemExit(f"web route smoke check failed: {label} analyze run auto-run drift")
    if run_bundle.get("can_auto_apply") is not False:
        raise SystemExit(f"web route smoke check failed: {label} analyze run apply drift")
    if run_bundle.get("target_fields") != expected_repair_plan.get("target_fields"):
        raise SystemExit(f"web route smoke check failed: {label} analyze run field drift")
    inspection_results = run_bundle.get("inspection_results")
    if not isinstance(inspection_results, dict):
        raise SystemExit(f"web route smoke check failed: {label} analyze run result drift")
    for field in expected_repair_plan.get("target_fields", []):
        if inspection_results.get(field) != nested_field_value(analyze_payload, field):
            raise SystemExit(
                "web route smoke check failed: "
                f"{label} analyze run {field} value drift"
            )
    if run_bundle.get("repair_plan") != expected_repair_plan:
        raise SystemExit(f"web route smoke check failed: {label} analyze run plan drift")
    if run_bundle.get("diagnostics") != diagnostics:
        raise SystemExit(f"web route smoke check failed: {label} analyze run diagnostics drift")
    validate_reading_type_check_recovery_alignment(
        label,
        run_bundle.get("diagnostics"),
    )
    contract = run_bundle.get("contract")
    if not isinstance(contract, dict):
        raise SystemExit(f"web route smoke check failed: {label} analyze run contract drift")
    validate_diagnostic_contract_manifest(contract)
    validate_surface_type_contract_diagnostics_context(
        label,
        run_bundle.get("surface_type_contract_diagnostics"),
    )


def validate_analyze_action_inspection_run_rejection(
    label: str,
    sentence: str,
    action_index: int,
    analyze_payload: dict,
    run_bundle: dict,
) -> None:
    diagnostics = analyze_payload.get("diagnostics")
    if not isinstance(diagnostics, dict):
        raise SystemExit(f"web route smoke check failed: {label} analyze diagnostics drift")
    actions = diagnostics.get("recovery_actions")
    if not isinstance(actions, list) or action_index >= len(actions):
        raise SystemExit(f"web route smoke check failed: {label} analyze action drift")
    expected_action = actions[action_index]
    if not isinstance(expected_action, dict):
        raise SystemExit(f"web route smoke check failed: {label} analyze action shape drift")
    expected_repair_plan = recovery_action_repair_plan_preview(
        "ordinary_analyze_failure",
        action_index,
        str(diagnostics.get("failure_stage") or ""),
        expected_action,
    )
    expected_repair_plan["source"] = "analyze"
    expected_repair_plan["input_sentence"] = sentence
    if run_bundle.get("schema_version") != "diagnostic_inspection_run.v1":
        raise SystemExit(f"web route smoke check failed: {label} analyze run rejection schema drift")
    if run_bundle.get("ok") is not False:
        raise SystemExit(f"web route smoke check failed: {label} analyze run rejection ok drift")
    if run_bundle.get("source") != "analyze":
        raise SystemExit(f"web route smoke check failed: {label} analyze run rejection source drift")
    if run_bundle.get("input_sentence") != sentence:
        raise SystemExit(f"web route smoke check failed: {label} analyze run rejection input drift")
    if run_bundle.get("action_index") != action_index:
        raise SystemExit(f"web route smoke check failed: {label} analyze run rejection index drift")
    if run_bundle.get("action_kind") != expected_action.get("kind"):
        raise SystemExit(f"web route smoke check failed: {label} analyze run rejection kind drift")
    if run_bundle.get("failure_stage") != diagnostics.get("failure_stage"):
        raise SystemExit(f"web route smoke check failed: {label} analyze run rejection stage drift")
    if run_bundle.get("automation_mode") != expected_repair_plan.get("automation_mode"):
        raise SystemExit(f"web route smoke check failed: {label} analyze run rejection mode drift")
    if run_bundle.get("can_auto_run") is not False:
        raise SystemExit(f"web route smoke check failed: {label} analyze run rejection run drift")
    if run_bundle.get("can_auto_apply") is not False:
        raise SystemExit(f"web route smoke check failed: {label} analyze run rejection apply drift")
    if "requires human review" not in str(run_bundle.get("error", "")):
        raise SystemExit(f"web route smoke check failed: {label} analyze run rejection error drift")
    if run_bundle.get("repair_plan") != expected_repair_plan:
        raise SystemExit(f"web route smoke check failed: {label} analyze run rejection plan drift")
    if run_bundle.get("diagnostics") != diagnostics:
        raise SystemExit(f"web route smoke check failed: {label} analyze run rejection diagnostics drift")
    validate_reading_type_check_recovery_alignment(
        label,
        run_bundle.get("diagnostics"),
    )
    contract = run_bundle.get("contract")
    if not isinstance(contract, dict):
        raise SystemExit(f"web route smoke check failed: {label} analyze run rejection contract drift")
    validate_diagnostic_contract_manifest(contract)
    validate_surface_type_contract_diagnostics_context(
        label,
        run_bundle.get("surface_type_contract_diagnostics"),
    )


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


def surface_type_contract_diagnostics_context_preview() -> dict:
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


def surface_type_contract_diagnostic_category_text(context: dict) -> str:
    category_ids = context.get("category_ids")
    if not isinstance(category_ids, list):
        return ""
    return ",".join(
        str(category_id)
        for category_id in category_ids
        if isinstance(category_id, str)
    )


def validate_surface_type_contract_diagnostics_context(
    case: str,
    context: object,
) -> None:
    if context != surface_type_contract_diagnostics_context_preview():
        raise SystemExit(
            "web route smoke check failed: "
            f"{case} surface type contract diagnostic drift"
        )


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
            "surface_type_contract_diagnostics": (
                surface_type_contract_diagnostics_context_preview()
            ),
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


def validate_reading_type_check_diagnostics_html(
    case: str,
    diagnostics: object,
    page: str,
) -> None:
    if not isinstance(diagnostics, list):
        raise SystemExit(
            "web route smoke check failed: "
            f"{case} malformed reading type-check diagnostics"
        )
    if not diagnostics:
        if (
            "Reading Type Check Diagnostics" in page
            or 'data-reading-type-check-failure-count="' in page
        ):
            raise SystemExit(
                "web route smoke check failed: "
                f"{case} unexpected reading type-check diagnostics HTML"
            )
        return
    fragments = [
        "Reading Type Check Diagnostics",
        f'data-reading-type-check-failure-count="{len(diagnostics)}"',
        "Raw reading type-check JSON",
    ]
    for diagnostic in diagnostics:
        if not isinstance(diagnostic, dict):
            raise SystemExit(
                "web route smoke check failed: "
                f"{case} malformed reading type-check diagnostic"
            )
        state_count = str(diagnostic.get("state_opposition_count", ""))
        fragments.extend(
            [
                'data-reading-type-check-index="'
                + html.escape(str(diagnostic.get("reading_index", "")), quote=True)
                + '"',
                'data-reading-type-check-name="'
                + html.escape(str(diagnostic.get("reading_name", "")), quote=True)
                + '"',
                'data-reading-type-check-source="'
                + html.escape(str(diagnostic.get("source", "")), quote=True)
                + '"',
                'data-reading-type-check-scope="'
                + html.escape(str(diagnostic.get("scope", "")), quote=True)
                + '"',
                'data-reading-type-check-coq-definition="'
                + html.escape(str(diagnostic.get("coq_definition", "")), quote=True)
                + '"',
                'data-reading-type-check-path="'
                + html.escape(str(diagnostic.get("path", "")), quote=True)
                + '"',
                'data-reading-type-check-state-opposition-count="'
                + html.escape(state_count, quote=True)
                + '"',
            ]
        )
        errors = diagnostic.get("errors")
        if isinstance(errors, list):
            fragments.extend(
                'data-reading-type-check-error="'
                + html.escape(str(error), quote=True)
                + '"'
                for error in errors
            )
    require_html_fragments(
        page,
        fragments,
        f"{case} reading type-check diagnostics HTML",
    )


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


def validate_analyze_failure_surface_type_contract(
    payload: dict,
    page: str,
    sentence: str,
    label: str,
    expected_stage: str,
) -> None:
    if payload.get("schema_version") != "analyze.v1":
        raise SystemExit(f"web route smoke check failed: {label} analyze schema drift")
    if payload.get("ok") is not False:
        raise SystemExit(f"web route smoke check failed: {label} analyze did not fail")
    if payload.get("input_sentence") != sentence:
        raise SystemExit(f"web route smoke check failed: {label} analyze input drift")
    diagnostics = payload.get("diagnostics")
    if not isinstance(diagnostics, dict):
        raise SystemExit(f"web route smoke check failed: {label} diagnostics missing")
    if diagnostics.get("failure_stage") != expected_stage:
        raise SystemExit(f"web route smoke check failed: {label} diagnostics stage drift")
    validate_reading_type_check_diagnostics(
        label,
        diagnostics.get("reading_type_check_diagnostics"),
        expected_count=diagnostics.get("reading_type_check_failure_count"),
    )
    validate_reading_type_check_recovery_alignment(label, diagnostics)
    validate_reading_type_check_diagnostics_html(
        label,
        diagnostics.get("reading_type_check_diagnostics"),
        page,
    )
    validate_surface_type_contract_diagnostics_context(
        label,
        payload.get("surface_type_contract_diagnostics"),
    )
    type_contract_context = surface_type_contract_diagnostics_context_preview()
    type_contract_categories = surface_type_contract_diagnostic_category_text(
        type_contract_context
    )
    require_text_fragments(
        page,
        [
            "Surface Type Contract Diagnostics",
            (
                'data-surface-type-contract-diagnostic-schema="'
                + str(type_contract_context.get("schema_version", ""))
                + '"'
            ),
            (
                'data-surface-type-contract-diagnostic-count="'
                + str(type_contract_context.get("category_count", ""))
                + '"'
            ),
            (
                'data-surface-type-contract-diagnostic-categories="'
                + html.escape(type_contract_categories, quote=True)
                + '"'
            ),
            (
                'data-surface-type-contract-registry-id="'
                + str(type_contract_context.get("registry_id", ""))
                + '"'
            ),
            (
                'data-action-surface-type-contract-schema="'
                + str(type_contract_context.get("schema_version", ""))
                + '"'
            ),
            (
                'data-action-surface-type-contract-count="'
                + str(type_contract_context.get("category_count", ""))
                + '"'
            ),
            (
                'data-action-surface-type-contract-categories="'
                + html.escape(type_contract_categories, quote=True)
                + '"'
            ),
            (
                'data-action-surface-type-contract-registry-id="'
                + str(type_contract_context.get("registry_id", ""))
                + '"'
            ),
        ],
        f"{label} surface type contract diagnostics HTML",
    )


def validate_analyze_recovery_action_run_metadata(
    label: str,
    sentence: str,
    require_coq: bool,
    action_index: int,
    payload: dict,
) -> None:
    diagnostics = payload.get("diagnostics")
    if not isinstance(diagnostics, dict):
        raise SystemExit(f"web route smoke check failed: {label} diagnostics missing")
    actions = diagnostics.get("recovery_actions")
    if not isinstance(actions, list) or action_index >= len(actions):
        raise SystemExit(
            f"web route smoke check failed: {label} ordinary analyze action metadata missing"
        )
    action = actions[action_index]
    if not isinstance(action, dict):
        raise SystemExit(
            f"web route smoke check failed: {label} ordinary analyze action metadata malformed"
        )
    expected_plan = recovery_action_repair_plan_preview(
        "ordinary_analyze_failure",
        action_index,
        str(diagnostics.get("failure_stage") or ""),
        action,
    )
    expected_can_run = expected_plan.get("can_auto_run") is True
    if action.get("automation_mode") != expected_plan.get("automation_mode"):
        raise SystemExit(
            f"web route smoke check failed: {label} ordinary analyze action automation drift"
        )
    if action.get("can_auto_run") is not expected_can_run:
        raise SystemExit(
            f"web route smoke check failed: {label} ordinary analyze action run drift"
        )
    if action.get("can_auto_apply") is not False:
        raise SystemExit(
            f"web route smoke check failed: {label} ordinary analyze action apply drift"
        )
    if action.get("target_fields") != expected_plan.get("target_fields"):
        raise SystemExit(
            f"web route smoke check failed: {label} ordinary analyze action target drift"
        )
    expected_action_path = analyze_action_api_path(
        sentence,
        action_index,
        require_coq=require_coq,
    )
    expected_action_download_path = analyze_action_api_path(
        sentence,
        action_index,
        require_coq=require_coq,
        download=True,
    )
    expected_action_filename = analyze_action_artifact_filename(sentence, action_index)
    if action.get("api_path") != expected_action_path:
        raise SystemExit(
            f"web route smoke check failed: {label} ordinary analyze action export path drift"
        )
    if action.get("download_api_path") != expected_action_download_path:
        raise SystemExit(
            f"web route smoke check failed: {label} ordinary analyze action export download drift"
        )
    if action.get("download_filename") != expected_action_filename:
        raise SystemExit(
            f"web route smoke check failed: {label} ordinary analyze action export filename drift"
        )
    if expected_can_run:
        expected_path = analyze_action_run_api_path(
            sentence,
            action_index,
            require_coq=require_coq,
        )
        expected_download_path = analyze_action_run_api_path(
            sentence,
            action_index,
            require_coq=require_coq,
            download=True,
        )
        expected_filename = analyze_action_run_artifact_filename(sentence, action_index)
        if action.get("inspection_run_api_path") != expected_path:
            raise SystemExit(
                f"web route smoke check failed: {label} ordinary analyze action path drift"
            )
        if action.get("inspection_run_download_api_path") != expected_download_path:
            raise SystemExit(
                f"web route smoke check failed: {label} ordinary analyze action download drift"
            )
        if action.get("inspection_run_download_filename") != expected_filename:
            raise SystemExit(
                f"web route smoke check failed: {label} ordinary analyze action filename drift"
            )
    else:
        for field in [
            "inspection_run_api_path",
            "inspection_run_download_api_path",
            "inspection_run_download_filename",
        ]:
            if action.get(field) is not None:
                raise SystemExit(
                    "web route smoke check failed: "
                    f"{label} unsafe ordinary analyze action {field}"
                )


def validate_analyze_action_export_bundle(
    label: str,
    sentence: str,
    action_index: int,
    analyze_payload: dict,
    action_bundle: dict,
) -> None:
    diagnostics = analyze_payload.get("diagnostics")
    if not isinstance(diagnostics, dict):
        raise SystemExit(f"web route smoke check failed: {label} analyze diagnostics drift")
    actions = diagnostics.get("recovery_actions")
    if not isinstance(actions, list) or action_index >= len(actions):
        raise SystemExit(f"web route smoke check failed: {label} analyze action drift")
    expected_action = actions[action_index]
    if not isinstance(expected_action, dict):
        raise SystemExit(f"web route smoke check failed: {label} analyze action shape drift")
    expected_repair_plan = recovery_action_repair_plan_preview(
        "ordinary_analyze_failure",
        action_index,
        str(diagnostics.get("failure_stage") or ""),
        expected_action,
    )
    expected_repair_plan["source"] = "analyze"
    expected_repair_plan["input_sentence"] = sentence
    if action_bundle.get("schema_version") != "diagnostic_recovery_action.v1":
        raise SystemExit(f"web route smoke check failed: {label} analyze action schema drift")
    if action_bundle.get("source") != "analyze":
        raise SystemExit(f"web route smoke check failed: {label} analyze action source drift")
    if action_bundle.get("input_sentence") != sentence:
        raise SystemExit(f"web route smoke check failed: {label} analyze action input drift")
    if action_bundle.get("require_coq") is not True:
        raise SystemExit(f"web route smoke check failed: {label} analyze action coq flag drift")
    if action_bundle.get("action_index") != action_index:
        raise SystemExit(f"web route smoke check failed: {label} analyze action index drift")
    if action_bundle.get("failure_stage") != diagnostics.get("failure_stage"):
        raise SystemExit(f"web route smoke check failed: {label} analyze action stage drift")
    if action_bundle.get("action") != expected_action:
        raise SystemExit(f"web route smoke check failed: {label} analyze action payload drift")
    if action_bundle.get("repair_plan") != expected_repair_plan:
        raise SystemExit(f"web route smoke check failed: {label} analyze action plan drift")
    if action_bundle.get("diagnostics") != diagnostics:
        raise SystemExit(f"web route smoke check failed: {label} analyze action diagnostics drift")
    validate_reading_type_check_recovery_alignment(
        label,
        action_bundle.get("diagnostics"),
    )
    contract = action_bundle.get("contract")
    if not isinstance(contract, dict):
        raise SystemExit(f"web route smoke check failed: {label} analyze action contract drift")
    validate_diagnostic_contract_manifest(contract)
    validate_surface_type_contract_diagnostics_context(
        label,
        action_bundle.get("surface_type_contract_diagnostics"),
    )


def validate_analyze_action_export_preview(
    label: str,
    page: str,
    action_index: int,
    action_bundle: dict,
) -> None:
    action = action_bundle.get("action")
    if not isinstance(action, dict):
        raise SystemExit(f"web route smoke check failed: {label} action preview drift")
    next_step_block = html_list_item_block(
        page,
        f'id="recovery-action-{action_index}"',
        f"{label} ordinary next-step action {action_index}",
    )
    expected_json = html.escape(json.dumps(action_bundle, ensure_ascii=False, indent=2))
    expected_fragments = [
        'class="next-step-action-link"',
        'href="' + html.escape(str(action.get("api_path", "")), quote=True) + '"',
        'class="next-step-action-download-link"',
        'href="'
        + html.escape(str(action.get("download_api_path", "")), quote=True)
        + '"',
        'download="'
        + html.escape(str(action.get("download_filename", "")), quote=True)
        + '"',
        'class="next-step-action-json"',
        'data-action-json-schema="diagnostic_recovery_action.v1"',
        "<summary>Action JSON</summary>",
        expected_json,
    ]
    require_html_fragments(
        next_step_block,
        expected_fragments,
        f"{label} ordinary action JSON preview",
    )


def validate_ordinary_analyze_action_export_surface(
    label: str,
    surface_sentence: str,
    require_coq: bool,
    action_index: int,
    analyze_payload: dict,
    page: str,
    action_bundle: dict,
    *,
    expected_failure_stage: str | None = None,
    expected_action_kind: str | None = None,
    expected_can_auto_run: bool | None = None,
    expected_verification_scope_kind: str | None = None,
    expected_certification_level: str = "none",
    expected_verification_scope_rule: str | None = None,
) -> str:
    if analyze_payload.get("ok") is not False:
        raise SystemExit(f"web route smoke check failed: {label} analyze did not fail")
    sentence = str(analyze_payload.get("input_sentence", surface_sentence))
    diagnostics = analyze_payload.get("diagnostics")
    if not isinstance(diagnostics, dict):
        raise SystemExit(f"web route smoke check failed: {label} analyze diagnostics drift")
    if (
        expected_failure_stage is not None
        and diagnostics.get("failure_stage") != expected_failure_stage
    ):
        raise SystemExit(f"web route smoke check failed: {label} diagnostics stage drift")
    actions = diagnostics.get("recovery_actions")
    if not isinstance(actions, list) or action_index >= len(actions):
        raise SystemExit(f"web route smoke check failed: {label} analyze action drift")
    expected_action = actions[action_index]
    if not isinstance(expected_action, dict):
        raise SystemExit(f"web route smoke check failed: {label} analyze action shape drift")
    if expected_action_kind is not None and expected_action.get("kind") != expected_action_kind:
        raise SystemExit(f"web route smoke check failed: {label} action kind drift")
    if (
        expected_verification_scope_kind is not None
        and expected_verification_scope_kind != "fallback_shallow"
    ):
        validate_verification_scope(
            analyze_payload,
            page,
            label,
            expected_verification_scope_kind,
            expected_certification_level,
            expected_verification_scope_rule,
        )
    validate_analyze_recovery_action_run_metadata(
        label,
        sentence,
        require_coq,
        action_index,
        analyze_payload,
    )
    validate_analyze_action_export_bundle(
        label,
        sentence,
        action_index,
        analyze_payload,
        action_bundle,
    )
    repair_plan = action_bundle.get("repair_plan")
    if not isinstance(repair_plan, dict):
        raise SystemExit(f"web route smoke check failed: {label} analyze action plan drift")
    if (
        expected_can_auto_run is not None
        and repair_plan.get("can_auto_run") is not expected_can_auto_run
    ):
        raise SystemExit(f"web route smoke check failed: {label} analyze action run drift")
    validate_analyze_action_export_preview(
        label,
        page,
        action_index,
        action_bundle,
    )
    return sentence


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


def validate_fallback_promotion_contract(label: str, payload: dict) -> None:
    sentence = str(payload.get("input_sentence", ""))
    translation = payload.get("dependent_type_translation")
    verification_scope = payload.get("verification_scope")
    upgrade_plan = payload.get("certification_upgrade_plan")
    rule_draft = payload.get("construction_rule_draft")
    if not isinstance(verification_scope, dict):
        raise SystemExit(f"web route smoke check failed: {label} promotion scope missing")
    if not isinstance(upgrade_plan, dict):
        raise SystemExit(f"web route smoke check failed: {label} promotion plan missing")
    if not isinstance(rule_draft, dict):
        raise SystemExit(f"web route smoke check failed: {label} promotion draft missing")
    if (
        verification_scope.get("kind") != "fallback_shallow"
        or verification_scope.get("certification_level") != "shallow_scaffold"
    ):
        raise SystemExit(f"web route smoke check failed: {label} promotion scope drift")

    candidate_rule_id = rule_draft.get("candidate_rule_id")
    if (
        not isinstance(candidate_rule_id, str)
        or not candidate_rule_id
        or upgrade_plan.get("candidate_rule_id") != candidate_rule_id
        or rule_draft.get("candidate_analyzer") != f"{candidate_rule_id}_pipeline"
    ):
        raise SystemExit(f"web route smoke check failed: {label} promotion candidate drift")
    if (
        upgrade_plan.get("schema_version") != "certification_upgrade_plan.v1"
        or rule_draft.get("schema_version") != "construction_rule_draft.v1"
        or upgrade_plan.get("source_verification_scope") != "fallback_shallow"
        or rule_draft.get("source_verification_scope") != "fallback_shallow"
        or upgrade_plan.get("target_certification_level") != "construction_rule"
        or upgrade_plan.get("automation_mode") != "human_review_required"
        or rule_draft.get("automation_mode") != "human_review_required"
        or upgrade_plan.get("can_auto_apply") is not False
        or rule_draft.get("can_auto_apply") is not False
    ):
        raise SystemExit(f"web route smoke check failed: {label} promotion metadata drift")
    if (
        upgrade_plan.get("source_sentence") != sentence
        or rule_draft.get("accepted_examples") != [sentence]
    ):
        raise SystemExit(f"web route smoke check failed: {label} promotion sentence drift")
    if (
        upgrade_plan.get("dependent_type_translation") != translation
        or upgrade_plan.get("ast_summary") != rule_draft.get("ast_summary")
    ):
        raise SystemExit(f"web route smoke check failed: {label} promotion analysis drift")

    gaps = verification_scope.get("certification_gaps")
    gap_ids = [gap.get("id") for gap in gaps if isinstance(gap, dict)] if isinstance(gaps, list) else []
    expected_gap_ids = [
        "no_registered_construction_rule",
        "no_fragment_specific_readings",
        "no_construction_hygiene_policy",
    ]
    if gap_ids != expected_gap_ids:
        raise SystemExit(f"web route smoke check failed: {label} promotion gap drift")
    steps = upgrade_plan.get("steps")
    checked_steps = steps if isinstance(steps, list) else []
    step_gap_ids = (
        [step.get("gap_id") for step in checked_steps if isinstance(step, dict)]
    )
    if step_gap_ids != gap_ids:
        raise SystemExit(f"web route smoke check failed: {label} promotion step drift")
    for step in checked_steps:
        if (
            not isinstance(step, dict)
            or step.get("can_auto_apply") is not False
            or not isinstance(step.get("target_artifact"), str)
            or not isinstance(step.get("verification"), str)
        ):
            raise SystemExit(f"web route smoke check failed: {label} promotion step drift")

    readings = rule_draft.get("semantic_reading_drafts")
    if not isinstance(readings, list) or len(readings) != 1 or not isinstance(readings[0], dict):
        raise SystemExit(f"web route smoke check failed: {label} promotion reading drift")
    reading = readings[0]
    expected_reading_name = f"{candidate_rule_id}_single_reading"
    if (
        reading.get("name") != expected_reading_name
        or reading.get("source") != candidate_rule_id
        or reading.get("coq_definition") != expected_reading_name
        or reading.get("dependent_type_translation") != translation
        or reading.get("attachment_summary_kind") != "none"
    ):
        raise SystemExit(f"web route smoke check failed: {label} promotion reading drift")

    hygiene = rule_draft.get("hygiene_policy_draft")
    forbidden_fragments = (
        hygiene.get("forbidden_coq_fragments") if isinstance(hygiene, dict) else None
    )
    if not isinstance(forbidden_fragments, list) or len(forbidden_fragments) < 4:
        raise SystemExit(f"web route smoke check failed: {label} promotion hygiene drift")
    test_draft = rule_draft.get("test_draft")
    if (
        not isinstance(test_draft, dict)
        or test_draft.get("positive_sentence") != sentence
        or test_draft.get("expected_verification_scope_kind") != "registered_construction"
        or test_draft.get("expected_certification_level") != "construction_rule"
        or test_draft.get("expected_forbidden_fragment_count") != len(forbidden_fragments)
    ):
        raise SystemExit(f"web route smoke check failed: {label} promotion test drift")

    commands = upgrade_plan.get("verification_commands")
    if (
        not isinstance(commands, list)
        or not commands
        or commands != rule_draft.get("verification_commands")
    ):
        raise SystemExit(f"web route smoke check failed: {label} promotion command drift")
    patch_text = rule_draft.get("patch_text_preview")
    if (
        not isinstance(patch_text, str)
        or f"rule_id = {candidate_rule_id!r}" not in patch_text
        or f"analyzer = {candidate_rule_id + '_pipeline'!r}" not in patch_text
        or f"semantic_reading = {expected_reading_name!r}" not in patch_text
    ):
        raise SystemExit(f"web route smoke check failed: {label} promotion patch drift")

    preflight = rule_draft.get("registration_preflight")
    if not isinstance(preflight, dict):
        raise SystemExit(f"web route smoke check failed: {label} promotion preflight missing")
    if (
        preflight.get("schema_version") != "construction_rule_registration_preflight.v1"
        or preflight.get("candidate_rule_id") != candidate_rule_id
        or preflight.get("candidate_analyzer") != f"{candidate_rule_id}_pipeline"
        or preflight.get("ok") is not True
        or preflight.get("registration_status") != "human_review_required"
        or preflight.get("can_auto_register") is not False
        or preflight.get("human_review_required") is not True
        or preflight.get("blocking_issues") != []
    ):
        raise SystemExit(f"web route smoke check failed: {label} promotion preflight drift")
    checks = preflight.get("checks")
    expected_check_ids = [
        "candidate_rule_id_unique",
        "candidate_analyzer_unique",
        "accepted_examples_present",
        "semantic_reading_draft_present",
        "hygiene_policy_present",
        "test_draft_present",
    ]
    if (
        not isinstance(checks, list)
        or [check.get("id") for check in checks if isinstance(check, dict)] != expected_check_ids
        or any(
            not isinstance(check, dict) or check.get("ok") is not True
            for check in checks
        )
    ):
        raise SystemExit(f"web route smoke check failed: {label} promotion preflight check drift")
    review_fields = preflight.get("required_human_review_fields")
    if (
        not isinstance(review_fields, list)
        or "analyzer implementation" not in review_fields
        or "registration tests" not in review_fields
    ):
        raise SystemExit(f"web route smoke check failed: {label} promotion preflight review drift")


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
    validate_fallback_promotion_contract(case, payload)
    certification_gaps = payload.get("verification_scope", {}).get("certification_gaps")
    expected_gap_ids = [
        "no_registered_construction_rule",
        "no_fragment_specific_readings",
        "no_construction_hygiene_policy",
    ]
    if (
        not isinstance(certification_gaps, list)
        or [gap.get("id") for gap in certification_gaps if isinstance(gap, dict)]
        != expected_gap_ids
    ):
        raise SystemExit("web route smoke check failed: fallback certification gap drift")
    upgrade_plan = payload.get("certification_upgrade_plan")
    if not isinstance(upgrade_plan, dict):
        raise SystemExit("web route smoke check failed: fallback upgrade plan missing")
    if (
        upgrade_plan.get("schema_version") != "certification_upgrade_plan.v1"
        or upgrade_plan.get("source_verification_scope") != "fallback_shallow"
        or upgrade_plan.get("target_certification_level") != "construction_rule"
        or upgrade_plan.get("candidate_rule_id") != "fallback_time_time_candidate"
        or upgrade_plan.get("automation_mode") != "human_review_required"
        or upgrade_plan.get("can_auto_apply") is not False
    ):
        raise SystemExit("web route smoke check failed: fallback upgrade plan drift")
    upgrade_steps = upgrade_plan.get("steps")
    if (
        not isinstance(upgrade_steps, list)
        or [step.get("gap_id") for step in upgrade_steps if isinstance(step, dict)]
        != expected_gap_ids
    ):
        raise SystemExit("web route smoke check failed: fallback upgrade step drift")
    rule_draft = payload.get("construction_rule_draft")
    if not isinstance(rule_draft, dict):
        raise SystemExit("web route smoke check failed: fallback rule draft missing")
    if (
        rule_draft.get("schema_version") != "construction_rule_draft.v1"
        or rule_draft.get("source_verification_scope") != "fallback_shallow"
        or rule_draft.get("candidate_rule_id") != "fallback_time_time_candidate"
        or rule_draft.get("candidate_analyzer") != "fallback_time_time_candidate_pipeline"
        or rule_draft.get("automation_mode") != "human_review_required"
        or rule_draft.get("can_auto_apply") is not False
    ):
        raise SystemExit("web route smoke check failed: fallback rule draft drift")
    draft_readings = rule_draft.get("semantic_reading_drafts")
    if (
        not isinstance(draft_readings, list)
        or len(draft_readings) != 1
        or draft_readings[0].get("name") != "fallback_time_time_candidate_single_reading"
        or draft_readings[0].get("source") != "fallback_time_time_candidate"
    ):
        raise SystemExit("web route smoke check failed: fallback rule draft reading drift")
    hygiene = rule_draft.get("hygiene_policy_draft")
    forbidden_fragments = hygiene.get("forbidden_coq_fragments") if isinstance(hygiene, dict) else None
    expected_forbidden_fragments = [
        "Parameter Event : Type.",
        "exists e : Event",
        "Parameter Agent :",
        "Parameter Theme :",
    ]
    if forbidden_fragments != expected_forbidden_fragments:
        raise SystemExit("web route smoke check failed: fallback rule draft hygiene drift")
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
        "certification gaps",
        'data-certification-gap-id="no_registered_construction_rule"',
        'data-certification-gap-id="no_fragment_specific_readings"',
        'data-certification-gap-id="no_construction_hygiene_policy"',
        "Certification Upgrade Plan",
        'data-upgrade-plan-schema="certification_upgrade_plan.v1"',
        'data-upgrade-source-scope="fallback_shallow"',
        'data-upgrade-target-level="construction_rule"',
        'data-upgrade-candidate-rule-id="fallback_time_time_candidate"',
        'data-upgrade-gap-id="no_registered_construction_rule"',
        'data-upgrade-action-kind="draft_construction_rule"',
        "Construction Rule Draft",
        'data-rule-draft-schema="construction_rule_draft.v1"',
        'data-rule-draft-source-scope="fallback_shallow"',
        'data-rule-draft-id="fallback_time_time_candidate"',
        'data-rule-draft-analyzer="fallback_time_time_candidate_pipeline"',
        'data-rule-draft-can-auto-apply="false"',
        'data-rule-draft-reading="fallback_time_time_candidate_single_reading"',
        'data-rule-draft-forbidden-fragment="Parameter Event : Type."',
        (
            "/api/construction-rule-draft?sentence=Mary+laughed+"
            "from+a+window+with+a+camera+beside+a+shelf+"
            "loudly+under+a+lamp+on+a+table+with+a+microphone+"
            "near+a+door+with+a+telescope+near+a+window+"
            "with+a+knife+yesterday&amp;require_coq=1&amp;download=1"
        ),
    ]
    require_text_fragments(page, expected_page_fragments, "fallback HTML")
    if html.escape(sentence, quote=True) not in page:
        raise SystemExit("web route smoke check failed: fallback page input drift")


def validate_construction_rule_draft_export(
    label: str,
    analyze_payload: dict,
    page: str,
    draft_payload: dict,
    sentence: str,
    require_coq: bool,
) -> None:
    draft = analyze_payload.get("construction_rule_draft")
    if not isinstance(draft, dict):
        raise SystemExit(f"web route smoke check failed: {label} draft missing")
    if (
        draft_payload.get("schema_version") != "construction_rule_draft_response.v1"
        or draft_payload.get("ok") is not True
        or draft_payload.get("input_sentence") != sentence
        or draft_payload.get("draft_schema_version") != "construction_rule_draft.v1"
        or draft_payload.get("construction_rule_draft") != draft
    ):
        raise SystemExit(
            f"web route smoke check failed: {label} construction rule draft response drift"
        )
    if draft_payload.get("verification_scope") != analyze_payload.get("verification_scope"):
        raise SystemExit(
            f"web route smoke check failed: {label} construction rule draft scope drift"
        )
    if draft_payload.get("diagnostics") != analyze_payload.get("diagnostics"):
        raise SystemExit(
            f"web route smoke check failed: {label} construction rule draft diagnostics drift"
        )
    validate_fallback_promotion_contract(label, analyze_payload)

    candidate_rule_id = str(draft.get("candidate_rule_id", ""))
    if (
        draft.get("schema_version") != "construction_rule_draft.v1"
        or draft.get("source_verification_scope") != "fallback_shallow"
        or not candidate_rule_id
        or draft.get("automation_mode") != "human_review_required"
        or draft.get("can_auto_apply") is not False
    ):
        raise SystemExit(
            f"web route smoke check failed: {label} construction rule draft metadata drift"
        )
    accepted_examples = draft.get("accepted_examples")
    if not isinstance(accepted_examples, list) or sentence not in accepted_examples:
        raise SystemExit(
            f"web route smoke check failed: {label} construction rule draft example drift"
        )

    expected_href = "/api/construction-rule-draft?" + urlencode(
        {
            "sentence": sentence,
            **({"require_coq": "1"} if require_coq else {}),
            "download": "1",
        }
    )
    raw_json = html.escape(json.dumps(draft, ensure_ascii=False, indent=2))
    expected_fragments = [
        'data-rule-draft-schema="construction_rule_draft.v1"',
        f'data-rule-draft-source-scope="{html.escape(str(draft.get("source_verification_scope", "")), quote=True)}"',
        f'data-rule-draft-id="{html.escape(candidate_rule_id, quote=True)}"',
        f'data-rule-draft-analyzer="{html.escape(str(draft.get("candidate_analyzer", "")), quote=True)}"',
        'data-rule-draft-preflight-schema="construction_rule_registration_preflight.v1"',
        'data-rule-draft-registration-status="human_review_required"',
        'data-rule-draft-can-auto-register="false"',
        f'href="{html.escape(expected_href, quote=True)}"',
        raw_json,
    ]
    require_text_fragments(
        page,
        expected_fragments,
        f"{label} construction rule draft HTML",
    )

    readings = draft.get("semantic_reading_drafts")
    if not isinstance(readings, list) or not readings:
        raise SystemExit(
            f"web route smoke check failed: {label} construction rule draft readings drift"
        )
    for reading in readings:
        if not isinstance(reading, dict):
            raise SystemExit(
                f"web route smoke check failed: {label} construction rule draft readings drift"
            )
        require_text_fragments(
            page,
            [
                f'data-rule-draft-reading="{html.escape(str(reading.get("name", "")), quote=True)}"',
                (
                    'data-rule-draft-reading-source="'
                    f'{html.escape(str(reading.get("source", "")), quote=True)}"'
                ),
            ],
            f"{label} construction rule draft reading HTML",
        )

    hygiene = draft.get("hygiene_policy_draft")
    forbidden_fragments = (
        hygiene.get("forbidden_coq_fragments") if isinstance(hygiene, dict) else None
    )
    if not isinstance(forbidden_fragments, list) or not forbidden_fragments:
        raise SystemExit(
            f"web route smoke check failed: {label} construction rule draft hygiene drift"
        )
    for fragment in forbidden_fragments:
        require_text_fragments(
            page,
            [
                (
                    'data-rule-draft-forbidden-fragment="'
                    f'{html.escape(str(fragment), quote=True)}"'
                ),
            ],
            f"{label} construction rule draft hygiene HTML",
        )

    preflight = draft.get("registration_preflight")
    checks = preflight.get("checks") if isinstance(preflight, dict) else []
    if not isinstance(checks, list):
        raise SystemExit(
            f"web route smoke check failed: {label} construction rule draft preflight drift"
        )
    for check in checks:
        if not isinstance(check, dict):
            raise SystemExit(
                f"web route smoke check failed: {label} construction rule draft preflight drift"
            )
        require_text_fragments(
            page,
            [
                (
                    'data-rule-draft-preflight-check-id="'
                    f'{html.escape(str(check.get("id", "")), quote=True)}"'
                ),
                (
                    'data-rule-draft-preflight-check-ok="'
                    f'{str(check.get("ok") is True).lower()}"'
                ),
            ],
            f"{label} construction rule draft preflight HTML",
        )

    expected_filename = construction_rule_draft_artifact_filename(candidate_rule_id)
    if (
        not expected_filename.startswith("construction_rule_draft__")
        or not expected_filename.endswith(".json")
    ):
        raise SystemExit(
            f"web route smoke check failed: {label} construction rule draft filename drift"
        )


def validate_analyze_active_argument_omission_success(
    payload: dict,
    page: str,
    sentence: str,
) -> None:
    case = "analyze_active_argument_omission_success"
    validate_analyze_success_envelope(
        payload,
        sentence,
        "active_argument_omission",
        ["semantic_readings_check", "construction_hygiene"],
    )
    validate_verification_scope(
        payload,
        page,
        "active_argument_omission",
        "registered_construction",
        "construction_rule",
        "active_argument_omission",
    )
    if payload.get("kind") != "active_argument_omission":
        raise SystemExit("web route smoke check failed: active omission kind drift")
    if payload.get("dependent_type_translation") != "Sigma x_theme : Food. eat(0)(John, x_theme)":
        raise SystemExit("web route smoke check failed: active omission translation drift")
    if "certification_upgrade_plan" in payload or "construction_rule_draft" in payload:
        raise SystemExit("web route smoke check failed: active omission exposes fallback draft")
    ast = payload.get("ast")
    body = ast.get("body") if isinstance(ast, dict) else None
    role_frame = body.get("role_frame", {}).get("roles") if isinstance(body, dict) else None
    if (
        not isinstance(ast, dict)
        or ast.get("kind") != "sigma"
        or ast.get("witness") != "x_theme"
        or ast.get("type") != "Food"
        or not isinstance(body, dict)
        or body.get("kind") != "application"
        or body.get("function") != "eat"
        or body.get("arguments") != ["John", "x_theme"]
        or not isinstance(role_frame, list)
        or len(role_frame) != 2
        or role_frame[0].get("role") != "Agent"
        or role_frame[0].get("source") != "explicit"
        or role_frame[1].get("role") != "Theme"
        or role_frame[1].get("type") != "Food"
        or role_frame[1].get("source") != "omitted"
    ):
        raise SystemExit("web route smoke check failed: active omission AST drift")
    event_semantics = payload.get("event_semantics")
    omission = event_semantics.get("argument_omission") if isinstance(event_semantics, dict) else None
    if (
        not isinstance(event_semantics, dict)
        or event_semantics.get("analysis") != "active-argument-omission"
        or not isinstance(omission, dict)
        or omission.get("predicate") != "eat"
        or omission.get("witness") != "x_theme"
        or omission.get("witness_type") != "Food"
        or omission.get("omitted_role") != "Theme"
    ):
        raise SystemExit("web route smoke check failed: active omission analysis drift")
    hygiene = payload.get("construction_hygiene")
    if not isinstance(hygiene, dict) or hygiene.get("ok") is not True:
        raise SystemExit("web route smoke check failed: active omission hygiene drift")
    readings = payload.get("semantic_readings")
    if not isinstance(readings, list) or len(readings) != 1:
        raise SystemExit("web route smoke check failed: active omission reading count drift")
    validate_semantic_reading_summary(
        readings[0],
        {
            "name": "active_argument_omission_single_reading",
            "scope": "omitted_existential_theme",
            "source": "active_argument_omission",
            "coq_definition": "example_1",
        },
        "none",
        case,
        expected_type=None,
    )
    coq_code = payload.get("coq_code")
    if (
        not isinstance(coq_code, str)
        or "Parameter Food : Type." not in coq_code
        or "exists x_theme : Food" not in coq_code
        or "Parameter x_theme" in coq_code
        or "Parameter Event : Type." in coq_code
        or "Parameter Agent :" in coq_code
        or "Parameter Theme :" in coq_code
    ):
        raise SystemExit("web route smoke check failed: active omission Coq drift")
    validate_successful_semantic_reading_contract(case, payload, page)
    expected_page_fragments = [
        'data-verification-scope-kind="registered_construction"',
        'data-verification-level="construction_rule"',
        "<dt>rule</dt><dd>active_argument_omission</dd>",
        'data-reading-name="active_argument_omission_single_reading"',
        "<dt>source</dt><dd>active_argument_omission</dd>",
        "<dt>scope</dt><dd>omitted_existential_theme</dd>",
        "Sigma x_theme : Food. eat(0)(John, x_theme)",
        "Translation succeeded via construction rule active_argument_omission.",
    ]
    require_text_fragments(page, expected_page_fragments, "active omission HTML")
    if html.escape(sentence, quote=True) not in page:
        raise SystemExit("web route smoke check failed: active omission page input drift")


def validate_analyze_plain_transitive_success(
    payload: dict,
    page: str,
    sentence: str,
) -> None:
    case = "analyze_plain_transitive_success"
    is_timed = sentence == "Mary admired the painting yesterday"
    expected_translation = (
        "at_T(yesterday, admire(0)(mary, painting))"
        if is_timed
        else "admire(0)(mary, painting)"
    )
    expected_scope = "explicit_agent_theme_at_time" if is_timed else "explicit_agent_theme"
    validate_analyze_success_envelope(
        payload,
        sentence,
        "plain_transitive_predication",
        ["semantic_readings_check", "construction_hygiene"],
    )
    validate_verification_scope(
        payload,
        page,
        "plain_transitive_predication",
        "registered_construction",
        "construction_rule",
        "plain_transitive_predication",
    )
    if payload.get("kind") != "plain_transitive_predication":
        raise SystemExit("web route smoke check failed: plain transitive kind drift")
    if payload.get("dependent_type_translation") != expected_translation:
        raise SystemExit("web route smoke check failed: plain transitive translation drift")
    if "certification_upgrade_plan" in payload or "construction_rule_draft" in payload:
        raise SystemExit("web route smoke check failed: plain transitive exposes fallback draft")
    ast = payload.get("ast")
    application_ast = ast
    if is_timed and isinstance(ast, dict):
        if (
            ast.get("kind") != "time"
            or ast.get("operator") != "at"
            or ast.get("arguments") != ["yesterday"]
            or not isinstance(ast.get("body"), dict)
        ):
            raise SystemExit("web route smoke check failed: timed plain transitive AST drift")
        application_ast = ast["body"]
    role_frame = (
        application_ast.get("role_frame", {}).get("roles")
        if isinstance(application_ast, dict)
        else None
    )
    if (
        not isinstance(application_ast, dict)
        or application_ast.get("kind") != "application"
        or application_ast.get("function") != "admire"
        or application_ast.get("arguments") != ["mary", "painting"]
        or application_ast.get("modifiers") != []
        or not isinstance(role_frame, list)
        or len(role_frame) != 2
        or role_frame[0].get("role") != "Agent"
        or role_frame[0].get("type") != "Entity"
        or role_frame[0].get("source") != "explicit"
        or role_frame[1].get("role") != "Theme"
        or role_frame[1].get("type") != "Entity"
        or role_frame[1].get("source") != "explicit"
    ):
        raise SystemExit("web route smoke check failed: plain transitive AST drift")
    event_semantics = payload.get("event_semantics")
    typed_predication = (
        event_semantics.get("plain_transitive_predication")
        if isinstance(event_semantics, dict)
        else None
    )
    if (
        not isinstance(event_semantics, dict)
        or event_semantics.get("analysis") != "plain-transitive-predication"
        or not isinstance(typed_predication, dict)
        or typed_predication.get("predicate") != "admire"
        or typed_predication.get("agent") != "mary"
        or typed_predication.get("theme") != "painting"
        or typed_predication.get("theme_type") != "Entity"
    ):
        raise SystemExit("web route smoke check failed: plain transitive analysis drift")
    if is_timed:
        if typed_predication.get("time_modifier") != {
            "operator": "at",
            "argument": "yesterday",
        }:
            raise SystemExit("web route smoke check failed: timed plain transitive time drift")
    elif "time_modifier" in typed_predication:
        raise SystemExit("web route smoke check failed: untimed plain transitive time drift")
    hygiene = payload.get("construction_hygiene")
    if not isinstance(hygiene, dict) or hygiene.get("ok") is not True:
        raise SystemExit("web route smoke check failed: plain transitive hygiene drift")
    readings = payload.get("semantic_readings")
    if not isinstance(readings, list) or len(readings) != 1:
        raise SystemExit("web route smoke check failed: plain transitive reading count drift")
    validate_semantic_reading_summary(
        readings[0],
        {
            "name": "plain_transitive_predication_single_reading",
            "scope": expected_scope,
            "source": "plain_transitive_predication",
            "coq_definition": "example_1",
        },
        "none",
        case,
        expected_type=None,
    )
    coq_code = payload.get("coq_code")
    if (
        not isinstance(coq_code, str)
        or "Parameter admire : forall n : nat" not in coq_code
        or "Definition example_1" not in coq_code
        or "Parameter Event : Type." in coq_code
        or "Parameter Agent :" in coq_code
        or "Parameter Theme :" in coq_code
    ):
        raise SystemExit("web route smoke check failed: plain transitive Coq drift")
    validate_successful_semantic_reading_contract(case, payload, page)
    expected_page_fragments = [
        'data-verification-scope-kind="registered_construction"',
        'data-verification-level="construction_rule"',
        "<dt>rule</dt><dd>plain_transitive_predication</dd>",
        'data-reading-name="plain_transitive_predication_single_reading"',
        "<dt>source</dt><dd>plain_transitive_predication</dd>",
        f"<dt>scope</dt><dd>{expected_scope}</dd>",
        expected_translation,
        "Translation succeeded via construction rule plain_transitive_predication.",
    ]
    require_text_fragments(page, expected_page_fragments, "plain transitive HTML")
    if html.escape(sentence, quote=True) not in page:
        raise SystemExit("web route smoke check failed: plain transitive page input drift")


def validate_analyze_plain_intransitive_success(
    payload: dict,
    page: str,
    sentence: str,
) -> None:
    case = "analyze_plain_intransitive_success"
    is_timed = sentence == "Mary smiled yesterday"
    expected_translation = (
        "at_T(yesterday, smile(0)(mary))" if is_timed else "smile(0)(mary)"
    )
    expected_scope = "explicit_agent_at_time" if is_timed else "explicit_agent"
    validate_analyze_success_envelope(
        payload,
        sentence,
        "plain_intransitive_predication",
        ["semantic_readings_check", "construction_hygiene"],
    )
    validate_verification_scope(
        payload,
        page,
        "plain_intransitive_predication",
        "registered_construction",
        "construction_rule",
        "plain_intransitive_predication",
    )
    if payload.get("kind") != "plain_intransitive_predication":
        raise SystemExit("web route smoke check failed: plain intransitive kind drift")
    if payload.get("dependent_type_translation") != expected_translation:
        raise SystemExit(
            "web route smoke check failed: plain intransitive translation drift"
        )
    if "certification_upgrade_plan" in payload or "construction_rule_draft" in payload:
        raise SystemExit(
            "web route smoke check failed: plain intransitive exposes fallback draft"
        )
    ast = payload.get("ast")
    application_ast = ast
    if is_timed and isinstance(ast, dict):
        if (
            ast.get("kind") != "time"
            or ast.get("operator") != "at"
            or ast.get("arguments") != ["yesterday"]
            or not isinstance(ast.get("body"), dict)
        ):
            raise SystemExit(
                "web route smoke check failed: timed plain intransitive AST drift"
            )
        application_ast = ast["body"]
    role_frame = (
        application_ast.get("role_frame", {}).get("roles")
        if isinstance(application_ast, dict)
        else None
    )
    if (
        not isinstance(application_ast, dict)
        or application_ast.get("kind") != "application"
        or application_ast.get("function") != "smile"
        or application_ast.get("arguments") != ["mary"]
        or application_ast.get("modifiers") != []
        or not isinstance(role_frame, list)
        or len(role_frame) != 1
        or role_frame[0].get("role") != "Agent"
        or role_frame[0].get("type") != "Entity"
        or role_frame[0].get("source") != "explicit"
    ):
        raise SystemExit("web route smoke check failed: plain intransitive AST drift")
    event_semantics = payload.get("event_semantics")
    typed_predication = (
        event_semantics.get("plain_intransitive_predication")
        if isinstance(event_semantics, dict)
        else None
    )
    if (
        not isinstance(event_semantics, dict)
        or event_semantics.get("analysis") != "plain-intransitive-predication"
        or not isinstance(typed_predication, dict)
        or typed_predication.get("predicate") != "smile"
        or typed_predication.get("agent") != "mary"
        or typed_predication.get("agent_type") != "Entity"
    ):
        raise SystemExit(
            "web route smoke check failed: plain intransitive analysis drift"
        )
    if is_timed:
        if typed_predication.get("time_modifier") != {
            "operator": "at",
            "argument": "yesterday",
        }:
            raise SystemExit(
                "web route smoke check failed: timed plain intransitive time drift"
            )
    elif "time_modifier" in typed_predication:
        raise SystemExit(
            "web route smoke check failed: untimed plain intransitive time drift"
        )
    hygiene = payload.get("construction_hygiene")
    if not isinstance(hygiene, dict) or hygiene.get("ok") is not True:
        raise SystemExit("web route smoke check failed: plain intransitive hygiene drift")
    readings = payload.get("semantic_readings")
    if not isinstance(readings, list) or len(readings) != 1:
        raise SystemExit(
            "web route smoke check failed: plain intransitive reading count drift"
        )
    validate_semantic_reading_summary(
        readings[0],
        {
            "name": "plain_intransitive_predication_single_reading",
            "scope": expected_scope,
            "source": "plain_intransitive_predication",
            "coq_definition": "example_1",
        },
        "none",
        case,
        expected_type=None,
    )
    coq_code = payload.get("coq_code")
    expected_definition = (
        "Definition example_1 : PropT := (at_T yesterday (smile 0 mods_nil mary))."
        if is_timed
        else "Definition example_1 : PropT := (smile 0 mods_nil mary)."
    )
    if (
        not isinstance(coq_code, str)
        or "Parameter smile : forall n : nat, ModifierSeq n -> Entity -> PropT."
        not in coq_code
        or expected_definition not in coq_code
        or "Parameter Event : Type." in coq_code
        or "Parameter Agent :" in coq_code
        or "Parameter Theme :" in coq_code
    ):
        raise SystemExit("web route smoke check failed: plain intransitive Coq drift")
    validate_successful_semantic_reading_contract(case, payload, page)
    expected_page_fragments = [
        'data-verification-scope-kind="registered_construction"',
        'data-verification-level="construction_rule"',
        "<dt>rule</dt><dd>plain_intransitive_predication</dd>",
        'data-reading-name="plain_intransitive_predication_single_reading"',
        "<dt>source</dt><dd>plain_intransitive_predication</dd>",
        f"<dt>scope</dt><dd>{expected_scope}</dd>",
        expected_translation,
        "Translation succeeded via construction rule plain_intransitive_predication.",
    ]
    require_text_fragments(page, expected_page_fragments, "plain intransitive HTML")
    if html.escape(sentence, quote=True) not in page:
        raise SystemExit(
            "web route smoke check failed: plain intransitive page input drift"
        )


def validate_analyze_manner_intransitive_success(
    payload: dict,
    page: str,
    sentence: str,
) -> None:
    case = "analyze_manner_intransitive_success"
    is_timed = sentence == "Mary laughed loudly yesterday"
    expected_translation = (
        "at_T(yesterday, laugh(1)(loudly, mary))"
        if is_timed
        else "laugh(1)(loudly, mary)"
    )
    expected_scope = (
        "explicit_agent_with_manner_adv_at_time"
        if is_timed
        else "explicit_agent_with_manner_adv"
    )
    validate_analyze_success_envelope(
        payload,
        sentence,
        "manner_intransitive_predication",
        ["semantic_readings_check", "construction_hygiene"],
    )
    validate_verification_scope(
        payload,
        page,
        "manner_intransitive_predication",
        "registered_construction",
        "construction_rule",
        "manner_intransitive_predication",
    )
    if payload.get("kind") != "manner_intransitive_predication":
        raise SystemExit("web route smoke check failed: manner intransitive kind drift")
    if payload.get("dependent_type_translation") != expected_translation:
        raise SystemExit(
            "web route smoke check failed: manner intransitive translation drift"
        )
    if "certification_upgrade_plan" in payload or "construction_rule_draft" in payload:
        raise SystemExit(
            "web route smoke check failed: manner intransitive exposes fallback draft"
        )
    ast = payload.get("ast")
    application_ast = ast
    if is_timed and isinstance(ast, dict):
        if (
            ast.get("kind") != "time"
            or ast.get("operator") != "at"
            or ast.get("arguments") != ["yesterday"]
            or not isinstance(ast.get("body"), dict)
        ):
            raise SystemExit(
                "web route smoke check failed: timed manner intransitive AST drift"
            )
        application_ast = ast["body"]
    role_frame = (
        application_ast.get("role_frame", {}).get("roles")
        if isinstance(application_ast, dict)
        else None
    )
    modifier_roles = (
        application_ast.get("modifier_roles", {}).get("roles")
        if isinstance(application_ast, dict)
        else None
    )
    if (
        not isinstance(application_ast, dict)
        or application_ast.get("kind") != "application"
        or application_ast.get("function") != "laugh"
        or application_ast.get("arguments") != ["mary"]
        or application_ast.get("modifiers") != ["loudly"]
        or application_ast.get("adverb_count") != 1
        or not isinstance(role_frame, list)
        or len(role_frame) != 1
        or role_frame[0].get("role") != "Agent"
        or role_frame[0].get("type") != "Entity"
        or role_frame[0].get("source") != "explicit"
        or not isinstance(modifier_roles, list)
        or len(modifier_roles) != 1
        or modifier_roles[0].get("type") != "Adv"
        or modifier_roles[0].get("semantic_role") != "Manner"
    ):
        raise SystemExit("web route smoke check failed: manner intransitive AST drift")
    event_semantics = payload.get("event_semantics")
    typed_predication = (
        event_semantics.get("manner_intransitive_predication")
        if isinstance(event_semantics, dict)
        else None
    )
    if (
        not isinstance(event_semantics, dict)
        or event_semantics.get("analysis") != "manner-intransitive-predication"
        or not isinstance(typed_predication, dict)
        or typed_predication.get("predicate") != "laugh"
        or typed_predication.get("agent") != "mary"
        or typed_predication.get("agent_type") != "Entity"
        or typed_predication.get("modifiers") != ["loudly"]
    ):
        raise SystemExit(
            "web route smoke check failed: manner intransitive analysis drift"
        )
    if is_timed:
        if typed_predication.get("time_modifier") != {
            "operator": "at",
            "argument": "yesterday",
        }:
            raise SystemExit(
                "web route smoke check failed: timed manner intransitive time drift"
            )
    elif "time_modifier" in typed_predication:
        raise SystemExit(
            "web route smoke check failed: untimed manner intransitive time drift"
        )
    hygiene = payload.get("construction_hygiene")
    if not isinstance(hygiene, dict) or hygiene.get("ok") is not True:
        raise SystemExit("web route smoke check failed: manner intransitive hygiene drift")
    readings = payload.get("semantic_readings")
    if not isinstance(readings, list) or len(readings) != 1:
        raise SystemExit(
            "web route smoke check failed: manner intransitive reading count drift"
        )
    validate_semantic_reading_summary(
        readings[0],
        {
            "name": "manner_intransitive_predication_single_reading",
            "scope": expected_scope,
            "source": "manner_intransitive_predication",
            "coq_definition": "example_1",
        },
        "none",
        case,
        expected_type=None,
    )
    coq_code = payload.get("coq_code")
    expected_definition = (
        "Definition example_1 : PropT := (at_T yesterday (laugh 1 (mods_cons 0 loudly mods_nil) mary))."
        if is_timed
        else "Definition example_1 : PropT := (laugh 1 (mods_cons 0 loudly mods_nil) mary)."
    )
    if (
        not isinstance(coq_code, str)
        or "Parameter loudly : Adv." not in coq_code
        or "Parameter loudly : Entity." in coq_code
        or "Parameter laugh : forall n : nat, ModifierSeq n -> Entity -> PropT."
        not in coq_code
        or expected_definition not in coq_code
        or "Parameter Event : Type." in coq_code
        or "Parameter Agent :" in coq_code
        or "Parameter Theme :" in coq_code
    ):
        raise SystemExit("web route smoke check failed: manner intransitive Coq drift")
    validate_successful_semantic_reading_contract(case, payload, page)
    expected_page_fragments = [
        'data-verification-scope-kind="registered_construction"',
        'data-verification-level="construction_rule"',
        "<dt>rule</dt><dd>manner_intransitive_predication</dd>",
        'data-reading-name="manner_intransitive_predication_single_reading"',
        "<dt>source</dt><dd>manner_intransitive_predication</dd>",
        f"<dt>scope</dt><dd>{expected_scope}</dd>",
        expected_translation,
        "Translation succeeded via construction rule manner_intransitive_predication.",
    ]
    require_text_fragments(page, expected_page_fragments, "manner intransitive HTML")
    if html.escape(sentence, quote=True) not in page:
        raise SystemExit(
            "web route smoke check failed: manner intransitive page input drift"
        )


def validate_analyze_instrument_intransitive_success(
    payload: dict,
    page: str,
    sentence: str,
) -> None:
    case = "analyze_instrument_intransitive_success"
    is_timed = sentence == "Mary laughed with a telescope yesterday"
    expected_translation = (
        "at_T(yesterday, laugh(1)(with(telescope), mary))"
        if is_timed
        else "laugh(1)(with(telescope), mary)"
    )
    expected_scope = (
        "explicit_agent_with_instrument_adv_at_time"
        if is_timed
        else "explicit_agent_with_instrument_adv"
    )
    validate_analyze_success_envelope(
        payload,
        sentence,
        "instrument_intransitive_predication",
        ["semantic_readings_check", "construction_hygiene"],
    )
    validate_verification_scope(
        payload,
        page,
        "instrument_intransitive_predication",
        "registered_construction",
        "construction_rule",
        "instrument_intransitive_predication",
    )
    if payload.get("kind") != "instrument_intransitive_predication":
        raise SystemExit(
            "web route smoke check failed: instrument intransitive kind drift"
        )
    if payload.get("dependent_type_translation") != expected_translation:
        raise SystemExit(
            "web route smoke check failed: instrument intransitive translation drift"
        )
    if "certification_upgrade_plan" in payload or "construction_rule_draft" in payload:
        raise SystemExit(
            "web route smoke check failed: instrument intransitive exposes fallback draft"
        )
    ast = payload.get("ast")
    application_ast = ast
    if is_timed and isinstance(ast, dict):
        if (
            ast.get("kind") != "time"
            or ast.get("operator") != "at"
            or ast.get("arguments") != ["yesterday"]
            or not isinstance(ast.get("body"), dict)
        ):
            raise SystemExit(
                "web route smoke check failed: timed instrument intransitive AST drift"
            )
        application_ast = ast["body"]
    role_frame = (
        application_ast.get("role_frame", {}).get("roles")
        if isinstance(application_ast, dict)
        else None
    )
    modifier_roles = (
        application_ast.get("modifier_roles", {}).get("roles")
        if isinstance(application_ast, dict)
        else None
    )
    modifier_vector = (
        application_ast.get("modifier_vector", {}).get("items")
        if isinstance(application_ast, dict)
        else None
    )
    if (
        not isinstance(application_ast, dict)
        or application_ast.get("kind") != "application"
        or application_ast.get("function") != "laugh"
        or application_ast.get("arguments") != ["mary"]
        or application_ast.get("modifiers") != ["with(telescope)"]
        or application_ast.get("adverb_count") != 1
        or not isinstance(role_frame, list)
        or len(role_frame) != 1
        or role_frame[0].get("role") != "Agent"
        or role_frame[0].get("type") != "Entity"
        or role_frame[0].get("source") != "explicit"
        or not isinstance(modifier_roles, list)
        or len(modifier_roles) != 1
        or modifier_roles[0].get("type") != "Adv"
        or modifier_roles[0].get("semantic_role") != "Instrument"
        or not isinstance(modifier_vector, list)
        or [item.get("tail_length") for item in modifier_vector] != [0]
    ):
        raise SystemExit("web route smoke check failed: instrument intransitive AST drift")
    event_semantics = payload.get("event_semantics")
    typed_predication = (
        event_semantics.get("instrument_intransitive_predication")
        if isinstance(event_semantics, dict)
        else None
    )
    if (
        not isinstance(event_semantics, dict)
        or event_semantics.get("analysis") != "instrument-intransitive-predication"
        or not isinstance(typed_predication, dict)
        or typed_predication.get("predicate") != "laugh"
        or typed_predication.get("agent") != "mary"
        or typed_predication.get("agent_type") != "Entity"
        or typed_predication.get("modifiers") != ["with(telescope)"]
        or typed_predication.get("instrument_modifier") != "with(telescope)"
    ):
        raise SystemExit(
            "web route smoke check failed: instrument intransitive analysis drift"
        )
    if is_timed:
        if typed_predication.get("time_modifier") != {
            "operator": "at",
            "argument": "yesterday",
        }:
            raise SystemExit(
                "web route smoke check failed: timed instrument intransitive time drift"
            )
    elif "time_modifier" in typed_predication:
        raise SystemExit(
            "web route smoke check failed: untimed instrument intransitive time drift"
        )
    hygiene = payload.get("construction_hygiene")
    if not isinstance(hygiene, dict) or hygiene.get("ok") is not True:
        raise SystemExit(
            "web route smoke check failed: instrument intransitive hygiene drift"
        )
    readings = payload.get("semantic_readings")
    if not isinstance(readings, list) or len(readings) != 1:
        raise SystemExit(
            "web route smoke check failed: instrument intransitive reading count drift"
        )
    validate_semantic_reading_summary(
        readings[0],
        {
            "name": "instrument_intransitive_predication_single_reading",
            "scope": expected_scope,
            "source": "instrument_intransitive_predication",
            "coq_definition": "example_1",
        },
        "none",
        case,
        expected_type=None,
    )
    coq_code = payload.get("coq_code")
    expected_definition = (
        "Definition example_1 : PropT := (at_T yesterday (laugh 1 (mods_cons 0 with_telescope mods_nil) mary))."
        if is_timed
        else "Definition example_1 : PropT := (laugh 1 (mods_cons 0 with_telescope mods_nil) mary)."
    )
    if (
        not isinstance(coq_code, str)
        or "Parameter with_telescope : Adv." not in coq_code
        or "Parameter with_telescope : Entity." in coq_code
        or "Parameter laugh : forall n : nat, ModifierSeq n -> Entity -> PropT."
        not in coq_code
        or expected_definition not in coq_code
        or "Parameter Event : Type." in coq_code
        or "Parameter Agent :" in coq_code
        or "Parameter Theme :" in coq_code
    ):
        raise SystemExit("web route smoke check failed: instrument intransitive Coq drift")
    validate_successful_semantic_reading_contract(case, payload, page)
    expected_page_fragments = [
        'data-verification-scope-kind="registered_construction"',
        'data-verification-level="construction_rule"',
        "<dt>rule</dt><dd>instrument_intransitive_predication</dd>",
        'data-reading-name="instrument_intransitive_predication_single_reading"',
        "<dt>source</dt><dd>instrument_intransitive_predication</dd>",
        f"<dt>scope</dt><dd>{expected_scope}</dd>",
        expected_translation,
        "Translation succeeded via construction rule instrument_intransitive_predication.",
    ]
    require_text_fragments(page, expected_page_fragments, "instrument intransitive HTML")
    if html.escape(sentence, quote=True) not in page:
        raise SystemExit(
            "web route smoke check failed: instrument intransitive page input drift"
        )


def validate_analyze_directional_intransitive_success(
    payload: dict,
    page: str,
    sentence: str,
) -> None:
    case = "analyze_directional_intransitive_success"
    expectations = {
        "Mary laughed from a window": {
            "translation": "laugh(1)(from(window), mary)",
            "modifiers": ["from(window)"],
            "roles": ["Source"],
            "source_modifiers": ["from(window)"],
            "goal_modifiers": [],
            "scope": "explicit_agent_with_directional_adv_sequence",
            "coq_adv": ["Parameter from_window : Adv."],
            "forbidden_entity": ["Parameter from_window : Entity."],
            "definition": (
                "Definition example_1 : PropT := (laugh 1 "
                "(mods_cons 0 from_window mods_nil) mary)."
            ),
            "time_modifier": None,
        },
        "Mary laughed from a window yesterday": {
            "translation": "at_T(yesterday, laugh(1)(from(window), mary))",
            "modifiers": ["from(window)"],
            "roles": ["Source"],
            "source_modifiers": ["from(window)"],
            "goal_modifiers": [],
            "scope": "explicit_agent_with_directional_adv_sequence_at_time",
            "coq_adv": ["Parameter from_window : Adv."],
            "forbidden_entity": ["Parameter from_window : Entity."],
            "definition": (
                "Definition example_1 : PropT := (at_T yesterday (laugh 1 "
                "(mods_cons 0 from_window mods_nil) mary))."
            ),
            "time_modifier": {"operator": "at", "argument": "yesterday"},
        },
        "Mary laughed into a room yesterday": {
            "translation": "at_T(yesterday, laugh(1)(into(room), mary))",
            "modifiers": ["into(room)"],
            "roles": ["Goal"],
            "source_modifiers": [],
            "goal_modifiers": ["into(room)"],
            "scope": "explicit_agent_with_directional_adv_sequence_at_time",
            "coq_adv": ["Parameter into_room : Adv."],
            "forbidden_entity": ["Parameter into_room : Entity."],
            "definition": (
                "Definition example_1 : PropT := (at_T yesterday (laugh 1 "
                "(mods_cons 0 into_room mods_nil) mary))."
            ),
            "time_modifier": {"operator": "at", "argument": "yesterday"},
        },
        "Mary laughed from a window into a room yesterday": {
            "translation": "at_T(yesterday, laugh(2)(from(window), into(room), mary))",
            "modifiers": ["from(window)", "into(room)"],
            "roles": ["Source", "Goal"],
            "source_modifiers": ["from(window)"],
            "goal_modifiers": ["into(room)"],
            "scope": "explicit_agent_with_directional_adv_sequence_at_time",
            "coq_adv": [
                "Parameter from_window : Adv.",
                "Parameter into_room : Adv.",
            ],
            "forbidden_entity": [
                "Parameter from_window : Entity.",
                "Parameter into_room : Entity.",
            ],
            "definition": (
                "Definition example_1 : PropT := (at_T yesterday (laugh 2 "
                "(mods_cons 1 from_window (mods_cons 0 into_room mods_nil)) mary))."
            ),
            "time_modifier": {"operator": "at", "argument": "yesterday"},
        },
    }
    expected = expectations.get(sentence)
    if expected is None:
        raise SystemExit("web route smoke check failed: unknown directional fixture")
    validate_analyze_success_envelope(
        payload,
        sentence,
        "directional_intransitive_predication",
        ["semantic_readings_check", "construction_hygiene"],
    )
    validate_verification_scope(
        payload,
        page,
        "directional_intransitive_predication",
        "registered_construction",
        "construction_rule",
        "directional_intransitive_predication",
    )
    if payload.get("kind") != "directional_intransitive_predication":
        raise SystemExit("web route smoke check failed: directional kind drift")
    if payload.get("dependent_type_translation") != expected["translation"]:
        raise SystemExit("web route smoke check failed: directional translation drift")
    if "certification_upgrade_plan" in payload or "construction_rule_draft" in payload:
        raise SystemExit("web route smoke check failed: directional exposes fallback draft")
    ast = payload.get("ast")
    application_ast = ast
    if expected["time_modifier"] is not None:
        if (
            not isinstance(ast, dict)
            or ast.get("kind") != "time"
            or ast.get("operator") != expected["time_modifier"]["operator"]
            or ast.get("arguments") != [expected["time_modifier"]["argument"]]
            or not isinstance(ast.get("body"), dict)
        ):
            raise SystemExit("web route smoke check failed: timed directional AST drift")
        application_ast = ast["body"]
    modifier_roles = (
        application_ast.get("modifier_roles", {}).get("roles")
        if isinstance(application_ast, dict)
        else None
    )
    modifier_vector = (
        application_ast.get("modifier_vector", {}).get("items")
        if isinstance(application_ast, dict)
        else None
    )
    if (
        not isinstance(application_ast, dict)
        or application_ast.get("kind") != "application"
        or application_ast.get("function") != "laugh"
        or application_ast.get("arguments") != ["mary"]
        or application_ast.get("modifiers") != expected["modifiers"]
        or application_ast.get("adverb_count") != len(expected["modifiers"])
        or not isinstance(modifier_roles, list)
        or [role.get("semantic_role") for role in modifier_roles] != expected["roles"]
        or any(role.get("type") != "Adv" for role in modifier_roles)
        or not isinstance(modifier_vector, list)
        or [item.get("tail_length") for item in modifier_vector]
        != list(reversed(range(len(expected["modifiers"]))))
    ):
        raise SystemExit("web route smoke check failed: directional AST drift")
    event_semantics = payload.get("event_semantics")
    typed_predication = (
        event_semantics.get("directional_intransitive_predication")
        if isinstance(event_semantics, dict)
        else None
    )
    if (
        not isinstance(event_semantics, dict)
        or event_semantics.get("analysis") != "directional-intransitive-predication"
        or not isinstance(typed_predication, dict)
        or typed_predication.get("predicate") != "laugh"
        or typed_predication.get("agent") != "mary"
        or typed_predication.get("agent_type") != "Entity"
        or typed_predication.get("modifiers") != expected["modifiers"]
        or typed_predication.get("modifier_role_pattern") != expected["roles"]
        or typed_predication.get("directional_modifier_count")
        != len(expected["modifiers"])
        or typed_predication.get("source_modifiers") != expected["source_modifiers"]
        or typed_predication.get("goal_modifiers") != expected["goal_modifiers"]
    ):
        raise SystemExit("web route smoke check failed: directional analysis drift")
    if expected["time_modifier"] is None:
        if "time_modifier" in typed_predication:
            raise SystemExit("web route smoke check failed: untimed directional time drift")
    elif typed_predication.get("time_modifier") != expected["time_modifier"]:
        raise SystemExit("web route smoke check failed: timed directional time drift")
    hygiene = payload.get("construction_hygiene")
    if not isinstance(hygiene, dict) or hygiene.get("ok") is not True:
        raise SystemExit("web route smoke check failed: directional hygiene drift")
    readings = payload.get("semantic_readings")
    if not isinstance(readings, list) or len(readings) != 1:
        raise SystemExit("web route smoke check failed: directional reading count drift")
    validate_semantic_reading_summary(
        readings[0],
        {
            "name": "directional_intransitive_predication_single_reading",
            "scope": expected["scope"],
            "source": "directional_intransitive_predication",
            "coq_definition": "example_1",
        },
        "none",
        case,
        expected_type=None,
    )
    coq_code = payload.get("coq_code")
    if (
        not isinstance(coq_code, str)
        or expected["definition"] not in coq_code
        or "Parameter Event : Type." in coq_code
        or "Parameter Agent :" in coq_code
        or "Parameter Theme :" in coq_code
    ):
        raise SystemExit("web route smoke check failed: directional Coq drift")
    for fragment in expected["coq_adv"]:
        if fragment not in coq_code:
            raise SystemExit("web route smoke check failed: directional Adv declaration drift")
    for fragment in expected["forbidden_entity"]:
        if fragment in coq_code:
            raise SystemExit("web route smoke check failed: directional Entity surrogate drift")
    validate_successful_semantic_reading_contract(case, payload, page)
    expected_page_fragments = [
        'data-verification-scope-kind="registered_construction"',
        'data-verification-level="construction_rule"',
        "<dt>rule</dt><dd>directional_intransitive_predication</dd>",
        'data-reading-name="directional_intransitive_predication_single_reading"',
        "<dt>source</dt><dd>directional_intransitive_predication</dd>",
        f"<dt>scope</dt><dd>{expected['scope']}</dd>",
        expected["translation"],
        "Translation succeeded via construction rule directional_intransitive_predication.",
    ]
    require_text_fragments(page, expected_page_fragments, "directional intransitive HTML")
    if html.escape(sentence, quote=True) not in page:
        raise SystemExit("web route smoke check failed: directional page input drift")


def validate_analyze_directional_instrument_intransitive_success(
    payload: dict,
    page: str,
    sentence: str,
) -> None:
    case = "analyze_directional_instrument_intransitive_success"
    expectations = {
        "Mary laughed from a window with a camera": {
            "translation": "laugh(2)(from(window), with(camera), mary)",
            "modifiers": ["from(window)", "with(camera)"],
            "roles": ["Source", "Instrument"],
            "source_modifiers": ["from(window)"],
            "goal_modifiers": [],
            "instrument_modifiers": ["with(camera)"],
            "scope": "explicit_agent_with_directional_and_instrument_adv_sequence",
            "coq_adv": [
                "Parameter from_window : Adv.",
                "Parameter with_camera : Adv.",
            ],
            "forbidden_entity": [
                "Parameter from_window : Entity.",
                "Parameter with_camera : Entity.",
            ],
            "definition": (
                "Definition example_1 : PropT := (laugh 2 "
                "(mods_cons 1 from_window (mods_cons 0 with_camera mods_nil)) "
                "mary)."
            ),
            "time_modifier": None,
        },
        "Mary laughed from a window with a camera yesterday": {
            "translation": "at_T(yesterday, laugh(2)(from(window), with(camera), mary))",
            "modifiers": ["from(window)", "with(camera)"],
            "roles": ["Source", "Instrument"],
            "source_modifiers": ["from(window)"],
            "goal_modifiers": [],
            "instrument_modifiers": ["with(camera)"],
            "scope": (
                "explicit_agent_with_directional_and_instrument_adv_sequence_at_time"
            ),
            "coq_adv": [
                "Parameter from_window : Adv.",
                "Parameter with_camera : Adv.",
            ],
            "forbidden_entity": [
                "Parameter from_window : Entity.",
                "Parameter with_camera : Entity.",
            ],
            "definition": (
                "Definition example_1 : PropT := (at_T yesterday (laugh 2 "
                "(mods_cons 1 from_window (mods_cons 0 with_camera mods_nil)) "
                "mary))."
            ),
            "time_modifier": {"operator": "at", "argument": "yesterday"},
        },
        "Mary laughed into a room with a camera yesterday": {
            "translation": "at_T(yesterday, laugh(2)(into(room), with(camera), mary))",
            "modifiers": ["into(room)", "with(camera)"],
            "roles": ["Goal", "Instrument"],
            "source_modifiers": [],
            "goal_modifiers": ["into(room)"],
            "instrument_modifiers": ["with(camera)"],
            "scope": (
                "explicit_agent_with_directional_and_instrument_adv_sequence_at_time"
            ),
            "coq_adv": [
                "Parameter into_room : Adv.",
                "Parameter with_camera : Adv.",
            ],
            "forbidden_entity": [
                "Parameter into_room : Entity.",
                "Parameter with_camera : Entity.",
            ],
            "definition": (
                "Definition example_1 : PropT := (at_T yesterday (laugh 2 "
                "(mods_cons 1 into_room (mods_cons 0 with_camera mods_nil)) "
                "mary))."
            ),
            "time_modifier": {"operator": "at", "argument": "yesterday"},
        },
        "Mary laughed from a window into a room with a camera yesterday": {
            "translation": (
                "at_T(yesterday, laugh(3)(from(window), into(room), with(camera), mary))"
            ),
            "modifiers": ["from(window)", "into(room)", "with(camera)"],
            "roles": ["Source", "Goal", "Instrument"],
            "source_modifiers": ["from(window)"],
            "goal_modifiers": ["into(room)"],
            "instrument_modifiers": ["with(camera)"],
            "scope": (
                "explicit_agent_with_directional_and_instrument_adv_sequence_at_time"
            ),
            "coq_adv": [
                "Parameter from_window : Adv.",
                "Parameter into_room : Adv.",
                "Parameter with_camera : Adv.",
            ],
            "forbidden_entity": [
                "Parameter from_window : Entity.",
                "Parameter into_room : Entity.",
                "Parameter with_camera : Entity.",
            ],
            "definition": (
                "Definition example_1 : PropT := (at_T yesterday (laugh 3 "
                "(mods_cons 2 from_window (mods_cons 1 into_room "
                "(mods_cons 0 with_camera mods_nil))) mary))."
            ),
            "time_modifier": {"operator": "at", "argument": "yesterday"},
        },
    }
    expected = expectations.get(sentence)
    if expected is None:
        raise SystemExit(
            "web route smoke check failed: unknown directional-instrument fixture"
        )
    validate_analyze_success_envelope(
        payload,
        sentence,
        "directional_instrument_intransitive_predication",
        ["semantic_readings_check", "construction_hygiene"],
    )
    validate_verification_scope(
        payload,
        page,
        "directional_instrument_intransitive_predication",
        "registered_construction",
        "construction_rule",
        "directional_instrument_intransitive_predication",
    )
    if payload.get("kind") != "directional_instrument_intransitive_predication":
        raise SystemExit(
            "web route smoke check failed: directional-instrument kind drift"
        )
    if payload.get("dependent_type_translation") != expected["translation"]:
        raise SystemExit(
            "web route smoke check failed: directional-instrument translation drift"
        )
    if "certification_upgrade_plan" in payload or "construction_rule_draft" in payload:
        raise SystemExit(
            "web route smoke check failed: directional-instrument exposes fallback draft"
        )
    ast = payload.get("ast")
    application_ast = ast
    if expected["time_modifier"] is not None:
        if (
            not isinstance(ast, dict)
            or ast.get("kind") != "time"
            or ast.get("operator") != expected["time_modifier"]["operator"]
            or ast.get("arguments") != [expected["time_modifier"]["argument"]]
            or not isinstance(ast.get("body"), dict)
        ):
            raise SystemExit(
                "web route smoke check failed: timed directional-instrument AST drift"
            )
        application_ast = ast["body"]
    modifier_roles = (
        application_ast.get("modifier_roles", {}).get("roles")
        if isinstance(application_ast, dict)
        else None
    )
    modifier_vector = (
        application_ast.get("modifier_vector", {}).get("items")
        if isinstance(application_ast, dict)
        else None
    )
    role_frame = (
        application_ast.get("role_frame", {}).get("roles")
        if isinstance(application_ast, dict)
        else None
    )
    if (
        not isinstance(application_ast, dict)
        or application_ast.get("kind") != "application"
        or application_ast.get("function") != "laugh"
        or application_ast.get("arguments") != ["mary"]
        or application_ast.get("modifiers") != expected["modifiers"]
        or application_ast.get("adverb_count") != len(expected["modifiers"])
        or not isinstance(role_frame, list)
        or len(role_frame) != 1
        or role_frame[0].get("role") != "Agent"
        or role_frame[0].get("type") != "Entity"
        or role_frame[0].get("source") != "explicit"
        or not isinstance(modifier_roles, list)
        or [role.get("semantic_role") for role in modifier_roles] != expected["roles"]
        or any(role.get("type") != "Adv" for role in modifier_roles)
        or not isinstance(modifier_vector, list)
        or [item.get("tail_length") for item in modifier_vector]
        != list(reversed(range(len(expected["modifiers"]))))
    ):
        raise SystemExit(
            "web route smoke check failed: directional-instrument AST drift"
        )
    event_semantics = payload.get("event_semantics")
    typed_predication = (
        event_semantics.get("directional_instrument_intransitive_predication")
        if isinstance(event_semantics, dict)
        else None
    )
    if (
        not isinstance(event_semantics, dict)
        or event_semantics.get("analysis")
        != "directional-instrument-intransitive-predication"
        or not isinstance(typed_predication, dict)
        or typed_predication.get("predicate") != "laugh"
        or typed_predication.get("agent") != "mary"
        or typed_predication.get("agent_type") != "Entity"
        or typed_predication.get("modifiers") != expected["modifiers"]
        or typed_predication.get("modifier_role_pattern") != expected["roles"]
        or typed_predication.get("source_modifiers") != expected["source_modifiers"]
        or typed_predication.get("goal_modifiers") != expected["goal_modifiers"]
        or typed_predication.get("instrument_modifiers")
        != expected["instrument_modifiers"]
        or typed_predication.get("directional_modifier_count")
        != len(expected["source_modifiers"]) + len(expected["goal_modifiers"])
        or typed_predication.get("instrument_modifier_count")
        != len(expected["instrument_modifiers"])
    ):
        raise SystemExit(
            "web route smoke check failed: directional-instrument analysis drift"
        )
    if expected["time_modifier"] is None:
        if "time_modifier" in typed_predication:
            raise SystemExit(
                "web route smoke check failed: untimed directional-instrument time drift"
            )
    elif typed_predication.get("time_modifier") != expected["time_modifier"]:
        raise SystemExit(
            "web route smoke check failed: timed directional-instrument time drift"
        )
    hygiene = payload.get("construction_hygiene")
    if not isinstance(hygiene, dict) or hygiene.get("ok") is not True:
        raise SystemExit(
            "web route smoke check failed: directional-instrument hygiene drift"
        )
    readings = payload.get("semantic_readings")
    if not isinstance(readings, list) or len(readings) != 1:
        raise SystemExit(
            "web route smoke check failed: directional-instrument reading count drift"
        )
    validate_semantic_reading_summary(
        readings[0],
        {
            "name": (
                "directional_instrument_intransitive_predication_single_reading"
            ),
            "scope": expected["scope"],
            "source": "directional_instrument_intransitive_predication",
            "coq_definition": "example_1",
        },
        "none",
        case,
        expected_type=None,
    )
    coq_code = payload.get("coq_code")
    if (
        not isinstance(coq_code, str)
        or expected["definition"] not in coq_code
        or "Parameter Event : Type." in coq_code
        or "Parameter Agent :" in coq_code
        or "Parameter Theme :" in coq_code
    ):
        raise SystemExit(
            "web route smoke check failed: directional-instrument Coq drift"
        )
    for fragment in expected["coq_adv"]:
        if fragment not in coq_code:
            raise SystemExit(
                "web route smoke check failed: directional-instrument Adv declaration drift"
            )
    for fragment in expected["forbidden_entity"]:
        if fragment in coq_code:
            raise SystemExit(
                "web route smoke check failed: directional-instrument Entity surrogate drift"
            )
    validate_successful_semantic_reading_contract(case, payload, page)
    expected_page_fragments = [
        'data-verification-scope-kind="registered_construction"',
        'data-verification-level="construction_rule"',
        "<dt>rule</dt><dd>directional_instrument_intransitive_predication</dd>",
        (
            'data-reading-name="'
            "directional_instrument_intransitive_predication_single_reading"
            '"'
        ),
        "<dt>source</dt><dd>directional_instrument_intransitive_predication</dd>",
        f"<dt>scope</dt><dd>{expected['scope']}</dd>",
        expected["translation"],
        (
            "Translation succeeded via construction rule "
            "directional_instrument_intransitive_predication."
        ),
    ]
    require_text_fragments(
        page,
        expected_page_fragments,
        "directional-instrument intransitive HTML",
    )
    if html.escape(sentence, quote=True) not in page:
        raise SystemExit(
            "web route smoke check failed: directional-instrument page input drift"
        )


def validate_analyze_directional_instrument_location_intransitive_success(
    payload: dict,
    page: str,
    sentence: str,
) -> None:
    case = "analyze_directional_instrument_location_intransitive_success"
    expectations = {
        "Mary laughed from a window with a camera beside a shelf": {
            "translation": "laugh(3)(from(window), with(camera), beside(shelf), mary)",
            "modifiers": ["from(window)", "with(camera)", "beside(shelf)"],
            "roles": ["Source", "Instrument", "Location"],
            "source_modifiers": ["from(window)"],
            "goal_modifiers": [],
            "instrument_modifiers": ["with(camera)"],
            "location_modifiers": ["beside(shelf)"],
            "scope": (
                "explicit_agent_with_directional_instrument_and_location_adv_sequence"
            ),
            "coq_adv": [
                "Parameter from_window : Adv.",
                "Parameter with_camera : Adv.",
                "Parameter beside_shelf : Adv.",
            ],
            "forbidden_entity": [
                "Parameter from_window : Entity.",
                "Parameter with_camera : Entity.",
                "Parameter beside_shelf : Entity.",
            ],
            "definition": (
                "Definition example_1 : PropT := (laugh 3 "
                "(mods_cons 2 from_window (mods_cons 1 with_camera "
                "(mods_cons 0 beside_shelf mods_nil))) mary)."
            ),
            "time_modifier": None,
        },
        "Mary laughed from a window with a camera beside a shelf yesterday": {
            "translation": (
                "at_T(yesterday, laugh(3)(from(window), with(camera), "
                "beside(shelf), mary))"
            ),
            "modifiers": ["from(window)", "with(camera)", "beside(shelf)"],
            "roles": ["Source", "Instrument", "Location"],
            "source_modifiers": ["from(window)"],
            "goal_modifiers": [],
            "instrument_modifiers": ["with(camera)"],
            "location_modifiers": ["beside(shelf)"],
            "scope": (
                "explicit_agent_with_directional_instrument_and_location_adv_sequence_at_time"
            ),
            "coq_adv": [
                "Parameter from_window : Adv.",
                "Parameter with_camera : Adv.",
                "Parameter beside_shelf : Adv.",
            ],
            "forbidden_entity": [
                "Parameter from_window : Entity.",
                "Parameter with_camera : Entity.",
                "Parameter beside_shelf : Entity.",
            ],
            "definition": (
                "Definition example_1 : PropT := (at_T yesterday (laugh 3 "
                "(mods_cons 2 from_window (mods_cons 1 with_camera "
                "(mods_cons 0 beside_shelf mods_nil))) mary))."
            ),
            "time_modifier": {"operator": "at", "argument": "yesterday"},
        },
        "Mary laughed into a room with a camera beside a shelf yesterday": {
            "translation": (
                "at_T(yesterday, laugh(3)(into(room), with(camera), "
                "beside(shelf), mary))"
            ),
            "modifiers": ["into(room)", "with(camera)", "beside(shelf)"],
            "roles": ["Goal", "Instrument", "Location"],
            "source_modifiers": [],
            "goal_modifiers": ["into(room)"],
            "instrument_modifiers": ["with(camera)"],
            "location_modifiers": ["beside(shelf)"],
            "scope": (
                "explicit_agent_with_directional_instrument_and_location_adv_sequence_at_time"
            ),
            "coq_adv": [
                "Parameter into_room : Adv.",
                "Parameter with_camera : Adv.",
                "Parameter beside_shelf : Adv.",
            ],
            "forbidden_entity": [
                "Parameter into_room : Entity.",
                "Parameter with_camera : Entity.",
                "Parameter beside_shelf : Entity.",
            ],
            "definition": (
                "Definition example_1 : PropT := (at_T yesterday (laugh 3 "
                "(mods_cons 2 into_room (mods_cons 1 with_camera "
                "(mods_cons 0 beside_shelf mods_nil))) mary))."
            ),
            "time_modifier": {"operator": "at", "argument": "yesterday"},
        },
        (
            "Mary laughed from a window into a room with a camera beside a shelf "
            "yesterday"
        ): {
            "translation": (
                "at_T(yesterday, laugh(4)(from(window), into(room), with(camera), "
                "beside(shelf), mary))"
            ),
            "modifiers": [
                "from(window)",
                "into(room)",
                "with(camera)",
                "beside(shelf)",
            ],
            "roles": ["Source", "Goal", "Instrument", "Location"],
            "source_modifiers": ["from(window)"],
            "goal_modifiers": ["into(room)"],
            "instrument_modifiers": ["with(camera)"],
            "location_modifiers": ["beside(shelf)"],
            "scope": (
                "explicit_agent_with_directional_instrument_and_location_adv_sequence_at_time"
            ),
            "coq_adv": [
                "Parameter from_window : Adv.",
                "Parameter into_room : Adv.",
                "Parameter with_camera : Adv.",
                "Parameter beside_shelf : Adv.",
            ],
            "forbidden_entity": [
                "Parameter from_window : Entity.",
                "Parameter into_room : Entity.",
                "Parameter with_camera : Entity.",
                "Parameter beside_shelf : Entity.",
            ],
            "definition": (
                "Definition example_1 : PropT := (at_T yesterday (laugh 4 "
                "(mods_cons 3 from_window (mods_cons 2 into_room "
                "(mods_cons 1 with_camera (mods_cons 0 beside_shelf mods_nil)))) "
                "mary))."
            ),
            "time_modifier": {"operator": "at", "argument": "yesterday"},
        },
    }
    expected = expectations.get(sentence)
    if expected is None:
        raise SystemExit(
            "web route smoke check failed: unknown directional-instrument-location fixture"
        )
    validate_analyze_success_envelope(
        payload,
        sentence,
        "directional_instrument_location_intransitive_predication",
        ["semantic_readings_check", "construction_hygiene"],
    )
    validate_verification_scope(
        payload,
        page,
        "directional_instrument_location_intransitive_predication",
        "registered_construction",
        "construction_rule",
        "directional_instrument_location_intransitive_predication",
    )
    if payload.get("kind") != "directional_instrument_location_intransitive_predication":
        raise SystemExit(
            "web route smoke check failed: directional-instrument-location kind drift"
        )
    if payload.get("dependent_type_translation") != expected["translation"]:
        raise SystemExit(
            "web route smoke check failed: directional-instrument-location translation drift"
        )
    if "certification_upgrade_plan" in payload or "construction_rule_draft" in payload:
        raise SystemExit(
            "web route smoke check failed: directional-instrument-location exposes fallback draft"
        )
    ast = payload.get("ast")
    application_ast = ast
    if expected["time_modifier"] is not None:
        if (
            not isinstance(ast, dict)
            or ast.get("kind") != "time"
            or ast.get("operator") != expected["time_modifier"]["operator"]
            or ast.get("arguments") != [expected["time_modifier"]["argument"]]
            or not isinstance(ast.get("body"), dict)
        ):
            raise SystemExit(
                "web route smoke check failed: timed directional-instrument-location AST drift"
            )
        application_ast = ast["body"]
    modifier_roles = (
        application_ast.get("modifier_roles", {}).get("roles")
        if isinstance(application_ast, dict)
        else None
    )
    modifier_vector = (
        application_ast.get("modifier_vector", {}).get("items")
        if isinstance(application_ast, dict)
        else None
    )
    role_frame = (
        application_ast.get("role_frame", {}).get("roles")
        if isinstance(application_ast, dict)
        else None
    )
    if (
        not isinstance(application_ast, dict)
        or application_ast.get("kind") != "application"
        or application_ast.get("function") != "laugh"
        or application_ast.get("arguments") != ["mary"]
        or application_ast.get("modifiers") != expected["modifiers"]
        or application_ast.get("adverb_count") != len(expected["modifiers"])
        or not isinstance(role_frame, list)
        or len(role_frame) != 1
        or role_frame[0].get("role") != "Agent"
        or role_frame[0].get("type") != "Entity"
        or role_frame[0].get("source") != "explicit"
        or not isinstance(modifier_roles, list)
        or [role.get("semantic_role") for role in modifier_roles] != expected["roles"]
        or any(role.get("type") != "Adv" for role in modifier_roles)
        or not isinstance(modifier_vector, list)
        or [item.get("tail_length") for item in modifier_vector]
        != list(reversed(range(len(expected["modifiers"]))))
    ):
        raise SystemExit(
            "web route smoke check failed: directional-instrument-location AST drift"
        )
    event_semantics = payload.get("event_semantics")
    typed_predication = (
        event_semantics.get(
            "directional_instrument_location_intransitive_predication"
        )
        if isinstance(event_semantics, dict)
        else None
    )
    if (
        not isinstance(event_semantics, dict)
        or event_semantics.get("analysis")
        != "directional-instrument-location-intransitive-predication"
        or not isinstance(typed_predication, dict)
        or typed_predication.get("predicate") != "laugh"
        or typed_predication.get("agent") != "mary"
        or typed_predication.get("agent_type") != "Entity"
        or typed_predication.get("modifiers") != expected["modifiers"]
        or typed_predication.get("modifier_role_pattern") != expected["roles"]
        or typed_predication.get("source_modifiers") != expected["source_modifiers"]
        or typed_predication.get("goal_modifiers") != expected["goal_modifiers"]
        or typed_predication.get("instrument_modifiers")
        != expected["instrument_modifiers"]
        or typed_predication.get("location_modifiers")
        != expected["location_modifiers"]
        or typed_predication.get("directional_modifier_count")
        != len(expected["source_modifiers"]) + len(expected["goal_modifiers"])
        or typed_predication.get("instrument_modifier_count")
        != len(expected["instrument_modifiers"])
        or typed_predication.get("location_modifier_count")
        != len(expected["location_modifiers"])
    ):
        raise SystemExit(
            "web route smoke check failed: directional-instrument-location analysis drift"
        )
    if expected["time_modifier"] is None:
        if "time_modifier" in typed_predication:
            raise SystemExit(
                "web route smoke check failed: untimed directional-instrument-location time drift"
            )
    elif typed_predication.get("time_modifier") != expected["time_modifier"]:
        raise SystemExit(
            "web route smoke check failed: timed directional-instrument-location time drift"
        )
    hygiene = payload.get("construction_hygiene")
    if not isinstance(hygiene, dict) or hygiene.get("ok") is not True:
        raise SystemExit(
            "web route smoke check failed: directional-instrument-location hygiene drift"
        )
    readings = payload.get("semantic_readings")
    if not isinstance(readings, list) or len(readings) != 1:
        raise SystemExit(
            "web route smoke check failed: directional-instrument-location reading count drift"
        )
    validate_semantic_reading_summary(
        readings[0],
        {
            "name": (
                "directional_instrument_location_intransitive_predication_single_reading"
            ),
            "scope": expected["scope"],
            "source": "directional_instrument_location_intransitive_predication",
            "coq_definition": "example_1",
        },
        "none",
        case,
        expected_type=None,
    )
    coq_code = payload.get("coq_code")
    if (
        not isinstance(coq_code, str)
        or expected["definition"] not in coq_code
        or "Parameter Event : Type." in coq_code
        or "Parameter Agent :" in coq_code
        or "Parameter Theme :" in coq_code
    ):
        raise SystemExit(
            "web route smoke check failed: directional-instrument-location Coq drift"
        )
    for fragment in expected["coq_adv"]:
        if fragment not in coq_code:
            raise SystemExit(
                "web route smoke check failed: directional-instrument-location Adv declaration drift"
            )
    for fragment in expected["forbidden_entity"]:
        if fragment in coq_code:
            raise SystemExit(
                "web route smoke check failed: directional-instrument-location Entity surrogate drift"
            )
    validate_successful_semantic_reading_contract(case, payload, page)
    expected_page_fragments = [
        'data-verification-scope-kind="registered_construction"',
        'data-verification-level="construction_rule"',
        (
            "<dt>rule</dt><dd>"
            "directional_instrument_location_intransitive_predication</dd>"
        ),
        (
            'data-reading-name="'
            "directional_instrument_location_intransitive_predication_single_reading"
            '"'
        ),
        (
            "<dt>source</dt><dd>"
            "directional_instrument_location_intransitive_predication</dd>"
        ),
        f"<dt>scope</dt><dd>{expected['scope']}</dd>",
        expected["translation"],
        (
            "Translation succeeded via construction rule "
            "directional_instrument_location_intransitive_predication."
        ),
    ]
    require_text_fragments(
        page,
        expected_page_fragments,
        "directional-instrument-location intransitive HTML",
    )
    if html.escape(sentence, quote=True) not in page:
        raise SystemExit(
            "web route smoke check failed: directional-instrument-location page input drift"
        )


def validate_analyze_directional_instrument_location_manner_intransitive_success(
    payload: dict,
    page: str,
    sentence: str,
) -> None:
    case = "analyze_directional_instrument_location_manner_intransitive_success"
    expectations = {
        "Mary laughed from a window with a camera beside a shelf loudly": {
            "translation": (
                "laugh(4)(from(window), with(camera), beside(shelf), loudly, mary)"
            ),
            "modifiers": ["from(window)", "with(camera)", "beside(shelf)", "loudly"],
            "roles": ["Source", "Instrument", "Location", "Manner"],
            "source_modifiers": ["from(window)"],
            "goal_modifiers": [],
            "definition": (
                "Definition example_1 : PropT := (laugh 4 "
                "(mods_cons 3 from_window (mods_cons 2 with_camera "
                "(mods_cons 1 beside_shelf (mods_cons 0 loudly mods_nil)))) mary)."
            ),
            "time_modifier": None,
        },
        "Mary laughed from a window with a camera beside a shelf loudly yesterday": {
            "translation": (
                "at_T(yesterday, laugh(4)(from(window), with(camera), "
                "beside(shelf), loudly, mary))"
            ),
            "modifiers": ["from(window)", "with(camera)", "beside(shelf)", "loudly"],
            "roles": ["Source", "Instrument", "Location", "Manner"],
            "source_modifiers": ["from(window)"],
            "goal_modifiers": [],
            "definition": (
                "Definition example_1 : PropT := (at_T yesterday (laugh 4 "
                "(mods_cons 3 from_window (mods_cons 2 with_camera "
                "(mods_cons 1 beside_shelf (mods_cons 0 loudly mods_nil)))) mary))."
            ),
            "time_modifier": {"operator": "at", "argument": "yesterday"},
        },
        "Mary laughed into a room with a camera beside a shelf loudly yesterday": {
            "translation": (
                "at_T(yesterday, laugh(4)(into(room), with(camera), "
                "beside(shelf), loudly, mary))"
            ),
            "modifiers": ["into(room)", "with(camera)", "beside(shelf)", "loudly"],
            "roles": ["Goal", "Instrument", "Location", "Manner"],
            "source_modifiers": [],
            "goal_modifiers": ["into(room)"],
            "definition": (
                "Definition example_1 : PropT := (at_T yesterday (laugh 4 "
                "(mods_cons 3 into_room (mods_cons 2 with_camera "
                "(mods_cons 1 beside_shelf (mods_cons 0 loudly mods_nil)))) mary))."
            ),
            "time_modifier": {"operator": "at", "argument": "yesterday"},
        },
        (
            "Mary laughed from a window into a room with a camera beside a shelf "
            "loudly yesterday"
        ): {
            "translation": (
                "at_T(yesterday, laugh(5)(from(window), into(room), "
                "with(camera), beside(shelf), loudly, mary))"
            ),
            "modifiers": [
                "from(window)",
                "into(room)",
                "with(camera)",
                "beside(shelf)",
                "loudly",
            ],
            "roles": ["Source", "Goal", "Instrument", "Location", "Manner"],
            "source_modifiers": ["from(window)"],
            "goal_modifiers": ["into(room)"],
            "definition": (
                "Definition example_1 : PropT := (at_T yesterday (laugh 5 "
                "(mods_cons 4 from_window (mods_cons 3 into_room "
                "(mods_cons 2 with_camera (mods_cons 1 beside_shelf "
                "(mods_cons 0 loudly mods_nil))))) mary))."
            ),
            "time_modifier": {"operator": "at", "argument": "yesterday"},
        },
    }
    expected = expectations.get(sentence)
    if expected is None:
        raise SystemExit(
            "web route smoke check failed: unknown directional-instrument-location-manner fixture"
        )
    rule_id = "directional_instrument_location_manner_intransitive_predication"
    validate_analyze_success_envelope(
        payload,
        sentence,
        rule_id,
        ["semantic_readings_check", "construction_hygiene"],
    )
    validate_verification_scope(
        payload,
        page,
        rule_id,
        "registered_construction",
        "construction_rule",
        rule_id,
    )
    if payload.get("kind") != rule_id:
        raise SystemExit(
            "web route smoke check failed: directional-instrument-location-manner kind drift"
        )
    if payload.get("dependent_type_translation") != expected["translation"]:
        raise SystemExit(
            "web route smoke check failed: directional-instrument-location-manner translation drift"
        )
    if "certification_upgrade_plan" in payload or "construction_rule_draft" in payload:
        raise SystemExit(
            "web route smoke check failed: directional-instrument-location-manner exposes fallback draft"
        )
    ast = payload.get("ast")
    application_ast = ast
    if expected["time_modifier"] is not None:
        if (
            not isinstance(ast, dict)
            or ast.get("kind") != "time"
            or ast.get("operator") != expected["time_modifier"]["operator"]
            or ast.get("arguments") != [expected["time_modifier"]["argument"]]
            or not isinstance(ast.get("body"), dict)
        ):
            raise SystemExit(
                "web route smoke check failed: timed directional-instrument-location-manner AST drift"
            )
        application_ast = ast["body"]
    modifier_roles = (
        application_ast.get("modifier_roles", {}).get("roles")
        if isinstance(application_ast, dict)
        else None
    )
    modifier_vector = (
        application_ast.get("modifier_vector", {}).get("items")
        if isinstance(application_ast, dict)
        else None
    )
    if (
        not isinstance(application_ast, dict)
        or application_ast.get("kind") != "application"
        or application_ast.get("function") != "laugh"
        or application_ast.get("arguments") != ["mary"]
        or application_ast.get("modifiers") != expected["modifiers"]
        or application_ast.get("adverb_count") != len(expected["modifiers"])
        or not isinstance(modifier_roles, list)
        or [role.get("semantic_role") for role in modifier_roles] != expected["roles"]
        or any(role.get("type") != "Adv" for role in modifier_roles)
        or not isinstance(modifier_vector, list)
        or [item.get("tail_length") for item in modifier_vector]
        != list(reversed(range(len(expected["modifiers"]))))
    ):
        raise SystemExit(
            "web route smoke check failed: directional-instrument-location-manner AST drift"
        )
    event_semantics = payload.get("event_semantics")
    typed_predication = (
        event_semantics.get(rule_id) if isinstance(event_semantics, dict) else None
    )
    instrument_modifiers = ["with(camera)"]
    location_modifiers = ["beside(shelf)"]
    manner_modifiers = ["loudly"]
    if (
        not isinstance(event_semantics, dict)
        or event_semantics.get("analysis")
        != "directional-instrument-location-manner-intransitive-predication"
        or not isinstance(typed_predication, dict)
        or typed_predication.get("predicate") != "laugh"
        or typed_predication.get("agent") != "mary"
        or typed_predication.get("agent_type") != "Entity"
        or typed_predication.get("modifiers") != expected["modifiers"]
        or typed_predication.get("modifier_role_pattern") != expected["roles"]
        or typed_predication.get("source_modifiers") != expected["source_modifiers"]
        or typed_predication.get("goal_modifiers") != expected["goal_modifiers"]
        or typed_predication.get("instrument_modifiers") != instrument_modifiers
        or typed_predication.get("location_modifiers") != location_modifiers
        or typed_predication.get("manner_modifiers") != manner_modifiers
        or typed_predication.get("manner_modifier_count") != 1
    ):
        raise SystemExit(
            "web route smoke check failed: directional-instrument-location-manner analysis drift"
        )
    if expected["time_modifier"] is None:
        if "time_modifier" in typed_predication:
            raise SystemExit(
                "web route smoke check failed: untimed directional-instrument-location-manner time drift"
            )
    elif typed_predication.get("time_modifier") != expected["time_modifier"]:
        raise SystemExit(
            "web route smoke check failed: timed directional-instrument-location-manner time drift"
        )
    readings = payload.get("semantic_readings")
    scope = (
        "explicit_agent_with_directional_instrument_location_and_manner_adv_sequence_at_time"
        if expected["time_modifier"]
        else "explicit_agent_with_directional_instrument_location_and_manner_adv_sequence"
    )
    if not isinstance(readings, list) or len(readings) != 1:
        raise SystemExit(
            "web route smoke check failed: directional-instrument-location-manner reading count drift"
        )
    validate_semantic_reading_summary(
        readings[0],
        {
            "name": (
                "directional_instrument_location_manner_intransitive_predication_single_reading"
            ),
            "scope": scope,
            "source": rule_id,
            "coq_definition": "example_1",
        },
        "none",
        case,
        expected_type=None,
    )
    coq_code = payload.get("coq_code")
    if (
        not isinstance(coq_code, str)
        or expected["definition"] not in coq_code
        or "Parameter Event : Type." in coq_code
        or "Parameter Agent :" in coq_code
        or "Parameter Theme :" in coq_code
    ):
        raise SystemExit(
            "web route smoke check failed: directional-instrument-location-manner Coq drift"
        )
    expected_adv = {
        "from(window)": "Parameter from_window : Adv.",
        "into(room)": "Parameter into_room : Adv.",
        "with(camera)": "Parameter with_camera : Adv.",
        "beside(shelf)": "Parameter beside_shelf : Adv.",
        "loudly": "Parameter loudly : Adv.",
    }
    expected_entity = {
        "from(window)": "Parameter from_window : Entity.",
        "into(room)": "Parameter into_room : Entity.",
        "with(camera)": "Parameter with_camera : Entity.",
        "beside(shelf)": "Parameter beside_shelf : Entity.",
        "loudly": "Parameter loudly : Entity.",
    }
    for modifier in expected["modifiers"]:
        if expected_adv[modifier] not in coq_code:
            raise SystemExit(
                "web route smoke check failed: directional-instrument-location-manner Adv declaration drift"
            )
        if expected_entity[modifier] in coq_code:
            raise SystemExit(
                "web route smoke check failed: directional-instrument-location-manner Entity surrogate drift"
            )
    validate_successful_semantic_reading_contract(case, payload, page)
    expected_page_fragments = [
        'data-verification-scope-kind="registered_construction"',
        'data-verification-level="construction_rule"',
        f"<dt>rule</dt><dd>{rule_id}</dd>",
        (
            'data-reading-name="'
            "directional_instrument_location_manner_intransitive_predication_single_reading"
            '"'
        ),
        f"<dt>source</dt><dd>{rule_id}</dd>",
        f"<dt>scope</dt><dd>{scope}</dd>",
        expected["translation"],
        f"Translation succeeded via construction rule {rule_id}.",
    ]
    require_text_fragments(
        page,
        expected_page_fragments,
        "directional-instrument-location-manner intransitive HTML",
    )
    if html.escape(sentence, quote=True) not in page:
        raise SystemExit(
            "web route smoke check failed: directional-instrument-location-manner page input drift"
        )


def validate_analyze_directional_instrument_two_location_manner_intransitive_success(
    payload: dict,
    page: str,
    sentence: str,
) -> None:
    case = "analyze_directional_instrument_two_location_manner_intransitive_success"
    expectations = {
        (
            "Mary laughed from a window with a camera beside a shelf loudly "
            "under a lamp"
        ): {
            "translation": (
                "laugh(5)(from(window), with(camera), beside(shelf), loudly, "
                "under(lamp), mary)"
            ),
            "modifiers": [
                "from(window)",
                "with(camera)",
                "beside(shelf)",
                "loudly",
                "under(lamp)",
            ],
            "roles": ["Source", "Instrument", "Location", "Manner", "Location"],
            "source_modifiers": ["from(window)"],
            "goal_modifiers": [],
            "definition": (
                "Definition example_1 : PropT := (laugh 5 "
                "(mods_cons 4 from_window (mods_cons 3 with_camera "
                "(mods_cons 2 beside_shelf (mods_cons 1 loudly "
                "(mods_cons 0 under_lamp mods_nil))))) mary)."
            ),
            "time_modifier": None,
        },
        (
            "Mary laughed from a window with a camera beside a shelf loudly "
            "under a lamp yesterday"
        ): {
            "translation": (
                "at_T(yesterday, laugh(5)(from(window), with(camera), "
                "beside(shelf), loudly, under(lamp), mary))"
            ),
            "modifiers": [
                "from(window)",
                "with(camera)",
                "beside(shelf)",
                "loudly",
                "under(lamp)",
            ],
            "roles": ["Source", "Instrument", "Location", "Manner", "Location"],
            "source_modifiers": ["from(window)"],
            "goal_modifiers": [],
            "definition": (
                "Definition example_1 : PropT := (at_T yesterday (laugh 5 "
                "(mods_cons 4 from_window (mods_cons 3 with_camera "
                "(mods_cons 2 beside_shelf (mods_cons 1 loudly "
                "(mods_cons 0 under_lamp mods_nil))))) mary))."
            ),
            "time_modifier": {"operator": "at", "argument": "yesterday"},
        },
        (
            "Mary laughed into a room with a camera beside a shelf loudly "
            "under a lamp yesterday"
        ): {
            "translation": (
                "at_T(yesterday, laugh(5)(into(room), with(camera), "
                "beside(shelf), loudly, under(lamp), mary))"
            ),
            "modifiers": [
                "into(room)",
                "with(camera)",
                "beside(shelf)",
                "loudly",
                "under(lamp)",
            ],
            "roles": ["Goal", "Instrument", "Location", "Manner", "Location"],
            "source_modifiers": [],
            "goal_modifiers": ["into(room)"],
            "definition": (
                "Definition example_1 : PropT := (at_T yesterday (laugh 5 "
                "(mods_cons 4 into_room (mods_cons 3 with_camera "
                "(mods_cons 2 beside_shelf (mods_cons 1 loudly "
                "(mods_cons 0 under_lamp mods_nil))))) mary))."
            ),
            "time_modifier": {"operator": "at", "argument": "yesterday"},
        },
        (
            "Mary laughed from a window into a room with a camera beside a shelf "
            "loudly under a lamp yesterday"
        ): {
            "translation": (
                "at_T(yesterday, laugh(6)(from(window), into(room), "
                "with(camera), beside(shelf), loudly, under(lamp), mary))"
            ),
            "modifiers": [
                "from(window)",
                "into(room)",
                "with(camera)",
                "beside(shelf)",
                "loudly",
                "under(lamp)",
            ],
            "roles": [
                "Source",
                "Goal",
                "Instrument",
                "Location",
                "Manner",
                "Location",
            ],
            "source_modifiers": ["from(window)"],
            "goal_modifiers": ["into(room)"],
            "definition": (
                "Definition example_1 : PropT := (at_T yesterday (laugh 6 "
                "(mods_cons 5 from_window (mods_cons 4 into_room "
                "(mods_cons 3 with_camera (mods_cons 2 beside_shelf "
                "(mods_cons 1 loudly (mods_cons 0 under_lamp mods_nil)))))) "
                "mary))."
            ),
            "time_modifier": {"operator": "at", "argument": "yesterday"},
        },
    }
    expected = expectations.get(sentence)
    if expected is None:
        raise SystemExit(
            "web route smoke check failed: unknown directional-instrument-two-location-manner fixture"
        )
    rule_id = "directional_instrument_two_location_manner_intransitive_predication"
    validate_analyze_success_envelope(
        payload,
        sentence,
        rule_id,
        ["semantic_readings_check", "construction_hygiene"],
    )
    validate_verification_scope(
        payload,
        page,
        rule_id,
        "registered_construction",
        "construction_rule",
        rule_id,
    )
    if payload.get("kind") != rule_id:
        raise SystemExit(
            "web route smoke check failed: directional-instrument-two-location-manner kind drift"
        )
    if payload.get("dependent_type_translation") != expected["translation"]:
        raise SystemExit(
            "web route smoke check failed: directional-instrument-two-location-manner translation drift"
        )
    if "certification_upgrade_plan" in payload or "construction_rule_draft" in payload:
        raise SystemExit(
            "web route smoke check failed: directional-instrument-two-location-manner exposes fallback draft"
        )

    ast = payload.get("ast")
    application_ast = ast
    if expected["time_modifier"] is not None:
        if (
            not isinstance(ast, dict)
            or ast.get("kind") != "time"
            or ast.get("operator") != expected["time_modifier"]["operator"]
            or ast.get("arguments") != [expected["time_modifier"]["argument"]]
            or not isinstance(ast.get("body"), dict)
        ):
            raise SystemExit(
                "web route smoke check failed: timed directional-instrument-two-location-manner AST drift"
            )
        application_ast = ast["body"]
    modifier_roles = (
        application_ast.get("modifier_roles", {}).get("roles")
        if isinstance(application_ast, dict)
        else None
    )
    modifier_vector = (
        application_ast.get("modifier_vector", {}).get("items")
        if isinstance(application_ast, dict)
        else None
    )
    if (
        not isinstance(application_ast, dict)
        or application_ast.get("kind") != "application"
        or application_ast.get("function") != "laugh"
        or application_ast.get("arguments") != ["mary"]
        or application_ast.get("modifiers") != expected["modifiers"]
        or application_ast.get("adverb_count") != len(expected["modifiers"])
        or not isinstance(modifier_roles, list)
        or [role.get("semantic_role") for role in modifier_roles] != expected["roles"]
        or any(role.get("type") != "Adv" for role in modifier_roles)
        or not isinstance(modifier_vector, list)
        or [item.get("tail_length") for item in modifier_vector]
        != list(reversed(range(len(expected["modifiers"]))))
    ):
        raise SystemExit(
            "web route smoke check failed: directional-instrument-two-location-manner AST drift"
        )

    event_semantics = payload.get("event_semantics")
    typed_predication = (
        event_semantics.get(rule_id) if isinstance(event_semantics, dict) else None
    )
    if (
        not isinstance(event_semantics, dict)
        or event_semantics.get("analysis")
        != "directional-instrument-two-location-manner-intransitive-predication"
        or not isinstance(typed_predication, dict)
        or typed_predication.get("predicate") != "laugh"
        or typed_predication.get("agent") != "mary"
        or typed_predication.get("agent_type") != "Entity"
        or typed_predication.get("modifiers") != expected["modifiers"]
        or typed_predication.get("modifier_role_pattern") != expected["roles"]
        or typed_predication.get("source_modifiers") != expected["source_modifiers"]
        or typed_predication.get("goal_modifiers") != expected["goal_modifiers"]
        or typed_predication.get("instrument_modifiers") != ["with(camera)"]
        or typed_predication.get("location_modifiers")
        != ["beside(shelf)", "under(lamp)"]
        or typed_predication.get("location_modifier_count") != 2
        or typed_predication.get("manner_modifiers") != ["loudly"]
        or typed_predication.get("manner_modifier_count") != 1
    ):
        raise SystemExit(
            "web route smoke check failed: directional-instrument-two-location-manner analysis drift"
        )
    if expected["time_modifier"] is None:
        if "time_modifier" in typed_predication:
            raise SystemExit(
                "web route smoke check failed: untimed directional-instrument-two-location-manner time drift"
            )
    elif typed_predication.get("time_modifier") != expected["time_modifier"]:
        raise SystemExit(
            "web route smoke check failed: timed directional-instrument-two-location-manner time drift"
        )

    scope = (
        "explicit_agent_with_directional_instrument_two_location_and_manner_adv_sequence_at_time"
        if expected["time_modifier"]
        else "explicit_agent_with_directional_instrument_two_location_and_manner_adv_sequence"
    )
    readings = payload.get("semantic_readings")
    if not isinstance(readings, list) or len(readings) != 1:
        raise SystemExit(
            "web route smoke check failed: directional-instrument-two-location-manner reading count drift"
        )
    validate_semantic_reading_summary(
        readings[0],
        {
            "name": (
                "directional_instrument_two_location_manner_intransitive_predication_single_reading"
            ),
            "scope": scope,
            "source": rule_id,
            "coq_definition": "example_1",
        },
        "none",
        case,
        expected_type=None,
    )
    coq_code = payload.get("coq_code")
    if (
        not isinstance(coq_code, str)
        or expected["definition"] not in coq_code
        or "Parameter Event : Type." in coq_code
        or "Parameter Agent :" in coq_code
        or "Parameter Theme :" in coq_code
    ):
        raise SystemExit(
            "web route smoke check failed: directional-instrument-two-location-manner Coq drift"
        )
    expected_adv = {
        "from(window)": "Parameter from_window : Adv.",
        "into(room)": "Parameter into_room : Adv.",
        "with(camera)": "Parameter with_camera : Adv.",
        "beside(shelf)": "Parameter beside_shelf : Adv.",
        "loudly": "Parameter loudly : Adv.",
        "under(lamp)": "Parameter under_lamp : Adv.",
    }
    expected_entity = {
        "from(window)": "Parameter from_window : Entity.",
        "into(room)": "Parameter into_room : Entity.",
        "with(camera)": "Parameter with_camera : Entity.",
        "beside(shelf)": "Parameter beside_shelf : Entity.",
        "loudly": "Parameter loudly : Entity.",
        "under(lamp)": "Parameter under_lamp : Entity.",
    }
    for modifier in expected["modifiers"]:
        if expected_adv[modifier] not in coq_code:
            raise SystemExit(
                "web route smoke check failed: directional-instrument-two-location-manner Adv declaration drift"
            )
        if expected_entity[modifier] in coq_code:
            raise SystemExit(
                "web route smoke check failed: directional-instrument-two-location-manner Entity surrogate drift"
            )
    validate_successful_semantic_reading_contract(case, payload, page)
    expected_page_fragments = [
        'data-verification-scope-kind="registered_construction"',
        'data-verification-level="construction_rule"',
        f"<dt>rule</dt><dd>{rule_id}</dd>",
        (
            'data-reading-name="'
            "directional_instrument_two_location_manner_intransitive_predication_single_reading"
            '"'
        ),
        f"<dt>source</dt><dd>{rule_id}</dd>",
        f"<dt>scope</dt><dd>{scope}</dd>",
        expected["translation"],
        f"Translation succeeded via construction rule {rule_id}.",
    ]
    require_text_fragments(
        page,
        expected_page_fragments,
        "directional-instrument-two-location-manner intransitive HTML",
    )
    if html.escape(sentence, quote=True) not in page:
        raise SystemExit(
            "web route smoke check failed: directional-instrument-two-location-manner page input drift"
        )


def validate_analyze_directional_instrument_location_manner_location_sequence_success(
    payload: dict,
    page: str,
    sentence: str,
) -> None:
    case = "analyze_directional_instrument_location_manner_location_sequence_success"
    expectations = {
        (
            "Mary laughed from a window with a camera beside a shelf loudly "
            "under a lamp on a table"
        ): {
            "translation": (
                "laugh(6)(from(window), with(camera), beside(shelf), loudly, "
                "under(lamp), on(table), mary)"
            ),
            "modifiers": [
                "from(window)",
                "with(camera)",
                "beside(shelf)",
                "loudly",
                "under(lamp)",
                "on(table)",
            ],
            "roles": [
                "Source",
                "Instrument",
                "Location",
                "Manner",
                "Location",
                "Location",
            ],
            "source_modifiers": ["from(window)"],
            "goal_modifiers": [],
            "post_manner_locations": ["under(lamp)", "on(table)"],
            "time_modifier": None,
        },
        (
            "Mary laughed from a window with a camera beside a shelf loudly "
            "under a lamp on a table yesterday"
        ): {
            "translation": (
                "at_T(yesterday, laugh(6)(from(window), with(camera), "
                "beside(shelf), loudly, under(lamp), on(table), mary))"
            ),
            "modifiers": [
                "from(window)",
                "with(camera)",
                "beside(shelf)",
                "loudly",
                "under(lamp)",
                "on(table)",
            ],
            "roles": [
                "Source",
                "Instrument",
                "Location",
                "Manner",
                "Location",
                "Location",
            ],
            "source_modifiers": ["from(window)"],
            "goal_modifiers": [],
            "post_manner_locations": ["under(lamp)", "on(table)"],
            "time_modifier": {"operator": "at", "argument": "yesterday"},
        },
        (
            "Mary laughed into a room with a camera beside a shelf loudly "
            "under a lamp on a table yesterday"
        ): {
            "translation": (
                "at_T(yesterday, laugh(6)(into(room), with(camera), "
                "beside(shelf), loudly, under(lamp), on(table), mary))"
            ),
            "modifiers": [
                "into(room)",
                "with(camera)",
                "beside(shelf)",
                "loudly",
                "under(lamp)",
                "on(table)",
            ],
            "roles": [
                "Goal",
                "Instrument",
                "Location",
                "Manner",
                "Location",
                "Location",
            ],
            "source_modifiers": [],
            "goal_modifiers": ["into(room)"],
            "post_manner_locations": ["under(lamp)", "on(table)"],
            "time_modifier": {"operator": "at", "argument": "yesterday"},
        },
        (
            "Mary laughed from a window into a room with a camera beside a shelf "
            "loudly under a lamp on a table yesterday"
        ): {
            "translation": (
                "at_T(yesterday, laugh(7)(from(window), into(room), "
                "with(camera), beside(shelf), loudly, under(lamp), on(table), "
                "mary))"
            ),
            "modifiers": [
                "from(window)",
                "into(room)",
                "with(camera)",
                "beside(shelf)",
                "loudly",
                "under(lamp)",
                "on(table)",
            ],
            "roles": [
                "Source",
                "Goal",
                "Instrument",
                "Location",
                "Manner",
                "Location",
                "Location",
            ],
            "source_modifiers": ["from(window)"],
            "goal_modifiers": ["into(room)"],
            "post_manner_locations": ["under(lamp)", "on(table)"],
            "time_modifier": {"operator": "at", "argument": "yesterday"},
        },
        (
            "Mary laughed from a window with a camera beside a shelf loudly "
            "under a lamp on a table near a door yesterday"
        ): {
            "translation": (
                "at_T(yesterday, laugh(7)(from(window), with(camera), "
                "beside(shelf), loudly, under(lamp), on(table), near(door), "
                "mary))"
            ),
            "modifiers": [
                "from(window)",
                "with(camera)",
                "beside(shelf)",
                "loudly",
                "under(lamp)",
                "on(table)",
                "near(door)",
            ],
            "roles": [
                "Source",
                "Instrument",
                "Location",
                "Manner",
                "Location",
                "Location",
                "Location",
            ],
            "source_modifiers": ["from(window)"],
            "goal_modifiers": [],
            "post_manner_locations": ["under(lamp)", "on(table)", "near(door)"],
            "time_modifier": {"operator": "at", "argument": "yesterday"},
        },
    }
    expected = expectations.get(sentence)
    if expected is None:
        raise SystemExit(
            "web route smoke check failed: unknown directional-instrument-location-manner-location-sequence fixture"
        )
    rule_id = (
        "directional_instrument_location_manner_location_sequence_intransitive_predication"
    )
    validate_analyze_success_envelope(
        payload,
        sentence,
        rule_id,
        ["semantic_readings_check", "construction_hygiene"],
    )
    validate_verification_scope(
        payload,
        page,
        rule_id,
        "registered_construction",
        "construction_rule",
        rule_id,
    )
    if payload.get("kind") != rule_id:
        raise SystemExit(
            "web route smoke check failed: directional-instrument-location-manner-location-sequence kind drift"
        )
    if payload.get("dependent_type_translation") != expected["translation"]:
        raise SystemExit(
            "web route smoke check failed: directional-instrument-location-manner-location-sequence translation drift"
        )
    if "certification_upgrade_plan" in payload or "construction_rule_draft" in payload:
        raise SystemExit(
            "web route smoke check failed: directional-instrument-location-manner-location-sequence exposes fallback draft"
        )

    ast = payload.get("ast")
    application_ast = ast
    if expected["time_modifier"] is not None:
        if (
            not isinstance(ast, dict)
            or ast.get("kind") != "time"
            or ast.get("operator") != expected["time_modifier"]["operator"]
            or ast.get("arguments") != [expected["time_modifier"]["argument"]]
            or not isinstance(ast.get("body"), dict)
        ):
            raise SystemExit(
                "web route smoke check failed: timed directional-instrument-location-manner-location-sequence AST drift"
            )
        application_ast = ast["body"]
    modifier_roles = (
        application_ast.get("modifier_roles", {}).get("roles")
        if isinstance(application_ast, dict)
        else None
    )
    modifier_vector = (
        application_ast.get("modifier_vector", {}).get("items")
        if isinstance(application_ast, dict)
        else None
    )
    if (
        not isinstance(application_ast, dict)
        or application_ast.get("kind") != "application"
        or application_ast.get("function") != "laugh"
        or application_ast.get("arguments") != ["mary"]
        or application_ast.get("modifiers") != expected["modifiers"]
        or application_ast.get("adverb_count") != len(expected["modifiers"])
        or not isinstance(modifier_roles, list)
        or [role.get("semantic_role") for role in modifier_roles] != expected["roles"]
        or any(role.get("type") != "Adv" for role in modifier_roles)
        or not isinstance(modifier_vector, list)
        or [item.get("tail_length") for item in modifier_vector]
        != list(reversed(range(len(expected["modifiers"]))))
    ):
        raise SystemExit(
            "web route smoke check failed: directional-instrument-location-manner-location-sequence AST drift"
        )

    event_semantics = payload.get("event_semantics")
    typed_predication = (
        event_semantics.get(rule_id) if isinstance(event_semantics, dict) else None
    )
    if (
        not isinstance(event_semantics, dict)
        or event_semantics.get("analysis")
        != "directional-instrument-location-manner-location-sequence-intransitive-predication"
        or not isinstance(typed_predication, dict)
        or typed_predication.get("predicate") != "laugh"
        or typed_predication.get("agent") != "mary"
        or typed_predication.get("agent_type") != "Entity"
        or typed_predication.get("modifiers") != expected["modifiers"]
        or typed_predication.get("modifier_role_pattern") != expected["roles"]
        or typed_predication.get("source_modifiers") != expected["source_modifiers"]
        or typed_predication.get("goal_modifiers") != expected["goal_modifiers"]
        or typed_predication.get("instrument_modifiers") != ["with(camera)"]
        or typed_predication.get("pre_manner_location_modifiers") != ["beside(shelf)"]
        or typed_predication.get("post_manner_location_modifiers")
        != expected["post_manner_locations"]
        or typed_predication.get("post_manner_location_modifier_count")
        != len(expected["post_manner_locations"])
        or typed_predication.get("manner_modifiers") != ["loudly"]
    ):
        raise SystemExit(
            "web route smoke check failed: directional-instrument-location-manner-location-sequence analysis drift"
        )
    if expected["time_modifier"] is None:
        if "time_modifier" in typed_predication:
            raise SystemExit(
                "web route smoke check failed: untimed directional-instrument-location-manner-location-sequence time drift"
            )
    elif typed_predication.get("time_modifier") != expected["time_modifier"]:
        raise SystemExit(
            "web route smoke check failed: timed directional-instrument-location-manner-location-sequence time drift"
        )

    scope = (
        "explicit_agent_with_directional_instrument_location_manner_location_sequence_at_time"
        if expected["time_modifier"]
        else "explicit_agent_with_directional_instrument_location_manner_location_sequence"
    )
    readings = payload.get("semantic_readings")
    if not isinstance(readings, list) or len(readings) != 1:
        raise SystemExit(
            "web route smoke check failed: directional-instrument-location-manner-location-sequence reading count drift"
        )
    validate_semantic_reading_summary(
        readings[0],
        {
            "name": (
                "directional_instrument_location_manner_location_sequence_intransitive_predication_single_reading"
            ),
            "scope": scope,
            "source": rule_id,
            "coq_definition": "example_1",
        },
        "none",
        case,
        expected_type=None,
    )
    coq_code = payload.get("coq_code")
    if (
        not isinstance(coq_code, str)
        or "Parameter Event : Type." in coq_code
        or "Parameter Agent :" in coq_code
        or "Parameter Theme :" in coq_code
    ):
        raise SystemExit(
            "web route smoke check failed: directional-instrument-location-manner-location-sequence Coq drift"
        )
    expected_adv = {
        "from(window)": "Parameter from_window : Adv.",
        "into(room)": "Parameter into_room : Adv.",
        "with(camera)": "Parameter with_camera : Adv.",
        "beside(shelf)": "Parameter beside_shelf : Adv.",
        "loudly": "Parameter loudly : Adv.",
        "under(lamp)": "Parameter under_lamp : Adv.",
        "on(table)": "Parameter on_table : Adv.",
        "near(door)": "Parameter near_door : Adv.",
    }
    expected_entity = {
        "from(window)": "Parameter from_window : Entity.",
        "into(room)": "Parameter into_room : Entity.",
        "with(camera)": "Parameter with_camera : Entity.",
        "beside(shelf)": "Parameter beside_shelf : Entity.",
        "loudly": "Parameter loudly : Entity.",
        "under(lamp)": "Parameter under_lamp : Entity.",
        "on(table)": "Parameter on_table : Entity.",
        "near(door)": "Parameter near_door : Entity.",
    }
    for modifier in expected["modifiers"]:
        if expected_adv[modifier] not in coq_code:
            raise SystemExit(
                "web route smoke check failed: directional-instrument-location-manner-location-sequence Adv declaration drift"
            )
        if expected_entity[modifier] in coq_code:
            raise SystemExit(
                "web route smoke check failed: directional-instrument-location-manner-location-sequence Entity surrogate drift"
            )
    validate_successful_semantic_reading_contract(case, payload, page)
    expected_page_fragments = [
        'data-verification-scope-kind="registered_construction"',
        'data-verification-level="construction_rule"',
        f"<dt>rule</dt><dd>{rule_id}</dd>",
        (
            'data-reading-name="'
            "directional_instrument_location_manner_location_sequence_intransitive_predication_single_reading"
            '"'
        ),
        f"<dt>source</dt><dd>{rule_id}</dd>",
        f"<dt>scope</dt><dd>{scope}</dd>",
        expected["translation"],
        f"Translation succeeded via construction rule {rule_id}.",
    ]
    require_text_fragments(
        page,
        expected_page_fragments,
        "directional-instrument-location-manner-location-sequence intransitive HTML",
    )
    if html.escape(sentence, quote=True) not in page:
        raise SystemExit(
            "web route smoke check failed: directional-instrument-location-manner-location-sequence page input drift"
        )


def validate_analyze_directional_instrument_location_manner_location_sequence_instrument_tail_success(
    payload: dict,
    page: str,
    sentence: str,
) -> None:
    case = (
        "analyze_directional_instrument_location_manner_location_sequence_instrument_tail_success"
    )
    expectations = {
        (
            "Mary laughed from a window with a camera beside a shelf loudly "
            "under a lamp on a table with a microphone"
        ): {
            "translation": (
                "laugh(7)(from(window), with(camera), beside(shelf), loudly, "
                "under(lamp), on(table), with(microphone), mary)"
            ),
            "modifiers": [
                "from(window)",
                "with(camera)",
                "beside(shelf)",
                "loudly",
                "under(lamp)",
                "on(table)",
                "with(microphone)",
            ],
            "roles": [
                "Source",
                "Instrument",
                "Location",
                "Manner",
                "Location",
                "Location",
                "Instrument",
            ],
            "source_modifiers": ["from(window)"],
            "goal_modifiers": [],
            "post_manner_locations": ["under(lamp)", "on(table)"],
            "instrument_tail": ["with(microphone)"],
            "time_modifier": None,
        },
        (
            "Mary laughed from a window with a camera beside a shelf loudly "
            "under a lamp on a table with a microphone yesterday"
        ): {
            "translation": (
                "at_T(yesterday, laugh(7)(from(window), with(camera), "
                "beside(shelf), loudly, under(lamp), on(table), "
                "with(microphone), mary))"
            ),
            "modifiers": [
                "from(window)",
                "with(camera)",
                "beside(shelf)",
                "loudly",
                "under(lamp)",
                "on(table)",
                "with(microphone)",
            ],
            "roles": [
                "Source",
                "Instrument",
                "Location",
                "Manner",
                "Location",
                "Location",
                "Instrument",
            ],
            "source_modifiers": ["from(window)"],
            "goal_modifiers": [],
            "post_manner_locations": ["under(lamp)", "on(table)"],
            "instrument_tail": ["with(microphone)"],
            "time_modifier": {"operator": "at", "argument": "yesterday"},
        },
        (
            "Mary laughed into a room with a camera beside a shelf loudly "
            "under a lamp on a table with a microphone yesterday"
        ): {
            "translation": (
                "at_T(yesterday, laugh(7)(into(room), with(camera), "
                "beside(shelf), loudly, under(lamp), on(table), "
                "with(microphone), mary))"
            ),
            "modifiers": [
                "into(room)",
                "with(camera)",
                "beside(shelf)",
                "loudly",
                "under(lamp)",
                "on(table)",
                "with(microphone)",
            ],
            "roles": [
                "Goal",
                "Instrument",
                "Location",
                "Manner",
                "Location",
                "Location",
                "Instrument",
            ],
            "source_modifiers": [],
            "goal_modifiers": ["into(room)"],
            "post_manner_locations": ["under(lamp)", "on(table)"],
            "instrument_tail": ["with(microphone)"],
            "time_modifier": {"operator": "at", "argument": "yesterday"},
        },
        (
            "Mary laughed from a window into a room with a camera beside a shelf "
            "loudly under a lamp on a table with a microphone yesterday"
        ): {
            "translation": (
                "at_T(yesterday, laugh(8)(from(window), into(room), "
                "with(camera), beside(shelf), loudly, under(lamp), on(table), "
                "with(microphone), mary))"
            ),
            "modifiers": [
                "from(window)",
                "into(room)",
                "with(camera)",
                "beside(shelf)",
                "loudly",
                "under(lamp)",
                "on(table)",
                "with(microphone)",
            ],
            "roles": [
                "Source",
                "Goal",
                "Instrument",
                "Location",
                "Manner",
                "Location",
                "Location",
                "Instrument",
            ],
            "source_modifiers": ["from(window)"],
            "goal_modifiers": ["into(room)"],
            "post_manner_locations": ["under(lamp)", "on(table)"],
            "instrument_tail": ["with(microphone)"],
            "time_modifier": {"operator": "at", "argument": "yesterday"},
        },
        (
            "Mary laughed from a window with a camera beside a shelf loudly "
            "under a lamp on a table near a door with a microphone yesterday"
        ): {
            "translation": (
                "at_T(yesterday, laugh(8)(from(window), with(camera), "
                "beside(shelf), loudly, under(lamp), on(table), near(door), "
                "with(microphone), mary))"
            ),
            "modifiers": [
                "from(window)",
                "with(camera)",
                "beside(shelf)",
                "loudly",
                "under(lamp)",
                "on(table)",
                "near(door)",
                "with(microphone)",
            ],
            "roles": [
                "Source",
                "Instrument",
                "Location",
                "Manner",
                "Location",
                "Location",
                "Location",
                "Instrument",
            ],
            "source_modifiers": ["from(window)"],
            "goal_modifiers": [],
            "post_manner_locations": ["under(lamp)", "on(table)", "near(door)"],
            "instrument_tail": ["with(microphone)"],
            "time_modifier": {"operator": "at", "argument": "yesterday"},
        },
    }
    expected = expectations.get(sentence)
    if expected is None:
        raise SystemExit(
            "web route smoke check failed: unknown directional-instrument-location-manner-location-sequence-instrument-tail fixture"
        )
    rule_id = (
        "directional_instrument_location_manner_location_sequence_instrument_tail_intransitive_predication"
    )
    validate_analyze_success_envelope(
        payload,
        sentence,
        rule_id,
        ["semantic_readings_check", "construction_hygiene"],
    )
    validate_verification_scope(
        payload,
        page,
        rule_id,
        "registered_construction",
        "construction_rule",
        rule_id,
    )
    if payload.get("kind") != rule_id:
        raise SystemExit(
            "web route smoke check failed: directional-instrument-location-manner-location-sequence-instrument-tail kind drift"
        )
    if payload.get("dependent_type_translation") != expected["translation"]:
        raise SystemExit(
            "web route smoke check failed: directional-instrument-location-manner-location-sequence-instrument-tail translation drift"
        )
    if "certification_upgrade_plan" in payload or "construction_rule_draft" in payload:
        raise SystemExit(
            "web route smoke check failed: directional-instrument-location-manner-location-sequence-instrument-tail exposes fallback draft"
        )

    ast = payload.get("ast")
    application_ast = ast
    if expected["time_modifier"] is not None:
        if (
            not isinstance(ast, dict)
            or ast.get("kind") != "time"
            or ast.get("operator") != expected["time_modifier"]["operator"]
            or ast.get("arguments") != [expected["time_modifier"]["argument"]]
            or not isinstance(ast.get("body"), dict)
        ):
            raise SystemExit(
                "web route smoke check failed: timed directional-instrument-location-manner-location-sequence-instrument-tail AST drift"
            )
        application_ast = ast["body"]
    modifier_roles = (
        application_ast.get("modifier_roles", {}).get("roles")
        if isinstance(application_ast, dict)
        else None
    )
    modifier_vector = (
        application_ast.get("modifier_vector", {}).get("items")
        if isinstance(application_ast, dict)
        else None
    )
    if (
        not isinstance(application_ast, dict)
        or application_ast.get("kind") != "application"
        or application_ast.get("function") != "laugh"
        or application_ast.get("arguments") != ["mary"]
        or application_ast.get("modifiers") != expected["modifiers"]
        or application_ast.get("adverb_count") != len(expected["modifiers"])
        or not isinstance(modifier_roles, list)
        or [role.get("semantic_role") for role in modifier_roles] != expected["roles"]
        or any(role.get("type") != "Adv" for role in modifier_roles)
        or not isinstance(modifier_vector, list)
        or [item.get("tail_length") for item in modifier_vector]
        != list(reversed(range(len(expected["modifiers"]))))
    ):
        raise SystemExit(
            "web route smoke check failed: directional-instrument-location-manner-location-sequence-instrument-tail AST drift"
        )

    event_semantics = payload.get("event_semantics")
    typed_predication = (
        event_semantics.get(rule_id) if isinstance(event_semantics, dict) else None
    )
    if (
        not isinstance(event_semantics, dict)
        or event_semantics.get("analysis")
        != "directional-instrument-location-manner-location-sequence-instrument-tail-intransitive-predication"
        or not isinstance(typed_predication, dict)
        or typed_predication.get("predicate") != "laugh"
        or typed_predication.get("agent") != "mary"
        or typed_predication.get("agent_type") != "Entity"
        or typed_predication.get("modifiers") != expected["modifiers"]
        or typed_predication.get("modifier_role_pattern") != expected["roles"]
        or typed_predication.get("source_modifiers") != expected["source_modifiers"]
        or typed_predication.get("goal_modifiers") != expected["goal_modifiers"]
        or typed_predication.get("initial_instrument_modifiers") != ["with(camera)"]
        or typed_predication.get("instrument_tail_modifiers")
        != expected["instrument_tail"]
        or typed_predication.get("instrument_tail_modifier_count")
        != len(expected["instrument_tail"])
        or typed_predication.get("pre_manner_location_modifiers") != ["beside(shelf)"]
        or typed_predication.get("post_manner_location_modifiers")
        != expected["post_manner_locations"]
        or typed_predication.get("post_manner_location_modifier_count")
        != len(expected["post_manner_locations"])
        or typed_predication.get("manner_modifiers") != ["loudly"]
    ):
        raise SystemExit(
            "web route smoke check failed: directional-instrument-location-manner-location-sequence-instrument-tail analysis drift"
        )
    if expected["time_modifier"] is None:
        if "time_modifier" in typed_predication:
            raise SystemExit(
                "web route smoke check failed: untimed directional-instrument-location-manner-location-sequence-instrument-tail time drift"
            )
    elif typed_predication.get("time_modifier") != expected["time_modifier"]:
        raise SystemExit(
            "web route smoke check failed: timed directional-instrument-location-manner-location-sequence-instrument-tail time drift"
        )

    scope = (
        "explicit_agent_with_directional_instrument_location_manner_location_sequence_instrument_tail_at_time"
        if expected["time_modifier"]
        else "explicit_agent_with_directional_instrument_location_manner_location_sequence_instrument_tail"
    )
    readings = payload.get("semantic_readings")
    if not isinstance(readings, list) or len(readings) != 1:
        raise SystemExit(
            "web route smoke check failed: directional-instrument-location-manner-location-sequence-instrument-tail reading count drift"
        )
    validate_semantic_reading_summary(
        readings[0],
        {
            "name": (
                "directional_instrument_location_manner_location_sequence_instrument_tail_intransitive_predication_single_reading"
            ),
            "scope": scope,
            "source": rule_id,
            "coq_definition": "example_1",
        },
        "none",
        case,
        expected_type=None,
    )
    coq_code = payload.get("coq_code")
    if (
        not isinstance(coq_code, str)
        or "Parameter Event : Type." in coq_code
        or "Parameter Agent :" in coq_code
        or "Parameter Theme :" in coq_code
    ):
        raise SystemExit(
            "web route smoke check failed: directional-instrument-location-manner-location-sequence-instrument-tail Coq drift"
        )
    expected_adv = {
        "from(window)": "Parameter from_window : Adv.",
        "into(room)": "Parameter into_room : Adv.",
        "with(camera)": "Parameter with_camera : Adv.",
        "beside(shelf)": "Parameter beside_shelf : Adv.",
        "loudly": "Parameter loudly : Adv.",
        "under(lamp)": "Parameter under_lamp : Adv.",
        "on(table)": "Parameter on_table : Adv.",
        "near(door)": "Parameter near_door : Adv.",
        "with(microphone)": "Parameter with_microphone : Adv.",
    }
    expected_entity = {
        "from(window)": "Parameter from_window : Entity.",
        "into(room)": "Parameter into_room : Entity.",
        "with(camera)": "Parameter with_camera : Entity.",
        "beside(shelf)": "Parameter beside_shelf : Entity.",
        "loudly": "Parameter loudly : Entity.",
        "under(lamp)": "Parameter under_lamp : Entity.",
        "on(table)": "Parameter on_table : Entity.",
        "near(door)": "Parameter near_door : Entity.",
        "with(microphone)": "Parameter with_microphone : Entity.",
    }
    for modifier in expected["modifiers"]:
        if expected_adv[modifier] not in coq_code:
            raise SystemExit(
                "web route smoke check failed: directional-instrument-location-manner-location-sequence-instrument-tail Adv declaration drift"
            )
        if expected_entity[modifier] in coq_code:
            raise SystemExit(
                "web route smoke check failed: directional-instrument-location-manner-location-sequence-instrument-tail Entity surrogate drift"
            )
    validate_successful_semantic_reading_contract(case, payload, page)
    expected_page_fragments = [
        'data-verification-scope-kind="registered_construction"',
        'data-verification-level="construction_rule"',
        f"<dt>rule</dt><dd>{rule_id}</dd>",
        (
            'data-reading-name="'
            "directional_instrument_location_manner_location_sequence_instrument_tail_intransitive_predication_single_reading"
            '"'
        ),
        f"<dt>source</dt><dd>{rule_id}</dd>",
        f"<dt>scope</dt><dd>{scope}</dd>",
        expected["translation"],
        f"Translation succeeded via construction rule {rule_id}.",
    ]
    require_text_fragments(
        page,
        expected_page_fragments,
        "directional-instrument-location-manner-location-sequence-instrument-tail intransitive HTML",
    )
    if html.escape(sentence, quote=True) not in page:
        raise SystemExit(
            "web route smoke check failed: directional-instrument-location-manner-location-sequence-instrument-tail page input drift"
        )


def validate_analyze_directional_instrument_location_manner_location_sequence_instrument_location_tail_success(
    payload: dict,
    page: str,
    sentence: str,
) -> None:
    case = "analyze_directional_instrument_location_manner_location_sequence_instrument_location_tail_success"
    expectations = {
        (
            "Mary laughed from a window with a camera beside a shelf loudly "
            "under a lamp on a table with a microphone near a door"
        ): {
            "translation": (
                "laugh(8)(from(window), with(camera), beside(shelf), loudly, "
                "under(lamp), on(table), with(microphone), near(door), mary)"
            ),
            "modifiers": [
                "from(window)",
                "with(camera)",
                "beside(shelf)",
                "loudly",
                "under(lamp)",
                "on(table)",
                "with(microphone)",
                "near(door)",
            ],
            "roles": [
                "Source",
                "Instrument",
                "Location",
                "Manner",
                "Location",
                "Location",
                "Instrument",
                "Location",
            ],
            "source_modifiers": ["from(window)"],
            "goal_modifiers": [],
            "post_manner_locations": ["under(lamp)", "on(table)"],
            "instrument_tail": ["with(microphone)"],
            "final_location_tail": ["near(door)"],
            "time_modifier": None,
        },
        (
            "Mary laughed from a window with a camera beside a shelf loudly "
            "under a lamp on a table with a microphone near a door yesterday"
        ): {
            "translation": (
                "at_T(yesterday, laugh(8)(from(window), with(camera), "
                "beside(shelf), loudly, under(lamp), on(table), "
                "with(microphone), near(door), mary))"
            ),
            "modifiers": [
                "from(window)",
                "with(camera)",
                "beside(shelf)",
                "loudly",
                "under(lamp)",
                "on(table)",
                "with(microphone)",
                "near(door)",
            ],
            "roles": [
                "Source",
                "Instrument",
                "Location",
                "Manner",
                "Location",
                "Location",
                "Instrument",
                "Location",
            ],
            "source_modifiers": ["from(window)"],
            "goal_modifiers": [],
            "post_manner_locations": ["under(lamp)", "on(table)"],
            "instrument_tail": ["with(microphone)"],
            "final_location_tail": ["near(door)"],
            "time_modifier": {"operator": "at", "argument": "yesterday"},
        },
        (
            "Mary laughed into a room with a camera beside a shelf loudly "
            "under a lamp on a table with a microphone near a door yesterday"
        ): {
            "translation": (
                "at_T(yesterday, laugh(8)(into(room), with(camera), "
                "beside(shelf), loudly, under(lamp), on(table), "
                "with(microphone), near(door), mary))"
            ),
            "modifiers": [
                "into(room)",
                "with(camera)",
                "beside(shelf)",
                "loudly",
                "under(lamp)",
                "on(table)",
                "with(microphone)",
                "near(door)",
            ],
            "roles": [
                "Goal",
                "Instrument",
                "Location",
                "Manner",
                "Location",
                "Location",
                "Instrument",
                "Location",
            ],
            "source_modifiers": [],
            "goal_modifiers": ["into(room)"],
            "post_manner_locations": ["under(lamp)", "on(table)"],
            "instrument_tail": ["with(microphone)"],
            "final_location_tail": ["near(door)"],
            "time_modifier": {"operator": "at", "argument": "yesterday"},
        },
        (
            "Mary laughed from a window into a room with a camera beside a shelf "
            "loudly under a lamp on a table with a microphone near a door yesterday"
        ): {
            "translation": (
                "at_T(yesterday, laugh(9)(from(window), into(room), "
                "with(camera), beside(shelf), loudly, under(lamp), on(table), "
                "with(microphone), near(door), mary))"
            ),
            "modifiers": [
                "from(window)",
                "into(room)",
                "with(camera)",
                "beside(shelf)",
                "loudly",
                "under(lamp)",
                "on(table)",
                "with(microphone)",
                "near(door)",
            ],
            "roles": [
                "Source",
                "Goal",
                "Instrument",
                "Location",
                "Manner",
                "Location",
                "Location",
                "Instrument",
                "Location",
            ],
            "source_modifiers": ["from(window)"],
            "goal_modifiers": ["into(room)"],
            "post_manner_locations": ["under(lamp)", "on(table)"],
            "instrument_tail": ["with(microphone)"],
            "final_location_tail": ["near(door)"],
            "time_modifier": {"operator": "at", "argument": "yesterday"},
        },
        (
            "Mary laughed from a window with a camera beside a shelf loudly "
            "under a lamp on a table near a door with a microphone near a window "
            "yesterday"
        ): {
            "translation": (
                "at_T(yesterday, laugh(9)(from(window), with(camera), "
                "beside(shelf), loudly, under(lamp), on(table), near(door), "
                "with(microphone), near(window), mary))"
            ),
            "modifiers": [
                "from(window)",
                "with(camera)",
                "beside(shelf)",
                "loudly",
                "under(lamp)",
                "on(table)",
                "near(door)",
                "with(microphone)",
                "near(window)",
            ],
            "roles": [
                "Source",
                "Instrument",
                "Location",
                "Manner",
                "Location",
                "Location",
                "Location",
                "Instrument",
                "Location",
            ],
            "source_modifiers": ["from(window)"],
            "goal_modifiers": [],
            "post_manner_locations": ["under(lamp)", "on(table)", "near(door)"],
            "instrument_tail": ["with(microphone)"],
            "final_location_tail": ["near(window)"],
            "time_modifier": {"operator": "at", "argument": "yesterday"},
        },
    }
    expected = expectations.get(sentence)
    if expected is None:
        raise SystemExit(
            "web route smoke check failed: unknown directional-instrument-location-manner-location-sequence-instrument-location-tail fixture"
        )
    rule_id = (
        "directional_instrument_location_manner_location_sequence_instrument_location_tail_intransitive_predication"
    )
    validate_analyze_success_envelope(
        payload,
        sentence,
        rule_id,
        ["semantic_readings_check", "construction_hygiene"],
    )
    validate_verification_scope(
        payload,
        page,
        rule_id,
        "registered_construction",
        "construction_rule",
        rule_id,
    )
    if payload.get("kind") != rule_id:
        raise SystemExit(
            "web route smoke check failed: directional-instrument-location-manner-location-sequence-instrument-location-tail kind drift"
        )
    if payload.get("dependent_type_translation") != expected["translation"]:
        raise SystemExit(
            "web route smoke check failed: directional-instrument-location-manner-location-sequence-instrument-location-tail translation drift"
        )
    if "certification_upgrade_plan" in payload or "construction_rule_draft" in payload:
        raise SystemExit(
            "web route smoke check failed: directional-instrument-location-manner-location-sequence-instrument-location-tail exposes fallback draft"
        )

    ast = payload.get("ast")
    application_ast = ast
    if expected["time_modifier"] is not None:
        if (
            not isinstance(ast, dict)
            or ast.get("kind") != "time"
            or ast.get("operator") != expected["time_modifier"]["operator"]
            or ast.get("arguments") != [expected["time_modifier"]["argument"]]
            or not isinstance(ast.get("body"), dict)
        ):
            raise SystemExit(
                "web route smoke check failed: timed directional-instrument-location-manner-location-sequence-instrument-location-tail AST drift"
            )
        application_ast = ast["body"]
    modifier_roles = (
        application_ast.get("modifier_roles", {}).get("roles")
        if isinstance(application_ast, dict)
        else None
    )
    modifier_vector = (
        application_ast.get("modifier_vector", {}).get("items")
        if isinstance(application_ast, dict)
        else None
    )
    if (
        not isinstance(application_ast, dict)
        or application_ast.get("kind") != "application"
        or application_ast.get("function") != "laugh"
        or application_ast.get("arguments") != ["mary"]
        or application_ast.get("modifiers") != expected["modifiers"]
        or application_ast.get("adverb_count") != len(expected["modifiers"])
        or not isinstance(modifier_roles, list)
        or [role.get("semantic_role") for role in modifier_roles] != expected["roles"]
        or any(role.get("type") != "Adv" for role in modifier_roles)
        or not isinstance(modifier_vector, list)
        or [item.get("tail_length") for item in modifier_vector]
        != list(reversed(range(len(expected["modifiers"]))))
    ):
        raise SystemExit(
            "web route smoke check failed: directional-instrument-location-manner-location-sequence-instrument-location-tail AST drift"
        )

    event_semantics = payload.get("event_semantics")
    typed_predication = (
        event_semantics.get(rule_id) if isinstance(event_semantics, dict) else None
    )
    if (
        not isinstance(event_semantics, dict)
        or event_semantics.get("analysis")
        != "directional-instrument-location-manner-location-sequence-instrument-location-tail-intransitive-predication"
        or not isinstance(typed_predication, dict)
        or typed_predication.get("predicate") != "laugh"
        or typed_predication.get("agent") != "mary"
        or typed_predication.get("agent_type") != "Entity"
        or typed_predication.get("modifiers") != expected["modifiers"]
        or typed_predication.get("modifier_role_pattern") != expected["roles"]
        or typed_predication.get("source_modifiers") != expected["source_modifiers"]
        or typed_predication.get("goal_modifiers") != expected["goal_modifiers"]
        or typed_predication.get("initial_instrument_modifiers") != ["with(camera)"]
        or typed_predication.get("instrument_tail_modifiers")
        != expected["instrument_tail"]
        or typed_predication.get("instrument_tail_modifier_count")
        != len(expected["instrument_tail"])
        or typed_predication.get("pre_manner_location_modifiers") != ["beside(shelf)"]
        or typed_predication.get("post_manner_location_modifiers")
        != expected["post_manner_locations"]
        or typed_predication.get("post_manner_location_modifier_count")
        != len(expected["post_manner_locations"])
        or typed_predication.get("final_location_tail_modifiers")
        != expected["final_location_tail"]
        or typed_predication.get("final_location_tail_modifier_count")
        != len(expected["final_location_tail"])
        or typed_predication.get("manner_modifiers") != ["loudly"]
    ):
        raise SystemExit(
            "web route smoke check failed: directional-instrument-location-manner-location-sequence-instrument-location-tail analysis drift"
        )
    if expected["time_modifier"] is None:
        if "time_modifier" in typed_predication:
            raise SystemExit(
                "web route smoke check failed: untimed directional-instrument-location-manner-location-sequence-instrument-location-tail time drift"
            )
    elif typed_predication.get("time_modifier") != expected["time_modifier"]:
        raise SystemExit(
            "web route smoke check failed: timed directional-instrument-location-manner-location-sequence-instrument-location-tail time drift"
        )

    scope = (
        "explicit_agent_with_directional_instrument_location_manner_location_sequence_instrument_location_tail_at_time"
        if expected["time_modifier"]
        else "explicit_agent_with_directional_instrument_location_manner_location_sequence_instrument_location_tail"
    )
    readings = payload.get("semantic_readings")
    if not isinstance(readings, list) or len(readings) != 1:
        raise SystemExit(
            "web route smoke check failed: directional-instrument-location-manner-location-sequence-instrument-location-tail reading count drift"
        )
    validate_semantic_reading_summary(
        readings[0],
        {
            "name": (
                "directional_instrument_location_manner_location_sequence_instrument_location_tail_intransitive_predication_single_reading"
            ),
            "scope": scope,
            "source": rule_id,
            "coq_definition": "example_1",
        },
        "none",
        case,
        expected_type=None,
    )
    coq_code = payload.get("coq_code")
    if (
        not isinstance(coq_code, str)
        or "Parameter Event : Type." in coq_code
        or "Parameter Agent :" in coq_code
        or "Parameter Theme :" in coq_code
    ):
        raise SystemExit(
            "web route smoke check failed: directional-instrument-location-manner-location-sequence-instrument-location-tail Coq drift"
        )
    expected_adv = {
        "from(window)": "Parameter from_window : Adv.",
        "into(room)": "Parameter into_room : Adv.",
        "with(camera)": "Parameter with_camera : Adv.",
        "beside(shelf)": "Parameter beside_shelf : Adv.",
        "loudly": "Parameter loudly : Adv.",
        "under(lamp)": "Parameter under_lamp : Adv.",
        "on(table)": "Parameter on_table : Adv.",
        "near(door)": "Parameter near_door : Adv.",
        "with(microphone)": "Parameter with_microphone : Adv.",
        "near(window)": "Parameter near_window : Adv.",
    }
    expected_entity = {
        "from(window)": "Parameter from_window : Entity.",
        "into(room)": "Parameter into_room : Entity.",
        "with(camera)": "Parameter with_camera : Entity.",
        "beside(shelf)": "Parameter beside_shelf : Entity.",
        "loudly": "Parameter loudly : Entity.",
        "under(lamp)": "Parameter under_lamp : Entity.",
        "on(table)": "Parameter on_table : Entity.",
        "near(door)": "Parameter near_door : Entity.",
        "with(microphone)": "Parameter with_microphone : Entity.",
        "near(window)": "Parameter near_window : Entity.",
    }
    for modifier in expected["modifiers"]:
        if expected_adv[modifier] not in coq_code:
            raise SystemExit(
                "web route smoke check failed: directional-instrument-location-manner-location-sequence-instrument-location-tail Adv declaration drift"
            )
        if expected_entity[modifier] in coq_code:
            raise SystemExit(
                "web route smoke check failed: directional-instrument-location-manner-location-sequence-instrument-location-tail Entity surrogate drift"
            )
    validate_successful_semantic_reading_contract(case, payload, page)
    expected_page_fragments = [
        'data-verification-scope-kind="registered_construction"',
        'data-verification-level="construction_rule"',
        f"<dt>rule</dt><dd>{rule_id}</dd>",
        (
            'data-reading-name="'
            "directional_instrument_location_manner_location_sequence_instrument_location_tail_intransitive_predication_single_reading"
            '"'
        ),
        f"<dt>source</dt><dd>{rule_id}</dd>",
        f"<dt>scope</dt><dd>{scope}</dd>",
        expected["translation"],
        f"Translation succeeded via construction rule {rule_id}.",
    ]
    require_text_fragments(
        page,
        expected_page_fragments,
        "directional-instrument-location-manner-location-sequence-instrument-location-tail intransitive HTML",
    )
    if html.escape(sentence, quote=True) not in page:
        raise SystemExit(
            "web route smoke check failed: directional-instrument-location-manner-location-sequence-instrument-location-tail page input drift"
        )


def validate_analyze_directional_instrument_location_manner_location_sequence_instrument_location_instrument_tail_success(
    payload: dict,
    page: str,
    sentence: str,
) -> None:
    case = (
        "analyze_directional_instrument_location_manner_location_sequence_"
        "instrument_location_instrument_tail_success"
    )
    expectations = {
        (
            "Mary laughed from a window with a camera beside a shelf loudly "
            "under a lamp on a table with a microphone near a door with a telescope"
        ): {
            "translation": (
                "laugh(9)(from(window), with(camera), beside(shelf), loudly, "
                "under(lamp), on(table), with(microphone), near(door), "
                "with(telescope), mary)"
            ),
            "modifiers": [
                "from(window)",
                "with(camera)",
                "beside(shelf)",
                "loudly",
                "under(lamp)",
                "on(table)",
                "with(microphone)",
                "near(door)",
                "with(telescope)",
            ],
            "roles": [
                "Source",
                "Instrument",
                "Location",
                "Manner",
                "Location",
                "Location",
                "Instrument",
                "Location",
                "Instrument",
            ],
            "source_modifiers": ["from(window)"],
            "goal_modifiers": [],
            "post_manner_locations": ["under(lamp)", "on(table)"],
            "instrument_tail": ["with(microphone)"],
            "final_location_tail": ["near(door)"],
            "final_instrument_tail": ["with(telescope)"],
            "time_modifier": None,
        },
        (
            "Mary laughed from a window with a camera beside a shelf loudly "
            "under a lamp on a table with a microphone near a door with a telescope "
            "yesterday"
        ): {
            "translation": (
                "at_T(yesterday, laugh(9)(from(window), with(camera), "
                "beside(shelf), loudly, under(lamp), on(table), "
                "with(microphone), near(door), with(telescope), mary))"
            ),
            "modifiers": [
                "from(window)",
                "with(camera)",
                "beside(shelf)",
                "loudly",
                "under(lamp)",
                "on(table)",
                "with(microphone)",
                "near(door)",
                "with(telescope)",
            ],
            "roles": [
                "Source",
                "Instrument",
                "Location",
                "Manner",
                "Location",
                "Location",
                "Instrument",
                "Location",
                "Instrument",
            ],
            "source_modifiers": ["from(window)"],
            "goal_modifiers": [],
            "post_manner_locations": ["under(lamp)", "on(table)"],
            "instrument_tail": ["with(microphone)"],
            "final_location_tail": ["near(door)"],
            "final_instrument_tail": ["with(telescope)"],
            "time_modifier": {"operator": "at", "argument": "yesterday"},
        },
        (
            "Mary laughed into a room with a camera beside a shelf loudly "
            "under a lamp on a table with a microphone near a door with a telescope "
            "yesterday"
        ): {
            "translation": (
                "at_T(yesterday, laugh(9)(into(room), with(camera), "
                "beside(shelf), loudly, under(lamp), on(table), "
                "with(microphone), near(door), with(telescope), mary))"
            ),
            "modifiers": [
                "into(room)",
                "with(camera)",
                "beside(shelf)",
                "loudly",
                "under(lamp)",
                "on(table)",
                "with(microphone)",
                "near(door)",
                "with(telescope)",
            ],
            "roles": [
                "Goal",
                "Instrument",
                "Location",
                "Manner",
                "Location",
                "Location",
                "Instrument",
                "Location",
                "Instrument",
            ],
            "source_modifiers": [],
            "goal_modifiers": ["into(room)"],
            "post_manner_locations": ["under(lamp)", "on(table)"],
            "instrument_tail": ["with(microphone)"],
            "final_location_tail": ["near(door)"],
            "final_instrument_tail": ["with(telescope)"],
            "time_modifier": {"operator": "at", "argument": "yesterday"},
        },
        (
            "Mary laughed from a window into a room with a camera beside a shelf "
            "loudly under a lamp on a table with a microphone near a door with a "
            "telescope yesterday"
        ): {
            "translation": (
                "at_T(yesterday, laugh(10)(from(window), into(room), "
                "with(camera), beside(shelf), loudly, under(lamp), on(table), "
                "with(microphone), near(door), with(telescope), mary))"
            ),
            "modifiers": [
                "from(window)",
                "into(room)",
                "with(camera)",
                "beside(shelf)",
                "loudly",
                "under(lamp)",
                "on(table)",
                "with(microphone)",
                "near(door)",
                "with(telescope)",
            ],
            "roles": [
                "Source",
                "Goal",
                "Instrument",
                "Location",
                "Manner",
                "Location",
                "Location",
                "Instrument",
                "Location",
                "Instrument",
            ],
            "source_modifiers": ["from(window)"],
            "goal_modifiers": ["into(room)"],
            "post_manner_locations": ["under(lamp)", "on(table)"],
            "instrument_tail": ["with(microphone)"],
            "final_location_tail": ["near(door)"],
            "final_instrument_tail": ["with(telescope)"],
            "time_modifier": {"operator": "at", "argument": "yesterday"},
        },
        (
            "Mary laughed from a window with a camera beside a shelf loudly "
            "under a lamp on a table near a door with a microphone near a window "
            "with a telescope yesterday"
        ): {
            "translation": (
                "at_T(yesterday, laugh(10)(from(window), with(camera), "
                "beside(shelf), loudly, under(lamp), on(table), near(door), "
                "with(microphone), near(window), with(telescope), mary))"
            ),
            "modifiers": [
                "from(window)",
                "with(camera)",
                "beside(shelf)",
                "loudly",
                "under(lamp)",
                "on(table)",
                "near(door)",
                "with(microphone)",
                "near(window)",
                "with(telescope)",
            ],
            "roles": [
                "Source",
                "Instrument",
                "Location",
                "Manner",
                "Location",
                "Location",
                "Location",
                "Instrument",
                "Location",
                "Instrument",
            ],
            "source_modifiers": ["from(window)"],
            "goal_modifiers": [],
            "post_manner_locations": ["under(lamp)", "on(table)", "near(door)"],
            "instrument_tail": ["with(microphone)"],
            "final_location_tail": ["near(window)"],
            "final_instrument_tail": ["with(telescope)"],
            "time_modifier": {"operator": "at", "argument": "yesterday"},
        },
    }
    expected = expectations.get(sentence)
    if expected is None:
        raise SystemExit(
            "web route smoke check failed: unknown directional-instrument-location-manner-location-sequence-instrument-location-instrument-tail fixture"
        )
    rule_id = (
        "directional_instrument_location_manner_location_sequence_instrument_location_instrument_tail_intransitive_predication"
    )
    validate_analyze_success_envelope(
        payload,
        sentence,
        rule_id,
        ["semantic_readings_check", "construction_hygiene"],
    )
    validate_verification_scope(
        payload,
        page,
        rule_id,
        "registered_construction",
        "construction_rule",
        rule_id,
    )
    if payload.get("kind") != rule_id:
        raise SystemExit(
            "web route smoke check failed: directional-instrument-location-manner-location-sequence-instrument-location-instrument-tail kind drift"
        )
    if payload.get("dependent_type_translation") != expected["translation"]:
        raise SystemExit(
            "web route smoke check failed: directional-instrument-location-manner-location-sequence-instrument-location-instrument-tail translation drift"
        )
    if "certification_upgrade_plan" in payload or "construction_rule_draft" in payload:
        raise SystemExit(
            "web route smoke check failed: directional-instrument-location-manner-location-sequence-instrument-location-instrument-tail exposes fallback draft"
        )

    ast = payload.get("ast")
    application_ast = ast
    if expected["time_modifier"] is not None:
        if (
            not isinstance(ast, dict)
            or ast.get("kind") != "time"
            or ast.get("operator") != expected["time_modifier"]["operator"]
            or ast.get("arguments") != [expected["time_modifier"]["argument"]]
            or not isinstance(ast.get("body"), dict)
        ):
            raise SystemExit(
                "web route smoke check failed: timed directional-instrument-location-manner-location-sequence-instrument-location-instrument-tail AST drift"
            )
        application_ast = ast["body"]
    modifier_roles = (
        application_ast.get("modifier_roles", {}).get("roles")
        if isinstance(application_ast, dict)
        else None
    )
    modifier_vector = (
        application_ast.get("modifier_vector", {}).get("items")
        if isinstance(application_ast, dict)
        else None
    )
    if (
        not isinstance(application_ast, dict)
        or application_ast.get("kind") != "application"
        or application_ast.get("function") != "laugh"
        or application_ast.get("arguments") != ["mary"]
        or application_ast.get("modifiers") != expected["modifiers"]
        or application_ast.get("adverb_count") != len(expected["modifiers"])
        or not isinstance(modifier_roles, list)
        or [role.get("semantic_role") for role in modifier_roles] != expected["roles"]
        or any(role.get("type") != "Adv" for role in modifier_roles)
        or not isinstance(modifier_vector, list)
        or [item.get("tail_length") for item in modifier_vector]
        != list(reversed(range(len(expected["modifiers"]))))
    ):
        raise SystemExit(
            "web route smoke check failed: directional-instrument-location-manner-location-sequence-instrument-location-instrument-tail AST drift"
        )

    event_semantics = payload.get("event_semantics")
    typed_predication = (
        event_semantics.get(rule_id) if isinstance(event_semantics, dict) else None
    )
    if (
        not isinstance(event_semantics, dict)
        or event_semantics.get("analysis")
        != "directional-instrument-location-manner-location-sequence-instrument-location-instrument-tail-intransitive-predication"
        or not isinstance(typed_predication, dict)
        or typed_predication.get("predicate") != "laugh"
        or typed_predication.get("agent") != "mary"
        or typed_predication.get("agent_type") != "Entity"
        or typed_predication.get("modifiers") != expected["modifiers"]
        or typed_predication.get("modifier_role_pattern") != expected["roles"]
        or typed_predication.get("source_modifiers") != expected["source_modifiers"]
        or typed_predication.get("goal_modifiers") != expected["goal_modifiers"]
        or typed_predication.get("initial_instrument_modifiers") != ["with(camera)"]
        or typed_predication.get("instrument_tail_modifiers")
        != expected["instrument_tail"]
        or typed_predication.get("instrument_tail_modifier_count")
        != len(expected["instrument_tail"])
        or typed_predication.get("final_instrument_tail_modifiers")
        != expected["final_instrument_tail"]
        or typed_predication.get("final_instrument_tail_modifier_count")
        != len(expected["final_instrument_tail"])
        or typed_predication.get("pre_manner_location_modifiers") != ["beside(shelf)"]
        or typed_predication.get("post_manner_location_modifiers")
        != expected["post_manner_locations"]
        or typed_predication.get("post_manner_location_modifier_count")
        != len(expected["post_manner_locations"])
        or typed_predication.get("final_location_tail_modifiers")
        != expected["final_location_tail"]
        or typed_predication.get("final_location_tail_modifier_count")
        != len(expected["final_location_tail"])
        or typed_predication.get("manner_modifiers") != ["loudly"]
    ):
        raise SystemExit(
            "web route smoke check failed: directional-instrument-location-manner-location-sequence-instrument-location-instrument-tail analysis drift"
        )
    if expected["time_modifier"] is None:
        if "time_modifier" in typed_predication:
            raise SystemExit(
                "web route smoke check failed: untimed directional-instrument-location-manner-location-sequence-instrument-location-instrument-tail time drift"
            )
    elif typed_predication.get("time_modifier") != expected["time_modifier"]:
        raise SystemExit(
            "web route smoke check failed: timed directional-instrument-location-manner-location-sequence-instrument-location-instrument-tail time drift"
        )

    scope = (
        "explicit_agent_with_directional_instrument_location_manner_location_sequence_instrument_location_instrument_tail_at_time"
        if expected["time_modifier"]
        else "explicit_agent_with_directional_instrument_location_manner_location_sequence_instrument_location_instrument_tail"
    )
    readings = payload.get("semantic_readings")
    if not isinstance(readings, list) or len(readings) != 1:
        raise SystemExit(
            "web route smoke check failed: directional-instrument-location-manner-location-sequence-instrument-location-instrument-tail reading count drift"
        )
    validate_semantic_reading_summary(
        readings[0],
        {
            "name": (
                "directional_instrument_location_manner_location_sequence_instrument_location_instrument_tail_intransitive_predication_single_reading"
            ),
            "scope": scope,
            "source": rule_id,
            "coq_definition": "example_1",
        },
        "none",
        case,
        expected_type=None,
    )
    coq_code = payload.get("coq_code")
    if (
        not isinstance(coq_code, str)
        or "Parameter Event : Type." in coq_code
        or "Parameter Agent :" in coq_code
        or "Parameter Theme :" in coq_code
    ):
        raise SystemExit(
            "web route smoke check failed: directional-instrument-location-manner-location-sequence-instrument-location-instrument-tail Coq drift"
        )
    expected_adv = {
        "from(window)": "Parameter from_window : Adv.",
        "into(room)": "Parameter into_room : Adv.",
        "with(camera)": "Parameter with_camera : Adv.",
        "beside(shelf)": "Parameter beside_shelf : Adv.",
        "loudly": "Parameter loudly : Adv.",
        "under(lamp)": "Parameter under_lamp : Adv.",
        "on(table)": "Parameter on_table : Adv.",
        "near(door)": "Parameter near_door : Adv.",
        "with(microphone)": "Parameter with_microphone : Adv.",
        "near(window)": "Parameter near_window : Adv.",
        "with(telescope)": "Parameter with_telescope : Adv.",
    }
    expected_entity = {
        "from(window)": "Parameter from_window : Entity.",
        "into(room)": "Parameter into_room : Entity.",
        "with(camera)": "Parameter with_camera : Entity.",
        "beside(shelf)": "Parameter beside_shelf : Entity.",
        "loudly": "Parameter loudly : Entity.",
        "under(lamp)": "Parameter under_lamp : Entity.",
        "on(table)": "Parameter on_table : Entity.",
        "near(door)": "Parameter near_door : Entity.",
        "with(microphone)": "Parameter with_microphone : Entity.",
        "near(window)": "Parameter near_window : Entity.",
        "with(telescope)": "Parameter with_telescope : Entity.",
    }
    for modifier in expected["modifiers"]:
        if expected_adv[modifier] not in coq_code:
            raise SystemExit(
                "web route smoke check failed: directional-instrument-location-manner-location-sequence-instrument-location-instrument-tail Adv declaration drift"
            )
        if expected_entity[modifier] in coq_code:
            raise SystemExit(
                "web route smoke check failed: directional-instrument-location-manner-location-sequence-instrument-location-instrument-tail Entity surrogate drift"
            )
    validate_successful_semantic_reading_contract(case, payload, page)
    expected_page_fragments = [
        'data-verification-scope-kind="registered_construction"',
        'data-verification-level="construction_rule"',
        f"<dt>rule</dt><dd>{rule_id}</dd>",
        (
            'data-reading-name="'
            "directional_instrument_location_manner_location_sequence_instrument_location_instrument_tail_intransitive_predication_single_reading"
            '"'
        ),
        f"<dt>source</dt><dd>{rule_id}</dd>",
        f"<dt>scope</dt><dd>{scope}</dd>",
        expected["translation"],
        f"Translation succeeded via construction rule {rule_id}.",
    ]
    require_text_fragments(
        page,
        expected_page_fragments,
        "directional-instrument-location-manner-location-sequence-instrument-location-instrument-tail intransitive HTML",
    )
    if html.escape(sentence, quote=True) not in page:
        raise SystemExit(
            "web route smoke check failed: directional-instrument-location-manner-location-sequence-instrument-location-instrument-tail page input drift"
        )


def validate_analyze_directional_instrument_location_manner_location_sequence_instrument_location_instrument_location_tail_success(
    payload: dict,
    page: str,
    sentence: str,
) -> None:
    case = (
        "analyze_directional_instrument_location_manner_location_sequence_"
        "instrument_location_instrument_location_tail_success"
    )
    rule_id = (
        "directional_instrument_location_manner_location_sequence_instrument_location_instrument_location_tail_intransitive_predication"
    )
    base_modifiers = [
        "with(camera)",
        "beside(shelf)",
        "loudly",
        "under(lamp)",
        "on(table)",
        "with(microphone)",
        "near(door)",
        "with(telescope)",
        "near(window)",
    ]
    base_roles = [
        "Instrument",
        "Location",
        "Manner",
        "Location",
        "Location",
        "Instrument",
        "Location",
        "Instrument",
        "Location",
    ]
    expectations = {
        (
            "Mary laughed from a window with a camera beside a shelf loudly "
            "under a lamp on a table with a microphone near a door with a telescope near a window"
        ): {
            "translation": (
                "laugh(10)(from(window), with(camera), beside(shelf), loudly, "
                "under(lamp), on(table), with(microphone), near(door), "
                "with(telescope), near(window), mary)"
            ),
            "modifiers": ["from(window)", *base_modifiers],
            "roles": ["Source", *base_roles],
            "source_modifiers": ["from(window)"],
            "goal_modifiers": [],
            "post_manner_locations": ["under(lamp)", "on(table)"],
            "instrument_tail": ["with(microphone)"],
            "pre_final_location_tail": ["near(door)"],
            "final_instrument_tail": ["with(telescope)"],
            "final_location_tail": ["near(window)"],
            "time_modifier": None,
        },
        (
            "Mary laughed from a window with a camera beside a shelf loudly "
            "under a lamp on a table with a microphone near a door with a telescope "
            "near a window yesterday"
        ): {
            "translation": (
                "at_T(yesterday, laugh(10)(from(window), with(camera), "
                "beside(shelf), loudly, under(lamp), on(table), "
                "with(microphone), near(door), with(telescope), near(window), mary))"
            ),
            "modifiers": ["from(window)", *base_modifiers],
            "roles": ["Source", *base_roles],
            "source_modifiers": ["from(window)"],
            "goal_modifiers": [],
            "post_manner_locations": ["under(lamp)", "on(table)"],
            "instrument_tail": ["with(microphone)"],
            "pre_final_location_tail": ["near(door)"],
            "final_instrument_tail": ["with(telescope)"],
            "final_location_tail": ["near(window)"],
            "time_modifier": {"operator": "at", "argument": "yesterday"},
        },
        (
            "Mary laughed into a room with a camera beside a shelf loudly "
            "under a lamp on a table with a microphone near a door with a telescope "
            "near a window yesterday"
        ): {
            "translation": (
                "at_T(yesterday, laugh(10)(into(room), with(camera), "
                "beside(shelf), loudly, under(lamp), on(table), "
                "with(microphone), near(door), with(telescope), near(window), mary))"
            ),
            "modifiers": ["into(room)", *base_modifiers],
            "roles": ["Goal", *base_roles],
            "source_modifiers": [],
            "goal_modifiers": ["into(room)"],
            "post_manner_locations": ["under(lamp)", "on(table)"],
            "instrument_tail": ["with(microphone)"],
            "pre_final_location_tail": ["near(door)"],
            "final_instrument_tail": ["with(telescope)"],
            "final_location_tail": ["near(window)"],
            "time_modifier": {"operator": "at", "argument": "yesterday"},
        },
        (
            "Mary laughed from a window into a room with a camera beside a shelf "
            "loudly under a lamp on a table with a microphone near a door with a "
            "telescope near a window yesterday"
        ): {
            "translation": (
                "at_T(yesterday, laugh(11)(from(window), into(room), "
                "with(camera), beside(shelf), loudly, under(lamp), on(table), "
                "with(microphone), near(door), with(telescope), near(window), mary))"
            ),
            "modifiers": ["from(window)", "into(room)", *base_modifiers],
            "roles": ["Source", "Goal", *base_roles],
            "source_modifiers": ["from(window)"],
            "goal_modifiers": ["into(room)"],
            "post_manner_locations": ["under(lamp)", "on(table)"],
            "instrument_tail": ["with(microphone)"],
            "pre_final_location_tail": ["near(door)"],
            "final_instrument_tail": ["with(telescope)"],
            "final_location_tail": ["near(window)"],
            "time_modifier": {"operator": "at", "argument": "yesterday"},
        },
        (
            "Mary laughed from a window with a camera beside a shelf loudly "
            "under a lamp on a table with a microphone near a door with a telescope "
            "near a window in the park yesterday"
        ): {
            "translation": (
                "at_T(yesterday, laugh(11)(from(window), with(camera), "
                "beside(shelf), loudly, under(lamp), on(table), "
                "with(microphone), near(door), with(telescope), near(window), "
                "in(park), mary))"
            ),
            "modifiers": ["from(window)", *base_modifiers, "in(park)"],
            "roles": ["Source", *base_roles, "Location"],
            "source_modifiers": ["from(window)"],
            "goal_modifiers": [],
            "post_manner_locations": ["under(lamp)", "on(table)"],
            "instrument_tail": ["with(microphone)"],
            "pre_final_location_tail": ["near(door)"],
            "final_instrument_tail": ["with(telescope)"],
            "final_location_tail": ["near(window)", "in(park)"],
            "time_modifier": {"operator": "at", "argument": "yesterday"},
        },
    }
    expected = expectations.get(sentence)
    if expected is None:
        raise SystemExit(
            "web route smoke check failed: unknown directional-instrument-location-manner-location-sequence-instrument-location-instrument-location-tail fixture"
        )
    validate_analyze_success_envelope(
        payload,
        sentence,
        rule_id,
        ["semantic_readings_check", "construction_hygiene"],
    )
    validate_verification_scope(
        payload,
        page,
        rule_id,
        "registered_construction",
        "construction_rule",
        rule_id,
    )
    if payload.get("kind") != rule_id:
        raise SystemExit(
            "web route smoke check failed: directional-instrument-location-manner-location-sequence-instrument-location-instrument-location-tail kind drift"
        )
    if payload.get("dependent_type_translation") != expected["translation"]:
        raise SystemExit(
            "web route smoke check failed: directional-instrument-location-manner-location-sequence-instrument-location-instrument-location-tail translation drift"
        )
    if "certification_upgrade_plan" in payload or "construction_rule_draft" in payload:
        raise SystemExit(
            "web route smoke check failed: directional-instrument-location-manner-location-sequence-instrument-location-instrument-location-tail exposes fallback draft"
        )

    ast = payload.get("ast")
    application_ast = ast
    if expected["time_modifier"] is not None:
        if (
            not isinstance(ast, dict)
            or ast.get("kind") != "time"
            or ast.get("operator") != expected["time_modifier"]["operator"]
            or ast.get("arguments") != [expected["time_modifier"]["argument"]]
            or not isinstance(ast.get("body"), dict)
        ):
            raise SystemExit(
                "web route smoke check failed: timed directional-instrument-location-manner-location-sequence-instrument-location-instrument-location-tail AST drift"
            )
        application_ast = ast["body"]
    modifier_roles = (
        application_ast.get("modifier_roles", {}).get("roles")
        if isinstance(application_ast, dict)
        else None
    )
    modifier_vector = (
        application_ast.get("modifier_vector", {}).get("items")
        if isinstance(application_ast, dict)
        else None
    )
    if (
        not isinstance(application_ast, dict)
        or application_ast.get("kind") != "application"
        or application_ast.get("function") != "laugh"
        or application_ast.get("arguments") != ["mary"]
        or application_ast.get("modifiers") != expected["modifiers"]
        or application_ast.get("adverb_count") != len(expected["modifiers"])
        or not isinstance(modifier_roles, list)
        or [role.get("semantic_role") for role in modifier_roles] != expected["roles"]
        or any(role.get("type") != "Adv" for role in modifier_roles)
        or not isinstance(modifier_vector, list)
        or [item.get("tail_length") for item in modifier_vector]
        != list(reversed(range(len(expected["modifiers"]))))
    ):
        raise SystemExit(
            "web route smoke check failed: directional-instrument-location-manner-location-sequence-instrument-location-instrument-location-tail AST drift"
        )

    event_semantics = payload.get("event_semantics")
    typed_predication = (
        event_semantics.get(rule_id) if isinstance(event_semantics, dict) else None
    )
    if (
        not isinstance(event_semantics, dict)
        or event_semantics.get("analysis")
        != "directional-instrument-location-manner-location-sequence-instrument-location-instrument-location-tail-intransitive-predication"
        or not isinstance(typed_predication, dict)
        or typed_predication.get("predicate") != "laugh"
        or typed_predication.get("agent") != "mary"
        or typed_predication.get("agent_type") != "Entity"
        or typed_predication.get("modifiers") != expected["modifiers"]
        or typed_predication.get("modifier_role_pattern") != expected["roles"]
        or typed_predication.get("source_modifiers") != expected["source_modifiers"]
        or typed_predication.get("goal_modifiers") != expected["goal_modifiers"]
        or typed_predication.get("initial_instrument_modifiers") != ["with(camera)"]
        or typed_predication.get("instrument_tail_modifiers")
        != expected["instrument_tail"]
        or typed_predication.get("pre_final_instrument_location_tail_modifiers")
        != expected["pre_final_location_tail"]
        or typed_predication.get("final_instrument_tail_modifiers")
        != expected["final_instrument_tail"]
        or typed_predication.get("final_location_tail_modifiers")
        != expected["final_location_tail"]
        or typed_predication.get("post_manner_location_modifiers")
        != expected["post_manner_locations"]
        or typed_predication.get("manner_modifiers") != ["loudly"]
    ):
        raise SystemExit(
            "web route smoke check failed: directional-instrument-location-manner-location-sequence-instrument-location-instrument-location-tail analysis drift"
        )
    if expected["time_modifier"] is None:
        if "time_modifier" in typed_predication:
            raise SystemExit(
                "web route smoke check failed: untimed directional-instrument-location-manner-location-sequence-instrument-location-instrument-location-tail time drift"
            )
    elif typed_predication.get("time_modifier") != expected["time_modifier"]:
        raise SystemExit(
            "web route smoke check failed: timed directional-instrument-location-manner-location-sequence-instrument-location-instrument-location-tail time drift"
        )

    scope = (
        "explicit_agent_with_directional_instrument_location_manner_location_sequence_instrument_location_instrument_location_tail_at_time"
        if expected["time_modifier"]
        else "explicit_agent_with_directional_instrument_location_manner_location_sequence_instrument_location_instrument_location_tail"
    )
    readings = payload.get("semantic_readings")
    if not isinstance(readings, list) or len(readings) != 1:
        raise SystemExit(
            "web route smoke check failed: directional-instrument-location-manner-location-sequence-instrument-location-instrument-location-tail reading count drift"
        )
    validate_semantic_reading_summary(
        readings[0],
        {
            "name": (
                "directional_instrument_location_manner_location_sequence_instrument_location_instrument_location_tail_intransitive_predication_single_reading"
            ),
            "scope": scope,
            "source": rule_id,
            "coq_definition": "example_1",
        },
        "none",
        case,
        expected_type=None,
    )
    coq_code = payload.get("coq_code")
    if (
        not isinstance(coq_code, str)
        or "Parameter Event : Type." in coq_code
        or "Parameter Agent :" in coq_code
        or "Parameter Theme :" in coq_code
    ):
        raise SystemExit(
            "web route smoke check failed: directional-instrument-location-manner-location-sequence-instrument-location-instrument-location-tail Coq drift"
        )
    expected_adv = {
        "from(window)": "Parameter from_window : Adv.",
        "into(room)": "Parameter into_room : Adv.",
        "with(camera)": "Parameter with_camera : Adv.",
        "beside(shelf)": "Parameter beside_shelf : Adv.",
        "loudly": "Parameter loudly : Adv.",
        "under(lamp)": "Parameter under_lamp : Adv.",
        "on(table)": "Parameter on_table : Adv.",
        "with(microphone)": "Parameter with_microphone : Adv.",
        "near(door)": "Parameter near_door : Adv.",
        "with(telescope)": "Parameter with_telescope : Adv.",
        "near(window)": "Parameter near_window : Adv.",
        "in(park)": "Parameter in_park : Adv.",
    }
    expected_entity = {
        "from(window)": "Parameter from_window : Entity.",
        "into(room)": "Parameter into_room : Entity.",
        "with(camera)": "Parameter with_camera : Entity.",
        "beside(shelf)": "Parameter beside_shelf : Entity.",
        "loudly": "Parameter loudly : Entity.",
        "under(lamp)": "Parameter under_lamp : Entity.",
        "on(table)": "Parameter on_table : Entity.",
        "with(microphone)": "Parameter with_microphone : Entity.",
        "near(door)": "Parameter near_door : Entity.",
        "with(telescope)": "Parameter with_telescope : Entity.",
        "near(window)": "Parameter near_window : Entity.",
        "in(park)": "Parameter in_park : Entity.",
    }
    for modifier in expected["modifiers"]:
        if expected_adv[modifier] not in coq_code:
            raise SystemExit(
                "web route smoke check failed: directional-instrument-location-manner-location-sequence-instrument-location-instrument-location-tail Adv declaration drift"
            )
        if expected_entity[modifier] in coq_code:
            raise SystemExit(
                "web route smoke check failed: directional-instrument-location-manner-location-sequence-instrument-location-instrument-location-tail Entity surrogate drift"
            )
    validate_successful_semantic_reading_contract(case, payload, page)
    expected_page_fragments = [
        'data-verification-scope-kind="registered_construction"',
        'data-verification-level="construction_rule"',
        f"<dt>rule</dt><dd>{rule_id}</dd>",
        (
            'data-reading-name="'
            "directional_instrument_location_manner_location_sequence_instrument_location_instrument_location_tail_intransitive_predication_single_reading"
            '"'
        ),
        f"<dt>source</dt><dd>{rule_id}</dd>",
        f"<dt>scope</dt><dd>{scope}</dd>",
        expected["translation"],
        f"Translation succeeded via construction rule {rule_id}.",
    ]
    require_text_fragments(
        page,
        expected_page_fragments,
        "directional-instrument-location-manner-location-sequence-instrument-location-instrument-location-tail intransitive HTML",
    )
    if html.escape(sentence, quote=True) not in page:
        raise SystemExit(
            "web route smoke check failed: directional-instrument-location-manner-location-sequence-instrument-location-instrument-location-tail page input drift"
        )


def validate_analyze_manner_instrument_intransitive_success(
    payload: dict,
    page: str,
    sentence: str,
) -> None:
    case = "analyze_manner_instrument_intransitive_success"
    is_timed = sentence == "Mary laughed loudly with a telescope yesterday"
    expected_translation = (
        "at_T(yesterday, laugh(2)(loudly, with(telescope), mary))"
        if is_timed
        else "laugh(2)(loudly, with(telescope), mary)"
    )
    expected_scope = (
        "explicit_agent_with_manner_and_instrument_adv_at_time"
        if is_timed
        else "explicit_agent_with_manner_and_instrument_adv"
    )
    validate_analyze_success_envelope(
        payload,
        sentence,
        "manner_instrument_intransitive_predication",
        ["semantic_readings_check", "construction_hygiene"],
    )
    validate_verification_scope(
        payload,
        page,
        "manner_instrument_intransitive_predication",
        "registered_construction",
        "construction_rule",
        "manner_instrument_intransitive_predication",
    )
    if payload.get("kind") != "manner_instrument_intransitive_predication":
        raise SystemExit(
            "web route smoke check failed: manner-instrument intransitive kind drift"
        )
    if payload.get("dependent_type_translation") != expected_translation:
        raise SystemExit(
            "web route smoke check failed: manner-instrument intransitive translation drift"
        )
    if "certification_upgrade_plan" in payload or "construction_rule_draft" in payload:
        raise SystemExit(
            "web route smoke check failed: manner-instrument intransitive exposes fallback draft"
        )
    ast = payload.get("ast")
    application_ast = ast
    if is_timed and isinstance(ast, dict):
        if (
            ast.get("kind") != "time"
            or ast.get("operator") != "at"
            or ast.get("arguments") != ["yesterday"]
            or not isinstance(ast.get("body"), dict)
        ):
            raise SystemExit(
                "web route smoke check failed: timed manner-instrument intransitive AST drift"
            )
        application_ast = ast["body"]
    role_frame = (
        application_ast.get("role_frame", {}).get("roles")
        if isinstance(application_ast, dict)
        else None
    )
    modifier_roles = (
        application_ast.get("modifier_roles", {}).get("roles")
        if isinstance(application_ast, dict)
        else None
    )
    modifier_vector = (
        application_ast.get("modifier_vector", {}).get("items")
        if isinstance(application_ast, dict)
        else None
    )
    if (
        not isinstance(application_ast, dict)
        or application_ast.get("kind") != "application"
        or application_ast.get("function") != "laugh"
        or application_ast.get("arguments") != ["mary"]
        or application_ast.get("modifiers") != ["loudly", "with(telescope)"]
        or application_ast.get("adverb_count") != 2
        or not isinstance(role_frame, list)
        or len(role_frame) != 1
        or role_frame[0].get("role") != "Agent"
        or role_frame[0].get("type") != "Entity"
        or role_frame[0].get("source") != "explicit"
        or not isinstance(modifier_roles, list)
        or [role.get("type") for role in modifier_roles] != ["Adv", "Adv"]
        or [role.get("semantic_role") for role in modifier_roles]
        != ["Manner", "Instrument"]
        or not isinstance(modifier_vector, list)
        or [item.get("tail_length") for item in modifier_vector] != [1, 0]
    ):
        raise SystemExit(
            "web route smoke check failed: manner-instrument intransitive AST drift"
        )
    event_semantics = payload.get("event_semantics")
    typed_predication = (
        event_semantics.get("manner_instrument_intransitive_predication")
        if isinstance(event_semantics, dict)
        else None
    )
    if (
        not isinstance(event_semantics, dict)
        or event_semantics.get("analysis")
        != "manner-instrument-intransitive-predication"
        or not isinstance(typed_predication, dict)
        or typed_predication.get("predicate") != "laugh"
        or typed_predication.get("agent") != "mary"
        or typed_predication.get("agent_type") != "Entity"
        or typed_predication.get("modifiers") != ["loudly", "with(telescope)"]
        or typed_predication.get("manner_modifier") != "loudly"
        or typed_predication.get("instrument_modifier") != "with(telescope)"
    ):
        raise SystemExit(
            "web route smoke check failed: manner-instrument intransitive analysis drift"
        )
    if is_timed:
        if typed_predication.get("time_modifier") != {
            "operator": "at",
            "argument": "yesterday",
        }:
            raise SystemExit(
                "web route smoke check failed: timed manner-instrument intransitive time drift"
            )
    elif "time_modifier" in typed_predication:
        raise SystemExit(
            "web route smoke check failed: untimed manner-instrument intransitive time drift"
        )
    hygiene = payload.get("construction_hygiene")
    if not isinstance(hygiene, dict) or hygiene.get("ok") is not True:
        raise SystemExit(
            "web route smoke check failed: manner-instrument intransitive hygiene drift"
        )
    readings = payload.get("semantic_readings")
    if not isinstance(readings, list) or len(readings) != 1:
        raise SystemExit(
            "web route smoke check failed: manner-instrument intransitive reading count drift"
        )
    validate_semantic_reading_summary(
        readings[0],
        {
            "name": "manner_instrument_intransitive_predication_single_reading",
            "scope": expected_scope,
            "source": "manner_instrument_intransitive_predication",
            "coq_definition": "example_1",
        },
        "none",
        case,
        expected_type=None,
    )
    coq_code = payload.get("coq_code")
    expected_definition = (
        "Definition example_1 : PropT := (at_T yesterday (laugh 2 (mods_cons 1 loudly (mods_cons 0 with_telescope mods_nil)) mary))."
        if is_timed
        else "Definition example_1 : PropT := (laugh 2 (mods_cons 1 loudly (mods_cons 0 with_telescope mods_nil)) mary)."
    )
    if (
        not isinstance(coq_code, str)
        or "Parameter loudly : Adv." not in coq_code
        or "Parameter with_telescope : Adv." not in coq_code
        or "Parameter loudly : Entity." in coq_code
        or "Parameter with_telescope : Entity." in coq_code
        or "Parameter laugh : forall n : nat, ModifierSeq n -> Entity -> PropT."
        not in coq_code
        or expected_definition not in coq_code
        or "Parameter Event : Type." in coq_code
        or "Parameter Agent :" in coq_code
        or "Parameter Theme :" in coq_code
    ):
        raise SystemExit(
            "web route smoke check failed: manner-instrument intransitive Coq drift"
        )
    validate_successful_semantic_reading_contract(case, payload, page)
    expected_page_fragments = [
        'data-verification-scope-kind="registered_construction"',
        'data-verification-level="construction_rule"',
        "<dt>rule</dt><dd>manner_instrument_intransitive_predication</dd>",
        'data-reading-name="manner_instrument_intransitive_predication_single_reading"',
        "<dt>source</dt><dd>manner_instrument_intransitive_predication</dd>",
        f"<dt>scope</dt><dd>{expected_scope}</dd>",
        expected_translation,
        "Translation succeeded via construction rule manner_instrument_intransitive_predication.",
    ]
    require_text_fragments(page, expected_page_fragments, "manner-instrument HTML")
    if html.escape(sentence, quote=True) not in page:
        raise SystemExit(
            "web route smoke check failed: manner-instrument page input drift"
        )


def validate_analyze_manner_locative_intransitive_success(
    payload: dict,
    page: str,
    sentence: str,
) -> None:
    case = "analyze_manner_locative_intransitive_success"
    is_timed = sentence == "Mary laughed loudly in the park yesterday"
    expected_translation = (
        "at_T(yesterday, laugh(2)(loudly, in(park), mary))"
        if is_timed
        else "laugh(2)(loudly, in(park), mary)"
    )
    expected_scope = (
        "explicit_agent_with_manner_and_location_adv_at_time"
        if is_timed
        else "explicit_agent_with_manner_and_location_adv"
    )
    validate_analyze_success_envelope(
        payload,
        sentence,
        "manner_locative_intransitive_predication",
        ["semantic_readings_check", "construction_hygiene"],
    )
    validate_verification_scope(
        payload,
        page,
        "manner_locative_intransitive_predication",
        "registered_construction",
        "construction_rule",
        "manner_locative_intransitive_predication",
    )
    if payload.get("kind") != "manner_locative_intransitive_predication":
        raise SystemExit(
            "web route smoke check failed: manner-locative intransitive kind drift"
        )
    if payload.get("dependent_type_translation") != expected_translation:
        raise SystemExit(
            "web route smoke check failed: manner-locative intransitive translation drift"
        )
    if "certification_upgrade_plan" in payload or "construction_rule_draft" in payload:
        raise SystemExit(
            "web route smoke check failed: manner-locative intransitive exposes fallback draft"
        )
    ast = payload.get("ast")
    application_ast = ast
    if is_timed and isinstance(ast, dict):
        if (
            ast.get("kind") != "time"
            or ast.get("operator") != "at"
            or ast.get("arguments") != ["yesterday"]
            or not isinstance(ast.get("body"), dict)
        ):
            raise SystemExit(
                "web route smoke check failed: timed manner-locative intransitive AST drift"
            )
        application_ast = ast["body"]
    role_frame = (
        application_ast.get("role_frame", {}).get("roles")
        if isinstance(application_ast, dict)
        else None
    )
    modifier_roles = (
        application_ast.get("modifier_roles", {}).get("roles")
        if isinstance(application_ast, dict)
        else None
    )
    if (
        not isinstance(application_ast, dict)
        or application_ast.get("kind") != "application"
        or application_ast.get("function") != "laugh"
        or application_ast.get("arguments") != ["mary"]
        or application_ast.get("modifiers") != ["loudly", "in(park)"]
        or application_ast.get("adverb_count") != 2
        or not isinstance(role_frame, list)
        or len(role_frame) != 1
        or role_frame[0].get("role") != "Agent"
        or role_frame[0].get("type") != "Entity"
        or role_frame[0].get("source") != "explicit"
        or not isinstance(modifier_roles, list)
        or [role.get("type") for role in modifier_roles] != ["Adv", "Adv"]
        or [role.get("semantic_role") for role in modifier_roles]
        != ["Manner", "Location"]
    ):
        raise SystemExit(
            "web route smoke check failed: manner-locative intransitive AST drift"
        )
    event_semantics = payload.get("event_semantics")
    typed_predication = (
        event_semantics.get("manner_locative_intransitive_predication")
        if isinstance(event_semantics, dict)
        else None
    )
    if (
        not isinstance(event_semantics, dict)
        or event_semantics.get("analysis")
        != "manner-locative-intransitive-predication"
        or not isinstance(typed_predication, dict)
        or typed_predication.get("predicate") != "laugh"
        or typed_predication.get("agent") != "mary"
        or typed_predication.get("agent_type") != "Entity"
        or typed_predication.get("modifiers") != ["loudly", "in(park)"]
        or [
            role.get("semantic_role")
            for role in typed_predication.get("modifier_roles", [])
            if isinstance(role, dict)
        ]
        != ["Manner", "Location"]
    ):
        raise SystemExit(
            "web route smoke check failed: manner-locative intransitive analysis drift"
        )
    if is_timed:
        if typed_predication.get("time_modifier") != {
            "operator": "at",
            "argument": "yesterday",
        }:
            raise SystemExit(
                "web route smoke check failed: timed manner-locative intransitive time drift"
            )
    elif "time_modifier" in typed_predication:
        raise SystemExit(
            "web route smoke check failed: untimed manner-locative intransitive time drift"
        )
    hygiene = payload.get("construction_hygiene")
    if not isinstance(hygiene, dict) or hygiene.get("ok") is not True:
        raise SystemExit(
            "web route smoke check failed: manner-locative intransitive hygiene drift"
        )
    readings = payload.get("semantic_readings")
    if not isinstance(readings, list) or len(readings) != 1:
        raise SystemExit(
            "web route smoke check failed: manner-locative intransitive reading count drift"
        )
    validate_semantic_reading_summary(
        readings[0],
        {
            "name": "manner_locative_intransitive_predication_single_reading",
            "scope": expected_scope,
            "source": "manner_locative_intransitive_predication",
            "coq_definition": "example_1",
        },
        "none",
        case,
        expected_type=None,
    )
    coq_code = payload.get("coq_code")
    expected_definition = (
        "Definition example_1 : PropT := (at_T yesterday (laugh 2 (mods_cons 1 loudly (mods_cons 0 in_park mods_nil)) mary))."
        if is_timed
        else "Definition example_1 : PropT := (laugh 2 (mods_cons 1 loudly (mods_cons 0 in_park mods_nil)) mary)."
    )
    if (
        not isinstance(coq_code, str)
        or "Parameter loudly : Adv." not in coq_code
        or "Parameter in_park : Adv." not in coq_code
        or "Parameter loudly : Entity." in coq_code
        or "Parameter in_park : Entity." in coq_code
        or "Parameter laugh : forall n : nat, ModifierSeq n -> Entity -> PropT."
        not in coq_code
        or expected_definition not in coq_code
        or "Parameter Event : Type." in coq_code
        or "Parameter Agent :" in coq_code
        or "Parameter Theme :" in coq_code
    ):
        raise SystemExit(
            "web route smoke check failed: manner-locative intransitive Coq drift"
        )
    validate_successful_semantic_reading_contract(case, payload, page)
    expected_page_fragments = [
        'data-verification-scope-kind="registered_construction"',
        'data-verification-level="construction_rule"',
        "<dt>rule</dt><dd>manner_locative_intransitive_predication</dd>",
        'data-reading-name="manner_locative_intransitive_predication_single_reading"',
        "<dt>source</dt><dd>manner_locative_intransitive_predication</dd>",
        f"<dt>scope</dt><dd>{expected_scope}</dd>",
        expected_translation,
        (
            "Translation succeeded via construction rule "
            "manner_locative_intransitive_predication."
        ),
    ]
    require_text_fragments(
        page,
        expected_page_fragments,
        "manner-locative intransitive HTML",
    )
    if html.escape(sentence, quote=True) not in page:
        raise SystemExit(
            "web route smoke check failed: manner-locative intransitive page input drift"
        )


def validate_analyze_manner_two_location_intransitive_success(
    payload: dict,
    page: str,
    sentence: str,
) -> None:
    case = "analyze_manner_two_location_intransitive_success"
    is_timed = sentence == "Mary laughed loudly in the park near a window yesterday"
    expected_translation = (
        "at_T(yesterday, laugh(3)(loudly, in(park), near(window), mary))"
        if is_timed
        else "laugh(3)(loudly, in(park), near(window), mary)"
    )
    expected_scope = (
        "explicit_agent_with_manner_and_two_location_adv_at_time"
        if is_timed
        else "explicit_agent_with_manner_and_two_location_adv"
    )
    validate_analyze_success_envelope(
        payload,
        sentence,
        "manner_two_location_intransitive_predication",
        ["semantic_readings_check", "construction_hygiene"],
    )
    validate_verification_scope(
        payload,
        page,
        "manner_two_location_intransitive_predication",
        "registered_construction",
        "construction_rule",
        "manner_two_location_intransitive_predication",
    )
    if payload.get("kind") != "manner_two_location_intransitive_predication":
        raise SystemExit(
            "web route smoke check failed: manner-two-location intransitive kind drift"
        )
    if payload.get("dependent_type_translation") != expected_translation:
        raise SystemExit(
            "web route smoke check failed: manner-two-location intransitive translation drift"
        )
    if "certification_upgrade_plan" in payload or "construction_rule_draft" in payload:
        raise SystemExit(
            "web route smoke check failed: manner-two-location exposes fallback draft"
        )
    ast = payload.get("ast")
    application_ast = ast
    if is_timed and isinstance(ast, dict):
        if (
            ast.get("kind") != "time"
            or ast.get("operator") != "at"
            or ast.get("arguments") != ["yesterday"]
            or not isinstance(ast.get("body"), dict)
        ):
            raise SystemExit(
                "web route smoke check failed: timed manner-two-location AST drift"
            )
        application_ast = ast["body"]
    role_frame = (
        application_ast.get("role_frame", {}).get("roles")
        if isinstance(application_ast, dict)
        else None
    )
    modifier_roles = (
        application_ast.get("modifier_roles", {}).get("roles")
        if isinstance(application_ast, dict)
        else None
    )
    modifier_vector = (
        application_ast.get("modifier_vector", {}).get("items")
        if isinstance(application_ast, dict)
        else None
    )
    if (
        not isinstance(application_ast, dict)
        or application_ast.get("kind") != "application"
        or application_ast.get("function") != "laugh"
        or application_ast.get("arguments") != ["mary"]
        or application_ast.get("modifiers") != ["loudly", "in(park)", "near(window)"]
        or application_ast.get("adverb_count") != 3
        or not isinstance(role_frame, list)
        or len(role_frame) != 1
        or role_frame[0].get("role") != "Agent"
        or role_frame[0].get("type") != "Entity"
        or role_frame[0].get("source") != "explicit"
        or not isinstance(modifier_roles, list)
        or [role.get("type") for role in modifier_roles] != ["Adv", "Adv", "Adv"]
        or [role.get("semantic_role") for role in modifier_roles]
        != ["Manner", "Location", "Location"]
        or not isinstance(modifier_vector, list)
        or [item.get("tail_length") for item in modifier_vector] != [2, 1, 0]
    ):
        raise SystemExit(
            "web route smoke check failed: manner-two-location intransitive AST drift"
        )
    event_semantics = payload.get("event_semantics")
    typed_predication = (
        event_semantics.get("manner_two_location_intransitive_predication")
        if isinstance(event_semantics, dict)
        else None
    )
    if (
        not isinstance(event_semantics, dict)
        or event_semantics.get("analysis")
        != "manner-two-location-intransitive-predication"
        or not isinstance(typed_predication, dict)
        or typed_predication.get("predicate") != "laugh"
        or typed_predication.get("agent") != "mary"
        or typed_predication.get("agent_type") != "Entity"
        or typed_predication.get("modifiers") != ["loudly", "in(park)", "near(window)"]
        or [
            role.get("semantic_role")
            for role in typed_predication.get("modifier_roles", [])
            if isinstance(role, dict)
        ]
        != ["Manner", "Location", "Location"]
    ):
        raise SystemExit(
            "web route smoke check failed: manner-two-location intransitive analysis drift"
        )
    if is_timed:
        if typed_predication.get("time_modifier") != {
            "operator": "at",
            "argument": "yesterday",
        }:
            raise SystemExit(
                "web route smoke check failed: timed manner-two-location time drift"
            )
    elif "time_modifier" in typed_predication:
        raise SystemExit(
            "web route smoke check failed: untimed manner-two-location time drift"
        )
    hygiene = payload.get("construction_hygiene")
    if not isinstance(hygiene, dict) or hygiene.get("ok") is not True:
        raise SystemExit(
            "web route smoke check failed: manner-two-location hygiene drift"
        )
    readings = payload.get("semantic_readings")
    if not isinstance(readings, list) or len(readings) != 1:
        raise SystemExit(
            "web route smoke check failed: manner-two-location reading count drift"
        )
    validate_semantic_reading_summary(
        readings[0],
        {
            "name": "manner_two_location_intransitive_predication_single_reading",
            "scope": expected_scope,
            "source": "manner_two_location_intransitive_predication",
            "coq_definition": "example_1",
        },
        "none",
        case,
        expected_type=None,
    )
    coq_code = payload.get("coq_code")
    expected_definition = (
        "Definition example_1 : PropT := (at_T yesterday (laugh 3 (mods_cons 2 loudly (mods_cons 1 in_park (mods_cons 0 near_window mods_nil))) mary))."
        if is_timed
        else "Definition example_1 : PropT := (laugh 3 (mods_cons 2 loudly (mods_cons 1 in_park (mods_cons 0 near_window mods_nil))) mary)."
    )
    if (
        not isinstance(coq_code, str)
        or "Parameter loudly : Adv." not in coq_code
        or "Parameter in_park : Adv." not in coq_code
        or "Parameter near_window : Adv." not in coq_code
        or "Parameter loudly : Entity." in coq_code
        or "Parameter in_park : Entity." in coq_code
        or "Parameter near_window : Entity." in coq_code
        or "Parameter laugh : forall n : nat, ModifierSeq n -> Entity -> PropT."
        not in coq_code
        or expected_definition not in coq_code
        or "Parameter Event : Type." in coq_code
        or "Parameter Agent :" in coq_code
        or "Parameter Theme :" in coq_code
    ):
        raise SystemExit(
            "web route smoke check failed: manner-two-location Coq drift"
        )
    validate_successful_semantic_reading_contract(case, payload, page)
    expected_page_fragments = [
        'data-verification-scope-kind="registered_construction"',
        'data-verification-level="construction_rule"',
        "<dt>rule</dt><dd>manner_two_location_intransitive_predication</dd>",
        'data-reading-name="manner_two_location_intransitive_predication_single_reading"',
        "<dt>source</dt><dd>manner_two_location_intransitive_predication</dd>",
        f"<dt>scope</dt><dd>{expected_scope}</dd>",
        expected_translation,
        (
            "Translation succeeded via construction rule "
            "manner_two_location_intransitive_predication."
        ),
    ]
    require_text_fragments(
        page,
        expected_page_fragments,
        "manner-two-location intransitive HTML",
    )
    if html.escape(sentence, quote=True) not in page:
        raise SystemExit(
            "web route smoke check failed: manner-two-location page input drift"
        )


def validate_analyze_manner_three_location_intransitive_success(
    payload: dict,
    page: str,
    sentence: str,
) -> None:
    case = "analyze_manner_three_location_intransitive_success"
    is_timed = (
        sentence
        == "Mary laughed loudly in the park near a window beside a shelf yesterday"
    )
    expected_translation = (
        "at_T(yesterday, laugh(4)(loudly, in(park), near(window), beside(shelf), mary))"
        if is_timed
        else "laugh(4)(loudly, in(park), near(window), beside(shelf), mary)"
    )
    expected_scope = (
        "explicit_agent_with_manner_and_three_location_adv_at_time"
        if is_timed
        else "explicit_agent_with_manner_and_three_location_adv"
    )
    validate_analyze_success_envelope(
        payload,
        sentence,
        "manner_three_location_intransitive_predication",
        ["semantic_readings_check", "construction_hygiene"],
    )
    validate_verification_scope(
        payload,
        page,
        "manner_three_location_intransitive_predication",
        "registered_construction",
        "construction_rule",
        "manner_three_location_intransitive_predication",
    )
    if payload.get("kind") != "manner_three_location_intransitive_predication":
        raise SystemExit(
            "web route smoke check failed: manner-three-location intransitive kind drift"
        )
    if payload.get("dependent_type_translation") != expected_translation:
        raise SystemExit(
            "web route smoke check failed: manner-three-location intransitive translation drift"
        )
    if "certification_upgrade_plan" in payload or "construction_rule_draft" in payload:
        raise SystemExit(
            "web route smoke check failed: manner-three-location exposes fallback draft"
        )
    ast = payload.get("ast")
    application_ast = ast
    if is_timed and isinstance(ast, dict):
        if (
            ast.get("kind") != "time"
            or ast.get("operator") != "at"
            or ast.get("arguments") != ["yesterday"]
            or not isinstance(ast.get("body"), dict)
        ):
            raise SystemExit(
                "web route smoke check failed: timed manner-three-location AST drift"
            )
        application_ast = ast["body"]
    role_frame = (
        application_ast.get("role_frame", {}).get("roles")
        if isinstance(application_ast, dict)
        else None
    )
    modifier_roles = (
        application_ast.get("modifier_roles", {}).get("roles")
        if isinstance(application_ast, dict)
        else None
    )
    modifier_vector = (
        application_ast.get("modifier_vector", {}).get("items")
        if isinstance(application_ast, dict)
        else None
    )
    if (
        not isinstance(application_ast, dict)
        or application_ast.get("kind") != "application"
        or application_ast.get("function") != "laugh"
        or application_ast.get("arguments") != ["mary"]
        or application_ast.get("modifiers")
        != ["loudly", "in(park)", "near(window)", "beside(shelf)"]
        or application_ast.get("adverb_count") != 4
        or not isinstance(role_frame, list)
        or len(role_frame) != 1
        or role_frame[0].get("role") != "Agent"
        or role_frame[0].get("type") != "Entity"
        or role_frame[0].get("source") != "explicit"
        or not isinstance(modifier_roles, list)
        or [role.get("type") for role in modifier_roles]
        != ["Adv", "Adv", "Adv", "Adv"]
        or [role.get("semantic_role") for role in modifier_roles]
        != ["Manner", "Location", "Location", "Location"]
        or not isinstance(modifier_vector, list)
        or [item.get("tail_length") for item in modifier_vector] != [3, 2, 1, 0]
    ):
        raise SystemExit(
            "web route smoke check failed: manner-three-location intransitive AST drift"
        )
    event_semantics = payload.get("event_semantics")
    typed_predication = (
        event_semantics.get("manner_three_location_intransitive_predication")
        if isinstance(event_semantics, dict)
        else None
    )
    if (
        not isinstance(event_semantics, dict)
        or event_semantics.get("analysis")
        != "manner-three-location-intransitive-predication"
        or not isinstance(typed_predication, dict)
        or typed_predication.get("predicate") != "laugh"
        or typed_predication.get("agent") != "mary"
        or typed_predication.get("agent_type") != "Entity"
        or typed_predication.get("modifiers")
        != ["loudly", "in(park)", "near(window)", "beside(shelf)"]
        or [
            role.get("semantic_role")
            for role in typed_predication.get("modifier_roles", [])
            if isinstance(role, dict)
        ]
        != ["Manner", "Location", "Location", "Location"]
    ):
        raise SystemExit(
            "web route smoke check failed: manner-three-location intransitive analysis drift"
        )
    if is_timed:
        if typed_predication.get("time_modifier") != {
            "operator": "at",
            "argument": "yesterday",
        }:
            raise SystemExit(
                "web route smoke check failed: timed manner-three-location time drift"
            )
    elif "time_modifier" in typed_predication:
        raise SystemExit(
            "web route smoke check failed: untimed manner-three-location time drift"
        )
    hygiene = payload.get("construction_hygiene")
    if not isinstance(hygiene, dict) or hygiene.get("ok") is not True:
        raise SystemExit(
            "web route smoke check failed: manner-three-location hygiene drift"
        )
    readings = payload.get("semantic_readings")
    if not isinstance(readings, list) or len(readings) != 1:
        raise SystemExit(
            "web route smoke check failed: manner-three-location reading count drift"
        )
    validate_semantic_reading_summary(
        readings[0],
        {
            "name": "manner_three_location_intransitive_predication_single_reading",
            "scope": expected_scope,
            "source": "manner_three_location_intransitive_predication",
            "coq_definition": "example_1",
        },
        "none",
        case,
        expected_type=None,
    )
    coq_code = payload.get("coq_code")
    expected_definition = (
        "Definition example_1 : PropT := (at_T yesterday (laugh 4 (mods_cons 3 loudly (mods_cons 2 in_park (mods_cons 1 near_window (mods_cons 0 beside_shelf mods_nil)))) mary))."
        if is_timed
        else "Definition example_1 : PropT := (laugh 4 (mods_cons 3 loudly (mods_cons 2 in_park (mods_cons 1 near_window (mods_cons 0 beside_shelf mods_nil)))) mary)."
    )
    if (
        not isinstance(coq_code, str)
        or "Parameter loudly : Adv." not in coq_code
        or "Parameter in_park : Adv." not in coq_code
        or "Parameter near_window : Adv." not in coq_code
        or "Parameter beside_shelf : Adv." not in coq_code
        or "Parameter loudly : Entity." in coq_code
        or "Parameter in_park : Entity." in coq_code
        or "Parameter near_window : Entity." in coq_code
        or "Parameter beside_shelf : Entity." in coq_code
        or "Parameter laugh : forall n : nat, ModifierSeq n -> Entity -> PropT."
        not in coq_code
        or expected_definition not in coq_code
        or "Parameter Event : Type." in coq_code
        or "Parameter Agent :" in coq_code
        or "Parameter Theme :" in coq_code
    ):
        raise SystemExit(
            "web route smoke check failed: manner-three-location Coq drift"
        )
    validate_successful_semantic_reading_contract(case, payload, page)
    expected_page_fragments = [
        'data-verification-scope-kind="registered_construction"',
        'data-verification-level="construction_rule"',
        "<dt>rule</dt><dd>manner_three_location_intransitive_predication</dd>",
        'data-reading-name="manner_three_location_intransitive_predication_single_reading"',
        "<dt>source</dt><dd>manner_three_location_intransitive_predication</dd>",
        f"<dt>scope</dt><dd>{expected_scope}</dd>",
        expected_translation,
        (
            "Translation succeeded via construction rule "
            "manner_three_location_intransitive_predication."
        ),
    ]
    require_text_fragments(
        page,
        expected_page_fragments,
        "manner-three-location intransitive HTML",
    )
    if html.escape(sentence, quote=True) not in page:
        raise SystemExit(
            "web route smoke check failed: manner-three-location page input drift"
        )


def coq_modifier_sequence(constants: list[str]) -> str:
    term = "mods_nil"
    for index in range(len(constants) - 1, -1, -1):
        tail_length = len(constants) - index - 1
        term = f"(mods_cons {tail_length} {constants[index]} {term})"
    return term


def validate_analyze_manner_location_sequence_intransitive_success(
    payload: dict,
    page: str,
    sentence: str,
) -> None:
    case = "analyze_manner_location_sequence_intransitive_success"
    is_timed = sentence.endswith(" yesterday")
    expected_modifiers = [
        "loudly",
        "in(park)",
        "near(window)",
        "beside(shelf)",
        "under(lamp)",
    ]
    expected_constants = [
        "loudly",
        "in_park",
        "near_window",
        "beside_shelf",
        "under_lamp",
    ]
    if "on a table" in sentence:
        expected_modifiers.append("on(table)")
        expected_constants.append("on_table")
    expected_inner_translation = (
        f"laugh({len(expected_modifiers)})"
        f"({', '.join(expected_modifiers)}, mary)"
    )
    expected_translation = (
        f"at_T(yesterday, {expected_inner_translation})"
        if is_timed
        else expected_inner_translation
    )
    expected_scope = (
        "explicit_agent_with_manner_and_location_adv_sequence_at_time"
        if is_timed
        else "explicit_agent_with_manner_and_location_adv_sequence"
    )
    validate_analyze_success_envelope(
        payload,
        sentence,
        "manner_location_sequence_intransitive_predication",
        ["semantic_readings_check", "construction_hygiene"],
    )
    validate_verification_scope(
        payload,
        page,
        "manner_location_sequence_intransitive_predication",
        "registered_construction",
        "construction_rule",
        "manner_location_sequence_intransitive_predication",
    )
    if payload.get("kind") != "manner_location_sequence_intransitive_predication":
        raise SystemExit(
            "web route smoke check failed: manner-location-sequence kind drift"
        )
    if payload.get("dependent_type_translation") != expected_translation:
        raise SystemExit(
            "web route smoke check failed: manner-location-sequence translation drift"
        )
    if "certification_upgrade_plan" in payload or "construction_rule_draft" in payload:
        raise SystemExit(
            "web route smoke check failed: manner-location-sequence exposes fallback draft"
        )
    ast = payload.get("ast")
    application_ast = ast
    if is_timed and isinstance(ast, dict):
        if (
            ast.get("kind") != "time"
            or ast.get("operator") != "at"
            or ast.get("arguments") != ["yesterday"]
            or not isinstance(ast.get("body"), dict)
        ):
            raise SystemExit(
                "web route smoke check failed: timed manner-location-sequence AST drift"
            )
        application_ast = ast["body"]
    role_frame = (
        application_ast.get("role_frame", {}).get("roles")
        if isinstance(application_ast, dict)
        else None
    )
    modifier_roles = (
        application_ast.get("modifier_roles", {}).get("roles")
        if isinstance(application_ast, dict)
        else None
    )
    modifier_vector = (
        application_ast.get("modifier_vector", {}).get("items")
        if isinstance(application_ast, dict)
        else None
    )
    expected_roles = ["Manner", *["Location" for _ in expected_modifiers[1:]]]
    if (
        not isinstance(application_ast, dict)
        or application_ast.get("kind") != "application"
        or application_ast.get("function") != "laugh"
        or application_ast.get("arguments") != ["mary"]
        or application_ast.get("modifiers") != expected_modifiers
        or application_ast.get("adverb_count") != len(expected_modifiers)
        or not isinstance(role_frame, list)
        or len(role_frame) != 1
        or role_frame[0].get("role") != "Agent"
        or role_frame[0].get("type") != "Entity"
        or role_frame[0].get("source") != "explicit"
        or not isinstance(modifier_roles, list)
        or [role.get("type") for role in modifier_roles]
        != ["Adv" for _ in expected_modifiers]
        or [role.get("semantic_role") for role in modifier_roles] != expected_roles
        or not isinstance(modifier_vector, list)
        or [item.get("tail_length") for item in modifier_vector]
        != list(range(len(expected_modifiers) - 1, -1, -1))
    ):
        raise SystemExit(
            "web route smoke check failed: manner-location-sequence AST drift"
        )
    event_semantics = payload.get("event_semantics")
    typed_predication = (
        event_semantics.get("manner_location_sequence_intransitive_predication")
        if isinstance(event_semantics, dict)
        else None
    )
    if (
        not isinstance(event_semantics, dict)
        or event_semantics.get("analysis")
        != "manner-location-sequence-intransitive-predication"
        or not isinstance(typed_predication, dict)
        or typed_predication.get("predicate") != "laugh"
        or typed_predication.get("agent") != "mary"
        or typed_predication.get("agent_type") != "Entity"
        or typed_predication.get("modifiers") != expected_modifiers
        or typed_predication.get("location_modifier_count")
        != len(expected_modifiers) - 1
        or [
            role.get("semantic_role")
            for role in typed_predication.get("modifier_roles", [])
            if isinstance(role, dict)
        ]
        != expected_roles
    ):
        raise SystemExit(
            "web route smoke check failed: manner-location-sequence analysis drift"
        )
    if is_timed:
        if typed_predication.get("time_modifier") != {
            "operator": "at",
            "argument": "yesterday",
        }:
            raise SystemExit(
                "web route smoke check failed: timed manner-location-sequence time drift"
            )
    elif "time_modifier" in typed_predication:
        raise SystemExit(
            "web route smoke check failed: untimed manner-location-sequence time drift"
        )
    hygiene = payload.get("construction_hygiene")
    if not isinstance(hygiene, dict) or hygiene.get("ok") is not True:
        raise SystemExit(
            "web route smoke check failed: manner-location-sequence hygiene drift"
        )
    readings = payload.get("semantic_readings")
    if not isinstance(readings, list) or len(readings) != 1:
        raise SystemExit(
            "web route smoke check failed: manner-location-sequence reading count drift"
        )
    validate_semantic_reading_summary(
        readings[0],
        {
            "name": "manner_location_sequence_intransitive_predication_single_reading",
            "scope": expected_scope,
            "source": "manner_location_sequence_intransitive_predication",
            "coq_definition": "example_1",
        },
        "none",
        case,
        expected_type=None,
    )
    coq_code = payload.get("coq_code")
    modifier_seq = coq_modifier_sequence(expected_constants)
    expected_definition = (
        f"Definition example_1 : PropT := (at_T yesterday (laugh {len(expected_constants)} {modifier_seq} mary))."
        if is_timed
        else f"Definition example_1 : PropT := (laugh {len(expected_constants)} {modifier_seq} mary)."
    )
    if not isinstance(coq_code, str) or expected_definition not in coq_code:
        raise SystemExit(
            "web route smoke check failed: manner-location-sequence Coq definition drift"
        )
    for constant in expected_constants:
        if f"Parameter {constant} : Adv." not in coq_code:
            raise SystemExit(
                "web route smoke check failed: manner-location-sequence Adv declaration drift"
            )
        if f"Parameter {constant} : Entity." in coq_code:
            raise SystemExit(
                "web route smoke check failed: manner-location-sequence Entity surrogate drift"
            )
    if (
        "Parameter laugh : forall n : nat, ModifierSeq n -> Entity -> PropT."
        not in coq_code
        or "Parameter Event : Type." in coq_code
        or "Parameter Agent :" in coq_code
        or "Parameter Theme :" in coq_code
    ):
        raise SystemExit(
            "web route smoke check failed: manner-location-sequence Coq drift"
        )
    validate_successful_semantic_reading_contract(case, payload, page)
    expected_page_fragments = [
        'data-verification-scope-kind="registered_construction"',
        'data-verification-level="construction_rule"',
        "<dt>rule</dt><dd>manner_location_sequence_intransitive_predication</dd>",
        'data-reading-name="manner_location_sequence_intransitive_predication_single_reading"',
        "<dt>source</dt><dd>manner_location_sequence_intransitive_predication</dd>",
        f"<dt>scope</dt><dd>{expected_scope}</dd>",
        expected_translation,
        (
            "Translation succeeded via construction rule "
            "manner_location_sequence_intransitive_predication."
        ),
    ]
    require_text_fragments(
        page,
        expected_page_fragments,
        "manner-location-sequence intransitive HTML",
    )
    if html.escape(sentence, quote=True) not in page:
        raise SystemExit(
            "web route smoke check failed: manner-location-sequence page input drift"
        )


def validate_analyze_manner_location_instrument_intransitive_success(
    payload: dict,
    page: str,
    sentence: str,
) -> None:
    case = "analyze_manner_location_instrument_intransitive_success"
    is_timed = sentence.endswith(" yesterday")
    expected_modifiers = ["loudly", "in(park)"]
    expected_constants = ["loudly", "in_park"]
    if "near a window" in sentence:
        expected_modifiers.append("near(window)")
        expected_constants.append("near_window")
    if "beside a shelf" in sentence:
        expected_modifiers.append("beside(shelf)")
        expected_constants.append("beside_shelf")
    if "under a lamp" in sentence:
        expected_modifiers.append("under(lamp)")
        expected_constants.append("under_lamp")
    instrument_pairs = [
        ("with a telescope", "with(telescope)", "with_telescope"),
        ("with a camera", "with(camera)", "with_camera"),
        ("with a microphone", "with(microphone)", "with_microphone"),
    ]
    expected_instruments: list[str] = []
    for surface, modifier, constant in instrument_pairs:
        if surface in sentence:
            expected_modifiers.append(modifier)
            expected_constants.append(constant)
            expected_instruments.append(modifier)
    if not expected_instruments:
        raise SystemExit(
            "web route smoke check failed: manner-location-instrument missing instrument expectation"
        )
    expected_inner_translation = (
        f"laugh({len(expected_modifiers)})"
        f"({', '.join(expected_modifiers)}, mary)"
    )
    expected_translation = (
        f"at_T(yesterday, {expected_inner_translation})"
        if is_timed
        else expected_inner_translation
    )
    expected_scope = (
        "explicit_agent_with_manner_location_and_instrument_adv_sequence_at_time"
        if is_timed
        else "explicit_agent_with_manner_location_and_instrument_adv_sequence"
    )
    validate_analyze_success_envelope(
        payload,
        sentence,
        "manner_location_instrument_intransitive_predication",
        ["semantic_readings_check", "construction_hygiene"],
    )
    validate_verification_scope(
        payload,
        page,
        "manner_location_instrument_intransitive_predication",
        "registered_construction",
        "construction_rule",
        "manner_location_instrument_intransitive_predication",
    )
    if payload.get("kind") != "manner_location_instrument_intransitive_predication":
        raise SystemExit(
            "web route smoke check failed: manner-location-instrument kind drift"
        )
    if payload.get("dependent_type_translation") != expected_translation:
        raise SystemExit(
            "web route smoke check failed: manner-location-instrument translation drift"
        )
    if "certification_upgrade_plan" in payload or "construction_rule_draft" in payload:
        raise SystemExit(
            "web route smoke check failed: manner-location-instrument exposes fallback draft"
        )
    ast = payload.get("ast")
    application_ast = ast
    if is_timed and isinstance(ast, dict):
        if (
            ast.get("kind") != "time"
            or ast.get("operator") != "at"
            or ast.get("arguments") != ["yesterday"]
            or not isinstance(ast.get("body"), dict)
        ):
            raise SystemExit(
                "web route smoke check failed: timed manner-location-instrument AST drift"
            )
        application_ast = ast["body"]
    role_frame = (
        application_ast.get("role_frame", {}).get("roles")
        if isinstance(application_ast, dict)
        else None
    )
    modifier_roles = (
        application_ast.get("modifier_roles", {}).get("roles")
        if isinstance(application_ast, dict)
        else None
    )
    modifier_vector = (
        application_ast.get("modifier_vector", {}).get("items")
        if isinstance(application_ast, dict)
        else None
    )
    expected_roles = [
        "Manner",
        *["Location" for _ in range(1, len(expected_modifiers) - len(expected_instruments))],
        *["Instrument" for _ in expected_instruments],
    ]
    if (
        not isinstance(application_ast, dict)
        or application_ast.get("kind") != "application"
        or application_ast.get("function") != "laugh"
        or application_ast.get("arguments") != ["mary"]
        or application_ast.get("modifiers") != expected_modifiers
        or application_ast.get("adverb_count") != len(expected_modifiers)
        or not isinstance(role_frame, list)
        or len(role_frame) != 1
        or role_frame[0].get("role") != "Agent"
        or role_frame[0].get("type") != "Entity"
        or role_frame[0].get("source") != "explicit"
        or not isinstance(modifier_roles, list)
        or [role.get("type") for role in modifier_roles]
        != ["Adv" for _ in expected_modifiers]
        or [role.get("semantic_role") for role in modifier_roles] != expected_roles
        or not isinstance(modifier_vector, list)
        or [item.get("tail_length") for item in modifier_vector]
        != list(range(len(expected_modifiers) - 1, -1, -1))
    ):
        raise SystemExit(
            "web route smoke check failed: manner-location-instrument AST drift"
        )
    event_semantics = payload.get("event_semantics")
    typed_predication = (
        event_semantics.get("manner_location_instrument_intransitive_predication")
        if isinstance(event_semantics, dict)
        else None
    )
    if (
        not isinstance(event_semantics, dict)
        or event_semantics.get("analysis")
        != "manner-location-instrument-intransitive-predication"
        or not isinstance(typed_predication, dict)
        or typed_predication.get("predicate") != "laugh"
        or typed_predication.get("agent") != "mary"
        or typed_predication.get("agent_type") != "Entity"
        or typed_predication.get("modifiers") != expected_modifiers
        or typed_predication.get("location_modifier_count")
        != len(expected_modifiers) - len(expected_instruments) - 1
        or typed_predication.get("instrument_modifier_count")
        != len(expected_instruments)
        or typed_predication.get("instrument_modifiers") != expected_instruments
        or typed_predication.get("instrument_modifier") != expected_instruments[-1]
        or [
            role.get("semantic_role")
            for role in typed_predication.get("modifier_roles", [])
            if isinstance(role, dict)
        ]
        != expected_roles
    ):
        raise SystemExit(
            "web route smoke check failed: manner-location-instrument analysis drift"
        )
    if is_timed:
        if typed_predication.get("time_modifier") != {
            "operator": "at",
            "argument": "yesterday",
        }:
            raise SystemExit(
                "web route smoke check failed: timed manner-location-instrument time drift"
            )
    elif "time_modifier" in typed_predication:
        raise SystemExit(
            "web route smoke check failed: untimed manner-location-instrument time drift"
        )
    hygiene = payload.get("construction_hygiene")
    if not isinstance(hygiene, dict) or hygiene.get("ok") is not True:
        raise SystemExit(
            "web route smoke check failed: manner-location-instrument hygiene drift"
        )
    readings = payload.get("semantic_readings")
    if not isinstance(readings, list) or len(readings) != 1:
        raise SystemExit(
            "web route smoke check failed: manner-location-instrument reading count drift"
        )
    validate_semantic_reading_summary(
        readings[0],
        {
            "name": "manner_location_instrument_intransitive_predication_single_reading",
            "scope": expected_scope,
            "source": "manner_location_instrument_intransitive_predication",
            "coq_definition": "example_1",
        },
        "none",
        case,
        expected_type=None,
    )
    coq_code = payload.get("coq_code")
    modifier_seq = coq_modifier_sequence(expected_constants)
    expected_definition = (
        f"Definition example_1 : PropT := (at_T yesterday (laugh {len(expected_constants)} {modifier_seq} mary))."
        if is_timed
        else f"Definition example_1 : PropT := (laugh {len(expected_constants)} {modifier_seq} mary)."
    )
    if not isinstance(coq_code, str) or expected_definition not in coq_code:
        raise SystemExit(
            "web route smoke check failed: manner-location-instrument Coq definition drift"
        )
    for constant in expected_constants:
        if f"Parameter {constant} : Adv." not in coq_code:
            raise SystemExit(
                "web route smoke check failed: manner-location-instrument Adv declaration drift"
            )
        if f"Parameter {constant} : Entity." in coq_code:
            raise SystemExit(
                "web route smoke check failed: manner-location-instrument Entity surrogate drift"
            )
    if (
        "Parameter laugh : forall n : nat, ModifierSeq n -> Entity -> PropT."
        not in coq_code
        or "Parameter Event : Type." in coq_code
        or "Parameter Agent :" in coq_code
        or "Parameter Theme :" in coq_code
    ):
        raise SystemExit(
            "web route smoke check failed: manner-location-instrument Coq drift"
        )
    validate_successful_semantic_reading_contract(case, payload, page)
    expected_page_fragments = [
        'data-verification-scope-kind="registered_construction"',
        'data-verification-level="construction_rule"',
        "<dt>rule</dt><dd>manner_location_instrument_intransitive_predication</dd>",
        'data-reading-name="manner_location_instrument_intransitive_predication_single_reading"',
        "<dt>source</dt><dd>manner_location_instrument_intransitive_predication</dd>",
        f"<dt>scope</dt><dd>{expected_scope}</dd>",
        expected_translation,
        (
            "Translation succeeded via construction rule "
            "manner_location_instrument_intransitive_predication."
        ),
    ]
    require_text_fragments(
        page,
        expected_page_fragments,
        "manner-location-instrument intransitive HTML",
    )
    if html.escape(sentence, quote=True) not in page:
        raise SystemExit(
            "web route smoke check failed: manner-location-instrument page input drift"
        )


def validate_analyze_manner_mixed_location_instrument_intransitive_success(
    payload: dict,
    page: str,
    sentence: str,
) -> None:
    case = "analyze_manner_mixed_location_instrument_intransitive_success"
    is_timed = sentence.endswith(" yesterday")
    expected_modifiers = [
        "loudly",
        "in(park)",
        "with(telescope)",
        "near(window)",
    ]
    expected_constants = ["loudly", "in_park", "with_telescope", "near_window"]
    expected_roles = ["Manner", "Location", "Instrument", "Location"]
    if "beside a shelf" in sentence:
        expected_modifiers.append("beside(shelf)")
        expected_constants.append("beside_shelf")
        expected_roles.append("Location")
    expected_modifiers.append("with(camera)")
    expected_constants.append("with_camera")
    expected_roles.append("Instrument")
    expected_inner_translation = (
        f"laugh({len(expected_modifiers)})"
        f"({', '.join(expected_modifiers)}, mary)"
    )
    expected_translation = (
        f"at_T(yesterday, {expected_inner_translation})"
        if is_timed
        else expected_inner_translation
    )
    expected_scope = (
        "explicit_agent_with_manner_mixed_location_instrument_adv_sequence_at_time"
        if is_timed
        else "explicit_agent_with_manner_mixed_location_instrument_adv_sequence"
    )
    validate_analyze_success_envelope(
        payload,
        sentence,
        "manner_mixed_location_instrument_intransitive_predication",
        ["semantic_readings_check", "construction_hygiene"],
    )
    validate_verification_scope(
        payload,
        page,
        "manner_mixed_location_instrument_intransitive_predication",
        "registered_construction",
        "construction_rule",
        "manner_mixed_location_instrument_intransitive_predication",
    )
    if payload.get("kind") != "manner_mixed_location_instrument_intransitive_predication":
        raise SystemExit(
            "web route smoke check failed: manner-mixed-location-instrument kind drift"
        )
    if payload.get("dependent_type_translation") != expected_translation:
        raise SystemExit(
            "web route smoke check failed: manner-mixed-location-instrument translation drift"
        )
    if "certification_upgrade_plan" in payload or "construction_rule_draft" in payload:
        raise SystemExit(
            "web route smoke check failed: manner-mixed-location-instrument exposes fallback draft"
        )
    ast = payload.get("ast")
    application_ast = ast
    if is_timed and isinstance(ast, dict):
        if (
            ast.get("kind") != "time"
            or ast.get("operator") != "at"
            or ast.get("arguments") != ["yesterday"]
            or not isinstance(ast.get("body"), dict)
        ):
            raise SystemExit(
                "web route smoke check failed: timed manner-mixed-location-instrument AST drift"
            )
        application_ast = ast["body"]
    role_frame = (
        application_ast.get("role_frame", {}).get("roles")
        if isinstance(application_ast, dict)
        else None
    )
    modifier_roles = (
        application_ast.get("modifier_roles", {}).get("roles")
        if isinstance(application_ast, dict)
        else None
    )
    modifier_vector = (
        application_ast.get("modifier_vector", {}).get("items")
        if isinstance(application_ast, dict)
        else None
    )
    if (
        not isinstance(application_ast, dict)
        or application_ast.get("kind") != "application"
        or application_ast.get("function") != "laugh"
        or application_ast.get("arguments") != ["mary"]
        or application_ast.get("modifiers") != expected_modifiers
        or application_ast.get("adverb_count") != len(expected_modifiers)
        or not isinstance(role_frame, list)
        or len(role_frame) != 1
        or role_frame[0].get("role") != "Agent"
        or role_frame[0].get("type") != "Entity"
        or role_frame[0].get("source") != "explicit"
        or not isinstance(modifier_roles, list)
        or [role.get("type") for role in modifier_roles]
        != ["Adv" for _ in expected_modifiers]
        or [role.get("semantic_role") for role in modifier_roles] != expected_roles
        or not isinstance(modifier_vector, list)
        or [item.get("tail_length") for item in modifier_vector]
        != list(range(len(expected_modifiers) - 1, -1, -1))
    ):
        raise SystemExit(
            "web route smoke check failed: manner-mixed-location-instrument AST drift"
        )
    event_semantics = payload.get("event_semantics")
    typed_predication = (
        event_semantics.get(
            "manner_mixed_location_instrument_intransitive_predication"
        )
        if isinstance(event_semantics, dict)
        else None
    )
    expected_locations = [
        modifier
        for modifier, role in zip(expected_modifiers, expected_roles)
        if role == "Location"
    ]
    expected_instruments = [
        modifier
        for modifier, role in zip(expected_modifiers, expected_roles)
        if role == "Instrument"
    ]
    if (
        not isinstance(event_semantics, dict)
        or event_semantics.get("analysis")
        != "manner-mixed-location-instrument-intransitive-predication"
        or not isinstance(typed_predication, dict)
        or typed_predication.get("predicate") != "laugh"
        or typed_predication.get("agent") != "mary"
        or typed_predication.get("agent_type") != "Entity"
        or typed_predication.get("modifiers") != expected_modifiers
        or typed_predication.get("modifier_role_pattern") != expected_roles
        or typed_predication.get("location_modifier_count") != len(expected_locations)
        or typed_predication.get("location_modifiers") != expected_locations
        or typed_predication.get("instrument_modifier_count") != len(expected_instruments)
        or typed_predication.get("instrument_modifiers") != expected_instruments
        or typed_predication.get("interleaving_count") != 1
    ):
        raise SystemExit(
            "web route smoke check failed: manner-mixed-location-instrument analysis drift"
        )
    if is_timed:
        if typed_predication.get("time_modifier") != {
            "operator": "at",
            "argument": "yesterday",
        }:
            raise SystemExit(
                "web route smoke check failed: timed manner-mixed-location-instrument time drift"
            )
    elif "time_modifier" in typed_predication:
        raise SystemExit(
            "web route smoke check failed: untimed manner-mixed-location-instrument time drift"
        )
    hygiene = payload.get("construction_hygiene")
    if not isinstance(hygiene, dict) or hygiene.get("ok") is not True:
        raise SystemExit(
            "web route smoke check failed: manner-mixed-location-instrument hygiene drift"
        )
    readings = payload.get("semantic_readings")
    if not isinstance(readings, list) or len(readings) != 1:
        raise SystemExit(
            "web route smoke check failed: manner-mixed-location-instrument reading count drift"
        )
    validate_semantic_reading_summary(
        readings[0],
        {
            "name": (
                "manner_mixed_location_instrument_intransitive_predication_single_reading"
            ),
            "scope": expected_scope,
            "source": "manner_mixed_location_instrument_intransitive_predication",
            "coq_definition": "example_1",
        },
        "none",
        case,
        expected_type=None,
    )
    coq_code = payload.get("coq_code")
    modifier_seq = coq_modifier_sequence(expected_constants)
    expected_definition = (
        f"Definition example_1 : PropT := (at_T yesterday (laugh {len(expected_constants)} {modifier_seq} mary))."
        if is_timed
        else f"Definition example_1 : PropT := (laugh {len(expected_constants)} {modifier_seq} mary)."
    )
    if not isinstance(coq_code, str) or expected_definition not in coq_code:
        raise SystemExit(
            "web route smoke check failed: manner-mixed-location-instrument Coq definition drift"
        )
    for constant in expected_constants:
        if f"Parameter {constant} : Adv." not in coq_code:
            raise SystemExit(
                "web route smoke check failed: manner-mixed-location-instrument Adv declaration drift"
            )
        if f"Parameter {constant} : Entity." in coq_code:
            raise SystemExit(
                "web route smoke check failed: manner-mixed-location-instrument Entity surrogate drift"
            )
    if (
        "Parameter laugh : forall n : nat, ModifierSeq n -> Entity -> PropT."
        not in coq_code
        or "Parameter Event : Type." in coq_code
        or "Parameter Agent :" in coq_code
        or "Parameter Theme :" in coq_code
    ):
        raise SystemExit(
            "web route smoke check failed: manner-mixed-location-instrument Coq drift"
        )
    validate_successful_semantic_reading_contract(case, payload, page)
    expected_page_fragments = [
        'data-verification-scope-kind="registered_construction"',
        'data-verification-level="construction_rule"',
        (
            "<dt>rule</dt><dd>"
            "manner_mixed_location_instrument_intransitive_predication</dd>"
        ),
        (
            'data-reading-name="'
            "manner_mixed_location_instrument_intransitive_predication_single_reading"
            '"'
        ),
        (
            "<dt>source</dt><dd>"
            "manner_mixed_location_instrument_intransitive_predication</dd>"
        ),
        f"<dt>scope</dt><dd>{expected_scope}</dd>",
        expected_translation,
        (
            "Translation succeeded via construction rule "
            "manner_mixed_location_instrument_intransitive_predication."
        ),
    ]
    require_text_fragments(
        page,
        expected_page_fragments,
        "manner-mixed-location-instrument intransitive HTML",
    )
    if html.escape(sentence, quote=True) not in page:
        raise SystemExit(
            "web route smoke check failed: manner-mixed-location-instrument page input drift"
        )


def validate_analyze_manner_mixed_directional_instrument_intransitive_success(
    payload: dict,
    page: str,
    sentence: str,
) -> None:
    case = "analyze_manner_mixed_directional_instrument_intransitive_success"
    is_timed = sentence.endswith(" yesterday")
    expected_modifiers = ["loudly", "in(park)", "with(telescope)"]
    expected_constants = ["loudly", "in_park", "with_telescope"]
    expected_roles = ["Manner", "Location", "Instrument"]
    expected_sources: list[str] = []
    expected_goals: list[str] = []
    if "from a window" in sentence:
        expected_modifiers.append("from(window)")
        expected_constants.append("from_window")
        expected_roles.append("Source")
        expected_sources.append("from(window)")
    elif "into a room" in sentence:
        expected_modifiers.append("into(room)")
        expected_constants.append("into_room")
        expected_roles.append("Goal")
        expected_goals.append("into(room)")
    else:
        raise SystemExit(
            "web route smoke check failed: manner-mixed-directional-instrument fixture drift"
        )
    expected_modifiers.append("with(camera)")
    expected_constants.append("with_camera")
    expected_roles.append("Instrument")
    expected_inner_translation = (
        f"laugh({len(expected_modifiers)})"
        f"({', '.join(expected_modifiers)}, mary)"
    )
    expected_translation = (
        f"at_T(yesterday, {expected_inner_translation})"
        if is_timed
        else expected_inner_translation
    )
    expected_scope = (
        "explicit_agent_with_manner_mixed_directional_instrument_adv_sequence_at_time"
        if is_timed
        else "explicit_agent_with_manner_mixed_directional_instrument_adv_sequence"
    )
    validate_analyze_success_envelope(
        payload,
        sentence,
        "manner_mixed_directional_instrument_intransitive_predication",
        ["semantic_readings_check", "construction_hygiene"],
    )
    validate_verification_scope(
        payload,
        page,
        "manner_mixed_directional_instrument_intransitive_predication",
        "registered_construction",
        "construction_rule",
        "manner_mixed_directional_instrument_intransitive_predication",
    )
    if payload.get("kind") != "manner_mixed_directional_instrument_intransitive_predication":
        raise SystemExit(
            "web route smoke check failed: manner-mixed-directional-instrument kind drift"
        )
    if payload.get("dependent_type_translation") != expected_translation:
        raise SystemExit(
            "web route smoke check failed: manner-mixed-directional-instrument translation drift"
        )
    if "certification_upgrade_plan" in payload or "construction_rule_draft" in payload:
        raise SystemExit(
            "web route smoke check failed: manner-mixed-directional-instrument exposes fallback draft"
        )
    ast = payload.get("ast")
    application_ast = ast
    if is_timed and isinstance(ast, dict):
        if (
            ast.get("kind") != "time"
            or ast.get("operator") != "at"
            or ast.get("arguments") != ["yesterday"]
            or not isinstance(ast.get("body"), dict)
        ):
            raise SystemExit(
                "web route smoke check failed: timed manner-mixed-directional-instrument AST drift"
            )
        application_ast = ast["body"]
    role_frame = (
        application_ast.get("role_frame", {}).get("roles")
        if isinstance(application_ast, dict)
        else None
    )
    modifier_roles = (
        application_ast.get("modifier_roles", {}).get("roles")
        if isinstance(application_ast, dict)
        else None
    )
    modifier_vector = (
        application_ast.get("modifier_vector", {}).get("items")
        if isinstance(application_ast, dict)
        else None
    )
    if (
        not isinstance(application_ast, dict)
        or application_ast.get("kind") != "application"
        or application_ast.get("function") != "laugh"
        or application_ast.get("arguments") != ["mary"]
        or application_ast.get("modifiers") != expected_modifiers
        or application_ast.get("adverb_count") != len(expected_modifiers)
        or not isinstance(role_frame, list)
        or len(role_frame) != 1
        or role_frame[0].get("role") != "Agent"
        or role_frame[0].get("type") != "Entity"
        or role_frame[0].get("source") != "explicit"
        or not isinstance(modifier_roles, list)
        or [role.get("type") for role in modifier_roles]
        != ["Adv" for _ in expected_modifiers]
        or [role.get("semantic_role") for role in modifier_roles] != expected_roles
        or not isinstance(modifier_vector, list)
        or [item.get("tail_length") for item in modifier_vector]
        != list(range(len(expected_modifiers) - 1, -1, -1))
    ):
        raise SystemExit(
            "web route smoke check failed: manner-mixed-directional-instrument AST drift"
        )
    event_semantics = payload.get("event_semantics")
    typed_predication = (
        event_semantics.get(
            "manner_mixed_directional_instrument_intransitive_predication"
        )
        if isinstance(event_semantics, dict)
        else None
    )
    expected_locations = [
        modifier
        for modifier, role in zip(expected_modifiers, expected_roles)
        if role == "Location"
    ]
    expected_instruments = [
        modifier
        for modifier, role in zip(expected_modifiers, expected_roles)
        if role == "Instrument"
    ]
    if (
        not isinstance(event_semantics, dict)
        or event_semantics.get("analysis")
        != "manner-mixed-directional-instrument-intransitive-predication"
        or not isinstance(typed_predication, dict)
        or typed_predication.get("predicate") != "laugh"
        or typed_predication.get("agent") != "mary"
        or typed_predication.get("agent_type") != "Entity"
        or typed_predication.get("modifiers") != expected_modifiers
        or typed_predication.get("modifier_role_pattern") != expected_roles
        or typed_predication.get("location_modifiers") != expected_locations
        or typed_predication.get("instrument_modifiers") != expected_instruments
        or typed_predication.get("source_modifiers") != expected_sources
        or typed_predication.get("goal_modifiers") != expected_goals
        or typed_predication.get("directional_modifier_count") != 1
        or typed_predication.get("directional_after_instrument_count") != 1
        or typed_predication.get("directional_to_instrument_count") != 1
    ):
        raise SystemExit(
            "web route smoke check failed: manner-mixed-directional-instrument analysis drift"
        )
    if is_timed:
        if typed_predication.get("time_modifier") != {
            "operator": "at",
            "argument": "yesterday",
        }:
            raise SystemExit(
                "web route smoke check failed: timed manner-mixed-directional-instrument time drift"
            )
    elif "time_modifier" in typed_predication:
        raise SystemExit(
            "web route smoke check failed: untimed manner-mixed-directional-instrument time drift"
        )
    hygiene = payload.get("construction_hygiene")
    if not isinstance(hygiene, dict) or hygiene.get("ok") is not True:
        raise SystemExit(
            "web route smoke check failed: manner-mixed-directional-instrument hygiene drift"
        )
    readings = payload.get("semantic_readings")
    if not isinstance(readings, list) or len(readings) != 1:
        raise SystemExit(
            "web route smoke check failed: manner-mixed-directional-instrument reading count drift"
        )
    validate_semantic_reading_summary(
        readings[0],
        {
            "name": (
                "manner_mixed_directional_instrument_intransitive_predication_single_reading"
            ),
            "scope": expected_scope,
            "source": "manner_mixed_directional_instrument_intransitive_predication",
            "coq_definition": "example_1",
        },
        "none",
        case,
        expected_type=None,
    )
    coq_code = payload.get("coq_code")
    modifier_seq = coq_modifier_sequence(expected_constants)
    expected_definition = (
        f"Definition example_1 : PropT := (at_T yesterday (laugh {len(expected_constants)} {modifier_seq} mary))."
        if is_timed
        else f"Definition example_1 : PropT := (laugh {len(expected_constants)} {modifier_seq} mary)."
    )
    if not isinstance(coq_code, str) or expected_definition not in coq_code:
        raise SystemExit(
            "web route smoke check failed: manner-mixed-directional-instrument Coq definition drift"
        )
    for constant in expected_constants:
        if f"Parameter {constant} : Adv." not in coq_code:
            raise SystemExit(
                "web route smoke check failed: manner-mixed-directional-instrument Adv declaration drift"
            )
        if f"Parameter {constant} : Entity." in coq_code:
            raise SystemExit(
                "web route smoke check failed: manner-mixed-directional-instrument Entity surrogate drift"
            )
    if (
        "Parameter laugh : forall n : nat, ModifierSeq n -> Entity -> PropT."
        not in coq_code
        or "Parameter Event : Type." in coq_code
        or "Parameter Agent :" in coq_code
        or "Parameter Theme :" in coq_code
    ):
        raise SystemExit(
            "web route smoke check failed: manner-mixed-directional-instrument Coq drift"
        )
    validate_successful_semantic_reading_contract(case, payload, page)
    expected_page_fragments = [
        'data-verification-scope-kind="registered_construction"',
        'data-verification-level="construction_rule"',
        (
            "<dt>rule</dt><dd>"
            "manner_mixed_directional_instrument_intransitive_predication</dd>"
        ),
        (
            'data-reading-name="'
            "manner_mixed_directional_instrument_intransitive_predication_single_reading"
            '"'
        ),
        (
            "<dt>source</dt><dd>"
            "manner_mixed_directional_instrument_intransitive_predication</dd>"
        ),
        f"<dt>scope</dt><dd>{expected_scope}</dd>",
        expected_translation,
        (
            "Translation succeeded via construction rule "
            "manner_mixed_directional_instrument_intransitive_predication."
        ),
    ]
    require_text_fragments(
        page,
        expected_page_fragments,
        "manner-mixed-directional-instrument intransitive HTML",
    )
    if html.escape(sentence, quote=True) not in page:
        raise SystemExit(
            "web route smoke check failed: manner-mixed-directional-instrument page input drift"
        )


def validate_analyze_modified_transitive_success(
    payload: dict,
    page: str,
    sentence: str,
) -> None:
    case = "analyze_modified_transitive_success"
    is_timed = sentence.endswith(" yesterday")
    expected_modifiers = ["in(gallery)"]
    expected_modifier_roles = ["Location"]
    if "with a telescope" in sentence:
        expected_modifiers.append("with(telescope)")
        expected_modifier_roles.append("Instrument")
    if "near a window" in sentence:
        expected_modifiers.append("near(window)")
        expected_modifier_roles.append("Location")
    if "beside a shelf" in sentence:
        expected_modifiers.append("beside(shelf)")
        expected_modifier_roles.append("Location")
    if "under a lamp" in sentence:
        expected_modifiers.append("under(lamp)")
        expected_modifier_roles.append("Location")
    expected_inner_translation = (
        f"admire({len(expected_modifiers)})"
        f"({', '.join(expected_modifiers)}, mary, painting)"
    )
    expected_translation = (
        f"at_T(yesterday, {expected_inner_translation})"
        if is_timed
        else expected_inner_translation
    )
    expected_scope = (
        (
            "explicit_agent_theme_with_adv_at_time"
            if len(expected_modifiers) == 1
            else "explicit_agent_theme_with_adv_sequence_at_time"
        )
        if is_timed
        else (
            "explicit_agent_theme_with_adv"
            if len(expected_modifiers) == 1
            else "explicit_agent_theme_with_adv_sequence"
        )
    )
    validate_analyze_success_envelope(
        payload,
        sentence,
        "modified_transitive_predication",
        ["semantic_readings_check", "construction_hygiene"],
    )
    validate_verification_scope(
        payload,
        page,
        "modified_transitive_predication",
        "registered_construction",
        "construction_rule",
        "modified_transitive_predication",
    )
    if payload.get("kind") != "modified_transitive_predication":
        raise SystemExit("web route smoke check failed: modified transitive kind drift")
    if payload.get("dependent_type_translation") != expected_translation:
        raise SystemExit("web route smoke check failed: modified transitive translation drift")
    if "certification_upgrade_plan" in payload or "construction_rule_draft" in payload:
        raise SystemExit("web route smoke check failed: modified transitive exposes fallback draft")
    ast = payload.get("ast")
    application_ast = ast
    if is_timed and isinstance(ast, dict):
        if (
            ast.get("kind") != "time"
            or ast.get("operator") != "at"
            or ast.get("arguments") != ["yesterday"]
            or not isinstance(ast.get("body"), dict)
        ):
            raise SystemExit("web route smoke check failed: timed modified transitive AST drift")
        application_ast = ast["body"]
    role_frame = (
        application_ast.get("role_frame", {}).get("roles")
        if isinstance(application_ast, dict)
        else None
    )
    modifier_roles = (
        application_ast.get("modifier_roles", {}).get("roles")
        if isinstance(application_ast, dict)
        else None
    )
    if (
        not isinstance(application_ast, dict)
        or application_ast.get("kind") != "application"
        or application_ast.get("function") != "admire"
        or application_ast.get("arguments") != ["mary", "painting"]
        or application_ast.get("modifiers") != expected_modifiers
        or application_ast.get("adverb_count") != len(expected_modifiers)
        or not isinstance(role_frame, list)
        or len(role_frame) != 2
        or role_frame[0].get("role") != "Agent"
        or role_frame[0].get("type") != "Entity"
        or role_frame[0].get("source") != "explicit"
        or role_frame[1].get("role") != "Theme"
        or role_frame[1].get("type") != "Entity"
        or role_frame[1].get("source") != "explicit"
        or not isinstance(modifier_roles, list)
        or len(modifier_roles) != len(expected_modifiers)
    ):
        raise SystemExit("web route smoke check failed: modified transitive AST drift")
    for index, modifier in enumerate(expected_modifiers):
        if (
            modifier_roles[index].get("modifier") != modifier
            or modifier_roles[index].get("type") != "Adv"
            or modifier_roles[index].get("semantic_role") != expected_modifier_roles[index]
        ):
            raise SystemExit("web route smoke check failed: modified transitive modifier drift")
    event_semantics = payload.get("event_semantics")
    modified = (
        event_semantics.get("modified_transitive_predication")
        if isinstance(event_semantics, dict)
        else None
    )
    if (
        not isinstance(event_semantics, dict)
        or event_semantics.get("analysis") != "modified-transitive-predication"
        or not isinstance(modified, dict)
        or modified.get("predicate") != "admire"
        or modified.get("agent") != "mary"
        or modified.get("theme") != "painting"
        or modified.get("theme_type") != "Entity"
        or modified.get("modifiers") != expected_modifiers
        or not isinstance(modified.get("modifier_roles"), list)
        or modified["modifier_roles"][0].get("type") != "Adv"
    ):
        raise SystemExit("web route smoke check failed: modified transitive analysis drift")
    if is_timed:
        if modified.get("time_modifier") != {"operator": "at", "argument": "yesterday"}:
            raise SystemExit("web route smoke check failed: timed modified transitive time drift")
    elif "time_modifier" in modified:
        raise SystemExit("web route smoke check failed: untimed modified transitive time drift")
    hygiene = payload.get("construction_hygiene")
    if not isinstance(hygiene, dict) or hygiene.get("ok") is not True:
        raise SystemExit("web route smoke check failed: modified transitive hygiene drift")
    readings = payload.get("semantic_readings")
    if not isinstance(readings, list) or len(readings) != 1:
        raise SystemExit("web route smoke check failed: modified transitive reading count drift")
    validate_semantic_reading_summary(
        readings[0],
        {
            "name": "modified_transitive_predication_single_reading",
            "scope": expected_scope,
            "source": "modified_transitive_predication",
            "coq_definition": "example_1",
        },
        "none",
        case,
        expected_type=None,
    )
    coq_code = payload.get("coq_code")
    if (
        not isinstance(coq_code, str)
        or "Parameter admire : forall n : nat" not in coq_code
        or "Parameter in_gallery : Adv." not in coq_code
        or "Parameter in_gallery : Entity." in coq_code
        or (
            "with(telescope)" in expected_modifiers
            and "Parameter with_telescope : Adv." not in coq_code
        )
        or "Parameter with_telescope : Entity." in coq_code
        or (
            "near(window)" in expected_modifiers
            and "Parameter near_window : Adv." not in coq_code
        )
        or "Parameter near_window : Entity." in coq_code
        or (
            "beside(shelf)" in expected_modifiers
            and "Parameter beside_shelf : Adv." not in coq_code
        )
        or "Parameter beside_shelf : Entity." in coq_code
        or (
            "under(lamp)" in expected_modifiers
            and "Parameter under_lamp : Adv." not in coq_code
        )
        or "Parameter under_lamp : Entity." in coq_code
        or "Definition example_1" not in coq_code
        or "Parameter Event : Type." in coq_code
        or "Parameter Agent :" in coq_code
        or "Parameter Theme :" in coq_code
    ):
        raise SystemExit("web route smoke check failed: modified transitive Coq drift")
    validate_successful_semantic_reading_contract(case, payload, page)
    expected_page_fragments = [
        'data-verification-scope-kind="registered_construction"',
        'data-verification-level="construction_rule"',
        "<dt>rule</dt><dd>modified_transitive_predication</dd>",
        'data-reading-name="modified_transitive_predication_single_reading"',
        "<dt>source</dt><dd>modified_transitive_predication</dd>",
        f"<dt>scope</dt><dd>{expected_scope}</dd>",
        expected_translation,
        "Parameter in_gallery : Adv.",
        *(["Parameter with_telescope : Adv."] if "with(telescope)" in expected_modifiers else []),
        *(["Parameter near_window : Adv."] if "near(window)" in expected_modifiers else []),
        *(["Parameter beside_shelf : Adv."] if "beside(shelf)" in expected_modifiers else []),
        *(["Parameter under_lamp : Adv."] if "under(lamp)" in expected_modifiers else []),
        "Translation succeeded via construction rule modified_transitive_predication.",
    ]
    require_text_fragments(page, expected_page_fragments, "modified transitive HTML")
    if html.escape(sentence, quote=True) not in page:
        raise SystemExit("web route smoke check failed: modified transitive page input drift")


def validate_analyze_locative_intransitive_success(
    payload: dict,
    page: str,
    sentence: str,
) -> None:
    expectations = {
        "a cat sits on a mat": {
            "translation": "sit(1)(on(mat), cat)",
            "ast_kind": "application",
            "predicate": "sit",
            "arguments": ["cat"],
            "modifier": "on(mat)",
            "coq_adv": "Parameter on_mat : Adv.",
            "forbidden_entity": "Parameter on_mat : Entity.",
            "time_modifier": None,
        },
        "Mary laughed near a window yesterday": {
            "translation": "at_T(yesterday, laugh(1)(near(window), mary))",
            "ast_kind": "time",
            "predicate": "laugh",
            "arguments": ["mary"],
            "modifier": "near(window)",
            "coq_adv": "Parameter near_window : Adv.",
            "forbidden_entity": "Parameter near_window : Entity.",
            "time_modifier": {"operator": "at", "argument": "yesterday"},
        },
    }
    expected = expectations.get(sentence)
    if expected is None:
        raise SystemExit("web route smoke check failed: unknown locative expectation")
    case = "analyze_locative_intransitive_success"
    validate_analyze_success_envelope(
        payload,
        sentence,
        "locative_intransitive_predication",
        ["semantic_readings_check", "construction_hygiene"],
    )
    validate_verification_scope(
        payload,
        page,
        "locative_intransitive_predication",
        "registered_construction",
        "construction_rule",
        "locative_intransitive_predication",
    )
    if payload.get("kind") != "locative_intransitive_predication":
        raise SystemExit("web route smoke check failed: locative kind drift")
    if payload.get("dependent_type_translation") != expected["translation"]:
        raise SystemExit("web route smoke check failed: locative translation drift")
    ast = payload.get("ast")
    application_ast = ast
    if expected["ast_kind"] == "time":
        if (
            not isinstance(ast, dict)
            or ast.get("kind") != "time"
            or ast.get("operator") != expected["time_modifier"]["operator"]
            or ast.get("arguments") != [expected["time_modifier"]["argument"]]
            or not isinstance(ast.get("body"), dict)
        ):
            raise SystemExit("web route smoke check failed: timed locative AST drift")
        application_ast = ast["body"]
    modifier_roles = (
        application_ast.get("modifier_roles", {}).get("roles")
        if isinstance(application_ast, dict)
        else None
    )
    if (
        not isinstance(application_ast, dict)
        or application_ast.get("kind") != "application"
        or application_ast.get("function") != expected["predicate"]
        or application_ast.get("arguments") != expected["arguments"]
        or application_ast.get("modifiers") != [expected["modifier"]]
        or not isinstance(modifier_roles, list)
        or len(modifier_roles) != 1
        or modifier_roles[0].get("type") != "Adv"
        or modifier_roles[0].get("semantic_role") != "Location"
    ):
        raise SystemExit("web route smoke check failed: locative AST drift")
    if "certification_upgrade_plan" in payload or "construction_rule_draft" in payload:
        raise SystemExit("web route smoke check failed: registered locative exposes fallback draft")
    event_semantics = payload.get("event_semantics")
    locative = (
        event_semantics.get("locative_predication")
        if isinstance(event_semantics, dict)
        else None
    )
    if (
        not isinstance(event_semantics, dict)
        or event_semantics.get("analysis") != "locative-intransitive-predication"
        or not isinstance(locative, dict)
        or locative.get("predicate") != expected["predicate"]
        or locative.get("subject") != expected["arguments"][0]
        or locative.get("modifiers") != [expected["modifier"]]
    ):
        raise SystemExit("web route smoke check failed: locative analysis drift")
    if expected["time_modifier"] is None:
        if "time_modifier" in locative:
            raise SystemExit("web route smoke check failed: untimed locative time drift")
    elif locative.get("time_modifier") != expected["time_modifier"]:
        raise SystemExit("web route smoke check failed: timed locative time drift")
    construction_rule = payload.get("construction_rule")
    if (
        not isinstance(construction_rule, dict)
        or construction_rule.get("id") != "locative_intransitive_predication"
    ):
        raise SystemExit("web route smoke check failed: locative rule metadata drift")
    hygiene = payload.get("construction_hygiene")
    if not isinstance(hygiene, dict) or hygiene.get("ok") is not True:
        raise SystemExit("web route smoke check failed: locative hygiene drift")
    readings = payload.get("semantic_readings")
    if not isinstance(readings, list) or len(readings) != 1:
        raise SystemExit("web route smoke check failed: locative reading count drift")
    validate_semantic_reading_summary(
        readings[0],
        {
            "name": "locative_intransitive_predication_single_reading",
            "scope": "registered_single_reading",
            "source": "locative_intransitive_predication",
            "coq_definition": "example_1",
        },
        "none",
        case,
        expected_type=None,
    )
    coq_code = payload.get("coq_code")
    if (
        not isinstance(coq_code, str)
        or "Definition example_1" not in coq_code
        or expected["coq_adv"] not in coq_code
        or expected["forbidden_entity"] in coq_code
        or "Parameter Event : Type." in coq_code
    ):
        raise SystemExit("web route smoke check failed: locative Coq drift")
    validate_successful_semantic_reading_contract(case, payload, page)
    expected_page_fragments = [
        'data-verification-scope-kind="registered_construction"',
        'data-verification-level="construction_rule"',
        "<dt>rule</dt><dd>locative_intransitive_predication</dd>",
        'data-reading-name="locative_intransitive_predication_single_reading"',
        "<dt>source</dt><dd>locative_intransitive_predication</dd>",
        "Locative intransitive predication",
        expected["translation"],
        expected["coq_adv"],
    ]
    require_text_fragments(page, expected_page_fragments, "locative HTML")


def validate_analyze_resultative_predication_success(
    payload: dict,
    page: str,
    sentence: str,
) -> None:
    case = "analyze_resultative_predication_success"
    expectations = {
        "John hammered the metal flat": {
            "translation": "Cause(john, Transition(metal, shape_scale, not_flat, flat))",
            "scope": "explicit_agent_theme_result",
            "ast_kind": "cause",
            "time_argument": None,
            "causer": "john",
            "predicate": "hammer",
            "arguments": ["john", "metal"],
            "theme": "metal",
            "state_scale": "shape_scale",
            "source_state": "not_flat",
            "target_state": "flat",
            "coq_fragments": [
                "Parameter metal : Entity.",
                "Parameter shape_scale : StateScale.",
                "Parameter not_flat : State.",
                "Parameter flat : State.",
            ],
        },
        "Mary admired the painting red yesterday": {
            "translation": (
                "at_T(yesterday, Cause(mary, Transition(painting, color_scale, _, red)))"
            ),
            "scope": "explicit_agent_theme_result_at_time",
            "ast_kind": "time",
            "time_argument": "yesterday",
            "causer": "mary",
            "predicate": "admire",
            "arguments": ["mary", "painting"],
            "theme": "painting",
            "state_scale": "color_scale",
            "source_state": "_",
            "target_state": "red",
            "coq_fragments": [
                "Parameter painting : Entity.",
                "Parameter color_scale : StateScale.",
                "Parameter unknown_state : State.",
                "Parameter red : State.",
                "Parameter yesterday : Entity.",
            ],
        },
    }
    expected = expectations.get(sentence)
    if expected is None:
        raise SystemExit("web route smoke check failed: unknown resultative fixture")
    validate_analyze_success_envelope(
        payload,
        sentence,
        "resultative_predication",
        ["semantic_readings_check", "construction_hygiene"],
    )
    validate_verification_scope(
        payload,
        page,
        "resultative_predication",
        "registered_construction",
        "construction_rule",
        "resultative_predication",
    )
    if payload.get("kind") != "resultative_predication":
        raise SystemExit("web route smoke check failed: resultative kind drift")
    expected_translation = expected["translation"]
    if payload.get("dependent_type_translation") != expected_translation:
        raise SystemExit("web route smoke check failed: resultative translation drift")
    ast = payload.get("ast")
    cause_ast = ast
    if expected["ast_kind"] == "time":
        if (
            not isinstance(ast, dict)
            or ast.get("kind") != "time"
            or ast.get("operator") != "at"
            or ast.get("arguments") != [expected["time_argument"]]
            or not isinstance(ast.get("body"), dict)
        ):
            raise SystemExit("web route smoke check failed: timed resultative AST drift")
        cause_ast = ast["body"]
    activity = cause_ast.get("activity") if isinstance(cause_ast, dict) else None
    effect = cause_ast.get("effect") if isinstance(cause_ast, dict) else None
    if (
        not isinstance(cause_ast, dict)
        or cause_ast.get("kind") != "cause"
        or cause_ast.get("causer") != expected["causer"]
        or not isinstance(activity, dict)
        or activity.get("kind") != "application"
        or activity.get("function") != expected["predicate"]
        or activity.get("arguments") != expected["arguments"]
        or not isinstance(effect, dict)
        or effect.get("kind") != "transition"
        or effect.get("theme") != expected["theme"]
        or effect.get("state_scale") != expected["state_scale"]
        or effect.get("source_state") != expected["source_state"]
        or effect.get("target_state") != expected["target_state"]
    ):
        raise SystemExit("web route smoke check failed: resultative AST drift")
    if "certification_upgrade_plan" in payload or "construction_rule_draft" in payload:
        raise SystemExit("web route smoke check failed: registered resultative exposes fallback draft")
    if payload.get("event_semantics", {}).get("analysis") != "resultative-predication":
        raise SystemExit("web route smoke check failed: resultative analysis drift")
    construction_rule = payload.get("construction_rule")
    if (
        not isinstance(construction_rule, dict)
        or construction_rule.get("id") != "resultative_predication"
    ):
        raise SystemExit("web route smoke check failed: resultative rule metadata drift")
    hygiene = payload.get("construction_hygiene")
    if not isinstance(hygiene, dict) or hygiene.get("ok") is not True:
        raise SystemExit("web route smoke check failed: resultative hygiene drift")
    readings = payload.get("semantic_readings")
    if not isinstance(readings, list) or len(readings) != 1:
        raise SystemExit("web route smoke check failed: resultative reading count drift")
    validate_semantic_reading_summary(
        readings[0],
        {
            "name": "resultative_predication_single_reading",
            "scope": expected["scope"],
            "source": "resultative_predication",
            "coq_definition": "example_1",
        },
        "none",
        case,
        expected_type=None,
    )
    coq_code = payload.get("coq_code")
    if (
        not isinstance(coq_code, str)
        or "Definition example_1" not in coq_code
        or any(fragment not in coq_code for fragment in expected["coq_fragments"])
        or "Parameter Event : Type." in coq_code
        or "Parameter Agent :" in coq_code
        or "Parameter Theme :" in coq_code
        or "Parameter ResultState :" in coq_code
    ):
        raise SystemExit("web route smoke check failed: resultative Coq drift")
    validate_successful_semantic_reading_contract(case, payload, page)
    expected_page_fragments = [
        'data-verification-scope-kind="registered_construction"',
        'data-verification-level="construction_rule"',
        "<dt>rule</dt><dd>resultative_predication</dd>",
        'data-reading-name="resultative_predication_single_reading"',
        "<dt>source</dt><dd>resultative_predication</dd>",
        f"<dt>scope</dt><dd>{expected['scope']}</dd>",
        "Resultative predication",
        expected_translation,
        *expected["coq_fragments"],
    ]
    require_text_fragments(page, expected_page_fragments, "resultative HTML")


def validate_analyze_event_counting_success(payload: dict, page: str, sentence: str) -> None:
    case = "analyze_event_counting_success"
    validate_analyze_success_envelope(
        payload,
        sentence,
        "event_counting",
        ["semantic_readings_check", "construction_hygiene"],
    )
    validate_verification_scope(
        payload,
        page,
        "event_counting",
        "registered_construction",
        "construction_rule",
        "event_counting",
    )
    if payload.get("kind") != "event_counting":
        raise SystemExit("web route smoke check failed: event counting kind drift")
    if payload.get("dependent_type_translation") != "repeat(2, knock(0)(John))":
        raise SystemExit("web route smoke check failed: event counting translation drift")
    ast = payload.get("ast")
    if (
        not isinstance(ast, dict)
        or ast.get("kind") != "repeat"
        or ast.get("count") != "2"
        or not isinstance(ast.get("body"), dict)
        or ast["body"].get("function") != "knock"
    ):
        raise SystemExit("web route smoke check failed: event counting AST drift")
    if "certification_upgrade_plan" in payload or "construction_rule_draft" in payload:
        raise SystemExit("web route smoke check failed: promoted counting still exposes fallback draft")
    construction_rule = payload.get("construction_rule")
    if not isinstance(construction_rule, dict) or construction_rule.get("id") != "event_counting":
        raise SystemExit("web route smoke check failed: event counting rule metadata drift")
    hygiene = payload.get("construction_hygiene")
    if not isinstance(hygiene, dict) or hygiene.get("ok") is not True:
        raise SystemExit("web route smoke check failed: event counting hygiene drift")
    readings = payload.get("semantic_readings")
    if not isinstance(readings, list) or len(readings) != 1:
        raise SystemExit("web route smoke check failed: event counting reading count drift")
    validate_semantic_reading_summary(
        readings[0],
        {
            "name": "event_counting_single_reading",
            "scope": "registered_single_reading",
            "source": "event_counting",
            "coq_definition": "example_1",
        },
        "none",
        case,
        expected_type=None,
    )
    coq_code = payload.get("coq_code")
    if (
        not isinstance(coq_code, str)
        or "Definition example_1" not in coq_code
        or "Parameter Event : Type." in coq_code
    ):
        raise SystemExit("web route smoke check failed: event counting Coq drift")
    validate_successful_semantic_reading_contract(case, payload, page)
    expected_page_fragments = [
        'data-verification-scope-kind="registered_construction"',
        'data-verification-level="construction_rule"',
        "<dt>rule</dt><dd>event_counting</dd>",
        'data-reading-name="event_counting_single_reading"',
        "<dt>source</dt><dd>event_counting</dd>",
        "Counted occurrence",
        "repeat(2, knock(0)(John))",
    ]
    require_text_fragments(page, expected_page_fragments, "event counting HTML")


def validate_analyze_temporal_event_counting_success(
    payload: dict,
    page: str,
    sentence: str,
) -> None:
    case = "analyze_temporal_event_counting_success"
    validate_analyze_success_envelope(
        payload,
        sentence,
        "event_counting",
        ["semantic_readings_check", "construction_hygiene"],
    )
    validate_verification_scope(
        payload,
        page,
        "event_counting",
        "registered_construction",
        "construction_rule",
        "event_counting",
    )
    expected_translation = "at_T(yesterday, repeat(2, knock(0)(john)))"
    if payload.get("dependent_type_translation") != expected_translation:
        raise SystemExit(
            "web route smoke check failed: temporal event counting translation drift"
        )
    event_counting = payload.get("event_semantics", {}).get("event_counting")
    if (
        not isinstance(event_counting, dict)
        or event_counting.get("count") != "2"
        or event_counting.get("counted_predicate") != "knock"
        or event_counting.get("time_wrapped") is not True
    ):
        raise SystemExit(
            "web route smoke check failed: temporal event counting audit drift"
        )
    ast = payload.get("ast")
    if (
        not isinstance(ast, dict)
        or ast.get("kind") != "time"
        or ast.get("operator") != "at"
        or ast.get("arguments") != ["yesterday"]
        or not isinstance(ast.get("body"), dict)
        or ast["body"].get("kind") != "repeat"
        or ast["body"].get("count") != "2"
    ):
        raise SystemExit("web route smoke check failed: temporal event counting AST drift")
    if "certification_upgrade_plan" in payload or "construction_rule_draft" in payload:
        raise SystemExit(
            "web route smoke check failed: temporal counting still exposes fallback draft"
        )
    readings = payload.get("semantic_readings")
    if not isinstance(readings, list) or len(readings) != 1:
        raise SystemExit(
            "web route smoke check failed: temporal event counting reading count drift"
        )
    validate_semantic_reading_summary(
        readings[0],
        {
            "name": "event_counting_single_reading",
            "scope": "registered_single_reading",
            "source": "event_counting",
            "coq_definition": "example_1",
        },
        "none",
        case,
        expected_type=None,
    )
    coq_code = payload.get("coq_code")
    if (
        not isinstance(coq_code, str)
        or "Definition example_1" not in coq_code
        or "Parameter Event : Type." in coq_code
    ):
        raise SystemExit("web route smoke check failed: temporal event counting Coq drift")
    validate_successful_semantic_reading_contract(case, payload, page)
    expected_page_fragments = [
        'data-verification-scope-kind="registered_construction"',
        'data-verification-level="construction_rule"',
        "<dt>rule</dt><dd>event_counting</dd>",
        'data-reading-name="event_counting_single_reading"',
        "Temporal operators scope over the counted proposition.",
        expected_translation,
    ]
    require_text_fragments(page, expected_page_fragments, "temporal event counting HTML")


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
        validate_surface_type_contract_diagnostics_context(
            case,
            payload.get("surface_type_contract_diagnostics"),
        )
        fixture_page = fixture_pages.get(case, "")
        validate_reading_type_check_diagnostics(
            case,
            diagnostics.get("reading_type_check_diagnostics"),
            expected_count=diagnostics.get("reading_type_check_failure_count"),
        )
        validate_reading_type_check_recovery_alignment(case, diagnostics)
        validate_reading_type_check_diagnostics_html(
            case,
            diagnostics.get("reading_type_check_diagnostics"),
            fixture_page,
        )
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


def expected_modified_surface_witness_meta_from_spec(
    spec: dict,
) -> tuple[list[str], dict[str, tuple[str, int, bool, str, str, list[str]]]]:
    def spec_drift() -> None:
        raise SystemExit(
            "web route smoke check failed: certified surface parser generation spec drift"
        )

    if (
        spec.get("schema_version") != "surface_witness_generation.v1"
        or spec.get("generator") != "modifier_prefix_with_optional_time_suffix"
        or spec.get("base_surface_sentence") != "Mary admired the painting"
        or spec.get("predicate") != "admire"
        or spec.get("agent") != "mary"
        or spec.get("theme") != "painting"
        or spec.get("time_suffix") != "yesterday"
        or spec.get("time_operator") != "at_T"
        or spec.get("time_argument") != "yesterday"
        or spec.get("expected_event_analysis") != "modified-transitive-predication"
        or spec.get("expected_ast_kind_by_time_wrapped")
        != {"false": "application", "true": "time"}
        or spec.get("translation_template")
        != "{predicate}({n})({modifier_fragments}, {agent}, {theme})"
        or spec.get("timed_translation_template")
        != "{time_operator}({time_argument}, {body})"
    ):
        spec_drift()

    modifiers = spec.get("modifiers")
    if not isinstance(modifiers, list) or len(modifiers) != 5:
        spec_drift()
    expected_modifiers = [
        (1, "in the gallery", "in(gallery)", "Location"),
        (2, "with a telescope", "with(telescope)", "Instrument"),
        (3, "near a window", "near(window)", "Location"),
        (4, "beside a shelf", "beside(shelf)", "Location"),
        (5, "under a lamp", "under(lamp)", "Location"),
    ]
    for modifier, expected in zip(modifiers, expected_modifiers):
        if not isinstance(modifier, dict):
            spec_drift()
        index, surface, fragment, role = expected
        if (
            modifier.get("index") != index
            or modifier.get("surface") != surface
            or modifier.get("dependent_type_fragment") != fragment
            or modifier.get("semantic_role") != role
        ):
            spec_drift()

    prefix_lengths = spec.get("verified_prefix_lengths")
    if prefix_lengths != [1, 2, 3, 4, 5]:
        spec_drift()
    variant_id_by_prefix = spec.get("variant_id_by_prefix")
    source_by_prefix = spec.get("source_by_prefix")
    if not isinstance(variant_id_by_prefix, dict) or not isinstance(source_by_prefix, dict):
        spec_drift()

    expected_variant_ids = {
        "untimed": {
            "1": "primary_modified_transitive_predication",
            "2": "multi_adv_modified_transitive_predication",
            "3": "triple_adv_modified_transitive_predication",
            "4": "quad_adv_modified_transitive_predication",
            "5": "quint_adv_modified_transitive_predication",
        },
        "timed": {
            "1": "temporal_modified_transitive_predication",
            "2": "temporal_multi_adv_modified_transitive_predication",
            "3": "temporal_triple_adv_modified_transitive_predication",
            "4": "temporal_quad_adv_modified_transitive_predication",
            "5": "temporal_quint_adv_modified_transitive_predication",
        },
    }
    expected_sources = {
        "untimed": {
            "1": "registered_primary_example",
            "2": "registered_variant_example",
            "3": "registered_variant_example",
            "4": "registered_variant_example",
            "5": "registered_variant_example",
        },
        "timed": {
            "1": "registered_variant_example",
            "2": "registered_variant_example",
            "3": "registered_variant_example",
            "4": "registered_variant_example",
            "5": "registered_variant_example",
        },
    }
    if variant_id_by_prefix != expected_variant_ids or source_by_prefix != expected_sources:
        spec_drift()

    ordered_ids: list[str] = []
    expected_meta: dict[str, tuple[str, int, bool, str, str, list[str]]] = {}
    for prefix_length in prefix_lengths:
        modifier_prefix = modifiers[:prefix_length]
        modifier_surfaces = " ".join(
            str(modifier["surface"]) for modifier in modifier_prefix
        )
        modifier_fragments = ", ".join(
            str(modifier["dependent_type_fragment"]) for modifier in modifier_prefix
        )
        sentence_base = f"{spec['base_surface_sentence']} {modifier_surfaces}"
        body = str(spec["translation_template"]).format(
            predicate=spec["predicate"],
            n=prefix_length,
            modifier_fragments=modifier_fragments,
            agent=spec["agent"],
            theme=spec["theme"],
        )
        for bucket, timed in (("untimed", False), ("timed", True)):
            key = str(prefix_length)
            variant_id = variant_id_by_prefix[bucket][key]
            source = source_by_prefix[bucket][key]
            sentence = (
                f"{sentence_base} {spec['time_suffix']}"
                if timed
                else sentence_base
            )
            fragment = (
                str(spec["timed_translation_template"]).format(
                    time_operator=spec["time_operator"],
                    time_argument=spec["time_argument"],
                    body=body,
                )
                if timed
                else body
            )
            ast_kind = spec["expected_ast_kind_by_time_wrapped"][
                "true" if timed else "false"
            ]
            ordered_ids.append(variant_id)
            expected_meta[variant_id] = (
                sentence,
                prefix_length,
                timed,
                source,
                ast_kind,
                [fragment],
            )
    return ordered_ids, expected_meta


def expected_modified_surface_slot_probe_meta_from_spec(
    spec: dict,
) -> tuple[list[str], dict[str, tuple[str, str, int, bool, str, list[str]]]]:
    def spec_drift() -> None:
        raise SystemExit(
            "web route smoke check failed: certified surface parser slot probe generation spec drift"
        )

    expected_base_frame = {
        "agent": {"surface": "Mary", "semantic": "mary"},
        "predicate": {"surface": "admired", "semantic": "admire"},
        "theme": {"surface": "painting", "semantic": "painting"},
    }
    expected_probe_templates = [
        {
            "probe_id": "subject_slot_john",
            "slot": "agent",
            "modifier_prefix_length": 1,
            "time_wrapped": False,
            "substitutions": {
                "agent": {"surface": "John", "semantic": "john"},
            },
        },
        {
            "probe_id": "theme_slot_sculpture",
            "slot": "theme",
            "modifier_prefix_length": 1,
            "time_wrapped": False,
            "substitutions": {
                "theme": {"surface": "sculpture", "semantic": "sculpture"},
            },
        },
        {
            "probe_id": "predicate_slot_photograph",
            "slot": "predicate",
            "modifier_prefix_length": 1,
            "time_wrapped": False,
            "substitutions": {
                "predicate": {"surface": "photographed", "semantic": "photograph"},
            },
        },
        {
            "probe_id": "combined_slots_timed_max_prefix",
            "slot": "agent_predicate_theme",
            "modifier_prefix_length": 5,
            "time_wrapped": True,
            "substitutions": {
                "agent": {"surface": "John", "semantic": "john"},
                "predicate": {"surface": "photographed", "semantic": "photograph"},
                "theme": {"surface": "sculpture", "semantic": "sculpture"},
            },
        },
    ]
    if (
        not isinstance(spec, dict)
        or spec.get("schema_version") != "surface_slot_probe_generation.v1"
        or spec.get("generator") != "lexical_slot_substitution_with_modifier_prefix"
        or spec.get("base_family") != "modified_transitive_adv_sequence"
        or spec.get("base_frame") != expected_base_frame
        or spec.get("surface_template")
        != "{agent_surface} {predicate_surface} the {theme_surface} {modifier_surfaces}"
        or spec.get("timed_surface_template") != "{body} {time_suffix}"
        or spec.get("time_suffix") != "yesterday"
        or spec.get("time_operator") != "at_T"
        or spec.get("time_argument") != "yesterday"
        or spec.get("expected_ast_kind_by_time_wrapped")
        != {"false": "application", "true": "time"}
        or spec.get("translation_template")
        != "{predicate}({n})({modifier_fragments}, {agent}, {theme})"
        or spec.get("timed_translation_template")
        != "{time_operator}({time_argument}, {body})"
        or spec.get("probe_templates") != expected_probe_templates
    ):
        spec_drift()

    modifiers = spec.get("modifiers")
    if not isinstance(modifiers, list) or len(modifiers) != 5:
        spec_drift()
    expected_modifiers = [
        (1, "in the gallery", "in(gallery)", "Location"),
        (2, "with a telescope", "with(telescope)", "Instrument"),
        (3, "near a window", "near(window)", "Location"),
        (4, "beside a shelf", "beside(shelf)", "Location"),
        (5, "under a lamp", "under(lamp)", "Location"),
    ]
    for modifier, expected in zip(modifiers, expected_modifiers):
        if not isinstance(modifier, dict):
            spec_drift()
        index, surface, fragment, role = expected
        if (
            modifier.get("index") != index
            or modifier.get("surface") != surface
            or modifier.get("dependent_type_fragment") != fragment
            or modifier.get("semantic_role") != role
        ):
            spec_drift()

    ordered_ids: list[str] = []
    expected_meta: dict[str, tuple[str, str, int, bool, str, list[str]]] = {}
    for template in expected_probe_templates:
        frame = {
            slot: dict(values)
            for slot, values in expected_base_frame.items()
        }
        for slot, replacement in template["substitutions"].items():
            frame[slot] = dict(replacement)
        modifier_count = int(template["modifier_prefix_length"])
        modifier_prefix = modifiers[:modifier_count]
        modifier_surfaces = " ".join(
            str(modifier["surface"]) for modifier in modifier_prefix
        )
        modifier_fragments = ", ".join(
            str(modifier["dependent_type_fragment"])
            for modifier in modifier_prefix
        )
        sentence_body = str(spec["surface_template"]).format(
            agent_surface=frame["agent"]["surface"],
            predicate_surface=frame["predicate"]["surface"],
            theme_surface=frame["theme"]["surface"],
            modifier_surfaces=modifier_surfaces,
        )
        body = str(spec["translation_template"]).format(
            predicate=frame["predicate"]["semantic"],
            n=modifier_count,
            modifier_fragments=modifier_fragments,
            agent=frame["agent"]["semantic"],
            theme=frame["theme"]["semantic"],
        )
        time_wrapped = template.get("time_wrapped") is True
        sentence = (
            str(spec["timed_surface_template"]).format(
                body=sentence_body,
                time_suffix=spec["time_suffix"],
            )
            if time_wrapped
            else sentence_body
        )
        fragment = (
            str(spec["timed_translation_template"]).format(
                time_operator=spec["time_operator"],
                time_argument=spec["time_argument"],
                body=body,
            )
            if time_wrapped
            else body
        )
        ast_kind = spec["expected_ast_kind_by_time_wrapped"][
            "true" if time_wrapped else "false"
        ]
        probe_id = str(template["probe_id"])
        ordered_ids.append(probe_id)
        expected_meta[probe_id] = (
            str(template["slot"]),
            sentence,
            modifier_count,
            time_wrapped,
            ast_kind,
            [fragment],
        )
    return ordered_ids, expected_meta


def expected_modified_surface_slot_probe_matrix_meta_from_spec(
    spec: dict,
) -> tuple[list[str], dict[str, tuple[str, str, str, str, int, bool, str, list[str], dict]]]:
    from translator.surface_type_contracts import (
        modified_transitive_surface_type_contract_registry,
        validate_surface_type_contract_registry,
    )

    def spec_drift() -> None:
        raise SystemExit(
            "web route smoke check failed: certified surface parser slot probe matrix generation spec drift"
        )

    expected_type_contract_registry = (
        modified_transitive_surface_type_contract_registry()
    )
    try:
        validate_surface_type_contract_registry(spec.get("type_contract_registry"))
    except ValueError as exc:
        raise SystemExit(
            "web route smoke check failed: certified surface parser slot probe matrix "
            f"type contract registry invalid: {exc}"
        ) from exc
    expected_axis_type_contract = expected_type_contract_registry[
        "axis_type_contract"
    ]
    expected_modifier_type_contract = expected_type_contract_registry[
        "modifier_type_contract"
    ]
    expected_time_type_contract = expected_type_contract_registry[
        "time_type_contract"
    ]
    expected_axes = expected_type_contract_registry["axes"]
    expected_profiles = [
        {
            "profile_id": "one_adv_untimed",
            "modifier_prefix_length": 1,
            "time_wrapped": False,
        },
        {
            "profile_id": "max_prefix_timed",
            "modifier_prefix_length": 5,
            "time_wrapped": True,
        },
    ]
    if (
        not isinstance(spec, dict)
        or spec.get("schema_version") != "surface_slot_probe_matrix_generation.v1"
        or spec.get("generator") != "cartesian_lexical_frame_with_modifier_profiles"
        or spec.get("base_family") != "modified_transitive_adv_sequence"
        or spec.get("type_contract_registry") != expected_type_contract_registry
        or spec.get("axis_type_contract") != expected_axis_type_contract
        or spec.get("modifier_type_contract") != expected_modifier_type_contract
        or spec.get("time_type_contract") != expected_time_type_contract
        or spec.get("axes") != expected_axes
        or spec.get("surface_template")
        != "{agent_surface} {predicate_surface} the {theme_surface} {modifier_surfaces}"
        or spec.get("timed_surface_template") != "{body} {time_suffix}"
        or spec.get("modifier_profiles") != expected_profiles
        or spec.get("time_suffix") != "yesterday"
        or spec.get("time_operator") != "at_T"
        or spec.get("time_argument") != "yesterday"
        or spec.get("expected_ast_kind_by_time_wrapped")
        != {"false": "application", "true": "time"}
        or spec.get("translation_template")
        != "{predicate}({n})({modifier_fragments}, {agent}, {theme})"
        or spec.get("timed_translation_template")
        != "{time_operator}({time_argument}, {body})"
    ):
        spec_drift()

    modifiers = spec.get("modifiers")
    if not isinstance(modifiers, list) or len(modifiers) != 5:
        spec_drift()
    expected_modifiers = [
        (1, "in the gallery", "in(gallery)", "Location"),
        (2, "with a telescope", "with(telescope)", "Instrument"),
        (3, "near a window", "near(window)", "Location"),
        (4, "beside a shelf", "beside(shelf)", "Location"),
        (5, "under a lamp", "under(lamp)", "Location"),
    ]
    for modifier, expected in zip(modifiers, expected_modifiers):
        if not isinstance(modifier, dict):
            spec_drift()
        index, surface, fragment, role = expected
        if (
            modifier.get("index") != index
            or modifier.get("surface") != surface
            or modifier.get("dependent_type_fragment") != fragment
            or modifier.get("semantic_role") != role
        ):
            spec_drift()

    ordered_ids: list[str] = []
    expected_meta: dict[str, tuple[str, str, str, str, int, bool, str, list[str], dict]] = {}
    for agent in expected_axes["agents"]:
        for predicate in expected_axes["predicates"]:
            for theme in expected_axes["themes"]:
                for profile in expected_profiles:
                    modifier_count = int(profile["modifier_prefix_length"])
                    modifier_prefix = modifiers[:modifier_count]
                    modifier_surfaces = " ".join(
                        str(modifier["surface"]) for modifier in modifier_prefix
                    )
                    modifier_fragments = ", ".join(
                        str(modifier["dependent_type_fragment"])
                        for modifier in modifier_prefix
                    )
                    sentence_body = str(spec["surface_template"]).format(
                        agent_surface=agent["surface"],
                        predicate_surface=predicate["surface"],
                        theme_surface=theme["surface"],
                        modifier_surfaces=modifier_surfaces,
                    )
                    body = str(spec["translation_template"]).format(
                        predicate=predicate["semantic"],
                        n=modifier_count,
                        modifier_fragments=modifier_fragments,
                        agent=agent["semantic"],
                        theme=theme["semantic"],
                    )
                    time_wrapped = profile.get("time_wrapped") is True
                    sentence = (
                        str(spec["timed_surface_template"]).format(
                            body=sentence_body,
                            time_suffix=spec["time_suffix"],
                        )
                        if time_wrapped
                        else sentence_body
                    )
                    fragment = (
                        str(spec["timed_translation_template"]).format(
                            time_operator=spec["time_operator"],
                            time_argument=spec["time_argument"],
                            body=body,
                        )
                        if time_wrapped
                        else body
                    )
                    ast_kind = spec["expected_ast_kind_by_time_wrapped"][
                        "true" if time_wrapped else "false"
                    ]
                    matrix_id = (
                        f"agent_{agent['semantic']}__predicate_{predicate['semantic']}"
                        f"__theme_{theme['semantic']}__profile_{profile['profile_id']}"
                    )
                    ordered_ids.append(matrix_id)
                    type_contract = {
                        "agent_dependent_type": agent["dependent_type"],
                        "agent_role_label": agent["role_label"],
                        "predicate_dependent_type": predicate["dependent_type"],
                        "predicate_role_frame": list(predicate["role_frame"]),
                        "predicate_output_type": predicate["output_type"],
                        "theme_dependent_type": theme["dependent_type"],
                        "theme_role_label": theme["role_label"],
                        "modifier_dependent_type": expected_modifier_type_contract[
                            "dependent_type"
                        ],
                        "modifier_constructor_type": expected_modifier_type_contract[
                            "constructor_type"
                        ],
                        "time_argument_type": (
                            expected_time_type_contract["time_argument_type"]
                            if time_wrapped
                            else None
                        ),
                        "time_operator_type": (
                            expected_time_type_contract["time_operator_type"]
                            if time_wrapped
                            else None
                        ),
                    }
                    expected_meta[matrix_id] = (
                        str(profile["profile_id"]),
                        str(agent["semantic"]),
                        str(predicate["semantic"]),
                        str(theme["semantic"]),
                        modifier_count,
                        time_wrapped,
                        ast_kind,
                        [fragment],
                        type_contract,
                    )
    return ordered_ids, expected_meta


def validate_certified_fragment_manifest(manifest: dict) -> None:
    from translator.natural_language_pipeline import (
        application_modifier_role_occurrences,
        application_modifier_sequence_summaries,
        ast_structure_summary,
        construction_rules,
        declared_application_modifier_counts,
        derive_registered_modifier_role_inventory,
        derive_registered_modifier_role_witnesses,
        exported_prop_definition_names,
        registered_modifier_role_source_contract,
        registered_modifier_role_witness_selection_contract,
        run_pipeline,
    )

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
    snapshots = manifest.get("semantic_snapshots")
    if not isinstance(snapshots, list) or not snapshots:
        raise SystemExit("web route smoke check failed: certified semantic snapshots missing")
    if manifest.get("semantic_snapshot_count") != len(snapshots):
        raise SystemExit("web route smoke check failed: certified semantic snapshot count drift")
    snapshot_by_id = {
        item.get("rule_id"): item
        for item in snapshots
        if isinstance(item, dict) and isinstance(item.get("rule_id"), str)
    }
    if set(snapshot_by_id) != set(rules):
        raise SystemExit("web route smoke check failed: certified semantic snapshot id drift")
    coverage = manifest.get("coverage_matrix")
    counts = manifest.get("coverage_matrix_counts")
    if not isinstance(coverage, dict) or not isinstance(counts, dict):
        raise SystemExit("web route smoke check failed: certified coverage matrix missing")
    registered_cases = coverage.get("registered_success_cases")
    registered_variant_cases = coverage.get("registered_variant_success_cases")
    fallback_cases = coverage.get("fallback_success_cases")
    rejected_cases = coverage.get("rejected_unsupported_cases")
    if (
        not isinstance(registered_cases, list)
        or not isinstance(registered_variant_cases, list)
        or not isinstance(fallback_cases, list)
        or not isinstance(rejected_cases, list)
    ):
        raise SystemExit("web route smoke check failed: certified coverage case drift")
    if counts.get("registered_success_cases") != len(registered_cases):
        raise SystemExit("web route smoke check failed: certified registered coverage count drift")
    if counts.get("registered_variant_success_cases") != len(registered_variant_cases):
        raise SystemExit(
            "web route smoke check failed: certified registered variant coverage count drift"
        )
    if counts.get("fallback_success_cases") != len(fallback_cases):
        raise SystemExit("web route smoke check failed: certified fallback coverage count drift")
    if counts.get("rejected_unsupported_cases") != len(rejected_cases):
        raise SystemExit("web route smoke check failed: certified rejected coverage count drift")
    modifier_contract = manifest.get("registered_modifier_sequence_contract")
    expected_modifier_invariants = [
        "modifier_vector_length_matches_modifiers",
        "modifier_vector_tail_lengths_decrease_to_zero",
        "modifier_roles_length_matches_modifiers",
        "modifier_roles_are_adv_not_entity",
        "surface_lexicon_matches_modifier_roles",
        "observed_modifier_roles_are_registered",
        "registered_modifier_role_minima_are_observed",
        "registered_modifier_role_inventory_is_coverage_derived",
        "registered_modifier_roles_are_surface_lexicon_derived",
        "registered_modifier_roles_have_live_witnesses",
        "registered_modifier_role_witnesses_are_coverage_derived",
    ]
    expected_declared_modifier_counts = declared_application_modifier_counts(
        [*snapshots, *registered_variant_cases],
    )
    expected_modifier_role_inventory = derive_registered_modifier_role_inventory(
        snapshots,
        registered_variant_cases,
    )
    expected_modifier_role_source_contract = registered_modifier_role_source_contract()
    expected_modifier_role_witness_selection_contract = (
        registered_modifier_role_witness_selection_contract()
    )
    expected_modifier_role_witnesses = derive_registered_modifier_role_witnesses(
        snapshots,
        registered_variant_cases,
    )
    if (
        not isinstance(modifier_contract, dict)
        or modifier_contract.get("schema_version")
        != "registered_modifier_sequence_contract.v1"
        or modifier_contract.get("source")
        != "registered_primary_and_variant_success_cases"
        or modifier_contract.get("claim") != "registered_examples_only"
        or modifier_contract.get("full_surface_parser_certification") is not False
        or modifier_contract.get("primary_case_count") != len(snapshots)
        or modifier_contract.get("variant_case_count") != len(registered_variant_cases)
        or modifier_contract.get("case_count")
        != len(snapshots) + len(registered_variant_cases)
        or modifier_contract.get("declared_application_modifier_counts")
        != expected_declared_modifier_counts
        or modifier_contract.get("max_declared_application_modifier_count")
        != (max(expected_declared_modifier_counts) if expected_declared_modifier_counts else 0)
        or modifier_contract.get("required_invariants") != expected_modifier_invariants
        or modifier_contract.get("registered_semantic_role_inventory")
        != expected_modifier_role_inventory
        or modifier_contract.get("registered_semantic_role_witnesses")
        != expected_modifier_role_witnesses
        or modifier_contract.get("semantic_role_witness_selection_contract")
        != expected_modifier_role_witness_selection_contract
        or modifier_contract.get("semantic_role_source_contract")
        != expected_modifier_role_source_contract
    ):
        raise SystemExit(
            "web route smoke check failed: certified modifier sequence contract drift"
        )
    live_validation = modifier_contract.get("live_validation")
    if (
        not isinstance(live_validation, dict)
        or live_validation.get("max_application_modifier_count_is_recomputed") is not True
        or live_validation.get("semantic_role_inventory_is_coverage_derived") is not True
        or live_validation.get("semantic_role_source_contract_is_recomputed") is not True
        or live_validation.get(
            "semantic_role_witness_selection_contract_is_recomputed",
        )
        is not True
        or live_validation.get("semantic_role_witnesses_are_coverage_derived") is not True
        or live_validation.get("semantic_role_witnesses_are_live_checked") is not True
    ):
        raise SystemExit(
            "web route smoke check failed: certified modifier sequence live validator drift"
        )

    observed_application_modifier_counts: list[int] = []
    observed_modifier_roles: Counter[str] = Counter()
    expected_modifier_role_names = {
        str(item["role"]) for item in expected_modifier_role_inventory
    }
    if (
        expected_modifier_role_source_contract.get("derived_role_inventory")
        != sorted(expected_modifier_role_names)
    ):
        raise SystemExit(
            "web route smoke check failed: certified modifier sequence role source drift"
        )
    expected_modifier_role_witness_names = {
        str(item.get("role")) for item in expected_modifier_role_witnesses
    }
    if expected_modifier_role_witness_names != expected_modifier_role_names:
        raise SystemExit(
            "web route smoke check failed: certified modifier sequence role witness drift"
        )
    witness_allowed_sources = set(
        expected_modifier_role_witness_selection_contract.get("sentence_sources", []),
    )
    witness_required_fields = set(
        expected_modifier_role_witness_selection_contract.get(
            "required_witness_fields",
            [],
        ),
    )
    for witness in expected_modifier_role_witnesses:
        if (
            set(witness) != witness_required_fields
            or witness.get("source") not in witness_allowed_sources
        ):
            raise SystemExit(
                "web route smoke check failed: certified modifier sequence role witness drift"
            )
    registered_witness_sentences = {
        str(case.get("sentence"))
        for case in [*registered_cases, *registered_variant_cases]
        if isinstance(case, dict) and case.get("sentence")
    }
    expected_modifier_role_minima = {
        str(item["role"]): int(item["minimum_observed_occurrences"])
        for item in expected_modifier_role_inventory
    }

    def observe_modifier_sequences(result: dict, label: str) -> None:
        for summary in application_modifier_sequence_summaries(result.get("ast", {})):
            modifier_count = summary.get("modifier_count")
            if not isinstance(modifier_count, int):
                raise SystemExit(
                    f"web route smoke check failed: {label} modifier count drift"
                )
            observed_application_modifier_counts.append(modifier_count)
            if (
                summary.get("adverb_count") != modifier_count
                or summary.get("vector_length") != modifier_count
                or summary.get("vector_item_count") != modifier_count
                or summary.get("role_count") != modifier_count
                or summary.get("vector_matches_modifiers") is not True
                or summary.get("roles_match_modifiers") is not True
                or summary.get("roles_are_adv") is not True
                or summary.get("surface_lexicon_matches") is not True
            ):
                raise SystemExit(
                    f"web route smoke check failed: {label} modifier sequence invariant drift"
                )
            role_pattern = summary.get("role_pattern")
            if not isinstance(role_pattern, list):
                raise SystemExit(
                    f"web route smoke check failed: {label} modifier role pattern drift"
                )
            for role in role_pattern:
                if not isinstance(role, str) or role not in expected_modifier_role_names:
                    raise SystemExit(
                        f"web route smoke check failed: {label} modifier role inventory drift"
                    )
                observed_modifier_roles[role] += 1
    surface_parser_coverage = manifest.get("surface_parser_coverage")
    if not isinstance(surface_parser_coverage, dict):
        raise SystemExit("web route smoke check failed: certified surface parser coverage missing")
    modified_surface = surface_parser_coverage.get("modified_transitive_adv_sequence")
    if not isinstance(modified_surface, dict):
        raise SystemExit("web route smoke check failed: certified modified-transitive surface coverage missing")
    expected_surface_counts = [1, 2, 3, 4, 5]
    generation_spec = modified_surface.get("witness_generation_spec")
    if not isinstance(generation_spec, dict):
        raise SystemExit(
            "web route smoke check failed: certified surface parser generation spec missing"
        )
    (
        expected_surface_example_ids,
        expected_surface_example_meta,
    ) = expected_modified_surface_witness_meta_from_spec(generation_spec)
    if (
        modified_surface.get("rule_id") != "modified_transitive_predication"
        or modified_surface.get("type_principle") != "non_empty_modifier_sequence"
        or modified_surface.get("type_family")
        != "forall n : nat, ModifierSeq n -> Entity -> Entity -> PropT"
        or modified_surface.get("type_level_open_ended") is not True
        or modified_surface.get("surface_parser_claim") != "registered_examples_only"
        or modified_surface.get("full_surface_parser_certification") is not False
        or modified_surface.get("primary_modifier_count") != 1
        or modified_surface.get("verified_modifier_counts") != expected_surface_counts
        or modified_surface.get("verified_timed_modifier_counts") != expected_surface_counts
        or modified_surface.get("verified_untimed_modifier_counts") != expected_surface_counts
        or modified_surface.get("max_verified_modifier_count") != 5
        or modified_surface.get("verified_example_count") != len(expected_surface_example_ids)
        or not isinstance(modified_surface.get("boundary_note"), str)
    ):
        raise SystemExit("web route smoke check failed: certified surface parser coverage drift")
    surface_examples = modified_surface.get("verified_examples")
    if not isinstance(surface_examples, list) or len(surface_examples) != len(expected_surface_example_ids):
        raise SystemExit("web route smoke check failed: certified surface parser witness count drift")
    observed_surface_ids = [
        item.get("variant_id")
        for item in surface_examples
        if isinstance(item, dict)
    ]
    if observed_surface_ids != expected_surface_example_ids:
        raise SystemExit("web route smoke check failed: certified surface parser witness id drift")
    for item in surface_examples:
        if not isinstance(item, dict):
            raise SystemExit("web route smoke check failed: certified surface parser witness shape drift")
        expected_meta = expected_surface_example_meta.get(str(item.get("variant_id", "")))
        if (
            expected_meta is None
            or item.get("rule_id") != "modified_transitive_predication"
            or item.get("sentence") != expected_meta[0]
            or item.get("modifier_count") != expected_meta[1]
            or item.get("time_wrapped") is not expected_meta[2]
            or item.get("source") != expected_meta[3]
            or item.get("expected_event_analysis") != "modified-transitive-predication"
            or item.get("expected_ast_kind") != expected_meta[4]
            or item.get("expected_dependent_type_fragments") != expected_meta[5]
            or not isinstance(item.get("boundary_status"), str)
        ):
            raise SystemExit("web route smoke check failed: certified surface parser witness drift")
        expected_fragments = item.get("expected_dependent_type_fragments")
        if (
            not isinstance(expected_fragments, list)
            or not expected_fragments
            or not all(
                isinstance(fragment, str) and fragment
                for fragment in expected_fragments
            )
        ):
            raise SystemExit(
                "web route smoke check failed: certified surface parser witness fragment schema drift"
            )
        witness_result = run_pipeline(str(item.get("sentence", "")), require_coq=False)
        if not witness_result.get("ok"):
            raise SystemExit(
                "web route smoke check failed: certified surface parser witness no longer runs"
            )
        if witness_result.get("construction_rule", {}).get("id") != item.get("rule_id"):
            raise SystemExit(
                "web route smoke check failed: certified surface parser witness rule drift"
            )
        if witness_result.get("event_semantics", {}).get("analysis") != item.get(
            "expected_event_analysis",
        ):
            raise SystemExit(
                "web route smoke check failed: certified surface parser witness live analysis drift"
            )
        if witness_result.get("ast", {}).get("kind") != item.get("expected_ast_kind"):
            raise SystemExit(
                "web route smoke check failed: certified surface parser witness live AST drift"
            )
        witness_translation = str(
            witness_result.get("dependent_type_translation", ""),
        )
        for fragment in expected_fragments:
            if fragment not in witness_translation:
                raise SystemExit(
                    "web route smoke check failed: certified surface parser witness live translation drift"
                )
    for witness in expected_modifier_role_witnesses:
        role = str(witness.get("role", ""))
        sentence = str(witness.get("sentence", ""))
        if sentence not in registered_witness_sentences:
            raise SystemExit(
                "web route smoke check failed: certified modifier sequence role witness drift"
            )
        result = run_pipeline(sentence, require_coq=False)
        occurrences = application_modifier_role_occurrences(result.get("ast", {}))
        if not any(
            occurrence.get("semantic_role") == role
            and occurrence.get("type") == witness.get("type")
            and occurrence.get("surface_type") == witness.get("type")
            and occurrence.get("surface_semantic_role") == role
            and occurrence.get("modifier") == witness.get("modifier")
            and occurrence.get("normalized_modifier")
            == witness.get("normalized_modifier")
            and occurrence.get("source")
            == expected_modifier_role_source_contract.get("source_module")
            for occurrence in occurrences
        ):
            raise SystemExit(
                "web route smoke check failed: certified modifier sequence role witness drift"
            )
    slot_probe_examples = modified_surface.get("slot_probe_examples")
    if (
        not isinstance(slot_probe_examples, dict)
        or slot_probe_examples.get("schema_version") != "surface_slot_probes.v1"
        or slot_probe_examples.get("probe_claim")
        != "controlled_single_slot_and_combined_substitutions"
        or slot_probe_examples.get("full_lexical_slot_certification") is not False
        or slot_probe_examples.get("base_family") != "modified_transitive_adv_sequence"
        or slot_probe_examples.get("expected_rule_id")
        != "modified_transitive_predication"
        or slot_probe_examples.get("expected_event_analysis")
        != "modified-transitive-predication"
    ):
        raise SystemExit(
            "web route smoke check failed: certified surface parser slot probe schema drift"
        )
    (
        expected_probe_ids,
        expected_probe_meta,
    ) = expected_modified_surface_slot_probe_meta_from_spec(
        slot_probe_examples.get("probe_generation_spec"),
    )
    if slot_probe_examples.get("probe_count") != len(expected_probe_ids):
        raise SystemExit(
            "web route smoke check failed: certified surface parser slot probe schema drift"
        )
    slot_probes = slot_probe_examples.get("probes")
    if not isinstance(slot_probes, list) or len(slot_probes) != len(expected_probe_ids):
        raise SystemExit(
            "web route smoke check failed: certified surface parser slot probe count drift"
        )
    observed_probe_ids = [
        probe.get("probe_id")
        for probe in slot_probes
        if isinstance(probe, dict)
    ]
    if observed_probe_ids != expected_probe_ids:
        raise SystemExit(
            "web route smoke check failed: certified surface parser slot probe id drift"
        )
    for probe in slot_probes:
        if not isinstance(probe, dict):
            raise SystemExit(
                "web route smoke check failed: certified surface parser slot probe shape drift"
            )
        expected_probe = expected_probe_meta.get(str(probe.get("probe_id", "")))
        if (
            expected_probe is None
            or probe.get("slot") != expected_probe[0]
            or probe.get("sentence") != expected_probe[1]
            or probe.get("modifier_count") != expected_probe[2]
            or probe.get("time_wrapped") is not expected_probe[3]
            or probe.get("expected_ast_kind") != expected_probe[4]
            or probe.get("expected_dependent_type_fragments") != expected_probe[5]
        ):
            raise SystemExit(
                "web route smoke check failed: certified surface parser slot probe drift"
            )
        probe_fragments = probe.get("expected_dependent_type_fragments")
        if (
            not isinstance(probe_fragments, list)
            or not probe_fragments
            or not all(
                isinstance(fragment, str) and fragment
                for fragment in probe_fragments
            )
        ):
            raise SystemExit(
                "web route smoke check failed: certified surface parser slot probe fragment schema drift"
            )
        probe_result = run_pipeline(str(probe.get("sentence", "")), require_coq=False)
        if not probe_result.get("ok"):
            raise SystemExit(
                "web route smoke check failed: certified surface parser slot probe no longer runs"
            )
        if (
            probe_result.get("construction_rule", {}).get("id")
            != slot_probe_examples.get("expected_rule_id")
        ):
            raise SystemExit(
                "web route smoke check failed: certified surface parser slot probe rule drift"
            )
        if probe_result.get("event_semantics", {}).get("analysis") != slot_probe_examples.get(
            "expected_event_analysis",
        ):
            raise SystemExit(
                "web route smoke check failed: certified surface parser slot probe live analysis drift"
            )
        if probe_result.get("ast", {}).get("kind") != probe.get("expected_ast_kind"):
            raise SystemExit(
                "web route smoke check failed: certified surface parser slot probe live AST drift"
            )
        probe_translation = str(probe_result.get("dependent_type_translation", ""))
        for fragment in probe_fragments:
            if fragment not in probe_translation:
                raise SystemExit(
                    "web route smoke check failed: certified surface parser slot probe live translation drift"
                )
    if (
        slot_probe_examples.get("matrix_claim")
        != "controlled_cartesian_slot_substitutions"
        or slot_probe_examples.get("full_lexical_matrix_certification") is not False
    ):
        raise SystemExit(
            "web route smoke check failed: certified surface parser slot probe matrix schema drift"
        )
    (
        expected_matrix_ids,
        expected_matrix_meta,
    ) = expected_modified_surface_slot_probe_matrix_meta_from_spec(
        slot_probe_examples.get("matrix_generation_spec"),
    )
    if slot_probe_examples.get("matrix_example_count") != len(expected_matrix_ids):
        raise SystemExit(
            "web route smoke check failed: certified surface parser slot probe matrix schema drift"
        )
    matrix_examples = slot_probe_examples.get("matrix_examples")
    if not isinstance(matrix_examples, list) or len(matrix_examples) != len(expected_matrix_ids):
        raise SystemExit(
            "web route smoke check failed: certified surface parser slot probe matrix count drift"
        )
    observed_matrix_ids = [
        example.get("matrix_id")
        for example in matrix_examples
        if isinstance(example, dict)
    ]
    if observed_matrix_ids != expected_matrix_ids:
        raise SystemExit(
            "web route smoke check failed: certified surface parser slot probe matrix id drift"
        )
    for example in matrix_examples:
        if not isinstance(example, dict):
            raise SystemExit(
                "web route smoke check failed: certified surface parser slot probe matrix shape drift"
            )
        expected_matrix = expected_matrix_meta.get(str(example.get("matrix_id", "")))
        agent = example.get("agent")
        predicate = example.get("predicate")
        theme = example.get("theme")
        type_contract = example.get("type_contract")
        if (
            expected_matrix is None
            or not isinstance(agent, dict)
            or not isinstance(predicate, dict)
            or not isinstance(theme, dict)
            or not isinstance(type_contract, dict)
            or example.get("profile_id") != expected_matrix[0]
            or agent.get("semantic") != expected_matrix[1]
            or predicate.get("semantic") != expected_matrix[2]
            or theme.get("semantic") != expected_matrix[3]
            or example.get("modifier_count") != expected_matrix[4]
            or example.get("time_wrapped") is not expected_matrix[5]
            or example.get("expected_ast_kind") != expected_matrix[6]
            or example.get("expected_dependent_type_fragments") != expected_matrix[7]
        ):
            raise SystemExit(
                "web route smoke check failed: certified surface parser slot probe matrix drift"
            )
        if (
            agent.get("dependent_type") != "Entity"
            or agent.get("role_label") != "Agent"
            or predicate.get("dependent_type")
            != "forall n : nat, ModifierSeq n -> Entity -> Entity -> PropT"
            or predicate.get("role_frame") != ["Agent", "Theme"]
            or predicate.get("output_type") != "PropT"
            or theme.get("dependent_type") != "Entity"
            or theme.get("role_label") != "Theme"
            or type_contract != expected_matrix[8]
        ):
            raise SystemExit(
                "web route smoke check failed: certified surface parser slot probe matrix type drift"
            )
        matrix_fragments = example.get("expected_dependent_type_fragments")
        if (
            not isinstance(matrix_fragments, list)
            or not matrix_fragments
            or not all(
                isinstance(fragment, str) and fragment
                for fragment in matrix_fragments
            )
        ):
            raise SystemExit(
                "web route smoke check failed: certified surface parser slot probe matrix fragment schema drift"
            )
        matrix_result = run_pipeline(str(example.get("sentence", "")), require_coq=False)
        if not matrix_result.get("ok"):
            raise SystemExit(
                "web route smoke check failed: certified surface parser slot probe matrix no longer runs"
            )
        if (
            matrix_result.get("construction_rule", {}).get("id")
            != slot_probe_examples.get("expected_rule_id")
        ):
            raise SystemExit(
                "web route smoke check failed: certified surface parser slot probe matrix rule drift"
            )
        if matrix_result.get("event_semantics", {}).get("analysis") != slot_probe_examples.get(
            "expected_event_analysis",
        ):
            raise SystemExit(
                "web route smoke check failed: certified surface parser slot probe matrix live analysis drift"
            )
        if matrix_result.get("ast", {}).get("kind") != example.get("expected_ast_kind"):
            raise SystemExit(
                "web route smoke check failed: certified surface parser slot probe matrix live AST drift"
            )
        matrix_translation = str(matrix_result.get("dependent_type_translation", ""))
        for fragment in matrix_fragments:
            if fragment not in matrix_translation:
                raise SystemExit(
                    "web route smoke check failed: certified surface parser slot probe matrix live translation drift"
                )
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
        snapshot = snapshot_by_id[rule_id]
        if snapshot.get("sentence") != item.get("example"):
            raise SystemExit(
                f"web route smoke check failed: certified rule {rule_id} snapshot sentence drift"
            )
        expected_fragments = snapshot.get("expected_dependent_type_fragments")
        expected_reading_names = snapshot.get("expected_reading_names")
        expected_sources = snapshot.get("expected_reading_sources")
        expected_scopes = snapshot.get("expected_reading_scopes")
        expected_definitions = snapshot.get("expected_coq_definitions")
        expected_ast_summary = snapshot.get("expected_ast_summary")
        if (
            not isinstance(snapshot.get("expected_event_analysis"), str)
            or not snapshot["expected_event_analysis"]
            or not isinstance(expected_fragments, list)
            or not expected_fragments
            or not all(isinstance(fragment, str) and fragment for fragment in expected_fragments)
            or not isinstance(expected_reading_names, list)
            or not expected_reading_names
            or not isinstance(expected_sources, list)
            or not isinstance(expected_scopes, list)
            or not isinstance(expected_definitions, list)
            or not expected_definitions
            or not isinstance(snapshot.get("expected_type_check_type"), str)
            or not isinstance(expected_ast_summary, dict)
        ):
            raise SystemExit(
                f"web route smoke check failed: certified rule {rule_id} snapshot schema drift"
            )
        result = run_pipeline(snapshot["sentence"], require_coq=False)
        if not result.get("ok"):
            raise SystemExit(
                f"web route smoke check failed: certified rule {rule_id} snapshot no longer runs"
            )
        observe_modifier_sequences(result, f"certified rule {rule_id} primary")
        if result.get("construction_rule", {}).get("id") != rule_id:
            raise SystemExit(
                f"web route smoke check failed: certified rule {rule_id} snapshot rule drift"
            )
        if result.get("event_semantics", {}).get("analysis") != snapshot.get(
            "expected_event_analysis"
        ):
            raise SystemExit(
                f"web route smoke check failed: certified rule {rule_id} semantic snapshot analysis drift"
            )
        dependent_type_translation = str(result.get("dependent_type_translation", ""))
        for fragment in expected_fragments:
            if fragment not in dependent_type_translation:
                raise SystemExit(
                    "web route smoke check failed: certified rule "
                    f"{rule_id} semantic snapshot translation drift"
                )
        readings = result.get("semantic_readings")
        if not isinstance(readings, list):
            raise SystemExit(
                f"web route smoke check failed: certified rule {rule_id} semantic snapshot readings drift"
            )
        observed_names = [reading.get("name") for reading in readings if isinstance(reading, dict)]
        observed_sources = [
            reading.get("source") for reading in readings if isinstance(reading, dict)
        ]
        observed_scopes = [
            reading.get("scope") for reading in readings if isinstance(reading, dict)
        ]
        observed_definitions = [
            reading.get("coq_definition")
            for reading in readings
            if isinstance(reading, dict)
        ]
        if (
            observed_names != expected_reading_names
            or observed_sources != expected_sources
            or observed_scopes != expected_scopes
            or observed_definitions != expected_definitions
        ):
            raise SystemExit(
                f"web route smoke check failed: certified rule {rule_id} semantic snapshot reading drift"
            )
        if result.get("type_check", {}).get("type") != snapshot.get(
            "expected_type_check_type"
        ):
            raise SystemExit(
                f"web route smoke check failed: certified rule {rule_id} semantic snapshot type drift"
            )
        observed_ast_summary = ast_structure_summary(result.get("ast", {}))
        if observed_ast_summary != expected_ast_summary:
            raise SystemExit(
                f"web route smoke check failed: certified rule {rule_id} semantic snapshot AST drift"
            )
        exported_definitions = exported_prop_definition_names(result.get("coq_code", ""))
        missing_exports = sorted(set(expected_definitions) - set(exported_definitions))
        if missing_exports:
            raise SystemExit(
                "web route smoke check failed: certified rule "
                f"{rule_id} semantic snapshot export drift"
            )
    seen_variant_keys: set[tuple[str, str]] = set()
    for variant in registered_variant_cases:
        if not isinstance(variant, dict):
            raise SystemExit(
                "web route smoke check failed: certified registered variant shape drift"
            )
        rule_id = variant.get("rule_id")
        variant_id = variant.get("variant_id")
        sentence = variant.get("sentence")
        expected_fragments = variant.get("expected_dependent_type_fragments")
        if (
            not isinstance(rule_id, str)
            or rule_id not in rules
            or not isinstance(variant_id, str)
            or not variant_id
            or not isinstance(sentence, str)
            or not sentence
            or not isinstance(expected_fragments, list)
            or not expected_fragments
            or not all(isinstance(fragment, str) and fragment for fragment in expected_fragments)
            or variant.get("expected_verification_scope_kind") != "registered_construction"
            or variant.get("expected_certification_level") != "construction_rule"
            or variant.get("boundary_status") != "registered_variant_example"
            or not isinstance(variant.get("expected_event_analysis"), str)
            or not isinstance(variant.get("expected_ast_kind"), str)
        ):
            raise SystemExit(
                "web route smoke check failed: certified registered variant schema drift"
            )
        if variant.get("surface_parser_family") == "modified_transitive_adv_sequence":
            if (
                rule_id != "modified_transitive_predication"
                or variant.get("modifier_count") not in expected_surface_counts
                or not isinstance(variant.get("time_wrapped"), bool)
            ):
                raise SystemExit(
                    "web route smoke check failed: certified surface parser variant drift"
                )
        key = (rule_id, variant_id)
        if key in seen_variant_keys:
            raise SystemExit("web route smoke check failed: duplicate certified registered variant")
        seen_variant_keys.add(key)
        accepted_examples = registered_by_id[rule_id].get("accepted_examples")
        if not isinstance(accepted_examples, list) or sentence not in accepted_examples:
            raise SystemExit(
                f"web route smoke check failed: certified rule {rule_id} variant example drift"
            )
        result = run_pipeline(sentence, require_coq=False)
        if (
            not result.get("ok")
            or result.get("construction_rule", {}).get("id") != rule_id
            or result.get("verification_scope", {}).get("kind") != "registered_construction"
            or result.get("verification_scope", {}).get("certification_level")
            != "construction_rule"
            or result.get("event_semantics", {}).get("analysis")
            != variant.get("expected_event_analysis")
            or result.get("ast", {}).get("kind") != variant.get("expected_ast_kind")
        ):
            raise SystemExit(
                f"web route smoke check failed: certified rule {rule_id} variant runtime drift"
            )
        observe_modifier_sequences(result, f"certified rule {rule_id} variant {variant_id}")
        dependent_type_translation = str(result.get("dependent_type_translation", ""))
        for fragment in expected_fragments:
            if fragment not in dependent_type_translation:
                raise SystemExit(
                    "web route smoke check failed: certified rule "
                    f"{rule_id} variant translation drift"
                )
    if not observed_application_modifier_counts:
        raise SystemExit(
            "web route smoke check failed: certified modifier sequence live coverage missing"
        )
    observed_declared_counts = sorted(
        set(observed_application_modifier_counts)
        & set(expected_declared_modifier_counts),
    )
    if (
        max(observed_application_modifier_counts)
        != modifier_contract.get("max_declared_application_modifier_count")
        or observed_declared_counts != expected_declared_modifier_counts
    ):
        raise SystemExit(
            "web route smoke check failed: certified modifier sequence live coverage drift"
        )
    if set(observed_modifier_roles) != expected_modifier_role_names:
        raise SystemExit(
            "web route smoke check failed: certified modifier sequence role inventory drift"
        )
    for role, minimum in expected_modifier_role_minima.items():
        if observed_modifier_roles[role] < minimum:
            raise SystemExit(
                "web route smoke check failed: certified modifier sequence role coverage drift"
            )
    fallback = manifest.get("fallback")
    if (
        not isinstance(fallback, dict)
        or fallback.get("verification_scope_kind") != "fallback_shallow"
        or fallback.get("certification_level") != "shallow_scaffold"
    ):
        raise SystemExit("web route smoke check failed: certified fallback drift")
    fallback_gaps = fallback.get("certification_gaps")
    if (
        not isinstance(fallback_gaps, list)
        or [gap.get("id") for gap in fallback_gaps if isinstance(gap, dict)]
        != [
            "no_registered_construction_rule",
            "no_fragment_specific_readings",
            "no_construction_hygiene_policy",
        ]
    ):
        raise SystemExit("web route smoke check failed: certified fallback gap drift")
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
    modifier_sequence_contract = manifest.get("registered_modifier_sequence_contract")
    if not isinstance(modifier_sequence_contract, dict):
        modifier_sequence_contract = {}
    modifier_role_inventory = [
        item
        for item in modifier_sequence_contract.get("registered_semantic_role_inventory", [])
        if isinstance(item, dict)
    ]
    modifier_role_witnesses = [
        item
        for item in modifier_sequence_contract.get("registered_semantic_role_witnesses", [])
        if isinstance(item, dict)
    ]
    modifier_role_witness_selection_contract = modifier_sequence_contract.get(
        "semantic_role_witness_selection_contract",
    )
    if not isinstance(modifier_role_witness_selection_contract, dict):
        modifier_role_witness_selection_contract = {}
    modifier_role_source_contract = modifier_sequence_contract.get(
        "semantic_role_source_contract",
    )
    if not isinstance(modifier_role_source_contract, dict):
        modifier_role_source_contract = {}

    def csv_attribute(value: object) -> str:
        if not isinstance(value, list):
            return ""
        return ",".join(str(item) for item in value)

    def data_fragment(name: str, value: object) -> str:
        return f'{name}="{html.escape(str(value), quote=True)}"'

    modifier_role_names = ",".join(
        str(item.get("role", ""))
        for item in modifier_role_inventory
        if isinstance(item.get("role"), str)
    )
    modifier_role_minima = ",".join(
        f"{item.get('role')}:{item.get('minimum_observed_occurrences')}"
        for item in modifier_role_inventory
        if isinstance(item.get("role"), str)
        and isinstance(item.get("minimum_observed_occurrences"), int)
    )
    modifier_role_witness_summary = ",".join(
        f"{item.get('role')}:{item.get('normalized_modifier')}"
        for item in modifier_role_witnesses
        if isinstance(item.get("role"), str)
        and isinstance(item.get("normalized_modifier"), str)
    )
    witness_sources = csv_attribute(
        modifier_role_witness_selection_contract.get("sentence_sources"),
    )
    source_roles = csv_attribute(
        modifier_role_source_contract.get("derived_role_inventory"),
    )
    surface_parser_coverage = manifest.get("surface_parser_coverage")
    if not isinstance(surface_parser_coverage, dict):
        surface_parser_coverage = {}
    surface_family_names = [
        family
        for family, item in surface_parser_coverage.items()
        if isinstance(family, str) and isinstance(item, dict)
    ]
    surface_family_name = surface_family_names[0] if surface_family_names else ""
    modified_surface = surface_parser_coverage.get(surface_family_name, {})
    if not isinstance(modified_surface, dict):
        modified_surface = {}
    surface_generation_spec = modified_surface.get("witness_generation_spec")
    if not isinstance(surface_generation_spec, dict):
        surface_generation_spec = {}
    surface_generation_modifiers = surface_generation_spec.get("modifiers")
    surface_examples = [
        item
        for item in modified_surface.get("verified_examples", [])
        if isinstance(item, dict)
    ]
    surface_slot_probes = modified_surface.get("slot_probe_examples")
    if not isinstance(surface_slot_probes, dict):
        surface_slot_probes = {}
    surface_probe_rows = [
        item
        for item in surface_slot_probes.get("probes", [])
        if isinstance(item, dict)
    ]
    surface_matrix_rows = [
        item
        for item in surface_slot_probes.get("matrix_examples", [])
        if isinstance(item, dict)
    ]
    surface_slot_probe_generation_spec = surface_slot_probes.get(
        "probe_generation_spec",
    )
    if not isinstance(surface_slot_probe_generation_spec, dict):
        surface_slot_probe_generation_spec = {}
    surface_slot_probe_matrix_generation_spec = surface_slot_probes.get(
        "matrix_generation_spec",
    )
    if not isinstance(surface_slot_probe_matrix_generation_spec, dict):
        surface_slot_probe_matrix_generation_spec = {}
    surface_slot_probe_matrix_type_contract_registry = (
        surface_slot_probe_matrix_generation_spec.get("type_contract_registry")
    )
    if not isinstance(surface_slot_probe_matrix_type_contract_registry, dict):
        surface_slot_probe_matrix_type_contract_registry = {}
    diagnostic_categories = surface_slot_probe_matrix_type_contract_registry.get(
        "diagnostic_categories",
    )
    if not isinstance(diagnostic_categories, list):
        diagnostic_categories = []
    diagnostic_category_items = [
        item for item in diagnostic_categories if isinstance(item, dict)
    ]
    diagnostic_category_names = ",".join(
        str(item.get("category", ""))
        for item in diagnostic_category_items
        if item.get("category")
    )
    expected_fragments = [
        'class="panel certified-fragment-panel"',
        'data-certified-fragment-schema="certified_fragment.v1"',
        'data-certified-fragment-api="/api/certified-fragment"',
        'data-full-natural-language-certification="false"',
        'data-fallback-certification-level="shallow_scaffold"',
        'data-fallback-gap-id="no_registered_construction_rule"',
        'data-fallback-gap-id="no_fragment_specific_readings"',
        'data-fallback-gap-id="no_construction_hygiene_policy"',
        f'data-registered-construction-count="{len(registered)}"',
        f'data-semantic-snapshot-count="{manifest.get("semantic_snapshot_count")}"',
        (
            'data-coverage-registered-success-count="'
            f'{manifest.get("coverage_matrix_counts", {}).get("registered_success_cases")}"'
        ),
        (
            'data-coverage-registered-variant-success-count="'
            f'{manifest.get("coverage_matrix_counts", {}).get("registered_variant_success_cases")}"'
        ),
        (
            'data-coverage-fallback-success-count="'
            f'{manifest.get("coverage_matrix_counts", {}).get("fallback_success_cases")}"'
        ),
        (
            'data-coverage-rejected-unsupported-count="'
            f'{manifest.get("coverage_matrix_counts", {}).get("rejected_unsupported_cases")}"'
        ),
        data_fragment("data-surface-parser-family", surface_family_name),
        data_fragment(
            "data-surface-type-level-open-ended",
            str(modified_surface.get("type_level_open_ended") is True).lower(),
        ),
        data_fragment(
            "data-surface-parser-claim",
            modified_surface.get("surface_parser_claim", ""),
        ),
        data_fragment(
            "data-surface-full-certification",
            str(modified_surface.get("full_surface_parser_certification") is True).lower(),
        ),
        data_fragment(
            "data-surface-verified-counts",
            csv_attribute(modified_surface.get("verified_modifier_counts")),
        ),
        data_fragment(
            "data-surface-timed-counts",
            csv_attribute(modified_surface.get("verified_timed_modifier_counts")),
        ),
        data_fragment(
            "data-surface-untimed-counts",
            csv_attribute(modified_surface.get("verified_untimed_modifier_counts")),
        ),
        data_fragment(
            "data-surface-max-verified-count",
            modified_surface.get("max_verified_modifier_count", ""),
        ),
        data_fragment(
            "data-surface-verified-example-count",
            modified_surface.get("verified_example_count", ""),
        ),
        data_fragment(
            "data-surface-generator-schema",
            surface_generation_spec.get("schema_version", ""),
        ),
        data_fragment(
            "data-surface-generator-kind",
            surface_generation_spec.get("generator", ""),
        ),
        data_fragment(
            "data-surface-generator-modifier-count",
            len(surface_generation_modifiers)
            if isinstance(surface_generation_modifiers, list)
            else "",
        ),
        data_fragment(
            "data-surface-generator-time-suffix",
            surface_generation_spec.get("time_suffix", ""),
        ),
        data_fragment(
            "data-surface-slot-probe-schema",
            surface_slot_probes.get("schema_version", ""),
        ),
        data_fragment(
            "data-surface-slot-probe-count",
            surface_slot_probes.get("probe_count", ""),
        ),
        data_fragment(
            "data-surface-slot-probe-generation-schema",
            surface_slot_probe_generation_spec.get("schema_version", ""),
        ),
        data_fragment(
            "data-surface-slot-probe-generation-kind",
            surface_slot_probe_generation_spec.get("generator", ""),
        ),
        data_fragment(
            "data-surface-slot-probe-matrix-count",
            surface_slot_probes.get("matrix_example_count", ""),
        ),
        data_fragment(
            "data-surface-slot-probe-matrix-generation-schema",
            surface_slot_probe_matrix_generation_spec.get("schema_version", ""),
        ),
        data_fragment(
            "data-surface-slot-probe-matrix-generation-kind",
            surface_slot_probe_matrix_generation_spec.get("generator", ""),
        ),
        data_fragment(
            "data-surface-slot-probe-matrix-type-contract-schema",
            surface_slot_probe_matrix_type_contract_registry.get("schema_version", ""),
        ),
        data_fragment(
            "data-surface-slot-probe-matrix-type-contract-entry-schema",
            surface_slot_probe_matrix_type_contract_registry.get("entry_schema", ""),
        ),
        data_fragment(
            "data-surface-slot-probe-matrix-type-contract-entry-count",
            surface_slot_probe_matrix_type_contract_registry.get("entry_count", ""),
        ),
        data_fragment(
            "data-surface-slot-probe-matrix-type-contract-diagnostic-schema",
            surface_slot_probe_matrix_type_contract_registry.get("diagnostic_schema", ""),
        ),
        data_fragment(
            "data-surface-slot-probe-matrix-type-contract-diagnostic-count",
            len(diagnostic_category_items),
        ),
        data_fragment(
            "data-surface-slot-probe-matrix-type-contract-diagnostic-categories",
            diagnostic_category_names,
        ),
        data_fragment(
            "data-surface-slot-probe-matrix-type-contract-source",
            surface_slot_probe_matrix_type_contract_registry.get("source", ""),
        ),
        data_fragment(
            "data-surface-slot-probe-matrix-type-contract-registry-id",
            surface_slot_probe_matrix_type_contract_registry.get("registry_id", ""),
        ),
        data_fragment(
            "data-modifier-sequence-contract-schema",
            modifier_sequence_contract.get("schema_version", ""),
        ),
        data_fragment(
            "data-modifier-sequence-claim",
            modifier_sequence_contract.get("claim", ""),
        ),
        data_fragment(
            "data-modifier-sequence-case-count",
            modifier_sequence_contract.get("case_count", ""),
        ),
        data_fragment(
            "data-modifier-sequence-max-count",
            modifier_sequence_contract.get("max_declared_application_modifier_count", ""),
        ),
        data_fragment(
            "data-modifier-sequence-declared-counts",
            csv_attribute(
                modifier_sequence_contract.get("declared_application_modifier_counts"),
            ),
        ),
        data_fragment(
            "data-modifier-sequence-full-certification",
            str(modifier_sequence_contract.get("full_surface_parser_certification") is True).lower(),
        ),
        data_fragment("data-modifier-sequence-role-inventory", modifier_role_names),
        data_fragment("data-modifier-sequence-role-count", len(modifier_role_inventory)),
        data_fragment("data-modifier-sequence-role-minima", modifier_role_minima),
        data_fragment(
            "data-modifier-sequence-role-witness-count",
            len(modifier_role_witnesses),
        ),
        data_fragment(
            "data-modifier-sequence-role-witnesses",
            modifier_role_witness_summary,
        ),
        data_fragment(
            "data-modifier-sequence-role-witness-selection-schema",
            modifier_role_witness_selection_contract.get("schema_version", ""),
        ),
        data_fragment(
            "data-modifier-sequence-role-witness-selection-scope",
            modifier_role_witness_selection_contract.get("selection_scope", ""),
        ),
        data_fragment(
            "data-modifier-sequence-role-witness-selection-unit",
            modifier_role_witness_selection_contract.get("selection_unit", ""),
        ),
        data_fragment(
            "data-modifier-sequence-role-witness-selection-sources",
            witness_sources,
        ),
        data_fragment(
            "data-modifier-sequence-role-witness-full-generation",
            str(modifier_role_witness_selection_contract.get("full_witness_generation") is True).lower(),
        ),
        data_fragment(
            "data-modifier-sequence-role-source-schema",
            modifier_role_source_contract.get("schema_version", ""),
        ),
        data_fragment(
            "data-modifier-sequence-role-source-module",
            modifier_role_source_contract.get("source_module", ""),
        ),
        data_fragment(
            "data-modifier-sequence-role-source-table",
            modifier_role_source_contract.get("preposition_role_table", ""),
        ),
        data_fragment("data-modifier-sequence-role-source-derived", source_roles),
        'data-modifier-sequence-invariant="modifier_vector_length_matches_modifiers"',
        'data-modifier-sequence-invariant="modifier_roles_are_adv_not_entity"',
        'data-modifier-sequence-invariant="registered_modifier_roles_have_live_witnesses"',
        "surface parser coverage",
        "<h2>Certified Fragment</h2>",
    ]
    expected_fragments.extend(
        data_fragment("data-modifier-sequence-role", item.get("role", ""))
        for item in modifier_role_inventory
    )
    expected_fragments.extend(
        data_fragment(
            "data-modifier-sequence-role-minimum",
            item.get("minimum_observed_occurrences", ""),
        )
        for item in modifier_role_inventory
    )
    for witness in modifier_role_witnesses:
        expected_fragments.append(
            data_fragment(
                "data-modifier-sequence-role-witness-role",
                witness.get("role", ""),
            ),
        )
        expected_fragments.append(
            data_fragment(
                "data-modifier-sequence-role-witness-normalized",
                witness.get("normalized_modifier", ""),
            ),
        )
    for example in surface_examples:
        expected_fragments.extend(
            [
                data_fragment(
                    "data-surface-example-variant-id",
                    example.get("variant_id", ""),
                ),
                data_fragment(
                    "data-surface-example-sentence",
                    example.get("sentence", ""),
                ),
                data_fragment(
                    "data-surface-example-modifier-count",
                    example.get("modifier_count", ""),
                ),
                data_fragment(
                    "data-surface-example-time-wrapped",
                    str(example.get("time_wrapped") is True).lower(),
                ),
                data_fragment(
                    "data-surface-example-source",
                    example.get("source", ""),
                ),
                data_fragment(
                    "data-surface-example-analysis",
                    example.get("expected_event_analysis", ""),
                ),
                data_fragment(
                    "data-surface-example-ast-kind",
                    example.get("expected_ast_kind", ""),
                ),
                data_fragment(
                    "data-surface-example-fragment-count",
                    len(example.get("expected_dependent_type_fragments", []))
                    if isinstance(
                        example.get("expected_dependent_type_fragments"),
                        list,
                    )
                    else 0,
                ),
            ],
        )
    for probe in surface_probe_rows:
        expected_fragments.extend(
            [
                data_fragment("data-surface-slot-probe-id", probe.get("probe_id", "")),
                data_fragment("data-surface-slot-probe-slot", probe.get("slot", "")),
                data_fragment(
                    "data-surface-slot-probe-sentence",
                    probe.get("sentence", ""),
                ),
                data_fragment(
                    "data-surface-slot-probe-modifier-count",
                    probe.get("modifier_count", ""),
                ),
                data_fragment(
                    "data-surface-slot-probe-time-wrapped",
                    str(probe.get("time_wrapped") is True).lower(),
                ),
            ],
        )
    for matrix_row in surface_matrix_rows:
        agent = matrix_row.get("agent")
        if not isinstance(agent, dict):
            agent = {}
        predicate = matrix_row.get("predicate")
        if not isinstance(predicate, dict):
            predicate = {}
        theme = matrix_row.get("theme")
        if not isinstance(theme, dict):
            theme = {}
        type_contract = matrix_row.get("type_contract")
        if not isinstance(type_contract, dict):
            type_contract = {}
        expected_fragments.extend(
            [
                data_fragment(
                    "data-surface-slot-matrix-id",
                    matrix_row.get("matrix_id", ""),
                ),
                data_fragment(
                    "data-surface-slot-matrix-profile",
                    matrix_row.get("profile_id", ""),
                ),
                data_fragment(
                    "data-surface-slot-matrix-agent",
                    agent.get("semantic", ""),
                ),
                data_fragment(
                    "data-surface-slot-matrix-agent-type",
                    type_contract.get("agent_dependent_type", ""),
                ),
                data_fragment(
                    "data-surface-slot-matrix-predicate",
                    predicate.get("semantic", ""),
                ),
                data_fragment(
                    "data-surface-slot-matrix-predicate-type",
                    type_contract.get("predicate_dependent_type", ""),
                ),
                data_fragment(
                    "data-surface-slot-matrix-theme",
                    theme.get("semantic", ""),
                ),
                data_fragment(
                    "data-surface-slot-matrix-theme-type",
                    type_contract.get("theme_dependent_type", ""),
                ),
                data_fragment(
                    "data-surface-slot-matrix-modifier-type",
                    type_contract.get("modifier_dependent_type", ""),
                ),
                data_fragment(
                    "data-surface-slot-matrix-time-type",
                    type_contract.get("time_argument_type", ""),
                ),
                data_fragment(
                    "data-surface-slot-matrix-modifier-count",
                    matrix_row.get("modifier_count", ""),
                ),
                data_fragment(
                    "data-surface-slot-matrix-time-wrapped",
                    str(matrix_row.get("time_wrapped") is True).lower(),
                ),
            ],
        )
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
        for item in coverage.get("registered_success_cases", []):
            if not isinstance(item, dict):
                continue
            expected_fragments.extend(
                [
                    data_fragment("data-coverage-kind", "registered_success"),
                    data_fragment("data-coverage-rule-id", item.get("rule_id", "")),
                    data_fragment("data-coverage-sentence", item.get("sentence", "")),
                    data_fragment(
                        "data-coverage-scope",
                        item.get("expected_verification_scope_kind", ""),
                    ),
                    data_fragment(
                        "data-coverage-level",
                        item.get("expected_certification_level", ""),
                    ),
                    data_fragment(
                        "data-coverage-boundary",
                        item.get("boundary_status", ""),
                    ),
                ],
            )
        for item in coverage.get("registered_variant_success_cases", []):
            if not isinstance(item, dict):
                continue
            expected_fragments.extend(
                [
                    data_fragment("data-coverage-kind", "registered_variant_success"),
                    data_fragment("data-coverage-rule-id", item.get("rule_id", "")),
                    data_fragment("data-coverage-variant-id", item.get("variant_id", "")),
                    data_fragment("data-coverage-sentence", item.get("sentence", "")),
                    data_fragment(
                        "data-coverage-scope",
                        item.get("expected_verification_scope_kind", ""),
                    ),
                    data_fragment(
                        "data-coverage-level",
                        item.get("expected_certification_level", ""),
                    ),
                    data_fragment(
                        "data-coverage-boundary",
                        item.get("boundary_status", ""),
                    ),
                ],
            )
        for item in coverage.get("fallback_success_cases", []):
            if not isinstance(item, dict):
                continue
            expected_fragments.extend(
                [
                    data_fragment("data-coverage-kind", "fallback_success"),
                    data_fragment("data-coverage-sentence", item.get("sentence", "")),
                    data_fragment(
                        "data-coverage-scope",
                        item.get("expected_verification_scope_kind", ""),
                    ),
                    data_fragment(
                        "data-coverage-level",
                        item.get("expected_certification_level", ""),
                    ),
                    data_fragment(
                        "data-coverage-boundary",
                        item.get("boundary_status", ""),
                    ),
                ],
            )
        for item in coverage.get("rejected_unsupported_cases", []):
            if not isinstance(item, dict):
                continue
            expected_fragments.extend(
                [
                    data_fragment("data-coverage-kind", "rejected_unsupported"),
                    data_fragment("data-coverage-marker", item.get("marker", "")),
                    data_fragment("data-coverage-sentence", item.get("sentence", "")),
                    data_fragment(
                        "data-coverage-scope",
                        item.get("expected_verification_scope_kind", ""),
                    ),
                    data_fragment(
                        "data-coverage-level",
                        item.get("expected_certification_level", ""),
                    ),
                    data_fragment(
                        "data-coverage-boundary",
                        item.get("boundary_status", ""),
                    ),
                ],
            )
    snapshots = manifest.get("semantic_snapshots", [])
    if isinstance(snapshots, list):
        for item in snapshots:
            if not isinstance(item, dict):
                continue
            expected_ast_summary = item.get("expected_ast_summary")
            if not isinstance(expected_ast_summary, dict):
                expected_ast_summary = {}
            expected_fragments.extend(
                [
                    data_fragment(
                        "data-semantic-snapshot-rule-id",
                        item.get("rule_id", ""),
                    ),
                    data_fragment(
                        "data-semantic-snapshot-sentence",
                        item.get("sentence", ""),
                    ),
                    data_fragment(
                        "data-semantic-snapshot-analysis",
                        item.get("expected_event_analysis", ""),
                    ),
                    data_fragment(
                        "data-semantic-snapshot-ast-kind",
                        expected_ast_summary.get("kind", ""),
                    ),
                    data_fragment(
                        "data-semantic-snapshot-fragment-count",
                        len(item.get("expected_dependent_type_fragments", []))
                        if isinstance(
                            item.get("expected_dependent_type_fragments"),
                            list,
                        )
                        else 0,
                    ),
                    data_fragment(
                        "data-semantic-snapshot-reading-count",
                        len(item.get("expected_reading_names", []))
                        if isinstance(item.get("expected_reading_names"), list)
                        else 0,
                    ),
                    data_fragment(
                        "data-semantic-snapshot-reading-names",
                        csv_attribute(item.get("expected_reading_names")),
                    ),
                    data_fragment(
                        "data-semantic-snapshot-reading-sources",
                        csv_attribute(item.get("expected_reading_sources")),
                    ),
                    data_fragment(
                        "data-semantic-snapshot-reading-scopes",
                        csv_attribute(item.get("expected_reading_scopes")),
                    ),
                    data_fragment(
                        "data-semantic-snapshot-coq-definitions",
                        csv_attribute(item.get("expected_coq_definitions")),
                    ),
                    data_fragment(
                        "data-semantic-snapshot-type-check",
                        item.get("expected_type_check_type", ""),
                    ),
                ],
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
    type_contract_context = surface_type_contract_diagnostics_context_preview()
    type_contract_categories = surface_type_contract_diagnostic_category_text(
        type_contract_context
    )
    require_html_fragments(
        page,
        [
            'class="panel recovery-action-exports-panel"',
            'data-export-schema="diagnostic_recovery_action.v1"',
            f'data-export-case="{html.escape(case, quote=True)}"',
            f'data-export-count="{len(expected_actions)}"',
            (
                'data-surface-type-contract-diagnostic-schema="'
                + html.escape(
                    str(type_contract_context.get("schema_version", "")),
                    quote=True,
                )
                + '"'
            ),
            (
                'data-surface-type-contract-diagnostic-count="'
                + html.escape(
                    str(type_contract_context.get("category_count", "")),
                    quote=True,
                )
                + '"'
            ),
            (
                'data-surface-type-contract-diagnostic-categories="'
                + html.escape(type_contract_categories, quote=True)
                + '"'
            ),
            (
                'data-surface-type-contract-registry-id="'
                + html.escape(
                    str(type_contract_context.get("registry_id", "")),
                    quote=True,
                )
                + '"'
            ),
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
                "<dt>type contract</dt><dd><code>"
                + html.escape(str(type_contract_context.get("schema_version", "")))
                + "</code></dd>"
            ),
            (
                "<dt>type contract categories</dt><dd><code>"
                + html.escape(type_contract_categories)
                + "</code></dd>"
            ),
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
    try:
        server = ThreadingHTTPServer(("127.0.0.1", 0), PipelineHandler)
    except PermissionError as exc:
        print(f"==> web route smoke check skipped: local HTTP server unavailable ({exc})")
        return
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        base_url = f"http://127.0.0.1:{port}"
        opener = build_opener(ProxyHandler({}))
        event_counting_sentence = "John knocked twice"
        event_counting_query = urlencode(
            {"sentence": event_counting_sentence, "require_coq": "1"}
        )
        with opener.open(f"{base_url}/api/analyze?{event_counting_query}", timeout=5) as response:
            event_counting_payload = json.load(response)
        with opener.open(f"{base_url}/?{event_counting_query}", timeout=5) as response:
            event_counting_page = response.read().decode("utf-8")
        validate_analyze_event_counting_success(
            event_counting_payload,
            event_counting_page,
            event_counting_sentence,
        )
        temporal_event_counting_sentence = "John knocked twice yesterday"
        temporal_event_counting_query = urlencode(
            {"sentence": temporal_event_counting_sentence, "require_coq": "1"}
        )
        with opener.open(
            f"{base_url}/api/analyze?{temporal_event_counting_query}",
            timeout=5,
        ) as response:
            temporal_event_counting_payload = json.load(response)
        with opener.open(
            f"{base_url}/?{temporal_event_counting_query}",
            timeout=5,
        ) as response:
            temporal_event_counting_page = response.read().decode("utf-8")
        validate_analyze_temporal_event_counting_success(
            temporal_event_counting_payload,
            temporal_event_counting_page,
            temporal_event_counting_sentence,
        )
        active_omission_sentence = "John ate"
        active_omission_query = urlencode(
            {"sentence": active_omission_sentence, "require_coq": "1"}
        )
        with opener.open(f"{base_url}/api/analyze?{active_omission_query}", timeout=5) as response:
            active_omission_payload = json.load(response)
        with opener.open(f"{base_url}/?{active_omission_query}", timeout=5) as response:
            active_omission_page = response.read().decode("utf-8")
        validate_analyze_active_argument_omission_success(
            active_omission_payload,
            active_omission_page,
            active_omission_sentence,
        )
        plain_intransitive_sentence = "Mary smiled"
        plain_intransitive_query = urlencode(
            {"sentence": plain_intransitive_sentence, "require_coq": "1"}
        )
        with opener.open(
            f"{base_url}/api/analyze?{plain_intransitive_query}",
            timeout=5,
        ) as response:
            plain_intransitive_payload = json.load(response)
        with opener.open(
            f"{base_url}/?{plain_intransitive_query}",
            timeout=5,
        ) as response:
            plain_intransitive_page = response.read().decode("utf-8")
        validate_analyze_plain_intransitive_success(
            plain_intransitive_payload,
            plain_intransitive_page,
            plain_intransitive_sentence,
        )
        timed_plain_intransitive_sentence = "Mary smiled yesterday"
        timed_plain_intransitive_query = urlencode(
            {"sentence": timed_plain_intransitive_sentence, "require_coq": "1"}
        )
        with opener.open(
            f"{base_url}/api/analyze?{timed_plain_intransitive_query}",
            timeout=5,
        ) as response:
            timed_plain_intransitive_payload = json.load(response)
        with opener.open(
            f"{base_url}/?{timed_plain_intransitive_query}",
            timeout=5,
        ) as response:
            timed_plain_intransitive_page = response.read().decode("utf-8")
        validate_analyze_plain_intransitive_success(
            timed_plain_intransitive_payload,
            timed_plain_intransitive_page,
            timed_plain_intransitive_sentence,
        )
        manner_intransitive_sentence = "Mary laughed loudly"
        manner_intransitive_query = urlencode(
            {"sentence": manner_intransitive_sentence, "require_coq": "1"}
        )
        with opener.open(
            f"{base_url}/api/analyze?{manner_intransitive_query}",
            timeout=5,
        ) as response:
            manner_intransitive_payload = json.load(response)
        with opener.open(
            f"{base_url}/?{manner_intransitive_query}",
            timeout=5,
        ) as response:
            manner_intransitive_page = response.read().decode("utf-8")
        validate_analyze_manner_intransitive_success(
            manner_intransitive_payload,
            manner_intransitive_page,
            manner_intransitive_sentence,
        )
        timed_manner_intransitive_sentence = "Mary laughed loudly yesterday"
        timed_manner_intransitive_query = urlencode(
            {"sentence": timed_manner_intransitive_sentence, "require_coq": "1"}
        )
        with opener.open(
            f"{base_url}/api/analyze?{timed_manner_intransitive_query}",
            timeout=5,
        ) as response:
            timed_manner_intransitive_payload = json.load(response)
        with opener.open(
            f"{base_url}/?{timed_manner_intransitive_query}",
            timeout=5,
        ) as response:
            timed_manner_intransitive_page = response.read().decode("utf-8")
        validate_analyze_manner_intransitive_success(
            timed_manner_intransitive_payload,
            timed_manner_intransitive_page,
            timed_manner_intransitive_sentence,
        )
        instrument_intransitive_sentence = "Mary laughed with a telescope"
        instrument_intransitive_query = urlencode(
            {"sentence": instrument_intransitive_sentence, "require_coq": "1"}
        )
        with opener.open(
            f"{base_url}/api/analyze?{instrument_intransitive_query}",
            timeout=5,
        ) as response:
            instrument_intransitive_payload = json.load(response)
        with opener.open(
            f"{base_url}/?{instrument_intransitive_query}",
            timeout=5,
        ) as response:
            instrument_intransitive_page = response.read().decode("utf-8")
        validate_analyze_instrument_intransitive_success(
            instrument_intransitive_payload,
            instrument_intransitive_page,
            instrument_intransitive_sentence,
        )
        timed_instrument_intransitive_sentence = (
            "Mary laughed with a telescope yesterday"
        )
        timed_instrument_intransitive_query = urlencode(
            {"sentence": timed_instrument_intransitive_sentence, "require_coq": "1"}
        )
        with opener.open(
            f"{base_url}/api/analyze?{timed_instrument_intransitive_query}",
            timeout=5,
        ) as response:
            timed_instrument_intransitive_payload = json.load(response)
        with opener.open(
            f"{base_url}/?{timed_instrument_intransitive_query}",
            timeout=5,
        ) as response:
            timed_instrument_intransitive_page = response.read().decode("utf-8")
        validate_analyze_instrument_intransitive_success(
            timed_instrument_intransitive_payload,
            timed_instrument_intransitive_page,
            timed_instrument_intransitive_sentence,
        )
        for directional_sentence in (
            "Mary laughed from a window",
            "Mary laughed from a window yesterday",
            "Mary laughed into a room yesterday",
            "Mary laughed from a window into a room yesterday",
        ):
            directional_query = urlencode(
                {"sentence": directional_sentence, "require_coq": "1"}
            )
            with opener.open(
                f"{base_url}/api/analyze?{directional_query}",
                timeout=5,
            ) as response:
                directional_payload = json.load(response)
            with opener.open(
                f"{base_url}/?{directional_query}",
                timeout=5,
            ) as response:
                directional_page = response.read().decode("utf-8")
            validate_analyze_directional_intransitive_success(
                directional_payload,
                directional_page,
                directional_sentence,
            )
        for directional_instrument_sentence in (
            "Mary laughed from a window with a camera",
            "Mary laughed from a window with a camera yesterday",
            "Mary laughed into a room with a camera yesterday",
            "Mary laughed from a window into a room with a camera yesterday",
        ):
            directional_instrument_query = urlencode(
                {
                    "sentence": directional_instrument_sentence,
                    "require_coq": "1",
                }
            )
            with opener.open(
                f"{base_url}/api/analyze?{directional_instrument_query}",
                timeout=5,
            ) as response:
                directional_instrument_payload = json.load(response)
            with opener.open(
                f"{base_url}/?{directional_instrument_query}",
                timeout=5,
            ) as response:
                directional_instrument_page = response.read().decode("utf-8")
            validate_analyze_directional_instrument_intransitive_success(
                directional_instrument_payload,
                directional_instrument_page,
                directional_instrument_sentence,
            )
        for directional_instrument_location_sentence in (
            "Mary laughed from a window with a camera beside a shelf",
            "Mary laughed from a window with a camera beside a shelf yesterday",
            "Mary laughed into a room with a camera beside a shelf yesterday",
            (
                "Mary laughed from a window into a room with a camera beside a shelf "
                "yesterday"
            ),
        ):
            directional_instrument_location_query = urlencode(
                {
                    "sentence": directional_instrument_location_sentence,
                    "require_coq": "1",
                }
            )
            with opener.open(
                f"{base_url}/api/analyze?{directional_instrument_location_query}",
                timeout=5,
            ) as response:
                directional_instrument_location_payload = json.load(response)
            with opener.open(
                f"{base_url}/?{directional_instrument_location_query}",
                timeout=5,
            ) as response:
                directional_instrument_location_page = response.read().decode("utf-8")
            validate_analyze_directional_instrument_location_intransitive_success(
                directional_instrument_location_payload,
                directional_instrument_location_page,
                directional_instrument_location_sentence,
            )
        for directional_instrument_location_manner_sentence in (
            "Mary laughed from a window with a camera beside a shelf loudly",
            "Mary laughed from a window with a camera beside a shelf loudly yesterday",
            "Mary laughed into a room with a camera beside a shelf loudly yesterday",
            (
                "Mary laughed from a window into a room with a camera beside a shelf "
                "loudly yesterday"
            ),
        ):
            directional_instrument_location_manner_query = urlencode(
                {
                    "sentence": directional_instrument_location_manner_sentence,
                    "require_coq": "1",
                }
            )
            with opener.open(
                (
                    f"{base_url}/api/analyze?"
                    f"{directional_instrument_location_manner_query}"
                ),
                timeout=5,
            ) as response:
                directional_instrument_location_manner_payload = json.load(response)
            with opener.open(
                f"{base_url}/?{directional_instrument_location_manner_query}",
                timeout=5,
            ) as response:
                directional_instrument_location_manner_page = response.read().decode(
                    "utf-8"
                )
            validate_analyze_directional_instrument_location_manner_intransitive_success(
                directional_instrument_location_manner_payload,
                directional_instrument_location_manner_page,
                directional_instrument_location_manner_sentence,
            )
        for directional_instrument_two_location_manner_sentence in (
            (
                "Mary laughed from a window with a camera beside a shelf loudly "
                "under a lamp"
            ),
            (
                "Mary laughed from a window with a camera beside a shelf loudly "
                "under a lamp yesterday"
            ),
            (
                "Mary laughed into a room with a camera beside a shelf loudly "
                "under a lamp yesterday"
            ),
            (
                "Mary laughed from a window into a room with a camera beside a shelf "
                "loudly under a lamp yesterday"
            ),
        ):
            directional_instrument_two_location_manner_query = urlencode(
                {
                    "sentence": directional_instrument_two_location_manner_sentence,
                    "require_coq": "1",
                }
            )
            with opener.open(
                (
                    f"{base_url}/api/analyze?"
                    f"{directional_instrument_two_location_manner_query}"
                ),
                timeout=5,
            ) as response:
                directional_instrument_two_location_manner_payload = json.load(
                    response
                )
            with opener.open(
                f"{base_url}/?{directional_instrument_two_location_manner_query}",
                timeout=5,
            ) as response:
                directional_instrument_two_location_manner_page = (
                    response.read().decode("utf-8")
                )
            validate_analyze_directional_instrument_two_location_manner_intransitive_success(
                directional_instrument_two_location_manner_payload,
                directional_instrument_two_location_manner_page,
                directional_instrument_two_location_manner_sentence,
            )
        for directional_instrument_location_manner_location_sequence_sentence in (
            (
                "Mary laughed from a window with a camera beside a shelf loudly "
                "under a lamp on a table"
            ),
            (
                "Mary laughed from a window with a camera beside a shelf loudly "
                "under a lamp on a table yesterday"
            ),
            (
                "Mary laughed into a room with a camera beside a shelf loudly "
                "under a lamp on a table yesterday"
            ),
            (
                "Mary laughed from a window into a room with a camera beside a shelf "
                "loudly under a lamp on a table yesterday"
            ),
            (
                "Mary laughed from a window with a camera beside a shelf loudly "
                "under a lamp on a table near a door yesterday"
            ),
        ):
            directional_instrument_location_manner_location_sequence_query = urlencode(
                {
                    "sentence": (
                        directional_instrument_location_manner_location_sequence_sentence
                    ),
                    "require_coq": "1",
                }
            )
            with opener.open(
                (
                    f"{base_url}/api/analyze?"
                    f"{directional_instrument_location_manner_location_sequence_query}"
                ),
                timeout=5,
            ) as response:
                directional_instrument_location_manner_location_sequence_payload = (
                    json.load(response)
                )
            with opener.open(
                (
                    f"{base_url}/?"
                    f"{directional_instrument_location_manner_location_sequence_query}"
                ),
                timeout=5,
            ) as response:
                directional_instrument_location_manner_location_sequence_page = (
                    response.read().decode("utf-8")
                )
            validate_analyze_directional_instrument_location_manner_location_sequence_success(
                directional_instrument_location_manner_location_sequence_payload,
                directional_instrument_location_manner_location_sequence_page,
                directional_instrument_location_manner_location_sequence_sentence,
            )
        for directional_instrument_location_manner_location_sequence_instrument_tail_sentence in (
            (
                "Mary laughed from a window with a camera beside a shelf loudly "
                "under a lamp on a table with a microphone"
            ),
            (
                "Mary laughed from a window with a camera beside a shelf loudly "
                "under a lamp on a table with a microphone yesterday"
            ),
            (
                "Mary laughed into a room with a camera beside a shelf loudly "
                "under a lamp on a table with a microphone yesterday"
            ),
            (
                "Mary laughed from a window into a room with a camera beside a shelf "
                "loudly under a lamp on a table with a microphone yesterday"
            ),
            (
                "Mary laughed from a window with a camera beside a shelf loudly "
                "under a lamp on a table near a door with a microphone yesterday"
            ),
        ):
            directional_instrument_location_manner_location_sequence_instrument_tail_query = urlencode(
                {
                    "sentence": (
                        directional_instrument_location_manner_location_sequence_instrument_tail_sentence
                    ),
                    "require_coq": "1",
                }
            )
            with opener.open(
                (
                    f"{base_url}/api/analyze?"
                    f"{directional_instrument_location_manner_location_sequence_instrument_tail_query}"
                ),
                timeout=5,
            ) as response:
                directional_instrument_location_manner_location_sequence_instrument_tail_payload = json.load(
                    response
                )
            with opener.open(
                (
                    f"{base_url}/?"
                    f"{directional_instrument_location_manner_location_sequence_instrument_tail_query}"
                ),
                timeout=5,
            ) as response:
                directional_instrument_location_manner_location_sequence_instrument_tail_page = response.read().decode(
                    "utf-8"
                )
            validate_analyze_directional_instrument_location_manner_location_sequence_instrument_tail_success(
                directional_instrument_location_manner_location_sequence_instrument_tail_payload,
                directional_instrument_location_manner_location_sequence_instrument_tail_page,
                directional_instrument_location_manner_location_sequence_instrument_tail_sentence,
            )
        for directional_instrument_location_manner_location_sequence_instrument_location_tail_sentence in (
            (
                "Mary laughed from a window with a camera beside a shelf loudly "
                "under a lamp on a table with a microphone near a door"
            ),
            (
                "Mary laughed from a window with a camera beside a shelf loudly "
                "under a lamp on a table with a microphone near a door yesterday"
            ),
            (
                "Mary laughed into a room with a camera beside a shelf loudly "
                "under a lamp on a table with a microphone near a door yesterday"
            ),
            (
                "Mary laughed from a window into a room with a camera beside a shelf "
                "loudly under a lamp on a table with a microphone near a door yesterday"
            ),
            (
                "Mary laughed from a window with a camera beside a shelf loudly "
                "under a lamp on a table near a door with a microphone near a window "
                "yesterday"
            ),
        ):
            directional_instrument_location_manner_location_sequence_instrument_location_tail_query = urlencode(
                {
                    "sentence": (
                        directional_instrument_location_manner_location_sequence_instrument_location_tail_sentence
                    ),
                    "require_coq": "1",
                }
            )
            with opener.open(
                (
                    f"{base_url}/api/analyze?"
                    f"{directional_instrument_location_manner_location_sequence_instrument_location_tail_query}"
                ),
                timeout=5,
            ) as response:
                directional_instrument_location_manner_location_sequence_instrument_location_tail_payload = json.load(
                    response
                )
            with opener.open(
                (
                    f"{base_url}/?"
                    f"{directional_instrument_location_manner_location_sequence_instrument_location_tail_query}"
                ),
                timeout=5,
            ) as response:
                directional_instrument_location_manner_location_sequence_instrument_location_tail_page = response.read().decode(
                    "utf-8"
                )
            validate_analyze_directional_instrument_location_manner_location_sequence_instrument_location_tail_success(
                directional_instrument_location_manner_location_sequence_instrument_location_tail_payload,
                directional_instrument_location_manner_location_sequence_instrument_location_tail_page,
                directional_instrument_location_manner_location_sequence_instrument_location_tail_sentence,
            )
        for directional_instrument_location_manner_location_sequence_instrument_location_instrument_tail_sentence in (
            (
                "Mary laughed from a window with a camera beside a shelf loudly "
                "under a lamp on a table with a microphone near a door with a telescope"
            ),
            (
                "Mary laughed from a window with a camera beside a shelf loudly "
                "under a lamp on a table with a microphone near a door with a telescope "
                "yesterday"
            ),
            (
                "Mary laughed into a room with a camera beside a shelf loudly "
                "under a lamp on a table with a microphone near a door with a telescope "
                "yesterday"
            ),
            (
                "Mary laughed from a window into a room with a camera beside a shelf "
                "loudly under a lamp on a table with a microphone near a door with a "
                "telescope yesterday"
            ),
            (
                "Mary laughed from a window with a camera beside a shelf loudly "
                "under a lamp on a table near a door with a microphone near a window "
                "with a telescope yesterday"
            ),
        ):
            directional_instrument_location_manner_location_sequence_instrument_location_instrument_tail_query = urlencode(
                {
                    "sentence": (
                        directional_instrument_location_manner_location_sequence_instrument_location_instrument_tail_sentence
                    ),
                    "require_coq": "1",
                }
            )
            with opener.open(
                (
                    f"{base_url}/api/analyze?"
                    f"{directional_instrument_location_manner_location_sequence_instrument_location_instrument_tail_query}"
                ),
                timeout=5,
            ) as response:
                directional_instrument_location_manner_location_sequence_instrument_location_instrument_tail_payload = json.load(
                    response
                )
            with opener.open(
                (
                    f"{base_url}/?"
                    f"{directional_instrument_location_manner_location_sequence_instrument_location_instrument_tail_query}"
                ),
                timeout=5,
            ) as response:
                directional_instrument_location_manner_location_sequence_instrument_location_instrument_tail_page = response.read().decode(
                    "utf-8"
                )
            validate_analyze_directional_instrument_location_manner_location_sequence_instrument_location_instrument_tail_success(
                directional_instrument_location_manner_location_sequence_instrument_location_instrument_tail_payload,
                directional_instrument_location_manner_location_sequence_instrument_location_instrument_tail_page,
                directional_instrument_location_manner_location_sequence_instrument_location_instrument_tail_sentence,
            )
        for directional_instrument_location_manner_location_sequence_instrument_location_instrument_location_tail_sentence in (
            (
                "Mary laughed from a window with a camera beside a shelf loudly "
                "under a lamp on a table with a microphone near a door with a telescope near a window"
            ),
            (
                "Mary laughed from a window with a camera beside a shelf loudly "
                "under a lamp on a table with a microphone near a door with a telescope "
                "near a window yesterday"
            ),
            (
                "Mary laughed into a room with a camera beside a shelf loudly "
                "under a lamp on a table with a microphone near a door with a telescope "
                "near a window yesterday"
            ),
            (
                "Mary laughed from a window into a room with a camera beside a shelf "
                "loudly under a lamp on a table with a microphone near a door with a "
                "telescope near a window yesterday"
            ),
            (
                "Mary laughed from a window with a camera beside a shelf loudly "
                "under a lamp on a table with a microphone near a door with a telescope "
                "near a window in the park yesterday"
            ),
        ):
            directional_instrument_location_manner_location_sequence_instrument_location_instrument_location_tail_query = urlencode(
                {
                    "sentence": (
                        directional_instrument_location_manner_location_sequence_instrument_location_instrument_location_tail_sentence
                    ),
                    "require_coq": "1",
                }
            )
            with opener.open(
                (
                    f"{base_url}/api/analyze?"
                    f"{directional_instrument_location_manner_location_sequence_instrument_location_instrument_location_tail_query}"
                ),
                timeout=5,
            ) as response:
                directional_instrument_location_manner_location_sequence_instrument_location_instrument_location_tail_payload = json.load(
                    response
                )
            with opener.open(
                (
                    f"{base_url}/?"
                    f"{directional_instrument_location_manner_location_sequence_instrument_location_instrument_location_tail_query}"
                ),
                timeout=5,
            ) as response:
                directional_instrument_location_manner_location_sequence_instrument_location_instrument_location_tail_page = response.read().decode(
                    "utf-8"
                )
            validate_analyze_directional_instrument_location_manner_location_sequence_instrument_location_instrument_location_tail_success(
                directional_instrument_location_manner_location_sequence_instrument_location_instrument_location_tail_payload,
                directional_instrument_location_manner_location_sequence_instrument_location_instrument_location_tail_page,
                directional_instrument_location_manner_location_sequence_instrument_location_instrument_location_tail_sentence,
            )
        manner_instrument_sentence = "Mary laughed loudly with a telescope"
        manner_instrument_query = urlencode(
            {"sentence": manner_instrument_sentence, "require_coq": "1"}
        )
        with opener.open(
            f"{base_url}/api/analyze?{manner_instrument_query}",
            timeout=5,
        ) as response:
            manner_instrument_payload = json.load(response)
        with opener.open(
            f"{base_url}/?{manner_instrument_query}",
            timeout=5,
        ) as response:
            manner_instrument_page = response.read().decode("utf-8")
        validate_analyze_manner_instrument_intransitive_success(
            manner_instrument_payload,
            manner_instrument_page,
            manner_instrument_sentence,
        )
        timed_manner_instrument_sentence = (
            "Mary laughed loudly with a telescope yesterday"
        )
        timed_manner_instrument_query = urlencode(
            {"sentence": timed_manner_instrument_sentence, "require_coq": "1"}
        )
        with opener.open(
            f"{base_url}/api/analyze?{timed_manner_instrument_query}",
            timeout=5,
        ) as response:
            timed_manner_instrument_payload = json.load(response)
        with opener.open(
            f"{base_url}/?{timed_manner_instrument_query}",
            timeout=5,
        ) as response:
            timed_manner_instrument_page = response.read().decode("utf-8")
        validate_analyze_manner_instrument_intransitive_success(
            timed_manner_instrument_payload,
            timed_manner_instrument_page,
            timed_manner_instrument_sentence,
        )
        manner_locative_sentence = "Mary laughed loudly in the park"
        manner_locative_query = urlencode(
            {"sentence": manner_locative_sentence, "require_coq": "1"}
        )
        with opener.open(
            f"{base_url}/api/analyze?{manner_locative_query}",
            timeout=5,
        ) as response:
            manner_locative_payload = json.load(response)
        with opener.open(
            f"{base_url}/?{manner_locative_query}",
            timeout=5,
        ) as response:
            manner_locative_page = response.read().decode("utf-8")
        validate_analyze_manner_locative_intransitive_success(
            manner_locative_payload,
            manner_locative_page,
            manner_locative_sentence,
        )
        timed_manner_locative_sentence = "Mary laughed loudly in the park yesterday"
        timed_manner_locative_query = urlencode(
            {"sentence": timed_manner_locative_sentence, "require_coq": "1"}
        )
        with opener.open(
            f"{base_url}/api/analyze?{timed_manner_locative_query}",
            timeout=5,
        ) as response:
            timed_manner_locative_payload = json.load(response)
        with opener.open(
            f"{base_url}/?{timed_manner_locative_query}",
            timeout=5,
        ) as response:
            timed_manner_locative_page = response.read().decode("utf-8")
        validate_analyze_manner_locative_intransitive_success(
            timed_manner_locative_payload,
            timed_manner_locative_page,
            timed_manner_locative_sentence,
        )
        manner_two_location_sentence = "Mary laughed loudly in the park near a window"
        manner_two_location_query = urlencode(
            {"sentence": manner_two_location_sentence, "require_coq": "1"}
        )
        with opener.open(
            f"{base_url}/api/analyze?{manner_two_location_query}",
            timeout=5,
        ) as response:
            manner_two_location_payload = json.load(response)
        with opener.open(
            f"{base_url}/?{manner_two_location_query}",
            timeout=5,
        ) as response:
            manner_two_location_page = response.read().decode("utf-8")
        validate_analyze_manner_two_location_intransitive_success(
            manner_two_location_payload,
            manner_two_location_page,
            manner_two_location_sentence,
        )
        timed_manner_two_location_sentence = (
            "Mary laughed loudly in the park near a window yesterday"
        )
        timed_manner_two_location_query = urlencode(
            {"sentence": timed_manner_two_location_sentence, "require_coq": "1"}
        )
        with opener.open(
            f"{base_url}/api/analyze?{timed_manner_two_location_query}",
            timeout=5,
        ) as response:
            timed_manner_two_location_payload = json.load(response)
        with opener.open(
            f"{base_url}/?{timed_manner_two_location_query}",
            timeout=5,
        ) as response:
            timed_manner_two_location_page = response.read().decode("utf-8")
        validate_analyze_manner_two_location_intransitive_success(
            timed_manner_two_location_payload,
            timed_manner_two_location_page,
            timed_manner_two_location_sentence,
        )
        manner_three_location_sentence = (
            "Mary laughed loudly in the park near a window beside a shelf"
        )
        manner_three_location_query = urlencode(
            {"sentence": manner_three_location_sentence, "require_coq": "1"}
        )
        with opener.open(
            f"{base_url}/api/analyze?{manner_three_location_query}",
            timeout=5,
        ) as response:
            manner_three_location_payload = json.load(response)
        with opener.open(
            f"{base_url}/?{manner_three_location_query}",
            timeout=5,
        ) as response:
            manner_three_location_page = response.read().decode("utf-8")
        validate_analyze_manner_three_location_intransitive_success(
            manner_three_location_payload,
            manner_three_location_page,
            manner_three_location_sentence,
        )
        timed_manner_three_location_sentence = (
            "Mary laughed loudly in the park near a window beside a shelf yesterday"
        )
        timed_manner_three_location_query = urlencode(
            {"sentence": timed_manner_three_location_sentence, "require_coq": "1"}
        )
        with opener.open(
            f"{base_url}/api/analyze?{timed_manner_three_location_query}",
            timeout=5,
        ) as response:
            timed_manner_three_location_payload = json.load(response)
        with opener.open(
            f"{base_url}/?{timed_manner_three_location_query}",
            timeout=5,
        ) as response:
            timed_manner_three_location_page = response.read().decode("utf-8")
        validate_analyze_manner_three_location_intransitive_success(
            timed_manner_three_location_payload,
            timed_manner_three_location_page,
            timed_manner_three_location_sentence,
        )
        manner_location_sequence_sentence = (
            "Mary laughed loudly in the park near a window beside a shelf under a lamp"
        )
        manner_location_sequence_query = urlencode(
            {"sentence": manner_location_sequence_sentence, "require_coq": "1"}
        )
        with opener.open(
            f"{base_url}/api/analyze?{manner_location_sequence_query}",
            timeout=5,
        ) as response:
            manner_location_sequence_payload = json.load(response)
        with opener.open(
            f"{base_url}/?{manner_location_sequence_query}",
            timeout=5,
        ) as response:
            manner_location_sequence_page = response.read().decode("utf-8")
        validate_analyze_manner_location_sequence_intransitive_success(
            manner_location_sequence_payload,
            manner_location_sequence_page,
            manner_location_sequence_sentence,
        )
        timed_manner_location_sequence_sentence = (
            "Mary laughed loudly in the park near a window beside a shelf under a "
            "lamp yesterday"
        )
        timed_manner_location_sequence_query = urlencode(
            {"sentence": timed_manner_location_sequence_sentence, "require_coq": "1"}
        )
        with opener.open(
            f"{base_url}/api/analyze?{timed_manner_location_sequence_query}",
            timeout=5,
        ) as response:
            timed_manner_location_sequence_payload = json.load(response)
        with opener.open(
            f"{base_url}/?{timed_manner_location_sequence_query}",
            timeout=5,
        ) as response:
            timed_manner_location_sequence_page = response.read().decode("utf-8")
        validate_analyze_manner_location_sequence_intransitive_success(
            timed_manner_location_sequence_payload,
            timed_manner_location_sequence_page,
            timed_manner_location_sequence_sentence,
        )
        extended_manner_location_sequence_sentence = (
            "Mary laughed loudly in the park near a window beside a shelf under a "
            "lamp on a table yesterday"
        )
        extended_manner_location_sequence_query = urlencode(
            {
                "sentence": extended_manner_location_sequence_sentence,
                "require_coq": "1",
            }
        )
        with opener.open(
            f"{base_url}/api/analyze?{extended_manner_location_sequence_query}",
            timeout=5,
        ) as response:
            extended_manner_location_sequence_payload = json.load(response)
        with opener.open(
            f"{base_url}/?{extended_manner_location_sequence_query}",
            timeout=5,
        ) as response:
            extended_manner_location_sequence_page = response.read().decode("utf-8")
        validate_analyze_manner_location_sequence_intransitive_success(
            extended_manner_location_sequence_payload,
            extended_manner_location_sequence_page,
            extended_manner_location_sequence_sentence,
        )
        manner_location_instrument_sentence = (
            "Mary laughed loudly in the park with a telescope"
        )
        manner_location_instrument_query = urlencode(
            {"sentence": manner_location_instrument_sentence, "require_coq": "1"}
        )
        with opener.open(
            f"{base_url}/api/analyze?{manner_location_instrument_query}",
            timeout=5,
        ) as response:
            manner_location_instrument_payload = json.load(response)
        with opener.open(
            f"{base_url}/?{manner_location_instrument_query}",
            timeout=5,
        ) as response:
            manner_location_instrument_page = response.read().decode("utf-8")
        validate_analyze_manner_location_instrument_intransitive_success(
            manner_location_instrument_payload,
            manner_location_instrument_page,
            manner_location_instrument_sentence,
        )
        timed_manner_location_instrument_sentence = (
            "Mary laughed loudly in the park with a telescope yesterday"
        )
        timed_manner_location_instrument_query = urlencode(
            {
                "sentence": timed_manner_location_instrument_sentence,
                "require_coq": "1",
            }
        )
        with opener.open(
            f"{base_url}/api/analyze?{timed_manner_location_instrument_query}",
            timeout=5,
        ) as response:
            timed_manner_location_instrument_payload = json.load(response)
        with opener.open(
            f"{base_url}/?{timed_manner_location_instrument_query}",
            timeout=5,
        ) as response:
            timed_manner_location_instrument_page = response.read().decode("utf-8")
        validate_analyze_manner_location_instrument_intransitive_success(
            timed_manner_location_instrument_payload,
            timed_manner_location_instrument_page,
            timed_manner_location_instrument_sentence,
        )
        extended_manner_location_instrument_sentence = (
            "Mary laughed loudly in the park near a window beside a shelf under a "
            "lamp with a telescope yesterday"
        )
        extended_manner_location_instrument_query = urlencode(
            {
                "sentence": extended_manner_location_instrument_sentence,
                "require_coq": "1",
            }
        )
        with opener.open(
            f"{base_url}/api/analyze?{extended_manner_location_instrument_query}",
            timeout=5,
        ) as response:
            extended_manner_location_instrument_payload = json.load(response)
        with opener.open(
            f"{base_url}/?{extended_manner_location_instrument_query}",
            timeout=5,
        ) as response:
            extended_manner_location_instrument_page = response.read().decode("utf-8")
        validate_analyze_manner_location_instrument_intransitive_success(
            extended_manner_location_instrument_payload,
            extended_manner_location_instrument_page,
            extended_manner_location_instrument_sentence,
        )
        repeated_instrument_sentence = (
            "Mary laughed loudly in the park near a window beside a shelf under a "
            "lamp with a telescope with a camera yesterday"
        )
        repeated_instrument_query = urlencode(
            {
                "sentence": repeated_instrument_sentence,
                "require_coq": "1",
            }
        )
        with opener.open(
            f"{base_url}/api/analyze?{repeated_instrument_query}",
            timeout=5,
        ) as response:
            repeated_instrument_payload = json.load(response)
        with opener.open(
            f"{base_url}/?{repeated_instrument_query}",
            timeout=5,
        ) as response:
            repeated_instrument_page = response.read().decode("utf-8")
        validate_analyze_manner_location_instrument_intransitive_success(
            repeated_instrument_payload,
            repeated_instrument_page,
            repeated_instrument_sentence,
        )
        mixed_location_instrument_sentence = (
            "Mary laughed loudly in the park with a telescope near a window "
            "with a camera"
        )
        mixed_location_instrument_query = urlencode(
            {
                "sentence": mixed_location_instrument_sentence,
                "require_coq": "1",
            }
        )
        with opener.open(
            f"{base_url}/api/analyze?{mixed_location_instrument_query}",
            timeout=5,
        ) as response:
            mixed_location_instrument_payload = json.load(response)
        with opener.open(
            f"{base_url}/?{mixed_location_instrument_query}",
            timeout=5,
        ) as response:
            mixed_location_instrument_page = response.read().decode("utf-8")
        validate_analyze_manner_mixed_location_instrument_intransitive_success(
            mixed_location_instrument_payload,
            mixed_location_instrument_page,
            mixed_location_instrument_sentence,
        )
        timed_mixed_location_instrument_sentence = (
            "Mary laughed loudly in the park with a telescope near a window "
            "with a camera yesterday"
        )
        timed_mixed_location_instrument_query = urlencode(
            {
                "sentence": timed_mixed_location_instrument_sentence,
                "require_coq": "1",
            }
        )
        with opener.open(
            f"{base_url}/api/analyze?{timed_mixed_location_instrument_query}",
            timeout=5,
        ) as response:
            timed_mixed_location_instrument_payload = json.load(response)
        with opener.open(
            f"{base_url}/?{timed_mixed_location_instrument_query}",
            timeout=5,
        ) as response:
            timed_mixed_location_instrument_page = response.read().decode("utf-8")
        validate_analyze_manner_mixed_location_instrument_intransitive_success(
            timed_mixed_location_instrument_payload,
            timed_mixed_location_instrument_page,
            timed_mixed_location_instrument_sentence,
        )
        extended_mixed_location_instrument_sentence = (
            "Mary laughed loudly in the park with a telescope near a window "
            "beside a shelf with a camera yesterday"
        )
        extended_mixed_location_instrument_query = urlencode(
            {
                "sentence": extended_mixed_location_instrument_sentence,
                "require_coq": "1",
            }
        )
        with opener.open(
            f"{base_url}/api/analyze?{extended_mixed_location_instrument_query}",
            timeout=5,
        ) as response:
            extended_mixed_location_instrument_payload = json.load(response)
        with opener.open(
            f"{base_url}/?{extended_mixed_location_instrument_query}",
            timeout=5,
        ) as response:
            extended_mixed_location_instrument_page = response.read().decode("utf-8")
        validate_analyze_manner_mixed_location_instrument_intransitive_success(
            extended_mixed_location_instrument_payload,
            extended_mixed_location_instrument_page,
            extended_mixed_location_instrument_sentence,
        )
        mixed_directional_source_sentence = (
            "Mary laughed loudly in the park with a telescope from a window "
            "with a camera yesterday"
        )
        mixed_directional_source_query = urlencode(
            {
                "sentence": mixed_directional_source_sentence,
                "require_coq": "1",
            }
        )
        with opener.open(
            f"{base_url}/api/analyze?{mixed_directional_source_query}",
            timeout=5,
        ) as response:
            mixed_directional_source_payload = json.load(response)
        with opener.open(
            f"{base_url}/?{mixed_directional_source_query}",
            timeout=5,
        ) as response:
            mixed_directional_source_page = response.read().decode("utf-8")
        validate_analyze_manner_mixed_directional_instrument_intransitive_success(
            mixed_directional_source_payload,
            mixed_directional_source_page,
            mixed_directional_source_sentence,
        )
        mixed_directional_goal_sentence = (
            "Mary laughed loudly in the park with a telescope into a room "
            "with a camera yesterday"
        )
        mixed_directional_goal_query = urlencode(
            {
                "sentence": mixed_directional_goal_sentence,
                "require_coq": "1",
            }
        )
        with opener.open(
            f"{base_url}/api/analyze?{mixed_directional_goal_query}",
            timeout=5,
        ) as response:
            mixed_directional_goal_payload = json.load(response)
        with opener.open(
            f"{base_url}/?{mixed_directional_goal_query}",
            timeout=5,
        ) as response:
            mixed_directional_goal_page = response.read().decode("utf-8")
        validate_analyze_manner_mixed_directional_instrument_intransitive_success(
            mixed_directional_goal_payload,
            mixed_directional_goal_page,
            mixed_directional_goal_sentence,
        )
        locative_sentence = "a cat sits on a mat"
        locative_query = urlencode({"sentence": locative_sentence, "require_coq": "1"})
        with opener.open(f"{base_url}/api/analyze?{locative_query}", timeout=5) as response:
            locative_payload = json.load(response)
        with opener.open(f"{base_url}/?{locative_query}", timeout=5) as response:
            locative_page = response.read().decode("utf-8")
        validate_analyze_locative_intransitive_success(
            locative_payload,
            locative_page,
            locative_sentence,
        )
        timed_locative_sentence = "Mary laughed near a window yesterday"
        timed_locative_query = urlencode(
            {"sentence": timed_locative_sentence, "require_coq": "1"}
        )
        with opener.open(
            f"{base_url}/api/analyze?{timed_locative_query}",
            timeout=5,
        ) as response:
            timed_locative_payload = json.load(response)
        with opener.open(
            f"{base_url}/?{timed_locative_query}",
            timeout=5,
        ) as response:
            timed_locative_page = response.read().decode("utf-8")
        validate_analyze_locative_intransitive_success(
            timed_locative_payload,
            timed_locative_page,
            timed_locative_sentence,
        )
        plain_transitive_sentence = "Mary admired the painting"
        plain_transitive_query = urlencode(
            {"sentence": plain_transitive_sentence, "require_coq": "1"}
        )
        with opener.open(f"{base_url}/api/analyze?{plain_transitive_query}", timeout=5) as response:
            plain_transitive_payload = json.load(response)
        with opener.open(f"{base_url}/?{plain_transitive_query}", timeout=5) as response:
            plain_transitive_page = response.read().decode("utf-8")
        validate_analyze_plain_transitive_success(
            plain_transitive_payload,
            plain_transitive_page,
            plain_transitive_sentence,
        )
        timed_plain_transitive_sentence = "Mary admired the painting yesterday"
        timed_plain_transitive_query = urlencode(
            {"sentence": timed_plain_transitive_sentence, "require_coq": "1"}
        )
        with opener.open(
            f"{base_url}/api/analyze?{timed_plain_transitive_query}",
            timeout=5,
        ) as response:
            timed_plain_transitive_payload = json.load(response)
        with opener.open(
            f"{base_url}/?{timed_plain_transitive_query}",
            timeout=5,
        ) as response:
            timed_plain_transitive_page = response.read().decode("utf-8")
        validate_analyze_plain_transitive_success(
            timed_plain_transitive_payload,
            timed_plain_transitive_page,
            timed_plain_transitive_sentence,
        )
        modified_transitive_sentence = "Mary admired the painting in the gallery"
        modified_transitive_query = urlencode(
            {"sentence": modified_transitive_sentence, "require_coq": "1"}
        )
        with opener.open(
            f"{base_url}/api/analyze?{modified_transitive_query}",
            timeout=5,
        ) as response:
            modified_transitive_payload = json.load(response)
        with opener.open(
            f"{base_url}/?{modified_transitive_query}",
            timeout=5,
        ) as response:
            modified_transitive_page = response.read().decode("utf-8")
        validate_analyze_modified_transitive_success(
            modified_transitive_payload,
            modified_transitive_page,
            modified_transitive_sentence,
        )
        timed_modified_transitive_sentence = "Mary admired the painting in the gallery yesterday"
        timed_modified_transitive_query = urlencode(
            {"sentence": timed_modified_transitive_sentence, "require_coq": "1"}
        )
        with opener.open(
            f"{base_url}/api/analyze?{timed_modified_transitive_query}",
            timeout=5,
        ) as response:
            timed_modified_transitive_payload = json.load(response)
        with opener.open(
            f"{base_url}/?{timed_modified_transitive_query}",
            timeout=5,
        ) as response:
            timed_modified_transitive_page = response.read().decode("utf-8")
        validate_analyze_modified_transitive_success(
            timed_modified_transitive_payload,
            timed_modified_transitive_page,
            timed_modified_transitive_sentence,
        )
        multi_modified_transitive_sentence = (
            "Mary admired the painting in the gallery with a telescope"
        )
        multi_modified_transitive_query = urlencode(
            {"sentence": multi_modified_transitive_sentence, "require_coq": "1"}
        )
        with opener.open(
            f"{base_url}/api/analyze?{multi_modified_transitive_query}",
            timeout=5,
        ) as response:
            multi_modified_transitive_payload = json.load(response)
        with opener.open(
            f"{base_url}/?{multi_modified_transitive_query}",
            timeout=5,
        ) as response:
            multi_modified_transitive_page = response.read().decode("utf-8")
        validate_analyze_modified_transitive_success(
            multi_modified_transitive_payload,
            multi_modified_transitive_page,
            multi_modified_transitive_sentence,
        )
        timed_multi_modified_transitive_sentence = (
            "Mary admired the painting in the gallery with a telescope yesterday"
        )
        timed_multi_modified_transitive_query = urlencode(
            {"sentence": timed_multi_modified_transitive_sentence, "require_coq": "1"}
        )
        with opener.open(
            f"{base_url}/api/analyze?{timed_multi_modified_transitive_query}",
            timeout=5,
        ) as response:
            timed_multi_modified_transitive_payload = json.load(response)
        with opener.open(
            f"{base_url}/?{timed_multi_modified_transitive_query}",
            timeout=5,
        ) as response:
            timed_multi_modified_transitive_page = response.read().decode("utf-8")
        validate_analyze_modified_transitive_success(
            timed_multi_modified_transitive_payload,
            timed_multi_modified_transitive_page,
            timed_multi_modified_transitive_sentence,
        )
        triple_modified_transitive_sentence = (
            "Mary admired the painting in the gallery with a telescope near a window"
        )
        triple_modified_transitive_query = urlencode(
            {"sentence": triple_modified_transitive_sentence, "require_coq": "1"}
        )
        with opener.open(
            f"{base_url}/api/analyze?{triple_modified_transitive_query}",
            timeout=5,
        ) as response:
            triple_modified_transitive_payload = json.load(response)
        with opener.open(
            f"{base_url}/?{triple_modified_transitive_query}",
            timeout=5,
        ) as response:
            triple_modified_transitive_page = response.read().decode("utf-8")
        validate_analyze_modified_transitive_success(
            triple_modified_transitive_payload,
            triple_modified_transitive_page,
            triple_modified_transitive_sentence,
        )
        timed_triple_modified_transitive_sentence = (
            "Mary admired the painting in the gallery with a telescope near a window yesterday"
        )
        timed_triple_modified_transitive_query = urlencode(
            {"sentence": timed_triple_modified_transitive_sentence, "require_coq": "1"}
        )
        with opener.open(
            f"{base_url}/api/analyze?{timed_triple_modified_transitive_query}",
            timeout=5,
        ) as response:
            timed_triple_modified_transitive_payload = json.load(response)
        with opener.open(
            f"{base_url}/?{timed_triple_modified_transitive_query}",
            timeout=5,
        ) as response:
            timed_triple_modified_transitive_page = response.read().decode("utf-8")
        validate_analyze_modified_transitive_success(
            timed_triple_modified_transitive_payload,
            timed_triple_modified_transitive_page,
            timed_triple_modified_transitive_sentence,
        )
        quad_modified_transitive_sentence = (
            "Mary admired the painting in the gallery with a telescope near a window beside a shelf"
        )
        quad_modified_transitive_query = urlencode(
            {"sentence": quad_modified_transitive_sentence, "require_coq": "1"}
        )
        with opener.open(
            f"{base_url}/api/analyze?{quad_modified_transitive_query}",
            timeout=5,
        ) as response:
            quad_modified_transitive_payload = json.load(response)
        with opener.open(
            f"{base_url}/?{quad_modified_transitive_query}",
            timeout=5,
        ) as response:
            quad_modified_transitive_page = response.read().decode("utf-8")
        validate_analyze_modified_transitive_success(
            quad_modified_transitive_payload,
            quad_modified_transitive_page,
            quad_modified_transitive_sentence,
        )
        timed_quad_modified_transitive_sentence = (
            "Mary admired the painting in the gallery with a telescope near a window beside a shelf yesterday"
        )
        timed_quad_modified_transitive_query = urlencode(
            {"sentence": timed_quad_modified_transitive_sentence, "require_coq": "1"}
        )
        with opener.open(
            f"{base_url}/api/analyze?{timed_quad_modified_transitive_query}",
            timeout=5,
        ) as response:
            timed_quad_modified_transitive_payload = json.load(response)
        with opener.open(
            f"{base_url}/?{timed_quad_modified_transitive_query}",
            timeout=5,
        ) as response:
            timed_quad_modified_transitive_page = response.read().decode("utf-8")
        validate_analyze_modified_transitive_success(
            timed_quad_modified_transitive_payload,
            timed_quad_modified_transitive_page,
            timed_quad_modified_transitive_sentence,
        )
        quint_modified_transitive_sentence = (
            "Mary admired the painting in the gallery with a telescope near a window beside a shelf under a lamp"
        )
        quint_modified_transitive_query = urlencode(
            {"sentence": quint_modified_transitive_sentence, "require_coq": "1"}
        )
        with opener.open(
            f"{base_url}/api/analyze?{quint_modified_transitive_query}",
            timeout=5,
        ) as response:
            quint_modified_transitive_payload = json.load(response)
        with opener.open(
            f"{base_url}/?{quint_modified_transitive_query}",
            timeout=5,
        ) as response:
            quint_modified_transitive_page = response.read().decode("utf-8")
        validate_analyze_modified_transitive_success(
            quint_modified_transitive_payload,
            quint_modified_transitive_page,
            quint_modified_transitive_sentence,
        )
        timed_quint_modified_transitive_sentence = (
            "Mary admired the painting in the gallery with a telescope near a window beside a shelf under a lamp yesterday"
        )
        timed_quint_modified_transitive_query = urlencode(
            {"sentence": timed_quint_modified_transitive_sentence, "require_coq": "1"}
        )
        with opener.open(
            f"{base_url}/api/analyze?{timed_quint_modified_transitive_query}",
            timeout=5,
        ) as response:
            timed_quint_modified_transitive_payload = json.load(response)
        with opener.open(
            f"{base_url}/?{timed_quint_modified_transitive_query}",
            timeout=5,
        ) as response:
            timed_quint_modified_transitive_page = response.read().decode("utf-8")
        validate_analyze_modified_transitive_success(
            timed_quint_modified_transitive_payload,
            timed_quint_modified_transitive_page,
            timed_quint_modified_transitive_sentence,
        )
        resultative_sentence = "John hammered the metal flat"
        resultative_query = urlencode(
            {"sentence": resultative_sentence, "require_coq": "1"}
        )
        with opener.open(f"{base_url}/api/analyze?{resultative_query}", timeout=5) as response:
            resultative_payload = json.load(response)
        with opener.open(f"{base_url}/?{resultative_query}", timeout=5) as response:
            resultative_page = response.read().decode("utf-8")
        validate_analyze_resultative_predication_success(
            resultative_payload,
            resultative_page,
            resultative_sentence,
        )
        timed_resultative_sentence = "Mary admired the painting red yesterday"
        timed_resultative_query = urlencode(
            {"sentence": timed_resultative_sentence, "require_coq": "1"}
        )
        with opener.open(
            f"{base_url}/api/analyze?{timed_resultative_query}",
            timeout=5,
        ) as response:
            timed_resultative_payload = json.load(response)
        with opener.open(
            f"{base_url}/?{timed_resultative_query}",
            timeout=5,
        ) as response:
            timed_resultative_page = response.read().decode("utf-8")
        validate_analyze_resultative_predication_success(
            timed_resultative_payload,
            timed_resultative_page,
            timed_resultative_sentence,
        )
        fallback_sentence = "Mary laughed from a window with a camera beside a shelf loudly under a lamp on a table with a microphone near a door with a telescope near a window with a knife yesterday"
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
        with opener.open(
            f"{base_url}/api/construction-rule-draft?{fallback_query}",
            timeout=5,
        ) as response:
            draft_payload = json.load(response)
        validate_construction_rule_draft_export(
            "fallback",
            fallback_payload,
            fallback_page,
            draft_payload,
            fallback_sentence,
            True,
        )
        draft_download_query = urlencode(
            {
                "sentence": fallback_sentence,
                "require_coq": "1",
                "download": "1",
            }
        )
        with opener.open(
            f"{base_url}/api/construction-rule-draft?{draft_download_query}",
            timeout=5,
        ) as response:
            disposition = response.headers.get("Content-Disposition", "")
            filename = construction_rule_draft_artifact_filename(
                str(fallback_payload["construction_rule_draft"]["candidate_rule_id"])
            )
            if filename not in disposition:
                raise SystemExit("web route smoke check failed: rule draft download drift")
            draft_download_payload = json.load(response)
        if draft_download_payload != draft_payload:
            raise SystemExit("web route smoke check failed: rule draft download payload drift")
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
        ordinary_failure_matrix = (
            ("ordinary input failure", "  ", "input", "edit_input", False, "unverified_failure", "none", None),
            ("ordinary parsing failure", "John", "parsing", "revise_sentence", False, "unverified_failure", "none", None),
            (
                "ordinary unsupported-fragment failure",
                "if John left, Mary cried because Sue left",
                "parsing",
                "revise_sentence",
                False,
                "rejected_unsupported_fragment",
                "none",
                None,
            ),
            (
                "ordinary semantic-reading type-check failure",
                "Mary admired the door because it was closed and open",
                "semantic_readings_check",
                "fix_reading_type_checks",
                False,
                "registered_construction",
                "construction_rule",
                "causal_because",
            ),
            (
                "ordinary type-check failure",
                "the plant killed",
                "type_check",
                "inspect_ast",
                True,
                "registered_construction",
                "construction_rule",
                "lexical_state_change",
            ),
        )
        for (
            failure_label,
            surface_sentence,
            expected_stage,
            expected_action_kind,
            expected_can_auto_run,
            expected_scope_kind,
            expected_certification_level,
            expected_scope_rule,
        ) in ordinary_failure_matrix:
            failure_query = urlencode({"sentence": surface_sentence, "require_coq": "1"})
            with opener.open(
                f"{base_url}/api/analyze?{failure_query}",
                timeout=5,
            ) as response:
                failure_payload = json.load(response)
            with opener.open(f"{base_url}/?{failure_query}", timeout=5) as response:
                failure_page = response.read().decode("utf-8")
            normalized_sentence = str(
                failure_payload.get("input_sentence", surface_sentence)
            )
            validate_analyze_failure_surface_type_contract(
                failure_payload,
                failure_page,
                normalized_sentence,
                failure_label,
                expected_stage,
            )
            actions = failure_payload.get("diagnostics", {}).get("recovery_actions", [])
            if (
                not isinstance(actions, list)
                or not actions
                or not isinstance(actions[0], dict)
            ):
                raise SystemExit(
                    "web route smoke check failed: "
                    f"{failure_label} ordinary analyze action missing"
                )
            action = actions[0]
            analyze_action_path = action.get("api_path")
            if not isinstance(analyze_action_path, str):
                raise SystemExit(
                    "web route smoke check failed: "
                    f"{failure_label} ordinary analyze action path missing"
                )
            with opener.open(f"{base_url}{analyze_action_path}", timeout=5) as response:
                analyze_action_payload = json.load(response)
            normalized_sentence = validate_ordinary_analyze_action_export_surface(
                failure_label,
                surface_sentence,
                True,
                0,
                failure_payload,
                failure_page,
                analyze_action_payload,
                expected_failure_stage=expected_stage,
                expected_action_kind=expected_action_kind,
                expected_can_auto_run=expected_can_auto_run,
                expected_verification_scope_kind=expected_scope_kind,
                expected_certification_level=expected_certification_level,
                expected_verification_scope_rule=expected_scope_rule,
            )
            download_path = action.get("download_api_path")
            if not isinstance(download_path, str):
                raise SystemExit(
                    "web route smoke check failed: "
                    f"{failure_label} ordinary analyze action download path missing"
                )
            with opener.open(f"{base_url}{download_path}", timeout=5) as response:
                validate_json_download_http_response(
                    failure_label,
                    "analyze recovery action",
                    response,
                    analyze_action_payload,
                    analyze_action_artifact_filename(normalized_sentence, 0),
                )
            if analyze_action_payload.get("repair_plan", {}).get("can_auto_run") is True:
                analyze_run_path = action.get("inspection_run_api_path")
                if not isinstance(analyze_run_path, str):
                    raise SystemExit(
                        "web route smoke check failed: "
                        f"{failure_label} ordinary analyze run path missing"
                    )
                with opener.open(f"{base_url}{analyze_run_path}", timeout=5) as response:
                    analyze_run_payload = json.load(response)
                validate_analyze_action_inspection_run_bundle(
                    failure_label,
                    normalized_sentence,
                    0,
                    failure_payload,
                    analyze_run_payload,
                )
                run_download_path = action.get("inspection_run_download_api_path")
                if not isinstance(run_download_path, str):
                    raise SystemExit(
                        "web route smoke check failed: "
                        f"{failure_label} ordinary analyze run download path missing"
                    )
                with opener.open(f"{base_url}{run_download_path}", timeout=5) as response:
                    validate_json_download_http_response(
                        failure_label,
                        "analyze inspection run",
                        response,
                        analyze_run_payload,
                        analyze_action_run_artifact_filename(normalized_sentence, 0),
                    )
            else:
                rejection_path = analyze_action_run_api_path(
                    normalized_sentence,
                    0,
                    require_coq=True,
                )
                try:
                    opener.open(f"{base_url}{rejection_path}", timeout=5)
                except HTTPError as exc:
                    if exc.code != 400:
                        raise
                    rejection_payload = json.loads(exc.read().decode("utf-8"))
                else:
                    raise SystemExit(
                        "web route smoke check failed: "
                        f"{failure_label} unsafe ordinary analyze run accepted"
                    )
                validate_analyze_action_inspection_run_rejection(
                    failure_label,
                    normalized_sentence,
                    0,
                    failure_payload,
                    rejection_payload,
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
