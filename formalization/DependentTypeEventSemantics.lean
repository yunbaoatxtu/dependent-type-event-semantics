-- Auto-generated shallow embedding for dependent-type event semantics.
-- This file is an interface scaffold, not a complete proof development.

constant Entity : Type
constant Food : Type
constant State : Type
constant StateScale : Type
constant TransitionT : Type
abbrev PropT : Type := Prop
def Adv : Type := (Entity -> PropT) -> Entity -> PropT
constant ModifierSeq : Nat -> Type
constant mods_nil : ModifierSeq 0
constant mods_cons : (n : Nat) -> Adv -> ModifierSeq n -> ModifierSeq (Nat.succ n)

constant John : Entity
constant broken : State
constant intact : State
constant integrity_scale : StateScale
constant noon : Entity
constant toast : Entity
constant vase : Entity
constant in_bathroom : Adv
constant slowly : Adv

inductive ObligationStatus : Type
  | pending
  | shallow_checked
  | proved

structure SemanticPreservationObligation : Type where
  obligation_statement : Prop
  obligation_status : ObligationStatus

constant repeat : Nat -> PropT -> PropT
constant at_T : Entity -> PropT -> PropT
constant during_T : Entity -> PropT -> PropT
constant before_T : Entity -> PropT -> PropT
constant after_T : Entity -> PropT -> PropT
constant until_T : Entity -> PropT -> PropT
constant since_T : Entity -> PropT -> PropT
constant not_T : PropT -> PropT
constant Transition : Entity -> StateScale -> State -> State -> TransitionT
constant Cause : Entity -> TransitionT -> PropT
constant SemanticPreservation : (A : Type) -> A -> Prop
constant break : (n : Nat) -> ModifierSeq n -> Entity -> Entity -> PropT
constant butter : (n : Nat) -> ModifierSeq n -> Entity -> Entity -> PropT
constant eat : (n : Nat) -> ModifierSeq n -> Entity -> Food -> Prop
constant knock : (n : Nat) -> ModifierSeq n -> Entity -> PropT

def example_1 : PropT := (at_T noon (butter 2 (mods_cons 1 slowly (mods_cons 0 in_bathroom mods_nil)) John toast))
def example_2 : Prop := (Exists fun x_theme : Food => (eat 0 mods_nil John x_theme))
def example_3 : PropT := (repeat 2 (knock 0 mods_nil John))
def example_4 : PropT := (Cause John (Transition vase integrity_scale intact broken))

def example_1_semantic_preservation_obligation : Prop := SemanticPreservation PropT example_1
def example_2_semantic_preservation_obligation : Prop := SemanticPreservation Prop example_2
def example_3_semantic_preservation_obligation : Prop := SemanticPreservation PropT example_3
def example_4_semantic_preservation_obligation : Prop := SemanticPreservation PropT example_4

def example_1_semantic_preservation_obligation_record : SemanticPreservationObligation := {
  obligation_statement := example_1_semantic_preservation_obligation,
  obligation_status := ObligationStatus.shallow_checked
}
def example_2_semantic_preservation_obligation_record : SemanticPreservationObligation := {
  obligation_statement := example_2_semantic_preservation_obligation,
  obligation_status := ObligationStatus.shallow_checked
}
def example_3_semantic_preservation_obligation_record : SemanticPreservationObligation := {
  obligation_statement := example_3_semantic_preservation_obligation,
  obligation_status := ObligationStatus.shallow_checked
}
def example_4_semantic_preservation_obligation_record : SemanticPreservationObligation := {
  obligation_statement := example_4_semantic_preservation_obligation,
  obligation_status := ObligationStatus.shallow_checked
}

theorem example_1_semantic_preservation_obligation_is_prop :
    Exists (fun P : Prop => P = example_1_semantic_preservation_obligation) := by
  exact Exists.intro example_1_semantic_preservation_obligation rfl
theorem example_2_semantic_preservation_obligation_is_prop :
    Exists (fun P : Prop => P = example_2_semantic_preservation_obligation) := by
  exact Exists.intro example_2_semantic_preservation_obligation rfl
theorem example_3_semantic_preservation_obligation_is_prop :
    Exists (fun P : Prop => P = example_3_semantic_preservation_obligation) := by
  exact Exists.intro example_3_semantic_preservation_obligation rfl
theorem example_4_semantic_preservation_obligation_is_prop :
    Exists (fun P : Prop => P = example_4_semantic_preservation_obligation) := by
  exact Exists.intro example_4_semantic_preservation_obligation rfl

#check example_1
#check example_1_semantic_preservation_obligation
#check example_1_semantic_preservation_obligation_record
#check example_1_semantic_preservation_obligation_is_prop
#check example_2
#check example_2_semantic_preservation_obligation
#check example_2_semantic_preservation_obligation_record
#check example_2_semantic_preservation_obligation_is_prop
#check example_3
#check example_3_semantic_preservation_obligation
#check example_3_semantic_preservation_obligation_record
#check example_3_semantic_preservation_obligation_is_prop
#check example_4
#check example_4_semantic_preservation_obligation
#check example_4_semantic_preservation_obligation_record
#check example_4_semantic_preservation_obligation_is_prop
