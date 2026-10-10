# AI-Powered Bug Detection System

A clean, modular Python application providing **AST-based static bug analysis**, **syntax and indentation error detection**, **review history tracking via SQLite**, and **optional AI-assisted code review powered by OpenAI**, accessible via a **modern web dashboard** or a **terminal CLI**.

---

## Key Features

- **Strict Non-Execution Safety**: Submitted source code is parsed strictly as passive text using Python's standard `ast` module. Code is **never** executed, imported, or run in a subshell.
- **Python Syntax Error Pointer**: Pinpoints `SyntaxError` and `IndentationError` with exact 1-indexed line numbers, column offsets, and formatted ASCII caret pointer diagrams (`^`).
- **Modular AST Static Analysis Rules**:
  - **Security Rules**:
    - `SEC001`: Dangerous dynamic execution via `eval()` or `exec()`.
    - `SEC002`: Unsafe shell execution via `os.system()` or `subprocess` with `shell=True`.
    - `SEC003`: Insecure temporary file generation via `tempfile.mktemp()`.
  - **Correctness Rules**:
    - `COR001`: Mutable default arguments (`def fn(x=[], y={})`).
    - `COR002`: Ineffective comparisons (`== None`, `!= None`, `== True`, `== False`).
    - `COR003`: Division or modulo by literal zero (`/ 0`, `// 0`, `% 0`).
    - `COR004`: Duplicate dictionary keys in literal dictionaries (`{"a": 1, "a": 2}`).
    - `COR005`: Unreachable code after `return`, `raise`, `break`, or `continue`.
  - **Style & Quality Rules**:
    - `STY001`: Bare `except:` clauses or `except BaseException:`.
    - `STY002`: Identifiers shadowing Python built-ins (`list`, `dict`, `str`, `id`, `open`).
    - `STY003`: Assertions testing a 2-tuple (`assert (cond, msg)` which is always truthy).
- **Persistent Review History**:
  - Local, zero-configuration SQLite database (`data/history.db`).
  - Stores unique review IDs, UTC timestamps, SHA-256 code digests, findings, syntax errors, and execution timings.
  - Full CRUD operations with 100% parameterized SQL queries.
- **Optional AI-Powered Code Review**:
  - Leverages OpenAI (`gpt-4o-mini` by default).
  - Produces an overall code quality score (0–100), latency metrics, latent bug analysis, and suggested refactorings.
  - **100% Optional**: Works completely offline in static AST mode if no API key is provided.
  - **Secure Secret Management**: API keys are read strictly from `.env` or system environment variables and are never leaked to logs, history, or web responses.
- **Modern Web Dashboard**:
  - Fast, responsive Single-Page Application (FastAPI backend).
  - Monospace code editor with Tab indentation support and instant sample presets.
  - Visual metrics, severity filters (All, Error, Warning, Info), and expandable review history drawer.
- **Command-Line Interface (CLI)**:
  - Formatted terminal output with ANSI colors, line numbers, and actionable suggestions.
  - Pipeline friendly with `--json` output and standard input (`-`) support.

---

## Requirements

- **Operating System**: Linux (Ubuntu 22.04+, Ubuntu 26.04+, Debian, WSL2) or macOS / Windows.
- **Python Version**: **Python 3.10+** (Tested and verified on **Python 3.14.4**).
- **SQLite3**: Python built-in standard library module (no external server required).

---

## Installation & Setup

### 1. Clone or Navigate to the Project Directory
```bash
cd /path/to/ai-powered-bug-detection
```

### 2. Activate the Virtual Environment
A virtual environment has already been created in `.venv/`. To activate it in your terminal:

```bash
# On Linux / WSL / macOS
source .venv/bin/activate
```

*(If you ever need to create a fresh virtual environment from scratch)*:
```bash
python3 -m venv --without-pip .venv
curl -sS https://bootstrap.pypa.io/get-pip.py | .venv/bin/python
.venv/bin/pip install -r requirements.txt
```

---

## Configuration & OpenAI API Key (Optional)

The application includes `.env.example`. To customize settings or enable AI reviews:

1. Copy the example configuration to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Open `.env` and set your OpenAI API key:
   ```ini
   # Optional OpenAI API Key
   OPENAI_API_KEY=your_openai_api_key_here

   # Model name (default: gpt-4o-mini)
   OPENAI_MODEL=gpt-4o-mini

   # Server host and port
   APP_HOST=127.0.0.1
   APP_PORT=8000

   # SQLite Database path
   DB_PATH=data/history.db
   ```

### Using Without an API Key
If you do not set `OPENAI_API_KEY`, **the application works completely without error**. All AST static analysis, syntax checking, SQLite persistence, and dashboard features function at full capacity.

---

## How to Start the Web Dashboard

Run the FastAPI application with Uvicorn:

```bash
# Using the active virtual environment:
uvicorn bug_detector.web.app:app --host 127.0.0.1 --port 8000 --reload

# Or directly with the virtualenv binary:
.venv/bin/uvicorn bug_detector.web.app:app --host 127.0.0.1 --port 8000
```

