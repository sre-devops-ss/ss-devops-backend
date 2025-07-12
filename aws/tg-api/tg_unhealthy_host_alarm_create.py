import boto3, json, logging
from utils.authenticate_user_role import UserAuthenticator


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

        authenticator = UserAuthenticator()
        auth_result = authenticator.authenticate_user_account(event)
        authenticator.close_connection()
        
        if auth_result["statusCode"] != 200:
            return {
                "statusCode": 403,
                "headers": headers,
                "body": json.dumps("user not authorized")
            }

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

        return {"statusCode": 200, "headers": headers, "body": json.dumps({"message": "Unhealthy host alarm created"})}
    except Exception as e:
        logger.error(str(e))
        return {"statusCode": 500, "headers": headers, "body": json.dumps({"error": str(e)})}
