import json
import boto3
from monitoring_utils import MonitoringUtils
import logging
from datetime import datetime, timedelta
from utils.cross_account import CrossAccountClient
from utils.cassandra_client import CassandraClient

logger = logging.getLogger()
logger.setLevel(logging.INFO)

class RDSMonitoring:
    def __init__(self):
        self.rds = boto3.client('rds')
        self.monitoring = MonitoringUtils()
        self.sns_topic_arn = f"arn:aws:sns:{boto3.session.Session().region_name}:{boto3.client('sts').get_caller_identity()['Account']}:rds-alerts"

    def setup_rds_monitoring(self, db_instance_id, config=None):
        """Set up monitoring for RDS instance with configurable parameters"""
        try:
            # Default configuration
            default_config = {
                'cpu_threshold': 80.0,
                'memory_threshold': 1073741824,  # 1GB in bytes
                'connection_threshold': 0.8,  # 80% of max connections
                'storage_threshold': 10737418240,  # 10GB in bytes
                'deadlock_threshold': 1,
                'evaluation_periods': 2,
                'period': 300,
                'alarm_actions': [self.sns_topic_arn]
            }

            # Merge default config with user config
            if config:
                default_config.update(config)

            # Get RDS instance details
            response = self.rds.describe_db_instances(DBInstanceIdentifier=db_instance_id)
            if not response['DBInstances']:
                raise Exception(f"RDS instance {db_instance_id} not found")
            
            db_instance = response['DBInstances'][0]
            
            # Calculate connection threshold based on max connections
            max_connections = db_instance.get('MaxConnections', 100)
            connection_threshold = int(max_connections * default_config['connection_threshold'])
            
            # Define metrics and their configurations
            metrics_config = {
                'CPUUtilization': {
                    'threshold': default_config['cpu_threshold'],
                    'evaluation_periods': default_config['evaluation_periods'],
                    'period': default_config['period'],
                    'comparison_operator': 'GreaterThanThreshold'
                },
                'FreeableMemory': {
                    'threshold': default_config['memory_threshold'],
                    'evaluation_periods': default_config['evaluation_periods'],
                    'period': default_config['period'],
                    'comparison_operator': 'LessThanThreshold'
                },
                'DatabaseConnections': {
                    'threshold': connection_threshold,
                    'evaluation_periods': default_config['evaluation_periods'],
                    'period': default_config['period'],
                    'comparison_operator': 'GreaterThanThreshold'
                },
                'FreeLocalStorage': {
                    'threshold': default_config['storage_threshold'],
                    'evaluation_periods': default_config['evaluation_periods'],
                    'period': default_config['period'],
                    'comparison_operator': 'LessThanThreshold'
                },
                'Deadlocks': {
                    'threshold': default_config['deadlock_threshold'],
                    'evaluation_periods': 1,
                    'period': default_config['period'],
                    'comparison_operator': 'GreaterThanThreshold'
                }
            }
            
            # Create alarms for each metric
            for metric_name, config in metrics_config.items():
                alarm_name = f"{db_instance_id}-{metric_name.lower()}"
                
                # Create CloudWatch alarm
                self.monitoring.create_metric_alarm(
                    alarm_name=alarm_name,
                    metric_name=metric_name,
                    namespace="AWS/RDS",
                    dimensions=[{'Name': 'DBInstanceIdentifier', 'Value': db_instance_id}],
                    threshold=config['threshold'],
                    comparison_operator=config['comparison_operator'],
                    evaluation_periods=config['evaluation_periods'],
                    period=config['period'],
                    alarm_actions=default_config['alarm_actions']
                )
                
                # Store alarm information in Cassandra
                self.monitoring.store_alarm_info(
                    service_type="RDS",
                    resource_id=db_instance_id,
                    alarm_name=alarm_name,
                    metric_name=metric_name,
                    threshold=config['threshold'],
                    comparison_operator=config['comparison_operator'],
                    period=config['period']
                )
            
            # Set up event monitoring
            self.setup_event_monitoring(db_instance_id)
            
            return True
            
        except Exception as e:
            print(f"Error setting up RDS monitoring: {str(e)}")
            raise

    def setup_event_monitoring(self, db_instance_id):
        """Set up event monitoring for RDS instance"""
        try:
            # Create CloudWatch event rule for RDS events
            events = boto3.client('events')
            
            rule_name = f"{db_instance_id}-events"
            events.put_rule(
                Name=rule_name,
                EventPattern=json.dumps({
                    "source": ["aws.rds"],
                    "detail-type": ["AWS API Call via CloudTrail"],
                    "detail": {
                        "eventSource": ["rds.amazonaws.com"],
                        "eventName": [
                            "ModifyDBInstance",
                            "RebootDBInstance",
                            "ModifyDBInstance",
                            "ResetDBInstanceMasterUserPassword",
                            "ModifyDBSecurityGroup"
                        ],
                        "requestParameters": {
                            "dBInstanceIdentifier": [db_instance_id]
                        }
                    }
                }),
                State="ENABLED"
            )
            
            # Add target to the rule
            events.put_targets(
                Rule=rule_name,
                Targets=[
                    {
                        'Id': f"{db_instance_id}-event-target",
                        'Arn': f"arn:aws:lambda:{boto3.session.Session().region_name}:{boto3.client('sts').get_caller_identity()['Account']}:function:rds-event-handler",
                        'Input': json.dumps({
                            'db_instance_id': db_instance_id,
                            'event_type': 'rds_event'
                        })
                    }
                ]
            )
            
            return True
            
        except Exception as e:
            print(f"Error setting up event monitoring: {str(e)}")
            raise

