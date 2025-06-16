# AWS Resource Monitoring API Documentation

## Overview
This API provides endpoints for monitoring various AWS resources including EC2 instances, RDS databases, ECS services, Auto Scaling Groups, and Target Groups. The API uses AWS IAM for authentication and provides real-time monitoring capabilities through CloudWatch metrics and alarms.

## Base URL
```
https://{api-id}.execute-api.{region}.amazonaws.com/prod/api/monitor
```

## Authentication
All API endpoints require AWS IAM authentication. Include the following headers in your requests:

```
Authorization: AWS4-HMAC-SHA256 Credential={access-key}/{date}/{region}/execute-api/aws4_request
X-Amz-Date: {timestamp}
```

## API Endpoints

### EC2 Monitoring

#### Enable EC2 Monitoring
```http
POST /ec2
```

Enable monitoring for an EC2 instance.

**Request Body:**
```json
{
    "instance_id": "i-1234567890abcdef0",
    "config": {
        "cpu_threshold": 80,
        "memory_threshold": 80,
        "disk_threshold": 80,
        "evaluation_periods": 2,
        "period": 300,
        "alarm_actions": ["arn:aws:sns:region:account-id:topic-name"]
    }
}
```

**Response:**
```json
{
    "statusCode": 200,
    "body": {
        "message": "EC2 monitoring enabled successfully",
        "instance_id": "i-1234567890abcdef0",
        "alarms_created": [
            "cpu-utilization-alarm",
            "memory-utilization-alarm",
            "disk-utilization-alarm"
        ]
    }
}
```

### RDS Monitoring

#### Enable RDS Monitoring
```http
POST /rds
```

Enable monitoring for an RDS instance.

**Request Body:**
```json
{
    "instance_id": "db-instance-1",
    "config": {
        "cpu_threshold": 80,
        "memory_threshold": 80,
        "connection_threshold": 80,
        "storage_threshold": 80,
        "evaluation_periods": 2,
        "period": 300,
        "alarm_actions": ["arn:aws:sns:region:account-id:topic-name"]
    }
}
```

**Response:**
```json
{
    "statusCode": 200,
    "body": {
        "message": "RDS monitoring enabled successfully",
        "instance_id": "db-instance-1",
        "alarms_created": [
            "cpu-utilization-alarm",
            "memory-utilization-alarm",
            "connection-count-alarm",
            "storage-space-alarm"
        ]
    }
}
```

### ECS Monitoring

#### Enable ECS Monitoring
```http
POST /ecs
```

Enable monitoring for an ECS service.

**Request Body:**
```json
{
    "cluster_name": "my-cluster",
    "service_name": "my-service",
    "config": {
        "cpu_threshold": 80,
        "memory_threshold": 80,
        "evaluation_periods": 2,
        "period": 300,
        "alarm_actions": ["arn:aws:sns:region:account-id:topic-name"]
    }
}
```

**Response:**
```json
{
    "statusCode": 200,
    "body": {
        "message": "ECS monitoring enabled successfully",
        "cluster_name": "my-cluster",
        "service_name": "my-service",
        "alarms_created": [
            "cpu-utilization-alarm",
            "memory-utilization-alarm"
        ]
    }
}
```

### ASG Monitoring

#### Enable ASG Monitoring
```http
POST /asg
```

Enable monitoring for an Auto Scaling Group.

**Request Body:**
```json
{
    "asg_name": "my-asg",
    "config": {
        "cpu_threshold": 80,
        "memory_threshold": 80,
        "disk_threshold": 80,
        "evaluation_periods": 2,
        "period": 300,
        "alarm_actions": ["arn:aws:sns:region:account-id:topic-name"]
    }
}
```

**Response:**
```json
{
    "statusCode": 200,
    "body": {
        "message": "ASG monitoring enabled successfully",
        "asg_name": "my-asg",
        "alarms_created": [
            "cpu-utilization-alarm",
            "memory-utilization-alarm",
            "disk-utilization-alarm"
        ]
    }
}
```

### Target Group Monitoring

#### Enable Target Group Monitoring
```http
POST /targetgroup
```

Enable monitoring for a Target Group.

