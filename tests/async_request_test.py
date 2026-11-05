from __future__ import annotations

import time
from typing import List

import anyio
import httpx
import pytest

import kirora
from kirora import KiroraError, KiroraResponseError, KiroraTimeoutError, NotFoundError, last_response

from .conftest import Delayed, Server, error, ok, page

pytestmark = pytest.mark.asyncio


async def test_unwraps_the_data_envelope_and_retries_with_the_same_key() -> None:
    server = Server(error(503, "SERVICE_UNAVAILABLE", **{"x-request-id": "r"}), ok({"id": "c_1"}))
    server.install()
    contact = await kirora.Contacts.identify_async({"email": "ada@example.com"})
    assert contact == {"id": "c_1"}
    first, second = server.requests
    assert first.headers["idempotency-key"] == second.headers["idempotency-key"]


async def test_waits_between_attempts_without_blocking(no_waiting: List[float]) -> None:
    server = Server(error(429, "RATE_LIMITED", **{"retry-after": "3"}), ok({}))
    await server.client().me_async()
    assert 3 <= no_waiting[0] <= 3.75


async def test_awaiting_a_list_returns_the_first_page() -> None:
    server = Server(page([{"id": 1}], "c2"))
    server.install()
    first = await kirora.Contacts.list_async({"query": "ada"})
    assert first.data == [{"id": 1}]
    assert first.next_cursor == "c2"
    assert server.last.url.params["query"] == "ada"


async def test_iterating_a_list_walks_every_page() -> None:
    server = Server(page([{"id": 1}], "c2"), page([{"id": 2}]))
    ids = [item["id"] async for item in server.client().lists.list_async()]
    assert ids == [1, 2]


async def test_a_list_fetches_nothing_until_awaited_and_reuses_the_first_page() -> None:
    server = Server(page([{"id": 1}], "c2"), page([{"id": 2}]))
    pager = server.client().suppressions.list_async()
    assert server.requests == []
    first = await pager
    ids = [item["id"] async for item in pager]
    assert await pager is first
    assert ids == [1, 2]
    assert len(server.requests) == 2


async def test_stops_on_a_repeated_cursor() -> None:
    server = Server(page([], "c2"), page([], "c2"))
    with pytest.raises(KiroraResponseError, match="came round again"):
        async for _ in server.client().messages.list_async():
            pass


async def test_raises_api_errors_by_status() -> None:
    server = Server(error(404, "NOT_FOUND", "No such contact"))
    with pytest.raises(NotFoundError) as caught:
        await server.client().contacts.get_async("missing")
    assert isinstance(caught.value, KiroraError)
    assert caught.value.code == "NOT_FOUND"


async def test_attaches_response_metadata_and_scopes_a_workspace() -> None:
    server = Server(ok({"id": "w"}, **{"x-request-id": "req_9"}))
    result = await server.client().for_workspace("tenant-1").me_async()
    assert last_response(result).request_id == "req_9"  # type: ignore[union-attr]
    assert server.last.headers["kirora-workspace"] == "tenant-1"


async def test_deletes_return_none() -> None:
    server = Server(httpx.Response(204))
    assert await server.client().contacts.delete_installation_async("c_1", "device-1") is None
    assert server.last.url.raw_path == b"/v1/contacts/c_1/installations/device-1"


async def test_streams_a_raw_response() -> None:
    server = Server(httpx.Response(200, content=b"a,b\n"))
    async with server.client().request_raw_async("GET", "/v1/messages/exports/x/download") as response:
        assert b"".join([chunk async for chunk in response.aiter_bytes()]) == b"a,b\n"


async def test_opens_a_client_per_call_without_one(monkeypatch: pytest.MonkeyPatch) -> None:
    # Without an async_http_client, each call opens and closes its own, so it works in
    # any event loop.
    server = Server(ok({}), ok({}))
    opened = server.patch_opened(monkeypatch)
    client = kirora.Kirora("sk_test")
    await client.me_async()
    await client.me_async()
    assert len(opened) == 2
    assert all(c.is_closed for c in opened)


async def test_tasks_awaiting_a_list_at_once_share_the_first_page() -> None:
    async def slow_page(request: httpx.Request) -> httpx.Response:
        await anyio.sleep(0.01)  # Lets the other task run while this request is out.
        return page([{"id": 1}])

    server = Server(slow_page)
    results = []
    pager = server.client().contacts.list_async()

    async def first() -> None:
        results.append(await pager)

    async with anyio.create_task_group() as group:
        group.start_soon(first)
        group.start_soon(first)
    assert len(server.requests) == 1
    assert results[0] is results[1]


