# Lambda Monitoring API Documentation

## Overview

This API provides a Lambda-based solution for monitoring AWS Lambda function metrics (errors, duration, and log errors) and setting up alarms with customizable thresholds.

## Base URL

```
https://{api-gateway-id}.execute-api.{region}.amazonaws.com/{environment}
```

## Endpoints

### 1. Create Errors Alarm

**POST** `/errors-alarm`

Creates a CloudWatch alarm for Lambda function errors.

**Request Body:**
```json
{
  "function_name": "MyLambdaFunction",
  "config": {
    "error_threshold": 1,
    "period": 60,
    "evaluation_periods": 1,
    "alarm_actions": []
  }
}
```

- `function_name` (required): Name of the Lambda function
- `config` (optional): Object with thresholds and configuration

**Configuration Options:**
- `error_threshold` (default: 1): Number of errors before alarm triggers
- `period` (default: 60): Evaluation period in seconds
- `evaluation_periods` (default: 1): Number of periods to evaluate
- `alarm_actions` (default: []): Array of SNS topic ARNs for notifications

**Response Example:**
```json
{
  "message": "Errors alarm created"
}
```

### 2. Create Duration Alarm

**POST** `/duration-alarm`

Creates a CloudWatch alarm for Lambda function duration.

**Request Body:**
```json
{
  "function_name": "MyLambdaFunction",
  "config": {
    "duration_threshold": 3000,
    "period": 60,
    "evaluation_periods": 1,
    "alarm_actions": []
  }
}
```

- `function_name` (required): Name of the Lambda function
- `config` (optional): Object with thresholds and configuration

**Configuration Options:**
- `duration_threshold` (default: 3000): Maximum duration in milliseconds
- `period` (default: 60): Evaluation period in seconds
- `evaluation_periods` (default: 1): Number of periods to evaluate
- `alarm_actions` (default: []): Array of SNS topic ARNs for notifications

**Response Example:**
```json
{
  "message": "Duration alarm created"
}
```

### 3. Create Log Error Alarm

**POST** `/log-error-alarm`

Creates a CloudWatch alarm for Lambda log errors.

**Request Body:**
```json
{
  "function_name": "MyLambdaFunction",
  "config": {
    "log_error_threshold": 1,
    "period": 60,
    "evaluation_periods": 1,
    "alarm_actions": []
  }
}
```

- `function_name` (required): Name of the Lambda function
- `config` (optional): Object with thresholds and configuration

**Configuration Options:**
- `log_error_threshold` (default: 1): Number of log errors before alarm triggers
- `period` (default: 60): Evaluation period in seconds
- `evaluation_periods` (default: 1): Number of periods to evaluate
- `alarm_actions` (default: []): Array of SNS topic ARNs for notifications

**Response Example:**
```json
{
  "message": "Log error alarm created"
}
```

## Sample Events

### Errors Alarm Event
```json
{
  "function_name": "MyLambdaFunction",
  "config": {
    "error_threshold": 1,
    "period": 60,
    "evaluation_periods": 1,
    "alarm_actions": ["arn:aws:sns:us-east-1:123456789012:MyTopic"]
  }
}
```

### Duration Alarm Event
```json
{
  "function_name": "MyLambdaFunction",
  "config": {
    "duration_threshold": 3000,
    "period": 60,
    "evaluation_periods": 1,
    "alarm_actions": ["arn:aws:sns:us-east-1:123456789012:MyTopic"]
  }
}
```

### Log Error Alarm Event
```json
{
  "function_name": "MyLambdaFunction",
  "config": {
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

Each endpoint creates specific CloudWatch alarms:

### Errors Alarm Endpoint
- **{function_name}-errors-alarm**: Monitors Lambda invocation errors

### Duration Alarm Endpoint
- **{function_name}-duration-alarm**: Monitors Lambda execution duration

### Log Error Alarm Endpoint
- **{function_name}-log-error-alarm**: Monitors errors in Lambda logs
- **Metric Filter**: Creates a CloudWatch metric filter to monitor log errors
  - **Log Group**: `/aws/lambda/{function_name}`
  - **Filter Pattern**: `?"ERROR"`
  - **Metric Namespace**: `LambdaLogs`
  - **Metric Name**: `{function_name}-log-errors` 