**Request Body:**
```json
{
    "target_group_arn": "arn:aws:elasticloadbalancing:region:account-id:targetgroup/my-tg/1234567890abcdef",
    "config": {
        "response_time_threshold": 5,
        "request_count_threshold": 1000,
        "unhealthy_host_threshold": 1,
        "error_rate_threshold": 5,
        "evaluation_periods": 2,
        "period": 300,
        "alarm_actions": ["arn:aws:sns:region:account-id:topic-name"]
    }
}
```

**Response:**
```json
{
    "statusCode": 200,
    "body": {
        "message": "Target Group monitoring enabled successfully",
        "target_group_arn": "arn:aws:elasticloadbalancing:region:account-id:targetgroup/my-tg/1234567890abcdef",
        "alarms_created": [
            "response-time-alarm",
            "request-count-alarm",
            "unhealthy-host-alarm",
            "error-rate-alarm"
        ]
    }
}
```

### Lambda Monitoring

#### Enable Lambda Monitoring
```http
POST /lambda
```

Enable monitoring for a Lambda function.

**Request Body:**
```json
{
    "function_name": "my-function",
    "config": {
        "error_threshold": 1,
        "duration_threshold": 1000,
        "evaluation_periods": 2,
        "period": 300,
        "alarm_actions": ["arn:aws:sns:region:account-id:topic-name"]
    }
}
```

**Response:**
```json
{
    "statusCode": 200,
    "body": {
        "message": "Lambda monitoring enabled successfully",
        "function_name": "my-function",
        "alarms_created": [
            "my-function-error-alarm",
            "my-function-duration-alarm",
            "my-function-log-error-alarm"
        ]
    }
}
```

### Metrics Collection

#### Get Metrics
```http
GET /metrics
```

Get collected metrics for a resource.

**Query Parameters:**
- `resource_type`: Type of resource (ec2, rds, ecs, asg, targetgroup)
- `resource_id`: ID of the resource
- `metric_name`: Name of the metric
- `start_time`: Start time in ISO format
- `end_time`: End time in ISO format
- `period`: Period in seconds (default: 300)

**Response:**
```json
{
    "statusCode": 200,
    "body": {
        "resource_type": "ec2",
        "resource_id": "i-1234567890abcdef0",
        "metric_name": "CPUUtilization",
        "datapoints": [
            {
                "timestamp": "2024-03-20T10:00:00Z",
                "value": 45.2
            },
            {
                "timestamp": "2024-03-20T10:05:00Z",
                "value": 48.7
            }
        ]
    }
}
```

### Alarms Management

#### Get Alarms
```http
GET /alarms
```

Get alarms for a resource.

**Query Parameters:**
- `resource_type`: Type of resource (ec2, rds, ecs, asg, targetgroup)
- `resource_id`: ID of the resource

**Response:**
```json
{
    "statusCode": 200,
    "body": {
        "resource_type": "ec2",
        "resource_id": "i-1234567890abcdef0",
        "alarms": [
            {
                "alarm_name": "cpu-utilization-alarm",
                "metric_name": "CPUUtilization",
                "threshold": 80,
                "evaluation_periods": 2,
                "period": 300,
                "state": "OK"
            }
        ]
    }
}
```

## API Gateway Monitoring

### Enable API Gateway Monitoring
```http
POST /monitoring/apigateway
```

Enables monitoring for an API Gateway with configurable thresholds for errors and latency.

#### Request Body
```json
{
    "api_id": "string",
    "config": {
        "error_4xx_threshold": 10,
        "error_5xx_threshold": 5,
        "latency_threshold": 1000,
        "evaluation_periods": 2,
        "period": 300,
        "alarm_actions": [
            "arn:aws:sns:region:account:monitoring-alerts"
        ]
    }
}
```

#### Parameters
- `api_id` (required): The ID of the API Gateway to monitor
- `config` (optional): Configuration for monitoring thresholds and settings
  - `error_4xx_threshold`: Number of 4xx errors to trigger alarm (default: 10)
  - `error_5xx_threshold`: Number of 5xx errors to trigger alarm (default: 5)
  - `latency_threshold`: Maximum latency in milliseconds (default: 1000)
  - `evaluation_periods`: Number of periods to evaluate (default: 2)
  - `period`: Evaluation period in seconds (default: 300)
  - `alarm_actions`: List of SNS topic ARNs for notifications

