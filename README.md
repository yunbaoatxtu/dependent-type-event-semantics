# Dependent-Type Event Semantics

This repository develops a dependent-type replacement for several core
functions traditionally handled by Davidsonian and neo-Davidsonian event
semantics.

The central idea is not to deny that natural language can refer to events.
Rather, the project decomposes the hidden event variable into more specific
typed mechanisms:

- natural-number-indexed verb families for variable polyadicity;
- dependent role records for thematic-role structure;
- sigma and option types for argument omission;
- interval-indexed operators for time and aspect;
- state-transition types for causation and resultatives;
- episode witnesses introduced only for counting and discourse reference.

## Repository Layout

```text
paper/
  dependent_type_replacement_for_event_semantics_sci_manuscript.md
  dependent_type_replacement_for_event_semantics_sci_manuscript.docx

translator/
  dependent_type_event_translator.py
  surface_lexicon.py
  state_change_lexicon.py
  examples/
    example_butter.json

docs/
  event_to_dependent_type_notes.md
  ast_intermediate_representation.md

web/
  app.py
```

## Quick Start

Run the prototype translator on the included example:

```bash
python3 translator/dependent_type_event_translator.py \
  translator/examples/example_butter.json \
  --pretty
```

Expected core translation:

```text
at_T(noon, butter(2)(slowly, in(bathroom), John, toast))
```

Run the end-to-end natural-language prototype on a sentence:

```bash
python3 -m translator.natural_language_pipeline \
  "a cat sits on a mat"
```

The pipeline includes a conservative fallback parser for simple English
sentences. It emits four layers that can later be exposed in a web interface:
the natural-language input, an event-semantics JSON formula, the dependent-type
translation and AST, and generated Coq code with an optional Coq/Rocq boundary
check. For unlisted sentences, the fallback analysis is intentionally shallow:
it identifies a subject, predicate, possible object, common adverbs, count
words, simple word or digit `time(s)` count phrases, single-word and multi-word
temporal expressions, and simple prepositional modifiers. It also uses a small
shared verb-lemma table to avoid splitting simple adjective+noun subjects at the
wrong point: `a black cat sits on a mat` becomes
`sit(1)(on(mat), black_cat)`, not `cat(1)(on(mat), black, sits)`. The shared
surface lexicon also normalizes common past-tense forms before translation, so
examples such as `a dog chased a cat` export `chase` rather than a truncated
predicate name.

