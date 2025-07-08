import boto3
import json

budgets = boto3.client('budgets')

def lambda_handler(event, context):
    budget_name = event.get('budget_name', 'Monthly-Budget')
    account_id = event.get('account_id')
    sns_arn = event.get('sns_topic_arn')

    budget = {
        'BudgetName': budget_name,
        'BudgetLimit': {
            'Amount': '100',
            'Unit': 'USD'
        },
        'TimeUnit': 'MONTHLY',
        'BudgetType': 'COST',
        'CostFilters': {},
        'TimePeriod': {
            'Start': '2024-01-01T00:00:00Z',
            'End': '2087-12-31T00:00:00Z'
        }
    }

    notification = {
        'Notification': {
            'NotificationType': 'ACTUAL',
            'Threshold': 80,
            'ThresholdType': 'PERCENTAGE',
            'ComparisonOperator': 'GREATER_THAN'
        },
        'Subscribers': [
            {
                'SubscriptionType': 'SNS',
                'Address': sns_arn
            }
        ]
    }

    budgets.create_budget(AccountId=account_id, Budget=budget)
    budgets.create_notification(AccountId=account_id, BudgetName=budget_name, Notification=notification['Notification'], Subscribers=notification['Subscribers'])

    return {
        'statusCode': 200,
        'body': json.dumps(f"Budget alarm {budget_name} created")
    }
