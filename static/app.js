// Simple frontend script to poll the Flask API and update the dashboard.

const REFRESH_INTERVAL_MS = 2000; // metrics + processes
const LOGS_REFRESH_INTERVAL_MS = 5000; // logs viewer

// Cache DOM elements for performance and readability.
const cpuValueEl = document.getElementById("cpu-value");
const memoryValueEl = document.getElementById("memory-value");
const diskValueEl = document.getElementById("disk-value");

const cpuBarEl = document.getElementById("cpu-bar");
const memoryBarEl = document.getElementById("memory-bar");
const diskBarEl = document.getElementById("disk-bar");

const cpuCardEl = document.getElementById("cpu-card");
const memoryCardEl = document.getElementById("memory-card");
const diskCardEl = document.getElementById("disk-card");

const cpuLevelEl = document.getElementById("cpu-level");
const memoryLevelEl = document.getElementById("memory-level");
const diskLevelEl = document.getElementById("disk-level");

const cpuPillEl = document.getElementById("cpu-pill");
const memoryPillEl = document.getElementById("memory-pill");
const diskPillEl = document.getElementById("disk-pill");

const insightSummaryEl = document.getElementById("insight-summary");
const insightRecoEl = document.getElementById("insight-reco");
const thresholdHintEl = document.getElementById("threshold-hint");

const lastUpdatedEl = document.getElementById("last-updated");
const alertsContainerEl = document.getElementById("alerts-container");
const processesBodyEl = document.getElementById("processes-body");
const logsContainerEl = document.getElementById("logs-container");
const refreshLogsBtn = document.getElementById("refresh-logs-btn");

const historyStatusEl = document.getElementById("history-status");
const cpuChartCanvas = document.getElementById("cpuChart");

let latestThresholds = { warning: null, critical: null };

function levelLabel(level) {
  if (level === "green") return "Green (Normal)";
  if (level === "yellow") return "Yellow (Warning)";
  if (level === "red") return "Red (Critical)";
  return "--";
}

function pillText(level) {
  if (level === "green") return "NORMAL";
  if (level === "yellow") return "WARNING";
  if (level === "red") return "CRITICAL";
  return "--";
}

function applyLevelClass(cardEl, level) {
  cardEl.classList.remove("level-green", "level-yellow", "level-red");
  if (level === "green") cardEl.classList.add("level-green");
  if (level === "yellow") cardEl.classList.add("level-yellow");
  if (level === "red") cardEl.classList.add("level-red");
}

function applyPill(pillEl, level) {
  if (!pillEl) return;
  pillEl.classList.remove("pill-green", "pill-yellow", "pill-red");
  if (level === "green") pillEl.classList.add("pill-green");
  if (level === "yellow") pillEl.classList.add("pill-yellow");
  if (level === "red") pillEl.classList.add("pill-red");
  pillEl.textContent = pillText(level);
}

function setMetric(cardEl, valueEl, barEl, value) {
  const safeValue = Math.max(0, Math.min(100, value || 0));
  valueEl.textContent = `${safeValue.toFixed(1)} %`;
  barEl.style.width = `${safeValue}%`;
}

function escapeHtml(str) {
  return String(str)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function renderAlerts(actions, metrics) {
  if (!actions || actions.length === 0) {
    alertsContainerEl.innerHTML = '<div class="muted-text">No alerts yet. System is healthy.</div>';
    return;
  }

  const now = new Date();
  const timestamp = now.toLocaleTimeString();

  alertsContainerEl.innerHTML = "";

  actions.forEach((msg) => {
    const div = document.createElement("div");
    div.className = "alert-item";
    div.innerHTML = `
      <div class="alert-message">${msg}</div>
      <div class="alert-timestamp">${timestamp}</div>
    `;
    alertsContainerEl.appendChild(div);
  });
}

let cpuChart = null;

function initChart() {
  if (!cpuChartCanvas || !window.Chart) return;

  const ctx = cpuChartCanvas.getContext("2d");
  cpuChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: [],
      datasets: [
        {
          label: "CPU %",
          data: [],
          tension: 0.35,
          borderWidth: 2,
          borderColor: "rgba(56, 189, 248, 0.95)",
          backgroundColor: "rgba(56, 189, 248, 0.12)",
          fill: true,
          pointRadius: 0,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 450 },
      plugins: {
        legend: { display: false },
        tooltip: { enabled: true },
      },
      scales: {
        x: {
          ticks: { color: "rgba(148, 163, 184, 0.9)", maxTicksLimit: 6 },
          grid: { color: "rgba(148, 163, 184, 0.12)" },
        },
        y: {
          suggestedMin: 0,
          suggestedMax: 100,
          ticks: { color: "rgba(148, 163, 184, 0.9)" },
          grid: { color: "rgba(148, 163, 184, 0.12)" },
        },
      },
    },
  });
}

function updateChartFromHistory(history) {
  if (!cpuChart || !history || history.length === 0) return;
  const labels = history.map((h) => {
    const d = new Date(h.timestamp);
    return d.toLocaleTimeString();
  });
  const values = history.map((h) => Number(h.metrics?.cpu || 0));
  cpuChart.data.labels = labels;
  cpuChart.data.datasets[0].data = values;
  cpuChart.update();
}

async function fetchHistory() {
  if (!cpuChart) return;
  try {
    const res = await fetch("/history?limit=60");
    if (!res.ok) throw new Error(`Failed to fetch /history: ${res.status}`);
    const data = await res.json();
    const history = data.history || [];
    updateChartFromHistory(history);
    if (historyStatusEl) historyStatusEl.textContent = `Points: ${history.length}`;
  } catch (err) {
    console.error(err);
    if (historyStatusEl) historyStatusEl.textContent = "History: error";
  }
}

