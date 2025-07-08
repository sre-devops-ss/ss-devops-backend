# Billing API Documentation

## Overview

This API provides a Lambda-based solution for monitoring AWS Billing metrics and setting up alarms with customizable thresholds for billing and cost usage monitoring.

## Base URL

```
https://{api-gateway-id}.execute-api.{region}.amazonaws.com/{environment}
```

## Endpoints

### 1. Create Budget Alarm

**POST** `/budget-create-alarm`

Creates CloudWatch alarms for budget monitoring.

**Request Body:**
```json
{
  "budget_name": "monthly-budget",
  "config": {
    "budget_threshold": 1000,
    "period": 86400,
    "evaluation_periods": 1,
    "alarm_actions": []
  }
}
```

**Parameters:**
- `budget_name` (required): Name of the budget to monitor
- `config` (optional): Object with thresholds and configuration

**Configuration Options:**
- `budget_threshold` (default: 1000): Budget threshold in USD
- `period` (default: 86400): Evaluation period in seconds (daily)
- `evaluation_periods` (default: 1): Number of periods to evaluate
- `alarm_actions` (default: []): Array of SNS topic ARNs for notifications

**Response Example:**
```json
{
  "message": "Budget alarm created"
}
```

### 2. Create Cost Anomaly Alarm

**POST** `/cost-anomaly-create-alarm`

Creates CloudWatch alarms for cost anomaly detection.

**Request Body:**
```json
{
  "anomaly_threshold": 50,
  "config": {
    "period": 86400,
    "evaluation_periods": 1,
    "alarm_actions": []
  }
}
```

**Parameters:**
- `anomaly_threshold` (required): Percentage threshold for anomaly detection
- `config` (optional): Object with thresholds and configuration

**Configuration Options:**
- `period` (default: 86400): Evaluation period in seconds (daily)
- `evaluation_periods` (default: 1): Number of periods to evaluate
- `alarm_actions` (default: []): Array of SNS topic ARNs for notifications

**Response Example:**
```json
{
  "message": "Cost anomaly alarm created"
}
```

### 3. Create Data Transfer Alarm

**POST** `/data-transfer-create-alarm`

Creates CloudWatch alarms for data transfer monitoring.

**Request Body:**
```json
{
  "transfer_threshold": 100,
  "config": {
    "period": 3600,
    "evaluation_periods": 1,
    "alarm_actions": []
  }
}
```

**Parameters:**
- `transfer_threshold` (required): Data transfer threshold in GB
- `config` (optional): Object with thresholds and configuration

**Configuration Options:**
- `period` (default: 3600): Evaluation period in seconds (hourly)
- `evaluation_periods` (default: 1): Number of periods to evaluate
- `alarm_actions` (default: []): Array of SNS topic ARNs for notifications

**Response Example:**
```json
{
  "message": "Data transfer alarm created"
}
```

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

- Required IAM permissions for billing and cost monitoring
- AWS Cost Explorer access
- CloudWatch permissions

## SSM Parameter
- The API Gateway ID is stored in `/ss/backend/billing-monitoring-api/id`. 