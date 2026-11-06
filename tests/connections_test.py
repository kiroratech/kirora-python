"""The async clients the SDK opens itself, one for each event loop."""

from __future__ import annotations

import asyncio
from typing import List

import pytest

import kirora

from .conftest import Server, ok


def test_opens_a_client_for_each_event_loop_and_forgets_closed_ones(monkeypatch: pytest.MonkeyPatch) -> None:
    server = Server(ok({}), ok({}))
    opened = server.patch_opened(monkeypatch)
    client = kirora.Kirora("sk_test")
    loops: List[asyncio.AbstractEventLoop] = []

    async def call() -> int:
        loops.append(asyncio.get_running_loop())
        await client.me_async()
        return len(client._connections._opened_async)

    assert asyncio.run(call()) == 1
    assert asyncio.run(call()) == 1
    assert loops[0].is_closed()
    assert len(opened) == 2


def test_aclose_before_any_call_does_nothing() -> None:
    client = kirora.Kirora("sk_test")
    asyncio.run(client.aclose())
    assert len(client._connections._opened_async) == 0