Temporal adverbs such as `yesterday` are emitted as `at(e, yesterday)` before
translation, so `Mary admired the painting yesterday` becomes
`at_T(yesterday, admire(0)(mary, painting))` rather than treating
`painting_yesterday` as one entity.
Count phrases behave similarly: `Mary visited Paris three times` becomes
`repeat(3, visit(0)(mary, paris))`, not `visit(0)(mary, paris_three_times)`.
The digit form `Mary visited Paris 3 times` follows the same path.
Multi-word temporal phrases are also boundary-aware: `Mary admired the painting
last night` becomes `at_T(last_night, admire(0)(mary, painting))`, and
`John walked to school this morning` keeps `to(school)` separate from
`this_morning`.
The same temporal boundary applies at the beginning of a sentence: `Yesterday
Mary admired the painting` becomes `at_T(yesterday, admire(0)(mary, painting))`
rather than assigning the subject `yesterday_mary`.
Restricted prepositional time phrases are also recognized at the beginning and
end of a sentence: `At noon Mary admired the painting`, including the comma
variant `At noon, Mary admired the painting`, becomes
`at_T(noon, admire(0)(mary, painting))`; `At noon yesterday Mary admired the
painting` becomes `at_T(yesterday, at_T(noon, admire(0)(mary, painting)))`;
`In the morning John walked to school` becomes
`during_T(morning, walk(1)(to(school), john))`; and `Mary admired the painting
in the morning` becomes `during_T(morning, admire(0)(mary, painting))`. The
same whitelist keeps ordinary locatives such as `in the bathroom` as Adv
modifiers.
The ambiguous preposition `at` is split by the same boundary: `Mary waited at
noon` becomes `at_T(noon, wait(0)(mary))`, while `Mary waited at the station`
becomes `wait(1)(at(station), mary)` and `John buttered the toast at the table`
becomes `butter(1)(at(table), john, toast)`.
Fronted non-temporal modifiers use the same Adv path: `In the bathroom Mary
buttered the toast with a knife` becomes
`butter(2)(in(bathroom), with(knife), mary, toast)`, `With a knife John
buttered the toast in the bathroom` becomes
`butter(2)(with(knife), in(bathroom), john, toast)`, and `From home John walked
to school` becomes `walk(2)(from(home), to(school), john)`. This keeps the
fronted modifier from being folded into an entity constant such as
`in_bathroom_mary`; likewise, `At the station Mary waited` becomes
`wait(1)(at(station), mary)` rather than a temporal `at_T(station, ...)`.
The fronted boundary also keeps short multi-word PP objects together:
`In the old bathroom Mary buttered the toast` becomes
`butter(1)(in(old_bathroom), mary, toast)`, `With a sharp knife John buttered
the toast` becomes `butter(1)(with(sharp_knife), john, toast)`, and `At the
train station Mary waited` becomes `wait(1)(at(train_station), mary)`.
Simple copular location sentences are normalized to `be` and keep the located
entity as `Theme`, not `Agent`: `a cat is on a mat` becomes
`be(1)(on(mat), cat)`, `the old dog is near the door` becomes
`be(1)(near(door), old_dog)`, and `In the park the old dog is near the door`
becomes `be(2)(in(park), near(door), old_dog)`. Specialized stative-result and
passive rules still take priority for sentences such as `the vase is broken`
and `the toast is buttered`.
Ordinary copular property sentences now use a separate `Property` type:
`Mary is happy` becomes `holds_property(mary, happy)`, and `Mary was happy
yesterday` becomes `at_T(yesterday, holds_property(mary, happy))`. Registered
state words such as `red`, `open`, and `broken` remain `State` values rather
than generic `Property` values.
Negation and degree modifiers are structured rather than folded into a new
atomic property: `Mary is not happy` becomes
`not_T(holds_property(mary, happy))`, `Mary is very happy` becomes
`holds_property(mary, degree_property(very, happy))`, and `Mary is not very
happy` combines both wrappers. Registered state predicates keep their state
type under negation, so `the door is not red` becomes
`not_T(holds_state(door, color_scale, red))` rather than introducing
`not_red : Property`.
Simple do-support negation is now a separate proposition-level wrapper:
`John did not walk` becomes `not_T(walk(0)(john))`, while `John does not walk
slowly in the park` becomes `not_T(walk(2)(slowly, in(park), john))`. The rule
also preserves lexical object types, so `John did not eat bread` becomes
`not_T(eat(0)(john, bread))` with `bread : Food`. Right-branch coordinated
do-support negation is now handled as typed coordination, so `John walked and did
not talk` becomes `and_T(walk(john), not_T(talk(john)))`, and `John ate bread
and did not drink water` becomes `and_T(eat(john, bread), not_T(drink(john,
water)))`. The same typed boundary supports disjunction: `John walked or did
not talk` becomes `or_T(walk(john), not_T(talk(john)))`, and `John ate bread or
did not drink water` becomes `or_T(eat(john, bread), not_T(drink(john, water)))`.
Time expressions still scope outside the conjunction, and shared
locative/instrumental/manner material remains typed as `Adv`, e.g. `John walked
and did not talk in the park` keeps `in(park)` as a modifier in both
coordinates. Contrastive `but` coordination is handled for simple clear cases:
`John did not walk but talked` becomes `and_T(not_T(walk(john)), talk(john))`,
and `John did not eat bread but drank water` becomes
`and_T(not_T(eat(john, bread)), drink(john, water))`. The same shared-modifier
discipline now applies to clear contrastive examples, so `John did not walk but
talked in the park` keeps `in(park)` as an `Adv` in both coordinates. Left-branch
internal modifiers, such as `John did not eat bread in the park but drank water`,
now use branch-local `ModifierSeq` indices:
`and_T(not_T(eat(1)(in(park), john, bread)), drink(0)(john, water))`, rather
than being collapsed into `bread_in_park`. Right-branch local modifiers can be
kept independently as well, so `John did not eat bread in the park but drank
water quickly` becomes `and_T(not_T(eat(1)(in(park), john, bread)),
drink(1)(quickly, john, water))`. The same rules now require both verbs in a
transitive coordination slice to be licensed as transitive surface predicates,
preventing `walk in the park` or `talk quickly` from being compiled as
entity-object applications. Fronted shared modifiers now become a shared
branch-local prefix, so `In the park John did not eat bread slowly but drank
water quickly` keeps both local adverbs and the shared `in(park)` modifier
typed as `Adv`, rendering both branches with `in(park)` before their own local
modifier. Left-branch-internal time modifiers now remain inside their own
branch, so `John did not eat bread yesterday but drank water quickly` becomes
`and_T(not_T(at_T(yesterday, eat(0)(john, bread))), drink(1)(quickly, john,
water))`. All successful do-support negation routes now expose a normalized
`semantic_readings` list and `semantic_readings_check`, including single-reading
simple negation, right-branch coordination, contrastive `but`, and repeated
do-support negation, so API clients do not need special code just to find the
checked formula for these constructions. Scope-ambiguous patterns such as
`John did not walk and talk` are now
returned as two explicit readings, `not_T(and_T(walk(john), talk(john)))` and
`and_T(not_T(walk(john)), not_T(talk(john)))`, rather than being misread as a
subject `john_did_not` or an object `and_did_not_talk`. Negated disjunction is
kept structural as well: `John did not walk or talk` becomes
`not_T(or_T(walk(john), talk(john)))`, not `not_T(walk(0)(john, or_talk))`.
When both coordinates repeat do-support, the surface connective is preserved:
`John did not walk and did not talk` becomes
`and_T(not_T(walk(john)), not_T(talk(john)))`, while `John did not walk or did
not talk` becomes `or_T(not_T(walk(john)), not_T(talk(john)))`.
Simple copular coordination is structured with `and_T`: `Mary is happy and
calm` becomes `and_T(holds_property(mary, happy), holds_property(mary, calm))`,
and `Mary is happy and very calm` keeps the degree only on the second conjunct.
Registered state coordination stays in the state layer, so `the door is red and
open` becomes `and_T(holds_state(door, color_scale, red),
holds_state(door, access_scale, open))`, not `red_and_open : Property`.
Same-subject intransitive predicate coordination is also handled before the
generic fallback. `John walked and talked` becomes
`and_T(walk(john), talk(john))`, and `John walked and talked yesterday` becomes
`at_T(yesterday, and_T(walk(john), talk(john)))`. The same temporal scoping now
holds sentence-initially: `Yesterday John walked and talked` keeps `john` as
the subject and puts `yesterday` outside the conjunction. The two predicates are
declared as `Entity -> Prop`, so the analysis does not invent a Theme such as
`and_talked` or `or_talked` and does not export hidden `Event`, `Agent`, or
`Theme` declarations. The same AST uses `or_T` for disjunction: `John walked or
talked` and `John either walked or talked` both become
`or_T(walk(john), talk(john))`, while `John both walked and talked` becomes
`and_T(walk(john), talk(john))`; the surface markers `either` and `both` are
not folded into the subject. This rule is intentionally
narrow: object coordination such as `Mary visited Paris and London` is handled
by its own object-coordination rule rather than by predicate coordination.
Fronted and trailing non-temporal prepositional phrases stay in the Luo-Shi
modifier layer:
`In the park John walked and talked` becomes
`and_T(walk(1)(in(park), john), talk(1)(in(park), john))`, with shared modifier
`in_park : Adv`. The predicates have type
`forall n : nat, ModifierSeq n -> Entity -> PropT`, rather than using the
malformed subject `in_park_john`.
Single-word manner adverbs use the same shared-Adv path: `John walked and
talked slowly` and `Slowly John walked and talked` both become
`and_T(walk(1)(slowly, john), talk(1)(slowly, john))`, not a fallback with
`and_talked` or a subject `slowly_john`.
Multiple shared modifiers preserve surface order in the indexed sequence:
`John walked and talked slowly in the park` becomes
`and_T(walk(2)(slowly, in(park), john), talk(2)(slowly, in(park), john))`,
while `John walked and talked in the park slowly` becomes
`and_T(walk(2)(in(park), slowly, john), talk(2)(in(park), slowly, john))`,
not `in_park_slowly`.
The same order rule applies when one modifier is fronted and another is
trailing: `Slowly John walked and talked in the park` still yields the sequence
`slowly, in(park)`.
A separate subject-coordination rule handles two `Entity` subjects sharing one
intransitive predicate. `John and Mary walked` and `Both John and Mary walked`
both become `and_T(walk(john), walk(mary))`, while `John or Mary walked` becomes
`or_T(walk(john), walk(mary))`. Shared Adv and time material still composes
outside the subject names: `John and Mary walked in the park yesterday` becomes
`at_T(yesterday, and_T(walk(1)(in(park), john), walk(1)(in(park), mary)))`.
A companion transitive subject-coordination rule keeps the shared object and its
lexical type explicit: `John and Mary ate bread` becomes
`and_T(eat(john, bread), eat(mary, bread))` with `bread : Food`, and `John or
Mary drank water` becomes `or_T(drink(john, water), drink(mary, water))` with
`water : Drinkable`. Shared modifiers compose in the same way, so `John and Mary
ate bread in the park yesterday` becomes
`at_T(yesterday, and_T(eat(1)(in(park), john, bread), eat(1)(in(park), mary, bread)))`.
The next controlled coordination layer handles two transitive verb phrases with
the same subject. `John ate bread and drank water` becomes
`and_T(eat(john, bread), drink(john, water))`; `bread` is typed as `Food`, while
`water` is typed as `Drinkable`, following the existing lexical argument types.
The disjunctive case uses the same typed objects and replaces the connective:
`John ate bread or drank water` becomes
`or_T(eat(john, bread), drink(john, water))`, not a pseudo-object such as
`bread_or_drank_water`. The marked forms `John either ate bread or drank water`
and `John both ate bread and drank water` use the same typed subject/object
split and keep the subject as `john`, not `john_either` or `john_both`.
Sentence-final time still scopes over the whole conjunction, so `John ate bread
and drank water yesterday` becomes
`at_T(yesterday, and_T(eat(john, bread), drink(john, water)))`; fronted time
does the same, so `Yesterday John ate bread and drank water` no longer creates
the malformed subject `yesterday_john`. This rule also stays separate from
object coordination: `Mary visited Paris and London` is not treated as two verb
phrases.
Object coordination keeps one subject and predicate while distributing over two
typed objects. `Mary visited Paris and London` becomes
`and_T(visit(mary, paris), visit(mary, london))`, and `Mary visited Paris or
London` becomes `or_T(visit(mary, paris), visit(mary, london))`; the marked
object form `Mary visited both Paris and London` strips `both` rather than
constructing `both_paris`. Shared modifier/time material scopes over the
distributed object formula, so `Mary visited Paris and London in the park
yesterday` becomes `at_T(yesterday, and_T(visit(1)(in(park), mary, paris),
visit(1)(in(park), mary, london)))`.
The same shared-Adv treatment applies to fronted and trailing locations in this
transitive coordination slice: `In the park John ate bread and drank water` and
`John ate bread and drank water in the park` both become
`and_T(eat(1)(in(park), john, bread), drink(1)(in(park), john, water))`, while
`bread : Food` and `water : Drinkable` remain distinct object types rather than
creating `water_in_park`.
Shared manner adverbs keep the right-hand object intact as well:
`John ate bread and drank water quickly` becomes
`and_T(eat(1)(quickly, john, bread), drink(1)(quickly, john, water))`, not a
right-hand object `water_quickly`.
The order-sensitive modifier vector is shared across transitive conjuncts too:
`John ate bread and drank water quickly in the park` becomes
`and_T(eat(2)(quickly, in(park), john, bread), drink(2)(quickly, in(park), john, water))`.
With a fronted modifier plus a trailing modifier, `Quickly John ate bread and
drank water in the park` uses that same `quickly, in(park)` sequence.
The Coq declaration layer separates repeated semantic occurrences from
repeated declarations: `John walked and talked slowly slowly`,
`John walked and talked yesterday yesterday`, and `John ate bread and ate bread`
retain the repeated modifier, time operator, or conjunct in the formula but
declare `slowly`, `yesterday`, `bread`, and `eat` only once. A genuine lexical
type conflict is still rejected before Coq; for example, `John ate bread and
drank bread` tries to use `bread` as both `Food` and `Drinkable`.