async def test_times_out_headers_and_a_body_late_only_together() -> None:
    async def slow_headers(request: httpx.Request) -> httpx.Response:
        await anyio.sleep(0.14)
        return httpx.Response(200, stream=Delayed((0.14, b'{"data":{}}')))

    with pytest.raises(KiroraTimeoutError):
        await Server(slow_headers).client().me_async({"timeout": 0.2, "max_retries": 0})


async def test_cuts_off_a_stalled_body_at_the_deadline() -> None:
    stalled = Delayed((0, b'{"data":'), (5, b"{}}"))
    started = time.monotonic()
    with pytest.raises(KiroraTimeoutError):
        await (
            Server(lambda request: httpx.Response(200, stream=stalled))
            .client()
            .me_async({"timeout": 0.05, "max_retries": 0})
        )
    assert time.monotonic() - started < 1


async def test_checks_a_lists_options_at_the_call() -> None:
    server = Server()
    with pytest.raises(ValueError, match="workspace"):
        server.client().contacts.list_async(None, {"workspace": ""})
    with pytest.raises(ValueError, match="doesn't take an idempotency key"):
        server.client().contacts.list_async(None, {"idempotency_key": "k"})
    assert server.requests == []


async def test_an_iteration_shares_one_connection_between_its_pages(monkeypatch: pytest.MonkeyPatch) -> None:
    server = Server(page([{"id": 1}], "c2"), page([{"id": 2}], "c3"), page([{"id": 3}]), ok({}))
    opened = server.patch_opened(monkeypatch)
    client = kirora.Kirora("sk_test")
    ids = [item["id"] async for item in client.contacts.list_async()]
    assert ids == [1, 2, 3]
    assert len(opened) == 1 and opened[0].is_closed
    # A later call, outside the iteration, opens its own.
    await client.me_async()
    assert len(opened) == 2


async def test_a_call_after_breaking_out_of_an_iteration_still_works(monkeypatch: pytest.MonkeyPatch) -> None:
    server = Server(page([{"id": 1}], "c2"), ok({}))
    server.patch_opened(monkeypatch)
    client = kirora.Kirora("sk_test")
    async for _ in client.contacts.list_async():
        break
    await client.me_async()
    assert len(server.requests) == 2


async def test_cuts_off_an_error_body_at_the_deadline_keeping_its_status() -> None:
    body = Delayed((0, b'{"error":{"code":"NOT_FOUND",'), (5, b'"message":"No such contact"}}'))
    server = Server(lambda request: httpx.Response(404, stream=body, headers={"x-request-id": "req_slow"}))
    started = time.monotonic()
    with pytest.raises(NotFoundError) as caught:
        await server.client(timeout=0.05).contacts.get_async("c")
    assert time.monotonic() - started < 1
    assert caught.value.request_id == "req_slow"
    assert caught.value.message == "HTTP 404"


async def test_raises_the_404_of_a_retried_raw_delete() -> None:
    server = Server(httpx.ReadTimeout("slow"), error(404, "NOT_FOUND"))
    with pytest.raises(NotFoundError):
        async with server.client().request_raw_async("DELETE", "/v1/contacts/contact-1"):
            pass
    assert len(server.requests) == 2


async def test_walking_an_awaited_page_shares_one_connection(monkeypatch: pytest.MonkeyPatch) -> None:
    server = Server(page([1], "c2"), page([2], "c3"), page([3]))
    opened = server.patch_opened(monkeypatch)
    first = await kirora.Kirora("sk_test").contacts.list_async()
    assert [item async for item in first] == [1, 2, 3]
    # The first page's own request, then one for the walk.
    assert len(opened) == 2


async def test_a_call_inside_an_iteration_opens_its_own_connection(monkeypatch: pytest.MonkeyPatch) -> None:
    server = Server(page([1], "c2"), ok({}), page([2]))
    opened = server.patch_opened(monkeypatch)
    client = kirora.Kirora("sk_test")
    async for _ in client.contacts.list_async():
        if len(opened) == 1:
            await client.me_async()
    assert len(opened) == 2
    assert opened[1].is_closed
