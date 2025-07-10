import boto3
import json
import logging
import os
from utils.cross_account import CrossAccountClient

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    try:
        body = json.loads(event.get('body', '{}'))
        function_name = body['function_name']
        config = body.get('config', {})
        account_id = body['account_id']
        region = body.get('region', os.environ.get("AWS_REGION", "us-east-1"))

        # Assume role for cross-account access
        role_arn = f"arn:aws:iam::{account_id}:role/{os.environ['ROLE_NAME']}"
        client = CrossAccountClient(account_id, role_arn, region)
        client.assume_role()

        logs = client.get_client('logs')
        cloudwatch = client.get_client('cloudwatch')
        ssm = client.get_client('ssm')

        # Fetch SNS topic ARN from SSM
        sns_topic_arn = ssm.get_parameter(
            Name="/devops-backend/snstopic/arn",
            WithDecryption=False
        )["Parameter"]["Value"]

        alarm_actions = config.get('alarm_actions', [])
        if sns_topic_arn not in alarm_actions:
            alarm_actions.append(sns_topic_arn)

        # Define metric filter
        log_group = f"/aws/lambda/{function_name}"
        metric_namespace = "LambdaLogs"
        metric_name = f"{function_name}-log-errors"

        logs.put_metric_filter(
            logGroupName=log_group,
            filterName=f"{function_name}-log-error-filter",
            filterPattern='?"ERROR"',
            metricTransformations=[{
                'metricName': metric_name,
                'metricNamespace': metric_namespace,
                'metricValue': '1'
            }]
        )

        # Create CloudWatch alarm on the filtered metric
        cloudwatch.put_metric_alarm(
            AlarmName=f"{function_name}-log-error-alarm",
            MetricName=metric_name,
            Namespace=metric_namespace,
            Statistic="Sum",
            Period=config.get('period', 60),
            EvaluationPeriods=config.get('evaluation_periods', 1),
            Threshold=config.get('log_error_threshold', 1),
            ComparisonOperator="GreaterThanThreshold",
            AlarmDescription="Errors found in Lambda logs",
            AlarmActions=alarm_actions
        )

        logger.info(f"Log error alarm created for: {function_name}")
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Log error alarm created'})
        }

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
