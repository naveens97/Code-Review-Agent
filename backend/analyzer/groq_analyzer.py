"""
Groq static analyzer.

Uses the Groq API (OpenAI-compatible) to analyze code and generate structured
code quality suggestions. Groq provides ultra-fast inference.
"""

import json
import logging
import requests

logger = logging.getLogger(__name__)

_RESPONSE_SCHEMA_HINT = {
    "issues": [
        {
            "rule_id": "string",
            "severity": "critical|warning|info",
            "category": "bug|security|style|complexity|performance|maintainability|best-practice",
            "line": 1,
            "message": "string (1-3 sentences max)",
            "recommendation": "string (1-3 sentences max)",
            "before": "string or null",
            "after": "string or null"
        }
    ],
    "summary": "string"
}


class GroqAnalyzer:
    """Uses Groq API to perform static code analysis reviews."""

    def __init__(self, api_key: str):
        self.api_key = api_key

    def analyze(self, code: str, language: str = "python") -> dict:
        """Call Groq to analyze the code and return structured issues and a summary."""
        if not self.api_key:
            return {"issues": [], "summary": "Groq API key is not configured."}

        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        prompt = (
            f"You are a strict, senior code reviewer. Perform a static review of the following {language} code:\n\n"
            f"```\n{code}\n```\n\n"
            f"Identify bugs, security vulnerabilities, performance bottlenecks, style issues, and maintainability concerns. "
            f"CRITICAL: Keep your `message` and `recommendation` fields EXTREMELY CONCISE (1-3 sentences max). Do not ramble. "
            f"If the code uses a brute force approach, flag it and provide the optimal algorithmic solution briefly. "
            f"Provide the before/after code blocks demonstrating the fix. "
            f"Return ONLY a strictly valid JSON object (no markdown, no backticks). The JSON object MUST conform EXACTLY to this structure:\n"
            f"{json.dumps(_RESPONSE_SCHEMA_HINT)}"
        )

        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": "You are a helpful code review assistant. Return ONLY valid JSON."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 2048
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            if response.status_code != 200:
                error_msg = f"HTTP {response.status_code}"
                try:
                    err_json = response.json()
                    if "error" in err_json and "message" in err_json["error"]:
                        error_msg = err_json["error"]["message"]
                except Exception:
                    error_msg = response.text or error_msg
                raise RuntimeError(error_msg)

            result_data = response.json()
            content = result_data.get("choices", [])[0].get("message", {}).get("content", "{}")

            # Strip markdown wrapping if present
            if content.startswith("```"):
                content = "\n".join(content.split("\n")[1:])
            if content.endswith("```"):
                content = "\n".join(content.split("\n")[:-1])

            parsed_review = json.loads(content)

            issues = []
            for item in parsed_review.get("issues", []):
                line_no = item.get("line")
                if line_no is not None:
                    try:
                        line_no = int(line_no)
                    except (ValueError, TypeError):
                        line_no = 1
                else:
                    line_no = 1

                issues.append({
                    "source": "groq",
                    "rule_id": item.get("rule_id", "groq-suggestion"),
                    "severity": item.get("severity", "warning"),
                    "category": item.get("category", "best-practice"),
                    "line": line_no,
                    "column": None,
                    "message": item.get("message", ""),
                    "recommendation": item.get("recommendation", ""),
                    "before": item.get("before"),
                    "after": item.get("after")
                })

            if not issues:
                issues.append({
                    "source": "groq",
                    "rule_id": "groq-optimal",
                    "severity": "info",
                    "category": "best-practice",
                    "line": 1,
                    "column": None,
                    "message": "Good solution — the code is already in an optimal state.",
                    "recommendation": "No changes needed.",
                    "before": None,
                    "after": None
                })

            return {
                "issues": issues,
                "summary": parsed_review.get("summary", "Review completed successfully by Groq.")
            }

        except Exception as e:
            logger.exception("Failed to run Groq analysis.")
            return {
                "issues": [{
                    "source": "groq",
                    "rule_id": "groq-error",
                    "severity": "warning",
                    "category": "tooling",
                    "line": 1,
                    "column": None,
                    "message": f"Failed to get AI suggestions: {str(e)}",
                    "recommendation": "Check your network connection and verify your GROQ_API_KEY is correct.",
                    "before": None,
                    "after": None
                }],
                "summary": f"Groq review analysis failed: {str(e)}"
            }

    def chat(self, code: str, language: str, messages: list) -> str:
        """Process a conversational chat turn using Groq."""
        if not self.api_key:
            return "Groq API key is not configured."

        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        groq_msgs = [
            {
                "role": "system",
                "content": (
                    f"You are a helpful coding assistant. The user is working on the following {language} code:\n"
                    f"```\n{code}\n```\n"
                    f"Answer their questions concisely."
                )
            }
        ]

        for msg in messages:
            groq_msgs.append({
                "role": "user" if msg["role"] == "user" else "assistant",
                "content": msg["content"]
            })

        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": groq_msgs,
            "max_tokens": 512,
            "temperature": 0.5
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=15)
            if response.status_code != 200:
                return f"Error from Groq API: {response.text}"

            result_data = response.json()
            return result_data.get("choices", [])[0].get("message", {}).get("content", "No response.")

        except Exception as e:
            logger.exception("Failed to run Groq chat.")
            return f"An error occurred while contacting the AI: {e}"

    def autocomplete(self, prefix: str, suffix: str, language: str) -> str:
        """Provide inline code completions using Groq."""
        if not self.api_key:
            return ""

        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        prompt = (
            f"You are a strict, ultra-fast code completion engine for {language}. "
            f"Given the code BEFORE the cursor:\n<PREFIX>\n{prefix}\n</PREFIX>\n"
            f"And the code AFTER the cursor:\n<SUFFIX>\n{suffix}\n</SUFFIX>\n\n"
            f"Complete the code exactly where the cursor is. Return ONLY the missing code string. Do NOT use markdown. Do NOT wrap in backticks. Do NOT explain."
        )

        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 64,
            "temperature": 0.1
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=8)
            if response.status_code == 200:
                result_data = response.json()
                text = result_data.get("choices", [])[0].get("message", {}).get("content", "")
                if text.startswith("```"):
                    text = "\n".join(text.split("\n")[1:])
                if text.endswith("```"):
                    text = "\n".join(text.split("\n")[:-1])
                return text.strip("\n")
            return ""
        except Exception:
            return ""
