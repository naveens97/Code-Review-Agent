"""
Gemini AI static analyzer.

Uses the Gemini 1.5 Flash API to analyze code and generate structured code quality
suggestions with line numbers, severities, explanations, and before/after improvements.
"""

import json
import logging
import requests

logger = logging.getLogger(__name__)

# Structured JSON Schema to pass to Gemini's generationConfig
_RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "issues": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "rule_id": {"type": "STRING"},
                    "severity": {"type": "STRING", "enum": ["critical", "warning", "info"]},
                    "category": {"type": "STRING", "enum": ["bug", "security", "style", "complexity", "performance", "maintainability", "best-practice"]},
                    "line": {"type": "INTEGER"},
                    "message": {"type": "STRING"},
                    "recommendation": {"type": "STRING"},
                    "before": {"type": "STRING"},
                    "after": {"type": "STRING"}
                },
                "required": ["rule_id", "severity", "category", "line", "message", "recommendation"]
            }
        },
        "summary": {"type": "STRING"}
    },
    "required": ["issues", "summary"]
}


class GeminiAnalyzer:
    """Uses Gemini API to perform static code analysis reviews."""

    def __init__(self, api_key: str):
        self.api_key = api_key

    def analyze(self, code: str, language: str = "python") -> dict:
        """Call Gemini to analyze the code and return structured issues and a summary."""
        if not self.api_key:
            return {"issues": [], "summary": "Gemini API key is not configured."}

        if self.api_key == "DEMO":
            return self._get_demo_suggestions(code, language)

        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key
        }

        prompt = (
            f"You are a strict, senior code reviewer. Perform a static review of the following {language} code:\n\n"
            f"```\n{code}\n```\n\n"
            f"Identify bugs, security vulnerabilities, performance bottlenecks, style issues, and maintainability concerns. "
            f"CRITICAL: Keep your `message` and `recommendation` fields EXTREMELY CONCISE (1-3 sentences max). Do not ramble. "
            f"If the code uses a brute force approach, flag it and provide the optimal algorithmic solution briefly. "
            f"Provide the before/after code blocks demonstrating the fix. "
            f"Return ONLY a strictly valid JSON object (no markdown, no backticks). The JSON object MUST conform EXACTLY to this structure:\n"
            f"{json.dumps(_RESPONSE_SCHEMA)}"
        )

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt}
                    ]
                }
            ]
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=60)
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

            # Navigate response structure to retrieve candidate text
            candidates = result_data.get("candidates", [])
            if not candidates:
                logger.error("Gemini API returned no candidates.")
                return {"issues": [], "summary": "AI generated no review candidates."}

            part_text = candidates[0].get("content", {}).get("parts", [])[0].get("text", "")
            
            # Clean possible markdown wrapping
            part_text = part_text.strip()
            if part_text.startswith("```json"):
                part_text = part_text[7:]
            elif part_text.startswith("```"):
                part_text = part_text[3:]
            if part_text.endswith("```"):
                part_text = part_text[:-3]
            part_text = part_text.strip()

            try:
                parsed_review = json.loads(part_text)
            except json.JSONDecodeError as e:
                raise RuntimeError(f"Failed to parse AI response as JSON: {e}\nResponse text: {part_text[:100]}...")

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
                    "source": "gemini",
                    "rule_id": item.get("rule_id", "gemini-suggestion"),
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
                    "source": "gemini",
                    "rule_id": "gemini-optimal",
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
                "summary": parsed_review.get("summary", "Review completed successfully by Gemini AI.")
            }

        except Exception as e:
            logger.exception("Failed to run Gemini analysis.")
            return {
                "issues": [{
                    "source": "gemini",
                    "rule_id": "gemini-error",
                    "severity": "warning",
                    "category": "tooling",
                    "line": 1,
                    "column": None,
                    "message": f"Failed to get AI suggestions: {str(e)}",
                    "recommendation": "Check your network connection and verify your GEMINI_API_KEY is correct.",
                    "before": None,
                    "after": None
                }],
                "summary": f"Gemini review analysis failed: {str(e)}"
            }

    def _get_demo_suggestions(self, code: str, language: str) -> dict:
        """Returns mock AI suggestions for demonstration purposes."""
        issues = []
        summary = "AI Review (Demo Mode): Identified code quality recommendations."

        if language == "python":
            if "numbers = []" in code or "numbers=[]" in code:
                issues.append({
                    "source": "gemini",
                    "rule_id": "gemini-mutable-default",
                    "severity": "warning",
                    "category": "bug",
                    "line": 1,
                    "column": None,
                    "message": "AI Suggestion: Mutable default argument list used. Lists are instantiated once at function definition time, so changes will persist across calls.",
                    "recommendation": "Use `None` as default value instead, and initialize a new list inside the function body.",
                    "before": "def calculate_average(numbers=[]):",
                    "after": "def calculate_average(numbers=None):\n    if numbers is None:\n        numbers = []"
                })
            if "total = total + numbers[i]" in code:
                issues.append({
                    "source": "gemini",
                    "rule_id": "gemini-use-sum",
                    "severity": "info",
                    "category": "performance",
                    "line": 3,
                    "column": None,
                    "message": "AI Suggestion: Manual summation loop found. Python's built-in `sum()` is implemented in C and runs significantly faster.",
                    "recommendation": "Replace the explicit loop with built-in `sum()` function.",
                    "before": "    total = 0\n    for i in range(len(numbers)):\n        total = total + numbers[i]\n    return total / len(numbers)",
                    "after": "    return sum(numbers) / len(numbers)"
                })
        elif language == "java":
            if "factorial" in code:
                issues.append({
                    "source": "gemini",
                    "rule_id": "gemini-recursion-safety",
                    "severity": "warning",
                    "category": "performance",
                    "line": 2,
                    "column": None,
                    "message": "AI Suggestion: Deep recursion detected in factorial calculator. Can cause a StackOverflowError for large inputs.",
                    "recommendation": "Use an iterative loop or dynamic programming instead of simple recursion.",
                    "before": "    static int factorial(int n) {\n        int result;\n        if (n == 0) return 1;\n        result = n * factorial(n - 1);\n        return result;\n    }",
                    "after": "    static int factorial(int n) {\n        int result = 1;\n        for (int i = 1; i <= n; i++) {\n            result *= i;\n        }\n        return result;\n    }"
                })
        elif language == "cpp" or language == "c":
            if "findMax" in code or "sum_array" in code:
                issues.append({
                    "source": "gemini",
                    "rule_id": "gemini-const-correctness",
                    "severity": "info",
                    "category": "style",
                    "line": 4,
                    "column": None,
                    "message": "AI Suggestion: Function parameter passed by value without const keyword. This copies the container which is slow for large datasets.",
                    "recommendation": "Pass by const reference to avoid unnecessary copy overhead.",
                    "before": "int findMax(std::vector<int> nums)",
                    "after": "int findMax(const std::vector<int>& nums)"
                })

        if not issues:
            issues.append({
                "source": "gemini",
                "rule_id": "gemini-clean-code",
                "severity": "info",
                "category": "best-practice",
                "line": 1,
                "column": None,
                "message": "AI Suggestion: The program is already at an optimal level.",
                "recommendation": "Good way of approach! Keep up the excellent work.",
                "before": None,
                "after": None
            })

        return {"issues": issues, "summary": summary}

    def chat(self, code: str, language: str, messages: list) -> str:
        """Process a conversational chat turn using Gemini."""
        if not self.api_key or self.api_key == "DEMO":
            return "Demo mode: I cannot answer questions about this code right now. Try upgrading your API key!"

        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent"
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key
        }

        # Format history for Gemini contents array
        contents = []
        
        # System instructions disguised as first user prompt + model ok
        system_prompt = (
            f"You are a helpful coding assistant. The user is currently working on the following {language} code:\n"
            f"```\n{code}\n```\n"
            f"Answer any questions they have about it clearly and concisely. Keep responses short and to the point."
        )
        
        contents.append({"role": "user", "parts": [{"text": system_prompt}]})
        contents.append({"role": "model", "parts": [{"text": "Understood. How can I help you with this code?"}]})

        for msg in messages:
            role = "user" if msg["role"] == "user" else "model"
            contents.append({
                "role": role,
                "parts": [{"text": msg["content"]}]
            })

        payload = {
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": 512,
                "temperature": 0.5
            }
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            if response.status_code != 200:
                return f"Error from Google API: {response.text}"
            
            result_data = response.json()
            candidates = result_data.get("candidates", [])
            if not candidates:
                return "The AI returned an empty response."

            return candidates[0].get("content", {}).get("parts", [])[0].get("text", "")
            
        except Exception as e:
            logger.exception("Failed to run Gemini chat.")
            return f"An error occurred while contacting the AI: {e}"

    def autocomplete(self, prefix: str, suffix: str, language: str) -> str:
        """Provide inline code completions using Gemini."""
        if not self.api_key or self.api_key == "DEMO":
            return ""

        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-8b:generateContent"
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key
        }

        prompt = (
            f"You are a strict, ultra-fast code completion engine for {language}. "
            f"Given the code BEFORE the cursor:\n<PREFIX>\n{prefix}\n</PREFIX>\n"
            f"And the code AFTER the cursor:\n<SUFFIX>\n{suffix}\n</SUFFIX>\n\n"
            f"Complete the code exactly where the cursor is. Return ONLY the missing code string. Do NOT use markdown. Do NOT wrap in backticks. Do NOT explain."
        )

        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "maxOutputTokens": 64,
                "temperature": 0.1
            }
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            if response.status_code == 200:
                result_data = response.json()
                candidates = result_data.get("candidates", [])
                if candidates:
                    text = candidates[0].get("content", {}).get("parts", [])[0].get("text", "")
                    # strip accidental markdown blocks if Gemini ignores instructions
                    if text.startswith("```"):
                        text = "\n".join(text.split("\n")[1:])
                    if text.endswith("```"):
                        text = "\n".join(text.split("\n")[:-1])
                    return text.strip("\n")
            return ""
        except Exception:
            return ""
