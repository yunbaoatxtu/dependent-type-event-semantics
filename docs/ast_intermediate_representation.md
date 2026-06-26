# AST Intermediate Representation

The translator emits two views of the same result:

- `translation`: a compact human-readable rendering;
- `ast`: a structured intermediate representation intended for later type
  checking, proof-assistant export, or semantic validation.

## Term Kinds

### `application`

Represents a dependent verb-family application.

```json
{
  "kind": "application",
  "function": "butter",
  "adverb_count": 2,
  "modifiers": ["slowly", "in(bathroom)"],
  "modifier_vector": {
    "kind": "modifier_vector",
    "length": 2,
    "items": [
      {"modifier": "slowly", "tail_length": 1},
      {"modifier": "in(bathroom)", "tail_length": 0}
    ]
  },
  "modifier_roles": {
    "kind": "modifier_roles",
    "roles": [
      {
        "modifier": "slowly",
        "type": "Adv",
        "semantic_role": "Manner",
        "source": "modifier",
        "surface_lexicon": {
          "surface_modifier": "slowly",
          "normalized_modifier": "slowly",
          "type": "Adv",
          "semantic_role": "Manner",
          "source": "translator/surface_lexicon.py"
        }
      },
      {
        "modifier": "in(bathroom)",
        "type": "Adv",
        "semantic_role": "Location",
        "source": "modifier",
        "surface_lexicon": {
          "surface_modifier": "in(bathroom)",
          "normalized_modifier": "in_bathroom",
          "type": "Adv",
          "semantic_role": "Location",
          "source": "translator/surface_lexicon.py"
        }
      }
    ]
  },
  "arguments": ["John", "toast"],
  "role_frame": {
    "kind": "role_frame",
    "roles": [
      {"role": "Agent", "value": "John", "type": "Entity", "source": "explicit"},
      {"role": "Theme", "value": "toast", "type": "Entity", "source": "explicit"}
    ]
  }
}
```

Renders as:

```text
butter(2)(slowly, in(bathroom), John, toast)
```

### `sigma`

Represents a lexically licensed omitted argument.

```json
{
  "kind": "sigma",
  "witness": "x_theme",
  "type": "Food",
  "body": { "...": "..." }
}
```

Renders as:

```text
Sigma x_theme : Food. ...
```

### `repeat`

Represents event-counting or iteration.

```json
{
  "kind": "repeat",
  "count": "2",
  "body": { "...": "..." }
}
```

Renders as:

```text
repeat(2, ...)
```

### `time`

Represents temporal modification as a proposition-level operator.

```json
{
  "kind": "time",
  "operator": "at",
  "arguments": ["noon"],
  "body": { "...": "..." }
}
```

Renders as:

```text
at_T(noon, ...)
```

### `not`

Represents proposition-level negation. It wraps an already checked body instead
of folding `not` into a predicate, subject, or object name.

```json
{
  "kind": "not",
  "body": { "...": "..." }
}
```

Renders as:

```text
not_T(...)
```

### `cause` and `transition`

Represent causal-resultative structure.

```json
{
  "kind": "cause",
  "causer": "John",
  "effect": {
    "kind": "transition",
    "theme": "vase",
    "state_scale": "integrity_scale",
    "source_state": "intact",
    "target_state": "broken"
  },
  "activity": {
    "kind": "application",
    "function": "break",
    "adverb_count": 0,
    "modifiers": [],
    "modifier_vector": {
      "kind": "modifier_vector",
      "length": 0,
      "items": []
    },
    "arguments": ["John", "vase"]
  }
}
```

Renders as:

```text
Cause(John, Transition(vase, integrity_scale, intact, broken))
```

The optional `activity` field preserves the original verbal description even
when the visible rendering focuses on the causal transition. This is useful for
later proof assistant export, where the causing process and the result
transition may need separate types. The shallow exporter now gives the
transition theme type `Entity`, the scale type `StateScale`, and the
source/target states type `State`, so `Transition` is exported as
`Entity -> StateScale -> State -> State -> TransitionT`.

The translator infers the `state_scale` from a small lexical map. For example,
`broken` and `intact` map to `integrity_scale`, `flat`, `not_flat`, `round`, and
`straight` map to `shape_scale`, `open` and `closed` map to `access_scale`,
`solid`, `liquid`, `melted`, and `frozen` map to `phase_scale`, `dry` and `wet`
map to `moisture_scale`, `clean` and `dirty` map to `cleanliness_scale`,
`empty` and `full` map to `content_scale`, and `red` maps to `color_scale`. The
fallback natural-language parser uses the same map to recognize simple result
phrases such as `John hammered the metal flat` and `Mary painted the door red`:
the object is kept as an `Entity`, while the final result adjective becomes the
transition target `State`.
For target states with a clear opposite or pre-state, the resultative compiler
also supplies the source state: `broken` is reached from `intact`, `flat` from
`not_flat`, `open` from `closed`, `wet` from `dry`, and so on. States without a
safe lexical pre-state, such as the color state `red`, still export `_` as
`unknown_state`.
Their `source_policy` values are also used by the web diagnostics layer:
`lexical_prestate` is fully specified, while `unknown_source_allowed`,
`derived_scale_no_known_prestate`, and `source_state_only` generate non-fatal
warnings.

The same information is exposed as `result_state_lexicon` in pipeline output:

```json
[
  {
    "state": "flat",
    "scale": "shape_scale",
    "default_source_state": "not_flat",
    "source_policy": "lexical_prestate"
  }
]
```

### `timed_after`

Represents the Luo-Shi-style replacement for Parsons' temporal event-ordering
example `after the singing of the Marseillaise, John saluted the flag`. The AST
binds two times and checks the lexical predicates and temporal relation:

