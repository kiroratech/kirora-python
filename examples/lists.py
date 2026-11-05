import os

import kirora

if not os.environ.get("KIRORA_API_KEY"):
    raise OSError("KIRORA_API_KEY is missing")

vip = kirora.Lists.create({"name": "VIP"})
added = kirora.Lists.add_contacts(vip["id"], {"emails": ["ada@example.com"]})
print(added["addedCount"], "added;", added["notFound"], "not found")

# A list's members are the contacts listed with its id.
for contact in kirora.Contacts.list({"listId": vip["id"]}):
    print("Member:", contact["id"])
