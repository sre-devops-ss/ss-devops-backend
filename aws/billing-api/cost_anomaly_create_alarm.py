import boto3
import json

client = boto3.client('ce')

def lambda_handler(event, context):
    subscription_name = event.get('subscription_name', 'DefaultAnomalySub')
    monitor_arn = event['monitor_arn']
    sns_arn = event['sns_topic_arn']

    client.create_anomaly_subscription(
        AnomalySubscription={
            'SubscriptionName': subscription_name,
            'Threshold': 100,  # % above normal
            'Frequency': 'DAILY',
            'MonitorArnList': [monitor_arn],
            'Subscribers': [
                {
                    'Type': 'SNS',
                    'Address': sns_arn
                }
            ]
        }
    )

    return {
        'statusCode': 200,
        'body': json.dumps("Cost Anomaly subscription created")
    }
