#!/usr/bin/env python3
"""Small stdlib web demo for the translation verification pipeline."""

from __future__ import annotations

import argparse
import html
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from translator.natural_language_pipeline import run_pipeline


DEFAULT_SENTENCE = "John knocked twice"
FAILURE_STAGE_LABELS = {
    "input": "empty input",
    "parsing": "natural-language parsing",
    "type_check": "dependent-type checking",
    "construction_hygiene": "construction hygiene",
    "coq_check": "Coq/Rocq validation",
}
FAILURE_STAGE_HINTS = {
    "input": "Enter a non-empty sentence.",
    "parsing": "Try a sentence with at least a subject and a predicate.",
    "type_check": "Inspect the dependent-type AST and type-check errors.",
    "construction_hygiene": "Remove forbidden construction fragments from generated Coq.",
    "coq_check": "Check the generated Coq scaffold and local Coq/Rocq toolchain.",
}
FAILURE_STAGE_ACTIONS = {
    "input": [
        {
            "kind": "edit_input",
            "label": "Enter a sentence",
            "detail": "Type a non-empty natural-language sentence before analyzing.",
        }
    ],
    "parsing": [
        {
            "kind": "revise_sentence",
            "label": "Add subject and predicate",
            "detail": "Use a sentence with at least a recognizable subject and predicate.",
        }
    ],
    "type_check": [
        {
            "kind": "inspect_ast",
            "label": "Inspect typed AST",
            "detail": "Compare the generated AST with the dependent-type checker errors.",
        }
    ],
    "construction_hygiene": [
        {
            "kind": "inspect_coq",
            "label": "Remove forbidden fragments",
            "detail": "Regenerate Coq without fragments banned by the matched construction rule.",
        }
    ],
    "coq_check": [
        {
            "kind": "inspect_coq",
            "label": "Check Coq/Rocq scaffold",
            "detail": "Inspect declarations and verify the local Coq/Rocq toolchain is available.",
        }
    ],
}


def analyze_sentence(sentence: str, require_coq: bool = False) -> dict[str, Any]:
    sentence = sentence.strip()
    if not sentence:
        result = {
            "ok": False,
            "input_sentence": sentence,
            "error": "Please enter a sentence.",
            "conclusion": "Translation failed before parsing.",
        }
        return add_diagnostics(result)
    return add_diagnostics(run_pipeline(sentence, require_coq=require_coq))


def check_status(ok: Any) -> str:
    if ok is True:
        return "passed"
    if ok is None:
        return "skipped"
    return "failed"


def recovery_actions_for(failure_stage: str | None) -> list[dict[str, str]]:
    return [dict(action) for action in FAILURE_STAGE_ACTIONS.get(failure_stage, [])]


def state_lexicon_patch_line(state: str, scale: str, default_source_state: str) -> str:
    return (
        f"{state!r}: StateLexiconEntry("
        f"{scale!r}, default_source_state={default_source_state!r}),"
    )


def lexicon_entry_draft(policy: str, state: str, scale: str) -> dict[str, Any]:
    default_source_state = "<choose_source_state>"
    return {
        "state": state,
        "scale": scale,
        "default_source_state": default_source_state,
        "allow_unknown_source": False,
        "current_source_policy": policy,
        "source_policy_after_update": "lexical_prestate",
        "requires_human_choice": True,
        "placeholder_fields": ["default_source_state"],
        "can_auto_apply": False,
        "state_lexicon_patch_line": state_lexicon_patch_line(
            state,
            scale,
            default_source_state,
        ),
    }


def warning_action_for_entry(policy: str, state: str, scale: str) -> dict[str, Any] | None:
    if policy == "unknown_source_allowed":
        return {
            "kind": "add_state_prestate",
            "label": "Add lexical pre-state",
            "detail": (
                f"Choose a contextually justified source state for {state} on {scale}, "
                "or keep unknown_state when the source is genuinely underspecified."
            ),
            "lexicon_entry_draft": lexicon_entry_draft(policy, state, scale),
        }
    if policy == "derived_scale_no_known_prestate":
        return {
            "kind": "register_state_lexicon_entry",
            "label": "Register result state",
            "detail": (
                f"Add {state} to STATE_LEXICON with a stable scale and, if justified, "
                "a default_source_state."
            ),
            "lexicon_entry_draft": lexicon_entry_draft(policy, state, scale),
        }
    if policy == "source_state_only":
        return {
            "kind": "license_state_as_target",
            "label": "License target state",
            "detail": (
                f"Decide whether {state} can be a result target on {scale}; if so, "
                "add a default source state."
            ),
            "lexicon_entry_draft": lexicon_entry_draft(policy, state, scale),
        }
    return None


