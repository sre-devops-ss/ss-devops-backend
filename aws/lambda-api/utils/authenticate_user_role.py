import json
import os
from typing import Dict, Optional, Any, Tuple
from pymongo import MongoClient


class UserAuthenticationError(Exception):
    pass


class UserAuthenticator:
    
    def __init__(self, mongodb_uri: Optional[str] = None):
        self.mongodb_uri = mongodb_uri or os.environ.get("MONGODB_URI")
        self.db_name = "user"
        self.collection_name = "user"
        self._client: Optional[MongoClient] = None
        self._db: Optional[Any] = None
        self._collection: Optional[Any] = None
    
    def _get_mongodb_connection(self) -> Any:

        try:
            if not self._client:
                self._client = MongoClient(self.mongodb_uri)
                self._db = self._client[self.db_name]
                self._collection = self._db[self.collection_name]
            return self._collection
        except Exception as e:
            raise UserAuthenticationError(f"Failed to connect to MongoDB: {str(e)}")
    
    def _validate_input_data(self, body: Dict[str, Any]) -> Tuple[str, str, str]:
        sub = body.get("sub")
        acc_name = body.get("accountName")
        acc_uid = body.get("accUid")
        
        if not all([sub, acc_name, acc_uid]):
            raise UserAuthenticationError("Missing required fields: sub, accountName, accUid")
        
        # Type assertion since we've validated they're not None
        return str(sub), str(acc_name), str(acc_uid)
    
    def _find_user_document(self, sub: str) -> Optional[Dict[str, Any]]:
        collection = self._get_mongodb_connection()
        query = {f"user.{sub}": {"$exists": True}}
        return collection.find_one(query)
    
    def _find_account(self, user_data: Dict[str, Any], account_name: str, account_uid: str) -> Optional[Dict[str, Any]]:
        accounts = user_data.get("account", [])
        
        for account in accounts:
            if (account.get("accountName") == account_name and 
                account.get("accUid") == account_uid):
                return account
        
        return None
    
    def authenticate_user_account(self, event: Dict[str, Any]) -> Dict[str, Any]:

        try:
            body = event.get("body", {})
            if isinstance(body, str):
                body = json.loads(body)
            
            sub, account_name, account_uid = self._validate_input_data(body)
            
            # Find user document
            user_doc = self._find_user_document(sub)
            if not user_doc:
                return {
                    "statusCode": 404,
                    "body": json.dumps({"error": "User not found"})
                }
            
            # Get user data
            user_data = user_doc["user"][sub]
            
            # Find account
            account = self._find_account(user_data, account_name, account_uid)
            if not account:
                return {
                    "statusCode": 404,
                    "body": json.dumps({"error": "Account not found"})
                }
            
            # Return successful response
            return {
                "statusCode": 200,
                "body": json.dumps({"accountId": account["accountId"]})
            }
            
        except UserAuthenticationError as e:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": str(e)})
            }
        except json.JSONDecodeError:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Invalid JSON in request body"})
            }
        except Exception as e:
            return {
                "statusCode": 500,
                "body": json.dumps({"error": f"Internal server error: {str(e)}"})
            }
    
    def close_connection(self):
        if self._client:
            self._client.close()
            self._client = None
            self._db = None
            self._collection = None