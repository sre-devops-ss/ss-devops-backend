import boto3
import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

cloudwatch = boto3.client("cloudwatch")

def create_scaling_alarm(asg_name, config):
    dimensions = [{'Name': 'AutoScalingGroupName', 'Value': asg_name}]
    cloudwatch.put_metric_alarm(
        AlarmName=f"{asg_name}-scaling-activity",
        MetricName="GroupInServiceInstances",
        Namespace="AWS/AutoScaling",
        Statistic="Average",
        Period=config['period'],
        EvaluationPeriods=config['evaluation_periods'],
        Threshold=config['scaling_threshold'],
        ComparisonOperator="LessThanThreshold",
        AlarmDescription="ASG may be under-scaled",
        Dimensions=dimensions,
        AlarmActions=config['alarm_actions']
    )
    logger.info(f"Scaling alarm created for ASG: {asg_name}")


def lambda_handler(event, context):
    try:
        body = json.loads(event.get('body', '{}'))
        asg_name = body['asg_name']
        config = {
            'scaling_threshold': body.get('scaling_threshold', 1),
            'period': body.get('period', 60),
            'evaluation_periods': body.get('evaluation_periods', 1),
            'alarm_actions': body.get('alarm_actions', [])
        }

        create_scaling_alarm(asg_name, config)

        return {'statusCode': 200, 'body': json.dumps({'message': 'Scaling alarm created'})}

    except Exception as e:
        logger.error(str(e))
        return {'statusCode': 500, 'body': json.dumps({'error': str(e)})}
