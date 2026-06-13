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
words, and simple prepositional modifiers.

Quantifier-scope examples receive a separate ambiguity analysis instead of
being forced through the fallback parser:

```bash
python3 -m translator.natural_language_pipeline \
  "some boy loves some girl" \
  --require-coq
```

This produces both subject-wide and object-wide existential readings and checks
the generated Coq scaffold. Coq/Rocq verifies the exported formal terms; it does
not by itself prove that an arbitrary natural-language parse is the only correct
semantic analysis.

Modifier typing follows the Luo-Shi variable-polyadicity analysis. Adverbial
and prepositional modifiers are exported as `Adv`, not `Entity`:

```coq
Definition Adv : Type := (Entity -> PropT) -> Entity -> PropT.
Parameter in_bathroom : Adv.
Parameter with_knife : Adv.
Parameter butter : nat -> Adv -> Adv -> Entity -> Entity -> PropT.
```

Parsons-style event talk can also be routed through typed replacements. For
example:

```bash
python3 -m translator.natural_language_pipeline \
  "after the singing of the Marseillaise, John saluted the flag" \
  --require-coq
```

This stage exports `Time`, `before`, `sing`, and `salute` declarations and
checks a formula of the form `exists t_sing t_salute : Time, ...`. It does not
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
`E : Prop -> Entity`, yielding `see Mary (E (leave John))`. The burning example
uses universal time quantification:
`forall x : Entity, forall t : Time, burn x t -> consume oxygen t`. Both
generated Coq scaffolds are checked without introducing an `Event` type.

Specialized constructions are tracked by a small construction registry. Each
registered rule declares its phenomenon, analysis function, and Coq fragments
that must not appear in the generated scaffold. For example, the three
Parsons/Luo-Shi replacements forbid hidden `Event` declarations, and the
burning example additionally forbids `IN`.

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
is available. The response includes the same event-semantics JSON,
dependent-type rendering, generated Coq, `construction_rule`,
`construction_hygiene`, `coq_check`, and `diagnostics` fields used by the web
page.

For failures, `diagnostics.failure_stage` distinguishes `input`, `parsing`,
`type_check`, `construction_hygiene`, and `coq_check` failures.

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
- event counting with `once`/`twice`/`thrice` or explicit `count`;
- causal-resultative translation into a typed state transition.

Each translation result includes both a human-readable `translation` string and
a structured `ast` object. The AST is the intended next bridge toward a proof
assistant or a typed semantic checker. The translator also returns a
`type_check` object that verifies basic AST well-formedness.

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
Coq/Rocq installation. Use `--require-coq` locally when proof-assistant boundary
validation is required.

Run all deterministic project checks through one entry point:

```bash
python3 scripts/verify_project.py
```

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
