const selectors = {
  nodeCount: document.getElementById("node-count"),
  agentCount: document.getElementById("agent-count"),
  incidentCount: document.getElementById("incident-count"),
  actionCount: document.getElementById("action-count"),
  fleetTable: document.getElementById("fleet-table"),
  incidentList: document.getElementById("incident-list"),
  policyList: document.getElementById("policy-list"),
  actionList: document.getElementById("action-list"),
  auditList: document.getElementById("audit-list"),
  globalError: document.getElementById("global-error"),
  refreshBtn: document.getElementById("refresh-btn"),
  loginForm: document.getElementById("login-form"),
  emailInput: document.getElementById("email-input"),
  passwordInput: document.getElementById("password-input"),
  loginStatus: document.getElementById("login-status"),
};

function getToken() {
  return window.localStorage.getItem("controlPlaneToken") || "";
}

function setToken(token) {
  window.localStorage.setItem("controlPlaneToken", token);
}

function clearError() {
  selectors.globalError.textContent = "";
  selectors.globalError.classList.add("hidden");
}

function showError(message) {
  selectors.globalError.textContent = message;
  selectors.globalError.classList.remove("hidden");
}

function badge(status) {
  const span = document.createElement("span");
  const normalized = String(status || "unknown").toLowerCase();
  const tone =
    normalized === "healthy" || normalized === "online" || normalized === "completed"
      ? "good"
      : normalized === "open" || normalized === "critical" || normalized === "failed"
        ? "bad"
        : "warn";
  span.className = `badge ${tone}`;
  span.textContent = status;
  return span;
}

async function fetchJson(url) {
  const response = await fetch(url, {
    credentials: "same-origin",
    headers: getToken() ? { Authorization: `Bearer ${getToken()}` } : {},
  });
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
  return response.json();
}

async function login(event) {
  event.preventDefault();
  clearError();
  selectors.loginStatus.textContent = "Signing in...";
  try {
    const response = await fetch("/api/v1/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: selectors.emailInput.value,
        password: selectors.passwordInput.value,
      }),
    });
    if (!response.ok) {
      throw new Error(`${response.status} ${response.statusText}`);
    }
    const payload = await response.json();
    setToken(payload.access_token);
    selectors.loginStatus.textContent = "Authenticated. Loading fleet view...";
    await refreshDashboard();
  } catch (error) {
    selectors.loginStatus.textContent = "Login failed.";
    showError(`Login failed: ${error.message}`);
  }
}

function renderFleet(data) {
  selectors.nodeCount.textContent = String(data.node_count ?? 0);
  selectors.agentCount.textContent = String(data.agent_count ?? 0);
  if (!data.nodes?.length) {
    selectors.fleetTable.textContent = "No nodes registered yet.";
    selectors.fleetTable.className = "table-wrap empty-state";
    return;
  }

  const table = document.createElement("table");
  table.className = "table";
  const thead = document.createElement("thead");
  thead.innerHTML = "<tr><th>Hostname</th><th>Environment</th><th>Region</th><th>Status</th></tr>";
  const tbody = document.createElement("tbody");
  data.nodes.forEach((node) => {
    const tr = document.createElement("tr");
    ["hostname", "environment", "region"].forEach((key) => {
      const td = document.createElement("td");
      td.textContent = node[key] ?? "-";
      tr.appendChild(td);
    });
    const statusTd = document.createElement("td");
    statusTd.appendChild(badge(node.status ?? "unknown"));
    tr.appendChild(statusTd);
    tbody.appendChild(tr);
  });
  table.replaceChildren(thead, tbody);
  selectors.fleetTable.className = "table-wrap";
  selectors.fleetTable.replaceChildren(table);
}

function renderList(target, items, formatter, emptyText) {
  if (!items?.length) {
    target.textContent = emptyText;
    target.className = "list-wrap empty-state";
    return;
  }
  const fragment = document.createDocumentFragment();
  items.forEach((item) => fragment.appendChild(formatter(item)));
  target.className = "list-wrap";
  target.replaceChildren(fragment);
}

function renderIncidents(data) {
  selectors.incidentCount.textContent = String(data.total ?? 0);
  renderList(
    selectors.incidentList,
    data.items,
    (item) => {
      const row = document.createElement("div");
      row.className = "row";
      const left = document.createElement("div");
      const title = document.createElement("strong");
      title.textContent = item.title;
      const summary = document.createElement("div");
      summary.className = "list-subtle";
      summary.textContent = item.summary;
      left.replaceChildren(title, summary);
      row.append(left, badge(item.status ?? item.severity ?? "unknown"));
      return row;
    },
    "No incidents yet."
  );
}

function renderPolicies(items) {
  renderList(
    selectors.policyList,
    items,
    (item) => {
      const row = document.createElement("div");
      row.className = "row";
      const left = document.createElement("div");
      const title = document.createElement("strong");
      title.textContent = item.name;
      const meta = document.createElement("div");
      meta.className = "list-subtle";
      meta.textContent = `${item.policy_type} - v${item.version}`;
      left.replaceChildren(title, meta);
      row.append(left, badge(item.is_enabled ? "online" : "disabled"));
      return row;
    },
    "No policies configured yet."
  );
}

function renderActions(items) {
  selectors.actionCount.textContent = String(items?.length ?? 0);
  renderList(
    selectors.actionList,
    items,
    (item) => {
      const row = document.createElement("div");
      row.className = "row";
      const left = document.createElement("div");
      const title = document.createElement("strong");
      title.textContent = item.action_type ?? item.id;
      const meta = document.createElement("div");
      meta.className = "list-subtle";
      meta.textContent = `${item.status} - ${item.approval_status}`;
      left.replaceChildren(title, meta);
      row.append(left, badge(item.status ?? "unknown"));
      return row;
    },
    "No remediation actions yet."
  );
}

function renderAudit(data) {
  renderList(
    selectors.auditList,
    data.items,
    (item) => {
      const row = document.createElement("div");
      row.className = "row";
      const left = document.createElement("div");
      const title = document.createElement("strong");
      title.textContent = item.action;
      const meta = document.createElement("div");
      meta.className = "list-subtle";
      meta.textContent = item.actor_id || "system";
      left.replaceChildren(title, meta);
      row.append(left, badge(item.outcome ?? "unknown"));
      return row;
    },
    "No audit records yet."
  );
}

async function refreshDashboard() {
  clearError();
  try {
    if (!getToken()) {
      selectors.loginStatus.textContent = "Log in to load the control-plane dashboard.";
      return;
    }
    const [fleet, incidents, policies, actions, audit] = await Promise.all([
      fetchJson("/api/v1/fleet/overview"),
      fetchJson("/api/v1/incidents"),
      fetchJson("/api/v1/policies"),
      fetchJson("/api/v1/remediation/recent"),
      fetchJson("/api/v1/audit"),
    ]);

    renderFleet(fleet);
    renderIncidents(incidents);
    renderPolicies(policies);
    renderActions(actions.items);
    renderAudit(audit);
  } catch (error) {
    showError(`Dashboard refresh failed: ${error.message}`);
  }
}

selectors.refreshBtn?.addEventListener("click", refreshDashboard);
selectors.loginForm?.addEventListener("submit", login);
if (getToken()) {
  selectors.loginStatus.textContent = "Using saved access token.";
  refreshDashboard();
}
