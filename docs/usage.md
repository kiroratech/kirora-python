# Kirora Python SDK usage guide

This guide covers each part of the SDK in more depth than the [README](../README.md).
The snippets assume `import kirora`, with `KIRORA_API_KEY` set. The
[examples](../examples) hold runnable versions, which CI type-checks against the SDK.

## Contents

- [Usage](#usage): [contacts](#contacts), [events](#events),
  [transactional messages](#transactional-messages), [campaigns](#campaigns),
  [segments](#segments), [lists and suppressions](#lists-and-suppressions)
- [Types and optional fields](#types-and-optional-fields)
- [Pagination](#pagination)
- [Errors](#errors)
- [Settings](#settings)
- [Retries and idempotency](#retries-and-idempotency)
- [Async](#async)
- [Logging](#logging)
- [Webhooks](#webhooks)
- [Batch requests](#batch-requests)
- [Response details](#response-details)
- [User tokens](#user-tokens)
- [Partner workspaces](#partner-workspaces)
- [Other endpoints](#other-endpoints)
- [Testing your code](#testing-your-code)

## Usage

Each resource is a class whose methods you call directly, as
`kirora.Contacts.identify()`. A method takes the ids in its path first, then its
`params`, the request body or a list's filters, then its `options` for that call. Its
types sit on the class: `kirora.Contacts.IdentifyParams`, `kirora.Contacts.ListParams`
and so on.

### Contacts

`identify()` creates or updates a contact, matched by `externalId`, then `email`, then
`phone`; give at least one. Consent flags you leave out keep their value. Granting
consent needs a `statement` saying how the contact agreed:

```python
kirora.Contacts.identify(
    {
        "externalId": "customer-4821",
        "email": "amaka@example.com",
        "attributes": {"plan": "pro"},
        "consent": {"email": True, "statement": {"basis": "opted_in", "evidence": "Checkout opt-in"}},
    }
)
```

Methods that take a contact id read it as Kirora's id unless `id_type` says it's your
`"externalId"` or the contact's `"email"`:

```python
contact = kirora.Contacts.get("ada@example.com", id_type="email")
for membership in kirora.Contacts.list_lists("customer-4821", id_type="externalId"):
    print(membership["id"])
```

An update that changes the email or `externalId` the contact is looked up by isn't
retried after a network error or a 5xx, since a retry would look the contact up by its
old value.

### Events

Events need an existing contact. A workspace tracks at most 1,000 distinct event names,
so keep ids in `properties` rather than in the name:

```python
kirora.Events.track(
    {
        "externalId": "example-user-123",
        "name": "Order Completed",
        "properties": {"orderId": "order-123", "total": 49.99, "currency": "GBP"},
    },
    {"idempotency_key": "order-123-completed"},
)
```

### Transactional messages

```python
sent = kirora.Transactional.send(
    {
        "to": {"email": "customer@example.com"},
        "data": {"orderId": "order-123"},
        "email": {"template": "order-receipt"},
    },
    {"idempotency_key": "receipt-order-123"},
)
for skipped in sent["skippedChannels"]:
    print(skipped["channel"], skipped["code"])
```

Transactional sends ignore marketing preferences, but not suppressions. Cancel a send
scheduled with `sendAt` using `kirora.Transactional.cancel(message_id)`.

### Campaigns

Create a draft, check what would stop it sending, then schedule it:

```python
campaign = kirora.Campaigns.create({"name": "November newsletter", "segmentId": "SEGMENT_ID"})
eligibility = kirora.Campaigns.eligibility(campaign["id"])
if eligibility["canSend"]:
    kirora.Campaigns.schedule(campaign["id"], {"type": "fixed", "sendAt": "2026-11-20T09:00:00Z"})
else:
    for blocker in eligibility["blockers"]:
        print(blocker)
```

`send()` sends at once, and `trigger()` sends a draft to up to 5,000 recipients you name,
each with their own `data`. An unfinished draft raises a `ConflictError` with code
`DRAFT_INCOMPLETE`, with each missing field in `errors`.

### Segments

A segment is an audience defined by rules. Each send evaluates the rules live; the
stored membership behind `memberCount` and `Contacts.list({"segmentId": ...})` is
re-evaluated about every 15 minutes. Preview unsaved rules before creating a segment:

```python
rules: kirora.SegmentRulesInput = {
    "all": [{"type": "attribute", "field": "plan", "operator": "equals", "value": "pro"}]
}
preview = kirora.Segments.preview({"rules": rules})
print(preview["count"], "contacts match;", preview["reach"]["email"], "reachable by email")
segment = kirora.Segments.create({"name": "Pro plan", "rules": rules})
```

Then see who's in it, how it has changed, and what uses it:

```python
for contact in kirora.Segments.list_contacts(segment["id"]):  # Evaluated now.
    print(contact["id"])

joined = kirora.Segments.list_membership_changes(segment["id"], {"change": "joined", "day": dt.date(2026, 11, 1)})
print(joined.meta["count"], "joined that day")

history = kirora.Segments.size_history(segment["id"], {"from": dt.date(2026, 10, 1)})
for point in history["points"]:
    print(point["day"], point["memberCount"])

usage = kirora.Segments.usage(segment["id"])
if not (usage["campaigns"] or usage["segments"]):
    kirora.Segments.delete(segment["id"])
```

A report window's `from` is inclusive and `to` exclusive; each takes a date, which is a
day in the workspace's timezone, an aware `datetime`, or an ISO 8601 string. Deleting a
segment something still uses raises a `ConflictError` with code `IN_USE`.
`Contacts.list_segments()` lists the segments a contact is in.

### Lists and suppressions

```python
vip = kirora.Lists.create({"name": "VIP"})
added = kirora.Lists.add_contacts(vip["id"], {"emails": ["ada@example.com"]})
print(added["addedCount"], "added;", added["notFound"], "not found")

kirora.Suppressions.add({"emails": ["bounced@example.com"]})
for suppression in kirora.Suppressions.list({"email": "bounced@example.com"}):
    print(suppression["address"], suppression["reason"])
```

Only `manual` and `imported` suppressions can be removed with `Suppressions.delete()`.

## Types and optional fields

Request bodies, filters and results are plain dicts. Each is described by a `TypedDict`
generated from the OpenAPI spec, so mypy, pyright and your editor check field names and
value types. The request types are on each resource, as `kirora.Contacts.UpdateParams`;
the models are exported from `kirora`, as `kirora.ContactDetail`, and every generated
type is in `kirora.types`. Keys use the API's camelCase names, as in the
[API reference](https://kirora.io/docs/api/reference): your own keys inside
`attributes`, `properties` and `data` are sent exactly as given.

- Leave a field out of an update to keep its current value.
- Set a nullable field to `None` to clear it, and an `attributes` key to `None` to
  remove it.

```python
kirora.Contacts.update(contact["id"], {"phone": None, "attributes": {"plan": "pro", "trial": None}})
```

A list's filters take Python values: booleans for `"true"`/`"false"` filters, and
`datetime` or `date` objects for times, as well as ISO 8601 strings. A `datetime` must
be timezone-aware.

A result can carry fields newer than your version of the SDK; they come through as extra
keys. Annotate your own values with the types when you build them apart from the call:

```python
params: kirora.Contacts.IdentifyParams = {"email": "ada@example.com"}
```

## Pagination

A `list()` method fetches the first page and returns a `Page`. Iterating the page
yields every item, fetching later pages as it goes; `page.data` holds this page's items
alone:

```python
for contact in kirora.Contacts.list({"query": "ada"}):
    print(contact["id"], contact["email"])

page = kirora.Contacts.list({"query": "ada"})
print(page.data, page.next_cursor, page.meta)
```

Iterate `page.iter_pages()` to work a page at a time, or call `page.next_page()` for the
next one, which returns None after the last. To resume later, save `next_cursor` and pass
it back as `cursor` with the same filters:

```python
later = kirora.Contacts.list({"query": "ada", "cursor": saved_cursor})
```

Every page is fetched with the filters and options of the first. If the API returns a
cursor it has already returned, iteration raises `KiroraResponseError` rather than loop.

## Errors

| Exception                        | Raised for                                                                         |
| -------------------------------- | ---------------------------------------------------------------------------------- |
| `KiroraError`                    | An error response from the API. Branch on `code`.                                  |
| `BadRequestError`                | A 400, such as `VALIDATION_ERROR`. A subclass of `KiroraError`, as are those below. |
| `AuthenticationError`            | A 401: the key is missing, revoked, expired or unknown.                            |
| `PermissionDeniedError`          | A 403: the key can't do this, such as without a scope it needs.                    |
| `NotFoundError`                  | A 404.                                                                             |
| `ConflictError`                  | A 409, such as `ALREADY_EXISTS` or `DRAFT_INCOMPLETE`.                             |
| `RateLimitError`                 | A 429, after the SDK's own retries.                                                |
| `ServerError`                    | A 5xx, after the SDK's own retries.                                                |
| `KiroraConnectionError`          | No complete response: a network failure, or a connection dropped mid-body.         |
| `KiroraTimeoutError`             | An attempt that took longer than `timeout`. A subclass of `KiroraConnectionError`. |
| `KiroraResponseError`            | A response the SDK can't use, such as HTML from a proxy, or a redirect.            |
| `KiroraWebhookVerificationError` | A webhook that failed verification. Branch on `reason`.                            |

All of them subclass `KiroraException`, and are in `kirora.exceptions`. Invalid
arguments, such as an out-of-range `timeout` or an empty id, raise `ValueError` or
`TypeError` before anything is sent.

```python
try:
    kirora.Contacts.get("example-user-123", id_type="externalId")
except kirora.NotFoundError:
    return
except kirora.BadRequestError as error:
    for field_error in error.errors:
        print(field_error["field"], field_error["message"])
    raise
except kirora.KiroraError as error:
    print(f"Kirora error: code={error.code} status={error.status} request_id={error.request_id}")
    raise
```

`KiroraError` has `code`, `status`, `message`, `errors` (the fields a request got wrong,
on `VALIDATION_ERROR` and `DRAFT_INCOMPLETE`), `details`, `request_id`, `retry_after` (in
seconds), `rate_limit` and `last_response`, the HTTP response with its headers. A code
added to the API after your version of the SDK still comes through as a string;
`error.is_known_code()` says whether it's one of
`kirora.ERROR_CODES`. `error.is_retryable` is true for a 429, a 5xx other than 501 and
505, and `IDEMPOTENCY_KEY_IN_USE`.

`KiroraConnectionError.request_sent` is false when the connection was never made, so
the API never saw the request and sending it again is safe. Every SDK error can be
pickled, as for a task queue or a process pool.

## Settings

The resource classes read the module settings on each call, so a change applies to the
next one:

```python
import httpx

import kirora

kirora.api_key = os.environ["KIRORA_API_KEY"]
kirora.timeout = 10
kirora.max_retries = 2
kirora.app_info = {"name": "shop", "version": "1.2.0"}
kirora.default_http_client = httpx.Client(proxy="http://proxy.internal:3128")
```

The settings are listed in the [README](../README.md#settings). A `ValueError` is raised
on the next call for a missing API key, a base URL that isn't an absolute http or https
URL or has a query or fragment, or a setting out of range.

Every method takes these options for that call alone, as its `options` argument:

| Option            | Purpose                                                      |
| ----------------- | ------------------------------------------------------------ |
| `timeout`         | Overrides the timeout, in seconds.                           |
| `max_retries`     | Overrides the retries.                                       |
| `workspace`       | Partner keys only: acts in this tenant workspace.            |
| `headers`         | Adds headers to the request.                                 |
| `idempotency_key` | On methods that create, send or record something. See below. |

`timeout` limits each attempt, from sending the request to reading the whole response,
error responses included: an attempt that passes it raises `KiroraTimeoutError`, even if
the response then arrives in full, and is retried if the call is safe to repeat. An
error response whose body is cut off at the deadline raises its error class all the
same, from its status and headers, with its request ID, `retry_after` and rate limit;
the code and message its body held are lost, so `code` is the one for its status, such
as `CONFLICT` for a 409. The `_async` methods cancel the
attempt the moment it passes. The sync methods can't interrupt a network wait already
under way, so they check the deadline as the headers and each part of the body arrive;
httpx limits each single wait to `timeout`, so a stalled sync attempt can run longer
before it fails, but never returns a result after its deadline. The body of
`request_raw()`, which you read yourself, isn't covered.

A call that retries can take longer than `timeout` in total. To limit the total, run the
call under a deadline, such as `anyio.fail_after()` around an `_async` method.

A `Kirora` client takes the same settings as arguments, plus `workspace` and `headers`
for every request; see [partner workspaces](#partner-workspaces). Close a client you
create with `close()` or a `with` block. An `httpx` client you pass is yours to close.

## Retries and idempotency

### Retry behavior

A failed attempt is retried, up to `max_retries` times, when it's worth trying again
and repeating it is safe:

- A 429, or a connection that was never made, is always retried: the API did nothing.
- A network failure, a timeout or a 5xx is retried when the operation is safe to repeat.
  The SDK knows which are, from the API spec: reads, updates that converge, and anything
  sent with an idempotency key.
- `IDEMPOTENCY_KEY_IN_USE` is retried, since the earlier request with the key will
  answer.
- Other 4xx responses are not retried.

Waits grow exponentially from 1 second, with jitter, up to `max_retry_delay`. When the
API asks for a wait with `Retry-After`, the SDK waits at least that long, and raises
rather than wait longer than `max_retry_delay`. A retried delete that then gets a 404
returns normally, since an earlier attempt may have done it.

### Idempotency keys

For operations that take one, the SDK sends a new idempotency key with each call and
reuses it for its own retries. Your own retries of a call, such as from a job queue, get
new keys and can repeat it. Pass the same `idempotency_key` each time instead:

```python
kirora.Contacts.identify({"email": "ada@example.com"}, {"idempotency_key": "signup-ada"})
```

Reuse a key only for the same operation and body: the API refuses a key reused with a
different body, with `IDEMPOTENCY_KEY_REUSED`. Keys are per call. Passing one to an
endpoint that doesn't take keys, such as a read, raises a `ValueError` before anything
is sent; an endpoint newer than the SDK is trusted to take one.

## Async

Every method has an `_async` form, with the same arguments, to await. They work under
asyncio and trio.

```python
async def main() -> None:
    contact = await kirora.Contacts.get_async("ada@example.com", id_type="email")
    print(contact["id"])
    async for message in kirora.Messages.list_async({"recipient": "ada@example.com"}):
        print(message["id"], message["status"])
```

A `list_async()` fetches nothing until you await it, for the first page, or iterate it
with `async for`, for every item. Awaiting and then iterating reuses the first page, and
tasks awaiting it at once share one request.

Without a client of your own, the SDK opens one `httpx.AsyncClient` for each event loop
it's used in, under asyncio or Trio, and every later call in that loop reuses its
connections. A `Kirora` client closes the one it opened for the running loop with
`await client.aclose()`, or at the end of `async with`:

```python
async with kirora.Kirora(api_key) as client:
    await client.contacts.get_async("ada@example.com", id_type="email")
```

To use your own, such as one with a proxy, set `kirora.default_async_http_client`, or
pass `async_http_client` to a `Kirora` client, and close it yourself when your
application shuts down.

## Logging

The SDK logs to the `kirora` logger, with the standard `logging` module: each attempt
and each response at `DEBUG`, and each retry, with the error that caused it and the
wait, at `INFO`. It never logs your API key, headers or bodies; it does log each
request's method and path, which can hold an email address used as a contact id.

```python
import logging

logging.getLogger("kirora").setLevel(logging.DEBUG)
```

Or set `KIRORA_LOG` to `debug` or `info` before importing the SDK, and it logs to
standard error itself.

## Webhooks

Kirora signs each webhook with your endpoint's secret. Verify the **raw** request body,
before parsing it: parsing and re-encoding JSON changes the bytes the signature covers.

```python
verified = kirora.Webhooks.verify(secret, raw_body, headers)
if verified is not None:
    print(verified.headers.event, verified.headers.event_id, verified.payload["eventType"])
```

`Webhooks.verify()` returns `None` for a webhook that fails verification; reject that
request before processing it. `Webhooks.assert_valid()` raises
`KiroraWebhookVerificationError` instead, whose `reason` says why. Both check the
signature, refuse a timestamp more than 5 minutes from now (`tolerance_seconds` changes
it), and check the event headers match the signed body. Neither needs an API key.

Webhooks can arrive more than once. Deduplicate on the verified `event_id`, and record an
event as handled only once its work has succeeded, so a failed delivery is handled again
on retry.

### Frameworks

Flask:

```python
@app.post("/webhooks/kirora")
def kirora_webhook():
    verified = kirora.Webhooks.verify(SECRET, request.get_data(), request.headers)
    if verified is None:
        abort(400)
    handle(verified)
    return "", 204
```

FastAPI and Starlette:

```python
@app.post("/webhooks/kirora", status_code=204)
async def kirora_webhook(request: Request) -> None:
    verified = kirora.Webhooks.verify(SECRET, await request.body(), request.headers)
    if verified is None:
        raise HTTPException(400)
    await handle(verified)
```

Django:

```python
@csrf_exempt
@require_POST
def kirora_webhook(request):
    verified = kirora.Webhooks.verify(SECRET, request.body, request.headers)
    if verified is None:
        return HttpResponseBadRequest()
    handle(verified)
    return HttpResponse(status=204)
```

For a server with only the standard library, see
[`examples/webhook_receiver.py`](../examples/webhook_receiver.py).

### Verification diagnostics

| `reason`                      | Usually means                                                       |
| ----------------------------- | ------------------------------------------------------------------- |
| `signature_mismatch`          | The wrong secret, or a body that was parsed before it was verified. |
| `timestamp_outside_tolerance` | A replay, or a server clock out of sync.                            |
| `invalid_timestamp`           | The timestamp header is missing or isn't whole seconds.             |
| `invalid_headers`             | A header is missing, or the event headers don't match the body.     |

`Webhooks.verify_signature()` and `Webhooks.assert_signature()` check just the
signature and timestamp; `Webhooks.read_headers()` reads the headers. The signature
doesn't cover the event headers, so trust them only through `Webhooks.verify()`.

## Batch requests

`Contacts.identify_batch()`, `Events.track_batch()` and `Transactional.send_batch()`
take up to 100 entries. One refused entry doesn't stop the rest: check each entry of
`results`, in the order sent, for an `error`, even when the call succeeds.

```python
result = kirora.Events.track_batch(
    {
        "events": [
            {"idempotencyKey": "order-123-completed", "event": {"externalId": "user-1", "name": "Order Completed"}},
            {"idempotencyKey": "order-124-completed", "event": {"externalId": "user-2", "name": "Order Completed"}},
        ]
    }
)
for entry in result["results"]:
    if "error" in entry:
        print("Refused:", entry["idempotencyKey"], entry["error"]["code"])
```

Event and transactional batches take a key per entry, not per call. The SDK gives each
entry without one a key of its own for its retries; set them yourself, as above, so your
own retries replay entries rather than repeat them.

## Response details

`kirora.last_response()` gives the HTTP response a result came from:

```python
contact = kirora.Contacts.identify({"email": "ada@example.com"}, {"idempotency_key": "signup-ada"})
info = kirora.last_response(contact)
if info is not None:
    print(info.status, info.request_id, info.idempotency_replay, info.rate_limit)
```

`idempotency_replay` is true when the API answered with its stored response to an earlier
request with the same key. `rate_limit` has `limit`, `remaining` and `reset_seconds`. A
page has the same as `page.last_response`. A copy of a result, such as `dict(contact)`,
doesn't keep it.

## User tokens

Kirora's web and mobile SDKs sign users in with a token your server creates. Sign it
with the SDK token secret from Developer → SDK in the dashboard, and keep the secret on
your server:

```python
token = kirora.UserTokens.create(os.environ["KIRORA_SDK_TOKEN_SECRET"], "user-123")
```

`user_id` must come from your authenticated server session, never an ID supplied by the
browser. Creating a token needs no API key. Return tokens from an authenticated route
with `Cache-Control: no-store`. Tokens last an hour unless `expires_in_seconds` says
otherwise, up to 86,400 (24 hours).

## Partner workspaces

A partner key manages its tenants' workspaces. Create a `Kirora` client for it, create a
workspace for each tenant, then act in one with `for_workspace()`, which shares the
client's connections:

```python
partner = kirora.Kirora(os.environ["KIRORA_PARTNER_KEY"])
partner.workspaces.create({"name": "Acme Bakery", "externalId": "acme", "country": "GB"})
acme = partner.for_workspace("acme")
acme.contacts.identify({"email": "owner@acme.example"})
session = acme.embed_sessions.create({"components": ["segment_builder"]})
```

A client's attributes are the resource classes, bound to it, so `acme.contacts` takes
what `kirora.Contacts` does. Give an embed session's token to the browser to embed
Kirora's builders. `kirora.for_workspace(external_id)` does the same with the module
settings, and each method also takes `{"workspace": ...}` in its options for a single
call.

## Other endpoints

A client reaches the rest of the API with the same authentication, retries and errors:

```python
client = kirora.Kirora()
tags = client.request_data("GET", "/v1/tags")  # The body's `data`.
for template in client.request_list("/v1/templates", query={"limit": 50}):
    print(template["id"])
client.request("POST", "/v1/tags", body={"name": "vip"}, idempotency_key="create-tag-vip")
```

`request()` returns the whole JSON body, or None for a 204. Each method retries as the
spec says the endpoint allows; for an endpoint newer than the SDK, pass
`repeatable=True` if it's safe to repeat. Each has an `_async` form. Stream a body that
isn't JSON, such as an export, with `request_raw()`:

```python
with client.request_raw("GET", "/v1/messages/exports/EXPORT_ID/download") as response:
    with open("messages.csv", "wb") as file:
        for chunk in response.iter_bytes():
            file.write(chunk)
```

## Testing your code

Point `kirora.default_http_client` at an `httpx.MockTransport` to answer requests in
your tests without the network:

```python
def handler(request: httpx.Request) -> httpx.Response:
    assert request.url.path == "/v1/contacts/identify"
    return httpx.Response(200, json={"data": {"id": "contact-1"}})

kirora.api_key = "sk_test"
kirora.default_http_client = httpx.Client(transport=httpx.MockTransport(handler))
assert kirora.Contacts.identify({"email": "ada@example.com"})["id"] == "contact-1"
```

Set `kirora.default_async_http_client` the same way for the `_async` methods, and use
`kirora.max_retries = 0` in tests that return errors, so they fail without waiting.
