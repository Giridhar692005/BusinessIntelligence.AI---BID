import { useState } from "react";
import { detectStrong } from "../api";

export default function StrongAnomalyWindow({ file, selectedKpi = "revenue" }) {
  const [result, setResult] = useState(null);
  const [windowSize, setWindowSize] = useState(14);
  const [threshold, setThreshold] = useState(2.5);
  const [intervalWidth, setIntervalWidth] = useState(0.9);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function run() {
    if (!file) return setError("Upload a CSV before running an analysis.");
    setLoading(true); setError("");
    try { setResult(await detectStrong(file, selectedKpi, Number(windowSize), Number(threshold), Number(intervalWidth))); }
    catch (err) { setError(err.message); }
    finally { setLoading(false); }
  }

  return (
    <div className="analysis-panel">
      <div className="panel-intro">
        <div><span className="eyebrow">ENSEMBLE ANALYSIS</span><h2>Strong anomaly detection</h2><p>Combines z-score spikes with Prophet seasonality and drift.</p></div>
        <div className="hero-metric">{result ? result.anomaly_count : "—"}<span>flags</span></div>
      </div>
      <div className="strong-controls"><div><span>Selected KPI</span><strong>{selectedKpi.replaceAll("_", " ")}</strong></div><label>Rolling window<input type="number" min="1" value={windowSize} onChange={(event) => setWindowSize(event.target.value)} /></label><label>Z-score threshold<input type="number" step="0.1" value={threshold} onChange={(event) => setThreshold(event.target.value)} /></label><label>Interval width<input type="number" min="0.5" max="0.99" step="0.01" value={intervalWidth} onChange={(event) => setIntervalWidth(event.target.value)} /></label><button className="primary-action" onClick={run} disabled={loading}>{loading ? "Detecting…" : "Detect strong anomalies"}<span>→</span></button></div>
      {error && <div className="error-box">{error}</div>}
      {result ? <><div className="mini-stats"><div><span>Total days</span><strong>{result.total_days}</strong></div><div><span>Anomalies</span><strong className="danger">{result.anomaly_count}</strong></div><div><span>Detected by both</span><strong>{result.both_count}</strong></div></div><div className="table-scroll"><table><thead><tr><th>Date</th><th>Value</th><th>Detected by</th><th>Status</th></tr></thead><tbody>{result.data.map((row, index) => <tr key={index}><td>{row.date}</td><td>{row.value}</td><td>{row.detected_by || "—"}</td><td><span className={row.is_anomaly ? "status-bad" : "status-ok"}>{row.is_anomaly ? "Anomaly" : "Normal"}</span></td></tr>)}</tbody></table></div></> : <div className="empty-panel"><div className="empty-symbol">◈</div><strong>{file ? "Run strong detection" : "Upload a CSV to begin"}</strong><span>Defaults use a 14-day window and 2.5 z-score threshold.</span></div>}
      </div>
  );
}
