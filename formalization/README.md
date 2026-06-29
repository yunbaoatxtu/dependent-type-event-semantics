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

The scaffold also declares `SemanticPreservation` as an inductive structural
proof relation and `ModelInterpretable` as a separate inductive
model-interface relation. It generates one
`example_i_semantic_preservation_obligation` statement for each exported
example. It also generates a structured obligation record and a Coq theorem
named `example_i_semantic_preservation_obligation_is_prop` for each example.
Those theorems are well-formedness proofs: they show that the named target is a
`Prop`-level obligation.
The generated theorem `example_i_semantic_preservation_target_matches` is a
record-binding proof: it shows that the record's `obligation_statement` is
exactly the `SemanticPreservation` target for the exported example.
The generated theorem `example_i_semantic_preservation_proved` is a structural
preservation proof: Coq checks that the exported example can be derived from
constructors for lexical predicate application, Sigma witnesses, repetition,
time operators, negation, Transition, and Cause. The generated theorem
`semantic_preservation_model_interpretable` proves that every structural
preservation derivation can be lifted to `ModelInterpretable`, and each example
therefore receives a checked `example_i_model_interpretable` theorem. The
scaffold now also declares a `SemanticModel` record with a generic
`model_denotes` field and closure fields for lexical applications, Sigma
witnesses, repetition, time operators, negation, Transition, and Cause. The
global theorem `model_interpretable_denotational_sound` proves that every
`ModelInterpretable` term is denoted by any `SemanticModel` satisfying those
closure fields, and each exported example receives a checked
`example_i_denotationally_sound` theorem. The next interface layer declares a
`TruthConditionSpec` record, turns any such record into a `SemanticModel` via
`semantic_model_from_truth_conditions`, proves
`truth_conditions_induce_denotational_soundness`, and checks
`example_i_truth_condition_sound` for each exported example. The generated
file also includes a deliberately degenerate `tautological_truth_conditions`
instance, the induced `tautological_semantic_model`, an existence theorem for
that instance, and `example_i_tautological_truth_condition_sound` for every
exported example. The generated file now also includes a stricter
`structural_truth_conditions` instance whose `truth_denotes` predicate is
`ModelInterpretable`, the induced `structural_semantic_model`, an existence
theorem, and `example_i_structural_truth_condition_sound` for every exported
example. This is still not a proof of full denotational soundness, because the
structural instance does not provide independently specified lexical,
temporal, causal, quantificational, or modifier truth conditions. The generated
file therefore adds one more bridge layer, `ConcreteTruthConditionKernel`,
which names the lexical, quantifier/Sigma, repetition, temporal, polarity,
transition, and causal clauses that an independently justified concrete model
must provide. `truth_conditions_from_concrete_kernel` turns any such kernel
into a `TruthConditionSpec`, and every exported example receives a checked
`example_i_concrete_kernel_truth_condition_sound` theorem parameterized by an
arbitrary kernel. The generated file now also inhabits that interface with
`model_interpretable_truth_kernel`, whose denotation predicate is
`ModelInterpretable`, exports
`model_interpretable_truth_conditions_from_kernel`, proves kernel existence, and
checks `example_i_model_interpretable_truth_kernel_sound` for every exported
example. It now also introduces `SyntaxDirectedTruth` as a distinct
syntax-directed truth relation, proves
`semantic_preservation_syntax_directed_truth`, inhabits the kernel interface
with `syntax_directed_truth_kernel`, and checks
`example_i_syntax_directed_truth_kernel_sound` for every exported example. Thus
the current semantic preservation layer, the truth-condition-spec bridge, the
inhabitation sanity instance, the structural truth-condition instance, the
concrete-kernel bridge, the model-interpretable kernel instance, and the
syntax-directed kernel instance are proof-checked. The file now also declares a
`PrimitiveTruthAssumptions` record, a `primitive_truth_assumptions` parameter,
a `primitive_truth_kernel` derived from that record, and
`example_i_primitive_truth_kernel_sound` checks. This turns the next concrete
model stage into a typed set of primitive lexical, temporal, causal,
quantificational, polarity, and transition obligations, while independently
specified concrete truth-condition instantiation remains open. The next layer
is `AtomicClosureTruth`: the generated files declare `AtomicBaseTruth` and
`AtomicTruthFacts`, close Sigma, repetition, time, negation, transition, and
cause through checked constructors, build `atomic_closure_truth_kernel`, and
check both `example_i_atomic_closure_truth` and
`example_i_atomic_closure_truth_kernel_sound` for every exported example. This
narrows the remaining assumptions to atom-level lexical and transition facts
without claiming that those facts have already been derived from a full
semantic model.

Use `python3 scripts/verify_project.py --skip-coq` to skip this optional
boundary check, or `python3 scripts/verify_project.py --require-coq` to fail
when Coq/Rocq is unavailable.
