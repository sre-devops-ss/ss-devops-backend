import json
import boto3
import os
import logging
from datetime import datetime, timedelta
from utils.cross_account import CrossAccountClient

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Define the metrics to fetch
EC2_METRICS = [
    {
        "name": "CPUUtilization",
        "namespace": "AWS/EC2",
        "unit": "Percent",
        "description": "CPU utilization percentage"
    },
    {
        "name": "mem_used_percent",
        "namespace": "CWAgent",
        "unit": "Percent",
        "description": "Memory utilization percentage"
    },
    {
        "name": "disk_used_percent",
        "namespace": "CWAgent",
        "unit": "Percent",
        "description": "Disk utilization percentage"
    },
    {
        "name": "NetworkIn",
        "namespace": "AWS/EC2",
        "unit": "Bytes",
        "description": "Network bytes received"
    },
    {
        "name": "NetworkOut",
        "namespace": "AWS/EC2",
        "unit": "Bytes",
        "description": "Network bytes sent"
    },
    {
        "name": "DiskReadBytes",
        "namespace": "AWS/EC2",
        "unit": "Bytes",
        "description": "Disk read bytes"
    },
    {
        "name": "DiskWriteBytes",
        "namespace": "AWS/EC2",
        "unit": "Bytes",
        "description": "Disk write bytes"
    },
    {
        "name": "load1",
        "namespace": "CWAgent",
        "unit": "None",
        "description": "1-minute load average"
    },
    {
        "name": "load5",
        "namespace": "CWAgent",
        "unit": "None",
        "description": "5-minute load average"
    },
    {
        "name": "load15",
        "namespace": "CWAgent",
        "unit": "None",
        "description": "15-minute load average"
    }
]

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

def fetch_metric_data(cross_account_client, instance_id, metric_name, namespace, start_time, end_time, period=300):
    """
    Fetch metric data from CloudWatch
    
    Args:
        cloudwatch_client: CloudWatch client
        instance_id (str): EC2 instance ID
        metric_name (str): Metric name
        namespace (str): Metric namespace
        start_time (datetime): Start time for data collection
        end_time (datetime): End time for data collection
        period (int): Data point period in seconds
    
    Returns:
        list: List of metric data points
    """
    try:
        ec2_client = cross_account_client.get_client('ec2')
        cloudwatch_client = cross_account_client.get_client('cloudwatch')
        dimensions = [{'Name': 'InstanceId', 'Value': instance_id}]
        
        # Add additional dimensions for CWAgent metrics
        if namespace == 'CWAgent':
            # Try to get instance type for additional dimension
            try:
                response = ec2_client.describe_instances(InstanceIds=[instance_id])
                if response['Reservations']:
                    instance_type = response['Reservations'][0]['Instances'][0]['InstanceType']
                    dimensions.append({'Name': 'InstanceType', 'Value': instance_type})
            except Exception as e:
                logger.warning(f"Could not get instance type for {instance_id}: {str(e)}")
        
        response = cloudwatch_client.get_metric_statistics(
            Namespace=namespace,
            MetricName=metric_name,
            Dimensions=dimensions,
            StartTime=start_time,
            EndTime=end_time,
            Period=period,
            Statistics=['Average', 'Minimum', 'Maximum']
        )
        
        return response.get('Datapoints', [])
    except Exception as e:
        logger.error(f"Error fetching metric {metric_name} for instance {instance_id}: {str(e)}")
        return []

def fetch_all_metrics(cross_account_client, instance_id, start_time, end_time, period=300):
    """
    Fetch all available metrics for an EC2 instance
    
    Args:
        cloudwatch_client: CloudWatch client
        instance_id (str): EC2 instance ID
        start_time (datetime): Start time for data collection
        end_time (datetime): End time for data collection
        period (int): Data point period in seconds
    
    Returns:
        dict: Dictionary containing all metrics data
    """
    ec2_client = cross_account_client.get_client('ec2')
    cloudwatch_client = cross_account_client.get_client('cloudwatch')
    all_metrics = {}
    
    for metric_config in EC2_METRICS:
        metric_name = metric_config['name']
        namespace = metric_config['namespace']
        
        data_points = fetch_metric_data(
            cross_account_client, 
            instance_id, 
            metric_name, 
            namespace, 
            start_time, 
            end_time, 
            period
        )
        
        if data_points:
            # Sort data points by timestamp
            data_points.sort(key=lambda x: x['Timestamp'])
            
            all_metrics[metric_name] = {
                'namespace': namespace,
                'unit': metric_config['unit'],
                'description': metric_config['description'],
                'data_points': [
                    {
                        'timestamp': dp['Timestamp'].isoformat(),
                        'average': dp.get('Average'),
                        'minimum': dp.get('Minimum'),
                        'maximum': dp.get('Maximum')
                    }
                    for dp in data_points
                ]
            }
    
    return all_metrics

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
            start_dt = datetime.utcnow() - timedelta(hours=1)
        
        if end_time:
            end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
        else:
            end_dt = datetime.utcnow()
        
        # Ensure start_time is before end_time
        if start_dt >= end_dt:
            raise ValueError("Start time must be before end time")
        
        # Limit time range to 30 days
        if (end_dt - start_dt) > timedelta(days=30):
            raise ValueError("Time range cannot exceed 30 days")
        
        return start_dt, end_dt
    except Exception as e:
        raise ValueError(f"Invalid time format: {str(e)}")

def lambda_handler(event, context):
    """
    Lambda handler for fetching EC2 metrics
    
    Expected event structure:
    {
        "account_id": "123456789012",  // Optional for cross-account
        "role_name": "EC2CrossAccountMetricsRole",  // Optional for cross-account
        "instance_id": "i-1234567890abcdef0",
        "region": "us-east-1",
        "start_time": "2024-01-01T00:00:00",
        "end_time": "2024-01-01T23:59:59",
        "period": 300,
        "metrics": ["CPUUtilization", "mem_used_percent"]  // Optional, fetch all if not specified
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
        period = int(body.get('period', 300))
        requested_metrics = body.get('metrics', [])
        role_arn = f"arn:aws:iam::{account_id}:role/{role_name}"
        cross_account_client = CrossAccountClient(account_id, role_arn, region)
        if not cross_account_client.assume_role():
            return {
                'statusCode': 500,
                'body': json.dumps({'error': 'Failed to assume cross-account role'})
            }
        
        # Validate required parameters
        if not instance_id:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Missing required parameter: instance_id'
                })
            }
        
        # Validate time range
        try:
            start_dt, end_dt = validate_time_range(start_time, end_time)
        except ValueError as e:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': str(e)
                })
            }
        
      
        all_metrics = fetch_all_metrics(cross_account_client, instance_id, start_dt, end_dt, period)
        
        # Filter metrics if specific ones were requested
        if requested_metrics:
            filtered_metrics = {}
            for metric_name in requested_metrics:
                if metric_name in all_metrics:
                    filtered_metrics[metric_name] = all_metrics[metric_name]
            all_metrics = filtered_metrics
        
        # Prepare response
        response_data = {
            'instance_id': instance_id,
            'account_id': account_id,
            'region': region,
            'start_time': start_dt.isoformat(),
            'end_time': end_dt.isoformat(),
            'period': period,
            'metrics_count': len(all_metrics),
            'metrics': all_metrics
        }
        
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