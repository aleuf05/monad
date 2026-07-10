const state = { manifest: null, entries: [], activeId: null, query: "", filters: { role: "all", entity: "all", year: "all", type: "all" } };
const els = {
  indexMeta: document.querySelector("#indexMeta"), totalLogs: document.querySelector("#totalLogs"), latestLog: document.querySelector("#latestLog"),
  searchInput: document.querySelector("#searchInput"), roleFilter: document.querySelector("#roleFilter"), entityFilter: document.querySelector("#entityFilter"),
  yearFilter: document.querySelector("#yearFilter"), typeFilter: document.querySelector("#typeFilter"), countsList: document.querySelector("#countsList"),
  resultCount: document.querySelector("#resultCount"), logList: document.querySelector("#logList"), readerRole: document.querySelector("#readerRole"),
  readerTitle: document.querySelector("#readerTitle"), sourcePath: document.querySelector("#sourcePath"), readerDetails: document.querySelector("#readerDetails"),
  copyCitationButton: document.querySelector("#copyCitationButton"), content: document.querySelector("#content")
};
function escapeHtml(value) { return String(value ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;"); }
function formatDate(value) { if (!value) return "Unknown"; const isoDate = /^\d{4}-\d{2}-\d{2}/.exec(value); if (isoDate) return isoDate[0]; const date = new Date(value); return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString([], { year: "numeric", month: "short", day: "2-digit" }); }

function formatGenerated(value) { const date = new Date(value); return Number.isNaN(date.getTime()) ? (value || "unknown") : date.toLocaleString([], { year: "numeric", month: "short", day: "2-digit", hour: "2-digit", minute: "2-digit" }); }
function queryTerms() { return state.query.toLowerCase().split(/\s+/).map((term) => term.trim()).filter(Boolean); }
function matchesEntry(entry) {
  if (state.filters.role !== "all" && entry.role !== state.filters.role) return false;
  if (state.filters.entity !== "all" && entry.entity !== state.filters.entity) return false;
  if (state.filters.year !== "all" && entry.year !== state.filters.year) return false;
  if (state.filters.type !== "all" && entry.fileType !== state.filters.type) return false;
  const terms = queryTerms();
  if (!terms.length) return true;
  const haystack = `${entry.title}\n${entry.path}\n${entry.excerpt}\n${entry.content || ""}`.toLowerCase();
  return terms.every((term) => haystack.includes(term));
}
function highlight(value) {
  let html = escapeHtml(value);
  for (const term of queryTerms()) {
    const escaped = term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    html = html.replace(new RegExp(`(${escaped})`, "ig"), "<mark>$1</mark>");
  }
  return html;
}
function optionList(select, values, label) { select.innerHTML = `<option value="all">All ${label}</option>` + values.map((value) => `<option value="${escapeHtml(value)}">${escapeHtml(value)}</option>`).join(""); }
function unique(key) { return [...new Set(state.entries.map((entry) => entry[key]).filter(Boolean))].sort((a, b) => String(b).localeCompare(String(a))); }
function renderSummary() {
  els.totalLogs.textContent = state.manifest.entryCount;
  els.latestLog.textContent = formatDate(state.manifest.latestLogTimestamp);
  els.indexMeta.textContent = `Index generated ${formatGenerated(state.manifest.generatedAt)}`;
  els.countsList.innerHTML = Object.entries(state.manifest.counts.byRole).map(([role, count]) => `<span class="count-chip"><b>${escapeHtml(role)}</b>${count}</span>`).join("");
  optionList(els.roleFilter, unique("role"), "roles"); optionList(els.entityFilter, unique("entity"), "officers"); optionList(els.yearFilter, unique("year"), "years"); optionList(els.typeFilter, unique("fileType"), "types");
}
function renderList() {
  const shown = state.entries.filter(matchesEntry);
  els.resultCount.textContent = `${shown.length} shown`;
  els.logList.innerHTML = shown.map((entry) => `<li class="log-item ${entry.id === state.activeId ? "is-active" : ""}"><button type="button" data-id="${escapeHtml(entry.id)}"><span class="log-title">${highlight(entry.title)}</span><span class="log-meta">${escapeHtml(entry.role)} / ${escapeHtml(entry.entity)} / ${escapeHtml(entry.year)} / .${escapeHtml(entry.fileType)}</span><span class="log-path">${highlight(entry.path)}</span></button></li>`).join("");
}
function inlineMarkdown(text) { return escapeHtml(text).replace(/`([^`]+)`/g, "<code>$1</code>").replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>").replace(/\*([^*]+)\*/g, "<em>$1</em>"); }
function renderMarkdown(text) {
  const lines = text.replace(/\r\n/g, "\n").split("\n"); const out = []; let inCode = false; let code = []; let list = [];
  const flushList = () => { if (list.length) { out.push(`<ul>${list.map((item) => `<li>${inlineMarkdown(item)}</li>`).join("")}</ul>`); list = []; } };
  for (const line of lines) {
    if (line.trim().startsWith("```")) { if (inCode) { out.push(`<pre><code>${escapeHtml(code.join("\n"))}</code></pre>`); code = []; inCode = false; } else { flushList(); inCode = true; } continue; }
    if (inCode) { code.push(line); continue; }
    const trimmed = line.trim(); if (!trimmed) { flushList(); continue; }
    const heading = /^(#{1,3})\s+(.+)$/.exec(trimmed); if (heading) { flushList(); const level = heading[1].length; out.push(`<h${level}>${inlineMarkdown(heading[2])}</h${level}>`); continue; }
    const bullet = /^[-*]\s+(.+)$/.exec(trimmed); if (bullet) { list.push(bullet[1]); continue; }
    if (trimmed.startsWith(">")) { flushList(); out.push(`<blockquote>${inlineMarkdown(trimmed.replace(/^>\s?/, ""))}</blockquote>`); continue; }
    flushList(); out.push(`<p>${inlineMarkdown(trimmed)}</p>`);
  }
  flushList(); if (inCode) out.push(`<pre><code>${escapeHtml(code.join("\n"))}</code></pre>`); return out.join("\n");
}
function renderContent(entry) { if (!entry.content) return "<p>Log content has not loaded.</p>"; return (entry.fileType === "md" || entry.fileType === "markdown") ? renderMarkdown(entry.content) : `<pre class="plaintext"><code>${escapeHtml(entry.content)}</code></pre>`; }
async function selectLog(id, pushHash = true) {
  const entry = state.entries.find((item) => item.id === id); if (!entry) return; state.activeId = id;
  if (!entry.content) { entry.content = await fetch(entry.fetchPath).then((response) => { if (!response.ok) throw new Error(`${response.status} ${response.statusText}`); return response.text(); }); }
  els.readerRole.textContent = `${entry.role} / ${entry.entity} / ${entry.year}`; els.readerTitle.textContent = entry.title; els.sourcePath.textContent = entry.path;
  els.readerDetails.textContent = `${formatDate(entry.sortTimestamp)} / ${entry.sizeBytes.toLocaleString()} bytes / .${entry.fileType}`;
  els.copyCitationButton.disabled = false; els.copyCitationButton.dataset.path = entry.path; els.content.classList.remove("empty-state"); els.content.innerHTML = renderContent(entry); renderList();
  if (pushHash) location.hash = `log=${encodeURIComponent(id)}`;
}
function bindEvents() {
  els.searchInput.addEventListener("input", () => { state.query = els.searchInput.value.trim(); renderList(); });
  for (const [select, key] of [[els.roleFilter, "role"], [els.entityFilter, "entity"], [els.yearFilter, "year"], [els.typeFilter, "type"]]) { select.addEventListener("change", () => { state.filters[key] = select.value; renderList(); }); }
  els.logList.addEventListener("click", (event) => { const button = event.target.closest("button[data-id]"); if (button) selectLog(button.dataset.id); });
  els.copyCitationButton.addEventListener("click", async () => { const citation = els.copyCitationButton.dataset.path; if (!citation) return; try { await navigator.clipboard.writeText(citation); els.copyCitationButton.textContent = "Copied"; setTimeout(() => { els.copyCitationButton.textContent = "Copy citation"; }, 1200); } catch { els.copyCitationButton.textContent = citation; } });
  window.addEventListener("hashchange", () => openHashRoute());
}
function openHashRoute() { const params = new URLSearchParams(location.hash.replace(/^#/, "")); const id = params.get("log"); if (id && id !== state.activeId) selectLog(id, false); }
async function loadManifest() {
  state.manifest = await fetch("log-index.json", { cache: "no-store" }).then((response) => { if (!response.ok) throw new Error(`${response.status} ${response.statusText}`); return response.json(); });
  state.entries = state.manifest.entries.map((entry) => ({ ...entry, content: "" })); renderSummary(); renderList(); bindEvents();
  await Promise.allSettled(state.entries.map(async (entry) => { entry.content = await fetch(entry.fetchPath).then((response) => response.ok ? response.text() : ""); }));
  openHashRoute(); if (!state.activeId && state.entries[0]) selectLog(state.entries[0].id, false);
}
loadManifest().catch((error) => { els.indexMeta.textContent = "Index failed"; els.content.classList.add("empty-state"); els.content.innerHTML = `<p>Watchbook could not load <code>log-index.json</code>.</p><pre>${escapeHtml(error.message)}</pre>`; });
