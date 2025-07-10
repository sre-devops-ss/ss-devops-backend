import json
import os
import logging
from utils.cross_account import CrossAccountClient

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

        role_arn = f"arn:aws:iam::{account_id}:role/{os.environ['ROLE_NAME']}"
        client = CrossAccountClient(account_id, role_arn, region)
        client.assume_role()

        cloudwatch = client.get_client("cloudwatch")
        ssm = client.get_client("ssm")

        sns_topic_arn = ssm.get_parameter(
            Name="/devops-backend/snstopic/arn",
            WithDecryption=False
        )["Parameter"]["Value"]

        threshold = config.get("latency_threshold", 1000)
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
            AlarmName=f"{api_name}-{stage}-latency",
            MetricName="Latency",
            Namespace="AWS/ApiGateway",
            Statistic="Average",
            Dimensions=dimensions,
            Period=period,
            EvaluationPeriods=evaluation_periods,
            Threshold=threshold,
            ComparisonOperator="GreaterThanThreshold",
            Unit="Milliseconds",
            AlarmDescription="API latency too high",
            AlarmActions=alarm_actions
        )

        return {"statusCode": 200, "headers": headers, "body": json.dumps("Latency alarm created")}

    except Exception as e:
        logger.error(f"Error creating latency alarm: {str(e)}")
        return {"statusCode": 500, "headers": headers, "body": json.dumps({"error": str(e)})}
