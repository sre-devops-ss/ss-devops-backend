import boto3
import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

cloudwatch = boto3.client('cloudwatch')

headers= {
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Origin': f"*",
    'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
}
def create_tg_alarms(lb_name, tg_name, config):
    dimensions = [
        {"Name": "TargetGroup", "Value": tg_name},
        {"Name": "LoadBalancer", "Value": lb_name}
    ]

    # 1. Target Response Time
    cloudwatch.put_metric_alarm(
        AlarmName=f"{tg_name}-response-time",
        Namespace="AWS/ApplicationELB",
        MetricName="TargetResponseTime",
        Dimensions=dimensions,
        Statistic="Average",
        Period=config['period'],
        EvaluationPeriods=config['evaluation_periods'],
        Threshold=config['response_time_threshold'],
        ComparisonOperator="GreaterThanThreshold",
        AlarmDescription="High response time from TG",
        AlarmActions=config['alarm_actions']
    )

    # 2. Request Count
    cloudwatch.put_metric_alarm(
        AlarmName=f"{tg_name}-request-count",
        Namespace="AWS/ApplicationELB",
        MetricName="RequestCount",
        Dimensions=dimensions,
        Statistic="Sum",
        Period=config['period'],
        EvaluationPeriods=config['evaluation_periods'],
        Threshold=config['request_count_threshold'],
        ComparisonOperator="GreaterThanThreshold",
        AlarmDescription="High number of requests",
        AlarmActions=config['alarm_actions']
    )

    # 3. Unhealthy Host Count
    cloudwatch.put_metric_alarm(
        AlarmName=f"{tg_name}-unhealthy-hosts",
        Namespace="AWS/ApplicationELB",
        MetricName="UnHealthyHostCount",
        Dimensions=dimensions,
        Statistic="Average",
        Period=config['period'],
        EvaluationPeriods=config['evaluation_periods'],
        Threshold=config['unhealthy_threshold'],
        ComparisonOperator="GreaterThanThreshold",
        AlarmDescription="Too many unhealthy targets",
        AlarmActions=config['alarm_actions']
    )

    # 4. 5xx Errors from Targets
    cloudwatch.put_metric_alarm(
        AlarmName=f"{tg_name}-5xx-errors",
        Namespace="AWS/ApplicationELB",
        MetricName="HTTPCode_Target_5XX_Count",
        Dimensions=dimensions,
        Statistic="Sum",
        Period=config['period'],
        EvaluationPeriods=config['evaluation_periods'],
        Threshold=config['target_5xx_threshold'],
        ComparisonOperator="GreaterThanThreshold",
        AlarmDescription="High 5XX errors from targets",
        AlarmActions=config['alarm_actions']
    )

    logger.info(f"Created 4 alarms for Target Group: {tg_name}")


def lambda_handler(event, context):
    try:
        body = json.loads(event.get('body', '{}'))

        lb_name = body['load_balancer_name']     
        tg_name = body['target_group_name']       
        config = body.get('config', {})

        default_config = {
            'response_time_threshold': 1.0,
            'request_count_threshold': 1000,
            'unhealthy_threshold': 1,
            'target_5xx_threshold': 10,
            'period': 60,
            'evaluation_periods': 1,
            'alarm_actions': []
        }

        for key, val in default_config.items():
            if key not in config:
                config[key] = val

        create_tg_alarms(lb_name, tg_name, config)

        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({'message': 'Target Group alarms created'})
        }

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': str(e)})
        }
