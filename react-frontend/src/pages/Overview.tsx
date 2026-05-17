import { useEffect, useState } from "react";
import { api } from "../api/client";

interface HealthData { status: string; version: string }

const STAT_CARDS = [
  { label: "US Data Centers", value: "203", sub: "15 states" },
  { label: "Indian Cities Scored", value: "13", sub: "Gravity model" },
  { label: "ML Accuracy", value: "95%", sub: "Random Forest" },
  { label: "Cluster Tiers", value: "3", sub: "K-Means" },
];

export default function Overview() {
  const [health, setHealth] = useState<HealthData | null>(null);
  const [err, setErr] = useState(false);

  useEffect(() => {
    api.get<HealthData>("/health")
      .then(r => setHealth(r.data))
      .catch(() => setErr(true));
  }, []);

  return (
    <div style={{ padding: 32 }}>
      <h1 style={{ fontSize: 26, fontWeight: 700, color: "#0f1e46", marginBottom: 4 }}>
        Data Center Intelligence Platform
      </h1>
      <p style={{ color: "#556688", marginBottom: 32, fontSize: 14 }}>
        AI-powered site selection, multi-objective optimization, and cluster prediction for data center expansion.
      </p>

      {/* API status */}
      <div style={{
        display: "inline-flex", alignItems: "center", gap: 8,
        padding: "6px 14px", borderRadius: 20, marginBottom: 32,
        background: err ? "#fff0f0" : "#f0fff8",
        border: `1px solid ${err ? "#ffaaaa" : "#00c8c8"}`,
        fontSize: 13, color: err ? "#cc0000" : "#007777",
      }}>
        <span style={{
          width: 8, height: 8, borderRadius: "50%",
          background: err ? "#cc0000" : "#00c870", display: "inline-block",
        }} />
        {err ? "API offline — start FastAPI backend" : `API online · v${health?.version ?? "…"}`}
      </div>

      {/* Stat cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16, marginBottom: 40 }}>
        {STAT_CARDS.map(c => (
          <div key={c.label} style={{
            background: "#fff", borderRadius: 12, padding: 20,
            boxShadow: "0 1px 4px rgba(0,0,0,0.07)",
          }}>
            <div style={{ fontSize: 32, fontWeight: 800, color: "#0f1e46" }}>{c.value}</div>
            <div style={{ fontSize: 13, fontWeight: 600, color: "#334466", marginTop: 4 }}>{c.label}</div>
            <div style={{ fontSize: 11, color: "#8899bb", marginTop: 2 }}>{c.sub}</div>
          </div>
        ))}
      </div>

      {/* Feature summary */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
        {[
          {
            title: "Gravity Model — India Expansion",
            desc: "Weighted multi-parameter scoring across 13 Indian cities: infrastructure, power, connectivity, seismic risk, cost, and renewable energy availability.",
          },
          {
            title: "NSGA-II Optimizer",
            desc: "Multi-objective evolutionary algorithm balancing PUE efficiency, energy capacity, and facility footprint across Pareto-optimal solutions.",
          },
          {
            title: "K-Means Cluster Prediction",
            desc: "Random Forest classifier (95% accuracy) predicts Hyperscale, Mid-Tier, or Edge tier for any new data center specification.",
          },
          {
            title: "Site Scout Agent",
            desc: "Agentic Claude pipeline that takes your requirements, runs all models autonomously, and produces a structured 6-section site recommendation report.",
          },
        ].map(f => (
          <div key={f.title} style={{
            background: "#fff", borderRadius: 12, padding: 20,
            boxShadow: "0 1px 4px rgba(0,0,0,0.07)",
            borderTop: "3px solid #00c8c8",
          }}>
            <div style={{ fontWeight: 600, color: "#0f1e46", marginBottom: 8 }}>{f.title}</div>
            <div style={{ fontSize: 13, color: "#556688", lineHeight: 1.6 }}>{f.desc}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
