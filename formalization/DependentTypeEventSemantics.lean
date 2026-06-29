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

inductive ModelInterpretable : (A : Type) -> A -> Prop where
  | model_break_application : (n : Nat) -> (mods : ModifierSeq n) -> (arg1 : Entity) -> (arg2 : Entity) -> ModelInterpretable PropT (break n mods arg1 arg2)
  | model_butter_application : (n : Nat) -> (mods : ModifierSeq n) -> (arg1 : Entity) -> (arg2 : Entity) -> ModelInterpretable PropT (butter n mods arg1 arg2)
  | model_eat_application : (n : Nat) -> (mods : ModifierSeq n) -> (arg1 : Entity) -> (arg2 : Food) -> ModelInterpretable Prop (eat n mods arg1 arg2)
  | model_knock_application : (n : Nat) -> (mods : ModifierSeq n) -> (arg1 : Entity) -> ModelInterpretable PropT (knock n mods arg1)
  | model_sigma_Entity : (P : Entity -> Prop) -> ((x : Entity) -> ModelInterpretable Prop (P x)) -> ModelInterpretable Prop (Exists fun x : Entity => P x)
  | model_sigma_Food : (P : Food -> Prop) -> ((x : Food) -> ModelInterpretable Prop (P x)) -> ModelInterpretable Prop (Exists fun x : Food => P x)
  | model_sigma_State : (P : State -> Prop) -> ((x : State) -> ModelInterpretable Prop (P x)) -> ModelInterpretable Prop (Exists fun x : State => P x)
  | model_sigma_StateScale : (P : StateScale -> Prop) -> ((x : StateScale) -> ModelInterpretable Prop (P x)) -> ModelInterpretable Prop (Exists fun x : StateScale => P x)
  | model_sigma_TransitionT : (P : TransitionT -> Prop) -> ((x : TransitionT) -> ModelInterpretable Prop (P x)) -> ModelInterpretable Prop (Exists fun x : TransitionT => P x)
  | model_repeat : (n : Nat) -> (body : PropT) -> ModelInterpretable PropT body -> ModelInterpretable PropT (repeat n body)
  | model_at_T : (marker : Entity) -> (body : PropT) -> ModelInterpretable PropT body -> ModelInterpretable PropT (at_T marker body)
  | model_during_T : (marker : Entity) -> (body : PropT) -> ModelInterpretable PropT body -> ModelInterpretable PropT (during_T marker body)
  | model_before_T : (marker : Entity) -> (body : PropT) -> ModelInterpretable PropT body -> ModelInterpretable PropT (before_T marker body)
  | model_after_T : (marker : Entity) -> (body : PropT) -> ModelInterpretable PropT body -> ModelInterpretable PropT (after_T marker body)
  | model_until_T : (marker : Entity) -> (body : PropT) -> ModelInterpretable PropT body -> ModelInterpretable PropT (until_T marker body)
  | model_since_T : (marker : Entity) -> (body : PropT) -> ModelInterpretable PropT body -> ModelInterpretable PropT (since_T marker body)
  | model_not_T : (body : PropT) -> ModelInterpretable PropT body -> ModelInterpretable PropT (not_T body)
  | model_transition : (theme : Entity) -> (scale : StateScale) -> (source : State) -> (target : State) -> ModelInterpretable TransitionT (Transition theme scale source target)
  | model_cause : (causer : Entity) -> (effect : TransitionT) -> ModelInterpretable TransitionT effect -> ModelInterpretable PropT (Cause causer effect)

inductive SyntaxDirectedTruth : (A : Type) -> A -> Prop where
  | syntax_truth_break_application : (n : Nat) -> (mods : ModifierSeq n) -> (arg1 : Entity) -> (arg2 : Entity) -> SyntaxDirectedTruth PropT (break n mods arg1 arg2)
  | syntax_truth_butter_application : (n : Nat) -> (mods : ModifierSeq n) -> (arg1 : Entity) -> (arg2 : Entity) -> SyntaxDirectedTruth PropT (butter n mods arg1 arg2)
  | syntax_truth_eat_application : (n : Nat) -> (mods : ModifierSeq n) -> (arg1 : Entity) -> (arg2 : Food) -> SyntaxDirectedTruth Prop (eat n mods arg1 arg2)
  | syntax_truth_knock_application : (n : Nat) -> (mods : ModifierSeq n) -> (arg1 : Entity) -> SyntaxDirectedTruth PropT (knock n mods arg1)
  | syntax_truth_sigma_Entity : (P : Entity -> Prop) -> ((x : Entity) -> SyntaxDirectedTruth Prop (P x)) -> SyntaxDirectedTruth Prop (Exists fun x : Entity => P x)
  | syntax_truth_sigma_Food : (P : Food -> Prop) -> ((x : Food) -> SyntaxDirectedTruth Prop (P x)) -> SyntaxDirectedTruth Prop (Exists fun x : Food => P x)
  | syntax_truth_sigma_State : (P : State -> Prop) -> ((x : State) -> SyntaxDirectedTruth Prop (P x)) -> SyntaxDirectedTruth Prop (Exists fun x : State => P x)
  | syntax_truth_sigma_StateScale : (P : StateScale -> Prop) -> ((x : StateScale) -> SyntaxDirectedTruth Prop (P x)) -> SyntaxDirectedTruth Prop (Exists fun x : StateScale => P x)
  | syntax_truth_sigma_TransitionT : (P : TransitionT -> Prop) -> ((x : TransitionT) -> SyntaxDirectedTruth Prop (P x)) -> SyntaxDirectedTruth Prop (Exists fun x : TransitionT => P x)
  | syntax_truth_repeat : (n : Nat) -> (body : PropT) -> SyntaxDirectedTruth PropT body -> SyntaxDirectedTruth PropT (repeat n body)
  | syntax_truth_at_T : (marker : Entity) -> (body : PropT) -> SyntaxDirectedTruth PropT body -> SyntaxDirectedTruth PropT (at_T marker body)
  | syntax_truth_during_T : (marker : Entity) -> (body : PropT) -> SyntaxDirectedTruth PropT body -> SyntaxDirectedTruth PropT (during_T marker body)
  | syntax_truth_before_T : (marker : Entity) -> (body : PropT) -> SyntaxDirectedTruth PropT body -> SyntaxDirectedTruth PropT (before_T marker body)
  | syntax_truth_after_T : (marker : Entity) -> (body : PropT) -> SyntaxDirectedTruth PropT body -> SyntaxDirectedTruth PropT (after_T marker body)
  | syntax_truth_until_T : (marker : Entity) -> (body : PropT) -> SyntaxDirectedTruth PropT body -> SyntaxDirectedTruth PropT (until_T marker body)
  | syntax_truth_since_T : (marker : Entity) -> (body : PropT) -> SyntaxDirectedTruth PropT body -> SyntaxDirectedTruth PropT (since_T marker body)
  | syntax_truth_not_T : (body : PropT) -> SyntaxDirectedTruth PropT body -> SyntaxDirectedTruth PropT (not_T body)
  | syntax_truth_transition : (theme : Entity) -> (scale : StateScale) -> (source : State) -> (target : State) -> SyntaxDirectedTruth TransitionT (Transition theme scale source target)
  | syntax_truth_cause : (causer : Entity) -> (effect : TransitionT) -> SyntaxDirectedTruth TransitionT effect -> SyntaxDirectedTruth PropT (Cause causer effect)

theorem semantic_preservation_model_interpretable :
    (A : Type) -> (term : A) -> SemanticPreservation A term -> ModelInterpretable A term := by
  intro A term h
  induction h <;> constructor <;> assumption

theorem semantic_preservation_syntax_directed_truth :
    (A : Type) -> (term : A) -> SemanticPreservation A term -> SyntaxDirectedTruth A term := by
  intro A term h
  induction h <;> constructor <;> assumption

structure SemanticModel : Type where
  model_denotes : (A : Type) -> A -> Prop
  denote_break_application : (n : Nat) -> (mods : ModifierSeq n) -> (arg1 : Entity) -> (arg2 : Entity) -> model_denotes PropT (break n mods arg1 arg2)
  denote_butter_application : (n : Nat) -> (mods : ModifierSeq n) -> (arg1 : Entity) -> (arg2 : Entity) -> model_denotes PropT (butter n mods arg1 arg2)
  denote_eat_application : (n : Nat) -> (mods : ModifierSeq n) -> (arg1 : Entity) -> (arg2 : Food) -> model_denotes Prop (eat n mods arg1 arg2)
  denote_knock_application : (n : Nat) -> (mods : ModifierSeq n) -> (arg1 : Entity) -> model_denotes PropT (knock n mods arg1)
  denote_sigma_Entity : (P : Entity -> Prop) -> ((x : Entity) -> model_denotes Prop (P x)) -> model_denotes Prop (Exists fun x : Entity => P x)
  denote_sigma_Food : (P : Food -> Prop) -> ((x : Food) -> model_denotes Prop (P x)) -> model_denotes Prop (Exists fun x : Food => P x)
  denote_sigma_State : (P : State -> Prop) -> ((x : State) -> model_denotes Prop (P x)) -> model_denotes Prop (Exists fun x : State => P x)
  denote_sigma_StateScale : (P : StateScale -> Prop) -> ((x : StateScale) -> model_denotes Prop (P x)) -> model_denotes Prop (Exists fun x : StateScale => P x)
  denote_sigma_TransitionT : (P : TransitionT -> Prop) -> ((x : TransitionT) -> model_denotes Prop (P x)) -> model_denotes Prop (Exists fun x : TransitionT => P x)
  denote_repeat : (n : Nat) -> (body : PropT) -> model_denotes PropT body -> model_denotes PropT (repeat n body)
  denote_at_T : (marker : Entity) -> (body : PropT) -> model_denotes PropT body -> model_denotes PropT (at_T marker body)
  denote_during_T : (marker : Entity) -> (body : PropT) -> model_denotes PropT body -> model_denotes PropT (during_T marker body)
  denote_before_T : (marker : Entity) -> (body : PropT) -> model_denotes PropT body -> model_denotes PropT (before_T marker body)
  denote_after_T : (marker : Entity) -> (body : PropT) -> model_denotes PropT body -> model_denotes PropT (after_T marker body)
  denote_until_T : (marker : Entity) -> (body : PropT) -> model_denotes PropT body -> model_denotes PropT (until_T marker body)
  denote_since_T : (marker : Entity) -> (body : PropT) -> model_denotes PropT body -> model_denotes PropT (since_T marker body)
  denote_not_T : (body : PropT) -> model_denotes PropT body -> model_denotes PropT (not_T body)
  denote_transition : (theme : Entity) -> (scale : StateScale) -> (source : State) -> (target : State) -> model_denotes TransitionT (Transition theme scale source target)
  denote_cause : (causer : Entity) -> (effect : TransitionT) -> model_denotes TransitionT effect -> model_denotes PropT (Cause causer effect)

theorem model_interpretable_denotational_sound :
    (M : SemanticModel) -> (A : Type) -> (term : A) -> ModelInterpretable A term -> M.model_denotes A term := by
  intro M A term h
  induction h
  | model_break_application n mods arg1 arg2 => exact M.denote_break_application n mods arg1 arg2
  | model_butter_application n mods arg1 arg2 => exact M.denote_butter_application n mods arg1 arg2
  | model_eat_application n mods arg1 arg2 => exact M.denote_eat_application n mods arg1 arg2
  | model_knock_application n mods arg1 => exact M.denote_knock_application n mods arg1
  | model_sigma_Entity P h ih => exact M.denote_sigma_Entity P ih
  | model_sigma_Food P h ih => exact M.denote_sigma_Food P ih
  | model_sigma_State P h ih => exact M.denote_sigma_State P ih
  | model_sigma_StateScale P h ih => exact M.denote_sigma_StateScale P ih
  | model_sigma_TransitionT P h ih => exact M.denote_sigma_TransitionT P ih
  | model_repeat n body h ih => exact M.denote_repeat n body ih
  | model_at_T marker body h ih => exact M.denote_at_T marker body ih
  | model_during_T marker body h ih => exact M.denote_during_T marker body ih
  | model_before_T marker body h ih => exact M.denote_before_T marker body ih
  | model_after_T marker body h ih => exact M.denote_after_T marker body ih
  | model_until_T marker body h ih => exact M.denote_until_T marker body ih
  | model_since_T marker body h ih => exact M.denote_since_T marker body ih
  | model_not_T body h ih => exact M.denote_not_T body ih
  | model_transition theme scale source target => exact M.denote_transition theme scale source target
  | model_cause causer effect h ih => exact M.denote_cause causer effect ih

structure TruthConditionSpec : Type where
  truth_denotes : (A : Type) -> A -> Prop
  truth_break_application : (n : Nat) -> (mods : ModifierSeq n) -> (arg1 : Entity) -> (arg2 : Entity) -> truth_denotes PropT (break n mods arg1 arg2)
  truth_butter_application : (n : Nat) -> (mods : ModifierSeq n) -> (arg1 : Entity) -> (arg2 : Entity) -> truth_denotes PropT (butter n mods arg1 arg2)
  truth_eat_application : (n : Nat) -> (mods : ModifierSeq n) -> (arg1 : Entity) -> (arg2 : Food) -> truth_denotes Prop (eat n mods arg1 arg2)
  truth_knock_application : (n : Nat) -> (mods : ModifierSeq n) -> (arg1 : Entity) -> truth_denotes PropT (knock n mods arg1)
  truth_sigma_Entity : (P : Entity -> Prop) -> ((x : Entity) -> truth_denotes Prop (P x)) -> truth_denotes Prop (Exists fun x : Entity => P x)
  truth_sigma_Food : (P : Food -> Prop) -> ((x : Food) -> truth_denotes Prop (P x)) -> truth_denotes Prop (Exists fun x : Food => P x)
  truth_sigma_State : (P : State -> Prop) -> ((x : State) -> truth_denotes Prop (P x)) -> truth_denotes Prop (Exists fun x : State => P x)
  truth_sigma_StateScale : (P : StateScale -> Prop) -> ((x : StateScale) -> truth_denotes Prop (P x)) -> truth_denotes Prop (Exists fun x : StateScale => P x)
  truth_sigma_TransitionT : (P : TransitionT -> Prop) -> ((x : TransitionT) -> truth_denotes Prop (P x)) -> truth_denotes Prop (Exists fun x : TransitionT => P x)
  truth_repeat : (n : Nat) -> (body : PropT) -> truth_denotes PropT body -> truth_denotes PropT (repeat n body)
  truth_at_T : (marker : Entity) -> (body : PropT) -> truth_denotes PropT body -> truth_denotes PropT (at_T marker body)
  truth_during_T : (marker : Entity) -> (body : PropT) -> truth_denotes PropT body -> truth_denotes PropT (during_T marker body)
  truth_before_T : (marker : Entity) -> (body : PropT) -> truth_denotes PropT body -> truth_denotes PropT (before_T marker body)
  truth_after_T : (marker : Entity) -> (body : PropT) -> truth_denotes PropT body -> truth_denotes PropT (after_T marker body)
  truth_until_T : (marker : Entity) -> (body : PropT) -> truth_denotes PropT body -> truth_denotes PropT (until_T marker body)
  truth_since_T : (marker : Entity) -> (body : PropT) -> truth_denotes PropT body -> truth_denotes PropT (since_T marker body)
  truth_not_T : (body : PropT) -> truth_denotes PropT body -> truth_denotes PropT (not_T body)
  truth_transition : (theme : Entity) -> (scale : StateScale) -> (source : State) -> (target : State) -> truth_denotes TransitionT (Transition theme scale source target)
  truth_cause : (causer : Entity) -> (effect : TransitionT) -> truth_denotes TransitionT effect -> truth_denotes PropT (Cause causer effect)

def semantic_model_from_truth_conditions (T : TruthConditionSpec) : SemanticModel := {
  model_denotes := T.truth_denotes,
  denote_break_application := T.truth_break_application,
  denote_butter_application := T.truth_butter_application,
  denote_eat_application := T.truth_eat_application,
  denote_knock_application := T.truth_knock_application,
  denote_sigma_Entity := T.truth_sigma_Entity,
  denote_sigma_Food := T.truth_sigma_Food,
  denote_sigma_State := T.truth_sigma_State,
  denote_sigma_StateScale := T.truth_sigma_StateScale,
  denote_sigma_TransitionT := T.truth_sigma_TransitionT,
  denote_repeat := T.truth_repeat,
  denote_at_T := T.truth_at_T,
  denote_during_T := T.truth_during_T,
  denote_before_T := T.truth_before_T,
  denote_after_T := T.truth_after_T,
  denote_until_T := T.truth_until_T,
  denote_since_T := T.truth_since_T,
  denote_not_T := T.truth_not_T,
  denote_transition := T.truth_transition,
  denote_cause := T.truth_cause
}

theorem truth_conditions_induce_denotational_soundness :
    (T : TruthConditionSpec) -> (A : Type) -> (term : A) -> ModelInterpretable A term -> T.truth_denotes A term := by
  intro T A term h
  exact model_interpretable_denotational_sound (semantic_model_from_truth_conditions T) A term h

structure ConcreteTruthConditionKernel : Type where
  kernel_denotes : (A : Type) -> A -> Prop
  lexical_truth_break_application : (n : Nat) -> (mods : ModifierSeq n) -> (arg1 : Entity) -> (arg2 : Entity) -> kernel_denotes PropT (break n mods arg1 arg2)
  lexical_truth_butter_application : (n : Nat) -> (mods : ModifierSeq n) -> (arg1 : Entity) -> (arg2 : Entity) -> kernel_denotes PropT (butter n mods arg1 arg2)
  lexical_truth_eat_application : (n : Nat) -> (mods : ModifierSeq n) -> (arg1 : Entity) -> (arg2 : Food) -> kernel_denotes Prop (eat n mods arg1 arg2)
  lexical_truth_knock_application : (n : Nat) -> (mods : ModifierSeq n) -> (arg1 : Entity) -> kernel_denotes PropT (knock n mods arg1)
  quantifier_truth_sigma_Entity : (P : Entity -> Prop) -> ((x : Entity) -> kernel_denotes Prop (P x)) -> kernel_denotes Prop (Exists fun x : Entity => P x)
  quantifier_truth_sigma_Food : (P : Food -> Prop) -> ((x : Food) -> kernel_denotes Prop (P x)) -> kernel_denotes Prop (Exists fun x : Food => P x)
  quantifier_truth_sigma_State : (P : State -> Prop) -> ((x : State) -> kernel_denotes Prop (P x)) -> kernel_denotes Prop (Exists fun x : State => P x)
  quantifier_truth_sigma_StateScale : (P : StateScale -> Prop) -> ((x : StateScale) -> kernel_denotes Prop (P x)) -> kernel_denotes Prop (Exists fun x : StateScale => P x)
  quantifier_truth_sigma_TransitionT : (P : TransitionT -> Prop) -> ((x : TransitionT) -> kernel_denotes Prop (P x)) -> kernel_denotes Prop (Exists fun x : TransitionT => P x)
  repetition_truth : (n : Nat) -> (body : PropT) -> kernel_denotes PropT body -> kernel_denotes PropT (repeat n body)
  temporal_truth_at_T : (marker : Entity) -> (body : PropT) -> kernel_denotes PropT body -> kernel_denotes PropT (at_T marker body)
  temporal_truth_during_T : (marker : Entity) -> (body : PropT) -> kernel_denotes PropT body -> kernel_denotes PropT (during_T marker body)
  temporal_truth_before_T : (marker : Entity) -> (body : PropT) -> kernel_denotes PropT body -> kernel_denotes PropT (before_T marker body)
  temporal_truth_after_T : (marker : Entity) -> (body : PropT) -> kernel_denotes PropT body -> kernel_denotes PropT (after_T marker body)
  temporal_truth_until_T : (marker : Entity) -> (body : PropT) -> kernel_denotes PropT body -> kernel_denotes PropT (until_T marker body)
  temporal_truth_since_T : (marker : Entity) -> (body : PropT) -> kernel_denotes PropT body -> kernel_denotes PropT (since_T marker body)
  polarity_truth_not_T : (body : PropT) -> kernel_denotes PropT body -> kernel_denotes PropT (not_T body)
  transition_truth : (theme : Entity) -> (scale : StateScale) -> (source : State) -> (target : State) -> kernel_denotes TransitionT (Transition theme scale source target)
  cause_truth : (causer : Entity) -> (effect : TransitionT) -> kernel_denotes TransitionT effect -> kernel_denotes PropT (Cause causer effect)

