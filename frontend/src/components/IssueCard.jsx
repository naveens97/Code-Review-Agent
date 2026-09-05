import { motion } from "framer-motion";
import { AlertCircle, AlertTriangle, ChevronRight, Info, MapPin } from "lucide-react";
import { useState } from "react";
import ReactMarkdown from "react-markdown";
import { CATEGORY_LABELS } from "../constants";

const ICONS = { critical: AlertCircle, warning: AlertTriangle, info: Info };

export default function IssueCard({ issue, onJumpToLine }) {
  const [open, setOpen] = useState(false);
  const Icon = ICONS[issue.severity] || Info;

  return (
    <motion.div
      className={`issue-card issue-card-${issue.severity}`}
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
    >
      <button className="issue-card-header" onClick={() => setOpen((o) => !o)}>
        <Icon size={16} className="issue-icon" />
        <div className="issue-card-main">
          <div className="issue-card-toprow">
            <span className="issue-category">{CATEGORY_LABELS[issue.category] || issue.category}</span>
            {issue.line != null && (
              <button
                className="issue-line-link"
                onClick={(e) => {
                  e.stopPropagation();
                  onJumpToLine?.(issue.line);
                }}
              >
                <MapPin size={11} /> line {issue.line}
              </button>
            )}
          </div>
          <p className={`issue-message ${!open ? "issue-message-truncate" : ""}`}>{issue.message}</p>
        </div>
        <ChevronRight size={16} className={`issue-chevron ${open ? "issue-chevron-open" : ""}`} />
      </button>

      {open && (
        <div className="issue-card-body">
          <div className="issue-recommendation">
            <ReactMarkdown>{issue.recommendation}</ReactMarkdown>
          </div>
          {issue.before && (
            <div className="issue-diff">
              <div className="issue-diff-block issue-diff-before">
                <span className="issue-diff-label">Before</span>
                <pre>{issue.before}</pre>
              </div>
              <div className="issue-diff-block issue-diff-after">
                <span className="issue-diff-label">After</span>
                <pre>{issue.after}</pre>
              </div>
            </div>
          )}
          <span className="issue-rule-id mono">{issue.source}: {issue.rule_id}</span>
        </div>
      )}
    </motion.div>
  );
}
