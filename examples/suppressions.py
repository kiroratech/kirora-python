import os

import kirora

if not os.environ.get("KIRORA_API_KEY"):
    raise OSError("KIRORA_API_KEY is missing")

kirora.Suppressions.add({"emails": ["bounced@example.com"]})
for suppression in kirora.Suppressions.list({"email": "bounced@example.com"}):
    print(suppression["address"], suppression["reason"])
removed = kirora.Suppressions.delete({"emails": ["bounced@example.com"]})
print(removed["deletedCount"], "removed;", removed["notRemovable"], "can't be")
