import boto3
import json
from botocore.exceptions import ClientError
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

class CrossAccountClient:
    """Handles cross-account authentication and AWS client creation."""
    def __init__(self, account_id, role_arn, region='us-east-1', external_id=None):
        self.account_id = account_id
        self.role_arn = role_arn
        self.region = region
        self.external_id = external_id
        self.credentials = None
        self._clients = {}

    def assume_role(self):
        """Assume role in the target account."""
        try:
            sts_client = boto3.client('sts')
            
            assume_role_params = {
                'RoleArn': self.role_arn,
                'RoleSessionName': 'MonitoringSession'
            }
            
            # Add external ID if provided for additional security
            if self.external_id:
                assume_role_params['ExternalId'] = self.external_id
            
            response = sts_client.assume_role(**assume_role_params)
            self.credentials = response['Credentials']
            return True
        except ClientError as e:
            logger.error(f"Failed to assume role: {str(e)}")
            return False

    def get_client(self, service_name):
        """Get boto3 client for the specified service using assumed role."""
        if service_name not in self._clients:
            if not self.credentials:
                if not self.assume_role():
                    raise Exception("Failed to assume role")
            self._clients[service_name] = boto3.client(
                service_name,
                region_name=self.region,
                aws_access_key_id=self.credentials['AccessKeyId'],
                aws_secret_access_key=self.credentials['SecretAccessKey'],
                aws_session_token=self.credentials['SessionToken']
            )
        return self._clients[service_name]

    def store_monitoring_config(self, resource_type, config):
        """Store monitoring configuration for later use."""
        # This could be extended to store config in a database
        # For now, we'll just log it
        logger.info(f"Stored monitoring config for {resource_type}: {config}")
        return True

def get_account_id_from_role_arn(role_arn):
    """Extract account ID from role ARN"""
    try:
        return role_arn.split(':')[4]
    except:
        return None

def format_metric_data(metric_data, account_id, region):
    """Format metric data for Cassandra storage"""
    formatted_data = []
    for datapoint in metric_data:
        formatted_data.append({
            'account_id': account_id,
            'region': region,
            'timestamp': datapoint['Timestamp'].isoformat(),
            'value': datapoint['Value'],
            'unit': datapoint['Unit'],
            'statistic': datapoint['Statistic']
        })
    return formatted_data

def format_alarm_data(alarm_data, account_id, region):
    """Format alarm data for Cassandra storage"""
    formatted_data = []
    for alarm in alarm_data:
        formatted_data.append({
            'account_id': account_id,
            'region': region,
            'alarm_name': alarm['AlarmName'],
            'alarm_arn': alarm['AlarmARN'],
            'metric_name': alarm['MetricName'],
            'namespace': alarm['Namespace'],
            'dimensions': json.dumps(alarm['Dimensions']),
            'threshold': alarm['Threshold'],
            'comparison_operator': alarm['ComparisonOperator'],
            'evaluation_periods': alarm['EvaluationPeriods'],
            'period': alarm['Period'],
            'state_value': alarm['StateValue'],
            'state_updated_timestamp': alarm['StateUpdatedTimestamp'].isoformat()
        })
    return formatted_data 