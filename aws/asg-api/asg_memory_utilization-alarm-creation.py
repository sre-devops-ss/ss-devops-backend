import boto3
import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

cloudwatch = boto3.client("cloudwatch")

def create_memory_alarm(instance_id, config):
    dimensions = [{'Name': 'InstanceId', 'Value': instance_id}]
    cloudwatch.put_metric_alarm(
        AlarmName=f"{instance_id}-memory-utilization",
        MetricName="mem_used_percent",
        Namespace="CWAgent",
        Statistic="Average",
        Period=config['period'],
        EvaluationPeriods=config['evaluation_periods'],
        Threshold=config['memory_threshold'],
        ComparisonOperator="GreaterThanThreshold",
        AlarmDescription="High memory utilization",
        Dimensions=dimensions,
        AlarmActions=config['alarm_actions']
    )
    logger.info(f"Memory alarm created for instance: {instance_id}")


def lambda_handler(event, context):
    try:
        body = json.loads(event.get('body', '{}'))
        instance_ids = body.get('instance_ids', [])
        config = {
            'memory_threshold': body.get('memory_threshold', 85),
            'period': body.get('period', 60),
            'evaluation_periods': body.get('evaluation_periods', 1),
            'alarm_actions': body.get('alarm_actions', [])
        }

        for instance_id in instance_ids:
            create_memory_alarm(instance_id, config)

        return {'statusCode': 200, 'body': json.dumps({'message': 'Memory alarms created'})}

    except Exception as e:
        logger.error(str(e))
        return {'statusCode': 500, 'body': json.dumps({'error': str(e)})}