```json
{
  "kind": "timed_after",
  "binders": [
    {"variable": "t_sing", "type": "Time"},
    {"variable": "t_salute", "type": "Time"}
  ],
  "first": {
    "predicate": "sing",
    "predicate_type": "Entity -> Time -> Prop",
    "theme": {
      "name": "Marseillaise",
      "type": "Entity"
    },
    "time": "t_sing"
  },
  "second": {
    "predicate": "salute",
    "predicate_type": "Entity -> Entity -> Time -> Prop",
    "agent": {
      "name": "John",
      "type": "Entity"
    },
    "theme": {
      "name": "flag",
      "type": "Entity"
    },
    "time": "t_salute"
  },
  "relation": {
    "predicate": "before",
    "predicate_type": "Time -> Time -> Prop",
    "arguments": ["t_sing", "t_salute"]
  }
}
```

This captures temporal dependence without introducing an event-to-event
ordering predicate. The pipeline also emits a top-level
`semantic_readings` entry named `timed_after_singing_salute`; its
`semantic_readings_check` record confirms that the reading type-checks and
that the referenced Coq definition is exported.

### `perception_nominalization`

Represents the Luo-Shi-style replacement for perception complements such as
`Mary saw John leave`. The embedded clause is first checked as a proposition,
then mapped into an entity-denoting percept by `E : Prop -> Entity`:

```json
{
  "kind": "perception_nominalization",
  "perception": {
    "predicate": "see",
    "predicate_type": "Entity -> Entity -> Prop",
    "experiencer": {
      "name": "Mary",
      "type": "Entity"
    },
    "object": {
      "kind": "nominalized_proposition",
      "nominalizer": "E",
      "nominalizer_type": "Prop -> Entity",
      "proposition": {
        "predicate": "leave",
        "predicate_type": "Entity -> Prop",
        "subject": {
          "name": "John",
          "type": "Entity"
        }
      }
    }
  }
}
```

This prevents the construction from being represented as a hidden event object
while still giving the perception verb an entity-denoting object.

The nominalized proposition can itself be a checked subject coordination. For
`Mary saw John and Bill leave`, the object of perception is not a fresh event
entity or a flat `john_and_bill` constant; it is `E` applied to the coordinated
proposition:

```json
{
  "kind": "perception_nominalization",
  "perception": {
    "predicate": "see",
    "predicate_type": "Entity -> Entity -> Prop",
    "experiencer": {
      "name": "Mary",
      "type": "Entity"
    },
    "object": {
      "kind": "nominalized_proposition",
      "nominalizer": "E",
      "nominalizer_type": "Prop -> Entity",
      "proposition": {
        "kind": "subject_coordination",
        "subjects": [
          {"name": "John", "type": "Entity"},
          {"name": "Bill", "type": "Entity"}
        ],
        "predicate": {
          "surface": "leave",
          "name": "leave",
          "predicate_type": "Entity -> Prop"
        },
        "modifiers": [],
        "connective": "and_T",
        "connective_type": "Prop -> Prop -> Prop",
        "time_modifiers": []
      }
    }
  }
}
```

This renders as:

```text
see(Mary, E(and_T(leave(John), leave(Bill))))
```

The embedded proposition can also coordinate two complete embedded clauses. For
`Mary saw John leave and Bill wave`, the nominalizer applies to a
`proposition_coordination` object rather than to a subject-coordination object:

```json
{
  "kind": "perception_nominalization",
  "perception": {
    "predicate": "see",
    "predicate_type": "Entity -> Entity -> Prop",
    "experiencer": {
      "name": "Mary",
      "type": "Entity"
    },
    "object": {
      "kind": "nominalized_proposition",
      "nominalizer": "E",
      "nominalizer_type": "Prop -> Entity",
      "proposition": {
        "kind": "proposition_coordination",
        "clauses": [
          {
            "predicate": "leave",
            "predicate_type": "Entity -> Prop",
            "subject": {"name": "John", "type": "Entity"}
          },
          {
            "predicate": "wave",
            "predicate_type": "Entity -> Prop",
            "subject": {"name": "Bill", "type": "Entity"}
          }
        ],
        "connective": "and_T",
        "connective_type": "Prop -> Prop -> Prop"
      }
    }
  }
}
```

This renders as:

```text
see(Mary, E(and_T(leave(John), wave(Bill))))
```

The same nominalization layer can keep a temporal dependency inside the
embedded proposition. For `Mary saw John leave after Bill waved`, the perceived
object is not an event ordered after another event. It is `E` applied to a
time-indexed proposition whose reference time precedes the main time:

```json
{
  "kind": "perception_nominalization",
  "perception": {
    "predicate": "see",
    "predicate_type": "Entity -> Entity -> Prop",
    "experiencer": {
      "name": "Mary",
      "type": "Entity"
    },
    "object": {
      "kind": "nominalized_proposition",
      "nominalizer": "E",
      "nominalizer_type": "Prop -> Entity",
      "proposition": {
        "kind": "temporal_relation",
        "relation_surface": "after",
        "binders": [
          {"variable": "t_main", "type": "Time"},
          {"variable": "t_reference", "type": "Time"}
        ],
        "main": {
          "predicate": "leave",
          "predicate_type": "Entity -> Time -> Prop",
          "subject": {"name": "John", "type": "Entity"},
          "time": "t_main"
        },
        "reference": {
          "predicate": "wave",
          "predicate_type": "Entity -> Time -> Prop",
          "subject": {"name": "Bill", "type": "Entity"},
          "time": "t_reference"
        },
        "relation": {
          "predicate": "before",
          "predicate_type": "Time -> Time -> Prop",
          "arguments": ["t_reference", "t_main"]
        }
      }
    }
  }
}
```

This renders as:

```text
see(Mary, E(exists t_main t_reference : Time. leave(John, t_main) and wave(Bill, t_reference) and before(t_reference, t_main)))
```

The reference side of a temporal complement may also be a checked timed
proposition coordination. For `Mary saw John leave after Bill waved and Sue
smiled`, the reference proposition contains two timed clauses and therefore two
ordering constraints:

