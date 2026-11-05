import os

import kirora

if not os.environ.get("KIRORA_API_KEY"):
    raise OSError("KIRORA_API_KEY is missing")

params: kirora.Events.TrackParams = {
    "externalId": "example-user-123",
    "name": "Order Completed",
    "properties": {"orderId": "order-123", "total": 49.99, "currency": "GBP"},
}
# Derive the key from your own id for the event, so your retries can't record it twice.
event = kirora.Events.track(params, {"idempotency_key": "order-123-completed"})
print("Tracked:", event["id"])

batch: kirora.Events.TrackBatchParams = {
    "events": [
        {
            "idempotencyKey": "order-124-completed",
            "event": {"externalId": "user-1", "name": "Order Completed"},
        },
        {
            "idempotencyKey": "order-125-completed",
            "event": {"externalId": "user-2", "name": "Order Completed"},
        },
    ]
}
for entry in kirora.Events.track_batch(batch)["results"]:
    if "error" in entry:
        print("Refused:", entry["idempotencyKey"], entry["error"]["code"])
