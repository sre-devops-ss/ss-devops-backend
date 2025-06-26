# sso-api: IAM Role Creation Lambda

This Lambda function provides an API to create IAM roles in target AWS accounts using cross-account access. It is designed to be deployed in a management account and uses a cross-account role to assume into the target account.

## Features
- Create IAM roles in specified AWS accounts
- Attach managed policies to the created role
- Uses a reusable cross-account utility for secure access

## API Endpoint
- **POST /iam/create**
  - `account_id` (string, required): Target AWS account ID
  - `role_name` (string, required): Name for the new IAM role
  - `assume_role_policy_document` (object, required): Trust policy for the new role
  - `policies` (list, optional): List of managed policy ARNs to attach

### Example Request Body
```json
{
  "account_id": "123456789012",
  "role_name": "MyNewRole",
  "assume_role_policy_document": { ... },
  "policies": ["arn:aws:iam::aws:policy/ReadOnlyAccess"]
}
```

## Deployment
- Deploy using AWS SAM or your preferred method.
- See `template.yaml` for resource definitions and environment variables.

## Requirements
- Python 3.10+
- boto3, botocore, requests

## Folder Structure
- `iam_create.py`: Lambda handler for IAM role creation
- `utils/cross_account.py`: Cross-account utility for assuming roles
- `requirements.txt`: Python dependencies
- `template.yaml`: SAM/CloudFormation template 