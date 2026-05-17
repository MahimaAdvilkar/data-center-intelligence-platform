import { NavLink, Outlet } from "react-router-dom";
import { Building2, Map, Zap, Cpu, BarChart3, MessageSquare, Radar } from "lucide-react";
import ErrorBoundary from "./ErrorBoundary";
import BackendStatus from "./BackendStatus";

const NAV = [
  { to: "/",          label: "Overview",      icon: Building2 },
  { to: "/gravity",   label: "Site Finder",   icon: Map },
  { to: "/optimizer", label: "Optimizer",     icon: Zap },
  { to: "/cluster",   label: "Cluster",       icon: Cpu },
  { to: "/explorer",  label: "Data Explorer", icon: BarChart3 },
  { to: "/ai",        label: "AI Analyst",    icon: MessageSquare },
  { to: "/scout",     label: "Site Scout",    icon: Radar },
];

export default function Layout() {
  return (
    <div style={{ display: "flex", minHeight: "100vh", fontFamily: "Inter, sans-serif" }}>
      {/* Sidebar */}
      <aside style={{
        width: 220, background: "#0f1e46", color: "#fff",
        display: "flex", flexDirection: "column", padding: "24px 0",
        flexShrink: 0,
      }}>
        <div style={{ padding: "0 20px 24px", borderBottom: "1px solid #1e3a7a" }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: "#00c8c8", letterSpacing: 1 }}>
            DC INTELLIGENCE
          </div>
          <div style={{ fontSize: 11, color: "#8899bb", marginTop: 4 }}>
            AI-Powered Platform
          </div>
        </div>
        <nav style={{ flex: 1, padding: "16px 0" }}>
          {NAV.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              style={({ isActive }) => ({
                display: "flex", alignItems: "center", gap: 10,
                padding: "10px 20px", textDecoration: "none",
                color: isActive ? "#00c8c8" : "#c0d0e8",
                background: isActive ? "rgba(0,200,200,0.08)" : "transparent",
                borderLeft: isActive ? "3px solid #00c8c8" : "3px solid transparent",
                fontSize: 13, fontWeight: isActive ? 600 : 400,
                transition: "all 0.15s",
              })}
            >
              <Icon size={16} />
              {label}
            </NavLink>
          ))}
        </nav>
        <div style={{ padding: "16px 20px", fontSize: 10, color: "#556688" }}>
          Capstone → Production<br />Phase 3 · Claude-Sonnet-4-6
        </div>
      </aside>

      {/* Main content */}
      <main style={{ flex: 1, background: "#f4f6fb", overflow: "auto" }}>
        <BackendStatus />
        <ErrorBoundary>
          <Outlet />
        </ErrorBoundary>
      </main>
    </div>
  );
}
