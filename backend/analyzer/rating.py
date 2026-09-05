"""
Turns a list of issues into a single, explainable quality score.

Design goals:
  - Transparent: every point lost can be traced back to a rule.
  - Bounded: one severity category can never single-handedly wipe out the
    score just because a big file triggered the same minor rule 40 times.
  - Honest about broken code: a file that doesn't even parse cannot score
    "Good" no matter how clean the rest of the analysis looks.

This is intentionally a plain, deterministic formula (not a black box) so
it can be tuned by changing the constants below.
"""

# Points lost per issue, before capping.
SEVERITY_WEIGHTS = {
    "critical": 12,
    "warning": 5,
    "info": 1.5,
}

# Maximum points a severity tier can cost in total, no matter how many
# issues of that tier are found. This exists to stop a single noisy LOW
# value rule (e.g. a style nit repeated 40 times) from dominating the
# score. Critical issues are deliberately NOT capped this way: if code
# has a genuinely large number of critical bugs/vulnerabilities, nothing
# should stop the score from reflecting that.
SEVERITY_CAPS = {
    "critical": 1000,  # effectively unbounded; final score still clamps to 0
    "warning": 40,
    "info": 15,
}

LABELS = (
    (90, "Excellent"),
    (75, "Good"),
    (60, "Fair"),
    (40, "Needs Improvement"),
    (0, "Poor"),
)

# A file that fails to parse is capped here regardless of what else is true.
SYNTAX_ERROR_SCORE_CEILING = 15


def score_to_label(score: int, has_syntax_error: bool = False) -> str:
    if has_syntax_error:
        return "Fails to Run"
    for threshold, label in LABELS:
        if score >= threshold:
            return label
    return "Poor"


def compute_rating(issues: list, has_syntax_error: bool = False) -> dict:
    """
    issues: list of dicts each containing at least a "severity" key
            ("critical" | "warning" | "info").
    """
    counts = {"critical": 0, "warning": 0, "info": 0}
    for issue in issues:
        sev = issue.get("severity", "info")
        if sev not in counts:
            sev = "info"
        counts[sev] += 1

    breakdown_penalty = {}
    total_penalty = 0.0
    for sev in ("critical", "warning", "info"):
        raw = counts[sev] * SEVERITY_WEIGHTS[sev]
        capped = min(raw, SEVERITY_CAPS[sev])
        breakdown_penalty[sev] = round(capped, 1)
        total_penalty += capped

    score = 100 - total_penalty

    if has_syntax_error:
        score = min(score, SYNTAX_ERROR_SCORE_CEILING)

    score = max(0, min(100, round(score)))

    return {
        "score": score,
        "score_out_of_10": round(score / 10, 1),
        "label": score_to_label(score, has_syntax_error),
        "breakdown": counts,
        "penalty_breakdown": breakdown_penalty,
    }
