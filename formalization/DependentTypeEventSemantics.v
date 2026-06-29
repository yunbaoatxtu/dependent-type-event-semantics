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

Theorem semantic_preservation_model_interpretable :
  forall A : Type, forall term : A,
    SemanticPreservation A term -> ModelInterpretable A term.
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

Check example_1.
Check example_1_semantic_preservation_obligation.
Check example_1_semantic_preservation_obligation_record.
Check example_1_semantic_preservation_obligation_is_prop.
Check example_1_semantic_preservation_target_matches.
Check example_1_semantic_preservation_proved.
Check example_1_model_interpretable.
Check example_1_denotationally_sound.
Check example_1_truth_condition_sound.
Check example_2.
Check example_2_semantic_preservation_obligation.
Check example_2_semantic_preservation_obligation_record.
Check example_2_semantic_preservation_obligation_is_prop.
Check example_2_semantic_preservation_target_matches.
Check example_2_semantic_preservation_proved.
Check example_2_model_interpretable.
Check example_2_denotationally_sound.
Check example_2_truth_condition_sound.
Check example_3.
Check example_3_semantic_preservation_obligation.
Check example_3_semantic_preservation_obligation_record.
Check example_3_semantic_preservation_obligation_is_prop.
Check example_3_semantic_preservation_target_matches.
Check example_3_semantic_preservation_proved.
Check example_3_model_interpretable.
Check example_3_denotationally_sound.
Check example_3_truth_condition_sound.
Check example_4.
Check example_4_semantic_preservation_obligation.
Check example_4_semantic_preservation_obligation_record.
Check example_4_semantic_preservation_obligation_is_prop.
Check example_4_semantic_preservation_target_matches.
Check example_4_semantic_preservation_proved.
Check example_4_model_interpretable.
Check example_4_denotationally_sound.
Check example_4_truth_condition_sound.
