"""
C static analyzer.

Primary engine: gcc -Wall -Wextra -fsyntax-only
  - -fsyntax-only skips linking/binary output — analysis only.
  - -Wall -Wextra enables a comprehensive set of warnings.
  - stderr is parsed into our standard issue format.

Requires: GCC installed with `gcc` on PATH.
"""

import os
import re
import subprocess
import tempfile

from .base import BaseAnalyzer
from .rating import compute_rating

# gcc/g++ diagnostic format:
#   <file>:<line>:<col>: error: <message>
#   <file>:<line>:<col>: warning: <message> [-W<flag>]
_DIAG_RE = re.compile(
    r"[^\n:]+:(\d+):\d+:\s*(error|warning|note):\s*(.+?)(?:\s+\[-W[^\]]*\])?\s*$",
    re.MULTILINE,
)

_C_RECOMMENDATIONS = {
    "implicit declaration of function": {
        "explanation": (
            "You're calling a function that hasn't been declared yet. In C, "
            "functions must be declared (or defined) before they are called, "
            "or a prototype must appear at the top of the file."
        ),
        "before": "int main() { print_greeting(); }\nvoid print_greeting() { printf(\"hi\\n\"); }",
        "after": "void print_greeting();\nint main() { print_greeting(); }\nvoid print_greeting() { printf(\"hi\\n\"); }",
    },
    "unused variable": {
        "explanation": "This variable is declared but never read. Remove it or prefix with (void) to silence the warning intentionally.",
    },
    "unused parameter": {
        "explanation": "This function parameter is never used. Cast it to (void) in the body to document that it's intentionally ignored: `(void)param;`",
    },
    "control reaches end of non-void function": {
        "explanation": "Not all code paths in this function return a value. Add a return statement at the end.",
        "before": "int max(int a, int b) {\n    if (a > b) return a;\n    // falls off the end!",
        "after": "int max(int a, int b) {\n    if (a > b) return a;\n    return b;\n}",
    },
    "comparison between pointer and integer": {
        "explanation": "You're comparing a pointer to an integer, which is usually a bug. Make sure both sides of the comparison are the same type.",
    },
    "passing argument": {
        "explanation": "The argument type doesn't match the parameter type. Check the function signature and cast if necessary.",
    },
    "format specifies type": {
        "explanation": "The printf/scanf format specifier doesn't match the argument type. For example, use %zu for size_t, %d for int, %f for float.",
    },
    "may be used uninitialized": {
        "explanation": "This variable may be read before it's been given a value. Initialize it at the point of declaration to avoid undefined behavior.",
        "before": "int result;\n// ... conditional code that might not assign result ...\nreturn result;",
        "after": "int result = 0;  /* safe default */\n// ... conditional code ...\nreturn result;",
    },
    "integer overflow": {
        "explanation": "This arithmetic operation can overflow the integer type. Use a larger type (long, long long) or check bounds before the operation.",
    },
    "taking address of packed member": {
        "explanation": "Taking the address of a field in a __packed__ struct may cause unaligned access on some architectures. Copy it to a local variable first.",
    },
    "return type defaults to": {
        "explanation": "Old-style C allows omitting return types, defaulting to int. Always declare the return type explicitly.",
    },
}


def _match_recommendation(message: str) -> dict:
    msg_lower = message.lower()
    for key, rec in _C_RECOMMENDATIONS.items():
        if key.lower() in msg_lower:
            return rec
    return {}


def _parse_gcc_output(stderr: str) -> tuple[list, bool]:
    """Returns (issues, has_syntax_error)."""
    issues = []
    has_error = False
    seen = set()

    for match in _DIAG_RE.finditer(stderr):
        line_no = int(match.group(1))
        kind = match.group(2)
        message = match.group(3).strip()

        key = (line_no, message)
        if key in seen:
            continue
        seen.add(key)

        severity = "critical" if kind == "error" else ("warning" if kind == "warning" else "info")
        if kind == "error":
            has_error = True

        rec = _match_recommendation(message)
        issues.append({
            "source": "gcc",
            "rule_id": f"gcc-{kind}",
            "severity": severity,
            "category": _categorize(message),
            "line": line_no,
            "column": None,
            "message": message,
            "recommendation": rec.get("explanation", message),
            "before": rec.get("before"),
            "after": rec.get("after"),
        })

    return issues, has_error


