import asyncio
import os

import kirora

if not os.environ.get("KIRORA_API_KEY"):
    raise OSError("KIRORA_API_KEY is missing")


async def main() -> None:
    event = await kirora.Events.track_async(
        {"externalId": "example-user-123", "name": "Order Completed"},
        {"idempotency_key": "order-123-completed"},
    )
    print("Tracked:", event["id"])


asyncio.run(main())
