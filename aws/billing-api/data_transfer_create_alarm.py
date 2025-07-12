import boto3
import json
import os
from datetime import date
from utils.cross_account import CrossAccountClient
from utils.authenticate_user_role import UserAuthenticator


headers= {
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Origin': f"*",
    'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
}

def lambda_handler(event, context):
    body = json.loads(event.get("body", "{}"))
    account_id = body["account_id"]
    region = body.get("region", os.environ.get("AWS_REGION", "us-east-1"))
    threshold = body.get("threshold", 10.0)
    send_alert = body.get("send_alert", True)

    authenticator = UserAuthenticator()
    auth_result = authenticator.authenticate_user_account(event)
    authenticator.close_connection()
    
    if auth_result["statusCode"] != 200:
        return {
            "statusCode": 403,
            "headers": headers,
            "body": json.dumps("user not authorized")
        }

    role_arn = f"arn:aws:iam::{account_id}:role/{os.environ['ROLE_NAME']}"
    client = CrossAccountClient(account_id, role_arn, region)
    client.assume_role()

    ce = client.get_client('ce')
    cloudwatch = client.get_client('cloudwatch')
    ssm = client.get_client('ssm')

    today = date.today()
    start = today.replace(day=1).isoformat()
    end = today.isoformat()

    result = ce.get_cost_and_usage(
        TimePeriod={'Start': start, 'End': end},
        Granularity='MONTHLY',
        Metrics=['UnblendedCost'],
        Filter={
            'Dimensions': {
                'Key': 'SERVICE',
                'Values': ['Amazon Elastic Compute Cloud - Data Transfer']
            }
        }
    )

    amount = float(result['ResultsByTime'][0]['Total']['UnblendedCost']['Amount'])
    print(f"Data Transfer Cost So Far: ${amount}")

    cloudwatch.put_metric_data(
        Namespace='Billing/DataTransfer',
        MetricData=[
            {
                'MetricName': 'BandwidthCost',
                'Value': amount,
                'Unit': 'None'
            }
        ]
    )

    if send_alert and amount > threshold:
        sns = client.get_client('sns')
        sns_topic_arn = ssm.get_parameter(
            Name="/devops-backend/snstopic/arn",
            WithDecryption=False
        )["Parameter"]["Value"]

        sns.publish(
            TopicArn=sns_topic_arn,
            Subject="High Bandwidth Cost Alert",
            Message=f"Bandwidth cost for this month has reached ${amount}, exceeding the threshold of ${threshold}."
        )

    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps(f"Data transfer cost this month: ${amount}")
    }