```json
{
  "kind": "perception_nominalization",
  "perception": {
    "predicate": "see",
    "predicate_type": "Entity -> Entity -> Prop",
    "experiencer": {
      "name": "Mary",
      "type": "Entity"
    },
    "object": {
      "kind": "nominalized_proposition",
      "nominalizer": "E",
      "nominalizer_type": "Prop -> Entity",
      "proposition": {
        "kind": "temporal_relation",
        "relation_surface": "after",
        "binders": [
          {"variable": "t_main", "type": "Time"},
          {"variable": "t_reference_1", "type": "Time"},
          {"variable": "t_reference_2", "type": "Time"}
        ],
        "main": {
          "predicate": "leave",
          "predicate_type": "Entity -> Time -> Prop",
          "subject": {"name": "John", "type": "Entity"},
          "time": "t_main"
        },
        "reference": {
          "kind": "timed_proposition_coordination",
          "clauses": [
            {
              "predicate": "wave",
              "predicate_type": "Entity -> Time -> Prop",
              "subject": {"name": "Bill", "type": "Entity"},
              "time": "t_reference_1"
            },
            {
              "predicate": "smile",
              "predicate_type": "Entity -> Time -> Prop",
              "subject": {"name": "Sue", "type": "Entity"},
              "time": "t_reference_2"
            }
          ],
          "connective": "and_T",
          "connective_type": "Prop -> Prop -> Prop"
        },
        "relations": [
          {
            "predicate": "before",
            "predicate_type": "Time -> Time -> Prop",
            "arguments": ["t_reference_1", "t_main"]
          },
          {
            "predicate": "before",
            "predicate_type": "Time -> Time -> Prop",
            "arguments": ["t_reference_2", "t_main"]
          }
        ]
      }
    }
  }
}
```

This renders as:

```text
see(Mary, E(exists t_main t_reference_1 t_reference_2 : Time. leave(John, t_main) and and_T(wave(Bill, t_reference_1), smile(Sue, t_reference_2)) and before(t_reference_1, t_main) and before(t_reference_2, t_main)))
```

The main side can also be a checked timed proposition coordination. For `Mary
saw John leave and Sue smile after Bill waved`, the main proposition contains
two timed clauses, so the AST binds `t_main_1`, `t_main_2`, and `t_reference`
and stores one `before` relation for each main/reference time pair:

```text
see(Mary, E(exists t_main_1 t_main_2 t_reference : Time. and_T(leave(John, t_main_1), smile(Sue, t_main_2)) and wave(Bill, t_reference) and before(t_reference, t_main_1) and before(t_reference, t_main_2)))
```

If both sides are coordinated, the `relations` list is the full Cartesian set
of ordered main/reference time pairs. For `Mary saw John leave and Sue smile
after Bill waved and Ann laughed`, the checked translation contains four
ordering constraints:

```text
before(t_reference_1, t_main_1), before(t_reference_2, t_main_1), before(t_reference_1, t_main_2), before(t_reference_2, t_main_2)
```

Timed proposition coordination may contain more than two clauses. The AST still
stores a single `clauses` list and a binary connective type
`Prop -> Prop -> Prop`; rendering folds the list as a right-associated binary
term. For example, `Mary saw John leave and Sue smile and Ann laugh after Bill
waved` renders the main side as:

```text
and_T(leave(John, t_main_1), and_T(smile(Sue, t_main_2), laugh(Ann, t_main_3)))
```

### `forall_time`

Represents the Luo-Shi-style replacement for Parsons' event-inclusion example
`In every burning, oxygen is consumed`. Instead of introducing events and
`IN(e, e')`, the AST binds an entity and a time, then checks two time-indexed
predicates:

```json
{
  "kind": "forall_time",
  "binders": [
    {"variable": "x", "type": "Entity"},
    {"variable": "t", "type": "Time"}
  ],
  "antecedent": {
    "predicate": "burn",
    "predicate_type": "Entity -> Time -> Prop",
    "arguments": ["x", "t"]
  },
  "consequent": {
    "predicate": "consume",
    "predicate_type": "Entity -> Time -> Prop",
    "arguments": ["oxygen", "t"],
    "theme": {
      "name": "oxygen",
      "type": "Entity"
    }
  }
}
```

The structural check requires the antecedent and consequent to share the bound
time variable `t`. The corresponding top-level `semantic_readings` entry is
named `universal_timed_burning` and points to the exported
`every_burning_consumes_oxygen` definition.

### `lexical_state_change`

Represents lexical change-of-state alternations such as `the door opened`,
`John opened the door`, `John opened the door with a key`, `the clothes dried`,
`the water froze`, `Mary cleaned the room`, `the tank emptied`, and `John
filled the glass`. It also supports asymmetric life-scale registrations such as
`John died` and `Mary killed the plant with poison`. The construction uses the
state lexicon to build a transition directly, without treating the changing
object as an Agent:

```json
{
  "kind": "lexical_state_change",
  "verb": "open",
  "surface_lexicon": {
    "surface_verb": "opened",
    "lemma": "open",
    "source": "translator/surface_lexicon.py"
  },
  "frame": "inchoative",
  "transition": {
    "kind": "transition",
    "theme": {
      "name": "door",
      "type": "Entity"
    },
    "state_scale": "access_scale",
    "source_state": "closed",
    "target_state": {
      "name": "open",
      "type": "State"
    }
  }
}
```

The inchoative form renders as
`Change(Transition(door, access_scale, closed, open))`. If a causer is present,
the AST records `frame: "causative"`, adds `causer : Entity`, and renders
`Cause(causer, Transition(...))`. If a `with` phrase is present, the AST records
`frame: "instrumental"`, adds an Instrument entity, and renders
`CauseWithInstrument(causer, instrument, Transition(...))`. The structural
check requires `state_scale` and `source_state` to match the state lexicon, so
`the clothes dried` receives `moisture_scale` with source `wet`, while `the
water froze` receives `phase_scale` with source `liquid`.

The surrounding pipeline result also includes the lexical registration record
that selected the transition. These records live in
`translator/state_change_lexicon.py`, so the lexical inventory is maintained
outside the natural-language parsing rule:

