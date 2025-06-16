import json
import boto3
from datetime import datetime, timedelta
from utils import get_cassandra_session, store_alarm

class NATGatewayMonitoring:
    def __init__(self):
        self.ec2 = boto3.client('ec2')
        self.cloudwatch = boto3.client('cloudwatch')
        self.session = get_cassandra_session()

    def setup_nat_monitoring(self, nat_id, config=None):
        """Set up monitoring for a NAT Gateway"""
        try:
            # Verify NAT Gateway exists
            self.ec2.describe_nat_gateways(NatGatewayIds=[nat_id])
            
            # Default configuration
            default_config = {
                'packets_drop_threshold': 100,
                'evaluation_periods': 2,
                'period': 300,
                'alarm_actions': [
                    f"arn:aws:sns:{boto3.session.Session().region_name}:{boto3.client('sts').get_caller_identity()['Account']}:monitoring-alerts"
                ]
            }
            
            # Merge with user config
            if config:
                default_config.update(config)
            
            # Create alarms for NAT Gateway metrics
            self._create_packets_drop_alarm(nat_id, default_config)
            
            return {
                'statusCode': 200,
                'body': {
                    'message': 'NAT Gateway monitoring enabled successfully',
                    'nat_id': nat_id,
                    'alarms_created': [
                        f"{nat_id}-packets-drop-alarm"
                    ]
                }
            }
            
        except Exception as e:
            print(f"Error setting up NAT Gateway monitoring: {str(e)}")
            return {
                'statusCode': 500,
                'body': {
                    'error': 'Internal Server Error',
                    'message': str(e)
                }
            }

    def _create_packets_drop_alarm(self, nat_id, config):
        """Create CloudWatch alarm for packet drops"""
        try:
            alarm_name = f"{nat_id}-packets-drop-alarm"
            
            # Create alarm
            self.cloudwatch.put_metric_alarm(
                AlarmName=alarm_name,
                AlarmDescription=f"Alarm for {nat_id} packet drops",
                MetricName='PacketsDropCount',
                Namespace='AWS/NATGateway',
                Statistic='Sum',
                Period=config['period'],
                EvaluationPeriods=config['evaluation_periods'],
                Threshold=config['packets_drop_threshold'],
                ComparisonOperator='GreaterThanThreshold',
                Dimensions=[
                    {
                        'Name': 'NatGatewayId',
                        'Value': nat_id
                    }
                ],
                AlarmActions=config['alarm_actions']
            )
            
            # Store alarm info in Cassandra
            store_alarm(
                self.session,
                'nat',
                nat_id,
                alarm_name,
                'PacketsDropCount',
                config['packets_drop_threshold'],
                'GreaterThanThreshold',
                config['period']
            )
            
        except Exception as e:
            print(f"Error creating packets drop alarm: {str(e)}")
            raise

def lambda_handler(event, context):
    """Lambda handler for setting up monitoring"""
    try:
        # Get NAT Gateway ID from event
        nat_id = event.get('nat_id')
        if not nat_id:
            return {
                'statusCode': 400,
                'body': {
                    'error': 'Bad Request',
                    'message': 'nat_id is required'
                }
            }
        
        # Get configuration from event
        config = event.get('config')
        
        # Initialize monitoring
        monitor = NATGatewayMonitoring()
        
        # Set up monitoring
        return monitor.setup_nat_monitoring(nat_id, config)
        
    except Exception as e:
        print(f"Error in lambda_handler: {str(e)}")
        return {
            'statusCode': 500,
            'body': {
                'error': 'Internal Server Error',
                'message': str(e)
            }
        } 