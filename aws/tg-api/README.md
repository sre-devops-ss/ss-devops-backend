# Target Group Monitoring

This project provides a modular Lambda-based solution for monitoring AWS Application Load Balancer (ALB) Target Group metrics including response time, request count, and unhealthy host count. Each metric type has its own dedicated endpoint for maximum flexibility.

## Features

- Monitor ALB Target Group response time
- Monitor ALB Target Group request count
- Monitor ALB Target Group unhealthy host count
- Individual endpoints for creating specific alarm types
- Customizable thresholds for each metric
- Cross-account monitoring support
- Health check endpoint
- Deployable via AWS SAM/CloudFormation

## Architecture

The solution creates 4 Lambda functions:
1. **Response Time Alarm Function** - Creates response time alarms for target groups
2. **Request Count Alarm Function** - Creates request count alarms for target groups
3. **Unhealthy Host Alarm Function** - Creates unhealthy host count alarms for target groups
4. **Health Check Function** - Provides API health status

## File Structure

```
tg-api/
├── template.yaml                           # CloudFormation template
├── domain.yaml                             # Custom domain configuration
├── requirements.txt                        # Python dependencies
├── README.md                               # This file
├── API-DOCUMENTATION.md                    # Detailed API documentation
├── health_check.py                         # Health check endpoint
├── tg_response_time_alarm_create.py        # Response time alarm creation
├── tg_request_count_alarm_create.py        # Request count alarm creation
├── tg_unhealthy_host_alarm_create.py       # Unhealthy host alarm creation
└── utils/
    ├── cross_account.py                    # Cross-account authentication
    └── cloudwatch_client.py                # CloudWatch operations
```

## API Endpoints

### Individual Alarm Creation
- **POST** `/tg/response-time` - Create response time alarms
- **POST** `/tg/request-count` - Create request count alarms
- **POST** `/tg/unhealthy-hosts` - Create unhealthy host count alarms

### Health Check
**GET** `/health` - Check API health status

## Usage Examples

### Response Time Alarm Creation

**Request:**
```json
POST /tg/response-time
{
  "load_balancer_name": "prod-alb",
  "target_group_name": "web-servers",
  "config": {
    "threshold": 3.0,
    "period": 300,
    "evaluation_periods": 2
  }
}
```

**Response:**
```json
{
  "message": "Response time alarm created"
}
```

### Request Count Alarm Creation

**Request:**
```json
POST /tg/request-count
{
  "load_balancer_name": "prod-alb",
  "target_group_name": "web-servers",
  "config": {
    "threshold": 500,
    "period": 60,
    "evaluation_periods": 1
  }
}
```

**Response:**
```json
{
  "message": "Request count alarm created"
}
```

### Unhealthy Host Alarm Creation

**Request:**
```json
POST /tg/unhealthy-hosts
{
  "load_balancer_name": "prod-alb",
  "target_group_name": "web-servers",
  "config": {
    "threshold": 2,
    "period": 300,
    "evaluation_periods": 2
  }
}
```

**Response:**
```json
{
  "message": "Unhealthy host alarm created"
}
```

## Configuration Options

### Default Thresholds
- **Response Time**: 1.0 seconds average
- **Request Count**: 1000 requests per period
- **Unhealthy Host Count**: 1 unhealthy host
- **Period**: 60 seconds
- **Evaluation Periods**: 1

### Customizable Parameters
- `threshold`: Threshold value for the specific metric
- `period`: Evaluation period in seconds
- `evaluation_periods`: Number of periods to evaluate
- `alarm_actions`: Array of SNS topic ARNs for notifications

## Prerequisites

### Required IAM Permissions
The Lambda functions require the following permissions:
- `cloudwatch:PutMetricAlarm`
- `elasticloadbalancing:DescribeTargetGroups`
- `elasticloadbalancing:DescribeLoadBalancers`
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
- **Response Time Alarm**: `{target_group_name}-response-time` - Triggers when response time exceeds threshold
- **Request Count Alarm**: `{target_group_name}-request-count` - Triggers when request count exceeds threshold
- **Unhealthy Host Alarm**: `{target_group_name}-unhealthy-hosts` - Triggers when unhealthy host count exceeds threshold

### CloudWatch Metrics

#### Response Time
- **Namespace**: `AWS/ApplicationELB`
- **Metric**: `TargetResponseTime`
- **Statistic**: Average
- **Unit**: Seconds

#### Request Count
- **Namespace**: `AWS/ApplicationELB`
- **Metric**: `RequestCount`
- **Statistic**: Sum
- **Unit**: Count

#### Unhealthy Host Count
- **Namespace**: `AWS/ApplicationELB`
- **Metric**: `UnHealthyHostCount`
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
2. **Target group not found**: Ensure target group exists and is accessible
3. **Alarm creation fails**: Verify CloudWatch permissions
4. **API Gateway errors**: Check CORS configuration

### Logs
- Lambda function logs are available in CloudWatch Logs
- Each function has its own log group
- Log level is set to INFO for detailed debugging

## License

MIT 