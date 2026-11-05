import datetime as dt
import os

import kirora

if not os.environ.get("KIRORA_API_KEY"):
    raise OSError("KIRORA_API_KEY is missing")

rules: kirora.SegmentRulesInput = {
    "all": [{"type": "attribute", "field": "plan", "operator": "equals", "value": "pro"}]
}

# Check what the rules match before saving them.
preview = kirora.Segments.preview({"rules": rules})
print(preview["count"], "contacts match;", preview["reach"]["email"], "reachable by email")

segment = kirora.Segments.create({"name": "Pro plan", "rules": rules})

# Who matches now, as a send would reach them.
for contact in kirora.Segments.list_contacts(segment["id"]):
    print("Member:", contact["id"])

joined = kirora.Segments.list_membership_changes(segment["id"], {"change": "joined", "day": dt.date.today()})
print(joined.meta["count"], "joined today")

history = kirora.Segments.size_history(segment["id"], {"from": dt.date.today() - dt.timedelta(days=30)})
for point in history["points"]:
    print(point["day"], point["memberCount"])

usage = kirora.Segments.usage(segment["id"])
if not (usage["campaigns"] or usage["segments"]):
    kirora.Segments.delete(segment["id"])
