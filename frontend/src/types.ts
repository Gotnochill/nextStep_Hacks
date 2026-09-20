export type FindingType =
  | "idle_instance"
  | "oversized_instance"
  | "forgotten_dev"
  | "unattached_volume"
  | "unused_eip"
  | "idle_nat";

export type Severity = "critical" | "high" | "medium" | "low";

export type Finding = {
  id: string;
  primary_type: FindingType;
  types: FindingType[];
  severity: Severity;
  resource_id: string;
  resource_name: string;
  resource_kind: string;
  instance_type: string | null;
  region: string;
  monthly_cost_usd: number;
  annual_cost_usd: number;
  monthly_kwh: number;
  monthly_kg_co2: number;
  annual_kg_co2: number;
  recommendation: string;
  evidence: Record<string, unknown>;
};

export type ScanResult = {
  scanned_at: string;
  region: string;
  account_id: string;
  mode: "live" | "demo";
  lookback_days: number;
  totals: {
    monthly_cost_usd: number;
    annual_cost_usd: number;
    monthly_kwh: number;
    annual_kwh: number;
    monthly_kg_co2: number;
    annual_kg_co2: number;
    equivalents: {
      miles_driven: number;
      phones_charged: number;
      trees_to_offset_year: number;
    };
  };
  counts: {
    idle_instances: number;
    oversized_instances: number;
    forgotten_dev: number;
    unattached_volumes: number;
    unused_eips: number;
    idle_nats: number;
    total: number;
  };
  findings: Finding[];
  methodology: string;
};
