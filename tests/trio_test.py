"""The ``_async`` methods under Trio, which the README says they support."""

from __future__ import annotations

import time

import httpx
import pytest

import kirora

from .conftest import Server, error, ok, page

trio = pytest.importorskip("trio")


def test_a_call_a_retry_and_a_paged_iteration_under_trio() -> None:
    server = Server(
        error(503, "SERVICE_UNAVAILABLE", **{"x-request-id": "r"}),
        ok({"id": "c"}),
        page([1], "c2"),
        page([2]),
    )

    async def main() -> None:
        client = kirora.Kirora(
            "sk_test", async_http_client=httpx.AsyncClient(transport=httpx.MockTransport(server))
        )
        assert await client.contacts.identify_async({"email": "ada@example.com"}) == {"id": "c"}
        assert [item async for item in client.contacts.list_async()] == [1, 2]

    trio.run(main)
    assert len(server.requests) == 4


def test_reuses_one_client_in_a_trio_run_until_aclose(monkeypatch: pytest.MonkeyPatch) -> None:
    server = Server(page([1], "c2"), page([2]), ok({}))
    opened = server.patch_opened(monkeypatch)

    async def main() -> None:
        client = kirora.Kirora("sk_test")
        assert [item async for item in client.contacts.list_async()] == [1, 2]
        await client.me_async()
        assert len(opened) == 1 and not opened[0].is_closed
        await client.aclose()

    trio.run(main)
    assert len(opened) == 1 and opened[0].is_closed


def test_opens_a_client_for_each_trio_run(monkeypatch: pytest.MonkeyPatch) -> None:
    server = Server(ok({}), ok({}))
    opened = server.patch_opened(monkeypatch)
    client = kirora.Kirora("sk_test")
    trio.run(client.me_async)
    trio.run(client.me_async)
    assert len(opened) == 2


def test_the_deadline_cancels_an_attempt_under_trio() -> None:
    async def stalled(request: httpx.Request) -> httpx.Response:
        await trio.sleep(5)
        return ok({})

    server = Server(stalled)

    async def main() -> None:
        client = kirora.Kirora(
            "sk_test", async_http_client=httpx.AsyncClient(transport=httpx.MockTransport(server))
        )
        with pytest.raises(kirora.KiroraTimeoutError):
            await client.me_async({"timeout": 0.05, "max_retries": 0})

    started = time.monotonic()
    trio.run(main)
    assert time.monotonic() - started < 2
