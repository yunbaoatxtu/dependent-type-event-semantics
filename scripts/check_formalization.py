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
            and "#check concrete_registered_truth_kernel" in lean
            and "#check concrete_registered_truth_conditions_from_kernel" in lean
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
            and "Check concrete_registered_truth_kernel." in coq
            and "Check concrete_registered_truth_conditions_from_kernel." in coq
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
