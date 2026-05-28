import { useState, useRef, useEffect } from "react";
import axios from "axios";

const API = "http://localhost:8000";

// Example questions to help users get started
const EXAMPLES = [
  "What deadlines are coming up?",
  "Summarise all client complaints",
  "Which emails mention invoice disputes?",
  "Find all cybersecurity risks mentioned",
  "What action items were assigned last month?",
];

export default function Query() {
  const [messages, setMessages] = useState([]);
  const [input, setInput]       = useState("");
  const [loading, setLoading]   = useState(false);
  const bottomRef               = useRef(null);

  // Auto-scroll to latest message
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const ask = async (question) => {
    if (!question.trim() || loading) return;

    // Add user message
    setMessages(prev => [...prev, { role: "user", text: question }]);
    setInput("");
    setLoading(true);

    try {
      const { data } = await axios.post(`${API}/query`, { question });
      setMessages(prev => [...prev, {
        role:    "assistant",
        text:    data.answer,
        sources: data.sources,
      }]);
    } catch (err) {
      const msg = err.response?.data?.detail ?? "Failed to get a response. Is the backend running?";
      setMessages(prev => [...prev, { role: "error", text: msg }]);
    } finally {
      setLoading(false);
    }
  };

  const handleKey = e => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      ask(input);
    }
  };

  return (
    <div className="query-page">
      {/* Header */}
      <div className="page-header">
        <div className="page-eyebrow">Semantic Search</div>
        <h1 className="page-title">Query documents</h1>
        <p className="page-desc">
          Ask natural language questions about your uploaded documents.
          Answers are grounded in source content with citations.
        </p>
      </div>

      {/* Chat area */}
      <div className="chat-area">
        {messages.length === 0 ? (
          <EmptyState onSelect={ask} />
        ) : (
          <div className="messages">
            {messages.map((m, i) => (
              <Message key={i} message={m} />
            ))}
            {loading && <ThinkingBubble />}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {/* Input bar */}
      <div className="input-bar">
        <textarea
          className="input chat-input"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKey}
          placeholder="Ask a question about your documents…"
          rows={1}
          disabled={loading}
        />
        <button
          className="btn btn-primary"
          onClick={() => ask(input)}
          disabled={loading || !input.trim()}
        >
          {loading ? <span className="spinner" /> : "Ask"}
        </button>
      </div>

      <style>{`
        .query-page {
          display: flex;
          flex-direction: column;
          height: calc(100vh - 96px);
        }
        .chat-area {
          flex: 1;
          overflow-y: auto;
          margin-bottom: 16px;
        }
        .messages {
          display: flex;
          flex-direction: column;
          gap: 20px;
          padding-bottom: 8px;
        }
        .input-bar {
          display: flex;
          gap: 10px;
          align-items: flex-end;
        }
        .chat-input {
          flex: 1;
          min-height: 44px;
          max-height: 140px;
          resize: none;
        }
      `}</style>
    </div>
  );
}

function EmptyState({ onSelect }) {
  return (
    <div className="empty-state">
      <div className="empty-icon">?</div>
      <div className="empty-title">Ask anything about your documents</div>
      <div className="empty-sub dim">Try one of these examples to get started</div>
      <div className="examples">
        {EXAMPLES.map(q => (
          <button key={q} className="example-btn" onClick={() => onSelect(q)}>
            {q}
          </button>
        ))}
      </div>
      <style>{`
        .empty-state {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          height: 100%;
          min-height: 320px;
          text-align: center;
          gap: 12px;
        }
        .empty-icon {
          width: 48px; height: 48px;
          border-radius: 50%;
          background: var(--bg3);
          border: 1px solid var(--line2);
          display: flex; align-items: center; justify-content: center;
          font-size: 20px; color: var(--muted);
          margin-bottom: 4px;
        }
        .empty-title { font-size: 16px; font-weight: 500; color: var(--text); }
        .empty-sub   { font-size: 13px; }
        .examples {
          display: flex; flex-wrap: wrap;
          gap: 8px; justify-content: center;
          max-width: 560px; margin-top: 8px;
        }
        .example-btn {
          background: var(--bg2);
          border: 1px solid var(--line2);
          border-radius: var(--r);
          padding: 7px 14px;
          color: var(--dim);
          font-size: 12px;
          cursor: pointer;
          transition: all 0.15s;
          font-family: var(--sans);
        }
        .example-btn:hover {
          border-color: var(--accent);
          color: var(--accent);
          background: rgba(200,184,154,0.04);
        }
      `}</style>
    </div>
  );
}

function Message({ message }) {
  const isUser      = message.role === "user";
  const isError     = message.role === "error";
  const isAssistant = message.role === "assistant";

  return (
    <div className={`msg-row ${isUser ? "user" : "assistant"}`}>
      <div className={`msg-bubble ${isError ? "error" : ""}`}>
        {isAssistant && (
          <div className="msg-label mono dim">Assistant</div>
        )}
        <div className="msg-text">{message.text}</div>
        {isAssistant && message.sources?.length > 0 && (
          <div className="msg-sources">
            <span className="dim mono" style={{ fontSize: 11 }}>Sources: </span>
            {message.sources.map(s => (
              <span key={s} className="badge badge-file mono" style={{ fontSize: 11 }}>{s}</span>
            ))}
          </div>
        )}
      </div>
      <style>{`
        .msg-row { display: flex; }
        .msg-row.user { justify-content: flex-end; }
        .msg-row.assistant { justify-content: flex-start; }
        .msg-bubble {
          max-width: 72%;
          padding: 14px 18px;
          border-radius: var(--r2);
          font-size: 14px;
          line-height: 1.65;
        }
        .msg-row.user .msg-bubble {
          background: var(--accent);
          color: var(--bg);
          border-bottom-right-radius: 2px;
        }
        .msg-row.assistant .msg-bubble {
          background: var(--bg2);
          border: 1px solid var(--line);
          color: var(--text);
          border-bottom-left-radius: 2px;
        }
        .msg-bubble.error {
          background: rgba(224,112,112,0.08);
          border-color: rgba(224,112,112,0.3);
          color: var(--danger);
        }
        .msg-label {
          font-size: 10px;
          letter-spacing: 0.1em;
          text-transform: uppercase;
          margin-bottom: 6px;
        }
        .msg-text { white-space: pre-wrap; }
        .msg-sources {
          margin-top: 12px;
          padding-top: 10px;
          border-top: 1px solid var(--line);
          display: flex;
          flex-wrap: wrap;
          align-items: center;
          gap: 6px;
        }
      `}</style>
    </div>
  );
}

function ThinkingBubble() {
  return (
    <div className="msg-row assistant">
      <div className="msg-bubble thinking">
        <span /><span /><span />
      </div>
      <style>{`
        .thinking {
          background: var(--bg2);
          border: 1px solid var(--line);
          display: flex; gap: 5px; align-items: center;
          padding: 16px 20px;
        }
        .thinking span {
          width: 6px; height: 6px;
          border-radius: 50%;
          background: var(--muted);
          animation: bounce 1.2s infinite;
        }
        .thinking span:nth-child(2) { animation-delay: 0.2s; }
        .thinking span:nth-child(3) { animation-delay: 0.4s; }
        @keyframes bounce {
          0%,80%,100% { transform: translateY(0); }
          40% { transform: translateY(-5px); }
        }
      `}</style>
    </div>
  );
}
