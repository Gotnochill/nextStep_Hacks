import { FormEvent, useEffect, useMemo, useState } from "react";
import { fetchDemo, fetchStatus, runLiveAccountScan, runScan } from "./api";
import type { Finding, FindingType, ScanResult } from "./types";
import "./App.css";

type View = "land" | "connect" | "scanning" | "results";

const SCAN_LINES = [
  "Opening the account inventory…",
  "Asking CloudWatch which machines never wake up…",
  "Looking for volumes nobody attached…",
  "Pricing the waste in dollars…",
  "Translating idle watts into carbon…",
];

const TYPE_LABEL: Record<FindingType, string> = {
  idle_instance: "Idle compute",
  oversized_instance: "Oversized",
  forgotten_dev: "Forgotten env",
  unattached_volume: "Unattached volume",
  unused_eip: "Idle Elastic IP",
  idle_nat: "Idle NAT gateway",
};

const REGIONS = [
  "us-east-1",
  "us-east-2",
  "us-west-1",
  "us-west-2",
  "eu-west-1",
  "eu-central-1",
  "ap-south-1",
  "ap-southeast-1",
];

function money(n: number) {
  return n.toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });
}

function moneyExact(n: number) {
  return n.toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 2 });
}

function compact(n: number, unit: string) {
  const abs = Math.abs(n);
  const body = abs >= 100 ? abs.toFixed(0) : abs >= 10 ? abs.toFixed(1) : abs.toFixed(2);
  return `${body} ${unit}`;
}

function useCountUp(target: number, duration = 1100) {
  const [value, setValue] = useState(0);
  useEffect(() => {
    let frame = 0;
    const start = performance.now();
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / duration);
      const eased = 1 - (1 - t) ** 3;
      setValue(target * eased);
      if (t < 1) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [target, duration]);
  return value;
}

function Mark() {
  return (
    <svg className="mark" viewBox="0 0 32 32" aria-hidden>
      <circle cx="16" cy="16" r="13" fill="none" stroke="currentColor" strokeWidth="1.4" />
      <path d="M16 22c4-5 6-8 6-11a6 6 0 1 0-12 0c0 3 2 6 6 11Z" fill="currentColor" />
    </svg>
  );
}

export default function App() {
  const [view, setView] = useState<View>("land");
  const [result, setResult] = useState<ScanResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [region, setRegion] = useState("us-east-1");
  const [lookback, setLookback] = useState(7);
  const [keyId, setKeyId] = useState("");
  const [secret, setSecret] = useState("");
  const [token, setToken] = useState("");
  const [scanLine, setScanLine] = useState(0);
  const [liveAws, setLiveAws] = useState(false);
  const [liveRegion, setLiveRegion] = useState("us-east-1");

  useEffect(() => {
    fetchStatus()
      .then((s) => {
        setLiveAws(s.live_aws);
        if (s.region) setLiveRegion(s.region);
      })
      .catch(() => setLiveAws(false));
  }, []);

  useEffect(() => {
    if (view !== "scanning") return;
    const id = window.setInterval(() => setScanLine((n) => (n + 1) % SCAN_LINES.length), 1400);
    return () => window.clearInterval(id);
  }, [view]);

  async function loadLiveAccount() {
    setError(null);
    setView("scanning");
    setScanLine(0);
    try {
      const data = await runLiveAccountScan({
        region: liveRegion,
        lookback_days: lookback,
        cpu_idle_threshold: 5,
      });
      setResult(data);
      setView("results");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Live AWS scan failed");
      setView("land");
    }
  }

  async function loadDemo() {
    setError(null);
    setView("scanning");
    setScanLine(0);
    try {
      const data = await fetchDemo(region);
      setResult(data);
      setView("results");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Demo failed");
      setView("land");
    }
  }

  async function onScan(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setView("scanning");
    setScanLine(0);
    try {
      const data = await runScan({
        region,
        lookback_days: lookback,
        cpu_idle_threshold: 5,
        aws_access_key_id: keyId || undefined,
        aws_secret_access_key: secret || undefined,
        aws_session_token: token || undefined,
      });
      setResult(data);
      setView("results");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Scan failed");
      setView("connect");
    }
  }

  return (
    <div className="shell">
      <div className="heat" aria-hidden />
      <header className="top">
        <button className="brand" onClick={() => { setView("land"); setError(null); }}>
          <Mark />
          <span>Ember</span>
          <em>Cloud waste finder</em>
        </button>
        <nav>
          <span className="eyebrow">Earth Forward</span>
          {view !== "connect" && view !== "scanning" && (
            <button className="ghost" onClick={() => setView("connect")}>
              Scan AWS
            </button>
          )}
        </nav>
      </header>

      {error && <div className="banner">{error}</div>}

      {view === "land" && (
        <Landing onDemo={loadDemo} onScan={() => setView("connect")} onLive={loadLiveAccount} liveAws={liveAws} />
      )}
      {view === "connect" && (
        <Connect
          region={region}
          lookback={lookback}
          keyId={keyId}
          secret={secret}
          token={token}
          onRegion={setRegion}
          onLookback={setLookback}
          onKeyId={setKeyId}
          onSecret={setSecret}
          onToken={setToken}
          onSubmit={onScan}
          onDemo={loadDemo}
          onLive={liveAws ? loadLiveAccount : undefined}
          onBack={() => setView("land")}
        />
      )}
      {view === "scanning" && (
        <div className="scan-stage">
          <div className="pulse" />
          <p className="eyebrow">Scanning {region}</p>
          <h2>{SCAN_LINES[scanLine]}</h2>
          <p className="muted">Idle servers still draw power. We are looking for the ones that never clock in.</p>
        </div>
      )}
      {view === "results" && result && (
        <Results result={result} onAgain={() => setView("connect")} onHome={() => setView("land")} />
      )}
    </div>
  );
}

