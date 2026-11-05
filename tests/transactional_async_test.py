"""``kirora.Transactional`` async methods: each method reaches its endpoint and returns its result."""

from __future__ import annotations

import pytest

import kirora

from .conftest import Server, ok
from .resources_test import operation_of

pytestmark = pytest.mark.asyncio


class TestTransactionalAsync:
    async def test_send(self) -> None:
        server = Server(ok({}, 202))
        server.install()
        await kirora.Transactional.send_async({})  # type: ignore[typeddict-item]
        assert operation_of(server.last) == "sendTransactionalMessage"

    async def test_send_batch(self) -> None:
        server = Server(ok({}, 202))
        server.install()
        await kirora.Transactional.send_batch_async({"messages": []})
        assert operation_of(server.last) == "sendTransactionalMessagesBatch"

    async def test_cancel(self) -> None:
        server = Server(ok({}))
        server.install()
        await kirora.Transactional.cancel_async("m")  # type: ignore[typeddict-item]  # type: ignore[typeddict-item]  # type: ignore[typeddict-item]
        assert operation_of(server.last) == "cancelScheduledTransactionalMessage"
