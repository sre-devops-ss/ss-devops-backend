# Cost Overview: Monitoring Solution

## Amazon Keyspaces (Cassandra)

**Pricing Model:**
- Amazon Keyspaces is serverless and charges based on reads, writes, and storage.
- [Official Pricing](https://aws.amazon.com/keyspaces/pricing/)

**Typical Costs:**
- **Write request unit (WRU):** $1.45 per million WRUs
- **Read request unit (RRU):** $0.47 per million RRUs
- **Storage:** $0.30 per GB-month
- **Backup storage:** $0.095 per GB-month

**Example (light usage):**
- 10 million writes/month: $14.50
- 10 million reads/month: $4.70
- 10 GB storage: $3.00
- **Total:** ~$22.20/month (plus backup)

**Example (heavy usage):**
- 100 million writes/month: $145
- 100 million reads/month: $47
- 100 GB storage: $30
- **Total:** ~$222/month (plus backup)

---

## AWS Lambda (per function)

**Pricing Model:**
- Charged by number of requests and compute time (GB-seconds)
- [Official Pricing](https://aws.amazon.com/lambda/pricing/)

**Typical Costs:**
- **Requests:** First 1M/month free, then $0.20 per 1M requests
- **Duration:** $0.00001667 per GB-second
- **Example function:** 256MB, 1s duration, 1M invocations/month
  - Compute: 0.25GB * 1s * 1M = 250,000 GB-s = $4.17
  - Requests: Free (first 1M)
  - **Total:** ~$4.17/month per function

**Heavy usage example:**
- 256MB, 1s, 10M invocations/month
  - Compute: $41.70
  - Requests: $1.80
  - **Total:** ~$43.50/month per function

---

## Other AWS Costs
- **API Gateway:** $3.50 per million API calls (plus data transfer)
- **CloudWatch Alarms:** $0.10 per alarm/month
- **SNS Notifications:** $0.50 per million publishes

---

## Notes
- All prices are for us-east-1 and may vary by region.
- Actual costs depend on usage patterns.
- Use the [AWS Pricing Calculator](https://calculator.aws.amazon.com/) for precise estimates. 