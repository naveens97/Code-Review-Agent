import { ChevronDown, Terminal } from "lucide-react";
import { useState } from "react";

/**
 * Collapsible stdin textarea that sits below the code editor.
 * Collapsed by default so it doesn't intrude on users who don't need it.
 */
export default function StdinPanel({ value, onChange }) {
  const [open, setOpen] = useState(false);

  return (
    <div className={`stdin-panel ${open ? "stdin-panel-open" : ""}`}>
      <button
        className="stdin-toggle"
        onClick={() => setOpen((o) => !o)}
        title={open ? "Collapse stdin" : "Expand stdin input"}
        id="stdin-toggle"
      >
        <Terminal size={13} />
        <span>stdin</span>
        {value && !open && (
          <span className="stdin-has-value" title="stdin has content" />
        )}
        <ChevronDown
          size={13}
          className={`stdin-chevron ${open ? "stdin-chevron-open" : ""}`}
        />
      </button>

      {open && (
        <textarea
          className="stdin-textarea"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="Provide input for your program here (piped to stdin when Run is clicked)…"
          spellCheck={false}
          id="stdin-textarea"
          rows={4}
        />
      )}
    </div>
  );
}
