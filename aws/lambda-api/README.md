# Lambda Monitoring

This project provides a Lambda-based solution for monitoring AWS Lambda function metrics (errors, duration, and log errors) and setting up alarms with customizable thresholds.

## Features

- Monitor Lambda function errors, duration, and log errors
- Customizable thresholds for each metric
- CloudWatch metric filters for log monitoring
- Deployable via AWS SAM/CloudFormation

## File Structure

```
lambda-api/
├── template.yaml              # CloudFormation template
├── domain.yaml                # Custom domain configuration
├── requirements.txt           # Python dependencies
├── README.md                  # This file
├── API-DOCUMENTATION.md       # API documentation
├── health_check.py            # Health check endpoint
├── lambda_monitoring_create.py # Main monitoring function
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
  "function_name": "MyLambdaFunction",
  "region": "us-east-1",
  "config": {
    "error_threshold": 1,
    "duration_threshold": 3000,
    "log_error_threshold": 1,
    "period": 60,
    "evaluation_periods": 1,
    "alarm_actions": []
  }
}
```

**Response Example:**
```json
{
  "message": "Alarms created"
}
```

## Alarms Created

The API creates three CloudWatch alarms:

1. **{function_name}-errors-alarm**: Monitors Lambda invocation errors
2. **{function_name}-duration-alarm**: Monitors Lambda execution duration  
3. **{function_name}-log-error-alarm**: Monitors errors in Lambda logs

## Metric Filter

A CloudWatch metric filter is created to monitor log errors:
- **Log Group**: `/aws/lambda/{function_name}`
- **Filter Pattern**: `?"ERROR"`
- **Metric Namespace**: `LambdaLogs`
- **Metric Name**: `{function_name}-log-errors`

## Deployment

- Deploy using AWS SAM or CloudFormation.
- The Lambda function code should be placed in `../lambda-api/` as referenced in `template.yaml`.
- The stack will create an SSM parameter `/ss/backend/lambda-monitoring-api/id` for the API Gateway ID.

## Environment Variables

- `ROLE_NAME`: Cross-account role name (if used)
- `REGION`: AWS region

## License

MIT 