# Web Pipeline Design

This project can support a web interface with four visible stages:

1. Natural-language input
2. Event-semantics analysis
3. Dependent-type translation
4. Coq/Rocq boundary validation

The current repository implements the first small backend slice in
`translator/natural_language_pipeline.py`. It combines hand-written analyses
for the main research examples with a conservative fallback parser for simple
English sentences. This keeps the verification problem honest: the user can see
where parsing succeeds, where translation succeeds, and where Coq validation
succeeds, while unlisted sentences receive a shallow first-pass analysis rather
than a false claim of full semantic understanding.

The repository also includes a small dependency-free local web demo in
`web/app.py`. It is intended as a thin interface over the verified backend, not
as a separate semantic implementation.

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

The request has two stable query parameters:

- `sentence`: required natural-language input;
- `require_coq`: optional flag, where `1` requests the external Coq/Rocq
  boundary check and the default leaves it skipped when not needed.

The response is a single JSON object. On success, it must expose the same
semantic artifacts shown on the page: `event_semantics`,
`dependent_type_translation`, `ast`, `coq_code`, `construction_rule`,
`construction_hygiene`, `coq_check`, `diagnostics`, and `conclusion`. On
failure, it must still return `ok: false`, an `error` message when available,
and a `diagnostics` object so callers can distinguish parser, type-checking,
construction-hygiene, and Coq/Rocq boundary failures.

`diagnostics.failure_stage` is the machine-readable failure locator. It is
`null` on successful translations and otherwise one of `input`, `parsing`,
`type_check`, `construction_hygiene`, or `coq_check`.

## Successful Response

A successful response should include:

- the original sentence;
- the event-semantics formula as JSON;
- the dependent-type rendering;
- the compact diagnostics summary;
- the structured AST;
- the generated Coq scaffold;
- the Coq/Rocq validation status;
- a short conclusion.

The diagnostics summary has four stage values: `passed`, `failed`, `skipped`,
and `not_applicable`. It summarizes `type_check`, `construction_hygiene`, and
`coq_check` so a user can see whether a failure belongs to internal structure,
construction-specific hygiene, or the external proof-assistant boundary.
The separate `failure_stage` field distinguishes input/parsing failures from
later semantic and proof-assistant failures.

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
in which the girl existential has wider scope. In this path, `boy` and `girl`
are predicates of type `Entity -> Prop`, while `some` is a quantifier pattern,
not an entity constant.

The first Parsons-style event-talk case is handled by a timed replacement
instead of an event parameter. The sentence `after the singing of the
Marseillaise, John saluted the flag` keeps a visible event-semantics reference
formula for comparison, but its checked Coq scaffold declares `Time`,
`before : Time -> Time -> Prop`, `sing : Entity -> Time -> Prop`, and
`salute : Entity -> Entity -> Time -> Prop`. It defines the translation as an
existential formula over two time variables and deliberately does not declare
`Event`.

The remaining two Parsons/Luo-Shi examples have their own typed routes. `Mary
saw John leave` uses a nominalizing map `E : Prop -> Entity`, so the perceived
content is rendered as `see Mary (E (leave John))` rather than as a hidden
event argument. `In every burning, oxygen is consumed` is rendered as
`forall x : Entity, forall t : Time, burn x t -> consume oxygen t`; the checked
scaffold therefore avoids both an `Event` type and an event-inclusion predicate
such as `IN`.

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

The `Construction Rule` panel must distinguish a rule's policy from an actual
failure. `forbidden_coq_fragments` names fragments that would be illegal for the
matched construction. `found_forbidden_fragments` reports fragments that were
actually found in the generated Coq scaffold. A successful replacement can
therefore display forbidden fragments as policy while still showing `hygiene:
passed` and `found forbidden fragments: none`.

## Type Discipline

The web demo must not treat every surface phrase as an entity. In particular,
Luo-Shi style adverbial and prepositional modifiers are represented at type
`Adv`, with the shallow Coq interface:

```coq
Definition Adv : Type := (Entity -> PropT) -> Entity -> PropT.
```

For example, `john buttered the toast in the bathroom with a knife` exports
`in_bathroom : Adv`, `with_knife : Adv`, `john : Entity`, `toast : Entity`, and
`butter : nat -> Adv -> Adv -> Entity -> Entity -> PropT`.
