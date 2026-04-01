"""
HTML UI for the Operator Console.

This page is intentionally single-screen and action-forward for non-technical
operators: one primary button, concise status, and guided approvals.
"""


def build_operator_console_html() -> str:
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Operator Console</title>
  <style>
    :root {
      --bg: #f7f8fa;
      --card: #ffffff;
      --text: #0f172a;
      --muted: #475569;
      --border: #e2e8f0;
      --primary: #0b5fff;
      --danger: #b42318;
      --ok: #067647;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
    }
    .wrap {
      max-width: 980px;
      margin: 0 auto;
      padding: 24px 16px 40px;
    }
    h1 {
      margin: 0 0 8px;
      font-size: 32px;
      line-height: 1.1;
      letter-spacing: -0.02em;
    }
    .sub {
      margin: 0 0 20px;
      color: var(--muted);
      font-size: 16px;
    }
    .card {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 16px;
      margin-bottom: 14px;
    }
    .primary {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      border: 2px solid #cfe0ff;
    }
    .primary h2 {
      margin: 0;
      font-size: 22px;
      letter-spacing: -0.01em;
    }
    .hint {
      margin: 6px 0 0;
      color: var(--muted);
      font-size: 14px;
    }
    .btn {
      border: 0;
      border-radius: 10px;
      padding: 11px 16px;
      font-weight: 600;
      cursor: pointer;
    }
    .btn:disabled { opacity: 0.5; cursor: not-allowed; }
    .btn-primary {
      color: #fff;
      background: var(--primary);
      min-width: 220px;
    }
    .btn-secondary {
      color: var(--text);
      background: #eef2f7;
    }
    .btn-danger {
      color: #fff;
      background: var(--danger);
    }
    .row {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 10px;
    }
    .kpi {
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 12px;
      background: #fff;
    }
    .kpi .label {
      display: block;
      color: var(--muted);
      font-size: 12px;
      margin-bottom: 6px;
    }
    .kpi .value {
      font-weight: 700;
      font-size: 22px;
      line-height: 1;
    }
    .status-line {
      margin: 10px 0 0;
      font-size: 13px;
      color: var(--muted);
    }
    .status-ok { color: var(--ok); }
    .status-bad { color: var(--danger); }
    .auth {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
    }
    input[type="password"], input[type="number"] {
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 10px 12px;
      min-width: 240px;
      font-size: 14px;
      background: #fff;
    }
    .section-title {
      margin: 0 0 10px;
      font-size: 18px;
      letter-spacing: -0.01em;
    }
    .list {
      display: grid;
      gap: 8px;
    }
    .item {
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 10px;
      background: #fff;
    }
    .item strong { display: block; margin-bottom: 4px; }
    .item p { margin: 0; color: var(--muted); font-size: 13px; }
    .item-actions {
      margin-top: 8px;
      display: flex;
      gap: 8px;
    }
    .empty {
      margin: 0;
      color: var(--muted);
      font-size: 14px;
    }
    .top-actions {
      display: flex;
      gap: 8px;
      align-items: center;
      margin-top: 10px;
    }
    .mono {
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 12px;
      color: var(--muted);
    }
    @media (max-width: 780px) {
      .row { grid-template-columns: 1fr 1fr; }
    }
    @media (max-width: 560px) {
      .row { grid-template-columns: 1fr; }
      .btn-primary { width: 100%; }
      input[type="password"], input[type="number"] { min-width: 0; width: 100%; }
    }
  </style>
