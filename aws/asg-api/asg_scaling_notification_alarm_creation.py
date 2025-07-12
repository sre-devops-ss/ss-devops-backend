import boto3
import json
import logging
from utils.cross_account import CrossAccountClient
from utils.authenticate_user_role import UserAuthenticator

logger = logging.getLogger()
logger.setLevel(logging.INFO)

cloudwatch = boto3.client("cloudwatch")
headers= {
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Origin': f"*",
    'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
} 

def create_scaling_alarm(asg_name, config, alarm_actions):
    dimensions = [{'Name': 'AutoScalingGroupName', 'Value': asg_name}]
    cloudwatch.put_metric_alarm(
        AlarmName=f"{asg_name}-scaling-activity",
        MetricName="GroupInServiceInstances",
        Namespace="AWS/AutoScaling",
        Statistic="Average",
        Period=config['period'],
        EvaluationPeriods=config['evaluation_periods'],
        Threshold=config['scaling_threshold'],
        ComparisonOperator="LessThanThreshold",
        AlarmDescription="ASG may be under-scaled",
        Dimensions=dimensions,
        AlarmActions=alarm_actions
    )
    logger.info(f"Scaling alarm created for ASG: {asg_name}")


def lambda_handler(event, context):
    try:
        body = json.loads(event.get('body', '{}'))
        asg_name = body['asg_name']
        account_id = body['account_id']
        region = body.get("region", os.environ.get("AWS_REGION"))

        authenticator = UserAuthenticator()
        auth_result = authenticator.authenticate_user_account(event)
        authenticator.close_connection()
        
        if auth_result["statusCode"] != 200:
            return {
                "statusCode": 403,
                "headers": headers,
                "body": json.dumps("user not authorized")
            }  

        config = {
            'scaling_threshold': body.get('scaling_threshold', 1),
            'period': body.get('period', 60),
            'evaluation_periods': body.get('evaluation_periods', 1),
            'alarm_actions': body.get('alarm_actions', [])
        }
        role_arn = f"arn:aws:iam::{account_id}:role/{os.environ['ROLE_NAME']}"
        client = CrossAccountClient(account_id, role_arn, region)
        client.assume_role()

        ssm = client.get_client("ssm")
        sns_topic_arn = ssm.get_parameter(
            Name="/devops-backend/snstopic/arn",
            WithDecryption=False
        )["Parameter"]["Value"]

        if sns_topic_arn not in config["alarm_actions"]:
            config["alarm_actions"].append(sns_topic_arn)

        cloudwatch = client.get_client("cloudwatch")


        create_scaling_alarm(asg_name, config, config["alarm_actions"])

        return {'statusCode': 200, 'headers': headers, 'body': json.dumps({'message': 'Scaling alarm created'})}

    except Exception as e:
        logger.error(str(e))
        return {'statusCode': 500, 'headers': headers, 'body': json.dumps({'error': str(e)})}
