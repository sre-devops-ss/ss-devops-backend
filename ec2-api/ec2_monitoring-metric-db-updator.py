import json
import boto3
import os
import logging
from datetime import datetime, timedelta
from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider
from cassandra.query import SimpleStatement
from utils.cross_account import CrossAccountClient
from utils.cassandra_client import CassandraClient

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Metrics to fetch from CloudWatch
METRICS = [
    {"Namespace": "AWS/EC2", "MetricName": "CPUUtilization", "DimensionsKey": "InstanceId"},
    {"Namespace": "CWAgent", "MetricName": "mem_used_percent", "DimensionsKey": "InstanceId"},
    {"Namespace": "CWAgent", "MetricName": "disk_used_percent", "DimensionsKey": "InstanceId"}
]


# Insert a single metric row into Cassandra
def insert_metric(session, item):
    table = os.environ.get('CASSANDRA_TABLE', 'ec2_metrics')
    query = f"""
        INSERT INTO {table} (instance_id, metric_name, namespace, timestamp, value)
        VALUES (%s, %s, %s, %s, %s)
    """
    session.execute(query, (
        item['instance_id'],
        item['metric_name'],
        item['namespace'],
        item['timestamp'],
        float(item['value'])  # ensure numeric
    ))

# Fetch CloudWatch metric data
def fetch_metric(cloudwatch, instance_id, metric_name, namespace, dimensions, start_time, end_time):
    response = cloudwatch.get_metric_statistics(
        Namespace=namespace,
        MetricName=metric_name,
        Dimensions=dimensions,
        StartTime=start_time,
        EndTime=end_time,
        Period=300,
        Statistics=["Average"]
    )
    return response.get("Datapoints", [])

def lambda_handler(event, context):
    try:
        body = json.loads(event.get('body', '{}'))
        instance_id = body.get("instance_id")
        account_id = body.get("account_id")
        region = body.get("region") or os.environ.get("AWS_REGION", "us-east-1")
        start_time = body.get("start_time")
        end_time = body.get("end_time")

        if not all([instance_id, account_id]):
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Required parameters: instance_id, account_id'})
            }

        # Set time range default to last 1 hour if not provided
        now = datetime.utcnow()
        if not start_time:
            start_dt = now - timedelta(hours=1)
        else:
            start_dt = datetime.fromisoformat(start_time)

        if not end_time:
            end_dt = now
        else:
            end_dt = datetime.fromisoformat(end_time)

        role_name = os.environ.get("ROLE_NAME", "EC2CrossAccountMetricsRole")
        role_arn = f"arn:aws:iam::{account_id}:role/{role_name}"

        # Assume role in client account
        cross_client = CrossAccountClient(account_id, role_arn, region)
        cross_client.assume_role()
        cloudwatch = cross_client.get_client("cloudwatch")
        
        cassandra_client = CassandraClient()
        session = cassandra_client.getSession()

        all_metrics = []

        for metric in METRICS:
            dimensions = [{"Name": metric["DimensionsKey"], "Value": instance_id}]
            data_points = fetch_metric(
                cloudwatch,
                instance_id,
                metric["MetricName"],
                metric["Namespace"],
                dimensions,
                start_dt,
                end_dt
            )
            for dp in data_points:
                record = {
                    "instance_id": instance_id,
                    "metric_name": metric["MetricName"],
                    "namespace": metric["Namespace"],
                    "timestamp": dp["Timestamp"],
                    "value": dp["Average"]
                }
                insert_metric(session, record)
                all_metrics.append(record)

        if not all_metrics:
            return {
                'statusCode': 204,
                'body': json.dumps({'message': 'No metrics found for the given time range'})
            }

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Metrics stored successfully',
                'records': len(all_metrics)
            })
        }

    except Exception as e:
        logger.exception("Failed to fetch/store metrics")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
