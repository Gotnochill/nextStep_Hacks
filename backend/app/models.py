from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

FindingType = Literal[
    "idle_instance",
    "oversized_instance",
    "forgotten_dev",
    "unattached_volume",
    "unused_eip",
    "idle_nat",
]
Severity = Literal["critical", "high", "medium", "low"]
ScanMode = Literal["live", "demo"]


class ScanRequest(BaseModel):
    region: str = "us-east-1"
    lookback_days: int = Field(default=7, ge=1, le=14)
    cpu_idle_threshold: float = Field(default=5.0, ge=0, le=50)
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    aws_session_token: str | None = None


class Finding(BaseModel):
    id: str
    primary_type: FindingType
    types: list[FindingType]
    severity: Severity
    resource_id: str
    resource_name: str
    resource_kind: str
    instance_type: str | None = None
    region: str
    monthly_cost_usd: float
    annual_cost_usd: float
    monthly_kwh: float
    monthly_kg_co2: float
    annual_kg_co2: float
    recommendation: str
    evidence: dict[str, Any] = Field(default_factory=dict)


class Equivalents(BaseModel):
    miles_driven: float
    phones_charged: float
    trees_to_offset_year: float


class Totals(BaseModel):
    monthly_cost_usd: float
    annual_cost_usd: float
    monthly_kwh: float
    annual_kwh: float
    monthly_kg_co2: float
    annual_kg_co2: float
    equivalents: Equivalents


class Counts(BaseModel):
    idle_instances: int = 0
    oversized_instances: int = 0
    forgotten_dev: int = 0
    unattached_volumes: int = 0
    unused_eips: int = 0
    idle_nats: int = 0
    total: int = 0


class ScanResult(BaseModel):
    scanned_at: str
    region: str
    account_id: str
    mode: ScanMode
    lookback_days: int
    totals: Totals
    counts: Counts
    findings: list[Finding]
    methodology: str
