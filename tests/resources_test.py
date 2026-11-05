"""Every resource method calls the endpoint of the spec operation it wraps."""

from __future__ import annotations

import ast
import inspect
from pathlib import Path
from typing import Any, Callable, List, Tuple

import httpx
import pytest

import kirora
from kirora import Kirora
from kirora._retry import operation_for, with_entry_keys

from .conftest import Server, ok, page

ROOT = Path(__file__).resolve().parent.parent

RESOURCES = [
    kirora.Campaigns,
    kirora.Contacts,
    kirora.EmbedSessions,
    kirora.Events,
    kirora.Lists,
    kirora.Messages,
    kirora.Segments,
    kirora.Suppressions,
    kirora.Transactional,
    kirora.Workspaces,
]

# (operationId, a call, the reply it gets).
CALLS: List[Tuple[str, Callable[[Kirora], Any], httpx.Response]] = [
    ("listCampaigns", lambda k: k.campaigns.list({"status": "draft"}), page([])),
    ("getCampaign", lambda k: k.campaigns.get("cmp"), ok({})),
    ("createCampaign", lambda k: k.campaigns.create({"name": "n"}), ok({}, 201)),
    ("sendCampaign", lambda k: k.campaigns.send("cmp"), ok({}, 202)),
    ("triggerCampaign", lambda k: k.campaigns.trigger("cmp", {"recipients": []}), ok({}, 202)),
    ("scheduleCampaign", lambda k: k.campaigns.schedule("cmp", {}), ok({})),  # type: ignore[typeddict-item]
    ("getCampaignEligibility", lambda k: k.campaigns.eligibility("cmp"), ok({})),
    ("listContacts", lambda k: k.contacts.list(), page([])),
    ("getContact", lambda k: k.contacts.get("c"), ok({})),
    ("updateContact", lambda k: k.contacts.update("c", {}), ok({})),
    ("deleteContact", lambda k: k.contacts.delete("c"), httpx.Response(204)),
    ("identifyContact", lambda k: k.contacts.identify({"email": "a@b.co"}), ok({})),
    ("identifyContactsBatch", lambda k: k.contacts.identify_batch({"contacts": []}), ok({})),
    ("deleteContacts", lambda k: k.contacts.delete_batch({"contacts": []}), ok({})),  # type: ignore[typeddict-item]
    ("mergeContacts", lambda k: k.contacts.merge("c", {"keep": "d"}), ok({})),  # type: ignore[typeddict-item]
    ("getContactExport", lambda k: k.contacts.export("c"), ok({})),
    ("listContactLists", lambda k: k.contacts.list_lists("c"), page([])),
    ("listContactTopics", lambda k: k.contacts.list_topics("c"), ok([])),
    ("setContactTopic", lambda k: k.contacts.set_topic("c", "t", {}), ok({})),  # type: ignore[typeddict-item]
    ("listPushInstallations", lambda k: k.contacts.list_installations("c"), page([])),
    ("registerPushInstallation", lambda k: k.contacts.register_installation("c", {}), ok({})),  # type: ignore[arg-type]
    ("deletePushInstallation", lambda k: k.contacts.delete_installation("c", "i"), httpx.Response(204)),
    ("createEmbedSession", lambda k: k.embed_sessions.create({}), ok({}, 201)),  # type: ignore[typeddict-item]
    ("getMe", lambda k: k.me(), ok({})),
    ("listMessages", lambda k: k.messages.list({"opened": True}), page([])),
    ("getMessage", lambda k: k.messages.get("m"), ok({})),
    ("listSuppressions", lambda k: k.suppressions.list(), page([])),
    ("addSuppressions", lambda k: k.suppressions.add({"emails": []}), ok({})),
    ("deleteSuppressions", lambda k: k.suppressions.delete({"emails": []}), ok({})),
    ("listWorkspaces", lambda k: k.workspaces.list(), page([])),
    ("createWorkspace", lambda k: k.workspaces.create({}), ok({}, 201)),  # type: ignore[typeddict-item]
    ("getWorkspace", lambda k: k.workspaces.get("w"), ok({})),
    ("updateWorkspace", lambda k: k.workspaces.update("w", {}), ok({})),
    ("deleteWorkspace", lambda k: k.workspaces.delete("w"), ok({})),
    ("suspendWorkspace", lambda k: k.workspaces.suspend("w"), ok({})),
    ("resumeWorkspace", lambda k: k.workspaces.resume("w"), ok({})),
    ("cancelWorkspaceDeletion", lambda k: k.workspaces.cancel_deletion("w"), ok({})),
    ("trackEvent", lambda k: k.events.track({"email": "a@b.co", "name": "x"}), ok({}, 201)),
    ("trackEventsBatch", lambda k: k.events.track_batch({"events": []}), ok({})),
    ("listLists", lambda k: k.lists.list(), page([])),
    ("getList", lambda k: k.lists.get("l"), ok({})),
    ("createList", lambda k: k.lists.create({"name": "n"}), ok({}, 201)),
    ("updateList", lambda k: k.lists.update("l", {}), ok({})),
    ("deleteList", lambda k: k.lists.delete("l"), httpx.Response(204)),
    ("addListContacts", lambda k: k.lists.add_contacts("l", {}), ok({})),  # type: ignore[arg-type]
    ("deleteListContacts", lambda k: k.lists.delete_contacts("l", {}), ok({})),  # type: ignore[arg-type]
    ("sendTransactionalMessage", lambda k: k.transactional.send({}), ok({}, 202)),  # type: ignore[typeddict-item]
    ("sendTransactionalMessagesBatch", lambda k: k.transactional.send_batch({"messages": []}), ok({}, 202)),
    ("listContactSegments", lambda k: k.contacts.list_segments("c", {"query": "vip"}), page([])),
    ("listSegments", lambda k: k.segments.list({"tag": "core"}), page([])),
    ("createSegment", lambda k: k.segments.create({"name": "n", "rules": {"all": []}}), ok({}, 201)),
    ("getSegment", lambda k: k.segments.get("s"), ok({})),
    ("updateSegment", lambda k: k.segments.update("s", {}), ok({})),
    ("deleteSegment", lambda k: k.segments.delete("s"), httpx.Response(204)),
    ("previewSegment", lambda k: k.segments.preview({"rules": {"all": []}}), ok({})),
    ("listSegmentContacts", lambda k: k.segments.list_contacts("s"), page([])),
    (
        "listSegmentMembershipChanges",
        lambda k: k.segments.list_membership_changes("s", {"change": "joined", "day": "2026-11-01"}),
        page([]),
    ),
    ("getSegmentSizeHistory", lambda k: k.segments.size_history("s"), ok({})),
    ("getSegmentUsage", lambda k: k.segments.usage("s"), ok({})),
    ("cancelScheduledTransactionalMessage", lambda k: k.transactional.cancel("m"), ok({})),  # type: ignore[typeddict-item]  # type: ignore[typeddict-item]  # type: ignore[typeddict-item]
]


