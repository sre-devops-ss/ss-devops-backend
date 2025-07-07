import json
import logging
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """Health check endpoint for the lambda monitoring API."""
    try:
        health_status = {
            'status': 'healthy',
            'service': 'lambda-monitoring-api',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
            'endpoints': {
                'errors-alarm': 'POST /errors-alarm - Create Lambda errors alarm',
                'duration-alarm': 'POST /duration-alarm - Create Lambda duration alarm',
                'log-error-alarm': 'POST /log-error-alarm - Create Lambda log error alarm',
                'health': 'GET /health - Health check endpoint'
            },
            'supported_services': [
                'lambda_errors_alarm',
                'lambda_duration_alarm',
                'lambda_log_error_alarm'
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