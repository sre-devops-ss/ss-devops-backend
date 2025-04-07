import os
import json
import boto3

client = boto3.client("cognito-idp")

USER_POOL_ID = os.getenv("COGNITO_USER_POOL_ID", "ap-south-1_Bch3jYn0q")
ORIGIN= os.getenv("DOMAIN","localhost")
headers= {
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Origin': f"{ORIGIN}",
    'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
}
def apiResponse(message, statuscode):

    return  {
        'headers':headers,
        "statusCode":statuscode,
        "body": json.dumps({"message": message})
    }


def lambda_handler(event, context):
    try:

        body = json.loads(event["body"])

        EMAIL = body.get("username")
        PASSWORD = body.get("password")

        if not EMAIL or not PASSWORD:
            return apiResponse("Username and password are required",400)

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

        return  apiResponse(f"User created successfully",200)


    except Exception as e:
       return apiResponse(str(e),500)

