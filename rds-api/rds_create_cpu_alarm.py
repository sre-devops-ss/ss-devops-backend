import json
import os
from utils.cross_account import CrossAccountClient

# Default fallback values
CPU_THRESHOLD = int(os.getenv('CPU_THRESHOLD', '80'))
EVALUATION_PERIODS = int(os.getenv('EVALUATION_PERIODS', '2'))
PERIOD = int(os.getenv('PERIOD', '300'))
DEFAULT_REGION = os.getenv('REGION', 'us-east-1')
DEFAULT_ROLE_NAME = os.getenv('ROLE_NAME', 'CrossAccountMonitoringRole')

def lambda_handler(event, context):
    try:
        print("Event:", json.dumps(event))
        body = json.loads(event.get('body', '{}'))

        account_id = body.get('account_id')
        region = body.get('region', DEFAULT_REGION)
        role_name = body.get('role_name', DEFAULT_ROLE_NAME)
        db_identifier = body.get('db_identifier')
        external_id = body.get('external_id')
        alarm_actions = body.get('alarm_actions', [])

        # Optional overrides
        threshold = int(body.get('cpu_threshold', CPU_THRESHOLD))
        evaluation_periods = int(body.get('evaluation_periods', EVALUATION_PERIODS))
        period = int(body.get('period', PERIOD))

        if not all([account_id, role_name, db_identifier]):
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Missing required fields',
                    'message': 'account_id, role_name, and db_identifier are required'
                })
            }

        # Cross-account role assumption
        role_arn = f"arn:aws:iam::{account_id}:role/{role_name}"
        cross_account = CrossAccountClient(account_id, role_arn, region, external_id)
        if not cross_account.assume_role():
            return {
                'statusCode': 500,
                'body': json.dumps({'error': 'Failed to assume cross-account role'})
            }

        cloudwatch = cross_account.get_client('cloudwatch')

        alarm_name = f"{db_identifier}-CPUUtilization"
        namespace = 'AWS/RDS'
        metric_name = 'CPUUtilization'
        stat = 'Average'
        comparison_operator = 'GreaterThanThreshold'
        dimensions = [{'Name': 'DBInstanceIdentifier', 'Value': db_identifier}]

       
        cloudwatch.put_metric_alarm(
            AlarmName=alarm_name,
            MetricName=metric_name,
            Namespace=namespace,
            Statistic=stat,
            Period=period,
            EvaluationPeriods=evaluation_periods,
            Threshold=threshold,
            ComparisonOperator=comparison_operator,
            AlarmActions=alarm_actions,
            Dimensions=dimensions
        )

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Alarm created successfully',
                'alarm_name': alarm_name,
                'db_identifier': db_identifier,
                'account_id': account_id,
                'region': region
            })
        }

    except Exception as e:
        print("Error:", str(e))
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
