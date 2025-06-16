import json
import boto3
from datetime import datetime, timedelta
from utils import get_cassandra_session, store_alarm

class S3Monitoring:
    def __init__(self):
        self.s3 = boto3.client('s3')
        self.cloudwatch = boto3.client('cloudwatch')
        self.session = get_cassandra_session()

    def setup_s3_monitoring(self, bucket_name, config=None):
        """Set up monitoring for an S3 bucket"""
        try:
            # Verify bucket exists
            self.s3.head_bucket(Bucket=bucket_name)
            
            # Default configuration
            default_config = {
                'bucket_size_threshold': 1000000000,  # 1GB in bytes
                'evaluation_periods': 2,
                'period': 300,
                'alarm_actions': [
                    f"arn:aws:sns:{boto3.session.Session().region_name}:{boto3.client('sts').get_caller_identity()['Account']}:monitoring-alerts"
                ]
            }
            
            # Merge with user config
            if config:
                default_config.update(config)
            
            # Create alarms for S3 metrics
            self._create_bucket_size_alarm(bucket_name, default_config)
            
            # Set up delete event notifications for backup bucket
            if 'backup' in bucket_name.lower():
                self._setup_delete_notifications(bucket_name)
            
            return {
                'statusCode': 200,
                'body': {
                    'message': 'S3 bucket monitoring enabled successfully',
                    'bucket_name': bucket_name,
                    'alarms_created': [
                        f"{bucket_name}-size-alarm"
                    ]
                }
            }
            
        except Exception as e:
            print(f"Error setting up S3 bucket monitoring: {str(e)}")
            return {
                'statusCode': 500,
                'body': {
                    'error': 'Internal Server Error',
                    'message': str(e)
                }
            }

    def _create_bucket_size_alarm(self, bucket_name, config):
        """Create CloudWatch alarm for bucket size"""
        try:
            alarm_name = f"{bucket_name}-size-alarm"
            
            # Create alarm
            self.cloudwatch.put_metric_alarm(
                AlarmName=alarm_name,
                AlarmDescription=f"Alarm for {bucket_name} size",
                MetricName='BucketSizeBytes',
                Namespace='AWS/S3',
                Statistic='Average',
                Period=config['period'],
                EvaluationPeriods=config['evaluation_periods'],
                Threshold=config['bucket_size_threshold'],
                ComparisonOperator='GreaterThanThreshold',
                Dimensions=[
                    {
                        'Name': 'BucketName',
                        'Value': bucket_name
                    },
                    {
                        'Name': 'StorageType',
                        'Value': 'StandardStorage'
                    }
                ],
                AlarmActions=config['alarm_actions']
            )
            
            # Store alarm info in Cassandra
            store_alarm(
                self.session,
                's3',
                bucket_name,
                alarm_name,
                'BucketSizeBytes',
                config['bucket_size_threshold'],
                'GreaterThanThreshold',
                config['period']
            )
            
        except Exception as e:
            print(f"Error creating bucket size alarm: {str(e)}")
            raise

    def _setup_delete_notifications(self, bucket_name):
        """Set up delete event notifications for backup bucket"""
        try:
            # Get current notification configuration
            notification_config = self.s3.get_bucket_notification_configuration(
                Bucket=bucket_name
            )
            
            # Create or update notification configuration
            notification_config['EventBridgeConfiguration'] = {}
            
            # Add delete event notification
            if 'LambdaFunctionConfigurations' not in notification_config:
                notification_config['LambdaFunctionConfigurations'] = []
            
            notification_config['LambdaFunctionConfigurations'].append({
                'Id': f"{bucket_name}-delete-notification",
                'LambdaFunctionArn': f"arn:aws:lambda:{boto3.session.Session().region_name}:{boto3.client('sts').get_caller_identity()['Account']}:function:backup-delete-handler",
                'Events': ['s3:ObjectRemoved:*']
            })
            
            # Update bucket notification configuration
            self.s3.put_bucket_notification_configuration(
                Bucket=bucket_name,
                NotificationConfiguration=notification_config
            )
            
        except Exception as e:
            print(f"Error setting up delete notifications: {str(e)}")
            raise

def lambda_handler(event, context):
    """Lambda handler for setting up monitoring"""
    try:
        # Get bucket name from event
        bucket_name = event.get('bucket_name')
        if not bucket_name:
            return {
                'statusCode': 400,
                'body': {
                    'error': 'Bad Request',
                    'message': 'bucket_name is required'
                }
            }
        
        # Get configuration from event
        config = event.get('config')
        
        # Initialize monitoring
        monitor = S3Monitoring()
        
        # Set up monitoring
        return monitor.setup_s3_monitoring(bucket_name, config)
        
    except Exception as e:
        print(f"Error in lambda_handler: {str(e)}")
        return {
            'statusCode': 500,
            'body': {
                'error': 'Internal Server Error',
                'message': str(e)
            }
        } 