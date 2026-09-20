"""Instance specs and on-demand list prices (us-east-1), used as a reliable demo fallback.

Prices are approximate Linux on-demand USD/hour. The scanner never needs a
third-party key; if AWS Price List is unavailable we still produce numbers.
"""

from __future__ import annotations

from dataclasses import dataclass

HOURS_PER_MONTH = 730


@dataclass(frozen=True)
class InstanceSpec:
    vcpu: int
    memory_gb: float
    usd_per_hour: float


# Common types you would actually seed or find in a hackathon account.
INSTANCE_CATALOG: dict[str, InstanceSpec] = {
    "t3.nano": InstanceSpec(2, 0.5, 0.0052),
    "t3.micro": InstanceSpec(2, 1.0, 0.0104),
    "t3.small": InstanceSpec(2, 2.0, 0.0208),
    "t3.medium": InstanceSpec(2, 4.0, 0.0416),
    "t3.large": InstanceSpec(2, 8.0, 0.0832),
    "t3.xlarge": InstanceSpec(4, 16.0, 0.1664),
    "t3.2xlarge": InstanceSpec(8, 32.0, 0.3328),
    "t2.micro": InstanceSpec(1, 1.0, 0.0116),
    "t2.small": InstanceSpec(1, 2.0, 0.023),
    "t2.medium": InstanceSpec(2, 4.0, 0.0464),
    "t2.large": InstanceSpec(2, 8.0, 0.0928),
    "m5.large": InstanceSpec(2, 8.0, 0.096),
    "m5.xlarge": InstanceSpec(4, 16.0, 0.192),
    "m5.2xlarge": InstanceSpec(8, 32.0, 0.384),
    "m5.4xlarge": InstanceSpec(16, 64.0, 0.768),
    "m5.8xlarge": InstanceSpec(32, 128.0, 1.536),
    "m6i.large": InstanceSpec(2, 8.0, 0.096),
    "m6i.xlarge": InstanceSpec(4, 16.0, 0.192),
    "m6i.2xlarge": InstanceSpec(8, 32.0, 0.384),
    "c5.large": InstanceSpec(2, 4.0, 0.085),
    "c5.xlarge": InstanceSpec(4, 8.0, 0.17),
    "c5.2xlarge": InstanceSpec(8, 16.0, 0.34),
    "c5.4xlarge": InstanceSpec(16, 32.0, 0.68),
    "c6i.large": InstanceSpec(2, 4.0, 0.085),
    "c6i.xlarge": InstanceSpec(4, 8.0, 0.17),
    "r5.large": InstanceSpec(2, 16.0, 0.126),
    "r5.xlarge": InstanceSpec(4, 32.0, 0.252),
    "r5.2xlarge": InstanceSpec(8, 64.0, 0.504),
    "r5.4xlarge": InstanceSpec(16, 128.0, 1.008),
    "r6i.large": InstanceSpec(2, 16.0, 0.126),
    "r6i.xlarge": InstanceSpec(4, 32.0, 0.252),
    "g4dn.xlarge": InstanceSpec(4, 16.0, 0.526),
    "g4dn.2xlarge": InstanceSpec(8, 32.0, 0.752),
    "p3.2xlarge": InstanceSpec(8, 61.0, 3.06),
}

SIZE_FALLBACK: dict[str, InstanceSpec] = {
    "nano": InstanceSpec(2, 0.5, 0.0052),
    "micro": InstanceSpec(2, 1.0, 0.0104),
    "small": InstanceSpec(2, 2.0, 0.0208),
    "medium": InstanceSpec(2, 4.0, 0.0416),
    "large": InstanceSpec(2, 8.0, 0.0832),
    "xlarge": InstanceSpec(4, 16.0, 0.1664),
    "2xlarge": InstanceSpec(8, 32.0, 0.3328),
    "3xlarge": InstanceSpec(12, 48.0, 0.50),
    "4xlarge": InstanceSpec(16, 64.0, 0.768),
    "8xlarge": InstanceSpec(32, 128.0, 1.536),
    "9xlarge": InstanceSpec(36, 144.0, 1.728),
    "12xlarge": InstanceSpec(48, 192.0, 2.304),
    "16xlarge": InstanceSpec(64, 256.0, 3.072),
    "24xlarge": InstanceSpec(96, 384.0, 4.608),
    "32xlarge": InstanceSpec(128, 512.0, 6.144),
    "metal": InstanceSpec(96, 384.0, 4.608),
}

FAMILY_PRICE_MULT = {
    "t": 1.0,
    "m": 1.15,
    "c": 1.05,
    "r": 1.55,
    "g": 4.8,
    "p": 18.0,
    "inf": 8.0,
}

EBS_USD_PER_GB_MONTH = {
    "gp3": 0.08,
    "gp2": 0.10,
    "io1": 0.125,
    "io2": 0.125,
    "st1": 0.045,
    "sc1": 0.015,
    "standard": 0.05,
}

EIP_USD_PER_HOUR = 0.005
NAT_USD_PER_HOUR = 0.045

# One size down for "oversized" savings deltas.
DOWNSIZE = {
    "32xlarge": "16xlarge",
    "24xlarge": "16xlarge",
    "16xlarge": "8xlarge",
    "12xlarge": "8xlarge",
    "9xlarge": "4xlarge",
    "8xlarge": "4xlarge",
    "4xlarge": "2xlarge",
    "3xlarge": "2xlarge",
    "2xlarge": "xlarge",
    "xlarge": "large",
    "large": "medium",
    "medium": "small",
    "small": "micro",
}


def parse_size(instance_type: str) -> str:
    if "." in instance_type:
        return instance_type.split(".", 1)[1]
    return instance_type


def parse_family(instance_type: str) -> str:
    prefix = instance_type.split(".", 1)[0] if "." in instance_type else instance_type
    return prefix[:1]


def spec_for(instance_type: str) -> InstanceSpec:
    key = instance_type.lower()
    if key in INSTANCE_CATALOG:
        return INSTANCE_CATALOG[key]
    size = parse_size(key)
    base = SIZE_FALLBACK.get(size, InstanceSpec(2, 8.0, 0.10))
    mult = FAMILY_PRICE_MULT.get(parse_family(key), 1.2)
    return InstanceSpec(base.vcpu, base.memory_gb, round(base.usd_per_hour * mult, 4))


def downsized_type(instance_type: str) -> str | None:
    if "." not in instance_type:
        return None
    family, size = instance_type.split(".", 1)
    nxt = DOWNSIZE.get(size)
    if not nxt:
        return None
    return f"{family}.{nxt}"
