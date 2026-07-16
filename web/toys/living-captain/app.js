const API_BASE = new URLSearchParams(location.search).get("api") || "/living-captain-api/status";
const POLL_INTERVAL_MS = 10000;

const el = (id) => document.getElementById(id);

function setLink(ok, label) {
  el("liveDot").classList.toggle("is-live", ok);
  el("liveDot").classList.toggle("is-error", !ok);
  el("linkStatus").textContent = label;
}

function showFeedback(message, isError) {
  const node = el("feedback");
  node.textContent = message;
  node.hidden = !message;
  node.classList.toggle("is-error", Boolean(isError));
}

function renderIdentity(identity) {
  el("captainId").textContent = identity.captain_id ?? "—";
  el("restartCount").textContent = identity.restart_count ?? "—";
  el("createdAt").textContent = identity.created_at ?? "—";
  el("lastAssembled").textContent = identity.last_assembled_at ?? "—";
}

function renderSight(sight) {
  const fields = [
    ["FleetCore Tick", sight.fleetcore_tick],
    ["FleetCore Event Sequence", sight.fleetcore_event_sequence],
    ["World Intake Pending", sight.world_intake_pending_count],
  ];
  el("sightGrid").innerHTML = fields
    .map(
      ([label, value]) => `
      <div class="captain-card">
        <dl><dt>${label}</dt><dd>${value ?? "— (no observation recorded yet)"}</dd></dl>
      </div>`
    )
    .join("");
}

function renderSpend(spend) {
  const count = spend.observe_count ?? 0;
  const limit = spend.observe_limit;
  const remaining = limit == null ? null : Math.max(0, limit - count);
  const pct = limit ? Math.min(100, (count / limit) * 100) : 0;
  el("spendLabel").textContent = `${count} / ${limit ?? "—"} observe calls used`;
  el("spendRemaining").textContent = remaining == null ? "—" : `${remaining} left`;
  const fill = el("spendFill");
  fill.style.width = `${pct}%`;
  fill.classList.toggle("is-exhausted", remaining === 0);
}

function renderCustody(manifest) {
  const requests = manifest?.allowed_requests ?? [];
  el("custodyList").innerHTML = requests.length
    ? requests
        .map((req) => `<li><span class="method">${req.method}</span>${req.url}</li>`)
        .join("")
    : "<li>No custody manifest recorded yet.</li>";
}

function renderActions(actions, totalLength) {
  el("actionLogLength").textContent = totalLength ?? actions.length;
  if (!actions.length) {
    el("actionBody").innerHTML = '<tr><td colspan="4">No actions recorded yet.</td></tr>';
    return;
  }
  el("actionBody").innerHTML = actions
    .slice()
    .reverse()
    .map(
      (entry) => `
      <tr>
        <td>${entry.sequence}</td>
        <td>${entry.recorded_at}</td>
        <td class="kind-${entry.kind}">${entry.kind}</td>
        <td>${entry.summary}</td>
      </tr>`
    )
    .join("");
}

async function refresh() {
  try {
    const response = await fetch(API_BASE, { cache: "no-store" });
    if (!response.ok) throw new Error(`status API returned HTTP ${response.status}`);
    const data = await response.json();

    renderIdentity(data.identity ?? {});
    renderSight(data.last_observed ?? {});
    renderSpend(data.spend ?? {});
    renderCustody(data.custody_manifest);
    renderActions(data.recent_actions ?? [], data.action_log_length);

    setLink(true, "Connected");
    showFeedback("", false);
  } catch (error) {
    setLink(false, "Unreachable");
    showFeedback(`Could not reach the Living Captain status API: ${error.message}`, true);
  }
}

refresh();
setInterval(refresh, POLL_INTERVAL_MS);
