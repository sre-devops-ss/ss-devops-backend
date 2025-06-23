import json
import boto3
import base64
import os
import logging
import time
from datetime import datetime, timedelta
from utils.cross_account import CrossAccountClient


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

def is_cloudwatch_agent_running(instance_id,cross_account_client):
    """Check if CloudWatch agent is running on the EC2 instance via SSM."""
    try:
        ssm = cross_account_client.get_client('ssm')
   
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

def setup_cloudwatch_agent(instance_id,cross_account_client):
    """Set up CloudWatch agent on EC2 instance if not already running."""
    ssm = cross_account_client.get_client('ssm')
    
    if is_cloudwatch_agent_running(instance_id,cross_account_client):
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
def attach_monitoring_role(instance_id,cross_account_client,region=None,):
    ec2=cross_account_client.get_client('ec2')
    iam=cross_account_client.get_client('iam')
    instance = ec2.describe_instances(InstanceIds=[instance_id])['Reservations'][0]['Instances'][0]
    
    
    iam_instance_profile = instance.get('IamInstanceProfile')
    instance_name = next((tag['Value'] for tag in instance.get('Tags', []) if tag['Key'] == 'Name'), instance_id)

    policy_name = f"{instance_name}-CloudWatchAccessPolicy"
    role_name = f"{instance_name}-MonitoringRole"

    monitoring_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "cloudwatch:PutMetricData",
                    "ec2:DescribeVolumes",
                    "ec2:DescribeTags",
                    "logs:PutLogEvents",
                    "logs:DescribeLogStreams",
                    "logs:DescribeLogGroups",
                    "logs:CreateLogStream",
                    "logs:CreateLogGroup"
                ],
                "Resource": "*"
            }
        ]
    }

    # Add SSM managed policy ARN
    ssm_managed_policy_arn = 'arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore'

    if iam_instance_profile:
        profile_arn = iam_instance_profile['Arn']
        profile_name = profile_arn.split('/')[-1]
        profile = iam.get_instance_profile(InstanceProfileName=profile_name)
        role_name_attached = profile['InstanceProfile']['Roles'][0]['RoleName']

        print(f"[INFO] Instance already has IAM role: {role_name_attached}. Adding inline policy...")

        iam.put_role_policy(
            RoleName=role_name_attached,
            PolicyName=policy_name,
            PolicyDocument=json.dumps(monitoring_policy)
        )
    else:
        print(f"[INFO] Instance has no IAM role. Creating role and attaching...")

        # Create IAM role with EC2 trust policy
        trust_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"Service": "ec2.amazonaws.com"},
                    "Action": "sts:AssumeRole"
                }
            ]
        }

        try:
            iam.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=json.dumps(trust_policy),
                Description=f"Monitoring role for instance {instance_id}"
            )
            print(f"[INFO] Created IAM role: {role_name}")
        except iam.exceptions.EntityAlreadyExistsException:
            print(f"[WARN] Role {role_name} already exists.")

        # Attach inline monitoring policy
        iam.put_role_policy(
            RoleName=role_name,
            PolicyName=policy_name,
            PolicyDocument=json.dumps(monitoring_policy)
        )

        # Attach SSM managed policy
        iam.attach_role_policy(
            RoleName=role_name,
            PolicyArn=ssm_managed_policy_arn
        )

        # Create instance profile and attach role
        try:
            iam.create_instance_profile(InstanceProfileName=role_name)
            time.sleep(2)  # Wait for IAM to propagate
        except iam.exceptions.EntityAlreadyExistsException:
            print(f"[WARN] Instance profile {role_name} already exists.")

        try:
            iam.add_role_to_instance_profile(
                InstanceProfileName=role_name,
                RoleName=role_name
            )
            time.sleep(2)
        except iam.exceptions.LimitExceededException:
            print(f"[WARN] Role already attached to profile")

        # Attach instance profile to instance
        ec2.associate_iam_instance_profile(
            IamInstanceProfile={'Name': role_name},
            InstanceId=instance_id
        )
        print(f"[INFO] Attached instance profile {role_name} to instance {instance_id}")




