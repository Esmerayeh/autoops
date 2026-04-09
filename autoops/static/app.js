const state = {
  autoRefresh: true,
  timeRange: 60,
  chart: null,
  validationChart: null,
  processes: [],
  processSort: { key: "cpu_percent", asc: false },
  latestActionId: null,
  refreshInFlight: false,
};

const POLL_INTERVAL_MS = 6000;
const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute("content") || "";

const refs = {
  healthScore: document.getElementById("health-score"),
  healthSummary: document.getElementById("health-summary"),
  anomalyScore: document.getElementById("anomaly-score"),
  anomalyConfidence: document.getElementById("anomaly-confidence"),
  riskScore: document.getElementById("risk-score"),
  latencyP95: document.getElementById("latency-p95"),
  mlModeBadge: document.getElementById("ml-mode-badge"),
  hostName: document.getElementById("host-name"),
  hostPlatform: document.getElementById("host-platform"),
  hostCpuCount: document.getElementById("host-cpu-count"),
  hostBootTime: document.getElementById("host-boot-time"),
  hostPid: document.getElementById("host-pid"),
  hostMlMode: document.getElementById("host-ml-mode"),
  statusEnvironment: document.getElementById("status-environment"),
  statusSampler: document.getElementById("status-sampler"),
  statusHealing: document.getElementById("status-healing"),
  statusLastAction: document.getElementById("status-last-action"),
  recommendationTitle: document.getElementById("recommendation-title"),
  recommendationReasoning: document.getElementById("recommendation-reasoning"),
  forecastChip: document.getElementById("forecast-chip"),
  causeList: document.getElementById("cause-list"),
  recommendationActions: document.getElementById("recommendation-actions"),
  alertTimeline: document.getElementById("alert-timeline"),
  actionsTimeline: document.getElementById("actions-timeline"),
  processesBody: document.getElementById("processes-body"),
  logsBody: document.getElementById("logs-body"),
  logLevelFilter: document.getElementById("log-level-filter"),
  refreshLogsBtn: document.getElementById("refresh-logs-btn"),
  processSearch: document.getElementById("process-search"),
  timeRangeSelect: document.getElementById("time-range-select"),
  autoRefreshToggle: document.getElementById("auto-refresh-toggle"),
  telemetryChart: document.getElementById("telemetry-chart"),
  telemetryEmptyState: document.getElementById("telemetry-empty-state"),
  validationChart: document.getElementById("validation-chart"),
  validationEmptyState: document.getElementById("validation-empty-state"),
  decisionBadge: document.getElementById("decision-badge"),
  decisionResult: document.getElementById("decision-result"),
  decisionConfidence: document.getElementById("decision-confidence"),
  decisionSafety: document.getElementById("decision-safety"),
  decisionAction: document.getElementById("decision-action"),
  decisionWhy: document.getElementById("decision-why"),
  autonomyModeSelect: document.getElementById("autonomy-mode-select"),
  saveAutonomyMode: document.getElementById("save-autonomy-mode"),
  autonomyActionsCount: document.getElementById("autonomy-actions-count"),
  autonomyConfidenceGate: document.getElementById("autonomy-confidence-gate"),
  autonomySafetyGate: document.getElementById("autonomy-safety-gate"),
  autonomyFeedbackRate: document.getElementById("autonomy-feedback-rate"),
  incidentList: document.getElementById("incident-list"),
  reasoningPanel: document.getElementById("reasoning-panel"),
  validationBadge: document.getElementById("validation-badge"),
  feedbackSuccessRate: document.getElementById("feedback-success-rate"),
  feedbackFalseRate: document.getElementById("feedback-false-rate"),
  feedbackRecurrenceRate: document.getElementById("feedback-recurrence-rate"),
  feedbackRecordCount: document.getElementById("feedback-record-count"),
  feedbackList: document.getElementById("feedback-list"),
  dashboardError: document.getElementById("dashboard-error"),
};

function numberOr(value, fallback = 0) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function safeArray(value) {
  return Array.isArray(value) ? value : [];
}