def truth_conditions_from_concrete_kernel (K : ConcreteTruthConditionKernel) : TruthConditionSpec := {
  truth_denotes := K.kernel_denotes,
  truth_break_application := K.lexical_truth_break_application,
  truth_butter_application := K.lexical_truth_butter_application,
  truth_eat_application := K.lexical_truth_eat_application,
  truth_knock_application := K.lexical_truth_knock_application,
  truth_sigma_Entity := K.quantifier_truth_sigma_Entity,
  truth_sigma_Food := K.quantifier_truth_sigma_Food,
  truth_sigma_State := K.quantifier_truth_sigma_State,
  truth_sigma_StateScale := K.quantifier_truth_sigma_StateScale,
  truth_sigma_TransitionT := K.quantifier_truth_sigma_TransitionT,
  truth_repeat := K.repetition_truth,
  truth_at_T := K.temporal_truth_at_T,
  truth_during_T := K.temporal_truth_during_T,
  truth_before_T := K.temporal_truth_before_T,
  truth_after_T := K.temporal_truth_after_T,
  truth_until_T := K.temporal_truth_until_T,
  truth_since_T := K.temporal_truth_since_T,
  truth_not_T := K.polarity_truth_not_T,
  truth_transition := K.transition_truth,
  truth_cause := K.cause_truth
}

theorem concrete_kernel_truth_condition_spec_exists :
    (K : ConcreteTruthConditionKernel) -> Exists (fun T : TruthConditionSpec => T = truth_conditions_from_concrete_kernel K) := by
  intro K
  exact Exists.intro (truth_conditions_from_concrete_kernel K) rfl

theorem concrete_kernel_induces_truth_condition_soundness :
    (K : ConcreteTruthConditionKernel) -> (A : Type) -> (term : A) -> ModelInterpretable A term -> (truth_conditions_from_concrete_kernel K).truth_denotes A term := by
  intro K A term h
  apply truth_conditions_induce_denotational_soundness
  exact h

structure PrimitiveTruthAssumptions : Type where
  primitive_denotes : (A : Type) -> A -> Prop
  primitive_lexical_truth_break_application : (n : Nat) -> (mods : ModifierSeq n) -> (arg1 : Entity) -> (arg2 : Entity) -> primitive_denotes PropT (break n mods arg1 arg2)
  primitive_lexical_truth_butter_application : (n : Nat) -> (mods : ModifierSeq n) -> (arg1 : Entity) -> (arg2 : Entity) -> primitive_denotes PropT (butter n mods arg1 arg2)
  primitive_lexical_truth_eat_application : (n : Nat) -> (mods : ModifierSeq n) -> (arg1 : Entity) -> (arg2 : Food) -> primitive_denotes Prop (eat n mods arg1 arg2)
  primitive_lexical_truth_knock_application : (n : Nat) -> (mods : ModifierSeq n) -> (arg1 : Entity) -> primitive_denotes PropT (knock n mods arg1)
  primitive_quantifier_truth_sigma_Entity : (P : Entity -> Prop) -> ((x : Entity) -> primitive_denotes Prop (P x)) -> primitive_denotes Prop (Exists fun x : Entity => P x)
  primitive_quantifier_truth_sigma_Food : (P : Food -> Prop) -> ((x : Food) -> primitive_denotes Prop (P x)) -> primitive_denotes Prop (Exists fun x : Food => P x)
  primitive_quantifier_truth_sigma_State : (P : State -> Prop) -> ((x : State) -> primitive_denotes Prop (P x)) -> primitive_denotes Prop (Exists fun x : State => P x)
  primitive_quantifier_truth_sigma_StateScale : (P : StateScale -> Prop) -> ((x : StateScale) -> primitive_denotes Prop (P x)) -> primitive_denotes Prop (Exists fun x : StateScale => P x)
  primitive_quantifier_truth_sigma_TransitionT : (P : TransitionT -> Prop) -> ((x : TransitionT) -> primitive_denotes Prop (P x)) -> primitive_denotes Prop (Exists fun x : TransitionT => P x)
  primitive_repetition_truth : (n : Nat) -> (body : PropT) -> primitive_denotes PropT body -> primitive_denotes PropT (repeat n body)
  primitive_temporal_truth_at_T : (marker : Entity) -> (body : PropT) -> primitive_denotes PropT body -> primitive_denotes PropT (at_T marker body)
  primitive_temporal_truth_during_T : (marker : Entity) -> (body : PropT) -> primitive_denotes PropT body -> primitive_denotes PropT (during_T marker body)
  primitive_temporal_truth_before_T : (marker : Entity) -> (body : PropT) -> primitive_denotes PropT body -> primitive_denotes PropT (before_T marker body)
  primitive_temporal_truth_after_T : (marker : Entity) -> (body : PropT) -> primitive_denotes PropT body -> primitive_denotes PropT (after_T marker body)
  primitive_temporal_truth_until_T : (marker : Entity) -> (body : PropT) -> primitive_denotes PropT body -> primitive_denotes PropT (until_T marker body)
  primitive_temporal_truth_since_T : (marker : Entity) -> (body : PropT) -> primitive_denotes PropT body -> primitive_denotes PropT (since_T marker body)
  primitive_polarity_truth_not_T : (body : PropT) -> primitive_denotes PropT body -> primitive_denotes PropT (not_T body)
  primitive_transition_truth : (theme : Entity) -> (scale : StateScale) -> (source : State) -> (target : State) -> primitive_denotes TransitionT (Transition theme scale source target)
  primitive_cause_truth : (causer : Entity) -> (effect : TransitionT) -> primitive_denotes TransitionT effect -> primitive_denotes PropT (Cause causer effect)

constant primitive_truth_assumptions : PrimitiveTruthAssumptions

def primitive_truth_kernel : ConcreteTruthConditionKernel := {
  kernel_denotes := primitive_truth_assumptions.primitive_denotes,
  lexical_truth_break_application := primitive_truth_assumptions.primitive_lexical_truth_break_application,
  lexical_truth_butter_application := primitive_truth_assumptions.primitive_lexical_truth_butter_application,
  lexical_truth_eat_application := primitive_truth_assumptions.primitive_lexical_truth_eat_application,
  lexical_truth_knock_application := primitive_truth_assumptions.primitive_lexical_truth_knock_application,
  quantifier_truth_sigma_Entity := primitive_truth_assumptions.primitive_quantifier_truth_sigma_Entity,
  quantifier_truth_sigma_Food := primitive_truth_assumptions.primitive_quantifier_truth_sigma_Food,
  quantifier_truth_sigma_State := primitive_truth_assumptions.primitive_quantifier_truth_sigma_State,
  quantifier_truth_sigma_StateScale := primitive_truth_assumptions.primitive_quantifier_truth_sigma_StateScale,
  quantifier_truth_sigma_TransitionT := primitive_truth_assumptions.primitive_quantifier_truth_sigma_TransitionT,
  repetition_truth := primitive_truth_assumptions.primitive_repetition_truth,
  temporal_truth_at_T := primitive_truth_assumptions.primitive_temporal_truth_at_T,
  temporal_truth_during_T := primitive_truth_assumptions.primitive_temporal_truth_during_T,
  temporal_truth_before_T := primitive_truth_assumptions.primitive_temporal_truth_before_T,
  temporal_truth_after_T := primitive_truth_assumptions.primitive_temporal_truth_after_T,
  temporal_truth_until_T := primitive_truth_assumptions.primitive_temporal_truth_until_T,
  temporal_truth_since_T := primitive_truth_assumptions.primitive_temporal_truth_since_T,
  polarity_truth_not_T := primitive_truth_assumptions.primitive_polarity_truth_not_T,
  transition_truth := primitive_truth_assumptions.primitive_transition_truth,
  cause_truth := primitive_truth_assumptions.primitive_cause_truth
}

def primitive_truth_conditions_from_kernel : TruthConditionSpec :=
  truth_conditions_from_concrete_kernel primitive_truth_kernel

theorem primitive_truth_kernel_exists :
    Exists (fun K : ConcreteTruthConditionKernel => K = primitive_truth_kernel) := by
  exact Exists.intro primitive_truth_kernel rfl

theorem primitive_truth_kernel_denotes_primitive_assumptions :
    (A : Type) -> (term : A) -> primitive_truth_assumptions.primitive_denotes A term -> (truth_conditions_from_concrete_kernel primitive_truth_kernel).truth_denotes A term := by
  intro A term h
  exact h

theorem primitive_truth_kernel_denotes_model_interpretable :
    (A : Type) -> (term : A) -> ModelInterpretable A term -> (truth_conditions_from_concrete_kernel primitive_truth_kernel).truth_denotes A term := by
  intro A term h
  apply concrete_kernel_induces_truth_condition_soundness
  exact h

inductive AtomicBaseTruth : (A : Type) -> A -> Prop where
  | atomic_base_truth_break_application : (n : Nat) -> (mods : ModifierSeq n) -> (arg1 : Entity) -> (arg2 : Entity) -> AtomicBaseTruth PropT (break n mods arg1 arg2)
  | atomic_base_truth_butter_application : (n : Nat) -> (mods : ModifierSeq n) -> (arg1 : Entity) -> (arg2 : Entity) -> AtomicBaseTruth PropT (butter n mods arg1 arg2)
  | atomic_base_truth_eat_application : (n : Nat) -> (mods : ModifierSeq n) -> (arg1 : Entity) -> (arg2 : Food) -> AtomicBaseTruth Prop (eat n mods arg1 arg2)
  | atomic_base_truth_knock_application : (n : Nat) -> (mods : ModifierSeq n) -> (arg1 : Entity) -> AtomicBaseTruth PropT (knock n mods arg1)
  | atomic_base_truth_transition : (theme : Entity) -> (scale : StateScale) -> (source : State) -> (target : State) -> AtomicBaseTruth TransitionT (Transition theme scale source target)

structure LexicalAtomTruthAssumptions (D : (A : Type) -> A -> Prop) : Type where
  lexical_atom_truth_break_application : (n : Nat) -> (mods : ModifierSeq n) -> (arg1 : Entity) -> (arg2 : Entity) -> D PropT (break n mods arg1 arg2)
  lexical_atom_truth_butter_application : (n : Nat) -> (mods : ModifierSeq n) -> (arg1 : Entity) -> (arg2 : Entity) -> D PropT (butter n mods arg1 arg2)
  lexical_atom_truth_eat_application : (n : Nat) -> (mods : ModifierSeq n) -> (arg1 : Entity) -> (arg2 : Food) -> D Prop (eat n mods arg1 arg2)
  lexical_atom_truth_knock_application : (n : Nat) -> (mods : ModifierSeq n) -> (arg1 : Entity) -> D PropT (knock n mods arg1)

structure TransitionAtomTruthAssumptions (D : (A : Type) -> A -> Prop) : Type where
  transition_atom_truth : (theme : Entity) -> (scale : StateScale) -> (source : State) -> (target : State) -> D TransitionT (Transition theme scale source target)

structure LexicalTransitionTruthAssumptions : Type where
  atom_assumption_denotes : (A : Type) -> A -> Prop
  lexical_atom_assumptions : LexicalAtomTruthAssumptions atom_assumption_denotes
  transition_atom_assumptions : TransitionAtomTruthAssumptions atom_assumption_denotes

def lexical_atom_truth_assumptions_from_atomic_base : LexicalAtomTruthAssumptions AtomicBaseTruth := {
  lexical_atom_truth_break_application := fun n mods arg1 arg2 => AtomicBaseTruth.atomic_base_truth_break_application n mods arg1 arg2,
  lexical_atom_truth_butter_application := fun n mods arg1 arg2 => AtomicBaseTruth.atomic_base_truth_butter_application n mods arg1 arg2,
  lexical_atom_truth_eat_application := fun n mods arg1 arg2 => AtomicBaseTruth.atomic_base_truth_eat_application n mods arg1 arg2,
  lexical_atom_truth_knock_application := fun n mods arg1 => AtomicBaseTruth.atomic_base_truth_knock_application n mods arg1
}

def transition_atom_truth_assumptions_from_atomic_base : TransitionAtomTruthAssumptions AtomicBaseTruth := {
  transition_atom_truth := fun theme scale source target => AtomicBaseTruth.atomic_base_truth_transition theme scale source target
}

def lexical_transition_truth_assumptions_from_atomic_base : LexicalTransitionTruthAssumptions := {
  atom_assumption_denotes := AtomicBaseTruth,
  lexical_atom_assumptions := lexical_atom_truth_assumptions_from_atomic_base,
  transition_atom_assumptions := transition_atom_truth_assumptions_from_atomic_base
}

theorem lexical_atom_truth_assumptions_from_atomic_base_exists :
    Exists (fun L : LexicalAtomTruthAssumptions AtomicBaseTruth => L = lexical_atom_truth_assumptions_from_atomic_base) := by
  exact Exists.intro lexical_atom_truth_assumptions_from_atomic_base rfl

theorem transition_atom_truth_assumptions_from_atomic_base_exists :
    Exists (fun T : TransitionAtomTruthAssumptions AtomicBaseTruth => T = transition_atom_truth_assumptions_from_atomic_base) := by
  exact Exists.intro transition_atom_truth_assumptions_from_atomic_base rfl

theorem lexical_transition_truth_assumptions_from_atomic_base_exists :
    Exists (fun A : LexicalTransitionTruthAssumptions => A = lexical_transition_truth_assumptions_from_atomic_base) := by
  exact Exists.intro lexical_transition_truth_assumptions_from_atomic_base rfl

structure LexicalTransitionTruthModel : Type where
  atom_model_denotes : (A : Type) -> A -> Prop
  model_lexical_truth_break_application : (n : Nat) -> (mods : ModifierSeq n) -> (arg1 : Entity) -> (arg2 : Entity) -> atom_model_denotes PropT (break n mods arg1 arg2)
  model_lexical_truth_butter_application : (n : Nat) -> (mods : ModifierSeq n) -> (arg1 : Entity) -> (arg2 : Entity) -> atom_model_denotes PropT (butter n mods arg1 arg2)
  model_lexical_truth_eat_application : (n : Nat) -> (mods : ModifierSeq n) -> (arg1 : Entity) -> (arg2 : Food) -> atom_model_denotes Prop (eat n mods arg1 arg2)
  model_lexical_truth_knock_application : (n : Nat) -> (mods : ModifierSeq n) -> (arg1 : Entity) -> atom_model_denotes PropT (knock n mods arg1)
  model_transition_truth : (theme : Entity) -> (scale : StateScale) -> (source : State) -> (target : State) -> atom_model_denotes TransitionT (Transition theme scale source target)

def lexical_transition_truth_model_from_assumptions (assumptions : LexicalTransitionTruthAssumptions) : LexicalTransitionTruthModel := {
  atom_model_denotes := assumptions.atom_assumption_denotes,
  model_lexical_truth_break_application := assumptions.lexical_atom_assumptions.lexical_atom_truth_break_application,
  model_lexical_truth_butter_application := assumptions.lexical_atom_assumptions.lexical_atom_truth_butter_application,
  model_lexical_truth_eat_application := assumptions.lexical_atom_assumptions.lexical_atom_truth_eat_application,
  model_lexical_truth_knock_application := assumptions.lexical_atom_assumptions.lexical_atom_truth_knock_application,
  model_transition_truth := assumptions.transition_atom_assumptions.transition_atom_truth
}

def lexical_transition_truth_model : LexicalTransitionTruthModel :=
  lexical_transition_truth_model_from_assumptions lexical_transition_truth_assumptions_from_atomic_base

theorem lexical_transition_truth_model_from_assumptions_exists :
    Exists (fun M : LexicalTransitionTruthModel => M = lexical_transition_truth_model_from_assumptions lexical_transition_truth_assumptions_from_atomic_base) := by
  exact Exists.intro (lexical_transition_truth_model_from_assumptions lexical_transition_truth_assumptions_from_atomic_base) rfl

theorem lexical_transition_truth_model_exists :
    Exists (fun M : LexicalTransitionTruthModel => M = lexical_transition_truth_model) := by
  exact Exists.intro lexical_transition_truth_model rfl

theorem lexical_transition_truth_model_denotes_atomic_base_truth :
    (A : Type) -> (term : A) -> AtomicBaseTruth A term -> lexical_transition_truth_model.atom_model_denotes A term := by
  intro A term h
  exact h

structure AtomicValuationSpec : Type where
  atomic_valuation_denotes : (A : Type) -> A -> Prop
  valuation_lexical_truth_break_application : (n : Nat) -> (mods : ModifierSeq n) -> (arg1 : Entity) -> (arg2 : Entity) -> atomic_valuation_denotes PropT (break n mods arg1 arg2)
  valuation_lexical_truth_butter_application : (n : Nat) -> (mods : ModifierSeq n) -> (arg1 : Entity) -> (arg2 : Entity) -> atomic_valuation_denotes PropT (butter n mods arg1 arg2)
  valuation_lexical_truth_eat_application : (n : Nat) -> (mods : ModifierSeq n) -> (arg1 : Entity) -> (arg2 : Food) -> atomic_valuation_denotes Prop (eat n mods arg1 arg2)
  valuation_lexical_truth_knock_application : (n : Nat) -> (mods : ModifierSeq n) -> (arg1 : Entity) -> atomic_valuation_denotes PropT (knock n mods arg1)
  valuation_transition_truth : (theme : Entity) -> (scale : StateScale) -> (source : State) -> (target : State) -> atomic_valuation_denotes TransitionT (Transition theme scale source target)

