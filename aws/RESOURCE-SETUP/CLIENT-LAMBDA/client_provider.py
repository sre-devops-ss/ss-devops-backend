import os
import json
import sys
import boto3

from monitor_relay import postData

UPDATE_URL = "/api/user/update"

ORIGIN= os.getenv("DOMAIN","awsmonitor.supportsages.com")
headers= {
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Origin': f"*",
    'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
}
def apiResponse(message, statuscode):

    return  {
        'headers':headers,
        "statusCode":statuscode,
        "body": json.dumps({"message": message})
    }
# def get_account_details():
#     sts_client = boto3.client('sts')
#     identity = sts_client.get_caller_identity()
#     account_id = identity["Account"]
# 
#     # org_client = boto3.client('organizations')
#     # account_detail = org_client.describe_account(AccountId=account_id)
#     # account_name = account_detail['Account']['Name']
#     # account_name = "test"
# 
# 
#     return account_id

def post_account_update(account_id, account_name):
    payload = {
        "account_id": account_id,
        "account_name": account_name,
        "user_sub": user_sub,
        "dataType": "account"
    }
    return postData(UPDATE_URL, payload)


def lambda_handler(event, context):
    try:
        print(event)
        account_name = os.getenv("ACCOUNT_NAME")
        account_id = os.getenv("ACCOUNT_NUMBER")
        user_sub = os.getenv("userSub")
        response = post_account_update(account_id, account_name)
        if response.status_code in [401, 403]:
            print(response.text)
        if response.status_code == 200:
            return apiResponse("Account updated successfully", 200)
        else:
            return apiResponse(f"Failed to update account: {response.text}",response.status_code )
    except Exception as e:
        return apiResponse(str(e), 500)