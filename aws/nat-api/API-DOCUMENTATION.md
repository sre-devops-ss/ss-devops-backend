# NAT Gateway Monitoring API Documentation

## Overview

This API provides a Lambda-based solution for monitoring AWS NAT Gateway metrics (PacketDropCount) and setting up alarms with customizable thresholds.

## Base URL

```
https://{api-gateway-id}.execute-api.{region}.amazonaws.com/{environment}
```

## Endpoint

### Install Monitoring

**POST** `/install`

Sets up monitoring for a NAT Gateway by creating a CloudWatch alarm for packet drop count.

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

- `nat_gateway_id` (required): NAT Gateway ID
- `account_id` (required): AWS account ID
- `region` (required): AWS region
- `config` (optional): Object with alarm configuration (e.g., `drop_threshold`)

**Response Example:**
```json
{
  "message": "Alarm created"
}
```

## Sample Event

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

## Error Responses

- **400**: Missing required parameters
- **500**: Internal server error

**Error Example:**
```json
{
  "error": "Missing parameters"
}
``` 