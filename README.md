# Ember — Cloud Waste Finder

**Live app:** [https://gotnochill.github.io/nextStep_Hacks/](https://gotnochill.github.io/nextStep_Hacks/)

Data centers already use a growing share of the world’s electricity. A lot of that is idle cloud: instances nobody shut down, forgotten dev boxes, unattached disks, leftover IPs and NAT gateways that still bill and still draw power.

Ember scans an AWS account for that waste and shows what you get back by removing it — **dollars, kilowatt-hours, and kg of CO₂**. The scan uses the account’s own APIs (boto3 and CloudWatch). Carbon figures are estimates from published energy coefficients, not per-instance meters from AWS.

Click **Sample ledger** on the live app to see a full findings report.
