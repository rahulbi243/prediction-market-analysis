"use client";

import { useState, useRef, useEffect } from "react";
import { Send, Lightbulb, CheckCircle2 } from "lucide-react";
import { sendChatMessage, type ChatMessage, type ChatResponse } from "@/lib/api";

const SUGGESTED_PROMPTS = [
  "Why is there a difference in accuracy across domains?",
  "Which failure mode is most common in Finance?",
  "How does news context affect forecast quality?",
];

export default function ChatInterface() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = async (text: string) => {
    if (!text.trim() || loading) return;
    const userMsg: ChatMessage = { role: "user", content: text.trim() };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const history = [...messages, userMsg].map((m) => ({ role: m.role, content: m.content }));
      const resp: ChatResponse = await sendChatMessage(text.trim(), history);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: resp.answer, sparql: resp.sparql_query || undefined, raw_results: resp.raw_results },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Sorry, I couldn't process that request. Make sure the backend is running." },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Messages area */}
      <div className="flex-1 overflow-auto px-6 py-8">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full">
            <div
              className="w-16 h-16 rounded-2xl flex items-center justify-center mb-4"
              style={{ background: "var(--accent)" }}
            >
              <Lightbulb size={28} color="#fff" />
            </div>
            <h2 className="text-lg font-semibold mb-1" style={{ color: "var(--text-primary)" }}>
              AI Hypothesis Assistant
            </h2>
            <p className="text-sm mb-8 text-center max-w-md" style={{ color: "var(--text-muted)" }}>
              Ask questions about prediction markets, forecast accuracy, and get AI-powered root cause hypotheses based on the knowledge graph.
            </p>
            <div className="flex flex-wrap gap-2 justify-center max-w-lg">
              {SUGGESTED_PROMPTS.map((p) => (
                <button
                  key={p}
                  onClick={() => send(p)}
                  className="px-4 py-2 text-xs rounded-full border transition-colors cursor-pointer"
                  style={{ borderColor: "var(--border)", color: "var(--text-secondary)", background: "var(--bg-secondary)" }}
                >
                  {p}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="max-w-2xl mx-auto space-y-4">
            {messages.map((msg, i) => (
              <div
                key={i}
                className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
              >
                <div
                  className="max-w-[80%] px-4 py-3 rounded-2xl text-sm"
                  style={{
                    background: msg.role === "user" ? "var(--accent)" : "var(--bg-secondary)",
                    color: msg.role === "user" ? "#fff" : "var(--text-primary)",
                    border: msg.role === "assistant" ? "1px solid var(--border)" : "none",
                  }}
                >
                  <p className="whitespace-pre-wrap">{msg.content}</p>
                  {msg.sparql && (
                    <details className="mt-2">
                      <summary className="text-xs cursor-pointer opacity-70">SPARQL Query</summary>
                      <pre className="mt-1 text-[10px] font-mono p-2 rounded overflow-x-auto" style={{ background: "#1e293b", color: "#e2e8f0" }}>
                        {msg.sparql}
                      </pre>
                    </details>
                  )}
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex justify-start">
                <div className="px-4 py-3 rounded-2xl text-sm" style={{ background: "var(--bg-secondary)", border: "1px solid var(--border)" }}>
                  <span className="animate-pulse" style={{ color: "var(--text-muted)" }}>Thinking...</span>
                </div>
              </div>
            )}
            <div ref={endRef} />
          </div>
        )}
      </div>

      {/* Action buttons + input */}
      <div className="border-t px-6 py-4 space-y-3" style={{ borderColor: "var(--border)", background: "var(--bg-secondary)" }}>
        <div className="flex justify-center gap-3">
          <button
            onClick={() => send("Generate hypotheses about forecast accuracy patterns")}
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-medium cursor-pointer"
            style={{ background: "var(--accent)", color: "#fff" }}
          >
            <Lightbulb size={16} />
            Generate Hypotheses
          </button>
          <button
            onClick={() => send("Validate existing hypotheses about domain-stratified accuracy")}
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-medium border cursor-pointer"
            style={{ borderColor: "var(--accent)", color: "var(--accent)", background: "transparent" }}
          >
            <CheckCircle2 size={16} />
            Validate Existing
          </button>
        </div>
        <div className="flex items-center gap-2 max-w-2xl mx-auto">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && send(input)}
            placeholder="Ask about network alarms, root causes, or request hypothesis generation..."
            className="flex-1 px-4 py-3 rounded-xl text-sm border outline-none"
            style={{ borderColor: "var(--border)", background: "var(--bg-primary)", color: "var(--text-primary)" }}
          />
          <button
            onClick={() => send(input)}
            disabled={!input.trim() || loading}
            className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0 cursor-pointer"
            style={{ background: "var(--accent)", color: "#fff", opacity: !input.trim() || loading ? 0.5 : 1 }}
          >
            <Send size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}
