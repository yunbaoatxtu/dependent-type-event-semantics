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
`construction_hygiene`, `coq_check`, `diagnostics`, `verification_scope`, and
`conclusion`.
The page mirrors that version in a compact `API Contract` panel, including the
`/api/analyze` endpoint, so a browser screenshot and a JSON client can refer to
the same response contract. It also renders the response `conclusion` in a
dedicated `Conclusion` panel so the final outcome is visible outside the status
line.
The page also renders `verification_scope` as a dedicated panel. Registered
construction successes must expose `kind: registered_construction`,
`certification_level: construction_rule`, and the matched rule id. Fallback
successes must expose `kind: fallback_shallow` and
`certification_level: shallow_scaffold`, together with limitations explaining
that the result is a structurally checked scaffold rather than full
natural-language certification. They also expose `certification_gaps`, currently
`no_registered_construction_rule`, `no_fragment_specific_readings`, and
`no_construction_hygiene_policy`, so clients can distinguish a successful
fallback parse from a construction that is ready for rule-level certification.
Fallback responses also expose `certification_upgrade_plan` with
`schema_version: "certification_upgrade_plan.v1"`, a generated
`candidate_rule_id`, `target_certification_level: construction_rule`, and one
human-review upgrade step per gap. The page renders this as a dedicated
`Certification Upgrade Plan` panel with stable hooks such as
`data-upgrade-plan-schema`, `data-upgrade-candidate-rule-id`, and
`data-upgrade-action-kind`. They also expose `construction_rule_draft` with
`schema_version: "construction_rule_draft.v1"`, a generated
`candidate_analyzer`, accepted examples, semantic-reading drafts, a hygiene
policy draft, a test draft, and a patch-text preview. The draft is explicitly
marked `automation_mode: "human_review_required"` and `can_auto_apply: false`.
The page renders it as `Construction Rule Draft` with stable hooks such as
`data-rule-draft-schema`, `data-rule-draft-id`,
`data-rule-draft-reading`, and `data-rule-draft-forbidden-fragment`. The
parallel `/api/construction-rule-draft` route returns
`schema_version: "construction_rule_draft_response.v1"` and can serve the same
payload as a downloadable JSON artifact through `download=1`. The route is also
covered by a pure verifier helper: the response wrapper must preserve the
ordinary analysis' `construction_rule_draft`, `verification_scope`, and
`diagnostics`, and the HTML `Raw draft JSON` preview must equal the same draft
payload. This keeps the upgrade artifact checkable even in environments that
cannot start the local HTTP smoke-test server. A promotion-contract helper also
compares `certification_upgrade_plan` with the draft: candidate rule id, source
sentence, dependent-type translation, AST summary, semantic-reading draft, test
draft, verification commands, and patch-text preview must agree.
The draft additionally carries `registration_preflight` with
`schema_version: "construction_rule_registration_preflight.v1"`. It checks
candidate rule-id and analyzer-name uniqueness against the live registry,
presence of accepted examples, semantic-reading drafts, hygiene fragments, and
a registration test draft, and it must expose
`registration_status: "human_review_required"` with `can_auto_register: false`.
The page renders these checks through `data-rule-draft-preflight-*` hooks.
Rejected or failed paths use
`certification_level: none`.
The page also exposes a project-level certified-fragment contract. The
`/api/certified-fragment` endpoint returns `schema_version:
"certified_fragment.v1"`, `full_natural_language_certification: false`, all
registered construction rules generated from the live analyzer registry, the
fallback certification level, the fallback `certification_gaps`, and the
rejected clause-marker set. The
`Certified Fragment` panel mirrors the same metadata with stable data
attributes for the schema, API path, registered rule count, fallback level, and
each registered rule id through `data-certified-rule-id`. It also exposes each
fallback gap through `data-fallback-gap-id`, which gives smoke tests a stable
hook for checking that shallow fallback success is not presented as a completed
certification result.
The manifest also carries a `coverage_matrix` with
`registered_success_cases`, `registered_variant_success_cases`,
`fallback_success_cases`, and `rejected_unsupported_cases`, plus matching
`coverage_matrix_counts`. The page exposes those counts through stable
`data-coverage-*` attributes and renders registered-variant, fallback, and
rejected example rows with `data-coverage-kind`, `data-coverage-sentence`, and,
for registered variants, `data-coverage-variant-id`; for rejection rows it also
uses `data-coverage-marker`. Current registered variants include
`temporal_event_counting`, `temporal_plain_intransitive_predication`,
`temporal_manner_intransitive_predication`,
`temporal_instrument_intransitive_predication`,
`temporal_locative_intransitive_predication`,
`temporal_manner_instrument_intransitive_predication`,
`temporal_manner_locative_intransitive_predication`,
`temporal_manner_two_location_intransitive_predication`,
`temporal_manner_three_location_intransitive_predication`,
`temporal_manner_location_sequence_intransitive_predication`,
`extended_manner_location_sequence_intransitive_predication`, and
`temporal_extended_manner_location_sequence_intransitive_predication`,
`temporal_manner_location_instrument_intransitive_predication`,
`extended_manner_location_instrument_intransitive_predication`, and
`temporal_extended_manner_location_instrument_intransitive_predication`,
`repeated_instrument_manner_location_instrument_intransitive_predication`,
`temporal_repeated_instrument_manner_location_instrument_intransitive_predication`,
`temporal_extended_repeated_instrument_manner_location_instrument_intransitive_predication`,
and `stacked_instrument_manner_location_instrument_intransitive_predication`,
`temporal_manner_mixed_location_instrument_intransitive_predication`, and
`temporal_extended_manner_mixed_location_instrument_intransitive_predication`,
`temporal_manner_mixed_directional_instrument_intransitive_predication`, and
`temporal_goal_manner_mixed_directional_instrument_intransitive_predication`,
`temporal_resultative_predication`, `temporal_plain_transitive_predication`,
`multi_adv_modified_transitive_predication`,
`temporal_multi_adv_modified_transitive_predication`,
`triple_adv_modified_transitive_predication`, and
`temporal_triple_adv_modified_transitive_predication`,
`quad_adv_modified_transitive_predication`, and
`temporal_quad_adv_modified_transitive_predication`,
`quint_adv_modified_transitive_predication`, and
`temporal_quint_adv_modified_transitive_predication`, so the manifest records
two-, three-, four-, and five-Adv Luo-Shi modifier routes as witnesses of the
non-empty `ModifierSeq` rule rather than treating modifier count as a fallback
boundary.
The same manifest now includes `surface_parser_coverage` for
`modified_transitive_adv_sequence`. This object records the open-ended type
family `forall n : nat, ModifierSeq n -> Entity -> Entity -> PropT`, the parser
claim `registered_examples_only`, `full_surface_parser_certification: false`,
and the verified timed and untimed modifier counts `1,2,3,4,5`. The
`Certified Fragment` panel mirrors these values through `data-surface-*`
attributes, so the page can advertise the current parser boundary without
confusing it with the stronger type-level Luo-Shi principle.
It also carries `verified_examples`, a concrete witness list containing the
registered primary one-Adv sentence plus every timed and untimed registered
variant up through five Adv modifiers. The HTML panel renders each witness with
`data-surface-example-variant-id`, `data-surface-example-sentence`,
`data-surface-example-modifier-count`, `data-surface-example-time-wrapped`, and
`data-surface-example-source`, and exposes the total through
`data-surface-verified-example-count`. The verifier checks those hooks against
the manifest so the advertised parser boundary remains tied to actual smoke
inputs. Each witness also includes `expected_event_analysis`,
`expected_ast_kind`, and `expected_dependent_type_fragments`, while the page
mirrors the analysis, AST kind, and fragment count through stable attributes.
Thus a witness is not merely an example sentence: it is a compact semantic
contract for what that surface sentence must produce. During the project smoke
check, every surface witness is rerun through the live analyzer and compared
against that contract, so parser-boundary drift is caught at the same level as
ordinary registered-construction drift. Dedicated regression tests patch the
live analyzer response to simulate no-run, rule, analysis, AST, and translation
drift for a witness and require the verifier to reject each case explicitly.
The same surface object now carries `witness_generation_spec`, a compact
generator contract for the audited prefix of the Adv-sequence family. It names
the base sentence, ordered modifier surfaces, dependent-type fragments,
`yesterday` time suffix, variant ids, sources, and translation templates. The
verifier derives the expected witness list from this spec before checking the
manifest and the live analyzer, while the HTML panel mirrors the generator
schema, generator kind, modifier count, and time suffix through stable
`data-surface-generator-*` attributes.
The surface object also exposes `slot_probe_examples`. These are controlled
Agent, Theme, predicate, and combined timed/max-prefix substitutions that must
still match the modified-transitive rule, analysis label, AST shape, and
translation fragments. They are generated from a `probe_generation_spec` that
records the base lexical frame, slot substitutions, prefix lengths, surface
templates, and translation templates, and the verifier reconstructs the probes
from that spec before running the live analyzer. They are intentionally marked
as probes rather than full lexical-slot certification, and the panel mirrors
both the probe rows and generator metadata through `data-surface-slot-probe-*`
attributes.
The same object now includes `matrix_examples`, a generated 2-by-2-by-2
lexical-frame matrix for Mary/John, admire/photograph, and
painting/sculpture, evaluated under one untimed one-Adv profile and one timed
five-Adv profile. The matrix is exposed with
`full_lexical_matrix_certification: false` and mirrored through
`data-surface-slot-matrix-*` attributes, so the UI can show broader finite
coverage without implying arbitrary lexical replacement. Those attributes now
include the type boundary for the matrix: Agent and Theme slots are
`Entity`-typed role bearers, predicate slots are dependent transitive Adv
families, modifier slots are `Adv`, and timed rows expose the `Time` argument
used by the proposition-level temporal operator.
The matrix generation spec also embeds a `surface_type_contract_registry.v1`
object from `translator/surface_type_contracts.py` and mirrors its schema,
entry schema, entry count, source module, and registry id through
`data-surface-slot-probe-matrix-type-contract-*`, making the UI boundary check
the same source used by the verifier. The current registry exposes six
`surface_type_contract_entry.v1` rows for the controlled Agent, predicate, and
Theme axes, and `validate_surface_type_contract_registry` rejects bad registry
schemas, duplicate entry keys, stale entry counts, role/type mismatches, and
axes that cannot be reconstructed from the entry rows. The same validator now
checks the modifier and time contracts as fixed field-level objects: modifiers
must stay `Adv` values built by `Entity -> Adv`, modifier objects must not be
treated as events, and time rows must expose `Time` plus the proposition-level
`Time -> PropT -> PropT` operator rather than an `Entity` surrogate. The
registry also carries a `surface_type_contract_diagnostic.v1` category table,
mirrored through stable HTML attributes, so the page can distinguish registry
schema, entry/axis synchronization, thematic-role, modifier-type, and
time-type boundary failures.
The same manifest includes `semantic_snapshots` and `semantic_snapshot_count`.
Each snapshot is keyed by registered rule id and stores the expected analysis
label, dependent-type translation fragments, semantic-reading names/sources,
Coq/Rocq definition names, and type-check result for that rule's primary
example. It also stores `expected_ast_summary`, a compact structural digest of
AST kind, predicate symbols/types, entity and state symbols, binder and
quantifier signatures, and core list counts. The `Certified Fragment` panel
mirrors the snapshot count and exposes per-rule `data-semantic-snapshot-*`
hooks, including `data-semantic-snapshot-ast-kind`, while the verifier runs the
live pipeline against the static snapshots to catch semantic and AST drift.
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
For reading-local type-check failures, clients should not have to rewalk the
whole `semantic_readings` array. The compact diagnostics object also exposes
`reading_type_check_failure_count` and `reading_type_check_diagnostics`; each
record names the reading index, reading name, source, scope, Coq/Rocq
definition, `semantic_readings[i].type_check` path, emitted error strings, and
any nested state-opposition diagnostics. The HTML should render these records
in a `Reading Type Check Diagnostics` panel with hooks including
`data-reading-type-check-name`, `data-reading-type-check-path`, and
`data-reading-type-check-state-opposition-count`.
This object should be checked as a fixed schema: definition-name fields are
string lists, reading-index fields are integer lists, `expected_export_count`
is an integer or `null`, and `observed_export_count` is an integer. The same
verifier should validate the reading-local diagnostics directly:
`reading_type_check_failure_count` agrees with the diagnostic list length,
record-level `error_count` and `state_opposition_count` agree with their nested
lists, each path remains `semantic_readings[i].type_check`, and the HTML panel
keeps the corresponding `data-reading-type-check-index`, name, source, scope,
Coq-definition, path, error, and state-opposition-count hooks. It should also
compare the failed reading indices across the diagnostics list,
`semantic_readings_repair_details.failed_type_check_indices`, and the
specialized `fix_reading_type_checks.reading_indices` action, including the
ordinary analyze-action export and human-review inspection-rejection bundle.
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
pages are not the only typed failure surface: ordinary failed `/api/analyze`
responses should also carry `surface_type_contract_diagnostics`, and the HTML
page should render a `Surface Type Contract Diagnostics` panel with stable
`data-surface-type-contract-*` hooks. The same context should be mirrored on
each ordinary failure `Next Steps` action row via
`data-action-surface-type-contract-*` hooks, so action buttons and browser
tests can bind a suggested repair to the protected surface-type boundary.
Diagnostic fixture
pages should also expose each action through
`/api/recovery-action?case=<case>&index=<n>`, returning a
`diagnostic_recovery_action.v1` object with the case, action index, failure
stage, exact action payload, a `diagnostic_repair_plan.v1` object, and shared
diagnostic contract. It should also carry a
`surface_type_contract_diagnostics` object from the
`surface_type_contract_diagnostic.v1` category table, so downloaded
failure-local repair bundles retain the registry, role-frame, modifier-type,
and time-type boundary context. The repair plan should record
`can_auto_apply`, target fields, ordered repair steps, a review-only patch preview when one can be
constructed, and verification commands; the verifier should reject repair-plan drift
rather than trusting prose. It should also distinguish `automation_mode` values:
`inspection_only` actions expose `can_auto_run` for read-only checks, while
semantic or Coq/Rocq repair actions remain `human_review_required` and must not
be applied silently. The companion
`/api/recovery-action-run?case=<case>&index=<n>` endpoint should return a
`diagnostic_inspection_run.v1` target-field snapshot only for inspection-only
actions and should reject human-review-required actions with a 400 response.
The ordinary analysis route should expose the same read-only shape through
`/api/analyze-action-run?sentence=<sentence>&index=<n>` for failed
`/api/analyze` results. This endpoint should set `source: "analyze"`, preserve
the input sentence, diagnostics, diagnostic contract, and
`surface_type_contract_diagnostics`, and snapshot only the repair-plan target
fields. It should reject human-review actions such as `edit_input` or
`revise_sentence` with the same `diagnostic_inspection_run.v1` error envelope.
The corresponding `/api/analyze-action?sentence=<sentence>&index=<n>` endpoint
should return a `diagnostic_recovery_action.v1` bundle for the ordinary action
itself, preserving `source: "analyze"`, the input sentence, the action, repair
plan, diagnostics, diagnostic contract, and surface type diagnostics. Unlike
the inspection-run endpoint, it may export human-review-required actions because
the export is read-only. The ordinary failure `Next Steps` row should render an
expandable `Action JSON` preview for this bundle, and the verifier should compare
that row-local preview with the `/api/analyze-action` payload so a stale page-wide
JSON snippet cannot satisfy the contract. The ordinary-failure route check should
cover at least four stage-local cases: normalized empty input with `edit_input`,
short parsing failure such as `John` with `revise_sentence`, unsupported-fragment
rejection such as `if John left, Mary cried because Sue left` with
`verification_scope.kind = rejected_unsupported_fragment`, and type-check failure
such as `the plant killed` with `inspect_ast` under the registered construction
scope `construction_rule` for `lexical_state_change`. Human-review actions in
that matrix should still have downloadable action JSON, but their
`/api/analyze-action-run` route should return a structured
`diagnostic_inspection_run.v1` rejection rather than an auto-runnable snapshot.
The ordinary `diagnostics.recovery_actions` list should make these routes
discoverable without HTML scraping: each action should carry `automation_mode`,
`can_auto_run`, `can_auto_apply`, `target_fields`, `api_path`,
`download_api_path`, `download_filename`, nullable `inspection_run_api_path`,
nullable `inspection_run_download_api_path`, and a nullable
`inspection_run_download_filename` that matches the downloadable JSON artifact
for inspection-only actions.
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
`data-export-failure-stage` hooks, plus
`data-surface-type-contract-diagnostic-*` hooks for the type-boundary schema,
category count, category ids, and registry id, making the export inventory
visible before a developer opens a JSON link. Each export row should include an expandable
`Action JSON` preview; the verifier should reconstruct the expected
`diagnostic_recovery_action.v1` bundle from the fixture payload and shared
diagnostic contract, then require the rendered preview and surface type
diagnostic context to match that JSON exactly.
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
The project-level web smoke check should exercise the promoted event-counting
route, the promoted active argument-omission route, the promoted
plain-intransitive route, the promoted manner-intransitive route, the promoted
manner-locative intransitive route, the promoted plain-transitive route, the
promoted locative route, and the ordinary fallback route directly before it
walks the diagnostic fixtures. `John knocked twice`
must surface as the registered `event_counting`
construction with
`event_counting_single_reading`; the timed variant `John knocked twice
yesterday` must keep the same registered rule while rendering
`at_T(yesterday, repeat(2, knock(0)(john)))`. `John ate` must surface as the
registered `active_argument_omission` construction with
`active_argument_omission_single_reading` and `omitted_existential_theme`,
without exposing a fallback draft. `Mary smiled` must surface as the registered
`plain_intransitive_predication` construction with
`plain_intransitive_predication_single_reading` and `explicit_agent`, while
`Mary smiled yesterday` must keep the same rule under
`at_T(yesterday, smile(0)(mary))` with `explicit_agent_at_time`; neither surface
may expose a fallback draft. `Mary admired the painting` must surface as the
registered `plain_transitive_predication` construction with
`plain_transitive_predication_single_reading` and `explicit_agent_theme`,
without exposing a fallback draft. The timed variant `Mary admired the painting
yesterday` must keep the same registered rule while rendering
`at_T(yesterday, admire(0)(mary, painting))` and the
`explicit_agent_theme_at_time` scope, also without exposing a fallback draft.
`Mary admired the painting in the gallery` must surface as the registered
`modified_transitive_predication` construction with
`modified_transitive_predication_single_reading`,
`explicit_agent_theme_with_adv`, and `in_gallery : Adv` rather than
`in_gallery : Entity`. The timed variant `Mary admired the painting in the
gallery yesterday` must keep the same registered rule while rendering
`at_T(yesterday, admire(1)(in(gallery), mary, painting))` and
`explicit_agent_theme_with_adv_at_time`, again without exposing a fallback draft.
The same rule now accepts the two-Adv sequence `Mary admired the painting in the
gallery with a telescope`, checks `in_gallery : Adv` and `with_telescope : Adv`,
and renders `admire(2)(in(gallery), with(telescope), mary, painting)`. Its timed
variant stays registered as
`at_T(yesterday, admire(2)(in(gallery), with(telescope), mary, painting))` with
`explicit_agent_theme_with_adv_sequence_at_time`. The three-Adv sequence
`Mary admired the painting in the gallery with a telescope near a window` is
checked with `near_window : Adv` alongside the earlier Adv declarations, and
renders `admire(3)(in(gallery), with(telescope), near(window), mary, painting)`.
The four-Adv sequence `Mary admired the painting in the gallery with a telescope
near a window beside a shelf` is also checked as registered, with
`beside_shelf : Adv` and
`admire(4)(in(gallery), with(telescope), near(window), beside(shelf), mary,
painting)`. The former five-Adv fallback boundary is now checked as the same
registered construction: `Mary admired the painting in the gallery with a
telescope near a window beside a shelf under a lamp yesterday` renders
`at_T(yesterday, admire(5)(in(gallery), with(telescope), near(window),
beside(shelf), under(lamp), mary, painting))` with `under_lamp : Adv`.
Meanwhile, `Mary laughed loudly` must surface as the registered
`manner_intransitive_predication` construction with
`manner_intransitive_predication_single_reading`; its scaffold must declare
`loudly : Adv`, not `loudly : Entity`. The timed variant `Mary laughed loudly
yesterday` remains registered as
`at_T(yesterday, laugh(1)(loudly, mary))` with the
`explicit_agent_with_manner_adv_at_time` scope and no fallback draft.
`Mary laughed loudly in the park` must surface as the registered
`manner_locative_intransitive_predication` construction with
`manner_locative_intransitive_predication_single_reading`; its scaffold must
declare `loudly : Adv` and `in_park : Adv`, not entity surrogates. The timed
variant `Mary laughed loudly in the park yesterday` remains registered as
`at_T(yesterday, laugh(2)(loudly, in(park), mary))` with the
`explicit_agent_with_manner_and_location_adv_at_time` scope and no fallback
draft.
`Mary laughed loudly in the park near a window` must surface as the registered
`manner_two_location_intransitive_predication` construction with
`manner_two_location_intransitive_predication_single_reading`; its scaffold must
declare `loudly : Adv`, `in_park : Adv`, and `near_window : Adv`, not entity
surrogates. The timed variant `Mary laughed loudly in the park near a window
yesterday` remains registered as
`at_T(yesterday, laugh(3)(loudly, in(park), near(window), mary))` with the
`explicit_agent_with_manner_and_two_location_adv_at_time` scope and no fallback
draft.
`Mary laughed loudly in the park near a window beside a shelf` must surface as
the registered `manner_three_location_intransitive_predication` construction
with `manner_three_location_intransitive_predication_single_reading`; its
scaffold must declare `loudly : Adv`, `in_park : Adv`, `near_window : Adv`, and
`beside_shelf : Adv`, not entity surrogates. The timed variant `Mary laughed
loudly in the park near a window beside a shelf yesterday` remains registered
as `at_T(yesterday, laugh(4)(loudly, in(park), near(window), beside(shelf), mary))`
with the `explicit_agent_with_manner_and_three_location_adv_at_time` scope and
no fallback draft.
`Mary laughed loudly in the park near a window beside a shelf under a lamp`
must surface as the registered
`manner_location_sequence_intransitive_predication` construction with
`manner_location_sequence_intransitive_predication_single_reading`; its
scaffold must declare `loudly : Adv`, `in_park : Adv`, `near_window : Adv`,
`beside_shelf : Adv`, and `under_lamp : Adv`, not entity surrogates. The timed
variant remains registered as
`at_T(yesterday, laugh(5)(loudly, in(park), near(window), beside(shelf), under(lamp), mary))`.
The extended pure Location sequence `Mary laughed loudly in the park near a
window beside a shelf under a lamp on a table yesterday` remains registered as
`at_T(yesterday, laugh(6)(loudly, in(park), near(window), beside(shelf), under(lamp), on(table), mary))`,
with `on_table : Adv` rather than an entity surrogate.
`Mary laughed loudly in the park with a telescope` must surface as the
registered `manner_location_instrument_intransitive_predication` construction
with `manner_location_instrument_intransitive_predication_single_reading`; its
scaffold must declare `loudly : Adv`, `in_park : Adv`, and
`with_telescope : Adv`, not entity surrogates. The extended timed mixed-role
sequence `Mary laughed loudly in the park near a window beside a shelf under a
lamp with a telescope yesterday` remains registered as
`at_T(yesterday, laugh(6)(loudly, in(park), near(window), beside(shelf), under(lamp), with(telescope), mary))`.
Tail Instrument+ sequences are registered under the same rule: `Mary laughed
loudly in the park near a window beside a shelf under a lamp with a telescope
with a camera yesterday` exports
`at_T(yesterday, laugh(7)(loudly, in(park), near(window), beside(shelf), under(lamp), with(telescope), with(camera), mary))`
and must declare both `with_telescope : Adv` and `with_camera : Adv`.
The mixed Location/Instrument route `Mary laughed loudly in the park with a
telescope near a window with a camera yesterday` is also registered, but under
`manner_mixed_location_instrument_intransitive_predication`: it preserves the
surface role pattern `Manner, Location, Instrument, Location, Instrument`,
exports
`at_T(yesterday, laugh(5)(loudly, in(park), with(telescope), near(window), with(camera), mary))`,
and declares `with_telescope`, `near_window`, and `with_camera` as `Adv`
rather than `Entity`.
The mixed directional/Instrument route `Mary laughed loudly in the park with a
telescope from a window with a camera yesterday` is registered under
`manner_mixed_directional_instrument_intransitive_predication`: it preserves the
surface role pattern `Manner, Location, Instrument, Source, Instrument`, exports
`at_T(yesterday, laugh(5)(loudly, in(park), with(telescope), from(window), with(camera), mary))`,
and declares `from_window` and `with_camera` as `Adv` rather than `Entity`. The
same rule has a Goal witness with `into a room`, preserving
`Manner, Location, Instrument, Goal, Instrument`.
The smaller Manner/Instrument route `Mary laughed loudly with a telescope
yesterday` is now registered under
`manner_instrument_intransitive_predication`: it preserves the surface role
pattern `Manner, Instrument`, exports
`at_T(yesterday, laugh(2)(loudly, with(telescope), mary))`, and declares both
`loudly` and `with_telescope` as `Adv`. The semantic-reading row is
`manner_instrument_intransitive_predication_single_reading`.
The smaller Instrument-only route `Mary laughed with a telescope yesterday` is
now registered under `instrument_intransitive_predication`: it preserves the
surface role pattern `Instrument`, exports
`at_T(yesterday, laugh(1)(with(telescope), mary))`, declares `with_telescope`
as `Adv`, and surfaces `instrument_intransitive_predication_single_reading`.
Meanwhile, `a cat sits on a mat` and `Mary laughed near a window yesterday`
must surface
as the registered `locative_intransitive_predication` construction with
`locative_intransitive_predication_single_reading`; their Coq/Rocq scaffolds
must declare `on_mat : Adv` and `near_window : Adv`, not Entity surrogates. The
ordinary fallback success contract is instead exercised with `Mary laughed from
a window yesterday`, a shallow Source-only directional modifier scaffold
`at_T(yesterday, laugh(1)(from(window), mary))` with
`fallback_single_reading` and a downloadable construction-rule draft. This
keeps promoted constructions and the
remaining fallback success contract from drifting apart.
It should also exercise a multi-reading quantifier-scope success path with
`some boy loves some girl`, requiring `some_boy_wide_scope` and
`some_girl_wide_scope` to appear as distinct JSON readings, Coq/Rocq exports,
and HTML reading rows.
It should also exercise a registered perception-complement success path with
`Mary saw John leave`, requiring `mary_saw_john_leave`,
`perception_nominalization`, and the `E : Prop -> Entity` nominalizer scaffold
to remain visible at the HTTP boundary.
It should also exercise a registered timed-after success path with
`after the singing of the Marseillaise, John saluted the flag`, requiring
`after_singing_salute`, `timed_after_singing_salute`, and
`before : Time -> Time -> Prop` to remain visible instead of an event-ordering
parameter.
It should also exercise a registered universal timed burning success path with
`In every burning, oxygen is consumed`, requiring
`every_burning_consumes_oxygen`, `universal_timed_burning`, and the
`Time`-indexed `burn : Entity -> Time -> Prop` / `consume : Entity -> Time -> Prop`
scaffold to remain visible without `Event` or `IN` in the generated Coq/Rocq
module.
The verifier should implement these ordinary success cases through shared
success-envelope, semantic-reading-summary, and text-fragment helpers rather
than five hand-maintained copies, so adding a new registered success case
extends one audited acceptance shape.
Those helpers should also check the `verification_scope` JSON object and the
matching HTML data attributes, so browser and API clients can tell whether a
successful result is a construction-rule certification or only a shallow
fallback scaffold.
The same smoke check should fetch `/api/certified-fragment` and compare the
manifest with the `Certified Fragment` panel. This keeps the project-level
coverage boundary synchronized with the registered construction registry.
It should also validate `coverage_matrix_counts` against the actual matrix
lists and compare the page's coverage-count attributes and example hooks with
the JSON manifest.
It should likewise validate `semantic_snapshot_count`, the page's
`data-semantic-snapshot-*` hooks, and the live pipeline output for every
snapshot so analysis labels, reading names, Coq/Rocq definitions, and
dependent-type fragments cannot drift silently. It should compare
`expected_ast_summary` with a freshly computed AST structure summary for the
same sentence, so parser-level drift is caught before it is hidden by a similar
surface rendering.
The helper should reject any fixture whose `failure_stage` is outside the
controlled diagnostics set: `input`, `parsing`, `type_check`,
`semantic_readings_check`, `construction_hygiene`, and `coq_check`. The fixture
manifest should also cover the four internal/proof-boundary stages
`type_check`, `semantic_readings_check`, `construction_hygiene`, and
`coq_check`; input and parsing failures remain covered by ordinary
`/api/analyze` failure tests rather than by controlled fixture pages. Those
ordinary tests should compare the page-local Action JSON preview, the
`/api/analyze-action` payload, the download response, and the
human-review inspection rejection where no automatic run is allowed.
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

