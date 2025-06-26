import json
import boto3
import os

client = boto3.client("cognito-idp")

USER_POOL_ID = os.getenv("COGNITO_USER_POOL_ID", "ap-south-1_Bch3jYn0q")
ORIGIN = os.getenv("DOMAIN", "localhost")

headers = {
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Origin': ORIGIN,
    'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
}

def lambda_handler(event, context):
    try:
        if event.get("httpMethod") == "OPTIONS":
            return {
                "statusCode": 200,
                "headers": headers,
                "body": json.dumps({"message": "CORS preflight OK"})
            }

        if "body" not in event or not event["body"]:
            return {
                "statusCode": 400,
                "headers": headers,
                "body": json.dumps({"error": "Missing request body"})
            }

        body = json.loads(event["body"])
        username = body.get("username")
        group_name = body.get("group_name")

        if not username or not group_name:
            return {
                "statusCode": 400,
                "headers": headers,
                "body": json.dumps({
                    "error": "Both 'username' and 'group_name' are required"
                })
            }

        client.admin_add_user_to_group(
            UserPoolId=USER_POOL_ID,
            Username=username,
            GroupName=group_name
        )

        return {
            "statusCode": 200,
            "headers": headers,
            "body": json.dumps({
                "message": f"User '{username}' added to group '{group_name}'"
            })
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "headers": headers,
            "body": json.dumps({"error": str(e)})
        }
