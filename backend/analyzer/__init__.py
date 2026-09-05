"""
Analyzer package: static analysis engine for code review, dispatched by
language.

get_analyzer(language) is the seam a new language plugs into -- add a
class implementing BaseAnalyzer, register it in ANALYZER_REGISTRY below,
and nothing in app.py or the frontend has to change to route requests to
it correctly.

Supported languages
  python      -- PythonAnalyzer  (Pylint + Bandit + custom AST checks)
  javascript  -- JavaScriptAnalyzer (ESLint or Node --check fallback)
  java        -- JavaAnalyzer    (javac -Xlint:all)
  c           -- CAnalyzer       (gcc -Wall -Wextra -fsyntax-only)
  cpp         -- CppAnalyzer     (g++ -Wall -Wextra -std=c++17 -fsyntax-only)

analyze_code() is a thin convenience wrapper kept for callers (app.py,
the test suite) that just want "run the right analyzer and give me the
result" without touching the registry directly.
"""
from .base import BaseAnalyzer
from .c_analyzer import CAnalyzer
from .cpp_analyzer import CppAnalyzer
from .java_analyzer import JavaAnalyzer
from .javascript_analyzer import JavaScriptAnalyzer
from .python_analyzer import PythonAnalyzer
from .rating import compute_rating

ANALYZER_REGISTRY = {
    "python": PythonAnalyzer,
    "javascript": JavaScriptAnalyzer,
    "java": JavaAnalyzer,
    "c": CAnalyzer,
    "cpp": CppAnalyzer,
}


def get_analyzer(language: str) -> BaseAnalyzer:
    analyzer_cls = ANALYZER_REGISTRY.get(language)
    if analyzer_cls is None:
        supported = ", ".join(sorted(ANALYZER_REGISTRY))
        raise ValueError(f"No analyzer registered for '{language}'. Supported: {supported}.")
    return analyzer_cls()


def analyze_code(code: str, language: str = "python", **kwargs) -> dict:
    """kwargs are forwarded as-is to whichever analyzer `language` resolves
    to (e.g. max_complexity, which only PythonAnalyzer understands right
    now). Deliberately not hardcoded to a Python-specific parameter name
    here, so this function doesn't quietly assume every future analyzer
    accepts the same tuning knobs Pylint does."""
    
    # Extract AI key before forwarding kwargs to language analyzers
    dynamic_key = kwargs.pop("ai_key", None)
    
    analyzer = get_analyzer(language)
    result = analyzer.analyze(code, **kwargs)

    from config import Config
    from .gemini_analyzer import GeminiAnalyzer
    from .openai_analyzer import OpenAIAnalyzer
    from .groq_analyzer import GroqAnalyzer
    
    openai_key = getattr(Config, "OPENAI_API_KEY", "")
    gemini_key = getattr(Config, "GEMINI_API_KEY", "")
    groq_key = getattr(Config, "GROQ_API_KEY", "")

    # If the user passed a dynamic key, determine its type based on the prefix
    if dynamic_key:
        if dynamic_key.startswith("sk-"):
            openai_key = dynamic_key
            gemini_key = ""
            groq_key = ""
        elif dynamic_key.startswith("gsk_"):
            groq_key = dynamic_key
            openai_key = ""
            gemini_key = ""
        else:
            gemini_key = dynamic_key
            openai_key = ""
            groq_key = ""
    
    ai_issues = []
    ai_summary = ""

    if groq_key:
        try:
            groq = GroqAnalyzer(groq_key)
            ai_result = groq.analyze(code, language=language)
            ai_issues = ai_result.get("issues", [])
            ai_summary = ai_result.get("summary", "")
        except Exception as e:
            ai_summary = f"Groq Error: {e}"
    elif openai_key:
        try:
            openai_analyzer = OpenAIAnalyzer(openai_key)
            ai_result = openai_analyzer.analyze(code, language=language)
            ai_issues = ai_result.get("issues", [])
            ai_summary = ai_result.get("summary", "")
        except Exception as e:
            ai_summary = f"OpenAI Error: {e}"
    elif gemini_key:
        try:
            gemini = GeminiAnalyzer(gemini_key)
            ai_result = gemini.analyze(code, language=language)
            ai_issues = ai_result.get("issues", [])
            ai_summary = ai_result.get("summary", "")
        except Exception as e:
            ai_summary = f"Gemini Error: {e}"

    if ai_issues:
        # Merge tool and AI issues
        all_issues = result.get("issues", []) + ai_issues
        # Sort: critical first, then warning, then info, then by line number
        all_issues.sort(key=lambda i: ({"critical": 0, "warning": 1, "info": 2}.get(i["severity"], 3), i["line"] or 0))
        result["issues"] = all_issues

        # Merge summaries
        tool_summary = result.get("summary", "")
        if tool_summary and ai_summary:
            result["summary"] = f"{ai_summary} (Traditional diagnostics: {tool_summary})"
        elif ai_summary:
            result["summary"] = ai_summary

        # Recompute rating with merged issues
        has_syntax_error = result.get("has_syntax_error", False)
        result["rating"] = compute_rating(all_issues, has_syntax_error=has_syntax_error)

    return result

