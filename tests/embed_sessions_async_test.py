"""``kirora.EmbedSessions`` async methods: each method reaches its endpoint and returns its result."""

from __future__ import annotations

import pytest

import kirora

from .conftest import Server, ok
from .resources_test import operation_of

pytestmark = pytest.mark.asyncio


class TestEmbedSessionsAsync:
    async def test_create(self) -> None:
        server = Server(ok({}, 201))
        server.install()
        await kirora.EmbedSessions.create_async({})  # type: ignore[typeddict-item]
        assert operation_of(server.last) == "createEmbedSession"
