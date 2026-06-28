"""Shared diagnostic-stage and recovery-action contract for the web pipeline."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Iterable

from translator.semantic_reading_contract import SEMANTIC_READING_CONTRACT_FIELDS


JSON_API_ROUTE_VALIDATION_SCHEMA = "json_api_route_validation.v1"
DIAGNOSTIC_FAILURE_STAGES = frozenset(
    {
        "input",
        "parsing",
        "type_check",
        "semantic_readings_check",
        "construction_hygiene",
        "coq_check",
    }
)
REQUIRED_DIAGNOSTIC_FIXTURE_STAGES = frozenset(
    {
        "type_check",
        "semantic_readings_check",
        "construction_hygiene",
        "coq_check",
    }
)
DIAGNOSTIC_RECOVERY_ACTION_KINDS = frozenset(
    {
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
)
DIAGNOSTIC_REPAIR_PLAN_AUTOMATION_MODES = frozenset(
    {
        "human_review_required",
        "inspection_only",
    }
)
INSPECTION_ONLY_RECOVERY_ACTION_KINDS = frozenset(
    {
        "inspect_ast",
        "inspect_coq",
        "inspect_readings",
    }
)


@dataclass(frozen=True)
class JsonApiRouteValidationSpec:
    path: str
    label: str
    expected_statuses: tuple[int, ...]
    json_modes: tuple[str, ...]
    text_bypass_modes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        path = self.path.strip()
        label = self.label.strip()
        expected_statuses = tuple(int(status) for status in self.expected_statuses)
        json_modes = tuple(mode.strip() for mode in self.json_modes)
        text_bypass_modes = tuple(mode.strip() for mode in self.text_bypass_modes)
        if not path.startswith("/api/"):
            raise ValueError(f"JSON route validation path must be an API route: {path!r}.")
        if "?" in path:
            raise ValueError(
                f"JSON route validation path must not include a query: {path!r}."
            )
        if not label:
            raise ValueError(f"JSON route validation path {path!r} needs a label.")
        if not expected_statuses:
            raise ValueError(f"JSON route validation path {path!r} needs statuses.")
        if any(status < 100 or status > 599 for status in expected_statuses):
            raise ValueError(
                f"JSON route validation path {path!r} has invalid HTTP statuses."
            )
        if len(set(expected_statuses)) != len(expected_statuses):
            raise ValueError(
                f"JSON route validation path {path!r} has duplicate statuses."
            )
        if not json_modes:
            raise ValueError(f"JSON route validation path {path!r} needs JSON modes.")
        if any(not mode for mode in json_modes + text_bypass_modes):
            raise ValueError(f"JSON route validation path {path!r} has an empty mode.")
        if len(set(json_modes)) != len(json_modes):
            raise ValueError(
                f"JSON route validation path {path!r} has duplicate JSON modes."
            )
        if len(set(text_bypass_modes)) != len(text_bypass_modes):
            raise ValueError(
                f"JSON route validation path {path!r} has duplicate text bypass modes."
            )
        overlap = sorted(set(json_modes) & set(text_bypass_modes))
        if overlap:
            raise ValueError(
                f"JSON route validation path {path!r} has mode overlap: {overlap!r}."
            )
        object.__setattr__(self, "path", path)
        object.__setattr__(self, "label", label)
        object.__setattr__(self, "expected_statuses", expected_statuses)
        object.__setattr__(self, "json_modes", json_modes)
        object.__setattr__(self, "text_bypass_modes", text_bypass_modes)

    def as_contract_entry(self) -> dict[str, object]:
        return {
            "path": self.path,
            "label": self.label,
            "validator": "JsonApiRouteValidatingOpener",
            "expected_statuses": list(self.expected_statuses),
            "json_modes": list(self.json_modes),
            "text_bypass_modes": list(self.text_bypass_modes),
        }


def validate_json_api_route_validation_specs(
    specs: Iterable[JsonApiRouteValidationSpec],
) -> tuple[JsonApiRouteValidationSpec, ...]:
    normalized = tuple(specs)
    if not normalized:
        raise ValueError("JSON route validation specs require at least one route.")
    paths = [spec.path for spec in normalized]
    duplicates = sorted(path for path, count in Counter(paths).items() if count > 1)
    if duplicates:
        raise ValueError(f"Duplicate JSON route validation paths: {duplicates!r}.")
    return normalized


JSON_API_ROUTE_VALIDATION_SPECS = validate_json_api_route_validation_specs(
    (
        JsonApiRouteValidationSpec(
            "/api/analyze",
            "ordinary analyze",
            (200,),
            ("ordinary_success_or_failure_json",),
        ),
        JsonApiRouteValidationSpec(
            "/api/analyze-action",
            "ordinary analyze action",
            (200, 400),
            ("action_export_json", "action_download_json", "invalid_index_error_json"),
        ),
        JsonApiRouteValidationSpec(
            "/api/analyze-action-run",
            "ordinary analyze inspection run",
            (200, 400),
            ("inspection_json", "inspection_download_json", "human_review_error_json"),
        ),
        JsonApiRouteValidationSpec(
            "/api/construction-rule-draft",
            "construction rule draft",
            (200, 400),
            ("draft_json", "draft_download_json", "no_draft_error_json"),
        ),
        JsonApiRouteValidationSpec(
            "/api/diagnostic-contract",
            "diagnostic contract",
            (200,),
            ("manifest_json",),
        ),
        JsonApiRouteValidationSpec(
            "/api/certified-fragment",
            "certified fragment",
            (200,),
            ("manifest_json",),
        ),
        JsonApiRouteValidationSpec(
            "/api/diagnostic-fixtures",
            "diagnostic fixtures manifest",
            (200,),
            ("manifest_json",),
        ),
        JsonApiRouteValidationSpec(
            "/api/diagnostic-fixture",
            "diagnostic fixture",
            (200,),
            ("fixture_json",),
        ),
        JsonApiRouteValidationSpec(
            "/api/recovery-action",
            "diagnostic recovery action",
            (200, 400),
            ("action_export_json", "action_download_json", "bad_request_json"),
        ),
        JsonApiRouteValidationSpec(
            "/api/recovery-action-run",
            "diagnostic recovery action run",
            (200, 400),
            ("inspection_json", "inspection_download_json", "human_review_error_json"),
        ),
        JsonApiRouteValidationSpec(
            "/api/lexicon-patch-drafts",
            "lexicon patch bundle",
            (200, 400),
            ("bundle_json", "unsupported_format_error_json"),
            ("format=patch",),
        ),
    )
)


def json_api_route_validation_manifest() -> dict[str, object]:
    return {
        "schema_version": JSON_API_ROUTE_VALIDATION_SCHEMA,
        "validator": "JsonApiRouteValidatingOpener",
        "route_count": len(JSON_API_ROUTE_VALIDATION_SPECS),
        "routes": [spec.as_contract_entry() for spec in JSON_API_ROUTE_VALIDATION_SPECS],
    }


def recovery_action_automation_mode(action_kind: str) -> str:
    if action_kind in INSPECTION_ONLY_RECOVERY_ACTION_KINDS:
        return "inspection_only"
    return "human_review_required"


def recovery_action_can_auto_run(action_kind: str) -> bool:
    return recovery_action_automation_mode(action_kind) == "inspection_only"


@dataclass(frozen=True)
class DiagnosticFixtureSpec:
    case: str
    label: str
    failure_stage: str
    recovery_action_kinds: tuple[str, ...]

    def __post_init__(self) -> None:
        case = self.case.strip()
        label = self.label.strip()
        failure_stage = self.failure_stage.strip()
        recovery_action_kinds = tuple(
            action.strip() for action in self.recovery_action_kinds
        )
        if not case:
            raise ValueError("Diagnostic fixture specs require a non-empty case.")
        if not label:
            raise ValueError(f"Diagnostic fixture {case!r} requires a non-empty label.")
        if failure_stage not in DIAGNOSTIC_FAILURE_STAGES:
            raise ValueError(
                f"Diagnostic fixture {case!r} uses unknown failure stage "
                f"{failure_stage!r}."
            )
        if not recovery_action_kinds:
            raise ValueError(
                f"Diagnostic fixture {case!r} requires at least one recovery action."
            )
        unknown_actions = sorted(
            action
            for action in set(recovery_action_kinds)
            if action not in DIAGNOSTIC_RECOVERY_ACTION_KINDS
        )
        if unknown_actions:
            raise ValueError(
                f"Diagnostic fixture {case!r} uses unknown recovery actions: "
                f"{unknown_actions!r}."
            )
        object.__setattr__(self, "case", case)
        object.__setattr__(self, "label", label)
        object.__setattr__(self, "failure_stage", failure_stage)
        object.__setattr__(self, "recovery_action_kinds", recovery_action_kinds)
