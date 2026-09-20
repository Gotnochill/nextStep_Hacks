#!/usr/bin/env python3
"""Delete only resources tagged Project=ember-waste-seed."""

from __future__ import annotations

import argparse

import boto3
from botocore.exceptions import ClientError

PROJECT = "ember-waste-seed"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--region", default="us-east-1")
    args = parser.parse_args()
    ec2 = boto3.client("ec2", region_name=args.region)
    filt = [{"Name": "tag:Project", "Values": [PROJECT]}]

    instance_ids = []
    for page in ec2.get_paginator("describe_instances").paginate(Filters=filt):
        for res in page.get("Reservations", []):
            for inst in res.get("Instances", []):
                state = inst.get("State", {}).get("Name")
                if state not in ("terminated", "shutting-down"):
                    instance_ids.append(inst["InstanceId"])
    if instance_ids:
        print("terminating", instance_ids)
        ec2.terminate_instances(InstanceIds=instance_ids)
        waiter = ec2.get_waiter("instance_terminated")
        waiter.wait(InstanceIds=instance_ids)

    vol_ids = [v["VolumeId"] for v in ec2.describe_volumes(Filters=filt).get("Volumes", [])]
    for vid in vol_ids:
        print("deleting volume", vid)
        try:
            ec2.delete_volume(VolumeId=vid)
        except ClientError as exc:
            print("  skip", vid, exc)

    eips = ec2.describe_addresses(Filters=filt).get("Addresses", [])
    for addr in eips:
        alloc = addr["AllocationId"]
        print("releasing EIP", alloc)
        ec2.release_address(AllocationId=alloc)

    print("Teardown complete.")


if __name__ == "__main__":
    main()
