# Target Group API Documentation

## Overview

This API provides a Lambda-based solution for monitoring AWS Target Group metrics and setting up alarms with customizable thresholds for Application Load Balancer target group monitoring.

## Base URL

```
https://{api-gateway-id}.execute-api.{region}.amazonaws.com/{environment}
```

## Endpoints

### 1. Create Target Group Alarm

**POST** `/create-alarm`

Creates CloudWatch alarms for Target Group monitoring.

**Request Body:**
```json
{
  "load_balancer_name": "app/my-alb/50dc6c495c0c9188",
  "target_group_name": "targetgroup/my-tg/73e2d6bc24d8a067",
  "config": {
    "response_time_threshold": 1.0,
    "request_count_threshold": 1000,
    "unhealthy_threshold": 1,
    "target_5xx_threshold": 10,
    "period": 60,
    "evaluation_periods": 1,
    "alarm_actions": []
  }
}
```

**Parameters:**
- `load_balancer_name` (required): Load Balancer name in CloudWatch format (e.g., app/my-alb/50dc6c495c0c9188)
- `target_group_name` (required): Target Group name in CloudWatch format (e.g., targetgroup/my-tg/73e2d6bc24d8a067)
- `config` (optional): Object with thresholds and configuration

**Configuration Options:**
- `response_time_threshold` (default: 1.0): Response time threshold in seconds
- `request_count_threshold` (default: 1000): Request count threshold
- `unhealthy_threshold` (default: 1): Unhealthy host count threshold
- `target_5xx_threshold` (default: 10): 5xx errors threshold
- `period` (default: 60): Evaluation period in seconds
- `evaluation_periods` (default: 1): Number of periods to evaluate
- `alarm_actions` (default: []): Array of SNS topic ARNs for notifications

**Response Example:**
```json
{
  "message": "Target Group alarms created"
}
```

## Alarms Created

The API creates the following CloudWatch alarms:

1. **{target_group_name}-response-time**: Monitors target response time
2. **{target_group_name}-request-count**: Monitors request count
3. **{target_group_name}-unhealthy-hosts**: Monitors unhealthy host count
4. **{target_group_name}-5xx-errors**: Monitors 5xx errors from targets

## Error Responses

- **400**: Invalid parameters or missing required fields
- **500**: Internal server error

**Error Example:**
```json
{
  "error": "Invalid parameters"
}
```

## Prerequisites

- Required IAM permissions for CloudWatch and Application Load Balancer monitoring
- Target Group and Load Balancer must exist
- CloudWatch permissions

## SSM Parameter
- The API Gateway ID is stored in `/ss/backend/tg-monitoring-api/id`. 