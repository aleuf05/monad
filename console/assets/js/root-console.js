// Root Console frontend, served live at cameronlampley.com/root.
// Talks to the root-console daemon (tools/root-console/server.py, port
// 4792) through Caddy's /root-console-api/* reverse proxy -- there is no
// separate dev deployment, this file IS the live page.
const API_BASE = "/root-console-api/api";
// The conversation surface itself (turn/stream only) is served by the
// separate Live Captain minimum-context bootstrap
// (tools/live-captain/server.py, port 4778) -- see
// LIVE-CAPTAIN-MINIMUM-CONTEXT-BOOTSTRAP-0.1. Login, status, and handoffs
// stay on root-console.service above; only the actual Captain
// conversation moved.
//
// NON-OBVIOUS AND COSTLY IF MISSED: these two services are not
// independent. live-captain-bootstrap imports the SAME
// tools/root-console/generated_images.py module root-console.service uses,
// and every image URL it mints still points back at
// root-console.service's /api/generated-image/ route -- root-console is
// the ONLY service that ever serves the actual image bytes, even for a
// conversation running entirely on live-captain-bootstrap. Restarting only
// one of the two, or checking only one of the two before declaring
// something broken/fixed, WILL produce misleading results. Always check
// and restart both together.
const LIVE_CAPTAIN_API_BASE = "/live-captain-bootstrap-api/api";

const bearingIndicatorEl = document.getElementById("bearing-indicator");
const loginGate = document.getElementById("login-gate");
const loginForm = document.getElementById("login-form");
const loginPassword = document.getElementById("login-password");
const loginError = document.getElementById("login-error");

const terminalEl = document.getElementById("terminal");
const promptRowEl = document.getElementById("prompt-row");
const connEl = document.getElementById("conn");
const connTextEl = document.getElementById("conn-text");
const input = document.getElementById("input");
const commandDraftInput = document.getElementById("command-draft-input");
const commandDraftToggle = document.getElementById("command-draft-toggle");
const commandDraftSend = document.getElementById("command-draft-send");
let commandDraftMode = false;

function activeCommandInput() { return commandDraftMode ? commandDraftInput : input; }
function setCommandDraftMode(enabled) {
  commandDraftMode = Boolean(enabled);
  promptRowEl.classList.toggle("command-draft", commandDraftMode);
  commandDraftToggle?.classList.toggle("on", commandDraftMode);
  if (commandDraftToggle) commandDraftToggle.textContent = commandDraftMode ? "COMMAND DRAFT" : "LONG COMMAND";
  captainPosture.textContent = commandDraftMode ? "Command Draft posture" : "Bridge posture";
  activeCommandInput()?.focus();
}
commandDraftToggle?.addEventListener("click", () => setCommandDraftMode(!commandDraftMode));
commandDraftSend?.addEventListener("click", () => submitDirective());
const captainPresenceState = document.getElementById("captain-presence-state");
const captainPresenceDetail = document.getElementById("captain-presence-detail");
const captainPosture = document.getElementById("captain-posture");
let currentCaptainState = "connecting";

function setCaptainPresence(state, detail) {
  currentCaptainState = state || "ready";
  document.body.dataset.captainState = currentCaptainState;
  const labels = {
    connecting: "CONNECTING", ready: "ON WATCH", thinking: "THINKING",
    researching: "RESEARCHING", speaking: "SPEAKING", fault: "FAULT",
  };
  captainPresenceState.textContent = labels[currentCaptainState] || currentCaptainState.toUpperCase();
  if (detail) captainPresenceDetail.textContent = detail;
}
window.setCaptainPresence = setCaptainPresence;
setCaptainPresence("connecting", "Establishing the watch…");

function setActivePairMove(move) {
  const action = document.getElementById("bridge-course-action");
  if (action && move) action.textContent = move;
}
window.setActivePairMove = setActivePairMove;

const telPid = document.getElementById("tel-pid");
const telUptime = document.getElementById("tel-uptime");
const telThread = document.getElementById("tel-thread");
const telTokens = document.getElementById("tel-tokens");
const telRatelimit = document.getElementById("tel-ratelimit");
const telSubs = document.getElementById("tel-subs");
const imageStage = document.getElementById("image-stage");
const imageStageImage = document.getElementById("image-stage-image");
const imageStageTitle = document.getElementById("image-stage-title");
const imageStageOpen = document.getElementById("image-stage-open");
const imageStageClose = document.getElementById("image-stage-close");
const imageStageCanvas = document.getElementById("image-stage-canvas");

const activityToggle = document.getElementById("activity-toggle");
const activityLog = document.getElementById("activity-log");

const handoffsList = document.getElementById("handoffs-list");
const handoffsRefresh = document.getElementById("handoffs-refresh");
const shipLogList = document.getElementById("ship-log-list");
const shipLogRefresh = document.getElementById("ship-log-refresh");
const handoffDetail = document.getElementById("handoff-detail");
const handoffDetailTitle = document.getElementById("handoff-detail-title");
const handoffDetailBody = document.getElementById("handoff-detail-body");
const handoffDetailClose = document.getElementById("handoff-detail-close");
const dispatchViewLatest = document.getElementById("dispatch-view-latest");
const captainCourseGrid = document.getElementById("captain-course-grid");
const captainCourseRefresh = document.getElementById("captain-course-refresh");
const objectiveState = document.getElementById("captain-objective-state");
const objectiveText = document.getElementById("captain-objective-text");
const objectiveProgress = document.getElementById("captain-objective-progress");
const objectiveButtons = {
  propose: document.getElementById("objective-propose"), approve: document.getElementById("objective-approve"),
  pause: document.getElementById("objective-pause"), resume: document.getElementById("objective-resume"),
  reject: document.getElementById("objective-reject"),
};
let currentObjective = null;

function paintObjective(objective) {
  currentObjective = objective;
  objectiveState.textContent = objective ? objective.state.replaceAll("_", " ") : "NO OBJECTIVE";
  objectiveText.textContent = objective ? objective.objective : "No bounded autonomous campaign is staged.";
  objectiveProgress.textContent = objective ? `${objective.moves_used}/${objective.move_budget} autonomous moves · ${objective.scope}` : "";
  objectiveButtons.propose.hidden = Boolean(objective && !["COMPLETE", "BLOCKED", "REJECTED"].includes(objective.state));
  objectiveButtons.approve.hidden = !objective || !["AWAITING_ADMIRAL", "CHECKPOINT"].includes(objective.state);
  objectiveButtons.pause.hidden = !objective || !["APPROVED", "ACTIVE"].includes(objective.state);
  objectiveButtons.resume.hidden = !objective || objective.state !== "PAUSED";
  objectiveButtons.reject.hidden = !objective || !["AWAITING_ADMIRAL", "CHECKPOINT", "PAUSED"].includes(objective.state);
}

async function objectiveRequest(payload) {
  const response = await fetch(`${LIVE_CAPTAIN_API_BASE}/objective`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.error || `HTTP ${response.status}`);
  paintObjective(body.objective);
}

async function refreshObjective() {
  const response = await fetch(`${LIVE_CAPTAIN_API_BASE}/objective`, { cache: "no-store" });
  if (response.ok) paintObjective((await response.json()).objective);
}

objectiveButtons.propose.addEventListener("click", () => objectiveRequest({
  action: "propose",
  objective: "Research how the live Semantic Document Viewer can better support deep reading, comprehension, comparison, and movement from documents into engineering action.",
  scope: "console/documents.html and its existing document sources; reversible research instruments, measurements, prototypes, and tests only; no publication or unrelated work.",
  success_criteria: ["Current viewer behavior and friction are inspected", "At least three distinct improvement concepts are compared", "One discriminating viewer probe or prototype is run", "Evidence and a recommended implementation course are returned"],
  move_budget: 3,
}).catch((error) => window.alert(error.message)));
for (const action of ["approve", "pause", "resume", "reject"]) {
  objectiveButtons[action].addEventListener("click", () => {
    if (action === "approve" && !window.confirm("Authorize the Captain to execute this bounded objective now?")) return;
    objectiveRequest({ action, id: currentObjective.id }).catch((error) => window.alert(error.message));
  });
}
refreshObjective();
const bridgeCourseRefresh = document.getElementById("bridge-course-refresh");

