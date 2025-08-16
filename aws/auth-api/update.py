import os
import json
import boto3

client = boto3.client("cognito-idp")
lambda_client = boto3.client("lambda")
ssm_client = boto3.client("ssm")
cf_client = boto3.client("cloudformation")


USER_POOL_ID = os.getenv("COGNITO_USER_POOL_ID", "ap-south-1_Bch3jYn0q")
ORIGIN = os.getenv("DOMAIN", "localhost")
SSM_PARAM = "/dashboard/client"

headers = {
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Origin': f"{ORIGIN}",
    'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
}

def apiResponse(message, statuscode):
    return {
        'headers': headers,
        "statusCode": statuscode,
        "body": json.dumps({"message": message})
    }

def update_ssm_parameter(account_id, account_name):
    """Updates the JSON in SSM Parameter Store with new account_id → account_name."""
    try:
        try:
            response = ssm_client.get_parameter(Name=SSM_PARAM)
            current_value = json.loads(response["Parameter"]["Value"])
        except ssm_client.exceptions.ParameterNotFound:
            current_value = {}

        current_value[account_id] = account_name

        ssm_client.put_parameter(
            Name=SSM_PARAM,
            Value=json.dumps(current_value),
            Type="String",
            Overwrite=True
        )

        print(f"✅ Updated SSM Parameter: {SSM_PARAM} → {account_id}: {account_name}")
        return True

    except Exception as e:
        print(f"❌ Failed to update SSM Parameter: {str(e)}")
        return False



def create_client_lambda_stack(event, context):
    """
    Event should contain:
    {
        "account_id": "1234567890",
        "account_name": "test"
    }
    """
    try:
        account_id = event["account_id"]
        account_name = event["account_name"]

        stack_name = f"CreateLambda-{account_id}"
        s3_template_url = os.getenv("CF_TEMPLATE_URL")

        try:
            response = cf_client.create_stack(
                StackName=stack_name,
                TemplateURL=s3_template_url,
                Parameters=[
                    {"ParameterKey": "AccountId", "ParameterValue": account_id},
                    {"ParameterKey": "AccountName", "ParameterValue": account_name}
                ],
                Capabilities=["CAPABILITY_IAM", "CAPABILITY_NAMED_IAM"],
            )
            message = f"Stack {stack_name} creation initiated."
        except cf_client.exceptions.AlreadyExistsException:
            response = cf_client.update_stack(
                StackName=stack_name,
                TemplateURL=s3_template_url,
                Parameters=[
                    {"ParameterKey": "AccountId", "ParameterValue": account_id},
                    {"ParameterKey": "AccountName", "ParameterValue": account_name}
                ],
                Capabilities=["CAPABILITY_IAM", "CAPABILITY_NAMED_IAM"],
            )
            message = f"Stack {stack_name} update initiated."

        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": message,
                "stackId": response.get("StackId")
            })
        }

    except Exception as e:
        print("Error:", str(e))
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }

def lambda_handler(event, context):
    try:
        print("Event:", event)
        body = json.loads(event.get("body", "{}"))
        print("Request Body:", body)

        account = event["account_name"].strip('"')
        account_id = event["account_id"].strip('"')
        user_sub = event["user_sub"].strip('"')
        print("Account:", account)

        if user_sub:
            # Update Parameter Store
            update_success = update_ssm_parameter(account_id, account)

            # Call resource-Monitoring Lambda
            lambda_client.invoke(
                FunctionName="resource-Monitoring",
                InvocationType="RequestResponse",
                Payload=json.dumps(event)
            )
            lambda_client.invoke(
                FunctionName="insert-client",
                InvocationType="RequestResponse",
                Payload=json.dumps(event)
            )

            return apiResponse(
                f"User {account} updated successfully. "
                f"SSM Update: {'OK' if update_success else 'FAILED'}",
                200
            )

        return apiResponse("User sub not provided", 400)

    except Exception as e:
        print("Error:", str(e))
        return apiResponse(f"Internal Server Error: {str(e)}", 500)
