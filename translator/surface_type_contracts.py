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
SURFACE_TYPE_CONTRACT_SLOTS = ("agents", "predicates", "themes")
MODIFIER_TYPE_CONTRACT = {
    "dependent_type": "Adv",
    "constructor_type": "Entity -> Adv",
    "accepted_semantic_roles": ["Location", "Instrument"],
    "treat_modifier_objects_as_events": False,
}
TIME_TYPE_CONTRACT = {
    "time_argument_type": "Time",
    "time_operator_type": "Time -> PropT -> PropT",
    "proposition_scope": True,
}


def _copy_contract(contract: dict[str, Any]) -> dict[str, Any]:
    return copy.deepcopy(contract)


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
    for slot in SURFACE_TYPE_CONTRACT_SLOTS:
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


def _validate_exact_contract_fields(
    errors: list[str],
    name: str,
    observed: Any,
    expected: dict[str, Any],
) -> dict[str, Any]:
    if not isinstance(observed, dict):
        errors.append(f"{name} is not an object")
        return {}
    for field, expected_value in expected.items():
        if observed.get(field) != expected_value:
            errors.append(f"{name}.{field} must be {expected_value!r}")
    for field in sorted(set(observed) - set(expected)):
        errors.append(f"{name}.{field} is not declared")
    return observed