def setup_ec2_monitoring(cross_account_client, instances, config=None ):
    try:
        # Get CloudWatch client using cross-account authentication
        cloudwatch = cross_account_client.get_client('cloudwatch')
        
        # Store monitoring config
        cross_account_client.store_monitoring_config('ec2', config)
        
        for instance in instances:
            instance_id = instance['InstanceId']
            instance_name = next((tag['Value'] for tag in instance.get('Tags', []) 
                                if tag['Key'] == 'Name'), instance_id)
            
            # Create CPU Utilization alarm
            cpu_alarm_name = f"{instance_name}-cpu-utilization"
            attach_monitoring_role(instance_id,cross_account_client)
            setup_cloudwatch_agent(instance_id,cross_account_client)
            cloudwatch.put_metric_alarm(
                AlarmName=cpu_alarm_name,
                AlarmDescription=f"CPU utilization alarm for {instance_name}",
                MetricName='CPUUtilization',
                Namespace='AWS/EC2',
                Statistic='Average',
                Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
                Period=config['period'],
                EvaluationPeriods=config['evaluation_periods'],
                Threshold=config['cpu_threshold'],
                ComparisonOperator='GreaterThanThreshold',
                AlarmActions=config['alarm_actions']
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
                Period=config['period'],
                EvaluationPeriods=config['evaluation_periods'],
                Threshold=config['memory_threshold'],
                ComparisonOperator='GreaterThanThreshold',
                AlarmActions=config['alarm_actions']
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
                Period=config['period'],
                EvaluationPeriods=config['evaluation_periods'],
                Threshold=config['disk_threshold'],
                ComparisonOperator='GreaterThanThreshold',
                AlarmActions=config['alarm_actions']
            )
            
            logger.info(f"Successfully set up monitoring for instance {instance_id}")
            
        return True
        
    except Exception as e:
        logger.error(f"Error setting up EC2 monitoring: {str(e)}")
        return False
def get_config(config, ssm_client, sns_topic_arn_parameter_name):
    default_config = {
        'cpu_threshold': 80,
        'memory_threshold': 85,
        'disk_threshold': 85,
        'evaluation_periods': 2,
        'period': 300,
        'alarm_actions': []
    }

    # Fetch SNS topic ARN from SSM
    sns_response = ssm_client.get_parameter(
        Name=sns_topic_arn_parameter_name,
        WithDecryption=False
    )
    sns_topic_arn = sns_response['Parameter']['Value']

    # Merge default config with user config
    config = config or {}
    monitoring_config = {**default_config, **config}

    # Ensure alarm_actions is a list and includes the SNS topic ARN
    alarm_actions = monitoring_config.get('alarm_actions', [])
    if not isinstance(alarm_actions, list):
        alarm_actions = [alarm_actions]

    if sns_topic_arn not in alarm_actions:
        alarm_actions.append(sns_topic_arn)

    monitoring_config['alarm_actions'] = alarm_actions
    return monitoring_config
    
def lambda_handler(event, context):
    try:
        # Get parameters from the event
        body = json.loads(event.get('body', '{}'))
        ROLE_NAME = os.environ.get('ROLE_NAME')
        REGION = os.environ.get('REGION')
        account_id = body.get('account_id')
        role_arn = f"arn:aws:iam::{account_id}:role/{ROLE_NAME}"
        region = body.get('region') or REGION 
        config = body.get('config') or {}
        sns_topic_arn_parameter_name = "/devops-backend/snstopic/arn"
        
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
        sns_topic_arn_parameter_name = "/devops-backend/snstopic/arn"
        
        config=get_config(config,ssm_client,sns_topic_arn_parameter_name)

        
        
        instance_ids = body.get('instance_ids', [])
        if not instance_ids:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'instance_ids is required'})
            }
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
        success = setup_ec2_monitoring(cross_account_client, instances,config)
        
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