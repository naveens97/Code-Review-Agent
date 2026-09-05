"""
Java static analyzer.

Primary engine: javac (JDK compiler).
  - Runs `javac -Xlint:all <file>` and parses its stderr.
  - Even without finding bugs, this catches all syntax errors and
    type errors that Python/ESLint-style analysis can't reach.

Requires: JDK installed with `javac` on PATH.
"""

import os
import re
import subprocess
import tempfile

from .base import BaseAnalyzer
from .rating import compute_rating

# ---------------------------------------------------------------------------
# javac warning/error → our severity
# ---------------------------------------------------------------------------
# javac output format:
#   <file>:<line>: error: <message>
#   <file>:<line>: warning: <message>
_LINE_RE = re.compile(
    r"(?:[^\n:]+):(\d+):\s*(error|warning|note):\s*(.+)"
)

_JAVA_RECOMMENDATIONS = {
    "variable might not have been initialized": {
        "explanation": "Java requires every local variable to be definitely assigned before use. Assign a default value (e.g. 0, null, or \"\") when you declare it.",
        "before": "int x;\nSystem.out.println(x); // error",
        "after": "int x = 0;\nSystem.out.println(x);",
    },
    "cannot find symbol": {
        "explanation": "The compiler can't find this identifier. Check for typos, missing imports, wrong capitalization, or a variable declared in the wrong scope.",
    },
    "incompatible types": {
        "explanation": "You're assigning or passing a value of the wrong type. Use an explicit cast if the conversion is intentional, or fix the type mismatch.",
    },
    "reached end of file while parsing": {
        "explanation": "A closing brace, parenthesis, or bracket is missing. Count your braces — the compiler ran out of file looking for one.",
    },
    "class, interface, or enum expected": {
        "explanation": "Top-level Java code must be inside a class. Wrap your code in `public class Main { public static void main(String[] args) { ... } }`.",
    },
    "method does not override or implement a method from a supertype": {
        "explanation": "@Override is present but the method signature doesn't match the supertype. Check the method name, return type, and parameter types exactly.",
    },
    "unchecked or unsafe operations": {
        "explanation": "Generic type safety is being bypassed (raw types or unchecked casts). Add proper type parameters or use @SuppressWarnings(\"unchecked\") with a comment explaining why it's safe.",
    },
    "possible lossy conversion": {
        "explanation": "You're converting a larger numeric type to a smaller one (e.g. double → int), which can silently lose data. Add an explicit cast if intentional: (int) value.",
        "before": "int x = 3.14;",
        "after": "int x = (int) 3.14; // loses decimal part",
    },
    "unreachable statement": {
        "explanation": "This statement can never be reached — it's after a return, throw, or unconditional break. Remove it.",
    },
    "missing return statement": {
        "explanation": "Not all code paths in this method return a value. Make sure every branch either returns a value or throws an exception.",
    },
    "non-static method cannot be referenced from a static context": {
        "explanation": "You're calling an instance method from a static method (like main). Either make the method static, or create an instance of the class first.",
        "before": "public static void main(String[] args) {\n    greet(); // non-static\n}",
        "after": "public static void main(String[] args) {\n    Main obj = new Main();\n    obj.greet();\n}",
    },
    "non-static variable cannot be referenced from a static context": {
        "explanation": "You're accessing an instance field from a static method. Either make the field static, or access it through an instance.",
    },
    ";": {
        "explanation": "A semicolon is missing at the end of a statement.",
    },
}


def _match_recommendation(message: str) -> dict:
    msg_lower = message.lower()
    for key, rec in _JAVA_RECOMMENDATIONS.items():
        if key.lower() in msg_lower:
            return rec
    return {}


def _severity_from_kind(kind: str) -> str:
    if kind == "error":
        return "critical"
    if kind == "warning":
        return "warning"
    return "info"  # 'note'