function Landing({
  onDemo,
  onScan,
  onLive,
  liveAws,
}: {
  onDemo: () => void;
  onScan: () => void;
  onLive: () => void;
  liveAws: boolean;
}) {
  return (
    <main className="land">
      <p className="kicker">Data centers already eat a slice of the planet’s electricity. Idle cloud eats it for nothing.</p>
      <h1>
        Your cloud is on
        <br />
        <em>even when you are not.</em>
      </h1>
      <p className="lede">
        Ember scans an AWS account for idle instances, forgotten dev boxes, unattached volumes, and leftover network
        gear — then tells you the dollars, kilowatt-hours, and CO<sub>2</sub> you get back by shutting them down.
      </p>
      <div className="cta-row">
        {liveAws ? (
          <button className="primary" onClick={onLive}>
            Scan the live AWS account
          </button>
        ) : (
          <button className="primary" onClick={onScan}>
            Scan an AWS account
          </button>
        )}
        <button className="ghost" onClick={onDemo}>
          Sample ledger (no AWS)
        </button>
        {liveAws && (
          <button className="ghost" onClick={onScan}>
            Use your own keys
          </button>
        )}
      </div>
      {liveAws && (
        <p className="live-note">The primary button hits a real throwaway AWS account seeded with idle waste. Keys never leave the server.</p>
      )}

      <section className="stat-grid">
        <article>
          <strong>~1.5%</strong>
          <span>of global electricity already goes to data centers, and that share is climbing. (IEA)</span>
        </article>
        <article>
          <strong>24 / 7</strong>
          <span>An idle EC2 instance still draws watts, still needs cooling, still bills you every hour.</span>
        </article>
        <article>
          <strong>~30%</strong>
          <span>of cloud spend is commonly wasted on idle and oversized resources. (Flexera)</span>
        </article>
      </section>

      <section className="how">
        <h2>What it actually checks</h2>
        <ol>
          <li>
            <b>Idle compute</b>
            CloudWatch CPU and network. If a machine has been awake and unemployed, it is waste.
          </li>
          <li>
            <b>Forgotten environments</b>
            Names and tags like dev, test, sandbox — left running from last quarter.
          </li>
          <li>
            <b>Stranded storage &amp; IPs</b>
            Unattached EBS volumes and Elastic IPs nobody released.
          </li>
          <li>
            <b>Always-on appliances</b>
            NAT gateways that cost ~$32/month even with zero traffic.
          </li>
        </ol>
        <p className="footnote">
          No third-party APIs. Credentials stay in your session. Carbon numbers are modeled with Cloud Carbon Footprint
          coefficients — the same class of estimate scientists use when AWS will not give per-instance watts.
        </p>
      </section>
    </main>
  );
}

