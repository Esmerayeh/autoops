const state = {
  autoRefresh: true,
  timeRange: 60,
  chart: null,
  validationChart: null,
  processes: [],
  processSort: { key: "cpu_percent", asc: false },
  latestActionId: null,
};

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
  validationChart: document.getElementById("validation-chart"),
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
};

function formatPercent(value) {
  return `${Number(value || 0).toFixed(1)}%`;
}

function formatRatio(value) {
  return `${Math.round(Number(value || 0) * 100)}%`;
}

function setMetric(metric, value, trend, extraLabel) {
  const valueNode = document.getElementById(`${metric}-value`);
  const trendNode = document.getElementById(`${metric}-trend`);
  const barNode = document.getElementById(`${metric}-bar`);
  const badgeNode = document.getElementById(`${metric}-anomaly`);
  if (valueNode) valueNode.textContent = extraLabel || formatPercent(value);
  if (trendNode) trendNode.textContent = `Trend: ${trend || "--"}`;
  if (barNode) barNode.style.width = `${Math.max(0, Math.min(100, Number(value || 0)))}%`;
  if (badgeNode) badgeNode.textContent = Number(value || 0) >= 85 ? "Critical" : Number(value || 0) >= 70 ? "Warning" : "Normal";
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
        plugins: { legend: { labels: { color: "#cfe0f6" } } },
        scales: {
          x: { ticks: { color: "#8da2bc" }, grid: { color: "rgba(255,255,255,0.05)" } },
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
        plugins: { legend: { labels: { color: "#cfe0f6" } } },
        scales: {
          x: { ticks: { color: "#8da2bc" }, grid: { color: "rgba(255,255,255,0.05)" } },
          y: { ticks: { color: "#8da2bc" }, grid: { color: "rgba(255,255,255,0.05)" }, suggestedMin: 0, suggestedMax: 100 },
        },
      },
    });
  }
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    ...options,
  });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload?.error?.message || `Request failed for ${path}: ${response.status}`);
  return payload;
}

function renderPills(container, items, className) {
  container.innerHTML = "";
  if (!items || items.length === 0) {
    container.innerHTML = `<span class="${className}">No items</span>`;
    return;
  }
  items.forEach((item) => {
    const span = document.createElement("span");
    span.className = className;
    span.textContent = item;
    container.appendChild(span);
  });
}

