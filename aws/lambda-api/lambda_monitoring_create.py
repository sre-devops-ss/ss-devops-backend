import boto3
import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

cloudwatch = boto3.client('cloudwatch')
logs = boto3.client('logs')

def create_lambda_alarms(function_name, region, config):
    log_group = f"/aws/lambda/{function_name}"
    
    cloudwatch.put_metric_alarm(
        AlarmName=f"{function_name}-errors-alarm",
        MetricName="Errors",
        Namespace="AWS/Lambda",
        Statistic="Sum",
        Period=config['period'],
        EvaluationPeriods=config['evaluation_periods'],
        Threshold=config['error_threshold'],
        ComparisonOperator="GreaterThanThreshold",
        AlarmDescription="Lambda has invocation errors",
        Dimensions=[{"Name": "FunctionName", "Value": function_name}],
        AlarmActions=config['alarm_actions']
    )

    cloudwatch.put_metric_alarm(
        AlarmName=f"{function_name}-duration-alarm",
        MetricName="Duration",
        Namespace="AWS/Lambda",
        Statistic="Average",
        Period=config['period'],
        EvaluationPeriods=config['evaluation_periods'],
        Threshold=config['duration_threshold'],
        ComparisonOperator="GreaterThanThreshold",
        AlarmDescription="Lambda execution duration is too high",
        Dimensions=[{"Name": "FunctionName", "Value": function_name}],
        AlarmActions=config['alarm_actions']
    )

    metric_namespace = "LambdaLogs"
    metric_name = f"{function_name}-log-errors"

    logs.put_metric_filter(
        logGroupName=log_group,
        filterName=f"{function_name}-log-error-filter",
        filterPattern='?"ERROR"',
        metricTransformations=[{
            'metricName': metric_name,
            'metricNamespace': metric_namespace,
            'metricValue': '1'
        }]
    )

    cloudwatch.put_metric_alarm(
        AlarmName=f"{function_name}-log-error-alarm",
        MetricName=metric_name,
        Namespace=metric_namespace,
        Statistic="Sum",
        Period=config['period'],
        EvaluationPeriods=config['evaluation_periods'],
        Threshold=config['log_error_threshold'],
        ComparisonOperator="GreaterThanThreshold",
        AlarmDescription="Errors found in Lambda logs",
        AlarmActions=config['alarm_actions']
    )

    logger.info(f"Alarms created for Lambda function: {function_name}")


def lambda_handler(event, context):
    try:
        body = json.loads(event.get('body', '{}'))
        function_name = body['function_name']
        region = body.get('region', 'us-east-1')
        config = body.get('config', {})

        default_config = {
            'error_threshold': 1,
            'duration_threshold': 3000,  # ms
            'log_error_threshold': 1,
            'period': 60,
            'evaluation_periods': 1,
            'alarm_actions': []
        }

        for key in default_config:
            if key not in config:
                config[key] = default_config[key]

        create_lambda_alarms(function_name, region, config)

        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Alarms created'})
        }

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
