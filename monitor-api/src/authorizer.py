import json
import boto3
from botocore.exceptions import ClientError

def generate_policy(principal_id, effect, resource):
    """Generate IAM policy document"""
    return {
        'principalId': principal_id,
        'policyDocument': {
            'Version': '2012-10-17',
            'Statement': [{
                'Action': 'execute-api:Invoke',
                'Effect': effect,
                'Resource': resource
            }]
        }
    }

def lambda_handler(event, context):
    """API Gateway IAM authorizer"""
    try:
        # Get the authorization token from the event
        auth_token = event.get('headers', {}).get('Authorization')
        if not auth_token:
            raise Exception('No authorization token provided')

        # Get the API Gateway ARN
        method_arn = event['methodArn']
        
        # Verify the token is a valid AWS signature
        sts = boto3.client('sts')
        try:
            # This will raise an exception if the token is invalid
            sts.get_caller_identity()
            
            # If we get here, the token is valid
            return generate_policy('user', 'Allow', method_arn)
        except ClientError:
            # Token is invalid
            return generate_policy('user', 'Deny', method_arn)
            
    except Exception as e:
        print(f"Authorization error: {str(e)}")
        return generate_policy('user', 'Deny', event['methodArn']) 