```json
{
  "state_change_verb_entry": {
    "verb": "dry",
    "target_state": "dry",
    "allow_inchoative": true,
    "allow_causative": true,
    "allow_instrument": true
  }
}
```

The AST also carries a `surface_lexicon` audit object, distinct from the
state-change registration, so the checker can verify that a surface form such
as `died` or `froze` was lemmatized to the registered verb before the transition
was selected. The AST checker uses the registration as an additional guard: a
malformed AST
whose verb is `open` but whose target state is `closed` is rejected even though
both states are valid members of the access scale, because the registered verb
and target state disagree (`registered_verb_target_state_mismatch`).
The same checker requires `frame` to agree with the presence or absence of
`causer` and `instrument`, and it enforces lexical frame licensing. Thus
`die` licenses `Change(Transition(john, life_scale, alive, dead))` but rejects a
causative `die` frame, while `kill` licenses
`CauseWithInstrument(mary, poison, Transition(plant, life_scale, alive, dead))`
but rejects an inchoative `kill` frame.

### `stative_result_state`

Represents copular result-state clauses such as `the vase is broken`. The
construction uses the result-state lexicon and asserts that an entity holds a
state on the relevant scale. It does not introduce an event variable or an
omitted Agent:

```json
{
  "kind": "stative_result_state",
  "subject": {
    "name": "vase",
    "type": "Entity"
  },
  "state": {
    "name": "broken",
    "type": "State"
  },
  "state_scale": "integrity_scale",
  "predicate": "holds_state",
  "predicate_type": "Entity -> StateScale -> State -> Prop",
  "auxiliary": "is"
}
```

The structural check requires the state to occur in the state lexicon, requires
`state_scale` to match that lexical entry, and requires the auxiliary to be one
of `is`, `was`, `are`, or `were`. A by-phrase keeps the sentence in the
agentive passive rule instead.

### `passive_argument_omission`

Represents passive clauses with either an explicit by-phrase or an omitted
agent. The construction does not export event-role predicates. Instead, the
surface subject is stored as the logical Patient, while the Agent is either a
named entity from the by-phrase or an existentially bound entity:

```json
{
  "kind": "passive_argument_omission",
  "predicate": "butter",
  "predicate_type": "Entity -> Entity -> Prop",
  "auxiliary": "was",
  "surface_lexicon": {
    "participle": "buttered",
    "lemma": "butter",
    "source": "translator/surface_lexicon.py"
  },
  "argument_order": ["Agent", "Patient"],
  "time_modifiers": [
    {"operator": "at", "argument": "yesterday"}
  ],
  "patient": {
    "name": "toast",
    "type": "Entity",
    "surface_role": "subject"
  },
  "agent": {
    "variable": "x_agent",
    "type": "Entity",
    "source": "omitted_existential"
  }
}
```

The structural check requires the predicate to keep the order
`Entity -> Entity -> Prop`, with the Agent before the Patient, and it requires
the auxiliary to be one of `is`, `was`, `are`, or `were`. It also checks
`time_modifiers`, when present, as proposition-level `at_T` or `during_T`
operators. Thus `the toast was buttered by John yesterday` renders as
`at_T(yesterday, butter(john, toast))`, and the time expression is not folded
into the by-phrase agent name. The checker also validates the `surface_lexicon`
audit object: the participle must be a licensed passive participle, `lemma`
must match both the predicate and the lemmatized participle, and `source` must
identify `translator/surface_lexicon.py`. If the by-phrase is present,
`agent.source` is `by_phrase` and `agent.name` stores the overt individual;
otherwise `agent.source` is `omitted_existential` and the exported Coq scaffold
binds `x_agent : Entity`. Both branches are normalized as single-reading
outputs: `by_phrase_agent` for the overt agent and `omitted_existential_agent`
for the existentially bound agent.

### `scope_ambiguity`

Represents a construction-specific ambiguity that is not forced through the
simple event-formula fallback parser. For `some boy loves some girl`, the AST
keeps two readings with explicit quantifier order and predicate types:

```json
{
  "kind": "scope_ambiguity",
  "quantifier": "some",
  "readings": [
    {
      "name": "some_boy_wide_scope",
      "quantifier": "some",
      "scope_order": [
        {
          "role": "subject",
          "variable": "x_boy",
          "predicate": "boy",
          "predicate_type": "Entity -> Prop"
        },
        {
          "role": "object",
          "variable": "x_girl",
          "predicate": "girl",
          "predicate_type": "Entity -> Prop"
        }
      ],
      "relation": {
        "predicate": "love",
        "predicate_type": "Entity -> Entity -> Prop",
        "arguments": ["x_boy", "x_girl"]
      }
    }
  ]
}
```

The paired object-wide reading has the same relation arguments but reverses the
`scope_order`. This makes the ambiguity auditable before the Coq formula is
rendered. The API result also exposes the two formulas through top-level
`semantic_readings`, using the same `name`, `scope`, rendered dependent-type
translation, Coq definition name, and type-check metadata shape used for other
ambiguity-producing constructions. `semantic_readings_check` then audits the
normalized list for duplicate names, missing formulas, failed per-reading
checks, and Coq definition names that are not actually exported.
At the registered-rule boundary, successful single-reading constructions that
do not provide a specialized reading list are normalized in the same format:
the executor extracts the unique exported `Definition ... : Prop/PropT`, emits
`{rule_id}_single_reading`, and records the same audit in
`semantic_readings_check`.

### `subject_coordination`

Represents coordinated `Entity` subjects sharing one intransitive predicate,
such as `John and Mary walked`, `Both John and Mary walked`, or `John or Mary
walked`. The construction records the two subjects, the shared lemmatized
predicate, and the Boolean connective:

```json
{
  "kind": "subject_coordination",
  "subjects": [
    {
      "name": "john",
      "type": "Entity"
    },
    {
      "name": "mary",
      "type": "Entity"
    }
  ],
  "predicate": {
    "surface": "walked",
    "name": "walk",
    "predicate_type": "Entity -> Prop"
  },
  "modifiers": [],
  "connective": "and_T",
  "connective_type": "Prop -> Prop -> Prop",
  "time_modifiers": []
}
```

