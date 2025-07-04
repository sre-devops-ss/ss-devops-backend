# API Gateway Monitoring

This project provides a Lambda-based solution for monitoring AWS API Gateway metrics (4xx, 5xx errors, and latency) and setting up alarms with customizable thresholds.

## Features

- Monitor API Gateway 4xx, 5xx error rates, and latency
- Customizable thresholds for each metric
- Deployable via AWS SAM/CloudFormation

## File Structure

```
api-gateway/
├── template.yaml              # CloudFormation template
├── domain.yaml                # Custom domain configuration
├── requirements.txt           # Python dependencies
├── README.md                  # This file
├── API-DOCUMENTATION.md       # API documentation
├── health_check.py            # Health check endpoint
├── utils/
│   ├── cross_account.py       # Cross-account authentication
│   └── cloudwatch_client.py   # CloudWatch operations
```

## Usage

### Install Monitoring

**POST** `/install`

**Request Body:**
```json
{
  "api_name": "MyApiName",
  "stage": "prod",
  "account_id": "123456789012",
  "region": "us-east-1",
  "config": {
    "4xx_threshold": 20,
    "5xx_threshold": 5,
    "latency_threshold": 2000
  }
}
```

**Response Example:**
```json
{
  "message": "Successfully set up monitoring for API Gateway MyApiName (stage: prod)",
  "alarms": [
    "MyApiName-prod-4XXAlarm",
    "MyApiName-prod-5XXAlarm",
    "MyApiName-prod-LatencyAlarm"
  ]
}
```

## Deployment

- Deploy using AWS SAM or CloudFormation.
- The Lambda function code should be placed in `../apigateway-api/` as referenced in `template.yaml`.
- The stack will create an SSM parameter `/devops-backend/apigatewayapi/id` for the API Gateway ID.

## Environment Variables

- `ROLE_NAME`: Cross-account role name (if used)
- `REGION`: AWS region

## License

MIT 