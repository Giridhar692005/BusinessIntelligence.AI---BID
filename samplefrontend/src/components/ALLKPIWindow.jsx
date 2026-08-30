import { useState } from "react";
import { detectAll } from "../api";

const labels = {
  revenue: "Revenue",
  conversion_rate: "Conversion rate",
  aov: "AOV",
  cac: "CAC",
};

export default function AllKPIWindow({ file, selectedKpi, onKpiSelect }) {
  const [window, setWindow] = useState(14);
  const [threshold, setThreshold] = useState(2.5);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function run() {
    if (!file) return setError("Upload a CSV before running the dashboard analysis.");
    setLoading(true); setError("");
    try { setResult(await detectAll(file, Number(window), Number(threshold))); }
    catch (e) { setError(e.message); }
    finally { setLoading(false); }
  }

  return <div className="analysis-panel">
    <div className="panel-intro">
      <div><span className="eyebrow">MULTI-KPI</span><h2>All KPI overview</h2><p>Run your backend multi-KPI detector in one request.</p></div>
    </div>
    <div className="control-grid compact">
      <label>Rolling window<input type="number" value={window} onChange={e => setWindow(e.target.value)} /></label>
      <label>Threshold<input type="number" step="0.1" value={threshold} onChange={e => setThreshold(e.target.value)} /></label>
      <button className="primary-action" onClick={run}>{loading ? "Running…" : "Run all KPIs"} <span>→</span></button>
    </div>
    {error && <div className="error-box">{error}</div>}
    {result ? <div className="kpi-card-grid">{Object.entries(result).map(([kpi, data]) =>
      <button className={`metric-card ${selectedKpi === kpi ? "selected" : ""}`} key={kpi} type="button" onClick={() => onKpiSelect(kpi)} title={`Use ${labels[kpi] || kpi} in every analysis panel`}><div className="metric-card-top"><span>{labels[kpi] || kpi}</span><span className="metric-icon">↗</span></div><strong>{data.anomaly_count}</strong><small>anomalies detected · Click to analyze</small></button>
    )}</div> : <div className="empty-panel"><div className="empty-symbol">▦</div><strong>{file ? "Run the full KPI scan" : "Upload a CSV to begin"}</strong><span>Revenue, conversion rate, AOV and CAC are checked when present.</span></div>}
  </div>;
}