The active argument-omission slice has now been promoted out of ordinary
fallback. For example, `John ate` becomes an event-semantics formula with
`eat(e)` and `Agent(e, John)`, then translates to
`Sigma x_theme : Food. eat(0)(John, x_theme)` under the registered
`active_argument_omission` rule. The omitted Theme is represented by the typed
Sigma witness `x_theme : Food`, not by an exported `Event`, `Agent`, or `Theme`
predicate.

The plain transitive slice has also been promoted out of ordinary fallback. For
example, `Mary admired the painting` becomes an event-semantics formula with
`admire(e)`, `Agent(e, mary)`, and `Theme(e, painting)`, then translates to
`admire(0)(mary, painting)` under the registered
`plain_transitive_predication` rule. Both arguments remain explicit typed
predicate arguments; construction hygiene rejects exported `Event`, `Agent`, or
`Theme` role predicates. The same rule accepts a single outer temporal wrapper:
`Mary admired the painting yesterday` becomes
`at_T(yesterday, admire(0)(mary, painting))` with
`explicit_agent_theme_at_time`, rather than being exported as a fallback draft.

The plain intransitive slice is now registered separately from locative
intransitives and from the ordinary fallback path. `Mary smiled` is recognized
as a typed unary predicate over the explicit Agent argument and exports
`smile(0)(mary)` with the semantic reading
`plain_intransitive_predication_single_reading`. `Mary smiled yesterday` keeps
the same construction under the proposition-level temporal wrapper
`at_T(yesterday, smile(0)(mary))`. The generated Coq/Rocq scaffold declares
`smile : forall n : nat, ModifierSeq n -> Entity -> PropT` and rejects hidden
`Event`, `Agent`, or `Theme` role-predicate declarations.