async function refreshBridgeCourse() {
  if (bridgeCourseRefresh) bridgeCourseRefresh.disabled = true;
  try {
    const response = await fetch(`${API_BASE}/course`, { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const course = await response.json();
    setActivePairMove(course.captain_action);
    const watch = course.watch || {};
    document.getElementById("bridge-course-watch").textContent = watch.status === "clear"
      ? "Clear · no action required" : `${watch.alert_count || 0} alert(s) · ${watch.next_action}`;
    document.getElementById("bridge-watch-card").classList.toggle("warn", watch.status !== "clear");
    document.getElementById("bridge-course-gate").textContent = course.human_gate;
    const continuity = course.continuity || {};
    const latest = continuity.latest_handoff;
    document.getElementById("bridge-course-continuity").textContent = latest
      ? `${latest.taskId} · ${latest.agent}` : "No completed handoff indexed";
  } catch (error) {
    document.getElementById("bridge-course-action").textContent = `Course unavailable · ${error.message}`;
    document.getElementById("bridge-watch-card").classList.add("warn");
  } finally {
    if (bridgeCourseRefresh) bridgeCourseRefresh.disabled = false;
  }
}

if (bridgeCourseRefresh) bridgeCourseRefresh.addEventListener("click", refreshBridgeCourse);

async function refreshWorldIntake() {
  const button = document.getElementById("world-intake-refresh");
  const summary = document.getElementById("world-intake-summary");
  const cards = document.getElementById("world-intake-cards");
  const state = document.getElementById("world-intake-state");
  if (!button || !summary || !cards || !state) return;
  button.disabled = true;
  try {
    const response = await fetch(`${API_BASE}/intake`, { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const intake = await response.json();
    const world = intake.world || {};
    const packets = intake.packets || {};
    summary.replaceChildren();
    for (const [value, label, warn] of [
      [world.pending ?? "?", "pending", world.pending > 0],
      [world.individual_approval ?? "?", "individual", world.individual_approval > 0],
      [packets.staged ?? "?", "packets staged", packets.staged > 0],
    ]) {
      const metric = document.createElement("div");
      metric.className = `intake-metric${warn ? " warn" : ""}`;
      const strong = document.createElement("strong"); strong.textContent = value;
      const caption = document.createElement("span"); caption.textContent = label;
      metric.append(strong, caption); summary.append(metric);
    }
    cards.replaceChildren();
    for (const item of world.cards || []) {
      const card = document.createElement("div");
      card.className = `intake-card${item.individual_approval || item.conflicts ? " risk" : ""}`;
      const head = document.createElement("div"); head.className = "intake-card-head";
      const subject = document.createElement("strong"); subject.textContent = item.subject;
      const kind = document.createElement("span"); kind.textContent = item.class;
      head.append(subject, kind);
      const meta = document.createElement("div"); meta.className = "intake-card-meta";
      meta.textContent = `${item.operation || "proposal"} · ${Math.round((item.confidence || 0) * 100)}%${item.conflicts ? ` · ${item.conflicts} conflict(s)` : ""}${item.individual_approval ? " · individual approval" : ""}`;
      card.append(head, meta); cards.append(card);
    }
    if (!(world.cards || []).length) cards.textContent = "No pending World Intake proposals.";
    state.textContent = intake.status === "ready"
      ? `${world.pending} pending · ${world.deferred} deferred · live API`
      : `degraded · ${Object.keys(intake.errors || {}).join(", ")}`;
  } catch (error) {
    cards.textContent = `Intake unavailable · ${error.message}`;
    state.textContent = "fault";
  } finally {
    button.disabled = false;
  }
}

document.getElementById("world-intake-refresh")?.addEventListener("click", refreshWorldIntake);

function courseItem(label, value, tone = "") {
  const item = document.createElement("div");
  item.className = `course-item ${tone}`.trim();
  const heading = document.createElement("div");
  heading.className = "course-label";
  heading.textContent = label;
  const body = document.createElement("div");
  body.className = "course-value";
  body.textContent = value;
  item.append(heading, body);
  return item;
}

async function refreshCaptainCourse() {
  captainCourseRefresh.disabled = true;
  const requests = await Promise.allSettled([
    fetch(`${API_BASE}/course`, { cache: "no-store" }).then((r) => r.json()),
    fetch("/m3-cycle-api/api/evaluate").then((r) => r.json()),
  ]);
  const value = (index, fallback) => requests[index].status === "fulfilled" ? requests[index].value : fallback;
  const course = value(0, {});
  const m3 = value(1, {}).result || null;
  captainCourseGrid.replaceChildren();

  const ops = course.watch || {};
  captainCourseGrid.append(courseItem(
    "Operator watch",
    ops.status === "clear" ? "Clear — no action required." : `${ops.alert_count || 0} alert(s) — ${ops.next_action || "inspect Fleetnet"}`,
    ops.status === "clear" ? "good" : "warn",
  ));
  captainCourseGrid.append(courseItem("Captain action", course.captain_action || "Course unavailable.", course.captain_action ? "good" : "warn"));
  captainCourseGrid.append(courseItem("Human gate", course.human_gate || "No human gate reported.", (course.speech || {}).outcome === "fault" ? "warn" : ""));
  const tree = course.engineering || {};
  captainCourseGrid.append(courseItem(
    "Engineering state",
    `${tree.uncommitted ?? "?"} uncommitted files · head ${tree.head || "unknown"}`,
    tree.uncommitted ? "warn" : "good",
  ));
  const latest = (course.continuity || {}).latest_handoff;
  captainCourseGrid.append(courseItem(
    "Latest completed work",
    latest ? `${latest.agent} · ${latest.taskId} · ${latest.publicationState.toLowerCase()}` : "No handoff available.",
    latest ? "good" : "",
  ));
  const newest = (course.continuity || {}).latest_log;
  captainCourseGrid.append(courseItem(
    "Latest preserved signal",
    newest ? `${newest.title || newest.file} · ${newest.source}` : "Ship's Log unavailable.",
    newest ? "good" : "warn",
  ));
  captainCourseGrid.append(courseItem(
    "M³ counsel",
    !m3 ? "Evaluation unavailable." : !m3.proposed ? "No docs change proposed." :
      `${m3.verdict.toUpperCase()} · continuity ${m3.continuity.holds ? "holds" : "fails"} · value ${m3.valuation.before}→${m3.valuation.after} · Q ${m3.q_rev.holds ? "improves" : "fails"}`,
    m3 && (m3.verdict === "commit" || !m3.proposed) ? "good" : "warn",
  ));
  captainCourseRefresh.disabled = false;
}

captainCourseRefresh.addEventListener("click", refreshCaptainCourse);

// Living Captain stations are an attention model over the existing working
// controls. They do not copy state or create alternate backends.
(function wireCaptainStations() {
  const labels = {
    bridge: "Conversation has the deck.",
    wardroom: "Captain leads · Admiral shapes and rules · Master Chief tests.",
    course: "Orders, handoffs, record, and revision.",
    intake: "New material enters under Captain review.",
    research: "Live Research posture — inquire, probe, observe, adapt.",
    systems: "Raw machinery and live execution signals.",
  };
  const buttons = Array.from(document.querySelectorAll(".captain-station"));
  const bearing = document.getElementById("captain-station-bearing");
  function select(station) {
    if (!labels[station]) station = "bridge";
    document.body.dataset.captainStation = station;
    buttons.forEach((button) => button.classList.toggle("on", button.dataset.station === station));
    bearing.textContent = labels[station];
    captainPosture.textContent = `${station === "research" ? "Live Research" : station} posture`;
    if (["ready", "connecting"].includes(currentCaptainState)) {
      setCaptainPresence(currentCaptainState, labels[station]);
    }
    localStorage.setItem("monad.captainStation", station);
    if (station === "course") refreshCaptainCourse();
    if (station === "bridge") refreshBridgeCourse();
    if (station === "wardroom" && window.refreshWardroom) window.refreshWardroom();
    if (station === "intake") refreshWorldIntake();
    if (!window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      terminalEl.animate(
        station === "bridge"
          ? [{ transform: "scale(.985)", opacity: .78 }, { transform: "scale(1)", opacity: 1 }]
          : [{ transform: "translateX(-8px)", opacity: .82 }, { transform: "translateX(0)", opacity: 1 }],
        { duration: 330, easing: "cubic-bezier(.2,.85,.25,1)" },
      );
      const panel = document.getElementById("status-panel");
      if (station !== "bridge") panel.animate(
        [{ transform: "translateX(22px)", opacity: 0 }, { transform: "translateX(0)", opacity: 1 }],
        { duration: 420, easing: "cubic-bezier(.18,.9,.2,1)" },
      );
    }
  }
  window.selectCaptainStation = select;
  buttons.forEach((button) => button.addEventListener("click", () => select(button.dataset.station)));
  const requestedStation = new URLSearchParams(window.location.search).get("station");
  select(requestedStation || localStorage.getItem("monad.captainStation") || "bridge");
})();
refreshCaptainCourse();

// Wardroom is a meeting posture over the real Captain conversation. It owns
// no alternate transcript or backend: every action enters the same command
// seam, and every spoken answer uses the same verified Captain voice path.
(function wireWardroom() {
  const agenda = Array.from(document.querySelectorAll("#wardroom-agenda [data-phase]"));
  const audioState = document.getElementById("wardroom-audio-state");
  const fleetnetState = document.getElementById("wardroom-fleetnet-state");
  const clock = document.getElementById("wardroom-clock");
  if (!agenda.length || !audioState || !fleetnetState || !clock) return;
  let fleetnetCursor = null;
  let fleetnetPrimed = false;
  let wardroomAudioArmed = false;
  let wardroomAudioArmedAt = 0;
  let wardroomRoomReady = false;
  // Calling to order is a one-shot transition. Repeated clicks must be
  // harmless rather than dispatching duplicate meeting commands.
  let wardroomMeetingCalled = localStorage.getItem("monad.wardroomMeetingCalled") === "1";
  const audioConfirm = document.getElementById("wardroom-audio-confirm");
  const openMeeting = document.getElementById("wardroom-open");

  function inject(text, dispatch = false) {
    setCommandDraftMode(false);
    input.value = text;
    input.focus();
    if (dispatch) submitDirective();
  }

  function refresh() {
    const now = new Date();
    const local = new Intl.DateTimeFormat("en-US", {
      timeZone: "America/New_York", hour: "2-digit", minute: "2-digit",
      hour12: false, weekday: "short",
    }).format(now);
    clock.textContent = `Readiness muster · America/New_York · now ${local}`;
    audioState.textContent = wardroomRoomReady
      ? "Room audio confirmed · Wardroom may be called to order."
      : wardroomAudioArmed
        ? "Sound check dispatched · after hearing room sound, complete step 2."
        : "READY FOR STEP 1 · Press Arm & test audio to unlock this device's speakers.";
    audioState.classList.toggle("ready", wardroomAudioArmed);
    fleetnetState.textContent = wardroomAudioArmed
      ? "FleetNet receiver armed · new priority traffic will sound in this room."
      : "FleetNet receiver awaiting audio arm.";
    fleetnetState.classList.toggle("ready", wardroomAudioArmed);
    document.getElementById("wardroom-step-audio")?.classList.toggle("ready", wardroomAudioArmed);
    document.getElementById("wardroom-step-confirm")?.classList.toggle("ready", wardroomRoomReady);
    document.getElementById("wardroom-step-open")?.classList.toggle("ready", wardroomRoomReady);
    if (audioConfirm) audioConfirm.disabled = !wardroomAudioArmed || wardroomRoomReady;
    if (openMeeting) {
      openMeeting.disabled = !wardroomRoomReady || wardroomMeetingCalled;
      openMeeting.textContent = wardroomMeetingCalled ? "meeting called ✓" : "call to order";
    }
  }
  window.refreshWardroom = refresh;

  document.getElementById("wardroom-sound-check")?.addEventListener("click", () => {
    unlockCaptainVoice();
    setCaptainVoice(true);
    wardroomAudioArmed = true;
    wardroomAudioArmedAt = Date.now();
    refresh();
    speakLocally("Wardroom audio path. Captain on watch. Room channel five by five.");
  });
  audioConfirm?.addEventListener("click", () => {
    wardroomRoomReady = true;
    refresh();
  });
  openMeeting?.addEventListener("click", () => {
    if (!wardroomRoomReady) return;
    if (wardroomMeetingCalled) return;
    wardroomMeetingCalled = true;
    localStorage.setItem("monad.wardroomMeetingCalled", "1");
    refresh();
    inject("Captain, call the Wardroom meeting to order. Confirm the muster, state the purpose and present position, then lead the first agenda phase concisely.", true);
  });
  document.getElementById("wardroom-readback")?.addEventListener("click", () => {
    inject("Captain readback: summarize decisions, canon rulings, flexible practice, actions with acceptance conditions, and remaining gates. Do not promote an unstated ruling.", true);
  });
  document.querySelectorAll("[data-wardroom-marker]").forEach((button) => {
    button.addEventListener("click", () => inject(button.dataset.wardroomMarker || ""));
  });
  agenda.forEach((button) => button.addEventListener("click", () => {
    agenda.forEach((item) => item.classList.toggle("on", item === button));
    localStorage.setItem("monad.wardroomPhase", button.dataset.phase);
    inject(`Captain, proceed to Wardroom phase: ${button.textContent.trim()}. Lead this phase and preserve the current course.`);
  }));
  const saved = localStorage.getItem("monad.wardroomPhase") || "purpose";
  agenda.find((button) => button.dataset.phase === saved)?.classList.add("on");

  async function pollFleetnet() {
    try {
      const response = await fetch("/data/fleetnet-wire.json", { cache: "no-store" });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const entries = (await response.json()).entries || [];
      if (!fleetnetPrimed) {
        const savedCursor = localStorage.getItem("monad.fleetnetCursor");
        const latest = entries.at(-1);
        const recentPriorityMuster = latest && Number(latest.priority || 0) >= 7
          && Date.now() - Date.parse(latest.at) < 15 * 60 * 1000;
        fleetnetCursor = savedCursor || (recentPriorityMuster ? entries.at(-2)?.id || null : latest?.id || null);
        fleetnetPrimed = true;
      }
      const cursorIndex = entries.findIndex((entry) => entry.id === fleetnetCursor);
      const incoming = fleetnetCursor === null ? entries.slice(-1)
        : cursorIndex >= 0 ? entries.slice(cursorIndex + 1) : entries.slice(-1);
      if (!wardroomAudioArmed || Date.now() - wardroomAudioArmedAt < 4000) return;
      for (const entry of incoming) {
        if (Number(entry.priority || 0) < 4) continue;
        const source = entry.from === "captain" ? "Captain" : String(entry.from || "FleetNet");
        speakLocally(`FleetNet. ${source}. ${entry.text}`);
        addRow("lifecycle", "fleetnet", `${source} · ${entry.text}`);
        fleetnetState.textContent = `FleetNet sounded · ${source} · priority ${entry.priority}`;
        fleetnetState.classList.add("ready");
      }
      if (entries.length) {
        fleetnetCursor = entries.at(-1).id;
        localStorage.setItem("monad.fleetnetCursor", fleetnetCursor);
      }
    } catch (error) {
      fleetnetState.textContent = `FleetNet receiver fault · ${error.message}`;
      fleetnetState.classList.remove("ready");
    }
  }
  pollFleetnet();
  window.setInterval(pollFleetnet, 3000);
  refresh();
})();

// Universal helm: one low-friction entrance to every Captain posture and
// active command surface. This is navigation plus command routing, not a
// second conversation or copied state.
(function wireHelmPalette() {
  const palette = document.getElementById("command-palette");
  const openButton = document.getElementById("helm-palette-open");
  const paletteInput = document.getElementById("command-palette-input");
  const choices = Array.from(document.querySelectorAll(".command-choice"));
  const telemetryButton = document.getElementById("telemetry-toggle");
  if (!palette || !paletteInput || !openButton) return;

  function close() { palette.hidden = true; paletteInput.value = ""; choices.forEach((choice) => { choice.hidden = false; }); }
  function open() { palette.hidden = false; requestAnimationFrame(() => paletteInput.focus()); }
  function select(station) {
    if (window.selectCaptainStation) window.selectCaptainStation(station);
    close();
    setTimeout(() => {
      if (station === "research") document.getElementById("concept-input")?.focus();
      else input.focus();
    }, 80);
  }
  openButton.addEventListener("click", open);
  palette.addEventListener("click", (event) => { if (event.target === palette) close(); });
  choices.forEach((choice) => choice.addEventListener("click", () => select(choice.dataset.helmStation)));
  paletteInput.addEventListener("input", () => {
    const query = paletteInput.value.trim().toLowerCase();
    choices.forEach((choice) => { choice.hidden = Boolean(query && !choice.textContent.toLowerCase().includes(query)); });
  });
  paletteInput.addEventListener("keydown", (event) => {
    if (event.key === "Escape") { close(); return; }
    if (event.key !== "Enter") return;
    event.preventDefault();
    const text = paletteInput.value.trim();
    const visible = choices.find((choice) => !choice.hidden);
    const exact = choices.find((choice) => choice.dataset.helmStation === text.toLowerCase());
    if (exact || (!text && visible)) { select((exact || visible).dataset.helmStation); return; }
    close();
    const station = document.body.dataset.captainStation;
    if (station === "research") {
      const conceptInput = document.getElementById("concept-input");
      if (conceptInput) { conceptInput.value = text; document.getElementById("concept-form")?.requestSubmit(); }
    } else {
      input.value = text; submitDirective();
    }
  });
  document.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
      event.preventDefault(); palette.hidden ? open() : close();
    } else if (event.key === "Escape" && !palette.hidden) close();
  });
  telemetryButton?.addEventListener("click", () => {
    document.body.classList.toggle("telemetry-open");
    const openState = document.body.classList.contains("telemetry-open");
    telemetryButton.textContent = openState ? "◆ SYSTEMS" : "◇ SYSTEMS";
    telemetryButton.setAttribute("aria-pressed", String(openState));
  });
})();
let latestHandoffFile = null;
const activityLights = {};
for (const el of document.querySelectorAll(".status-widget")) {
  activityLights[el.dataset.cat] = { el, count: 0, timer: null };
}

let authenticated = false;
let statusPollHandle = null;
let coursePollHandle = null;
let streamSource = null;
window.captainBridgeReady = false;

function timestamp() {
  return new Date().toTimeString().slice(0, 8);
}

function flashTile(valueEl) {
  const tile = valueEl.closest(".tile");
  tile.classList.remove("flash");
  void tile.offsetWidth;
  tile.classList.add("flash");
}

function setTelemetry(el, value) {
  if (el.textContent === String(value)) return;
  el.textContent = value;
  flashTile(el);
}

function fmtUptime(seconds) {
  const s = Math.floor(seconds);
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  return `${h}h${m}m${sec}s`;
}

function shortThread(threadId) {
  return threadId ? threadId.slice(0, 8) : "—";
}

// An image card that just rendered was getting shoved out of the visible
// terminal within a second by the next chat row's own auto-scroll-to-
// bottom -- still in the DOM, just immediately unseeable. Pin the view in
// place for a few seconds after an image lands instead of always
// snapping to the newest row.
let imagePinnedUntil = 0;

function followTerminalBottom() {
  if (Date.now() < imagePinnedUntil) return;
  terminalEl.scrollTop = terminalEl.scrollHeight;
}

// Deterministic per-message "living glyph" -- same 5x5 symmetric block
// identicon already shipped in the Document Viewer (console/documents.html),
// ported here so every Captain row carries its own hashed visual signature
// instead of only the bare word "captain". Hashed from the row's own text,
// not stored anywhere -- matches this console's live-off-disk rule.
function hashString(s) {
  let h = 5381;
  for (let i = 0; i < s.length; i++) h = ((h << 5) + h + s.charCodeAt(i)) | 0;
  return Math.abs(h);
}

function identiconSvg(seed, size) {
  const h = hashString(seed);
  const hue = h % 360;
  const color = `hsl(${hue}, 62%, 58%)`;
  const cols = 3, rows = 5, cell = size / rows;
  const cells = [];
  let bit = 0;
  for (let y = 0; y < rows; y++) {
    for (let x = 0; x < cols; x++) {
      bit++;
      if (((h >> bit) & 1) !== 1) continue;
      cells.push([x, y]);
      if (x < cols - 1) cells.push([2 * cols - 2 - x, y]);
    }
  }
  const rects = cells.map(([x, y]) => `<rect x="${x * cell}" y="${y * cell}" width="${cell}" height="${cell}" fill="${color}"/>`).join("");
  return `<svg class="glyph" width="${size}" height="${size}" viewBox="0 0 ${cell * 5} ${cell * rows}" style="border-radius:2px;background:rgba(255,255,255,0.06);flex:none;">${rects}</svg>`;
}

function addRow(cssClass, src, body) {
  if (["agent", "injected"].includes(cssClass)) document.body.classList.add("has-captain-dialogue");
  const row = document.createElement("div");
  row.className = `row ${cssClass}`;
  const ts = document.createElement("span");
  ts.className = "ts";
  ts.textContent = timestamp();
  const srcEl = document.createElement("span");
  srcEl.className = "src";
  if (src === "captain") srcEl.innerHTML = identiconSvg(body || cssClass + ts.textContent, 13);
  srcEl.append(document.createTextNode(src));
  const bodyEl = document.createElement("span");
  bodyEl.className = "body";
  bodyEl.textContent = body;
  row.append(ts, srcEl, bodyEl);
  terminalEl.insertBefore(row, promptRowEl);
  followTerminalBottom();
  return bodyEl;
}

function openImageStage(url, label) {
  imageStageImage.src = url;
  imageStageImage.alt = label || "Captain image artifact";
  imageStageImage.classList.remove("actual");
  imageStageTitle.textContent = label || "Captain image artifact";
  imageStageOpen.href = url;
  imageStage.hidden = false;
  document.body.style.overflow = "hidden";
  imageStageClose.focus();
}

function closeImageStage() {
  if (imageStage.hidden) return;
  imageStage.classList.add("closing");
  window.setTimeout(() => {
    imageStage.hidden = true;
    imageStage.classList.remove("closing");
    imageStageImage.src = "";
    document.body.style.overflow = "";
    input.focus();
  }, 180);
}

function addImageArtifact(url, label = "Captain image artifact") {
  const bodyEl = addRow("agent image-artifact", "captain", "");
  const button = document.createElement("button");
  button.type = "button";
  button.className = "image-preview";
  button.setAttribute("aria-label", `Open image preview: ${label}`);
  const image = document.createElement("img");
  image.src = url;
  image.alt = label;
  image.loading = "lazy";
  const badge = document.createElement("span");
  badge.className = "artifact-label";
  badge.textContent = "CAPTAIN · IMAGE";
  button.append(image, badge);
  button.addEventListener("click", (event) => {
    event.stopPropagation();
    openImageStage(url, label);
  });
  bodyEl.appendChild(button);
  imagePinnedUntil = Date.now() + 5000;
  bodyEl.closest(".row")?.scrollIntoView({ block: "center", behavior: "smooth" });
  return bodyEl;
}

// Live wiring for the Semantic Text Metamorphosis capability
// (console/assets/js/semantic-metamorphosis.js, capability card
// semantic-metamorphosis.capability.json): captain-kernel.md documents this
// trigger syntax so the Captain itself can compose a real, physics-driven
// choreography from plain conversational text -- not a single fixed
// preset. The tag is stripped from the displayed message; phrases named in
// it must already appear verbatim elsewhere in the same message (the
// component locates and lifts real rendered text, it doesn't fabricate the
// source words).
//
// General form: ⟦fx: phrases="a, b, c" | op1(args) | op2(args) | ...⟧
// Legacy form (kept working): ⟦metamorphose: phrases="a, b, c" => "result"⟧
const FX_TRIGGER = /⟦fx:\s*([^⟧]+)⟧\s*/i;
const LEGACY_METAMORPHOSIS_TRIGGER = /⟦metamorphose:\s*phrases="([^"]+)"\s*=>\s*"([^"]+)"⟧\s*/i;

const FX_POSITIONAL_KEY = { orbit: "turns", scatter: "radius", shed: "fraction", morph: "to", merge: "into", pulse: "strength", crystallize: "glyph", trail: "on" };

function parseFxStepArgs(argsStr) {
  const args = {};
  const parts = (argsStr.match(/(?:[^,"]+|"[^"]*")+/g) || []).map((s) => s.trim()).filter(Boolean);
  parts.forEach((part, i) => {
    const kv = /^([a-zA-Z_]+)\s*=\s*(.+)$/.exec(part);
    let key, raw;
    if (kv) { key = kv[1]; raw = kv[2].trim(); } else { key = `_pos${i}`; raw = part; }
    let val;
    if (/^".*"$/.test(raw)) val = raw.slice(1, -1);
    else if (raw !== "" && !isNaN(Number(raw))) val = Number(raw);
    else val = raw;
    args[key] = val;
  });
  return args;
}

function remapFxPositional(op, args) {
  const posKey = FX_POSITIONAL_KEY[op];
  if (posKey && args._pos0 !== undefined && args[posKey] === undefined) args[posKey] = args._pos0;
  Object.keys(args).forEach((k) => { if (k.startsWith("_pos")) delete args[k]; });
  return args;
}

function parseFxTrigger(text) {
  const m = FX_TRIGGER.exec(text);
  if (!m) return null;
  const segments = m[1].split("|").map((s) => s.trim()).filter(Boolean);
  const first = segments.length ? /^phrases\s*=\s*"([^"]*)"$/i.exec(segments[0]) : null;
  if (!first) return null;
  const phrases = first[1].split(",").map((p) => p.trim()).filter(Boolean).slice(0, 6);
  const steps = [];
  let resultText = "";
  for (let i = 1; i < segments.length; i++) {
    const seg = /^([a-zA-Z_]+)(?:\(([^)]*)\))?$/.exec(segments[i]);
    if (!seg) continue;
    const op = seg[1];
    const args = remapFxPositional(op, parseFxStepArgs(seg[2] || ""));
    if (args.to) resultText = args.to;
    if (args.into) resultText = args.into;
    steps.push({ op, args });
  }
  return { matchedText: m[0], phrases, steps, resultText };
}

function runMetamorphosisTrigger(bodyEl) {
  if (!window.liveCaptainMetamorphosis) return;
  const text = bodyEl.textContent || "";

  const fx = parseFxTrigger(text);
  if (fx) {
    bodyEl.textContent = text.replace(fx.matchedText, "");
    if (!fx.phrases.length || !fx.steps.length) return;
    const landTarget = document.createElement("span");
    landTarget.className = "metamorphosis-land-wrap";
    bodyEl.parentElement.appendChild(landTarget);
    // A trigger arriving while a previous metamorphosis is still animating
    // is dropped, not queued (the component only runs one choreography at
    // a time) -- catch that rejection so it doesn't surface as an
    // unhandled promise error; the tag is still stripped from the message
    // either way so the raw syntax never leaks into the visible transcript.
    window.liveCaptainMetamorphosis.run(fx.steps, {
      sourceContainer: bodyEl,
      phrases: fx.phrases,
      resultText: fx.resultText,
      landTarget,
    }).done.catch(() => {});
    return;
  }

  const legacy = LEGACY_METAMORPHOSIS_TRIGGER.exec(text);
  if (legacy) {
    const phrases = legacy[1].split(",").map((p) => p.trim()).filter(Boolean).slice(0, 6);
    const resultText = legacy[2].trim();
    bodyEl.textContent = text.replace(LEGACY_METAMORPHOSIS_TRIGGER, "");
    if (!phrases.length || !resultText) return;
    const landTarget = document.createElement("span");
    landTarget.className = "metamorphosis-land-wrap";
    bodyEl.parentElement.appendChild(landTarget);
    window.liveCaptainMetamorphosis.perform({ sourceContainer: bodyEl, phrases, resultText, landTarget }).done.catch(() => {});
  }
}

function imageArtifactsFrom(value, opts = {}, found = new Map(), depth = 0) {
  // scanFreeText: only true for the Captain's actual agentMessage prose.
  // Tool/reasoning/command items get structured-field detection only
  // (an explicit image_url/src key) -- this repo is full of incidental
  // image file paths in command output and reasoning text (web/toys,
  // GLB intake, image-gen tooling), and a loose extension regex over
  // every completed item's every string field was matching those and
  // flooding the dialogue with false-positive preview cards. Bare local
  // filesystem paths are dropped entirely -- they aren't browser-fetchable
  // anyway, so matching them can only ever produce a broken image, never
  // a real preview.
  const { scanFreeText = true } = opts;
  const trustedImageUrl = (candidate) => /^(?:data:image\/|https?:\/\/|\/root-console-api\/api\/generated-image\/)/.test(candidate);
  if (depth > 5 || value == null) return found;
  if (typeof value === "string") {
    // The generated-image endpoint is server-validated and single-purpose
    // (server.py mints it only for paths resolved inside GENERATED_IMAGE_DIR),
    // so it's safe to recognize wherever it appears -- not just under the
    // known field-name allow-list below, and not just in agentMessage prose.
    for (const match of value.matchAll(/\/root-console-api\/api\/generated-image\/[A-Za-z0-9_-]+/g)) {
      if (!found.has(match[0])) found.set(match[0], "Captain image artifact");
    }
    if (scanFreeText) {
      const markdownImages = value.matchAll(/!\[([^\]]*)\]\(([^\s)]+)(?:\s+["'][^"']*["'])?\)/g);
      for (const match of markdownImages) found.set(match[2], match[1] || "Captain image artifact");
      const imageUrls = value.match(/https?:\/\/[^\s<>'"()]+\.(?:avif|gif|jpe?g|png|webp)(?:\?[^\s<>'"()]*)?/gi) || [];
      for (const url of imageUrls) if (!found.has(url)) found.set(url, "Captain image artifact");
      if (value.startsWith("data:image/")) found.set(value, "Captain image artifact");
    }
    return found;
  }
  if (Array.isArray(value)) {
    for (const entry of value) imageArtifactsFrom(entry, opts, found, depth + 1);
    return found;
  }
  if (typeof value === "object") {
    const label = value.output_hint || value.prompt || value.alt || value.title;
    for (const [key, entry] of Object.entries(value)) {
      if (typeof entry === "string" && /^(image_url|imageUrl|url|src|data|path)$/.test(key) && trustedImageUrl(entry)) {
        found.set(entry, typeof label === "string" ? label : "Captain image artifact");
      } else {
        imageArtifactsFrom(entry, opts, found, depth + 1);
      }
    }
  }
  return found;
}

imageStageClose.addEventListener("click", closeImageStage);
imageStage.addEventListener("click", (event) => {
  if (event.target === imageStage || event.target === imageStageCanvas) closeImageStage();
});
imageStageImage.addEventListener("click", () => imageStageImage.classList.toggle("actual"));
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && !imageStage.hidden) closeImageStage();
  if (event.key === "Escape" && !handoffDetail.hidden) closeHandoffDetail();
});

