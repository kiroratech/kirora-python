"""``kirora.Campaigns``: each method reaches its endpoint and returns its result."""

from __future__ import annotations

import kirora

from .conftest import Server, ok, page
from .resources_test import operation_of


class TestCampaigns:
    def test_list(self) -> None:
        server = Server(page([]))
        server.install()
        kirora.Campaigns.list({"status": "draft"})
        assert operation_of(server.last) == "listCampaigns"

    def test_get(self) -> None:
        server = Server(ok({}))
        server.install()
        kirora.Campaigns.get("cmp")
        assert operation_of(server.last) == "getCampaign"

    def test_create(self) -> None:
        server = Server(ok({}, 201))
        server.install()
        kirora.Campaigns.create({"name": "n"})
        assert operation_of(server.last) == "createCampaign"

    def test_send(self) -> None:
        server = Server(ok({}, 202))
        server.install()
        kirora.Campaigns.send("cmp")
        assert operation_of(server.last) == "sendCampaign"

    def test_trigger(self) -> None:
        server = Server(ok({}, 202))
        server.install()
        kirora.Campaigns.trigger("cmp", {"recipients": []})
        assert operation_of(server.last) == "triggerCampaign"

    def test_schedule(self) -> None:
        server = Server(ok({}))
        server.install()
        kirora.Campaigns.schedule("cmp", {})  # type: ignore[typeddict-item]
        assert operation_of(server.last) == "scheduleCampaign"

    def test_eligibility(self) -> None:
        server = Server(ok({}))
        server.install()
        kirora.Campaigns.eligibility("cmp")
        assert operation_of(server.last) == "getCampaignEligibility"
