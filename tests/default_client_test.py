"""The module settings, as ``kirora.api_key``, which the resource classes use."""

from __future__ import annotations

import httpx
import pytest

import kirora

from .conftest import API_KEY, Server, ok


def test_resource_classes_use_the_module_settings() -> None:
    server = Server(ok({"id": "c"}))
    server.install()
    kirora.app_info = {"name": "shop", "version": "1.0"}
    kirora.Contacts.get("ada@example.com", id_type="email")
    request = server.last
    assert request.headers["authorization"] == f"Bearer {API_KEY}"
    assert request.headers["user-agent"].endswith(" shop/1.0")
    assert request.url.raw_path == b"/v1/contacts/ada%40example.com?idType=email"


def test_reads_a_changed_setting_on_the_next_call() -> None:
    server = Server(ok({}), ok({}))
    server.install()
    kirora.me()
    kirora.api_key = "sk_other"
    kirora.me()
    assert [r.headers["authorization"] for r in server.requests] == [f"Bearer {API_KEY}", "Bearer sk_other"]


def test_reads_the_key_from_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    server = Server(ok({}))
    server.install()
    kirora.api_key = None
    monkeypatch.setenv("KIRORA_API_KEY", "sk_from_env")
    kirora.me()
    assert server.last.headers["authorization"] == "Bearer sk_from_env"


def test_says_how_to_set_a_missing_key() -> None:
    with pytest.raises(ValueError, match=r"set kirora\.api_key or KIRORA_API_KEY"):
        kirora.Contacts.get("c")


def test_keeps_one_connection_pool_across_settings() -> None:
    kirora.api_key = API_KEY
    first = kirora.default_client()
    assert kirora.default_client() is first
    kirora.timeout = 5
    second = kirora.default_client()
    assert second is not first
    assert second._connections is first._connections


def test_a_bound_class_uses_its_client_not_the_settings() -> None:
    server = Server(ok({}))
    client = server.client(workspace="tenant-a")
    kirora.api_key = "sk_module"
    client.contacts.get("c")
    assert server.last.headers["authorization"] == f"Bearer {API_KEY}"
    assert server.last.headers["kirora-workspace"] == "tenant-a"
    assert kirora.Contacts._client is None


def test_for_workspace_uses_the_module_settings() -> None:
    server = Server(ok({}))
    server.install()
    kirora.for_workspace("acme").lists.get("l")
    assert server.last.headers["kirora-workspace"] == "acme"
    assert server.last.headers["authorization"] == f"Bearer {API_KEY}"


def test_default_http_client_is_used_as_given() -> None:
    server = Server(ok({}))
    kirora.api_key = API_KEY
    kirora.default_http_client = httpx.Client(transport=httpx.MockTransport(server))
    kirora.me()
    assert len(server.requests) == 1


def test_sees_a_changed_environment_variable(monkeypatch: pytest.MonkeyPatch) -> None:
    server = Server(ok({}), ok({}))
    server.install()
    kirora.api_key = None
    monkeypatch.setenv("KIRORA_API_KEY", "sk_a")
    kirora.me()
    monkeypatch.setenv("KIRORA_API_KEY", "sk_b")
    kirora.me()
    assert [r.headers["authorization"] for r in server.requests] == ["Bearer sk_a", "Bearer sk_b"]
