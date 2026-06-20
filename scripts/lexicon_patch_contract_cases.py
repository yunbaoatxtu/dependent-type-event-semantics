"""Shared CLI/HTTP contract cases for lexicon patch draft exports."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlencode


@dataclass(frozen=True)
class LexiconPatchContractCase:
    name: str
    sentence: str
    resolution_items: tuple[str, ...] = ()
    resolve_draft_ids: tuple[str, ...] = ()
    source_states: tuple[str, ...] = ()
    expected_returncode: int = 0
    expected_error_fragments: tuple[str, ...] = ()

    def cli_args(self, *, require_coq: bool = False) -> list[str]:
        args = ["--sentence", self.sentence]
        if require_coq:
            args.append("--require-coq")
        for item in self.resolution_items:
            args.extend(["--resolve", item])
        for draft_id in self.resolve_draft_ids:
            args.extend(["--resolve-draft-id", draft_id])
        for state in self.source_states:
            args.extend(["--source-state", state])
        return args

    def query(self, *, require_coq: bool = False) -> str:
        params: list[tuple[str, str]] = [("sentence", self.sentence)]
        if require_coq:
            params.append(("require_coq", "1"))
        params.extend(("resolve", item) for item in self.resolution_items)
        params.extend(("resolve_draft_id", draft_id) for draft_id in self.resolve_draft_ids)
        params.extend(("source_state", state) for state in self.source_states)
        return urlencode(params)

    def expected_bundle(self, *, require_coq: bool = False) -> dict:
        from scripts.export_lexicon_patch_drafts import build_patch_bundle

        return build_patch_bundle(
            self.sentence,
            require_coq=require_coq,
            resolution_items=list(self.resolution_items),
            resolve_draft_ids=list(self.resolve_draft_ids),
            source_states=list(self.source_states),
        )


LEXICON_PATCH_CONTRACT_CASES = (
    LexiconPatchContractCase(
        name="empty_sentence",
        sentence="",
        expected_returncode=1,
        expected_error_fragments=("sentence is required",),
    ),
    LexiconPatchContractCase(
        name="pending_red",
        sentence="Mary painted the door red",
    ),
    LexiconPatchContractCase(
        name="resolved_red_compact",
        sentence="Mary painted the door red",
        resolution_items=("state-red--unknown_source_allowed=not_red",),
    ),
    LexiconPatchContractCase(
        name="resolved_red_structured",
        sentence="Mary painted the door red",
        resolve_draft_ids=("state-red--unknown_source_allowed",),
        source_states=("not_red",),
    ),
    LexiconPatchContractCase(
        name="duplicate_same_resolution",
        sentence="Mary painted the door red",
        resolution_items=(
            "state-red--unknown_source_allowed=not_red",
            "state-red--unknown_source_allowed=not_red",
        ),
    ),
    LexiconPatchContractCase(
        name="unknown_draft",
        sentence="Mary painted the door red",
        resolution_items=("state-blue--unknown_source_allowed=not_red",),
        expected_returncode=1,
        expected_error_fragments=("no matching lexicon patch draft",),
    ),
    LexiconPatchContractCase(
        name="conflicting_resolution",
        sentence="Mary painted the door red",
        resolution_items=("state-red--unknown_source_allowed=not_red",),
        resolve_draft_ids=("state-red--unknown_source_allowed",),
        source_states=("dry",),
        expected_returncode=1,
        expected_error_fragments=("Conflicting resolution",),
    ),
    LexiconPatchContractCase(
        name="invalid_source_state",
        sentence="Mary painted the door red",
        resolution_items=("state-red--unknown_source_allowed=intact",),
        expected_returncode=1,
        expected_error_fragments=("expected 'color_scale'",),
    ),
)