Renders as:

```text
and_T(walk(john), walk(mary))
```

The sentence-initial marker in `Both John and Mary walked` is not absorbed into
the subject name; it licenses the same `and_T` reading. Disjunction uses
`"connective": "or_T"`, so `John or Mary walked` renders as
`or_T(walk(john), walk(mary))`.

Shared Adv and time material use the same modifier and time fields as predicate
coordination. For example, `John and Mary walked in the park yesterday` renders
as `at_T(yesterday, and_T(walk(1)(in(park), john), walk(1)(in(park), mary)))`.

This construction is deliberately limited to intransitive predicates. Transitive
shared-object cases are represented by `transitive_subject_coordination` instead.

### `transitive_subject_coordination`

Represents coordinated `Entity` subjects sharing one transitive predicate and
one typed object, such as `John and Mary ate bread` or `John or Mary drank
water`:

```json
{
  "kind": "transitive_subject_coordination",
  "subjects": [
    {
      "name": "john",
      "type": "Entity"
    },
    {
      "name": "mary",
      "type": "Entity"
    }
  ],
  "predicate": {
    "surface": "ate",
    "name": "eat",
    "predicate_type": "Entity -> Food -> Prop"
  },
  "object": {
    "name": "bread",
    "type": "Food"
  },
  "modifiers": [],
  "connective": "and_T",
  "connective_type": "Prop -> Prop -> Prop",
  "time_modifiers": []
}
```

Renders as:

```text
and_T(eat(john, bread), eat(mary, bread))
```

The object type is inferred through the same lexical argument table used by
other transitive rules, so `bread` is `Food` for `eat`, while `water` is
`Drinkable` for `drink`. Shared Adv and time material remain separate from both
subjects and the object: `John and Mary ate bread in the park yesterday` renders
as `at_T(yesterday, and_T(eat(1)(in(park), john, bread), eat(1)(in(park), mary,
bread)))`.

### `object_coordination`

Represents one subject and one transitive predicate distributed over two typed
objects, such as `Mary visited Paris and London`, `Mary visited Paris or
London`, or `Mary visited both Paris and London`:

```json
{
  "kind": "object_coordination",
  "subject": {
    "name": "mary",
    "type": "Entity"
  },
  "predicate": {
    "surface": "visited",
    "name": "visit",
    "predicate_type": "Entity -> Entity -> Prop"
  },
  "objects": [
    {
      "name": "paris",
      "type": "Entity"
    },
    {
      "name": "london",
      "type": "Entity"
    }
  ],
  "modifiers": [],
  "connective": "and_T",
  "connective_type": "Prop -> Prop -> Prop",
  "time_modifiers": []
}
```

Renders as:

```text
and_T(visit(mary, paris), visit(mary, london))
```

The object-level marker `both` is stripped only when it marks an `and`
coordination before the first object, so `Mary visited both Paris and London`
does not construct `both_paris`. Shared Adv and time material scope over the
distributed object formula: `Mary visited Paris and London in the park yesterday`
renders as `at_T(yesterday, and_T(visit(1)(in(park), mary, paris),
visit(1)(in(park), mary, london)))`.

### `predicate_coordination`

Represents same-subject intransitive predicate coordination such as `John walked
and talked` or `John walked or talked`. The construction records both surface
forms, their lemmatized `Entity -> Prop` predicates, and a typed Boolean
connective. It does not introduce a Theme such as `and_talked` or `or_talked`:

```json
{
  "kind": "predicate_coordination",
  "subject": {
    "name": "john",
    "type": "Entity"
  },
  "modifiers": [],
  "predicates": [
    {
      "surface": "walked",
      "name": "walk",
      "predicate_type": "Entity -> Prop"
    },
    {
      "surface": "talked",
      "name": "talk",
      "predicate_type": "Entity -> Prop"
    }
  ],
  "connective": "and_T",
  "connective_type": "Prop -> Prop -> Prop",
  "time_modifiers": []
}
```

Renders as:

```text
and_T(walk(john), talk(john))
```

The same AST shape licenses disjunction by setting `"connective": "or_T"`:
`John walked or talked` renders as `or_T(walk(john), talk(john))`.
The marked surface form `John either walked or talked` uses the same AST and
keeps `john` as the subject rather than constructing `john_either`.
The paired marker in `John both walked and talked` is treated similarly, yielding
the same subject and the `and_T` connective. A sentence-initial `both` before a
coordinated subject is not stripped by this same-subject predicate rule.

If a fronted or trailing time expression is present, the time operator scopes
over the whole conjunction rather than being folded into the subject.

Fronted or trailing non-temporal modifier material is instead represented as
shared `Adv` material. For example, both `In the park John walked and talked`
and `John walked and talked in the park` keep `john` as the subject and store
the prepositional phrase as:

```json
"modifiers": [
  {
    "expression": "in(park)",
    "name": "in_park",
    "type": "Adv",
    "semantic_role": "Location",
    "surface_lexicon": {
      "surface_modifier": "in(park)",
      "normalized_modifier": "in_park",
      "type": "Adv",
      "semantic_role": "Location",
      "source": "translator/surface_lexicon.py"
    }
  }
]
```

The rendered replacement is `and_T(walk(1)(in(park), john),
talk(1)(in(park), john))`. Its predicate type is therefore
`forall n : nat, ModifierSeq n -> Entity -> PropT`, not just
`Entity -> Prop`.

Single-word manner adverbs use the same field: `John walked and talked slowly`
stores `slowly : Adv` and renders as `and_T(walk(1)(slowly, john),
talk(1)(slowly, john))`.

