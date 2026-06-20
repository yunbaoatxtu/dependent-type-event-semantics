# Web Pipeline Design

This project can support a web interface with visible verification panels:

1. Natural-language input
2. Event-semantics analysis
3. Dependent-type translation
4. Result-state lexicon audit records
5. Internal diagnostics and next steps
6. Coq/Rocq boundary validation

The current repository implements the first small backend slice in
`translator/natural_language_pipeline.py`. It combines hand-written analyses
for the main research examples with a conservative fallback parser for simple
English sentences. This keeps the verification problem honest: the user can see
where parsing succeeds, where translation succeeds, and where Coq validation
succeeds, while unlisted sentences receive a shallow first-pass analysis rather
than a false claim of full semantic understanding.

The repository also includes a small dependency-free local web demo in
`web/app.py`. It is intended as a thin interface over the verified backend, not
as a separate semantic implementation. The page renders `result_state_lexicon`
twice: a compact human-readable Result State Lexicon panel and a raw JSON panel
for exact audit data. It also renders a dedicated Type Check panel, so failed
construction-specific AST checks expose their error list directly instead of
forcing users to infer the problem from the status banner alone.

## Proposed Request Flow

```text
sentence
  -> sentence_to_event_semantics(sentence)
  -> translate(event_semantics_json)
  -> export_module([translation], "coq")
  -> verify_coq_code(coq_code)
  -> web response
```

The local page is started with:

```bash
python3 -m web.app --port 8765
```

## API Contract

The web demo exposes the same checked pipeline as a JSON endpoint:

```text
GET /api/analyze?sentence=Mary+saw+John+leave&require_coq=1
```

It also exposes the lexicon repair queue alone:

```text
GET /api/lexicon-patch-drafts?sentence=Mary+painted+the+door+red&require_coq=1
```

For clients that only need the review patch text:

```text
GET /api/lexicon-patch-drafts?sentence=Mary+painted+the+door+red&require_coq=1&format=patch
```

After a reviewer chooses a source state, the same endpoint can validate the
choice without changing the repository:

```text
GET /api/lexicon-patch-drafts?sentence=Mary+painted+the+door+red&require_coq=1&resolve=state-red--unknown_source_allowed=not_red
```

The same resolution can be submitted as structured query fields:

```text
GET /api/lexicon-patch-drafts?sentence=Mary+painted+the+door+red&require_coq=1&format=patch&resolve_draft_id=state-red--unknown_source_allowed&source_state=not_red
```

The request has two stable query parameters:

- `sentence`: required natural-language input;
- `require_coq`: optional flag, where `1` requests the external Coq/Rocq
  boundary check and the default leaves it skipped when not needed.

The response is a single JSON object with `schema_version: "analyze.v1"` so
clients can distinguish this contract from later API revisions. On success, it
must expose the same semantic artifacts shown on the page: `event_semantics`,
`dependent_type_translation`, `result_state_lexicon`, `modifier_role_audit`,
`lexicon_patch_drafts`, `patch_text_preview`, `semantic_readings`,
`semantic_readings_check`, `ast`, `coq_code`, `construction_rule`,
`construction_summary`,
`construction_hygiene`, `coq_check`, `diagnostics`, and `conclusion`.
The page mirrors that version in a compact `API Contract` panel, including the
`/api/analyze` endpoint, so a browser screenshot and a JSON client can refer to
the same response contract. It also renders the response `conclusion` in a
dedicated `Conclusion` panel so the final outcome is visible outside the status
line.
`result_state_lexicon` is a list of audit
records for resultative targets; each record includes the target `state`, its
`scale`, an optional `default_source_state`, and a `source_policy` such as
`lexical_prestate` or `unknown_source_allowed`. `lexicon_patch_drafts` lifts
the repair templates from warning actions into a top-level list that clients
can treat as a candidate STATE_LEXICON patch queue. On any failure, it must
still return `ok: false`, an `error` message when available, and a
`diagnostics` object so callers can distinguish parser, type-checking,
semantic-readings-audit, construction-hygiene, and Coq/Rocq boundary failures.

