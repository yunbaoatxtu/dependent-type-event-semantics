(* Auto-generated shallow embedding for dependent-type event semantics. *)
(* This file is an interface scaffold, not a complete proof development. *)

Parameter Entity : Type.
Parameter Food : Type.
Parameter PropT : Type.
Parameter TransitionT : Type.
Definition Adv : Type := (Entity -> PropT) -> Entity -> PropT.

Parameter John : Entity.
Parameter broken : Entity.
Parameter noon : Entity.
Parameter toast : Entity.
Parameter unknown_state : Entity.
Parameter vase : Entity.
Parameter in_bathroom : Adv.
Parameter slowly : Adv.

Parameter repeat : nat -> PropT -> PropT.
Parameter at_T : Entity -> PropT -> PropT.
Parameter during_T : Entity -> PropT -> PropT.
Parameter before_T : Entity -> PropT -> PropT.
Parameter after_T : Entity -> PropT -> PropT.
Parameter until_T : Entity -> PropT -> PropT.
Parameter since_T : Entity -> PropT -> PropT.
Parameter Transition : Entity -> Entity -> Entity -> TransitionT.
Parameter Cause : Entity -> TransitionT -> PropT.
Parameter break : nat -> Entity -> Entity -> PropT.
Parameter butter : nat -> Adv -> Adv -> Entity -> Entity -> PropT.
Parameter eat : nat -> Entity -> Food -> Prop.
Parameter knock : nat -> Entity -> PropT.

Definition example_1 : PropT := (at_T noon (butter 2 slowly in_bathroom John toast)).
Definition example_2 : Prop := (exists x_theme : Food, (eat 0 John x_theme)).
Definition example_3 : PropT := (repeat 2 (knock 0 John)).
Definition example_4 : PropT := (Cause John (Transition vase unknown_state broken)).

Check example_1.
Check example_2.
Check example_3.
Check example_4.
