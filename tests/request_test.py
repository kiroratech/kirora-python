from __future__ import annotations

import datetime as dt
import email.utils
import json
import re
import time
import uuid
from typing import List

import httpx
import pytest

import kirora
from kirora import (
    Kirora,
    KiroraConnectionError,
    KiroraError,
    KiroraResponseError,
    KiroraTimeoutError,
    last_response,
)

from .conftest import API_KEY, Delayed, Server, error, ok, page

CONTACT = {"id": "c_1", "email": "ada@example.com"}


def is_uuid(value: str) -> bool:
    try:
        uuid.UUID(value)
    except ValueError:
        return False
    return True


class TestRequests:
    def test_sends_the_key_as_a_bearer_token_and_unwraps_the_data_envelope(self) -> None:
        server = Server(ok(CONTACT))
        contact = server.client().contacts.get("c_1")
        assert contact == CONTACT
        request = server.last
        assert request.method == "GET"
        assert str(request.url) == "https://api.kirora.io/v1/contacts/c_1"
        assert request.headers["authorization"] == f"Bearer {API_KEY}"
        assert request.headers["accept"] == "application/json"
        assert "idempotency-key" not in request.headers

    def test_looks_a_contact_up_by_email_with_the_id_encoded(self) -> None:
        server = Server(ok(CONTACT))
        server.client().contacts.get("ada+1@example.com", id_type="email")
        assert server.last.url.raw_path == b"/v1/contacts/ada%2B1%40example.com?idType=email"

    def test_encodes_an_id_as_one_segment(self) -> None:
        server = Server(ok({}))
        server.client().lists.get("a/b c")
        assert server.last.url.raw_path == b"/v1/lists/a%2Fb%20c"

    def test_sends_a_body_as_json_with_a_new_idempotency_key(self) -> None:
        server = Server(ok(CONTACT), ok(CONTACT))
        client = server.client()
        client.contacts.identify({"externalId": "user-1", "email": "ada@example.com"})
        client.contacts.identify({"externalId": "user-1"})
        first, second = server.requests
        assert first.headers["content-type"] == "application/json"
        assert server.body(0) == {"externalId": "user-1", "email": "ada@example.com"}
        assert is_uuid(first.headers["idempotency-key"])
        # Separate calls get separate keys.
        assert first.headers["idempotency-key"] != second.headers["idempotency-key"]

    def test_uses_the_callers_idempotency_key(self) -> None:
        server = Server(ok({"id": "e_1"}, 201))
        server.client().events.track(
            {"externalId": "user-1", "name": "Order Completed"}, {"idempotency_key": "order-1"}
        )
        assert server.last.headers["idempotency-key"] == "order-1"

    def test_a_delete_returns_none(self) -> None:
        server = Server(httpx.Response(204))
        assert server.client().contacts.delete("user-1", id_type="externalId") is None
        assert server.last.method == "DELETE"
        assert server.last.url.params["idType"] == "externalId"

    def test_writes_bools_and_datetimes_as_the_api_reads_them(self) -> None:
        server = Server(page([]))
        server.client().contacts.list(
            {"suppressed": False, "createdAfter": dt.datetime(2026, 1, 2, 3, 4, 5, tzinfo=dt.timezone.utc)}
        )
        params = server.last.url.params
        assert params["suppressed"] == "false"
        assert params["createdAfter"] == "2026-01-02T03:04:05Z"

    def test_refuses_a_naive_datetime(self) -> None:
        with pytest.raises(ValueError, match="no timezone"):
            Server().client().contacts.list({"createdAfter": dt.datetime(2026, 1, 2)})

    def test_refuses_an_unknown_option_before_sending(self) -> None:
        server = Server()
        with pytest.raises(TypeError, match="timeout_ms"):
            server.client().me({"timeout_ms": 5})  # type: ignore[typeddict-unknown-key]
        assert server.requests == []

    def test_names_the_sdk_and_the_app_in_the_user_agent(self) -> None:
        server = Server(ok({}), ok({}))
        client = server.client(app_info={"name": "shop", "version": "1.2.0"})
        client.me()
        client.for_workspace("tenant-1").me()
        for request in server.requests:
            assert re.fullmatch(
                rf"kirora-python/{kirora.__version__} python/[\d.]+\S* shop/1\.2\.0",
                request.headers["user-agent"],
            )

    def test_sends_the_clients_and_the_calls_headers_under_the_sdks_own(self) -> None:
        server = Server(ok({}))
        client = server.client(headers={"X-Team": "growth", "Authorization": "nope"})
        client.me({"headers": {"x-trace": "t1"}})
        headers = server.last.headers
        assert headers["x-team"] == "growth"
        assert headers["x-trace"] == "t1"
        assert headers["authorization"] == f"Bearer {API_KEY}"


