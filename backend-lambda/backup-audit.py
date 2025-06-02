import boto3
import json
import urllib3
import logging
from datetime import datetime, timedelta

# Constants
ROLE_NAME = "devops-ui-cross-account"
SSM_PARAM = "/dashboard/client"  # SSM parameter key
API_GATEWAY_URL = "https://xxxxxxxx.execute-api.ap-south-1.amazonaws.com/dashboard/dump"  # Replace with your API URL

# Setup
http = urllib3.PoolManager()
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    today = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    results = []

    try:
        accounts = get_account_list_from_ssm()
    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": f"Failed to fetch accounts from SSM: {str(e)}"})}

    for account_id, account_name in accounts.items():
        account_id = account_id.strip('"')
        account_name = account_name.strip('"')
        account_name = account_name.split("-")[0]
        
        try:
            session = assume_role(account_id)
            regions = get_activated_regions(session)

            for region in regions:
                # Fetch backup data for each region
                backup_data = handle_backup_plans(session, account_id, region, account_name, today)
                if backup_data:
                    # Prepare final structure
                    final_payload = {
                        "db": account_name,
                        "collection": "backup2",
                        "method": "insert_backup",
                        "body": backup_data
                    }
                    # Invoke API Gateway
                    # invoke_api_gateway(final_payload)
                    results.append(final_payload)
                    print("final_payload", final_payload)

        except Exception as e:
            print(f"Skipping account {account_name} due to error: {str(e)}")
            continue  # Skip this account and do not add any error to results

    return {
        "statusCode": 200,
        "body": json.dumps({"backup_status": results}, indent=2)
    }

def get_account_list_from_ssm():
    """Fetch account list from SSM Parameter Store."""
    ssm = boto3.client("ssm")
    param = ssm.get_parameter(Name=SSM_PARAM, WithDecryption=True)
    raw_text = param['Parameter']['Value']
    
    accounts = {}
    for line in raw_text.strip().split('\n'):
        if ':' in line:
            name, account_id = line.strip().split(':')
            accounts[name] = account_id
    return accounts

def assume_role(account_id):
    """Assumes the cross-account role and returns a boto3 session."""
    sts_client = boto3.client('sts')
    role_arn = f"arn:aws:iam::{account_id}:role/{ROLE_NAME}"
    print(f"Assuming role: {role_arn}")
    response = sts_client.assume_role(
        RoleArn=role_arn,
        RoleSessionName="CrossAccountSession"
    )

    creds = response['Credentials']
    session = boto3.Session(
        aws_access_key_id=creds['AccessKeyId'],
        aws_secret_access_key=creds['SecretAccessKey'],
        aws_session_token=creds['SessionToken']
    )
    return session

def get_activated_regions(session):
    """Returns enabled AWS regions for the session."""
    ec2 = session.client("ec2")
    regions = ec2.describe_regions(AllRegions=True)['Regions']
    return [r['RegionName'] for r in regions if r['OptInStatus'] in ['opted-in', 'opt-in-not-required']]

def parse_cron_expression(cron_expression):
    parts = cron_expression.replace("cron(", "").replace(")", "").split()
    
    try:
        minute = int(parts[0]) if '/' not in parts[0] else parts[0]
    except ValueError:
        minute = "Unknown"
    
    try:
        hour = int(parts[1]) if '/' not in parts[1] else parts[1]
    except ValueError:
        hour = "Unknown"

    frequency = "Daily" if parts[2] == "*" else "Custom"

    if isinstance(hour, int) and isinstance(minute, int):
        utc = datetime(1970, 1, 1, hour=hour, minute=minute)
        ist = utc + timedelta(hours=5, minutes=30)
        time_ist = ist.strftime("%H:%M:%S (UTC+05:30)")
    else:
        time_ist = f"Hour: {hour}, Minute: {minute} (Custom Schedule)"

    return frequency, time_ist

def handle_backup_plans(session, account_id, region, account_name, timestamp):
    """Fetches backup plans and builds structured status."""
    backup_client = session.client('backup', region_name=region)
    results = []

    try:
        plans = backup_client.list_backup_plans().get('BackupPlansList', [])
        if not plans:
            print(f"No backup plans found for account {account_name} in region {region}.")
            return []
    except Exception as e:
        print(f"Error fetching backup plans for account {account_name} in region {region}: {str(e)}")
        return []

    for plan in plans:
        plan_id = plan.get('BackupPlanId')
        plan_name = plan.get('BackupPlanName')
        if not plan_id or not plan_name:
            print(f"Skipping invalid plan with missing ID or name.")
            continue

        try:
            plan_data = backup_client.get_backup_plan(BackupPlanId=plan_id)
            rules = plan_data.get('BackupPlan', {}).get('Rules', [])
            if not rules:
                print(f"No rules found for Backup Plan {plan_name}. Skipping.")
                continue
        except Exception as e:
            print(f"Error fetching backup plan details for {plan_name}: {str(e)}")
            continue

        for rule in rules:
            schedule = rule.get('ScheduleExpression', 'No Schedule Expression')
            lifecycle = rule.get('Lifecycle', {})
            retention_days = lifecycle.get('DeleteAfterDays', 'No Retention')
            freq, time = parse_cron_expression(schedule) if schedule != 'No Schedule Expression' else ("No Schedule", "No Time")
            vault = rule.get('TargetBackupVaultName', 'Unknown')

            # Collect unique resource ARNs from vault
            try:
                points = backup_client.list_recovery_points_by_backup_vault(
                    BackupVaultName=vault
                ).get('RecoveryPoints', [])
                if not points:
                    print(f"No recovery points found for vault {vault} in plan {plan_name}.")
                    continue

                resource_arns = set()
                for point in points:
                    arn = point.get('ResourceArn')
                    if arn:
                        resource_arns.add(arn)

            except Exception as e:
                print(f"Error retrieving recovery points from vault {vault}: {str(e)}")
                continue

            # For each resource ARN, get recovery points by resource
            for resource_arn in resource_arns:
                try:
                    resource_points = backup_client.list_recovery_points_by_resource(
                        ResourceArn=resource_arn,
                        MaxResults=50
                    ).get('RecoveryPoints', [])

                    for rp in resource_points:
                        completed = rp.get('Status') == 'COMPLETED'
                        results.append({
                            "RecoveryPointArn": rp.get('RecoveryPointArn', 'N/A'),
                            "CreationDate": str(rp.get('CreationDate', '')),
                            "Status": rp.get('Status', 'Unknown'),
                            "BackupSizeBytes": rp.get('BackupSizeInBytes', 0),
                            "BackupVaultName": vault,
                            "ResourceName": rp.get('ResourceName', 'Unknown'),
                            "VaultType": rp.get('ResourceType', 'Unknown'),  # e.g., AWS::RDS::DBInstance
                            "timestamp": timestamp,
                            "AccountName": account_name,
                            "AccountId": account_id,
                            "Region": region,
                            "Rule": rule.get('RuleName'),
                            "RetentionDays": retention_days,
                            "Schedule": freq,
                            "BackupTimeIST": time,
                            "RecoveryPointsStatus": "Completed" if completed else "Not Completed"
                        })

                        results.append(result)

                except Exception as e:
                    print(f"Error fetching recovery points for resource {resource_arn}: {str(e)}")
                    continue

    return results

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
