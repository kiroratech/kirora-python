"""Sends requests through a proxy, with your own httpx client and settings."""

import os

import httpx

import kirora

kirora.api_key = os.environ["KIRORA_API_KEY"]
kirora.timeout = 10
kirora.max_retries = 2
kirora.app_info = {"name": "shop", "version": "1.2.0"}
kirora.default_http_client = httpx.Client(proxy="http://proxy.internal:3128")

contact = kirora.Contacts.get("ada@example.com", {"timeout": 5, "max_retries": 0}, id_type="email")
info = kirora.last_response(contact)
if info is not None:
    print(info.request_id, info.rate_limit)
