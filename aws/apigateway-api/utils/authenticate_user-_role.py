import json
import os
from pymongo import MongoClient

MONGODB_URI = os.environ.get("MONGODB_URI")

DB_NAME = "user"
COLLECTION_NAME = "user"

def lambda_handler(event, context):
    try:
        body = event.get("body")
        if isinstance(body, str):
            body = json.loads(body)

        sub = body.get("sub")
        acc_name = body.get("accountName")
        acc_uid = body.get("accUid")

        if not (sub and acc_name and acc_uid):
            return {"statusCode": 400, "body": json.dumps({"error": "Missing required fields"})}

        client = MongoClient(MONGODB_URI)
        db = client[DB_NAME]
        collection = db[COLLECTION_NAME]

        query = {f"user.{sub}": {"$exists": True}}
        doc = collection.find_one(query)

        if not doc:
            return {"statusCode": 404, "body": json.dumps({"error": "User not found"})}

        user_data = doc["user"][sub]
        accounts = user_data.get("account", [])

        for acc in accounts:
            if acc.get("accountName") == acc_name and acc.get("accUid") == acc_uid:
                return {
                    "statusCode": 200,
                    "body": json.dumps({"accountId": acc["accountId"]})
                }

        return {
            "statusCode": 404,
            "body": json.dumps({"error": "Account not found"})
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
