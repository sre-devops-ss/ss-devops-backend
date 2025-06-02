import boto3
import json
import urllib3
import logging
from datetime import datetime

# Init HTTP and logger
http = urllib3.PoolManager()
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Set your target API Gateway URL here
API_GATEWAY_URL = "https://xxxxxxxx.execute-api.ap-south-1.amazonaws.com/dashboard/dump"

def get_accounts_from_parameter_store(param_name):
    ssm = boto3.client("ssm")
    try:
        response = ssm.get_parameter(Name=param_name)
        account_data = json.loads(response['Parameter']['Value'])
        return account_data
    except Exception as e:
        print(f"Error fetching parameter {param_name}: {str(e)}")
        return None

def get_cost_and_usage(start_date, end_date, account_id, granularity):
    sts_client = boto3.client('sts')

    assumed_role = sts_client.assume_role(
        RoleArn=f'arn:aws:iam::{account_id}:role/devops-ui-cross-account',
        RoleSessionName='AssumedRoleSession'
    )

    client = boto3.client(
        'ce',
        aws_access_key_id=assumed_role['Credentials']['AccessKeyId'],
        aws_secret_access_key=assumed_role['Credentials']['SecretAccessKey'],
        aws_session_token=assumed_role['Credentials']['SessionToken']
    )

    try:
        print(f"Start Date: {start_date}, End Date: {end_date}, Granularity: {granularity}")

        response = client.get_cost_and_usage(
            TimePeriod={
                'Start': start_date,
                'End': end_date
            },
            Granularity=granularity,
            Metrics=['UnblendedCost'],
            GroupBy=[
                {
                    'Type': 'DIMENSION',
                    'Key': 'SERVICE'
                },
            ],
            Filter={
                'And': [
                    {
                        'Dimensions': {
                            'Key': 'LINKED_ACCOUNT',
                            'Values': [account_id]
                        }
                    },
                    {
                        'Dimensions': {
                            'Key': 'RECORD_TYPE',
                            'Values': ['Usage']
                        }
                    }
                ]
            }
        )

        results = response['ResultsByTime']
        data_list = []
        total_cost = 0  # Initialize total cost

        for result in results:
            date = result['TimePeriod']['Start']
            for group in result['Groups']:
                service = group['Keys'][0]
                cost = float(group['Metrics']['UnblendedCost']['Amount'])
                total_cost += cost  # Add cost to total
                data_list.append({
                    "Date": date,
                    "Service": service,
                    "Usage_Cost": cost,
                    "Account_id": account_id
                })

        return data_list, total_cost  # Return data and total cost

    except Exception as e:
        print(f"Error: {str(e)}")
        return None, 0  # Return 0 as total cost in case of error

def invoke_api_gateway(data):
    """Invoke API Gateway URL asynchronously using urllib3."""
    try:
        headers = {"Content-Type": "application/json"}

        # Fire and forget, without waiting for the response
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

import boto3
import json
from datetime import datetime

def lambda_handler(event, context):
    PARAMETER_NAME = "/dashboard/client"
    ROLE_NAME = "devops-ui-cross-account"

    start_date = event.get("startDate", "2025-01-01")
    end_date = event.get("endDate", datetime.utcnow().date().isoformat())
    granularity = event.get("granularity", "DAILY")

    logger.info("Fetching accounts...")

    responses = []

    if 'method' in event:
        logger.info("Found 'method' in event — processing single account")
        cross_account_id = event.get('account_id', '').strip('"')
        account_name = event.get('account_name', '').strip('"')

        try:
            logger.info(f"Processing account: {account_name}")

            data_list = get_cost_and_usage(start_date, end_date, cross_account_id, granularity)
            print(data_list)
            result = {
                "db": account_name,
                "collection": "CostAndUsage",
                "method": "insert_costUsage",
                "body": data_list
            }

            print(result)
            invoke_response = invoke_api_gateway(result)
            responses.append({
                "account_id": cross_account_id,
                "status": invoke_response['status'],
                "message": invoke_response['message']
            })

        except Exception as e:
            logger.error(f"Error processing account {cross_account_id}: {str(e)}")
            responses.append({
                "account_id": cross_account_id,
                "status": "error",
                "message": str(e)
            })

    else:
        logger.info("No 'method' in event — using Parameter Store")
        account_data = get_accounts_from_parameter_store(PARAMETER_NAME)

        if not account_data:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "No accounts found"}),
                "headers": {"Content-Type": "application/json"}
            }

        for account_id, full_account_name in account_data.items():
            try:
                logger.info(f"Processing account: {full_account_name}")
                account_name = full_account_name.split("-")[0]

                data_list = get_cost_and_usage(start_date, end_date, account_id, granularity)
                print(data_list)
                result = {
                    "db": account_name,
                    "collection": "CostAndUsage",
                    "method": "insert_costUsage",   # default method
                    "body": data_list
                }
                print(result)
                invoke_response = invoke_api_gateway(result)
                responses.append({
                    "account_id": account_id,
                    "status": invoke_response['status'],
                    "message": invoke_response['message']
                })

            except Exception as e:
                logger.error(f"Error processing account {account_id}: {str(e)}")
                responses.append({
                    "account_id": account_id,
                    "status": "error",
                    "message": str(e)
                })

    return {
        "statusCode": 200,
        "body": json.dumps(responses),
        "headers": {
            "Content-Type": "application/json"
        }
    }