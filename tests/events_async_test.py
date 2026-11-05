"""``kirora.Events`` async methods: each method reaches its endpoint and returns its result."""

from __future__ import annotations

import pytest

import kirora

from .conftest import Server, ok
from .resources_test import operation_of

pytestmark = pytest.mark.asyncio


class TestEventsAsync:
    async def test_track(self) -> None:
        server = Server(ok({}, 201))
        server.install()
        await kirora.Events.track_async({"email": "a@b.co", "name": "x"})
        assert operation_of(server.last) == "trackEvent"

    async def test_track_batch(self) -> None:
        server = Server(ok({}))
        server.install()
        await kirora.Events.track_batch_async({"events": []})
        assert operation_of(server.last) == "trackEventsBatch"
