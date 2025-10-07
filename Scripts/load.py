
import os
import time
import random
from datetime import datetime
from decimal import Decimal
import requests
import boto3


REGION = os.environ.get("AWS_REGION") or "us-east-1"
SSM_PARAM = "/cc-hw1/yelp_api_key"
TABLE_NAME = "yelp-restaurants"


CUISINES = {
    "japanese": "japanese",
    "chinese": "chinese",
    "italian": "italian",
    "indian": "indpak",     
    "mexican": "mexican",
    "french": "french",
}

YELP_BASE = "https://api.yelp.com/v3/businesses/search"
PAGE_LIMIT = 50          
TARGET_PER_CUISINE = 200
MAX_OFFSET = 240- PAGE_LIMIT       


ssm = boto3.client("ssm", region_name=REGION)
ddb = boto3.resource("dynamodb", region_name=REGION).Table(TABLE_NAME)


def get_yelp_key():
    resp = ssm.get_parameter(Name=SSM_PARAM, WithDecryption=True)
    return resp["Parameter"]["Value"]

def to_decimal(x):
    """Recursively convert floats to Decimal and drop None/empty values."""
    if isinstance(x, float):
        return Decimal(str(x))
    if isinstance(x, dict):
        out = {}
        for k, v in x.items():
            if v is None or v == "" or v == [] or v == {}:
                continue
            out[k] = to_decimal(v)
        return out
    if isinstance(x, list):
        out = []
        for v in x:
            if v is None or v == "" or v == [] or v == {}:
                continue
            out.append(to_decimal(v))
        return out
    return x  

def fetch_page(yelp_category: str, offset: int) -> list:
    """Call Yelp search; no sort_by (avoid 400 when using string location)."""
    params = {
        "categories": yelp_category,
        "location": "Manhattan, NY",
        "limit": PAGE_LIMIT,
        "offset": offset,
        
    }
    r = requests.get(YELP_BASE, headers=HEADERS, params=params, timeout=20)

    
    if r.status_code == 429:
        time.sleep(3)
        r = requests.get(YELP_BASE, headers=HEADERS, params=params, timeout=20)

    if not r.ok:
        
        print(f"Fetch error {yelp_category}@{offset}: {r.status_code} {r.reason} | body={r.text[:200]}")
        return []

    payload = r.json() or {}
    return payload.get("businesses", []) or []

def build_item(b: dict, cuisine_label: str) -> dict:
    """Build a DynamoDB item for a Yelp business."""
    coords_src = b.get("coordinates") or {}
    coords = None
    if coords_src.get("latitude") is not None and coords_src.get("longitude") is not None:
        coords = {
            "latitude": coords_src.get("latitude"),
            "longitude": coords_src.get("longitude"),
        }

    item = {
        "id": b.get("id"), 
        "name": b.get("name"),
        "address": ", ".join((b.get("location") or {}).get("display_address", [])),
        "coordinates": coords,                         
        "review_count": b.get("review_count"),        
        "rating": b.get("rating"),                    
        "zip_code": (b.get("location") or {}).get("zip_code"),
        "cuisine": cuisine_label,
        "insertedAtTimestamp": datetime.utcnow().isoformat(),
    }
    return to_decimal(item)

if __name__ == "__main__":
    YELP_KEY = get_yelp_key()
    HEADERS = {"Authorization": f"Bearer {YELP_KEY}"}

    seen_ids = set()
    total_inserted = 0

    for label, ycat in CUISINES.items():
        collected = 0
        offset = 0
        empty_pages_seen = 0

        while collected < TARGET_PER_CUISINE and offset < MAX_OFFSET:
            businesses = fetch_page(ycat, offset)
            if not businesses:
                empty_pages_seen += 1
                
                if empty_pages_seen >= 3:
                    print(f"{label}: no more results (stopping early at {collected}).")
                    break
                offset += PAGE_LIMIT
                continue

            empty_pages_seen = 0  
            for b in businesses:
                rid = b.get("id")
                if not rid or rid in seen_ids:
                    continue
                seen_ids.add(rid)

                try:
                    item = build_item(b, label)
                    
                    if not item.get("id") or not item.get("name"):
                        continue

                    ddb.put_item(Item=item)
                    collected += 1
                    total_inserted += 1
                except Exception as e:
                    print(f"Put error id={rid}: {e}")
                    continue

                if collected >= TARGET_PER_CUISINE:
                    break

            offset += PAGE_LIMIT
            time.sleep(0.35)  

        print(f"{label}: inserted {collected}")

    print(f"Done. Inserted approximately {total_inserted} items across cuisines.")
