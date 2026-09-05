# CodeSage — Python Code Review Agent

A web-based Python IDE that runs your code and gives it a scored, actionable
code review — bug risks, security issues, style, and performance, each with
a plain-English explanation and a concrete fix.

```
┌─────────────────────────────────────────────────────────┐
│  Monaco editor (Python)     │  Output │ Review │ History │
│                              ├─────────────────────────────┤
│  def calculate_average(     │        ╭─────────╮           │
│      numbers=[]):           │       ╱  Score 92 ╲          │
│      ...                    │      │   Excellent  │         │
│                              │       ╲___________╱          │
│  [▶ Run]  [✦ Review]         │  ⚠ 1 warning · 2 suggestions │
└─────────────────────────────────────────────────────────┘
```

## Features

- **Monaco-powered editor** with real-time Python syntax highlighting — no
  linting-as-you-type; analysis only runs when you ask for it.
- **One-click run** in a resource-limited sandbox (CPU/memory/time capped),
  with stdout/stderr and an animated "running" state.
- **On-demand code review** combining three independent checkers:
  - [Pylint](https://pylint.readthedocs.io/) — bugs, style, complexity
  - [Bandit](https://bandit.readthedocs.io/) — security vulnerabilities
  - A small custom AST layer — nested-loop / string-concat performance
    heuristics, TODO tracking, missing `if __name__ == "__main__":` guard
- **A transparent 0–100 rating** with a documented, tunable formula (see
  [How scoring works](#how-scoring-works)) — not a black box.
- **Post-run review prompt** — after a successful run, the app offers a
  review of the code you just executed.
- **Specific fixes**, not just warnings — many issues include a before/after
  code snippet showing the recommended rewrite.
- **Automatic history** of past reviews (SQLite), click any entry to reload
  it into the editor.
- Built to grow into a multi-language tool: analyzers and executors sit
  behind small interfaces, so adding a language is additive, not a rewrite.

## Architecture

```
code-review-agent/
├── backend/                  Flask API
│   ├── app.py                 routes
│   ├── config.py               all settings, env-var overridable
│   ├── database.py             SQLite history store
│   ├── analyzer/
│   │   ├── base.py              BaseAnalyzer interface
│   │   ├── __init__.py          language registry + get_analyzer() factory
│   │   ├── python_analyzer.py   orchestrates pylint+bandit+custom checks
│   │   ├── pylint_runner.py     shells out to pylint, normalizes JSON
│   │   ├── bandit_runner.py     shells out to bandit, normalizes JSON
│   │   ├── custom_checks.py     AST-based performance/structure checks
│   │   ├── recommendations.py   curated explanations + before/after fixes
│   │   └── rating.py            issues -> 0-100 score (shared by every language)
│   ├── executor/
│   │   ├── base.py              executor interface
│   │   ├── __init__.py          get_executor() factory
│   │   ├── local_sandbox.py     default: subprocess + OS resource limits
│   │   └── judge0_provider.py   optional: delegate to Judge0 (reference, see below)
│   └── tests/                 pytest suite (29 tests)
└── frontend/                  React + Vite
    └── src/
        ├── components/         CodeEditor, Toolbar, OutputPanel,
        │                       ReviewPanel, RatingGauge, IssueList, …
        └── App.jsx              wires it together
```

**Why this split:** both the analyzer and executor sit behind a small
interface (`BaseAnalyzer`, `BaseExecutor`) plus a factory (`get_analyzer(language)`,
`get_executor(config)`) that picks the right implementation. `app.py` calls
`analyze_code(code, language=...)` without knowing or caring whether that
resolves to `PythonAnalyzer` or, eventually, a `JavaScriptAnalyzer` — same
for execution. That factory function is the seam a new language plugs
into; nothing above it changes.

## Quick start (no Node.js required)

The frontend is already built into `frontend/dist/`, and Flask serves it
directly — so you only need Python to try the app immediately:

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python3 app.py
```

Open **http://localhost:5000**.

## Development setup (hot reload)

If you want to edit the frontend, run it separately with Vite's dev
server, which proxies API calls to Flask:

```bash
# terminal 1
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python3 app.py                 # http://localhost:5000 (API)

# terminal 2
cd frontend
npm install
npm run dev                    # http://localhost:5173 (UI, hot reload)
```

Visit **http://localhost:5173** while developing. When you're done, run
`npm run build` inside `frontend/` to refresh `dist/` so the Flask-only
Quick Start path stays up to date.

## Running tests

```bash
cd backend
pip install -r requirements-dev.txt
pytest -v
```

29 tests cover the rating algorithm's edge cases, real pylint/bandit
findings on known-bad code samples, syntax-error handling, the execution
sandbox's timeout/memory/stdin behavior, and the analyzer registry
(unsupported languages fail with a clear error instead of silently
running the wrong analyzer).

## How scoring works

Every finding has a **severity** (critical / warning / info) and costs
points: critical −12, warning −5, info −1.5. Warning and info penalties are
each capped (40 and 15 points respectively) so one noisy, repeated minor
rule can't tank the score by itself — but **critical issues are not
capped**, so code riddled with real bugs or vulnerabilities can still
land at the bottom of the scale. Code that fails to parse at all is
capped at 15 regardless of anything else, because it can't be "mostly
fine" if it doesn't run.

```
score = 100 − (Σ critical penalties)
            − min(Σ warning penalties, 40)
            − min(Σ info penalties, 15)
```

All of this lives in `backend/analyzer/rating.py` as plain constants —
tune `SEVERITY_WEIGHTS` / `SEVERITY_CAPS` if you want a stricter or looser
curve.

## API reference

| Method | Path | Body | Returns |
|---|---|---|---|
| POST | `/api/execute` | `{code, language?, stdin?}` | `{success, stdout, stderr, exit_code, execution_time_ms, timed_out}` |
| POST | `/api/analyze` | `{code, language?}` | `{rating, issues[], summary, metrics, submission_id}` |
| GET | `/api/history?limit=50` | — | list of past reviews (preview only) |
| GET | `/api/history/<id>` | — | full past review, same shape as `/api/analyze` |
| DELETE | `/api/history/<id>` | — | `{deleted: true}` |
| GET | `/api/health` | — | `{status: "ok"}` |

`language` defaults to `"python"` if omitted — today it's also the only
valid value; both routes return a clean `400` (analyze) or an
error-shaped `200` (execute, matching its fail-soft design) rather than a
crash if you pass anything else. The frontend doesn't send this field
yet, since the language dropdown is still Python-only in the UI, but the
backend already understands it end to end.

## Security considerations — please read before deploying publicly

The default executor (`executor/local_sandbox.py`) runs submitted code as
a subprocess **on the same host, with the same OS permissions as the
Flask process**, with these protections:

- Wall-clock timeout (default 8s) and a CPU-time rlimit
- Memory rlimit (default 128MB address space)
- Process-count rlimit (fork-bomb protection)
- Output truncation

This is genuinely useful — it stops infinite loops, memory bombs, and
runaway output from taking down your dev machine — but **it does not
sandbox filesystem or network access**. That's fine for local use, demos,
or a trusted internal tool. It is **not** sufficient for a public site
where strangers submit code.

For a real public deployment, do one of:

1. **Run the whole backend in a container** with `--network=none`, a
   read-only root filesystem, dropped capabilities, and a non-root user.
   See `Dockerfile` and the commented-out hardening block in
   `docker-compose.yml`.
2. **Swap in the Judge0 provider** (`executor/judge0_provider.py`,
   enabled via `EXECUTION_PROVIDER=judge0` + `JUDGE0_API_KEY`), which runs
   code in Judge0's own disposable, network-isolated containers instead
   of this host. This module is a well-formed reference implementation
   but was **not** tested against a live Judge0 instance in the
   environment this project was built in — verify it against current
   Judge0 API docs first.

## Configuration

All of `backend/config.py` reads from environment variables with sane
defaults — nothing needs to change to run locally. Notable ones:

| Variable | Default | Purpose |
|---|---|---|
| `EXECUTION_PROVIDER` | `local` | `local` or `judge0` |
| `EXECUTION_TIMEOUT_SECONDS` | `8` | per-run wall-clock limit |
| `EXECUTION_MEMORY_MB` | `128` | per-run memory limit |
| `MAX_CYCLOMATIC_COMPLEXITY` | `10` | threshold for pylint's complexity check |
| `MAX_CODE_LENGTH` | `50000` | rejects larger submissions with a 400 |
| `GEMINI_API_KEY` | `DEMO` | Sets Gemini AI key. Put your key here to disable demo mode. |
| `OPENAI_API_KEY` | `""` | Sets OpenAI API key. Overrides Gemini if both are provided. |
| `DATABASE_PATH` | `backend/data/history.db` | SQLite file location |

## Extending to another language

The registry pattern described above is live today, not just planned —
`python` is simply the only entry in it so far. Adding another language:

1. Create a class implementing `BaseAnalyzer` (see `analyzer/base.py`),
   e.g. `analyzer/javascript_analyzer.py` wrapping ESLint the way
   `python_analyzer.py` wraps Pylint/Bandit — same input (`code: str`),
   same output shape (`rating`, `issues`, `summary`, `metrics`,
   `has_syntax_error`).
2. Register it: add one line to `ANALYZER_REGISTRY` in `analyzer/__init__.py`.
3. Add a runtime entry to `_LANGUAGE_CONFIGS` in `executor/local_sandbox.py` 
   (it fully supports two-stage compile-then-run models for compiled languages!).
4. Add the language to the dropdown in `Toolbar.jsx` and `constants.js`. The 
   frontend and backend are already fully wired up to accept and process it end-to-end.

Nothing in `app.py`, the rating algorithm, or any React component needs
to change — that's the point of the registry sitting where it does.

## Known limitations

- Static analysis (pylint/bandit/AST heuristics) catches a lot, but it's
  pattern-based — it won't catch every logic bug a human reviewer would.
- No user accounts: history is a single shared local workspace, like an
  editor's local undo history, not per-user cloud storage.
- The Judge0 provider is unverified (see Security Considerations).

## Tech stack

Flask 3 · SQLite · Pylint 4 · Bandit 1.9 · React 18 · Vite 5 ·
Monaco Editor · Framer Motion · lucide-react
