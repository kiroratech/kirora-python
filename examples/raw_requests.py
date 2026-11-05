"""Endpoints without a resource method, with the same authentication, retries and errors."""

import os

import kirora

client = kirora.Kirora(os.environ["KIRORA_API_KEY"])

tags = client.request_data("GET", "/v1/tags")
print(tags)
for template in client.request_list("/v1/templates", query={"limit": 50}):
    print(template["id"])
client.request("POST", "/v1/tags", body={"name": "vip"}, idempotency_key="create-tag-vip")

with client.request_raw("GET", "/v1/messages/exports/EXPORT_ID/download") as response:
    with open("messages.csv", "wb") as file:
        for chunk in response.iter_bytes():
            file.write(chunk)