#### Response
```json
{
    "statusCode": 200,
    "body": {
        "message": "API Gateway monitoring enabled successfully",
        "api_id": "string",
        "alarms_created": [
            "api-id-4xx-error-alarm",
            "api-id-5xx-error-alarm",
            "api-id-latency-alarm"
        ]
    }
}
```

#### Error Response
```json
{
    "statusCode": 400,
    "body": {
        "error": "Bad Request",
        "message": "api_id is required"
    }
}
```

#### Notes
- All alarms are stored in Cassandra for tracking
- Default thresholds are set based on AWS best practices
- Alarms are created in the same region as the API Gateway
- Notifications are sent to the specified SNS topics

## NAT Gateway Monitoring

### Enable NAT Gateway Monitoring
```http
POST /monitoring/nat
```

Enables monitoring for a NAT Gateway with configurable thresholds for packet drops and other metrics.

#### Request Body
```json
{
    "nat_id": "string",
    "config": {
        "packets_drop_threshold": 100,
        "evaluation_periods": 2,
        "period": 300,
        "alarm_actions": [
            "arn:aws:sns:region:account:monitoring-alerts"
        ]
    }
}
```

#### Parameters
- `nat_id` (required): The ID of the NAT Gateway to monitor
- `config` (optional): Configuration for monitoring thresholds and settings
  - `packets_drop_threshold`: Number of packet drops to trigger alarm (default: 100)
  - `evaluation_periods`: Number of periods to evaluate (default: 2)
  - `period`: Evaluation period in seconds (default: 300)
  - `alarm_actions`: List of SNS topic ARNs for notifications

#### Response
```json
{
    "statusCode": 200,
    "body": {
        "message": "NAT Gateway monitoring enabled successfully",
        "nat_id": "string",
        "alarms_created": [
            "nat-id-packets-drop-alarm"
        ]
    }
}
```

#### Error Response
```json
{
    "statusCode": 400,
    "body": {
        "error": "Bad Request",
        "message": "nat_id is required"
    }
}
```

#### Notes
- All alarms are stored in Cassandra for tracking
- Default thresholds are set based on AWS best practices
- Alarms are created in the same region as the NAT Gateway
- Notifications are sent to the specified SNS topics

## S3 Bucket Monitoring

### Enable S3 Bucket Monitoring
```http
POST /monitoring/s3
```

Enables monitoring for an S3 bucket with configurable thresholds for bucket size and automatic setup of delete event notifications for backup buckets.

#### Request Body
```json
{
    "bucket_name": "string",
    "config": {
        "bucket_size_threshold": 1000000000,
        "evaluation_periods": 2,
        "period": 300,
        "alarm_actions": [
            "arn:aws:sns:region:account:monitoring-alerts"
        ]
    }
}
```

#### Parameters
- `bucket_name` (required): The name of the S3 bucket to monitor
- `config` (optional): Configuration for monitoring thresholds and settings
  - `bucket_size_threshold`: Maximum bucket size in bytes (default: 1GB)
  - `evaluation_periods`: Number of periods to evaluate (default: 2)
  - `period`: Evaluation period in seconds (default: 300)
  - `alarm_actions`: List of SNS topic ARNs for notifications

#### Response
```json
{
    "statusCode": 200,
    "body": {
        "message": "S3 bucket monitoring enabled successfully",
        "bucket_name": "string",
        "alarms_created": [
            "bucket-name-size-alarm"
        ]
    }
}
```

#### Error Response
```json
{
    "statusCode": 400,
    "body": {
        "error": "Bad Request",
        "message": "bucket_name is required"
    }
}
```

#### Notes
- All alarms are stored in Cassandra for tracking
- Default thresholds are set based on AWS best practices
- For buckets with 'backup' in their name, delete event notifications are automatically configured
- Notifications are sent to the specified SNS topics
- Delete event notifications require a Lambda function named 'backup-delete-handler'

