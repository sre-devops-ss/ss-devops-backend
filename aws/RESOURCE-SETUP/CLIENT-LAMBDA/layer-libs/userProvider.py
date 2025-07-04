#https://github.com/awslabs/aws-support-tools/blob/master/Cognito/decode-verify-jwt/decode-verify-jwt.py

import json
import time
import urllib.request
import os
from typing import List, Optional
from datetime import datetime, timezone
from account_provider import AccountProvider
from account_provider import AccountProvider

region = os.environ["REGION"]
userpool_id = os.environ["USERPOOL_ID"]
app_client_id = os.environ["CLIENT_ID"]

class UserProvider:
    def __init__(self, user_id = None, username = None, groups = None,
                 allowed_accounts = [],
                 created_at = None, updated_at = None):
        self.id = user_id  # Cognito `sub`
        self.username = username
        self.groups = groups
        self.allowed_accounts = allowed_accounts
        self.created_at = created_at or datetime.now(timezone.utc)
        self.updated_at = updated_at or datetime.now(timezone.utc)
        
    
    def varify_jwt(self, token,keys_url=None,app_client_id=None):
        if keys_url is None:
            keys_url = f'https://cognito-idp.{region}.amazonaws.com/{userpool_id}/.well-known/jwks.json'
        if app_client_id is None:
            app_client_id = os.environ["CLIENT_ID"]
        
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
        if claims['aud'] != app_client_id:
            print('Token was not issued for this audience')
            return False
        print(claims)
        return claims

    def to_dict(self):
        return {
            "_id": self.id,
            "username": self.username,
            "groups": self.groups,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
            "allowedAccounts": [acc.to_dict() for acc in self.allowed_accounts],
        }


    def from_dict(self, data):
        return UserProvider(
            user_id=data["_id"],
            username=data.get("username"),
            groups=data.get("groups", []),
            allowed_accounts=[AccountProvider.from_dict(a) for a in data.get("allowedAccounts", [])],
            created_at=data.get("createdAt"),
            updated_at=data.get("updatedAt"),
        )

    def has_group(self, group) -> bool:
        return group in self.groups

    def get_permission_for_account(self, account_id: str, user_data = None) -> Optional[str]:
        if self.allowed_accounts.length != 0:
            for acc in self.allowed_accounts:
                if acc.account_id == account_id and acc.enabled:
                    return True
                else:
                    return False
        else:
            if user_data:
                for acc in user_data.allowed_accounts:
                    if acc.account_id == account_id and acc.enabled:
                        return True
                    else:
                        return False
        # return None

    def get_user_id_from_jwt(self, event): 
        try:
            return event["requestContext"]["authorizer"]["claims"].get("sub")
        except Exception:
            return None
        
    
        
    

