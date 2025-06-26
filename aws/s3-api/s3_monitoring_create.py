# s3_alarm_creator.py

import json
import os
import boto3
import logging
from utils.cross_account import CrossAccountClient

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class S3AlarmCreator:
    def __init__(self, account_client):
        self.s3 = account_client.get_client("s3")
        self.cloudwatch = account_client.get_client("cloudwatch")

    def create_bucket_size_alarm(self, bucket_name, config=None):
        try:
            self.s3.head_bucket(Bucket=bucket_name)

            alarm_config = {
                'bucket_size_threshold': 1_000_000_000,  # 1 GB
                'evaluation_periods': 1,
                'period': 86400,  # daily
                'alarm_actions': [],
                **(config or {})
            }

            alarm_name = f"{bucket_name}-size-alarm"
            self.cloudwatch.put_metric_alarm(
                AlarmName=alarm_name,
                MetricName='BucketSizeBytes',
                Namespace='AWS/S3',
                Statistic='Average',
                Period=alarm_config['period'],
                EvaluationPeriods=alarm_config['evaluation_periods'],
                Threshold=alarm_config['bucket_size_threshold'],
                ComparisonOperator='GreaterThanThreshold',
                Dimensions=[
                    {'Name': 'BucketName', 'Value': bucket_name},
                    {'Name': 'StorageType', 'Value': 'StandardStorage'}
                ],
                AlarmDescription=f"Alarm for {bucket_name} size exceeding threshold",
                AlarmActions=alarm_config['alarm_actions']
            )

            return alarm_name

        except Exception as e:
            logger.error(f"Error creating alarm: {str(e)}")
            raise


def lambda_handler(event, context):
    try:
        body = json.loads(event.get("body", "{}"))
        bucket_name = body.get("bucket_name")
        account_id = body.get("account_id")
        region = body.get("region") or os.environ.get("REGION")
        config = body.get("config", {})

        if not bucket_name or not account_id:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'bucket_name and account_id are required'})
            }

        role_name = os.environ.get("ROLE_NAME")
        role_arn = f"arn:aws:iam::{account_id}:role/{role_name}"

        client = CrossAccountClient(account_id, role_arn, region)
        client.assume_role()

        monitor = S3AlarmCreator(client)
        alarm_name = monitor.create_bucket_size_alarm(bucket_name, config)

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'S3 bucket size alarm created',
                'alarm_name': alarm_name
            })
        }

    except Exception as e:
        logger.error(f"Lambda error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
