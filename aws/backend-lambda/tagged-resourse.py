
import boto3
import json
import urllib3
import logging
from botocore.exceptions import ClientError
from datetime import datetime

API_GATEWAY_URL = "https://xjgkd4ty8i.execute-api.ap-south-1.amazonaws.com/dashboard/dump"

# Init HTTP client + logger
http = urllib3.PoolManager()
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def invoke_api_gateway(data):
    """Invoke API Gateway URL asynchronously using urllib3."""
    try:
        headers = {"Content-Type": "application/json"}
        http.request(
            "POST",
            API_GATEWAY_URL,
            body=json.dumps(data).encode("utf-8"),
            headers=headers,
            preload_content=False
        )
        logger.info("API Gateway request sent successfully.")
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Failed to invoke API Gateway: {str(e)}")
        return {"status": "error", "message": str(e)}

def lambda_handler(event, context):
    resources_report = {}

    def add_resource(service, resource_id, tags):
        """Helper to add resource with tag status and details"""
        resources_report.setdefault(service, []).append({
            "ResourceId": resource_id,
            "HasTags": bool(tags),
            "Tags": tags if tags else []
        })

    # -------------------- 1. Generic Resources --------------------
    tagging_client = boto3.client('resourcegroupstaggingapi')
    paginator = tagging_client.get_paginator('get_resources')
    for page in paginator.paginate(ResourcesPerPage=50):
        for resource in page.get('ResourceTagMappingList', []):
            arn = resource['ResourceARN']
            service = arn.split(":")[2] if ":" in arn else "Other"
            tags = resource.get('Tags', [])
            add_resource(service, arn, tags)

    # -------------------- 2. S3 Buckets --------------------
    s3_client = boto3.client('s3')
    for bucket in s3_client.list_buckets().get('Buckets', []):
        bucket_name = bucket['Name']
        tags = []
        try:
            tags = s3_client.get_bucket_tagging(Bucket=bucket_name).get('TagSet', [])
        except ClientError as e:
            if e.response['Error']['Code'] != 'NoSuchTagSet':
                raise
        add_resource("S3", bucket_name, tags)

    # -------------------- 3. EC2 Instances --------------------
    ec2_client = boto3.client('ec2')
    for reservation in ec2_client.describe_instances().get('Reservations', []):
        for instance in reservation.get('Instances', []):
            add_resource("EC2", instance['InstanceId'], instance.get('Tags', []))

    # -------------------- 4. RDS --------------------
    rds_client = boto3.client('rds')
    for db in rds_client.describe_db_instances().get('DBInstances', []):
        arn = db['DBInstanceArn']
        tags = rds_client.list_tags_for_resource(ResourceName=arn).get('TagList', [])
        add_resource("RDS", db['DBInstanceIdentifier'], tags)

    # -------------------- 5. Lambda --------------------
    lambda_client = boto3.client('lambda')
    for fn in lambda_client.list_functions().get('Functions', []):
        arn = fn['FunctionArn']
        tags = lambda_client.list_tags(Resource=arn).get('Tags', {})
        tag_list = [{"Key": k, "Value": v} for k, v in tags.items()] if tags else []
        add_resource("Lambda", fn['FunctionName'], tag_list)

    # -------------------- 6. ECS --------------------
    ecs_client = boto3.client('ecs')
    for cluster_arn in ecs_client.list_clusters().get('clusterArns', []):
        tags = ecs_client.list_tags_for_resource(resourceArn=cluster_arn).get('tags', [])
        add_resource("ECS-Clusters", cluster_arn, tags)
        for task_arn in ecs_client.list_tasks(cluster=cluster_arn).get('taskArns', []):
            tags = ecs_client.list_tags_for_resource(resourceArn=task_arn).get('tags', [])
            add_resource("ECS-Tasks", task_arn, tags)

    # -------------------- 7. VPCs --------------------
    for vpc in ec2_client.describe_vpcs().get('Vpcs', []):
        add_resource("VPC", vpc['VpcId'], vpc.get('Tags', []))

    # -------------------- 8. Subnets --------------------
    for subnet in ec2_client.describe_subnets().get('Subnets', []):
        add_resource("Subnet", subnet['SubnetId'], subnet.get('Tags', []))

    # -------------------- 9. Security Groups --------------------
    for sg in ec2_client.describe_security_groups().get('SecurityGroups', []):
        add_resource("SecurityGroup", sg['GroupId'], sg.get('Tags', []))

    # -------------------- 10. CloudFormation --------------------
    cf_client = boto3.client('cloudformation')
    for stack in cf_client.list_stacks(StackStatusFilter=['CREATE_COMPLETE','UPDATE_COMPLETE']).get('StackSummaries', []):
        stack_name = stack['StackName']
        tags = cf_client.describe_stacks(StackName=stack_name)['Stacks'][0].get('Tags', [])
        add_resource("CloudFormation", stack_name, tags)

    # -------------------- 11. IAM --------------------
    iam_client = boto3.client('iam')
    for role in iam_client.list_roles().get('Roles', []):
        tags = iam_client.list_role_tags(RoleName=role['RoleName']).get('Tags', [])
        add_resource("IAM-Roles", role['RoleName'], tags)
    for user in iam_client.list_users().get('Users', []):
        tags = iam_client.list_user_tags(UserName=user['UserName']).get('Tags', [])
        add_resource("IAM-Users", user['UserName'], tags)

    # -------------------- 12. CloudTrail --------------------
    ct_client = boto3.client('cloudtrail')
    for trail in ct_client.describe_trails()['trailList']:
        arn = trail['TrailARN']
        tag_list = []
        for res in ct_client.list_tags(ResourceIdList=[arn]).get('ResourceTagList', []):
            tag_list.extend(res.get("TagsList", []))
        add_resource("CloudTrail", trail['Name'], tag_list)

    # -------------------- 13. Config Rules --------------------
    config_client = boto3.client('config')
    for rule in config_client.describe_config_rules().get('ConfigRules', []):
        tags = config_client.list_tags_for_resource(ResourceArn=rule['ConfigRuleArn']).get('Tags', {})
        tag_list = [{"Key": k, "Value": v} for k, v in tags.items()] if tags else []
        add_resource("ConfigRules", rule['ConfigRuleName'], tag_list)

    # -------------------- Final Response --------------------
    report_date = datetime.utcnow().strftime("%Y-%m-%d")
    sts_client = boto3.client("sts")
    # account_id = sts_client.get_caller_identity()["Account"]
    account_id = "979453078508"
    account_name = "supportsages"

    mongo_docs = []
    for service, resources in resources_report.items():
        mongo_docs.append({
            "Service": service,
            "Resources": resources,
            "Count": len(resources),
            "ReportDate": report_date
        })

    result = {
        "db": account_name,
        "collection": "tagging",
        "method": "tagged_resources",
        "body": mongo_docs
    }
    print(result)
    logger.info(f"DEBUG | Final result payload: {json.dumps(result)[:300]}")

    if mongo_docs:
        invoke_api_gateway(result)

    return {"statusCode": 200, "body": json.dumps(result)}
