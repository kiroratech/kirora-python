from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any, Dict

import pytest

from kirora import UserTokens

SECRET = "sdk_secret_reference"


def decode(token: str) -> Dict[str, Any]:
    header, claims, signature = token.split(".")

    def parse(part: str) -> Any:
        return json.loads(base64.urlsafe_b64decode(part + "=" * (-len(part) % 4)))

    return {
        "header": parse(header),
        "claims": parse(claims),
        "signature": signature,
        "signed": f"{header}.{claims}",
    }


def test_signs_an_hs256_token_that_lasts_an_hour_by_default() -> None:
    before = int(time.time())
    token = decode(UserTokens.create(SECRET, "user-1"))
    assert token["header"] == {"alg": "HS256", "typ": "JWT"}
    assert token["claims"]["sub"] == "user-1"
    assert token["claims"]["iat"] >= before
    assert token["claims"]["exp"] - token["claims"]["iat"] == 3600
    expected = hmac.new(SECRET.encode(), token["signed"].encode(), hashlib.sha256).digest()
    assert token["signature"] == base64.urlsafe_b64encode(expected).rstrip(b"=").decode()
    assert "=" not in token["signature"]


def test_encodes_parts_as_compact_json_as_the_node_sdk_does(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("kirora.user_tokens._user_tokens.time.time", lambda: 1_790_000_000.5)
    token = UserTokens.create(SECRET, "user-1")
    # base64url of {"alg":"HS256","typ":"JWT"}, as Node's JSON.stringify writes it.
    assert token.split(".")[0] == "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    assert decode(token)["claims"] == {
        "sub": "user-1",
        "iat": 1_790_000_000,
        "exp": 1_790_003_600,
    }


def test_accepts_up_to_24_hours() -> None:
    token = decode(UserTokens.create(SECRET, "user-1", expires_in_seconds=86_400))
    assert token["claims"]["exp"] - token["claims"]["iat"] == 86_400


@pytest.mark.parametrize("lifetime", [86_401, 1.5, 0, -1, float("inf"), True])
def test_rejects_a_lifetime_out_of_range(lifetime: Any) -> None:
    with pytest.raises(ValueError, match="expires_in_seconds"):
        UserTokens.create(SECRET, "user-1", expires_in_seconds=lifetime)


def test_rejects_an_empty_secret_or_user_id() -> None:
    with pytest.raises(ValueError, match="token_secret can't be an empty string"):
        UserTokens.create("", "user-1")
    with pytest.raises(ValueError, match="user_id can't be an empty string"):
        UserTokens.create(SECRET, "")


def test_rejects_a_user_id_that_isnt_a_string() -> None:
    with pytest.raises(TypeError, match="user_id must be a string"):
        UserTokens.create(SECRET, 42)  # type: ignore[arg-type]