The modified transitive slice now covers non-empty predicate-level `ModifierSeq`
values on the same explicit Agent/Theme frame. For example, `Mary admired the painting in
the gallery` translates to `admire(1)(in(gallery), mary, painting)` under the
registered `modified_transitive_predication` rule. The modifier is checked
through the `ModifierSeq` family and exported as `in_gallery : Adv`, not as an
entity. Its timed variant `Mary admired the painting in the gallery yesterday`
is checked as `at_T(yesterday, admire(1)(in(gallery), mary, painting))` with
`explicit_agent_theme_with_adv_at_time`. The same construction now accepts the
ordered sequence `in(gallery), with(telescope)` and renders `Mary admired the
painting in the gallery with a telescope` as
`admire(2)(in(gallery), with(telescope), mary, painting)`, with the two modifier
roles audited as Location and Instrument and exported as Adv constants. The
same non-empty `ModifierSeq` rule covers longer sequences: `Mary admired the painting in the gallery with a
telescope near a window` is checked as
`admire(3)(in(gallery), with(telescope), near(window), mary, painting)`, with
`near_window : Adv` and a Location audit for the third modifier. It also covers
`Mary admired the painting in the gallery with a
telescope near a window beside a shelf` as
`admire(4)(in(gallery), with(telescope), near(window), beside(shelf), mary,
painting)`, with `beside_shelf : Adv` and a Location audit for the fourth
modifier, and the five-Adv timed sequence
`Mary admired the painting in the gallery with a telescope near a window beside
a shelf under a lamp yesterday` is checked as
`at_T(yesterday, admire(5)(in(gallery), with(telescope), near(window),
beside(shelf), under(lamp), mary, painting))`, with `under_lamp : Adv`.