function setEmptyState(element, message) {
  if (!element) return;
  element.classList.add("empty-state");
  element.textContent = message;
}

function clearEmptyState(element) {
  if (!element) return;
  element.classList.remove("empty-state");
}

function showGlobalError(message) {
  if (!refs.dashboardError) return;
  refs.dashboardError.textContent = message;
  refs.dashboardError.classList.remove("hidden");
}

function clearGlobalError() {
  if (!refs.dashboardError) return;
  refs.dashboardError.textContent = "";
  refs.dashboardError.classList.add("hidden");
}

function createNode(tag, text, className) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text != null) node.textContent = text;
  return node;
}

function setChartEmptyState(element, message, visible) {
  if (!element) return;
  element.textContent = message;
  element.classList.toggle("visible", Boolean(visible));
}

function formatTimestampLabel(value) {
  if (!value) return "--";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function hasMeaningfulSeries(values) {
  return safeArray(values).some((value) => Number.isFinite(Number(value)));
}

function formatPercent(value) {
  return `${numberOr(value).toFixed(1)}%`;
}

function formatRatio(value) {
  return `${Math.round(numberOr(value) * 100)}%`;
}

function setMetric(metric, value, trend, extraLabel) {
  const valueNode = document.getElementById(`${metric}-value`);
  const trendNode = document.getElementById(`${metric}-trend`);
  const barNode = document.getElementById(`${metric}-bar`);
  const badgeNode = document.getElementById(`${metric}-anomaly`);
  if (valueNode) valueNode.textContent = extraLabel || formatPercent(value);
  if (trendNode) trendNode.textContent = `Trend: ${trend || "--"}`;
  if (barNode) barNode.style.width = `${Math.max(0, Math.min(100, numberOr(value)))}%`;
  if (badgeNode) badgeNode.textContent = numberOr(value) >= 85 ? "Critical" : numberOr(value) >= 70 ? "Warning" : "Normal";
}

function createCharts() {
  if (refs.telemetryChart && window.Chart) {
    state.chart = new Chart(refs.telemetryChart.getContext("2d"), {
      type: "line",
      data: {
        labels: [],
        datasets: [
          { label: "CPU", data: [], borderColor: "#4fd1c5", backgroundColor: "rgba(79, 209, 197, 0.1)", tension: 0.35, fill: true, pointRadius: 0 },
          { label: "Memory", data: [], borderColor: "#60a5fa", backgroundColor: "rgba(96, 165, 250, 0.08)", tension: 0.35, fill: false, pointRadius: 0 },
          { label: "Disk", data: [], borderColor: "#f59e0b", backgroundColor: "rgba(245, 158, 11, 0.08)", tension: 0.35, fill: false, pointRadius: 0 },
          { label: "Net RX", data: [], borderColor: "#c084fc", backgroundColor: "rgba(192, 132, 252, 0.08)", tension: 0.35, fill: false, pointRadius: 0, yAxisID: "y1" },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        resizeDelay: 150,
        plugins: { legend: { labels: { color: "#cfe0f6" } } },
        scales: {
          x: {
            ticks: {
              color: "#8da2bc",
              autoSkip: true,
              maxTicksLimit: 8,
              maxRotation: 0,
              minRotation: 0,
            },
            grid: { color: "rgba(255,255,255,0.05)" },
          },
          y: { ticks: { color: "#8da2bc" }, grid: { color: "rgba(255,255,255,0.05)" }, suggestedMin: 0, suggestedMax: 100 },
          y1: { position: "right", ticks: { color: "#8da2bc" }, grid: { display: false } },
        },
      },
    });
  }

  if (refs.validationChart && window.Chart) {
    state.validationChart = new Chart(refs.validationChart.getContext("2d"), {
      type: "bar",
      data: {
        labels: ["Before", "After"],
        datasets: [
          { label: "CPU", data: [0, 0], backgroundColor: ["rgba(79, 209, 197, 0.7)", "rgba(79, 209, 197, 0.35)"] },
          { label: "Memory", data: [0, 0], backgroundColor: ["rgba(96, 165, 250, 0.7)", "rgba(96, 165, 250, 0.35)"] },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        resizeDelay: 150,
        plugins: { legend: { labels: { color: "#cfe0f6" } } },
        scales: {
          x: {
            ticks: {
              color: "#8da2bc",
              autoSkip: false,
              maxRotation: 0,
              minRotation: 0,
            },
            grid: { color: "rgba(255,255,255,0.05)" },
          },
          y: { ticks: { color: "#8da2bc" }, grid: { color: "rgba(255,255,255,0.05)" }, suggestedMin: 0, suggestedMax: 100 },
        },
      },
    });
  }
}

async function api(path, options = {}) {
  const headers = {
    Accept: "application/json",
    ...options.headers,
  };
  if (options.body && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }
  if (csrfToken && !headers["X-CSRFToken"]) {
    headers["X-CSRFToken"] = csrfToken;
  }
  const response = await fetch(path, {
    credentials: "same-origin",
    headers,
    ...options,
  });
  const text = await response.text();
  let payload = {};
  try {
    payload = text ? JSON.parse(text) : {};
  } catch {
    const error = new Error(`Invalid JSON response for ${path}`);
    error.status = response.status;
    throw error;
  }
  if (!response.ok) {
    const error = new Error(payload?.error?.message || `Request failed for ${path}: ${response.status}`);
    error.status = response.status;
    throw error;
  }
  return payload;
}

function renderPills(container, items, className) {
  container.replaceChildren();
  if (!items || items.length === 0) {
    container.appendChild(createNode("span", "No items", className));
    return;
  }
  items.forEach((item) => {
    container.appendChild(createNode("span", item, className));
  });
}

function renderTimeline(container, items, mode) {
  if (!items || items.length === 0) {
    setEmptyState(container, mode === "alerts" ? "No active alerts yet." : "No healing actions recorded yet.");
    return;
  }
  clearEmptyState(container);
  container.replaceChildren();
  items.forEach((item) => {
    const severity = item.severity || item.status || "info";
    const el = createNode("article", null, "timeline-item");
    el.appendChild(createNode("span", severity, `timeline-severity severity-${severity}`));
    el.appendChild(createNode("strong", item.title || item.policy_name || item.summary || "--"));
    el.appendChild(createNode("div", item.message || item.summary || ""));
    el.appendChild(createNode("div", item.recommendation || item.target || item.validation_status || "", "timeline-meta"));
    container.appendChild(el);
  });
}

function renderProcesses() {
  const search = (refs.processSearch?.value || "").toLowerCase();
  const items = state.processes
    .filter((item) => !search || String(item.name || "").toLowerCase().includes(search))
    .sort((a, b) => {
      const key = state.processSort.key;
      const av = a[key] ?? "";
      const bv = b[key] ?? "";
      if (typeof av === "number" && typeof bv === "number") return state.processSort.asc ? av - bv : bv - av;
      return state.processSort.asc ? String(av).localeCompare(String(bv)) : String(bv).localeCompare(String(av));
    });

  refs.processesBody.replaceChildren();
  if (!items.length) {
    const tr = document.createElement("tr");
    const td = createNode("td", "No matching processes.");
    td.colSpan = 5;
    tr.appendChild(td);
    refs.processesBody.appendChild(tr);
    return;
  }
  items.forEach((item) => {
    const tr = document.createElement("tr");
    tr.appendChild(createNode("td", String(item.pid ?? "-")));
    tr.appendChild(createNode("td", item.name || "-"));
    tr.appendChild(createNode("td", numberOr(item.cpu_percent).toFixed(1)));
    tr.appendChild(createNode("td", numberOr(item.memory_percent).toFixed(2)));
    tr.appendChild(createNode("td", `${item.status || "-"} / ${numberOr(item.anomaly_score).toFixed(0)}`));
    refs.processesBody.appendChild(tr);
  });
}

function renderIncidentList(incidents, timeline) {
  if (!incidents.length && !timeline.length) {
    setEmptyState(refs.incidentList, "No active incidents.");
    return;
  }
  clearEmptyState(refs.incidentList);
  refs.incidentList.replaceChildren();
  incidents.forEach((incident) => {
    const el = createNode("article", null, "timeline-item");
    el.appendChild(createNode("span", incident.severity, `timeline-severity severity-${incident.severity}`));
    el.appendChild(createNode("strong", `#${incident.id} ${incident.title}`));
    el.appendChild(createNode("div", incident.summary || ""));
    el.appendChild(createNode("div", `${incident.status} | root cause: ${incident.root_cause_hypothesis || "pending"}`, "timeline-meta"));
    refs.incidentList.appendChild(el);
  });
  timeline.slice(0, 3).forEach((event) => {
    const el = createNode("article", null, "timeline-item");
    el.appendChild(createNode("span", event.event_type.replaceAll("_", " "), "timeline-severity severity-info"));
    el.appendChild(createNode("strong", `Incident ${event.incident_id}`));
    el.appendChild(createNode("div", event.message || ""));
    el.appendChild(createNode("div", new Date(event.timestamp).toLocaleString(), "timeline-meta"));
    refs.incidentList.appendChild(el);
  });
}

function renderReasoning(decisions, feedbackSummary) {
  if (!decisions.length) {
    setEmptyState(refs.reasoningPanel, "Waiting for the next decision cycle.");
    return;
  }
  const latest = decisions[decisions.length - 1];
  clearEmptyState(refs.reasoningPanel);
  refs.reasoningPanel.replaceChildren();
  const first = createNode("div", null, "reasoning-item");
  first.appendChild(createNode("strong", "Anomaly detected"));
  first.appendChild(document.createTextNode(`${latest.risk_level} risk with decision "${latest.decision}".`));
  refs.reasoningPanel.appendChild(first);
  const second = createNode("div", null, "reasoning-item");
  second.appendChild(createNode("strong", "Decision made"));
  second.appendChild(document.createTextNode(latest.why || "No decision reasoning available."));
  refs.reasoningPanel.appendChild(second);
  const third = createNode("div", null, "reasoning-item");
  third.appendChild(createNode("strong", "Feedback learning"));
  third.appendChild(document.createTextNode(`Success ${formatRatio(feedbackSummary.action_success_rate)}, false positives ${formatRatio(feedbackSummary.false_positive_rate)}.`));
  refs.reasoningPanel.appendChild(third);
}

function updateValidationChart(validation) {
  if (!state.validationChart) return;
  if (!validation) {
    refs.validationBadge.textContent = "No validation yet";
    state.validationChart.data.datasets[0].data = [0, 0];
    state.validationChart.data.datasets[1].data = [0, 0];
    state.validationChart.update();
    setChartEmptyState(refs.validationEmptyState, "No validation data yet.", true);
    return;
  }
  refs.validationBadge.textContent = `Validation ${validation.validation_status || "pending"}`;
  const before = validation.before || {};
  const after = validation.after || {};
  const cpuSeries = [numberOr(before.cpu), numberOr(after.cpu)];
  const memorySeries = [numberOr(before.memory), numberOr(after.memory)];
  state.validationChart.data.datasets[0].data = cpuSeries;
  state.validationChart.data.datasets[1].data = memorySeries;
  state.validationChart.update();
  setChartEmptyState(
    refs.validationEmptyState,
    "Validation data is present but does not yet contain meaningful before/after measurements.",
    !hasMeaningfulSeries(cpuSeries) && !hasMeaningfulSeries(memorySeries),
  );
}

async function loadStats() {
  const payload = await api("/api/v1/stats");
  const summary = payload.data || {};
  const snapshot = summary.snapshot || {};
  const analysis = summary.analysis || {};
  const metrics = snapshot.metrics || {};
  const host = snapshot.host || {};
  const recommendation = analysis.recommendation || {};
  const anomaly = analysis.anomaly || {};
  const risk = analysis.risk || {};
  const forecast = analysis.forecast || {};
  const decision = analysis.decision || {};
  const trend = analysis.trend || {};
  const statusBar = summary.status_bar || {};

  refs.healthScore.textContent = numberOr(summary.health_score).toFixed(1);
  refs.healthSummary.textContent = recommendation.summary || "Telemetry is online. Waiting for enough signal to produce a stronger diagnosis.";
  refs.anomalyScore.textContent = numberOr(anomaly.score).toFixed(3);
  refs.anomalyConfidence.textContent = formatRatio(anomaly.confidence);
  refs.riskScore.textContent = `${numberOr(risk.score).toFixed(1)} (${risk.label || "low"})`;
  refs.latencyP95.textContent = `${numberOr(metrics.api_latency_ms_p95).toFixed(1)} ms`;
  refs.mlModeBadge.textContent = `Mode: ${(analysis.mode || "rules").toUpperCase()}`;
  refs.hostName.textContent = host.hostname || "localhost";
  refs.hostPlatform.textContent = host.platform || "--";
  refs.hostCpuCount.textContent = `${host.physical_cpu_count || host.cpu_count || "--"}/${host.cpu_count || "--"}`;
  refs.hostBootTime.textContent = host.boot_time ? new Date(host.boot_time).toLocaleString() : "--";
  refs.hostPid.textContent = host.python_pid || "--";
  refs.hostMlMode.textContent = host.ml_mode || analysis.mode || "--";
  refs.statusEnvironment.textContent = statusBar.environment || "--";
  refs.statusSampler.textContent = statusBar.sampler_state || "--";
  refs.statusHealing.textContent = `${statusBar.self_healing_mode || "--"} / ${statusBar.autonomy_mode || "--"}`;
  refs.statusLastAction.textContent = statusBar.last_action || "No healing actions yet";
  refs.recommendationTitle.textContent = recommendation.summary || "Awaiting analysis";
  refs.recommendationReasoning.textContent = recommendation.reasoning || "The analytics engine is collecting more context before making a recommendation.";
  refs.forecastChip.textContent = `CPU forecast ${numberOr(forecast.cpu?.next_5m_estimate).toFixed(1)}%`;
  renderPills(refs.causeList, safeArray(recommendation.probable_causes), "cause-pill");
  renderPills(refs.recommendationActions, safeArray(recommendation.next_actions), "action-pill");

  refs.decisionBadge.textContent = decision.decision || "decision pending";
  refs.decisionResult.textContent = decision.decision || "--";
  refs.decisionConfidence.textContent = decision.confidence != null ? formatRatio(decision.confidence) : "--";
  refs.decisionSafety.textContent = decision.safety_score != null ? formatRatio(decision.safety_score) : "--";
  refs.decisionAction.textContent = decision.recommended_action_type || "none";
  refs.decisionWhy.textContent = decision.why || "No decision reasoning yet.";

  setMetric("cpu", metrics.cpu, trend.cpu);
  setMetric("memory", metrics.memory, trend.memory);
  setMetric("disk", metrics.disk, trend.disk);
  const netRecvKb = numberOr(metrics.network?.bytes_recv_per_sec) / 1024;
  setMetric("network", netRecvKb, "live", `${netRecvKb.toFixed(1)} KB/s`);
}

async function loadHistory() {
  const payload = await api(`/api/v1/history?limit=${state.timeRange}`);
  const history = safeArray(payload.data?.history);
  if (!state.chart) return;
  const labels = history.map((item) => formatTimestampLabel(item.timestamp));
  const cpuSeries = history.map((item) => numberOr(item.metrics?.cpu, NaN));
  const memorySeries = history.map((item) => numberOr(item.metrics?.memory, NaN));
  const diskSeries = history.map((item) => numberOr(item.metrics?.disk, NaN));
  const networkSeries = history.map((item) => {
    const raw = item.metrics?.network?.bytes_recv_per_sec;
    const parsed = Number(raw);
    return Number.isFinite(parsed) ? parsed / 1024 : NaN;
  });
  state.chart.data.labels = labels;
  state.chart.data.datasets[0].data = cpuSeries;
  state.chart.data.datasets[1].data = memorySeries;
  state.chart.data.datasets[2].data = diskSeries;
  state.chart.data.datasets[3].data = networkSeries;
  state.chart.update();
  const sparseHistory = history.length < 2;
  const noSeries =
    !hasMeaningfulSeries(cpuSeries) &&
    !hasMeaningfulSeries(memorySeries) &&
    !hasMeaningfulSeries(diskSeries) &&
    !hasMeaningfulSeries(networkSeries);
  setChartEmptyState(
    refs.telemetryEmptyState,
    sparseHistory
      ? "Telemetry history still building. Wait for a few more sampling intervals."
      : "History loaded, but the plotted series are empty or malformed.",
    sparseHistory || noSeries,
  );
}

async function loadAlerts() {
  const payload = await api("/api/v1/alerts?limit=8");
  renderTimeline(refs.alertTimeline, payload.data.alerts || [], "alerts");
}

async function loadActions() {
  const payload = await api("/api/v1/actions?limit=8");
  const actions = safeArray(payload.data?.actions);
  renderTimeline(refs.actionsTimeline, actions, "actions");
  state.latestActionId = actions[0]?.id || null;
}

async function loadProcesses() {
  const payload = await api("/api/v1/processes?limit=15");
  state.processes = safeArray(payload.data?.processes);
  renderProcesses();
}

async function loadLogs() {
  const level = refs.logLevelFilter?.value || "";
  const payload = await api(`/api/v1/logs?limit=80${level ? `&level=${encodeURIComponent(level)}` : ""}`);
  const entries = safeArray(payload.data?.entries);
  refs.logsBody.replaceChildren();
  if (!entries.length) {
    const tr = document.createElement("tr");
    const td = createNode("td", "No logs available.");
    td.colSpan = 3;
    tr.appendChild(td);
    refs.logsBody.appendChild(tr);
    return;
  }
  entries.forEach((entry) => {
    const tr = document.createElement("tr");
    tr.appendChild(createNode("td", entry.timestamp ? new Date(entry.timestamp).toLocaleString() : "-"));
    tr.appendChild(createNode("td", entry.level || "-"));
    tr.appendChild(createNode("td", entry.message || "-"));
    refs.logsBody.appendChild(tr);
  });
}

async function loadIncidents() {
  const payload = await api("/api/v1/incidents?limit=6");
  renderIncidentList(safeArray(payload.data?.incidents), safeArray(payload.data?.timeline));
}

async function loadDecisions() {
  const decisionsPayload = await api("/api/v1/decisions?limit=8");
  const feedbackPayload = await api("/api/v1/feedback?limit=6");
  const decisions = safeArray(decisionsPayload.data?.decisions);
  const feedbackSummary = feedbackPayload.data?.summary || {};
  renderReasoning(decisions, feedbackSummary);
}

async function loadAutonomyStatus() {
  const payload = await api("/api/v1/autonomy/status");
  const autonomy = payload.data?.autonomy || {};
  if (document.activeElement !== refs.autonomyModeSelect) {
    refs.autonomyModeSelect.value = autonomy.mode || "assisted";
  }
  refs.autonomyActionsCount.textContent = numberOr(autonomy.recent_autonomous_actions).toFixed(0);
  refs.autonomyConfidenceGate.textContent = formatRatio(autonomy.decision_confidence_threshold);
  refs.autonomySafetyGate.textContent = formatRatio(autonomy.decision_safety_threshold);
  refs.autonomyFeedbackRate.textContent = formatRatio(autonomy.feedback_summary?.action_success_rate);
}

async function loadFeedback() {
  const payload = await api("/api/v1/feedback?limit=5");
  const summary = payload.data?.summary || {};
  const records = safeArray(payload.data?.records);
  refs.feedbackSuccessRate.textContent = formatRatio(summary.action_success_rate);
  refs.feedbackFalseRate.textContent = formatRatio(summary.false_positive_rate);
  refs.feedbackRecurrenceRate.textContent = formatRatio(summary.recurrence_rate);
  refs.feedbackRecordCount.textContent = numberOr(summary.total_records).toFixed(0);
  refs.feedbackList.replaceChildren();
  if (!records.length) {
    setEmptyState(refs.feedbackList, "No feedback records yet.");
    return;
  }
  clearEmptyState(refs.feedbackList);
  records.forEach((record) => {
    const label = record.action_effective ? "confidence increased" : "confidence decreased";
    const el = createNode("article", null, "timeline-item");
    el.appendChild(createNode("span", label, "timeline-severity severity-info"));
    el.appendChild(createNode("strong", `${record.metric_name || "system"} / ${record.process_name || "general"}`));
    el.appendChild(createNode("div", record.notes || "Feedback sample captured."));
    el.appendChild(createNode("div", `${record.action_effective ? "validation passed" : "validation failed"} | ${new Date(record.created_at).toLocaleString()}`, "timeline-meta"));
    refs.feedbackList.appendChild(el);
  });
}

async function loadValidation() {
  if (!state.latestActionId) {
    updateValidationChart(null);
    return;
  }
  try {
    const payload = await api(`/api/v1/actions/${state.latestActionId}/validation`);
    updateValidationChart(payload.data.validation);
  } catch (error) {
    if (error.status === 404) {
      refs.validationBadge.textContent = "Validation pending";
      setChartEmptyState(refs.validationEmptyState, "No validation data yet.", true);
    } else if (error.status === 401 || error.status === 403) {
      refs.validationBadge.textContent = "Validation unauthorized";
      setChartEmptyState(refs.validationEmptyState, "Validation could not be loaded because access was denied.", true);
    } else {
      refs.validationBadge.textContent = "Validation unavailable";
      setChartEmptyState(refs.validationEmptyState, "Validation data is temporarily unavailable.", true);
    }
  }
}

async function saveAutonomyMode() {
  const mode = refs.autonomyModeSelect.value;
  await api("/api/v1/autonomy/mode", {
    method: "POST",
    body: JSON.stringify({ mode }),
  });
  await loadAutonomyStatus();
}

async function refresh() {
  if (state.refreshInFlight) return;
  state.refreshInFlight = true;
  clearGlobalError();
  const results = await Promise.allSettled([
      loadStats(),
      loadHistory(),
      loadAlerts(),
      loadActions(),
      loadProcesses(),
      loadLogs(),
      loadIncidents(),
      loadDecisions(),
      loadAutonomyStatus(),
      loadFeedback(),
    ]);
  const failures = [];
  results.forEach((result) => {
    if (result.status === "rejected") {
      console.error(result.reason);
      failures.push(result.reason?.message || "Dashboard refresh failed.");
    }
  });
  try {
    await loadValidation();
  } catch (error) {
    console.error(error);
    failures.push(error?.message || "Validation data failed to load.");
  } finally {
    if (failures.length) {
      showGlobalError(`Some live panels could not refresh. ${failures[0]}`);
    }
    state.refreshInFlight = false;
  }
}

function bindEvents() {
  refs.refreshLogsBtn?.addEventListener("click", loadLogs);
  refs.logLevelFilter?.addEventListener("change", loadLogs);
  refs.processSearch?.addEventListener("input", renderProcesses);
  refs.timeRangeSelect?.addEventListener("change", (event) => {
    state.timeRange = Number(event.target.value || 60);
    loadHistory();
  });
  refs.autoRefreshToggle?.addEventListener("change", (event) => {
    state.autoRefresh = Boolean(event.target.checked);
  });
  refs.saveAutonomyMode?.addEventListener("click", () => {
    saveAutonomyMode().catch((error) => console.error(error));
  });
  document.querySelectorAll("th[data-sort]").forEach((th) => {
    th.addEventListener("click", () => {
      const key = th.getAttribute("data-sort");
      if (!key) return;
      if (state.processSort.key === key) state.processSort.asc = !state.processSort.asc;
      else state.processSort = { key, asc: false };
      renderProcesses();
    });
  });
}

window.addEventListener("load", () => {
  createCharts();
  bindEvents();
  refresh();
  setInterval(() => {
    if (state.autoRefresh) refresh();
  }, POLL_INTERVAL_MS);
});