def result_state_warning_for_entry(entry: dict[str, Any]) -> dict[str, Any] | None:
    policy = str(entry.get("source_policy", ""))
    state = str(entry.get("state", ""))
    scale = str(entry.get("scale", ""))
    if policy == "unknown_source_allowed":
        return {
            "kind": "unknown_result_source",
            "state": state,
            "scale": scale,
            "message": (
                f"Result state {state} has no unique lexical pre-state; "
                "source remains unknown_state."
            ),
            "suggested_action": warning_action_for_entry(policy, state, scale),
        }
    if policy == "derived_scale_no_known_prestate":
        return {
            "kind": "derived_result_scale",
            "state": state,
            "scale": scale,
            "message": (
                f"Result state {state} uses a derived scale without a known lexical "
                "pre-state; source remains unknown_state."
            ),
            "suggested_action": warning_action_for_entry(policy, state, scale),
        }
    if policy == "source_state_only":
        return {
            "kind": "source_state_used_as_target",
            "state": state,
            "scale": scale,
            "message": (
                f"Result state {state} is currently licensed only as a source state; "
                "source remains unknown_state."
            ),
            "suggested_action": warning_action_for_entry(policy, state, scale),
        }
    return None


def result_state_warnings(result: dict[str, Any]) -> list[dict[str, Any]]:
    warnings = []
    for entry in result.get("result_state_lexicon", []):
        warning = result_state_warning_for_entry(entry)
        if warning is not None:
            warnings.append(warning)
    return warnings


def lexicon_patch_drafts(result: dict[str, Any]) -> list[dict[str, Any]]:
    diagnostics = result.get("diagnostics", {})
    warnings = diagnostics.get("warnings") or result_state_warnings(result)
    drafts = []
    seen = set()
    for warning in warnings:
        action = warning.get("suggested_action") or {}
        draft = action.get("lexicon_entry_draft")
        if not draft:
            continue
        key = (
            draft.get("state"),
            draft.get("scale"),
            draft.get("current_source_policy"),
            draft.get("source_policy_after_update"),
        )
        if key in seen:
            continue
        seen.add(key)
        drafts.append(dict(draft))
    return drafts


def build_diagnostics(result: dict[str, Any]) -> dict[str, Any]:
    type_check = result.get("type_check", {})
    construction_hygiene = result.get("construction_hygiene", {})
    coq_check = result.get("coq_check", {})
    stages = {
        "type_check": check_status(type_check.get("ok")) if type_check else "not_applicable",
        "construction_hygiene": (
            check_status(construction_hygiene.get("ok"))
            if construction_hygiene
            else "not_applicable"
        ),
        "coq_check": check_status(coq_check.get("ok")) if coq_check else "not_applicable",
    }
    if result.get("ok"):
        summary = "translation verified"
        failure_stage = None
    elif construction_hygiene and construction_hygiene.get("ok") is False:
        summary = "construction hygiene failed"
        failure_stage = "construction_hygiene"
    elif coq_check and coq_check.get("ok") is False:
        summary = "coq validation failed"
        failure_stage = "coq_check"
    elif type_check and type_check.get("ok") is False:
        summary = "type check failed"
        failure_stage = "type_check"
    elif not result.get("input_sentence", "").strip():
        summary = "translation failed"
        failure_stage = "input"
    else:
        summary = "translation failed"
        failure_stage = "parsing"
    recovery_hint = FAILURE_STAGE_HINTS.get(failure_stage) if failure_stage else None
    return {
        "summary": summary,
        "failure_stage": failure_stage,
        "recovery_hint": recovery_hint,
        "recovery_actions": recovery_actions_for(failure_stage),
        "stages": stages,
        "warnings": result_state_warnings(result),
    }


