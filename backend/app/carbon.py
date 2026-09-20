"""Energy and CO2 estimates aligned with Cloud Carbon Footprint coefficients.

AWS does not publish per-instance wattage. Ember estimates:

  kWh = (CPU watts + memory kWh) * PUE
  kg CO2e = kWh * regional grid intensity

Coefficients (Thoughtworks Cloud Carbon Footprint / SPECpower-derived):
  min 0.74 W/vCPU at 0% utilization, max 3.5 W/vCPU at 100%
  memory 0.000392 kWh per GB-hour
  SSD/EBS 1.2 Wh per TB-hour, EBS replication factor 2
  AWS PUE 1.135
  grid intensity: EPA eGRID / CCF regional factors
"""

from __future__ import annotations

from .catalog import HOURS_PER_MONTH, spec_for

PUE = 1.135
MIN_WATTS_PER_VCPU = 0.74
MAX_WATTS_PER_VCPU = 3.5
MEMORY_KWH_PER_GB_HOUR = 0.000392
SSD_WH_PER_TB_HOUR = 1.2
EBS_REPLICATION = 2.0

# metric tons CO2e / kWh from CCF grid-emissions-factors-aws.csv → g / kWh
GRID_G_PER_KWH: dict[str, float] = {
    "us-east-1": 415.755,
    "us-east-2": 440.187,
    "us-west-1": 350.861,
    "us-west-2": 350.861,
    "ca-central-1": 130.0,
    "eu-central-1": 338.0,
    "eu-west-1": 316.0,
    "eu-west-2": 228.0,
    "eu-west-3": 52.0,
    "eu-north-1": 8.0,
    "eu-south-1": 233.0,
    "ap-south-1": 708.0,
    "ap-southeast-1": 408.5,
    "ap-southeast-2": 790.0,
    "ap-northeast-1": 506.0,
    "ap-northeast-2": 500.0,
    "ap-northeast-3": 506.0,
    "ap-east-1": 810.0,
    "sa-east-1": 74.0,
    "af-south-1": 928.0,
    "me-south-1": 732.0,
}
DEFAULT_G_PER_KWH = 400.0

# EPA: average US passenger vehicle ~404 g CO2 / mile
G_CO2_PER_MILE = 404.0
# ~0.011 kWh per smartphone charge (EPA)
KWH_PER_PHONE_CHARGE = 0.011
# Mature tree ~21 kg CO2 / year (rough urban-forestry rule of thumb)
KG_CO2_PER_TREE_YEAR = 21.0

METHODOLOGY = (
    "Estimates use Cloud Carbon Footprint coefficients (min/max watts per vCPU, "
    "0.392 W/GB memory, 1.2 Wh/TB-hour SSD, EBS replication 2, AWS PUE 1.135) "
    "and regional grid intensity (EPA eGRID / CCF). These are modeled figures, "
    "not AWS-measured per-resource emissions. Dollar amounts use us-east-1 "
    "on-demand list prices. Idle Elastic IPs have cost but negligible energy."
)


def grid_g_per_kwh(region: str) -> float:
    return GRID_G_PER_KWH.get(region, DEFAULT_G_PER_KWH)


def cpu_watts(vcpu: int, cpu_percent: float) -> float:
    util = max(0.0, min(100.0, cpu_percent)) / 100.0
    per = MIN_WATTS_PER_VCPU + (MAX_WATTS_PER_VCPU - MIN_WATTS_PER_VCPU) * util
    return vcpu * per


def compute_monthly_kwh(
    instance_type: str, cpu_percent: float, hours: float = HOURS_PER_MONTH
) -> float:
    spec = spec_for(instance_type)
    cpu_kwh = cpu_watts(spec.vcpu, cpu_percent) * hours / 1000.0
    mem_kwh = spec.memory_gb * MEMORY_KWH_PER_GB_HOUR * hours
    return (cpu_kwh + mem_kwh) * PUE


def ebs_monthly_kwh(size_gb: float, hours: float = HOURS_PER_MONTH) -> float:
    tb = max(size_gb, 0.0) / 1024.0
    # 1.2 Wh per TB-hour → kWh
    kwh = tb * (SSD_WH_PER_TB_HOUR / 1000.0) * hours * EBS_REPLICATION
    return kwh * PUE


def nat_monthly_kwh(hours: float = HOURS_PER_MONTH) -> float:
    """Managed NAT has no public wattage; model as a small always-on appliance (~12W)."""
    return (12.0 * hours / 1000.0) * PUE


def kwh_to_kg(kwh: float, region: str) -> float:
    return kwh * grid_g_per_kwh(region) / 1000.0


def equivalents(annual_kg_co2: float, annual_kwh: float) -> dict[str, float]:
    return {
        "miles_driven": annual_kg_co2 * 1000.0 / G_CO2_PER_MILE,
        "phones_charged": annual_kwh / KWH_PER_PHONE_CHARGE,
        "trees_to_offset_year": annual_kg_co2 / KG_CO2_PER_TREE_YEAR,
    }
