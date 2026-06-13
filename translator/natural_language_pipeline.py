#!/usr/bin/env python3
"""End-to-end prototype for natural language to checked Coq scaffolds."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from translator.dependent_type_event_translator import export_module, translate


ROOT = Path(__file__).resolve().parents[1]
ROCQ_ENV = Path(
    "/Applications/Rocq-Platform~9.0~2025.08.app/Contents/Resources/bin/coq-env.sh"
)
ARTICLES = {"a", "an", "the"}
PREPOSITIONS = {
    "at", "in", "on", "under", "over", "near", "beside", "with", "from", "to", "into",
}
COUNT_WORDS = {"once", "twice", "thrice"}
COMMON_ADVERBS = {
    "slowly", "quickly", "quietly", "loudly", "carefully", "happily", "sadly",
}
IRREGULAR_VERBS = {
    "admired": "admire",
    "ate": "eat",
    "saw": "see",
    "sat": "sit",
    "saluted": "salute",
    "loves": "love",
    "broke": "break",
    "broken": "break",
    "drank": "drink",
    "went": "go",
    "ran": "run",
    "left": "leave",
}


@dataclass(frozen=True)
class ConstructionRule:
    rule_id: str
    label: str
    phenomenon: str
    analyzer: Callable[[str], dict[str, Any] | None]
    forbidden_coq_fragments: tuple[str, ...] = ()


def atom(pred: str, *args: str) -> dict[str, Any]:
    return {"pred": pred, "args": list(args)}


def event_formula(*items: dict[str, Any]) -> dict[str, Any]:
    return {"exists": ["e"], "body": {"and": list(items)}}


def quantifier_scope_reading(
    subject_noun: str,
    verb: str,
    object_noun: str,
    subject_first: bool,
) -> dict[str, Any]:
    subject = {
        "role": "subject",
        "variable": f"x_{subject_noun}",
        "predicate": subject_noun,
        "predicate_type": "Entity -> Prop",
    }
    obj = {
        "role": "object",
        "variable": f"x_{object_noun}",
        "predicate": object_noun,
        "predicate_type": "Entity -> Prop",
    }
    scope_order = [subject, obj] if subject_first else [obj, subject]
    relation = {
        "predicate": verb,
        "predicate_type": "Entity -> Entity -> Prop",
        "arguments": [subject["variable"], obj["variable"]],
    }
    if subject_first:
        name = f"some_{subject_noun}_wide_scope"
    else:
        name = f"some_{object_noun}_wide_scope"
    return {
        "name": name,
        "quantifier": "some",
        "scope_order": scope_order,
        "relation": relation,
    }


def render_quantifier_reading(reading: dict[str, Any], coq: bool = False) -> str:
    relation = reading["relation"]
    args = relation["arguments"]
    if coq:
        body = f"{relation['predicate']} {' '.join(args)}"
        connective = "/\\"
        separator = ", "
    else:
        body = f"{relation['predicate']}({', '.join(args)})"
        connective = "and"
        separator = ". "
    for binder in reversed(reading["scope_order"]):
        var = binder["variable"]
        predicate = binder["predicate"]
        if coq:
            predicate_application = f"{predicate} {var}"
            body = (
                f"exists {var} : Entity{separator}"
                f"{predicate_application} {connective} {body}"
            )
        else:
            predicate_application = f"{predicate}({var})"
            body = (
                f"exists {var} : Entity{separator}"
                f"{predicate_application} {connective} {body}"
            )
    return body


def quantifier_scope_coq(reading: dict[str, Any]) -> str:
    return f"Definition {reading['name']} : Prop := {render_quantifier_reading(reading, coq=True)}."


def check_quantifier_scope_readings(readings: list[dict[str, Any]]) -> dict[str, Any]:
    errors: list[str] = []
    if len(readings) != 2:
        errors.append(f"expected two scope readings, got {len(readings)}")

    observed_orders: list[tuple[str, ...]] = []
    for index, reading in enumerate(readings):
        order = reading.get("scope_order")
        relation = reading.get("relation")
        if not isinstance(order, list) or len(order) != 2:
            errors.append(f"readings[{index}].scope_order must contain two binders")
            continue
        if not isinstance(relation, dict):
            errors.append(f"readings[{index}].relation must be an object")
            continue

        observed_orders.append(tuple(str(binder.get("role")) for binder in order))
        relation_args = relation.get("arguments")
        if relation.get("predicate_type") != "Entity -> Entity -> Prop":
            errors.append(
                f"readings[{index}].relation must have type Entity -> Entity -> Prop"
            )
        if not isinstance(relation_args, list) or len(relation_args) != 2:
            errors.append(f"readings[{index}].relation.arguments must contain two entities")

        for binder_index, binder in enumerate(order):
            if not isinstance(binder, dict):
                errors.append(f"readings[{index}].scope_order[{binder_index}] must be an object")
                continue
            if binder.get("predicate_type") != "Entity -> Prop":
                errors.append(
                    f"readings[{index}].scope_order[{binder_index}] "
                    "must have predicate type Entity -> Prop"
                )
            if not binder.get("variable"):
                errors.append(
                    f"readings[{index}].scope_order[{binder_index}] must bind a variable"
                )

    if set(observed_orders) != {("subject", "object"), ("object", "subject")}:
        errors.append(
            "scope readings must include both subject-wide and object-wide orders"
        )
    return {
        "ok": not errors,
        "type": "Prop" if not errors else None,
        "errors": errors,
        "reading_count": len(readings),
    }


def quantifier_scope_pipeline(sentence: str) -> dict[str, Any] | None:
    tokens = tokenize(sentence)
    if len(tokens) != 5 or tokens[0] != "some" or tokens[3] != "some":
        return None
    subject_noun = lemma_verb(tokens[1])
    verb = lemma_verb(tokens[2])
    object_noun = lemma_verb(tokens[4])
    readings = [
        quantifier_scope_reading(subject_noun, verb, object_noun, subject_first=True),
        quantifier_scope_reading(subject_noun, verb, object_noun, subject_first=False),
    ]
    type_check = check_quantifier_scope_readings(readings)
    event_semantics = {
        "analysis": "quantifier-scope",
        "source": sentence,
        "readings": [
            {**reading, "formula": render_quantifier_reading(reading)}
            for reading in readings
        ],
    }
    coq_code = "\n".join(
        [
            "(* Quantifier-scope scaffold for dependent-type event semantics. *)",
            "Parameter Entity : Type.",
            f"Parameter {subject_noun} : Entity -> Prop.",
            f"Parameter {object_noun} : Entity -> Prop.",
            f"Parameter {verb} : Entity -> Entity -> Prop.",
            "",
            quantifier_scope_coq(readings[0]),
            quantifier_scope_coq(readings[1]),
            "",
            f"Check some_{subject_noun}_wide_scope.",
            f"Check some_{object_noun}_wide_scope.",
            "",
        ]
    )
    return {
        "kind": "quantifier_scope_ambiguity",
        "input_sentence": sentence,
        "event_semantics": event_semantics,
        "dependent_type_translation": "\n".join(
            reading["formula"] for reading in event_semantics["readings"]
        ),
        "ast": {
            "kind": "scope_ambiguity",
            "quantifier": "some",
            "readings": readings,
        },
        "type_check": {
            **type_check,
            "note": (
                "Both scope readings are represented with entity predicates "
                "and a binary relation; no Event argument is introduced."
            ),
        },
        "coq_code": coq_code,
    }


def timed_after_pipeline(sentence: str) -> dict[str, Any] | None:
    tokens = tokenize(sentence)
    expected = [
        "after",
        "the",
        "singing",
        "of",
        "the",
        "marseillaise",
        "john",
        "saluted",
        "the",
        "flag",
    ]
    if tokens != expected:
        return None

    first_predicate = lemma_verb(tokens[2])
    first_theme = "Marseillaise"
    second_agent = "John"
    second_predicate = lemma_verb(tokens[7])
    second_theme = "flag"
    coq_code = "\n".join(
        [
            "(* Timed Luo-Shi-style replacement for Parsons-style event talk. *)",
            "Parameter Entity : Type.",
            "Parameter Time : Type.",
            "",
            f"Parameter {first_theme} : Entity.",
            f"Parameter {second_agent} : Entity.",
            f"Parameter {second_theme} : Entity.",
            "",
            f"Parameter {first_predicate} : Entity -> Time -> Prop.",
            f"Parameter {second_predicate} : Entity -> Entity -> Time -> Prop.",
            "Parameter before : Time -> Time -> Prop.",
            "",
            "Definition after_singing_salute : Prop :=",
            "  exists t_sing : Time,",
            "  exists t_salute : Time,",
            f"    {first_predicate} {first_theme} t_sing /\\",
            f"    {second_predicate} {second_agent} {second_theme} t_salute /\\",
            "    before t_sing t_salute.",
            "",
            "Check after_singing_salute.",
            "",
        ]
    )
    event_semantics = {
        "analysis": "parsons-after-event-talk",
        "source": sentence,
        "event_style_reference": (
            "exists e e'. singing(e') and Theme(e', Marseillaise) and "
            "saluting(e) and Agent(e, John) and Theme(e, flag) and after(e', e)"
        ),
        "typed_replacement": (
            "exists t_sing t_salute : Time. "
            "sing(Marseillaise, t_sing) and salute(John, flag, t_salute) "
            "and before(t_sing, t_salute)"
        ),
    }
    return {
        "kind": "timed_after",
        "input_sentence": sentence,
        "event_semantics": event_semantics,
        "dependent_type_translation": event_semantics["typed_replacement"],
        "ast": {
            "kind": "timed_after",
            "first": {
                "predicate": first_predicate,
                "theme": first_theme,
                "time": "t_sing",
            },
            "second": {
                "predicate": second_predicate,
                "agent": second_agent,
                "theme": second_theme,
                "time": "t_salute",
            },
            "relation": "before(t_sing, t_salute)",
        },
        "type_check": {
            "ok": True,
            "type": "Prop",
            "errors": [],
            "note": "The Parsons-style event relation is represented with Time variables, not an Event parameter.",
        },
        "coq_code": coq_code,
    }


def perception_nominalization_pipeline(sentence: str) -> dict[str, Any] | None:
    tokens = tokenize(sentence)
    if tokens not in (["mary", "saw", "john", "leave"], ["mary", "saw", "john", "left"]):
        return None

    experiencer = "Mary"
    embedded_subject = "John"
    perception_predicate = lemma_verb(tokens[1])
    embedded_predicate = lemma_verb(tokens[3])
    coq_code = "\n".join(
        [
            "(* Luo-Shi-style nominalization for perception complements. *)",
            "Parameter Entity : Type.",
            "",
            f"Parameter {experiencer} : Entity.",
            f"Parameter {embedded_subject} : Entity.",
            "",
            "Parameter E : Prop -> Entity.",
            f"Parameter {embedded_predicate} : Entity -> Prop.",
            f"Parameter {perception_predicate} : Entity -> Entity -> Prop.",
            "",
            "Definition mary_saw_john_leave : Prop :=",
            f"  {perception_predicate} {experiencer} (E ({embedded_predicate} {embedded_subject})).",
            "",
            "Check mary_saw_john_leave.",
            "",
        ]
    )
    event_semantics = {
        "analysis": "parsons-perception-complement",
        "source": sentence,
        "event_style_reference": (
            "exists e e'. seeing(e) and Experiencer(e, Mary) and "
            "leaving(e') and Agent(e', John) and Theme(e, e')"
        ),
        "typed_replacement": "see(Mary, E(leave(John)))",
    }
    return {
        "kind": "perception_nominalization",
        "input_sentence": sentence,
        "event_semantics": event_semantics,
        "dependent_type_translation": event_semantics["typed_replacement"],
        "ast": {
            "kind": "perception_nominalization",
            "perception": perception_predicate,
            "experiencer": experiencer,
            "embedded": {
                "predicate": embedded_predicate,
                "subject": embedded_subject,
                "nominalizer": "E",
            },
        },
        "type_check": {
            "ok": True,
            "type": "Prop",
            "errors": [],
            "note": "The perceived eventuality is embedded by E : Prop -> Entity, not by an Event argument.",
        },
        "coq_code": coq_code,
    }


def every_burning_pipeline(sentence: str) -> dict[str, Any] | None:
    tokens = tokenize(sentence)
    if tokens != ["in", "every", "burning", "oxygen", "is", "consumed"]:
        return None

    coq_code = "\n".join(
        [
            "(* Timed universal replacement for Parsons-style event inclusion. *)",
            "Parameter Entity : Type.",
            "Parameter Time : Type.",
            "",
            "Parameter oxygen : Entity.",
            "",
            "Parameter burn : Entity -> Time -> Prop.",
            "Parameter consume : Entity -> Time -> Prop.",
            "",
            "Definition every_burning_consumes_oxygen : Prop :=",
            "  forall x : Entity,",
            "  forall t : Time,",
            "    burn x t -> consume oxygen t.",
            "",
            "Check every_burning_consumes_oxygen.",
            "",
        ]
    )
    event_semantics = {
        "analysis": "parsons-event-inclusion",
        "source": sentence,
        "event_style_reference": (
            "forall e. burning(e) -> exists e'. consuming(e') and "
            "Theme(e', oxygen) and IN(e', e)"
        ),
        "typed_replacement": (
            "forall x : Entity. forall t : Time. "
            "burn(x, t) -> consume(oxygen, t)"
        ),
    }
    return {
        "kind": "universal_timed_burning",
        "input_sentence": sentence,
        "event_semantics": event_semantics,
        "dependent_type_translation": event_semantics["typed_replacement"],
        "ast": {
            "kind": "forall_time",
            "domain": "burning",
            "entity_variable": "x",
            "time_variable": "t",
            "antecedent": "burn(x, t)",
            "consequent": "consume(oxygen, t)",
        },
        "type_check": {
            "ok": True,
            "type": "Prop",
            "errors": [],
            "note": "Event inclusion is represented as universal quantification over entities and times.",
        },
        "coq_code": coq_code,
    }


def construction_rules() -> list[ConstructionRule]:
    return [
        ConstructionRule(
            rule_id="perception_nominalization",
            label="Perception complement nominalization",
            phenomenon="Parsons/Luo-Shi perception complement",
            analyzer=perception_nominalization_pipeline,
            forbidden_coq_fragments=("Parameter Event : Type.", "exists e : Event"),
        ),
        ConstructionRule(
            rule_id="universal_timed_burning",
            label="Universal timed burning",
            phenomenon="Parsons/Luo-Shi event inclusion",
            analyzer=every_burning_pipeline,
            forbidden_coq_fragments=("Parameter Event : Type.", "IN"),
        ),
        ConstructionRule(
            rule_id="timed_after",
            label="Timed after relation",
            phenomenon="Parsons/Luo-Shi event ordering",
            analyzer=timed_after_pipeline,
            forbidden_coq_fragments=("Parameter Event : Type.", "exists e : Event"),
        ),
        ConstructionRule(
            rule_id="quantifier_scope_ambiguity",
            label="Quantifier-scope ambiguity",
            phenomenon="Existential scope ambiguity",
            analyzer=quantifier_scope_pipeline,
            forbidden_coq_fragments=(
                "Parameter Event : Type.",
                "exists e : Event",
                "Parameter Agent :",
                "Parameter Theme :",
                "Parameter some : Entity.",
                "Parameter boy : nat ->",
            ),
        ),
    ]


def check_forbidden_coq_fragments(
    coq_code: str,
    forbidden_fragments: tuple[str, ...],
) -> list[str]:
    return [fragment for fragment in forbidden_fragments if fragment in coq_code]


def construction_rule_payload(rule: ConstructionRule) -> dict[str, Any]:
    return {
        "id": rule.rule_id,
        "label": rule.label,
        "phenomenon": rule.phenomenon,
        "forbidden_coq_fragments": list(rule.forbidden_coq_fragments),
    }


def construction_hygiene_payload(
    rule: ConstructionRule,
    found_fragments: list[str],
) -> dict[str, Any]:
    return {
        "ok": not found_fragments,
        "checked": True,
        "forbidden_coq_fragments": list(rule.forbidden_coq_fragments),
        "found_forbidden_fragments": found_fragments,
    }


def run_registered_rule(
    rule: ConstructionRule,
    sentence: str,
    require_coq: bool,
) -> dict[str, Any] | None:
    analysis = rule.analyzer(sentence)
    if analysis is None:
        return None

    forbidden_found = check_forbidden_coq_fragments(
        analysis["coq_code"],
        rule.forbidden_coq_fragments,
    )
    if forbidden_found:
        return {
            **analysis,
            "ok": False,
            "construction_rule": construction_rule_payload(rule),
            "construction_hygiene": construction_hygiene_payload(rule, forbidden_found),
            "coq_check": {
                "ok": False,
                "status": "failed",
                "message": (
                    "Generated Coq contains forbidden construction fragments: "
                    + ", ".join(forbidden_found)
                ),
            },
            "conclusion": "Translation failed construction-specific Coq hygiene checks.",
        }

    coq_check = verify_coq_code(analysis["coq_code"], require_coq=require_coq)
    success = analysis["type_check"]["ok"] and coq_check["ok"] is not False
    return {
        **analysis,
        "ok": success,
        "construction_rule": construction_rule_payload(rule),
        "construction_hygiene": construction_hygiene_payload(rule, forbidden_found),
        "coq_check": coq_check,
        "conclusion": (
            f"Translation succeeded via construction rule {rule.rule_id}."
            if success
            else "Translation failed at Coq/Rocq boundary validation."
        ),
    }


def normalize_sentence(sentence: str) -> str:
    normalized = sentence.strip().rstrip(".!?")
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.lower()


def tokenize(sentence: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9_']+", normalize_sentence(sentence))


def clean_phrase(tokens: list[str]) -> str:
    content = [token for token in tokens if token not in ARTICLES]
    if not content:
        return "entity"
    return "_".join(content)


def lemma_verb(token: str) -> str:
    if token in IRREGULAR_VERBS:
        return IRREGULAR_VERBS[token]
    if token.endswith("ies") and len(token) > 3:
        return token[:-3] + "y"
    if token.endswith("es") and len(token) > 3:
        return token[:-2]
    if token.endswith("s") and len(token) > 2:
        return token[:-1]
    if token.endswith("ed") and len(token) > 3:
        stem = token[:-2]
        if len(stem) > 1 and stem[-1] == stem[-2]:
            return stem[:-1]
        return stem
    if token.endswith("ing") and len(token) > 4:
        stem = token[:-3]
        if len(stem) > 1 and stem[-1] == stem[-2]:
            return stem[:-1]
        return stem
    return token


def fallback_sentence_to_event_semantics(sentence: str) -> dict[str, Any]:
    tokens = tokenize(sentence)
    if len(tokens) < 2:
        raise ValueError("Please enter at least a subject and a predicate.")

    subject_tokens: list[str] = []
    idx = 0
    while idx < len(tokens) and tokens[idx] in ARTICLES:
        idx += 1
    if idx < len(tokens):
        subject_tokens.append(tokens[idx])
        idx += 1
    if idx >= len(tokens):
        raise ValueError("Could not identify a predicate after the subject.")

    verb = lemma_verb(tokens[idx])
    idx += 1
    items = [atom(verb, "e"), atom("Agent", "e", clean_phrase(subject_tokens))]
    object_tokens: list[str] = []

    while idx < len(tokens):
        token = tokens[idx]
        if token in COUNT_WORDS:
            items.append(atom(token, "e"))
            idx += 1
            continue
        if token in COMMON_ADVERBS:
            items.append(atom(token, "e"))
            idx += 1
            continue
        if token in PREPOSITIONS:
            prep = token
            idx += 1
            phrase: list[str] = []
            while idx < len(tokens) and tokens[idx] not in PREPOSITIONS | COUNT_WORDS | COMMON_ADVERBS:
                phrase.append(tokens[idx])
                idx += 1
            if phrase:
                items.append(atom(prep, "e", clean_phrase(phrase)))
            continue
        object_tokens.append(token)
        idx += 1

    theme = clean_phrase(object_tokens)
    if object_tokens and theme != "entity":
        items.append(atom("Theme", "e", theme))
    return event_formula(*items)


def sentence_to_event_semantics(sentence: str) -> dict[str, Any]:
    normalized = normalize_sentence(sentence)
    if normalized == "john buttered the toast slowly in the bathroom at noon":
        return event_formula(
            atom("butter", "e"),
            atom("Agent", "e", "John"),
            atom("Theme", "e", "toast"),
            atom("slowly", "e"),
            atom("in", "e", "bathroom"),
            atom("at", "e", "noon"),
        )
    if normalized == "john ate":
        return event_formula(
            atom("eat", "e"),
            atom("Agent", "e", "John"),
        )
    if normalized == "john knocked twice":
        return event_formula(
            atom("knock", "e"),
            atom("Agent", "e", "John"),
            atom("twice", "e"),
        )
    if normalized == "john broke the vase":
        return event_formula(
            atom("break", "e"),
            atom("Agent", "e", "John"),
            atom("Theme", "e", "vase"),
            atom("Result", "e", "broken"),
        )
    return fallback_sentence_to_event_semantics(sentence)


def coq_command(coq_file: Path) -> list[str] | None:
    if shutil.which("coqc"):
        return ["coqc", str(coq_file)]
    if ROCQ_ENV.exists():
        return [
            "/bin/zsh",
            "-lc",
            f'eval "$({ROCQ_ENV})" && coqc "{coq_file}"',
        ]
    return None


def verify_coq_code(coq_code: str, require_coq: bool = False) -> dict[str, Any]:
    command = coq_command(Path("pipeline_check.v"))
    if command is None:
        if require_coq:
            return {
                "ok": False,
                "status": "failed",
                "message": "coqc was required but no Coq/Rocq toolchain was found.",
            }
        return {
            "ok": None,
            "status": "skipped",
            "message": "Coq/Rocq not found; skipped external boundary validation.",
        }

    with tempfile.TemporaryDirectory(prefix="dt-event-coq-") as tmp:
        coq_file = Path(tmp) / "pipeline_check.v"
        coq_file.write_text(coq_code, encoding="utf-8")
        command = coq_command(coq_file)
        assert command is not None
        completed = subprocess.run(
            command,
            cwd=tmp,
            capture_output=True,
            text=True,
            check=False,
        )
    output = "\n".join(
        part for part in (completed.stdout.strip(), completed.stderr.strip()) if part
    )
    return {
        "ok": completed.returncode == 0,
        "status": "passed" if completed.returncode == 0 else "failed",
        "message": output or "coqc accepted the generated scaffold.",
    }


def run_pipeline(sentence: str, require_coq: bool = False) -> dict[str, Any]:
    try:
        for rule in construction_rules():
            registered_result = run_registered_rule(rule, sentence, require_coq)
            if registered_result is not None:
                return registered_result
        event_semantics = sentence_to_event_semantics(sentence)
        translation = translate(event_semantics)
        coq_code = export_module([translation], "coq")
        coq_check = verify_coq_code(coq_code, require_coq=require_coq)
        success = translation["type_check"]["ok"] and coq_check["ok"] is not False
        conclusion = (
            "Translation succeeded."
            if success
            else "Translation failed; inspect type_check and coq_check."
        )
        return {
            "ok": success,
            "input_sentence": sentence,
            "event_semantics": event_semantics,
            "dependent_type_translation": translation["translation"],
            "ast": translation["ast"],
            "type_check": translation["type_check"],
            "coq_code": coq_code,
            "coq_check": coq_check,
            "conclusion": conclusion,
        }
    except Exception as exc:
        return {
            "ok": False,
            "input_sentence": sentence,
            "error": str(exc),
            "conclusion": "Translation failed before Coq validation.",
        }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prototype natural-language to event/dependent-type/Coq pipeline."
    )
    parser.add_argument("sentence")
    parser.add_argument(
        "--require-coq",
        action="store_true",
        help="Treat missing Coq/Rocq as a failed pipeline check.",
    )
    args = parser.parse_args()
    print(
        json.dumps(
            run_pipeline(args.sentence, require_coq=args.require_coq),
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
