import os

import kirora

if not os.environ.get("KIRORA_API_KEY"):
    raise OSError("KIRORA_API_KEY is missing")

params: kirora.Transactional.SendParams = {
    "to": {"email": "customer@example.com"},
    "data": {"orderId": "order-123"},
    "email": {"template": "order-receipt"},
}
sent = kirora.Transactional.send(params, {"idempotency_key": "receipt-order-123"})
print("Messages:", [message["id"] for message in sent["messages"]])
for skipped in sent["skippedChannels"]:
    print("Not sent by", skipped["channel"], "because", skipped["code"])
