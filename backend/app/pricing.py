from __future__ import annotations

from .catalog import (
    EBS_USD_PER_GB_MONTH,
    EIP_USD_PER_HOUR,
    HOURS_PER_MONTH,
    NAT_USD_PER_HOUR,
    spec_for,
)


def instance_monthly_usd(instance_type: str, hours: float = HOURS_PER_MONTH) -> float:
    return spec_for(instance_type).usd_per_hour * hours


def ebs_monthly_usd(size_gb: float, volume_type: str) -> float:
    rate = EBS_USD_PER_GB_MONTH.get(volume_type, 0.08)
    return size_gb * rate


def eip_monthly_usd(hours: float = HOURS_PER_MONTH) -> float:
    return EIP_USD_PER_HOUR * hours


def nat_monthly_usd(hours: float = HOURS_PER_MONTH) -> float:
    return NAT_USD_PER_HOUR * hours
