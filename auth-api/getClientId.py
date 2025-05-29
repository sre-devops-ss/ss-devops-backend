import boto3
import os

client = boto3.client('cognito-idp')

USER_POOL_ID = os.environ.get('COGNITO_USER_POOL')
CLIENT_ID = os.environ.get('COGNITO_USER_POOL_ID')  


def lambda_handler(event, context):
    refresh_token = event.get('refresh_token')

    if not refresh_token:
        return {
            'statusCode': 400,
            'body': 'Refresh token is required'
        }

    try:
        response = client.admin_initiate_auth(
            UserPoolId=USER_POOL_ID,
            ClientId=CLIENT_ID,
            AuthFlow='REFRESH_TOKEN_AUTH',
            AuthParameters={
                'REFRESH_TOKEN': refresh_token
               
            }
        )

        access_token = response['AuthenticationResult']['AccessToken']
        id_token = response['AuthenticationResult'].get('IdToken')
        expires_in = response['AuthenticationResult'].get('ExpiresIn')

        return {
            'statusCode': 200,
            'body': {
                'access_token': access_token,
                'id_token': id_token,
                'expires_in': expires_in
            }
        }

    except client.exceptions.NotAuthorizedException:
        return {
            'statusCode': 401,
            'body': 'Invalid refresh token or client configuration'
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'body': str(e)
        }
