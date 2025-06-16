import json
import boto3
import base64
import os
import logging
from datetime import datetime, timedelta
from utils.cross_account import CrossAccountClient
from boto3.session import Session
from cassandra.auth import SigV4AuthProvider
from cassandra.cluster import Cluster, ExecutionProfile, EXEC_PROFILE_DEFAULT
from ssl import SSLContext, CERT_REQUIRED, PROTOCOL_TLS
from requests.utils import DEFAULT_CA_BUNDLE_PATH

logger = logging.getLogger()
logger.setLevel(logging.INFO)

class AWSKeyspacesClient:
    def __init__(self):
        self.region = os.environ.get('KEYSPACES_REGION', 'us-east-1')
        self.keyspace = os.environ.get('KEYSPACES_KEYSPACE')
        
        # Use the default credentials for Keyspaces (from Lambda role)
        session = Session()
        credentials = session.get_credentials()
        
        ssl_context = SSLContext(PROTOCOL_TLS)
        ssl_context.load_verify_locations(DEFAULT_CA_BUNDLE_PATH)
        ssl_context.verify_mode = CERT_REQUIRED
        
        auth_provider = SigV4AuthProvider(
            region=self.region,
            aws_access_key_id=credentials.access_key,
            aws_secret_access_key=credentials.secret_key,
            aws_session_token=credentials.token
        )
        
        contact_point = f'cassandra.{self.region}.amazonaws.com'
        
        self.cluster = Cluster(
            [contact_point],
            ssl_context=ssl_context,
            auth_provider=auth_provider,
            port=9142
        )
        
        self.session = self.cluster.connect()
        
    def execute(self, query, params=None):
        try:
            return self.session.execute(query, params or {})
        except Exception as e:
            logger.error(f"Keyspaces query execution error: {str(e)}")
            raise
            
    def close(self):
        self.cluster.shutdown()

def store_metrics_in_keyspaces(keyspaces_client, account_id, instance_id, metric_name, metrics):
    """
    Store EC2 metrics in AWS Keyspaces
    """
    try:
        for metric in metrics:
            query = """
                INSERT INTO ec2_metrics (
                    account_id, instance_id, metric_name, timestamp,
                    value, unit
                ) VALUES (?, ?, ?, ?, ?, ?)
            """
            params = (
                account_id,
                instance_id,
                metric_name,
                metric.get('Timestamp'),
                float(metric.get('Value', 0.0)),
                metric.get('Unit', 'None')
            )
            keyspaces_client.execute(query, params)
        logger.info(f"Stored metrics for instance {instance_id} in Keyspaces")
    except Exception as e:
        logger.error(f"Error storing metrics in Keyspaces: {str(e)}")
        raise

def store_alarms_in_keyspaces(keyspaces_client, account_id, instance_id, alarms):
    """
    Store EC2 alarms in AWS Keyspaces
    """
    try:
        for alarm in alarms:
            query = """
                INSERT INTO ec2_alarms (
                    account_id, instance_id, alarm_name, alarm_description,
                    state_value, state_updated_timestamp
                ) VALUES (?, ?, ?, ?, ?, ?)
            """
            params = (
                account_id,
                instance_id,
                alarm.get('AlarmName'),
                alarm.get('AlarmDescription', ''),
                alarm.get('StateValue'),
                alarm.get('StateUpdatedTimestamp')
            )
            keyspaces_client.execute(query, params)
        logger.info(f"Stored alarms for instance {instance_id} in Keyspaces")
    except Exception as e:
        logger.error(f"Error storing alarms in Keyspaces: {str(e)}")
        raise

