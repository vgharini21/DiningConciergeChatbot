import os, json, boto3, re

sqs = boto3.client('sqs')
QUEUE_URL = os.environ['REQUESTS_QUEUE_URL']

def _msg(text): return {"contentType":"PlainText","content":text}
def _close(ss,intent,text):
    ss = ss or {}; ss["dialogAction"]={"type":"Close"}
    intent = intent or {}; intent["state"]="Fulfilled"; ss["intent"]=intent
    return {"sessionState": ss, "messages":[_msg(text)]}
def _elicit(ss,slot,text):
    ss = ss or {}; ss["dialogAction"]={"type":"ElicitSlot","slotToElicit":slot}
    return {"sessionState": ss, "messages":[_msg(text)]}
def _sv(slots,k):
    v=(slots or {}).get(k) or {}; v=v.get("value") or {}; return v.get("interpretedValue")

def lambda_handler(event, context):
    print(json.dumps(event))
    ss = event.get("sessionState", {}); intent = ss.get("intent", {}); name = intent.get("name"); slots = intent.get("slots") or {}

    if name in ("GreetingIntent","ThankYouIntent"):
        return _close(ss,intent,"Hi there, how can I help?" if name=="GreetingIntent" else "You're welcome!")

    if name == "DiningSuggestionsIntent":
        location=_sv(slots,"Location"); cuisine=_sv(slots,"Cuisine")
        dtime=_sv(slots,"DiningTime"); party=_sv(slots,"PartySize"); email=_sv(slots,"Email")

        if email and not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
            return _elicit(ss,"Email","That email looks off—what's the correct email?")
        for key,val in [("Location",location),("Cuisine",cuisine),("DiningTime",dtime),("PartySize",party),("Email",email)]:
            if not val: return _elicit(ss,key,f"What is the {key.lower()}?")

        sqs.send_message(QueueUrl=QUEUE_URL, MessageBody=json.dumps({
            "location": location, "cuisine": cuisine, "dining_time": dtime,
            "party_size": int(party), "email": email
        }))
        return _close(ss,intent,"Got it! I’ll email you suggestions shortly.")

    return _close(ss,intent,"Sorry, I didn’t quite understand that.")
