import { useState } from "react";
import Upload from "./components/Upload";
import Query from "./components/Query";
import Compliance from "./components/Compliance";
import Summary from "./components/Summary";
import "./styles.css";

const NAV = [
  { id: "upload",     label: "Ingest",     icon: "↑" },
  { id: "query",      label: "Query",      icon: "?" },
  { id: "compliance", label: "Compliance", icon: "⚑" },
  { id: "summary",    label: "Summary",    icon: "≡" },
];

export default function App() {
  const [page, setPage] = useState("upload");

  return (
    <div className="app">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">M</span>
          <span className="brand-name">Meridian</span>
        </div>

        <nav className="nav">
          {NAV.map(n => (
            <button
              key={n.id}
              className={`nav-item ${page === n.id ? "active" : ""}`}
              onClick={() => setPage(n.id)}
            >
              <span className="nav-icon">{n.icon}</span>
              <span className="nav-label">{n.label}</span>
            </button>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div className="user-pill">
            <span className="user-avatar">AD</span>
            <div>
              <div className="user-name">Admin</div>
              <div className="user-role">Full access</div>
            </div>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="main">
        {page === "upload"     && <Upload />}
        {page === "query"      && <Query />}
        {page === "compliance" && <Compliance />}
        {page === "summary"    && <Summary />}
      </main>
    </div>
  );
}
