"""
Lightweight SQLite-backed history store.

Every review (not every run) is saved automatically so the History panel
in the UI has something to show without requiring an explicit "save"
step. No user accounts -- this is a single-workspace local history, the
same way an IDE's local file history works. Swapping in per-user history
later just means adding a user_id column and a WHERE clause; the schema
is intentionally simple so that's a small change, not a rewrite.
"""
import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone

_local = threading.local()
_db_path = None
_lock = threading.Lock()


def init_db(db_path: str):
    global _db_path
    _db_path = db_path
    import os
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL,
                language TEXT NOT NULL DEFAULT 'python',
                score INTEGER,
                label TEXT,
                issues_json TEXT,
                metrics_json TEXT,
                summary TEXT,
                critical_count INTEGER DEFAULT 0,
                warning_count INTEGER DEFAULT 0,
                info_count INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            )
        """)
        conn.commit()


@contextmanager
def _connect():
    conn = sqlite3.connect(_db_path, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def save_submission(code: str, analysis: dict, language: str = "python") -> int:
    rating = analysis["rating"]
    with _lock, _connect() as conn:
        cur = conn.execute(
            """INSERT INTO submissions
               (code, language, score, label, issues_json, metrics_json, summary,
                critical_count, warning_count, info_count, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                code, language, rating["score"], rating["label"],
                json.dumps(analysis["issues"]), json.dumps(analysis.get("metrics", {})),
                analysis["summary"],
                rating["breakdown"]["critical"], rating["breakdown"]["warning"],
                rating["breakdown"]["info"],
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()
        return cur.lastrowid


def get_history(limit: int = 50) -> list:
    with _connect() as conn:
        rows = conn.execute(
            """SELECT id, code, language, score, label, summary,
                      critical_count, warning_count, info_count, created_at
               FROM submissions ORDER BY id DESC LIMIT ?""",
            (limit,),
        ).fetchall()
        results = []
        for row in rows:
            d = dict(row)
            preview = d["code"].strip().splitlines()
            d["preview"] = (preview[0][:80] if preview else "")
            del d["code"]
            results.append(d)
        return results


def get_submission(submission_id: int):
    """Returns a dict shaped like the live /api/analyze response (plus
    `id`, `code`, and `created_at`), so the frontend can render a
    history item with the exact same component it uses for a fresh
    review."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM submissions WHERE id = ?", (submission_id,)
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        return {
            "id": d["id"],
            "code": d["code"],
            "language": d["language"],
            "created_at": d["created_at"],
            "summary": d["summary"],
            "issues": json.loads(d["issues_json"] or "[]"),
            "metrics": json.loads(d["metrics_json"] or "{}"),
            "rating": {
                "score": d["score"],
                "score_out_of_10": round(d["score"] / 10, 1) if d["score"] is not None else None,
                "label": d["label"],
                "breakdown": {
                    "critical": d["critical_count"],
                    "warning": d["warning_count"],
                    "info": d["info_count"],
                },
            },
        }


def delete_submission(submission_id: int) -> bool:
    with _lock, _connect() as conn:
        cur = conn.execute("DELETE FROM submissions WHERE id = ?", (submission_id,))
        conn.commit()
        return cur.rowcount > 0
