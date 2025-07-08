import boto3
import json
from datetime import date, timedelta

ce = boto3.client('ce')
cloudwatch = boto3.client('cloudwatch')

def lambda_handler(event, context):
    today = date.today()
    start = today.replace(day=1).isoformat()
    end = today.isoformat()

    result = ce.get_cost_and_usage(
        TimePeriod={'Start': start, 'End': end},
        Granularity='MONTHLY',
        Metrics=['UnblendedCost'],
        Filter={
            'Dimensions': {
                'Key': 'SERVICE',
                'Values': ['Amazon Elastic Compute Cloud - Data Transfer']
            }
        }
    )

    amount = float(result['ResultsByTime'][0]['Total']['UnblendedCost']['Amount'])
    print(f"Data Transfer Cost So Far: ${amount}")

    # Publish to CW custom metric
    cloudwatch.put_metric_data(
        Namespace='Billing/DataTransfer',
        MetricData=[
            {
                'MetricName': 'BandwidthCost',
                'Value': amount,
                'Unit': 'None'
            }
        ]
    )

    return {
        'statusCode': 200,
        'body': json.dumps(f"Data transfer cost this month: ${amount}")
    }
