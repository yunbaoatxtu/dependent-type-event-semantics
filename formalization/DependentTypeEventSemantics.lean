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
constant break : (n : Nat) -> ModifierSeq n -> Entity -> Entity -> PropT
constant butter : (n : Nat) -> ModifierSeq n -> Entity -> Entity -> PropT
constant eat : (n : Nat) -> ModifierSeq n -> Entity -> Food -> Prop
constant knock : (n : Nat) -> ModifierSeq n -> Entity -> PropT

inductive SemanticPreservation : (A : Type) -> A -> Prop where
  | preserve_break_application : (n : Nat) -> (mods : ModifierSeq n) -> (arg1 : Entity) -> (arg2 : Entity) -> SemanticPreservation PropT (break n mods arg1 arg2)
  | preserve_butter_application : (n : Nat) -> (mods : ModifierSeq n) -> (arg1 : Entity) -> (arg2 : Entity) -> SemanticPreservation PropT (butter n mods arg1 arg2)
  | preserve_eat_application : (n : Nat) -> (mods : ModifierSeq n) -> (arg1 : Entity) -> (arg2 : Food) -> SemanticPreservation Prop (eat n mods arg1 arg2)
  | preserve_knock_application : (n : Nat) -> (mods : ModifierSeq n) -> (arg1 : Entity) -> SemanticPreservation PropT (knock n mods arg1)
  | preserve_sigma_Entity : (P : Entity -> Prop) -> ((x : Entity) -> SemanticPreservation Prop (P x)) -> SemanticPreservation Prop (Exists fun x : Entity => P x)
  | preserve_sigma_Food : (P : Food -> Prop) -> ((x : Food) -> SemanticPreservation Prop (P x)) -> SemanticPreservation Prop (Exists fun x : Food => P x)
  | preserve_sigma_State : (P : State -> Prop) -> ((x : State) -> SemanticPreservation Prop (P x)) -> SemanticPreservation Prop (Exists fun x : State => P x)
  | preserve_sigma_StateScale : (P : StateScale -> Prop) -> ((x : StateScale) -> SemanticPreservation Prop (P x)) -> SemanticPreservation Prop (Exists fun x : StateScale => P x)
  | preserve_sigma_TransitionT : (P : TransitionT -> Prop) -> ((x : TransitionT) -> SemanticPreservation Prop (P x)) -> SemanticPreservation Prop (Exists fun x : TransitionT => P x)
  | preserve_repeat : (n : Nat) -> (body : PropT) -> SemanticPreservation PropT body -> SemanticPreservation PropT (repeat n body)
  | preserve_at_T : (marker : Entity) -> (body : PropT) -> SemanticPreservation PropT body -> SemanticPreservation PropT (at_T marker body)
  | preserve_during_T : (marker : Entity) -> (body : PropT) -> SemanticPreservation PropT body -> SemanticPreservation PropT (during_T marker body)
  | preserve_before_T : (marker : Entity) -> (body : PropT) -> SemanticPreservation PropT body -> SemanticPreservation PropT (before_T marker body)
  | preserve_after_T : (marker : Entity) -> (body : PropT) -> SemanticPreservation PropT body -> SemanticPreservation PropT (after_T marker body)
  | preserve_until_T : (marker : Entity) -> (body : PropT) -> SemanticPreservation PropT body -> SemanticPreservation PropT (until_T marker body)
  | preserve_since_T : (marker : Entity) -> (body : PropT) -> SemanticPreservation PropT body -> SemanticPreservation PropT (since_T marker body)
  | preserve_not_T : (body : PropT) -> SemanticPreservation PropT body -> SemanticPreservation PropT (not_T body)
  | preserve_transition : (theme : Entity) -> (scale : StateScale) -> (source : State) -> (target : State) -> SemanticPreservation TransitionT (Transition theme scale source target)
  | preserve_cause : (causer : Entity) -> (effect : TransitionT) -> SemanticPreservation TransitionT effect -> SemanticPreservation PropT (Cause causer effect)
def PreservationTargetMatches (A : Type) (term : A) (target : SemanticPreservationObligation) : Prop :=
  target.obligation_statement = SemanticPreservation A term

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
  obligation_status := ObligationStatus.proved
}
def example_2_semantic_preservation_obligation_record : SemanticPreservationObligation := {
  obligation_statement := example_2_semantic_preservation_obligation,
  obligation_status := ObligationStatus.proved
}
def example_3_semantic_preservation_obligation_record : SemanticPreservationObligation := {
  obligation_statement := example_3_semantic_preservation_obligation,
  obligation_status := ObligationStatus.proved
}
def example_4_semantic_preservation_obligation_record : SemanticPreservationObligation := {
  obligation_statement := example_4_semantic_preservation_obligation,
  obligation_status := ObligationStatus.proved
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

theorem example_1_semantic_preservation_target_matches :
    PreservationTargetMatches PropT example_1 example_1_semantic_preservation_obligation_record := by
  rfl
theorem example_2_semantic_preservation_target_matches :
    PreservationTargetMatches Prop example_2 example_2_semantic_preservation_obligation_record := by
  rfl
theorem example_3_semantic_preservation_target_matches :
    PreservationTargetMatches PropT example_3 example_3_semantic_preservation_obligation_record := by
  rfl
theorem example_4_semantic_preservation_target_matches :
    PreservationTargetMatches PropT example_4 example_4_semantic_preservation_obligation_record := by
  rfl

theorem example_1_semantic_preservation_proved : example_1_semantic_preservation_obligation := by
  unfold example_1_semantic_preservation_obligation
  unfold example_1
  apply SemanticPreservation.preserve_at_T
  apply SemanticPreservation.preserve_butter_application
theorem example_2_semantic_preservation_proved : example_2_semantic_preservation_obligation := by
  unfold example_2_semantic_preservation_obligation
  unfold example_2
  apply SemanticPreservation.preserve_sigma_Food
  intro x_theme
  apply SemanticPreservation.preserve_eat_application
theorem example_3_semantic_preservation_proved : example_3_semantic_preservation_obligation := by
  unfold example_3_semantic_preservation_obligation
  unfold example_3
  apply SemanticPreservation.preserve_repeat
  apply SemanticPreservation.preserve_knock_application
theorem example_4_semantic_preservation_proved : example_4_semantic_preservation_obligation := by
  unfold example_4_semantic_preservation_obligation
  unfold example_4
  apply SemanticPreservation.preserve_cause
  apply SemanticPreservation.preserve_transition

#check example_1
#check example_1_semantic_preservation_obligation
#check example_1_semantic_preservation_obligation_record
#check example_1_semantic_preservation_obligation_is_prop
#check example_1_semantic_preservation_target_matches
#check example_1_semantic_preservation_proved
#check example_2
#check example_2_semantic_preservation_obligation
#check example_2_semantic_preservation_obligation_record
#check example_2_semantic_preservation_obligation_is_prop
#check example_2_semantic_preservation_target_matches
#check example_2_semantic_preservation_proved
#check example_3
#check example_3_semantic_preservation_obligation
#check example_3_semantic_preservation_obligation_record
#check example_3_semantic_preservation_obligation_is_prop
#check example_3_semantic_preservation_target_matches
#check example_3_semantic_preservation_proved
#check example_4
#check example_4_semantic_preservation_obligation
#check example_4_semantic_preservation_obligation_record
#check example_4_semantic_preservation_obligation_is_prop
#check example_4_semantic_preservation_target_matches
#check example_4_semantic_preservation_proved