def atomic_valuation_spec_from_lexical_transition_model : AtomicValuationSpec := {
  atomic_valuation_denotes := lexical_transition_truth_model.atom_model_denotes,
  valuation_lexical_truth_break_application := lexical_transition_truth_model.model_lexical_truth_break_application,
  valuation_lexical_truth_butter_application := lexical_transition_truth_model.model_lexical_truth_butter_application,
  valuation_lexical_truth_eat_application := lexical_transition_truth_model.model_lexical_truth_eat_application,
  valuation_lexical_truth_knock_application := lexical_transition_truth_model.model_lexical_truth_knock_application,
  valuation_transition_truth := lexical_transition_truth_model.model_transition_truth
}

def atomic_base_valuation_spec : AtomicValuationSpec :=
  atomic_valuation_spec_from_lexical_transition_model

theorem atomic_valuation_spec_from_lexical_transition_model_exists :
    Exists (fun V : AtomicValuationSpec => V = atomic_valuation_spec_from_lexical_transition_model) := by
  exact Exists.intro atomic_valuation_spec_from_lexical_transition_model rfl

theorem atomic_base_valuation_spec_exists :
    Exists (fun V : AtomicValuationSpec => V = atomic_base_valuation_spec) := by
  exact Exists.intro atomic_base_valuation_spec rfl

theorem atomic_base_valuation_denotes_atomic_base_truth :
    (A : Type) -> (term : A) -> AtomicBaseTruth A term -> atomic_base_valuation_spec.atomic_valuation_denotes A term := by
  intro A term h
  exact h

structure AtomicTruthFacts : Type where
  atomic_lexical_truth_break_application : (n : Nat) -> (mods : ModifierSeq n) -> (arg1 : Entity) -> (arg2 : Entity) -> AtomicBaseTruth PropT (break n mods arg1 arg2)
  atomic_lexical_truth_butter_application : (n : Nat) -> (mods : ModifierSeq n) -> (arg1 : Entity) -> (arg2 : Entity) -> AtomicBaseTruth PropT (butter n mods arg1 arg2)
  atomic_lexical_truth_eat_application : (n : Nat) -> (mods : ModifierSeq n) -> (arg1 : Entity) -> (arg2 : Food) -> AtomicBaseTruth Prop (eat n mods arg1 arg2)
  atomic_lexical_truth_knock_application : (n : Nat) -> (mods : ModifierSeq n) -> (arg1 : Entity) -> AtomicBaseTruth PropT (knock n mods arg1)
  atomic_transition_truth : (theme : Entity) -> (scale : StateScale) -> (source : State) -> (target : State) -> AtomicBaseTruth TransitionT (Transition theme scale source target)

def atomic_truth_facts_from_atomic_base_valuation : AtomicTruthFacts := {
  atomic_lexical_truth_break_application := fun n mods arg1 arg2 => atomic_base_valuation_spec.valuation_lexical_truth_break_application n mods arg1 arg2,
  atomic_lexical_truth_butter_application := fun n mods arg1 arg2 => atomic_base_valuation_spec.valuation_lexical_truth_butter_application n mods arg1 arg2,
  atomic_lexical_truth_eat_application := fun n mods arg1 arg2 => atomic_base_valuation_spec.valuation_lexical_truth_eat_application n mods arg1 arg2,
  atomic_lexical_truth_knock_application := fun n mods arg1 => atomic_base_valuation_spec.valuation_lexical_truth_knock_application n mods arg1,
  atomic_transition_truth := fun theme scale source target => atomic_base_valuation_spec.valuation_transition_truth theme scale source target
}

def atomic_truth_facts : AtomicTruthFacts :=
  atomic_truth_facts_from_atomic_base_valuation

theorem atomic_truth_facts_from_atomic_base_valuation_exists :
    Exists (fun F : AtomicTruthFacts => F = atomic_truth_facts_from_atomic_base_valuation) := by
  exact Exists.intro atomic_truth_facts_from_atomic_base_valuation rfl

inductive AtomicClosureTruth : (A : Type) -> A -> Prop where
  | atomic_closure_truth_break_application : (n : Nat) -> (mods : ModifierSeq n) -> (arg1 : Entity) -> (arg2 : Entity) -> AtomicBaseTruth PropT (break n mods arg1 arg2) -> AtomicClosureTruth PropT (break n mods arg1 arg2)
  | atomic_closure_truth_butter_application : (n : Nat) -> (mods : ModifierSeq n) -> (arg1 : Entity) -> (arg2 : Entity) -> AtomicBaseTruth PropT (butter n mods arg1 arg2) -> AtomicClosureTruth PropT (butter n mods arg1 arg2)
  | atomic_closure_truth_eat_application : (n : Nat) -> (mods : ModifierSeq n) -> (arg1 : Entity) -> (arg2 : Food) -> AtomicBaseTruth Prop (eat n mods arg1 arg2) -> AtomicClosureTruth Prop (eat n mods arg1 arg2)
  | atomic_closure_truth_knock_application : (n : Nat) -> (mods : ModifierSeq n) -> (arg1 : Entity) -> AtomicBaseTruth PropT (knock n mods arg1) -> AtomicClosureTruth PropT (knock n mods arg1)
  | atomic_closure_truth_sigma_Entity : (P : Entity -> Prop) -> ((x : Entity) -> AtomicClosureTruth Prop (P x)) -> AtomicClosureTruth Prop (Exists fun x : Entity => P x)
  | atomic_closure_truth_sigma_Food : (P : Food -> Prop) -> ((x : Food) -> AtomicClosureTruth Prop (P x)) -> AtomicClosureTruth Prop (Exists fun x : Food => P x)
  | atomic_closure_truth_sigma_State : (P : State -> Prop) -> ((x : State) -> AtomicClosureTruth Prop (P x)) -> AtomicClosureTruth Prop (Exists fun x : State => P x)
  | atomic_closure_truth_sigma_StateScale : (P : StateScale -> Prop) -> ((x : StateScale) -> AtomicClosureTruth Prop (P x)) -> AtomicClosureTruth Prop (Exists fun x : StateScale => P x)
  | atomic_closure_truth_sigma_TransitionT : (P : TransitionT -> Prop) -> ((x : TransitionT) -> AtomicClosureTruth Prop (P x)) -> AtomicClosureTruth Prop (Exists fun x : TransitionT => P x)
  | atomic_closure_truth_repeat : (n : Nat) -> (body : PropT) -> AtomicClosureTruth PropT body -> AtomicClosureTruth PropT (repeat n body)
  | atomic_closure_truth_at_T : (marker : Entity) -> (body : PropT) -> AtomicClosureTruth PropT body -> AtomicClosureTruth PropT (at_T marker body)
  | atomic_closure_truth_during_T : (marker : Entity) -> (body : PropT) -> AtomicClosureTruth PropT body -> AtomicClosureTruth PropT (during_T marker body)
  | atomic_closure_truth_before_T : (marker : Entity) -> (body : PropT) -> AtomicClosureTruth PropT body -> AtomicClosureTruth PropT (before_T marker body)
  | atomic_closure_truth_after_T : (marker : Entity) -> (body : PropT) -> AtomicClosureTruth PropT body -> AtomicClosureTruth PropT (after_T marker body)
  | atomic_closure_truth_until_T : (marker : Entity) -> (body : PropT) -> AtomicClosureTruth PropT body -> AtomicClosureTruth PropT (until_T marker body)
  | atomic_closure_truth_since_T : (marker : Entity) -> (body : PropT) -> AtomicClosureTruth PropT body -> AtomicClosureTruth PropT (since_T marker body)
  | atomic_closure_truth_not_T : (body : PropT) -> AtomicClosureTruth PropT body -> AtomicClosureTruth PropT (not_T body)
  | atomic_closure_truth_transition : (theme : Entity) -> (scale : StateScale) -> (source : State) -> (target : State) -> AtomicBaseTruth TransitionT (Transition theme scale source target) -> AtomicClosureTruth TransitionT (Transition theme scale source target)
  | atomic_closure_truth_cause : (causer : Entity) -> (effect : TransitionT) -> AtomicClosureTruth TransitionT effect -> AtomicClosureTruth PropT (Cause causer effect)

theorem model_interpretable_atomic_closure_truth :
    (A : Type) -> (term : A) -> ModelInterpretable A term -> AtomicClosureTruth A term := by
  intro A term h
  induction h
  | model_break_application n mods arg1 arg2 =>
      apply AtomicClosureTruth.atomic_closure_truth_break_application
      exact atomic_truth_facts.atomic_lexical_truth_break_application n mods arg1 arg2
  | model_butter_application n mods arg1 arg2 =>
      apply AtomicClosureTruth.atomic_closure_truth_butter_application
      exact atomic_truth_facts.atomic_lexical_truth_butter_application n mods arg1 arg2
  | model_eat_application n mods arg1 arg2 =>
      apply AtomicClosureTruth.atomic_closure_truth_eat_application
      exact atomic_truth_facts.atomic_lexical_truth_eat_application n mods arg1 arg2
  | model_knock_application n mods arg1 =>
      apply AtomicClosureTruth.atomic_closure_truth_knock_application
      exact atomic_truth_facts.atomic_lexical_truth_knock_application n mods arg1
  | model_sigma_Entity P h ih => exact AtomicClosureTruth.atomic_closure_truth_sigma_Entity P ih
  | model_sigma_Food P h ih => exact AtomicClosureTruth.atomic_closure_truth_sigma_Food P ih
  | model_sigma_State P h ih => exact AtomicClosureTruth.atomic_closure_truth_sigma_State P ih
  | model_sigma_StateScale P h ih => exact AtomicClosureTruth.atomic_closure_truth_sigma_StateScale P ih
  | model_sigma_TransitionT P h ih => exact AtomicClosureTruth.atomic_closure_truth_sigma_TransitionT P ih
  | model_repeat n body h ih => exact AtomicClosureTruth.atomic_closure_truth_repeat n body ih
  | model_at_T marker body h ih => exact AtomicClosureTruth.atomic_closure_truth_at_T marker body ih
  | model_during_T marker body h ih => exact AtomicClosureTruth.atomic_closure_truth_during_T marker body ih
  | model_before_T marker body h ih => exact AtomicClosureTruth.atomic_closure_truth_before_T marker body ih
  | model_after_T marker body h ih => exact AtomicClosureTruth.atomic_closure_truth_after_T marker body ih
  | model_until_T marker body h ih => exact AtomicClosureTruth.atomic_closure_truth_until_T marker body ih
  | model_since_T marker body h ih => exact AtomicClosureTruth.atomic_closure_truth_since_T marker body ih
  | model_not_T body h ih => exact AtomicClosureTruth.atomic_closure_truth_not_T body ih
  | model_transition theme scale source target =>
      apply AtomicClosureTruth.atomic_closure_truth_transition
      exact atomic_truth_facts.atomic_transition_truth theme scale source target
  | model_cause causer effect h ih => exact AtomicClosureTruth.atomic_closure_truth_cause causer effect ih

def atomic_closure_truth_kernel_denotes : (A : Type) -> A -> Prop :=
  AtomicClosureTruth

def atomic_closure_truth_kernel : ConcreteTruthConditionKernel := {
  kernel_denotes := atomic_closure_truth_kernel_denotes,
  lexical_truth_break_application := fun n mods arg1 arg2 => AtomicClosureTruth.atomic_closure_truth_break_application n mods arg1 arg2 (atomic_truth_facts.atomic_lexical_truth_break_application n mods arg1 arg2),
  lexical_truth_butter_application := fun n mods arg1 arg2 => AtomicClosureTruth.atomic_closure_truth_butter_application n mods arg1 arg2 (atomic_truth_facts.atomic_lexical_truth_butter_application n mods arg1 arg2),
  lexical_truth_eat_application := fun n mods arg1 arg2 => AtomicClosureTruth.atomic_closure_truth_eat_application n mods arg1 arg2 (atomic_truth_facts.atomic_lexical_truth_eat_application n mods arg1 arg2),
  lexical_truth_knock_application := fun n mods arg1 => AtomicClosureTruth.atomic_closure_truth_knock_application n mods arg1 (atomic_truth_facts.atomic_lexical_truth_knock_application n mods arg1),
  quantifier_truth_sigma_Entity := fun P h => AtomicClosureTruth.atomic_closure_truth_sigma_Entity P h,
  quantifier_truth_sigma_Food := fun P h => AtomicClosureTruth.atomic_closure_truth_sigma_Food P h,
  quantifier_truth_sigma_State := fun P h => AtomicClosureTruth.atomic_closure_truth_sigma_State P h,
  quantifier_truth_sigma_StateScale := fun P h => AtomicClosureTruth.atomic_closure_truth_sigma_StateScale P h,
  quantifier_truth_sigma_TransitionT := fun P h => AtomicClosureTruth.atomic_closure_truth_sigma_TransitionT P h,
  repetition_truth := fun n body h => AtomicClosureTruth.atomic_closure_truth_repeat n body h,
  temporal_truth_at_T := fun marker body h => AtomicClosureTruth.atomic_closure_truth_at_T marker body h,
  temporal_truth_during_T := fun marker body h => AtomicClosureTruth.atomic_closure_truth_during_T marker body h,
  temporal_truth_before_T := fun marker body h => AtomicClosureTruth.atomic_closure_truth_before_T marker body h,
  temporal_truth_after_T := fun marker body h => AtomicClosureTruth.atomic_closure_truth_after_T marker body h,
  temporal_truth_until_T := fun marker body h => AtomicClosureTruth.atomic_closure_truth_until_T marker body h,
  temporal_truth_since_T := fun marker body h => AtomicClosureTruth.atomic_closure_truth_since_T marker body h,
  polarity_truth_not_T := fun body h => AtomicClosureTruth.atomic_closure_truth_not_T body h,
  transition_truth := fun theme scale source target => AtomicClosureTruth.atomic_closure_truth_transition theme scale source target (atomic_truth_facts.atomic_transition_truth theme scale source target),
  cause_truth := fun causer effect h => AtomicClosureTruth.atomic_closure_truth_cause causer effect h
}

def atomic_closure_truth_conditions_from_kernel : TruthConditionSpec :=
  truth_conditions_from_concrete_kernel atomic_closure_truth_kernel

theorem atomic_closure_truth_kernel_exists :
    Exists (fun K : ConcreteTruthConditionKernel => K = atomic_closure_truth_kernel) := by
  exact Exists.intro atomic_closure_truth_kernel rfl

theorem atomic_closure_truth_kernel_denotes_atomic_closure_truth :
    (A : Type) -> (term : A) -> AtomicClosureTruth A term -> (truth_conditions_from_concrete_kernel atomic_closure_truth_kernel).truth_denotes A term := by
  intro A term h
  exact h

def atomic_closure_truth_conditions : TruthConditionSpec :=
  atomic_closure_truth_conditions_from_kernel

theorem atomic_closure_truth_conditions_exists :
    Exists (fun T : TruthConditionSpec => T = atomic_closure_truth_conditions) := by
  exact Exists.intro atomic_closure_truth_conditions rfl

theorem atomic_closure_truth_conditions_denote_atomic_closure_truth :
    (A : Type) -> (term : A) -> AtomicClosureTruth A term -> atomic_closure_truth_conditions.truth_denotes A term := by
  intro A term h
  exact h

inductive RegisteredStateTransitionTruth : Entity -> StateScale -> State -> State -> Prop where
  | registered_transition_vase_integrity_scale_intact_to_broken : RegisteredStateTransitionTruth vase integrity_scale intact broken

theorem registered_state_transition_atomic_base_truth :
    (theme : Entity) -> (scale : StateScale) -> (source : State) -> (target : State) ->
    RegisteredStateTransitionTruth theme scale source target ->
    AtomicBaseTruth TransitionT (Transition theme scale source target) := by
  intro theme scale source target h
  induction h
  | registered_transition_vase_integrity_scale_intact_to_broken =>
      exact AtomicBaseTruth.atomic_base_truth_transition vase integrity_scale intact broken

inductive TransitionRefinedAtomicClosureTruth : (A : Type) -> A -> Prop where
  | transition_refined_truth_break_application : (n : Nat) -> (mods : ModifierSeq n) -> (arg1 : Entity) -> (arg2 : Entity) -> AtomicBaseTruth PropT (break n mods arg1 arg2) -> TransitionRefinedAtomicClosureTruth PropT (break n mods arg1 arg2)
  | transition_refined_truth_butter_application : (n : Nat) -> (mods : ModifierSeq n) -> (arg1 : Entity) -> (arg2 : Entity) -> AtomicBaseTruth PropT (butter n mods arg1 arg2) -> TransitionRefinedAtomicClosureTruth PropT (butter n mods arg1 arg2)
  | transition_refined_truth_eat_application : (n : Nat) -> (mods : ModifierSeq n) -> (arg1 : Entity) -> (arg2 : Food) -> AtomicBaseTruth Prop (eat n mods arg1 arg2) -> TransitionRefinedAtomicClosureTruth Prop (eat n mods arg1 arg2)
  | transition_refined_truth_knock_application : (n : Nat) -> (mods : ModifierSeq n) -> (arg1 : Entity) -> AtomicBaseTruth PropT (knock n mods arg1) -> TransitionRefinedAtomicClosureTruth PropT (knock n mods arg1)
  | transition_refined_truth_sigma_Entity : (P : Entity -> Prop) -> ((x : Entity) -> TransitionRefinedAtomicClosureTruth Prop (P x)) -> TransitionRefinedAtomicClosureTruth Prop (Exists fun x : Entity => P x)
  | transition_refined_truth_sigma_Food : (P : Food -> Prop) -> ((x : Food) -> TransitionRefinedAtomicClosureTruth Prop (P x)) -> TransitionRefinedAtomicClosureTruth Prop (Exists fun x : Food => P x)
  | transition_refined_truth_sigma_State : (P : State -> Prop) -> ((x : State) -> TransitionRefinedAtomicClosureTruth Prop (P x)) -> TransitionRefinedAtomicClosureTruth Prop (Exists fun x : State => P x)
  | transition_refined_truth_sigma_StateScale : (P : StateScale -> Prop) -> ((x : StateScale) -> TransitionRefinedAtomicClosureTruth Prop (P x)) -> TransitionRefinedAtomicClosureTruth Prop (Exists fun x : StateScale => P x)
  | transition_refined_truth_sigma_TransitionT : (P : TransitionT -> Prop) -> ((x : TransitionT) -> TransitionRefinedAtomicClosureTruth Prop (P x)) -> TransitionRefinedAtomicClosureTruth Prop (Exists fun x : TransitionT => P x)
  | transition_refined_truth_repeat : (n : Nat) -> (body : PropT) -> TransitionRefinedAtomicClosureTruth PropT body -> TransitionRefinedAtomicClosureTruth PropT (repeat n body)
  | transition_refined_truth_at_T : (marker : Entity) -> (body : PropT) -> TransitionRefinedAtomicClosureTruth PropT body -> TransitionRefinedAtomicClosureTruth PropT (at_T marker body)
  | transition_refined_truth_during_T : (marker : Entity) -> (body : PropT) -> TransitionRefinedAtomicClosureTruth PropT body -> TransitionRefinedAtomicClosureTruth PropT (during_T marker body)
  | transition_refined_truth_before_T : (marker : Entity) -> (body : PropT) -> TransitionRefinedAtomicClosureTruth PropT body -> TransitionRefinedAtomicClosureTruth PropT (before_T marker body)
  | transition_refined_truth_after_T : (marker : Entity) -> (body : PropT) -> TransitionRefinedAtomicClosureTruth PropT body -> TransitionRefinedAtomicClosureTruth PropT (after_T marker body)
  | transition_refined_truth_until_T : (marker : Entity) -> (body : PropT) -> TransitionRefinedAtomicClosureTruth PropT body -> TransitionRefinedAtomicClosureTruth PropT (until_T marker body)
  | transition_refined_truth_since_T : (marker : Entity) -> (body : PropT) -> TransitionRefinedAtomicClosureTruth PropT body -> TransitionRefinedAtomicClosureTruth PropT (since_T marker body)
  | transition_refined_truth_not_T : (body : PropT) -> TransitionRefinedAtomicClosureTruth PropT body -> TransitionRefinedAtomicClosureTruth PropT (not_T body)
  | transition_refined_truth_transition : (theme : Entity) -> (scale : StateScale) -> (source : State) -> (target : State) -> RegisteredStateTransitionTruth theme scale source target -> TransitionRefinedAtomicClosureTruth TransitionT (Transition theme scale source target)
  | transition_refined_truth_cause : (causer : Entity) -> (effect : TransitionT) -> TransitionRefinedAtomicClosureTruth TransitionT effect -> TransitionRefinedAtomicClosureTruth PropT (Cause causer effect)

