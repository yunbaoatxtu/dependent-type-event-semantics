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

Run all deterministic project checks through one entry point:

```bash
python3 scripts/verify_project.py
```

If Coq/Rocq is installed, the verification script also checks:

```bash
coqc formalization/DependentTypeEventSemantics.v
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
