import boto3
import json
import os
from datetime import datetime, timezone

iam_client = boto3.client("iam")

INACTIVE_DAYS_THRESHOLD = int(os.getenv("INACTIVE_DAYS_THRESHOLD", 90))

headers= {
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Origin': f"*",
    'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
}

def process_role(role):
    role_name = role["RoleName"]
    creation_time = role["CreateDate"]
    
    role_details = iam_client.get_role(RoleName=role_name)
    last_used_info = role_details["Role"].get("RoleLastUsed", {})

    last_used_date = last_used_info.get("LastUsedDate")
    if not last_used_date:
        last_used_str = "Never Used"
        days_since_used = "N/A"
        status = "Inactive"
    else:
        last_used_date = last_used_date.replace(tzinfo=timezone.utc)
        days_since_used = (datetime.now(timezone.utc) - last_used_date).days
        last_used_str = last_used_date.isoformat()
        status = "Inactive" if days_since_used > INACTIVE_DAYS_THRESHOLD else "Active"

    attached_policies = iam_client.list_attached_role_policies(RoleName=role_name).get("AttachedPolicies", [])
    policies = [policy["PolicyName"] for policy in attached_policies]

    return {
        "RoleName": role_name,
        "CreationTime": creation_time.isoformat(),
        "LastUsed": last_used_str,
        "DaysSinceUsed": str(days_since_used),
        "Status": status,
        "AttachedPolicies": policies
    }

def lambda_handler(event, context):
    try:
        paginator = iam_client.get_paginator("list_roles")
        roles_with_details = []
        
        for page in paginator.paginate():
            for role in page["Roles"]:
                roles_with_details.append(process_role(role))

        json_response = {
            "statusCode": 200,
            "body": {
                "TotalRoles": len(roles_with_details),
                "INACTIVE_DAYS_THRESHOLD": INACTIVE_DAYS_THRESHOLD,
                "roles": roles_with_details
            },
            "headers": headers
        }

        return json_response

    except Exception as e:
        return {
            "statusCode": 500,
            "body": {"error": str(e)},
            "headers": headers
        }
        