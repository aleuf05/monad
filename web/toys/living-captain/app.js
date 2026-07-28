const API_BASE = new URLSearchParams(location.search).get("api") || "/living-captain-api/status";
const CONFERENCE_API = "/live-captain-chat-api";
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
let operatorControlsActive = false;
const PERFORMANCE_AXES = ["tension", "warmth", "energy", "restraint"];

function operatorPerformanceControls() {
  if (!operatorControlsActive) return undefined;
  return Object.fromEntries(PERFORMANCE_AXES.map((axis) => [axis, Number(el(`${axis}Control`).value) / 100]));
}

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
  const character = MonadCharacters.get("captain.monad");
  const actions = data.recent_actions || [];
  const latest = actions.length ? actions[actions.length - 1] : null;
  const contextualIntent = latest?.kind === "custody_rejection" || latest?.kind === "spend_exhausted" ? "urgent" : "operational";
  const selectedIntent = el("performanceIntent").value;
  const intent = selectedIntent === "auto" ? contextualIntent : selectedIntent;
  const pressure = intent === "urgent" ? 0.75 : Math.min(0.5, (data.spend?.observe_count || 0) / Math.max(1, data.spend?.observe_limit || 1));
  const performance = MonadPerformance.plan("captain.monad", {
    character: character.traits,
    state: { pressure },
    intent,
    controls: operatorPerformanceControls(),
    context: { audience: "lieutenant", setting: "private-status", latest_action_kind: latest?.kind || null }
  });
  MonadVoice.setProfile({ speaker: character.id, ...character.voice, ...performance.voice });
  el("performanceStatus").textContent = `${performance.label} · tension ${Math.round(performance.axes.tension * 100)} · energy ${Math.round(performance.axes.energy * 100)} · ${performance.reasons.join(" / ")}`;
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
PERFORMANCE_AXES.forEach((axis) => {
  el(`${axis}Control`).addEventListener("input", (event) => {
    operatorControlsActive = true;
    el(`${axis}Value`).value = event.target.value;
  });
});
el("previewPerformanceButton").addEventListener("click", () => {
  if (captainVoiceHandle) stopCaptainVoice();
  speakCaptainStatus(lastStatusData || {}, "Performance preview. ");
});
el("resetPerformanceButton").addEventListener("click", () => {
  operatorControlsActive = false;
  el("performanceIntent").value = "auto";
  MonadPerformance.reset("captain.monad");
  el("performanceStatus").textContent = "Context control restored · continuity reset";
});

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

// --- Private Conference: optional authenticated conversation. This is
// deliberately independent of the public status poll above, so model or
// conference failure cannot take the Living Captain instrument down. ---
const conference = {
  authenticated: false,
  busy: false,
};

function setConferenceState(label, ok = false) {
  el("conferenceStatus").textContent = label;
  el("conferenceDot").classList.toggle("is-live", ok);
  el("conferenceDot").classList.toggle("is-error", !ok);
}

function conferenceFeedback(message, error = false) {
  el("conferenceFeedback").textContent = message;
  el("conferenceFeedback").classList.toggle("is-error", error);
}

function renderConferenceMessages(messages) {
  const container = el("conferenceMessages");
  container.replaceChildren();
  messages.forEach((message) => {
    const article = document.createElement("article");
    article.className = `conference-message ${message.role}`;
    const label = document.createElement("small");
    label.textContent = message.role === "assistant" ? "Captain" : "Admiral";
    const content = document.createElement("div");
    content.textContent = message.content;
    article.append(label, content);
    container.append(article);
  });
  container.scrollTop = container.scrollHeight;
}

function renderConferenceUsage(usage = {}) {
  const reserved = Number(usage.reserved_dollars || 0);
  el("conferenceUsage").textContent =
    `${usage.request_count ?? 0}/${usage.max_requests ?? "—"} requests · $${reserved.toFixed(4)}/$${Number(usage.max_dollars || 2).toFixed(2)} reserved estimate`;
}

async function conferenceRequest(path, options = {}) {
  const response = await fetch(`${CONFERENCE_API}${path}`, {
    credentials: "same-origin",
    cache: "no-store",
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  let data;
  try {
    data = await response.json();
  } catch {
    data = { ok: false, error: `HTTP ${response.status}` };
  }
  if (!response.ok) {
    const error = new Error(data.error || `HTTP ${response.status}`);
    error.status = response.status;
    throw error;
  }
  return data;
}

async function loadConference() {
  try {
    const [status, transcript] = await Promise.all([
      conferenceRequest("/status"),
      conferenceRequest("/messages"),
    ]);
    conference.authenticated = true;
    el("conferenceLogin").hidden = true;
    el("conferenceRoom").hidden = false;
    el("conferenceProvider").textContent = `${status.provider} / ${status.model}`;
    renderConferenceUsage(status.usage);
    renderConferenceMessages(transcript.messages || []);
    setConferenceState("Private service ready", true);
    conferenceFeedback("Authenticated session. The Captain remains advisory and read-only.");
  } catch (error) {
    conference.authenticated = false;
    el("conferenceRoom").hidden = true;
    if (error.status === 401) {
      el("conferenceLogin").hidden = false;
      setConferenceState("Authentication required");
      conferenceFeedback("Enter the private conference password. Public instruments remain available.");
    } else {
      el("conferenceLogin").hidden = true;
      setConferenceState("Conference unavailable");
      conferenceFeedback(`Private conference offline: ${error.message}. Public status remains operational.`, true);
    }
  }
}

el("conferenceLogin").addEventListener("submit", async (event) => {
  event.preventDefault();
  conferenceFeedback("Authenticating…");
  try {
    await conferenceRequest("/login", {
      method: "POST",
      body: JSON.stringify({ password: el("conferencePassword").value }),
    });
    el("conferencePassword").value = "";
    await loadConference();
  } catch (error) {
    conferenceFeedback(error.status === 401 ? "Password rejected." : `Login failed: ${error.message}`, true);
  }
});

el("conferenceComposer").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (conference.busy) return;
  const message = el("conferenceMessage").value.trim();
  if (!message) return;
  conference.busy = true;
  el("conferenceSend").disabled = true;
  el("conferenceMessage").disabled = true;
  conferenceFeedback("Captain is considering the message…");
  try {
    const result = await conferenceRequest("/messages", {
      method: "POST",
      body: JSON.stringify({ message }),
    });
    el("conferenceMessage").value = "";
    renderConferenceUsage(result.usage);
    const transcript = await conferenceRequest("/messages");
    renderConferenceMessages(transcript.messages || []);
    conferenceFeedback("Reply received and preserved.");
  } catch (error) {
    conferenceFeedback(`No reply: ${error.message}`, true);
    if (error.status === 401) await loadConference();
    else {
      const transcript = await conferenceRequest("/messages").catch(() => null);
      if (transcript) renderConferenceMessages(transcript.messages || []);
    }
  } finally {
    conference.busy = false;
    el("conferenceSend").disabled = false;
    el("conferenceMessage").disabled = false;
    el("conferenceMessage").focus();
  }
});

el("conferenceLogout").addEventListener("click", async () => {
  await conferenceRequest("/logout", { method: "POST", body: "{}" }).catch(() => {});
  conference.authenticated = false;
  el("conferenceRoom").hidden = true;
  el("conferenceLogin").hidden = false;
  setConferenceState("Authentication required");
  conferenceFeedback("Private conference closed. Local history remains preserved.");
});

loadConference();
