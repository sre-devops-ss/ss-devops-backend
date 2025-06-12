import json
import boto3
import base64
from utils import get_cassandra_session, create_cloudwatch_alarm, store_alarm
import os
from monitoring_utils import MonitoringUtils
import logging
from datetime import datetime, timedelta
from utils.cross_account import CrossAccountClient
from utils.cassandra_client import CassandraClient

ecs = boto3.client('ecs')
ssm = boto3.client('ssm')
ec2 = boto3.client('ec2')

logger = logging.getLogger()
logger.setLevel(logging.INFO)

class ECSMonitoring:
    def __init__(self):
        self.ecs = boto3.client('ecs')
        self.monitoring = MonitoringUtils()
        self.sns_topic_arn = f"arn:aws:sns:{boto3.session.Session().region_name}:{boto3.client('sts').get_caller_identity()['Account']}:ecs-alerts"

    def get_cloudwatch_agent_config(self):
        """Generate CloudWatch agent configuration for memory and disk monitoring"""
        return {
            "metrics": {
                "metrics_collected": {
                    "mem": {
                        "measurement": [
                            "mem_used_percent",
                            "mem_available",
                            "mem_total"
                        ],
                        "metrics_collection_interval": 60
                    },
                    "disk": {
                        "measurement": [
                            "used_percent",
                            "free",
                            "total"
                        ],
                        "resources": [
                            "/"
                        ],
                        "metrics_collection_interval": 60
                    }
                }
            }
        }

    def setup_cloudwatch_agent(self, instance_id):
        """Set up CloudWatch agent on EC2 instance"""
        try:
            # Create SSM document for CloudWatch agent installation
            ssm.put_parameter(
                Name=f'/cloudwatch-agent/config/{instance_id}',
                Value=json.dumps(self.get_cloudwatch_agent_config()),
                Type='String',
                Overwrite=True
            )

            # Send command to install and configure CloudWatch agent
            ssm.send_command(
                InstanceIds=[instance_id],
                DocumentName='AWS-ConfigureAWSPackage',
                Parameters={
                    'action': ['Install'],
                    'name': ['AmazonCloudWatchAgent']
                }
            )

            # Start CloudWatch agent
            ssm.send_command(
                InstanceIds=[instance_id],
                DocumentName='AmazonCloudWatch-ManageAgent',
                Parameters={
                    'action': ['configure'],
                    'mode': ['ec2'],
                    'optionalConfigurationSource': ['ssm'],
                    'optionalConfigurationLocation': [f'/cloudwatch-agent/config/{instance_id}'],
                    'optionalRestart': ['yes']
                }
            )

        except Exception as e:
            print(f"Error setting up CloudWatch agent: {str(e)}")
            raise

    def setup_ecs_monitoring(self, cluster_name, service_name, config=None):
        """Set up monitoring for ECS service"""
        try:
            # Default configuration
            default_config = {
                'cpu_threshold': 80.0,
                'memory_threshold': 80.0,
                'evaluation_periods': 2,
                'period': 300,
                'alarm_actions': [self.sns_topic_arn]
            }

            # Merge default config with user config
            if config:
                default_config.update(config)

            # Get ECS service details
            response = self.ecs.describe_services(
                cluster=cluster_name,
                services=[service_name]
            )
            
            if not response['services']:
                raise Exception(f"ECS service {service_name} not found in cluster {cluster_name}")
            
            service = response['services'][0]
            
            # Define metrics and their configurations
            metrics_config = {
                'CPUUtilization': {
                    'threshold': default_config['cpu_threshold'],
                    'evaluation_periods': default_config['evaluation_periods'],
                    'period': default_config['period'],
                    'comparison_operator': 'GreaterThanThreshold'
                },
                'MemoryUtilization': {
                    'threshold': default_config['memory_threshold'],
                    'evaluation_periods': default_config['evaluation_periods'],
                    'period': default_config['period'],
                    'comparison_operator': 'GreaterThanThreshold'
                }
            }
            
            # Create alarms for each metric
            for metric_name, config in metrics_config.items():
                alarm_name = f"{cluster_name}-{service_name}-{metric_name.lower()}"
                
                # Create CloudWatch alarm
                self.monitoring.create_metric_alarm(
                    alarm_name=alarm_name,
                    metric_name=metric_name,
                    namespace="AWS/ECS",
                    dimensions=[
                        {'Name': 'ClusterName', 'Value': cluster_name},
                        {'Name': 'ServiceName', 'Value': service_name}
                    ],
                    threshold=config['threshold'],
                    comparison_operator=config['comparison_operator'],
                    evaluation_periods=config['evaluation_periods'],
                    period=config['period'],
                    alarm_actions=default_config['alarm_actions']
                )
                
                # Store alarm information in Cassandra
                self.monitoring.store_alarm_info(
                    service_type="ECS",
                    resource_id=f"{cluster_name}/{service_name}",
                    alarm_name=alarm_name,
                    metric_name=metric_name,
                    threshold=config['threshold'],
                    comparison_operator=config['comparison_operator'],
                    period=config['period']
                )
            
            # Set up event monitoring
            self.setup_event_monitoring(cluster_name, service_name)
            
            return True
            
        except Exception as e:
            print(f"Error setting up ECS monitoring: {str(e)}")
            raise

    def setup_event_monitoring(self, cluster_name, service_name):
        """Set up event monitoring for ECS service"""
        try:
            # Create CloudWatch event rule for ECS events
            events = boto3.client('events')
            
            rule_name = f"{cluster_name}-{service_name}-events"
            events.put_rule(
                Name=rule_name,
                EventPattern=json.dumps({
                    "source": ["aws.ecs"],
                    "detail-type": ["ECS Service Action", "ECS Task State Change"],
                    "detail": {
                        "clusterArn": [f"arn:aws:ecs:{boto3.session.Session().region_name}:{boto3.client('sts').get_caller_identity()['Account']}:cluster/{cluster_name}"],
                        "serviceName": [service_name]
                    }
                }),
                State="ENABLED"
            )
            
            # Add target to the rule
            events.put_targets(
                Rule=rule_name,
                Targets=[
                    {
                        'Id': f"{cluster_name}-{service_name}-event-target",
                        'Arn': f"arn:aws:lambda:{boto3.session.Session().region_name}:{boto3.client('sts').get_caller_identity()['Account']}:function:ecs-event-handler",
                        'Input': json.dumps({
                            'cluster_name': cluster_name,
                            'service_name': service_name,
                            'event_type': 'ecs_event'
                        })
                    }
                ]
            )
            
            return True
            
        except Exception as e:
            print(f"Error setting up event monitoring: {str(e)}")
            raise

