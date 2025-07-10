import boto3, json, logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)
cloudwatch = boto3.client("cloudwatch")
headers= {
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Origin': f"*",
    'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
}

def lambda_handler(event, context):
    try:
        body = json.loads(event.get("body", "{}"))
        lb = body["load_balancer_name"]
        tg = body["target_group_name"]
        cfg = body["config"]
        dimensions = [{"Name": "TargetGroup", "Value": tg}, {"Name": "LoadBalancer", "Value": lb}]

        cloudwatch.put_metric_alarm(
            AlarmName=f"{tg}-5xx-errors",
            Namespace="AWS/ApplicationELB",
            MetricName="HTTPCode_Target_5XX_Count",
            Statistic="Sum",
            Period=cfg["period"],
            EvaluationPeriods=cfg["evaluation_periods"],
            Threshold=cfg["threshold"],
            ComparisonOperator="GreaterThanThreshold",
            AlarmDescription="High 5XX errors from targets",
            Dimensions=dimensions,
            AlarmActions=cfg["alarm_actions"]
        )

        return {"statusCode": 200, "headers": headers, "body": json.dumps({"message": "5XX error alarm created"})}
    except Exception as e:
        logger.error(str(e))
        return {"statusCode": 500, "headers": headers, "body": json.dumps({"error": str(e)})}
