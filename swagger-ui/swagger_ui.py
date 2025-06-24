import json

def lambda_handler(event, context):
    with open("index.html", "r") as f:
        html = f.read()

    with open("swagger.json", "r") as f:
        swagger_data = json.load(f)

    rendered_html = html.replace("__SWAGGER_JSON__", json.dumps(swagger_data))

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "text/html"
        },
        "body": rendered_html
    }