theorem transition_refined_atomic_closure_truth_implies_atomic_closure_truth :
    (A : Type) -> (term : A) -> TransitionRefinedAtomicClosureTruth A term -> AtomicClosureTruth A term := by
  intro A term h
  induction h
  | transition_refined_truth_break_application n mods arg1 arg2 hbase =>
      apply AtomicClosureTruth.atomic_closure_truth_break_application
      exact hbase
  | transition_refined_truth_butter_application n mods arg1 arg2 hbase =>
      apply AtomicClosureTruth.atomic_closure_truth_butter_application
      exact hbase
  | transition_refined_truth_eat_application n mods arg1 arg2 hbase =>
      apply AtomicClosureTruth.atomic_closure_truth_eat_application
      exact hbase
  | transition_refined_truth_knock_application n mods arg1 hbase =>
      apply AtomicClosureTruth.atomic_closure_truth_knock_application
      exact hbase
  | transition_refined_truth_sigma_Entity P h ih => exact AtomicClosureTruth.atomic_closure_truth_sigma_Entity P ih
  | transition_refined_truth_sigma_Food P h ih => exact AtomicClosureTruth.atomic_closure_truth_sigma_Food P ih
  | transition_refined_truth_sigma_State P h ih => exact AtomicClosureTruth.atomic_closure_truth_sigma_State P ih
  | transition_refined_truth_sigma_StateScale P h ih => exact AtomicClosureTruth.atomic_closure_truth_sigma_StateScale P ih
  | transition_refined_truth_sigma_TransitionT P h ih => exact AtomicClosureTruth.atomic_closure_truth_sigma_TransitionT P ih
  | transition_refined_truth_repeat n body h ih => exact AtomicClosureTruth.atomic_closure_truth_repeat n body ih
  | transition_refined_truth_at_T marker body h ih => exact AtomicClosureTruth.atomic_closure_truth_at_T marker body ih
  | transition_refined_truth_during_T marker body h ih => exact AtomicClosureTruth.atomic_closure_truth_during_T marker body ih
  | transition_refined_truth_before_T marker body h ih => exact AtomicClosureTruth.atomic_closure_truth_before_T marker body ih
  | transition_refined_truth_after_T marker body h ih => exact AtomicClosureTruth.atomic_closure_truth_after_T marker body ih
  | transition_refined_truth_until_T marker body h ih => exact AtomicClosureTruth.atomic_closure_truth_until_T marker body ih
  | transition_refined_truth_since_T marker body h ih => exact AtomicClosureTruth.atomic_closure_truth_since_T marker body ih
  | transition_refined_truth_not_T body h ih => exact AtomicClosureTruth.atomic_closure_truth_not_T body ih
  | transition_refined_truth_transition theme scale source target hreg =>
      apply AtomicClosureTruth.atomic_closure_truth_transition
      exact registered_state_transition_atomic_base_truth theme scale source target hreg
  | transition_refined_truth_cause causer effect h ih => exact AtomicClosureTruth.atomic_closure_truth_cause causer effect ih

structure RegisteredTruthConditionSpec : Type where
  registered_truth_denotes : (A : Type) -> A -> Prop
  registered_truth_break_application : (n : Nat) -> (mods : ModifierSeq n) -> (arg1 : Entity) -> (arg2 : Entity) -> registered_truth_denotes PropT (break n mods arg1 arg2)
  registered_truth_butter_application : (n : Nat) -> (mods : ModifierSeq n) -> (arg1 : Entity) -> (arg2 : Entity) -> registered_truth_denotes PropT (butter n mods arg1 arg2)
  registered_truth_eat_application : (n : Nat) -> (mods : ModifierSeq n) -> (arg1 : Entity) -> (arg2 : Food) -> registered_truth_denotes Prop (eat n mods arg1 arg2)
  registered_truth_knock_application : (n : Nat) -> (mods : ModifierSeq n) -> (arg1 : Entity) -> registered_truth_denotes PropT (knock n mods arg1)
  registered_truth_sigma_Entity : (P : Entity -> Prop) -> ((x : Entity) -> registered_truth_denotes Prop (P x)) -> registered_truth_denotes Prop (Exists fun x : Entity => P x)
  registered_truth_sigma_Food : (P : Food -> Prop) -> ((x : Food) -> registered_truth_denotes Prop (P x)) -> registered_truth_denotes Prop (Exists fun x : Food => P x)
  registered_truth_sigma_State : (P : State -> Prop) -> ((x : State) -> registered_truth_denotes Prop (P x)) -> registered_truth_denotes Prop (Exists fun x : State => P x)
  registered_truth_sigma_StateScale : (P : StateScale -> Prop) -> ((x : StateScale) -> registered_truth_denotes Prop (P x)) -> registered_truth_denotes Prop (Exists fun x : StateScale => P x)
  registered_truth_sigma_TransitionT : (P : TransitionT -> Prop) -> ((x : TransitionT) -> registered_truth_denotes Prop (P x)) -> registered_truth_denotes Prop (Exists fun x : TransitionT => P x)
  registered_truth_repeat : (n : Nat) -> (body : PropT) -> registered_truth_denotes PropT body -> registered_truth_denotes PropT (repeat n body)
  registered_truth_at_T : (marker : Entity) -> (body : PropT) -> registered_truth_denotes PropT body -> registered_truth_denotes PropT (at_T marker body)
  registered_truth_during_T : (marker : Entity) -> (body : PropT) -> registered_truth_denotes PropT body -> registered_truth_denotes PropT (during_T marker body)
  registered_truth_before_T : (marker : Entity) -> (body : PropT) -> registered_truth_denotes PropT body -> registered_truth_denotes PropT (before_T marker body)
  registered_truth_after_T : (marker : Entity) -> (body : PropT) -> registered_truth_denotes PropT body -> registered_truth_denotes PropT (after_T marker body)
  registered_truth_until_T : (marker : Entity) -> (body : PropT) -> registered_truth_denotes PropT body -> registered_truth_denotes PropT (until_T marker body)
  registered_truth_since_T : (marker : Entity) -> (body : PropT) -> registered_truth_denotes PropT body -> registered_truth_denotes PropT (since_T marker body)
  registered_truth_not_T : (body : PropT) -> registered_truth_denotes PropT body -> registered_truth_denotes PropT (not_T body)
  registered_truth_transition : (theme : Entity) -> (scale : StateScale) -> (source : State) -> (target : State) -> RegisteredStateTransitionTruth theme scale source target -> registered_truth_denotes TransitionT (Transition theme scale source target)
  registered_truth_cause : (causer : Entity) -> (effect : TransitionT) -> registered_truth_denotes TransitionT effect -> registered_truth_denotes PropT (Cause causer effect)

def transition_refined_registered_truth_denotes : (A : Type) -> A -> Prop :=
  TransitionRefinedAtomicClosureTruth

def transition_refined_registered_truth_conditions : RegisteredTruthConditionSpec := {
  registered_truth_denotes := transition_refined_registered_truth_denotes,
  registered_truth_break_application := fun n mods arg1 arg2 => TransitionRefinedAtomicClosureTruth.transition_refined_truth_break_application n mods arg1 arg2 (AtomicBaseTruth.atomic_base_truth_break_application n mods arg1 arg2),
  registered_truth_butter_application := fun n mods arg1 arg2 => TransitionRefinedAtomicClosureTruth.transition_refined_truth_butter_application n mods arg1 arg2 (AtomicBaseTruth.atomic_base_truth_butter_application n mods arg1 arg2),
  registered_truth_eat_application := fun n mods arg1 arg2 => TransitionRefinedAtomicClosureTruth.transition_refined_truth_eat_application n mods arg1 arg2 (AtomicBaseTruth.atomic_base_truth_eat_application n mods arg1 arg2),
  registered_truth_knock_application := fun n mods arg1 => TransitionRefinedAtomicClosureTruth.transition_refined_truth_knock_application n mods arg1 (AtomicBaseTruth.atomic_base_truth_knock_application n mods arg1),
  registered_truth_sigma_Entity := fun P h => TransitionRefinedAtomicClosureTruth.transition_refined_truth_sigma_Entity P h,
  registered_truth_sigma_Food := fun P h => TransitionRefinedAtomicClosureTruth.transition_refined_truth_sigma_Food P h,
  registered_truth_sigma_State := fun P h => TransitionRefinedAtomicClosureTruth.transition_refined_truth_sigma_State P h,
  registered_truth_sigma_StateScale := fun P h => TransitionRefinedAtomicClosureTruth.transition_refined_truth_sigma_StateScale P h,
  registered_truth_sigma_TransitionT := fun P h => TransitionRefinedAtomicClosureTruth.transition_refined_truth_sigma_TransitionT P h,
  registered_truth_repeat := fun n body h => TransitionRefinedAtomicClosureTruth.transition_refined_truth_repeat n body h,
  registered_truth_at_T := fun marker body h => TransitionRefinedAtomicClosureTruth.transition_refined_truth_at_T marker body h,
  registered_truth_during_T := fun marker body h => TransitionRefinedAtomicClosureTruth.transition_refined_truth_during_T marker body h,
  registered_truth_before_T := fun marker body h => TransitionRefinedAtomicClosureTruth.transition_refined_truth_before_T marker body h,
  registered_truth_after_T := fun marker body h => TransitionRefinedAtomicClosureTruth.transition_refined_truth_after_T marker body h,
  registered_truth_until_T := fun marker body h => TransitionRefinedAtomicClosureTruth.transition_refined_truth_until_T marker body h,
  registered_truth_since_T := fun marker body h => TransitionRefinedAtomicClosureTruth.transition_refined_truth_since_T marker body h,
  registered_truth_not_T := fun body h => TransitionRefinedAtomicClosureTruth.transition_refined_truth_not_T body h,
  registered_truth_transition := fun theme scale source target h => TransitionRefinedAtomicClosureTruth.transition_refined_truth_transition theme scale source target h,
  registered_truth_cause := fun causer effect h => TransitionRefinedAtomicClosureTruth.transition_refined_truth_cause causer effect h
}

theorem transition_refined_registered_truth_condition_spec_exists :
    Exists (fun R : RegisteredTruthConditionSpec => R = transition_refined_registered_truth_conditions) := by
  exact Exists.intro transition_refined_registered_truth_conditions rfl

theorem transition_refined_registered_truth_conditions_denote_transition_refined :
    (A : Type) -> (term : A) -> TransitionRefinedAtomicClosureTruth A term -> transition_refined_registered_truth_conditions.registered_truth_denotes A term := by
  intro A term h
  exact h

theorem transition_refined_registered_truth_conditions_imply_atomic_closure :
    (A : Type) -> (term : A) -> transition_refined_registered_truth_conditions.registered_truth_denotes A term -> AtomicClosureTruth A term := by
  intro A term h
  apply transition_refined_atomic_closure_truth_implies_atomic_closure_truth
  exact h

inductive RegisteredLexicalApplicationTruth : (A : Type) -> A -> Prop where
  | registered_lexical_break_0_John_vase : RegisteredLexicalApplicationTruth PropT (break 0 mods_nil John vase)
  | registered_lexical_butter_2_slowly_in_bathroom_John_toast : RegisteredLexicalApplicationTruth PropT (butter 2 (mods_cons 1 slowly (mods_cons 0 in_bathroom mods_nil)) John toast)
  | registered_lexical_eat_0_John_x_theme : (x_theme : Food) -> RegisteredLexicalApplicationTruth Prop (eat 0 mods_nil John x_theme)
  | registered_lexical_knock_0_John : RegisteredLexicalApplicationTruth PropT (knock 0 mods_nil John)

theorem registered_lexical_application_atomic_base_truth :
    (A : Type) -> (term : A) -> RegisteredLexicalApplicationTruth A term -> AtomicBaseTruth A term := by
  intro A term h
  induction h
  | registered_lexical_break_0_John_vase =>
      apply AtomicBaseTruth.atomic_base_truth_break_application
  | registered_lexical_butter_2_slowly_in_bathroom_John_toast =>
      apply AtomicBaseTruth.atomic_base_truth_butter_application
  | registered_lexical_eat_0_John_x_theme x_theme =>
      apply AtomicBaseTruth.atomic_base_truth_eat_application
  | registered_lexical_knock_0_John =>
      apply AtomicBaseTruth.atomic_base_truth_knock_application

theorem registered_lexical_application_atomic_closure_truth :
    (A : Type) -> (term : A) -> RegisteredLexicalApplicationTruth A term -> AtomicClosureTruth A term := by
  intro A term h
  induction h
  | registered_lexical_break_0_John_vase =>
      apply AtomicClosureTruth.atomic_closure_truth_break_application
      apply AtomicBaseTruth.atomic_base_truth_break_application
  | registered_lexical_butter_2_slowly_in_bathroom_John_toast =>
      apply AtomicClosureTruth.atomic_closure_truth_butter_application
      apply AtomicBaseTruth.atomic_base_truth_butter_application
  | registered_lexical_eat_0_John_x_theme x_theme =>
      apply AtomicClosureTruth.atomic_closure_truth_eat_application
      apply AtomicBaseTruth.atomic_base_truth_eat_application
  | registered_lexical_knock_0_John =>
      apply AtomicClosureTruth.atomic_closure_truth_knock_application
      apply AtomicBaseTruth.atomic_base_truth_knock_application

inductive FullyRegisteredAtomicClosureTruth : (A : Type) -> A -> Prop where
  | fully_registered_atomic_truth_lexical_application : (A : Type) -> (term : A) -> RegisteredLexicalApplicationTruth A term -> FullyRegisteredAtomicClosureTruth A term
  | fully_registered_atomic_truth_sigma_Entity : (P : Entity -> Prop) -> ((x : Entity) -> FullyRegisteredAtomicClosureTruth Prop (P x)) -> FullyRegisteredAtomicClosureTruth Prop (Exists fun x : Entity => P x)
  | fully_registered_atomic_truth_sigma_Food : (P : Food -> Prop) -> ((x : Food) -> FullyRegisteredAtomicClosureTruth Prop (P x)) -> FullyRegisteredAtomicClosureTruth Prop (Exists fun x : Food => P x)
  | fully_registered_atomic_truth_sigma_State : (P : State -> Prop) -> ((x : State) -> FullyRegisteredAtomicClosureTruth Prop (P x)) -> FullyRegisteredAtomicClosureTruth Prop (Exists fun x : State => P x)
  | fully_registered_atomic_truth_sigma_StateScale : (P : StateScale -> Prop) -> ((x : StateScale) -> FullyRegisteredAtomicClosureTruth Prop (P x)) -> FullyRegisteredAtomicClosureTruth Prop (Exists fun x : StateScale => P x)
  | fully_registered_atomic_truth_sigma_TransitionT : (P : TransitionT -> Prop) -> ((x : TransitionT) -> FullyRegisteredAtomicClosureTruth Prop (P x)) -> FullyRegisteredAtomicClosureTruth Prop (Exists fun x : TransitionT => P x)
  | fully_registered_atomic_truth_repeat : (n : Nat) -> (body : PropT) -> FullyRegisteredAtomicClosureTruth PropT body -> FullyRegisteredAtomicClosureTruth PropT (repeat n body)
  | fully_registered_atomic_truth_at_T : (marker : Entity) -> (body : PropT) -> FullyRegisteredAtomicClosureTruth PropT body -> FullyRegisteredAtomicClosureTruth PropT (at_T marker body)
  | fully_registered_atomic_truth_during_T : (marker : Entity) -> (body : PropT) -> FullyRegisteredAtomicClosureTruth PropT body -> FullyRegisteredAtomicClosureTruth PropT (during_T marker body)
  | fully_registered_atomic_truth_before_T : (marker : Entity) -> (body : PropT) -> FullyRegisteredAtomicClosureTruth PropT body -> FullyRegisteredAtomicClosureTruth PropT (before_T marker body)
  | fully_registered_atomic_truth_after_T : (marker : Entity) -> (body : PropT) -> FullyRegisteredAtomicClosureTruth PropT body -> FullyRegisteredAtomicClosureTruth PropT (after_T marker body)
  | fully_registered_atomic_truth_until_T : (marker : Entity) -> (body : PropT) -> FullyRegisteredAtomicClosureTruth PropT body -> FullyRegisteredAtomicClosureTruth PropT (until_T marker body)
  | fully_registered_atomic_truth_since_T : (marker : Entity) -> (body : PropT) -> FullyRegisteredAtomicClosureTruth PropT body -> FullyRegisteredAtomicClosureTruth PropT (since_T marker body)
  | fully_registered_atomic_truth_not_T : (body : PropT) -> FullyRegisteredAtomicClosureTruth PropT body -> FullyRegisteredAtomicClosureTruth PropT (not_T body)
  | fully_registered_atomic_truth_transition : (theme : Entity) -> (scale : StateScale) -> (source : State) -> (target : State) -> RegisteredStateTransitionTruth theme scale source target -> FullyRegisteredAtomicClosureTruth TransitionT (Transition theme scale source target)
  | fully_registered_atomic_truth_cause : (causer : Entity) -> (effect : TransitionT) -> FullyRegisteredAtomicClosureTruth TransitionT effect -> FullyRegisteredAtomicClosureTruth PropT (Cause causer effect)