def lambda_handler(event, context):
    try:
        # Get RDS instance details and configuration from event
        body = json.loads(event.get('body', '{}'))
        db_instance_id = body.get('db_instance_id')
        config = body.get('config', {})
        
        if not db_instance_id:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'db_instance_id is required'
                })
            }
        
        # Initialize RDS monitoring
        rds_monitoring = RDSMonitoring()
        
        # Set up monitoring with configuration
        rds_monitoring.setup_rds_monitoring(db_instance_id, config)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f'Successfully set up monitoring for RDS instance {db_instance_id}'
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }

def setup_rds_monitoring(cross_account_client, db_instance_id, config=None):
    """
    Set up monitoring for RDS instance using cross-account authentication
    
    Args:
        cross_account_client (CrossAccountClient): Authenticated client for cross-account operations
        db_instance_id (str): RDS instance identifier
        config (dict): Optional configuration overrides
    """
    try:
        # Default monitoring configuration
        default_config = {
            'cpu_threshold': 80,
            'memory_threshold': 85,
            'connection_threshold': 80,
            'storage_threshold': 85,
            'evaluation_periods': 2,
            'period': 300,
            'alarm_actions': []
        }
        
        # Merge with user config
        monitoring_config = {**default_config, **(config or {})}
        
        # Get RDS client using cross-account authentication
        rds = cross_account_client.get_client('rds')
        cloudwatch = cross_account_client.get_client('cloudwatch')
        
        # Get RDS instance details
        response = rds.describe_db_instances(DBInstanceIdentifier=db_instance_id)
        if not response['DBInstances']:
            raise Exception(f"RDS instance {db_instance_id} not found")
        
        db_instance = response['DBInstances'][0]
        
        # Store monitoring config
        cross_account_client.store_monitoring_config('rds', monitoring_config)
        
        # Create CPU Utilization alarm
        cpu_alarm_name = f"{db_instance_id}-cpu-utilization"
        cloudwatch.put_metric_alarm(
            AlarmName=cpu_alarm_name,
            AlarmDescription=f"CPU utilization alarm for {db_instance_id}",
            MetricName='CPUUtilization',
            Namespace='AWS/RDS',
            Statistic='Average',
            Dimensions=[{'Name': 'DBInstanceIdentifier', 'Value': db_instance_id}],
            Period=monitoring_config['period'],
            EvaluationPeriods=monitoring_config['evaluation_periods'],
            Threshold=monitoring_config['cpu_threshold'],
            ComparisonOperator='GreaterThanThreshold',
            AlarmActions=monitoring_config['alarm_actions']
        )
        
        # Create Memory Utilization alarm
        memory_alarm_name = f"{db_instance_id}-memory-utilization"
        cloudwatch.put_metric_alarm(
            AlarmName=memory_alarm_name,
            AlarmDescription=f"Memory utilization alarm for {db_instance_id}",
            MetricName='FreeableMemory',
            Namespace='AWS/RDS',
            Statistic='Average',
            Dimensions=[{'Name': 'DBInstanceIdentifier', 'Value': db_instance_id}],
            Period=monitoring_config['period'],
            EvaluationPeriods=monitoring_config['evaluation_periods'],
            Threshold=monitoring_config['memory_threshold'],
            ComparisonOperator='LessThanThreshold',
            AlarmActions=monitoring_config['alarm_actions']
        )
        
        # Create Connection Count alarm
        connection_alarm_name = f"{db_instance_id}-connection-count"
        cloudwatch.put_metric_alarm(
            AlarmName=connection_alarm_name,
            AlarmDescription=f"Database connection count alarm for {db_instance_id}",
            MetricName='DatabaseConnections',
            Namespace='AWS/RDS',
            Statistic='Average',
            Dimensions=[{'Name': 'DBInstanceIdentifier', 'Value': db_instance_id}],
            Period=monitoring_config['period'],
            EvaluationPeriods=monitoring_config['evaluation_periods'],
            Threshold=monitoring_config['connection_threshold'],
            ComparisonOperator='GreaterThanThreshold',
            AlarmActions=monitoring_config['alarm_actions']
        )
        
        # Create Storage Space alarm
        storage_alarm_name = f"{db_instance_id}-storage-space"
        cloudwatch.put_metric_alarm(
            AlarmName=storage_alarm_name,
            AlarmDescription=f"Storage space alarm for {db_instance_id}",
            MetricName='FreeStorageSpace',
            Namespace='AWS/RDS',
            Statistic='Average',
            Dimensions=[{'Name': 'DBInstanceIdentifier', 'Value': db_instance_id}],
            Period=monitoring_config['period'],
            EvaluationPeriods=monitoring_config['evaluation_periods'],
            Threshold=monitoring_config['storage_threshold'],
            ComparisonOperator='LessThanThreshold',
            AlarmActions=monitoring_config['alarm_actions']
        )
        
        # Get current metrics and store in Cassandra
        metrics = cross_account_client.get_metrics(
            namespace='AWS/RDS',
            metric_name='CPUUtilization',
            dimensions=[{'Name': 'DBInstanceIdentifier', 'Value': db_instance_id}],
            start_time=datetime.utcnow() - timedelta(hours=1),
            end_time=datetime.utcnow()
        )
        
        # Get alarms and store in Cassandra
        alarms = cross_account_client.get_alarms()
        
        logger.info(f"Successfully set up monitoring for RDS instance {db_instance_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error setting up RDS monitoring: {str(e)}")
        return False

