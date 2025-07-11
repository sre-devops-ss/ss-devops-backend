import json
import os
import logging
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

class UserAuthenticator:
    """Handles user authentication and role verification."""
    
    def __init__(self, region='us-east-1'):
        self.region = region
        self.iam_client = boto3.client('iam', region_name=region)
        self.sts_client = boto3.client('sts', region_name=region)

    def get_user_info(self, access_key_id=None, session_token=None):
        """Get current user information."""
        try:
            if access_key_id and session_token:
                # Use provided credentials
                sts_client = boto3.client(
                    'sts',
                    aws_access_key_id=access_key_id,
                    aws_session_token=session_token,
                    region_name=self.region
                )
            else:
                # Use default credentials
                sts_client = self.sts_client
            
            response = sts_client.get_caller_identity()
            return {
                'UserId': response.get('UserId'),
                'Account': response.get('Account'),
                'Arn': response.get('Arn')
            }
        except ClientError as e:
            logger.error(f"Error getting user info: {str(e)}")
            return None

    def verify_user_role(self, user_arn, required_role_name):
        """Verify if user has the required role."""
        try:
            # Extract role name from ARN
            if '/role/' in user_arn:
                role_name = user_arn.split('/role/')[-1]
                return role_name == required_role_name
            return False
        except Exception as e:
            logger.error(f"Error verifying user role: {str(e)}")
            return False

    def get_user_permissions(self, user_name):
        """Get user's IAM permissions."""
        try:
            # Get attached policies
            attached_policies = self.iam_client.list_attached_user_policies(UserName=user_name)
            
            # Get inline policies
            inline_policies = self.iam_client.list_user_policies(UserName=user_name)
            
            # Get groups
            groups = self.iam_client.list_groups_for_user(UserName=user_name)
            
            return {
                'attached_policies': attached_policies.get('AttachedPolicies', []),
                'inline_policies': inline_policies.get('PolicyNames', []),
                'groups': groups.get('Groups', [])
            }
        except ClientError as e:
            logger.error(f"Error getting user permissions: {str(e)}")
            return None

    def validate_cross_account_access(self, account_id, role_name):
        """Validate cross-account access permissions."""
        try:
            role_arn = f"arn:aws:iam::{account_id}:role/{role_name}"
            
            # Check if we can assume the role
            response = self.sts_client.assume_role(
                RoleArn=role_arn,
                RoleSessionName='ValidationSession'
            )
            
            return {
                'success': True,
                'credentials': response['Credentials'],
                'role_arn': role_arn
            }
        except ClientError as e:
            logger.error(f"Error validating cross-account access: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'role_arn': role_arn
            }

    def authenticate_user_request(self, event_body):
        """Authenticate user from request body."""
        try:
            if isinstance(event_body, str):
                body = json.loads(event_body)
            else:
                body = event_body

            # Extract user information
            user_info = self.get_user_info()
            if not user_info:
                return {
                    'authenticated': False,
                    'error': 'Unable to get user information'
                }

            # Validate required fields
            required_fields = ['account_id', 'role_name']
            for field in required_fields:
                if field not in body:
                    return {
                        'authenticated': False,
                        'error': f'Missing required field: {field}'
                    }

            # Validate cross-account access
            validation_result = self.validate_cross_account_access(
                body['account_id'], 
                body['role_name']
            )

            if not validation_result['success']:
                return {
                    'authenticated': False,
                    'error': f'Cross-account access denied: {validation_result["error"]}'
                }

            return {
                'authenticated': True,
                'user_info': user_info,
                'account_id': body['account_id'],
                'role_name': body['role_name'],
                'credentials': validation_result['credentials']
            }

        except Exception as e:
            logger.error(f"Error authenticating user: {str(e)}")
            return {
                'authenticated': False,
                'error': str(e)
            }

def get_user_authenticator(region='us-east-1'):
    """Factory function to create UserAuthenticator instance."""
    return UserAuthenticator(region)
