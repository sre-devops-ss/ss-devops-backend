import json
import os
import boto3
import logging

from utils.cross_account import CrossAccountClient
from utils.authenticate_user_role import UserAuthenticator

logger = logging.getLogger()
logger.setLevel(logging.INFO)

headers= {
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Origin': f"*",
    'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
}

class NATAlarmCreator:
    def __init__(self, account_client):
        self.cloudwatch = account_client.get_client("cloudwatch")

    def create_alarm(self, nat_gateway_id, config):
        dimensions = [
            {'Name': 'NatGatewayId', 'Value': nat_gateway_id}
        ]
        try:
            self.cloudwatch.put_metric_alarm(
                AlarmName=f"{nat_gateway_id}-packet-drop",
                MetricName='PacketDropCount',
                Namespace='AWS/NATGateway',
                Statistic='Sum',
                Dimensions=dimensions,
                Period=config['period'],
                EvaluationPeriods=config['evaluation_periods'],
                Threshold=config['drop_threshold'],
                ComparisonOperator='GreaterThanThreshold',
                AlarmDescription="High packet drop on NAT Gateway",
                AlarmActions=config['alarm_actions']
            )
            logger.info(f"Alarm created for NAT Gateway {nat_gateway_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to create NAT alarm: {str(e)}")
            return False


def get_config(config, ssm_client, sns_topic_param_name):
    default_config = {
        'drop_threshold': 100,
        'period': 60,
        'evaluation_periods': 1,
        'alarm_actions': []
    }

    sns_arn = ssm_client.get_parameter(Name=sns_topic_param_name, WithDecryption=False)['Parameter']['Value']

    config = config or {}
    merged_config = {**default_config, **config}

    alarm_actions = merged_config.get('alarm_actions', [])
    if sns_arn not in alarm_actions:
        alarm_actions.append(sns_arn)

    merged_config['alarm_actions'] = alarm_actions
    return merged_config


def lambda_handler(event, context):
    try:
        body = json.loads(event.get('body', '{}'))
        nat_gateway_id = body.get('nat_gateway_id')
        account_id = body.get('account_id')
        region = body.get('region') or os.environ.get('REGION')
        config = body.get('config', {})

        role_name = os.environ.get("ROLE_NAME")
        if not all([nat_gateway_id, account_id, role_name]):
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Missing parameters'})
            }

        role_arn = f"arn:aws:iam::{account_id}:role/{role_name}"
        client = CrossAccountClient(account_id, role_arn, region)
        client.assume_role()

        ssm = client.get_client("ssm")
        sns_param = "/devops-backend/snstopic/arn"

        config = get_config(config, ssm, sns_param)

        creator = NATAlarmCreator(client)
        success = creator.create_alarm(nat_gateway_id, config)

        return {
            'statusCode': 200 if success else 500,
            'headers': headers,
            'body': json.dumps({'message': 'Alarm created' if success else 'Failed to create alarm'})
        }

    except Exception as e:
        logger.error(f"Unhandled exception: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': str(e)})
        }