def get_ec2_metrics(cross_account_client, instance_id, metric_name, start_time=None, end_time=None):
    """
    Get metrics for a specific EC2 instance
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
    keyspaces_client = None
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

        # Initialize AWS Keyspaces client
        keyspaces_client = AWSKeyspacesClient()

        # Initialize cross-account client for EC2 monitoring
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
            
            # Store metrics in AWS Keyspaces
            store_metrics_in_keyspaces(keyspaces_client, account_id, instance_id, metric_name, result)

        elif path == "/ec2/getAlarms":
            result = get_ec2_alarms(cross_account_client, instance_id=instance_id)
            
            # Store alarms in AWS Keyspaces
            store_alarms_in_keyspaces(keyspaces_client, account_id, instance_id, result)

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
    finally:
        if keyspaces_client:
            keyspaces_client.close()
import logging
from datetime import datetime, timedelta

logger = logging.getLogger()
logger.setLevel(logging.INFO)

class MetricsRetriever:
    def __init__(self, cassandra_client):
        self.cassandra = cassandra_client

    def get_metrics_for_plotting(self, account_id, resource_type, metric_name, start_time=None, end_time=None):
        """
        Get metrics data formatted for plotting
        """
        try:
            if not start_time:
                start_time = datetime.utcnow() - timedelta(days=7)
            if not end_time:
                end_time = datetime.utcnow()

            # Query metrics from Cassandra
            query = """
                SELECT timestamp, value, unit
                FROM monitoring.metrics
                WHERE account_id = %s
                AND resource_type = %s
                AND metric_name = %s
                AND timestamp >= %s
                AND timestamp <= %s
                ALLOW FILTERING
            """
            params = (account_id, resource_type, metric_name, start_time, end_time)
            
            results = self.cassandra.execute(query, params)
            
            # Format data for plotting
            timestamps = []
            values = []
            unit = None
            
            for row in results:
                timestamps.append(row.timestamp)
                values.append(row.value)
                unit = row.unit
            
            return {
                'timestamps': [t.isoformat() for t in timestamps],
                'values': values,
                'unit': unit,
                'metric_name': metric_name,
                'resource_type': resource_type
            }
            
        except Exception as e:
            logger.error(f"Error getting metrics for plotting: {str(e)}")
            raise

    def get_resource_metrics(self, account_id, resource_id, start_time=None, end_time=None):
        """
        Get all metrics for a specific resource
        """
        try:
            if not start_time:
                start_time = datetime.utcnow() - timedelta(days=7)
            if not end_time:
                end_time = datetime.utcnow()

            # Query metrics from Cassandra
            query = """
                SELECT metric_name, timestamp, value, unit
                FROM monitoring.metrics
                WHERE account_id = %s
                AND resource_id = %s
                AND timestamp >= %s
                AND timestamp <= %s
                ALLOW FILTERING
            """
            params = (account_id, resource_id, start_time, end_time)
            
            results = self.cassandra.execute(query, params)
            
            # Group metrics by name
            metrics_data = {}
            for row in results:
                if row.metric_name not in metrics_data:
                    metrics_data[row.metric_name] = {
                        'timestamps': [],
                        'values': [],
                        'unit': row.unit
                    }
                metrics_data[row.metric_name]['timestamps'].append(row.timestamp)
                metrics_data[row.metric_name]['values'].append(row.value)
            
            # Sort timestamps and values
            for metric_name in metrics_data:
                sorted_data = sorted(zip(metrics_data[metric_name]['timestamps'], 
                                      metrics_data[metric_name]['values']))
                metrics_data[metric_name]['timestamps'] = [t for t, _ in sorted_data]
                metrics_data[metric_name]['values'] = [v for _, v in sorted_data]
                metrics_data[metric_name]['timestamps'] = [t.isoformat() for t in metrics_data[metric_name]['timestamps']]
            
            return metrics_data
            
        except Exception as e:
            logger.error(f"Error getting resource metrics: {str(e)}")
            raise

    def get_alarm_history_for_plotting(self, account_id, resource_id, start_time=None, end_time=None):
        """
        Get alarm history formatted for plotting
        """
        try:
            if not start_time:
                start_time = datetime.utcnow() - timedelta(days=7)
            if not end_time:
                end_time = datetime.utcnow()

            # Query alarm history from Cassandra
            query = """
                SELECT timestamp, state, severity
                FROM monitoring.alarm_history
                WHERE account_id = %s
                AND resource_id = %s
                AND timestamp >= %s
                AND timestamp <= %s
                ALLOW FILTERING
            """
            params = (account_id, resource_id, start_time, end_time)
            
            results = self.cassandra.execute(query, params)
            
            # Format data for plotting
            timestamps = []
            states = []
            severities = []
            
            for row in results:
                timestamps.append(row.timestamp)
                states.append(row.state)
                severities.append(row.severity)
            
            # Sort by timestamp
            sorted_data = sorted(zip(timestamps, states, severities))
            timestamps = [t for t, _, _ in sorted_data]
            states = [s for _, s, _ in sorted_data]
            severities = [s for _, _, s in sorted_data]
            
            return {
                'timestamps': [t.isoformat() for t in timestamps],
                'states': states,
                'severities': severities
            }
            
        except Exception as e:
            logger.error(f"Error getting alarm history for plotting: {str(e)}")
            raise

    def get_metric_thresholds(self, account_id, resource_type, metric_name):
        """
        Get threshold values for a specific metric
        """
        try:
            query = """
                SELECT warning_threshold, critical_threshold
                FROM monitoring.metric_thresholds
                WHERE account_id = %s
                AND resource_type = %s
                AND metric_name = %s
                ALLOW FILTERING
            """
            params = (account_id, resource_type, metric_name)
            
            results = self.cassandra.execute(query, params)
            
            if results:
                row = results[0]
                return {
                    'warning_threshold': row.warning_threshold,
                    'critical_threshold': row.critical_threshold
                }
            return None
            
        except Exception as e:
            logger.error(f"Error getting metric thresholds: {str(e)}")
            raise