When multiple shared modifiers appear, their order is preserved in the same
sequence. Thus `John walked and talked slowly in the park` renders as
`and_T(walk(2)(slowly, in(park), john), talk(2)(slowly, in(park), john))`,
whereas `John walked and talked in the park slowly` renders as
`and_T(walk(2)(in(park), slowly, john), talk(2)(in(park), slowly, john))`.
The Coq scaffold mirrors this order with `mods_cons 1 ... (mods_cons 0 ... mods_nil)`.
The same invariant holds when one modifier is fronted and another is trailing:
`Slowly John walked and talked in the park` stores the sequence
`slowly, in(park)`.

### `transitive_predicate_coordination`

Represents same-subject transitive VP coordination such as `John ate bread and
drank water` or `John ate bread or drank water`. Each conjunct keeps its own
object and lexical object type:

```json
{
  "kind": "transitive_predicate_coordination",
  "subject": {
    "name": "john",
    "type": "Entity"
  },
  "modifiers": [],
  "clauses": [
    {
      "predicate": {
        "surface": "ate",
        "name": "eat",
        "predicate_type": "Entity -> Food -> Prop"
      },
      "object": {
        "name": "bread",
        "type": "Food"
      }
    },
    {
      "predicate": {
        "surface": "drank",
        "name": "drink",
        "predicate_type": "Entity -> Drinkable -> Prop"
      },
      "object": {
        "name": "water",
        "type": "Drinkable"
      }
    }
  ],
  "connective": "and_T",
  "connective_type": "Prop -> Prop -> Prop",
  "time_modifiers": []
}
```

Renders as:

```text
and_T(eat(john, bread), drink(john, water))
```

Disjunctive VP coordination sets `"connective": "or_T"`, so `John ate bread or
drank water` renders as `or_T(eat(john, bread), drink(john, water))` rather than
forming a pseudo-object such as `bread_or_drank_water`. `Either` may appear
before the shared subject or before the first VP, and `both` may appear before
the first VP in the `and` case; these are treated as surface coordination
markers, not as part of the subject.

Fronted and trailing time expressions use the same `time_modifiers` field and
therefore scope over the whole conjunction, e.g. `at_T(yesterday, and_T(...))`.
Fronted or trailing non-temporal prepositional phrases use the shared
`modifiers` field, so `In the park John ate bread and drank water` and `John
ate bread and drank water in the park` both render as
`and_T(eat(1)(in(park), john, bread), drink(1)(in(park), john, water))`.
Single-word manner adverbs behave the same way: `John ate bread and drank water
quickly` keeps `water` as the right-hand object and stores `quickly : Adv`.
Multiple shared modifiers remain order-sensitive here as well; for example,
`John ate bread and drank water quickly in the park` uses the modifier sequence
`quickly, in(park)` across both transitive conjuncts.
`Quickly John ate bread and drank water in the park` uses the same sequence,
because fronted and trailing shared modifiers are concatenated before Coq export.

This construction is deliberately separate from object coordination. `Mary
visited Paris and London` is handled by `object_coordination`, not as VP
coordination.

Repeated semantic occurrences are not treated as repeated declarations. Thus
`John ate bread and ate bread` keeps two conjuncts in the formula but exports
only one `bread : Food` and one `eat : Entity -> Food -> Prop` declaration.
Likewise, repeated time modifiers such as `yesterday yesterday` keep nested
temporal operators while declaring `yesterday : Entity` once. If the same
surface object would need incompatible lexical types, as in `John ate bread and
drank bread`, the AST type check reports the conflict before Coq is attempted.

## Type Checking

The translator runs a lightweight structural type check over every emitted AST.
The result is returned as:

```json
{
  "type_check": {
    "ok": true,
    "type": "t",
    "errors": []
  }
}
```

Current type rules:

- `application` has type `t` when `adverb_count` is a natural number equal to
  the number of `modifiers`, and when the normalized `modifier_vector` has the
  same length, the same modifier order, and descending `tail_length` fields.
  It must also contain a `role_frame` whose role values match
  `application.arguments` in canonical thematic order and whose role types
  match the generated function argument types. This preserves thematic-role
  labels such as `Agent` and `Theme` after the event variable is discharged
  while still allowing lexically refined object types such as `Food`,
  `Readable`, and `Drinkable`.
- `sigma` has type `t` when its body has type `t`.
- `repeat` has type `t` when `count` is a positive natural number and its body
  has type `t`.
- `time` has type `t` when its operator is a recognized temporal operator and
  its body has type `t`.
