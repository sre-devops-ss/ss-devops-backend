import boto3
import requests

ssm = boto3.client('ssm')

REFRESH_PARAM = "/ss/backend/refresh_token"
ORIGIN = ssm.get_parameter(Name="/ss/backend/domain")['Parameter']['Value']
REFRESH_ID_ENDPOINT = "/api/user/accessId"

def get_param(name):
    return ssm.get_parameter(Name=name)['Parameter']['Value']

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
        return tokens.get("access_token")
    else:
        raise Exception(f"Token refresh failed: {response.status_code}, {response.text}")

def postData(endpointUrl, payload):
    token = refresh_access_token()
    headers = { "Authorization": f"Bearer {token}", "Content-Type": "application/json" }
    fqdn = f"https://{ORIGIN}{endpointUrl}"
    resp = requests.post(fqdn, headers=headers, json=payload)
    if not resp.ok:
        raise Exception(f"POST failed: {resp.status_code}, {resp.text}")
    return resp.json()

def getData(endpointUrl, params):
    token = refresh_access_token()
    headers = { "Authorization": f"Bearer {token}", "Content-Type": "application/json" }
    fqdn = f"https://{ORIGIN}{endpointUrl}"
    resp = requests.get(fqdn, headers=headers, params=params)
    if not resp.ok:
        raise Exception(f"GET failed: {resp.status_code}, {resp.text}")
    return resp.json()
