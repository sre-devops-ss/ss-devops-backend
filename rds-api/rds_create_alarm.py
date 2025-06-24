import json
import os
from utils.cross_account import CrossAccountClient


def lambda_handler(event, context):
    body = event.get('body')
    if isinstance(body, str):
        body = json.loads(body)
    elif body is None:
        body = event

    account_id = body.get('account_id')
    region = body.get('region')
    role_name = body.get('role_name', os.environ.get('ROLE_NAME'))
    db_instance_id = body.get('db_instance_id')
    alarm_actions = body.get('alarm_actions', [])
    writer_only = body.get('writer_only', False)
    threshold_map = body.get('thresholds', {})  # Optional: {metric_name: threshold}

    RDS_METRICS = [
        {"name": "CPUUtilization", "namespace": "AWS/RDS", "description": "CPU Utilization"},
        {"name": "FreeableMemory", "namespace": "AWS/RDS", "description": "Freeable Memory"},
        {"name": "DatabaseConnections", "namespace": "AWS/RDS", "description": "DB Connections"},
        {"name": "ConnectionAttempts", "namespace": "AWS/RDS", "description": "Connection Attempts"},
        {"name": "Deadlocks", "namespace": "AWS/RDS", "description": "Deadlocks"},
        {"name": "Queries", "namespace": "AWS/RDS", "description": "Queries"},
        {"name": "FreeLocalStorage", "namespace": "AWS/RDS", "description": "Free Local Storage"},
        {"name": "Failover", "namespace": "AWS/RDS", "description": "Failover Notification"},
        {"name": "MasterUserPasswordReset", "namespace": "AWS/RDS", "description": "Master password reset notifications"},
        {"name": "SecurityGroupChanges", "namespace": "AWS/RDS", "description": "SG Modification alert"},
        {"name": "Reboot", "namespace": "AWS/RDS", "description": "Reboot notification"},
        {"name": "Scaling", "namespace": "AWS/RDS", "description": "Scaling Notification"}
    ]
    metrics = body.get('metrics') or RDS_METRICS
   

    cross_account_client = CrossAccountClient(account_id, f"arn:aws:iam::{account_id}:role/{role_name}", region)
    if not cross_account_client.assume_role():
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Failed to assume cross-account role"})
        }
    cloudwatch = cross_account_client.get_client('cloudwatch')

    results = []
    for metric in RDS_METRICS:
        alarm_name = f"{db_instance_id}-{metric['name'].lower()}"
        threshold = threshold_map.get(metric['name'], 80 if metric['name'] == 'CPUUtilization' else 1)
        dimensions = [{"Name": "DBInstanceIdentifier", "Value": db_instance_id}]
        if writer_only:
            dimensions.append({"Name": "Role", "Value": "WRITER"})
        try:
            cloudwatch.put_metric_alarm(
                AlarmName=alarm_name,
                MetricName=metric['name'],
                Namespace=metric['namespace'],
                Statistic='Average',
                Period=60,
                EvaluationPeriods=2,
                Threshold=threshold,
                ComparisonOperator='GreaterThanThreshold',
                AlarmActions=alarm_actions,
                Dimensions=dimensions
            )
            results.append({"alarm_name": alarm_name, "status": "created"})
        except Exception as e:
            results.append({"alarm_name": alarm_name, "status": "error", "error": str(e)})
    return {
        "statusCode": 200,
        "body": json.dumps({"results": results})
    } 