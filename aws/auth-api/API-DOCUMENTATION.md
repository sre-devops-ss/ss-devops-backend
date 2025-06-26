# Auth API Documentation

## Endpoints

### 1. Create User
- **POST /create**
  - **Request Example:**
    ```json
    {
      "username": "john.doe",
      "email": "john@example.com",
      "password": "SecretPass123!"
    }
    ```
  - **Response Example:**
    ```json
    {
      "statusCode": 200,
      "body": {
        "message": "User created successfully",
        "user_id": "abc123"
      }
    }
    ```

### 2. Login User
- **POST /login**
  - **Request Example:**
    ```json
    {
      "username": "john.doe",
      "password": "SecretPass123!"
    }
    ```
  - **Response Example:**
    ```json
    {
      "statusCode": 200,
      "body": {
        "access_token": "eyJraWQiOiJ...",
        "refresh_token": "eyJjdHkiOiJ..."
      }
    }
    ```

### 3. Add User to Group
- **POST /addgroup**
  - **Request Example:**
    ```json
    {
      "username": "john.doe",
      "group": "admin"
    }
    ```
  - **Response Example:**
    ```json
    {
      "statusCode": 200,
      "body": {
        "message": "User added to group"
      }
    }
    ```

### 4. Get Access ID
- **POST /accessId**
  - **Request Example:**
    ```json
    {
      "refresh_token": "eyJjdHkiOiJ..."
    }
    ```
  - **Response Example:**
    ```json
    {
      "statusCode": 200,
      "body": {
        "access_id": "xyz789"
      }
    }
    ``` 