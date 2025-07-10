import json
import boto3
from botocore.exceptions import ClientError
headers= {
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Origin': f"*",
    'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
}

def lambda_handler(event, context):
    try:
        body = json.loads(event['body'])
        account_id = body.get('account_id')
        region = body.get('region')

        if not account_id or not region:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing account_id or region"})
            }

        ec2_client = boto3.client('ec2', region_name=region)

        response = ec2_client.describe_instances()
        instances = []

        for reservation in response.get('Reservations', []):
            for instance in reservation.get('Instances', []):
                instances.append({
                    "InstanceId": instance.get("InstanceId"),
                    "State": instance.get("State", {}).get("Name"),
                    "InstanceType": instance.get("InstanceType"),
                    "LaunchTime": str(instance.get("LaunchTime")),
                    "Tags": instance.get("Tags", []),
                    "AvailabilityZone": instance.get("Placement", {}).get("AvailabilityZone")
                })

        return {
            "statusCode": 200,
            "headers": headers,
            "body": json.dumps(instances)
        }

    except ClientError as e:
        print(f"ClientError: {e}")
        return {
            "statusCode": 500,
            "headers": headers,
            "body": json.dumps({"error": "Failed to describe instances."})
        }

    except Exception as e:
        print(f"Exception: {e}")
        return {
            "statusCode": 500,
            "headers": headers,
            "body": json.dumps({"error": "Internal server error."})
        }
