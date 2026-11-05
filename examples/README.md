# Examples

Each example runs on its own: set `KIRORA_API_KEY` first, and replace the sample ids
with your own.

| Example | Shows |
| --- | --- |
| [`contacts.py`](contacts.py) | Identifying, finding, updating, listing and exporting contacts. |
| [`events.py`](events.py) | Tracking events, singly and in batches. |
| [`transactional.py`](transactional.py) | Sending a transactional email with a template. |
| [`campaigns.py`](campaigns.py) | Creating, checking and scheduling a campaign. |
| [`lists.py`](lists.py) | Creating a list and adding contacts to it. |
| [`segments.py`](segments.py) | Previewing, creating and inspecting a segment. |
| [`messages.py`](messages.py) | Listing sent messages page by page. |
| [`suppressions.py`](suppressions.py) | Blocking and unblocking email addresses. |
| [`partner_workspaces.py`](partner_workspaces.py) | Acting in a tenant's workspace with a partner key. |
| [`user_tokens.py`](user_tokens.py) | Signing users in to the web and mobile SDKs. |
| [`webhook_receiver.py`](webhook_receiver.py) | Verifying and deduplicating webhooks with the standard library. |
| [`with_exception.py`](with_exception.py) | Handling errors by class and code. |
| [`with_custom_http_client.py`](with_custom_http_client.py) | Module settings and your own `httpx.Client`. |
| [`raw_requests.py`](raw_requests.py) | Endpoints without a resource method. |
| [`async/`](async) | The `_async` methods. |

CI type-checks every example with `mypy --strict`.
