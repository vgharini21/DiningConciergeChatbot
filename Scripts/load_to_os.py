
import os, boto3, requests
from requests.auth import HTTPBasicAuth

REGION = os.environ.get("AWS_REGION") or "us-east-1"
TABLE  = boto3.resource("dynamodb", region_name=REGION).Table("yelp-restaurants")

OS_URL = os.environ["OS_URL"].rstrip("/")      
OS_USER = os.environ["OS_USER"]
OS_PWD  = os.environ["OS_PWD"]
AUTH = HTTPBasicAuth(OS_USER, OS_PWD)

def main():
    total = 0
    scan_kwargs = {}
    while True:
        resp = TABLE.scan(**scan_kwargs)
        for item in resp.get("Items", []):
            rid = item.get("id")
            cuisine = item.get("cuisine")
            if not rid or not cuisine:
                continue
            doc = {"restaurant_id": rid, "cuisine": cuisine}
            r = requests.post(f"{OS_URL}/restaurants/_doc", json=doc, auth=AUTH, timeout=15)
            r.raise_for_status()
            total += 1
        if "LastEvaluatedKey" not in resp:
            break
        scan_kwargs["ExclusiveStartKey"] = resp["LastEvaluatedKey"]
    print(f"Indexed {total} docs.")

if __name__ == "__main__":
    main()
