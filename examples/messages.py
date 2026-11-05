import os

import kirora

if not os.environ.get("KIRORA_API_KEY"):
    raise OSError("KIRORA_API_KEY is missing")

for page in kirora.Messages.list({"status": "bounced", "limit": 100}).iter_pages():
    for message in page.data:
        print(message["id"], message["recipientEmail"])
