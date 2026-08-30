import { useEffect, useState } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { API_URL } from "../api";

export default function PlotWindowClean({
  file,
  selectedKpi,
  availableKpis = [],
  onKpiSelect
}) {
  const [data, setData] = useState([]);
  const [mode, setMode] = useState("regular");
  const [windowSize, setWindowSize] = useState(14);
  const [threshold, setThreshold] = useState(2.5);
  const [intervalWidth, setIntervalWidth] = useState(0.9);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function loadGraph(nextMode = mode) {
    if (!file) return setError("Upload a CSV file first.");
    setLoading(true); setError(""); setMode(nextMode);
    try {
      const formData = new FormData(); formData.append("file", file);
      const endpoint = nextMode === "strong" ? "detect-strong" : "detect";
      const interval = nextMode === "strong" ? `&interval_width=${intervalWidth}` : "";
      const response = await fetch(`${API_URL}/${endpoint}?kpi=${encodeURIComponent(selectedKpi)}&window=${windowSize}&threshold=${threshold}${interval}`, { method: "POST", body: formData });
      if (!response.ok) throw new Error("Failed to load graph data.");
      const result = await response.json();
      setData((result.data || []).map((row) => ({ ...row, value: Number(row.value), anomalyValue: row.is_anomaly ? Number(row.value) : null })));
    } catch (err) { setError(err.message); } finally { setLoading(false); }
  }

  useEffect(() => {
    if (file) loadGraph("regular");
  }, [file, selectedKpi]);

  return <div className="analysis-panel plot-panel">
    <div className="panel-intro"><div><span className="eyebrow">VISUAL ANALYSIS</span><h2>KPI plot</h2><p>Detected anomalies are highlighted on the selected KPI.</p></div></div>
    <div className="plot-toolbar">
      <label>
  KPI
  <select
    value={selectedKpi}
    onChange={(event) => onKpiSelect(event.target.value)}
    disabled={!availableKpis.length}
  >
    {availableKpis.map((kpi) => (
      <option key={kpi} value={kpi}>
        {kpi
          .replaceAll("_", " ")
          .replace(/\b\w/g, (c) => c.toUpperCase())}
      </option>
    ))}
  </select>
</label>
      <label>Rolling window<input type="number" min="1" value={windowSize} onChange={(event) => setWindowSize(event.target.value)} /></label>
      <label>Z-score threshold<input type="number" step="0.1" value={threshold} onChange={(event) => setThreshold(event.target.value)} /></label>
      {mode === "strong" && <label>Interval width<input type="number" min="0.5" max="0.99" step="0.01" value={intervalWidth} onChange={(event) => setIntervalWidth(event.target.value)} /></label>}
      <button className={mode === "regular" ? "plot-action active" : "plot-action"} onClick={() => loadGraph("regular")} disabled={loading}>Detect regular</button>
      <button className={mode === "strong" ? "plot-action active" : "plot-action"} onClick={() => loadGraph("strong")} disabled={loading}>Detect strong</button>
    </div>
    {error && <div className="error-box">{error}</div>}
    <div className="plot-chart-card">{data.length ? <ResponsiveContainer width="100%" height={350}><LineChart data={data} margin={{ top: 15, right: 20, left: 5, bottom: 35 }}><CartesianGrid stroke="#34416b" strokeDasharray="3 3" /><XAxis dataKey="date" stroke="#ABD2FA" tick={{ fill: "#ABD2FA", fontSize: 10 }} label={{ value: "Date", position: "insideBottom", offset: -20, fill: "#ABD2FA" }} /><YAxis stroke="#ABD2FA" tick={{ fill: "#ABD2FA", fontSize: 10 }} label={{ value: selectedKpi.replaceAll("_", " "), angle: -90, position: "insideLeft", fill: "#ABD2FA" }} /><Tooltip content={<ChartTooltip />} /><Line type="monotone" dataKey="value" name={selectedKpi} stroke="#ABD2FA" strokeWidth={2} dot={false} /><Line type="monotone" dataKey="anomalyValue" name="Anomaly" stroke="transparent" strokeWidth={0} dot={<AnomalyDot />} connectNulls={false} /></LineChart></ResponsiveContainer> : <div className="empty-panel"><div className="empty-symbol">⌁</div><strong>{file ? "Choose a detection mode" : "Upload a CSV to begin"}</strong><span>{loading ? "Loading graph…" : "Set the detector values, then run detection."}</span></div>}</div>
  </div>;
}

function AnomalyDot({ cx, cy, payload }) {
  if (!payload?.is_anomaly || cx == null || cy == null) return null;
  return <g aria-label="Anomaly detected"><line x1={cx - 5} y1={cy - 5} x2={cx + 5} y2={cy + 5} stroke="#ff7373" strokeWidth={2.5} /><line x1={cx + 5} y1={cy - 5} x2={cx - 5} y2={cy + 5} stroke="#ff7373" strokeWidth={2.5} /><title>Anomaly detected</title></g>;
}

function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  const point = payload[0].payload;
  return <div className="chart-tooltip"><strong>{label}</strong><span>Value: {point.value}</span>{point.is_anomaly && <b>Anomaly detected</b>}</div>;
}
