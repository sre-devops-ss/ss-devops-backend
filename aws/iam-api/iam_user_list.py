import json
import os
import logging
from utils.cross_account import CrossAccountClient

logger = logging.getLogger()
logger.setLevel(logging.INFO)
def lambda_handler(event, context):
    try:
        # Parse input
        body = json.loads(event.get("body", "{}"))
        account_id = body.get("account_id")
        region = body.get("region") or os.environ.get("REGION")
        marker = body.get("marker")  # For pagination

        if not account_id:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'account_id is required'})
            }

        role_name_env = os.environ.get("ROLE_NAME")
        role_arn = f"arn:aws:iam::{account_id}:role/{role_name_env}"

        client = CrossAccountClient(account_id, role_arn, region)
        client.assume_role()
        iam = client.get_client("iam")

        paginator = iam.get_paginator('list_users')
        pagination_config = {
            'PageSize': 10
        }
        if marker:
            pagination_config['StartingToken'] = marker

        # Use paginator to fetch users
        response_iterator = paginator.paginate(PaginationConfig=pagination_config)
        users = []
        next_marker = None
        is_truncated = False

        for page in response_iterator:
            for user in page.get('Users', []):
                users.append({
                    'UserName': user['UserName'],
                    'UserId': user['UserId'],
                    'Arn': user['Arn'],
                    'CreateDate': user['CreateDate'].isoformat()
                })
            # 'IsTruncated' indicates if there are more results to fetch
            # If True, use 'Marker' for the next request
            is_truncated = page.get('IsTruncated', False)
            if is_truncated:
                next_marker = page.get('Marker')
            break  # Only return the first page (10 users)

        return {
            'statusCode': 200,
            'body': json.dumps({
                'users': users,
                'is_truncated': is_truncated,
                'next_marker': next_marker
            })
        }

    except Exception as e:
        logger.error(f"Lambda error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        } 