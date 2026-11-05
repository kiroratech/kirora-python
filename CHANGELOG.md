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
