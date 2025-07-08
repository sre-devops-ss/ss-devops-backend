# Target Group Monitoring

This project provides a Lambda-based solution for monitoring AWS Target Group metrics and setting up alarms with customizable thresholds for Application Load Balancer target group monitoring.

## Features

- Monitor Target Group response time
- Monitor request count
- Monitor unhealthy host count
- Monitor 5xx errors from targets
- Customizable thresholds for each metric
- Deployable via AWS SAM/CloudFormation

## File Structure

```
tg-api/
├── template.yaml              # CloudFormation template
├── domain.yaml                # Custom domain configuration
├── requirements.txt           # Python dependencies
├── README.md                  # This file
├── API-DOCUMENTATION.md       # API documentation
├── health_check.py            # Health check endpoint
├── tg_create_alarm.py         # Target Group alarm creation function
├── utils/
│   ├── cross_account.py       # Cross-account authentication
│   └── cloudwatch_client.py   # CloudWatch operations
```

## Usage

### Create Target Group Alarms

**POST** `/create-alarm`

Creates CloudWatch alarms for Target Group monitoring including:
- Response time monitoring
- Request count monitoring
- Unhealthy host count monitoring
- 5xx errors monitoring

## Prerequisites

- Required IAM permissions for CloudWatch and Application Load Balancer monitoring
- Target Group and Load Balancer must exist
- CloudWatch permissions

## Deployment

- Deploy using AWS SAM or CloudFormation.
- The Lambda function code should be placed in `../tg-api/` as referenced in `template.yaml`.
- The stack will create an SSM parameter `/ss/backend/tg-monitoring-api/id` for the API Gateway ID.

## Environment Variables

- `ROLE_NAME`: Cross-account role name (if used)
- `REGION`: AWS region

## License

MIT 