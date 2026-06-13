-- Auto-generated shallow embedding for dependent-type event semantics.
-- This file is an interface scaffold, not a complete proof development.

constant Entity : Type
constant Food : Type
constant State : Type
constant TransitionT : Type
abbrev PropT : Type := Prop
def Adv : Type := (Entity -> PropT) -> Entity -> PropT
constant ModifierSeq : Nat -> Type
constant mods_nil : ModifierSeq 0
constant mods_cons : (n : Nat) -> Adv -> ModifierSeq n -> ModifierSeq (Nat.succ n)

constant John : Entity
constant broken : State
constant noon : Entity
constant toast : Entity
constant unknown_state : State
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
constant Transition : Entity -> State -> State -> TransitionT
constant Cause : Entity -> TransitionT -> PropT
constant break : (n : Nat) -> ModifierSeq n -> Entity -> Entity -> PropT
constant butter : (n : Nat) -> ModifierSeq n -> Entity -> Entity -> PropT
constant eat : (n : Nat) -> ModifierSeq n -> Entity -> Food -> Prop
constant knock : (n : Nat) -> ModifierSeq n -> Entity -> PropT

def example_1 : PropT := (at_T noon (butter 2 (mods_cons 1 slowly (mods_cons 0 in_bathroom mods_nil)) John toast))
def example_2 : Prop := (Exists fun x_theme : Food => (eat 0 mods_nil John x_theme))
def example_3 : PropT := (repeat 2 (knock 0 mods_nil John))
def example_4 : PropT := (Cause John (Transition vase unknown_state broken))

#check example_1
#check example_2
#check example_3
#check example_4
