import json
import boto3
import os

# Get Cognito Client ID from environment variable
CLIENT_ID = os.getenv("COGNITO_CLIENT_ID")
if not CLIENT_ID:
    raise ValueError("COGNITO_CLIENT_ID environment variable is not set")

client = boto3.client("cognito-idp")

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

    print("Received event:", json.dumps(event))

    try:

        if "body" not in event or not isinstance(event["body"], str):
            return  apiResponse("Request body is missing or invalid",400)



        body = json.loads(event["body"])
        username = body.get("username")
        password = body.get("password")

        if not username or not password:
            return apiResponse("Username and password are required",400)



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
            "headers": headers,
            "body": json.dumps({
                "access_token": auth_result["AccessToken"],
                "id_token": auth_result["IdToken"],
                "refresh_token": auth_result.get("RefreshToken", "Not provided"),
                "message": "Login successful"
            })
        }
    except json.JSONDecodeError:
        return apiResponse("Invalid JSON in request body",400)

    except client.exceptions.NotAuthorizedException:
        return apiResponse("Incorrect username or password",401)
    except client.exceptions.UserNotFoundException:
       return  apiResponse("User does not exist",404)
    except client.exceptions.ClientError as e:
        return  apiResponse(str(e),500)
    except Exception as e:
        return apiResponse(str(e),500)