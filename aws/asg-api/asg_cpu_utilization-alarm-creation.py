import boto3
import json
import logging
import os

headers= {
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Origin': f"*",
    'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
} 

logger = logging.getLogger()
logger.setLevel(logging.INFO)
from utils.cross_account import CrossAccountClient
cloudwatch = boto3.client("cloudwatch")

def create_cpu_alarm(instance_id, config, alarm_actions):
    dimensions = [{'Name': 'InstanceId', 'Value': instance_id}]
    cloudwatch.put_metric_alarm(
        AlarmName=f"{instance_id}-cpu-utilization",
        MetricName="CPUUtilization",
        Namespace="AWS/EC2",
        Statistic="Average",
        Period=config['period'],
        EvaluationPeriods=config['evaluation_periods'],
        Threshold=config['cpu_threshold'],
        ComparisonOperator="GreaterThanThreshold",
        AlarmDescription="High CPU utilization",
        Dimensions=dimensions,
        AlarmActions=alarm_actions
    )
    logger.info(f"CPU alarm created for instance: {instance_id}")


def lambda_handler(event, context):
    try:
        body = json.loads(event.get('body', '{}'))
        instance_ids = body.get('instance_ids', [])
        account_id = body.get("account_id")
        region = body.get("region", os.environ.get("AWS_REGION"))
        config = {
            'cpu_threshold': body.get('cpu_threshold', 80),
            'period': body.get('period', 60),
            'evaluation_periods': body.get('evaluation_periods', 1),
            'alarm_actions': body.get('alarm_actions', [])
        }
        role_arn = f"arn:aws:iam::{account_id}:role/{os.environ['ROLE_NAME']}"
        client = CrossAccountClient(account_id, role_arn, region)
        client.assume_role()

        ssm = client.get_client("ssm")
        sns_topic_arn = ssm.get_parameter(
            Name="/devops-backend/snstopic/arn",
            WithDecryption=False
        )["Parameter"]["Value"]

        if sns_topic_arn not in config["alarm_actions"]:
            config["alarm_actions"].append(sns_topic_arn)

        cloudwatch = client.get_client("cloudwatch")

        for instance_id in instance_ids:
            create_cpu_alarm(instance_id, config, alarm_actions)

        return {'statusCode': 200, 'headers': headers, 'body': json.dumps({'message': 'CPU alarms created'})}

    except Exception as e:
        logger.error(str(e))
        return {'statusCode': 500, 'headers': headers, 'body': json.dumps({'error': str(e)})}
