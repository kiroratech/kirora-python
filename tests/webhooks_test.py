from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any, Callable, Optional

import pytest

from kirora import KiroraWebhookVerificationError, Webhooks

# The same reference values as the Node SDK's tests, so both SDKs agree on them.
SECRET = "whsec_reference"
BODY = '{"eventId":"evt_1","type":"message.bounced"}'
NOW = 1_790_000_000.0
TIMESTAMP = str(int(NOW))
SIGNATURE = "sha256=786e82a809095e8f9308254ed5517ffda803370d60f531e5ac9aae4f9b95c841"


def sign(timestamp: str, body: str, secret: str = SECRET) -> str:
    return "sha256=" + hmac.new(secret.encode(), f"{timestamp}.{body}".encode(), hashlib.sha256).hexdigest()


def reason_of(check: Callable[[], Any]) -> Optional[str]:
    try:
        check()
    except KiroraWebhookVerificationError as error:
        return error.reason
    return None


def failure(**overrides: Any) -> Optional[str]:
    args = {"secret": SECRET, "raw_body": BODY, "signature": SIGNATURE, "timestamp": TIMESTAMP}
    args.update({k: v for k, v in overrides.items() if k in args})
    return reason_of(
        lambda: Webhooks.assert_signature(
            args["secret"],
            args["raw_body"],
            args["signature"],
            args["timestamp"],
            now=overrides.get("now", NOW),
            tolerance_seconds=overrides.get("tolerance_seconds", 300),
        )
    )


class TestSignature:
    def test_accepts_a_signature_the_server_produced(self) -> None:
        assert Webhooks.verify_signature(SECRET, BODY, SIGNATURE, TIMESTAMP, now=NOW)
        assert failure() is None

    def test_accepts_bytes_and_any_one_of_several_signatures(self) -> None:
        assert failure(raw_body=BODY.encode()) is None
        assert failure(raw_body=bytearray(BODY.encode())) is None
        assert failure(signature=f"sha256=old, {SIGNATURE}") is None

    @pytest.mark.parametrize(
        "overrides",
        [
            {"raw_body": BODY + " "},
            {"secret": "whsec_other"},
            {"signature": "786e82a809095e8f9308254ed5517ffda803370d60f531e5ac9aae4f9b95c841"},
            {"signature": ""},
        ],
    )
    def test_rejects_a_tampered_body_a_wrong_secret_or_a_malformed_signature(self, overrides: Any) -> None:
        assert failure(**overrides) == "signature_mismatch"

    def test_refuses_a_replay(self) -> None:
        assert failure(now=NOW + 301) == "timestamp_outside_tolerance"
        assert failure(now=NOW - 301) == "timestamp_outside_tolerance"
        assert failure(now=NOW + 300) is None
        # A fresh timestamp on an old signature doesn't match.
        assert failure(timestamp=str(int(NOW) + 10)) == "signature_mismatch"

    def test_reports_a_bad_signature_before_a_stale_timestamp(self) -> None:
        assert failure(secret="wrong", now=NOW + 10_000) == "signature_mismatch"

    @pytest.mark.parametrize("timestamp", ["", "abc", "-5", "1.5", "١٢٣"])
    def test_refuses_a_timestamp_that_isnt_whole_seconds(self, timestamp: str) -> None:
        assert failure(timestamp=timestamp) == "invalid_timestamp"

    def test_refuses_a_huge_signed_timestamp_as_invalid(self) -> None:
        huge = "9" * 4500
        assert failure(timestamp=huge, signature=sign(huge, BODY)) == "invalid_timestamp"

    def test_raises_on_invalid_options_rather_than_skipping_the_replay_check(self) -> None:
        with pytest.raises(ValueError, match="secret"):
            Webhooks.verify_signature("", BODY, SIGNATURE, TIMESTAMP)
        for tolerance in (-1, float("nan"), float("inf")):
            with pytest.raises(ValueError, match="tolerance_seconds"):
                Webhooks.verify_signature(SECRET, BODY, SIGNATURE, TIMESTAMP, tolerance_seconds=tolerance)
        with pytest.raises(ValueError, match="now"):
            Webhooks.verify_signature(SECRET, BODY, SIGNATURE, TIMESTAMP, now=float("nan"))


