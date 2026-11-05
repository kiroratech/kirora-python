from __future__ import annotations

import pytest

import kirora
from kirora import exceptions

from .conftest import Server, error


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
