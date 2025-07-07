# ASG Monitoring

This project provides a Lambda-based solution for monitoring AWS Auto Scaling Group (ASG) metrics and setting up alarms with customizable thresholds for both instance-level and scaling-level monitoring.

## Features

- Monitor ASG instance CPU and memory utilization
- Monitor ASG scaling activities and in-service instances
- Customizable thresholds for each metric
- Support for CloudWatch Agent metrics (memory monitoring)
- Deployable via AWS SAM/CloudFormation

## File Structure

```
asg-api/
├── template.yaml              # CloudFormation template
├── domain.yaml                # Custom domain configuration
├── requirements.txt           # Python dependencies
├── README.md                  # This file
├── API-DOCUMENTATION.md       # API documentation
├── health_check.py            # Health check endpoint
├── asg-create-alarm.py        # Main monitoring function
├── utils/
│   ├── cross_account.py       # Cross-account authentication
│   └── cloudwatch_client.py   # CloudWatch operations
```

## Usage

### 1. Create Instance Alarms

**POST** `/create-alarm`

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

**Response Example:**
```json
{
  "message": "Alarms created"
}
```

### 2. Create Scaling Alarms

**POST** `/create-alarm`

**Request Body:**
```json
{
  "event_type": "scaling",
  "asg_name": "my-production-asg",
  "config": {
    "scaling_threshold": 2,
    "period": 60,
    "evaluation_periods": 1,
    "alarm_actions": []
  }
}
```

**Response Example:**
```json
{
  "message": "Alarms created"
}
```

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

## Deployment

- Deploy using AWS SAM or CloudFormation.
- The Lambda function code should be placed in `../asg-api/` as referenced in `template.yaml`.
- The stack will create an SSM parameter `/ss/backend/asg-monitoring-api/id` for the API Gateway ID.

## Environment Variables

- `ROLE_NAME`: Cross-account role name (if used)
- `REGION`: AWS region

## Configuration Options

### Default Thresholds
- `cpu_threshold`: 80% (CPU utilization)
- `memory_threshold`: 85% (Memory utilization)
- `scaling_threshold`: 1 (Minimum in-service instances)
- `period`: 60 seconds (Evaluation period)
- `evaluation_periods`: 1 (Number of periods to evaluate)

### Customization
All thresholds and timing parameters can be customized through the `config` object in the request body.

## License

MIT 