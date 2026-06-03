import os
import uuid
from datetime import datetime, timezone
import boto3

AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")
INCIDENT_TABLE = os.getenv("INCIDENT_TABLE", "support-incidents")

dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
table = dynamodb.Table(INCIDENT_TABLE)

def create_incident(data: dict):
    incident_id = f"INC-{uuid.uuid4().hex[:8].upper()}"

    item = {
        "incident_id": incident_id,
        "customer_name": data["customer_name"],
        "email": data["email"],
        "title": data["title"],
        "description": data["description"],
        "category": data.get("category", "General"),
        "severity": data.get("severity", "Medium"),
        "status": "Open",
        "created_at": datetime.now(timezone.utc).isoformat()
    }

    table.put_item(Item=item)
    return item

def list_incidents():
    response = table.scan()
    return response.get("Items", [])
