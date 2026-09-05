"""
Python implementation of BaseAnalyzer: syntax check -> pylint -> bandit ->
custom AST checks -> dedupe -> rating -> summary.

This is the exact logic that used to live directly in analyzer/engine.py
as a bare analyze_code() function. Moving it behind BaseAnalyzer didn't
change what it does -- it changed how it's reached, so that
analyzer/__init__.py can pick between this and (eventually) a
JavaScriptAnalyzer, JavaAnalyzer, etc. based on the submitted code's
language, without app.py or the frontend needing to know analyzers other
than "python" exist yet.
"""
import ast

from .bandit_runner import run_bandit
from .base import BaseAnalyzer
from .custom_checks import basic_metrics, run_custom_checks
from .pylint_runner import run_pylint
from .rating import compute_rating

SEVERITY_ORDER = {"critical": 0, "warning": 1, "info": 2}


def _check_syntax(code: str):
    """Returns (has_error, issue_or_None)."""
    try:
        ast.parse(code)
        return False, None
    except SyntaxError as e:
        return True, {
            "source": "python",
            "rule_id": "syntax-error",
            "severity": "critical",
            "category": "bug",
            "line": e.lineno,
            "column": e.offset,
            "message": f"{e.msg}",
            "recommendation": (
                "The code can't be parsed, so nothing after this point could be checked "
                "either. Fix this syntax error first, then re-run the review to see "
                "everything else."
            ),
            "before": None,
            "after": None,
        }


def _dedupe(issues: list) -> list:
    """Pylint independently reports its own fatal syntax-error message when
    a file doesn't parse, which would otherwise duplicate our own syntax
    check. Keep only the first syntax-error-flavored issue."""
    seen_syntax_error = False
    result = []
    for issue in issues:
        if issue["rule_id"] in ("syntax-error", "E0001"):
            if seen_syntax_error:
                continue
            seen_syntax_error = True
        result.append(issue)
    return result


def _sort_issues(issues: list) -> list:
    return sorted(
        issues,
        key=lambda i: (SEVERITY_ORDER.get(i["severity"], 3), i["line"] or 0),
    )


def _build_summary(issues: list, rating: dict, has_syntax_error: bool) -> str:
    if has_syntax_error:
        return "This code has a syntax error and couldn't be fully analyzed. Fix it first, then run the review again for a complete report."

    counts = rating["breakdown"]
    if not issues:
        return "No issues found. The code follows Python best practices as far as static analysis can tell -- nice work."

    parts = []
    if counts["critical"]:
        parts.append(f"{counts['critical']} critical issue{'s' if counts['critical'] != 1 else ''}")
    if counts["warning"]:
        parts.append(f"{counts['warning']} warning{'s' if counts['warning'] != 1 else ''}")
    if counts["info"]:
        parts.append(f"{counts['info']} suggestion{'s' if counts['info'] != 1 else ''}")

    headline = ", ".join(parts) + " found."

    if counts["critical"] > 0:
        top_critical = next((i for i in issues if i["severity"] == "critical"), None)
        if top_critical and top_critical["line"]:
            headline += f" Start with the critical issue at line {top_critical['line']}."
    elif counts["warning"] > 0:
        headline += " Nothing critical, but the warnings below are worth fixing before this ships."
    else:
        headline += " These are minor -- the code is solid overall."

    return headline


class PythonAnalyzer(BaseAnalyzer):
    def analyze(self, code: str, max_complexity: int = 10) -> dict:
        has_syntax_error, syntax_issue = _check_syntax(code)

        issues = []
        if syntax_issue:
            issues.append(syntax_issue)

        # Even with a syntax error, still attempt pylint/bandit -- they may
        # surface a clearer message, or (for partially-valid files) still
        # produce useful signal. Both fail soft on their own.
        issues += run_pylint(code, max_complexity=max_complexity)
        issues += run_bandit(code)
        if not has_syntax_error:
            issues += run_custom_checks(code)

        issues = _dedupe(issues)
        issues = _sort_issues(issues)

        rating = compute_rating(issues, has_syntax_error=has_syntax_error)
        metrics = basic_metrics(code)
        summary = _build_summary(issues, rating, has_syntax_error)

        return {
            "rating": rating,
            "issues": issues,
            "summary": summary,
            "metrics": metrics,
            "has_syntax_error": has_syntax_error,
        }
