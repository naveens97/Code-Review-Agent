"""
Code Review Agent -- Flask backend.

Routes:
  POST /api/execute          run submitted code, return stdout/stderr
  POST /api/analyze          static-analyze submitted code, return a report
  GET  /api/history          list past reviews
  GET  /api/history/<id>     full detail for one past review
  DELETE /api/history/<id>   remove one past review
  GET  /api/health           liveness check
  GET  /*                    serves the built frontend (frontend/dist)
"""
import os

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

import database as db
from analyzer import analyze_code
from config import Config
from executor import get_executor

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIST = os.path.abspath(os.path.join(BASE_DIR, "..", "frontend", "dist"))

app = Flask(__name__, static_folder=FRONTEND_DIST, static_url_path="")
CORS(app)  # Fine for local dev / same-origin prod; restrict origins before exposing publicly.

db.init_db(Config.DATABASE_PATH)
executor = get_executor(Config)


def _error(message, status=400):
    return jsonify({"error": message}), status


def _validate_code(payload) -> tuple:
    """Returns (code, error_response_or_None)."""
    code = (payload or {}).get("code", "")
    if not isinstance(code, str) or not code.strip():
        return None, _error("No code provided.")
    if len(code) > Config.MAX_CODE_LENGTH:
        return None, _error(f"Code exceeds the {Config.MAX_CODE_LENGTH:,}-character limit.")
    return code, None


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/api/execute", methods=["POST"])
def api_execute():
    payload = request.get_json(silent=True) or {}
    code, err = _validate_code(payload)
    if err:
        return err

    stdin_data = payload.get("stdin", "")
    if not isinstance(stdin_data, str):
        stdin_data = ""
    if len(stdin_data) > Config.MAX_STDIN_LENGTH:
        return _error(f"stdin exceeds the {Config.MAX_STDIN_LENGTH:,}-character limit.")

    language = payload.get("language", "python")
    if not isinstance(language, str):
        language = "python"

    try:
        result = executor.execute(code, language=language, stdin=stdin_data)
    except Exception as e:  # noqa: BLE001 -- last line of defense, never 500 on user code
        return jsonify({
            "success": False, "stdout": "", "stderr": f"Execution failed unexpectedly: {e}",
            "exit_code": -1, "execution_time_ms": 0, "timed_out": False,
        })
    return jsonify(result)


@app.route("/api/analyze", methods=["POST"])
def api_analyze():
    payload = request.get_json(silent=True) or {}
    code, err = _validate_code(payload)
    if err:
        return err

    language = payload.get("language", "python")
    if not isinstance(language, str):
        language = "python"

    ai_api_key = request.headers.get("X-AI-API-Key", "")

    try:
        result = analyze_code(code, language=language, max_complexity=Config.MAX_CYCLOMATIC_COMPLEXITY, ai_key=ai_api_key)
    except ValueError as e:
        # Unsupported language -- a client error (bad request), not a server fault.
        return _error(str(e), status=400)
    except Exception as e:  # noqa: BLE001
        return _error(f"Analysis failed unexpectedly: {e}", status=500)

    try:
        submission_id = db.save_submission(code, result, language=language)
        result["submission_id"] = submission_id
    except Exception:  # noqa: BLE001 -- history is a convenience, not core to the review
        result["submission_id"] = None

    return jsonify(result)


@app.route("/api/chat", methods=["POST"])
def api_chat():
    from analyzer import chat_code
    payload = request.get_json(silent=True) or {}
    code, err = _validate_code(payload)
    if err:
        return err

    language = payload.get("language", "python")
    messages = payload.get("messages", [])
    
    if not isinstance(messages, list) or len(messages) == 0:
        return _error("No messages provided.", status=400)

    ai_api_key = request.headers.get("X-AI-API-Key", "")

    try:
        reply = chat_code(code, language=language, messages=messages, ai_key=ai_api_key)
        return jsonify({"reply": reply})
    except Exception as e:
        return _error(f"Chat failed: {e}", status=500)


@app.route("/api/autocomplete", methods=["POST"])
def api_autocomplete():
    from analyzer import autocomplete_code
    payload = request.get_json(silent=True) or {}
    
    prefix = payload.get("prefix", "")
    suffix = payload.get("suffix", "")
    language = payload.get("language", "python")

    if not isinstance(prefix, str) or not isinstance(suffix, str):
        return _error("Invalid prefix or suffix.", status=400)

    ai_api_key = request.headers.get("X-AI-API-Key", "")

    try:
        completion = autocomplete_code(prefix, suffix, language=language, ai_key=ai_api_key)
        return jsonify({"completion": completion})
    except Exception as e:
        return _error(f"Autocomplete failed: {e}", status=500)


@app.route("/api/history", methods=["GET"])
def api_history():
    limit = request.args.get("limit", default=Config.HISTORY_LIMIT_DEFAULT, type=int)
    limit = max(1, min(limit, 200))
    return jsonify(db.get_history(limit))


@app.route("/api/history/<int:submission_id>", methods=["GET"])
def api_history_detail(submission_id):
    sub = db.get_submission(submission_id)
    if not sub:
        return _error("No review found with that id.", status=404)
    return jsonify(sub)


@app.route("/api/history/<int:submission_id>", methods=["DELETE"])
def api_history_delete(submission_id):
    deleted = db.delete_submission(submission_id)
    if not deleted:
        return _error("No review found with that id.", status=404)
    return jsonify({"deleted": True})


# --- Frontend static serving (production build) ---
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_frontend(path):
    if not os.path.isdir(FRONTEND_DIST):
        return (
            "Frontend build not found. Run `npm install && npm run build` inside "
            "the frontend/ directory, or use `npm run dev` for local development "
            "(see README.md).",
            501,
        )
    full_path = os.path.join(FRONTEND_DIST, path)
    if path and os.path.isfile(full_path):
        return send_from_directory(FRONTEND_DIST, path)
    return send_from_directory(FRONTEND_DIST, "index.html")


if __name__ == "__main__":
    app.run(debug=Config.DEBUG, host=Config.HOST, port=Config.PORT)