def headers(**overrides: Optional[str]) -> dict:
    base = {
        "X-Webhook-Event": "message.bounced",
        "X-Webhook-Event-Id": "evt_1",
        "X-Webhook-Timestamp": TIMESTAMP,
        "X-Webhook-Signature": SIGNATURE,
        "X-Webhook-Attempt": "2",
    }
    for name, value in overrides.items():
        key = "X-Webhook-" + name.replace("_", "-").title().replace("Id", "Id")
        if value is None:
            base.pop(key, None)
        else:
            base[key] = value
    return base


class TestHeaders:
    def test_reads_the_headers_whatever_their_case(self) -> None:
        read = Webhooks.read_headers({k.lower(): v for k, v in headers().items()})
        assert read is not None
        assert (read.event, read.event_id, read.attempt, read.timestamp, read.signature) == (
            "message.bounced",
            "evt_1",
            2,
            TIMESTAMP,
            SIGNATURE,
        )

    def test_reads_a_list_of_pairs_with_byte_names_and_repeated_values(self) -> None:
        pairs = [(k.lower().encode(), v.encode()) for k, v in headers().items()]
        pairs.append((b"x-webhook-event", b"other"))
        read = Webhooks.read_headers(pairs)
        assert read is not None and read.event == "message.bounced"

    def test_the_attempt_defaults_to_1(self) -> None:
        read = Webhooks.read_headers(headers(attempt=None))
        assert read is not None and read.attempt == 1

    @pytest.mark.parametrize(
        ("overrides", "reason"),
        [
            ({"timestamp": None}, "invalid_timestamp"),
            ({"timestamp": ""}, "invalid_timestamp"),
            ({"signature": None}, "invalid_headers"),
            ({"event": ""}, "invalid_headers"),
            ({"event_id": None}, "invalid_headers"),
            ({"attempt": "0"}, "invalid_headers"),
            ({"attempt": "1.5"}, "invalid_headers"),
            ({"attempt": "-1"}, "invalid_headers"),
            ({"attempt": "1000000000"}, "invalid_headers"),
            ({"attempt": "9" * 4500}, "invalid_headers"),
        ],
    )
    def test_says_why_headers_were_refused(self, overrides: Any, reason: str) -> None:
        given = headers(**overrides)
        assert Webhooks.read_headers(given) is None
        assert reason_of(lambda: Webhooks.assert_headers(given)) == reason


class TestAssertWebhook:
    body = json.dumps({"eventId": "evt_1", "eventType": "message.bounced", "messageId": "m_1"})

    def signed_headers(self, **overrides: Optional[str]) -> dict:
        return headers(signature=sign(TIMESTAMP, self.body), **overrides)

    def test_returns_the_headers_and_the_parsed_body(self) -> None:
        verified = Webhooks.assert_valid(SECRET, self.body, self.signed_headers(), now=NOW)
        assert verified.payload["messageId"] == "m_1"
        assert verified.headers.event_id == "evt_1"
        assert Webhooks.verify(SECRET, self.body.encode(), self.signed_headers(), now=NOW) is not None

    @pytest.mark.parametrize("overrides", [{"event": "message.opened"}, {"event_id": "evt_2"}])
    def test_refuses_event_headers_that_dont_match_the_signed_body(self, overrides: Any) -> None:
        given = self.signed_headers(**overrides)
        assert (
            reason_of(lambda: Webhooks.assert_valid(SECRET, self.body, given, now=NOW)) == "invalid_headers"
        )
        assert Webhooks.verify(SECRET, self.body, given, now=NOW) is None

    def test_refuses_a_huge_attempt_header_without_a_valid_signature(self) -> None:
        given = headers(attempt="9" * 4500, signature="sha256=bad")
        assert Webhooks.verify(SECRET, self.body, given, now=NOW) is None
        assert (
            reason_of(lambda: Webhooks.assert_valid(SECRET, self.body, given, now=NOW)) == "invalid_headers"
        )

    def test_accepts_the_largest_attempt(self) -> None:
        read = Webhooks.read_headers(headers(attempt="999999999"))
        assert read is not None and read.attempt == 999_999_999

    def test_still_checks_the_signature_and_the_headers_first(self) -> None:
        assert reason_of(
            lambda: Webhooks.assert_valid("wrong", self.body, self.signed_headers(), now=NOW)
        ) == ("signature_mismatch")
        assert reason_of(lambda: Webhooks.assert_valid(SECRET, self.body, {}, now=NOW)) == "invalid_timestamp"
