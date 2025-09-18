import boto3, json

ec2 = boto3.client("ec2")

def lambda_handler(event, context):
    # Extract instance ID from the API Gateway path parameter
    instance_id = event["pathParameters"]["id"]

    try:
        # Terminate the EC2 instance
        ec2.terminate_instances(InstanceIds=[instance_id])

        return {
            "statusCode": 200,
            "body": json.dumps({"message": f"Terminated {instance_id}"})
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
