# AutoOps AI – Self-Healing Infrastructure Monitor

Polished, production-ready Flask application that monitors system metrics, exposes JSON APIs, and demonstrates **safe self-healing automation** with guardrails, **metrics history**, and a deterministic “AI-like” explanation layer.

Built to look and feel like a real DevOps/System Engineering product—simple, fast, and easy to explain in interviews.

## Features

- **System metrics** via `psutil`:
  - CPU usage
  - Memory usage
  - Disk usage
- **Metrics history (last 50–100 points)**:
  - In-memory fixed-size queue (no DB)
  - `GET /history` for past snapshots
  - CPU line chart on the dashboard (Chart.js)
- **JSON APIs**:
  - `GET /stats` – live metrics + alert levels + explanation + recent actions
  - `GET /history` – past metric snapshots (chart-friendly)
  - `GET /processes` – top CPU-consuming processes (safe fields only)
  - `GET /logs` – structured log entries from `logs/system.log`
- **Smart alert system**:
  - Green (Normal), Yellow (Warning ≥ 70%), Red (Critical ≥ 85%)
  - Color-coded cards + critical pulse/glow
- **Self-healing (safe by design)**:
  - If CPU is **Critical (≥ 85%)**:
    - Identifies the top CPU-consuming process
    - **Rate-limited** (max 1 termination per 30s by default)
    - **Never** terminates protected PIDs (0/1) or protected process names
    - Performs **real termination locally** when enabled:
      - Windows: `taskkill /PID <pid> /F`
      - Linux/macOS: `kill -9 <pid>`
    - Falls back to **safe simulation** in cloud/sandbox environments via:
      - `AUTOOPS_ENABLE_SELF_HEALING=false`
- **Basic authentication (session-based)**:
  - `/login`, `/logout`
  - Protects dashboard and APIs
- **Production-ready basics**:
  - `requirements.txt`
  - Gunicorn-compatible `app:app`
  - Dockerfile for containerized runs

---

## Project Structure

```text
app.py              # Flask app (APIs, auth, self-healing, sampler)
Dockerfile          # Container build (gunicorn)
requirements.txt    # Python dependencies
logs/
  └── system.log    # Runtime logs (alerts/actions/requests)
templates/
  ├── index.html    # Dashboard (Flask template)
  └── login.html    # Login page
static/
  ├── style.css     # Premium dark UI
  └── app.js        # Polling + Chart.js updates
```

---

## Architecture (simple)

```text
Browser (UI)
  ├─ polls /stats, /processes, /logs every 2–5s
  └─ polls /history for the CPU chart

Flask API
  ├─ /login, /logout (session auth)
  ├─ /stats (fast: uses latest sampled snapshot)
  ├─ /history (in-memory deque, max 50–100 points)
  ├─ /processes (top CPU processes, safe fields only)
  └─ /logs (tail + parse logs/system.log)

Background sampler thread (every 2s)
  ├─ collects psutil stats (low overhead)
  ├─ appends to in-memory history (fixed-size)
  └─ evaluates self-healing rules (rate-limited + protected list)
```

---

## Screenshots

Add screenshots to `docs/screenshots/` and reference them here:

- `docs/screenshots/dashboard.png`
- `docs/screenshots/login.png`

---

## Local Setup

```bash
cd /path/to/this/project
python -m venv .venv

# Windows PowerShell
.venv\Scripts\Activate.ps1

pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000/`.

### Default login

- Username: `admin`
- Password: `admin123`

Override via environment variables:

- `AUTOOPS_USERNAME`
- `AUTOOPS_PASSWORD`

---

## Deployment on Render

Create a Render **Web Service**.

- **Build Command**:

```bash
pip install -r requirements.txt
```

- **Start Command**:

```bash
gunicorn app:app --bind 0.0.0.0:$PORT
```

### Required environment variables (Render)

- `AUTOOPS_SECRET_KEY` (set a strong value)
- `AUTOOPS_USERNAME`
- `AUTOOPS_PASSWORD`
- `AUTOOPS_ENABLE_SELF_HEALING=false` (cloud-safe)

### Optional environment variables

- `AUTOOPS_WARNING_THRESHOLD` (default `70`)
- `AUTOOPS_CRITICAL_THRESHOLD` (default `85`)
- `AUTOOPS_KILL_COOLDOWN_SECONDS` (default `30`)
- `AUTOOPS_SAMPLE_INTERVAL_SECONDS` (default `2`)
- `AUTOOPS_MAX_HISTORY_POINTS` (default `100`, clamped to 50–100)

---

## Docker

```bash
docker build -t autoops-ai .
docker run -p 5000:5000 ^
  -e AUTOOPS_SECRET_KEY="change-me" ^
  -e AUTOOPS_USERNAME="admin" ^
  -e AUTOOPS_PASSWORD="admin123" ^
  -e AUTOOPS_ENABLE_SELF_HEALING="true" ^
  autoops-ai
```

---

## API Endpoints

- `GET /stats`
- `GET /history?limit=60`
- `GET /processes`
- `GET /logs`
- `GET /login`, `POST /login`, `GET /logout`

---

## Interview talking points

- **System design**: background sampler keeps APIs fast (<200ms typical) and avoids blocking requests
- **Safety**: protected process list + PID blacklist + cooldown rate limiting
- **Cloud constraints**: self-healing disabled by env (`AUTOOPS_ENABLE_SELF_HEALING=false`) to respect sandbox limitations
- **Observability**: structured logs + request logging + action events
- **Explainability**: deterministic rules generate “what happened / why / what to do next” insights


