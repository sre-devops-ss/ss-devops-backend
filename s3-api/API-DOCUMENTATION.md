# S3 API Documentation

## Endpoints

### 1. Create S3 Monitoring Alarm
- **POST alarm/create/all**
  - **Request Example:**
    ```json
    {
      "bucket_name": "my-bucket",
      "account_id": "",
      "config": { "object_count_threshold": 100000 }
    }
    ```
  - **Response Example:**
    ```json
    {
      "statusCode": 200,
      "body": {
        "message": "S3 monitoring alarm created successfully",
        "bucket_name": "my-bucket"
      }
    }
    ```

### 2. Delete S3 Notification
- **POST /notification/deleteObject**
  - **Request Example:**
    ```json
    {
      "bucket_name": "my-bucket",
      "object_key": "path/to/object.txt"
    }
    ```
  - **Response Example:**
    ```json
    {
      "statusCode": 200,
      "body": {
        "message": "S3 delete notification processed",
        "object_key": "path/to/object.txt"
      }
    }
    ``` 