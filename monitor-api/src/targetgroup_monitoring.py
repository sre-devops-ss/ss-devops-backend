import json
import boto3
from utils import get_cassandra_session, create_cloudwatch_alarm, store_alarm
import os

elbv2 = boto3.client('elbv2')
cloudwatch = boto3.client('cloudwatch')

def setup_targetgroup_monitoring(target_group_arn):
    """Set up monitoring for Target Group"""
    try:
        # Verify Target Group exists
        response = elbv2.describe_target_groups(
            TargetGroupArns=[target_group_arn]
        )
        
        if not response['TargetGroups']:
            raise Exception(f"Target Group {target_group_arn} not found")
        
        target_group = response['TargetGroups'][0]
        target_group_name = target_group['TargetGroupName']
        
        # Create CloudWatch alarms
        alarms = []
        
        # Response Time alarm
        response_time_alarm = create_cloudwatch_alarm(
            target_group_name,
            "TargetResponseTime",
            5.0,  # threshold in seconds
            "GreaterThanThreshold",
            2,  # evaluation periods
            300  # period
        )
        alarms.append(response_time_alarm)
        
        # Request Count alarm
        request_count_alarm = create_cloudwatch_alarm(
            target_group_name,
            "RequestCount",
            1000,  # threshold
            "GreaterThanThreshold",
            2,  # evaluation periods
            300  # period
        )
        alarms.append(request_count_alarm)
        
        # Unhealthy Host Count alarm
        unhealthy_host_alarm = create_cloudwatch_alarm(
            target_group_name,
            "UnHealthyHostCount",
            0,  # threshold
            "GreaterThanThreshold",
            1,  # evaluation periods
            60  # period
        )
        alarms.append(unhealthy_host_alarm)
        
        # 5xx Error alarm
        error_alarm = create_cloudwatch_alarm(
            target_group_name,
            "HTTPCode_Target_5XX_Count",
            10,  # threshold
            "GreaterThanThreshold",
            2,  # evaluation periods
            300  # period
        )
        alarms.append(error_alarm)
        
        # Store alarm information in Cassandra
        session = get_cassandra_session()
        for alarm_name in alarms:
            metric_name = alarm_name.split('-')[1]  # Extract metric name from alarm name
            threshold = 80  # Default threshold
            if metric_name == "TargetResponseTime":
                threshold = 5.0
            elif metric_name == "RequestCount":
                threshold = 1000
            elif metric_name == "UnHealthyHostCount":
                threshold = 0
            elif metric_name == "HTTPCode_Target_5XX_Count":
                threshold = 10
            
            store_alarm(
                session,
                alarm_name,
                'TargetGroup',
                target_group_name,
                metric_name,
                threshold,
                'OK',
                [os.environ['SNS_TOPIC_ARN']]
            )
        
        return alarms
        
    except Exception as e:
        print(f"Error setting up Target Group monitoring: {str(e)}")
        raise

def lambda_handler(event, context):
    try:
        # Get Target Group ARN from the event
        body = json.loads(event.get('body', '{}'))
        target_group_arn = body.get('target_group_arn')
        
        if not target_group_arn:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'target_group_arn is required'})
            }
        
        # Set up monitoring
        alarms = setup_targetgroup_monitoring(target_group_arn)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Target Group monitoring enabled successfully',
                'alarms': alarms
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        } 