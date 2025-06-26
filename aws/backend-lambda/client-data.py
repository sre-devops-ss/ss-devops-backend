import boto3
from pymongo import MongoClient
from datetime import datetime, timedelta
import os
import logging
import json
import urllib3


# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ROLE_NAME = os.getenv("ROLE_NAME", "devops-ui-cross-account")
API_GATEWAY_URL = "https://xxxxxxx.execute-api.ap-south-1.amazonaws.com/dashboard/dump"

def get_accounts_from_parameter_store(parameter_name):
    """Retrieve AWS accounts from SSM Parameter Store."""
    try:
        ssm_client = boto3.client('ssm')
        response = ssm_client.get_parameter(Name=parameter_name, WithDecryption=True)
        accounts = json.loads(response['Parameter']['Value'])  # Ensure this matches expected JSON structure
        return accounts
    except Exception as e:
        logger.error(f"Error retrieving accounts from Parameter Store: {str(e)}")
        return {}

def assume_role(account_id, role_name):
    """Assume a role in a target AWS account."""
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

def get_aws_clients(account_id, role_name):
    """Create AWS service clients using assumed role credentials."""
    credentials = assume_role(account_id, role_name)
    return {
        'ce_client': boto3.client('ce', **credentials),
        'budget_client': boto3.client('budgets', **credentials),
        'sts_client': boto3.client('sts', **credentials),
        'ec2_client': boto3.client('ec2', **credentials),
        's3_client': boto3.client('s3', **credentials),
        'backup_client': boto3.client('backup', **credentials),
        'sns_client': boto3.client('sns', **credentials)
    }

def send_sns_notification(sns_client, subject, message):
    """Send an SNS notification."""
    try:
        response = sns_client.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject=subject,
            Message=message
        )
        logger.info(f"SNS notification sent: {response}")
    except Exception as e:
        logger.error(f"Error sending SNS notification: {str(e)}")

def check_data_transfer(ce_client, sns_client, threshold_gb=100):
    """Check daily AWS data transfer and send alerts if exceeded."""
    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=1)

    try:
        response = ce_client.get_cost_and_usage(
            TimePeriod={'Start': start_date.strftime('%Y-%m-%d'), 'End': end_date.strftime('%Y-%m-%d')},
            Granularity='DAILY',
            Metrics=['UsageQuantity'],
            GroupBy=[{'Type': 'DIMENSION', 'Key': 'USAGE_TYPE'}]
        )

        total_gb = sum(
            float(group['Metrics']['UsageQuantity']['Amount']) / (1024 ** 3)  # Convert bytes to GB
            for group in response['ResultsByTime'][0]['Groups']
            if 'DataTransfer' in group['Keys'][0] or 'Bytes' in group['Keys'][0]
        )

        status = "Exceeded" if total_gb > threshold_gb else "Within Limit"
        alert_data = {"total_gb": round(total_gb, 2), "Limit": threshold_gb, "Status": status, "timestamp": datetime.utcnow().isoformat()}
        
        if total_gb > threshold_gb:
            send_sns_notification(sns_client, "Data Transfer Alert", json.dumps(alert_data, indent=4))
        
        return alert_data
    except Exception as e:
        logger.error(f"Error checking data transfer: {str(e)}")
        return {}

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

        logger.info("API Gateway request sent successfully.")
        return {"status": "success", "message": "API request sent"}
    
    except Exception as e:
        logger.error(f"Failed to invoke API Gateway: {str(e)}")
        return {"status": "error", "message": str(e)}