The locative intransitive slice has also been promoted out of ordinary fallback.
For example, `a cat sits on a mat` becomes an event-semantics formula with
`sit(e)`, `Agent(e, cat)`, and `on(e, mat)`, then translates to
`sit(1)(on(mat), cat)` under the registered
`locative_intransitive_predication` rule. The modifier `on(mat)` is exported as
an `Adv` item, not as an entity, and construction hygiene rejects an
`on_mat : Entity` declaration.

The object-final resultative slice is now registered as well. `John hammered
the metal flat` is checked under `resultative_predication`, exposes
`resultative_predication_single_reading` with scope
`explicit_agent_theme_result`, and exports
`Cause(john, Transition(metal, shape_scale, not_flat, flat))` with `metal` as
an `Entity`, `flat`/`not_flat` as `State` values, and `shape_scale` as a
`StateScale`. `Mary painted the door red` follows the same registered route,
while still surfacing a non-fatal warning because `red` has no unique lexical
pre-state and therefore uses `unknown_state`. Simple temporal wrappers are now
registered too: `Mary admired the painting red yesterday` exports
`at_T(yesterday, Cause(mary, Transition(painting, color_scale, _, red)))` with
the scope `explicit_agent_theme_result_at_time`. The construction hygiene policy
rejects hidden `Event`, `Agent`, `Theme`, and `ResultState` predicate fragments.

