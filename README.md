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

The pipeline includes registered construction rules plus a conservative
fallback parser for residual simple English sentences. It emits four layers
that can later be exposed in a web interface: the natural-language input, an
event-semantics JSON formula, the dependent-type translation and AST, and
generated Coq code with an optional Coq/Rocq boundary check. A registered
active argument-omission construction now covers `John ate` as
`Sigma x_theme : Food. eat(0)(John, x_theme)`, with the omitted Theme represented
as a typed Sigma witness rather than an event role predicate. A registered
plain-transitive construction covers `Mary admired the painting` as
`admire(0)(mary, painting)`, with explicit Agent and Theme arguments kept in a
typed binary predicate rather than exported as role predicates. A registered
locative-intransitive construction also covers `a cat sits on a mat` as
`sit(1)(on(mat), cat)`, with `on(mat)` exported as an `Adv` value rather than an
entity. For still-unregistered sentences, the fallback analysis is
intentionally shallow: it identifies a subject, predicate, possible object,
common adverbs, count
words, simple word or digit `time(s)` count phrases, single-word and multi-word
temporal expressions, and simple prepositional modifiers. It also uses a small
shared verb-lemma table to avoid splitting simple adjective+noun subjects at the
wrong point: `a black cat sits on a mat` becomes
`sit(1)(on(mat), black_cat)`, not `cat(1)(on(mat), black, sits)`. The shared
surface lexicon also normalizes common past-tense forms before translation, so
examples such as `a dog chased a cat` export `chase` rather than a truncated
predicate name.
Successful fallback analyses also expose the normalized semantic-reading
contract used by registered constructions: a single `fallback_single_reading`
entry sourced as `fallback_event_semantics`, linked to exported Coq/Rocq
definition `example_1`, carrying a `none` attachment summary, and checked by a
passing `semantic_readings_check`.

