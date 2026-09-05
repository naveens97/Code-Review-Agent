import { motion } from "framer-motion";
import { History, Trash2 } from "lucide-react";
import { SUPPORTED_LANGUAGES } from "../constants";

const LANG_LABEL = Object.fromEntries(SUPPORTED_LANGUAGES.map(({ id, label }) => [id, label]));

function scoreColor(score) {
  if (score < 40) return "var(--critical)";
  if (score < 75) return "var(--warning)";
  return "var(--success)";
}

function timeAgo(isoString) {
  const diffMs = Date.now() - new Date(isoString).getTime();
  const mins = Math.floor(diffMs / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

export default function HistoryPanel({ items, isLoading, onSelect, onDelete }) {
  if (isLoading) {
    return (
      <div className="panel-content history-panel">
        <div className="skeleton" style={{ height: 52, marginBottom: 10 }} />
        <div className="skeleton" style={{ height: 52, marginBottom: 10 }} />
        <div className="skeleton" style={{ height: 52 }} />
      </div>
    );
  }

  if (!items || items.length === 0) {
    return (
      <div className="panel-content history-panel empty-state">
        <History size={30} strokeWidth={1.4} />
        <p>Reviews you run are saved here automatically.</p>
      </div>
    );
  }

  return (
    <div className="panel-content history-panel">
      {items.map((item) => (
        <motion.div
          key={item.id}
          className="history-item"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          onClick={() => onSelect(item.id)}
        >
          <div className="history-item-score" style={{ color: scoreColor(item.score) }}>
            {item.score}
          </div>
          <div className="history-item-main">
            <code className="history-item-preview mono">{item.preview || "(empty)"}</code>
            <div className="history-item-meta">
              <span>{item.label}</span>
              <span>·</span>
              <span className="lang-badge">{LANG_LABEL[item.language] ?? item.language ?? "Python"}</span>
              <span>·</span>
              <span>{timeAgo(item.created_at)}</span>
            </div>
          </div>
          <button
            className="icon-btn"
            onClick={(e) => {
              e.stopPropagation();
              onDelete(item.id);
            }}
            aria-label="Delete"
          >
            <Trash2 size={14} />
          </button>
        </motion.div>
      ))}
    </div>
  );
}

