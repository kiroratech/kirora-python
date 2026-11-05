"""With a partner key: create a tenant's workspace, then act in it."""

import os

import kirora

partner = kirora.Kirora(os.environ["KIRORA_PARTNER_KEY"])

partner.workspaces.create({"name": "Acme Bakery", "externalId": "acme", "country": "GB"})
acme = partner.for_workspace("acme")
acme.contacts.identify({"email": "owner@acme.example"})

# A session for embedding Kirora's segment builder in your app, for this tenant.
session = acme.embed_sessions.create({"components": ["segment_builder"]})
print(session)
