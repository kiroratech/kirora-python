"""``kirora.Suppressions``: each method reaches its endpoint and returns its result."""

from __future__ import annotations

import kirora

from .conftest import Server, ok, page
from .resources_test import operation_of


class TestSuppressions:
    def test_list(self) -> None:
        server = Server(page([]))
        server.install()
        kirora.Suppressions.list()
        assert operation_of(server.last) == "listSuppressions"

    def test_add(self) -> None:
        server = Server(ok({}))
        server.install()
        kirora.Suppressions.add({"emails": []})
        assert operation_of(server.last) == "addSuppressions"

    def test_delete(self) -> None:
        server = Server(ok({}))
        server.install()
        kirora.Suppressions.delete({"emails": []})
        assert operation_of(server.last) == "deleteSuppressions"
