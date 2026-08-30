import { useState } from "react";
import { detectAnomalies } from "../api";

const KPIS = ["revenue", "conversion_rate", "aov", "cac"];

export default function AnomalyWindow({ file, selectedKpi = "revenue", onKpiSelect }) {
  const [window, setWindow] = useState(14);
  const [threshold, setThreshold] = useState(2.5);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function run() {
    if (!file) return setError("Upload a CSV before running an analysis.");
    setLoading(true); setError("");
    try {
      setResult(await detectAnomalies(file, selectedKpi, Number(window), Number(threshold)));
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  }

  return (
    <div className="analysis-panel">
      <div className="panel-intro">
        <div>
          <span className="eyebrow">STATISTICAL ANALYSIS</span>
          <h2>Detect anomalies</h2>
          <p>Find unusual KPI movements using a rolling z-score.</p>
        </div>
        <div className="hero-metric">{result ? result.anomaly_count : "—"}<span>flags</span></div>
      </div>

      <div className="control-grid">
        <label>KPI<select value={selectedKpi} onChange={e => onKpiSelect(e.target.value)}>
          {KPIS.map(x => <option key={x}>{x}</option>)}
        </select></label>
        <label>Rolling window<input type="number" min="1" value={window} onChange={e => setWindow(e.target.value)} /></label>
        <label>Z-score threshold<input type="number" step="0.1" value={threshold} onChange={e => setThreshold(e.target.value)} /></label>
        <button className="primary-action" onClick={run}>{loading ? "Running…" : "Run detection"} <span>→</span></button>
      </div>

      {error && <div className="error-box">{error}</div>}

      {result ? (
        <div className="result-area">
          <div className="mini-stats">
            <div><span>Total days</span><strong>{result.total_days}</strong></div>
            <div><span>Anomalies</span><strong className="danger">{result.anomaly_count}</strong></div>
            <div><span>KPI</span><strong>{result.kpi}</strong></div>
          </div>
          <div className="table-scroll">
            <table><thead><tr><th>Date</th><th>Value</th><th>Z-score</th><th>Status</th></tr></thead>
              <tbody>{result.data.map((row, i) => (
                <tr key={i}><td>{row.date}</td><td>{row.value}</td><td>{row.z_score ?? "—"}</td>
                  <td><span className={row.is_anomaly ? "status-bad" : "status-ok"}>{row.is_anomaly ? "Anomaly" : "Normal"}</span></td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        </div>
      ) : <EmptyState file={file} text="Run detection to see the anomaly timeline." />}
    </div>
  );
}

function EmptyState({ file, text }) {
  return <div className="empty-panel"><div className="empty-symbol">{file ? "◌" : "↑"}</div><strong>{file ? text : "Upload a CSV to begin"}</strong><span>{file ? "Tune the parameters above and run the function." : "The same file will be shared with every workspace panel."}</span></div>;
}
