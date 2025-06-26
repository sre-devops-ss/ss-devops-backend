import json
import boto3
import concurrent.futures
import logging
import urllib3
from datetime import datetime, timedelta, date

# Logger setup
logger = logging.getLogger()
logger.setLevel(logging.INFO)

http = urllib3.PoolManager()
API_GATEWAY_URL = "https://xxxxx.execute-api.ap-south-1.amazonaws.com/dashboard/dump"
def assume_role(account_id, role_name):
    sts_client = boto3.client('sts')
    assumed_role = sts_client.assume_role(
        RoleArn=f'arn:aws:iam::{account_id}:role/{role_name}',
        RoleSessionName='AssumedRoleSession'
    )
    credentials = assumed_role['Credentials']
    return {
        "aws_access_key_id": credentials['AccessKeyId'],
        "aws_secret_access_key": credentials['SecretAccessKey'],
        "aws_session_token": credentials['SessionToken']
    }

def get_aws_client(service_name, account_id, role_name):
    credentials = assume_role(account_id, role_name)
    return boto3.client(
        service_name,
        aws_access_key_id=credentials['aws_access_key_id'],
        aws_secret_access_key=credentials['aws_secret_access_key'],
        aws_session_token=credentials['aws_session_token']
    )

def get_default_policy_version(policy_arn, iam_client):
    try:
        policy_details = iam_client.get_policy(PolicyArn=policy_arn)
        default_version_id = policy_details['Policy']['DefaultVersionId']
        policy_version = iam_client.get_policy_version(
            PolicyArn=policy_arn,
            VersionId=default_version_id
        )
        return policy_version['PolicyVersion']['Document']
    except iam_client.exceptions.NoSuchEntityException:
        return None

def process_role(role, iam_client, account_id):
    role_name = role['RoleName']
    role_details = iam_client.get_role(RoleName=role_name)
    trust_policy = role_details['Role']['AssumeRolePolicyDocument']
    last_used = role_details['Role'].get('RoleLastUsed', {}).get('LastUsedDate', 'Never')

    # Attached Managed Policies
    attached_policies_response = iam_client.list_attached_role_policies(RoleName=role_name)
    attached_policies = [
        {
            "PolicyName": policy['PolicyName'],
            "PolicyDocument": get_default_policy_version(policy['PolicyArn'], iam_client)
        }
        for policy in attached_policies_response.get('AttachedPolicies', [])
    ]

    # Inline Policies
    inline_policies_response = iam_client.list_role_policies(RoleName=role_name)
    inline_policies = [
        {
            "PolicyName": policy_name,
            "PolicyDocument": iam_client.get_role_policy(RoleName=role_name, PolicyName=policy_name)['PolicyDocument']
        }
        for policy_name in inline_policies_response.get('PolicyNames', [])
    ]

    role_info = {
        'RoleName': role_name,
        'TrustPolicy': trust_policy,
        'LastUsed': str(last_used),
        'AttachedPolicies': attached_policies,
        'InlinePolicies': inline_policies,
        'AccountId': account_id,
        'Timestamp': str(date.today())
    }
    
    return role_info

def invoke_api_gateway(data):
    try:
        headers = {"Content-Type": "application/json"}
        http.request(
            "POST",
            API_GATEWAY_URL,
            body=json.dumps(data).encode("utf-8"),
            headers=headers,
            preload_content=False
        )
        logger.info("API Gateway request sent successfully.")
        return {"status": "success", "message": "API request sent"}
    except Exception as e:
        logger.error(f"Failed to invoke API Gateway: {str(e)}")
        return {"status": "error", "message": str(e)}

def get_accounts_from_parameter_store(parameter_name):
    ssm_client = boto3.client('ssm')
    try:
        response = ssm_client.get_parameter(Name=parameter_name, WithDecryption=True)
        account_data = json.loads(response['Parameter']['Value'])
        return account_data
    except ssm_client.exceptions.ParameterNotFound:
        logger.error(f"Parameter {parameter_name} not found in Parameter Store.")
        return {}

import concurrent.futures


def lambda_handler(event, context):
    PARAMETER_NAME = "/dashboard/client"
    ROLE_NAME = "devops-ui-cross-account"

    if 'method' in event:
        print("Found 'method' in event — processing single account")
        account_id = event.get('account_id', '').strip('"')
        account_name = event.get('account_name', '').strip('"')
        method = event['method']

        try:
            iam_client = get_aws_client('iam', account_id, ROLE_NAME)
            roles = iam_client.list_roles().get('Roles', [])
            role_details_list = []

            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                results = executor.map(
                    lambda role: process_role(role, iam_client, account_id),
                    roles
                )
                role_details_list.extend(results)

            if role_details_list:
                result = {
                    "db": account_name,
                    "collection": "iam_role",
                    "method": "insert_iamRole",
                    "body": role_details_list
                }
                invoke_api_gateway(result)
                print(result)

        except Exception as e:
            logger.error(f"Error processing account {account_id}: {str(e)}")

    else:
        print("No 'method' in event — fetching accounts from Parameter Store")
        account_data = get_accounts_from_parameter_store(PARAMETER_NAME)

        if not account_data:
            return {"statusCode": 400, "body": json.dumps({"error": "No accounts found"})}

        for account_id, full_account_name in account_data.items():
            try:
                iam_client = get_aws_client('iam', account_id, ROLE_NAME)
                account_name = full_account_name.split("-")[0]
                roles = iam_client.list_roles().get('Roles', [])
                role_details_list = []

                with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                    results = executor.map(
                        lambda role: process_role(role, iam_client, account_id),
                        roles
                    )
                    role_details_list.extend(results)

                if role_details_list:
                    result = {
                        "db": account_name,
                        "collection": "iam_role",
                        "method": "insert_iamRole",
                        "body": role_details_list
                    }
                    invoke_api_gateway(result)
                    print(result)

            except Exception as e:
                logger.error(f"Error processing account {account_id}: {str(e)}")

    return {
        "statusCode": 200,
        "body": json.dumps({
            "status": "success",
            "processed_accounts": 1 if 'method' in event else len(account_data)
        })
    }