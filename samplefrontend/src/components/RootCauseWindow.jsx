import { useState } from "react";
import { API_URL, downloadReport } from "../api";

export default function RootCauseWindow({ file, selectedKpi, availableKpis = [], onKpiSelect }) {

  const [date, setDate] = useState("");
  const [windowSize, setWindowSize] = useState(14);
  const [threshold, setThreshold] = useState(2.5);
  const [persona, setPersona] = useState("");

  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // -----------------------------------------
  // Feedback state
  // -----------------------------------------

  const [ratings, setRatings] = useState({});
  const [takenActions, setTakenActions] = useState({});
  const [outcomes, setOutcomes] = useState({});
  const [outcomeValues, setOutcomeValues] = useState({});
  const [feedbackStatus, setFeedbackStatus] = useState({});
  const [feedbackOpen, setFeedbackOpen] = useState(null);


  // -----------------------------------------
  // RUN ROOT CAUSE ANALYSIS
  // -----------------------------------------

  async function runAnalysis() {

    setError("");
    setResult(null);

    if (!file) {
      setError("Upload a CSV before analyzing a root cause.");
      return;
    }

    if (!selectedKpi) {
      setError("Select a KPI.");
      return;
    }

    if (!date) {
      setError("Select the anomaly date.");
      return;
    }

    setLoading(true);

    try {

      const formData = new FormData();

      formData.append("file", file);

      const params = new URLSearchParams();

      params.append("kpi", selectedKpi);
      params.append("date", date);
      params.append("window", String(windowSize));
      params.append("threshold", String(threshold));

      if (persona) {
        params.append("persona", persona);
      }

      const response = await fetch(
        `${API_URL}/narrative?${params.toString()}`,
        {
          method: "POST",
          body: formData,
        }
      );

      if (!response.ok) {

        let errorMessage =
          "Failed to generate root-cause narrative.";

        try {

          const errorData = await response.json();

          if (errorData.error) {
            errorMessage = errorData.error;
          }

        } catch {
          // Ignore JSON parsing error
        }

        throw new Error(errorMessage);
      }

      const data = await response.json();

      setResult(data);

    } catch (err) {

      setError(
        err.message ||
        "Something went wrong."
      );

    } finally {

      setLoading(false);
    }
  }
  async function handleDownloadReport() {
  if (!file || !selectedKpi || !date) {
    setError("Select a KPI and anomaly date first.");
    return;
  }

  try {
    setError("");
    await downloadReport(file, selectedKpi, date, windowSize, threshold);
  } catch (err) {
    setError(err.message || "Failed to generate PDF report.");
  }
  }

  // -----------------------------------------
  // EXTRACT NARRATIVE
  // -----------------------------------------

  function getNarrativeText() {

    if (!result) {
      return "";
    }

    if (result.narrative) {

      if (typeof result.narrative === "string") {
        return result.narrative;
      }

      if (result.narrative.narrative) {
        return result.narrative.narrative;
      }

      if (result.narrative.text) {
        return result.narrative.text;
      }

      if (result.narrative.explanation) {
        return result.narrative.explanation;
      }

      return JSON.stringify(
        result.narrative,
        null,
        2
      );
    }

    return "";
  }


  // -----------------------------------------
  // RENDER NARRATIVES
  // -----------------------------------------

  function renderNarratives() {

    if (!result) {
      return null;
    }

    if (result.narrative) {

      return (
        <NarrativeCard
          title={
            persona === "marketing_manager"
              ? "Marketing Manager"
              : persona === "sales_ops_manager"
              ? "Sales / Operations Manager"
              : "Root Cause Narrative"
          }
          text={getNarrativeText()}
        />
      );
    }

    if (result.narratives) {

      return (
        <div className="narrative-list">

          {Object.entries(result.narratives).map(
            ([personaName, narrative]) => {

              let text = narrative;

              if (typeof narrative !== "string") {

                if (narrative?.narrative) {
                  text = narrative.narrative;

                } else if (narrative?.text) {
                  text = narrative.text;

                } else if (narrative?.explanation) {
                  text = narrative.explanation;

                } else {
                  text = JSON.stringify(
                    narrative,
                    null,
                    2
                  );
                }
              }

              const title =
                personaName
                  .replaceAll("_", " ")
                  .replace(
                    /\b\w/g,
                    (letter) => letter.toUpperCase()
                  );

              return (
                <NarrativeCard
                  key={personaName}
                  title={title}
                  text={text}
                />
              );
            }
          )}

        </div>
      );
    }

    return null;
  }


  // -----------------------------------------
  // GET RECOMMENDATIONS
  // -----------------------------------------

  function getRecommendations() {

    if (!result) {
      return [];
    }

    const recommendationKeys = /recommend|suggest|action/i;
    function normalize(value, key = "") {
      if (typeof value === "string" && recommendationKeys.test(key)) {
        try { return normalize(JSON.parse(value), key); } catch { return value.trim() ? [value] : []; }
      }
      if (Array.isArray(value)) return value;
      if (value && typeof value === "object") {
        const values = Object.values(value);
        if (values.length && values.every((item) => typeof item === "string" || typeof item === "object")) return values;
      }
      return [];
    }
    function search(value, key = "") {
      if (typeof value === "string" && /^[\[{]/.test(value.trim())) {
        try { return search(JSON.parse(value), key); } catch { /* keep searching */ }
      }
      const direct = recommendationKeys.test(key) ? normalize(value, key) : [];
      if (direct.length) return direct;
      if (!value || typeof value !== "object") return [];
      for (const [childKey, childValue] of Object.entries(value)) {
        const found = search(childValue, childKey);
        if (found.length) return found;
      }
      return [];
    }
    const found = search(result);
    if (found.length) return found;

    // If the backend returned the statistical drivers but omitted the
    // decision-engine list, still give the analyst actionable suggestions.
    const drivers = Array.isArray(result.report?.drivers?.drivers_ranked) ? result.report.drivers.drivers_ranked : [];
    return drivers.slice(0, 3).map((driver) => ({
      action: `Investigate the ${driver.factor || "primary"} driver and apply a corrective action.`,
      lever: driver.factor || "Business driver",
      expected_impact: driver.pct_change != null ? `${driver.pct_change}% change to monitor` : "Review driver trend",
      monitor: driver.factor || "Selected KPI",
    }));
  }


  function recommendationText(item) {
    if (typeof item === "string") return item;
    return item?.action || item?.recommendation || item?.text || item?.title || item?.description || "Recommended action";
  }

  function renderRecommendationsCompact(recommendations, primaryDriver) {
    return (
      <section className="decision-engine">
        <div className="recommendations-heading">
          <div><span className="eyebrow">DECISION ENGINE</span><h3>Recommended actions</h3><p>Suggested next steps for the detected {String(primaryDriver).replaceAll("_", " ")} driver.</p></div>
          <span className="recommendation-count">{recommendations.length} suggestions</span>
        </div>
        <div className="recommendation-list">
          {recommendations.length === 0 && <div className="recommendation-empty">The API response did not include any recommendations for this analysis.</div>}
          {recommendations.map((action, index) => (
            <article className="recommendation-card compact-recommendation" key={index}>
              <div className="recommendation-header"><div><span className="recommendation-number">#{index + 1}</span><h4>{recommendationText(action)}</h4></div>{action?.score != null && <div className="recommendation-score">{Math.round(action.score * 100)}%</div>}</div>
              {(action?.lever || action?.owner || action?.expected_impact || action?.monitor) && <div className="recommendation-details"><div><span>Lever</span><strong>{action.lever || "—"}</strong></div><div><span>Owner</span><strong>{action.owner || "—"}</strong></div><div><span>Expected impact</span><strong>{action.expected_impact || "—"}</strong></div><div><span>Monitor</span><strong>{action.monitor || "—"}</strong></div></div>}
              <button type="button" className="feedback-trigger" onClick={() => setFeedbackOpen(index)}>Please give your feedback</button>
              {feedbackOpen === index && <div className="feedback-popover" role="dialog" aria-label={`Feedback for recommendation ${index + 1}`}>
                <div className="feedback-popover-header"><strong>Feedback for #{index + 1}</strong><button type="button" onClick={() => setFeedbackOpen(null)} aria-label="Close feedback">×</button></div>
                <div className="rating-row"><span>Rating:</span>{[1, 2, 3, 4, 5].map((rating) => <button key={rating} type="button" className={ratings[index] >= rating ? "star active" : "star"} onClick={() => setRatings((prev) => ({ ...prev, [index]: rating }))}>★</button>)}</div>
                <div className="taken-row"><span>Was it taken?</span><button type="button" className={takenActions[index] === true ? "feedback-button selected" : "feedback-button"} onClick={() => setTakenActions((prev) => ({ ...prev, [index]: true }))}>Yes</button><button type="button" className={takenActions[index] === false ? "feedback-button selected" : "feedback-button"} onClick={() => setTakenActions((prev) => ({ ...prev, [index]: false }))}>No</button></div>
                <textarea className="feedback-textarea" value={outcomes[index] || ""} onChange={(event) => setOutcomes((prev) => ({ ...prev, [index]: event.target.value }))} placeholder="Tell us what you think or what happened…" />
                <button type="button" className="feedback-submit" onClick={async () => { await submitFeedback(action, index); setFeedbackOpen(null); }}>Send feedback</button>
                {feedbackStatus[index] && <div className="feedback-status">{feedbackStatus[index]}</div>}
              </div>}
            </article>
          ))}
        </div>
      </section>
    );
  }

  // -----------------------------------------
  // SUBMIT FEEDBACK
  // -----------------------------------------

  async function submitFeedback(action, index) {

  setFeedbackStatus((prev) => ({
    ...prev,
    [index]: "Submitting..."
  }));

  try {

    // -----------------------------------------
    // Extract root-cause information
    // -----------------------------------------

    const report = result?.report || {};

    const drivers =
      report?.drivers?.drivers_ranked || [];

    const confidenceScore =
      report?.confidence?.score ?? null;

    const primaryDriver =
      result?.decision_engine?.primary_driver ||
      report?.drivers?.primary_driver ||
      selectedKpi;

    const primaryDriverChange =
      report?.drivers?.primary_driver_pct_change ?? null;


    // -----------------------------------------
    // Helper to find percentage change
    // for a specific business factor
    // -----------------------------------------

    function getFactorChange(factorName) {

      const factor = drivers.find(
        (item) => item.factor === factorName
      );

      return factor?.pct_change ?? null;
    }


    // -----------------------------------------
    // Send feedback + business context
    // -----------------------------------------

    const response = await fetch(
      `${API_URL}/feedback`,
      {
        method: "POST",

        headers: {
          "Content-Type": "application/json"
        },

        body: JSON.stringify({

          // Basic decision information
          kpi: selectedKpi,

          anomaly_date: date,

          root_cause: primaryDriver,

          recommended_action:
            recommendationText(action),


          // Analyst feedback
          analyst_rating:
            ratings[index] || null,

          action_taken:
            takenActions[index] ?? null,

          outcome:
            outcomes[index] || null,

          outcome_value:
            outcomeValues[index]
              ? Number(outcomeValues[index])
              : null,


          // -----------------------------------------
          // Business context for future ML
          // -----------------------------------------

          primary_driver_pct_change:
            primaryDriverChange,

          confidence_score:
            confidenceScore,

          visitors_change:
            getFactorChange("visitors"),

          orders_change:
            getFactorChange("orders"),

          revenue_change:
            getFactorChange("revenue"),

          aov_change:
            getFactorChange("aov"),

          cac_change:
            getFactorChange("cac"),

          ad_spend_change:
            getFactorChange("ad_spend")
        })
      }
    );


    const data = await response.json();


    if (!response.ok) {

      throw new Error(
        data.message ||
        data.error ||
        "Failed to save feedback."
      );
    }


    setFeedbackStatus((prev) => ({
      ...prev,
      [index]:
        `Saved ✓ Decision #${data.decision_id}`
    }));


  } catch (err) {

    setFeedbackStatus((prev) => ({
      ...prev,
      [index]:
        `Error: ${err.message}`
    }));

  }
}

  // -----------------------------------------
  // RECOMMENDATIONS UI
  // -----------------------------------------

  function renderRecommendations() {

    const recommendations = getRecommendations();

    if (!result) {
      return null;
    }

    const primaryDriver =
      result.decision_engine?.primary_driver ||
      result.root_cause?.decision_engine?.primary_driver ||
      selectedKpi;

    const compactRecommendations = renderRecommendationsCompact(recommendations, primaryDriver);
    if (compactRecommendations) return compactRecommendations;

    return (

      <div className="decision-engine">

        <div className="section-title">
          Recommended Actions
        </div>

        <div className="decision-summary">

          <span className="eyebrow">
            DECISION ENGINE
          </span>

          <strong>
            Main driver:{" "}
            {String(primaryDriver).replaceAll("_", " ")}
          </strong>

          <span>
            These recommendations are generated from
            the detected business driver.
          </span>

        </div>


        <div className="recommendation-list">

          {recommendations.map((action, index) => {

            return (

              <div
                className="recommendation-card"
                key={index}
              >

                {/* HEADER */}

                <div className="recommendation-header">

                  <div>

                    <span className="recommendation-number">
                      #{index + 1}
                    </span>

                    <h4>
                      {action.action}
                    </h4>

                  </div>

                  <div className="recommendation-score">

                    {Math.round(
                      (action.score ?? 0) * 100
                    )}%

                  </div>

                </div>


                {/* DETAILS */}

                <div className="recommendation-details">

                  <div>
                    <span>Lever</span>
                    <strong>
                      {action.lever || "—"}
                    </strong>
                  </div>

                  <div>
                    <span>Owner</span>
                    <strong>
                      {action.owner || "—"}
                    </strong>
                  </div>

                  <div>
                    <span>Expected Impact</span>
                    <strong>
                      {action.expected_impact || "—"}
                    </strong>
                  </div>

                  <div>
                    <span>Monitor</span>
                    <strong>
                      {action.monitor || "—"}
                    </strong>
                  </div>

                </div>


                {/* ANALYST FEEDBACK */}

                <div className="recommendation-feedback">

                  <div className="feedback-title">
                    Analyst Feedback
                  </div>


                  {/* RATING */}

                  <div className="rating-row">

                    <span>Rate this recommendation:</span>

                    {[1, 2, 3, 4, 5].map(
                      (rating) => (

                        <button
                          key={rating}
                          type="button"
                          className={
                            ratings[index] >= rating
                              ? "star active"
                              : "star"
                          }
                          onClick={() =>
                            setRatings((prev) => ({
                              ...prev,
                              [index]: rating
                            }))
                          }
                        >
                          ★
                        </button>

                      )
                    )}

                  </div>


                  {/* ACTION TAKEN */}

                  <div className="taken-row">

                    <span>
                      Was this action taken?
                    </span>

                    <button
                      type="button"
                      className={
                        takenActions[index] === true
                          ? "feedback-button selected"
                          : "feedback-button"
                      }
                      onClick={() =>
                        setTakenActions((prev) => ({
                          ...prev,
                          [index]: true
                        }))
                      }
                    >
                      Yes
                    </button>

                    <button
                      type="button"
                      className={
                        takenActions[index] === false
                          ? "feedback-button selected"
                          : "feedback-button"
                      }
                      onClick={() =>
                        setTakenActions((prev) => ({
                          ...prev,
                          [index]: false
                        }))
                      }
                    >
                      No
                    </button>

                  </div>


                  {/* OUTCOME */}

                  <div className="outcome-grid">

                    <label>

                      Outcome

                      <input
                        type="text"
                        placeholder="e.g. Revenue recovered"
                        value={outcomes[index] || ""}
                        onChange={(e) =>
                          setOutcomes((prev) => ({
                            ...prev,
                            [index]: e.target.value
                          }))
                        }
                      />

                    </label>


                    <label>

                      Outcome Value

                      <input
                        type="number"
                        step="0.1"
                        placeholder="e.g. 11.2"
                        value={
                          outcomeValues[index] || ""
                        }
                        onChange={(e) =>
                          setOutcomeValues((prev) => ({
                            ...prev,
                            [index]: e.target.value
                          }))
                        }
                      />

                    </label>

                  </div>


                  {/* SUBMIT */}

                  <button
                    type="button"
                    className="feedback-submit"
                    onClick={() =>
                      submitFeedback(action, index)
                    }
                  >
                    Save Decision
                  </button>


                  {/* STATUS */}

                  {feedbackStatus[index] && (

                    <div className="feedback-status">

                      {feedbackStatus[index]}

                    </div>

                  )}

                </div>

              </div>
            );
          })}

        </div>

      </div>
    );
  }


  // -----------------------------------------
  // MAIN UI
  // -----------------------------------------

  return (

    <div className="analysis-panel">

      {/* HEADER */}

      <div className="panel-intro">

        <div>

          <span className="eyebrow">
            AI EXPLANATION
          </span>

          <h2>
            Root Cause Analysis
          </h2>

          <p>
            Find out why a KPI became anomalous
            on a specific date and get recommended
            business actions.
          </p>

        </div>

      </div>


      {/* CONTROLS */}

      <div className="control-grid">

        <label>

          KPI

          <select
            value={selectedKpi}
            onChange={(e) =>
              onKpiSelect(e.target.value)
            }
          >

      {availableKpis.map((kpi) => (
       <option key={kpi} value={kpi}>
       {kpi.replaceAll("_", " ").replace(/\b\w/g, (c) => c.toUpperCase())}
       </option>
        ))}

          </select>

        </label>


        <label>

          Anomaly Date

          <input
            type="date"
            value={date}
            onChange={(e) =>
              setDate(e.target.value)
            }
          />

        </label>


        <label>

          Rolling Window

          <input
            type="number"
            min="1"
            value={windowSize}
            onChange={(e) =>
              setWindowSize(
                Number(e.target.value)
              )
            }
          />

        </label>


        <label>

          Threshold

          <input
            type="number"
            step="0.1"
            value={threshold}
            onChange={(e) =>
              setThreshold(
                Number(e.target.value)
              )
            }
          />

        </label>


        <label>

          Explain For

          <select
            value={persona}
            onChange={(e) =>
              setPersona(e.target.value)
            }
          >

            <option value="">
              All audiences
            </option>

            <option value="marketing_manager">
              Marketing Manager
            </option>

            <option value="sales_ops_manager">
              Sales / Operations Manager
            </option>

          </select>

        </label>


        <button
          className="primary-action"
          onClick={runAnalysis}
          disabled={loading}
        >

          {loading
            ? "Generating..."
            : "Find Root Cause"}

          <span>
            →
          </span>

        </button>

      </div>


      {/* ERROR */}

      {error && (

        <div className="error-box">
          {error}
        </div>

      )}


      {/* RESULT */}

      {result ? (

        <div className="root-cause-result">

          {/* ANALYSIS HEADER */}

          <div className="result-header">
          <div>
          <span className="eyebrow">ANALYSIS</span>
          <h3>{selectedKpi.replaceAll("_", " ")}</h3>
          </div>

         <div>
         <div className="result-date">{date}</div>

         <button
         type="button"
         className="primary-action"
         onClick={handleDownloadReport}
         disabled={!file || !date}
         style={{ marginTop: "8px" }}
         >
         Download PDF
         </button>
        </div>
        </div>


          {/* NARRATIVE */}

          <div className="narrative-section">

            <div className="section-title">
              AI Narrative
            </div>

            {renderNarratives()}

          </div>


          {/* RECOMMENDATIONS */}

          {renderRecommendations()}


          {/* RAW REPORT */}

          {result.report && (

            <details className="raw-report">

              <summary>
                View statistical analysis
              </summary>

              <pre>
                {JSON.stringify(
                  result.report,
                  null,
                  2
                )}
              </pre>

            </details>

          )}

        </div>

      ) : (

        <div className="empty-panel">

          <div className="empty-symbol">
            ⌕
          </div>

          <strong>

            {file
              ? "Select a KPI and anomaly date"
              : "Upload a CSV to begin"}

          </strong>

          <span>

            The AI-generated explanation
            and business recommendations
            will appear here.

          </span>

        </div>

      )}

    </div>
  );
}


/*
=====================================================
NARRATIVE CARD
=====================================================
*/

function NarrativeCard({
  title,
  text,
}) {

  return (

    <div className="narrative-card">

      <div className="narrative-card-header">

        <span className="narrative-icon">
          ✦
        </span>

        <strong>
          {title}
        </strong>

      </div>

      <div className="narrative-text">
        {text}
      </div>

    </div>

  );
}
