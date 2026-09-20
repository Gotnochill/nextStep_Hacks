#!/usr/bin/env python3
"""Seed a throwaway AWS account with deliberately wasteful resources for the demo.

Creates:
  - idle t3.micro tagged as a forgotten dev box
  - oversized m5.large (will look idle after a few minutes)
  - unattached 50 GB gp3 volume
  - unassociated Elastic IP

All resources are tagged Project=ember-waste-seed so teardown_waste.py can
delete only what this script created.

Usage (from repo root, with AWS credentials configured):
  python scripts/seed_waste.py --region us-east-1
"""

from __future__ import annotations

import argparse
import json
import time

import boto3
from botocore.exceptions import ClientError

PROJECT = "ember-waste-seed"
TAGS = [
    {"Key": "Project", "Value": PROJECT},
    {"Key": "Keep", "Value": "false"},
    {"Key": "CreatedBy", "Value": "ember-seed"},
]


def tag_spec(resource_type: str, extra: list[dict] | None = None):
    return [{"ResourceType": resource_type, "Tags": TAGS + (extra or [])}]


def latest_al2023(ec2) -> str:
    ssm = boto3.client("ssm", region_name=ec2.meta.region_name)
    param = ssm.get_parameter(Name="/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64")
    return param["Parameter"]["Value"]


def default_subnet(ec2) -> str:
    vpcs = ec2.describe_vpcs(Filters=[{"Name": "isDefault", "Values": ["true"]}]).get("Vpcs", [])
    if not vpcs:
        raise SystemExit("No default VPC in this region. Pick another region or create a default VPC.")
    vpc_id = vpcs[0]["VpcId"]
    subnets = ec2.describe_subnets(Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]).get("Subnets", [])
    if not subnets:
        raise SystemExit("Default VPC has no subnets.")
    return subnets[0]["SubnetId"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--region", default="us-east-1")
    args = parser.parse_args()

    ec2 = boto3.client("ec2", region_name=args.region)
    ami = latest_al2023(ec2)
    subnet = default_subnet(ec2)
    created: dict = {"region": args.region, "instances": [], "volumes": [], "eips": []}

    print(f"Seeding waste in {args.region} (AMI {ami})")

    dev = ec2.run_instances(
        ImageId=ami,
        InstanceType="t3.micro",
        MinCount=1,
        MaxCount=1,
        SubnetId=subnet,
        TagSpecifications=tag_spec(
            "instance",
            [{"Key": "Name", "Value": "dev-api-joshua"}, {"Key": "Environment", "Value": "dev"}],
        ),
    )["Instances"][0]
    created["instances"].append(dev["InstanceId"])
    print(f"  launched forgotten dev  {dev['InstanceId']}  t3.micro")

    fat = ec2.run_instances(
        ImageId=ami,
        InstanceType="m5.large",
        MinCount=1,
        MaxCount=1,
        SubnetId=subnet,
        TagSpecifications=tag_spec(
            "instance",
            [{"Key": "Name", "Value": "analytics-worker-OLD"}, {"Key": "Environment", "Value": "legacy"}],
        ),
    )["Instances"][0]
    created["instances"].append(fat["InstanceId"])
    print(f"  launched oversized idle {fat['InstanceId']}  m5.large")

    vol = ec2.create_volume(
        AvailabilityZone=ec2.describe_subnets(SubnetIds=[subnet])["Subnets"][0]["AvailabilityZone"],
        Size=50,
        VolumeType="gp3",
        TagSpecifications=tag_spec("volume", [{"Key": "Name", "Value": "backup-restore-tmp"}]),
    )
    created["volumes"].append(vol["VolumeId"])
    print(f"  unattached volume       {vol['VolumeId']}  50 GB gp3")

    alloc = ec2.allocate_address(Domain="vpc", TagSpecifications=tag_spec("elastic-ip"))
    created["eips"].append(alloc["AllocationId"])
    print(f"  unused Elastic IP       {alloc['AllocationId']}  {alloc.get('PublicIp')}")

    stamp = f"scripts/.ember-seed-{args.region}.json"
    with open(stamp, "w", encoding="utf-8") as fh:
        json.dump(created, fh, indent=2)

    print("\nWaiting 20s for instances to enter running...")
    time.sleep(20)
    print("Seed complete.")
    print("CloudWatch CPU needs ~5–15 minutes before idle looks obvious.")
    print("Teardown:  python scripts/teardown_waste.py --region", args.region)
    print("Manifest:", stamp)


if __name__ == "__main__":
    try:
        main()
    except ClientError as exc:
        raise SystemExit(f"AWS error: {exc}") from exc