def lambda_handler(event, context):
    """AWS Lambda entry point."""
    PARAMETER_NAME = "/dashboard/client"
    ROLE_NAME = "devops-ui-cross-account"

    print("Fetching accounts from Parameter Store...")
    account_data = get_accounts_from_parameter_store(PARAMETER_NAME)

    if not account_data:
        return {"statusCode": 400, "body": json.dumps({"error": "No accounts found"})}

    all_results = []

    for account_id, full_account_name in account_data.items():
        try:
            account_name = full_account_name.split("-")[0]
            print(f"Processing account: {account_name} ({account_id})")

            clients = get_aws_clients(account_id, ROLE_NAME)
            alerts = {
                "account": None,
                "Budget_Alerts": [],
                "Backup_Alerts": [],
                "S3_Alerts": [],
                "Data_Transfer_Alerts": [],
                "Regions": [],
                "Default_Region": None
            }

            # Get Account ID
            account_id = clients['sts_client'].get_caller_identity().get('Account')
            alerts["account"] = account_id

            # Fetch AWS regions
            try:
                response = clients['ec2_client'].describe_regions(AllRegions=True)
                alerts["Regions"] = [
                    r['RegionName'] for r in response['Regions']
                    if r['OptInStatus'] in ['opt-in-not-required', 'opted-in']
                ]
                alerts["Default_Region"] = clients['ec2_client'].meta.region_name
            except Exception as e:
                logger.error(f"Error retrieving region details: {str(e)}")

            # Data Transfer Alerts
            try:
                alerts["Data_Transfer_Alerts"] = check_data_transfer(
                    clients['ce_client'], clients['sns_client']
                )
            except Exception as e:
                logger.error(f"Error checking data transfer: {str(e)}")

            # Budget Alerts
            try:
                budget_response = clients['budget_client'].describe_budgets(AccountId=account_id)
                for budget in budget_response.get('Budgets', []):
                    alerts["Budget_Alerts"].append({
                        "BudgetName": budget['BudgetName'],
                        "Limit": budget.get('BudgetLimit'),
                        "TimePeriod": budget.get('TimePeriod'),
                        "BudgetType": budget.get('BudgetType')
                    })
            except Exception as e:
                logger.error(f"Error retrieving budget alerts: {str(e)}")

            # Backup Alerts
            try:
                backup_vaults = clients['backup_client'].list_backup_vaults().get('BackupVaultList', [])
                for vault in backup_vaults:
                    vault_name = vault['BackupVaultName']
                    jobs = clients['backup_client'].list_backup_jobs(
                        BackupVaultName=vault_name,
                        ByState='FAILED'
                    ).get('BackupJobs', [])
                    if jobs:
                        alerts["Backup_Alerts"].append({
                            "Vault": vault_name,
                            "FailedJobs": len(jobs),
                            "JobIDs": [job['BackupJobId'] for job in jobs]
                        })
            except Exception as e:
                logger.error(f"Error retrieving backup alerts: {str(e)}")

            # S3 Alerts
            try:
                buckets = clients['s3_client'].list_buckets().get('Buckets', [])
                for bucket in buckets:
                    bucket_name = bucket['Name']
                    try:
                        policy_status = clients['s3_client'].get_bucket_policy_status(Bucket=bucket_name)
                        if policy_status.get('PolicyStatus', {}).get('IsPublic'):
                            alerts["S3_Alerts"].append({
                                "Bucket": bucket_name,
                                "Alert": "Bucket is public"
                            })
                    except clients['s3_client'].exceptions.NoSuchBucketPolicy:
                        continue
                    except ClientError as e:
                        if e.response['Error']['Code'] == 'NoSuchBucketPolicy':
                            continue
                        logger.error(f"Error checking policy for bucket {bucket_name}: {str(e)}")
                    except Exception as e:
                        logger.error(f"Unhandled error for bucket {bucket_name}: {str(e)}")
            except Exception as e:
                logger.error(f"Error listing S3 buckets: {str(e)}")

            all_results.append(alerts)

        except Exception as e:
            logger.error(f"Skipping account {account_id} due to error: {str(e)}")

    result = {
        "db": "config",
        "collection": "client_data3",
        "method": "clientData",
        "body": all_results
    }
    print(result)

    invoke_api_gateway(result)

    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Data processed and sent to API Gateway"})
    }