# Ember — Cloud Waste Finder

Hackathon project for **Earth Forward**: data centers already consume on the order of 1–2% of global electricity, and a large slice of cloud capacity sits idle. Ember scans an AWS account for that waste and translates it into dollars, kilowatt-hours, and kilograms of CO₂.

No third-party API keys. The scan uses **boto3** and **CloudWatch** against the account you provide.

## Live app

Public UI: **https://gotnochill.github.io/nextStep_Hacks/**

Judges can open that link on any PC. **Sample ledger (no AWS)** works there immediately.

**Scan the live AWS account** needs the Python API plus a throwaway AWS user. The app is Docker-ready for that. This GitHub account’s previous Railway trial is expired, so the live boto3 endpoint is not on the public internet until a host plan is active (Railway Hobby, Render, or Fly) and these env vars are set on the host — never in git:

- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_DEFAULT_REGION=us-east-1`

Until then, clone this repo and run Quick start locally with your own read-only keys.

### Submission

- **Video** — screen-record: landing pitch → sample or live scan → dollars / kWh / kg CO₂. Keep it under 5 minutes.
- **Repository** — https://github.com/Gotnochill/nextStep_Hacks
- **Live website** — https://gotnochill.github.io/nextStep_Hacks/

## What it finds

- Idle EC2 (low CPU + quiet network over the lookback window)
- Oversized instances (low CPU on a machine you can downsize)
- Forgotten dev / test / sandbox environments (name + tags)
- Unattached EBS volumes
- Unassociated Elastic IPs
- Idle NAT gateways (still ~$32/month with no traffic)

Each finding carries **$/month**, **kWh**, and **kg CO₂e**, with annual rollups and everyday equivalents (miles driven, phone charges, trees).

## Quick start

You need Python 3.11+ and Node 18+.

```bash
# backend
cd backend
python -m venv .venv
source .venv/Scripts/activate   # Windows Git Bash
# source .venv/bin/activate     # macOS / Linux
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

```bash
# frontend (second terminal)
cd frontend
npm install
npm run dev
```

Open [http://127.0.0.1:5173](http://127.0.0.1:5173). Click **Sample ledger (no AWS)** for a pitch-ready dataset with no AWS account. Click **Scan an AWS account** for a live read of keys on your machine.

Leave access keys blank to use the default credential chain (`AWS_ACCESS_KEY_ID`, `~/.aws/credentials`, or SSO). Optional: copy `.env.example` to `.env`.

CLI:

```bash
cd backend
python -m app.cli --demo
python -m app.cli --region us-east-1 --lookback-days 7
```

## Live demo against a throwaway account

This **creates billable resources**. Use a throwaway account, then tear down.

```bash
pip install boto3   # if you are not already in the backend venv
python scripts/seed_waste.py --region us-east-1
```

Wait 10–15 minutes so CloudWatch has CPU samples, then scan `us-east-1` with lookback 1–7 days.

```bash
python scripts/teardown_waste.py --region us-east-1
```

The seed script only tags `Project=ember-waste-seed`. Teardown deletes those tags only.

To power **Scan the live AWS account** on the public site, put a **read-only** IAM user from that same throwaway account into the host as:

- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_DEFAULT_REGION=us-east-1`

Never commit those values. Seed the account first, wait for CloudWatch, then the public button will return real findings.

### IAM (read-only)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "sts:GetCallerIdentity",
        "ec2:DescribeInstances",
        "ec2:DescribeVolumes",
        "ec2:DescribeAddresses",
        "ec2:DescribeNatGateways",
        "cloudwatch:GetMetricData"
      ],
      "Resource": "*"
    }
  ]
}
```

Seed/teardown need `ec2:RunInstances`, `ec2:CreateVolume`, `ec2:AllocateAddress`, `ec2:CreateTags`, `ec2:TerminateInstances`, `ec2:DeleteVolume`, `ec2:ReleaseAddress`, `ssm:GetParameter`.

## Carbon methodology (say this in the pitch)

AWS does not publish watts per instance. Ember estimates, using [Cloud Carbon Footprint](https://www.cloudcarbonfootprint.org/docs/methodology/) coefficients:

1. CPU watts interpolated between **0.74 W/vCPU** (idle) and **3.5 W/vCPU** (full)
2. Memory **0.392 W/GB**
3. EBS SSD **1.2 Wh per TB-hour**, replication factor 2
4. AWS **PUE 1.135**
5. Regional grid intensity (EPA eGRID / CCF), e.g. `us-east-1` ≈ **416 g CO₂e/kWh**

Label the numbers as **estimates**. Dollar amounts use public on-demand list prices.

## Pitch spine

1. Data centers are a growing electricity and water load. Idle cloud is the most pointless part of that load.
2. Teams leave GPUs, “just for a minute” dev boxes, and NAT gateways running. The planet and the bill both stay on.
3. Ember is a read-only scan of *your* account. No extra vendors.
4. Show the demo ledger: one forgotten `g4dn.xlarge` plus an `m5.4xlarge` already looks like real money and real carbon.
5. Close: the greenest server is the one you turn off.

## Project layout

```
backend/app/     FastAPI + scanner + carbon model
frontend/       Vite + React dashboard
scripts/        seed + teardown for a throwaway account
```
