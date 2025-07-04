import boto3
import json
import logging
from datetime import datetime, timedelta
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

class CloudWatchClient:
    """Handles CloudWatch operations for monitoring."""
    
    def __init__(self, cross_account_client=None, region='us-east-1'):
        self.cross_account_client = cross_account_client
        self.region = region
        if cross_account_client:
            self.client = cross_account_client.get_client('cloudwatch')
        else:
            self.client = boto3.client('cloudwatch', region_name=region)

    def get_metric_data(self, namespace, metric_name, dimensions, start_time, end_time, period=300):
        """Get metric data from CloudWatch."""
        try:
            response = self.client.get_metric_data(
                MetricDataQueries=[
                    {
                        'Id': f'metric_{metric_name}',
                        'MetricStat': {
                            'Metric': {
                                'Namespace': namespace,
                                'MetricName': metric_name,
                                'Dimensions': dimensions
                            },
                            'Period': period,
                            'Stat': 'Average'
                        }
                    }
                ],
                StartTime=start_time,
                EndTime=end_time
            )
            return response
        except ClientError as e:
            logger.error(f"Error getting metric data: {str(e)}")
            return None

    def list_metrics(self, namespace=None, metric_name=None, dimensions=None):
        """List available metrics."""
        try:
            params = {}
            if namespace:
                params['Namespace'] = namespace
            if metric_name:
                params['MetricName'] = metric_name
            if dimensions:
                params['Dimensions'] = dimensions

            response = self.client.list_metrics(**params)
            return response.get('Metrics', [])
        except ClientError as e:
            logger.error(f"Error listing metrics: {str(e)}")
            return []

    def describe_alarms(self, alarm_names=None, alarm_name_prefix=None, state_value=None):
        """Describe CloudWatch alarms."""
        try:
            params = {}
            if alarm_names:
                params['AlarmNames'] = alarm_names
            if alarm_name_prefix:
                params['AlarmNamePrefix'] = alarm_name_prefix
            if state_value:
                params['StateValue'] = state_value

            response = self.client.describe_alarms(**params)
            return response.get('MetricAlarms', [])
        except ClientError as e:
            logger.error(f"Error describing alarms: {str(e)}")
            return []

    def put_metric_alarm(self, alarm_name, metric_name, namespace, dimensions, 
                        threshold, comparison_operator, evaluation_periods=1, 
                        period=300, statistic='Average', alarm_description=''):
        """Create a CloudWatch alarm."""
        try:
            response = self.client.put_metric_alarm(
                AlarmName=alarm_name,
                AlarmDescription=alarm_description,
                MetricName=metric_name,
                Namespace=namespace,
                Dimensions=dimensions,
                Period=period,
                EvaluationPeriods=evaluation_periods,
                Threshold=threshold,
                ComparisonOperator=comparison_operator,
                Statistic=statistic
            )
            return response
        except ClientError as e:
            logger.error(f"Error creating alarm: {str(e)}")
            return None

    def delete_alarms(self, alarm_names):
        """Delete CloudWatch alarms."""
        try:
            response = self.client.delete_alarms(AlarmNames=alarm_names)
            return response
        except ClientError as e:
            logger.error(f"Error deleting alarms: {str(e)}")
            return None 