def add_diagnostics(result: dict[str, Any]) -> dict[str, Any]:
    enriched = {**result}
    enriched.setdefault("result_state_lexicon", [])
    enriched["diagnostics"] = build_diagnostics(enriched)
    enriched["lexicon_patch_drafts"] = lexicon_patch_drafts(enriched)
    return enriched


def compact_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def status_label(result: dict[str, Any]) -> str:
    if result.get("ok"):
        warnings = result.get("diagnostics", {}).get("warnings", [])
        coq = result.get("coq_check", {})
        if coq.get("status") == "skipped":
            if warnings:
                return "Internally checked with warnings; Coq/Rocq skipped"
            return "Internally checked; Coq/Rocq skipped"
        if warnings:
            return "Translation verified with warnings"
        return "Translation verified"
    return "Needs attention"


def status_detail(result: dict[str, Any]) -> str:
    warnings = result.get("diagnostics", {}).get("warnings", [])
    failure_stage = result.get("diagnostics", {}).get("failure_stage")
    if not failure_stage:
        conclusion = result.get("conclusion", "")
        if warnings:
            warning_text = "; ".join(warning["message"] for warning in warnings)
            if conclusion:
                return f"{conclusion} Warnings: {warning_text}"
            return f"Warnings: {warning_text}"
        return conclusion
    label = FAILURE_STAGE_LABELS.get(failure_stage, failure_stage)
    conclusion = result.get("conclusion", "")
    hint = result.get("diagnostics", {}).get("recovery_hint")
    suffix = f" Suggested next step: {hint}" if hint else ""
    if conclusion:
        return f"{conclusion} Failure stage: {label}.{suffix}"
    return f"Failure stage: {label}.{suffix}"


def construction_rule_summary(result: dict[str, Any]) -> str:
    rule = result.get("construction_rule")
    if not rule:
        return "No registered construction rule matched; fallback or general translator path was used."
    hygiene = result.get("construction_hygiene", {})
    forbidden = rule.get("forbidden_coq_fragments", [])
    hygiene_status = check_status(hygiene.get("ok")) if hygiene else "not_applicable"
    lines = [
        f"id: {rule.get('id', '')}",
        f"label: {rule.get('label', '')}",
        f"phenomenon: {rule.get('phenomenon', '')}",
        f"hygiene: {hygiene_status}",
        "hygiene policy:",
    ]
    if forbidden:
        lines.extend(f"- {fragment}" for fragment in forbidden)
    else:
        lines.append("- none")
    found = hygiene.get("found_forbidden_fragments", [])
    lines.append("found forbidden fragments:")
    if found:
        lines.extend(f"- {fragment}" for fragment in found)
    else:
        lines.append("- none")
    return "\n".join(lines)


def css_token(value: str) -> str:
    return "".join(char if char.isalnum() or char in {"-", "_"} else "-" for char in value)


def next_steps_panel(result: dict[str, Any]) -> str:
    actions = result.get("diagnostics", {}).get("recovery_actions", [])
    if not actions:
        body = '<p class="next-step-empty">No recovery actions needed.</p>'
    else:
        items = []
        for action in actions:
            kind = action.get("kind", "")
            label = action.get("label", "")
            detail = action.get("detail", "")
            kind_class = css_token(kind)
            items.append(
                '<li '
                f'class="next-step next-step--{html.escape(kind_class)}" '
                f'data-action-kind="{html.escape(kind)}">'
                f'<strong>{html.escape(label)}</strong>'
                f'<code>{html.escape(kind)}</code>'
                f'<p>{html.escape(detail)}</p>'
                "</li>"
            )
        body = '<ul class="next-step-list">' + "".join(items) + "</ul>"
    return (
        '<section class="panel next-steps-panel">'
        "<h2>Next Steps</h2>"
        f'<div class="next-steps">{body}</div>'
        "</section>"
    )


