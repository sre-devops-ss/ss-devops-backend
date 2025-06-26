import json
import yaml

def lambda_handler(event, context):
    with open("index.html", "r") as f:
        html = f.read()

    with open("openapi.yaml", "r") as f:
        openapi_data = yaml.safe_load(f)

    # Inject the OpenAPI spec as a JS variable at the top of <body>
    injection = f'<script>window.OPENAPI_SPEC = {json.dumps(openapi_data)};</script>'
    html = html.replace('<body>', f'<body>\n{injection}', 1)

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "text/html"
        },
        "body": html
    }
