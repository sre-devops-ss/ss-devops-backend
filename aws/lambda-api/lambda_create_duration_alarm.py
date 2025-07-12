import boto3
import json
import logging
import os
from utils.cross_account import CrossAccountClient
from utils.authenticate_user_role import UserAuthenticator


logger = logging.getLogger()
logger.setLevel(logging.INFO)

headers= {
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Origin': f"*",
    'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
}

def lambda_handler(event, context):
    try:
        body = json.loads(event.get('body', '{}'))
        function_name = body['function_name']
        config = body.get('config', {})
        account_id = body['account_id']
        region = body.get("region", os.environ.get("AWS_REGION", "us-east-1"))

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

        ssm = client.get_client("ssm")
        sns_topic_arn = ssm.get_parameter(
            Name="/devops-backend/snstopic/arn",
            WithDecryption=False
        )["Parameter"]["Value"]

        # Prepare alarm actions
        alarm_actions = config.get('alarm_actions', [])
        if sns_topic_arn not in alarm_actions:
            alarm_actions.append(sns_topic_arn)
        # Get SNS topic ARN from SSM

        # Get CloudWatch client
        cloudwatch = client.get_client("cloudwatch")

        alarm_name = f"{function_name}-duration-alarm"

        cloudwatch.put_metric_alarm(
            AlarmName=alarm_name,
            MetricName="Duration",
            Namespace="AWS/Lambda",
            Statistic="Average",
            Period=config.get('period', 60),
            EvaluationPeriods=config.get('evaluation_periods', 1),
            Threshold=config.get('duration_threshold', 3000),  # in milliseconds
            ComparisonOperator="GreaterThanThreshold",
            AlarmDescription="Lambda execution duration is too high",
            Dimensions=[{"Name": "FunctionName", "Value": function_name}],
            AlarmActions=alarm_actions
        )

        logger.info(f"Duration alarm created for: {function_name}")
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({'message': f'Duration alarm created for {function_name}'})
        }

    except Exception as e:
        logger.error(f"Error creating alarm: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': str(e)})
        }
