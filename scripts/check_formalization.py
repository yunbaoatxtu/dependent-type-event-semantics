#!/usr/bin/env python3
"""Check that generated formalization scaffolds match current examples."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEAN_FILE = ROOT / "formalization" / "DependentTypeEventSemantics.lean"
COQ_FILE = ROOT / "formalization" / "DependentTypeEventSemantics.v"


def main() -> None:
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "generate_formalization.py")],
        check=True,
        capture_output=True,
        text=True,
    )

    lean = LEAN_FILE.read_text(encoding="utf-8")
    coq = COQ_FILE.read_text(encoding="utf-8")
    lean_example_count = len(re.findall(r"^def example_\d+ :", lean, re.MULTILINE))
    coq_example_count = len(re.findall(r"^Definition example_\d+ :", coq, re.MULTILINE))
    lean_obligation_count = len(
        re.findall(
            r"^def example_\d+_semantic_preservation_obligation : Prop :=",
            lean,
            re.MULTILINE,
        )
    )
    coq_obligation_count = len(
        re.findall(
            r"^Definition example_\d+_semantic_preservation_obligation : Prop :=",
            coq,
            re.MULTILINE,
        )
    )
    lean_obligation_record_count = len(
        re.findall(
            r"^def example_\d+_semantic_preservation_obligation_record : "
            r"SemanticPreservationObligation :=",
            lean,
            re.MULTILINE,
        )
    )
    coq_obligation_record_count = len(
        re.findall(
            r"^Definition example_\d+_semantic_preservation_obligation_record : "
            r"SemanticPreservationObligation :=",
            coq,
            re.MULTILINE,
        )
    )
    lean_obligation_wellformed_count = len(
        re.findall(
            r"^theorem example_\d+_semantic_preservation_obligation_is_prop :",
            lean,
            re.MULTILINE,
        )
    )
    coq_obligation_wellformed_count = len(
        re.findall(
            r"^Theorem example_\d+_semantic_preservation_obligation_is_prop :",
            coq,
            re.MULTILINE,
        )
    )
    coq_obligation_wellformed_proof_count = len(
        re.findall(
            r"^Proof\. exists example_\d+_semantic_preservation_obligation\. "
            r"reflexivity\. Qed\.$",
            coq,
            re.MULTILINE,
        )
    )
    lean_target_match_count = len(
        re.findall(
            r"^theorem example_\d+_semantic_preservation_target_matches :",
            lean,
            re.MULTILINE,
        )
    )
    coq_target_match_count = len(
        re.findall(
            r"^Theorem example_\d+_semantic_preservation_target_matches :",
            coq,
            re.MULTILINE,
        )
    )
    coq_reflexive_proof_count = len(
        re.findall(r"^Proof\. reflexivity\. Qed\.$", coq, re.MULTILINE)
    )
    lean_structural_proof_count = len(
        re.findall(
            r"^theorem example_\d+_semantic_preservation_proved :",
            lean,
            re.MULTILINE,
        )
    )
    coq_structural_proof_count = len(
        re.findall(
            r"^Theorem example_\d+_semantic_preservation_proved :",
            coq,
            re.MULTILINE,
        )
    )
    lean_model_boundary_count = len(
        re.findall(
            r"^theorem example_\d+_model_interpretable :",
            lean,
            re.MULTILINE,
        )
    )
    coq_model_boundary_count = len(
        re.findall(
            r"^Theorem example_\d+_model_interpretable :",
            coq,
            re.MULTILINE,
        )
    )
    lean_denotation_sound_count = len(
        re.findall(
            r"^theorem example_\d+_denotationally_sound :",
            lean,
            re.MULTILINE,
        )
    )
    coq_denotation_sound_count = len(
        re.findall(
            r"^Theorem example_\d+_denotationally_sound :",
            coq,
            re.MULTILINE,
        )
    )
    lean_truth_condition_sound_count = len(
        re.findall(
            r"^theorem example_\d+_truth_condition_sound :",
            lean,
            re.MULTILINE,
        )
    )
    coq_truth_condition_sound_count = len(
        re.findall(
            r"^Theorem example_\d+_truth_condition_sound :",
            coq,
            re.MULTILINE,
        )
    )
    lean_tautological_truth_condition_sound_count = len(
        re.findall(
            r"^theorem example_\d+_tautological_truth_condition_sound :",
            lean,
            re.MULTILINE,
        )
    )
    coq_tautological_truth_condition_sound_count = len(
        re.findall(
            r"^Theorem example_\d+_tautological_truth_condition_sound :",
            coq,
            re.MULTILINE,
        )
    )
    lean_structural_truth_condition_sound_count = len(
        re.findall(
            r"^theorem example_\d+_structural_truth_condition_sound :",
            lean,
            re.MULTILINE,
        )
    )
    coq_structural_truth_condition_sound_count = len(
        re.findall(
            r"^Theorem example_\d+_structural_truth_condition_sound :",
            coq,
            re.MULTILINE,
        )
    )
    lean_concrete_kernel_truth_condition_sound_count = len(
        re.findall(
            r"^theorem example_\d+_concrete_kernel_truth_condition_sound :",
            lean,
            re.MULTILINE,
        )
    )
    coq_concrete_kernel_truth_condition_sound_count = len(
        re.findall(
            r"^Theorem example_\d+_concrete_kernel_truth_condition_sound :",
            coq,
            re.MULTILINE,
        )
    )
    lean_model_interpretable_truth_kernel_sound_count = len(
        re.findall(
            r"^theorem example_\d+_model_interpretable_truth_kernel_sound :",
            lean,
            re.MULTILINE,
        )
    )
    coq_model_interpretable_truth_kernel_sound_count = len(
        re.findall(
            r"^Theorem example_\d+_model_interpretable_truth_kernel_sound :",
            coq,
            re.MULTILINE,
        )
    )
    lean_primitive_truth_kernel_sound_count = len(
        re.findall(
            r"^theorem example_\d+_primitive_truth_kernel_sound :",
            lean,
            re.MULTILINE,
        )
    )
    coq_primitive_truth_kernel_sound_count = len(
        re.findall(
            r"^Theorem example_\d+_primitive_truth_kernel_sound :",
            coq,
            re.MULTILINE,
        )
    )
    lean_atomic_closure_truth_count = len(
        re.findall(
            r"^theorem example_\d+_atomic_closure_truth :",
            lean,
            re.MULTILINE,
        )
    )
    coq_atomic_closure_truth_count = len(
        re.findall(
            r"^Theorem example_\d+_atomic_closure_truth :",
            coq,
            re.MULTILINE,
        )
    )
    lean_atomic_closure_truth_kernel_sound_count = len(
        re.findall(
            r"^theorem example_\d+_atomic_closure_truth_kernel_sound :",
            lean,
            re.MULTILINE,
        )
    )
    coq_atomic_closure_truth_kernel_sound_count = len(
        re.findall(
            r"^Theorem example_\d+_atomic_closure_truth_kernel_sound :",
            coq,
            re.MULTILINE,
        )
    )
    lean_syntax_directed_truth_count = len(
        re.findall(
            r"^theorem example_\d+_syntax_directed_truth :",
            lean,
            re.MULTILINE,
        )
    )
    coq_syntax_directed_truth_count = len(
        re.findall(
            r"^Theorem example_\d+_syntax_directed_truth :",
            coq,
            re.MULTILINE,
        )
    )
    lean_syntax_directed_truth_kernel_sound_count = len(
        re.findall(
            r"^theorem example_\d+_syntax_directed_truth_kernel_sound :",
            lean,
            re.MULTILINE,
        )
    )
    coq_syntax_directed_truth_kernel_sound_count = len(
        re.findall(
            r"^Theorem example_\d+_syntax_directed_truth_kernel_sound :",
            coq,
            re.MULTILINE,
        )
    )
    lean_fully_registered_atomic_closure_truth_count = len(
        re.findall(
            r"^theorem example_\d+_fully_registered_atomic_closure_truth :",
            lean,
            re.MULTILINE,
        )
    )
    coq_fully_registered_atomic_closure_truth_count = len(
        re.findall(
            r"^Theorem example_\d+_fully_registered_atomic_closure_truth :",
            coq,
            re.MULTILINE,
        )
    )
    lean_fully_registered_truth_condition_sound_count = len(
        re.findall(
            r"^theorem example_\d+_fully_registered_truth_condition_sound :",
            lean,
            re.MULTILINE,
        )
    )
    coq_fully_registered_truth_condition_sound_count = len(
        re.findall(
            r"^Theorem example_\d+_fully_registered_truth_condition_sound :",
            coq,
            re.MULTILINE,
        )
    )
    lean_registered_example_truth_instance_atomic_sound_count = len(
        re.findall(
            r"^theorem registered_example_\d+_truth_instance_atomic_sound :",
            lean,
            re.MULTILINE,
        )
    )
    coq_registered_example_truth_instance_atomic_sound_count = len(
        re.findall(
            r"^Theorem registered_example_\d+_truth_instance_atomic_sound :",
            coq,
            re.MULTILINE,
        )
    )
    lean_registered_lexical_truth_model_sound_count = len(
        re.findall(
            r"^theorem example_\d+_registered_lexical_truth_model_sound :",
            lean,
            re.MULTILINE,
        )
    )
    coq_registered_lexical_truth_model_sound_count = len(
        re.findall(
            r"^Theorem example_\d+_registered_lexical_truth_model_sound :",
            coq,
            re.MULTILINE,
        )
    )
    lean_registered_lexical_truth_conditions_from_model_sound_count = len(
        re.findall(
            r"^theorem example_\d+_registered_lexical_truth_conditions_from_model_sound :",
            lean,
            re.MULTILINE,
        )
    )
    coq_registered_lexical_truth_conditions_from_model_sound_count = len(
        re.findall(
            r"^Theorem example_\d+_registered_lexical_truth_conditions_from_model_sound :",
            coq,
            re.MULTILINE,
        )
    )
    lean_concrete_registered_truth_count = len(
        re.findall(
            r"^theorem example_\d+_concrete_registered_truth :",
            lean,
            re.MULTILINE,
        )
    )
    coq_concrete_registered_truth_count = len(
        re.findall(
            r"^Theorem example_\d+_concrete_registered_truth :",
            coq,
            re.MULTILINE,
        )
    )
    lean_concrete_registered_truth_kernel_sound_count = len(
        re.findall(
            r"^theorem example_\d+_concrete_registered_truth_kernel_sound :",
            lean,
            re.MULTILINE,
        )
    )
    coq_concrete_registered_truth_kernel_sound_count = len(
        re.findall(
            r"^Theorem example_\d+_concrete_registered_truth_kernel_sound :",
            coq,
            re.MULTILINE,
        )
    )
    lean_concrete_registered_truth_conditions_from_kernel_sound_count = len(
        re.findall(
            r"^theorem example_\d+_concrete_registered_truth_conditions_from_kernel_sound :",
            lean,
            re.MULTILINE,
        )
    )
    coq_concrete_registered_truth_conditions_from_kernel_sound_count = len(
        re.findall(
            r"^Theorem example_\d+_concrete_registered_truth_conditions_from_kernel_sound :",
            coq,
            re.MULTILINE,
        )
    )
    lean_concrete_registered_truth_conditions_from_kernel_atomic_sound_count = len(
        re.findall(
            r"^theorem example_\d+_concrete_registered_truth_conditions_from_kernel_atomic_sound :",
            lean,
            re.MULTILINE,
        )
    )
    coq_concrete_registered_truth_conditions_from_kernel_atomic_sound_count = len(
        re.findall(
            r"^Theorem example_\d+_concrete_registered_truth_conditions_from_kernel_atomic_sound :",
            coq,
            re.MULTILINE,
        )
    )
    lean_concrete_registered_truth_condition_sound_count = len(
        re.findall(
            r"^theorem example_\d+_concrete_registered_truth_condition_sound :",
            lean,
            re.MULTILINE,
        )
    )
    coq_concrete_registered_truth_condition_sound_count = len(
        re.findall(
            r"^Theorem example_\d+_concrete_registered_truth_condition_sound :",
            coq,
            re.MULTILINE,
        )
    )
    lean_concrete_registered_truth_condition_atomic_sound_count = len(
        re.findall(
            r"^theorem example_\d+_concrete_registered_truth_condition_atomic_sound :",
            lean,
            re.MULTILINE,
        )
    )
    coq_concrete_registered_truth_condition_atomic_sound_count = len(
        re.findall(
            r"^Theorem example_\d+_concrete_registered_truth_condition_atomic_sound :",
            coq,
            re.MULTILINE,
        )
    )
    lean_concrete_registered_evidence_backed_truth_condition_sound_count = len(
        re.findall(
            r"^theorem example_\d+_concrete_registered_evidence_backed_truth_condition_sound :",
            lean,
            re.MULTILINE,
        )
    )
    coq_concrete_registered_evidence_backed_truth_condition_sound_count = len(
        re.findall(
            r"^Theorem example_\d+_concrete_registered_evidence_backed_truth_condition_sound :",
            coq,
            re.MULTILINE,
        )
    )
    lean_concrete_registered_evidence_backed_truth_condition_atomic_sound_count = len(
        re.findall(
            r"^theorem example_\d+_concrete_registered_evidence_backed_truth_condition_atomic_sound :",
            lean,
            re.MULTILINE,
        )
    )
    coq_concrete_registered_evidence_backed_truth_condition_atomic_sound_count = len(
        re.findall(
            r"^Theorem example_\d+_concrete_registered_evidence_backed_truth_condition_atomic_sound :",
            coq,
            re.MULTILINE,
        )
    )
    lean_concrete_registered_evidence_backed_example_truth_instance_atomic_sound_count = len(
        re.findall(
            r"^theorem concrete_registered_evidence_backed_example_\d+_truth_instance_atomic_sound :",
            lean,
            re.MULTILINE,
        )
    )
    coq_concrete_registered_evidence_backed_example_truth_instance_atomic_sound_count = len(
        re.findall(
            r"^Theorem concrete_registered_evidence_backed_example_\d+_truth_instance_atomic_sound :",
            coq,
            re.MULTILINE,
        )
    )
    lean_concrete_registered_example_truth_instance_atomic_sound_count = len(
        re.findall(
            r"^theorem concrete_registered_example_\d+_truth_instance_atomic_sound :",
            lean,
            re.MULTILINE,
        )
    )
    coq_concrete_registered_example_truth_instance_atomic_sound_count = len(
        re.findall(
            r"^Theorem concrete_registered_example_\d+_truth_instance_atomic_sound :",
            coq,
            re.MULTILINE,
        )
    )
    lean_concrete_registered_kernel_example_truth_instance_atomic_sound_count = len(
        re.findall(
            r"^theorem concrete_registered_kernel_example_\d+_truth_instance_atomic_sound :",
            lean,
            re.MULTILINE,
        )
    )
    coq_concrete_registered_kernel_example_truth_instance_atomic_sound_count = len(
        re.findall(
            r"^Theorem concrete_registered_kernel_example_\d+_truth_instance_atomic_sound :",
            coq,
            re.MULTILINE,
        )
    )
    lean_concrete_registered_route_direct_atomic_sound_count = len(
        re.findall(
            r"^theorem concrete_registered_truth_condition_route_example_\d+_direct_atomic_sound :",
            lean,
            re.MULTILINE,
        )
    )
    coq_concrete_registered_route_direct_atomic_sound_count = len(
        re.findall(
            r"^Theorem concrete_registered_truth_condition_route_example_\d+_direct_atomic_sound :",
            coq,
            re.MULTILINE,
        )
    )
    lean_concrete_registered_route_evidence_atomic_sound_count = len(
        re.findall(
            r"^theorem concrete_registered_truth_condition_route_example_\d+_evidence_atomic_sound :",
            lean,
            re.MULTILINE,
        )
    )
    coq_concrete_registered_route_evidence_atomic_sound_count = len(
        re.findall(
            r"^Theorem concrete_registered_truth_condition_route_example_\d+_evidence_atomic_sound :",
            coq,
            re.MULTILINE,
        )
    )
    lean_concrete_registered_route_kernel_atomic_sound_count = len(
        re.findall(
            r"^theorem concrete_registered_truth_condition_route_example_\d+_kernel_atomic_sound :",
            lean,
            re.MULTILINE,
        )
    )
    coq_concrete_registered_route_kernel_atomic_sound_count = len(
        re.findall(
            r"^Theorem concrete_registered_truth_condition_route_example_\d+_kernel_atomic_sound :",
            coq,
            re.MULTILINE,
        )
    )
    lean_concrete_registered_route_agreement_direct_atomic_sound_count = len(
        re.findall(
            r"^theorem concrete_registered_truth_condition_route_example_\d+_agreement_direct_atomic_sound :",
            lean,
            re.MULTILINE,
        )
    )
    coq_concrete_registered_route_agreement_direct_atomic_sound_count = len(
        re.findall(
            r"^Theorem concrete_registered_truth_condition_route_example_\d+_agreement_direct_atomic_sound :",
            coq,
            re.MULTILINE,
        )
    )
    lean_concrete_registered_route_agreement_evidence_atomic_sound_count = len(
        re.findall(
            r"^theorem concrete_registered_truth_condition_route_example_\d+_agreement_evidence_atomic_sound :",
            lean,
            re.MULTILINE,
        )
    )
    coq_concrete_registered_route_agreement_evidence_atomic_sound_count = len(
        re.findall(
            r"^Theorem concrete_registered_truth_condition_route_example_\d+_agreement_evidence_atomic_sound :",
            coq,
            re.MULTILINE,
        )
    )
    lean_concrete_registered_route_agreement_kernel_atomic_sound_count = len(
        re.findall(
            r"^theorem concrete_registered_truth_condition_route_example_\d+_agreement_kernel_atomic_sound :",
            lean,
            re.MULTILINE,
        )
    )
    coq_concrete_registered_route_agreement_kernel_atomic_sound_count = len(
        re.findall(
            r"^Theorem concrete_registered_truth_condition_route_example_\d+_agreement_kernel_atomic_sound :",
            coq,
            re.MULTILINE,
        )
    )
    lean_independent_registered_truth_condition_source_atomic_sound_count = len(
        re.findall(
            r"^theorem independent_registered_truth_condition_sources_example_\d+_atomic_sound :",
            lean,
            re.MULTILINE,
        )
    )
    coq_independent_registered_truth_condition_source_atomic_sound_count = len(
        re.findall(
            r"^Theorem independent_registered_truth_condition_sources_example_\d+_atomic_sound :",
            coq,
            re.MULTILINE,
        )
    )
    lean_independent_registered_truth_condition_clause_atomic_sound_count = len(
        re.findall(
            r"^theorem independent_registered_truth_condition_clause_example_\d+_atomic_sound :",
            lean,
            re.MULTILINE,
        )
    )
    coq_independent_registered_truth_condition_clause_atomic_sound_count = len(
        re.findall(
            r"^Theorem independent_registered_truth_condition_clause_example_\d+_atomic_sound :",
            coq,
            re.MULTILINE,
        )
    )
    lean_independent_registered_truth_condition_clause_coverage_atomic_sound_count = len(
        re.findall(
            r"^theorem independent_registered_truth_condition_clause_coverage_example_\d+_atomic_sound :",
            lean,
            re.MULTILINE,
        )
    )
    coq_independent_registered_truth_condition_clause_coverage_atomic_sound_count = len(
        re.findall(
            r"^Theorem independent_registered_truth_condition_clause_coverage_example_\d+_atomic_sound :",
            coq,
            re.MULTILINE,
        )
    )
    lean_independent_registered_truth_condition_suite_example_atomic_sound_count = len(
        re.findall(
            r"^theorem independent_registered_truth_condition_instance_suite_example_\d+_atomic_sound :",
            lean,
            re.MULTILINE,
        )
    )
    coq_independent_registered_truth_condition_suite_example_atomic_sound_count = len(
        re.findall(
            r"^Theorem independent_registered_truth_condition_instance_suite_example_\d+_atomic_sound :",
            coq,
            re.MULTILINE,
        )
    )
    finite_ledger_atomic_patterns = {
        "suite": r"^theorem finite_registered_truth_condition_ledger_example_\d+_suite_atomic_sound :",
        "registered": r"^theorem finite_registered_truth_condition_ledger_example_\d+_registered_atomic_sound :",
        "concrete": r"^theorem finite_registered_truth_condition_ledger_example_\d+_concrete_atomic_sound :",
        "kernel": r"^theorem finite_registered_truth_condition_ledger_example_\d+_kernel_atomic_sound :",
    }
    lean_finite_registered_truth_condition_ledger_atomic_counts = {
        key: len(re.findall(pattern, lean, re.MULTILINE))
        for key, pattern in finite_ledger_atomic_patterns.items()
    }
    coq_finite_registered_truth_condition_ledger_atomic_counts = {
        key: len(
            re.findall(
                pattern.replace("^theorem", "^Theorem"),
                coq,
                re.MULTILINE,
            )
        )
        for key, pattern in finite_ledger_atomic_patterns.items()
    }
    finite_completion_atomic_patterns = {
        "registered": r"^theorem finite_registered_truth_condition_completion_example_\d+_registered_atomic_sound :",
        "direct": r"^theorem finite_registered_truth_condition_completion_example_\d+_direct_atomic_sound :",
        "evidence": r"^theorem finite_registered_truth_condition_completion_example_\d+_evidence_atomic_sound :",
        "kernel": r"^theorem finite_registered_truth_condition_completion_example_\d+_kernel_atomic_sound :",
        "source": r"^theorem finite_registered_truth_condition_completion_example_\d+_source_atomic_sound :",
        "suite": r"^theorem finite_registered_truth_condition_completion_example_\d+_suite_atomic_sound :",
    }
    lean_finite_registered_truth_condition_completion_atomic_counts = {
        key: len(re.findall(pattern, lean, re.MULTILINE))
        for key, pattern in finite_completion_atomic_patterns.items()
    }
    coq_finite_registered_truth_condition_completion_atomic_counts = {
        key: len(
            re.findall(
                pattern.replace("^theorem", "^Theorem"),
                coq,
                re.MULTILINE,
            )
        )
        for key, pattern in finite_completion_atomic_patterns.items()
    }
    lean_finite_registered_truth_condition_component_coverage_atomic_count = len(
        re.findall(
            r"^theorem finite_registered_truth_condition_component_coverage_example_\d+_atomic_sound :",
            lean,
            re.MULTILINE,
        )
    )
    coq_finite_registered_truth_condition_component_coverage_atomic_count = len(
        re.findall(
            r"^Theorem finite_registered_truth_condition_component_coverage_example_\d+_atomic_sound :",
            coq,
            re.MULTILINE,
        )
    )
    lean_finite_registered_atomic_witness_lexical_projection_count = len(
        re.findall(
            r"^theorem finite_registered_atomic_witness_lexical_\d+_(concrete|base|closure)_projected :",
            lean,
            re.MULTILINE,
        )
    )
    coq_finite_registered_atomic_witness_lexical_projection_count = len(
        re.findall(
            r"^Theorem finite_registered_atomic_witness_lexical_\d+_(concrete|base|closure)_projected :",
            coq,
            re.MULTILINE,
        )
    )
    lean_finite_registered_atomic_witness_transition_projection_count = len(
        re.findall(
            r"^theorem finite_registered_atomic_witness_transition_\d+_(concrete|base|closure)_projected :",
            lean,
            re.MULTILINE,
        )
    )
    coq_finite_registered_atomic_witness_transition_projection_count = len(
        re.findall(
            r"^Theorem finite_registered_atomic_witness_transition_\d+_(concrete|base|closure)_projected :",
            coq,
            re.MULTILINE,
        )
    )
    lean_finite_registered_atomic_source_lexical_source_count = len(
        re.findall(
            r"^theorem finite_registered_atomic_source_lexical_\d+_source_projected :",
            lean,
            re.MULTILINE,
        )
    )
    coq_finite_registered_atomic_source_lexical_source_count = len(
        re.findall(
            r"^Theorem finite_registered_atomic_source_lexical_\d+_source_projected :",
            coq,
            re.MULTILINE,
        )
    )
    lean_finite_registered_atomic_source_lexical_bridge_count = len(
        re.findall(
            r"^theorem finite_registered_atomic_source_lexical_\d+_(concrete|base|closure)_from_source_projected :",
            lean,
            re.MULTILINE,
        )
    )
    coq_finite_registered_atomic_source_lexical_bridge_count = len(
        re.findall(
            r"^Theorem finite_registered_atomic_source_lexical_\d+_(concrete|base|closure)_from_source_projected :",
            coq,
            re.MULTILINE,
        )
    )
    lean_finite_registered_atomic_source_transition_source_count = len(
        re.findall(
            r"^theorem finite_registered_atomic_source_transition_\d+_source_projected :",
            lean,
            re.MULTILINE,
        )
    )
    coq_finite_registered_atomic_source_transition_source_count = len(
        re.findall(
            r"^Theorem finite_registered_atomic_source_transition_\d+_source_projected :",
            coq,
            re.MULTILINE,
        )
    )
    lean_finite_registered_atomic_source_transition_bridge_count = len(
        re.findall(
            r"^theorem finite_registered_atomic_source_transition_\d+_(concrete|base|closure)_from_source_projected :",
            lean,
            re.MULTILINE,
        )
    )
    coq_finite_registered_atomic_source_transition_bridge_count = len(
        re.findall(
            r"^Theorem finite_registered_atomic_source_transition_\d+_(concrete|base|closure)_from_source_projected :",
            coq,
            re.MULTILINE,
        )
    )
    lean_finite_registered_atomic_kernel_alignment_lexical_source_count = len(
        re.findall(
            r"^theorem finite_registered_atomic_kernel_alignment_lexical_\d+_source_to_kernel_projected :",
            lean,
            re.MULTILINE,
        )
    )
    coq_finite_registered_atomic_kernel_alignment_lexical_source_count = len(
        re.findall(
            r"^Theorem finite_registered_atomic_kernel_alignment_lexical_\d+_source_to_kernel_projected :",
            coq,
            re.MULTILINE,
        )
    )
    lean_finite_registered_atomic_kernel_alignment_lexical_atomic_count = len(
        re.findall(
            r"^theorem finite_registered_atomic_kernel_alignment_lexical_\d+_atomic_projected :",
            lean,
            re.MULTILINE,
        )
    )
    coq_finite_registered_atomic_kernel_alignment_lexical_atomic_count = len(
        re.findall(
            r"^Theorem finite_registered_atomic_kernel_alignment_lexical_\d+_atomic_projected :",
            coq,
            re.MULTILINE,
        )
    )
    lean_finite_registered_atomic_kernel_alignment_transition_source_count = len(
        re.findall(
            r"^theorem finite_registered_atomic_kernel_alignment_transition_\d+_source_to_kernel_projected :",
            lean,
            re.MULTILINE,
        )
    )
    coq_finite_registered_atomic_kernel_alignment_transition_source_count = len(
        re.findall(
            r"^Theorem finite_registered_atomic_kernel_alignment_transition_\d+_source_to_kernel_projected :",
            coq,
            re.MULTILINE,
        )
    )
    lean_finite_registered_atomic_kernel_alignment_transition_atomic_count = len(
        re.findall(
            r"^theorem finite_registered_atomic_kernel_alignment_transition_\d+_atomic_projected :",
            lean,
            re.MULTILINE,
        )
    )
    coq_finite_registered_atomic_kernel_alignment_transition_atomic_count = len(
        re.findall(
            r"^Theorem finite_registered_atomic_kernel_alignment_transition_\d+_atomic_projected :",
            coq,
            re.MULTILINE,
        )
    )
    lean_finite_registered_atomic_truth_condition_source_lexical_spec_count = len(
        re.findall(
            r"^theorem finite_registered_atomic_truth_condition_source_lexical_\d+_source_to_spec_projected :",
            lean,
            re.MULTILINE,
        )
    )
    coq_finite_registered_atomic_truth_condition_source_lexical_spec_count = len(
        re.findall(
            r"^Theorem finite_registered_atomic_truth_condition_source_lexical_\d+_source_to_spec_projected :",
            coq,
            re.MULTILINE,
        )
    )
    lean_finite_registered_atomic_truth_condition_source_lexical_kernel_count = len(
        re.findall(
            r"^theorem finite_registered_atomic_truth_condition_source_lexical_\d+_source_to_kernel_projected :",
            lean,
            re.MULTILINE,
        )
    )
    coq_finite_registered_atomic_truth_condition_source_lexical_kernel_count = len(
        re.findall(
            r"^Theorem finite_registered_atomic_truth_condition_source_lexical_\d+_source_to_kernel_projected :",
            coq,
            re.MULTILINE,
        )
    )
    lean_finite_registered_atomic_truth_condition_source_lexical_atomic_count = len(
        re.findall(
            r"^theorem finite_registered_atomic_truth_condition_source_lexical_\d+_atomic_projected :",
            lean,
            re.MULTILINE,
        )
    )
    coq_finite_registered_atomic_truth_condition_source_lexical_atomic_count = len(
        re.findall(
            r"^Theorem finite_registered_atomic_truth_condition_source_lexical_\d+_atomic_projected :",
            coq,
            re.MULTILINE,
        )
    )
    lean_finite_registered_atomic_truth_condition_source_transition_spec_count = len(
        re.findall(
            r"^theorem finite_registered_atomic_truth_condition_source_transition_\d+_source_to_spec_projected :",
            lean,
            re.MULTILINE,
        )
    )
    coq_finite_registered_atomic_truth_condition_source_transition_spec_count = len(
        re.findall(
            r"^Theorem finite_registered_atomic_truth_condition_source_transition_\d+_source_to_spec_projected :",
            coq,
            re.MULTILINE,
        )
    )
    lean_finite_registered_atomic_truth_condition_source_transition_kernel_count = len(
        re.findall(
            r"^theorem finite_registered_atomic_truth_condition_source_transition_\d+_source_to_kernel_projected :",
            lean,
            re.MULTILINE,
        )
    )
    coq_finite_registered_atomic_truth_condition_source_transition_kernel_count = len(
        re.findall(
            r"^Theorem finite_registered_atomic_truth_condition_source_transition_\d+_source_to_kernel_projected :",
            coq,
            re.MULTILINE,
        )
    )
    lean_finite_registered_atomic_truth_condition_source_transition_atomic_count = len(
        re.findall(
            r"^theorem finite_registered_atomic_truth_condition_source_transition_\d+_atomic_projected :",
            lean,
            re.MULTILINE,
        )
    )
    coq_finite_registered_atomic_truth_condition_source_transition_atomic_count = len(
        re.findall(
            r"^Theorem finite_registered_atomic_truth_condition_source_transition_\d+_atomic_projected :",
            coq,
            re.MULTILINE,
        )
    )
    lean_finite_registered_atomic_truth_condition_instance_lexical_truth_count = len(
        re.findall(
            r"^theorem finite_registered_atomic_truth_condition_instance_lexical_\d+_truth_projected :",
            lean,
            re.MULTILINE,
        )
    )
    coq_finite_registered_atomic_truth_condition_instance_lexical_truth_count = len(
        re.findall(
            r"^Theorem finite_registered_atomic_truth_condition_instance_lexical_\d+_truth_projected :",
            coq,
            re.MULTILINE,
        )
    )
    lean_finite_registered_atomic_truth_condition_instance_lexical_atomic_count = len(
        re.findall(
            r"^theorem finite_registered_atomic_truth_condition_instance_lexical_\d+_atomic_projected :",
            lean,
            re.MULTILINE,
        )
    )
    coq_finite_registered_atomic_truth_condition_instance_lexical_atomic_count = len(
        re.findall(
            r"^Theorem finite_registered_atomic_truth_condition_instance_lexical_\d+_atomic_projected :",
            coq,
            re.MULTILINE,
        )
    )
    lean_finite_registered_atomic_truth_condition_instance_transition_truth_count = len(
        re.findall(
            r"^theorem finite_registered_atomic_truth_condition_instance_transition_\d+_truth_projected :",
            lean,
            re.MULTILINE,
        )
    )
    coq_finite_registered_atomic_truth_condition_instance_transition_truth_count = len(
        re.findall(
            r"^Theorem finite_registered_atomic_truth_condition_instance_transition_\d+_truth_projected :",
            coq,
            re.MULTILINE,
        )
    )
    lean_finite_registered_atomic_truth_condition_instance_transition_atomic_count = len(
        re.findall(
            r"^theorem finite_registered_atomic_truth_condition_instance_transition_\d+_atomic_projected :",
            lean,
            re.MULTILINE,
        )
    )
    coq_finite_registered_atomic_truth_condition_instance_transition_atomic_count = len(
        re.findall(
            r"^Theorem finite_registered_atomic_truth_condition_instance_transition_\d+_atomic_projected :",
            coq,
            re.MULTILINE,
        )
    )
    lean_finite_registered_atomic_truth_condition_witness_lexical_witness_count = len(
        re.findall(
            r"^theorem finite_registered_atomic_truth_condition_witness_lexical_\d+_projected :",
            lean,
            re.MULTILINE,
        )
    )
    coq_finite_registered_atomic_truth_condition_witness_lexical_witness_count = len(
        re.findall(
            r"^Theorem finite_registered_atomic_truth_condition_witness_lexical_\d+_projected :",
            coq,
            re.MULTILINE,
        )
    )
    lean_finite_registered_atomic_truth_condition_witness_lexical_truth_count = len(
        re.findall(
            r"^theorem finite_registered_atomic_truth_condition_witness_lexical_\d+_truth_projected :",
            lean,
            re.MULTILINE,
        )
    )
    coq_finite_registered_atomic_truth_condition_witness_lexical_truth_count = len(
        re.findall(
            r"^Theorem finite_registered_atomic_truth_condition_witness_lexical_\d+_truth_projected :",
            coq,
            re.MULTILINE,
        )
    )
    lean_finite_registered_atomic_truth_condition_witness_lexical_atomic_count = len(
        re.findall(
            r"^theorem finite_registered_atomic_truth_condition_witness_lexical_\d+_atomic_projected :",
            lean,
            re.MULTILINE,
        )
    )
    coq_finite_registered_atomic_truth_condition_witness_lexical_atomic_count = len(
        re.findall(
            r"^Theorem finite_registered_atomic_truth_condition_witness_lexical_\d+_atomic_projected :",
            coq,
            re.MULTILINE,
        )
    )
    lean_finite_registered_atomic_truth_condition_witness_transition_witness_count = len(
        re.findall(
            r"^theorem finite_registered_atomic_truth_condition_witness_transition_\d+_projected :",
            lean,
            re.MULTILINE,
        )
    )
    coq_finite_registered_atomic_truth_condition_witness_transition_witness_count = len(
        re.findall(
            r"^Theorem finite_registered_atomic_truth_condition_witness_transition_\d+_projected :",
            coq,
            re.MULTILINE,
        )
    )
    lean_finite_registered_atomic_truth_condition_witness_transition_truth_count = len(
        re.findall(
            r"^theorem finite_registered_atomic_truth_condition_witness_transition_\d+_truth_projected :",
            lean,
            re.MULTILINE,
        )
    )
    coq_finite_registered_atomic_truth_condition_witness_transition_truth_count = len(
        re.findall(
            r"^Theorem finite_registered_atomic_truth_condition_witness_transition_\d+_truth_projected :",
            coq,
            re.MULTILINE,
        )
    )
    lean_finite_registered_atomic_truth_condition_witness_transition_atomic_count = len(
        re.findall(
            r"^theorem finite_registered_atomic_truth_condition_witness_transition_\d+_atomic_projected :",
            lean,
            re.MULTILINE,
        )
    )
    coq_finite_registered_atomic_truth_condition_witness_transition_atomic_count = len(
        re.findall(
            r"^Theorem finite_registered_atomic_truth_condition_witness_transition_\d+_atomic_projected :",
            coq,
            re.MULTILINE,
        )
    )
    lean_finite_registered_atomic_truth_condition_evidence_lexical_evidence_count = len(
        re.findall(
            r"^theorem finite_registered_atomic_truth_condition_evidence_lexical_\d+_evidence_projected :",
            lean,
            re.MULTILINE,
        )
    )
    coq_finite_registered_atomic_truth_condition_evidence_lexical_evidence_count = len(
        re.findall(
            r"^Theorem finite_registered_atomic_truth_condition_evidence_lexical_\d+_evidence_projected :",
            coq,
            re.MULTILINE,
        )
    )
    lean_finite_registered_atomic_truth_condition_evidence_lexical_truth_count = len(
        re.findall(
            r"^theorem finite_registered_atomic_truth_condition_evidence_lexical_\d+_truth_from_evidence_projected :",
            lean,
            re.MULTILINE,
        )
    )
    coq_finite_registered_atomic_truth_condition_evidence_lexical_truth_count = len(
        re.findall(
            r"^Theorem finite_registered_atomic_truth_condition_evidence_lexical_\d+_truth_from_evidence_projected :",
            coq,
            re.MULTILINE,
        )
    )
    lean_finite_registered_atomic_truth_condition_evidence_lexical_atomic_count = len(
        re.findall(
            r"^theorem finite_registered_atomic_truth_condition_evidence_lexical_\d+_atomic_from_evidence_projected :",
            lean,
            re.MULTILINE,
        )
    )
    coq_finite_registered_atomic_truth_condition_evidence_lexical_atomic_count = len(
        re.findall(
            r"^Theorem finite_registered_atomic_truth_condition_evidence_lexical_\d+_atomic_from_evidence_projected :",
            coq,
            re.MULTILINE,
        )
    )
    lean_finite_registered_atomic_truth_condition_evidence_transition_evidence_count = len(
        re.findall(
            r"^theorem finite_registered_atomic_truth_condition_evidence_transition_\d+_evidence_projected :",
            lean,
            re.MULTILINE,
        )
    )
    coq_finite_registered_atomic_truth_condition_evidence_transition_evidence_count = len(
        re.findall(
            r"^Theorem finite_registered_atomic_truth_condition_evidence_transition_\d+_evidence_projected :",
            coq,
            re.MULTILINE,
        )
    )
    lean_finite_registered_atomic_truth_condition_evidence_transition_truth_count = len(
        re.findall(
            r"^theorem finite_registered_atomic_truth_condition_evidence_transition_\d+_truth_from_evidence_projected :",
            lean,
            re.MULTILINE,
        )
    )
    coq_finite_registered_atomic_truth_condition_evidence_transition_truth_count = len(
        re.findall(
            r"^Theorem finite_registered_atomic_truth_condition_evidence_transition_\d+_truth_from_evidence_projected :",
            coq,
            re.MULTILINE,
        )
    )
    lean_finite_registered_atomic_truth_condition_evidence_transition_atomic_count = len(
        re.findall(
            r"^theorem finite_registered_atomic_truth_condition_evidence_transition_\d+_atomic_from_evidence_projected :",
            lean,
            re.MULTILINE,
        )
    )
    coq_finite_registered_atomic_truth_condition_evidence_transition_atomic_count = len(
        re.findall(
            r"^Theorem finite_registered_atomic_truth_condition_evidence_transition_\d+_atomic_from_evidence_projected :",
            coq,
            re.MULTILINE,
        )
    )
    lean_finite_registered_atomic_truth_condition_evidence_source_alignment_lexical_source_count = len(
        re.findall(
            r"^theorem finite_registered_atomic_truth_condition_evidence_source_alignment_lexical_\d+_source_evidence_projected :",
            lean,
            re.MULTILINE,
        )
    )
    coq_finite_registered_atomic_truth_condition_evidence_source_alignment_lexical_source_count = len(
        re.findall(
            r"^Theorem finite_registered_atomic_truth_condition_evidence_source_alignment_lexical_\d+_source_evidence_projected :",
            coq,
            re.MULTILINE,
        )
    )
    lean_finite_registered_atomic_truth_condition_evidence_source_alignment_lexical_truth_count = len(
        re.findall(
            r"^theorem finite_registered_atomic_truth_condition_evidence_source_alignment_lexical_\d+_truth_projected :",
            lean,
            re.MULTILINE,
        )
    )
    coq_finite_registered_atomic_truth_condition_evidence_source_alignment_lexical_truth_count = len(
        re.findall(
            r"^Theorem finite_registered_atomic_truth_condition_evidence_source_alignment_lexical_\d+_truth_projected :",
            coq,
            re.MULTILINE,
        )
    )
    lean_finite_registered_atomic_truth_condition_evidence_source_alignment_lexical_atomic_count = len(
        re.findall(
            r"^theorem finite_registered_atomic_truth_condition_evidence_source_alignment_lexical_\d+_atomic_projected :",
            lean,
            re.MULTILINE,
        )
    )
    coq_finite_registered_atomic_truth_condition_evidence_source_alignment_lexical_atomic_count = len(
        re.findall(
            r"^Theorem finite_registered_atomic_truth_condition_evidence_source_alignment_lexical_\d+_atomic_projected :",
            coq,
            re.MULTILINE,
        )
    )
    lean_finite_registered_atomic_truth_condition_evidence_source_alignment_transition_source_count = len(
        re.findall(
            r"^theorem finite_registered_atomic_truth_condition_evidence_source_alignment_transition_\d+_source_evidence_projected :",
            lean,
            re.MULTILINE,
        )
    )
    coq_finite_registered_atomic_truth_condition_evidence_source_alignment_transition_source_count = len(
        re.findall(
            r"^Theorem finite_registered_atomic_truth_condition_evidence_source_alignment_transition_\d+_source_evidence_projected :",
            coq,
            re.MULTILINE,
        )
    )
    lean_finite_registered_atomic_truth_condition_evidence_source_alignment_transition_truth_count = len(
        re.findall(
            r"^theorem finite_registered_atomic_truth_condition_evidence_source_alignment_transition_\d+_truth_projected :",
            lean,
            re.MULTILINE,
        )
    )
    coq_finite_registered_atomic_truth_condition_evidence_source_alignment_transition_truth_count = len(
        re.findall(
            r"^Theorem finite_registered_atomic_truth_condition_evidence_source_alignment_transition_\d+_truth_projected :",
            coq,
            re.MULTILINE,
        )
    )
    lean_finite_registered_atomic_truth_condition_evidence_source_alignment_transition_atomic_count = len(
        re.findall(
            r"^theorem finite_registered_atomic_truth_condition_evidence_source_alignment_transition_\d+_atomic_projected :",
            lean,
            re.MULTILINE,
        )
    )
    coq_finite_registered_atomic_truth_condition_evidence_source_alignment_transition_atomic_count = len(
        re.findall(
            r"^Theorem finite_registered_atomic_truth_condition_evidence_source_alignment_transition_\d+_atomic_projected :",
            coq,
            re.MULTILINE,
        )
    )
    lean_finite_registered_atomic_truth_condition_independent_suite_alignment_lexical_truth_count = len(
        re.findall(
            r"^theorem finite_registered_atomic_truth_condition_independent_suite_alignment_lexical_\d+_truth_projected :",
            lean,
            re.MULTILINE,
        )
    )
    coq_finite_registered_atomic_truth_condition_independent_suite_alignment_lexical_truth_count = len(
        re.findall(
            r"^Theorem finite_registered_atomic_truth_condition_independent_suite_alignment_lexical_\d+_truth_projected :",
            coq,
            re.MULTILINE,
        )
    )
    lean_finite_registered_atomic_truth_condition_independent_suite_alignment_lexical_atomic_count = len(
        re.findall(
            r"^theorem finite_registered_atomic_truth_condition_independent_suite_alignment_lexical_\d+_atomic_projected :",
            lean,
            re.MULTILINE,
        )
    )
    coq_finite_registered_atomic_truth_condition_independent_suite_alignment_lexical_atomic_count = len(
        re.findall(
            r"^Theorem finite_registered_atomic_truth_condition_independent_suite_alignment_lexical_\d+_atomic_projected :",
            coq,
            re.MULTILINE,
        )
    )
    lean_finite_registered_atomic_truth_condition_independent_suite_alignment_transition_truth_count = len(
        re.findall(
            r"^theorem finite_registered_atomic_truth_condition_independent_suite_alignment_transition_\d+_truth_projected :",
            lean,
            re.MULTILINE,
        )
    )
    coq_finite_registered_atomic_truth_condition_independent_suite_alignment_transition_truth_count = len(
        re.findall(
            r"^Theorem finite_registered_atomic_truth_condition_independent_suite_alignment_transition_\d+_truth_projected :",
            coq,
            re.MULTILINE,
        )
    )
    lean_finite_registered_atomic_truth_condition_independent_suite_alignment_transition_atomic_count = len(
        re.findall(
            r"^theorem finite_registered_atomic_truth_condition_independent_suite_alignment_transition_\d+_atomic_projected :",
            lean,
            re.MULTILINE,
        )
    )
    coq_finite_registered_atomic_truth_condition_independent_suite_alignment_transition_atomic_count = len(
        re.findall(
            r"^Theorem finite_registered_atomic_truth_condition_independent_suite_alignment_transition_\d+_atomic_projected :",
            coq,
            re.MULTILINE,
        )
    )
    lean_finite_registered_atomic_truth_condition_discharge_lexical_truth_count = len(
        re.findall(
            r"^theorem finite_registered_atomic_truth_condition_discharge_lexical_\d+_truth_projected :",
            lean,
            re.MULTILINE,
        )
    )
    coq_finite_registered_atomic_truth_condition_discharge_lexical_truth_count = len(
        re.findall(
            r"^Theorem finite_registered_atomic_truth_condition_discharge_lexical_\d+_truth_projected :",
            coq,
            re.MULTILINE,
        )
    )
    lean_finite_registered_atomic_truth_condition_discharge_lexical_atomic_count = len(
        re.findall(
            r"^theorem finite_registered_atomic_truth_condition_discharge_lexical_\d+_atomic_projected :",
            lean,
            re.MULTILINE,
        )
    )
    coq_finite_registered_atomic_truth_condition_discharge_lexical_atomic_count = len(
        re.findall(
            r"^Theorem finite_registered_atomic_truth_condition_discharge_lexical_\d+_atomic_projected :",
            coq,
            re.MULTILINE,
        )
    )
    lean_finite_registered_atomic_truth_condition_discharge_transition_truth_count = len(
        re.findall(
            r"^theorem finite_registered_atomic_truth_condition_discharge_transition_\d+_truth_projected :",
            lean,
            re.MULTILINE,
        )
    )
    coq_finite_registered_atomic_truth_condition_discharge_transition_truth_count = len(
        re.findall(
            r"^Theorem finite_registered_atomic_truth_condition_discharge_transition_\d+_truth_projected :",
            coq,
            re.MULTILINE,
        )
    )
    lean_finite_registered_atomic_truth_condition_discharge_transition_atomic_count = len(
        re.findall(
            r"^theorem finite_registered_atomic_truth_condition_discharge_transition_\d+_atomic_projected :",
            lean,
            re.MULTILINE,
        )
    )
    coq_finite_registered_atomic_truth_condition_discharge_transition_atomic_count = len(
        re.findall(
            r"^Theorem finite_registered_atomic_truth_condition_discharge_transition_\d+_atomic_projected :",
            coq,
            re.MULTILINE,
        )
    )
    lean_finite_registered_atomic_truth_condition_typed_lexical_atom_count = len(
        re.findall(
            r"^def finite_registered_atomic_truth_condition_typed_lexical_atom_\d+(?:\s|:)",
            lean,
            re.MULTILINE,
        )
    )
    coq_finite_registered_atomic_truth_condition_typed_lexical_atom_count = len(
        re.findall(
            r"^Definition finite_registered_atomic_truth_condition_typed_lexical_atom_\d+(?:\s|:)",
            coq,
            re.MULTILINE,
        )
    )
    lean_finite_registered_atomic_truth_condition_typed_lexical_truth_count = len(
        re.findall(
            r"^theorem finite_registered_atomic_truth_condition_typed_discharge_lexical_\d+_projected :",
            lean,
            re.MULTILINE,
        )
    )
    coq_finite_registered_atomic_truth_condition_typed_lexical_truth_count = len(
        re.findall(
            r"^Theorem finite_registered_atomic_truth_condition_typed_discharge_lexical_\d+_projected :",
            coq,
            re.MULTILINE,
        )
    )
    lean_finite_registered_atomic_truth_condition_typed_lexical_atomic_count = len(
        re.findall(
            r"^theorem finite_registered_atomic_truth_condition_typed_discharge_lexical_\d+_atomic_projected :",
            lean,
            re.MULTILINE,
        )
    )
    coq_finite_registered_atomic_truth_condition_typed_lexical_atomic_count = len(
        re.findall(
            r"^Theorem finite_registered_atomic_truth_condition_typed_discharge_lexical_\d+_atomic_projected :",
            coq,
            re.MULTILINE,
        )
    )
    lean_finite_registered_atomic_truth_condition_typed_transition_atom_count = len(
        re.findall(
            r"^def finite_registered_atomic_truth_condition_typed_transition_atom_\d+(?:\s|:)",
            lean,
            re.MULTILINE,
        )
    )
    coq_finite_registered_atomic_truth_condition_typed_transition_atom_count = len(
        re.findall(
            r"^Definition finite_registered_atomic_truth_condition_typed_transition_atom_\d+(?:\s|:)",
            coq,
            re.MULTILINE,
        )
    )
    lean_finite_registered_atomic_truth_condition_typed_transition_truth_count = len(
        re.findall(
            r"^theorem finite_registered_atomic_truth_condition_typed_discharge_transition_\d+_projected :",
            lean,
            re.MULTILINE,
        )
    )
    coq_finite_registered_atomic_truth_condition_typed_transition_truth_count = len(
        re.findall(
            r"^Theorem finite_registered_atomic_truth_condition_typed_discharge_transition_\d+_projected :",
            coq,
            re.MULTILINE,
        )
    )
    lean_finite_registered_atomic_truth_condition_typed_transition_atomic_count = len(
        re.findall(
            r"^theorem finite_registered_atomic_truth_condition_typed_discharge_transition_\d+_atomic_projected :",
            lean,
            re.MULTILINE,
        )
    )
    coq_finite_registered_atomic_truth_condition_typed_transition_atomic_count = len(
        re.findall(
            r"^Theorem finite_registered_atomic_truth_condition_typed_discharge_transition_\d+_atomic_projected :",
            coq,
            re.MULTILINE,
        )
    )

    checks = {
        "lean declarations": "constant Entity : Type" in lean,
        "coq declarations": "Parameter Entity : Type." in coq,
        "lean state declarations": "constant State : Type" in lean,
        "coq state declarations": "Parameter State : Type." in coq,
        "lean state scale declarations": "constant StateScale : Type" in lean,
        "coq state scale declarations": "Parameter StateScale : Type." in coq,
        "lean PropT alias": "abbrev PropT : Type := Prop" in lean,
        "coq PropT alias": "Definition PropT : Type := Prop." in coq,
        "lean indexed modifier sequence type": "constant ModifierSeq : Nat -> Type" in lean,
        "coq indexed modifier sequence type": "Parameter ModifierSeq : nat -> Type." in coq,
        "lean indexed modifier sequence constructor": (
            "constant mods_cons : (n : Nat) -> Adv -> ModifierSeq n -> ModifierSeq (Nat.succ n)"
            in lean
        ),
        "coq indexed modifier sequence constructor": (
            "Parameter mods_cons : forall n : nat, Adv -> ModifierSeq n -> ModifierSeq (S n)."
            in coq
        ),
        "lean check commands": "#check example_4" in lean,
        "coq check commands": "Check example_4." in coq,
        "lean semantic preservation inductive relation": (
            "inductive SemanticPreservation : (A : Type) -> A -> Prop where" in lean
            and "SemanticPreservation.preserve_repeat" in lean
            and "SemanticPreservation.preserve_sigma_Food" in lean
        ),
        "coq semantic preservation inductive relation": (
            "Inductive SemanticPreservation : forall A : Type, A -> Prop :=" in coq
            and "preserve_repeat : forall n : nat" in coq
            and "preserve_sigma_Food : forall P : Food -> Prop" in coq
        ),
        "lean model interpretability inductive relation": (
            "inductive ModelInterpretable : (A : Type) -> A -> Prop where" in lean
            and "| model_repeat : (n : Nat)" in lean
            and "| model_sigma_Food : (P : Food -> Prop)" in lean
        ),
        "coq model interpretability inductive relation": (
            "Inductive ModelInterpretable : forall A : Type, A -> Prop :=" in coq
            and "model_repeat : forall n : nat" in coq
            and "model_sigma_Food : forall P : Food -> Prop" in coq
        ),
        "lean syntax-directed truth inductive relation": (
            "inductive SyntaxDirectedTruth : (A : Type) -> A -> Prop where" in lean
            and "| syntax_truth_repeat : (n : Nat)" in lean
            and "| syntax_truth_sigma_Food : (P : Food -> Prop)" in lean
        ),
        "coq syntax-directed truth inductive relation": (
            "Inductive SyntaxDirectedTruth : forall A : Type, A -> Prop :=" in coq
            and "syntax_truth_repeat : forall n : nat" in coq
            and "syntax_truth_sigma_Food : forall P : Food -> Prop" in coq
        ),
        "lean preservation to model boundary theorem": (
            "theorem semantic_preservation_model_interpretable :" in lean
            and "SemanticPreservation A term -> ModelInterpretable A term" in lean
        ),
        "coq preservation to model boundary theorem": (
            "Theorem semantic_preservation_model_interpretable :" in coq
            and "SemanticPreservation A term -> ModelInterpretable A term." in coq
            and "induction H; constructor; assumption." in coq
        ),
        "lean preservation to syntax-directed truth boundary theorem": (
            "theorem semantic_preservation_syntax_directed_truth :" in lean
            and "SemanticPreservation A term -> SyntaxDirectedTruth A term" in lean
        ),
        "coq preservation to syntax-directed truth boundary theorem": (
            "Theorem semantic_preservation_syntax_directed_truth :" in coq
            and "SemanticPreservation A term -> SyntaxDirectedTruth A term." in coq
            and coq.count("induction H; constructor; assumption.") >= 2
        ),
        "lean semantic model denotation record": (
            "structure SemanticModel : Type where" in lean
            and "model_denotes : (A : Type) -> A -> Prop" in lean
            and "denote_repeat : (n : Nat)" in lean
            and "denote_sigma_Food : (P : Food -> Prop)" in lean
        ),
        "coq semantic model denotation record": (
            "Record SemanticModel : Type := {" in coq
            and "model_denotes : forall A : Type, A -> Prop;" in coq
            and "denote_repeat : forall n : nat" in coq
            and "denote_sigma_Food : forall P : Food -> Prop" in coq
        ),
        "lean model to denotation soundness theorem": (
            "theorem model_interpretable_denotational_sound :" in lean
            and "ModelInterpretable A term -> M.model_denotes A term" in lean
        ),
        "coq model to denotation soundness theorem": (
            "Theorem model_interpretable_denotational_sound :" in coq
            and "ModelInterpretable A term -> model_denotes M A term." in coq
            and "induction H; eauto using" in coq
            and "denote_cause." in coq
        ),
        "lean truth condition spec": (
            "structure TruthConditionSpec : Type where" in lean
            and "truth_denotes : (A : Type) -> A -> Prop" in lean
            and "truth_repeat : (n : Nat)" in lean
            and "truth_sigma_Food : (P : Food -> Prop)" in lean
        ),
        "coq truth condition spec": (
            "Record TruthConditionSpec : Type := {" in coq
            and "truth_denotes : forall A : Type, A -> Prop;" in coq
            and "truth_repeat : forall n : nat" in coq
            and "truth_sigma_Food : forall P : Food -> Prop" in coq
        ),
        "lean truth conditions to semantic model bridge": (
            "def semantic_model_from_truth_conditions (T : TruthConditionSpec) : SemanticModel := {"
            in lean
            and "model_denotes := T.truth_denotes" in lean
            and "theorem truth_conditions_induce_denotational_soundness :" in lean
            and "ModelInterpretable A term -> T.truth_denotes A term" in lean
        ),
        "coq truth conditions to semantic model bridge": (
            "Definition semantic_model_from_truth_conditions (T : TruthConditionSpec) : SemanticModel := {|"
            in coq
            and "model_denotes := truth_denotes T;" in coq
            and "Theorem truth_conditions_induce_denotational_soundness :" in coq
            and "ModelInterpretable A term -> truth_denotes T A term." in coq
        ),
        "lean tautological truth condition instance": (
            "def tautological_truth_denotes : (A : Type) -> A -> Prop :="
            in lean
            and "def tautological_truth_conditions : TruthConditionSpec := {"
            in lean
            and "def tautological_semantic_model : SemanticModel :="
            in lean
            and "theorem tautological_truth_condition_spec_exists :" in lean
            and "theorem tautological_truth_conditions_denote_model_interpretable :"
            in lean
        ),
        "coq tautological truth condition instance": (
            "Definition tautological_truth_denotes : forall A : Type, A -> Prop :="
            in coq
            and "Definition tautological_truth_conditions : TruthConditionSpec := {|"
            in coq
            and "Definition tautological_semantic_model : SemanticModel :="
            in coq
            and "Theorem tautological_truth_condition_spec_exists :" in coq
            and "Theorem tautological_truth_conditions_denote_model_interpretable :"
            in coq
        ),
        "lean structural truth condition instance": (
            "def structural_truth_denotes : (A : Type) -> A -> Prop :="
            in lean
            and "  ModelInterpretable" in lean
            and "def structural_truth_conditions : TruthConditionSpec := {"
            in lean
            and "truth_denotes := structural_truth_denotes" in lean
            and "def structural_semantic_model : SemanticModel :="
            in lean
            and "theorem structural_truth_condition_spec_exists :" in lean
            and "theorem structural_truth_conditions_denote_model_interpretable :"
            in lean
        ),
        "coq structural truth condition instance": (
            "Definition structural_truth_denotes : forall A : Type, A -> Prop :="
            in coq
            and "  ModelInterpretable." in coq
            and "Definition structural_truth_conditions : TruthConditionSpec := {|"
            in coq
            and "truth_denotes := structural_truth_denotes" in coq
            and "Definition structural_semantic_model : SemanticModel :="
            in coq
            and "Theorem structural_truth_condition_spec_exists :" in coq
            and "Theorem structural_truth_conditions_denote_model_interpretable :"
            in coq
        ),
        "lean concrete truth condition kernel bridge": (
            "structure ConcreteTruthConditionKernel : Type where" in lean
            and "kernel_denotes : (A : Type) -> A -> Prop" in lean
            and "lexical_truth_eat_application : (n : Nat)" in lean
            and "quantifier_truth_sigma_Food : (P : Food -> Prop)" in lean
            and "repetition_truth : (n : Nat)" in lean
            and "temporal_truth_after_T : (marker : Entity)" in lean
            and "polarity_truth_not_T : (body : PropT)" in lean
            and "transition_truth : (theme : Entity)" in lean
            and "cause_truth : (causer : Entity)" in lean
            and "def truth_conditions_from_concrete_kernel " in lean
            and "theorem concrete_kernel_truth_condition_spec_exists :" in lean
            and "theorem concrete_kernel_induces_truth_condition_soundness :" in lean
        ),
        "coq concrete truth condition kernel bridge": (
            "Record ConcreteTruthConditionKernel : Type := {" in coq
            and "kernel_denotes : forall A : Type, A -> Prop;" in coq
            and "lexical_truth_eat_application : forall n : nat" in coq
            and "quantifier_truth_sigma_Food : forall P : Food -> Prop" in coq
            and "repetition_truth : forall n : nat" in coq
            and "temporal_truth_after_T : forall marker : Entity" in coq
            and "polarity_truth_not_T : forall body : PropT" in coq
            and "transition_truth : forall theme : Entity" in coq
            and "cause_truth : forall causer : Entity" in coq
            and "Definition truth_conditions_from_concrete_kernel "
            in coq
            and "Theorem concrete_kernel_truth_condition_spec_exists :" in coq
            and "Theorem concrete_kernel_induces_truth_condition_soundness :"
            in coq
        ),
        "lean independent truth-condition obligation ledger": (
            "structure IndependentTruthConditionObligationLedger : Type where"
            in lean
            and "ledger_denotes : (A : Type) -> A -> Prop" in lean
            and "ledger_kernel : ConcreteTruthConditionKernel" in lean
            and "ledger_truth_conditions : TruthConditionSpec" in lean
            and "ledger_lexical_truth_eat_obligation : (n : Nat)" in lean
            and "ledger_quantifier_truth_sigma_Food_obligation : (P : Food -> Prop)"
            in lean
            and "ledger_repetition_truth_obligation : (n : Nat)" in lean
            and "ledger_temporal_truth_after_T_obligation : (marker : Entity)"
            in lean
            and "ledger_polarity_truth_not_T_obligation : (body : PropT)"
            in lean
            and "ledger_transition_truth_obligation : (theme : Entity)" in lean
            and "ledger_cause_truth_obligation : (causer : Entity)" in lean
            and "def independent_truth_condition_obligation_ledger "
            in lean
            and "theorem independent_truth_condition_obligation_ledger_exists :"
            in lean
            and "theorem independent_truth_condition_obligation_ledger_induces_truth_conditions :"
            in lean
            and "theorem independent_truth_condition_obligation_ledger_truth_conditions_sound :"
            in lean
        ),
        "coq independent truth-condition obligation ledger": (
            "Record IndependentTruthConditionObligationLedger : Type := {"
            in coq
            and "ledger_denotes : forall A : Type, A -> Prop;" in coq
            and "ledger_kernel : ConcreteTruthConditionKernel;" in coq
            and "ledger_truth_conditions : TruthConditionSpec;" in coq
            and "ledger_lexical_truth_eat_obligation : forall n : nat" in coq
            and "ledger_quantifier_truth_sigma_Food_obligation : forall P : Food -> Prop"
            in coq
            and "ledger_repetition_truth_obligation : forall n : nat" in coq
            and "ledger_temporal_truth_after_T_obligation : forall marker : Entity"
            in coq
            and "ledger_polarity_truth_not_T_obligation : forall body : PropT"
            in coq
            and "ledger_transition_truth_obligation : forall theme : Entity" in coq
            and "ledger_cause_truth_obligation : forall causer : Entity" in coq
            and "Definition independent_truth_condition_obligation_ledger"
            in coq
            and "Theorem independent_truth_condition_obligation_ledger_exists :"
            in coq
            and "Theorem independent_truth_condition_obligation_ledger_induces_truth_conditions :"
            in coq
            and "Theorem independent_truth_condition_obligation_ledger_truth_conditions_sound :"
            in coq
        ),
        "lean evidence-backed truth-condition sources": (
            "constant TruthEvidence : Prop -> Type" in lean
            and "constant truth_evidence_sound : (P : Prop) -> TruthEvidence P -> P"
            in lean
            and "constant truth_evidence_intro : (P : Prop) -> P -> TruthEvidence P"
            in lean
            and "structure EvidenceBackedTruthConditionSources : Type where"
            in lean
            and "evidence_denotes : (A : Type) -> A -> Prop" in lean
            and "evidence_lexical_truth_eat_application : (n : Nat)" in lean
            and "evidence_quantifier_truth_sigma_Food : (P : Food -> Prop)"
            in lean
            and "evidence_repetition_truth : (n : Nat)" in lean
            and "evidence_temporal_truth_after_T : (marker : Entity)"
            in lean
            and "evidence_polarity_truth_not_T : (body : PropT)" in lean
            and "evidence_transition_truth : (theme : Entity)" in lean
            and "evidence_cause_truth : (causer : Entity)" in lean
            and "def concrete_kernel_from_evidence_sources " in lean
            and "def evidence_backed_truth_condition_ledger " in lean
            and "theorem evidence_backed_truth_condition_sources_induce_kernel :"
            in lean
            and "theorem evidence_backed_truth_condition_sources_induce_truth_conditions :"
            in lean
            and "theorem evidence_backed_truth_condition_sources_sound :"
            in lean
        ),
        "coq evidence-backed truth-condition sources": (
            "Parameter TruthEvidence : Prop -> Type." in coq
            and "Parameter truth_evidence_sound : forall P : Prop, TruthEvidence P -> P."
            in coq
            and "Parameter truth_evidence_intro : forall P : Prop, P -> TruthEvidence P."
            in coq
            and "Record EvidenceBackedTruthConditionSources : Type := {"
            in coq
            and "evidence_denotes : forall A : Type, A -> Prop;" in coq
            and "evidence_lexical_truth_eat_application : forall n : nat" in coq
            and "evidence_quantifier_truth_sigma_Food : forall P : Food -> Prop"
            in coq
            and "evidence_repetition_truth : forall n : nat" in coq
            and "evidence_temporal_truth_after_T : forall marker : Entity"
            in coq
            and "evidence_polarity_truth_not_T : forall body : PropT" in coq
            and "evidence_transition_truth : forall theme : Entity" in coq
            and "evidence_cause_truth : forall causer : Entity" in coq
            and "Definition concrete_kernel_from_evidence_sources" in coq
            and "Definition evidence_backed_truth_condition_ledger" in coq
            and "Theorem evidence_backed_truth_condition_sources_induce_kernel :"
            in coq
            and "Theorem evidence_backed_truth_condition_sources_induce_truth_conditions :"
            in coq
            and "Theorem evidence_backed_truth_condition_sources_sound :" in coq
        ),
        "lean primitive truth assumption kernel instance": (
            "structure PrimitiveTruthAssumptions : Type where" in lean
            and "primitive_denotes : (A : Type) -> A -> Prop" in lean
            and "primitive_lexical_truth_eat_application : (n : Nat)" in lean
            and "primitive_quantifier_truth_sigma_Food : (P : Food -> Prop)" in lean
            and "primitive_temporal_truth_after_T : (marker : Entity)" in lean
            and "constant primitive_truth_assumptions : PrimitiveTruthAssumptions" in lean
            and "def primitive_truth_kernel : ConcreteTruthConditionKernel := {" in lean
            and "kernel_denotes := primitive_truth_assumptions.primitive_denotes" in lean
            and "def primitive_truth_conditions_from_kernel : TruthConditionSpec :=" in lean
            and "theorem primitive_truth_kernel_exists :" in lean
            and "theorem primitive_truth_kernel_denotes_primitive_assumptions :" in lean
            and "theorem primitive_truth_kernel_denotes_model_interpretable :" in lean
        ),
        "coq primitive truth assumption kernel instance": (
            "Record PrimitiveTruthAssumptions : Type := {" in coq
            and "primitive_denotes : forall A : Type, A -> Prop;" in coq
            and "primitive_lexical_truth_eat_application : forall n : nat" in coq
            and "primitive_quantifier_truth_sigma_Food : forall P : Food -> Prop" in coq
            and "primitive_temporal_truth_after_T : forall marker : Entity" in coq
            and "Parameter primitive_truth_assumptions : PrimitiveTruthAssumptions." in coq
            and "Definition primitive_truth_kernel : ConcreteTruthConditionKernel := {|" in coq
            and "kernel_denotes := primitive_denotes primitive_truth_assumptions" in coq
            and "Definition primitive_truth_conditions_from_kernel : TruthConditionSpec :=" in coq
            and "Theorem primitive_truth_kernel_exists :" in coq
            and "Theorem primitive_truth_kernel_denotes_primitive_assumptions :" in coq
            and "Theorem primitive_truth_kernel_denotes_model_interpretable :" in coq
        ),
        "lean atomic closure truth kernel instance": (
            "inductive AtomicBaseTruth : (A : Type) -> A -> Prop where" in lean
            and "| atomic_base_truth_eat_application : (n : Nat)" in lean
            and "| atomic_base_truth_transition : (theme : Entity)" in lean
            and "structure LexicalAtomTruthAssumptions (D : (A : Type) -> A -> Prop) : Type where"
            in lean
            and "lexical_atom_truth_eat_application : (n : Nat)" in lean
            and "structure TransitionAtomTruthAssumptions (D : (A : Type) -> A -> Prop) : Type where"
            in lean
            and "transition_atom_truth : (theme : Entity)" in lean
            and "structure LexicalTransitionTruthAssumptions : Type where" in lean
            and "def lexical_atom_truth_assumptions_from_atomic_base :" in lean
            and "def transition_atom_truth_assumptions_from_atomic_base :" in lean
            and "def lexical_transition_truth_assumptions_from_atomic_base :"
            in lean
            and "theorem lexical_atom_truth_assumptions_from_atomic_base_exists :"
            in lean
            and "theorem transition_atom_truth_assumptions_from_atomic_base_exists :"
            in lean
            and "theorem lexical_transition_truth_assumptions_from_atomic_base_exists :"
            in lean
            and "structure LexicalTransitionTruthModel : Type where" in lean
            and "atom_model_denotes : (A : Type) -> A -> Prop" in lean
            and "model_lexical_truth_eat_application : (n : Nat)" in lean
            and "def lexical_transition_truth_model_from_assumptions"
            in lean
            and "def lexical_transition_truth_model : LexicalTransitionTruthModel :="
            in lean
            and "theorem lexical_transition_truth_model_from_assumptions_exists :"
            in lean
            and "theorem lexical_transition_truth_model_exists :" in lean
            and "theorem lexical_transition_truth_model_denotes_atomic_base_truth :"
            in lean
            and "structure AtomicValuationSpec : Type where" in lean
            and "atomic_valuation_denotes : (A : Type) -> A -> Prop" in lean
            and "valuation_lexical_truth_eat_application : (n : Nat)" in lean
            and "def atomic_valuation_spec_from_lexical_transition_model : AtomicValuationSpec := {"
            in lean
            and "def atomic_base_valuation_spec : AtomicValuationSpec :=" in lean
            and "theorem atomic_valuation_spec_from_lexical_transition_model_exists :"
            in lean
            and "theorem atomic_base_valuation_spec_exists :" in lean
            and "theorem atomic_base_valuation_denotes_atomic_base_truth :" in lean
            and "structure AtomicTruthFacts : Type where" in lean
            and "atomic_lexical_truth_eat_application : (n : Nat)" in lean
            and "AtomicBaseTruth Prop (eat n mods arg1 arg2)" in lean
            and "def atomic_truth_facts_from_atomic_base_valuation : AtomicTruthFacts := {"
            in lean
            and "def atomic_truth_facts : AtomicTruthFacts :=" in lean
            and "theorem atomic_truth_facts_from_atomic_base_valuation_exists :"
            in lean
            and "AtomicBaseTruth.atomic_base_truth_eat_application" in lean
            and "AtomicBaseTruth.atomic_base_truth_transition" in lean
            and "inductive AtomicClosureTruth : (A : Type) -> A -> Prop where"
            in lean
            and "| atomic_closure_truth_repeat : (n : Nat)" in lean
            and "theorem model_interpretable_atomic_closure_truth :" in lean
            and "def atomic_closure_truth_kernel_denotes : (A : Type) -> A -> Prop :="
            in lean
            and "def atomic_closure_truth_kernel : ConcreteTruthConditionKernel := {"
            in lean
            and "kernel_denotes := atomic_closure_truth_kernel_denotes" in lean
            and "def atomic_closure_truth_conditions_from_kernel : TruthConditionSpec :="
            in lean
            and "theorem atomic_closure_truth_kernel_exists :" in lean
            and "theorem atomic_closure_truth_kernel_denotes_atomic_closure_truth :"
            in lean
            and "def atomic_closure_truth_conditions : TruthConditionSpec :="
            in lean
            and "theorem atomic_closure_truth_conditions_exists :" in lean
            and "theorem atomic_closure_truth_conditions_denote_atomic_closure_truth :"
            in lean
        ),
        "lean atomic closure evidence-backed source instance": (
            "def atomic_closure_evidence_backed_truth_sources : "
            "EvidenceBackedTruthConditionSources := {" in lean
            and "evidence_denotes := AtomicClosureTruth" in lean
            and "def atomic_closure_evidence_backed_truth_kernel : "
            "ConcreteTruthConditionKernel :=" in lean
            and "def atomic_closure_evidence_backed_truth_ledger : "
            "IndependentTruthConditionObligationLedger :=" in lean
            and "theorem atomic_closure_evidence_backed_truth_sources_exist :"
            in lean
            and "theorem atomic_closure_evidence_backed_truth_kernel_exists :"
            in lean
            and "theorem atomic_closure_evidence_backed_truth_ledger_exists :"
            in lean
            and "theorem atomic_closure_evidence_backed_truth_sources_sound :"
            in lean
            and "theorem example_4_atomic_closure_evidence_backed_truth_condition_sound :"
            in lean
        ),
        "coq atomic closure truth kernel instance": (
            "Inductive AtomicBaseTruth : forall A : Type, A -> Prop :=" in coq
            and "atomic_base_truth_eat_application : forall n : nat" in coq
            and "atomic_base_truth_transition : forall theme : Entity" in coq
            and "Record LexicalAtomTruthAssumptions (D : forall A : Type, A -> Prop) : Type := {"
            in coq
            and "lexical_atom_truth_eat_application : forall n : nat" in coq
            and "Record TransitionAtomTruthAssumptions (D : forall A : Type, A -> Prop) : Type := {"
            in coq
            and "transition_atom_truth : forall theme : Entity" in coq
            and "Record LexicalTransitionTruthAssumptions : Type := {" in coq
            and "Definition lexical_atom_truth_assumptions_from_atomic_base :"
            in coq
            and "Definition transition_atom_truth_assumptions_from_atomic_base :"
            in coq
            and "Definition lexical_transition_truth_assumptions_from_atomic_base :"
            in coq
            and "Theorem lexical_atom_truth_assumptions_from_atomic_base_exists :"
            in coq
            and "Theorem transition_atom_truth_assumptions_from_atomic_base_exists :"
            in coq
            and "Theorem lexical_transition_truth_assumptions_from_atomic_base_exists :"
            in coq
            and "Record LexicalTransitionTruthModel : Type := {" in coq
            and "atom_model_denotes : forall A : Type, A -> Prop;" in coq
            and "model_lexical_truth_eat_application : forall n : nat" in coq
            and "Definition lexical_transition_truth_model_from_assumptions" in coq
            and "Definition lexical_transition_truth_model : LexicalTransitionTruthModel :="
            in coq
            and "Theorem lexical_transition_truth_model_from_assumptions_exists :"
            in coq
            and "Theorem lexical_transition_truth_model_exists :" in coq
            and "Theorem lexical_transition_truth_model_denotes_atomic_base_truth :"
            in coq
            and "Record AtomicValuationSpec : Type := {" in coq
            and "atomic_valuation_denotes : forall A : Type, A -> Prop;" in coq
            and "valuation_lexical_truth_eat_application : forall n : nat" in coq
            and "Definition atomic_valuation_spec_from_lexical_transition_model : AtomicValuationSpec := {|"
            in coq
            and "Definition atomic_base_valuation_spec : AtomicValuationSpec :=" in coq
            and "Theorem atomic_valuation_spec_from_lexical_transition_model_exists :"
            in coq
            and "Theorem atomic_base_valuation_spec_exists :" in coq
            and "Theorem atomic_base_valuation_denotes_atomic_base_truth :" in coq
            and "Record AtomicTruthFacts : Type := {" in coq
            and "atomic_lexical_truth_eat_application : forall n : nat" in coq
            and "AtomicBaseTruth Prop (eat n mods arg1 arg2)" in coq
            and "Definition atomic_truth_facts_from_atomic_base_valuation : AtomicTruthFacts := {|"
            in coq
            and "Definition atomic_truth_facts : AtomicTruthFacts :=" in coq
            and "Theorem atomic_truth_facts_from_atomic_base_valuation_exists :" in coq
            and "atomic_base_truth_eat_application n mods arg1 arg2" in coq
            and "atomic_base_truth_transition theme scale source target" in coq
            and "Inductive AtomicClosureTruth : forall A : Type, A -> Prop :="
            in coq
            and "atomic_closure_truth_repeat : forall n : nat" in coq
            and "Theorem model_interpretable_atomic_closure_truth :" in coq
            and "Definition atomic_closure_truth_kernel_denotes : forall A : Type, A -> Prop :="
            in coq
            and "Definition atomic_closure_truth_kernel : ConcreteTruthConditionKernel := {|"
            in coq
            and "kernel_denotes := atomic_closure_truth_kernel_denotes" in coq
            and "Definition atomic_closure_truth_conditions_from_kernel : TruthConditionSpec :="
            in coq
            and "Theorem atomic_closure_truth_kernel_exists :" in coq
            and "Theorem atomic_closure_truth_kernel_denotes_atomic_closure_truth :"
            in coq
            and "Definition atomic_closure_truth_conditions : TruthConditionSpec :="
            in coq
            and "Theorem atomic_closure_truth_conditions_exists :" in coq
            and "Theorem atomic_closure_truth_conditions_denote_atomic_closure_truth :"
            in coq
        ),
        "coq atomic closure evidence-backed source instance": (
            "Definition atomic_closure_evidence_backed_truth_sources :"
            in coq
            and "EvidenceBackedTruthConditionSources := {|" in coq
            and "evidence_denotes := AtomicClosureTruth;" in coq
            and "Definition atomic_closure_evidence_backed_truth_kernel :"
            in coq
            and "Definition atomic_closure_evidence_backed_truth_ledger :"
            in coq
            and "Theorem atomic_closure_evidence_backed_truth_sources_exist :"
            in coq
            and "Theorem atomic_closure_evidence_backed_truth_kernel_exists :"
            in coq
            and "Theorem atomic_closure_evidence_backed_truth_ledger_exists :"
            in coq
            and "Theorem atomic_closure_evidence_backed_truth_sources_sound :"
            in coq
            and "Theorem example_4_atomic_closure_evidence_backed_truth_condition_sound :"
            in coq
        ),
        "lean transition-refined atomic closure layer": (
            "inductive RegisteredStateTransitionTruth : Entity -> StateScale -> State -> State -> Prop where"
            in lean
            and "registered_transition_vase_integrity_scale_intact_to_broken"
            in lean
            and "theorem registered_state_transition_atomic_base_truth :"
            in lean
            and "inductive TransitionRefinedAtomicClosureTruth : (A : Type) -> A -> Prop where"
            in lean
            and "| transition_refined_truth_transition : (theme : Entity)"
            in lean
            and "theorem transition_refined_atomic_closure_truth_implies_atomic_closure_truth :"
            in lean
            and "theorem example_4_transition_refined_atomic_closure_truth :"
            in lean
            and "theorem example_4_transition_refined_atomic_closure_sound :"
            in lean
            and "#check example_4_transition_refined_atomic_closure_truth"
            in lean
        ),
        "coq transition-refined atomic closure layer": (
            "Inductive RegisteredStateTransitionTruth : Entity -> StateScale -> State -> State -> Prop :="
            in coq
            and "registered_transition_vase_integrity_scale_intact_to_broken"
            in coq
            and "Theorem registered_state_transition_atomic_base_truth :"
            in coq
            and "Inductive TransitionRefinedAtomicClosureTruth : forall A : Type, A -> Prop :="
            in coq
            and "transition_refined_truth_transition : forall theme : Entity"
            in coq
            and "Theorem transition_refined_atomic_closure_truth_implies_atomic_closure_truth :"
            in coq
            and "Theorem example_4_transition_refined_atomic_closure_truth :"
            in coq
            and "Theorem example_4_transition_refined_atomic_closure_sound :"
            in coq
            and "Check example_4_transition_refined_atomic_closure_truth."
            in coq
        ),
        "lean registered truth condition spec instance": (
            "structure RegisteredTruthConditionSpec : Type where" in lean
            and "registered_truth_denotes : (A : Type) -> A -> Prop" in lean
            and "registered_truth_transition : (theme : Entity)" in lean
            and "RegisteredStateTransitionTruth theme scale source target ->"
            in lean
            and "def transition_refined_registered_truth_conditions : RegisteredTruthConditionSpec := {"
            in lean
            and "theorem transition_refined_registered_truth_condition_spec_exists :"
            in lean
            and "theorem transition_refined_registered_truth_conditions_denote_transition_refined :"
            in lean
            and "theorem transition_refined_registered_truth_conditions_imply_atomic_closure :"
            in lean
            and "theorem example_4_transition_refined_registered_truth_condition_sound :"
            in lean
            and "theorem example_4_transition_refined_registered_truth_condition_atomic_sound :"
            in lean
            and "#check example_4_transition_refined_registered_truth_condition_sound"
            in lean
        ),
        "coq registered truth condition spec instance": (
            "Record RegisteredTruthConditionSpec : Type := {" in coq
            and "registered_truth_denotes : forall A : Type, A -> Prop;" in coq
            and "registered_truth_transition : forall theme : Entity" in coq
            and "RegisteredStateTransitionTruth theme scale source target ->" in coq
            and "Definition transition_refined_registered_truth_conditions : RegisteredTruthConditionSpec := {|"
            in coq
            and "Theorem transition_refined_registered_truth_condition_spec_exists :"
            in coq
            and "Theorem transition_refined_registered_truth_conditions_denote_transition_refined :"
            in coq
            and "Theorem transition_refined_registered_truth_conditions_imply_atomic_closure :"
            in coq
            and "Theorem example_4_transition_refined_registered_truth_condition_sound :"
            in coq
            and "Theorem example_4_transition_refined_registered_truth_condition_atomic_sound :"
            in coq
            and "Check example_4_transition_refined_registered_truth_condition_sound."
            in coq
        ),
        "lean registered lexical truth condition spec instance": (
            "inductive RegisteredLexicalApplicationTruth : (A : Type) -> A -> Prop where"
            in lean
            and "registered_lexical_eat_0_John_x_theme" in lean
            and "(x_theme : Food) -> RegisteredLexicalApplicationTruth Prop (eat 0 mods_nil John x_theme)"
            in lean
            and "theorem registered_lexical_application_atomic_base_truth :"
            in lean
            and "theorem registered_lexical_application_atomic_closure_truth :"
            in lean
            and "inductive FullyRegisteredAtomicClosureTruth : (A : Type) -> A -> Prop where"
            in lean
            and "structure FullyRegisteredTruthConditionSpec : Type where" in lean
            and "def fully_registered_truth_conditions : FullyRegisteredTruthConditionSpec := {"
            in lean
            and "theorem fully_registered_truth_conditions_denote_fully_registered :"
            in lean
            and "theorem fully_registered_truth_conditions_imply_atomic_closure :"
            in lean
            and "theorem example_4_fully_registered_atomic_closure_truth :"
            in lean
            and "theorem example_4_fully_registered_truth_condition_sound :"
            in lean
            and "#check example_4_fully_registered_truth_condition_sound"
            in lean
        ),
        "coq registered lexical truth condition spec instance": (
            "Inductive RegisteredLexicalApplicationTruth : forall A : Type, A -> Prop :="
            in coq
            and "registered_lexical_eat_0_John_x_theme" in coq
            and "forall x_theme : Food" in coq
            and "RegisteredLexicalApplicationTruth Prop (eat 0 mods_nil John x_theme)"
            in coq
            and "Theorem registered_lexical_application_atomic_base_truth :"
            in coq
            and "Theorem registered_lexical_application_atomic_closure_truth :"
            in coq
            and "Inductive FullyRegisteredAtomicClosureTruth : forall A : Type, A -> Prop :="
            in coq
            and "Record FullyRegisteredTruthConditionSpec : Type := {" in coq
            and "Definition fully_registered_truth_conditions : FullyRegisteredTruthConditionSpec := {|"
            in coq
            and "Theorem fully_registered_truth_conditions_denote_fully_registered :"
            in coq
            and "Theorem fully_registered_truth_conditions_imply_atomic_closure :"
            in coq
            and "Theorem example_4_fully_registered_atomic_closure_truth :"
            in coq
            and "Theorem example_4_fully_registered_truth_condition_sound :"
            in coq
            and "Check example_4_fully_registered_truth_condition_sound."
            in coq
        ),
        "lean registered example truth instance package": (
            "structure RegisteredExampleTruthInstances : Type where" in lean
            and "example_4_truth_instance : fully_registered_truth_conditions."
            "fully_registered_truth_denotes PropT example_4" in lean
            and "def registered_example_truth_instances : "
            "RegisteredExampleTruthInstances := {" in lean
            and "theorem registered_example_truth_instances_exists :" in lean
            and "theorem registered_example_4_truth_instance_atomic_sound :"
            in lean
            and "#check registered_example_4_truth_instance_atomic_sound" in lean
            and "#check registered_example_truth_instances" in lean
        ),
        "coq registered example truth instance package": (
            "Record RegisteredExampleTruthInstances : Type := {" in coq
            and "example_4_truth_instance :" in coq
            and "fully_registered_truth_denotes fully_registered_truth_conditions "
            "PropT example_4" in coq
            and "Definition registered_example_truth_instances : "
            "RegisteredExampleTruthInstances := {|" in coq
            and "Theorem registered_example_truth_instances_exists :" in coq
            and "Theorem registered_example_4_truth_instance_atomic_sound :"
            in coq
            and "exact (example_4_truth_instance registered_example_truth_instances)."
            in coq
            and "Check registered_example_4_truth_instance_atomic_sound." in coq
            and "Check registered_example_truth_instances." in coq
        ),
        "lean finite registered truth-condition instance ledger": (
            all(
                count == lean_example_count
                for count in lean_finite_registered_truth_condition_ledger_atomic_counts.values()
            )
            and "structure FiniteRegisteredTruthConditionInstanceLedger : Type where"
            in lean
            and "finite_registered_ledger_route : ConcreteRegisteredTruthConditionRoute"
            in lean
            and "finite_registered_ledger_sources : IndependentRegisteredTruthConditionSources"
            in lean
            and "finite_registered_ledger_suite : "
            "IndependentRegisteredTruthConditionInstanceSuite"
            in lean
            and "finite_registered_ledger_suite_examples :" in lean
            and "IndependentRegisteredTruthConditionInstanceSuiteExamplePackage"
            in lean
            and "finite_registered_ledger_registered_examples : "
            "RegisteredExampleTruthInstances"
            in lean
            and "finite_registered_ledger_concrete_examples : "
            "ConcreteRegisteredExampleTruthInstances"
            in lean
            and "finite_registered_ledger_kernel_examples : "
            "ConcreteRegisteredKernelExampleTruthInstances"
            in lean
            and "def finite_registered_truth_condition_instance_ledger :"
            in lean
            and "theorem finite_registered_truth_condition_instance_ledger_exists :"
            in lean
            and "theorem "
            "finite_registered_truth_condition_instance_ledger_route_matches :"
            in lean
            and "theorem "
            "finite_registered_truth_condition_instance_ledger_suite_examples_matches :"
            in lean
            and "theorem "
            "finite_registered_truth_condition_instance_ledger_kernel_examples_matches :"
            in lean
            and "theorem "
            "finite_registered_truth_condition_ledger_example_4_suite_atomic_sound :"
            in lean
            and "theorem "
            "finite_registered_truth_condition_ledger_example_4_registered_atomic_sound :"
            in lean
            and "theorem "
            "finite_registered_truth_condition_ledger_example_4_concrete_atomic_sound :"
            in lean
            and "theorem "
            "finite_registered_truth_condition_ledger_example_4_kernel_atomic_sound :"
            in lean
            and "finite_registered_ledger_suite_examples.example_4_suite_atomic_sound"
            in lean
            and "finite_registered_ledger_registered_examples.example_4_truth_instance"
            in lean
            and "finite_registered_ledger_concrete_examples.example_4_concrete_truth_instance"
            in lean
            and "finite_registered_ledger_kernel_examples.example_4_kernel_truth_instance"
            in lean
            and "#check FiniteRegisteredTruthConditionInstanceLedger" in lean
            and "#check finite_registered_truth_condition_instance_ledger"
            in lean
            and "#check "
            "finite_registered_truth_condition_instance_ledger_kernel_examples_matches"
            in lean
            and "#check "
            "finite_registered_truth_condition_ledger_example_4_kernel_atomic_sound"
            in lean
        ),
        "coq finite registered truth-condition instance ledger": (
            all(
                count == coq_example_count
                for count in coq_finite_registered_truth_condition_ledger_atomic_counts.values()
            )
            and "Record FiniteRegisteredTruthConditionInstanceLedger : Type := {"
            in coq
            and "finite_registered_ledger_route : ConcreteRegisteredTruthConditionRoute;"
            in coq
            and "finite_registered_ledger_sources : IndependentRegisteredTruthConditionSources;"
            in coq
            and "finite_registered_ledger_suite : "
            "IndependentRegisteredTruthConditionInstanceSuite;"
            in coq
            and "finite_registered_ledger_suite_examples :" in coq
            and "IndependentRegisteredTruthConditionInstanceSuiteExamplePackage;"
            in coq
            and "finite_registered_ledger_registered_examples : "
            "RegisteredExampleTruthInstances;"
            in coq
            and "finite_registered_ledger_concrete_examples : "
            "ConcreteRegisteredExampleTruthInstances;"
            in coq
            and "finite_registered_ledger_kernel_examples : "
            "ConcreteRegisteredKernelExampleTruthInstances;"
            in coq
            and "Definition finite_registered_truth_condition_instance_ledger :"
            in coq
            and "Theorem finite_registered_truth_condition_instance_ledger_exists :"
            in coq
            and "Theorem "
            "finite_registered_truth_condition_instance_ledger_route_matches :"
            in coq
            and "Theorem "
            "finite_registered_truth_condition_instance_ledger_suite_examples_matches :"
            in coq
            and "Theorem "
            "finite_registered_truth_condition_instance_ledger_kernel_examples_matches :"
            in coq
            and "Theorem "
            "finite_registered_truth_condition_ledger_example_4_suite_atomic_sound :"
            in coq
            and "Theorem "
            "finite_registered_truth_condition_ledger_example_4_registered_atomic_sound :"
            in coq
            and "Theorem "
            "finite_registered_truth_condition_ledger_example_4_concrete_atomic_sound :"
            in coq
            and "Theorem "
            "finite_registered_truth_condition_ledger_example_4_kernel_atomic_sound :"
            in coq
            and "finite_registered_ledger_suite_examples" in coq
            and "finite_registered_ledger_registered_examples" in coq
            and "finite_registered_ledger_concrete_examples" in coq
            and "finite_registered_ledger_kernel_examples" in coq
            and "Check FiniteRegisteredTruthConditionInstanceLedger." in coq
            and "Check finite_registered_truth_condition_instance_ledger."
            in coq
            and "Check "
            "finite_registered_truth_condition_instance_ledger_kernel_examples_matches."
            in coq
            and "Check "
            "finite_registered_truth_condition_ledger_example_4_kernel_atomic_sound."
            in coq
        ),
        "lean finite registered truth-condition completion certificate": (
            all(
                count == lean_example_count
                for count in lean_finite_registered_truth_condition_completion_atomic_counts.values()
            )
            and "structure FiniteRegisteredTruthConditionCompletionCertificate : "
            "Type where" in lean
            and "finite_registered_completion_ledger : "
            "FiniteRegisteredTruthConditionInstanceLedger" in lean
            and "finite_registered_completion_registered_sound :" in lean
            and "finite_registered_completion_direct_sound :" in lean
            and "finite_registered_completion_evidence_sound :" in lean
            and "finite_registered_completion_kernel_sound :" in lean
            and "finite_registered_completion_source_sound :" in lean
            and "finite_registered_completion_suite_sound :" in lean
            and "def finite_registered_truth_condition_completion_certificate :"
            in lean
            and "theorem finite_registered_truth_condition_completion_certificate_exists :"
            in lean
            and "theorem finite_registered_truth_condition_completion_ledger_matches :"
            in lean
            and "theorem "
            "finite_registered_truth_condition_completion_registered_spec_sound :"
            in lean
            and "theorem "
            "finite_registered_truth_condition_completion_direct_spec_sound :"
            in lean
            and "theorem "
            "finite_registered_truth_condition_completion_evidence_spec_sound :"
            in lean
            and "theorem "
            "finite_registered_truth_condition_completion_kernel_spec_sound :"
            in lean
            and "theorem "
            "finite_registered_truth_condition_completion_source_spec_sound :"
            in lean
            and "theorem "
            "finite_registered_truth_condition_completion_suite_spec_sound :"
            in lean
            and "theorem "
            "finite_registered_truth_condition_completion_example_4_registered_atomic_sound :"
            in lean
            and "theorem "
            "finite_registered_truth_condition_completion_example_4_direct_atomic_sound :"
            in lean
            and "theorem "
            "finite_registered_truth_condition_completion_example_4_evidence_atomic_sound :"
            in lean
            and "theorem "
            "finite_registered_truth_condition_completion_example_4_kernel_atomic_sound :"
            in lean
            and "theorem "
            "finite_registered_truth_condition_completion_example_4_source_atomic_sound :"
            in lean
            and "theorem "
            "finite_registered_truth_condition_completion_example_4_suite_atomic_sound :"
            in lean
            and "finite_registered_completion_ledger."
            "finite_registered_ledger_route."
            "concrete_registered_route_evidence_examples."
            "example_4_evidence_backed_truth_instance" in lean
            and "finite_registered_completion_ledger."
            "finite_registered_ledger_sources."
            "independent_registered_truth_condition_examples."
            "example_4_concrete_truth_instance" in lean
            and "#check FiniteRegisteredTruthConditionCompletionCertificate"
            in lean
            and "#check finite_registered_truth_condition_completion_certificate"
            in lean
            and "#check "
            "finite_registered_truth_condition_completion_direct_spec_sound"
            in lean
            and "#check "
            "finite_registered_truth_condition_completion_example_4_source_atomic_sound"
            in lean
        ),
        "coq finite registered truth-condition completion certificate": (
            all(
                count == coq_example_count
                for count in coq_finite_registered_truth_condition_completion_atomic_counts.values()
            )
            and "Record FiniteRegisteredTruthConditionCompletionCertificate : Type := {"
            in coq
            and "finite_registered_completion_ledger : "
            "FiniteRegisteredTruthConditionInstanceLedger;" in coq
            and "finite_registered_completion_registered_sound :" in coq
            and "finite_registered_completion_direct_sound :" in coq
            and "finite_registered_completion_evidence_sound :" in coq
            and "finite_registered_completion_kernel_sound :" in coq
            and "finite_registered_completion_source_sound :" in coq
            and "finite_registered_completion_suite_sound :" in coq
            and "Definition finite_registered_truth_condition_completion_certificate :"
            in coq
            and "Theorem finite_registered_truth_condition_completion_certificate_exists :"
            in coq
            and "Theorem finite_registered_truth_condition_completion_ledger_matches :"
            in coq
            and "Theorem "
            "finite_registered_truth_condition_completion_registered_spec_sound :"
            in coq
            and "Theorem "
            "finite_registered_truth_condition_completion_direct_spec_sound :"
            in coq
            and "Theorem "
            "finite_registered_truth_condition_completion_evidence_spec_sound :"
            in coq
            and "Theorem "
            "finite_registered_truth_condition_completion_kernel_spec_sound :"
            in coq
            and "Theorem "
            "finite_registered_truth_condition_completion_source_spec_sound :"
            in coq
            and "Theorem "
            "finite_registered_truth_condition_completion_suite_spec_sound :"
            in coq
            and "Theorem "
            "finite_registered_truth_condition_completion_example_4_registered_atomic_sound :"
            in coq
            and "Theorem "
            "finite_registered_truth_condition_completion_example_4_direct_atomic_sound :"
            in coq
            and "Theorem "
            "finite_registered_truth_condition_completion_example_4_evidence_atomic_sound :"
            in coq
            and "Theorem "
            "finite_registered_truth_condition_completion_example_4_kernel_atomic_sound :"
            in coq
            and "Theorem "
            "finite_registered_truth_condition_completion_example_4_source_atomic_sound :"
            in coq
            and "Theorem "
            "finite_registered_truth_condition_completion_example_4_suite_atomic_sound :"
            in coq
            and "concrete_registered_route_evidence_examples" in coq
            and "independent_registered_truth_condition_examples" in coq
            and "Check FiniteRegisteredTruthConditionCompletionCertificate."
            in coq
            and "Check finite_registered_truth_condition_completion_certificate."
            in coq
            and "Check "
            "finite_registered_truth_condition_completion_direct_spec_sound."
            in coq
            and "Check "
            "finite_registered_truth_condition_completion_example_4_source_atomic_sound."
            in coq
        ),
        "lean finite registered truth-condition component coverage certificate": (
            lean_finite_registered_truth_condition_component_coverage_atomic_count
            == lean_example_count
            and "structure "
            "FiniteRegisteredTruthConditionComponentCoverageCertificate : "
            "Type where" in lean
            and "finite_registered_component_completion : "
            "FiniteRegisteredTruthConditionCompletionCertificate" in lean
            and "finite_registered_component_lexical : "
            "IndependentRegisteredLexicalTruthConditionInstances" in lean
            and "finite_registered_component_temporal : "
            "IndependentRegisteredTemporalTruthConditionInstances" in lean
            and "finite_registered_component_sigma : "
            "IndependentRegisteredSigmaTruthConditionInstances" in lean
            and "finite_registered_component_repeat : "
            "IndependentRegisteredRepeatTruthConditionInstances" in lean
            and "finite_registered_component_polarity : "
            "IndependentRegisteredPolarityTruthConditionInstances" in lean
            and "finite_registered_component_transition_cause : "
            "IndependentRegisteredTransitionCauseTruthConditionInstances" in lean
            and "finite_registered_component_suite : "
            "IndependentRegisteredTruthConditionInstanceSuite" in lean
            and "def "
            "finite_registered_truth_condition_component_coverage_certificate :"
            in lean
            and "theorem "
            "finite_registered_truth_condition_component_coverage_certificate_exists :"
            in lean
            and "theorem "
            "finite_registered_truth_condition_component_completion_matches :"
            in lean
            and "theorem "
            "finite_registered_truth_condition_component_transition_cause_matches :"
            in lean
            and "theorem "
            "finite_registered_truth_condition_component_lexical_spec_sound :"
            in lean
            and "theorem "
            "finite_registered_truth_condition_component_temporal_spec_sound :"
            in lean
            and "theorem "
            "finite_registered_truth_condition_component_sigma_spec_sound :"
            in lean
            and "theorem "
            "finite_registered_truth_condition_component_repeat_spec_sound :"
            in lean
            and "theorem "
            "finite_registered_truth_condition_component_polarity_spec_sound :"
            in lean
            and "theorem "
            "finite_registered_truth_condition_component_transition_cause_spec_sound :"
            in lean
            and "theorem "
            "finite_registered_truth_condition_component_suite_spec_sound :"
            in lean
            and "theorem "
            "finite_registered_truth_condition_component_coverage_example_4_atomic_sound :"
            in lean
            and "#check "
            "FiniteRegisteredTruthConditionComponentCoverageCertificate"
            in lean
            and "#check "
            "finite_registered_truth_condition_component_coverage_certificate"
            in lean
            and "#check "
            "finite_registered_truth_condition_component_transition_cause_spec_sound"
            in lean
            and "#check "
            "finite_registered_truth_condition_component_coverage_example_4_atomic_sound"
            in lean
        ),
        "coq finite registered truth-condition component coverage certificate": (
            coq_finite_registered_truth_condition_component_coverage_atomic_count
            == coq_example_count
            and "Record "
            "FiniteRegisteredTruthConditionComponentCoverageCertificate : Type := {"
            in coq
            and "finite_registered_component_completion : "
            "FiniteRegisteredTruthConditionCompletionCertificate;" in coq
            and "finite_registered_component_lexical : "
            "IndependentRegisteredLexicalTruthConditionInstances;" in coq
            and "finite_registered_component_temporal : "
            "IndependentRegisteredTemporalTruthConditionInstances;" in coq
            and "finite_registered_component_sigma : "
            "IndependentRegisteredSigmaTruthConditionInstances;" in coq
            and "finite_registered_component_repeat : "
            "IndependentRegisteredRepeatTruthConditionInstances;" in coq
            and "finite_registered_component_polarity : "
            "IndependentRegisteredPolarityTruthConditionInstances;" in coq
            and "finite_registered_component_transition_cause : "
            "IndependentRegisteredTransitionCauseTruthConditionInstances;" in coq
            and "finite_registered_component_suite : "
            "IndependentRegisteredTruthConditionInstanceSuite;" in coq
            and "Definition "
            "finite_registered_truth_condition_component_coverage_certificate :"
            in coq
            and "Theorem "
            "finite_registered_truth_condition_component_coverage_certificate_exists :"
            in coq
            and "Theorem "
            "finite_registered_truth_condition_component_completion_matches :"
            in coq
            and "Theorem "
            "finite_registered_truth_condition_component_transition_cause_matches :"
            in coq
            and "Theorem "
            "finite_registered_truth_condition_component_lexical_spec_sound :"
            in coq
            and "Theorem "
            "finite_registered_truth_condition_component_temporal_spec_sound :"
            in coq
            and "Theorem "
            "finite_registered_truth_condition_component_sigma_spec_sound :"
            in coq
            and "Theorem "
            "finite_registered_truth_condition_component_repeat_spec_sound :"
            in coq
            and "Theorem "
            "finite_registered_truth_condition_component_polarity_spec_sound :"
            in coq
            and "Theorem "
            "finite_registered_truth_condition_component_transition_cause_spec_sound :"
            in coq
            and "Theorem "
            "finite_registered_truth_condition_component_suite_spec_sound :"
            in coq
            and "Theorem "
            "finite_registered_truth_condition_component_coverage_example_4_atomic_sound :"
            in coq
            and "Check "
            "FiniteRegisteredTruthConditionComponentCoverageCertificate."
            in coq
            and "Check "
            "finite_registered_truth_condition_component_coverage_certificate."
            in coq
            and "Check "
            "finite_registered_truth_condition_component_transition_cause_spec_sound."
            in coq
            and "Check "
            "finite_registered_truth_condition_component_coverage_example_4_atomic_sound."
            in coq
        ),
        "lean finite registered atomic witness certificate": (
            lean_finite_registered_atomic_witness_lexical_projection_count == 12
            and lean_finite_registered_atomic_witness_transition_projection_count
            == 3
            and "structure FiniteRegisteredAtomicWitnessCertificate : Type where"
            in lean
            and "finite_registered_atomic_witness_basis : "
            "ConcreteRegisteredTruthBasis" in lean
            and "finite_registered_atomic_witness_lexical_3_concrete : "
            "(x_theme : Food) -> "
            "ConcreteRegisteredAtomicTruth Prop (eat 0 mods_nil John x_theme)"
            in lean
            and "finite_registered_atomic_witness_transition_1_closure : "
            "AtomicClosureTruth TransitionT "
            "(Transition vase integrity_scale intact broken)" in lean
            and "def finite_registered_atomic_witness_certificate :" in lean
            and "theorem finite_registered_atomic_witness_certificate_exists :"
            in lean
            and "theorem finite_registered_atomic_witness_basis_matches :"
            in lean
            and "theorem "
            "finite_registered_atomic_witness_lexical_3_base_projected :"
            in lean
            and "theorem "
            "finite_registered_atomic_witness_transition_1_closure_projected :"
            in lean
            and "#check FiniteRegisteredAtomicWitnessCertificate" in lean
            and "#check finite_registered_atomic_witness_certificate" in lean
            and "#check "
            "finite_registered_atomic_witness_lexical_3_closure_projected"
            in lean
            and "#check "
            "finite_registered_atomic_witness_transition_1_closure_projected"
            in lean
        ),
        "coq finite registered atomic witness certificate": (
            coq_finite_registered_atomic_witness_lexical_projection_count == 12
            and coq_finite_registered_atomic_witness_transition_projection_count
            == 3
            and "Record FiniteRegisteredAtomicWitnessCertificate : Type := {"
            in coq
            and "finite_registered_atomic_witness_basis : "
            "ConcreteRegisteredTruthBasis;" in coq
            and "finite_registered_atomic_witness_lexical_3_concrete : "
            "forall x_theme : Food," in coq
            and "ConcreteRegisteredAtomicTruth Prop "
            "(eat 0 mods_nil John x_theme);" in coq
            and "finite_registered_atomic_witness_transition_1_closure : "
            "AtomicClosureTruth TransitionT "
            "(Transition vase integrity_scale intact broken)" in coq
            and "Definition finite_registered_atomic_witness_certificate :"
            in coq
            and "Theorem finite_registered_atomic_witness_certificate_exists :"
            in coq
            and "Theorem finite_registered_atomic_witness_basis_matches :"
            in coq
            and "Theorem "
            "finite_registered_atomic_witness_lexical_3_base_projected :"
            in coq
            and "Theorem "
            "finite_registered_atomic_witness_transition_1_closure_projected :"
            in coq
            and "Check FiniteRegisteredAtomicWitnessCertificate." in coq
            and "Check finite_registered_atomic_witness_certificate." in coq
            and "Check "
            "finite_registered_atomic_witness_lexical_3_closure_projected."
            in coq
            and "Check "
            "finite_registered_atomic_witness_transition_1_closure_projected."
            in coq
        ),
        "lean finite registered atomic source discipline certificate": (
            lean_finite_registered_atomic_source_lexical_source_count == 4
            and lean_finite_registered_atomic_source_lexical_bridge_count == 12
            and lean_finite_registered_atomic_source_transition_source_count == 1
            and lean_finite_registered_atomic_source_transition_bridge_count == 3
            and "structure FiniteRegisteredAtomicSourceDisciplineCertificate : Type where"
            in lean
            and "finite_registered_atomic_source_witness : "
            "FiniteRegisteredAtomicWitnessCertificate" in lean
            and "finite_registered_atomic_source_lexical_3_source : "
            "(x_theme : Food) -> "
            "RegisteredLexicalApplicationTruth Prop "
            "(eat 0 mods_nil John x_theme)" in lean
            and "finite_registered_atomic_source_lexical_3_closure_from_source : "
            "(x_theme : Food) -> RegisteredLexicalApplicationTruth Prop "
            "(eat 0 mods_nil John x_theme) -> AtomicClosureTruth Prop "
            "(eat 0 mods_nil John x_theme)" in lean
            and "finite_registered_atomic_source_transition_1_source : "
            "RegisteredStateTransitionTruth vase integrity_scale intact broken"
            in lean
            and "def finite_registered_atomic_source_discipline_certificate :"
            in lean
            and "theorem finite_registered_atomic_source_discipline_certificate_exists :"
            in lean
            and "theorem finite_registered_atomic_source_witness_matches :"
            in lean
            and "theorem "
            "finite_registered_atomic_source_lexical_3_source_projected :"
            in lean
            and "theorem "
            "finite_registered_atomic_source_lexical_3_closure_from_source_projected :"
            in lean
            and "theorem "
            "finite_registered_atomic_source_transition_1_closure_from_source_projected :"
            in lean
            and "#check FiniteRegisteredAtomicSourceDisciplineCertificate"
            in lean
            and "#check "
            "finite_registered_atomic_source_lexical_3_closure_from_source_projected"
            in lean
            and "#check "
            "finite_registered_atomic_source_transition_1_closure_from_source_projected"
            in lean
        ),
        "coq finite registered atomic source discipline certificate": (
            coq_finite_registered_atomic_source_lexical_source_count == 4
            and coq_finite_registered_atomic_source_lexical_bridge_count == 12
            and coq_finite_registered_atomic_source_transition_source_count == 1
            and coq_finite_registered_atomic_source_transition_bridge_count == 3
            and "Record FiniteRegisteredAtomicSourceDisciplineCertificate : Type := {"
            in coq
            and "finite_registered_atomic_source_witness : "
            "FiniteRegisteredAtomicWitnessCertificate;" in coq
            and "finite_registered_atomic_source_lexical_3_source : "
            "forall x_theme : Food," in coq
            and "RegisteredLexicalApplicationTruth Prop "
            "(eat 0 mods_nil John x_theme);" in coq
            and "finite_registered_atomic_source_lexical_3_closure_from_source : "
            "forall x_theme : Food," in coq
            and "RegisteredLexicalApplicationTruth Prop "
            "(eat 0 mods_nil John x_theme) ->" in coq
            and "AtomicClosureTruth Prop (eat 0 mods_nil John x_theme);"
            in coq
            and "finite_registered_atomic_source_transition_1_source : "
            "RegisteredStateTransitionTruth vase integrity_scale intact broken;"
            in coq
            and "Definition finite_registered_atomic_source_discipline_certificate :"
            in coq
            and "Theorem finite_registered_atomic_source_discipline_certificate_exists :"
            in coq
            and "Theorem finite_registered_atomic_source_witness_matches :"
            in coq
            and "Theorem "
            "finite_registered_atomic_source_lexical_3_source_projected :"
            in coq
            and "Theorem "
            "finite_registered_atomic_source_lexical_3_closure_from_source_projected :"
            in coq
            and "Theorem "
            "finite_registered_atomic_source_transition_1_closure_from_source_projected :"
            in coq
            and "Check FiniteRegisteredAtomicSourceDisciplineCertificate."
            in coq
            and "Check "
            "finite_registered_atomic_source_lexical_3_closure_from_source_projected."
            in coq
            and "Check "
            "finite_registered_atomic_source_transition_1_closure_from_source_projected."
            in coq
        ),
        "lean finite registered atomic kernel alignment certificate": (
            lean_finite_registered_atomic_kernel_alignment_lexical_source_count
            == 4
            and lean_finite_registered_atomic_kernel_alignment_lexical_atomic_count
            == 4
            and lean_finite_registered_atomic_kernel_alignment_transition_source_count
            == 1
            and lean_finite_registered_atomic_kernel_alignment_transition_atomic_count
            == 1
            and "theorem finite_registered_atomic_kernel_denotes_imply_atomic_closure :"
            in lean
            and "structure FiniteRegisteredAtomicKernelAlignmentCertificate : Type where"
            in lean
            and "finite_registered_atomic_kernel_alignment_source : "
            "FiniteRegisteredAtomicSourceDisciplineCertificate" in lean
            and "finite_registered_atomic_kernel_alignment_kernel : "
            "ConcreteRegisteredTruthKernel" in lean
            and "finite_registered_atomic_kernel_alignment_lexical_3_source_to_kernel : "
            "(x_theme : Food) -> RegisteredLexicalApplicationTruth Prop "
            "(eat 0 mods_nil John x_theme) -> "
            "concrete_registered_truth_kernel.concrete_registered_kernel_denotes "
            "Prop (eat 0 mods_nil John x_theme)" in lean
            and "finite_registered_atomic_kernel_alignment_transition_1_source_to_kernel : "
            "RegisteredStateTransitionTruth vase integrity_scale intact broken -> "
            "concrete_registered_truth_kernel.concrete_registered_kernel_denotes "
            "TransitionT (Transition vase integrity_scale intact broken)" in lean
            and "def finite_registered_atomic_kernel_alignment_certificate :"
            in lean
            and "theorem finite_registered_atomic_kernel_alignment_certificate_exists :"
            in lean
            and "theorem finite_registered_atomic_kernel_alignment_source_matches :"
            in lean
            and "theorem finite_registered_atomic_kernel_alignment_kernel_matches :"
            in lean
            and "theorem "
            "finite_registered_atomic_kernel_alignment_lexical_3_source_to_kernel_projected :"
            in lean
            and "theorem "
            "finite_registered_atomic_kernel_alignment_lexical_3_atomic_projected :"
            in lean
            and "theorem "
            "finite_registered_atomic_kernel_alignment_transition_1_atomic_projected :"
            in lean
            and "#check FiniteRegisteredAtomicKernelAlignmentCertificate"
            in lean
            and "#check finite_registered_atomic_kernel_alignment_certificate"
            in lean
            and "#check "
            "finite_registered_atomic_kernel_alignment_lexical_3_atomic_projected"
            in lean
            and "#check "
            "finite_registered_atomic_kernel_alignment_transition_1_atomic_projected"
            in lean
        ),
        "coq finite registered atomic kernel alignment certificate": (
            coq_finite_registered_atomic_kernel_alignment_lexical_source_count
            == 4
            and coq_finite_registered_atomic_kernel_alignment_lexical_atomic_count
            == 4
            and coq_finite_registered_atomic_kernel_alignment_transition_source_count
            == 1
            and coq_finite_registered_atomic_kernel_alignment_transition_atomic_count
            == 1
            and "Theorem finite_registered_atomic_kernel_denotes_imply_atomic_closure :"
            in coq
            and "Record FiniteRegisteredAtomicKernelAlignmentCertificate : Type := {"
            in coq
            and "finite_registered_atomic_kernel_alignment_source : "
            "FiniteRegisteredAtomicSourceDisciplineCertificate;" in coq
            and "finite_registered_atomic_kernel_alignment_kernel : "
            "ConcreteRegisteredTruthKernel;" in coq
            and "finite_registered_atomic_kernel_alignment_lexical_3_source_to_kernel : "
            "forall x_theme : Food," in coq
            and "RegisteredLexicalApplicationTruth Prop "
            "(eat 0 mods_nil John x_theme) ->" in coq
            and "concrete_registered_kernel_denotes concrete_registered_truth_kernel "
            "Prop (eat 0 mods_nil John x_theme);" in coq
            and "finite_registered_atomic_kernel_alignment_transition_1_source_to_kernel : "
            "RegisteredStateTransitionTruth vase integrity_scale intact broken ->"
            in coq
            and "concrete_registered_kernel_denotes concrete_registered_truth_kernel "
            "TransitionT (Transition vase integrity_scale intact broken)" in coq
            and "Definition finite_registered_atomic_kernel_alignment_certificate :"
            in coq
            and "Theorem finite_registered_atomic_kernel_alignment_certificate_exists :"
            in coq
            and "Theorem finite_registered_atomic_kernel_alignment_source_matches :"
            in coq
            and "Theorem finite_registered_atomic_kernel_alignment_kernel_matches :"
            in coq
            and "Theorem "
            "finite_registered_atomic_kernel_alignment_lexical_3_source_to_kernel_projected :"
            in coq
            and "Theorem "
            "finite_registered_atomic_kernel_alignment_lexical_3_atomic_projected :"
            in coq
            and "Theorem "
            "finite_registered_atomic_kernel_alignment_transition_1_atomic_projected :"
            in coq
            and "Check FiniteRegisteredAtomicKernelAlignmentCertificate."
            in coq
            and "Check finite_registered_atomic_kernel_alignment_certificate."
            in coq
            and "Check "
            "finite_registered_atomic_kernel_alignment_lexical_3_atomic_projected."
            in coq
            and "Check "
            "finite_registered_atomic_kernel_alignment_transition_1_atomic_projected."
            in coq
        ),
        "lean finite registered atomic truth condition source certificate": (
            lean_finite_registered_atomic_truth_condition_source_lexical_spec_count
            == 4
            and lean_finite_registered_atomic_truth_condition_source_lexical_kernel_count
            == 4
            and lean_finite_registered_atomic_truth_condition_source_lexical_atomic_count
            == 4
            and lean_finite_registered_atomic_truth_condition_source_transition_spec_count
            == 1
            and lean_finite_registered_atomic_truth_condition_source_transition_kernel_count
            == 1
            and lean_finite_registered_atomic_truth_condition_source_transition_atomic_count
            == 1
            and "structure FiniteRegisteredAtomicTruthConditionSourceCertificate : Type where"
            in lean
            and "finite_registered_atomic_truth_condition_source_alignment : "
            "FiniteRegisteredAtomicKernelAlignmentCertificate" in lean
            and "finite_registered_atomic_truth_condition_source_spec : "
            "FullyRegisteredTruthConditionSpec" in lean
            and "finite_registered_atomic_truth_condition_source_lexical_3_source_to_spec : "
            "(x_theme : Food) -> RegisteredLexicalApplicationTruth Prop "
            "(eat 0 mods_nil John x_theme) -> "
            "concrete_registered_truth_conditions."
            "fully_registered_truth_denotes Prop (eat 0 mods_nil John x_theme)"
            in lean
            and "def finite_registered_atomic_truth_condition_source_certificate :"
            in lean
            and "theorem "
            "finite_registered_atomic_truth_condition_source_certificate_exists :"
            in lean
            and "theorem "
            "finite_registered_atomic_truth_condition_source_alignment_matches :"
            in lean
            and "theorem finite_registered_atomic_truth_condition_source_spec_matches :"
            in lean
            and "theorem "
            "finite_registered_atomic_truth_condition_source_sound_projected :"
            in lean
            and "theorem "
            "finite_registered_atomic_truth_condition_source_lexical_3_source_to_spec_projected :"
            in lean
            and "theorem "
            "finite_registered_atomic_truth_condition_source_lexical_3_source_to_kernel_projected :"
            in lean
            and "theorem "
            "finite_registered_atomic_truth_condition_source_lexical_3_atomic_projected :"
            in lean
            and "theorem "
            "finite_registered_atomic_truth_condition_source_transition_1_atomic_projected :"
            in lean
            and "#check FiniteRegisteredAtomicTruthConditionSourceCertificate"
            in lean
            and "#check "
            "finite_registered_atomic_truth_condition_source_lexical_3_atomic_projected"
            in lean
            and "#check "
            "finite_registered_atomic_truth_condition_source_transition_1_atomic_projected"
            in lean
        ),
        "coq finite registered atomic truth condition source certificate": (
            coq_finite_registered_atomic_truth_condition_source_lexical_spec_count
            == 4
            and coq_finite_registered_atomic_truth_condition_source_lexical_kernel_count
            == 4
            and coq_finite_registered_atomic_truth_condition_source_lexical_atomic_count
            == 4
            and coq_finite_registered_atomic_truth_condition_source_transition_spec_count
            == 1
            and coq_finite_registered_atomic_truth_condition_source_transition_kernel_count
            == 1
            and coq_finite_registered_atomic_truth_condition_source_transition_atomic_count
            == 1
            and "Record FiniteRegisteredAtomicTruthConditionSourceCertificate : Type := {"
            in coq
            and "finite_registered_atomic_truth_condition_source_alignment : "
            "FiniteRegisteredAtomicKernelAlignmentCertificate;" in coq
            and "finite_registered_atomic_truth_condition_source_spec : "
            "FullyRegisteredTruthConditionSpec;" in coq
            and "finite_registered_atomic_truth_condition_source_lexical_3_source_to_spec : "
            "forall x_theme : Food," in coq
            and "RegisteredLexicalApplicationTruth Prop "
            "(eat 0 mods_nil John x_theme) ->" in coq
            and "fully_registered_truth_denotes concrete_registered_truth_conditions "
            "Prop (eat 0 mods_nil John x_theme);" in coq
            and "Definition finite_registered_atomic_truth_condition_source_certificate :"
            in coq
            and "Theorem "
            "finite_registered_atomic_truth_condition_source_certificate_exists :"
            in coq
            and "Theorem "
            "finite_registered_atomic_truth_condition_source_alignment_matches :"
            in coq
            and "Theorem finite_registered_atomic_truth_condition_source_spec_matches :"
            in coq
            and "Theorem "
            "finite_registered_atomic_truth_condition_source_sound_projected :"
            in coq
            and "Theorem "
            "finite_registered_atomic_truth_condition_source_lexical_3_source_to_spec_projected :"
            in coq
            and "Theorem "
            "finite_registered_atomic_truth_condition_source_lexical_3_source_to_kernel_projected :"
            in coq
            and "Theorem "
            "finite_registered_atomic_truth_condition_source_lexical_3_atomic_projected :"
            in coq
            and "Theorem "
            "finite_registered_atomic_truth_condition_source_transition_1_atomic_projected :"
            in coq
            and "Check FiniteRegisteredAtomicTruthConditionSourceCertificate."
            in coq
            and "Check "
            "finite_registered_atomic_truth_condition_source_lexical_3_atomic_projected."
            in coq
            and "Check "
            "finite_registered_atomic_truth_condition_source_transition_1_atomic_projected."
            in coq
        ),
        "lean finite registered atomic truth condition instance certificate": (
            lean_finite_registered_atomic_truth_condition_instance_lexical_truth_count
            == 4
            and lean_finite_registered_atomic_truth_condition_instance_lexical_atomic_count
            == 4
            and lean_finite_registered_atomic_truth_condition_instance_transition_truth_count
            == 1
            and lean_finite_registered_atomic_truth_condition_instance_transition_atomic_count
            == 1
            and "structure FiniteRegisteredAtomicTruthConditionInstanceCertificate : Type where"
            in lean
            and "finite_registered_atomic_truth_condition_instance_source : "
            "FiniteRegisteredAtomicTruthConditionSourceCertificate" in lean
            and "finite_registered_atomic_truth_condition_instance_spec : "
            "FullyRegisteredTruthConditionSpec" in lean
            and "finite_registered_atomic_truth_condition_instance_lexical_3_truth : "
            "(x_theme : Food) -> concrete_registered_truth_conditions."
            "fully_registered_truth_denotes Prop (eat 0 mods_nil John x_theme)"
            in lean
            and "def finite_registered_atomic_truth_condition_instance_certificate :"
            in lean
            and "theorem "
            "finite_registered_atomic_truth_condition_instance_certificate_exists :"
            in lean
            and "theorem "
            "finite_registered_atomic_truth_condition_instance_source_matches :"
            in lean
            and "theorem finite_registered_atomic_truth_condition_instance_spec_matches :"
            in lean
            and "theorem "
            "finite_registered_atomic_truth_condition_instance_sound_projected :"
            in lean
            and "theorem "
            "finite_registered_atomic_truth_condition_instance_lexical_3_truth_projected :"
            in lean
            and "theorem "
            "finite_registered_atomic_truth_condition_instance_lexical_3_atomic_projected :"
            in lean
            and "theorem "
            "finite_registered_atomic_truth_condition_instance_transition_1_truth_projected :"
            in lean
            and "theorem "
            "finite_registered_atomic_truth_condition_instance_transition_1_atomic_projected :"
            in lean
            and "#check FiniteRegisteredAtomicTruthConditionInstanceCertificate"
            in lean
            and "#check "
            "finite_registered_atomic_truth_condition_instance_lexical_3_truth_projected"
            in lean
            and "#check "
            "finite_registered_atomic_truth_condition_instance_transition_1_atomic_projected"
            in lean
        ),
        "coq finite registered atomic truth condition instance certificate": (
            coq_finite_registered_atomic_truth_condition_instance_lexical_truth_count
            == 4
            and coq_finite_registered_atomic_truth_condition_instance_lexical_atomic_count
            == 4
            and coq_finite_registered_atomic_truth_condition_instance_transition_truth_count
            == 1
            and coq_finite_registered_atomic_truth_condition_instance_transition_atomic_count
            == 1
            and "Record FiniteRegisteredAtomicTruthConditionInstanceCertificate : Type := {"
            in coq
            and "finite_registered_atomic_truth_condition_instance_source : "
            "FiniteRegisteredAtomicTruthConditionSourceCertificate;" in coq
            and "finite_registered_atomic_truth_condition_instance_spec : "
            "FullyRegisteredTruthConditionSpec;" in coq
            and "finite_registered_atomic_truth_condition_instance_lexical_3_truth : "
            "forall x_theme : Food," in coq
            and "fully_registered_truth_denotes concrete_registered_truth_conditions "
            "Prop (eat 0 mods_nil John x_theme);" in coq
            and "Definition finite_registered_atomic_truth_condition_instance_certificate :"
            in coq
            and "Theorem "
            "finite_registered_atomic_truth_condition_instance_certificate_exists :"
            in coq
            and "Theorem "
            "finite_registered_atomic_truth_condition_instance_source_matches :"
            in coq
            and "Theorem finite_registered_atomic_truth_condition_instance_spec_matches :"
            in coq
            and "Theorem "
            "finite_registered_atomic_truth_condition_instance_sound_projected :"
            in coq
            and "Theorem "
            "finite_registered_atomic_truth_condition_instance_lexical_3_truth_projected :"
            in coq
            and "Theorem "
            "finite_registered_atomic_truth_condition_instance_lexical_3_atomic_projected :"
            in coq
            and "Theorem "
            "finite_registered_atomic_truth_condition_instance_transition_1_truth_projected :"
            in coq
            and "Theorem "
            "finite_registered_atomic_truth_condition_instance_transition_1_atomic_projected :"
            in coq
            and "Check FiniteRegisteredAtomicTruthConditionInstanceCertificate."
            in coq
            and "Check "
            "finite_registered_atomic_truth_condition_instance_lexical_3_truth_projected."
            in coq
            and "Check "
            "finite_registered_atomic_truth_condition_instance_transition_1_atomic_projected."
            in coq
        ),
        "lean finite registered atomic truth condition witness ledger": (
            lean_finite_registered_atomic_truth_condition_witness_lexical_witness_count
            == 4
            and lean_finite_registered_atomic_truth_condition_witness_lexical_truth_count
            == 4
            and lean_finite_registered_atomic_truth_condition_witness_lexical_atomic_count
            == 4
            and lean_finite_registered_atomic_truth_condition_witness_transition_witness_count
            == 1
            and lean_finite_registered_atomic_truth_condition_witness_transition_truth_count
            == 1
            and lean_finite_registered_atomic_truth_condition_witness_transition_atomic_count
            == 1
            and "structure RegisteredAtomicTruthConditionWitness "
            "(A : Type) (term : A) : Type where" in lean
            and "structure FiniteRegisteredAtomicTruthConditionWitnessLedger : Type where"
            in lean
            and "finite_registered_atomic_truth_condition_witness_source : "
            "FiniteRegisteredAtomicTruthConditionInstanceCertificate" in lean
            and "finite_registered_atomic_truth_condition_witness_lexical_3 : "
            "(x_theme : Food) -> RegisteredAtomicTruthConditionWitness Prop "
            "(eat 0 mods_nil John x_theme)" in lean
            and "def finite_registered_atomic_truth_condition_witness_ledger :"
            in lean
            and "theorem "
            "finite_registered_atomic_truth_condition_witness_ledger_exists :"
            in lean
            and "theorem "
            "finite_registered_atomic_truth_condition_witness_source_matches :"
            in lean
            and "theorem "
            "finite_registered_atomic_truth_condition_witness_sound_projected :"
            in lean
            and "theorem "
            "finite_registered_atomic_truth_condition_witness_lexical_3_projected :"
            in lean
            and "theorem "
            "finite_registered_atomic_truth_condition_witness_lexical_3_truth_projected :"
            in lean
            and "theorem "
            "finite_registered_atomic_truth_condition_witness_lexical_3_atomic_projected :"
            in lean
            and "theorem "
            "finite_registered_atomic_truth_condition_witness_transition_1_projected :"
            in lean
            and "theorem "
            "finite_registered_atomic_truth_condition_witness_transition_1_truth_projected :"
            in lean
            and "theorem "
            "finite_registered_atomic_truth_condition_witness_transition_1_atomic_projected :"
            in lean
            and "#check RegisteredAtomicTruthConditionWitness" in lean
            and "#check FiniteRegisteredAtomicTruthConditionWitnessLedger" in lean
            and "#check "
            "finite_registered_atomic_truth_condition_witness_lexical_3_projected"
            in lean
            and "#check "
            "finite_registered_atomic_truth_condition_witness_transition_1_atomic_projected"
            in lean
        ),
        "coq finite registered atomic truth condition witness ledger": (
            coq_finite_registered_atomic_truth_condition_witness_lexical_witness_count
            == 4
            and coq_finite_registered_atomic_truth_condition_witness_lexical_truth_count
            == 4
            and coq_finite_registered_atomic_truth_condition_witness_lexical_atomic_count
            == 4
            and coq_finite_registered_atomic_truth_condition_witness_transition_witness_count
            == 1
            and coq_finite_registered_atomic_truth_condition_witness_transition_truth_count
            == 1
            and coq_finite_registered_atomic_truth_condition_witness_transition_atomic_count
            == 1
            and "Record RegisteredAtomicTruthConditionWitness "
            "(A : Type) (term : A) : Type := {" in coq
            and "Record FiniteRegisteredAtomicTruthConditionWitnessLedger : Type := {"
            in coq
            and "finite_registered_atomic_truth_condition_witness_source : "
            "FiniteRegisteredAtomicTruthConditionInstanceCertificate;" in coq
            and "finite_registered_atomic_truth_condition_witness_lexical_3 : "
            "forall x_theme : Food," in coq
            and "RegisteredAtomicTruthConditionWitness Prop "
            "(eat 0 mods_nil John x_theme);" in coq
            and "Definition finite_registered_atomic_truth_condition_witness_ledger :"
            in coq
            and "Theorem "
            "finite_registered_atomic_truth_condition_witness_ledger_exists :"
            in coq
            and "Theorem "
            "finite_registered_atomic_truth_condition_witness_source_matches :"
            in coq
            and "Theorem "
            "finite_registered_atomic_truth_condition_witness_sound_projected :"
            in coq
            and "Theorem "
            "finite_registered_atomic_truth_condition_witness_lexical_3_projected :"
            in coq
            and "Theorem "
            "finite_registered_atomic_truth_condition_witness_lexical_3_truth_projected :"
            in coq
            and "Theorem "
            "finite_registered_atomic_truth_condition_witness_lexical_3_atomic_projected :"
            in coq
            and "Theorem "
            "finite_registered_atomic_truth_condition_witness_transition_1_projected :"
            in coq
            and "Theorem "
            "finite_registered_atomic_truth_condition_witness_transition_1_truth_projected :"
            in coq
            and "Theorem "
            "finite_registered_atomic_truth_condition_witness_transition_1_atomic_projected :"
            in coq
            and "Check RegisteredAtomicTruthConditionWitness." in coq
            and "Check FiniteRegisteredAtomicTruthConditionWitnessLedger." in coq
            and "Check "
            "finite_registered_atomic_truth_condition_witness_lexical_3_projected."
            in coq
            and "Check "
            "finite_registered_atomic_truth_condition_witness_transition_1_atomic_projected."
            in coq
        ),
        "lean finite registered atomic truth condition evidence ledger": (
            lean_finite_registered_atomic_truth_condition_evidence_lexical_evidence_count
            == 4
            and lean_finite_registered_atomic_truth_condition_evidence_lexical_truth_count
            == 4
            and lean_finite_registered_atomic_truth_condition_evidence_lexical_atomic_count
            == 4
            and lean_finite_registered_atomic_truth_condition_evidence_transition_evidence_count
            == 1
            and lean_finite_registered_atomic_truth_condition_evidence_transition_truth_count
            == 1
            and lean_finite_registered_atomic_truth_condition_evidence_transition_atomic_count
            == 1
            and "def registered_atomic_truth_condition_witness_evidence "
            in lean
            and "structure FiniteRegisteredAtomicTruthConditionEvidenceLedger : Type where"
            in lean
            and "finite_registered_atomic_truth_condition_evidence_source : "
            "FiniteRegisteredAtomicTruthConditionWitnessLedger" in lean
            and "finite_registered_atomic_truth_condition_witness_to_evidence :"
            in lean
            and "finite_registered_atomic_truth_condition_evidence_lexical_3 : "
            "(x_theme : Food) -> TruthEvidence "
            "(concrete_registered_truth_conditions."
            "fully_registered_truth_denotes Prop (eat 0 mods_nil John x_theme))"
            in lean
            and "def finite_registered_atomic_truth_condition_evidence_ledger :"
            in lean
            and "theorem "
            "finite_registered_atomic_truth_condition_evidence_ledger_exists :"
            in lean
            and "theorem "
            "finite_registered_atomic_truth_condition_evidence_source_matches :"
            in lean
            and "theorem "
            "finite_registered_atomic_truth_condition_witness_to_evidence_projected :"
            in lean
            and "theorem "
            "finite_registered_atomic_truth_condition_evidence_sound_projected :"
            in lean
            and "theorem "
            "finite_registered_atomic_truth_condition_evidence_lexical_3_evidence_projected :"
            in lean
            and "theorem "
            "finite_registered_atomic_truth_condition_evidence_lexical_3_truth_from_evidence_projected :"
            in lean
            and "theorem "
            "finite_registered_atomic_truth_condition_evidence_lexical_3_atomic_from_evidence_projected :"
            in lean
            and "theorem "
            "finite_registered_atomic_truth_condition_evidence_transition_1_evidence_projected :"
            in lean
            and "theorem "
            "finite_registered_atomic_truth_condition_evidence_transition_1_atomic_from_evidence_projected :"
            in lean
            and "#check registered_atomic_truth_condition_witness_evidence"
            in lean
            and "#check FiniteRegisteredAtomicTruthConditionEvidenceLedger"
            in lean
            and "#check "
            "finite_registered_atomic_truth_condition_evidence_lexical_3_evidence_projected"
            in lean
            and "#check "
            "finite_registered_atomic_truth_condition_evidence_transition_1_atomic_from_evidence_projected"
            in lean
        ),
        "coq finite registered atomic truth condition evidence ledger": (
            coq_finite_registered_atomic_truth_condition_evidence_lexical_evidence_count
            == 4
            and coq_finite_registered_atomic_truth_condition_evidence_lexical_truth_count
            == 4
            and coq_finite_registered_atomic_truth_condition_evidence_lexical_atomic_count
            == 4
            and coq_finite_registered_atomic_truth_condition_evidence_transition_evidence_count
            == 1
            and coq_finite_registered_atomic_truth_condition_evidence_transition_truth_count
            == 1
            and coq_finite_registered_atomic_truth_condition_evidence_transition_atomic_count
            == 1
            and "Definition registered_atomic_truth_condition_witness_evidence"
            in coq
            and "Record FiniteRegisteredAtomicTruthConditionEvidenceLedger : Type := {"
            in coq
            and "finite_registered_atomic_truth_condition_evidence_source : "
            "FiniteRegisteredAtomicTruthConditionWitnessLedger;" in coq
            and "finite_registered_atomic_truth_condition_witness_to_evidence :"
            in coq
            and "finite_registered_atomic_truth_condition_evidence_lexical_3 : "
            "forall x_theme : Food," in coq
            and "TruthEvidence (fully_registered_truth_denotes "
            "concrete_registered_truth_conditions Prop "
            "(eat 0 mods_nil John x_theme));" in coq
            and "Definition finite_registered_atomic_truth_condition_evidence_ledger :"
            in coq
            and "Theorem "
            "finite_registered_atomic_truth_condition_evidence_ledger_exists :"
            in coq
            and "Theorem "
            "finite_registered_atomic_truth_condition_evidence_source_matches :"
            in coq
            and "Theorem "
            "finite_registered_atomic_truth_condition_witness_to_evidence_projected :"
            in coq
            and "Theorem "
            "finite_registered_atomic_truth_condition_evidence_sound_projected :"
            in coq
            and "Theorem "
            "finite_registered_atomic_truth_condition_evidence_lexical_3_evidence_projected :"
            in coq
            and "Theorem "
            "finite_registered_atomic_truth_condition_evidence_lexical_3_truth_from_evidence_projected :"
            in coq
            and "Theorem "
            "finite_registered_atomic_truth_condition_evidence_lexical_3_atomic_from_evidence_projected :"
            in coq
            and "Theorem "
            "finite_registered_atomic_truth_condition_evidence_transition_1_evidence_projected :"
            in coq
            and "Theorem "
            "finite_registered_atomic_truth_condition_evidence_transition_1_atomic_from_evidence_projected :"
            in coq
            and "Check registered_atomic_truth_condition_witness_evidence."
            in coq
            and "Check FiniteRegisteredAtomicTruthConditionEvidenceLedger."
            in coq
            and "Check "
            "finite_registered_atomic_truth_condition_evidence_lexical_3_evidence_projected."
            in coq
            and "Check "
            "finite_registered_atomic_truth_condition_evidence_transition_1_atomic_from_evidence_projected."
            in coq
        ),
        "lean finite registered atomic truth condition evidence source alignment certificate": (
            lean_finite_registered_atomic_truth_condition_evidence_source_alignment_lexical_source_count
            == 4
            and lean_finite_registered_atomic_truth_condition_evidence_source_alignment_lexical_truth_count
            == 4
            and lean_finite_registered_atomic_truth_condition_evidence_source_alignment_lexical_atomic_count
            == 4
            and lean_finite_registered_atomic_truth_condition_evidence_source_alignment_transition_source_count
            == 1
            and lean_finite_registered_atomic_truth_condition_evidence_source_alignment_transition_truth_count
            == 1
            and lean_finite_registered_atomic_truth_condition_evidence_source_alignment_transition_atomic_count
            == 1
            and "structure FiniteRegisteredAtomicTruthConditionEvidenceSourceAlignmentCertificate : Type where"
            in lean
            and "finite_registered_atomic_truth_condition_evidence_source_alignment_sources : "
            "RegisteredEvidenceBackedTruthConditionSources" in lean
            and "finite_registered_atomic_truth_condition_evidence_source_alignment_sources_eq :"
            in lean
            and "def finite_registered_atomic_truth_condition_evidence_source_alignment_certificate :"
            in lean
            and "theorem "
            "finite_registered_atomic_truth_condition_evidence_source_alignment_certificate_exists :"
            in lean
            and "theorem "
            "finite_registered_atomic_truth_condition_evidence_source_alignment_sources_match :"
            in lean
            and "theorem "
            "finite_registered_atomic_truth_condition_evidence_source_alignment_lexical_3_source_evidence_projected :"
            in lean
            and "theorem "
            "finite_registered_atomic_truth_condition_evidence_source_alignment_lexical_3_atomic_projected :"
            in lean
            and "theorem "
            "finite_registered_atomic_truth_condition_evidence_source_alignment_transition_1_atomic_projected :"
            in lean
            and "#check "
            "FiniteRegisteredAtomicTruthConditionEvidenceSourceAlignmentCertificate"
            in lean
            and "#check "
            "finite_registered_atomic_truth_condition_evidence_source_alignment_transition_1_atomic_projected"
            in lean
        ),
        "coq finite registered atomic truth condition evidence source alignment certificate": (
            coq_finite_registered_atomic_truth_condition_evidence_source_alignment_lexical_source_count
            == 4
            and coq_finite_registered_atomic_truth_condition_evidence_source_alignment_lexical_truth_count
            == 4
            and coq_finite_registered_atomic_truth_condition_evidence_source_alignment_lexical_atomic_count
            == 4
            and coq_finite_registered_atomic_truth_condition_evidence_source_alignment_transition_source_count
            == 1
            and coq_finite_registered_atomic_truth_condition_evidence_source_alignment_transition_truth_count
            == 1
            and coq_finite_registered_atomic_truth_condition_evidence_source_alignment_transition_atomic_count
            == 1
            and "Record FiniteRegisteredAtomicTruthConditionEvidenceSourceAlignmentCertificate : Type := {"
            in coq
            and "finite_registered_atomic_truth_condition_evidence_source_alignment_sources : "
            "RegisteredEvidenceBackedTruthConditionSources;" in coq
            and "finite_registered_atomic_truth_condition_evidence_source_alignment_sources_eq :"
            in coq
            and "Definition finite_registered_atomic_truth_condition_evidence_source_alignment_certificate :"
            in coq
            and "Theorem "
            "finite_registered_atomic_truth_condition_evidence_source_alignment_certificate_exists :"
            in coq
            and "Theorem "
            "finite_registered_atomic_truth_condition_evidence_source_alignment_sources_match :"
            in coq
            and "Theorem "
            "finite_registered_atomic_truth_condition_evidence_source_alignment_lexical_3_source_evidence_projected :"
            in coq
            and "Theorem "
            "finite_registered_atomic_truth_condition_evidence_source_alignment_lexical_3_atomic_projected :"
            in coq
            and "Theorem "
            "finite_registered_atomic_truth_condition_evidence_source_alignment_transition_1_atomic_projected :"
            in coq
            and "Check "
            "FiniteRegisteredAtomicTruthConditionEvidenceSourceAlignmentCertificate."
            in coq
            and "Check "
            "finite_registered_atomic_truth_condition_evidence_source_alignment_transition_1_atomic_projected."
            in coq
        ),
        "lean finite registered atomic truth condition independent suite alignment certificate": (
            lean_finite_registered_atomic_truth_condition_independent_suite_alignment_lexical_truth_count
            == 4
            and lean_finite_registered_atomic_truth_condition_independent_suite_alignment_lexical_atomic_count
            == 4
            and lean_finite_registered_atomic_truth_condition_independent_suite_alignment_transition_truth_count
            == 1
            and lean_finite_registered_atomic_truth_condition_independent_suite_alignment_transition_atomic_count
            == 1
            and "structure FiniteRegisteredAtomicTruthConditionIndependentSuiteAlignmentCertificate : Type where"
            in lean
            and "finite_registered_atomic_truth_condition_independent_suite_alignment_suite : "
            "IndependentRegisteredTruthConditionInstanceSuite" in lean
            and "finite_registered_atomic_truth_condition_independent_suite_alignment_clause_instances : "
            "IndependentRegisteredTruthConditionClauseInstances" in lean
            and "finite_registered_atomic_truth_condition_independent_suite_alignment_spec : "
            "FullyRegisteredTruthConditionSpec" in lean
            and "def finite_registered_atomic_truth_condition_independent_suite_alignment_certificate :"
            in lean
            and "theorem "
            "finite_registered_atomic_truth_condition_independent_suite_alignment_certificate_exists :"
            in lean
            and "theorem "
            "finite_registered_atomic_truth_condition_independent_suite_alignment_suite_matches :"
            in lean
            and "theorem "
            "finite_registered_atomic_truth_condition_independent_suite_alignment_clause_instances_matches :"
            in lean
            and "theorem "
            "finite_registered_atomic_truth_condition_independent_suite_alignment_lexical_3_truth_projected :"
            in lean
            and "theorem "
            "finite_registered_atomic_truth_condition_independent_suite_alignment_lexical_3_atomic_projected :"
            in lean
            and "theorem "
            "finite_registered_atomic_truth_condition_independent_suite_alignment_transition_1_atomic_projected :"
            in lean
            and "#check "
            "FiniteRegisteredAtomicTruthConditionIndependentSuiteAlignmentCertificate"
            in lean
            and "#check "
            "finite_registered_atomic_truth_condition_independent_suite_alignment_transition_1_atomic_projected"
            in lean
        ),
        "coq finite registered atomic truth condition independent suite alignment certificate": (
            coq_finite_registered_atomic_truth_condition_independent_suite_alignment_lexical_truth_count
            == 4
            and coq_finite_registered_atomic_truth_condition_independent_suite_alignment_lexical_atomic_count
            == 4
            and coq_finite_registered_atomic_truth_condition_independent_suite_alignment_transition_truth_count
            == 1
            and coq_finite_registered_atomic_truth_condition_independent_suite_alignment_transition_atomic_count
            == 1
            and "Record FiniteRegisteredAtomicTruthConditionIndependentSuiteAlignmentCertificate : Type := {"
            in coq
            and "finite_registered_atomic_truth_condition_independent_suite_alignment_suite : "
            "IndependentRegisteredTruthConditionInstanceSuite;" in coq
            and "finite_registered_atomic_truth_condition_independent_suite_alignment_clause_instances : "
            "IndependentRegisteredTruthConditionClauseInstances;" in coq
            and "finite_registered_atomic_truth_condition_independent_suite_alignment_spec : "
            "FullyRegisteredTruthConditionSpec;" in coq
            and "Definition finite_registered_atomic_truth_condition_independent_suite_alignment_certificate :"
            in coq
            and "Theorem "
            "finite_registered_atomic_truth_condition_independent_suite_alignment_certificate_exists :"
            in coq
            and "Theorem "
            "finite_registered_atomic_truth_condition_independent_suite_alignment_suite_matches :"
            in coq
            and "Theorem "
            "finite_registered_atomic_truth_condition_independent_suite_alignment_clause_instances_matches :"
            in coq
            and "Theorem "
            "finite_registered_atomic_truth_condition_independent_suite_alignment_lexical_3_truth_projected :"
            in coq
            and "Theorem "
            "finite_registered_atomic_truth_condition_independent_suite_alignment_lexical_3_atomic_projected :"
            in coq
            and "Theorem "
            "finite_registered_atomic_truth_condition_independent_suite_alignment_transition_1_atomic_projected :"
            in coq
            and "Check "
            "FiniteRegisteredAtomicTruthConditionIndependentSuiteAlignmentCertificate."
            in coq
            and "Check "
            "finite_registered_atomic_truth_condition_independent_suite_alignment_transition_1_atomic_projected."
            in coq
        ),
        "lean finite registered atomic truth condition instance discharge certificate": (
            lean_finite_registered_atomic_truth_condition_discharge_lexical_truth_count
            == 4
            and lean_finite_registered_atomic_truth_condition_discharge_lexical_atomic_count
            == 4
            and lean_finite_registered_atomic_truth_condition_discharge_transition_truth_count
            == 1
            and lean_finite_registered_atomic_truth_condition_discharge_transition_atomic_count
            == 1
            and "structure FiniteRegisteredAtomicTruthConditionInstanceDischargeCertificate : Type where"
            in lean
            and "finite_registered_atomic_truth_condition_discharge_alignment : "
            "FiniteRegisteredAtomicTruthConditionIndependentSuiteAlignmentCertificate"
            in lean
            and "finite_registered_atomic_truth_condition_discharge_spec : "
            "FullyRegisteredTruthConditionSpec" in lean
            and "def finite_registered_atomic_truth_condition_instance_discharge_certificate :"
            in lean
            and "theorem "
            "finite_registered_atomic_truth_condition_instance_discharge_certificate_exists :"
            in lean
            and "theorem "
            "finite_registered_atomic_truth_condition_discharge_alignment_matches :"
            in lean
            and "theorem "
            "finite_registered_atomic_truth_condition_discharge_spec_matches :"
            in lean
            and "theorem "
            "finite_registered_atomic_truth_condition_discharge_truth_sound_projected :"
            in lean
            and "theorem "
            "finite_registered_atomic_truth_condition_discharge_lexical_3_truth_projected :"
            in lean
            and "theorem "
            "finite_registered_atomic_truth_condition_discharge_lexical_3_atomic_projected :"
            in lean
            and "theorem "
            "finite_registered_atomic_truth_condition_discharge_transition_1_atomic_projected :"
            in lean
            and "#check "
            "FiniteRegisteredAtomicTruthConditionInstanceDischargeCertificate"
            in lean
            and "#check "
            "finite_registered_atomic_truth_condition_discharge_transition_1_atomic_projected"
            in lean
        ),
        "coq finite registered atomic truth condition instance discharge certificate": (
            coq_finite_registered_atomic_truth_condition_discharge_lexical_truth_count
            == 4
            and coq_finite_registered_atomic_truth_condition_discharge_lexical_atomic_count
            == 4
            and coq_finite_registered_atomic_truth_condition_discharge_transition_truth_count
            == 1
            and coq_finite_registered_atomic_truth_condition_discharge_transition_atomic_count
            == 1
            and "Record FiniteRegisteredAtomicTruthConditionInstanceDischargeCertificate : Type := {"
            in coq
            and "finite_registered_atomic_truth_condition_discharge_alignment : "
            "FiniteRegisteredAtomicTruthConditionIndependentSuiteAlignmentCertificate;"
            in coq
            and "finite_registered_atomic_truth_condition_discharge_spec : "
            "FullyRegisteredTruthConditionSpec;" in coq
            and "Definition finite_registered_atomic_truth_condition_instance_discharge_certificate :"
            in coq
            and "Theorem "
            "finite_registered_atomic_truth_condition_instance_discharge_certificate_exists :"
            in coq
            and "Theorem "
            "finite_registered_atomic_truth_condition_discharge_alignment_matches :"
            in coq
            and "Theorem "
            "finite_registered_atomic_truth_condition_discharge_spec_matches :"
            in coq
            and "Theorem "
            "finite_registered_atomic_truth_condition_discharge_truth_sound_projected :"
            in coq
            and "Theorem "
            "finite_registered_atomic_truth_condition_discharge_lexical_3_truth_projected :"
            in coq
            and "Theorem "
            "finite_registered_atomic_truth_condition_discharge_lexical_3_atomic_projected :"
            in coq
            and "Theorem "
            "finite_registered_atomic_truth_condition_discharge_transition_1_atomic_projected :"
            in coq
            and "Check "
            "FiniteRegisteredAtomicTruthConditionInstanceDischargeCertificate."
            in coq
            and "Check "
            "finite_registered_atomic_truth_condition_discharge_transition_1_atomic_projected."
            in coq
        ),
        "lean finite registered atomic truth condition typed discharge certificate": (
            lean_finite_registered_atomic_truth_condition_typed_lexical_atom_count
            == 4
            and lean_finite_registered_atomic_truth_condition_typed_lexical_truth_count
            == 4
            and lean_finite_registered_atomic_truth_condition_typed_lexical_atomic_count
            == 4
            and lean_finite_registered_atomic_truth_condition_typed_transition_atom_count
            == 1
            and lean_finite_registered_atomic_truth_condition_typed_transition_truth_count
            == 1
            and lean_finite_registered_atomic_truth_condition_typed_transition_atomic_count
            == 1
            and "structure RegisteredTruthConditionAtom : Type where" in lean
            and "structure RegisteredTruthConditionAtomDischarge "
            "(atom : RegisteredTruthConditionAtom) : Type where" in lean
            and "structure FiniteRegisteredAtomicTruthConditionTypedDischargeCertificate : Type where"
            in lean
            and "def finite_registered_atomic_truth_condition_typed_discharge_certificate :"
            in lean
            and "theorem "
            "finite_registered_atomic_truth_condition_typed_discharge_certificate_exists :"
            in lean
            and "theorem "
            "finite_registered_atomic_truth_condition_typed_discharge_source_matches :"
            in lean
            and "theorem "
            "finite_registered_atomic_truth_condition_typed_discharge_sound_projected :"
            in lean
            and "theorem "
            "finite_registered_atomic_truth_condition_typed_discharge_lexical_3_projected :"
            in lean
            and "theorem "
            "finite_registered_atomic_truth_condition_typed_discharge_lexical_3_atomic_projected :"
            in lean
            and "theorem "
            "finite_registered_atomic_truth_condition_typed_discharge_transition_1_atomic_projected :"
            in lean
            and "#check "
            "FiniteRegisteredAtomicTruthConditionTypedDischargeCertificate"
            in lean
            and "#check "
            "finite_registered_atomic_truth_condition_typed_discharge_transition_1_atomic_projected"
            in lean
        ),
        "coq finite registered atomic truth condition typed discharge certificate": (
            coq_finite_registered_atomic_truth_condition_typed_lexical_atom_count
            == 4
            and coq_finite_registered_atomic_truth_condition_typed_lexical_truth_count
            == 4
            and coq_finite_registered_atomic_truth_condition_typed_lexical_atomic_count
            == 4
            and coq_finite_registered_atomic_truth_condition_typed_transition_atom_count
            == 1
            and coq_finite_registered_atomic_truth_condition_typed_transition_truth_count
            == 1
            and coq_finite_registered_atomic_truth_condition_typed_transition_atomic_count
            == 1
            and "Record RegisteredTruthConditionAtom : Type := {" in coq
            and "Record RegisteredTruthConditionAtomDischarge "
            "(atom : RegisteredTruthConditionAtom) : Type := {" in coq
            and "Record FiniteRegisteredAtomicTruthConditionTypedDischargeCertificate : Type := {"
            in coq
            and "Definition finite_registered_atomic_truth_condition_typed_discharge_certificate :"
            in coq
            and "Theorem "
            "finite_registered_atomic_truth_condition_typed_discharge_certificate_exists :"
            in coq
            and "Theorem "
            "finite_registered_atomic_truth_condition_typed_discharge_source_matches :"
            in coq
            and "Theorem "
            "finite_registered_atomic_truth_condition_typed_discharge_sound_projected :"
            in coq
            and "Theorem "
            "finite_registered_atomic_truth_condition_typed_discharge_lexical_3_projected :"
            in coq
            and "Theorem "
            "finite_registered_atomic_truth_condition_typed_discharge_lexical_3_atomic_projected :"
            in coq
            and "Theorem "
            "finite_registered_atomic_truth_condition_typed_discharge_transition_1_atomic_projected :"
            in coq
            and "Check "
            "FiniteRegisteredAtomicTruthConditionTypedDischargeCertificate."
            in coq
            and "Check "
            "finite_registered_atomic_truth_condition_typed_discharge_transition_1_atomic_projected."
            in coq
        ),
        "lean registered truth condition constructor discharge certificate": (
            "structure RegisteredTruthConditionConstructorDischargeCertificate : Type where"
            in lean
            and "def registered_truth_condition_constructor_discharge_certificate :"
            in lean
            and "theorem "
            "registered_truth_condition_constructor_discharge_certificate_exists :"
            in lean
            and "theorem "
            "registered_truth_condition_constructor_discharge_source_matches :"
            in lean
            and "theorem "
            "registered_truth_condition_constructor_discharge_spec_matches :"
            in lean
            and "theorem "
            "registered_truth_condition_constructor_discharge_lexical_application_projected :"
            in lean
            and "theorem "
            "registered_truth_condition_constructor_discharge_sigma_Entity_projected :"
            in lean
            and "theorem "
            "registered_truth_condition_constructor_discharge_cause_projected :"
            in lean
            and "#check RegisteredTruthConditionConstructorDischargeCertificate"
            in lean
            and "#check registered_truth_condition_constructor_discharge_spec_sound_projected"
            in lean
        ),
        "coq registered truth condition constructor discharge certificate": (
            "Record RegisteredTruthConditionConstructorDischargeCertificate : Type := {"
            in coq
            and "Definition registered_truth_condition_constructor_discharge_certificate :"
            in coq
            and "Theorem "
            "registered_truth_condition_constructor_discharge_certificate_exists :"
            in coq
            and "Theorem "
            "registered_truth_condition_constructor_discharge_source_matches :"
            in coq
            and "Theorem "
            "registered_truth_condition_constructor_discharge_spec_matches :"
            in coq
            and "Theorem "
            "registered_truth_condition_constructor_discharge_lexical_application_projected :"
            in coq
            and "Theorem "
            "registered_truth_condition_constructor_discharge_sigma_Entity_projected :"
            in coq
            and "Theorem "
            "registered_truth_condition_constructor_discharge_cause_projected :"
            in coq
            and "Check RegisteredTruthConditionConstructorDischargeCertificate."
            in coq
            and "Check registered_truth_condition_constructor_discharge_spec_sound_projected."
            in coq
        ),
        "lean registered truth condition constructor class discharge suite": (
            "structure RegisteredLexicalConstructorDischarge : Type where"
            in lean
            and "structure RegisteredSigmaConstructorDischarge : Type where"
            in lean
            and "structure RegisteredTemporalConstructorDischarge : Type where"
            in lean
            and "structure RegisteredRepeatConstructorDischarge : Type where"
            in lean
            and "structure RegisteredPolarityConstructorDischarge : Type where"
            in lean
            and "structure RegisteredTransitionCauseConstructorDischarge : Type where"
            in lean
            and "structure RegisteredTruthConditionConstructorClassDischargeSuite : Type where"
            in lean
            and "def registered_truth_condition_constructor_class_discharge_suite :"
            in lean
            and "theorem "
            "registered_truth_condition_constructor_class_discharge_suite_exists :"
            in lean
            and "theorem registered_lexical_constructor_discharge_application_projected :"
            in lean
            and "theorem registered_sigma_constructor_discharge_Entity_projected :"
            in lean
            and "theorem registered_temporal_constructor_discharge_at_T_projected :"
            in lean
            and "theorem registered_transition_cause_constructor_discharge_cause_projected :"
            in lean
            and "#check RegisteredTruthConditionConstructorClassDischargeSuite"
            in lean
            and "#check registered_constructor_class_discharge_suite_spec_sound_projected"
            in lean
        ),
        "coq registered truth condition constructor class discharge suite": (
            "Record RegisteredLexicalConstructorDischarge : Type := {" in coq
            and "Record RegisteredSigmaConstructorDischarge : Type := {" in coq
            and "Record RegisteredTemporalConstructorDischarge : Type := {" in coq
            and "Record RegisteredRepeatConstructorDischarge : Type := {" in coq
            and "Record RegisteredPolarityConstructorDischarge : Type := {" in coq
            and "Record RegisteredTransitionCauseConstructorDischarge : Type := {"
            in coq
            and "Record RegisteredTruthConditionConstructorClassDischargeSuite : Type := {"
            in coq
            and "Definition registered_truth_condition_constructor_class_discharge_suite :"
            in coq
            and "Theorem "
            "registered_truth_condition_constructor_class_discharge_suite_exists :"
            in coq
            and "Theorem registered_lexical_constructor_discharge_application_projected :"
            in coq
            and "Theorem registered_sigma_constructor_discharge_Entity_projected :"
            in coq
            and "Theorem registered_temporal_constructor_discharge_at_T_projected :"
            in coq
            and "Theorem registered_transition_cause_constructor_discharge_cause_projected :"
            in coq
            and "Check RegisteredTruthConditionConstructorClassDischargeSuite."
            in coq
            and "Check registered_constructor_class_discharge_suite_spec_sound_projected."
            in coq
        ),
        "lean registered truth condition constructor class projection coverage": (
            "structure RegisteredTruthConditionConstructorClassProjectionCoverageCertificate : Type where"
            in lean
            and "def registered_truth_condition_constructor_class_projection_coverage_certificate :"
            in lean
            and "theorem "
            "registered_truth_condition_constructor_class_projection_coverage_certificate_exists :"
            in lean
            and "theorem registered_constructor_class_projection_coverage_source_matches :"
            in lean
            and "theorem registered_constructor_class_projection_coverage_sigma_Food_projected :"
            in lean
            and "theorem registered_constructor_class_projection_coverage_sigma_TransitionT_projected :"
            in lean
            and "theorem registered_constructor_class_projection_coverage_during_T_projected :"
            in lean
            and "theorem registered_constructor_class_projection_coverage_since_T_projected :"
            in lean
            and "theorem registered_constructor_class_projection_coverage_cause_projected :"
            in lean
            and "#check RegisteredTruthConditionConstructorClassProjectionCoverageCertificate"
            in lean
            and "#check registered_constructor_class_projection_coverage_spec_sound_projected"
            in lean
        ),
        "coq registered truth condition constructor class projection coverage": (
            "Record RegisteredTruthConditionConstructorClassProjectionCoverageCertificate : Type := {"
            in coq
            and "Definition registered_truth_condition_constructor_class_projection_coverage_certificate :"
            in coq
            and "Theorem "
            "registered_truth_condition_constructor_class_projection_coverage_certificate_exists :"
            in coq
            and "Theorem registered_constructor_class_projection_coverage_source_matches :"
            in coq
            and "Theorem registered_constructor_class_projection_coverage_sigma_Food_projected :"
            in coq
            and "Theorem registered_constructor_class_projection_coverage_sigma_TransitionT_projected :"
            in coq
            and "Theorem registered_constructor_class_projection_coverage_during_T_projected :"
            in coq
            and "Theorem registered_constructor_class_projection_coverage_since_T_projected :"
            in coq
            and "Theorem registered_constructor_class_projection_coverage_cause_projected :"
            in coq
            and "Check RegisteredTruthConditionConstructorClassProjectionCoverageCertificate."
            in coq
            and "Check registered_constructor_class_projection_coverage_spec_sound_projected."
            in coq
        ),
        "lean registered truth condition constructor class projection obligation ledger": (
            "structure RegisteredTruthConditionConstructorClassProjectionObligationLedger : Type where"
            in lean
            and "def registered_truth_condition_constructor_class_projection_obligation_ledger :"
            in lean
            and "theorem "
            "registered_truth_condition_constructor_class_projection_obligation_ledger_exists :"
            in lean
            and "theorem registered_constructor_class_projection_obligation_ledger_source_matches :"
            in lean
            and "theorem registered_constructor_class_projection_obligation_ledger_sigma_Food_projected :"
            in lean
            and "theorem registered_constructor_class_projection_obligation_ledger_sigma_TransitionT_projected :"
            in lean
            and "theorem registered_constructor_class_projection_obligation_ledger_during_T_projected :"
            in lean
            and "theorem registered_constructor_class_projection_obligation_ledger_since_T_projected :"
            in lean
            and "theorem registered_constructor_class_projection_obligation_ledger_cause_projected :"
            in lean
            and "#check RegisteredTruthConditionConstructorClassProjectionObligationLedger"
            in lean
            and "#check registered_constructor_class_projection_obligation_ledger_spec_sound_projected"
            in lean
        ),
        "coq registered truth condition constructor class projection obligation ledger": (
            "Record RegisteredTruthConditionConstructorClassProjectionObligationLedger : Type := {"
            in coq
            and "Definition registered_truth_condition_constructor_class_projection_obligation_ledger :"
            in coq
            and "Theorem "
            "registered_truth_condition_constructor_class_projection_obligation_ledger_exists :"
            in coq
            and "Theorem registered_constructor_class_projection_obligation_ledger_source_matches :"
            in coq
            and "Theorem registered_constructor_class_projection_obligation_ledger_sigma_Food_projected :"
            in coq
            and "Theorem registered_constructor_class_projection_obligation_ledger_sigma_TransitionT_projected :"
            in coq
            and "Theorem registered_constructor_class_projection_obligation_ledger_during_T_projected :"
            in coq
            and "Theorem registered_constructor_class_projection_obligation_ledger_since_T_projected :"
            in coq
            and "Theorem registered_constructor_class_projection_obligation_ledger_cause_projected :"
            in coq
            and "Check RegisteredTruthConditionConstructorClassProjectionObligationLedger."
            in coq
            and "Check registered_constructor_class_projection_obligation_ledger_spec_sound_projected."
            in coq
        ),
        "lean finite registered atomic constructor obligation alignment certificate": (
            "structure FiniteRegisteredAtomicConstructorObligationAlignmentCertificate : Type where"
            in lean
            and "def finite_registered_atomic_constructor_obligation_alignment_certificate :"
            in lean
            and "theorem "
            "finite_registered_atomic_constructor_obligation_alignment_certificate_exists :"
            in lean
            and "theorem finite_registered_atomic_constructor_obligation_alignment_typed_source_matches :"
            in lean
            and "theorem finite_registered_atomic_constructor_obligation_alignment_ledger_matches :"
            in lean
            and "theorem finite_registered_atomic_constructor_obligation_alignment_lexical_1_truth_projected :"
            in lean
            and "theorem finite_registered_atomic_constructor_obligation_alignment_lexical_1_atomic_projected :"
            in lean
            and "theorem finite_registered_atomic_constructor_obligation_alignment_transition_1_truth_projected :"
            in lean
            and "theorem finite_registered_atomic_constructor_obligation_alignment_transition_1_atomic_projected :"
            in lean
            and "#check FiniteRegisteredAtomicConstructorObligationAlignmentCertificate"
            in lean
            and "#check finite_registered_atomic_constructor_obligation_alignment_transition_1_atomic_from_certificate"
            in lean
        ),
        "coq finite registered atomic constructor obligation alignment certificate": (
            "Record FiniteRegisteredAtomicConstructorObligationAlignmentCertificate : Type := {"
            in coq
            and "Definition finite_registered_atomic_constructor_obligation_alignment_certificate :"
            in coq
            and "Theorem "
            "finite_registered_atomic_constructor_obligation_alignment_certificate_exists :"
            in coq
            and "Theorem finite_registered_atomic_constructor_obligation_alignment_typed_source_matches :"
            in coq
            and "Theorem finite_registered_atomic_constructor_obligation_alignment_ledger_matches :"
            in coq
            and "Theorem finite_registered_atomic_constructor_obligation_alignment_lexical_1_truth_projected :"
            in coq
            and "Theorem finite_registered_atomic_constructor_obligation_alignment_lexical_1_atomic_projected :"
            in coq
            and "Theorem finite_registered_atomic_constructor_obligation_alignment_transition_1_truth_projected :"
            in coq
            and "Theorem finite_registered_atomic_constructor_obligation_alignment_transition_1_atomic_projected :"
            in coq
            and "Check FiniteRegisteredAtomicConstructorObligationAlignmentCertificate."
            in coq
            and "Check finite_registered_atomic_constructor_obligation_alignment_transition_1_atomic_from_certificate."
            in coq
        ),
        "lean finite registered atomic concrete route comparison certificate": (
            "structure FiniteRegisteredAtomicConcreteRouteComparisonCertificate : Type where"
            in lean
            and "def finite_registered_atomic_concrete_route_comparison_certificate :"
            in lean
            and "theorem "
            "finite_registered_atomic_concrete_route_comparison_certificate_exists :"
            in lean
            and "theorem finite_registered_atomic_concrete_route_comparison_constructor_alignment_matches :"
            in lean
            and "theorem finite_registered_atomic_concrete_route_comparison_direct_spec_matches :"
            in lean
            and "theorem finite_registered_atomic_concrete_route_comparison_evidence_spec_matches :"
            in lean
            and "theorem finite_registered_atomic_concrete_route_comparison_kernel_spec_matches :"
            in lean
            and "theorem finite_registered_atomic_concrete_route_comparison_lexical_1_direct_truth_projected :"
            in lean
            and "theorem finite_registered_atomic_concrete_route_comparison_lexical_1_evidence_truth_projected :"
            in lean
            and "theorem finite_registered_atomic_concrete_route_comparison_lexical_1_kernel_truth_projected :"
            in lean
            and "theorem finite_registered_atomic_concrete_route_comparison_transition_1_kernel_atomic_projected :"
            in lean
            and "#check FiniteRegisteredAtomicConcreteRouteComparisonCertificate"
            in lean
            and "#check finite_registered_atomic_concrete_route_comparison_transition_1_kernel_atomic_projected"
            in lean
        ),
        "coq finite registered atomic concrete route comparison certificate": (
            "Record FiniteRegisteredAtomicConcreteRouteComparisonCertificate : Type := {"
            in coq
            and "Definition finite_registered_atomic_concrete_route_comparison_certificate :"
            in coq
            and "Theorem "
            "finite_registered_atomic_concrete_route_comparison_certificate_exists :"
            in coq
            and "Theorem finite_registered_atomic_concrete_route_comparison_constructor_alignment_matches :"
            in coq
            and "Theorem finite_registered_atomic_concrete_route_comparison_direct_spec_matches :"
            in coq
            and "Theorem finite_registered_atomic_concrete_route_comparison_evidence_spec_matches :"
            in coq
            and "Theorem finite_registered_atomic_concrete_route_comparison_kernel_spec_matches :"
            in coq
            and "Theorem finite_registered_atomic_concrete_route_comparison_lexical_1_direct_truth_projected :"
            in coq
            and "Theorem finite_registered_atomic_concrete_route_comparison_lexical_1_evidence_truth_projected :"
            in coq
            and "Theorem finite_registered_atomic_concrete_route_comparison_lexical_1_kernel_truth_projected :"
            in coq
            and "Theorem finite_registered_atomic_concrete_route_comparison_transition_1_kernel_atomic_projected :"
            in coq
            and "Check FiniteRegisteredAtomicConcreteRouteComparisonCertificate."
            in coq
            and "Check finite_registered_atomic_concrete_route_comparison_transition_1_kernel_atomic_projected."
            in coq
        ),
        "lean finite registered atomic concrete truth closure certificate": (
            "structure FiniteRegisteredAtomicConcreteTruthClosureCertificate : Type where"
            in lean
            and "def finite_registered_atomic_concrete_truth_closure_certificate :"
            in lean
            and "theorem "
            "finite_registered_atomic_concrete_truth_closure_certificate_exists :"
            in lean
            and "theorem finite_registered_atomic_concrete_truth_closure_route_comparison_matches :"
            in lean
            and "theorem finite_registered_atomic_concrete_truth_closure_basis_matches :"
            in lean
            and "theorem finite_registered_atomic_concrete_truth_closure_to_direct_spec_projected :"
            in lean
            and "theorem finite_registered_atomic_concrete_truth_closure_to_atomic_projected :"
            in lean
            and "theorem finite_registered_atomic_concrete_truth_closure_lexical_1_concrete_projected :"
            in lean
            and "theorem finite_registered_atomic_concrete_truth_closure_lexical_1_direct_from_closure :"
            in lean
            and "theorem finite_registered_atomic_concrete_truth_closure_transition_1_atomic_from_closure :"
            in lean
            and "#check FiniteRegisteredAtomicConcreteTruthClosureCertificate"
            in lean
            and "#check finite_registered_atomic_concrete_truth_closure_transition_1_atomic_from_closure"
            in lean
        ),
        "coq finite registered atomic concrete truth closure certificate": (
            "Record FiniteRegisteredAtomicConcreteTruthClosureCertificate : Type := {"
            in coq
            and "Definition finite_registered_atomic_concrete_truth_closure_certificate :"
            in coq
            and "Theorem "
            "finite_registered_atomic_concrete_truth_closure_certificate_exists :"
            in coq
            and "Theorem finite_registered_atomic_concrete_truth_closure_route_comparison_matches :"
            in coq
            and "Theorem finite_registered_atomic_concrete_truth_closure_basis_matches :"
            in coq
            and "Theorem finite_registered_atomic_concrete_truth_closure_to_direct_spec_projected :"
            in coq
            and "Theorem finite_registered_atomic_concrete_truth_closure_to_atomic_projected :"
            in coq
            and "Theorem finite_registered_atomic_concrete_truth_closure_lexical_1_concrete_projected :"
            in coq
            and "Theorem finite_registered_atomic_concrete_truth_closure_lexical_1_direct_from_closure :"
            in coq
            and "Theorem finite_registered_atomic_concrete_truth_closure_transition_1_atomic_from_closure :"
            in coq
            and "Check FiniteRegisteredAtomicConcreteTruthClosureCertificate."
            in coq
            and "Check finite_registered_atomic_concrete_truth_closure_transition_1_atomic_from_closure."
            in coq
        ),
        "lean finite registered atomic concrete truth instance ledger": (
            "structure ConcreteRegisteredTruthInstance (atom : RegisteredTruthConditionAtom) : Type where"
            in lean
            and "structure FiniteRegisteredAtomicConcreteTruthInstanceLedger : Type where"
            in lean
            and "def finite_registered_atomic_concrete_truth_instance_ledger :"
            in lean
            and "theorem finite_registered_atomic_concrete_truth_instance_ledger_exists :"
            in lean
            and "theorem finite_registered_atomic_concrete_truth_instance_ledger_source_matches :"
            in lean
            and "theorem finite_registered_atomic_concrete_truth_instance_ledger_sound_projected :"
            in lean
            and "theorem finite_registered_atomic_concrete_truth_instance_lexical_1_direct_projected :"
            in lean
            and "theorem finite_registered_atomic_concrete_truth_instance_ledger_lexical_1_direct_projected :"
            in lean
            and "theorem finite_registered_atomic_concrete_truth_instance_ledger_transition_1_atomic_projected :"
            in lean
            and "#check ConcreteRegisteredTruthInstance" in lean
            and "#check finite_registered_atomic_concrete_truth_instance_ledger_transition_1_atomic_projected"
            in lean
        ),
        "coq finite registered atomic concrete truth instance ledger": (
            "Record ConcreteRegisteredTruthInstance (atom : RegisteredTruthConditionAtom) : Type := {"
            in coq
            and "Record FiniteRegisteredAtomicConcreteTruthInstanceLedger : Type := {"
            in coq
            and "Definition finite_registered_atomic_concrete_truth_instance_ledger :"
            in coq
            and "Theorem finite_registered_atomic_concrete_truth_instance_ledger_exists :"
            in coq
            and "Theorem finite_registered_atomic_concrete_truth_instance_ledger_source_matches :"
            in coq
            and "Theorem finite_registered_atomic_concrete_truth_instance_ledger_sound_projected :"
            in coq
            and "Theorem finite_registered_atomic_concrete_truth_instance_lexical_1_direct_projected :"
            in coq
            and "Theorem finite_registered_atomic_concrete_truth_instance_ledger_lexical_1_direct_projected :"
            in coq
            and "Theorem finite_registered_atomic_concrete_truth_instance_ledger_transition_1_atomic_projected :"
            in coq
            and "Check ConcreteRegisteredTruthInstance." in coq
            and "Check finite_registered_atomic_concrete_truth_instance_ledger_transition_1_atomic_projected."
            in coq
        ),
        "lean finite registered atomic concrete truth provider certificate": (
            "structure FiniteRegisteredAtomicConcreteTruthProviderCertificate : Type where"
            in lean
            and "def finite_registered_atomic_concrete_truth_provider_certificate :"
            in lean
            and "theorem finite_registered_atomic_concrete_truth_provider_certificate_exists :"
            in lean
            and "theorem finite_registered_atomic_concrete_truth_provider_ledger_matches :"
            in lean
            and "theorem finite_registered_atomic_concrete_truth_provider_suite_matches :"
            in lean
            and "theorem finite_registered_atomic_concrete_truth_provider_suite_sound_projected :"
            in lean
            and "theorem finite_registered_atomic_concrete_truth_provider_lexical_1_direct_truth_projected :"
            in lean
            and "theorem finite_registered_atomic_concrete_truth_provider_lexical_1_suite_truth_projected :"
            in lean
            and "theorem finite_registered_atomic_concrete_truth_provider_transition_1_suite_atomic_projected :"
            in lean
            and "#check FiniteRegisteredAtomicConcreteTruthProviderCertificate"
            in lean
            and "#check finite_registered_atomic_concrete_truth_provider_transition_1_suite_atomic_projected"
            in lean
        ),
        "coq finite registered atomic concrete truth provider certificate": (
            "Record FiniteRegisteredAtomicConcreteTruthProviderCertificate : Type := {"
            in coq
            and "Definition finite_registered_atomic_concrete_truth_provider_certificate :"
            in coq
            and "Theorem finite_registered_atomic_concrete_truth_provider_certificate_exists :"
            in coq
            and "Theorem finite_registered_atomic_concrete_truth_provider_ledger_matches :"
            in coq
            and "Theorem finite_registered_atomic_concrete_truth_provider_suite_matches :"
            in coq
            and "Theorem finite_registered_atomic_concrete_truth_provider_suite_sound_projected :"
            in coq
            and "Theorem finite_registered_atomic_concrete_truth_provider_lexical_1_direct_truth_projected :"
            in coq
            and "Theorem finite_registered_atomic_concrete_truth_provider_lexical_1_suite_truth_projected :"
            in coq
            and "Theorem finite_registered_atomic_concrete_truth_provider_transition_1_suite_atomic_projected :"
            in coq
            and "Check FiniteRegisteredAtomicConcreteTruthProviderCertificate."
            in coq
            and "Check finite_registered_atomic_concrete_truth_provider_transition_1_suite_atomic_projected."
            in coq
        ),
        "lean finite registered atomic concrete truth provider interface certificate": (
            "structure ConcreteTruthConditionProviderInterface : Type where"
            in lean
            and "def concrete_truth_condition_provider_interface :"
            in lean
            and "theorem concrete_truth_condition_provider_interface_exists :"
            in lean
            and "theorem concrete_truth_condition_provider_direct_spec_matches :"
            in lean
            and "theorem concrete_truth_condition_provider_independent_spec_matches :"
            in lean
            and "theorem concrete_truth_condition_provider_certificate_matches :"
            in lean
            and "theorem concrete_truth_condition_provider_direct_sound_projected :"
            in lean
            and "theorem concrete_truth_condition_provider_independent_sound_projected :"
            in lean
            and "structure FiniteRegisteredAtomicConcreteTruthProviderInterfaceCertificate : Type where"
            in lean
            and "def finite_registered_atomic_concrete_truth_provider_interface_certificate :"
            in lean
            and "theorem finite_registered_atomic_concrete_truth_provider_interface_certificate_exists :"
            in lean
            and "theorem finite_registered_atomic_concrete_truth_provider_interface_source_matches :"
            in lean
            and "theorem finite_registered_atomic_concrete_truth_provider_interface_lexical_1_direct_atomic_projected :"
            in lean
            and "theorem finite_registered_atomic_concrete_truth_provider_interface_transition_1_suite_atomic_projected :"
            in lean
            and "#check ConcreteTruthConditionProviderInterface" in lean
            and "#check finite_registered_atomic_concrete_truth_provider_interface_transition_1_suite_atomic_projected"
            in lean
        ),
        "coq finite registered atomic concrete truth provider interface certificate": (
            "Record ConcreteTruthConditionProviderInterface : Type := {"
            in coq
            and "Definition concrete_truth_condition_provider_interface :"
            in coq
            and "Theorem concrete_truth_condition_provider_interface_exists :"
            in coq
            and "Theorem concrete_truth_condition_provider_direct_spec_matches :"
            in coq
            and "Theorem concrete_truth_condition_provider_independent_spec_matches :"
            in coq
            and "Theorem concrete_truth_condition_provider_certificate_matches :"
            in coq
            and "Theorem concrete_truth_condition_provider_direct_sound_projected :"
            in coq
            and "Theorem concrete_truth_condition_provider_independent_sound_projected :"
            in coq
            and "Record FiniteRegisteredAtomicConcreteTruthProviderInterfaceCertificate : Type := {"
            in coq
            and "Definition finite_registered_atomic_concrete_truth_provider_interface_certificate :"
            in coq
            and "Theorem finite_registered_atomic_concrete_truth_provider_interface_certificate_exists :"
            in coq
            and "Theorem finite_registered_atomic_concrete_truth_provider_interface_source_matches :"
            in coq
            and "Theorem finite_registered_atomic_concrete_truth_provider_interface_lexical_1_direct_atomic_projected :"
            in coq
            and "Theorem finite_registered_atomic_concrete_truth_provider_interface_transition_1_suite_atomic_projected :"
            in coq
            and "Check ConcreteTruthConditionProviderInterface." in coq
            and "Check finite_registered_atomic_concrete_truth_provider_interface_transition_1_suite_atomic_projected."
            in coq
        ),
        "lean concrete truth provider class obligation suite": (
            "structure ConcreteTruthConditionProviderClassObligationSuite : Type where"
            in lean
            and "def concrete_truth_condition_provider_class_obligation_suite :"
            in lean
            and "theorem concrete_truth_condition_provider_class_obligation_suite_exists :"
            in lean
            and "theorem concrete_truth_condition_provider_class_obligation_source_matches :"
            in lean
            and "theorem concrete_truth_condition_provider_class_obligation_ledger_matches :"
            in lean
            and "theorem concrete_truth_condition_provider_class_obligation_direct_sound_projected :"
            in lean
            and "theorem concrete_truth_condition_provider_class_obligation_independent_sound_projected :"
            in lean
            and "theorem concrete_truth_condition_provider_class_obligation_ledger_lexical_application_projected :"
            in lean
            and "theorem concrete_truth_condition_provider_class_obligation_ledger_sigma_Food_projected :"
            in lean
            and "theorem concrete_truth_condition_provider_class_obligation_ledger_since_T_projected :"
            in lean
            and "theorem concrete_truth_condition_provider_class_obligation_ledger_cause_projected :"
            in lean
            and "#check ConcreteTruthConditionProviderClassObligationSuite"
            in lean
            and "#check concrete_truth_condition_provider_class_obligation_ledger_spec_sound_projected"
            in lean
        ),
        "coq concrete truth provider class obligation suite": (
            "Record ConcreteTruthConditionProviderClassObligationSuite : Type := {"
            in coq
            and "Definition concrete_truth_condition_provider_class_obligation_suite :"
            in coq
            and "Theorem concrete_truth_condition_provider_class_obligation_suite_exists :"
            in coq
            and "Theorem concrete_truth_condition_provider_class_obligation_source_matches :"
            in coq
            and "Theorem concrete_truth_condition_provider_class_obligation_ledger_matches :"
            in coq
            and "Theorem concrete_truth_condition_provider_class_obligation_direct_sound_projected :"
            in coq
            and "Theorem concrete_truth_condition_provider_class_obligation_independent_sound_projected :"
            in coq
            and "Theorem concrete_truth_condition_provider_class_obligation_ledger_lexical_application_projected :"
            in coq
            and "Theorem concrete_truth_condition_provider_class_obligation_ledger_sigma_Food_projected :"
            in coq
            and "Theorem concrete_truth_condition_provider_class_obligation_ledger_since_T_projected :"
            in coq
            and "Theorem concrete_truth_condition_provider_class_obligation_ledger_cause_projected :"
            in coq
            and "Check ConcreteTruthConditionProviderClassObligationSuite."
            in coq
            and "Check concrete_truth_condition_provider_class_obligation_ledger_spec_sound_projected."
            in coq
        ),
        "lean concrete truth provider lexical class instance certificate": (
            "structure ConcreteTruthConditionProviderLexicalClassInstanceCertificate : Type where"
            in lean
            and "def concrete_truth_condition_provider_lexical_class_instance_certificate :"
            in lean
            and "theorem concrete_truth_condition_provider_lexical_class_instance_certificate_exists :"
            in lean
            and "theorem concrete_truth_condition_provider_lexical_class_source_matches :"
            in lean
            and "theorem concrete_truth_condition_provider_lexical_class_instances_match :"
            in lean
            and "theorem concrete_truth_condition_provider_lexical_class_provider_truth_projected :"
            in lean
            and "theorem concrete_truth_condition_provider_lexical_class_provider_atomic_projected :"
            in lean
            and "theorem concrete_truth_condition_provider_lexical_class_ledger_truth_projected :"
            in lean
            and "theorem concrete_truth_condition_provider_lexical_class_ledger_atomic_projected :"
            in lean
            and "#check ConcreteTruthConditionProviderLexicalClassInstanceCertificate"
            in lean
            and "#check concrete_truth_condition_provider_lexical_class_ledger_atomic_projected"
            in lean
        ),
        "coq concrete truth provider lexical class instance certificate": (
            "Record ConcreteTruthConditionProviderLexicalClassInstanceCertificate : Type := {"
            in coq
            and "Definition concrete_truth_condition_provider_lexical_class_instance_certificate :"
            in coq
            and "Theorem concrete_truth_condition_provider_lexical_class_instance_certificate_exists :"
            in coq
            and "Theorem concrete_truth_condition_provider_lexical_class_source_matches :"
            in coq
            and "Theorem concrete_truth_condition_provider_lexical_class_instances_match :"
            in coq
            and "Theorem concrete_truth_condition_provider_lexical_class_provider_truth_projected :"
            in coq
            and "Theorem concrete_truth_condition_provider_lexical_class_provider_atomic_projected :"
            in coq
            and "Theorem concrete_truth_condition_provider_lexical_class_ledger_truth_projected :"
            in coq
            and "Theorem concrete_truth_condition_provider_lexical_class_ledger_atomic_projected :"
            in coq
            and "Check ConcreteTruthConditionProviderLexicalClassInstanceCertificate."
            in coq
            and "Check concrete_truth_condition_provider_lexical_class_ledger_atomic_projected."
            in coq
        ),
        "lean concrete truth provider sigma class instance certificate": (
            "structure ConcreteTruthConditionProviderSigmaClassInstanceCertificate : Type where"
            in lean
            and "def concrete_truth_condition_provider_sigma_class_instance_certificate :"
            in lean
            and "theorem concrete_truth_condition_provider_sigma_class_instance_certificate_exists :"
            in lean
            and "theorem concrete_truth_condition_provider_sigma_class_source_matches :"
            in lean
            and "theorem concrete_truth_condition_provider_sigma_class_instances_match :"
            in lean
            and all(
                (
                    f"theorem concrete_truth_condition_provider_sigma_class_provider_{type_name}_truth_projected :"
                    in lean
                    and f"theorem concrete_truth_condition_provider_sigma_class_provider_{type_name}_atomic_projected :"
                    in lean
                    and f"theorem concrete_truth_condition_provider_sigma_class_ledger_{type_name}_truth_projected :"
                    in lean
                    and f"theorem concrete_truth_condition_provider_sigma_class_ledger_{type_name}_atomic_projected :"
                    in lean
                    and f"#check concrete_truth_condition_provider_sigma_class_ledger_{type_name}_atomic_projected"
                    in lean
                )
                for type_name in ("Entity", "Food", "State", "StateScale", "TransitionT")
            )
            and "#check ConcreteTruthConditionProviderSigmaClassInstanceCertificate"
            in lean
        ),
        "coq concrete truth provider sigma class instance certificate": (
            "Record ConcreteTruthConditionProviderSigmaClassInstanceCertificate : Type := {"
            in coq
            and "Definition concrete_truth_condition_provider_sigma_class_instance_certificate :"
            in coq
            and "Theorem concrete_truth_condition_provider_sigma_class_instance_certificate_exists :"
            in coq
            and "Theorem concrete_truth_condition_provider_sigma_class_source_matches :"
            in coq
            and "Theorem concrete_truth_condition_provider_sigma_class_instances_match :"
            in coq
            and all(
                (
                    f"Theorem concrete_truth_condition_provider_sigma_class_provider_{type_name}_truth_projected :"
                    in coq
                    and f"Theorem concrete_truth_condition_provider_sigma_class_provider_{type_name}_atomic_projected :"
                    in coq
                    and f"Theorem concrete_truth_condition_provider_sigma_class_ledger_{type_name}_truth_projected :"
                    in coq
                    and f"Theorem concrete_truth_condition_provider_sigma_class_ledger_{type_name}_atomic_projected :"
                    in coq
                    and f"Check concrete_truth_condition_provider_sigma_class_ledger_{type_name}_atomic_projected."
                    in coq
                )
                for type_name in ("Entity", "Food", "State", "StateScale", "TransitionT")
            )
            and "Check ConcreteTruthConditionProviderSigmaClassInstanceCertificate."
            in coq
        ),
        "lean concrete truth provider temporal class instance certificate": (
            "structure ConcreteTruthConditionProviderTemporalClassInstanceCertificate : Type where"
            in lean
            and "def concrete_truth_condition_provider_temporal_class_instance_certificate :"
            in lean
            and "theorem concrete_truth_condition_provider_temporal_class_instance_certificate_exists :"
            in lean
            and "theorem concrete_truth_condition_provider_temporal_class_source_matches :"
            in lean
            and "theorem concrete_truth_condition_provider_temporal_class_instances_match :"
            in lean
            and all(
                (
                    f"theorem concrete_truth_condition_provider_temporal_class_provider_{name}_truth_projected :"
                    in lean
                    and f"theorem concrete_truth_condition_provider_temporal_class_provider_{name}_atomic_projected :"
                    in lean
                    and f"theorem concrete_truth_condition_provider_temporal_class_ledger_{name}_truth_projected :"
                    in lean
                    and f"theorem concrete_truth_condition_provider_temporal_class_ledger_{name}_atomic_projected :"
                    in lean
                    and f"#check concrete_truth_condition_provider_temporal_class_ledger_{name}_atomic_projected"
                    in lean
                )
                for name in ("at_T", "during_T", "before_T", "after_T", "until_T", "since_T")
            )
            and "#check ConcreteTruthConditionProviderTemporalClassInstanceCertificate"
            in lean
        ),
        "coq concrete truth provider temporal class instance certificate": (
            "Record ConcreteTruthConditionProviderTemporalClassInstanceCertificate : Type := {"
            in coq
            and "Definition concrete_truth_condition_provider_temporal_class_instance_certificate :"
            in coq
            and "Theorem concrete_truth_condition_provider_temporal_class_instance_certificate_exists :"
            in coq
            and "Theorem concrete_truth_condition_provider_temporal_class_source_matches :"
            in coq
            and "Theorem concrete_truth_condition_provider_temporal_class_instances_match :"
            in coq
            and all(
                (
                    f"Theorem concrete_truth_condition_provider_temporal_class_provider_{name}_truth_projected :"
                    in coq
                    and f"Theorem concrete_truth_condition_provider_temporal_class_provider_{name}_atomic_projected :"
                    in coq
                    and f"Theorem concrete_truth_condition_provider_temporal_class_ledger_{name}_truth_projected :"
                    in coq
                    and f"Theorem concrete_truth_condition_provider_temporal_class_ledger_{name}_atomic_projected :"
                    in coq
                    and f"Check concrete_truth_condition_provider_temporal_class_ledger_{name}_atomic_projected."
                    in coq
                )
                for name in ("at_T", "during_T", "before_T", "after_T", "until_T", "since_T")
            )
            and "Check ConcreteTruthConditionProviderTemporalClassInstanceCertificate."
            in coq
        ),
        "lean concrete truth provider repeat class instance certificate": (
            "structure ConcreteTruthConditionProviderRepeatClassInstanceCertificate : Type where"
            in lean
            and "def concrete_truth_condition_provider_repeat_class_instance_certificate :"
            in lean
            and "theorem concrete_truth_condition_provider_repeat_class_instance_certificate_exists :"
            in lean
            and "theorem concrete_truth_condition_provider_repeat_class_source_matches :"
            in lean
            and "theorem concrete_truth_condition_provider_repeat_class_instances_match :"
            in lean
            and "theorem concrete_truth_condition_provider_repeat_class_provider_truth_projected :"
            in lean
            and "theorem concrete_truth_condition_provider_repeat_class_provider_atomic_projected :"
            in lean
            and "theorem concrete_truth_condition_provider_repeat_class_ledger_truth_projected :"
            in lean
            and "theorem concrete_truth_condition_provider_repeat_class_ledger_atomic_projected :"
            in lean
            and "#check ConcreteTruthConditionProviderRepeatClassInstanceCertificate"
            in lean
            and "#check concrete_truth_condition_provider_repeat_class_ledger_atomic_projected"
            in lean
        ),
        "coq concrete truth provider repeat class instance certificate": (
            "Record ConcreteTruthConditionProviderRepeatClassInstanceCertificate : Type := {"
            in coq
            and "Definition concrete_truth_condition_provider_repeat_class_instance_certificate :"
            in coq
            and "Theorem concrete_truth_condition_provider_repeat_class_instance_certificate_exists :"
            in coq
            and "Theorem concrete_truth_condition_provider_repeat_class_source_matches :"
            in coq
            and "Theorem concrete_truth_condition_provider_repeat_class_instances_match :"
            in coq
            and "Theorem concrete_truth_condition_provider_repeat_class_provider_truth_projected :"
            in coq
            and "Theorem concrete_truth_condition_provider_repeat_class_provider_atomic_projected :"
            in coq
            and "Theorem concrete_truth_condition_provider_repeat_class_ledger_truth_projected :"
            in coq
            and "Theorem concrete_truth_condition_provider_repeat_class_ledger_atomic_projected :"
            in coq
            and "Check ConcreteTruthConditionProviderRepeatClassInstanceCertificate."
            in coq
            and "Check concrete_truth_condition_provider_repeat_class_ledger_atomic_projected."
            in coq
        ),
        "lean concrete truth provider polarity class instance certificate": (
            "structure ConcreteTruthConditionProviderPolarityClassInstanceCertificate : Type where"
            in lean
            and "def concrete_truth_condition_provider_polarity_class_instance_certificate :"
            in lean
            and "theorem concrete_truth_condition_provider_polarity_class_instance_certificate_exists :"
            in lean
            and "theorem concrete_truth_condition_provider_polarity_class_source_matches :"
            in lean
            and "theorem concrete_truth_condition_provider_polarity_class_instances_match :"
            in lean
            and "theorem concrete_truth_condition_provider_polarity_class_provider_truth_projected :"
            in lean
            and "theorem concrete_truth_condition_provider_polarity_class_provider_atomic_projected :"
            in lean
            and "theorem concrete_truth_condition_provider_polarity_class_ledger_truth_projected :"
            in lean
            and "theorem concrete_truth_condition_provider_polarity_class_ledger_atomic_projected :"
            in lean
            and "#check ConcreteTruthConditionProviderPolarityClassInstanceCertificate"
            in lean
            and "#check concrete_truth_condition_provider_polarity_class_ledger_atomic_projected"
            in lean
        ),
        "coq concrete truth provider polarity class instance certificate": (
            "Record ConcreteTruthConditionProviderPolarityClassInstanceCertificate : Type := {"
            in coq
            and "Definition concrete_truth_condition_provider_polarity_class_instance_certificate :"
            in coq
            and "Theorem concrete_truth_condition_provider_polarity_class_instance_certificate_exists :"
            in coq
            and "Theorem concrete_truth_condition_provider_polarity_class_source_matches :"
            in coq
            and "Theorem concrete_truth_condition_provider_polarity_class_instances_match :"
            in coq
            and "Theorem concrete_truth_condition_provider_polarity_class_provider_truth_projected :"
            in coq
            and "Theorem concrete_truth_condition_provider_polarity_class_provider_atomic_projected :"
            in coq
            and "Theorem concrete_truth_condition_provider_polarity_class_ledger_truth_projected :"
            in coq
            and "Theorem concrete_truth_condition_provider_polarity_class_ledger_atomic_projected :"
            in coq
            and "Check ConcreteTruthConditionProviderPolarityClassInstanceCertificate."
            in coq
            and "Check concrete_truth_condition_provider_polarity_class_ledger_atomic_projected."
            in coq
        ),
        "lean concrete truth provider transition cause class instance certificate": (
            "structure ConcreteTruthConditionProviderTransitionCauseClassInstanceCertificate : Type where"
            in lean
            and "def concrete_truth_condition_provider_transition_cause_class_instance_certificate :"
            in lean
            and "theorem concrete_truth_condition_provider_transition_cause_class_instance_certificate_exists :"
            in lean
            and "theorem concrete_truth_condition_provider_transition_cause_class_source_matches :"
            in lean
            and "theorem concrete_truth_condition_provider_transition_cause_class_instances_match :"
            in lean
            and "theorem concrete_truth_condition_provider_transition_cause_class_provider_transition_truth_projected :"
            in lean
            and "theorem concrete_truth_condition_provider_transition_cause_class_provider_transition_atomic_projected :"
            in lean
            and "theorem concrete_truth_condition_provider_transition_cause_class_provider_cause_truth_projected :"
            in lean
            and "theorem concrete_truth_condition_provider_transition_cause_class_provider_cause_atomic_projected :"
            in lean
            and "theorem concrete_truth_condition_provider_transition_cause_class_ledger_transition_truth_projected :"
            in lean
            and "theorem concrete_truth_condition_provider_transition_cause_class_ledger_transition_atomic_projected :"
            in lean
            and "theorem concrete_truth_condition_provider_transition_cause_class_ledger_cause_truth_projected :"
            in lean
            and "theorem concrete_truth_condition_provider_transition_cause_class_ledger_cause_atomic_projected :"
            in lean
            and "#check ConcreteTruthConditionProviderTransitionCauseClassInstanceCertificate"
            in lean
            and "#check concrete_truth_condition_provider_transition_cause_class_ledger_cause_atomic_projected"
            in lean
        ),
        "coq concrete truth provider transition cause class instance certificate": (
            "Record ConcreteTruthConditionProviderTransitionCauseClassInstanceCertificate : Type := {"
            in coq
            and "Definition concrete_truth_condition_provider_transition_cause_class_instance_certificate :"
            in coq
            and "Theorem concrete_truth_condition_provider_transition_cause_class_instance_certificate_exists :"
            in coq
            and "Theorem concrete_truth_condition_provider_transition_cause_class_source_matches :"
            in coq
            and "Theorem concrete_truth_condition_provider_transition_cause_class_instances_match :"
            in coq
            and "Theorem concrete_truth_condition_provider_transition_cause_class_provider_transition_truth_projected :"
            in coq
            and "Theorem concrete_truth_condition_provider_transition_cause_class_provider_transition_atomic_projected :"
            in coq
            and "Theorem concrete_truth_condition_provider_transition_cause_class_provider_cause_truth_projected :"
            in coq
            and "Theorem concrete_truth_condition_provider_transition_cause_class_provider_cause_atomic_projected :"
            in coq
            and "Theorem concrete_truth_condition_provider_transition_cause_class_ledger_transition_truth_projected :"
            in coq
            and "Theorem concrete_truth_condition_provider_transition_cause_class_ledger_transition_atomic_projected :"
            in coq
            and "Theorem concrete_truth_condition_provider_transition_cause_class_ledger_cause_truth_projected :"
            in coq
            and "Theorem concrete_truth_condition_provider_transition_cause_class_ledger_cause_atomic_projected :"
            in coq
            and "Check ConcreteTruthConditionProviderTransitionCauseClassInstanceCertificate."
            in coq
            and "Check concrete_truth_condition_provider_transition_cause_class_ledger_cause_atomic_projected."
            in coq
        ),
        "lean concrete truth provider class instance suite certificate": (
            "structure ConcreteTruthConditionProviderClassInstanceSuiteCertificate : Type where"
            in lean
            and "def concrete_truth_condition_provider_class_instance_suite_certificate :"
            in lean
            and "theorem concrete_truth_condition_provider_class_instance_suite_certificate_exists :"
            in lean
            and "theorem concrete_truth_condition_provider_class_instance_suite_source_matches :"
            in lean
            and "theorem concrete_truth_condition_provider_class_instance_suite_independent_suite_matches :"
            in lean
            and "theorem concrete_truth_condition_provider_class_instance_suite_lexical_certificate_matches :"
            in lean
            and "theorem concrete_truth_condition_provider_class_instance_suite_sigma_certificate_matches :"
            in lean
            and "theorem concrete_truth_condition_provider_class_instance_suite_temporal_certificate_matches :"
            in lean
            and "theorem concrete_truth_condition_provider_class_instance_suite_repeat_certificate_matches :"
            in lean
            and "theorem concrete_truth_condition_provider_class_instance_suite_polarity_certificate_matches :"
            in lean
            and "theorem concrete_truth_condition_provider_class_instance_suite_transition_cause_certificate_matches :"
            in lean
            and "theorem concrete_truth_condition_provider_class_instance_suite_independent_spec_sound_projected :"
            in lean
            and "theorem concrete_truth_condition_provider_class_instance_suite_ledger_spec_sound_projected :"
            in lean
            and "#check ConcreteTruthConditionProviderClassInstanceSuiteCertificate"
            in lean
            and "#check concrete_truth_condition_provider_class_instance_suite_ledger_spec_sound_projected"
            in lean
        ),
        "coq concrete truth provider class instance suite certificate": (
            "Record ConcreteTruthConditionProviderClassInstanceSuiteCertificate : Type := {"
            in coq
            and "Definition concrete_truth_condition_provider_class_instance_suite_certificate :"
            in coq
            and "Theorem concrete_truth_condition_provider_class_instance_suite_certificate_exists :"
            in coq
            and "Theorem concrete_truth_condition_provider_class_instance_suite_source_matches :"
            in coq
            and "Theorem concrete_truth_condition_provider_class_instance_suite_independent_suite_matches :"
            in coq
            and "Theorem concrete_truth_condition_provider_class_instance_suite_lexical_certificate_matches :"
            in coq
            and "Theorem concrete_truth_condition_provider_class_instance_suite_sigma_certificate_matches :"
            in coq
            and "Theorem concrete_truth_condition_provider_class_instance_suite_temporal_certificate_matches :"
            in coq
            and "Theorem concrete_truth_condition_provider_class_instance_suite_repeat_certificate_matches :"
            in coq
            and "Theorem concrete_truth_condition_provider_class_instance_suite_polarity_certificate_matches :"
            in coq
            and "Theorem concrete_truth_condition_provider_class_instance_suite_transition_cause_certificate_matches :"
            in coq
            and "Theorem concrete_truth_condition_provider_class_instance_suite_independent_spec_sound_projected :"
            in coq
            and "Theorem concrete_truth_condition_provider_class_instance_suite_ledger_spec_sound_projected :"
            in coq
            and "Check ConcreteTruthConditionProviderClassInstanceSuiteCertificate."
            in coq
            and "Check concrete_truth_condition_provider_class_instance_suite_ledger_spec_sound_projected."
            in coq
        ),
        "lean concrete truth provider class instance suite example package": (
            "structure ConcreteTruthConditionProviderClassInstanceSuiteExamplePackage : Type where"
            in lean
            and "def concrete_truth_condition_provider_class_instance_suite_example_package :"
            in lean
            and "theorem concrete_truth_condition_provider_class_instance_suite_example_package_exists :"
            in lean
            and "theorem concrete_truth_condition_provider_class_instance_suite_example_provider_matches :"
            in lean
            and "theorem concrete_truth_condition_provider_class_instance_suite_example_agreement_matches :"
            in lean
            and "theorem concrete_truth_condition_provider_class_instance_suite_example_independent_sound_projected :"
            in lean
            and "theorem concrete_truth_condition_provider_class_instance_suite_example_ledger_sound_projected :"
            in lean
            and "theorem concrete_truth_condition_provider_class_instance_suite_example_1_direct_atomic_sound :"
            in lean
            and "theorem concrete_truth_condition_provider_class_instance_suite_example_1_evidence_atomic_sound :"
            in lean
            and "theorem concrete_truth_condition_provider_class_instance_suite_example_1_kernel_atomic_sound :"
            in lean
            and "#check ConcreteTruthConditionProviderClassInstanceSuiteExamplePackage"
            in lean
            and "#check concrete_truth_condition_provider_class_instance_suite_example_1_direct_atomic_sound"
            in lean
        ),
        "coq concrete truth provider class instance suite example package": (
            "Record ConcreteTruthConditionProviderClassInstanceSuiteExamplePackage : Type := {"
            in coq
            and "Definition concrete_truth_condition_provider_class_instance_suite_example_package :"
            in coq
            and "Theorem concrete_truth_condition_provider_class_instance_suite_example_package_exists :"
            in coq
            and "Theorem concrete_truth_condition_provider_class_instance_suite_example_provider_matches :"
            in coq
            and "Theorem concrete_truth_condition_provider_class_instance_suite_example_agreement_matches :"
            in coq
            and "Theorem concrete_truth_condition_provider_class_instance_suite_example_independent_sound_projected :"
            in coq
            and "Theorem concrete_truth_condition_provider_class_instance_suite_example_ledger_sound_projected :"
            in coq
            and "Theorem concrete_truth_condition_provider_class_instance_suite_example_1_direct_atomic_sound :"
            in coq
            and "Theorem concrete_truth_condition_provider_class_instance_suite_example_1_evidence_atomic_sound :"
            in coq
            and "Theorem concrete_truth_condition_provider_class_instance_suite_example_1_kernel_atomic_sound :"
            in coq
            and "Check ConcreteTruthConditionProviderClassInstanceSuiteExamplePackage."
            in coq
            and "Check concrete_truth_condition_provider_class_instance_suite_example_1_direct_atomic_sound."
            in coq
        ),
        "lean concrete truth condition instance supply certificate": (
            "structure ConcreteTruthConditionInstanceSupplyCertificate : Type where"
            in lean
            and "def concrete_truth_condition_instance_supply_certificate :"
            in lean
            and "theorem concrete_truth_condition_instance_supply_certificate_exists :"
            in lean
            and "theorem concrete_truth_condition_instance_supply_direct_spec_matches :"
            in lean
            and "theorem concrete_truth_condition_instance_supply_evidence_spec_matches :"
            in lean
            and "theorem concrete_truth_condition_instance_supply_kernel_spec_matches :"
            in lean
            and "theorem concrete_truth_condition_instance_supply_atomic_ledger_matches :"
            in lean
            and "theorem concrete_truth_condition_instance_supply_provider_suite_matches :"
            in lean
            and "theorem concrete_truth_condition_instance_supply_example_package_matches :"
            in lean
            and "theorem concrete_truth_condition_instance_supply_direct_sound_projected :"
            in lean
            and "theorem concrete_truth_condition_instance_supply_evidence_sound_projected :"
            in lean
            and "theorem concrete_truth_condition_instance_supply_kernel_sound_projected :"
            in lean
            and "theorem concrete_truth_condition_instance_supply_example_1_direct_truth_projected :"
            in lean
            and "theorem concrete_truth_condition_instance_supply_example_1_evidence_truth_projected :"
            in lean
            and "theorem concrete_truth_condition_instance_supply_example_1_kernel_truth_projected :"
            in lean
            and "#check ConcreteTruthConditionInstanceSupplyCertificate"
            in lean
            and "#check concrete_truth_condition_instance_supply_example_1_direct_truth_projected"
            in lean
        ),
        "coq concrete truth condition instance supply certificate": (
            "Record ConcreteTruthConditionInstanceSupplyCertificate : Type := {"
            in coq
            and "Definition concrete_truth_condition_instance_supply_certificate :"
            in coq
            and "Theorem concrete_truth_condition_instance_supply_certificate_exists :"
            in coq
            and "Theorem concrete_truth_condition_instance_supply_direct_spec_matches :"
            in coq
            and "Theorem concrete_truth_condition_instance_supply_evidence_spec_matches :"
            in coq
            and "Theorem concrete_truth_condition_instance_supply_kernel_spec_matches :"
            in coq
            and "Theorem concrete_truth_condition_instance_supply_atomic_ledger_matches :"
            in coq
            and "Theorem concrete_truth_condition_instance_supply_provider_suite_matches :"
            in coq
            and "Theorem concrete_truth_condition_instance_supply_example_package_matches :"
            in coq
            and "Theorem concrete_truth_condition_instance_supply_direct_sound_projected :"
            in coq
            and "Theorem concrete_truth_condition_instance_supply_evidence_sound_projected :"
            in coq
            and "Theorem concrete_truth_condition_instance_supply_kernel_sound_projected :"
            in coq
            and "Theorem concrete_truth_condition_instance_supply_atom_sound_projected :"
            in coq
            and "Theorem concrete_truth_condition_instance_supply_example_1_direct_truth_projected :"
            in coq
            and "Theorem concrete_truth_condition_instance_supply_example_1_evidence_truth_projected :"
            in coq
            and "Theorem concrete_truth_condition_instance_supply_example_1_kernel_truth_projected :"
            in coq
            and "Check ConcreteTruthConditionInstanceSupplyCertificate."
            in coq
            and "Check concrete_truth_condition_instance_supply_example_1_direct_truth_projected."
            in coq
        ),
        "lean concrete truth condition independent model candidate certificate": (
            "structure ConcreteTruthConditionIndependentModelCandidateCertificate :"
            in lean
            and "def concrete_truth_condition_independent_model_candidate_certificate :"
            in lean
            and "theorem concrete_truth_condition_independent_model_candidate_certificate_exists :"
            in lean
            and "theorem concrete_truth_condition_independent_model_candidate_direct_spec_model_matches :"
            in lean
            and "theorem concrete_truth_condition_independent_model_candidate_evidence_spec_model_matches :"
            in lean
            and "theorem concrete_truth_condition_independent_model_candidate_kernel_spec_route_matches :"
            in lean
            and "theorem concrete_truth_condition_independent_model_candidate_direct_model_to_spec_projected :"
            in lean
            and "theorem concrete_truth_condition_independent_model_candidate_kernel_supply_sound_projected :"
            in lean
            and "theorem concrete_truth_condition_independent_model_candidate_example_1_direct_model_truth_projected :"
            in lean
            and "theorem concrete_truth_condition_independent_model_candidate_example_1_kernel_atomic_projected :"
            in lean
            and "#check ConcreteTruthConditionIndependentModelCandidateCertificate"
            in lean
            and "#check concrete_truth_condition_independent_model_candidate_example_1_direct_model_truth_projected"
            in lean
        ),
        "coq concrete truth condition independent model candidate certificate": (
            "Record ConcreteTruthConditionIndependentModelCandidateCertificate : Type := {"
            in coq
            and "Definition concrete_truth_condition_independent_model_candidate_certificate :"
            in coq
            and "Theorem concrete_truth_condition_independent_model_candidate_certificate_exists :"
            in coq
            and "Theorem concrete_truth_condition_independent_model_candidate_direct_spec_model_matches :"
            in coq
            and "Theorem concrete_truth_condition_independent_model_candidate_evidence_spec_model_matches :"
            in coq
            and "Theorem concrete_truth_condition_independent_model_candidate_kernel_spec_route_matches :"
            in coq
            and "Theorem concrete_truth_condition_independent_model_candidate_direct_model_to_spec_projected :"
            in coq
            and "Theorem concrete_truth_condition_independent_model_candidate_kernel_supply_sound_projected :"
            in coq
            and "Theorem concrete_truth_condition_independent_model_candidate_example_1_direct_model_truth_projected :"
            in coq
            and "Theorem concrete_truth_condition_independent_model_candidate_example_1_kernel_atomic_projected :"
            in coq
            and "Check ConcreteTruthConditionIndependentModelCandidateCertificate."
            in coq
            and "Check concrete_truth_condition_independent_model_candidate_example_1_direct_model_truth_projected."
            in coq
        ),
        "lean concrete truth condition independent model readiness certificate": (
            "structure ConcreteTruthConditionIndependentModelReadinessCertificate :"
            in lean
            and "def concrete_truth_condition_independent_model_readiness_certificate :"
            in lean
            and "theorem concrete_truth_condition_independent_model_readiness_certificate_exists :"
            in lean
            and "theorem concrete_truth_condition_independent_model_readiness_candidate_matches :"
            in lean
            and "theorem concrete_truth_condition_independent_model_readiness_coverage_matches :"
            in lean
            and "theorem concrete_truth_condition_independent_model_readiness_ledger_matches :"
            in lean
            and "theorem concrete_truth_condition_independent_model_readiness_provider_obligation_matches :"
            in lean
            and "theorem concrete_truth_condition_independent_model_readiness_supply_matches :"
            in lean
            and "theorem concrete_truth_condition_independent_model_readiness_direct_sound_projected :"
            in lean
            and "theorem concrete_truth_condition_independent_model_readiness_constructor_sound_projected :"
            in lean
            and "theorem concrete_truth_condition_independent_model_readiness_example_1_direct_atomic_projected :"
            in lean
            and "#check ConcreteTruthConditionIndependentModelReadinessCertificate"
            in lean
            and "#check concrete_truth_condition_independent_model_readiness_example_1_direct_atomic_projected"
            in lean
        ),
        "coq concrete truth condition independent model readiness certificate": (
            "Record ConcreteTruthConditionIndependentModelReadinessCertificate : Type := {"
            in coq
            and "Definition concrete_truth_condition_independent_model_readiness_certificate :"
            in coq
            and "Theorem concrete_truth_condition_independent_model_readiness_certificate_exists :"
            in coq
            and "Theorem concrete_truth_condition_independent_model_readiness_candidate_matches :"
            in coq
            and "Theorem concrete_truth_condition_independent_model_readiness_coverage_matches :"
            in coq
            and "Theorem concrete_truth_condition_independent_model_readiness_ledger_matches :"
            in coq
            and "Theorem concrete_truth_condition_independent_model_readiness_provider_obligation_matches :"
            in coq
            and "Theorem concrete_truth_condition_independent_model_readiness_supply_matches :"
            in coq
            and "Theorem concrete_truth_condition_independent_model_readiness_direct_sound_projected :"
            in coq
            and "Theorem concrete_truth_condition_independent_model_readiness_constructor_sound_projected :"
            in coq
            and "Theorem concrete_truth_condition_independent_model_readiness_example_1_direct_atomic_projected :"
            in coq
            and "Check ConcreteTruthConditionIndependentModelReadinessCertificate."
            in coq
            and "Check concrete_truth_condition_independent_model_readiness_example_1_direct_atomic_projected."
            in coq
        ),
        "lean concrete truth condition independent model class readiness certificate": (
            "structure ConcreteTruthConditionIndependentModelClassReadinessCertificate :"
            in lean
            and "def concrete_truth_condition_independent_model_class_readiness_certificate :"
            in lean
            and "theorem concrete_truth_condition_independent_model_class_readiness_certificate_exists :"
            in lean
            and "theorem concrete_truth_condition_independent_model_class_readiness_source_matches :"
            in lean
            and "theorem concrete_truth_condition_independent_model_class_readiness_provider_suite_matches :"
            in lean
            and "theorem concrete_truth_condition_independent_model_class_readiness_provider_obligation_matches_readiness :"
            in lean
            and "theorem concrete_truth_condition_independent_model_class_readiness_lexical_certificate_matches :"
            in lean
            and "theorem concrete_truth_condition_independent_model_class_readiness_transition_cause_certificate_matches :"
            in lean
            and "theorem concrete_truth_condition_independent_model_class_readiness_independent_sound_projected :"
            in lean
            and "theorem concrete_truth_condition_independent_model_class_readiness_constructor_sound_projected :"
            in lean
            and "#check ConcreteTruthConditionIndependentModelClassReadinessCertificate"
            in lean
            and "#check concrete_truth_condition_independent_model_class_readiness_constructor_sound_projected"
            in lean
        ),
        "coq concrete truth condition independent model class readiness certificate": (
            "Record ConcreteTruthConditionIndependentModelClassReadinessCertificate : Type := {"
            in coq
            and "Definition concrete_truth_condition_independent_model_class_readiness_certificate :"
            in coq
            and "Theorem concrete_truth_condition_independent_model_class_readiness_certificate_exists :"
            in coq
            and "Theorem concrete_truth_condition_independent_model_class_readiness_source_matches :"
            in coq
            and "Theorem concrete_truth_condition_independent_model_class_readiness_provider_suite_matches :"
            in coq
            and "Theorem concrete_truth_condition_independent_model_class_readiness_provider_obligation_matches_readiness :"
            in coq
            and "Theorem concrete_truth_condition_independent_model_class_readiness_lexical_certificate_matches :"
            in coq
            and "Theorem concrete_truth_condition_independent_model_class_readiness_transition_cause_certificate_matches :"
            in coq
            and "Theorem concrete_truth_condition_independent_model_class_readiness_independent_sound_projected :"
            in coq
            and "Theorem concrete_truth_condition_independent_model_class_readiness_constructor_sound_projected :"
            in coq
            and "Check ConcreteTruthConditionIndependentModelClassReadinessCertificate."
            in coq
            and "Check concrete_truth_condition_independent_model_class_readiness_constructor_sound_projected."
            in coq
        ),
        "lean concrete truth condition independent lexical model candidate certificate": (
            "structure ConcreteTruthConditionIndependentLexicalModelCandidateCertificate :"
            in lean
            and "def concrete_truth_condition_independent_lexical_model_candidate_certificate :"
            in lean
            and "theorem concrete_truth_condition_independent_lexical_model_candidate_certificate_exists :"
            in lean
            and "theorem concrete_truth_condition_independent_lexical_model_candidate_class_certificate_matches :"
            in lean
            and "theorem concrete_truth_condition_independent_lexical_model_candidate_registered_model_matches :"
            in lean
            and "theorem concrete_truth_condition_independent_lexical_model_candidate_independent_sound_projected :"
            in lean
            and "theorem concrete_truth_condition_independent_lexical_model_candidate_lexical_1_provider_truth_projected :"
            in lean
            and "theorem concrete_truth_condition_independent_lexical_model_candidate_lexical_1_model_atomic_projected :"
            in lean
            and "#check ConcreteTruthConditionIndependentLexicalModelCandidateCertificate"
            in lean
            and "#check concrete_truth_condition_independent_lexical_model_candidate_lexical_1_model_atomic_projected"
            in lean
        ),
        "coq concrete truth condition independent lexical model candidate certificate": (
            "Record ConcreteTruthConditionIndependentLexicalModelCandidateCertificate : Type := {"
            in coq
            and "Definition concrete_truth_condition_independent_lexical_model_candidate_certificate :"
            in coq
            and "Theorem concrete_truth_condition_independent_lexical_model_candidate_certificate_exists :"
            in coq
            and "Theorem concrete_truth_condition_independent_lexical_model_candidate_class_certificate_matches :"
            in coq
            and "Theorem concrete_truth_condition_independent_lexical_model_candidate_registered_model_matches :"
            in coq
            and "Theorem concrete_truth_condition_independent_lexical_model_candidate_independent_sound_projected :"
            in coq
            and "Theorem concrete_truth_condition_independent_lexical_model_candidate_lexical_1_provider_truth_projected :"
            in coq
            and "Theorem concrete_truth_condition_independent_lexical_model_candidate_lexical_1_model_atomic_projected :"
            in coq
            and "Check ConcreteTruthConditionIndependentLexicalModelCandidateCertificate."
            in coq
            and "Check concrete_truth_condition_independent_lexical_model_candidate_lexical_1_model_atomic_projected."
            in coq
        ),
        "lean concrete truth condition independent sigma model candidate certificate": (
            "structure ConcreteTruthConditionIndependentSigmaModelCandidateCertificate :"
            in lean
            and "def concrete_truth_condition_independent_sigma_model_candidate_certificate :"
            in lean
            and "theorem concrete_truth_condition_independent_sigma_model_candidate_certificate_exists :"
            in lean
            and "theorem concrete_truth_condition_independent_sigma_model_candidate_class_certificate_matches :"
            in lean
            and "theorem concrete_truth_condition_independent_sigma_model_candidate_instances_matches :"
            in lean
            and "theorem concrete_truth_condition_independent_sigma_model_candidate_compositional_model_matches :"
            in lean
            and "theorem concrete_truth_condition_independent_sigma_model_candidate_model_sound_projected :"
            in lean
            and "theorem concrete_truth_condition_independent_sigma_model_candidate_sigma_Entity_provider_truth_projected :"
            in lean
            and "theorem concrete_truth_condition_independent_sigma_model_candidate_sigma_Entity_model_atomic_projected :"
            in lean
            and "#check ConcreteTruthConditionIndependentSigmaModelCandidateCertificate"
            in lean
            and "#check concrete_truth_condition_independent_sigma_model_candidate_sigma_Entity_model_atomic_projected"
            in lean
        ),
        "coq concrete truth condition independent sigma model candidate certificate": (
            "Record ConcreteTruthConditionIndependentSigmaModelCandidateCertificate : Type := {"
            in coq
            and "Definition concrete_truth_condition_independent_sigma_model_candidate_certificate :"
            in coq
            and "Theorem concrete_truth_condition_independent_sigma_model_candidate_certificate_exists :"
            in coq
            and "Theorem concrete_truth_condition_independent_sigma_model_candidate_class_certificate_matches :"
            in coq
            and "Theorem concrete_truth_condition_independent_sigma_model_candidate_instances_matches :"
            in coq
            and "Theorem concrete_truth_condition_independent_sigma_model_candidate_compositional_model_matches :"
            in coq
            and "Theorem concrete_truth_condition_independent_sigma_model_candidate_model_sound_projected :"
            in coq
            and "Theorem concrete_truth_condition_independent_sigma_model_candidate_sigma_Entity_provider_truth_projected :"
            in coq
            and "Theorem concrete_truth_condition_independent_sigma_model_candidate_sigma_Entity_model_atomic_projected :"
            in coq
            and "Check ConcreteTruthConditionIndependentSigmaModelCandidateCertificate."
            in coq
            and "Check concrete_truth_condition_independent_sigma_model_candidate_sigma_Entity_model_atomic_projected."
            in coq
        ),
        "lean concrete truth condition independent temporal model candidate certificate": (
            "structure ConcreteTruthConditionIndependentTemporalModelCandidateCertificate :"
            in lean
            and "def concrete_truth_condition_independent_temporal_model_candidate_certificate :"
            in lean
            and "theorem concrete_truth_condition_independent_temporal_model_candidate_certificate_exists :"
            in lean
            and "theorem concrete_truth_condition_independent_temporal_model_candidate_class_certificate_matches :"
            in lean
            and "theorem concrete_truth_condition_independent_temporal_model_candidate_instances_matches :"
            in lean
            and "theorem concrete_truth_condition_independent_temporal_model_candidate_compositional_model_matches :"
            in lean
            and "theorem concrete_truth_condition_independent_temporal_model_candidate_model_sound_projected :"
            in lean
            and "theorem concrete_truth_condition_independent_temporal_model_candidate_at_T_provider_truth_projected :"
            in lean
            and "theorem concrete_truth_condition_independent_temporal_model_candidate_at_T_model_atomic_projected :"
            in lean
            and "#check ConcreteTruthConditionIndependentTemporalModelCandidateCertificate"
            in lean
            and "#check concrete_truth_condition_independent_temporal_model_candidate_at_T_model_atomic_projected"
            in lean
        ),
        "coq concrete truth condition independent temporal model candidate certificate": (
            "Record ConcreteTruthConditionIndependentTemporalModelCandidateCertificate : Type := {"
            in coq
            and "Definition concrete_truth_condition_independent_temporal_model_candidate_certificate :"
            in coq
            and "Theorem concrete_truth_condition_independent_temporal_model_candidate_certificate_exists :"
            in coq
            and "Theorem concrete_truth_condition_independent_temporal_model_candidate_class_certificate_matches :"
            in coq
            and "Theorem concrete_truth_condition_independent_temporal_model_candidate_instances_matches :"
            in coq
            and "Theorem concrete_truth_condition_independent_temporal_model_candidate_compositional_model_matches :"
            in coq
            and "Theorem concrete_truth_condition_independent_temporal_model_candidate_model_sound_projected :"
            in coq
            and "Theorem concrete_truth_condition_independent_temporal_model_candidate_at_T_provider_truth_projected :"
            in coq
            and "Theorem concrete_truth_condition_independent_temporal_model_candidate_at_T_model_atomic_projected :"
            in coq
            and "Check ConcreteTruthConditionIndependentTemporalModelCandidateCertificate."
            in coq
            and "Check concrete_truth_condition_independent_temporal_model_candidate_at_T_model_atomic_projected."
            in coq
        ),
        "lean concrete truth condition independent repeat model candidate certificate": (
            "structure ConcreteTruthConditionIndependentRepeatModelCandidateCertificate :"
            in lean
            and "def concrete_truth_condition_independent_repeat_model_candidate_certificate :"
            in lean
            and "theorem concrete_truth_condition_independent_repeat_model_candidate_certificate_exists :"
            in lean
            and "theorem concrete_truth_condition_independent_repeat_model_candidate_class_certificate_matches :"
            in lean
            and "theorem concrete_truth_condition_independent_repeat_model_candidate_instances_matches :"
            in lean
            and "theorem concrete_truth_condition_independent_repeat_model_candidate_compositional_model_matches :"
            in lean
            and "theorem concrete_truth_condition_independent_repeat_model_candidate_model_sound_projected :"
            in lean
            and "theorem concrete_truth_condition_independent_repeat_model_candidate_repeat_provider_truth_projected :"
            in lean
            and "theorem concrete_truth_condition_independent_repeat_model_candidate_repeat_model_atomic_projected :"
            in lean
            and "#check ConcreteTruthConditionIndependentRepeatModelCandidateCertificate"
            in lean
            and "#check concrete_truth_condition_independent_repeat_model_candidate_repeat_model_atomic_projected"
            in lean
        ),
        "coq concrete truth condition independent repeat model candidate certificate": (
            "Record ConcreteTruthConditionIndependentRepeatModelCandidateCertificate : Type := {"
            in coq
            and "Definition concrete_truth_condition_independent_repeat_model_candidate_certificate :"
            in coq
            and "Theorem concrete_truth_condition_independent_repeat_model_candidate_certificate_exists :"
            in coq
            and "Theorem concrete_truth_condition_independent_repeat_model_candidate_class_certificate_matches :"
            in coq
            and "Theorem concrete_truth_condition_independent_repeat_model_candidate_instances_matches :"
            in coq
            and "Theorem concrete_truth_condition_independent_repeat_model_candidate_compositional_model_matches :"
            in coq
            and "Theorem concrete_truth_condition_independent_repeat_model_candidate_model_sound_projected :"
            in coq
            and "Theorem concrete_truth_condition_independent_repeat_model_candidate_repeat_provider_truth_projected :"
            in coq
            and "Theorem concrete_truth_condition_independent_repeat_model_candidate_repeat_model_atomic_projected :"
            in coq
            and "Check ConcreteTruthConditionIndependentRepeatModelCandidateCertificate."
            in coq
            and "Check concrete_truth_condition_independent_repeat_model_candidate_repeat_model_atomic_projected."
            in coq
        ),
        "lean concrete truth condition independent polarity model candidate certificate": (
            "structure ConcreteTruthConditionIndependentPolarityModelCandidateCertificate :"
            in lean
            and "def concrete_truth_condition_independent_polarity_model_candidate_certificate :"
            in lean
            and "theorem concrete_truth_condition_independent_polarity_model_candidate_certificate_exists :"
            in lean
            and "theorem concrete_truth_condition_independent_polarity_model_candidate_class_certificate_matches :"
            in lean
            and "theorem concrete_truth_condition_independent_polarity_model_candidate_instances_matches :"
            in lean
            and "theorem concrete_truth_condition_independent_polarity_model_candidate_compositional_model_matches :"
            in lean
            and "theorem concrete_truth_condition_independent_polarity_model_candidate_model_sound_projected :"
            in lean
            and "theorem concrete_truth_condition_independent_polarity_model_candidate_not_T_provider_truth_projected :"
            in lean
            and "theorem concrete_truth_condition_independent_polarity_model_candidate_not_T_model_atomic_projected :"
            in lean
            and "#check ConcreteTruthConditionIndependentPolarityModelCandidateCertificate"
            in lean
            and "#check concrete_truth_condition_independent_polarity_model_candidate_not_T_model_atomic_projected"
            in lean
        ),
        "coq concrete truth condition independent polarity model candidate certificate": (
            "Record ConcreteTruthConditionIndependentPolarityModelCandidateCertificate : Type := {"
            in coq
            and "Definition concrete_truth_condition_independent_polarity_model_candidate_certificate :"
            in coq
            and "Theorem concrete_truth_condition_independent_polarity_model_candidate_certificate_exists :"
            in coq
            and "Theorem concrete_truth_condition_independent_polarity_model_candidate_class_certificate_matches :"
            in coq
            and "Theorem concrete_truth_condition_independent_polarity_model_candidate_instances_matches :"
            in coq
            and "Theorem concrete_truth_condition_independent_polarity_model_candidate_compositional_model_matches :"
            in coq
            and "Theorem concrete_truth_condition_independent_polarity_model_candidate_model_sound_projected :"
            in coq
            and "Theorem concrete_truth_condition_independent_polarity_model_candidate_not_T_provider_truth_projected :"
            in coq
            and "Theorem concrete_truth_condition_independent_polarity_model_candidate_not_T_model_atomic_projected :"
            in coq
            and "Check ConcreteTruthConditionIndependentPolarityModelCandidateCertificate."
            in coq
            and "Check concrete_truth_condition_independent_polarity_model_candidate_not_T_model_atomic_projected."
            in coq
        ),
        "lean concrete truth condition independent transition cause model candidate certificate": (
            "structure ConcreteTruthConditionIndependentTransitionCauseModelCandidateCertificate :"
            in lean
            and "def concrete_truth_condition_independent_transition_cause_model_candidate_certificate :"
            in lean
            and "theorem concrete_truth_condition_independent_transition_cause_model_candidate_certificate_exists :"
            in lean
            and "theorem concrete_truth_condition_independent_transition_cause_model_candidate_class_certificate_matches :"
            in lean
            and "theorem concrete_truth_condition_independent_transition_cause_model_candidate_instances_matches :"
            in lean
            and "theorem concrete_truth_condition_independent_transition_cause_model_candidate_compositional_model_matches :"
            in lean
            and "theorem concrete_truth_condition_independent_transition_cause_model_candidate_model_sound_projected :"
            in lean
            and "theorem concrete_truth_condition_independent_transition_cause_model_candidate_transition_provider_truth_projected :"
            in lean
            and "theorem concrete_truth_condition_independent_transition_cause_model_candidate_transition_model_atomic_projected :"
            in lean
            and "theorem concrete_truth_condition_independent_transition_cause_model_candidate_cause_provider_truth_projected :"
            in lean
            and "theorem concrete_truth_condition_independent_transition_cause_model_candidate_cause_model_atomic_projected :"
            in lean
            and "#check ConcreteTruthConditionIndependentTransitionCauseModelCandidateCertificate"
            in lean
            and "#check concrete_truth_condition_independent_transition_cause_model_candidate_cause_model_atomic_projected"
            in lean
        ),
        "coq concrete truth condition independent transition cause model candidate certificate": (
            "Record ConcreteTruthConditionIndependentTransitionCauseModelCandidateCertificate : Type := {"
            in coq
            and "Definition concrete_truth_condition_independent_transition_cause_model_candidate_certificate :"
            in coq
            and "Theorem concrete_truth_condition_independent_transition_cause_model_candidate_certificate_exists :"
            in coq
            and "Theorem concrete_truth_condition_independent_transition_cause_model_candidate_class_certificate_matches :"
            in coq
            and "Theorem concrete_truth_condition_independent_transition_cause_model_candidate_instances_matches :"
            in coq
            and "Theorem concrete_truth_condition_independent_transition_cause_model_candidate_compositional_model_matches :"
            in coq
            and "Theorem concrete_truth_condition_independent_transition_cause_model_candidate_model_sound_projected :"
            in coq
            and "Theorem concrete_truth_condition_independent_transition_cause_model_candidate_transition_provider_truth_projected :"
            in coq
            and "Theorem concrete_truth_condition_independent_transition_cause_model_candidate_transition_model_atomic_projected :"
            in coq
            and "Theorem concrete_truth_condition_independent_transition_cause_model_candidate_cause_provider_truth_projected :"
            in coq
            and "Theorem concrete_truth_condition_independent_transition_cause_model_candidate_cause_model_atomic_projected :"
            in coq
            and "Check ConcreteTruthConditionIndependentTransitionCauseModelCandidateCertificate."
            in coq
            and "Check concrete_truth_condition_independent_transition_cause_model_candidate_cause_model_atomic_projected."
            in coq
        ),
        "lean concrete truth condition independent model candidate class suite certificate": (
            "structure ConcreteTruthConditionIndependentModelCandidateClassSuiteCertificate :"
            in lean
            and "def concrete_truth_condition_independent_model_candidate_class_suite_certificate :"
            in lean
            and "theorem concrete_truth_condition_independent_model_candidate_class_suite_certificate_exists :"
            in lean
            and "theorem concrete_truth_condition_independent_model_candidate_class_suite_lexical_candidate_matches :"
            in lean
            and "theorem concrete_truth_condition_independent_model_candidate_class_suite_transition_cause_candidate_matches :"
            in lean
            and "theorem concrete_truth_condition_independent_model_candidate_class_suite_independent_sound_projected :"
            in lean
            and "theorem concrete_truth_condition_independent_model_candidate_class_suite_model_sound_projected :"
            in lean
            and "theorem concrete_truth_condition_independent_model_candidate_class_suite_sigma_Entity_model_atomic_projected :"
            in lean
            and "theorem concrete_truth_condition_independent_model_candidate_class_suite_cause_model_atomic_projected :"
            in lean
            and "#check ConcreteTruthConditionIndependentModelCandidateClassSuiteCertificate"
            in lean
            and "#check concrete_truth_condition_independent_model_candidate_class_suite_cause_model_atomic_projected"
            in lean
        ),
        "coq concrete truth condition independent model candidate class suite certificate": (
            "Record ConcreteTruthConditionIndependentModelCandidateClassSuiteCertificate : Type := {"
            in coq
            and "Definition concrete_truth_condition_independent_model_candidate_class_suite_certificate :"
            in coq
            and "Theorem concrete_truth_condition_independent_model_candidate_class_suite_certificate_exists :"
            in coq
            and "Theorem concrete_truth_condition_independent_model_candidate_class_suite_lexical_candidate_matches :"
            in coq
            and "Theorem concrete_truth_condition_independent_model_candidate_class_suite_transition_cause_candidate_matches :"
            in coq
            and "Theorem concrete_truth_condition_independent_model_candidate_class_suite_independent_sound_projected :"
            in coq
            and "Theorem concrete_truth_condition_independent_model_candidate_class_suite_model_sound_projected :"
            in coq
            and "Theorem concrete_truth_condition_independent_model_candidate_class_suite_sigma_Entity_model_atomic_projected :"
            in coq
            and "Theorem concrete_truth_condition_independent_model_candidate_class_suite_cause_model_atomic_projected :"
            in coq
            and "Check ConcreteTruthConditionIndependentModelCandidateClassSuiteCertificate."
            in coq
            and "Check concrete_truth_condition_independent_model_candidate_class_suite_cause_model_atomic_projected."
            in coq
        ),
        "lean concrete truth condition independent model candidate class suite example package": (
            "structure ConcreteTruthConditionIndependentModelCandidateClassSuiteExamplePackage :"
            in lean
            and "def concrete_truth_condition_independent_model_candidate_class_suite_example_package :"
            in lean
            and "theorem concrete_truth_condition_independent_model_candidate_class_suite_example_package_exists :"
            in lean
            and "theorem concrete_truth_condition_independent_model_candidate_class_suite_example_suite_matches :"
            in lean
            and "theorem concrete_truth_condition_independent_model_candidate_class_suite_example_candidate_matches :"
            in lean
            and "theorem concrete_truth_condition_independent_model_candidate_class_suite_example_model_sound_projected :"
            in lean
            and "theorem concrete_truth_condition_independent_model_candidate_class_suite_example_1_direct_atomic_sound :"
            in lean
            and "theorem concrete_truth_condition_independent_model_candidate_class_suite_example_1_kernel_atomic_sound :"
            in lean
            and "#check ConcreteTruthConditionIndependentModelCandidateClassSuiteExamplePackage"
            in lean
            and "#check concrete_truth_condition_independent_model_candidate_class_suite_example_1_kernel_atomic_sound"
            in lean
        ),
        "coq concrete truth condition independent model candidate class suite example package": (
            "Record ConcreteTruthConditionIndependentModelCandidateClassSuiteExamplePackage : Type := {"
            in coq
            and "Definition concrete_truth_condition_independent_model_candidate_class_suite_example_package :"
            in coq
            and "Theorem concrete_truth_condition_independent_model_candidate_class_suite_example_package_exists :"
            in coq
            and "Theorem concrete_truth_condition_independent_model_candidate_class_suite_example_suite_matches :"
            in coq
            and "Theorem concrete_truth_condition_independent_model_candidate_class_suite_example_candidate_matches :"
            in coq
            and "Theorem concrete_truth_condition_independent_model_candidate_class_suite_example_model_sound_projected :"
            in coq
            and "Theorem concrete_truth_condition_independent_model_candidate_class_suite_example_1_direct_atomic_sound :"
            in coq
            and "Theorem concrete_truth_condition_independent_model_candidate_class_suite_example_1_kernel_atomic_sound :"
            in coq
            and "Check ConcreteTruthConditionIndependentModelCandidateClassSuiteExamplePackage."
            in coq
            and "Check concrete_truth_condition_independent_model_candidate_class_suite_example_1_kernel_atomic_sound."
            in coq
        ),
        "lean concrete truth condition registered fragment instance completion certificate": (
            "structure ConcreteTruthConditionRegisteredFragmentInstanceCompletionCertificate :"
            in lean
            and "def concrete_truth_condition_registered_fragment_instance_completion_certificate :"
            in lean
            and "theorem concrete_truth_condition_registered_fragment_instance_completion_certificate_exists :"
            in lean
            and "theorem concrete_truth_condition_registered_fragment_instance_completion_supply_matches :"
            in lean
            and "theorem concrete_truth_condition_registered_fragment_instance_completion_provider_suite_matches :"
            in lean
            and "theorem concrete_truth_condition_registered_fragment_instance_completion_model_suite_matches :"
            in lean
            and "theorem concrete_truth_condition_registered_fragment_instance_completion_direct_sound_projected :"
            in lean
            and "theorem concrete_truth_condition_registered_fragment_instance_completion_model_sound_projected :"
            in lean
            and "theorem concrete_truth_condition_registered_fragment_instance_completion_example_1_direct_atomic_sound :"
            in lean
            and "theorem concrete_truth_condition_registered_fragment_instance_completion_example_1_kernel_atomic_sound :"
            in lean
            and "#check ConcreteTruthConditionRegisteredFragmentInstanceCompletionCertificate"
            in lean
            and "#check concrete_truth_condition_registered_fragment_instance_completion_example_1_kernel_atomic_sound"
            in lean
        ),
        "coq concrete truth condition registered fragment instance completion certificate": (
            "Record ConcreteTruthConditionRegisteredFragmentInstanceCompletionCertificate : Type := {"
            in coq
            and "Definition concrete_truth_condition_registered_fragment_instance_completion_certificate :"
            in coq
            and "Theorem concrete_truth_condition_registered_fragment_instance_completion_certificate_exists :"
            in coq
            and "Theorem concrete_truth_condition_registered_fragment_instance_completion_supply_matches :"
            in coq
            and "Theorem concrete_truth_condition_registered_fragment_instance_completion_provider_suite_matches :"
            in coq
            and "Theorem concrete_truth_condition_registered_fragment_instance_completion_model_suite_matches :"
            in coq
            and "Theorem concrete_truth_condition_registered_fragment_instance_completion_direct_sound_projected :"
            in coq
            and "Theorem concrete_truth_condition_registered_fragment_instance_completion_model_sound_projected :"
            in coq
            and "Theorem concrete_truth_condition_registered_fragment_instance_completion_example_1_direct_atomic_sound :"
            in coq
            and "Theorem concrete_truth_condition_registered_fragment_instance_completion_example_1_kernel_atomic_sound :"
            in coq
            and "Check ConcreteTruthConditionRegisteredFragmentInstanceCompletionCertificate."
            in coq
            and "Check concrete_truth_condition_registered_fragment_instance_completion_example_1_kernel_atomic_sound."
            in coq
        ),
        "lean concrete truth condition instance source audit certificate": (
            "structure ConcreteTruthConditionInstanceSourceAuditCertificate :"
            in lean
            and "def concrete_truth_condition_instance_source_audit_certificate :"
            in lean
            and "theorem concrete_truth_condition_instance_source_audit_certificate_exists :"
            in lean
            and "theorem concrete_truth_condition_instance_source_audit_completion_matches :"
            in lean
            and "theorem concrete_truth_condition_instance_source_audit_atomic_ledger_matches :"
            in lean
            and "theorem concrete_truth_condition_instance_source_audit_direct_spec_matches :"
            in lean
            and "theorem concrete_truth_condition_instance_source_audit_constructor_spec_matches :"
            in lean
            and "theorem concrete_truth_condition_instance_source_audit_direct_sound_projected :"
            in lean
            and "theorem concrete_truth_condition_instance_source_audit_model_sound_projected :"
            in lean
            and "theorem concrete_truth_condition_instance_source_audit_example_1_direct_atomic_sound :"
            in lean
            and "theorem concrete_truth_condition_instance_source_audit_example_1_kernel_atomic_sound :"
            in lean
            and "#check ConcreteTruthConditionInstanceSourceAuditCertificate"
            in lean
            and "#check concrete_truth_condition_instance_source_audit_example_1_kernel_atomic_sound"
            in lean
        ),
        "coq concrete truth condition instance source audit certificate": (
            "Record ConcreteTruthConditionInstanceSourceAuditCertificate : Type := {"
            in coq
            and "Definition concrete_truth_condition_instance_source_audit_certificate :"
            in coq
            and "Theorem concrete_truth_condition_instance_source_audit_certificate_exists :"
            in coq
            and "Theorem concrete_truth_condition_instance_source_audit_completion_matches :"
            in coq
            and "Theorem concrete_truth_condition_instance_source_audit_atomic_ledger_matches :"
            in coq
            and "Theorem concrete_truth_condition_instance_source_audit_direct_spec_matches :"
            in coq
            and "Theorem concrete_truth_condition_instance_source_audit_constructor_spec_matches :"
            in coq
            and "Theorem concrete_truth_condition_instance_source_audit_direct_sound_projected :"
            in coq
            and "Theorem concrete_truth_condition_instance_source_audit_model_sound_projected :"
            in coq
            and "Theorem concrete_truth_condition_instance_source_audit_example_1_direct_atomic_sound :"
            in coq
            and "Theorem concrete_truth_condition_instance_source_audit_example_1_kernel_atomic_sound :"
            in coq
            and "Check ConcreteTruthConditionInstanceSourceAuditCertificate."
            in coq
            and "Check concrete_truth_condition_instance_source_audit_example_1_kernel_atomic_sound."
            in coq
        ),
        "lean registered lexical truth model bridge": (
            "structure RegisteredLexicalTruthModel : Type where" in lean
            and "registered_lexical_model_denotes : (A : Type) -> A -> Prop"
            in lean
            and "def fully_registered_truth_conditions_from_registered_lexical_model"
            in lean
            and "def registered_lexical_truth_model : RegisteredLexicalTruthModel := {"
            in lean
            and "def registered_lexical_truth_conditions_from_model : "
            "FullyRegisteredTruthConditionSpec :=" in lean
            and "theorem registered_lexical_truth_model_exists :" in lean
            and "theorem registered_lexical_truth_conditions_from_model_exists :"
            in lean
            and "theorem registered_lexical_truth_model_denotes_fully_registered :"
            in lean
            and "theorem registered_lexical_truth_conditions_from_model_denote_fully_registered :"
            in lean
            and "theorem registered_lexical_truth_conditions_from_model_imply_atomic_closure :"
            in lean
        ),
        "coq registered lexical truth model bridge": (
            "Record RegisteredLexicalTruthModel : Type := {" in coq
            and "registered_lexical_model_denotes : forall A : Type, A -> Prop;"
            in coq
            and "Definition fully_registered_truth_conditions_from_registered_lexical_model"
            in coq
            and "Definition registered_lexical_truth_model : "
            "RegisteredLexicalTruthModel := {|" in coq
            and "Definition registered_lexical_truth_conditions_from_model :"
            in coq
            and "Theorem registered_lexical_truth_model_exists :" in coq
            and "Theorem registered_lexical_truth_conditions_from_model_exists :"
            in coq
            and "Theorem registered_lexical_truth_model_denotes_fully_registered :"
            in coq
            and "Theorem registered_lexical_truth_conditions_from_model_denote_fully_registered :"
            in coq
            and "Theorem registered_lexical_truth_conditions_from_model_imply_atomic_closure :"
            in coq
        ),
        "lean concrete registered atomic model bridge": (
            "structure ConcreteRegisteredAtomicModel : Type where" in lean
            and "concrete_registered_atom_model_denotes : (A : Type) -> A -> Prop"
            in lean
            and "concrete_registered_atom_model_lexical_application : "
            "(A : Type) -> (term : A) -> "
            "RegisteredLexicalApplicationTruth A term ->" in lean
            and "concrete_registered_atom_model_transition : "
            "(theme : Entity) -> (scale : StateScale) ->" in lean
            and "concrete_registered_atom_model_sound : "
            "(A : Type) -> (term : A) ->" in lean
            and "def concrete_registered_atomic_model : "
            "ConcreteRegisteredAtomicModel := {" in lean
            and "theorem concrete_registered_atomic_model_exists :" in lean
            and "theorem concrete_registered_atomic_model_denotes_atomic_base_truth :"
            in lean
            and "theorem concrete_registered_truth_basis_denotes_atomic_base_truth :"
            in lean
            and "#check concrete_registered_atomic_model" in lean
            and "#check concrete_registered_atomic_model_denotes_atomic_base_truth"
            in lean
        ),
        "coq concrete registered atomic model bridge": (
            "Record ConcreteRegisteredAtomicModel : Type := {" in coq
            and "concrete_registered_atom_model_denotes : forall A : Type, A -> Prop;"
            in coq
            and "concrete_registered_atom_model_lexical_application :" in coq
            and "RegisteredLexicalApplicationTruth A term ->" in coq
            and "concrete_registered_atom_model_transition :" in coq
            and "RegisteredStateTransitionTruth theme scale source target ->"
            in coq
            and "concrete_registered_atom_model_sound :" in coq
            and "Definition concrete_registered_atomic_model :" in coq
            and "ConcreteRegisteredAtomicModel := {|" in coq
            and "Theorem concrete_registered_atomic_model_exists :" in coq
            and "Theorem concrete_registered_atomic_model_denotes_atomic_base_truth :"
            in coq
            and "Theorem concrete_registered_truth_basis_denotes_atomic_base_truth :"
            in coq
            and "Check concrete_registered_atomic_model." in coq
            and "Check concrete_registered_atomic_model_denotes_atomic_base_truth."
            in coq
        ),
        "lean concrete registered truth condition instance": (
            "inductive ConcreteRegisteredAtomicTruth : (A : Type) -> A -> Prop where"
            in lean
            and "structure ConcreteRegisteredTruthBasis : Type where" in lean
            and "def concrete_registered_truth_basis : ConcreteRegisteredTruthBasis := {"
            in lean
            and "theorem concrete_registered_atomic_truth_implies_atomic_base_truth :"
            in lean
            and "structure ConcreteRegisteredAtomicModel : Type where" in lean
            and "def concrete_registered_atomic_model : "
            "ConcreteRegisteredAtomicModel := {" in lean
            and "theorem concrete_registered_atomic_model_denotes_atomic_base_truth :"
            in lean
            and "theorem concrete_registered_truth_basis_denotes_atomic_base_truth :"
            in lean
            and "inductive ConcreteRegisteredTruth : (A : Type) -> A -> Prop where"
            in lean
            and "def concrete_registered_truth_conditions : FullyRegisteredTruthConditionSpec := {"
            in lean
            and "theorem concrete_registered_truth_condition_spec_exists :"
            in lean
            and "theorem concrete_registered_truth_conditions_denote_concrete_registered :"
            in lean
            and "theorem concrete_registered_truth_conditions_imply_atomic_closure :"
            in lean
            and "structure ConcreteRegisteredCompositionalModel : Type where"
            in lean
            and "def concrete_registered_compositional_model : "
            "ConcreteRegisteredCompositionalModel := {" in lean
            and "theorem concrete_registered_compositional_model_exists :"
            in lean
            and "theorem "
            "concrete_registered_compositional_model_denotes_concrete_registered :"
            in lean
            and "theorem concrete_registered_compositional_model_repeat_clause :"
            in lean
            and "theorem concrete_registered_compositional_model_at_T_clause :"
            in lean
            and "theorem concrete_registered_compositional_model_cause_clause :"
            in lean
            and "theorem concrete_registered_compositional_model_sigma_Entity_clause :"
            in lean
            and "structure ConcreteRegisteredTruthConditionModel : Type where"
            in lean
            and "def concrete_registered_truth_condition_model : "
            "ConcreteRegisteredTruthConditionModel := {" in lean
            and "theorem concrete_registered_truth_condition_model_exists :"
            in lean
            and "theorem concrete_registered_truth_condition_model_denote_spec :"
            in lean
            and "theorem concrete_registered_truth_condition_model_imply_atomic_closure :"
            in lean
            and "theorem "
            "concrete_registered_truth_condition_model_spec_imply_atomic_closure :"
            in lean
            and "structure ConcreteRegisteredTruthKernel : Type where" in lean
            and "def fully_registered_truth_conditions_from_concrete_registered_kernel"
            in lean
            and "def concrete_registered_truth_kernel : "
            "ConcreteRegisteredTruthKernel := {" in lean
            and "def concrete_registered_truth_conditions_from_kernel : "
            "FullyRegisteredTruthConditionSpec :=" in lean
            and "theorem concrete_registered_truth_kernel_exists :" in lean
            and "theorem concrete_registered_truth_conditions_from_kernel_exists :"
            in lean
            and "theorem concrete_registered_truth_kernel_denotes_concrete_registered :"
            in lean
            and "theorem concrete_registered_truth_conditions_from_kernel_denote_concrete_registered :"
            in lean
            and "theorem concrete_registered_truth_conditions_from_kernel_imply_atomic_closure :"
            in lean
            and "theorem example_4_concrete_registered_truth :"
            in lean
            and "theorem example_4_concrete_registered_truth_kernel_sound :"
            in lean
            and "theorem example_4_concrete_registered_truth_conditions_from_kernel_sound :"
            in lean
            and "theorem example_4_concrete_registered_truth_conditions_from_kernel_atomic_sound :"
            in lean
            and "theorem example_4_concrete_registered_truth_condition_sound :"
            in lean
            and "theorem example_4_concrete_registered_truth_condition_atomic_sound :"
            in lean
            and "#check example_4_concrete_registered_truth_kernel_sound"
            in lean
            and "#check example_4_concrete_registered_truth_conditions_from_kernel_sound"
            in lean
            and "#check example_4_concrete_registered_truth_conditions_from_kernel_atomic_sound"
            in lean
            and "#check example_4_concrete_registered_truth_condition_sound"
            in lean
            and "#check concrete_registered_truth_conditions" in lean
            and "#check concrete_registered_compositional_model" in lean
            and "#check concrete_registered_compositional_model_repeat_clause"
            in lean
            and "#check concrete_registered_truth_condition_model" in lean
            and "#check concrete_registered_truth_condition_model_denote_spec"
            in lean
            and "#check concrete_registered_truth_kernel" in lean
            and "#check concrete_registered_truth_conditions_from_kernel" in lean
        ),
        "lean concrete registered compositional model bridge": (
            "structure ConcreteRegisteredCompositionalModel : Type where"
            in lean
            and "concrete_registered_composition_denotes : (A : Type) -> A -> Prop"
            in lean
            and "concrete_registered_composition_atomic : " in lean
            and "concrete_registered_composition_sigma_Entity : " in lean
            and "concrete_registered_composition_repeat : " in lean
            and "concrete_registered_composition_at_T : " in lean
            and "concrete_registered_composition_cause : " in lean
            and "concrete_registered_composition_sound : " in lean
            and "def concrete_registered_compositional_model : "
            "ConcreteRegisteredCompositionalModel := {" in lean
            and "theorem concrete_registered_compositional_model_exists :"
            in lean
            and "theorem "
            "concrete_registered_compositional_model_denotes_concrete_registered :"
            in lean
            and "theorem "
            "concrete_registered_compositional_model_imply_atomic_closure :"
            in lean
            and "theorem concrete_registered_compositional_model_repeat_clause :"
            in lean
            and "theorem concrete_registered_compositional_model_at_T_clause :"
            in lean
            and "theorem concrete_registered_compositional_model_cause_clause :"
            in lean
            and "theorem concrete_registered_compositional_model_sigma_Entity_clause :"
            in lean
            and "#check concrete_registered_compositional_model" in lean
            and "#check concrete_registered_compositional_model_repeat_clause"
            in lean
            and "#check concrete_registered_compositional_model_cause_clause"
            in lean
        ),
        "lean concrete registered truth condition model bridge": (
            "structure ConcreteRegisteredTruthConditionModel : Type where"
            in lean
            and "concrete_registered_model_denotes : (A : Type) -> A -> Prop"
            in lean
            and "concrete_registered_model_spec : FullyRegisteredTruthConditionSpec"
            in lean
            and "concrete_registered_model_denote_spec : " in lean
            and "concrete_registered_model_sound : " in lean
            and "def concrete_registered_truth_condition_model : "
            "ConcreteRegisteredTruthConditionModel := {" in lean
            and "theorem concrete_registered_truth_condition_model_exists :"
            in lean
            and "theorem concrete_registered_truth_condition_model_denote_spec :"
            in lean
            and "theorem concrete_registered_truth_condition_model_imply_atomic_closure :"
            in lean
            and "theorem "
            "concrete_registered_truth_condition_model_spec_imply_atomic_closure :"
            in lean
            and "#check concrete_registered_truth_condition_model" in lean
            and "#check concrete_registered_truth_condition_model_denote_spec"
            in lean
            and "#check "
            "concrete_registered_truth_condition_model_spec_imply_atomic_closure"
            in lean
        ),
        "coq concrete registered truth condition instance": (
            "Inductive ConcreteRegisteredAtomicTruth : forall A : Type, A -> Prop :="
            in coq
            and "Record ConcreteRegisteredTruthBasis : Type := {" in coq
            and "Definition concrete_registered_truth_basis :" in coq
            and "ConcreteRegisteredTruthBasis := {|" in coq
            and "Theorem concrete_registered_atomic_truth_implies_atomic_base_truth :"
            in coq
            and "Record ConcreteRegisteredAtomicModel : Type := {" in coq
            and "Definition concrete_registered_atomic_model :" in coq
            and "Theorem concrete_registered_atomic_model_denotes_atomic_base_truth :"
            in coq
            and "Theorem concrete_registered_truth_basis_denotes_atomic_base_truth :"
            in coq
            and "Inductive ConcreteRegisteredTruth : forall A : Type, A -> Prop :="
            in coq
            and "Definition concrete_registered_truth_conditions : FullyRegisteredTruthConditionSpec := {|"
            in coq
            and "Theorem concrete_registered_truth_condition_spec_exists :"
            in coq
            and "Theorem concrete_registered_truth_conditions_denote_concrete_registered :"
            in coq
            and "Theorem concrete_registered_truth_conditions_imply_atomic_closure :"
            in coq
            and "Record ConcreteRegisteredCompositionalModel : Type := {"
            in coq
            and "Definition concrete_registered_compositional_model :"
            in coq
            and "ConcreteRegisteredCompositionalModel := {|" in coq
            and "Theorem concrete_registered_compositional_model_exists :"
            in coq
            and "Theorem concrete_registered_compositional_model_denotes_concrete_registered :"
            in coq
            and "Theorem concrete_registered_compositional_model_repeat_clause :"
            in coq
            and "Theorem concrete_registered_compositional_model_at_T_clause :"
            in coq
            and "Theorem concrete_registered_compositional_model_cause_clause :"
            in coq
            and "Theorem concrete_registered_compositional_model_sigma_Entity_clause :"
            in coq
            and "Record ConcreteRegisteredTruthConditionModel : Type := {"
            in coq
            and "Definition concrete_registered_truth_condition_model :"
            in coq
            and "ConcreteRegisteredTruthConditionModel := {|" in coq
            and "Theorem concrete_registered_truth_condition_model_exists :"
            in coq
            and "Theorem concrete_registered_truth_condition_model_denote_spec :"
            in coq
            and "Theorem concrete_registered_truth_condition_model_imply_atomic_closure :"
            in coq
            and "Theorem concrete_registered_truth_condition_model_spec_imply_atomic_closure :"
            in coq
            and "Record ConcreteRegisteredTruthKernel : Type := {" in coq
            and "Definition fully_registered_truth_conditions_from_concrete_registered_kernel"
            in coq
            and "Definition concrete_registered_truth_kernel : "
            "ConcreteRegisteredTruthKernel := {|" in coq
            and "Definition concrete_registered_truth_conditions_from_kernel :"
            in coq
            and "Theorem concrete_registered_truth_kernel_exists :" in coq
            and "Theorem concrete_registered_truth_conditions_from_kernel_exists :"
            in coq
            and "Theorem concrete_registered_truth_kernel_denotes_concrete_registered :"
            in coq
            and "Theorem concrete_registered_truth_conditions_from_kernel_denote_concrete_registered :"
            in coq
            and "Theorem concrete_registered_truth_conditions_from_kernel_imply_atomic_closure :"
            in coq
            and "Theorem example_4_concrete_registered_truth :"
            in coq
            and "Theorem example_4_concrete_registered_truth_kernel_sound :"
            in coq
            and "Theorem example_4_concrete_registered_truth_conditions_from_kernel_sound :"
            in coq
            and "Theorem example_4_concrete_registered_truth_conditions_from_kernel_atomic_sound :"
            in coq
            and "Theorem example_4_concrete_registered_truth_condition_sound :"
            in coq
            and "Theorem example_4_concrete_registered_truth_condition_atomic_sound :"
            in coq
            and "Check example_4_concrete_registered_truth_kernel_sound."
            in coq
            and "Check example_4_concrete_registered_truth_conditions_from_kernel_sound."
            in coq
            and "Check example_4_concrete_registered_truth_conditions_from_kernel_atomic_sound."
            in coq
            and "Check example_4_concrete_registered_truth_condition_sound."
            in coq
            and "Check concrete_registered_truth_conditions." in coq
            and "Check concrete_registered_compositional_model." in coq
            and "Check concrete_registered_compositional_model_repeat_clause."
            in coq
            and "Check concrete_registered_truth_condition_model." in coq
            and "Check concrete_registered_truth_condition_model_denote_spec."
            in coq
            and "Check concrete_registered_truth_kernel." in coq
            and "Check concrete_registered_truth_conditions_from_kernel." in coq
        ),
        "coq concrete registered compositional model bridge": (
            "Record ConcreteRegisteredCompositionalModel : Type := {" in coq
            and "concrete_registered_composition_denotes : forall A : Type, A -> Prop;"
            in coq
            and "concrete_registered_composition_atomic :" in coq
            and "concrete_registered_composition_sigma_Entity :" in coq
            and "concrete_registered_composition_repeat :" in coq
            and "concrete_registered_composition_at_T :" in coq
            and "concrete_registered_composition_cause :" in coq
            and "concrete_registered_composition_sound :" in coq
            and "Definition concrete_registered_compositional_model :"
            in coq
            and "ConcreteRegisteredCompositionalModel := {|" in coq
            and "Theorem concrete_registered_compositional_model_exists :"
            in coq
            and "Theorem concrete_registered_compositional_model_denotes_concrete_registered :"
            in coq
            and "Theorem concrete_registered_compositional_model_imply_atomic_closure :"
            in coq
            and "Theorem concrete_registered_compositional_model_repeat_clause :"
            in coq
            and "Theorem concrete_registered_compositional_model_at_T_clause :"
            in coq
            and "Theorem concrete_registered_compositional_model_cause_clause :"
            in coq
            and "Theorem concrete_registered_compositional_model_sigma_Entity_clause :"
            in coq
            and "Check concrete_registered_compositional_model." in coq
            and "Check concrete_registered_compositional_model_repeat_clause."
            in coq
            and "Check concrete_registered_compositional_model_cause_clause."
            in coq
        ),
        "coq concrete registered truth condition model bridge": (
            "Record ConcreteRegisteredTruthConditionModel : Type := {" in coq
            and "concrete_registered_model_denotes : forall A : Type, A -> Prop;"
            in coq
            and "concrete_registered_model_spec : FullyRegisteredTruthConditionSpec;"
            in coq
            and "concrete_registered_model_denote_spec :" in coq
            and "concrete_registered_model_sound :" in coq
            and "Definition concrete_registered_truth_condition_model :"
            in coq
            and "ConcreteRegisteredTruthConditionModel := {|" in coq
            and "Theorem concrete_registered_truth_condition_model_exists :"
            in coq
            and "Theorem concrete_registered_truth_condition_model_denote_spec :"
            in coq
            and "Theorem concrete_registered_truth_condition_model_imply_atomic_closure :"
            in coq
            and "Theorem concrete_registered_truth_condition_model_spec_imply_atomic_closure :"
            in coq
            and "Check concrete_registered_truth_condition_model." in coq
            and "Check concrete_registered_truth_condition_model_denote_spec."
            in coq
            and "Check concrete_registered_truth_condition_model_spec_imply_atomic_closure."
            in coq
        ),
        "lean concrete registered example truth instance package": (
            "structure ConcreteRegisteredExampleTruthInstances : Type where"
            in lean
            and "example_4_concrete_truth_instance : "
            "concrete_registered_truth_conditions."
            "fully_registered_truth_denotes PropT example_4" in lean
            and "def concrete_registered_example_truth_instances : "
            "ConcreteRegisteredExampleTruthInstances := {" in lean
            and "theorem concrete_registered_example_truth_instances_exists :"
            in lean
            and "theorem concrete_registered_example_4_truth_instance_atomic_sound :"
            in lean
            and "#check concrete_registered_example_4_truth_instance_atomic_sound"
            in lean
            and "#check concrete_registered_example_truth_instances" in lean
        ),
        "coq concrete registered example truth instance package": (
            "Record ConcreteRegisteredExampleTruthInstances : Type := {" in coq
            and "example_4_concrete_truth_instance :" in coq
            and "fully_registered_truth_denotes concrete_registered_truth_conditions "
            "PropT example_4" in coq
            and "Definition concrete_registered_example_truth_instances : "
            "ConcreteRegisteredExampleTruthInstances := {|" in coq
            and "Theorem concrete_registered_example_truth_instances_exists :"
            in coq
            and "Theorem concrete_registered_example_4_truth_instance_atomic_sound :"
            in coq
            and "exact (example_4_concrete_truth_instance "
            "concrete_registered_example_truth_instances)." in coq
            and "Check concrete_registered_example_4_truth_instance_atomic_sound." in coq
            and "Check concrete_registered_example_truth_instances." in coq
        ),
        "lean concrete registered kernel example truth instance package": (
            "structure ConcreteRegisteredKernelExampleTruthInstances : Type where"
            in lean
            and "example_4_kernel_truth_instance : "
            "concrete_registered_truth_conditions_from_kernel."
            "fully_registered_truth_denotes PropT example_4" in lean
            and "def concrete_registered_kernel_example_truth_instances : "
            "ConcreteRegisteredKernelExampleTruthInstances := {" in lean
            and "theorem concrete_registered_kernel_example_truth_instances_exists :"
            in lean
            and "theorem concrete_registered_kernel_example_4_truth_instance_atomic_sound :"
            in lean
            and "#check concrete_registered_kernel_example_4_truth_instance_atomic_sound"
            in lean
            and "#check concrete_registered_kernel_example_truth_instances"
            in lean
        ),
        "coq concrete registered kernel example truth instance package": (
            "Record ConcreteRegisteredKernelExampleTruthInstances : Type := {"
            in coq
            and "example_4_kernel_truth_instance :" in coq
            and "fully_registered_truth_denotes "
            "concrete_registered_truth_conditions_from_kernel "
            "PropT example_4" in coq
            and "Definition concrete_registered_kernel_example_truth_instances : "
            "ConcreteRegisteredKernelExampleTruthInstances := {|" in coq
            and "Theorem concrete_registered_kernel_example_truth_instances_exists :"
            in coq
            and "Theorem concrete_registered_kernel_example_4_truth_instance_atomic_sound :"
            in coq
            and "exact (example_4_kernel_truth_instance "
            "concrete_registered_kernel_example_truth_instances)." in coq
            and "Check concrete_registered_kernel_example_4_truth_instance_atomic_sound."
            in coq
            and "Check concrete_registered_kernel_example_truth_instances." in coq
        ),
        "lean model-interpretable truth kernel instance": (
            "def model_interpretable_truth_kernel_denotes : (A : Type) -> A -> Prop :="
            in lean
            and "def model_interpretable_truth_kernel : ConcreteTruthConditionKernel := {"
            in lean
            and "kernel_denotes := model_interpretable_truth_kernel_denotes" in lean
            and "def model_interpretable_truth_conditions_from_kernel : TruthConditionSpec :="
            in lean
            and "theorem model_interpretable_truth_kernel_exists :" in lean
            and "theorem model_interpretable_truth_kernel_denotes_model_interpretable :"
            in lean
        ),
        "coq model-interpretable truth kernel instance": (
            "Definition model_interpretable_truth_kernel_denotes : forall A : Type, A -> Prop :="
            in coq
            and "Definition model_interpretable_truth_kernel : ConcreteTruthConditionKernel := {|"
            in coq
            and "kernel_denotes := model_interpretable_truth_kernel_denotes" in coq
            and "Definition model_interpretable_truth_conditions_from_kernel : TruthConditionSpec :="
            in coq
            and "Theorem model_interpretable_truth_kernel_exists :" in coq
            and "Theorem model_interpretable_truth_kernel_denotes_model_interpretable :"
            in coq
        ),
        "lean syntax-directed truth kernel instance": (
            "def syntax_directed_truth_kernel_denotes : (A : Type) -> A -> Prop :="
            in lean
            and "def syntax_directed_truth_kernel : ConcreteTruthConditionKernel := {"
            in lean
            and "kernel_denotes := syntax_directed_truth_kernel_denotes" in lean
            and "def syntax_directed_truth_conditions_from_kernel : TruthConditionSpec :="
            in lean
            and "theorem syntax_directed_truth_kernel_exists :" in lean
            and "theorem syntax_directed_truth_kernel_denotes_syntax_directed_truth :"
            in lean
        ),
        "coq syntax-directed truth kernel instance": (
            "Definition syntax_directed_truth_kernel_denotes : forall A : Type, A -> Prop :="
            in coq
            and "Definition syntax_directed_truth_kernel : ConcreteTruthConditionKernel := {|"
            in coq
            and "kernel_denotes := syntax_directed_truth_kernel_denotes" in coq
            and "Definition syntax_directed_truth_conditions_from_kernel : TruthConditionSpec :="
            in coq
            and "Theorem syntax_directed_truth_kernel_exists :" in coq
            and "Theorem syntax_directed_truth_kernel_denotes_syntax_directed_truth :"
            in coq
        ),
        "lean semantic preservation obligation status": (
            "inductive ObligationStatus : Type" in lean
            and "structure SemanticPreservationObligation : Type where" in lean
        ),
        "coq semantic preservation obligation status": (
            "Inductive ObligationStatus : Type :=" in coq
            and "Record SemanticPreservationObligation : Type := {" in coq
        ),
        "lean preservation target match relation": (
            "def PreservationTargetMatches (A : Type) (term : A) (target : SemanticPreservationObligation) : Prop :="
            in lean
        ),
        "coq preservation target match relation": (
            "Definition PreservationTargetMatches" in coq
            and "obligation_statement target = SemanticPreservation A term." in coq
        ),
        "lean semantic preservation obligations": (
            lean_example_count > 0 and lean_obligation_count == lean_example_count
        ),
        "coq semantic preservation obligations": (
            coq_example_count > 0 and coq_obligation_count == coq_example_count
        ),
        "lean semantic preservation obligation records": (
            lean_obligation_record_count == lean_example_count
        ),
        "coq semantic preservation obligation records": (
            coq_obligation_record_count == coq_example_count
        ),
        "lean semantic preservation wellformedness statements": (
            lean_obligation_wellformed_count == lean_example_count
        ),
        "coq semantic preservation wellformedness proofs": (
            coq_obligation_wellformed_count == coq_example_count
            and coq_obligation_wellformed_proof_count == coq_example_count
        ),
        "lean preservation target match proofs": (
            lean_target_match_count == lean_example_count
        ),
        "coq preservation target match proofs": (
            coq_target_match_count == coq_example_count
            and coq_reflexive_proof_count >= coq_example_count
        ),
        "lean structural semantic preservation proofs": (
            lean_structural_proof_count == lean_example_count
            and "#check example_4_semantic_preservation_proved" in lean
        ),
        "coq structural semantic preservation proofs": (
            coq_structural_proof_count == coq_example_count
            and "Check example_4_semantic_preservation_proved." in coq
            and "apply preserve_repeat." in coq
            and "apply preserve_sigma_Food." in coq
            and "apply preserve_cause." in coq
        ),
        "lean model interpretability boundary proofs": (
            lean_model_boundary_count == lean_example_count
            and "#check example_4_model_interpretable" in lean
            and "apply semantic_preservation_model_interpretable" in lean
        ),
        "coq model interpretability boundary proofs": (
            coq_model_boundary_count == coq_example_count
            and "Check example_4_model_interpretable." in coq
            and "apply semantic_preservation_model_interpretable." in coq
        ),
        "lean syntax-directed truth boundary proofs": (
            lean_syntax_directed_truth_count == lean_example_count
            and "#check example_4_syntax_directed_truth" in lean
            and "apply semantic_preservation_syntax_directed_truth" in lean
        ),
        "coq syntax-directed truth boundary proofs": (
            coq_syntax_directed_truth_count == coq_example_count
            and "Check example_4_syntax_directed_truth." in coq
            and "apply semantic_preservation_syntax_directed_truth." in coq
        ),
        "lean denotational soundness boundary proofs": (
            lean_denotation_sound_count == lean_example_count
            and "#check example_4_denotationally_sound" in lean
            and "apply model_interpretable_denotational_sound" in lean
        ),
        "coq denotational soundness boundary proofs": (
            coq_denotation_sound_count == coq_example_count
            and "Check example_4_denotationally_sound." in coq
            and "apply model_interpretable_denotational_sound." in coq
        ),
        "lean truth condition soundness proofs": (
            lean_truth_condition_sound_count == lean_example_count
            and "#check example_4_truth_condition_sound" in lean
            and "apply truth_conditions_induce_denotational_soundness" in lean
        ),
        "coq truth condition soundness proofs": (
            coq_truth_condition_sound_count == coq_example_count
            and "Check example_4_truth_condition_sound." in coq
            and "apply truth_conditions_induce_denotational_soundness." in coq
        ),
        "lean tautological truth condition soundness proofs": (
            lean_tautological_truth_condition_sound_count == lean_example_count
            and "#check example_4_tautological_truth_condition_sound" in lean
            and "apply tautological_truth_conditions_denote_model_interpretable"
            in lean
        ),
        "coq tautological truth condition soundness proofs": (
            coq_tautological_truth_condition_sound_count == coq_example_count
            and "Check example_4_tautological_truth_condition_sound." in coq
            and "apply tautological_truth_conditions_denote_model_interpretable."
            in coq
        ),
        "lean structural truth condition soundness proofs": (
            lean_structural_truth_condition_sound_count == lean_example_count
            and "#check example_4_structural_truth_condition_sound" in lean
            and "apply structural_truth_conditions_denote_model_interpretable"
            in lean
        ),
        "coq structural truth condition soundness proofs": (
            coq_structural_truth_condition_sound_count == coq_example_count
            and "Check example_4_structural_truth_condition_sound." in coq
            and "apply structural_truth_conditions_denote_model_interpretable."
            in coq
        ),
        "lean concrete kernel truth condition soundness proofs": (
            lean_concrete_kernel_truth_condition_sound_count == lean_example_count
            and "#check example_4_concrete_kernel_truth_condition_sound" in lean
            and "apply concrete_kernel_induces_truth_condition_soundness" in lean
        ),
        "coq concrete kernel truth condition soundness proofs": (
            coq_concrete_kernel_truth_condition_sound_count == coq_example_count
            and "Check example_4_concrete_kernel_truth_condition_sound." in coq
            and "apply concrete_kernel_induces_truth_condition_soundness." in coq
        ),
        "lean model-interpretable truth kernel soundness proofs": (
            lean_model_interpretable_truth_kernel_sound_count == lean_example_count
            and "#check example_4_model_interpretable_truth_kernel_sound" in lean
            and "apply model_interpretable_truth_kernel_denotes_model_interpretable"
            in lean
        ),
        "coq model-interpretable truth kernel soundness proofs": (
            coq_model_interpretable_truth_kernel_sound_count == coq_example_count
            and "Check example_4_model_interpretable_truth_kernel_sound." in coq
            and "apply model_interpretable_truth_kernel_denotes_model_interpretable."
            in coq
        ),
        "lean primitive truth kernel soundness proofs": (
            lean_primitive_truth_kernel_sound_count == lean_example_count
            and "#check example_4_primitive_truth_kernel_sound" in lean
            and "apply primitive_truth_kernel_denotes_model_interpretable" in lean
        ),
        "coq primitive truth kernel soundness proofs": (
            coq_primitive_truth_kernel_sound_count == coq_example_count
            and "Check example_4_primitive_truth_kernel_sound." in coq
            and "apply primitive_truth_kernel_denotes_model_interpretable."
            in coq
        ),
        "lean atomic closure truth proofs": (
            lean_atomic_closure_truth_count == lean_example_count
            and "#check example_4_atomic_closure_truth" in lean
            and "apply model_interpretable_atomic_closure_truth" in lean
        ),
        "coq atomic closure truth proofs": (
            coq_atomic_closure_truth_count == coq_example_count
            and "Check example_4_atomic_closure_truth." in coq
            and "apply model_interpretable_atomic_closure_truth." in coq
        ),
        "lean atomic closure truth kernel soundness proofs": (
            lean_atomic_closure_truth_kernel_sound_count == lean_example_count
            and "#check example_4_atomic_closure_truth_kernel_sound" in lean
            and "apply atomic_closure_truth_kernel_denotes_atomic_closure_truth"
            in lean
        ),
        "coq atomic closure truth kernel soundness proofs": (
            coq_atomic_closure_truth_kernel_sound_count == coq_example_count
            and "Check example_4_atomic_closure_truth_kernel_sound." in coq
            and "apply atomic_closure_truth_kernel_denotes_atomic_closure_truth."
            in coq
        ),
        "lean fully registered truth condition soundness proofs": (
            lean_fully_registered_atomic_closure_truth_count == lean_example_count
            and lean_fully_registered_truth_condition_sound_count == lean_example_count
            and "#check example_4_fully_registered_atomic_closure_truth" in lean
            and "#check example_4_fully_registered_truth_condition_sound" in lean
            and "apply fully_registered_truth_conditions_denote_fully_registered"
            in lean
        ),
        "coq fully registered truth condition soundness proofs": (
            coq_fully_registered_atomic_closure_truth_count == coq_example_count
            and coq_fully_registered_truth_condition_sound_count == coq_example_count
            and "Check example_4_fully_registered_atomic_closure_truth." in coq
            and "Check example_4_fully_registered_truth_condition_sound." in coq
            and "apply fully_registered_truth_conditions_denote_fully_registered."
            in coq
        ),
        "lean registered example truth instance atomic proofs": (
            lean_registered_example_truth_instance_atomic_sound_count
            == lean_example_count
            and "#check registered_example_4_truth_instance_atomic_sound" in lean
            and "apply fully_registered_truth_conditions_imply_atomic_closure"
            in lean
        ),
        "coq registered example truth instance atomic proofs": (
            coq_registered_example_truth_instance_atomic_sound_count
            == coq_example_count
            and "Check registered_example_4_truth_instance_atomic_sound." in coq
            and "apply fully_registered_truth_conditions_imply_atomic_closure."
            in coq
        ),
        "lean registered lexical truth model soundness proofs": (
            lean_registered_lexical_truth_model_sound_count == lean_example_count
            and lean_registered_lexical_truth_conditions_from_model_sound_count
            == lean_example_count
            and "#check example_4_registered_lexical_truth_model_sound" in lean
            and "#check example_4_registered_lexical_truth_conditions_from_model_sound"
            in lean
            and "apply registered_lexical_truth_model_denotes_fully_registered"
            in lean
            and "apply registered_lexical_truth_conditions_from_model_denote_fully_registered"
            in lean
        ),
        "coq registered lexical truth model soundness proofs": (
            coq_registered_lexical_truth_model_sound_count == coq_example_count
            and coq_registered_lexical_truth_conditions_from_model_sound_count
            == coq_example_count
            and "Check example_4_registered_lexical_truth_model_sound." in coq
            and "Check example_4_registered_lexical_truth_conditions_from_model_sound."
            in coq
            and "apply registered_lexical_truth_model_denotes_fully_registered."
            in coq
            and "apply registered_lexical_truth_conditions_from_model_denote_fully_registered."
            in coq
        ),
        "lean concrete registered truth condition soundness proofs": (
            lean_concrete_registered_truth_count == lean_example_count
            and lean_concrete_registered_truth_kernel_sound_count
            == lean_example_count
            and lean_concrete_registered_truth_conditions_from_kernel_sound_count
            == lean_example_count
            and lean_concrete_registered_truth_conditions_from_kernel_atomic_sound_count
            == lean_example_count
            and lean_concrete_registered_truth_condition_sound_count
            == lean_example_count
            and lean_concrete_registered_truth_condition_atomic_sound_count
            == lean_example_count
            and "#check example_4_concrete_registered_truth" in lean
            and "#check example_4_concrete_registered_truth_kernel_sound"
            in lean
            and "#check example_4_concrete_registered_truth_conditions_from_kernel_sound"
            in lean
            and "#check example_4_concrete_registered_truth_conditions_from_kernel_atomic_sound"
            in lean
            and "#check example_4_concrete_registered_truth_condition_sound"
            in lean
            and "#check example_4_concrete_registered_truth_condition_atomic_sound"
            in lean
            and "apply concrete_registered_truth_kernel_denotes_concrete_registered"
            in lean
            and "apply concrete_registered_truth_conditions_from_kernel_denote_concrete_registered"
            in lean
            and "apply concrete_registered_truth_conditions_from_kernel_imply_atomic_closure"
            in lean
            and "apply concrete_registered_truth_conditions_denote_concrete_registered"
            in lean
            and "apply concrete_registered_truth_conditions_imply_atomic_closure"
            in lean
        ),
        "coq concrete registered truth condition soundness proofs": (
            coq_concrete_registered_truth_count == coq_example_count
            and coq_concrete_registered_truth_kernel_sound_count
            == coq_example_count
            and coq_concrete_registered_truth_conditions_from_kernel_sound_count
            == coq_example_count
            and coq_concrete_registered_truth_conditions_from_kernel_atomic_sound_count
            == coq_example_count
            and coq_concrete_registered_truth_condition_sound_count
            == coq_example_count
            and coq_concrete_registered_truth_condition_atomic_sound_count
            == coq_example_count
            and "Check example_4_concrete_registered_truth." in coq
            and "Check example_4_concrete_registered_truth_kernel_sound."
            in coq
            and "Check example_4_concrete_registered_truth_conditions_from_kernel_sound."
            in coq
            and "Check example_4_concrete_registered_truth_conditions_from_kernel_atomic_sound."
            in coq
            and "Check example_4_concrete_registered_truth_condition_sound."
            in coq
            and "Check example_4_concrete_registered_truth_condition_atomic_sound."
            in coq
            and "apply concrete_registered_truth_kernel_denotes_concrete_registered."
            in coq
            and "apply concrete_registered_truth_conditions_from_kernel_denote_concrete_registered."
            in coq
            and "apply concrete_registered_truth_conditions_from_kernel_imply_atomic_closure."
            in coq
            and "apply concrete_registered_truth_conditions_denote_concrete_registered."
            in coq
            and "apply concrete_registered_truth_conditions_imply_atomic_closure."
            in coq
        ),
        "lean registered evidence-backed truth condition sources": (
            lean_concrete_registered_evidence_backed_truth_condition_sound_count
            == lean_example_count
            and lean_concrete_registered_evidence_backed_truth_condition_atomic_sound_count
            == lean_example_count
            and "structure RegisteredEvidenceBackedTruthConditionSources : Type where"
            in lean
            and "registered_evidence_denotes : (A : Type) -> A -> Prop" in lean
            and "registered_evidence_lexical_application : " in lean
            and "registered_evidence_transition : " in lean
            and "def fully_registered_truth_conditions_from_registered_evidence_sources"
            in lean
            and "theorem registered_evidence_backed_truth_condition_sources_induce_fully_registered_truth_conditions :"
            in lean
            and "def concrete_registered_evidence_backed_truth_sources : "
            "RegisteredEvidenceBackedTruthConditionSources := {" in lean
            and "def concrete_registered_evidence_backed_truth_conditions : "
            "FullyRegisteredTruthConditionSpec :=" in lean
            and "theorem concrete_registered_evidence_backed_truth_sources_exist :"
            in lean
            and "theorem concrete_registered_evidence_backed_truth_conditions_exists :"
            in lean
            and "theorem "
            "concrete_registered_evidence_backed_truth_conditions_denote_concrete_registered :"
            in lean
            and "theorem "
            "concrete_registered_evidence_backed_truth_conditions_imply_atomic_closure :"
            in lean
            and "#check RegisteredEvidenceBackedTruthConditionSources" in lean
            and "#check fully_registered_truth_conditions_from_registered_evidence_sources"
            in lean
            and "#check concrete_registered_evidence_backed_truth_sources" in lean
            and "#check concrete_registered_evidence_backed_truth_conditions" in lean
            and "#check example_4_concrete_registered_evidence_backed_truth_condition_sound"
            in lean
            and "#check example_4_concrete_registered_evidence_backed_truth_condition_atomic_sound"
            in lean
            and "apply concrete_registered_evidence_backed_truth_conditions_denote_concrete_registered"
            in lean
            and "apply concrete_registered_evidence_backed_truth_conditions_imply_atomic_closure"
            in lean
        ),
        "coq registered evidence-backed truth condition sources": (
            coq_concrete_registered_evidence_backed_truth_condition_sound_count
            == coq_example_count
            and coq_concrete_registered_evidence_backed_truth_condition_atomic_sound_count
            == coq_example_count
            and "Record RegisteredEvidenceBackedTruthConditionSources : Type := {"
            in coq
            and "registered_evidence_denotes : forall A : Type, A -> Prop;"
            in coq
            and "registered_evidence_lexical_application :" in coq
            and "registered_evidence_transition :" in coq
            and "Definition fully_registered_truth_conditions_from_registered_evidence_sources"
            in coq
            and "Theorem registered_evidence_backed_truth_condition_sources_induce_fully_registered_truth_conditions :"
            in coq
            and "Definition concrete_registered_evidence_backed_truth_sources :"
            in coq
            and "RegisteredEvidenceBackedTruthConditionSources := {|" in coq
            and "Definition concrete_registered_evidence_backed_truth_conditions :"
            in coq
            and "Theorem concrete_registered_evidence_backed_truth_sources_exist :"
            in coq
            and "Theorem concrete_registered_evidence_backed_truth_conditions_exists :"
            in coq
            and "Theorem concrete_registered_evidence_backed_truth_conditions_denote_concrete_registered :"
            in coq
            and "Theorem concrete_registered_evidence_backed_truth_conditions_imply_atomic_closure :"
            in coq
            and "Check RegisteredEvidenceBackedTruthConditionSources." in coq
            and "Check fully_registered_truth_conditions_from_registered_evidence_sources."
            in coq
            and "Check concrete_registered_evidence_backed_truth_sources." in coq
            and "Check concrete_registered_evidence_backed_truth_conditions." in coq
            and "Check example_4_concrete_registered_evidence_backed_truth_condition_sound."
            in coq
            and "Check example_4_concrete_registered_evidence_backed_truth_condition_atomic_sound."
            in coq
            and "apply concrete_registered_evidence_backed_truth_conditions_denote_concrete_registered."
            in coq
            and "apply concrete_registered_evidence_backed_truth_conditions_imply_atomic_closure."
            in coq
        ),
        "lean concrete registered evidence-backed truth condition model bridge": (
            "structure ConcreteRegisteredEvidenceBackedTruthConditionModel : Type where"
            in lean
            and "concrete_registered_evidence_backed_model_denotes : "
            in lean
            and "concrete_registered_evidence_backed_model_spec : "
            "FullyRegisteredTruthConditionSpec" in lean
            and "concrete_registered_evidence_backed_model_denote_spec : "
            in lean
            and "concrete_registered_evidence_backed_model_sound : "
            in lean
            and "def concrete_registered_evidence_backed_truth_condition_model : "
            "ConcreteRegisteredEvidenceBackedTruthConditionModel := {" in lean
            and "theorem concrete_registered_evidence_backed_truth_condition_model_exists :"
            in lean
            and "theorem "
            "concrete_registered_evidence_backed_truth_condition_model_denote_spec :"
            in lean
            and "theorem "
            "concrete_registered_evidence_backed_truth_condition_model_imply_atomic_closure :"
            in lean
            and "theorem "
            "concrete_registered_evidence_backed_truth_condition_model_spec_imply_atomic_closure :"
            in lean
            and "concrete_registered_evidence_backed_truth_conditions_denote_concrete_registered"
            in lean
            and "concrete_registered_evidence_backed_truth_conditions_imply_atomic_closure"
            in lean
            and "#check concrete_registered_evidence_backed_truth_condition_model"
            in lean
            and "#check concrete_registered_evidence_backed_truth_condition_model_denote_spec"
            in lean
            and "#check "
            "concrete_registered_evidence_backed_truth_condition_model_spec_imply_atomic_closure"
            in lean
        ),
        "coq concrete registered evidence-backed truth condition model bridge": (
            "Record ConcreteRegisteredEvidenceBackedTruthConditionModel : Type := {"
            in coq
            and "concrete_registered_evidence_backed_model_denotes : "
            "forall A : Type, A -> Prop;" in coq
            and "concrete_registered_evidence_backed_model_spec : "
            "FullyRegisteredTruthConditionSpec;" in coq
            and "concrete_registered_evidence_backed_model_denote_spec :"
            in coq
            and "concrete_registered_evidence_backed_model_sound :"
            in coq
            and "Definition concrete_registered_evidence_backed_truth_condition_model :"
            in coq
            and "ConcreteRegisteredEvidenceBackedTruthConditionModel := {|"
            in coq
            and "Theorem concrete_registered_evidence_backed_truth_condition_model_exists :"
            in coq
            and "Theorem concrete_registered_evidence_backed_truth_condition_model_denote_spec :"
            in coq
            and "Theorem concrete_registered_evidence_backed_truth_condition_model_imply_atomic_closure :"
            in coq
            and "Theorem concrete_registered_evidence_backed_truth_condition_model_spec_imply_atomic_closure :"
            in coq
            and "concrete_registered_evidence_backed_truth_conditions_denote_concrete_registered;"
            in coq
            and "apply concrete_registered_evidence_backed_truth_conditions_imply_atomic_closure."
            in coq
            and "Check concrete_registered_evidence_backed_truth_condition_model."
            in coq
            and "Check concrete_registered_evidence_backed_truth_condition_model_denote_spec."
            in coq
            and "Check "
            "concrete_registered_evidence_backed_truth_condition_model_spec_imply_atomic_closure."
            in coq
        ),
        "lean concrete registered evidence-backed example truth instance package": (
            lean_concrete_registered_evidence_backed_example_truth_instance_atomic_sound_count
            == lean_example_count
            and "structure ConcreteRegisteredEvidenceBackedExampleTruthInstances : Type where"
            in lean
            and "def concrete_registered_evidence_backed_example_truth_instances : "
            "ConcreteRegisteredEvidenceBackedExampleTruthInstances := {" in lean
            and "theorem concrete_registered_evidence_backed_example_truth_instances_exists :"
            in lean
            and "#check concrete_registered_evidence_backed_example_truth_instances"
            in lean
            and "#check concrete_registered_evidence_backed_example_truth_instances_exists"
            in lean
            and "#check concrete_registered_evidence_backed_example_4_truth_instance_atomic_sound"
            in lean
            and "exact concrete_registered_evidence_backed_example_truth_instances."
            "example_4_evidence_backed_truth_instance" in lean
            and "concrete_registered_evidence_backed_truth_conditions_imply_atomic_closure"
            in lean
        ),
        "coq concrete registered evidence-backed example truth instance package": (
            coq_concrete_registered_evidence_backed_example_truth_instance_atomic_sound_count
            == coq_example_count
            and "Record ConcreteRegisteredEvidenceBackedExampleTruthInstances : Type := {"
            in coq
            and "Definition concrete_registered_evidence_backed_example_truth_instances : "
            "ConcreteRegisteredEvidenceBackedExampleTruthInstances := {|" in coq
            and "Theorem concrete_registered_evidence_backed_example_truth_instances_exists :"
            in coq
            and "Check concrete_registered_evidence_backed_example_truth_instances."
            in coq
            and "Check concrete_registered_evidence_backed_example_truth_instances_exists."
            in coq
            and "Check concrete_registered_evidence_backed_example_4_truth_instance_atomic_sound."
            in coq
            and "exact (example_4_evidence_backed_truth_instance "
            "concrete_registered_evidence_backed_example_truth_instances)."
            in coq
            and "concrete_registered_evidence_backed_truth_conditions_imply_atomic_closure."
            in coq
        ),
        "lean concrete registered example truth instance atomic proofs": (
            lean_concrete_registered_example_truth_instance_atomic_sound_count
            == lean_example_count
            and "#check concrete_registered_example_4_truth_instance_atomic_sound"
            in lean
            and "exact concrete_registered_example_truth_instances."
            "example_4_concrete_truth_instance" in lean
            and "apply concrete_registered_truth_conditions_imply_atomic_closure"
            in lean
        ),
        "coq concrete registered example truth instance atomic proofs": (
            coq_concrete_registered_example_truth_instance_atomic_sound_count
            == coq_example_count
            and "Check concrete_registered_example_4_truth_instance_atomic_sound."
            in coq
            and "exact (example_4_concrete_truth_instance "
            "concrete_registered_example_truth_instances)." in coq
            and "apply concrete_registered_truth_conditions_imply_atomic_closure."
            in coq
        ),
        "lean concrete registered kernel example truth instance atomic proofs": (
            lean_concrete_registered_kernel_example_truth_instance_atomic_sound_count
            == lean_example_count
            and "#check concrete_registered_kernel_example_4_truth_instance_atomic_sound"
            in lean
            and "exact concrete_registered_kernel_example_truth_instances."
            "example_4_kernel_truth_instance" in lean
            and "concrete_registered_truth_conditions_from_kernel_imply_atomic_closure"
            in lean
        ),
        "coq concrete registered kernel example truth instance atomic proofs": (
            coq_concrete_registered_kernel_example_truth_instance_atomic_sound_count
            == coq_example_count
            and "Check concrete_registered_kernel_example_4_truth_instance_atomic_sound."
            in coq
            and "exact (example_4_kernel_truth_instance "
            "concrete_registered_kernel_example_truth_instances)." in coq
            and "concrete_registered_truth_conditions_from_kernel_imply_atomic_closure."
            in coq
        ),
        "lean concrete registered truth-condition route package": (
            lean_concrete_registered_route_direct_atomic_sound_count
            == lean_example_count
            and lean_concrete_registered_route_evidence_atomic_sound_count
            == lean_example_count
            and lean_concrete_registered_route_kernel_atomic_sound_count
            == lean_example_count
            and "structure ConcreteRegisteredTruthConditionRoute : Type where"
            in lean
            and "concrete_registered_route_direct_model : "
            "ConcreteRegisteredTruthConditionModel" in lean
            and "concrete_registered_route_evidence_sources : "
            "RegisteredEvidenceBackedTruthConditionSources" in lean
            and "concrete_registered_route_evidence_model : "
            "ConcreteRegisteredEvidenceBackedTruthConditionModel" in lean
            and "concrete_registered_route_kernel : ConcreteRegisteredTruthKernel"
            in lean
            and "def concrete_registered_truth_condition_route : "
            "ConcreteRegisteredTruthConditionRoute := {" in lean
            and "theorem concrete_registered_truth_condition_route_exists :"
            in lean
            and "theorem "
            "concrete_registered_truth_condition_route_direct_spec_matches_model :"
            in lean
            and "theorem "
            "concrete_registered_truth_condition_route_evidence_spec_matches_model :"
            in lean
            and "theorem "
            "concrete_registered_truth_condition_route_kernel_spec_matches_kernel :"
            in lean
            and "theorem concrete_registered_truth_condition_route_direct_spec_sound :"
            in lean
            and "theorem concrete_registered_truth_condition_route_evidence_spec_sound :"
            in lean
            and "theorem concrete_registered_truth_condition_route_kernel_spec_sound :"
            in lean
            and "#check concrete_registered_truth_condition_route" in lean
            and "#check concrete_registered_truth_condition_route_direct_spec_matches_model"
            in lean
            and "#check concrete_registered_truth_condition_route_example_4_direct_atomic_sound"
            in lean
            and "#check concrete_registered_truth_condition_route_example_4_evidence_atomic_sound"
            in lean
            and "#check concrete_registered_truth_condition_route_example_4_kernel_atomic_sound"
            in lean
        ),
        "coq concrete registered truth-condition route package": (
            coq_concrete_registered_route_direct_atomic_sound_count
            == coq_example_count
            and coq_concrete_registered_route_evidence_atomic_sound_count
            == coq_example_count
            and coq_concrete_registered_route_kernel_atomic_sound_count
            == coq_example_count
            and "Record ConcreteRegisteredTruthConditionRoute : Type := {"
            in coq
            and "concrete_registered_route_direct_model : "
            "ConcreteRegisteredTruthConditionModel;" in coq
            and "concrete_registered_route_evidence_sources : "
            "RegisteredEvidenceBackedTruthConditionSources;" in coq
            and "concrete_registered_route_evidence_model : "
            "ConcreteRegisteredEvidenceBackedTruthConditionModel;" in coq
            and "concrete_registered_route_kernel : ConcreteRegisteredTruthKernel;"
            in coq
            and "Definition concrete_registered_truth_condition_route :"
            in coq
            and "ConcreteRegisteredTruthConditionRoute := {|" in coq
            and "Theorem concrete_registered_truth_condition_route_exists :"
            in coq
            and "Theorem concrete_registered_truth_condition_route_direct_spec_matches_model :"
            in coq
            and "Theorem concrete_registered_truth_condition_route_evidence_spec_matches_model :"
            in coq
            and "Theorem concrete_registered_truth_condition_route_kernel_spec_matches_kernel :"
            in coq
            and "Theorem concrete_registered_truth_condition_route_direct_spec_sound :"
            in coq
            and "Theorem concrete_registered_truth_condition_route_evidence_spec_sound :"
            in coq
            and "Theorem concrete_registered_truth_condition_route_kernel_spec_sound :"
            in coq
            and "Check concrete_registered_truth_condition_route." in coq
            and "Check concrete_registered_truth_condition_route_direct_spec_matches_model."
            in coq
            and "Check concrete_registered_truth_condition_route_example_4_direct_atomic_sound."
            in coq
            and "Check concrete_registered_truth_condition_route_example_4_evidence_atomic_sound."
            in coq
            and "Check concrete_registered_truth_condition_route_example_4_kernel_atomic_sound."
            in coq
        ),
        "lean concrete registered truth-condition route example agreement package": (
            lean_concrete_registered_route_agreement_direct_atomic_sound_count
            == lean_example_count
            and lean_concrete_registered_route_agreement_evidence_atomic_sound_count
            == lean_example_count
            and lean_concrete_registered_route_agreement_kernel_atomic_sound_count
            == lean_example_count
            and "structure ConcreteRegisteredTruthConditionRouteExampleAgreement : "
            "Type where" in lean
            and "concrete_registered_route_agreement_route : "
            "ConcreteRegisteredTruthConditionRoute" in lean
            and "def concrete_registered_truth_condition_route_example_agreement : "
            "ConcreteRegisteredTruthConditionRouteExampleAgreement := {" in lean
            and "theorem "
            "concrete_registered_truth_condition_route_example_agreement_exists :"
            in lean
            and "theorem "
            "concrete_registered_truth_condition_route_example_agreement_route_matches :"
            in lean
            and "#check concrete_registered_truth_condition_route_example_agreement"
            in lean
            and "#check "
            "concrete_registered_truth_condition_route_example_agreement_route_matches"
            in lean
            and "#check "
            "concrete_registered_truth_condition_route_example_4_agreement_direct_atomic_sound"
            in lean
            and "#check "
            "concrete_registered_truth_condition_route_example_4_agreement_evidence_atomic_sound"
            in lean
            and "#check "
            "concrete_registered_truth_condition_route_example_4_agreement_kernel_atomic_sound"
            in lean
        ),
        "coq concrete registered truth-condition route example agreement package": (
            coq_concrete_registered_route_agreement_direct_atomic_sound_count
            == coq_example_count
            and coq_concrete_registered_route_agreement_evidence_atomic_sound_count
            == coq_example_count
            and coq_concrete_registered_route_agreement_kernel_atomic_sound_count
            == coq_example_count
            and "Record ConcreteRegisteredTruthConditionRouteExampleAgreement : Type := {"
            in coq
            and "concrete_registered_route_agreement_route : "
            "ConcreteRegisteredTruthConditionRoute;" in coq
            and "Definition concrete_registered_truth_condition_route_example_agreement :"
            in coq
            and "ConcreteRegisteredTruthConditionRouteExampleAgreement := {|"
            in coq
            and "Theorem concrete_registered_truth_condition_route_example_agreement_exists :"
            in coq
            and "Theorem "
            "concrete_registered_truth_condition_route_example_agreement_route_matches :"
            in coq
            and "Check concrete_registered_truth_condition_route_example_agreement."
            in coq
            and "Check "
            "concrete_registered_truth_condition_route_example_agreement_route_matches."
            in coq
            and "Check "
            "concrete_registered_truth_condition_route_example_4_agreement_direct_atomic_sound."
            in coq
            and "Check "
            "concrete_registered_truth_condition_route_example_4_agreement_evidence_atomic_sound."
            in coq
            and "Check "
            "concrete_registered_truth_condition_route_example_4_agreement_kernel_atomic_sound."
            in coq
        ),
        "lean independent registered truth-condition source package": (
            lean_independent_registered_truth_condition_source_atomic_sound_count
            == lean_example_count
            and "structure IndependentRegisteredTruthConditionSources : Type where"
            in lean
            and "independent_registered_truth_condition_route : "
            "ConcreteRegisteredTruthConditionRoute" in lean
            and "independent_registered_truth_condition_agreement : "
            "ConcreteRegisteredTruthConditionRouteExampleAgreement" in lean
            and "independent_registered_truth_condition_spec : "
            "FullyRegisteredTruthConditionSpec" in lean
            and "def independent_registered_truth_condition_sources : "
            "IndependentRegisteredTruthConditionSources := {" in lean
            and "theorem independent_registered_truth_condition_sources_exist :"
            in lean
            and "theorem "
            "independent_registered_truth_condition_sources_spec_matches_route :"
            in lean
            and "theorem "
            "independent_registered_truth_condition_sources_agreement_matches_route :"
            in lean
            and "theorem independent_registered_truth_condition_sources_spec_sound :"
            in lean
            and "#check IndependentRegisteredTruthConditionSources" in lean
            and "#check independent_registered_truth_condition_sources" in lean
            and "#check "
            "independent_registered_truth_condition_sources_spec_matches_route"
            in lean
            and "#check "
            "independent_registered_truth_condition_sources_agreement_matches_route"
            in lean
            and "#check independent_registered_truth_condition_sources_spec_sound"
            in lean
            and "#check independent_registered_truth_condition_sources_example_4_atomic_sound"
            in lean
        ),
        "coq independent registered truth-condition source package": (
            coq_independent_registered_truth_condition_source_atomic_sound_count
            == coq_example_count
            and "Record IndependentRegisteredTruthConditionSources : Type := {"
            in coq
            and "independent_registered_truth_condition_route : "
            "ConcreteRegisteredTruthConditionRoute;" in coq
            and "independent_registered_truth_condition_agreement : "
            "ConcreteRegisteredTruthConditionRouteExampleAgreement;" in coq
            and "independent_registered_truth_condition_spec : "
            "FullyRegisteredTruthConditionSpec;" in coq
            and "Definition independent_registered_truth_condition_sources :"
            in coq
            and "IndependentRegisteredTruthConditionSources := {|" in coq
            and "Theorem independent_registered_truth_condition_sources_exist :"
            in coq
            and "Theorem "
            "independent_registered_truth_condition_sources_spec_matches_route :"
            in coq
            and "Theorem "
            "independent_registered_truth_condition_sources_agreement_matches_route :"
            in coq
            and "Theorem independent_registered_truth_condition_sources_spec_sound :"
            in coq
            and "Check IndependentRegisteredTruthConditionSources." in coq
            and "Check independent_registered_truth_condition_sources." in coq
            and "Check "
            "independent_registered_truth_condition_sources_spec_matches_route."
            in coq
            and "Check "
            "independent_registered_truth_condition_sources_agreement_matches_route."
            in coq
            and "Check independent_registered_truth_condition_sources_spec_sound."
            in coq
            and "Check independent_registered_truth_condition_sources_example_4_atomic_sound."
            in coq
        ),
        "lean independent registered truth-condition clause instances package": (
            lean_independent_registered_truth_condition_clause_atomic_sound_count
            == lean_example_count
            and "structure IndependentRegisteredTruthConditionClauseInstances : Type where"
            in lean
            and "independent_registered_clause_source : "
            "IndependentRegisteredTruthConditionSources" in lean
            and "independent_registered_clause_spec : "
            "FullyRegisteredTruthConditionSpec" in lean
            and "def independent_registered_truth_condition_clause_instances : "
            "IndependentRegisteredTruthConditionClauseInstances := {" in lean
            and "theorem independent_registered_truth_condition_clause_instances_exists :"
            in lean
            and "theorem "
            "independent_registered_truth_condition_clause_spec_matches_source :"
            in lean
            and "theorem "
            "independent_registered_truth_condition_clause_lexical_application_instance :"
            in lean
            and "theorem "
            "independent_registered_truth_condition_clause_sigma_Entity_instance :"
            in lean
            and "theorem independent_registered_truth_condition_clause_repeat_instance :"
            in lean
            and "theorem independent_registered_truth_condition_clause_at_T_instance :"
            in lean
            and "theorem independent_registered_truth_condition_clause_not_T_instance :"
            in lean
            and "theorem "
            "independent_registered_truth_condition_clause_transition_instance :"
            in lean
            and "theorem independent_registered_truth_condition_clause_cause_instance :"
            in lean
            and "theorem independent_registered_truth_condition_clause_spec_sound :"
            in lean
            and "#check IndependentRegisteredTruthConditionClauseInstances"
            in lean
            and "#check "
            "independent_registered_truth_condition_clause_lexical_application_instance"
            in lean
            and "#check "
            "independent_registered_truth_condition_clause_sigma_Entity_instance"
            in lean
            and "#check independent_registered_truth_condition_clause_repeat_instance"
            in lean
            and "#check independent_registered_truth_condition_clause_transition_instance"
            in lean
            and "#check independent_registered_truth_condition_clause_example_4_atomic_sound"
            in lean
        ),
        "coq independent registered truth-condition clause instances package": (
            coq_independent_registered_truth_condition_clause_atomic_sound_count
            == coq_example_count
            and "Record IndependentRegisteredTruthConditionClauseInstances : Type := {"
            in coq
            and "independent_registered_clause_source : "
            "IndependentRegisteredTruthConditionSources;" in coq
            and "independent_registered_clause_spec : FullyRegisteredTruthConditionSpec;"
            in coq
            and "Definition independent_registered_truth_condition_clause_instances :"
            in coq
            and "IndependentRegisteredTruthConditionClauseInstances := {|" in coq
            and "Theorem independent_registered_truth_condition_clause_instances_exists :"
            in coq
            and "Theorem "
            "independent_registered_truth_condition_clause_spec_matches_source :"
            in coq
            and "Theorem "
            "independent_registered_truth_condition_clause_lexical_application_instance :"
            in coq
            and "Theorem "
            "independent_registered_truth_condition_clause_sigma_Entity_instance :"
            in coq
            and "Theorem independent_registered_truth_condition_clause_repeat_instance :"
            in coq
            and "Theorem independent_registered_truth_condition_clause_at_T_instance :"
            in coq
            and "Theorem independent_registered_truth_condition_clause_not_T_instance :"
            in coq
            and "Theorem "
            "independent_registered_truth_condition_clause_transition_instance :"
            in coq
            and "Theorem independent_registered_truth_condition_clause_cause_instance :"
            in coq
            and "Theorem independent_registered_truth_condition_clause_spec_sound :"
            in coq
            and "Check IndependentRegisteredTruthConditionClauseInstances." in coq
            and "Check "
            "independent_registered_truth_condition_clause_lexical_application_instance."
            in coq
            and "Check independent_registered_truth_condition_clause_sigma_Entity_instance."
            in coq
            and "Check independent_registered_truth_condition_clause_repeat_instance."
            in coq
            and "Check independent_registered_truth_condition_clause_transition_instance."
            in coq
            and "Check independent_registered_truth_condition_clause_example_4_atomic_sound."
            in coq
        ),
        "lean independent registered truth-condition clause coverage package": (
            lean_independent_registered_truth_condition_clause_coverage_atomic_sound_count
            == lean_example_count
            and "structure IndependentRegisteredTruthConditionClauseCoverage : Type where"
            in lean
            and "independent_registered_clause_coverage_instances :"
            in lean
            and "IndependentRegisteredTruthConditionClauseInstances" in lean
            and "def independent_registered_truth_condition_clause_coverage :"
            in lean
            and "IndependentRegisteredTruthConditionClauseCoverage := {"
            in lean
            and "theorem independent_registered_truth_condition_clause_coverage_exists :"
            in lean
            and "theorem "
            "independent_registered_truth_condition_clause_coverage_instances_match :"
            in lean
            and "theorem "
            "independent_registered_truth_condition_clause_coverage_spec_sound :"
            in lean
            and "theorem "
            "independent_registered_truth_condition_clause_coverage_example_4_atomic_sound :"
            in lean
            and "#check IndependentRegisteredTruthConditionClauseCoverage"
            in lean
            and "#check independent_registered_truth_condition_clause_coverage"
            in lean
            and "#check "
            "independent_registered_truth_condition_clause_coverage_instances_match"
            in lean
            and "#check "
            "independent_registered_truth_condition_clause_coverage_spec_sound"
            in lean
            and "#check "
            "independent_registered_truth_condition_clause_coverage_example_4_atomic_sound"
            in lean
        ),
        "coq independent registered truth-condition clause coverage package": (
            coq_independent_registered_truth_condition_clause_coverage_atomic_sound_count
            == coq_example_count
            and "Record IndependentRegisteredTruthConditionClauseCoverage : Type := {"
            in coq
            and "independent_registered_clause_coverage_instances :" in coq
            and "IndependentRegisteredTruthConditionClauseInstances" in coq
            and "Definition independent_registered_truth_condition_clause_coverage :"
            in coq
            and "IndependentRegisteredTruthConditionClauseCoverage := {|"
            in coq
            and "Theorem independent_registered_truth_condition_clause_coverage_exists :"
            in coq
            and "Theorem "
            "independent_registered_truth_condition_clause_coverage_instances_match :"
            in coq
            and "Theorem "
            "independent_registered_truth_condition_clause_coverage_spec_sound :"
            in coq
            and "Theorem "
            "independent_registered_truth_condition_clause_coverage_example_4_atomic_sound :"
            in coq
            and "Check IndependentRegisteredTruthConditionClauseCoverage." in coq
            and "Check independent_registered_truth_condition_clause_coverage."
            in coq
            and "Check "
            "independent_registered_truth_condition_clause_coverage_instances_match."
            in coq
            and "Check "
            "independent_registered_truth_condition_clause_coverage_spec_sound."
            in coq
            and "Check "
            "independent_registered_truth_condition_clause_coverage_example_4_atomic_sound."
            in coq
        ),
        "lean independent registered lexical truth-condition instances package": (
            "structure IndependentRegisteredLexicalTruthConditionInstances : Type where"
            in lean
            and "independent_registered_lexical_clause_coverage :" in lean
            and "IndependentRegisteredTruthConditionClauseCoverage" in lean
            and "def independent_registered_lexical_truth_condition_instances :"
            in lean
            and "IndependentRegisteredLexicalTruthConditionInstances := {"
            in lean
            and "theorem "
            "independent_registered_lexical_truth_condition_instances_exists :"
            in lean
            and "theorem "
            "independent_registered_lexical_truth_condition_coverage_matches :"
            in lean
            and "theorem "
            "independent_registered_lexical_truth_condition_application_instance :"
            in lean
            and "RegisteredLexicalApplicationTruth A term ->" in lean
            and "theorem independent_registered_lexical_truth_condition_spec_sound :"
            in lean
            and "#check IndependentRegisteredLexicalTruthConditionInstances"
            in lean
            and "#check independent_registered_lexical_truth_condition_instances"
            in lean
            and "#check independent_registered_lexical_truth_condition_coverage_matches"
            in lean
            and "#check independent_registered_lexical_truth_condition_application_instance"
            in lean
            and "#check independent_registered_lexical_truth_condition_spec_sound"
            in lean
        ),
        "coq independent registered lexical truth-condition instances package": (
            "Record IndependentRegisteredLexicalTruthConditionInstances : Type := {"
            in coq
            and "independent_registered_lexical_clause_coverage :" in coq
            and "IndependentRegisteredTruthConditionClauseCoverage" in coq
            and "Definition independent_registered_lexical_truth_condition_instances :"
            in coq
            and "IndependentRegisteredLexicalTruthConditionInstances := {|"
            in coq
            and "Theorem "
            "independent_registered_lexical_truth_condition_instances_exists :"
            in coq
            and "Theorem "
            "independent_registered_lexical_truth_condition_coverage_matches :"
            in coq
            and "Theorem "
            "independent_registered_lexical_truth_condition_application_instance :"
            in coq
            and "RegisteredLexicalApplicationTruth A term ->" in coq
            and "Theorem independent_registered_lexical_truth_condition_spec_sound :"
            in coq
            and "Check IndependentRegisteredLexicalTruthConditionInstances."
            in coq
            and "Check independent_registered_lexical_truth_condition_instances."
            in coq
            and "Check independent_registered_lexical_truth_condition_coverage_matches."
            in coq
            and "Check independent_registered_lexical_truth_condition_application_instance."
            in coq
            and "Check independent_registered_lexical_truth_condition_spec_sound."
            in coq
        ),
        "lean independent registered temporal truth-condition instances package": (
            "structure IndependentRegisteredTemporalTruthConditionInstances : Type where"
            in lean
            and "independent_registered_temporal_clause_coverage :"
            in lean
            and "IndependentRegisteredTruthConditionClauseCoverage" in lean
            and "def independent_registered_temporal_truth_condition_instances :"
            in lean
            and "IndependentRegisteredTemporalTruthConditionInstances := {"
            in lean
            and "theorem "
            "independent_registered_temporal_truth_condition_instances_exists :"
            in lean
            and "theorem "
            "independent_registered_temporal_truth_condition_coverage_matches :"
            in lean
            and "theorem "
            "independent_registered_temporal_truth_condition_at_T_instance :"
            in lean
            and "theorem "
            "independent_registered_temporal_truth_condition_during_T_instance :"
            in lean
            and "theorem "
            "independent_registered_temporal_truth_condition_before_T_instance :"
            in lean
            and "theorem "
            "independent_registered_temporal_truth_condition_after_T_instance :"
            in lean
            and "theorem "
            "independent_registered_temporal_truth_condition_until_T_instance :"
            in lean
            and "theorem "
            "independent_registered_temporal_truth_condition_since_T_instance :"
            in lean
            and "theorem "
            "independent_registered_temporal_truth_condition_spec_sound :"
            in lean
            and "#check IndependentRegisteredTemporalTruthConditionInstances"
            in lean
            and "#check independent_registered_temporal_truth_condition_instances"
            in lean
            and "#check "
            "independent_registered_temporal_truth_condition_coverage_matches"
            in lean
            and "#check "
            "independent_registered_temporal_truth_condition_at_T_instance"
            in lean
            and "#check "
            "independent_registered_temporal_truth_condition_since_T_instance"
            in lean
            and "#check independent_registered_temporal_truth_condition_spec_sound"
            in lean
        ),
        "coq independent registered temporal truth-condition instances package": (
            "Record IndependentRegisteredTemporalTruthConditionInstances : Type := {"
            in coq
            and "independent_registered_temporal_clause_coverage :" in coq
            and "IndependentRegisteredTruthConditionClauseCoverage" in coq
            and "Definition independent_registered_temporal_truth_condition_instances :"
            in coq
            and "IndependentRegisteredTemporalTruthConditionInstances := {|"
            in coq
            and "Theorem "
            "independent_registered_temporal_truth_condition_instances_exists :"
            in coq
            and "Theorem "
            "independent_registered_temporal_truth_condition_coverage_matches :"
            in coq
            and "Theorem "
            "independent_registered_temporal_truth_condition_at_T_instance :"
            in coq
            and "Theorem "
            "independent_registered_temporal_truth_condition_during_T_instance :"
            in coq
            and "Theorem "
            "independent_registered_temporal_truth_condition_before_T_instance :"
            in coq
            and "Theorem "
            "independent_registered_temporal_truth_condition_after_T_instance :"
            in coq
            and "Theorem "
            "independent_registered_temporal_truth_condition_until_T_instance :"
            in coq
            and "Theorem "
            "independent_registered_temporal_truth_condition_since_T_instance :"
            in coq
            and "Theorem independent_registered_temporal_truth_condition_spec_sound :"
            in coq
            and "Check IndependentRegisteredTemporalTruthConditionInstances."
            in coq
            and "Check independent_registered_temporal_truth_condition_instances."
            in coq
            and "Check independent_registered_temporal_truth_condition_coverage_matches."
            in coq
            and "Check independent_registered_temporal_truth_condition_at_T_instance."
            in coq
            and "Check independent_registered_temporal_truth_condition_since_T_instance."
            in coq
            and "Check independent_registered_temporal_truth_condition_spec_sound."
            in coq
        ),
        "lean independent registered sigma truth-condition instances package": (
            "structure IndependentRegisteredSigmaTruthConditionInstances : Type where"
            in lean
            and "independent_registered_sigma_clause_coverage :"
            in lean
            and "IndependentRegisteredTruthConditionClauseCoverage" in lean
            and "def independent_registered_sigma_truth_condition_instances :"
            in lean
            and "IndependentRegisteredSigmaTruthConditionInstances := {"
            in lean
            and "theorem "
            "independent_registered_sigma_truth_condition_instances_exists :"
            in lean
            and "theorem "
            "independent_registered_sigma_truth_condition_coverage_matches :"
            in lean
            and "theorem "
            "independent_registered_sigma_truth_condition_sigma_Entity_instance :"
            in lean
            and "theorem independent_registered_sigma_truth_condition_spec_sound :"
            in lean
            and "#check IndependentRegisteredSigmaTruthConditionInstances"
            in lean
            and "#check independent_registered_sigma_truth_condition_instances"
            in lean
            and "#check independent_registered_sigma_truth_condition_coverage_matches"
            in lean
            and "#check "
            "independent_registered_sigma_truth_condition_sigma_Entity_instance"
            in lean
            and "#check independent_registered_sigma_truth_condition_spec_sound"
            in lean
        ),
        "coq independent registered sigma truth-condition instances package": (
            "Record IndependentRegisteredSigmaTruthConditionInstances : Type := {"
            in coq
            and "independent_registered_sigma_clause_coverage :" in coq
            and "IndependentRegisteredTruthConditionClauseCoverage" in coq
            and "Definition independent_registered_sigma_truth_condition_instances :"
            in coq
            and "IndependentRegisteredSigmaTruthConditionInstances := {|"
            in coq
            and "Theorem "
            "independent_registered_sigma_truth_condition_instances_exists :"
            in coq
            and "Theorem "
            "independent_registered_sigma_truth_condition_coverage_matches :"
            in coq
            and "Theorem "
            "independent_registered_sigma_truth_condition_sigma_Entity_instance :"
            in coq
            and "Theorem independent_registered_sigma_truth_condition_spec_sound :"
            in coq
            and "Check IndependentRegisteredSigmaTruthConditionInstances."
            in coq
            and "Check independent_registered_sigma_truth_condition_instances."
            in coq
            and "Check independent_registered_sigma_truth_condition_coverage_matches."
            in coq
            and "Check "
            "independent_registered_sigma_truth_condition_sigma_Entity_instance."
            in coq
            and "Check independent_registered_sigma_truth_condition_spec_sound."
            in coq
        ),
        "lean independent registered repeat truth-condition instances package": (
            "structure IndependentRegisteredRepeatTruthConditionInstances : Type where"
            in lean
            and "independent_registered_repeat_clause_coverage :"
            in lean
            and "IndependentRegisteredTruthConditionClauseCoverage" in lean
            and "def independent_registered_repeat_truth_condition_instances :"
            in lean
            and "IndependentRegisteredRepeatTruthConditionInstances := {"
            in lean
            and "theorem "
            "independent_registered_repeat_truth_condition_instances_exists :"
            in lean
            and "theorem "
            "independent_registered_repeat_truth_condition_coverage_matches :"
            in lean
            and "theorem independent_registered_repeat_truth_condition_repeat_instance :"
            in lean
            and "theorem independent_registered_repeat_truth_condition_spec_sound :"
            in lean
            and "#check IndependentRegisteredRepeatTruthConditionInstances"
            in lean
            and "#check independent_registered_repeat_truth_condition_instances"
            in lean
            and "#check independent_registered_repeat_truth_condition_coverage_matches"
            in lean
            and "#check independent_registered_repeat_truth_condition_repeat_instance"
            in lean
            and "#check independent_registered_repeat_truth_condition_spec_sound"
            in lean
        ),
        "coq independent registered repeat truth-condition instances package": (
            "Record IndependentRegisteredRepeatTruthConditionInstances : Type := {"
            in coq
            and "independent_registered_repeat_clause_coverage :" in coq
            and "IndependentRegisteredTruthConditionClauseCoverage" in coq
            and "Definition independent_registered_repeat_truth_condition_instances :"
            in coq
            and "IndependentRegisteredRepeatTruthConditionInstances := {|"
            in coq
            and "Theorem "
            "independent_registered_repeat_truth_condition_instances_exists :"
            in coq
            and "Theorem "
            "independent_registered_repeat_truth_condition_coverage_matches :"
            in coq
            and "Theorem independent_registered_repeat_truth_condition_repeat_instance :"
            in coq
            and "Theorem independent_registered_repeat_truth_condition_spec_sound :"
            in coq
            and "Check IndependentRegisteredRepeatTruthConditionInstances."
            in coq
            and "Check independent_registered_repeat_truth_condition_instances."
            in coq
            and "Check independent_registered_repeat_truth_condition_coverage_matches."
            in coq
            and "Check independent_registered_repeat_truth_condition_repeat_instance."
            in coq
            and "Check independent_registered_repeat_truth_condition_spec_sound."
            in coq
        ),
        "lean independent registered polarity truth-condition instances package": (
            "structure IndependentRegisteredPolarityTruthConditionInstances : Type where"
            in lean
            and "independent_registered_polarity_clause_coverage :"
            in lean
            and "IndependentRegisteredTruthConditionClauseCoverage" in lean
            and "def independent_registered_polarity_truth_condition_instances :"
            in lean
            and "IndependentRegisteredPolarityTruthConditionInstances := {"
            in lean
            and "theorem "
            "independent_registered_polarity_truth_condition_instances_exists :"
            in lean
            and "theorem "
            "independent_registered_polarity_truth_condition_coverage_matches :"
            in lean
            and "theorem independent_registered_polarity_truth_condition_not_T_instance :"
            in lean
            and "theorem independent_registered_polarity_truth_condition_spec_sound :"
            in lean
            and "#check IndependentRegisteredPolarityTruthConditionInstances"
            in lean
            and "#check independent_registered_polarity_truth_condition_instances"
            in lean
            and "#check independent_registered_polarity_truth_condition_coverage_matches"
            in lean
            and "#check independent_registered_polarity_truth_condition_not_T_instance"
            in lean
            and "#check independent_registered_polarity_truth_condition_spec_sound"
            in lean
        ),
        "coq independent registered polarity truth-condition instances package": (
            "Record IndependentRegisteredPolarityTruthConditionInstances : Type := {"
            in coq
            and "independent_registered_polarity_clause_coverage :" in coq
            and "IndependentRegisteredTruthConditionClauseCoverage" in coq
            and "Definition independent_registered_polarity_truth_condition_instances :"
            in coq
            and "IndependentRegisteredPolarityTruthConditionInstances := {|"
            in coq
            and "Theorem "
            "independent_registered_polarity_truth_condition_instances_exists :"
            in coq
            and "Theorem "
            "independent_registered_polarity_truth_condition_coverage_matches :"
            in coq
            and "Theorem independent_registered_polarity_truth_condition_not_T_instance :"
            in coq
            and "Theorem independent_registered_polarity_truth_condition_spec_sound :"
            in coq
            and "Check IndependentRegisteredPolarityTruthConditionInstances."
            in coq
            and "Check independent_registered_polarity_truth_condition_instances."
            in coq
            and "Check independent_registered_polarity_truth_condition_coverage_matches."
            in coq
            and "Check independent_registered_polarity_truth_condition_not_T_instance."
            in coq
            and "Check independent_registered_polarity_truth_condition_spec_sound."
            in coq
        ),
        "lean independent registered transition-cause truth-condition instances package": (
            "structure IndependentRegisteredTransitionCauseTruthConditionInstances : Type where"
            in lean
            and "independent_registered_transition_cause_clause_coverage :"
            in lean
            and "IndependentRegisteredTruthConditionClauseCoverage" in lean
            and "def independent_registered_transition_cause_truth_condition_instances :"
            in lean
            and "IndependentRegisteredTransitionCauseTruthConditionInstances := {"
            in lean
            and "theorem "
            "independent_registered_transition_cause_truth_condition_instances_exists :"
            in lean
            and "theorem "
            "independent_registered_transition_cause_truth_condition_coverage_matches :"
            in lean
            and "theorem "
            "independent_registered_transition_cause_truth_condition_transition_instance :"
            in lean
            and "theorem "
            "independent_registered_transition_cause_truth_condition_cause_instance :"
            in lean
            and "theorem "
            "independent_registered_transition_cause_truth_condition_spec_sound :"
            in lean
            and "#check IndependentRegisteredTransitionCauseTruthConditionInstances"
            in lean
            and "#check independent_registered_transition_cause_truth_condition_instances"
            in lean
            and "#check "
            "independent_registered_transition_cause_truth_condition_coverage_matches"
            in lean
            and "#check "
            "independent_registered_transition_cause_truth_condition_transition_instance"
            in lean
            and "#check "
            "independent_registered_transition_cause_truth_condition_cause_instance"
            in lean
            and "#check "
            "independent_registered_transition_cause_truth_condition_spec_sound"
            in lean
        ),
        "coq independent registered transition-cause truth-condition instances package": (
            "Record IndependentRegisteredTransitionCauseTruthConditionInstances : Type := {"
            in coq
            and "independent_registered_transition_cause_clause_coverage :" in coq
            and "IndependentRegisteredTruthConditionClauseCoverage" in coq
            and "Definition "
            "independent_registered_transition_cause_truth_condition_instances :"
            in coq
            and "IndependentRegisteredTransitionCauseTruthConditionInstances := {|"
            in coq
            and "Theorem "
            "independent_registered_transition_cause_truth_condition_instances_exists :"
            in coq
            and "Theorem "
            "independent_registered_transition_cause_truth_condition_coverage_matches :"
            in coq
            and "Theorem "
            "independent_registered_transition_cause_truth_condition_transition_instance :"
            in coq
            and "Theorem "
            "independent_registered_transition_cause_truth_condition_cause_instance :"
            in coq
            and "Theorem "
            "independent_registered_transition_cause_truth_condition_spec_sound :"
            in coq
            and "Check IndependentRegisteredTransitionCauseTruthConditionInstances."
            in coq
            and "Check independent_registered_transition_cause_truth_condition_instances."
            in coq
            and "Check "
            "independent_registered_transition_cause_truth_condition_coverage_matches."
            in coq
            and "Check "
            "independent_registered_transition_cause_truth_condition_transition_instance."
            in coq
            and "Check "
            "independent_registered_transition_cause_truth_condition_cause_instance."
            in coq
            and "Check independent_registered_transition_cause_truth_condition_spec_sound."
            in coq
        ),
        "lean independent registered truth-condition instance suite package": (
            "structure IndependentRegisteredTruthConditionInstanceSuite : Type where"
            in lean
            and "independent_registered_suite_lexical :" in lean
            and "IndependentRegisteredLexicalTruthConditionInstances" in lean
            and "independent_registered_suite_temporal :" in lean
            and "IndependentRegisteredTemporalTruthConditionInstances" in lean
            and "independent_registered_suite_sigma :" in lean
            and "IndependentRegisteredSigmaTruthConditionInstances" in lean
            and "independent_registered_suite_repeat :" in lean
            and "IndependentRegisteredRepeatTruthConditionInstances" in lean
            and "independent_registered_suite_polarity :" in lean
            and "IndependentRegisteredPolarityTruthConditionInstances" in lean
            and "independent_registered_suite_transition_cause :" in lean
            and "IndependentRegisteredTransitionCauseTruthConditionInstances" in lean
            and "def independent_registered_truth_condition_instance_suite :"
            in lean
            and "theorem independent_registered_truth_condition_instance_suite_exists :"
            in lean
            and "theorem "
            "independent_registered_truth_condition_instance_suite_lexical_matches :"
            in lean
            and "theorem "
            "independent_registered_truth_condition_instance_suite_temporal_matches :"
            in lean
            and "theorem "
            "independent_registered_truth_condition_instance_suite_sigma_matches :"
            in lean
            and "theorem "
            "independent_registered_truth_condition_instance_suite_repeat_matches :"
            in lean
            and "theorem "
            "independent_registered_truth_condition_instance_suite_polarity_matches :"
            in lean
            and "theorem "
            "independent_registered_truth_condition_instance_suite_transition_cause_matches :"
            in lean
            and "theorem "
            "independent_registered_truth_condition_instance_suite_spec_sound :"
            in lean
            and "#check IndependentRegisteredTruthConditionInstanceSuite" in lean
            and "#check independent_registered_truth_condition_instance_suite"
            in lean
            and "#check "
            "independent_registered_truth_condition_instance_suite_lexical_matches"
            in lean
            and "#check "
            "independent_registered_truth_condition_instance_suite_transition_cause_matches"
            in lean
            and "#check "
            "independent_registered_truth_condition_instance_suite_spec_sound"
            in lean
        ),
        "coq independent registered truth-condition instance suite package": (
            "Record IndependentRegisteredTruthConditionInstanceSuite : Type := {"
            in coq
            and "independent_registered_suite_lexical :" in coq
            and "IndependentRegisteredLexicalTruthConditionInstances" in coq
            and "independent_registered_suite_temporal :" in coq
            and "IndependentRegisteredTemporalTruthConditionInstances" in coq
            and "independent_registered_suite_sigma :" in coq
            and "IndependentRegisteredSigmaTruthConditionInstances" in coq
            and "independent_registered_suite_repeat :" in coq
            and "IndependentRegisteredRepeatTruthConditionInstances" in coq
            and "independent_registered_suite_polarity :" in coq
            and "IndependentRegisteredPolarityTruthConditionInstances" in coq
            and "independent_registered_suite_transition_cause :" in coq
            and "IndependentRegisteredTransitionCauseTruthConditionInstances" in coq
            and "Definition independent_registered_truth_condition_instance_suite :"
            in coq
            and "Theorem independent_registered_truth_condition_instance_suite_exists :"
            in coq
            and "Theorem "
            "independent_registered_truth_condition_instance_suite_lexical_matches :"
            in coq
            and "Theorem "
            "independent_registered_truth_condition_instance_suite_temporal_matches :"
            in coq
            and "Theorem "
            "independent_registered_truth_condition_instance_suite_sigma_matches :"
            in coq
            and "Theorem "
            "independent_registered_truth_condition_instance_suite_repeat_matches :"
            in coq
            and "Theorem "
            "independent_registered_truth_condition_instance_suite_polarity_matches :"
            in coq
            and "Theorem "
            "independent_registered_truth_condition_instance_suite_transition_cause_matches :"
            in coq
            and "Theorem "
            "independent_registered_truth_condition_instance_suite_spec_sound :"
            in coq
            and "Check IndependentRegisteredTruthConditionInstanceSuite." in coq
            and "Check independent_registered_truth_condition_instance_suite."
            in coq
            and "Check "
            "independent_registered_truth_condition_instance_suite_lexical_matches."
            in coq
            and "Check "
            "independent_registered_truth_condition_instance_suite_transition_cause_matches."
            in coq
            and "Check independent_registered_truth_condition_instance_suite_spec_sound."
            in coq
        ),
        "lean independent registered truth-condition suite example package": (
            lean_independent_registered_truth_condition_suite_example_atomic_sound_count
            == lean_example_count
            and "structure "
            "IndependentRegisteredTruthConditionInstanceSuiteExamplePackage : "
            "Type where"
            in lean
            and "independent_registered_suite_example_suite :" in lean
            and "IndependentRegisteredTruthConditionInstanceSuite" in lean
            and "def "
            "independent_registered_truth_condition_instance_suite_example_package :"
            in lean
            and "theorem "
            "independent_registered_truth_condition_instance_suite_example_package_exists :"
            in lean
            and "theorem "
            "independent_registered_truth_condition_instance_suite_example_package_suite_matches :"
            in lean
            and "theorem "
            "independent_registered_truth_condition_instance_suite_example_4_atomic_sound :"
            in lean
            and "independent_registered_truth_condition_clause_coverage_example_4_atomic_sound"
            in lean
            and "#check IndependentRegisteredTruthConditionInstanceSuiteExamplePackage"
            in lean
            and "#check "
            "independent_registered_truth_condition_instance_suite_example_package"
            in lean
            and "#check "
            "independent_registered_truth_condition_instance_suite_example_4_atomic_sound"
            in lean
        ),
        "coq independent registered truth-condition suite example package": (
            coq_independent_registered_truth_condition_suite_example_atomic_sound_count
            == coq_example_count
            and "Record "
            "IndependentRegisteredTruthConditionInstanceSuiteExamplePackage : "
            "Type := {"
            in coq
            and "independent_registered_suite_example_suite :" in coq
            and "IndependentRegisteredTruthConditionInstanceSuite" in coq
            and "Definition "
            "independent_registered_truth_condition_instance_suite_example_package :"
            in coq
            and "Theorem "
            "independent_registered_truth_condition_instance_suite_example_package_exists :"
            in coq
            and "Theorem "
            "independent_registered_truth_condition_instance_suite_example_package_suite_matches :"
            in coq
            and "Theorem "
            "independent_registered_truth_condition_instance_suite_example_4_atomic_sound :"
            in coq
            and "independent_registered_truth_condition_clause_coverage_example_4_atomic_sound"
            in coq
            and "Check IndependentRegisteredTruthConditionInstanceSuiteExamplePackage."
            in coq
            and "Check "
            "independent_registered_truth_condition_instance_suite_example_package."
            in coq
            and "Check "
            "independent_registered_truth_condition_instance_suite_example_4_atomic_sound."
            in coq
        ),
        "lean syntax-directed truth kernel soundness proofs": (
            lean_syntax_directed_truth_kernel_sound_count == lean_example_count
            and "#check example_4_syntax_directed_truth_kernel_sound" in lean
            and "apply syntax_directed_truth_kernel_denotes_syntax_directed_truth"
            in lean
        ),
        "coq syntax-directed truth kernel soundness proofs": (
            coq_syntax_directed_truth_kernel_sound_count == coq_example_count
            and "Check example_4_syntax_directed_truth_kernel_sound." in coq
            and "apply syntax_directed_truth_kernel_denotes_syntax_directed_truth."
            in coq
        ),
        "lean semantic preservation obligation checks": (
            "#check example_4_semantic_preservation_obligation" in lean
            and "#check example_4_semantic_preservation_obligation_record" in lean
            and "#check example_4_semantic_preservation_obligation_is_prop" in lean
            and "#check example_4_semantic_preservation_target_matches" in lean
            and "#check example_4_semantic_preservation_proved" in lean
            and "#check example_4_model_interpretable" in lean
            and "#check example_4_syntax_directed_truth" in lean
            and "#check example_4_denotationally_sound" in lean
            and "#check example_4_truth_condition_sound" in lean
            and "#check example_4_tautological_truth_condition_sound" in lean
            and "#check example_4_structural_truth_condition_sound" in lean
            and "#check example_4_concrete_kernel_truth_condition_sound" in lean
            and "#check example_4_model_interpretable_truth_kernel_sound" in lean
            and "#check example_4_syntax_directed_truth_kernel_sound" in lean
            and "#check example_4_primitive_truth_kernel_sound" in lean
            and "#check example_4_atomic_closure_truth" in lean
            and "#check example_4_atomic_closure_truth_kernel_sound" in lean
            and "#check example_4_atomic_closure_evidence_backed_truth_condition_sound"
            in lean
            and "#check example_4_fully_registered_atomic_closure_truth" in lean
            and "#check example_4_fully_registered_truth_condition_sound" in lean
            and "#check example_4_registered_lexical_truth_model_sound" in lean
            and "#check example_4_registered_lexical_truth_conditions_from_model_sound"
            in lean
            and "#check example_4_concrete_registered_truth" in lean
            and "#check example_4_concrete_registered_truth_kernel_sound"
            in lean
            and "#check example_4_concrete_registered_truth_conditions_from_kernel_sound"
            in lean
            and "#check example_4_concrete_registered_truth_conditions_from_kernel_atomic_sound"
            in lean
            and "#check example_4_concrete_registered_truth_condition_sound"
            in lean
            and "#check example_4_concrete_registered_truth_condition_atomic_sound"
            in lean
            and "#check concrete_registered_kernel_example_4_truth_instance_atomic_sound"
            in lean
            and "#check example_4_fully_registered_truth_condition_atomic_sound" in lean
            and "#check registered_example_4_truth_instance_atomic_sound" in lean
            and "#check registered_lexical_truth_model" in lean
            and "#check registered_lexical_truth_conditions_from_model" in lean
            and "#check concrete_registered_truth_basis" in lean
            and "#check concrete_registered_truth_conditions" in lean
            and "#check concrete_registered_truth_kernel" in lean
            and "#check concrete_registered_truth_conditions_from_kernel" in lean
            and "#check concrete_registered_kernel_example_truth_instances" in lean
            and "#check registered_example_truth_instances" in lean
            and "#check independent_truth_condition_obligation_ledger" in lean
            and "#check independent_truth_condition_obligation_ledger_truth_conditions_sound"
            in lean
            and "#check TruthEvidence" in lean
            and "#check truth_evidence_sound" in lean
            and "#check truth_evidence_intro" in lean
            and "#check EvidenceBackedTruthConditionSources" in lean
            and "#check concrete_kernel_from_evidence_sources" in lean
            and "#check evidence_backed_truth_condition_ledger" in lean
            and "#check evidence_backed_truth_condition_sources_induce_kernel"
            in lean
            and "#check evidence_backed_truth_condition_sources_induce_truth_conditions"
            in lean
            and "#check evidence_backed_truth_condition_sources_sound" in lean
            and "#check atomic_closure_evidence_backed_truth_sources" in lean
            and "#check atomic_closure_evidence_backed_truth_kernel" in lean
            and "#check atomic_closure_evidence_backed_truth_ledger" in lean
            and "#check atomic_closure_evidence_backed_truth_sources_sound"
            in lean
        ),
        "coq semantic preservation obligation checks": (
            "Check example_4_semantic_preservation_obligation." in coq
            and "Check example_4_semantic_preservation_obligation_record." in coq
            and "Check example_4_semantic_preservation_obligation_is_prop." in coq
            and "Check example_4_semantic_preservation_target_matches." in coq
            and "Check example_4_semantic_preservation_proved." in coq
            and "Check example_4_model_interpretable." in coq
            and "Check example_4_syntax_directed_truth." in coq
            and "Check example_4_denotationally_sound." in coq
            and "Check example_4_truth_condition_sound." in coq
            and "Check example_4_tautological_truth_condition_sound." in coq
            and "Check example_4_structural_truth_condition_sound." in coq
            and "Check example_4_concrete_kernel_truth_condition_sound." in coq
            and "Check example_4_model_interpretable_truth_kernel_sound." in coq
            and "Check example_4_syntax_directed_truth_kernel_sound." in coq
            and "Check example_4_primitive_truth_kernel_sound." in coq
            and "Check example_4_atomic_closure_truth." in coq
            and "Check example_4_atomic_closure_truth_kernel_sound." in coq
            and "Check example_4_atomic_closure_evidence_backed_truth_condition_sound."
            in coq
            and "Check example_4_fully_registered_atomic_closure_truth." in coq
            and "Check example_4_fully_registered_truth_condition_sound." in coq
            and "Check example_4_registered_lexical_truth_model_sound." in coq
            and "Check example_4_registered_lexical_truth_conditions_from_model_sound."
            in coq
            and "Check example_4_concrete_registered_truth." in coq
            and "Check example_4_concrete_registered_truth_kernel_sound." in coq
            and "Check example_4_concrete_registered_truth_conditions_from_kernel_sound."
            in coq
            and "Check example_4_concrete_registered_truth_conditions_from_kernel_atomic_sound."
            in coq
            and "Check example_4_concrete_registered_truth_condition_sound."
            in coq
            and "Check example_4_concrete_registered_truth_condition_atomic_sound."
            in coq
            and "Check concrete_registered_kernel_example_4_truth_instance_atomic_sound."
            in coq
            and "Check example_4_fully_registered_truth_condition_atomic_sound." in coq
            and "Check registered_example_4_truth_instance_atomic_sound." in coq
            and "Check registered_lexical_truth_model." in coq
            and "Check registered_lexical_truth_conditions_from_model." in coq
            and "Check concrete_registered_truth_basis." in coq
            and "Check concrete_registered_truth_conditions." in coq
            and "Check concrete_registered_truth_kernel." in coq
            and "Check concrete_registered_truth_conditions_from_kernel." in coq
            and "Check concrete_registered_kernel_example_truth_instances." in coq
            and "Check registered_example_truth_instances." in coq
            and "Check independent_truth_condition_obligation_ledger." in coq
            and "Check independent_truth_condition_obligation_ledger_truth_conditions_sound."
            in coq
            and "Check TruthEvidence." in coq
            and "Check truth_evidence_sound." in coq
            and "Check truth_evidence_intro." in coq
            and "Check EvidenceBackedTruthConditionSources." in coq
            and "Check concrete_kernel_from_evidence_sources." in coq
            and "Check evidence_backed_truth_condition_ledger." in coq
            and "Check evidence_backed_truth_condition_sources_induce_kernel."
            in coq
            and "Check evidence_backed_truth_condition_sources_induce_truth_conditions."
            in coq
            and "Check evidence_backed_truth_condition_sources_sound." in coq
            and "Check atomic_closure_evidence_backed_truth_sources." in coq
            and "Check atomic_closure_evidence_backed_truth_kernel." in coq
            and "Check atomic_closure_evidence_backed_truth_ledger." in coq
            and "Check atomic_closure_evidence_backed_truth_sources_sound." in coq
        ),
        "lean transition state-scale signature": (
            "constant Transition : Entity -> StateScale -> State -> State -> TransitionT"
            in lean
        ),
        "coq transition state-scale signature": (
            "Parameter Transition : Entity -> StateScale -> State -> State -> TransitionT."
            in coq
        ),
        "lean result scale": "constant integrity_scale : StateScale" in lean,
        "coq result scale": "Parameter integrity_scale : StateScale." in coq,
        "lean result states": "constant intact : State" in lean
        and "constant broken : State" in lean,
        "coq result states": "Parameter intact : State." in coq
        and "Parameter broken : State." in coq,
        "lean inferred source state": (
            "Transition vase integrity_scale intact broken" in lean
        ),
        "coq inferred source state": (
            "Transition vase integrity_scale intact broken" in coq
        ),
        "no raw transition placeholder": "Transition vase integrity_scale _ broken" not in lean
        and "Transition vase integrity_scale _ broken" not in coq,
    }

    failed = [name for name, ok in checks.items() if not ok]
    if failed:
        for name in failed:
            print(f"FAILED: {name}", file=sys.stderr)
        raise SystemExit(1)

    print("formalization scaffolds are consistent")


if __name__ == "__main__":
    main()