class TestPartnerWorkspaces:
    def test_for_workspace_sends_the_header_and_keeps_the_settings(self) -> None:
        server = Server(ok({}), ok({}))
        client = server.client(base_url="https://proxy.example/kirora")
        tenant = client.for_workspace("tenant-1")
        tenant.me()
        client.me()
        assert server.requests[0].headers["kirora-workspace"] == "tenant-1"
        assert str(server.requests[0].url) == "https://proxy.example/kirora/v1/me"
        assert "kirora-workspace" not in server.requests[1].headers

    def test_a_kirora_workspace_header_counts_as_the_workspace(self) -> None:
        server = Server(ok({}), ok({}))
        client = server.client(headers={"Kirora-Workspace": "tenant-1"})
        client.me()
        client.me({"workspace": "tenant-2"})
        assert [r.headers["kirora-workspace"] for r in server.requests] == ["tenant-1", "tenant-2"]

    def test_refuses_an_empty_workspace(self) -> None:
        with pytest.raises(ValueError, match="workspace"):
            Server().client(workspace="")
        with pytest.raises(ValueError, match="workspace"):
            Server().client().me({"workspace": ""})


class TestConfiguration:
    def test_reads_the_key_from_the_environment_and_trims_quotes(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("KIRORA_API_KEY", ' "sk_from_env" ')
        server = Server(ok({}))
        Kirora(http_client=httpx.Client(transport=httpx.MockTransport(server))).me()
        assert server.last.headers["authorization"] == "Bearer sk_from_env"

    @pytest.mark.parametrize("key", [None, "", "  ", "undefined", "null", "None", "''"])
    def test_refuses_a_missing_key(self, key: str) -> None:
        with pytest.raises(ValueError, match="api_key is required"):
            Kirora(key)

    def test_reads_the_base_url_from_the_environment(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("KIRORA_BASE_URL", "http://localhost:8787/")
        server = Server(ok({}))
        server.client().me()
        assert str(server.last.url) == "http://localhost:8787/v1/me"
        monkeypatch.setenv("KIRORA_BASE_URL", "localhost")
        with pytest.raises(ValueError, match="KIRORA_BASE_URL"):
            server.client()

    @pytest.mark.parametrize(
        "url",
        ["ftp://api.kirora.io", "api.kirora.io", "https://api.kirora.io?x=1", "https://api.kirora.io#a"],
    )
    def test_refuses_a_base_url_that_would_misroute(self, url: str) -> None:
        with pytest.raises(ValueError, match="base_url"):
            Kirora(API_KEY, base_url=url)

    def test_warns_of_a_plain_http_base_url_off_this_machine(self) -> None:
        with pytest.warns(UserWarning, match="plain http"):
            Kirora(API_KEY, base_url="http://api.example.com")

    @pytest.mark.parametrize(
        "url", ["http://localhost:8787", "http://127.0.0.1", "http://[::1]:8000", "http://api.localhost"]
    )
    def test_allows_plain_http_on_this_machine(self, url: str) -> None:
        Kirora(API_KEY, base_url=url)

    def test_refuses_an_idempotency_key_for_every_call(self) -> None:
        with pytest.raises(ValueError, match="per call"):
            Kirora(API_KEY, headers={"Idempotency-Key": "k"})

    def test_refuses_an_empty_idempotency_key(self) -> None:
        client = Server().client()
        with pytest.raises(ValueError, match="empty"):
            client.contacts.identify({"email": "a@example.com"}, {"idempotency_key": ""})
        with pytest.raises(ValueError, match="empty"):
            client.contacts.identify({"email": "a@example.com"}, {"headers": {"Idempotency-Key": ""}})

    @pytest.mark.parametrize(
        ("option", "value"),
        [
            ("timeout", 0),
            ("timeout", -1),
            ("timeout", float("inf")),
            ("timeout", True),
            ("max_retries", 11),
            ("max_retries", -1),
            ("max_retries", 1.5),
            ("max_retry_delay", -1),
        ],
    )
    def test_refuses_an_option_out_of_range(self, option: str, value: object) -> None:
        with pytest.raises(ValueError, match=option):
            Kirora(API_KEY, **{option: value})  # type: ignore[arg-type]

    def test_accepts_the_boundary_values(self) -> None:
        Kirora(API_KEY, timeout=0.001, max_retries=0, max_retry_delay=0)
        Kirora(API_KEY, max_retries=10)

    @pytest.mark.parametrize("name", ["my app", "a/b", "", "app\n"])
    def test_refuses_an_app_name_that_would_break_the_user_agent(self, name: str) -> None:
        with pytest.raises(ValueError, match="app_info"):
            Kirora(API_KEY, app_info={"name": name})

    def test_closes_only_its_own_http_client(self) -> None:
        own = Kirora(API_KEY)
        opened = own._connections.sync()
        own.close()
        assert opened.is_closed
        given = httpx.Client()
        with Kirora(API_KEY, http_client=given):
            pass
        assert not given.is_closed


class TestPaths:
    @pytest.mark.parametrize("contact_id", ["", ".", "..", "%2e%2E"])
    def test_refuses_an_id_that_would_change_the_route(self, contact_id: str) -> None:
        server = Server()
        with pytest.raises(ValueError, match="can't be empty"):
            server.client().contacts.get(contact_id) if contact_id != "%2e%2E" else server.client().request(
                "GET", f"/v1/contacts/{contact_id}"
            )
        assert server.requests == []

    @pytest.mark.parametrize("path", ["v1/me", "/v1/me#x", "/v1/me\\x", "/v1/me\n"])
    def test_refuses_a_raw_path_that_would_go_elsewhere(self, path: str) -> None:
        with pytest.raises(ValueError):
            Server().client().request("GET", path)

    def test_refuses_an_id_that_isnt_a_string(self) -> None:
        with pytest.raises(TypeError):
            Server().client().contacts.get(123)  # type: ignore[arg-type]


class TestResponses:
    def test_refuses_a_success_that_isnt_json(self) -> None:
        server = Server(httpx.Response(200, text="<html>proxy</html>"))
        with pytest.raises(KiroraResponseError, match="not JSON"):
            server.client().me()

    @pytest.mark.parametrize("body", [{}, {"data": "x"}, {"data": None}, []])
    def test_refuses_a_success_without_the_envelope(self, body: object) -> None:
        with pytest.raises(KiroraResponseError, match="envelope"):
            Server(httpx.Response(200, json=body)).client().me()

    def test_refuses_a_page_without_its_pagination(self) -> None:
        reply = httpx.Response(200, json={"data": [], "meta": {"pagination": {"nextCursor": None}}})
        with pytest.raises(KiroraResponseError, match="pagination"):
            Server(reply).client().lists.list()

    def test_returns_none_for_a_204_or_a_head(self) -> None:
        server = Server(httpx.Response(204), httpx.Response(200, headers={"content-length": "5"}))
        client = server.client()
        assert client.request("DELETE", "/v1/lists/l_1") is None
        assert client.request("HEAD", "/v1/me") is None

    def test_reads_a_body_with_a_byte_order_mark(self) -> None:
        reply = httpx.Response(200, content=b"\xef\xbb\xbf" + json.dumps({"data": {"id": "x"}}).encode())
        assert Server(reply).client().me() == {"id": "x"}

    def test_attaches_the_response_metadata(self) -> None:
        reply = ok(
            CONTACT,
            **{
                "x-request-id": "req_1",
                "idempotency-replay": "true",
                "ratelimit-limit": "100",
                "ratelimit-remaining": "99",
                "ratelimit-reset": "30",
            },
        )
        contact = Server(reply).client().contacts.identify({"email": "ada@example.com"})
        info = last_response(contact)
        assert info is not None
        assert info.status == 200
        assert info.request_id == "req_1"
        assert info.idempotency_replay is True
        assert info.rate_limit == kirora.RateLimit(limit=100, remaining=99, reset_seconds=30)
        # The result is still a plain dict to every other code.
        assert json.loads(json.dumps(contact)) == CONTACT
        assert last_response(dict(contact)) is None

    def test_attaches_the_response_to_a_list_result(self) -> None:
        topics = Server(ok([{"id": "t_1"}], **{"x-request-id": "req_2"})).client().contacts.list_topics("c_1")
        assert topics == [{"id": "t_1"}]
        assert last_response(topics).request_id == "req_2"  # type: ignore[union-attr]

    def test_refuses_a_body_larger_than_64_mib_without_reading_it(self) -> None:
        reply = httpx.Response(200, headers={"content-length": str(65 * 1024 * 1024)}, content=b"{}")
        with pytest.raises(KiroraResponseError, match="64 MiB"):
            Server(reply).client().me()

    def test_keeps_the_status_of_an_error_whose_body_is_too_large(self) -> None:
        big = httpx.Response(503, headers={"content-length": str(65 * 1024 * 1024)}, content=b"{}")
        server = Server(big, ok({"id": "x"}))
        assert server.client().me() == {"id": "x"}
        assert len(server.requests) == 2

    def test_never_follows_a_redirect(self) -> None:
        server = Server(httpx.Response(307, headers={"location": "https://elsewhere.example/v1/campaigns"}))
        with pytest.raises(KiroraResponseError, match=r"redirected to https://elsewhere\.example"):
            server.client().campaigns.create({"name": "Launch"})
        assert len(server.requests) == 1

    def test_streams_a_raw_response_after_retrying_an_error(self) -> None:
        server = Server(error(503, "SERVICE_UNAVAILABLE"), httpx.Response(200, content=b"id,email\n1,a\n"))
        with server.client().request_raw("GET", "/v1/messages/exports/x/download") as response:
            assert b"".join(response.iter_bytes()) == b"id,email\n1,a\n"
        assert len(server.requests) == 2


class TestErrors:
    def test_maps_an_error_body_onto_a_typed_error(self) -> None:
        reply = httpx.Response(
            400,
            json={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Invalid request",
                    "errors": [{"field": "email", "message": "Not an email"}, {"bad": True}],
                    "details": {"hint": 1},
                    "requestId": "req_body",
                }
            },
        )
        with pytest.raises(KiroraError) as caught:
            Server(reply).client().contacts.identify({"email": "nope"})
        err = caught.value
        assert err.code == "VALIDATION_ERROR"
        assert err.status == 400
        assert err.message == "Invalid request"
        assert err.errors == [{"field": "email", "message": "Not an email"}]
        assert err.details == {"hint": 1}
        assert err.request_id == "req_body"
        assert err.is_known_code()
        assert not err.is_retryable
        assert str(err) == "VALIDATION_ERROR: Invalid request (request req_body)"

    def test_prefers_the_request_id_header(self) -> None:
        reply = httpx.Response(
            404,
            json={"error": {"code": "NOT_FOUND", "message": "x", "requestId": "b"}},
            headers={"x-request-id": "h"},
        )
        with pytest.raises(KiroraError) as caught:
            Server(reply).client().me()
        assert caught.value.request_id == "h"

    @pytest.mark.parametrize(
        ("status", "code"),
        [(401, "UNAUTHORIZED"), (404, "NOT_FOUND"), (418, "BAD_REQUEST"), (502, "INTERNAL_ERROR")],
    )
    def test_falls_back_to_a_code_by_status_for_an_unexpected_body(self, status: int, code: str) -> None:
        with pytest.raises(KiroraError) as caught:
            Server(httpx.Response(status, text="oops")).client(max_retries=0).me()
        assert caught.value.code == code
        assert caught.value.message == f"HTTP {status}"

    def test_keeps_an_unknown_code_as_a_string(self) -> None:
        with pytest.raises(KiroraError) as caught:
            Server(error(409, "SOMETHING_NEW", "new")).client().me()
        assert caught.value.code == "SOMETHING_NEW"
        assert not caught.value.is_known_code()

    def test_every_sdk_error_is_a_kirora_exception(self) -> None:
        for cls in (KiroraError, KiroraConnectionError, KiroraTimeoutError, KiroraResponseError):
            assert issubclass(cls, kirora.KiroraException)

    def test_reads_retry_after_as_seconds_or_an_http_date(self) -> None:
        future = dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=20)
        dates = [
            email.utils.format_datetime(future, usegmt=True),
            future.strftime("%A, %d-%b-%y %H:%M:%S GMT"),
            future.strftime("%a %b %e %H:%M:%S %Y"),
        ]
        for header, low, high in [("12", 12, 12), ("1.5", 1.5, 1.5), *[(d, 15, 21) for d in dates]]:
            with pytest.raises(KiroraError) as caught:
                Server(error(429, "RATE_LIMITED", **{"retry-after": header})).client(max_retries=0).me()
            assert caught.value.retry_after is not None
            assert low <= caught.value.retry_after <= high, header

    @pytest.mark.parametrize("header", ["-1", "soon", "Tue, 3 Jun 2008 11:05:30 GMT"])
    def test_ignores_a_retry_after_that_isnt_valid(self, header: str) -> None:
        with pytest.raises(KiroraError) as caught:
            Server(error(429, "RATE_LIMITED", **{"retry-after": header})).client(max_retries=0).me()
        assert caught.value.retry_after is None


