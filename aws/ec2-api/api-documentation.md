# EC2 Monitoring API Documentation

This document provides comprehensive documentation for the EC2 Monitoring API, which enables monitoring of EC2 instances across multiple AWS accounts using cross-account authentication.

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [API Endpoints](#api-endpoints)
4. [Request/Response Formats](#requestresponse-formats)
5. [Error Handling](#error-handling)
6. [Examples](#examples)
7. [Deployment](#deployment)

## Overview



The EC2 Monitoring API provides the following capabilities:

- **Cross-Account Monitoring**: Monitor EC2 instances in different AWS accounts
- **CloudWatch Integration**: Create and manage CloudWatch alarms for CPU, memory, and disk utilization
- **Metrics Collection**: Fetch comprehensive metrics data with time ranges
- **Alarm Management**: Retrieve alarm states and history
- **Database Storage**: Store metrics and alarm history in Cassandra database

## Authentication

### Cross-Account Setup

To use cross-account functionality, you need:

1. **IAM Role in Target Account**:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cloudwatch:*",
        "ec2:DescribeInstances",
        "ssm:*",
        "sns:Publish"
      ],
      "Resource": "*"
    }
  ]
}
```

2. **Trust Relationship**:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::MONITORING_ACCOUNT_ID:root"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

## API Endpoints

### 1. Create EC2 Monitoring

**Endpoint**: `POST /ec2/install`

**Description**: Sets up monitoring for EC2 instances by creating CloudWatch alarms and optionally installing CloudWatch agent.

**Request Body**:
```json
{
  "account_id": "123456789012",
  "region": "us-east-1",
  "instance_ids": ["i-1234567890abcdef0", "i-0987654321fedcba0"],
  "config": {
    "cpu_threshold": 80,
    "memory_threshold": 85,
    "disk_threshold": 85,
    "evaluation_periods": 2,
    "period": 300,
    "alarm_actions": ["arn:aws:sns:us-east-1:123456789012:alerts-topic"]
  }
}
```

**Response**:
```json
{
  "statusCode": 200,
  "body": {
    "message": "EC2 monitoring enabled successfully",
    "instances": ["i-1234567890abcdef0", "i-0987654321fedcba0"]
  }
}
```

### 2. Fetch EC2 Metrics

**Endpoint**: `GET/POST /ec2/getMetrics`

**Description**: Fetches CloudWatch metrics for EC2 instances with specific time ranges and periods.

**Request Parameters**:
- `instance_id` (required): EC2 instance ID
- `account_id` (optional): Target account ID for cross-account operations
- `role_name` (optional): IAM role name for cross-account operations
- `region` (optional): AWS region (default: us-east-1)
- `start_time` (optional): Start time in ISO format
- `end_time` (optional): End time in ISO format
- `period` (optional): Data point period in seconds (default: 300)
- `metrics` (optional): Array of specific metrics to fetch
- namespace (optional): Namespace for specific metrics to fetch default is `AWS/EC2` and can be changed to `CWAgent` for custom metrics
- `unit` (optional): Unit for specific metrics to fetch
- `description` (optional): Description for specific metrics to fetch
- `data_points` (optional): Array of specific data points to fetch

**Sample POST Payloads**:

#### Basic Metrics Fetch (Client Account)
```json
{
  "instance_id": "i-1234567890abcdef0",
  "start_time": "2024-01-15T00:00:00",
  "end_time": "2024-01-15T23:59:59",
  "period": 300
}
```

#### Cross-Account Metrics Fetch
```json
{
  "account_id": "123456789012",
  "role_name": "EC2CrossAccountMetricsRole",
  "instance_id": "i-1234567890abcdef0",
  "region": "us-east-1",
  "start_time": "2024-01-15T00:00:00",
  "end_time": "2024-01-15T23:59:59",
  "period": 300
}
```

#### Specific Metrics Only
```json
{
  "instance_id": "i-1234567890abcdef0",
  "start_time": "2024-01-15T00:00:00",
  "end_time": "2024-01-15T23:59:59",
  "metrics": ["CPUUtilization", "mem_used_percent", "disk_used_percent"],
  "period": 300
}
```

#### Recent Metrics (Last Hour)
```json
{
  "instance_id": "i-1234567890abcdef0",
  "period": 60
}
```

**Response**:
```json
{
  "instance_id": "i-1234567890abcdef0",
  "account_id": "123456789012",
  "region": "us-east-1",
  "start_time": "2024-01-15T00:00:00",
  "end_time": "2024-01-15T23:59:59",
  "period": 300,
  "metrics_count": 3,
  "metrics": {
    "CPUUtilization": {
      "namespace": "AWS/EC2",
      "unit": "Percent",
      "description": "CPU utilization percentage",
      "data_points": [
        {
          "timestamp": "2024-01-15T00:05:00",
          "average": 45.2,
          "minimum": 42.1,
          "maximum": 48.3
        }
      ]
    }
  }
}
```

### 3. Fetch EC2 Alarms

**Endpoint**: `GET/POST /ec2/getAlarms`

**Description**: Fetches CloudWatch alarms for EC2 instances with optional alarm history.

**Request Parameters**:
- `instance_id` (required): EC2 instance ID
- `account_id` (optional): Target account ID for cross-account operations
- `role_name` (optional): IAM role name for cross-account operations
- `region` (optional): AWS region (default: us-east-1)
- `start_time` (optional): Start time for alarm history
- `end_time` (optional): End time for alarm history
- `include_history` (optional): Include alarm history (default: false)
- `alarm_names` (optional): Array of specific alarm names to fetch

**Sample POST Payloads**:

#### Basic Alarms Fetch
```json
{
  "instance_id": "i-1234567890abcdef0"
}
```

#### Cross-Account Alarms Fetch
```json
{
  "account_id": "123456789012",
  "role_name": "EC2CrossAccountMetricsRole",
  "instance_id": "i-1234567890abcdef0",
  "region": "us-east-1"
}
```

#### Alarms with History
```json
{
  "instance_id": "i-1234567890abcdef0",
  "include_history": true,
  "start_time": "2024-01-15T00:00:00",
  "end_time": "2024-01-15T23:59:59"
}
```

#### Specific Alarms
```json
{
  "instance_id": "i-1234567890abcdef0",
  "alarm_names": ["my-instance-cpu-utilization", "my-instance-memory-utilization"]
}
```

**Response**:
```json
{
  "instance_id": "i-1234567890abcdef0",
  "account_id": "123456789012",
  "region": "us-east-1",
  "alarms_count": 2,
  "alarms": [
    {
      "alarm_name": "my-instance-cpu-utilization",
      "alarm_arn": "arn:aws:cloudwatch:us-east-1:123456789012:alarm:my-instance-cpu-utilization",
      "alarm_description": "CPU utilization alarm for my-instance",
      "metric_name": "CPUUtilization",
      "namespace": "AWS/EC2",
      "dimensions": [
        {
          "Name": "InstanceId",
          "Value": "i-1234567890abcdef0"
        }
      ],
      "threshold": 80.0,
      "comparison_operator": "GreaterThanThreshold",
      "evaluation_periods": 2,
      "period": 300,
      "statistic": "Average",
      "state_value": "OK",
      "state_reason": "Threshold Crossed: 1 datapoint (45.2) was not greater than the threshold (80.0).",
      "state_updated_timestamp": "2024-01-15T12:00:00",
      "actions_enabled": true,
      "alarm_actions": [],
      "ok_actions": [],
      "insufficient_data_actions": [],
      "instance_details": {
        "instance_id": "i-1234567890abcdef0",
        "instance_type": "t3.micro",
        "state": "running",
        "launch_time": "2024-01-01T00:00:00",
        "tags": {
          "Name": "my-instance",
          "Environment": "production"
        }
      },
      "history": [
        {
          "timestamp": "2024-01-15T10:30:00",
          "history_item_type": "StateUpdate",
          "history_summary": "Alarm OK from ALARM",
          "history_data": "{\"version\":\"1.0\",\"queryDate\":\"2024-01-15T10:30:00Z\"}"
        }
      ]
    }
  ]
}
```

### 4. Update Metrics to Database

**Endpoint**: `POST /ec2/updateMetricsToDb`

**Description**: Fetches CloudWatch metrics and stores them in Cassandra database.

**Request Body**:
```json
{
  "account_id": "123456789012",
  "instance_id": "i-1234567890abcdef0",
  "region": "us-east-1",
  "start_time": "2024-01-01T00:00:00",
  "end_time": "2024-01-01T23:59:59"
}
```

**Response**:
```json
{
  "statusCode": 200,
  "body": {
    "message": "Metrics stored successfully",
    "records": 144
  }
}
```

### 5. Update Alarms to Database

**Endpoint**: `POST /ec2/updateAlarmToDb`

**Description**: Fetches CloudWatch alarm history and stores it in Cassandra database.

**Request Body**:
```json
{
  "account_id": "123456789012",
  "instance_id": "i-1234567890abcdef0",
  "region": "us-east-1",
  "start_time": "2024-01-01T00:00:00",
  "end_time": "2024-01-01T23:59:59"
}
```

**Response**:
```json
{
  "statusCode": 200,
  "body": {
    "message": "Alarms stored successfully",
    "records": 5
  }
}
```

## Available Metrics

The API supports the following CloudWatch metrics:

| Metric Name | Namespace | Unit | Description |
|-------------|-----------|------|-------------|
| CPUUtilization | AWS/EC2 | Percent | CPU utilization percentage |
| mem_used_percent | CWAgent | Percent | Memory utilization percentage |
| disk_used_percent | CWAgent | Percent | Disk utilization percentage |
| NetworkIn | AWS/EC2 | Bytes | Network bytes received |
| NetworkOut | AWS/EC2 | Bytes | Network bytes sent |
| DiskReadBytes | AWS/EC2 | Bytes | Disk read bytes |
| DiskWriteBytes | AWS/EC2 | Bytes | Disk write bytes |
| load1 | CWAgent | None | 1-minute load average |
| load5 | CWAgent | None | 5-minute load average |
| load15 | CWAgent | None | 15-minute load average |

## Error Handling

### Common Error Responses

#### 400 Bad Request
```json
{
  "error": "Missing required parameter: instance_id"
}
```

#### 500 Internal Server Error
```json
{
  "error": "Failed to get CloudWatch client: AccessDenied"
}
```

### Error Codes

- `400`: Bad Request - Missing or invalid parameters
- `401`: Unauthorized - Authentication failed
- `403`: Forbidden - Insufficient permissions
- `404`: Not Found - Resource not found
- `500`: Internal Server Error - Server-side error

## Examples

### cURL Examples

#### Fetch Metrics (GET)
```bash
curl -X GET "https://your-api-gateway-url.execute-api.region.amazonaws.com/dev/ec2/getMetrics?instance_id=i-1234567890abcdef0&start_time=2024-01-15T00:00:00&end_time=2024-01-15T23:59:59"
```

#### Fetch Metrics (POST)
```bash
curl -X POST "https://your-api-gateway-url.execute-api.region.amazonaws.com/dev/ec2/getMetrics" \
  -H "Content-Type: application/json" \
  -d '{
    "instance_id": "i-1234567890abcdef0",
    "start_time": "2024-01-15T00:00:00",
    "end_time": "2024-01-15T23:59:59",
    "metrics": ["CPUUtilization", "mem_used_percent"]
  }'
