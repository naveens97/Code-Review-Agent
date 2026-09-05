"""
Executor package: pluggable code-execution backends behind one interface.

get_executor() is the only thing the rest of the app needs to import --
it reads config and returns whichever provider is configured, so
app.py never has to know the difference between "run it locally" and
"send it to Judge0".
"""
from .base import BaseExecutor
from .local_sandbox import LocalSandboxExecutor


def get_executor(config) -> BaseExecutor:
    if config.EXECUTION_PROVIDER == "judge0":
        from .judge0_provider import Judge0Executor
        return Judge0Executor(
            base_url=config.JUDGE0_URL,
            api_key=config.JUDGE0_API_KEY,
            timeout_seconds=config.EXECUTION_TIMEOUT_SECONDS,
        )
    return LocalSandboxExecutor(
        timeout_seconds=config.EXECUTION_TIMEOUT_SECONDS,
        memory_mb=config.EXECUTION_MEMORY_MB,
        max_output_chars=config.EXECUTION_MAX_OUTPUT_CHARS,
    )


__all__ = ["BaseExecutor", "LocalSandboxExecutor", "get_executor"]
