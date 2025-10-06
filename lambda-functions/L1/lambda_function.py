import os, json, boto3, re

sqs = boto3.client('sqs')
QUEUE_URL = os.environ['REQUESTS_QUEUE_URL']

def _msg(text):
    return {"contentType":"PlainText","content":text}

def _close(ss, intent, text):
    ss = ss or {}
    intent = intent or {}
    intent["state"] = "Fulfilled"
    ss["dialogAction"] = {"type":"Close"}
    ss["intent"] = intent
    return {"sessionState": ss, "messages":[_msg(text)]}

def _elicit(ss, intent, slots, slot_key, text):
    # elicit exactly the slot name that exists in the intent (case-sensitive)
    ss = ss or {}
    intent = intent or {}
    intent["state"] = "InProgress"
    intent["slots"] = slots
    ss["dialogAction"] = {"type":"ElicitSlot","slotToElicit": slot_key}
    ss["intent"] = intent
    return {"sessionState": ss, "messages":[_msg(text)]}

def _slot_value(slots, k):
    v = (slots or {}).get(k) or {}
    v = v.get("value") or {}
    return v.get("interpretedValue")

def _find_slot_key(slots, candidates):
    """Return the actual slot key present in 'slots' matching any name in candidates (case-insensitive)."""
    if not slots: return None
    keys = list(slots.keys())
    lower = {k.lower(): k for k in keys}
    for name in candidates:
        if name.lower() in lower:
            return lower[name.lower()]
    return None

def lambda_handler(event, context):
    print("EVENT:", json.dumps(event))  # debug
    ss = event.get("sessionState", {})
    intent = ss.get("intent", {}) or {}
    name = intent.get("name")
    slots = intent.get("slots") or {}
    print("SLOT KEYS:", list(slots.keys()))

    # Map your current names to canonical concepts
    key_location = _find_slot_key(slots, ["Location","City"])
    key_cuisine  = _find_slot_key(slots, ["Cuisine"])  # MUST exist in the intent
    key_time     = _find_slot_key(slots, ["DiningTime","Time"])
    key_party    = _find_slot_key(slots, ["PartySize","People","Number"])
    key_email    = _find_slot_key(slots, ["Email","email","EmailId","emailid"])

    if name in ("GreetingIntent","ThankYouIntent","ThankyouIntent"):
        text = "Hi there, how can I help?" if name=="GreetingIntent" else "You're welcome!"
        return _close(ss, intent, text)

    if name == "DiningSuggestionsIntent":
        # sanity: require a Cuisine slot in the intent
        if key_cuisine is None:
            return _close(ss, intent, "Config error: please add a 'Cuisine' slot to this intent (custom list).")

        location = _slot_value(slots, key_location) if key_location else None
        cuisine  = _slot_value(slots, key_cuisine)
        dtime    = _slot_value(slots, key_time) if key_time else None
        party    = _slot_value(slots, key_party) if key_party else None
        email    = _slot_value(slots, key_email) if key_email else None

        # Validate email if present
        # if email and not re.match(r"^[^@\s]+@[^@\\s]+\\.[^@\\s]+$", email):
        #     ek = key_email or "Email"
        #     return _elicit(ss, intent, slots, ek, "That email looks off—what's the correct email?")

        # Elicit any missing required concept, using the actual slot key names found
        required = [
            (key_location or "Location", location, "city"),
            (key_cuisine, cuisine, "cuisine"),
            (key_time or "DiningTime", dtime, "time"),
            (key_party or "PartySize", party, "party size"),
            (key_email or "Email", email, "email"),
        ]
        for actual_key, val, noun in required:
            if not val:
                # If the slot isn't actually in the intent (bad config), fail early with a helpful message
                if actual_key not in slots:
                    return _close(ss, intent, f"Config error: slot '{actual_key}' is missing from the intent.")
                return _elicit(ss, intent, slots, actual_key, f"What is the {noun}?")

        # All set — enqueue
        sqs.send_message(QueueUrl=QUEUE_URL, MessageBody=json.dumps({
            "location": location,
            "cuisine": cuisine,
            "dining_time": dtime,
            "party_size": int(party),
            "email": email
        }))
        return _close(ss, intent, "Got it! I’ll email you suggestions shortly.")

    return _close(ss, intent, "Sorry, I didn’t quite understand that.")
