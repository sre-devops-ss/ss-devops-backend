# ASG Monitoring API Documentation

## Overview

This API provides a modular Lambda-based solution for monitoring AWS Auto Scaling Group (ASG) metrics including CPU utilization, memory utilization, and scaling activities. Each metric type has its own dedicated endpoint for maximum flexibility.

## Base URL

```
https://{api-gateway-id}.execute-api.{region}.amazonaws.com/{environment}
```

## Endpoints

### 1. CPU Utilization Alarm Creation

**POST** `/alarms/cpu`

Creates CloudWatch alarms for CPU utilization on EC2 instances within an Auto Scaling Group.

**Request Body:**
```json
{
  "instance_ids": ["i-1234567890abcdef0", "i-0987654321fedcba0"],
  "cpu_threshold": 80,
  "period": 60,
  "evaluation_periods": 1,
  "alarm_actions": ["arn:aws:sns:region:account:topic-name"]
}
```

**Response Example:**
```json
{
  "message": "CPU alarms created"
}
```

### 2. Memory Utilization Alarm Creation

**POST** `/alarms/memory`

Creates CloudWatch alarms for memory utilization on EC2 instances within an Auto Scaling Group.

**Request Body:**
```json
{
  "instance_ids": ["i-1234567890abcdef0", "i-0987654321fedcba0"],
  "memory_threshold": 85,
  "period": 60,
  "evaluation_periods": 1,
  "alarm_actions": ["arn:aws:sns:region:account:topic-name"]
}
```

**Response Example:**
```json
{
  "message": "Memory alarms created"
}
```

### 3. Scaling Activity Alarm Creation

**POST** `/alarms/scaling`

Creates CloudWatch alarms for Auto Scaling Group scaling activities.

**Request Body:**
```json
{
  "asg_name": "my-asg-name",
  "scaling_threshold": 1,
  "period": 60,
  "evaluation_periods": 1,
  "alarm_actions": ["arn:aws:sns:region:account:topic-name"]
}
```

**Response Example:**
```json
{
  "message": "Scaling alarm created"
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

### CPU and Memory Alarm Parameters
- `instance_ids` (required): Array of EC2 instance IDs to monitor
- `cpu_threshold` (optional, default: 80): CPU utilization percentage threshold
- `memory_threshold` (optional, default: 85): Memory utilization percentage threshold
- `period` (optional, default: 60): Evaluation period in seconds
- `evaluation_periods` (optional, default: 1): Number of evaluation periods
- `alarm_actions` (optional): Array of SNS topic ARNs for notifications

### Scaling Alarm Parameters
- `asg_name` (required): Name of the Auto Scaling Group
- `scaling_threshold` (optional, default: 1): Minimum number of in-service instances
- `period` (optional, default: 60): Evaluation period in seconds
- `evaluation_periods` (optional, default: 1): Number of evaluation periods
- `alarm_actions` (optional): Array of SNS topic ARNs for notifications

## Sample Events

### CPU Alarm Creation
```json
{
  "instance_ids": ["i-1234567890abcdef0"],
  "cpu_threshold": 75,
  "period": 300,
  "evaluation_periods": 2
}
```

### Memory Alarm Creation
```json
{
  "instance_ids": ["i-1234567890abcdef0", "i-0987654321fedcba0"],
  "memory_threshold": 90,
  "period": 60,
  "evaluation_periods": 1
}
```

### Scaling Alarm Creation
```json
{
  "asg_name": "production-asg",
  "scaling_threshold": 2,
  "period": 300,
  "evaluation_periods": 2
}
```

## Error Responses

- **400**: Missing required parameters
- **500**: Internal server error

**Error Example:**
```json
{
  "error": "Missing required parameter: instance_ids"
}
```

## Lambda Functions

The API creates the following Lambda functions:
1. `Devops-asg_cpu_alarm_create` - CPU utilization alarm creation
2. `Devops-asg_memory_alarm_create` - Memory utilization alarm creation
3. `Devops-asg_scaling_alarm_create` - Scaling activity alarm creation
4. `Devops-asg_health_check` - Health check endpoint

## CloudWatch Metrics

### CPU Utilization
- **Namespace**: `AWS/EC2`
- **Metric**: `CPUUtilization`
- **Statistic**: Average
- **Unit**: Percent

### Memory Utilization
- **Namespace**: `CWAgent`
- **Metric**: `mem_used_percent`
- **Statistic**: Average
- **Unit**: Percent

### Scaling Activity
- **Namespace**: `AWS/AutoScaling`
- **Metric**: `GroupInServiceInstances`
- **Statistic**: Average
- **Unit**: Count

## SSM Parameters
- The API Gateway ID is stored in `/ss/backend/asg-monitoring-api/id`
- Cross-account role name is retrieved from `/ss/backend/cross-account-role-name` 