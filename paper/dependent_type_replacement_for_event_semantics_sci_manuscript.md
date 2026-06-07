# A Dependent-Type Replacement for Event Semantics: Variable Polyadicity, Argument Omission, Thematic Roles, Event Counting, and Causal Resultatives

_Manuscript draft prepared for conceptual and formal development_

## Abstract

Event semantics has provided a powerful architecture for the analysis of natural-language predication: it explains variable polyadicity, supports argument-omission inferences, hosts thematic-role modifiers, and gives uniform treatments of temporal modification, event counting, causation, resultatives, and discourse anaphora. However, its uniform hidden-event variable also conflates several distinct semantic tasks. This article proposes a modular dependent-type alternative in which the functions performed by event variables are decomposed into typed role records, dependent families indexed by natural numbers, sigma types for implicit arguments, interval-indexed temporal operators, state-transition types for causal resultatives, and episodic witnesses introduced only when counting or discourse reference requires them. The resulting framework preserves the empirical coverage of event semantics while avoiding the ontological and compositional overgeneration associated with assigning an event argument to every predicate. We define a formal translation from neo-Davidsonian conjunctions into dependent-type terms, give rules for argument deletion, thematic-role saturation, temporal and aspectual modification, event counting, causation, and result states, and show how the system can be implemented as an automatic translator. The implementation emits both a readable formula and a structured abstract syntax tree with a shallow type-checking layer for sigma witnesses, repetition, temporal operators, and causal transitions. The proposal yields a typed, modular, and computationally tractable semantics in which events are no longer the default glue of predication but one derived representational option among several.

**Keywords:** dependent type theory; event semantics; neo-Davidsonian semantics; argument omission; thematic roles; causation; resultatives; event counting; natural language semantics

## Functional replacement map

| Event-semantic function | Dependent-type replacement | Canonical constructor |
|---|---|---|
| Variable polyadicity | Natural-number-indexed verb families | V : Pi n : Nat. Vk-ADV(n) |
| Thematic roles | Dependent role records | {agent : Human; theme : Food; instrument? : Tool} |
| Argument omission | Sigma and option types | eat(john, none) entails Sigma x : Food. eat(john, some x) |
| Time | Temporal operators | at_T(noon, P); during_T(i, P) |
| Aspect | Process and culmination types | progressive_T(i, Process(V, frame)) |
| Event counting | Episode vectors under count operators | Sigma xs : Vec(EpisodeOf(P), 2). Disjoint(xs) |
| Causal resultatives | State-transition types | Cause(agent, Transition(x, s1, s2)) |
| Event anaphora | Selective discourse referents | Introduce Situation/Episode only when referenced |

## 1. Introduction

Event semantics has become one of the central tools of formal semantics because it gives a simple answer to several otherwise unrelated problems. A sentence such as John buttered the toast slowly in the bathroom at noon can be analyzed by positing an event variable e and conjoining predicates over it: butter(e), Agent(e, John), Theme(e, toast), slowly(e), in(e, bathroom), and at(e, noon). This analysis explains why modifiers can accumulate without changing the lexical arity of the verb. It also gives a natural host for thematic roles, temporal localization, manner modification, instruments, locations, and subsequent event anaphora.

The elegance of this architecture is also its weakness. The event variable is asked to do too many jobs. It counts modifier positions, represents implicit arguments, supports role labeling, anchors time, provides a unit for counting, mediates causation, licenses result states, and sometimes serves as a discourse referent. These functions are not semantically identical. A manner adverb, an implicit object of eat, a result state in break, a repeated occurrence in knock twice, and an anaphoric expression such as that happened again do not require the same kind of object. Treating them all as consequences of one hidden event argument risks turning a useful notation into an overly general ontology.

This article develops a replacement strategy rather than a rejection of the phenomena. The central hypothesis is that the empirical advantages of event semantics can be preserved if the hidden event variable is decomposed into typed components. Variable polyadicity is handled by a dependent family indexed by natural numbers. Thematic-role structure is handled by dependent role records. Argument omission is handled by sigma types and option types. Temporal and aspectual modification is handled by interval-indexed operators. Causal resultatives are handled by state-transition types. Event counting is handled by finite vectors of episode witnesses, introduced only in environments where counting or discourse reference demands them. The result is a modular semantics that keeps the expressive gains of event semantics while giving each phenomenon its own type-theoretic mechanism.

## 2. Background and Motivation

Davidsonian and neo-Davidsonian event semantics introduced an event variable as an additional argument of action predicates. The neo-Davidsonian development separates the core event predicate from thematic roles, allowing the semantic contribution of modifiers and arguments to be expressed as independent conjuncts. This architecture is attractive because it converts apparently variable-arity predicates into a uniform conjunctive form.