`modifier_role_audit` is a flat list extracted from the AST. Each record gives
the application path, function, modifier string, `Adv` type, and semantic role,
so the page can show a `Modifier Role Audit` panel without making the frontend
traverse the full AST. The path is structural: a modifier inside a temporal
wrapper is reported at a nested path such as `ast.body`, rather than being
dropped or flattened into an ambiguous top-level record. Each record also
carries the nested `surface_lexicon` audit from the AST, including
`surface_modifier`, `normalized_modifier`, `type`, `semantic_role`, and the
source module, so API clients can confirm that the displayed modifier is the
same `Adv` constant exported to Coq/Rocq.

`diagnostics.failure_stage` is the machine-readable failure locator. It is
`null` on successful translations and otherwise one of `input`, `parsing`,
`type_check`, `semantic_readings_check`, `construction_hygiene`, or
`coq_check`.
`diagnostics.recovery_hint` is `null` on success and otherwise gives a compact
next-step suggestion tied to the failure stage.
`diagnostics.recovery_actions` is an array of structured action objects with
`kind`, `label`, and `detail` fields so a frontend can render repair steps
without parsing prose.
`diagnostics.warnings` is an array of non-fatal semantic audit notices. It is
empty for fully specified result-state transitions such as `hammered ... flat`,
but records cases such as `painted ... red` where the target state is typed and
checked while the source state remains `unknown_state`. Warning kinds currently
cover `unknown_result_source`, `derived_result_scale`, and
`source_state_used_as_target`, corresponding to `unknown_source_allowed`,
`derived_scale_no_known_prestate`, and `source_state_only` lexicon policies.
`manual_repair_required` and `lexicon_patch_draft_count` summarize whether
those warnings produce human-gated lexicon repair drafts.
Each warning includes a `suggested_action` object with `kind`, `label`, and
`detail` fields; warning actions currently include `add_state_prestate`,
`register_state_lexicon_entry`, and `license_state_as_target`. Suggested
actions also include a `lexicon_entry_draft` object with `draft_id`, `state`,
`scale`, `default_source_state`, `allow_unknown_source`,
`current_source_policy`, and `source_policy_after_update` fields. They also include
`state_lexicon_patch_line`, a candidate `StateLexiconEntry` text preview with a
placeholder pre-state rather than an automatically applied lexicon mutation.
The accompanying `requires_human_choice`, `placeholder_fields`, and
`can_auto_apply` fields make that non-automatic status machine-readable.

The same repair queue is available outside the page through:

```bash
python3 scripts/export_lexicon_patch_drafts.py \
  --sentence "Mary painted the door red" \
  --require-coq \
  --resolve-draft-id state-red--unknown_source_allowed \
  --source-state not_red \
  --patch-out work/red_state_lexicon.patch
```

For compact shell calls, the older equivalent
`--resolve state-red--unknown_source_allowed=not_red` remains accepted.
If a client supplies repeated resolutions for the same draft, they must agree;
conflicting source-state choices are reported in `validation_errors` and make
the bundle non-auto-applicable.
Patch text for a bundle with validation errors suppresses candidate replacement
lines until the client fixes those errors.

The script returns a `lexicon_patch_drafts.v1` JSON bundle with the compact
diagnostics summary, the manual-repair flags, and the draft records. The
`/api/lexicon-patch-drafts` endpoint returns the same bundle shape, or returns
the `patch_text_preview` as `text/plain` when called with `format=patch`.
Resolved bundles report `resolved_patch_count`; malformed or semantically
invalid choices are reported in `validation_errors`. The optional `--patch-out`
path writes the same review-only candidate text exposed in
`patch_text_preview` and does not mutate the lexicon. When a draft still needs
a human source-state choice, the preview keeps the pending patch line as a comment
instead of presenting it as auto-applicable source code. Both JSON and
patch-text file exports create missing parent directories before writing.
The project-level verification script includes a smoke check for this exporter
so the file-output path is exercised alongside unit tests and formalization
checks.

## Successful Response

A successful response should include:

- the original sentence;
- the event-semantics formula as JSON;
- the dependent-type rendering;
- result-state lexicon audit records when resultatives are present;
- the compact diagnostics summary;
- the structured AST;
- the generated Coq scaffold;
- the Coq/Rocq validation status;
- a short conclusion.