Quantifier-scope examples receive a separate ambiguity analysis instead of
being forced through the fallback parser:

```bash
python3 -m translator.natural_language_pipeline \
  "some boy loves some girl" \
  --require-coq
```

This produces both subject-wide and object-wide existential readings and checks
the generated Coq scaffold. The result also exposes a top-level
`semantic_readings` list, so clients can consume quantifier, negation, and
mixed temporal scope alternatives through one common shape; the companion
`semantic_readings_check` object confirms that the readings are named,
non-empty, unique, type-checked, and backed by exported Coq definitions when a
definition name is given. The intermediate AST stores each reading as a
structured scope order with bound variables, `Entity -> Prop` restrictor
predicates, and an `Entity -> Entity -> Prop` relation before any formula string
is rendered. Coq/Rocq verifies the exported formal terms; it does not by itself
prove that an arbitrary natural-language parse is the only correct semantic
analysis. The quantifier-scope scaffold does not introduce an `Event` type:
`boy` and `girl` are predicates of type `Entity -> Prop`, and `love` is typed
directly as `Entity -> Entity -> Prop`. Clause-level time modifiers now remain
inside the same ambiguity analysis instead of triggering the fallback parser:
`some boy loves some girl yesterday` yields the two scope readings
`at_T(yesterday, exists x_boy : Entity. boy(x_boy) and exists x_girl : Entity.
girl(x_girl) and love(x_boy, x_girl))` and its object-wide counterpart, while
`some boy loves some girl in the morning` uses `during_T(morning, ...)`.
Shared Adv modifiers are kept in the same two scope readings as dependent
modifier sequences: `some boy loved some girl in the bathroom` renders
`love(1)(in(bathroom), x_boy, x_girl)`, declares `in_bathroom : Adv`, and gives
`love` the type `forall n : nat, ModifierSeq n -> Entity -> Entity -> PropT`.
Fronted variants such as `In the bathroom some boy loved some girl` use the
same readings: the modifier parser stops before the quantified subject and does
not collapse the phrase into a malformed `in_bathroom_some` constant.
The same existential-scope rule covers indefinite articles: `a boy loves a
girl` yields `a_boy_wide_scope` and `a_girl_wide_scope`, while mixed forms such
as `a boy loves some girl` preserve both surface quantifiers in the AST instead
of treating `boy` or `girl` as entity constants.

Modifier typing follows the Luo-Shi variable-polyadicity analysis. Adverbial
and prepositional modifiers are exported as `Adv`, not `Entity`:

```coq
Definition PropT : Type := Prop.
Definition Adv : Type := (Entity -> PropT) -> Entity -> PropT.
Parameter ModifierSeq : nat -> Type.
Parameter mods_nil : ModifierSeq 0.
Parameter mods_cons : forall n : nat, Adv -> ModifierSeq n -> ModifierSeq (S n).
Parameter in_bathroom : Adv.
Parameter with_knife : Adv.
Parameter butter : forall n : nat, ModifierSeq n -> Entity -> Entity -> PropT.
```

The generated AST records both the surface modifier list and a normalized
`modifier_vector` with explicit tail lengths; it rejects mismatches among the
natural-number count, the surface list, and the vector. It also records
`modifier_roles`, so `in(bathroom)` is a Location-like `Adv`, `with(knife)` is
an Instrument-like `Adv`, and ordinary adverbs such as `slowly` are Manner-like
`Adv` values rather than entity arguments. The type checker verifies these
roles against the modifier predicate, so `with(knife)` cannot be mislabeled as a
Location modifier. Each modifier-role entry also carries a `surface_lexicon`
audit object with the surface modifier, its normalized proof-assistant name
such as `in_bathroom` or `with_knife`, its `Adv` type, semantic role, and source
module; the checker rejects mismatches between the surface modifier and the
`normalized_modifier` constant. The role mapping itself lives in the shared
surface lexicon (`MODIFIER_ROLE_BY_PREDICATE` in
`translator/surface_lexicon.py`), so modifier classification is maintained with
the same lexical resources that normalize surface forms. The AST also carries a
`role_frame`
that preserves thematic labels such as `Agent` and `Theme` and checks that those
role values match the ordered entity arguments in canonical thematic order, with
role types aligned to the generated function argument types. Thus an overt
object of `read`, for example, is tracked as `Readable` rather than collapsed
back to an undifferentiated `Entity`. The proof-assistant scaffold then packages
the same vector into an indexed
`ModifierSeq n`, so Coq also checks that the sequence passed to `butter n` has
length `n`. One lexical constant such as `butter` can therefore occur in the
same Coq file with zero, two, or three modifiers without producing conflicting
shallow function declarations.
The web/API layer also lifts these records to `modifier_role_audit`, and the
page renders them in a dedicated `Modifier Role Audit` panel for quick
inspection. That panel includes the nested `surface_lexicon` audit, so a reader
can see both the semantic role and the normalized `Adv` constant used by the
generated Coq/Rocq scaffold. When a modifier-bearing application is nested
inside another term, such as a temporal wrapper, the audit path records that
structure with paths like `ast.body`. Directional fallback sentences use the same path:
`John went from home to school` exports `from_home : Adv` with role `Source`
and `to_school : Adv` with role `Goal`, then checks `go` with a
`ModifierSeq 2`.

Parsons-style event talk can also be routed through typed replacements. For
example:

```bash
python3 -m translator.natural_language_pipeline \
  "after the singing of the Marseillaise, John saluted the flag" \
  --require-coq
```

This stage exports `Time`, `before`, `sing`, and `salute` declarations and
checks a formula of the form `exists t_sing t_salute : Time, ...`. Its AST also
checks that `sing : Entity -> Time -> Prop`,
`salute : Entity -> Entity -> Time -> Prop`, and
`before : Time -> Time -> Prop` relate `t_sing` before `t_salute`. It does not
introduce a hidden `Event` parameter for this sentence. The same output now
also exposes a single checked `semantic_readings` entry,
`timed_after_singing_salute`, whose Coq definition is audited by
`semantic_readings_check`.

