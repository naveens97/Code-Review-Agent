"""
Optional Judge0 execution provider.

This is a reference integration for anyone who wants code to run inside
Judge0's disposable, network-isolated containers instead of this
project's local subprocess sandbox (see local_sandbox.py) -- meaningfully
stronger isolation for a real public deployment.

IMPORTANT: this module was written against the documented Judge0 CE API
shape but could NOT be executed or tested in the environment this project
was built in (no outbound network access to Judge0 from that sandbox).
Treat it as a well-formed starting point, not a verified integration --
confirm the endpoint paths, field names, and language IDs against
https://ce.judge0.com/ (or your self-hosted instance's /languages route)
before relying on it, and test it against a real Judge0 key first.

To use it: set EXECUTION_PROVIDER=judge0 and JUDGE0_API_KEY in the
environment (see config.py / README).
"""
import time

from .base import BaseExecutor

# Judge0 CE language IDs. Verify current IDs via GET {JUDGE0_URL}/languages
# -- these are occasionally renumbered between Judge0 versions.
LANGUAGE_IDS = {
    "python": 71,  # Python 3.8.1
}

STATUS_POLL_INTERVAL_SECONDS = 1
STATUS_POLL_MAX_ATTEMPTS = 15
# Judge0 status IDs 1 and 2 mean "In Queue" / "Processing" respectively;
# anything >= 3 is a terminal state (Accepted, Wrong Answer, TLE, error, etc).
TERMINAL_STATUS_THRESHOLD = 3


class Judge0Executor(BaseExecutor):
    def __init__(self, base_url: str, api_key: str, timeout_seconds: int = 10):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    def execute(self, code: str, language: str = "python", stdin: str = "") -> dict:
        if not self.api_key:
            return {
                "success": False, "stdout": "", "exit_code": -1, "timed_out": False,
                "execution_time_ms": 0,
                "stderr": "JUDGE0_API_KEY is not configured. Set it in the environment, "
                          "or set EXECUTION_PROVIDER=local to use the built-in sandbox instead.",
            }
        if language not in LANGUAGE_IDS:
            return {
                "success": False, "stdout": "", "exit_code": -1, "timed_out": False,
                "execution_time_ms": 0,
                "stderr": f"'{language}' has no configured Judge0 language ID yet.",
            }

        try:
            import requests  # imported lazily so this dependency is optional
        except ImportError:
            return {
                "success": False, "stdout": "", "exit_code": -1, "timed_out": False,
                "execution_time_ms": 0,
                "stderr": "The 'requests' package is required for the Judge0 provider "
                          "(pip install requests).",
            }

        headers = {
            "content-type": "application/json",
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": self.base_url.replace("https://", "").replace("http://", ""),
        }
        payload = {
            "source_code": code,
            "language_id": LANGUAGE_IDS[language],
            "stdin": stdin,
            "cpu_time_limit": self.timeout_seconds,
        }

        start = time.monotonic()
        try:
            submit_resp = requests.post(
                f"{self.base_url}/submissions?base64_encoded=false&wait=false",
                json=payload, headers=headers, timeout=15,
            )
            submit_resp.raise_for_status()
            token = submit_resp.json()["token"]

            for _ in range(STATUS_POLL_MAX_ATTEMPTS):
                time.sleep(STATUS_POLL_INTERVAL_SECONDS)
                result_resp = requests.get(
                    f"{self.base_url}/submissions/{token}?base64_encoded=false",
                    headers=headers, timeout=15,
                )
                result_resp.raise_for_status()
                data = result_resp.json()
                if data.get("status", {}).get("id", 0) >= TERMINAL_STATUS_THRESHOLD:
                    elapsed_ms = int((time.monotonic() - start) * 1000)
                    status_desc = data.get("status", {}).get("description", "")
                    return {
                        "success": data.get("status", {}).get("id") == TERMINAL_STATUS_THRESHOLD,
                        "stdout": data.get("stdout") or "",
                        "stderr": data.get("stderr") or data.get("compile_output") or status_desc,
                        "exit_code": 0 if data.get("status", {}).get("id") == TERMINAL_STATUS_THRESHOLD else 1,
                        "execution_time_ms": elapsed_ms,
                        "timed_out": "Time Limit" in status_desc,
                    }

            return {
                "success": False, "stdout": "", "exit_code": -1, "timed_out": True,
                "execution_time_ms": int((time.monotonic() - start) * 1000),
                "stderr": "Timed out waiting for Judge0 to return a result.",
            }
        except requests.RequestException as e:
            return {
                "success": False, "stdout": "", "exit_code": -1, "timed_out": False,
                "execution_time_ms": int((time.monotonic() - start) * 1000),
                "stderr": f"Judge0 request failed: {e}",
            }
