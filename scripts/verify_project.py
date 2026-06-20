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
from urllib.parse import parse_qs, urlparse
from pathlib import Path
from urllib.request import ProxyHandler, build_opener

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
PYCACHE = ROOT / ".pycache"
COQ_FILE = ROOT / "formalization" / "DependentTypeEventSemantics.v"
PACKAGE_WHEEL_DIR = ROOT / "work" / "verify_package_build"
ROCQ_ENV = Path(
    "/Applications/Rocq-Platform~9.0~2025.08.app/Contents/Resources/bin/coq-env.sh"
)
VALID_DIAGNOSTIC_FAILURE_STAGES = {
    "input",
    "parsing",
    "type_check",
    "semantic_readings_check",
    "construction_hygiene",
    "coq_check",
}
REQUIRED_DIAGNOSTIC_FIXTURE_STAGES = {
    "type_check",
    "semantic_readings_check",
    "construction_hygiene",
    "coq_check",
}
VALID_DIAGNOSTIC_RECOVERY_ACTION_KINDS = {
    "add_missing_coq_definitions",
    "add_semantic_readings",
    "edit_input",
    "fix_malformed_readings",
    "fix_reading_type_checks",
    "inspect_ast",
    "inspect_coq",
    "inspect_readings",
    "normalize_reading_exports",
    "rename_duplicate_readings",
    "revise_sentence",
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
    if not bundle.get("can_auto_apply"):
        raise SystemExit("lexicon patch exporter smoke check failed: bundle is not auto-applicable")
    if "patch_text_preview" not in bundle:
        raise SystemExit("lexicon patch exporter smoke check failed: missing patch_text_preview")
    if 'StateLexiconEntry("color_scale", default_source_state="not_red")' not in patch_text:
        raise SystemExit("lexicon patch exporter smoke check failed: patch text missing red entry")


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
        expected_fragments.extend(
            f'data-action-kind="{action_kind}"' for action_kind in expected_actions
        )
        for fragment in expected_fragments:
            if fragment not in fixture_page:
                raise SystemExit(
                    "web route smoke check failed: diagnostic fixture page missing "
                    f"{fragment} for {case}"
                )


def run_web_route_smoke_check() -> None:
    from web.app import PipelineHandler

    print("==> web route smoke check")
    server = ThreadingHTTPServer(("127.0.0.1", 0), PipelineHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        opener = build_opener(ProxyHandler({}))
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
            with opener.open(f"http://127.0.0.1:{port}{html_path}", timeout=5) as response:
                fixture_pages[case] = response.read().decode("utf-8")
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
    run_web_route_smoke_check()
    if args.skip_coq:
        print("==> Coq scaffold boundary check skipped by --skip-coq")
    else:
        run_optional_coq_check(args.require_coq)
    print("all deterministic checks passed")


if __name__ == "__main__":
    main()
