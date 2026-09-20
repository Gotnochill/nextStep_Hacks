import type { ScanResult, Status } from "./types";

export type ScanPayload = {
  region: string;
  lookback_days: number;
  cpu_idle_threshold: number;
  aws_access_key_id?: string;
  aws_secret_access_key?: string;
  aws_session_token?: string;
};

async function readError(res: Response): Promise<string> {
  try {
    const body = await res.json();
    return body.detail || body.message || res.statusText;
  } catch {
    return res.statusText;
  }
}

const asset = (path: string) => {
  const base = import.meta.env.BASE_URL || "/";
  return `${base}${path.replace(/^\//, "")}`;
};

export async function fetchStatus(): Promise<Status> {
  try {
    const res = await fetch("/api/status");
    if (res.ok) return res.json();
  } catch {
    /* static host has no API */
  }
  return { ok: true, name: "ember", live_aws: false, region: "us-east-1" };
}

export async function fetchDemo(region = "us-east-1"): Promise<ScanResult> {
  try {
    const res = await fetch(`/api/demo?region=${encodeURIComponent(region)}`);
    if (res.ok) return res.json();
  } catch {
    /* fall through to bundled ledger */
  }
  const res = await fetch(asset("sample-ledger.json"));
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function runLiveAccountScan(payload: {
  region: string;
  lookback_days: number;
  cpu_idle_threshold: number;
}): Promise<ScanResult> {
  const res = await fetch("/api/scan/live", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function runScan(payload: ScanPayload): Promise<ScanResult> {
  const res = await fetch("/api/scan", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}
