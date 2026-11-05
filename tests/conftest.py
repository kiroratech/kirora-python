from __future__ import annotations

import json
import time
from typing import Any, AsyncIterator, Callable, Iterator, List, Tuple, Union

import anyio
import httpx
import pytest

import kirora
from kirora import Kirora
from kirora._client import DEFAULT_SETTINGS

API_KEY = "sk_test_reference"

Reply = Union[httpx.Response, Exception, Callable[[httpx.Request], httpx.Response]]


def ok(data: Any, status: int = 200, **headers: str) -> httpx.Response:
    """A success with ``data`` in the API's envelope."""
    return httpx.Response(status, json={"data": data}, headers=headers)


def page(items: List[Any], cursor: Union[str, None] = None, **meta: Any) -> httpx.Response:
    return httpx.Response(
        200, json={"data": items, "meta": {"pagination": {"limit": 20, "nextCursor": cursor}, **meta}}
    )


def error(status: int, code: str = "", message: str = "", **headers: str) -> httpx.Response:
    body = {"error": {"code": code, "message": message}} if code else {}
    return httpx.Response(status, json=body, headers=headers)


Part = Tuple[float, bytes]


class Delayed(httpx.SyncByteStream, httpx.AsyncByteStream):
    """A body that waits before each part: ``Delayed((0, b"{"), (0.05, b"}"))``. It
    sleeps for the sync client and awaits for the async one."""

    def __init__(self, *parts: Part) -> None:
        self.parts = parts

    def __iter__(self) -> Iterator[bytes]:
        for delay, chunk in self.parts:
            time.sleep(delay)
            yield chunk

    async def __aiter__(self) -> AsyncIterator[bytes]:
        for delay, chunk in self.parts:
            await anyio.sleep(delay)
            yield chunk


class Server:
    """Answers each request with the next reply, and records what was sent. A reply can be
    a function of the request, and for the async client an async one."""

    def __init__(self, *replies: Reply) -> None:
        self.replies = list(replies)
        self.requests: List[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        request.read()
        self.requests.append(request)
        if not self.replies:
            raise AssertionError(f"unexpected request: {request.method} {request.url}")
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            if isinstance(reply, httpx.RequestError):
                reply._request = request
            raise reply
        if callable(reply) and not isinstance(reply, httpx.Response):
            return reply(request)
        return reply

    @property
    def last(self) -> httpx.Request:
        return self.requests[-1]

    def body(self, index: int = -1) -> Any:
        return json.loads(self.requests[index].content)

    def client(self, **options: Any) -> Kirora:
        """A ``Kirora`` client whose sync and async methods both reach this server."""
        options.setdefault("api_key", API_KEY)
        return Kirora(
            http_client=httpx.Client(transport=httpx.MockTransport(self)),
            async_http_client=httpx.AsyncClient(transport=httpx.MockTransport(self)),
            **options,
        )

    def patch_opened(self, monkeypatch: pytest.MonkeyPatch) -> List[Any]:
        """Makes the httpx clients the SDK opens itself reach this server, and returns
        the list of them, as they're opened."""
        opened: List[Any] = []
        real_sync, real_async = httpx.Client, httpx.AsyncClient

        def sync(*args: object, **kwargs: object) -> httpx.Client:
            opened.append(real_sync(transport=httpx.MockTransport(self)))
            return opened[-1]  # type: ignore[no-any-return]

        def async_(*args: object, **kwargs: object) -> httpx.AsyncClient:
            opened.append(real_async(transport=httpx.MockTransport(self)))
            return opened[-1]  # type: ignore[no-any-return]

        monkeypatch.setattr("kirora._connections.httpx.Client", sync)
        monkeypatch.setattr("kirora._connections.httpx.AsyncClient", async_)
        return opened

    def install(self) -> None:
        """Points the module settings, which ``kirora.Contacts`` and the rest use, here."""
        kirora.api_key = API_KEY
        kirora.default_http_client = httpx.Client(transport=httpx.MockTransport(self))
        kirora.default_async_http_client = httpx.AsyncClient(transport=httpx.MockTransport(self))


@pytest.fixture(autouse=True)
def no_waiting(monkeypatch: pytest.MonkeyPatch) -> List[float]:
    """Records each wait between attempts instead of sleeping."""
    waits: List[float] = []

    async def async_sleep(seconds: float) -> None:
        waits.append(seconds)

    monkeypatch.setattr("kirora.request._sleep", waits.append)
    monkeypatch.setattr("kirora.async_request._async_sleep", async_sleep)
    return waits


@pytest.fixture(autouse=True)
def clean_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Each test starts from the default module settings and environment."""
    monkeypatch.delenv("KIRORA_API_KEY", raising=False)
    monkeypatch.delenv("KIRORA_BASE_URL", raising=False)
    for name, value in DEFAULT_SETTINGS.items():
        monkeypatch.setattr(kirora, name, value)