The diagnostics summary has four stage values: `passed`, `failed`, `skipped`,
and `not_applicable`. It summarizes `type_check`,
`semantic_readings_check`, `construction_hygiene`, and `coq_check` so a user
can see whether a failure belongs to internal structure, reading/export
alignment, construction-specific hygiene, or the external proof-assistant
boundary.
When `semantic_readings_check` fails, the diagnostics object also exposes
`semantic_readings_failure_kinds` and `semantic_readings_failure_summary`.
Current failure kinds distinguish missing readings, duplicate reading names,
malformed reading records, reading-local type-check failures, missing Coq/Rocq
exports, registered-rule export-count mismatches, and unclassified
semantic-reading errors.
It also exposes `semantic_readings_repair_details`, a structured audit record
with exported Prop/PropT definition names, expected reading definition names,
missing Coq/Rocq definitions, duplicate reading names, malformed reading
indices, failed reading-local type-check indices, and expected versus observed
export counts when a registered rule emits too many or too few propositions.
The separate `failure_stage` field distinguishes input/parsing failures from
later semantic and proof-assistant failures.
The web status line should surface `recovery_hint` directly so users do not
have to inspect raw JSON before trying the next repair. For successful
translations with non-fatal warnings, it should state that the translation is
verified with warnings and include the warning message in the status detail.
When manual lexicon drafts exist, the status detail should also show the draft
count rather than forcing the user to inspect raw JSON first.
Machine clients should prefer `recovery_actions` when they need stable action
names or button labels, and `warnings` when they need to flag underspecified but
still successfully checked translations.
For `semantic_readings_check` failures, the action list is derived from
`semantic_readings_repair_details`: `add_missing_coq_definitions` carries
`target_definitions`, `rename_duplicate_readings` carries duplicate names,
`fix_malformed_readings` and `fix_reading_type_checks` carry
`reading_indices`, and `normalize_reading_exports` carries expected and
observed export counts plus the exported definition names.
The page should render the same actions in a `Next Steps` panel, keeping
human-facing guidance and machine-facing API output aligned.
Each rendered action must expose `data-action-kind` and a `next-step--<kind>`
CSS class so later UI controls and browser tests have stable hooks. When an
action carries target metadata, the panel should display it in a compact
`next-step-details` table.
The service should keep these hooks browser-testable through controlled
diagnostics fixtures. `/api/diagnostic-fixture?case=semantic_readings_missing_export`
returns the JSON version of a semantic-reading export failure, while
`/diagnostic-fixture?case=semantic_readings_missing_export` renders the same
failure through the ordinary page panels. Additional fixture cases can cover
malformed readings and export-count mismatches without changing the normal
`/api/analyze` behavior. The same endpoint should expose `type_check_failure`,
`construction_hygiene_failure`, and `coq_check_failure` cases so every major
stage-local failure can be checked as both JSON and HTML.
The HTML page should provide a compact `diagnostic-fixture-form` selector for
these cases, pointing at `/diagnostic-fixture`, so browser tests and developers
can switch among fixtures without modifying the normal sentence-analysis form.
The page should also render `semantic_readings_check` as a structured
`Semantic Readings Check` panel, not only as raw JSON. The panel summarizes the
audit status and reading count, lists exported Prop/PropT definition names, and
renders one row per reading with stable `data-reading-name`,
`data-coq-definition`, and `data-coq-exported` hooks. Each row shows the
reading name, scope, source, Coq/Rocq definition, exported status, and
reading-local type-check status. If the audit fails, the same panel displays
failure-kind chips with stable `data-semantic-reading-kind` hooks and the
semantic-readings repair details and error list before the raw JSON details.
Warnings are rendered separately in a `Semantic Warnings` panel. Each rendered
warning exposes `data-warning-kind` and a `semantic-warning--<kind>` CSS class
so the interface can distinguish semantic caveats from recovery actions. If a
warning has `suggested_action`, the rendered action exposes
`data-warning-action-kind` for UI automation and displays the
`lexicon_entry_draft` fields as a compact draft record.
The page also renders a `Lexicon Patch Drafts` panel from top-level
`lexicon_patch_drafts`, with stable `data-draft-id`, `data-draft-state`, and
`data-draft-current-policy` hooks for future repair controls. The panel shows
the same `state_lexicon_patch_line` preview that JSON clients receive, together
with the `placeholder_fields` and `can_auto_apply` status. A separate
`Lexicon Patch Text Preview` panel shows the review-only patch text generated
from the current result, including commented pending lines when a human source
state is still required. The panel includes an `Open patch text` link whose
`data-patch-format="text"` hook targets the same `format=patch` endpoint for
download or inspection. Pending drafts also render a source-state form with a
stable `data-resolve-draft-id` hook; the form posts `resolve_draft_id` and
`source_state` to preview a resolved patch without changing the repository.

