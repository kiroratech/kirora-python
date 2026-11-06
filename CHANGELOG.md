# Changelog

## 0.1.0 — Unreleased

Initial release.

- Resource classes with class methods, as `kirora.Contacts.identify()`, configured by
  module settings such as `kirora.api_key`, after the layout of Resend's Python SDK. Each
  method has an `_async` form.
- Request types on each resource, as `kirora.Contacts.IdentifyParams`, and models, all
  generated from the Kirora API's OpenAPI spec.
- `Kirora` clients with their own settings, for partner keys and apps with several keys.
- Contacts, events, segments, transactional messages, campaigns, lists, messages,
  suppressions, workspaces and embed sessions.
- Automatic pagination, retries and idempotency keys.
- Errors by status, as `kirora.NotFoundError`, under `KiroraError`.
- `kirora.Webhooks` to verify webhooks, and `kirora.UserTokens` to sign SDK tokens.
- The `_async` methods reuse one `httpx.AsyncClient` for each event loop, rather than
  opening one per call. `Kirora.aclose()`, or `async with`, closes it.
- Logging to the `kirora` logger: each attempt and response at `DEBUG`, each retry at
  `INFO`. Set `KIRORA_LOG=debug` or `info` to log to standard error.
- Every SDK error can be pickled. `KiroraError.last_response` holds the HTTP response,
  and `KiroraConnectionError.request_sent` says whether the request may have reached
  the API.
- A 501 or 505 isn't retried.
- A plain `http` `base_url` other than this machine's warns that it sends the key
  unencrypted.