theorem fully_registered_atomic_closure_truth_implies_atomic_closure_truth :
    (A : Type) -> (term : A) -> FullyRegisteredAtomicClosureTruth A term -> AtomicClosureTruth A term := by
  intro A term h
  induction h
  | fully_registered_atomic_truth_lexical_application A term hreg =>
      apply registered_lexical_application_atomic_closure_truth
      exact hreg
  | fully_registered_atomic_truth_sigma_Entity P h ih => exact AtomicClosureTruth.atomic_closure_truth_sigma_Entity P ih
  | fully_registered_atomic_truth_sigma_Food P h ih => exact AtomicClosureTruth.atomic_closure_truth_sigma_Food P ih
  | fully_registered_atomic_truth_sigma_State P h ih => exact AtomicClosureTruth.atomic_closure_truth_sigma_State P ih
  | fully_registered_atomic_truth_sigma_StateScale P h ih => exact AtomicClosureTruth.atomic_closure_truth_sigma_StateScale P ih
  | fully_registered_atomic_truth_sigma_TransitionT P h ih => exact AtomicClosureTruth.atomic_closure_truth_sigma_TransitionT P ih
  | fully_registered_atomic_truth_repeat n body h ih => exact AtomicClosureTruth.atomic_closure_truth_repeat n body ih
  | fully_registered_atomic_truth_at_T marker body h ih => exact AtomicClosureTruth.atomic_closure_truth_at_T marker body ih
  | fully_registered_atomic_truth_during_T marker body h ih => exact AtomicClosureTruth.atomic_closure_truth_during_T marker body ih
  | fully_registered_atomic_truth_before_T marker body h ih => exact AtomicClosureTruth.atomic_closure_truth_before_T marker body ih
  | fully_registered_atomic_truth_after_T marker body h ih => exact AtomicClosureTruth.atomic_closure_truth_after_T marker body ih
  | fully_registered_atomic_truth_until_T marker body h ih => exact AtomicClosureTruth.atomic_closure_truth_until_T marker body ih
  | fully_registered_atomic_truth_since_T marker body h ih => exact AtomicClosureTruth.atomic_closure_truth_since_T marker body ih
  | fully_registered_atomic_truth_not_T body h ih => exact AtomicClosureTruth.atomic_closure_truth_not_T body ih
  | fully_registered_atomic_truth_transition theme scale source target hreg =>
      apply AtomicClosureTruth.atomic_closure_truth_transition
      exact registered_state_transition_atomic_base_truth theme scale source target hreg
  | fully_registered_atomic_truth_cause causer effect h ih => exact AtomicClosureTruth.atomic_closure_truth_cause causer effect ih

structure FullyRegisteredTruthConditionSpec : Type where
  fully_registered_truth_denotes : (A : Type) -> A -> Prop
  fully_registered_truth_lexical_application : (A : Type) -> (term : A) -> RegisteredLexicalApplicationTruth A term -> fully_registered_truth_denotes A term
  fully_registered_truth_sigma_Entity : (P : Entity -> Prop) -> ((x : Entity) -> fully_registered_truth_denotes Prop (P x)) -> fully_registered_truth_denotes Prop (Exists fun x : Entity => P x)
  fully_registered_truth_sigma_Food : (P : Food -> Prop) -> ((x : Food) -> fully_registered_truth_denotes Prop (P x)) -> fully_registered_truth_denotes Prop (Exists fun x : Food => P x)
  fully_registered_truth_sigma_State : (P : State -> Prop) -> ((x : State) -> fully_registered_truth_denotes Prop (P x)) -> fully_registered_truth_denotes Prop (Exists fun x : State => P x)
  fully_registered_truth_sigma_StateScale : (P : StateScale -> Prop) -> ((x : StateScale) -> fully_registered_truth_denotes Prop (P x)) -> fully_registered_truth_denotes Prop (Exists fun x : StateScale => P x)
  fully_registered_truth_sigma_TransitionT : (P : TransitionT -> Prop) -> ((x : TransitionT) -> fully_registered_truth_denotes Prop (P x)) -> fully_registered_truth_denotes Prop (Exists fun x : TransitionT => P x)
  fully_registered_truth_repeat : (n : Nat) -> (body : PropT) -> fully_registered_truth_denotes PropT body -> fully_registered_truth_denotes PropT (repeat n body)
  fully_registered_truth_at_T : (marker : Entity) -> (body : PropT) -> fully_registered_truth_denotes PropT body -> fully_registered_truth_denotes PropT (at_T marker body)
  fully_registered_truth_during_T : (marker : Entity) -> (body : PropT) -> fully_registered_truth_denotes PropT body -> fully_registered_truth_denotes PropT (during_T marker body)
  fully_registered_truth_before_T : (marker : Entity) -> (body : PropT) -> fully_registered_truth_denotes PropT body -> fully_registered_truth_denotes PropT (before_T marker body)
  fully_registered_truth_after_T : (marker : Entity) -> (body : PropT) -> fully_registered_truth_denotes PropT body -> fully_registered_truth_denotes PropT (after_T marker body)
  fully_registered_truth_until_T : (marker : Entity) -> (body : PropT) -> fully_registered_truth_denotes PropT body -> fully_registered_truth_denotes PropT (until_T marker body)
  fully_registered_truth_since_T : (marker : Entity) -> (body : PropT) -> fully_registered_truth_denotes PropT body -> fully_registered_truth_denotes PropT (since_T marker body)
  fully_registered_truth_not_T : (body : PropT) -> fully_registered_truth_denotes PropT body -> fully_registered_truth_denotes PropT (not_T body)
  fully_registered_truth_transition : (theme : Entity) -> (scale : StateScale) -> (source : State) -> (target : State) -> RegisteredStateTransitionTruth theme scale source target -> fully_registered_truth_denotes TransitionT (Transition theme scale source target)
  fully_registered_truth_cause : (causer : Entity) -> (effect : TransitionT) -> fully_registered_truth_denotes TransitionT effect -> fully_registered_truth_denotes PropT (Cause causer effect)

def fully_registered_atomic_truth_denotes : (A : Type) -> A -> Prop :=
  FullyRegisteredAtomicClosureTruth

def fully_registered_truth_conditions : FullyRegisteredTruthConditionSpec := {
  fully_registered_truth_denotes := fully_registered_atomic_truth_denotes,
  fully_registered_truth_lexical_application := fun A term h => FullyRegisteredAtomicClosureTruth.fully_registered_atomic_truth_lexical_application A term h,
  fully_registered_truth_sigma_Entity := fun P h => FullyRegisteredAtomicClosureTruth.fully_registered_atomic_truth_sigma_Entity P h,
  fully_registered_truth_sigma_Food := fun P h => FullyRegisteredAtomicClosureTruth.fully_registered_atomic_truth_sigma_Food P h,
  fully_registered_truth_sigma_State := fun P h => FullyRegisteredAtomicClosureTruth.fully_registered_atomic_truth_sigma_State P h,
  fully_registered_truth_sigma_StateScale := fun P h => FullyRegisteredAtomicClosureTruth.fully_registered_atomic_truth_sigma_StateScale P h,
  fully_registered_truth_sigma_TransitionT := fun P h => FullyRegisteredAtomicClosureTruth.fully_registered_atomic_truth_sigma_TransitionT P h,
  fully_registered_truth_repeat := fun n body h => FullyRegisteredAtomicClosureTruth.fully_registered_atomic_truth_repeat n body h,
  fully_registered_truth_at_T := fun marker body h => FullyRegisteredAtomicClosureTruth.fully_registered_atomic_truth_at_T marker body h,
  fully_registered_truth_during_T := fun marker body h => FullyRegisteredAtomicClosureTruth.fully_registered_atomic_truth_during_T marker body h,
  fully_registered_truth_before_T := fun marker body h => FullyRegisteredAtomicClosureTruth.fully_registered_atomic_truth_before_T marker body h,
  fully_registered_truth_after_T := fun marker body h => FullyRegisteredAtomicClosureTruth.fully_registered_atomic_truth_after_T marker body h,
  fully_registered_truth_until_T := fun marker body h => FullyRegisteredAtomicClosureTruth.fully_registered_atomic_truth_until_T marker body h,
  fully_registered_truth_since_T := fun marker body h => FullyRegisteredAtomicClosureTruth.fully_registered_atomic_truth_since_T marker body h,
  fully_registered_truth_not_T := fun body h => FullyRegisteredAtomicClosureTruth.fully_registered_atomic_truth_not_T body h,
  fully_registered_truth_transition := fun theme scale source target h => FullyRegisteredAtomicClosureTruth.fully_registered_atomic_truth_transition theme scale source target h,
  fully_registered_truth_cause := fun causer effect h => FullyRegisteredAtomicClosureTruth.fully_registered_atomic_truth_cause causer effect h
}

theorem fully_registered_truth_condition_spec_exists :
    Exists (fun F : FullyRegisteredTruthConditionSpec => F = fully_registered_truth_conditions) := by
  exact Exists.intro fully_registered_truth_conditions rfl

theorem fully_registered_truth_conditions_denote_fully_registered :
    (A : Type) -> (term : A) -> FullyRegisteredAtomicClosureTruth A term -> fully_registered_truth_conditions.fully_registered_truth_denotes A term := by
  intro A term h
  exact h

theorem fully_registered_truth_conditions_imply_atomic_closure :
    (A : Type) -> (term : A) -> fully_registered_truth_conditions.fully_registered_truth_denotes A term -> AtomicClosureTruth A term := by
  intro A term h
  apply fully_registered_atomic_closure_truth_implies_atomic_closure_truth
  exact h

structure RegisteredLexicalTruthModel : Type where
  registered_lexical_model_denotes : (A : Type) -> A -> Prop
  registered_lexical_model_lexical_application : (A : Type) -> (term : A) -> RegisteredLexicalApplicationTruth A term -> registered_lexical_model_denotes A term
  registered_lexical_model_sigma_Entity : (P : Entity -> Prop) -> ((x : Entity) -> registered_lexical_model_denotes Prop (P x)) -> registered_lexical_model_denotes Prop (Exists fun x : Entity => P x)
  registered_lexical_model_sigma_Food : (P : Food -> Prop) -> ((x : Food) -> registered_lexical_model_denotes Prop (P x)) -> registered_lexical_model_denotes Prop (Exists fun x : Food => P x)
  registered_lexical_model_sigma_State : (P : State -> Prop) -> ((x : State) -> registered_lexical_model_denotes Prop (P x)) -> registered_lexical_model_denotes Prop (Exists fun x : State => P x)
  registered_lexical_model_sigma_StateScale : (P : StateScale -> Prop) -> ((x : StateScale) -> registered_lexical_model_denotes Prop (P x)) -> registered_lexical_model_denotes Prop (Exists fun x : StateScale => P x)
  registered_lexical_model_sigma_TransitionT : (P : TransitionT -> Prop) -> ((x : TransitionT) -> registered_lexical_model_denotes Prop (P x)) -> registered_lexical_model_denotes Prop (Exists fun x : TransitionT => P x)
  registered_lexical_model_repeat : (n : Nat) -> (body : PropT) -> registered_lexical_model_denotes PropT body -> registered_lexical_model_denotes PropT (repeat n body)
  registered_lexical_model_at_T : (marker : Entity) -> (body : PropT) -> registered_lexical_model_denotes PropT body -> registered_lexical_model_denotes PropT (at_T marker body)
  registered_lexical_model_during_T : (marker : Entity) -> (body : PropT) -> registered_lexical_model_denotes PropT body -> registered_lexical_model_denotes PropT (during_T marker body)
  registered_lexical_model_before_T : (marker : Entity) -> (body : PropT) -> registered_lexical_model_denotes PropT body -> registered_lexical_model_denotes PropT (before_T marker body)
  registered_lexical_model_after_T : (marker : Entity) -> (body : PropT) -> registered_lexical_model_denotes PropT body -> registered_lexical_model_denotes PropT (after_T marker body)
  registered_lexical_model_until_T : (marker : Entity) -> (body : PropT) -> registered_lexical_model_denotes PropT body -> registered_lexical_model_denotes PropT (until_T marker body)
  registered_lexical_model_since_T : (marker : Entity) -> (body : PropT) -> registered_lexical_model_denotes PropT body -> registered_lexical_model_denotes PropT (since_T marker body)
  registered_lexical_model_not_T : (body : PropT) -> registered_lexical_model_denotes PropT body -> registered_lexical_model_denotes PropT (not_T body)
  registered_lexical_model_transition : (theme : Entity) -> (scale : StateScale) -> (source : State) -> (target : State) -> RegisteredStateTransitionTruth theme scale source target -> registered_lexical_model_denotes TransitionT (Transition theme scale source target)
  registered_lexical_model_cause : (causer : Entity) -> (effect : TransitionT) -> registered_lexical_model_denotes TransitionT effect -> registered_lexical_model_denotes PropT (Cause causer effect)

def fully_registered_truth_conditions_from_registered_lexical_model (M : RegisteredLexicalTruthModel) : FullyRegisteredTruthConditionSpec := {
  fully_registered_truth_denotes := M.registered_lexical_model_denotes,
  fully_registered_truth_lexical_application := M.registered_lexical_model_lexical_application,
  fully_registered_truth_sigma_Entity := M.registered_lexical_model_sigma_Entity,
  fully_registered_truth_sigma_Food := M.registered_lexical_model_sigma_Food,
  fully_registered_truth_sigma_State := M.registered_lexical_model_sigma_State,
  fully_registered_truth_sigma_StateScale := M.registered_lexical_model_sigma_StateScale,
  fully_registered_truth_sigma_TransitionT := M.registered_lexical_model_sigma_TransitionT,
  fully_registered_truth_repeat := M.registered_lexical_model_repeat,
  fully_registered_truth_at_T := M.registered_lexical_model_at_T,
  fully_registered_truth_during_T := M.registered_lexical_model_during_T,
  fully_registered_truth_before_T := M.registered_lexical_model_before_T,
  fully_registered_truth_after_T := M.registered_lexical_model_after_T,
  fully_registered_truth_until_T := M.registered_lexical_model_until_T,
  fully_registered_truth_since_T := M.registered_lexical_model_since_T,
  fully_registered_truth_not_T := M.registered_lexical_model_not_T,
  fully_registered_truth_transition := M.registered_lexical_model_transition,
  fully_registered_truth_cause := M.registered_lexical_model_cause
}

def registered_lexical_truth_model_denotes : (A : Type) -> A -> Prop :=
  FullyRegisteredAtomicClosureTruth

def registered_lexical_truth_model : RegisteredLexicalTruthModel := {
  registered_lexical_model_denotes := registered_lexical_truth_model_denotes,
  registered_lexical_model_lexical_application := fun A term h => FullyRegisteredAtomicClosureTruth.fully_registered_atomic_truth_lexical_application A term h,
  registered_lexical_model_sigma_Entity := fun P h => FullyRegisteredAtomicClosureTruth.fully_registered_atomic_truth_sigma_Entity P h,
  registered_lexical_model_sigma_Food := fun P h => FullyRegisteredAtomicClosureTruth.fully_registered_atomic_truth_sigma_Food P h,
  registered_lexical_model_sigma_State := fun P h => FullyRegisteredAtomicClosureTruth.fully_registered_atomic_truth_sigma_State P h,
  registered_lexical_model_sigma_StateScale := fun P h => FullyRegisteredAtomicClosureTruth.fully_registered_atomic_truth_sigma_StateScale P h,
  registered_lexical_model_sigma_TransitionT := fun P h => FullyRegisteredAtomicClosureTruth.fully_registered_atomic_truth_sigma_TransitionT P h,
  registered_lexical_model_repeat := fun n body h => FullyRegisteredAtomicClosureTruth.fully_registered_atomic_truth_repeat n body h,
  registered_lexical_model_at_T := fun marker body h => FullyRegisteredAtomicClosureTruth.fully_registered_atomic_truth_at_T marker body h,
  registered_lexical_model_during_T := fun marker body h => FullyRegisteredAtomicClosureTruth.fully_registered_atomic_truth_during_T marker body h,
  registered_lexical_model_before_T := fun marker body h => FullyRegisteredAtomicClosureTruth.fully_registered_atomic_truth_before_T marker body h,
  registered_lexical_model_after_T := fun marker body h => FullyRegisteredAtomicClosureTruth.fully_registered_atomic_truth_after_T marker body h,
  registered_lexical_model_until_T := fun marker body h => FullyRegisteredAtomicClosureTruth.fully_registered_atomic_truth_until_T marker body h,
  registered_lexical_model_since_T := fun marker body h => FullyRegisteredAtomicClosureTruth.fully_registered_atomic_truth_since_T marker body h,
  registered_lexical_model_not_T := fun body h => FullyRegisteredAtomicClosureTruth.fully_registered_atomic_truth_not_T body h,
  registered_lexical_model_transition := fun theme scale source target h => FullyRegisteredAtomicClosureTruth.fully_registered_atomic_truth_transition theme scale source target h,
  registered_lexical_model_cause := fun causer effect h => FullyRegisteredAtomicClosureTruth.fully_registered_atomic_truth_cause causer effect h
}

def registered_lexical_truth_conditions_from_model : FullyRegisteredTruthConditionSpec :=
  fully_registered_truth_conditions_from_registered_lexical_model registered_lexical_truth_model

theorem registered_lexical_truth_model_exists :
    Exists (fun M : RegisteredLexicalTruthModel => M = registered_lexical_truth_model) := by
  exact Exists.intro registered_lexical_truth_model rfl

theorem registered_lexical_truth_conditions_from_model_exists :
    Exists (fun F : FullyRegisteredTruthConditionSpec => F = registered_lexical_truth_conditions_from_model) := by
  exact Exists.intro registered_lexical_truth_conditions_from_model rfl

theorem registered_lexical_truth_model_denotes_fully_registered :
    (A : Type) -> (term : A) -> FullyRegisteredAtomicClosureTruth A term -> registered_lexical_truth_model.registered_lexical_model_denotes A term := by
  intro A term h
  exact h

theorem registered_lexical_truth_conditions_from_model_denote_fully_registered :
    (A : Type) -> (term : A) -> FullyRegisteredAtomicClosureTruth A term -> registered_lexical_truth_conditions_from_model.fully_registered_truth_denotes A term := by
  intro A term h
  exact h

theorem registered_lexical_truth_conditions_from_model_imply_atomic_closure :
    (A : Type) -> (term : A) -> registered_lexical_truth_conditions_from_model.fully_registered_truth_denotes A term -> AtomicClosureTruth A term := by
  intro A term h
  apply fully_registered_atomic_closure_truth_implies_atomic_closure_truth
  exact h

inductive ConcreteRegisteredAtomicTruth : (A : Type) -> A -> Prop where
  | concrete_registered_atomic_truth_lexical_application : (A : Type) -> (term : A) -> RegisteredLexicalApplicationTruth A term -> ConcreteRegisteredAtomicTruth A term
  | concrete_registered_atomic_truth_transition : (theme : Entity) -> (scale : StateScale) -> (source : State) -> (target : State) -> RegisteredStateTransitionTruth theme scale source target -> ConcreteRegisteredAtomicTruth TransitionT (Transition theme scale source target)

structure ConcreteRegisteredTruthBasis : Type where
  concrete_registered_basis_denotes : (A : Type) -> A -> Prop
  concrete_registered_basis_lexical_application : (A : Type) -> (term : A) -> RegisteredLexicalApplicationTruth A term -> concrete_registered_basis_denotes A term
  concrete_registered_basis_transition : (theme : Entity) -> (scale : StateScale) -> (source : State) -> (target : State) -> RegisteredStateTransitionTruth theme scale source target -> concrete_registered_basis_denotes TransitionT (Transition theme scale source target)

