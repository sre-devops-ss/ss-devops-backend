import boto3
import json

cloudwatch = boto3.client('cloudwatch')

def create_alarm(api_name, stage, metric_name, threshold):
    alarm_name = f"{api_name}-{stage}-{metric_name}-alarm"
    dimensions = [
        {"Name": "ApiName", "Value": api_name},
        {"Name": "Stage", "Value": stage}
    ]
    cloudwatch.put_metric_alarm(
        AlarmName=alarm_name,
        ComparisonOperator='GreaterThanThreshold',
        EvaluationPeriods=1,
        MetricName=metric_name,
        Namespace='AWS/ApiGateway',
        Period=60,
        Statistic='Sum' if 'Error' in metric_name else 'Average',
        Threshold=threshold,
        ActionsEnabled=False,  # Change to True and add SNS actions if needed
        AlarmDescription=f'Alarm for {metric_name}',
        Dimensions=dimensions,
        Unit='Milliseconds' if metric_name == 'Latency' else 'Count'
    )
    return alarm_name

def list_alarms(prefix=None):
    response = cloudwatch.describe_alarms(
        AlarmNamePrefix=prefix or ''
    )
    alarms = response['MetricAlarms']
    return [
        {
            "AlarmName": alarm['AlarmName'],
            "MetricName": alarm['MetricName'],
            "Namespace": alarm['Namespace'],
            "StateValue": alarm['StateValue'],
            "Threshold": alarm['Threshold'],
            "EvaluationPeriods": alarm['EvaluationPeriods'],
            "Dimensions": alarm['Dimensions'],
            "Description": alarm.get('AlarmDescription', '')
        }
        for alarm in alarms
    ]

def lambda_handler(event, context):
    method = event.get("method")
    
    if method == "create":
        api_name = event["api_name"]
        stage = event["stage"]
        thresholds = {
            "4XXError": 5,
            "5XXError": 1,
            "Latency": 1000
        }
        created = []
        for metric, threshold in thresholds.items():
            alarm = create_alarm(api_name, stage, metric, threshold)
            created.append(alarm)
        return {
            'statusCode': 200,
            'body': json.dumps({"created_alarms": created})
        }

    elif method == "list":
        prefix = event.get("prefix")  # Optional
        alarms = list_alarms(prefix)
        return {
            'statusCode': 200,
            'body': json.dumps(alarms)
        }

    return {
        'statusCode': 400,
        'body': 'Invalid method'
    }
