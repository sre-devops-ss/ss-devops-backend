import json
import logging
from datetime import datetime
from utils.metrics_retriever import MetricsRetriever
from utils.cassandra_client import CassandraClient
from utils.cross_account import CrossAccountClient

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """
    API handler for retrieving metrics and alarm data for plotting
    """
    try:
        # Parse request
        path = event.get('path', '')
        query_params = event.get('queryStringParameters', {}) or {}
        
        # Get required parameters
        account_id = query_params.get('account_id')
        role_arn = query_params.get('role_arn')
        region = query_params.get('region', 'us-east-1')
        
        if not all([account_id, role_arn]):
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'account_id and role_arn are required'
                })
            }
        
        # Initialize cross-account client
        cross_account_client = CrossAccountClient(account_id, role_arn, region)
        
        # Initialize other clients
        cassandra = CassandraClient()
        metrics_retriever = MetricsRetriever(cassandra)
        
        # Route requests based on path
        if path == '/metrics/plot':
            resource_type = query_params.get('resource_type')
            metric_name = query_params.get('metric_name')
            start_time = query_params.get('start_time')
            end_time = query_params.get('end_time')
            
            if not all([resource_type, metric_name]):
                return {
                    'statusCode': 400,
                    'body': json.dumps({
                        'error': 'resource_type and metric_name are required'
                    })
                }
            
            # Convert string timestamps to datetime objects
            if start_time:
                start_time = datetime.fromisoformat(start_time)
            if end_time:
                end_time = datetime.fromisoformat(end_time)
            
            # Get metrics data
            metrics_data = metrics_retriever.get_metrics_for_plotting(
                account_id,
                resource_type,
                metric_name,
                start_time,
                end_time
            )
            
            # Get thresholds
            thresholds = metrics_retriever.get_metric_thresholds(
                account_id,
                resource_type,
                metric_name
            )
            
            if thresholds:
                metrics_data['thresholds'] = thresholds
            
            return {
                'statusCode': 200,
                'body': json.dumps(metrics_data)
            }
            
        elif path == '/metrics/resource':
            resource_id = query_params.get('resource_id')
            start_time = query_params.get('start_time')
            end_time = query_params.get('end_time')
            
            if not resource_id:
                return {
                    'statusCode': 400,
                    'body': json.dumps({
                        'error': 'resource_id is required'
                    })
                }
            
            # Convert string timestamps to datetime objects
            if start_time:
                start_time = datetime.fromisoformat(start_time)
            if end_time:
                end_time = datetime.fromisoformat(end_time)
            
            # Get all metrics for the resource
            metrics_data = metrics_retriever.get_resource_metrics(
                account_id,
                resource_id,
                start_time,
                end_time
            )
            
            return {
                'statusCode': 200,
                'body': json.dumps(metrics_data)
            }
            
        elif path == '/metrics/alarm-history':
            resource_id = query_params.get('resource_id')
            start_time = query_params.get('start_time')
            end_time = query_params.get('end_time')
            
            if not resource_id:
                return {
                    'statusCode': 400,
                    'body': json.dumps({
                        'error': 'resource_id is required'
                    })
                }
            
            # Convert string timestamps to datetime objects
            if start_time:
                start_time = datetime.fromisoformat(start_time)
            if end_time:
                end_time = datetime.fromisoformat(end_time)
            
            # Get alarm history
            alarm_history = metrics_retriever.get_alarm_history_for_plotting(
                account_id,
                resource_id,
                start_time,
                end_time
            )
            
            return {
                'statusCode': 200,
                'body': json.dumps(alarm_history)
            }
            
        else:
            return {
                'statusCode': 404,
                'body': json.dumps({
                    'error': 'Not Found'
                })
            }
            
    except Exception as e:
        logger.error(f"Error in metrics_api: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        } 