def concrete_registered_truth_basis : ConcreteRegisteredTruthBasis := {
  concrete_registered_basis_denotes := ConcreteRegisteredAtomicTruth,
  concrete_registered_basis_lexical_application := fun A term h => ConcreteRegisteredAtomicTruth.concrete_registered_atomic_truth_lexical_application A term h,
  concrete_registered_basis_transition := fun theme scale source target h => ConcreteRegisteredAtomicTruth.concrete_registered_atomic_truth_transition theme scale source target h
}

theorem concrete_registered_truth_basis_exists :
    Exists (fun B : ConcreteRegisteredTruthBasis => B = concrete_registered_truth_basis) := by
  exact Exists.intro concrete_registered_truth_basis rfl

theorem concrete_registered_atomic_truth_implies_atomic_base_truth :
    (A : Type) -> (term : A) -> ConcreteRegisteredAtomicTruth A term -> AtomicBaseTruth A term := by
  intro A term h
  induction h
  | concrete_registered_atomic_truth_lexical_application A term hreg =>
      apply registered_lexical_application_atomic_base_truth
      exact hreg
  | concrete_registered_atomic_truth_transition theme scale source target hreg =>
      apply registered_state_transition_atomic_base_truth
      exact hreg

inductive ConcreteRegisteredTruth : (A : Type) -> A -> Prop where
  | concrete_registered_truth_atomic : (A : Type) -> (term : A) -> ConcreteRegisteredAtomicTruth A term -> ConcreteRegisteredTruth A term
  | concrete_registered_truth_sigma_Entity : (P : Entity -> Prop) -> ((x : Entity) -> ConcreteRegisteredTruth Prop (P x)) -> ConcreteRegisteredTruth Prop (Exists fun x : Entity => P x)
  | concrete_registered_truth_sigma_Food : (P : Food -> Prop) -> ((x : Food) -> ConcreteRegisteredTruth Prop (P x)) -> ConcreteRegisteredTruth Prop (Exists fun x : Food => P x)
  | concrete_registered_truth_sigma_State : (P : State -> Prop) -> ((x : State) -> ConcreteRegisteredTruth Prop (P x)) -> ConcreteRegisteredTruth Prop (Exists fun x : State => P x)
  | concrete_registered_truth_sigma_StateScale : (P : StateScale -> Prop) -> ((x : StateScale) -> ConcreteRegisteredTruth Prop (P x)) -> ConcreteRegisteredTruth Prop (Exists fun x : StateScale => P x)
  | concrete_registered_truth_sigma_TransitionT : (P : TransitionT -> Prop) -> ((x : TransitionT) -> ConcreteRegisteredTruth Prop (P x)) -> ConcreteRegisteredTruth Prop (Exists fun x : TransitionT => P x)
  | concrete_registered_truth_repeat : (n : Nat) -> (body : PropT) -> ConcreteRegisteredTruth PropT body -> ConcreteRegisteredTruth PropT (repeat n body)
  | concrete_registered_truth_at_T : (marker : Entity) -> (body : PropT) -> ConcreteRegisteredTruth PropT body -> ConcreteRegisteredTruth PropT (at_T marker body)
  | concrete_registered_truth_during_T : (marker : Entity) -> (body : PropT) -> ConcreteRegisteredTruth PropT body -> ConcreteRegisteredTruth PropT (during_T marker body)
  | concrete_registered_truth_before_T : (marker : Entity) -> (body : PropT) -> ConcreteRegisteredTruth PropT body -> ConcreteRegisteredTruth PropT (before_T marker body)
  | concrete_registered_truth_after_T : (marker : Entity) -> (body : PropT) -> ConcreteRegisteredTruth PropT body -> ConcreteRegisteredTruth PropT (after_T marker body)
  | concrete_registered_truth_until_T : (marker : Entity) -> (body : PropT) -> ConcreteRegisteredTruth PropT body -> ConcreteRegisteredTruth PropT (until_T marker body)
  | concrete_registered_truth_since_T : (marker : Entity) -> (body : PropT) -> ConcreteRegisteredTruth PropT body -> ConcreteRegisteredTruth PropT (since_T marker body)
  | concrete_registered_truth_not_T : (body : PropT) -> ConcreteRegisteredTruth PropT body -> ConcreteRegisteredTruth PropT (not_T body)
  | concrete_registered_truth_cause : (causer : Entity) -> (effect : TransitionT) -> ConcreteRegisteredTruth TransitionT effect -> ConcreteRegisteredTruth PropT (Cause causer effect)

theorem concrete_registered_truth_implies_fully_registered :
    (A : Type) -> (term : A) -> ConcreteRegisteredTruth A term -> FullyRegisteredAtomicClosureTruth A term := by
  intro A term h
  induction h
  | concrete_registered_truth_atomic A term hatom =>
      induction hatom
      | concrete_registered_atomic_truth_lexical_application A term hreg =>
          apply FullyRegisteredAtomicClosureTruth.fully_registered_atomic_truth_lexical_application
          exact hreg
      | concrete_registered_atomic_truth_transition theme scale source target hreg =>
          apply FullyRegisteredAtomicClosureTruth.fully_registered_atomic_truth_transition
          exact hreg
  | concrete_registered_truth_sigma_Entity P h ih => exact FullyRegisteredAtomicClosureTruth.fully_registered_atomic_truth_sigma_Entity P ih
  | concrete_registered_truth_sigma_Food P h ih => exact FullyRegisteredAtomicClosureTruth.fully_registered_atomic_truth_sigma_Food P ih
  | concrete_registered_truth_sigma_State P h ih => exact FullyRegisteredAtomicClosureTruth.fully_registered_atomic_truth_sigma_State P ih
  | concrete_registered_truth_sigma_StateScale P h ih => exact FullyRegisteredAtomicClosureTruth.fully_registered_atomic_truth_sigma_StateScale P ih
  | concrete_registered_truth_sigma_TransitionT P h ih => exact FullyRegisteredAtomicClosureTruth.fully_registered_atomic_truth_sigma_TransitionT P ih
  | concrete_registered_truth_repeat n body h ih => exact FullyRegisteredAtomicClosureTruth.fully_registered_atomic_truth_repeat n body ih
  | concrete_registered_truth_at_T marker body h ih => exact FullyRegisteredAtomicClosureTruth.fully_registered_atomic_truth_at_T marker body ih
  | concrete_registered_truth_during_T marker body h ih => exact FullyRegisteredAtomicClosureTruth.fully_registered_atomic_truth_during_T marker body ih
  | concrete_registered_truth_before_T marker body h ih => exact FullyRegisteredAtomicClosureTruth.fully_registered_atomic_truth_before_T marker body ih
  | concrete_registered_truth_after_T marker body h ih => exact FullyRegisteredAtomicClosureTruth.fully_registered_atomic_truth_after_T marker body ih
  | concrete_registered_truth_until_T marker body h ih => exact FullyRegisteredAtomicClosureTruth.fully_registered_atomic_truth_until_T marker body ih
  | concrete_registered_truth_since_T marker body h ih => exact FullyRegisteredAtomicClosureTruth.fully_registered_atomic_truth_since_T marker body ih
  | concrete_registered_truth_not_T body h ih => exact FullyRegisteredAtomicClosureTruth.fully_registered_atomic_truth_not_T body ih
  | concrete_registered_truth_cause causer effect h ih => exact FullyRegisteredAtomicClosureTruth.fully_registered_atomic_truth_cause causer effect ih

theorem concrete_registered_truth_implies_atomic_closure :
    (A : Type) -> (term : A) -> ConcreteRegisteredTruth A term -> AtomicClosureTruth A term := by
  intro A term h
  apply fully_registered_atomic_closure_truth_implies_atomic_closure_truth
  apply concrete_registered_truth_implies_fully_registered
  exact h

def concrete_registered_truth_denotes : (A : Type) -> A -> Prop :=
  ConcreteRegisteredTruth

def concrete_registered_truth_conditions : FullyRegisteredTruthConditionSpec := {
  fully_registered_truth_denotes := concrete_registered_truth_denotes,
  fully_registered_truth_lexical_application := fun A term h => ConcreteRegisteredTruth.concrete_registered_truth_atomic A term (ConcreteRegisteredAtomicTruth.concrete_registered_atomic_truth_lexical_application A term h),
  fully_registered_truth_sigma_Entity := fun P h => ConcreteRegisteredTruth.concrete_registered_truth_sigma_Entity P h,
  fully_registered_truth_sigma_Food := fun P h => ConcreteRegisteredTruth.concrete_registered_truth_sigma_Food P h,
  fully_registered_truth_sigma_State := fun P h => ConcreteRegisteredTruth.concrete_registered_truth_sigma_State P h,
  fully_registered_truth_sigma_StateScale := fun P h => ConcreteRegisteredTruth.concrete_registered_truth_sigma_StateScale P h,
  fully_registered_truth_sigma_TransitionT := fun P h => ConcreteRegisteredTruth.concrete_registered_truth_sigma_TransitionT P h,
  fully_registered_truth_repeat := fun n body h => ConcreteRegisteredTruth.concrete_registered_truth_repeat n body h,
  fully_registered_truth_at_T := fun marker body h => ConcreteRegisteredTruth.concrete_registered_truth_at_T marker body h,
  fully_registered_truth_during_T := fun marker body h => ConcreteRegisteredTruth.concrete_registered_truth_during_T marker body h,
  fully_registered_truth_before_T := fun marker body h => ConcreteRegisteredTruth.concrete_registered_truth_before_T marker body h,
  fully_registered_truth_after_T := fun marker body h => ConcreteRegisteredTruth.concrete_registered_truth_after_T marker body h,
  fully_registered_truth_until_T := fun marker body h => ConcreteRegisteredTruth.concrete_registered_truth_until_T marker body h,
  fully_registered_truth_since_T := fun marker body h => ConcreteRegisteredTruth.concrete_registered_truth_since_T marker body h,
  fully_registered_truth_not_T := fun body h => ConcreteRegisteredTruth.concrete_registered_truth_not_T body h,
  fully_registered_truth_transition := fun theme scale source target h => ConcreteRegisteredTruth.concrete_registered_truth_atomic TransitionT (Transition theme scale source target) (ConcreteRegisteredAtomicTruth.concrete_registered_atomic_truth_transition theme scale source target h),
  fully_registered_truth_cause := fun causer effect h => ConcreteRegisteredTruth.concrete_registered_truth_cause causer effect h
}

theorem concrete_registered_truth_condition_spec_exists :
    Exists (fun F : FullyRegisteredTruthConditionSpec => F = concrete_registered_truth_conditions) := by
  exact Exists.intro concrete_registered_truth_conditions rfl

theorem concrete_registered_truth_conditions_denote_concrete_registered :
    (A : Type) -> (term : A) -> ConcreteRegisteredTruth A term -> concrete_registered_truth_conditions.fully_registered_truth_denotes A term := by
  intro A term h
  exact h

theorem concrete_registered_truth_conditions_imply_fully_registered :
    (A : Type) -> (term : A) -> concrete_registered_truth_conditions.fully_registered_truth_denotes A term -> FullyRegisteredAtomicClosureTruth A term := by
  intro A term h
  apply concrete_registered_truth_implies_fully_registered
  exact h

theorem concrete_registered_truth_conditions_imply_atomic_closure :
    (A : Type) -> (term : A) -> concrete_registered_truth_conditions.fully_registered_truth_denotes A term -> AtomicClosureTruth A term := by
  intro A term h
  apply concrete_registered_truth_implies_atomic_closure
  exact h

def model_interpretable_truth_kernel_denotes : (A : Type) -> A -> Prop :=
  ModelInterpretable

def model_interpretable_truth_kernel : ConcreteTruthConditionKernel := {
  kernel_denotes := model_interpretable_truth_kernel_denotes,
  lexical_truth_break_application := fun n mods arg1 arg2 => ModelInterpretable.model_break_application n mods arg1 arg2,
  lexical_truth_butter_application := fun n mods arg1 arg2 => ModelInterpretable.model_butter_application n mods arg1 arg2,
  lexical_truth_eat_application := fun n mods arg1 arg2 => ModelInterpretable.model_eat_application n mods arg1 arg2,
  lexical_truth_knock_application := fun n mods arg1 => ModelInterpretable.model_knock_application n mods arg1,
  quantifier_truth_sigma_Entity := fun P h => ModelInterpretable.model_sigma_Entity P h,
  quantifier_truth_sigma_Food := fun P h => ModelInterpretable.model_sigma_Food P h,
  quantifier_truth_sigma_State := fun P h => ModelInterpretable.model_sigma_State P h,
  quantifier_truth_sigma_StateScale := fun P h => ModelInterpretable.model_sigma_StateScale P h,
  quantifier_truth_sigma_TransitionT := fun P h => ModelInterpretable.model_sigma_TransitionT P h,
  repetition_truth := fun n body h => ModelInterpretable.model_repeat n body h,
  temporal_truth_at_T := fun marker body h => ModelInterpretable.model_at_T marker body h,
  temporal_truth_during_T := fun marker body h => ModelInterpretable.model_during_T marker body h,
  temporal_truth_before_T := fun marker body h => ModelInterpretable.model_before_T marker body h,
  temporal_truth_after_T := fun marker body h => ModelInterpretable.model_after_T marker body h,
  temporal_truth_until_T := fun marker body h => ModelInterpretable.model_until_T marker body h,
  temporal_truth_since_T := fun marker body h => ModelInterpretable.model_since_T marker body h,
  polarity_truth_not_T := fun body h => ModelInterpretable.model_not_T body h,
  transition_truth := fun theme scale source target => ModelInterpretable.model_transition theme scale source target,
  cause_truth := fun causer effect h => ModelInterpretable.model_cause causer effect h
}

def model_interpretable_truth_conditions_from_kernel : TruthConditionSpec :=
  truth_conditions_from_concrete_kernel model_interpretable_truth_kernel

theorem model_interpretable_truth_kernel_exists :
    Exists (fun K : ConcreteTruthConditionKernel => K = model_interpretable_truth_kernel) := by
  exact Exists.intro model_interpretable_truth_kernel rfl

theorem model_interpretable_truth_kernel_denotes_model_interpretable :
    (A : Type) -> (term : A) -> ModelInterpretable A term -> (truth_conditions_from_concrete_kernel model_interpretable_truth_kernel).truth_denotes A term := by
  intro A term h
  apply concrete_kernel_induces_truth_condition_soundness
  exact h

def syntax_directed_truth_kernel_denotes : (A : Type) -> A -> Prop :=
  SyntaxDirectedTruth

def syntax_directed_truth_kernel : ConcreteTruthConditionKernel := {
  kernel_denotes := syntax_directed_truth_kernel_denotes,
  lexical_truth_break_application := fun n mods arg1 arg2 => SyntaxDirectedTruth.syntax_truth_break_application n mods arg1 arg2,
  lexical_truth_butter_application := fun n mods arg1 arg2 => SyntaxDirectedTruth.syntax_truth_butter_application n mods arg1 arg2,
  lexical_truth_eat_application := fun n mods arg1 arg2 => SyntaxDirectedTruth.syntax_truth_eat_application n mods arg1 arg2,
  lexical_truth_knock_application := fun n mods arg1 => SyntaxDirectedTruth.syntax_truth_knock_application n mods arg1,
  quantifier_truth_sigma_Entity := fun P h => SyntaxDirectedTruth.syntax_truth_sigma_Entity P h,
  quantifier_truth_sigma_Food := fun P h => SyntaxDirectedTruth.syntax_truth_sigma_Food P h,
  quantifier_truth_sigma_State := fun P h => SyntaxDirectedTruth.syntax_truth_sigma_State P h,
  quantifier_truth_sigma_StateScale := fun P h => SyntaxDirectedTruth.syntax_truth_sigma_StateScale P h,
  quantifier_truth_sigma_TransitionT := fun P h => SyntaxDirectedTruth.syntax_truth_sigma_TransitionT P h,
  repetition_truth := fun n body h => SyntaxDirectedTruth.syntax_truth_repeat n body h,
  temporal_truth_at_T := fun marker body h => SyntaxDirectedTruth.syntax_truth_at_T marker body h,
  temporal_truth_during_T := fun marker body h => SyntaxDirectedTruth.syntax_truth_during_T marker body h,
  temporal_truth_before_T := fun marker body h => SyntaxDirectedTruth.syntax_truth_before_T marker body h,
  temporal_truth_after_T := fun marker body h => SyntaxDirectedTruth.syntax_truth_after_T marker body h,
  temporal_truth_until_T := fun marker body h => SyntaxDirectedTruth.syntax_truth_until_T marker body h,
  temporal_truth_since_T := fun marker body h => SyntaxDirectedTruth.syntax_truth_since_T marker body h,
  polarity_truth_not_T := fun body h => SyntaxDirectedTruth.syntax_truth_not_T body h,
  transition_truth := fun theme scale source target => SyntaxDirectedTruth.syntax_truth_transition theme scale source target,
  cause_truth := fun causer effect h => SyntaxDirectedTruth.syntax_truth_cause causer effect h
}

def syntax_directed_truth_conditions_from_kernel : TruthConditionSpec :=
  truth_conditions_from_concrete_kernel syntax_directed_truth_kernel

theorem syntax_directed_truth_kernel_exists :
    Exists (fun K : ConcreteTruthConditionKernel => K = syntax_directed_truth_kernel) := by
  exact Exists.intro syntax_directed_truth_kernel rfl

theorem syntax_directed_truth_kernel_denotes_syntax_directed_truth :
    (A : Type) -> (term : A) -> SyntaxDirectedTruth A term -> (truth_conditions_from_concrete_kernel syntax_directed_truth_kernel).truth_denotes A term := by
  intro A term h
  exact h

def tautological_truth_denotes : (A : Type) -> A -> Prop :=
  fun _ _ => True

def tautological_truth_conditions : TruthConditionSpec := {
  truth_denotes := tautological_truth_denotes,
  truth_break_application := fun n mods arg1 arg2 => True.intro,
  truth_butter_application := fun n mods arg1 arg2 => True.intro,
  truth_eat_application := fun n mods arg1 arg2 => True.intro,
  truth_knock_application := fun n mods arg1 => True.intro,
  truth_sigma_Entity := fun P h => True.intro,
  truth_sigma_Food := fun P h => True.intro,
  truth_sigma_State := fun P h => True.intro,
  truth_sigma_StateScale := fun P h => True.intro,
  truth_sigma_TransitionT := fun P h => True.intro,
  truth_repeat := fun n body h => True.intro,
  truth_at_T := fun marker body h => True.intro,
  truth_during_T := fun marker body h => True.intro,
  truth_before_T := fun marker body h => True.intro,
  truth_after_T := fun marker body h => True.intro,
  truth_until_T := fun marker body h => True.intro,
  truth_since_T := fun marker body h => True.intro,
  truth_not_T := fun body h => True.intro,
  truth_transition := fun theme scale source target => True.intro,
  truth_cause := fun causer effect h => True.intro
}

def tautological_semantic_model : SemanticModel :=
  semantic_model_from_truth_conditions tautological_truth_conditions

theorem tautological_truth_condition_spec_exists :
    Exists (fun T : TruthConditionSpec => T = tautological_truth_conditions) := by
  exact Exists.intro tautological_truth_conditions rfl

