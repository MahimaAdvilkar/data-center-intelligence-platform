import { useEffect, useState } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { getGravityScores, type GravityScore } from "../api/client";

const TEAL  = "#00c8c8";
const NAVY  = "#0f1e46";
const LGREY = "#f4f6fb";

export default function GravityModel() {
  const [scores, setScores] = useState<GravityScore[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    getGravityScores(13)
      .then(r => setScores(r.data?.scores ?? []))
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div style={{ padding: 32 }}>
      <h1 style={{ fontSize: 22, fontWeight: 700, color: NAVY, marginBottom: 4 }}>
        Site Finder — India Gravity Model
      </h1>
      <p style={{ color: "#556688", fontSize: 13, marginBottom: 28 }}>
        13 Indian cities ranked by composite gravity score (infrastructure, power, connectivity, cost, renewables).
      </p>

      {loading && <p style={{ color: "#8899bb" }}>Loading scores…</p>}
      {error   && <p style={{ color: "#cc0000" }}>{error}</p>}

      {!loading && !error && (
        <>
          {/* Bar chart */}
          <div style={{ background: "#fff", borderRadius: 12, padding: 24, marginBottom: 24, boxShadow: "0 1px 4px rgba(0,0,0,0.07)" }}>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={scores} layout="vertical" margin={{ left: 20 }}>
                <XAxis type="number" domain={[0, 1]} tickFormatter={v => v.toFixed(2)} />
                <YAxis type="category" dataKey="city" width={90} tick={{ fontSize: 12 }} />
                <Tooltip formatter={(v) => typeof v === "number" ? v.toFixed(4) : v} />
                <Bar dataKey="score" radius={[0, 4, 4, 0]}>
                  {scores.map((_, i) => (
                    <Cell key={i} fill={i === 0 ? TEAL : i < 3 ? "#3399cc" : "#8899bb"} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Table */}
          <div style={{ background: "#fff", borderRadius: 12, overflow: "hidden", boxShadow: "0 1px 4px rgba(0,0,0,0.07)" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead>
                <tr style={{ background: NAVY, color: "#fff" }}>
                  <th style={{ padding: "10px 16px", textAlign: "left" }}>Rank</th>
                  <th style={{ padding: "10px 16px", textAlign: "left" }}>City</th>
                  <th style={{ padding: "10px 16px", textAlign: "right" }}>Gravity Score</th>
                  <th style={{ padding: "10px 16px", textAlign: "left" }}>Rating</th>
                </tr>
              </thead>
              <tbody>
                {scores.map((s, i) => (
                  <tr key={s.city} style={{ background: i % 2 === 0 ? LGREY : "#fff" }}>
                    <td style={{ padding: "9px 16px", color: i === 0 ? TEAL : "#334466", fontWeight: i === 0 ? 700 : 400 }}>
                      {s.rank}
                    </td>
                    <td style={{ padding: "9px 16px", fontWeight: i < 3 ? 600 : 400, color: NAVY }}>
                      {s.city}
                    </td>
                    <td style={{ padding: "9px 16px", textAlign: "right", fontFamily: "monospace" }}>
                      {s.score.toFixed(4)}
                    </td>
                    <td style={{ padding: "9px 16px" }}>
                      <span style={{
                        padding: "2px 8px", borderRadius: 10, fontSize: 11,
                        background: i === 0 ? "#e0fff8" : i < 3 ? "#e8f4ff" : "#f0f0f0",
                        color: i === 0 ? "#007777" : i < 3 ? "#0055aa" : "#667788",
                      }}>
                        {i === 0 ? "Top Pick" : i < 3 ? "Strong" : i < 6 ? "Good" : "Consider"}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
