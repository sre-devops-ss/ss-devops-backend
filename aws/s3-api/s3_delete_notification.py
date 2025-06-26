

import json
import os
import boto3
import logging
from utils.cross_account import CrossAccountClient

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class S3DeleteNotifier:
    def __init__(self, account_client):
        self.s3 = account_client.get_client("s3")
        self.sns = account_client.get_client("sns")

    def add_delete_notification(self, bucket_name, sns_topic_arn=None, sns_topic_name=None):
        if not sns_topic_arn and sns_topic_name:
            response = self.sns.list_topics()
            for topic in response.get("Topics", []):
                if topic["TopicArn"].endswith(f":{sns_topic_name}"):
                    sns_topic_arn = topic["TopicArn"]
                    break

        if not sns_topic_arn:
            raise Exception("SNS topic ARN not found")

        try:
            existing_config = self.s3.get_bucket_notification_configuration(Bucket=bucket_name)

            existing_config.setdefault('TopicConfigurations', [])
            existing_config['TopicConfigurations'].append({
                'Id': f"{bucket_name}-delete-events",
                'TopicArn': sns_topic_arn,
                'Events': ['s3:ObjectRemoved:*']
            })

            self.s3.put_bucket_notification_configuration(
                Bucket=bucket_name,
                NotificationConfiguration=existing_config
            )

            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'Delete event notification added',
                    'bucket': bucket_name,
                    'sns_topic_arn': sns_topic_arn
                })
            }
        except Exception as e:
            logger.error(f"Notification setup failed: {str(e)}")
            raise


def lambda_handler(event, context):
    try:
        body = json.loads(event.get("body", "{}"))
        bucket_name = body.get("bucket_name")
        account_id = body.get("account_id")
        region = body.get("region") or os.environ.get("REGION")

        sns_topic_arn_parameter_arn = "/devops-backend/snstopic/arn"
        sns_topic_name_parameter_name = "/devops-backend/snstopic/name"
            
        if not bucket_name or not account_id:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'bucket_name and account_id are required'})
            }

        role_name = os.environ.get("ROLE_NAME")
        role_arn = f"arn:aws:iam::{account_id}:role/{role_name}"

        client = CrossAccountClient(account_id, role_arn, region)
        client.assume_role()
        
        ssm_client = client.get_client("ssm")
        sns_arn_responce = ssm_client.get_parameter(
            Name=sns_topic_arn_parameter_arn,
            WithDecryption=False )

        sns_topic_arn =  body.get("sns_topic_arn") or sns_arn_responce['Parameter']['Value']

        sns_name_responce = ssm_client.get_parameter(
            Name=sns_topic_name_parameter_name,
            WithDecryption=False )

        sns_topic_name = body.get("sns_topic_name") or sns_name_responce['Parameter']['Value']

        notifier = S3DeleteNotifier(client)
        
        return notifier.add_delete_notification(bucket_name, sns_topic_arn, sns_topic_name)

    except Exception as e:
        logger.error(f"Lambda error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
