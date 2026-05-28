import { useState } from "react";
import axios from "axios";

const API = "http://localhost:8000";

export default function Compliance() {
  // ── Manual text check ─────────────────────────────────────────
  const [text, setText]         = useState("");
  const [textResult, setResult] = useState(null);
  const [textLoading, setTL]    = useState(false);

  // ── Full DB scan ──────────────────────────────────────────────
  const [scanResult, setScan]   = useState(null);
  const [scanLoading, setSL]    = useState(false);
  const [expanded, setExpanded] = useState(null);

  const checkText = async () => {
    if (!text.trim()) return;
    setTL(true);
    setResult(null);
    try {
      const { data } = await axios.post(`${API}/compliance`, { text });
      setResult(data);
    } catch (err) {
      setResult({ error: err.response?.data?.detail ?? "Request failed" });
    } finally {
      setTL(false);
    }
  };

  const runScan = async () => {
    setSL(true);
    setScan(null);
    setExpanded(null);
    try {
      const { data } = await axios.get(`${API}/compliance/scan`);
      setScan(data);
    } catch (err) {
      setScan({ error: err.response?.data?.detail ?? "Scan failed" });
    } finally {
      setSL(false);
    }
  };

  return (
    <div>
      {/* Header */}
      <div className="page-header">
        <div className="page-eyebrow">Risk & Compliance</div>
        <h1 className="page-title">Compliance scanner</h1>
        <p className="page-desc">
          Detect PII, risk keywords, and compliance violations using
          rule-based and AI-powered analysis.
        </p>
      </div>

      {/* Two-column layout */}
      <div className="compliance-grid">

        {/* Left — manual text check */}
        <div className="card">
          <div className="section-label mono dim">Analyse text</div>
          <p className="dim mt8" style={{ fontSize: 13, marginBottom: 16 }}>
            Paste any text to run a quick compliance check.
          </p>
          <textarea
            className="input"
            rows={6}
            placeholder="Paste an email, message, or document excerpt…"
            value={text}
            onChange={e => setText(e.target.value)}
          />
          <button
            className="btn btn-primary mt16"
            onClick={checkText}
            disabled={textLoading || !text.trim()}
          >
            {textLoading ? <><span className="spinner" /> Analysing…</> : "Run analysis"}
          </button>

          {textResult && !textResult.error && (
            <div className="mt24">
              <div className="divider" />
              <RiskBadge score={textResult.risk_score} large />

              {Object.keys(textResult.personal_info).length > 0 && (
                <div className="result-block mt16">
                  <div className="result-label">PII detected</div>
                  <div className="pill-row">
                    {Object.entries(textResult.personal_info).map(([k, v]) => (
                      <span key={k} className="badge badge-high mono">
                        {k.replace("_", " ")} ×{v}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {textResult.risk_keywords.length > 0 && (
                <div className="result-block mt16">
                  <div className="result-label">Risk keywords</div>
                  <div className="pill-row">
                    {textResult.risk_keywords.map(k => (
                      <span key={k} className="badge badge-medium mono">{k}</span>
                    ))}
                  </div>
                </div>
              )}

              {!textResult.flagged && (
                <div className="result-block mt16 clean-block">
                  <span className="dot dot-ok" /> No issues detected
                </div>
              )}
            </div>
          )}

          {textResult?.error && (
            <div className="error-msg mt16">{textResult.error}</div>
          )}
        </div>

        {/* Right — full database scan */}
        <div className="card">
          <div className="section-label mono dim">Database scan</div>
          <p className="dim mt8" style={{ fontSize: 13, marginBottom: 16 }}>
            Semantically scan all uploaded documents for compliance risks.
            Uses AI to filter false positives.
          </p>
          <button
            className="btn btn-primary"
            onClick={runScan}
            disabled={scanLoading}
          >
            {scanLoading
              ? <><span className="spinner" /> Scanning…</>
              : "⚑ Scan all documents"}
          </button>

          {scanResult && !scanResult.error && (
            <div className="mt24">
              <div className="divider" />
              <div className="scan-summary">
                <span className="scan-count">{scanResult.total_flagged}</span>
                <span className="dim">
                  {scanResult.total_flagged === 1 ? "risk" : "risks"} found
                </span>
              </div>

              {scanResult.total_flagged === 0 && (
                <div className="clean-block mt16">
                  <span className="dot dot-ok" /> All documents appear clean
                </div>
              )}

              <div className="scan-list mt16">
                {scanResult.flagged_chunks?.map((chunk, i) => (
                  <div key={i} className="scan-item">
                    <div
                      className="scan-header"
                      onClick={() => setExpanded(expanded === i ? null : i)}
                    >
                      <RiskBadge score={chunk.risk_score} />
                      <span className="badge badge-file mono" style={{ fontSize: 11 }}>
                        {chunk.filename}
                      </span>
                      <span className="dim" style={{ fontSize: 12, marginLeft: "auto" }}>
                        {chunk.reason}
                      </span>
                      <span className="dim" style={{ fontSize: 12 }}>
                        {expanded === i ? "▲" : "▼"}
                      </span>
                    </div>

                    {expanded === i && (
                      <div className="scan-body">
                        <div className="chunk-text mono">{chunk.content}</div>
                        {chunk.risk_keywords?.length > 0 && (
                          <div className="pill-row mt8">
                            {chunk.risk_keywords.map(k => (
                              <span key={k} className="badge badge-medium mono">{k}</span>
                            ))}
                          </div>
                        )}
                        {Object.keys(chunk.personal_info ?? {}).length > 0 && (
                          <div className="pill-row mt8">
                            {Object.entries(chunk.personal_info).map(([k, v]) => (
                              <span key={k} className="badge badge-high mono">
                                {k.replace("_", " ")} ×{v}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {scanResult?.error && (
            <div className="error-msg mt16">{scanResult.error}</div>
          )}
        </div>
      </div>

      <style>{`
        .compliance-grid {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 24px;
        }
        .section-label {
          font-size: 11px;
          letter-spacing: 0.1em;
          text-transform: uppercase;
        }
        .result-label {
          font-size: 12px;
          color: var(--dim);
          margin-bottom: 8px;
          font-family: var(--mono);
          letter-spacing: 0.06em;
          text-transform: uppercase;
        }
        .result-block { }
        .pill-row { display: flex; flex-wrap: wrap; gap: 6px; }
        .clean-block {
          display: flex; align-items: center; gap: 8px;
          padding: 12px 14px;
          background: rgba(109,184,138,0.06);
          border: 1px solid rgba(109,184,138,0.2);
          border-radius: var(--r);
          font-size: 13px;
          color: var(--ok);
        }
        .scan-summary {
          display: flex; align-items: baseline; gap: 8px;
        }
        .scan-count {
          font-family: var(--serif);
          font-size: 40px;
          color: var(--bright);
          line-height: 1;
        }
        .scan-list { display: flex; flex-direction: column; gap: 8px; }
        .scan-item {
          border: 1px solid var(--line);
          border-radius: var(--r2);
          overflow: hidden;
        }
        .scan-header {
          display: flex; align-items: center; gap: 8px;
          padding: 12px 14px;
          cursor: pointer;
          background: var(--bg3);
          transition: background 0.15s;
          flex-wrap: wrap;
        }
        .scan-header:hover { background: var(--bg4); }
        .scan-body {
          padding: 14px;
          border-top: 1px solid var(--line);
          background: var(--bg2);
        }
        .chunk-text {
          font-size: 12px;
          color: var(--dim);
          line-height: 1.7;
          white-space: pre-wrap;
          word-break: break-word;
        }
        .error-msg {
          padding: 12px 14px;
          background: rgba(224,112,112,0.08);
          border: 1px solid rgba(224,112,112,0.25);
          border-radius: var(--r);
          color: var(--danger);
          font-size: 13px;
        }
        @media (max-width: 900px) {
          .compliance-grid { grid-template-columns: 1fr; }
        }
      `}</style>
    </div>
  );
}

function RiskBadge({ score, large }) {
  const map = {
    "High Risk":   "badge-high",
    "Medium Risk": "badge-medium",
    "Low Risk":    "badge-low",
  };
  return (
    <span
      className={`badge ${map[score] ?? "badge-low"}`}
      style={large ? { fontSize: 13, padding: "4px 14px" } : {}}
    >
      {score ?? "Low Risk"}
    </span>
  );
}
