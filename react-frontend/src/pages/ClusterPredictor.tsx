import { useState } from "react";
import { predictCluster, type ClusterPrediction } from "../api/client";

const NAVY = "#0f1e46";
const TEAL = "#00c8c8";

const FIELDS = [
  { key: "ENERGY_CAPACITY_MW",  label: "Energy capacity (MW)",   min: 1,   max: 500,    step: 1,   def: 50   },
  { key: "PUE",                 label: "PUE",                    min: 1.0, max: 3.0,    step: 0.05, def: 1.5  },
  { key: "TOTAL_AREA_SQFT",     label: "Total area (sq ft)",     min: 1000,max: 2000000, step: 1000, def: 100000},
  { key: "IXP_COUNT",           label: "IXP count (state)",      min: 0,   max: 30,     step: 1,   def: 5    },
  { key: "YEAR_OPERATIONAL",    label: "Year operational",       min: 1990, max: 2025,  step: 1,   def: 2015 },
  { key: "SERVICE_SCORE",       label: "Service score (0-8)",    min: 0,   max: 8,      step: 1,   def: 4    },
];

const CLUSTER_META: Record<number, { label: string; color: string; desc: string }> = {
  0: { label: "Hyperscale",       color: "#0055cc", desc: "Large-scale, high-energy, hyperscale operator" },
  1: { label: "Mid-Tier",         color: TEAL,      desc: "Regional enterprise, balanced spec" },
  2: { label: "Edge / Colo",      color: "#7744cc", desc: "Small, local edge or colocation facility" },
};

export default function ClusterPredictor() {
  const initFeatures = Object.fromEntries(FIELDS.map(f => [f.key, f.def]));
  const [features, setFeatures] = useState<Record<string, number>>(initFeatures);
  const [result, setResult] = useState<ClusterPrediction | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const predict = () => {
    setLoading(true);
    setError("");
    predictCluster(features)
      .then(r => setResult(r.data))
      .catch(e => setError(e.response?.data?.detail ?? e.message))
      .finally(() => setLoading(false));
  };

  const meta = result ? CLUSTER_META[result.cluster] : null;

  return (
    <div style={{ padding: 32 }}>
      <h1 style={{ fontSize: 22, fontWeight: 700, color: NAVY, marginBottom: 4 }}>
        Cluster Predictor
      </h1>
      <p style={{ color: "#556688", fontSize: 13, marginBottom: 28 }}>
        Predict whether a data center spec maps to Hyperscale, Mid-Tier, or Edge using the Random Forest model (95% accuracy).
      </p>

      <div style={{ display: "grid", gridTemplateColumns: "320px 1fr", gap: 24 }}>
        {/* Inputs */}
        <div style={{ background: "#fff", borderRadius: 12, padding: 20, boxShadow: "0 1px 4px rgba(0,0,0,0.07)", height: "fit-content" }}>
          <div style={{ fontWeight: 600, color: NAVY, marginBottom: 16 }}>Facility Specification</div>
          {FIELDS.map(f => (
            <div key={f.key} style={{ marginBottom: 14 }}>
              <label style={{ display: "flex", justifyContent: "space-between", fontSize: 12, color: "#556688", marginBottom: 4 }}>
                {f.label}
                <span style={{ fontWeight: 600, color: NAVY }}>{features[f.key]}</span>
              </label>
              <input
                type="range" min={f.min} max={f.max} step={f.step}
                value={features[f.key]}
                onChange={e => setFeatures(p => ({ ...p, [f.key]: Number(e.target.value) }))}
                style={{ width: "100%" }}
              />
            </div>
          ))}
          <button
            onClick={predict}
            disabled={loading}
            style={{
              width: "100%", padding: 10, borderRadius: 8, border: "none",
              background: loading ? "#8899bb" : TEAL, color: "#fff",
              fontWeight: 600, cursor: loading ? "not-allowed" : "pointer",
            }}
          >
            {loading ? "Predicting…" : "Predict Cluster"}
          </button>
          {error && <p style={{ color: "#cc0000", fontSize: 12, marginTop: 8 }}>{error}</p>}
        </div>

        {/* Result */}
        <div>
          {!result && !loading && (
            <div style={{
              background: "#fff", borderRadius: 12, padding: 40,
              textAlign: "center", color: "#8899bb", boxShadow: "0 1px 4px rgba(0,0,0,0.07)",
            }}>
              Adjust parameters and click Predict Cluster.
            </div>
          )}

          {result && meta && (
            <div style={{ background: "#fff", borderRadius: 12, padding: 28, boxShadow: "0 1px 4px rgba(0,0,0,0.07)" }}>
              {/* Cluster badge */}
              <div style={{ textAlign: "center", marginBottom: 28 }}>
                <div style={{
                  display: "inline-block", padding: "10px 28px", borderRadius: 24,
                  background: meta.color, color: "#fff", fontSize: 22, fontWeight: 800,
                }}>
                  {meta.label}
                </div>
                <p style={{ color: "#556688", fontSize: 13, marginTop: 12 }}>{meta.desc}</p>
              </div>

              {/* Probability bars */}
              <div style={{ fontWeight: 600, color: NAVY, marginBottom: 12 }}>Class Probabilities</div>
              {Object.entries(result.probabilities).map(([k, v]) => (
                <div key={k} style={{ marginBottom: 10 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, marginBottom: 4 }}>
                    <span style={{ color: "#334466" }}>{CLUSTER_META[Number(k)]?.label ?? k}</span>
                    <span style={{ fontWeight: 600 }}>{(v * 100).toFixed(1)}%</span>
                  </div>
                  <div style={{ background: "#eee", borderRadius: 4, height: 8 }}>
                    <div style={{
                      width: `${v * 100}%`, height: 8, borderRadius: 4,
                      background: CLUSTER_META[Number(k)]?.color ?? "#888",
                      transition: "width 0.4s",
                    }} />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