function closeHandoffDetail() {
  handoffDetail.hidden = true;
  handoffDetailBody.textContent = "";
}

async function openHandoffDetail(file) {
  handoffDetailTitle.textContent = file;
  handoffDetailBody.textContent = "loading…";
  handoffDetail.hidden = false;
  handoffDetailClose.focus();
  try {
    const response = await fetch(`${API_BASE}/handoffs/detail?file=${encodeURIComponent(file)}`);
    const body = await response.json();
    handoffDetailBody.textContent = response.ok ? body.content : (body.error || `HTTP ${response.status}`);
  } catch (err) {
    handoffDetailBody.textContent = String(err);
  }
}

handoffDetailClose.addEventListener("click", closeHandoffDetail);
handoffDetail.addEventListener("click", (event) => {
  if (event.target === handoffDetail) closeHandoffDetail();
});

function fmtHandoffTimestamp(ts) {
  // ts is YYYYMMDDTHHMMSSZ
  const match = /^(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})Z$/.exec(ts || "");
  if (!match) return ts || "—";
  const [, y, mo, d, h, mi, s] = match;
  return `${y}-${mo}-${d} ${h}:${mi}:${s}Z`;
}

function renderHandoffs(items) {
  handoffsList.innerHTML = "";
  latestHandoffFile = items.length ? items[0].file : null;
  dispatchViewLatest.disabled = !latestHandoffFile;
  if (!items.length) {
    const empty = document.createElement("div");
    empty.className = "h-empty";
    empty.textContent = "No handoffs yet.";
    handoffsList.appendChild(empty);
    return;
  }
  for (const item of items) {
    const row = document.createElement("div");
    row.className = "h-row";
    row.tabIndex = 0;

    const head = document.createElement("div");
    head.className = "h-head";
    const task = document.createElement("span");
    task.className = "h-task";
    task.textContent = `${item.agent} · ${item.taskId}`;
    const badge = document.createElement("span");
    badge.className = `h-badge${item.publicationState === "PUBLISHED" ? " published" : ""}`;
    badge.textContent = item.publicationState === "PUBLISHED" ? "published" : "local-only";
    head.appendChild(task);
    head.appendChild(badge);

    const meta = document.createElement("div");
    meta.className = "h-meta";
    meta.textContent = `${fmtHandoffTimestamp(item.timestamp)} · ${item.branch || "—"}`;

    const path = document.createElement("div");
    path.className = "h-path";
    path.textContent = item.path;

    row.appendChild(head);
    row.appendChild(meta);
    row.appendChild(path);
    row.addEventListener("click", () => openHandoffDetail(item.file));
    row.addEventListener("keydown", (event) => {
      if (event.key === "Enter") openHandoffDetail(item.file);
    });
    handoffsList.appendChild(row);
  }
}

