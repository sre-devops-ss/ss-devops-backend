import json
import os
import logging
from utils.cross_account import CrossAccountClient

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    try:
        body = json.loads(event.get("body", "{}"))
        api_name = body["api_name"]
        stage = body["stage"]
        account_id = body["account_id"]
        region = body.get("region") or os.environ["REGION"]
        config = body.get("config", {})

        role_arn = f"arn:aws:iam::{account_id}:role/{os.environ['ROLE_NAME']}"
        client = CrossAccountClient(account_id, role_arn, region)
        client.assume_role()

        cloudwatch = client.get_client("cloudwatch")
        ssm = client.get_client("ssm")

        sns_topic_arn = ssm.get_parameter(
            Name="/devops-backend/snstopic/arn",
            WithDecryption=False
        )["Parameter"]["Value"]

        threshold = config.get("5xx_threshold", 1)
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
            AlarmName=f"{api_name}-{stage}-5xx-errors",
            MetricName="5XXError",
            Namespace="AWS/ApiGateway",
            Statistic="Sum",
            Dimensions=dimensions,
            Period=period,
            EvaluationPeriods=evaluation_periods,
            Threshold=threshold,
            ComparisonOperator="GreaterThanThreshold",
             AlarmDescription="Too many 5XX errors",
            AlarmActions=alarm_actions
        )

        return {"statusCode": 200, "body": json.dumps("5XX error alarm created")}

    except Exception as e:
        logger.error(f"Error creating 5XX alarm: {str(e)}")
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
