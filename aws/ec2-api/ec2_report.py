import boto3
import json
from datetime import datetime
import urllib3
http = urllib3.PoolManager()
import time



ssm = boto3.client('ssm')
sts = boto3.client('sts')
API_GATEWAY_URL = "https://xjgkd4ty8i.execute-api.ap-south-1.amazonaws.com/dashboard/dump"

def process_account(cross_account_id, account_name):
    all_instances = []
    try:
        credentials = assume_role(cross_account_id, "devops-ui-cross-account")
        lambda_client = boto3.client('lambda', **credentials)
        apigateway_client = boto3.client('apigateway', **credentials)
        ec2_client = boto3.client('ec2', **credentials)
        region = boto3.session.Session().region_name
        print("region", region)

        function_description, api_url = check_lambda_function_and_get_description("ipwhitelist", lambda_client, apigateway_client)
        print("Function description:", function_description)

        instance_list = list_ec2_instances(function_description, api_url, ec2_client, cross_account_id, region)
        print("Instance list:", instance_list)

        if instance_list:
            result = {
                "db": account_name,
                "collection": "ec2_instances",
                "method": "insert-ec2",
                "body": instance_list
            }
            print("Sending result for account:", cross_account_id)
            invoke_api_gateway(result)

        all_instances.extend(instance_list)

    except Exception as account_error:
        print(f"Error processing account {cross_account_id}: {str(account_error)}")

    return all_instances

def assume_role(account_id, role_name):
    RoleArn=f'arn:aws:iam::{account_id}:role/{role_name}'
    print(RoleArn)
    assumed_role = sts.assume_role(
        RoleArn=f'arn:aws:iam::{account_id}:role/{role_name}',
        RoleSessionName='AssumedRoleSession'
    )
    
    creds = assumed_role['Credentials']
    return {
        "aws_access_key_id": creds['AccessKeyId'],
        "aws_secret_access_key": creds['SecretAccessKey'],
        "aws_session_token": creds['SessionToken']
    }

def check_lambda_function_and_get_description(function_name, lambda_client, apigateway_client):
    try:
        response = lambda_client.get_function(FunctionName=function_name)
        print("response", response)
        function_description = response['Configuration'].get('Description', 'No description provided.')
        function_arn = response['Configuration']['FunctionArn']

        api_url = None
        apis = apigateway_client.get_rest_apis()
        for api in apis['items']:
            api_id = api['id']
            resources = apigateway_client.get_resources(restApiId=api_id)
            for resource in resources['items']:
                if 'resourceMethods' in resource:
                    for method in resource['resourceMethods']:
                        integration = apigateway_client.get_integration(
                            restApiId=api_id,
                            resourceId=resource['id'],
                            httpMethod=method
                        )
                        if 'uri' in integration:
                            integration_uri = integration['uri']
                            if function_arn in integration_uri:
                                region = boto3.session.Session().region_name
                                stage = 'default'
                                api_url = f"https://{api_id}.execute-api.{region}.amazonaws.com/{stage}"
                                return function_description, api_url

        return function_description, api_url

    except lambda_client.exceptions.ResourceNotFoundException:
        print(f"Lambda function '{function_name}' does not exist.")
        return None, None

    except Exception as e:
        print(f"Error checking Lambda function: {e}")
        return None, None

def list_ec2_instances(function_description, api_url, ec2_client, account_id, region):
    instances_data = []
    try:
        print("ec2_client", ec2_client)
        response = ec2_client.describe_instances()
        print("response.................", response)
        sg_ids_from_description = []
        if function_description:
            sg_ids_from_description = [sg.strip() for sg in function_description.split() if 'sg-' in sg]

        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                security_groups = [sg['GroupId'] for sg in instance.get('SecurityGroups', [])]
                instance_name = next((tag['Value'] for tag in instance.get('Tags', []) if tag['Key'] == 'Name'), None)
                matched_sgs = list(set(security_groups) & set(sg_ids_from_description))

                instance_info = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "AccountId": account_id,
                    "Region": region,
                    "InstanceId": instance.get('InstanceId'),
                    "InstanceType": instance.get('InstanceType'),
                    "State": instance.get('State', {}).get('Name'),
                    "PrivateIpAddress": instance.get('PrivateIpAddress'),
                    "PublicIpAddress": instance.get('PublicIpAddress'),
                    "LaunchTime": instance.get('LaunchTime').isoformat() if instance.get('LaunchTime') else None,
                    "SecurityGroupIds": security_groups,
                    "InstanceName": instance_name,
                }

                if matched_sgs:
                    instance_info["WhitelistAPI"] = api_url

                instances_data.append(instance_info)

    except Exception as e:
        print(f"Error retrieving EC2 instances: {e}")
    
    return instances_data

def invoke_api_gateway(data):
    """Invoke API Gateway URL asynchronously using urllib3."""
    try:
        headers = {"Content-Type": "application/json"}

        # Fire and forget, without waiting for the response
        http.request(
            "POST",
            API_GATEWAY_URL,
            body=json.dumps(data).encode("utf-8"),
            headers=headers,
            preload_content=False
        )

        print("API Gateway request sent successfully.")
        return {"status": "success", "message": "API request sent"}

    except Exception as e:
        print(f"Failed to invoke API Gateway: {str(e)}")
        return {"status": "error", "message": str(e)}



def lambda_handler(event, context):
    try:
        print(event)
        all_results = []

        if 'method' in event:
            print("Key 'method' found!")
            cross_account_id = event.get('account_id', '').strip('"')
            account_name = event.get('account_name', '').strip('"')
            all_results.extend(
                process_account(cross_account_id, account_name)
            )
            time.sleep(2)

        else:
            PARAMETER_NAME = "/dashboard/client"
            response = ssm.get_parameter(Name=PARAMETER_NAME, WithDecryption=True)
            account_lines = response['Parameter']['Value'].splitlines()
            for line in account_lines:
                if ':' in line:
                    cross_account_id, account = map(str.strip, line.split(':'))
                    cross_account_id = cross_account_id.strip('"')
                    account_name = account.split('-')[0].strip()
                    print("Processing account:", account_name)
                    all_results.extend(
                        process_account(cross_account_id, account_name)
                    )

        return {
            "statusCode": 200,
            "body": json.dumps(all_results, indent=2),
            "headers": {"Content-Type": "application/json"}
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}),
            "headers": {"Content-Type": "application/json"}
        }


