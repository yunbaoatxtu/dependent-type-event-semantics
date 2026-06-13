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
  "arguments": ["John", "toast"]
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

### `cause` and `transition`

Represent causal-resultative structure.

```json
{
  "kind": "cause",
  "causer": "John",
  "effect": {
    "kind": "transition",
    "theme": "vase",
    "source_state": "_",
    "target_state": "broken"
  },
  "activity": {
    "kind": "application",
    "function": "break",
    "adverb_count": 0,
    "modifiers": [],
    "arguments": ["John", "vase"]
  }
}
```

Renders as:

```text
Cause(John, Transition(vase, _, broken))
```

The optional `activity` field preserves the original verbal description even
when the visible rendering focuses on the causal transition. This is useful for
later proof assistant export, where the causing process and the result
transition may need separate types.

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
  the number of `modifiers`.
- `sigma` has type `t` when its body has type `t`.
- `repeat` has type `t` when `count` is a positive natural number and its body
  has type `t`.
- `time` has type `t` when its operator is a recognized temporal operator and
  its body has type `t`.
- `transition` has type `Transition`.
- `cause` has type `t` only when its `effect` has type `Transition`; its
  optional `activity` must have type `t`.

This is intentionally a shallow type layer. It does not yet prove semantic
validity, but it prevents malformed intermediate representations from being
silently rendered as plausible formulas.

Modifier entries are not entity-denoting arguments. In the proof-assistant
scaffold they are exported at type `Adv`, with the current shallow Coq
definition:

```coq
Definition PropT : Type := Prop.
Definition Adv : Type := (Entity -> PropT) -> Entity -> PropT.
```

Thus `in(bathroom)` exports as `in_bathroom : Adv`, while ordinary arguments
such as `John` and `toast` export as `Entity`.

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
(Exists fun x_theme : Food => (eat 0 John x_theme))
```

Coq-style output:

```text
(exists x_theme : Food, (eat 0 John x_theme))
```

For non-binding constructors, both targets currently use the same shallow
prefix form:

```text
(repeat 2 (knock 0 John))
(Cause John (Transition vase _ broken))
```

Names are normalized for proof-assistant friendliness. For example,
`in(bathroom)` is exported as `in_bathroom`, and the unknown source state `_`
is exported as `unknown_state`.

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