def get_rds_metrics(cross_account_client, db_instance_id, metric_name, start_time=None, end_time=None):
    """
    Get metrics for a specific RDS instance
    
    Args:
        cross_account_client (CrossAccountClient): Authenticated client for cross-account operations
        db_instance_id (str): RDS instance identifier
        metric_name (str): Name of the metric to retrieve
        start_time (datetime): Start time for metric data
        end_time (datetime): End time for metric data
    """
    try:
        return cross_account_client.get_metrics(
            namespace='AWS/RDS',
            metric_name=metric_name,
            dimensions=[{'Name': 'DBInstanceIdentifier', 'Value': db_instance_id}],
            start_time=start_time,
            end_time=end_time
        )
    except Exception as e:
        logger.error(f"Error getting RDS metrics: {str(e)}")
        return []

def get_rds_alarms(cross_account_client, db_instance_id):
    """
    Get alarms for a specific RDS instance
    
    Args:
        cross_account_client (CrossAccountClient): Authenticated client for cross-account operations
        db_instance_id (str): RDS instance identifier
    """
    try:
        alarms = cross_account_client.get_alarms()
        return [alarm for alarm in alarms if any(
            dim['Name'] == 'DBInstanceIdentifier' and dim['Value'] == db_instance_id
            for dim in alarm.get('Dimensions', [])
        )]
    except Exception as e:
        logger.error(f"Error getting RDS alarms: {str(e)}")
        return [] 