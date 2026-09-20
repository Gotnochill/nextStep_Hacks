from __future__ import annotations

from datetime import datetime, timezone

from .carbon import METHODOLOGY, compute_monthly_kwh, ebs_monthly_kwh, equivalents, kwh_to_kg, nat_monthly_kwh
from .catalog import HOURS_PER_MONTH, downsized_type
from .models import Counts, Equivalents, Finding, ScanResult, Totals
from .pricing import ebs_monthly_usd, eip_monthly_usd, instance_monthly_usd, nat_monthly_usd


def _totals(findings: list[Finding]) -> Totals:
    monthly_cost = sum(f.monthly_cost_usd for f in findings)
    monthly_kwh = sum(f.monthly_kwh for f in findings)
    monthly_kg = sum(f.monthly_kg_co2 for f in findings)
    annual_kwh = monthly_kwh * 12
    annual_kg = monthly_kg * 12
    eq = equivalents(annual_kg, annual_kwh)
    return Totals(
        monthly_cost_usd=round(monthly_cost, 2),
        annual_cost_usd=round(monthly_cost * 12, 2),
        monthly_kwh=round(monthly_kwh, 2),
        annual_kwh=round(annual_kwh, 2),
        monthly_kg_co2=round(monthly_kg, 2),
        annual_kg_co2=round(annual_kg, 2),
        equivalents=Equivalents(
            miles_driven=round(eq["miles_driven"], 1),
            phones_charged=round(eq["phones_charged"], 0),
            trees_to_offset_year=round(eq["trees_to_offset_year"], 2),
        ),
    )


def _counts(findings: list[Finding]) -> Counts:
    c = Counts(total=len(findings))
    for f in findings:
        if f.primary_type == "idle_instance":
            c.idle_instances += 1
        elif f.primary_type == "oversized_instance":
            c.oversized_instances += 1
        elif f.primary_type == "forgotten_dev":
            c.forgotten_dev += 1
        elif f.primary_type == "unattached_volume":
            c.unattached_volumes += 1
        elif f.primary_type == "unused_eip":
            c.unused_eips += 1
        elif f.primary_type == "idle_nat":
            c.idle_nats += 1
    return c


def _finding(**kwargs) -> Finding:
    monthly_cost = kwargs.pop("monthly_cost_usd")
    monthly_kwh = kwargs.pop("monthly_kwh")
    monthly_kg = kwargs.pop("monthly_kg_co2")
    return Finding(
        monthly_cost_usd=round(monthly_cost, 2),
        annual_cost_usd=round(monthly_cost * 12, 2),
        monthly_kwh=round(monthly_kwh, 3),
        monthly_kg_co2=round(monthly_kg, 3),
        annual_kg_co2=round(monthly_kg * 12, 2),
        **kwargs,
    )


