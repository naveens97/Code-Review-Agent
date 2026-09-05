import { motion } from "framer-motion";
import { ClipboardList, Search } from "lucide-react";
import IssueList from "./IssueList";
import RatingGauge from "./RatingGauge";

function AnalyzingState() {
  return (
    <div className="analyzing-state">
      <div className="analyzing-icon">
        <Search size={22} />
      </div>
      <p>Running pylint, bandit, and structural checks…</p>
      <div className="skeleton" style={{ height: 90, width: 180, borderRadius: 90, margin: "8px auto" }} />
      <div className="skeleton" style={{ height: 14, width: "80%", margin: "6px auto" }} />
      <div className="skeleton" style={{ height: 14, width: "60%", margin: "6px auto" }} />
    </div>
  );
}

export default function ReviewPanel({ isReviewing, review, onJumpToLine }) {
  if (isReviewing) {
    return (
      <div className="panel-content review-panel">
        <AnalyzingState />
      </div>
    );
  }

  if (!review) {
    return (
      <div className="panel-content review-panel empty-state">
        <ClipboardList size={30} strokeWidth={1.4} />
        <p>Click Review to get a scored report with specific fixes.</p>
      </div>
    );
  }

  return (
    <motion.div
      className="panel-content review-panel"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.2 }}
    >
      <div className="review-top">
        <RatingGauge score={review.rating.score} label={review.rating.label} />
        <div className="review-summary">
          <p>{review.summary}</p>
          <div className="review-metrics mono">
            <span>{review.metrics.code_lines} lines</span>
            <span>{review.metrics.functions} functions</span>
            {review.metrics.classes > 0 && <span>{review.metrics.classes} classes</span>}
          </div>
        </div>
      </div>

      {review.issues.length > 0 ? (
        <IssueList issues={review.issues} onJumpToLine={onJumpToLine} />
      ) : (
        <div className="all-clear">✓ No issues found by static analysis.</div>
      )}
    </motion.div>
  );
}
