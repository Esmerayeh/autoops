"""UI and API routes for AutoOps AI."""

from __future__ import annotations

from flask import Blueprint, Response, current_app, jsonify, request
from flask_login import login_required

from autoops.api.schemas import validate_api_envelope, validate_autonomy_status, validate_cluster_overview, validate_health_payload
from autoops.extensions import csrf, limiter
from autoops.services.runtime import runtime_manager
from autoops.utils.responses import success_response
from autoops.utils.validators import clamp_int

api_bp = Blueprint("api", __name__, url_prefix="/api/v1")
legacy_bp = Blueprint("legacy", __name__)


def monitoring_service():
    assert runtime_manager.monitoring_service is not None
    return runtime_manager.monitoring_service


def control_plane_service():
    assert runtime_manager.control_plane_service is not None
    return runtime_manager.control_plane_service


def alert_level(value: float) -> str:
    if value >= current_app.config["CRITICAL_THRESHOLD"]:
        return "red"
    if value >= current_app.config["WARNING_THRESHOLD"]:
        return "yellow"
    return "green"


@api_bp.route("/health")
@login_required
def health():
    payload = monitoring_service().health_payload()
    validate_health_payload(payload)
    return jsonify(validate_api_envelope(success_response(payload)))


@api_bp.route("/host")
@login_required
def host():
    return jsonify(success_response(monitoring_service().get_host_summary()))


@api_bp.route("/stats")
@login_required
@limiter.limit(lambda: current_app.config["API_RATE_LIMIT"])
def stats_v1():
    payload = success_response(monitoring_service().get_live_summary())
    return jsonify(validate_api_envelope(payload))


@api_bp.route("/history")
@login_required
def history_v1():
    limit = clamp_int(request.args.get("limit"), 90, 10, 300)
    history = monitoring_service().get_history(limit.value)
    return jsonify(success_response({"history": history}, {"count": len(history)}))


@api_bp.route("/processes")
@login_required
def processes_v1():
    limit = clamp_int(request.args.get("limit"), current_app.config["PROCESS_LIST_LIMIT"], 5, 50)
    return jsonify(success_response({"processes": monitoring_service().get_top_processes(limit.value)}))


@api_bp.route("/alerts")
@login_required
def alerts_v1():
    limit = clamp_int(request.args.get("limit"), 50, 5, 200)
    alerts = monitoring_service().get_alerts(limit.value)
    return jsonify(success_response({"alerts": alerts}, {"count": len(alerts)}))


@api_bp.route("/incidents")
@login_required
def incidents_v1():
    limit = clamp_int(request.args.get("limit"), 50, 5, 200)
    incidents = monitoring_service().get_incidents(limit.value)
    timeline = monitoring_service().get_incident_timeline(limit.value * 2)
    return jsonify(success_response({"incidents": incidents, "timeline": timeline}, {"count": len(incidents)}))


@api_bp.route("/decisions")
@login_required
def decisions_v1():
    limit = clamp_int(request.args.get("limit"), 20, 5, 100)
    decisions = monitoring_service().get_recent_decisions(limit.value)
    return jsonify(success_response({"decisions": decisions}, {"count": len(decisions)}))


@api_bp.route("/feedback")
@login_required
def feedback_v1():
    limit = clamp_int(request.args.get("limit"), 20, 5, 100)
    data = monitoring_service().get_feedback(limit.value)
    return jsonify(success_response(data, {"count": len(data["records"])}))


@api_bp.route("/autonomy/status")
@login_required
def autonomy_status_v1():
    data = monitoring_service().get_autonomy_status()
    validate_autonomy_status(data)
    return jsonify(success_response({"autonomy": data}))


@api_bp.route("/autonomy/mode", methods=["POST"])
@login_required
@csrf.exempt
def autonomy_mode_v1():
    payload = request.get_json(silent=True) or {}
    mode = str(payload.get("mode", "")).lower()
    if mode not in {"manual", "assisted", "autonomous"}:
        return jsonify({"ok": False, "error": {"message": "Mode must be manual, assisted, or autonomous."}}), 400
    current_app.config["AUTONOMY_MODE"] = mode
    return jsonify(success_response({"autonomy": monitoring_service().get_autonomy_status()}))


@api_bp.route("/actions")
@login_required
def actions_v1():
    limit = clamp_int(request.args.get("limit"), 50, 5, 200)
    actions = monitoring_service().get_actions(limit.value)
    return jsonify(success_response({"actions": actions}, {"count": len(actions)}))


@api_bp.route("/actions/<int:action_id>/validation")
@login_required
def action_validation_v1(action_id: int):
    validation = monitoring_service().get_action_validation(action_id)
    if validation is None:
        return jsonify({"ok": False, "error": {"message": "Validation result not found."}}), 404
    return jsonify(success_response({"validation": validation}))


@api_bp.route("/logs")
@login_required
def logs_v1():
    limit = clamp_int(request.args.get("limit"), current_app.config["LOG_TAIL_LINES"], 50, 1000)
    level = request.args.get("level")
    entries = monitoring_service().get_logs(level=level, limit=limit.value)
    return jsonify(success_response({"entries": entries}, {"count": len(entries), "level": level or "ALL"}))


@api_bp.route("/recommendations")
@login_required
def recommendations_v1():
    data = monitoring_service().get_live_summary()["analysis"]["recommendation"]
    return jsonify(success_response({"recommendation": data}))


