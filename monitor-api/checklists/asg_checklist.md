# Auto Scaling Group Monitoring Checklist

## Prerequisites
- [ ] Auto Scaling Group is configured
- [ ] Launch template/configuration includes:
  - [ ] Required IAM role with:
    - [ ] CloudWatchAgentServerPolicy
    - [ ] AmazonSSMManagedInstanceCore
  - [ ] User data script for:
    - [ ] SSM agent installation
    - [ ] CloudWatch agent installation
- [ ] SNS topic exists for notifications
- [ ] IAM role has permissions for:
  - [ ] CloudWatch metrics
  - [ ] CloudWatch logs
  - [ ] SSM operations
  - [ ] SNS notifications
  - [ ] Auto Scaling operations

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

## ASG Metrics Collection
- [ ] Group Metrics
  - [ ] GroupMinSize
  - [ ] GroupMaxSize
  - [ ] GroupDesiredCapacity
  - [ ] GroupInServiceInstances
  - [ ] GroupPendingInstances
  - [ ] GroupStandbyInstances
  - [ ] GroupTerminatingInstances
  - [ ] GroupTotalInstances
- [ ] Target Tracking Metrics
  - [ ] CPU utilization target
  - [ ] Memory utilization target
  - [ ] Request count target
  - [ ] Average network traffic target

## Alarms Configuration
- [ ] Instance Level Alarms
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
- [ ] ASG Level Alarms
  - [ ] Group Size Alarms
    - [ ] High instance count
    - [ ] Low instance count
  - [ ] Scaling Activity Alarms
    - [ ] Failed scaling activities
    - [ ] Failed instance launches
    - [ ] Failed instance terminations

## Scaling Notifications
- [ ] EC2 Instance Events
  - [ ] Instance launch
  - [ ] Instance terminate
  - [ ] Instance fail to launch
  - [ ] Instance fail to terminate
- [ ] ASG Events
  - [ ] Scaling activity start
  - [ ] Scaling activity end
  - [ ] Scaling activity fail
- [ ] Notification Configuration
  - [ ] SNS topic subscription
  - [ ] Email notifications
  - [ ] CloudWatch Events rules

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

## Verification Steps
1. [ ] Verify Launch Configuration
   - [ ] Check IAM role
   - [ ] Verify user data script
   - [ ] Test instance launch
2. [ ] Verify Instance Setup
   - [ ] Check SSM agent
   - [ ] Check CloudWatch agent
   - [ ] Verify metrics collection
3. [ ] Verify ASG Configuration
   - [ ] Check scaling policies
   - [ ] Verify target tracking
   - [ ] Test scaling events
4. [ ] Verify Monitoring
   - [ ] Check CloudWatch metrics
   - [ ] Verify alarms
   - [ ] Test notifications
5. [ ] Verify Logging
   - [ ] Check log groups
   - [ ] Verify log streams
   - [ ] Test log collection

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
- Scaling Cooldown: 300 seconds
- Health Check Grace Period: 300 seconds 