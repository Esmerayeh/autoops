import os
import logging
import platform
import subprocess
import threading
import time
import re
import sqlite3
from collections import deque
from datetime import datetime, timezone

from functools import wraps

from flask import Flask, jsonify, render_template, request, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
import psutil


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Logs live under logs/ so they can be persisted/inspected easily.
LOG_DIR = os.path.join(BASE_DIR, "logs")
LOG_FILE = os.path.join(LOG_DIR, "system.log")

# Alert levels and self-healing thresholds (can be overridden via environment variables)
WARNING_THRESHOLD = float(os.getenv("AUTOOPS_WARNING_THRESHOLD", "70"))
CRITICAL_THRESHOLD = float(os.getenv("AUTOOPS_CRITICAL_THRESHOLD", "85"))

# Sampling interval for background metrics collection (seconds)
SAMPLE_INTERVAL_SECONDS = float(os.getenv("AUTOOPS_SAMPLE_INTERVAL_SECONDS", "2"))

# Number of metric snapshots to keep in memory (fixed-size, prevents leaks)
MAX_HISTORY_POINTS = int(os.getenv("AUTOOPS_MAX_HISTORY_POINTS", "100"))
MAX_HISTORY_POINTS = max(50, min(100, MAX_HISTORY_POINTS))

# If enabled, the app will actually attempt to terminate the top CPU process (safely).
# Render deployments will typically run in a container and may not allow process control.
ENABLE_SELF_HEALING = os.getenv("AUTOOPS_ENABLE_SELF_HEALING", "true").lower() in ("1", "true", "yes", "on")

# Rate limiting for real self-healing (avoid repeated termination)
KILL_COOLDOWN_SECONDS = int(os.getenv("AUTOOPS_KILL_COOLDOWN_SECONDS", "30"))
KILL_COOLDOWN_SECONDS = max(10, min(300, KILL_COOLDOWN_SECONDS))

# SQLite database path (in project root for Render compatibility)
DB_FILE = os.path.join(BASE_DIR, "users.db")

# Optional validation rules
USERNAME_MIN_LEN = 3
PASSWORD_MIN_LEN = 5

# Protected process names (never terminate these). Keep names lowercase for comparison.
# This list covers common critical Windows and Linux processes; add more as needed.
PROTECTED_PROCESS_NAMES = {
    "system",
    "system idle process",
    "idle",
    "registry",
    "csrss.exe",
    "wininit.exe",
    "winlogon.exe",
    "services.exe",
    "lsass.exe",
    "smss.exe",
    "svchost.exe",
    "explorer.exe",
    "init",
    "systemd",
    "kthreadd",
    "ksoftirqd",
    "rcu_sched",
}

# Protected PIDs (never terminate these). On Linux/macOS, 1 is init/systemd.
PROTECTED_PIDS = {0, 1}