Once started, open your web browser at:
👉 **[http://127.0.0.1:8000](http://127.0.0.1:8000)**

### Dashboard Features:
1. Select a pre-loaded sample from the **"Load Demo Snippet..."** dropdown.
2. Click **"Analyze Code"** to view findings, line numbers, and actionable suggestions.
3. Toggle the **"Enable AI Review"** checkbox if an OpenAI API key is configured.
4. Click **"Review History"** in the top navigation bar to view past scans, re-inspect code, or delete past records.

---

## How to Use the CLI

You can analyze Python files directly from the command line:

```bash
# Analyze a Python script
python -m bug_detector path/to/script.py

# Analyze with optional AI review enabled
python -m bug_detector path/to/script.py --ai

# Output raw JSON report (ideal for CI/CD pipelines)
python -m bug_detector path/to/script.py --json

# Analyze source code directly from stdin
echo "def f(x=[]): return 1 / 0" | python -m bug_detector -

# View recent review history stored in SQLite
python -m bug_detector --history

# Clear SQLite review history
python -m bug_detector --clear-history
```

---

## How to Run Automated Tests

The project includes a comprehensive automated test suite covering syntax detection, AST rules, SQLite storage, CLI, web API, and mocked AI responses.

### Run with Pytest:
```bash
# Run all tests
.venv/bin/pytest -v tests

# Run in quiet mode
.venv/bin/pytest -q
```

### Run with Python Standard Library Unittest (Zero Dependencies):
```bash
.venv/bin/python -m unittest discover -s tests -p "test_*.py"
```

---

## Project Directory Structure

```text
ai-powered-bug-detection/
├── .env.example               # Template for environment configuration
├── .gitignore                 # Excludes .venv, .env, data/, databases, and caches
├── README.md                  # Complete documentation and setup guide
├── requirements.txt           # Verified Python dependencies
├── pyproject.toml             # Project packaging metadata
│
├── bug_detector/              # Core application package
│   ├── __init__.py            # Package exports and version
│   ├── __main__.py            # Top-level CLI entry point
│   ├── config.py              # Environment configuration loader and settings
│   ├── exceptions.py          # Domain exceptions (StorageError, etc.)
│   ├── models.py              # Pydantic models (BugFinding, AnalysisReport, ReviewRecord)
│   ├── service.py             # High-level coordinator (Analysis + AI + Storage)
│   │
│   ├── analyzer/              # Static analysis engine
│   │   ├── __init__.py
│   │   ├── engine.py          # ASTAnalyzer orchestration
│   │   ├── syntax_checker.py  # Safe syntax and indentation parser
│   │   └── rules/             # Modular AST rule definitions
│   │       ├── __init__.py    # Rule registry and export
│   │       ├── base.py        # BaseRule abstract class
│   │       ├── correctness.py # COR001 to COR005
│   │       ├── security.py    # SEC001 to SEC003
│   │       └── style.py       # STY001 to STY003
│   │
│   ├── ai/                    # Optional OpenAI code review
│   │   ├── __init__.py
│   │   ├── client.py          # Resilient OpenAI client wrapper
│   │   ├── models.py          # AIReviewResult and AIFinding models
│   │   └── prompts.py         # Structured review prompt templates
│   │
│   ├── storage/               # Persistence layer
│   │   ├── __init__.py
│   │   ├── database.py        # SQLite connection and schema manager
│   │   └── repository.py      # ReviewRepository CRUD and search operations
│   │
│   ├── cli/                   # Command-line interface
│   │   ├── __init__.py
│   │   ├── __main__.py        # CLI package runner
│   │   └── main.py            # Terminal interface and argument parser
│   │
│   └── web/                   # Web application
│       ├── __init__.py
│       ├── app.py             # FastAPI backend with REST endpoints
│       └── static/            # Frontend Single-Page Application
│           ├── index.html     # Dashboard user interface
│           ├── css/style.css  # Modern theme styling
│           └── js/app.js      # Client interactivity and API integration
│
└── tests/                     # Automated test suite (68 tests)
    ├── __init__.py
    ├── test_ai_reviewer.py    # Mocked AI tests and error handling
    ├── test_ast_rules.py      # AST rules positive and negative unit tests
    ├── test_cli.py            # CLI terminal execution tests
    ├── test_engine.py         # ASTAnalyzer engine tests
    ├── test_integration.py    # End-to-end integration and security tests
    ├── test_storage.py        # SQLite database and repository tests
    ├── test_syntax_checker.py # Syntax and indentation error tests
    └── test_web_api.py        # FastAPI endpoints and dashboard tests
```

---

## Security Notes & Limitations

- **Non-Execution Assurance**: Code submitted to the analyzer is parsed exclusively using `ast.parse`. It is never executed, evaluated, or imported.
- **API Key Security**: The API key is stored only in `.env` (which is excluded from Git via `.gitignore`). The web API `/api/health` reports only whether an API key is configured as a boolean flag and never exposes key contents.
- **Dynamic Behavior**: Static AST analysis evaluates code structure without runtime information. Dynamic behaviors such as monkey patching or runtime-computed attributes require dynamic execution or complete type checkers (e.g. `mypy`).
- **Database Concurrency**: The SQLite database uses standard connection pooling suitable for local development and single-server deployments. For multi-node distributed setups, a dedicated database service (e.g. PostgreSQL) can replace the SQLite repository layer.
