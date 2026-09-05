"""
Common interface for language-specific code analyzers, mirroring the
BaseExecutor pattern in executor/base.py. Add a new language by
implementing this and registering it in __init__.py -- app.py and every
frontend component stay untouched.
"""
from abc import ABC, abstractmethod


class BaseAnalyzer(ABC):
    @abstractmethod
    def analyze(self, code: str, **kwargs) -> dict:
        """
        Must return a dict with exactly these keys:
          rating (dict): {score, score_out_of_10, label, breakdown, penalty_breakdown}
                          -- see analyzer/rating.py, which is language-agnostic
                          and shared by every analyzer.
          issues (list[dict]): each with at least
                          {source, rule_id, severity, category, line, column,
                           message, recommendation, before, after}
          summary (str): one or two plain-English sentences.
          metrics (dict): whatever structural stats make sense for the
                          language (line/function counts, etc).
          has_syntax_error (bool)

        kwargs are analyzer-specific tuning knobs (e.g. PythonAnalyzer
        accepts max_complexity) -- callers that don't know which analyzer
        they're talking to should stick to code-only calls and let each
        analyzer fall back to its own defaults.
        """
        raise NotImplementedError