```

#### Cross-Account Metrics Fetch
```bash
curl -X POST "https://your-api-gateway-url.execute-api.region.amazonaws.com/dev/ec2/getMetrics" \
  -H "Content-Type: application/json" \
  -d '{
    "account_id": "123456789012",
    "role_name": "EC2CrossAccountMetricsRole",
    "instance_id": "i-1234567890abcdef0",
    "start_time": "2024-01-15T00:00:00",
    "end_time": "2024-01-15T23:59:59"
  }'
```

#### Fetch Alarms
```bash
curl -X POST "https://your-api-gateway-url.execute-api.region.amazonaws.com/dev/ec2/getAlarms" \
  -H "Content-Type: application/json" \
  -d '{
    "instance_id": "i-1234567890abcdef0",
    "include_history": true,
    "start_time": "2024-01-15T00:00:00",
    "end_time": "2024-01-15T23:59:59"
  }'
```

### Python Examples

#### Fetch Metrics
```python
import requests
import json

url = "https://your-api-gateway-url.execute-api.region.amazonaws.com/dev/ec2/getMetrics"

payload = {
    "instance_id": "i-1234567890abcdef0",
    "start_time": "2024-01-15T00:00:00",
    "end_time": "2024-01-15T23:59:59",
    "metrics": ["CPUUtilization", "mem_used_percent"]
}

