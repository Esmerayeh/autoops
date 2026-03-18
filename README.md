# AutoOps AI – Self-Healing Infrastructure Monitor

Production-ready Flask application that monitors system metrics, exposes JSON APIs, and demonstrates **real self-healing** automation with safety guardrails plus an AI-like explanation/recommendation layer.

## Features

- **System metrics** via `psutil`:
  - CPU usage
  - Memory usage
  - Disk usage
- **JSON APIs**:
  - `GET /stats` – live metrics + alert levels + AI-like explanation + self-healing actions
  - `GET /processes` – top CPU-consuming processes
  - `GET /logs` – recent log lines from `logs/system.log`
- **Dashboard UI (Flask templates + static assets)**:
  - Auto-refreshing cards for CPU, memory, and disk usage (every 2 seconds)
  - 3 alert levels: **Green (Normal)**, **Yellow (Warning ≥ 70%)**, **Red (Critical ≥ 85%)**
  - Color-coded indicators on metric cards
  - Live table of top CPU processes
  - Logs panel for alerts/actions and API request logs
- **Real self-healing (with safety handling)**:
  - If CPU **Critical (≥ 85%)**: identify the top CPU-consuming process and attempt to terminate it:
    - Windows: `taskkill /PID <pid> /F`
    - Linux/macOS: `kill -9 <pid>`
  - **Protected process list** prevents terminating known critical system processes.
  - All actions are logged to `logs/system.log`.
- **Production-ready basics**:
  - `requirements.txt`
  - Gunicorn-compatible `app:app` entrypoint

---

## Project Structure

```text
app.py              # Flask application (APIs, self-healing, logging)
requirements.txt    # Python dependencies
logs/
  └── system.log    # Generated at runtime, holds alerts/actions/request logs
templates/
  └── index.html    # Main dashboard (Flask template)
static/
  ├── style.css     # Dashboard styling
  └── app.js        # Frontend logic (polling, DOM updates)
```

---

## Running Locally

### 1. Create and activate a virtual environment (recommended)

```bash
cd /path/to/this/project

python -m venv .venv

# Windows PowerShell
.venv\Scripts\Activate.ps1

# Or Command Prompt
.venv\Scripts\activate.bat
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the Flask development server

```bash
python app.py
```

By default the app will start on `http://127.0.0.1:5000/`.

Open your browser and navigate to:

- `http://127.0.0.1:5000/` – monitoring dashboard
- `http://127.0.0.1:5000/stats` – raw metrics JSON
- `http://127.0.0.1:5000/processes` – top processes JSON
- `http://127.0.0.1:5000/logs` – recent actions JSON

> Note: The self-healing logic is intentionally **non-destructive**. It logs what *would* happen (e.g., a process termination) rather than actually killing processes.

This project **can perform real termination** when enabled and when the target is not protected. Use it carefully.

---

## Deploying on Render

You can deploy this app as a **Web Service** on Render.

### 1. Push code to GitHub

1. Create a new Git repository (if needed) and commit this project.
2. Push it to a GitHub repository.

### 2. Create a new Render Web Service

1. Log in to Render and choose **New → Web Service**.
2. Connect your GitHub repo that contains this project.
3. Select your branch and click **Create Web Service**.

### 3. Configure Render build & start commands

- **Environment**: `Python`
- **Build Command**:

  ```bash
  pip install -r requirements.txt
  ```

- **Start Command**:

  ```bash
  gunicorn app:app
  ```

Render will:

- Install dependencies from `requirements.txt`
- Start the app with Gunicorn using the `app` object in `app.py`
- Expose the web service via a public URL

Once deployed, you can use the provided Render URL in place of `http://127.0.0.1:5000/`.

### Environment variables (optional)

- `AUTOOPS_WARNING_THRESHOLD` (default `70`)
- `AUTOOPS_CRITICAL_THRESHOLD` (default `85`)
- `AUTOOPS_ENABLE_SELF_HEALING` (default `true`)

> On hosted environments/containers, process termination may fail due to permissions or isolation. The app will log the failure gracefully.

---

## Explaining This Project in an Interview

- **System engineering concepts**:
  - Uses `psutil` to read OS-level metrics (CPU, memory, disk, processes).
  - Demonstrates how to expose operational metrics via HTTP APIs.
- **API design**:
  - `/stats` aggregates metrics and self-healing actions for the UI.
  - `/processes` returns structured process data suitable for charts/tables.
  - `/logs` streams recent operational events from `system.log`.
- **Self-healing / automation**:
  - Implements threshold-based alerting with 3 severity levels.
  - Demonstrates safe automation: attempts termination for CPU-critical events while preventing critical system processes from being killed.
  - Logs all actions and request traces for auditability.
- **Frontend integration**:
  - Vanilla JS polls APIs every 2 seconds and updates the DOM.
  - Visual alerts communicate when metrics cross thresholds.
  - Logs viewer lets you correlate actions with system state.

From here you can extend it with authentication, historical charts (time-series DB), real process management, or integration with alerting tools.

