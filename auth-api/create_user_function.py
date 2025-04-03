import os
import json
import boto3

client = boto3.client("cognito-idp")

USER_POOL_ID = os.getenv("COGNITO_USER_POOL_ID", "ap-south-1_Bch3jYn0q")

def lambda_handler(event, context):
    try:

        body = json.loads(event["body"])

        EMAIL = body.get("username")
        PASSWORD = body.get("password")

        if not EMAIL or not PASSWORD:
            return {
                "statusCode": 400,
                "body": json.dumps({"message": "Username and password are required"})
            }


        client.admin_create_user(
            UserPoolId=USER_POOL_ID,
            Username=EMAIL,
            UserAttributes=[
                {"Name": "email", "Value": EMAIL},
                {"Name": "email_verified", "Value": "true"},
            ],
            TemporaryPassword=PASSWORD,
            MessageAction="SUPPRESS"  # Prevents Cognito from sending an email
        )


        client.admin_set_user_password(
            UserPoolId=USER_POOL_ID,
            Username=EMAIL,
            Password=PASSWORD,
            Permanent=True
        )

        return {
            "statusCode": 200,
            "body": json.dumps({"message": f"User {EMAIL} created successfully"})
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