The Coq/Rocq step remains a boundary check, not the implementation language of
the translator. If it is unavailable, the web page can still show the internal
type-check result and mark external validation as skipped.

## Failure Modes

The interface should distinguish at least four failure classes:

- empty or severely underspecified natural-language input;
- malformed event-semantics JSON;
- failed dependent-type AST check;
- failed Coq/Rocq boundary validation.

This distinction is important for research use. A sentence may fail because
the parser is too weak, not because the dependent-type replacement is wrong.
Likewise, an AST may pass internally while the exported proof-assistant syntax
needs more declarations.

## Current Sentence Coverage

The prototype has specific analyses for:

- `John buttered the toast slowly in the bathroom at noon`
- `John ate`
- `John knocked twice`
- `John broke the vase`

These examples correspond to variable polyadicity with time, argument
omission, event counting, and causal-resultative translation.

Other simple English sentences are handled by the fallback parser. For example,
`a cat sits on a mat` becomes an event-semantics formula with `sit(e)`,
`Agent(e, cat)`, and `on(e, mat)`, then translates to
`sit(1)(on(mat), cat)` and can be checked by the generated Coq scaffold.
The modifier `on(mat)` is exported as an `Adv` item, not as an entity.

Quantifier-scope cases are not sent through the simple fallback parser. The
sentence `some boy loves some girl` is represented as a scope ambiguity with
two checked readings: one in which the boy existential has wider scope, and one
in which the girl existential has wider scope. Each reading is recorded as a
structured AST object with a `scope_order`, bound variables, restrictor
predicate types, and the binary relation type before the readable and Coq
formulas are rendered. The API also exposes the same alternatives through
top-level `semantic_readings`, matching the shape used by both single-reading
and ambiguity-producing do-support negation routes and by mixed temporal
perception alternatives. A companion
`semantic_readings_check` confirms that the readings are unique, non-empty, and
linked to exported Coq definitions. In this path, `boy` and `girl` are
predicates of type
`Entity -> Prop`, while `some` is a quantifier pattern, not an entity constant.
The checked scaffold also types `love` directly as `Entity -> Entity -> Prop`,
so the two readings do not smuggle in an `Event` type, `Agent`, or `Theme`
declaration.

The first Parsons-style event-talk case is handled by a timed replacement
instead of an event parameter. The sentence `after the singing of the
Marseillaise, John saluted the flag` keeps a visible event-semantics reference
formula for comparison, but its checked Coq scaffold declares `Time`,
`before : Time -> Time -> Prop`, `sing : Entity -> Time -> Prop`, and
`salute : Entity -> Entity -> Time -> Prop`. It defines the translation as an
existential formula over two time variables. The AST records the two `Time`
binders and checks that the `before` relation orders `t_sing` before
`t_salute`; the scaffold deliberately does not declare `Event`.

