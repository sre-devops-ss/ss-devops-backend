# ASG Monitoring API Documentation

## Overview

This API provides a Lambda-based solution for monitoring AWS Auto Scaling Group (ASG) metrics and setting up alarms with customizable thresholds for both instance-level and scaling-level monitoring.

## Base URL

```
https://{api-gateway-id}.execute-api.{region}.amazonaws.com/{environment}
```

## Endpoints

### 1. Create ASG Alarm

**POST** `/create-alarm`

Creates CloudWatch alarms for ASG instances and scaling activities.

**Request Body:**
```json
{
  "event_type": "instance",
  "instance_ids": ["i-1234567890abcdef0", "i-0987654321fedcba0"],
  "config": {
    "cpu_threshold": 80,
    "memory_threshold": 85,
    "period": 60,
    "evaluation_periods": 1,
    "alarm_actions": []
  }
}
```

**For Scaling Alarms:**
```json
{
  "event_type": "scaling",
  "asg_name": "my-asg-name",
  "config": {
    "scaling_threshold": 1,
    "period": 60,
    "evaluation_periods": 1,
    "alarm_actions": []
  }
}
```

**Parameters:**
- `event_type` (required): Either "instance" or "scaling"
- `instance_ids` (required for instance alarms): Array of EC2 instance IDs
- `asg_name` (required for scaling alarms): Name of the Auto Scaling Group
- `config` (optional): Object with thresholds and configuration

**Configuration Options:**
- `cpu_threshold` (default: 80): CPU utilization percentage threshold
- `memory_threshold` (default: 85): Memory utilization percentage threshold
- `scaling_threshold` (default: 1): Minimum number of in-service instances
- `period` (default: 60): Evaluation period in seconds
- `evaluation_periods` (default: 1): Number of periods to evaluate
- `alarm_actions` (default: []): Array of SNS topic ARNs for notifications

**Response Example:**
```json
{
  "message": "Alarms created"
}
```

## Sample Events

### Instance Alarms Event
```json
{
  "event_type": "instance",
  "instance_ids": ["i-1234567890abcdef0", "i-0987654321fedcba0"],
  "config": {
    "cpu_threshold": 80,
    "memory_threshold": 85,
    "period": 60,
    "evaluation_periods": 1,
    "alarm_actions": ["arn:aws:sns:us-east-1:123456789012:MyTopic"]
  }
}
```

### Scaling Alarms Event
```json
{
  "event_type": "scaling",
  "asg_name": "my-production-asg",
  "config": {
    "scaling_threshold": 2,
    "period": 60,
    "evaluation_periods": 1,
    "alarm_actions": ["arn:aws:sns:us-east-1:123456789012:MyTopic"]
  }
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

## SSM Parameter
- The API Gateway ID is stored in `/ss/backend/asg-monitoring-api/id`.

## Alarms Created

The API creates different types of CloudWatch alarms based on the event_type:

### Instance Alarms (event_type: "instance")
- **{instance_id}-cpu-utilization**: Monitors CPU utilization for each instance
- **{instance_id}-memory-utilization**: Monitors memory utilization for each instance (requires CloudWatch Agent)

### Scaling Alarms (event_type: "scaling")
- **{asg_name}-scaling-activity**: Monitors the number of in-service instances in the ASG

## Prerequisites

### For Memory Monitoring
To enable memory utilization monitoring, ensure that:
1. CloudWatch Agent is installed on the EC2 instances
2. The agent is configured to collect memory metrics
3. The agent is running and sending data to CloudWatch

### Required IAM Permissions
The Lambda function requires the following permissions:
- `cloudwatch:PutMetricAlarm`
- `autoscaling:DescribeAutoScalingGroups`
- `ec2:DescribeInstances`
- `sts:AssumeRole` (for cross-account access) 