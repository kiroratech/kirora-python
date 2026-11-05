"""``kirora.Messages``: each method reaches its endpoint and returns its result."""

from __future__ import annotations

import kirora

from .conftest import Server, ok, page
from .resources_test import operation_of


class TestMessages:
    def test_list(self) -> None:
        server = Server(page([]))
        server.install()
        kirora.Messages.list({"opened": True})
        assert operation_of(server.last) == "listMessages"

    def test_get(self) -> None:
        server = Server(ok({}))
        server.install()
        kirora.Messages.get("m")
        assert operation_of(server.last) == "getMessage"
