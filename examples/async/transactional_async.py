import asyncio
import os

import httpx

import kirora

if not os.environ.get("KIRORA_API_KEY"):
    raise OSError("KIRORA_API_KEY is missing")


async def main() -> None:
    # One client for every call, so they share connections. Without it, each call opens
    # its own.
    async with httpx.AsyncClient() as http:
        kirora.default_async_http_client = http
        sent = await kirora.Transactional.send_async(
            {"to": {"email": "customer@example.com"}, "email": {"template": "order-receipt"}},
            {"idempotency_key": "receipt-order-123"},
        )
        print("Messages:", [message["id"] for message in sent["messages"]])


asyncio.run(main())
