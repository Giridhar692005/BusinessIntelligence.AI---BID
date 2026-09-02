import { useMemo, useState, useEffect } from "react";
import { Mosaic, MosaicWindow } from "react-mosaic-component";
import "react-mosaic-component/react-mosaic-component.css";
import "./styles.css";

import { API_URL, uploadOrders, uploadMarketing, calculateKpis, fetchKpis, kpisToFile, chatWithDataset, downloadReport } from "./api";
import AnomalyWindow from "./components/AnomalyWindow";
import PlotWindow from "./components/PlotWindowClean";
import StrongAnomalyWindow from "./components/StrongAnomalyWindow";
import AllKPIWindow from "./components/AllKPIWindow";
import CustomKPIWindow from "./components/CustomKPIWindow";
import RootCauseWindow from "./components/RootCauseWindow";
import ChatDrawer from "./components/ChatDrawer";
import FloatingChatButton from "./components/FloatingChatButton";


const TYPES = {
  anomaly: { label: "Anomaly Detection", icon: "◈" },
  strong: { label: "Strong Anomaly", icon: "◆" },
  plot: { label: "KPI Plot", icon: "⌁" },
  all: { label: "All KPIs", icon: "▦" },
  root: { label: "Root Cause", icon: "⌕" },
  custom: { label: "Add KPI", icon: "+KPI" },
};

