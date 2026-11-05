import asyncio
import os

import kirora

if not os.environ.get("KIRORA_API_KEY"):
    raise OSError("KIRORA_API_KEY is missing")


async def main() -> None:
    contact = await kirora.Contacts.identify_async(
        {"externalId": "example-user-123", "email": "ada@example.com"}
    )
    print("Identified:", contact["id"])
    first = await kirora.Contacts.list_async({"query": "ada"})
    print("First page:", first.data)
    async for each in kirora.Contacts.list_async({"query": "ada"}):
        print(each["id"])


asyncio.run(main())
