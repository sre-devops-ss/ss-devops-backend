import json
import boto3
import base64
import os
import logging
from datetime import datetime, timedelta
from utils.cross_account import CrossAccountClient
ec2 = boto3.client('ec2')
ssm = boto3.client('ssm')

logger = logging.getLogger()
logger.setLevel(logging.INFO)
def get_cloudwatch_agent_config():
    """Generate CloudWatch agent configuration for memory, disk, and load average monitoring"""
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
                },
                "swap": {
                    "measurement": [
                        "swap_used_percent"
                    ],
                    "metrics_collection_interval": 60
                },
                "load": {
                    "measurement": [
                        "load1",
                        "load5",
                        "load15"
                    ],
                    "metrics_collection_interval": 60
                }
            }
        }
    }

def is_cloudwatch_agent_running(instance_id):
    """Check if CloudWatch agent is running on the EC2 instance via SSM."""
    try:
        response = ssm.send_command(
            InstanceIds=[instance_id],
            DocumentName='AWS-RunShellScript',
            Parameters={'commands': [
                '/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -m ec2 -a status'
            ]},
        )
        command_id = response['Command']['CommandId']
        # Wait for command to complete (simple polling, can be improved)
        for _ in range(10):
            output = ssm.get_command_invocation(
                CommandId=command_id,
                InstanceId=instance_id
            )
            if output['Status'] in ['Success', 'Failed', 'Cancelled', 'TimedOut']:
                break
            import time; time.sleep(2)
        return 'running' in output.get('StandardOutputContent', '').lower()
    except Exception as e:
        logger.error(f"Error checking CloudWatch agent status: {str(e)}")
        return False

