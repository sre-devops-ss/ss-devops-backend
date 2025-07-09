# ASG Monitoring

This project provides a modular Lambda-based solution for monitoring AWS Auto Scaling Group (ASG) metrics including CPU utilization, memory utilization, and scaling activities. Each metric type has its own dedicated endpoint for maximum flexibility.

## Features

- Monitor ASG instance CPU utilization
- Monitor ASG instance memory utilization (requires CloudWatch Agent)
- Monitor ASG scaling activities
- Individual endpoints for creating specific alarm types
- Customizable thresholds for each metric
- Cross-account monitoring support
- Health check endpoint
- Deployable via AWS SAM/CloudFormation

## Architecture

The solution creates 4 Lambda functions:
1. **CPU Alarm Function** - Creates CPU utilization alarms for EC2 instances
2. **Memory Alarm Function** - Creates memory utilization alarms for EC2 instances
3. **Scaling Alarm Function** - Creates scaling activity alarms for ASGs
4. **Health Check Function** - Provides API health status

## File Structure

```
asg-api/
├── template.yaml                           # CloudFormation template
├── domain.yaml                             # Custom domain configuration
├── requirements.txt                        # Python dependencies
├── README.md                               # This file
├── API-DOCUMENTATION.md                    # Detailed API documentation
├── health_check.py                         # Health check endpoint
├── asg_cpu_utilization-alarm-creation.py   # CPU utilization alarm creation
├── asg_memory_utilization-alarm-creation.py # Memory utilization alarm creation
├── asg_scaling_notification_alarm_creation.py # Scaling activity alarm creation
└── utils/
    ├── cross_account.py                    # Cross-account authentication
    └── cloudwatch_client.py                # CloudWatch operations
```

## API Endpoints

### Individual Alarm Creation
- **POST** `/alarms/cpu` - Create CPU utilization alarms
- **POST** `/alarms/memory` - Create memory utilization alarms
- **POST** `/alarms/scaling` - Create scaling activity alarms

### Health Check
**GET** `/health` - Check API health status

## Usage Examples

### CPU Utilization Alarm Creation

**Request:**
```json
POST /alarms/cpu
{
  "instance_ids": ["i-1234567890abcdef0", "i-0987654321fedcba0"],
  "cpu_threshold": 75,
  "period": 300,
  "evaluation_periods": 2
}
```

**Response:**
```json
{
  "message": "CPU alarms created"
}
```

### Memory Utilization Alarm Creation

**Request:**
```json
POST /alarms/memory
{
  "instance_ids": ["i-1234567890abcdef0"],
  "memory_threshold": 90,
  "period": 60,
  "evaluation_periods": 1
}
```

**Response:**
```json
{
  "message": "Memory alarms created"
}
```

### Scaling Activity Alarm Creation

**Request:**
```json
POST /alarms/scaling
{
  "asg_name": "production-asg",
  "scaling_threshold": 2,
  "period": 300,
  "evaluation_periods": 2
}
```

**Response:**
```json
{
  "message": "Scaling alarm created"
}
```

## Configuration Options

### Default Thresholds
- **CPU Utilization**: 80% average
- **Memory Utilization**: 85% average
- **Scaling Threshold**: 1 in-service instance
- **Period**: 60 seconds
- **Evaluation Periods**: 1

### Customizable Parameters
- `cpu_threshold`: CPU utilization percentage before alarm
- `memory_threshold`: Memory utilization percentage before alarm
- `scaling_threshold`: Minimum number of in-service instances
- `period`: Evaluation period in seconds
- `evaluation_periods`: Number of periods to evaluate
- `alarm_actions`: Array of SNS topic ARNs for notifications

## Prerequisites

### For Memory Monitoring
To enable memory utilization monitoring, ensure that:
1. CloudWatch Agent is installed on the EC2 instances
2. The agent is configured to collect memory metrics
3. The agent is running and sending data to CloudWatch

### Required IAM Permissions
The Lambda functions require the following permissions:
- `cloudwatch:PutMetricAlarm`
- `autoscaling:DescribeAutoScalingGroups`
- `ec2:DescribeInstances`
- `sts:AssumeRole` (for cross-account access)

## Deployment

### Prerequisites
- AWS SAM CLI installed
- Cross-account role configured
- SNS topic for alarm notifications
- SSM parameters configured

### Deploy Steps
1. Build the SAM application:
   ```bash
   sam build
   ```

2. Deploy the stack:
   ```bash
   sam deploy --guided
   ```

3. The stack will create:
   - 4 Lambda functions
   - API Gateway with 4 endpoints
   - SSM parameter for API Gateway ID
   - IAM roles and policies

### Environment Variables
- `ROLE_NAME`: Cross-account role name
- `REGION`: AWS region
- `CASSANDRA_HOST`: Cassandra host (if using)
- `CASSANDRA_PORT`: Cassandra port (if using)

## Monitoring

### CloudWatch Alarms Created
- **CPU Alarm**: `{instance_id}-cpu-utilization` - Triggers when CPU exceeds threshold
- **Memory Alarm**: `{instance_id}-memory-utilization` - Triggers when memory exceeds threshold
- **Scaling Alarm**: `{asg_name}-scaling-activity` - Triggers when in-service instances below threshold

### CloudWatch Metrics

#### CPU Utilization
- **Namespace**: `AWS/EC2`
- **Metric**: `CPUUtilization`
- **Statistic**: Average
- **Unit**: Percent

#### Memory Utilization
- **Namespace**: `CWAgent`
- **Metric**: `mem_used_percent`
- **Statistic**: Average
- **Unit**: Percent

#### Scaling Activity
- **Namespace**: `AWS/AutoScaling`
- **Metric**: `GroupInServiceInstances`
- **Statistic**: Average
- **Unit**: Count

### Alarm Actions
- All alarms are configured to send notifications to the SNS topic
- Additional alarm actions can be specified in the config

## Security

- Cross-account access using IAM roles
- Least privilege IAM policies
- SSM parameter encryption for sensitive data
- CORS configuration for API Gateway

## Troubleshooting

### Common Issues
1. **Cross-account access denied**: Verify role ARN and permissions
2. **Memory metrics not available**: Ensure CloudWatch Agent is installed and configured
3. **Alarm creation fails**: Verify CloudWatch permissions
4. **API Gateway errors**: Check CORS configuration

### Logs
- Lambda function logs are available in CloudWatch Logs
- Each function has its own log group
- Log level is set to INFO for detailed debugging

## License

MIT 