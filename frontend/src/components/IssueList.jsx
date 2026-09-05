import { SEVERITY_META } from "../constants";
import IssueCard from "./IssueCard";

export default function IssueList({ issues, onJumpToLine }) {
  const groups = { critical: [], warning: [], info: [] };
  for (const issue of issues) {
    (groups[issue.severity] || groups.info).push(issue);
  }

  return (
    <div className="issue-list">
      {["critical", "warning", "info"].map((severity) => {
        const group = groups[severity];
        if (group.length === 0) return null;
        const meta = SEVERITY_META[severity];
        return (
          <div key={severity} className="issue-group">
            <div className="issue-group-header" style={{ color: meta.color }}>
              <span className="issue-group-dot" style={{ background: meta.color }} />
              {meta.label}
              <span className="issue-group-count">{group.length}</span>
            </div>
            {group.map((issue, idx) => (
              <IssueCard key={`${severity}-${idx}`} issue={issue} onJumpToLine={onJumpToLine} />
            ))}
          </div>
        );
      })}
    </div>
  );
}
