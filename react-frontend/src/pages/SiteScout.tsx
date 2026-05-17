import { useState } from "react";
import { api } from "../api/client";

const NAVY = "#0f1e46";
const TEAL = "#00c8c8";

const REGIONS = ["South India", "North India", "West India", "East India", "Pan-India"];
const BUDGET_TIERS = ["Economy", "Mid-Range", "Enterprise", "Premium"];
const PRIORITIES = ["PUE / Efficiency", "Renewable energy", "Connectivity (IXP)", "Land cost", "Grid reliability"];

interface ScoutResult {
  report: string;
  tools_used: string[];
  top_city: string;
  requirements: Record<string, string | number>;
}

function renderReport(report: string) {
  return report.split("\n").map((line, i) => {
    if (line.startsWith("## ")) {
      return (
        <div key={i} style={{
          background: TEAL, color: "#fff", fontWeight: 700, fontSize: 13,
          padding: "6px 14px", borderRadius: 4, margin: "18px 0 8px",
        }}>
          {line.replace(/^## /, "")}
        </div>
      );
    }
    if (line.startsWith("- ") || line.startsWith("* ")) {
      return <div key={i} style={{ paddingLeft: 18, color: "#334466", fontSize: 13, lineHeight: 1.8 }}>• {line.slice(2)}</div>;
    }
    if (/^\d+\./.test(line)) {
      return <div key={i} style={{ paddingLeft: 14, color: "#334466", fontSize: 13, lineHeight: 1.8, fontWeight: 500 }}>{line}</div>;
    }
    if (!line.trim()) return <div key={i} style={{ height: 6 }} />;
    return <p key={i} style={{ margin: "4px 0", color: "#334466", fontSize: 13, lineHeight: 1.7 }}>{line}</p>;
  });
}

export default function SiteScout() {
  const [apiKey, setApiKey] = useState(localStorage.getItem("anthropic_key") ?? "");
  const [keySet, setKeySet] = useState(!!localStorage.getItem("anthropic_key"));

  const [form, setForm] = useState({
    region: "South India",
    capacity_mw: 50,
    renewable_target_pct: 60,
    budget_tier: "Enterprise",
    priority: "Renewable energy",
  });
  const [result, setResult] = useState<ScoutResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const activateKey = () => {
    localStorage.setItem("anthropic_key", apiKey);
    setKeySet(true);
  };

  const run = async () => {
    setLoading(true);
    setError("");
    try {
      const r = await api.post<ScoutResult>("/ai/scout", { ...form, api_key: apiKey });
      setResult(r.data);
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } }; message?: string };
      setError(err.response?.data?.detail ?? err.message ?? "Error");
    } finally {
      setLoading(false);
    }
  };

  const downloadTxt = () => {
    if (!result) return;
    const blob = new Blob([result.report], { type: "text/plain" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "site_scout_report.txt";
    a.click();
  };

  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLSelectElement | HTMLInputElement>) =>
    setForm(p => ({ ...p, [k]: e.target.type === "range" ? Number(e.target.value) : e.target.value }));

  return (
    <div style={{ padding: 32 }}>
      <h1 style={{ fontSize: 22, fontWeight: 700, color: NAVY, marginBottom: 4 }}>
        Site Scout Agent
      </h1>
      <p style={{ color: "#556688", fontSize: 13, marginBottom: 20 }}>
        Agentic AI that analyses your requirements, runs gravity + cluster models, and produces a structured recommendation report.
      </p>

      {!keySet && (
        <div style={{ background: "#fff", borderRadius: 12, padding: 20, marginBottom: 20, boxShadow: "0 1px 4px rgba(0,0,0,0.07)" }}>
          <div style={{ fontWeight: 600, color: NAVY, marginBottom: 10 }}>Anthropic API Key</div>
          <div style={{ display: "flex", gap: 10 }}>
            <input type="password" value={apiKey} onChange={e => setApiKey(e.target.value)}
              placeholder="sk-ant-…"
              style={{ flex: 1, padding: "8px 12px", borderRadius: 8, border: "1px solid #dde", fontSize: 13 }}
            />
            <button onClick={activateKey} disabled={!apiKey}
              style={{ padding: "8px 18px", borderRadius: 8, border: "none", background: TEAL, color: "#fff", fontWeight: 600, cursor: "pointer" }}
            >Activate</button>
          </div>
        </div>
      )}

      {keySet && (
        <div style={{ display: "grid", gridTemplateColumns: "300px 1fr", gap: 24 }}>
          {/* Form */}
          <div style={{ background: "#fff", borderRadius: 12, padding: 20, boxShadow: "0 1px 4px rgba(0,0,0,0.07)", height: "fit-content" }}>
            <div style={{ fontWeight: 600, color: NAVY, marginBottom: 16 }}>Requirements</div>

            {/* Region */}
            <label style={{ display: "block", fontSize: 12, color: "#556688", marginBottom: 4 }}>Region</label>
            <select value={form.region} onChange={set("region")} style={{ width: "100%", padding: "8px", borderRadius: 6, border: "1px solid #dde", fontSize: 13, marginBottom: 14 }}>
              {REGIONS.map(r => <option key={r}>{r}</option>)}
            </select>

            {/* Capacity */}
            <label style={{ display: "flex", justifyContent: "space-between", fontSize: 12, color: "#556688", marginBottom: 4 }}>
              Capacity (MW) <span style={{ fontWeight: 600, color: NAVY }}>{form.capacity_mw}</span>
            </label>
            <input type="range" min={1} max={200} step={1} value={form.capacity_mw} onChange={set("capacity_mw")} style={{ width: "100%", marginBottom: 14 }} />

            {/* Renewable */}
            <label style={{ display: "flex", justifyContent: "space-between", fontSize: 12, color: "#556688", marginBottom: 4 }}>
              Renewable target (%) <span style={{ fontWeight: 600, color: NAVY }}>{form.renewable_target_pct}%</span>
            </label>
            <input type="range" min={0} max={100} step={5} value={form.renewable_target_pct} onChange={set("renewable_target_pct")} style={{ width: "100%", marginBottom: 14 }} />

            {/* Budget */}
            <label style={{ display: "block", fontSize: 12, color: "#556688", marginBottom: 4 }}>Budget tier</label>
            <select value={form.budget_tier} onChange={set("budget_tier")} style={{ width: "100%", padding: "8px", borderRadius: 6, border: "1px solid #dde", fontSize: 13, marginBottom: 14 }}>
              {BUDGET_TIERS.map(b => <option key={b}>{b}</option>)}
            </select>

            {/* Priority */}
            <label style={{ display: "block", fontSize: 12, color: "#556688", marginBottom: 4 }}>Top priority</label>
            <select value={form.priority} onChange={set("priority")} style={{ width: "100%", padding: "8px", borderRadius: 6, border: "1px solid #dde", fontSize: 13, marginBottom: 20 }}>
              {PRIORITIES.map(p => <option key={p}>{p}</option>)}
            </select>

            <button
              onClick={run} disabled={loading}
              style={{
                width: "100%", padding: 10, borderRadius: 8, border: "none",
                background: loading ? "#8899bb" : TEAL, color: "#fff",
                fontWeight: 700, cursor: loading ? "not-allowed" : "pointer", fontSize: 14,
              }}
            >
              {loading ? "Agent running…" : "Run Site Scout"}
            </button>
            {error && <p style={{ color: "#cc0000", fontSize: 12, marginTop: 8 }}>{error}</p>}

            <button
              onClick={() => { localStorage.removeItem("anthropic_key"); setKeySet(false); setApiKey(""); }}
              style={{ marginTop: 10, width: "100%", padding: 8, borderRadius: 8, border: "1px solid #dde", background: "#fff", color: "#556688", cursor: "pointer", fontSize: 12 }}
            >
              Reset API Key
            </button>
          </div>

          {/* Report */}
          <div>
            {!result && !loading && (
              <div style={{ background: "#fff", borderRadius: 12, padding: 40, textAlign: "center", color: "#8899bb", boxShadow: "0 1px 4px rgba(0,0,0,0.07)" }}>
                Fill in requirements and click Run Site Scout.<br />
                <span style={{ fontSize: 12 }}>The agent will call 4 tools and produce a 6-section report (~20s).</span>
              </div>
            )}

            {loading && (
              <div style={{ background: "#fff", borderRadius: 12, padding: 40, textAlign: "center", color: "#8899bb" }}>
                <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 8 }}>Agent running…</div>
                Fetching gravity scores, benchmarking cities, writing structured report.
              </div>
            )}

            {result && (
              <>
                {/* Top city banner */}
                <div style={{
                  background: "#e0fff8", border: "1px solid #00c8c8", borderRadius: 10,
                  padding: "14px 20px", marginBottom: 16, display: "flex", alignItems: "center", gap: 12,
                }}>
                  <span style={{ fontSize: 22 }}>📍</span>
                  <div>
                    <div style={{ fontWeight: 700, color: NAVY }}>Top Recommended Site: {result.top_city}</div>
                    <div style={{ fontSize: 11, color: "#556688" }}>Tools used: {result.tools_used.join(", ")}</div>
                  </div>
                  <button onClick={downloadTxt} style={{
                    marginLeft: "auto", padding: "6px 14px", borderRadius: 6,
                    border: "1px solid #00c8c8", background: "#fff", color: TEAL,
                    fontWeight: 600, cursor: "pointer", fontSize: 12,
                  }}>
                    Download .txt
                  </button>
                </div>

                {/* Report */}
                <div style={{ background: "#fff", borderRadius: 12, padding: 24, boxShadow: "0 1px 4px rgba(0,0,0,0.07)" }}>
                  <div style={{ fontWeight: 700, color: NAVY, marginBottom: 12, fontSize: 15 }}>Site Recommendation Report</div>
                  {renderReport(result.report)}
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
