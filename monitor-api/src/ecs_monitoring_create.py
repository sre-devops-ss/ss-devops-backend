import json
import boto3
import base64
import os

import logging
from datetime import datetime, timedelta
from utils.cross_account import CrossAccountClient
from utils.cassandra_client import CassandraClient



logger = logging.getLogger()
logger.setLevel(logging.INFO)

class ECSMonitoring:
    def __init__(self,account):
        
        self.ssm_client=account.get_client("ssm")
        self.ecs_client=account.get_client("ecs")
        self.cloudwatch_client=account.get_client("ecs")
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
            self.ssm_client.put_parameter(
                Name=f'/cloudwatch-agent/config/{instance_id}',
                Value=json.dumps(self.get_cloudwatch_agent_config()),
                Type='String',
                Overwrite=True
            )

            # Send command to install and configure CloudWatch agent
            self.ssm_client.send_command(
                InstanceIds=[instance_id],
                DocumentName='AWS-ConfigureAWSPackage',
                Parameters={
                    'action': ['Install'],
                    'name': ['AmazonCloudWatchAgent']
                }
            )

            # Start CloudWatch agent
            self.ssm_client.send_command(
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

    def setup_ecs_monitoring(self, cluster_name, service_name, service_details, config=None):
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
            
            # Create CPU Utilization alarm
            cpu_alarm_name = f"{cluster_name}-{service_name}-cpu-utilization"
            self.cloudwatch_client.put_metric_alarm(
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
            self.cloudwatch_client.put_metric_alarm(
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
            self.cloudwatch_client.put_metric_alarm(
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
            

            
            logger.info(f"Successfully set up monitoring for service {service_name} in cluster {cluster_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error setting up ECS monitoring: {str(e)}")
            return False
    

def lambda_handler(event, context):
    try:
        # Get ECS service details from event
        body = json.loads(event.get('body', '{}'))
        cluster_name = body.get('cluster_name')
        service_name = body.get('service_name')
        config = body.get('config', {})

        ROLE_NAME = os.environ.get('ROLE_NAME')
        account_id = body.get('account_id')
        role_arn = f"arn:aws:iam::{account_id}:role/{ROLE_NAME}"
        region = body.get('region', 'us-east-1')

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
        
        if not cluster_name or not service_name:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'cluster_name and service_name are required'
                })
            }
        
        # Initialize ECS monitoring
        ecs_monitoring = ECSMonitoring(cross_account_client)
        
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