The manner intransitive slice is now registered for exactly one typed manner
adverb over an explicit Agent. `Mary laughed loudly` exports
`laugh(1)(loudly, mary)` with `loudly : Adv`; `Mary laughed loudly yesterday`
keeps the same registered rule under `at_T`. A second reviewed slice registers
one Manner Adv plus one Location Adv over the same unary predicate family:
`Mary laughed loudly in the park` exports
`laugh(2)(loudly, in(park), mary)` with `loudly : Adv` and `in_park : Adv`,
and its timed variant remains registered under `at_T`. Other simple English
sentences are still handled by the fallback parser. A third reviewed slice
registers one Manner Adv plus two Location Advs:
`Mary laughed loudly in the park near a window` exports
`laugh(3)(loudly, in(park), near(window), mary)`, and its timed variant remains
registered under `at_T`. A fourth reviewed slice registers one Manner Adv plus
three Location Advs: `Mary laughed loudly in the park near a window beside a
shelf` exports `laugh(4)(loudly, in(park), near(window), beside(shelf), mary)`,
and its timed variant remains registered under `at_T`. A fifth reviewed slice
registers the pure Location sequence beyond that fixed depth:
`Mary laughed loudly in the park near a window beside a shelf under a lamp`
exports `laugh(5)(loudly, in(park), near(window), beside(shelf), under(lamp), mary)`,
and the extended timed sequence with `on a table yesterday` exports
`at_T(yesterday, laugh(6)(loudly, in(park), near(window), beside(shelf), under(lamp), on(table), mary))`.
The next reviewed slice registers one Manner Adv followed by one or more
Location Advs and one Instrument Adv:
`Mary laughed loudly in the park with a telescope` exports
`laugh(3)(loudly, in(park), with(telescope), mary)`, and the longer timed
variant with `near a window beside a shelf under a lamp with a telescope
yesterday` exports
`at_T(yesterday, laugh(6)(loudly, in(park), near(window), beside(shelf), under(lamp), with(telescope), mary))`.
It now also registers tail Instrument+ sequences: `Mary laughed loudly in the
park with a telescope with a camera with a microphone` exports
`laugh(5)(loudly, in(park), with(telescope), with(camera), with(microphone), mary)`.
The next reviewed slice then registers true Location/Instrument interleaving:
`Mary laughed loudly in the park with a telescope near a window with a camera
yesterday` exports
`at_T(yesterday, laugh(5)(loudly, in(park), with(telescope), near(window), with(camera), mary))`
under `manner_mixed_location_instrument_intransitive_predication`. The next
reviewed slice registers directional/Instrument interleaving:
`Mary laughed loudly in the park with a telescope from a window with a camera
yesterday` exports
`at_T(yesterday, laugh(5)(loudly, in(park), with(telescope), from(window), with(camera), mary))`
under `manner_mixed_directional_instrument_intransitive_predication`, and its
Goal witness uses `into(room)` in the same typed Adv position. The remaining
fallback example is deliberately narrower because the Instrument-only and
Manner/Instrument slices are now registered:
`Mary laughed from a window yesterday` remains a shallow Source-only directional
modifier scaffold,
`at_T(yesterday, laugh(1)(from(window), mary))`, with a
construction-rule draft rather than construction-level certification.

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
The same page should expose the narrow because-clause route as a certified
proposition-level causal connective: `John left because Mary cried` appears as
`because_T(cry(mary), leave(john))`, the typed transitive variant
`John ate bread because Mary drank water yesterday` appears as
`because_T(at_T(yesterday, drink(mary, water)), eat(john, bread))` with
`water : Drinkable` and `bread : Food`, the lexical-state-change variant
`John opened the door because Mary cleaned the room` appears as
`because_T(Cause(mary, Transition(room, cleanliness_scale, dirty, clean)), Cause(john, Transition(door, access_scale, closed, open)))`,
with `clean` and `open` displayed as `State` targets in the result-state audit,
mixed simple/state-change variants such as `Mary cried because the door opened`
and `the door opened because Mary cried` appear as
`because_T(Change(Transition(door, access_scale, closed, open)), cry(mary))`
and `because_T(cry(mary), Change(Transition(door, access_scale, closed, open)))`,
and the instrumental variant `Mary cried because John opened the door with a key`
appears as
`because_T(CauseWithInstrument(john, key, Transition(door, access_scale, closed, open)), cry(mary))`,
and the controlled anaphoric variant
`Mary admired the door because it opened` appears as
`because_T(Change(Transition(door, access_scale, closed, open)), admire(mary, door))`.
The AST panel should show the transition theme's `anaphora` object with
`pronoun`, `resolved_to`, `source_clause`, `source_role`, and
`resolution_policy`. Inputs such as `Mary cried because it opened` or
`Mary visited Paris because it opened` should fail at `type_check`, so the page
does not present `it : Entity` as a verified proof-assistant declaration,
and the stative-precondition variant
`John opened the door because it was closed` appears as
`because_T(holds_state(door, access_scale, closed), Cause(john, Transition(door, access_scale, closed, open)))`.
The Coq/Rocq panel should declare
`holds_state : Entity -> StateScale -> State -> Prop` and should not export
`it : Entity`; a scale-incompatible case such as
`John opened the door because it was red` should stop at `type_check`,
while a negated stative reason such as
`Mary admired the vase because it was not broken` should appear as
`because_T(not_T(holds_state(vase, integrity_scale, broken)), admire(mary, vase))`
with `not_T : Prop -> Prop` and the same controlled `it` resolution,
and concrete color-state cases such as
`Mary admired the door because it was red` should resolve to
`because_T(holds_state(door, color_scale, red), admire(mary, door))` while
place-like inputs such as `Mary visited Paris because it was red` remain
type-check failures,
and conjoined state cases such as
`Mary admired the door because it was red and open` should resolve to
`because_T(and_T(holds_state(door, color_scale, red), holds_state(door, access_scale, open)), admire(mary, door))`;
same-scale compatible cases such as
`Mary admired the board because it was flat and straight` should pass without
duplicating the `shape_scale` Coq/Rocq declaration, while registered
same-scale oppositions such as `the door is closed and open` and
`Mary admired the door because it was closed and open` should remain visible as
`type_check` failures with the message that `access_scale` has both `closed`
and `open`;
the JSON result carries the same lexical opposition as
`type_check.incompatible_state_pairs`, and `diagnostics.state_opposition_count`
with `diagnostics.state_opposition_diagnostics` mirrors that list for clients;
the HTML renders a `State Opposition Diagnostics` panel with stable hooks such
as `data-state-opposition-scale`, `data-state-opposition-left`,
`data-state-opposition-right`, `data-state-opposition-relation`, and
`data-state-opposition-path`;
the page should still reject partial state-scale matches such as
`John opened the door because it was red and open`,
and the timed/modifier case
`John left quickly because Mary cried today` appears as
`because_T(at_T(today, cry(mary)), leave(1)(quickly, john))`, with
`because_T` declared at type `Prop -> Prop -> Prop`.
Clause-level markers outside the current certified fragment, including `who`,
`which`, `that`, `whether`, nested because strings such as
`John left because Mary cried because Sue left`, and overextended conditional
strings such as `if John left, Mary cried because Sue left`, stop the analysis
at the parsing stage before a fallback formula or Coq/Rocq scaffold can be
generated. This prevents malformed
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
