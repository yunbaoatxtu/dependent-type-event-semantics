"""Shared surface-level type contracts for certified parser fragments."""

from __future__ import annotations

from typing import Any


SURFACE_TYPE_CONTRACT_REGISTRY_SCHEMA = "surface_type_contract_registry.v1"
SURFACE_TYPE_CONTRACT_SOURCE_MODULE = "translator/surface_type_contracts.py"
MODIFIED_TRANSITIVE_SURFACE_REGISTRY_ID = (
    "modified_transitive_adv_sequence.surface_slot_matrix"
)
TRANSITIVE_ADV_PREDICATE_TYPE = (
    "forall n : nat, ModifierSeq n -> Entity -> Entity -> PropT"
)


def modified_transitive_surface_type_contract_registry() -> dict[str, Any]:
    return {
        "schema_version": SURFACE_TYPE_CONTRACT_REGISTRY_SCHEMA,
        "source": SURFACE_TYPE_CONTRACT_SOURCE_MODULE,
        "registry_id": MODIFIED_TRANSITIVE_SURFACE_REGISTRY_ID,
        "base_family": "modified_transitive_adv_sequence",
        "axis_type_contract": {
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
        },
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
        "axes": {
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
        },
    }
