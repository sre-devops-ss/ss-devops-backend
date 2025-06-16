# ECS Service Monitoring Checklist

## Prerequisites
- [ ] ECS cluster is properly configured
- [ ] ECS service is running
- [ ] IAM roles have proper permissions
- [ ] SNS topic for notifications exists
- [ ] CloudWatch agent is installed on container instances

## Service Metrics Collection
- [ ] CPU Utilization
  - [ ] Service-level monitoring
  - [ ] Task-level monitoring
- [ ] Memory Utilization
  - [ ] Service-level monitoring
  - [ ] Task-level monitoring
- [ ] Container Instance metrics
  - [ ] CPU
  - [ ] Memory
  - [ ] Disk
  - [ ] Network

## Alarms Configuration
- [ ] CPU Utilization alarms
  - [ ] High CPU (configurable threshold)
  - [ ] Critical CPU (configurable threshold)
- [ ] Memory Utilization alarms
  - [ ] High Memory (configurable threshold)
  - [ ] Critical Memory (configurable threshold)
- [ ] Task health alarms
  - [ ] Unhealthy task count
  - [ ] Failed task count

## Event Monitoring
- [ ] Service scaling events
- [ ] Task state changes
- [ ] Container instance state changes
- [ ] Service deployment events
- [ ] Task placement failures

## Notification Configuration
- [ ] Alarm notifications
- [ ] Scaling notifications
- [ ] Task health notifications
- [ ] Service deployment notifications

## Verification Steps
1. Verify metrics are being collected
2. Test alarm triggers
3. Verify notifications
4. Check event monitoring
5. Verify service health
6. Test scaling events
7. Verify task placement

## Configuration Parameters
- CPU threshold (default: 80%)
- Memory threshold (default: 80%)
- Evaluation periods (default: 2)
- Period (default: 300 seconds)
- Alarm actions (SNS topic ARN) 