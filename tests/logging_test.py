from __future__ import annotations

import logging
from typing import Iterator

import pytest

from kirora._logs import configure_from_env, logger

from .conftest import API_KEY, Server, error, ok


@pytest.fixture
def restore_logger() -> Iterator[None]:
    handlers, level = list(logger.handlers), logger.level
    yield
    logger.handlers = handlers
    logger.setLevel(level)


def test_logs_each_attempt_and_retry_without_the_key_or_body(caplog: pytest.LogCaptureFixture) -> None:
    server = Server(
        error(503, "SERVICE_UNAVAILABLE", **{"x-request-id": "req_1"}), ok({}, **{"x-request-id": "req_2"})
    )
    with caplog.at_level(logging.DEBUG, logger="kirora"):
        server.client().contacts.identify({"email": "ada@example.com"})
    key = server.requests[0].headers["idempotency-key"]
    assert [record.getMessage() for record in caplog.records] == [
        f"POST /v1/contacts/identify: attempt 1 of 4, idempotency key {key}",
        "POST /v1/contacts/identify: 503, request id req_1",
        caplog.records[2].getMessage(),
        f"POST /v1/contacts/identify: attempt 2 of 4, idempotency key {key}",
        "POST /v1/contacts/identify: 200, request id req_2",
    ]
    retry = caplog.records[2]
    assert retry.levelno == logging.INFO
    assert retry.getMessage().startswith(
        "POST /v1/contacts/identify: attempt 1 of 4 failed (ServerError: SERVICE_UNAVAILABLE"
    )
    assert "retrying in" in retry.getMessage()
    assert API_KEY not in caplog.text
    assert "ada@example.com" not in caplog.text


def test_logs_why_a_call_stops(caplog: pytest.LogCaptureFixture) -> None:
    server = Server(error(400, "BAD_REQUEST"))
    with caplog.at_level(logging.DEBUG, logger="kirora"), pytest.raises(Exception):
        server.client().me()
    assert caplog.records[-1].getMessage() == (
        "GET /v1/me: attempt 1 failed (BadRequestError: BAD_REQUEST: HTTP 400), not retrying"
    )


def test_logs_nothing_at_the_default_level(caplog: pytest.LogCaptureFixture) -> None:
    Server(ok({})).client().me()
    assert caplog.records == []


@pytest.mark.usefixtures("restore_logger")
def test_kirora_log_logs_to_standard_error(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("KIRORA_LOG", " DEBUG ")
    logger.handlers = []
    configure_from_env()
    Server(ok({})).client().me()
    assert "kirora DEBUG GET /v1/me: attempt 1 of 4" in capsys.readouterr().err


@pytest.mark.usefixtures("restore_logger")
@pytest.mark.parametrize("value", ["", "verbose"])
def test_kirora_log_ignores_other_values(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv("KIRORA_LOG", value)
    logger.handlers = []
    configure_from_env()
    assert logger.handlers == []