Two further Parsons/Luo-Shi examples are now checked by specialized paths:

```bash
python3 -m translator.natural_language_pipeline \
  "Mary saw John leave" \
  --require-coq

python3 -m translator.natural_language_pipeline \
  "In every burning, oxygen is consumed" \
  --require-coq
```

The perception-complement example uses a nominalizing map
`E : Prop -> Entity`, yielding `see Mary (E (leave John))`. Its AST records
`see : Entity -> Entity -> Prop`, `leave : Entity -> Prop`, and the nominalized
object produced by `E`, so the construction is type-checked before Coq export.
The nominalized object may also be a checked embedded subject coordination:
`Mary saw John and Bill leave` becomes
`see(Mary, E(and_T(leave(John), leave(Bill))))`, while
`Mary saw John or Bill leave` uses `or_T` inside the same nominalizer. This keeps
the perceived complement propositional before `E` maps it into the entity object
position of `see`.
The same layer now handles two coordinated embedded propositions:
`Mary saw John leave and Bill wave` becomes
`see(Mary, E(and_T(leave(John), wave(Bill))))`, with `leave` and `wave`
declared separately at type `Entity -> Prop`.
It can also keep an internal temporal relation inside the perceived
proposition: `Mary saw John leave after Bill waved` becomes:

```text
see(Mary, E(exists t_main t_reference : Time. leave(John, t_main) and wave(Bill, t_reference) and before(t_reference, t_main)))
```

Here `leave` and `wave` are declared as `Entity -> Time -> Prop`.
Either side of that temporal relation can itself be coordinated. A coordinated
reference side is:

```text
Mary saw John leave after Bill waved and Sue smiled
```

This yields:

```text
see(Mary, E(exists t_main t_reference_1 t_reference_2 : Time. leave(John, t_main) and and_T(wave(Bill, t_reference_1), smile(Sue, t_reference_2)) and before(t_reference_1, t_main) and before(t_reference_2, t_main)))
```

The checker requires one `before` relation for each timed reference clause.
A coordinated main side receives the same treatment:

```text
Mary saw John leave and Sue smile after Bill waved
```

This yields:

```text
see(Mary, E(exists t_main_1 t_main_2 t_reference : Time. and_T(leave(John, t_main_1), smile(Sue, t_main_2)) and wave(Bill, t_reference) and before(t_reference, t_main_1) and before(t_reference, t_main_2)))
```

The checker requires one `before` relation for each timed main/reference pair,
so deleting either ordering constraint is rejected before Coq/Rocq export.
When both sides are coordinated, the checker requires the full Cartesian set of
main/reference time constraints. For example, `Mary saw John leave and Sue smile
after Bill waved and Ann laughed` binds `t_main_1`, `t_main_2`,
`t_reference_1`, and `t_reference_2`, then checks four `before` relations.
Timed perception coordination is not limited to two clauses: `Mary saw John
leave and Sue smile and Ann laugh after Bill waved` is rendered with three main
times and a right-associated `and_T` term, then checks three `before`
constraints from the reference time to the three main times.
The corresponding `before` forms reverse every ordered pair, so three main
clauses before one reference clause check `before(t_main_i, t_reference)`, and
one main clause before three reference clauses checks `before(t_main,
t_reference_i)`.
Timed perception disjunction now uses branch-local time binding: `Mary saw John
leave or Sue smile after Bill waved` renders as an `or_T` of two existential
time propositions, so each branch carries its own `before` constraint and the
temporal phrase is not folded into an entity name. If both the main and
reference sides are disjunctive, the renderer builds the Cartesian set of
branch-local alternatives, so two main possibilities against two reference
possibilities yield four scoped `or_T` branches. Mixed `and`/`or` timed
coordination now uses a controlled precedence policy: adjacent `and` groups are
formed first, and those groups are then folded by `or_T`, with each disjunctive
branch retaining its own existential time binders and `before` constraints. For
example, `Mary saw John leave and Sue smile or Ann laugh after Bill waved`
renders as an `or_T` whose first branch contains
`and_T(leave(John, t_main_1), smile(Sue, t_main_2))` and whose second branch
contains `laugh(Ann, t_main_3)`. The same policy applies on the reference side:
`Mary saw John leave after Bill waved and Sue smiled or Ann laughed` becomes an
`or_T` over one branch with
`and_T(wave(Bill, t_reference_1), smile(Sue, t_reference_2))` and one branch
with `laugh(Ann, t_reference_3)`. If both sides are mixed, the renderer builds
the Cartesian set of branch-local alternatives. The default reading is still
the exported primary translation, but the pipeline now also reports an
`alternative_scope_readings` list with the opposite `or_before_and` grouping;
those alternatives are emitted as extra Coq/Rocq definitions and checked in the
same scaffold. The primary reading and these checked alternatives are also
normalized into top-level `semantic_readings`, matching the schema used for
quantifier scope and do-support negation ambiguity; `semantic_readings_check`
audits that the primary and alternative Coq definition names are actually
exported. Parenthesized or pragmatically marked scope alternatives are still
outside this small controlled fragment.
The burning example uses universal time quantification:
`forall x : Entity, forall t : Time, burn x t -> consume oxygen t`. Its AST
stores the binders `x : Entity` and `t : Time`, then checks that both `burn` and
`consume` have type `Entity -> Time -> Prop` and share the same time variable.
Its single `semantic_readings` entry is named `universal_timed_burning` and
points to the exported `every_burning_consumes_oxygen` Coq definition. Both
generated Coq scaffolds are checked without introducing an `Event` type.

The argument-omission path now also covers a passive slice:

```bash
python3 -m translator.natural_language_pipeline \
  "the toast was buttered by John" \
  --require-coq

python3 -m translator.natural_language_pipeline \
  "the toast was buttered" \
  --require-coq

python3 -m translator.natural_language_pipeline \
  "the doors were opened by John" \
  --require-coq

python3 -m translator.natural_language_pipeline \
  "John was seen by Mary" \
  --require-coq
```

The explicit by-phrase version checks as `butter(john, toast)`. The omitted
agent version checks as
`exists x_agent : Entity. butter(x_agent, toast)`. The AST records
`toast : Entity` as the surface subject but the logical Patient, records either
`john : Entity` from the by-phrase or the existential `x_agent : Entity`, and
keeps the predicate type fixed as `Entity -> Entity -> Prop`. It also records
the passive auxiliary (`is`, `was`, `are`, or `were`) so that finite passive
forms are recognized before the generic fallback parser can misread them as
ordinary verbs. The generated Coq does not introduce `Event`, `Agent`, or
`Theme` declarations. Irregular passive participles are normalized through the
shared surface lexicon in `translator/surface_lexicon.py`, so `seen` exports
`see : Entity -> Entity -> Prop` and `written` exports
`write : Entity -> Entity -> Prop`. The AST exposes this step as a
`surface_lexicon` audit object recording the surface participle, the selected
lemma, and the lexicon module that supplied the mapping. Passive by-phrase and
omitted-agent outputs are normalized into single `semantic_readings` entries
with `by_phrase_agent` or `omitted_existential_agent` scope labels, so clients
can consume them through the same checked interface as quantifier, negation,
and Parsons/Luo-Shi time examples. This passive slice now also accepts typed
time modifiers at the clause boundary: `the toast was buttered by John
yesterday` becomes `at_T(yesterday, butter(john, toast))`, while `the toast was
buttered in the morning` becomes `during_T(morning, exists x_agent : Entity.
butter(x_agent, toast))`. The time operator scopes over the completed passive
proposition, not over a hidden event variable or a misparsed by-phrase agent.

