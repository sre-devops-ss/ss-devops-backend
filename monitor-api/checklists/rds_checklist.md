# RDS Instance Monitoring Checklist

## Prerequisites
- [ ] RDS instance is properly configured
- [ ] IAM role has CloudWatch permissions
- [ ] SNS topic for notifications exists
- [ ] Security groups are properly configured

## Instance Metrics Collection
- [ ] CPU Utilization
  - [ ] Writer instance monitoring
  - [ ] Reader instance monitoring
- [ ] Freeable Memory
- [ ] DB Connections
- [ ] Connection Attempts
- [ ] Deadlocks
- [ ] Queries
- [ ] Free Local Storage
- [ ] Read/Write IOPS
- [ ] Read/Write Latency
- [ ] Network Throughput

## Instance Events Monitoring
- [ ] Failover Events
- [ ] Master Password Reset
- [ ] Security Group Modifications
- [ ] Instance Reboots
- [ ] Scaling Events
- [ ] Maintenance Events
- [ ] Backup Events

## Alarms Configuration
- [ ] CPU Utilization alarms
  - [ ] High CPU (threshold: 80%)
  - [ ] Critical CPU (threshold: 90%)
- [ ] Memory alarms
  - [ ] Low Freeable Memory (threshold: 1GB)
  - [ ] Critical Memory (threshold: 500MB)
- [ ] Connection alarms
  - [ ] High Connection Count (threshold: 80% of max)
  - [ ] Connection Attempt Failures
- [ ] Storage alarms
  - [ ] Low Free Storage (threshold: 10GB)
  - [ ] Critical Storage (threshold: 5GB)
- [ ] Performance alarms
  - [ ] High Deadlock Count
  - [ ] High Query Latency
  - [ ] High IOPS

## Event Notifications
- [ ] Failover notifications
- [ ] Password reset notifications
- [ ] Security group modification alerts
- [ ] Reboot notifications
- [ ] Scaling notifications
- [ ] Maintenance notifications

## Verification Steps
1. Verify metrics are being collected
2. Test alarm triggers
3. Verify notifications
4. Check event monitoring
5. Verify instance health
6. Test failover scenarios
7. Verify backup monitoring 