The type-theoretic critique begins from the observation that variable polyadicity need not be represented by an event ontology. Luo and Shi argue that the ability of a verb to combine with an arbitrary number of adverbial modifiers can be modeled in an extension of Church's type theory with dependent products and the natural-number type. If ADV is the type of predicate modifiers, a transitive verb can be assigned the dependent type Pi n : N. TV-ADV(n), where TV-ADV(0) = e -> e -> t, TV-ADV(1) = ADV -> e -> e -> t, and TV-ADV(n + 1) adds one more modifier argument. A verb such as butter can therefore take zero, one, two, or more modifiers without positing an event variable.

Yet variable polyadicity is only one reason event semantics has been successful. A credible replacement must also address argument omission, role-based modification, temporal reference, aspect, event counting, causal structure, result states, and event anaphora. The contribution of the present article is to extend the dependent-type strategy from variable polyadicity to this wider empirical domain.

## 3. The Event-Variable Decomposition Thesis

The proposed framework is based on the Event-Variable Decomposition Thesis: the hidden event variable in neo-Davidsonian semantics is not a semantically atomic object but a bundle of representational functions. A replacement system should therefore map each function to a typed construction with a narrower domain of application.

The decomposition is summarized as follows. Modifier accumulation is handled by natural-number-indexed predicate families. Role assignment is handled by dependent records whose fields are typed by selectional and thematic constraints. Argument omission is handled by existential dependent pairs or option types. Temporal location is handled by interval and time-point operators over propositions or processes. Aspect is handled by process and culmination types. Causation and resultatives are handled by state-transition types. Counting is handled by finite vectors or lists of episode witnesses. Discourse anaphora is handled by optional introduction of a referential situation or episode token, not by a universal event parameter.

## 4. Formal Architecture

We assume base types Entity, Truth, Time, Interval, State, and Nat. We also assume a type of predicate modifiers ADV = (Entity -> Truth) -> (Entity -> Truth), generalized where necessary to role-record predicates. For an intransitive predicate family we define IV-ADV(0) = Entity -> Truth and IV-ADV(n + 1) = ADV -> IV-ADV(n). For a transitive predicate family, TV-ADV(0) = Entity -> Entity -> Truth and TV-ADV(n + 1) = ADV -> TV-ADV(n). More generally, Vk-ADV(n) = ADV^n -> Entity^k -> Truth.

A lexical verb is assigned a dependent type of the form V : Pi n : Nat. Vk-ADV(n). This captures variable polyadicity. For example, butter : Pi n : Nat. TV-ADV(n). The term butter(2)(slowly, in(bathroom), John, toast) denotes the proposition that John buttered the toast slowly in the bathroom, with the two modifiers counted by the index 2.

Thematic-role information is not lost. Instead of representing roles as conjuncts Agent(e, x) and Theme(e, y), the system constructs a role record. A simplified transitive frame has the form { agent : AgentiveEntity; theme : Entity; instrument? : Tool; location? : Place; manner : Vec ADV n; time? : Interval }. The role record can be made dependent: the admissible type of theme may depend on the lexical verb, and the admissible type of instrument may depend on both the verb and the theme.

Argument omission is modeled by dependent existential types. For verbs whose lexical semantics licenses implicit objects, we assign a rule such as eat : Human -> Option Food -> Truth, together with an inference from eat(john, none) to Sigma x : Food. eat(john, some x). The inference is lexical and constructional rather than a consequence of an event variable. In contrast, a verb such as arrive does not introduce a missing theme, and a verb such as butter normally requires an overt or contextually recoverable theme.

## 5. Translation from Neo-Davidsonian Formulas

The input language consists of formulas of the form exists e. Verb(e) and R1(e, x1) and ... and Am(e) and T(e, tau), where R predicates are thematic roles, A predicates are adverbial or locative modifiers, and T predicates are temporal relations. The translation proceeds in five stages.

First, identify the core lexical predicate Verb(e). Second, collect role conjuncts into a dependent role record. Third, collect adverbial and locative predicates into a vector of modifiers and compute its length n : Nat. Fourth, translate temporal predicates into proposition-level or process-level temporal operators. Fifth, discharge the event variable and construct the dependent-type term.

For example, exists e. butter(e) and Agent(e, John) and Theme(e, toast) and slowly(e) and in(e, bathroom) and at(e, noon) becomes at_T(noon, butter(2)(slowly, in(bathroom), John, toast)). No event variable remains in the output. The semantic work of the original formula is distributed among the natural-number index, the modifier vector, the ordered role arguments, and the temporal operator.

