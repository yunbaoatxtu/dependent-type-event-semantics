(* Auto-generated shallow embedding for dependent-type event semantics. *)
(* This file is an interface scaffold, not a complete proof development. *)

Parameter Entity : Type.
Parameter Food : Type.
Parameter State : Type.
Parameter StateScale : Type.
Parameter TransitionT : Type.
Definition PropT : Type := Prop.
Definition Adv : Type := (Entity -> PropT) -> Entity -> PropT.
Parameter ModifierSeq : nat -> Type.
Parameter mods_nil : ModifierSeq 0.
Parameter mods_cons : forall n : nat, Adv -> ModifierSeq n -> ModifierSeq (S n).

Parameter John : Entity.
Parameter broken : State.
Parameter intact : State.
Parameter integrity_scale : StateScale.
Parameter noon : Entity.
Parameter toast : Entity.
Parameter vase : Entity.
Parameter in_bathroom : Adv.
Parameter slowly : Adv.

Inductive ObligationStatus : Type :=
  | pending
  | shallow_checked
  | proved.

Record SemanticPreservationObligation : Type := {
  obligation_statement : Prop;
  obligation_status : ObligationStatus
}.

Parameter repeat : nat -> PropT -> PropT.
Parameter at_T : Entity -> PropT -> PropT.
Parameter during_T : Entity -> PropT -> PropT.
Parameter before_T : Entity -> PropT -> PropT.
Parameter after_T : Entity -> PropT -> PropT.
Parameter until_T : Entity -> PropT -> PropT.
Parameter since_T : Entity -> PropT -> PropT.
Parameter not_T : PropT -> PropT.
Parameter Transition : Entity -> StateScale -> State -> State -> TransitionT.
Parameter Cause : Entity -> TransitionT -> PropT.
Parameter break : forall n : nat, ModifierSeq n -> Entity -> Entity -> PropT.
Parameter butter : forall n : nat, ModifierSeq n -> Entity -> Entity -> PropT.
Parameter eat : forall n : nat, ModifierSeq n -> Entity -> Food -> Prop.
Parameter knock : forall n : nat, ModifierSeq n -> Entity -> PropT.

Inductive SemanticPreservation : forall A : Type, A -> Prop :=
  | preserve_break_application : forall n : nat, forall mods : ModifierSeq n, forall arg1 : Entity, forall arg2 : Entity,
      SemanticPreservation PropT (break n mods arg1 arg2)
  | preserve_butter_application : forall n : nat, forall mods : ModifierSeq n, forall arg1 : Entity, forall arg2 : Entity,
      SemanticPreservation PropT (butter n mods arg1 arg2)
  | preserve_eat_application : forall n : nat, forall mods : ModifierSeq n, forall arg1 : Entity, forall arg2 : Food,
      SemanticPreservation Prop (eat n mods arg1 arg2)
  | preserve_knock_application : forall n : nat, forall mods : ModifierSeq n, forall arg1 : Entity,
      SemanticPreservation PropT (knock n mods arg1)
  | preserve_sigma_Entity : forall P : Entity -> Prop,
      (forall x : Entity, SemanticPreservation Prop (P x)) ->
      SemanticPreservation Prop (exists x : Entity, P x)
  | preserve_sigma_Food : forall P : Food -> Prop,
      (forall x : Food, SemanticPreservation Prop (P x)) ->
      SemanticPreservation Prop (exists x : Food, P x)
  | preserve_sigma_State : forall P : State -> Prop,
      (forall x : State, SemanticPreservation Prop (P x)) ->
      SemanticPreservation Prop (exists x : State, P x)
  | preserve_sigma_StateScale : forall P : StateScale -> Prop,
      (forall x : StateScale, SemanticPreservation Prop (P x)) ->
      SemanticPreservation Prop (exists x : StateScale, P x)
  | preserve_sigma_TransitionT : forall P : TransitionT -> Prop,
      (forall x : TransitionT, SemanticPreservation Prop (P x)) ->
      SemanticPreservation Prop (exists x : TransitionT, P x)
  | preserve_repeat : forall n : nat, forall body : PropT,
      SemanticPreservation PropT body ->
      SemanticPreservation PropT (repeat n body)
  | preserve_at_T : forall marker : Entity, forall body : PropT,
      SemanticPreservation PropT body ->
      SemanticPreservation PropT (at_T marker body)
  | preserve_during_T : forall marker : Entity, forall body : PropT,
      SemanticPreservation PropT body ->
      SemanticPreservation PropT (during_T marker body)
  | preserve_before_T : forall marker : Entity, forall body : PropT,
      SemanticPreservation PropT body ->
      SemanticPreservation PropT (before_T marker body)
  | preserve_after_T : forall marker : Entity, forall body : PropT,
      SemanticPreservation PropT body ->
      SemanticPreservation PropT (after_T marker body)
  | preserve_until_T : forall marker : Entity, forall body : PropT,
      SemanticPreservation PropT body ->
      SemanticPreservation PropT (until_T marker body)
  | preserve_since_T : forall marker : Entity, forall body : PropT,
      SemanticPreservation PropT body ->
      SemanticPreservation PropT (since_T marker body)
  | preserve_not_T : forall body : PropT,
      SemanticPreservation PropT body ->
      SemanticPreservation PropT (not_T body)
  | preserve_transition : forall theme : Entity, forall scale : StateScale, forall source : State, forall target : State,
      SemanticPreservation TransitionT (Transition theme scale source target)
  | preserve_cause : forall causer : Entity, forall effect : TransitionT,
      SemanticPreservation TransitionT effect ->
      SemanticPreservation PropT (Cause causer effect).

Inductive ModelInterpretable : forall A : Type, A -> Prop :=
  | model_break_application : forall n : nat, forall mods : ModifierSeq n, forall arg1 : Entity, forall arg2 : Entity,
      ModelInterpretable PropT (break n mods arg1 arg2)
  | model_butter_application : forall n : nat, forall mods : ModifierSeq n, forall arg1 : Entity, forall arg2 : Entity,
      ModelInterpretable PropT (butter n mods arg1 arg2)
  | model_eat_application : forall n : nat, forall mods : ModifierSeq n, forall arg1 : Entity, forall arg2 : Food,
      ModelInterpretable Prop (eat n mods arg1 arg2)
  | model_knock_application : forall n : nat, forall mods : ModifierSeq n, forall arg1 : Entity,
      ModelInterpretable PropT (knock n mods arg1)
  | model_sigma_Entity : forall P : Entity -> Prop,
      (forall x : Entity, ModelInterpretable Prop (P x)) ->
      ModelInterpretable Prop (exists x : Entity, P x)
  | model_sigma_Food : forall P : Food -> Prop,
      (forall x : Food, ModelInterpretable Prop (P x)) ->
      ModelInterpretable Prop (exists x : Food, P x)
  | model_sigma_State : forall P : State -> Prop,
      (forall x : State, ModelInterpretable Prop (P x)) ->
      ModelInterpretable Prop (exists x : State, P x)
  | model_sigma_StateScale : forall P : StateScale -> Prop,
      (forall x : StateScale, ModelInterpretable Prop (P x)) ->
      ModelInterpretable Prop (exists x : StateScale, P x)
  | model_sigma_TransitionT : forall P : TransitionT -> Prop,
      (forall x : TransitionT, ModelInterpretable Prop (P x)) ->
      ModelInterpretable Prop (exists x : TransitionT, P x)
  | model_repeat : forall n : nat, forall body : PropT,
      ModelInterpretable PropT body ->
      ModelInterpretable PropT (repeat n body)
  | model_at_T : forall marker : Entity, forall body : PropT,
      ModelInterpretable PropT body ->
      ModelInterpretable PropT (at_T marker body)
  | model_during_T : forall marker : Entity, forall body : PropT,
      ModelInterpretable PropT body ->
      ModelInterpretable PropT (during_T marker body)
  | model_before_T : forall marker : Entity, forall body : PropT,
      ModelInterpretable PropT body ->
      ModelInterpretable PropT (before_T marker body)
  | model_after_T : forall marker : Entity, forall body : PropT,
      ModelInterpretable PropT body ->
      ModelInterpretable PropT (after_T marker body)
  | model_until_T : forall marker : Entity, forall body : PropT,
      ModelInterpretable PropT body ->
      ModelInterpretable PropT (until_T marker body)
  | model_since_T : forall marker : Entity, forall body : PropT,
      ModelInterpretable PropT body ->
      ModelInterpretable PropT (since_T marker body)
  | model_not_T : forall body : PropT,
      ModelInterpretable PropT body ->
      ModelInterpretable PropT (not_T body)
  | model_transition : forall theme : Entity, forall scale : StateScale, forall source : State, forall target : State,
      ModelInterpretable TransitionT (Transition theme scale source target)
  | model_cause : forall causer : Entity, forall effect : TransitionT,
      ModelInterpretable TransitionT effect ->
      ModelInterpretable PropT (Cause causer effect).

Inductive SyntaxDirectedTruth : forall A : Type, A -> Prop :=
  | syntax_truth_break_application : forall n : nat, forall mods : ModifierSeq n, forall arg1 : Entity, forall arg2 : Entity,
      SyntaxDirectedTruth PropT (break n mods arg1 arg2)
  | syntax_truth_butter_application : forall n : nat, forall mods : ModifierSeq n, forall arg1 : Entity, forall arg2 : Entity,
      SyntaxDirectedTruth PropT (butter n mods arg1 arg2)
  | syntax_truth_eat_application : forall n : nat, forall mods : ModifierSeq n, forall arg1 : Entity, forall arg2 : Food,
      SyntaxDirectedTruth Prop (eat n mods arg1 arg2)
  | syntax_truth_knock_application : forall n : nat, forall mods : ModifierSeq n, forall arg1 : Entity,
      SyntaxDirectedTruth PropT (knock n mods arg1)
  | syntax_truth_sigma_Entity : forall P : Entity -> Prop,
      (forall x : Entity, SyntaxDirectedTruth Prop (P x)) ->
      SyntaxDirectedTruth Prop (exists x : Entity, P x)
  | syntax_truth_sigma_Food : forall P : Food -> Prop,
      (forall x : Food, SyntaxDirectedTruth Prop (P x)) ->
      SyntaxDirectedTruth Prop (exists x : Food, P x)
  | syntax_truth_sigma_State : forall P : State -> Prop,
      (forall x : State, SyntaxDirectedTruth Prop (P x)) ->
      SyntaxDirectedTruth Prop (exists x : State, P x)
  | syntax_truth_sigma_StateScale : forall P : StateScale -> Prop,
      (forall x : StateScale, SyntaxDirectedTruth Prop (P x)) ->
      SyntaxDirectedTruth Prop (exists x : StateScale, P x)
  | syntax_truth_sigma_TransitionT : forall P : TransitionT -> Prop,
      (forall x : TransitionT, SyntaxDirectedTruth Prop (P x)) ->
      SyntaxDirectedTruth Prop (exists x : TransitionT, P x)
  | syntax_truth_repeat : forall n : nat, forall body : PropT,
      SyntaxDirectedTruth PropT body ->
      SyntaxDirectedTruth PropT (repeat n body)
  | syntax_truth_at_T : forall marker : Entity, forall body : PropT,
      SyntaxDirectedTruth PropT body ->
      SyntaxDirectedTruth PropT (at_T marker body)
  | syntax_truth_during_T : forall marker : Entity, forall body : PropT,
      SyntaxDirectedTruth PropT body ->
      SyntaxDirectedTruth PropT (during_T marker body)
  | syntax_truth_before_T : forall marker : Entity, forall body : PropT,
      SyntaxDirectedTruth PropT body ->
      SyntaxDirectedTruth PropT (before_T marker body)
  | syntax_truth_after_T : forall marker : Entity, forall body : PropT,
      SyntaxDirectedTruth PropT body ->
      SyntaxDirectedTruth PropT (after_T marker body)
  | syntax_truth_until_T : forall marker : Entity, forall body : PropT,
      SyntaxDirectedTruth PropT body ->
      SyntaxDirectedTruth PropT (until_T marker body)
  | syntax_truth_since_T : forall marker : Entity, forall body : PropT,
      SyntaxDirectedTruth PropT body ->
      SyntaxDirectedTruth PropT (since_T marker body)
  | syntax_truth_not_T : forall body : PropT,
      SyntaxDirectedTruth PropT body ->
      SyntaxDirectedTruth PropT (not_T body)
  | syntax_truth_transition : forall theme : Entity, forall scale : StateScale, forall source : State, forall target : State,
      SyntaxDirectedTruth TransitionT (Transition theme scale source target)
  | syntax_truth_cause : forall causer : Entity, forall effect : TransitionT,
      SyntaxDirectedTruth TransitionT effect ->
      SyntaxDirectedTruth PropT (Cause causer effect).

Theorem semantic_preservation_model_interpretable :
  forall A : Type, forall term : A,
    SemanticPreservation A term -> ModelInterpretable A term.
Proof.
  intros A term H.
  induction H; constructor; assumption.
Qed.

Theorem semantic_preservation_syntax_directed_truth :
  forall A : Type, forall term : A,
    SemanticPreservation A term -> SyntaxDirectedTruth A term.
Proof.
  intros A term H.
  induction H; constructor; assumption.
Qed.

Record SemanticModel : Type := {
  model_denotes : forall A : Type, A -> Prop;
  denote_break_application : forall n : nat, forall mods : ModifierSeq n, forall arg1 : Entity, forall arg2 : Entity,
      model_denotes PropT (break n mods arg1 arg2);
  denote_butter_application : forall n : nat, forall mods : ModifierSeq n, forall arg1 : Entity, forall arg2 : Entity,
      model_denotes PropT (butter n mods arg1 arg2);
  denote_eat_application : forall n : nat, forall mods : ModifierSeq n, forall arg1 : Entity, forall arg2 : Food,
      model_denotes Prop (eat n mods arg1 arg2);
  denote_knock_application : forall n : nat, forall mods : ModifierSeq n, forall arg1 : Entity,
      model_denotes PropT (knock n mods arg1);
  denote_sigma_Entity : forall P : Entity -> Prop,
      (forall x : Entity, model_denotes Prop (P x)) ->
      model_denotes Prop (exists x : Entity, P x);
  denote_sigma_Food : forall P : Food -> Prop,
      (forall x : Food, model_denotes Prop (P x)) ->
      model_denotes Prop (exists x : Food, P x);
  denote_sigma_State : forall P : State -> Prop,
      (forall x : State, model_denotes Prop (P x)) ->
      model_denotes Prop (exists x : State, P x);
  denote_sigma_StateScale : forall P : StateScale -> Prop,
      (forall x : StateScale, model_denotes Prop (P x)) ->
      model_denotes Prop (exists x : StateScale, P x);
  denote_sigma_TransitionT : forall P : TransitionT -> Prop,
      (forall x : TransitionT, model_denotes Prop (P x)) ->
      model_denotes Prop (exists x : TransitionT, P x);
  denote_repeat : forall n : nat, forall body : PropT,
      model_denotes PropT body ->
      model_denotes PropT (repeat n body);
  denote_at_T : forall marker : Entity, forall body : PropT,
      model_denotes PropT body ->
      model_denotes PropT (at_T marker body);
  denote_during_T : forall marker : Entity, forall body : PropT,
      model_denotes PropT body ->
      model_denotes PropT (during_T marker body);
  denote_before_T : forall marker : Entity, forall body : PropT,
      model_denotes PropT body ->
      model_denotes PropT (before_T marker body);
  denote_after_T : forall marker : Entity, forall body : PropT,
      model_denotes PropT body ->
      model_denotes PropT (after_T marker body);
  denote_until_T : forall marker : Entity, forall body : PropT,
      model_denotes PropT body ->
      model_denotes PropT (until_T marker body);
  denote_since_T : forall marker : Entity, forall body : PropT,
      model_denotes PropT body ->
      model_denotes PropT (since_T marker body);
  denote_not_T : forall body : PropT,
      model_denotes PropT body ->
      model_denotes PropT (not_T body);
  denote_transition : forall theme : Entity, forall scale : StateScale, forall source : State, forall target : State,
      model_denotes TransitionT (Transition theme scale source target);
  denote_cause : forall causer : Entity, forall effect : TransitionT,
      model_denotes TransitionT effect ->
      model_denotes PropT (Cause causer effect)
}.

Theorem model_interpretable_denotational_sound :
  forall M : SemanticModel, forall A : Type, forall term : A,
    ModelInterpretable A term -> model_denotes M A term.
Proof.
  intros M A term H.
  induction H; eauto using
    denote_break_application,
    denote_butter_application,
    denote_eat_application,
    denote_knock_application,
    denote_sigma_Entity,
    denote_sigma_Food,
    denote_sigma_State,
    denote_sigma_StateScale,
    denote_sigma_TransitionT,
    denote_repeat,
    denote_at_T,
    denote_during_T,
    denote_before_T,
    denote_after_T,
    denote_until_T,
    denote_since_T,
    denote_not_T,
    denote_transition,
    denote_cause.
Qed.

Record TruthConditionSpec : Type := {
  truth_denotes : forall A : Type, A -> Prop;
  truth_break_application : forall n : nat, forall mods : ModifierSeq n, forall arg1 : Entity, forall arg2 : Entity,
      truth_denotes PropT (break n mods arg1 arg2);
  truth_butter_application : forall n : nat, forall mods : ModifierSeq n, forall arg1 : Entity, forall arg2 : Entity,
      truth_denotes PropT (butter n mods arg1 arg2);
  truth_eat_application : forall n : nat, forall mods : ModifierSeq n, forall arg1 : Entity, forall arg2 : Food,
      truth_denotes Prop (eat n mods arg1 arg2);
  truth_knock_application : forall n : nat, forall mods : ModifierSeq n, forall arg1 : Entity,
      truth_denotes PropT (knock n mods arg1);
  truth_sigma_Entity : forall P : Entity -> Prop,
      (forall x : Entity, truth_denotes Prop (P x)) ->
      truth_denotes Prop (exists x : Entity, P x);
  truth_sigma_Food : forall P : Food -> Prop,
      (forall x : Food, truth_denotes Prop (P x)) ->
      truth_denotes Prop (exists x : Food, P x);
  truth_sigma_State : forall P : State -> Prop,
      (forall x : State, truth_denotes Prop (P x)) ->
      truth_denotes Prop (exists x : State, P x);
  truth_sigma_StateScale : forall P : StateScale -> Prop,
      (forall x : StateScale, truth_denotes Prop (P x)) ->
      truth_denotes Prop (exists x : StateScale, P x);
  truth_sigma_TransitionT : forall P : TransitionT -> Prop,
      (forall x : TransitionT, truth_denotes Prop (P x)) ->
      truth_denotes Prop (exists x : TransitionT, P x);
  truth_repeat : forall n : nat, forall body : PropT,
      truth_denotes PropT body ->
      truth_denotes PropT (repeat n body);
  truth_at_T : forall marker : Entity, forall body : PropT,
      truth_denotes PropT body ->
      truth_denotes PropT (at_T marker body);
  truth_during_T : forall marker : Entity, forall body : PropT,
      truth_denotes PropT body ->
      truth_denotes PropT (during_T marker body);
  truth_before_T : forall marker : Entity, forall body : PropT,
      truth_denotes PropT body ->
      truth_denotes PropT (before_T marker body);
  truth_after_T : forall marker : Entity, forall body : PropT,
      truth_denotes PropT body ->
      truth_denotes PropT (after_T marker body);
  truth_until_T : forall marker : Entity, forall body : PropT,
      truth_denotes PropT body ->
      truth_denotes PropT (until_T marker body);
  truth_since_T : forall marker : Entity, forall body : PropT,
      truth_denotes PropT body ->
      truth_denotes PropT (since_T marker body);
  truth_not_T : forall body : PropT,
      truth_denotes PropT body ->
      truth_denotes PropT (not_T body);
  truth_transition : forall theme : Entity, forall scale : StateScale, forall source : State, forall target : State,
      truth_denotes TransitionT (Transition theme scale source target);
  truth_cause : forall causer : Entity, forall effect : TransitionT,
      truth_denotes TransitionT effect ->
      truth_denotes PropT (Cause causer effect)
}.

Definition semantic_model_from_truth_conditions (T : TruthConditionSpec) : SemanticModel := {|
  model_denotes := truth_denotes T;
  denote_break_application := truth_break_application T;
  denote_butter_application := truth_butter_application T;
  denote_eat_application := truth_eat_application T;
  denote_knock_application := truth_knock_application T;
  denote_sigma_Entity := truth_sigma_Entity T;
  denote_sigma_Food := truth_sigma_Food T;
  denote_sigma_State := truth_sigma_State T;
  denote_sigma_StateScale := truth_sigma_StateScale T;
  denote_sigma_TransitionT := truth_sigma_TransitionT T;
  denote_repeat := truth_repeat T;
  denote_at_T := truth_at_T T;
  denote_during_T := truth_during_T T;
  denote_before_T := truth_before_T T;
  denote_after_T := truth_after_T T;
  denote_until_T := truth_until_T T;
  denote_since_T := truth_since_T T;
  denote_not_T := truth_not_T T;
  denote_transition := truth_transition T;
  denote_cause := truth_cause T
|}.

Theorem truth_conditions_induce_denotational_soundness :
  forall T : TruthConditionSpec, forall A : Type, forall term : A,
    ModelInterpretable A term -> truth_denotes T A term.
Proof.
  intros T A term H.
  exact (model_interpretable_denotational_sound
    (semantic_model_from_truth_conditions T) A term H).
Qed.

Record ConcreteTruthConditionKernel : Type := {
  kernel_denotes : forall A : Type, A -> Prop;
  lexical_truth_break_application : forall n : nat, forall mods : ModifierSeq n, forall arg1 : Entity, forall arg2 : Entity,
      kernel_denotes PropT (break n mods arg1 arg2);
  lexical_truth_butter_application : forall n : nat, forall mods : ModifierSeq n, forall arg1 : Entity, forall arg2 : Entity,
      kernel_denotes PropT (butter n mods arg1 arg2);
  lexical_truth_eat_application : forall n : nat, forall mods : ModifierSeq n, forall arg1 : Entity, forall arg2 : Food,
      kernel_denotes Prop (eat n mods arg1 arg2);
  lexical_truth_knock_application : forall n : nat, forall mods : ModifierSeq n, forall arg1 : Entity,
      kernel_denotes PropT (knock n mods arg1);
  quantifier_truth_sigma_Entity : forall P : Entity -> Prop,
      (forall x : Entity, kernel_denotes Prop (P x)) ->
      kernel_denotes Prop (exists x : Entity, P x);
  quantifier_truth_sigma_Food : forall P : Food -> Prop,
      (forall x : Food, kernel_denotes Prop (P x)) ->
      kernel_denotes Prop (exists x : Food, P x);
  quantifier_truth_sigma_State : forall P : State -> Prop,
      (forall x : State, kernel_denotes Prop (P x)) ->
      kernel_denotes Prop (exists x : State, P x);
  quantifier_truth_sigma_StateScale : forall P : StateScale -> Prop,
      (forall x : StateScale, kernel_denotes Prop (P x)) ->
      kernel_denotes Prop (exists x : StateScale, P x);
  quantifier_truth_sigma_TransitionT : forall P : TransitionT -> Prop,
      (forall x : TransitionT, kernel_denotes Prop (P x)) ->
      kernel_denotes Prop (exists x : TransitionT, P x);
  repetition_truth : forall n : nat, forall body : PropT,
      kernel_denotes PropT body ->
      kernel_denotes PropT (repeat n body);
  temporal_truth_at_T : forall marker : Entity, forall body : PropT,
      kernel_denotes PropT body ->
      kernel_denotes PropT (at_T marker body);
  temporal_truth_during_T : forall marker : Entity, forall body : PropT,
      kernel_denotes PropT body ->
      kernel_denotes PropT (during_T marker body);
  temporal_truth_before_T : forall marker : Entity, forall body : PropT,
      kernel_denotes PropT body ->
      kernel_denotes PropT (before_T marker body);
  temporal_truth_after_T : forall marker : Entity, forall body : PropT,
      kernel_denotes PropT body ->
      kernel_denotes PropT (after_T marker body);
  temporal_truth_until_T : forall marker : Entity, forall body : PropT,
      kernel_denotes PropT body ->
      kernel_denotes PropT (until_T marker body);
  temporal_truth_since_T : forall marker : Entity, forall body : PropT,
      kernel_denotes PropT body ->
      kernel_denotes PropT (since_T marker body);
  polarity_truth_not_T : forall body : PropT,
      kernel_denotes PropT body ->
      kernel_denotes PropT (not_T body);
  transition_truth : forall theme : Entity, forall scale : StateScale, forall source : State, forall target : State,
      kernel_denotes TransitionT (Transition theme scale source target);
  cause_truth : forall causer : Entity, forall effect : TransitionT,
      kernel_denotes TransitionT effect ->
      kernel_denotes PropT (Cause causer effect)
}.

Definition truth_conditions_from_concrete_kernel (K : ConcreteTruthConditionKernel) : TruthConditionSpec := {|
  truth_denotes := kernel_denotes K;
  truth_break_application := lexical_truth_break_application K;
  truth_butter_application := lexical_truth_butter_application K;
  truth_eat_application := lexical_truth_eat_application K;
  truth_knock_application := lexical_truth_knock_application K;
  truth_sigma_Entity := quantifier_truth_sigma_Entity K;
  truth_sigma_Food := quantifier_truth_sigma_Food K;
  truth_sigma_State := quantifier_truth_sigma_State K;
  truth_sigma_StateScale := quantifier_truth_sigma_StateScale K;
  truth_sigma_TransitionT := quantifier_truth_sigma_TransitionT K;
  truth_repeat := repetition_truth K;
  truth_at_T := temporal_truth_at_T K;
  truth_during_T := temporal_truth_during_T K;
  truth_before_T := temporal_truth_before_T K;
  truth_after_T := temporal_truth_after_T K;
  truth_until_T := temporal_truth_until_T K;
  truth_since_T := temporal_truth_since_T K;
  truth_not_T := polarity_truth_not_T K;
  truth_transition := transition_truth K;
  truth_cause := cause_truth K
|}.

Theorem concrete_kernel_truth_condition_spec_exists :
  forall K : ConcreteTruthConditionKernel,
    exists T : TruthConditionSpec,
      T = truth_conditions_from_concrete_kernel K.
Proof.
  intro K. exists (truth_conditions_from_concrete_kernel K).
  reflexivity.
Qed.

Theorem concrete_kernel_induces_truth_condition_soundness :
  forall K : ConcreteTruthConditionKernel,
  forall A : Type, forall term : A,
    ModelInterpretable A term ->
    truth_denotes (truth_conditions_from_concrete_kernel K) A term.
Proof.
  intros K A term H.
  apply truth_conditions_induce_denotational_soundness.
  exact H.
Qed.

Record IndependentTruthConditionObligationLedger : Type := {
  ledger_denotes : forall A : Type, A -> Prop;
  ledger_kernel : ConcreteTruthConditionKernel;
  ledger_denotes_matches_kernel : forall A : Type, forall term : A,
      ledger_denotes A term = kernel_denotes ledger_kernel A term;
  ledger_truth_conditions : TruthConditionSpec;
  ledger_truth_conditions_match_kernel :
      ledger_truth_conditions = truth_conditions_from_concrete_kernel ledger_kernel;
  ledger_lexical_truth_break_obligation : forall n : nat, forall mods : ModifierSeq n, forall arg1 : Entity, forall arg2 : Entity,
      ledger_denotes PropT (break n mods arg1 arg2);
  ledger_lexical_truth_butter_obligation : forall n : nat, forall mods : ModifierSeq n, forall arg1 : Entity, forall arg2 : Entity,
      ledger_denotes PropT (butter n mods arg1 arg2);
  ledger_lexical_truth_eat_obligation : forall n : nat, forall mods : ModifierSeq n, forall arg1 : Entity, forall arg2 : Food,
      ledger_denotes Prop (eat n mods arg1 arg2);
  ledger_lexical_truth_knock_obligation : forall n : nat, forall mods : ModifierSeq n, forall arg1 : Entity,
      ledger_denotes PropT (knock n mods arg1);
  ledger_quantifier_truth_sigma_Entity_obligation : forall P : Entity -> Prop,
      (forall x : Entity, ledger_denotes Prop (P x)) ->
      ledger_denotes Prop (exists x : Entity, P x);
  ledger_quantifier_truth_sigma_Food_obligation : forall P : Food -> Prop,
      (forall x : Food, ledger_denotes Prop (P x)) ->
      ledger_denotes Prop (exists x : Food, P x);
  ledger_quantifier_truth_sigma_State_obligation : forall P : State -> Prop,
      (forall x : State, ledger_denotes Prop (P x)) ->
      ledger_denotes Prop (exists x : State, P x);
  ledger_quantifier_truth_sigma_StateScale_obligation : forall P : StateScale -> Prop,
      (forall x : StateScale, ledger_denotes Prop (P x)) ->
      ledger_denotes Prop (exists x : StateScale, P x);
  ledger_quantifier_truth_sigma_TransitionT_obligation : forall P : TransitionT -> Prop,
      (forall x : TransitionT, ledger_denotes Prop (P x)) ->
      ledger_denotes Prop (exists x : TransitionT, P x);
  ledger_repetition_truth_obligation : forall n : nat, forall body : PropT,
      ledger_denotes PropT body ->
      ledger_denotes PropT (repeat n body);
  ledger_temporal_truth_at_T_obligation : forall marker : Entity, forall body : PropT,
      ledger_denotes PropT body ->
      ledger_denotes PropT (at_T marker body);
  ledger_temporal_truth_during_T_obligation : forall marker : Entity, forall body : PropT,
      ledger_denotes PropT body ->
      ledger_denotes PropT (during_T marker body);
  ledger_temporal_truth_before_T_obligation : forall marker : Entity, forall body : PropT,
      ledger_denotes PropT body ->
      ledger_denotes PropT (before_T marker body);
  ledger_temporal_truth_after_T_obligation : forall marker : Entity, forall body : PropT,
      ledger_denotes PropT body ->
      ledger_denotes PropT (after_T marker body);
  ledger_temporal_truth_until_T_obligation : forall marker : Entity, forall body : PropT,
      ledger_denotes PropT body ->
      ledger_denotes PropT (until_T marker body);
  ledger_temporal_truth_since_T_obligation : forall marker : Entity, forall body : PropT,
      ledger_denotes PropT body ->
      ledger_denotes PropT (since_T marker body);
  ledger_polarity_truth_not_T_obligation : forall body : PropT,
      ledger_denotes PropT body ->
      ledger_denotes PropT (not_T body);
  ledger_transition_truth_obligation : forall theme : Entity, forall scale : StateScale,
forall source : State, forall target : State,
      ledger_denotes TransitionT (Transition theme scale source target);
  ledger_cause_truth_obligation : forall causer : Entity, forall effect : TransitionT,
      ledger_denotes TransitionT effect ->
      ledger_denotes PropT (Cause causer effect)
}.

Definition independent_truth_condition_obligation_ledger
  (K : ConcreteTruthConditionKernel) :
  IndependentTruthConditionObligationLedger := {|
  ledger_denotes := kernel_denotes K;
  ledger_kernel := K;
  ledger_denotes_matches_kernel := fun A term => eq_refl;
  ledger_truth_conditions := truth_conditions_from_concrete_kernel K;
  ledger_truth_conditions_match_kernel := eq_refl;
  ledger_lexical_truth_break_obligation := lexical_truth_break_application K;
  ledger_lexical_truth_butter_obligation := lexical_truth_butter_application K;
  ledger_lexical_truth_eat_obligation := lexical_truth_eat_application K;
  ledger_lexical_truth_knock_obligation := lexical_truth_knock_application K;
  ledger_quantifier_truth_sigma_Entity_obligation := quantifier_truth_sigma_Entity K;
  ledger_quantifier_truth_sigma_Food_obligation := quantifier_truth_sigma_Food K;
  ledger_quantifier_truth_sigma_State_obligation := quantifier_truth_sigma_State K;
  ledger_quantifier_truth_sigma_StateScale_obligation := quantifier_truth_sigma_StateScale K;
  ledger_quantifier_truth_sigma_TransitionT_obligation := quantifier_truth_sigma_TransitionT K;
  ledger_repetition_truth_obligation := repetition_truth K;
  ledger_temporal_truth_at_T_obligation := temporal_truth_at_T K;
  ledger_temporal_truth_during_T_obligation := temporal_truth_during_T K;
  ledger_temporal_truth_before_T_obligation := temporal_truth_before_T K;
  ledger_temporal_truth_after_T_obligation := temporal_truth_after_T K;
  ledger_temporal_truth_until_T_obligation := temporal_truth_until_T K;
  ledger_temporal_truth_since_T_obligation := temporal_truth_since_T K;
  ledger_polarity_truth_not_T_obligation := polarity_truth_not_T K;
  ledger_transition_truth_obligation := transition_truth K;
  ledger_cause_truth_obligation := cause_truth K
|}.

Theorem independent_truth_condition_obligation_ledger_exists :
  forall K : ConcreteTruthConditionKernel,
    exists L : IndependentTruthConditionObligationLedger,
      ledger_kernel L = K.
Proof.
  intro K.
  exists (independent_truth_condition_obligation_ledger K).
  reflexivity.
Qed.

Theorem independent_truth_condition_obligation_ledger_induces_truth_conditions :
  forall K : ConcreteTruthConditionKernel,
    ledger_truth_conditions
      (independent_truth_condition_obligation_ledger K) =
    truth_conditions_from_concrete_kernel K.
Proof.
  intro K. reflexivity.
Qed.

Theorem independent_truth_condition_obligation_ledger_truth_conditions_sound :
  forall K : ConcreteTruthConditionKernel,
  forall A : Type, forall term : A,
    ModelInterpretable A term ->
    truth_denotes
      (ledger_truth_conditions
        (independent_truth_condition_obligation_ledger K))
      A term.
Proof.
  intros K A term H.
  apply concrete_kernel_induces_truth_condition_soundness.
  exact H.
Qed.

Parameter TruthEvidence : Prop -> Type.
Parameter truth_evidence_sound : forall P : Prop, TruthEvidence P -> P.
Parameter truth_evidence_intro : forall P : Prop, P -> TruthEvidence P.

Record EvidenceBackedTruthConditionSources : Type := {
  evidence_denotes : forall A : Type, A -> Prop;
  evidence_lexical_truth_break_application : forall n : nat, forall mods : ModifierSeq n, forall arg1 : Entity, forall arg2 : Entity,
      TruthEvidence (evidence_denotes PropT (break n mods arg1 arg2));
  evidence_lexical_truth_butter_application : forall n : nat, forall mods : ModifierSeq n, forall arg1 : Entity, forall arg2 : Entity,
      TruthEvidence (evidence_denotes PropT (butter n mods arg1 arg2));
  evidence_lexical_truth_eat_application : forall n : nat, forall mods : ModifierSeq n, forall arg1 : Entity, forall arg2 : Food,
      TruthEvidence (evidence_denotes Prop (eat n mods arg1 arg2));
  evidence_lexical_truth_knock_application : forall n : nat, forall mods : ModifierSeq n, forall arg1 : Entity,
      TruthEvidence (evidence_denotes PropT (knock n mods arg1));
  evidence_quantifier_truth_sigma_Entity : forall P : Entity -> Prop,
      (forall x : Entity, evidence_denotes Prop (P x)) ->
      TruthEvidence (evidence_denotes Prop (exists x : Entity, P x));
  evidence_quantifier_truth_sigma_Food : forall P : Food -> Prop,
      (forall x : Food, evidence_denotes Prop (P x)) ->
      TruthEvidence (evidence_denotes Prop (exists x : Food, P x));
  evidence_quantifier_truth_sigma_State : forall P : State -> Prop,
      (forall x : State, evidence_denotes Prop (P x)) ->
      TruthEvidence (evidence_denotes Prop (exists x : State, P x));
  evidence_quantifier_truth_sigma_StateScale : forall P : StateScale -> Prop,
      (forall x : StateScale, evidence_denotes Prop (P x)) ->
      TruthEvidence (evidence_denotes Prop (exists x : StateScale, P x));
  evidence_quantifier_truth_sigma_TransitionT : forall P : TransitionT -> Prop,
      (forall x : TransitionT, evidence_denotes Prop (P x)) ->
      TruthEvidence (evidence_denotes Prop (exists x : TransitionT, P x));
  evidence_repetition_truth : forall n : nat, forall body : PropT,
      evidence_denotes PropT body ->
      TruthEvidence (evidence_denotes PropT (repeat n body));
  evidence_temporal_truth_at_T : forall marker : Entity, forall body : PropT,
      evidence_denotes PropT body ->
      TruthEvidence (evidence_denotes PropT (at_T marker body));
  evidence_temporal_truth_during_T : forall marker : Entity, forall body : PropT,
      evidence_denotes PropT body ->
      TruthEvidence (evidence_denotes PropT (during_T marker body));
  evidence_temporal_truth_before_T : forall marker : Entity, forall body : PropT,
      evidence_denotes PropT body ->
      TruthEvidence (evidence_denotes PropT (before_T marker body));
  evidence_temporal_truth_after_T : forall marker : Entity, forall body : PropT,
      evidence_denotes PropT body ->
      TruthEvidence (evidence_denotes PropT (after_T marker body));
  evidence_temporal_truth_until_T : forall marker : Entity, forall body : PropT,
      evidence_denotes PropT body ->
      TruthEvidence (evidence_denotes PropT (until_T marker body));
  evidence_temporal_truth_since_T : forall marker : Entity, forall body : PropT,
      evidence_denotes PropT body ->
      TruthEvidence (evidence_denotes PropT (since_T marker body));
  evidence_polarity_truth_not_T : forall body : PropT,
      evidence_denotes PropT body ->
      TruthEvidence (evidence_denotes PropT (not_T body));
  evidence_transition_truth : forall theme : Entity, forall scale : StateScale,
forall source : State, forall target : State,
      TruthEvidence (evidence_denotes TransitionT (Transition theme scale source target));
  evidence_cause_truth : forall causer : Entity, forall effect : TransitionT,
      evidence_denotes TransitionT effect ->
      TruthEvidence (evidence_denotes PropT (Cause causer effect))
}.

Definition concrete_kernel_from_evidence_sources
  (S : EvidenceBackedTruthConditionSources) :
  ConcreteTruthConditionKernel := {|
  kernel_denotes := evidence_denotes S;
  lexical_truth_break_application := fun n mods arg1 arg2 =>
      truth_evidence_sound
        (evidence_denotes S PropT (break n mods arg1 arg2))
        (evidence_lexical_truth_break_application S n mods arg1 arg2);
  lexical_truth_butter_application := fun n mods arg1 arg2 =>
      truth_evidence_sound
        (evidence_denotes S PropT (butter n mods arg1 arg2))
        (evidence_lexical_truth_butter_application S n mods arg1 arg2);
  lexical_truth_eat_application := fun n mods arg1 arg2 =>
      truth_evidence_sound
        (evidence_denotes S Prop (eat n mods arg1 arg2))
        (evidence_lexical_truth_eat_application S n mods arg1 arg2);
  lexical_truth_knock_application := fun n mods arg1 =>
      truth_evidence_sound
        (evidence_denotes S PropT (knock n mods arg1))
        (evidence_lexical_truth_knock_application S n mods arg1);
  quantifier_truth_sigma_Entity := fun P h =>
      truth_evidence_sound
        (evidence_denotes S Prop (exists x : Entity, P x))
        (evidence_quantifier_truth_sigma_Entity S P h);
  quantifier_truth_sigma_Food := fun P h =>
      truth_evidence_sound
        (evidence_denotes S Prop (exists x : Food, P x))
        (evidence_quantifier_truth_sigma_Food S P h);
  quantifier_truth_sigma_State := fun P h =>
      truth_evidence_sound
        (evidence_denotes S Prop (exists x : State, P x))
        (evidence_quantifier_truth_sigma_State S P h);
  quantifier_truth_sigma_StateScale := fun P h =>
      truth_evidence_sound
        (evidence_denotes S Prop (exists x : StateScale, P x))
        (evidence_quantifier_truth_sigma_StateScale S P h);
  quantifier_truth_sigma_TransitionT := fun P h =>
      truth_evidence_sound
        (evidence_denotes S Prop (exists x : TransitionT, P x))
        (evidence_quantifier_truth_sigma_TransitionT S P h);
  repetition_truth := fun n body h =>
      truth_evidence_sound
        (evidence_denotes S PropT (repeat n body))
        (evidence_repetition_truth S n body h);
  temporal_truth_at_T := fun marker body h =>
      truth_evidence_sound
        (evidence_denotes S PropT (at_T marker body))
        (evidence_temporal_truth_at_T S marker body h);
  temporal_truth_during_T := fun marker body h =>
      truth_evidence_sound
        (evidence_denotes S PropT (during_T marker body))
        (evidence_temporal_truth_during_T S marker body h);
  temporal_truth_before_T := fun marker body h =>
      truth_evidence_sound
        (evidence_denotes S PropT (before_T marker body))
        (evidence_temporal_truth_before_T S marker body h);
  temporal_truth_after_T := fun marker body h =>
      truth_evidence_sound
        (evidence_denotes S PropT (after_T marker body))
        (evidence_temporal_truth_after_T S marker body h);
  temporal_truth_until_T := fun marker body h =>
      truth_evidence_sound
        (evidence_denotes S PropT (until_T marker body))
        (evidence_temporal_truth_until_T S marker body h);
  temporal_truth_since_T := fun marker body h =>
      truth_evidence_sound
        (evidence_denotes S PropT (since_T marker body))
        (evidence_temporal_truth_since_T S marker body h);
  polarity_truth_not_T := fun body h =>
      truth_evidence_sound
        (evidence_denotes S PropT (not_T body))
        (evidence_polarity_truth_not_T S body h);
  transition_truth := fun theme scale source target =>
      truth_evidence_sound
        (evidence_denotes S TransitionT (Transition theme scale source target))
        (evidence_transition_truth S theme scale source target);
  cause_truth := fun causer effect h =>
      truth_evidence_sound
        (evidence_denotes S PropT (Cause causer effect))
        (evidence_cause_truth S causer effect h)
|}.

Definition evidence_backed_truth_condition_ledger
  (S : EvidenceBackedTruthConditionSources) :
  IndependentTruthConditionObligationLedger :=
  independent_truth_condition_obligation_ledger
    (concrete_kernel_from_evidence_sources S).

Theorem evidence_backed_truth_condition_sources_induce_kernel :
  forall S : EvidenceBackedTruthConditionSources,
    exists K : ConcreteTruthConditionKernel,
      K = concrete_kernel_from_evidence_sources S.
Proof.
  intro S.
  exists (concrete_kernel_from_evidence_sources S).
  reflexivity.
Qed.

Theorem evidence_backed_truth_condition_sources_induce_truth_conditions :
  forall S : EvidenceBackedTruthConditionSources,
    ledger_truth_conditions
      (evidence_backed_truth_condition_ledger S) =
    truth_conditions_from_concrete_kernel
      (concrete_kernel_from_evidence_sources S).
Proof.
  intro S. reflexivity.
Qed.

Theorem evidence_backed_truth_condition_sources_sound :
  forall S : EvidenceBackedTruthConditionSources,
  forall A : Type, forall term : A,
    ModelInterpretable A term ->
    truth_denotes
      (ledger_truth_conditions
        (evidence_backed_truth_condition_ledger S))
      A term.
Proof.
  intros S A term H.
  exact
    (independent_truth_condition_obligation_ledger_truth_conditions_sound
      (concrete_kernel_from_evidence_sources S) A term H).
Qed.

Record PrimitiveTruthAssumptions : Type := {
  primitive_denotes : forall A : Type, A -> Prop;
  primitive_lexical_truth_break_application : forall n : nat, forall mods : ModifierSeq n, forall arg1 : Entity, forall arg2 : Entity,
      primitive_denotes PropT (break n mods arg1 arg2);
  primitive_lexical_truth_butter_application : forall n : nat, forall mods : ModifierSeq n, forall arg1 : Entity, forall arg2 : Entity,
      primitive_denotes PropT (butter n mods arg1 arg2);
  primitive_lexical_truth_eat_application : forall n : nat, forall mods : ModifierSeq n, forall arg1 : Entity, forall arg2 : Food,
      primitive_denotes Prop (eat n mods arg1 arg2);
  primitive_lexical_truth_knock_application : forall n : nat, forall mods : ModifierSeq n, forall arg1 : Entity,
      primitive_denotes PropT (knock n mods arg1);
  primitive_quantifier_truth_sigma_Entity : forall P : Entity -> Prop,
      (forall x : Entity, primitive_denotes Prop (P x)) ->
      primitive_denotes Prop (exists x : Entity, P x);
  primitive_quantifier_truth_sigma_Food : forall P : Food -> Prop,
      (forall x : Food, primitive_denotes Prop (P x)) ->
      primitive_denotes Prop (exists x : Food, P x);
  primitive_quantifier_truth_sigma_State : forall P : State -> Prop,
      (forall x : State, primitive_denotes Prop (P x)) ->
      primitive_denotes Prop (exists x : State, P x);
  primitive_quantifier_truth_sigma_StateScale : forall P : StateScale -> Prop,
      (forall x : StateScale, primitive_denotes Prop (P x)) ->
      primitive_denotes Prop (exists x : StateScale, P x);
  primitive_quantifier_truth_sigma_TransitionT : forall P : TransitionT -> Prop,
      (forall x : TransitionT, primitive_denotes Prop (P x)) ->
      primitive_denotes Prop (exists x : TransitionT, P x);
  primitive_repetition_truth : forall n : nat, forall body : PropT,
      primitive_denotes PropT body ->
      primitive_denotes PropT (repeat n body);
  primitive_temporal_truth_at_T : forall marker : Entity, forall body : PropT,
      primitive_denotes PropT body ->
      primitive_denotes PropT (at_T marker body);
  primitive_temporal_truth_during_T : forall marker : Entity, forall body : PropT,
      primitive_denotes PropT body ->
      primitive_denotes PropT (during_T marker body);
  primitive_temporal_truth_before_T : forall marker : Entity, forall body : PropT,
      primitive_denotes PropT body ->
      primitive_denotes PropT (before_T marker body);
  primitive_temporal_truth_after_T : forall marker : Entity, forall body : PropT,
      primitive_denotes PropT body ->
      primitive_denotes PropT (after_T marker body);
  primitive_temporal_truth_until_T : forall marker : Entity, forall body : PropT,
      primitive_denotes PropT body ->
      primitive_denotes PropT (until_T marker body);
  primitive_temporal_truth_since_T : forall marker : Entity, forall body : PropT,
      primitive_denotes PropT body ->
      primitive_denotes PropT (since_T marker body);
  primitive_polarity_truth_not_T : forall body : PropT,
      primitive_denotes PropT body ->
      primitive_denotes PropT (not_T body);
  primitive_transition_truth : forall theme : Entity, forall scale : StateScale, forall source : State, forall target : State,
      primitive_denotes TransitionT (Transition theme scale source target);
  primitive_cause_truth : forall causer : Entity, forall effect : TransitionT,
      primitive_denotes TransitionT effect ->
      primitive_denotes PropT (Cause causer effect)
}.

Parameter primitive_truth_assumptions : PrimitiveTruthAssumptions.

Definition primitive_truth_kernel : ConcreteTruthConditionKernel := {|
  kernel_denotes := primitive_denotes primitive_truth_assumptions;
  lexical_truth_break_application := primitive_lexical_truth_break_application primitive_truth_assumptions;
  lexical_truth_butter_application := primitive_lexical_truth_butter_application primitive_truth_assumptions;
  lexical_truth_eat_application := primitive_lexical_truth_eat_application primitive_truth_assumptions;
  lexical_truth_knock_application := primitive_lexical_truth_knock_application primitive_truth_assumptions;
  quantifier_truth_sigma_Entity := primitive_quantifier_truth_sigma_Entity primitive_truth_assumptions;
  quantifier_truth_sigma_Food := primitive_quantifier_truth_sigma_Food primitive_truth_assumptions;
  quantifier_truth_sigma_State := primitive_quantifier_truth_sigma_State primitive_truth_assumptions;
  quantifier_truth_sigma_StateScale := primitive_quantifier_truth_sigma_StateScale primitive_truth_assumptions;
  quantifier_truth_sigma_TransitionT := primitive_quantifier_truth_sigma_TransitionT primitive_truth_assumptions;
  repetition_truth := primitive_repetition_truth primitive_truth_assumptions;
  temporal_truth_at_T := primitive_temporal_truth_at_T primitive_truth_assumptions;
  temporal_truth_during_T := primitive_temporal_truth_during_T primitive_truth_assumptions;
  temporal_truth_before_T := primitive_temporal_truth_before_T primitive_truth_assumptions;
  temporal_truth_after_T := primitive_temporal_truth_after_T primitive_truth_assumptions;
  temporal_truth_until_T := primitive_temporal_truth_until_T primitive_truth_assumptions;
  temporal_truth_since_T := primitive_temporal_truth_since_T primitive_truth_assumptions;
  polarity_truth_not_T := primitive_polarity_truth_not_T primitive_truth_assumptions;
  transition_truth := primitive_transition_truth primitive_truth_assumptions;
  cause_truth := primitive_cause_truth primitive_truth_assumptions
|}.

Definition primitive_truth_conditions_from_kernel : TruthConditionSpec :=
  truth_conditions_from_concrete_kernel primitive_truth_kernel.

Theorem primitive_truth_kernel_exists :
  exists K : ConcreteTruthConditionKernel,
    K = primitive_truth_kernel.
Proof.
  exists primitive_truth_kernel. reflexivity.
Qed.

Theorem primitive_truth_kernel_denotes_primitive_assumptions :
  forall A : Type, forall term : A,
    primitive_denotes primitive_truth_assumptions A term ->
    truth_denotes (truth_conditions_from_concrete_kernel
      primitive_truth_kernel) A term.
Proof.
  intros A term H.
  exact H.
Qed.

Theorem primitive_truth_kernel_denotes_model_interpretable :
  forall A : Type, forall term : A,
    ModelInterpretable A term ->
    truth_denotes (truth_conditions_from_concrete_kernel
      primitive_truth_kernel) A term.
Proof.
  intros A term H.
  apply concrete_kernel_induces_truth_condition_soundness.
  exact H.
Qed.

Inductive AtomicBaseTruth : forall A : Type, A -> Prop :=
  | atomic_base_truth_break_application : forall n : nat, forall mods : ModifierSeq n, forall arg1 : Entity, forall arg2 : Entity,
      AtomicBaseTruth PropT (break n mods arg1 arg2)
  | atomic_base_truth_butter_application : forall n : nat, forall mods : ModifierSeq n, forall arg1 : Entity, forall arg2 : Entity,
      AtomicBaseTruth PropT (butter n mods arg1 arg2)
  | atomic_base_truth_eat_application : forall n : nat, forall mods : ModifierSeq n, forall arg1 : Entity, forall arg2 : Food,
      AtomicBaseTruth Prop (eat n mods arg1 arg2)
  | atomic_base_truth_knock_application : forall n : nat, forall mods : ModifierSeq n, forall arg1 : Entity,
      AtomicBaseTruth PropT (knock n mods arg1)
  | atomic_base_truth_transition : forall theme : Entity, forall scale : StateScale, forall source : State, forall target : State,
      AtomicBaseTruth TransitionT (Transition theme scale source target).

Record LexicalAtomTruthAssumptions (D : forall A : Type, A -> Prop) : Type := {
  lexical_atom_truth_break_application : forall n : nat, forall mods : ModifierSeq n, forall arg1 : Entity, forall arg2 : Entity,
      D PropT (break n mods arg1 arg2);
  lexical_atom_truth_butter_application : forall n : nat, forall mods : ModifierSeq n, forall arg1 : Entity, forall arg2 : Entity,
      D PropT (butter n mods arg1 arg2);
  lexical_atom_truth_eat_application : forall n : nat, forall mods : ModifierSeq n, forall arg1 : Entity, forall arg2 : Food,
      D Prop (eat n mods arg1 arg2);
  lexical_atom_truth_knock_application : forall n : nat, forall mods : ModifierSeq n, forall arg1 : Entity,
      D PropT (knock n mods arg1);
}.

Record TransitionAtomTruthAssumptions (D : forall A : Type, A -> Prop) : Type := {
  transition_atom_truth : forall theme : Entity, forall scale : StateScale, forall source : State, forall target : State,
      D TransitionT (Transition theme scale source target)
}.

Record LexicalTransitionTruthAssumptions : Type := {
  atom_assumption_denotes : forall A : Type, A -> Prop;
  lexical_atom_assumptions : LexicalAtomTruthAssumptions atom_assumption_denotes;
  transition_atom_assumptions : TransitionAtomTruthAssumptions atom_assumption_denotes
}.

Definition lexical_atom_truth_assumptions_from_atomic_base :
  LexicalAtomTruthAssumptions AtomicBaseTruth := {|
  lexical_atom_truth_break_application := fun n mods arg1 arg2 => atomic_base_truth_break_application n mods arg1 arg2;
  lexical_atom_truth_butter_application := fun n mods arg1 arg2 => atomic_base_truth_butter_application n mods arg1 arg2;
  lexical_atom_truth_eat_application := fun n mods arg1 arg2 => atomic_base_truth_eat_application n mods arg1 arg2;
  lexical_atom_truth_knock_application := fun n mods arg1 => atomic_base_truth_knock_application n mods arg1
|}.

Definition transition_atom_truth_assumptions_from_atomic_base :
  TransitionAtomTruthAssumptions AtomicBaseTruth := {|
  transition_atom_truth := fun theme scale source target =>
    atomic_base_truth_transition theme scale source target
|}.

Definition lexical_transition_truth_assumptions_from_atomic_base :
  LexicalTransitionTruthAssumptions := {|
  atom_assumption_denotes := AtomicBaseTruth;
  lexical_atom_assumptions := lexical_atom_truth_assumptions_from_atomic_base;
  transition_atom_assumptions := transition_atom_truth_assumptions_from_atomic_base
|}.

Theorem lexical_atom_truth_assumptions_from_atomic_base_exists :
  exists L : LexicalAtomTruthAssumptions AtomicBaseTruth,
    L = lexical_atom_truth_assumptions_from_atomic_base.
Proof.
  exists lexical_atom_truth_assumptions_from_atomic_base. reflexivity.
Qed.

Theorem transition_atom_truth_assumptions_from_atomic_base_exists :
  exists T : TransitionAtomTruthAssumptions AtomicBaseTruth,
    T = transition_atom_truth_assumptions_from_atomic_base.
Proof.
  exists transition_atom_truth_assumptions_from_atomic_base. reflexivity.
Qed.

Theorem lexical_transition_truth_assumptions_from_atomic_base_exists :
  exists A : LexicalTransitionTruthAssumptions,
    A = lexical_transition_truth_assumptions_from_atomic_base.
Proof.
  exists lexical_transition_truth_assumptions_from_atomic_base.
  reflexivity.
Qed.

Record LexicalTransitionTruthModel : Type := {
  atom_model_denotes : forall A : Type, A -> Prop;
  model_lexical_truth_break_application : forall n : nat, forall mods : ModifierSeq n, forall arg1 : Entity, forall arg2 : Entity,
      atom_model_denotes PropT (break n mods arg1 arg2);
  model_lexical_truth_butter_application : forall n : nat, forall mods : ModifierSeq n, forall arg1 : Entity, forall arg2 : Entity,
      atom_model_denotes PropT (butter n mods arg1 arg2);
  model_lexical_truth_eat_application : forall n : nat, forall mods : ModifierSeq n, forall arg1 : Entity, forall arg2 : Food,
      atom_model_denotes Prop (eat n mods arg1 arg2);
  model_lexical_truth_knock_application : forall n : nat, forall mods : ModifierSeq n, forall arg1 : Entity,
      atom_model_denotes PropT (knock n mods arg1);
  model_transition_truth : forall theme : Entity, forall scale : StateScale, forall source : State, forall target : State,
      atom_model_denotes TransitionT (Transition theme scale source target)
}.

Definition lexical_transition_truth_model_from_assumptions
  (assumptions : LexicalTransitionTruthAssumptions) :
  LexicalTransitionTruthModel := {|
  atom_model_denotes := atom_assumption_denotes assumptions;
  model_lexical_truth_break_application := @lexical_atom_truth_break_application (atom_assumption_denotes assumptions) (lexical_atom_assumptions assumptions);
  model_lexical_truth_butter_application := @lexical_atom_truth_butter_application (atom_assumption_denotes assumptions) (lexical_atom_assumptions assumptions);
  model_lexical_truth_eat_application := @lexical_atom_truth_eat_application (atom_assumption_denotes assumptions) (lexical_atom_assumptions assumptions);
  model_lexical_truth_knock_application := @lexical_atom_truth_knock_application (atom_assumption_denotes assumptions) (lexical_atom_assumptions assumptions);
  model_transition_truth := @transition_atom_truth (atom_assumption_denotes assumptions) (transition_atom_assumptions assumptions)
|}.

Definition lexical_transition_truth_model : LexicalTransitionTruthModel :=
  lexical_transition_truth_model_from_assumptions
    lexical_transition_truth_assumptions_from_atomic_base.

Theorem lexical_transition_truth_model_from_assumptions_exists :
  exists M : LexicalTransitionTruthModel,
    M = lexical_transition_truth_model_from_assumptions
      lexical_transition_truth_assumptions_from_atomic_base.
Proof.
  exists (lexical_transition_truth_model_from_assumptions
    lexical_transition_truth_assumptions_from_atomic_base).
  reflexivity.
Qed.

Theorem lexical_transition_truth_model_exists :
  exists M : LexicalTransitionTruthModel,
    M = lexical_transition_truth_model.
Proof.
  exists lexical_transition_truth_model. reflexivity.
Qed.

Theorem lexical_transition_truth_model_denotes_atomic_base_truth :
  forall A : Type, forall term : A,
    AtomicBaseTruth A term ->
    atom_model_denotes lexical_transition_truth_model A term.
Proof.
  intros A term H.
  exact H.
Qed.

Record AtomicValuationSpec : Type := {
  atomic_valuation_denotes : forall A : Type, A -> Prop;
  valuation_lexical_truth_break_application : forall n : nat, forall mods : ModifierSeq n, forall arg1 : Entity, forall arg2 : Entity,
      atomic_valuation_denotes PropT (break n mods arg1 arg2);
  valuation_lexical_truth_butter_application : forall n : nat, forall mods : ModifierSeq n, forall arg1 : Entity, forall arg2 : Entity,
      atomic_valuation_denotes PropT (butter n mods arg1 arg2);
  valuation_lexical_truth_eat_application : forall n : nat, forall mods : ModifierSeq n, forall arg1 : Entity, forall arg2 : Food,
      atomic_valuation_denotes Prop (eat n mods arg1 arg2);
  valuation_lexical_truth_knock_application : forall n : nat, forall mods : ModifierSeq n, forall arg1 : Entity,
      atomic_valuation_denotes PropT (knock n mods arg1);
  valuation_transition_truth : forall theme : Entity, forall scale : StateScale, forall source : State, forall target : State,
      atomic_valuation_denotes TransitionT (Transition theme scale source target)
}.

Definition atomic_valuation_spec_from_lexical_transition_model : AtomicValuationSpec := {|
  atomic_valuation_denotes := atom_model_denotes lexical_transition_truth_model;
  valuation_lexical_truth_break_application := model_lexical_truth_break_application lexical_transition_truth_model;
  valuation_lexical_truth_butter_application := model_lexical_truth_butter_application lexical_transition_truth_model;
  valuation_lexical_truth_eat_application := model_lexical_truth_eat_application lexical_transition_truth_model;
  valuation_lexical_truth_knock_application := model_lexical_truth_knock_application lexical_transition_truth_model;
  valuation_transition_truth := model_transition_truth lexical_transition_truth_model
|}.

Definition atomic_base_valuation_spec : AtomicValuationSpec :=
  atomic_valuation_spec_from_lexical_transition_model.

Theorem atomic_valuation_spec_from_lexical_transition_model_exists :
  exists V : AtomicValuationSpec,
    V = atomic_valuation_spec_from_lexical_transition_model.
Proof.
  exists atomic_valuation_spec_from_lexical_transition_model.
  reflexivity.
Qed.

Theorem atomic_base_valuation_spec_exists :
  exists V : AtomicValuationSpec,
    V = atomic_base_valuation_spec.
Proof.
  exists atomic_base_valuation_spec. reflexivity.
Qed.

Theorem atomic_base_valuation_denotes_atomic_base_truth :
  forall A : Type, forall term : A,
    AtomicBaseTruth A term ->
    atomic_valuation_denotes atomic_base_valuation_spec A term.
Proof.
  intros A term H.
  exact H.
Qed.

Record AtomicTruthFacts : Type := {
  atomic_lexical_truth_break_application : forall n : nat, forall mods : ModifierSeq n, forall arg1 : Entity, forall arg2 : Entity,
      AtomicBaseTruth PropT (break n mods arg1 arg2);
  atomic_lexical_truth_butter_application : forall n : nat, forall mods : ModifierSeq n, forall arg1 : Entity, forall arg2 : Entity,
      AtomicBaseTruth PropT (butter n mods arg1 arg2);
  atomic_lexical_truth_eat_application : forall n : nat, forall mods : ModifierSeq n, forall arg1 : Entity, forall arg2 : Food,
      AtomicBaseTruth Prop (eat n mods arg1 arg2);
  atomic_lexical_truth_knock_application : forall n : nat, forall mods : ModifierSeq n, forall arg1 : Entity,
      AtomicBaseTruth PropT (knock n mods arg1);
  atomic_transition_truth : forall theme : Entity, forall scale : StateScale, forall source : State, forall target : State,
      AtomicBaseTruth TransitionT (Transition theme scale source target)
}.

Definition atomic_truth_facts_from_atomic_base_valuation : AtomicTruthFacts := {|
  atomic_lexical_truth_break_application := fun n mods arg1 arg2 => valuation_lexical_truth_break_application atomic_base_valuation_spec n mods arg1 arg2;
  atomic_lexical_truth_butter_application := fun n mods arg1 arg2 => valuation_lexical_truth_butter_application atomic_base_valuation_spec n mods arg1 arg2;
  atomic_lexical_truth_eat_application := fun n mods arg1 arg2 => valuation_lexical_truth_eat_application atomic_base_valuation_spec n mods arg1 arg2;
  atomic_lexical_truth_knock_application := fun n mods arg1 => valuation_lexical_truth_knock_application atomic_base_valuation_spec n mods arg1;
  atomic_transition_truth := fun theme scale source target => valuation_transition_truth atomic_base_valuation_spec theme scale source target
|}.

Definition atomic_truth_facts : AtomicTruthFacts :=
  atomic_truth_facts_from_atomic_base_valuation.

Theorem atomic_truth_facts_from_atomic_base_valuation_exists :
  exists F : AtomicTruthFacts,
    F = atomic_truth_facts_from_atomic_base_valuation.
Proof.
  exists atomic_truth_facts_from_atomic_base_valuation. reflexivity.
Qed.

Inductive AtomicClosureTruth : forall A : Type, A -> Prop :=
  | atomic_closure_truth_break_application : forall n : nat, forall mods : ModifierSeq n, forall arg1 : Entity, forall arg2 : Entity,
      AtomicBaseTruth PropT (break n mods arg1 arg2) ->
      AtomicClosureTruth PropT (break n mods arg1 arg2)
  | atomic_closure_truth_butter_application : forall n : nat, forall mods : ModifierSeq n, forall arg1 : Entity, forall arg2 : Entity,
      AtomicBaseTruth PropT (butter n mods arg1 arg2) ->
      AtomicClosureTruth PropT (butter n mods arg1 arg2)
  | atomic_closure_truth_eat_application : forall n : nat, forall mods : ModifierSeq n, forall arg1 : Entity, forall arg2 : Food,
      AtomicBaseTruth Prop (eat n mods arg1 arg2) ->
      AtomicClosureTruth Prop (eat n mods arg1 arg2)
  | atomic_closure_truth_knock_application : forall n : nat, forall mods : ModifierSeq n, forall arg1 : Entity,
      AtomicBaseTruth PropT (knock n mods arg1) ->
      AtomicClosureTruth PropT (knock n mods arg1)
  | atomic_closure_truth_sigma_Entity : forall P : Entity -> Prop,
      (forall x : Entity, AtomicClosureTruth Prop (P x)) ->
      AtomicClosureTruth Prop (exists x : Entity, P x)
  | atomic_closure_truth_sigma_Food : forall P : Food -> Prop,
      (forall x : Food, AtomicClosureTruth Prop (P x)) ->
      AtomicClosureTruth Prop (exists x : Food, P x)
  | atomic_closure_truth_sigma_State : forall P : State -> Prop,
      (forall x : State, AtomicClosureTruth Prop (P x)) ->
      AtomicClosureTruth Prop (exists x : State, P x)
  | atomic_closure_truth_sigma_StateScale : forall P : StateScale -> Prop,
      (forall x : StateScale, AtomicClosureTruth Prop (P x)) ->
      AtomicClosureTruth Prop (exists x : StateScale, P x)
  | atomic_closure_truth_sigma_TransitionT : forall P : TransitionT -> Prop,
      (forall x : TransitionT, AtomicClosureTruth Prop (P x)) ->
      AtomicClosureTruth Prop (exists x : TransitionT, P x)
  | atomic_closure_truth_repeat : forall n : nat, forall body : PropT,
      AtomicClosureTruth PropT body ->
      AtomicClosureTruth PropT (repeat n body)
  | atomic_closure_truth_at_T : forall marker : Entity, forall body : PropT,
      AtomicClosureTruth PropT body ->
      AtomicClosureTruth PropT (at_T marker body)
  | atomic_closure_truth_during_T : forall marker : Entity, forall body : PropT,
      AtomicClosureTruth PropT body ->
      AtomicClosureTruth PropT (during_T marker body)
  | atomic_closure_truth_before_T : forall marker : Entity, forall body : PropT,
      AtomicClosureTruth PropT body ->
      AtomicClosureTruth PropT (before_T marker body)
  | atomic_closure_truth_after_T : forall marker : Entity, forall body : PropT,
      AtomicClosureTruth PropT body ->
      AtomicClosureTruth PropT (after_T marker body)
  | atomic_closure_truth_until_T : forall marker : Entity, forall body : PropT,
      AtomicClosureTruth PropT body ->
      AtomicClosureTruth PropT (until_T marker body)
  | atomic_closure_truth_since_T : forall marker : Entity, forall body : PropT,
      AtomicClosureTruth PropT body ->
      AtomicClosureTruth PropT (since_T marker body)
  | atomic_closure_truth_not_T : forall body : PropT,
      AtomicClosureTruth PropT body ->
      AtomicClosureTruth PropT (not_T body)
  | atomic_closure_truth_transition : forall theme : Entity, forall scale : StateScale, forall source : State, forall target : State,
      AtomicBaseTruth TransitionT (Transition theme scale source target) ->
      AtomicClosureTruth TransitionT (Transition theme scale source target)
  | atomic_closure_truth_cause : forall causer : Entity, forall effect : TransitionT,
      AtomicClosureTruth TransitionT effect ->
      AtomicClosureTruth PropT (Cause causer effect).

Theorem model_interpretable_atomic_closure_truth :
  forall A : Type, forall term : A,
    ModelInterpretable A term -> AtomicClosureTruth A term.
Proof.
  intros A term H.
  induction H.
  - apply atomic_closure_truth_break_application.
    apply (atomic_lexical_truth_break_application atomic_truth_facts).
  - apply atomic_closure_truth_butter_application.
    apply (atomic_lexical_truth_butter_application atomic_truth_facts).
  - apply atomic_closure_truth_eat_application.
    apply (atomic_lexical_truth_eat_application atomic_truth_facts).
  - apply atomic_closure_truth_knock_application.
    apply (atomic_lexical_truth_knock_application atomic_truth_facts).
  - apply atomic_closure_truth_sigma_Entity.
    assumption.
  - apply atomic_closure_truth_sigma_Food.
    assumption.
  - apply atomic_closure_truth_sigma_State.
    assumption.
  - apply atomic_closure_truth_sigma_StateScale.
    assumption.
  - apply atomic_closure_truth_sigma_TransitionT.
    assumption.
  - apply atomic_closure_truth_repeat. assumption.
  - apply atomic_closure_truth_at_T. assumption.
  - apply atomic_closure_truth_during_T. assumption.
  - apply atomic_closure_truth_before_T. assumption.
  - apply atomic_closure_truth_after_T. assumption.
  - apply atomic_closure_truth_until_T. assumption.
  - apply atomic_closure_truth_since_T. assumption.
  - apply atomic_closure_truth_not_T. assumption.
  - apply atomic_closure_truth_transition.
    apply (atomic_transition_truth atomic_truth_facts).
  - apply atomic_closure_truth_cause. assumption.
Qed.

Definition atomic_closure_truth_kernel_denotes : forall A : Type, A -> Prop :=
  AtomicClosureTruth.

Definition atomic_closure_truth_kernel : ConcreteTruthConditionKernel := {|
  kernel_denotes := atomic_closure_truth_kernel_denotes;
  lexical_truth_break_application := fun n mods arg1 arg2 => atomic_closure_truth_break_application n mods arg1 arg2 (atomic_lexical_truth_break_application atomic_truth_facts n mods arg1 arg2);
  lexical_truth_butter_application := fun n mods arg1 arg2 => atomic_closure_truth_butter_application n mods arg1 arg2 (atomic_lexical_truth_butter_application atomic_truth_facts n mods arg1 arg2);
  lexical_truth_eat_application := fun n mods arg1 arg2 => atomic_closure_truth_eat_application n mods arg1 arg2 (atomic_lexical_truth_eat_application atomic_truth_facts n mods arg1 arg2);
  lexical_truth_knock_application := fun n mods arg1 => atomic_closure_truth_knock_application n mods arg1 (atomic_lexical_truth_knock_application atomic_truth_facts n mods arg1);
  quantifier_truth_sigma_Entity := fun P h => atomic_closure_truth_sigma_Entity P h;
  quantifier_truth_sigma_Food := fun P h => atomic_closure_truth_sigma_Food P h;
  quantifier_truth_sigma_State := fun P h => atomic_closure_truth_sigma_State P h;
  quantifier_truth_sigma_StateScale := fun P h => atomic_closure_truth_sigma_StateScale P h;
  quantifier_truth_sigma_TransitionT := fun P h => atomic_closure_truth_sigma_TransitionT P h;
  repetition_truth := fun n body h => atomic_closure_truth_repeat n body h;
  temporal_truth_at_T := fun marker body h => atomic_closure_truth_at_T marker body h;
  temporal_truth_during_T := fun marker body h => atomic_closure_truth_during_T marker body h;
  temporal_truth_before_T := fun marker body h => atomic_closure_truth_before_T marker body h;
  temporal_truth_after_T := fun marker body h => atomic_closure_truth_after_T marker body h;
  temporal_truth_until_T := fun marker body h => atomic_closure_truth_until_T marker body h;
  temporal_truth_since_T := fun marker body h => atomic_closure_truth_since_T marker body h;
  polarity_truth_not_T := fun body h => atomic_closure_truth_not_T body h;
  transition_truth := fun theme scale source target => atomic_closure_truth_transition theme scale source target (atomic_transition_truth atomic_truth_facts theme scale source target);
  cause_truth := fun causer effect h => atomic_closure_truth_cause causer effect h
|}.

Definition atomic_closure_truth_conditions_from_kernel : TruthConditionSpec :=
  truth_conditions_from_concrete_kernel atomic_closure_truth_kernel.

Theorem atomic_closure_truth_kernel_exists :
  exists K : ConcreteTruthConditionKernel,
    K = atomic_closure_truth_kernel.
Proof.
  exists atomic_closure_truth_kernel. reflexivity.
Qed.

Theorem atomic_closure_truth_kernel_denotes_atomic_closure_truth :
  forall A : Type, forall term : A,
    AtomicClosureTruth A term ->
    truth_denotes (truth_conditions_from_concrete_kernel
      atomic_closure_truth_kernel) A term.
Proof.
  intros A term H.
  exact H.
Qed.

Definition atomic_closure_truth_conditions : TruthConditionSpec :=
  atomic_closure_truth_conditions_from_kernel.

Theorem atomic_closure_truth_conditions_exists :
  exists T : TruthConditionSpec,
    T = atomic_closure_truth_conditions.
Proof.
  exists atomic_closure_truth_conditions. reflexivity.
Qed.

Theorem atomic_closure_truth_conditions_denote_atomic_closure_truth :
  forall A : Type, forall term : A,
    AtomicClosureTruth A term ->
    truth_denotes atomic_closure_truth_conditions A term.
Proof.
  intros A term H.
  exact H.
Qed.

Definition atomic_closure_evidence_backed_truth_sources :
  EvidenceBackedTruthConditionSources := {|
  evidence_denotes := AtomicClosureTruth;
  evidence_lexical_truth_break_application := fun n mods arg1 arg2 =>
      truth_evidence_intro
        (AtomicClosureTruth PropT (break n mods arg1 arg2))
        (atomic_closure_truth_break_application n mods arg1 arg2 (atomic_lexical_truth_break_application atomic_truth_facts n mods arg1 arg2));
  evidence_lexical_truth_butter_application := fun n mods arg1 arg2 =>
      truth_evidence_intro
        (AtomicClosureTruth PropT (butter n mods arg1 arg2))
        (atomic_closure_truth_butter_application n mods arg1 arg2 (atomic_lexical_truth_butter_application atomic_truth_facts n mods arg1 arg2));
  evidence_lexical_truth_eat_application := fun n mods arg1 arg2 =>
      truth_evidence_intro
        (AtomicClosureTruth Prop (eat n mods arg1 arg2))
        (atomic_closure_truth_eat_application n mods arg1 arg2 (atomic_lexical_truth_eat_application atomic_truth_facts n mods arg1 arg2));
  evidence_lexical_truth_knock_application := fun n mods arg1 =>
      truth_evidence_intro
        (AtomicClosureTruth PropT (knock n mods arg1))
        (atomic_closure_truth_knock_application n mods arg1 (atomic_lexical_truth_knock_application atomic_truth_facts n mods arg1));
  evidence_quantifier_truth_sigma_Entity := fun P h =>
      truth_evidence_intro
        (AtomicClosureTruth Prop (exists x : Entity, P x))
        (atomic_closure_truth_sigma_Entity P h);
  evidence_quantifier_truth_sigma_Food := fun P h =>
      truth_evidence_intro
        (AtomicClosureTruth Prop (exists x : Food, P x))
        (atomic_closure_truth_sigma_Food P h);
  evidence_quantifier_truth_sigma_State := fun P h =>
      truth_evidence_intro
        (AtomicClosureTruth Prop (exists x : State, P x))
        (atomic_closure_truth_sigma_State P h);
  evidence_quantifier_truth_sigma_StateScale := fun P h =>
      truth_evidence_intro
        (AtomicClosureTruth Prop (exists x : StateScale, P x))
        (atomic_closure_truth_sigma_StateScale P h);
  evidence_quantifier_truth_sigma_TransitionT := fun P h =>
      truth_evidence_intro
        (AtomicClosureTruth Prop (exists x : TransitionT, P x))
        (atomic_closure_truth_sigma_TransitionT P h);
  evidence_repetition_truth := fun n body h =>
      truth_evidence_intro
        (AtomicClosureTruth PropT (repeat n body))
        (atomic_closure_truth_repeat n body h);
  evidence_temporal_truth_at_T := fun marker body h =>
      truth_evidence_intro
        (AtomicClosureTruth PropT (at_T marker body))
        (atomic_closure_truth_at_T marker body h);
  evidence_temporal_truth_during_T := fun marker body h =>
      truth_evidence_intro
        (AtomicClosureTruth PropT (during_T marker body))
        (atomic_closure_truth_during_T marker body h);
  evidence_temporal_truth_before_T := fun marker body h =>
      truth_evidence_intro
        (AtomicClosureTruth PropT (before_T marker body))
        (atomic_closure_truth_before_T marker body h);
  evidence_temporal_truth_after_T := fun marker body h =>
      truth_evidence_intro
        (AtomicClosureTruth PropT (after_T marker body))
        (atomic_closure_truth_after_T marker body h);
  evidence_temporal_truth_until_T := fun marker body h =>
      truth_evidence_intro
        (AtomicClosureTruth PropT (until_T marker body))
        (atomic_closure_truth_until_T marker body h);
  evidence_temporal_truth_since_T := fun marker body h =>
      truth_evidence_intro
        (AtomicClosureTruth PropT (since_T marker body))
        (atomic_closure_truth_since_T marker body h);
  evidence_polarity_truth_not_T := fun body h =>
      truth_evidence_intro
        (AtomicClosureTruth PropT (not_T body))
        (atomic_closure_truth_not_T body h);
  evidence_transition_truth := fun theme scale source target =>
      truth_evidence_intro
        (AtomicClosureTruth TransitionT (Transition theme scale source target))
        (atomic_closure_truth_transition theme scale source target (atomic_transition_truth atomic_truth_facts theme scale source target));
  evidence_cause_truth := fun causer effect h =>
      truth_evidence_intro
        (AtomicClosureTruth PropT (Cause causer effect))
        (atomic_closure_truth_cause causer effect h)
|}.

Definition atomic_closure_evidence_backed_truth_kernel :
  ConcreteTruthConditionKernel :=
  concrete_kernel_from_evidence_sources
    atomic_closure_evidence_backed_truth_sources.

Definition atomic_closure_evidence_backed_truth_ledger :
  IndependentTruthConditionObligationLedger :=
  evidence_backed_truth_condition_ledger
    atomic_closure_evidence_backed_truth_sources.

Theorem atomic_closure_evidence_backed_truth_sources_exist :
  exists S : EvidenceBackedTruthConditionSources,
    S = atomic_closure_evidence_backed_truth_sources.
Proof.
  exists atomic_closure_evidence_backed_truth_sources.
  reflexivity.
Qed.

Theorem atomic_closure_evidence_backed_truth_kernel_exists :
  exists K : ConcreteTruthConditionKernel,
    K = atomic_closure_evidence_backed_truth_kernel.
Proof.
  exists atomic_closure_evidence_backed_truth_kernel.
  reflexivity.
Qed.

Theorem atomic_closure_evidence_backed_truth_ledger_exists :
  exists L : IndependentTruthConditionObligationLedger,
    L = atomic_closure_evidence_backed_truth_ledger.
Proof.
  exists atomic_closure_evidence_backed_truth_ledger.
  reflexivity.
Qed.

Theorem atomic_closure_evidence_backed_truth_sources_sound :
  forall A : Type, forall term : A,
    ModelInterpretable A term ->
    truth_denotes
      (ledger_truth_conditions
        atomic_closure_evidence_backed_truth_ledger)
      A term.
Proof.
  intros A term H.
  exact
    (evidence_backed_truth_condition_sources_sound
      atomic_closure_evidence_backed_truth_sources A term H).
Qed.

Inductive RegisteredStateTransitionTruth : Entity -> StateScale -> State -> State -> Prop :=
  | registered_transition_vase_integrity_scale_intact_to_broken :
      RegisteredStateTransitionTruth vase integrity_scale intact broken.

Theorem registered_state_transition_atomic_base_truth :
  forall theme : Entity, forall scale : StateScale,
  forall source : State, forall target : State,
    RegisteredStateTransitionTruth theme scale source target ->
    AtomicBaseTruth TransitionT (Transition theme scale source target).
Proof.
  intros theme scale source target H.
  induction H.
  - apply atomic_base_truth_transition.
Qed.

Inductive TransitionRefinedAtomicClosureTruth : forall A : Type, A -> Prop :=
  | transition_refined_truth_break_application : forall n : nat, forall mods : ModifierSeq n, forall arg1 : Entity, forall arg2 : Entity,
      AtomicBaseTruth PropT (break n mods arg1 arg2) ->
      TransitionRefinedAtomicClosureTruth PropT (break n mods arg1 arg2)
  | transition_refined_truth_butter_application : forall n : nat, forall mods : ModifierSeq n, forall arg1 : Entity, forall arg2 : Entity,
      AtomicBaseTruth PropT (butter n mods arg1 arg2) ->
      TransitionRefinedAtomicClosureTruth PropT (butter n mods arg1 arg2)
  | transition_refined_truth_eat_application : forall n : nat, forall mods : ModifierSeq n, forall arg1 : Entity, forall arg2 : Food,
      AtomicBaseTruth Prop (eat n mods arg1 arg2) ->
      TransitionRefinedAtomicClosureTruth Prop (eat n mods arg1 arg2)
  | transition_refined_truth_knock_application : forall n : nat, forall mods : ModifierSeq n, forall arg1 : Entity,
      AtomicBaseTruth PropT (knock n mods arg1) ->
      TransitionRefinedAtomicClosureTruth PropT (knock n mods arg1)
  | transition_refined_truth_sigma_Entity : forall P : Entity -> Prop,
      (forall x : Entity, TransitionRefinedAtomicClosureTruth Prop (P x)) ->
      TransitionRefinedAtomicClosureTruth Prop (exists x : Entity, P x)
  | transition_refined_truth_sigma_Food : forall P : Food -> Prop,
      (forall x : Food, TransitionRefinedAtomicClosureTruth Prop (P x)) ->
      TransitionRefinedAtomicClosureTruth Prop (exists x : Food, P x)
  | transition_refined_truth_sigma_State : forall P : State -> Prop,
      (forall x : State, TransitionRefinedAtomicClosureTruth Prop (P x)) ->
      TransitionRefinedAtomicClosureTruth Prop (exists x : State, P x)
  | transition_refined_truth_sigma_StateScale : forall P : StateScale -> Prop,
      (forall x : StateScale, TransitionRefinedAtomicClosureTruth Prop (P x)) ->
      TransitionRefinedAtomicClosureTruth Prop (exists x : StateScale, P x)
  | transition_refined_truth_sigma_TransitionT : forall P : TransitionT -> Prop,
      (forall x : TransitionT, TransitionRefinedAtomicClosureTruth Prop (P x)) ->
      TransitionRefinedAtomicClosureTruth Prop (exists x : TransitionT, P x)
  | transition_refined_truth_repeat : forall n : nat, forall body : PropT,
      TransitionRefinedAtomicClosureTruth PropT body ->
      TransitionRefinedAtomicClosureTruth PropT (repeat n body)
  | transition_refined_truth_at_T : forall marker : Entity, forall body : PropT,
      TransitionRefinedAtomicClosureTruth PropT body ->
      TransitionRefinedAtomicClosureTruth PropT (at_T marker body)
  | transition_refined_truth_during_T : forall marker : Entity, forall body : PropT,
      TransitionRefinedAtomicClosureTruth PropT body ->
      TransitionRefinedAtomicClosureTruth PropT (during_T marker body)
  | transition_refined_truth_before_T : forall marker : Entity, forall body : PropT,
      TransitionRefinedAtomicClosureTruth PropT body ->
      TransitionRefinedAtomicClosureTruth PropT (before_T marker body)
  | transition_refined_truth_after_T : forall marker : Entity, forall body : PropT,
      TransitionRefinedAtomicClosureTruth PropT body ->
      TransitionRefinedAtomicClosureTruth PropT (after_T marker body)
  | transition_refined_truth_until_T : forall marker : Entity, forall body : PropT,
      TransitionRefinedAtomicClosureTruth PropT body ->
      TransitionRefinedAtomicClosureTruth PropT (until_T marker body)
  | transition_refined_truth_since_T : forall marker : Entity, forall body : PropT,
      TransitionRefinedAtomicClosureTruth PropT body ->
      TransitionRefinedAtomicClosureTruth PropT (since_T marker body)
  | transition_refined_truth_not_T : forall body : PropT,
      TransitionRefinedAtomicClosureTruth PropT body ->
      TransitionRefinedAtomicClosureTruth PropT (not_T body)
  | transition_refined_truth_transition : forall theme : Entity, forall scale : StateScale,
      forall source : State, forall target : State,
      RegisteredStateTransitionTruth theme scale source target ->
      TransitionRefinedAtomicClosureTruth TransitionT (Transition theme scale source target)
  | transition_refined_truth_cause : forall causer : Entity, forall effect : TransitionT,
      TransitionRefinedAtomicClosureTruth TransitionT effect ->
      TransitionRefinedAtomicClosureTruth PropT (Cause causer effect).

Theorem transition_refined_atomic_closure_truth_implies_atomic_closure_truth :
  forall A : Type, forall term : A,
    TransitionRefinedAtomicClosureTruth A term ->
    AtomicClosureTruth A term.
Proof.
  intros A term H.
  induction H.
  - apply atomic_closure_truth_break_application.
    assumption.
  - apply atomic_closure_truth_butter_application.
    assumption.
  - apply atomic_closure_truth_eat_application.
    assumption.
  - apply atomic_closure_truth_knock_application.
    assumption.
  - apply atomic_closure_truth_sigma_Entity.
    assumption.
  - apply atomic_closure_truth_sigma_Food.
    assumption.
  - apply atomic_closure_truth_sigma_State.
    assumption.
  - apply atomic_closure_truth_sigma_StateScale.
    assumption.
  - apply atomic_closure_truth_sigma_TransitionT.
    assumption.
  - apply atomic_closure_truth_repeat. assumption.
  - apply atomic_closure_truth_at_T. assumption.
  - apply atomic_closure_truth_during_T. assumption.
  - apply atomic_closure_truth_before_T. assumption.
  - apply atomic_closure_truth_after_T. assumption.
  - apply atomic_closure_truth_until_T. assumption.
  - apply atomic_closure_truth_since_T. assumption.
  - apply atomic_closure_truth_not_T. assumption.
  - apply atomic_closure_truth_transition.
    apply registered_state_transition_atomic_base_truth.
    assumption.
  - apply atomic_closure_truth_cause. assumption.
Qed.

Record RegisteredTruthConditionSpec : Type := {
  registered_truth_denotes : forall A : Type, A -> Prop;
  registered_truth_break_application : forall n : nat, forall mods : ModifierSeq n, forall arg1 : Entity, forall arg2 : Entity,
      registered_truth_denotes PropT (break n mods arg1 arg2);
  registered_truth_butter_application : forall n : nat, forall mods : ModifierSeq n, forall arg1 : Entity, forall arg2 : Entity,
      registered_truth_denotes PropT (butter n mods arg1 arg2);
  registered_truth_eat_application : forall n : nat, forall mods : ModifierSeq n, forall arg1 : Entity, forall arg2 : Food,
      registered_truth_denotes Prop (eat n mods arg1 arg2);
  registered_truth_knock_application : forall n : nat, forall mods : ModifierSeq n, forall arg1 : Entity,
      registered_truth_denotes PropT (knock n mods arg1);
  registered_truth_sigma_Entity : forall P : Entity -> Prop,
      (forall x : Entity, registered_truth_denotes Prop (P x)) ->
      registered_truth_denotes Prop (exists x : Entity, P x);
  registered_truth_sigma_Food : forall P : Food -> Prop,
      (forall x : Food, registered_truth_denotes Prop (P x)) ->
      registered_truth_denotes Prop (exists x : Food, P x);
  registered_truth_sigma_State : forall P : State -> Prop,
      (forall x : State, registered_truth_denotes Prop (P x)) ->
      registered_truth_denotes Prop (exists x : State, P x);
  registered_truth_sigma_StateScale : forall P : StateScale -> Prop,
      (forall x : StateScale, registered_truth_denotes Prop (P x)) ->
      registered_truth_denotes Prop (exists x : StateScale, P x);
  registered_truth_sigma_TransitionT : forall P : TransitionT -> Prop,
      (forall x : TransitionT, registered_truth_denotes Prop (P x)) ->
      registered_truth_denotes Prop (exists x : TransitionT, P x);
  registered_truth_repeat : forall n : nat, forall body : PropT,
      registered_truth_denotes PropT body ->
      registered_truth_denotes PropT (repeat n body);
  registered_truth_at_T : forall marker : Entity, forall body : PropT,
      registered_truth_denotes PropT body ->
      registered_truth_denotes PropT (at_T marker body);
  registered_truth_during_T : forall marker : Entity, forall body : PropT,
      registered_truth_denotes PropT body ->
      registered_truth_denotes PropT (during_T marker body);
  registered_truth_before_T : forall marker : Entity, forall body : PropT,
      registered_truth_denotes PropT body ->
      registered_truth_denotes PropT (before_T marker body);
  registered_truth_after_T : forall marker : Entity, forall body : PropT,
      registered_truth_denotes PropT body ->
      registered_truth_denotes PropT (after_T marker body);
  registered_truth_until_T : forall marker : Entity, forall body : PropT,
      registered_truth_denotes PropT body ->
      registered_truth_denotes PropT (until_T marker body);
  registered_truth_since_T : forall marker : Entity, forall body : PropT,
      registered_truth_denotes PropT body ->
      registered_truth_denotes PropT (since_T marker body);
  registered_truth_not_T : forall body : PropT,
      registered_truth_denotes PropT body ->
      registered_truth_denotes PropT (not_T body);
  registered_truth_transition : forall theme : Entity, forall scale : StateScale, forall source : State, forall target : State,
      RegisteredStateTransitionTruth theme scale source target ->
      registered_truth_denotes TransitionT (Transition theme scale source target);
  registered_truth_cause : forall causer : Entity, forall effect : TransitionT,
      registered_truth_denotes TransitionT effect ->
      registered_truth_denotes PropT (Cause causer effect)
}.

Definition transition_refined_registered_truth_denotes : forall A : Type, A -> Prop :=
  TransitionRefinedAtomicClosureTruth.

Definition transition_refined_registered_truth_conditions : RegisteredTruthConditionSpec := {|
  registered_truth_denotes := transition_refined_registered_truth_denotes;
  registered_truth_break_application := fun n mods arg1 arg2 => transition_refined_truth_break_application n mods arg1 arg2 (atomic_base_truth_break_application n mods arg1 arg2);
  registered_truth_butter_application := fun n mods arg1 arg2 => transition_refined_truth_butter_application n mods arg1 arg2 (atomic_base_truth_butter_application n mods arg1 arg2);
  registered_truth_eat_application := fun n mods arg1 arg2 => transition_refined_truth_eat_application n mods arg1 arg2 (atomic_base_truth_eat_application n mods arg1 arg2);
  registered_truth_knock_application := fun n mods arg1 => transition_refined_truth_knock_application n mods arg1 (atomic_base_truth_knock_application n mods arg1);
  registered_truth_sigma_Entity := fun P h => transition_refined_truth_sigma_Entity P h;
  registered_truth_sigma_Food := fun P h => transition_refined_truth_sigma_Food P h;
  registered_truth_sigma_State := fun P h => transition_refined_truth_sigma_State P h;
  registered_truth_sigma_StateScale := fun P h => transition_refined_truth_sigma_StateScale P h;
  registered_truth_sigma_TransitionT := fun P h => transition_refined_truth_sigma_TransitionT P h;
  registered_truth_repeat := fun n body h => transition_refined_truth_repeat n body h;
  registered_truth_at_T := fun marker body h => transition_refined_truth_at_T marker body h;
  registered_truth_during_T := fun marker body h => transition_refined_truth_during_T marker body h;
  registered_truth_before_T := fun marker body h => transition_refined_truth_before_T marker body h;
  registered_truth_after_T := fun marker body h => transition_refined_truth_after_T marker body h;
  registered_truth_until_T := fun marker body h => transition_refined_truth_until_T marker body h;
  registered_truth_since_T := fun marker body h => transition_refined_truth_since_T marker body h;
  registered_truth_not_T := fun body h => transition_refined_truth_not_T body h;
  registered_truth_transition := fun theme scale source target h => transition_refined_truth_transition theme scale source target h;
  registered_truth_cause := fun causer effect h => transition_refined_truth_cause causer effect h
|}.

Theorem transition_refined_registered_truth_condition_spec_exists :
  exists R : RegisteredTruthConditionSpec,
    R = transition_refined_registered_truth_conditions.
Proof.
  exists transition_refined_registered_truth_conditions. reflexivity.
Qed.

Theorem transition_refined_registered_truth_conditions_denote_transition_refined :
  forall A : Type, forall term : A,
    TransitionRefinedAtomicClosureTruth A term ->
    registered_truth_denotes transition_refined_registered_truth_conditions A term.
Proof.
  intros A term H.
  exact H.
Qed.

Theorem transition_refined_registered_truth_conditions_imply_atomic_closure :
  forall A : Type, forall term : A,
    registered_truth_denotes transition_refined_registered_truth_conditions A term ->
    AtomicClosureTruth A term.
Proof.
  intros A term H.
  apply transition_refined_atomic_closure_truth_implies_atomic_closure_truth.
  exact H.
Qed.

Inductive RegisteredLexicalApplicationTruth : forall A : Type, A -> Prop :=
  | registered_lexical_break_0_John_vase :
      RegisteredLexicalApplicationTruth PropT (break 0 mods_nil John vase)
  | registered_lexical_butter_2_slowly_in_bathroom_John_toast :
      RegisteredLexicalApplicationTruth PropT (butter 2 (mods_cons 1 slowly (mods_cons 0 in_bathroom mods_nil)) John toast)
  | registered_lexical_eat_0_John_x_theme : forall x_theme : Food,
      RegisteredLexicalApplicationTruth Prop (eat 0 mods_nil John x_theme)
  | registered_lexical_knock_0_John :
      RegisteredLexicalApplicationTruth PropT (knock 0 mods_nil John).

Theorem registered_lexical_application_atomic_base_truth :
  forall A : Type, forall term : A,
    RegisteredLexicalApplicationTruth A term -> AtomicBaseTruth A term.
Proof.
  intros A term H.
  induction H.
  - apply atomic_base_truth_break_application.
  - apply atomic_base_truth_butter_application.
  - apply atomic_base_truth_eat_application.
  - apply atomic_base_truth_knock_application.
Qed.

Theorem registered_lexical_application_atomic_closure_truth :
  forall A : Type, forall term : A,
    RegisteredLexicalApplicationTruth A term -> AtomicClosureTruth A term.
Proof.
  intros A term H.
  induction H.
  - apply atomic_closure_truth_break_application.
    apply atomic_base_truth_break_application.
  - apply atomic_closure_truth_butter_application.
    apply atomic_base_truth_butter_application.
  - apply atomic_closure_truth_eat_application.
    apply atomic_base_truth_eat_application.
  - apply atomic_closure_truth_knock_application.
    apply atomic_base_truth_knock_application.
Qed.

Inductive FullyRegisteredAtomicClosureTruth : forall A : Type, A -> Prop :=
  | fully_registered_atomic_truth_lexical_application :
      forall A : Type, forall term : A,
      RegisteredLexicalApplicationTruth A term ->
      FullyRegisteredAtomicClosureTruth A term
  | fully_registered_atomic_truth_sigma_Entity : forall P : Entity -> Prop,
      (forall x : Entity, FullyRegisteredAtomicClosureTruth Prop (P x)) ->
      FullyRegisteredAtomicClosureTruth Prop (exists x : Entity, P x)
  | fully_registered_atomic_truth_sigma_Food : forall P : Food -> Prop,
      (forall x : Food, FullyRegisteredAtomicClosureTruth Prop (P x)) ->
      FullyRegisteredAtomicClosureTruth Prop (exists x : Food, P x)
  | fully_registered_atomic_truth_sigma_State : forall P : State -> Prop,
      (forall x : State, FullyRegisteredAtomicClosureTruth Prop (P x)) ->
      FullyRegisteredAtomicClosureTruth Prop (exists x : State, P x)
  | fully_registered_atomic_truth_sigma_StateScale : forall P : StateScale -> Prop,
      (forall x : StateScale, FullyRegisteredAtomicClosureTruth Prop (P x)) ->
      FullyRegisteredAtomicClosureTruth Prop (exists x : StateScale, P x)
  | fully_registered_atomic_truth_sigma_TransitionT : forall P : TransitionT -> Prop,
      (forall x : TransitionT, FullyRegisteredAtomicClosureTruth Prop (P x)) ->
      FullyRegisteredAtomicClosureTruth Prop (exists x : TransitionT, P x)
  | fully_registered_atomic_truth_repeat : forall n : nat, forall body : PropT,
      FullyRegisteredAtomicClosureTruth PropT body ->
      FullyRegisteredAtomicClosureTruth PropT (repeat n body)
  | fully_registered_atomic_truth_at_T : forall marker : Entity, forall body : PropT,
      FullyRegisteredAtomicClosureTruth PropT body ->
      FullyRegisteredAtomicClosureTruth PropT (at_T marker body)
  | fully_registered_atomic_truth_during_T : forall marker : Entity, forall body : PropT,
      FullyRegisteredAtomicClosureTruth PropT body ->
      FullyRegisteredAtomicClosureTruth PropT (during_T marker body)
  | fully_registered_atomic_truth_before_T : forall marker : Entity, forall body : PropT,
      FullyRegisteredAtomicClosureTruth PropT body ->
      FullyRegisteredAtomicClosureTruth PropT (before_T marker body)
  | fully_registered_atomic_truth_after_T : forall marker : Entity, forall body : PropT,
      FullyRegisteredAtomicClosureTruth PropT body ->
      FullyRegisteredAtomicClosureTruth PropT (after_T marker body)
  | fully_registered_atomic_truth_until_T : forall marker : Entity, forall body : PropT,
      FullyRegisteredAtomicClosureTruth PropT body ->
      FullyRegisteredAtomicClosureTruth PropT (until_T marker body)
  | fully_registered_atomic_truth_since_T : forall marker : Entity, forall body : PropT,
      FullyRegisteredAtomicClosureTruth PropT body ->
      FullyRegisteredAtomicClosureTruth PropT (since_T marker body)
  | fully_registered_atomic_truth_not_T : forall body : PropT,
      FullyRegisteredAtomicClosureTruth PropT body ->
      FullyRegisteredAtomicClosureTruth PropT (not_T body)
  | fully_registered_atomic_truth_transition : forall theme : Entity, forall scale : StateScale,
      forall source : State, forall target : State,
      RegisteredStateTransitionTruth theme scale source target ->
      FullyRegisteredAtomicClosureTruth TransitionT (Transition theme scale source target)
  | fully_registered_atomic_truth_cause : forall causer : Entity, forall effect : TransitionT,
      FullyRegisteredAtomicClosureTruth TransitionT effect ->
      FullyRegisteredAtomicClosureTruth PropT (Cause causer effect).

Theorem fully_registered_atomic_closure_truth_implies_atomic_closure_truth :
  forall A : Type, forall term : A,
    FullyRegisteredAtomicClosureTruth A term -> AtomicClosureTruth A term.
Proof.
  intros A term H.
  induction H.
  - apply registered_lexical_application_atomic_closure_truth.
    assumption.
  - apply atomic_closure_truth_sigma_Entity.
    assumption.
  - apply atomic_closure_truth_sigma_Food.
    assumption.
  - apply atomic_closure_truth_sigma_State.
    assumption.
  - apply atomic_closure_truth_sigma_StateScale.
    assumption.
  - apply atomic_closure_truth_sigma_TransitionT.
    assumption.
  - apply atomic_closure_truth_repeat. assumption.
  - apply atomic_closure_truth_at_T. assumption.
  - apply atomic_closure_truth_during_T. assumption.
  - apply atomic_closure_truth_before_T. assumption.
  - apply atomic_closure_truth_after_T. assumption.
  - apply atomic_closure_truth_until_T. assumption.
  - apply atomic_closure_truth_since_T. assumption.
  - apply atomic_closure_truth_not_T. assumption.
  - apply atomic_closure_truth_transition.
    apply registered_state_transition_atomic_base_truth.
    assumption.
  - apply atomic_closure_truth_cause. assumption.
Qed.

Record FullyRegisteredTruthConditionSpec : Type := {
  fully_registered_truth_denotes : forall A : Type, A -> Prop;
  fully_registered_truth_lexical_application :
      forall A : Type, forall term : A,
      RegisteredLexicalApplicationTruth A term ->
      fully_registered_truth_denotes A term;
  fully_registered_truth_sigma_Entity : forall P : Entity -> Prop,
      (forall x : Entity, fully_registered_truth_denotes Prop (P x)) ->
      fully_registered_truth_denotes Prop (exists x : Entity, P x);
  fully_registered_truth_sigma_Food : forall P : Food -> Prop,
      (forall x : Food, fully_registered_truth_denotes Prop (P x)) ->
      fully_registered_truth_denotes Prop (exists x : Food, P x);
  fully_registered_truth_sigma_State : forall P : State -> Prop,
      (forall x : State, fully_registered_truth_denotes Prop (P x)) ->
      fully_registered_truth_denotes Prop (exists x : State, P x);
  fully_registered_truth_sigma_StateScale : forall P : StateScale -> Prop,
      (forall x : StateScale, fully_registered_truth_denotes Prop (P x)) ->
      fully_registered_truth_denotes Prop (exists x : StateScale, P x);
  fully_registered_truth_sigma_TransitionT : forall P : TransitionT -> Prop,
      (forall x : TransitionT, fully_registered_truth_denotes Prop (P x)) ->
      fully_registered_truth_denotes Prop (exists x : TransitionT, P x);
  fully_registered_truth_repeat : forall n : nat, forall body : PropT,
      fully_registered_truth_denotes PropT body ->
      fully_registered_truth_denotes PropT (repeat n body);
  fully_registered_truth_at_T : forall marker : Entity, forall body : PropT,
      fully_registered_truth_denotes PropT body ->
      fully_registered_truth_denotes PropT (at_T marker body);
  fully_registered_truth_during_T : forall marker : Entity, forall body : PropT,
      fully_registered_truth_denotes PropT body ->
      fully_registered_truth_denotes PropT (during_T marker body);
  fully_registered_truth_before_T : forall marker : Entity, forall body : PropT,
      fully_registered_truth_denotes PropT body ->
      fully_registered_truth_denotes PropT (before_T marker body);
  fully_registered_truth_after_T : forall marker : Entity, forall body : PropT,
      fully_registered_truth_denotes PropT body ->
      fully_registered_truth_denotes PropT (after_T marker body);
  fully_registered_truth_until_T : forall marker : Entity, forall body : PropT,
      fully_registered_truth_denotes PropT body ->
      fully_registered_truth_denotes PropT (until_T marker body);
  fully_registered_truth_since_T : forall marker : Entity, forall body : PropT,
      fully_registered_truth_denotes PropT body ->
      fully_registered_truth_denotes PropT (since_T marker body);
  fully_registered_truth_not_T : forall body : PropT,
      fully_registered_truth_denotes PropT body ->
      fully_registered_truth_denotes PropT (not_T body);
  fully_registered_truth_transition : forall theme : Entity, forall scale : StateScale,
      forall source : State, forall target : State,
      RegisteredStateTransitionTruth theme scale source target ->
      fully_registered_truth_denotes TransitionT (Transition theme scale source target);
  fully_registered_truth_cause : forall causer : Entity, forall effect : TransitionT,
      fully_registered_truth_denotes TransitionT effect ->
      fully_registered_truth_denotes PropT (Cause causer effect)
}.

Definition fully_registered_atomic_truth_denotes : forall A : Type, A -> Prop :=
  FullyRegisteredAtomicClosureTruth.

Definition fully_registered_truth_conditions : FullyRegisteredTruthConditionSpec := {|
  fully_registered_truth_denotes := fully_registered_atomic_truth_denotes;
  fully_registered_truth_lexical_application := fun A term h => fully_registered_atomic_truth_lexical_application A term h;
  fully_registered_truth_sigma_Entity := fun P h => fully_registered_atomic_truth_sigma_Entity P h;
  fully_registered_truth_sigma_Food := fun P h => fully_registered_atomic_truth_sigma_Food P h;
  fully_registered_truth_sigma_State := fun P h => fully_registered_atomic_truth_sigma_State P h;
  fully_registered_truth_sigma_StateScale := fun P h => fully_registered_atomic_truth_sigma_StateScale P h;
  fully_registered_truth_sigma_TransitionT := fun P h => fully_registered_atomic_truth_sigma_TransitionT P h;
  fully_registered_truth_repeat := fun n body h => fully_registered_atomic_truth_repeat n body h;
  fully_registered_truth_at_T := fun marker body h => fully_registered_atomic_truth_at_T marker body h;
  fully_registered_truth_during_T := fun marker body h => fully_registered_atomic_truth_during_T marker body h;
  fully_registered_truth_before_T := fun marker body h => fully_registered_atomic_truth_before_T marker body h;
  fully_registered_truth_after_T := fun marker body h => fully_registered_atomic_truth_after_T marker body h;
  fully_registered_truth_until_T := fun marker body h => fully_registered_atomic_truth_until_T marker body h;
  fully_registered_truth_since_T := fun marker body h => fully_registered_atomic_truth_since_T marker body h;
  fully_registered_truth_not_T := fun body h => fully_registered_atomic_truth_not_T body h;
  fully_registered_truth_transition := fun theme scale source target h => fully_registered_atomic_truth_transition theme scale source target h;
  fully_registered_truth_cause := fun causer effect h => fully_registered_atomic_truth_cause causer effect h
|}.

Theorem fully_registered_truth_condition_spec_exists :
  exists F : FullyRegisteredTruthConditionSpec,
    F = fully_registered_truth_conditions.
Proof.
  exists fully_registered_truth_conditions. reflexivity.
Qed.

Theorem fully_registered_truth_conditions_denote_fully_registered :
  forall A : Type, forall term : A,
    FullyRegisteredAtomicClosureTruth A term ->
    fully_registered_truth_denotes fully_registered_truth_conditions A term.
Proof.
  intros A term H.
  exact H.
Qed.

Theorem fully_registered_truth_conditions_imply_atomic_closure :
  forall A : Type, forall term : A,
    fully_registered_truth_denotes fully_registered_truth_conditions A term ->
    AtomicClosureTruth A term.
Proof.
  intros A term H.
  apply fully_registered_atomic_closure_truth_implies_atomic_closure_truth.
  exact H.
Qed.

Record RegisteredLexicalTruthModel : Type := {
  registered_lexical_model_denotes : forall A : Type, A -> Prop;
  registered_lexical_model_lexical_application :
      forall A : Type, forall term : A,
      RegisteredLexicalApplicationTruth A term ->
      registered_lexical_model_denotes A term;
  registered_lexical_model_sigma_Entity : forall P : Entity -> Prop,
      (forall x : Entity, registered_lexical_model_denotes Prop (P x)) ->
      registered_lexical_model_denotes Prop (exists x : Entity, P x);
  registered_lexical_model_sigma_Food : forall P : Food -> Prop,
      (forall x : Food, registered_lexical_model_denotes Prop (P x)) ->
      registered_lexical_model_denotes Prop (exists x : Food, P x);
  registered_lexical_model_sigma_State : forall P : State -> Prop,
      (forall x : State, registered_lexical_model_denotes Prop (P x)) ->
      registered_lexical_model_denotes Prop (exists x : State, P x);
  registered_lexical_model_sigma_StateScale : forall P : StateScale -> Prop,
      (forall x : StateScale, registered_lexical_model_denotes Prop (P x)) ->
      registered_lexical_model_denotes Prop (exists x : StateScale, P x);
  registered_lexical_model_sigma_TransitionT : forall P : TransitionT -> Prop,
      (forall x : TransitionT, registered_lexical_model_denotes Prop (P x)) ->
      registered_lexical_model_denotes Prop (exists x : TransitionT, P x);
  registered_lexical_model_repeat : forall n : nat, forall body : PropT,
      registered_lexical_model_denotes PropT body ->
      registered_lexical_model_denotes PropT (repeat n body);
  registered_lexical_model_at_T : forall marker : Entity, forall body : PropT,
      registered_lexical_model_denotes PropT body ->
      registered_lexical_model_denotes PropT (at_T marker body);
  registered_lexical_model_during_T : forall marker : Entity, forall body : PropT,
      registered_lexical_model_denotes PropT body ->
      registered_lexical_model_denotes PropT (during_T marker body);
  registered_lexical_model_before_T : forall marker : Entity, forall body : PropT,
      registered_lexical_model_denotes PropT body ->
      registered_lexical_model_denotes PropT (before_T marker body);
  registered_lexical_model_after_T : forall marker : Entity, forall body : PropT,
      registered_lexical_model_denotes PropT body ->
      registered_lexical_model_denotes PropT (after_T marker body);
  registered_lexical_model_until_T : forall marker : Entity, forall body : PropT,
      registered_lexical_model_denotes PropT body ->
      registered_lexical_model_denotes PropT (until_T marker body);
  registered_lexical_model_since_T : forall marker : Entity, forall body : PropT,
      registered_lexical_model_denotes PropT body ->
      registered_lexical_model_denotes PropT (since_T marker body);
  registered_lexical_model_not_T : forall body : PropT,
      registered_lexical_model_denotes PropT body ->
      registered_lexical_model_denotes PropT (not_T body);
  registered_lexical_model_transition : forall theme : Entity, forall scale : StateScale,
      forall source : State, forall target : State,
      RegisteredStateTransitionTruth theme scale source target ->
      registered_lexical_model_denotes TransitionT (Transition theme scale source target);
  registered_lexical_model_cause : forall causer : Entity, forall effect : TransitionT,
      registered_lexical_model_denotes TransitionT effect ->
      registered_lexical_model_denotes PropT (Cause causer effect)
}.

Definition fully_registered_truth_conditions_from_registered_lexical_model
  (M : RegisteredLexicalTruthModel) : FullyRegisteredTruthConditionSpec := {|
  fully_registered_truth_denotes := registered_lexical_model_denotes M;
  fully_registered_truth_lexical_application := registered_lexical_model_lexical_application M;
  fully_registered_truth_sigma_Entity := registered_lexical_model_sigma_Entity M;
  fully_registered_truth_sigma_Food := registered_lexical_model_sigma_Food M;
  fully_registered_truth_sigma_State := registered_lexical_model_sigma_State M;
  fully_registered_truth_sigma_StateScale := registered_lexical_model_sigma_StateScale M;
  fully_registered_truth_sigma_TransitionT := registered_lexical_model_sigma_TransitionT M;
  fully_registered_truth_repeat := registered_lexical_model_repeat M;
  fully_registered_truth_at_T := registered_lexical_model_at_T M;
  fully_registered_truth_during_T := registered_lexical_model_during_T M;
  fully_registered_truth_before_T := registered_lexical_model_before_T M;
  fully_registered_truth_after_T := registered_lexical_model_after_T M;
  fully_registered_truth_until_T := registered_lexical_model_until_T M;
  fully_registered_truth_since_T := registered_lexical_model_since_T M;
  fully_registered_truth_not_T := registered_lexical_model_not_T M;
  fully_registered_truth_transition := registered_lexical_model_transition M;
  fully_registered_truth_cause := registered_lexical_model_cause M
|}.

Definition registered_lexical_truth_model_denotes : forall A : Type, A -> Prop :=
  FullyRegisteredAtomicClosureTruth.

Definition registered_lexical_truth_model : RegisteredLexicalTruthModel := {|
  registered_lexical_model_denotes := registered_lexical_truth_model_denotes;
  registered_lexical_model_lexical_application := fun A term h => fully_registered_atomic_truth_lexical_application A term h;
  registered_lexical_model_sigma_Entity := fun P h => fully_registered_atomic_truth_sigma_Entity P h;
  registered_lexical_model_sigma_Food := fun P h => fully_registered_atomic_truth_sigma_Food P h;
  registered_lexical_model_sigma_State := fun P h => fully_registered_atomic_truth_sigma_State P h;
  registered_lexical_model_sigma_StateScale := fun P h => fully_registered_atomic_truth_sigma_StateScale P h;
  registered_lexical_model_sigma_TransitionT := fun P h => fully_registered_atomic_truth_sigma_TransitionT P h;
  registered_lexical_model_repeat := fun n body h => fully_registered_atomic_truth_repeat n body h;
  registered_lexical_model_at_T := fun marker body h => fully_registered_atomic_truth_at_T marker body h;
  registered_lexical_model_during_T := fun marker body h => fully_registered_atomic_truth_during_T marker body h;
  registered_lexical_model_before_T := fun marker body h => fully_registered_atomic_truth_before_T marker body h;
  registered_lexical_model_after_T := fun marker body h => fully_registered_atomic_truth_after_T marker body h;
  registered_lexical_model_until_T := fun marker body h => fully_registered_atomic_truth_until_T marker body h;
  registered_lexical_model_since_T := fun marker body h => fully_registered_atomic_truth_since_T marker body h;
  registered_lexical_model_not_T := fun body h => fully_registered_atomic_truth_not_T body h;
  registered_lexical_model_transition := fun theme scale source target h => fully_registered_atomic_truth_transition theme scale source target h;
  registered_lexical_model_cause := fun causer effect h => fully_registered_atomic_truth_cause causer effect h
|}.

Definition registered_lexical_truth_conditions_from_model :
  FullyRegisteredTruthConditionSpec :=
  fully_registered_truth_conditions_from_registered_lexical_model
    registered_lexical_truth_model.

Theorem registered_lexical_truth_model_exists :
  exists M : RegisteredLexicalTruthModel,
    M = registered_lexical_truth_model.
Proof.
  exists registered_lexical_truth_model. reflexivity.
Qed.

Theorem registered_lexical_truth_conditions_from_model_exists :
  exists F : FullyRegisteredTruthConditionSpec,
    F = registered_lexical_truth_conditions_from_model.
Proof.
  exists registered_lexical_truth_conditions_from_model. reflexivity.
Qed.

Theorem registered_lexical_truth_model_denotes_fully_registered :
  forall A : Type, forall term : A,
    FullyRegisteredAtomicClosureTruth A term ->
    registered_lexical_model_denotes registered_lexical_truth_model A term.
Proof.
  intros A term H.
  exact H.
Qed.

Theorem registered_lexical_truth_conditions_from_model_denote_fully_registered :
  forall A : Type, forall term : A,
    FullyRegisteredAtomicClosureTruth A term ->
    fully_registered_truth_denotes registered_lexical_truth_conditions_from_model A term.
Proof.
  intros A term H.
  exact H.
Qed.

Theorem registered_lexical_truth_conditions_from_model_imply_atomic_closure :
  forall A : Type, forall term : A,
    fully_registered_truth_denotes registered_lexical_truth_conditions_from_model A term ->
    AtomicClosureTruth A term.
Proof.
  intros A term H.
  apply fully_registered_atomic_closure_truth_implies_atomic_closure_truth.
  exact H.
Qed.

Inductive ConcreteRegisteredAtomicTruth : forall A : Type, A -> Prop :=
  | concrete_registered_atomic_truth_lexical_application :
      forall A : Type, forall term : A,
      RegisteredLexicalApplicationTruth A term ->
      ConcreteRegisteredAtomicTruth A term
  | concrete_registered_atomic_truth_transition :
      forall theme : Entity, forall scale : StateScale,
      forall source : State, forall target : State,
      RegisteredStateTransitionTruth theme scale source target ->
      ConcreteRegisteredAtomicTruth TransitionT
        (Transition theme scale source target).

Record ConcreteRegisteredTruthBasis : Type := {
  concrete_registered_basis_denotes : forall A : Type, A -> Prop;
  concrete_registered_basis_lexical_application :
      forall A : Type, forall term : A,
      RegisteredLexicalApplicationTruth A term ->
      concrete_registered_basis_denotes A term;
  concrete_registered_basis_transition :
      forall theme : Entity, forall scale : StateScale,
      forall source : State, forall target : State,
      RegisteredStateTransitionTruth theme scale source target ->
      concrete_registered_basis_denotes TransitionT
        (Transition theme scale source target)
}.

Definition concrete_registered_truth_basis :
  ConcreteRegisteredTruthBasis := {|
  concrete_registered_basis_denotes := ConcreteRegisteredAtomicTruth;
  concrete_registered_basis_lexical_application :=
    fun A term h =>
      concrete_registered_atomic_truth_lexical_application A term h;
  concrete_registered_basis_transition :=
    fun theme scale source target h =>
      concrete_registered_atomic_truth_transition theme scale source target h
|}.

Theorem concrete_registered_truth_basis_exists :
  exists B : ConcreteRegisteredTruthBasis,
    B = concrete_registered_truth_basis.
Proof.
  exists concrete_registered_truth_basis. reflexivity.
Qed.

Theorem concrete_registered_atomic_truth_implies_atomic_base_truth :
  forall A : Type, forall term : A,
    ConcreteRegisteredAtomicTruth A term -> AtomicBaseTruth A term.
Proof.
  intros A term H.
  induction H.
  - apply registered_lexical_application_atomic_base_truth.
    assumption.
  - apply registered_state_transition_atomic_base_truth.
    assumption.
Qed.

Record ConcreteRegisteredAtomicModel : Type := {
  concrete_registered_atom_model_denotes : forall A : Type, A -> Prop;
  concrete_registered_atom_model_lexical_application :
      forall A : Type, forall term : A,
      RegisteredLexicalApplicationTruth A term ->
      concrete_registered_atom_model_denotes A term;
  concrete_registered_atom_model_transition :
      forall theme : Entity, forall scale : StateScale,
      forall source : State, forall target : State,
      RegisteredStateTransitionTruth theme scale source target ->
      concrete_registered_atom_model_denotes TransitionT
        (Transition theme scale source target);
  concrete_registered_atom_model_sound :
      forall A : Type, forall term : A,
      concrete_registered_atom_model_denotes A term ->
      AtomicBaseTruth A term
}.

Definition concrete_registered_atomic_model :
  ConcreteRegisteredAtomicModel := {|
  concrete_registered_atom_model_denotes := ConcreteRegisteredAtomicTruth;
  concrete_registered_atom_model_lexical_application :=
    fun A term h =>
      concrete_registered_atomic_truth_lexical_application A term h;
  concrete_registered_atom_model_transition :=
    fun theme scale source target h =>
      concrete_registered_atomic_truth_transition theme scale source target h;
  concrete_registered_atom_model_sound :=
    concrete_registered_atomic_truth_implies_atomic_base_truth
|}.

Theorem concrete_registered_atomic_model_exists :
  exists M : ConcreteRegisteredAtomicModel,
    M = concrete_registered_atomic_model.
Proof.
  exists concrete_registered_atomic_model. reflexivity.
Qed.

Theorem concrete_registered_atomic_model_denotes_atomic_base_truth :
  forall A : Type, forall term : A,
    concrete_registered_atom_model_denotes
      concrete_registered_atomic_model A term ->
    AtomicBaseTruth A term.
Proof.
  intros A term H.
  exact (concrete_registered_atom_model_sound
    concrete_registered_atomic_model A term H).
Qed.

Theorem concrete_registered_truth_basis_denotes_atomic_base_truth :
  forall A : Type, forall term : A,
    concrete_registered_basis_denotes concrete_registered_truth_basis A term ->
    AtomicBaseTruth A term.
Proof.
  intros A term H.
  apply concrete_registered_atomic_truth_implies_atomic_base_truth.
  exact H.
Qed.

Inductive ConcreteRegisteredTruth : forall A : Type, A -> Prop :=
  | concrete_registered_truth_atomic :
      forall A : Type, forall term : A,
      ConcreteRegisteredAtomicTruth A term ->
      ConcreteRegisteredTruth A term
  | concrete_registered_truth_sigma_Entity : forall P : Entity -> Prop,
      (forall x : Entity, ConcreteRegisteredTruth Prop (P x)) ->
      ConcreteRegisteredTruth Prop (exists x : Entity, P x)
  | concrete_registered_truth_sigma_Food : forall P : Food -> Prop,
      (forall x : Food, ConcreteRegisteredTruth Prop (P x)) ->
      ConcreteRegisteredTruth Prop (exists x : Food, P x)
  | concrete_registered_truth_sigma_State : forall P : State -> Prop,
      (forall x : State, ConcreteRegisteredTruth Prop (P x)) ->
      ConcreteRegisteredTruth Prop (exists x : State, P x)
  | concrete_registered_truth_sigma_StateScale : forall P : StateScale -> Prop,
      (forall x : StateScale, ConcreteRegisteredTruth Prop (P x)) ->
      ConcreteRegisteredTruth Prop (exists x : StateScale, P x)
  | concrete_registered_truth_sigma_TransitionT : forall P : TransitionT -> Prop,
      (forall x : TransitionT, ConcreteRegisteredTruth Prop (P x)) ->
      ConcreteRegisteredTruth Prop (exists x : TransitionT, P x)
  | concrete_registered_truth_repeat : forall n : nat, forall body : PropT,
      ConcreteRegisteredTruth PropT body ->
      ConcreteRegisteredTruth PropT (repeat n body)
  | concrete_registered_truth_at_T : forall marker : Entity, forall body : PropT,
      ConcreteRegisteredTruth PropT body ->
      ConcreteRegisteredTruth PropT (at_T marker body)
  | concrete_registered_truth_during_T : forall marker : Entity, forall body : PropT,
      ConcreteRegisteredTruth PropT body ->
      ConcreteRegisteredTruth PropT (during_T marker body)
  | concrete_registered_truth_before_T : forall marker : Entity, forall body : PropT,
      ConcreteRegisteredTruth PropT body ->
      ConcreteRegisteredTruth PropT (before_T marker body)
  | concrete_registered_truth_after_T : forall marker : Entity, forall body : PropT,
      ConcreteRegisteredTruth PropT body ->
      ConcreteRegisteredTruth PropT (after_T marker body)
  | concrete_registered_truth_until_T : forall marker : Entity, forall body : PropT,
      ConcreteRegisteredTruth PropT body ->
      ConcreteRegisteredTruth PropT (until_T marker body)
  | concrete_registered_truth_since_T : forall marker : Entity, forall body : PropT,
      ConcreteRegisteredTruth PropT body ->
      ConcreteRegisteredTruth PropT (since_T marker body)
  | concrete_registered_truth_not_T : forall body : PropT,
      ConcreteRegisteredTruth PropT body ->
      ConcreteRegisteredTruth PropT (not_T body)
  | concrete_registered_truth_cause :
      forall causer : Entity, forall effect : TransitionT,
      ConcreteRegisteredTruth TransitionT effect ->
      ConcreteRegisteredTruth PropT (Cause causer effect).

Theorem concrete_registered_truth_implies_fully_registered :
  forall A : Type, forall term : A,
    ConcreteRegisteredTruth A term ->
    FullyRegisteredAtomicClosureTruth A term.
Proof.
  intros A term H.
  induction H.
  - induction H.
    + apply fully_registered_atomic_truth_lexical_application.
      assumption.
    + apply fully_registered_atomic_truth_transition.
      assumption.
  - apply fully_registered_atomic_truth_sigma_Entity.
    assumption.
  - apply fully_registered_atomic_truth_sigma_Food.
    assumption.
  - apply fully_registered_atomic_truth_sigma_State.
    assumption.
  - apply fully_registered_atomic_truth_sigma_StateScale.
    assumption.
  - apply fully_registered_atomic_truth_sigma_TransitionT.
    assumption.
  - apply fully_registered_atomic_truth_repeat. assumption.
  - apply fully_registered_atomic_truth_at_T. assumption.
  - apply fully_registered_atomic_truth_during_T. assumption.
  - apply fully_registered_atomic_truth_before_T. assumption.
  - apply fully_registered_atomic_truth_after_T. assumption.
  - apply fully_registered_atomic_truth_until_T. assumption.
  - apply fully_registered_atomic_truth_since_T. assumption.
  - apply fully_registered_atomic_truth_not_T. assumption.
  - apply fully_registered_atomic_truth_cause. assumption.
Qed.

Theorem concrete_registered_truth_implies_atomic_closure :
  forall A : Type, forall term : A,
    ConcreteRegisteredTruth A term -> AtomicClosureTruth A term.
Proof.
  intros A term H.
  apply fully_registered_atomic_closure_truth_implies_atomic_closure_truth.
  apply concrete_registered_truth_implies_fully_registered.
  exact H.
Qed.

Definition concrete_registered_truth_denotes : forall A : Type, A -> Prop :=
  ConcreteRegisteredTruth.

Definition concrete_registered_truth_conditions : FullyRegisteredTruthConditionSpec := {|
  fully_registered_truth_denotes := concrete_registered_truth_denotes;
  fully_registered_truth_lexical_application :=
    fun A term h => concrete_registered_truth_atomic A term
      (concrete_registered_atomic_truth_lexical_application A term h);
  fully_registered_truth_sigma_Entity := fun P h => concrete_registered_truth_sigma_Entity P h;
  fully_registered_truth_sigma_Food := fun P h => concrete_registered_truth_sigma_Food P h;
  fully_registered_truth_sigma_State := fun P h => concrete_registered_truth_sigma_State P h;
  fully_registered_truth_sigma_StateScale := fun P h => concrete_registered_truth_sigma_StateScale P h;
  fully_registered_truth_sigma_TransitionT := fun P h => concrete_registered_truth_sigma_TransitionT P h;
  fully_registered_truth_repeat := fun n body h => concrete_registered_truth_repeat n body h;
  fully_registered_truth_at_T := fun marker body h => concrete_registered_truth_at_T marker body h;
  fully_registered_truth_during_T := fun marker body h => concrete_registered_truth_during_T marker body h;
  fully_registered_truth_before_T := fun marker body h => concrete_registered_truth_before_T marker body h;
  fully_registered_truth_after_T := fun marker body h => concrete_registered_truth_after_T marker body h;
  fully_registered_truth_until_T := fun marker body h => concrete_registered_truth_until_T marker body h;
  fully_registered_truth_since_T := fun marker body h => concrete_registered_truth_since_T marker body h;
  fully_registered_truth_not_T := fun body h => concrete_registered_truth_not_T body h;
  fully_registered_truth_transition := fun theme scale source target h => concrete_registered_truth_atomic TransitionT (Transition theme scale source target) (concrete_registered_atomic_truth_transition theme scale source target h);
  fully_registered_truth_cause := fun causer effect h => concrete_registered_truth_cause causer effect h
|}.

Theorem concrete_registered_truth_condition_spec_exists :
  exists F : FullyRegisteredTruthConditionSpec,
    F = concrete_registered_truth_conditions.
Proof.
  exists concrete_registered_truth_conditions. reflexivity.
Qed.

Theorem concrete_registered_truth_conditions_denote_concrete_registered :
  forall A : Type, forall term : A,
    ConcreteRegisteredTruth A term ->
    fully_registered_truth_denotes concrete_registered_truth_conditions A term.
Proof.
  intros A term H.
  exact H.
Qed.

Theorem concrete_registered_truth_conditions_imply_fully_registered :
  forall A : Type, forall term : A,
    fully_registered_truth_denotes concrete_registered_truth_conditions A term ->
    FullyRegisteredAtomicClosureTruth A term.
Proof.
  intros A term H.
  apply concrete_registered_truth_implies_fully_registered.
  exact H.
Qed.

Theorem concrete_registered_truth_conditions_imply_atomic_closure :
  forall A : Type, forall term : A,
    fully_registered_truth_denotes concrete_registered_truth_conditions A term ->
    AtomicClosureTruth A term.
Proof.
  intros A term H.
  apply concrete_registered_truth_implies_atomic_closure.
  exact H.
Qed.

Record ConcreteRegisteredCompositionalModel : Type := {
  concrete_registered_composition_denotes : forall A : Type, A -> Prop;
  concrete_registered_composition_atomic :
      forall A : Type, forall term : A,
      ConcreteRegisteredAtomicTruth A term ->
      concrete_registered_composition_denotes A term;
  concrete_registered_composition_sigma_Entity :
      forall P : Entity -> Prop,
      (forall x : Entity,
        concrete_registered_composition_denotes Prop (P x)) ->
      concrete_registered_composition_denotes Prop
        (exists x : Entity, P x);
  concrete_registered_composition_sigma_Food :
      forall P : Food -> Prop,
      (forall x : Food,
        concrete_registered_composition_denotes Prop (P x)) ->
      concrete_registered_composition_denotes Prop
        (exists x : Food, P x);
  concrete_registered_composition_sigma_State :
      forall P : State -> Prop,
      (forall x : State,
        concrete_registered_composition_denotes Prop (P x)) ->
      concrete_registered_composition_denotes Prop
        (exists x : State, P x);
  concrete_registered_composition_sigma_StateScale :
      forall P : StateScale -> Prop,
      (forall x : StateScale,
        concrete_registered_composition_denotes Prop (P x)) ->
      concrete_registered_composition_denotes Prop
        (exists x : StateScale, P x);
  concrete_registered_composition_sigma_TransitionT :
      forall P : TransitionT -> Prop,
      (forall x : TransitionT,
        concrete_registered_composition_denotes Prop (P x)) ->
      concrete_registered_composition_denotes Prop
        (exists x : TransitionT, P x);
  concrete_registered_composition_repeat :
      forall n : nat, forall body : PropT,
      concrete_registered_composition_denotes PropT body ->
      concrete_registered_composition_denotes PropT (repeat n body);
  concrete_registered_composition_at_T :
      forall marker : Entity, forall body : PropT,
      concrete_registered_composition_denotes PropT body ->
      concrete_registered_composition_denotes PropT (at_T marker body);
  concrete_registered_composition_during_T :
      forall marker : Entity, forall body : PropT,
      concrete_registered_composition_denotes PropT body ->
      concrete_registered_composition_denotes PropT (during_T marker body);
  concrete_registered_composition_before_T :
      forall marker : Entity, forall body : PropT,
      concrete_registered_composition_denotes PropT body ->
      concrete_registered_composition_denotes PropT (before_T marker body);
  concrete_registered_composition_after_T :
      forall marker : Entity, forall body : PropT,
      concrete_registered_composition_denotes PropT body ->
      concrete_registered_composition_denotes PropT (after_T marker body);
  concrete_registered_composition_until_T :
      forall marker : Entity, forall body : PropT,
      concrete_registered_composition_denotes PropT body ->
      concrete_registered_composition_denotes PropT (until_T marker body);
  concrete_registered_composition_since_T :
      forall marker : Entity, forall body : PropT,
      concrete_registered_composition_denotes PropT body ->
      concrete_registered_composition_denotes PropT (since_T marker body);
  concrete_registered_composition_not_T :
      forall body : PropT,
      concrete_registered_composition_denotes PropT body ->
      concrete_registered_composition_denotes PropT (not_T body);
  concrete_registered_composition_cause :
      forall causer : Entity, forall effect : TransitionT,
      concrete_registered_composition_denotes TransitionT effect ->
      concrete_registered_composition_denotes PropT (Cause causer effect);
  concrete_registered_composition_sound :
      forall A : Type, forall term : A,
      concrete_registered_composition_denotes A term ->
      AtomicClosureTruth A term
}.

Definition concrete_registered_compositional_model :
  ConcreteRegisteredCompositionalModel := {|
  concrete_registered_composition_denotes := ConcreteRegisteredTruth;
  concrete_registered_composition_atomic :=
    fun A term h => concrete_registered_truth_atomic A term h;
  concrete_registered_composition_sigma_Entity := fun P h => concrete_registered_truth_sigma_Entity P h;
  concrete_registered_composition_sigma_Food := fun P h => concrete_registered_truth_sigma_Food P h;
  concrete_registered_composition_sigma_State := fun P h => concrete_registered_truth_sigma_State P h;
  concrete_registered_composition_sigma_StateScale := fun P h => concrete_registered_truth_sigma_StateScale P h;
  concrete_registered_composition_sigma_TransitionT := fun P h => concrete_registered_truth_sigma_TransitionT P h;
  concrete_registered_composition_repeat := fun n body h => concrete_registered_truth_repeat n body h;
  concrete_registered_composition_at_T := fun marker body h => concrete_registered_truth_at_T marker body h;
  concrete_registered_composition_during_T := fun marker body h => concrete_registered_truth_during_T marker body h;
  concrete_registered_composition_before_T := fun marker body h => concrete_registered_truth_before_T marker body h;
  concrete_registered_composition_after_T := fun marker body h => concrete_registered_truth_after_T marker body h;
  concrete_registered_composition_until_T := fun marker body h => concrete_registered_truth_until_T marker body h;
  concrete_registered_composition_since_T := fun marker body h => concrete_registered_truth_since_T marker body h;
  concrete_registered_composition_not_T := fun body h => concrete_registered_truth_not_T body h;
  concrete_registered_composition_cause := fun causer effect h => concrete_registered_truth_cause causer effect h;
  concrete_registered_composition_sound := concrete_registered_truth_implies_atomic_closure
|}.

Theorem concrete_registered_compositional_model_exists :
  exists M : ConcreteRegisteredCompositionalModel,
    M = concrete_registered_compositional_model.
Proof.
  exists concrete_registered_compositional_model. reflexivity.
Qed.

Theorem concrete_registered_compositional_model_denotes_concrete_registered :
  forall A : Type, forall term : A,
    ConcreteRegisteredTruth A term ->
    concrete_registered_composition_denotes
      concrete_registered_compositional_model A term.
Proof.
  intros A term H.
  exact H.
Qed.

Theorem concrete_registered_compositional_model_imply_atomic_closure :
  forall A : Type, forall term : A,
    concrete_registered_composition_denotes
      concrete_registered_compositional_model A term ->
    AtomicClosureTruth A term.
Proof.
  intros A term H.
  exact (concrete_registered_composition_sound
    concrete_registered_compositional_model A term H).
Qed.

Theorem concrete_registered_compositional_model_repeat_clause :
  forall n : nat, forall body : PropT,
    concrete_registered_composition_denotes
      concrete_registered_compositional_model PropT body ->
    concrete_registered_composition_denotes
      concrete_registered_compositional_model PropT (repeat n body).
Proof.
  intros n body H.
  exact (concrete_registered_composition_repeat
    concrete_registered_compositional_model n body H).
Qed.

Theorem concrete_registered_compositional_model_at_T_clause :
  forall marker : Entity, forall body : PropT,
    concrete_registered_composition_denotes
      concrete_registered_compositional_model PropT body ->
    concrete_registered_composition_denotes
      concrete_registered_compositional_model PropT (at_T marker body).
Proof.
  intros marker body H.
  exact (concrete_registered_composition_at_T
    concrete_registered_compositional_model marker body H).
Qed.

Theorem concrete_registered_compositional_model_cause_clause :
  forall causer : Entity, forall effect : TransitionT,
    concrete_registered_composition_denotes
      concrete_registered_compositional_model TransitionT effect ->
    concrete_registered_composition_denotes
      concrete_registered_compositional_model PropT (Cause causer effect).
Proof.
  intros causer effect H.
  exact (concrete_registered_composition_cause
    concrete_registered_compositional_model causer effect H).
Qed.

Theorem concrete_registered_compositional_model_sigma_Entity_clause :
  forall P : Entity -> Prop,
    (forall x : Entity,
      concrete_registered_composition_denotes
        concrete_registered_compositional_model Prop (P x)) ->
    concrete_registered_composition_denotes
      concrete_registered_compositional_model Prop
      (exists x : Entity, P x).
Proof.
  intros P H.
  exact (concrete_registered_composition_sigma_Entity concrete_registered_compositional_model P H).
Qed.

Theorem concrete_registered_compositional_model_sigma_Food_clause :
  forall P : Food -> Prop,
    (forall x : Food,
      concrete_registered_composition_denotes
        concrete_registered_compositional_model Prop (P x)) ->
    concrete_registered_composition_denotes
      concrete_registered_compositional_model Prop
      (exists x : Food, P x).
Proof.
  intros P H.
  exact (concrete_registered_composition_sigma_Food concrete_registered_compositional_model P H).
Qed.

Theorem concrete_registered_compositional_model_sigma_State_clause :
  forall P : State -> Prop,
    (forall x : State,
      concrete_registered_composition_denotes
        concrete_registered_compositional_model Prop (P x)) ->
    concrete_registered_composition_denotes
      concrete_registered_compositional_model Prop
      (exists x : State, P x).
Proof.
  intros P H.
  exact (concrete_registered_composition_sigma_State concrete_registered_compositional_model P H).
Qed.

Theorem concrete_registered_compositional_model_sigma_StateScale_clause :
  forall P : StateScale -> Prop,
    (forall x : StateScale,
      concrete_registered_composition_denotes
        concrete_registered_compositional_model Prop (P x)) ->
    concrete_registered_composition_denotes
      concrete_registered_compositional_model Prop
      (exists x : StateScale, P x).
Proof.
  intros P H.
  exact (concrete_registered_composition_sigma_StateScale concrete_registered_compositional_model P H).
Qed.

Theorem concrete_registered_compositional_model_sigma_TransitionT_clause :
  forall P : TransitionT -> Prop,
    (forall x : TransitionT,
      concrete_registered_composition_denotes
        concrete_registered_compositional_model Prop (P x)) ->
    concrete_registered_composition_denotes
      concrete_registered_compositional_model Prop
      (exists x : TransitionT, P x).
Proof.
  intros P H.
  exact (concrete_registered_composition_sigma_TransitionT concrete_registered_compositional_model P H).
Qed.
Record ConcreteRegisteredTruthConditionModel : Type := {
  concrete_registered_model_denotes : forall A : Type, A -> Prop;
  concrete_registered_model_spec : FullyRegisteredTruthConditionSpec;
  concrete_registered_model_denote_spec :
      forall A : Type, forall term : A,
      concrete_registered_model_denotes A term ->
      fully_registered_truth_denotes
        concrete_registered_model_spec A term;
  concrete_registered_model_sound :
      forall A : Type, forall term : A,
      concrete_registered_model_denotes A term ->
      AtomicClosureTruth A term
}.

Definition concrete_registered_truth_condition_model :
  ConcreteRegisteredTruthConditionModel := {|
  concrete_registered_model_denotes := ConcreteRegisteredTruth;
  concrete_registered_model_spec := concrete_registered_truth_conditions;
  concrete_registered_model_denote_spec := fun A term h => h;
  concrete_registered_model_sound :=
    concrete_registered_truth_implies_atomic_closure
|}.

Theorem concrete_registered_truth_condition_model_exists :
  exists M : ConcreteRegisteredTruthConditionModel,
    M = concrete_registered_truth_condition_model.
Proof.
  exists concrete_registered_truth_condition_model. reflexivity.
Qed.

Theorem concrete_registered_truth_condition_model_denote_spec :
  forall A : Type, forall term : A,
    concrete_registered_model_denotes
      concrete_registered_truth_condition_model A term ->
    fully_registered_truth_denotes
      (concrete_registered_model_spec
        concrete_registered_truth_condition_model) A term.
Proof.
  intros A term H.
  exact (concrete_registered_model_denote_spec
    concrete_registered_truth_condition_model A term H).
Qed.

Theorem concrete_registered_truth_condition_model_imply_atomic_closure :
  forall A : Type, forall term : A,
    concrete_registered_model_denotes
      concrete_registered_truth_condition_model A term ->
    AtomicClosureTruth A term.
Proof.
  intros A term H.
  exact (concrete_registered_model_sound
    concrete_registered_truth_condition_model A term H).
Qed.

Theorem concrete_registered_truth_condition_model_spec_imply_atomic_closure :
  forall A : Type, forall term : A,
    fully_registered_truth_denotes
      (concrete_registered_model_spec
        concrete_registered_truth_condition_model) A term ->
    AtomicClosureTruth A term.
Proof.
  intros A term H.
  apply concrete_registered_truth_conditions_imply_atomic_closure.
  exact H.
Qed.

Record RegisteredEvidenceBackedTruthConditionSources : Type := {
  registered_evidence_denotes : forall A : Type, A -> Prop;
  registered_evidence_lexical_application :
      forall A : Type, forall term : A,
      RegisteredLexicalApplicationTruth A term ->
      TruthEvidence (registered_evidence_denotes A term);
  registered_evidence_sigma_Entity : forall P : Entity -> Prop,
      (forall x : Entity, registered_evidence_denotes Prop (P x)) ->
      TruthEvidence (registered_evidence_denotes Prop (exists x : Entity, P x));
  registered_evidence_sigma_Food : forall P : Food -> Prop,
      (forall x : Food, registered_evidence_denotes Prop (P x)) ->
      TruthEvidence (registered_evidence_denotes Prop (exists x : Food, P x));
  registered_evidence_sigma_State : forall P : State -> Prop,
      (forall x : State, registered_evidence_denotes Prop (P x)) ->
      TruthEvidence (registered_evidence_denotes Prop (exists x : State, P x));
  registered_evidence_sigma_StateScale : forall P : StateScale -> Prop,
      (forall x : StateScale, registered_evidence_denotes Prop (P x)) ->
      TruthEvidence (registered_evidence_denotes Prop (exists x : StateScale, P x));
  registered_evidence_sigma_TransitionT : forall P : TransitionT -> Prop,
      (forall x : TransitionT, registered_evidence_denotes Prop (P x)) ->
      TruthEvidence (registered_evidence_denotes Prop (exists x : TransitionT, P x));
  registered_evidence_repeat : forall n : nat, forall body : PropT,
      registered_evidence_denotes PropT body ->
      TruthEvidence (registered_evidence_denotes PropT (repeat n body));
  registered_evidence_at_T : forall marker : Entity, forall body : PropT,
      registered_evidence_denotes PropT body ->
      TruthEvidence (registered_evidence_denotes PropT (at_T marker body));
  registered_evidence_during_T : forall marker : Entity, forall body : PropT,
      registered_evidence_denotes PropT body ->
      TruthEvidence (registered_evidence_denotes PropT (during_T marker body));
  registered_evidence_before_T : forall marker : Entity, forall body : PropT,
      registered_evidence_denotes PropT body ->
      TruthEvidence (registered_evidence_denotes PropT (before_T marker body));
  registered_evidence_after_T : forall marker : Entity, forall body : PropT,
      registered_evidence_denotes PropT body ->
      TruthEvidence (registered_evidence_denotes PropT (after_T marker body));
  registered_evidence_until_T : forall marker : Entity, forall body : PropT,
      registered_evidence_denotes PropT body ->
      TruthEvidence (registered_evidence_denotes PropT (until_T marker body));
  registered_evidence_since_T : forall marker : Entity, forall body : PropT,
      registered_evidence_denotes PropT body ->
      TruthEvidence (registered_evidence_denotes PropT (since_T marker body));
  registered_evidence_not_T : forall body : PropT,
      registered_evidence_denotes PropT body ->
      TruthEvidence (registered_evidence_denotes PropT (not_T body));
  registered_evidence_transition :
      forall theme : Entity, forall scale : StateScale,
      forall source : State, forall target : State,
      RegisteredStateTransitionTruth theme scale source target ->
      TruthEvidence (registered_evidence_denotes TransitionT
        (Transition theme scale source target));
  registered_evidence_cause :
      forall causer : Entity, forall effect : TransitionT,
      registered_evidence_denotes TransitionT effect ->
      TruthEvidence (registered_evidence_denotes PropT (Cause causer effect))
}.

Definition fully_registered_truth_conditions_from_registered_evidence_sources
  (S : RegisteredEvidenceBackedTruthConditionSources) :
  FullyRegisteredTruthConditionSpec := {|
  fully_registered_truth_denotes := registered_evidence_denotes S;
  fully_registered_truth_lexical_application :=
    fun A term h => truth_evidence_sound
      (registered_evidence_denotes S A term)
      (registered_evidence_lexical_application S A term h);
  fully_registered_truth_sigma_Entity :=
    fun P h => truth_evidence_sound
          (registered_evidence_denotes S Prop
            (exists x : Entity, P x))
          (registered_evidence_sigma_Entity S P h);
  fully_registered_truth_sigma_Food :=
    fun P h => truth_evidence_sound
          (registered_evidence_denotes S Prop
            (exists x : Food, P x))
          (registered_evidence_sigma_Food S P h);
  fully_registered_truth_sigma_State :=
    fun P h => truth_evidence_sound
          (registered_evidence_denotes S Prop
            (exists x : State, P x))
          (registered_evidence_sigma_State S P h);
  fully_registered_truth_sigma_StateScale :=
    fun P h => truth_evidence_sound
          (registered_evidence_denotes S Prop
            (exists x : StateScale, P x))
          (registered_evidence_sigma_StateScale S P h);
  fully_registered_truth_sigma_TransitionT :=
    fun P h => truth_evidence_sound
          (registered_evidence_denotes S Prop
            (exists x : TransitionT, P x))
          (registered_evidence_sigma_TransitionT S P h);
  fully_registered_truth_repeat :=
    fun n body h => truth_evidence_sound
          (registered_evidence_denotes S PropT (repeat n body))
          (registered_evidence_repeat S n body h);
  fully_registered_truth_at_T :=
    fun marker body h => truth_evidence_sound
          (registered_evidence_denotes S PropT (at_T marker body))
          (registered_evidence_at_T S marker body h);
  fully_registered_truth_during_T :=
    fun marker body h => truth_evidence_sound
          (registered_evidence_denotes S PropT (during_T marker body))
          (registered_evidence_during_T S marker body h);
  fully_registered_truth_before_T :=
    fun marker body h => truth_evidence_sound
          (registered_evidence_denotes S PropT (before_T marker body))
          (registered_evidence_before_T S marker body h);
  fully_registered_truth_after_T :=
    fun marker body h => truth_evidence_sound
          (registered_evidence_denotes S PropT (after_T marker body))
          (registered_evidence_after_T S marker body h);
  fully_registered_truth_until_T :=
    fun marker body h => truth_evidence_sound
          (registered_evidence_denotes S PropT (until_T marker body))
          (registered_evidence_until_T S marker body h);
  fully_registered_truth_since_T :=
    fun marker body h => truth_evidence_sound
          (registered_evidence_denotes S PropT (since_T marker body))
          (registered_evidence_since_T S marker body h);
  fully_registered_truth_not_T :=
    fun body h => truth_evidence_sound
          (registered_evidence_denotes S PropT (not_T body))
          (registered_evidence_not_T S body h);
  fully_registered_truth_transition :=
    fun theme scale source target h => truth_evidence_sound
          (registered_evidence_denotes S TransitionT
            (Transition theme scale source target))
          (registered_evidence_transition S theme scale source target h);
  fully_registered_truth_cause :=
    fun causer effect h => truth_evidence_sound
          (registered_evidence_denotes S PropT (Cause causer effect))
          (registered_evidence_cause S causer effect h)
|}.

Theorem registered_evidence_backed_truth_condition_sources_induce_fully_registered_truth_conditions :
  forall S : RegisteredEvidenceBackedTruthConditionSources,
    exists F : FullyRegisteredTruthConditionSpec,
      F = fully_registered_truth_conditions_from_registered_evidence_sources S.
Proof.
  intro S.
  exists (fully_registered_truth_conditions_from_registered_evidence_sources S).
  reflexivity.
Qed.

Definition concrete_registered_evidence_backed_truth_sources :
  RegisteredEvidenceBackedTruthConditionSources := {|
  registered_evidence_denotes := ConcreteRegisteredTruth;
  registered_evidence_lexical_application :=
    fun A term h => truth_evidence_intro
      (ConcreteRegisteredTruth A term)
      (concrete_registered_truth_atomic A term
        (concrete_registered_atomic_truth_lexical_application A term h));
  registered_evidence_sigma_Entity :=
    fun P h => truth_evidence_intro
          (ConcreteRegisteredTruth Prop (exists x : Entity, P x))
          (concrete_registered_truth_sigma_Entity P h);
  registered_evidence_sigma_Food :=
    fun P h => truth_evidence_intro
          (ConcreteRegisteredTruth Prop (exists x : Food, P x))
          (concrete_registered_truth_sigma_Food P h);
  registered_evidence_sigma_State :=
    fun P h => truth_evidence_intro
          (ConcreteRegisteredTruth Prop (exists x : State, P x))
          (concrete_registered_truth_sigma_State P h);
  registered_evidence_sigma_StateScale :=
    fun P h => truth_evidence_intro
          (ConcreteRegisteredTruth Prop (exists x : StateScale, P x))
          (concrete_registered_truth_sigma_StateScale P h);
  registered_evidence_sigma_TransitionT :=
    fun P h => truth_evidence_intro
          (ConcreteRegisteredTruth Prop (exists x : TransitionT, P x))
          (concrete_registered_truth_sigma_TransitionT P h);
  registered_evidence_repeat :=
    fun n body h => truth_evidence_intro
          (ConcreteRegisteredTruth PropT (repeat n body))
          (concrete_registered_truth_repeat n body h);
  registered_evidence_at_T :=
    fun marker body h => truth_evidence_intro
          (ConcreteRegisteredTruth PropT (at_T marker body))
          (concrete_registered_truth_at_T marker body h);
  registered_evidence_during_T :=
    fun marker body h => truth_evidence_intro
          (ConcreteRegisteredTruth PropT (during_T marker body))
          (concrete_registered_truth_during_T marker body h);
  registered_evidence_before_T :=
    fun marker body h => truth_evidence_intro
          (ConcreteRegisteredTruth PropT (before_T marker body))
          (concrete_registered_truth_before_T marker body h);
  registered_evidence_after_T :=
    fun marker body h => truth_evidence_intro
          (ConcreteRegisteredTruth PropT (after_T marker body))
          (concrete_registered_truth_after_T marker body h);
  registered_evidence_until_T :=
    fun marker body h => truth_evidence_intro
          (ConcreteRegisteredTruth PropT (until_T marker body))
          (concrete_registered_truth_until_T marker body h);
  registered_evidence_since_T :=
    fun marker body h => truth_evidence_intro
          (ConcreteRegisteredTruth PropT (since_T marker body))
          (concrete_registered_truth_since_T marker body h);
  registered_evidence_not_T :=
    fun body h => truth_evidence_intro
          (ConcreteRegisteredTruth PropT (not_T body))
          (concrete_registered_truth_not_T body h);
  registered_evidence_transition :=
    fun theme scale source target h => truth_evidence_intro
          (ConcreteRegisteredTruth TransitionT
            (Transition theme scale source target))
          (concrete_registered_truth_atomic TransitionT
            (Transition theme scale source target)
            (concrete_registered_atomic_truth_transition
              theme scale source target h));
  registered_evidence_cause :=
    fun causer effect h => truth_evidence_intro
          (ConcreteRegisteredTruth PropT (Cause causer effect))
          (concrete_registered_truth_cause causer effect h)
|}.

Definition concrete_registered_evidence_backed_truth_conditions :
  FullyRegisteredTruthConditionSpec :=
  fully_registered_truth_conditions_from_registered_evidence_sources
    concrete_registered_evidence_backed_truth_sources.

Theorem concrete_registered_evidence_backed_truth_sources_exist :
  exists S : RegisteredEvidenceBackedTruthConditionSources,
    S = concrete_registered_evidence_backed_truth_sources.
Proof.
  exists concrete_registered_evidence_backed_truth_sources. reflexivity.
Qed.

Theorem concrete_registered_evidence_backed_truth_conditions_exists :
  exists F : FullyRegisteredTruthConditionSpec,
    F = concrete_registered_evidence_backed_truth_conditions.
Proof.
  exists concrete_registered_evidence_backed_truth_conditions. reflexivity.
Qed.

Theorem concrete_registered_evidence_backed_truth_conditions_denote_concrete_registered :
  forall A : Type, forall term : A,
    ConcreteRegisteredTruth A term ->
    fully_registered_truth_denotes
      concrete_registered_evidence_backed_truth_conditions A term.
Proof.
  intros A term H.
  exact H.
Qed.

Theorem concrete_registered_evidence_backed_truth_conditions_imply_atomic_closure :
  forall A : Type, forall term : A,
    fully_registered_truth_denotes
      concrete_registered_evidence_backed_truth_conditions A term ->
    AtomicClosureTruth A term.
Proof.
  intros A term H.
  apply concrete_registered_truth_implies_atomic_closure.
  exact H.
Qed.

Record ConcreteRegisteredEvidenceBackedTruthConditionModel : Type := {
  concrete_registered_evidence_backed_model_denotes : forall A : Type, A -> Prop;
  concrete_registered_evidence_backed_model_spec : FullyRegisteredTruthConditionSpec;
  concrete_registered_evidence_backed_model_denote_spec :
      forall A : Type, forall term : A,
      concrete_registered_evidence_backed_model_denotes A term ->
      fully_registered_truth_denotes
        concrete_registered_evidence_backed_model_spec A term;
  concrete_registered_evidence_backed_model_sound :
      forall A : Type, forall term : A,
      concrete_registered_evidence_backed_model_denotes A term ->
      AtomicClosureTruth A term
}.

Definition concrete_registered_evidence_backed_truth_condition_model :
  ConcreteRegisteredEvidenceBackedTruthConditionModel := {|
  concrete_registered_evidence_backed_model_denotes := ConcreteRegisteredTruth;
  concrete_registered_evidence_backed_model_spec := concrete_registered_evidence_backed_truth_conditions;
  concrete_registered_evidence_backed_model_denote_spec :=
    concrete_registered_evidence_backed_truth_conditions_denote_concrete_registered;
  concrete_registered_evidence_backed_model_sound :=
    concrete_registered_truth_implies_atomic_closure
|}.

Theorem concrete_registered_evidence_backed_truth_condition_model_exists :
  exists M : ConcreteRegisteredEvidenceBackedTruthConditionModel,
    M = concrete_registered_evidence_backed_truth_condition_model.
Proof.
  exists concrete_registered_evidence_backed_truth_condition_model.
  reflexivity.
Qed.

Theorem concrete_registered_evidence_backed_truth_condition_model_denote_spec :
  forall A : Type, forall term : A,
    concrete_registered_evidence_backed_model_denotes
      concrete_registered_evidence_backed_truth_condition_model A term ->
    fully_registered_truth_denotes
      (concrete_registered_evidence_backed_model_spec
        concrete_registered_evidence_backed_truth_condition_model) A term.
Proof.
  intros A term H.
  exact (concrete_registered_evidence_backed_model_denote_spec
    concrete_registered_evidence_backed_truth_condition_model A term H).
Qed.

Theorem concrete_registered_evidence_backed_truth_condition_model_imply_atomic_closure :
  forall A : Type, forall term : A,
    concrete_registered_evidence_backed_model_denotes
      concrete_registered_evidence_backed_truth_condition_model A term ->
    AtomicClosureTruth A term.
Proof.
  intros A term H.
  exact (concrete_registered_evidence_backed_model_sound
    concrete_registered_evidence_backed_truth_condition_model A term H).
Qed.

Theorem concrete_registered_evidence_backed_truth_condition_model_spec_imply_atomic_closure :
  forall A : Type, forall term : A,
    fully_registered_truth_denotes
      (concrete_registered_evidence_backed_model_spec
        concrete_registered_evidence_backed_truth_condition_model) A term ->
    AtomicClosureTruth A term.
Proof.
  intros A term H.
  apply concrete_registered_evidence_backed_truth_conditions_imply_atomic_closure.
  exact H.
Qed.

Record ConcreteRegisteredTruthKernel : Type := {
  concrete_registered_kernel_denotes : forall A : Type, A -> Prop;
  concrete_registered_kernel_lexical_application :
      forall A : Type, forall term : A,
      RegisteredLexicalApplicationTruth A term ->
      concrete_registered_kernel_denotes A term;
  concrete_registered_kernel_sigma_Entity : forall P : Entity -> Prop,
      (forall x : Entity, concrete_registered_kernel_denotes Prop (P x)) ->
      concrete_registered_kernel_denotes Prop (exists x : Entity, P x);
  concrete_registered_kernel_sigma_Food : forall P : Food -> Prop,
      (forall x : Food, concrete_registered_kernel_denotes Prop (P x)) ->
      concrete_registered_kernel_denotes Prop (exists x : Food, P x);
  concrete_registered_kernel_sigma_State : forall P : State -> Prop,
      (forall x : State, concrete_registered_kernel_denotes Prop (P x)) ->
      concrete_registered_kernel_denotes Prop (exists x : State, P x);
  concrete_registered_kernel_sigma_StateScale : forall P : StateScale -> Prop,
      (forall x : StateScale, concrete_registered_kernel_denotes Prop (P x)) ->
      concrete_registered_kernel_denotes Prop (exists x : StateScale, P x);
  concrete_registered_kernel_sigma_TransitionT : forall P : TransitionT -> Prop,
      (forall x : TransitionT, concrete_registered_kernel_denotes Prop (P x)) ->
      concrete_registered_kernel_denotes Prop (exists x : TransitionT, P x);
  concrete_registered_kernel_repeat : forall n : nat, forall body : PropT,
      concrete_registered_kernel_denotes PropT body ->
      concrete_registered_kernel_denotes PropT (repeat n body);
  concrete_registered_kernel_at_T : forall marker : Entity, forall body : PropT,
      concrete_registered_kernel_denotes PropT body ->
      concrete_registered_kernel_denotes PropT (at_T marker body);
  concrete_registered_kernel_during_T : forall marker : Entity, forall body : PropT,
      concrete_registered_kernel_denotes PropT body ->
      concrete_registered_kernel_denotes PropT (during_T marker body);
  concrete_registered_kernel_before_T : forall marker : Entity, forall body : PropT,
      concrete_registered_kernel_denotes PropT body ->
      concrete_registered_kernel_denotes PropT (before_T marker body);
  concrete_registered_kernel_after_T : forall marker : Entity, forall body : PropT,
      concrete_registered_kernel_denotes PropT body ->
      concrete_registered_kernel_denotes PropT (after_T marker body);
  concrete_registered_kernel_until_T : forall marker : Entity, forall body : PropT,
      concrete_registered_kernel_denotes PropT body ->
      concrete_registered_kernel_denotes PropT (until_T marker body);
  concrete_registered_kernel_since_T : forall marker : Entity, forall body : PropT,
      concrete_registered_kernel_denotes PropT body ->
      concrete_registered_kernel_denotes PropT (since_T marker body);
  concrete_registered_kernel_not_T : forall body : PropT,
      concrete_registered_kernel_denotes PropT body ->
      concrete_registered_kernel_denotes PropT (not_T body);
  concrete_registered_kernel_transition : forall theme : Entity, forall scale : StateScale,
      forall source : State, forall target : State,
      RegisteredStateTransitionTruth theme scale source target ->
      concrete_registered_kernel_denotes TransitionT (Transition theme scale source target);
  concrete_registered_kernel_cause : forall causer : Entity, forall effect : TransitionT,
      concrete_registered_kernel_denotes TransitionT effect ->
      concrete_registered_kernel_denotes PropT (Cause causer effect)
}.

Definition fully_registered_truth_conditions_from_concrete_registered_kernel
  (K : ConcreteRegisteredTruthKernel) : FullyRegisteredTruthConditionSpec := {|
  fully_registered_truth_denotes := concrete_registered_kernel_denotes K;
  fully_registered_truth_lexical_application := concrete_registered_kernel_lexical_application K;
  fully_registered_truth_sigma_Entity := concrete_registered_kernel_sigma_Entity K;
  fully_registered_truth_sigma_Food := concrete_registered_kernel_sigma_Food K;
  fully_registered_truth_sigma_State := concrete_registered_kernel_sigma_State K;
  fully_registered_truth_sigma_StateScale := concrete_registered_kernel_sigma_StateScale K;
  fully_registered_truth_sigma_TransitionT := concrete_registered_kernel_sigma_TransitionT K;
  fully_registered_truth_repeat := concrete_registered_kernel_repeat K;
  fully_registered_truth_at_T := concrete_registered_kernel_at_T K;
  fully_registered_truth_during_T := concrete_registered_kernel_during_T K;
  fully_registered_truth_before_T := concrete_registered_kernel_before_T K;
  fully_registered_truth_after_T := concrete_registered_kernel_after_T K;
  fully_registered_truth_until_T := concrete_registered_kernel_until_T K;
  fully_registered_truth_since_T := concrete_registered_kernel_since_T K;
  fully_registered_truth_not_T := concrete_registered_kernel_not_T K;
  fully_registered_truth_transition := concrete_registered_kernel_transition K;
  fully_registered_truth_cause := concrete_registered_kernel_cause K
|}.

Definition concrete_registered_truth_kernel_denotes : forall A : Type, A -> Prop :=
  ConcreteRegisteredTruth.

Definition concrete_registered_truth_kernel : ConcreteRegisteredTruthKernel := {|
  concrete_registered_kernel_denotes := concrete_registered_truth_kernel_denotes;
  concrete_registered_kernel_lexical_application :=
    fun A term h => concrete_registered_truth_atomic A term
      (concrete_registered_atomic_truth_lexical_application A term h);
  concrete_registered_kernel_sigma_Entity := fun P h => concrete_registered_truth_sigma_Entity P h;
  concrete_registered_kernel_sigma_Food := fun P h => concrete_registered_truth_sigma_Food P h;
  concrete_registered_kernel_sigma_State := fun P h => concrete_registered_truth_sigma_State P h;
  concrete_registered_kernel_sigma_StateScale := fun P h => concrete_registered_truth_sigma_StateScale P h;
  concrete_registered_kernel_sigma_TransitionT := fun P h => concrete_registered_truth_sigma_TransitionT P h;
  concrete_registered_kernel_repeat := fun n body h => concrete_registered_truth_repeat n body h;
  concrete_registered_kernel_at_T := fun marker body h => concrete_registered_truth_at_T marker body h;
  concrete_registered_kernel_during_T := fun marker body h => concrete_registered_truth_during_T marker body h;
  concrete_registered_kernel_before_T := fun marker body h => concrete_registered_truth_before_T marker body h;
  concrete_registered_kernel_after_T := fun marker body h => concrete_registered_truth_after_T marker body h;
  concrete_registered_kernel_until_T := fun marker body h => concrete_registered_truth_until_T marker body h;
  concrete_registered_kernel_since_T := fun marker body h => concrete_registered_truth_since_T marker body h;
  concrete_registered_kernel_not_T := fun body h => concrete_registered_truth_not_T body h;
  concrete_registered_kernel_transition := fun theme scale source target h => concrete_registered_truth_atomic TransitionT (Transition theme scale source target) (concrete_registered_atomic_truth_transition theme scale source target h);
  concrete_registered_kernel_cause := fun causer effect h => concrete_registered_truth_cause causer effect h
|}.

Definition concrete_registered_truth_conditions_from_kernel :
  FullyRegisteredTruthConditionSpec :=
  fully_registered_truth_conditions_from_concrete_registered_kernel
    concrete_registered_truth_kernel.

Theorem concrete_registered_truth_kernel_exists :
  exists K : ConcreteRegisteredTruthKernel,
    K = concrete_registered_truth_kernel.
Proof.
  exists concrete_registered_truth_kernel. reflexivity.
Qed.

Theorem concrete_registered_truth_conditions_from_kernel_exists :
  exists F : FullyRegisteredTruthConditionSpec,
    F = concrete_registered_truth_conditions_from_kernel.
Proof.
  exists concrete_registered_truth_conditions_from_kernel. reflexivity.
Qed.

Theorem concrete_registered_truth_kernel_denotes_concrete_registered :
  forall A : Type, forall term : A,
    ConcreteRegisteredTruth A term ->
    concrete_registered_kernel_denotes concrete_registered_truth_kernel A term.
Proof.
  intros A term H.
  exact H.
Qed.

Theorem concrete_registered_truth_conditions_from_kernel_denote_concrete_registered :
  forall A : Type, forall term : A,
    ConcreteRegisteredTruth A term ->
    fully_registered_truth_denotes concrete_registered_truth_conditions_from_kernel A term.
Proof.
  intros A term H.
  exact H.
Qed.

Theorem concrete_registered_truth_conditions_from_kernel_imply_atomic_closure :
  forall A : Type, forall term : A,
    fully_registered_truth_denotes concrete_registered_truth_conditions_from_kernel A term ->
    AtomicClosureTruth A term.
Proof.
  intros A term H.
  apply concrete_registered_truth_implies_atomic_closure.
  exact H.
Qed.

Definition model_interpretable_truth_kernel_denotes : forall A : Type, A -> Prop :=
  ModelInterpretable.

Definition model_interpretable_truth_kernel : ConcreteTruthConditionKernel := {|
  kernel_denotes := model_interpretable_truth_kernel_denotes;
  lexical_truth_break_application := fun n mods arg1 arg2 => model_break_application n mods arg1 arg2;
  lexical_truth_butter_application := fun n mods arg1 arg2 => model_butter_application n mods arg1 arg2;
  lexical_truth_eat_application := fun n mods arg1 arg2 => model_eat_application n mods arg1 arg2;
  lexical_truth_knock_application := fun n mods arg1 => model_knock_application n mods arg1;
  quantifier_truth_sigma_Entity := fun P h => model_sigma_Entity P h;
  quantifier_truth_sigma_Food := fun P h => model_sigma_Food P h;
  quantifier_truth_sigma_State := fun P h => model_sigma_State P h;
  quantifier_truth_sigma_StateScale := fun P h => model_sigma_StateScale P h;
  quantifier_truth_sigma_TransitionT := fun P h => model_sigma_TransitionT P h;
  repetition_truth := fun n body h => model_repeat n body h;
  temporal_truth_at_T := fun marker body h => model_at_T marker body h;
  temporal_truth_during_T := fun marker body h => model_during_T marker body h;
  temporal_truth_before_T := fun marker body h => model_before_T marker body h;
  temporal_truth_after_T := fun marker body h => model_after_T marker body h;
  temporal_truth_until_T := fun marker body h => model_until_T marker body h;
  temporal_truth_since_T := fun marker body h => model_since_T marker body h;
  polarity_truth_not_T := fun body h => model_not_T body h;
  transition_truth := fun theme scale source target => model_transition theme scale source target;
  cause_truth := fun causer effect h => model_cause causer effect h
|}.

Definition model_interpretable_truth_conditions_from_kernel : TruthConditionSpec :=
  truth_conditions_from_concrete_kernel model_interpretable_truth_kernel.

Theorem model_interpretable_truth_kernel_exists :
  exists K : ConcreteTruthConditionKernel,
    K = model_interpretable_truth_kernel.
Proof.
  exists model_interpretable_truth_kernel. reflexivity.
Qed.

Theorem model_interpretable_truth_kernel_denotes_model_interpretable :
  forall A : Type, forall term : A,
    ModelInterpretable A term ->
    truth_denotes (truth_conditions_from_concrete_kernel
      model_interpretable_truth_kernel) A term.
Proof.
  intros A term H.
  apply concrete_kernel_induces_truth_condition_soundness.
  exact H.
Qed.

Definition syntax_directed_truth_kernel_denotes : forall A : Type, A -> Prop :=
  SyntaxDirectedTruth.

Definition syntax_directed_truth_kernel : ConcreteTruthConditionKernel := {|
  kernel_denotes := syntax_directed_truth_kernel_denotes;
  lexical_truth_break_application := fun n mods arg1 arg2 => syntax_truth_break_application n mods arg1 arg2;
  lexical_truth_butter_application := fun n mods arg1 arg2 => syntax_truth_butter_application n mods arg1 arg2;
  lexical_truth_eat_application := fun n mods arg1 arg2 => syntax_truth_eat_application n mods arg1 arg2;
  lexical_truth_knock_application := fun n mods arg1 => syntax_truth_knock_application n mods arg1;
  quantifier_truth_sigma_Entity := fun P h => syntax_truth_sigma_Entity P h;
  quantifier_truth_sigma_Food := fun P h => syntax_truth_sigma_Food P h;
  quantifier_truth_sigma_State := fun P h => syntax_truth_sigma_State P h;
  quantifier_truth_sigma_StateScale := fun P h => syntax_truth_sigma_StateScale P h;
  quantifier_truth_sigma_TransitionT := fun P h => syntax_truth_sigma_TransitionT P h;
  repetition_truth := fun n body h => syntax_truth_repeat n body h;
  temporal_truth_at_T := fun marker body h => syntax_truth_at_T marker body h;
  temporal_truth_during_T := fun marker body h => syntax_truth_during_T marker body h;
  temporal_truth_before_T := fun marker body h => syntax_truth_before_T marker body h;
  temporal_truth_after_T := fun marker body h => syntax_truth_after_T marker body h;
  temporal_truth_until_T := fun marker body h => syntax_truth_until_T marker body h;
  temporal_truth_since_T := fun marker body h => syntax_truth_since_T marker body h;
  polarity_truth_not_T := fun body h => syntax_truth_not_T body h;
  transition_truth := fun theme scale source target => syntax_truth_transition theme scale source target;
  cause_truth := fun causer effect h => syntax_truth_cause causer effect h
|}.

Definition syntax_directed_truth_conditions_from_kernel : TruthConditionSpec :=
  truth_conditions_from_concrete_kernel syntax_directed_truth_kernel.

Theorem syntax_directed_truth_kernel_exists :
  exists K : ConcreteTruthConditionKernel,
    K = syntax_directed_truth_kernel.
Proof.
  exists syntax_directed_truth_kernel. reflexivity.
Qed.

Theorem syntax_directed_truth_kernel_denotes_syntax_directed_truth :
  forall A : Type, forall term : A,
    SyntaxDirectedTruth A term ->
    truth_denotes (truth_conditions_from_concrete_kernel
      syntax_directed_truth_kernel) A term.
Proof.
  intros A term H.
  exact H.
Qed.

Definition tautological_truth_denotes : forall A : Type, A -> Prop :=
  fun A term => True.

Definition tautological_truth_conditions : TruthConditionSpec := {|
  truth_denotes := tautological_truth_denotes;
  truth_break_application := fun n mods arg1 arg2 => I;
  truth_butter_application := fun n mods arg1 arg2 => I;
  truth_eat_application := fun n mods arg1 arg2 => I;
  truth_knock_application := fun n mods arg1 => I;
  truth_sigma_Entity := fun P h => I;
  truth_sigma_Food := fun P h => I;
  truth_sigma_State := fun P h => I;
  truth_sigma_StateScale := fun P h => I;
  truth_sigma_TransitionT := fun P h => I;
  truth_repeat := fun n body h => I;
  truth_at_T := fun marker body h => I;
  truth_during_T := fun marker body h => I;
  truth_before_T := fun marker body h => I;
  truth_after_T := fun marker body h => I;
  truth_until_T := fun marker body h => I;
  truth_since_T := fun marker body h => I;
  truth_not_T := fun body h => I;
  truth_transition := fun theme scale source target => I;
  truth_cause := fun causer effect h => I
|}.

Definition tautological_semantic_model : SemanticModel :=
  semantic_model_from_truth_conditions tautological_truth_conditions.

Theorem tautological_truth_condition_spec_exists :
  exists T : TruthConditionSpec, T = tautological_truth_conditions.
Proof.
  exists tautological_truth_conditions. reflexivity.
Qed.

Theorem tautological_truth_conditions_denote_model_interpretable :
  forall A : Type, forall term : A,
    ModelInterpretable A term ->
    truth_denotes tautological_truth_conditions A term.
Proof.
  intros A term H.
  apply truth_conditions_induce_denotational_soundness.
  exact H.
Qed.

Definition structural_truth_denotes : forall A : Type, A -> Prop :=
  ModelInterpretable.

Definition structural_truth_conditions : TruthConditionSpec := {|
  truth_denotes := structural_truth_denotes;
  truth_break_application := fun n mods arg1 arg2 => model_break_application n mods arg1 arg2;
  truth_butter_application := fun n mods arg1 arg2 => model_butter_application n mods arg1 arg2;
  truth_eat_application := fun n mods arg1 arg2 => model_eat_application n mods arg1 arg2;
  truth_knock_application := fun n mods arg1 => model_knock_application n mods arg1;
  truth_sigma_Entity := fun P h => model_sigma_Entity P h;
  truth_sigma_Food := fun P h => model_sigma_Food P h;
  truth_sigma_State := fun P h => model_sigma_State P h;
  truth_sigma_StateScale := fun P h => model_sigma_StateScale P h;
  truth_sigma_TransitionT := fun P h => model_sigma_TransitionT P h;
  truth_repeat := fun n body h => model_repeat n body h;
  truth_at_T := fun marker body h => model_at_T marker body h;
  truth_during_T := fun marker body h => model_during_T marker body h;
  truth_before_T := fun marker body h => model_before_T marker body h;
  truth_after_T := fun marker body h => model_after_T marker body h;
  truth_until_T := fun marker body h => model_until_T marker body h;
  truth_since_T := fun marker body h => model_since_T marker body h;
  truth_not_T := fun body h => model_not_T body h;
  truth_transition := fun theme scale source target => model_transition theme scale source target;
  truth_cause := fun causer effect h => model_cause causer effect h
|}.

Definition structural_semantic_model : SemanticModel :=
  semantic_model_from_truth_conditions structural_truth_conditions.

Theorem structural_truth_condition_spec_exists :
  exists T : TruthConditionSpec, T = structural_truth_conditions.
Proof.
  exists structural_truth_conditions. reflexivity.
Qed.

Theorem structural_truth_conditions_denote_model_interpretable :
  forall A : Type, forall term : A,
    ModelInterpretable A term ->
    truth_denotes structural_truth_conditions A term.
Proof.
  intros A term H.
  exact H.
Qed.

Definition PreservationTargetMatches
  (A : Type) (term : A) (target : SemanticPreservationObligation) : Prop :=
  obligation_statement target = SemanticPreservation A term.

Definition example_1 : PropT := (at_T noon (butter 2 (mods_cons 1 slowly (mods_cons 0 in_bathroom mods_nil)) John toast)).
Definition example_2 : Prop := (exists x_theme : Food, (eat 0 mods_nil John x_theme)).
Definition example_3 : PropT := (repeat 2 (knock 0 mods_nil John)).
Definition example_4 : PropT := (Cause John (Transition vase integrity_scale intact broken)).

Definition example_1_semantic_preservation_obligation : Prop := SemanticPreservation PropT example_1.
Definition example_2_semantic_preservation_obligation : Prop := SemanticPreservation Prop example_2.
Definition example_3_semantic_preservation_obligation : Prop := SemanticPreservation PropT example_3.
Definition example_4_semantic_preservation_obligation : Prop := SemanticPreservation PropT example_4.

Definition example_1_semantic_preservation_obligation_record : SemanticPreservationObligation := {|
  obligation_statement := example_1_semantic_preservation_obligation;
  obligation_status := proved
|}.
Definition example_2_semantic_preservation_obligation_record : SemanticPreservationObligation := {|
  obligation_statement := example_2_semantic_preservation_obligation;
  obligation_status := proved
|}.
Definition example_3_semantic_preservation_obligation_record : SemanticPreservationObligation := {|
  obligation_statement := example_3_semantic_preservation_obligation;
  obligation_status := proved
|}.
Definition example_4_semantic_preservation_obligation_record : SemanticPreservationObligation := {|
  obligation_statement := example_4_semantic_preservation_obligation;
  obligation_status := proved
|}.

Theorem example_1_semantic_preservation_obligation_is_prop : exists P : Prop, P = example_1_semantic_preservation_obligation.
Proof. exists example_1_semantic_preservation_obligation. reflexivity. Qed.
Theorem example_2_semantic_preservation_obligation_is_prop : exists P : Prop, P = example_2_semantic_preservation_obligation.
Proof. exists example_2_semantic_preservation_obligation. reflexivity. Qed.
Theorem example_3_semantic_preservation_obligation_is_prop : exists P : Prop, P = example_3_semantic_preservation_obligation.
Proof. exists example_3_semantic_preservation_obligation. reflexivity. Qed.
Theorem example_4_semantic_preservation_obligation_is_prop : exists P : Prop, P = example_4_semantic_preservation_obligation.
Proof. exists example_4_semantic_preservation_obligation. reflexivity. Qed.

Theorem example_1_semantic_preservation_target_matches : PreservationTargetMatches PropT example_1 example_1_semantic_preservation_obligation_record.
Proof. reflexivity. Qed.
Theorem example_2_semantic_preservation_target_matches : PreservationTargetMatches Prop example_2 example_2_semantic_preservation_obligation_record.
Proof. reflexivity. Qed.
Theorem example_3_semantic_preservation_target_matches : PreservationTargetMatches PropT example_3 example_3_semantic_preservation_obligation_record.
Proof. reflexivity. Qed.
Theorem example_4_semantic_preservation_target_matches : PreservationTargetMatches PropT example_4 example_4_semantic_preservation_obligation_record.
Proof. reflexivity. Qed.

Theorem example_1_semantic_preservation_proved : example_1_semantic_preservation_obligation.
Proof.
  unfold example_1_semantic_preservation_obligation.
  unfold example_1.
  apply preserve_at_T.
  apply preserve_butter_application.
Qed.
Theorem example_2_semantic_preservation_proved : example_2_semantic_preservation_obligation.
Proof.
  unfold example_2_semantic_preservation_obligation.
  unfold example_2.
  apply preserve_sigma_Food.
  intro x_theme.
  apply preserve_eat_application.
Qed.
Theorem example_3_semantic_preservation_proved : example_3_semantic_preservation_obligation.
Proof.
  unfold example_3_semantic_preservation_obligation.
  unfold example_3.
  apply preserve_repeat.
  apply preserve_knock_application.
Qed.
Theorem example_4_semantic_preservation_proved : example_4_semantic_preservation_obligation.
Proof.
  unfold example_4_semantic_preservation_obligation.
  unfold example_4.
  apply preserve_cause.
  apply preserve_transition.
Qed.

Theorem example_1_model_interpretable : ModelInterpretable PropT example_1.
Proof.
  apply semantic_preservation_model_interpretable.
  exact example_1_semantic_preservation_proved.
Qed.
Theorem example_2_model_interpretable : ModelInterpretable Prop example_2.
Proof.
  apply semantic_preservation_model_interpretable.
  exact example_2_semantic_preservation_proved.
Qed.
Theorem example_3_model_interpretable : ModelInterpretable PropT example_3.
Proof.
  apply semantic_preservation_model_interpretable.
  exact example_3_semantic_preservation_proved.
Qed.
Theorem example_4_model_interpretable : ModelInterpretable PropT example_4.
Proof.
  apply semantic_preservation_model_interpretable.
  exact example_4_semantic_preservation_proved.
Qed.

Theorem example_1_syntax_directed_truth : SyntaxDirectedTruth PropT example_1.
Proof.
  apply semantic_preservation_syntax_directed_truth.
  exact example_1_semantic_preservation_proved.
Qed.
Theorem example_2_syntax_directed_truth : SyntaxDirectedTruth Prop example_2.
Proof.
  apply semantic_preservation_syntax_directed_truth.
  exact example_2_semantic_preservation_proved.
Qed.
Theorem example_3_syntax_directed_truth : SyntaxDirectedTruth PropT example_3.
Proof.
  apply semantic_preservation_syntax_directed_truth.
  exact example_3_semantic_preservation_proved.
Qed.
Theorem example_4_syntax_directed_truth : SyntaxDirectedTruth PropT example_4.
Proof.
  apply semantic_preservation_syntax_directed_truth.
  exact example_4_semantic_preservation_proved.
Qed.

Theorem example_1_denotationally_sound : forall M : SemanticModel, model_denotes M PropT example_1.
Proof.
  intro M.
  apply model_interpretable_denotational_sound.
  exact example_1_model_interpretable.
Qed.
Theorem example_2_denotationally_sound : forall M : SemanticModel, model_denotes M Prop example_2.
Proof.
  intro M.
  apply model_interpretable_denotational_sound.
  exact example_2_model_interpretable.
Qed.
Theorem example_3_denotationally_sound : forall M : SemanticModel, model_denotes M PropT example_3.
Proof.
  intro M.
  apply model_interpretable_denotational_sound.
  exact example_3_model_interpretable.
Qed.
Theorem example_4_denotationally_sound : forall M : SemanticModel, model_denotes M PropT example_4.
Proof.
  intro M.
  apply model_interpretable_denotational_sound.
  exact example_4_model_interpretable.
Qed.

Theorem example_1_truth_condition_sound : forall T : TruthConditionSpec, truth_denotes T PropT example_1.
Proof.
  intro T.
  apply truth_conditions_induce_denotational_soundness.
  exact example_1_model_interpretable.
Qed.
Theorem example_2_truth_condition_sound : forall T : TruthConditionSpec, truth_denotes T Prop example_2.
Proof.
  intro T.
  apply truth_conditions_induce_denotational_soundness.
  exact example_2_model_interpretable.
Qed.
Theorem example_3_truth_condition_sound : forall T : TruthConditionSpec, truth_denotes T PropT example_3.
Proof.
  intro T.
  apply truth_conditions_induce_denotational_soundness.
  exact example_3_model_interpretable.
Qed.
Theorem example_4_truth_condition_sound : forall T : TruthConditionSpec, truth_denotes T PropT example_4.
Proof.
  intro T.
  apply truth_conditions_induce_denotational_soundness.
  exact example_4_model_interpretable.
Qed.

Theorem example_1_tautological_truth_condition_sound : truth_denotes tautological_truth_conditions PropT example_1.
Proof.
  apply tautological_truth_conditions_denote_model_interpretable.
  exact example_1_model_interpretable.
Qed.
Theorem example_2_tautological_truth_condition_sound : truth_denotes tautological_truth_conditions Prop example_2.
Proof.
  apply tautological_truth_conditions_denote_model_interpretable.
  exact example_2_model_interpretable.
Qed.
Theorem example_3_tautological_truth_condition_sound : truth_denotes tautological_truth_conditions PropT example_3.
Proof.
  apply tautological_truth_conditions_denote_model_interpretable.
  exact example_3_model_interpretable.
Qed.
Theorem example_4_tautological_truth_condition_sound : truth_denotes tautological_truth_conditions PropT example_4.
Proof.
  apply tautological_truth_conditions_denote_model_interpretable.
  exact example_4_model_interpretable.
Qed.

Theorem example_1_structural_truth_condition_sound : truth_denotes structural_truth_conditions PropT example_1.
Proof.
  apply structural_truth_conditions_denote_model_interpretable.
  exact example_1_model_interpretable.
Qed.
Theorem example_2_structural_truth_condition_sound : truth_denotes structural_truth_conditions Prop example_2.
Proof.
  apply structural_truth_conditions_denote_model_interpretable.
  exact example_2_model_interpretable.
Qed.
Theorem example_3_structural_truth_condition_sound : truth_denotes structural_truth_conditions PropT example_3.
Proof.
  apply structural_truth_conditions_denote_model_interpretable.
  exact example_3_model_interpretable.
Qed.
Theorem example_4_structural_truth_condition_sound : truth_denotes structural_truth_conditions PropT example_4.
Proof.
  apply structural_truth_conditions_denote_model_interpretable.
  exact example_4_model_interpretable.
Qed.

Theorem example_1_concrete_kernel_truth_condition_sound : forall K : ConcreteTruthConditionKernel, truth_denotes (truth_conditions_from_concrete_kernel K) PropT example_1.
Proof.
  intro K.
  apply concrete_kernel_induces_truth_condition_soundness.
  exact example_1_model_interpretable.
Qed.
Theorem example_2_concrete_kernel_truth_condition_sound : forall K : ConcreteTruthConditionKernel, truth_denotes (truth_conditions_from_concrete_kernel K) Prop example_2.
Proof.
  intro K.
  apply concrete_kernel_induces_truth_condition_soundness.
  exact example_2_model_interpretable.
Qed.
Theorem example_3_concrete_kernel_truth_condition_sound : forall K : ConcreteTruthConditionKernel, truth_denotes (truth_conditions_from_concrete_kernel K) PropT example_3.
Proof.
  intro K.
  apply concrete_kernel_induces_truth_condition_soundness.
  exact example_3_model_interpretable.
Qed.
Theorem example_4_concrete_kernel_truth_condition_sound : forall K : ConcreteTruthConditionKernel, truth_denotes (truth_conditions_from_concrete_kernel K) PropT example_4.
Proof.
  intro K.
  apply concrete_kernel_induces_truth_condition_soundness.
  exact example_4_model_interpretable.
Qed.

Theorem example_1_model_interpretable_truth_kernel_sound : truth_denotes (truth_conditions_from_concrete_kernel model_interpretable_truth_kernel) PropT example_1.
Proof.
  apply model_interpretable_truth_kernel_denotes_model_interpretable.
  exact example_1_model_interpretable.
Qed.
Theorem example_2_model_interpretable_truth_kernel_sound : truth_denotes (truth_conditions_from_concrete_kernel model_interpretable_truth_kernel) Prop example_2.
Proof.
  apply model_interpretable_truth_kernel_denotes_model_interpretable.
  exact example_2_model_interpretable.
Qed.
Theorem example_3_model_interpretable_truth_kernel_sound : truth_denotes (truth_conditions_from_concrete_kernel model_interpretable_truth_kernel) PropT example_3.
Proof.
  apply model_interpretable_truth_kernel_denotes_model_interpretable.
  exact example_3_model_interpretable.
Qed.
Theorem example_4_model_interpretable_truth_kernel_sound : truth_denotes (truth_conditions_from_concrete_kernel model_interpretable_truth_kernel) PropT example_4.
Proof.
  apply model_interpretable_truth_kernel_denotes_model_interpretable.
  exact example_4_model_interpretable.
Qed.

Theorem example_1_syntax_directed_truth_kernel_sound : truth_denotes (truth_conditions_from_concrete_kernel syntax_directed_truth_kernel) PropT example_1.
Proof.
  apply syntax_directed_truth_kernel_denotes_syntax_directed_truth.
  exact example_1_syntax_directed_truth.
Qed.
Theorem example_2_syntax_directed_truth_kernel_sound : truth_denotes (truth_conditions_from_concrete_kernel syntax_directed_truth_kernel) Prop example_2.
Proof.
  apply syntax_directed_truth_kernel_denotes_syntax_directed_truth.
  exact example_2_syntax_directed_truth.
Qed.
Theorem example_3_syntax_directed_truth_kernel_sound : truth_denotes (truth_conditions_from_concrete_kernel syntax_directed_truth_kernel) PropT example_3.
Proof.
  apply syntax_directed_truth_kernel_denotes_syntax_directed_truth.
  exact example_3_syntax_directed_truth.
Qed.
Theorem example_4_syntax_directed_truth_kernel_sound : truth_denotes (truth_conditions_from_concrete_kernel syntax_directed_truth_kernel) PropT example_4.
Proof.
  apply syntax_directed_truth_kernel_denotes_syntax_directed_truth.
  exact example_4_syntax_directed_truth.
Qed.

Theorem example_1_primitive_truth_kernel_sound : truth_denotes (truth_conditions_from_concrete_kernel primitive_truth_kernel) PropT example_1.
Proof.
  apply primitive_truth_kernel_denotes_model_interpretable.
  exact example_1_model_interpretable.
Qed.
Theorem example_2_primitive_truth_kernel_sound : truth_denotes (truth_conditions_from_concrete_kernel primitive_truth_kernel) Prop example_2.
Proof.
  apply primitive_truth_kernel_denotes_model_interpretable.
  exact example_2_model_interpretable.
Qed.
Theorem example_3_primitive_truth_kernel_sound : truth_denotes (truth_conditions_from_concrete_kernel primitive_truth_kernel) PropT example_3.
Proof.
  apply primitive_truth_kernel_denotes_model_interpretable.
  exact example_3_model_interpretable.
Qed.
Theorem example_4_primitive_truth_kernel_sound : truth_denotes (truth_conditions_from_concrete_kernel primitive_truth_kernel) PropT example_4.
Proof.
  apply primitive_truth_kernel_denotes_model_interpretable.
  exact example_4_model_interpretable.
Qed.

Theorem example_1_atomic_closure_truth : AtomicClosureTruth PropT example_1.
Proof.
  apply model_interpretable_atomic_closure_truth.
  exact example_1_model_interpretable.
Qed.
Theorem example_2_atomic_closure_truth : AtomicClosureTruth Prop example_2.
Proof.
  apply model_interpretable_atomic_closure_truth.
  exact example_2_model_interpretable.
Qed.
Theorem example_3_atomic_closure_truth : AtomicClosureTruth PropT example_3.
Proof.
  apply model_interpretable_atomic_closure_truth.
  exact example_3_model_interpretable.
Qed.
Theorem example_4_atomic_closure_truth : AtomicClosureTruth PropT example_4.
Proof.
  apply model_interpretable_atomic_closure_truth.
  exact example_4_model_interpretable.
Qed.

Theorem example_1_atomic_closure_truth_kernel_sound : truth_denotes (truth_conditions_from_concrete_kernel atomic_closure_truth_kernel) PropT example_1.
Proof.
  apply atomic_closure_truth_kernel_denotes_atomic_closure_truth.
  exact example_1_atomic_closure_truth.
Qed.
Theorem example_2_atomic_closure_truth_kernel_sound : truth_denotes (truth_conditions_from_concrete_kernel atomic_closure_truth_kernel) Prop example_2.
Proof.
  apply atomic_closure_truth_kernel_denotes_atomic_closure_truth.
  exact example_2_atomic_closure_truth.
Qed.
Theorem example_3_atomic_closure_truth_kernel_sound : truth_denotes (truth_conditions_from_concrete_kernel atomic_closure_truth_kernel) PropT example_3.
Proof.
  apply atomic_closure_truth_kernel_denotes_atomic_closure_truth.
  exact example_3_atomic_closure_truth.
Qed.
Theorem example_4_atomic_closure_truth_kernel_sound : truth_denotes (truth_conditions_from_concrete_kernel atomic_closure_truth_kernel) PropT example_4.
Proof.
  apply atomic_closure_truth_kernel_denotes_atomic_closure_truth.
  exact example_4_atomic_closure_truth.
Qed.

Theorem example_1_atomic_closure_truth_condition_sound : truth_denotes atomic_closure_truth_conditions PropT example_1.
Proof.
  apply atomic_closure_truth_conditions_denote_atomic_closure_truth.
  exact example_1_atomic_closure_truth.
Qed.
Theorem example_2_atomic_closure_truth_condition_sound : truth_denotes atomic_closure_truth_conditions Prop example_2.
Proof.
  apply atomic_closure_truth_conditions_denote_atomic_closure_truth.
  exact example_2_atomic_closure_truth.
Qed.
Theorem example_3_atomic_closure_truth_condition_sound : truth_denotes atomic_closure_truth_conditions PropT example_3.
Proof.
  apply atomic_closure_truth_conditions_denote_atomic_closure_truth.
  exact example_3_atomic_closure_truth.
Qed.
Theorem example_4_atomic_closure_truth_condition_sound : truth_denotes atomic_closure_truth_conditions PropT example_4.
Proof.
  apply atomic_closure_truth_conditions_denote_atomic_closure_truth.
  exact example_4_atomic_closure_truth.
Qed.

Theorem example_1_atomic_closure_evidence_backed_truth_condition_sound :
  truth_denotes (ledger_truth_conditions atomic_closure_evidence_backed_truth_ledger) PropT example_1.
Proof.
  apply atomic_closure_evidence_backed_truth_sources_sound.
  exact example_1_model_interpretable.
Qed.
Theorem example_2_atomic_closure_evidence_backed_truth_condition_sound :
  truth_denotes (ledger_truth_conditions atomic_closure_evidence_backed_truth_ledger) Prop example_2.
Proof.
  apply atomic_closure_evidence_backed_truth_sources_sound.
  exact example_2_model_interpretable.
Qed.
Theorem example_3_atomic_closure_evidence_backed_truth_condition_sound :
  truth_denotes (ledger_truth_conditions atomic_closure_evidence_backed_truth_ledger) PropT example_3.
Proof.
  apply atomic_closure_evidence_backed_truth_sources_sound.
  exact example_3_model_interpretable.
Qed.
Theorem example_4_atomic_closure_evidence_backed_truth_condition_sound :
  truth_denotes (ledger_truth_conditions atomic_closure_evidence_backed_truth_ledger) PropT example_4.
Proof.
  apply atomic_closure_evidence_backed_truth_sources_sound.
  exact example_4_model_interpretable.
Qed.

Theorem example_1_transition_refined_atomic_closure_truth : TransitionRefinedAtomicClosureTruth PropT example_1.
Proof.
  unfold example_1.
  apply transition_refined_truth_at_T.
  apply transition_refined_truth_butter_application.
  apply atomic_base_truth_butter_application.
Qed.
Theorem example_2_transition_refined_atomic_closure_truth : TransitionRefinedAtomicClosureTruth Prop example_2.
Proof.
  unfold example_2.
  apply transition_refined_truth_sigma_Food.
  intro x_theme.
  apply transition_refined_truth_eat_application.
  apply atomic_base_truth_eat_application.
Qed.
Theorem example_3_transition_refined_atomic_closure_truth : TransitionRefinedAtomicClosureTruth PropT example_3.
Proof.
  unfold example_3.
  apply transition_refined_truth_repeat.
  apply transition_refined_truth_knock_application.
  apply atomic_base_truth_knock_application.
Qed.
Theorem example_4_transition_refined_atomic_closure_truth : TransitionRefinedAtomicClosureTruth PropT example_4.
Proof.
  unfold example_4.
  apply transition_refined_truth_cause.
  apply transition_refined_truth_transition.
  apply registered_transition_vase_integrity_scale_intact_to_broken.
Qed.

Theorem example_1_transition_refined_atomic_closure_sound : AtomicClosureTruth PropT example_1.
Proof.
  apply transition_refined_atomic_closure_truth_implies_atomic_closure_truth.
  exact example_1_transition_refined_atomic_closure_truth.
Qed.
Theorem example_2_transition_refined_atomic_closure_sound : AtomicClosureTruth Prop example_2.
Proof.
  apply transition_refined_atomic_closure_truth_implies_atomic_closure_truth.
  exact example_2_transition_refined_atomic_closure_truth.
Qed.
Theorem example_3_transition_refined_atomic_closure_sound : AtomicClosureTruth PropT example_3.
Proof.
  apply transition_refined_atomic_closure_truth_implies_atomic_closure_truth.
  exact example_3_transition_refined_atomic_closure_truth.
Qed.
Theorem example_4_transition_refined_atomic_closure_sound : AtomicClosureTruth PropT example_4.
Proof.
  apply transition_refined_atomic_closure_truth_implies_atomic_closure_truth.
  exact example_4_transition_refined_atomic_closure_truth.
Qed.

Theorem example_1_transition_refined_registered_truth_condition_sound : registered_truth_denotes transition_refined_registered_truth_conditions PropT example_1.
Proof.
  apply transition_refined_registered_truth_conditions_denote_transition_refined.
  exact example_1_transition_refined_atomic_closure_truth.
Qed.
Theorem example_2_transition_refined_registered_truth_condition_sound : registered_truth_denotes transition_refined_registered_truth_conditions Prop example_2.
Proof.
  apply transition_refined_registered_truth_conditions_denote_transition_refined.
  exact example_2_transition_refined_atomic_closure_truth.
Qed.
Theorem example_3_transition_refined_registered_truth_condition_sound : registered_truth_denotes transition_refined_registered_truth_conditions PropT example_3.
Proof.
  apply transition_refined_registered_truth_conditions_denote_transition_refined.
  exact example_3_transition_refined_atomic_closure_truth.
Qed.
Theorem example_4_transition_refined_registered_truth_condition_sound : registered_truth_denotes transition_refined_registered_truth_conditions PropT example_4.
Proof.
  apply transition_refined_registered_truth_conditions_denote_transition_refined.
  exact example_4_transition_refined_atomic_closure_truth.
Qed.

Theorem example_1_transition_refined_registered_truth_condition_atomic_sound : AtomicClosureTruth PropT example_1.
Proof.
  apply transition_refined_registered_truth_conditions_imply_atomic_closure.
  exact example_1_transition_refined_registered_truth_condition_sound.
Qed.
Theorem example_2_transition_refined_registered_truth_condition_atomic_sound : AtomicClosureTruth Prop example_2.
Proof.
  apply transition_refined_registered_truth_conditions_imply_atomic_closure.
  exact example_2_transition_refined_registered_truth_condition_sound.
Qed.
Theorem example_3_transition_refined_registered_truth_condition_atomic_sound : AtomicClosureTruth PropT example_3.
Proof.
  apply transition_refined_registered_truth_conditions_imply_atomic_closure.
  exact example_3_transition_refined_registered_truth_condition_sound.
Qed.
Theorem example_4_transition_refined_registered_truth_condition_atomic_sound : AtomicClosureTruth PropT example_4.
Proof.
  apply transition_refined_registered_truth_conditions_imply_atomic_closure.
  exact example_4_transition_refined_registered_truth_condition_sound.
Qed.

Theorem example_1_fully_registered_atomic_closure_truth : FullyRegisteredAtomicClosureTruth PropT example_1.
Proof.
  unfold example_1.
  apply fully_registered_atomic_truth_at_T.
  apply fully_registered_atomic_truth_lexical_application.
  apply registered_lexical_butter_2_slowly_in_bathroom_John_toast.
Qed.
Theorem example_2_fully_registered_atomic_closure_truth : FullyRegisteredAtomicClosureTruth Prop example_2.
Proof.
  unfold example_2.
  apply fully_registered_atomic_truth_sigma_Food.
  intro x_theme.
  apply fully_registered_atomic_truth_lexical_application.
  apply registered_lexical_eat_0_John_x_theme.
Qed.
Theorem example_3_fully_registered_atomic_closure_truth : FullyRegisteredAtomicClosureTruth PropT example_3.
Proof.
  unfold example_3.
  apply fully_registered_atomic_truth_repeat.
  apply fully_registered_atomic_truth_lexical_application.
  apply registered_lexical_knock_0_John.
Qed.
Theorem example_4_fully_registered_atomic_closure_truth : FullyRegisteredAtomicClosureTruth PropT example_4.
Proof.
  unfold example_4.
  apply fully_registered_atomic_truth_cause.
  apply fully_registered_atomic_truth_transition.
  apply registered_transition_vase_integrity_scale_intact_to_broken.
Qed.

Theorem example_1_fully_registered_truth_condition_sound : fully_registered_truth_denotes fully_registered_truth_conditions PropT example_1.
Proof.
  apply fully_registered_truth_conditions_denote_fully_registered.
  exact example_1_fully_registered_atomic_closure_truth.
Qed.
Theorem example_2_fully_registered_truth_condition_sound : fully_registered_truth_denotes fully_registered_truth_conditions Prop example_2.
Proof.
  apply fully_registered_truth_conditions_denote_fully_registered.
  exact example_2_fully_registered_atomic_closure_truth.
Qed.
Theorem example_3_fully_registered_truth_condition_sound : fully_registered_truth_denotes fully_registered_truth_conditions PropT example_3.
Proof.
  apply fully_registered_truth_conditions_denote_fully_registered.
  exact example_3_fully_registered_atomic_closure_truth.
Qed.
Theorem example_4_fully_registered_truth_condition_sound : fully_registered_truth_denotes fully_registered_truth_conditions PropT example_4.
Proof.
  apply fully_registered_truth_conditions_denote_fully_registered.
  exact example_4_fully_registered_atomic_closure_truth.
Qed.

Theorem example_1_registered_lexical_truth_model_sound :
  registered_lexical_model_denotes registered_lexical_truth_model PropT example_1.
Proof.
  apply registered_lexical_truth_model_denotes_fully_registered.
  exact example_1_fully_registered_atomic_closure_truth.
Qed.

Theorem example_1_registered_lexical_truth_conditions_from_model_sound :
  fully_registered_truth_denotes registered_lexical_truth_conditions_from_model PropT example_1.
Proof.
  apply registered_lexical_truth_conditions_from_model_denote_fully_registered.
  exact example_1_fully_registered_atomic_closure_truth.
Qed.

Theorem example_2_registered_lexical_truth_model_sound :
  registered_lexical_model_denotes registered_lexical_truth_model Prop example_2.
Proof.
  apply registered_lexical_truth_model_denotes_fully_registered.
  exact example_2_fully_registered_atomic_closure_truth.
Qed.

Theorem example_2_registered_lexical_truth_conditions_from_model_sound :
  fully_registered_truth_denotes registered_lexical_truth_conditions_from_model Prop example_2.
Proof.
  apply registered_lexical_truth_conditions_from_model_denote_fully_registered.
  exact example_2_fully_registered_atomic_closure_truth.
Qed.

Theorem example_3_registered_lexical_truth_model_sound :
  registered_lexical_model_denotes registered_lexical_truth_model PropT example_3.
Proof.
  apply registered_lexical_truth_model_denotes_fully_registered.
  exact example_3_fully_registered_atomic_closure_truth.
Qed.

Theorem example_3_registered_lexical_truth_conditions_from_model_sound :
  fully_registered_truth_denotes registered_lexical_truth_conditions_from_model PropT example_3.
Proof.
  apply registered_lexical_truth_conditions_from_model_denote_fully_registered.
  exact example_3_fully_registered_atomic_closure_truth.
Qed.

Theorem example_4_registered_lexical_truth_model_sound :
  registered_lexical_model_denotes registered_lexical_truth_model PropT example_4.
Proof.
  apply registered_lexical_truth_model_denotes_fully_registered.
  exact example_4_fully_registered_atomic_closure_truth.
Qed.

Theorem example_4_registered_lexical_truth_conditions_from_model_sound :
  fully_registered_truth_denotes registered_lexical_truth_conditions_from_model PropT example_4.
Proof.
  apply registered_lexical_truth_conditions_from_model_denote_fully_registered.
  exact example_4_fully_registered_atomic_closure_truth.
Qed.

Theorem example_1_concrete_registered_truth : ConcreteRegisteredTruth PropT example_1.
Proof.
  unfold example_1.
  apply concrete_registered_truth_at_T.
  apply concrete_registered_truth_atomic.
  apply concrete_registered_atomic_truth_lexical_application.
  apply registered_lexical_butter_2_slowly_in_bathroom_John_toast.
Qed.
Theorem example_2_concrete_registered_truth : ConcreteRegisteredTruth Prop example_2.
Proof.
  unfold example_2.
  apply concrete_registered_truth_sigma_Food.
  intro x_theme.
  apply concrete_registered_truth_atomic.
  apply concrete_registered_atomic_truth_lexical_application.
  apply registered_lexical_eat_0_John_x_theme.
Qed.
Theorem example_3_concrete_registered_truth : ConcreteRegisteredTruth PropT example_3.
Proof.
  unfold example_3.
  apply concrete_registered_truth_repeat.
  apply concrete_registered_truth_atomic.
  apply concrete_registered_atomic_truth_lexical_application.
  apply registered_lexical_knock_0_John.
Qed.
Theorem example_4_concrete_registered_truth : ConcreteRegisteredTruth PropT example_4.
Proof.
  unfold example_4.
  apply concrete_registered_truth_cause.
  apply concrete_registered_truth_atomic.
  apply concrete_registered_atomic_truth_transition.
  apply registered_transition_vase_integrity_scale_intact_to_broken.
Qed.

Theorem example_1_concrete_registered_truth_kernel_sound :
  concrete_registered_kernel_denotes concrete_registered_truth_kernel PropT example_1.
Proof.
  apply concrete_registered_truth_kernel_denotes_concrete_registered.
  exact example_1_concrete_registered_truth.
Qed.

Theorem example_1_concrete_registered_truth_conditions_from_kernel_sound :
  fully_registered_truth_denotes concrete_registered_truth_conditions_from_kernel PropT example_1.
Proof.
  apply concrete_registered_truth_conditions_from_kernel_denote_concrete_registered.
  exact example_1_concrete_registered_truth.
Qed.

Theorem example_1_concrete_registered_truth_conditions_from_kernel_atomic_sound :
  AtomicClosureTruth PropT example_1.
Proof.
  apply concrete_registered_truth_conditions_from_kernel_imply_atomic_closure.
  exact example_1_concrete_registered_truth_conditions_from_kernel_sound.
Qed.

Theorem example_2_concrete_registered_truth_kernel_sound :
  concrete_registered_kernel_denotes concrete_registered_truth_kernel Prop example_2.
Proof.
  apply concrete_registered_truth_kernel_denotes_concrete_registered.
  exact example_2_concrete_registered_truth.
Qed.

Theorem example_2_concrete_registered_truth_conditions_from_kernel_sound :
  fully_registered_truth_denotes concrete_registered_truth_conditions_from_kernel Prop example_2.
Proof.
  apply concrete_registered_truth_conditions_from_kernel_denote_concrete_registered.
  exact example_2_concrete_registered_truth.
Qed.

Theorem example_2_concrete_registered_truth_conditions_from_kernel_atomic_sound :
  AtomicClosureTruth Prop example_2.
Proof.
  apply concrete_registered_truth_conditions_from_kernel_imply_atomic_closure.
  exact example_2_concrete_registered_truth_conditions_from_kernel_sound.
Qed.

Theorem example_3_concrete_registered_truth_kernel_sound :
  concrete_registered_kernel_denotes concrete_registered_truth_kernel PropT example_3.
Proof.
  apply concrete_registered_truth_kernel_denotes_concrete_registered.
  exact example_3_concrete_registered_truth.
Qed.

Theorem example_3_concrete_registered_truth_conditions_from_kernel_sound :
  fully_registered_truth_denotes concrete_registered_truth_conditions_from_kernel PropT example_3.
Proof.
  apply concrete_registered_truth_conditions_from_kernel_denote_concrete_registered.
  exact example_3_concrete_registered_truth.
Qed.

Theorem example_3_concrete_registered_truth_conditions_from_kernel_atomic_sound :
  AtomicClosureTruth PropT example_3.
Proof.
  apply concrete_registered_truth_conditions_from_kernel_imply_atomic_closure.
  exact example_3_concrete_registered_truth_conditions_from_kernel_sound.
Qed.

Theorem example_4_concrete_registered_truth_kernel_sound :
  concrete_registered_kernel_denotes concrete_registered_truth_kernel PropT example_4.
Proof.
  apply concrete_registered_truth_kernel_denotes_concrete_registered.
  exact example_4_concrete_registered_truth.
Qed.

Theorem example_4_concrete_registered_truth_conditions_from_kernel_sound :
  fully_registered_truth_denotes concrete_registered_truth_conditions_from_kernel PropT example_4.
Proof.
  apply concrete_registered_truth_conditions_from_kernel_denote_concrete_registered.
  exact example_4_concrete_registered_truth.
Qed.

Theorem example_4_concrete_registered_truth_conditions_from_kernel_atomic_sound :
  AtomicClosureTruth PropT example_4.
Proof.
  apply concrete_registered_truth_conditions_from_kernel_imply_atomic_closure.
  exact example_4_concrete_registered_truth_conditions_from_kernel_sound.
Qed.

Theorem example_1_concrete_registered_truth_condition_sound : fully_registered_truth_denotes concrete_registered_truth_conditions PropT example_1.
Proof.
  apply concrete_registered_truth_conditions_denote_concrete_registered.
  exact example_1_concrete_registered_truth.
Qed.
Theorem example_2_concrete_registered_truth_condition_sound : fully_registered_truth_denotes concrete_registered_truth_conditions Prop example_2.
Proof.
  apply concrete_registered_truth_conditions_denote_concrete_registered.
  exact example_2_concrete_registered_truth.
Qed.
Theorem example_3_concrete_registered_truth_condition_sound : fully_registered_truth_denotes concrete_registered_truth_conditions PropT example_3.
Proof.
  apply concrete_registered_truth_conditions_denote_concrete_registered.
  exact example_3_concrete_registered_truth.
Qed.
Theorem example_4_concrete_registered_truth_condition_sound : fully_registered_truth_denotes concrete_registered_truth_conditions PropT example_4.
Proof.
  apply concrete_registered_truth_conditions_denote_concrete_registered.
  exact example_4_concrete_registered_truth.
Qed.

Theorem example_1_concrete_registered_truth_condition_atomic_sound : AtomicClosureTruth PropT example_1.
Proof.
  apply concrete_registered_truth_conditions_imply_atomic_closure.
  exact example_1_concrete_registered_truth_condition_sound.
Qed.
Theorem example_2_concrete_registered_truth_condition_atomic_sound : AtomicClosureTruth Prop example_2.
Proof.
  apply concrete_registered_truth_conditions_imply_atomic_closure.
  exact example_2_concrete_registered_truth_condition_sound.
Qed.
Theorem example_3_concrete_registered_truth_condition_atomic_sound : AtomicClosureTruth PropT example_3.
Proof.
  apply concrete_registered_truth_conditions_imply_atomic_closure.
  exact example_3_concrete_registered_truth_condition_sound.
Qed.
Theorem example_4_concrete_registered_truth_condition_atomic_sound : AtomicClosureTruth PropT example_4.
Proof.
  apply concrete_registered_truth_conditions_imply_atomic_closure.
  exact example_4_concrete_registered_truth_condition_sound.
Qed.

Theorem example_1_concrete_registered_evidence_backed_truth_condition_sound : fully_registered_truth_denotes concrete_registered_evidence_backed_truth_conditions PropT example_1.
Proof.
  apply concrete_registered_evidence_backed_truth_conditions_denote_concrete_registered.
  exact example_1_concrete_registered_truth.
Qed.

Theorem example_1_concrete_registered_evidence_backed_truth_condition_atomic_sound : AtomicClosureTruth PropT example_1.
Proof.
  apply concrete_registered_evidence_backed_truth_conditions_imply_atomic_closure.
  exact example_1_concrete_registered_evidence_backed_truth_condition_sound.
Qed.

Theorem example_2_concrete_registered_evidence_backed_truth_condition_sound : fully_registered_truth_denotes concrete_registered_evidence_backed_truth_conditions Prop example_2.
Proof.
  apply concrete_registered_evidence_backed_truth_conditions_denote_concrete_registered.
  exact example_2_concrete_registered_truth.
Qed.

Theorem example_2_concrete_registered_evidence_backed_truth_condition_atomic_sound : AtomicClosureTruth Prop example_2.
Proof.
  apply concrete_registered_evidence_backed_truth_conditions_imply_atomic_closure.
  exact example_2_concrete_registered_evidence_backed_truth_condition_sound.
Qed.

Theorem example_3_concrete_registered_evidence_backed_truth_condition_sound : fully_registered_truth_denotes concrete_registered_evidence_backed_truth_conditions PropT example_3.
Proof.
  apply concrete_registered_evidence_backed_truth_conditions_denote_concrete_registered.
  exact example_3_concrete_registered_truth.
Qed.

Theorem example_3_concrete_registered_evidence_backed_truth_condition_atomic_sound : AtomicClosureTruth PropT example_3.
Proof.
  apply concrete_registered_evidence_backed_truth_conditions_imply_atomic_closure.
  exact example_3_concrete_registered_evidence_backed_truth_condition_sound.
Qed.

Theorem example_4_concrete_registered_evidence_backed_truth_condition_sound : fully_registered_truth_denotes concrete_registered_evidence_backed_truth_conditions PropT example_4.
Proof.
  apply concrete_registered_evidence_backed_truth_conditions_denote_concrete_registered.
  exact example_4_concrete_registered_truth.
Qed.

Theorem example_4_concrete_registered_evidence_backed_truth_condition_atomic_sound : AtomicClosureTruth PropT example_4.
Proof.
  apply concrete_registered_evidence_backed_truth_conditions_imply_atomic_closure.
  exact example_4_concrete_registered_evidence_backed_truth_condition_sound.
Qed.

Record ConcreteRegisteredEvidenceBackedExampleTruthInstances : Type := {
  example_1_evidence_backed_truth_instance :
      fully_registered_truth_denotes concrete_registered_evidence_backed_truth_conditions PropT example_1;
  example_2_evidence_backed_truth_instance :
      fully_registered_truth_denotes concrete_registered_evidence_backed_truth_conditions Prop example_2;
  example_3_evidence_backed_truth_instance :
      fully_registered_truth_denotes concrete_registered_evidence_backed_truth_conditions PropT example_3;
  example_4_evidence_backed_truth_instance :
      fully_registered_truth_denotes concrete_registered_evidence_backed_truth_conditions PropT example_4
}.

Definition concrete_registered_evidence_backed_example_truth_instances : ConcreteRegisteredEvidenceBackedExampleTruthInstances := {|
  example_1_evidence_backed_truth_instance := example_1_concrete_registered_evidence_backed_truth_condition_sound;
  example_2_evidence_backed_truth_instance := example_2_concrete_registered_evidence_backed_truth_condition_sound;
  example_3_evidence_backed_truth_instance := example_3_concrete_registered_evidence_backed_truth_condition_sound;
  example_4_evidence_backed_truth_instance := example_4_concrete_registered_evidence_backed_truth_condition_sound
|}.

Theorem concrete_registered_evidence_backed_example_truth_instances_exists :
  exists I : ConcreteRegisteredEvidenceBackedExampleTruthInstances,
    I = concrete_registered_evidence_backed_example_truth_instances.
Proof.
  exists concrete_registered_evidence_backed_example_truth_instances.
  reflexivity.
Qed.

Theorem concrete_registered_evidence_backed_example_1_truth_instance_atomic_sound : AtomicClosureTruth PropT example_1.
Proof.
  apply concrete_registered_evidence_backed_truth_conditions_imply_atomic_closure.
  exact (example_1_evidence_backed_truth_instance concrete_registered_evidence_backed_example_truth_instances).
Qed.

Theorem concrete_registered_evidence_backed_example_2_truth_instance_atomic_sound : AtomicClosureTruth Prop example_2.
Proof.
  apply concrete_registered_evidence_backed_truth_conditions_imply_atomic_closure.
  exact (example_2_evidence_backed_truth_instance concrete_registered_evidence_backed_example_truth_instances).
Qed.

Theorem concrete_registered_evidence_backed_example_3_truth_instance_atomic_sound : AtomicClosureTruth PropT example_3.
Proof.
  apply concrete_registered_evidence_backed_truth_conditions_imply_atomic_closure.
  exact (example_3_evidence_backed_truth_instance concrete_registered_evidence_backed_example_truth_instances).
Qed.

Theorem concrete_registered_evidence_backed_example_4_truth_instance_atomic_sound : AtomicClosureTruth PropT example_4.
Proof.
  apply concrete_registered_evidence_backed_truth_conditions_imply_atomic_closure.
  exact (example_4_evidence_backed_truth_instance concrete_registered_evidence_backed_example_truth_instances).
Qed.

Record ConcreteRegisteredExampleTruthInstances : Type := {
  example_1_concrete_truth_instance :
      fully_registered_truth_denotes concrete_registered_truth_conditions PropT example_1;
  example_2_concrete_truth_instance :
      fully_registered_truth_denotes concrete_registered_truth_conditions Prop example_2;
  example_3_concrete_truth_instance :
      fully_registered_truth_denotes concrete_registered_truth_conditions PropT example_3;
  example_4_concrete_truth_instance :
      fully_registered_truth_denotes concrete_registered_truth_conditions PropT example_4
}.

Definition concrete_registered_example_truth_instances : ConcreteRegisteredExampleTruthInstances := {|
  example_1_concrete_truth_instance := example_1_concrete_registered_truth_condition_sound;
  example_2_concrete_truth_instance := example_2_concrete_registered_truth_condition_sound;
  example_3_concrete_truth_instance := example_3_concrete_registered_truth_condition_sound;
  example_4_concrete_truth_instance := example_4_concrete_registered_truth_condition_sound
|}.

Theorem concrete_registered_example_truth_instances_exists :
  exists I : ConcreteRegisteredExampleTruthInstances,
    I = concrete_registered_example_truth_instances.
Proof.
  exists concrete_registered_example_truth_instances. reflexivity.
Qed.

Theorem concrete_registered_example_1_truth_instance_atomic_sound : AtomicClosureTruth PropT example_1.
Proof.
  apply concrete_registered_truth_conditions_imply_atomic_closure.
  exact (example_1_concrete_truth_instance concrete_registered_example_truth_instances).
Qed.

Theorem concrete_registered_example_2_truth_instance_atomic_sound : AtomicClosureTruth Prop example_2.
Proof.
  apply concrete_registered_truth_conditions_imply_atomic_closure.
  exact (example_2_concrete_truth_instance concrete_registered_example_truth_instances).
Qed.

Theorem concrete_registered_example_3_truth_instance_atomic_sound : AtomicClosureTruth PropT example_3.
Proof.
  apply concrete_registered_truth_conditions_imply_atomic_closure.
  exact (example_3_concrete_truth_instance concrete_registered_example_truth_instances).
Qed.

Theorem concrete_registered_example_4_truth_instance_atomic_sound : AtomicClosureTruth PropT example_4.
Proof.
  apply concrete_registered_truth_conditions_imply_atomic_closure.
  exact (example_4_concrete_truth_instance concrete_registered_example_truth_instances).
Qed.

Record ConcreteRegisteredKernelExampleTruthInstances : Type := {
  example_1_kernel_truth_instance :
      fully_registered_truth_denotes concrete_registered_truth_conditions_from_kernel PropT example_1;
  example_2_kernel_truth_instance :
      fully_registered_truth_denotes concrete_registered_truth_conditions_from_kernel Prop example_2;
  example_3_kernel_truth_instance :
      fully_registered_truth_denotes concrete_registered_truth_conditions_from_kernel PropT example_3;
  example_4_kernel_truth_instance :
      fully_registered_truth_denotes concrete_registered_truth_conditions_from_kernel PropT example_4
}.

Definition concrete_registered_kernel_example_truth_instances : ConcreteRegisteredKernelExampleTruthInstances := {|
  example_1_kernel_truth_instance := example_1_concrete_registered_truth_conditions_from_kernel_sound;
  example_2_kernel_truth_instance := example_2_concrete_registered_truth_conditions_from_kernel_sound;
  example_3_kernel_truth_instance := example_3_concrete_registered_truth_conditions_from_kernel_sound;
  example_4_kernel_truth_instance := example_4_concrete_registered_truth_conditions_from_kernel_sound
|}.

Theorem concrete_registered_kernel_example_truth_instances_exists :
  exists I : ConcreteRegisteredKernelExampleTruthInstances,
    I = concrete_registered_kernel_example_truth_instances.
Proof.
  exists concrete_registered_kernel_example_truth_instances. reflexivity.
Qed.

Theorem concrete_registered_kernel_example_1_truth_instance_atomic_sound : AtomicClosureTruth PropT example_1.
Proof.
  apply concrete_registered_truth_conditions_from_kernel_imply_atomic_closure.
  exact (example_1_kernel_truth_instance concrete_registered_kernel_example_truth_instances).
Qed.

Theorem concrete_registered_kernel_example_2_truth_instance_atomic_sound : AtomicClosureTruth Prop example_2.
Proof.
  apply concrete_registered_truth_conditions_from_kernel_imply_atomic_closure.
  exact (example_2_kernel_truth_instance concrete_registered_kernel_example_truth_instances).
Qed.

Theorem concrete_registered_kernel_example_3_truth_instance_atomic_sound : AtomicClosureTruth PropT example_3.
Proof.
  apply concrete_registered_truth_conditions_from_kernel_imply_atomic_closure.
  exact (example_3_kernel_truth_instance concrete_registered_kernel_example_truth_instances).
Qed.

Theorem concrete_registered_kernel_example_4_truth_instance_atomic_sound : AtomicClosureTruth PropT example_4.
Proof.
  apply concrete_registered_truth_conditions_from_kernel_imply_atomic_closure.
  exact (example_4_kernel_truth_instance concrete_registered_kernel_example_truth_instances).
Qed.

Record ConcreteRegisteredTruthConditionRoute : Type := {
  concrete_registered_route_direct_model : ConcreteRegisteredTruthConditionModel;
  concrete_registered_route_evidence_sources : RegisteredEvidenceBackedTruthConditionSources;
  concrete_registered_route_evidence_model : ConcreteRegisteredEvidenceBackedTruthConditionModel;
  concrete_registered_route_kernel : ConcreteRegisteredTruthKernel;
  concrete_registered_route_direct_spec : FullyRegisteredTruthConditionSpec;
  concrete_registered_route_evidence_spec : FullyRegisteredTruthConditionSpec;
  concrete_registered_route_kernel_spec : FullyRegisteredTruthConditionSpec;
  concrete_registered_route_direct_examples : ConcreteRegisteredExampleTruthInstances;
  concrete_registered_route_evidence_examples : ConcreteRegisteredEvidenceBackedExampleTruthInstances;
  concrete_registered_route_kernel_examples : ConcreteRegisteredKernelExampleTruthInstances
}.

Definition concrete_registered_truth_condition_route :
  ConcreteRegisteredTruthConditionRoute := {|
  concrete_registered_route_direct_model := concrete_registered_truth_condition_model;
  concrete_registered_route_evidence_sources := concrete_registered_evidence_backed_truth_sources;
  concrete_registered_route_evidence_model := concrete_registered_evidence_backed_truth_condition_model;
  concrete_registered_route_kernel := concrete_registered_truth_kernel;
  concrete_registered_route_direct_spec := concrete_registered_truth_conditions;
  concrete_registered_route_evidence_spec := concrete_registered_evidence_backed_truth_conditions;
  concrete_registered_route_kernel_spec := concrete_registered_truth_conditions_from_kernel;
  concrete_registered_route_direct_examples := concrete_registered_example_truth_instances;
  concrete_registered_route_evidence_examples := concrete_registered_evidence_backed_example_truth_instances;
  concrete_registered_route_kernel_examples := concrete_registered_kernel_example_truth_instances
|}.

Theorem concrete_registered_truth_condition_route_exists :
  exists R : ConcreteRegisteredTruthConditionRoute,
    R = concrete_registered_truth_condition_route.
Proof.
  exists concrete_registered_truth_condition_route. reflexivity.
Qed.

Theorem concrete_registered_truth_condition_route_direct_spec_matches_model :
  concrete_registered_route_direct_spec concrete_registered_truth_condition_route =
    concrete_registered_model_spec
      (concrete_registered_route_direct_model
        concrete_registered_truth_condition_route).
Proof. reflexivity. Qed.

Theorem concrete_registered_truth_condition_route_evidence_spec_matches_model :
  concrete_registered_route_evidence_spec concrete_registered_truth_condition_route =
    concrete_registered_evidence_backed_model_spec
      (concrete_registered_route_evidence_model
        concrete_registered_truth_condition_route).
Proof. reflexivity. Qed.

Theorem concrete_registered_truth_condition_route_kernel_spec_matches_kernel :
  concrete_registered_route_kernel_spec concrete_registered_truth_condition_route =
    fully_registered_truth_conditions_from_concrete_registered_kernel
      (concrete_registered_route_kernel
        concrete_registered_truth_condition_route).
Proof. reflexivity. Qed.

Theorem concrete_registered_truth_condition_route_direct_spec_sound :
  forall A : Type, forall term : A,
    fully_registered_truth_denotes
      (concrete_registered_route_direct_spec
        concrete_registered_truth_condition_route) A term ->
    AtomicClosureTruth A term.
Proof.
  intros A term H.
  apply concrete_registered_truth_conditions_imply_atomic_closure.
  exact H.
Qed.

Theorem concrete_registered_truth_condition_route_evidence_spec_sound :
  forall A : Type, forall term : A,
    fully_registered_truth_denotes
      (concrete_registered_route_evidence_spec
        concrete_registered_truth_condition_route) A term ->
    AtomicClosureTruth A term.
Proof.
  intros A term H.
  apply concrete_registered_evidence_backed_truth_conditions_imply_atomic_closure.
  exact H.
Qed.

Theorem concrete_registered_truth_condition_route_kernel_spec_sound :
  forall A : Type, forall term : A,
    fully_registered_truth_denotes
      (concrete_registered_route_kernel_spec
        concrete_registered_truth_condition_route) A term ->
    AtomicClosureTruth A term.
Proof.
  intros A term H.
  apply concrete_registered_truth_conditions_from_kernel_imply_atomic_closure.
  exact H.
Qed.

Theorem concrete_registered_truth_condition_route_example_1_direct_atomic_sound : AtomicClosureTruth PropT example_1.
Proof.
  apply concrete_registered_truth_condition_route_direct_spec_sound.
  exact (example_1_concrete_truth_instance
    (concrete_registered_route_direct_examples
      concrete_registered_truth_condition_route)).
Qed.

Theorem concrete_registered_truth_condition_route_example_1_evidence_atomic_sound : AtomicClosureTruth PropT example_1.
Proof.
  apply concrete_registered_truth_condition_route_evidence_spec_sound.
  exact (example_1_evidence_backed_truth_instance
    (concrete_registered_route_evidence_examples
      concrete_registered_truth_condition_route)).
Qed.

Theorem concrete_registered_truth_condition_route_example_1_kernel_atomic_sound : AtomicClosureTruth PropT example_1.
Proof.
  apply concrete_registered_truth_condition_route_kernel_spec_sound.
  exact (example_1_kernel_truth_instance
    (concrete_registered_route_kernel_examples
      concrete_registered_truth_condition_route)).
Qed.

Theorem concrete_registered_truth_condition_route_example_2_direct_atomic_sound : AtomicClosureTruth Prop example_2.
Proof.
  apply concrete_registered_truth_condition_route_direct_spec_sound.
  exact (example_2_concrete_truth_instance
    (concrete_registered_route_direct_examples
      concrete_registered_truth_condition_route)).
Qed.

Theorem concrete_registered_truth_condition_route_example_2_evidence_atomic_sound : AtomicClosureTruth Prop example_2.
Proof.
  apply concrete_registered_truth_condition_route_evidence_spec_sound.
  exact (example_2_evidence_backed_truth_instance
    (concrete_registered_route_evidence_examples
      concrete_registered_truth_condition_route)).
Qed.

Theorem concrete_registered_truth_condition_route_example_2_kernel_atomic_sound : AtomicClosureTruth Prop example_2.
Proof.
  apply concrete_registered_truth_condition_route_kernel_spec_sound.
  exact (example_2_kernel_truth_instance
    (concrete_registered_route_kernel_examples
      concrete_registered_truth_condition_route)).
Qed.

Theorem concrete_registered_truth_condition_route_example_3_direct_atomic_sound : AtomicClosureTruth PropT example_3.
Proof.
  apply concrete_registered_truth_condition_route_direct_spec_sound.
  exact (example_3_concrete_truth_instance
    (concrete_registered_route_direct_examples
      concrete_registered_truth_condition_route)).
Qed.

Theorem concrete_registered_truth_condition_route_example_3_evidence_atomic_sound : AtomicClosureTruth PropT example_3.
Proof.
  apply concrete_registered_truth_condition_route_evidence_spec_sound.
  exact (example_3_evidence_backed_truth_instance
    (concrete_registered_route_evidence_examples
      concrete_registered_truth_condition_route)).
Qed.

Theorem concrete_registered_truth_condition_route_example_3_kernel_atomic_sound : AtomicClosureTruth PropT example_3.
Proof.
  apply concrete_registered_truth_condition_route_kernel_spec_sound.
  exact (example_3_kernel_truth_instance
    (concrete_registered_route_kernel_examples
      concrete_registered_truth_condition_route)).
Qed.

Theorem concrete_registered_truth_condition_route_example_4_direct_atomic_sound : AtomicClosureTruth PropT example_4.
Proof.
  apply concrete_registered_truth_condition_route_direct_spec_sound.
  exact (example_4_concrete_truth_instance
    (concrete_registered_route_direct_examples
      concrete_registered_truth_condition_route)).
Qed.

Theorem concrete_registered_truth_condition_route_example_4_evidence_atomic_sound : AtomicClosureTruth PropT example_4.
Proof.
  apply concrete_registered_truth_condition_route_evidence_spec_sound.
  exact (example_4_evidence_backed_truth_instance
    (concrete_registered_route_evidence_examples
      concrete_registered_truth_condition_route)).
Qed.

Theorem concrete_registered_truth_condition_route_example_4_kernel_atomic_sound : AtomicClosureTruth PropT example_4.
Proof.
  apply concrete_registered_truth_condition_route_kernel_spec_sound.
  exact (example_4_kernel_truth_instance
    (concrete_registered_route_kernel_examples
      concrete_registered_truth_condition_route)).
Qed.

Record ConcreteRegisteredTruthConditionRouteExampleAgreement : Type := {
  concrete_registered_route_agreement_route : ConcreteRegisteredTruthConditionRoute;
  concrete_registered_route_agreement_example_1_direct_atomic :
      AtomicClosureTruth PropT example_1;
  concrete_registered_route_agreement_example_1_evidence_atomic :
      AtomicClosureTruth PropT example_1;
  concrete_registered_route_agreement_example_1_kernel_atomic :
      AtomicClosureTruth PropT example_1;
  concrete_registered_route_agreement_example_2_direct_atomic :
      AtomicClosureTruth Prop example_2;
  concrete_registered_route_agreement_example_2_evidence_atomic :
      AtomicClosureTruth Prop example_2;
  concrete_registered_route_agreement_example_2_kernel_atomic :
      AtomicClosureTruth Prop example_2;
  concrete_registered_route_agreement_example_3_direct_atomic :
      AtomicClosureTruth PropT example_3;
  concrete_registered_route_agreement_example_3_evidence_atomic :
      AtomicClosureTruth PropT example_3;
  concrete_registered_route_agreement_example_3_kernel_atomic :
      AtomicClosureTruth PropT example_3;
  concrete_registered_route_agreement_example_4_direct_atomic :
      AtomicClosureTruth PropT example_4;
  concrete_registered_route_agreement_example_4_evidence_atomic :
      AtomicClosureTruth PropT example_4;
  concrete_registered_route_agreement_example_4_kernel_atomic :
      AtomicClosureTruth PropT example_4
}.

Definition concrete_registered_truth_condition_route_example_agreement :
  ConcreteRegisteredTruthConditionRouteExampleAgreement := {|
  concrete_registered_route_agreement_route := concrete_registered_truth_condition_route;
  concrete_registered_route_agreement_example_1_direct_atomic := concrete_registered_truth_condition_route_example_1_direct_atomic_sound;
  concrete_registered_route_agreement_example_1_evidence_atomic := concrete_registered_truth_condition_route_example_1_evidence_atomic_sound;
  concrete_registered_route_agreement_example_1_kernel_atomic := concrete_registered_truth_condition_route_example_1_kernel_atomic_sound;
  concrete_registered_route_agreement_example_2_direct_atomic := concrete_registered_truth_condition_route_example_2_direct_atomic_sound;
  concrete_registered_route_agreement_example_2_evidence_atomic := concrete_registered_truth_condition_route_example_2_evidence_atomic_sound;
  concrete_registered_route_agreement_example_2_kernel_atomic := concrete_registered_truth_condition_route_example_2_kernel_atomic_sound;
  concrete_registered_route_agreement_example_3_direct_atomic := concrete_registered_truth_condition_route_example_3_direct_atomic_sound;
  concrete_registered_route_agreement_example_3_evidence_atomic := concrete_registered_truth_condition_route_example_3_evidence_atomic_sound;
  concrete_registered_route_agreement_example_3_kernel_atomic := concrete_registered_truth_condition_route_example_3_kernel_atomic_sound;
  concrete_registered_route_agreement_example_4_direct_atomic := concrete_registered_truth_condition_route_example_4_direct_atomic_sound;
  concrete_registered_route_agreement_example_4_evidence_atomic := concrete_registered_truth_condition_route_example_4_evidence_atomic_sound;
  concrete_registered_route_agreement_example_4_kernel_atomic := concrete_registered_truth_condition_route_example_4_kernel_atomic_sound
|}.

Theorem concrete_registered_truth_condition_route_example_agreement_exists :
  exists A : ConcreteRegisteredTruthConditionRouteExampleAgreement,
    A = concrete_registered_truth_condition_route_example_agreement.
Proof.
  exists concrete_registered_truth_condition_route_example_agreement.
  reflexivity.
Qed.

Theorem concrete_registered_truth_condition_route_example_agreement_route_matches :
  concrete_registered_route_agreement_route
    concrete_registered_truth_condition_route_example_agreement =
  concrete_registered_truth_condition_route.
Proof. reflexivity. Qed.

Theorem concrete_registered_truth_condition_route_example_1_agreement_direct_atomic_sound : AtomicClosureTruth PropT example_1.
Proof.
  exact (concrete_registered_route_agreement_example_1_direct_atomic concrete_registered_truth_condition_route_example_agreement).
Qed.

Theorem concrete_registered_truth_condition_route_example_1_agreement_evidence_atomic_sound : AtomicClosureTruth PropT example_1.
Proof.
  exact (concrete_registered_route_agreement_example_1_evidence_atomic concrete_registered_truth_condition_route_example_agreement).
Qed.

Theorem concrete_registered_truth_condition_route_example_1_agreement_kernel_atomic_sound : AtomicClosureTruth PropT example_1.
Proof.
  exact (concrete_registered_route_agreement_example_1_kernel_atomic concrete_registered_truth_condition_route_example_agreement).
Qed.

Theorem concrete_registered_truth_condition_route_example_2_agreement_direct_atomic_sound : AtomicClosureTruth Prop example_2.
Proof.
  exact (concrete_registered_route_agreement_example_2_direct_atomic concrete_registered_truth_condition_route_example_agreement).
Qed.

Theorem concrete_registered_truth_condition_route_example_2_agreement_evidence_atomic_sound : AtomicClosureTruth Prop example_2.
Proof.
  exact (concrete_registered_route_agreement_example_2_evidence_atomic concrete_registered_truth_condition_route_example_agreement).
Qed.

Theorem concrete_registered_truth_condition_route_example_2_agreement_kernel_atomic_sound : AtomicClosureTruth Prop example_2.
Proof.
  exact (concrete_registered_route_agreement_example_2_kernel_atomic concrete_registered_truth_condition_route_example_agreement).
Qed.

Theorem concrete_registered_truth_condition_route_example_3_agreement_direct_atomic_sound : AtomicClosureTruth PropT example_3.
Proof.
  exact (concrete_registered_route_agreement_example_3_direct_atomic concrete_registered_truth_condition_route_example_agreement).
Qed.

Theorem concrete_registered_truth_condition_route_example_3_agreement_evidence_atomic_sound : AtomicClosureTruth PropT example_3.
Proof.
  exact (concrete_registered_route_agreement_example_3_evidence_atomic concrete_registered_truth_condition_route_example_agreement).
Qed.

Theorem concrete_registered_truth_condition_route_example_3_agreement_kernel_atomic_sound : AtomicClosureTruth PropT example_3.
Proof.
  exact (concrete_registered_route_agreement_example_3_kernel_atomic concrete_registered_truth_condition_route_example_agreement).
Qed.

Theorem concrete_registered_truth_condition_route_example_4_agreement_direct_atomic_sound : AtomicClosureTruth PropT example_4.
Proof.
  exact (concrete_registered_route_agreement_example_4_direct_atomic concrete_registered_truth_condition_route_example_agreement).
Qed.

Theorem concrete_registered_truth_condition_route_example_4_agreement_evidence_atomic_sound : AtomicClosureTruth PropT example_4.
Proof.
  exact (concrete_registered_route_agreement_example_4_evidence_atomic concrete_registered_truth_condition_route_example_agreement).
Qed.

Theorem concrete_registered_truth_condition_route_example_4_agreement_kernel_atomic_sound : AtomicClosureTruth PropT example_4.
Proof.
  exact (concrete_registered_route_agreement_example_4_kernel_atomic concrete_registered_truth_condition_route_example_agreement).
Qed.

Record IndependentRegisteredTruthConditionSources : Type := {
  independent_registered_truth_condition_route : ConcreteRegisteredTruthConditionRoute;
  independent_registered_truth_condition_agreement : ConcreteRegisteredTruthConditionRouteExampleAgreement;
  independent_registered_truth_condition_spec : FullyRegisteredTruthConditionSpec;
  independent_registered_truth_condition_spec_route_eq :
      independent_registered_truth_condition_spec =
        concrete_registered_route_direct_spec
          independent_registered_truth_condition_route;
  independent_registered_truth_condition_agreement_route_eq :
      concrete_registered_route_agreement_route
        independent_registered_truth_condition_agreement =
        independent_registered_truth_condition_route;
  independent_registered_truth_condition_examples : ConcreteRegisteredExampleTruthInstances
}.

Definition independent_registered_truth_condition_sources :
  IndependentRegisteredTruthConditionSources := {|
  independent_registered_truth_condition_route := concrete_registered_truth_condition_route;
  independent_registered_truth_condition_agreement := concrete_registered_truth_condition_route_example_agreement;
  independent_registered_truth_condition_spec := concrete_registered_truth_conditions;
  independent_registered_truth_condition_spec_route_eq := eq_refl;
  independent_registered_truth_condition_agreement_route_eq := eq_refl;
  independent_registered_truth_condition_examples := concrete_registered_example_truth_instances
|}.

Theorem independent_registered_truth_condition_sources_exist :
  exists S : IndependentRegisteredTruthConditionSources,
    S = independent_registered_truth_condition_sources.
Proof.
  exists independent_registered_truth_condition_sources. reflexivity.
Qed.

Theorem independent_registered_truth_condition_sources_spec_matches_route :
  independent_registered_truth_condition_spec
    independent_registered_truth_condition_sources =
  concrete_registered_route_direct_spec
    (independent_registered_truth_condition_route
      independent_registered_truth_condition_sources).
Proof.
  exact (independent_registered_truth_condition_spec_route_eq
    independent_registered_truth_condition_sources).
Qed.

Theorem independent_registered_truth_condition_sources_agreement_matches_route :
  concrete_registered_route_agreement_route
    (independent_registered_truth_condition_agreement
      independent_registered_truth_condition_sources) =
  independent_registered_truth_condition_route
    independent_registered_truth_condition_sources.
Proof.
  exact (independent_registered_truth_condition_agreement_route_eq
    independent_registered_truth_condition_sources).
Qed.

Theorem independent_registered_truth_condition_sources_spec_sound :
  forall A : Type, forall term : A,
    fully_registered_truth_denotes
      (independent_registered_truth_condition_spec
        independent_registered_truth_condition_sources) A term ->
    AtomicClosureTruth A term.
Proof.
  intros A term H.
  apply concrete_registered_truth_condition_route_direct_spec_sound.
  exact H.
Qed.

Theorem independent_registered_truth_condition_sources_example_1_atomic_sound : AtomicClosureTruth PropT example_1.
Proof.
  exact (concrete_registered_route_agreement_example_1_direct_atomic
    (independent_registered_truth_condition_agreement
      independent_registered_truth_condition_sources)).
Qed.

Theorem independent_registered_truth_condition_sources_example_2_atomic_sound : AtomicClosureTruth Prop example_2.
Proof.
  exact (concrete_registered_route_agreement_example_2_direct_atomic
    (independent_registered_truth_condition_agreement
      independent_registered_truth_condition_sources)).
Qed.

Theorem independent_registered_truth_condition_sources_example_3_atomic_sound : AtomicClosureTruth PropT example_3.
Proof.
  exact (concrete_registered_route_agreement_example_3_direct_atomic
    (independent_registered_truth_condition_agreement
      independent_registered_truth_condition_sources)).
Qed.

Theorem independent_registered_truth_condition_sources_example_4_atomic_sound : AtomicClosureTruth PropT example_4.
Proof.
  exact (concrete_registered_route_agreement_example_4_direct_atomic
    (independent_registered_truth_condition_agreement
      independent_registered_truth_condition_sources)).
Qed.

Record IndependentRegisteredTruthConditionClauseInstances : Type := {
  independent_registered_clause_source : IndependentRegisteredTruthConditionSources;
  independent_registered_clause_spec : FullyRegisteredTruthConditionSpec;
  independent_registered_clause_spec_eq :
      independent_registered_clause_spec =
        independent_registered_truth_condition_spec
          independent_registered_clause_source
}.

Definition independent_registered_truth_condition_clause_instances :
  IndependentRegisteredTruthConditionClauseInstances := {|
  independent_registered_clause_source := independent_registered_truth_condition_sources;
  independent_registered_clause_spec := independent_registered_truth_condition_spec
    independent_registered_truth_condition_sources;
  independent_registered_clause_spec_eq := eq_refl
|}.

Theorem independent_registered_truth_condition_clause_instances_exists :
  exists C : IndependentRegisteredTruthConditionClauseInstances,
    C = independent_registered_truth_condition_clause_instances.
Proof.
  exists independent_registered_truth_condition_clause_instances.
  reflexivity.
Qed.

Theorem independent_registered_truth_condition_clause_spec_matches_source :
  independent_registered_clause_spec
    independent_registered_truth_condition_clause_instances =
  independent_registered_truth_condition_spec
    (independent_registered_clause_source
      independent_registered_truth_condition_clause_instances).
Proof.
  exact (independent_registered_clause_spec_eq
    independent_registered_truth_condition_clause_instances).
Qed.

Theorem independent_registered_truth_condition_clause_lexical_application_instance :
  forall A : Type, forall term : A,
    RegisteredLexicalApplicationTruth A term ->
    fully_registered_truth_denotes
      (independent_registered_clause_spec
        independent_registered_truth_condition_clause_instances) A term.
Proof.
  intros A term H.
  exact (fully_registered_truth_lexical_application
    (independent_registered_clause_spec
      independent_registered_truth_condition_clause_instances) A term H).
Qed.

Theorem independent_registered_truth_condition_clause_sigma_Entity_instance :
  forall P : Entity -> Prop,
    (forall x : Entity,
      fully_registered_truth_denotes
        (independent_registered_clause_spec
          independent_registered_truth_condition_clause_instances)
        Prop (P x)) ->
    fully_registered_truth_denotes
      (independent_registered_clause_spec
        independent_registered_truth_condition_clause_instances)
      Prop (exists x : Entity, P x).
Proof.
  intros P H.
  exact (fully_registered_truth_sigma_Entity
    (independent_registered_clause_spec
      independent_registered_truth_condition_clause_instances)
    P H).
Qed.

Theorem independent_registered_truth_condition_clause_sigma_Food_instance :
  forall P : Food -> Prop,
    (forall x : Food,
      fully_registered_truth_denotes
        (independent_registered_clause_spec
          independent_registered_truth_condition_clause_instances)
        Prop (P x)) ->
    fully_registered_truth_denotes
      (independent_registered_clause_spec
        independent_registered_truth_condition_clause_instances)
      Prop (exists x : Food, P x).
Proof.
  intros P H.
  exact (fully_registered_truth_sigma_Food
    (independent_registered_clause_spec
      independent_registered_truth_condition_clause_instances)
    P H).
Qed.

Theorem independent_registered_truth_condition_clause_sigma_State_instance :
  forall P : State -> Prop,
    (forall x : State,
      fully_registered_truth_denotes
        (independent_registered_clause_spec
          independent_registered_truth_condition_clause_instances)
        Prop (P x)) ->
    fully_registered_truth_denotes
      (independent_registered_clause_spec
        independent_registered_truth_condition_clause_instances)
      Prop (exists x : State, P x).
Proof.
  intros P H.
  exact (fully_registered_truth_sigma_State
    (independent_registered_clause_spec
      independent_registered_truth_condition_clause_instances)
    P H).
Qed.

Theorem independent_registered_truth_condition_clause_sigma_StateScale_instance :
  forall P : StateScale -> Prop,
    (forall x : StateScale,
      fully_registered_truth_denotes
        (independent_registered_clause_spec
          independent_registered_truth_condition_clause_instances)
        Prop (P x)) ->
    fully_registered_truth_denotes
      (independent_registered_clause_spec
        independent_registered_truth_condition_clause_instances)
      Prop (exists x : StateScale, P x).
Proof.
  intros P H.
  exact (fully_registered_truth_sigma_StateScale
    (independent_registered_clause_spec
      independent_registered_truth_condition_clause_instances)
    P H).
Qed.

Theorem independent_registered_truth_condition_clause_sigma_TransitionT_instance :
  forall P : TransitionT -> Prop,
    (forall x : TransitionT,
      fully_registered_truth_denotes
        (independent_registered_clause_spec
          independent_registered_truth_condition_clause_instances)
        Prop (P x)) ->
    fully_registered_truth_denotes
      (independent_registered_clause_spec
        independent_registered_truth_condition_clause_instances)
      Prop (exists x : TransitionT, P x).
Proof.
  intros P H.
  exact (fully_registered_truth_sigma_TransitionT
    (independent_registered_clause_spec
      independent_registered_truth_condition_clause_instances)
    P H).
Qed.

Theorem independent_registered_truth_condition_clause_repeat_instance :
  forall n : nat, forall body : PropT,
    fully_registered_truth_denotes
      (independent_registered_clause_spec
        independent_registered_truth_condition_clause_instances)
      PropT body ->
    fully_registered_truth_denotes
      (independent_registered_clause_spec
        independent_registered_truth_condition_clause_instances)
      PropT (repeat n body).
Proof.
  intros n body H.
  exact (fully_registered_truth_repeat
    (independent_registered_clause_spec
      independent_registered_truth_condition_clause_instances)
    n body H).
Qed.

Theorem independent_registered_truth_condition_clause_at_T_instance :
  forall marker : Entity, forall body : PropT,
    fully_registered_truth_denotes
      (independent_registered_clause_spec
        independent_registered_truth_condition_clause_instances)
      PropT body ->
    fully_registered_truth_denotes
      (independent_registered_clause_spec
        independent_registered_truth_condition_clause_instances)
      PropT (at_T marker body).
Proof.
  intros marker body H.
  exact (fully_registered_truth_at_T
    (independent_registered_clause_spec
      independent_registered_truth_condition_clause_instances)
    marker body H).
Qed.

Theorem independent_registered_truth_condition_clause_during_T_instance :
  forall marker : Entity, forall body : PropT,
    fully_registered_truth_denotes
      (independent_registered_clause_spec
        independent_registered_truth_condition_clause_instances)
      PropT body ->
    fully_registered_truth_denotes
      (independent_registered_clause_spec
        independent_registered_truth_condition_clause_instances)
      PropT (during_T marker body).
Proof.
  intros marker body H.
  exact (fully_registered_truth_during_T
    (independent_registered_clause_spec
      independent_registered_truth_condition_clause_instances)
    marker body H).
Qed.

Theorem independent_registered_truth_condition_clause_before_T_instance :
  forall marker : Entity, forall body : PropT,
    fully_registered_truth_denotes
      (independent_registered_clause_spec
        independent_registered_truth_condition_clause_instances)
      PropT body ->
    fully_registered_truth_denotes
      (independent_registered_clause_spec
        independent_registered_truth_condition_clause_instances)
      PropT (before_T marker body).
Proof.
  intros marker body H.
  exact (fully_registered_truth_before_T
    (independent_registered_clause_spec
      independent_registered_truth_condition_clause_instances)
    marker body H).
Qed.

Theorem independent_registered_truth_condition_clause_after_T_instance :
  forall marker : Entity, forall body : PropT,
    fully_registered_truth_denotes
      (independent_registered_clause_spec
        independent_registered_truth_condition_clause_instances)
      PropT body ->
    fully_registered_truth_denotes
      (independent_registered_clause_spec
        independent_registered_truth_condition_clause_instances)
      PropT (after_T marker body).
Proof.
  intros marker body H.
  exact (fully_registered_truth_after_T
    (independent_registered_clause_spec
      independent_registered_truth_condition_clause_instances)
    marker body H).
Qed.

Theorem independent_registered_truth_condition_clause_until_T_instance :
  forall marker : Entity, forall body : PropT,
    fully_registered_truth_denotes
      (independent_registered_clause_spec
        independent_registered_truth_condition_clause_instances)
      PropT body ->
    fully_registered_truth_denotes
      (independent_registered_clause_spec
        independent_registered_truth_condition_clause_instances)
      PropT (until_T marker body).
Proof.
  intros marker body H.
  exact (fully_registered_truth_until_T
    (independent_registered_clause_spec
      independent_registered_truth_condition_clause_instances)
    marker body H).
Qed.

Theorem independent_registered_truth_condition_clause_since_T_instance :
  forall marker : Entity, forall body : PropT,
    fully_registered_truth_denotes
      (independent_registered_clause_spec
        independent_registered_truth_condition_clause_instances)
      PropT body ->
    fully_registered_truth_denotes
      (independent_registered_clause_spec
        independent_registered_truth_condition_clause_instances)
      PropT (since_T marker body).
Proof.
  intros marker body H.
  exact (fully_registered_truth_since_T
    (independent_registered_clause_spec
      independent_registered_truth_condition_clause_instances)
    marker body H).
Qed.

Theorem independent_registered_truth_condition_clause_not_T_instance :
  forall body : PropT,
    fully_registered_truth_denotes
      (independent_registered_clause_spec
        independent_registered_truth_condition_clause_instances)
      PropT body ->
    fully_registered_truth_denotes
      (independent_registered_clause_spec
        independent_registered_truth_condition_clause_instances)
      PropT (not_T body).
Proof.
  intros body H.
  exact (fully_registered_truth_not_T
    (independent_registered_clause_spec
      independent_registered_truth_condition_clause_instances)
    body H).
Qed.

Theorem independent_registered_truth_condition_clause_transition_instance :
  forall theme : Entity, forall scale : StateScale,
  forall source : State, forall target : State,
    RegisteredStateTransitionTruth theme scale source target ->
    fully_registered_truth_denotes
      (independent_registered_clause_spec
        independent_registered_truth_condition_clause_instances)
      TransitionT (Transition theme scale source target).
Proof.
  intros theme scale source target H.
  exact (fully_registered_truth_transition
    (independent_registered_clause_spec
      independent_registered_truth_condition_clause_instances)
    theme scale source target H).
Qed.

Theorem independent_registered_truth_condition_clause_cause_instance :
  forall causer : Entity, forall effect : TransitionT,
    fully_registered_truth_denotes
      (independent_registered_clause_spec
        independent_registered_truth_condition_clause_instances)
      TransitionT effect ->
    fully_registered_truth_denotes
      (independent_registered_clause_spec
        independent_registered_truth_condition_clause_instances)
      PropT (Cause causer effect).
Proof.
  intros causer effect H.
  exact (fully_registered_truth_cause
    (independent_registered_clause_spec
      independent_registered_truth_condition_clause_instances)
    causer effect H).
Qed.

Theorem independent_registered_truth_condition_clause_spec_sound :
  forall A : Type, forall term : A,
    fully_registered_truth_denotes
      (independent_registered_clause_spec
        independent_registered_truth_condition_clause_instances) A term ->
    AtomicClosureTruth A term.
Proof.
  intros A term H.
  apply independent_registered_truth_condition_sources_spec_sound.
  exact H.
Qed.

Theorem independent_registered_truth_condition_clause_example_1_atomic_sound : AtomicClosureTruth PropT example_1.
Proof.
  apply independent_registered_truth_condition_clause_spec_sound.
  exact (example_1_concrete_truth_instance
    (independent_registered_truth_condition_examples
      (independent_registered_clause_source
        independent_registered_truth_condition_clause_instances))).
Qed.

Theorem independent_registered_truth_condition_clause_example_2_atomic_sound : AtomicClosureTruth Prop example_2.
Proof.
  apply independent_registered_truth_condition_clause_spec_sound.
  exact (example_2_concrete_truth_instance
    (independent_registered_truth_condition_examples
      (independent_registered_clause_source
        independent_registered_truth_condition_clause_instances))).
Qed.

Theorem independent_registered_truth_condition_clause_example_3_atomic_sound : AtomicClosureTruth PropT example_3.
Proof.
  apply independent_registered_truth_condition_clause_spec_sound.
  exact (example_3_concrete_truth_instance
    (independent_registered_truth_condition_examples
      (independent_registered_clause_source
        independent_registered_truth_condition_clause_instances))).
Qed.

Theorem independent_registered_truth_condition_clause_example_4_atomic_sound : AtomicClosureTruth PropT example_4.
Proof.
  apply independent_registered_truth_condition_clause_spec_sound.
  exact (example_4_concrete_truth_instance
    (independent_registered_truth_condition_examples
      (independent_registered_clause_source
        independent_registered_truth_condition_clause_instances))).
Qed.

Record IndependentRegisteredTruthConditionClauseCoverage : Type := {
  independent_registered_clause_coverage_instances :
      IndependentRegisteredTruthConditionClauseInstances;
  independent_registered_clause_coverage_instances_eq :
      independent_registered_clause_coverage_instances =
        independent_registered_truth_condition_clause_instances;
  independent_registered_clause_coverage_lexical_application :
    forall A : Type, forall term : A,
      RegisteredLexicalApplicationTruth A term ->
      fully_registered_truth_denotes
        (independent_registered_clause_spec
          independent_registered_truth_condition_clause_instances) A term;
  independent_registered_clause_coverage_sigma_Entity :
    forall P : Entity -> Prop,
      (forall x : Entity,
        fully_registered_truth_denotes
          (independent_registered_clause_spec
            independent_registered_truth_condition_clause_instances)
          Prop (P x)) ->
      fully_registered_truth_denotes
        (independent_registered_clause_spec
          independent_registered_truth_condition_clause_instances)
        Prop (exists x : Entity, P x);
  independent_registered_clause_coverage_sigma_Food :
    forall P : Food -> Prop,
      (forall x : Food,
        fully_registered_truth_denotes
          (independent_registered_clause_spec
            independent_registered_truth_condition_clause_instances)
          Prop (P x)) ->
      fully_registered_truth_denotes
        (independent_registered_clause_spec
          independent_registered_truth_condition_clause_instances)
        Prop (exists x : Food, P x);
  independent_registered_clause_coverage_sigma_State :
    forall P : State -> Prop,
      (forall x : State,
        fully_registered_truth_denotes
          (independent_registered_clause_spec
            independent_registered_truth_condition_clause_instances)
          Prop (P x)) ->
      fully_registered_truth_denotes
        (independent_registered_clause_spec
          independent_registered_truth_condition_clause_instances)
        Prop (exists x : State, P x);
  independent_registered_clause_coverage_sigma_StateScale :
    forall P : StateScale -> Prop,
      (forall x : StateScale,
        fully_registered_truth_denotes
          (independent_registered_clause_spec
            independent_registered_truth_condition_clause_instances)
          Prop (P x)) ->
      fully_registered_truth_denotes
        (independent_registered_clause_spec
          independent_registered_truth_condition_clause_instances)
        Prop (exists x : StateScale, P x);
  independent_registered_clause_coverage_sigma_TransitionT :
    forall P : TransitionT -> Prop,
      (forall x : TransitionT,
        fully_registered_truth_denotes
          (independent_registered_clause_spec
            independent_registered_truth_condition_clause_instances)
          Prop (P x)) ->
      fully_registered_truth_denotes
        (independent_registered_clause_spec
          independent_registered_truth_condition_clause_instances)
        Prop (exists x : TransitionT, P x);
  independent_registered_clause_coverage_repeat :
    forall n : nat, forall body : PropT,
      fully_registered_truth_denotes
        (independent_registered_clause_spec
          independent_registered_truth_condition_clause_instances)
        PropT body ->
      fully_registered_truth_denotes
        (independent_registered_clause_spec
          independent_registered_truth_condition_clause_instances)
        PropT (repeat n body);
  independent_registered_clause_coverage_at_T :
    forall marker : Entity, forall body : PropT,
      fully_registered_truth_denotes
        (independent_registered_clause_spec
          independent_registered_truth_condition_clause_instances)
        PropT body ->
      fully_registered_truth_denotes
        (independent_registered_clause_spec
          independent_registered_truth_condition_clause_instances)
        PropT (at_T marker body);
  independent_registered_clause_coverage_during_T :
    forall marker : Entity, forall body : PropT,
      fully_registered_truth_denotes
        (independent_registered_clause_spec
          independent_registered_truth_condition_clause_instances)
        PropT body ->
      fully_registered_truth_denotes
        (independent_registered_clause_spec
          independent_registered_truth_condition_clause_instances)
        PropT (during_T marker body);
  independent_registered_clause_coverage_before_T :
    forall marker : Entity, forall body : PropT,
      fully_registered_truth_denotes
        (independent_registered_clause_spec
          independent_registered_truth_condition_clause_instances)
        PropT body ->
      fully_registered_truth_denotes
        (independent_registered_clause_spec
          independent_registered_truth_condition_clause_instances)
        PropT (before_T marker body);
  independent_registered_clause_coverage_after_T :
    forall marker : Entity, forall body : PropT,
      fully_registered_truth_denotes
        (independent_registered_clause_spec
          independent_registered_truth_condition_clause_instances)
        PropT body ->
      fully_registered_truth_denotes
        (independent_registered_clause_spec
          independent_registered_truth_condition_clause_instances)
        PropT (after_T marker body);
  independent_registered_clause_coverage_until_T :
    forall marker : Entity, forall body : PropT,
      fully_registered_truth_denotes
        (independent_registered_clause_spec
          independent_registered_truth_condition_clause_instances)
        PropT body ->
      fully_registered_truth_denotes
        (independent_registered_clause_spec
          independent_registered_truth_condition_clause_instances)
        PropT (until_T marker body);
  independent_registered_clause_coverage_since_T :
    forall marker : Entity, forall body : PropT,
      fully_registered_truth_denotes
        (independent_registered_clause_spec
          independent_registered_truth_condition_clause_instances)
        PropT body ->
      fully_registered_truth_denotes
        (independent_registered_clause_spec
          independent_registered_truth_condition_clause_instances)
        PropT (since_T marker body);
  independent_registered_clause_coverage_not_T :
    forall body : PropT,
      fully_registered_truth_denotes
        (independent_registered_clause_spec
          independent_registered_truth_condition_clause_instances)
        PropT body ->
      fully_registered_truth_denotes
        (independent_registered_clause_spec
          independent_registered_truth_condition_clause_instances)
        PropT (not_T body);
  independent_registered_clause_coverage_transition :
    forall theme : Entity, forall scale : StateScale,
    forall source : State, forall target : State,
      RegisteredStateTransitionTruth theme scale source target ->
      fully_registered_truth_denotes
        (independent_registered_clause_spec
          independent_registered_truth_condition_clause_instances)
        TransitionT (Transition theme scale source target);
  independent_registered_clause_coverage_cause :
    forall causer : Entity, forall effect : TransitionT,
      fully_registered_truth_denotes
        (independent_registered_clause_spec
          independent_registered_truth_condition_clause_instances)
        TransitionT effect ->
      fully_registered_truth_denotes
        (independent_registered_clause_spec
          independent_registered_truth_condition_clause_instances)
        PropT (Cause causer effect);
  independent_registered_clause_coverage_spec_sound :
    forall A : Type, forall term : A,
      fully_registered_truth_denotes
        (independent_registered_clause_spec
          independent_registered_truth_condition_clause_instances) A term ->
      AtomicClosureTruth A term;
  independent_registered_clause_coverage_example_1 :
      AtomicClosureTruth PropT example_1;
  independent_registered_clause_coverage_example_2 :
      AtomicClosureTruth Prop example_2;
  independent_registered_clause_coverage_example_3 :
      AtomicClosureTruth PropT example_3;
  independent_registered_clause_coverage_example_4 :
      AtomicClosureTruth PropT example_4
}.

Definition independent_registered_truth_condition_clause_coverage :
  IndependentRegisteredTruthConditionClauseCoverage := {|
  independent_registered_clause_coverage_instances := independent_registered_truth_condition_clause_instances;
  independent_registered_clause_coverage_instances_eq := eq_refl;
  independent_registered_clause_coverage_lexical_application := independent_registered_truth_condition_clause_lexical_application_instance;
  independent_registered_clause_coverage_sigma_Entity := independent_registered_truth_condition_clause_sigma_Entity_instance;
  independent_registered_clause_coverage_sigma_Food := independent_registered_truth_condition_clause_sigma_Food_instance;
  independent_registered_clause_coverage_sigma_State := independent_registered_truth_condition_clause_sigma_State_instance;
  independent_registered_clause_coverage_sigma_StateScale := independent_registered_truth_condition_clause_sigma_StateScale_instance;
  independent_registered_clause_coverage_sigma_TransitionT := independent_registered_truth_condition_clause_sigma_TransitionT_instance;
  independent_registered_clause_coverage_repeat := independent_registered_truth_condition_clause_repeat_instance;
  independent_registered_clause_coverage_at_T := independent_registered_truth_condition_clause_at_T_instance;
  independent_registered_clause_coverage_during_T := independent_registered_truth_condition_clause_during_T_instance;
  independent_registered_clause_coverage_before_T := independent_registered_truth_condition_clause_before_T_instance;
  independent_registered_clause_coverage_after_T := independent_registered_truth_condition_clause_after_T_instance;
  independent_registered_clause_coverage_until_T := independent_registered_truth_condition_clause_until_T_instance;
  independent_registered_clause_coverage_since_T := independent_registered_truth_condition_clause_since_T_instance;
  independent_registered_clause_coverage_not_T := independent_registered_truth_condition_clause_not_T_instance;
  independent_registered_clause_coverage_transition := independent_registered_truth_condition_clause_transition_instance;
  independent_registered_clause_coverage_cause := independent_registered_truth_condition_clause_cause_instance;
  independent_registered_clause_coverage_spec_sound := independent_registered_truth_condition_clause_spec_sound;
  independent_registered_clause_coverage_example_1 := independent_registered_truth_condition_clause_example_1_atomic_sound;
  independent_registered_clause_coverage_example_2 := independent_registered_truth_condition_clause_example_2_atomic_sound;
  independent_registered_clause_coverage_example_3 := independent_registered_truth_condition_clause_example_3_atomic_sound;
  independent_registered_clause_coverage_example_4 := independent_registered_truth_condition_clause_example_4_atomic_sound
|}.

Theorem independent_registered_truth_condition_clause_coverage_exists :
  exists C : IndependentRegisteredTruthConditionClauseCoverage,
    C = independent_registered_truth_condition_clause_coverage.
Proof.
  exists independent_registered_truth_condition_clause_coverage.
  reflexivity.
Qed.

Theorem independent_registered_truth_condition_clause_coverage_instances_match :
  independent_registered_clause_coverage_instances
    independent_registered_truth_condition_clause_coverage =
  independent_registered_truth_condition_clause_instances.
Proof.
  exact (independent_registered_clause_coverage_instances_eq
    independent_registered_truth_condition_clause_coverage).
Qed.

Theorem independent_registered_truth_condition_clause_coverage_spec_sound :
  forall A : Type, forall term : A,
    fully_registered_truth_denotes
      (independent_registered_clause_spec
        independent_registered_truth_condition_clause_instances) A term ->
    AtomicClosureTruth A term.
Proof.
  exact (independent_registered_clause_coverage_spec_sound
    independent_registered_truth_condition_clause_coverage).
Qed.

Theorem independent_registered_truth_condition_clause_coverage_example_1_atomic_sound : AtomicClosureTruth PropT example_1.
Proof.
  exact (independent_registered_clause_coverage_example_1
    independent_registered_truth_condition_clause_coverage).
Qed.

Theorem independent_registered_truth_condition_clause_coverage_example_2_atomic_sound : AtomicClosureTruth Prop example_2.
Proof.
  exact (independent_registered_clause_coverage_example_2
    independent_registered_truth_condition_clause_coverage).
Qed.

Theorem independent_registered_truth_condition_clause_coverage_example_3_atomic_sound : AtomicClosureTruth PropT example_3.
Proof.
  exact (independent_registered_clause_coverage_example_3
    independent_registered_truth_condition_clause_coverage).
Qed.

Theorem independent_registered_truth_condition_clause_coverage_example_4_atomic_sound : AtomicClosureTruth PropT example_4.
Proof.
  exact (independent_registered_clause_coverage_example_4
    independent_registered_truth_condition_clause_coverage).
Qed.

Record IndependentRegisteredLexicalTruthConditionInstances : Type := {
  independent_registered_lexical_clause_coverage :
      IndependentRegisteredTruthConditionClauseCoverage;
  independent_registered_lexical_clause_coverage_eq :
      independent_registered_lexical_clause_coverage =
        independent_registered_truth_condition_clause_coverage;
  independent_registered_lexical_application_instance :
    forall A : Type, forall term : A,
      RegisteredLexicalApplicationTruth A term ->
      fully_registered_truth_denotes
        (independent_registered_clause_spec
          independent_registered_truth_condition_clause_instances) A term;
  independent_registered_lexical_spec_sound :
    forall A : Type, forall term : A,
      fully_registered_truth_denotes
        (independent_registered_clause_spec
          independent_registered_truth_condition_clause_instances) A term ->
      AtomicClosureTruth A term
}.

Definition independent_registered_lexical_truth_condition_instances :
  IndependentRegisteredLexicalTruthConditionInstances := {|
  independent_registered_lexical_clause_coverage :=
    independent_registered_truth_condition_clause_coverage;
  independent_registered_lexical_clause_coverage_eq := eq_refl;
  independent_registered_lexical_application_instance :=
    independent_registered_truth_condition_clause_lexical_application_instance;
  independent_registered_lexical_spec_sound :=
    independent_registered_clause_coverage_spec_sound
      independent_registered_truth_condition_clause_coverage
|}.

Theorem independent_registered_lexical_truth_condition_instances_exists :
  exists L : IndependentRegisteredLexicalTruthConditionInstances,
    L = independent_registered_lexical_truth_condition_instances.
Proof.
  exists independent_registered_lexical_truth_condition_instances.
  reflexivity.
Qed.

Theorem independent_registered_lexical_truth_condition_coverage_matches :
  independent_registered_lexical_clause_coverage
    independent_registered_lexical_truth_condition_instances =
  independent_registered_truth_condition_clause_coverage.
Proof.
  exact (independent_registered_lexical_clause_coverage_eq
    independent_registered_lexical_truth_condition_instances).
Qed.

Theorem independent_registered_lexical_truth_condition_application_instance :
  forall A : Type, forall term : A,
    RegisteredLexicalApplicationTruth A term ->
    fully_registered_truth_denotes
      (independent_registered_clause_spec
        independent_registered_truth_condition_clause_instances) A term.
Proof.
  exact (independent_registered_lexical_application_instance
    independent_registered_lexical_truth_condition_instances).
Qed.

Theorem independent_registered_lexical_truth_condition_spec_sound :
  forall A : Type, forall term : A,
    fully_registered_truth_denotes
      (independent_registered_clause_spec
        independent_registered_truth_condition_clause_instances) A term ->
    AtomicClosureTruth A term.
Proof.
  exact (independent_registered_lexical_spec_sound
    independent_registered_lexical_truth_condition_instances).
Qed.

Record IndependentRegisteredTemporalTruthConditionInstances : Type := {
  independent_registered_temporal_clause_coverage :
      IndependentRegisteredTruthConditionClauseCoverage;
  independent_registered_temporal_clause_coverage_eq :
      independent_registered_temporal_clause_coverage =
        independent_registered_truth_condition_clause_coverage;
  independent_registered_temporal_at_T_instance :
    forall marker : Entity, forall body : PropT,
      fully_registered_truth_denotes
        (independent_registered_clause_spec
          independent_registered_truth_condition_clause_instances)
        PropT body ->
      fully_registered_truth_denotes
        (independent_registered_clause_spec
          independent_registered_truth_condition_clause_instances)
        PropT (at_T marker body);
  independent_registered_temporal_during_T_instance :
    forall marker : Entity, forall body : PropT,
      fully_registered_truth_denotes
        (independent_registered_clause_spec
          independent_registered_truth_condition_clause_instances)
        PropT body ->
      fully_registered_truth_denotes
        (independent_registered_clause_spec
          independent_registered_truth_condition_clause_instances)
        PropT (during_T marker body);
  independent_registered_temporal_before_T_instance :
    forall marker : Entity, forall body : PropT,
      fully_registered_truth_denotes
        (independent_registered_clause_spec
          independent_registered_truth_condition_clause_instances)
        PropT body ->
      fully_registered_truth_denotes
        (independent_registered_clause_spec
          independent_registered_truth_condition_clause_instances)
        PropT (before_T marker body);
  independent_registered_temporal_after_T_instance :
    forall marker : Entity, forall body : PropT,
      fully_registered_truth_denotes
        (independent_registered_clause_spec
          independent_registered_truth_condition_clause_instances)
        PropT body ->
      fully_registered_truth_denotes
        (independent_registered_clause_spec
          independent_registered_truth_condition_clause_instances)
        PropT (after_T marker body);
  independent_registered_temporal_until_T_instance :
    forall marker : Entity, forall body : PropT,
      fully_registered_truth_denotes
        (independent_registered_clause_spec
          independent_registered_truth_condition_clause_instances)
        PropT body ->
      fully_registered_truth_denotes
        (independent_registered_clause_spec
          independent_registered_truth_condition_clause_instances)
        PropT (until_T marker body);
  independent_registered_temporal_since_T_instance :
    forall marker : Entity, forall body : PropT,
      fully_registered_truth_denotes
        (independent_registered_clause_spec
          independent_registered_truth_condition_clause_instances)
        PropT body ->
      fully_registered_truth_denotes
        (independent_registered_clause_spec
          independent_registered_truth_condition_clause_instances)
        PropT (since_T marker body);
  independent_registered_temporal_spec_sound :
    forall A : Type, forall term : A,
      fully_registered_truth_denotes
        (independent_registered_clause_spec
          independent_registered_truth_condition_clause_instances) A term ->
      AtomicClosureTruth A term
}.

Definition independent_registered_temporal_truth_condition_instances :
  IndependentRegisteredTemporalTruthConditionInstances := {|
  independent_registered_temporal_clause_coverage :=
    independent_registered_truth_condition_clause_coverage;
  independent_registered_temporal_clause_coverage_eq := eq_refl;
  independent_registered_temporal_at_T_instance := independent_registered_truth_condition_clause_at_T_instance;
  independent_registered_temporal_during_T_instance := independent_registered_truth_condition_clause_during_T_instance;
  independent_registered_temporal_before_T_instance := independent_registered_truth_condition_clause_before_T_instance;
  independent_registered_temporal_after_T_instance := independent_registered_truth_condition_clause_after_T_instance;
  independent_registered_temporal_until_T_instance := independent_registered_truth_condition_clause_until_T_instance;
  independent_registered_temporal_since_T_instance := independent_registered_truth_condition_clause_since_T_instance;
  independent_registered_temporal_spec_sound :=
    independent_registered_clause_coverage_spec_sound
      independent_registered_truth_condition_clause_coverage
|}.

Theorem independent_registered_temporal_truth_condition_instances_exists :
  exists T : IndependentRegisteredTemporalTruthConditionInstances,
    T = independent_registered_temporal_truth_condition_instances.
Proof.
  exists independent_registered_temporal_truth_condition_instances.
  reflexivity.
Qed.

Theorem independent_registered_temporal_truth_condition_coverage_matches :
  independent_registered_temporal_clause_coverage
    independent_registered_temporal_truth_condition_instances =
  independent_registered_truth_condition_clause_coverage.
Proof.
  exact (independent_registered_temporal_clause_coverage_eq
    independent_registered_temporal_truth_condition_instances).
Qed.

Theorem independent_registered_temporal_truth_condition_at_T_instance :
  forall marker : Entity, forall body : PropT,
    fully_registered_truth_denotes
      (independent_registered_clause_spec
        independent_registered_truth_condition_clause_instances)
      PropT body ->
    fully_registered_truth_denotes
      (independent_registered_clause_spec
        independent_registered_truth_condition_clause_instances)
      PropT (at_T marker body).
Proof.
  exact (independent_registered_temporal_at_T_instance
    independent_registered_temporal_truth_condition_instances).
Qed.

Theorem independent_registered_temporal_truth_condition_during_T_instance :
  forall marker : Entity, forall body : PropT,
    fully_registered_truth_denotes
      (independent_registered_clause_spec
        independent_registered_truth_condition_clause_instances)
      PropT body ->
    fully_registered_truth_denotes
      (independent_registered_clause_spec
        independent_registered_truth_condition_clause_instances)
      PropT (during_T marker body).
Proof.
  exact (independent_registered_temporal_during_T_instance
    independent_registered_temporal_truth_condition_instances).
Qed.

Theorem independent_registered_temporal_truth_condition_before_T_instance :
  forall marker : Entity, forall body : PropT,
    fully_registered_truth_denotes
      (independent_registered_clause_spec
        independent_registered_truth_condition_clause_instances)
      PropT body ->
    fully_registered_truth_denotes
      (independent_registered_clause_spec
        independent_registered_truth_condition_clause_instances)
      PropT (before_T marker body).
Proof.
  exact (independent_registered_temporal_before_T_instance
    independent_registered_temporal_truth_condition_instances).
Qed.

Theorem independent_registered_temporal_truth_condition_after_T_instance :
  forall marker : Entity, forall body : PropT,
    fully_registered_truth_denotes
      (independent_registered_clause_spec
        independent_registered_truth_condition_clause_instances)
      PropT body ->
    fully_registered_truth_denotes
      (independent_registered_clause_spec
        independent_registered_truth_condition_clause_instances)
      PropT (after_T marker body).
Proof.
  exact (independent_registered_temporal_after_T_instance
    independent_registered_temporal_truth_condition_instances).
Qed.

Theorem independent_registered_temporal_truth_condition_until_T_instance :
  forall marker : Entity, forall body : PropT,
    fully_registered_truth_denotes
      (independent_registered_clause_spec
        independent_registered_truth_condition_clause_instances)
      PropT body ->
    fully_registered_truth_denotes
      (independent_registered_clause_spec
        independent_registered_truth_condition_clause_instances)
      PropT (until_T marker body).
Proof.
  exact (independent_registered_temporal_until_T_instance
    independent_registered_temporal_truth_condition_instances).
Qed.

Theorem independent_registered_temporal_truth_condition_since_T_instance :
  forall marker : Entity, forall body : PropT,
    fully_registered_truth_denotes
      (independent_registered_clause_spec
        independent_registered_truth_condition_clause_instances)
      PropT body ->
    fully_registered_truth_denotes
      (independent_registered_clause_spec
        independent_registered_truth_condition_clause_instances)
      PropT (since_T marker body).
Proof.
  exact (independent_registered_temporal_since_T_instance
    independent_registered_temporal_truth_condition_instances).
Qed.

Theorem independent_registered_temporal_truth_condition_spec_sound :
  forall A : Type, forall term : A,
    fully_registered_truth_denotes
      (independent_registered_clause_spec
        independent_registered_truth_condition_clause_instances) A term ->
    AtomicClosureTruth A term.
Proof.
  exact (independent_registered_temporal_spec_sound
    independent_registered_temporal_truth_condition_instances).
Qed.

Record IndependentRegisteredSigmaTruthConditionInstances : Type := {
  independent_registered_sigma_clause_coverage :
      IndependentRegisteredTruthConditionClauseCoverage;
  independent_registered_sigma_clause_coverage_eq :
      independent_registered_sigma_clause_coverage =
        independent_registered_truth_condition_clause_coverage;
  independent_registered_sigma_Entity_instance :
    forall P : Entity -> Prop,
      (forall x : Entity,
        fully_registered_truth_denotes
          (independent_registered_clause_spec
            independent_registered_truth_condition_clause_instances)
          Prop (P x)) ->
      fully_registered_truth_denotes
        (independent_registered_clause_spec
          independent_registered_truth_condition_clause_instances)
        Prop (exists x : Entity, P x);
  independent_registered_sigma_Food_instance :
    forall P : Food -> Prop,
      (forall x : Food,
        fully_registered_truth_denotes
          (independent_registered_clause_spec
            independent_registered_truth_condition_clause_instances)
          Prop (P x)) ->
      fully_registered_truth_denotes
        (independent_registered_clause_spec
          independent_registered_truth_condition_clause_instances)
        Prop (exists x : Food, P x);
  independent_registered_sigma_State_instance :
    forall P : State -> Prop,
      (forall x : State,
        fully_registered_truth_denotes
          (independent_registered_clause_spec
            independent_registered_truth_condition_clause_instances)
          Prop (P x)) ->
      fully_registered_truth_denotes
        (independent_registered_clause_spec
          independent_registered_truth_condition_clause_instances)
        Prop (exists x : State, P x);
  independent_registered_sigma_StateScale_instance :
    forall P : StateScale -> Prop,
      (forall x : StateScale,
        fully_registered_truth_denotes
          (independent_registered_clause_spec
            independent_registered_truth_condition_clause_instances)
          Prop (P x)) ->
      fully_registered_truth_denotes
        (independent_registered_clause_spec
          independent_registered_truth_condition_clause_instances)
        Prop (exists x : StateScale, P x);
  independent_registered_sigma_TransitionT_instance :
    forall P : TransitionT -> Prop,
      (forall x : TransitionT,
        fully_registered_truth_denotes
          (independent_registered_clause_spec
            independent_registered_truth_condition_clause_instances)
          Prop (P x)) ->
      fully_registered_truth_denotes
        (independent_registered_clause_spec
          independent_registered_truth_condition_clause_instances)
        Prop (exists x : TransitionT, P x);
  independent_registered_sigma_spec_sound :
    forall A : Type, forall term : A,
      fully_registered_truth_denotes
        (independent_registered_clause_spec
          independent_registered_truth_condition_clause_instances) A term ->
      AtomicClosureTruth A term
}.

Definition independent_registered_sigma_truth_condition_instances :
  IndependentRegisteredSigmaTruthConditionInstances := {|
  independent_registered_sigma_clause_coverage :=
    independent_registered_truth_condition_clause_coverage;
  independent_registered_sigma_clause_coverage_eq := eq_refl;
  independent_registered_sigma_Entity_instance := independent_registered_truth_condition_clause_sigma_Entity_instance;
  independent_registered_sigma_Food_instance := independent_registered_truth_condition_clause_sigma_Food_instance;
  independent_registered_sigma_State_instance := independent_registered_truth_condition_clause_sigma_State_instance;
  independent_registered_sigma_StateScale_instance := independent_registered_truth_condition_clause_sigma_StateScale_instance;
  independent_registered_sigma_TransitionT_instance := independent_registered_truth_condition_clause_sigma_TransitionT_instance;
  independent_registered_sigma_spec_sound :=
    independent_registered_clause_coverage_spec_sound
      independent_registered_truth_condition_clause_coverage
|}.

Theorem independent_registered_sigma_truth_condition_instances_exists :
  exists S : IndependentRegisteredSigmaTruthConditionInstances,
    S = independent_registered_sigma_truth_condition_instances.
Proof.
  exists independent_registered_sigma_truth_condition_instances.
  reflexivity.
Qed.

Theorem independent_registered_sigma_truth_condition_coverage_matches :
  independent_registered_sigma_clause_coverage
    independent_registered_sigma_truth_condition_instances =
  independent_registered_truth_condition_clause_coverage.
Proof.
  exact (independent_registered_sigma_clause_coverage_eq
    independent_registered_sigma_truth_condition_instances).
Qed.

Theorem independent_registered_sigma_truth_condition_sigma_Entity_instance :
  forall P : Entity -> Prop,
    (forall x : Entity,
      fully_registered_truth_denotes
        (independent_registered_clause_spec
          independent_registered_truth_condition_clause_instances)
        Prop (P x)) ->
    fully_registered_truth_denotes
      (independent_registered_clause_spec
        independent_registered_truth_condition_clause_instances)
      Prop (exists x : Entity, P x).
Proof.
  exact (independent_registered_sigma_Entity_instance
    independent_registered_sigma_truth_condition_instances).
Qed.

Theorem independent_registered_sigma_truth_condition_sigma_Food_instance :
  forall P : Food -> Prop,
    (forall x : Food,
      fully_registered_truth_denotes
        (independent_registered_clause_spec
          independent_registered_truth_condition_clause_instances)
        Prop (P x)) ->
    fully_registered_truth_denotes
      (independent_registered_clause_spec
        independent_registered_truth_condition_clause_instances)
      Prop (exists x : Food, P x).
Proof.
  exact (independent_registered_sigma_Food_instance
    independent_registered_sigma_truth_condition_instances).
Qed.

Theorem independent_registered_sigma_truth_condition_sigma_State_instance :
  forall P : State -> Prop,
    (forall x : State,
      fully_registered_truth_denotes
        (independent_registered_clause_spec
          independent_registered_truth_condition_clause_instances)
        Prop (P x)) ->
    fully_registered_truth_denotes
      (independent_registered_clause_spec
        independent_registered_truth_condition_clause_instances)
      Prop (exists x : State, P x).
Proof.
  exact (independent_registered_sigma_State_instance
    independent_registered_sigma_truth_condition_instances).
Qed.

Theorem independent_registered_sigma_truth_condition_sigma_StateScale_instance :
  forall P : StateScale -> Prop,
    (forall x : StateScale,
      fully_registered_truth_denotes
        (independent_registered_clause_spec
          independent_registered_truth_condition_clause_instances)
        Prop (P x)) ->
    fully_registered_truth_denotes
      (independent_registered_clause_spec
        independent_registered_truth_condition_clause_instances)
      Prop (exists x : StateScale, P x).
Proof.
  exact (independent_registered_sigma_StateScale_instance
    independent_registered_sigma_truth_condition_instances).
Qed.

Theorem independent_registered_sigma_truth_condition_sigma_TransitionT_instance :
  forall P : TransitionT -> Prop,
    (forall x : TransitionT,
      fully_registered_truth_denotes
        (independent_registered_clause_spec
          independent_registered_truth_condition_clause_instances)
        Prop (P x)) ->
    fully_registered_truth_denotes
      (independent_registered_clause_spec
        independent_registered_truth_condition_clause_instances)
      Prop (exists x : TransitionT, P x).
Proof.
  exact (independent_registered_sigma_TransitionT_instance
    independent_registered_sigma_truth_condition_instances).
Qed.

Theorem independent_registered_sigma_truth_condition_spec_sound :
  forall A : Type, forall term : A,
    fully_registered_truth_denotes
      (independent_registered_clause_spec
        independent_registered_truth_condition_clause_instances) A term ->
    AtomicClosureTruth A term.
Proof.
  exact (independent_registered_sigma_spec_sound
    independent_registered_sigma_truth_condition_instances).
Qed.

Record IndependentRegisteredRepeatTruthConditionInstances : Type := {
  independent_registered_repeat_clause_coverage :
      IndependentRegisteredTruthConditionClauseCoverage;
  independent_registered_repeat_clause_coverage_eq :
      independent_registered_repeat_clause_coverage =
        independent_registered_truth_condition_clause_coverage;
  independent_registered_repeat_instance :
    forall n : nat, forall body : PropT,
      fully_registered_truth_denotes
        (independent_registered_clause_spec
          independent_registered_truth_condition_clause_instances)
        PropT body ->
      fully_registered_truth_denotes
        (independent_registered_clause_spec
          independent_registered_truth_condition_clause_instances)
        PropT (repeat n body);
  independent_registered_repeat_spec_sound :
    forall A : Type, forall term : A,
      fully_registered_truth_denotes
        (independent_registered_clause_spec
          independent_registered_truth_condition_clause_instances) A term ->
      AtomicClosureTruth A term
}.

Definition independent_registered_repeat_truth_condition_instances :
  IndependentRegisteredRepeatTruthConditionInstances := {|
  independent_registered_repeat_clause_coverage :=
    independent_registered_truth_condition_clause_coverage;
  independent_registered_repeat_clause_coverage_eq := eq_refl;
  independent_registered_repeat_instance :=
    independent_registered_truth_condition_clause_repeat_instance;
  independent_registered_repeat_spec_sound :=
    independent_registered_clause_coverage_spec_sound
      independent_registered_truth_condition_clause_coverage
|}.

Theorem independent_registered_repeat_truth_condition_instances_exists :
  exists R : IndependentRegisteredRepeatTruthConditionInstances,
    R = independent_registered_repeat_truth_condition_instances.
Proof.
  exists independent_registered_repeat_truth_condition_instances.
  reflexivity.
Qed.

Theorem independent_registered_repeat_truth_condition_coverage_matches :
  independent_registered_repeat_clause_coverage
    independent_registered_repeat_truth_condition_instances =
  independent_registered_truth_condition_clause_coverage.
Proof.
  exact (independent_registered_repeat_clause_coverage_eq
    independent_registered_repeat_truth_condition_instances).
Qed.

Theorem independent_registered_repeat_truth_condition_repeat_instance :
  forall n : nat, forall body : PropT,
    fully_registered_truth_denotes
      (independent_registered_clause_spec
        independent_registered_truth_condition_clause_instances)
      PropT body ->
    fully_registered_truth_denotes
      (independent_registered_clause_spec
        independent_registered_truth_condition_clause_instances)
      PropT (repeat n body).
Proof.
  exact (independent_registered_repeat_instance
    independent_registered_repeat_truth_condition_instances).
Qed.

Theorem independent_registered_repeat_truth_condition_spec_sound :
  forall A : Type, forall term : A,
    fully_registered_truth_denotes
      (independent_registered_clause_spec
        independent_registered_truth_condition_clause_instances) A term ->
    AtomicClosureTruth A term.
Proof.
  exact (independent_registered_repeat_spec_sound
    independent_registered_repeat_truth_condition_instances).
Qed.

Record IndependentRegisteredPolarityTruthConditionInstances : Type := {
  independent_registered_polarity_clause_coverage :
      IndependentRegisteredTruthConditionClauseCoverage;
  independent_registered_polarity_clause_coverage_eq :
      independent_registered_polarity_clause_coverage =
        independent_registered_truth_condition_clause_coverage;
  independent_registered_polarity_instance :
    forall body : PropT,
      fully_registered_truth_denotes
        (independent_registered_clause_spec
          independent_registered_truth_condition_clause_instances)
        PropT body ->
      fully_registered_truth_denotes
        (independent_registered_clause_spec
          independent_registered_truth_condition_clause_instances)
        PropT (not_T body);
  independent_registered_polarity_spec_sound :
    forall A : Type, forall term : A,
      fully_registered_truth_denotes
        (independent_registered_clause_spec
          independent_registered_truth_condition_clause_instances) A term ->
      AtomicClosureTruth A term
}.

Definition independent_registered_polarity_truth_condition_instances :
  IndependentRegisteredPolarityTruthConditionInstances := {|
  independent_registered_polarity_clause_coverage :=
    independent_registered_truth_condition_clause_coverage;
  independent_registered_polarity_clause_coverage_eq := eq_refl;
  independent_registered_polarity_instance :=
    independent_registered_truth_condition_clause_not_T_instance;
  independent_registered_polarity_spec_sound :=
    independent_registered_clause_coverage_spec_sound
      independent_registered_truth_condition_clause_coverage
|}.

Theorem independent_registered_polarity_truth_condition_instances_exists :
  exists P : IndependentRegisteredPolarityTruthConditionInstances,
    P = independent_registered_polarity_truth_condition_instances.
Proof.
  exists independent_registered_polarity_truth_condition_instances.
  reflexivity.
Qed.

Theorem independent_registered_polarity_truth_condition_coverage_matches :
  independent_registered_polarity_clause_coverage
    independent_registered_polarity_truth_condition_instances =
  independent_registered_truth_condition_clause_coverage.
Proof.
  exact (independent_registered_polarity_clause_coverage_eq
    independent_registered_polarity_truth_condition_instances).
Qed.

Theorem independent_registered_polarity_truth_condition_not_T_instance :
  forall body : PropT,
    fully_registered_truth_denotes
      (independent_registered_clause_spec
        independent_registered_truth_condition_clause_instances)
      PropT body ->
    fully_registered_truth_denotes
      (independent_registered_clause_spec
        independent_registered_truth_condition_clause_instances)
      PropT (not_T body).
Proof.
  exact (independent_registered_polarity_instance
    independent_registered_polarity_truth_condition_instances).
Qed.

Theorem independent_registered_polarity_truth_condition_spec_sound :
  forall A : Type, forall term : A,
    fully_registered_truth_denotes
      (independent_registered_clause_spec
        independent_registered_truth_condition_clause_instances) A term ->
    AtomicClosureTruth A term.
Proof.
  exact (independent_registered_polarity_spec_sound
    independent_registered_polarity_truth_condition_instances).
Qed.

Record IndependentRegisteredTransitionCauseTruthConditionInstances : Type := {
  independent_registered_transition_cause_clause_coverage :
      IndependentRegisteredTruthConditionClauseCoverage;
  independent_registered_transition_cause_clause_coverage_eq :
      independent_registered_transition_cause_clause_coverage =
        independent_registered_truth_condition_clause_coverage;
  independent_registered_transition_cause_transition_instance :
    forall theme : Entity, forall scale : StateScale,
    forall source : State, forall target : State,
      RegisteredStateTransitionTruth theme scale source target ->
      fully_registered_truth_denotes
        (independent_registered_clause_spec
          independent_registered_truth_condition_clause_instances)
        TransitionT (Transition theme scale source target);
  independent_registered_transition_cause_cause_instance :
    forall causer : Entity, forall effect : TransitionT,
      fully_registered_truth_denotes
        (independent_registered_clause_spec
          independent_registered_truth_condition_clause_instances)
        TransitionT effect ->
      fully_registered_truth_denotes
        (independent_registered_clause_spec
          independent_registered_truth_condition_clause_instances)
        PropT (Cause causer effect);
  independent_registered_transition_cause_spec_sound :
    forall A : Type, forall term : A,
      fully_registered_truth_denotes
        (independent_registered_clause_spec
          independent_registered_truth_condition_clause_instances) A term ->
      AtomicClosureTruth A term
}.

Definition independent_registered_transition_cause_truth_condition_instances :
  IndependentRegisteredTransitionCauseTruthConditionInstances := {|
  independent_registered_transition_cause_clause_coverage :=
    independent_registered_truth_condition_clause_coverage;
  independent_registered_transition_cause_clause_coverage_eq := eq_refl;
  independent_registered_transition_cause_transition_instance :=
    independent_registered_truth_condition_clause_transition_instance;
  independent_registered_transition_cause_cause_instance :=
    independent_registered_truth_condition_clause_cause_instance;
  independent_registered_transition_cause_spec_sound :=
    independent_registered_clause_coverage_spec_sound
      independent_registered_truth_condition_clause_coverage
|}.

Theorem independent_registered_transition_cause_truth_condition_instances_exists :
  exists TC : IndependentRegisteredTransitionCauseTruthConditionInstances,
    TC = independent_registered_transition_cause_truth_condition_instances.
Proof.
  exists independent_registered_transition_cause_truth_condition_instances.
  reflexivity.
Qed.

Theorem independent_registered_transition_cause_truth_condition_coverage_matches :
  independent_registered_transition_cause_clause_coverage
    independent_registered_transition_cause_truth_condition_instances =
  independent_registered_truth_condition_clause_coverage.
Proof.
  exact (independent_registered_transition_cause_clause_coverage_eq
    independent_registered_transition_cause_truth_condition_instances).
Qed.

Theorem independent_registered_transition_cause_truth_condition_transition_instance :
  forall theme : Entity, forall scale : StateScale,
  forall source : State, forall target : State,
    RegisteredStateTransitionTruth theme scale source target ->
    fully_registered_truth_denotes
      (independent_registered_clause_spec
        independent_registered_truth_condition_clause_instances)
      TransitionT (Transition theme scale source target).
Proof.
  exact (independent_registered_transition_cause_transition_instance
    independent_registered_transition_cause_truth_condition_instances).
Qed.

Theorem independent_registered_transition_cause_truth_condition_cause_instance :
  forall causer : Entity, forall effect : TransitionT,
    fully_registered_truth_denotes
      (independent_registered_clause_spec
        independent_registered_truth_condition_clause_instances)
      TransitionT effect ->
    fully_registered_truth_denotes
      (independent_registered_clause_spec
        independent_registered_truth_condition_clause_instances)
      PropT (Cause causer effect).
Proof.
  exact (independent_registered_transition_cause_cause_instance
    independent_registered_transition_cause_truth_condition_instances).
Qed.

Theorem independent_registered_transition_cause_truth_condition_spec_sound :
  forall A : Type, forall term : A,
    fully_registered_truth_denotes
      (independent_registered_clause_spec
        independent_registered_truth_condition_clause_instances) A term ->
    AtomicClosureTruth A term.
Proof.
  exact (independent_registered_transition_cause_spec_sound
    independent_registered_transition_cause_truth_condition_instances).
Qed.

Record IndependentRegisteredTruthConditionInstanceSuite : Type := {
  independent_registered_suite_lexical :
      IndependentRegisteredLexicalTruthConditionInstances;
  independent_registered_suite_temporal :
      IndependentRegisteredTemporalTruthConditionInstances;
  independent_registered_suite_sigma :
      IndependentRegisteredSigmaTruthConditionInstances;
  independent_registered_suite_repeat :
      IndependentRegisteredRepeatTruthConditionInstances;
  independent_registered_suite_polarity :
      IndependentRegisteredPolarityTruthConditionInstances;
  independent_registered_suite_transition_cause :
      IndependentRegisteredTransitionCauseTruthConditionInstances;
  independent_registered_suite_lexical_eq :
      independent_registered_suite_lexical =
        independent_registered_lexical_truth_condition_instances;
  independent_registered_suite_temporal_eq :
      independent_registered_suite_temporal =
        independent_registered_temporal_truth_condition_instances;
  independent_registered_suite_sigma_eq :
      independent_registered_suite_sigma =
        independent_registered_sigma_truth_condition_instances;
  independent_registered_suite_repeat_eq :
      independent_registered_suite_repeat =
        independent_registered_repeat_truth_condition_instances;
  independent_registered_suite_polarity_eq :
      independent_registered_suite_polarity =
        independent_registered_polarity_truth_condition_instances;
  independent_registered_suite_transition_cause_eq :
      independent_registered_suite_transition_cause =
        independent_registered_transition_cause_truth_condition_instances;
  independent_registered_suite_spec_sound :
    forall A : Type, forall term : A,
      fully_registered_truth_denotes
        (independent_registered_clause_spec
          independent_registered_truth_condition_clause_instances) A term ->
      AtomicClosureTruth A term
}.

Definition independent_registered_truth_condition_instance_suite :
  IndependentRegisteredTruthConditionInstanceSuite := {|
  independent_registered_suite_lexical :=
    independent_registered_lexical_truth_condition_instances;
  independent_registered_suite_temporal :=
    independent_registered_temporal_truth_condition_instances;
  independent_registered_suite_sigma :=
    independent_registered_sigma_truth_condition_instances;
  independent_registered_suite_repeat :=
    independent_registered_repeat_truth_condition_instances;
  independent_registered_suite_polarity :=
    independent_registered_polarity_truth_condition_instances;
  independent_registered_suite_transition_cause :=
    independent_registered_transition_cause_truth_condition_instances;
  independent_registered_suite_lexical_eq := eq_refl;
  independent_registered_suite_temporal_eq := eq_refl;
  independent_registered_suite_sigma_eq := eq_refl;
  independent_registered_suite_repeat_eq := eq_refl;
  independent_registered_suite_polarity_eq := eq_refl;
  independent_registered_suite_transition_cause_eq := eq_refl;
  independent_registered_suite_spec_sound :=
    independent_registered_clause_coverage_spec_sound
      independent_registered_truth_condition_clause_coverage
|}.

Theorem independent_registered_truth_condition_instance_suite_exists :
  exists S : IndependentRegisteredTruthConditionInstanceSuite,
    S = independent_registered_truth_condition_instance_suite.
Proof.
  exists independent_registered_truth_condition_instance_suite.
  reflexivity.
Qed.

Theorem independent_registered_truth_condition_instance_suite_lexical_matches :
  independent_registered_suite_lexical
    independent_registered_truth_condition_instance_suite =
  independent_registered_lexical_truth_condition_instances.
Proof.
  exact (independent_registered_suite_lexical_eq
    independent_registered_truth_condition_instance_suite).
Qed.

Theorem independent_registered_truth_condition_instance_suite_temporal_matches :
  independent_registered_suite_temporal
    independent_registered_truth_condition_instance_suite =
  independent_registered_temporal_truth_condition_instances.
Proof.
  exact (independent_registered_suite_temporal_eq
    independent_registered_truth_condition_instance_suite).
Qed.

Theorem independent_registered_truth_condition_instance_suite_sigma_matches :
  independent_registered_suite_sigma
    independent_registered_truth_condition_instance_suite =
  independent_registered_sigma_truth_condition_instances.
Proof.
  exact (independent_registered_suite_sigma_eq
    independent_registered_truth_condition_instance_suite).
Qed.

Theorem independent_registered_truth_condition_instance_suite_repeat_matches :
  independent_registered_suite_repeat
    independent_registered_truth_condition_instance_suite =
  independent_registered_repeat_truth_condition_instances.
Proof.
  exact (independent_registered_suite_repeat_eq
    independent_registered_truth_condition_instance_suite).
Qed.

Theorem independent_registered_truth_condition_instance_suite_polarity_matches :
  independent_registered_suite_polarity
    independent_registered_truth_condition_instance_suite =
  independent_registered_polarity_truth_condition_instances.
Proof.
  exact (independent_registered_suite_polarity_eq
    independent_registered_truth_condition_instance_suite).
Qed.

Theorem independent_registered_truth_condition_instance_suite_transition_cause_matches :
  independent_registered_suite_transition_cause
    independent_registered_truth_condition_instance_suite =
  independent_registered_transition_cause_truth_condition_instances.
Proof.
  exact (independent_registered_suite_transition_cause_eq
    independent_registered_truth_condition_instance_suite).
Qed.

Theorem independent_registered_truth_condition_instance_suite_spec_sound :
  forall A : Type, forall term : A,
    fully_registered_truth_denotes
      (independent_registered_clause_spec
        independent_registered_truth_condition_clause_instances) A term ->
    AtomicClosureTruth A term.
Proof.
  exact (independent_registered_suite_spec_sound
    independent_registered_truth_condition_instance_suite).
Qed.

Record IndependentRegisteredTruthConditionInstanceSuiteExamplePackage : Type := {
  independent_registered_suite_example_suite :
      IndependentRegisteredTruthConditionInstanceSuite;
  independent_registered_suite_example_suite_eq :
      independent_registered_suite_example_suite =
        independent_registered_truth_condition_instance_suite;
  example_1_suite_atomic_sound :
      AtomicClosureTruth PropT example_1;
  example_2_suite_atomic_sound :
      AtomicClosureTruth Prop example_2;
  example_3_suite_atomic_sound :
      AtomicClosureTruth PropT example_3;
  example_4_suite_atomic_sound :
      AtomicClosureTruth PropT example_4
}.

Definition independent_registered_truth_condition_instance_suite_example_package :
  IndependentRegisteredTruthConditionInstanceSuiteExamplePackage := {|
  independent_registered_suite_example_suite :=
    independent_registered_truth_condition_instance_suite;
  independent_registered_suite_example_suite_eq := eq_refl;
  example_1_suite_atomic_sound := independent_registered_truth_condition_clause_coverage_example_1_atomic_sound;
  example_2_suite_atomic_sound := independent_registered_truth_condition_clause_coverage_example_2_atomic_sound;
  example_3_suite_atomic_sound := independent_registered_truth_condition_clause_coverage_example_3_atomic_sound;
  example_4_suite_atomic_sound := independent_registered_truth_condition_clause_coverage_example_4_atomic_sound
|}.

Theorem independent_registered_truth_condition_instance_suite_example_package_exists :
  exists P : IndependentRegisteredTruthConditionInstanceSuiteExamplePackage,
    P = independent_registered_truth_condition_instance_suite_example_package.
Proof.
  exists independent_registered_truth_condition_instance_suite_example_package.
  reflexivity.
Qed.

Theorem independent_registered_truth_condition_instance_suite_example_package_suite_matches :
  independent_registered_suite_example_suite
    independent_registered_truth_condition_instance_suite_example_package =
  independent_registered_truth_condition_instance_suite.
Proof.
  exact (independent_registered_suite_example_suite_eq
    independent_registered_truth_condition_instance_suite_example_package).
Qed.

Theorem independent_registered_truth_condition_instance_suite_example_1_atomic_sound :
  AtomicClosureTruth PropT example_1.
Proof.
  exact (example_1_suite_atomic_sound
    independent_registered_truth_condition_instance_suite_example_package).
Qed.

Theorem independent_registered_truth_condition_instance_suite_example_2_atomic_sound :
  AtomicClosureTruth Prop example_2.
Proof.
  exact (example_2_suite_atomic_sound
    independent_registered_truth_condition_instance_suite_example_package).
Qed.

Theorem independent_registered_truth_condition_instance_suite_example_3_atomic_sound :
  AtomicClosureTruth PropT example_3.
Proof.
  exact (example_3_suite_atomic_sound
    independent_registered_truth_condition_instance_suite_example_package).
Qed.

Theorem independent_registered_truth_condition_instance_suite_example_4_atomic_sound :
  AtomicClosureTruth PropT example_4.
Proof.
  exact (example_4_suite_atomic_sound
    independent_registered_truth_condition_instance_suite_example_package).
Qed.

Theorem example_1_fully_registered_truth_condition_atomic_sound : AtomicClosureTruth PropT example_1.
Proof.
  apply fully_registered_truth_conditions_imply_atomic_closure.
  exact example_1_fully_registered_truth_condition_sound.
Qed.
Theorem example_2_fully_registered_truth_condition_atomic_sound : AtomicClosureTruth Prop example_2.
Proof.
  apply fully_registered_truth_conditions_imply_atomic_closure.
  exact example_2_fully_registered_truth_condition_sound.
Qed.
Theorem example_3_fully_registered_truth_condition_atomic_sound : AtomicClosureTruth PropT example_3.
Proof.
  apply fully_registered_truth_conditions_imply_atomic_closure.
  exact example_3_fully_registered_truth_condition_sound.
Qed.
Theorem example_4_fully_registered_truth_condition_atomic_sound : AtomicClosureTruth PropT example_4.
Proof.
  apply fully_registered_truth_conditions_imply_atomic_closure.
  exact example_4_fully_registered_truth_condition_sound.
Qed.

Record RegisteredExampleTruthInstances : Type := {
  example_1_truth_instance :
      fully_registered_truth_denotes fully_registered_truth_conditions PropT example_1;
  example_2_truth_instance :
      fully_registered_truth_denotes fully_registered_truth_conditions Prop example_2;
  example_3_truth_instance :
      fully_registered_truth_denotes fully_registered_truth_conditions PropT example_3;
  example_4_truth_instance :
      fully_registered_truth_denotes fully_registered_truth_conditions PropT example_4
}.

Definition registered_example_truth_instances : RegisteredExampleTruthInstances := {|
  example_1_truth_instance := example_1_fully_registered_truth_condition_sound;
  example_2_truth_instance := example_2_fully_registered_truth_condition_sound;
  example_3_truth_instance := example_3_fully_registered_truth_condition_sound;
  example_4_truth_instance := example_4_fully_registered_truth_condition_sound
|}.

Theorem registered_example_truth_instances_exists :
  exists I : RegisteredExampleTruthInstances,
    I = registered_example_truth_instances.
Proof.
  exists registered_example_truth_instances. reflexivity.
Qed.

Theorem registered_example_1_truth_instance_atomic_sound : AtomicClosureTruth PropT example_1.
Proof.
  apply fully_registered_truth_conditions_imply_atomic_closure.
  exact (example_1_truth_instance registered_example_truth_instances).
Qed.

Theorem registered_example_2_truth_instance_atomic_sound : AtomicClosureTruth Prop example_2.
Proof.
  apply fully_registered_truth_conditions_imply_atomic_closure.
  exact (example_2_truth_instance registered_example_truth_instances).
Qed.

Theorem registered_example_3_truth_instance_atomic_sound : AtomicClosureTruth PropT example_3.
Proof.
  apply fully_registered_truth_conditions_imply_atomic_closure.
  exact (example_3_truth_instance registered_example_truth_instances).
Qed.

Theorem registered_example_4_truth_instance_atomic_sound : AtomicClosureTruth PropT example_4.
Proof.
  apply fully_registered_truth_conditions_imply_atomic_closure.
  exact (example_4_truth_instance registered_example_truth_instances).
Qed.

Record FiniteRegisteredTruthConditionInstanceLedger : Type := {
  finite_registered_ledger_route : ConcreteRegisteredTruthConditionRoute;
  finite_registered_ledger_route_eq :
      finite_registered_ledger_route = concrete_registered_truth_condition_route;
  finite_registered_ledger_sources : IndependentRegisteredTruthConditionSources;
  finite_registered_ledger_sources_eq :
      finite_registered_ledger_sources = independent_registered_truth_condition_sources;
  finite_registered_ledger_suite : IndependentRegisteredTruthConditionInstanceSuite;
  finite_registered_ledger_suite_eq :
      finite_registered_ledger_suite = independent_registered_truth_condition_instance_suite;
  finite_registered_ledger_suite_examples :
      IndependentRegisteredTruthConditionInstanceSuiteExamplePackage;
  finite_registered_ledger_suite_examples_eq :
      finite_registered_ledger_suite_examples =
        independent_registered_truth_condition_instance_suite_example_package;
  finite_registered_ledger_registered_examples : RegisteredExampleTruthInstances;
  finite_registered_ledger_registered_examples_eq :
      finite_registered_ledger_registered_examples = registered_example_truth_instances;
  finite_registered_ledger_concrete_examples : ConcreteRegisteredExampleTruthInstances;
  finite_registered_ledger_concrete_examples_eq :
      finite_registered_ledger_concrete_examples = concrete_registered_example_truth_instances;
  finite_registered_ledger_kernel_examples : ConcreteRegisteredKernelExampleTruthInstances;
  finite_registered_ledger_kernel_examples_eq :
      finite_registered_ledger_kernel_examples = concrete_registered_kernel_example_truth_instances
}.

Definition finite_registered_truth_condition_instance_ledger :
  FiniteRegisteredTruthConditionInstanceLedger := {|
  finite_registered_ledger_route := concrete_registered_truth_condition_route;
  finite_registered_ledger_route_eq := eq_refl;
  finite_registered_ledger_sources := independent_registered_truth_condition_sources;
  finite_registered_ledger_sources_eq := eq_refl;
  finite_registered_ledger_suite := independent_registered_truth_condition_instance_suite;
  finite_registered_ledger_suite_eq := eq_refl;
  finite_registered_ledger_suite_examples :=
    independent_registered_truth_condition_instance_suite_example_package;
  finite_registered_ledger_suite_examples_eq := eq_refl;
  finite_registered_ledger_registered_examples := registered_example_truth_instances;
  finite_registered_ledger_registered_examples_eq := eq_refl;
  finite_registered_ledger_concrete_examples := concrete_registered_example_truth_instances;
  finite_registered_ledger_concrete_examples_eq := eq_refl;
  finite_registered_ledger_kernel_examples := concrete_registered_kernel_example_truth_instances;
  finite_registered_ledger_kernel_examples_eq := eq_refl
|}.

Theorem finite_registered_truth_condition_instance_ledger_exists :
  exists L : FiniteRegisteredTruthConditionInstanceLedger,
    L = finite_registered_truth_condition_instance_ledger.
Proof.
  exists finite_registered_truth_condition_instance_ledger.
  reflexivity.
Qed.

Theorem finite_registered_truth_condition_instance_ledger_route_matches :
  finite_registered_ledger_route
    finite_registered_truth_condition_instance_ledger =
  concrete_registered_truth_condition_route.
Proof.
  exact (finite_registered_ledger_route_eq
    finite_registered_truth_condition_instance_ledger).
Qed.

Theorem finite_registered_truth_condition_instance_ledger_sources_matches :
  finite_registered_ledger_sources
    finite_registered_truth_condition_instance_ledger =
  independent_registered_truth_condition_sources.
Proof.
  exact (finite_registered_ledger_sources_eq
    finite_registered_truth_condition_instance_ledger).
Qed.

Theorem finite_registered_truth_condition_instance_ledger_suite_matches :
  finite_registered_ledger_suite
    finite_registered_truth_condition_instance_ledger =
  independent_registered_truth_condition_instance_suite.
Proof.
  exact (finite_registered_ledger_suite_eq
    finite_registered_truth_condition_instance_ledger).
Qed.

Theorem finite_registered_truth_condition_instance_ledger_suite_examples_matches :
  finite_registered_ledger_suite_examples
    finite_registered_truth_condition_instance_ledger =
  independent_registered_truth_condition_instance_suite_example_package.
Proof.
  exact (finite_registered_ledger_suite_examples_eq
    finite_registered_truth_condition_instance_ledger).
Qed.

Theorem finite_registered_truth_condition_instance_ledger_registered_examples_matches :
  finite_registered_ledger_registered_examples
    finite_registered_truth_condition_instance_ledger =
  registered_example_truth_instances.
Proof.
  exact (finite_registered_ledger_registered_examples_eq
    finite_registered_truth_condition_instance_ledger).
Qed.

Theorem finite_registered_truth_condition_instance_ledger_concrete_examples_matches :
  finite_registered_ledger_concrete_examples
    finite_registered_truth_condition_instance_ledger =
  concrete_registered_example_truth_instances.
Proof.
  exact (finite_registered_ledger_concrete_examples_eq
    finite_registered_truth_condition_instance_ledger).
Qed.

Theorem finite_registered_truth_condition_instance_ledger_kernel_examples_matches :
  finite_registered_ledger_kernel_examples
    finite_registered_truth_condition_instance_ledger =
  concrete_registered_kernel_example_truth_instances.
Proof.
  exact (finite_registered_ledger_kernel_examples_eq
    finite_registered_truth_condition_instance_ledger).
Qed.

Theorem finite_registered_truth_condition_ledger_example_1_suite_atomic_sound :
  AtomicClosureTruth PropT example_1.
Proof.
  exact (example_1_suite_atomic_sound
    (finite_registered_ledger_suite_examples
      finite_registered_truth_condition_instance_ledger)).
Qed.

Theorem finite_registered_truth_condition_ledger_example_1_registered_atomic_sound :
  AtomicClosureTruth PropT example_1.
Proof.
  apply fully_registered_truth_conditions_imply_atomic_closure.
  exact (example_1_truth_instance
    (finite_registered_ledger_registered_examples
      finite_registered_truth_condition_instance_ledger)).
Qed.

Theorem finite_registered_truth_condition_ledger_example_1_concrete_atomic_sound :
  AtomicClosureTruth PropT example_1.
Proof.
  apply concrete_registered_truth_conditions_imply_atomic_closure.
  exact (example_1_concrete_truth_instance
    (finite_registered_ledger_concrete_examples
      finite_registered_truth_condition_instance_ledger)).
Qed.

Theorem finite_registered_truth_condition_ledger_example_1_kernel_atomic_sound :
  AtomicClosureTruth PropT example_1.
Proof.
  apply concrete_registered_truth_conditions_from_kernel_imply_atomic_closure.
  exact (example_1_kernel_truth_instance
    (finite_registered_ledger_kernel_examples
      finite_registered_truth_condition_instance_ledger)).
Qed.

Theorem finite_registered_truth_condition_ledger_example_2_suite_atomic_sound :
  AtomicClosureTruth Prop example_2.
Proof.
  exact (example_2_suite_atomic_sound
    (finite_registered_ledger_suite_examples
      finite_registered_truth_condition_instance_ledger)).
Qed.

Theorem finite_registered_truth_condition_ledger_example_2_registered_atomic_sound :
  AtomicClosureTruth Prop example_2.
Proof.
  apply fully_registered_truth_conditions_imply_atomic_closure.
  exact (example_2_truth_instance
    (finite_registered_ledger_registered_examples
      finite_registered_truth_condition_instance_ledger)).
Qed.

Theorem finite_registered_truth_condition_ledger_example_2_concrete_atomic_sound :
  AtomicClosureTruth Prop example_2.
Proof.
  apply concrete_registered_truth_conditions_imply_atomic_closure.
  exact (example_2_concrete_truth_instance
    (finite_registered_ledger_concrete_examples
      finite_registered_truth_condition_instance_ledger)).
Qed.

Theorem finite_registered_truth_condition_ledger_example_2_kernel_atomic_sound :
  AtomicClosureTruth Prop example_2.
Proof.
  apply concrete_registered_truth_conditions_from_kernel_imply_atomic_closure.
  exact (example_2_kernel_truth_instance
    (finite_registered_ledger_kernel_examples
      finite_registered_truth_condition_instance_ledger)).
Qed.

Theorem finite_registered_truth_condition_ledger_example_3_suite_atomic_sound :
  AtomicClosureTruth PropT example_3.
Proof.
  exact (example_3_suite_atomic_sound
    (finite_registered_ledger_suite_examples
      finite_registered_truth_condition_instance_ledger)).
Qed.

Theorem finite_registered_truth_condition_ledger_example_3_registered_atomic_sound :
  AtomicClosureTruth PropT example_3.
Proof.
  apply fully_registered_truth_conditions_imply_atomic_closure.
  exact (example_3_truth_instance
    (finite_registered_ledger_registered_examples
      finite_registered_truth_condition_instance_ledger)).
Qed.

Theorem finite_registered_truth_condition_ledger_example_3_concrete_atomic_sound :
  AtomicClosureTruth PropT example_3.
Proof.
  apply concrete_registered_truth_conditions_imply_atomic_closure.
  exact (example_3_concrete_truth_instance
    (finite_registered_ledger_concrete_examples
      finite_registered_truth_condition_instance_ledger)).
Qed.

Theorem finite_registered_truth_condition_ledger_example_3_kernel_atomic_sound :
  AtomicClosureTruth PropT example_3.
Proof.
  apply concrete_registered_truth_conditions_from_kernel_imply_atomic_closure.
  exact (example_3_kernel_truth_instance
    (finite_registered_ledger_kernel_examples
      finite_registered_truth_condition_instance_ledger)).
Qed.

Theorem finite_registered_truth_condition_ledger_example_4_suite_atomic_sound :
  AtomicClosureTruth PropT example_4.
Proof.
  exact (example_4_suite_atomic_sound
    (finite_registered_ledger_suite_examples
      finite_registered_truth_condition_instance_ledger)).
Qed.

Theorem finite_registered_truth_condition_ledger_example_4_registered_atomic_sound :
  AtomicClosureTruth PropT example_4.
Proof.
  apply fully_registered_truth_conditions_imply_atomic_closure.
  exact (example_4_truth_instance
    (finite_registered_ledger_registered_examples
      finite_registered_truth_condition_instance_ledger)).
Qed.

Theorem finite_registered_truth_condition_ledger_example_4_concrete_atomic_sound :
  AtomicClosureTruth PropT example_4.
Proof.
  apply concrete_registered_truth_conditions_imply_atomic_closure.
  exact (example_4_concrete_truth_instance
    (finite_registered_ledger_concrete_examples
      finite_registered_truth_condition_instance_ledger)).
Qed.

Theorem finite_registered_truth_condition_ledger_example_4_kernel_atomic_sound :
  AtomicClosureTruth PropT example_4.
Proof.
  apply concrete_registered_truth_conditions_from_kernel_imply_atomic_closure.
  exact (example_4_kernel_truth_instance
    (finite_registered_ledger_kernel_examples
      finite_registered_truth_condition_instance_ledger)).
Qed.

Record FiniteRegisteredTruthConditionCompletionCertificate : Type := {
  finite_registered_completion_ledger : FiniteRegisteredTruthConditionInstanceLedger;
  finite_registered_completion_ledger_eq :
      finite_registered_completion_ledger = finite_registered_truth_condition_instance_ledger;
  finite_registered_completion_registered_sound :
      forall A : Type, forall term : A,
      fully_registered_truth_denotes fully_registered_truth_conditions A term ->
      AtomicClosureTruth A term;
  finite_registered_completion_direct_sound :
      forall A : Type, forall term : A,
      fully_registered_truth_denotes
        (concrete_registered_route_direct_spec
          (finite_registered_ledger_route finite_registered_completion_ledger))
        A term ->
      AtomicClosureTruth A term;
  finite_registered_completion_evidence_sound :
      forall A : Type, forall term : A,
      fully_registered_truth_denotes
        (concrete_registered_route_evidence_spec
          (finite_registered_ledger_route finite_registered_completion_ledger))
        A term ->
      AtomicClosureTruth A term;
  finite_registered_completion_kernel_sound :
      forall A : Type, forall term : A,
      fully_registered_truth_denotes
        (concrete_registered_route_kernel_spec
          (finite_registered_ledger_route finite_registered_completion_ledger))
        A term ->
      AtomicClosureTruth A term;
  finite_registered_completion_source_sound :
      forall A : Type, forall term : A,
      fully_registered_truth_denotes
        (independent_registered_truth_condition_spec
          (finite_registered_ledger_sources finite_registered_completion_ledger))
        A term ->
      AtomicClosureTruth A term;
  finite_registered_completion_suite_sound :
      forall A : Type, forall term : A,
      fully_registered_truth_denotes
        (independent_registered_clause_spec
          independent_registered_truth_condition_clause_instances) A term ->
      AtomicClosureTruth A term
}.

Definition finite_registered_truth_condition_completion_certificate :
  FiniteRegisteredTruthConditionCompletionCertificate := {|
  finite_registered_completion_ledger := finite_registered_truth_condition_instance_ledger;
  finite_registered_completion_ledger_eq := eq_refl;
  finite_registered_completion_registered_sound :=
    fun A term H =>
      fully_registered_truth_conditions_imply_atomic_closure A term H;
  finite_registered_completion_direct_sound :=
    fun A term H =>
      concrete_registered_truth_condition_route_direct_spec_sound A term H;
  finite_registered_completion_evidence_sound :=
    fun A term H =>
      concrete_registered_truth_condition_route_evidence_spec_sound A term H;
  finite_registered_completion_kernel_sound :=
    fun A term H =>
      concrete_registered_truth_condition_route_kernel_spec_sound A term H;
  finite_registered_completion_source_sound :=
    fun A term H =>
      independent_registered_truth_condition_sources_spec_sound A term H;
  finite_registered_completion_suite_sound :=
    fun A term H =>
      independent_registered_suite_spec_sound
        (finite_registered_ledger_suite
          finite_registered_truth_condition_instance_ledger) A term H
|}.

Theorem finite_registered_truth_condition_completion_certificate_exists :
  exists C : FiniteRegisteredTruthConditionCompletionCertificate,
    C = finite_registered_truth_condition_completion_certificate.
Proof.
  exists finite_registered_truth_condition_completion_certificate.
  reflexivity.
Qed.

Theorem finite_registered_truth_condition_completion_ledger_matches :
  finite_registered_completion_ledger
    finite_registered_truth_condition_completion_certificate =
  finite_registered_truth_condition_instance_ledger.
Proof.
  exact (finite_registered_completion_ledger_eq
    finite_registered_truth_condition_completion_certificate).
Qed.

Theorem finite_registered_truth_condition_completion_registered_spec_sound :
  forall A : Type, forall term : A,
    fully_registered_truth_denotes fully_registered_truth_conditions A term ->
    AtomicClosureTruth A term.
Proof.
  intros A term H.
  exact (finite_registered_completion_registered_sound
    finite_registered_truth_condition_completion_certificate A term H).
Qed.

Theorem finite_registered_truth_condition_completion_direct_spec_sound :
  forall A : Type, forall term : A,
    fully_registered_truth_denotes
          (concrete_registered_route_direct_spec
            (finite_registered_ledger_route
              (finite_registered_completion_ledger
                finite_registered_truth_condition_completion_certificate)))
          A term ->
    AtomicClosureTruth A term.
Proof.
  intros A term H.
  exact (finite_registered_completion_direct_sound
    finite_registered_truth_condition_completion_certificate A term H).
Qed.

Theorem finite_registered_truth_condition_completion_evidence_spec_sound :
  forall A : Type, forall term : A,
    fully_registered_truth_denotes
          (concrete_registered_route_evidence_spec
            (finite_registered_ledger_route
              (finite_registered_completion_ledger
                finite_registered_truth_condition_completion_certificate)))
          A term ->
    AtomicClosureTruth A term.
Proof.
  intros A term H.
  exact (finite_registered_completion_evidence_sound
    finite_registered_truth_condition_completion_certificate A term H).
Qed.

Theorem finite_registered_truth_condition_completion_kernel_spec_sound :
  forall A : Type, forall term : A,
    fully_registered_truth_denotes
          (concrete_registered_route_kernel_spec
            (finite_registered_ledger_route
              (finite_registered_completion_ledger
                finite_registered_truth_condition_completion_certificate)))
          A term ->
    AtomicClosureTruth A term.
Proof.
  intros A term H.
  exact (finite_registered_completion_kernel_sound
    finite_registered_truth_condition_completion_certificate A term H).
Qed.

Theorem finite_registered_truth_condition_completion_source_spec_sound :
  forall A : Type, forall term : A,
    fully_registered_truth_denotes
          (independent_registered_truth_condition_spec
            (finite_registered_ledger_sources
              (finite_registered_completion_ledger
                finite_registered_truth_condition_completion_certificate)))
          A term ->
    AtomicClosureTruth A term.
Proof.
  intros A term H.
  exact (finite_registered_completion_source_sound
    finite_registered_truth_condition_completion_certificate A term H).
Qed.

Theorem finite_registered_truth_condition_completion_suite_spec_sound :
  forall A : Type, forall term : A,
    fully_registered_truth_denotes
          (independent_registered_clause_spec
            independent_registered_truth_condition_clause_instances)
          A term ->
    AtomicClosureTruth A term.
Proof.
  intros A term H.
  exact (finite_registered_completion_suite_sound
    finite_registered_truth_condition_completion_certificate A term H).
Qed.

Theorem finite_registered_truth_condition_completion_example_1_registered_atomic_sound :
  AtomicClosureTruth PropT example_1.
Proof.
  apply finite_registered_truth_condition_completion_registered_spec_sound.
  exact (example_1_truth_instance
    (finite_registered_ledger_registered_examples
      (finite_registered_completion_ledger
        finite_registered_truth_condition_completion_certificate))).
Qed.

Theorem finite_registered_truth_condition_completion_example_1_direct_atomic_sound :
  AtomicClosureTruth PropT example_1.
Proof.
  apply finite_registered_truth_condition_completion_direct_spec_sound.
  exact (example_1_concrete_truth_instance
    (concrete_registered_route_direct_examples
      (finite_registered_ledger_route
        (finite_registered_completion_ledger
          finite_registered_truth_condition_completion_certificate)))).
Qed.

Theorem finite_registered_truth_condition_completion_example_1_evidence_atomic_sound :
  AtomicClosureTruth PropT example_1.
Proof.
  apply finite_registered_truth_condition_completion_evidence_spec_sound.
  exact (example_1_evidence_backed_truth_instance
    (concrete_registered_route_evidence_examples
      (finite_registered_ledger_route
        (finite_registered_completion_ledger
          finite_registered_truth_condition_completion_certificate)))).
Qed.

Theorem finite_registered_truth_condition_completion_example_1_kernel_atomic_sound :
  AtomicClosureTruth PropT example_1.
Proof.
  apply finite_registered_truth_condition_completion_kernel_spec_sound.
  exact (example_1_kernel_truth_instance
    (concrete_registered_route_kernel_examples
      (finite_registered_ledger_route
        (finite_registered_completion_ledger
          finite_registered_truth_condition_completion_certificate)))).
Qed.

Theorem finite_registered_truth_condition_completion_example_1_source_atomic_sound :
  AtomicClosureTruth PropT example_1.
Proof.
  apply finite_registered_truth_condition_completion_source_spec_sound.
  exact (example_1_concrete_truth_instance
    (independent_registered_truth_condition_examples
      (finite_registered_ledger_sources
        (finite_registered_completion_ledger
          finite_registered_truth_condition_completion_certificate)))).
Qed.

Theorem finite_registered_truth_condition_completion_example_1_suite_atomic_sound :
  AtomicClosureTruth PropT example_1.
Proof.
  exact (example_1_suite_atomic_sound
    (finite_registered_ledger_suite_examples
      (finite_registered_completion_ledger
        finite_registered_truth_condition_completion_certificate))).
Qed.

Theorem finite_registered_truth_condition_completion_example_2_registered_atomic_sound :
  AtomicClosureTruth Prop example_2.
Proof.
  apply finite_registered_truth_condition_completion_registered_spec_sound.
  exact (example_2_truth_instance
    (finite_registered_ledger_registered_examples
      (finite_registered_completion_ledger
        finite_registered_truth_condition_completion_certificate))).
Qed.

Theorem finite_registered_truth_condition_completion_example_2_direct_atomic_sound :
  AtomicClosureTruth Prop example_2.
Proof.
  apply finite_registered_truth_condition_completion_direct_spec_sound.
  exact (example_2_concrete_truth_instance
    (concrete_registered_route_direct_examples
      (finite_registered_ledger_route
        (finite_registered_completion_ledger
          finite_registered_truth_condition_completion_certificate)))).
Qed.

Theorem finite_registered_truth_condition_completion_example_2_evidence_atomic_sound :
  AtomicClosureTruth Prop example_2.
Proof.
  apply finite_registered_truth_condition_completion_evidence_spec_sound.
  exact (example_2_evidence_backed_truth_instance
    (concrete_registered_route_evidence_examples
      (finite_registered_ledger_route
        (finite_registered_completion_ledger
          finite_registered_truth_condition_completion_certificate)))).
Qed.

Theorem finite_registered_truth_condition_completion_example_2_kernel_atomic_sound :
  AtomicClosureTruth Prop example_2.
Proof.
  apply finite_registered_truth_condition_completion_kernel_spec_sound.
  exact (example_2_kernel_truth_instance
    (concrete_registered_route_kernel_examples
      (finite_registered_ledger_route
        (finite_registered_completion_ledger
          finite_registered_truth_condition_completion_certificate)))).
Qed.

Theorem finite_registered_truth_condition_completion_example_2_source_atomic_sound :
  AtomicClosureTruth Prop example_2.
Proof.
  apply finite_registered_truth_condition_completion_source_spec_sound.
  exact (example_2_concrete_truth_instance
    (independent_registered_truth_condition_examples
      (finite_registered_ledger_sources
        (finite_registered_completion_ledger
          finite_registered_truth_condition_completion_certificate)))).
Qed.

Theorem finite_registered_truth_condition_completion_example_2_suite_atomic_sound :
  AtomicClosureTruth Prop example_2.
Proof.
  exact (example_2_suite_atomic_sound
    (finite_registered_ledger_suite_examples
      (finite_registered_completion_ledger
        finite_registered_truth_condition_completion_certificate))).
Qed.

Theorem finite_registered_truth_condition_completion_example_3_registered_atomic_sound :
  AtomicClosureTruth PropT example_3.
Proof.
  apply finite_registered_truth_condition_completion_registered_spec_sound.
  exact (example_3_truth_instance
    (finite_registered_ledger_registered_examples
      (finite_registered_completion_ledger
        finite_registered_truth_condition_completion_certificate))).
Qed.

Theorem finite_registered_truth_condition_completion_example_3_direct_atomic_sound :
  AtomicClosureTruth PropT example_3.
Proof.
  apply finite_registered_truth_condition_completion_direct_spec_sound.
  exact (example_3_concrete_truth_instance
    (concrete_registered_route_direct_examples
      (finite_registered_ledger_route
        (finite_registered_completion_ledger
          finite_registered_truth_condition_completion_certificate)))).
Qed.

Theorem finite_registered_truth_condition_completion_example_3_evidence_atomic_sound :
  AtomicClosureTruth PropT example_3.
Proof.
  apply finite_registered_truth_condition_completion_evidence_spec_sound.
  exact (example_3_evidence_backed_truth_instance
    (concrete_registered_route_evidence_examples
      (finite_registered_ledger_route
        (finite_registered_completion_ledger
          finite_registered_truth_condition_completion_certificate)))).
Qed.

Theorem finite_registered_truth_condition_completion_example_3_kernel_atomic_sound :
  AtomicClosureTruth PropT example_3.
Proof.
  apply finite_registered_truth_condition_completion_kernel_spec_sound.
  exact (example_3_kernel_truth_instance
    (concrete_registered_route_kernel_examples
      (finite_registered_ledger_route
        (finite_registered_completion_ledger
          finite_registered_truth_condition_completion_certificate)))).
Qed.

Theorem finite_registered_truth_condition_completion_example_3_source_atomic_sound :
  AtomicClosureTruth PropT example_3.
Proof.
  apply finite_registered_truth_condition_completion_source_spec_sound.
  exact (example_3_concrete_truth_instance
    (independent_registered_truth_condition_examples
      (finite_registered_ledger_sources
        (finite_registered_completion_ledger
          finite_registered_truth_condition_completion_certificate)))).
Qed.

Theorem finite_registered_truth_condition_completion_example_3_suite_atomic_sound :
  AtomicClosureTruth PropT example_3.
Proof.
  exact (example_3_suite_atomic_sound
    (finite_registered_ledger_suite_examples
      (finite_registered_completion_ledger
        finite_registered_truth_condition_completion_certificate))).
Qed.

Theorem finite_registered_truth_condition_completion_example_4_registered_atomic_sound :
  AtomicClosureTruth PropT example_4.
Proof.
  apply finite_registered_truth_condition_completion_registered_spec_sound.
  exact (example_4_truth_instance
    (finite_registered_ledger_registered_examples
      (finite_registered_completion_ledger
        finite_registered_truth_condition_completion_certificate))).
Qed.

Theorem finite_registered_truth_condition_completion_example_4_direct_atomic_sound :
  AtomicClosureTruth PropT example_4.
Proof.
  apply finite_registered_truth_condition_completion_direct_spec_sound.
  exact (example_4_concrete_truth_instance
    (concrete_registered_route_direct_examples
      (finite_registered_ledger_route
        (finite_registered_completion_ledger
          finite_registered_truth_condition_completion_certificate)))).
Qed.

Theorem finite_registered_truth_condition_completion_example_4_evidence_atomic_sound :
  AtomicClosureTruth PropT example_4.
Proof.
  apply finite_registered_truth_condition_completion_evidence_spec_sound.
  exact (example_4_evidence_backed_truth_instance
    (concrete_registered_route_evidence_examples
      (finite_registered_ledger_route
        (finite_registered_completion_ledger
          finite_registered_truth_condition_completion_certificate)))).
Qed.

Theorem finite_registered_truth_condition_completion_example_4_kernel_atomic_sound :
  AtomicClosureTruth PropT example_4.
Proof.
  apply finite_registered_truth_condition_completion_kernel_spec_sound.
  exact (example_4_kernel_truth_instance
    (concrete_registered_route_kernel_examples
      (finite_registered_ledger_route
        (finite_registered_completion_ledger
          finite_registered_truth_condition_completion_certificate)))).
Qed.

Theorem finite_registered_truth_condition_completion_example_4_source_atomic_sound :
  AtomicClosureTruth PropT example_4.
Proof.
  apply finite_registered_truth_condition_completion_source_spec_sound.
  exact (example_4_concrete_truth_instance
    (independent_registered_truth_condition_examples
      (finite_registered_ledger_sources
        (finite_registered_completion_ledger
          finite_registered_truth_condition_completion_certificate)))).
Qed.

Theorem finite_registered_truth_condition_completion_example_4_suite_atomic_sound :
  AtomicClosureTruth PropT example_4.
Proof.
  exact (example_4_suite_atomic_sound
    (finite_registered_ledger_suite_examples
      (finite_registered_completion_ledger
        finite_registered_truth_condition_completion_certificate))).
Qed.

Record FiniteRegisteredTruthConditionComponentCoverageCertificate : Type := {
  finite_registered_component_completion : FiniteRegisteredTruthConditionCompletionCertificate;
  finite_registered_component_completion_eq :
      finite_registered_component_completion = finite_registered_truth_condition_completion_certificate;
  finite_registered_component_lexical : IndependentRegisteredLexicalTruthConditionInstances;
  finite_registered_component_lexical_eq :
      finite_registered_component_lexical = independent_registered_lexical_truth_condition_instances;
  finite_registered_component_lexical_sound :
      forall A : Type, forall term : A,
      fully_registered_truth_denotes
        (independent_registered_clause_spec
          independent_registered_truth_condition_clause_instances)
        A term ->
      AtomicClosureTruth A term;
  finite_registered_component_temporal : IndependentRegisteredTemporalTruthConditionInstances;
  finite_registered_component_temporal_eq :
      finite_registered_component_temporal = independent_registered_temporal_truth_condition_instances;
  finite_registered_component_temporal_sound :
      forall A : Type, forall term : A,
      fully_registered_truth_denotes
        (independent_registered_clause_spec
          independent_registered_truth_condition_clause_instances)
        A term ->
      AtomicClosureTruth A term;
  finite_registered_component_sigma : IndependentRegisteredSigmaTruthConditionInstances;
  finite_registered_component_sigma_eq :
      finite_registered_component_sigma = independent_registered_sigma_truth_condition_instances;
  finite_registered_component_sigma_sound :
      forall A : Type, forall term : A,
      fully_registered_truth_denotes
        (independent_registered_clause_spec
          independent_registered_truth_condition_clause_instances)
        A term ->
      AtomicClosureTruth A term;
  finite_registered_component_repeat : IndependentRegisteredRepeatTruthConditionInstances;
  finite_registered_component_repeat_eq :
      finite_registered_component_repeat = independent_registered_repeat_truth_condition_instances;
  finite_registered_component_repeat_sound :
      forall A : Type, forall term : A,
      fully_registered_truth_denotes
        (independent_registered_clause_spec
          independent_registered_truth_condition_clause_instances)
        A term ->
      AtomicClosureTruth A term;
  finite_registered_component_polarity : IndependentRegisteredPolarityTruthConditionInstances;
  finite_registered_component_polarity_eq :
      finite_registered_component_polarity = independent_registered_polarity_truth_condition_instances;
  finite_registered_component_polarity_sound :
      forall A : Type, forall term : A,
      fully_registered_truth_denotes
        (independent_registered_clause_spec
          independent_registered_truth_condition_clause_instances)
        A term ->
      AtomicClosureTruth A term;
  finite_registered_component_transition_cause : IndependentRegisteredTransitionCauseTruthConditionInstances;
  finite_registered_component_transition_cause_eq :
      finite_registered_component_transition_cause = independent_registered_transition_cause_truth_condition_instances;
  finite_registered_component_transition_cause_sound :
      forall A : Type, forall term : A,
      fully_registered_truth_denotes
        (independent_registered_clause_spec
          independent_registered_truth_condition_clause_instances)
        A term ->
      AtomicClosureTruth A term;
  finite_registered_component_suite : IndependentRegisteredTruthConditionInstanceSuite;
  finite_registered_component_suite_eq :
      finite_registered_component_suite = independent_registered_truth_condition_instance_suite;
  finite_registered_component_suite_sound :
      forall A : Type, forall term : A,
      fully_registered_truth_denotes
        (independent_registered_clause_spec
          independent_registered_truth_condition_clause_instances)
        A term ->
      AtomicClosureTruth A term
}.

Definition finite_registered_truth_condition_component_coverage_certificate :
  FiniteRegisteredTruthConditionComponentCoverageCertificate := {|
  finite_registered_component_completion := finite_registered_truth_condition_completion_certificate;
  finite_registered_component_completion_eq := eq_refl;
  finite_registered_component_lexical := independent_registered_lexical_truth_condition_instances;
  finite_registered_component_lexical_eq := eq_refl;
  finite_registered_component_lexical_sound := independent_registered_lexical_truth_condition_spec_sound;
  finite_registered_component_temporal := independent_registered_temporal_truth_condition_instances;
  finite_registered_component_temporal_eq := eq_refl;
  finite_registered_component_temporal_sound := independent_registered_temporal_truth_condition_spec_sound;
  finite_registered_component_sigma := independent_registered_sigma_truth_condition_instances;
  finite_registered_component_sigma_eq := eq_refl;
  finite_registered_component_sigma_sound := independent_registered_sigma_truth_condition_spec_sound;
  finite_registered_component_repeat := independent_registered_repeat_truth_condition_instances;
  finite_registered_component_repeat_eq := eq_refl;
  finite_registered_component_repeat_sound := independent_registered_repeat_truth_condition_spec_sound;
  finite_registered_component_polarity := independent_registered_polarity_truth_condition_instances;
  finite_registered_component_polarity_eq := eq_refl;
  finite_registered_component_polarity_sound := independent_registered_polarity_truth_condition_spec_sound;
  finite_registered_component_transition_cause := independent_registered_transition_cause_truth_condition_instances;
  finite_registered_component_transition_cause_eq := eq_refl;
  finite_registered_component_transition_cause_sound := independent_registered_transition_cause_truth_condition_spec_sound;
  finite_registered_component_suite := independent_registered_truth_condition_instance_suite;
  finite_registered_component_suite_eq := eq_refl;
  finite_registered_component_suite_sound := independent_registered_truth_condition_instance_suite_spec_sound
|}.

Theorem finite_registered_truth_condition_component_coverage_certificate_exists :
  exists C : FiniteRegisteredTruthConditionComponentCoverageCertificate,
    C = finite_registered_truth_condition_component_coverage_certificate.
Proof.
  exists finite_registered_truth_condition_component_coverage_certificate.
  reflexivity.
Qed.

Theorem finite_registered_truth_condition_component_completion_matches :
  finite_registered_component_completion
    finite_registered_truth_condition_component_coverage_certificate =
  finite_registered_truth_condition_completion_certificate.
Proof.
  exact (finite_registered_component_completion_eq
    finite_registered_truth_condition_component_coverage_certificate).
Qed.

Theorem finite_registered_truth_condition_component_lexical_matches :
  finite_registered_component_lexical
    finite_registered_truth_condition_component_coverage_certificate =
  independent_registered_lexical_truth_condition_instances.
Proof.
  exact (finite_registered_component_lexical_eq
    finite_registered_truth_condition_component_coverage_certificate).
Qed.

Theorem finite_registered_truth_condition_component_temporal_matches :
  finite_registered_component_temporal
    finite_registered_truth_condition_component_coverage_certificate =
  independent_registered_temporal_truth_condition_instances.
Proof.
  exact (finite_registered_component_temporal_eq
    finite_registered_truth_condition_component_coverage_certificate).
Qed.

Theorem finite_registered_truth_condition_component_sigma_matches :
  finite_registered_component_sigma
    finite_registered_truth_condition_component_coverage_certificate =
  independent_registered_sigma_truth_condition_instances.
Proof.
  exact (finite_registered_component_sigma_eq
    finite_registered_truth_condition_component_coverage_certificate).
Qed.

Theorem finite_registered_truth_condition_component_repeat_matches :
  finite_registered_component_repeat
    finite_registered_truth_condition_component_coverage_certificate =
  independent_registered_repeat_truth_condition_instances.
Proof.
  exact (finite_registered_component_repeat_eq
    finite_registered_truth_condition_component_coverage_certificate).
Qed.

Theorem finite_registered_truth_condition_component_polarity_matches :
  finite_registered_component_polarity
    finite_registered_truth_condition_component_coverage_certificate =
  independent_registered_polarity_truth_condition_instances.
Proof.
  exact (finite_registered_component_polarity_eq
    finite_registered_truth_condition_component_coverage_certificate).
Qed.

Theorem finite_registered_truth_condition_component_transition_cause_matches :
  finite_registered_component_transition_cause
    finite_registered_truth_condition_component_coverage_certificate =
  independent_registered_transition_cause_truth_condition_instances.
Proof.
  exact (finite_registered_component_transition_cause_eq
    finite_registered_truth_condition_component_coverage_certificate).
Qed.

Theorem finite_registered_truth_condition_component_suite_matches :
  finite_registered_component_suite
    finite_registered_truth_condition_component_coverage_certificate =
  independent_registered_truth_condition_instance_suite.
Proof.
  exact (finite_registered_component_suite_eq
    finite_registered_truth_condition_component_coverage_certificate).
Qed.

Theorem finite_registered_truth_condition_component_lexical_spec_sound :
  forall A : Type, forall term : A,
    fully_registered_truth_denotes
      (independent_registered_clause_spec
        independent_registered_truth_condition_clause_instances)
      A term ->
    AtomicClosureTruth A term.
Proof.
  exact (finite_registered_component_lexical_sound
    finite_registered_truth_condition_component_coverage_certificate).
Qed.

Theorem finite_registered_truth_condition_component_temporal_spec_sound :
  forall A : Type, forall term : A,
    fully_registered_truth_denotes
      (independent_registered_clause_spec
        independent_registered_truth_condition_clause_instances)
      A term ->
    AtomicClosureTruth A term.
Proof.
  exact (finite_registered_component_temporal_sound
    finite_registered_truth_condition_component_coverage_certificate).
Qed.

Theorem finite_registered_truth_condition_component_sigma_spec_sound :
  forall A : Type, forall term : A,
    fully_registered_truth_denotes
      (independent_registered_clause_spec
        independent_registered_truth_condition_clause_instances)
      A term ->
    AtomicClosureTruth A term.
Proof.
  exact (finite_registered_component_sigma_sound
    finite_registered_truth_condition_component_coverage_certificate).
Qed.

Theorem finite_registered_truth_condition_component_repeat_spec_sound :
  forall A : Type, forall term : A,
    fully_registered_truth_denotes
      (independent_registered_clause_spec
        independent_registered_truth_condition_clause_instances)
      A term ->
    AtomicClosureTruth A term.
Proof.
  exact (finite_registered_component_repeat_sound
    finite_registered_truth_condition_component_coverage_certificate).
Qed.

Theorem finite_registered_truth_condition_component_polarity_spec_sound :
  forall A : Type, forall term : A,
    fully_registered_truth_denotes
      (independent_registered_clause_spec
        independent_registered_truth_condition_clause_instances)
      A term ->
    AtomicClosureTruth A term.
Proof.
  exact (finite_registered_component_polarity_sound
    finite_registered_truth_condition_component_coverage_certificate).
Qed.

Theorem finite_registered_truth_condition_component_transition_cause_spec_sound :
  forall A : Type, forall term : A,
    fully_registered_truth_denotes
      (independent_registered_clause_spec
        independent_registered_truth_condition_clause_instances)
      A term ->
    AtomicClosureTruth A term.
Proof.
  exact (finite_registered_component_transition_cause_sound
    finite_registered_truth_condition_component_coverage_certificate).
Qed.

Theorem finite_registered_truth_condition_component_suite_spec_sound :
  forall A : Type, forall term : A,
    fully_registered_truth_denotes
      (independent_registered_clause_spec
        independent_registered_truth_condition_clause_instances)
      A term ->
    AtomicClosureTruth A term.
Proof.
  exact (finite_registered_component_suite_sound
    finite_registered_truth_condition_component_coverage_certificate).
Qed.

Theorem finite_registered_truth_condition_component_coverage_example_1_atomic_sound :
  AtomicClosureTruth PropT example_1.
Proof.
  exact (example_1_suite_atomic_sound
    (finite_registered_ledger_suite_examples
      (finite_registered_completion_ledger
        (finite_registered_component_completion
          finite_registered_truth_condition_component_coverage_certificate)))).
Qed.

Theorem finite_registered_truth_condition_component_coverage_example_2_atomic_sound :
  AtomicClosureTruth Prop example_2.
Proof.
  exact (example_2_suite_atomic_sound
    (finite_registered_ledger_suite_examples
      (finite_registered_completion_ledger
        (finite_registered_component_completion
          finite_registered_truth_condition_component_coverage_certificate)))).
Qed.

Theorem finite_registered_truth_condition_component_coverage_example_3_atomic_sound :
  AtomicClosureTruth PropT example_3.
Proof.
  exact (example_3_suite_atomic_sound
    (finite_registered_ledger_suite_examples
      (finite_registered_completion_ledger
        (finite_registered_component_completion
          finite_registered_truth_condition_component_coverage_certificate)))).
Qed.

Theorem finite_registered_truth_condition_component_coverage_example_4_atomic_sound :
  AtomicClosureTruth PropT example_4.
Proof.
  exact (example_4_suite_atomic_sound
    (finite_registered_ledger_suite_examples
      (finite_registered_completion_ledger
        (finite_registered_component_completion
          finite_registered_truth_condition_component_coverage_certificate)))).
Qed.

Record FiniteRegisteredAtomicWitnessCertificate : Type := {
  finite_registered_atomic_witness_basis : ConcreteRegisteredTruthBasis;
  finite_registered_atomic_witness_basis_eq :
      finite_registered_atomic_witness_basis = concrete_registered_truth_basis;
  finite_registered_atomic_witness_lexical_1_concrete : ConcreteRegisteredAtomicTruth PropT (break 0 mods_nil John vase);
  finite_registered_atomic_witness_lexical_1_base : AtomicBaseTruth PropT (break 0 mods_nil John vase);
  finite_registered_atomic_witness_lexical_1_closure : AtomicClosureTruth PropT (break 0 mods_nil John vase);
  finite_registered_atomic_witness_lexical_2_concrete : ConcreteRegisteredAtomicTruth PropT (butter 2 (mods_cons 1 slowly (mods_cons 0 in_bathroom mods_nil)) John toast);
  finite_registered_atomic_witness_lexical_2_base : AtomicBaseTruth PropT (butter 2 (mods_cons 1 slowly (mods_cons 0 in_bathroom mods_nil)) John toast);
  finite_registered_atomic_witness_lexical_2_closure : AtomicClosureTruth PropT (butter 2 (mods_cons 1 slowly (mods_cons 0 in_bathroom mods_nil)) John toast);
  finite_registered_atomic_witness_lexical_3_concrete : forall x_theme : Food,
      ConcreteRegisteredAtomicTruth Prop (eat 0 mods_nil John x_theme);
  finite_registered_atomic_witness_lexical_3_base : forall x_theme : Food,
      AtomicBaseTruth Prop (eat 0 mods_nil John x_theme);
  finite_registered_atomic_witness_lexical_3_closure : forall x_theme : Food,
      AtomicClosureTruth Prop (eat 0 mods_nil John x_theme);
  finite_registered_atomic_witness_lexical_4_concrete : ConcreteRegisteredAtomicTruth PropT (knock 0 mods_nil John);
  finite_registered_atomic_witness_lexical_4_base : AtomicBaseTruth PropT (knock 0 mods_nil John);
  finite_registered_atomic_witness_lexical_4_closure : AtomicClosureTruth PropT (knock 0 mods_nil John);
  finite_registered_atomic_witness_transition_1_concrete : ConcreteRegisteredAtomicTruth TransitionT (Transition vase integrity_scale intact broken);
  finite_registered_atomic_witness_transition_1_base : AtomicBaseTruth TransitionT (Transition vase integrity_scale intact broken);
  finite_registered_atomic_witness_transition_1_closure : AtomicClosureTruth TransitionT (Transition vase integrity_scale intact broken)
}.

Definition finite_registered_atomic_witness_certificate :
  FiniteRegisteredAtomicWitnessCertificate := {|
  finite_registered_atomic_witness_basis := concrete_registered_truth_basis;
  finite_registered_atomic_witness_basis_eq := eq_refl;
  finite_registered_atomic_witness_lexical_1_concrete := concrete_registered_atomic_truth_lexical_application PropT (break 0 mods_nil John vase) (registered_lexical_break_0_John_vase);
  finite_registered_atomic_witness_lexical_1_base := registered_lexical_application_atomic_base_truth PropT (break 0 mods_nil John vase) (registered_lexical_break_0_John_vase);
  finite_registered_atomic_witness_lexical_1_closure := registered_lexical_application_atomic_closure_truth PropT (break 0 mods_nil John vase) (registered_lexical_break_0_John_vase);
  finite_registered_atomic_witness_lexical_2_concrete := concrete_registered_atomic_truth_lexical_application PropT (butter 2 (mods_cons 1 slowly (mods_cons 0 in_bathroom mods_nil)) John toast) (registered_lexical_butter_2_slowly_in_bathroom_John_toast);
  finite_registered_atomic_witness_lexical_2_base := registered_lexical_application_atomic_base_truth PropT (butter 2 (mods_cons 1 slowly (mods_cons 0 in_bathroom mods_nil)) John toast) (registered_lexical_butter_2_slowly_in_bathroom_John_toast);
  finite_registered_atomic_witness_lexical_2_closure := registered_lexical_application_atomic_closure_truth PropT (butter 2 (mods_cons 1 slowly (mods_cons 0 in_bathroom mods_nil)) John toast) (registered_lexical_butter_2_slowly_in_bathroom_John_toast);
  finite_registered_atomic_witness_lexical_3_concrete := fun x_theme => concrete_registered_atomic_truth_lexical_application Prop (eat 0 mods_nil John x_theme) (registered_lexical_eat_0_John_x_theme x_theme);
  finite_registered_atomic_witness_lexical_3_base := fun x_theme => registered_lexical_application_atomic_base_truth Prop (eat 0 mods_nil John x_theme) (registered_lexical_eat_0_John_x_theme x_theme);
  finite_registered_atomic_witness_lexical_3_closure := fun x_theme => registered_lexical_application_atomic_closure_truth Prop (eat 0 mods_nil John x_theme) (registered_lexical_eat_0_John_x_theme x_theme);
  finite_registered_atomic_witness_lexical_4_concrete := concrete_registered_atomic_truth_lexical_application PropT (knock 0 mods_nil John) (registered_lexical_knock_0_John);
  finite_registered_atomic_witness_lexical_4_base := registered_lexical_application_atomic_base_truth PropT (knock 0 mods_nil John) (registered_lexical_knock_0_John);
  finite_registered_atomic_witness_lexical_4_closure := registered_lexical_application_atomic_closure_truth PropT (knock 0 mods_nil John) (registered_lexical_knock_0_John);
  finite_registered_atomic_witness_transition_1_concrete := concrete_registered_atomic_truth_transition vase integrity_scale intact broken registered_transition_vase_integrity_scale_intact_to_broken;
  finite_registered_atomic_witness_transition_1_base := registered_state_transition_atomic_base_truth vase integrity_scale intact broken registered_transition_vase_integrity_scale_intact_to_broken;
  finite_registered_atomic_witness_transition_1_closure := atomic_closure_truth_transition vase integrity_scale intact broken (registered_state_transition_atomic_base_truth vase integrity_scale intact broken registered_transition_vase_integrity_scale_intact_to_broken)
|}.

Theorem finite_registered_atomic_witness_certificate_exists :
  exists C : FiniteRegisteredAtomicWitnessCertificate,
    C = finite_registered_atomic_witness_certificate.
Proof.
  exists finite_registered_atomic_witness_certificate.
  reflexivity.
Qed.

Theorem finite_registered_atomic_witness_basis_matches :
  finite_registered_atomic_witness_basis
    finite_registered_atomic_witness_certificate =
  concrete_registered_truth_basis.
Proof.
  exact (finite_registered_atomic_witness_basis_eq
    finite_registered_atomic_witness_certificate).
Qed.

Theorem finite_registered_atomic_witness_lexical_1_concrete_projected :
  ConcreteRegisteredAtomicTruth PropT (break 0 mods_nil John vase).
Proof.
  exact (finite_registered_atomic_witness_lexical_1_concrete
    finite_registered_atomic_witness_certificate).
Qed.

Theorem finite_registered_atomic_witness_lexical_1_base_projected :
  AtomicBaseTruth PropT (break 0 mods_nil John vase).
Proof.
  exact (finite_registered_atomic_witness_lexical_1_base
    finite_registered_atomic_witness_certificate).
Qed.

Theorem finite_registered_atomic_witness_lexical_1_closure_projected :
  AtomicClosureTruth PropT (break 0 mods_nil John vase).
Proof.
  exact (finite_registered_atomic_witness_lexical_1_closure
    finite_registered_atomic_witness_certificate).
Qed.

Theorem finite_registered_atomic_witness_lexical_2_concrete_projected :
  ConcreteRegisteredAtomicTruth PropT (butter 2 (mods_cons 1 slowly (mods_cons 0 in_bathroom mods_nil)) John toast).
Proof.
  exact (finite_registered_atomic_witness_lexical_2_concrete
    finite_registered_atomic_witness_certificate).
Qed.

Theorem finite_registered_atomic_witness_lexical_2_base_projected :
  AtomicBaseTruth PropT (butter 2 (mods_cons 1 slowly (mods_cons 0 in_bathroom mods_nil)) John toast).
Proof.
  exact (finite_registered_atomic_witness_lexical_2_base
    finite_registered_atomic_witness_certificate).
Qed.

Theorem finite_registered_atomic_witness_lexical_2_closure_projected :
  AtomicClosureTruth PropT (butter 2 (mods_cons 1 slowly (mods_cons 0 in_bathroom mods_nil)) John toast).
Proof.
  exact (finite_registered_atomic_witness_lexical_2_closure
    finite_registered_atomic_witness_certificate).
Qed.

Theorem finite_registered_atomic_witness_lexical_3_concrete_projected :
  forall x_theme : Food,
      ConcreteRegisteredAtomicTruth Prop (eat 0 mods_nil John x_theme).
Proof.
  exact (finite_registered_atomic_witness_lexical_3_concrete
    finite_registered_atomic_witness_certificate).
Qed.

Theorem finite_registered_atomic_witness_lexical_3_base_projected :
  forall x_theme : Food,
      AtomicBaseTruth Prop (eat 0 mods_nil John x_theme).
Proof.
  exact (finite_registered_atomic_witness_lexical_3_base
    finite_registered_atomic_witness_certificate).
Qed.

Theorem finite_registered_atomic_witness_lexical_3_closure_projected :
  forall x_theme : Food,
      AtomicClosureTruth Prop (eat 0 mods_nil John x_theme).
Proof.
  exact (finite_registered_atomic_witness_lexical_3_closure
    finite_registered_atomic_witness_certificate).
Qed.

Theorem finite_registered_atomic_witness_lexical_4_concrete_projected :
  ConcreteRegisteredAtomicTruth PropT (knock 0 mods_nil John).
Proof.
  exact (finite_registered_atomic_witness_lexical_4_concrete
    finite_registered_atomic_witness_certificate).
Qed.

Theorem finite_registered_atomic_witness_lexical_4_base_projected :
  AtomicBaseTruth PropT (knock 0 mods_nil John).
Proof.
  exact (finite_registered_atomic_witness_lexical_4_base
    finite_registered_atomic_witness_certificate).
Qed.

Theorem finite_registered_atomic_witness_lexical_4_closure_projected :
  AtomicClosureTruth PropT (knock 0 mods_nil John).
Proof.
  exact (finite_registered_atomic_witness_lexical_4_closure
    finite_registered_atomic_witness_certificate).
Qed.

Theorem finite_registered_atomic_witness_transition_1_concrete_projected :
  ConcreteRegisteredAtomicTruth TransitionT (Transition vase integrity_scale intact broken).
Proof.
  exact (finite_registered_atomic_witness_transition_1_concrete
    finite_registered_atomic_witness_certificate).
Qed.

Theorem finite_registered_atomic_witness_transition_1_base_projected :
  AtomicBaseTruth TransitionT (Transition vase integrity_scale intact broken).
Proof.
  exact (finite_registered_atomic_witness_transition_1_base
    finite_registered_atomic_witness_certificate).
Qed.

Theorem finite_registered_atomic_witness_transition_1_closure_projected :
  AtomicClosureTruth TransitionT (Transition vase integrity_scale intact broken).
Proof.
  exact (finite_registered_atomic_witness_transition_1_closure
    finite_registered_atomic_witness_certificate).
Qed.

Record FiniteRegisteredAtomicSourceDisciplineCertificate : Type := {
  finite_registered_atomic_source_witness : FiniteRegisteredAtomicWitnessCertificate;
  finite_registered_atomic_source_witness_eq :
      finite_registered_atomic_source_witness = finite_registered_atomic_witness_certificate;
  finite_registered_atomic_source_lexical_1_source : RegisteredLexicalApplicationTruth PropT (break 0 mods_nil John vase);
  finite_registered_atomic_source_lexical_1_concrete_from_source : RegisteredLexicalApplicationTruth PropT (break 0 mods_nil John vase) ->
      ConcreteRegisteredAtomicTruth PropT (break 0 mods_nil John vase);
  finite_registered_atomic_source_lexical_1_base_from_source : RegisteredLexicalApplicationTruth PropT (break 0 mods_nil John vase) ->
      AtomicBaseTruth PropT (break 0 mods_nil John vase);
  finite_registered_atomic_source_lexical_1_closure_from_source : RegisteredLexicalApplicationTruth PropT (break 0 mods_nil John vase) ->
      AtomicClosureTruth PropT (break 0 mods_nil John vase);
  finite_registered_atomic_source_lexical_2_source : RegisteredLexicalApplicationTruth PropT (butter 2 (mods_cons 1 slowly (mods_cons 0 in_bathroom mods_nil)) John toast);
  finite_registered_atomic_source_lexical_2_concrete_from_source : RegisteredLexicalApplicationTruth PropT (butter 2 (mods_cons 1 slowly (mods_cons 0 in_bathroom mods_nil)) John toast) ->
      ConcreteRegisteredAtomicTruth PropT (butter 2 (mods_cons 1 slowly (mods_cons 0 in_bathroom mods_nil)) John toast);
  finite_registered_atomic_source_lexical_2_base_from_source : RegisteredLexicalApplicationTruth PropT (butter 2 (mods_cons 1 slowly (mods_cons 0 in_bathroom mods_nil)) John toast) ->
      AtomicBaseTruth PropT (butter 2 (mods_cons 1 slowly (mods_cons 0 in_bathroom mods_nil)) John toast);
  finite_registered_atomic_source_lexical_2_closure_from_source : RegisteredLexicalApplicationTruth PropT (butter 2 (mods_cons 1 slowly (mods_cons 0 in_bathroom mods_nil)) John toast) ->
      AtomicClosureTruth PropT (butter 2 (mods_cons 1 slowly (mods_cons 0 in_bathroom mods_nil)) John toast);
  finite_registered_atomic_source_lexical_3_source : forall x_theme : Food,
      RegisteredLexicalApplicationTruth Prop (eat 0 mods_nil John x_theme);
  finite_registered_atomic_source_lexical_3_concrete_from_source : forall x_theme : Food,
      RegisteredLexicalApplicationTruth Prop (eat 0 mods_nil John x_theme) ->
      ConcreteRegisteredAtomicTruth Prop (eat 0 mods_nil John x_theme);
  finite_registered_atomic_source_lexical_3_base_from_source : forall x_theme : Food,
      RegisteredLexicalApplicationTruth Prop (eat 0 mods_nil John x_theme) ->
      AtomicBaseTruth Prop (eat 0 mods_nil John x_theme);
  finite_registered_atomic_source_lexical_3_closure_from_source : forall x_theme : Food,
      RegisteredLexicalApplicationTruth Prop (eat 0 mods_nil John x_theme) ->
      AtomicClosureTruth Prop (eat 0 mods_nil John x_theme);
  finite_registered_atomic_source_lexical_4_source : RegisteredLexicalApplicationTruth PropT (knock 0 mods_nil John);
  finite_registered_atomic_source_lexical_4_concrete_from_source : RegisteredLexicalApplicationTruth PropT (knock 0 mods_nil John) ->
      ConcreteRegisteredAtomicTruth PropT (knock 0 mods_nil John);
  finite_registered_atomic_source_lexical_4_base_from_source : RegisteredLexicalApplicationTruth PropT (knock 0 mods_nil John) ->
      AtomicBaseTruth PropT (knock 0 mods_nil John);
  finite_registered_atomic_source_lexical_4_closure_from_source : RegisteredLexicalApplicationTruth PropT (knock 0 mods_nil John) ->
      AtomicClosureTruth PropT (knock 0 mods_nil John);
  finite_registered_atomic_source_transition_1_source : RegisteredStateTransitionTruth vase integrity_scale intact broken;
  finite_registered_atomic_source_transition_1_concrete_from_source : RegisteredStateTransitionTruth vase integrity_scale intact broken ->
      ConcreteRegisteredAtomicTruth TransitionT (Transition vase integrity_scale intact broken);
  finite_registered_atomic_source_transition_1_base_from_source : RegisteredStateTransitionTruth vase integrity_scale intact broken ->
      AtomicBaseTruth TransitionT (Transition vase integrity_scale intact broken);
  finite_registered_atomic_source_transition_1_closure_from_source : RegisteredStateTransitionTruth vase integrity_scale intact broken ->
      AtomicClosureTruth TransitionT (Transition vase integrity_scale intact broken)
}.

Definition finite_registered_atomic_source_discipline_certificate :
  FiniteRegisteredAtomicSourceDisciplineCertificate := {|
  finite_registered_atomic_source_witness := finite_registered_atomic_witness_certificate;
  finite_registered_atomic_source_witness_eq := eq_refl;
  finite_registered_atomic_source_lexical_1_source := registered_lexical_break_0_John_vase;
  finite_registered_atomic_source_lexical_1_concrete_from_source := fun h_source => concrete_registered_atomic_truth_lexical_application PropT (break 0 mods_nil John vase) h_source;
  finite_registered_atomic_source_lexical_1_base_from_source := fun h_source => registered_lexical_application_atomic_base_truth PropT (break 0 mods_nil John vase) h_source;
  finite_registered_atomic_source_lexical_1_closure_from_source := fun h_source => registered_lexical_application_atomic_closure_truth PropT (break 0 mods_nil John vase) h_source;
  finite_registered_atomic_source_lexical_2_source := registered_lexical_butter_2_slowly_in_bathroom_John_toast;
  finite_registered_atomic_source_lexical_2_concrete_from_source := fun h_source => concrete_registered_atomic_truth_lexical_application PropT (butter 2 (mods_cons 1 slowly (mods_cons 0 in_bathroom mods_nil)) John toast) h_source;
  finite_registered_atomic_source_lexical_2_base_from_source := fun h_source => registered_lexical_application_atomic_base_truth PropT (butter 2 (mods_cons 1 slowly (mods_cons 0 in_bathroom mods_nil)) John toast) h_source;
  finite_registered_atomic_source_lexical_2_closure_from_source := fun h_source => registered_lexical_application_atomic_closure_truth PropT (butter 2 (mods_cons 1 slowly (mods_cons 0 in_bathroom mods_nil)) John toast) h_source;
  finite_registered_atomic_source_lexical_3_source := fun x_theme => registered_lexical_eat_0_John_x_theme x_theme;
  finite_registered_atomic_source_lexical_3_concrete_from_source := fun x_theme h_source => concrete_registered_atomic_truth_lexical_application Prop (eat 0 mods_nil John x_theme) h_source;
  finite_registered_atomic_source_lexical_3_base_from_source := fun x_theme h_source => registered_lexical_application_atomic_base_truth Prop (eat 0 mods_nil John x_theme) h_source;
  finite_registered_atomic_source_lexical_3_closure_from_source := fun x_theme h_source => registered_lexical_application_atomic_closure_truth Prop (eat 0 mods_nil John x_theme) h_source;
  finite_registered_atomic_source_lexical_4_source := registered_lexical_knock_0_John;
  finite_registered_atomic_source_lexical_4_concrete_from_source := fun h_source => concrete_registered_atomic_truth_lexical_application PropT (knock 0 mods_nil John) h_source;
  finite_registered_atomic_source_lexical_4_base_from_source := fun h_source => registered_lexical_application_atomic_base_truth PropT (knock 0 mods_nil John) h_source;
  finite_registered_atomic_source_lexical_4_closure_from_source := fun h_source => registered_lexical_application_atomic_closure_truth PropT (knock 0 mods_nil John) h_source;
  finite_registered_atomic_source_transition_1_source := registered_transition_vase_integrity_scale_intact_to_broken;
  finite_registered_atomic_source_transition_1_concrete_from_source := fun h_source => concrete_registered_atomic_truth_transition vase integrity_scale intact broken h_source;
  finite_registered_atomic_source_transition_1_base_from_source := fun h_source => registered_state_transition_atomic_base_truth vase integrity_scale intact broken h_source;
  finite_registered_atomic_source_transition_1_closure_from_source := fun h_source => atomic_closure_truth_transition vase integrity_scale intact broken (registered_state_transition_atomic_base_truth vase integrity_scale intact broken h_source)
|}.

Theorem finite_registered_atomic_source_discipline_certificate_exists :
  exists C : FiniteRegisteredAtomicSourceDisciplineCertificate,
    C = finite_registered_atomic_source_discipline_certificate.
Proof.
  exists finite_registered_atomic_source_discipline_certificate.
  reflexivity.
Qed.

Theorem finite_registered_atomic_source_witness_matches :
  finite_registered_atomic_source_witness
    finite_registered_atomic_source_discipline_certificate =
  finite_registered_atomic_witness_certificate.
Proof.
  exact (finite_registered_atomic_source_witness_eq
    finite_registered_atomic_source_discipline_certificate).
Qed.

Theorem finite_registered_atomic_source_lexical_1_source_projected :
  RegisteredLexicalApplicationTruth PropT (break 0 mods_nil John vase).
Proof.
  exact (finite_registered_atomic_source_lexical_1_source
    finite_registered_atomic_source_discipline_certificate).
Qed.

Theorem finite_registered_atomic_source_lexical_1_concrete_from_source_projected :
  RegisteredLexicalApplicationTruth PropT (break 0 mods_nil John vase) ->
      ConcreteRegisteredAtomicTruth PropT (break 0 mods_nil John vase).
Proof.
  exact (finite_registered_atomic_source_lexical_1_concrete_from_source
    finite_registered_atomic_source_discipline_certificate).
Qed.

Theorem finite_registered_atomic_source_lexical_1_base_from_source_projected :
  RegisteredLexicalApplicationTruth PropT (break 0 mods_nil John vase) ->
      AtomicBaseTruth PropT (break 0 mods_nil John vase).
Proof.
  exact (finite_registered_atomic_source_lexical_1_base_from_source
    finite_registered_atomic_source_discipline_certificate).
Qed.

Theorem finite_registered_atomic_source_lexical_1_closure_from_source_projected :
  RegisteredLexicalApplicationTruth PropT (break 0 mods_nil John vase) ->
      AtomicClosureTruth PropT (break 0 mods_nil John vase).
Proof.
  exact (finite_registered_atomic_source_lexical_1_closure_from_source
    finite_registered_atomic_source_discipline_certificate).
Qed.

Theorem finite_registered_atomic_source_lexical_2_source_projected :
  RegisteredLexicalApplicationTruth PropT (butter 2 (mods_cons 1 slowly (mods_cons 0 in_bathroom mods_nil)) John toast).
Proof.
  exact (finite_registered_atomic_source_lexical_2_source
    finite_registered_atomic_source_discipline_certificate).
Qed.

Theorem finite_registered_atomic_source_lexical_2_concrete_from_source_projected :
  RegisteredLexicalApplicationTruth PropT (butter 2 (mods_cons 1 slowly (mods_cons 0 in_bathroom mods_nil)) John toast) ->
      ConcreteRegisteredAtomicTruth PropT (butter 2 (mods_cons 1 slowly (mods_cons 0 in_bathroom mods_nil)) John toast).
Proof.
  exact (finite_registered_atomic_source_lexical_2_concrete_from_source
    finite_registered_atomic_source_discipline_certificate).
Qed.

Theorem finite_registered_atomic_source_lexical_2_base_from_source_projected :
  RegisteredLexicalApplicationTruth PropT (butter 2 (mods_cons 1 slowly (mods_cons 0 in_bathroom mods_nil)) John toast) ->
      AtomicBaseTruth PropT (butter 2 (mods_cons 1 slowly (mods_cons 0 in_bathroom mods_nil)) John toast).
Proof.
  exact (finite_registered_atomic_source_lexical_2_base_from_source
    finite_registered_atomic_source_discipline_certificate).
Qed.

Theorem finite_registered_atomic_source_lexical_2_closure_from_source_projected :
  RegisteredLexicalApplicationTruth PropT (butter 2 (mods_cons 1 slowly (mods_cons 0 in_bathroom mods_nil)) John toast) ->
      AtomicClosureTruth PropT (butter 2 (mods_cons 1 slowly (mods_cons 0 in_bathroom mods_nil)) John toast).
Proof.
  exact (finite_registered_atomic_source_lexical_2_closure_from_source
    finite_registered_atomic_source_discipline_certificate).
Qed.

Theorem finite_registered_atomic_source_lexical_3_source_projected :
  forall x_theme : Food,
      RegisteredLexicalApplicationTruth Prop (eat 0 mods_nil John x_theme).
Proof.
  exact (finite_registered_atomic_source_lexical_3_source
    finite_registered_atomic_source_discipline_certificate).
Qed.

Theorem finite_registered_atomic_source_lexical_3_concrete_from_source_projected :
  forall x_theme : Food,
      RegisteredLexicalApplicationTruth Prop (eat 0 mods_nil John x_theme) ->
      ConcreteRegisteredAtomicTruth Prop (eat 0 mods_nil John x_theme).
Proof.
  exact (finite_registered_atomic_source_lexical_3_concrete_from_source
    finite_registered_atomic_source_discipline_certificate).
Qed.

Theorem finite_registered_atomic_source_lexical_3_base_from_source_projected :
  forall x_theme : Food,
      RegisteredLexicalApplicationTruth Prop (eat 0 mods_nil John x_theme) ->
      AtomicBaseTruth Prop (eat 0 mods_nil John x_theme).
Proof.
  exact (finite_registered_atomic_source_lexical_3_base_from_source
    finite_registered_atomic_source_discipline_certificate).
Qed.

Theorem finite_registered_atomic_source_lexical_3_closure_from_source_projected :
  forall x_theme : Food,
      RegisteredLexicalApplicationTruth Prop (eat 0 mods_nil John x_theme) ->
      AtomicClosureTruth Prop (eat 0 mods_nil John x_theme).
Proof.
  exact (finite_registered_atomic_source_lexical_3_closure_from_source
    finite_registered_atomic_source_discipline_certificate).
Qed.

Theorem finite_registered_atomic_source_lexical_4_source_projected :
  RegisteredLexicalApplicationTruth PropT (knock 0 mods_nil John).
Proof.
  exact (finite_registered_atomic_source_lexical_4_source
    finite_registered_atomic_source_discipline_certificate).
Qed.

Theorem finite_registered_atomic_source_lexical_4_concrete_from_source_projected :
  RegisteredLexicalApplicationTruth PropT (knock 0 mods_nil John) ->
      ConcreteRegisteredAtomicTruth PropT (knock 0 mods_nil John).
Proof.
  exact (finite_registered_atomic_source_lexical_4_concrete_from_source
    finite_registered_atomic_source_discipline_certificate).
Qed.

Theorem finite_registered_atomic_source_lexical_4_base_from_source_projected :
  RegisteredLexicalApplicationTruth PropT (knock 0 mods_nil John) ->
      AtomicBaseTruth PropT (knock 0 mods_nil John).
Proof.
  exact (finite_registered_atomic_source_lexical_4_base_from_source
    finite_registered_atomic_source_discipline_certificate).
Qed.

Theorem finite_registered_atomic_source_lexical_4_closure_from_source_projected :
  RegisteredLexicalApplicationTruth PropT (knock 0 mods_nil John) ->
      AtomicClosureTruth PropT (knock 0 mods_nil John).
Proof.
  exact (finite_registered_atomic_source_lexical_4_closure_from_source
    finite_registered_atomic_source_discipline_certificate).
Qed.

Theorem finite_registered_atomic_source_transition_1_source_projected :
  RegisteredStateTransitionTruth vase integrity_scale intact broken.
Proof.
  exact (finite_registered_atomic_source_transition_1_source
    finite_registered_atomic_source_discipline_certificate).
Qed.

Theorem finite_registered_atomic_source_transition_1_concrete_from_source_projected :
  RegisteredStateTransitionTruth vase integrity_scale intact broken ->
      ConcreteRegisteredAtomicTruth TransitionT (Transition vase integrity_scale intact broken).
Proof.
  exact (finite_registered_atomic_source_transition_1_concrete_from_source
    finite_registered_atomic_source_discipline_certificate).
Qed.

Theorem finite_registered_atomic_source_transition_1_base_from_source_projected :
  RegisteredStateTransitionTruth vase integrity_scale intact broken ->
      AtomicBaseTruth TransitionT (Transition vase integrity_scale intact broken).
Proof.
  exact (finite_registered_atomic_source_transition_1_base_from_source
    finite_registered_atomic_source_discipline_certificate).
Qed.

Theorem finite_registered_atomic_source_transition_1_closure_from_source_projected :
  RegisteredStateTransitionTruth vase integrity_scale intact broken ->
      AtomicClosureTruth TransitionT (Transition vase integrity_scale intact broken).
Proof.
  exact (finite_registered_atomic_source_transition_1_closure_from_source
    finite_registered_atomic_source_discipline_certificate).
Qed.

Theorem finite_registered_atomic_kernel_denotes_imply_atomic_closure :
  forall A : Type, forall term : A,
    concrete_registered_kernel_denotes concrete_registered_truth_kernel A term ->
    AtomicClosureTruth A term.
Proof.
  intros A term H.
  apply concrete_registered_truth_conditions_from_kernel_imply_atomic_closure.
  exact H.
Qed.

Record FiniteRegisteredAtomicKernelAlignmentCertificate : Type := {
  finite_registered_atomic_kernel_alignment_source : FiniteRegisteredAtomicSourceDisciplineCertificate;
  finite_registered_atomic_kernel_alignment_source_eq :
      finite_registered_atomic_kernel_alignment_source = finite_registered_atomic_source_discipline_certificate;
  finite_registered_atomic_kernel_alignment_kernel : ConcreteRegisteredTruthKernel;
  finite_registered_atomic_kernel_alignment_kernel_eq :
      finite_registered_atomic_kernel_alignment_kernel = concrete_registered_truth_kernel;
  finite_registered_atomic_kernel_alignment_sound :
      forall A : Type, forall term : A,
      concrete_registered_kernel_denotes concrete_registered_truth_kernel A term ->
      AtomicClosureTruth A term;
  finite_registered_atomic_kernel_alignment_lexical_1_source_to_kernel : RegisteredLexicalApplicationTruth PropT (break 0 mods_nil John vase) ->
      concrete_registered_kernel_denotes concrete_registered_truth_kernel PropT (break 0 mods_nil John vase);
  finite_registered_atomic_kernel_alignment_lexical_2_source_to_kernel : RegisteredLexicalApplicationTruth PropT (butter 2 (mods_cons 1 slowly (mods_cons 0 in_bathroom mods_nil)) John toast) ->
      concrete_registered_kernel_denotes concrete_registered_truth_kernel PropT (butter 2 (mods_cons 1 slowly (mods_cons 0 in_bathroom mods_nil)) John toast);
  finite_registered_atomic_kernel_alignment_lexical_3_source_to_kernel : forall x_theme : Food,
      RegisteredLexicalApplicationTruth Prop (eat 0 mods_nil John x_theme) ->
      concrete_registered_kernel_denotes concrete_registered_truth_kernel Prop (eat 0 mods_nil John x_theme);
  finite_registered_atomic_kernel_alignment_lexical_4_source_to_kernel : RegisteredLexicalApplicationTruth PropT (knock 0 mods_nil John) ->
      concrete_registered_kernel_denotes concrete_registered_truth_kernel PropT (knock 0 mods_nil John);
  finite_registered_atomic_kernel_alignment_transition_1_source_to_kernel : RegisteredStateTransitionTruth vase integrity_scale intact broken ->
      concrete_registered_kernel_denotes concrete_registered_truth_kernel TransitionT (Transition vase integrity_scale intact broken)
}.

Definition finite_registered_atomic_kernel_alignment_certificate :
  FiniteRegisteredAtomicKernelAlignmentCertificate := {|
  finite_registered_atomic_kernel_alignment_source := finite_registered_atomic_source_discipline_certificate;
  finite_registered_atomic_kernel_alignment_source_eq := eq_refl;
  finite_registered_atomic_kernel_alignment_kernel := concrete_registered_truth_kernel;
  finite_registered_atomic_kernel_alignment_kernel_eq := eq_refl;
  finite_registered_atomic_kernel_alignment_sound := finite_registered_atomic_kernel_denotes_imply_atomic_closure;
  finite_registered_atomic_kernel_alignment_lexical_1_source_to_kernel := fun h_source => concrete_registered_kernel_lexical_application concrete_registered_truth_kernel PropT (break 0 mods_nil John vase) h_source;
  finite_registered_atomic_kernel_alignment_lexical_2_source_to_kernel := fun h_source => concrete_registered_kernel_lexical_application concrete_registered_truth_kernel PropT (butter 2 (mods_cons 1 slowly (mods_cons 0 in_bathroom mods_nil)) John toast) h_source;
  finite_registered_atomic_kernel_alignment_lexical_3_source_to_kernel := fun x_theme h_source => concrete_registered_kernel_lexical_application concrete_registered_truth_kernel Prop (eat 0 mods_nil John x_theme) h_source;
  finite_registered_atomic_kernel_alignment_lexical_4_source_to_kernel := fun h_source => concrete_registered_kernel_lexical_application concrete_registered_truth_kernel PropT (knock 0 mods_nil John) h_source;
  finite_registered_atomic_kernel_alignment_transition_1_source_to_kernel := fun h_source => concrete_registered_kernel_transition concrete_registered_truth_kernel vase integrity_scale intact broken h_source
|}.

Theorem finite_registered_atomic_kernel_alignment_certificate_exists :
  exists C : FiniteRegisteredAtomicKernelAlignmentCertificate,
    C = finite_registered_atomic_kernel_alignment_certificate.
Proof.
  exists finite_registered_atomic_kernel_alignment_certificate.
  reflexivity.
Qed.

Theorem finite_registered_atomic_kernel_alignment_source_matches :
  finite_registered_atomic_kernel_alignment_source
    finite_registered_atomic_kernel_alignment_certificate =
  finite_registered_atomic_source_discipline_certificate.
Proof.
  exact (finite_registered_atomic_kernel_alignment_source_eq
    finite_registered_atomic_kernel_alignment_certificate).
Qed.

Theorem finite_registered_atomic_kernel_alignment_kernel_matches :
  finite_registered_atomic_kernel_alignment_kernel
    finite_registered_atomic_kernel_alignment_certificate =
  concrete_registered_truth_kernel.
Proof.
  exact (finite_registered_atomic_kernel_alignment_kernel_eq
    finite_registered_atomic_kernel_alignment_certificate).
Qed.

Theorem finite_registered_atomic_kernel_alignment_sound_projected :
  forall A : Type, forall term : A,
    concrete_registered_kernel_denotes concrete_registered_truth_kernel A term ->
    AtomicClosureTruth A term.
Proof.
  exact (finite_registered_atomic_kernel_alignment_sound
    finite_registered_atomic_kernel_alignment_certificate).
Qed.

Theorem finite_registered_atomic_kernel_alignment_lexical_1_source_to_kernel_projected :
  RegisteredLexicalApplicationTruth PropT (break 0 mods_nil John vase) ->
      concrete_registered_kernel_denotes concrete_registered_truth_kernel PropT (break 0 mods_nil John vase).
Proof.
  exact (finite_registered_atomic_kernel_alignment_lexical_1_source_to_kernel
    finite_registered_atomic_kernel_alignment_certificate).
Qed.

Theorem finite_registered_atomic_kernel_alignment_lexical_1_atomic_projected :
  AtomicClosureTruth PropT (break 0 mods_nil John vase).
Proof.
  apply finite_registered_atomic_kernel_denotes_imply_atomic_closure.
  exact (finite_registered_atomic_kernel_alignment_lexical_1_source_to_kernel
    finite_registered_atomic_kernel_alignment_certificate
    (finite_registered_atomic_source_lexical_1_source_projected)).
Qed.

Theorem finite_registered_atomic_kernel_alignment_lexical_2_source_to_kernel_projected :
  RegisteredLexicalApplicationTruth PropT (butter 2 (mods_cons 1 slowly (mods_cons 0 in_bathroom mods_nil)) John toast) ->
      concrete_registered_kernel_denotes concrete_registered_truth_kernel PropT (butter 2 (mods_cons 1 slowly (mods_cons 0 in_bathroom mods_nil)) John toast).
Proof.
  exact (finite_registered_atomic_kernel_alignment_lexical_2_source_to_kernel
    finite_registered_atomic_kernel_alignment_certificate).
Qed.

Theorem finite_registered_atomic_kernel_alignment_lexical_2_atomic_projected :
  AtomicClosureTruth PropT (butter 2 (mods_cons 1 slowly (mods_cons 0 in_bathroom mods_nil)) John toast).
Proof.
  apply finite_registered_atomic_kernel_denotes_imply_atomic_closure.
  exact (finite_registered_atomic_kernel_alignment_lexical_2_source_to_kernel
    finite_registered_atomic_kernel_alignment_certificate
    (finite_registered_atomic_source_lexical_2_source_projected)).
Qed.

Theorem finite_registered_atomic_kernel_alignment_lexical_3_source_to_kernel_projected :
  forall x_theme : Food,
      RegisteredLexicalApplicationTruth Prop (eat 0 mods_nil John x_theme) ->
      concrete_registered_kernel_denotes concrete_registered_truth_kernel Prop (eat 0 mods_nil John x_theme).
Proof.
  exact (finite_registered_atomic_kernel_alignment_lexical_3_source_to_kernel
    finite_registered_atomic_kernel_alignment_certificate).
Qed.

Theorem finite_registered_atomic_kernel_alignment_lexical_3_atomic_projected :
  forall x_theme : Food,
      AtomicClosureTruth Prop (eat 0 mods_nil John x_theme).
Proof.
  intros x_theme.
  apply finite_registered_atomic_kernel_denotes_imply_atomic_closure.
  exact (finite_registered_atomic_kernel_alignment_lexical_3_source_to_kernel
    finite_registered_atomic_kernel_alignment_certificate
    x_theme
    (finite_registered_atomic_source_lexical_3_source_projected x_theme)).
Qed.

Theorem finite_registered_atomic_kernel_alignment_lexical_4_source_to_kernel_projected :
  RegisteredLexicalApplicationTruth PropT (knock 0 mods_nil John) ->
      concrete_registered_kernel_denotes concrete_registered_truth_kernel PropT (knock 0 mods_nil John).
Proof.
  exact (finite_registered_atomic_kernel_alignment_lexical_4_source_to_kernel
    finite_registered_atomic_kernel_alignment_certificate).
Qed.

Theorem finite_registered_atomic_kernel_alignment_lexical_4_atomic_projected :
  AtomicClosureTruth PropT (knock 0 mods_nil John).
Proof.
  apply finite_registered_atomic_kernel_denotes_imply_atomic_closure.
  exact (finite_registered_atomic_kernel_alignment_lexical_4_source_to_kernel
    finite_registered_atomic_kernel_alignment_certificate
    (finite_registered_atomic_source_lexical_4_source_projected)).
Qed.

Theorem finite_registered_atomic_kernel_alignment_transition_1_source_to_kernel_projected :
  RegisteredStateTransitionTruth vase integrity_scale intact broken ->
      concrete_registered_kernel_denotes concrete_registered_truth_kernel TransitionT (Transition vase integrity_scale intact broken).
Proof.
  exact (finite_registered_atomic_kernel_alignment_transition_1_source_to_kernel
    finite_registered_atomic_kernel_alignment_certificate).
Qed.

Theorem finite_registered_atomic_kernel_alignment_transition_1_atomic_projected :
  AtomicClosureTruth TransitionT (Transition vase integrity_scale intact broken).
Proof.
  apply finite_registered_atomic_kernel_denotes_imply_atomic_closure.
  exact (finite_registered_atomic_kernel_alignment_transition_1_source_to_kernel
    finite_registered_atomic_kernel_alignment_certificate
    (finite_registered_atomic_source_transition_1_source_projected)).
Qed.

Record FiniteRegisteredAtomicTruthConditionSourceCertificate : Type := {
  finite_registered_atomic_truth_condition_source_alignment : FiniteRegisteredAtomicKernelAlignmentCertificate;
  finite_registered_atomic_truth_condition_source_alignment_eq :
      finite_registered_atomic_truth_condition_source_alignment = finite_registered_atomic_kernel_alignment_certificate;
  finite_registered_atomic_truth_condition_source_spec : FullyRegisteredTruthConditionSpec;
  finite_registered_atomic_truth_condition_source_spec_eq :
      finite_registered_atomic_truth_condition_source_spec = concrete_registered_truth_conditions;
  finite_registered_atomic_truth_condition_source_sound :
      forall A : Type, forall term : A,
      fully_registered_truth_denotes concrete_registered_truth_conditions A term ->
      AtomicClosureTruth A term;
  finite_registered_atomic_truth_condition_source_lexical_1_source_to_spec : RegisteredLexicalApplicationTruth PropT (break 0 mods_nil John vase) ->
      fully_registered_truth_denotes concrete_registered_truth_conditions PropT (break 0 mods_nil John vase);
  finite_registered_atomic_truth_condition_source_lexical_2_source_to_spec : RegisteredLexicalApplicationTruth PropT (butter 2 (mods_cons 1 slowly (mods_cons 0 in_bathroom mods_nil)) John toast) ->
      fully_registered_truth_denotes concrete_registered_truth_conditions PropT (butter 2 (mods_cons 1 slowly (mods_cons 0 in_bathroom mods_nil)) John toast);
  finite_registered_atomic_truth_condition_source_lexical_3_source_to_spec : forall x_theme : Food,
      RegisteredLexicalApplicationTruth Prop (eat 0 mods_nil John x_theme) ->
      fully_registered_truth_denotes concrete_registered_truth_conditions Prop (eat 0 mods_nil John x_theme);
  finite_registered_atomic_truth_condition_source_lexical_4_source_to_spec : RegisteredLexicalApplicationTruth PropT (knock 0 mods_nil John) ->
      fully_registered_truth_denotes concrete_registered_truth_conditions PropT (knock 0 mods_nil John);
  finite_registered_atomic_truth_condition_source_transition_1_source_to_spec : RegisteredStateTransitionTruth vase integrity_scale intact broken ->
      fully_registered_truth_denotes concrete_registered_truth_conditions TransitionT (Transition vase integrity_scale intact broken)
}.

Definition finite_registered_atomic_truth_condition_source_certificate :
  FiniteRegisteredAtomicTruthConditionSourceCertificate := {|
  finite_registered_atomic_truth_condition_source_alignment := finite_registered_atomic_kernel_alignment_certificate;
  finite_registered_atomic_truth_condition_source_alignment_eq := eq_refl;
  finite_registered_atomic_truth_condition_source_spec := concrete_registered_truth_conditions;
  finite_registered_atomic_truth_condition_source_spec_eq := eq_refl;
  finite_registered_atomic_truth_condition_source_sound := concrete_registered_truth_conditions_imply_atomic_closure;
  finite_registered_atomic_truth_condition_source_lexical_1_source_to_spec := fun h_source => fully_registered_truth_lexical_application concrete_registered_truth_conditions PropT (break 0 mods_nil John vase) h_source;
  finite_registered_atomic_truth_condition_source_lexical_2_source_to_spec := fun h_source => fully_registered_truth_lexical_application concrete_registered_truth_conditions PropT (butter 2 (mods_cons 1 slowly (mods_cons 0 in_bathroom mods_nil)) John toast) h_source;
  finite_registered_atomic_truth_condition_source_lexical_3_source_to_spec := fun x_theme h_source => fully_registered_truth_lexical_application concrete_registered_truth_conditions Prop (eat 0 mods_nil John x_theme) h_source;
  finite_registered_atomic_truth_condition_source_lexical_4_source_to_spec := fun h_source => fully_registered_truth_lexical_application concrete_registered_truth_conditions PropT (knock 0 mods_nil John) h_source;
  finite_registered_atomic_truth_condition_source_transition_1_source_to_spec := fun h_source => fully_registered_truth_transition concrete_registered_truth_conditions vase integrity_scale intact broken h_source
|}.

Theorem finite_registered_atomic_truth_condition_source_certificate_exists :
  exists C : FiniteRegisteredAtomicTruthConditionSourceCertificate,
    C = finite_registered_atomic_truth_condition_source_certificate.
Proof.
  exists finite_registered_atomic_truth_condition_source_certificate.
  reflexivity.
Qed.

Theorem finite_registered_atomic_truth_condition_source_alignment_matches :
  finite_registered_atomic_truth_condition_source_alignment
    finite_registered_atomic_truth_condition_source_certificate =
  finite_registered_atomic_kernel_alignment_certificate.
Proof.
  exact (finite_registered_atomic_truth_condition_source_alignment_eq
    finite_registered_atomic_truth_condition_source_certificate).
Qed.

Theorem finite_registered_atomic_truth_condition_source_spec_matches :
  finite_registered_atomic_truth_condition_source_spec
    finite_registered_atomic_truth_condition_source_certificate =
  concrete_registered_truth_conditions.
Proof.
  exact (finite_registered_atomic_truth_condition_source_spec_eq
    finite_registered_atomic_truth_condition_source_certificate).
Qed.

Theorem finite_registered_atomic_truth_condition_source_sound_projected :
  forall A : Type, forall term : A,
    fully_registered_truth_denotes concrete_registered_truth_conditions A term ->
    AtomicClosureTruth A term.
Proof.
  exact (finite_registered_atomic_truth_condition_source_sound
    finite_registered_atomic_truth_condition_source_certificate).
Qed.

Theorem finite_registered_atomic_truth_condition_source_lexical_1_source_to_spec_projected :
  RegisteredLexicalApplicationTruth PropT (break 0 mods_nil John vase) ->
      fully_registered_truth_denotes concrete_registered_truth_conditions PropT (break 0 mods_nil John vase).
Proof.
  exact (finite_registered_atomic_truth_condition_source_lexical_1_source_to_spec
    finite_registered_atomic_truth_condition_source_certificate).
Qed.

Theorem finite_registered_atomic_truth_condition_source_lexical_1_source_to_kernel_projected :
  RegisteredLexicalApplicationTruth PropT (break 0 mods_nil John vase) ->
      concrete_registered_kernel_denotes concrete_registered_truth_kernel PropT (break 0 mods_nil John vase).
Proof.
  exact (finite_registered_atomic_kernel_alignment_lexical_1_source_to_kernel
    (finite_registered_atomic_truth_condition_source_alignment
      finite_registered_atomic_truth_condition_source_certificate)).
Qed.

Theorem finite_registered_atomic_truth_condition_source_lexical_1_atomic_projected :
  AtomicClosureTruth PropT (break 0 mods_nil John vase).
Proof.
  apply concrete_registered_truth_conditions_imply_atomic_closure.
  exact (finite_registered_atomic_truth_condition_source_lexical_1_source_to_spec
    finite_registered_atomic_truth_condition_source_certificate
    (finite_registered_atomic_source_lexical_1_source_projected)).
Qed.

Theorem finite_registered_atomic_truth_condition_source_lexical_2_source_to_spec_projected :
  RegisteredLexicalApplicationTruth PropT (butter 2 (mods_cons 1 slowly (mods_cons 0 in_bathroom mods_nil)) John toast) ->
      fully_registered_truth_denotes concrete_registered_truth_conditions PropT (butter 2 (mods_cons 1 slowly (mods_cons 0 in_bathroom mods_nil)) John toast).
Proof.
  exact (finite_registered_atomic_truth_condition_source_lexical_2_source_to_spec
    finite_registered_atomic_truth_condition_source_certificate).
Qed.

Theorem finite_registered_atomic_truth_condition_source_lexical_2_source_to_kernel_projected :
  RegisteredLexicalApplicationTruth PropT (butter 2 (mods_cons 1 slowly (mods_cons 0 in_bathroom mods_nil)) John toast) ->
      concrete_registered_kernel_denotes concrete_registered_truth_kernel PropT (butter 2 (mods_cons 1 slowly (mods_cons 0 in_bathroom mods_nil)) John toast).
Proof.
  exact (finite_registered_atomic_kernel_alignment_lexical_2_source_to_kernel
    (finite_registered_atomic_truth_condition_source_alignment
      finite_registered_atomic_truth_condition_source_certificate)).
Qed.

Theorem finite_registered_atomic_truth_condition_source_lexical_2_atomic_projected :
  AtomicClosureTruth PropT (butter 2 (mods_cons 1 slowly (mods_cons 0 in_bathroom mods_nil)) John toast).
Proof.
  apply concrete_registered_truth_conditions_imply_atomic_closure.
  exact (finite_registered_atomic_truth_condition_source_lexical_2_source_to_spec
    finite_registered_atomic_truth_condition_source_certificate
    (finite_registered_atomic_source_lexical_2_source_projected)).
Qed.

Theorem finite_registered_atomic_truth_condition_source_lexical_3_source_to_spec_projected :
  forall x_theme : Food,
      RegisteredLexicalApplicationTruth Prop (eat 0 mods_nil John x_theme) ->
      fully_registered_truth_denotes concrete_registered_truth_conditions Prop (eat 0 mods_nil John x_theme).
Proof.
  exact (finite_registered_atomic_truth_condition_source_lexical_3_source_to_spec
    finite_registered_atomic_truth_condition_source_certificate).
Qed.

Theorem finite_registered_atomic_truth_condition_source_lexical_3_source_to_kernel_projected :
  forall x_theme : Food,
      RegisteredLexicalApplicationTruth Prop (eat 0 mods_nil John x_theme) ->
      concrete_registered_kernel_denotes concrete_registered_truth_kernel Prop (eat 0 mods_nil John x_theme).
Proof.
  exact (finite_registered_atomic_kernel_alignment_lexical_3_source_to_kernel
    (finite_registered_atomic_truth_condition_source_alignment
      finite_registered_atomic_truth_condition_source_certificate)).
Qed.

Theorem finite_registered_atomic_truth_condition_source_lexical_3_atomic_projected :
  forall x_theme : Food,
      AtomicClosureTruth Prop (eat 0 mods_nil John x_theme).
Proof.
  intros x_theme.
  apply concrete_registered_truth_conditions_imply_atomic_closure.
  exact (finite_registered_atomic_truth_condition_source_lexical_3_source_to_spec
    finite_registered_atomic_truth_condition_source_certificate
    x_theme
    (finite_registered_atomic_source_lexical_3_source_projected x_theme)).
Qed.

Theorem finite_registered_atomic_truth_condition_source_lexical_4_source_to_spec_projected :
  RegisteredLexicalApplicationTruth PropT (knock 0 mods_nil John) ->
      fully_registered_truth_denotes concrete_registered_truth_conditions PropT (knock 0 mods_nil John).
Proof.
  exact (finite_registered_atomic_truth_condition_source_lexical_4_source_to_spec
    finite_registered_atomic_truth_condition_source_certificate).
Qed.

Theorem finite_registered_atomic_truth_condition_source_lexical_4_source_to_kernel_projected :
  RegisteredLexicalApplicationTruth PropT (knock 0 mods_nil John) ->
      concrete_registered_kernel_denotes concrete_registered_truth_kernel PropT (knock 0 mods_nil John).
Proof.
  exact (finite_registered_atomic_kernel_alignment_lexical_4_source_to_kernel
    (finite_registered_atomic_truth_condition_source_alignment
      finite_registered_atomic_truth_condition_source_certificate)).
Qed.

Theorem finite_registered_atomic_truth_condition_source_lexical_4_atomic_projected :
  AtomicClosureTruth PropT (knock 0 mods_nil John).
Proof.
  apply concrete_registered_truth_conditions_imply_atomic_closure.
  exact (finite_registered_atomic_truth_condition_source_lexical_4_source_to_spec
    finite_registered_atomic_truth_condition_source_certificate
    (finite_registered_atomic_source_lexical_4_source_projected)).
Qed.

Theorem finite_registered_atomic_truth_condition_source_transition_1_source_to_spec_projected :
  RegisteredStateTransitionTruth vase integrity_scale intact broken ->
      fully_registered_truth_denotes concrete_registered_truth_conditions TransitionT (Transition vase integrity_scale intact broken).
Proof.
  exact (finite_registered_atomic_truth_condition_source_transition_1_source_to_spec
    finite_registered_atomic_truth_condition_source_certificate).
Qed.

Theorem finite_registered_atomic_truth_condition_source_transition_1_source_to_kernel_projected :
  RegisteredStateTransitionTruth vase integrity_scale intact broken ->
      concrete_registered_kernel_denotes concrete_registered_truth_kernel TransitionT (Transition vase integrity_scale intact broken).
Proof.
  exact (finite_registered_atomic_kernel_alignment_transition_1_source_to_kernel
    (finite_registered_atomic_truth_condition_source_alignment
      finite_registered_atomic_truth_condition_source_certificate)).
Qed.

Theorem finite_registered_atomic_truth_condition_source_transition_1_atomic_projected :
  AtomicClosureTruth TransitionT (Transition vase integrity_scale intact broken).
Proof.
  apply concrete_registered_truth_conditions_imply_atomic_closure.
  exact (finite_registered_atomic_truth_condition_source_transition_1_source_to_spec
    finite_registered_atomic_truth_condition_source_certificate
    (finite_registered_atomic_source_transition_1_source_projected)).
Qed.

Check example_1.
Check example_1_semantic_preservation_obligation.
Check example_1_semantic_preservation_obligation_record.
Check example_1_semantic_preservation_obligation_is_prop.
Check example_1_semantic_preservation_target_matches.
Check example_1_semantic_preservation_proved.
Check example_1_model_interpretable.
Check example_1_syntax_directed_truth.
Check example_1_denotationally_sound.
Check example_1_truth_condition_sound.
Check example_1_tautological_truth_condition_sound.
Check example_1_structural_truth_condition_sound.
Check example_1_concrete_kernel_truth_condition_sound.
Check example_1_model_interpretable_truth_kernel_sound.
Check example_1_syntax_directed_truth_kernel_sound.
Check example_1_primitive_truth_kernel_sound.
Check example_1_atomic_closure_truth.
Check example_1_atomic_closure_truth_kernel_sound.
Check example_1_atomic_closure_truth_condition_sound.
Check example_1_atomic_closure_evidence_backed_truth_condition_sound.
Check example_1_transition_refined_atomic_closure_truth.
Check example_1_transition_refined_atomic_closure_sound.
Check example_1_transition_refined_registered_truth_condition_sound.
Check example_1_transition_refined_registered_truth_condition_atomic_sound.
Check example_1_fully_registered_atomic_closure_truth.
Check example_1_fully_registered_truth_condition_sound.
Check example_1_registered_lexical_truth_model_sound.
Check example_1_registered_lexical_truth_conditions_from_model_sound.
Check example_1_concrete_registered_truth.
Check example_1_concrete_registered_truth_kernel_sound.
Check example_1_concrete_registered_truth_conditions_from_kernel_sound.
Check example_1_concrete_registered_truth_conditions_from_kernel_atomic_sound.
Check example_1_concrete_registered_truth_condition_sound.
Check example_1_concrete_registered_truth_condition_atomic_sound.
Check example_1_concrete_registered_evidence_backed_truth_condition_sound.
Check example_1_concrete_registered_evidence_backed_truth_condition_atomic_sound.
Check concrete_registered_evidence_backed_example_1_truth_instance_atomic_sound.
Check concrete_registered_example_1_truth_instance_atomic_sound.
Check concrete_registered_kernel_example_1_truth_instance_atomic_sound.
Check concrete_registered_truth_condition_route_example_1_direct_atomic_sound.
Check concrete_registered_truth_condition_route_example_1_evidence_atomic_sound.
Check concrete_registered_truth_condition_route_example_1_kernel_atomic_sound.
Check concrete_registered_truth_condition_route_example_1_agreement_direct_atomic_sound.
Check concrete_registered_truth_condition_route_example_1_agreement_evidence_atomic_sound.
Check concrete_registered_truth_condition_route_example_1_agreement_kernel_atomic_sound.
Check independent_registered_truth_condition_sources_example_1_atomic_sound.
Check independent_registered_truth_condition_clause_example_1_atomic_sound.
Check independent_registered_truth_condition_clause_coverage_example_1_atomic_sound.
Check example_1_fully_registered_truth_condition_atomic_sound.
Check registered_example_1_truth_instance_atomic_sound.
Check finite_registered_truth_condition_ledger_example_1_suite_atomic_sound.
Check finite_registered_truth_condition_ledger_example_1_registered_atomic_sound.
Check finite_registered_truth_condition_ledger_example_1_concrete_atomic_sound.
Check finite_registered_truth_condition_ledger_example_1_kernel_atomic_sound.
Check finite_registered_truth_condition_completion_example_1_registered_atomic_sound.
Check finite_registered_truth_condition_completion_example_1_direct_atomic_sound.
Check finite_registered_truth_condition_completion_example_1_evidence_atomic_sound.
Check finite_registered_truth_condition_completion_example_1_kernel_atomic_sound.
Check finite_registered_truth_condition_completion_example_1_source_atomic_sound.
Check finite_registered_truth_condition_completion_example_1_suite_atomic_sound.
Check finite_registered_truth_condition_component_coverage_example_1_atomic_sound.
Check example_2.
Check example_2_semantic_preservation_obligation.
Check example_2_semantic_preservation_obligation_record.
Check example_2_semantic_preservation_obligation_is_prop.
Check example_2_semantic_preservation_target_matches.
Check example_2_semantic_preservation_proved.
Check example_2_model_interpretable.
Check example_2_syntax_directed_truth.
Check example_2_denotationally_sound.
Check example_2_truth_condition_sound.
Check example_2_tautological_truth_condition_sound.
Check example_2_structural_truth_condition_sound.
Check example_2_concrete_kernel_truth_condition_sound.
Check example_2_model_interpretable_truth_kernel_sound.
Check example_2_syntax_directed_truth_kernel_sound.
Check example_2_primitive_truth_kernel_sound.
Check example_2_atomic_closure_truth.
Check example_2_atomic_closure_truth_kernel_sound.
Check example_2_atomic_closure_truth_condition_sound.
Check example_2_atomic_closure_evidence_backed_truth_condition_sound.
Check example_2_transition_refined_atomic_closure_truth.
Check example_2_transition_refined_atomic_closure_sound.
Check example_2_transition_refined_registered_truth_condition_sound.
Check example_2_transition_refined_registered_truth_condition_atomic_sound.
Check example_2_fully_registered_atomic_closure_truth.
Check example_2_fully_registered_truth_condition_sound.
Check example_2_registered_lexical_truth_model_sound.
Check example_2_registered_lexical_truth_conditions_from_model_sound.
Check example_2_concrete_registered_truth.
Check example_2_concrete_registered_truth_kernel_sound.
Check example_2_concrete_registered_truth_conditions_from_kernel_sound.
Check example_2_concrete_registered_truth_conditions_from_kernel_atomic_sound.
Check example_2_concrete_registered_truth_condition_sound.
Check example_2_concrete_registered_truth_condition_atomic_sound.
Check example_2_concrete_registered_evidence_backed_truth_condition_sound.
Check example_2_concrete_registered_evidence_backed_truth_condition_atomic_sound.
Check concrete_registered_evidence_backed_example_2_truth_instance_atomic_sound.
Check concrete_registered_example_2_truth_instance_atomic_sound.
Check concrete_registered_kernel_example_2_truth_instance_atomic_sound.
Check concrete_registered_truth_condition_route_example_2_direct_atomic_sound.
Check concrete_registered_truth_condition_route_example_2_evidence_atomic_sound.
Check concrete_registered_truth_condition_route_example_2_kernel_atomic_sound.
Check concrete_registered_truth_condition_route_example_2_agreement_direct_atomic_sound.
Check concrete_registered_truth_condition_route_example_2_agreement_evidence_atomic_sound.
Check concrete_registered_truth_condition_route_example_2_agreement_kernel_atomic_sound.
Check independent_registered_truth_condition_sources_example_2_atomic_sound.
Check independent_registered_truth_condition_clause_example_2_atomic_sound.
Check independent_registered_truth_condition_clause_coverage_example_2_atomic_sound.
Check example_2_fully_registered_truth_condition_atomic_sound.
Check registered_example_2_truth_instance_atomic_sound.
Check finite_registered_truth_condition_ledger_example_2_suite_atomic_sound.
Check finite_registered_truth_condition_ledger_example_2_registered_atomic_sound.
Check finite_registered_truth_condition_ledger_example_2_concrete_atomic_sound.
Check finite_registered_truth_condition_ledger_example_2_kernel_atomic_sound.
Check finite_registered_truth_condition_completion_example_2_registered_atomic_sound.
Check finite_registered_truth_condition_completion_example_2_direct_atomic_sound.
Check finite_registered_truth_condition_completion_example_2_evidence_atomic_sound.
Check finite_registered_truth_condition_completion_example_2_kernel_atomic_sound.
Check finite_registered_truth_condition_completion_example_2_source_atomic_sound.
Check finite_registered_truth_condition_completion_example_2_suite_atomic_sound.
Check finite_registered_truth_condition_component_coverage_example_2_atomic_sound.
Check example_3.
Check example_3_semantic_preservation_obligation.
Check example_3_semantic_preservation_obligation_record.
Check example_3_semantic_preservation_obligation_is_prop.
Check example_3_semantic_preservation_target_matches.
Check example_3_semantic_preservation_proved.
Check example_3_model_interpretable.
Check example_3_syntax_directed_truth.
Check example_3_denotationally_sound.
Check example_3_truth_condition_sound.
Check example_3_tautological_truth_condition_sound.
Check example_3_structural_truth_condition_sound.
Check example_3_concrete_kernel_truth_condition_sound.
Check example_3_model_interpretable_truth_kernel_sound.
Check example_3_syntax_directed_truth_kernel_sound.
Check example_3_primitive_truth_kernel_sound.
Check example_3_atomic_closure_truth.
Check example_3_atomic_closure_truth_kernel_sound.
Check example_3_atomic_closure_truth_condition_sound.
Check example_3_atomic_closure_evidence_backed_truth_condition_sound.
Check example_3_transition_refined_atomic_closure_truth.
Check example_3_transition_refined_atomic_closure_sound.
Check example_3_transition_refined_registered_truth_condition_sound.
Check example_3_transition_refined_registered_truth_condition_atomic_sound.
Check example_3_fully_registered_atomic_closure_truth.
Check example_3_fully_registered_truth_condition_sound.
Check example_3_registered_lexical_truth_model_sound.
Check example_3_registered_lexical_truth_conditions_from_model_sound.
Check example_3_concrete_registered_truth.
Check example_3_concrete_registered_truth_kernel_sound.
Check example_3_concrete_registered_truth_conditions_from_kernel_sound.
Check example_3_concrete_registered_truth_conditions_from_kernel_atomic_sound.
Check example_3_concrete_registered_truth_condition_sound.
Check example_3_concrete_registered_truth_condition_atomic_sound.
Check example_3_concrete_registered_evidence_backed_truth_condition_sound.
Check example_3_concrete_registered_evidence_backed_truth_condition_atomic_sound.
Check concrete_registered_evidence_backed_example_3_truth_instance_atomic_sound.
Check concrete_registered_example_3_truth_instance_atomic_sound.
Check concrete_registered_kernel_example_3_truth_instance_atomic_sound.
Check concrete_registered_truth_condition_route_example_3_direct_atomic_sound.
Check concrete_registered_truth_condition_route_example_3_evidence_atomic_sound.
Check concrete_registered_truth_condition_route_example_3_kernel_atomic_sound.
Check concrete_registered_truth_condition_route_example_3_agreement_direct_atomic_sound.
Check concrete_registered_truth_condition_route_example_3_agreement_evidence_atomic_sound.
Check concrete_registered_truth_condition_route_example_3_agreement_kernel_atomic_sound.
Check independent_registered_truth_condition_sources_example_3_atomic_sound.
Check independent_registered_truth_condition_clause_example_3_atomic_sound.
Check independent_registered_truth_condition_clause_coverage_example_3_atomic_sound.
Check example_3_fully_registered_truth_condition_atomic_sound.
Check registered_example_3_truth_instance_atomic_sound.
Check finite_registered_truth_condition_ledger_example_3_suite_atomic_sound.
Check finite_registered_truth_condition_ledger_example_3_registered_atomic_sound.
Check finite_registered_truth_condition_ledger_example_3_concrete_atomic_sound.
Check finite_registered_truth_condition_ledger_example_3_kernel_atomic_sound.
Check finite_registered_truth_condition_completion_example_3_registered_atomic_sound.
Check finite_registered_truth_condition_completion_example_3_direct_atomic_sound.
Check finite_registered_truth_condition_completion_example_3_evidence_atomic_sound.
Check finite_registered_truth_condition_completion_example_3_kernel_atomic_sound.
Check finite_registered_truth_condition_completion_example_3_source_atomic_sound.
Check finite_registered_truth_condition_completion_example_3_suite_atomic_sound.
Check finite_registered_truth_condition_component_coverage_example_3_atomic_sound.
Check example_4.
Check example_4_semantic_preservation_obligation.
Check example_4_semantic_preservation_obligation_record.
Check example_4_semantic_preservation_obligation_is_prop.
Check example_4_semantic_preservation_target_matches.
Check example_4_semantic_preservation_proved.
Check example_4_model_interpretable.
Check example_4_syntax_directed_truth.
Check example_4_denotationally_sound.
Check example_4_truth_condition_sound.
Check example_4_tautological_truth_condition_sound.
Check example_4_structural_truth_condition_sound.
Check example_4_concrete_kernel_truth_condition_sound.
Check example_4_model_interpretable_truth_kernel_sound.
Check example_4_syntax_directed_truth_kernel_sound.
Check example_4_primitive_truth_kernel_sound.
Check example_4_atomic_closure_truth.
Check example_4_atomic_closure_truth_kernel_sound.
Check example_4_atomic_closure_truth_condition_sound.
Check example_4_atomic_closure_evidence_backed_truth_condition_sound.
Check example_4_transition_refined_atomic_closure_truth.
Check example_4_transition_refined_atomic_closure_sound.
Check example_4_transition_refined_registered_truth_condition_sound.
Check example_4_transition_refined_registered_truth_condition_atomic_sound.
Check example_4_fully_registered_atomic_closure_truth.
Check example_4_fully_registered_truth_condition_sound.
Check example_4_registered_lexical_truth_model_sound.
Check example_4_registered_lexical_truth_conditions_from_model_sound.
Check example_4_concrete_registered_truth.
Check example_4_concrete_registered_truth_kernel_sound.
Check example_4_concrete_registered_truth_conditions_from_kernel_sound.
Check example_4_concrete_registered_truth_conditions_from_kernel_atomic_sound.
Check example_4_concrete_registered_truth_condition_sound.
Check example_4_concrete_registered_truth_condition_atomic_sound.
Check example_4_concrete_registered_evidence_backed_truth_condition_sound.
Check example_4_concrete_registered_evidence_backed_truth_condition_atomic_sound.
Check concrete_registered_evidence_backed_example_4_truth_instance_atomic_sound.
Check concrete_registered_example_4_truth_instance_atomic_sound.
Check concrete_registered_kernel_example_4_truth_instance_atomic_sound.
Check concrete_registered_truth_condition_route_example_4_direct_atomic_sound.
Check concrete_registered_truth_condition_route_example_4_evidence_atomic_sound.
Check concrete_registered_truth_condition_route_example_4_kernel_atomic_sound.
Check concrete_registered_truth_condition_route_example_4_agreement_direct_atomic_sound.
Check concrete_registered_truth_condition_route_example_4_agreement_evidence_atomic_sound.
Check concrete_registered_truth_condition_route_example_4_agreement_kernel_atomic_sound.
Check independent_registered_truth_condition_sources_example_4_atomic_sound.
Check independent_registered_truth_condition_clause_example_4_atomic_sound.
Check independent_registered_truth_condition_clause_coverage_example_4_atomic_sound.
Check example_4_fully_registered_truth_condition_atomic_sound.
Check registered_example_4_truth_instance_atomic_sound.
Check finite_registered_truth_condition_ledger_example_4_suite_atomic_sound.
Check finite_registered_truth_condition_ledger_example_4_registered_atomic_sound.
Check finite_registered_truth_condition_ledger_example_4_concrete_atomic_sound.
Check finite_registered_truth_condition_ledger_example_4_kernel_atomic_sound.
Check finite_registered_truth_condition_completion_example_4_registered_atomic_sound.
Check finite_registered_truth_condition_completion_example_4_direct_atomic_sound.
Check finite_registered_truth_condition_completion_example_4_evidence_atomic_sound.
Check finite_registered_truth_condition_completion_example_4_kernel_atomic_sound.
Check finite_registered_truth_condition_completion_example_4_source_atomic_sound.
Check finite_registered_truth_condition_completion_example_4_suite_atomic_sound.
Check finite_registered_truth_condition_component_coverage_example_4_atomic_sound.
Check independent_truth_condition_obligation_ledger.
Check independent_truth_condition_obligation_ledger_exists.
Check independent_truth_condition_obligation_ledger_induces_truth_conditions.
Check independent_truth_condition_obligation_ledger_truth_conditions_sound.
Check TruthEvidence.
Check truth_evidence_sound.
Check truth_evidence_intro.
Check EvidenceBackedTruthConditionSources.
Check concrete_kernel_from_evidence_sources.
Check evidence_backed_truth_condition_ledger.
Check evidence_backed_truth_condition_sources_induce_kernel.
Check evidence_backed_truth_condition_sources_induce_truth_conditions.
Check evidence_backed_truth_condition_sources_sound.
Check atomic_closure_evidence_backed_truth_sources.
Check atomic_closure_evidence_backed_truth_kernel.
Check atomic_closure_evidence_backed_truth_ledger.
Check atomic_closure_evidence_backed_truth_sources_exist.
Check atomic_closure_evidence_backed_truth_kernel_exists.
Check atomic_closure_evidence_backed_truth_ledger_exists.
Check atomic_closure_evidence_backed_truth_sources_sound.
Check registered_lexical_truth_model.
Check registered_lexical_truth_model_exists.
Check registered_lexical_truth_conditions_from_model.
Check registered_lexical_truth_conditions_from_model_exists.
Check concrete_registered_truth_basis.
Check concrete_registered_truth_basis_exists.
Check concrete_registered_atomic_model.
Check concrete_registered_atomic_model_exists.
Check concrete_registered_atomic_model_denotes_atomic_base_truth.
Check concrete_registered_truth_basis_denotes_atomic_base_truth.
Check concrete_registered_truth_conditions.
Check concrete_registered_truth_condition_spec_exists.
Check RegisteredEvidenceBackedTruthConditionSources.
Check fully_registered_truth_conditions_from_registered_evidence_sources.
Check registered_evidence_backed_truth_condition_sources_induce_fully_registered_truth_conditions.
Check concrete_registered_evidence_backed_truth_sources.
Check concrete_registered_evidence_backed_truth_conditions.
Check concrete_registered_evidence_backed_truth_sources_exist.
Check concrete_registered_evidence_backed_truth_conditions_exists.
Check concrete_registered_evidence_backed_truth_conditions_denote_concrete_registered.
Check concrete_registered_evidence_backed_truth_conditions_imply_atomic_closure.
Check concrete_registered_evidence_backed_truth_condition_model.
Check concrete_registered_evidence_backed_truth_condition_model_exists.
Check concrete_registered_evidence_backed_truth_condition_model_denote_spec.
Check concrete_registered_evidence_backed_truth_condition_model_spec_imply_atomic_closure.
Check concrete_registered_evidence_backed_example_truth_instances.
Check concrete_registered_evidence_backed_example_truth_instances_exists.
Check concrete_registered_compositional_model.
Check concrete_registered_compositional_model_exists.
Check concrete_registered_compositional_model_denotes_concrete_registered.
Check concrete_registered_compositional_model_imply_atomic_closure.
Check concrete_registered_compositional_model_repeat_clause.
Check concrete_registered_compositional_model_at_T_clause.
Check concrete_registered_compositional_model_cause_clause.
Check concrete_registered_truth_condition_model.
Check concrete_registered_truth_condition_model_exists.
Check concrete_registered_truth_condition_model_denote_spec.
Check concrete_registered_truth_condition_model_imply_atomic_closure.
Check concrete_registered_truth_condition_model_spec_imply_atomic_closure.
Check concrete_registered_truth_kernel.
Check concrete_registered_truth_kernel_exists.
Check concrete_registered_truth_conditions_from_kernel.
Check concrete_registered_truth_conditions_from_kernel_exists.
Check concrete_registered_example_truth_instances.
Check concrete_registered_example_truth_instances_exists.
Check concrete_registered_kernel_example_truth_instances.
Check concrete_registered_kernel_example_truth_instances_exists.
Check concrete_registered_truth_condition_route.
Check concrete_registered_truth_condition_route_exists.
Check concrete_registered_truth_condition_route_direct_spec_matches_model.
Check concrete_registered_truth_condition_route_evidence_spec_matches_model.
Check concrete_registered_truth_condition_route_kernel_spec_matches_kernel.
Check concrete_registered_truth_condition_route_direct_spec_sound.
Check concrete_registered_truth_condition_route_evidence_spec_sound.
Check concrete_registered_truth_condition_route_kernel_spec_sound.
Check concrete_registered_truth_condition_route_example_agreement.
Check concrete_registered_truth_condition_route_example_agreement_exists.
Check concrete_registered_truth_condition_route_example_agreement_route_matches.
Check IndependentRegisteredTruthConditionSources.
Check independent_registered_truth_condition_sources.
Check independent_registered_truth_condition_sources_exist.
Check independent_registered_truth_condition_sources_spec_matches_route.
Check independent_registered_truth_condition_sources_agreement_matches_route.
Check independent_registered_truth_condition_sources_spec_sound.
Check IndependentRegisteredTruthConditionClauseInstances.
Check independent_registered_truth_condition_clause_instances.
Check independent_registered_truth_condition_clause_instances_exists.
Check independent_registered_truth_condition_clause_spec_matches_source.
Check independent_registered_truth_condition_clause_lexical_application_instance.
Check independent_registered_truth_condition_clause_sigma_Entity_instance.
Check independent_registered_truth_condition_clause_repeat_instance.
Check independent_registered_truth_condition_clause_at_T_instance.
Check independent_registered_truth_condition_clause_not_T_instance.
Check independent_registered_truth_condition_clause_transition_instance.
Check independent_registered_truth_condition_clause_cause_instance.
Check independent_registered_truth_condition_clause_spec_sound.
Check IndependentRegisteredTruthConditionClauseCoverage.
Check independent_registered_truth_condition_clause_coverage.
Check independent_registered_truth_condition_clause_coverage_exists.
Check independent_registered_truth_condition_clause_coverage_instances_match.
Check independent_registered_truth_condition_clause_coverage_spec_sound.
Check IndependentRegisteredLexicalTruthConditionInstances.
Check independent_registered_lexical_truth_condition_instances.
Check independent_registered_lexical_truth_condition_instances_exists.
Check independent_registered_lexical_truth_condition_coverage_matches.
Check independent_registered_lexical_truth_condition_application_instance.
Check independent_registered_lexical_truth_condition_spec_sound.
Check IndependentRegisteredTemporalTruthConditionInstances.
Check independent_registered_temporal_truth_condition_instances.
Check independent_registered_temporal_truth_condition_instances_exists.
Check independent_registered_temporal_truth_condition_coverage_matches.
Check independent_registered_temporal_truth_condition_at_T_instance.
Check independent_registered_temporal_truth_condition_during_T_instance.
Check independent_registered_temporal_truth_condition_before_T_instance.
Check independent_registered_temporal_truth_condition_after_T_instance.
Check independent_registered_temporal_truth_condition_until_T_instance.
Check independent_registered_temporal_truth_condition_since_T_instance.
Check independent_registered_temporal_truth_condition_spec_sound.
Check IndependentRegisteredSigmaTruthConditionInstances.
Check independent_registered_sigma_truth_condition_instances.
Check independent_registered_sigma_truth_condition_instances_exists.
Check independent_registered_sigma_truth_condition_coverage_matches.
Check independent_registered_sigma_truth_condition_sigma_Entity_instance.
Check independent_registered_sigma_truth_condition_spec_sound.
Check IndependentRegisteredRepeatTruthConditionInstances.
Check independent_registered_repeat_truth_condition_instances.
Check independent_registered_repeat_truth_condition_instances_exists.
Check independent_registered_repeat_truth_condition_coverage_matches.
Check independent_registered_repeat_truth_condition_repeat_instance.
Check independent_registered_repeat_truth_condition_spec_sound.
Check IndependentRegisteredPolarityTruthConditionInstances.
Check independent_registered_polarity_truth_condition_instances.
Check independent_registered_polarity_truth_condition_instances_exists.
Check independent_registered_polarity_truth_condition_coverage_matches.
Check independent_registered_polarity_truth_condition_not_T_instance.
Check independent_registered_polarity_truth_condition_spec_sound.
Check IndependentRegisteredTransitionCauseTruthConditionInstances.
Check independent_registered_transition_cause_truth_condition_instances.
Check independent_registered_transition_cause_truth_condition_instances_exists.
Check independent_registered_transition_cause_truth_condition_coverage_matches.
Check independent_registered_transition_cause_truth_condition_transition_instance.
Check independent_registered_transition_cause_truth_condition_cause_instance.
Check independent_registered_transition_cause_truth_condition_spec_sound.
Check IndependentRegisteredTruthConditionInstanceSuite.
Check independent_registered_truth_condition_instance_suite.
Check independent_registered_truth_condition_instance_suite_exists.
Check independent_registered_truth_condition_instance_suite_lexical_matches.
Check independent_registered_truth_condition_instance_suite_temporal_matches.
Check independent_registered_truth_condition_instance_suite_sigma_matches.
Check independent_registered_truth_condition_instance_suite_repeat_matches.
Check independent_registered_truth_condition_instance_suite_polarity_matches.
Check independent_registered_truth_condition_instance_suite_transition_cause_matches.
Check independent_registered_truth_condition_instance_suite_spec_sound.
Check IndependentRegisteredTruthConditionInstanceSuiteExamplePackage.
Check independent_registered_truth_condition_instance_suite_example_package.
Check independent_registered_truth_condition_instance_suite_example_package_exists.
Check independent_registered_truth_condition_instance_suite_example_package_suite_matches.
Check independent_registered_truth_condition_instance_suite_example_1_atomic_sound.
Check independent_registered_truth_condition_instance_suite_example_2_atomic_sound.
Check independent_registered_truth_condition_instance_suite_example_3_atomic_sound.
Check independent_registered_truth_condition_instance_suite_example_4_atomic_sound.
Check registered_example_truth_instances.
Check registered_example_truth_instances_exists.
Check FiniteRegisteredTruthConditionInstanceLedger.
Check finite_registered_truth_condition_instance_ledger.
Check finite_registered_truth_condition_instance_ledger_exists.
Check finite_registered_truth_condition_instance_ledger_route_matches.
Check finite_registered_truth_condition_instance_ledger_sources_matches.
Check finite_registered_truth_condition_instance_ledger_suite_matches.
Check finite_registered_truth_condition_instance_ledger_suite_examples_matches.
Check finite_registered_truth_condition_instance_ledger_registered_examples_matches.
Check finite_registered_truth_condition_instance_ledger_concrete_examples_matches.
Check finite_registered_truth_condition_instance_ledger_kernel_examples_matches.
Check FiniteRegisteredTruthConditionCompletionCertificate.
Check finite_registered_truth_condition_completion_certificate.
Check finite_registered_truth_condition_completion_certificate_exists.
Check finite_registered_truth_condition_completion_ledger_matches.
Check finite_registered_truth_condition_completion_registered_spec_sound.
Check finite_registered_truth_condition_completion_direct_spec_sound.
Check finite_registered_truth_condition_completion_evidence_spec_sound.
Check finite_registered_truth_condition_completion_kernel_spec_sound.
Check finite_registered_truth_condition_completion_source_spec_sound.
Check finite_registered_truth_condition_completion_suite_spec_sound.
Check FiniteRegisteredTruthConditionComponentCoverageCertificate.
Check finite_registered_truth_condition_component_coverage_certificate.
Check finite_registered_truth_condition_component_coverage_certificate_exists.
Check finite_registered_truth_condition_component_completion_matches.
Check finite_registered_truth_condition_component_lexical_matches.
Check finite_registered_truth_condition_component_lexical_spec_sound.
Check finite_registered_truth_condition_component_temporal_matches.
Check finite_registered_truth_condition_component_temporal_spec_sound.
Check finite_registered_truth_condition_component_sigma_matches.
Check finite_registered_truth_condition_component_sigma_spec_sound.
Check finite_registered_truth_condition_component_repeat_matches.
Check finite_registered_truth_condition_component_repeat_spec_sound.
Check finite_registered_truth_condition_component_polarity_matches.
Check finite_registered_truth_condition_component_polarity_spec_sound.
Check finite_registered_truth_condition_component_transition_cause_matches.
Check finite_registered_truth_condition_component_transition_cause_spec_sound.
Check finite_registered_truth_condition_component_suite_matches.
Check finite_registered_truth_condition_component_suite_spec_sound.
Check FiniteRegisteredAtomicWitnessCertificate.
Check finite_registered_atomic_witness_certificate.
Check finite_registered_atomic_witness_certificate_exists.
Check finite_registered_atomic_witness_basis_matches.
Check finite_registered_atomic_witness_lexical_1_concrete_projected.
Check finite_registered_atomic_witness_lexical_1_base_projected.
Check finite_registered_atomic_witness_lexical_1_closure_projected.
Check finite_registered_atomic_witness_lexical_2_concrete_projected.
Check finite_registered_atomic_witness_lexical_2_base_projected.
Check finite_registered_atomic_witness_lexical_2_closure_projected.
Check finite_registered_atomic_witness_lexical_3_concrete_projected.
Check finite_registered_atomic_witness_lexical_3_base_projected.
Check finite_registered_atomic_witness_lexical_3_closure_projected.
Check finite_registered_atomic_witness_lexical_4_concrete_projected.
Check finite_registered_atomic_witness_lexical_4_base_projected.
Check finite_registered_atomic_witness_lexical_4_closure_projected.
Check finite_registered_atomic_witness_transition_1_concrete_projected.
Check finite_registered_atomic_witness_transition_1_base_projected.
Check finite_registered_atomic_witness_transition_1_closure_projected.
Check FiniteRegisteredAtomicSourceDisciplineCertificate.
Check finite_registered_atomic_source_discipline_certificate.
Check finite_registered_atomic_source_discipline_certificate_exists.
Check finite_registered_atomic_source_witness_matches.
Check finite_registered_atomic_source_lexical_1_source_projected.
Check finite_registered_atomic_source_lexical_1_concrete_from_source_projected.
Check finite_registered_atomic_source_lexical_1_base_from_source_projected.
Check finite_registered_atomic_source_lexical_1_closure_from_source_projected.
Check finite_registered_atomic_source_lexical_2_source_projected.
Check finite_registered_atomic_source_lexical_2_concrete_from_source_projected.
Check finite_registered_atomic_source_lexical_2_base_from_source_projected.
Check finite_registered_atomic_source_lexical_2_closure_from_source_projected.
Check finite_registered_atomic_source_lexical_3_source_projected.
Check finite_registered_atomic_source_lexical_3_concrete_from_source_projected.
Check finite_registered_atomic_source_lexical_3_base_from_source_projected.
Check finite_registered_atomic_source_lexical_3_closure_from_source_projected.
Check finite_registered_atomic_source_lexical_4_source_projected.
Check finite_registered_atomic_source_lexical_4_concrete_from_source_projected.
Check finite_registered_atomic_source_lexical_4_base_from_source_projected.
Check finite_registered_atomic_source_lexical_4_closure_from_source_projected.
Check finite_registered_atomic_source_transition_1_source_projected.
Check finite_registered_atomic_source_transition_1_concrete_from_source_projected.
Check finite_registered_atomic_source_transition_1_base_from_source_projected.
Check finite_registered_atomic_source_transition_1_closure_from_source_projected.
Check finite_registered_atomic_kernel_denotes_imply_atomic_closure.
Check FiniteRegisteredAtomicKernelAlignmentCertificate.
Check finite_registered_atomic_kernel_alignment_certificate.
Check finite_registered_atomic_kernel_alignment_certificate_exists.
Check finite_registered_atomic_kernel_alignment_source_matches.
Check finite_registered_atomic_kernel_alignment_kernel_matches.
Check finite_registered_atomic_kernel_alignment_sound_projected.
Check finite_registered_atomic_kernel_alignment_lexical_1_source_to_kernel_projected.
Check finite_registered_atomic_kernel_alignment_lexical_1_atomic_projected.
Check finite_registered_atomic_kernel_alignment_lexical_2_source_to_kernel_projected.
Check finite_registered_atomic_kernel_alignment_lexical_2_atomic_projected.
Check finite_registered_atomic_kernel_alignment_lexical_3_source_to_kernel_projected.
Check finite_registered_atomic_kernel_alignment_lexical_3_atomic_projected.
Check finite_registered_atomic_kernel_alignment_lexical_4_source_to_kernel_projected.
Check finite_registered_atomic_kernel_alignment_lexical_4_atomic_projected.
Check finite_registered_atomic_kernel_alignment_transition_1_source_to_kernel_projected.
Check finite_registered_atomic_kernel_alignment_transition_1_atomic_projected.
Check FiniteRegisteredAtomicTruthConditionSourceCertificate.
Check finite_registered_atomic_truth_condition_source_certificate.
Check finite_registered_atomic_truth_condition_source_certificate_exists.
Check finite_registered_atomic_truth_condition_source_alignment_matches.
Check finite_registered_atomic_truth_condition_source_spec_matches.
Check finite_registered_atomic_truth_condition_source_sound_projected.
Check finite_registered_atomic_truth_condition_source_lexical_1_source_to_spec_projected.
Check finite_registered_atomic_truth_condition_source_lexical_1_source_to_kernel_projected.
Check finite_registered_atomic_truth_condition_source_lexical_1_atomic_projected.
Check finite_registered_atomic_truth_condition_source_lexical_2_source_to_spec_projected.
Check finite_registered_atomic_truth_condition_source_lexical_2_source_to_kernel_projected.
Check finite_registered_atomic_truth_condition_source_lexical_2_atomic_projected.
Check finite_registered_atomic_truth_condition_source_lexical_3_source_to_spec_projected.
Check finite_registered_atomic_truth_condition_source_lexical_3_source_to_kernel_projected.
Check finite_registered_atomic_truth_condition_source_lexical_3_atomic_projected.
Check finite_registered_atomic_truth_condition_source_lexical_4_source_to_spec_projected.
Check finite_registered_atomic_truth_condition_source_lexical_4_source_to_kernel_projected.
Check finite_registered_atomic_truth_condition_source_lexical_4_atomic_projected.
Check finite_registered_atomic_truth_condition_source_transition_1_source_to_spec_projected.
Check finite_registered_atomic_truth_condition_source_transition_1_source_to_kernel_projected.
Check finite_registered_atomic_truth_condition_source_transition_1_atomic_projected.
