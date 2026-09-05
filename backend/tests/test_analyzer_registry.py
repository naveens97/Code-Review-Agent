import pytest

from analyzer import ANALYZER_REGISTRY, BaseAnalyzer, PythonAnalyzer, analyze_code, get_analyzer


def test_python_is_registered():
    assert "python" in ANALYZER_REGISTRY
    assert ANALYZER_REGISTRY["python"] is PythonAnalyzer


def test_get_analyzer_returns_a_base_analyzer_instance():
    analyzer = get_analyzer("python")
    assert isinstance(analyzer, BaseAnalyzer)
    assert isinstance(analyzer, PythonAnalyzer)


def test_get_analyzer_raises_clean_error_for_unknown_language():
    with pytest.raises(ValueError, match="java"):
        get_analyzer("java")


def test_analyze_code_defaults_to_python():
    result = analyze_code('print("hi")\n')
    assert result["rating"]["score"] == 100


def test_analyze_code_explicit_python_language_matches_default():
    default = analyze_code('x = 1\ny = eval("1")')
    explicit = analyze_code('x = 1\ny = eval("1")', language="python")
    assert default["rating"]["score"] == explicit["rating"]["score"]
    assert len(default["issues"]) == len(explicit["issues"])


def test_analyze_code_unsupported_language_raises_instead_of_silently_using_python():
    with pytest.raises(ValueError):
        analyze_code("console.log(1)", language="javascript")


def test_analyze_code_forwards_kwargs_to_the_resolved_analyzer():
    # max_complexity is Python/pylint-specific and should reach PythonAnalyzer
    # unchanged -- a very low threshold should surface a too-complex finding
    # that the default threshold wouldn't.
    nested_code = """
def f(a, b, c):
    if a:
        if b:
            if c:
                return 1
    return 0
"""
    lenient = analyze_code(nested_code, max_complexity=50)
    strict = analyze_code(nested_code, max_complexity=1)
    lenient_ids = {i["rule_id"] for i in lenient["issues"]}
    strict_ids = {i["rule_id"] for i in strict["issues"]}
    assert "too-complex" not in lenient_ids
    assert "too-complex" in strict_ids