- `not` has type `t` when its body has type `t`. Simple do-support negation
  such as `John did not walk` is compiled by wrapping the positive-clause AST in
  this constructor. Right-branch coordinated do-support negation, as in `John
  walked and did not talk`, records `negated: true` on the second checked
  coordinate and renders `and_T(walk(john), not_T(talk(john)))`.
  The same right-branch rule can use `or_T`: `John walked or did not talk`
  renders as `or_T(walk(john), not_T(talk(john)))`, and the transitive case
  `John ate bread or did not drink water` preserves `bread : Food` and
  `water : Drinkable`.
  Scope-ambiguous
  coordinated do-support negation, as in `John did not walk and talk`, is
  represented by `do_support_negation_coordination_ambiguity` with two readings:
  `negation_over_conjunction` renders `not_T(and_T(walk(john), talk(john)))`,
  while `distributed_negation` renders
  `and_T(not_T(walk(john)), not_T(talk(john)))`.
  Negated disjunction is a separate single-reading boundary:
  `John did not walk or talk` is represented by
  `do_support_negation_disjunction` and renders
  `not_T(or_T(walk(john), talk(john)))`, so `or talk` is not consumed as an
  entity-like object.
  Branch-local modifiers are preserved inside both readings: `John did not walk
  slowly and talk quickly` renders `walk(1)(slowly, john)` and
  `talk(1)(quickly, john)` under the two alternative negation scopes, while
  `John did not eat bread slowly and drink water quickly` keeps `bread : Food`
  and `water : Drinkable` separate from the `slowly` and `quickly` Adv entries.
  Branch-local time behaves the same way: `John did not walk yesterday and talk
  today` stores `yesterday` and `today` on the two clause records before the
  alternative negation scopes are rendered. Fronted shared material is kept out
  of the subject: `Yesterday John did not walk and talk` stores `john` as the
  subject and wraps both readings in `at_T(yesterday, ...)`, while `In the park
  John did not walk and talk` copies `in(park) : Adv` into both branch-local
  modifier vectors. The do-support ambiguity entry alternates over the fronted
  prefix, so mixed orders such as `In the park yesterday John did not walk and
  talk` still keep `john` as the subject, `in(park)` as shared `Adv`, and
  `yesterday` as a proposition-level time operator. Time modifiers scope over
  the resulting proposition, and Adv modifiers remain typed modifier entries
  rather than entities or object-name suffixes. For the ambiguous coordination
  entry, the API mirrors the two negation readings in top-level
  `semantic_readings`, so clients can enumerate the checked wide-scope and
  distributed readings without knowing the construction-specific AST layout.
  `semantic_readings_check` records the same reading count and rejects malformed
  normalized entries before clients need to inspect the nested
  construction-specific representation.
  Repeated do-support negation across both branches, such as `John did not walk
  and did not talk`, is treated as an explicit distributed surface form:
  `and_T(not_T(walk(john)), not_T(talk(john)))`. The same parser boundary keeps
  `john` as the subject rather than accepting a malformed subject like
  `john_did_not`. If the repeated surface connective is `or`, as in
  `John did not walk or did not talk`, the checked output preserves that
  disjunction as `or_T(not_T(walk(john)), not_T(talk(john)))`.
  Clear contrastive `but` cases use the same local marker on the first
  coordinate: `John did not walk but talked` renders as
  `and_T(not_T(walk(john)), talk(john))`.
  Shared modifiers are preserved for those clear contrastive readings as well,
  so `John did not walk but talked in the park` records `in(park) : Adv` instead
  of introducing an entity-like object. Branch-local Adv modifiers are
  represented by `contrastive_branch_modifier_coordination`: the negated branch
  may use `walk(1)(in(park), john)` or `eat(1)(in(park), john, bread)`, while the
  positive branch can independently use either a zero-length sequence, such as
  `talk(0)(john)` or `drink(0)(john, water)`, or its own local Adv sequence, such
  as `talk(1)(quickly, john)` or `drink(1)(quickly, john, water)`. Transitive
  coordination rules are additionally gated by the shared surface lexicon's
  transitive-verb list, so intransitive predicates such as `walk` and `talk` do
  not license pseudo-objects formed from modifiers. Fronted shared Adv material
  is represented as a shared prefix in both branch-local modifier lists, e.g.
  `eat(2)(in(park), slowly, john, bread)` and
  `drink(2)(in(park), quickly, john, water)`. Branch-internal time modifiers
  are stored on the relevant clause in `time_modifiers`, so the negated branch
  can render as `not_T(at_T(yesterday, eat(0)(john, bread)))` while the positive
  branch remains independently modified. The same normalized `semantic_readings`
  and `semantic_readings_check` shape is emitted for successful single-reading
  do-support routes: simple negation, right-branch negation coordination,
  contrastive `but`, repeated do-support negation, and negated disjunction.
  Single readings therefore have the same checked formula, scope label, and Coq
  definition audit shape as ambiguity sets.
- `transition` has type `TransitionT`; its `theme` is exported as `Entity`, while
  `state_scale` is exported as `StateScale`, and `source_state` and
  `target_state` are exported as `State`. The `state_scale` must match the
  target state scale inferred from the lexical state map, known source-state
  scales must agree with it, and if both states are known rather than `_`, they
  must differ. The `target_state` must be known, because a resultative
  transition without a target state is not a completed change-of-state
  analysis.
- `cause` has type `t` only when its `effect` has type `TransitionT`; its
  optional `activity` must have type `t`.
- `lexical_state_change` has type `Prop` when its `frame` is one of
  `inchoative`, `causative`, or `instrumental`, the frame matches the `causer`
  and `instrument` fields, the registered verb licenses that frame, and the
  transition target matches both the state lexicon and the verb registration.
- `timed_after` has type `Prop` when it binds `t_sing : Time` and
  `t_salute : Time`, the first predicate has type `Entity -> Time -> Prop`, the
  second predicate has type `Entity -> Entity -> Time -> Prop`, and
  `before : Time -> Time -> Prop` relates `t_sing` before `t_salute`.
- `perception_nominalization` has type `Prop` when the perception predicate has
  type `Entity -> Entity -> Prop`, the embedded proposition is either a simple
  `Entity -> Prop` clause, a checked proposition coordination, or a checked
  temporal relation over `Time`, and the nominalizer has type `Prop -> Entity`.
  Embedded temporal relations bind the time variables used by their main and
  reference propositions and require `before : Time -> Time -> Prop` relations
  in the direction licensed by the surface connector. If either side is a timed
  proposition coordination, its `clauses` list must contain at least two timed
  clauses, and the checker requires one `before` relation for each
  main/reference time pair. Homogeneous `or` timed lists are rendered with
  branch-local time quantification: each disjunct receives its own existential
  `Time` binders and its own `before` constraints before the branches are
  folded by `or_T`. When both sides are disjunctive, the branch renderer uses
  the Cartesian product of main-side and reference-side alternatives, preserving
  one scoped temporal relation per pair. Mixed `and`/`or` timed coordination is
  accepted only under an explicit precedence policy: `and` groups are built
  first, and the resulting groups are folded by `or_T`. The checker then
  flattens the timed leaves to verify that every leaf has the expected bound
  time variable and that the temporal relation still contains one ordered
  `before` constraint per main/reference leaf pair. This policy is symmetric:
  mixed coordination may occur on the main side, on the reference side, or on
  both sides, in which case the branch renderer takes the Cartesian product of
  the top-level `or_T` alternatives while preserving nested `and_T` groups.
  Mixed nodes also carry an `alternative_scope_readings` audit at the temporal
  relation level. Each alternative records the opposite `or_before_and` policy,
  its branch count, a rendered dependent-type formula, and a type-check result;
  the perception Coq/Rocq scaffold emits one checked definition per alternative.
  The same primary and alternative formulas are normalized into top-level
  `semantic_readings`, preserving the scope policy and type-check result for
  the web/API layer. The companion `semantic_readings_check` verifies that each
  normalized alternative names an exported Coq/Rocq definition.
