from analyzer import analyze_code

CLEAN_CODE = '''\
def add(a: int, b: int) -> int:
    """Return the sum of two integers."""
    return a + b


if __name__ == "__main__":
    print(add(2, 3))
'''

INSECURE_CODE = '''\
import os

def run(cmd):
    os.system("echo " + cmd)

def get_data(raw):
    return eval(raw)
'''

SYNTAX_ERROR_CODE = "def broken(\n    print('no closing paren'\n"

MUTABLE_DEFAULT_CODE = '''\
def add_item(item, bucket=[]):
    bucket.append(item)
    return bucket
'''


def test_clean_code_scores_high_with_no_issues():
    result = analyze_code(CLEAN_CODE)
    assert result["rating"]["score"] == 100
    assert result["issues"] == []
    assert result["has_syntax_error"] is False


def test_insecure_code_flags_security_issues_as_critical_or_warning():
    result = analyze_code(INSECURE_CODE)
    security_issues = [i for i in result["issues"] if i["category"] == "security"]
    assert len(security_issues) >= 2
    assert all(i["severity"] in ("critical", "warning") for i in security_issues)
    # both bandit rule IDs should be present
    rule_ids = {i["rule_id"] for i in security_issues}
    assert "B605" in rule_ids or "B602" in rule_ids
    assert "B307" in rule_ids


def test_syntax_error_produces_exactly_one_syntax_issue_no_duplicates():
    result = analyze_code(SYNTAX_ERROR_CODE)
    assert result["has_syntax_error"] is True
    syntax_issues = [i for i in result["issues"] if i["rule_id"] == "syntax-error"]
    assert len(syntax_issues) == 1
    assert result["rating"]["score"] <= 15


def test_mutable_default_argument_detected():
    result = analyze_code(MUTABLE_DEFAULT_CODE)
    rule_ids = {i["rule_id"] for i in result["issues"]}
    assert "dangerous-default-value" in rule_ids


def test_every_issue_has_a_recommendation():
    result = analyze_code(INSECURE_CODE)
    for issue in result["issues"]:
        assert issue["recommendation"], f"{issue['rule_id']} has no recommendation text"


def test_issues_sorted_critical_first():
    result = analyze_code(INSECURE_CODE)
    severities = [i["severity"] for i in result["issues"]]
    severity_rank = {"critical": 0, "warning": 1, "info": 2}
    ranks = [severity_rank[s] for s in severities]
    assert ranks == sorted(ranks)


def test_metrics_are_computed():
    result = analyze_code(CLEAN_CODE)
    assert result["metrics"]["functions"] == 1
    assert result["metrics"]["code_lines"] > 0
