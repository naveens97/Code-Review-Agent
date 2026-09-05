import { ChevronDown, Play, Sparkles } from "lucide-react";
import { SUPPORTED_LANGUAGES } from "../constants";

export default function Toolbar({ language, onLanguageChange, onRun, onReview, isRunning, isReviewing }) {
  const currentLabel = SUPPORTED_LANGUAGES.find((l) => l.id === language)?.label ?? language;

  return (
    <div className="toolbar">
      <div className="toolbar-left">
        <button
          className="btn btn-run"
          onClick={onRun}
          disabled={isRunning}
          title="Run this code (Ctrl+Enter)"
          id="btn-run"
        >
          {isRunning ? <span className="btn-spinner" /> : <Play size={15} fill="currentColor" />}
          {isRunning ? "Running…" : "Run"}
        </button>
        <button
          className="btn btn-review"
          onClick={onReview}
          disabled={isReviewing}
          title="Get a code quality review"
          id="btn-review"
        >
          {isReviewing ? <span className="btn-spinner" /> : <Sparkles size={15} />}
          {isReviewing ? "Reviewing…" : "Review"}
        </button>
      </div>

      <div className="toolbar-right">
        <div className="lang-select-wrap">
          <span className="lang-dot" />
          <span className="lang-select-label">{currentLabel}</span>
          <ChevronDown size={14} style={{ color: "var(--ink-faint)", pointerEvents: "none" }} />
          <select
            className="lang-select-native"
            value={language}
            onChange={(e) => onLanguageChange(e.target.value)}
            title="Select programming language"
            id="lang-select"
          >
            {SUPPORTED_LANGUAGES.map(({ id, label }) => (
              <option key={id} value={id}>
                {label}
              </option>
            ))}
          </select>
        </div>
      </div>
    </div>
  );
}
