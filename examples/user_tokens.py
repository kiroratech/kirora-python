"""Signs a user in to Kirora's web and mobile SDKs, on your server."""

import os

import kirora

token = kirora.UserTokens.create(os.environ["KIRORA_SDK_TOKEN_SECRET"], "user-123")
short_lived = kirora.UserTokens.create(
    os.environ["KIRORA_SDK_TOKEN_SECRET"], "user-123", expires_in_seconds=600
)
print(token, short_lived)