async function pollHandoffs() {
  try {
    const response = await fetch(`${API_BASE}/handoffs`);
    if (response.status === 401) return; // pollStatus's own 401 handling covers the gate
    const body = await response.json();
    renderHandoffs(body.handoffs || []);
  } catch (err) {
    // handoffs endpoint unreachable; list just goes stale
  }
}

function fmtShipLogTimestamp(epochSeconds) {
  if (!epochSeconds) return "—";
  const d = new Date(epochSeconds * 1000);
  return d.toISOString().replace("T", " ").replace(/\.\d+Z$/, "Z");
}

function renderShipLog(entries) {
  shipLogList.innerHTML = "";
  if (!entries.length) {
    const empty = document.createElement("div");
    empty.className = "sl-empty";
    empty.textContent = "Nothing on disk yet.";
    shipLogList.appendChild(empty);
    return;
  }
  for (const entry of entries) {
    const row = document.createElement("div");
    row.className = "sl-row";

    const head = document.createElement("div");
    head.className = "sl-head";
    const title = document.createElement("span");
    title.className = "sl-title";
    title.textContent = entry.title || entry.file;
    const source = document.createElement("span");
    source.className = "sl-source";
    source.textContent = entry.source;
    head.appendChild(title);
    head.appendChild(source);

    const meta = document.createElement("div");
    meta.className = "sl-meta";
    meta.textContent = `${fmtShipLogTimestamp(entry.timestamp)} · ${entry.file}`;

    const excerpt = document.createElement("div");
    excerpt.className = "sl-excerpt";
    excerpt.textContent = entry.excerpt || "";

    row.appendChild(head);
    row.appendChild(meta);
    row.appendChild(excerpt);
    shipLogList.appendChild(row);
  }
}

async function pollShipLog() {
  try {
    const response = await fetch(`${API_BASE}/ship-log`);
    if (response.status === 401) return;
    const body = await response.json();
    renderShipLog(body.entries || []);
  } catch (err) {
    // ship-log endpoint unreachable; list just goes stale
  }
}

shipLogRefresh.addEventListener("click", pollShipLog);
handoffsRefresh.addEventListener("click", pollHandoffs);
dispatchViewLatest.addEventListener("click", () => {
  if (latestHandoffFile) openHandoffDetail(latestHandoffFile);
});

let activityLogOpen = false;
let activityEntryCount = 0;
const ACTIVITY_LOG_CAP = 60;

