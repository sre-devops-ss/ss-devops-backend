import json
import boto3
import os
import logging
from datetime import datetime, timedelta
from cassandra.cluster import Cluster
from ssl import SSLContext, CERT_REQUIRED, PROTOCOL_TLS
from requests.utils import DEFAULT_CA_BUNDLE_PATH

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ORIGIN = os.getenv("DOMAIN", "*")

headers = {
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Origin': ORIGIN,
    'Access-Control-Allow-Methods': 'OPTIONS,GET,POST'
}

class KeyspacesClient:
    def __init__(self):
        self.region = os.environ.get('KEYSPACES_REGION', 'us-east-1')
        self.keyspace = os.environ.get('KEYSPACES_KEYSPACE')
        
        ssl_context = SSLContext(PROTOCOL_TLS)
        ssl_context.load_verify_locations(DEFAULT_CA_BUNDLE_PATH)
        ssl_context.verify_mode = CERT_REQUIRED
        
        auth_provider = SigV4AuthProvider(
            region=self.region
        )
        
        contact_point = f'cassandra.{self.region}.amazonaws.com'
        
        self.cluster = Cluster(
            [contact_point],
            ssl_context=ssl_context,
            auth_provider=auth_provider,
            port=9142
        )
        
        self.session = self.cluster.connect(self.keyspace)
        
    def execute(self, query, params=None):
        try:
            return self.session.execute(query, params or {})
        except Exception as e:
            logger.error(f"Keyspaces query execution error: {str(e)}")
            raise
            
    def close(self):
        self.cluster.shutdown()

def get_ec2_alarms_from_keyspaces(keyspaces_client, account_id, instance_id, start_time=None, end_time=None):
    """
    Get EC2 alarms from Amazon Keyspaces with history
    """
    try:
        # Get current alarms
        current_alarms_query = """
            SELECT alarm_name, alarm_description, state_value, state_updated_timestamp,
                   metric_name, threshold, comparison_operator, evaluation_periods
            FROM ec2_alarms
            WHERE account_id = %s
            AND instance_id = %s
        """
        current_alarms_params = [account_id, instance_id]
        current_alarms = keyspaces_client.execute(current_alarms_query, current_alarms_params)
        
        # Get alarm history if time range provided
        alarm_history = []
        if start_time and end_time:
            history_query = """
                SELECT alarm_name, state_value, state_reason, timestamp
                FROM ec2_alarm_history
                WHERE account_id = %s
                AND instance_id = %s
                AND timestamp >= %s
                AND timestamp <= %s
                ALLOW FILTERING
            """
            history_params = [account_id, instance_id, start_time, end_time]
            alarm_history = keyspaces_client.execute(history_query, history_params)

        return {
            'current_alarms': [{
                'AlarmName': row.alarm_name,
                'AlarmDescription': row.alarm_description,
                'StateValue': row.state_value,
                'StateUpdatedTimestamp': row.state_updated_timestamp,
                'MetricName': row.metric_name,
                'Threshold': float(row.threshold),
                'ComparisonOperator': row.comparison_operator,
                'EvaluationPeriods': row.evaluation_periods
            } for row in current_alarms],
            'alarm_history': [{
                'AlarmName': row.alarm_name,
                'StateValue': row.state_value,
                'StateReason': row.state_reason,
                'Timestamp': row.timestamp
            } for row in alarm_history] if alarm_history else []
        }
    except Exception as e:
        logger.error(f"Error fetching alarms from Keyspaces: {str(e)}")
        return {'current_alarms': [], 'alarm_history': []}

def store_ec2_alarms_in_keyspaces(keyspaces_client, account_id, instance_id, alarms):
    """
    Store EC2 alarms in Amazon Keyspaces
    """
    try:
        # Store current alarm state
        current_state_query = """
            INSERT INTO ec2_alarms (
                account_id, instance_id, alarm_name, alarm_description,
                state_value, state_updated_timestamp, metric_name,
                threshold, comparison_operator, evaluation_periods
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        # Store alarm history
        history_query = """
            INSERT INTO ec2_alarm_history (
                account_id, instance_id, alarm_name, state_value,
                state_reason, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?)
        """
        
        for alarm in alarms:
            # Store current state
            current_params = (
                account_id,
                instance_id,
                alarm.get('AlarmName'),
                alarm.get('AlarmDescription', ''),
                alarm.get('StateValue'),
                alarm.get('StateUpdatedTimestamp'),
                alarm.get('MetricName'),
                float(alarm.get('Threshold', 0.0)),
                alarm.get('ComparisonOperator'),
                alarm.get('EvaluationPeriods', 1)
            )
            keyspaces_client.execute(current_state_query, current_params)
            
            # Store in history
            history_params = (
                account_id,
                instance_id,
                alarm.get('AlarmName'),
                alarm.get('StateValue'),
                alarm.get('StateReason', ''),
                datetime.utcnow()
            )
            keyspaces_client.execute(history_query, history_params)
            
        return True
    except Exception as e:
        logger.error(f"Error storing alarms in Keyspaces: {str(e)}")
        raise

def lambda_handler(event, context):
    keyspaces_client = None
    try:
        if event.get("httpMethod") == "OPTIONS":
            return {
                "statusCode": 200,
                "headers": headers,
                "body": json.dumps({"message": "CORS preflight OK"})
            }

        method = event.get("httpMethod")
        path = event.get("path", "")
        params = event.get("queryStringParameters", {}) or {}

        account_id = params.get("account_id")
        instance_id = params.get("instance_id")

        if not account_id or not instance_id:
            return {
                "statusCode": 400,
                "headers": headers,
                "body": json.dumps({"error": "Missing account_id or instance_id"})
            }

        keyspaces_client = KeyspacesClient()

        if method == "GET" and path == "/ec2/alarms":
            def parse_time(key):
                try:
                    return datetime.fromisoformat(params[key]) if key in params else None
                except ValueError:
                    raise Exception(f"Invalid format for {key}, must be ISO format")

            start_time = parse_time("start_time")
            end_time = parse_time("end_time")

            result = get_ec2_alarms_from_keyspaces(
                keyspaces_client,
                account_id=account_id,
                instance_id=instance_id,
                start_time=start_time,
                end_time=end_time
            )

        elif method == "POST" and path == "/ec2/alarms":
            if not event.get("body"):
                return {
                    "statusCode": 400,
                    "headers": headers,
                    "body": json.dumps({"error": "Missing request body"})
                }

            body = json.loads(event["body"])
            alarms = body.get("alarms", [])

            if not alarms:
                return {
                    "statusCode": 400,
                    "headers": headers,
                    "body": json.dumps({"error": "No alarms provided"})
                }

            store_ec2_alarms_in_keyspaces(
                keyspaces_client,
                account_id,
                instance_id,
                alarms
            )

            result = {"message": "Alarms stored successfully"}

        else:
            return {
                "statusCode": 404,
                "headers": headers,
                "body": json.dumps({"error": f"No route defined for {method} {path}"})
            }

        return {
            "statusCode": 200,
            "headers": headers,
            "body": json.dumps({
                "data": result,
                "metadata": {
                    "account_id": account_id,
                    "instance_id": instance_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }, default=str)
        }

    except Exception as e:
        logger.error(f"Unhandled exception: {e}")
        return {
            "statusCode": 500,
            "headers": headers,
            "body": json.dumps({"error": str(e)})
        }
    finally:
        if keyspaces_client:
            keyspaces_client.close()