## 6. Argument Omission and Existential Inference

Argument omission is one of the strongest motivations for event-based analyses. From John ate, speakers commonly infer that John ate something; from John read for an hour, they may infer that there was reading material; from John swept, the object or area may remain contextually underspecified. A uniform event variable can support such inferences by existential closure over missing role predicates, but this uniformity obscures important lexical differences.

The dependent-type replacement uses lexically governed omission schemas. A verb may specify a silent argument policy: obligatory, optional-existential, context-recoverable, incorporated, or absent. The rule for eat is optional-existential because the omitted object introduces a witness of type Food. The rule for arrive marks the theme role as absent rather than omitted. The rule for sweep may introduce either an affected surface or an affected object depending on constructional context. These distinctions are encoded in the verb's frame type rather than inferred from the existence of an event token.

Formally, optional-existential omission is represented by Sigma types. If V : A -> Option B -> Truth and V has the omission policy existential(B), then V(a, none) entails Sigma b : B. V(a, some b). This reproduces the relevant inference without assuming that all missing arguments are recoverable as thematic predicates of an event.

## 7. Thematic Roles without Event Conjuncts

Thematic roles are preserved as typed fields rather than event predicates. This shift has three advantages. First, role compatibility becomes type-checkable. A role record for butter can require an agent capable of intentional action and a theme that is a spreadable or surface-like object. Second, optional roles can be represented directly by option types. Third, cross-role dependencies can be stated explicitly: the type of result state may depend on the theme, and the type of instrument may depend on the action class.

The resulting role structure is not less expressive than neo-Davidsonian role conjunction. It can still represent agents, themes, patients, recipients, instruments, goals, sources, locations, and manners. The difference is that roles are no longer predicates of an event variable; they are fields in a typed frame that composes with the lexical predicate. This makes the role inventory available for automated checking and for construction-specific inference.

## 8. Time, Aspect, and Event Quantity

Temporal modification is treated by operators over propositions, processes, or states. Simple punctual location can be represented as at_T(t, P), and interval inclusion as during_T(i, P). Progressive aspect requires a process-level representation: progressive_T(i, Process(V, frame)) need not entail Culminated(V, frame). Perfect aspect can be represented as a relation between a prior culmination or state transition and a reference interval.

Event quantity is handled separately from ordinary predication. Sentences such as John knocked twice or Mary visited Paris three times require countable occurrences. The framework introduces EpisodeOf(P) only under counting, iteration, or anaphoric pressure. Twice(P) can be modeled as Sigma xs : Vec(EpisodeOf(P), 2). Disjoint(xs), where Disjoint ensures that the counted episodes are not merely duplicate descriptions of the same occurrence. Thus, event tokens appear as derived witnesses in counting constructions, not as universal arguments of every verb.

This selective introduction solves the event-number problem. A single accomplishment may contain many subevents, and different descriptions may count differently. By tying episode witnesses to a predicate P and a granularity condition, the framework avoids assuming that the world comes pre-partitioned into one canonical event inventory.

## 9. Causation and Resultatives

Causation and result states are often treated as event relations: an event of acting causes a result event or result state. The dependent-type alternative represents them as typed transitions. A state transition has the form Transition(object, source_state, target_state). A causal predicate then relates an agent or causing condition to that transition: Cause(causer, Transition(x, s1, s2)).

For John broke the vase, the translation is not exists e. break(e) and Agent(e, John) and Theme(e, vase). Instead, it is Cause(John, Transition(vase, intact, broken)), with lexical constraints specifying the relevant state scale. For John hammered the metal flat, the result phrase flat supplies the target state: Cause(Hammering(John, metal), Transition(metal, not_flat, flat)). This preserves the event-semantic insight that resultatives encode change, but it represents change directly rather than through an event variable.

The same strategy extends to accomplishments, achievements, and caused-motion constructions. The semantic core is a transition in a typed state or location space; the causing activity may be represented as a process if aspectual modification requires it.

## 10. Automation and Computational Implementation

The decomposition yields a practical translation pipeline. A parser or annotation layer identifies the core predicate, role predicates, modifiers, temporal relations, aspectual morphology, quantity expressions, result phrases, and causal constructions. The compiler then emits a dependent-type term using a small inventory of constructors: Pi-indexed verb families, role records, Sigma witnesses, option types, temporal operators, process constructors, transition constructors, and episode vectors.

