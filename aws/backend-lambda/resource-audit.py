import boto3
import json
from datetime import datetime, timedelta
import urllib3

API_GATEWAY_URL = "https://xxxxxxxxxx.execute-api.ap-south-1.amazonaws.com/dashboard/dump"

def get_accounts_from_parameter_store(parameter_name):
    """Fetch account data from AWS SSM Parameter Store"""
    ssm_client = boto3.client('ssm')
    response = ssm_client.get_parameter(Name=parameter_name, WithDecryption=True)
    return json.loads(response['Parameter']['Value'])

def assume_role(account_id, role_name):
    """Assume IAM role in another AWS account"""
    sts_client = boto3.client('sts')
    try:
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
    except Exception as e:
        print(f"Failed to assume role in account {account_id}: {e}")
        return None

def get_aws_clients(account_id, role_name):
    """Return AWS clients for cross-account access"""
    creds = assume_role(account_id, role_name)
    if not creds:
        return None
    
    session = boto3.session.Session(
        aws_access_key_id=creds["aws_access_key_id"],
        aws_secret_access_key=creds["aws_secret_access_key"],
        aws_session_token=creds["aws_session_token"]
    )
    
    return {
        "resource-explorer-2": session.client('resource-explorer-2')
    }

def list_all_resources(clients, account_id):
    """Fetch all AWS resources using Resource Explorer"""
    resource_client = clients['resource-explorer-2']
    resources = []
    next_token = None
    
    try:
        while True:
            params = {"QueryString": ""}
            if next_token:
                params["NextToken"] = next_token
            
            response = resource_client.search(**params)
            
            for resource in response.get("Resources", []):
                resources.append({
                    "arn": resource["Arn"],
                    "ResourceType": resource["ResourceType"],
                    "region": resource["Region"],
                    "service": resource["Arn"].split(":")[2],
                    "date": datetime.utcnow().strftime("%Y-%m-%d"),
                    "account_id": account_id
                })
            
            next_token = response.get("NextToken")
            if not next_token:
                break
    except Exception as e:
        print(f"Error fetching resources: {e}")
        return []
    
    return resources

def invoke_api_gateway(data):
    """Invoke API Gateway URL asynchronously using urllib3."""
    try:
        http = urllib3.PoolManager()
        headers = {"Content-Type": "application/json"}

        # Fire and forget, without waiting for the response
        http.request(
            "POST",
            API_GATEWAY_URL,
            body=json.dumps(data).encode("utf-8"),
            headers=headers,
            preload_content=False  # Do not wait for response
        )

        print("API Gateway request sent successfully.")
        return {"status": "success", "message": "API request sent"}
    
    except Exception as e:
        print(f"Failed to invoke API Gateway: {str(e)}")
        return {"status": "error", "message": str(e)}

def lambda_handler(event, context):
    PARAMETER_NAME = "/dashboard/client"
    ROLE_NAME = "devops-ui-cross-account"

    # Determine method to use
    method_from_event = event.get('method', 'insert-iamUser')

    accounts_to_process = {}

    if 'method' in event:
        print("Found 'method' in event — processing single account")

        account_id = event.get('account_id', '').strip('"')
        account_name = event.get('account_name', '').strip('"')
        body_data = event.get('body', [])

        if not account_id or not account_name or not body_data:
            return {"statusCode": 400, "body": "Missing account_id, account_name or body in event."}

        accounts_to_process[account_id] = account_name
        process_from_event = True

    else:
        print("Fetching accounts from Parameter Store...")
        account_data = get_accounts_from_parameter_store(PARAMETER_NAME)
        
        if not account_data:
            print("No accounts found.")
            return {"statusCode": 400, "body": "No accounts found."}
        
        accounts_to_process = account_data
        process_from_event = False

    results_summary = []


    for account_id, full_account_name in accounts_to_process.items():
        account_name = full_account_name.split("-")[0]
        print(f"Processing account: {account_name} ({account_id})")

        clients = get_aws_clients(account_id, ROLE_NAME)
        if not clients:
            print(f"Skipping {account_id} due to role assumption failure.")
            results_summary.append({"account_id": account_id, "status": "role assumption failure"})
            continue

        if process_from_event:
            # Use event-provided data
            all_resources = body_data
        else:
            # Fetch fresh data
            all_resources = list_all_resources(clients, account_id)
            if not all_resources:
                print(f"Skipping {account_id} due to resource fetch failure.")
                results_summary.append({"account_id": account_id, "status": "no resources"})
                continue

        print(all_resources)
        result = {
            "db": account_name,
            "collection": "resource_explorer",
            "method": "insert-resources",
            "body": all_resources
        }

        invoke_api_gateway(result)
        results_summary.append({"account_id": account_id, "status": "success", "resources": len(all_resources)})

    print("Resource data processing complete.")
    return {
        "statusCode": 200,
        "body": json.dumps({
            "status": "complete",
            "processed_accounts": len(accounts_to_process),
            "results": results_summary
        })
    }