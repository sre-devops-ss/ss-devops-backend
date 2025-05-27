import boto3
import json
import requests
import os

ssm = boto3.client('ssm')

REFRESH_PARAM = "/aws-monitor/ss-backend/refresh_token"
ACCESS_PARAM = "/aws-monitor/ss-backend/access_token"
ORIGIN = ssm.get_parameter(Name="/aws-monitor/ss-backend/domain", WithDecryption=True)['Parameter']['Value']
REFRESH_ID_ENDPOINT="/user/refreshId"

def get_param(name):
    return ssm.get_parameter(Name=name, WithDecryption=True)['Parameter']['Value']

def set_param(name, value):
    ssm.put_parameter(Name=name, Value=value, Overwrite=True)

def refresh_access_token():
    refresh_token = get_param(REFRESH_PARAM)
    url = f"https://{ORIGIN}{REFRESH_ID_ENDPOINT}"
    headers = { "Content-Type": "application/x-www-form-urlencoded" }
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token
    }
    response = requests.post(url, headers=headers, data=data)
    if response.status_code == 200:
        tokens = response.json()
        access_token = tokens.get("access_token")
        set_param(ACCESS_PARAM, access_token)
        return access_token
    else:
        raise Exception(f"Token refresh failed: {response.text}")

def get_valid_token():
    token = get_param(ACCESS_PARAM)
    return token

def postData(endpointUrl, payload):
    headers = { "Authorization": f"Bearer {get_valid_token()}", "Content-Type": "application/json" }
    fqdn=f"https://${ORIGIN}{endpointUrl}"
    resp = requests.post(fqdn, headers=headers, json=payload)
    if resp.status_code == 403:
        token = refresh_access_token()
        headers["Authorization"] = f"Bearer {token}"
        resp = requests.post(fqdn, headers=headers, json=payload)
    if not resp.ok:
        raise Exception(f"Update failed: {resp.status_code}, {resp.text}")
    return resp.json()

def getData(endpointUrl, params):
    headers = {
        "Authorization": f"Bearer {get_valid_token()}",
        "Content-Type": "application/json"
    }
    fqdn=f"https://${ORIGIN}{endpointUrl}"
    resp = requests.get(fqdn, headers=headers, params=params)
    if resp.status_code == 403:
        token = refresh_access_token()
        headers["Authorization"] = f"Bearer {token}"
        resp = requests.get(fqdn, headers=headers, params=params)
    if not resp.ok:
        raise Exception(f"GET request failed: {resp.status_code}, {resp.text}")
    return resp.json()