def chat_code(code: str, language: str = "python", messages: list = None, ai_key: str = "") -> str:
    if not messages:
        messages = []

    from config import Config
    from .gemini_analyzer import GeminiAnalyzer
    from .openai_analyzer import OpenAIAnalyzer
    from .groq_analyzer import GroqAnalyzer
    
    openai_key = getattr(Config, "OPENAI_API_KEY", "")
    gemini_key = getattr(Config, "GEMINI_API_KEY", "")
    groq_key = getattr(Config, "GROQ_API_KEY", "")

    if ai_key:
        if ai_key.startswith("sk-"):
            openai_key = ai_key
            gemini_key = ""
            groq_key = ""
        elif ai_key.startswith("gsk_"):
            groq_key = ai_key
            openai_key = ""
            gemini_key = ""
        else:
            gemini_key = ai_key
            openai_key = ""
            groq_key = ""
    
    if groq_key:
        groq = GroqAnalyzer(groq_key)
        return groq.chat(code, language, messages)
    elif openai_key:
        openai_analyzer = OpenAIAnalyzer(openai_key)
        return openai_analyzer.chat(code, language, messages)
    elif gemini_key:
        gemini = GeminiAnalyzer(gemini_key)
        return gemini.chat(code, language, messages)
    else:
        return "Error: No AI API key configured for chat."

def autocomplete_code(prefix: str, suffix: str, language: str = "python", ai_key: str = "") -> str:
    from config import Config
    from .gemini_analyzer import GeminiAnalyzer
    from .openai_analyzer import OpenAIAnalyzer
    from .groq_analyzer import GroqAnalyzer
    
    openai_key = getattr(Config, "OPENAI_API_KEY", "")
    gemini_key = getattr(Config, "GEMINI_API_KEY", "")
    groq_key = getattr(Config, "GROQ_API_KEY", "")

    if ai_key:
        if ai_key.startswith("sk-"):
            openai_key = ai_key
            gemini_key = ""
            groq_key = ""
        elif ai_key.startswith("gsk_"):
            groq_key = ai_key
            openai_key = ""
            gemini_key = ""
        else:
            gemini_key = ai_key
            openai_key = ""
            groq_key = ""
    
    if groq_key:
        groq = GroqAnalyzer(groq_key)
        return groq.autocomplete(prefix, suffix, language)
    elif openai_key:
        openai_analyzer = OpenAIAnalyzer(openai_key)
        return openai_analyzer.autocomplete(prefix, suffix, language)
    elif gemini_key:
        gemini = GeminiAnalyzer(gemini_key)
        return gemini.autocomplete(prefix, suffix, language)
    else:
        return ""

__all__ = [
    "BaseAnalyzer", "PythonAnalyzer", "JavaScriptAnalyzer",
    "JavaAnalyzer", "CAnalyzer", "CppAnalyzer",
    "get_analyzer", "analyze_code", "chat_code", "autocomplete_code", "compute_rating", "ANALYZER_REGISTRY",
]
