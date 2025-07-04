import json
import os
from utils.cross_account import CrossAccountClient

class FreeableMemoryAlarmCreator:
    def __init__(self, account_id, region, role_name, db_identifier, cluster_identifier, external_id, alarm_actions, threshold, evaluation_periods, period):
        self.account_id = account_id
        self.region = region
        self.role_name = role_name
        self.db_identifier = db_identifier
        self.cluster_identifier = cluster_identifier
        self.external_id = external_id
        self.alarm_actions = alarm_actions
        self.threshold = threshold
        self.evaluation_periods = evaluation_periods
        self.period = period

    def validate(self):
        if not self.account_id or not self.role_name or (not self.db_identifier and not self.cluster_identifier):
            return False, {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Missing required fields',
                    'message': 'account_id, role_name, and db_identifier or cluster_identifier are required'
                })
            }
        return True, None

    def create_alarm(self):
        role_arn = f"arn:aws:iam::{self.account_id}:role/{self.role_name}"
        cross_account = CrossAccountClient(self.account_id, role_arn, self.region, self.external_id)
        if not cross_account.assume_role():
            return {
                'statusCode': 500,
                'body': json.dumps({'error': 'Failed to assume cross-account role'})
            }

        cloudwatch = cross_account.get_client('cloudwatch')

        if self.db_identifier:
            alarm_name = f"{self.db_identifier}-FreeableMemory"
            dimensions = [{'Name': 'DBInstanceIdentifier', 'Value': self.db_identifier}]
        else:
            alarm_name = f"{self.cluster_identifier}-FreeableMemory"
            dimensions = [{'Name': 'DBClusterIdentifier', 'Value': self.cluster_identifier}]

        namespace = 'AWS/RDS'
        metric_name = 'FreeableMemory'
        stat = 'Average'
        comparison_operator = 'LessThanThreshold'

        cloudwatch.put_metric_alarm(
            AlarmName=alarm_name,
            MetricName=metric_name,
            Namespace=namespace,
            Statistic=stat,
            Period=self.period,
            EvaluationPeriods=self.evaluation_periods,
            Threshold=self.threshold,
            ComparisonOperator=comparison_operator,
            AlarmActions=self.alarm_actions,
            Dimensions=dimensions,
            Unit='Bytes'
        )

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'FreeableMemory alarm created successfully',
                'alarm_name': alarm_name,
                'identifier': self.db_identifier or self.cluster_identifier,
                'account_id': self.account_id,
                'region': self.region
            })
        }

def lambda_handler(event, context):
    try:
        print("Event:", json.dumps(event))
        body = json.loads(event.get('body', '{}'))
        account_id = body.get('account_id')
        region = body.get('region', os.getenv('REGION', 'us-east-1'))
        role_name = body.get('role_name', os.getenv('ROLE_NAME', 'CrossAccountMonitoringRole'))
        db_identifier = body.get('db_identifier')
        cluster_identifier = body.get('cluster_identifier')
        external_id = body.get('external_id')
        alarm_actions = body.get('alarm_actions', [])
        threshold = int(body.get('freeable_mem_threshold', 500000000))  # Default: 500MB in bytes
        evaluation_periods = int(body.get('evaluation_periods', 2))
        period = int(body.get('period', 300))
        alarm_creator = FreeableMemoryAlarmCreator(
            account_id, region, role_name, db_identifier, cluster_identifier,
            external_id, alarm_actions, threshold, evaluation_periods, period
        )
        valid, error_response = alarm_creator.validate()
        if not valid:
            return error_response
        return alarm_creator.create_alarm()
    except Exception as e:
        print("Error:", str(e))
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
