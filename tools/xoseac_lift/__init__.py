"""Executable apparatus for a minimal lifted XOSEAC instance."""

from .lift import (
    AddEdge,
    AddState,
    EUp,
    XOSEACError,
    XOSEACInstance,
    XUp,
    apply_lift,
    apply_self_application,
    execute_using_self_representation,
    instance_from_dict,
    is_self_representation,
    operative_instance,
    operative_source_digest,
)

__all__ = [
    "AddEdge",
    "AddState",
    "EUp",
    "XOSEACError",
    "XOSEACInstance",
    "XUp",
    "apply_lift",
    "apply_self_application",
    "execute_using_self_representation",
    "instance_from_dict",
    "is_self_representation",
    "operative_instance",
    "operative_source_digest",
]