def setup_ecs_monitoring(cross_account_client, cluster_name, service_name, service_details, config=None):
    """
    Set up monitoring for an ECS service using cross-account authentication
    
    Args:
        cross_account_client (CrossAccountClient): Authenticated client for cross-account operations
        cluster_name (str): Name of the ECS cluster
        service_name (str): Name of the ECS service
        service_details (dict): Details of the ECS service
        config (dict): Optional configuration overrides
    """
    try:
        # Default monitoring configuration
        default_config = {
            'cpu_threshold': 80,
            'memory_threshold': 85,
            'evaluation_periods': 2,
            'period': 300,
            'alarm_actions': []
        }
        
        # Merge with user config
        monitoring_config = {**default_config, **(config or {})}
        
        # Get CloudWatch client using cross-account authentication
        cloudwatch = cross_account_client.get_client('cloudwatch')
        
        # Store monitoring config
        cross_account_client.store_monitoring_config('ecs', monitoring_config)
        
        # Create CPU Utilization alarm
        cpu_alarm_name = f"{cluster_name}-{service_name}-cpu-utilization"
        cloudwatch.put_metric_alarm(
            AlarmName=cpu_alarm_name,
            AlarmDescription=f"CPU utilization alarm for {service_name} in {cluster_name}",
            MetricName='CPUUtilization',
            Namespace='AWS/ECS',
            Statistic='Average',
            Dimensions=[
                {'Name': 'ClusterName', 'Value': cluster_name},
                {'Name': 'ServiceName', 'Value': service_name}
            ],
            Period=monitoring_config['period'],
            EvaluationPeriods=monitoring_config['evaluation_periods'],
            Threshold=monitoring_config['cpu_threshold'],
            ComparisonOperator='GreaterThanThreshold',
            AlarmActions=monitoring_config['alarm_actions']
        )
        
        # Create Memory Utilization alarm
        memory_alarm_name = f"{cluster_name}-{service_name}-memory-utilization"
        cloudwatch.put_metric_alarm(
            AlarmName=memory_alarm_name,
            AlarmDescription=f"Memory utilization alarm for {service_name} in {cluster_name}",
            MetricName='MemoryUtilization',
            Namespace='AWS/ECS',
            Statistic='Average',
            Dimensions=[
                {'Name': 'ClusterName', 'Value': cluster_name},
                {'Name': 'ServiceName', 'Value': service_name}
            ],
            Period=monitoring_config['period'],
            EvaluationPeriods=monitoring_config['evaluation_periods'],
            Threshold=monitoring_config['memory_threshold'],
            ComparisonOperator='GreaterThanThreshold',
            AlarmActions=monitoring_config['alarm_actions']
        )
        
        # Create Running Task Count alarm
        task_alarm_name = f"{cluster_name}-{service_name}-running-tasks"
        cloudwatch.put_metric_alarm(
            AlarmName=task_alarm_name,
            AlarmDescription=f"Running task count alarm for {service_name} in {cluster_name}",
            MetricName='RunningTaskCount',
            Namespace='AWS/ECS',
            Statistic='Average',
            Dimensions=[
                {'Name': 'ClusterName', 'Value': cluster_name},
                {'Name': 'ServiceName', 'Value': service_name}
            ],
            Period=monitoring_config['period'],
            EvaluationPeriods=monitoring_config['evaluation_periods'],
            Threshold=service_details['desiredCount'],
            ComparisonOperator='LessThanThreshold',
            AlarmActions=monitoring_config['alarm_actions']
        )
        
        # Get current metrics and store in Cassandra
        metrics = cross_account_client.get_metrics(
            namespace='AWS/ECS',
            metric_name='CPUUtilization',
            dimensions=[
                {'Name': 'ClusterName', 'Value': cluster_name},
                {'Name': 'ServiceName', 'Value': service_name}
            ],
            start_time=datetime.utcnow() - timedelta(hours=1),
            end_time=datetime.utcnow()
        )
        
        # Get alarms and store in Cassandra
        alarms = cross_account_client.get_alarms()
        
        logger.info(f"Successfully set up monitoring for service {service_name} in cluster {cluster_name}")
        return True
        
    except Exception as e:
        logger.error(f"Error setting up ECS monitoring: {str(e)}")
        return False