class TestRetries:
    def test_retries_a_429_and_succeeds(self, no_waiting: List[float]) -> None:
        server = Server(error(429, "RATE_LIMITED", **{"retry-after": "2"}), ok({"id": "x"}))
        assert server.client().me() == {"id": "x"}
        assert len(server.requests) == 2
        assert 2 <= no_waiting[0] <= 2.5

    def test_gives_the_caller_a_wait_longer_than_max_retry_delay(self, no_waiting: List[float]) -> None:
        server = Server(error(429, "RATE_LIMITED", **{"retry-after": "60"}))
        with pytest.raises(KiroraError) as caught:
            server.client(max_retry_delay=30).me()
        assert caught.value.retry_after == 60
        assert no_waiting == []

    def test_backs_off_exponentially(self, no_waiting: List[float]) -> None:
        server = Server(*[error(500, "INTERNAL_ERROR")] * 4)
        with pytest.raises(KiroraError):
            server.client().me()
        assert len(server.requests) == 4
        for attempt, wait in enumerate(no_waiting):
            assert 0.75 * 2**attempt <= wait <= 1.25 * 2**attempt

    def test_does_not_retry_a_4xx(self) -> None:
        server = Server(error(400, "BAD_REQUEST"))
        with pytest.raises(KiroraError):
            server.client().me()
        assert len(server.requests) == 1

    def test_uses_a_calls_own_max_retries(self) -> None:
        server = Server(*[error(500, "INTERNAL_ERROR")] * 2)
        with pytest.raises(KiroraError):
            server.client().me({"max_retries": 1})
        assert len(server.requests) == 2

    def test_sends_the_same_bytes_and_key_on_each_attempt(self) -> None:
        server = Server(error(503, "SERVICE_UNAVAILABLE", **{"x-request-id": "r"}), ok(CONTACT))
        params = {"email": "ada@example.com"}
        server.client().contacts.identify(params)  # type: ignore[arg-type]
        first, second = server.requests
        assert first.content == second.content
        assert first.headers["idempotency-key"] == second.headers["idempotency-key"]

    def test_keys_each_entry_of_a_batch_once_for_every_attempt(self) -> None:
        server = Server(error(500, "INTERNAL_ERROR"), ok({"results": []}))
        server.client().events.track_batch(
            {
                "events": [
                    {"event": {"externalId": "u", "name": "A"}},
                    {"event": {"externalId": "u", "name": "B"}, "idempotencyKey": "mine"},
                ]
            }
        )
        first, second = (server.body(0)["events"], server.body(1)["events"])
        assert first == second
        assert is_uuid(first[0]["idempotencyKey"])
        assert first[1]["idempotencyKey"] == "mine"
        # The batch itself takes no key.
        assert "idempotency-key" not in server.requests[0].headers

    def test_never_repeats_a_write_without_a_key_that_may_have_happened(self) -> None:
        server = Server(error(500, "INTERNAL_ERROR"))
        with pytest.raises(KiroraError):
            server.client().request("POST", "/v1/something-new", body={})
        assert len(server.requests) == 1

    def test_retries_any_request_whose_connection_was_never_made(self) -> None:
        server = Server(httpx.ConnectError("refused"), ok({}))
        server.client().request("POST", "/v1/something-new", body={})
        assert len(server.requests) == 2

    def test_retries_a_newer_endpoint_by_its_method_or_with_a_key(self) -> None:
        server = Server(error(500, "INTERNAL_ERROR"), ok({}), error(500, "INTERNAL_ERROR"), ok({}))
        client = server.client()
        client.request("PUT", "/v1/something-new/x", body={})
        client.request("POST", "/v1/something-new", body={}, idempotency_key="k")
        assert len(server.requests) == 4

    def test_retries_idempotency_key_in_use(self) -> None:
        server = Server(error(409, "IDEMPOTENCY_KEY_IN_USE"), ok({"id": "e"}, 201))
        server.client().events.track({"externalId": "u", "name": "A"})
        assert len(server.requests) == 2

    def test_retries_an_update_unless_it_changes_how_the_contact_is_found(self) -> None:
        server = Server(error(500, "INTERNAL_ERROR"), ok(CONTACT))
        server.client().contacts.update("Ada@Example.com ", {"email": "ada@example.com"}, id_type="email")
        assert len(server.requests) == 2
        for params in ({"email": "new@example.com"}, {"email": None}):
            server = Server(error(500, "INTERNAL_ERROR"))
            with pytest.raises(KiroraError):
                server.client().contacts.update("ada@example.com", params, id_type="email")  # type: ignore[arg-type]
            assert len(server.requests) == 1
        server = Server(error(500, "INTERNAL_ERROR"))
        with pytest.raises(KiroraError):
            server.client().contacts.update("user-1", {"externalId": "user-2"}, id_type="externalId")
        assert len(server.requests) == 1

    def test_counts_a_404_on_a_retried_delete_as_done(self) -> None:
        server = Server(error(500, "INTERNAL_ERROR", **{"x-request-id": "r"}), error(404, "NOT_FOUND"))
        assert server.client().lists.delete("l_1") is None
        # Unless no attempt could have deleted it.
        server = Server(error(503, "SERVICE_UNAVAILABLE"), error(404, "NOT_FOUND"))
        with pytest.raises(KiroraError, match="NOT_FOUND"):
            server.client().lists.delete("l_1")
        server = Server(error(404, "NOT_FOUND"))
        with pytest.raises(KiroraError, match="NOT_FOUND"):
            server.client().lists.delete("l_1")

    def test_reports_a_timeout_and_retries_it_when_safe(self) -> None:
        server = Server(httpx.ReadTimeout("slow"), ok({}))
        server.client().me()
        assert len(server.requests) == 2
        server = Server(httpx.ReadTimeout("slow"))
        with pytest.raises(KiroraTimeoutError, match="timed out after 5s"):
            server.client(timeout=5).request("POST", "/v1/something-new", body={})
        assert len(server.requests) == 1

    def test_a_connect_timeout_never_reached_the_api(self) -> None:
        server = Server(httpx.ConnectTimeout("slow"), ok({}))
        server.client().request("POST", "/v1/something-new", body={})
        assert len(server.requests) == 2

    def test_wraps_a_network_failure(self) -> None:
        server = Server(*[httpx.ReadError("reset")] * 4)
        with pytest.raises(KiroraConnectionError) as caught:
            server.client().me()
        assert isinstance(caught.value.__cause__, httpx.ReadError)
        assert "GET /v1/me failed: reset" in str(caught.value)

    def test_times_out_a_body_still_arriving_after_the_timeout(self) -> None:
        body = Delayed((0, b'{"data":'), (0.05, b"{"), (0, b"}}"))
        server = Server(lambda request: httpx.Response(200, stream=body))
        with pytest.raises(KiroraTimeoutError):
            server.client(timeout=0.01, max_retries=0).me()

    def test_times_out_a_body_whose_last_chunk_arrives_after_the_timeout(self) -> None:
        # `timeout` limits the attempt, including reading the response, as in Node.
        body = Delayed((0, b'{"data":'), (0.05, b'{"id":"x"}}'))
        server = Server(lambda request: httpx.Response(200, stream=body))
        with pytest.raises(KiroraTimeoutError):
            server.client(timeout=0.01, max_retries=0).me()

    def test_times_out_headers_and_a_body_late_only_together(self) -> None:
        def slow_headers(request: httpx.Request) -> httpx.Response:
            time.sleep(0.14)
            return httpx.Response(200, stream=Delayed((0.14, b'{"data":{}}')))

        server = Server(slow_headers)
        with pytest.raises(KiroraTimeoutError):
            server.client(timeout=0.2, max_retries=0).me()

    def test_times_out_headers_that_arrive_after_the_timeout(self) -> None:
        def slow(request: httpx.Request) -> httpx.Response:
            time.sleep(0.05)
            return ok({})

        server = Server(slow, ok({"id": "x"}))
        # A read, so the timed-out attempt is retried.
        assert server.client(timeout=0.02).me() == {"id": "x"}
        assert len(server.requests) == 2

    def test_names_an_error_without_a_message_by_its_type(self) -> None:
        server = Server(httpx.ReadError(""))
        with pytest.raises(KiroraConnectionError, match=r"GET /v1/me failed: ReadError$"):
            server.client(max_retries=0).me()


