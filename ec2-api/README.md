# EC2 Monitoring API

This API provides comprehensive monitoring capabilities for EC2 instances across multiple AWS accounts using cross-account authentication.

## Features

- **Cross-Account Monitoring**: Monitor EC2 instances in different AWS accounts
- **CloudWatch Integration**: Create and manage CloudWatch alarms for CPU, memory, and disk utilization
- **CloudWatch Agent Setup**: Automatically install and configure CloudWatch agent on instances
- **Database Storage**: Store metrics and alarm history in Cassandra database
- **RESTful API**: HTTP endpoints for all monitoring operations

## API Endpoints

### 1. Create EC2 Monitoring (`POST /ec2/install`)

Sets up monitoring for EC2 instances by creating CloudWatch alarms and optionally installing CloudWatch agent.

**Request Body:**
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

**Response:**
```json
{
  "statusCode": 200,
  "body": {
    "message": "EC2 monitoring enabled successfully",
    "instances": ["i-1234567890abcdef0", "i-0987654321fedcba0"]
  }
}
```

### 2. Get EC2 Alarms (`GET /ec2/getAlarms`)

Retrieves alarm information for EC2 instances.

**Query Parameters:**
- `account_id`: AWS account ID
- `instance_id`: EC2 instance ID
- `start_time` (optional): Start time in ISO format
- `end_time` (optional): End time in ISO format

### 3. Update Metrics to Database (`POST /ec2/updateMetricsToDb`)

Fetches CloudWatch metrics and stores them in Cassandra database.

**Request Body:**
```json
{
  "account_id": "123456789012",
  "instance_id": "i-1234567890abcdef0",
  "region": "us-east-1",
  "start_time": "2024-01-01T00:00:00",
  "end_time": "2024-01-01T23:59:59"
}
```

### 4. Update Alarms to Database (`POST /ec2/updateAlarmToDb`)

Fetches CloudWatch alarm history and stores it in Cassandra database.

**Request Body:**
```json
{
  "account_id": "123456789012",
  "instance_id": "i-1234567890abcdef0",
  "region": "us-east-1",
  "start_time": "2024-01-01T00:00:00",
  "end_time": "2024-01-01T23:59:59"
}
```

## Prerequisites

### 1. Cross-Account IAM Role

Create an IAM role in the target account with the following permissions:

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

### 2. Trust Relationship

Configure the trust relationship to allow the monitoring account to assume the role:

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

### 3. Cassandra Database

Set up a Cassandra database with the following tables:

- `ec2_metrics`: Stores CloudWatch metrics
- `ec2_alarms`: Stores current alarm states
- `ec2_alarm_history`: Stores alarm history

## Environment Variables

- `ROLE_NAME`: Name of the cross-account IAM role (default: EC2CrossAccountMetricsRole)
- `CASSANDRA_HOST`: Cassandra database host
- `CASSANDRA_PORT`: Cassandra database port (default: 9042)
- `CASSANDRA_USER`: Cassandra username
- `CASSANDRA_PASSWORD`: Cassandra password
- `CASSANDRA_KEYSPACE`: Cassandra keyspace (default: monitoring)
- `USE_AWS_KEYSPACE`: Use AWS Keyspaces instead of local Cassandra (default: false)

## Deployment

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Deploy using AWS SAM:
   ```bash
   sam build
   sam deploy --guided
   ```

## Monitoring Configuration

The API creates the following CloudWatch alarms for each EC2 instance:

1. **CPU Utilization**: Monitors CPU usage above threshold (default: 80%)
2. **Memory Utilization**: Monitors memory usage above threshold (default: 85%)
3. **Disk Utilization**: Monitors disk usage above threshold (default: 85%)

## CloudWatch Agent

The API can automatically install and configure the CloudWatch agent on EC2 instances to collect:

- Memory utilization metrics
- Disk utilization metrics
- Load average metrics
- Swap utilization metrics

## Error Handling

The API includes comprehensive error handling for:

- Invalid account IDs or instance IDs
- Cross-account role assumption failures
- CloudWatch API errors
- Database connection issues
- Missing required parameters

## Security

- All API endpoints validate required parameters
- Cross-account authentication uses temporary credentials
- Database connections use SSL/TLS encryption
- IAM roles follow the principle of least privilege 