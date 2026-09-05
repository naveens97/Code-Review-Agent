from analyzer.rating import compute_rating


def _issue(severity):
    return {"severity": severity}


def test_no_issues_scores_100():
    rating = compute_rating([])
    assert rating["score"] == 100
    assert rating["label"] == "Excellent"


def test_syntax_error_caps_score_regardless_of_issue_count():
    rating = compute_rating([], has_syntax_error=True)
    assert rating["score"] <= 15
    assert rating["label"] == "Fails to Run"


def test_syntax_error_caps_even_with_few_other_issues():
    # A single low-severity issue would barely dent the score on its own,
    # but a syntax error must still force the score down regardless.
    rating = compute_rating([_issue("info")], has_syntax_error=True)
    assert rating["score"] <= 15


def test_severity_ordering_reduces_score_monotonically():
    critical = compute_rating([_issue("critical")])
    warning = compute_rating([_issue("warning")])
    info = compute_rating([_issue("info")])
    assert critical["score"] < warning["score"] < info["score"] < 100


def test_score_never_goes_negative():
    many_critical = [_issue("critical") for _ in range(50)]
    rating = compute_rating(many_critical)
    assert rating["score"] == 0
    assert rating["label"] == "Poor"


def test_severity_cap_limits_runaway_penalty_from_one_tier():
    # 3 infos should cost less than 30 infos thanks to the per-tier cap,
    # not scale linearly forever.
    few = compute_rating([_issue("info") for _ in range(3)])
    many = compute_rating([_issue("info") for _ in range(30)])
    assert few["score"] > many["score"]
    assert many["score"] >= 100 - 15  # info tier capped at 15 points total


def test_breakdown_counts_match_input():
    issues = [_issue("critical"), _issue("warning"), _issue("warning"), _issue("info")]
    rating = compute_rating(issues)
    assert rating["breakdown"] == {"critical": 1, "warning": 2, "info": 1}


def test_score_out_of_10_is_consistent_with_score():
    rating = compute_rating([_issue("warning")])
    assert rating["score_out_of_10"] == round(rating["score"] / 10, 1)
