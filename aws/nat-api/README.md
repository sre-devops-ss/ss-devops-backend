# NAT Gateway Monitoring

This project provides a Lambda-based solution for monitoring AWS NAT Gateway metrics (PacketDropCount) and setting up alarms with customizable thresholds.

## Features

- Monitor NAT Gateway packet drop count
- Customizable thresholds for alarms
- Deployable via AWS SAM/CloudFormation

## File Structure

```
nat-api/
├── template.yaml              # CloudFormation template (to be created)
├── requirements.txt           # Python dependencies
├── README.md                  # This file
├── nat_monotoring_create.py   # Lambda function for alarm creation
├── utils/
│   └── cross_account.py       # Cross-account authentication (to be added)
```

## Usage

### Install Monitoring

**POST** `/install`

**Request Body:**
```json
{
  "nat_gateway_id": "nat-0abc123456789xyz",
  "account_id": "123456789012",
  "region": "ap-south-1",
  "config": {
    "drop_threshold": 50
  }
}
```

**Response Example:**
```json
{
  "message": "Alarm created"
}
```

## Deployment

- Deploy using AWS SAM or CloudFormation.
- The Lambda function code should be placed in `nat_monotoring_create.py` as referenced in `template.yaml`.

## Environment Variables

- `ROLE_NAME`: Cross-account role name (required)
- `REGION`: AWS region

## License

MIT 