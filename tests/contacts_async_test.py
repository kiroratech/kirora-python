"""``kirora.Contacts`` async methods: each method reaches its endpoint and returns its result."""

from __future__ import annotations

import httpx
import pytest

import kirora

from .conftest import Server, ok, page
from .resources_test import operation_of

pytestmark = pytest.mark.asyncio


class TestContactsAsync:
    async def test_list(self) -> None:
        server = Server(page([]))
        server.install()
        await kirora.Contacts.list_async()
        assert operation_of(server.last) == "listContacts"

    async def test_get(self) -> None:
        server = Server(ok({}))
        server.install()
        await kirora.Contacts.get_async("c")
        assert operation_of(server.last) == "getContact"

    async def test_update(self) -> None:
        server = Server(ok({}))
        server.install()
        await kirora.Contacts.update_async("c", {})
        assert operation_of(server.last) == "updateContact"

    async def test_delete(self) -> None:
        server = Server(httpx.Response(204))
        server.install()
        await kirora.Contacts.delete_async("c")
        assert operation_of(server.last) == "deleteContact"

    async def test_identify(self) -> None:
        server = Server(ok({}))
        server.install()
        await kirora.Contacts.identify_async({"email": "a@b.co"})
        assert operation_of(server.last) == "identifyContact"

    async def test_identify_batch(self) -> None:
        server = Server(ok({}))
        server.install()
        await kirora.Contacts.identify_batch_async({"contacts": []})
        assert operation_of(server.last) == "identifyContactsBatch"

    async def test_delete_batch(self) -> None:
        server = Server(ok({}))
        server.install()
        await kirora.Contacts.delete_batch_async({"contacts": []})  # type: ignore[typeddict-item]
        assert operation_of(server.last) == "deleteContacts"

    async def test_merge(self) -> None:
        server = Server(ok({}))
        server.install()
        await kirora.Contacts.merge_async("c", {"keep": "d"})  # type: ignore[typeddict-item]
        assert operation_of(server.last) == "mergeContacts"

    async def test_export(self) -> None:
        server = Server(ok({}))
        server.install()
        await kirora.Contacts.export_async("c")
        assert operation_of(server.last) == "getContactExport"

    async def test_list_lists(self) -> None:
        server = Server(page([]))
        server.install()
        await kirora.Contacts.list_lists_async("c")
        assert operation_of(server.last) == "listContactLists"

    async def test_list_topics(self) -> None:
        server = Server(ok([]))
        server.install()
        await kirora.Contacts.list_topics_async("c")
        assert operation_of(server.last) == "listContactTopics"

    async def test_set_topic(self) -> None:
        server = Server(ok({}))
        server.install()
        await kirora.Contacts.set_topic_async("c", "t", {})  # type: ignore[typeddict-item]
        assert operation_of(server.last) == "setContactTopic"

    async def test_list_installations(self) -> None:
        server = Server(page([]))
        server.install()
        await kirora.Contacts.list_installations_async("c")
        assert operation_of(server.last) == "listPushInstallations"

    async def test_register_installation(self) -> None:
        server = Server(ok({}))
        server.install()
        await kirora.Contacts.register_installation_async("c", {})  # type: ignore[arg-type]
        assert operation_of(server.last) == "registerPushInstallation"

    async def test_delete_installation(self) -> None:
        server = Server(httpx.Response(204))
        server.install()
        await kirora.Contacts.delete_installation_async("c", "i")
        assert operation_of(server.last) == "deletePushInstallation"
