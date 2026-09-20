from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from .carbon import METHODOLOGY, compute_monthly_kwh, ebs_monthly_kwh, equivalents, kwh_to_kg, nat_monthly_kwh
from .catalog import downsized_type, spec_for
from .demo import _counts, _finding, _totals
from .models import Finding, FindingType, ScanRequest, ScanResult, Severity
from .pricing import ebs_monthly_usd, eip_monthly_usd, instance_monthly_usd, nat_monthly_usd

log = logging.getLogger("ember.scanner")

DEV_HINTS = ("dev", "test", "staging", "sandbox", "qa", "demo", "tmp", "temp", "experiment")
BOTO_CONFIG = Config(retries={"max_attempts": 4, "mode": "standard"})


def _session(req: ScanRequest):
    kwargs: dict[str, Any] = {"region_name": req.region}
    if req.aws_access_key_id and req.aws_secret_access_key:
        kwargs["aws_access_key_id"] = req.aws_access_key_id
        kwargs["aws_secret_access_key"] = req.aws_secret_access_key
        if req.aws_session_token:
            kwargs["aws_session_token"] = req.aws_session_token
    return boto3.Session(**kwargs)


def _name_from_tags(tags: list[dict] | None) -> str:
    for tag in tags or []:
        if tag.get("Key") == "Name":
            return str(tag.get("Value") or "")
    return ""


def _tag_map(tags: list[dict] | None) -> dict[str, str]:
    return {t.get("Key", ""): t.get("Value", "") for t in (tags or [])}


def _looks_like_dev(name: str, tags: dict[str, str]) -> bool:
    blob = " ".join([name, *tags.keys(), *tags.values()]).lower()
    return any(h in blob for h in DEV_HINTS)


def _age_days(when: datetime | None) -> int | None:
    if not when:
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    return max(0, (datetime.now(timezone.utc) - when).days)


def _severity_compute(monthly_cost: float, primary: FindingType) -> Severity:
    if primary in ("idle_nat",) and monthly_cost >= 20:
        return "high"
    if monthly_cost >= 200:
        return "critical"
    if monthly_cost >= 50:
        return "high"
    if monthly_cost >= 15:
        return "medium"
    return "low"