def semantic_warnings_panel(result: dict[str, Any]) -> str:
    warnings = result.get("diagnostics", {}).get("warnings", [])
    if not warnings:
        body = '<p class="semantic-warning-empty">No semantic warnings.</p>'
    else:
        items = []
        for warning in warnings:
            kind = str(warning.get("kind", ""))
            state = str(warning.get("state", ""))
            scale = str(warning.get("scale", ""))
            message = str(warning.get("message", ""))
            action = warning.get("suggested_action") or {}
            action_kind = str(action.get("kind", ""))
            action_label = str(action.get("label", ""))
            action_detail = str(action.get("detail", ""))
            draft = action.get("lexicon_entry_draft") or {}
            draft_html = ""
            if draft:
                draft_html = (
                    '<dl class="semantic-warning-draft">'
                    f'<dt>draft state</dt><dd>{html.escape(str(draft.get("state", "")))}</dd>'
                    f'<dt>draft scale</dt><dd>{html.escape(str(draft.get("scale", "")))}</dd>'
                    '<dt>draft source</dt>'
                    f'<dd>{html.escape(str(draft.get("default_source_state", "")))}</dd>'
                    '<dt>after policy</dt>'
                    f'<dd>{html.escape(str(draft.get("source_policy_after_update", "")))}</dd>'
                    '</dl>'
                )
            action_html = ""
            if action_kind or action_label or action_detail:
                action_class = css_token(action_kind)
                action_html = (
                    '<div '
                    f'class="semantic-warning-action semantic-warning-action--{html.escape(action_class)}" '
                    f'data-warning-action-kind="{html.escape(action_kind)}">'
                    f'<strong>{html.escape(action_label)}</strong>'
                    f'<code>{html.escape(action_kind)}</code>'
                    f'<p>{html.escape(action_detail)}</p>'
                    f"{draft_html}"
                    '</div>'
                )
            kind_class = css_token(kind)
            items.append(
                '<li '
                f'class="semantic-warning semantic-warning--{html.escape(kind_class)}" '
                f'data-warning-kind="{html.escape(kind)}">'
                f'<strong>{html.escape(kind)}</strong>'
                '<dl>'
                f'<dt>state</dt><dd>{html.escape(state)}</dd>'
                f'<dt>scale</dt><dd>{html.escape(scale)}</dd>'
                '</dl>'
                f'<p>{html.escape(message)}</p>'
                f"{action_html}"
                "</li>"
            )
        body = '<ul class="semantic-warning-list">' + "".join(items) + "</ul>"
    return (
        '<section class="panel semantic-warnings-panel">'
        "<h2>Semantic Warnings</h2>"
        f'<div class="semantic-warnings">{body}</div>'
        "</section>"
    )


def result_state_lexicon_panel(result: dict[str, Any]) -> str:
    entries = result.get("result_state_lexicon", [])
    if not entries:
        body = '<p class="lexicon-empty">No result states detected.</p>'
    else:
        rows = []
        for entry in entries:
            state = str(entry.get("state", ""))
            scale = str(entry.get("scale", ""))
            source = entry.get("default_source_state")
            source_text = str(source) if source is not None else "unknown_state"
            policy = str(entry.get("source_policy", ""))
            warning = result_state_warning_for_entry(entry)
            warning_html = (
                f'<p class="lexicon-warning">{html.escape(warning["message"])}</p>'
                if warning
                else ""
            )
            item_class = "lexicon-entry lexicon-entry--warning" if warning else "lexicon-entry"
            rows.append(
                f'<li class="{item_class}">'
                f'<strong>{html.escape(state)}</strong>'
                '<dl>'
                f'<dt>scale</dt><dd>{html.escape(scale)}</dd>'
                f'<dt>source</dt><dd>{html.escape(source_text)}</dd>'
                f'<dt>policy</dt><dd>{html.escape(policy)}</dd>'
                '</dl>'
                f"{warning_html}"
                '</li>'
            )
        body = '<ul class="lexicon-list">' + "".join(rows) + "</ul>"
    return (
        '<section class="panel result-lexicon-panel">'
        "<h2>Result State Lexicon</h2>"
        f'<div class="result-lexicon">{body}</div>'
        "</section>"
    )