function Connect(props: {
  region: string;
  lookback: number;
  keyId: string;
  secret: string;
  token: string;
  onRegion: (v: string) => void;
  onLookback: (v: number) => void;
  onKeyId: (v: string) => void;
  onSecret: (v: string) => void;
  onToken: (v: string) => void;
  onSubmit: (e: FormEvent) => void;
  onDemo: () => void;
  onLive?: () => void;
  onBack: () => void;
}) {
  return (
    <main className="connect">
      <button className="text-btn" onClick={props.onBack}>
        ← Back
      </button>
      <h1>Read-only look into the furnace.</h1>
      <p className="lede">
        Keys are used for this scan only and never stored. Leave them blank to use AWS credentials already on this
        machine.
      </p>
      <form onSubmit={props.onSubmit} className="form">
        <label>
          Region
          <select value={props.region} onChange={(e) => props.onRegion(e.target.value)}>
            {REGIONS.map((r) => (
              <option key={r}>{r}</option>
            ))}
          </select>
        </label>
        <label>
          Lookback (days)
          <input
            type="number"
            min={1}
            max={14}
            value={props.lookback}
            onChange={(e) => props.onLookback(Number(e.target.value))}
          />
        </label>
        <label>
          Access key ID
          <input value={props.keyId} onChange={(e) => props.onKeyId(e.target.value)} autoComplete="off" />
        </label>
        <label>
          Secret access key
          <input
            type="password"
            value={props.secret}
            onChange={(e) => props.onSecret(e.target.value)}
            autoComplete="off"
          />
        </label>
        <label className="wide">
          Session token <span className="hint">optional, for SSO / temporary keys</span>
          <input value={props.token} onChange={(e) => props.onToken(e.target.value)} autoComplete="off" />
        </label>
        <div className="cta-row">
          {props.onLive && (
            <button className="primary" type="button" onClick={props.onLive}>
              Scan live AWS account
            </button>
          )}
          <button className={props.onLive ? "ghost" : "primary"} type="submit">
            Run scan
          </button>
          <button className="ghost" type="button" onClick={props.onDemo}>
            Use sample ledger instead
          </button>
        </div>
      </form>
    </main>
  );
}

