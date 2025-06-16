# Lambda Function Monitoring Checklist

## Prerequisites
- [ ] Lambda function is deployed and running
- [ ] CloudWatch Logs are enabled for the function
- [ ] SNS topic exists for notifications
- [ ] IAM role has permissions for:
  - [ ] CloudWatch metrics
  - [ ] CloudWatch logs
  - [ ] SNS notifications
  - [ ] Lambda operations

## Metrics Collection
- [ ] Error Metrics
  - [ ] Invocation errors
  - [ ] Throttled invocations
  - [ ] Log errors (via metric filter)
- [ ] Performance Metrics
  - [ ] Duration
  - [ ] Concurrent executions
  - [ ] Memory usage
- [ ] Cost Metrics
  - [ ] Invocation count
  - [ ] Duration billing

## Alarms Configuration
- [ ] Error Alarms
  - [ ] Invocation error rate
  - [ ] Throttled invocation rate
  - [ ] Log error count
- [ ] Performance Alarms
  - [ ] Duration threshold
  - [ ] Memory usage threshold
  - [ ] Concurrent execution limit
- [ ] Cost Alarms
  - [ ] Invocation count threshold
  - [ ] Duration billing threshold

## Log Monitoring
- [ ] CloudWatch Logs Configuration
  - [ ] Log group created
  - [ ] Log retention period set
  - [ ] Metric filters configured
- [ ] Error Log Patterns
  - [ ] Exception patterns
  - [ ] Error message patterns
  - [ ] Stack trace patterns
- [ ] Performance Log Patterns
  - [ ] Duration patterns
  - [ ] Memory usage patterns
  - [ ] Cold start patterns

## Notification Configuration
- [ ] Alarm Notifications
  - [ ] Error notifications
  - [ ] Performance notifications
  - [ ] Cost notifications
- [ ] Log Notifications
  - [ ] Error log notifications
  - [ ] Performance log notifications
- [ ] SNS Topic Configuration
  - [ ] Topic created
  - [ ] Subscribers added
  - [ ] Access permissions set

## Verification Steps
1. [ ] Verify Metrics Collection
   - [ ] Check CloudWatch metrics
   - [ ] Verify metric filters
   - [ ] Test metric collection
2. [ ] Verify Alarms
   - [ ] Test alarm conditions
   - [ ] Check alarm actions
   - [ ] Verify notifications
3. [ ] Verify Logging
   - [ ] Check log groups
   - [ ] Verify log streams
   - [ ] Test log patterns
4. [ ] Verify Notifications
   - [ ] Test SNS delivery
   - [ ] Check notification format
   - [ ] Verify recipients

## Configuration Parameters
- Error Thresholds:
  - Error Rate: 1%
  - Throttle Rate: 1%
  - Log Error Count: 1
- Performance Thresholds:
  - Duration: 1000ms
  - Memory Usage: 80%
  - Concurrent Executions: 100
- Cost Thresholds:
  - Invocation Count: 1000
  - Duration Billing: $10
- Evaluation Periods: 2
- Period: 300 seconds
- Alarm Actions: SNS topic ARN 