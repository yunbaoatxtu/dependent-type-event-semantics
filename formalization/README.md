# Formalization Scaffolds

This directory contains generated Lean/Coq-style shallow embeddings of checked
translator examples.

Generate the files with:

```bash
python3 scripts/generate_formalization.py
```

The generated files are interface scaffolds. They are intended as the next
bridge toward a real proof-assistant development, not as complete proofs.

The current files include all checked examples in `translator/examples/` and
are regenerated from `type_check.ok` translator outputs.

Check consistency with:

```bash
python3 scripts/check_formalization.py
```

The checker regenerates the scaffold files and verifies that the committed
outputs contain the expected declarations, `Check`/`#check` commands, and
normalized proof-assistant names. It also checks that causal-resultative states
are not exported as ordinary entities: `intact` and `broken` have type `State`,
`integrity_scale` has type `StateScale`, and `Transition` has type
`Entity -> StateScale -> State -> State -> TransitionT`. Resultative examples
with a known lexical pre-state therefore export that state directly; examples
without one still normalize `_` as `unknown_state`.

Coq/Rocq is a boundary validator here, not the implementation language of the
translator. The Python translator is responsible for producing and checking the
AST. When Coq/Rocq is available, the project verification script can also
compile the generated Coq scaffold to confirm that exported terms are acceptable
to a proof-assistant type checker:

```bash
python3 scripts/verify_project.py
```

The scaffold also declares `SemanticPreservation` and generates one
`example_i_semantic_preservation_obligation` statement for each exported
example. It also generates a structured obligation record and a Coq theorem
named `example_i_semantic_preservation_obligation_is_prop` for each example.
Those theorems are well-formedness proofs: they show that the named target is a
`Prop`-level obligation, not that semantic preservation itself has been proved.
The generated theorem `example_i_semantic_preservation_target_matches` is a
record-binding proof: it shows that the record's `obligation_statement` is
exactly the `SemanticPreservation` target for the exported example.
The statements remain named theorem-obligation rows and not proofs of semantic
preservation. They make the next proof-development targets explicit while
preserving the current shallow-boundary claim.

Use `python3 scripts/verify_project.py --skip-coq` to skip this optional
boundary check, or `python3 scripts/verify_project.py --require-coq` to fail
when Coq/Rocq is unavailable.
