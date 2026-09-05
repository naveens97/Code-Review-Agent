"""
Runs bandit (a dedicated Python security linter) against a code string and
normalizes its JSON output into our unified issue schema.

We use bandit specifically for the "security vulnerabilities" dimension of
the rating -- eval/exec, shell injection, hardcoded secrets, insecure
deserialization, weak hashing, and similar. pylint doesn't cover this
category well, so the two tools are complementary, not redundant.
"""
import json
import os
import subprocess
import sys
import tempfile

from .recommendations import get_bandit_recommendation

# bandit's own severity is about how bad the issue is IF it's real;
# confidence is how sure bandit is that it correctly identified the
# pattern. A HIGH-severity but LOW-confidence hit is downgraded one tier
# so a shaky guess doesn't read as an unambiguous critical alarm.
SEVERITY_RANK = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}
OUR_SEVERITY_BY_RANK = {0: "info", 1: "warning", 2: "critical"}


def _map_result(r: dict) -> dict:
    sev_rank = SEVERITY_RANK.get(r.get("issue_severity", "LOW"), 0)
    conf_rank = SEVERITY_RANK.get(r.get("issue_confidence", "LOW"), 0)
    if conf_rank < sev_rank:
        sev_rank = max(0, sev_rank - 1)
    severity = OUR_SEVERITY_BY_RANK[sev_rank]

    test_id = r.get("test_id", "")
    rec = get_bandit_recommendation(test_id, r.get("issue_text", ""))

    return {
        "source": "bandit",
        "rule_id": test_id,
        "severity": severity,
        "category": "security",
        "line": r.get("line_number"),
        "column": r.get("col_offset"),
        "message": r.get("issue_text", ""),
        "recommendation": rec["recommendation"],
        "before": rec["before"],
        "after": rec["after"],
    }


def run_bandit(code: str, timeout: int = 15) -> list:
    """Returns a list of normalized issue dicts. Never raises."""
    issues = []
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "submission.py")
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(code)

            cmd = [sys.executable, "-m", "bandit", "-f", "json", "-q", filepath]
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=tmpdir,
            )
            raw = proc.stdout.strip()
            if raw:
                data = json.loads(raw)
                for r in data.get("results", []):
                    issues.append(_map_result(r))
    except subprocess.TimeoutExpired:
        issues.append({
            "source": "bandit", "rule_id": "analysis-timeout", "severity": "warning",
            "category": "tooling", "line": None, "column": None,
            "message": "Security analysis with bandit timed out.",
            "recommendation": "The file may be unusually large. Try analyzing a smaller section.",
            "before": None, "after": None,
        })
    except (json.JSONDecodeError, FileNotFoundError, OSError):
        pass
    return issues