class TestReviewFixes:
    @pytest.mark.parametrize("external_id", [None, "", 42])
    def test_for_workspace_refuses_a_missing_id_rather_than_drop_the_scope(self, external_id: object) -> None:
        server = Server()
        parent = server.client(workspace="tenant-a")
        with pytest.raises(TypeError if external_id != "" else ValueError, match="external_id"):
            parent.for_workspace(external_id)  # type: ignore[arg-type]
        assert server.requests == []
        # The parent keeps its own scope.
        server.replies.append(ok({}))
        parent.me()
        assert server.last.headers["kirora-workspace"] == "tenant-a"

    def test_refuses_a_key_for_an_operation_that_doesnt_take_one(self) -> None:
        # The spec's table decides, for resource methods and raw requests alike.
        server = Server()
        client = server.client()
        with pytest.raises(ValueError, match="GET /v1/contacts/c_1 doesn't take an idempotency key"):
            client.contacts.get("c_1", {"idempotency_key": "k"})  # type: ignore[call-arg]
        with pytest.raises(ValueError, match="doesn't take an idempotency key"):
            client.request_list("/v1/contacts", idempotency_key="k1")
        with pytest.raises(ValueError, match="doesn't take an idempotency key"):
            client.events.track_batch({"events": []}, {"headers": {"Idempotency-Key": "k"}})
        assert server.requests == []
        # One that takes a key gets the caller's, and one newer than the SDK is trusted to.
        server = Server(ok({}))
        server.client().request("POST", "/v1/contacts/identify", body={}, idempotency_key="k2")
        assert server.last.headers["idempotency-key"] == "k2"
        server = Server(ok({}))
        server.client().request("POST", "/v1/something-new", body={}, idempotency_key="k3")
        assert server.last.headers["idempotency-key"] == "k3"

    def test_response_info_can_be_hashed(self) -> None:
        info = last_response(Server(ok({})).client().me())
        assert info is not None
        assert info in {info}

    def test_messages_list_sends_every_filter(self) -> None:
        server = Server(page([]))
        server.client().messages.list(
            {
                "limit": 5,
                "cursor": "c",
                "status": "bounced",
                "channel": "email",
                "recipient": "a@b.co",
                "query": "q",
                "messageType": "marketing",
                "campaignId": "cmp",
                "journeyId": "j",
                "stepId": "s",
                "templateId": "t",
                "correlationId": "corr",
                "sent": True,
                "delivered": False,
                "opened": True,
                "clicked": False,
                "createdAfter": "2026-01-01T00:00:00Z",
                "createdBefore": "2026-02-01T00:00:00Z",
            }
        )
        assert dict(server.last.url.params) == {
            "limit": "5",
            "cursor": "c",
            "status": "bounced",
            "channel": "email",
            "recipient": "a@b.co",
            "query": "q",
            "messageType": "marketing",
            "campaignId": "cmp",
            "journeyId": "j",
            "stepId": "s",
            "templateId": "t",
            "correlationId": "corr",
            "sent": "true",
            "delivered": "false",
            "opened": "true",
            "clicked": "false",
            "createdAfter": "2026-01-01T00:00:00Z",
            "createdBefore": "2026-02-01T00:00:00Z",
        }


