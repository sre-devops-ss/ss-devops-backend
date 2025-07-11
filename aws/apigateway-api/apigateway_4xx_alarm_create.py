import json
import os
import logging
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
        body = json.loads(event.get("body", "{}"))
        api_name = body["api_name"]
        stage = body["stage"]
        account_id = body["account_id"]
        region = body.get("region") or os.environ["REGION"]
        config = body.get("config", {})

        # Authenticate user
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

        cloudwatch = client.get_client("cloudwatch")
        ssm = client.get_client("ssm")

        sns_topic_arn = ssm.get_parameter(
            Name="/devops-backend/snstopic/arn",
            WithDecryption=False
        )["Parameter"]["Value"]

        threshold = config.get("4xx_threshold", 10)
        period = config.get("period", 60)
        evaluation_periods = config.get("evaluation_periods", 1)
        alarm_actions = config.get("alarm_actions", [])
        if sns_topic_arn not in alarm_actions:
            alarm_actions.append(sns_topic_arn)

        dimensions = [
            {"Name": "ApiName", "Value": api_name},
            {"Name": "Stage", "Value": stage}
        ]

        cloudwatch.put_metric_alarm(
            AlarmName=f"{api_name}-{stage}-4xx-errors",
            MetricName="4XXError",
            Namespace="AWS/ApiGateway",
            Statistic="Sum",
            Dimensions=dimensions,
            Period=period,
            EvaluationPeriods=evaluation_periods,
            Threshold=threshold,
            ComparisonOperator="GreaterThanThreshold",
            AlarmDescription="Too many 4XX errors",
            AlarmActions=alarm_actions
        )

        return {
            "statusCode": 200,
            "headers": headers,
            "body": json.dumps("4XX error alarm created")}

    except Exception as e:
        logger.error(f"Error creating 4XX alarm: {str(e)}")
        return {"statusCode": 500, "headers": headers, "body": json.dumps({"error": str(e)})}