function pulseLight(cat, summary) {
  const light = activityLights[cat];
  if (!light) return;
  light.count += 1;
  light.el.querySelector(".count").textContent = light.count;
  light.el.querySelector(".caption").textContent = summary || "";
  light.el.classList.add("pulse");
  clearTimeout(light.timer);
  // Long enough to actually read the caption, short enough to stay "blinky"
  // rather than becoming another wall of standing text.
  light.timer = setTimeout(() => light.el.classList.remove("pulse"), 2400);
}

function recordActivity(cat, label, summary) {
  pulseLight(cat, summary);
  if (activityEntryCount === 0) activityLog.innerHTML = "";
  const row = document.createElement("div");
  row.className = "a-row";
  row.innerHTML = `<span class="ts">${timestamp()}</span><span class="cat">${label}</span><span class="sum"></span>`;
  row.querySelector(".sum").textContent = summary;
  activityLog.insertBefore(row, activityLog.firstChild);
  activityEntryCount += 1;
  while (activityLog.children.length > ACTIVITY_LOG_CAP) {
    activityLog.removeChild(activityLog.lastChild);
  }
}

activityToggle.addEventListener("click", () => {
  activityLogOpen = !activityLogOpen;
  activityLog.classList.toggle("open", activityLogOpen);
  activityToggle.textContent = activityLogOpen ? "activity log ▴" : "activity log ▾";
});

const SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"];
let thinkingBodyEl = null;
let thinkingInterval = null;

function startThinking() {
  if (thinkingBodyEl) return;
  thinkingBodyEl = addRow("thinking", "captain", SPINNER_FRAMES[0]);
  let frame = 0;
  thinkingInterval = setInterval(() => {
    frame = (frame + 1) % SPINNER_FRAMES.length;
    thinkingBodyEl.textContent = SPINNER_FRAMES[frame];
  }, 80);
}

function stopThinking() {
  if (thinkingInterval) {
    clearInterval(thinkingInterval);
    thinkingInterval = null;
  }
  if (thinkingBodyEl) {
    thinkingBodyEl.closest(".row")?.remove();
    thinkingBodyEl = null;
  }
}

async function pollStatus() {
  try {
    const response = await fetch(`${API_BASE}/status`);
    if (response.status === 401) {
      showLoginGate();
      return;
    }
    if (!authenticated) onAuthenticated();
    const status = await response.json();
    telPid.textContent = status.pid;
    telUptime.textContent = fmtUptime(status.uptime_seconds);
    setTelemetry(telThread, shortThread(status.active_thread_id));
    setTelemetry(telSubs, status.subscriber_count);
  } catch (err) {
    // status endpoint unreachable; telemetry goes stale, connection indicator still reflects reality
  }
  try {
    const bearingResponse = await fetch(`${LIVE_CAPTAIN_API_BASE}/status`);
    if (!bearingResponse.ok) {
      bearingIndicatorEl.textContent = `Live Captain — status unavailable (HTTP ${bearingResponse.status})`;
      return;
    }
    const bearing = await bearingResponse.json();
    bearingIndicatorEl.textContent =
      `${bearing.label} · kernel ${bearing.kernel_digest.slice(0, 8)} · ` +
      `bearing ${bearing.bearing_digest.slice(0, 8)} · restarts ${bearing.restart_count}`;
  } catch (err) {
    bearingIndicatorEl.textContent = "Live Captain — status unavailable";
  }
}

function showLoginGate() {
  authenticated = false;
  window.captainBridgeReady = false;
  window.dispatchEvent(new Event("captain-bridge-unavailable"));
  loginGate.classList.remove("hidden");
  if (streamSource) {
    streamSource.close();
    streamSource = null;
  }
  if (statusPollHandle) {
    clearInterval(statusPollHandle);
    statusPollHandle = null;
  }
  if (coursePollHandle) {
    clearInterval(coursePollHandle);
    coursePollHandle = null;
  }
}

function onAuthenticated() {
  if (authenticated) return;
  authenticated = true;
  loginGate.classList.add("hidden");
  loginError.textContent = "";
  connect();
  if (!statusPollHandle) statusPollHandle = setInterval(pollStatus, 4000);
  pollHandoffs();
  pollShipLog();
  refreshBridgeCourse();
  if (!coursePollHandle) coursePollHandle = window.setInterval(refreshBridgeCourse, 30000);
  input.focus();
}

