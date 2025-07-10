import boto3
import json
import os
from utils.cross_account import CrossAccountClient

def lambda_handler(event, context):
    body = json.loads(event.get("body", "{}"))
    budget_name = body.get("budget_name", "MonthlyCostBudget")
    amount = body.get("amount", 100)  # Budget in USD
    account_id = body.get("account_id")
    region = body.get("region", os.environ.get("AWS_REGION"))

    # Assume cross-account role
    role_arn = f"arn:aws:iam::{account_id}:role/{os.environ['ROLE_NAME']}"
    client = CrossAccountClient(account_id, role_arn, region)
    client.assume_role()

    ssm = client.get_client("ssm")
    sns_topic_arn = ssm.get_parameter(
        Name="/devops-backend/snstopic/arn",
        WithDecryption=False
    )["Parameter"]["Value"]

    alarm_actions = [sns_topic_arn]

    budgets = client.get_client("budgets")

    response = budgets.create_budget(
        AccountId=account_id,
        Budget={
            "BudgetName": budget_name,
            "BudgetLimit": {
                "Amount": str(amount),
                "Unit": "USD"
            },
            "CostFilters": {},
            "CostTypes": {
                "IncludeTax": True,
                "IncludeSubscription": True,
                "UseBlended": False,
                "IncludeRefund": False
            },
            "TimeUnit": "MONTHLY",
            "BudgetType": "COST"
        },
        NotificationsWithSubscribers=[
            {
                "Notification": {
                    "NotificationType": "ACTUAL",
                    "ComparisonOperator": "GREATER_THAN",
                    "Threshold": 80,
                    "ThresholdType": "PERCENTAGE"
                },
                "Subscribers": [
                    {
                        "SubscriptionType": "SNS",
                        "Address": sns_topic_arn
                    }
                ]
            }
        ]
    )

    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Budget created", "response": response})
    }