The same entry point now has a certified-fragment safety guard around
registered construction rules and fallback sentence analysis. A small
allowlisted construction handles simple conditionals first, so `if John left,
Mary cried` is checked as `leave(john) -> cry(mary)`, and `if John ate bread,
Mary drank water` is checked as `eat(john, bread) -> drink(mary, water)` with
`bread : Food` and `water : Drinkable`. Clause-level Adv modifiers are stored
as `Adv` values and passed through a `ModifierSeq`, so
`if John ate bread quickly, Mary cried loudly` becomes
`eat(1)(quickly, john, bread) -> cry(1)(loudly, mary)`. When the same
conditional predicate appears once with Adv modifiers and once without them,
the unmodified clause is lifted to the same dependent signature and receives
the zero-length modifier vector: `if John left quickly, Mary left` becomes
`leave(1)(quickly, john) -> leave(0)(mary)`, with `mods_nil` in the generated
Coq/Rocq term. The same normalization composes with clause-local time:
`if John left quickly yesterday, Mary left today` becomes
`at_T(yesterday, leave(1)(quickly, john)) -> at_T(today, leave(0)(mary))`.
Clause-level time
modifiers scope over their own proposition, so
`if John left in the park yesterday, Mary cried today` becomes
`at_T(yesterday, leave(1)(in(park), john)) -> at_T(today, cry(mary))`. The same certified
route handles narrow do-support negation inside a conditional clause:
`if John did not leave quickly, Mary cried today` becomes
`not_T(leave(1)(quickly, john)) -> at_T(today, cry(mary))`, with `not_T`
declared at type `Prop -> Prop`. It also handles two coordinated subjects that
share a clause predicate: `if John and Mary ate bread quickly in the park yesterday, Sue cried today`
becomes
`at_T(yesterday, and_T(eat(2)(quickly, in(park), john, bread), eat(2)(quickly, in(park), mary, bread))) -> at_T(today, cry(sue))`,
with `and_T : PropT -> PropT -> PropT`. These exports use no event, Agent, or Theme
declarations. A separate narrow because-clause route now treats simple causal
subordination as a proposition-level connective: `John left because Mary cried`
becomes `because_T(cry(mary), leave(john))`, and
`John ate bread because Mary drank water yesterday` becomes
`because_T(at_T(yesterday, drink(mary, water)), eat(john, bread))`, preserving
the typed transitive objects `water : Drinkable` and `bread : Food` instead of
collapsing them to generic event roles. The same route now composes with the
registered lexical state-change layer: `John opened the door because Mary cleaned the room`
becomes
`because_T(Cause(mary, Transition(room, cleanliness_scale, dirty, clean)), Cause(john, Transition(door, access_scale, closed, open)))`,
where `clean` and `open` remain `State` targets inside typed transitions rather
than ordinary binary predicates. Mixed simple/state-change cases are now
covered in both directions: `Mary cried because the door opened` becomes
`because_T(Change(Transition(door, access_scale, closed, open)), cry(mary))`,
and `the door opened because Mary cried` becomes
`because_T(cry(mary), Change(Transition(door, access_scale, closed, open)))`.
Instrumental state changes are preserved as well:
`Mary cried because John opened the door with a key` becomes
`because_T(CauseWithInstrument(john, key, Transition(door, access_scale, closed, open)), cry(mary))`.
The same certified route now has a controlled discourse-anaphora bridge for
state-change themes: `Mary admired the door because it opened` resolves `it`
to the explicitly mentioned object `door` and becomes
`because_T(Change(Transition(door, access_scale, closed, open)), admire(mary, door))`.
The AST records the resolution under the transition theme as an `anaphora`
object with `pronoun`, `resolved_to`, `source_clause`, `source_role`, and
`resolution_policy`; unresolved or incompatible cases such as
`Mary cried because it opened` and `Mary visited Paris because it opened` fail
the internal type check before Coq/Rocq validation.
The bridge now also composes with stative result-state clauses used as
preconditions: `John opened the door because it was closed` becomes
`because_T(holds_state(door, access_scale, closed), Cause(john, Transition(door, access_scale, closed, open)))`.
The pronoun in `it was closed` is resolved to the state-change theme `door`,
and the generated scaffold declares `holds_state : Entity -> StateScale -> State -> Prop`
without exporting `it : Entity`. Scale-incompatible cases such as
`John opened the door because it was red` fail before Coq/Rocq validation.
Negated stative reasons remain proposition-level wrappers rather than new
atomic states: `Mary admired the vase because it was not broken` becomes
`because_T(not_T(holds_state(vase, integrity_scale, broken)), admire(mary, vase))`,
with `it` resolved to the admired object and `not_T : Prop -> Prop`.
Color states are also allowed for concrete compatible objects:
`Mary admired the door because it was red` becomes
`because_T(holds_state(door, color_scale, red), admire(mary, door))`, while
place-like antecedents such as `Mary visited Paris because it was red` still
fail before Coq/Rocq export.
Conjoined stative reasons are preserved structurally:
`Mary admired the door because it was red and open` becomes
`because_T(and_T(holds_state(door, color_scale, red), holds_state(door, access_scale, open)), admire(mary, door))`.
The same type boundary is now lexical rather than a blanket same-scale ban:
`Mary admired the board because it was flat and straight` can pass because
`flat` and `straight` are not registered as incompatible, while explicitly
opposed states such as `the door is closed and open` and
`Mary admired the door because it was closed and open` now fail before
Coq/Rocq export with the diagnostic that `access_scale` has both `closed` and
`open`.
The structured failure also exposes `type_check.incompatible_state_pairs`, and
the web/API diagnostics mirror it as `state_opposition_count` and
`state_opposition_diagnostics`; the page renders those records in a
`State Opposition Diagnostics` panel.
If the available antecedent already carries a state scale, all conjoined
states must be covered; `John opened the door because it was red and open`
therefore fails rather than resolving a color-state clause to an access-scale
transition theme.
The modifier/time case
`John left quickly because Mary cried today` becomes
`because_T(at_T(today, cry(mary)), leave(1)(quickly, john))`, with
`because_T : Prop -> Prop -> Prop`. Clause-level markers outside certified
paths, such as `which`, `whether`, nested because strings such as
`John left because Mary cried because Sue left`, or overextended conditional
strings such as `if John left, Mary cried because Sue left`, produce a
parsing-stage diagnostic instead of being
collapsed into entity names and sent to Coq/Rocq. The controlled exception is a
simple quantifier-NP relative restrictor of the form `who/that` plus either one
intransitive verb or one transitive verb with either one entity object or a
controlled determiner phrase object, optionally with common Adv modifiers and
certified temporal modifiers:
`some boy who laughed loved a girl` renders
`boy(x_boy) and laugh(x_boy)`, `some boy who saw Mary loved a girl` renders
`boy(x_boy) and see(x_boy, mary)`, and
`some boy who saw a girl loved a cat` renders
`boy(x_boy) and exists x_rel_girl : Entity. girl(x_rel_girl) and see(x_boy, x_rel_girl)`,
while `some boy who saw the young girl loved a cat` renders the internal
object description as `(young(x_rel_girl) and girl(x_rel_girl))` rather than as
a constant named `the_young_girl`. Likewise,
`some boy who quickly saw Mary loved a girl` renders
`boy(x_boy) and see(1)(quickly, x_boy, mary)`, with `see` lifted to a
`ModifierSeq`-indexed predicate family. A single non-temporal PP after a named
relative object is treated as another relative-clause `Adv`, not as an entity:
`some boy who quickly saw Mary in the park loved a girl` renders
`boy(x_boy) and see(2)(quickly, in(park), x_boy, mary)`. The normalized
`semantic_readings` entry carries an `attachment_summary` with
`kind: subject_relative_adv`, `subject_relative: mary : Entity`, and typed Adv
modifiers `subject_relative: quickly : Adv` and `subject_relative: in_park : Adv`,
plus a `reading_explanation` sentence that says those Adv items fill predicate
modifier slots while `mary` remains an Entity argument. Thus API clients can audit
the attachment without traversing the raw AST. Likewise,
`some boy who saw Mary yesterday loved a girl` renders
`boy(x_boy) and at_T(yesterday, see(x_boy, mary))`. The sentence
`some boy loved a girl that saw Mary` renders
`girl(x_girl) and see(x_girl, mary)`, while
`some boy loved a girl that saw Mary quickly` exposes both the main-clause Adv
reading and the object-relative-Adv reading. A single non-temporal PP inside a
relative object NP is now split into explicit typed readings:
`some boy who saw a girl in the park loved a cat` exposes a
`subject_relative_object_np_restrictor` reading where
`in_park_np : Entity -> Prop` restricts the internal girl, and a
`subject_relative_adv` reading where `in_park : Adv` modifies the relative
`see` predicate. The timed/manner variant
`some boy who quickly saw a girl in the park yesterday loved a cat` composes the
same two attachments with `quickly` and `at_T(yesterday, ...)`. More complex
relation-clause subjects, such as
`the tall boy who Mary saw yesterday quickly opened the old door with a key`,
and stacked relative object PP cases such as
`some boy who quickly saw Mary in the park with a telescope loved a girl` or
`some boy who saw a girl in the park with a telescope loved a cat`, are still
rejected. This prevents the misleading formula
`leave(0)(if_john, mary_cried)` and keeps unsupported relatives from being
accepted by the lexical state-change rule as single causer constants.

