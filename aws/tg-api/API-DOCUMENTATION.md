# Target Group Monitoring API Documentation

## Overview

This API provides a modular Lambda-based solution for monitoring AWS Application Load Balancer (ALB) Target Group metrics including response time, request count, and unhealthy host count. Each metric type has its own dedicated endpoint for maximum flexibility.

## Base URL

```
https://{api-gateway-id}.execute-api.{region}.amazonaws.com/{environment}
```

## Endpoints

### 1. Response Time Alarm Creation

**POST** `/tg/response-time`

Creates CloudWatch alarms for target response time in Application Load Balancer target groups.

**Request Body:**
```json
{
  "load_balancer_name": "my-alb",
  "target_group_name": "my-target-group",
  "config": {
    "threshold": 5.0,
    "period": 60,
    "evaluation_periods": 1,
    "alarm_actions": ["arn:aws:sns:region:account:topic-name"]
  }
}
```

**Response Example:**
```json
{
  "message": "Response time alarm created"
}
```

### 2. Request Count Alarm Creation

**POST** `/tg/request-count`

Creates CloudWatch alarms for request count in Application Load Balancer target groups.

**Request Body:**
```json
{
  "load_balancer_name": "my-alb",
  "target_group_name": "my-target-group",
  "config": {
    "threshold": 1000,
    "period": 60,
    "evaluation_periods": 1,
    "alarm_actions": ["arn:aws:sns:region:account:topic-name"]
  }
}
```

**Response Example:**
```json
{
  "message": "Request count alarm created"
}
```

### 3. Unhealthy Host Alarm Creation

**POST** `/tg/unhealthy-hosts`

Creates CloudWatch alarms for unhealthy host count in Application Load Balancer target groups.

**Request Body:**
```json
{
  "load_balancer_name": "my-alb",
  "target_group_name": "my-target-group",
  "config": {
    "threshold": 1,
    "period": 60,
    "evaluation_periods": 1,
    "alarm_actions": ["arn:aws:sns:region:account:topic-name"]
  }
}
```

**Response Example:**
```json
{
  "message": "Unhealthy host alarm created"
}
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
- `load_balancer_name` (required): Name of the Application Load Balancer
- `target_group_name` (required): Name of the Target Group
- `config` (required): Configuration object with thresholds and settings

### Configuration Options
- `threshold` (required): Threshold value for the alarm
- `period` (optional, default: 60): Evaluation period in seconds
- `evaluation_periods` (optional, default: 1): Number of evaluation periods
- `alarm_actions` (optional): Array of SNS topic ARNs for notifications

## Sample Events

### Response Time Alarm Creation
```json
{
  "load_balancer_name": "prod-alb",
  "target_group_name": "web-servers",
  "config": {
    "threshold": 3.0,
    "period": 300,
    "evaluation_periods": 2
  }
}
```

### Request Count Alarm Creation
```json
{
  "load_balancer_name": "prod-alb",
  "target_group_name": "web-servers",
  "config": {
    "threshold": 500,
    "period": 60,
    "evaluation_periods": 1
  }
}
```

### Unhealthy Host Alarm Creation
```json
{
  "load_balancer_name": "prod-alb",
  "target_group_name": "web-servers",
  "config": {
    "threshold": 2,
    "period": 300,
    "evaluation_periods": 2
  }
}
```

## Error Responses

- **400**: Missing required parameters
- **500**: Internal server error

**Error Example:**
```json
{
  "error": "Missing required parameter: load_balancer_name"
}
```

## Lambda Functions

The API creates the following Lambda functions:
1. `Devops-tg_response_time_alarm_create` - Response time alarm creation
2. `Devops-tg_request_count_alarm_create` - Request count alarm creation
3. `Devops-tg_unhealthy_host_alarm_create` - Unhealthy host alarm creation
4. `Devops-tg_health_check` - Health check endpoint

## CloudWatch Metrics

### Response Time
- **Namespace**: `AWS/ApplicationELB`
- **Metric**: `TargetResponseTime`
- **Statistic**: Average
- **Unit**: Seconds

### Request Count
- **Namespace**: `AWS/ApplicationELB`
- **Metric**: `RequestCount`
- **Statistic**: Sum
- **Unit**: Count

### Unhealthy Host Count
- **Namespace**: `AWS/ApplicationELB`
- **Metric**: `UnHealthyHostCount`
- **Statistic**: Average
- **Unit**: Count

## SSM Parameters
- The API Gateway ID is stored in `/ss/backend/tg-monitoring-api/id`
- Cross-account role name is retrieved from `/ss/backend/cross-account-role-name` 