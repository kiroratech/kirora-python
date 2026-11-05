"""``kirora.EmbedSessions``: each method reaches its endpoint and returns its result."""

from __future__ import annotations

import kirora

from .conftest import Server, ok
from .resources_test import operation_of


class TestEmbedSessions:
    def test_create(self) -> None:
        server = Server(ok({}, 201))
        server.install()
        kirora.EmbedSessions.create({})  # type: ignore[typeddict-item]
        assert operation_of(server.last) == "createEmbedSession"
