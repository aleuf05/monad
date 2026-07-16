const API_BASE = new URLSearchParams(location.search).get("api") || "/living-captain-api/status";
const POLL_INTERVAL_MS = 10000;

const el = (id) => document.getElementById(id);

// --- Voice: on-demand read + opt-in auto-announce on a genuinely new
// observation (never continuous -- Living Captain's own spend boundary
// means there is rarely anything new to say; see the voice-panel's own
// copy in index.html). Self-contained rather than sharing Radio
// Console's speech code: separate deployable toy, small enough that a
// shared module isn't worth the coupling. ---
let lastStatusData = null;
let captainVoiceHandle = null;
let autoAnnounceArmed = false;
let hasSeededObserveCount = false;
let lastSeenObserveCount = null;

function buildStatusSentence(data) {
  const identity = data.identity || {};
  const sight = data.last_observed || {};
  const spend = data.spend || {};
  const actions = data.recent_actions || [];
  const latest = actions.length ? actions[actions.length - 1] : null;
  const parts = [`Captain's report. ${identity.captain_id || "Unidentified captain"}.`];
  if (sight.fleetcore_tick != null) {
    parts.push(`Last observed FleetCore at tick ${sight.fleetcore_tick}, event sequence ${sight.fleetcore_event_sequence}.`);
    if (sight.world_intake_pending_count != null) {
      parts.push(`${sight.world_intake_pending_count} World Intake proposal${sight.world_intake_pending_count === 1 ? "" : "s"} pending.`);
    }
  } else {
    parts.push("No observation recorded yet.");
  }
  if (spend.observe_limit != null) {
    const remaining = Math.max(0, spend.observe_limit - (spend.observe_count ?? 0));
    parts.push(`Observe budget: ${remaining} of ${spend.observe_limit} remaining.`);
  }
  if (latest) parts.push(`Most recent action: ${latest.summary}`);
  return parts.join(" ");
}

function stopCaptainVoice() {
  captainVoiceHandle?.stop();
  captainVoiceHandle = null;
  el("readStatusButton").textContent = "Read Status";
  const status = el("voiceStatus");
  status.textContent = autoAnnounceArmed ? "Auto-announce armed; voice idle." : "Voice idle.";
  status.classList.remove("is-reading");
}

function speakCaptainStatus(data, prefix) {
  MonadVoice.setProfile({ speaker: "captain.monad", provider_id: "browser-speechsynthesis", rate: 0.96, pitch: 1, volume: 1 });
  MonadVoice.speak("captain.monad", `${prefix}${buildStatusSentence(data)}`).then(({ handle, fallback_used }) => {
    captainVoiceHandle = handle;
    handle.onstart = () => {
    el("readStatusButton").textContent = "Stop Reading";
    const status = el("voiceStatus");
    status.textContent = `Reading captain's report · ${handle.provider_label}${handle.voice_label ? ` · ${handle.voice_label}` : ""}${fallback_used ? " · fallback" : ""}`;
    status.classList.add("is-reading");
    };
    handle.onend = stopCaptainVoice;
    handle.onerror = stopCaptainVoice;
  }).catch((error) => { el("voiceStatus").textContent = error.message; });
  return true;
}

function handleReadStatusClick() {
  if (captainVoiceHandle) return stopCaptainVoice();
  speakCaptainStatus(lastStatusData || {}, "");
}

function handleAutoAnnounceToggle() {
  autoAnnounceArmed = el("autoAnnounceToggle").checked;
  if (!captainVoiceHandle) {
    el("voiceStatus").textContent = autoAnnounceArmed ? "Auto-announce armed; voice idle." : "Voice idle.";
  }
}

el("readStatusButton").addEventListener("click", handleReadStatusClick);
el("autoAnnounceToggle").addEventListener("change", handleAutoAnnounceToggle);

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

    lastStatusData = data;
    // observe_count rising is the one real signal a genuinely new
    // observation happened -- Living Captain's spend boundary means this
    // is rare (default limit 1 per restart), by design, not a bug in this
    // check. Seeded silently on first load so arming auto-announce (or
    // just opening the page) never speaks whatever was already there.
    const observeCount = data.spend?.observe_count ?? null;
    if (observeCount !== null) {
      if (!hasSeededObserveCount) {
        hasSeededObserveCount = true;
        lastSeenObserveCount = observeCount;
      } else if (autoAnnounceArmed && observeCount !== lastSeenObserveCount && !captainVoiceHandle) {
        lastSeenObserveCount = observeCount;
        speakCaptainStatus(data, "New observation. ");
      }
    }

    setLink(true, "Connected");
    showFeedback("", false);
  } catch (error) {
    setLink(false, "Unreachable");
    showFeedback(`Could not reach the Living Captain status API: ${error.message}`, true);
  }
}

refresh();
setInterval(refresh, POLL_INTERVAL_MS);
