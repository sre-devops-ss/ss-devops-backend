# ECS API Documentation

## Endpoints

### 1. Create ECS Monitoring
- **POST /install**
  - **Request Example:**
  ```json
  {
  "account_id": "",
  "cluster_name": "",
  "service_name": ""
  }
```
  - **Response Example:**
    ```json
    {
      "statusCode": 200,
      "body": {
        "message": "ECS monitoring enabled successfully",
        "cluster_arn": "arn:aws:ecs:us-east-1:123456789012:cluster/my-cluster"
      }
    }
    ``` 