def _parse_javac_output(stderr: str) -> list:
    """Parse javac's stderr into our issue format."""
    issues = []
    seen = set()  # (line, message) dedup key

    for match in _LINE_RE.finditer(stderr):
        line_no = int(match.group(1))
        kind = match.group(2)
        message = match.group(3).strip()

        key = (line_no, message)
        if key in seen:
            continue
        seen.add(key)

        rec = _match_recommendation(message)
        severity = _severity_from_kind(kind)

        issues.append({
            "source": "javac",
            "rule_id": f"javac-{kind}",
            "severity": severity,
            "category": "bug" if kind == "error" else "style",
            "line": line_no,
            "column": None,
            "message": message,
            "recommendation": rec.get("explanation", message),
            "before": rec.get("before"),
            "after": rec.get("after"),
        })

    return issues


def _basic_metrics(code: str) -> dict:
    lines = code.splitlines()
    code_lines = sum(
        1 for ln in lines
        if ln.strip() and not ln.strip().startswith("//") and not ln.strip().startswith("*")
    )
    methods = len(re.findall(
        r"(?:public|private|protected|static|\s)+[\w<>\[\]]+\s+(\w+)\s*\([^)]*\)\s*(?:throws\s+\w+\s*)?\{",
        code
    ))
    classes = len(re.findall(r"\bclass\s+\w+", code))
    return {"code_lines": code_lines, "functions": methods, "classes": classes}


def _build_summary(issues: list, rating: dict, compiler_not_found: bool) -> str:
    if compiler_not_found:
        return "javac not found — install a JDK and ensure javac is on your PATH to enable Java analysis."
    if not issues:
        return "No issues found. The Java code compiled cleanly."
    counts = rating["breakdown"]
    parts = []
    if counts["critical"]:
        parts.append(f"{counts['critical']} error{'s' if counts['critical'] != 1 else ''}")
    if counts["warning"]:
        parts.append(f"{counts['warning']} warning{'s' if counts['warning'] != 1 else ''}")
    if counts["info"]:
        parts.append(f"{counts['info']} note{'s' if counts['info'] != 1 else ''}")
    headline = ", ".join(parts) + " from javac."
    if counts["critical"] > 0:
        first = next((i for i in issues if i["severity"] == "critical"), None)
        if first and first["line"]:
            headline += f" Start with the error at line {first['line']}."
    return headline


class JavaAnalyzer(BaseAnalyzer):
    def analyze(self, code: str, **kwargs) -> dict:
        compiler_not_found = False
        issues = []
        has_syntax_error = False

        with tempfile.TemporaryDirectory() as tmpdir:
            src = os.path.join(tmpdir, "Main.java")
            with open(src, "w", encoding="utf-8") as fh:
                fh.write(code)

            from executor.local_sandbox import _find_tool
            javac_path = _find_tool("javac")

            try:
                proc = subprocess.run(
                    [javac_path, "-Xlint:all", src],
                    capture_output=True,
                    text=True,
                    timeout=20,
                    cwd=tmpdir,
                )
            except FileNotFoundError:
                compiler_not_found = True
                issues = [{
                    "source": "java",
                    "rule_id": "javac-not-found",
                    "severity": "info",
                    "category": "tooling",
                    "line": None, "column": None,
                    "message": "javac not found. Install a JDK to enable Java analysis.",
                    "recommendation": (
                        "Install a JDK (e.g. OpenJDK 17+) and ensure `javac` is on your PATH. "
                        "On Windows: winget install Microsoft.OpenJDK.17"
                    ),
                    "before": None, "after": None,
                }]
            except subprocess.TimeoutExpired:
                issues = [{
                    "source": "java",
                    "rule_id": "javac-timeout",
                    "severity": "warning",
                    "category": "tooling",
                    "line": None, "column": None,
                    "message": "javac timed out during analysis.",
                    "recommendation": "The file may be too large or complex for the analysis timeout.",
                    "before": None, "after": None,
                }]
            else:
                issues = _parse_javac_output(proc.stderr)
                has_syntax_error = any(
                    i["severity"] == "critical" for i in issues
                )

        issues.sort(key=lambda i: ({"critical": 0, "warning": 1, "info": 2}.get(i["severity"], 3), i["line"] or 0))

        rating = compute_rating(issues, has_syntax_error=has_syntax_error)
        metrics = _basic_metrics(code)
        summary = _build_summary(issues, rating, compiler_not_found)

        return {
            "rating": rating,
            "issues": issues,
            "summary": summary,
            "metrics": metrics,
            "has_syntax_error": has_syntax_error,
        }