def lexicon_patch_drafts_panel(result: dict[str, Any]) -> str:
    drafts = result.get("lexicon_patch_drafts", [])
    if not drafts:
        body = '<p class="lexicon-draft-empty">No lexicon patch drafts.</p>'
    else:
        rows = []
        for draft in drafts:
            state = str(draft.get("state", ""))
            scale = str(draft.get("scale", ""))
            source = str(draft.get("default_source_state", ""))
            current_policy = str(draft.get("current_source_policy", ""))
            next_policy = str(draft.get("source_policy_after_update", ""))
            patch_line = str(draft.get("state_lexicon_patch_line", ""))
            auto_apply = "yes" if draft.get("can_auto_apply") else "no"
            placeholders = ", ".join(map(str, draft.get("placeholder_fields", []))) or "none"
            rows.append(
                '<li '
                'class="lexicon-draft" '
                f'data-draft-state="{html.escape(state)}" '
                f'data-draft-current-policy="{html.escape(current_policy)}">'
                f'<strong>{html.escape(state)}</strong>'
                '<dl>'
                f'<dt>scale</dt><dd>{html.escape(scale)}</dd>'
                f'<dt>source</dt><dd>{html.escape(source)}</dd>'
                f'<dt>current</dt><dd>{html.escape(current_policy)}</dd>'
                f'<dt>after</dt><dd>{html.escape(next_policy)}</dd>'
                f'<dt>auto apply</dt><dd>{html.escape(auto_apply)}</dd>'
                f'<dt>placeholders</dt><dd>{html.escape(placeholders)}</dd>'
                f'<dt>entry</dt><dd>{html.escape(patch_line)}</dd>'
                '</dl>'
                '</li>'
            )
        body = '<ul class="lexicon-draft-list">' + "".join(rows) + "</ul>"
    return (
        '<section class="panel lexicon-drafts-panel">'
        "<h2>Lexicon Patch Drafts</h2>"
        f'<div class="lexicon-drafts">{body}</div>'
        "</section>"
    )


def panel(title: str, body: str) -> str:
    return (
        '<section class="panel">'
        f"<h2>{html.escape(title)}</h2>"
        f"<pre>{html.escape(body)}</pre>"
        "</section>"
    )


