# API Gateway Monitoring API Documentation

## Overview

This API provides a Lambda-based solution for monitoring AWS API Gateway metrics (4xx, 5xx errors, and latency) and setting up alarms with customizable thresholds. The API includes individual alarm creation endpoints for each metric type.

## Base URL

```
https://{api-gateway-id}.execute-api.{region}.amazonaws.com/{environment}
```

## Endpoints

### 1. 4XX Error Alarm Creation

**POST** `/alarms/4xx`

Creates a CloudWatch alarm specifically for 4XX errors.

**Request Body:**
```json
{
  "api_name": "MyApiName",
  "stage": "prod",
  "account_id": "123456789012",
  "region": "us-east-1",
  "config": {
    "4xx_threshold": 10,
    "period": 60,
    "evaluation_periods": 1
  }
}
```

**Response Example:**
```json
"4XX error alarm created"
```

### 2. 5XX Error Alarm Creation

**POST** `/alarms/5xx`

Creates a CloudWatch alarm specifically for 5XX errors.

**Request Body:**
```json
{
  "api_name": "MyApiName",
  "stage": "prod",
  "account_id": "123456789012",
  "region": "us-east-1",
  "config": {
    "5xx_threshold": 1,
    "period": 60,
    "evaluation_periods": 1
  }
}
```

**Response Example:**
```json
"5XX error alarm created"
```

### 3. Latency Alarm Creation

**POST** `/alarms/latency`

Creates a CloudWatch alarm specifically for API Gateway latency.

**Request Body:**
```json
{
  "api_name": "MyApiName",
  "stage": "prod",
  "account_id": "123456789012",
  "region": "us-east-1",
  "config": {
    "latency_threshold": 1000,
    "period": 60,
    "evaluation_periods": 1
  }
}
```

**Response Example:**
```json
"Latency alarm created"
```

### 4. Health Check

**GET** `/health`

Returns the health status of the API.

**Response Example:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

## Request Parameters

### Common Parameters
- `api_name` (required): Name of the API Gateway
- `stage` (required): Stage name (e.g., prod, dev)
- `account_id` (required): AWS account ID
- `region` (optional): AWS region (defaults to Lambda region)
- `config` (optional): Configuration object with thresholds and settings

### Configuration Options
- `4xx_threshold` (default: 10): Threshold for 4XX error count
- `5xx_threshold` (default: 1): Threshold for 5XX error count
- `latency_threshold` (default: 1000): Threshold for latency in milliseconds
- `period` (default: 60): Evaluation period in seconds
- `evaluation_periods` (default: 1): Number of evaluation periods

## Sample Events

### 4XX Alarm Creation
```json
{
  "api_name": "MyApiName",
  "stage": "prod",
  "account_id": "123456789012",
  "config": {
    "4xx_threshold": 15
  }
}
```

### 5XX Alarm Creation
```json
{
  "api_name": "MyApiName",
  "stage": "prod",
  "account_id": "123456789012",
  "config": {
    "5xx_threshold": 2
  }
}
```

### Latency Alarm Creation
```json
{
  "api_name": "MyApiName",
  "stage": "prod",
  "account_id": "123456789012",
  "config": {
    "latency_threshold": 1500
  }
}
```

## Error Responses

- **400**: Missing required parameters
- **500**: Internal server error

**Error Example:**
```json
{
  "error": "Missing required parameter: api_name"
}
```

## Lambda Functions

The API creates the following Lambda functions:
1. `Devops-apigateway_4xx_alarm_create` - 4XX error alarm creation
2. `Devops-apigateway_5xx_alarm_create` - 5XX error alarm creation
3. `Devops-apigateway_latency_alarm_create` - Latency alarm creation
4. `Devops-apigateway_health_check` - Health check endpoint

## SSM Parameters
- The API Gateway ID is stored in `/ss/backend/apigateway-monitoring-api/id`
- SNS Topic ARN is retrieved from `/devops-backend/snstopic/arn`
- Cross-account role name is retrieved from `/ss/backend/cross-account-role-name`