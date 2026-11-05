"""``kirora.Contacts``: each method reaches its endpoint and returns its result."""

from __future__ import annotations

import httpx

import kirora

from .conftest import Server, ok, page
from .resources_test import operation_of


class TestContacts:
    def test_list(self) -> None:
        server = Server(page([]))
        server.install()
        kirora.Contacts.list()
        assert operation_of(server.last) == "listContacts"

    def test_get(self) -> None:
        server = Server(ok({}))
        server.install()
        kirora.Contacts.get("c")
        assert operation_of(server.last) == "getContact"

    def test_update(self) -> None:
        server = Server(ok({}))
        server.install()
        kirora.Contacts.update("c", {})
        assert operation_of(server.last) == "updateContact"

    def test_delete(self) -> None:
        server = Server(httpx.Response(204))
        server.install()
        kirora.Contacts.delete("c")
        assert operation_of(server.last) == "deleteContact"

    def test_identify(self) -> None:
        server = Server(ok({}))
        server.install()
        kirora.Contacts.identify({"email": "a@b.co"})
        assert operation_of(server.last) == "identifyContact"

    def test_identify_batch(self) -> None:
        server = Server(ok({}))
        server.install()
        kirora.Contacts.identify_batch({"contacts": []})
        assert operation_of(server.last) == "identifyContactsBatch"

    def test_delete_batch(self) -> None:
        server = Server(ok({}))
        server.install()
        kirora.Contacts.delete_batch({"contacts": []})  # type: ignore[typeddict-item]
        assert operation_of(server.last) == "deleteContacts"

    def test_merge(self) -> None:
        server = Server(ok({}))
        server.install()
        kirora.Contacts.merge("c", {"keep": "d"})  # type: ignore[typeddict-item]
        assert operation_of(server.last) == "mergeContacts"

    def test_export(self) -> None:
        server = Server(ok({}))
        server.install()
        kirora.Contacts.export("c")
        assert operation_of(server.last) == "getContactExport"

    def test_list_lists(self) -> None:
        server = Server(page([]))
        server.install()
        kirora.Contacts.list_lists("c")
        assert operation_of(server.last) == "listContactLists"

    def test_list_topics(self) -> None:
        server = Server(ok([]))
        server.install()
        kirora.Contacts.list_topics("c")
        assert operation_of(server.last) == "listContactTopics"

    def test_set_topic(self) -> None:
        server = Server(ok({}))
        server.install()
        kirora.Contacts.set_topic("c", "t", {})  # type: ignore[typeddict-item]
        assert operation_of(server.last) == "setContactTopic"

    def test_list_installations(self) -> None:
        server = Server(page([]))
        server.install()
        kirora.Contacts.list_installations("c")
        assert operation_of(server.last) == "listPushInstallations"

    def test_register_installation(self) -> None:
        server = Server(ok({}))
        server.install()
        kirora.Contacts.register_installation("c", {})  # type: ignore[arg-type]
        assert operation_of(server.last) == "registerPushInstallation"

    def test_delete_installation(self) -> None:
        server = Server(httpx.Response(204))
        server.install()
        kirora.Contacts.delete_installation("c", "i")
        assert operation_of(server.last) == "deletePushInstallation"
