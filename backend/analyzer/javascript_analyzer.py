"""
JavaScript static analyzer.

Primary engine : ESLint (subprocess, --format json).
Fallback        : Basic syntax check via Node --check if ESLint is not
                  installed.  Even without ESLint, the analyzer still
                  returns a valid report; it just surfaces fewer issues.

ESLint rules that map to our severity schema
  error (2)   -> critical
  warn  (1)   -> warning
  (no info-level equivalent in eslint; we map rule categories below)

To install ESLint globally so this analyzer can find it:
  npm install -g eslint
"""

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from .base import BaseAnalyzer
from .rating import compute_rating

# ---------------------------------------------------------------------------
# ESLint severity mapping
# ---------------------------------------------------------------------------
_ESLINT_SEVERITY = {
    2: "critical",
    1: "warning",
    0: "info",
}

# Rules we want to annotate with a curated explanation.
_JS_RECOMMENDATIONS = {
    "no-var": {
        "explanation": "var has function scope, not block scope, which leads to hard-to-trace bugs around loops and closures. Use let for mutable bindings and const for everything else.",
        "before": "var count = 0;",
        "after": "let count = 0;",
    },
    "no-unused-vars": {
        "explanation": "This variable is declared but never used. Remove it or prefix with _ to signal it's intentionally unused.",
    },
    "eqeqeq": {
        "explanation": "== performs type coercion, so '0' == 0 is true. Use === (strict equality) to compare value AND type.",
        "before": "if (x == null)",
        "after": "if (x === null || x === undefined)",
    },
    "no-undef": {
        "explanation": "This variable is used but never declared. Check for a typo, a missing import, or a missing global declaration.",
    },
    "no-console": {
        "explanation": "console.log statements left in production code can leak sensitive data and hurt performance. Remove them or replace with a proper logging library.",
    },
    "no-eval": {
        "explanation": "eval() executes arbitrary strings as JavaScript — a serious security risk if any part comes from user input. Restructure your logic to avoid it.",
    },
    "no-implicit-globals": {
        "explanation": "Variables declared without let/const/var inside a function become implicit globals and can clobber each other across modules.",
    },
    "prefer-const": {
        "explanation": "This variable is never reassigned after declaration. Use const to communicate that intent and prevent accidental mutation.",
        "before": "let name = 'Alice';",
        "after": "const name = 'Alice';",
    },
    "no-shadow": {
        "explanation": "This variable shadows a variable in an outer scope. Both names become harder to reason about — rename one of them.",
    },
    "no-throw-literal": {
        "explanation": "Only Error objects (or subclasses) should be thrown so callers can reliably catch and inspect them. Throwing a plain string loses the stack trace.",
        "before": "throw 'Something went wrong';",
        "after": "throw new Error('Something went wrong');",
    },
    "semi": {
        "explanation": "JavaScript has Automatic Semicolon Insertion (ASI), but it can behave unexpectedly. Being explicit avoids subtle bugs.",
    },
    "no-unreachable": {
        "explanation": "This code is unreachable — it comes after a return, throw, or break. It will never execute; remove it.",
    },
    "no-duplicate-case": {
        "explanation": "This switch case label is duplicated. The second branch can never be reached.",
    },
    "no-empty": {
        "explanation": "Empty block statements are usually a mistake. If intentional, add a comment to make it clear.",
    },
    "use-isnan": {
        "explanation": "Comparing to NaN with == or === always returns false. Use Number.isNaN() instead.",
        "before": "if (x == NaN)",
        "after": "if (Number.isNaN(x))",
    },
}

# Minimal ESLint config written to the temp dir when linting.
_ESLINT_CONFIG = {
    "env": {"browser": True, "node": True, "es2022": True},
    "parserOptions": {"ecmaVersion": "latest", "sourceType": "module"},
    "rules": {
        "no-var": "warn",
        "no-unused-vars": "warn",
        "eqeqeq": "warn",
        "no-undef": "error",
        "no-console": "warn",
        "no-eval": "error",
        "prefer-const": "warn",
        "no-shadow": "warn",
        "no-throw-literal": "warn",
        "no-unreachable": "error",
        "no-duplicate-case": "error",
        "no-empty": "warn",
        "use-isnan": "error",
    },
}


