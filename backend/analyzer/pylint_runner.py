"""
Runs pylint against a code string and normalizes its JSON output into our
unified issue schema.
"""
import json
import os
import subprocess
import sys
import tempfile

from .recommendations import get_pylint_recommendation

PYLINT_TYPE_TO_SEVERITY = {
    "fatal": "critical",
    "error": "critical",
    "warning": "warning",
    "refactor": "warning",
    "convention": "info",
}

# Symbols that represent a genuine best-practice/design smell rather than
# pure style, used to steer the "category" badge shown in the UI.
BUG_LIKE_SYMBOLS = {
    "dangerous-default-value",
    "bare-except",
    "broad-exception-caught",
    "eval-used",
    "inconsistent-return-statements",
    "used-before-assignment",
    "undefined-variable",
    "comparison-with-callable",
    "unreachable",
}

COMPLEXITY_SYMBOLS = {
    "too-complex",
    "too-many-arguments",
    "too-many-positional-arguments",
    "too-many-branches",
    "too-many-locals",
    "too-many-statements",
    "too-many-nested-blocks",
}

# Rules that are disabled outright because they add noise without much
# teaching value for short, interview-style scripts.
DISABLED_RULES = [
    "missing-module-docstring",
]


def _categorize(pylint_type: str, symbol: str) -> str:
    if symbol in COMPLEXITY_SYMBOLS:
        return "complexity"
    if symbol in BUG_LIKE_SYMBOLS:
        return "bug"
    if pylint_type in ("error", "fatal"):
        return "bug"
    if pylint_type == "warning":
        return "bug"
    return "style"


def _map_message(msg: dict) -> dict:
    severity = PYLINT_TYPE_TO_SEVERITY.get(msg.get("type"), "info")
    symbol = msg.get("symbol") or msg.get("message-id", "unknown")
    rec = get_pylint_recommendation(symbol, msg.get("message", ""))
    return {
        "source": "pylint",
        "rule_id": symbol,
        "severity": severity,
        "category": _categorize(msg.get("type"), symbol),
        "line": msg.get("line"),
        "column": msg.get("column"),
        "message": msg.get("message", ""),
        "recommendation": rec["recommendation"],
        "before": rec["before"],
        "after": rec["after"],
    }


def run_pylint(code: str, timeout: int = 15, max_complexity: int = 10) -> list:
    """Returns a list of normalized issue dicts. Never raises -- on any
    tooling failure it returns an empty list so one broken tool can't take
    down the whole review."""
    issues = []
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "submission.py")
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(code)

            cmd = [
                sys.executable, "-m", "pylint",
                "--output-format=json",
                "--load-plugins=pylint.extensions.mccabe",
                f"--max-complexity={max_complexity}",
                f"--disable={','.join(DISABLED_RULES)}",
                "--jobs=1",
                "--persistent=n",
                filepath,
            ]
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=tmpdir,
            )
            raw = proc.stdout.strip()
            if raw:
                messages = json.loads(raw)
                for m in messages:
                    issues.append(_map_message(m))
    except subprocess.TimeoutExpired:
        issues.append({
            "source": "pylint", "rule_id": "analysis-timeout", "severity": "warning",
            "category": "tooling", "line": None, "column": None,
            "message": "Static analysis with pylint timed out.",
            "recommendation": "The file may be unusually large or complex. Try analyzing a smaller section.",
            "before": None, "after": None,
        })
    except (json.JSONDecodeError, FileNotFoundError, OSError):
        # pylint not installed, or produced unparsable output -- fail soft.
        pass
    return issues
