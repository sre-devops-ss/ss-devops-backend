# Billing Monitoring

This project provides a Lambda-based solution for monitoring AWS Billing metrics and setting up alarms with customizable thresholds for billing-related monitoring.

## Features

- Monitor AWS billing and cost usage
- Create budget alarms
- Create cost anomaly alarms
- Create data transfer alarms
- Customizable thresholds for each metric
- Deployable via AWS SAM/CloudFormation

## File Structure

```
billing-api/
├── template.yaml              # CloudFormation template
├── domain.yaml                # Custom domain configuration
├── requirements.txt           # Python dependencies
├── README.md                  # This file
├── API-DOCUMENTATION.md       # API documentation
├── health_check.py            # Health check endpoint
├── budget_create_alarm.py     # Budget alarm creation function
├── cost_anomaly_create_alarm.py # Cost anomaly alarm creation function
├── data_transfer_create_alarm.py # Data transfer alarm creation function
├── utils/
│   ├── cross_account.py       # Cross-account authentication
│   └── cloudwatch_client.py   # CloudWatch operations
```

## Usage

### 1. Create Budget Alarms

**POST** `/budget-create-alarm`

Creates CloudWatch alarms for budget monitoring.

### 2. Create Cost Anomaly Alarms

**POST** `/cost-anomaly-create-alarm`

Creates CloudWatch alarms for cost anomaly detection.

### 3. Create Data Transfer Alarms

**POST** `/data-transfer-create-alarm`

Creates CloudWatch alarms for data transfer monitoring.

## Prerequisites

- Required IAM permissions for billing and cost monitoring
- AWS Cost Explorer access
- CloudWatch permissions

## Deployment

- Deploy using AWS SAM or CloudFormation.
- The Lambda function code should be placed in `../billing-api/` as referenced in `template.yaml`.
- The stack will create an SSM parameter `/ss/backend/billing-monitoring-api/id` for the API Gateway ID.

## Environment Variables

- `ROLE_NAME`: Cross-account role name (if used)
- `REGION`: AWS region

## License

MIT 