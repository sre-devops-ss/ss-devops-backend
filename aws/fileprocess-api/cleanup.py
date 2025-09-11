import boto3, json

ec2 = boto3.client("ec2")

def lambda_handler(event, context):
    instance_id = event["pathParameters"]["id"]
    ec2.stop_instances(InstanceIds=[instance_id])
    return {
        "statusCode": 200,
        "body": json.dumps({"message": f"Stopped {instance_id}"})
    }
