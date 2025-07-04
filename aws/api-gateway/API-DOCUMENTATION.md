# API Gateway Monitoring API Documentation

## Overview

This API provides a Lambda-based solution for monitoring AWS API Gateway metrics (4xx, 5xx errors, and latency) and setting up alarms with customizable thresholds.

## Base URL

```
https://{api-gateway-id}.execute-api.{region}.amazonaws.com/{environment}
```

## Endpoint

### Install Monitoring

**POST** `/install`

Sets up monitoring for an API Gateway stage by creating CloudWatch alarms for 4xx, 5xx, and latency metrics.

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

- `api_name` (required): Name of the API Gateway
- `stage` (required): Stage name (e.g., prod, dev)
- `account_id` (required): AWS account ID
- `region` (required): AWS region
- `config` (required): Object with thresholds for 4xx, 5xx, and latency

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

## Sample Event

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

## Error Responses

- **400**: Missing required parameters
- **500**: Internal server error

**Error Example:**
```json
{
  "error": "Missing required parameter: api_name"
}
```

## SSM Parameter
- The API Gateway ID is stored in `/devops-backend/apigatewayapi/id`.



sample event