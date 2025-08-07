import os
import json
import boto3

client = boto3.client("cognito-idp")
lambda_client = boto3.client("lambda")

USER_POOL_ID = os.getenv("COGNITO_USER_POOL_ID", "ap-south-1_Bch3jYn0q")
ORIGIN = os.getenv("DOMAIN", "localhost")

headers = {
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Origin': f"{ORIGIN}",
    'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
}

def apiResponse(message, statuscode):
    return {
        'headers': headers,
        "statusCode": statuscode,
        "body": json.dumps({"message": message})
    }

def lambda_handler(event, context):
    try:
        body = json.loads(event.get("body", "{}"))
        print("Request Body:", body)

        EMAIL = body.get("username")
        PASSWORD = body.get("password")
        user_sub = body.get("user_sub")

        if not EMAIL or not PASSWORD:
            return apiResponse("Username and password are required", 400)

        if user_sub:
            response = lambda_client.invoke(
                FunctionName="resource-Monitoring",
                InvocationType="RequestResponse",
                Payload=json.dumps(event)
            )

            return apiResponse(f"User {EMAIL} updated successfully", 200)

        return apiResponse("User sub not provided", 400)

    except Exception as e:
        print("Error:", str(e))
        return apiResponse(f"Internal Server Error: {str(e)}", 500)