def setup_cloudwatch_agent(instance_id):
    """Set up CloudWatch agent on EC2 instance if not already running."""
    if is_cloudwatch_agent_running(instance_id):
        logger.info(f"CloudWatch agent already running on {instance_id}")
        return
    try:
        # Create SSM document for CloudWatch agent installation
        ssm.put_parameter(
            Name=f'/cloudwatch-agent/config/{instance_id}',
            Value=json.dumps(get_cloudwatch_agent_config()),
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

def setup_ec2_monitoring(cross_account_client, instances, config=None,sns_topic_arn=None ):
    """
    Set up monitoring for EC2 instances using cross-account authentication
    
    Args:
        cross_account_client (CrossAccountClient): Authenticated client for cross-account operations
        instances (list): List of EC2 instances to monitor
        config (dict): Optional configuration overrides
    """
    try:
        # Default monitoring configuration
        default_config = {
            'cpu_threshold': 80,
            'memory_threshold': 85,
            'disk_threshold': 85,
            'evaluation_periods': 2,
            'period': 300,
            'alarm_actions': [sns_topic_arn]
        }
        
        # Merge with user config
        monitoring_config = {**default_config, **(config or {})}
        
        # Get CloudWatch client using cross-account authentication
        cloudwatch = cross_account_client.get_client('cloudwatch')
        
        # Store monitoring config
        cross_account_client.store_monitoring_config('ec2', monitoring_config)
        
        for instance in instances:
            instance_id = instance['InstanceId']
            instance_name = next((tag['Value'] for tag in instance.get('Tags', []) 
                                if tag['Key'] == 'Name'), instance_id)
            
            # Create CPU Utilization alarm
            cpu_alarm_name = f"{instance_name}-cpu-utilization"
            setup_cloudwatch_agent(instance_id)
            cloudwatch.put_metric_alarm(
                AlarmName=cpu_alarm_name,
                AlarmDescription=f"CPU utilization alarm for {instance_name}",
                MetricName='CPUUtilization',
                Namespace='AWS/EC2',
                Statistic='Average',
                Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
                Period=monitoring_config['period'],
                EvaluationPeriods=monitoring_config['evaluation_periods'],
                Threshold=monitoring_config['cpu_threshold'],
                ComparisonOperator='GreaterThanThreshold',
                AlarmActions=monitoring_config['alarm_actions']
            )
            
            # Create Memory Utilization alarm (requires CloudWatch agent)
            memory_alarm_name = f"{instance_name}-memory-utilization"
            cloudwatch.put_metric_alarm(
                AlarmName=memory_alarm_name,
                AlarmDescription=f"Memory utilization alarm for {instance_name}",
                MetricName='mem_used_percent',
                Namespace='CWAgent',
                Statistic='Average',
                Dimensions=[
                    {'Name': 'InstanceId', 'Value': instance_id},
                    {'Name': 'InstanceType', 'Value': instance['InstanceType']}
                ],
                Period=monitoring_config['period'],
                EvaluationPeriods=monitoring_config['evaluation_periods'],
                Threshold=monitoring_config['memory_threshold'],
                ComparisonOperator='GreaterThanThreshold',
                AlarmActions=monitoring_config['alarm_actions']
            )
            
            # Create Disk Utilization alarm (requires CloudWatch agent)
            disk_alarm_name = f"{instance_name}-disk-utilization"
            cloudwatch.put_metric_alarm(
                AlarmName=disk_alarm_name,
                AlarmDescription=f"Disk utilization alarm for {instance_name}",
                MetricName='disk_used_percent',
                Namespace='CWAgent',
                Statistic='Average',
                Dimensions=[
                    {'Name': 'InstanceId', 'Value': instance_id},
                    {'Name': 'InstanceType', 'Value': instance['InstanceType']},
                    {'Name': 'Filesystem', 'Value': '/dev/xvda1'}
                ],
                Period=monitoring_config['period'],
                EvaluationPeriods=monitoring_config['evaluation_periods'],
                Threshold=monitoring_config['disk_threshold'],
                ComparisonOperator='GreaterThanThreshold',
                AlarmActions=monitoring_config['alarm_actions']
            )
            
            logger.info(f"Successfully set up monitoring for instance {instance_id}")
            
        return True
        
    except Exception as e:
        logger.error(f"Error setting up EC2 monitoring: {str(e)}")
        return False

def lambda_handler(event, context):
    try:
        # Get parameters from the event
        body = json.loads(event.get('body', '{}'))
        ROLE_NAME = os.environ.get('ROLE_NAME')
        REGION = os.environ.get('REGION')
        sns_topic_arn_parameter_name = "/devops-backend/snstopic/arn"
        account_id = body.get('account_id')
        role_arn = f"arn:aws:iam::{account_id}:role/{ROLE_NAME}"
        region = body.get('region') or REGION 
        config = body.get('config')
    
        if not all([account_id, ROLE_NAME]):
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Missing required parameters',
                    'message': 'account_id and ROLE_NAME are required'
                })
            }
        
        # Initialize cross-account client
        cross_account_client = CrossAccountClient(account_id, role_arn, region)
        if not cross_account_client.assume_role():
            return {
                'statusCode': 500,
                'body': json.dumps({'error': 'Failed to assume cross-account role'})
            }
        
        # Get EC2 client
        ec2_client = cross_account_client.get_client('ec2')
        ssm_client = cross_account_client.get_client('ssm')

        sns_responce = ssm_client.get_parameter(
                    Name=sns_topic_arn_parameter_name,
                    WithDecryption=False )

        sns_topic_arn = sns_responce['Parameter']['Value']
        
        
        instance_ids = body.get('instance_ids', [])
        if not instance_ids:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'instance_ids is required'})
            }
        
        # Get EC2 instance details
        try:
            response = ec2_client.describe_instances(
                InstanceIds=instance_ids
            )
            instances = []
            for reservation in response['Reservations']:
                instances.extend(reservation['Instances'])
        except Exception as e:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': f'Failed to describe instances: {str(e)}'})
            }
        
        # Set up monitoring for the instances
        success = setup_ec2_monitoring(cross_account_client, instances, config,sns_topic_arn)
        
        if success:
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'EC2 monitoring enabled successfully',
                    'instances': [instance['InstanceId'] for instance in instances]
                })
            }
        else:
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'error': 'Failed to set up EC2 monitoring'
                })
            }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        } 