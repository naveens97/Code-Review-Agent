import { motion } from "framer-motion";
import { Sparkles, X } from "lucide-react";

export default function ReviewPrompt({ executionTimeMs, onAccept, onDismiss }) {
  return (
    <motion.div
      className="review-prompt"
      initial={{ opacity: 0, y: 24, scale: 0.97 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: 12, scale: 0.97 }}
      transition={{ type: "spring", stiffness: 300, damping: 24 }}
    >
      <div className="review-prompt-icon">
        <Sparkles size={16} />
      </div>
      <div className="review-prompt-text">
        <strong>Ran successfully in {executionTimeMs}ms.</strong>
        <span>Want a code review to see how it could be better?</span>
      </div>
      <button className="btn btn-review btn-sm" onClick={onAccept}>
        Get Recommendations
      </button>
      <button className="icon-btn" onClick={onDismiss} aria-label="Dismiss">
        <X size={15} />
      </button>
    </motion.div>
  );
}
