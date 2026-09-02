const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

async function parseError(response) {
  try {
    const body = await response.json();
    const message = body.error || body.detail || "Request failed";
    return typeof message === "string" ? message : JSON.stringify(message);
  } catch {
    return `Request failed (${response.status})`;
  }
}

export async function detectAnomalies(file, kpi, window = 14, threshold = 2.5) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(
    `${API_URL}/detect?kpi=${encodeURIComponent(kpi)}&window=${window}&threshold=${threshold}`,
    { method: "POST", body: formData }
  );

  if (!response.ok) throw new Error(await parseError(response));
  return response.json();
}

export async function detectAll(file, window = 14, threshold = 2.5) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(
    `${API_URL}/detect-all?window=${window}&threshold=${threshold}`,
    { method: "POST", body: formData }
  );

  if (!response.ok) throw new Error(await parseError(response));
  return response.json();
}

export async function getPlot(file, kpi, window = 14, threshold = 2.5) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(
    `${API_URL}/plot-base64?kpi=${encodeURIComponent(kpi)}&window=${window}&threshold=${threshold}`,
    { method: "POST", body: formData }
  );

  if (!response.ok) throw new Error(await parseError(response));
  return response.json();
}

export async function getRootCause(file, date, window = 14, threshold = 2.5) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(
    `${API_URL}/root-cause?date=${encodeURIComponent(date)}&window=${window}&threshold=${threshold}`,
    { method: "POST", body: formData }
  );

  if (!response.ok) throw new Error(await parseError(response));
  return response.json();
}
export async function downloadReport(file, kpi, date, window = 14, threshold = 2.5, analysis) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("analysis_json", JSON.stringify(analysis));

  const response = await fetch(
    `${API_URL}/report?kpi=${encodeURIComponent(kpi)}&date=${encodeURIComponent(date)}&window=${window}&threshold=${threshold}`,
    {
      method: "POST",
      body: formData,
    }
  );

  if (!response.ok) throw new Error(await parseError(response));

  return response.blob();
}
// ---------------------------------------------------------------
// Build-from-raw-data pipeline: upload the two source CSVs, ask the
// backend to (re)calculate KPIs from them, then read the calculated
// KPIs back out. This is what lets someone go from raw order/marketing
// exports straight to a working analysis, without hand-preparing a
// KPI CSV themselves first.
// ---------------------------------------------------------------

export async function uploadOrders(file) {
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch(`${API_URL}/upload-orders`, { method: "POST", body: formData });
  if (!response.ok) throw new Error(await parseError(response));
  return response.json();
}

export async function uploadMarketing(file) {
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch(`${API_URL}/upload-marketing`, { method: "POST", body: formData });
  if (!response.ok) throw new Error(await parseError(response));
  return response.json();
}

export async function calculateKpis() {
  const response = await fetch(`${API_URL}/calculate-kpis`, { method: "POST" });
  if (!response.ok) throw new Error(await parseError(response));
  return response.json();
}

export async function detectStrong(file, kpi, window = 14, threshold = 2.5, intervalWidth = 0.9) {
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch(`${API_URL}/detect-strong?kpi=${encodeURIComponent(kpi)}&window=${window}&threshold=${threshold}&interval_width=${intervalWidth}`, { method: "POST", body: formData });
  if (!response.ok) throw new Error(await parseError(response));
  return response.json();
}
export async function uploadReviews(file) {
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch(`${API_URL}/upload-reviews`, { method: "POST", body: formData });
  if (!response.ok) throw new Error(await parseError(response));
  return response.json();
}
export async function fetchKpis() {
  const response = await fetch(`${API_URL}/kpis`);
  if (!response.ok) throw new Error(await parseError(response));
  return response.json();
}

export async function chatWithDataset(file, message, history, pdfFile = null) {
  const formData = new FormData();

  formData.append("file", file);

  formData.append(
    "req",
    JSON.stringify({
      message,
      history,
    })
  );

  if (pdfFile) {
    formData.append("pdf", pdfFile);
  }

  const response = await fetch(
    `${API_URL}/chat`,
    {
      method: "POST",
      body: formData,
    }
  );

  if (!response.ok) {
    throw new Error(await parseError(response));
  }

  return response.json();
}

export async function addCustomKpi(
  file,
  extraFiles = [],
  {
    name,
    definition,
    unit,
    formula,
    drivenBy = [],
    drives = [],
    higherIsBetter = true,
    threshold = 2.5
  }
) {
  const formData = new FormData();

  formData.append("file", file);
  extraFiles.forEach((extraFile) => {
    formData.append("extra_files", extraFile);
  });

  formData.append("name", name);
  formData.append("definition", definition);
  formData.append("unit", unit);
  formData.append("formula", formula);
  formData.append("driven_by", drivenBy.join(","));
  formData.append("drives", drives.join(","));
  formData.append("higher_is_better", String(higherIsBetter));
  formData.append("threshold", String(threshold));

  const response = await fetch(`${API_URL}/custom-kpi`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw new Error(await parseError(response));
  }

  return response.json();
}
export async function previewCustomKpiData(file, extraFiles = []) {
  const formData = new FormData(); formData.append("file", file); extraFiles.forEach(f => formData.append("extra_files", f));
  const response = await fetch(`${API_URL}/custom-kpi/preview`, { method: "POST", body: formData });
  if (!response.ok) throw new Error(await parseError(response)); return response.json();
}
// Turns the /kpis JSON response into a File object shaped exactly like
// the CSV every analysis panel already expects (date, revenue,
// conversion_rate, aov, cac) - so calculated KPIs can be dropped straight
// into the same `file` state the rest of the app already uses.
export function kpisToFile(kpiRows) {
  const header = "date,revenue,conversion_rate,aov,cac";
  const lines = kpiRows.map((row) =>
    [row.date, row.revenue ?? "", row.conversion_rate ?? "", row.aov ?? "", ""].join(",")
  );
  const csvText = [header, ...lines].join("\n");
  return new File([csvText], "kpis_from_database.csv", { type: "text/csv" });
}

export { API_URL };
