# API Gateway Monitoring

This project provides a modular Lambda-based solution for monitoring AWS API Gateway metrics (4xx, 5xx errors, and latency) and setting up alarms with customizable thresholds. Each alarm type has its own dedicated endpoint for maximum flexibility.

## Features

- Monitor API Gateway 4xx, 5xx error rates, and latency
- Individual endpoints for creating specific alarm types
- Customizable thresholds for each metric
- Cross-account monitoring support
- Health check endpoint
- Deployable via AWS SAM/CloudFormation

## Architecture

The solution creates 4 Lambda functions:
1. **4XX Alarm Function** - Creates only 4XX error alarms
2. **5XX Alarm Function** - Creates only 5XX error alarms
3. **Latency Alarm Function** - Creates only latency alarms
4. **Health Check Function** - Provides API health status

## File Structure

```
apigateway-api/
├── template.yaml                    # CloudFormation template
├── domain.yaml                      # Custom domain configuration
├── requirements.txt                 # Python dependencies
├── README.md                        # This file
├── API-DOCUMENTATION.md             # Detailed API documentation
├── health_check.py                  # Health check endpoint
├── apigateway_4xx_alarm_create.py   # 4XX error alarm creation
├── apigateway_5xx_alarm_creation.py # 5XX error alarm creation
├── apigateway_latency_alarm_create.py # Latency alarm creation
└── utils/
    ├── cross_account.py             # Cross-account authentication
    └── cloudwatch_client.py         # CloudWatch operations
```

## API Endpoints

### Individual Alarm Creation
- **POST** `/alarms/4xx` - Create 4XX error alarm
- **POST** `/alarms/5xx` - Create 5XX error alarm  
- **POST** `/alarms/latency` - Create latency alarm

### Health Check
**GET** `/health` - Check API health status

## Usage Examples

### 4XX Error Alarm Creation

**Request:**
```json
POST /alarms/4xx
{
  "api_name": "MyApiName",
  "stage": "prod",
  "account_id": "123456789012",
  "region": "us-east-1",
  "config": {
    "4xx_threshold": 15,
    "period": 60,
    "evaluation_periods": 1
  }
}
```

**Response:**
```json
"4XX error alarm created"
```

### 5XX Error Alarm Creation

**Request:**
```json
POST /alarms/5xx
{
  "api_name": "MyApiName",
  "stage": "prod",
  "account_id": "123456789012",
  "config": {
    "5xx_threshold": 2
  }
}
```

**Response:**
```json
"5XX error alarm created"
```

### Latency Alarm Creation

**Request:**
```json
POST /alarms/latency
{
  "api_name": "MyApiName",
  "stage": "prod",
  "account_id": "123456789012",
  "config": {
    "latency_threshold": 1500
  }
}
```

**Response:**
```json
"Latency alarm created"
```

## Configuration Options

### Default Thresholds
- **4XX Errors**: 10 errors per period
- **5XX Errors**: 1 error per period
- **Latency**: 1000ms average
- **Period**: 60 seconds
- **Evaluation Periods**: 1

### Customizable Parameters
- `4xx_threshold`: Number of 4XX errors before alarm
- `5xx_threshold`: Number of 5XX errors before alarm
- `latency_threshold`: Latency in milliseconds
- `period`: Evaluation period in seconds
- `evaluation_periods`: Number of periods to evaluate

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
- **4XX Error Alarm**: Triggers when 4XX error count exceeds threshold
- **5XX Error Alarm**: Triggers when 5XX error count exceeds threshold
- **Latency Alarm**: Triggers when average latency exceeds threshold

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
2. **SNS topic not found**: Check SSM parameter `/devops-backend/snstopic/arn`
3. **Alarm creation fails**: Verify CloudWatch permissions
4. **API Gateway errors**: Check CORS configuration

### Logs
- Lambda function logs are available in CloudWatch Logs
- Each function has its own log group
- Log level is set to INFO for detailed debugging

## License

MIT 