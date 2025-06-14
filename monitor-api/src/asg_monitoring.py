import json
import os

import boto3
import time
from utils.cross_account import CrossAccountClient


autoscaling= boto3.client('autoscaling')
cloudwatch=boto3.client('cloudwatch')
ssm=boto3.client('ssm')
ec2=boto3.client('ec2')
# Initialize AWS clients

class AsgMonitoring:
    def __init__(self, account):
        
        autoscaling = account.get_client('autoscaling')
        cloudwatch = account.get_client('cloudwatch')
        ssm = account.get_client('ssm')
        ec2 = account.get_client('ec2')
        

    def get_instance_os(self,instance_id):
        """Detect the operating system of the instance"""
        try:
            # Get instance details
            response = ec2.describe_instances(InstanceIds=[instance_id])
            image_id = response['Reservations'][0]['Instances'][0]['ImageId']
    
            # Get AMI details
            ami_response = ec2.describe_images(ImageIds=[image_id])
            platform_details = ami_response['Images'][0].get('PlatformDetails', '').lower()
    
            if 'ubuntu' in platform_details:
                return 'ubuntu'
            elif 'alma' in platform_details or 'rhel' in platform_details or 'amazon linux' in platform_details:
                return 'rhel'
            else:
                raise Exception(f"Unsupported platform: {platform_details}")
    
        except Exception as e:
            print(f"Error detecting OS: {str(e)}")
            raise

    def check_cloudwatch_agent(self,instance_id):
        """Check if CloudWatch agent is installed and running on the instance"""
        try:
            # Check if agent is installed
            response = ssm.send_command(
                InstanceIds=[instance_id],
                DocumentName="AWS-RunShellScript",
                Parameters={
                    'commands': ['systemctl status amazon-cloudwatch-agent']
                }
            )
    
            command_id = response['Command']['CommandId']
    
            # Wait for command to complete
            time.sleep(5)
    
            # Get command output
            output = ssm.get_command_invocation(
                CommandId=command_id,
                InstanceId=instance_id
            )
    
            return 'active (running)' in output['StandardOutputContent']
        except Exception as e:
            print(f"Error checking CloudWatch agent: {str(e)}")
            return False
    
    def install_cloudwatch_agent(self,instance_id):
        """Install and configure CloudWatch agent on the instance based on OS type"""
        try:
            os_type = self.get_instance_os(instance_id)
    
            if os_type == 'ubuntu':
                install_commands = [
                    'wget https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb',
                    'dpkg -i amazon-cloudwatch-agent.deb',
                    'mkdir -p /opt/aws/amazon-cloudwatch-agent/etc/',
                    'cat > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json << EOF\n'
                    '{\n'
                    '    "metrics": {\n'
                    '        "metrics_collected": {\n'
                    '            "mem": {\n'
                    '                "measurement": ["mem_used_percent"]\n'
                    '            }\n'
                    '        }\n'
                    '    }\n'
                    '}\n'
                    'EOF',
                    'systemctl enable amazon-cloudwatch-agent',
                    'systemctl start amazon-cloudwatch-agent'
                ]
            else:  # RHEL/AlmaLinux/Amazon Linux
                install_commands = [
                    'yum install -y amazon-cloudwatch-agent',
                    'mkdir -p /opt/aws/amazon-cloudwatch-agent/etc/',
                    'cat > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json << EOF\n'
                    '{\n'
                    '    "metrics": {\n'
                    '        "metrics_collected": {\n'
                    '            "mem": {\n'
                    '                "measurement": ["mem_used_percent"]\n'
                    '            }\n'
                    '        }\n'
                    '    }\n'
                    '}\n'
                    'EOF',
                    'systemctl enable amazon-cloudwatch-agent',
                    'systemctl start amazon-cloudwatch-agent'
                ]
    
            # Install CloudWatch agent
            ssm.send_command(
                InstanceIds=[instance_id],
                DocumentName="AWS-RunShellScript",
                Parameters={
                    'commands': install_commands
                }
            )
    
            # Wait for installation to complete
            time.sleep(30)
    
            # Verify installation
            if not self.check_cloudwatch_agent(instance_id):
                raise Exception("CloudWatch agent installation verification failed")
    
            return True
        except Exception as e:
            print(f"Error installing CloudWatch agent: {str(e)}")
            return False
    
    def setup_asg_monitoring(self,asg_name):
        """Set up monitoring for Auto Scaling Group"""
        try:
            # Verify ASG exists
            response = autoscaling.describe_auto_scaling_groups(
                AutoScalingGroupNames=[asg_name]
            )
    
            if not response['AutoScalingGroups']:
                raise Exception(f"Auto Scaling Group {asg_name} not found")
    
            asg = response['AutoScalingGroups'][0]
    
            # Get ASG instances
            instances = asg['Instances']
    
            for instance in instances:
                instance_id = instance['InstanceId']
    
                # Check and install CloudWatch agent if needed
                if not self.check_cloudwatch_agent(instance_id):
                    print(f"Installing CloudWatch agent on instance {instance_id}")
                    if not self.install_cloudwatch_agent(instance_id):
                        print(f"Failed to install CloudWatch agent on instance {instance_id}")
                        continue
    
                # Create CPU Utilization alarm
                cpu_alarm_name = f"{asg_name}-{instance_id}-cpu-utilization"
                cloudwatch.put_metric_alarm(
                    AlarmName=cpu_alarm_name,
                    AlarmDescription=f"CPU utilization alarm for instance {instance_id} in ASG {asg_name}",
                    MetricName="CPUUtilization",
                    Namespace="AWS/EC2",
                    Statistic="Average",
                    Period=300,
                    EvaluationPeriods=2,
                    Threshold=80.0,
                    ComparisonOperator="GreaterThanThreshold",
                    Dimensions=[
                        {
                            'Name': 'InstanceId',
                            'Value': instance_id
                        }
                    ],
                    AlarmActions=[
                        f"arn:aws:sns:{boto3.session.Session().region_name}:{boto3.client('sts').get_caller_identity()['Account']}:asg-alerts"
                    ]
                )
    
                # Create Memory Utilization alarm
                memory_alarm_name = f"{asg_name}-{instance_id}-memory-utilization"
                cloudwatch.put_metric_alarm(
                    AlarmName=memory_alarm_name,
                    AlarmDescription=f"Memory utilization alarm for instance {instance_id} in ASG {asg_name}",
                    MetricName="mem_used_percent",
                    Namespace="CWAgent",
                    Statistic="Average",
                    Period=300,
                    EvaluationPeriods=2,
                    Threshold=80.0,
                    ComparisonOperator="GreaterThanThreshold",
                    Dimensions=[
                        {
                            'Name': 'InstanceId',
                            'Value': instance_id
                        }
                    ],
                    AlarmActions=[
                        f"arn:aws:sns:{boto3.session.Session().region_name}:{boto3.client('sts').get_caller_identity()['Account']}:asg-alerts"
                    ]
                )
    
             
            
    
        except Exception as e:
            print(f"Error setting up ASG monitoring: {str(e)}")
            raise
    
    def setup_cloudtrail_monitoring(self,asg_name):
        """Set up CloudTrail event monitoring for ASG scaling events"""
        try:
            # Create CloudWatch event rule for ASG scaling events
            events = boto3.client('events')
    
            rule_name = f"{asg_name}-scaling-events"
            events.put_rule(
                Name=rule_name,
                EventPattern=json.dumps({
                    "source": ["aws.autoscaling"],
                    "detail-type": ["AWS API Call via CloudTrail"],
                    "detail": {
                        "eventSource": ["autoscaling.amazonaws.com"],
                        "eventName": ["CreateAutoScalingGroup", "UpdateAutoScalingGroup", "DeleteAutoScalingGroup"]
                    }
                }),
                State="ENABLED"
            )
    
            # Add target to the rule
            events.put_targets(
                Rule=rule_name,
                Targets=[
                    {
                        'Id': f"{asg_name}-scaling-target",
                        'Arn': f"arn:aws:lambda:{boto3.session.Session().region_name}:{boto3.client('sts').get_caller_identity()['Account']}:function:asg-scaling-handler"
                    }
                ]
            )
    
        except Exception as e:
            print(f"Error setting up CloudTrail monitoring: {str(e)}")
            raise

def lambda_handler(event, context):
    try:
        # Get ASG name from event


        body = json.loads(event.get('body', '{}'))
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
    
        asg_name = body.get('asg_name')
        
        asgClient=AsgMonitoring(cross_account_client)
        # Set up monitoring
        asgClient.asgsetup_asg_monitoring(asg_name)
        asgClient.setup_cloudtrail_monitoring(asg_name)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f'Successfully set up monitoring for ASG {asg_name}'
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        } 