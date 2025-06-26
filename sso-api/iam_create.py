import json
import os
import logging
from utils.cross_account import CrossAccountClient

logger = logging.getLogger()
logger.setLevel(logging.INFO)

class IAMRoleCreator:
    def __init__(self, account_client):
        self.iam = account_client.get_client("iam")

    def create_role(self, role_name, trust_policy_document, managed_policies=None, assume_remote_role_arns=None):
    
        try:
            response = self.iam.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=json.dumps(trust_policy_document),
                Description="Created by cross-account Lambda"
            )
            role_arn = response['Role']['Arn']
            attached_policies = []

            # Attach managed policies
            if managed_policies:
                for policy_arn in managed_policies:
                    self.iam.attach_role_policy(RoleName=role_name, PolicyArn=policy_arn)
                    attached_policies.append(policy_arn)

            if assume_remote_role_arns:
                inline_policy = {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Action": "sts:AssumeRole",
                            "Resource": assume_remote_role_arns if isinstance(assume_remote_role_arns, list) else [assume_remote_role_arns]
                        }
                    ]
                }

                self.iam.put_role_policy(
                    RoleName=role_name,
                    PolicyName="InlineSTSAssumePolicy",
                    PolicyDocument=json.dumps(inline_policy)
                )

            return role_arn, attached_policies

        except Exception as e:
            logger.error(f"Error creating IAM role: {str(e)}")
            raise


def lambda_handler(event, context):
    try:
        body = json.loads(event.get("body", "{}"))
        account_id = body.get("account_id")
        region = body.get("region") or os.environ.get("REGION")
        role_name = body.get("role_name") or os.environ.get("ROLE_NAME")
        trust_policy_document = body.get("trust_policy_document")
        policies = body.get("policies", [])
        assume_remote_role_arns = body.get("assume_remote_role_arns", [])

        if not account_id or not role_name or not trust_policy_document:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'account_id, role_name, and assume_role_policy_document are required'})
            }

        role_name_env = os.environ.get("ROLE_NAME")
        role_arn = f"arn:aws:iam::{account_id}:role/{role_name_env}"

        client = CrossAccountClient(account_id, role_arn, region)
        client.assume_role()

        creator = client.get_client("iam")
        role_arn, attached_policies = creator.create_role(role_name, trust_policy_document, policies,assume_remote_role_arns)

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'IAM role created',
                'role_arn': role_arn,
                'attached_policies': attached_policies
            })
        }

    except Exception as e:
        logger.error(f"Lambda error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        } 