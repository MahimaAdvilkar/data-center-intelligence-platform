import { useState, useRef, useEffect } from "react";
import { sendChat } from "../api/client";

const NAVY = "#0f1e46";
const TEAL = "#00c8c8";

interface Message { role: "user" | "assistant"; content: string; tools?: string[] }

export default function AIChat() {
  const [apiKey, setApiKey] = useState(localStorage.getItem("anthropic_key") ?? "");
  const [keySet, setKeySet] = useState(!!localStorage.getItem("anthropic_key"));
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  const activateKey = () => {
    localStorage.setItem("anthropic_key", apiKey);
    setKeySet(true);
  };

  const send = async () => {
    if (!input.trim() || loading) return;
    const userMsg: Message = { role: "user", content: input };
    setMessages(prev => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    const history = messages.map(m => ({ role: m.role, content: m.content }));

    try {
      const r = await sendChat(input, history, apiKey);
      setMessages(prev => [...prev, {
        role: "assistant",
        content: r.data.response,
        tools: r.data.tools_used,
      }]);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Error";
      setMessages(prev => [...prev, { role: "assistant", content: `Error: ${msg}` }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: 32, display: "flex", flexDirection: "column", height: "calc(100vh - 0px)" }}>
      <h1 style={{ fontSize: 22, fontWeight: 700, color: NAVY, marginBottom: 4 }}>
        AI Analyst
      </h1>
      <p style={{ color: "#556688", fontSize: 13, marginBottom: 20 }}>
        Conversational AI with live access to gravity scores, cluster data, and dataset stats.
      </p>

      {/* API key setup */}
      {!keySet && (
        <div style={{ background: "#fff", borderRadius: 12, padding: 20, marginBottom: 20, boxShadow: "0 1px 4px rgba(0,0,0,0.07)" }}>
          <div style={{ fontWeight: 600, color: NAVY, marginBottom: 10 }}>Enter Anthropic API Key</div>
          <div style={{ display: "flex", gap: 10 }}>
            <input
              type="password"
              value={apiKey}
              onChange={e => setApiKey(e.target.value)}
              placeholder="sk-ant-…"
              style={{ flex: 1, padding: "8px 12px", borderRadius: 8, border: "1px solid #dde", fontSize: 13 }}
            />
            <button
              onClick={activateKey}
              disabled={!apiKey}
              style={{ padding: "8px 18px", borderRadius: 8, border: "none", background: TEAL, color: "#fff", fontWeight: 600, cursor: "pointer" }}
            >
              Activate
            </button>
          </div>
        </div>
      )}

      {keySet && (
        <>
          {/* Chat window */}
          <div style={{
            flex: 1, background: "#fff", borderRadius: 12, padding: 20,
            boxShadow: "0 1px 4px rgba(0,0,0,0.07)", overflowY: "auto",
            minHeight: 300, maxHeight: "calc(100vh - 320px)", marginBottom: 16,
          }}>
            {messages.length === 0 && (
              <p style={{ color: "#8899bb", fontSize: 13 }}>
                Ask anything — "Which Indian city should I pick for 50 MW?", "What's the average PUE of hyperscale DCs?", "Compare Mumbai and Hyderabad."
              </p>
            )}
            {messages.map((m, i) => (
              <div key={i} style={{ marginBottom: 16 }}>
                <div style={{
                  display: "inline-block", padding: "8px 14px", borderRadius: 10,
                  background: m.role === "user" ? TEAL : "#f4f6fb",
                  color: m.role === "user" ? "#fff" : NAVY,
                  maxWidth: "80%", fontSize: 13, lineHeight: 1.6,
                  float: m.role === "user" ? "right" : "left",
                  clear: "both",
                }}>
                  <div style={{ whiteSpace: "pre-wrap" }}>{m.content}</div>
                  {m.tools && m.tools.length > 0 && (
                    <div style={{ fontSize: 10, color: "#8899bb", marginTop: 6 }}>
                      Tools: {m.tools.join(", ")}
                    </div>
                  )}
                </div>
                <div style={{ clear: "both" }} />
              </div>
            ))}
            {loading && (
              <div style={{ color: "#8899bb", fontSize: 13, fontStyle: "italic" }}>Thinking…</div>
            )}
            <div ref={bottomRef} />
          </div>

          {/* Input */}
          <div style={{ display: "flex", gap: 10 }}>
            <input
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === "Enter" && send()}
              placeholder="Ask about data centers…"
              style={{ flex: 1, padding: "10px 14px", borderRadius: 8, border: "1px solid #dde", fontSize: 13 }}
            />
            <button
              onClick={send}
              disabled={loading || !input.trim()}
              style={{
                padding: "10px 20px", borderRadius: 8, border: "none",
                background: loading ? "#8899bb" : TEAL, color: "#fff",
                fontWeight: 600, cursor: loading ? "not-allowed" : "pointer",
              }}
            >
              Send
            </button>
            <button
              onClick={() => { localStorage.removeItem("anthropic_key"); setKeySet(false); setApiKey(""); setMessages([]); }}
              style={{ padding: "10px 14px", borderRadius: 8, border: "1px solid #dde", background: "#fff", color: "#556688", cursor: "pointer", fontSize: 12 }}
            >
              Reset Key
            </button>
          </div>
        </>
      )}
    </div>
  );
}
