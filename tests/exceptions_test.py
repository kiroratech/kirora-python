from __future__ import annotations

import pickle

import httpx
import pytest

import kirora
from kirora import exceptions

from .conftest import Server, error, ok


@pytest.mark.parametrize(
    ("status", "cls"),
    [
        (400, exceptions.BadRequestError),
        (401, exceptions.AuthenticationError),
        (403, exceptions.PermissionDeniedError),
        (404, exceptions.NotFoundError),
        (409, exceptions.ConflictError),
        (429, exceptions.RateLimitError),
        (500, exceptions.ServerError),
        (503, exceptions.ServerError),
        (413, exceptions.KiroraError),
    ],
)
def test_raises_the_error_class_for_the_status(status: int, cls: type) -> None:
    server = Server(error(status, "SOME_CODE", "Went wrong"))
    with pytest.raises(cls) as caught:
        server.client(max_retries=0).me()
    assert type(caught.value) is cls
    assert caught.value.code == "SOME_CODE"
    assert repr(caught.value).startswith(f"{cls.__name__}(code='SOME_CODE'")


def test_every_error_class_is_a_kirora_error() -> None:
    for name in ("BadRequestError", "AuthenticationError", "NotFoundError", "RateLimitError", "ServerError"):
        assert issubclass(getattr(kirora, name), kirora.KiroraError)
    for name in (
        "KiroraError",
        "KiroraConnectionError",
        "KiroraResponseError",
        "KiroraWebhookVerificationError",
    ):
        assert issubclass(getattr(kirora, name), kirora.KiroraException)


def test_an_api_error_survives_pickling_with_its_response() -> None:
    server = Server(error(404, "NOT_FOUND", "No such contact", **{"x-request-id": "req_1", "x-extra": "1"}))
    with pytest.raises(exceptions.NotFoundError) as caught:
        server.client().contacts.get("c")
    copy = pickle.loads(pickle.dumps(caught.value))
    assert type(copy) is exceptions.NotFoundError
    assert (copy.code, copy.status, copy.message, copy.request_id) == (
        "NOT_FOUND",
        404,
        "No such contact",
        "req_1",
    )
    assert str(copy) == str(caught.value)
    info = kirora.last_response(copy)
    assert info is not None
    assert info.headers["x-extra"] == "1"


@pytest.mark.parametrize(
    "error_",
    [
        exceptions.ServerError(code="INTERNAL_ERROR", message="Oops", status=500, details={"a": 1}),
        exceptions.KiroraConnectionError("GET /v1/me", httpx.ReadError("reset")),
        exceptions.KiroraTimeoutError("GET /v1/me", 5, httpx.ConnectTimeout("slow"), unsent=True),
        exceptions.KiroraResponseError("GET /v1/me returned 200", status=200, request_id="r"),
        exceptions.KiroraWebhookVerificationError("signature_mismatch", "No signature matches"),
    ],
)
def test_every_error_survives_pickling(error_: exceptions.KiroraException) -> None:
    copy = pickle.loads(pickle.dumps(error_))
    assert type(copy) is type(error_)
    assert str(copy) == str(error_)
    assert copy.__dict__ == error_.__dict__


def test_says_whether_a_request_that_failed_was_sent() -> None:
    server = Server(httpx.ConnectError("refused"), httpx.ReadError("reset"))
    client = server.client(max_retries=0)
    with pytest.raises(exceptions.KiroraConnectionError) as unsent:
        client.me()
    with pytest.raises(exceptions.KiroraConnectionError) as sent:
        client.me()
    assert not unsent.value.request_sent
    assert sent.value.request_sent


def test_an_api_error_carries_its_response() -> None:
    server = Server(error(409, "CONFLICT", "Taken", **{"x-request-id": "req_2", "ratelimit-limit": "10"}))
    with pytest.raises(exceptions.ConflictError) as caught:
        server.client().me()
    info = kirora.last_response(caught.value)
    assert info is caught.value.last_response
    assert info is not None
    assert (info.status, info.request_id, info.headers["ratelimit-limit"]) == (409, "req_2", "10")


@pytest.mark.parametrize("status", [501, 505])
def test_does_not_retry_a_501_or_505(status: int) -> None:
    server = Server(error(status), ok({}))
    with pytest.raises(exceptions.ServerError) as caught:
        server.client().me()
    assert not caught.value.is_retryable
    assert len(server.requests) == 1
