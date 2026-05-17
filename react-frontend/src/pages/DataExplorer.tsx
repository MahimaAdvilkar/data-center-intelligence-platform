import { useEffect, useState } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend } from "recharts";
import { getClusterSummary, type ClusterSummary } from "../api/client";

const NAVY  = "#0f1e46";
const TEAL  = "#00c8c8";
const COLORS = ["#0055cc", TEAL, "#7744cc"];
const LABELS: Record<number, string> = { 0: "Hyperscale", 1: "Mid-Tier", 2: "Edge/Colo" };

export default function DataExplorer() {
  const [clusters, setClusters] = useState<ClusterSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    getClusterSummary()
      .then(r => setClusters(r.data.clusters))
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div style={{ padding: 32, color: "#8899bb" }}>Loading…</div>;
  if (error)   return <div style={{ padding: 32, color: "#cc0000" }}>{error}</div>;

  const pieData = clusters.map(c => ({ name: LABELS[c.cluster] ?? `Cluster ${c.cluster}`, value: c.count }));

  return (
    <div style={{ padding: 32 }}>
      <h1 style={{ fontSize: 22, fontWeight: 700, color: NAVY, marginBottom: 4 }}>
        Data Explorer — US Dataset
      </h1>
      <p style={{ color: "#556688", fontSize: 13, marginBottom: 28 }}>
        203 data centers across 15 US states, clustered into 3 tiers via K-Means.
      </p>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20, marginBottom: 24 }}>
        {/* Distribution pie */}
        <div style={{ background: "#fff", borderRadius: 12, padding: 20, boxShadow: "0 1px 4px rgba(0,0,0,0.07)" }}>
          <div style={{ fontWeight: 600, color: NAVY, marginBottom: 12 }}>Cluster Distribution</div>
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} label>
                {pieData.map((_, i) => <Cell key={i} fill={COLORS[i]} />)}
              </Pie>
              <Legend />
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Avg PUE bar */}
        <div style={{ background: "#fff", borderRadius: 12, padding: 20, boxShadow: "0 1px 4px rgba(0,0,0,0.07)" }}>
          <div style={{ fontWeight: 600, color: NAVY, marginBottom: 12 }}>Average PUE by Cluster</div>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={clusters.map(c => ({ name: LABELS[c.cluster] ?? `C${c.cluster}`, pue: c.avg_pue }))}>
              <XAxis dataKey="name" tick={{ fontSize: 12 }} />
              <YAxis domain={[1, 2.5]} />
              <Tooltip formatter={(v) => typeof v === "number" ? v.toFixed(3) : v} />
              <Bar dataKey="pue" radius={[4, 4, 0, 0]}>
                {clusters.map((_, i) => <Cell key={i} fill={COLORS[i]} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Cluster summary table */}
      <div style={{ background: "#fff", borderRadius: 12, overflow: "hidden", boxShadow: "0 1px 4px rgba(0,0,0,0.07)" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
          <thead>
            <tr style={{ background: NAVY, color: "#fff" }}>
              {["Cluster", "Label", "Count", "Avg PUE", "Avg Energy (MW)", "Avg Area (sq ft)"].map(h => (
                <th key={h} style={{ padding: "10px 16px", textAlign: "left" }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {clusters.map((c, i) => (
              <tr key={c.cluster} style={{ background: i % 2 === 0 ? "#f4f6fb" : "#fff" }}>
                <td style={{ padding: "9px 16px" }}>
                  <span style={{
                    width: 12, height: 12, borderRadius: "50%",
                    background: COLORS[i], display: "inline-block", marginRight: 8,
                  }} />
                  {c.cluster}
                </td>
                <td style={{ padding: "9px 16px", fontWeight: 600, color: NAVY }}>{LABELS[c.cluster] ?? c.label}</td>
                <td style={{ padding: "9px 16px" }}>{c.count}</td>
                <td style={{ padding: "9px 16px", fontFamily: "monospace" }}>{c.avg_pue.toFixed(3)}</td>
                <td style={{ padding: "9px 16px", fontFamily: "monospace" }}>{c.avg_energy_mw.toFixed(1)}</td>
                <td style={{ padding: "9px 16px", fontFamily: "monospace" }}>{c.avg_area_sqft.toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
