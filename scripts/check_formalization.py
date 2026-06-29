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
        "lean semantic preservation parameter": (
            "constant SemanticPreservation : (A : Type) -> A -> Prop" in lean
        ),
        "coq semantic preservation parameter": (
            "Parameter SemanticPreservation : forall A : Type, A -> Prop." in coq
        ),
        "lean semantic preservation obligation status": (
            "inductive ObligationStatus : Type" in lean
            and "structure SemanticPreservationObligation : Type where" in lean
        ),
        "coq semantic preservation obligation status": (
            "Inductive ObligationStatus : Type :=" in coq
            and "Record SemanticPreservationObligation : Type := {" in coq
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
        "lean semantic preservation obligation checks": (
            "#check example_4_semantic_preservation_obligation" in lean
            and "#check example_4_semantic_preservation_obligation_record" in lean
            and "#check example_4_semantic_preservation_obligation_is_prop" in lean
        ),
        "coq semantic preservation obligation checks": (
            "Check example_4_semantic_preservation_obligation." in coq
            and "Check example_4_semantic_preservation_obligation_record." in coq
            and "Check example_4_semantic_preservation_obligation_is_prop." in coq
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