Temporal adverbs such as `yesterday` are emitted as `at(e, yesterday)` before
translation, so `Mary admired the painting yesterday` becomes
`at_T(yesterday, admire(0)(mary, painting))` rather than treating
`painting_yesterday` as one entity. The registered
`plain_transitive_predication` construction now accepts this temporal wrapper
as a certified variant, while still rejecting additional Adv modifiers that
need a separate attachment policy.
Count phrases behave similarly: `Mary visited Paris three times` becomes
`repeat(3, visit(0)(mary, paris))`, not `visit(0)(mary, paris_three_times)`.
The digit form `Mary visited Paris 3 times` follows the same path.
When a temporal adverb scopes over the counted proposition, the registered
`event_counting` construction preserves the outer time wrapper, so
`John knocked twice yesterday` is reported as
`at_T(yesterday, repeat(2, knock(0)(john)))` rather than falling back to a
shallow draft.
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
Shared Adv modifiers are kept as dependent modifier sequences. The sentence
`some boy loved some girl in the bathroom` now exposes the PP attachment
ambiguity explicitly: the `clause_adv` readings render
`love(1)(in(bathroom), x_boy, x_girl)` and declare `in_bathroom : Adv`, while
the `object_np_restrictor` readings render
`girl(x_girl) and in_bathroom_np(x_girl)` and declare
`in_bathroom_np : Entity -> Prop`. Because the readings share one verb symbol,
`love` is lifted to the common type
`forall n : nat, ModifierSeq n -> Entity -> Entity -> PropT`; the unmodified
object-restrictor branch uses `love(0)(x_boy, x_girl)`.
With multiple final PPs, intermediate attachments are enumerated with stable
reading names: `some boy loved some girl in the park with a telescope` includes
a clause-Adv branch, a branch where only `in_park_np` restricts the object, and
a branch where both `in_park_np` and `with_telescope_np` restrict the object.
The article inside `with a telescope` is treated as part of the PP phrase, not
as a new outer scope quantifier.
Predicate-preverbal manner adverbs use the same route: `some boy quickly loved some girl`
renders `love(1)(quickly, x_boy, x_girl)`, declares `quickly : Adv`, and does
not produce the pseudo-entity `some_boy_quickly`.
Intersective adjective NPs are kept inside the binder restrictor rather than
collapsed into entity names: `some young boy quickly loved some happy girl`
renders `(young(x_boy) and boy(x_boy))` and
`(happy(x_girl) and girl(x_girl))`, with `young`, `boy`, `happy`, and `girl`
all exported as `Entity -> Prop` predicates, not pseudo-entities such as
`some_young_boy_quickly` or `some_happy_girl`.
Postnominal PP material inside a quantified NP uses the same restrictor field
with an NP-specific predicate name: `some boy in the park loved some happy girl`
renders `boy(x_boy) and in_park_np(x_boy)`, declares
`in_park_np : Entity -> Prop`, and does not collide with the clause-level
modifier declaration `in_park : Adv`.
Simple NP-internal relative clauses now use that same restrictor discipline:
`some boy who laughed loved a girl` records a `relative_clause_restrictors`
entry for `laugh : Entity -> Prop` and renders
`boy(x_boy) and laugh(x_boy)`, while
`some boy loved a girl that smiled` renders
`girl(x_girl) and smile(x_girl)`. The same field can store a controlled
transitive relative predicate with one entity object: `some boy who saw Mary loved a girl`
declares `see : Entity -> Entity -> Prop` and `mary : Entity`, then renders
`boy(x_boy) and see(x_boy, mary)`. It can also store a controlled determiner
phrase object with its own internal existential binder:
`some boy who saw a girl loved a cat` records an `object_np` with
`variable: "x_rel_girl"` and `girl : Entity -> Prop`, then renders
`boy(x_boy) and exists x_rel_girl : Entity. girl(x_rel_girl) and see(x_boy, x_rel_girl)`.
For descriptive definites such as
`some boy who saw the young girl loved a cat`, the object NP restrictors are
`young : Entity -> Prop` and `girl : Entity -> Prop`; no `the_young_girl`
entity constant is exported. A relative-internal time modifier remains
inside the binder restrictor: `some boy who saw Mary yesterday loved a girl`
renders `boy(x_boy) and at_T(yesterday, see(x_boy, mary))`, and the object-side
variant `some boy loved a girl that saw Mary yesterday` exposes an
`object_relative_time` branch alongside the main-clause time branch. Ordinary
Adv modifiers inside the relative clause use the same dependent modifier
sequence as clause-level modifiers: `some boy who quickly saw Mary loved a girl`
declares `see : forall n : nat, ModifierSeq n -> Entity -> Entity -> PropT`,
declares `quickly : Adv`, and renders
`boy(x_boy) and see(1)(quickly, x_boy, mary)`. If the trailing modifier can
attach either to the main clause or to the object relative, as in
`some boy loved a girl that saw Mary quickly`, the AST exposes both a
`clause_adv` branch and an `object_relative_adv` branch; the unmodified
relative branch uses `see(0)(x_girl, mary)` with `mods_nil`. A named relative
object followed by a single non-temporal PP is also a relative `Adv`:
`some boy who quickly saw Mary in the park loved a girl` keeps `mary : Entity`
and renders `see(2)(quickly, in(park), x_boy, mary)`, without exporting a
`mary_in_park` constant. A relative-object NP with one non-temporal PP receives
the same typed attachment split:
`some boy who saw a girl in the park loved a cat` has a
`subject_relative_object_np_restrictor` branch with
`girl(x_rel_girl) and in_park_np(x_rel_girl)` and a `subject_relative_adv`
branch with `see(1)(in(park), x_boy, x_rel_girl)`. On the object side,
`some boy loved a girl that saw a cat in the park` exposes `clause_adv`,
`object_relative_object_np_restrictor`, and `object_relative_adv` branches. The
marker `who` or `that` is not exported as an entity, and stacked relative-object
PP material such as `a girl in the park with a telescope` remains outside the
certified fragment.
Fronted variants such as `In the bathroom some boy loved some girl` use the
clause-Adv branch only: the modifier parser stops before the quantified subject
and does not collapse the phrase into a malformed `in_bathroom_some` constant.
The same existential-scope rule covers indefinite articles: `a boy loves a
girl` yields `a_boy_wide_scope` and `a_girl_wide_scope`, while mixed forms such
as `a boy loves some girl` preserve both surface quantifiers in the AST instead
of treating `boy` or `girl` as entity constants.
The same structured layer now covers universal/existential interactions:
`every boy loves a girl` yields `every_boy_wide_scope`, rendered as `forall
x_boy : Entity. boy(x_boy) -> exists x_girl : Entity. girl(x_girl) and
love(x_boy, x_girl)`, and `a_girl_wide_scope`, rendered with the existential
girl taking wider scope. The object-universal counterpart `a boy loves every
girl` is handled analogously. In each case `every` is a quantifier binder, not
an `Entity`, and the two readings remain available to the Coq/Rocq scaffold.
Negative quantifiers use the same scope interface but render as restricted
universal negation: `no boy loves a girl` yields `no_boy_wide_scope`, rendered
as `forall x_boy : Entity. boy(x_boy) -> not (exists x_girl : Entity.
girl(x_girl) and love(x_boy, x_girl))`, and `a_girl_wide_scope`, where one girl
takes wider scope over the negative subject binder. `a boy loves no girl` is
handled symmetrically. In both cases `no` is a binder, not an exported
`Entity`, and Adv/time modifiers still attach to the checked quantified
proposition.

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
`construction_summary`, `construction_hygiene`, `coq_check`, `diagnostics`,
`verification_scope`, `certification_upgrade_plan`, and
`construction_rule_draft` fields used by the web page. For registered construction rules,
`construction_summary` gives a sentence-local explanation such as
`Same subject john coordinates eat(bread : Food) and drink(water : Drinkable).`
The `verification_scope` object makes the certification boundary explicit:
registered rules report `kind: registered_construction` and
`certification_level: construction_rule`, while conservative fallback successes
report `kind: fallback_shallow` and `certification_level: shallow_scaffold`.
Failure and unsupported-fragment paths report `certification_level: none`, so a
client cannot mistake a rejected or shallow parse for a fully certified
natural-language interpretation. Fallback scopes also carry
`certification_gaps`: a machine-readable upgrade checklist whose current ids are
`no_registered_construction_rule`, `no_fragment_specific_readings`, and
`no_construction_hygiene_policy`. These gaps record the missing artifacts needed
to promote a shallow fallback result into a registered, construction-level
analysis. Fallback responses now also include a `certification_upgrade_plan`
with `schema_version: "certification_upgrade_plan.v1"`, a generated
`candidate_rule_id`, the target level `construction_rule`, one upgrade step per
gap, and the verification command that should pass after the new construction
has been registered. They also include a `construction_rule_draft` with
`schema_version: "construction_rule_draft.v1"`, the generated candidate
analyzer name, accepted example list, semantic-reading draft, construction
hygiene policy draft, test draft, and patch-text preview. The draft is marked
`automation_mode: "human_review_required"` and `can_auto_apply: false`: it is a
machine-readable promotion artifact for authors, not an automatic claim that the
fallback sentence has become construction-level certified. The same payload is
available from `/api/construction-rule-draft`, with `download=1` returning a
JSON artifact for review. The deterministic verifier now checks this route even
when the local HTTP smoke test is unavailable: the
`construction_rule_draft_response.v1` wrapper must carry the same
`construction_rule_draft`, `verification_scope`, and `diagnostics` as the
ordinary analysis, and the page's raw draft JSON preview must match the API
payload exactly. The same promotion contract also cross-checks the
`certification_upgrade_plan` against the draft: candidate rule id, source
sentence, dependent-type translation, AST summary, semantic-reading draft,
test draft, verification command, and patch-text preview must agree before the
fallback artifact is treated as a coherent human-review candidate.
The draft now also embeds `registration_preflight` with
`schema_version: "construction_rule_registration_preflight.v1"`. This preflight
checks that the candidate rule id and analyzer name do not collide with the
live construction registry, that accepted examples, semantic-reading drafts,
hygiene fragments, and a registration test draft are present, and that
`can_auto_register` remains `false` with `registration_status:
"human_review_required"`. In other words, the artifact can be reviewed as a
coherent candidate, but the system still refuses to auto-register it as a
certified construction.
The project-level coverage boundary is available separately at
`/api/certified-fragment` with `schema_version: "certified_fragment.v1"`.
That manifest is generated from the live registered construction table rather
than from a hand-written README list. It reports
`full_natural_language_certification: false`, one row per registered
construction rule with `certification_level: construction_rule`, the fallback
row with `certification_level: shallow_scaffold`, and the unsupported
clause-marker guard set. The fallback row also repeats the same
`certification_gaps`, so the certified-fragment manifest describes not only what
is accepted but what remains to be supplied before a fallback sentence can be
claimed as certified. The page renders the same data in a `Certified Fragment`
panel, so users can distinguish the current certified fragment from the
stronger, still-open goal of arbitrary natural-language certification.
The same manifest now includes a `coverage_matrix` with four audited slices:
`registered_success_cases`, `registered_variant_success_cases`,
`fallback_success_cases`, and `rejected_unsupported_cases`. Registered cases
point back to each rule's primary example, registered variants capture
composition examples such as `John knocked twice yesterday` under
`temporal_event_counting`, `Mary smiled yesterday` under
`temporal_plain_intransitive_predication`, `Mary laughed loudly yesterday`
under `temporal_manner_intransitive_predication`, `Mary laughed loudly in the
park yesterday` under `temporal_manner_locative_intransitive_predication`,
`Mary admired the painting red yesterday` under `temporal_resultative_predication`,
plus modifier-sequence
variants such as
`multi_adv_modified_transitive_predication` and
`temporal_multi_adv_modified_transitive_predication`,
`triple_adv_modified_transitive_predication`, and
`temporal_triple_adv_modified_transitive_predication`,
`quad_adv_modified_transitive_predication`, and
`temporal_quad_adv_modified_transitive_predication`,
`quint_adv_modified_transitive_predication`, and
`temporal_quint_adv_modified_transitive_predication`; fallback cases remain
explicitly shallow, and rejected cases record the marker that must stop the
pipeline before fallback.
The manifest also exposes `surface_parser_coverage` for the modified
transitive Adv-sequence family. That record states the open-ended type
principle `forall n : nat, ModifierSeq n -> Entity -> Entity -> PropT`, while
marking the current surface parser claim as `registered_examples_only` and
`full_surface_parser_certification: false`. Its audited modifier counts are
`1,2,3,4,5` for both timed and untimed registered examples. This makes the
boundary machine-readable: the dependent type family is not capped at five
modifiers, but the present web parser only certifies the registered examples it
actually smoke-tests.
The same record now includes a `verified_examples` witness list. Each witness
stores the variant id, surface sentence, modifier count, whether the clause is
time-wrapped, and whether the example came from the registered primary example
or from the registered variant matrix. The page mirrors those witnesses through
`data-surface-example-*` hooks, so an API client can audit the advertised parser
boundary against concrete tested sentences rather than trusting only aggregate
counts. Each witness also carries its expected analysis label, expected AST
kind, and dependent-type translation fragments, tying the parser boundary to
the same checked semantic contract used by the live analyzer smoke tests. The
project verifier reruns every witness sentence and rejects any drift in the
matched construction rule, analysis label, AST kind, or translation fragments.
Regression tests also simulate each of those live-witness drift modes directly,
so the check is guarded by counterexamples rather than by a text-only assertion.
The coverage object also carries a `witness_generation_spec` for this finite
front-end prefix: it records the base clause, ordered modifier prefix, optional
`yesterday` time suffix, variant-id mapping, and translation templates. The
verifier rebuilds the advertised witness sentences and expected translation
fragments from that spec before running the live analyzer, which turns the
finite coverage claim into a generated contract rather than a hand-maintained
list alone.
Finally, `slot_probe_examples` adds a smaller lexical-slot stability check. It
reruns controlled substitutions for the Agent, Theme, predicate, and one
combined timed five-modifier case, while keeping
`full_lexical_slot_certification: false`. These probes are now generated from a
`probe_generation_spec` that records the base lexical frame, surface templates,
slot substitutions, modifier prefix lengths, and translation templates. The
verifier rebuilds the probe sentences and expected dependent-type fragments
from that spec before running the live analyzer. These probes make sure the
current front end does not accidentally bake the surface contract into only the
Mary / painting / admire example, without claiming arbitrary lexical
replacement. A companion `matrix_examples` contract now enumerates a small
2-by-2-by-2 lexical-frame matrix over Mary/John, admire/photograph, and
painting/sculpture under both a one-Adv untimed profile and a timed five-Adv
profile. This gives the certified fragment a broader, generated stability
check while still marking `full_lexical_matrix_certification: false`. The
matrix also carries an axis-level type contract: agents and themes are
`Entity`-typed role bearers, predicates are dependent transitive Adv families
of type `forall n : nat, ModifierSeq n -> Entity -> Entity -> PropT`,
modifiers are `Adv`, and timed rows use a `Time -> PropT -> PropT` operator.
That contract is now exposed as a `surface_type_contract_registry.v1` object
implemented in `translator/surface_type_contracts.py`; its `registry_id`
identifies the concrete `modified_transitive_adv_sequence.surface_slot_matrix`
contract. The registry now also contains six `surface_type_contract_entry.v1`
records, so the matrix axes can be reconstructed by querying individual
agent, predicate, and theme entries rather than by trusting only a copied
axes block. The registry is also checked by
`validate_surface_type_contract_registry`, which rejects schema drift,
duplicate slot entries, entry-count drift, and copied axes that no longer
match the entry records. It now also audits the modifier and time contracts
field by field, so modifier material must remain `Adv` with constructor type
`Entity -> Adv`, modifier objects cannot be reintroduced as events, and
temporal material must remain `Time` with a proposition-level
`Time -> PropT -> PropT` operator. The registry carries a
`surface_type_contract_diagnostic.v1` category table for those checks, covering
registry schema, entry/axis synchronization, role frames, modifier typing, and
time typing; the API and page mirror these categories so a failed boundary can
be identified without reading raw Python exceptions. The verifier checks that
the copied axis, modifier, time, and lexical-frame fields remain synchronized
with that source.
It also exposes `semantic_snapshots`: one static, rule-indexed summary per
registered construction. Each snapshot records the expected analysis label,
required dependent-type translation fragments, semantic-reading names and
sources, exported Coq/Rocq definition names, and the internal type-check result.
Each snapshot also includes `expected_ast_summary`, a compact structural digest
covering AST kind, predicate symbols and types, entity/state symbols, time
binders, quantifier signatures, and core list counts. The verifier runs the
live pipeline against those snapshots, so a parser or exporter change that
silently alters the certified fragment's core semantics or AST shape is
reported as snapshot drift.
Successful registered rules must expose a passing `semantic_readings_check`.
Rules with explicit ambiguity keep their specialized readings; otherwise the
registered-rule boundary creates a conservative single reading from the unique
exported Coq/Rocq `Definition ... : Prop/PropT`.
Ordinary fallback successes carry that row in JSON as well: clients should see
`fallback_single_reading` from `fallback_event_semantics`, linked to
`example_1`, with a `none` attachment summary and a passing
`semantic_readings_check`.
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
When those failed indices point to a reading-local type error,
`diagnostics.reading_type_check_failure_count` and
`diagnostics.reading_type_check_diagnostics` expand the affected reading name,
scope, Coq/Rocq definition, local `type_check` path, local error list, and any
nested state-opposition diagnostics; the page renders the same data in a
`Reading Type Check Diagnostics` panel with `data-reading-type-check-*` hooks.
The verifier treats this as a fixed schema: the definition-name fields must be
string lists, the index fields must be integer lists, `expected_export_count`
must be either an integer or `null`, and `observed_export_count` must be an
integer. It now also validates `reading_type_check_diagnostics` itself:
`reading_type_check_failure_count` must match the list length, each record's
`error_count` and `state_opposition_count` must match its nested lists, the
path must stay at `semantic_readings[i].type_check`, and the HTML panel must
carry matching `data-reading-type-check-index`, name, source, scope,
Coq-definition, path, error, and state-opposition-count hooks. It also checks
that the failed reading indices agree across `reading_type_check_diagnostics`,
`semantic_readings_repair_details.failed_type_check_indices`, and the
specialized `fix_reading_type_checks.reading_indices` recovery action, so a
repair/export bundle cannot point at a different reading from the one that
actually failed.
For the same boundary, `diagnostics.recovery_actions` is specialized from
those repair details: missing exports produce `add_missing_coq_definitions`
with `target_definitions`, duplicate names produce `rename_duplicate_readings`,
malformed records and local type-check failures identify `reading_indices`, and
registered-rule export-count mismatches produce `normalize_reading_exports`
with expected and observed counts.
Ordinary failed `/api/analyze` responses also expose a top-level
`surface_type_contract_diagnostics` object. This keeps real input failures,
such as parser failures or dependent-type failures, tied to the same
`surface_type_contract_diagnostic.v1` category table used by the certified
surface matrix. The HTML page renders the same context in a
`Surface Type Contract Diagnostics` panel with stable
`data-surface-type-contract-*` hooks. The same context is mirrored on every
ordinary failure `Next Steps` action row through
`data-action-surface-type-contract-*` hooks, so repair buttons can remain tied
to the registry, role-frame, modifier-type, and time-type boundary they are
meant to protect.
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
repair plan, the shared diagnostic contract, and a
`surface_type_contract_diagnostics` object. That surface context points back to
the `surface_type_contract_diagnostic.v1` category table, so a downloaded
failure-local repair bundle still records the registry, role-frame,
modifier-type, and time-type boundaries that are being protected. The repair plan records
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
Ordinary failed analyses use the same inspection schema through
`/api/analyze-action-run?sentence=<sentence>&index=<n>`, and they can export
the action itself through `/api/analyze-action?sentence=<sentence>&index=<n>`.
For example, the ordinary type-check failure `the plant killed` exposes an
`inspect_ast` action whose action bundle uses `diagnostic_recovery_action.v1`
with `source: "analyze"` and downloads as
`analyze_recovery_action__the-plant-killed__0.json`. The same ordinary
`Next Steps` row renders an expandable `Action JSON` preview whose content must
match that `/api/analyze-action` bundle before the verifier accepts the page;
its run bundle snapshots `ast` and `type_check`, preserves
`surface_type_contract_diagnostics`, and downloads as
`analyze_inspection_run__the-plant-killed__0.json`. The same project-level
check now walks a small ordinary-failure matrix: empty input is normalized to
the `input` stage with an `edit_input` action, `John` is treated as a `parsing`
failure with a `revise_sentence` action, `if John left, Mary cried because Sue
left` remains a `parsing` failure with `verification_scope.kind:
rejected_unsupported_fragment`, and `the plant killed` remains the `type_check`
example with an `inspect_ast` action under the registered construction scope
`construction_rule` for `lexical_state_change`. The human-review actions must still export
row-local action JSON, but their inspection-run route must return a
`diagnostic_inspection_run.v1` rejection rather than an executable snapshot. The ordinary
`diagnostics.recovery_actions` entry now carries the same machine-readable
`api_path`, `download_api_path`, `download_filename`, `automation_mode`,
`can_auto_run`, `can_auto_apply`, `target_fields`, `inspection_run_api_path`,
`inspection_run_download_api_path`, and `inspection_run_download_filename`
metadata, with those inspection-run paths set to `null` for human-review
actions. Human-review actions such as `edit_input` and `revise_sentence` are
exportable as review bundles, but rejected by the inspection-run endpoint with
the same `diagnostic_inspection_run.v1` error shape instead of being treated as
automatic repairs.
The same fixture pages render a `Recovery Action Exports` panel that lists
those action JSON routes with their schema, case, index, action kind, and
failure stage, and it mirrors the surface type diagnostic schema, category
count, category ids, and registry id in stable data attributes, so browser
checks can verify the export contract without opening each link manually. Each export row also includes an expandable `Action JSON`
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
`required_fixture_stages`, `recovery_action_kinds`, and
`semantic_reading_fields`.
The verifier rejects schema drift, failure-stage drift, required-fixture-stage
drift, recovery-action drift, semantic-reading field drift, and stale selector
links to that contract endpoint.
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
It also requests the registered event-counting route
`/api/analyze?sentence=John+knocked+twice&require_coq=1` and the matching HTML
page, requiring both surfaces to expose `event_counting_single_reading` under
the registered `event_counting` construction. It then requests the timed
variant `/api/analyze?sentence=John+knocked+twice+yesterday&require_coq=1`,
requiring the same construction to expose
`at_T(yesterday, repeat(2, knock(0)(john)))` without a fallback draft. The
same smoke check now also requests the registered active argument-omission route
`/api/analyze?sentence=John+ate&require_coq=1`, requiring both surfaces to expose
`active_argument_omission_single_reading`, the `omitted_existential_theme` scope,
and no construction-rule draft. It then requests the registered plain
intransitive route `/api/analyze?sentence=Mary+smiled&require_coq=1`, requiring
`plain_intransitive_predication_single_reading`, the `explicit_agent` scope, and
no construction-rule draft. Its timed variant
`/api/analyze?sentence=Mary+smiled+yesterday&require_coq=1` must keep the same
registered rule while rendering `at_T(yesterday, smile(0)(mary))` with the
`explicit_agent_at_time` scope. It then requests the registered
manner-intransitive route
`/api/analyze?sentence=Mary+laughed+loudly&require_coq=1`, requiring
`manner_intransitive_predication_single_reading`, the
`explicit_agent_with_manner_adv` scope, and `Parameter loudly : Adv.` rather
than `Parameter loudly : Entity.`. Its timed variant
`/api/analyze?sentence=Mary+laughed+loudly+yesterday&require_coq=1` must keep
the same registered rule while rendering
`at_T(yesterday, laugh(1)(loudly, mary))` with the
`explicit_agent_with_manner_adv_at_time` scope and no construction-rule draft.
It then requests the registered manner-locative intransitive route
`/api/analyze?sentence=Mary+laughed+loudly+in+the+park&require_coq=1`,
requiring `manner_locative_intransitive_predication_single_reading`, the
`explicit_agent_with_manner_and_location_adv` scope, `Parameter loudly : Adv.`,
and `Parameter in_park : Adv.` rather than entity declarations. Its timed
variant
`/api/analyze?sentence=Mary+laughed+loudly+in+the+park+yesterday&require_coq=1`
must keep the same registered rule while rendering
`at_T(yesterday, laugh(2)(loudly, in(park), mary))` with the
`explicit_agent_with_manner_and_location_adv_at_time` scope and no
construction-rule draft. It then requests the registered
plain-transitive route `/api/analyze?sentence=Mary+admired+the+painting&require_coq=1`, requiring
`plain_transitive_predication_single_reading`, the `explicit_agent_theme` scope,
and no construction-rule draft. It also requests the timed plain-transitive
variant
`/api/analyze?sentence=Mary+admired+the+painting+yesterday&require_coq=1`,
requiring `at_T(yesterday, admire(0)(mary, painting))`, the
`explicit_agent_theme_at_time` scope, and no construction-rule draft. It then
requests the registered modified-transitive route
`/api/analyze?sentence=Mary+admired+the+painting+in+the+gallery&require_coq=1`,
requiring `modified_transitive_predication_single_reading`,
`explicit_agent_theme_with_adv`, and `Parameter in_gallery : Adv.` rather than
`Parameter in_gallery : Entity.`. The timed modified-transitive variant
`/api/analyze?sentence=Mary+admired+the+painting+in+the+gallery+yesterday&require_coq=1`
must keep the same rule while rendering
`at_T(yesterday, admire(1)(in(gallery), mary, painting))` and
`explicit_agent_theme_with_adv_at_time`. The same rule now also checks the
two-Adv sequence
`/api/analyze?sentence=Mary+admired+the+painting+in+the+gallery+with+a+telescope&require_coq=1`
as `admire(2)(in(gallery), with(telescope), mary, painting)`, requiring both
`Parameter in_gallery : Adv.` and `Parameter with_telescope : Adv.`. Its timed
variant renders
`at_T(yesterday, admire(2)(in(gallery), with(telescope), mary, painting))` with
the `explicit_agent_theme_with_adv_sequence_at_time` scope and no fallback
draft. It also checks the three-Adv sequence
`/api/analyze?sentence=Mary+admired+the+painting+in+the+gallery+with+a+telescope+near+a+window&require_coq=1`
as `admire(3)(in(gallery), with(telescope), near(window), mary, painting)`,
requiring `Parameter near_window : Adv.` together with the earlier Adv
declarations. Its timed variant renders
`at_T(yesterday, admire(3)(in(gallery), with(telescope), near(window), mary, painting))`
with the same sequence scope under `at_T`. It also checks the four-Adv sequence
`/api/analyze?sentence=Mary+admired+the+painting+in+the+gallery+with+a+telescope+near+a+window+beside+a+shelf&require_coq=1`
as `admire(4)(in(gallery), with(telescope), near(window), beside(shelf), mary, painting)`,
requiring `Parameter beside_shelf : Adv.` together with the earlier Adv
declarations. Its timed variant remains registered under `at_T`. It also checks
the five-Adv sequence
`/api/analyze?sentence=Mary+admired+the+painting+in+the+gallery+with+a+telescope+near+a+window+beside+a+shelf+under+a+lamp&require_coq=1`
as `admire(5)(in(gallery), with(telescope), near(window), beside(shelf), under(lamp), mary, painting)`,
requiring `Parameter under_lamp : Adv.` and no `Parameter under_lamp : Entity.`;
the timed five-Adv variant remains registered under `at_T`. It then
requests the registered locative route
`/api/analyze?sentence=a+cat+sits+on+a+mat&require_coq=1`, requiring both
surfaces to expose `locative_intransitive_predication_single_reading`, the
registered `locative_intransitive_predication` rule, and `Parameter on_mat :
Adv.` rather than `Parameter on_mat : Entity.`. The ordinary fallback success
contract is checked separately with
`/api/analyze?sentence=Mary+laughed+loudly+in+the+park+near+a+window+yesterday&require_coq=1`,
requiring both surfaces to expose the same `fallback_single_reading` row, the
typed scaffold `at_T(yesterday, laugh(3)(loudly, in(park), near(window), mary))`, and the
construction-rule draft before the diagnostic fixture sweep begins.
The same live boundary now requests
`/api/analyze?sentence=some+boy+loves+some+girl&require_coq=1` and checks the
two quantifier-scope readings, `some_boy_wide_scope` and
`some_girl_wide_scope`, against their JSON records, Coq/Rocq definitions, and
HTML reading rows.
It also requests
`/api/analyze?sentence=Mary+saw+John+leave&require_coq=1`, requiring the
registered perception-complement analysis to export `mary_saw_john_leave`,
render the `perception_nominalization` reading, and keep the Coq/Rocq scaffold
at `E : Prop -> Entity` rather than reintroducing event-role declarations.
It also requests
`/api/analyze?sentence=after+the+singing+of+the+Marseillaise%2C+John+saluted+the+flag&require_coq=1`,
requiring the registered timed-after analysis to export `after_singing_salute`,
render the `timed_after_singing_salute` reading, and keep the order relation at
`before : Time -> Time -> Prop` rather than an event-ordering parameter.
It now also requests
`/api/analyze?sentence=In+every+burning%2C+oxygen+is+consumed&require_coq=1`,
requiring the registered universal timed burning analysis to export
`every_burning_consumes_oxygen`, render the `universal_timed_burning` reading,
and keep the scaffold at `Time`, `burn : Entity -> Time -> Prop`, and
`consume : Entity -> Time -> Prop` rather than reintroducing `Event` or `IN`.
These ordinary success checks now share the same success-envelope,
semantic-reading-summary, and fragment guards in the verifier, so fallback,
quantifier, perception, timed-after, and burning cases cannot silently drift
through five separately maintained copies of the same HTTP acceptance logic.
The same live checks now require the JSON payload and HTML page to expose
matching `verification_scope` metadata: fallback remains visibly shallow,
whereas the registered quantifier, perception, timed-after, and burning cases
are marked as construction-rule certification.
The smoke check also fetches `/api/certified-fragment` and checks that the
matching page panel exposes `certified_fragment.v1`, the registered rule count,
each registered rule id, `full_natural_language_certification=false`, and the
fallback `shallow_scaffold` level.
It also checks the coverage-matrix counts and page hooks for registered,
fallback, and rejected examples. Unit tests run the manifest's registered
success cases, fallback success cases, and rejected unsupported cases against
the actual pipeline, so the coverage matrix cannot become a prose-only
inventory.
The certified-fragment smoke check also validates `semantic_snapshot_count`,
the per-rule snapshot hooks in HTML, and the live analyzer output against every
snapshot's expected analysis, readings, Coq/Rocq definitions, and translation
fragments. It also compares each live AST against `expected_ast_summary` and
checks the page's `data-semantic-snapshot-ast-kind` hooks.
It walks every fixture case listed by the manifest and checks the API payload,
selected HTML option, API/HTML route case parameter, failure stage, and
recovery-action metadata for each one.
For fixture cases whose `semantic_readings_check` passes, the same smoke check
also requires each normalized reading to carry the contract fields and verifies
that `reading_explanation` is rendered as the row's `interpretation`.
The core `check_semantic_readings` boundary now enforces the same normalized
reading contract for ordinary analyzer outputs: missing `scope`, `source`,
`coq_definition`, `type_check`, `attachment_summary`, or `reading_explanation`
is a malformed semantic-reading failure before construction hygiene or
Coq/Rocq validation can run. The shared `semantic_reading` constructor emits a
`none` attachment summary and a conservative interpretation sentence for
single-reading constructions that do not have specialized PP, time, or relative
attachments.
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
definition, exported status, reading-local type-check status, human-readable
interpretation, attachment kind, typed Adv modifiers, typed NP restrictors,
typed time modifiers, and relative objects, followed by
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
- registered causal-resultative predication into a typed state transition;
- simple conditionals represented as implication between typed propositions,
  including typed transitive objects such as `bread : Food` and
  `water : Drinkable`, plus clause-local temporal wrappers such as
  `at_T(yesterday, leave(john))`, ModifierSeq-indexed Adv clauses such as
  `eat(1)(quickly, john, bread)`, clause-local do-support negation such as
  `not_T(leave(1)(quickly, john))`, and two-subject clause coordination such as
  `and_T(eat(2)(quickly, in(park), john, bread), eat(2)(quickly, in(park), mary, bread))`;
  the same predicate can also mix a modified and unmodified clause, as in
  `if John left quickly, Mary left`, where the unmodified branch is rendered
  as `leave(0)(mary)` and checked with `mods_nil` rather than a conflicting
  plain `Entity -> Prop` declaration;
