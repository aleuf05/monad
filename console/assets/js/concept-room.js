/* Captain's Concept Room: one Captain, scoped research conversations. */
(function () {
  "use strict";
  const API = "/live-captain-bootstrap-api/api";
  const els = {
    rooms: document.getElementById("concept-room-list"), newRoom: document.getElementById("concept-new-room"),
    title: document.getElementById("concept-room-title"), transcript: document.getElementById("concept-transcript"),
    form: document.getElementById("concept-form"), input: document.getElementById("concept-input"),
    state: document.getElementById("concept-state"), evidence: document.getElementById("concept-evidence"),
    history: document.getElementById("concept-history"), memory: document.getElementById("concept-memory"),
    atlas: document.getElementById("concept-atlas"), atlasNote: document.getElementById("concept-atlas-note"),
  };
  if (!els.form) return;
  let rooms = [];
  let currentRoom = localStorage.getItem("monad.conceptRoom") || null;
  let currentEvidence = [];
  let streamingRow = null;
  let streamingBody = null;

  function say(text, kind) {
    els.state.textContent = text;
    els.state.className = `concept-state ${kind || ""}`;
  }
  function escapeText(value) { const node = document.createElement("span"); node.textContent = value || ""; return node.innerHTML; }
  function renderCitedText(container, text) {
    container.textContent = "";
    const parts = String(text || "").split(/(\[S\d+\])/g);
    for (const part of parts) {
      const match = part.match(/^\[(S\d+)\]$/);
      if (!match) { container.appendChild(document.createTextNode(part)); continue; }
      const button = document.createElement("button");
      button.type = "button"; button.className = "concept-citation"; button.textContent = part;
      button.addEventListener("click", () => openEvidence(match[1]));
      container.appendChild(button);
    }
  }
  function addTurn(turn) {
    const row = document.createElement("div"); row.className = `concept-turn ${turn.role}`;
    const who = document.createElement("span"); who.className = "concept-who"; who.textContent = turn.role === "admiral" ? "Admiral" : "Living Captain";
    row.appendChild(who); const body = document.createElement("div"); renderCitedText(body, turn.text); row.appendChild(body);
    els.transcript.appendChild(row); els.transcript.scrollTop = els.transcript.scrollHeight;
    return row;
  }
  function viewerHash(item) {
    const stem = (item.path.split("/").pop() || "").replace(/\.md$/i, "");
    return `${item.category || "packet"}/${stem}`;
  }
  function openEvidence(sourceId) {
    const item = currentEvidence.find((source) => source.id === sourceId);
    if (!item) return;
    window.open(`documents.html#${encodeURIComponent(viewerHash(item))}`, "_blank", "noopener");
  }
  function renderEvidence(retrieval) {
    currentEvidence = retrieval.evidence || [];
    els.evidence.innerHTML = "";
    if (!currentEvidence.length) els.evidence.innerHTML = '<div class="concept-small">No matching evidence. Treat the answer as ungrounded.</div>';
    currentEvidence.forEach((item) => {
      const row = document.createElement("div"); row.className = "concept-evidence-item";
      row.innerHTML = `<strong>${escapeText(`[${item.id}] ${item.title}`)}</strong><div>${escapeText(item.heading)}</div><div class="concept-small">${escapeText(item.status)} · ${escapeText(item.path)} · ${escapeText(item.content_hash.slice(0, 12))}</div>`;
      row.addEventListener("click", () => openEvidence(item.id)); els.evidence.appendChild(row);
    });
    els.history.innerHTML = "";
    const events = retrieval.history || [];
    if (!events.length) els.history.innerHTML = '<div class="concept-small">No Git events in this answer.</div>';
    events.forEach((item) => {
      const row = document.createElement("div"); row.className = "concept-history-item";
      row.innerHTML = `<strong>${escapeText(item.subject)}</strong><div class="concept-small">${escapeText(item.authored_at)} · ${escapeText(item.commit.slice(0, 12))}</div>`;
      els.history.appendChild(row);
    });
  }
  function renderMemory(items) {
    els.memory.innerHTML = "";
    if (!items.length) els.memory.innerHTML = '<div class="concept-small">No cards yet.</div>';
    items.forEach((item) => {
      const row = document.createElement("div"); row.className = "concept-memory-item";
      row.innerHTML = `<strong>${escapeText(item.title)}</strong><div class="concept-small">revision ${item.current_revision} · working interpretation</div>`;
      row.addEventListener("click", () => loadConcept(item.id));
      els.memory.appendChild(row);
    });
  }
  function sourceCategory(path) {
    if (path.includes("/incoming/")) return "incoming";
    if (path.includes("/queries/")) return "query";
    if (path.includes("/packets/")) return "packet";
    if (path.includes("/reports/")) return "chronicle";
    if (path.includes("/logs/")) return "notes";
    if (path.includes("/doctrine/")) return "doctrine";
    return "packet";
  }
  function openAtlasSource(item) {
    window.open(`documents.html#${encodeURIComponent(viewerHash({...item, category: sourceCategory(item.path)}))}`, "_blank", "noopener");
  }
  function svgElement(name, attributes) {
    const node = document.createElementNS("http://www.w3.org/2000/svg", name);
    Object.entries(attributes || {}).forEach(([key, value]) => node.setAttribute(key, value));
    return node;
  }
  function renderAtlas(concept) {
    els.atlas.textContent = "";
    if (!concept || !concept.revisions || !concept.revisions.length) {
      els.atlasNote.textContent = "No durable concept revision selected."; return;
    }
    const revision = concept.revisions[concept.revisions.length - 1];
    const evidence = revision.evidence || [];
    const center = {x:210, y:168};
    evidence.forEach((item, index) => {
      const angle = (Math.PI * 2 * index / Math.max(1, evidence.length)) - Math.PI / 2;
      const radius = evidence.length > 6 ? 128 : 112;
      const x = center.x + Math.cos(angle) * radius;
      const y = center.y + Math.sin(angle) * radius;
      els.atlas.appendChild(svgElement("line", {x1:center.x, y1:center.y, x2:x, y2:y, class:"atlas-link"}));
      const group = svgElement("g", {class:"atlas-node source", style:`animation-delay:${index * 55}ms`});
      group.appendChild(svgElement("circle", {cx:x, cy:y, r:25}));
      const label = svgElement("text", {x, y:y-2, "text-anchor":"middle"}); label.textContent = item.id; group.appendChild(label);
      const meta = svgElement("text", {x, y:y+11, "text-anchor":"middle", class:"atlas-meta"}); meta.textContent = (item.heading || "source").slice(0, 15); group.appendChild(meta);
      group.addEventListener("click", () => openAtlasSource(item)); els.atlas.appendChild(group);
    });
    const core = svgElement("g", {class:"atlas-node center"});
    core.appendChild(svgElement("circle", {cx:center.x, cy:center.y, r:52}));
    const title = svgElement("text", {x:center.x, y:center.y-4, "text-anchor":"middle"}); title.textContent = concept.title.slice(0, 27); core.appendChild(title);
    const meta = svgElement("text", {x:center.x, y:center.y+13, "text-anchor":"middle", class:"atlas-meta"}); meta.textContent = `revision ${revision.revision} · ${revision.epistemic_state}`; core.appendChild(meta);
    els.atlas.appendChild(core);
    els.atlasNote.textContent = `${evidence.length} evidence relationship(s) · source geometry is provenance, not authority.`;
  }
  async function loadConcept(conceptId) {
    const response = await fetch(`${API}/concepts/${encodeURIComponent(conceptId)}`);
    if (!response.ok) return;
    renderAtlas((await response.json()).concept);
    document.querySelector('[data-concept-tab="atlas"]')?.click();
  }
  function renderRooms() {
    els.rooms.innerHTML = "";
    rooms.forEach((room) => {
      const row = document.createElement("div"); row.className = `concept-room-item ${room.id === currentRoom ? "on" : ""}`;
      row.innerHTML = `<strong>${escapeText(room.title)}</strong><div class="concept-small">whole corpus</div>`;
      row.addEventListener("click", () => openRoom(room.id)); els.rooms.appendChild(row);
    });
  }
  async function createRoom(title) {
    const response = await fetch(`${API}/concept/rooms`, {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({title:title || "New Concept Room"})});
    if (!response.ok) throw new Error(`room creation failed: HTTP ${response.status}`);
    const body = await response.json(); rooms.unshift(body.room); await openRoom(body.room.id);
  }
  async function loadRooms() {
    const response = await fetch(`${API}/concept/rooms`);
    if (!response.ok) { say(`Concept Room unavailable (HTTP ${response.status})`, "fault"); return; }
    rooms = (await response.json()).rooms || [];
    if (!rooms.length) await createRoom("Monad Concepts");
    else await openRoom(rooms.some((room) => room.id === currentRoom) ? currentRoom : rooms[0].id);
  }
  async function openRoom(roomId) {
    currentRoom = roomId; localStorage.setItem("monad.conceptRoom", roomId); renderRooms(); say("Loading room…", "live");
    const response = await fetch(`${API}/concept/rooms/${encodeURIComponent(roomId)}/turns`);
    if (!response.ok) { say(`Room unavailable (HTTP ${response.status})`, "fault"); return; }
    const body = await response.json(); els.title.textContent = body.room.title; els.transcript.innerHTML = "";
    (body.turns || []).forEach(addTurn); renderMemory(body.concepts || []);
    if ((body.concepts || []).length) loadConcept(body.concepts[0].id);
    const latest = [...(body.turns || [])].reverse().find((turn) => turn.role === "captain");
    if (latest) renderEvidence(latest.retrieval || {}); say("Captain ready."); els.input.focus();
  }
  els.form.addEventListener("submit", async (event) => {
    event.preventDefault(); const text = els.input.value.trim(); if (!text || !currentRoom) return;
    els.input.value = ""; addTurn({role:"admiral", text}); say("📚 Retrieving live corpus…", "live");
    try {
      const response = await fetch(`${API}/concept/rooms/${encodeURIComponent(currentRoom)}/turns`, {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({text})});
      const body = await response.json().catch(() => ({})); if (!response.ok) throw new Error(body.error || `HTTP ${response.status}`);
      if (streamingRow) streamingRow.remove(); streamingRow = null; streamingBody = null;
      addTurn(body.captain_turn); renderEvidence(body.captain_turn.retrieval || {});
      const memoryResponse = await fetch(`${API}/concept/rooms/${encodeURIComponent(currentRoom)}/concepts`);
      if (memoryResponse.ok) renderMemory((await memoryResponse.json()).concepts || []);
      renderAtlas(body.concept);
      say(`✅ grounded in ${(body.captain_turn.retrieval.evidence || []).length} source passage(s) · memory revision ${body.concept.current_revision}`);
      if (typeof speakCaptain === "function") speakCaptain(body.captain_turn.spoken_brief || body.captain_turn.text);
    } catch (error) { if (streamingRow) streamingRow.remove(); streamingRow = null; streamingBody = null; say(`FAULT: ${error.message}`, "fault"); }
  });
  els.input.addEventListener("keydown", (event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); els.form.requestSubmit(); } });
  els.newRoom.addEventListener("click", () => createRoom(`Concept Room ${rooms.length + 1}`).catch((error) => say(error.message, "fault")));
  document.querySelectorAll("[data-concept-intent]").forEach((button) => button.addEventListener("click", () => { els.input.value = button.dataset.conceptIntent; els.input.focus(); }));
  document.querySelectorAll("[data-concept-tab]").forEach((button) => button.addEventListener("click", () => {
    document.querySelectorAll("[data-concept-tab]").forEach((item) => item.classList.toggle("on", item === button));
    document.querySelectorAll("[data-concept-pane]").forEach((pane) => { pane.hidden = pane.dataset.conceptPane !== button.dataset.conceptTab; });
  }));
  window.addEventListener("concept-room-stream", (streamEvent) => {
    const event = streamEvent.detail || {};
    const expectedSource = `concept-room:${currentRoom}`;
    if (event.type === "concept_room") {
      if (event.room_id !== currentRoom) return;
      if (event.phase === "retrieving") say("📚 Retrieving live corpus…", "live");
      if (event.phase === "synthesizing") say(`🧠 Synthesizing ${event.evidence_count || 0} grounded passage(s)…`, "live");
      if (event.phase === "failed") say(`FAULT: ${event.error || "Captain turn failed"}`, "fault");
      return;
    }
    if (event.source !== expectedSource || event.type !== "codex_event") return;
    const params = event.params || {};
    if (event.method === "item/agentMessage/delta") {
      if (!streamingRow) {
        streamingRow = addTurn({role:"captain", text:""});
        streamingRow.classList.add("streaming"); streamingBody = streamingRow.lastElementChild;
      }
      streamingBody.textContent += params.delta || "";
      els.transcript.scrollTop = els.transcript.scrollHeight;
    }
    if (event.method === "item/completed" && (params.item || {}).type === "agentMessage" && streamingBody) {
      renderCitedText(streamingBody, params.item.text || streamingBody.textContent);
    }
  });
  loadRooms().catch((error) => say(error.message, "fault"));
})();
