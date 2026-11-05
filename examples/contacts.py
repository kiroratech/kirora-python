import os

import kirora

if not os.environ.get("KIRORA_API_KEY"):
    raise OSError("KIRORA_API_KEY is missing")

params: kirora.Contacts.IdentifyParams = {
    "externalId": "example-user-123",
    "email": "ada@example.com",
    "firstName": "Ada",
    "attributes": {"plan": "pro"},
    "consent": {"email": True, "statement": {"basis": "opted_in", "evidence": "Signup form"}},
}
contact = kirora.Contacts.identify(params)
print("Identified:", contact["id"])

found = kirora.Contacts.get("ada@example.com", id_type="email")
kirora.Contacts.update(found["id"], {"lastName": "Lovelace", "attributes": {"trial": None}})

for each in kirora.Contacts.list({"query": "ada"}):
    print(each["id"], each["email"])

for membership in kirora.Contacts.list_lists(found["id"]):
    print("In list:", membership["id"])

export = kirora.Contacts.export(found["id"])
print("Export has", len(export), "sections")
