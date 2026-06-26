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
For ordinary fallback successes, the API response and HTML panel must agree on
the same normalized reading row: `fallback_single_reading` from
`fallback_event_semantics`, linked to `example_1`, with a `none` attachment and
a passing `semantic_readings_check`.
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
The verifier now checks this warning/action/draft chain as a fixed schema:
warning kinds must map to their expected suggested-action kinds, each embedded
`lexicon_entry_draft` must match the warning state, scale, and source policy,
top-level `lexicon_patch_drafts` must equal the de-duplicated embedded drafts,
`lexicon_patch_draft_count` and `manual_repair_required` must agree with that
queue, and `patch_text_preview` must mention every draft id that it previews.

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
patch-text outputs are now checked as a bundle-level fixed schema: the verifier
requires `resolved_patch_count`, `requires_human_choice`, `can_auto_apply`,
`validation_errors`, each draft's resolved or pending state, and the candidate
or guarded patch text to agree.
patch-text file exports create missing parent directories before writing.
The project-level verification script includes a smoke check for this exporter
so the file-output path is exercised alongside unit tests and formalization
checks.
The regression tests also compare the direct bundle builder, API JSON response,
API `format=patch` text response, CLI JSON output, and CLI `--patch-out` file
for unresolved, resolved, and validation-error bundles. This keeps browser
downloads, command-line review files, and JSON clients on one repair contract.
The project-level web smoke check exercises the live HTTP route as well,
checking that `/api/lexicon-patch-drafts` returns JSON as `application/json`,
patch text as `text/plain`, matching byte lengths, and payloads identical to
the fixed bundle builder for pending, resolved, and validation-error cases.
Negative HTTP cases are checked on the same route. Empty input is represented as
a bundle validation error with no candidate patch lines, conflicting
source-state choices keep the bundle non-auto-applicable, repeated identical
choices collapse to one safe resolution, and unsupported `format` values return
a 400 JSON response with the allowed formats.
The CLI exporter is regression-tested against those live HTTP outputs for the
same shared case table, covering pending, compact resolved, structured
resolved, duplicate-resolution, empty-sentence, unknown-draft, conflicting
source-state, and invalid-source-state bundles. Successful and non-zero
command-line exits still have to write the JSON bundle and `--patch-out` text,
and those files must match the browser/API payloads before the smoke check
passes.
The direct API tests, live HTTP tests, CLI tests, and verifier import the same
shared contract-case table from `scripts/lexicon_patch_contract_cases.py`, so
CLI review and browser/API review cannot accumulate separate hand-maintained
case lists.
For failing cases, that table also records the expected `validation_errors`
fragments. The direct handler, live HTTP route, command-line exporter, and
project verifier all check those fragments, so a boundary can no longer keep a
valid bundle shape while reporting a different rejection reason.

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
This object should be checked as a fixed schema: definition-name fields are
string lists, reading-index fields are integer lists, `expected_export_count`
is an integer or `null`, and `observed_export_count` is an integer. The same
verifier should compare these details with the payload fields of the specialized
recovery actions derived from them.
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
Every recovery action should carry non-empty `kind`, `label`, and `detail`
fields. The verifier should reject unknown diagnostic action kinds and should
check kind-specific payload shapes, including `target_definitions`,
`duplicate_reading_names`, `reading_indices`, `expected_export_count`,
`observed_export_count`, and `exported_definitions`.
For `semantic_readings_check` failures, the action list is derived from
`semantic_readings_repair_details`: `add_missing_coq_definitions` carries
`target_definitions`, `rename_duplicate_readings` carries duplicate names,
`fix_malformed_readings` and `fix_reading_type_checks` carry
`reading_indices`, and `normalize_reading_exports` carries expected and
observed export counts plus the exported definition names.
The page should render the same actions in a `Next Steps` panel, keeping
human-facing guidance and machine-facing API output aligned.
Each rendered action must expose `data-action-kind`, `data-action-index`,
`data-action-contract-kind`, a `data-action-contract-api="/api/diagnostic-contract"`
pointer, and a `next-step--<kind>` CSS class so later UI controls and browser
tests have stable hooks. When an action carries target metadata, the panel
should display it in a compact `next-step-details` table. Diagnostic fixture
pages should also expose each action through
`/api/recovery-action?case=<case>&index=<n>`, returning a
`diagnostic_recovery_action.v1` object with the case, action index, failure
stage, exact action payload, a `diagnostic_repair_plan.v1` object, and shared
diagnostic contract. The repair plan should record `can_auto_apply`, target
fields, ordered repair steps, a review-only patch preview when one can be
constructed, and verification commands; the verifier should reject repair-plan drift
rather than trusting prose. It should also distinguish `automation_mode` values:
`inspection_only` actions expose `can_auto_run` for read-only checks, while
semantic or Coq/Rocq repair actions remain `human_review_required` and must not
be applied silently. The companion
`/api/recovery-action-run?case=<case>&index=<n>` endpoint should return a
`diagnostic_inspection_run.v1` target-field snapshot only for inspection-only
actions and should reject human-review-required actions with a 400 response.
For fixture pages, the same bundle should be rendered as an expandable
`Inspection Run JSON` preview in both the `Next Steps` list and the
`Recovery Action Exports` panel, so browser checks can compare the visible
preview with the API-shaped diagnostic run without issuing another request.
The verifier should compare each preview inside its own action list item, not
merely search the whole page, so duplicated or stale JSON in a neighboring panel
cannot mask a bad row.
The same row should expose a separate `download=1` URL and a stable `.json`
filename for both the recovery-action bundle and, when available, the inspection
run bundle. The server should return the same JSON payload with a
`Content-Disposition` attachment header for those download URLs, while leaving
the ordinary API path unchanged for clients that want to parse JSON directly.
The live web smoke check should request both forms and reject content-type,
content-length, filename, or payload drift at the HTTP boundary.
The download-response helper should also be tested with direct counterexamples
for status, content-type, content-length, filename, and payload drift, so the
HTTP artifact contract remains guarded even when the route smoke check is not
running.
This gives browser tools an inspection/export path for one suggested repair
without scraping the full analysis response. The fixture HTML should also render a
`Recovery Action Exports` panel that summarizes every such route with
`data-export-schema`, `data-export-case`, `data-export-count`,
`data-export-action-index`, `data-export-action-kind`, and
`data-export-failure-stage` hooks, making the export inventory visible before a
developer opens a JSON link. Each export row should include an expandable
`Action JSON` preview; the verifier should reconstruct the expected
`diagnostic_recovery_action.v1` bundle from the fixture payload and shared
diagnostic contract, then require the rendered preview to match that JSON
exactly.
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
The JSON companion `/api/diagnostic-fixtures` should expose a
`diagnostic_fixtures.v1` manifest listing every fixture case, its label, JSON
path, HTML path, failure stage, recovery action kinds, and
`recovery_action_exports` per-action export metadata. Each export metadata
record should name the `diagnostic_recovery_action.v1` schema, case, action
index, action kind, failure stage, `/api/recovery-action` path, automation
mode, `can_auto_run`, `can_auto_apply`, `target_fields`, and either an
`inspection_run_api_path` for read-only inspection actions or `null` for
human-review-required repairs. The fixture selector should also expose
`data-inspection-run-count` on each option, so clients can discover whether a
case has executable diagnostic inspections before opening the full fixture
payload.
The fixture case inventory, visible labels, expected failure stages, and
expected recovery-action kinds should be derived from a single
`DIAGNOSTIC_FIXTURE_SPECS` table of validated `DiagnosticFixtureSpec` entries
rather than maintained as parallel case, label, stage, and action structures;
unknown stage/action names should fail before the manifest is served.
The web application and project verifier should import the same diagnostic
contract module for the controlled failure-stage and recovery-action
vocabularies, so verifier acceptance cannot drift from UI construction.
The same vocabulary should be exposed to clients at `/api/diagnostic-contract`
as a `diagnostic_contract.v1` manifest containing `failure_stages`,
`required_fixture_stages`, `recovery_action_kinds`, and
`semantic_reading_fields`.
The verifier should reject schema drift, failure-stage drift,
required-fixture-stage drift, recovery-action drift, semantic-reading field
drift, and stale selector links to that contract endpoint.
The ordinary HTML page should render the same contract as a `Diagnostic
Contract` panel with stable `data-contract-schema`, `data-contract-api`,
`data-contract-field`, `data-contract-count`, and `data-contract-token` hooks,
so browser automation can inspect the controlled vocabulary directly instead
of inferring it from prose or selector labels.
The selector should be rendered from that same manifest and expose
`data-fixtures-schema`, `data-fixtures-api`, `data-diagnostic-contract-api`,
option-level failure-stage and recovery-action metadata, and the manifest label
as the option text so the UI cannot drift from the JSON inventory.
The project verification smoke check should request both the manifest endpoint
and the HTML fixture page, making selector/manifest drift visible in the same
deterministic check suite that exercises the backend pipeline.
It should iterate over every case advertised by the manifest and compare the
API payload, selected HTML option, API/HTML route case parameter, failure stage,
and recovery-action metadata.
For fixture cases with a passing `semantic_readings_check`, it should also check
that each semantic reading carries the contract fields and that the JSON
`reading_explanation` text appears in the HTML row as `interpretation`.
The core analyzer boundary should enforce the same normalized reading contract:
`check_semantic_readings` should classify a reading with missing `scope`,
`source`, `coq_definition`, `type_check`, `attachment_summary`, or
`reading_explanation` as `malformed_readings`, before construction hygiene or
Coq/Rocq validation runs. The shared constructor should give ordinary
single-reading outputs a `none` attachment summary and a conservative
interpretation sentence, so specialized attachment explanations extend a stable
schema instead of patching one in later.
Successful ordinary fallback analyses should enter the same interface as
`fallback_single_reading`, sourced from `fallback_event_semantics`, linked to
`example_1`, and rendered in the Semantic Readings Check panel with a `none`
attachment summary rather than bypassing the semantic-reading audit.
The project-level web smoke check should exercise that ordinary `/api/analyze`
success path directly, using `John knocked twice` and the matching HTML page
before it walks the diagnostic fixtures, so fallback success cannot drift from
the normalized semantic-reading interface.
The helper should reject any fixture whose `failure_stage` is outside the
controlled diagnostics set: `input`, `parsing`, `type_check`,
`semantic_readings_check`, `construction_hygiene`, and `coq_check`. The fixture
manifest should also cover the four internal/proof-boundary stages
`type_check`, `semantic_readings_check`, `construction_hygiene`, and
`coq_check`; input and parsing failures remain covered by ordinary
`/api/analyze` failure tests rather than by controlled fixture pages.
The expected selector count should be derived from the manifest rather than
from a second hard-coded case total.
The same consistency rules should be factored into a pure verifier helper so
tests can inject duplicate cases, incomplete metadata, payload case drift, and
stale selector attributes without needing a live server. The helper should also
parse each manifest `api_path` and `html_path` to verify that its endpoint and
`case` query parameter point back to the same fixture case, compare the manifest
label with the rendered option text, and compare the manifest's
`recovery_action_kinds` with the actual payload `diagnostics.recovery_actions`
list and the rendered `Next Steps` `data-action-kind` hooks. It should also
validate each payload action's schema and compare action payloads against
`semantic_readings_repair_details`, so routes, labels, typed repair arguments,
and repair advice cannot drift between JSON and HTML.
The page should also render `semantic_readings_check` as a structured
`Semantic Readings Check` panel, not only as raw JSON. The panel summarizes the
audit status and reading count, lists exported Prop/PropT definition names, and
renders one row per reading with stable `data-reading-name`,
`data-coq-definition`, `data-coq-exported`, and
`data-reading-attachment-kind` hooks. Each row shows the reading name, scope,
source, Coq/Rocq definition, exported status, reading-local type-check status,
human-readable interpretation, attachment kind, typed Adv modifiers, typed NP
restrictors, typed time modifiers, and relative objects. If the audit fails, the same panel displays
failure-kind chips with stable `data-semantic-reading-kind` hooks and the
semantic-readings repair details and error list before the raw JSON details.
Warnings are rendered separately in a `Semantic Warnings` panel. Each rendered
warning exposes `data-warning-kind` and a `semantic-warning--<kind>` CSS class
so the interface can distinguish semantic caveats from recovery actions. If a
warning has `suggested_action`, the rendered action exposes
`data-warning-action-kind` for UI automation and displays the
`lexicon_entry_draft` fields as a compact draft record. The project smoke check
also compares those embedded draft records with the top-level draft queue and
patch preview, so the visible warning and the repair queue cannot silently
drift apart.
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