function newWindow(type) {
  const id = `${type}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
  return { id, type, title: TYPES[type].label };
}

function App() {
  const first = useMemo(() => newWindow("all"), []);

  const [file, setFile] = useState(null);
  const [availableKpis, setAvailableKpis] = useState([]);
  const [pdfFile, setPdfFile] = useState(null);
  const [windows, setWindows] = useState([first]);
  const [layout, setLayout] = useState(first.id);
  const [activeId, setActiveId] = useState(first.id);
  const [notice, setNotice] = useState("");
  const [selectedKpi, setSelectedKpi] = useState("revenue");
  const [analysisStarted, setAnalysisStarted] = useState(false);
  const [authOpen, setAuthOpen] = useState(false);
  const [authMode, setAuthMode] = useState("login");
  const [accountName, setAccountName] = useState("");
  const [chatInput, setChatInput] = useState("");
  const [chatOpen, setChatOpen] = useState(false);
  const [chatLoading, setChatLoading] = useState(false);
  const [chatMessages, setChatMessages] = useState([]);

  // ---- build-from-raw-data pipeline state ----
  const [ordersFile, setOrdersFile] = useState(null);
  const [marketingFile, setMarketingFile] = useState(null);
  const [reviewsFile, setReviewsFile] = useState(null);
  const [pipelineRunning, setPipelineRunning] = useState(false);
  const [customKpis, setCustomKpis] = useState([]);

  useEffect(() => {
  if (!file) {
    setAvailableKpis([]);
    return;
  }

  file.text().then((text) => {
    const lines = text.split(/\r?\n/).filter(Boolean);
    if (!lines.length) return;

    const columns = lines[0].split(",").map((c) => c.trim().replace(/^"|"$/g, ""));
    const sampleRows = lines.slice(1, Math.min(lines.length, 11));

    const kpis = columns.filter((column, index) => {
      if (column.toLowerCase() === "date") return false;

      const values = sampleRows
        .map((line) => line.split(",")[index]?.trim())
        .filter(Boolean);

      return values.length > 0 && values.every((value) => !Number.isNaN(Number(value)));
    });

    setAvailableKpis(kpis);

    setSelectedKpi((current) =>
      kpis.includes(current) ? current : kpis[0] || ""
    );
  });
  }, [file]);
  function addWindow(type) {
    const item = newWindow(type);
    setWindows((items) => [...items, item]);
    setLayout(item.id);
    setActiveId(item.id);
  }

  function openKpiAnalysis(kpi) {
    const plot = newWindow("plot");

    setSelectedKpi(kpi);
    setAnalysisStarted(true);
    setWindows([plot]);
    setActiveId(plot.id);
    setLayout(plot.id);
  }

  function returnToOverview() {
    const overview = newWindow("all");
    setWindows([overview]);
    setLayout(overview.id);
    setActiveId(overview.id);
    setAnalysisStarted(false);
    setNotice("Choose a KPI from All KPIs to start a new investigation.");
  }

  function changeWindowType(id, type) {
    setWindows((items) =>
      items.map((item) =>
        item.id === id
          ? { ...item, type, title: TYPES[type].label }
          : item
      )
    );
  }

  function closeWindow(id) {
    if (windows.length <= 1) return;
    const remaining = windows.filter((item) => item.id !== id);
    const replacement = activeId === id ? (remaining[0]?.id ?? null) : activeId;
    setWindows(remaining);
    setActiveId(replacement);
    setLayout(replacement);
  }

  function handleFile(event) {
    const selected = event.target.files?.[0];
    if (!selected) return;
    if (!selected.name.toLowerCase().endsWith(".csv")) {
      setNotice("Please choose a .csv file.");
      return;
    }
    setFile(selected);
    setCustomKpis([]);
    setNotice(`Loaded ${selected.name}`);
  }

  // Uploads the two raw CSVs into Postgres, recalculates KPIs there, then
  // pulls the calculated KPIs back and loads them as the working file -
  // same end result as the manual "Upload CSV" button, minus having to
  // pre-compute a KPI file yourself first.
  async function runPipeline() {
    if (!ordersFile || !marketingFile) {
      setNotice("Choose both an orders CSV and a marketing CSV first.");
      return;
    }
    setPipelineRunning(true);
    try {
      setNotice("Uploading orders…");
      await uploadOrders(ordersFile);

      setNotice("Uploading marketing data…");
      await uploadMarketing(marketingFile);

      setNotice("Calculating KPIs…");
      await calculateKpis();

      setNotice("Loading calculated KPIs…");
      const kpiRows = await fetchKpis();
      const builtFile = kpisToFile(kpiRows);

      setFile(builtFile);
      setCustomKpis([]);
      setNotice(`Loaded ${kpiRows.length} day(s) of calculated KPIs`);
    } catch (e) {
      setNotice(`Pipeline failed: ${e.message}`);
    } finally {
      setPipelineRunning(false);
    }
  }

  function handleOrdersFile(event) {
    const selected = event.target.files?.[0];
    if (selected) setOrdersFile(selected);
  }

  function handleMarketingFile(event) {
    const selected = event.target.files?.[0];
    if (selected) setMarketingFile(selected);
  }
   
  function handleReviewsFile(event) {
    const selected = event.target.files?.[0];
    if (selected) setReviewsFile(selected);
  }

  async function submitChat(event) {
    event.preventDefault();
    const message = chatInput.trim();
    if (!message || chatLoading) return;
    setChatOpen(true);
    setChatInput("");

    if (!file) {
      setChatMessages((items) => [...items, { role: "user", content: message }, { role: "assistant", content: "Upload or build a KPI CSV before asking a question." }]);
      return;
    }

    const history = chatMessages.map(({ role, content }) => ({ role, content }));
    setChatMessages((items) => [...items, { role: "user", content: message }]);
    setChatLoading(true);
    try {
      const result = await chatWithDataset(file, message, history, pdfFile);
      let replyData = result;
      if (typeof replyData === "string") {
        try { replyData = JSON.parse(replyData); } catch { /* plain-text reply */ }
      }
      const answer = typeof replyData === "string" ? replyData : replyData.reply ?? replyData.answer ?? replyData.response ?? replyData.message ?? JSON.stringify(replyData, null, 2);
      setChatMessages((items) => [...items, { role: "assistant", content: answer }]);
    } catch (error) {
      setChatMessages((items) => [...items, { role: "assistant", content: `Unable to reach the assistant: ${error.message}` }]);
    } finally {
      setChatLoading(false);
    }
  }

  function renderContent(item) {
    const common = { file, selectedKpi, availableKpis, onKpiSelect: setSelectedKpi, onBusy: () => setNotice("") };
    switch (item.type) {
      case "anomaly":
        return <AnomalyWindow {...common} />;
      case "plot":
        return <PlotWindow {...common} />;
      case "strong":
        return <StrongAnomalyWindow {...common} />;
      case "all":
        return <AllKPIWindow file={file} onKpiSelect={openKpiAnalysis} />;
      case "root":
        return <RootCauseWindow {...common} />;
      case "custom":
        return (<CustomKPIWindow file={file} customKpis={customKpis} onCreated={(result, updatedFile) => {setFile(updatedFile); setSelectedKpi(result.metadata.name); setCustomKpis((items) => [...items, result.metadata]);
        setNotice(`Added KPI: ${result.metadata.name}`);
      }}/>);

      default:
        return null;
    }
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <div className="brand-mark">BID</div>
          <div>
            <div className="brand-name">Business-Investigation-Dept</div>
            <div className="brand-subtitle">Let's find the cause</div>
          </div>
        </div>

          <div className="top-actions">
          <label className="upload-button">
            <span className="button-icon">↑</span>
            {file ? "Replace CSV" : "Upload CSV"}
            <input type="file" accept=".csv" onChange={handleFile} hidden />
          </label>

          <div className={`connection-pill ${API_URL ? "online" : ""}`}>
            <span className="status-dot" />
            API :8000
          </div>
          <button className="auth-button" type="button" onClick={() => { setAuthMode("login"); setAuthOpen(true); }}>
            Login / Sign up
          </button>
          </div>
      </header>

      <div className="main-area">
        <aside className="sidebar">
          <div className="sidebar-section">
            <div className="section-label">Dashboard</div>
            {analysisStarted && (
              <>
                <button className="back-to-overview" onClick={returnToOverview}>← All KPIs overview</button>
                <button className="new-window-button" onClick={() => addWindow("anomaly")}><span>＋</span> New window</button>
                <div className="section-label add-panel-label">ADD PANEL</div>
                <div className="analysis-navigation">
                <button className="tool-button" onClick={() => addWindow("anomaly")}><span className="tool-icon">◈</span><span>Anomaly Detection</span></button>
                <button className="tool-button" onClick={() => addWindow("strong")}><span className="tool-icon">◆</span><span>Strong Anomaly</span></button>
                <button className="tool-button" onClick={() => addWindow("custom")}><span className="tool-icon">★</span> <span>Add KPI</span></button>
                <button className="tool-button" onClick={() => addWindow("plot")}><span className="tool-icon">⌁</span><span>KPI Plot</span></button>
                <button className="tool-button" onClick={() => addWindow("root")}><span className="tool-icon">⌕</span><span>Root Cause</span></button>
                </div>
              </>
            )}
          </div>

          <div className="sidebar-section data-section">
            <div className="section-label">DATA SOURCE</div>
            <div className={`data-card ${file ? "ready" : ""}`}>
              <div className="data-icon">CSV</div>
              <div className="data-copy">
                <strong>{file ? file.name : "No CSV loaded"}</strong>
                <span>{file ? "Available to every panel" : "Upload a dataset above"}</span>
              </div>
            </div>
          </div>

          <div className="sidebar-section data-section">
            <div className="section-label">BUILD FROM RAW DATA</div>
            <label className="upload-button raw-file-input">
              {ordersFile ? ordersFile.name : "Orders CSV"}
              <input type="file" accept=".csv" onChange={handleOrdersFile} hidden />
            </label>
            <label className="upload-button raw-file-input">
              {marketingFile ? marketingFile.name : "Marketing CSV"}
              <input type="file" accept=".csv" onChange={handleMarketingFile} hidden />
            </label>
            <label className="upload-button raw-file-input">
              {reviewsFile ? reviewsFile.name : "Reviews CSV (optional)"}
              <input type="file" accept=".csv" onChange={handleReviewsFile} hidden />
            </label>
            <button
              className="new-window-button pipeline-run-button"
              onClick={runPipeline}
              disabled={pipelineRunning || !ordersFile || !marketingFile}
            >
              <span>⚡</span> {pipelineRunning ? "Running…" : "Calculate & Load"}
            </button>
          </div>

          <div className="sidebar-help">
            <span className="help-key">TIP</span>
            <p>Drag panel dividers to resize your workspace. Add as many analysis panels as you need.</p>
          </div>
        </aside>

        <main className="workspace-wrap">
          <div className="workspace-toolbar">
            <div>
              <span className="crumb">WORKSPACE</span>
              <span className="crumb-separator">/</span>
              <strong>Analysis Board</strong>
            </div>
            <div className="toolbar-right">
              {notice && <span className="notice">{notice}</span>}
              <span className="window-count">{windows.length} panels</span>
            </div>
          </div>

          <div className="window-tabs" role="tablist" aria-label="Open analysis windows">
            {windows.map((item) => (
              <button key={item.id} type="button" role="tab" aria-selected={activeId === item.id} className={activeId === item.id ? "window-tab active" : "window-tab"} onClick={() => { setActiveId(item.id); setLayout(item.id); }}>
                <span>{TYPES[item.type].icon}</span>{TYPES[item.type].label}
              </button>
            ))}
          </div>

          <div className="mosaic-shell">
            <Mosaic
              value={layout}
              onChange={setLayout}
              className="workspace-mosaic"
              renderTile={(id, path) => {
                const item = windows.find((window) => window.id === id);
                if (!item) return <div className="missing-panel">Panel unavailable</div>;

                return (
                  <MosaicWindow
                    path={path}
                    title={
                      <div
                        className="window-title"
                        onMouseDown={() => setActiveId(id)}
                      >
                        <span className="window-title-icon">{TYPES[item.type].icon}</span>
                        <select
                          className="window-type-select"
                          value={item.type}
                          onChange={(event) => changeWindowType(id, event.target.value)}
                          onMouseDown={(event) => event.stopPropagation()}
                        >
                          {Object.entries(TYPES).map(([type, info]) => (
                            <option value={type} key={type}>{info.label}</option>
                          ))}
                        </select>
                        {activeId === id && <span className="active-badge">ACTIVE</span>}
                      </div>
                    }
                    toolbarControls={
                      <button
                        className="close-panel"
                        title="Close panel"
                        onClick={(event) => {
                          event.stopPropagation();
                          closeWindow(id);
                        }}
                      >
                        ×
                      </button>
                    }
                  >
                    <div className="panel-body">{renderContent(item)}</div>
                  </MosaicWindow>
                );
              }}
            />
          </div>

          <form className="command-bar" onSubmit={submitChat}>
            <div className="command-icon">✦</div>
            <input
              placeholder="Describe what you want to analyze…"
              value={chatInput}
              onChange={(event) => setChatInput(event.target.value)}
            />
            <button
              className="command-send"
              type="submit"
              disabled={chatLoading}
            >
              ↑
            </button>
          </form>
        </main>
      </div>
      {authOpen && (
        <div className="auth-backdrop" role="presentation" onMouseDown={() => setAuthOpen(false)}>
          <section className="auth-dialog" role="dialog" aria-modal="true" aria-label="Demo account access" onMouseDown={(event) => event.stopPropagation()}>
            <button className="auth-close" type="button" aria-label="Close" onClick={() => setAuthOpen(false)}>×</button>
            <span className="eyebrow">DEMO ACCESS</span>
            <h2>{authMode === "login" ? "Welcome back" : "Create your demo account"}</h2>
            <p>{authMode === "login" ? "Sign in to save decisions and workspace preferences." : "Create a local demo profile to explore the dashboard."}</p>
            {authMode === "signup" && <label>Name<input value={accountName} onChange={(event) => setAccountName(event.target.value)} placeholder="Your name" /></label>}
            <label>Email<input type="email" placeholder="you@example.com" /></label>
            <label>Password<input type="password" placeholder="••••••••" /></label>
            <button className="auth-submit" type="button" onClick={() => { setNotice(authMode === "login" ? "Demo login successful." : `Demo account created${accountName ? ` for ${accountName}` : ""}.`); setAuthOpen(false); }}>
              {authMode === "login" ? "Log in" : "Create account"}
            </button>
            <button className="auth-switch" type="button" onClick={() => setAuthMode((mode) => mode === "login" ? "signup" : "login")}>
              {authMode === "login" ? "New here? Sign up" : "Already have an account? Log in"}
            </button>
          </section>
        </div>
      )}
      <FloatingChatButton onClick={() => setChatOpen(true)} />
      <ChatDrawer
      open={chatOpen}
      messages={chatMessages}
      loading={chatLoading}
      inputValue={chatInput}
      onInputChange={setChatInput}
    onSubmit={submitChat}
    onClose={() => setChatOpen(false)}
    pdfFile={pdfFile}
    onPdfSelect={setPdfFile}
   />
    </div>
  );
}

export default App;
