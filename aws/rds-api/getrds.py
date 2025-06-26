import json
import boto3
import os
from utils.cross_account import CrossAccountClient
def lambda_handler(event, context):
    try:
        print("Event:", json.dumps(event))

        # Get query parameters
        query = event.get('queryStringParameters') or {}
        account_id = query.get('account_id')
        region = query.get('region') or os.environ.get('REGION')
        role_name = os.environ.get('ROLE_NAME')
        next_token = query.get('next_token')

        if not account_id or not role_name:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Missing required parameters',
                    'message': 'account_id and ROLE_NAME are required'
                })
            }

        role_arn = f"arn:aws:iam::{account_id}:role/{role_name}"


        cross_account_client = CrossAccountClient(account_id, role_arn, region)
        if not cross_account_client.assume_role():
            return {
                'statusCode': 500,
                'body': json.dumps({'error': 'Failed to assume cross-account role'})
            }

        rds_client = cross_account_client.get_client('rds')

        db_data, next_token_returned = get_rds_instances(rds_client, next_token)

        return {
            'statusCode': 200,
            'body': json.dumps({
                "rds_data": db_data,
                "next_token": next_token_returned
            }, default=str)
        }

    except Exception as e:
        print(f"Error: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


def get_rds_instances(rds_client, next_token=None):
    cluster_map = {}
    standalone_instances = []
    next_token_out = None

    paginator = rds_client.get_paginator('describe_db_instances')
    pagination_config = {'PageSize': 20}
    if next_token:
        pagination_config['StartingToken'] = next_token

    page_iterator = paginator.paginate(PaginationConfig=pagination_config)

    # Only return first page (for current GET request)
    for page in page_iterator:
        for db in page.get('DBInstances', []):
            instance_id = db['DBInstanceIdentifier']
            is_cluster = 'DBClusterIdentifier' in db

            if is_cluster:
                cluster_id = db['DBClusterIdentifier']
                role = db.get('DBInstanceRole', 'UNKNOWN').capitalize()

                if cluster_id not in cluster_map:
                    cluster_map[cluster_id] = {
                        "type": "cluster",
                        "cluster_id": cluster_id,
                        "instances": []
                    }

                cluster_map[cluster_id]["instances"].append({
                    "id": instance_id,
                    "role": role
                })

            else:
                standalone_instances.append({
                    "id": instance_id
                })

        next_token_out = page.get('NextToken') or page.get('Marker')
        break  # process only one page per call

    result = list(cluster_map.values())
    if standalone_instances:
        result.append({
            "type": "standalone",
            "instances": standalone_instances
        })

    return result, next_token_out
