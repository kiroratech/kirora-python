import os

import kirora

if not os.environ.get("KIRORA_API_KEY"):
    raise OSError("KIRORA_API_KEY is missing")

try:
    kirora.Contacts.get("no-such-user", id_type="externalId")
except kirora.NotFoundError:
    print("No contact with that id")
except kirora.BadRequestError as error:
    for field_error in error.errors:
        print(field_error["field"], field_error["message"])
except kirora.KiroraError as error:
    print(f"Kirora error: code={error.code} status={error.status} request_id={error.request_id}")
    raise
