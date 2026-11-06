from __future__ import annotations

import time
from typing import List

import anyio
import httpx
import pytest

import kirora
from kirora import (
    KiroraConnectionError,
    KiroraError,
    KiroraResponseError,
    KiroraTimeoutError,
    NotFoundError,
    last_response,
)

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


async def test_reuses_one_client_in_an_event_loop_without_one(monkeypatch: pytest.MonkeyPatch) -> None:
    server = Server(ok({}), ok({}))
    opened = server.patch_opened(monkeypatch)
    client = kirora.Kirora("sk_test")
    await client.me_async()
    await client.me_async()
    assert len(opened) == 1
    assert not opened[0].is_closed
    await client.aclose()
    assert opened[0].is_closed


async def test_a_call_after_aclose_opens_a_new_client(monkeypatch: pytest.MonkeyPatch) -> None:
    server = Server(ok({}), ok({}))
    opened = server.patch_opened(monkeypatch)
    async with kirora.Kirora("sk_test") as client:
        await client.me_async()
    assert len(opened) == 1 and opened[0].is_closed
    await client.me_async()
    assert len(opened) == 2 and not opened[1].is_closed


async def test_workspace_clients_share_their_parents_client_and_leave_it_open(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    server = Server(ok({}), ok({}))
    opened = server.patch_opened(monkeypatch)
    parent = kirora.Kirora("sk_test")
    await parent.me_async()
    child = parent.for_workspace("tenant-1")
    await child.me_async()
    await child.aclose()
    assert len(opened) == 1 and not opened[0].is_closed


async def test_the_module_settings_reuse_one_client(monkeypatch: pytest.MonkeyPatch) -> None:
    server = Server(ok({}), ok({}))
    opened = server.patch_opened(monkeypatch)
    kirora.api_key = "sk_test"
    await kirora.me_async()
    await kirora.me_async()
    assert len(opened) == 1


async def test_leaves_a_client_it_was_given_open() -> None:
    given = httpx.AsyncClient(transport=httpx.MockTransport(Server(ok({}))))
    client = kirora.Kirora("sk_test", async_http_client=given)
    await client.me_async()
    await client.aclose()
    assert not given.is_closed
    await given.aclose()


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
    await client.me_async()
    assert len(opened) == 1


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
    assert len(opened) == 1


async def test_a_call_inside_an_iteration_shares_its_client(monkeypatch: pytest.MonkeyPatch) -> None:
    server = Server(page([1], "c2"), ok({}), page([2]))
    opened = server.patch_opened(monkeypatch)
    client = kirora.Kirora("sk_test")
    called = False
    async for _ in client.contacts.list_async():
        if not called:
            called = True
            await client.me_async()
    assert len(server.requests) == 3
    assert len(opened) == 1


async def test_retries_a_429_after_its_retry_after(no_waiting: List[float]) -> None:
    server = Server(error(429, "RATE_LIMITED", **{"retry-after": "2"}), ok({"id": "x"}))
    assert await server.client().me_async() == {"id": "x"}
    assert len(server.requests) == 2
    assert 2 <= no_waiting[0] <= 2.5


async def test_gives_the_caller_a_wait_longer_than_max_retry_delay(no_waiting: List[float]) -> None:
    server = Server(error(429, "RATE_LIMITED", **{"retry-after": "60"}))
    with pytest.raises(KiroraError) as caught:
        await server.client(max_retry_delay=30).me_async()
    assert caught.value.retry_after == 60
    assert no_waiting == []


async def test_backs_off_exponentially(no_waiting: List[float]) -> None:
    server = Server(*[error(500, "INTERNAL_ERROR")] * 4)
    with pytest.raises(KiroraError):
        await server.client().me_async()
    assert len(server.requests) == 4
    for attempt, wait in enumerate(no_waiting):
        assert 0.75 * 2**attempt <= wait <= 1.25 * 2**attempt


async def test_does_not_retry_a_4xx() -> None:
    server = Server(error(400, "BAD_REQUEST"))
    with pytest.raises(KiroraError):
        await server.client().me_async()
    assert len(server.requests) == 1


async def test_uses_a_calls_own_max_retries() -> None:
    server = Server(*[error(500, "INTERNAL_ERROR")] * 2)
    with pytest.raises(KiroraError):
        await server.client().me_async({"max_retries": 1})
    assert len(server.requests) == 2


async def test_keys_each_entry_of_a_batch_once_for_every_attempt() -> None:
    server = Server(error(500, "INTERNAL_ERROR"), ok({"results": []}))
    await server.client().events.track_batch_async(
        {
            "events": [
                {"event": {"externalId": "u", "name": "A"}},
                {"event": {"externalId": "u", "name": "B"}, "idempotencyKey": "mine"},
            ]
        }
    )
    first, second = server.body(0)["events"], server.body(1)["events"]
    assert first == second
    assert first[0]["idempotencyKey"]
    assert first[1]["idempotencyKey"] == "mine"


async def test_never_repeats_a_write_without_a_key_that_may_have_happened() -> None:
    server = Server(error(500, "INTERNAL_ERROR"))
    with pytest.raises(KiroraError):
        await server.client().request_async("POST", "/v1/something-new", body={})
    assert len(server.requests) == 1


async def test_retries_any_request_whose_connection_was_never_made() -> None:
    server = Server(httpx.ConnectError("refused"), httpx.ConnectTimeout("slow"), ok({}))
    await server.client().request_async("POST", "/v1/something-new", body={})
    assert len(server.requests) == 3


async def test_retries_a_newer_endpoint_by_its_method_or_with_a_key() -> None:
    server = Server(error(500, "INTERNAL_ERROR"), ok({}), error(500, "INTERNAL_ERROR"), ok({}))
    client = server.client()
    await client.request_async("PUT", "/v1/something-new/x", body={})
    await client.request_async("POST", "/v1/something-new", body={}, idempotency_key="k")
    assert len(server.requests) == 4


async def test_retries_idempotency_key_in_use() -> None:
    server = Server(error(409, "IDEMPOTENCY_KEY_IN_USE"), ok({"id": "e"}, 201))
    await server.client().events.track_async({"externalId": "u", "name": "A"})
    assert len(server.requests) == 2


async def test_retries_an_update_unless_it_changes_how_the_contact_is_found() -> None:
    server = Server(error(500, "INTERNAL_ERROR"), ok({"id": "c_1"}))
    await server.client().contacts.update_async("ada@example.com", {"firstName": "Ada"}, id_type="email")
    assert len(server.requests) == 2
    server = Server(error(500, "INTERNAL_ERROR"))
    with pytest.raises(KiroraError):
        await server.client().contacts.update_async(
            "ada@example.com", {"email": "new@example.com"}, id_type="email"
        )
    assert len(server.requests) == 1


async def test_counts_a_404_on_a_retried_delete_as_done() -> None:
    server = Server(error(500, "INTERNAL_ERROR", **{"x-request-id": "r"}), error(404, "NOT_FOUND"))
    assert await server.client().lists.delete_async("l_1") is None
    server = Server(error(503, "SERVICE_UNAVAILABLE"), error(404, "NOT_FOUND"))
    with pytest.raises(NotFoundError):
        await server.client().lists.delete_async("l_1")


async def test_reports_a_timeout_and_retries_it_when_safe() -> None:
    server = Server(httpx.ReadTimeout("slow"), ok({}))
    await server.client().me_async()
    assert len(server.requests) == 2
    server = Server(httpx.ReadTimeout("slow"))
    with pytest.raises(KiroraTimeoutError, match="timed out after 5s"):
        await server.client(timeout=5).request_async("POST", "/v1/something-new", body={})
    assert len(server.requests) == 1


async def test_retries_an_attempt_whose_headers_arrive_after_the_timeout() -> None:
    async def slow(request: httpx.Request) -> httpx.Response:
        await anyio.sleep(0.5)
        return ok({})

    server = Server(slow, ok({"id": "x"}))
    assert await server.client(timeout=0.02).me_async() == {"id": "x"}
    assert len(server.requests) == 2


async def test_wraps_a_network_failure() -> None:
    server = Server(*[httpx.ReadError("reset")] * 4)
    with pytest.raises(KiroraConnectionError) as caught:
        await server.client().me_async()
    assert isinstance(caught.value.__cause__, httpx.ReadError)
    assert caught.value.request_sent
    assert "GET /v1/me failed: reset" in str(caught.value)
