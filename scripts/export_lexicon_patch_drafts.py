#!/usr/bin/env python3
"""Export manual result-state lexicon patch drafts for one sentence."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from web.app import (  # noqa: E402
    LEXICON_PATCH_DRAFTS_SCHEMA,
    build_lexicon_patch_bundle,
    parse_patch_resolution_params,
    render_lexicon_patch_text,
)


SCHEMA_VERSION = LEXICON_PATCH_DRAFTS_SCHEMA


def write_output_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def build_patch_bundle(
    sentence: str,
    require_coq: bool = False,
    resolution_items: list[str] | None = None,
    resolve_draft_ids: list[str] | None = None,
    source_states: list[str] | None = None,
) -> dict:
    params = {
        "resolve": resolution_items or [],
        "resolve_draft_id": resolve_draft_ids or [],
        "source_state": source_states or [],
    }
    resolutions, resolution_errors = parse_patch_resolution_params(params)
    return build_lexicon_patch_bundle(
        sentence,
        require_coq=require_coq,
        resolutions=resolutions,
        resolution_errors=resolution_errors,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export human-gated STATE_LEXICON repair drafts for a sentence."
    )
    parser.add_argument("--sentence", required=True, help="Natural-language sentence to analyze.")
    parser.add_argument(
        "--require-coq",
        action="store_true",
        help="Require the same external Coq/Rocq check used by the web pipeline.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        help="Optional JSON output path. Defaults to stdout.",
    )
    parser.add_argument(
        "--patch-out",
        type=Path,
        help="Optional candidate patch-text output path for resolved drafts.",
    )
    parser.add_argument(
        "--resolve",
        action="append",
        default=[],
        metavar="DRAFT_ID=SOURCE_STATE",
        help="Resolve one draft placeholder with a chosen source state. Kept for compact shell use.",
    )
    parser.add_argument(
        "--resolve-draft-id",
        action="append",
        default=[],
        metavar="DRAFT_ID",
        help="Structured draft id to resolve; pair each occurrence with --source-state.",
    )
    parser.add_argument(
        "--source-state",
        action="append",
        default=[],
        metavar="SOURCE_STATE",
        help="Structured source state; pair each occurrence with --resolve-draft-id.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    bundle = build_patch_bundle(
        args.sentence,
        require_coq=args.require_coq,
        resolution_items=args.resolve,
        resolve_draft_ids=args.resolve_draft_id,
        source_states=args.source_state,
    )
    encoded = json.dumps(bundle, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        write_output_file(args.out, encoded)
    else:
        sys.stdout.write(encoded)
    if args.patch_out:
        write_output_file(args.patch_out, render_lexicon_patch_text(bundle))
    if bundle.get("validation_errors"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
