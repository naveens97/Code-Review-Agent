import unittest
from unittest.mock import patch, MagicMock
from analyzer.gemini_analyzer import GeminiAnalyzer

class TestGeminiAnalyzer(unittest.TestCase):
    @patch("requests.post")
    def test_gemini_analysis_success(self, mock_post):
        # Configure mock response
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": '{"issues": [{"rule_id": "test-rule", "severity": "warning", "category": "style", "line": 5, "message": "use better naming", "recommendation": "rename variables", "before": "int x = 0;", "after": "int count = 0;"}], "summary": "Code looks decent."}'
                            }
                        ]
                    }
                }
            ]
        }
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        analyzer = GeminiAnalyzer("test-api-key")
        result = analyzer.analyze("int x = 0;", "java")

        self.assertEqual(len(result["issues"]), 1)
        issue = result["issues"][0]
        self.assertEqual(issue["source"], "gemini")
        self.assertEqual(issue["rule_id"], "test-rule")
        self.assertEqual(issue["line"], 5)
        self.assertEqual(issue["message"], "use better naming")
        self.assertEqual(issue["before"], "int x = 0;")
        self.assertEqual(issue["after"], "int count = 0;")
        self.assertEqual(result["summary"], "Code looks decent.")

    @patch("requests.post")
    def test_gemini_analysis_failure(self, mock_post):
        mock_post.side_effect = Exception("API connection timed out")

        analyzer = GeminiAnalyzer("test-api-key")
        result = analyzer.analyze("int x = 0;", "java")

        self.assertEqual(len(result["issues"]), 1)
        self.assertEqual(result["issues"][0]["rule_id"], "gemini-error")
        self.assertIn("API connection timed out", result["summary"])