def demo_scan(region: str = "us-east-1", lookback_days: int = 7) -> ScanResult:
    """A messy mid-size account: forgotten GPU experiment, idle NAT, leftover disks."""
    m54_kwh = compute_monthly_kwh("m5.4xlarge", cpu_percent=1.4)
    m54_kg = kwh_to_kg(m54_kwh, region)
    g4_kwh = compute_monthly_kwh("g4dn.xlarge", cpu_percent=0.6)
    g4_kg = kwh_to_kg(g4_kwh, region)
    t3_kwh = compute_monthly_kwh("t3.large", cpu_percent=2.1)
    t3_kg = kwh_to_kg(t3_kwh, region)
    r5_full = instance_monthly_usd("r5.xlarge")
    r5_down = instance_monthly_usd(downsized_type("r5.xlarge") or "r5.large")
    r5_delta = r5_full - r5_down
    r5_kwh_full = compute_monthly_kwh("r5.xlarge", cpu_percent=8.4)
    r5_kwh_down = compute_monthly_kwh("r5.large", cpu_percent=16.8)
    r5_kwh = max(r5_kwh_full - r5_kwh_down, 0)
    r5_kg = kwh_to_kg(r5_kwh, region)
    vol_kwh = ebs_monthly_kwh(200)
    vol2_kwh = ebs_monthly_kwh(80)
    nat_kwh = nat_monthly_kwh()

    findings = [
        _finding(
            id="demo-gpu",
            primary_type="forgotten_dev",
            types=["forgotten_dev", "idle_instance"],
            severity="critical",
            resource_id="i-0a1b2c3d4e5f67890",
            resource_name="ml-experiment-march",
            resource_kind="EC2",
            instance_type="g4dn.xlarge",
            region=region,
            monthly_cost_usd=instance_monthly_usd("g4dn.xlarge"),
            monthly_kwh=g4_kwh,
            monthly_kg_co2=g4_kg,
            recommendation="Terminate this forgotten GPU box. It has been idle since the hack-week experiment.",
            evidence={
                "avg_cpu_percent": 0.6,
                "avg_network_bytes_per_hour": 12000,
                "lookback_days": lookback_days,
                "age_days": 47,
                "tags": {"Name": "ml-experiment-march", "Environment": "dev", "Owner": "intern-2019"},
                "state": "running",
            },
        ),
        _finding(
            id="demo-m5",
            primary_type="idle_instance",
            types=["idle_instance", "oversized_instance"],
            severity="critical",
            resource_id="i-0f9e8d7c6b5a43210",
            resource_name="analytics-worker-OLD",
            resource_kind="EC2",
            instance_type="m5.4xlarge",
            region=region,
            monthly_cost_usd=instance_monthly_usd("m5.4xlarge"),
            monthly_kwh=m54_kwh,
            monthly_kg_co2=m54_kg,
            recommendation="Stop or terminate. Average CPU is under 2% — this is a 16-vCPU machine doing nothing.",
            evidence={
                "avg_cpu_percent": 1.4,
                "avg_network_bytes_per_hour": 8400,
                "lookback_days": lookback_days,
                "age_days": 86,
                "tags": {"Name": "analytics-worker-OLD", "Project": "legacy"},
                "state": "running",
            },
        ),
        _finding(
            id="demo-dev",
            primary_type="forgotten_dev",
            types=["forgotten_dev", "idle_instance"],
            severity="high",
            resource_id="i-0123456789abcdef0",
            resource_name="dev-api-joshua",
            resource_kind="EC2",
            instance_type="t3.large",
            region=region,
            monthly_cost_usd=instance_monthly_usd("t3.large"),
            monthly_kwh=t3_kwh,
            monthly_kg_co2=t3_kg,
            recommendation="This looks like a personal dev environment left running. Stop it overnight or replace with a start/stop schedule.",
            evidence={
                "avg_cpu_percent": 2.1,
                "avg_network_bytes_per_hour": 22000,
                "lookback_days": lookback_days,
                "age_days": 23,
                "tags": {"Name": "dev-api-joshua", "Environment": "dev"},
                "state": "running",
            },
        ),
        _finding(
            id="demo-r5",
            primary_type="oversized_instance",
            types=["oversized_instance"],
            severity="medium",
            resource_id="i-0bbccddeeff001122",
            resource_name="prod-cache-1",
            resource_kind="EC2",
            instance_type="r5.xlarge",
            region=region,
            monthly_cost_usd=r5_delta,
            monthly_kwh=r5_kwh,
            monthly_kg_co2=r5_kg,
            recommendation="Downsize r5.xlarge → r5.large. CPU is low enough that half the RAM is not earning its keep.",
            evidence={
                "avg_cpu_percent": 8.4,
                "avg_network_bytes_per_hour": 1_200_000,
                "lookback_days": lookback_days,
                "age_days": 120,
                "suggested_type": "r5.large",
                "current_monthly_usd": round(r5_full, 2),
                "resized_monthly_usd": round(r5_down, 2),
                "tags": {"Name": "prod-cache-1", "Environment": "prod"},
                "state": "running",
            },
        ),
        _finding(
            id="demo-nat",
            primary_type="idle_nat",
            types=["idle_nat"],
            severity="high",
            resource_id="nat-0abc111def222333",
            resource_name="dev-nat",
            resource_kind="NAT Gateway",
            instance_type=None,
            region=region,
            monthly_cost_usd=nat_monthly_usd(),
            monthly_kwh=nat_kwh,
            monthly_kg_co2=kwh_to_kg(nat_kwh, region),
            recommendation="NAT gateways bill ~$32/month even with zero traffic. Delete this leftover from a discarded VPC experiment.",
            evidence={
                "bytes_out_lookback": 48000,
                "lookback_days": lookback_days,
                "age_days": 61,
                "state": "available",
            },
        ),
        _finding(
            id="demo-vol",
            primary_type="unattached_volume",
            types=["unattached_volume"],
            severity="high",
            resource_id="vol-0aaa111bbb222ccc",
            resource_name="backup-restore-tmp",
            resource_kind="EBS",
            instance_type=None,
            region=region,
            monthly_cost_usd=ebs_monthly_usd(200, "gp3"),
            monthly_kwh=vol_kwh,
            monthly_kg_co2=kwh_to_kg(vol_kwh, region),
            recommendation="Unattached 200 GB volume. Snapshot if you need the data, then delete.",
            evidence={
                "size_gb": 200,
                "volume_type": "gp3",
                "state": "available",
                "age_days": 34,
                "tags": {"Name": "backup-restore-tmp"},
            },
        ),
        _finding(
            id="demo-vol2",
            primary_type="unattached_volume",
            types=["unattached_volume"],
            severity="medium",
            resource_id="vol-0ddd444eee555fff",
            resource_name="from-terminated-i-0999",
            resource_kind="EBS",
            instance_type=None,
            region=region,
            monthly_cost_usd=ebs_monthly_usd(80, "gp2"),
            monthly_kwh=vol2_kwh,
            monthly_kg_co2=kwh_to_kg(vol2_kwh, region),
            recommendation="Orphaned root volume from a terminated instance. Delete if no snapshot is required.",
            evidence={
                "size_gb": 80,
                "volume_type": "gp2",
                "state": "available",
                "age_days": 19,
                "tags": {"Name": "from-terminated-i-0999"},
            },
        ),
        _finding(
            id="demo-eip",
            primary_type="unused_eip",
            types=["unused_eip"],
            severity="low",
            resource_id="eipalloc-0aa11bb22cc33dd",
            resource_name="54.234.10.88",
            resource_kind="Elastic IP",
            instance_type=None,
            region=region,
            monthly_cost_usd=eip_monthly_usd(),
            monthly_kwh=0,
            monthly_kg_co2=0,
            recommendation="Unassociated Elastic IP. Release it — AWS charges for idle public IPv4.",
            evidence={"public_ip": "54.234.10.88", "associated": False},
        ),
    ]

    return ScanResult(
        scanned_at=datetime.now(timezone.utc).isoformat(),
        region=region,
        account_id="123456789012",
        mode="demo",
        lookback_days=lookback_days,
        totals=_totals(findings),
        counts=_counts(findings),
        findings=findings,
        methodology=METHODOLOGY,
    )
