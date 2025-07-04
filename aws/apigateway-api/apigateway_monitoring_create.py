import json
import os
import logging
import boto3

from utils.cross_account import CrossAccountClient

logger = logging.getLogger()
logger.setLevel(logging.INFO)

class APIGatewayAlarmCreator:
    def __init__(self, account_client):
        self.cloudwatch = account_client.get_client("cloudwatch")

    def create_alarms(self, api_name, stage, config=None):
        try:
            monitoring_config = config or {}
            dimensions = [
                {"Name": "ApiName", "Value": api_name},
                {"Name": "Stage", "Value": stage}
            ]

            self.cloudwatch.put_metric_alarm(
                AlarmName=f"{api_name}-{stage}-4xx-errors",
                MetricName="4XXError",
                Namespace="AWS/ApiGateway",
                Statistic="Sum",
                Dimensions=dimensions,
                Period=monitoring_config['period'],
                EvaluationPeriods=monitoring_config['evaluation_periods'],
                Threshold=monitoring_config['4xx_threshold'],
                ComparisonOperator="GreaterThanThreshold",
                AlarmDescription="Too many 4XX errors",
                AlarmActions=monitoring_config['alarm_actions']
            )

            self.cloudwatch.put_metric_alarm(
                AlarmName=f"{api_name}-{stage}-5xx-errors",
                MetricName="5XXError",
                Namespace="AWS/ApiGateway",
                Statistic="Sum",
                Dimensions=dimensions,
                Period=monitoring_config['period'],
                EvaluationPeriods=monitoring_config['evaluation_periods'],
                Threshold=monitoring_config['5xx_threshold'],
                ComparisonOperator="GreaterThanThreshold",
                AlarmDescription="Too many 5XX errors",
                AlarmActions=monitoring_config['alarm_actions']
            )

            self.cloudwatch.put_metric_alarm(
                AlarmName=f"{api_name}-{stage}-latency",
                MetricName="Latency",
                Namespace="AWS/ApiGateway",
                Statistic="Average",
                Dimensions=dimensions,
                Period=monitoring_config['period'],
                EvaluationPeriods=monitoring_config['evaluation_periods'],
                Threshold=monitoring_config['latency_threshold'],
                ComparisonOperator="GreaterThanThreshold",
                AlarmDescription="API latency too high",
                Unit="Milliseconds",
                AlarmActions=monitoring_config['alarm_actions']
            )

            logger.info(f"API Gateway alarms created for {api_name} - {stage}")
            return True

        except Exception as e:
            logger.error(f"Failed to create API Gateway alarms: {str(e)}")
            return False


def get_config(config, ssm_client, sns_topic_arn_parameter_name):
    default_config = {
        '4xx_threshold': 10,
        '5xx_threshold': 1,
        'latency_threshold': 1000,  # ms
        'evaluation_periods': 1,
        'period': 60,
        'alarm_actions': []
    }

    sns_response = ssm_client.get_parameter(
        Name=sns_topic_arn_parameter_name,
        WithDecryption=False
    )
    sns_topic_arn = sns_response['Parameter']['Value']

    config = config or {}
    monitoring_config = {**default_config, **config}

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
        api_name = body.get('api_name')
        stage = body.get('stage')
        account_id = body.get('account_id')
        region = body.get('region') or os.environ.get('REGION')
        config = body.get('config', {})

        role_name = os.environ.get("ROLE_NAME")
        if not all([api_name, stage, account_id, role_name]):
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Missing required parameters'})
            }

        role_arn = f"arn:aws:iam::{account_id}:role/{role_name}"
        client = CrossAccountClient(account_id, role_arn, region)
        client.assume_role()
        ssm = client.get_client("ssm")
        sns_topic_arn_parameter_name = "/devops-backend/snstopic/arn"

        config = get_config(config, ssm, sns_topic_arn_parameter_name)

        api_alarm_creator = APIGatewayAlarmCreator(client)
        success = api_alarm_creator.create_alarms(api_name, stage, config)

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