- `forall_time` has type `Prop` when it binds `x : Entity` and `t : Time`, and
  both the antecedent and consequent have type `Entity -> Time -> Prop` over the
  shared time variable `t`.
- `predicate_coordination` has type `Prop` when the subject has type `Entity`,
  the connective type matches the proposition type of the conjuncts, each
  coordinated predicate has either type `Entity -> Prop` or, when shared `Adv`
  modifiers are present, `forall n : nat, ModifierSeq n -> Entity -> PropT`, and
  every predicate lemma matches its surface form.
- `subject_coordination` has type `Prop` when exactly two subjects have type
  `Entity`, the shared predicate has type `Entity -> Prop` or, when shared `Adv`
  modifiers are present, `forall n : nat, ModifierSeq n -> Entity -> PropT`,
  and the connective type matches the resulting proposition type.
- `transitive_subject_coordination` has type `Prop` when exactly two subjects
  have type `Entity`, the shared object has a stable lexical type, and the
  shared predicate has type `Entity -> ObjectType -> Prop` or, with shared `Adv`
  modifiers, `forall n : nat, ModifierSeq n -> Entity -> ObjectType -> PropT`.
- `object_coordination` has type `Prop` when the subject has type `Entity`, both
  coordinated objects share the predicate's lexical object type, and the shared
  predicate has type `Entity -> ObjectType -> Prop` or, with shared `Adv`
  modifiers, `forall n : nat, ModifierSeq n -> Entity -> ObjectType -> PropT`.
- `transitive_predicate_coordination` has type `Prop` when the shared subject has
  type `Entity`, each clause supplies an object with a stable lexical type, and
  each predicate has the corresponding type `Entity -> ObjectType -> Prop` or,
  with shared `Adv` modifiers, `forall n : nat, ModifierSeq n -> Entity ->
  ObjectType -> PropT`.

This is intentionally a shallow type layer. It does not yet prove semantic
validity, but it prevents malformed intermediate representations from being
silently rendered as plausible formulas.

Modifier entries are not entity-denoting arguments. The AST records this twice:
`modifier_vector` preserves the dependent length index, while `modifier_roles`
records the semantic class of each modifier as an `Adv` value. For example,
`in(bathroom)` receives `semantic_role: "Location"`, `with(knife)` receives
`semantic_role: "Instrument"`, and ordinary adverbs such as `slowly` receive
`semantic_role: "Manner"`. The checker verifies this metadata against the
modifier predicate, so an instrumental `with(...)` modifier cannot be labeled as
`Location`. Each role entry also carries a nested `surface_lexicon` audit:
`surface_modifier` preserves the original modifier string, while
`normalized_modifier` records the constant name that will be exported to the
proof-assistant scaffold, such as `in_bathroom` or `with_knife`. The checker
validates that this audit agrees with the modifier, the `Adv` type, the semantic
role, and the shared surface-lexicon module source. The role classification is
also supplied by the same module through `MODIFIER_ROLE_BY_PREDICATE`, keeping
the Location/Instrument/Source/Goal/Manner choice with the lexical resources
that normalize surface forms. Thus `from(home)` is a Source-like `Adv` exported
as `from_home`, while `to(school)` is a Goal-like `Adv` exported as
`to_school`. In the proof-assistant scaffold all of these are still exported at
type `Adv`, with the current shallow Coq definition:

```coq
Definition PropT : Type := Prop.
Definition Adv : Type := (Entity -> PropT) -> Entity -> PropT.
Parameter ModifierSeq : nat -> Type.
Parameter mods_nil : ModifierSeq 0.
Parameter mods_cons : forall n : nat, Adv -> ModifierSeq n -> ModifierSeq (S n).
```

Thus `in(bathroom)` exports as `in_bathroom : Adv`, while ordinary arguments
such as `John` and `toast` export as `Entity`. Application exports read the
normalized `modifier_vector` and place its individual modifier constants into an
indexed `ModifierSeq n` value. This keeps one verb declaration stable when
several checked examples use different numbers of modifiers, while giving Coq an
explicit length invariant to check.

## Lean and Coq Style Export

Well-typed ASTs are exported to shallow embedding syntax for Lean- or Coq-style
formalization. Export is intentionally blocked when `type_check.ok` is false.

Run:

```bash
python3 translator/dependent_type_event_translator.py \
  translator/examples/example_eat_omission.json \
  --export lean
```

Lean-style output:

```text
(Exists fun x_theme : Food => (eat 0 mods_nil John x_theme))
```

Coq-style output:

```text
(exists x_theme : Food, (eat 0 mods_nil John x_theme))
```

For non-binding constructors, both targets currently use the same shallow
prefix form:

```text
(repeat 2 (knock 0 mods_nil John))
(Cause John (Transition vase integrity_scale intact broken))
```

Names are normalized for proof-assistant friendliness. For example,
`in(bathroom)` is exported as `in_bathroom`, and the unknown source state `_`
is exported as `unknown_state` when no lexical pre-state is available. Surface
verb lemmatization and passive participle recognition live in
`translator/surface_lexicon.py`, so irregular forms such as `seen`, `written`,
and `froze` are normalized before the semantic AST is checked or exported.

## Formalization Files

Run:

```bash
python3 scripts/generate_formalization.py
```

This writes:

```text
formalization/DependentTypeEventSemantics.lean
formalization/DependentTypeEventSemantics.v
```

The generated files contain shared declarations for the shallow embedding and
one `example_n` definition for each checked example.

They also include `#check example_n` commands in Lean style and
`Check example_n.` commands in Coq style. When no proof assistant is installed,
`scripts/check_formalization.py` still provides a deterministic consistency
check by regenerating the files and checking their expected declarations,
examples, normalized names, and check commands.
