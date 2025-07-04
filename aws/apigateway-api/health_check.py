import json
import logging
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """Health check endpoint for the generic monitoring API."""
    try:
        health_status = {
            'status': 'healthy',
            'service': 'generic-monitoring-api',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
            'endpoints': {
                'install': 'POST /install - Set up monitoring for AWS resources',
                'getMetrics': 'GET/POST /getMetrics - Fetch CloudWatch metrics',
                'getAlarms': 'GET/POST /getAlarms - Fetch CloudWatch alarms',
                'listResources': 'GET/POST /listResources - List AWS resources',
                'updateMetricsToDb': 'POST /updateMetricsToDb - Update metrics to database',
                'updateAlarmsToDb': 'POST /updateAlarmsToDb - Update alarms to database',
                'health': 'GET /health - Health check endpoint'
            },
            'supported_services': [
                'ec2',
                'rds', 
                's3',
                'iam_roles',
                'iam_users'
            ]
        }
        
        return {
            'statusCode': 200,
            'body': json.dumps(health_status),
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': '*',
                'Access-Control-Allow-Methods': 'GET,POST,PUT,OPTIONS'
            }
        }
        
    except Exception as e:
        logger.error(f"Error in health check: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }),
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': '*',
                'Access-Control-Allow-Methods': 'GET,POST,PUT,OPTIONS'
            }
        } 