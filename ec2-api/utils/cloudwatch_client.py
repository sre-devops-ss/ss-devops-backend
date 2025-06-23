# cloudwatch_monitoring_handler.py
import json
import os
from datetime import datetime, timedelta
from utils.cross_account import CrossAccountClient

class CloudWatchMonitor:
    def __init__(self, account_id, region, role_name):
        self.account_id = account_id
        self.region = region
        self.role_arn = f"arn:aws:iam::{account_id}:role/{role_name}"
        self.cross_account = CrossAccountClient(account_id, self.role_arn, region)
        if not self.cross_account.assume_role():
            raise Exception("Failed to assume cross-account role")
        self.cloudwatch = self.cross_account.get_client('cloudwatch')

    def parse_time(self, ts, fallback):
        try:
            return datetime.strptime(ts, '%Y-%m-%dT%H:%M:%S')
        except:
            return fallback

    def get_metrics(self, instance_id, metric_name, namespace='CWAgent', stat='Average',
                    period=60, start_time=None, end_time=None, next_token=None):

        now = datetime.utcnow()
        start_time = self.parse_time(start_time, now - timedelta(minutes=10))
        end_time = self.parse_time(end_time, now)

        queries = [{
            'Id': 'm1',
            'MetricStat': {
                'Metric': {
                    'Namespace': namespace,
                    'MetricName': metric_name,
                    'Dimensions': [
                        {'Name': 'InstanceId', 'Value': instance_id}
                    ]
                },
                'Period': period,
                'Stat': stat
            },
            'ReturnData': True
        }]

        kwargs = {
            'MetricDataQueries': queries,
            'StartTime': start_time,
            'EndTime': end_time
        }

        if next_token:
            kwargs['NextToken'] = next_token

        response = self.cloudwatch.get_metric_data(**kwargs)

        return {
            'metric': response['MetricDataResults'][0] if response['MetricDataResults'] else {},
            'next_token': response.get('NextToken')
        }

    def create_alarm(self, alarm_name, instance_id, metric_name, threshold=80, evaluation_periods=2,
                     period=60, namespace='CWAgent', stat='Average', comparison_operator='GreaterThanThreshold',
                     alarm_actions=[]):

        dimensions = [{'Name': 'InstanceId', 'Value': instance_id}]
        self.cloudwatch.put_metric_alarm(
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

        response = self.cloudwatch.describe_alarms(AlarmNames=[alarm_name])
        return response['MetricAlarms'][0]

    def get_alarm(self, alarm_name, start_time=None, end_time=None, next_token=None):
        try:
            kwargs = {'AlarmNames': [alarm_name]}
            if next_token:
                kwargs['NextToken'] = next_token

            response = self.cloudwatch.describe_alarms(**kwargs)
            if response['MetricAlarms']:
                alarm = response['MetricAlarms'][0]
                alarm_metric_name = alarm['MetricName']
                instance_id = next((d['Value'] for d in alarm['Dimensions'] if d['Name'] == 'InstanceId'), None)

                if instance_id:
                    metrics_data = self.get_metrics(
                        instance_id=instance_id,
                        metric_names=[alarm_metric_name],
                        namespace=alarm['Namespace'],
                        stat=alarm.get('Statistic', 'Average'),
                        period=alarm.get('Period', 60),
                        start_time=start_time,
                        end_time=end_time
                    )
                    alarm['metrics'] = metrics_data

                return {
                    'alarm': alarm,
                    'next_token': response.get('NextToken')
                }
        except:
            pass
        return None


# Example API call (GET or POST)
# POST body:
# {
#   "account_id": "123456789012",
#   "alarm_name": "my-instance-cpu-alarm",
#   "instance_id": "i-0abc123456def7890",
#   "metric_name": "CPUUtilization",
#   "start_time": "2025-06-20T00:00:00",
#   "end_time": "2025-06-22T23:59:59",
#   "next_token": null
# }
