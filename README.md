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

Quantifier-scope examples receive a separate ambiguity analysis instead of
being forced through the fallback parser:

```bash
python3 -m translator.natural_language_pipeline \
  "some boy loves some girl" \
  --require-coq
```

This produces both subject-wide and object-wide existential readings and checks
the generated Coq scaffold. The intermediate AST stores each reading as a
structured scope order with bound variables, `Entity -> Prop` restrictor
predicates, and an `Entity -> Entity -> Prop` relation before any formula string
is rendered. Coq/Rocq verifies the exported formal terms; it does not by itself
prove that an arbitrary natural-language parse is the only correct semantic
analysis. The quantifier-scope scaffold does not introduce an `Event` type:
`boy` and `girl` are predicates of type `Entity -> Prop`, and `love` is typed
directly as `Entity -> Entity -> Prop`.

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
introduce a hidden `Event` parameter for this sentence.

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
The burning example uses universal time quantification:
`forall x : Entity, forall t : Time, burn x t -> consume oxygen t`. Its AST
stores the binders `x : Entity` and `t : Time`, then checks that both `burn` and
`consume` have type `Entity -> Time -> Prop` and share the same time variable.
Both generated Coq scaffolds are checked without introducing an `Event` type.

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
lemma, and the lexicon module that supplied the mapping.

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
three relevant checks for user interfaces:

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
`modifier_role_audit`, `lexicon_patch_drafts`, `patch_text_preview`, `construction_rule`,
`construction_hygiene`, `coq_check`, and `diagnostics` fields used by the web
page. The page also renders an `API Contract` panel with the same schema
version and endpoint, so browser users and automated clients can check the
contract without inspecting raw network traffic, and a `Conclusion` panel with
the same short outcome string returned by the API.

For failures, `diagnostics.failure_stage` distinguishes `input`, `parsing`,
`type_check`, `construction_hygiene`, and `coq_check` failures.
`diagnostics.recovery_hint` gives a short next-step suggestion for that failure
stage, while `diagnostics.recovery_actions` exposes the same advice as
structured actions for frontends and automation. Registered construction rules
stop at the first failed stage: if internal AST `type_check` fails,
construction hygiene and Coq/Rocq validation are reported as `skipped` rather
than attempted.
The local web page renders those structured actions in a separate `Next Steps`
panel. Each rendered action carries a stable `data-action-kind` attribute and a
`next-step--<kind>` CSS class for frontend automation.
It also renders a dedicated `Type Check` panel, so construction-specific AST
errors such as an unlicensed lexical state-change frame are visible beside the
AST instead of being hidden behind the status banner.
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
records. Each draft includes a stable `draft_id` and a
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

The same bundle is available from the web service at
`/api/lexicon-patch-drafts?sentence=Mary+painted+the+door+red&require_coq=1`.
Use `format=patch` on that endpoint to receive the review-only patch text as
`text/plain`. The web page also renders a source-state form for each pending
draft; submitting it previews the resolved patch through structured
`resolve_draft_id` and `source_state` parameters without mutating the lexicon.

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
web page renders the same text in a `Lexicon Patch Text Preview` panel with an
`Open patch text` link backed by `format=patch`, and the command-line exporter
can additionally write that review-only candidate patch text with `--patch-out`.
File outputs create missing parent directories, so review bundles and patch
previews can be written into a fresh `work/` tree.

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

The GitHub Actions workflow runs the portable deterministic checks with
`--skip-coq`, because GitHub's default Ubuntu runner does not provide a local
Coq/Rocq installation. It installs the document extra and also passes
`--require-docx`, so the Word-generation tests must really run instead of being
silently skipped. Use `--require-coq` locally when proof-assistant boundary
validation is required.

Run all deterministic project checks through one entry point:

```bash
python3 scripts/verify_project.py
```

This includes a package-build smoke check that runs
`pip wheel --no-build-isolation --no-deps`, using the active Python
environment's local build tooling rather than requiring a network fetch for
build dependencies. It also runs a smoke check for the lexicon patch exporter,
verifying that it can write both the JSON bundle and review-only patch text.

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
python3 scripts/verify_project.py --skip-coq --require-docx
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
