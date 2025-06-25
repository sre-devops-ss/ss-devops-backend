import json
import yaml

def lambda_handler(event, context):
    with open("index.html", "r") as f:
        html = f.read()

    with open("openapi.yaml", "r") as f:
        openapi_data = yaml.safe_load(f)

    rendered_html = html.replace("__SWAGGER_JSON__", json.dumps(openapi_data))

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "text/html"
        },
        "body": rendered_html
    }
