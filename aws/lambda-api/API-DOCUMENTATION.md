# Lambda Monitoring API Documentation

## Overview

This API provides a Lambda-based solution for monitoring AWS Lambda function metrics (errors, duration, and log errors) and setting up alarms with customizable thresholds.

## Base URL

```
https://{api-gateway-id}.execute-api.{region}.amazonaws.com/{environment}
```

## Endpoint

### Install Monitoring

**POST** `/install`

Sets up monitoring for a Lambda function by creating CloudWatch alarms for errors, duration, and log errors.

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

- `function_name` (required): Name of the Lambda function
- `region` (optional): AWS region (default: us-east-1)
- `config` (optional): Object with thresholds and configuration

**Configuration Options:**
- `error_threshold` (default: 1): Number of errors before alarm triggers
- `duration_threshold` (default: 3000): Maximum duration in milliseconds
- `log_error_threshold` (default: 1): Number of log errors before alarm triggers
- `period` (default: 60): Evaluation period in seconds
- `evaluation_periods` (default: 1): Number of periods to evaluate
- `alarm_actions` (default: []): Array of SNS topic ARNs for notifications

**Response Example:**
```json
{
  "message": "Alarms created"
}
```

## Sample Event

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
    "alarm_actions": ["arn:aws:sns:us-east-1:123456789012:MyTopic"]
  }
}
```

## Error Responses

- **400**: Missing required parameters
- **500**: Internal server error

**Error Example:**
```json
{
  "error": "Missing required parameter: function_name"
}
```

## SSM Parameter
- The API Gateway ID is stored in `/ss/backend/lambda-monitoring-api/id`.

## Alarms Created

The API creates the following CloudWatch alarms:

1. **{function_name}-errors-alarm**: Monitors Lambda invocation errors
2. **{function_name}-duration-alarm**: Monitors Lambda execution duration
3. **{function_name}-log-error-alarm**: Monitors errors in Lambda logs

## Metric Filter

A CloudWatch metric filter is also created to monitor log errors:
- **Log Group**: `/aws/lambda/{function_name}`
- **Filter Pattern**: `?"ERROR"`
- **Metric Namespace**: `LambdaLogs`
- **Metric Name**: `{function_name}-log-errors` 