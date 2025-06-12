import json
import boto3
import base64
import os
import logging
from datetime import datetime, timedelta
from utils.cross_account import CrossAccountClient
from utils.cassandra_client import CassandraClient

ec2 = boto3.client('ec2')
ssm = boto3.client('ssm')

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def get_ec2_metrics(cross_account_client, instance_id, metric_name, start_time=None, end_time=None):
    """
    Get metrics for a specific EC2 instance
    
    Args:
        cross_account_client (CrossAccountClient): Authenticated client for cross-account operations
        instance_id (str): EC2 instance ID
        metric_name (str): Name of the metric to retrieve
        start_time (datetime): Start time for metric data
        end_time (datetime): End time for metric data
    """
    try:
        return cross_account_client.get_metrics(
            namespace='AWS/EC2',
            metric_name=metric_name,
            dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
            start_time=start_time,
            end_time=end_time
        )
    except Exception as e:
        logger.error(f"Error getting EC2 metrics: {str(e)}")
        return []

def get_ec2_alarms(cross_account_client, instance_id):
    """
    Get alarms for a specific EC2 instance
    
    Args:
        cross_account_client (CrossAccountClient): Authenticated client for cross-account operations
        instance_id (str): EC2 instance ID
    """
    try:
        alarms = cross_account_client.get_alarms()
        return [alarm for alarm in alarms if any(
            dim['Name'] == 'InstanceId' and dim['Value'] == instance_id 
            for dim in alarm.get('Dimensions', [])
        )]
    except Exception as e:
        logger.error(f"Error getting EC2 alarms: {str(e)}")
        return []

def lambda_handler(event, context):
    try:
        path = event.get("path", "")
        params = event.get("queryStringParameters", {}) or {}

        account_id = params.get("account_id")
        instance_id = params.get("instance_id")
        region = params.get("region", "us-east-1")
        role_name = os.environ.get("ROLE_NAME")

        if not account_id or not instance_id:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing account_id or instance_id"})
            }

        role_arn = f"arn:aws:iam::{account_id}:role/{role_name}"
        cross_account_client = CrossAccountClient(account_id, role_arn, region)
        cross_account_client.assume_role()

        if path == "/ec2/getMetrics":
            metric_name = params.get("metric_name")
            if not metric_name:
                return {
                    "statusCode": 400,
                    "body": json.dumps({"error": "Missing metric_name for metrics API"})
                }
            def parse_time(key):
                try:
                    return datetime.fromisoformat(params[key]) if key in params else None
                except ValueError:
                    raise Exception(f"Invalid format for {key}, must be ISO format")

            start_time = parse_time("start_time")
            end_time = parse_time("end_time")

            result = get_ec2_metrics(
                cross_account_client,
                instance_id=instance_id,
                metric_name=metric_name,
                start_time=start_time,
                end_time=end_time
            )

        elif path == "/ec2/getAlarms":
            result = get_ec2_alarms(cross_account_client, instance_id=instance_id)

        else:
            return {
                "statusCode": 404,
                "body": json.dumps({"error": f"No route defined for path {path}"})
            }

        return {
            "statusCode": 200,
            "body": json.dumps(result, default=str)
        }

    except Exception as e:
        logger.error(f"Unhandled exception: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }