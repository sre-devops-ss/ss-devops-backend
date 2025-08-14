import os
import json
import boto3
import requests

UPDATE_URL = "/api/user/update"
ORIGIN = os.getenv("DOMAIN", "awsmonitor.supportsages.com")

headers = {
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
}

def apiResponse(message, statuscode):
    return {
        'headers': headers,
        "statusCode": statuscode,
        "body": json.dumps({"message": message})
    }

def get_refresh_token():
    ssm_client = boto3.client('ssm')
    param = ssm_client.get_parameter(
        Name='/ss/backend/refresh_token',
        WithDecryption=True
    )
    return param['Parameter']['Value']

def post_account_update(account_id, account_name, user_sub):
    token = get_refresh_token()
    payload = {
        "account_id": account_id,
        "account_name": account_name,
        "user_sub": user_sub,
        "dataType": "account"
    }
    url = f"https://{ORIGIN}{UPDATE_URL}"
    return requests.post(
        url,
        json=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
    )

def lambda_handler(event, context):
    try:
        print(event)
        # account_name = os.getenv("ACCOUNT_NAME")
        account_name = event["ACCOUNT_NAME"].strip('"')
        # account_id = os.getenv("ACCOUNT_NUMBER")
        account_id = event["ACCOUNT_NUMBER"].strip('"')
        # user_sub = os.getenv("userSub")
        user_sub = event["userSub"].strip('"')
        EMAIL = event["EMAIL"].strip('"')
        print(user_sub)
        response = post_account_update(account_id, account_name, user_sub)
        print(response)
        if response.status_code in [401, 403]:
            print(response.text)
        if response.status_code == 200:
            return apiResponse("Account updated successfully", 200)
        else:
            return apiResponse(
                f"Failed to update account: {response.text}",
                response.status_code
            )
    except Exception as e:
        return apiResponse(str(e), 500)