The remaining two Parsons/Luo-Shi examples have their own typed routes. `Mary
saw John leave` uses a nominalizing map `E : Prop -> Entity`, so the perceived
content is rendered as `see Mary (E (leave John))` rather than as a hidden
event argument. The AST records the nominalized proposition explicitly:
`see : Entity -> Entity -> Prop` takes Mary and the object produced by
`E : Prop -> Entity` from `leave John : Prop`. `In every burning, oxygen is
consumed` is rendered as
`forall x : Entity, forall t : Time, burn x t -> consume oxygen t`; the checked
AST stores the `Entity` and `Time` binders and verifies that `burn` and
`consume` are both typed as `Entity -> Time -> Prop` over the shared time
variable. The scaffold therefore avoids both an `Event` type and an
event-inclusion predicate such as `IN`. When the perception complement contains
mixed temporal coordination, the primary policy and checked alternative
policies are exposed through `semantic_readings` as well as the
construction-specific `alternative_scope_readings` audit. The
`semantic_readings_check` object reports the number of readings and rejects
duplicate names or alternative Coq definition names that are not exported in
the generated scaffold.
The single-reading Parsons/Luo-Shi routes use the same web/API contract:
`after the singing of the Marseillaise, John saluted the flag` exposes
`timed_after_singing_salute`, and `In every burning, oxygen is consumed`
exposes `universal_timed_burning`, with each name checked against an exported
Coq/Rocq definition.
The registered-rule executor now enforces this shape for every successful
registered construction. If an analyzer does not supply explicit readings and
its generated scaffold exports exactly one `Definition ... : Prop/PropT`, the
executor creates a conservative `{rule_id}_single_reading` entry and runs the
same `semantic_readings_check` before Coq/Rocq validation.

The pasted legacy browser prototype from the earlier webpage is useful as a
design sketch: it already distinguished nested perception cases from temporal
`After` cases. The current repository keeps that separation, but replaces the
regex-only browser logic with typed Python stages, visible ASTs, and Coq/Rocq
boundary checks.

Specialized analyses are now mediated by a construction registry. Each rule
records a rule identifier, a human-readable label, the semantic phenomenon it
covers, its analyzer, and Coq fragments that are disallowed for that
construction. This keeps the web pipeline honest: a rule may compile in Coq and
still fail if it reintroduces a hidden `Event` declaration or an unwanted
event-inclusion predicate.

The same registry also covers the passive argument-omission slice. For `the
toast was buttered by John`, the web/API result reports `butter(john, toast)`;
for `the toast was buttered`, it reports
`exists x_agent : Entity. butter(x_agent, toast)`. Its hygiene policy forbids
`Event`, `Agent`, and `Theme` declarations, because the replacement is an
ordinary typed existential over entities rather than a hidden event-role
analysis. The rule recognizes finite passive auxiliaries `is`, `was`, `are`,
and `were`, and stores the auxiliary in the AST so that the fallback parser does
not misclassify those words as lexical verbs. Passive participle recognition and
irregular lemmatization are supplied by `translator/surface_lexicon.py`, keeping
surface morphology separate from the construction-specific semantic rule. The
web/API output also normalizes the two passive cases into checked
`semantic_readings`: `by_phrase_agent` for an explicit by-phrase and
`omitted_existential_agent` for the existential-agent replacement. The
AST shown by the web/API result includes a `surface_lexicon` audit object with
the original participle, selected lemma, and lexicon source module.

Copular result-state clauses use a narrower registered rule before the passive
fallback. For `the vase is broken`, the web/API result reports
`holds_state(vase, integrity_scale, broken)` with `broken : State` and
`integrity_scale : StateScale`, not an existential omitted Agent. A by-phrase,
as in `the vase was broken by John`, keeps the sentence in the agentive passive
analysis.

