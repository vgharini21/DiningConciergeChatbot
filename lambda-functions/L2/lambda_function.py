import os, json, random, boto3, requests

from requests.auth import HTTPBasicAuth

sqs = boto3.client("sqs")
ses = boto3.client("ses")
ddb = boto3.resource("dynamodb").Table("yelp-restaurants")

QURL = os.environ["REQUESTS_QUEUE_URL"]          
OS_URL = os.environ["OS_URL"].rstrip("/")        
OS_USER = os.environ.get("OS_USER")              
OS_PASSWORD = os.environ.get("OS_PASSWORD")
SES_SENDER = os.environ["SES_SENDER"]                

AUTH = HTTPBasicAuth(OS_USER, OS_PASSWORD) if OS_USER and OS_PASSWORD else None


def pick_random_by_cuisine(cuisine: str, k: int = 3):

    r = requests.get(
        f"{OS_URL}/restaurants/_search",
        json={"size": 100, "query": {"term": {"cuisine": cuisine}}},
        auth=AUTH,
        timeout=15,
    )
    r.raise_for_status()
    hits = [h["_source"].get("restaurant_id") for h in r.json().get("hits", {}).get("hits", [])]
    hits = [x for x in hits if x]
    if not hits:
        return []
    return random.sample(hits, min(k, len(hits)))


def fetch_details(ids):

    out = []
    for rid in ids:
        item = ddb.get_item(Key={"id": rid}).get("Item")
        if item:
            out.append(item)
    return out


def make_email_text(payload, items):

    cuisine = payload["cuisine"]
    party = payload["party_size"]
    when = str(payload["dining_time"])
    loc = payload.get("location")

    header = f"Hello! Here are my {cuisine} restaurant suggestions for {party} people"
    if loc:
        header += f" in {loc}"
    header += f", for {when}:\n"

    lines = []
    for i, it in enumerate(items, 1):
        name = it.get("name", "Unknown")
        addr = it.get("address", "(address n/a)")
        lines.append(f"{i}. {name}, located at {addr}")

    return header + "\n".join(lines) + "\nEnjoy your meal!"


def handle_message(m):
    payload = json.loads(m["Body"])

    def get_required(key, fallback=None):
        if key in payload:
            return payload[key]
        if fallback and fallback in payload:
            return payload[fallback]
        raise ValueError(f"Missing required field '{key}' in payload")

    cuisine = get_required("cuisine", "Cuisine")
    email = get_required("email", "Email")
    when = get_required("dining_time", "DiningTime")
    party = get_required("party_size", "PartySize")
    location = payload.get("location") or payload.get("Location")

    ids = pick_random_by_cuisine(cuisine, k=3)

    # Prepare email body
    if not ids:
        body_text = f"Sorry — no {cuisine} restaurants found right now."
    else:
        details = fetch_details(ids)
        body_text = make_email_text(
            {"cuisine": cuisine, "party_size": party, "dining_time": when, "location": location}, details
        )

    # Attempt to send email, let SQS retry if it fails
    try:
        ses.send_email(
            Source=SES_SENDER,
            Destination={"ToAddresses": [email]},
            Message={
                "Subject": {"Data": "Your Dining Suggestions"},
                "Body": {"Text": {"Data": body_text}},
            },
        )
        print(f" Email sent successfully to {email}")

    except Exception as e:
        # Log to CloudWatch
        print(f" Failed to send email to {email}. Error: {e}")
        # Raise error so Lambda doesn't delete message → triggers SQS retry
        raise e



def lambda_handler(event, _context):
    resp = sqs.receive_message(
        QueueUrl=QURL,
        MaxNumberOfMessages=5,
        WaitTimeSeconds=0,
        VisibilityTimeout=60,
        MessageAttributeNames=["All"],
        AttributeNames=["All"],
    )

    msgs = resp.get("Messages", [])
    if not msgs:
        return {"status": "empty"}

    processed = 0
    for m in msgs:
        try:
            handle_message(m)
            # Delete only if successful
            sqs.delete_message(QueueUrl=QURL, ReceiptHandle=m["ReceiptHandle"])
            processed += 1
        except Exception as e:
            # Do NOT delete → message stays in queue for retry
            print(f"Error handling message: {e}")

    return {"status": "processed", "count": processed}
