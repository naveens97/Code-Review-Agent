import { motion } from "framer-motion";
import { CheckCircle2, Clock, TerminalSquare, XCircle } from "lucide-react";

function RunningIndicator() {
  return (
    <div className="running-indicator">
      <div className="running-bar">
        <div className="running-bar-fill" />
      </div>
      <div className="running-text mono">
        <span className="blink-cursor">▍</span> executing submission.py
      </div>
    </div>
  );
}

function StatusBadge({ result }) {
  if (result.timed_out) {
    return (
      <span className="status-badge status-badge-warning">
        <Clock size={13} /> Timed out
      </span>
    );
  }
  if (result.success) {
    return (
      <span className="status-badge status-badge-success">
        <CheckCircle2 size={13} /> Exit code 0
      </span>
    );
  }
  return (
    <span className="status-badge status-badge-critical">
      <XCircle size={13} /> Exit code {result.exit_code}
    </span>
  );
}

export default function OutputPanel({ isRunning, result, language = "python" }) {
  if (isRunning) {
    return (
      <div className="panel-content output-panel">
        <RunningIndicator />
      </div>
    );
  }

  if (!result) {
    const langLabel = language.charAt(0).toUpperCase() + language.slice(1);
    return (
      <div className="panel-content output-panel empty-state">
        <TerminalSquare size={30} strokeWidth={1.4} />
        <p>Write some {langLabel} code and hit Run to see output.</p>
        <p style={{ fontSize: 11, color: "var(--ink-faint)" }}>Ctrl+Enter to run quickly</p>
      </div>
    );
  }

  return (
    <motion.div
      className="panel-content output-panel"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, ease: "easeOut" }}
    >
      <div className="output-meta">
        <StatusBadge result={result} />
        <span className="output-timing mono">{result.execution_time_ms}ms</span>
      </div>

      {result.stdout && (
        <div className="output-block">
          <div className="output-block-label">stdout</div>
          <pre className="output-text">{result.stdout}</pre>
        </div>
      )}

      {result.stderr && (
        <div className="output-block">
          <div className="output-block-label output-block-label-error">stderr</div>
          <pre className="output-text output-text-error">{result.stderr}</pre>
        </div>
      )}

      {!result.stdout && !result.stderr && (
        <div className="output-block">
          <p className="dim-note">Program ran with no output.</p>
        </div>
      )}
    </motion.div>
  );
}
