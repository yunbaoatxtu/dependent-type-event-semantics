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
arbitrary kernel. The generated file now also packages any such kernel as an
`IndependentTruthConditionObligationLedger`, whose fields expose the remaining
independently supplied lexical, quantifier/Sigma, repetition, temporal,
polarity, transition, and causal truth-condition obligations. The checked
ledger theorems prove that this package records the kernel-derived
`TruthConditionSpec` and that the induced truth conditions preserve the
existing model-interpretable boundary. This is a bookkeeping layer, not yet an
independently justified concrete model. The generated file now also adds an
evidence-source boundary for that ledger. `TruthEvidence` is a proof-carrying
interface for clause-level truth evidence, `truth_evidence_sound` decodes such
evidence into a proposition, and `EvidenceBackedTruthConditionSources` collects
lexical, quantifier/Sigma, repetition, temporal, polarity, transition, and
Cause evidence fields. The bridge `concrete_kernel_from_evidence_sources`
converts those evidence fields into a `ConcreteTruthConditionKernel`;
`evidence_backed_truth_condition_ledger` then packages the result as an
`IndependentTruthConditionObligationLedger`, with checked theorems
`evidence_backed_truth_condition_sources_induce_kernel`,
`evidence_backed_truth_condition_sources_induce_truth_conditions`, and
`evidence_backed_truth_condition_sources_sound`. This still does not provide a
full independently justified concrete model, but it makes the future source of
such truth-condition inhabitants explicit. The generated file now also
instantiates that evidence-source boundary with the atomic-closure layer:
`truth_evidence_intro` wraps `AtomicClosureTruth` derivations as evidence,
`atomic_closure_evidence_backed_truth_sources` collects those evidence fields,
and `atomic_closure_evidence_backed_truth_ledger` checks the induced
truth-condition route with per-example
`example_i_atomic_closure_evidence_backed_truth_condition_sound` theorems. This
is a checked source instance for the generated atomic-closure fragment, not a
claim that arbitrary lexical or temporal truth conditions have been
independently justified. The generated file now also inhabits that interface with
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
narrows the remaining assumptions to atom-level lexical and transition facts.
The atom layer is now also less opaque: `AtomicBaseTruth` is generated as an
inductive base-valuation relation, `LexicalAtomTruthAssumptions`,
`TransitionAtomTruthAssumptions`, and
`LexicalTransitionTruthAssumptions` split the remaining atom assumptions into
lexical and transition interfaces, `LexicalTransitionTruthModel` names a
model bridge assembled from those assumptions whose denotation predicate is
`AtomicBaseTruth`, `AtomicValuationSpec` then re-exports those fields as
valuation evidence, and
`atomic_truth_facts` is a concrete record assembled through
`atomic_truth_facts_from_atomic_base_valuation`. The generated files now
additionally name the induced `TruthConditionSpec` as
`atomic_closure_truth_conditions`,
prove `atomic_closure_truth_conditions_exists`, and check
`example_i_atomic_closure_truth_condition_sound` for every exported example.
The latest layer registers only the concrete state transitions that occur in
the exported examples. It declares `RegisteredStateTransitionTruth`, proves
`registered_state_transition_atomic_base_truth`, defines
`TransitionRefinedAtomicClosureTruth`, and checks both
`example_i_transition_refined_atomic_closure_truth` and
`example_i_transition_refined_atomic_closure_sound`. This makes the transition
atom stricter than the generic `AtomicBaseTruth.atomic_base_truth_transition`
constructor while leaving full lexical truth-condition instantiation open.
The generated files now also expose this registered fragment as
`RegisteredTruthConditionSpec`. Its transition field is explicitly restricted
to `RegisteredStateTransitionTruth`, and the checker requires
`transition_refined_registered_truth_conditions`,
`example_i_transition_refined_registered_truth_condition_sound`, and
`example_i_transition_refined_registered_truth_condition_atomic_sound` to stay
present and type checked.
The next generated layer also registers the lexical applications observed in
the exported examples. `RegisteredLexicalApplicationTruth` contains one
constructor per concrete exported lexical application shape, including the
Sigma-bound `x_theme : Food` application in the argument-omission example.
The file proves that these registered lexical applications imply both
`AtomicBaseTruth` and `AtomicClosureTruth`, defines
`FullyRegisteredAtomicClosureTruth`, packages it as
`FullyRegisteredTruthConditionSpec`, and checks
`example_i_fully_registered_atomic_closure_truth`,
`example_i_fully_registered_truth_condition_sound`, and
`example_i_fully_registered_truth_condition_atomic_sound` for every exported
example. The scaffold then factors that same finite registered fragment through
`RegisteredLexicalTruthModel`, converts the model record into
`FullyRegisteredTruthConditionSpec`, instantiates
`registered_lexical_truth_model` with `FullyRegisteredAtomicClosureTruth`, and
checks `example_i_registered_lexical_truth_model_sound` plus
`example_i_registered_lexical_truth_conditions_from_model_sound` for every
exported example. The scaffold then separates the finite registered atom basis
into `ConcreteRegisteredAtomicTruth` and `ConcreteRegisteredTruthBasis`, closes
that basis through `ConcreteRegisteredAtomicModel`, proves
`concrete_registered_atomic_model_denotes_atomic_base_truth` and
`concrete_registered_truth_basis_denotes_atomic_base_truth`, closes it as
`ConcreteRegisteredTruth`, instantiates
`concrete_registered_truth_conditions : FullyRegisteredTruthConditionSpec`, and
checks `example_i_concrete_registered_truth`,
`example_i_concrete_registered_truth_condition_sound`, and
`example_i_concrete_registered_truth_condition_atomic_sound` for every exported
example. The scaffold now also packages this same finite closure as
`RegisteredEvidenceBackedTruthConditionSources`: the generated
`concrete_registered_evidence_backed_truth_sources` wraps registered lexical,
transition, Sigma, repetition, temporal, polarity, and Cause clauses as
`TruthEvidence`, derives
`concrete_registered_evidence_backed_truth_conditions :
FullyRegisteredTruthConditionSpec`, and checks
`example_i_concrete_registered_evidence_backed_truth_condition_sound` plus
`example_i_concrete_registered_evidence_backed_truth_condition_atomic_sound` for
every exported example. This is still a finite registered-fragment source, not
an independently justified truth-condition model for arbitrary lexical
applications. The scaffold then packages the same spec as
`ConcreteRegisteredEvidenceBackedTruthConditionModel`, instantiates
`concrete_registered_evidence_backed_truth_condition_model`, proves that the
model exists, proves that its denotation feeds
`concrete_registered_evidence_backed_truth_conditions`, and proves that both
the model denotation and the spec denotation imply `AtomicClosureTruth`. This
gives the evidence-backed route a model-shaped boundary while keeping the
source finite and registered-fragment-only. The scaffold then gathers the
evidence-backed per-example
truth-condition proofs into
`ConcreteRegisteredEvidenceBackedExampleTruthInstances`, instantiates
`concrete_registered_evidence_backed_example_truth_instances`, proves
`concrete_registered_evidence_backed_example_truth_instances_exists`, and checks
per-example projections such as
`concrete_registered_evidence_backed_example_i_truth_instance_atomic_sound` back
to `AtomicClosureTruth`. This is a package-level witness for the registered
evidence-backed route, not a full truth-condition model. The scaffold then
packages the direct concrete truth-condition model, evidence-backed source and
model, concrete registered kernel, direct/evidence/kernel specs, and the three
example-instance packages as `ConcreteRegisteredTruthConditionRoute`,
instantiates `concrete_registered_truth_condition_route`, proves that the route
exists, proves the direct/evidence/kernel spec-coherence theorems, and checks
route-level direct, evidence-backed, and kernel atomic soundness for every
exported example. This makes the finite registered truth-condition routes
auditable as one object before any broader independently supplied truth model
is claimed. The scaffold then packages those three route projections for every
exported example as
`ConcreteRegisteredTruthConditionRouteExampleAgreement`, instantiates
`concrete_registered_truth_condition_route_example_agreement`, proves that the
agreement exists and points back to `concrete_registered_truth_condition_route`,
and rechecks the packaged direct, evidence-backed, and kernel projections back
to `AtomicClosureTruth`. This is still finite route agreement, not a proof of a
general independently supplied truth-condition model. The scaffold then records
the same finite route as `IndependentRegisteredTruthConditionSources`,
instantiates `independent_registered_truth_condition_sources`, proves that this
source package exists, proves that its stored direct spec and route-agreement
package match the stored route, proves
`independent_registered_truth_condition_sources_spec_sound`, and checks
`independent_registered_truth_condition_sources_example_i_atomic_sound` for
every exported example. This gives the next independently supplied
truth-condition stage a named source boundary without claiming full natural
language coverage. The scaffold then expands that boundary as
`IndependentRegisteredTruthConditionClauseInstances`, instantiates
`independent_registered_truth_condition_clause_instances`, proves that the
clause package exists and matches the stored source spec, and checks named
constructor-level projections for lexical applications, each exported Sigma
type, repetition, temporal operators, polarity, registered Transition, and
Cause. It also checks
`independent_registered_truth_condition_clause_example_i_atomic_sound` for
every exported example. This gives later semantic-strengthening work a
constructor-by-constructor replacement surface instead of one opaque source
record. The scaffold then packages those projections as
`IndependentRegisteredTruthConditionClauseCoverage`, instantiates
`independent_registered_truth_condition_clause_coverage`, proves that the
coverage package exists, proves that it still points to
`independent_registered_truth_condition_clause_instances`, exposes
`independent_registered_truth_condition_clause_coverage_spec_sound`, and checks
`independent_registered_truth_condition_clause_coverage_example_i_atomic_sound`
for every exported example. This is a finite coverage ledger for the registered
constructor classes, not a proof that arbitrary lexical, temporal, causal, or
quantificational clauses have independent truth conditions. The scaffold then
extracts the temporal fragment as
`IndependentRegisteredTemporalTruthConditionInstances`, instantiates
`independent_registered_temporal_truth_condition_instances`, proves that the
temporal package exists, proves that it still points to
`independent_registered_truth_condition_clause_coverage`, and checks named
projections for `at_T`, `during_T`, `before_T`, `after_T`, `until_T`, and
`since_T`. This gives the Parsons/Luo-Shi time-operator replacement route a
separate proof interface while keeping the broader truth-condition completion
blocker in place. The scaffold also
packages the finite registered closure clauses as
`ConcreteRegisteredCompositionalModel`: its fields expose the denotation
predicate, the atomic inclusion clause, Sigma projection clauses for exported
types, repetition, temporal, polarity, and Cause closure clauses, and a
soundness bridge back to `AtomicClosureTruth`. The generated files instantiate
`concrete_registered_compositional_model` from `ConcreteRegisteredTruth`, prove
`concrete_registered_compositional_model_exists`, and check projection theorems
such as `concrete_registered_compositional_model_repeat_clause`,
`concrete_registered_compositional_model_at_T_clause`,
`concrete_registered_compositional_model_cause_clause`, and
`concrete_registered_compositional_model_sigma_Entity_clause`. This makes the
compositional closure stage explicit before the scaffold packages the same
finite truth-condition route as
`ConcreteRegisteredTruthConditionModel`, proving that its model denotation feeds
the generated `FullyRegisteredTruthConditionSpec` and that both routes imply
`AtomicClosureTruth`. The scaffold then factors the same finite closure through
`ConcreteRegisteredTruthKernel`, whose lexical and transition clauses require
`RegisteredLexicalApplicationTruth` and `RegisteredStateTransitionTruth`
evidence rather than arbitrary unregistered atom facts. It derives
`concrete_registered_truth_conditions_from_kernel` and checks
`example_i_concrete_registered_truth_kernel_sound`,
`example_i_concrete_registered_truth_conditions_from_kernel_sound`, and
`example_i_concrete_registered_truth_conditions_from_kernel_atomic_sound` for
every exported example. The scaffold then gathers the kernel-induced
truth-condition proofs into `ConcreteRegisteredKernelExampleTruthInstances`,
proves `concrete_registered_kernel_example_truth_instances_exists`, and checks
per-example projections such as
`concrete_registered_kernel_example_i_truth_instance_atomic_sound` back to
`AtomicClosureTruth` through `concrete_registered_truth_conditions_from_kernel`.
The scaffold then gathers those checked example-level proofs into
`ConcreteRegisteredExampleTruthInstances`, proves
`concrete_registered_example_truth_instances_exists`, and checks per-example
projections such as
`concrete_registered_example_i_truth_instance_atomic_sound` back to
`AtomicClosureTruth` through `concrete_registered_truth_conditions`. The
scaffold also gathers the fully registered proof layer into
`RegisteredExampleTruthInstances`, proves
`registered_example_truth_instances_exists`, and checks per-example projections
such as `registered_example_i_truth_instance_atomic_sound` back to
`AtomicClosureTruth`. This still does not claim that the lexical and transition
constructors have been derived from a full semantic model.

Use `python3 scripts/verify_project.py --skip-coq` to skip this optional
boundary check, or `python3 scripts/verify_project.py --require-coq` to fail
when Coq/Rocq is unavailable.
