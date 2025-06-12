# EC2 Instance Monitoring Checklist

## Prerequisites
- [ ] EC2 instance is running
- [ ] Instance has required IAM role with:
  - [ ] CloudWatchAgentServerPolicy
  - [ ] AmazonSSMManagedInstanceCore
- [ ] SSM agent is installed and running
- [ ] CloudWatch agent is installed and running
- [ ] SNS topic exists for notifications
- [ ] IAM role has permissions for:
  - [ ] CloudWatch metrics
  - [ ] CloudWatch logs
  - [ ] SSM operations
  - [ ] SNS notifications

## Instance Metrics Collection
- [ ] CPU Utilization
  - [ ] Basic metrics (AWS provided)
  - [ ] Detailed metrics (CloudWatch agent)
- [ ] Memory Utilization
  - [ ] CloudWatch agent metrics
  - [ ] Memory used percentage
  - [ ] Swap usage
- [ ] Disk Utilization
  - [ ] Root volume
  - [ ] Additional volumes
- [ ] Network Performance
  - [ ] Network in/out
  - [ ] Network packets
  - [ ] Network errors

## Alarms Configuration
- [ ] CPU Utilization Alarms
  - [ ] High CPU (80%)
  - [ ] Critical CPU (90%)
- [ ] Memory Utilization Alarms
  - [ ] High Memory (80%)
  - [ ] Critical Memory (90%)
- [ ] Disk Space Alarms
  - [ ] High Disk Usage (80%)
  - [ ] Critical Disk Usage (90%)
- [ ] Status Check Alarms
  - [ ] System status check
  - [ ] Instance status check

## Log Monitoring
- [ ] System Logs
  - [ ] /var/log/syslog (Ubuntu)
  - [ ] /var/log/messages (RHEL/Amazon Linux)
- [ ] Application Logs
  - [ ] Custom application logs
  - [ ] Error logs
- [ ] CloudWatch Logs Configuration
  - [ ] Log groups created
  - [ ] Log streams configured
  - [ ] Retention period set

## Notification Configuration
- [ ] Alarm Notifications
  - [ ] Email notifications
  - [ ] SNS topic subscription
- [ ] Status Check Notifications
  - [ ] System status failures
  - [ ] Instance status failures
- [ ] Metric Alarms
  - [ ] High utilization alerts
  - [ ] Critical utilization alerts

## Verification Steps
1. [ ] Verify IAM role and policies
   - [ ] Check role attachment
   - [ ] Verify policy permissions
2. [ ] Verify SSM agent
   - [ ] Check agent status
   - [ ] Test SSM connectivity
3. [ ] Verify CloudWatch agent
   - [ ] Check agent status
   - [ ] Verify metrics collection
4. [ ] Verify metrics collection
   - [ ] Check CloudWatch metrics
   - [ ] Verify custom metrics
5. [ ] Verify alarm triggers
   - [ ] Test alarm conditions
   - [ ] Check notifications
6. [ ] Verify log collection
   - [ ] Check log groups
   - [ ] Verify log streams
7. [ ] Verify instance health
   - [ ] Check system status
   - [ ] Check instance status

## Configuration Parameters
- CPU Thresholds:
  - High: 80%
  - Critical: 90%
- Memory Thresholds:
  - High: 80%
  - Critical: 90%
- Disk Thresholds:
  - High: 80%
  - Critical: 90%
- Evaluation Periods: 2
- Period: 300 seconds
- Alarm Actions: SNS topic ARN 