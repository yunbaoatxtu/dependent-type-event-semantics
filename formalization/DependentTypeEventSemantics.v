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

Check example_1.
Check example_1_semantic_preservation_obligation.
Check example_1_semantic_preservation_obligation_record.
Check example_1_semantic_preservation_obligation_is_prop.
Check example_1_semantic_preservation_target_matches.
Check example_1_semantic_preservation_proved.
Check example_2.
Check example_2_semantic_preservation_obligation.
Check example_2_semantic_preservation_obligation_record.
Check example_2_semantic_preservation_obligation_is_prop.
Check example_2_semantic_preservation_target_matches.
Check example_2_semantic_preservation_proved.
Check example_3.
Check example_3_semantic_preservation_obligation.
Check example_3_semantic_preservation_obligation_record.
Check example_3_semantic_preservation_obligation_is_prop.
Check example_3_semantic_preservation_target_matches.
Check example_3_semantic_preservation_proved.
Check example_4.
Check example_4_semantic_preservation_obligation.
Check example_4_semantic_preservation_obligation_record.
Check example_4_semantic_preservation_obligation_is_prop.
Check example_4_semantic_preservation_target_matches.
Check example_4_semantic_preservation_proved.