response = requests.post(url, json=payload)
print(json.dumps(response.json(), indent=2))
```

#### Cross-Account Metrics
```python
import requests
import json

url = "https://your-api-gateway-url.execute-api.region.amazonaws.com/dev/ec2/getMetrics"

payload = {
    "account_id": "123456789012",
    "role_name": "EC2CrossAccountMetricsRole",
    "instance_id": "i-1234567890abcdef0",
    "start_time": "2024-01-15T00:00:00",
    "end_time": "2024-01-15T23:59:59"
}

response = requests.post(url, json=payload)
print(json.dumps(response.json(), indent=2))
```

## Deployment

### Prerequisites

1. AWS CLI configured
2. AWS SAM CLI installed
3. Python 3.10 or later
4. Required IAM roles and permissions

### Environment Variables

- `ROLE_NAME`: Name of the cross-account IAM role (default: EC2CrossAccountMetricsRole)
- `CASSANDRA_HOST`: Cassandra database host
- `CASSANDRA_PORT`: Cassandra database port (default: 9042)
- `CASSANDRA_USER`: Cassandra username
- `CASSANDRA_PASSWORD`: Cassandra password
- `CASSANDRA_KEYSPACE`: Cassandra keyspace (default: monitoring)
- `USE_AWS_KEYSPACE`: Use AWS Keyspaces instead of local Cassandra (default: false)

### Deployment Steps

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Build the application**:
   ```bash
   sam build
   ```

3. **Deploy**:
   ```bash
   sam deploy --guided
   ```

4. **Get API Gateway URL**:
   ```bash
   aws cloudformation describe-stacks \
     --stack-name ec2-monitoring-api \
     --query 'Stacks[0].Outputs[?OutputKey==`ApiGatewayApi`].OutputValue' \
     --output text
   ```

## Rate Limits

- **API Gateway**: 10,000 requests per second per region
- **CloudWatch**: 5 requests per second per account
- **Lambda**: 1,000 concurrent executions per region

## Security Considerations

- All API endpoints validate required parameters
- Cross-account authentication uses temporary credentials
- Database connections use SSL/TLS encryption
- IAM roles follow the principle of least privilege
- CORS is configured for web applications

## Support

For issues and questions:
1. Check the CloudWatch logs for Lambda function errors
2. Verify IAM permissions and trust relationships
3. Ensure proper time format (ISO 8601)
4. Validate instance IDs and account IDs

## Version History

- **v1.0.0**: Initial release with basic monitoring capabilities
- **v1.1.0**: Added cross-account support
- **v1.2.0**: Added metrics and alarms fetching APIs
- **v1.3.0**: Added database storage capabilities 