def get_ecs_metrics(cross_account_client, cluster_name, service_name, metric_name, start_time=None, end_time=None):
    """
    Get metrics for a specific ECS service
    
    Args:
        cross_account_client (CrossAccountClient): Authenticated client for cross-account operations
        cluster_name (str): ECS cluster name
        service_name (str): ECS service name
        metric_name (str): Name of the metric to retrieve
        start_time (datetime): Start time for metric data
        end_time (datetime): End time for metric data
    """
    try:
        return cross_account_client.get_metrics(
            namespace='AWS/ECS',
            metric_name=metric_name,
            dimensions=[
                {'Name': 'ClusterName', 'Value': cluster_name},
                {'Name': 'ServiceName', 'Value': service_name}
            ],
            start_time=start_time,
            end_time=end_time
        )
    except Exception as e:
        logger.error(f"Error getting ECS metrics: {str(e)}")
        return []

def get_ecs_alarms(cross_account_client, cluster_name, service_name):
    """
    Get alarms for a specific ECS service
    
    Args:
        cross_account_client (CrossAccountClient): Authenticated client for cross-account operations
        cluster_name (str): ECS cluster name
        service_name (str): ECS service name
    """
    try:
        alarms = cross_account_client.get_alarms()
        return [alarm for alarm in alarms if any(
            dim['Name'] == 'ClusterName' and dim['Value'] == cluster_name and
            dim['Name'] == 'ServiceName' and dim['Value'] == service_name
            for dim in alarm.get('Dimensions', [])
        )]
    except Exception as e:
        logger.error(f"Error getting ECS alarms: {str(e)}")
        return []

def lambda_handler(event, context):
    try:
        # Get ECS service details from event
        body = json.loads(event.get('body', '{}'))
        cluster_name = body.get('cluster_name')
        service_name = body.get('service_name')
        config = body.get('config', {})
        
        if not cluster_name or not service_name:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'cluster_name and service_name are required'
                })
            }
        
        # Initialize ECS monitoring
        ecs_monitoring = ECSMonitoring()
        
        # Set up monitoring
        ecs_monitoring.setup_ecs_monitoring(cluster_name, service_name, config)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f'Successfully set up monitoring for ECS service {service_name} in cluster {cluster_name}'
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        } 