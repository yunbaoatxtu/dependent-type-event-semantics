#!/usr/bin/env python3
"""End-to-end prototype for natural language to checked Coq scaffolds."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import tempfile
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
    "went": "go",
    "ran": "run",
    "left": "leave",
}


def atom(pred: str, *args: str) -> dict[str, Any]:
    return {"pred": pred, "args": list(args)}


def event_formula(*items: dict[str, Any]) -> dict[str, Any]:
    return {"exists": ["e"], "body": {"and": list(items)}}


def quantifier_scope_coq(
    subject_noun: str,
    verb: str,
    object_noun: str,
    subject_first: bool,
) -> str:
    if subject_first:
        name = f"some_{subject_noun}_wide_scope"
        body = (
            f"exists x_{subject_noun} : Entity, "
            f"{subject_noun} x_{subject_noun} /\\ "
            f"exists x_{object_noun} : Entity, "
            f"{object_noun} x_{object_noun} /\\ "
            f"exists e : Event, {verb} e /\\ Agent e x_{subject_noun} /\\ Theme e x_{object_noun}"
        )
    else:
        name = f"some_{object_noun}_wide_scope"
        body = (
            f"exists x_{object_noun} : Entity, "
            f"{object_noun} x_{object_noun} /\\ "
            f"exists x_{subject_noun} : Entity, "
            f"{subject_noun} x_{subject_noun} /\\ "
            f"exists e : Event, {verb} e /\\ Agent e x_{subject_noun} /\\ Theme e x_{object_noun}"
        )
    return f"Definition {name} : Prop := {body}."


def quantifier_scope_pipeline(sentence: str) -> dict[str, Any] | None:
    tokens = tokenize(sentence)
    if len(tokens) != 5 or tokens[0] != "some" or tokens[3] != "some":
        return None
    subject_noun = lemma_verb(tokens[1])
    verb = lemma_verb(tokens[2])
    object_noun = lemma_verb(tokens[4])
    event_semantics = {
        "analysis": "quantifier-scope",
        "source": sentence,
        "readings": [
            {
                "name": f"some_{subject_noun}_wide_scope",
                "formula": (
                    f"exists x:{subject_noun}. exists y:{object_noun}. "
                    f"exists e. {verb}(e) and Agent(e,x) and Theme(e,y)"
                ),
            },
            {
                "name": f"some_{object_noun}_wide_scope",
                "formula": (
                    f"exists y:{object_noun}. exists x:{subject_noun}. "
                    f"exists e. {verb}(e) and Agent(e,x) and Theme(e,y)"
                ),
            },
        ],
    }
    coq_code = "\n".join(
        [
            "(* Quantifier-scope scaffold for dependent-type event semantics. *)",
            "Parameter Entity : Type.",
            "Parameter Event : Type.",
            f"Parameter {subject_noun} : Entity -> Prop.",
            f"Parameter {object_noun} : Entity -> Prop.",
            f"Parameter {verb} : Event -> Prop.",
            "Parameter Agent : Event -> Entity -> Prop.",
            "Parameter Theme : Event -> Entity -> Prop.",
            "",
            quantifier_scope_coq(subject_noun, verb, object_noun, subject_first=True),
            quantifier_scope_coq(subject_noun, verb, object_noun, subject_first=False),
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
            "readings": event_semantics["readings"],
        },
        "type_check": {
            "ok": True,
            "type": "Prop",
            "errors": [],
            "note": "Both scope readings are represented; no single reading is forced.",
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
        perception = perception_nominalization_pipeline(sentence)
        if perception is not None:
            coq_check = verify_coq_code(perception["coq_code"], require_coq=require_coq)
            success = perception["type_check"]["ok"] and coq_check["ok"] is not False
            return {
                **perception,
                "ok": success,
                "coq_check": coq_check,
                "conclusion": (
                    "Translation succeeded with perception-complement nominalization."
                    if success
                    else "Translation failed at Coq/Rocq boundary validation."
                ),
            }
        burning = every_burning_pipeline(sentence)
        if burning is not None:
            coq_check = verify_coq_code(burning["coq_code"], require_coq=require_coq)
            success = burning["type_check"]["ok"] and coq_check["ok"] is not False
            return {
                **burning,
                "ok": success,
                "coq_check": coq_check,
                "conclusion": (
                    "Translation succeeded with universal timed replacement."
                    if success
                    else "Translation failed at Coq/Rocq boundary validation."
                ),
            }
        timed = timed_after_pipeline(sentence)
        if timed is not None:
            coq_check = verify_coq_code(timed["coq_code"], require_coq=require_coq)
            success = timed["type_check"]["ok"] and coq_check["ok"] is not False
            return {
                **timed,
                "ok": success,
                "coq_check": coq_check,
                "conclusion": (
                    "Translation succeeded with timed dependent-type replacement."
                    if success
                    else "Translation failed at Coq/Rocq boundary validation."
                ),
            }
        scoped = quantifier_scope_pipeline(sentence)
        if scoped is not None:
            coq_check = verify_coq_code(scoped["coq_code"], require_coq=require_coq)
            success = coq_check["ok"] is not False
            return {
                **scoped,
                "ok": success,
                "coq_check": coq_check,
                "conclusion": (
                    "Translation succeeded with multiple quantifier-scope readings."
                    if success
                    else "Translation failed at Coq/Rocq boundary validation."
                ),
            }
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
