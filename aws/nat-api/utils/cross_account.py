import boto3
import logging
from botocore.exceptions import ClientError
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
                'RoleSessionName': 'CrossAccSession'
            }
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