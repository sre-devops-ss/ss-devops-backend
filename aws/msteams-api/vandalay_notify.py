import json
import os
import requests

WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
corsHeaders= {
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Origin': f"*",
    'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
}
def lambda_handler(event, context):
    try:

        message = {
            "text": "🚨 Alert: New event received!",
            "event": event
        }

        response = requests.post(
            WEBHOOK_URL,
            data=json.dumps(message),
            headers=corsHeaders
        )

  
        print(f"Webhook response: {response.status_code}, {response.text}")
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Notification sent', 'status': response.status_code})
        }

    except Exception as e:
        print(f"Error sending webhook: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
