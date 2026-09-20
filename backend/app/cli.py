from __future__ import annotations

import argparse
import json

from .demo import demo_scan
from .models import ScanRequest
from .scanner import live_scan


def main() -> None:
    parser = argparse.ArgumentParser(description="Ember — scan an AWS account for idle cloud waste")
    parser.add_argument("--demo", action="store_true", help="Print seeded demo findings (no AWS call)")
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--lookback-days", type=int, default=7)
    parser.add_argument("--cpu-idle-threshold", type=float, default=5.0)
    args = parser.parse_args()

    if args.demo:
        result = demo_scan(region=args.region, lookback_days=args.lookback_days)
    else:
        result = live_scan(
            ScanRequest(
                region=args.region,
                lookback_days=args.lookback_days,
                cpu_idle_threshold=args.cpu_idle_threshold,
            )
        )

    print(json.dumps(result.model_dump(), indent=2))
    t = result.totals
    print(
        f"\n{result.counts.total} findings · "
        f"${t.monthly_cost_usd:.0f}/mo · "
        f"{t.annual_kg_co2:.0f} kg CO2/year · "
        f"{t.annual_kwh:.0f} kWh/year",
        flush=True,
    )


if __name__ == "__main__":
    main()
