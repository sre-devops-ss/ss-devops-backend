from userProvider import UserProvider
import os
import pymongo
import json


USERNAME = os.environ["MONGO_USERNAME"]
PASSWORD = os.environ["MONGO_PASSWORD"]
HOST = os.environ["MONGO_HOST"]
PORT = os.environ["MONGO_PORT"]
DATABASE = os.environ["MONGO_DATABASE"]

mongo_uri = f"mongodb://{USERNAME}:{PASSWORD}@{HOST}:{PORT}/{DATABASE}?authSource=admin"
client = pymongo.MongoClient(mongo_uri)
db = client[DATABASE]
users_collection = db["users"]

user_provider = UserProvider()

def get_user_id_from_jwt(event): 
    try:
        return event["requestContext"]["authorizer"]["claims"].get("sub")
    except Exception:
        return None
        
def get_user_from_jwt(event):
    user_id = get_user_id_from_jwt(event)
    if not user_id:
        return None
    user_data = users_collection.find_one({"_id": user_id})
    if not user_data:
        return None
    return user_provider.from_dict(user_data)

def check_user_authentication(event):
    body = json.loads(event.get("body", "{}"))
    account_id = body.get("account_id")
    if not account_id:
        return None
    user = get_user_from_jwt(event)
    if not user:
        return None
    return user.get_permission_for_account(account_id)