import json
import boto3
from datetime import datetime, timedelta
from utils import get_cassandra_session, store_alarm

class LambdaMonitoring:
    def __init__(self):
        self.lambda_client = boto3.client('lambda')
        self.cloudwatch = boto3.client('cloudwatch')
        self.logs = boto3.client('logs')
        self.session = get_cassandra_session()

    def setup_lambda_monitoring(self, function_name, config=None):
        """Set up monitoring for a Lambda function"""
        try:
            # Verify Lambda function exists
            self.lambda_client.get_function(FunctionName=function_name)
            
            # Default configuration
            default_config = {
                'error_threshold': 1,
                'duration_threshold': 1000,  # milliseconds
                'evaluation_periods': 2,
                'period': 300,
                'alarm_actions': [
                    f"arn:aws:sns:{boto3.session.Session().region_name}:{boto3.client('sts').get_caller_identity()['Account']}:monitoring-alerts"
                ]
            }
            
            # Merge with user config
            if config:
                default_config.update(config)
            
            # Create alarms for Lambda metrics
            self._create_error_alarm(function_name, default_config)
            self._create_duration_alarm(function_name, default_config)
            self._setup_log_metric_filter(function_name, default_config)
            
            return {
                'statusCode': 200,
                'body': {
                    'message': 'Lambda monitoring enabled successfully',
                    'function_name': function_name,
                    'alarms_created': [
                        f"{function_name}-error-alarm",
                        f"{function_name}-duration-alarm"
                    ]
                }
            }
            
        except Exception as e:
            print(f"Error setting up Lambda monitoring: {str(e)}")
            return {
                'statusCode': 500,
                'body': {
                    'error': 'Internal Server Error',
                    'message': str(e)
                }
            }

    def _create_error_alarm(self, function_name, config):
        """Create CloudWatch alarm for Lambda errors"""
        try:
            alarm_name = f"{function_name}-error-alarm"
            
            # Create alarm
            self.cloudwatch.put_metric_alarm(
                AlarmName=alarm_name,
                AlarmDescription=f"Alarm for {function_name} errors",
                MetricName='Errors',
                Namespace='AWS/Lambda',
                Statistic='Sum',
                Period=config['period'],
                EvaluationPeriods=config['evaluation_periods'],
                Threshold=config['error_threshold'],
                ComparisonOperator='GreaterThanThreshold',
                Dimensions=[
                    {
                        'Name': 'FunctionName',
                        'Value': function_name
                    }
                ],
                AlarmActions=config['alarm_actions']
            )
            
            # Store alarm info in Cassandra
            store_alarm(
                self.session,
                'lambda',
                function_name,
                alarm_name,
                'Errors',
                config['error_threshold'],
                'GreaterThanThreshold',
                config['period']
            )
            
        except Exception as e:
            print(f"Error creating error alarm: {str(e)}")
            raise

    def _create_duration_alarm(self, function_name, config):
        """Create CloudWatch alarm for Lambda duration"""
        try:
            alarm_name = f"{function_name}-duration-alarm"
            
            # Create alarm
            self.cloudwatch.put_metric_alarm(
                AlarmName=alarm_name,
                AlarmDescription=f"Alarm for {function_name} duration",
                MetricName='Duration',
                Namespace='AWS/Lambda',
                Statistic='Maximum',
                Period=config['period'],
                EvaluationPeriods=config['evaluation_periods'],
                Threshold=config['duration_threshold'],
                ComparisonOperator='GreaterThanThreshold',
                Dimensions=[
                    {
                        'Name': 'FunctionName',
                        'Value': function_name
                    }
                ],
                AlarmActions=config['alarm_actions']
            )
            
            # Store alarm info in Cassandra
            store_alarm(
                self.session,
                'lambda',
                function_name,
                alarm_name,
                'Duration',
                config['duration_threshold'],
                'GreaterThanThreshold',
                config['period']
            )
            
        except Exception as e:
            print(f"Error creating duration alarm: {str(e)}")
            raise

    def _setup_log_metric_filter(self, function_name, config):
        """Set up CloudWatch Logs metric filter for Lambda errors"""
        try:
            log_group_name = f"/aws/lambda/{function_name}"
            filter_name = f"{function_name}-error-filter"
            metric_name = f"{function_name}-error-count"
            
            # Create metric filter
            self.logs.put_metric_filter(
                logGroupName=log_group_name,
                filterName=filter_name,
                filterPattern='{ $.level = "ERROR" || $.errorMessage = "*" }',
                metricTransformations=[
                    {
                        'metricName': metric_name,
                        'metricNamespace': 'LambdaErrors',
                        'metricValue': '1'
                    }
                ]
            )
            
            # Create alarm for the metric
            alarm_name = f"{function_name}-log-error-alarm"
            self.cloudwatch.put_metric_alarm(
                AlarmName=alarm_name,
                AlarmDescription=f"Alarm for {function_name} log errors",
                MetricName=metric_name,
                Namespace='LambdaErrors',
                Statistic='Sum',
                Period=config['period'],
                EvaluationPeriods=config['evaluation_periods'],
                Threshold=config['error_threshold'],
                ComparisonOperator='GreaterThanThreshold',
                Dimensions=[
                    {
                        'Name': 'FunctionName',
                        'Value': function_name
                    }
                ],
                AlarmActions=config['alarm_actions']
            )
            
            # Store alarm info in Cassandra
            store_alarm(
                self.session,
                'lambda',
                function_name,
                alarm_name,
                metric_name,
                config['error_threshold'],
                'GreaterThanThreshold',
                config['period']
            )
            
        except Exception as e:
            print(f"Error setting up log metric filter: {str(e)}")
            raise

def lambda_handler(event, context):
    """Lambda handler for setting up monitoring"""
    try:
        # Get function name from event
        function_name = event.get('function_name')
        if not function_name:
            return {
                'statusCode': 400,
                'body': {
                    'error': 'Bad Request',
                    'message': 'function_name is required'
                }
            }
        
        # Get configuration from event
        config = event.get('config')
        
        # Initialize monitoring
        monitor = LambdaMonitoring()
        
        # Set up monitoring
        return monitor.setup_lambda_monitoring(function_name, config)
        
    except Exception as e:
        print(f"Error in lambda_handler: {str(e)}")
        return {
            'statusCode': 500,
            'body': {
                'error': 'Internal Server Error',
                'message': str(e)
            }
        } 