import { Send } from "lucide-react";
import { useState } from "react";
import ReactMarkdown from "react-markdown";
import { chatCode } from "../api";

export default function ChatPanel({ code, language }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage = { role: "user", content: input };
    const newMessages = [...messages, userMessage];
    setMessages(newMessages);
    setInput("");
    setIsLoading(true);

    try {
      const response = await chatCode(code, language, newMessages);
      setMessages([...newMessages, { role: "assistant", content: response.reply }]);
    } catch (err) {
      setMessages([
        ...newMessages,
        { role: "assistant", content: `**Error:** ${err.message}` },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="panel-content" style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <div style={{ flex: 1, overflowY: "auto", paddingBottom: 16 }}>
        {messages.length === 0 ? (
          <div className="empty-state">
            <p>Ask a question about the code!</p>
          </div>
        ) : (
          messages.map((msg, i) => (
            <div
              key={i}
              style={{
                marginBottom: 16,
                padding: "8px 12px",
                borderRadius: 8,
                backgroundColor: msg.role === "user" ? "var(--surface-hover)" : "var(--surface)",
                border: msg.role === "assistant" ? "1px solid var(--border)" : "none",
                color: msg.role === "user" ? "var(--ink)" : "var(--ink-secondary)",
              }}
            >
              <span style={{ fontWeight: 600, fontSize: 11, textTransform: "uppercase", color: "var(--ink-faint)", marginBottom: 4, display: "block" }}>
                {msg.role === "user" ? "You" : "AI"}
              </span>
              <div className="markdown-body" style={{ fontSize: 13 }}>
                <ReactMarkdown>{msg.content}</ReactMarkdown>
              </div>
            </div>
          ))
        )}
        {isLoading && (
          <div style={{ fontStyle: "italic", color: "var(--ink-faint)", fontSize: 12 }}>
            Thinking...
          </div>
        )}
      </div>
      <div style={{ display: "flex", gap: 8, marginTop: "auto", borderTop: "1px solid var(--border)", paddingTop: 12 }}>
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask something..."
          style={{
            flex: 1,
            resize: "none",
            height: 40,
            padding: "8px 12px",
            borderRadius: 6,
            border: "1px solid var(--border)",
            backgroundColor: "var(--surface)",
            color: "var(--ink)",
            fontFamily: "inherit",
          }}
        />
        <button
          onClick={handleSend}
          disabled={!input.trim() || isLoading}
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "0 16px",
            borderRadius: 6,
            backgroundColor: "var(--brand)",
            color: "var(--bg)",
            border: "none",
            cursor: "pointer",
            opacity: input.trim() && !isLoading ? 1 : 0.5,
          }}
        >
          <Send size={16} />
        </button>
      </div>
    </div>
  );
}
