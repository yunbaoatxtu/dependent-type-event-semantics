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
    DIAGNOSTIC_RECOVERY_ACTION_KINDS,
    REQUIRED_DIAGNOSTIC_FIXTURE_STAGES,
)
PYCACHE = ROOT / ".pycache"
COQ_FILE = ROOT / "formalization" / "DependentTypeEventSemantics.v"
PACKAGE_WHEEL_DIR = ROOT / "work" / "verify_package_build"
ROCQ_ENV = Path(
    "/Applications/Rocq-Platform~9.0~2025.08.app/Contents/Resources/bin/coq-env.sh"
)
VALID_DIAGNOSTIC_FAILURE_STAGES = DIAGNOSTIC_FAILURE_STAGES
VALID_DIAGNOSTIC_RECOVERY_ACTION_KINDS = DIAGNOSTIC_RECOVERY_ACTION_KINDS
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
    if not isinstance(bundle.get("failure_stage"), str):
        raise SystemExit(f"web route smoke check failed: {case} recovery action stage drift")
    contract = bundle.get("contract")
    if not isinstance(contract, dict):
        raise SystemExit(f"web route smoke check failed: {case} recovery action contract drift")
    validate_diagnostic_contract_manifest(contract)


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
        if not all(
            isinstance(value, str)
            for value in [case, label, api_path, html_path, failure_stage]
        ):
            raise SystemExit("web route smoke check failed: incomplete fixture case metadata")
        if not isinstance(recovery_actions, list) or not all(
            isinstance(action, str) for action in recovery_actions
        ):
            raise SystemExit("web route smoke check failed: incomplete fixture case metadata")
        if failure_stage not in VALID_DIAGNOSTIC_FAILURE_STAGES:
            raise SystemExit(f"web route smoke check failed: {case} unknown fixture failure stage")

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
        recovery_action_text = ", ".join(
            str(action) for action in expected_actions if isinstance(action, str)
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
        ]
        expected_selected_option = (
            f'value="{html.escape(case, quote=True)}" selected '
            f'data-failure-stage="{html.escape(str(expected_stage), quote=True)}" '
            f'data-recovery-action-kinds="{html.escape(recovery_action_text, quote=True)}">'
            f'{html.escape(str(expected_label))}</option>'
        )
        if not isinstance(expected_label, str) or expected_selected_option not in fixture_page:
            raise SystemExit(f"web route smoke check failed: {case} label drift")
        for action_index, action_kind in enumerate(expected_actions):
            expected_fragments.extend(
                [
                    f'id="recovery-action-{action_index}"',
                    f'data-action-kind="{action_kind}"',
                    f'data-action-index="{action_index}"',
                    'data-action-contract-api="/api/diagnostic-contract"',
                    f'data-action-contract-kind="{action_kind}"',
                    (
                        "href=\"/api/recovery-action?"
                        + html.escape(
                            urlencode({"case": case, "index": str(action_index)}),
                            quote=True,
                        )
                        + '"'
                    ),
                    'data-action-export="json"',
                ]
            )
        for fragment in expected_fragments:
            if fragment not in fixture_page:
                raise SystemExit(
                    "web route smoke check failed: diagnostic fixture page missing "
                    f"{fragment} for {case}"
                )
        validate_diagnostic_contract_html_panel(fixture_page)


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


def validate_diagnostic_contract_html_panel(page: str) -> None:
    expected_fields = {
        "failure_stages": sorted(VALID_DIAGNOSTIC_FAILURE_STAGES),
        "required_fixture_stages": sorted(REQUIRED_DIAGNOSTIC_FIXTURE_STAGES),
        "recovery_action_kinds": sorted(VALID_DIAGNOSTIC_RECOVERY_ACTION_KINDS),
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


def run_web_route_smoke_check() -> None:
    from web.app import PipelineHandler

    print("==> web route smoke check")
    server = ThreadingHTTPServer(("127.0.0.1", 0), PipelineHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        opener = build_opener(ProxyHandler({}))
        with opener.open(f"http://127.0.0.1:{port}/api/diagnostic-contract", timeout=5) as response:
            validate_diagnostic_contract_manifest(json.load(response))
        with opener.open(f"http://127.0.0.1:{port}/api/diagnostic-fixtures", timeout=5) as response:
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
            with opener.open(f"http://127.0.0.1:{port}{api_path}", timeout=5) as response:
                fixture_payloads[case] = json.load(response)
            actions = fixture_payloads[case].get("diagnostics", {}).get("recovery_actions", [])
            if not isinstance(actions, list):
                raise SystemExit(f"web route smoke check failed: {case} missing recovery actions")
            for action_index, action in enumerate(actions):
                query = urlencode({"case": case, "index": str(action_index)})
                with opener.open(
                    f"http://127.0.0.1:{port}/api/recovery-action?{query}",
                    timeout=5,
                ) as response:
                    validate_recovery_action_export_bundle(
                        case,
                        action_index,
                        action,
                        json.load(response),
                    )
            with opener.open(f"http://127.0.0.1:{port}{html_path}", timeout=5) as response:
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
