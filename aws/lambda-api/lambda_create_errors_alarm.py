import boto3
import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

cloudwatch = boto3.client('cloudwatch')

def lambda_handler(event, context):
    try:
        body = json.loads(event.get('body', '{}'))
        function_name = body['function_name']
        config = body.get('config', {})

        cloudwatch.put_metric_alarm(
            AlarmName=f"{function_name}-errors-alarm",
            MetricName="Errors",
            Namespace="AWS/Lambda",
            Statistic="Sum",
            Period=config.get('period', 60),
            EvaluationPeriods=config.get('evaluation_periods', 1),
            Threshold=config.get('error_threshold', 1),
            ComparisonOperator="GreaterThanThreshold",
            AlarmDescription="Lambda has invocation errors",
            Dimensions=[{"Name": "FunctionName", "Value": function_name}],
            AlarmActions=config.get('alarm_actions', [])
        )

        logger.info(f"Errors alarm created for: {function_name}")
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Errors alarm created'})
        }

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