def _find_eslint() -> str | None:
    """Return the path to eslint if it can be found on PATH, else None."""
    for candidate in ("eslint", "eslint.cmd"):
        try:
            result = subprocess.run(
                [candidate, "--version"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0:
                return candidate
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
    return None


def _run_eslint(code: str, eslint_bin: str) -> list:
    """Run ESLint on *code* and return a list of issue dicts."""
    issues = []
    with tempfile.TemporaryDirectory() as tmpdir:
        src = os.path.join(tmpdir, "submission.js")
        cfg = os.path.join(tmpdir, ".eslintrc.json")
        with open(src, "w", encoding="utf-8") as fh:
            fh.write(code)
        with open(cfg, "w", encoding="utf-8") as fh:
            json.dump(_ESLINT_CONFIG, fh)

        try:
            proc = subprocess.run(
                [eslint_bin, "--format", "json", "--no-eslintrc", "-c", cfg, src],
                capture_output=True, text=True, timeout=20,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return []

        raw = proc.stdout.strip()
        if not raw:
            return []

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return []

        for file_result in data:
            for msg in file_result.get("messages", []):
                rule = msg.get("ruleId") or "eslint"
                sev_int = msg.get("severity", 1)
                severity = _ESLINT_SEVERITY.get(sev_int, "warning")
                rec = _JS_RECOMMENDATIONS.get(rule, {})
                issues.append({
                    "source": "eslint",
                    "rule_id": rule,
                    "severity": severity,
                    "category": _categorize(rule),
                    "line": msg.get("line"),
                    "column": msg.get("column"),
                    "message": msg.get("message", ""),
                    "recommendation": rec.get("explanation", msg.get("message", "")),
                    "before": rec.get("before"),
                    "after": rec.get("after"),
                })
    return issues


def _node_syntax_check(code: str) -> list:
    """Lightweight fallback: use `node --check` to catch parse errors only."""
    issues = []
    with tempfile.TemporaryDirectory() as tmpdir:
        src = os.path.join(tmpdir, "submission.js")
        with open(src, "w", encoding="utf-8") as fh:
            fh.write(code)
        try:
            proc = subprocess.run(
                ["node", "--check", src],
                capture_output=True, text=True, timeout=10,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return [{
                "source": "javascript",
                "rule_id": "runtime-not-found",
                "severity": "info",
                "category": "tooling",
                "line": None, "column": None,
                "message": "Node.js not found — install Node.js to enable syntax checking.",
                "recommendation": "Install Node.js (https://nodejs.org) to enable JavaScript execution and analysis.",
                "before": None, "after": None,
            }]

        if proc.returncode != 0:
            # Parse Node's SyntaxError output: "file.js:3\n  bad code\n  ^\nSyntaxError: ..."
            line_match = re.search(r":(\d+)\n", proc.stderr)
            line = int(line_match.group(1)) if line_match else None
            msg_match = re.search(r"SyntaxError: (.+)", proc.stderr)
            msg = msg_match.group(1) if msg_match else proc.stderr.strip()
            issues.append({
                "source": "javascript",
                "rule_id": "syntax-error",
                "severity": "critical",
                "category": "bug",
                "line": line, "column": None,
                "message": f"SyntaxError: {msg}",
                "recommendation": "Fix this syntax error first. Everything else depends on the code parsing cleanly.",
                "before": None, "after": None,
            })
    return issues


def _basic_metrics(code: str) -> dict:
    lines = code.splitlines()
    code_lines = sum(1 for ln in lines if ln.strip() and not ln.strip().startswith("//"))
    functions = len(re.findall(r"\bfunction\b|\b=>\s*{|\b(?:async\s+)?function\s*\w*\s*\(", code))
    classes = len(re.findall(r"\bclass\s+\w+", code))
    return {"code_lines": code_lines, "functions": functions, "classes": classes}


def _categorize(rule_id: str) -> str:
    security_rules = {"no-eval", "no-new-func", "no-implied-eval"}
    style_rules = {"semi", "quotes", "indent", "eol-last", "no-trailing-spaces"}
    bug_rules = {"no-unreachable", "no-duplicate-case", "use-isnan", "no-undef",
                 "no-dupe-keys", "no-dupe-args", "no-cond-assign"}
    if rule_id in security_rules:
        return "security"
    if rule_id in style_rules:
        return "style"
    if rule_id in bug_rules:
        return "bug"
    return "best-practice"


def _build_summary(issues: list, rating: dict) -> str:
    if not issues:
        return "No issues found. The JavaScript looks clean as far as static analysis can tell."
    counts = rating["breakdown"]
    parts = []
    if counts["critical"]:
        parts.append(f"{counts['critical']} critical issue{'s' if counts['critical'] != 1 else ''}")
    if counts["warning"]:
        parts.append(f"{counts['warning']} warning{'s' if counts['warning'] != 1 else ''}")
    if counts["info"]:
        parts.append(f"{counts['info']} suggestion{'s' if counts['info'] != 1 else ''}")
    headline = ", ".join(parts) + " found."
    if counts["critical"] > 0:
        first = next((i for i in issues if i["severity"] == "critical"), None)
        if first and first["line"]:
            headline += f" Start with the critical issue at line {first['line']}."
    elif counts["warning"] > 0:
        headline += " Nothing critical, but the warnings are worth fixing."
    else:
        headline += " These are minor — the code is solid overall."
    return headline


class JavaScriptAnalyzer(BaseAnalyzer):
    def analyze(self, code: str, **kwargs) -> dict:
        eslint_bin = _find_eslint()
        has_syntax_error = False

        if eslint_bin:
            issues = _run_eslint(code, eslint_bin)
            # Check if any critical is a syntax error
            has_syntax_error = any(
                i["rule_id"] in ("syntax-error", "parsing-error") and i["severity"] == "critical"
                for i in issues
            )
        else:
            # Fallback: node --check only
            issues = _node_syntax_check(code)
            has_syntax_error = any(i["rule_id"] == "syntax-error" for i in issues)
            if not has_syntax_error and not issues:
                # Node not found either -- add an info note
                issues = [{
                    "source": "javascript",
                    "rule_id": "eslint-not-found",
                    "severity": "info",
                    "category": "tooling",
                    "line": None, "column": None,
                    "message": "ESLint is not installed — install it for full JavaScript analysis.",
                    "recommendation": (
                        "Run `npm install -g eslint` to enable comprehensive JavaScript static analysis. "
                        "Without it, only basic syntax checking is available via Node."
                    ),
                    "before": None, "after": None,
                }]

        # Sort: critical first, then by line
        issues.sort(key=lambda i: ({"critical": 0, "warning": 1, "info": 2}.get(i["severity"], 3), i["line"] or 0))

        rating = compute_rating(issues, has_syntax_error=has_syntax_error)
        metrics = _basic_metrics(code)
        summary = _build_summary(issues, rating)

        return {
            "rating": rating,
            "issues": issues,
            "summary": summary,
            "metrics": metrics,
            "has_syntax_error": has_syntax_error,
        }
