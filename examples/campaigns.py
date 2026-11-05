import os

import kirora

if not os.environ.get("KIRORA_API_KEY"):
    raise OSError("KIRORA_API_KEY is missing")

campaign = kirora.Campaigns.create({"name": "November newsletter", "segmentId": "SEGMENT_ID"})
eligibility = kirora.Campaigns.eligibility(campaign["id"])
if eligibility["canSend"]:
    kirora.Campaigns.schedule(campaign["id"], {"type": "fixed", "sendAt": "2026-11-20T09:00:00Z"})
else:
    for blocker in eligibility["blockers"]:
        print("Blocked:", blocker)

for draft in kirora.Campaigns.list({"status": "draft"}):
    print(draft["id"], draft["name"])
