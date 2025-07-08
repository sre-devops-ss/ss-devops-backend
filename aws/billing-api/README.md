# Billing Monitoring

This project provides a Lambda-based solution for monitoring AWS Billing metrics and setting up alarms with customizable thresholds for billing-related monitoring.

## Features

- Monitor AWS billing and cost usage
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
├── utils/
│   ├── cross_account.py       # Cross-account authentication
│   └── cloudwatch_client.py   # CloudWatch operations
```

## Usage

(Describe usage for billing API here)

## Prerequisites

- Required IAM permissions for billing and cost monitoring

## Deployment

- Deploy using AWS SAM or CloudFormation.
- The Lambda function code should be placed in `../billing-api/` as referenced in `template.yaml`.

## License

MIT 