## AWS Billing Monitoring

### Enable Billing Monitoring
```http
POST /monitoring/billing
```

Enables monitoring for AWS billing with configurable thresholds for budgets, cost anomalies, and bandwidth costs.

#### Request Body
```json
{
    "config": {
        "monthly_budget": 1000,
        "anomaly_threshold": 20,
        "bandwidth_threshold": 100,
        "evaluation_periods": 2,
        "period": 300,
        "alarm_actions": [
            "arn:aws:sns:region:account:monitoring-alerts"
        ],
        "notification_email": "admin@example.com"
    }
}
```

#### Parameters
- `config` (optional): Configuration for monitoring thresholds and settings
  - `monthly_budget`: Monthly budget limit in USD (default: 1000)
  - `anomaly_threshold`: Cost anomaly threshold percentage (default: 20)
  - `bandwidth_threshold`: Bandwidth cost threshold in USD (default: 100)
  - `evaluation_periods`: Number of periods to evaluate (default: 2)
  - `period`: Evaluation period in seconds (default: 300)
  - `alarm_actions`: List of SNS topic ARNs for notifications
  - `notification_email`: Email address for notifications

#### Response
```json
{
    "statusCode": 200,
    "body": {
        "message": "Billing monitoring enabled successfully",
        "monitoring_configured": [
            "budget",
            "cost_anomaly",
            "bandwidth_cost"
        ]
    }
}
```

#### Error Response
```json
{
    "statusCode": 500,
    "body": {
        "error": "Internal Server Error",
        "message": "Error message details"
    }
}
```

#### Notes
- All alarms are stored in Cassandra for tracking
- Default thresholds are set based on AWS best practices
- Budget notifications are sent at 80% and 100% of the monthly budget
- Cost anomaly detection runs daily
- Bandwidth cost monitoring includes CloudFront and other data transfer costs
- Notifications are sent to both SNS topics and email addresses

## Error Responses

All endpoints may return the following error responses:

### 400 Bad Request
```json
{
    "statusCode": 400,
    "body": {
        "error": "Bad Request",
        "message": "Invalid request parameters"
    }
}
```

### 404 Not Found
```json
{
    "statusCode": 404,
    "body": {
        "error": "Not Found",
        "message": "Resource not found"
    }
}
```

### 500 Internal Server Error
```json
{
    "statusCode": 500,
    "body": {
        "error": "Internal Server Error",
        "message": "An error occurred while processing your request"
    }
}
```

## Rate Limits
- Maximum 100 requests per second per API key
- Maximum 1000 requests per minute per API key

## Best Practices
1. Always include proper error handling in your requests
2. Use appropriate timeouts for long-running operations
3. Implement retry logic for failed requests
4. Cache responses when appropriate
5. Monitor your API usage to stay within rate limits

## Example Usage

### Python Example
```python
import boto3
import requests
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from datetime import datetime

def get_signed_headers(method, url, region, service='execute-api'):
    request = AWSRequest(method=method, url=url)
    credentials = boto3.Session().get_credentials()
    SigV4Auth(credentials, service, region).add_auth(request)
    return dict(request.headers)

# Example: Enable EC2 monitoring
def enable_ec2_monitoring(instance_id, api_url, region):
    url = f"{api_url}/ec2"
    headers = get_signed_headers('POST', url, region)
    
    payload = {
        "instance_id": instance_id,
        "config": {
            "cpu_threshold": 80,
            "memory_threshold": 80,
            "disk_threshold": 80
        }
    }
    
    response = requests.post(url, json=payload, headers=headers)
    return response.json()
```

### cURL Example
```bash
# Get metrics for an EC2 instance
curl -X GET "https://{api-id}.execute-api.{region}.amazonaws.com/prod/api/monitor/metrics?resource_type=ec2&resource_id=i-1234567890abcdef0" \
  -H "Authorization: AWS4-HMAC-SHA256 Credential={access-key}/{date}/{region}/execute-api/aws4_request" \
  -H "X-Amz-Date: {timestamp}"
```

## Support
For support or questions about the API, please contact the development team or raise an issue in the project repository. 