Unlike a purely event-based compiler, the proposed system can preserve typing information during translation. It can detect an ill-typed instrument, distinguish absent from omitted arguments, prevent accidental event counting where no count operator is present, and encode result states as typed targets. The output is therefore suitable not only for semantic representation but also for automated reasoning, theorem proving, and controlled natural-language interfaces.

## 11. Prototype Implementation and Verification

The current prototype implements the translation strategy as a small compiler from a JSON representation of neo-Davidsonian conjunctions into two synchronized outputs. The first output is a compact formula string intended for inspection, for example at_T(noon, butter(2)(slowly, in(bathroom), John, toast)). The second output is a structured abstract syntax tree (AST) intended for type checking and later export to a proof assistant. This division is important because a string can be persuasive while still hiding malformed structure; the AST makes the translation auditable.

The AST currently contains six term forms. An application term represents a dependent verb-family application and stores the verb, modifier vector, natural-number modifier count, and ordered arguments. A sigma term represents a lexically licensed implicit argument, as in Sigma x_theme : Food. eat(0)(John, x_theme). A repeat term represents event counting, as in repeat(2, knock(0)(John)). A time term represents temporal modification as a proposition-level operator. Transition and cause terms represent causal-resultative structure, requiring the result component to be a typed transition rather than an arbitrary proposition.

The implementation also contains a shallow type checker. It verifies that the modifier count in an application agrees with the number of modifiers, that sigma bodies have propositional type, that repetition counts are positive natural numbers, that time operators are recognized, that transitions have the type Transition, and that the effect of Cause is a transition. This type checker is intentionally modest: it does not yet prove the full semantic validity of the analysis. Its role is to prevent malformed intermediate representations from being silently rendered as well-formed-looking formulas.

Well-typed ASTs can now be exported to a shallow proof-assistant embedding. The Lean-style exporter renders a sigma witness as Exists fun x_theme : Food => (eat 0 John x_theme), while the Coq-style exporter renders the same structure as exists x_theme : Food, (eat 0 John x_theme). Non-binding constructors use a shared prefix notation, for example repeat 2 (knock 0 John) and Cause John (Transition vase unknown_state broken). Export is deliberately refused for ill-typed ASTs, so the proof-assistant boundary is guarded by the same structural checks used by the translator.

