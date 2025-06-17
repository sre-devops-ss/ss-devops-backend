import json
import boto3
import os
import logging
from datetime import datetime, timedelta
from utils.cross_account import CrossAccountClient

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def get_cloudwatch_client(account_id=None, role_name=None, region='us-east-1'):
    """
    Get CloudWatch client for either client account or cross-account
    
    Args:
        account_id (str): Target account ID for cross-account operations
        role_name (str): IAM role name for cross-account operations
        region (str): AWS region
    
    Returns:
        boto3.client: CloudWatch client
    """
    if account_id and role_name:
        # Cross-account operation
        role_arn = f"arn:aws:iam::{account_id}:role/{role_name}"
        cross_account_client = CrossAccountClient(account_id, role_arn, region)
        if not cross_account_client.assume_role():
            raise Exception("Failed to assume cross-account role")
        return cross_account_client.get_client('cloudwatch')
    else:
        # Client account operation
        return boto3.client('cloudwatch', region_name=region)

def get_ec2_client(account_id=None, role_name=None, region='us-east-1'):
    """
    Get EC2 client for either client account or cross-account
    
    Args:
        account_id (str): Target account ID for cross-account operations
        role_name (str): IAM role name for cross-account operations
        region (str): AWS region
    
    Returns:
        boto3.client: EC2 client
    """
    if account_id and role_name:
        # Cross-account operation
        role_arn = f"arn:aws:iam::{account_id}:role/{role_name}"
        cross_account_client = CrossAccountClient(account_id, role_arn, region)
        if not cross_account_client.assume_role():
            raise Exception("Failed to assume cross-account role")
        return cross_account_client.get_client('ec2')
    else:
        # Client account operation
        return boto3.client('ec2', region_name=region)

def fetch_instance_alarms(cloudwatch_client, instance_id, alarm_names=None):
    """
    Fetch all alarms for a specific EC2 instance
    
    Args:
        cloudwatch_client: CloudWatch client
        instance_id (str): EC2 instance ID
        alarm_names (list): Optional list of specific alarm names to fetch
    
    Returns:
        list: List of alarm objects
    """
    try:
        if alarm_names:
            # Fetch specific alarms
            response = cloudwatch_client.describe_alarms(AlarmNames=alarm_names)
        else:
            # Fetch all alarms and filter by instance
            response = cloudwatch_client.describe_alarms()
        
        alarms = response.get('MetricAlarms', [])
        
        # Filter alarms for the specific instance
        instance_alarms = []
        for alarm in alarms:
            if any(dim['Name'] == 'InstanceId' and dim['Value'] == instance_id 
                   for dim in alarm.get('Dimensions', [])):
                instance_alarms.append(alarm)
        
        return instance_alarms
    except Exception as e:
        logger.error(f"Error fetching alarms for instance {instance_id}: {str(e)}")
        return []

def fetch_alarm_history(cloudwatch_client, alarm_name, start_time=None, end_time=None):
    """
    Fetch alarm history for a specific alarm
    
    Args:
        cloudwatch_client: CloudWatch client
        alarm_name (str): Alarm name
        start_time (datetime): Start time for history
        end_time (datetime): End time for history
    
    Returns:
        list: List of alarm history items
    """
    try:
        params = {
            'AlarmName': alarm_name,
            'HistoryItemType': 'StateUpdate'
        }
        
        if start_time:
            params['StartDate'] = start_time
        if end_time:
            params['EndDate'] = end_time
        
        response = cloudwatch_client.describe_alarm_history(**params)
        return response.get('AlarmHistoryItems', [])
    except Exception as e:
        logger.error(f"Error fetching alarm history for {alarm_name}: {str(e)}")
        return []

def get_instance_details(ec2_client, instance_id):
    """
    Get EC2 instance details
    
    Args:
        ec2_client: EC2 client
        instance_id (str): EC2 instance ID
    
    Returns:
        dict: Instance details
    """
    try:
        response = ec2_client.describe_instances(InstanceIds=[instance_id])
        if response['Reservations']:
            instance = response['Reservations'][0]['Instances'][0]
            return {
                'instance_id': instance['InstanceId'],
                'instance_type': instance['InstanceType'],
                'state': instance['State']['Name'],
                'launch_time': instance['LaunchTime'].isoformat(),
                'tags': {tag['Key']: tag['Value'] for tag in instance.get('Tags', [])}
            }
        return None
    except Exception as e:
        logger.error(f"Error getting instance details for {instance_id}: {str(e)}")
        return None

def format_alarm_data(alarm, instance_details=None):
    """
    Format alarm data for response
    
    Args:
        alarm (dict): Raw alarm data from CloudWatch
        instance_details (dict): Optional instance details
    
    Returns:
        dict: Formatted alarm data
    """
    return {
        'alarm_name': alarm['AlarmName'],
        'alarm_arn': alarm['AlarmARN'],
        'alarm_description': alarm.get('AlarmDescription', ''),
        'metric_name': alarm['MetricName'],
        'namespace': alarm['Namespace'],
        'dimensions': alarm.get('Dimensions', []),
        'threshold': alarm['Threshold'],
        'comparison_operator': alarm['ComparisonOperator'],
        'evaluation_periods': alarm['EvaluationPeriods'],
        'period': alarm['Period'],
        'statistic': alarm['Statistic'],
        'state_value': alarm['StateValue'],
        'state_reason': alarm.get('StateReason', ''),
        'state_reason_data': alarm.get('StateReasonData', ''),
        'state_updated_timestamp': alarm['StateUpdatedTimestamp'].isoformat(),
        'actions_enabled': alarm['ActionsEnabled'],
        'alarm_actions': alarm.get('AlarmActions', []),
        'ok_actions': alarm.get('OKActions', []),
        'insufficient_data_actions': alarm.get('InsufficientDataActions', []),
        'instance_details': instance_details
    }

