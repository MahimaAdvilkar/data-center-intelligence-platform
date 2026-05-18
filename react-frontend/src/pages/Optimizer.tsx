import { useState } from "react";
import { ScatterChart, Scatter, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import { runOptimization, type OptimizationResult } from "../api/client";

const NAVY = "#0f1e46";
const TEAL = "#00c8c8";

export default function Optimizer() {
  const [params, setParams] = useState({ capacity_mw: 50, max_pue: 1.5, min_area_sqft: 50000, generations: 100 });
  const [result, setResult] = useState<OptimizationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const run = () => {
    setLoading(true);
    setError("");
    runOptimization(params)
      .then(r => setResult(r.data))
      .catch(e => setError(e.response?.data?.detail ?? e.message))
      .finally(() => setLoading(false));
  };

  const field = (label: string, key: keyof typeof params, min: number, max: number, step: number) => (
    <div style={{ marginBottom: 16 }}>
      <label style={{ display: "block", fontSize: 12, color: "#556688", marginBottom: 4 }}>{label}</label>
      <input
        type="range" min={min} max={max} step={step}
        value={params[key]}
        onChange={e => setParams(p => ({ ...p, [key]: Number(e.target.value) }))}
        style={{ width: "100%" }}
      />
      <span style={{ fontSize: 13, color: NAVY, fontWeight: 600 }}>{params[key]}</span>
    </div>
  );

  return (
    <div style={{ padding: 32 }}>
      <h1 style={{ fontSize: 22, fontWeight: 700, color: NAVY, marginBottom: 4 }}>
        NSGA-II Multi-Objective Optimizer
      </h1>
      <p style={{ color: "#556688", fontSize: 13, marginBottom: 28 }}>
        Evolves a Pareto-optimal set of data center configurations balancing PUE, energy, and footprint.
      </p>

      <div style={{ display: "grid", gridTemplateColumns: "280px 1fr", gap: 24 }}>
        {/* Controls */}
        <div style={{ background: "#fff", borderRadius: 12, padding: 20, boxShadow: "0 1px 4px rgba(0,0,0,0.07)", height: "fit-content" }}>
          <div style={{ fontWeight: 600, color: NAVY, marginBottom: 16 }}>Parameters</div>
          {field("Required capacity (MW)", "capacity_mw", 5, 200, 5)}
          {field("Max PUE target", "max_pue", 1.1, 2.5, 0.05)}
          {field("Min area (sq ft)", "min_area_sqft", 10000, 500000, 10000)}
          {field("Generations", "generations", 20, 300, 10)}
          <button
            onClick={run}
            disabled={loading}
            style={{
              width: "100%", padding: "10px", borderRadius: 8, border: "none",
              background: loading ? "#8899bb" : TEAL, color: "#fff",
              fontWeight: 600, cursor: loading ? "not-allowed" : "pointer", fontSize: 14,
            }}
          >
            {loading ? "Running…" : "Run Optimization"}
          </button>
          {error && <p style={{ color: "#cc0000", fontSize: 12, marginTop: 8 }}>{error}</p>}
        </div>

        {/* Results */}
        <div>
          {!result && !loading && (
            <div style={{
              background: "#fff", borderRadius: 12, padding: 40,
              textAlign: "center", color: "#8899bb", boxShadow: "0 1px 4px rgba(0,0,0,0.07)",
            }}>
              Set parameters and click Run Optimization to see the Pareto front.
            </div>
          )}

          {loading && (
            <div style={{ background: "#fff", borderRadius: 12, padding: 40, textAlign: "center", color: "#8899bb" }}>
              Running {params.generations} generations…
            </div>
          )}

          {result && (() => {
            const best = result.best_solution;
            const front = result.pareto_front ?? [];
            if (!best) {
              return (
                <div style={{ background: "#fff", borderRadius: 12, padding: 40, textAlign: "center", color: "#cc0000", boxShadow: "0 1px 4px rgba(0,0,0,0.07)" }}>
                  Backend returned an unexpected response. Railway may still be deploying — try again in 30 seconds.
                </div>
              );
            }
            return (
              <>
                {/* Best solution */}
                <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12, marginBottom: 20 }}>
                  {[
                    { label: "Best PUE",     value: best.pue?.toFixed(3) ?? "—" },
                    { label: "Energy (MW)",  value: best.energy_mw?.toFixed(1) ?? "—" },
                    { label: "Area (sq ft)", value: best.area_sqft?.toLocaleString() ?? "—" },
                  ].map(c => (
                    <div key={c.label} style={{
                      background: "#fff", borderRadius: 10, padding: 16,
                      boxShadow: "0 1px 4px rgba(0,0,0,0.07)", borderTop: `3px solid ${TEAL}`,
                    }}>
                      <div style={{ fontSize: 22, fontWeight: 800, color: NAVY }}>{c.value}</div>
                      <div style={{ fontSize: 12, color: "#556688", marginTop: 4 }}>{c.label}</div>
                    </div>
                  ))}
                </div>

                {/* Pareto scatter */}
                <div style={{ background: "#fff", borderRadius: 12, padding: 20, boxShadow: "0 1px 4px rgba(0,0,0,0.07)" }}>
                  <div style={{ fontWeight: 600, color: NAVY, marginBottom: 12 }}>
                    Pareto Front — PUE vs Energy ({front.length} solutions)
                  </div>
                  <ResponsiveContainer width="100%" height={280}>
                    <ScatterChart>
                      <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
                      <XAxis dataKey="energy_mw" name="Energy (MW)" label={{ value: "Energy (MW)", position: "bottom", fontSize: 12 }} />
                      <YAxis dataKey="pue" name="PUE" domain={[1, "auto"]} label={{ value: "PUE", angle: -90, position: "left", fontSize: 12 }} />
                      <Tooltip cursor={{ strokeDasharray: "3 3" }} />
                      <Scatter data={front} fill={TEAL} opacity={0.7} />
                    </ScatterChart>
                  </ResponsiveContainer>
                </div>
              </>
            );
          })()}
        </div>
      </div>
    </div>
  );
}