- simple because-clauses represented as proposition-level causal connection,
  for example `John left because Mary cried` as
  `because_T(cry(mary), leave(john))`, and the typed transitive variant
  `John ate bread because Mary drank water yesterday` as
  `because_T(at_T(yesterday, drink(mary, water)), eat(john, bread))`, with
  `because_T : Prop -> Prop -> Prop`; the same rule composes with lexical
  state changes, for example `John opened the door because Mary cleaned the room`
  as `because_T(Cause(mary, Transition(room, cleanliness_scale, dirty, clean)), Cause(john, Transition(door, access_scale, closed, open)))`,
  and mixed simple/state-change cases such as `Mary cried because the door opened`
  as `because_T(Change(Transition(door, access_scale, closed, open)), cry(mary))`;
  the same construction has a controlled state-change anaphora bridge, for
  example `Mary admired the door because it opened` as
  `because_T(Change(Transition(door, access_scale, closed, open)), admire(mary, door))`,
  while unresolved `it` cases fail before Coq/Rocq export; stative
  preconditions such as `John opened the door because it was closed` render as
  `because_T(holds_state(door, access_scale, closed), Cause(john, Transition(door, access_scale, closed, open)))`,
  and negated stative reasons such as
  `Mary admired the vase because it was not broken` render as
  `because_T(not_T(holds_state(vase, integrity_scale, broken)), admire(mary, vase))`;
  concrete color-state reasons such as `Mary admired the door because it was red`
  render as `because_T(holds_state(door, color_scale, red), admire(mary, door))`,
  and conjoined color/access-state reasons such as
  `Mary admired the door because it was red and open` render as
  `because_T(and_T(holds_state(door, color_scale, red), holds_state(door, access_scale, open)), admire(mary, door))`,
  while place-like color antecedents and partial state-scale matches remain rejected;