The fallback path is intentionally guarded. A small allowlisted rule handles
simple conditionals first, so `if John left, Mary cried` is certified as
`leave(john) -> cry(mary)` with an implication between typed propositions. The
same route covers simple typed-object clauses: `if John ate bread, Mary drank
water` is certified as `eat(john, bread) -> drink(mary, water)` while preserving
`bread : Food` and `water : Drinkable` in the generated Coq/Rocq scaffold.
Clause-local time modifiers are also visible in the same panels:
`if John left yesterday, Mary cried today` is certified as
`at_T(yesterday, leave(john)) -> at_T(today, cry(mary))`, with `at_T` declared
at type `Entity -> Prop -> Prop`. Clause-local Adv modifiers are shown through
the same ModifierSeq convention used by the Luo-Shi modifier rules:
`if John ate bread quickly, Mary cried loudly` is displayed as
`eat(1)(quickly, john, bread) -> cry(1)(loudly, mary)`, and the generated
scaffold declares `quickly : Adv`, `loudly : Adv`, `ModifierSeq`, and `PropT`.
The same panel now shows mixed modified/unmodified uses of one predicate with a
single lifted signature: `if John left quickly, Mary left` is displayed as
`leave(1)(quickly, john) -> leave(0)(mary)`, and the generated Coq/Rocq term
uses `mods_nil` for the zero-modifier branch rather than a second plain
`leave : Entity -> Prop` declaration. Timed variants follow the same display
contract: `if John left quickly yesterday, Mary left today` is shown as
`at_T(yesterday, leave(1)(quickly, john)) -> at_T(today, leave(0)(mary))`, so
the page exposes both the temporal wrappers and the zero-modifier branch.
Conditional-clause do-support negation is
shown as proposition-level negation over the timed clause, so
`if John did not leave quickly, Mary cried today` appears as
`not_T(leave(1)(quickly, john)) -> at_T(today, cry(mary))`, with `not_T`
declared at type `Prop -> Prop`. Two-subject conditional clauses appear in the
same panels without a pseudo-subject: `if John and Mary ate bread quickly in the park yesterday,
Sue cried today` is displayed as
`at_T(yesterday, and_T(eat(2)(quickly, in(park), john, bread), eat(2)(quickly, in(park), mary, bread))) -> at_T(today, cry(sue))`,
with `and_T` declared at type `PropT -> PropT -> PropT`.
Clause-level markers outside the current certified fragment, including `who`,
`which`, `that`, `whether`, and overextended conditional strings such as
`if John left, Mary cried because Sue left`, stop the analysis at the parsing stage before a
fallback formula or Coq/Rocq scaffold can be generated. This prevents malformed
conditionals from being certified as `leave(0)(if_john, mary_cried)` and
prevents relation-clause subjects from being swallowed by the lexical
state-change rule as one entity constant.

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
When PP or relative-clause attachment is ambiguous, each quantifier
`semantic_readings` item now includes an `attachment_summary`. For example,
`subject_relative_adv` exposes `subject_relative: in_park : Adv` and
`subject_relative: mary : Entity`, whereas an object-NP restrictor exposes
`object_np: in_park_np : Entity -> Prop`. The page renders the same summary in
the `Semantic Readings Check` rows and adds the `reading_explanation` text as an
`interpretation` field, so users can distinguish Adv modification from binder
restriction without opening the raw AST.

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