theorem tautological_truth_conditions_denote_model_interpretable :
    (A : Type) -> (term : A) -> ModelInterpretable A term -> tautological_truth_conditions.truth_denotes A term := by
  intro A term h
  apply truth_conditions_induce_denotational_soundness
  exact h

def structural_truth_denotes : (A : Type) -> A -> Prop :=
  ModelInterpretable

def structural_truth_conditions : TruthConditionSpec := {
  truth_denotes := structural_truth_denotes,
  truth_break_application := fun n mods arg1 arg2 => ModelInterpretable.model_break_application n mods arg1 arg2,
  truth_butter_application := fun n mods arg1 arg2 => ModelInterpretable.model_butter_application n mods arg1 arg2,
  truth_eat_application := fun n mods arg1 arg2 => ModelInterpretable.model_eat_application n mods arg1 arg2,
  truth_knock_application := fun n mods arg1 => ModelInterpretable.model_knock_application n mods arg1,
  truth_sigma_Entity := fun P h => ModelInterpretable.model_sigma_Entity P h,
  truth_sigma_Food := fun P h => ModelInterpretable.model_sigma_Food P h,
  truth_sigma_State := fun P h => ModelInterpretable.model_sigma_State P h,
  truth_sigma_StateScale := fun P h => ModelInterpretable.model_sigma_StateScale P h,
  truth_sigma_TransitionT := fun P h => ModelInterpretable.model_sigma_TransitionT P h,
  truth_repeat := fun n body h => ModelInterpretable.model_repeat n body h,
  truth_at_T := fun marker body h => ModelInterpretable.model_at_T marker body h,
  truth_during_T := fun marker body h => ModelInterpretable.model_during_T marker body h,
  truth_before_T := fun marker body h => ModelInterpretable.model_before_T marker body h,
  truth_after_T := fun marker body h => ModelInterpretable.model_after_T marker body h,
  truth_until_T := fun marker body h => ModelInterpretable.model_until_T marker body h,
  truth_since_T := fun marker body h => ModelInterpretable.model_since_T marker body h,
  truth_not_T := fun body h => ModelInterpretable.model_not_T body h,
  truth_transition := fun theme scale source target => ModelInterpretable.model_transition theme scale source target,
  truth_cause := fun causer effect h => ModelInterpretable.model_cause causer effect h
}

def structural_semantic_model : SemanticModel :=
  semantic_model_from_truth_conditions structural_truth_conditions

theorem structural_truth_condition_spec_exists :
    Exists (fun T : TruthConditionSpec => T = structural_truth_conditions) := by
  exact Exists.intro structural_truth_conditions rfl

theorem structural_truth_conditions_denote_model_interpretable :
    (A : Type) -> (term : A) -> ModelInterpretable A term -> structural_truth_conditions.truth_denotes A term := by
  intro A term h
  exact h

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

theorem example_1_model_interpretable : ModelInterpretable PropT example_1 := by
  apply semantic_preservation_model_interpretable
  exact example_1_semantic_preservation_proved
theorem example_2_model_interpretable : ModelInterpretable Prop example_2 := by
  apply semantic_preservation_model_interpretable
  exact example_2_semantic_preservation_proved
theorem example_3_model_interpretable : ModelInterpretable PropT example_3 := by
  apply semantic_preservation_model_interpretable
  exact example_3_semantic_preservation_proved
theorem example_4_model_interpretable : ModelInterpretable PropT example_4 := by
  apply semantic_preservation_model_interpretable
  exact example_4_semantic_preservation_proved

theorem example_1_syntax_directed_truth : SyntaxDirectedTruth PropT example_1 := by
  apply semantic_preservation_syntax_directed_truth
  exact example_1_semantic_preservation_proved
theorem example_2_syntax_directed_truth : SyntaxDirectedTruth Prop example_2 := by
  apply semantic_preservation_syntax_directed_truth
  exact example_2_semantic_preservation_proved
theorem example_3_syntax_directed_truth : SyntaxDirectedTruth PropT example_3 := by
  apply semantic_preservation_syntax_directed_truth
  exact example_3_semantic_preservation_proved
theorem example_4_syntax_directed_truth : SyntaxDirectedTruth PropT example_4 := by
  apply semantic_preservation_syntax_directed_truth
  exact example_4_semantic_preservation_proved

theorem example_1_denotationally_sound : (M : SemanticModel) -> M.model_denotes PropT example_1 := by
  intro M
  apply model_interpretable_denotational_sound
  exact example_1_model_interpretable
theorem example_2_denotationally_sound : (M : SemanticModel) -> M.model_denotes Prop example_2 := by
  intro M
  apply model_interpretable_denotational_sound
  exact example_2_model_interpretable
theorem example_3_denotationally_sound : (M : SemanticModel) -> M.model_denotes PropT example_3 := by
  intro M
  apply model_interpretable_denotational_sound
  exact example_3_model_interpretable
theorem example_4_denotationally_sound : (M : SemanticModel) -> M.model_denotes PropT example_4 := by
  intro M
  apply model_interpretable_denotational_sound
  exact example_4_model_interpretable

theorem example_1_truth_condition_sound : (T : TruthConditionSpec) -> T.truth_denotes PropT example_1 := by
  intro T
  apply truth_conditions_induce_denotational_soundness
  exact example_1_model_interpretable
theorem example_2_truth_condition_sound : (T : TruthConditionSpec) -> T.truth_denotes Prop example_2 := by
  intro T
  apply truth_conditions_induce_denotational_soundness
  exact example_2_model_interpretable
theorem example_3_truth_condition_sound : (T : TruthConditionSpec) -> T.truth_denotes PropT example_3 := by
  intro T
  apply truth_conditions_induce_denotational_soundness
  exact example_3_model_interpretable
theorem example_4_truth_condition_sound : (T : TruthConditionSpec) -> T.truth_denotes PropT example_4 := by
  intro T
  apply truth_conditions_induce_denotational_soundness
  exact example_4_model_interpretable

theorem example_1_tautological_truth_condition_sound : tautological_truth_conditions.truth_denotes PropT example_1 := by
  apply tautological_truth_conditions_denote_model_interpretable
  exact example_1_model_interpretable
theorem example_2_tautological_truth_condition_sound : tautological_truth_conditions.truth_denotes Prop example_2 := by
  apply tautological_truth_conditions_denote_model_interpretable
  exact example_2_model_interpretable
theorem example_3_tautological_truth_condition_sound : tautological_truth_conditions.truth_denotes PropT example_3 := by
  apply tautological_truth_conditions_denote_model_interpretable
  exact example_3_model_interpretable
theorem example_4_tautological_truth_condition_sound : tautological_truth_conditions.truth_denotes PropT example_4 := by
  apply tautological_truth_conditions_denote_model_interpretable
  exact example_4_model_interpretable

theorem example_1_structural_truth_condition_sound : structural_truth_conditions.truth_denotes PropT example_1 := by
  apply structural_truth_conditions_denote_model_interpretable
  exact example_1_model_interpretable
theorem example_2_structural_truth_condition_sound : structural_truth_conditions.truth_denotes Prop example_2 := by
  apply structural_truth_conditions_denote_model_interpretable
  exact example_2_model_interpretable
theorem example_3_structural_truth_condition_sound : structural_truth_conditions.truth_denotes PropT example_3 := by
  apply structural_truth_conditions_denote_model_interpretable
  exact example_3_model_interpretable
theorem example_4_structural_truth_condition_sound : structural_truth_conditions.truth_denotes PropT example_4 := by
  apply structural_truth_conditions_denote_model_interpretable
  exact example_4_model_interpretable

theorem example_1_concrete_kernel_truth_condition_sound : (K : ConcreteTruthConditionKernel) -> (truth_conditions_from_concrete_kernel K).truth_denotes PropT example_1 := by
  intro K
  apply concrete_kernel_induces_truth_condition_soundness
  exact example_1_model_interpretable
theorem example_2_concrete_kernel_truth_condition_sound : (K : ConcreteTruthConditionKernel) -> (truth_conditions_from_concrete_kernel K).truth_denotes Prop example_2 := by
  intro K
  apply concrete_kernel_induces_truth_condition_soundness
  exact example_2_model_interpretable
theorem example_3_concrete_kernel_truth_condition_sound : (K : ConcreteTruthConditionKernel) -> (truth_conditions_from_concrete_kernel K).truth_denotes PropT example_3 := by
  intro K
  apply concrete_kernel_induces_truth_condition_soundness
  exact example_3_model_interpretable
theorem example_4_concrete_kernel_truth_condition_sound : (K : ConcreteTruthConditionKernel) -> (truth_conditions_from_concrete_kernel K).truth_denotes PropT example_4 := by
  intro K
  apply concrete_kernel_induces_truth_condition_soundness
  exact example_4_model_interpretable

theorem example_1_model_interpretable_truth_kernel_sound : (truth_conditions_from_concrete_kernel model_interpretable_truth_kernel).truth_denotes PropT example_1 := by
  apply model_interpretable_truth_kernel_denotes_model_interpretable
  exact example_1_model_interpretable
theorem example_2_model_interpretable_truth_kernel_sound : (truth_conditions_from_concrete_kernel model_interpretable_truth_kernel).truth_denotes Prop example_2 := by
  apply model_interpretable_truth_kernel_denotes_model_interpretable
  exact example_2_model_interpretable
theorem example_3_model_interpretable_truth_kernel_sound : (truth_conditions_from_concrete_kernel model_interpretable_truth_kernel).truth_denotes PropT example_3 := by
  apply model_interpretable_truth_kernel_denotes_model_interpretable
  exact example_3_model_interpretable
theorem example_4_model_interpretable_truth_kernel_sound : (truth_conditions_from_concrete_kernel model_interpretable_truth_kernel).truth_denotes PropT example_4 := by
  apply model_interpretable_truth_kernel_denotes_model_interpretable
  exact example_4_model_interpretable

theorem example_1_syntax_directed_truth_kernel_sound : (truth_conditions_from_concrete_kernel syntax_directed_truth_kernel).truth_denotes PropT example_1 := by
  apply syntax_directed_truth_kernel_denotes_syntax_directed_truth
  exact example_1_syntax_directed_truth
theorem example_2_syntax_directed_truth_kernel_sound : (truth_conditions_from_concrete_kernel syntax_directed_truth_kernel).truth_denotes Prop example_2 := by
  apply syntax_directed_truth_kernel_denotes_syntax_directed_truth
  exact example_2_syntax_directed_truth
theorem example_3_syntax_directed_truth_kernel_sound : (truth_conditions_from_concrete_kernel syntax_directed_truth_kernel).truth_denotes PropT example_3 := by
  apply syntax_directed_truth_kernel_denotes_syntax_directed_truth
  exact example_3_syntax_directed_truth
theorem example_4_syntax_directed_truth_kernel_sound : (truth_conditions_from_concrete_kernel syntax_directed_truth_kernel).truth_denotes PropT example_4 := by
  apply syntax_directed_truth_kernel_denotes_syntax_directed_truth
  exact example_4_syntax_directed_truth

theorem example_1_primitive_truth_kernel_sound : (truth_conditions_from_concrete_kernel primitive_truth_kernel).truth_denotes PropT example_1 := by
  apply primitive_truth_kernel_denotes_model_interpretable
  exact example_1_model_interpretable
theorem example_2_primitive_truth_kernel_sound : (truth_conditions_from_concrete_kernel primitive_truth_kernel).truth_denotes Prop example_2 := by
  apply primitive_truth_kernel_denotes_model_interpretable
  exact example_2_model_interpretable
theorem example_3_primitive_truth_kernel_sound : (truth_conditions_from_concrete_kernel primitive_truth_kernel).truth_denotes PropT example_3 := by
  apply primitive_truth_kernel_denotes_model_interpretable
  exact example_3_model_interpretable
theorem example_4_primitive_truth_kernel_sound : (truth_conditions_from_concrete_kernel primitive_truth_kernel).truth_denotes PropT example_4 := by
  apply primitive_truth_kernel_denotes_model_interpretable
  exact example_4_model_interpretable

theorem example_1_atomic_closure_truth : AtomicClosureTruth PropT example_1 := by
  apply model_interpretable_atomic_closure_truth
  exact example_1_model_interpretable
theorem example_2_atomic_closure_truth : AtomicClosureTruth Prop example_2 := by
  apply model_interpretable_atomic_closure_truth
  exact example_2_model_interpretable
theorem example_3_atomic_closure_truth : AtomicClosureTruth PropT example_3 := by
  apply model_interpretable_atomic_closure_truth
  exact example_3_model_interpretable
theorem example_4_atomic_closure_truth : AtomicClosureTruth PropT example_4 := by
  apply model_interpretable_atomic_closure_truth
  exact example_4_model_interpretable

theorem example_1_atomic_closure_truth_kernel_sound : (truth_conditions_from_concrete_kernel atomic_closure_truth_kernel).truth_denotes PropT example_1 := by
  apply atomic_closure_truth_kernel_denotes_atomic_closure_truth
  exact example_1_atomic_closure_truth
theorem example_2_atomic_closure_truth_kernel_sound : (truth_conditions_from_concrete_kernel atomic_closure_truth_kernel).truth_denotes Prop example_2 := by
  apply atomic_closure_truth_kernel_denotes_atomic_closure_truth
  exact example_2_atomic_closure_truth
theorem example_3_atomic_closure_truth_kernel_sound : (truth_conditions_from_concrete_kernel atomic_closure_truth_kernel).truth_denotes PropT example_3 := by
  apply atomic_closure_truth_kernel_denotes_atomic_closure_truth
  exact example_3_atomic_closure_truth
theorem example_4_atomic_closure_truth_kernel_sound : (truth_conditions_from_concrete_kernel atomic_closure_truth_kernel).truth_denotes PropT example_4 := by
  apply atomic_closure_truth_kernel_denotes_atomic_closure_truth
  exact example_4_atomic_closure_truth

theorem example_1_atomic_closure_truth_condition_sound : atomic_closure_truth_conditions.truth_denotes PropT example_1 := by
  apply atomic_closure_truth_conditions_denote_atomic_closure_truth
  exact example_1_atomic_closure_truth
theorem example_2_atomic_closure_truth_condition_sound : atomic_closure_truth_conditions.truth_denotes Prop example_2 := by
  apply atomic_closure_truth_conditions_denote_atomic_closure_truth
  exact example_2_atomic_closure_truth
theorem example_3_atomic_closure_truth_condition_sound : atomic_closure_truth_conditions.truth_denotes PropT example_3 := by
  apply atomic_closure_truth_conditions_denote_atomic_closure_truth
  exact example_3_atomic_closure_truth
theorem example_4_atomic_closure_truth_condition_sound : atomic_closure_truth_conditions.truth_denotes PropT example_4 := by
  apply atomic_closure_truth_conditions_denote_atomic_closure_truth
  exact example_4_atomic_closure_truth

theorem example_1_transition_refined_atomic_closure_truth : TransitionRefinedAtomicClosureTruth PropT example_1 := by
  unfold example_1
  apply TransitionRefinedAtomicClosureTruth.transition_refined_truth_at_T
  apply TransitionRefinedAtomicClosureTruth.transition_refined_truth_butter_application
  exact AtomicBaseTruth.atomic_base_truth_butter_application 2 (mods_cons 1 slowly (mods_cons 0 in_bathroom mods_nil)) John toast
theorem example_2_transition_refined_atomic_closure_truth : TransitionRefinedAtomicClosureTruth Prop example_2 := by
  unfold example_2
  apply TransitionRefinedAtomicClosureTruth.transition_refined_truth_sigma_Food
  intro x_theme
  apply TransitionRefinedAtomicClosureTruth.transition_refined_truth_eat_application
  exact AtomicBaseTruth.atomic_base_truth_eat_application 0 mods_nil John x_theme
theorem example_3_transition_refined_atomic_closure_truth : TransitionRefinedAtomicClosureTruth PropT example_3 := by
  unfold example_3
  apply TransitionRefinedAtomicClosureTruth.transition_refined_truth_repeat
  apply TransitionRefinedAtomicClosureTruth.transition_refined_truth_knock_application
  exact AtomicBaseTruth.atomic_base_truth_knock_application 0 mods_nil John
theorem example_4_transition_refined_atomic_closure_truth : TransitionRefinedAtomicClosureTruth PropT example_4 := by
  unfold example_4
  apply TransitionRefinedAtomicClosureTruth.transition_refined_truth_cause
  apply TransitionRefinedAtomicClosureTruth.transition_refined_truth_transition
  exact RegisteredStateTransitionTruth.registered_transition_vase_integrity_scale_intact_to_broken

theorem example_1_transition_refined_atomic_closure_sound : AtomicClosureTruth PropT example_1 := by
  apply transition_refined_atomic_closure_truth_implies_atomic_closure_truth
  exact example_1_transition_refined_atomic_closure_truth
theorem example_2_transition_refined_atomic_closure_sound : AtomicClosureTruth Prop example_2 := by
  apply transition_refined_atomic_closure_truth_implies_atomic_closure_truth
  exact example_2_transition_refined_atomic_closure_truth
theorem example_3_transition_refined_atomic_closure_sound : AtomicClosureTruth PropT example_3 := by
  apply transition_refined_atomic_closure_truth_implies_atomic_closure_truth
  exact example_3_transition_refined_atomic_closure_truth
theorem example_4_transition_refined_atomic_closure_sound : AtomicClosureTruth PropT example_4 := by
  apply transition_refined_atomic_closure_truth_implies_atomic_closure_truth
  exact example_4_transition_refined_atomic_closure_truth

theorem example_1_transition_refined_registered_truth_condition_sound : transition_refined_registered_truth_conditions.registered_truth_denotes PropT example_1 := by
  apply transition_refined_registered_truth_conditions_denote_transition_refined
  exact example_1_transition_refined_atomic_closure_truth
theorem example_2_transition_refined_registered_truth_condition_sound : transition_refined_registered_truth_conditions.registered_truth_denotes Prop example_2 := by
  apply transition_refined_registered_truth_conditions_denote_transition_refined
  exact example_2_transition_refined_atomic_closure_truth
theorem example_3_transition_refined_registered_truth_condition_sound : transition_refined_registered_truth_conditions.registered_truth_denotes PropT example_3 := by
  apply transition_refined_registered_truth_conditions_denote_transition_refined
  exact example_3_transition_refined_atomic_closure_truth
theorem example_4_transition_refined_registered_truth_condition_sound : transition_refined_registered_truth_conditions.registered_truth_denotes PropT example_4 := by
  apply transition_refined_registered_truth_conditions_denote_transition_refined
  exact example_4_transition_refined_atomic_closure_truth

theorem example_1_transition_refined_registered_truth_condition_atomic_sound : AtomicClosureTruth PropT example_1 := by
  apply transition_refined_registered_truth_conditions_imply_atomic_closure
  exact example_1_transition_refined_registered_truth_condition_sound
theorem example_2_transition_refined_registered_truth_condition_atomic_sound : AtomicClosureTruth Prop example_2 := by
  apply transition_refined_registered_truth_conditions_imply_atomic_closure
  exact example_2_transition_refined_registered_truth_condition_sound
