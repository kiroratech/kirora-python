from __future__ import annotations

import math
import re
from typing import Any, Optional

_DIGITS = re.compile(r"[0-9]+")


def check_number(
    name: str,
    value: Any,
    *,
    minimum: float,
    above: bool = False,
    maximum: Optional[float] = None,
    integer: bool = False,
) -> Any:
    """Returns ``value`` if it's a finite number from ``minimum`` (exclusive if
    ``above``) to ``maximum``, and a whole number if ``integer``; otherwise raises a
    ``ValueError`` naming ``name``."""
    kinds = int if integer else (int, float)
    valid = (
        not isinstance(value, bool)
        and isinstance(value, kinds)
        and math.isfinite(value)
        and (value > minimum if above else value >= minimum)
        and (maximum is None or value <= maximum)
    )
    if not valid:
        bound = f"greater than {minimum:g}" if above else f"of at least {minimum:g}"
        if maximum is not None:
            bound = f"from {minimum:g} to {maximum:g}"
        kind = "whole number" if integer else "number"
        raise ValueError(f"{name} must be a {kind} {bound}, not {value!r}")
    return value


def parse_uint(text: Optional[str], max_digits: int) -> Optional[int]:
    """Returns ``text`` as a whole number if it's ASCII digits, at most ``max_digits`` of
    them, and None otherwise. Bounded so a huge header can't make ``int()`` raise or do
    needless work."""
    if text is None or len(text) > max_digits or not _DIGITS.fullmatch(text):
        return None
    return int(text)


def check_id(name: str, value: Any) -> str:
    """Returns ``value`` if it's a non-empty string; otherwise raises a ``TypeError`` or
    ``ValueError`` naming ``name``."""
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string, not {type(value).__name__}")
    if not value:
        raise ValueError(f"{name} can't be an empty string")
    return value
