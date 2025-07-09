import boto3
import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

cloudwatch = boto3.client("cloudwatch")

def create_cpu_alarm(instance_id, config):
    dimensions = [{'Name': 'InstanceId', 'Value': instance_id}]
    cloudwatch.put_metric_alarm(
        AlarmName=f"{instance_id}-cpu-utilization",
        MetricName="CPUUtilization",
        Namespace="AWS/EC2",
        Statistic="Average",
        Period=config['period'],
        EvaluationPeriods=config['evaluation_periods'],
        Threshold=config['cpu_threshold'],
        ComparisonOperator="GreaterThanThreshold",
        AlarmDescription="High CPU utilization",
        Dimensions=dimensions,
        AlarmActions=config['alarm_actions']
    )
    logger.info(f"CPU alarm created for instance: {instance_id}")


def lambda_handler(event, context):
    try:
        body = json.loads(event.get('body', '{}'))
        instance_ids = body.get('instance_ids', [])
        config = {
            'cpu_threshold': body.get('cpu_threshold', 80),
            'period': body.get('period', 60),
            'evaluation_periods': body.get('evaluation_periods', 1),
            'alarm_actions': body.get('alarm_actions', [])
        }

        for instance_id in instance_ids:
            create_cpu_alarm(instance_id, config)

        return {'statusCode': 200, 'body': json.dumps({'message': 'CPU alarms created'})}

    except Exception as e:
        logger.error(str(e))
        return {'statusCode': 500, 'body': json.dumps({'error': str(e)})}
