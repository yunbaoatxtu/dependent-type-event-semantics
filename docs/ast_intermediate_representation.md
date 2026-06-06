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
