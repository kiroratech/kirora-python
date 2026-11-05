# Kirora Python SDK

Use the Kirora API from Python to manage contacts, track events, build segments, and
send campaigns and transactional messages.

[Python guide](https://kirora.io/docs/sdks/python) ·
[API reference](https://kirora.io/docs/api/reference) ·
[Usage guide](docs/usage.md) · [Examples](examples) · [Changelog](CHANGELOG.md)

- Request and response types generated from Kirora's OpenAPI specification.
- Sync methods, and an `_async` form of each, for asyncio and trio.
- Automatic pagination, configurable retries, and idempotency keys for supported operations.
- Webhook verification, user token signing, and partner workspace support.
- Depends only on `httpx`, `anyio` and `typing-extensions`.

## Contents

- [Installation](#installation)
- [Quickstart](#quickstart)
- [Async](#async)
- [Usage](#usage)
- [Pagination](#pagination)
- [Errors](#errors)
- [Settings](#settings) and [clients](#clients)
- [Retries and idempotency](#retries-and-idempotency)
- [More guides](#more-guides)
- [Troubleshooting](#troubleshooting)
- [Compatibility](#compatibility) and [help](#help-and-contributing)

## Installation

Requires **Python 3.9 or later**.

```sh
python -m pip install kirora
# or
uv add kirora
# or
poetry add kirora
```

Create an API key under **Developer → Server keys** in the Kirora dashboard, with the
scopes your integration needs. Set it in your server's environment:

```sh
export KIRORA_API_KEY="your_api_key"
```

Or set it in code, as `kirora.api_key = "your_api_key"`. Keep the key on your server
and out of source control. A `.env` file is not loaded automatically; export its values
or load it through your application. For browser and mobile apps, use
[server-issued user tokens](docs/usage.md#user-tokens).

## Quickstart

Save this as `quickstart.py`. It creates or updates a contact in your workspace.
Replace the sample external ID and email with your own test values.

```python
import kirora  # Reads KIRORA_API_KEY.

params: kirora.Contacts.IdentifyParams = {
    "externalId": "example-user-123",
    "email": "ada@example.com",
}
contact = kirora.Contacts.identify(params)
print("Contact ID:", contact["id"])
```

Run it:

```sh
python quickstart.py
```

A successful request prints `Contact ID: <contact ID>`. To check credentials without
creating data, call `print(kirora.me())` instead.

Each resource is a class whose methods you call directly, as
`kirora.Contacts.identify()`. Its request types sit on the class, as
`kirora.Contacts.IdentifyParams`, and its models are exported from `kirora`, as
`kirora.ContactDetail`. Requests and results are plain dicts, keyed by the API's own
field names, so `externalId` and `firstName` read just as they do in the
[API reference](https://kirora.io/docs/api/reference). See the
[runnable examples](examples/README.md) for each resource.

## Async

Every method has an `_async` form. No extra package is needed:

```python
import asyncio

import kirora


async def main() -> None:
    contact = await kirora.Contacts.get_async("ada@example.com", id_type="email")
    print(contact["id"])
    async for message in kirora.Messages.list_async({"recipient": "ada@example.com"}):
        print(message["id"], message["status"])


asyncio.run(main())
```

Await a `list_async()` for its first page, or iterate it with `async for` for every
item. It makes no request until you do either. In a Trio application, use
`trio.run(main)`. Use the `_async` methods in async request handlers, so SDK calls
don't block the event loop.

Each async call opens its own connection, which works in any event loop; the pages of
one `async for` over a list share one. To share connections between calls, set `kirora.default_async_http_client` to an
`httpx.AsyncClient`; see [settings](#settings).

## Usage

### Contacts

`identify()` creates or updates a contact, matching by external ID, then email, then
phone. Retrieve and update a contact by email:

```python
contact = kirora.Contacts.get("ada@example.com", id_type="email")
kirora.Contacts.update(contact["id"], {"firstName": "Ada"})
```

Methods use Kirora IDs by default. Pass `id_type="externalId"` or `id_type="email"` to
use another identifier. Leave a field out of an update to keep its current value; set
a **nullable** field to `None` to clear it. `None` is sent as JSON `null`; it does not
mean "leave unchanged."

### Events

Track an event for an existing contact:

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

A method's last argument is its options for that call, as here. Derive the idempotency
key from the operation in your application, and reuse it when retrying that same
operation with the same body.

### Transactional messages

Complete your workspace's email sending setup and configure an email template first.
Replace `order-receipt` with your template's alias or ID and use a recipient you control.

```python
sent = kirora.Transactional.send(
    {
        "to": {"email": "customer@example.com"},
        "data": {"orderId": "order-123"},
        "email": {"template": "order-receipt"},
    },
    {"idempotency_key": "receipt-order-123"},
)
print(sent["messages"])
```

A send can succeed with a channel left unsent, such as push for a contact without a
device. Inspect both the created messages and skipped channels:

```python
for skipped in sent["skippedChannels"]:
    print(skipped["channel"], skipped["code"])
```

`Contacts.identify_batch()`, `Events.track_batch()` and `Transactional.send_batch()`
accept up to 100 entries. Check each entry in `results` for an `error` even when the
call succeeds. Set each entry's `idempotencyKey` when retrying batches from your
application. See [batch requests](docs/usage.md#batch-requests).

### Segments

Preview what a segment's rules match, then save it:

```python
rules: kirora.SegmentRulesInput = {
    "all": [{"type": "attribute", "field": "plan", "operator": "equals", "value": "pro"}]
}
preview = kirora.Segments.preview({"rules": rules})
print(preview["count"], "contacts match")
segment = kirora.Segments.create({"name": "Pro plan", "rules": rules})
```

See [segments](docs/usage.md#segments) for their contacts, size history and usage.

### Resources

| Resource               | Use it to                                                                                  |
| ---------------------- | ------------------------------------------------------------------------------------------ |
| `kirora.Contacts`      | Identify, update, merge, export, and delete contacts; manage preferences and push devices. |
| `kirora.Events`        | Track individual events or batches.                                                        |
| `kirora.Transactional` | Send messages individually or in batches; cancel scheduled messages.                       |
| `kirora.Campaigns`     | Create campaigns, check eligibility, send, and schedule.                                   |
| `kirora.Lists`         | Create lists and manage membership.                                                        |
| `kirora.Segments`      | Preview, create and update segments; list their contacts, size history and usage.          |
| `kirora.Messages`      | Inspect sent messages.                                                                     |
| `kirora.Suppressions`  | Manage suppressed email addresses.                                                         |
| `kirora.Workspaces`    | Manage tenant workspaces with a partner key.                                               |
| `kirora.EmbedSessions` | Create sessions for embedded Kirora builders.                                              |
| `kirora.Webhooks`      | Verify the webhooks Kirora sends you.                                                      |
| `kirora.UserTokens`    | Sign users in to Kirora's web and mobile SDKs.                                             |

See the [usage guide](docs/usage.md) and the
[API reference](https://kirora.io/docs/api/reference) for endpoint requirements.

## Pagination

Iterate a `list()` result to fetch matching items across pages automatically:

```python
for contact in kirora.Contacts.list({"query": "ada"}):
    print(contact["id"], contact["email"])
```

Use `break` to stop fetching more pages. `list()` fetches the first page when you call
it, so `page.data` holds that page alone:

```python
page = kirora.Contacts.list({"query": "ada", "limit": 50})
print(page.data, page.next_cursor)
```

A list's filters are its `params`, typed as `kirora.Contacts.ListParams` and the like.
See [pagination details](docs/usage.md#pagination) for cursors and page-by-page
iteration.

## Errors

API failures raise `KiroraError`, or its subclass for the status, such as
`NotFoundError` or `RateLimitError`. Connection failures, including timeouts, raise
`KiroraConnectionError`. Branch on the class or the API `code`, and include
`request_id` when reporting a failure:

```python
try:
    contact = kirora.Contacts.get("example-user-123", id_type="externalId")
except kirora.KiroraConnectionError:
    # Automatic retries have finished, or the operation could not be safely retried.
    raise
except kirora.NotFoundError:
    ...  # Handle the missing contact in your application.
except kirora.KiroraError as error:
    print(f"Kirora error: code={error.code} status={error.status} request_id={error.request_id}")
    raise
```

`KiroraError` includes the API code, HTTP status, message, request ID, field errors
(`errors`), `details`, and any `retry_after` and rate limit. Unusable success responses
raise `KiroraResponseError`. All of them subclass `KiroraException`, in
`kirora.exceptions`.

Invalid local arguments raise `ValueError` or `TypeError` before sending a request.

See [error handling](docs/usage.md#errors) and the
[API error codes](https://kirora.io/docs/api/reference/errors).

## Settings

The resource classes read these module settings on each call:

```python
import kirora

kirora.api_key = "your_api_key"  # Or KIRORA_API_KEY.
kirora.timeout = 10
kirora.max_retries = 2
```

| Setting                            | Default                                      | Purpose                                                                   |
| ---------------------------------- | -------------------------------------------- | ------------------------------------------------------------------------- |
| `kirora.api_key`                   | `KIRORA_API_KEY`                             | Your API key.                                                             |
| `kirora.timeout`                   | 30 seconds                                   | Seconds per attempt, including reading the response.                      |
| `kirora.max_retries`               | 3                                            | Allow 0–10 retries after the first attempt.                               |
| `kirora.max_retry_delay`           | 30 seconds                                   | Limit the wait between attempts; a longer `Retry-After` stops retries.    |
| `kirora.base_url`                  | `KIRORA_BASE_URL` or `https://api.kirora.io` | Set the API host, without `/v1`.                                          |
| `kirora.app_info`                  | None                                         | Add your app to the `User-Agent`: `{"name": "shop", "version": "1.2.0"}`. |
| `kirora.default_http_client`       | One the SDK opens                            | An `httpx.Client` for the sync methods, such as one with a proxy.         |
| `kirora.default_async_http_client` | One per call                                 | An `httpx.AsyncClient` the `_async` methods share.                        |

Each method also takes options for that call alone: `timeout`, `max_retries`,
`workspace` and `headers`, and `idempotency_key` where its endpoint takes one. For
example, override the timeout and disable retries for one request:

```python
contact = kirora.Contacts.get("ada@example.com", {"timeout": 5, "max_retries": 0}, id_type="email")
```

The timeout applies to **each attempt**, not to the entire call. Retries and backoff can
make a call take longer. The [usage guide](docs/usage.md#settings) explains overall
async deadlines and transport configuration.

### Clients

For a partner key acting in several tenant workspaces, or an app holding more than one
key, create a `Kirora` client with its own settings. It takes them as arguments, with
the same names and defaults, plus `workspace` and `headers`. Its attributes are the
same resource classes, bound to it:

```python
client = kirora.Kirora(api_key="partner_key", timeout=10)
acme = client.for_workspace("acme")
acme.contacts.identify({"email": "owner@acme.example"})
```

Create one client and reuse it; it's safe to share between threads. Close it at
shutdown with `client.close()`, or use it as a context manager.

## Retries and idempotency

The SDK allows up to **3 retries** by default, with exponential backoff and jitter:

- Rate limits (429) and failures that never established a connection can be retried.
- Other network failures and 5xx responses are retried only when repeating the
  operation is safe.
- `IDEMPOTENCY_KEY_IN_USE` (409) can be retried when the call has a key.
- Other 4xx responses are not retried.

For supported operations, the SDK generates an idempotency key per call and reuses it
for its own retries. Separate calls get separate keys. To deduplicate retries from your
application, pass a stable `idempotency_key` to each call for the same operation and
body, as in the event and transactional examples above.

See [retry behavior](docs/usage.md#retries-and-idempotency) for operation-specific rules.

## More guides

The [usage guide](docs/usage.md) covers:

- [Webhooks](docs/usage.md#webhooks): verify the raw request body with
  `kirora.Webhooks.verify()` before parsing it. Deduplicate on the verified `event_id`.
- [User tokens](docs/usage.md#user-tokens): sign tokens for the browser and mobile SDKs
  with `kirora.UserTokens.create()`.
- [Partner workspaces](docs/usage.md#partner-workspaces): use
  `kirora.for_workspace(external_id)` with a partner key to act in a tenant's workspace.
- [Response details](docs/usage.md#response-details): `kirora.last_response()` reads a
  result's request ID, rate limit and idempotency replay.
- [Other endpoints](docs/usage.md#other-endpoints): a client's `request()`,
  `request_data()`, `request_list()` and `request_raw()` reach the rest of the API.
- [Testing your code](docs/usage.md#testing-your-code) with `httpx.MockTransport`.

## Troubleshooting

| Problem                                   | Check                                                                                                                                  |
| ----------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| `api_key is required`                     | Set `KIRORA_API_KEY` in the process running your app, or `kirora.api_key`. A `.env` file alone is not loaded.                          |
| API returns `401`                         | Check that the key is valid, unexpired and has not been revoked.                                                                       |
| API returns `403`                         | Check the endpoint's required scopes and whether it accepts your key kind; partner calls may need a workspace.                         |
| The call takes longer than `timeout`      | The timeout applies per attempt: check `max_retries` and `max_retry_delay`. A sync attempt can also wait out one stalled network read. |
| A batch succeeds but some work is missing | Inspect every entry in `results` for an `error`.                                                                                       |
| A webhook fails verification              | Pass the unchanged raw body and the endpoint's webhook secret. See [verification diagnostics](docs/usage.md#verification-diagnostics). |

## Compatibility

The SDK follows [semantic versioning](https://semver.org). While it's 0.x, a minor
release can change the public API; the [changelog](CHANGELOG.md) says how. It supports
CPython 3.9 and later, and is tested on 3.9 to 3.14.

## Help and contributing

For integration help, email [support@kirora.io](mailto:support@kirora.io). Report bugs in the
[issue tracker](https://github.com/kiroratech/kirora-python/issues); see
[CONTRIBUTING.md](CONTRIBUTING.md) and, for security issues, [SECURITY.md](SECURITY.md).

## License

[MIT](LICENSE)
