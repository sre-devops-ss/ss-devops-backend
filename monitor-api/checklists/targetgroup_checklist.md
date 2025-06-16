# Target Group Monitoring Checklist

## Prerequisites
- [ ] Target Group is properly configured
- [ ] Load Balancer is attached
- [ ] Health check settings are configured
- [ ] SNS topic for notifications exists

## Metrics Collection
- [ ] Target Response Time
- [ ] Request Count
- [ ] Healthy Host Count
- [ ] Unhealthy Host Count
- [ ] 5XX Error Count
- [ ] 4XX Error Count
- [ ] Target Connection Error Count
- [ ] Target TLS Negotiation Error Count

## Alarms Configuration
- [ ] High Response Time alarm (threshold: 5 seconds)
- [ ] High Error Rate alarm (threshold: 5%)
- [ ] Unhealthy Host alarm (threshold: 1)
- [ ] Connection Error alarm
- [ ] TLS Error alarm
- [ ] Alarm actions configured (SNS topic)

## Health Check Monitoring
- [ ] Health check status monitoring
- [ ] Health check failure notifications
- [ ] Target deregistration monitoring
- [ ] Target registration monitoring

## Load Balancer Integration
- [ ] Load Balancer metrics collection
- [ ] Load Balancer error monitoring
- [ ] Load Balancer latency monitoring

## Verification Steps
1. Verify Target Group configuration
2. Check health check settings
3. Verify metrics are being collected
4. Test alarm triggers
5. Verify notifications
6. Check target health status
7. Verify load balancer integration 