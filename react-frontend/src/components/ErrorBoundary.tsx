import { Component, type ReactNode } from "react";

interface Props { children: ReactNode }
interface State { hasError: boolean; message: string }

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, message: "" };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, message: error.message };
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: 40, textAlign: "center" }}>
          <div style={{ fontSize: 32, marginBottom: 12 }}>⚠️</div>
          <div style={{ fontWeight: 700, color: "#0f1e46", marginBottom: 8 }}>
            Something went wrong
          </div>
          <div style={{ color: "#556688", fontSize: 13, marginBottom: 20 }}>
            {this.state.message}
          </div>
          <button
            onClick={() => this.setState({ hasError: false, message: "" })}
            style={{
              padding: "8px 20px", borderRadius: 8, border: "none",
              background: "#00c8c8", color: "#fff", fontWeight: 600, cursor: "pointer",
            }}
          >
            Try again
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
