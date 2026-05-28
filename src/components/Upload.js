import { useState, useCallback } from "react";
import axios from "axios";

const API = "http://localhost:8000";
const ACCEPTED = [".eml", ".pdf", ".csv"];

function getExt(name) {
  return "." + name.split(".").pop().toLowerCase();
}

function fmtSize(b) {
  if (b < 1024) return b + " B";
  if (b < 1024 * 1024) return (b / 1024).toFixed(1) + " KB";
  return (b / 1024 / 1024).toFixed(2) + " MB";
}

export default function Upload() {
  const [files, setFiles]   = useState([]);
  const [dragging, setDrag] = useState(false);

  // ── Add files from input or drop ──────────────────────────────
  const addFiles = useCallback((incoming) => {
    const validated = Array.from(incoming)
      .filter(f => {
        const ext = getExt(f.name);
        if (!ACCEPTED.includes(ext)) {
          alert(`"${f.name}" — only .eml, .pdf, .csv are supported`);
          return false;
        }
        if (f.size > 10 * 1024 * 1024) {
          alert(`"${f.name}" exceeds 10 MB`);
          return false;
        }
        return true;
      })
      .map(f => ({
        id:       crypto.randomUUID(),
        file:     f,
        status:   "pending",   // pending | uploading | done | error
        progress: 0,
        error:    null,
      }));
    setFiles(prev => {
      const existingNames = new Set(prev.map(x => x.file.name));
      return [...prev, ...validated.filter(f => !existingNames.has(f.file.name))];
    });
  }, []);

  // ── Drag handlers ─────────────────────────────────────────────
  const onDragOver  = e => { e.preventDefault(); setDrag(true); };
  const onDragLeave = ()  => setDrag(false);
  const onDrop      = e  => {
    e.preventDefault();
    setDrag(false);
    addFiles(e.dataTransfer.files);
  };

  // ── Upload one file ───────────────────────────────────────────
  const uploadOne = async (id) => {
    const item = files.find(f => f.id === id);
    if (!item) return;

    setFiles(prev => prev.map(f =>
      f.id === id ? { ...f, status: "uploading" } : f
    ));

    const form = new FormData();
    form.append("file", item.file);

    try {
      await axios.post(`${API}/upload`, form, {
        onUploadProgress: ({ loaded, total }) => {
          const pct = Math.round((loaded / (total ?? 1)) * 100);
          setFiles(prev => prev.map(f =>
            f.id === id ? { ...f, progress: pct } : f
          ));
        },
      });
      setFiles(prev => prev.map(f =>
        f.id === id ? { ...f, status: "done", progress: 100 } : f
      ));
    } catch (err) {
      const msg = err.response?.data?.detail ?? "Upload failed";
      setFiles(prev => prev.map(f =>
        f.id === id ? { ...f, status: "error", error: msg } : f
      ));
    }
  };

  const uploadAll = () =>
    files.filter(f => f.status === "pending").forEach(f => uploadOne(f.id));

  const remove = id =>
    setFiles(prev => prev.filter(f => f.id !== id));

  const clearDone = () =>
    setFiles(prev => prev.filter(f => f.status !== "done"));

  const pending = files.filter(f => f.status === "pending").length;
  const done    = files.filter(f => f.status === "done").length;

  return (
    <div>
      {/* Header */}
      <div className="page-header">
        <div className="page-eyebrow">Document Ingestion</div>
        <h1 className="page-title">Upload files</h1>
        <p className="page-desc">
          Upload .eml, .pdf, or .csv files. Each file will be parsed, chunked,
          embedded, and stored in the vector database for AI querying.
        </p>
      </div>

      {/* Drop zone */}
      <div
        className={`dropzone ${dragging ? "over" : ""}`}
        onClick={() => document.getElementById("file-input").click()}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
      >
        <input
          id="file-input"
          type="file"
          multiple
          accept=".eml,.pdf,.csv"
          style={{ display: "none" }}
          onChange={e => { addFiles(e.target.files); e.target.value = ""; }}
        />
        <div className="dropzone-icon">↑</div>
        <div className="dropzone-text">
          Drop files here <span className="dim">or click to browse</span>
        </div>
        <div className="dropzone-sub mono dim">.eml · .pdf · .csv — max 10 MB each</div>
      </div>

      {/* File list */}
      {files.length > 0 && (
        <div className="mt24">
          <div className="flex gap12" style={{ marginBottom: 16, justifyContent: "space-between" }}>
            <span className="dim" style={{ fontSize: 13 }}>
              {files.length} file{files.length !== 1 ? "s" : ""} queued
              {done > 0 && ` — ${done} ingested`}
            </span>
            <div className="flex gap8">
              {done > 0 && (
                <button className="btn" onClick={clearDone}>Clear done</button>
              )}
              {pending > 0 && (
                <button className="btn btn-primary" onClick={uploadAll}>
                  Upload {pending} file{pending !== 1 ? "s" : ""}
                </button>
              )}
            </div>
          </div>

          <div className="file-list">
            {files.map(f => (
              <FileRow
                key={f.id}
                item={f}
                onRemove={() => remove(f.id)}
                onRetry={() => uploadOne(f.id)}
              />
            ))}
          </div>
        </div>
      )}

      {/* Inline styles for this component */}
      <style>{`
        .dropzone {
          border: 1px dashed var(--line2);
          border-radius: var(--r3);
          padding: 56px 32px;
          text-align: center;
          cursor: pointer;
          transition: border-color 0.15s, background 0.15s;
        }
        .dropzone:hover, .dropzone.over {
          border-color: var(--accent);
          background: rgba(200,184,154,0.04);
        }
        .dropzone-icon {
          font-size: 28px;
          margin-bottom: 12px;
          color: var(--muted);
        }
        .dropzone-text {
          font-size: 15px;
          color: var(--text);
          margin-bottom: 6px;
        }
        .dropzone-sub {
          font-size: 12px;
          letter-spacing: 0.06em;
        }
        .file-list {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }
      `}</style>
    </div>
  );
}