The exporter also generates complete interface scaffolds rather than isolated expressions. The generated Lean and Coq files introduce shallow constants for Entity, Food, PropT, TransitionT, the example individuals, the predicate constructors, repetition, temporal operators, Transition, and Cause. They then define one example term for each checked translation and include proof-assistant-style inspection commands (#check in Lean style and Check in Coq style). This stage is still a shallow embedding, but it changes the engineering status of the project: the output is now a stable file-level artifact that can be refined into a genuine proof-assistant development. Coq is not used as the implementation language of the translator. Rather, Rocq/Coq is used as an optional boundary validator: when it is available, the repository-level verification command compiles the generated Coq scaffold with coqc to confirm that the exported terms are acceptable to an external dependent-type checker. In the current environment this check succeeds under the Rocq Prover, version 9.0.1.

The scaffold now separates entity-denoting arguments from Luo-Shi style predicate modifiers. In a sentence such as John buttered the toast in the bathroom with a knife, the individual arguments John and toast are exported at type Entity, while in_bathroom and with_knife are exported at type Adv, with Adv represented in the shallow Coq interface as (Entity -> PropT) -> Entity -> PropT. The generated verb type is therefore butter : nat -> Adv -> Adv -> Entity -> Entity -> PropT rather than a spurious all-entity type. This correction is conceptually important: an automatic translator is not trustworthy if it merely produces Coq-checkable declarations after erasing the semantic distinction between modifiers and individuals.

The implementation now includes a first Parsons-style event-talk case, after the singing of the Marseillaise, John saluted the flag. The generated analysis preserves an event-semantics reference formula for comparison, but the checked replacement follows the Luo-Shi timed strategy: it introduces Time, before : Time -> Time -> Prop, sing : Entity -> Time -> Prop, and salute : Entity -> Entity -> Time -> Prop, then defines the translation as an existential formula over t_sing and t_salute. The generated Coq scaffold deliberately contains no Event declaration for this case. This test is narrow, but it is methodologically important because it shows how a construction apparently motivating event-to-event ordering can be refactored into typed temporal dependence and externally checked without a hidden event variable.

The verified test suite covers positive translation cases for variable polyadicity with time, argument omission, event counting, causal resultatives, quantifier-scope ambiguity, typed modifiers, fallback simple sentences, and the timed Parsons case above. The negative cases reject an application whose adverb count does not match its modifier vector, a Cause term whose effect is not a Transition, and an attempted proof-assistant export of an ill-typed AST. The module-generation case checks that the emitted Lean and Coq scaffolds contain both the shared declarations and the expected example definitions. A separate formalization-consistency checker regenerates the scaffold files and verifies the expected declarations, normalized names, example definitions, and inspection commands. The repository also provides a single deterministic verification entry point that runs the unit tests, Python compilation checks, formalization-consistency check, and a controllable Coq scaffold compilation check: users may skip it when only the translator is being tested, or require it when proof-assistant compatibility is part of the acceptance criterion. The same command is wired into a GitHub Actions workflow. These tests turn the theoretical decomposition into a sequence of small, reproducible implementation stages.

The same architecture can be exposed as an interactive web pipeline. A user-facing interface would accept a natural-language sentence, display the event-semantics analysis, translate it into the dependent-type AST and readable formula, generate a Coq scaffold, and report whether the internal type check and optional Coq/Rocq boundary check succeed. The present implementation contains a small rule-based backend slice for controlled sentences such as John ate, John knocked twice, and John broke the vase. It now also includes a conservative fallback parser for simple unlisted sentences; for example, a cat sits on a mat is analyzed as sit(e), Agent(e, cat), and on(e, mat), then translated as sit(1)(on(mat), cat). Quantifier-scope cases are handled separately rather than forced into this fallback: some boy loves some girl is represented by two checked readings, one with the boy existential taking wider scope and one with the girl existential taking wider scope, with boy and girl assigned predicate types Entity -> Prop rather than being treated as event predicates or entity constants. The local web demo presents these stages as separate panels over the same verified backend. This slice is not a general natural-language parser, but it establishes the desired diagnostic structure: parsing failures, AST type failures, and proof-assistant boundary failures are reported as distinct stages rather than collapsed into a single error. The Coq/Rocq check certifies the well-typedness of the exported formal scaffold; it does not by itself prove that a natural-language sentence has no additional readings or that the parser has selected the only correct analysis.

## 12. Discussion

The framework does not claim that natural language never refers to events. Rather, it denies that every predicate must introduce a hidden event argument. Event-denoting nominals, explicit event anaphora, counting constructions, and discourse reference may still introduce episode or situation objects. The difference is architectural: event-like objects are licensed by specific constructions, not by the lexical semantics of every verb.

This modular view also clarifies disagreements about event ontology. Some empirical effects attributed to events are actually effects of modifier polyadicity, typed role structure, existential omission, temporal anchoring, aspectual process structure, or causal transition. Once these are separated, the residual need for event objects becomes narrower and more empirically testable.

## 13. Conclusion

A comprehensive replacement for event semantics must do more than solve variable polyadicity. It must also account for argument omission, thematic roles, time, aspect, event quantity, causation, and resultatives. This article has proposed a dependent-type architecture that distributes these functions across typed constructions: natural-number-indexed verb families, dependent role records, sigma and option types, temporal and aspectual operators, state-transition types, and selectively introduced episode witnesses. The resulting semantics preserves the main explanatory benefits of event semantics while avoiding a universal hidden event argument. It is also well suited to automation because each representational function is associated with a distinct typed constructor and a corresponding translation rule. The prototype strengthens this claim by showing that the target representation can be emitted as a structured AST, checked for basic type well-formedness, exported as Lean- and Coq-style formalization scaffolds, and compiled as a Coq scaffold when a local Coq/Rocq toolchain is present.

## References

- Davidson, D. (1967). The logical form of action sentences. In N. Rescher (Ed.), The Logic of Decision and Action. University of Pittsburgh Press.
- Parsons, T. (1990). Events in the Semantics of English: A Study in Subatomic Semantics. MIT Press.
- Luo, Z., & Shi, B. (2017). Variable polyadicity without events: A type-theoretic analysis of event semantics. Mathematical Structures in Computer Science, 27(6), 919-935.
- Kamp, H., & Reyle, U. (1993). From Discourse to Logic. Kluwer Academic Publishers.
- Pustejovsky, J. (1991). The syntax of event structure. Cognition, 41(1-3), 47-81.
- Krifka, M. (1998). The origins of telicity. In S. Rothstein (Ed.), Events and Grammar. Kluwer Academic Publishers.
- Dowty, D. (1991). Thematic proto-roles and argument selection. Language, 67(3), 547-619.
- Ranta, A. (1994). Type-Theoretical Grammar. Oxford University Press.
- Martin-Lof, P. (1984). Intuitionistic Type Theory. Bibliopolis.
- Cooper, R. (2012). Type theory and semantics in flux. In R. Kempson et al. (Eds.), Handbook of the Philosophy of Science: Philosophy of Linguistics. Elsevier.
