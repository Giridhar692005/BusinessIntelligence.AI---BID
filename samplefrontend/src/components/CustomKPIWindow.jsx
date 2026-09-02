import { useState } from "react";
import { addCustomKpi, previewCustomKpiData } from "../api";
const MAX_CUSTOM_KPIS = 3;

export default function CustomKPIWindow({ file, customKpis = [], onCreated, onError }) {
  const [name, setName] = useState("");
  const [definition, setDefinition] = useState("");
  const [unit, setUnit] = useState("");
  const [formula, setFormula] = useState("");
  const [drivenBy, setDrivenBy] = useState("");
  const [drives, setDrives] = useState("");
  const [higherIsBetter, setHigherIsBetter] = useState(true);
  const [threshold, setThreshold] = useState(2.5);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [extraFiles, setExtraFiles] = useState([]);
  const [availableVariables, setAvailableVariables] = useState([]);

  const remaining = MAX_CUSTOM_KPIS - customKpis.length;
  async function previewData() {
  if (!file) return;
  try {
    const result = await previewCustomKpiData(file, extraFiles);
    setAvailableVariables(result.numeric_variables || []);
  } catch (error) {
    setMessage(`✕ ${error?.message || "Could not preview data."}`);
  }
}

  async function handleSubmit(event) {
    event.preventDefault();
    setMessage("");

    if (!file) {
      setMessage("Upload a CSV before defining a custom KPI.");
      return;
    }

    if (remaining <= 0) {
      setMessage("You have reached the limit of 3 custom KPIs for this dataset.");
      return;
    }

    setSaving(true);

    try {
      const result = await addCustomKpi(file,extraFiles, {
        name,
        definition,
        unit,
        formula,
        drivenBy: drivenBy.split(",").map((x) => x.trim()).filter(Boolean),
        drives: drives.split(",").map((x) => x.trim()).filter(Boolean),
        higherIsBetter,
        threshold: Number(threshold),
      });
      console.log("CUSTOM KPI CSV:", result.csv);
      const updatedFile = new File([result.csv], file.name, { type: "text/csv" });

      onCreated?.(result, updatedFile);
      setName("");
      setDefinition("");
      setUnit("");
      setFormula("");
      setDrivenBy("");
      setDrives("");
      setThreshold(2.5);

      setMessage(`✓ ${result.metadata.name} added successfully.`);
    } catch (error) {
      const text = error?.message || "Could not add the KPI.";
      setMessage(`✕ ${text}`);
      onError?.(text);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="custom-kpi-panel">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 16, marginBottom: 20 }}>
        <div>
          <span className="eyebrow">CUSTOM KPI</span>
          <h2 style={{ margin: "6px 0 4px" }}>Add a business KPI</h2>
          <p style={{ margin: 0, opacity: 0.72 }}>
            Existing KPIs stay unchanged. You can add {MAX_CUSTOM_KPIS} custom KPIs per dataset.
          </p>
        </div>
        <div className="custom-kpi-counter">
        <strong>{remaining}</strong>
       <span>custom KPIs remaining</span>
       </div>
      </div>

      {customKpis.length > 0 && (
        <div style={{ marginBottom: 18, padding: 14, borderRadius: 12, background: "rgba(127,127,127,.08)" }}>
          <strong>Added KPIs</strong>
          <div style={{ marginTop: 8, display: "grid", gap: 8 }}>
            {customKpis.map((kpi) => (
              <div key={kpi.name} style={{ padding: 10, borderRadius: 9, border: "1px solid rgba(127,127,127,.18)" }}>
                <strong>{kpi.name}</strong>
                <div style={{ fontSize: 13, opacity: 0.75 }}>{kpi.formula}</div>
              </div>
            ))}
          </div>
        </div>
      )}
      
      <form onSubmit={handleSubmit} className="custom-kpi-form">
        <label>
           Additional daily data (optional)
         <input
         type="file"
          accept=".csv"
           multiple
          onChange={(e) => setExtraFiles(Array.from(e.target.files || []))}
          />
        </label>
        <button type="button" onClick={previewData} disabled={!file || saving}>Load Variables</button>
        {availableVariables.length > 0 && <div><strong>Available variables:</strong> {availableVariables.join(", ")}</div>}
        <label>
          KPI Name
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Gross Margin" disabled={saving || remaining <= 0} />
        </label>

        <label>
          Definition
          <input value={definition} onChange={(e) => setDefinition(e.target.value)} placeholder="e.g. Profit as a percentage of revenue" disabled={saving || remaining <= 0} />
        </label>

        <label>
          Formula
          <input value={formula} onChange={(e) => setFormula(e.target.value)} placeholder="e.g. (revenue - cost) / revenue * 100" disabled={saving || remaining <= 0} />
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>{availableVariables.map(v => <button type="button" key={v} onClick={() => setFormula(f => f ? `${f} ${v}` : v)}>{v}</button>)}</div>
         <small>Available variables: {availableVariables.length ? availableVariables.join(", ") : "Load Variables first."}</small>
        </label>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          <label>
            Unit
            <input value={unit} onChange={(e) => setUnit(e.target.value)} placeholder="%, currency, units…" disabled={saving || remaining <= 0} />
          </label>

          <label>
            Anomaly Threshold
            <input type="number" min="0.1" step="0.1" value={threshold} onChange={(e) => setThreshold(e.target.value)} disabled={saving || remaining <= 0} />
          </label>
        </div>

        <label>
          Driven By
          <input value={drivenBy} onChange={(e) => setDrivenBy(e.target.value)} placeholder="revenue, cost, orders" disabled={saving || remaining <= 0} />
          <small style={{ display: "block", marginTop: 5, opacity: 0.68 }}>Comma-separated business drivers.</small>
        </label>

        <label>
          Drives
          <input value={drives} onChange={(e) => setDrives(e.target.value)} placeholder="profitability, pricing, growth" disabled={saving || remaining <= 0} />
          <small style={{ display: "block", marginTop: 5, opacity: 0.68 }}>What business outcomes this KPI influences.</small>
        </label>

        <label style={{ display: "flex", alignItems: "center", gap: 9 }}>
          <input type="checkbox" checked={higherIsBetter} onChange={(e) => setHigherIsBetter(e.target.checked)} disabled={saving || remaining <= 0} />
          Higher values are generally better
        </label>
         
        <button type="submit" className="primary-action" disabled={saving || !file || remaining <= 0}>
          {saving ? "Validating…" : remaining > 0 ? "Validate & Add KPI" : "Limit reached"}
        </button>

        {message && (
          <div style={{
            padding: 12,
            borderRadius: 10,
            background: "rgba(127,127,127,.08)",
            lineHeight: 1.5
          }}>
            {message}
          </div>
        )}
      </form>
    </div>
  );
}