</head>
<body>
  <main class="wrap">
    <h1>Operator Console</h1>
    <p class="sub">Run your venture safely from one screen: review approvals, run batch, and monitor guardrails.</p>

    <section class="card">
      <div class="auth">
        <input id="apiKey" type="password" placeholder="Paste API key (X-API-Key)" autocomplete="off" />
        <button class="btn btn-secondary" id="saveKeyBtn">Use Key</button>
        <button class="btn btn-secondary" id="refreshBtn">Refresh</button>
      </div>
      <p class="status-line" id="authStatus">Enter API key to load secure operator data.</p>
    </section>

    <section class="card primary">
      <div>
        <h2 id="primaryLabel">Review pending approvals</h2>
        <p class="hint" id="primaryHint">This is your main action right now.</p>
      </div>
      <button class="btn btn-primary" id="primaryActionBtn">Loading…</button>
    </section>

    <section class="card">
      <h3 class="section-title">Status</h3>
      <div class="row">
        <div class="kpi"><span class="label">Pending approvals</span><span class="value" id="kpiApprovals">0</span></div>
        <div class="kpi"><span class="label">Pending jobs</span><span class="value" id="kpiPendingJobs">0</span></div>
        <div class="kpi"><span class="label">Running jobs</span><span class="value" id="kpiRunningJobs">0</span></div>
        <div class="kpi"><span class="label">Dead-letter jobs</span><span class="value" id="kpiDeadLetter">0</span></div>
        <div class="kpi"><span class="label">Daily spend (USD)</span><span class="value" id="kpiSpend">0.00</span></div>
        <div class="kpi"><span class="label">Kill switch</span><span class="value" id="kpiKill">OFF</span></div>
      </div>
      <div class="top-actions">
        <button class="btn btn-danger" id="toggleKillBtn">Pause Automation</button>
        <label class="mono">Batch limit <input id="batchLimit" type="number" min="1" max="200" value="20" style="min-width:90px; width:90px;" /></label>
      </div>
      <p class="status-line" id="consoleStatus">Waiting for data…</p>
    </section>

    <section class="card">
      <h3 class="section-title">Pending approvals</h3>
      <div id="approvalList" class="list"></div>
      <p id="approvalEmpty" class="empty">No pending approvals.</p>
    </section>

    <section class="card">
      <h3 class="section-title">Recent audit activity</h3>
      <div id="auditList" class="list"></div>
      <p id="auditEmpty" class="empty">No recent events.</p>
    </section>
  </main>

  <script>
    const keyInput = document.getElementById("apiKey");
    const saveKeyBtn = document.getElementById("saveKeyBtn");
    const refreshBtn = document.getElementById("refreshBtn");
    const authStatus = document.getElementById("authStatus");
    const primaryActionBtn = document.getElementById("primaryActionBtn");
    const primaryLabel = document.getElementById("primaryLabel");
    const primaryHint = document.getElementById("primaryHint");
    const consoleStatus = document.getElementById("consoleStatus");
    const toggleKillBtn = document.getElementById("toggleKillBtn");
    const batchLimit = document.getElementById("batchLimit");
    const approvalList = document.getElementById("approvalList");
    const approvalEmpty = document.getElementById("approvalEmpty");
    const auditList = document.getElementById("auditList");
    const auditEmpty = document.getElementById("auditEmpty");

    let consoleData = null;

    function getApiKey() {
      return localStorage.getItem("operator_api_key") || "";
    }

    function idempotencyKey(prefix) {
      if (window.crypto && crypto.randomUUID) return `${prefix}-${crypto.randomUUID()}`;
      return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
    }

    function authHeaders(jsonBody = false) {
      const headers = {};
      const key = getApiKey();
      if (key) headers["X-API-Key"] = key;
      if (jsonBody) headers["Content-Type"] = "application/json";
      return headers;
    }

    function setText(id, value) {
      const el = document.getElementById(id);
      if (el) el.textContent = String(value);
    }

    async function requestJson(url, options = {}) {
      const response = await fetch(url, options);
      const text = await response.text();
      let payload = {};
      try { payload = text ? JSON.parse(text) : {}; } catch (_) {}
      if (!response.ok) {
        const message = payload.detail || payload.message || `Request failed (${response.status})`;
        throw new Error(message);
      }
      return payload;
    }

    function renderConsole(data) {
      consoleData = data;
      const action = data.primary_action || { type: "run_daily_batch", label: "Run daily batch" };
      primaryActionBtn.dataset.actionType = action.type;
      primaryActionBtn.textContent = action.label || "Run action";
      primaryLabel.textContent = action.label || "Primary action";
      primaryHint.textContent = action.type === "review_approvals"
        ? "Approvals are blocking execution. Clear these first."
        : "No blockers found. Run one controlled batch.";

      const k = data.kpis || {};
      setText("kpiApprovals", k.pending_approvals ?? 0);
      setText("kpiPendingJobs", k.pending_jobs ?? 0);
      setText("kpiRunningJobs", k.running_jobs ?? 0);
      setText("kpiDeadLetter", k.dead_letter_jobs ?? 0);
      setText("kpiSpend", Number(k.daily_spend_usd || 0).toFixed(2));
      setText("kpiKill", k.kill_switch_active ? "ON" : "OFF");

      toggleKillBtn.textContent = k.kill_switch_active ? "Resume Automation" : "Pause Automation";
      toggleKillBtn.className = k.kill_switch_active ? "btn btn-secondary" : "btn btn-danger";

      const killInfo = data.kill_switch || {};
      const guardrailState = data.route_pauses && data.route_pauses.length
        ? `Paused routes: ${data.route_pauses.length}`
        : "No route pauses";
      const killState = k.kill_switch_active
        ? `Kill switch ON${killInfo.reason ? ` (${killInfo.reason})` : ""}`
        : "Kill switch OFF";
      consoleStatus.textContent = `${killState} • ${guardrailState} • Updated ${data.timestamp || "now"}`;
      consoleStatus.className = `status-line ${k.kill_switch_active ? "status-bad" : "status-ok"}`;
    }

    function renderApprovals(items) {
      approvalList.innerHTML = "";
      if (!items.length) {
        approvalEmpty.style.display = "block";
        return;
      }
      approvalEmpty.style.display = "none";
      for (const item of items) {
        const box = document.createElement("div");
        box.className = "item";
        box.innerHTML = `
          <strong>${item.scope.toUpperCase()} • ${item.action_type}</strong>
          <p>${item.endpoint} • ${item.method} • ${item.created_at}</p>
          <div class="item-actions">
            <button class="btn btn-primary" data-approval-id="${item.id}">Approve & Run</button>
          </div>
        `;
        const button = box.querySelector("button");
        button.addEventListener("click", () => approveAndRun(item.id));
        approvalList.appendChild(box);
      }
    }

    function renderAudit(events) {
      auditList.innerHTML = "";
      if (!events.length) {
        auditEmpty.style.display = "block";
        return;
      }
      auditEmpty.style.display = "none";
      for (const event of events.slice(0, 8)) {
        const box = document.createElement("div");
        box.className = "item";
        const result = event.success ? "SUCCESS" : "FAIL";
        box.innerHTML = `
          <strong>${result} • ${event.event_type}</strong>
          <p>${event.endpoint} • $${Number(event.cost_usd || 0).toFixed(2)} • ${event.created_at}</p>
        `;
        auditList.appendChild(box);
      }
    }

    async function loadConsole() {
      try {
        const data = await requestJson("/operator/console", {
          headers: authHeaders(false),
        });
        renderConsole(data);
        authStatus.textContent = "Connected. Operator data loaded.";
        authStatus.className = "status-line status-ok";
      } catch (error) {
        authStatus.textContent = error.message;
        authStatus.className = "status-line status-bad";
        consoleStatus.textContent = "Console locked. Add a valid API key.";
      }
    }

    async function loadApprovals() {
      try {
        const data = await requestJson("/operator/approvals?status=pending", {
          headers: authHeaders(false),
        });
        renderApprovals(data.approvals || []);
      } catch (error) {
        approvalList.innerHTML = "";
        approvalEmpty.style.display = "block";
        approvalEmpty.textContent = `Unable to load approvals: ${error.message}`;
      }
    }

    async function loadAudit() {
      try {
        const data = await requestJson("/operator/audit/recent?limit=20", {
          headers: authHeaders(false),
        });
        renderAudit(data.events || []);
      } catch (error) {
        auditList.innerHTML = "";
        auditEmpty.style.display = "block";
        auditEmpty.textContent = `Unable to load audit: ${error.message}`;
      }
    }

    async function runBatch() {
      const limit = Math.max(1, Math.min(200, Number(batchLimit.value || 20)));
      await requestJson("/operator/run-daily-batch", {
        method: "POST",
        headers: {
          ...authHeaders(true),
          "Idempotency-Key": idempotencyKey("run-batch"),
        },
        body: JSON.stringify({ limit }),
      });
      await refreshAll();
    }

    async function approveAndRun(approvalId) {
      await requestJson("/operator/approve-and-run", {
        method: "POST",
        headers: {
          ...authHeaders(true),
          "Idempotency-Key": idempotencyKey("approve-run"),
        },
        body: JSON.stringify({
          approval_id: approvalId,
          approve: true,
          decision_note: "Approved from visual console",
        }),
      });
      await refreshAll();
    }

    async function toggleKillSwitch() {
      const activeNow = Boolean(consoleData && consoleData.kpis && consoleData.kpis.kill_switch_active);
      const reason = activeNow
        ? "Resumed from visual operator console"
        : "Paused from visual operator console";
      await requestJson("/operator/kill-switch", {
        method: "POST",
        headers: {
          ...authHeaders(true),
          "Idempotency-Key": idempotencyKey("kill-switch"),
        },
        body: JSON.stringify({ active: !activeNow, reason }),
      });
      await refreshAll();
    }

    async function handlePrimaryAction() {
      const actionType = primaryActionBtn.dataset.actionType;
      if (actionType === "review_approvals") {
        document.getElementById("approvalList").scrollIntoView({ behavior: "smooth", block: "start" });
        await loadApprovals();
        return;
      }
      await runBatch();
    }

    async function refreshAll() {
      primaryActionBtn.disabled = true;
      toggleKillBtn.disabled = true;
      refreshBtn.disabled = true;
      try {
        await Promise.all([loadConsole(), loadApprovals(), loadAudit()]);
      } finally {
        primaryActionBtn.disabled = false;
        toggleKillBtn.disabled = false;
        refreshBtn.disabled = false;
      }
    }

    saveKeyBtn.addEventListener("click", async () => {
      const key = keyInput.value.trim();
      if (!key) {
        authStatus.textContent = "Please enter API key.";
        authStatus.className = "status-line status-bad";
        return;
      }
      localStorage.setItem("operator_api_key", key);
      keyInput.value = "";
      await refreshAll();
    });

    refreshBtn.addEventListener("click", refreshAll);
    primaryActionBtn.addEventListener("click", handlePrimaryAction);
    toggleKillBtn.addEventListener("click", toggleKillSwitch);

    window.addEventListener("load", async () => {
      const existing = getApiKey();
      if (existing) authStatus.textContent = "Saved key detected. Loading…";
      await refreshAll();
    });
  </script>
</body>
</html>"""
