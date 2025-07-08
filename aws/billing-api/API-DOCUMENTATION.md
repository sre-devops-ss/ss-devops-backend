# Billing API Documentation

## Overview

This API provides a Lambda-based solution for monitoring AWS Billing metrics and setting up alarms with customizable thresholds for billing and cost usage monitoring.

## Base URL

```
https://{api-gateway-id}.execute-api.{region}.amazonaws.com/{environment}
```

## Endpoints

### 1. Create Billing Alarm

**POST** `/create-alarm`

Creates CloudWatch alarms for billing and cost usage.

**Request Body:**
```json
{
  "event_type": "billing",
  "config": {
    "cost_threshold": 1000,
    "period": 86400,
    "evaluation_periods": 1,
    "alarm_actions": []
  }
}
```

**Parameters:**
- `event_type` (required): "billing"
- `config` (optional): Object with thresholds and configuration

**Configuration Options:**
- `cost_threshold` (default: 1000): Cost threshold in USD
- `period` (default: 86400): Evaluation period in seconds (daily)
- `evaluation_periods` (default: 1): Number of periods to evaluate
- `alarm_actions` (default: []): Array of SNS topic ARNs for notifications

**Response Example:**
```json
{
  "message": "Alarms created"
}
```

## Error Responses

- **400**: Invalid event_type or missing required parameters
- **500**: Internal server error

**Error Example:**
```json
{
  "error": "Invalid event_type"
}
```

## Prerequisites

- Required IAM permissions for billing and cost monitoring 