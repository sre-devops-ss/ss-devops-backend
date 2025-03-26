import boto3
import boto3
import json
import datetime
import urllib3
from botocore.exceptions import ClientError
import os

SERVICE_THRESHOLDS = {
    "Amazon EC2": 50.00,
    "Amazon S3": 30.00,
    "AWS Lambda": 20.00,
    "Amazon RDS": 40.00,
    "AWS CloudWatch": 10.00
}
DEFAULT_THRESHOLD = 10.00

API_GATEWAY_URL = os.environ.get('API_GATEWAY_URL')
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

def get_anomaly_data(credentials):
    client = boto3.client(
        'ce',
        aws_access_key_id=credentials['aws_access_key_id'],
        aws_secret_access_key=credentials['aws_secret_access_key'],
        aws_session_token=credentials['aws_session_token']
    )

    end_date = datetime.date.today().strftime('%Y-%m-%d')
    start_date = (datetime.date.today() - datetime.timedelta(days=7)).strftime('%Y-%m-%d')

    try:
        response = client.get_cost_and_usage(
            TimePeriod={'Start': start_date, 'End': end_date},
            Granularity='DAILY',
            Metrics=['BlendedCost'],
            GroupBy=[{'Type': 'DIMENSION', 'Key': 'SERVICE'}]
        )

        cost_data = {}
        for result in response['ResultsByTime']:
            date = result['TimePeriod']['Start']
            for group in result['Groups']:
                service = group['Keys'][0]
                cost = float(group['Metrics']['BlendedCost']['Amount'])
                cost_data.setdefault(service, []).append((date, cost))

        return cost_data

    except ClientError as e:
        if e.response['Error']['Code'] == 'AccessDeniedException':
            print(f"Access Denied: Cannot fetch cost data for this account. Skipping...")
            return None 
        else:
            raise

def detect_anomalies(cost_data):
    """Detect cost anomalies based on predefined thresholds."""
    anomalies = []
    for service, costs in cost_data.items():
        previous_cost = None
        threshold = SERVICE_THRESHOLDS.get(service, DEFAULT_THRESHOLD)

        for date, cost in costs:
            if previous_cost is not None:
                increase = cost - previous_cost
                if increase > threshold:
                    anomalies.append({
                        "service": service,
                        "date": date,
                        "cost": cost,
                        "increase": increase,
                        "threshold": threshold
                    })
            previous_cost = cost

    return anomalies

def get_accounts_from_parameter_store(parameter_name):
    """Retrieve AWS accounts from SSM Parameter Store."""
    try:
        ssm_client = boto3.client('ssm')
        response = ssm_client.get_parameter(Name=parameter_name, WithDecryption=True)
        accounts = json.loads(response['Parameter']['Value'])
        return accounts
    except Exception as e:
        print(f"Error retrieving accounts from Parameter Store: {str(e)}")
        return {}

def invoke_api_gateway(db, collection, method, body):
    try:
        http = urllib3.PoolManager()
        headers = {"Content-Type": "application/json"}

        payload = {
            "db": db,
            "collection": collection,
            "method": method,
            "body": body
        }

        response = http.request(
            "POST",
            API_GATEWAY_URL,
            body=json.dumps(payload).encode("utf-8"),
            headers=headers
        )

        print(f"API Gateway request sent successfully. Response: {response.data}")
        return {"status": "success", "message": "API request sent", "response": response.data}

    except Exception as e:
        print(f"Failed to invoke API Gateway: {str(e)}")
        return {"status": "error", "message": str(e)}

def lambda_handler(event, context):
    print("Starting cost anomaly detection...")

    anomalies_report = {}
    
    PARAMETER_NAME = "/dashboard/client"
    ROLE_NAME = "devops-ui-cross-account"
    
    print("Fetching accounts from Parameter Store...")
    account_data = get_accounts_from_parameter_store(PARAMETER_NAME)
    
    if not account_data:
        return {"statusCode": 400, "body": json.dumps({"error": "No accounts found"})}

    for account_id, full_account_name in account_data.items():
        try:
            account_name = full_account_name.split("-")[0]
            print(f"Fetching cost data for {account_name} ({account_id})...")

            try:
                credentials = assume_role(account_id, ROLE_NAME)
                cost_data = get_anomaly_data(credentials)

                if cost_data is None:
                    continue 

                anomalies = detect_anomalies(cost_data)

                if anomalies:
                    print(f"Cost anomalies detected for {account_name}!")
                    anomalies_report[account_name] = anomalies
                    
                    invoke_api_gateway(
                        db=account_name, 
                        collection="cost_anomalies", 
                        method="insert-costAnomaly",
                        body=anomalies
                    )
                else:
                    print(f"No anomalies detected for {account_name}.")

            except Exception as e:
                print(f"Error processing account {account_name}: {e}")
                continue 
        except Exception as e:
            print(f"Error processing account {account_id}: {e}")

    print("Cost anomaly detection completed!")
    return {
        "statusCode": 200,
        "body": json.dumps(anomalies_report if anomalies_report else {"message": "No anomalies detected"}, indent=4)
    }
