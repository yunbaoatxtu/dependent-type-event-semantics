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
