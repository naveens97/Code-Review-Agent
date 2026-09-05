"""
OpenAI static analyzer.

Uses the OpenAI API to analyze code and generate structured code quality
suggestions with line numbers, severities, explanations, and before/after improvements.
"""

import json
import logging
import requests

logger = logging.getLogger(__name__)

# Structured JSON Schema to pass to OpenAI's response_format
_RESPONSE_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "code_review",
        "schema": {
            "type": "object",
            "properties": {
                "issues": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "rule_id": {"type": "string"},
                            "severity": {"type": "string", "enum": ["critical", "warning", "info"]},
                            "category": {"type": "string", "enum": ["bug", "security", "style", "complexity", "performance", "maintainability", "best-practice"]},
                            "line": {"type": "integer"},
                            "message": {"type": "string"},
                            "recommendation": {"type": "string"},
                            "before": {"type": ["string", "null"]},
                            "after": {"type": ["string", "null"]}
                        },
                        "required": ["rule_id", "severity", "category", "line", "message", "recommendation", "before", "after"],
                        "additionalProperties": False
                    }
                },
                "summary": {"type": "string"}
            },
            "required": ["issues", "summary"],
            "additionalProperties": False
        },
        "strict": True
    }
}


class OpenAIAnalyzer:
    """Uses OpenAI API to perform static code analysis reviews."""

    def __init__(self, api_key: str):
        self.api_key = api_key

    def analyze(self, code: str, language: str = "python") -> dict:
        """Call OpenAI to analyze the code and return structured issues and a summary."""
        if not self.api_key:
            return {"issues": [], "summary": "OpenAI API key is not configured."}

        url = "https://api.openai.com/v1/chat/completions"
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
            f"Return a structured JSON output conforming to the required schema, specifying the list of issues with line numbers, "
            f"categories, messages, and recommendations. If the code is perfectly optimal and has no issues, return an empty issues list."
        )

        payload = {
            "model": "gpt-4o",
            "messages": [
                {"role": "system", "content": "You are a helpful code review assistant."},
                {"role": "user", "content": prompt}
            ],
            "response_format": _RESPONSE_SCHEMA
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
            parsed_review = json.loads(content)

            # Map the parsed issues to our standard format
            issues = []
            for item in parsed_review.get("issues", []):
                # Ensure fields are properly mapped and fallbacks exist
                line_no = item.get("line")
                if line_no is not None:
                    try:
                        line_no = int(line_no)
                    except (ValueError, TypeError):
                        line_no = 1
                else:
                    line_no = 1

                issues.append({
                    "source": "openai",
                    "rule_id": item.get("rule_id", "openai-suggestion"),
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
                    "source": "openai",
                    "rule_id": "openai-optimal",
                    "severity": "info",
                    "category": "best-practice",
                    "line": 1,
                    "column": None,
                    "message": "good solution the code is alteredy in optimal state",
                    "recommendation": "good solution the code is alteredy in optimal state",
                    "before": None,
                    "after": None
                })

            return {
                "issues": issues,
                "summary": parsed_review.get("summary", "Review completed successfully by OpenAI.")
            }

        except Exception as e:
            logger.exception("Failed to run OpenAI analysis.")
            return {
                "issues": [{
                    "source": "openai",
                    "rule_id": "openai-error",
                    "severity": "warning",
                    "category": "tooling",
                    "line": 1,
                    "column": None,
                    "message": f"Failed to get AI suggestions: {str(e)}",
                    "recommendation": "Check your network connection and verify your OPENAI_API_KEY is correct.",
                    "before": None,
                    "after": None
                }],
                "summary": f"OpenAI review analysis failed: {str(e)}"
            }

    def chat(self, code: str, language: str, messages: list) -> str:
        """Process a conversational chat turn using OpenAI."""
        if not self.api_key:
            return "OpenAI API key is not configured."

        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        openai_msgs = [
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
            openai_msgs.append({
                "role": "user" if msg["role"] == "user" else "assistant",
                "content": msg["content"]
            })

        payload = {
            "model": "gpt-4o",
            "messages": openai_msgs
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            if response.status_code != 200:
                return f"Error from OpenAI API: {response.text}"
            
            result_data = response.json()
            return result_data.get("choices", [])[0].get("message", {}).get("content", "No response.")
            
        except Exception as e:
            logger.exception("Failed to run OpenAI chat.")
            return f"An error occurred while contacting the AI: {e}"

    def autocomplete(self, prefix: str, suffix: str, language: str) -> str:
        """Provide inline code completions using OpenAI."""
        if not self.api_key:
            return ""

        url = "https://api.openai.com/v1/chat/completions"
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
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 64,
            "temperature": 0.1
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=10)
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