async function fetchStats() {
  try {
    const res = await fetch("/stats");
    if (!res.ok) throw new Error(`Failed to fetch /stats: ${res.status}`);
    const data = await res.json();

    const { metrics, thresholds, actions, timestamp, alert_levels, explanation } = data;
    latestThresholds = thresholds || latestThresholds;

    if (thresholdHintEl && latestThresholds?.warning != null && latestThresholds?.critical != null) {
      thresholdHintEl.textContent = `Thresholds: Warning ≥ ${latestThresholds.warning}% • Critical ≥ ${latestThresholds.critical}%`;
    }

    // Update metric cards
    setMetric(cpuCardEl, cpuValueEl, cpuBarEl, metrics.cpu);
    setMetric(memoryCardEl, memoryValueEl, memoryBarEl, metrics.memory);
    setMetric(diskCardEl, diskValueEl, diskBarEl, metrics.disk);

    const cpuLevel = alert_levels?.cpu;
    const memLevel = alert_levels?.memory;
    const diskLevel = alert_levels?.disk;

    applyLevelClass(cpuCardEl, cpuLevel);
    applyLevelClass(memoryCardEl, memLevel);
    applyLevelClass(diskCardEl, diskLevel);

    if (cpuLevelEl) cpuLevelEl.textContent = `Level: ${levelLabel(cpuLevel)}`;
    if (memoryLevelEl) memoryLevelEl.textContent = `Level: ${levelLabel(memLevel)}`;
    if (diskLevelEl) diskLevelEl.textContent = `Level: ${levelLabel(diskLevel)}`;

    applyPill(cpuPillEl, cpuLevel);
    applyPill(memoryPillEl, memLevel);
    applyPill(diskPillEl, diskLevel);

    // Pulse effect for critical states
    document.body.classList.toggle(
      "has-critical",
      cpuLevel === "red" || memLevel === "red" || diskLevel === "red"
    );

    if (insightSummaryEl) insightSummaryEl.textContent = `Summary: ${explanation?.summary || "--"}`;
    if (insightRecoEl) insightRecoEl.textContent = `Recommendation: ${explanation?.recommendation || "--"}`;

    // Render any self-healing actions as alerts
    renderAlerts(actions, metrics);

    // Show last updated time
    const ts = timestamp ? new Date(timestamp) : new Date();
    lastUpdatedEl.textContent = `Last update: ${ts.toLocaleTimeString()}`;
  } catch (err) {
    console.error(err);
    lastUpdatedEl.textContent = "Last update: error talking to server";
  }
}

async function fetchProcesses() {
  try {
    const res = await fetch("/processes");
    if (!res.ok) throw new Error(`Failed to fetch /processes: ${res.status}`);
    const data = await res.json();
    const processes = data.processes || [];

    if (processes.length === 0) {
      processesBodyEl.innerHTML =
        '<tr><td colspan="4" class="muted-text">No process data available.</td></tr>';
      return;
    }

    processesBodyEl.innerHTML = "";
    processes.forEach((p) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${p.pid}</td>
        <td>${p.name || "-"}</td>
        <td>${(p.cpu_percent || 0).toFixed(1)}</td>
        <td>${(p.memory_percent || 0).toFixed(2)}</td>
      `;
      processesBodyEl.appendChild(tr);
    });
  } catch (err) {
    console.error(err);
    processesBodyEl.innerHTML =
      '<tr><td colspan="4" class="muted-text">Failed to load process data.</td></tr>';
  }
}

function classifyLogLine(line) {
  if (!line) return "log-line";
  if (line.includes("[ERROR]")) return "log-line error";
  if (line.includes("[WARNING]")) return "log-line warning";
  if (line.includes("[INFO]")) return "log-line info";
  return "log-line";
}

async function fetchLogs() {
  try {
    const res = await fetch("/logs");
    if (!res.ok) throw new Error(`Failed to fetch /logs: ${res.status}`);
    const data = await res.json();
    const entries = data.entries || [];

    if (entries.length === 0) {
      logsContainerEl.innerHTML =
        '<div class="muted-text">No log entries yet. Self-healing actions will appear here.</div>';
      return;
    }

    logsContainerEl.innerHTML = "";
    entries.forEach((e) => {
      const line = e.raw || e.message || "";
      const div = document.createElement("div");
      div.className = classifyLogLine(line);
      div.textContent = line;
      logsContainerEl.appendChild(div);
    });

    logsContainerEl.scrollTop = logsContainerEl.scrollHeight;
  } catch (err) {
    console.error(err);
    logsContainerEl.innerHTML =
      '<div class="muted-text">Failed to load logs from server.</div>';
  }
}

function startPolling() {
  // Initial fetch so the UI updates quickly on first load.
  initChart();
  fetchStats();
  fetchHistory();
  fetchProcesses();
  fetchLogs();

  setInterval(fetchStats, REFRESH_INTERVAL_MS);
  setInterval(fetchHistory, REFRESH_INTERVAL_MS);
  setInterval(fetchProcesses, REFRESH_INTERVAL_MS);
  setInterval(fetchLogs, LOGS_REFRESH_INTERVAL_MS);
}

// Hook up manual logs refresh button
if (refreshLogsBtn) {
  refreshLogsBtn.addEventListener("click", fetchLogs);
}

// Start polling once the page has loaded.
window.addEventListener("load", startPolling);

