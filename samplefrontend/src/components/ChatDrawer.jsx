export default function ChatDrawer({
  open,
  messages,
  loading,
  inputValue,
  onInputChange,
  onSubmit,
  onClose,
  pdfFile,
  onPdfSelect
}) {
  if (!open) return null;

  return (
    <div className="chat-drawer-layer" role="presentation" onMouseDown={onClose}>
      <aside
        className="chat-drawer"
        role="dialog"
        aria-modal="true"
        aria-label="BID assistant"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <header className="chat-drawer-header">
          <div className="chat-drawer-title">
            <span className="robot-avatar" aria-hidden="true">🤖</span>
            <div>
              <span className="eyebrow">BID</span>
              <h2>BID</h2>
            </div>
          </div>

          <button
            type="button"
            className="chat-drawer-close"
            onClick={onClose}
            aria-label="Close assistant"
          >
            ×
          </button>
        </header>

        <div className="chat-messages">
          {messages.length === 0 && (
            <div className="chat-empty-state">
              <strong>Ask BID about your data</strong>
              <span>Upload a CSV or attach a PDF, then ask your question.</span>
            </div>
          )}

          {messages.map((item, index) => (
            <div
              className={`chat-message ${item.role}`}
              key={`${item.role}-${index}`}
            >
              <span>{item.role === "user" ? "You" : "BID"}</span>
              <p>{item.content}</p>
            </div>
          ))}

          {loading && (
            <div className="chat-message assistant">
              <span>BID</span>
              <p>Thinking…</p>
            </div>
          )}
        </div>

        {pdfFile && (
          <div className="chat-file-preview">
            <span>📄</span>
            <span>{pdfFile.name}</span>
            <button
              type="button"
              onClick={() => onPdfSelect(null)}
              aria-label="Remove PDF"
            >
              ×
            </button>
          </div>
        )}

        <form className="chat-drawer-composer" onSubmit={onSubmit}>
          <label
            className="chat-attach-button"
            title="Attach PDF"
          >
            +
            <input
              type="file"
              accept=".pdf,application/pdf"
              hidden
              onChange={(event) => {
                const selected = event.target.files?.[0];
                if (selected) onPdfSelect(selected);
                event.target.value = "";
              }}
            />
          </label>

          <input
            value={inputValue}
            onChange={(event) => onInputChange(event.target.value)}
            placeholder={
              pdfFile
                ? "Ask about the PDF…"
                : "Ask about your KPI data…"
            }
            aria-label="Chat message"
          />

          <button
            type="submit"
            disabled={loading || !inputValue.trim()}
          >
            Send
          </button>
        </form>
      </aside>
    </div>
  );
}