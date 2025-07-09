import boto3, json, logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)
cloudwatch = boto3.client("cloudwatch")

def lambda_handler(event, context):
    try:
        body = json.loads(event.get("body", "{}"))
        lb = body["load_balancer_name"]
        tg = body["target_group_name"]
        cfg = body["config"]
        dimensions = [{"Name": "TargetGroup", "Value": tg}, {"Name": "LoadBalancer", "Value": lb}]

        cloudwatch.put_metric_alarm(
            AlarmName=f"{tg}-unhealthy-hosts",
            Namespace="AWS/ApplicationELB",
            MetricName="UnHealthyHostCount",
            Statistic="Average",
            Period=cfg["period"],
            EvaluationPeriods=cfg["evaluation_periods"],
            Threshold=cfg["threshold"],
            ComparisonOperator="GreaterThanThreshold",
            AlarmDescription="Too many unhealthy hosts",
            Dimensions=dimensions,
            AlarmActions=cfg["alarm_actions"]
        )

        return {"statusCode": 200, "body": json.dumps({"message": "Unhealthy host alarm created"})}
    except Exception as e:
        logger.error(str(e))
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
