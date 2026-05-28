import { useState } from "react";
import axios from "axios";

const API = "http://localhost:8000";

// Parses the ## Section\n content format from GPT
function parseSections(text) {
  const sections = [];
  const lines = text.split("\n");
  let current = null;

  for (const line of lines) {
    if (line.startsWith("## ")) {
      if (current) sections.push(current);
      current = { title: line.replace("## ", "").trim(), lines: [] };
    } else if (current) {
      const trimmed = line.trim();
      if (trimmed) current.lines.push(trimmed);
    }
  }
  if (current) sections.push(current);

  // If no ## sections found, return raw text as one block
  if (sections.length === 0) {
    return [{ title: "Summary", lines: text.split("\n").filter(l => l.trim()) }];
  }
  return sections;
}

const SECTION_ICONS = {
  "Key Deadlines":    "◷",
  "Action Items":     "✓",
  "Risks & Concerns": "⚑",
  "Overall Sentiment":"◈",
};

const SECTION_COLORS = {
  "Key Deadlines":    "var(--info)",
  "Action Items":     "var(--ok)",
  "Risks & Concerns": "var(--danger)",
  "Overall Sentiment":"var(--accent)",
};

export default function Summary() {
  const [result, setResult]   = useState(null);
  const [loading, setLoading] = useState(false);

  const generate = async () => {
    setLoading(true);
    setResult(null);
    try {
      const { data } = await axios.get(`${API}/summary`);
      setResult(data);
    } catch (err) {
      setResult({ error: err.response?.data?.detail ?? "Failed to generate summary" });
    } finally {
      setLoading(false);
    }
  };

  const sections = result?.summary ? parseSections(result.summary) : [];

  return (
    <div>
      {/* Header */}
      <div className="page-header">
        <div className="page-eyebrow">Executive Intelligence</div>
        <h1 className="page-title">Document summary</h1>
        <p className="page-desc">
          AI-generated executive digest of all uploaded documents —
          deadlines, action items, risks, and sentiment.
        </p>
      </div>

      {/* Generate button */}
      <div className="flex gap12" style={{ marginBottom: 32 }}>
        <button
          className="btn btn-primary"
          onClick={generate}
          disabled={loading}
        >
          {loading
            ? <><span className="spinner" /> Generating…</>
            : "≡ Generate summary"}
        </button>
        {result && !result.error && (
          <button className="btn" onClick={generate} disabled={loading}>
            Regenerate
          </button>
        )}
      </div>

      {/* Loading state */}
      {loading && (
        <div className="loading-state">
          <div className="loading-inner">
            <span className="spinner" style={{ width: 24, height: 24, borderWidth: 3 }} />
            <div>
              <div style={{ fontWeight: 500 }}>Analysing documents…</div>
              <div className="dim" style={{ fontSize: 13 }}>
                Retrieving chunks, building context, generating summary
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Error */}
      {result?.error && (
        <div className="error-msg">{result.error}</div>
      )}

      {/* Results */}
      {result && !result.error && (
        <div>
          {/* Sources bar */}
          {result.sources?.length > 0 && (
            <div className="sources-bar">
              <span className="mono dim" style={{ fontSize: 11, letterSpacing: "0.08em", textTransform: "uppercase" }}>
                Sources
              </span>
              {result.sources.map(s => (
                <span key={s} className="badge badge-file mono">{s}</span>
              ))}
            </div>
          )}

          {/* Section cards grid */}
          <div className="summary-grid mt24">
            {sections.map((sec, i) => (
              <SectionCard key={i} section={sec} />
            ))}
          </div>
        </div>
      )}

      {/* No documents yet */}
      {result?.summary === "No documents have been uploaded yet." && (
        <div className="empty-summary">
          <div className="empty-icon-lg">≡</div>
          <div style={{ fontWeight: 500 }}>No documents uploaded yet</div>
          <div className="dim" style={{ fontSize: 13 }}>
            Upload some .eml, .pdf, or .csv files first, then generate a summary.
          </div>
        </div>
      )}

      <style>{`
        .loading-state {
          padding: 48px;
          display: flex;
          justify-content: center;
        }
        .loading-inner {
          display: flex; align-items: center; gap: 20px;
        }
        .sources-bar {
          display: flex; align-items: center;
          flex-wrap: wrap; gap: 8px;
          padding: 14px 18px;
          background: var(--bg2);
          border: 1px solid var(--line);
          border-radius: var(--r2);
        }
        .summary-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
          gap: 20px;
        }
        .error-msg {
          padding: 14px 16px;
          background: rgba(224,112,112,0.08);
          border: 1px solid rgba(224,112,112,0.25);
          border-radius: var(--r);
          color: var(--danger);
          font-size: 13px;
        }
        .empty-summary {
          display: flex; flex-direction: column;
          align-items: center; justify-content: center;
          gap: 12px; text-align: center;
          padding: 80px 32px;
        }
        .empty-icon-lg {
          width: 56px; height: 56px;
          border-radius: 50%;
          background: var(--bg3);
          border: 1px solid var(--line2);
          display: flex; align-items: center; justify-content: center;
          font-size: 22px; color: var(--muted);
          margin-bottom: 4px;
        }
      `}</style>
    </div>
  );
}

function SectionCard({ section }) {
  const icon  = SECTION_ICONS[section.title]  ?? "◆";
  const color = SECTION_COLORS[section.title] ?? "var(--dim)";
  const isNone = section.lines.length === 1 &&
    section.lines[0].toLowerCase().includes("none identified");

  return (
    <div className="section-card">
      <div className="section-head">
        <span className="section-icon" style={{ color }}>{icon}</span>
        <span className="section-title">{section.title}</span>
      </div>
      <div className="divider" style={{ margin: "14px 0" }} />

      {isNone ? (
        <div className="none-text dim">None identified</div>
      ) : (
        <ul className="section-list">
          {section.lines.map((line, i) => {
            // Strip leading bullet/dash characters GPT might add
            const clean = line.replace(/^[-•*]\s*/, "");
            return (
              <li key={i} className="section-line">
                <span className="line-dot" style={{ background: color }} />
                <span>{clean}</span>
              </li>
            );
          })}
        </ul>
      )}

      <style>{`
        .section-card {
          background: var(--bg2);
          border: 1px solid var(--line);
          border-radius: var(--r3);
          padding: 22px 24px;
        }
        .section-head {
          display: flex; align-items: center; gap: 10px;
        }
        .section-icon {
          font-size: 16px;
          flex-shrink: 0;
        }
        .section-title {
          font-family: var(--serif);
          font-size: 16px;
          color: var(--bright);
        }
        .none-text {
          font-size: 13px;
          font-style: italic;
        }
        .section-list {
          list-style: none;
          display: flex;
          flex-direction: column;
          gap: 10px;
        }
        .section-line {
          display: flex;
          align-items: flex-start;
          gap: 10px;
          font-size: 13px;
          line-height: 1.6;
          color: var(--text);
        }
        .line-dot {
          width: 5px; height: 5px;
          border-radius: 50%;
          flex-shrink: 0;
          margin-top: 7px;
        }
      `}</style>
    </div>
  );
}
