import boto3
import json
import urllib3
import logging

# Constants
ROLE_NAME = "devops-ui-cross-account"
SSM_PARAM = "/dashboard/client"
API_GATEWAY_URL = "https://xxxxxx.execute-api.ap-south-1.amazonaws.com/dashboard/dump"

# Init
http = urllib3.PoolManager()
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    try:
        accounts = get_account_list_from_ssm(event)
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": f"Failed to fetch accounts: {str(e)}"})
        }

    for account_name, account_id in accounts.items():
        print(account_name)
        account = account_name.strip().strip('"').strip(',').strip("'")
        print("account", account)

        account_ = account_name.strip().strip('"').strip(',').strip("'").split('-')[0]
        print(account_)

        try:
            session = assume_role(account_id)
            ec2_instances = get_ec2_instances(session)
            rds_instances = get_rds_instances(session)

            result_body = {
                "account_name": account_,
                "account_id": account_id,
                "ec2_instances": ec2_instances,
                "rds_instances": rds_instances
            }

            result = {
                "db": account_,
                "collection": "AWSResources1",
                "method": "insert_AWSResources",
                "body": result_body
            }

            print("DEBUG | Final result payload:", json.dumps(result)[:300])

            if result_body:
                invoke_api_gateway(result)

        except Exception as e:
            logger.error(f"Error for account {account_name}: {str(e)}")

    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Processing complete"})
    }

def get_account_list_from_ssm(event):
    """Get account list either from event or from SSM (supports JSON or raw text)."""
    if 'method' in event:
        print("Found 'method' in event — processing single account")
        account_id = event.get('account_id', '').strip('"')
        account_name = event.get('account_name', '').strip('"')

        if not account_id or not account_name:
            raise ValueError("Missing 'account_id' or 'account_name' in event.")
        
        return {account_name: account_id}
    
    # Else: fetch from SSM
    ssm = boto3.client("ssm")
    param = ssm.get_parameter(Name=SSM_PARAM, WithDecryption=True)
    raw_text = param['Parameter']['Value'].strip()

    accounts = {}

    # Try parsing as JSON first
    try:
        parsed_json = json.loads("{" + raw_text.strip(",") + "}")
        for acct_id, name in parsed_json.items():
            acct_id_clean = acct_id.strip().replace('"', '')
            name_clean = name.strip().replace('"', '')
            if acct_id_clean.isdigit():
                accounts[name_clean] = acct_id_clean
            else:
                logger.error(f"Invalid account ID: {acct_id_clean}")
    except json.JSONDecodeError:
        logger.warning("SSM content not valid JSON — falling back to raw parsing")

        for line in raw_text.splitlines():
            # Clean line
            line = line.strip().strip(',').strip()
            if ':' in line:
                acct_id, name = line.split(':', 1)
                acct_id = acct_id.strip().replace('"', '')
                name = name.strip().replace('"', '').replace(',', '')
                if acct_id.isdigit():
                    accounts[name] = acct_id
                else:
                    logger.error(f"Invalid account ID detected: '{acct_id}' in line '{line}'")


    return accounts



def assume_role(account_id):
    sts = boto3.client("sts")
    role_arn = f"arn:aws:iam::{account_id}:role/{ROLE_NAME}"

    response = sts.assume_role(
        RoleArn=role_arn,
        RoleSessionName="CrossAccountSession"
    )

    creds = response["Credentials"]
    return boto3.Session(
        aws_access_key_id=creds["AccessKeyId"],
        aws_secret_access_key=creds["SecretAccessKey"],
        aws_session_token=creds["SessionToken"]
    )

def get_ec2_instances(session):
    ec2_client = session.client("ec2")
    response = ec2_client.describe_instances()
    instances = []

    for reservation in response.get("Reservations", []):
        for instance in reservation.get("Instances", []):
            instance_name = None
            for tag in instance.get("Tags", []):
                if tag["Key"] == "Name":
                    instance_name = tag["Value"]
                    break
            if instance_name:
                instances.append(instance_name)
            else:
                instances.append(instance["InstanceId"])  # fallback if no Name tag
    return instances


def get_rds_instances(session):
    rds_client = session.client("rds")
    response = rds_client.describe_db_instances()
    instances = []

    for db in response.get("DBInstances", []):
        name = db.get("DBInstanceIdentifier")
        if name:
            instances.append(name)
    return instances

def invoke_api_gateway(data):
    """Invoke API Gateway URL asynchronously using urllib3."""
    try:
        headers = {"Content-Type": "application/json"}
        payload = json.dumps(data)

        print("DEBUG | Invoking API Gateway")
        print("DEBUG | Payload length:", len(payload))
        print("DEBUG | Payload preview:", payload[:300])

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
