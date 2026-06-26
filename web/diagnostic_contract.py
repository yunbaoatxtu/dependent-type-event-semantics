"""Shared diagnostic-stage and recovery-action contract for the web pipeline."""

from __future__ import annotations

from dataclasses import dataclass

from translator.semantic_reading_contract import SEMANTIC_READING_CONTRACT_FIELDS


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
