import json
import os
import urllib.request
import ssl
import time
from jose import jwk, jwt
from jose.utils import base64url_decode
 
# === CONFIG ===
COGNITO_REGION = os.environ.get('COGNITO_REGION', 'us-east-1')  # ← Replace with your region
USER_POOL_ID = os.environ.get('USER_POOL_ID', 'xxxxxxxxxxxxxxxx')  # ← Replace with your user pool ID
APP_CLIENT_ID = os.environ.get('APP_CLIENT_ID', 'xxxxxxxxxxxxxxxx')  # ← Replace with your app client ID  # ← Optional: validate aud
ENABLE_GROUP_CHECK = False  # ← Toggle group-based access check
 
# === GROUP ACCESS RULES ===
GROUP_ACCESS_RULES = {
    'admin': ['*'],
    'devops': ['/devops/*'],
    'viewer': ['/readonly/*']
}
 
# === MAIN HANDLER ===
def lambda_handler(event, context):
    print("Event:", json.dumps(event))
 
    token = extract_token_from_event(event)
    method_arn = event["routeArn"]
 
    if not token:
        raise Exception("Unauthorized: No token provided")
 
    try:
        decoded = verify_jwt(token)
        print("Decoded JWT:", decoded)
 
        user_sub = decoded.get("sub", "unknown-user")
        user_groups = decoded.get("cognito:groups", []) or []
        resource_path = get_resource_from_arn(method_arn)
 
        # Authorization check
        if ENABLE_GROUP_CHECK:
            if is_access_allowed(user_groups, resource_path):
                return generate_policy(user_sub, "Allow", method_arn)
            else:
                return generate_policy(user_sub, "Deny", method_arn)
        else:
            # Group check disabled – all valid users allowed
            return generate_policy(user_sub, "Allow", method_arn)
 
    except jwt.ExpiredSignatureError:
        raise Exception("Unauthorized: Token expired")
    #except jwt.InvalidTokenError as e:
    #    print("JWT validation error:", str(e))
    #    raise Exception("Unauthorized: Invalid token")
    
    except Exception as e:
        print("Error:", str(e))
        raise Exception("Unauthorized")
 
 
# === HELPERS ===
def get_resource_from_arn(method_arn):
    # arn:aws:execute-api:{region}:{account}:{api-id}/{stage}/{method}/{resource-path}
    # parts = method_arn.split('/')
    # if len(parts) >= 4:
    #     return f"/{parts[3]}"
    # return "/"
 
    parts = method_arn.split('/')
    if len(parts) >= 4:
        return '/' + '/'.join(parts[3:])
    return "/"
 
 
def is_access_allowed(groups, resource_path):
    for group in groups:
        allowed_paths = GROUP_ACCESS_RULES.get(group, [])
        for path in allowed_paths:
            if path == '*':
                return True
            if path.endswith('/*') and resource_path.startswith(path[:-1]):
                return True
            if resource_path == path:
                return True
    return False
 
 
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