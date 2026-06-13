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

Use `python3 scripts/verify_project.py --skip-coq` to skip this optional
boundary check, or `python3 scripts/verify_project.py --require-coq` to fail
when Coq/Rocq is unavailable.
