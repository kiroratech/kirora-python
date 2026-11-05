from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any, Dict

from .._validation import check_id, check_number

__all__ = ["UserTokens"]

DEFAULT_LIFETIME_SECONDS = 60 * 60
MAX_LIFETIME_SECONDS = 24 * 60 * 60


class UserTokens:
    """Signs users in to Kirora's web and mobile SDKs, with tokens your server creates."""

    @staticmethod
    def create(token_secret: str, user_id: str, *, expires_in_seconds: int = DEFAULT_LIFETIME_SECONDS) -> str:
        """Creates a token that signs a user in to Kirora's web and mobile SDKs.

        Sign it on your server with the SDK token secret from Developer → SDK in the
        dashboard, and keep the secret there. ``user_id`` is your own id for the signed-in
        user. Tokens last an hour unless ``expires_in_seconds`` says otherwise: a whole number
        from 1 to 86,400 (24 hours). An empty secret or user id, or any other lifetime, raises
        a ``ValueError``.
        """
        check_id("token_secret", token_secret)
        check_id("user_id", user_id)
        check_number(
            "expires_in_seconds", expires_in_seconds, minimum=1, maximum=MAX_LIFETIME_SECONDS, integer=True
        )
        issued_at = int(time.time())
        signing_input = (
            f"{_encode({'alg': 'HS256', 'typ': 'JWT'})}."
            f"{_encode({'sub': user_id, 'iat': issued_at, 'exp': issued_at + expires_in_seconds})}"
        )
        signature = hmac.new(token_secret.encode(), signing_input.encode(), hashlib.sha256).digest()
        return f"{signing_input}.{_base64url(signature)}"


def _encode(part: Dict[str, Any]) -> str:
    # Compact, as JavaScript's JSON.stringify writes it, so every SDK signs the same bytes.
    return _base64url(json.dumps(part, separators=(",", ":"), ensure_ascii=False).encode())


def _base64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()
