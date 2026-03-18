import os
import logging
import platform
import subprocess
from datetime import datetime

from flask import Flask, jsonify, render_template, request
import psutil


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Logs live under logs/ so they can be persisted/inspected easily.
LOG_DIR = os.path.join(BASE_DIR, "logs")
LOG_FILE = os.path.join(LOG_DIR, "system.log")

# Alert levels and self-healing thresholds (can be overridden via environment variables)
WARNING_THRESHOLD = float(os.getenv("AUTOOPS_WARNING_THRESHOLD", "70"))
CRITICAL_THRESHOLD = float(os.getenv("AUTOOPS_CRITICAL_THRESHOLD", "85"))

# If enabled, the app will actually attempt to terminate the top CPU process (safely).
# Render deployments will typically run in a container and may not allow process control.
ENABLE_SELF_HEALING = os.getenv("AUTOOPS_ENABLE_SELF_HEALING", "true").lower() in ("1", "true", "yes", "on")

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


def get_system_metrics() -> dict:
    """
    Collect core system metrics using psutil.

    Returns a dictionary with CPU, memory, and disk usage percentages.
    """
    cpu_usage = psutil.cpu_percent(interval=0.5)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage(os.path.abspath(os.sep))

    return {
        "cpu": cpu_usage,
        "memory": memory.percent,
        "disk": disk.percent,
    }

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

    If enabled, high CPU events can trigger a real termination of the top CPU process,
    protected by safety rules (protected process list and protected PIDs).
    All actions are logged to logs/system.log for auditing.
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

    # High CPU usage handling: identify the top process and terminate it (if allowed).
    if metrics["cpu"] >= CRITICAL_THRESHOLD:
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
                actions.append(message)
            elif not ENABLE_SELF_HEALING:
                message = (
                    f"High CPU detected ({metrics['cpu']:.1f}%). "
                    f"Self-healing disabled; would terminate pid={pid} name={name}."
                )
                logging.warning(message)
                actions.append(message)
            else:
                ok, result_msg = terminate_process(int(pid), name)
                if ok:
                    logging.warning("Self-healing action: %s", result_msg)
                    actions.append(f"Self-healing: {result_msg}")
                else:
                    logging.error("Self-healing failed: %s", result_msg)
                    actions.append(f"Self-healing failed: {result_msg}")

    # High memory usage handling: safe demonstration action (no OS cache clearing here).
    if metrics["memory"] >= CRITICAL_THRESHOLD:
        message = (
            f"High memory detected ({metrics['memory']:.1f}%). "
            "Recommendation: close memory-heavy apps or restart services to reclaim memory."
        )
        logging.warning(message)
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


@app.route("/")
def index():
    """
    Render the main dashboard page.

    The template loads static JavaScript to poll back-end APIs.
    """
    return render_template("index.html")


@app.route("/stats")
def stats():
    """
    API endpoint: current system metrics, alert levels, explanation layer,
    and any self-healing actions taken.
    """
    metrics = get_system_metrics()
    actions = perform_self_healing(metrics)
    explanation = build_explanation_and_recommendation(metrics)

    response = {
        "metrics": metrics,
        "alert_levels": {
            "cpu": get_alert_level(metrics["cpu"]),
            "memory": get_alert_level(metrics["memory"]),
            "disk": get_alert_level(metrics["disk"]),
        },
        "thresholds": {"warning": WARNING_THRESHOLD, "critical": CRITICAL_THRESHOLD},
        "explanation": explanation,
        "actions": actions,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    return jsonify(response)


@app.route("/processes")
def processes():
    """
    API endpoint: top CPU-consuming processes.
    """
    top = get_top_processes(limit=5)
    return jsonify({"processes": top})


@app.route("/logs")
def logs():
    """
    API endpoint: recent log lines from logs/system.log.

    The frontend uses this to display recent self-healing actions.
    """
    lines = tail_log_file(LOG_FILE, max_lines=100)
    return jsonify({"lines": lines})


if __name__ == "__main__":
    # Development entrypoint. In production (e.g. Render), a WSGI server like gunicorn
    # should be used instead, pointing at 'app:app'.
    logging.info("Starting AutoOps AI – Self-Healing Infrastructure Monitor (development server).")
    app.run(host="0.0.0.0", port=5000, debug=True)