Lexical change-of-state verbs are handled by another registered rule before the
generic fallback. `the door opened` reports
`Change(Transition(door, access_scale, closed, open))`, while `John opened the
door` reports `Cause(john, Transition(door, access_scale, closed, open))`.
Instrumental `with` phrases are preserved as typed Instrument entities through
`CauseWithInstrument(john, key, Transition(...))`. This prevents the web/API
layer from displaying `door` as an Agent merely because the sentence is
intransitive. The same path now uses the broader result-state lexicon for other
change-of-state verbs: `the clothes dried` reports
`Change(Transition(clothes, moisture_scale, wet, dry))`, `the water froze`
reports `Change(Transition(water, phase_scale, liquid, frozen))`, and
`Mary cleaned the room` reports
`Cause(mary, Transition(room, cleanliness_scale, dirty, clean))`. Content-scale
sentences such as `the tank emptied` and `John filled the glass` are treated in
the same way over `full` and `empty`. Life-scale verbs exercise asymmetric
frame licensing: `John died` is inchoative over `alive -> dead`, while
`Mary killed the plant with poison` is instrumental-causative over the same
scale, and `the plant killed` is not accepted as a lexical state-change
analysis. The response carries both an AST `frame` field and
`state_change_verb_entry`, a structured record with the selected target state
and the licensed inchoative, causative, and instrumental frames. This gives the
web/API layer stable audit fields for explaining why a given verb selected a
given transition. The same AST carries a `surface_lexicon` audit object for the
surface verb and selected lemma, so inflected forms such as `died` and `froze`
remain visible after normalization. The registrations are maintained in
`translator/state_change_lexicon.py`, separate from the parser rule that
recognizes the surface construction, and the type checker rejects an internally
malformed state-change AST whose registered verb, target state, or frame
disagree.

The `Construction Rule` panel must distinguish a rule's policy from an actual
failure. `forbidden_coq_fragments` names fragments that would be illegal for the
matched construction. `found_forbidden_fragments` reports fragments that were
actually found in the generated Coq scaffold. A successful replacement can
therefore display forbidden fragments as policy while still showing `hygiene:
passed` and `found forbidden fragments: none`. When a rule supplies
`construction_summary`, the panel also shows an instance summary, for example
that a same-subject VP coordination shares `john` while keeping `bread : Food`
and `water : Drinkable` in separate conjuncts.
If the construction's internal AST `type_check` fails, or if the normalized
`semantic_readings_check` cannot match each checked reading to an exported
Coq/Rocq definition, the pipeline stops before construction hygiene and
Coq/Rocq validation; those downstream stages are reported as `skipped`, so the
diagnostics do not blur an AST or reading-interface error into a proof assistant
error.
For example, `John ate bread and drank bread` is a transitive VP-coordination
analysis whose two object positions require incompatible lexical types for the
same surface constant. The web/API layer reports this as `failure_stage:
type_check`, shows the `Food vs Drinkable` conflict in the `Type Check` panel,
and does not call Coq/Rocq.

## Type Discipline

The web demo must not treat every surface phrase as an entity. In particular,
Luo-Shi style adverbial and prepositional modifiers are represented at type
`Adv`, with the shallow Coq interface:

```coq
Definition PropT : Type := Prop.
Definition Adv : Type := (Entity -> PropT) -> Entity -> PropT.
Parameter ModifierSeq : nat -> Type.
Parameter mods_nil : ModifierSeq 0.
Parameter mods_cons : forall n : nat, Adv -> ModifierSeq n -> ModifierSeq (S n).
```

For example, `john buttered the toast in the bathroom with a knife` exports
`in_bathroom : Adv`, `with_knife : Adv`, `john : Entity`, `toast : Entity`, and
`butter : forall n : nat, ModifierSeq n -> Entity -> Entity -> PropT`, with the
two modifiers passed as a `ModifierSeq 2` value. The AST checks the
natural-number index against both the visible modifier list and a normalized
`modifier_vector` before export. It also keeps a `role_frame` so Agent and Theme
labels remain available for diagnostics and are checked against the ordered
entity arguments in canonical thematic order, with each role type checked
against the function argument type that will be exported. The shallow Coq
interface now gives the external checker the same length invariant while
keeping the lexical verb declaration stable across different modifier counts.
The web/API result also exposes the modifier-level `surface_lexicon` audit:
`in(bathroom)` must normalize to `in_bathroom`, `with(knife)` must normalize to
`with_knife`, and both must remain typed as `Adv` with the expected semantic
role. Directional modifiers are checked the same way: `from(home)` normalizes
to `from_home` with role `Source`, and `to(school)` normalizes to `to_school`
with role `Goal`. Those expected roles come from the shared surface lexicon's
`MODIFIER_ROLE_BY_PREDICATE` table, not from a one-off web rule. This prevents
a successful-looking page from hiding the exact mistake that motivated the
typed modifier layer, namely treating a modifier expression as an entity
constant.
