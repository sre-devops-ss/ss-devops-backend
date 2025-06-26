import json
import urllib.request
import urllib.error
import logging
import os
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event=None, context=None):
    TEAMS_WEBHOOK_URL = os.environ.get('TEAMS_WEBHOOK_URL')

    try:
        # Dummy SNS CloudWatch-style message
        # sns_message = json.dumps({
        #     "AlarmName": "HighMemoryUsage",
        #     "AlarmDescription": "Memory usage exceeded 90% for more than 5 minutes.",
        #     "NewStateValue": "ALARM",
        #     "NewStateReason": "Threshold Crossed: 1 datapoint (95.0) was greater than the threshold (90.0).",
        #     "Region": "us-east-1",
        #     "StateChangeTime": "2025-06-19T13:45:00Z"
        # })

        sns_message = event['Records'][0]['Sns']['Message']

        logger.info("Received SNS message: %s", sns_message)

        alarm_data = json.loads(sns_message)

        alarm_name = alarm_data.get('AlarmName', 'Unknown Alarm')
        alarm_description = alarm_data.get('AlarmDescription', 'No description')
        state = alarm_data.get('NewStateValue', 'UNKNOWN')
        reason = alarm_data.get('NewStateReason', 'No reason provided')
        region = alarm_data.get('Region', 'Unknown Region')
        timestamp = alarm_data.get('StateChangeTime', 'Unknown Time')

        # Format as code block (monospaced for Teams)
        message_text = f"""```
CloudWatch Alarm Notification

Alarm Name : {alarm_name}
State      : {state}
Description: {alarm_description}
Reason     : {reason}
Region     : {region}
Time       : {timestamp}
```"""

        payload = {
            "text": message_text
        }

        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            TEAMS_WEBHOOK_URL,
            data=data,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )

        with urllib.request.urlopen(req) as response:
            response_data = response.read().decode('utf-8')
            logger.info("Teams response: %s", response_data)

        return {
            'statusCode': 200,
            'body': json.dumps('Formatted notification sent to Teams')
        }

    except urllib.error.HTTPError as e:
        logger.error("HTTP error sending to Teams: %s", e)
        return {
            'statusCode': e.code,
            'body': json.dumps(f"Failed to send notification: {str(e)}")
        }

    except Exception as e:
        logger.error("Error processing SNS message: %s", e)
        return {
            'statusCode': 500,
            'body': json.dumps(f"Error: {str(e)}")
        }

