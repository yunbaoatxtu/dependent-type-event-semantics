-- Auto-generated shallow embedding for dependent-type event semantics.
-- This file is an interface scaffold, not a complete proof development.

constant Entity : Type
constant Food : Type
constant PropT : Type
constant TransitionT : Type
def Adv : Type := (Entity -> PropT) -> Entity -> PropT

constant John : Entity
constant broken : Entity
constant noon : Entity
constant toast : Entity
constant unknown_state : Entity
constant vase : Entity
constant in_bathroom : Adv
constant slowly : Adv

constant repeat : Nat -> PropT -> PropT
constant at_T : Entity -> PropT -> PropT
constant during_T : Entity -> PropT -> PropT
constant before_T : Entity -> PropT -> PropT
constant after_T : Entity -> PropT -> PropT
constant until_T : Entity -> PropT -> PropT
constant since_T : Entity -> PropT -> PropT
constant Transition : Entity -> Entity -> Entity -> TransitionT
constant Cause : Entity -> TransitionT -> PropT
constant break : Nat -> Entity -> Entity -> PropT
constant butter : Nat -> Adv -> Adv -> Entity -> Entity -> PropT
constant eat : Nat -> Entity -> Food -> Prop
constant knock : Nat -> Entity -> PropT

def example_1 : PropT := (at_T noon (butter 2 slowly in_bathroom John toast))
def example_2 : Prop := (Exists fun x_theme : Food => (eat 0 John x_theme))
def example_3 : PropT := (repeat 2 (knock 0 John))
def example_4 : PropT := (Cause John (Transition vase unknown_state broken))

#check example_1
#check example_2
#check example_3
#check example_4
