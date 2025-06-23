import json

import os
from datetime import datetime
from utils.cloudwatch_client import CloudWatchMonitor
def parse_time(ts, fallback):
    try:
        return datetime.strptime(ts, '%Y-%m-%dT%H:%M:%S')
    except:
        return fallback

def lambda_handler(event, context):
    try:
        params = json.loads(event.get('body', '{}')) if event.get('body') else event.get('queryStringParameters')

        role_name = os.environ['ROLE_NAME']
        region = os.environ.get('REGION', 'us-east-1')
        account_id = params['account_id']
        instance_id = params['instance_id']
        metric_name = params['metric_name']
        namespace = params.get('namespace', 'AWS/EC2') 
        stat=params.get('stat','Average')
        period=int(params.get('period',60))
        start_time = params.get('start_time') 
        end_time = params.get('end_time') 
        next_token = params.get('next_token')

        monitor = CloudWatchMonitor(account_id, region, role_name)

        result = monitor.get_metrics(instance_id, metric_name, namespace, stat,
                                     period, start_time, end_time, next_token)
        created = False
        if not result:
            return {
                'statusCode': 404,
                'body': json.dumps({
                   'message': 'Metric not found'
                }, default=str)
            }
            

        return {
            'statusCode': 200,
            'body': json.dumps({
                'metric': result['metric'],
                'created': created,
                'next_token': result.get('next_token')
            }, default=str)
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }