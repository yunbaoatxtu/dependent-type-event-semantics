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
            "/api/construction-rule-draft?sentence=Mary+smiled+yesterday&amp;"
            "require_coq=1&amp;download=1"
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
    if payload.get("dependent_type_translation") != "sit(1)(on(mat), cat)":
        raise SystemExit("web route smoke check failed: locative translation drift")
    ast = payload.get("ast")
    modifier_roles = (
        ast.get("modifier_roles", {}).get("roles")
        if isinstance(ast, dict)
        else None
    )
    if (
        not isinstance(ast, dict)
        or ast.get("kind") != "application"
        or ast.get("function") != "sit"
        or ast.get("arguments") != ["cat"]
        or not isinstance(modifier_roles, list)
        or len(modifier_roles) != 1
        or modifier_roles[0].get("type") != "Adv"
        or modifier_roles[0].get("semantic_role") != "Location"
    ):
        raise SystemExit("web route smoke check failed: locative AST drift")
    if "certification_upgrade_plan" in payload or "construction_rule_draft" in payload:
        raise SystemExit("web route smoke check failed: registered locative exposes fallback draft")
    if payload.get("event_semantics", {}).get("analysis") != "locative-intransitive-predication":
        raise SystemExit("web route smoke check failed: locative analysis drift")
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
        or "Parameter on_mat : Adv." not in coq_code
        or "Parameter on_mat : Entity." in coq_code
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
        "sit(1)(on(mat), cat)",
        "Parameter on_mat : Adv.",
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
        ast_structure_summary,
        construction_rules,
        exported_prop_definition_names,
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
        dependent_type_translation = str(result.get("dependent_type_translation", ""))
        for fragment in expected_fragments:
            if fragment not in dependent_type_translation:
                raise SystemExit(
                    "web route smoke check failed: certified rule "
                    f"{rule_id} variant translation drift"
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
        'data-surface-parser-family="modified_transitive_adv_sequence"',
        'data-surface-type-level-open-ended="true"',
        'data-surface-parser-claim="registered_examples_only"',
        'data-surface-full-certification="false"',
        'data-surface-verified-counts="1,2,3,4,5"',
        'data-surface-timed-counts="1,2,3,4,5"',
        'data-surface-untimed-counts="1,2,3,4,5"',
        'data-surface-max-verified-count="5"',
        'data-surface-verified-example-count="10"',
        'data-surface-generator-schema="surface_witness_generation.v1"',
        'data-surface-generator-kind="modifier_prefix_with_optional_time_suffix"',
        'data-surface-generator-modifier-count="5"',
        'data-surface-generator-time-suffix="yesterday"',
        'data-surface-slot-probe-schema="surface_slot_probes.v1"',
        'data-surface-slot-probe-count="4"',
        'data-surface-slot-probe-generation-schema="surface_slot_probe_generation.v1"',
        'data-surface-slot-probe-generation-kind="lexical_slot_substitution_with_modifier_prefix"',
        'data-surface-slot-probe-matrix-count="16"',
        'data-surface-slot-probe-matrix-generation-schema="surface_slot_probe_matrix_generation.v1"',
        'data-surface-slot-probe-matrix-generation-kind="cartesian_lexical_frame_with_modifier_profiles"',
        'data-surface-slot-probe-matrix-type-contract-schema="surface_type_contract_registry.v1"',
        'data-surface-slot-probe-matrix-type-contract-entry-schema="surface_type_contract_entry.v1"',
        'data-surface-slot-probe-matrix-type-contract-entry-count="6"',
        (
            'data-surface-slot-probe-matrix-type-contract-diagnostic-schema="'
            'surface_type_contract_diagnostic.v1"'
        ),
        'data-surface-slot-probe-matrix-type-contract-diagnostic-count="5"',
        (
            'data-surface-slot-probe-matrix-type-contract-diagnostic-categories="'
            'registry_schema,entry_axis_sync,role_frame,modifier_type,time_type"'
        ),
        (
            'data-surface-slot-probe-matrix-type-contract-source="'
            'translator/surface_type_contracts.py"'
        ),
        (
            'data-surface-slot-probe-matrix-type-contract-registry-id="'
            'modified_transitive_adv_sequence.surface_slot_matrix"'
        ),
        'data-surface-slot-probe-id="subject_slot_john"',
        'data-surface-slot-probe-slot="agent"',
        'data-surface-slot-probe-sentence="John admired the painting in the gallery"',
        'data-surface-slot-probe-id="theme_slot_sculpture"',
        'data-surface-slot-probe-slot="theme"',
        'data-surface-slot-probe-sentence="Mary admired the sculpture in the gallery"',
        'data-surface-slot-probe-id="predicate_slot_photograph"',
        'data-surface-slot-probe-slot="predicate"',
        'data-surface-slot-probe-id="combined_slots_timed_max_prefix"',
        'data-surface-slot-probe-slot="agent_predicate_theme"',
        'data-surface-slot-probe-modifier-count="5"',
        'data-surface-slot-probe-time-wrapped="true"',
        (
            'data-surface-slot-matrix-id="'
            'agent_mary__predicate_admire__theme_painting__profile_one_adv_untimed"'
        ),
        'data-surface-slot-matrix-profile="max_prefix_timed"',
        'data-surface-slot-matrix-agent="john"',
        'data-surface-slot-matrix-agent-type="Entity"',
        'data-surface-slot-matrix-predicate="photograph"',
        (
            'data-surface-slot-matrix-predicate-type="forall n : nat, '
            'ModifierSeq n -&gt; Entity -&gt; Entity -&gt; PropT"'
        ),
        'data-surface-slot-matrix-theme="sculpture"',
        'data-surface-slot-matrix-theme-type="Entity"',
        'data-surface-slot-matrix-modifier-type="Adv"',
        'data-surface-slot-matrix-time-type="Time"',
        'data-surface-slot-matrix-modifier-count="5"',
        'data-surface-slot-matrix-time-wrapped="true"',
        'data-surface-example-variant-id="primary_modified_transitive_predication"',
        'data-surface-example-sentence="Mary admired the painting in the gallery"',
        'data-surface-example-source="registered_primary_example"',
        'data-surface-example-variant-id="temporal_quint_adv_modified_transitive_predication"',
        (
            'data-surface-example-sentence="Mary admired the painting in the gallery '
            'with a telescope near a window beside a shelf under a lamp yesterday"'
        ),
        'data-surface-example-modifier-count="5"',
        'data-surface-example-time-wrapped="true"',
        'data-surface-example-source="registered_variant_example"',
        'data-surface-example-analysis="modified-transitive-predication"',
        'data-surface-example-ast-kind="application"',
        'data-surface-example-ast-kind="time"',
        'data-surface-example-fragment-count="1"',
        "surface parser coverage",
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
            f'data-coverage-variant-id="{html.escape(str(item.get("variant_id", "")), quote=True)}"'
            for item in coverage.get("registered_variant_success_cases", [])
            if isinstance(item, dict)
        )
        expected_fragments.extend(
            f'data-coverage-rule-id="{html.escape(str(item.get("rule_id", "")), quote=True)}"'
            for item in coverage.get("registered_variant_success_cases", [])
            if isinstance(item, dict)
        )
        expected_fragments.extend(
            f'data-coverage-marker="{html.escape(str(item.get("marker", "")), quote=True)}"'
            for item in coverage.get("rejected_unsupported_cases", [])
            if isinstance(item, dict)
        )
    snapshots = manifest.get("semantic_snapshots", [])
    if isinstance(snapshots, list):
        expected_fragments.extend(
            f'data-semantic-snapshot-rule-id="{html.escape(str(item.get("rule_id", "")), quote=True)}"'
            for item in snapshots
            if isinstance(item, dict)
        )
        expected_fragments.extend(
            f'data-semantic-snapshot-analysis="{html.escape(str(item.get("expected_event_analysis", "")), quote=True)}"'
            for item in snapshots
            if isinstance(item, dict)
        )
        expected_fragments.extend(
            'data-semantic-snapshot-ast-kind="{}"'.format(
                html.escape(
                    str((item.get("expected_ast_summary") or {}).get("kind", "")),
                    quote=True,
                )
            )
            for item in snapshots
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
        fallback_sentence = "Mary smiled yesterday"
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