function renderTimeline(container, items, mode) {
  if (!items || items.length === 0) {
    container.classList.add("empty-state");
    container.textContent = mode === "alerts" ? "No active alerts yet." : "No healing actions recorded yet.";
    return;
  }
  container.classList.remove("empty-state");
  container.innerHTML = "";
  items.forEach((item) => {
    const severity = item.severity || item.status || "info";
    const el = document.createElement("article");
    el.className = "timeline-item";
    el.innerHTML = `
      <span class="timeline-severity severity-${severity}">${severity}</span>
      <strong>${item.title || item.policy_name || item.summary}</strong>
      <div>${item.message || item.summary || ""}</div>
      <div class="timeline-meta">${item.recommendation || item.target || ""}</div>
    `;
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

  refs.processesBody.innerHTML = "";
  if (!items.length) {
    refs.processesBody.innerHTML = '<tr><td colspan="5">No matching processes.</td></tr>';
    return;
  }
  items.forEach((item) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${item.pid}</td>
      <td>${item.name || "-"}</td>
      <td>${Number(item.cpu_percent || 0).toFixed(1)}</td>
      <td>${Number(item.memory_percent || 0).toFixed(2)}</td>
      <td>${item.status || "-"} / ${Number(item.anomaly_score || 0).toFixed(0)}</td>
    `;
    refs.processesBody.appendChild(tr);
  });
}

function renderIncidentList(incidents, timeline) {
  if (!incidents.length && !timeline.length) {
    refs.incidentList.classList.add("empty-state");
    refs.incidentList.textContent = "No active incidents.";
    return;
  }
  refs.incidentList.classList.remove("empty-state");
  refs.incidentList.innerHTML = "";
  incidents.forEach((incident) => {
    const el = document.createElement("article");
    el.className = "timeline-item";
    el.innerHTML = `
      <span class="timeline-severity severity-${incident.severity}">${incident.severity}</span>
      <strong>#${incident.id} ${incident.title}</strong>
      <div>${incident.summary}</div>
      <div class="timeline-meta">${incident.status} · root cause: ${incident.root_cause_hypothesis || "pending"}</div>
    `;
    refs.incidentList.appendChild(el);
  });
  timeline.slice(0, 3).forEach((event) => {
    const el = document.createElement("article");
    el.className = "timeline-item";
    el.innerHTML = `
      <span class="timeline-severity severity-info">${event.event_type.replaceAll("_", " ")}</span>
      <strong>Incident ${event.incident_id}</strong>
      <div>${event.message}</div>
      <div class="timeline-meta">${new Date(event.timestamp).toLocaleString()}</div>
    `;
    refs.incidentList.appendChild(el);
  });
}

function renderReasoning(decisions, feedbackSummary) {
  if (!decisions.length) {
    refs.reasoningPanel.classList.add("empty-state");
    refs.reasoningPanel.textContent = "Waiting for the next decision cycle.";
    return;
  }
  const latest = decisions[decisions.length - 1];
  refs.reasoningPanel.classList.remove("empty-state");
  refs.reasoningPanel.innerHTML = `
    <div class="reasoning-item"><strong>Anomaly detected</strong>${latest.risk_level} risk with decision "${latest.decision}".</div>
    <div class="reasoning-item"><strong>Decision made</strong>${latest.why}</div>
    <div class="reasoning-item"><strong>Feedback learning</strong>Success ${formatRatio(feedbackSummary.action_success_rate)}, false positives ${formatRatio(feedbackSummary.false_positive_rate)}.</div>
  `;
}

function updateValidationChart(validation) {
  if (!validation || !state.validationChart) return;
  refs.validationBadge.textContent = `validation ${validation.validation_status}`;
  state.validationChart.data.datasets[0].data = [validation.before.cpu || 0, validation.after.cpu || 0];
  state.validationChart.data.datasets[1].data = [validation.before.memory || 0, validation.after.memory || 0];
  state.validationChart.update();
}

async function loadStats() {
  const payload = await api("/api/v1/stats");
  const summary = payload.data;
  const snapshot = summary.snapshot;
  const analysis = summary.analysis;
  const metrics = snapshot.metrics;
  const host = snapshot.host;

  refs.healthScore.textContent = summary.health_score;
  refs.healthSummary.textContent = analysis.recommendation.summary;
  refs.anomalyScore.textContent = analysis.anomaly.score;
  refs.anomalyConfidence.textContent = formatRatio(analysis.anomaly.confidence || 0);
  refs.riskScore.textContent = `${analysis.risk.score} (${analysis.risk.label})`;
  refs.latencyP95.textContent = `${metrics.api_latency_ms_p95.toFixed(1)} ms`;
  refs.mlModeBadge.textContent = `Mode: ${analysis.mode.toUpperCase()}`;
  refs.hostName.textContent = host.hostname;
  refs.hostPlatform.textContent = host.platform;
  refs.hostCpuCount.textContent = `${host.physical_cpu_count || host.cpu_count}/${host.cpu_count}`;
  refs.hostBootTime.textContent = new Date(host.boot_time).toLocaleString();
  refs.hostPid.textContent = host.python_pid;
  refs.hostMlMode.textContent = host.ml_mode;
  refs.statusEnvironment.textContent = summary.status_bar.environment;
  refs.statusSampler.textContent = summary.status_bar.sampler_state;
  refs.statusHealing.textContent = `${summary.status_bar.self_healing_mode} / ${summary.status_bar.autonomy_mode}`;
  refs.statusLastAction.textContent = summary.status_bar.last_action;
  refs.recommendationTitle.textContent = analysis.recommendation.summary;
  refs.recommendationReasoning.textContent = analysis.recommendation.reasoning;
  refs.forecastChip.textContent = `CPU forecast ${analysis.forecast.cpu.next_5m_estimate}%`;
  renderPills(refs.causeList, analysis.recommendation.probable_causes, "cause-pill");
  renderPills(refs.recommendationActions, analysis.recommendation.next_actions, "action-pill");

  const decision = analysis.decision || {};
  refs.decisionBadge.textContent = decision.decision || "decision pending";
  refs.decisionResult.textContent = decision.decision || "--";
  refs.decisionConfidence.textContent = decision.confidence != null ? formatRatio(decision.confidence) : "--";
  refs.decisionSafety.textContent = decision.safety_score != null ? formatRatio(decision.safety_score) : "--";
  refs.decisionAction.textContent = decision.recommended_action_type || "none";
  refs.decisionWhy.textContent = decision.why || "No decision reasoning yet.";

  setMetric("cpu", metrics.cpu, analysis.trend.cpu);
  setMetric("memory", metrics.memory, analysis.trend.memory);
  setMetric("disk", metrics.disk, analysis.trend.disk);
  setMetric("network", metrics.network.bytes_recv_per_sec / 1024, "live", `${(metrics.network.bytes_recv_per_sec / 1024).toFixed(1)} KB/s`);
}

async function loadHistory() {
  const payload = await api(`/api/v1/history?limit=${state.timeRange}`);
  const history = payload.data.history || [];
  if (!state.chart) return;
  state.chart.data.labels = history.map((item) => new Date(item.timestamp).toLocaleTimeString());
  state.chart.data.datasets[0].data = history.map((item) => item.metrics.cpu);
  state.chart.data.datasets[1].data = history.map((item) => item.metrics.memory);
  state.chart.data.datasets[2].data = history.map((item) => item.metrics.disk);
  state.chart.data.datasets[3].data = history.map((item) => Number(item.metrics.network?.bytes_recv_per_sec || 0) / 1024);
  state.chart.update();
}

async function loadAlerts() {
  const payload = await api("/api/v1/alerts?limit=8");
  renderTimeline(refs.alertTimeline, payload.data.alerts || [], "alerts");
}

async function loadActions() {
  const payload = await api("/api/v1/actions?limit=8");
  const actions = payload.data.actions || [];
  renderTimeline(refs.actionsTimeline, actions, "actions");
  state.latestActionId = actions[0]?.id || null;
}

async function loadProcesses() {
  const payload = await api("/api/v1/processes?limit=15");
  state.processes = payload.data.processes || [];
  renderProcesses();
}

async function loadLogs() {
  const level = refs.logLevelFilter?.value || "";
  const payload = await api(`/api/v1/logs?limit=80${level ? `&level=${encodeURIComponent(level)}` : ""}`);
  const entries = payload.data.entries || [];
  refs.logsBody.innerHTML = "";
  if (!entries.length) {
    refs.logsBody.innerHTML = '<tr><td colspan="3">No logs available.</td></tr>';
    return;
  }
  entries.forEach((entry) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${entry.timestamp ? new Date(entry.timestamp).toLocaleString() : "-"}</td>
      <td>${entry.level || "-"}</td>
      <td>${entry.message || "-"}</td>
    `;
    refs.logsBody.appendChild(tr);
  });
}

async function loadIncidents() {
  const payload = await api("/api/v1/incidents?limit=6");
  renderIncidentList(payload.data.incidents || [], payload.data.timeline || []);
}

async function loadDecisions() {
  const decisionsPayload = await api("/api/v1/decisions?limit=8");
  const feedbackPayload = await api("/api/v1/feedback?limit=6");
  const decisions = decisionsPayload.data.decisions || [];
  const feedbackSummary = feedbackPayload.data.summary || {};
  renderReasoning(decisions, feedbackSummary);
}

async function loadAutonomyStatus() {
  const payload = await api("/api/v1/autonomy/status");
  const autonomy = payload.data.autonomy;
  refs.autonomyModeSelect.value = autonomy.mode;
  refs.autonomyActionsCount.textContent = autonomy.recent_autonomous_actions;
  refs.autonomyConfidenceGate.textContent = formatRatio(autonomy.decision_confidence_threshold);
  refs.autonomySafetyGate.textContent = formatRatio(autonomy.decision_safety_threshold);
  refs.autonomyFeedbackRate.textContent = formatRatio(autonomy.feedback_summary.action_success_rate);
}

async function loadFeedback() {
  const payload = await api("/api/v1/feedback?limit=5");
  const summary = payload.data.summary;
  const records = payload.data.records || [];
  refs.feedbackSuccessRate.textContent = formatRatio(summary.action_success_rate);
  refs.feedbackFalseRate.textContent = formatRatio(summary.false_positive_rate);
  refs.feedbackRecurrenceRate.textContent = formatRatio(summary.recurrence_rate);
  refs.feedbackRecordCount.textContent = summary.total_records;
  refs.feedbackList.innerHTML = "";
  if (!records.length) {
    refs.feedbackList.classList.add("empty-state");
    refs.feedbackList.textContent = "No feedback records yet.";
    return;
  }
  refs.feedbackList.classList.remove("empty-state");
  records.forEach((record) => {
    const label = record.action_effective ? "confidence increased" : "confidence decreased";
    const el = document.createElement("article");
    el.className = "timeline-item";
    el.innerHTML = `
      <span class="timeline-severity severity-info">${label}</span>
      <strong>${record.metric_name || "system"} / ${record.process_name || "general"}</strong>
      <div>${record.notes || "Feedback sample captured."}</div>
      <div class="timeline-meta">${record.action_effective ? "validation passed" : "validation failed"} · ${new Date(record.created_at).toLocaleString()}</div>
    `;
    refs.feedbackList.appendChild(el);
  });
}

async function loadValidation() {
  if (!state.latestActionId) return;
  try {
    const payload = await api(`/api/v1/actions/${state.latestActionId}/validation`);
    updateValidationChart(payload.data.validation);
  } catch {
    refs.validationBadge.textContent = "Validation pending";
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
  try {
    await Promise.all([
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
    await loadValidation();
  } catch (error) {
    console.error(error);
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
  }, 4000);
});