function Results({
  result,
  onAgain,
  onHome,
}: {
  result: ScanResult;
  onAgain: () => void;
  onHome: () => void;
}) {
  const cost = useCountUp(result.totals.monthly_cost_usd);
  const kg = useCountUp(result.totals.annual_kg_co2);
  const kwh = useCountUp(result.totals.annual_kwh);
  const [openId, setOpenId] = useState<string | null>(result.findings[0]?.id ?? null);

  const bars = useMemo(() => {
    const groups: Record<string, number> = {};
    for (const f of result.findings) {
      groups[f.primary_type] = (groups[f.primary_type] || 0) + f.monthly_cost_usd;
    }
    const max = Math.max(...Object.values(groups), 1);
    return Object.entries(groups)
      .sort((a, b) => b[1] - a[1])
      .map(([type, usd]) => ({ type: type as FindingType, usd, pct: (usd / max) * 100 }));
  }, [result.findings]);

  function download() {
    const blob = new Blob([JSON.stringify(result, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `ember-${result.mode}-${result.region}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <main className="results">
      <div className="results-head">
        <div>
          <p className="eyebrow">
            {result.mode === "demo" ? "Sample ledger" : "Live AWS account"} · {result.region} · {maskAccount(result.account_id)} ·{" "}
            {result.lookback_days}d lookback
          </p>
          <h1>If you shut this down.</h1>
        </div>
        <div className="cta-row">
          <button className="ghost" onClick={download}>
            Export JSON
          </button>
          <button className="ghost" onClick={onAgain}>
            Scan again
          </button>
          <button className="text-btn" onClick={onHome}>
            Home
          </button>
        </div>
      </div>

      <section className="heroes">
        <Hero label="wasted / month" value={money(cost)} hint={money(result.totals.annual_cost_usd) + " / year"} />
        <Hero
          label="CO2e / year"
          value={compact(kg, "kg")}
          hint={`${result.totals.monthly_kg_co2.toFixed(1)} kg this month`}
          accent
        />
        <Hero label="energy / year" value={compact(kwh, "kWh")} hint={`${result.totals.monthly_kwh.toFixed(1)} kWh this month`} />
      </section>

      <section className="equiv">
        <p>
          That annual carbon is about <b>{Math.round(result.totals.equivalents.miles_driven).toLocaleString()} miles</b> driven,{" "}
          <b>{Math.round(result.totals.equivalents.phones_charged).toLocaleString()} phone charges</b>, or{" "}
          <b>{result.totals.equivalents.trees_to_offset_year.toFixed(1)} trees</b> working for a year to take it back.
        </p>
      </section>

      <section className="split">
        <div>
          <h2>Where the heat is</h2>
          <ul className="bars">
            {bars.map((b) => (
              <li key={b.type}>
                <div className="bar-meta">
                  <span>{TYPE_LABEL[b.type]}</span>
                  <span>{moneyExact(b.usd)}/mo</span>
                </div>
                <div className="bar-track">
                  <i style={{ width: `${b.pct}%` }} />
                </div>
              </li>
            ))}
          </ul>
        </div>
        <div className="count-card">
          <h2>{result.counts.total} findings</h2>
          <ul>
            <li>{result.counts.forgotten_dev} forgotten environments</li>
            <li>{result.counts.idle_instances} idle instances</li>
            <li>{result.counts.oversized_instances} oversized machines</li>
            <li>{result.counts.unattached_volumes} unattached volumes</li>
            <li>{result.counts.idle_nats} idle NAT gateways</li>
            <li>{result.counts.unused_eips} unused Elastic IPs</li>
          </ul>
        </div>
      </section>

      <section className="ledger">
        <h2>Waste ledger</h2>
        <div className="table-head">
          <span>Resource</span>
          <span>$ / mo</span>
          <span>kg CO2 / yr</span>
        </div>
        {result.findings.map((f) => (
          <FindingRow key={f.id} finding={f} open={openId === f.id} onToggle={() => setOpenId(openId === f.id ? null : f.id)} />
        ))}
        {result.findings.length === 0 && (
          <p className="muted empty">No waste in this region for the lookback window. Try another region, or seed the demo account.</p>
        )}
      </section>

      <details className="method">
        <summary>How the carbon math works</summary>
        <p>{result.methodology}</p>
      </details>
    </main>
  );
}

function Hero({ label, value, hint, accent }: { label: string; value: string; hint: string; accent?: boolean }) {
  return (
    <article className={accent ? "hero accent" : "hero"}>
      <span className="hero-label">{label}</span>
      <strong>{value}</strong>
      <span className="hero-hint">{hint}</span>
    </article>
  );
}

function FindingRow({
  finding,
  open,
  onToggle,
}: {
  finding: Finding;
  open: boolean;
  onToggle: () => void;
}) {
  const cpu = finding.evidence.avg_cpu_percent;
  return (
    <article className={`row ${open ? "open" : ""}`}>
      <button className="row-main" onClick={onToggle}>
        <span className="row-id">
          <span className={`sev ${finding.severity}`}>{finding.severity}</span>
          <span className="pill">{TYPE_LABEL[finding.primary_type]}</span>
          <b>{finding.resource_name}</b>
          <code>{finding.instance_type || finding.resource_kind}</code>
        </span>
        <span className="row-num">{moneyExact(finding.monthly_cost_usd)}</span>
        <span className="row-num moss">{finding.annual_kg_co2.toFixed(1)}</span>
      </button>
      {open && (
        <div className="row-body">
          <p>{finding.recommendation}</p>
          <dl>
            <div>
              <dt>Resource</dt>
              <dd>{finding.resource_id}</dd>
            </div>
            {cpu !== undefined && cpu !== null && (
              <div>
                <dt>Avg CPU</dt>
                <dd>{String(cpu)}%</dd>
              </div>
            )}
            <div>
              <dt>Energy</dt>
              <dd>{finding.monthly_kwh.toFixed(2)} kWh / mo</dd>
            </div>
            <div>
              <dt>Carbon</dt>
              <dd>{finding.monthly_kg_co2.toFixed(2)} kg / mo</dd>
            </div>
          </dl>
        </div>
      )}
    </article>
  );
}

function maskAccount(id: string) {
  if (id.length < 6) return id;
  return `…${id.slice(-4)}`;
}