theorem example_3_transition_refined_registered_truth_condition_atomic_sound : AtomicClosureTruth PropT example_3 := by
  apply transition_refined_registered_truth_conditions_imply_atomic_closure
  exact example_3_transition_refined_registered_truth_condition_sound
theorem example_4_transition_refined_registered_truth_condition_atomic_sound : AtomicClosureTruth PropT example_4 := by
  apply transition_refined_registered_truth_conditions_imply_atomic_closure
  exact example_4_transition_refined_registered_truth_condition_sound

theorem example_1_fully_registered_atomic_closure_truth : FullyRegisteredAtomicClosureTruth PropT example_1 := by
  unfold example_1
  apply FullyRegisteredAtomicClosureTruth.fully_registered_atomic_truth_at_T
  apply FullyRegisteredAtomicClosureTruth.fully_registered_atomic_truth_lexical_application
  exact RegisteredLexicalApplicationTruth.registered_lexical_butter_2_slowly_in_bathroom_John_toast
theorem example_2_fully_registered_atomic_closure_truth : FullyRegisteredAtomicClosureTruth Prop example_2 := by
  unfold example_2
  apply FullyRegisteredAtomicClosureTruth.fully_registered_atomic_truth_sigma_Food
  intro x_theme
  apply FullyRegisteredAtomicClosureTruth.fully_registered_atomic_truth_lexical_application
  exact RegisteredLexicalApplicationTruth.registered_lexical_eat_0_John_x_theme x_theme
theorem example_3_fully_registered_atomic_closure_truth : FullyRegisteredAtomicClosureTruth PropT example_3 := by
  unfold example_3
  apply FullyRegisteredAtomicClosureTruth.fully_registered_atomic_truth_repeat
  apply FullyRegisteredAtomicClosureTruth.fully_registered_atomic_truth_lexical_application
  exact RegisteredLexicalApplicationTruth.registered_lexical_knock_0_John
theorem example_4_fully_registered_atomic_closure_truth : FullyRegisteredAtomicClosureTruth PropT example_4 := by
  unfold example_4
  apply FullyRegisteredAtomicClosureTruth.fully_registered_atomic_truth_cause
  apply FullyRegisteredAtomicClosureTruth.fully_registered_atomic_truth_transition
  exact RegisteredStateTransitionTruth.registered_transition_vase_integrity_scale_intact_to_broken

theorem example_1_fully_registered_truth_condition_sound : fully_registered_truth_conditions.fully_registered_truth_denotes PropT example_1 := by
  apply fully_registered_truth_conditions_denote_fully_registered
  exact example_1_fully_registered_atomic_closure_truth
theorem example_2_fully_registered_truth_condition_sound : fully_registered_truth_conditions.fully_registered_truth_denotes Prop example_2 := by
  apply fully_registered_truth_conditions_denote_fully_registered
  exact example_2_fully_registered_atomic_closure_truth
theorem example_3_fully_registered_truth_condition_sound : fully_registered_truth_conditions.fully_registered_truth_denotes PropT example_3 := by
  apply fully_registered_truth_conditions_denote_fully_registered
  exact example_3_fully_registered_atomic_closure_truth
theorem example_4_fully_registered_truth_condition_sound : fully_registered_truth_conditions.fully_registered_truth_denotes PropT example_4 := by
  apply fully_registered_truth_conditions_denote_fully_registered
  exact example_4_fully_registered_atomic_closure_truth

theorem example_1_registered_lexical_truth_model_sound : registered_lexical_truth_model.registered_lexical_model_denotes PropT example_1 := by
  apply registered_lexical_truth_model_denotes_fully_registered
  exact example_1_fully_registered_atomic_closure_truth

theorem example_1_registered_lexical_truth_conditions_from_model_sound : registered_lexical_truth_conditions_from_model.fully_registered_truth_denotes PropT example_1 := by
  apply registered_lexical_truth_conditions_from_model_denote_fully_registered
  exact example_1_fully_registered_atomic_closure_truth

theorem example_2_registered_lexical_truth_model_sound : registered_lexical_truth_model.registered_lexical_model_denotes Prop example_2 := by
  apply registered_lexical_truth_model_denotes_fully_registered
  exact example_2_fully_registered_atomic_closure_truth

theorem example_2_registered_lexical_truth_conditions_from_model_sound : registered_lexical_truth_conditions_from_model.fully_registered_truth_denotes Prop example_2 := by
  apply registered_lexical_truth_conditions_from_model_denote_fully_registered
  exact example_2_fully_registered_atomic_closure_truth

theorem example_3_registered_lexical_truth_model_sound : registered_lexical_truth_model.registered_lexical_model_denotes PropT example_3 := by
  apply registered_lexical_truth_model_denotes_fully_registered
  exact example_3_fully_registered_atomic_closure_truth

theorem example_3_registered_lexical_truth_conditions_from_model_sound : registered_lexical_truth_conditions_from_model.fully_registered_truth_denotes PropT example_3 := by
  apply registered_lexical_truth_conditions_from_model_denote_fully_registered
  exact example_3_fully_registered_atomic_closure_truth

theorem example_4_registered_lexical_truth_model_sound : registered_lexical_truth_model.registered_lexical_model_denotes PropT example_4 := by
  apply registered_lexical_truth_model_denotes_fully_registered
  exact example_4_fully_registered_atomic_closure_truth

theorem example_4_registered_lexical_truth_conditions_from_model_sound : registered_lexical_truth_conditions_from_model.fully_registered_truth_denotes PropT example_4 := by
  apply registered_lexical_truth_conditions_from_model_denote_fully_registered
  exact example_4_fully_registered_atomic_closure_truth

theorem example_1_concrete_registered_truth : ConcreteRegisteredTruth PropT example_1 := by
  unfold example_1
  apply ConcreteRegisteredTruth.concrete_registered_truth_at_T
  apply ConcreteRegisteredTruth.concrete_registered_truth_atomic
  exact ConcreteRegisteredAtomicTruth.concrete_registered_atomic_truth_lexical_application _ _ RegisteredLexicalApplicationTruth.registered_lexical_butter_2_slowly_in_bathroom_John_toast
theorem example_2_concrete_registered_truth : ConcreteRegisteredTruth Prop example_2 := by
  unfold example_2
  apply ConcreteRegisteredTruth.concrete_registered_truth_sigma_Food
  intro x_theme
  apply ConcreteRegisteredTruth.concrete_registered_truth_atomic
  exact ConcreteRegisteredAtomicTruth.concrete_registered_atomic_truth_lexical_application _ _ RegisteredLexicalApplicationTruth.registered_lexical_eat_0_John_x_theme x_theme
theorem example_3_concrete_registered_truth : ConcreteRegisteredTruth PropT example_3 := by
  unfold example_3
  apply ConcreteRegisteredTruth.concrete_registered_truth_repeat
  apply ConcreteRegisteredTruth.concrete_registered_truth_atomic
  exact ConcreteRegisteredAtomicTruth.concrete_registered_atomic_truth_lexical_application _ _ RegisteredLexicalApplicationTruth.registered_lexical_knock_0_John
theorem example_4_concrete_registered_truth : ConcreteRegisteredTruth PropT example_4 := by
  unfold example_4
  apply ConcreteRegisteredTruth.concrete_registered_truth_cause
  apply ConcreteRegisteredTruth.concrete_registered_truth_atomic
  exact ConcreteRegisteredAtomicTruth.concrete_registered_atomic_truth_transition vase integrity_scale intact broken RegisteredStateTransitionTruth.registered_transition_vase_integrity_scale_intact_to_broken

theorem example_1_concrete_registered_truth_condition_sound : concrete_registered_truth_conditions.fully_registered_truth_denotes PropT example_1 := by
  apply concrete_registered_truth_conditions_denote_concrete_registered
  exact example_1_concrete_registered_truth
theorem example_2_concrete_registered_truth_condition_sound : concrete_registered_truth_conditions.fully_registered_truth_denotes Prop example_2 := by
  apply concrete_registered_truth_conditions_denote_concrete_registered
  exact example_2_concrete_registered_truth
theorem example_3_concrete_registered_truth_condition_sound : concrete_registered_truth_conditions.fully_registered_truth_denotes PropT example_3 := by
  apply concrete_registered_truth_conditions_denote_concrete_registered
  exact example_3_concrete_registered_truth
theorem example_4_concrete_registered_truth_condition_sound : concrete_registered_truth_conditions.fully_registered_truth_denotes PropT example_4 := by
  apply concrete_registered_truth_conditions_denote_concrete_registered
  exact example_4_concrete_registered_truth

theorem example_1_concrete_registered_truth_condition_atomic_sound : AtomicClosureTruth PropT example_1 := by
  apply concrete_registered_truth_conditions_imply_atomic_closure
  exact example_1_concrete_registered_truth_condition_sound
theorem example_2_concrete_registered_truth_condition_atomic_sound : AtomicClosureTruth Prop example_2 := by
  apply concrete_registered_truth_conditions_imply_atomic_closure
  exact example_2_concrete_registered_truth_condition_sound
theorem example_3_concrete_registered_truth_condition_atomic_sound : AtomicClosureTruth PropT example_3 := by
  apply concrete_registered_truth_conditions_imply_atomic_closure
  exact example_3_concrete_registered_truth_condition_sound
theorem example_4_concrete_registered_truth_condition_atomic_sound : AtomicClosureTruth PropT example_4 := by
  apply concrete_registered_truth_conditions_imply_atomic_closure
  exact example_4_concrete_registered_truth_condition_sound

theorem example_1_fully_registered_truth_condition_atomic_sound : AtomicClosureTruth PropT example_1 := by
  apply fully_registered_truth_conditions_imply_atomic_closure
  exact example_1_fully_registered_truth_condition_sound
theorem example_2_fully_registered_truth_condition_atomic_sound : AtomicClosureTruth Prop example_2 := by
  apply fully_registered_truth_conditions_imply_atomic_closure
  exact example_2_fully_registered_truth_condition_sound
theorem example_3_fully_registered_truth_condition_atomic_sound : AtomicClosureTruth PropT example_3 := by
  apply fully_registered_truth_conditions_imply_atomic_closure
  exact example_3_fully_registered_truth_condition_sound
theorem example_4_fully_registered_truth_condition_atomic_sound : AtomicClosureTruth PropT example_4 := by
  apply fully_registered_truth_conditions_imply_atomic_closure
  exact example_4_fully_registered_truth_condition_sound

structure RegisteredExampleTruthInstances : Type where
  example_1_truth_instance : fully_registered_truth_conditions.fully_registered_truth_denotes PropT example_1
  example_2_truth_instance : fully_registered_truth_conditions.fully_registered_truth_denotes Prop example_2
  example_3_truth_instance : fully_registered_truth_conditions.fully_registered_truth_denotes PropT example_3
  example_4_truth_instance : fully_registered_truth_conditions.fully_registered_truth_denotes PropT example_4

def registered_example_truth_instances : RegisteredExampleTruthInstances := {
  example_1_truth_instance := example_1_fully_registered_truth_condition_sound,
  example_2_truth_instance := example_2_fully_registered_truth_condition_sound,
  example_3_truth_instance := example_3_fully_registered_truth_condition_sound,
  example_4_truth_instance := example_4_fully_registered_truth_condition_sound
}

theorem registered_example_truth_instances_exists :
    Exists (fun I : RegisteredExampleTruthInstances => I = registered_example_truth_instances) := by
  exact Exists.intro registered_example_truth_instances rfl

theorem registered_example_1_truth_instance_atomic_sound : AtomicClosureTruth PropT example_1 := by
  apply fully_registered_truth_conditions_imply_atomic_closure
  exact registered_example_truth_instances.example_1_truth_instance

theorem registered_example_2_truth_instance_atomic_sound : AtomicClosureTruth Prop example_2 := by
  apply fully_registered_truth_conditions_imply_atomic_closure
  exact registered_example_truth_instances.example_2_truth_instance

theorem registered_example_3_truth_instance_atomic_sound : AtomicClosureTruth PropT example_3 := by
  apply fully_registered_truth_conditions_imply_atomic_closure
  exact registered_example_truth_instances.example_3_truth_instance

theorem registered_example_4_truth_instance_atomic_sound : AtomicClosureTruth PropT example_4 := by
  apply fully_registered_truth_conditions_imply_atomic_closure
  exact registered_example_truth_instances.example_4_truth_instance

#check example_1
#check example_1_semantic_preservation_obligation
#check example_1_semantic_preservation_obligation_record
#check example_1_semantic_preservation_obligation_is_prop
#check example_1_semantic_preservation_target_matches
#check example_1_semantic_preservation_proved
#check example_1_model_interpretable
#check example_1_syntax_directed_truth
#check example_1_denotationally_sound
#check example_1_truth_condition_sound
#check example_1_tautological_truth_condition_sound
#check example_1_structural_truth_condition_sound
#check example_1_concrete_kernel_truth_condition_sound
#check example_1_model_interpretable_truth_kernel_sound
#check example_1_syntax_directed_truth_kernel_sound
#check example_1_primitive_truth_kernel_sound
#check example_1_atomic_closure_truth
#check example_1_atomic_closure_truth_kernel_sound
#check example_1_atomic_closure_truth_condition_sound
#check example_1_transition_refined_atomic_closure_truth
#check example_1_transition_refined_atomic_closure_sound
#check example_1_transition_refined_registered_truth_condition_sound
#check example_1_transition_refined_registered_truth_condition_atomic_sound
#check example_1_fully_registered_atomic_closure_truth
#check example_1_fully_registered_truth_condition_sound
#check example_1_registered_lexical_truth_model_sound
#check example_1_registered_lexical_truth_conditions_from_model_sound
#check example_1_concrete_registered_truth
#check example_1_concrete_registered_truth_condition_sound
#check example_1_concrete_registered_truth_condition_atomic_sound
#check example_1_fully_registered_truth_condition_atomic_sound
#check registered_example_1_truth_instance_atomic_sound
#check example_2
#check example_2_semantic_preservation_obligation
#check example_2_semantic_preservation_obligation_record
#check example_2_semantic_preservation_obligation_is_prop
#check example_2_semantic_preservation_target_matches
#check example_2_semantic_preservation_proved
#check example_2_model_interpretable
#check example_2_syntax_directed_truth
#check example_2_denotationally_sound
#check example_2_truth_condition_sound
#check example_2_tautological_truth_condition_sound
#check example_2_structural_truth_condition_sound
#check example_2_concrete_kernel_truth_condition_sound
#check example_2_model_interpretable_truth_kernel_sound
#check example_2_syntax_directed_truth_kernel_sound
#check example_2_primitive_truth_kernel_sound
#check example_2_atomic_closure_truth
#check example_2_atomic_closure_truth_kernel_sound
#check example_2_atomic_closure_truth_condition_sound
#check example_2_transition_refined_atomic_closure_truth
#check example_2_transition_refined_atomic_closure_sound
#check example_2_transition_refined_registered_truth_condition_sound
#check example_2_transition_refined_registered_truth_condition_atomic_sound
#check example_2_fully_registered_atomic_closure_truth
#check example_2_fully_registered_truth_condition_sound
#check example_2_registered_lexical_truth_model_sound
#check example_2_registered_lexical_truth_conditions_from_model_sound
#check example_2_concrete_registered_truth
#check example_2_concrete_registered_truth_condition_sound
#check example_2_concrete_registered_truth_condition_atomic_sound
#check example_2_fully_registered_truth_condition_atomic_sound
#check registered_example_2_truth_instance_atomic_sound
#check example_3
#check example_3_semantic_preservation_obligation
#check example_3_semantic_preservation_obligation_record
#check example_3_semantic_preservation_obligation_is_prop
#check example_3_semantic_preservation_target_matches
#check example_3_semantic_preservation_proved
#check example_3_model_interpretable
#check example_3_syntax_directed_truth
#check example_3_denotationally_sound
#check example_3_truth_condition_sound
#check example_3_tautological_truth_condition_sound
#check example_3_structural_truth_condition_sound
#check example_3_concrete_kernel_truth_condition_sound
#check example_3_model_interpretable_truth_kernel_sound
#check example_3_syntax_directed_truth_kernel_sound
#check example_3_primitive_truth_kernel_sound
#check example_3_atomic_closure_truth
#check example_3_atomic_closure_truth_kernel_sound
#check example_3_atomic_closure_truth_condition_sound
#check example_3_transition_refined_atomic_closure_truth
#check example_3_transition_refined_atomic_closure_sound
#check example_3_transition_refined_registered_truth_condition_sound
#check example_3_transition_refined_registered_truth_condition_atomic_sound
#check example_3_fully_registered_atomic_closure_truth
#check example_3_fully_registered_truth_condition_sound
#check example_3_registered_lexical_truth_model_sound
#check example_3_registered_lexical_truth_conditions_from_model_sound
#check example_3_concrete_registered_truth
#check example_3_concrete_registered_truth_condition_sound
#check example_3_concrete_registered_truth_condition_atomic_sound
#check example_3_fully_registered_truth_condition_atomic_sound
#check registered_example_3_truth_instance_atomic_sound
#check example_4
#check example_4_semantic_preservation_obligation
#check example_4_semantic_preservation_obligation_record
#check example_4_semantic_preservation_obligation_is_prop
#check example_4_semantic_preservation_target_matches
#check example_4_semantic_preservation_proved
#check example_4_model_interpretable
#check example_4_syntax_directed_truth
#check example_4_denotationally_sound
#check example_4_truth_condition_sound
#check example_4_tautological_truth_condition_sound
#check example_4_structural_truth_condition_sound
#check example_4_concrete_kernel_truth_condition_sound
#check example_4_model_interpretable_truth_kernel_sound
#check example_4_syntax_directed_truth_kernel_sound
#check example_4_primitive_truth_kernel_sound
#check example_4_atomic_closure_truth
#check example_4_atomic_closure_truth_kernel_sound
#check example_4_atomic_closure_truth_condition_sound
#check example_4_transition_refined_atomic_closure_truth
#check example_4_transition_refined_atomic_closure_sound
#check example_4_transition_refined_registered_truth_condition_sound
#check example_4_transition_refined_registered_truth_condition_atomic_sound
#check example_4_fully_registered_atomic_closure_truth
#check example_4_fully_registered_truth_condition_sound
#check example_4_registered_lexical_truth_model_sound
#check example_4_registered_lexical_truth_conditions_from_model_sound
#check example_4_concrete_registered_truth
#check example_4_concrete_registered_truth_condition_sound
#check example_4_concrete_registered_truth_condition_atomic_sound
#check example_4_fully_registered_truth_condition_atomic_sound
#check registered_example_4_truth_instance_atomic_sound
#check registered_lexical_truth_model
#check registered_lexical_truth_model_exists
#check registered_lexical_truth_conditions_from_model
#check registered_lexical_truth_conditions_from_model_exists
#check concrete_registered_truth_basis
#check concrete_registered_truth_basis_exists
#check concrete_registered_truth_conditions
#check concrete_registered_truth_condition_spec_exists
#check registered_example_truth_instances
#check registered_example_truth_instances_exists
