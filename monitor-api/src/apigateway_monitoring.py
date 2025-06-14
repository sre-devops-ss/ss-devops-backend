import json
import boto3
import os
from datetime import datetime, timedelta

from utils.cross_account import CrossAccountClient
class APIGatewayMonitoring:
    def __init__(self,account):
        self.apigateway = account.get_client("apigateway")
        self.cloudwatch = account.get_client("cloudwatch")
    

    def setup_apigateway_monitoring(self,api_id, config=None):
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
            
          
            
        except Exception as e:
            print(f"Error creating latency alarm: {str(e)}")
            raise

def lambda_handler(event, context):
    """Lambda handler for setting up monitoring"""
    try:
        # Get API ID from event
        body = json.loads(event.get('body', '{}'))
        api_id = body.get('api_id')
        ROLE_NAME = os.environ.get('ROLE_NAME')
        account_id = body.get('account_id')
        role_arn = f"arn:aws:iam::{account_id}:role/{ROLE_NAME}"
        region = body.get('region', 'us-east-1')
        config = body.get('config')
        
        if not all([account_id, role_arn]):
            return {
                'statusCode': 400,
                'body': {
                    'error': 'Missing required parameters',
                    'message': 'account_id and role_arn are required'
                }
            }

        # Initialize cross-account client
        cross_account_client = CrossAccountClient(account_id, role_arn, region)
        cross_account_client.assume_role()
        
        if not api_id:
            return {
                'statusCode': 400,
                'body': {
                    'error': 'Bad Request',
                    'message': 'api_id is required'
                }
            }
        

        
    
        monitor = APIGatewayMonitoring(cross_account_client)
        
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