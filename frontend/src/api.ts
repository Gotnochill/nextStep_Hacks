import type { ScanResult } from "./types";

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

export async function fetchDemo(region = "us-east-1"): Promise<ScanResult> {
  const res = await fetch(`/api/demo?region=${encodeURIComponent(region)}`);
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
