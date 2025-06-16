import json
import os
import logging
from datetime import datetime, timedelta
from utils.cross_account import CrossAccountClient
from utils.cassandra_client import CassandraClient

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def ensure_alarm_table(session):
    keyspace = os.environ.get('CASSANDRA_KEYSPACE', 'monitoring')
    table = os.environ.get('CASSANDRA_ALARM_TABLE', 'ec2_alarms')

    query = f"""
    CREATE TABLE IF NOT EXISTS {keyspace}.{table} (
        instance_id text,
        alarm_name text,
        timestamp timestamp,
        history_summary text,
        history_type text,
        PRIMARY KEY ((instance_id), timestamp)
    )
    """
    session.execute(query)

def insert_alarm(session, record):
    table = os.environ.get('CASSANDRA_ALARM_TABLE', 'ec2_alarms')
    query = f"""
        INSERT INTO {table} (instance_id, alarm_name, timestamp, history_summary, history_type)
        VALUES (%s, %s, %s, %s, %s)
    """
    session.execute(query, (
        record['instance_id'],
        record['alarm_name'],
        record['timestamp'],
        record['history_summary'],
        record['history_type']
    ))

def fetch_and_store_alarms(cloudwatch, session, instance_id, start_dt, end_dt):
    stored_records = []
    paginator = cloudwatch.get_paginator('describe_alarms')

    for page in paginator.paginate():
        for alarm in page.get('MetricAlarms', []):
            if not any(dim['Name'] == 'InstanceId' and dim['Value'] == instance_id for dim in alarm.get('Dimensions', [])):
                continue

            alarm_name = alarm['AlarmName']
            history = cloudwatch.describe_alarm_history(
                AlarmName=alarm_name,
                StartDate=start_dt,
                EndDate=end_dt,
                HistoryItemType='StateUpdate'
            )

            for item in history.get('AlarmHistoryItems', []):
                record = {
                    'instance_id': instance_id,
                    'alarm_name': alarm_name,
                    'timestamp': item['Timestamp'],
                    'history_summary': item['HistorySummary'],
                    'history_type': item['HistoryItemType']
                }
                insert_alarm(session, record)
                stored_records.append(record)

    return stored_records

def lambda_handler(event, context):
    try:
        body = json.loads(event.get('body', '{}'))
        instance_id = body.get("instance_id")
        account_id = body.get("account_id")
        region = body.get("region") or os.environ.get("AWS_REGION", "us-east-1")
        start_time = body.get("start_time")
        end_time = body.get("end_time")

        if not all([account_id, instance_id]):
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Required: account_id, instance_id'})
            }

        now = datetime.utcnow()
        start_dt = datetime.fromisoformat(start_time) if start_time else now - timedelta(hours=6)
        end_dt = datetime.fromisoformat(end_time) if end_time else now

        role_name = os.environ.get("ROLE_NAME", "EC2CrossAccountMetricsRole")
        role_arn = f"arn:aws:iam::{account_id}:role/{role_name}"

        cross_client = CrossAccountClient(account_id, role_arn, region)
        cross_client.assume_role()
        cloudwatch = cross_client.get_client("cloudwatch")

        cassandra_client = CassandraClient()
        session = cassandra_client.getSession()

        ensure_alarm_table(session)

        records = fetch_and_store_alarms(cloudwatch, session, instance_id, start_dt, end_dt)

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Alarms stored successfully',
                'records': len(records)
            })
        }

    except Exception as e:
        logger.exception("Error fetching/storing alarms")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
