import { useEffect, useState } from "react";
import { api } from "../api/client";

type Status = "checking" | "online" | "waking" | "offline";

export default function BackendStatus() {
  const [status, setStatus] = useState<Status>("checking");

  useEffect(() => {
    const start = Date.now();
    const timer = setTimeout(() => setStatus("waking"), 3000);

    api.get("/health", { timeout: 30_000 })
      .then(() => {
        clearTimeout(timer);
        setStatus("online");
        // Hide banner after 2s if online fast
        if (Date.now() - start < 2000) setTimeout(() => setStatus("online"), 2000);
      })
      .catch(() => {
        clearTimeout(timer);
        setStatus("offline");
      });

    return () => clearTimeout(timer);
  }, []);

  if (status === "online" || status === "checking") return null;

  const config = {
    waking:  { bg: "#fff8e1", border: "#f59e0b", color: "#92400e", text: "⏳  Backend is waking up on Railway (free tier cold start ~20s) — data will load shortly." },
    offline: { bg: "#fff0f0", border: "#f87171", color: "#991b1b", text: "❌  Cannot reach backend. Check that Railway is running and VITE_API_URL is set correctly." },
  }[status];

  return (
    <div style={{
      background: config.bg, border: `1px solid ${config.border}`,
      borderRadius: 8, padding: "10px 16px", margin: "16px 24px 0",
      fontSize: 13, color: config.color, lineHeight: 1.5,
    }}>
      {config.text}
    </div>
  );
}