def _chunk(items: list[str], size: int) -> list[list[str]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def _metric_averages(
    cloudwatch, namespace: str, metric_name: str, dim_name: str, ids: list[str], days: int, stat: str = "Average"
) -> dict[str, float | None]:
    if not ids:
        return {}
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    out: dict[str, float | None] = {i: None for i in ids}
    period = 3600
    for group_i, group in enumerate(_chunk(ids, 40)):
        queries = []
        for j, rid in enumerate(group):
            queries.append(
                {
                    "Id": f"m{group_i}_{j}",
                    "MetricStat": {
                        "Metric": {
                            "Namespace": namespace,
                            "MetricName": metric_name,
                            "Dimensions": [{"Name": dim_name, "Value": rid}],
                        },
                        "Period": period,
                        "Stat": stat,
                    },
                    "ReturnData": True,
                }
            )
        try:
            resp = cloudwatch.get_metric_data(
                MetricDataQueries=queries,
                StartTime=start,
                EndTime=end,
                ScanBy="TimestampAscending",
            )
        except (ClientError, BotoCoreError) as exc:
            log.warning("CloudWatch %s/%s failed: %s", namespace, metric_name, exc)
            continue
        for result in resp.get("MetricDataResults", []):
            idx = result["Id"].split("_")[-1]
            try:
                rid = group[int(idx)]
            except (ValueError, IndexError):
                continue
            values = result.get("Values") or []
            if values:
                out[rid] = sum(values) / len(values)
    return out


def live_scan(req: ScanRequest) -> ScanResult:
    session = _session(req)
    sts = session.client("sts", config=BOTO_CONFIG)
    try:
        account_id = sts.get_caller_identity()["Account"]
    except (ClientError, BotoCoreError) as exc:
        raise PermissionError(f"Could not authenticate with AWS: {exc}") from exc

    ec2 = session.client("ec2", config=BOTO_CONFIG)
    cloudwatch = session.client("cloudwatch", config=BOTO_CONFIG)
    findings: list[Finding] = []
    region = req.region
    days = req.lookback_days
    idle_cpu = req.cpu_idle_threshold

    instances = _running_instances(ec2)
    instance_ids = [i["InstanceId"] for i in instances]
    cpu = _metric_averages(cloudwatch, "AWS/EC2", "CPUUtilization", "InstanceId", instance_ids, days)
    net_in = _metric_averages(cloudwatch, "AWS/EC2", "NetworkIn", "InstanceId", instance_ids, days, stat="Sum")

    for inst in instances:
        iid = inst["InstanceId"]
        itype = inst.get("InstanceType") or "t3.micro"
        tags = _tag_map(inst.get("Tags"))
        name = tags.get("Name") or iid
        avg_cpu = cpu.get(iid)
        avg_net = net_in.get(iid)
        age = _age_days(inst.get("LaunchTime"))
        cpu_val = avg_cpu if avg_cpu is not None else 0.0
        net_quiet = avg_net is None or avg_net < 80_000
        is_idle = cpu_val < idle_cpu and net_quiet
        is_dev = _looks_like_dev(name, tags)
        spec = spec_for(itype)
        is_oversized = cpu_val < 12.0 and spec.vcpu >= 4 and downsized_type(itype)

        types: list[FindingType] = []
        if is_dev and (is_idle or (age or 0) >= 7):
            types.append("forgotten_dev")
        if is_idle:
            types.append("idle_instance")
        if is_oversized and not is_idle:
            types.append("oversized_instance")
        if not types:
            continue

        primary: FindingType = types[0]
        if primary == "oversized_instance":
            smaller = downsized_type(itype) or itype
            monthly_cost = instance_monthly_usd(itype) - instance_monthly_usd(smaller)
            kwh = max(
                compute_monthly_kwh(itype, cpu_val) - compute_monthly_kwh(smaller, min(cpu_val * 2, 40)),
                0,
            )
            rec = f"Downsize {itype} → {smaller}. CPU averaged {cpu_val:.1f}% over {days} days."
        else:
            monthly_cost = instance_monthly_usd(itype)
            kwh = compute_monthly_kwh(itype, cpu_val)
            rec = (
                "Stop or terminate this instance. It is burning energy with almost no work."
                if is_idle
                else "This looks like a forgotten environment. Shut it down or put it on a schedule."
            )

        kg = kwh_to_kg(kwh, region)
        findings.append(
            _finding(
                id=iid,
                primary_type=primary,
                types=types,
                severity=_severity_compute(monthly_cost, primary),
                resource_id=iid,
                resource_name=name,
                resource_kind="EC2",
                instance_type=itype,
                region=region,
                monthly_cost_usd=monthly_cost,
                monthly_kwh=kwh,
                monthly_kg_co2=kg,
                recommendation=rec,
                evidence={
                    "avg_cpu_percent": None if avg_cpu is None else round(cpu_val, 2),
                    "avg_network_bytes_per_hour": None if avg_net is None else round(avg_net, 0),
                    "lookback_days": days,
                    "age_days": age,
                    "tags": tags,
                    "state": inst.get("State", {}).get("Name"),
                    "metrics_missing": avg_cpu is None,
                    "suggested_type": downsized_type(itype) if "oversized_instance" in types else None,
                },
            )
        )

    findings.extend(_scan_volumes(ec2, region))
    findings.extend(_scan_eips(ec2, region))
    findings.extend(_scan_nats(ec2, cloudwatch, region, days))

    findings.sort(key=lambda f: f.monthly_cost_usd, reverse=True)
    return ScanResult(
        scanned_at=datetime.now(timezone.utc).isoformat(),
        region=region,
        account_id=account_id,
        mode="live",
        lookback_days=days,
        totals=_totals(findings),
        counts=_counts(findings),
        findings=findings,
        methodology=METHODOLOGY,
    )


def _running_instances(ec2) -> list[dict]:
    paginator = ec2.get_paginator("describe_instances")
    out: list[dict] = []
    for page in paginator.paginate(
        Filters=[{"Name": "instance-state-name", "Values": ["running"]}]
    ):
        for res in page.get("Reservations", []):
            out.extend(res.get("Instances", []))
    return out


def _scan_volumes(ec2, region: str) -> list[Finding]:
    findings: list[Finding] = []
    paginator = ec2.get_paginator("describe_volumes")
    for page in paginator.paginate(Filters=[{"Name": "status", "Values": ["available"]}]):
        for vol in page.get("Volumes", []):
            size = float(vol.get("Size") or 0)
            vtype = vol.get("VolumeType") or "gp3"
            tags = _tag_map(vol.get("Tags"))
            name = tags.get("Name") or vol["VolumeId"]
            kwh = ebs_monthly_kwh(size)
            cost = ebs_monthly_usd(size, vtype)
            findings.append(
                _finding(
                    id=vol["VolumeId"],
                    primary_type="unattached_volume",
                    types=["unattached_volume"],
                    severity=_severity_compute(cost, "unattached_volume"),
                    resource_id=vol["VolumeId"],
                    resource_name=name,
                    resource_kind="EBS",
                    instance_type=None,
                    region=region,
                    monthly_cost_usd=cost,
                    monthly_kwh=kwh,
                    monthly_kg_co2=kwh_to_kg(kwh, region),
                    recommendation="Snapshot if needed, then delete this unattached volume.",
                    evidence={
                        "size_gb": size,
                        "volume_type": vtype,
                        "state": vol.get("State"),
                        "age_days": _age_days(vol.get("CreateTime")),
                        "tags": tags,
                    },
                )
            )
    return findings


def _scan_eips(ec2, region: str) -> list[Finding]:
    findings: list[Finding] = []
    addrs = ec2.describe_addresses().get("Addresses", [])
    cost = eip_monthly_usd()
    for addr in addrs:
        if addr.get("AssociationId") or addr.get("InstanceId") or addr.get("NetworkInterfaceId"):
            continue
        alloc = addr.get("AllocationId") or addr.get("PublicIp")
        public_ip = addr.get("PublicIp") or alloc
        findings.append(
            _finding(
                id=str(alloc),
                primary_type="unused_eip",
                types=["unused_eip"],
                severity="low",
                resource_id=str(alloc),
                resource_name=str(public_ip),
                resource_kind="Elastic IP",
                instance_type=None,
                region=region,
                monthly_cost_usd=cost,
                monthly_kwh=0,
                monthly_kg_co2=0,
                recommendation="Release this unassociated Elastic IP. Idle public IPv4 is billed hourly.",
                evidence={"public_ip": public_ip, "associated": False},
            )
        )
    return findings


def _scan_nats(ec2, cloudwatch, region: str, days: int) -> list[Finding]:
    findings: list[Finding] = []
    try:
        nats = []
        paginator = ec2.get_paginator("describe_nat_gateways")
        for page in paginator.paginate(
            Filter=[{"Name": "state", "Values": ["available"]}]
        ):
            nats.extend(page.get("NatGateways", []))
    except ClientError as exc:
        log.warning("NAT describe failed: %s", exc)
        return findings

    ids = [n["NatGatewayId"] for n in nats]
    bytes_out = _metric_averages(
        cloudwatch, "AWS/NATGateway", "BytesOutToDestination", "NatGatewayId", ids, days, stat="Sum"
    )
    cost = nat_monthly_usd()
    kwh = nat_monthly_kwh()
    for nat in nats:
        nid = nat["NatGatewayId"]
        traffic = bytes_out.get(nid)
        # Idle if we saw almost no egress, or no metrics on a NAT that has been up a while.
        quiet = traffic is None or traffic < 1_000_000
        if not quiet:
            continue
        tags = _tag_map(nat.get("Tags"))
        name = tags.get("Name") or nid
        findings.append(
            _finding(
                id=nid,
                primary_type="idle_nat",
                types=["idle_nat"],
                severity=_severity_compute(cost, "idle_nat"),
                resource_id=nid,
                resource_name=name,
                resource_kind="NAT Gateway",
                instance_type=None,
                region=region,
                monthly_cost_usd=cost,
                monthly_kwh=kwh,
                monthly_kg_co2=kwh_to_kg(kwh, region),
                recommendation="NAT gateways cost ~$32/month even with no traffic. Delete if unused.",
                evidence={
                    "bytes_out_lookback": None if traffic is None else round(traffic, 0),
                    "lookback_days": days,
                    "age_days": _age_days(nat.get("CreateTime")),
                    "state": nat.get("State"),
                    "tags": tags,
                },
            )
        )
    return findings
