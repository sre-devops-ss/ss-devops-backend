import json
import logging
from datetime import datetime
from utils.alarm_retriever import AlarmRetriever
from utils.cassandra_client import CassandraClient
from utils.cross_account import CrossAccountClient

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """
    API handler for retrieving alarm data for the dashboard
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
        alarm_retriever = AlarmRetriever(cassandra)
        
        # Route requests based on path
        if path == '/alarms/active':
            resource_type = query_params.get('resource_type')
            
            alarms = alarm_retriever.get_active_alarms(account_id, resource_type)
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'alarms': alarms
                })
            }
            
        elif path == '/alarms/history':
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
            
            history = alarm_retriever.get_alarm_history(
                account_id,
                resource_id,
                start_time,
                end_time
            )
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'history': history
                })
            }
            
        elif path == '/alarms/severity':
            severity = query_params.get('severity')
            start_time = query_params.get('start_time')
            end_time = query_params.get('end_time')
            
            if not severity:
                return {
                    'statusCode': 400,
                    'body': json.dumps({
                        'error': 'severity is required'
                    })
                }
            
            # Convert string timestamps to datetime objects
            if start_time:
                start_time = datetime.fromisoformat(start_time)
            if end_time:
                end_time = datetime.fromisoformat(end_time)
            
            alarms = alarm_retriever.get_alarms_by_severity(
                account_id,
                severity,
                start_time,
                end_time
            )
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'alarms': alarms
                })
            }
            
        elif path == '/alarms/summary':
            resource_type = query_params.get('resource_type')
            start_time = query_params.get('start_time')
            end_time = query_params.get('end_time')
            
            # Convert string timestamps to datetime objects
            if start_time:
                start_time = datetime.fromisoformat(start_time)
            if end_time:
                end_time = datetime.fromisoformat(end_time)
            
            alarms = alarm_retriever.get_alarms_by_account(
                account_id,
                resource_type,
                start_time,
                end_time
            )
            
            # Generate summary statistics
            summary = {
                'total_alarms': len(alarms),
                'active_alarms': len([a for a in alarms if a['state'] == 'ALARM']),
                'by_severity': {},
                'by_resource_type': {},
                'by_state': {}
            }
            
            for alarm in alarms:
                # Count by severity
                severity = alarm['severity']
                summary['by_severity'][severity] = summary['by_severity'].get(severity, 0) + 1
                
                # Count by resource type
                resource_type = alarm['resource_type']
                summary['by_resource_type'][resource_type] = summary['by_resource_type'].get(resource_type, 0) + 1
                
                # Count by state
                state = alarm['state']
                summary['by_state'][state] = summary['by_state'].get(state, 0) + 1
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'summary': summary,
                    'alarms': alarms
                })
            }
            
        else:
            return {
                'statusCode': 404,
                'body': json.dumps({
                    'error': 'Not Found'
                })
            }
            
    except Exception as e:
        logger.error(f"Error in alarm_api: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        } 