"""Shared surface-level type contracts for certified parser fragments."""

from __future__ import annotations

import copy
from typing import Any, Optional


SURFACE_TYPE_CONTRACT_REGISTRY_SCHEMA = "surface_type_contract_registry.v1"
SURFACE_TYPE_CONTRACT_ENTRY_SCHEMA = "surface_type_contract_entry.v1"
SURFACE_TYPE_CONTRACT_SOURCE_MODULE = "translator/surface_type_contracts.py"
MODIFIED_TRANSITIVE_SURFACE_REGISTRY_ID = (
    "modified_transitive_adv_sequence.surface_slot_matrix"
)
TRANSITIVE_ADV_PREDICATE_TYPE = (
    "forall n : nat, ModifierSeq n -> Entity -> Entity -> PropT"
)


def _modified_transitive_axis_type_contract() -> dict[str, Any]:
    return {
        "agents": {
            "surface_slot": "subject",
            "role_label": "Agent",
            "dependent_type": "Entity",
            "semantic_class": "Person",
        },
        "predicates": {
            "surface_slot": "verb",
            "dependent_type": TRANSITIVE_ADV_PREDICATE_TYPE,
            "semantic_class": "TransitiveAdvPredicateFamily",
            "role_frame": ["Agent", "Theme"],
            "output_type": "PropT",
        },
        "themes": {
            "surface_slot": "direct_object",
            "role_label": "Theme",
            "dependent_type": "Entity",
            "semantic_class": "VisualObject",
        },
    }


def _modified_transitive_axes() -> dict[str, list[dict[str, Any]]]:
    return {
        "agents": [
            {
                "surface": "Mary",
                "semantic": "mary",
                "dependent_type": "Entity",
                "semantic_class": "Person",
                "role_label": "Agent",
            },
            {
                "surface": "John",
                "semantic": "john",
                "dependent_type": "Entity",
                "semantic_class": "Person",
                "role_label": "Agent",
            },
        ],
        "predicates": [
            {
                "surface": "admired",
                "semantic": "admire",
                "dependent_type": TRANSITIVE_ADV_PREDICATE_TYPE,
                "semantic_class": "TransitiveAdvPredicateFamily",
                "role_frame": ["Agent", "Theme"],
                "output_type": "PropT",
            },
            {
                "surface": "photographed",
                "semantic": "photograph",
                "dependent_type": TRANSITIVE_ADV_PREDICATE_TYPE,
                "semantic_class": "TransitiveAdvPredicateFamily",
                "role_frame": ["Agent", "Theme"],
                "output_type": "PropT",
            },
        ],
        "themes": [
            {
                "surface": "painting",
                "semantic": "painting",
                "dependent_type": "Entity",
                "semantic_class": "VisualObject",
                "role_label": "Theme",
            },
            {
                "surface": "sculpture",
                "semantic": "sculpture",
                "dependent_type": "Entity",
                "semantic_class": "VisualObject",
                "role_label": "Theme",
            },
        ],
    }


def _surface_type_entries_from_axes(
    axis_type_contract: dict[str, Any],
    axes: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for slot in ("agents", "predicates", "themes"):
        contract = axis_type_contract[slot]
        for axis_entry in axes[slot]:
            entry: dict[str, Any] = {
                "schema_version": SURFACE_TYPE_CONTRACT_ENTRY_SCHEMA,
                "registry_id": MODIFIED_TRANSITIVE_SURFACE_REGISTRY_ID,
                "slot": slot,
                "surface_slot": contract["surface_slot"],
                "surface": axis_entry["surface"],
                "semantic": axis_entry["semantic"],
                "dependent_type": axis_entry["dependent_type"],
                "semantic_class": axis_entry["semantic_class"],
            }
            if "role_label" in axis_entry:
                entry["role_label"] = axis_entry["role_label"]
            if "role_frame" in axis_entry:
                entry["role_frame"] = list(axis_entry["role_frame"])
            if "output_type" in axis_entry:
                entry["output_type"] = axis_entry["output_type"]
            entries.append(entry)
    return entries


def surface_type_contract_entries_by_slot(
    registry: Optional[dict[str, Any]] = None,
) -> dict[str, list[dict[str, Any]]]:
    if registry is None:
        registry = modified_transitive_surface_type_contract_registry()
    grouped: dict[str, list[dict[str, Any]]] = {
        "agents": [],
        "predicates": [],
        "themes": [],
    }
    entries = registry.get("entries", [])
    if not isinstance(entries, list):
        return grouped
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        slot = entry.get("slot")
        if slot in grouped:
            grouped[str(slot)].append(copy.deepcopy(entry))
    return grouped


def surface_type_contract_entry(
    slot: str,
    semantic: str,
    registry: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    for entry in surface_type_contract_entries_by_slot(registry).get(slot, []):
        if entry.get("semantic") == semantic:
            return copy.deepcopy(entry)
    raise KeyError(f"unknown surface type contract entry: {slot}:{semantic}")


def surface_type_contract_axes_from_entries(
    registry: Optional[dict[str, Any]] = None,
) -> dict[str, list[dict[str, Any]]]:
    axes: dict[str, list[dict[str, Any]]] = {
        "agents": [],
        "predicates": [],
        "themes": [],
    }
    for slot, entries in surface_type_contract_entries_by_slot(registry).items():
        for entry in entries:
            axis_entry = {
                "surface": entry["surface"],
                "semantic": entry["semantic"],
                "dependent_type": entry["dependent_type"],
                "semantic_class": entry["semantic_class"],
            }
            if "role_label" in entry:
                axis_entry["role_label"] = entry["role_label"]
            if "role_frame" in entry:
                axis_entry["role_frame"] = list(entry["role_frame"])
            if "output_type" in entry:
                axis_entry["output_type"] = entry["output_type"]
            axes[slot].append(axis_entry)
    return axes


def modified_transitive_surface_type_contract_registry() -> dict[str, Any]:
    axis_type_contract = _modified_transitive_axis_type_contract()
    axes = _modified_transitive_axes()
    entries = _surface_type_entries_from_axes(axis_type_contract, axes)
    return {
        "schema_version": SURFACE_TYPE_CONTRACT_REGISTRY_SCHEMA,
        "entry_schema": SURFACE_TYPE_CONTRACT_ENTRY_SCHEMA,
        "entry_count": len(entries),
        "source": SURFACE_TYPE_CONTRACT_SOURCE_MODULE,
        "registry_id": MODIFIED_TRANSITIVE_SURFACE_REGISTRY_ID,
        "base_family": "modified_transitive_adv_sequence",
        "axis_type_contract": axis_type_contract,
        "modifier_type_contract": {
            "dependent_type": "Adv",
            "constructor_type": "Entity -> Adv",
            "accepted_semantic_roles": ["Location", "Instrument"],
            "treat_modifier_objects_as_events": False,
        },
        "time_type_contract": {
            "time_argument_type": "Time",
            "time_operator_type": "Time -> PropT -> PropT",
            "proposition_scope": True,
        },
        "entries": entries,
        "axes": axes,
    }
