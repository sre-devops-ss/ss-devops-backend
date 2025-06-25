def lambda_handler(event, context):
    with open("index.html", "r") as f:
        html = f.read()

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "text/html"
        },
        "body": html
    }
