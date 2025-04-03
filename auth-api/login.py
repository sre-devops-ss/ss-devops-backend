import json
import boto3
import os

# Get Cognito Client ID from environment variable
CLIENT_ID = os.getenv("COGNITO_CLIENT_ID")
if not CLIENT_ID:
    raise ValueError("COGNITO_CLIENT_ID environment variable is not set")

client = boto3.client("cognito-idp")

def lambda_handler(event, context):

    print("Received event:", json.dumps(event))

    try:

        if "body" not in event or not isinstance(event["body"], str):
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Request body is missing or invalid"})
            }


        body = json.loads(event["body"])
        username = body.get("username")
        password = body.get("password")

        if not username or not password:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Username and password are required"})
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
                "refresh_token": auth_result.get("RefreshToken", "Not provided"),
                "message": "Login successful"
            })
        }

    except json.JSONDecodeError:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Invalid JSON in request body"})
        }
    except client.exceptions.NotAuthorizedException:
        return {
            "statusCode": 401,
            "body": json.dumps({"error": "Incorrect username or password"})
        }
    except client.exceptions.UserNotFoundException:
        return {
            "statusCode": 404,
            "body": json.dumps({"error": "User does not exist"})
        }
    except client.exceptions.ClientError as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": f"Cognito error: {str(e)}"})
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": f"Unexpected error: {str(e)}"})
        }