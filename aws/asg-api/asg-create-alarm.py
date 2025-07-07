import boto3
import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

cloudwatch = boto3.client("cloudwatch")

def create_instance_alarms(instance_id, config):
    dimensions = [{'Name': 'InstanceId', 'Value': instance_id}]

    # 1. CPU Utilization Alarm
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

    # 2. Memory Utilization Alarm (via CloudWatch Agent)
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

    logger.info(f"Alarms created for instance: {instance_id}")


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


def lambda_handler(event, context):
    try:
        body = json.loads(event.get('body', '{}'))
        event_type = body.get('event_type')  # "instance", "scaling"
        config = body.get('config', {})
        default_config = {
            'cpu_threshold': 80,
            'memory_threshold': 85,
            'scaling_threshold': 1,
            'period': 60,
            'evaluation_periods': 1,
            'alarm_actions': []  # SNS ARNs
        }
        config = {**default_config, **config}

        if event_type == "instance":
            instance_ids = body.get('instance_ids', [])
            for instance_id in instance_ids:
                create_instance_alarms(instance_id, config)

        elif event_type == "scaling":
            asg_name = body.get('asg_name')
            create_scaling_alarm(asg_name, config)

        else:
            return {'statusCode': 400, 'body': 'Invalid event_type'}

        return {'statusCode': 200, 'body': json.dumps({'message': 'Alarms created'})}

    except Exception as e:
        logger.error(str(e))
        return {'statusCode': 500, 'body': json.dumps({'error': str(e)})}