def validate_time_range(start_time, end_time):
    """
    Validate and parse time range parameters
    
    Args:
        start_time (str): Start time string
        end_time (str): End time string
    
    Returns:
        tuple: (start_datetime, end_datetime)
    """
    try:
        if start_time:
            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        else:
            start_dt = datetime.utcnow() - timedelta(days=7)  # Default to last 7 days
        
        if end_time:
            end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
        else:
            end_dt = datetime.utcnow()
        
        # Ensure start_time is before end_time
        if start_dt >= end_dt:
            raise ValueError("Start time must be before end time")
        
        # Limit time range to 90 days for alarm history
        if (end_dt - start_dt) > timedelta(days=90):
            raise ValueError("Time range cannot exceed 90 days")
        
        return start_dt, end_dt
    except Exception as e:
        raise ValueError(f"Invalid time format: {str(e)}")

def lambda_handler(event, context):
    """
    Lambda handler for fetching EC2 alarms
    
    Expected event structure:
    {
        "account_id": "123456789012",  // Optional for cross-account
        "role_name": "EC2CrossAccountMetricsRole",  // Optional for cross-account
        "instance_id": "i-1234567890abcdef0",
        "region": "us-east-1",
        "start_time": "2024-01-01T00:00:00",  // Optional, for alarm history
        "end_time": "2024-01-01T23:59:59",    // Optional, for alarm history
        "include_history": true,               // Optional, include alarm history
        "alarm_names": ["alarm1", "alarm2"]    // Optional, specific alarms to fetch
    }
    """
    try:
        # Parse request body
        if event.get('httpMethod') == 'POST':
            body = json.loads(event.get('body', '{}'))
        else:
            # For GET requests, parse query parameters
            body = event.get('queryStringParameters', {}) or {}
        
        # Extract parameters
        account_id = body.get('account_id')
        role_name = body.get('role_name') or os.environ.get('ROLE_NAME')
        instance_id = body.get('instance_id')
        region = body.get('region', 'us-east-1')
        start_time = body.get('start_time')
        end_time = body.get('end_time')
        include_history = body.get('include_history', 'false').lower() == 'true'
        alarm_names = body.get('alarm_names', [])
        
        # Convert alarm_names to list if it's a string
        if isinstance(alarm_names, str):
            alarm_names = [alarm_names] if alarm_names else []
        
        # Validate required parameters
        if not instance_id:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Missing required parameter: instance_id'
                })
            }
        
        # Validate time range if provided
        start_dt = None
        end_dt = None
        if start_time or end_time:
            try:
                start_dt, end_dt = validate_time_range(start_time, end_time)
            except ValueError as e:
                return {
                    'statusCode': 400,
                    'body': json.dumps({
                        'error': str(e)
                    })
                }
        
        # Get AWS clients
        try:
            cloudwatch_client = get_cloudwatch_client(account_id, role_name, region)
            ec2_client = get_ec2_client(account_id, role_name, region)
        except Exception as e:
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'error': f'Failed to get AWS clients: {str(e)}'
                })
            }
        
        # Get instance details
        instance_details = get_instance_details(ec2_client, instance_id)
        
        # Fetch alarms
        alarms = fetch_instance_alarms(cloudwatch_client, instance_id, alarm_names if alarm_names else None)
        
        # Format alarm data
        formatted_alarms = []
        for alarm in alarms:
            alarm_data = format_alarm_data(alarm, instance_details)
            
            # Include alarm history if requested
            if include_history and start_dt and end_dt:
                history = fetch_alarm_history(
                    cloudwatch_client, 
                    alarm['AlarmName'], 
                    start_dt, 
                    end_dt
                )
                alarm_data['history'] = [
                    {
                        'timestamp': item['Timestamp'].isoformat(),
                        'history_item_type': item['HistoryItemType'],
                        'history_summary': item['HistorySummary'],
                        'history_data': item.get('HistoryData', '')
                    }
                    for item in history
                ]
            
            formatted_alarms.append(alarm_data)
        
        # Prepare response
        response_data = {
            'instance_id': instance_id,
            'account_id': account_id,
            'region': region,
            'alarms_count': len(formatted_alarms),
            'alarms': formatted_alarms
        }
        
        if start_dt and end_dt:
            response_data['start_time'] = start_dt.isoformat()
            response_data['end_time'] = end_dt.isoformat()
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
            },
            'body': json.dumps(response_data, default=str)
        }
        
    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
            },
            'body': json.dumps({
                'error': f'Internal server error: {str(e)}'
            })
        } 