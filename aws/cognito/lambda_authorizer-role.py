import json
import os
import urllib.request
import ssl
import time
from jose import jwk, jwt
from jose.utils import base64url_decode

# === CONFIG ===
COGNITO_REGION = os.environ.get('REGION', 'us-east-1') 
USER_POOL_ID = os.environ.get('USER_POOL_ID', 'xxxxxxxxxxxxxxxx')  
APP_CLIENT_ID = os.environ.get('APP_CLIENT_ID', 'xxxxxxxxxxxxxxxx')  

PERMIT_POLICY = [
    {
        'group': 'admin',
        'actions': ['post /create', '*'],  # '*' means all actions
        'resources': ['*']  # '*' means all endpoints
    },
    {
        'group': 'devops',
        'actions': ['get /devops', 'post /devops'],
        'resources': ['/devops/*']
    },
    {
        'group': 'viewer',
        'actions': ['get /readonly'],
        'resources': ['/readonly/*']
    }
]

# === MAIN HANDLER ===
def lambda_handler(event, context):
    print("Event:", json.dumps(event))

    token = extract_token_from_event(event)
    method_arn = event["routeArn"]
    http_method = event.get("requestContext", {}).get("http", {}).get("method", "").lower()
    resource_path = get_resource_from_arn(method_arn)
    action_string = f"{http_method} {resource_path}" if http_method and resource_path else None

    if not token:
        raise Exception("Unauthorized: No token provided")

    try:
        decoded = verify_jwt(token)
        print("Decoded JWT:", decoded)

        user_sub = decoded.get("sub", "unknown-user")
        user_groups = decoded.get("cognito:groups", [])
        resource_path = get_resource_from_arn(method_arn)

        # Authorization check using PERMIT_POLICY
        if is_policy_permit(user_groups, action_string, resource_path):
            return generate_policy(user_sub, "Allow", method_arn)
        else:
            return generate_policy(user_sub, "Deny", method_arn)

    except jwt.ExpiredSignatureError:
        raise Exception("Unauthorized: Token expired")
    #except jwt.InvalidTokenError as e:
    #    print("JWT validation error:", str(e))
    #    raise Exception("Unauthorized: Invalid token")

    except Exception as e:
        print("Error:", str(e))
        raise Exception("Unauthorized")


def is_policy_permit(groups, action, resource):
    for group in groups:
        for policy in PERMIT_POLICY:
            if policy['group'] == group:
                # Check action
                if '*' in policy['actions'] or action in policy['actions']:
                    # Check resource
                    for allowed_resource in policy['resources']:
                        if allowed_resource == '*' or resource.startswith(allowed_resource.rstrip('*')):
                            return True
    return False
# === HELPERS ===
def get_resource_from_arn(method_arn):
    parts = method_arn.split('/')
    if len(parts) >= 4:
        return '/' + '/'.join(parts[3:])
    return "/"



def generate_policy(principal_id, effect, resource):
    print("Generating policy:", principal_id, effect, resource)
    return {
        "principalId": principal_id,
        "policyDocument": {
            "Version": "2012-10-17",
            "Statement": [{
                "Action": "execute-api:Invoke",
                "Effect": effect,
                "Resource": resource
            }]
        }
    }
# === TOKEN EXTRACTION ===
def extract_token_from_event(event):
    """
    Extract the authorization token from various possible locations in the event
    """
    # Method 1: Check identitySource array (Lambda authorizer v2 format)
    if "identitySource" in event and isinstance(event["identitySource"], list):
        for source in event["identitySource"]:
            if source and source.startswith("Bearer "):
                return source.replace("Bearer ", "")

    # Method 2: Check headers (standard API Gateway format)
    headers = event.get("headers", {})
    if headers:
        # Check for authorization header (case-insensitive)
        for header_name, header_value in headers.items():
            if header_name.lower() == "authorization" and header_value:
                return header_value.replace("Bearer ", "")

    # Method 3: Check direct authorization field (if present)
    if "authorization" in event:
        auth_value = event["authorization"]
        if auth_value and auth_value.startswith("Bearer "):
            return auth_value.replace("Bearer ", "")

    # Method 4: Check authorizationToken (Lambda authorizer v1 format)
    if "authorizationToken" in event:
        auth_token = event["authorizationToken"]
        if auth_token and auth_token.startswith("Bearer "):
            return auth_token.replace("Bearer ", "")

    return None

def verify_jwt(token,keys_url=None,app_client_id=None):
    if keys_url is None:
        keys_url = f'https://cognito-idp.{COGNITO_REGION}.amazonaws.com/{USER_POOL_ID}/.well-known/jwks.json'
    if app_client_id is None:
        app_client_id = os.environ["APP_CLIENT_ID"]

    with urllib.request.urlopen(keys_url) as f:
        response = f.read()
    keys = json.loads(response.decode('utf-8'))['keys']

    # token = event['token']
    headers = jwt.get_unverified_headers(token)
    kid = headers['kid']
    key_index = -1
    for i in range(len(keys)):
        if kid == keys[i]['kid']:
            key_index = i
            break
    if key_index == -1:
        print('Public key not found in jwks.json')
        return False
    public_key = jwk.construct(keys[key_index])

    message, encoded_signature = str(token).rsplit('.', 1)
    decoded_signature = base64url_decode(encoded_signature.encode('utf-8'))
    if not public_key.verify(message.encode("utf8"), decoded_signature):
        print('Signature verification failed')
        return False
    print('Signature successfully verified')
    claims = jwt.get_unverified_claims(token)
    if time.time() > claims['exp']:
        print('Token is expired')
        return False
    if claims['client_id'] != app_client_id:
        print('Token was not issued for this audience')
        return False
    print(claims)
    return claims
 