def configure_logging() -> None:
    """
    Configure application-wide logging.

    Logs are written both to the console (useful for local development)
    and to a persistent file (used by the logs viewer in the UI).
    """
    os.makedirs(LOG_DIR, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


configure_logging()

app = Flask(__name__)
app.secret_key = os.getenv("AUTOOPS_SECRET_KEY", "dev-only-secret-change-me")

# In-memory history (fixed-size) + recent actions (fixed-size)
METRICS_HISTORY: deque[dict] = deque(maxlen=MAX_HISTORY_POINTS)
ACTION_EVENTS: deque[dict] = deque(maxlen=200)

# Synchronization + termination cooldown tracking
HISTORY_LOCK = threading.Lock()
SELF_HEAL_LOCK = threading.Lock()
LAST_TERMINATION_AT: float = 0.0


def login_required(view_func):
    """
    Minimal session-based auth decorator.
    """

    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not session.get("user"):
            return redirect(url_for("login", next=request.path))
        return view_func(*args, **kwargs)

    return wrapper


def get_db_connection() -> sqlite3.Connection:
    """
    Open a SQLite connection.

    SQLite will create the DB file automatically if it doesn't exist.
    """
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """
    Ensure the users table exists.
    """
    try:
        conn = get_db_connection()
        with conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL
                )
                """
            )
        conn.close()
    except Exception as e:
        logging.error("DB init failed: %s", e)


init_db()


@app.before_request
def log_request_start():
    """
    Basic API request logging for operational visibility.

    This is intentionally lightweight and logs method/path + client IP.
    """
    # Avoid spamming logs with static asset requests in production-like runs.
    if request.path.startswith("/static/"):
        return
    logging.info("Request %s %s from %s", request.method, request.path, request.remote_addr)


def get_system_stats() -> dict:
    """
    Collect core system metrics using psutil.

    Returns a dictionary with CPU, memory, and disk usage percentages.
    """
    # Keep sampling very lightweight. Using interval=None avoids blocking.
    cpu_usage = psutil.cpu_percent(interval=None)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage(os.path.abspath(os.sep))

    return {
        "cpu": float(cpu_usage),
        "memory": memory.percent,
        "disk": disk.percent,
    }


def get_system_metrics() -> dict:
    """
    Backwards-compatible alias.
    """
    return get_system_stats()


def get_alert_level(value: float) -> str:
    """
    Convert a percentage value into an alert level string.
    """
    if value >= CRITICAL_THRESHOLD:
        return "red"
    if value >= WARNING_THRESHOLD:
        return "yellow"
    return "green"


def build_explanation_and_recommendation(metrics: dict) -> dict:
    """
    AI-like explanation layer (simple rule-based text).

    Returns a small object the UI can display during warning/critical states.
    """
    cpu = metrics["cpu"]
    mem = metrics["memory"]

    explanation_parts = []
    recommendations = []

    if cpu >= WARNING_THRESHOLD:
        explanation_parts.append("High CPU usage detected due to resource-intensive processes.")
        recommendations.append("Consider closing unused applications or optimizing background tasks.")

    if mem >= WARNING_THRESHOLD:
        explanation_parts.append("Elevated memory usage detected, which may indicate heavy workloads or leaks.")
        recommendations.append("Consider restarting memory-heavy apps and reducing the number of open programs.")

    if not explanation_parts:
        return {
            "summary": "System operating within normal ranges.",
            "recommendation": "No action needed. Continue monitoring.",
        }

    return {
        "summary": " ".join(explanation_parts),
        "recommendation": " ".join(dict.fromkeys(recommendations)),  # de-dupe while keeping order
    }


def get_top_processes(limit: int = 5) -> list:
    """
    Return the top CPU-consuming processes.

    Each returned item includes pid, name, CPU %, and memory %.
    """
    processes = []
    for proc in psutil.process_iter(attrs=["pid", "name", "cpu_percent", "memory_percent"]):
        try:
            info = proc.info
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            # Processes may terminate between iteration and info access; ignore such cases.
            continue
        processes.append(
            {
                "pid": info.get("pid"),
                "name": info.get("name"),
                "cpu_percent": info.get("cpu_percent", 0.0),
                "memory_percent": round(info.get("memory_percent", 0.0), 2),
            }
        )

    processes.sort(key=lambda p: p["cpu_percent"], reverse=True)
    return processes[:limit]


def record_action(level: str, action_type: str, message: str, extra: dict | None = None) -> None:
    """
    Store an action event in memory (fixed-size) and log it.

    This allows /stats to return recent actions without re-reading log files.
    """
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "level": level,
        "type": action_type,
        "message": message,
        "extra": extra or {},
    }
    with HISTORY_LOCK:
        ACTION_EVENTS.append(event)


def is_protected_process(pid: int | None, name: str | None) -> bool:
    """
    Safety check: never terminate protected PIDs or known critical process names.
    """
    if pid is None:
        return True
    if pid in PROTECTED_PIDS:
        return True
    if not name:
        return True
    return name.strip().lower() in PROTECTED_PROCESS_NAMES


def terminate_process(pid: int, name: str) -> tuple[bool, str]:
    """
    Attempt to terminate a process by PID using OS-specific commands.

    Returns (success, message). Any failure is captured as a readable message.
    """
    system = platform.system().lower()

    try:
        if system == "windows":
            # /F forces termination. For a demo tool, this matches the requested behavior.
            cmd = ["taskkill", "/PID", str(pid), "/F"]
        else:
            # Linux/macOS: force kill (requested). Note: this requires permissions.
            cmd = ["kill", "-9", str(pid)]

        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode == 0:
            return True, f"Terminated pid={pid} name={name} using {' '.join(cmd)}"

        stderr = (result.stderr or "").strip()
        stdout = (result.stdout or "").strip()
        details = stderr or stdout or f"exit_code={result.returncode}"
        return False, f"Failed to terminate pid={pid} name={name}. Details: {details}"
    except Exception as e:
        return False, f"Error while terminating pid={pid} name={name}: {e}"


def perform_self_healing(metrics: dict) -> list:
    """
    Apply simple self-healing logic based on current metrics.

    IMPORTANT:
    - This is designed for local/demo usage. In cloud environments (e.g. Render),
      set AUTOOPS_ENABLE_SELF_HEALING=false to force safe simulation.
    - Includes safety rules and rate limiting to prevent repeated terminations.

    Returns a list of action strings for immediate UI display.
    """
    actions = []

    # Alert logging: record when warning/critical thresholds are crossed.
    cpu_level = get_alert_level(metrics["cpu"])
    mem_level = get_alert_level(metrics["memory"])
    disk_level = get_alert_level(metrics["disk"])

    if cpu_level != "green" or mem_level != "green" or disk_level != "green":
        logging.warning(
            "Alert levels cpu=%s mem=%s disk=%s (cpu=%.1f%% mem=%.1f%% disk=%.1f%%)",
            cpu_level,
            mem_level,
            disk_level,
            metrics["cpu"],
            metrics["memory"],
            metrics["disk"],
        )

    # High CPU usage handling: identify the top process and terminate it (if allowed + rate-limited).
    if metrics["cpu"] >= CRITICAL_THRESHOLD:
        now = time.time()
        with SELF_HEAL_LOCK:
            global LAST_TERMINATION_AT
            cooldown_remaining = (LAST_TERMINATION_AT + KILL_COOLDOWN_SECONDS) - now

        if cooldown_remaining > 0:
            message = (
                f"High CPU detected ({metrics['cpu']:.1f}%). "
                f"Self-healing cooldown active ({int(cooldown_remaining)}s remaining)."
            )
            logging.warning(message)
            record_action("WARNING", "rate_limit", message)
            actions.append(message)
            return actions

        top_processes = get_top_processes(limit=1)
        if top_processes:
            proc = top_processes[0]
            pid = proc.get("pid")
            name = proc.get("name") or "unknown"

            if is_protected_process(pid, name):
                message = (
                    f"High CPU detected ({metrics['cpu']:.1f}%). "
                    f"Top process pid={pid}, name={name} is protected; no termination performed."
                )
                logging.warning(message)
                record_action("WARNING", "protected_process", message, {"pid": pid, "name": name})
                actions.append(message)
            elif not ENABLE_SELF_HEALING:
                message = (
                    f"High CPU detected ({metrics['cpu']:.1f}%). "
                    f"Self-healing disabled; would terminate pid={pid} name={name}."
                )
                logging.warning(message)
                record_action("WARNING", "simulation", message, {"pid": pid, "name": name})
                actions.append(message)
            else:
                # Log intent before execution (auditability)
                intent = f"Attempting termination of pid={pid} name={name} due to CPU={metrics['cpu']:.1f}%"
                logging.warning(intent)
                record_action("WARNING", "terminate_intent", intent, {"pid": pid, "name": name})

                ok, result_msg = terminate_process(int(pid), name)
                if ok:
                    logging.warning("Self-healing action: %s", result_msg)
                    actions.append(f"Self-healing: {result_msg}")
                    record_action("WARNING", "terminated", result_msg, {"pid": pid, "name": name})
                    with SELF_HEAL_LOCK:
                        LAST_TERMINATION_AT = time.time()
                else:
                    logging.error("Self-healing failed: %s", result_msg)
                    actions.append(f"Self-healing failed: {result_msg}")
                    record_action("ERROR", "termination_failed", result_msg, {"pid": pid, "name": name})

    # High memory usage handling: safe demonstration action (no OS cache clearing here).
    if metrics["memory"] >= CRITICAL_THRESHOLD:
        message = (
            f"High memory detected ({metrics['memory']:.1f}%). "
            "Recommendation: close memory-heavy apps or restart services to reclaim memory."
        )
        logging.warning(message)
        record_action("WARNING", "memory_alert", message)
        actions.append(message)

    return actions


def tail_log_file(path: str, max_lines: int = 100) -> list:
    """
    Read the last N lines from the log file.

    Implemented in a simple, readable way suitable for small log files.
    """
    if not os.path.exists(path):
        return []

    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    return [line.rstrip("\n") for line in lines[-max_lines:]]


def parse_log_lines(lines: list[str]) -> list[dict]:
    """
    Convert log lines into structured objects: {timestamp, level, message}.

    Expected format: "YYYY-MM-DD HH:MM:SS,mmm [LEVEL] message"
    """
    parsed = []
    pattern = re.compile(r"^(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) \[(?P<lvl>[A-Z]+)\] (?P<msg>.*)$")
    for line in lines:
        m = pattern.match(line)
        if not m:
            parsed.append({"timestamp": None, "level": None, "message": line, "raw": line})
            continue
        parsed.append(
            {
                "timestamp": m.group("ts"),
                "level": m.group("lvl"),
                "message": m.group("msg"),
                "raw": line,
            }
        )
    return parsed


def get_recent_action_events(max_events: int = 10, within_seconds: int = 10) -> list[dict]:
    """
    Return recent action events from memory (not from file logs).
    """
    now = time.time()
    with HISTORY_LOCK:
        events = list(ACTION_EVENTS)[-max_events:]
    # Filter by time window
    filtered = []
    for e in reversed(events):
        try:
            ts = e.get("timestamp", "")
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            age = now - dt.timestamp()
        except Exception:
            age = 0
        if age <= within_seconds:
            filtered.append(e)
    return list(reversed(filtered))


def append_history_snapshot(metrics: dict) -> dict:
    """
    Add a snapshot to in-memory history (fixed-size).
    """
    snapshot = {
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "metrics": metrics,
        "alert_levels": {
            "cpu": get_alert_level(metrics["cpu"]),
            "memory": get_alert_level(metrics["memory"]),
            "disk": get_alert_level(metrics["disk"]),
        },
    }
    with HISTORY_LOCK:
        METRICS_HISTORY.append(snapshot)
    return snapshot


def metrics_sampler_loop() -> None:
    """
    Background sampler that collects metrics every SAMPLE_INTERVAL_SECONDS.

    This avoids blocking the request thread and keeps API responses fast.
    """
    # Warm up cpu_percent so the first sample isn't always 0.0 on some platforms.
    try:
        psutil.cpu_percent(interval=None)
    except Exception:
        pass

    while True:
        start = time.time()
        try:
            metrics = get_system_stats()
            append_history_snapshot(metrics)
            # Self-healing decisions are evaluated on the same cadence as sampling.
            perform_self_healing(metrics)
        except Exception as e:
            logging.error("Sampler error: %s", e)
            record_action("ERROR", "sampler_error", str(e))

        elapsed = time.time() - start
        sleep_for = max(0.2, SAMPLE_INTERVAL_SECONDS - elapsed)
        time.sleep(sleep_for)


def start_background_sampler() -> None:
    """
    Start the background sampler thread once.

    Flask's debug reloader launches two processes; guard against double-start.
    """
    if app.debug and os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        return

    t = threading.Thread(target=metrics_sampler_loop, daemon=True, name="autoops-metrics-sampler")
    t.start()


start_background_sampler()


@app.route("/signup", methods=["GET", "POST"])
def signup():
    """
    Signup page to create a new user in SQLite.
    """
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""

        if len(username) < USERNAME_MIN_LEN:
            return render_template("signup.html", error=f"Username must be at least {USERNAME_MIN_LEN} characters.")
        if len(password) < PASSWORD_MIN_LEN:
            return render_template("signup.html", error=f"Password must be at least {PASSWORD_MIN_LEN} characters.")

        try:
            conn = get_db_connection()
            existing = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
            if existing:
                conn.close()
                return render_template("signup.html", error="User already exists")

            password_hash = generate_password_hash(password)
            # TEMP DEBUG (requested): confirm hashing output is created
            print("SIGNUP_DEBUG username:", username)
            print("SIGNUP_DEBUG password:", password)
            print("SIGNUP_DEBUG hash_prefix:", str(password_hash)[:25])
            with conn:
                conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password_hash))
            conn.close()

            logging.info("New user created: '%s'", username)
            return redirect(url_for("login"))
        except Exception as e:
            import traceback
            print("SIGNUP ERROR:", e)
            traceback.print_exc()
    return "Signup failed. Please try again."

    return render_template("signup.html", error=None)


@app.route("/login", methods=["GET", "POST"])
def login():
    """
    Login page. Validates username/password against SQLite (hashed passwords).
    """
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""

        try:
            conn = get_db_connection()
            row = conn.execute("SELECT username, password FROM users WHERE username = ?", (username,)).fetchone()
            conn.close()
        except Exception as e:
            logging.error("Login DB error: %s", e)
            return render_template("login.html", error="Login failed. Please try again.")

        # TEMP DEBUG (requested): confirm DB row + submitted password
        print("LOGIN_DEBUG row:", dict(row) if row else None)
        print("LOGIN_DEBUG password:", password)

        if not row:
            logging.warning("Failed login (no user) for '%s'.", username or "<empty>")
            return render_template("login.html", error="Invalid credentials")

        stored = row["password"]
        is_valid = check_password_hash(stored, password)

        # Compatibility fix: if an older user was stored with a plaintext password,
        # allow one-time login and upgrade the stored value to a hash.
        if not is_valid and stored == password:
            try:
                conn = get_db_connection()
                with conn:
                    conn.execute(
                        "UPDATE users SET password = ? WHERE username = ?",
                        (generate_password_hash(password), row["username"]),
                    )
                conn.close()
                logging.warning("Upgraded legacy plaintext password to hash for user '%s'.", row["username"])
                is_valid = True
            except Exception as e:
                logging.error("Failed to upgrade legacy password for user '%s': %s", row["username"], e)

        if not is_valid:
            logging.warning("Failed login (bad password) for '%s'.", username)
            return render_template("login.html", error="Invalid credentials")

        session["user"] = row["username"]
        logging.info("User '%s' logged in.", row["username"])
        next_url = request.args.get("next") or url_for("index")
        return redirect(next_url)

    return render_template("login.html", error=None)


@app.route("/logout")
def logout():
    """
    Clear session and return to login.
    """
    user = session.get("user")
    session.clear()
    logging.info("User '%s' logged out.", user or "<unknown>")
    return redirect(url_for("login"))


@app.route("/")
@login_required
def index():
    """
    Render the main dashboard page.

    The template loads static JavaScript to poll back-end APIs.
    """
    return render_template("index.html")


@app.route("/stats")
@login_required
def stats():
    """
    API endpoint: current system metrics, alert levels, explanation layer,
    and any self-healing actions taken.
    """
    try:
        with HISTORY_LOCK:
            latest = METRICS_HISTORY[-1] if METRICS_HISTORY else None
        if latest:
            metrics = latest["metrics"]
            levels = latest["alert_levels"]
            timestamp = latest["timestamp"]
        else:
            metrics = get_system_stats()
            snap = append_history_snapshot(metrics)
            levels = snap["alert_levels"]
            timestamp = snap["timestamp"]

        explanation = build_explanation_and_recommendation(metrics)
        actions = [e["message"] for e in get_recent_action_events(max_events=10, within_seconds=10)]

        response = {
            "metrics": metrics,
            "alert_levels": levels,
            "thresholds": {"warning": WARNING_THRESHOLD, "critical": CRITICAL_THRESHOLD},
            "explanation": explanation,
            "actions": actions,
            "timestamp": timestamp,
            "config": {
                "self_healing_enabled": ENABLE_SELF_HEALING,
                "kill_cooldown_seconds": KILL_COOLDOWN_SECONDS,
                "sample_interval_seconds": SAMPLE_INTERVAL_SECONDS,
            },
        }
        return jsonify(response)
    except Exception as e:
        logging.error("Error in /stats: %s", e)
        record_action("ERROR", "api_error", f"/stats failed: {e}")
        return jsonify({"error": "Failed to collect stats."}), 500


@app.route("/processes")
@login_required
def processes():
    """
    API endpoint: top CPU-consuming processes.
    """
    try:
        top = get_top_processes(limit=5)
        # Security constraint: do not expose process command lines/args.
        return jsonify({"processes": top})
    except Exception as e:
        logging.error("Error in /processes: %s", e)
        record_action("ERROR", "api_error", f"/processes failed: {e}")
        return jsonify({"error": "Failed to list processes."}), 500


@app.route("/history")
@login_required
def history():
    """
    API endpoint: return past metric snapshots (fixed-size in memory).

    Query params:
      - limit: number of points (max 100)
    """
    try:
        limit = int(request.args.get("limit", "60"))
        limit = max(10, min(100, limit))
        with HISTORY_LOCK:
            items = list(METRICS_HISTORY)[-limit:]
        return jsonify({"history": items, "count": len(items)})
    except Exception as e:
        logging.error("Error in /history: %s", e)
        record_action("ERROR", "api_error", f"/history failed: {e}")
        return jsonify({"error": "Failed to load history."}), 500


@app.route("/logs")
@login_required
def logs():
    """
    API endpoint: recent log lines from logs/system.log.

    The frontend uses this to display recent self-healing actions.
    """
    try:
        lines = tail_log_file(LOG_FILE, max_lines=100)
        entries = parse_log_lines(lines)
        return jsonify({"entries": entries, "count": len(entries)})
    except Exception as e:
        logging.error("Error in /logs: %s", e)
        record_action("ERROR", "api_error", f"/logs failed: {e}")
        return jsonify({"error": "Failed to load logs."}), 500


if __name__ == "__main__":
    # Development entrypoint. In production (e.g. Render), a WSGI server like gunicorn
    # should be used instead, pointing at 'app:app'.
    logging.info("Starting AutoOps AI – Self-Healing Infrastructure Monitor (development server).")
    app.run(host="0.0.0.0", port=5000, debug=True)