function FileRow({ item, onRemove, onRetry }) {
  const ext = getExt(item.file.name);

  const statusDot = {
    pending:   "dot-idle",
    uploading: "dot-warn",
    done:      "dot-ok",
    error:     "dot-error",
  }[item.status];

  return (
    <div className="file-row">
      <span className={`dot ${statusDot}`} />
      <span className="badge badge-file mono">{ext}</span>
      <span className="file-name">{item.file.name}</span>
      <span className="dim mono" style={{ fontSize: 12, marginLeft: "auto" }}>
        {fmtSize(item.file.size)}
      </span>

      {item.status === "error" && (
        <span style={{ color: "var(--danger)", fontSize: 12 }}>{item.error}</span>
      )}

      {item.status === "uploading" && (
        <span className="spinner" style={{ marginLeft: 8 }} />
      )}

      {item.status === "error" && (
        <button className="btn btn-danger" style={{ padding: "4px 10px", fontSize: 12 }} onClick={onRetry}>
          Retry
        </button>
      )}

      {item.status !== "uploading" && (
        <button className="icon-btn" onClick={onRemove} title="Remove">✕</button>
      )}

      {item.status === "uploading" && item.progress > 0 && item.progress < 100 && (
        <div className="prog-track">
          <div className="prog-fill" style={{ width: `${item.progress}%` }} />
        </div>
      )}

      <style>{`
        .file-row {
          display: flex;
          align-items: center;
          gap: 10px;
          padding: 12px 16px;
          background: var(--bg2);
          border: 1px solid var(--line);
          border-radius: var(--r2);
          flex-wrap: wrap;
        }
        .file-name {
          font-size: 13px;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
          max-width: 320px;
        }
        .icon-btn {
          background: none;
          border: none;
          color: var(--muted);
          cursor: pointer;
          font-size: 14px;
          padding: 2px 6px;
          border-radius: var(--r);
          transition: color 0.15s;
        }
        .icon-btn:hover { color: var(--danger); }
        .prog-track {
          width: 100%;
          height: 2px;
          background: var(--line);
          border-radius: 2px;
          overflow: hidden;
          flex-basis: 100%;
          margin-top: 4px;
        }
        .prog-fill {
          height: 100%;
          background: var(--accent);
          border-radius: 2px;
          transition: width 0.2s;
        }
      `}</style>
    </div>
  );
}
