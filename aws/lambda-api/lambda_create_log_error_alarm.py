import boto3
import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

cloudwatch = boto3.client('cloudwatch')
logs = boto3.client('logs')

def lambda_handler(event, context):
    try:
        body = json.loads(event.get('body', '{}'))
        function_name = body['function_name']
        config = body.get('config', {})

        log_group = f"/aws/lambda/{function_name}"
        metric_namespace = "LambdaLogs"
        metric_name = f"{function_name}-log-errors"

        # Create metric filter in logs
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

        # Create alarm for the metric
        cloudwatch.put_metric_alarm(
            AlarmName=f"{function_name}-log-error-alarm",
            MetricName=metric_name,
            Namespace=metric_namespace,
            Statistic="Sum",
            Period=config.get('period', 60),
            EvaluationPeriods=config.get('evaluation_periods', 1),
            Threshold=config.get('log_error_threshold', 1),
            ComparisonOperator="GreaterThanThreshold",
            AlarmDescription="Errors found in Lambda logs",
            AlarmActions=config.get('alarm_actions', [])
        )

        logger.info(f"Log error alarm created for: {function_name}")
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Log error alarm created'})
        }

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