def operation_of(request: httpx.Request) -> str:
    """The id of the spec operation ``request`` reached, checking it sent an idempotency
    key exactly when the operation takes one."""
    found = operation_for(request.method, request.url.path.split("/"))
    assert found is not None, f"{request.method} {request.url.path} isn't in the spec"
    assert ("idempotency-key" in request.headers) == found.accepts_key
    return found.id


@pytest.mark.parametrize(("operation_id", "call", "reply"), CALLS, ids=[c[0] for c in CALLS])
def test_each_method_calls_its_operation(
    operation_id: str, call: Callable[[Kirora], Any], reply: Any
) -> None:
    server = Server(reply)
    call(server.client())
    assert operation_of(server.last) == operation_id


def test_every_wrapped_operation_has_a_method() -> None:
    tree = ast.parse((ROOT / "scripts" / "codegen.py").read_text())
    wrapped = next(
        ast.literal_eval(node.value)
        for node in tree.body
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", None) == "OPERATIONS"
    )
    assert sorted(wrapped) == sorted(c[0] for c in CALLS)


def test_every_method_has_an_async_form_with_the_same_parameters() -> None:
    for resource in RESOURCES:
        methods = {
            n for n, f in vars(resource).items() if not n.startswith("_") and isinstance(f, classmethod)
        }
        sync = {n for n in methods if not n.endswith("_async")}
        assert {f"{n}_async" for n in sync} == methods - sync, resource.__name__
        for name in sync:
            sync_params = list(inspect.signature(getattr(resource, name)).parameters)
            async_params = list(inspect.signature(getattr(resource, f"{name}_async")).parameters)
            assert sync_params == async_params, f"{resource.__name__}.{name}"


def test_operation_for_prefers_a_literal_segment() -> None:
    assert operation_for("GET", ["", "v1", "templates", "gallery"]).id == "getTemplateGallery"  # type: ignore[union-attr]
    assert operation_for("GET", ["", "v1", "templates", "x"]).id == "getTemplate"  # type: ignore[union-attr]
    assert operation_for("GET", ["", "v1", "nothing-here"]) is None


def test_with_entry_keys_keys_only_entries_without_one() -> None:
    body = {"events": [{"name": "a"}, {"name": "b", "idempotencyKey": "k"}, "odd"], "other": 1}
    keyed = with_entry_keys(body, "events")
    assert keyed["events"][1] == {"name": "b", "idempotencyKey": "k"}
    assert keyed["events"][2] == "odd"
    assert isinstance(keyed["events"][0]["idempotencyKey"], str)
    assert "idempotencyKey" not in body["events"][0]
    assert with_entry_keys([1], "events") == [1]
