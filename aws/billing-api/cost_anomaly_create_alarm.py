import boto3
import json
import os
from utils.cross_account import CrossAccountClient

def create_bandwidth_alarm(cloudwatch, instance_id, threshold, alarm_actions):
    cloudwatch.put_metric_alarm(
        AlarmName=f"{instance_id}-network-out",
        MetricName="NetworkOut",
        Namespace="AWS/EC2",
        Statistic="Average",
        Period=300,
        EvaluationPeriods=1,
        Threshold=threshold,
        ComparisonOperator="GreaterThanThreshold",
        Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
        AlarmActions=alarm_actions,
        AlarmDescription="High outbound bandwidth usage"
    )

def lambda_handler(event, context):
    body = json.loads(event.get("body", "{}"))
    instance_ids = body.get("instance_ids", [])
    account_id = body['account_id']
    region = body.get("region", os.environ.get("AWS_REGION"))
    threshold = body.get("threshold", 50000000)  # ~50 MB

    role_arn = f"arn:aws:iam::{account_id}:role/{os.environ['ROLE_NAME']}"
    client = CrossAccountClient(account_id, role_arn, region)
    client.assume_role()

    ssm = client.get_client("ssm")
    sns_topic_arn = ssm.get_parameter(
        Name="/devops-backend/snstopic/arn",
        WithDecryption=False
    )["Parameter"]["Value"]

    alarm_actions = [sns_topic_arn]

    cloudwatch = client.get_client("cloudwatch")

    for instance_id in instance_ids:
        create_bandwidth_alarm(cloudwatch, instance_id, threshold, alarm_actions)

    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Bandwidth alarms created"})
    }