- a certified-fragment guard that rejects unsupported subordinate,
  complement, interrogative, and relative-clause markers before fallback or
  Coq/Rocq validation, except for controlled quantifier-NP relatives such as
  `some boy who laughed loved a girl` and
  `some boy who saw Mary loved a girl`, plus timed variants such as
  `some boy who saw Mary yesterday loved a girl` and Adv variants such as
  `some boy who quickly saw Mary loved a girl`, which are rendered as ordinary
  binder restrictors over `Entity -> Prop`, `Entity -> Entity -> Prop`, or
  `ModifierSeq`-indexed predicates, with temporal operators scoped inside the
  restrictor when present.

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
The object-final resultative slice has also been promoted out of ordinary
fallback. Simple result phrases whose final object-position word is a known
result state, such as `John hammered the metal flat`, now run through the
registered `resultative_predication` rule and become
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
Successful registered resultatives expose
`resultative_predication_single_reading` with scope
`explicit_agent_theme_result`; simple temporal wrappers such as `Mary admired
the painting red yesterday` keep the same registered construction and use the
scope `explicit_agent_theme_result_at_time`. Construction hygiene rejects hidden
`Event`, `Agent`, `Theme`, and `ResultState` predicate fragments.
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
and a web route smoke check that requests ordinary `/api/analyze` fallback and
quantifier-scope successes plus a registered perception-complement success
plus registered timed-after and universal timed burning successes before the
diagnostic fixture manifest through the local HTTP handler.

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
style rendering. It also accepts a controlled natural-language fragment, while
explicitly rejecting sentence forms outside the certified fragment before
proof-assistant validation. The accompanying paper explains the broader
theoretical architecture needed to replace event semantics across variable
polyadicity, argument omission, thematic roles, event quantity, causation, and
resultatives.

## Status

Early research prototype and manuscript draft.

## Citation

If you build on this project, cite the manuscript draft in `paper/` and the
background work discussed there, especially Luo and Shi's type-theoretic
analysis of variable polyadicity without events.