Specialized constructions are tracked by a small construction registry. Each
registered rule declares its phenomenon, analysis function, and Coq fragments
that must not appear in the generated scaffold. For example, the Parsons/Luo-Shi
replacements forbid hidden `Event` declarations, the burning example
additionally forbids `IN`, and the passive omission rule also forbids exported
`Agent` and `Theme` role predicates.

The web/API result separates the rule's hygiene policy from the actual
generated output. `forbidden_coq_fragments` is the policy list; it does not mean
those fragments appeared in the generated Coq. `found_forbidden_fragments`
records actual violations. A clean replacement therefore looks like:

```json
{
  "construction_hygiene": {
    "ok": true,
    "checked": true,
    "forbidden_coq_fragments": ["Parameter Event : Type.", "IN"],
    "found_forbidden_fragments": []
  }
}
```

The web/API layer also adds a compact `diagnostics` object that summarizes the
four relevant checks for user interfaces:

```json
{
  "diagnostics": {
    "summary": "translation verified",
    "failure_stage": null,
    "recovery_hint": null,
    "recovery_actions": [],
    "warnings": [],
    "stages": {
      "type_check": "passed",
      "semantic_readings_check": "passed",
      "construction_hygiene": "passed",
      "coq_check": "passed"
    }
  }
}
```

Programmatic clients can call the same pipeline through the local JSON API:

```text
GET /api/analyze?sentence=Mary+saw+John+leave&require_coq=1
```

The `sentence` parameter carries the natural-language input. `require_coq=1`
asks the server to run the external Coq/Rocq boundary check when the toolchain
is available. The response includes `schema_version: "analyze.v1"` plus the
same event-semantics JSON,
dependent-type rendering, generated Coq, `result_state_lexicon`,
`modifier_role_audit`, `lexicon_patch_drafts`, `patch_text_preview`,
`semantic_readings`, `semantic_readings_check`, `construction_rule`,
`construction_summary`, `construction_hygiene`, `coq_check`, and `diagnostics`
fields used by the web page. For registered construction rules,
`construction_summary` gives a sentence-local explanation such as
`Same subject john coordinates eat(bread : Food) and drink(water : Drinkable).`
Successful registered rules must expose a passing `semantic_readings_check`.
Rules with explicit ambiguity keep their specialized readings; otherwise the
registered-rule boundary creates a conservative single reading from the unique
exported Coq/Rocq `Definition ... : Prop/PropT`.
The page also renders an `API Contract` panel with the same schema
version and endpoint, so browser users and automated clients can check the
contract without inspecting raw network traffic, and a `Conclusion` panel with
the same short outcome string returned by the API.