loginForm.addEventListener("submit", async (submitEvent) => {
  submitEvent.preventDefault();
  const password = loginPassword.value;
  loginPassword.value = "";
  try {
    const response = await fetch(`${API_BASE}/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password }),
    });
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      loginError.textContent = body.error || `HTTP ${response.status}`;
      return;
    }
    onAuthenticated();
  } catch (err) {
    loginError.textContent = String(err);
  }
});

function summarizeItem(item) {
  if (item.type === "agentMessage") return item.text || "";
  if (item.type === "userMessage") {
    return (item.content || []).map((c) => c.text || "").join(" ");
  }
  if (item.type === "reasoning") return item.text || item.summary || "(reasoning)";
  if (item.type === "commandExecution" || item.type === "command") {
    return item.command || item.text || "(command)";
  }
  const stringField = Object.entries(item).find(
    ([key, value]) => typeof value === "string" && value && key !== "type" && key !== "id"
  );
  return stringField ? stringField[1] : "";
}

function categoryForItemType(type) {
  return type === "reasoning" ? "reasoning" : "tool";
}

const streamingRows = new Map();

// Image-gen status widget: separate from the generic tool/reasoning lights
// because generation can run long, and the point is "still obviously
// working," not a 2.4s blip like the other activity pulses.
const imageGenWidget = document.querySelector('.status-widget[data-cat="image"]');
const imageGenCaption = imageGenWidget.querySelector(".caption");
const imageGenCountEl = imageGenWidget.querySelector(".count");
let imageGenTimer = null;
let imageGenActiveItemId = null;
let imageGenDoneCount = 0;

function looksLikeImageGen(item) {
  if (!item) return false;
  const haystack = JSON.stringify(item).toLowerCase();
  return /image[_-]?gen|generate[_-]?image|gpt-image|generated_images/.test(haystack);
}

function startImageGenIndicator(itemId) {
  imageGenActiveItemId = itemId || imageGenActiveItemId || true;
  if (imageGenTimer) return;
  imageGenWidget.classList.remove("done-flash");
  imageGenWidget.classList.add("spinning");
  let frame = 0;
  imageGenCaption.textContent = `${SPINNER_FRAMES[0]} generating…`;
  imageGenTimer = setInterval(() => {
    frame = (frame + 1) % SPINNER_FRAMES.length;
    imageGenCaption.textContent = `${SPINNER_FRAMES[frame]} generating…`;
  }, 80);
}

function stopImageGenIndicator(doneLabel) {
  if (imageGenTimer) {
    clearInterval(imageGenTimer);
    imageGenTimer = null;
  }
  const wasActive = imageGenActiveItemId != null;
  imageGenActiveItemId = null;
  imageGenWidget.classList.remove("spinning");
  if (doneLabel && wasActive) {
    imageGenDoneCount += 1;
    imageGenCountEl.textContent = imageGenDoneCount;
    imageGenCaption.textContent = doneLabel;
    imageGenWidget.classList.add("done-flash");
    setTimeout(() => imageGenWidget.classList.remove("done-flash"), 2400);
  } else {
    imageGenCaption.textContent = "";
  }
}

function handleCodexEvent(event) {
  const method = event.method;
  const params = event.params || {};

  if (method === "item/agentMessage/delta") {
    setCaptainPresence("thinking", "Forming the response live…");
    let bodyEl = streamingRows.get(params.itemId);
    if (!bodyEl) {
      stopThinking();
      bodyEl = addRow("agent", "captain", "");
      streamingRows.set(params.itemId, bodyEl);
    }
    bodyEl.textContent += params.delta || "";
    followTerminalBottom();
    return;
  }

  if (method === "item/completed") {
    const item = params.item || {};
    if (item.type === "agentMessage") {
      stopThinking();
      let bodyEl = streamingRows.get(item.id);
      if (!bodyEl) bodyEl = addRow("agent", "captain", "");
      bodyEl.textContent = item.text || "";
      streamingRows.delete(item.id);
      for (const [url, label] of imageArtifactsFrom(item, { scanFreeText: true })) addImageArtifact(url, label);
      runMetamorphosisTrigger(bodyEl);
      followTerminalBottom();
      prepareCaptainSpeech(item.text || "");
      return;
    }
    if (item.type === "userMessage") return;
    const artifacts = imageArtifactsFrom(item, { scanFreeText: false });
    if (artifacts.size) {
      stopThinking();
      stopImageGenIndicator("✓ image ready");
      for (const [url, label] of artifacts) addImageArtifact(url, label);
      return;
    }
    if (imageGenActiveItemId != null && (item.id === imageGenActiveItemId || looksLikeImageGen(item))) {
      stopImageGenIndicator();
    }
    recordActivity(categoryForItemType(item.type), item.type || "item", summarizeItem(item) || "(completed)");
    return;
  }

  if (method === "item/started") {
    // The spinner already communicates liveness, and the completed event
    // for this same item lands moments later with an actual summary --
    // logging both would double every tool call in the activity log. The
    // image-gen widget is the one exception: it needs the start signal
    // because generation can run long and "still working" is the point.
    const item = params.item || {};
    if (looksLikeImageGen(item)) startImageGenIndicator(item.id);
    return;
  }

  if (method === "turn/started") {
    setActivePairMove("Carrying Admiral intent through the live vessel…");
    recordActivity("thread", "turn", "started");
    return;
  }
  if (method === "turn/completed") {
    stopThinking();
    stopImageGenIndicator();
    const turn = params.turn || {};
    const status = turn.status || "completed";
    recordActivity("thread", "turn", `completed (${status})`);
    window.dispatchEvent(new CustomEvent("captain-turn-completed", { detail: { status } }));
    if (status === "failed") {
      setActivePairMove("Preserving fault evidence and selecting recovery.");
      setCaptainPresence("fault", "Turn failed — evidence preserved.");
      // Turn.error is only populated when status is "failed" -- it's the
      // one place the actual reason lives. Previously this branch discarded
      // it and showed only the bare word "failed", making every failure
      // unexplainable after the fact.
      const error = turn.error || {};
      const detail = [error.message, error.additionalDetails].filter(Boolean).join(" -- ") || "no error detail provided by Codex";
      addRow("error", "error", `Turn failed: ${detail}`);
    } else if (!pendingCaptainSpeech) {
      setCaptainPresence("ready", "Turn complete · maintaining the shared watch.");
      refreshBridgeCourse();
    }
    return;
  }
  if (method === "thread/status/changed") {
    recordActivity("thread", "thread", (params.status || {}).type || "status changed");
    return;
  }
  if (method === "thread/tokenUsage/updated") {
    const total = (params.tokenUsage || {}).total || {};
    setTelemetry(telTokens, `${total.inputTokens ?? 0} in / ${total.outputTokens ?? 0} out`);
    return;
  }
  if (method === "account/rateLimits/updated") {
    const primary = (params.rateLimits || {}).primary || {};
    setTelemetry(telRatelimit, primary.usedPercent != null ? `${primary.usedPercent}%` : "—");
    return;
  }
  if (method === "mcpServer/startupStatus/updated") {
    recordActivity("mcp", `mcp:${params.name}`, params.status || "");
    return;
  }
  if (method === "thread/started") return;

  // Unknown/future protocol methods -- log them rather than silently
  // dropping (which is how noise-suppression regressed once already),
  // but keep them out of chat.
  recordActivity("thread", method, JSON.stringify(params));
}


// --- Captain speech --------------------------------------------------------
// The Captain's own replies, spoken in its own voice. Wired 2026-08-05.
//
// Everything this needs already existed: /api/turn returns the reply over
// SSE, /voice-api/render makes a 24kHz WAV, the browser plays it. This
// connects four working things; it builds no new machinery.
//
// Both endpoints sit behind the same forward_auth as the rest of /root. That
// boundary protects private Captain traffic; voice generation itself is
// ungated by spend or duration and retains usage accounting only.
//
// captain.monad / Kore — measured authority. Distinct from the front page
// Buddy's captain.alpha / Puck, so you can tell who is talking.
const CAPTAIN_VOICE_KEY = "monad.captainVoice";
// Default ON. Admiral, 2026-08-05: "Allow live captain to speak." Off was
// the cautious default while the render path was unproven; it is proven now
// (28.8s of real WAV from live state), so silence is no longer the sensible
// starting position. localStorage still wins if you have chosen either way.
const captainVoiceStored = localStorage.getItem(CAPTAIN_VOICE_KEY);
let captainVoiceOn = captainVoiceStored === null ? true : captainVoiceStored === "on";
let captainAudio = null;
let captainVoiceContext = null;

function unlockCaptainVoice() {
  try {
    const Context = window.AudioContext || window.webkitAudioContext;
    if (!Context) return null;
    if (!captainVoiceContext) captainVoiceContext = new Context();
    if (captainVoiceContext.state === "suspended") captainVoiceContext.resume();
    return captainVoiceContext;
  } catch (_) { return null; }
}

async function playCaptainArtifact(url, onDone) {
  const context = captainVoiceContext;
  if (!context || context.state === "closed") {
    const audio = new Audio(url);
    captainAudio = audio;
    audio.onended = audio.onerror = onDone;
    await audio.play();
    return;
  }
  const response = await fetch(url);
  if (!response.ok) throw new Error(`audio artifact HTTP ${response.status}`);
  const buffer = await context.decodeAudioData(await response.arrayBuffer());
  const source = context.createBufferSource();
  let settled = false;
  const finish = () => {
    if (settled) return;
    settled = true;
    onDone();
  };
  source.buffer = buffer;
  source.connect(context.destination);
  source.onended = finish;
  captainAudio = { pause: () => { try { source.stop(); } catch (_) {} finish(); } };
  source.start();
}

function captainSpokenLead(text) {
  let spoken = String(text || "")
    .replace(/⟦(?:fx|metamorphose):[^⟧]*⟧/g, "")
    .replace(/!\[([^\]]*)\]\([^)]*\)/g, "$1")
    .replace(/\[([^\]]+)\]\([^)]*\)/g, "$1")
    .replace(/https?:\/\/\S+/g, "")
    .replace(/[`*_#>|]/g, " ")
    .replace(/^\s*[-+]\s+/gm, "")
    .replace(/\s+/g, " ")
    .trim();
  if (spoken.length <= 320) return spoken;
  const lead = spoken.slice(0, 320);
  const sentenceEnd = Math.max(lead.lastIndexOf(". "), lead.lastIndexOf("! "), lead.lastIndexOf("? "));
  return (sentenceEnd >= 100 ? lead.slice(0, sentenceEnd + 1) : lead.replace(/\s+\S*$/, "")) + "…";
}

function setCaptainVoice(on) {
  captainVoiceOn = on;
  localStorage.setItem(CAPTAIN_VOICE_KEY, on ? "on" : "off");
  const btn = document.getElementById("captain-voice-toggle");
  if (btn) {
    btn.classList.toggle("on", on);
    btn.textContent = on ? "⚓ Voice: on" : "⚓ Voice: off";
  }
  if (!on && captainAudio) {
    captainAudio.pause();
    captainAudio = null;
    // Stopping speech is also a turn-taking action. Without this resume the
    // Live Bridge remained muted forever because a paused Audio element does
    // not fire `ended`.
    if (window.liveBridgeResumeAfterCaptain) window.liveBridgeResumeAfterCaptain();
  }
}

let pendingCaptainSpeech = "";
const consumedCaptainSpeech = new Set();

function prepareCaptainSpeech(text) {
  if (!captainVoiceOn || !text) {
    if (window.liveBridgeResumeAfterCaptain) window.liveBridgeResumeAfterCaptain();
    return;
  }
  pendingCaptainSpeech = captainSpokenLead(text);
  setCaptainPresence("speaking", "Preparing the spoken brief…");
  if (window.liveBridgePauseForCaptain) window.liveBridgePauseForCaptain();
  const btn = document.getElementById("captain-voice-toggle");
  if (btn) btn.textContent = "⚓ rendering…";
}

async function playCentralCaptainSpeech(event) {
  const btn = document.getElementById("captain-voice-toggle");
  const artifact = event.artifact || {};
  // The artifact arrives over both the live event stream and the direct
  // /api/turn response.  Either transport may be interrupted, but one render
  // must still produce exactly one playback in this console.
  const deliveryKey = artifact.audio_url || (event.thread_id ? `thread:${event.thread_id}` : "");
  if (deliveryKey && consumedCaptainSpeech.has(deliveryKey)) return;
  if (deliveryKey) consumedCaptainSpeech.add(deliveryKey);
  const spoken = artifact.transcript || pendingCaptainSpeech || captainSpokenLead(event.text || "");
  if (!captainVoiceOn) {
    pendingCaptainSpeech = "";
    if (window.liveBridgeResumeAfterCaptain) window.liveBridgeResumeAfterCaptain();
    return;
  }
  try {
    if (!artifact.audio_url) throw new Error("no artifact");
    if (captainAudio) captainAudio.pause();      // a new reply supersedes the old
    if (btn) btn.textContent = "⚓ speaking…";
    await playCaptainArtifact(artifact.audio_url, () => {
      if (btn) btn.textContent = "⚓ Voice: on";
      captainAudio = null;
      pendingCaptainSpeech = "";
      if (window.liveBridgeResumeAfterCaptain) window.liveBridgeResumeAfterCaptain();
      setCaptainPresence("ready", "Spoken brief complete · awaiting command.");
    });
  } catch (err) {
    if (btn) btn.textContent = "⚓ Voice: on (local)";
    speakLocally(spoken);
    pendingCaptainSpeech = "";
    addRow("error", "voice", `central Captain voice unavailable (${err.message}) — using local voice`);
  }
}

function speakLocally(text) {
  if (!window.speechSynthesis || !text) {
    if (window.liveBridgeResumeAfterCaptain) window.liveBridgeResumeAfterCaptain();
    return;
  }
  try {
    window.speechSynthesis.cancel();          // a new reply supersedes the old
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 0.97;
    utterance.pitch = 0.92;                   // lower: this is the Captain, not the Buddy
    utterance.onend = utterance.onerror = () => {
      if (window.liveBridgeResumeAfterCaptain) window.liveBridgeResumeAfterCaptain();
      setCaptainPresence("ready", "Spoken brief complete · awaiting command.");
    };
    window.speechSynthesis.speak(utterance);
  } catch (e) { /* no speech engine; nothing further to try */ }
}

function handleEvent(event) {
  if (event.type === "concept_room") {
    if (event.phase === "retrieving" || event.phase === "synthesizing") {
      setCaptainPresence("researching", event.phase === "retrieving" ? "Searching the documentary world…" : `Synthesizing ${event.evidence_count || 0} grounded passage(s)…`);
    } else if (event.phase === "failed") setCaptainPresence("fault", event.error || "Research turn failed.");
    else if (event.phase === "completed") setCaptainPresence("ready", "Concept memory preserved · awaiting inquiry.");
    window.dispatchEvent(new CustomEvent("concept-room-stream", { detail: event }));
    return;
  }
  // Concept Room owns its own room-scoped rendering. These events still flow
  // through the one Captain stream, but must never appear as injected Bridge
  // prompts or duplicate Captain answers.
  if (String(event.source || "").startsWith("concept-room:")) {
    window.dispatchEvent(new CustomEvent("concept-room-stream", { detail: event }));
    return;
  }
  if (event.type === "turn_started") {
    if (event.source !== "captain-watch") addRow("injected", "you", event.text);
    else addRow("tool", "watch", "Captain autonomous move started");
    return;
  }
  if (event.type === "codex_event") {
    handleCodexEvent(event);
    return;
  }
  if (event.type === "captain_handoff_available") {
    pollHandoffs();
    return;
  }
  if (event.type === "captain_speech") {
    if (event.phase === "ready") playCentralCaptainSpeech(event);
    else if (event.phase === "failed") playCentralCaptainSpeech({ text: event.text, artifact: {} });
    return;
  }
  if (event.type === "captain_objective" || event.type === "captain_watch_move") {
    refreshObjective();
    return;
  }
}

(function wireCaptainVoiceToggle() {
  const btn = document.getElementById("captain-voice-toggle");
  if (!btn) return;
  btn.addEventListener("click", () => {
    unlockCaptainVoice();
    setCaptainVoice(!captainVoiceOn);
  });
  setCaptainVoice(captainVoiceOn);   // restore the remembered choice
})();

// --- microphone: hold to speak --------------------------------------------
// The browser is the microphone, exactly as it is already the DAC. This is
// SpeechRecognition, the twin of the speechSynthesis the Captain already
// speaks through — same API, same page, no server, no model, no GPU, no
// install, no spend. Researched in
// docs/reports/2026-08-05-speech-to-text-two-way-captain.md.
//
// HOLD to talk, not always-listening. An open microphone in a room is a
// decision somebody should make deliberately, not inherit from a feature.
//
// Chrome streams audio to Google's recogniser. For a single-operator console
// behind a password that is an acceptable trade, and it is named here rather
// than left to be discovered.
(function wireMicrophone() {
  const btn = document.getElementById("mic-btn");
  if (!btn) return;
  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!Recognition) {
    // Graceful absence: the button says so and typing is unaffected.
    btn.classList.add("unsupported");
    btn.title = "This browser has no speech recognition — typing still works";
    btn.disabled = true;
    return;
  }
  btn.disabled = true;
  btn.textContent = "⏳";
  btn.setAttribute("aria-label", "Push to talk waiting for bridge");
  btn.title = "Waiting for the authenticated Captain bridge";

  let recognition = null;
  let listening = false;
  let pttHeld = false;
  let releasePending = false;
  let releaseTimer = null;
  let releaseCommitted = false;
  let pressStartedAt = 0;
  let recognitionBase = "";
  const fatalRecognitionErrors = new Set([
    "not-allowed", "service-not-allowed", "audio-capture",
  ]);

  function reportBridgeSignal(phase, pointer = "") {
    fetch(`${API_BASE}/bridge-signal`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        phase, pointer, live_mode: false,
        elapsed_ms: pressStartedAt ? Math.round(performance.now() - pressStartedAt) : 0,
      }), keepalive: true,
    }).catch(() => {});
  }

  function stop() {
    listening = false;
    btn.classList.remove("listening");
    btn.textContent = "🎙";
    if (recognition) { try { recognition.stop(); } catch (e) {} }
  }

  function commitReleasedUtterance() {
    if (!releasePending || releaseCommitted) return;
    releaseCommitted = true;
    releasePending = false;
    clearTimeout(releaseTimer);
    const text = activeCommandInput().value.trim();
    if (text) {
      reportBridgeSignal("commit");
      if (!commandDraftMode) submitDirective();
      else activeCommandInput().focus();
    } else activeCommandInput().focus();
  }

  function start() {
    if (listening) return;
    recognition = new Recognition();
    recognition.continuous = commandDraftMode;
    recognition.interimResults = true;   // paint it as you speak
    recognition.lang = "en-GB";
    recognitionBase = commandDraftMode ? activeCommandInput().value.trim() : "";

    recognition.onresult = (event) => {
      // SpeechRecognitionResultList is the recogniser's current authoritative
      // hypothesis set, not an append-only delta.  Chromium may replay result
      // slots (including final ones) with resultIndex pointing before text we
      // have already painted.  Appending those chunks recursively produced
      // "find / find your / find your own ..." boot-loop directives.  Rebuild
      // from indexed results every time so a revised hypothesis replaces its
      // predecessor and every spoken segment appears exactly once.
      let transcript = "";
      for (let i = 0; i < event.results.length; i++) {
        const chunk = event.results[i][0].transcript.trim();
        if (!chunk) continue;
        // The live provider sometimes returns cumulative hypotheses in
        // separate slots: "find", "find your", "find your own". Replace a
        // prefix with its longer form; join genuinely separate segments.
        if (!transcript) transcript = chunk;
        else if (chunk === transcript || chunk.startsWith(`${transcript} `)) transcript = chunk;
        else transcript = `${transcript} ${chunk}`;
      }
      // Show the live transcript in the real input, so you can see it hearing
      // you and correct before it goes anywhere.
      activeCommandInput().value = [recognitionBase, transcript].filter(Boolean).join(" ");
    };
    recognition.onerror = (event) => {
      reportBridgeSignal("recognition-error");
      releasePending = false;
      clearTimeout(releaseTimer);
      stop();
      if (fatalRecognitionErrors.has(event.error)) {
        btn.title = `Push-to-talk unavailable: ${event.error}`;
      }
      if (event.error !== "aborted" && event.error !== "no-speech") {
        addRow("error", "mic", `speech recognition: ${event.error}`);
      }
    };
    recognition.onend = () => {
      // Release fires stop(); whatever was heard is now in the input and is
      // sent from the pointerup handler, not from here — so a dropped
      // connection cannot silently submit something you did not finish.
      if (listening) stop();
      if (releasePending) setTimeout(commitReleasedUtterance, 80);
    };

    listening = true;
    btn.classList.add("listening");
    btn.textContent = "●";
    try {
      recognition.start();
      // Starting is synchronous admission, not proof of audio; onresult
      // remains the evidence that recognition actually heard something.
      reportBridgeSignal("recognition-start");
    } catch (e) { stop(); addRow("error", "mic", String(e)); }
  }

  // Hold anywhere on the button; release sends. Pointer events cover mouse,
  // pen and touch in one path.
  btn.addEventListener("pointerdown", (e) => {
    e.preventDefault();
    if (!authenticated || !window.captainBridgeReady || pttHeld) {
      btn.title = "Captain bridge is not ready yet";
      return;
    }
    pttHeld = true;
    pressStartedAt = performance.now();
    reportBridgeSignal("press", e.pointerType || "pointer");
    releasePending = false;
    releaseCommitted = false;
    try { btn.setPointerCapture(e.pointerId); } catch (_) {}
    unlockCaptainVoice();
    // Physical hold-to-talk is also barge-in: cut Captain output immediately.
    if (captainAudio) { captainAudio.pause(); captainAudio = null; }
    if (window.speechSynthesis) window.speechSynthesis.cancel();
    start();
  });
  const release = (event) => {
    if (!pttHeld) return;
    pttHeld = false;
    releasePending = true;
    reportBridgeSignal("release", event?.pointerType || "pointer");
    try { if (event && btn.hasPointerCapture(event.pointerId)) btn.releasePointerCapture(event.pointerId); } catch (_) {}
    stop();
    // onend is the authoritative flush boundary. This fallback covers browser
    // implementations that fail to emit onend after stop().
    releaseTimer = setTimeout(commitReleasedUtterance, 700);
  };
  btn.addEventListener("pointerup", release);
  btn.addEventListener("pointercancel", (event) => {
    pttHeld = false;
    releasePending = false;
    reportBridgeSignal("cancel", event.pointerType || "pointer");
    clearTimeout(releaseTimer);
    try { if (btn.hasPointerCapture(event.pointerId)) btn.releasePointerCapture(event.pointerId); } catch (_) {}
    stop();
    input.focus();
  });
  window.addEventListener("blur", () => {
    // Losing the physical interaction boundary cancels; it never submits.
    if (!pttHeld) return;
    pttHeld = false;
    releasePending = false;
    clearTimeout(releaseTimer);
    stop();
  });
  window.addEventListener("captain-bridge-ready", () => {
    btn.disabled = false;
    btn.textContent = "🎙";
    btn.setAttribute("aria-label", "Hold to speak, release to send");
    btn.title = "Hold to speak · release to send · press again to interrupt";
    reportBridgeSignal("armed");
  });
  window.addEventListener("captain-bridge-unavailable", () => {
    btn.disabled = true;
    pttHeld = false;
    releasePending = false;
    clearTimeout(releaseTimer);
    stop();
    reportBridgeSignal("disarmed");
    btn.textContent = "⏳";
    btn.setAttribute("aria-label", "Push to talk waiting for bridge");
    btn.title = "Waiting for the authenticated Captain bridge";
  });

})();

