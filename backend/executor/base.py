"""
Common interface for code execution providers, so the API layer doesn't
care whether code actually runs in a local subprocess or a hosted judge
service. Add a new language or a new provider by implementing this and
registering it in __init__.py -- nothing else has to change.
"""
from abc import ABC, abstractmethod


class BaseExecutor(ABC):
    @abstractmethod
    def execute(self, code: str, language: str = "python", stdin: str = "") -> dict:
        """
        Must return a dict with exactly these keys:
          success (bool): True if the program ran and exited with code 0
          stdout (str)
          stderr (str)
          exit_code (int)
          execution_time_ms (int)
          timed_out (bool)
        """
        raise NotImplementedError
