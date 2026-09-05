"""
Small, targeted checks written directly against the `ast` module for a
handful of things pylint/bandit don't cover well -- mainly performance
heuristics. Kept deliberately short: each check here is high-confidence
and low-false-positive rather than exhaustive, since a static heuristic
that's wrong most of the time erodes trust in the whole report faster
than not checking for it at all.
"""
import ast
import re

TODO_PATTERN = re.compile(r"#\s*(TODO|FIXME|XXX)\b[:\s]*(.*)", re.IGNORECASE)


def _issue(rule_id, severity, category, line, message, recommendation):
    return {
        "source": "custom",
        "rule_id": rule_id,
        "severity": severity,
        "category": category,
        "line": line,
        "column": None,
        "message": message,
        "recommendation": recommendation,
        "before": None,
        "after": None,
    }


class _LoopVisitor(ast.NodeVisitor):
    """Tracks loop nesting depth and flags string += inside a loop body."""

    def __init__(self):
        self.depth = 0
        self.max_depth_seen = 0
        self.max_depth_line = None
        self.string_concat_lines = set()

    def _enter_loop(self, node):
        self.depth += 1
        if self.depth > self.max_depth_seen:
            self.max_depth_seen = self.depth
            self.max_depth_line = node.lineno
        self.generic_visit(node)
        self.depth -= 1

    def visit_For(self, node):
        self._enter_loop(node)

    def visit_While(self, node):
        self._enter_loop(node)

    def visit_AugAssign(self, node):
        if self.depth > 0 and isinstance(node.op, ast.Add) and isinstance(node.target, ast.Name):
            self.string_concat_lines.add(node.lineno)
        self.generic_visit(node)


def _check_loop_patterns(tree):
    issues = []
    visitor = _LoopVisitor()
    visitor.visit(tree)

    if visitor.max_depth_seen >= 3:
        issues.append(_issue(
            "deep-nested-loops", "info", "performance", visitor.max_depth_line,
            f"Loops are nested {visitor.max_depth_seen} levels deep here, which often means "
            "O(n^3) or worse time complexity.",
            "Check whether the algorithm can be restructured -- e.g. precomputing a lookup "
            "set/dict to replace an inner loop, or an early exit once a match is found.",
        ))

    for line in sorted(visitor.string_concat_lines)[:3]:  # cap noise on repeated pattern
        issues.append(_issue(
            "string-concat-in-loop", "info", "performance", line,
            "Building up a value with += inside a loop is a common way strings get "
            "concatenated one character/piece at a time, which is O(n^2) for strings "
            "since each += copies the whole string so far.",
            "If this is building a string, collect the pieces in a list and join once "
            "at the end: ''.join(pieces). If it's a number/list, this pattern is fine.",
        ))

    return issues


def _check_todo_comments(source: str):
    issues = []
    for i, line in enumerate(source.splitlines(), start=1):
        match = TODO_PATTERN.search(line)
        if match:
            tag = match.group(1).upper()
            issues.append(_issue(
                "todo-comment", "info", "maintainability", i,
                f"{tag} comment left in code: {match.group(2).strip()[:80] or '(no detail)'}",
                "Resolve it before this is considered final, or file it as a tracked issue "
                "instead of leaving it in the source.",
            ))
    return issues[:10]  # cap noise for files with many TODOs


def _check_main_guard(tree, source: str):
    """Heuristic: if the file defines 2+ functions AND has executable
    top-level statements (calls, not just defs/imports/assignments) with no
    `if __name__ == "__main__":` guard, suggest adding one. Only fires when
    fairly confident, to avoid nagging on legitimately simple scripts."""
    if 'if __name__' in source:
        return []

    function_defs = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    if len(function_defs) < 2:
        return []

    has_top_level_call = any(
        isinstance(n, ast.Expr) and isinstance(n.value, ast.Call)
        for n in tree.body
    )
    if not has_top_level_call:
        return []

    first_call_line = next(
        (n.lineno for n in tree.body if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call)),
        None,
    )
    return [_issue(
        "missing-main-guard", "info", "best-practice", first_call_line,
        "This file defines multiple functions but runs top-level code unconditionally, "
        "which means importing this module (e.g. to reuse a function, or in tests) will "
        "also execute that code.",
        'Wrap the entry-point call in `if __name__ == "__main__":` so the file is safe to import.',
    )]


def run_custom_checks(code: str) -> list:
    """Returns a list of normalized issue dicts. Assumes `code` already
    parses -- callers should run this only when ast.parse succeeded."""
    issues = []
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return issues

    issues += _check_loop_patterns(tree)
    issues += _check_todo_comments(code)
    issues += _check_main_guard(tree, code)
    return issues


def basic_metrics(code: str) -> dict:
    """Lightweight structural stats used in the summary, independent of
    whether the code parses cleanly."""
    lines = code.splitlines()
    non_blank = [ln for ln in lines if ln.strip()]
    comment_lines = [ln for ln in non_blank if ln.strip().startswith("#")]
    metrics = {
        "total_lines": len(lines),
        "code_lines": len(non_blank) - len(comment_lines),
        "comment_lines": len(comment_lines),
        "functions": 0,
        "classes": 0,
    }
    try:
        tree = ast.parse(code)
        metrics["functions"] = sum(
            isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) for n in ast.walk(tree)
        )
        metrics["classes"] = sum(isinstance(n, ast.ClassDef) for n in ast.walk(tree))
    except SyntaxError:
        pass
    return metrics