For failures, `diagnostics.failure_stage` distinguishes `input`, `parsing`,
`type_check`, `semantic_readings_check`, `construction_hygiene`, and
`coq_check` failures.
`diagnostics.recovery_hint` gives a short next-step suggestion for that failure
stage, while `diagnostics.recovery_actions` exposes the same advice as
structured actions for frontends and automation. Registered construction rules
stop at the first failed stage: if internal AST `type_check` fails or the
normalized `semantic_readings_check` cannot match readings to exported
Coq/Rocq definitions, construction hygiene and Coq/Rocq validation are reported
as `skipped` rather than attempted.
Every recovery action must expose non-empty `kind`, `label`, and `detail`
fields. The project verifier also checks that action kinds come from the
controlled diagnostic action set and that kind-specific payload fields have the
right shape: `target_definitions`, `duplicate_reading_names`, `reading_indices`,
`expected_export_count`, `observed_export_count`, and `exported_definitions`.
For semantic-reading failures, `diagnostics.semantic_readings_failure_kinds`
and `diagnostics.semantic_readings_failure_summary` classify the problem as
missing readings, duplicate reading names, malformed reading records,
reading-local type-check failure, missing Coq/Rocq exports, or a registered
construction export-count mismatch.
`diagnostics.semantic_readings_repair_details` carries the actionable audit
data behind that classification: exported Prop/PropT definition names, expected
reading definition names, missing definitions, duplicate reading names,
malformed reading indices, failed reading-local type-check indices, and
expected versus observed export counts when a registered rule did not expose a
unique proposition.
The verifier treats this as a fixed schema: the definition-name fields must be
string lists, the index fields must be integer lists, `expected_export_count`
must be either an integer or `null`, and `observed_export_count` must be an
integer. It also checks that repair details agree with the specialized
recovery action payloads derived from them.
For the same boundary, `diagnostics.recovery_actions` is specialized from
those repair details: missing exports produce `add_missing_coq_definitions`
with `target_definitions`, duplicate names produce `rename_duplicate_readings`,
malformed records and local type-check failures identify `reading_indices`, and
registered-rule export-count mismatches produce `normalize_reading_exports`
with expected and observed counts.
The local web page renders those structured actions in a separate `Next Steps`
panel. Each rendered action carries a stable `data-action-kind` attribute, a
`data-action-index` attribute, a `data-action-contract-kind` attribute, a
`data-action-contract-api="/api/diagnostic-contract"` pointer, a
`next-step--<kind>` CSS class, and a compact details table for frontend
automation. Diagnostic fixture pages also expose each action through a stable
JSON link such as
`/api/recovery-action?case=semantic_readings_missing_export&index=0`, whose
`diagnostic_recovery_action.v1` payload contains the fixture case, action
index, failure stage, exact action object, a `diagnostic_repair_plan.v1`
repair plan, and the shared diagnostic contract. The repair plan records
its `automation_mode`, whether the action can be run automatically as a
read-only inspection, whether it can be applied automatically as a mutation,
which target fields it touches, ordered repair steps, any review-only patch
preview, and verification commands that should be rerun after the repair.
The inspection-only actions such as `inspect_ast`, `inspect_coq`, and
`inspect_readings` can be auto-run without mutating semantic readings or
Coq/Rocq output; semantic and export repairs remain human-review-required.
The companion `/api/recovery-action-run?case=<case>&index=<n>` endpoint emits a
`diagnostic_inspection_run.v1` bundle only for those inspection-only actions,
returning a target-field snapshot such as `ast`, `type_check`,
`semantic_readings`, `semantic_readings_check`, `coq_code`, or `coq_check`.
Human-review-required repairs are rejected at that endpoint rather than
silently applied. Fixture pages also render an expandable `Inspection Run JSON`
preview for every auto-runnable inspection action in both the `Next Steps` list
and the `Recovery Action Exports` panel, and that preview must match the same
`diagnostic_inspection_run.v1` bundle served by the API. The verifier checks
the preview inside the corresponding action row, so a stale preview elsewhere
on the page cannot satisfy the diagnostic contract by accident.
The same fixture pages render a `Recovery Action Exports` panel that lists
those action JSON routes with their schema, case, index, action kind, and
failure stage, so browser checks can verify the export contract without opening
each link manually. Each export row also includes an expandable `Action JSON`
preview whose content must match the corresponding
`diagnostic_recovery_action.v1` API bundle exactly. The ordinary API path stays
separate from a `download=1` path with a stable `.json` filename, and the same
split is exposed for inspection-run JSON, so browser downloads, archived
artifacts, and API clients can share the same payload without guessing a file
name from visible prose. The project-level live web smoke check now requests
both ordinary and download paths, compares the JSON payloads, and checks the
download `Content-Disposition` filename, content type, and byte length. The
download-response validator also has direct counterexample tests for status,
content-type, content-length, filename, and payload drift, so those HTTP
artifact guarantees are checked independently of a running web server.
The web service also exposes controlled diagnostics fixtures for these failure
states. Use
`/api/diagnostic-fixture?case=semantic_readings_missing_export` for JSON, or
`/diagnostic-fixture?case=semantic_readings_missing_export` for the matching
HTML page. Companion cases cover malformed readings and registered-rule export
count mismatches, letting browser checks inspect the same `Next Steps` details
without corrupting the ordinary `/api/analyze` path. The same fixture endpoint
also covers the other stage-local failures through `type_check_failure`,
`construction_hygiene_failure`, and `coq_check_failure`, so each major
failure-stage banner and recovery action can be tested directly.
The HTML page exposes those cases through a compact
`diagnostic-fixture-form` selector that opens `/diagnostic-fixture`, keeping
diagnostic fixtures reachable without changing the ordinary analysis form or
the `/api/analyze` contract.
The companion `/api/diagnostic-fixtures` endpoint returns a
`diagnostic_fixtures.v1` manifest with each case label, JSON path, HTML path,
failure stage, recovery action kinds, and a `recovery_action_exports` inventory
containing per-action JSON export paths for frontends and regression tools.
Each inventory entry also records `download_api_path`, `download_filename`, the
action's `automation_mode`, `can_auto_run`, `can_auto_apply`, `target_fields`,
and, when the action is a read-only inspection, `inspection_run_api_path`,
`inspection_run_download_api_path`, and `inspection_run_download_filename`
pointing directly to the `diagnostic_inspection_run.v1` endpoint and its
download artifact. The selector mirrors this distinction with a
`data-inspection-run-count` hook for each fixture option, so browser automation
can discover executable diagnostic inspections from the manifest and HTML
without reconstructing URLs.
The case inventory, display labels, expected failure stages, and expected
recovery-action kinds are now derived from one `DIAGNOSTIC_FIXTURE_SPECS`
table of validated `DiagnosticFixtureSpec` entries, so adding a fixture no
longer requires editing separate case, label, stage, and action lists, and
unknown stage/action names fail before the manifest is served.
The web application and project verifier import the same diagnostic contract
module for the controlled failure-stage and recovery-action vocabularies, so
the browser/API route checks cannot accept a stage name that the UI layer would
reject.
The same vocabulary is exposed to clients at `/api/diagnostic-contract` as a
`diagnostic_contract.v1` manifest containing `failure_stages`,
`required_fixture_stages`, and `recovery_action_kinds`.
The verifier rejects schema drift, failure-stage drift, required-fixture-stage
drift, recovery-action drift, and stale selector links to that contract
endpoint.
The ordinary HTML page now renders the same vocabulary in a `Diagnostic
Contract` panel with `data-contract-schema`, `data-contract-api`,
`data-contract-field`, `data-contract-count`, and `data-contract-token` hooks,
so browser checks can read the controlled terms without scraping prose or
fixture-selector options.
The selector is rendered from the same manifest and carries
`data-fixtures-schema`, `data-fixtures-api`, `data-diagnostic-contract-api`,
and per-option failure-stage and recovery-action metadata, so the visible
labels, controls, and API inventory cannot silently drift apart.
The project-level verification smoke check fetches both the JSON manifest and
the matching HTML fixture page, so this selector/manifest contract is enforced
outside the unit-test renderer as well.
It walks every fixture case listed by the manifest and checks the API payload,
selected HTML option, API/HTML route case parameter, failure stage, and
recovery-action metadata for each one.
Fixture `failure_stage` values are checked against the same controlled set used
by ordinary diagnostics: `input`, `parsing`, `type_check`,
`semantic_readings_check`, `construction_hygiene`, and `coq_check`. The fixture
manifest must cover the four internal/proof-boundary stages
`type_check`, `semantic_readings_check`, `construction_hygiene`, and
`coq_check`; input and parsing failures remain covered through ordinary
`/api/analyze` failure tests.
The expected selector count is derived from the manifest itself, so adding a new
diagnostic case does not require updating a separate hard-coded smoke-test
constant.
The manifest/API/HTML consistency rules also live in a standalone verifier
helper with counterexample tests for duplicate cases, missing metadata, payload
case drift, route case drift between manifest paths and the fixture case, label
drift between manifest and HTML, unknown fixture failure stages, missing
internal/proof-boundary stage coverage, malformed recovery actions, invalid
repair-detail fields, action/detail drift, invalid action targets or counts,
recovery-action drift between the payload and manifest, stale HTML selector
attributes, and stale `Next Steps` action hooks.
It also renders a dedicated `Type Check` panel, so construction-specific AST
errors such as an unlicensed lexical state-change frame are visible beside the
AST instead of being hidden behind the status banner.
The `Semantic Readings Check` panel is likewise structured rather than raw-only:
it displays the audit status, reading count, exported Prop/PropT definition
names, and one row per reading with its name, scope, source, Coq/Rocq
definition, exported status, and reading-local type-check status, followed by
classified semantic-reading failure kinds, repair details such as missing
definition names or export-count mismatches, any semantic-reading errors, and
the raw JSON record.
The same stage-local reporting covers lexical declaration conflicts: `John ate
bread and drank bread` is reported as a dependent-type checking failure because
`bread` would need both `Food` and `Drinkable`, and the Coq/Rocq stage is
marked as skipped.
`diagnostics.warnings` records non-fatal semantic audit notices. For example,
`Mary painted the door red` can pass type checking and Coq/Rocq validation while
still warning that `red` has no unique lexical pre-state, so the transition
source remains `unknown_state`. Diagnostics also expose
`manual_repair_required` and `lexicon_patch_draft_count` so clients can tell
whether a successful translation still needs a human lexical decision. The page
status banner reports this as `Translation verified with warnings`, keeping the
successful proof-assistant boundary result separate from the semantic audit
notice. The current warning policy distinguishes `unknown_source_allowed`,
`derived_scale_no_known_prestate`, and `source_state_only` result-state records.
The same notices are rendered in a dedicated `Semantic Warnings` panel with
stable `data-warning-kind` attributes for UI tests and later controls. Each
warning also carries a `suggested_action` object, such as `add_state_prestate`,
so clients can distinguish a semantic caveat from the concrete lexicon repair
it invites. Suggested actions include a `lexicon_entry_draft` template with
`state`, `scale`, `default_source_state`, and `source_policy_after_update`
fields. The API also lifts these templates to top-level `lexicon_patch_drafts`,
giving clients a direct repair queue without requiring them to traverse warning
records. The project verifier treats this warning/action/draft chain as a fixed
schema: warning kinds, suggested-action kinds, draft fields, manual-repair
flags, and patch-text draft ids must agree between `diagnostics.warnings`,
top-level `lexicon_patch_drafts`, and `patch_text_preview`. Each draft includes
a stable `draft_id` and a
`state_lexicon_patch_line` preview of the candidate `StateLexiconEntry`, with a
placeholder source state that must be resolved before changing the lexicon. The
draft records this explicitly with `requires_human_choice`,
`placeholder_fields`, and `can_auto_apply`.

Export just the human-gated lexicon repair bundle for a sentence:

```bash
python3 scripts/export_lexicon_patch_drafts.py \
  --sentence "Mary painted the door red" \
  --require-coq
```

After choosing a source state, resolve the draft without mutating the lexicon:

```bash
python3 scripts/export_lexicon_patch_drafts.py \
  --sentence "Mary painted the door red" \
  --require-coq \
  --resolve-draft-id state-red--unknown_source_allowed \
  --source-state not_red \
  --patch-out work/red_state_lexicon.patch
```

The compact legacy spelling `--resolve state-red--unknown_source_allowed=not_red`
is also accepted for shell use.
Repeated resolutions for the same draft are allowed only when they agree; a
conflicting source-state choice is reported in `validation_errors` and is never
auto-applied.
When `validation_errors` is non-empty, the review patch text suppresses
candidate replacement lines until the errors are resolved.
The verifier also checks the standalone `lexicon_patch_drafts.v1` bundle as a
fixed schema: `resolved_patch_count`, `requires_human_choice`, `can_auto_apply`,
`validation_errors`, draft states, and the review-only patch text must agree, so
an invalid review cannot quietly produce an auto-applicable replacement line.

The same bundle is available from the web service at
`/api/lexicon-patch-drafts?sentence=Mary+painted+the+door+red&require_coq=1`.
Use `format=patch` on that endpoint to receive the review-only patch text as
`text/plain`. The web page also renders a source-state form for each pending
draft; submitting it previews the resolved patch through structured
`resolve_draft_id` and `source_state` parameters without mutating the lexicon.
The test suite compares this API JSON bundle, the API `format=patch` response,
the direct bundle builder, the CLI JSON output, and the CLI `--patch-out` file
for the same unresolved, resolved, and validation-error cases, so all review
channels stay synchronized.
The repository-level web smoke check also starts a real local server and
requests both `/api/lexicon-patch-drafts` response formats, checking HTTP
status, `Content-Type`, `Content-Length`, parsed JSON, and patch text against the
same fixed bundle contract.
HTTP-level negative cases are part of the same guard: empty sentences add a
bundle `validation_errors` entry and suppress candidate lines, conflicting
source-state choices remain non-auto-applicable, repeated identical choices are
accepted as one resolution, and unsupported `format` values return a 400 JSON
error instead of silently changing response shape.
The CLI exporter is checked against the same live HTTP outputs for pending,
compact resolved, structured resolved, duplicate-resolution, empty-sentence,
unknown-draft, conflicting-source-state, and invalid-source-state cases. Even
when the CLI exits non-zero, it must still write the JSON bundle and
`--patch-out` text before failing, so reviewers can inspect the same guarded
artifact that the browser would download.
Those CLI/HTTP contract cases are defined once in
`scripts/lexicon_patch_contract_cases.py` and imported by the direct API tests,
live HTTP route tests, command-line tests, and project verifier, so a new
boundary case enters every gate together.
The same shared case object also carries the expected `validation_errors`
fragments for failing cases; direct API, HTTP, CLI, and verifier checks all
reject a bundle whose machine-readable failure reason drifts from that contract.

Run the local web demo:

```bash
python3 -m web.app --port 8765
```

Then open `http://127.0.0.1:8765`. The page uses the same checked pipeline and
shows event semantics, dependent-type output, AST, generated Coq, and the
validation result.

## Verified Translation Stages

The current prototype has small, testable rules for:

- variable polyadicity plus temporal modification;
- lexically licensed argument omission;
- passive argument omission with an existential typed agent;
- event counting with `once`/`twice`/`thrice`, word or digit `time(s)`
  phrases, or explicit `count`;
- causal-resultative translation into a typed state transition.

Resultatives now export result states separately from ordinary individuals:
`vase` has type `Entity`, while `intact` and `broken` have type `State`,
`integrity_scale` has type `StateScale`, and `Transition` has type
`Entity -> StateScale -> State -> State -> TransitionT`.
Copular result-state clauses now use the same lexicon without forcing an
omitted Agent. For example:

```bash
python3 -m translator.natural_language_pipeline \
  "the vase is broken" \
  --require-coq

python3 -m translator.natural_language_pipeline \
  "the door is open" \
  --require-coq
```

These check as `holds_state(vase, integrity_scale, broken)` and
`holds_state(door, access_scale, open)`. If a by-phrase is present, as in
`the vase was broken by John`, the passive rule still applies and yields
`break(john, vase)`. This keeps stative result assertions distinct from
agentive passive clauses.

Lexical change-of-state verbs are also separated from the generic fallback:

```bash
python3 -m translator.natural_language_pipeline \
  "the door opened" \
  --require-coq

python3 -m translator.natural_language_pipeline \
  "John opened the door" \
  --require-coq

python3 -m translator.natural_language_pipeline \
  "John opened the door with a key" \
  --require-coq

python3 -m translator.natural_language_pipeline \
  "the clothes dried" \
  --require-coq

python3 -m translator.natural_language_pipeline \
  "John dried the clothes with a towel" \
  --require-coq

python3 -m translator.natural_language_pipeline \
  "the water froze" \
  --require-coq

python3 -m translator.natural_language_pipeline \
  "Mary cleaned the room" \
  --require-coq

python3 -m translator.natural_language_pipeline \
  "John died" \
  --require-coq

python3 -m translator.natural_language_pipeline \
  "Mary killed the plant with poison" \
  --require-coq
```