def render_page(sentence: str = DEFAULT_SENTENCE, require_coq: bool = False) -> str:
    result = analyze_sentence(sentence, require_coq=require_coq)
    event_semantics = compact_json(result.get("event_semantics", result.get("error", "")))
    dependent = result.get("dependent_type_translation", result.get("error", ""))
    ast = compact_json(result.get("ast", {}))
    result_lexicon = compact_json(result.get("result_state_lexicon", []))
    patch_drafts = compact_json(result.get("lexicon_patch_drafts", []))
    construction = construction_rule_summary(result)
    diagnostics = compact_json(result.get("diagnostics", {}))
    coq_code = result.get("coq_code", "")
    coq_check = compact_json(result.get("coq_check", {}))
    checked = " checked" if require_coq else ""
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Dependent-Type Event Semantics</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #17212b;
      --muted: #5d6b78;
      --line: #d8dee6;
      --surface: #f7f9fb;
      --accent: #0f766e;
      --accent-soft: #e6f3f1;
      --warning: #92400e;
      --warning-soft: #fffbeb;
      --error: #9f1239;
      --error-soft: #fff1f2;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: var(--ink);
      background: #ffffff;
    }}
    main {{
      max-width: 1180px;
      margin: 0 auto;
      padding: 28px 20px 40px;
    }}
    header {{
      display: flex;
      justify-content: space-between;
      gap: 20px;
      align-items: end;
      border-bottom: 1px solid var(--line);
      padding-bottom: 16px;
      margin-bottom: 20px;
    }}
    h1 {{
      font-size: 24px;
      line-height: 1.2;
      margin: 0 0 6px;
      letter-spacing: 0;
    }}
    p {{
      margin: 0;
      color: var(--muted);
      line-height: 1.45;
    }}
    form {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto auto;
      gap: 10px;
      align-items: center;
      margin: 20px 0;
    }}
    input[type="text"] {{
      width: 100%;
      min-height: 42px;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 9px 11px;
      font-size: 15px;
    }}
    label {{
      display: inline-flex;
      gap: 7px;
      align-items: center;
      color: var(--muted);
      white-space: nowrap;
      font-size: 14px;
    }}
    button {{
      min-height: 42px;
      border: 0;
      border-radius: 6px;
      background: var(--accent);
      color: white;
      padding: 0 16px;
      font-weight: 650;
      cursor: pointer;
    }}
    .status {{
      border: 1px solid {('#fecdd3' if not result.get('ok') else '#b7ded8')};
      background: {('var(--error-soft)' if not result.get('ok') else 'var(--accent-soft)')};
      color: {('var(--error)' if not result.get('ok') else '#115e59')};
      border-radius: 6px;
      padding: 12px 14px;
      margin-bottom: 18px;
      font-weight: 650;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 14px;
    }}
    .panel {{
      border: 1px solid var(--line);
      border-radius: 6px;
      background: var(--surface);
      min-width: 0;
      overflow: hidden;
    }}
    .next-steps {{
      padding: 12px;
    }}
    .result-lexicon {{
      padding: 12px;
    }}
    .semantic-warnings {{
      padding: 12px;
    }}
    .lexicon-drafts {{
      padding: 12px;
    }}
    .next-step-list {{
      list-style: none;
      margin: 0;
      padding: 0;
      display: grid;
      gap: 10px;
    }}
    .semantic-warning-list {{
      list-style: none;
      margin: 0;
      padding: 0;
      display: grid;
      gap: 10px;
    }}
    .lexicon-draft-list {{
      list-style: none;
      margin: 0;
      padding: 0;
      display: grid;
      gap: 10px;
    }}
    .next-step {{
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #ffffff;
      padding: 10px;
      display: grid;
      gap: 6px;
    }}
    .next-step strong {{
      font-size: 14px;
    }}
    .next-step code {{
      width: fit-content;
      color: var(--muted);
      font: 12px/1.35 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    }}
    .next-step p,
    .next-step-empty,
    .semantic-warning-empty,
    .lexicon-empty,
    .lexicon-draft-empty {{
      margin: 0;
      color: var(--muted);
      line-height: 1.45;
    }}
    .semantic-warning {{
      border-left: 3px solid var(--warning);
      background: var(--warning-soft);
      padding: 9px 10px;
      display: grid;
      gap: 6px;
    }}
    .semantic-warning strong {{
      font-size: 13px;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    }}
    .semantic-warning dl {{
      display: grid;
      grid-template-columns: minmax(56px, auto) minmax(0, 1fr);
      gap: 4px 10px;
      margin: 0;
      font-size: 13px;
    }}
    .semantic-warning dt {{
      color: var(--muted);
    }}
    .semantic-warning dd {{
      margin: 0;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      word-break: break-word;
    }}
    .semantic-warning p {{
      margin: 0;
      color: var(--warning);
      line-height: 1.45;
      font-size: 13px;
    }}
    .semantic-warning-action {{
      border-top: 1px solid #fde68a;
      padding-top: 7px;
      display: grid;
      gap: 4px;
    }}
    .semantic-warning-action strong {{
      font-size: 13px;
      font-family: inherit;
    }}
    .semantic-warning-action code {{
      width: fit-content;
      color: var(--muted);
      font: 12px/1.35 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    }}
    .semantic-warning-action p {{
      color: var(--muted);
    }}
    .semantic-warning-action .semantic-warning-draft {{
      margin-top: 2px;
    }}
    .lexicon-list {{
      list-style: none;
      margin: 0;
      padding: 0;
      display: grid;
      gap: 10px;
    }}
    .lexicon-entry {{
      border-left: 3px solid var(--accent);
      background: #ffffff;
      padding: 9px 10px;
    }}
    .lexicon-entry--warning {{
      border-left-color: var(--warning);
      background: var(--warning-soft);
    }}
    .lexicon-entry strong {{
      display: block;
      margin-bottom: 6px;
      font-size: 14px;
    }}
    .lexicon-entry dl {{
      display: grid;
      grid-template-columns: minmax(72px, auto) minmax(0, 1fr);
      gap: 4px 10px;
      margin: 0;
      font-size: 13px;
    }}
    .lexicon-entry dt {{
      color: var(--muted);
    }}
    .lexicon-entry dd {{
      margin: 0;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      word-break: break-word;
    }}
    .lexicon-warning {{
      margin-top: 8px;
      color: var(--warning);
      font-size: 13px;
    }}
    .lexicon-draft {{
      border-left: 3px solid var(--warning);
      background: #ffffff;
      padding: 9px 10px;
    }}
    .lexicon-draft strong {{
      display: block;
      margin-bottom: 6px;
      font-size: 14px;
    }}
    .lexicon-draft dl {{
      display: grid;
      grid-template-columns: minmax(72px, auto) minmax(0, 1fr);
      gap: 4px 10px;
      margin: 0;
      font-size: 13px;
    }}
    .lexicon-draft dt {{
      color: var(--muted);
    }}
    .lexicon-draft dd {{
      margin: 0;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      word-break: break-word;
    }}
    h2 {{
      font-size: 14px;
      margin: 0;
      padding: 10px 12px;
      border-bottom: 1px solid var(--line);
      background: #ffffff;
      letter-spacing: 0;
    }}
    pre {{
      margin: 0;
      padding: 12px;
      min-height: 132px;
      max-height: 360px;
      overflow: auto;
      white-space: pre-wrap;
      word-break: break-word;
      font: 13px/1.45 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    }}
    @media (max-width: 760px) {{
      header, form, .grid {{ grid-template-columns: 1fr; display: grid; }}
      label {{ white-space: normal; }}
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <div>
        <h1>Dependent-Type Event Semantics</h1>
        <p>Natural-language input to event semantics, dependent-type translation, and Coq/Rocq validation.</p>
      </div>
    </header>
    <form method="get" action="/">
      <input name="sentence" type="text" value="{html.escape(sentence)}" aria-label="Sentence">
      <label><input name="require_coq" type="checkbox" value="1"{checked}> require Coq/Rocq</label>
      <button type="submit">Analyze</button>
    </form>
    <div class="status">{html.escape(status_label(result))}: {html.escape(status_detail(result))}</div>
    <div class="grid">
      {panel("Event Semantics", event_semantics)}
      {panel("Dependent-Type Translation", dependent)}
      {result_state_lexicon_panel(result)}
      {panel("Diagnostics", diagnostics)}
      {semantic_warnings_panel(result)}
      {lexicon_patch_drafts_panel(result)}
      {next_steps_panel(result)}
      {panel("Construction Rule", construction)}
      {panel("AST", ast)}
      {panel("Result State Lexicon JSON", result_lexicon)}
      {panel("Lexicon Patch Drafts JSON", patch_drafts)}
      {panel("Coq/Rocq Check", coq_check)}
      {panel("Generated Coq", coq_code)}
    </div>
  </main>
</body>
</html>
"""


class PipelineHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/analyze":
            self.write_json_response(self.handle_api(parsed.query))
            return
        if parsed.path not in {"/", ""}:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        params = parse_qs(parsed.query)
        sentence = params.get("sentence", [DEFAULT_SENTENCE])[0]
        require_coq = params.get("require_coq", ["0"])[0] == "1"
        self.write_html_response(render_page(sentence, require_coq=require_coq))

    def handle_api(self, query: str) -> dict[str, Any]:
        params = parse_qs(query)
        sentence = params.get("sentence", [""])[0]
        require_coq = params.get("require_coq", ["0"])[0] == "1"
        return analyze_sentence(sentence, require_coq=require_coq)

    def write_html_response(self, content: str) -> None:
        encoded = content.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def write_json_response(self, content: dict[str, Any]) -> None:
        encoded = compact_json(content).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local web demo.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument(
        "--render-static",
        type=Path,
        help="Write a static HTML preview instead of starting a server.",
    )
    parser.add_argument(
        "--sentence",
        default=DEFAULT_SENTENCE,
        help="Sentence used for --render-static output.",
    )
    args = parser.parse_args()
    if args.render_static:
        args.render_static.write_text(render_page(args.sentence), encoding="utf-8")
        print(f"Wrote {args.render_static}")
        return
    server = ThreadingHTTPServer((args.host, args.port), PipelineHandler)
    print(f"Serving http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
