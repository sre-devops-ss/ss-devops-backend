import json
import boto3
import concurrent.futures
import logging
from datetime import datetime, timedelta, date
import urllib3

# Initialize http connection manager
http = urllib3.PoolManager()

# Logger setup
logger = logging.getLogger()
logger.setLevel(logging.INFO)

API_GATEWAY_URL = "https://xxxxxxx.execute-api.ap-south-1.amazonaws.com/dashboard/dump"


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

def check_access_keys(username, iam_client):
    response = iam_client.list_access_keys(UserName=username)
    return len(response['AccessKeyMetadata']) > 0

def check_mfa(username, iam_client):
    response = iam_client.list_mfa_devices(UserName=username)
    return len(response.get('MFADevices', [])) > 0

def check_console_login(username, iam_client):
    try:
        iam_client.get_login_profile(UserName=username)
        return True
    except iam_client.exceptions.NoSuchEntityException:
        return False

def get_last_console_login(username, cloudtrail_client):
    response = cloudtrail_client.lookup_events(
        LookupAttributes=[{'AttributeKey': 'Username', 'AttributeValue': username}],
        StartTime=datetime.now() - timedelta(days=30),
        EndTime=datetime.now()
    )
    events = response.get('Events', [])
    if events:
        return max(event['EventTime'] for event in events)
    return None

def process_user(user, iam_client, cloudtrail_client, account_id):
    user_name = user['UserName']
    has_mfa = check_mfa(user_name, iam_client)
    has_console_login = check_console_login(user_name, iam_client)
    has_access_keys = check_access_keys(user_name, iam_client)
    last_console_login = get_last_console_login(user_name, cloudtrail_client)

    attached_policies_response = iam_client.list_attached_user_policies(UserName=user_name)
    attached_policies = [
        {"PolicyName": policy['PolicyName'], 
         "PolicyDocument": get_default_policy_version(policy['PolicyArn'], iam_client)}
        for policy in attached_policies_response.get('AttachedPolicies', [])
    ]

    user_details = {
        'UserName': user_name,
        'HasMFA': has_mfa,
        'HasConsoleLogin': has_console_login,
        'HasAccessKeys': has_access_keys,
        'LastConsoleLogin': str(last_console_login) if last_console_login else "Never",
        'AttachedPolicies': attached_policies,
        'AccountId': account_id,
        'Timestamp': str(date.today())
    }
    
    return user_details

def send_data_to_api(data):
    try:
        response = requests.post(API_GATEWAY_URL, json=data)
        response.raise_for_status()
        logger.info(f"Data successfully sent to API Gateway: {response.text}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error sending data to API Gateway: {str(e)}")

def get_accounts_from_parameter_store(parameter_name):
    """Retrieve account details from AWS Systems Manager Parameter Store."""
    ssm_client = boto3.client('ssm')
    try:
        response = ssm_client.get_parameter(Name=parameter_name, WithDecryption=True)
        account_data = json.loads(response['Parameter']['Value'])
        return account_data
    except ssm_client.exceptions.ParameterNotFound:
        logger.error(f"Parameter {parameter_name} not found in Parameter Store.")
        return {}

def invoke_api_gateway(data):
    """Invoke API Gateway URL asynchronously using urllib3."""
    try:
        headers = {"Content-Type": "application/json"}
        payload = json.dumps(data)

        print("DEBUG | Invoking API Gateway")
        print("DEBUG | Payload length:", len(payload))
        print("DEBUG | Payload preview:", payload[:300]) 

        # Fire and forget
        response = http.request(
            "POST",
            API_GATEWAY_URL,
            body=payload.encode("utf-8"),
            headers=headers,
            preload_content=False
        )

        print("DEBUG | API Request sent. Response status:", response.status)
        return {"status": "success", "message": "API request sent", "status_code": response.status}

    except Exception as e:
        logger.error(f"Failed to invoke API Gateway: {str(e)}")
        return {"status": "error", "message": str(e)}

def lambda_handler(event, context):
    PARAMETER_NAME = "/dashboard/client"
    ROLE_NAME = "devops-ui-cross-account"

    all_users_data = []
    if 'method' in event:
        print("Found 'method' in event — processing single account")
        account_id = event.get('account_id', '').strip('"')
        account_name = event.get('account_name', '').strip('"')
        method = event['method']

        try:
            print("Processing account:", account_name)
            iam_client = get_aws_client('iam', account_id, ROLE_NAME)
            cloudtrail_client = get_aws_client('cloudtrail', account_id, ROLE_NAME)

            users = iam_client.list_users().get('Users', [])
            user_details_list = []

            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                results = executor.map(
                    lambda user: process_user(user, iam_client, cloudtrail_client, account_id),
                    users
                )
                user_details_list.extend(results)

            all_users_data.extend(user_details_list)

            result = {
                "db": account_name,
                "collection": "iam_user",
                "method": "insert_iam",
                "body": all_users_data
            }
            print(result)

            if all_users_data:
                invoke_api_gateway(result)

        except Exception as e:
            logger.error(f"Error processing account {account_id}: {str(e)}")

    else:
        print("No 'method' in event — fetching accounts from Parameter Store")
        account_data = get_accounts_from_parameter_store(PARAMETER_NAME)

        if not account_data:
            return {"statusCode": 400, "body": json.dumps({"error": "No accounts found"})}

        for account_id, full_account_name in account_data.items():
            try:
                print("full_account_name", full_account_name)
                account_name = full_account_name.split("-")[0]
                iam_client = get_aws_client('iam', account_id, ROLE_NAME)
                cloudtrail_client = get_aws_client('cloudtrail', account_id, ROLE_NAME)

                users = iam_client.list_users().get('Users', [])
                user_details_list = []

                with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                    results = executor.map(
                        lambda user: process_user(user, iam_client, cloudtrail_client, account_id),
                        users
                    )
                    user_details_list.extend(results)

                all_users_data.extend(user_details_list)

                result = {
                    "db": account_name,
                    "collection": "iam_user",
                    "method": "insert_iam",
                    "body": all_users_data
                }
                print(result)

                if all_users_data:
                    invoke_api_gateway(result)

            except Exception as e:
                logger.error(f"Error processing account {account_id}: {str(e)}")

    return {
        "statusCode": 200,
        "body": json.dumps({
            "status": "success",
            "processed_accounts": 1 if 'method' in event else len(account_data)
        })
    }