class TestReviewFixesTwo:
    def test_a_closed_client_and_its_workspace_clients_open_new_connections(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        server = Server(ok({}), ok({}), ok({}))
        server.patch_opened(monkeypatch)
        parent = Kirora(API_KEY)
        child = parent.for_workspace("tenant-1")
        assert child._connections is parent._connections
        parent.me()
        parent.close()
        child.me()
        parent.me()
        assert len(server.requests) == 3
        assert server.requests[1].headers["kirora-workspace"] == "tenant-1"

    def test_closing_a_workspace_client_leaves_its_parent_open(self) -> None:
        server = Server(ok({}))
        parent = server.client()
        parent.for_workspace("tenant-1").close()
        parent.me()
        assert len(server.requests) == 1

    def test_cuts_off_an_error_body_at_the_deadline_keeping_its_status(self) -> None:
        body = Delayed((0, b'{"error":{"code":"IDEMPOTENCY_KEY_IN_USE",'), (0.05, b'"message":"Busy"}}'))
        server = Server(
            lambda request: httpx.Response(409, stream=body, headers={"x-request-id": "req_slow"})
        )
        started = time.monotonic()
        with pytest.raises(kirora.ConflictError) as caught:
            server.client(timeout=0.01).events.track({"externalId": "u", "name": "A"})
        # The deadline holds; the status and headers say what's known, not the body's code.
        assert time.monotonic() - started < 0.5
        assert caught.value.status == 409
        assert caught.value.code == "CONFLICT"
        assert caught.value.request_id == "req_slow"
        assert len(server.requests) == 1

    def test_retries_a_5xx_whose_body_is_cut_off_at_the_deadline(self) -> None:
        body = Delayed((0, b'{"error":'), (0.05, b'{"code":"INTERNAL_ERROR"}}'))
        server = Server(
            lambda request: httpx.Response(503, stream=body, headers={"x-request-id": "r"}), ok({})
        )
        server.client(timeout=0.01).me()
        assert len(server.requests) == 2

    def test_raises_the_404_of_a_retried_raw_delete(self) -> None:
        # A raw call is promised a response, so the 404 isn't turned into a result.
        server = Server(httpx.ReadTimeout("slow"), error(404, "NOT_FOUND"))
        with pytest.raises(kirora.NotFoundError), server.client().request_raw("DELETE", "/v1/contacts/c"):
            pass
        assert len(server.requests) == 2
        # A void delete still counts the 404 as done.
        server = Server(httpx.ReadTimeout("slow"), error(404, "NOT_FOUND"))
        assert server.client().contacts.delete("contact-1") is None

    def test_counts_a_404_on_a_retried_delete_as_done_from_request_data(self) -> None:
        server = Server(error(500, "INTERNAL_ERROR", **{"x-request-id": "r"}), error(404, "NOT_FOUND"))
        assert server.client().request_data("DELETE", "/v1/lists/l_1") is None


class TestPagination:
    def test_walks_pages_and_stops_on_a_null_cursor_not_an_empty_page(self) -> None:
        server = Server(page([{"id": 1}], "c2"), page([], "c3"), page([{"id": 3}]))
        client = server.client()
        ids = [item["id"] for item in client.lists.list({"query": "vip", "limit": 1})]
        assert ids == [1, 3]
        assert [r.url.params.get("cursor") for r in server.requests] == [None, "c2", "c3"]
        assert all(r.url.params["query"] == "vip" for r in server.requests)

    def test_returns_the_first_page_with_its_cursor(self) -> None:
        server = Server(page([{"id": 1}], "c2", count=5))
        first = server.client().contacts.list()
        assert first.data == [{"id": 1}]
        assert first.next_cursor == "c2"
        assert first.has_next_page()
        assert first.meta["count"] == 5
        assert first.last_response.status == 200
        assert last_response(first) is first.last_response

    def test_fetches_the_next_page_on_request(self) -> None:
        server = Server(page([{"id": 1}], "c2"), page([{"id": 2}]))
        second = server.client().lists.list().next_page()
        assert second is not None
        assert second.data == [{"id": 2}]
        assert second.next_page() is None

    def test_stops_on_a_cursor_that_comes_round_again(self) -> None:
        server = Server(page([{"id": 1}], "c2"), page([{"id": 2}], "c2"))
        with pytest.raises(KiroraResponseError, match="came round again"):
            list(server.client().lists.list())

    def test_keeps_the_options_it_was_given_for_later_pages(self) -> None:
        server = Server(page([], "c2"), page([]))
        headers = {"x-trace": "1"}
        first = server.client().workspaces.list(None, {"headers": headers, "workspace": "t"})
        headers["x-trace"] = "2"
        list(first)
        assert [r.headers["x-trace"] for r in server.requests] == ["1", "1"]
        assert server.requests[1].headers["kirora-workspace"] == "t"


def test_binds_each_resource_once_per_client() -> None:
    client = Kirora(API_KEY)
    assert client.contacts is client.contacts
    assert client.contacts._client is client
    assert Kirora.contacts is kirora.Contacts
    assert client.for_workspace("t").contacts is not client.contacts
