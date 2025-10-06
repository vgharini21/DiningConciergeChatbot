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
    if not ids:
        ses.send_email(
            Source=SES_SENDER,
            Destination={"ToAddresses": [email]},
            Message={
                "Subject": {"Data": "Your Dining Suggestions"},
                "Body": {"Text": {"Data": f"Sorry — no {cuisine} restaurants found right now."}},
            },
        )
        return

    details = fetch_details(ids)
    body_text = make_email_text(
        {"cuisine": cuisine, "party_size": party, "dining_time": when, "location": location}, details
    )

    ses.send_email(
        Source=SES_SENDER,
        Destination={"ToAddresses": [email]},
        Message={"Subject": {"Data": "Your Dining Suggestions"}, "Body": {"Text": {"Data": body_text}}},
    )


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

            sqs.delete_message(QueueUrl=QURL, ReceiptHandle=m["ReceiptHandle"])
            processed += 1
        except Exception as e:

            print("Failed:", e)

    return {"status": "processed", "count": processed}





# import json
# import os
# import boto3
# from opensearchpy import OpenSearch, RequestsHttpConnection
# from requests_aws4auth import AWS4Auth
# from boto3.dynamodb.conditions import Key
# from botocore.vendored import requests

# REGION = 'us-east-1'
# HOST = 'search-domainnew-pbje5ydguhee4vwekzjjosqaby.us-east-1.es.amazonaws.com'
# INDEX = 'restaurants'
# db = boto3.resource('dynamodb').Table('final_db')

# def query(term):
#     q = {'size': 5, 'query': {'multi_match': {'query': term}}}

#     client = OpenSearch(hosts=[{
#         'host': HOST,
#         'port': 443
#     }],
#                         http_auth=get_awsauth(REGION, 'es'),
#                         use_ssl=True,
#                         verify_certs=True,
#                         connection_class=RequestsHttpConnection)

#     res = client.search(index=INDEX, body=q)
#     hits = res['hits']['hits']
#     results = []
#     for hit in hits:
#         results.append(hit['_source'])
#     return results


# def get_awsauth(region, service):
#     cred = boto3.Session().get_credentials()
#     return AWS4Auth(cred.access_key,
#                     cred.secret_key,
#                     region,
#                     service,
#                     session_token=cred.token)
                    
                    
# def queryDynamo(ids):
#     results = []
#     for id in ids:
#         response = db.query(KeyConditionExpression = Key("Business ID").eq(id))
#         results.append(response["Items"][0])
#     return results


# def lambda_handler(event, context):
#     sqs_queue_url = 'https://sqs.us-east-1.amazonaws.com/439569526489/messages'  # Replace with your SQS queue URL
    
#     # Receive a message from the SQS queue
#     sqs = boto3.client('sqs')
#     response = sqs.receive_message(
#         QueueUrl=sqs_queue_url,
#         AttributeNames=[
#             'All'
#         ],
#         MaxNumberOfMessages=1,
#         MessageAttributeNames=[
#             'All'
#         ],
#         VisibilityTimeout=0,
#         WaitTimeSeconds=0)
        
#     d = response['Messages'][0]
#     msg_body = json.loads(d['Body'])

#     if 'Messages' in response:
#         # Extract the message body from the received message
#         message = msg_body
#         # Extract data from the message slots
#         city = msg_body.get('City')
#         cuisine = msg_body.get('Cuisine')
#         date = msg_body.get('Date')
#         people = msg_body.get('People')
#         time = msg_body.get('Time')
#         email = 'ss6960@columbia.edu'
        
#         # Getting the message from the open source
#         query_resp = query(cuisine)
    
#         ids = []
#         for i in range(0,5):
#             ids.append(query_resp[i]['restaurant'])
        
#         # Pulling the restaurant information from the dynamoDB
#         db_rest = queryDynamo(ids)
        
#         # Sending the confirmation to the email
        
#         client = boto3.client("ses")
#         subject = "Reservation Details"
        
#         # Create the HTML body using the data from the message slots
#         body = f"Hello, you have a reservation for {people} people at {time} in {city} on {date} for {cuisine} cuisine."
#         for i in range(0,5): 
#             body += str(i) + ': ' + db_rest[i]['Name'] + 'at' + db_rest[i]['Address']+'\n'
            
#         # Send the email
#         email_response = client.send_email(
#             Source = "hv2179@nyu.edu",
#             Destination = {"ToAddresses": [email]},
#             Message = {"Subject": {"Data": subject}, "Body": {"Html": {"Data": body}}}
#         )
        
#         # Delete the received message from the SQS queue
#         receipt_handle = response['Messages'][0]['ReceiptHandle']
#         sqs.delete_message(
#             QueueUrl = sqs_queue_url,
#             ReceiptHandle = receipt_handle
#         )
        
#         return email_response
    
#     else:
#         return "No messages available in the queue."