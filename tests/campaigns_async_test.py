"""``kirora.Campaigns`` async methods: each method reaches its endpoint and returns its result."""

from __future__ import annotations

import pytest

import kirora

from .conftest import Server, ok, page
from .resources_test import operation_of

pytestmark = pytest.mark.asyncio


class TestCampaignsAsync:
    async def test_list(self) -> None:
        server = Server(page([]))
        server.install()
        await kirora.Campaigns.list_async({"status": "draft"})
        assert operation_of(server.last) == "listCampaigns"

    async def test_get(self) -> None:
        server = Server(ok({}))
        server.install()
        await kirora.Campaigns.get_async("cmp")
        assert operation_of(server.last) == "getCampaign"

    async def test_create(self) -> None:
        server = Server(ok({}, 201))
        server.install()
        await kirora.Campaigns.create_async({"name": "n"})
        assert operation_of(server.last) == "createCampaign"

    async def test_send(self) -> None:
        server = Server(ok({}, 202))
        server.install()
        await kirora.Campaigns.send_async("cmp")
        assert operation_of(server.last) == "sendCampaign"

    async def test_trigger(self) -> None:
        server = Server(ok({}, 202))
        server.install()
        await kirora.Campaigns.trigger_async("cmp", {"recipients": []})
        assert operation_of(server.last) == "triggerCampaign"

    async def test_schedule(self) -> None:
        server = Server(ok({}))
        server.install()
        await kirora.Campaigns.schedule_async("cmp", {})  # type: ignore[typeddict-item]
        assert operation_of(server.last) == "scheduleCampaign"

    async def test_eligibility(self) -> None:
        server = Server(ok({}))
        server.install()
        await kirora.Campaigns.eligibility_async("cmp")
        assert operation_of(server.last) == "getCampaignEligibility"