function connect() {
  if (streamSource) return;
  streamSource = new EventSource(`${LIVE_CAPTAIN_API_BASE}/stream`);
  streamSource.onopen = () => {
    window.captainBridgeReady = true;
    window.dispatchEvent(new Event("captain-bridge-ready"));
    connEl.classList.add("live");
    connTextEl.textContent = "live";
    // A fresh connection (first load OR a reconnect after the backend
    // restarted) means any "in progress" state we were tracking from the
    // old connection is orphaned -- its completion event can never arrive,
    // so left alone it spins forever. Clear it silently rather than lie
    // about work still being done.
    stopThinking();
    stopImageGenIndicator();
    setCaptainPresence("ready", "Captain connected · awaiting command.");
  };
  streamSource.onerror = () => {
    window.captainBridgeReady = false;
    window.dispatchEvent(new Event("captain-bridge-unavailable"));
    connEl.classList.remove("live");
    connTextEl.textContent = "reconnecting…";
    setCaptainPresence("connecting", "Signal interrupted · reconnecting…");
  };
  streamSource.onmessage = (raw) => {
    try {
      handleEvent(JSON.parse(raw.data));
    } catch (err) {
      console.error("bad event", err, raw.data);
    }
  };
}

async function submitDirective() {
  unlockCaptainVoice();
  const sourceInput = activeCommandInput();
  const text = sourceInput.value.trim();
  if (!text) return;
  sourceInput.value = "";
  startThinking();
  setCaptainPresence("thinking", "Interpreting Admiral intent…");
  setActivePairMove("Interpreting signal and updating the shared course…");
  try {
    const response = await fetch(`${LIVE_CAPTAIN_API_BASE}/turn`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, interaction_mode: commandDraftMode ? "command_draft" : "bridge" }),
    });
    if (!response.ok) {
      stopThinking();
      const body = await response.json().catch(() => ({}));
      addRow("error", "error", body.error || `HTTP ${response.status}`);
      setCaptainPresence("fault", body.error || `Turn refused · HTTP ${response.status}`);
      window.dispatchEvent(new Event("captain-turn-submit-failed"));
    } else {
      // Do not make audible delivery depend on SSE remaining connected for the
      // entire inference + render. playCentralCaptainSpeech deduplicates this
      // against the normal captain_speech event.
      const body = await response.json().catch(() => ({}));
      if (body.speech_artifact) {
        playCentralCaptainSpeech({
          phase: "ready",
          thread_id: body.thread_id,
          text: body.text,
          artifact: body.speech_artifact,
        });
      }
    }
  } catch (err) {
    stopThinking();
    addRow("error", "error", String(err));
    setCaptainPresence("fault", String(err));
    window.dispatchEvent(new Event("captain-turn-submit-failed"));
  }
  activeCommandInput().focus();
}

input.addEventListener("keydown", (keyEvent) => {
  if (keyEvent.key === "Enter") {
    keyEvent.preventDefault();
    submitDirective();
  }
});
commandDraftInput?.addEventListener("keydown", (keyEvent) => {
  if (keyEvent.key === "Enter" && (keyEvent.ctrlKey || keyEvent.metaKey)) {
    keyEvent.preventDefault();
    submitDirective();
  }
});

terminalEl.addEventListener("click", () => {
  // A drag-select ends with a click on this same element -- refocusing the
  // input unconditionally stole focus the instant the mouse button was
  // released and collapsed the selection (Chrome clears window selection
  // when focus moves to a text input). Only steal focus back when the user
  // isn't in the middle of selecting text.
  if (window.getSelection().toString()) return;
  input.focus();
});

// --- .docx packet drop box -------------------------------------------------
// Uploads land in docs/incoming/ as staged material; the panel says so
// explicitly, because "the file arrived" and "the packet is filed" are two
// different states and the readout shouldn't blur them.
const DOCX_API_BASE = "/docx-intake-api/api";
const docxDrop = document.getElementById("docx-drop");
const docxFileInput = document.getElementById("docx-file");
const docxResult = document.getElementById("docx-result");
const docxRecent = document.getElementById("docx-recent");

function docxSay(message, kind) {
  docxResult.textContent = message;
  docxResult.className = kind || "";
}

const docxCommitBtn = document.getElementById("docx-commit");
const docxClearBtn = document.getElementById("docx-clear");

async function loadDocxRecent() {
  try {
    const response = await fetch(`${DOCX_API_BASE}/recent`);
    if (!response.ok) return;
    const body = await response.json();
    const entries = body.entries || [];
    docxRecent.innerHTML = entries.length
      ? `<div class="docx-recent-item">staged: ${entries.length}</div>` +
        entries.slice(0, 4).map((e) => `<div class="docx-recent-item">· ${e.name}</div>`).join("")
      : "";
    docxCommitBtn.disabled = entries.length === 0;
    docxClearBtn.disabled = entries.length === 0;
  } catch (err) {
    /* panel is supplementary; a failed listing shouldn't shout */
  }
}

async function docxAction(endpoint, button, workingLabel) {
  const original = button.textContent;
  button.textContent = workingLabel;
  docxCommitBtn.disabled = true;
  docxClearBtn.disabled = true;
  try {
    const response = await fetch(`${DOCX_API_BASE}/${endpoint}`, { method: "POST" });
    const body = await response.json().catch(() => ({}));
    if (response.ok && body.ok) return body;
    docxSay(`✗ ${body.error || `HTTP ${response.status}`}`, "err");
    return null;
  } catch (err) {
    docxSay(`✗ ${String(err)}`, "err");
    return null;
  } finally {
    button.textContent = original;
    loadDocxRecent();
  }
}