The inchoative version checks as
`Change(Transition(door, access_scale, closed, open))`; the causative version
checks as `Cause(john, Transition(door, access_scale, closed, open))`; and the
instrumental version checks as
`CauseWithInstrument(john, key, Transition(door, access_scale, closed, open))`.
The same registered construction now draws from the broader state lexicon:
`the clothes dried` checks as
`Change(Transition(clothes, moisture_scale, wet, dry))`,
`John dried the clothes with a towel` checks as
`CauseWithInstrument(john, towel, Transition(clothes, moisture_scale, wet, dry))`,
`the water froze` checks as
`Change(Transition(water, phase_scale, liquid, frozen))`, and
`Mary cleaned the room` checks as
`Cause(mary, Transition(room, cleanliness_scale, dirty, clean))`.
Content-scale alternations such as `the tank emptied` and
`John filled the glass` likewise map to transitions over `full` and `empty`.
Life-scale alternations demonstrate asymmetric frame licensing:
`John died` checks as `Change(Transition(john, life_scale, alive, dead))`,
while `Mary killed the plant with poison` checks as
`CauseWithInstrument(mary, poison, Transition(plant, life_scale, alive, dead))`.
The registered verb `die` licenses only the inchoative frame; `kill` licenses
causative and instrumental frames but not an inchoative frame such as
`the plant killed`.
Internally these verbs are registered as structured `StateChangeVerbEntry`
records in `translator/state_change_lexicon.py`, not as loose string rewrites
inside the parser. Each entry names the target state and the licensed
inchoative, causative, and instrumental frames, and the emitted result includes
`state_change_verb_entry` so clients can audit the lexical choice that selected
the transition. The AST also carries a `surface_lexicon` audit object for the
surface verb and lemma, so `died`, `killed`, `dried`, and `froze` remain visible
after lemmatization. The AST carries an explicit `frame` (`inchoative`,
`causative`, or `instrumental`), and the type checker rejects a mismatch such
as pairing the registered verb `open` with the target state `closed`, or
assigning a causative frame without a causer.
This prevents `the door opened` and similar inchoatives from being misread as
one-place predicates whose changing themes are Agents, while still preserving
the same typed transition used by resultative translations.
The fallback natural-language parser also recognizes simple result phrases
whose final object-position word is a known result state, so `John hammered the
metal flat` becomes
`Cause(john, Transition(metal, shape_scale, not_flat, flat))` rather than
treating `metal flat` as a single entity name. When a target state has a clear
opposite or pre-state, the translator supplies it as the transition source;
otherwise the source remains `unknown_state`. The same state-scale lexicon
covers common dimensions such as integrity, shape, access, phase, moisture,
fullness, color, cleanliness, and life status.
Internally this is a structured `StateLexiconEntry` table rather than two
independent dictionaries. Each known result state records its scale, optional
default source state, and whether an unknown source is explicitly allowed. The
pipeline exposes the same audit trail in `result_state_lexicon`, so a caller can
see, for example, that `flat` uses the lexical pre-state `not_flat`, while
`red` keeps an unknown source.
The web page renders these records in a dedicated Result State Lexicon panel
and also exposes the raw JSON for exact auditing. Entries whose source is
licensed as unknown are also surfaced through `diagnostics.warnings`, so a
successful translation can still report that the lexical state model is
underspecified. The same warning channel covers states whose scale is only
derived from the target name and states that are currently licensed only as
transition sources. The separate Semantic Warnings panel mirrors the same
records for readers who need the semantic caveat without opening the raw JSON,
and shows the warning's suggested action and lexicon-entry draft next to the
warning message. A separate Lexicon Patch Drafts panel mirrors the top-level
`lexicon_patch_drafts` queue for the same repairs. The same queue can also be
exported as a standalone JSON bundle with
`scripts/export_lexicon_patch_drafts.py` or `/api/lexicon-patch-drafts`.
Resolved bundles report `resolved_patch_count`, `validation_errors`, and a
`patch_text_preview`; unresolved previews keep pending human-choice lines as
comments, while resolved previews show candidate replacement lines. The
standalone bundle is checked as a fixed schema, so `can_auto_apply` cannot drift
from `validation_errors`, `resolved_patch_count`, or the candidate patch text.
The web page renders the same text in a `Lexicon Patch Text Preview` panel with an
`Open patch text` link backed by `format=patch`, and the command-line exporter
can additionally write that review-only candidate patch text with `--patch-out`.
File outputs create missing parent directories, so review bundles and patch
previews can be written into a fresh `work/` tree.
API JSON, API patch-text download, direct builder output, CLI JSON, and CLI
`--patch-out` files are regression-tested against one another for both resolved
and validation-error bundles.
The live HTTP route is covered too: the verifier checks the JSON response as
`application/json`, the patch response as `text/plain`, and the byte length and
payload for each response.
It also checks empty-input, repeated-resolution, conflicting-resolution, and
unknown-format cases so downloadable patch text cannot bypass the same
validation contract.
The exporter smoke check mirrors the same shared case table for command-line
review: successful CLI exits and non-zero CLI exits both have to leave behind
JSON and patch-text files whose payloads match the same bundle contract.
It reads the same shared contract-case table as the live HTTP regression test,
which keeps the command-line and browser/API acceptance boundaries from
silently drifting apart. The smoke check also enforces the expected
`validation_errors` fragments for failing cases, so a review artifact cannot
keep the right shape while silently changing the reason it rejects a repair.

Argument omission preserves the lexical type of the missing object at the Coq
boundary. For example, `John read` exports an existential witness
`x_theme : Readable` and
`read : forall n : nat, ModifierSeq n -> Entity -> Readable -> Prop`; `John drank`
analogously uses `Drinkable`. The same lexical object types are used for overt
objects, so `Mary read the book` declares `book : Readable` and gives the
example type `Prop`, matching the exported `read` signature. The shallow
interface defines `PropT` as an alias of Coq `Prop`, so temporal operators such
as `at_T` can also scope over these existential propositions.
The explanatory fields returned with each analysis use the same refinement:
`lexical_signature` and `dependent_type_principle` render `read` as
`ADV^n -> e -> Readable -> t`, not as a generic `ADV^n -> e -> e -> t`.

Each translation result includes both a human-readable `translation` string and
a structured `ast` object. The AST is the intended next bridge toward a proof
assistant or a typed semantic checker. The translator also returns a
`type_check` object that verifies basic AST well-formedness. Module-level
export also rejects declaration conflicts, such as reusing the same constant
name at incompatible types or exporting one shallow function name with
incompatible signatures. This includes cross-category clashes: a result-state
constant such as `broken : State` cannot be reused in the same generated module
as an entity-denoting constant `broken : Entity`.
Construction-specific exporters also de-duplicate identical declarations before
Coq/Rocq is called, so repeated occurrences of the same modifier, time
constant, object, or predicate do not become spurious `already exists` errors.
Incompatible repeated declarations remain type-checking failures rather than
being silently merged.

Run the test suite:

```bash
python3 -m unittest discover -v
```

Export a well-typed translation to a shallow proof-assistant embedding:

```bash
python3 translator/dependent_type_event_translator.py \
  translator/examples/example_eat_omission.json \
  --export lean
```

Render the manuscript locally. This wrapper fixes the macOS `soffice` crash
caused by a missing `little-cms2` library by pointing LibreOffice at the copy
bundled with the Codex runtime:

```bash
sh scripts/render_paper.sh
```

Synchronize the Word manuscript from the Markdown source before rendering:

```bash
python3 scripts/sync_paper_docx.py
```

Check that the committed Word manuscript still follows the Markdown source:

```bash
python3 scripts/check_paper_docx_sync.py
```

Generate Lean/Coq-style formalization scaffolds from the checked examples:

```bash
python3 scripts/generate_formalization.py
```

Check that the generated formalization scaffolds match the current translator
and examples:

```bash
python3 scripts/check_formalization.py
```

The GitHub Actions workflow installs Coq on the Ubuntu runner before running
the deterministic checks with `--require-coq`. It also installs the document
extra and passes `--require-docx`, so both the proof-assistant boundary checks
and the Word-generation tests must really run instead of being silently
skipped.

Run all deterministic project checks through one entry point:

```bash
python3 scripts/verify_project.py
```

This includes a package-build smoke check that runs
`pip wheel --no-build-isolation --no-deps`, using the active Python
environment's local build tooling rather than requiring a network fetch for
build dependencies. It also runs a smoke check for the lexicon patch exporter,
verifying that it can write both the JSON bundle and review-only patch text,
and a web route smoke check that requests the diagnostic fixture manifest
through the local HTTP handler.

Coq/Rocq is not required to run the translator. The Python implementation is
the core automation layer: it parses the event-semantics input, builds the
structured AST, type-checks that AST, and exports shallow proof-assistant
syntax. When Coq/Rocq is installed, the verification script can additionally
compile the generated Coq scaffold as an optional boundary check:

```bash
coqc formalization/DependentTypeEventSemantics.v
```

Use `--skip-coq` to run only the Python and scaffold-consistency checks, or
`--require-coq` when a local proof-assistant boundary check is mandatory:

```bash
python3 scripts/verify_project.py --skip-coq
python3 scripts/verify_project.py --require-coq
```

Use `--require-docx` when Word-generation tests must be enforced. If the system
Python does not provide `python-docx`, run the command with the bundled Codex
workspace Python runtime or install the project document extra:

```bash
python3 -m pip install ".[docx]"
python3 scripts/verify_project.py --require-coq --require-docx
```

## Scope

The current implementation is a prototype. It accepts a small JSON
representation of neo-Davidsonian event formulas and emits a dependent-type
style rendering. The accompanying paper explains the broader theoretical
architecture needed to replace event semantics across variable polyadicity,
argument omission, thematic roles, event quantity, causation, and resultatives.

## Status

Early research prototype and manuscript draft.

## Citation

If you build on this project, cite the manuscript draft in `paper/` and the
background work discussed there, especially Luo and Shi's type-theoretic
analysis of variable polyadicity without events.
