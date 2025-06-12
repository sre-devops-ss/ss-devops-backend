import json
import boto3
from datetime import datetime, timedelta
from utils import get_cassandra_session, store_alarm

class APIGatewayMonitoring:
    def __init__(self):
        self.apigateway = boto3.client('apigateway')
        self.cloudwatch = boto3.client('cloudwatch')
        self.session = get_cassandra_session()

    def setup_apigateway_monitoring(self, api_id, config=None):
        """Set up monitoring for an API Gateway"""
        try:
            # Verify API Gateway exists
            self.apigateway.get_rest_api(restApiId=api_id)
            
            # Default configuration
            default_config = {
                'error_4xx_threshold': 10,
                'error_5xx_threshold': 5,
                'latency_threshold': 1000,  # milliseconds
                'evaluation_periods': 2,
                'period': 300,
                'alarm_actions': [
                    f"arn:aws:sns:{boto3.session.Session().region_name}:{boto3.client('sts').get_caller_identity()['Account']}:monitoring-alerts"
                ]
            }
            
            # Merge with user config
            if config:
                default_config.update(config)
            
            # Create alarms for API Gateway metrics
            self._create_4xx_error_alarm(api_id, default_config)
            self._create_5xx_error_alarm(api_id, default_config)
            self._create_latency_alarm(api_id, default_config)
            
            return {
                'statusCode': 200,
                'body': {
                    'message': 'API Gateway monitoring enabled successfully',
                    'api_id': api_id,
                    'alarms_created': [
                        f"{api_id}-4xx-error-alarm",
                        f"{api_id}-5xx-error-alarm",
                        f"{api_id}-latency-alarm"
                    ]
                }
            }
            
        except Exception as e:
            print(f"Error setting up API Gateway monitoring: {str(e)}")
            return {
                'statusCode': 500,
                'body': {
                    'error': 'Internal Server Error',
                    'message': str(e)
                }
            }

    def _create_4xx_error_alarm(self, api_id, config):
        """Create CloudWatch alarm for 4xx errors"""
        try:
            alarm_name = f"{api_id}-4xx-error-alarm"
            
            # Create alarm
            self.cloudwatch.put_metric_alarm(
                AlarmName=alarm_name,
                AlarmDescription=f"Alarm for {api_id} 4xx errors",
                MetricName='4XXError',
                Namespace='AWS/ApiGateway',
                Statistic='Sum',
                Period=config['period'],
                EvaluationPeriods=config['evaluation_periods'],
                Threshold=config['error_4xx_threshold'],
                ComparisonOperator='GreaterThanThreshold',
                Dimensions=[
                    {
                        'Name': 'ApiId',
                        'Value': api_id
                    }
                ],
                AlarmActions=config['alarm_actions']
            )
            
            # Store alarm info in Cassandra
            store_alarm(
                self.session,
                'apigateway',
                api_id,
                alarm_name,
                '4XXError',
                config['error_4xx_threshold'],
                'GreaterThanThreshold',
                config['period']
            )
            
        except Exception as e:
            print(f"Error creating 4xx error alarm: {str(e)}")
            raise

    def _create_5xx_error_alarm(self, api_id, config):
        """Create CloudWatch alarm for 5xx errors"""
        try:
            alarm_name = f"{api_id}-5xx-error-alarm"
            
            # Create alarm
            self.cloudwatch.put_metric_alarm(
                AlarmName=alarm_name,
                AlarmDescription=f"Alarm for {api_id} 5xx errors",
                MetricName='5XXError',
                Namespace='AWS/ApiGateway',
                Statistic='Sum',
                Period=config['period'],
                EvaluationPeriods=config['evaluation_periods'],
                Threshold=config['error_5xx_threshold'],
                ComparisonOperator='GreaterThanThreshold',
                Dimensions=[
                    {
                        'Name': 'ApiId',
                        'Value': api_id
                    }
                ],
                AlarmActions=config['alarm_actions']
            )
            
            # Store alarm info in Cassandra
            store_alarm(
                self.session,
                'apigateway',
                api_id,
                alarm_name,
                '5XXError',
                config['error_5xx_threshold'],
                'GreaterThanThreshold',
                config['period']
            )
            
        except Exception as e:
            print(f"Error creating 5xx error alarm: {str(e)}")
            raise

    def _create_latency_alarm(self, api_id, config):
        """Create CloudWatch alarm for API Gateway latency"""
        try:
            alarm_name = f"{api_id}-latency-alarm"
            
            # Create alarm
            self.cloudwatch.put_metric_alarm(
                AlarmName=alarm_name,
                AlarmDescription=f"Alarm for {api_id} latency",
                MetricName='Latency',
                Namespace='AWS/ApiGateway',
                Statistic='Average',
                Period=config['period'],
                EvaluationPeriods=config['evaluation_periods'],
                Threshold=config['latency_threshold'],
                ComparisonOperator='GreaterThanThreshold',
                Dimensions=[
                    {
                        'Name': 'ApiId',
                        'Value': api_id
                    }
                ],
                AlarmActions=config['alarm_actions']
            )
            
            # Store alarm info in Cassandra
            store_alarm(
                self.session,
                'apigateway',
                api_id,
                alarm_name,
                'Latency',
                config['latency_threshold'],
                'GreaterThanThreshold',
                config['period']
            )
            
        except Exception as e:
            print(f"Error creating latency alarm: {str(e)}")
            raise

def lambda_handler(event, context):
    """Lambda handler for setting up monitoring"""
    try:
        # Get API ID from event
        api_id = event.get('api_id')
        if not api_id:
            return {
                'statusCode': 400,
                'body': {
                    'error': 'Bad Request',
                    'message': 'api_id is required'
                }
            }
        
        # Get configuration from event
        config = event.get('config')
        
        # Initialize monitoring
        monitor = APIGatewayMonitoring()
        
        # Set up monitoring
        return monitor.setup_apigateway_monitoring(api_id, config)
        
    except Exception as e:
        print(f"Error in lambda_handler: {str(e)}")
        return {
            'statusCode': 500,
            'body': {
                'error': 'Internal Server Error',
                'message': str(e)
            }
        } 