docxCommitBtn.addEventListener("click", async () => {
  const result = await docxAction("commit", docxCommitBtn, "pushing…");
  if (result) {
    const cleared = result.auto_cleared || {};
    let message = `✓ Committed ${result.commit} (${result.count} packet(s)) and pushed to ${result.branch}`;
    if (cleared.cleared) {
      message += ` · tray auto-cleared (${cleared.cleared} file(s), ${cleared.commit})`;
    }
    if (cleared.error) message += ` · ⚠ ${cleared.error}`;
    docxSay(message, cleared.error ? "err" : "ok");
  }
});

docxClearBtn.addEventListener("click", async () => {
  if (!window.confirm("Delete all staged packets and their originals? Anything already committed stays in git history.")) return;
  const result = await docxAction("clear", docxClearBtn, "clearing…");
  if (result) {
    docxSay(`✓ Cleared ${result.removed} staged packet(s)`, "ok");
  }
});

async function uploadDocx(file) {
  if (!file) return;
  if (!file.name.toLowerCase().endsWith(".docx")) {
    docxSay("That's not a .docx — Word documents only.", "err");
    return;
  }
  docxDrop.classList.add("busy");
  docxSay(`Uploading ${file.name}…`, "");
  try {
    const form = new FormData();
    form.append("file", file, file.name);
    const response = await fetch(`${DOCX_API_BASE}/upload`, { method: "POST", body: form });
    const body = await response.json().catch(() => ({}));
    if (response.ok && body.ok) {
      docxSay(`✓ Staged ${body.words} words → ${body.markdown_path} (awaiting evaluation)`, "ok");
      loadDocxRecent();
    } else {
      docxSay(`✗ ${body.error || `HTTP ${response.status}`}`, "err");
    }
  } catch (err) {
    docxSay(`✗ ${String(err)}`, "err");
  } finally {
    docxDrop.classList.remove("busy");
    docxFileInput.value = "";
  }
}

docxDrop.addEventListener("click", () => docxFileInput.click());
docxDrop.addEventListener("keydown", (keyEvent) => {
  if (keyEvent.key === "Enter" || keyEvent.key === " ") {
    keyEvent.preventDefault();
    docxFileInput.click();
  }
});
docxFileInput.addEventListener("change", () => uploadDocx(docxFileInput.files[0]));

for (const eventName of ["dragenter", "dragover"]) {
  docxDrop.addEventListener(eventName, (dragEvent) => {
    dragEvent.preventDefault();
    docxDrop.classList.add("dragover");
  });
}
for (const eventName of ["dragleave", "drop"]) {
  docxDrop.addEventListener(eventName, (dragEvent) => {
    dragEvent.preventDefault();
    docxDrop.classList.remove("dragover");
  });
}
docxDrop.addEventListener("drop", (dropEvent) => {
  uploadDocx(dropEvent.dataTransfer.files[0]);
});

loadDocxRecent();

// Private visual context gateway. It shares Root Console authentication but
// has no commit/push action: upload is not canon, publication, or consent.
(function wireContextImageDrop() {
  const drop = document.getElementById("context-image-drop");
  const input = document.getElementById("context-image-file");
  const result = document.getElementById("context-image-result");
  if (!drop || !input || !result) return;
  function say(text, kind = "") { result.textContent = text; result.className = kind; }
  async function upload(file) {
    if (!file) return;
    drop.classList.add("busy");
    say(`Uploading ${file.name}…`);
    try {
      const form = new FormData(); form.append("file", file, file.name);
      const response = await fetch(`${API_BASE}/context-image`, { method: "POST", body: form });
      const body = await response.json().catch(() => ({}));
      if (!response.ok || !body.ok) throw new Error(body.error || `HTTP ${response.status}`);
      say(`✓ Received ${body.path} · ${body.bytes} bytes`, "ok");
      addRow("injected", "context image", `Received ${body.path}; ready for Captain inspection.`);
    } catch (error) { say(`✗ ${error.message}`, "err"); }
    finally { drop.classList.remove("busy"); input.value = ""; }
  }
  drop.addEventListener("click", () => input.click());
  drop.addEventListener("keydown", (event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); input.click(); } });
  input.addEventListener("change", () => upload(input.files[0]));
  ["dragenter", "dragover"].forEach((name) => drop.addEventListener(name, (event) => { event.preventDefault(); drop.classList.add("dragover"); }));
  ["dragleave", "drop"].forEach((name) => drop.addEventListener(name, (event) => { event.preventDefault(); drop.classList.remove("dragover"); }));
  drop.addEventListener("drop", (event) => upload(event.dataTransfer.files[0]));
})();

// --- full speech-loop acceptance -----------------------------------------
// Automation can prove each wire but cannot prove what the Admiral heard.
// These authenticated controls make that final human observation durable.
(function wireSpeechAcceptance() {
  const panel = document.getElementById("speech-acceptance");
  const state = document.getElementById("speech-acceptance-state");
  const pass = document.getElementById("speech-loop-pass");
  const fault = document.getElementById("speech-loop-fault");
  if (!panel || !state || !pass || !fault) return;

  function paint(result) {
    const outcome = result.outcome || "pending";
    panel.dataset.outcome = outcome;
    state.textContent = outcome === "passed" ? "speech loop: ✓ heard"
      : outcome === "fault" ? "speech loop: ⚠ fault recorded"
      : "speech loop: unverified";
    panel.title = result.recorded_at
      ? `${result.test} · ${result.recorded_at}${result.note ? ` · ${result.note}` : ""}`
      : "Authenticated human acceptance record for the complete spoken loop";
  }

  async function record(outcome, note) {
    const response = await fetch(`${API_BASE}/speech-acceptance`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ outcome, note: note || "" }),
    });
    const result = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(result.error || `HTTP ${response.status}`);
    paint(result);
  }

  pass.addEventListener("click", () => {
    if (!window.confirm("Confirm you spoke naturally, the Captain understood, and you heard the spoken reply?")) return;
    record("passed", "Full loop confirmed from the Root Bridge").catch((error) => addRow("error", "speech proof", error.message));
  });
  fault.addEventListener("click", () => {
    const note = window.prompt("What failed? (optional)", "");
    if (note === null) return;
    record("fault", note).catch((error) => addRow("error", "speech proof", error.message));
  });
  fetch(`${API_BASE}/speech-acceptance`, { cache: "no-store" })
    .then((response) => response.ok ? response.json() : Promise.reject(new Error(`HTTP ${response.status}`)))
    .then(paint)
    .catch(() => paint({ outcome: "pending" }));
})();

// --- M³ cycle --------------------------------------------------------------
// D_t is the docs corpus, H_t is git, and Δ_t is whatever the working tree
// currently proposes (MSIR-M3-Q1, answered A). The panel shows the verdict
// and, when it fails, which condition failed and why -- a verdict without a
// reason is just an opinion.
const M3_API_BASE = "/m3-cycle-api/api";
const m3Verdict = document.getElementById("m3-verdict");
const m3Conds = document.getElementById("m3-conds");
const m3Why = document.getElementById("m3-why");
const m3Metrics = document.getElementById("m3-metrics");
const m3CommitBtn = document.getElementById("m3-commit");
const m3RollbackBtn = document.getElementById("m3-rollback");
const m3RefreshBtn = document.getElementById("m3-refresh");

function m3SetCond(name, state) {
  const el = m3Conds.querySelector(`[data-c="${name}"]`);
  if (el) el.className = "cond" + (state === null ? "" : state ? " pass" : " fail");
}

function m3Render(result) {
  if (!result.proposed) {
    m3Verdict.className = "v-noop";
    m3Verdict.innerHTML = '<div class="v-word">no change</div><div class="v-sub">docs/ matches HEAD — no Δ to evaluate</div>';
    ["I", "T", "R", "G", "V", "Q"].forEach((c) => m3SetCond(c, null));
    m3Why.textContent = "";
    m3Metrics.textContent = "";
    m3CommitBtn.disabled = true;
    m3RollbackBtn.disabled = true;
    return;
  }

  const commit = result.verdict === "commit";
  m3Verdict.className = commit ? "v-commit" : "v-rollback";
  m3Verdict.innerHTML = '<div class="v-word">' + result.verdict + "</div>" +
    '<div class="v-sub">' + result.changed.length + " document(s) changed of " + result.documents + "</div>";

  ["I", "T", "R", "G"].forEach((c) => m3SetCond(c, result.continuity[c]));
  m3SetCond("V", result.valuation.holds);
  m3SetCond("Q", result.q_rev.holds);

  const why = [];
  Object.keys(result.continuity.reasons || {}).forEach((k) => {
    result.continuity.reasons[k].slice(0, 2).forEach((r) => why.push(k + ": " + r));
  });
  if (!result.valuation.holds) {
    why.push("V: " + result.valuation.before + " → " + result.valuation.after + " (must increase)");
  }
  if (!result.q_rev.holds) {
    const regressed = result.q_rev.protected_regressed;
    why.push(regressed.length
      ? "Q: protected capacity regressed — " + regressed.join(", ")
      : "Q: no capacity improved");
  }
  m3Why.textContent = why.join(" · ");

  m3Metrics.textContent =
    "V " + result.valuation.before + "→" + result.valuation.after +
    " · Q↑ " + (result.q_rev.improved.join(", ") || "none");

  m3CommitBtn.disabled = !commit;
  m3RollbackBtn.disabled = false;
}

async function m3Evaluate() {
  try {
    const response = await fetch(`${M3_API_BASE}/evaluate`);
    const body = await response.json();
    if (body.ok) m3Render(body.result);
    else m3Why.textContent = "✗ " + (body.error || "evaluate failed");
  } catch (err) {
    m3Why.textContent = "✗ " + String(err);
  }
}

async function m3Act(endpoint, button, label) {
  const original = button.textContent;
  button.textContent = label;
  m3CommitBtn.disabled = true;
  m3RollbackBtn.disabled = true;
  try {
    const response = await fetch(`${M3_API_BASE}/${endpoint}`, { method: "POST" });
    const body = await response.json().catch(() => ({}));
    if (response.ok && body.ok) {
      m3Why.textContent = body.action === "commit"
        ? "✓ committed " + body.commit
        : "✓ rolled back " + body.restored + " document(s)";
    } else {
      m3Why.textContent = "✗ " + (body.error || `HTTP ${response.status}`);
    }
  } catch (err) {
    m3Why.textContent = "✗ " + String(err);
  } finally {
    button.textContent = original;
    m3Evaluate();
  }
}

m3RefreshBtn.addEventListener("click", m3Evaluate);
m3CommitBtn.addEventListener("click", () => m3Act("commit", m3CommitBtn, "committing…"));
m3RollbackBtn.addEventListener("click", () => {
  if (!window.confirm("Roll back all uncommitted changes under docs/? Tracked files are restored to HEAD; untracked additions are left alone.")) return;
  m3Act("rollback", m3RollbackBtn, "rolling back…");
});

m3Evaluate();

pollStatus();
