import json
import boto3
import os

CLIENT_ID = os.getenv("COGNITO_CLIENT_ID", "1_Bch3jYn0q")

client = boto3.client("cognito-idp")

def lambda_handler(event, context):
    try:
        body = json.loads(event["body"])
        username = body.get("username")
        password = body.get("password")

        if not username or not password:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Username and password are required!"})
            }

        response = client.initiate_auth(
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={
                "USERNAME": username,
                "PASSWORD": password,
            },
            ClientId=CLIENT_ID
        )

        auth_result = response["AuthenticationResult"]

        return {
            "statusCode": 200,
            "body": json.dumps({
                "access_token": auth_result["AccessToken"],
                "id_token": auth_result["IdToken"],
                "refresh_token": auth_result["RefreshToken"],
                "message": "Login successful!"
            })
        }

    except client.exceptions.NotAuthorizedException:
        return {
            "statusCode": 401,
            "body": json.dumps({"error": "Incorrect username or password!"})
        }

    except client.exceptions.UserNotFoundException:
        return {
            "statusCode": 404,
            "body": json.dumps({"error": "User does not exist!"})
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