def surface_type_contract_registry_errors(registry: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(registry, dict):
        return ["registry is not an object"]

    expected_scalars = {
        "schema_version": SURFACE_TYPE_CONTRACT_REGISTRY_SCHEMA,
        "entry_schema": SURFACE_TYPE_CONTRACT_ENTRY_SCHEMA,
        "source": SURFACE_TYPE_CONTRACT_SOURCE_MODULE,
        "registry_id": MODIFIED_TRANSITIVE_SURFACE_REGISTRY_ID,
        "base_family": "modified_transitive_adv_sequence",
    }
    for field, expected in expected_scalars.items():
        if registry.get(field) != expected:
            errors.append(f"{field} must be {expected!r}")

    axis_type_contract = registry.get("axis_type_contract")
    if not isinstance(axis_type_contract, dict):
        errors.append("axis_type_contract is not an object")
        axis_type_contract = {}
    _validate_exact_contract_fields(
        errors,
        "modifier_type_contract",
        registry.get("modifier_type_contract"),
        MODIFIER_TYPE_CONTRACT,
    )
    _validate_exact_contract_fields(
        errors,
        "time_type_contract",
        registry.get("time_type_contract"),
        TIME_TYPE_CONTRACT,
    )
    entries = registry.get("entries")
    if not isinstance(entries, list):
        errors.append("entries is not a list")
        entries = []
    axes = registry.get("axes")
    if not isinstance(axes, dict):
        errors.append("axes is not an object")
        axes = {}

    if registry.get("entry_count") != len(entries):
        errors.append("entry_count does not match entries length")

    seen_semantics: set[tuple[str, str]] = set()
    seen_surfaces: set[tuple[str, str]] = set()
    valid_slot_entries: list[dict[str, Any]] = []

    for slot in SURFACE_TYPE_CONTRACT_SLOTS:
        contract = axis_type_contract.get(slot)
        if not isinstance(contract, dict):
            errors.append(f"axis_type_contract.{slot} is missing")
            continue
        for field in ("surface_slot", "dependent_type", "semantic_class"):
            if not isinstance(contract.get(field), str) or not contract.get(field):
                errors.append(f"axis_type_contract.{slot}.{field} must be a string")
        if slot in ("agents", "themes"):
            if not isinstance(contract.get("role_label"), str) or not contract.get(
                "role_label"
            ):
                errors.append(f"axis_type_contract.{slot}.role_label must be a string")
        if slot == "predicates":
            if not isinstance(contract.get("role_frame"), list) or not all(
                isinstance(role, str) and role for role in contract.get("role_frame", [])
            ):
                errors.append(
                    "axis_type_contract.predicates.role_frame must be a string list"
                )
            if not isinstance(contract.get("output_type"), str) or not contract.get(
                "output_type"
            ):
                errors.append("axis_type_contract.predicates.output_type must be a string")

    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            errors.append(f"entry[{index}] is not an object")
            continue
        slot = entry.get("slot")
        surface = entry.get("surface")
        semantic = entry.get("semantic")
        entry_label = f"entry[{index}]"
        if isinstance(slot, str) and isinstance(semantic, str) and semantic:
            entry_label = f"entry {slot}:{semantic}"
        if entry.get("schema_version") != SURFACE_TYPE_CONTRACT_ENTRY_SCHEMA:
            errors.append(f"{entry_label} schema_version is invalid")
        if entry.get("registry_id") != MODIFIED_TRANSITIVE_SURFACE_REGISTRY_ID:
            errors.append(f"{entry_label} registry_id is invalid")
        if slot not in SURFACE_TYPE_CONTRACT_SLOTS:
            errors.append(f"{entry_label} slot is invalid")
            continue
        contract = axis_type_contract.get(slot, {})
        if entry.get("surface_slot") != contract.get("surface_slot"):
            errors.append(f"{entry_label} surface_slot does not match axis contract")
        for field in ("surface", "semantic", "dependent_type", "semantic_class"):
            if not isinstance(entry.get(field), str) or not entry.get(field):
                errors.append(f"{entry_label} {field} must be a string")
        if isinstance(semantic, str) and semantic:
            semantic_key = (slot, semantic)
            if semantic_key in seen_semantics:
                errors.append(f"duplicate entry semantic {slot}:{semantic}")
            seen_semantics.add(semantic_key)
        if isinstance(surface, str) and surface:
            surface_key = (slot, surface.lower())
            if surface_key in seen_surfaces:
                errors.append(f"duplicate entry surface {slot}:{surface}")
            seen_surfaces.add(surface_key)
        if entry.get("dependent_type") != contract.get("dependent_type"):
            errors.append(f"{entry_label} dependent_type does not match axis contract")
        if entry.get("semantic_class") != contract.get("semantic_class"):
            errors.append(f"{entry_label} semantic_class does not match axis contract")
        if slot in ("agents", "themes"):
            if entry.get("role_label") != contract.get("role_label"):
                errors.append(f"{entry_label} role_label does not match axis contract")
        if slot == "predicates":
            if entry.get("role_frame") != contract.get("role_frame"):
                errors.append(f"{entry_label} role_frame does not match axis contract")
            if entry.get("output_type") != contract.get("output_type"):
                errors.append(f"{entry_label} output_type does not match axis contract")
        valid_slot_entries.append(entry)

    for slot in SURFACE_TYPE_CONTRACT_SLOTS:
        if not isinstance(axes.get(slot), list):
            errors.append(f"axes.{slot} is not a list")
    unknown_axes = sorted(set(axes) - set(SURFACE_TYPE_CONTRACT_SLOTS))
    for slot in unknown_axes:
        errors.append(f"axes.{slot} is not a declared slot")

    if len(valid_slot_entries) == len(entries):
        try:
            reconstructed_axes = surface_type_contract_axes_from_entries(registry)
        except (KeyError, TypeError):
            errors.append("axes cannot be reconstructed from entries")
        else:
            if axes != reconstructed_axes:
                errors.append("axes do not match entries")
    return errors


def validate_surface_type_contract_registry(registry: Any) -> None:
    errors = surface_type_contract_registry_errors(registry)
    if errors:
        raise ValueError(
            "surface type contract registry invalid: " + "; ".join(errors)
        )


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
    registry = {
        "schema_version": SURFACE_TYPE_CONTRACT_REGISTRY_SCHEMA,
        "entry_schema": SURFACE_TYPE_CONTRACT_ENTRY_SCHEMA,
        "entry_count": len(entries),
        "source": SURFACE_TYPE_CONTRACT_SOURCE_MODULE,
        "registry_id": MODIFIED_TRANSITIVE_SURFACE_REGISTRY_ID,
        "base_family": "modified_transitive_adv_sequence",
        "axis_type_contract": axis_type_contract,
        "modifier_type_contract": _copy_contract(MODIFIER_TYPE_CONTRACT),
        "time_type_contract": _copy_contract(TIME_TYPE_CONTRACT),
        "entries": entries,
        "axes": axes,
    }
    validate_surface_type_contract_registry(registry)
    return registry