def _categorize(message: str) -> str:
    msg = message.lower()
    if any(k in msg for k in ("overflow", "uninitialized", "null", "undefined")):
        return "bug"
    if any(k in msg for k in ("unused",)):
        return "style"
    if any(k in msg for k in ("format", "conversion", "comparison")):
        return "bug"
    return "warning"


def _basic_metrics(code: str) -> dict:
    lines = code.splitlines()
    code_lines = sum(
        1 for ln in lines
        if ln.strip() and not ln.strip().startswith("//") and not ln.strip().startswith("*")
        and not ln.strip().startswith("/*")
    )
    functions = len(re.findall(
        r"^\s*(?:[\w\*]+\s+)+(\w+)\s*\([^)]*\)\s*\{",
        code, re.MULTILINE
    ))
    return {"code_lines": code_lines, "functions": functions, "classes": 0}


def _build_summary(issues: list, rating: dict, compiler_not_found: bool) -> str:
    if compiler_not_found:
        return "gcc not found — install GCC and ensure it is on your PATH to enable C analysis."
    if not issues:
        return "No issues found. The C code passed gcc -Wall -Wextra without warnings."
    counts = rating["breakdown"]
    parts = []
    if counts["critical"]:
        parts.append(f"{counts['critical']} error{'s' if counts['critical'] != 1 else ''}")
    if counts["warning"]:
        parts.append(f"{counts['warning']} warning{'s' if counts['warning'] != 1 else ''}")
    if counts["info"]:
        parts.append(f"{counts['info']} note{'s' if counts['info'] != 1 else ''}")
    headline = ", ".join(parts) + " from gcc."
    if counts["critical"] > 0:
        first = next((i for i in issues if i["severity"] == "critical"), None)
        if first and first["line"]:
            headline += f" Start with the error at line {first['line']}."
    return headline


class CAnalyzer(BaseAnalyzer):
    COMPILER = "gcc"
    EXTRA_FLAGS: list = []   # subclass can override for g++

    def analyze(self, code: str, **kwargs) -> dict:
        compiler_not_found = False
        issues = []
        has_syntax_error = False

        with tempfile.TemporaryDirectory() as tmpdir:
            ext = "c" if self.COMPILER == "gcc" else "cpp"
            src = os.path.join(tmpdir, f"submission.{ext}")
            with open(src, "w", encoding="utf-8") as fh:
                fh.write(code)

            from executor.local_sandbox import _find_tool
            compiler_path = _find_tool(self.COMPILER)
            cmd = [
                compiler_path, "-Wall", "-Wextra", "-fsyntax-only",
                *self.EXTRA_FLAGS, src,
            ]
            try:
                proc = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=20,
                    cwd=tmpdir,
                )
            except FileNotFoundError:
                compiler_not_found = True
                issues = [{
                    "source": self.COMPILER,
                    "rule_id": f"{self.COMPILER}-not-found",
                    "severity": "info",
                    "category": "tooling",
                    "line": None, "column": None,
                    "message": f"{self.COMPILER} not found. Install GCC/G++ to enable analysis.",
                    "recommendation": (
                        f"Install GCC: on Windows use `winget install GnuWin32.GCC` or "
                        "MinGW-w64; on Linux: `sudo apt install build-essential`."
                    ),
                    "before": None, "after": None,
                }]
            except subprocess.TimeoutExpired:
                issues = [{
                    "source": self.COMPILER,
                    "rule_id": f"{self.COMPILER}-timeout",
                    "severity": "warning",
                    "category": "tooling",
                    "line": None, "column": None,
                    "message": f"{self.COMPILER} analysis timed out.",
                    "recommendation": "The file may be too large for the analysis timeout.",
                    "before": None, "after": None,
                }]
            else:
                issues, has_syntax_error = _parse_gcc_output(proc.stderr)

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
