"""The models of ``Suppressions``: plain dicts typed with ``TypedDict``s generated from the API spec."""

from ..types import (
    AddedSuppressions,
    DeletedSuppressions,
    Suppression,
    SuppressionReason,
)

__all__ = [
    "Suppression",
    "SuppressionReason",
    "AddedSuppressions",
    "DeletedSuppressions",
]
