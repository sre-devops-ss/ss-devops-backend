import json
import os
import logging
import boto3

from utils.cross_account import CrossAccountClient

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class ECSAlarmCreator:
    def __init__(self, account_client):
        self.cloudwatch = account_client.get_client("cloudwatch")

    def create_alarms(self, cluster_name, service_name, service_details, config=None):
        """Create CloudWatch alarms for ECS service metrics"""
        try:
            monitoring_config =config or {}

            dimensions = [
                {'Name': 'ClusterName', 'Value': cluster_name},
                {'Name': 'ServiceName', 'Value': service_name}
            ]

            self.cloudwatch.put_metric_alarm(
                AlarmName=f"{cluster_name}-{service_name}-cpu-utilization",
                MetricName='CPUUtilization',
                Namespace='AWS/ECS',
                Statistic='Average',
                Dimensions=dimensions,
                Period=monitoring_config['period'],
                EvaluationPeriods=monitoring_config['evaluation_periods'],
                Threshold=monitoring_config['cpu_threshold'],
                ComparisonOperator='GreaterThanThreshold',
                AlarmDescription="High CPU utilization",
                AlarmActions=monitoring_config['alarm_actions']
            )

            self.cloudwatch.put_metric_alarm(
                AlarmName=f"{cluster_name}-{service_name}-memory-utilization",
                MetricName='MemoryUtilization',
                Namespace='AWS/ECS',
                Statistic='Average',
                Dimensions=dimensions,
                Period=monitoring_config['period'],
                EvaluationPeriods=monitoring_config['evaluation_periods'],
                Threshold=monitoring_config['memory_threshold'],
                ComparisonOperator='GreaterThanThreshold',
                AlarmDescription="High memory utilization",
                AlarmActions=monitoring_config['alarm_actions']
            )

            self.cloudwatch.put_metric_alarm(
                AlarmName=f"{cluster_name}-{service_name}-running-tasks",
                MetricName='RunningTaskCount',
                Namespace='AWS/ECS',
                Statistic='Average',
                Dimensions=dimensions,
                Period=monitoring_config['period'],
                EvaluationPeriods=monitoring_config['evaluation_periods'],
                Threshold=service_details['desiredCount'],
                ComparisonOperator='LessThanThreshold',
                AlarmDescription="Running task count is below desired",
                AlarmActions=monitoring_config['alarm_actions']
            )

            logger.info(f"Alarms created for ECS service {service_name} in cluster {cluster_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to create alarms: {str(e)}")
    
            return False


def get_config(config, ssm_client, sns_topic_arn_parameter_name):
    default_config = {
        'cpu_threshold': 80,
        'memory_threshold': 85,
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
        body = json.loads(event.get('body', '{}'))
        cluster_name = body.get('cluster_name')
        service_name = body.get('service_name')
        account_id = body.get('account_id')
        region = body.get('region') or os.environ.get('REGION')
        config = body.get('config', {})

        role_name = os.environ.get("ROLE_NAME")
        if not all([cluster_name, service_name, account_id, role_name]):
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Missing required parameters'})
            }

        role_arn = f"arn:aws:iam::{account_id}:role/{role_name}"
        client = CrossAccountClient(account_id, role_arn, region)
        client.assume_role()
        ecs = client.get_client("ecs")
        ssm = client.get_client("ssm")
        sns_topic_arn_parameter_name = "/devops-backend/snstopic/arn"

        config=get_config(config,ssm,sns_topic_arn_parameter_name)
        response = ecs.describe_services(cluster=cluster_name, services=[service_name])
        service_details = response['services'][0]

        ecs_alarm_creator = ECSAlarmCreator(client)
        success = ecs_alarm_creator.create_alarms(cluster_name, service_name, service_details, config)

        return {
            'statusCode': 200 if success else 500,
            'body': json.dumps({
                'message': 'Alarms created' if success else 'Alarm creation failed'
            })
        }

    except Exception as e:
        logger.error(f"Unhandled exception: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