@api_bp.route("/predictions")
@login_required
def predictions_v1():
    data = monitoring_service().get_live_summary()["analysis"]["forecast"]
    return jsonify(success_response({"predictions": data}))


@api_bp.route("/anomalies")
@login_required
def anomalies_v1():
    data = monitoring_service().get_live_summary()["analysis"]["anomaly"]
    return jsonify(success_response({"anomaly": data}))


@api_bp.route("/settings")
@login_required
def settings_v1():
    data = {
        "environment": current_app.config["ENV_NAME"],
        "self_healing_enabled": current_app.config["ENABLE_SELF_HEALING"],
        "dry_run": current_app.config["HEALING_DRY_RUN"],
        "operator_confirmation_required": current_app.config["OPERATOR_CONFIRMATION_REQUIRED"],
        "warning_threshold": current_app.config["WARNING_THRESHOLD"],
        "critical_threshold": current_app.config["CRITICAL_THRESHOLD"],
        "autonomy_mode": current_app.config["AUTONOMY_MODE"],
    }
    return jsonify(success_response({"settings": data}))


@api_bp.route("/policies")
@login_required
def policies_v1():
    data = monitoring_service().healing.policies()
    return jsonify(success_response({"policies": data}, {"count": len(data)}))


@api_bp.route("/cluster/overview")
@login_required
def cluster_overview_v1():
    data = control_plane_service().get_cluster_overview()
    validate_cluster_overview(data)
    return jsonify(success_response({"cluster": data}))


@api_bp.route("/cluster/nodes")
@login_required
def cluster_nodes_v1():
    limit = clamp_int(request.args.get("limit"), 50, 5, 200)
    data = control_plane_service().get_nodes(limit.value)
    return jsonify(success_response({"nodes": data}, {"count": len(data)}))


@api_bp.route("/cluster/dependencies")
@login_required
def cluster_dependencies_v1():
    edges = control_plane_service().get_dependency_map()
    return jsonify(success_response({"dependencies": edges}, {"count": len(edges)}))


@api_bp.route("/cluster/tasks")
@login_required
def cluster_tasks_v1():
    limit = clamp_int(request.args.get("limit"), 20, 1, 100)
    tasks = control_plane_service().get_tasks(limit.value)
    return jsonify(success_response({"tasks": tasks}, {"count": len(tasks)}))


@api_bp.route("/cluster/tasks", methods=["POST"])
@login_required
@csrf.exempt
def cluster_create_task_v1():
    payload = request.get_json(silent=True) or {}
    task_type = str(payload.get("task_type") or "").strip()
    if not task_type:
        return jsonify({"ok": False, "error": {"message": "task_type is required."}}), 400
    task = control_plane_service().create_task(
        task_type=task_type,
        target_node_id=payload.get("target_node_id"),
        payload=payload.get("payload") if isinstance(payload.get("payload"), dict) else {},
    )
    return jsonify(success_response({"task": task})), 201


@api_bp.route("/cluster/nodes/heartbeat", methods=["POST"])
@login_required
@csrf.exempt
def cluster_heartbeat_v1():
    payload = request.get_json(silent=True) or {}
    try:
        node = control_plane_service().heartbeat(payload)
    except ValueError as error:
        return jsonify({"ok": False, "error": {"message": str(error)}}), 400
    except PermissionError as error:
        return jsonify({"ok": False, "error": {"message": str(error)}}), 403
    return jsonify(success_response({"node": node}))


@api_bp.route("/stream")
@login_required
def stream_v1():
    payload = monitoring_service().get_live_summary()
    return Response(f"data: {jsonify(success_response(payload)).get_data(as_text=True)}\n\n", mimetype="text/event-stream")


@legacy_bp.route("/stats")
@login_required
def legacy_stats():
    payload = monitoring_service().get_live_summary()
    snapshot = payload["snapshot"]
    analysis = payload["analysis"]
    response = {
        "metrics": snapshot["metrics"],
        "alert_levels": {
            "cpu": alert_level(snapshot["metrics"]["cpu"]),
            "memory": alert_level(snapshot["metrics"]["memory"]),
            "disk": alert_level(snapshot["metrics"]["disk"]),
        },
        "thresholds": {
            "warning": current_app.config["WARNING_THRESHOLD"],
            "critical": current_app.config["CRITICAL_THRESHOLD"],
        },
        "explanation": {
            "summary": analysis["recommendation"]["summary"],
            "recommendation": analysis["recommendation"]["reasoning"],
        },
        "actions": [item["summary"] for item in payload["recent_actions"]],
        "timestamp": snapshot["timestamp"],
        "config": {
            "self_healing_enabled": current_app.config["ENABLE_SELF_HEALING"],
            "kill_cooldown_seconds": current_app.config["HEALING_COOLDOWN_SECONDS"],
            "sample_interval_seconds": current_app.config["SAMPLE_INTERVAL_SECONDS"],
        },
    }
    return jsonify(response)


@legacy_bp.route("/history")
@login_required
def legacy_history():
    limit = clamp_int(request.args.get("limit"), 60, 10, 100)
    history = monitoring_service().get_history(limit.value)
    return jsonify({"history": history, "count": len(history)})


@legacy_bp.route("/processes")
@login_required
def legacy_processes():
    return jsonify({"processes": monitoring_service().get_top_processes(current_app.config["PROCESS_LIST_LIMIT"])})


@legacy_bp.route("/logs")
@login_required
def legacy_logs():
    entries = monitoring_service().get_logs(level=request.args.get("level"), limit=100)
    return jsonify({"entries": entries, "count": len(entries)})
