# NAT Gateway Monitoring Checklist

## Prerequisites
- [ ] NAT Gateway is deployed and configured
- [ ] IAM roles have necessary permissions
- [ ] SNS topic exists for notifications
- [ ] CloudWatch is enabled for the NAT Gateway

## Metrics Collection
### Performance Metrics
- [ ] PacketsDropCount
  - [ ] Packet drops tracked
  - [ ] Drop patterns identified
  - [ ] Drop thresholds defined

### Network Metrics
- [ ] ActiveConnectionCount
- [ ] BytesInFromDestination
- [ ] BytesInFromSource
- [ ] BytesOutToDestination
- [ ] BytesOutToSource
- [ ] PacketDropCount

## Alarms Configuration
### Performance Alarms
- [ ] PacketsDropCount Alarm
  - [ ] Threshold: 100 packets per 5 minutes
  - [ ] Evaluation Period: 2 periods
  - [ ] Statistic: Sum

### Network Alarms
- [ ] ActiveConnectionCount Alarm
  - [ ] Threshold: 80% of maximum connections
  - [ ] Evaluation Period: 2 periods
  - [ ] Statistic: Average

## Notification Configuration
- [ ] Alarm Notifications
  - [ ] SNS topic configured
  - [ ] Email notifications enabled
  - [ ] Slack/Teams integration (if needed)

## Verification Steps
1. Metrics Verification
   - [ ] Verify packet drops are being collected
   - [ ] Verify connection counts are being collected
   - [ ] Verify byte counts are being collected
   - [ ] Check metric granularity (1-minute intervals)

2. Alarm Verification
   - [ ] Test packet drop alarm
   - [ ] Test connection count alarm
   - [ ] Verify alarm notifications

3. Network Testing
   - [ ] Test NAT Gateway connectivity
   - [ ] Verify packet forwarding
   - [ ] Check bandwidth utilization
   - [ ] Verify connection limits

## Configuration Parameters
```json
{
    "packets_drop_threshold": 100,
    "evaluation_periods": 2,
    "period": 300,
    "alarm_actions": [
        "arn:aws:sns:region:account:monitoring-alerts"
    ]
}
```

## Monitoring Best Practices
1. Network Performance
   - [ ] Monitor bandwidth utilization
   - [ ] Track connection limits
   - [ ] Set up packet drop alerts

2. Security
   - [ ] Monitor unauthorized access attempts
   - [ ] Track connection patterns
   - [ ] Set up security group monitoring

3. High Availability
   - [ ] Monitor NAT Gateway status
   - [ ] Track failover events
   - [ ] Set up availability zone monitoring

4. Documentation
   - [ ] Network architecture documented
   - [ ] Monitoring setup documented
   - [ ] Runbooks created for common issues 