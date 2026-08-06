/**
 * Monad top-level site redesign: a flat, manually-ordered Active Queue on
 * the homepage, plus a generic "+ Queue" affordance injected onto the
 * existing card-based project/component listings (build.html, command.html,
 * observe.html, story.html) so the queue references the SAME record (the
 * card's own href/title) instead of duplicating it.
 *
 * Storage: localStorage only, one JSON snapshot (monad.activeQueue.v1).
 * This is a deliberate v0 scope choice -- there is no writable backend for
 * site content today (web/ is static, served by Caddy), so "persists
 * across reloads" here means "persists on this browser/device," not
 * cross-device sync. See tools/living-basin and Beastscape Lab Mode for
 * the same honest pattern (client-side-only v1, flagged as such).
 *
 * The archive hierarchy itself is NOT rebuilt: this script does not
 * flatten or replace build.html/command.html/observe.html/story.html --
 * it only adds a lightweight "add this to the queue" affordance on top of
 * their existing .card markup, and a same-page text filter over the
 * homepage's own top-level categories grid. Deeper per-page structure is
 * untouched.
 */
(function () {
  "use strict";

  var QUEUE_KEY = "monad.activeQueue.v1";
  var ARCHIVE_PAGES = [
    { file: "build.html", label: "Build & Research" },
    { file: "command.html", label: "Command" },
    { file: "observe.html", label: "Observe" },
    { file: "story.html", label: "Story & Records" },
  ];

  function $(sel, root) { return (root || document).querySelector(sel); }
  function $all(sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); }
  function nowIso() { return new Date().toISOString(); }
  function uid() { return "q_" + Date.now().toString(36) + Math.floor(Math.random() * 1e4).toString(36); }

  // -- storage --------------------------------------------------------

  function loadQueue() {
    try {
      var data = JSON.parse(localStorage.getItem(QUEUE_KEY) || "");
      if (data.schema !== "monad.activeQueue.v1" || !Array.isArray(data.items)) throw 0;
      return data;
    } catch (e) {
      return { schema: "monad.activeQueue.v1", items: [] };
    }
  }
  function saveQueue(q) { localStorage.setItem(QUEUE_KEY, JSON.stringify(q)); }

  function sortedItems(q) {
    return q.items.slice().sort(function (a, b) { return a.queue_position - b.queue_position; });
  }
  function renumber(q) {
    sortedItems(q).forEach(function (item, i) { item.queue_position = i; });
  }
  function findItemByUrl(q, url) {
    return q.items.filter(function (i) { return i.url === url; })[0] || null;
  }

  function addToQueue(entry) {
    var q = loadQueue();
    var existing = findItemByUrl(q, entry.url);
    if (existing) return existing; // same record already queued -- don't duplicate
    var item = {
      id: uid(),
      title: entry.title,
      url: entry.url,
      parent: entry.parent || "",
      active_status: q.items.length === 0 ? "current" : "queued",
      latest_note: "",
      next_action: "",
      pinned: false,
      queue_position: q.items.length,
      activated_at: nowIso(),
      last_active_update: nowIso(),
    };
    q.items.push(item);
    saveQueue(q);
    return item;
  }

  function removeFromQueue(id) {
    var q = loadQueue();
    var item = q.items.filter(function (i) { return i.id === id; })[0];
    if (!item) return true;
    if (item.pinned) return false; // held -- must unpin first
    q.items = q.items.filter(function (i) { return i.id !== id; });
    renumber(q);
    saveQueue(q);
    return true;
  }

  function moveItem(id, delta) {
    var q = loadQueue();
    var items = sortedItems(q);
    var idx = items.findIndex(function (i) { return i.id === id; });
    var target = idx + delta;
    if (idx < 0 || target < 0 || target >= items.length) return;
    var a = items[idx], b = items[target];
    var tmp = a.queue_position; a.queue_position = b.queue_position; b.queue_position = tmp;
    saveQueue(q);
  }
  function moveToTop(id) {
    var q = loadQueue();
    var items = sortedItems(q);
    var idx = items.findIndex(function (i) { return i.id === id; });
    if (idx <= 0) return;
    var item = items[idx];
    items.splice(idx, 1);
    items.unshift(item);
    items.forEach(function (it, i) { it.queue_position = i; });
    saveQueue(q);
  }
  function togglePin(id) {
    var q = loadQueue();
    var item = q.items.filter(function (i) { return i.id === id; })[0];
    if (!item) return;
    item.pinned = !item.pinned;
    item.last_active_update = nowIso();
    saveQueue(q);
  }
  function updateItem(id, patch) {
    var q = loadQueue();
    var item = q.items.filter(function (i) { return i.id === id; })[0];
    if (!item) return;
    Object.keys(patch).forEach(function (k) { item[k] = patch[k]; });
    item.last_active_update = nowIso();
    saveQueue(q);
  }

  function relativeTime(iso) {
    var ms = Date.now() - new Date(iso).getTime();
    var min = Math.round(ms / 60000);
    if (min < 1) return "just now";
    if (min < 60) return min + "m ago";
    var hr = Math.round(min / 60);
    if (hr < 24) return hr + "h ago";
    return Math.round(hr / 24) + "d ago";
  }

  // -- homepage queue rendering ----------------------------------------

  function renderQueue() {
    var body = $("#aqBody");
    if (!body) return;
    var q = loadQueue();
    var items = sortedItems(q);
    if (items.length === 0) {
      body.innerHTML = '<p class="aq-empty">Nothing active yet. Use "+ Add from archive" to pull a project or tool into the queue.</p>';
      return;
    }
    var current = items[0];
    var rest = items.slice(1);

    var html = '';
    html += '<div class="aq-current" data-id="' + current.id + '">';
    html += '<div class="aq-parent">' + escapeHtml(current.parent || "Active queue") + (current.pinned ? " · held" : "") + '</div>';
    html += '<div class="aq-item-title">' + escapeHtml(current.title) + '</div>';
    html += '<div class="aq-summary">' + (current.latest_note ? escapeHtml(current.latest_note) : "No progress note yet.") + '</div>';
    html += '<div class="aq-fields">';
    html += '<label>Status<select data-field="active_status">' + statusOptions(current.active_status) + '</select></label>';
    html += '<label>Next action<input type="text" data-field="next_action" value="' + escapeAttr(current.next_action) + '" placeholder="What happens next?"></label>';
    html += '<label style="grid-column:1/-1">Progress note<input type="text" data-field="latest_note" value="' + escapeAttr(current.latest_note) + '" placeholder="Where things stand right now"></label>';
    html += '</div>';
    html += '<div class="aq-meta-row"><span>Activated ' + relativeTime(current.activated_at) + ' · updated ' + relativeTime(current.last_active_update) + '</span></div>';
    html += '<div class="aq-row-actions">';
    html += '<a class="aq-open" href="' + escapeAttr(current.url) + '">Open &amp; continue &rarr;</a>';
    html += '<button class="aq-btn" data-action="pin">' + (current.pinned ? "Unpin (release hold)" : "Pin (hold in queue)") + '</button>';
    html += '<button class="aq-btn danger" data-action="remove">Remove from queue</button>';
    html += '</div></div>';

    if (rest.length) {
      html += '<div class="aq-list">';
      rest.forEach(function (item) {
        html += '<div class="aq-item' + (item.pinned ? ' pinned' : '') + '" data-id="' + item.id + '">';
        html += '<div><div class="aq-parent">' + escapeHtml(item.parent || "") + '</div>';
        html += '<div class="aq-item-title">' + escapeHtml(item.title) + '</div>';
        if (item.next_action) html += '<div class="aq-next">Next: ' + escapeHtml(item.next_action) + '</div>';
        html += '</div>';
        html += '<div class="aq-item-controls">';
        html += '<button class="aq-mini" data-action="top" title="Move to top">&#8607;&#8607;</button>';
        html += '<button class="aq-mini" data-action="up" title="Move up">&#8593;</button>';
        html += '<button class="aq-mini" data-action="down" title="Move down">&#8595;</button>';
        html += '<button class="aq-mini' + (item.pinned ? ' on' : '') + '" data-action="pin" title="Pin (hold in queue)">&#128204;</button>';
        html += '<a class="aq-mini" style="display:inline-flex;align-items:center;justify-content:center;text-decoration:none" href="' + escapeAttr(item.url) + '" title="Open">&rarr;</a>';
        html += '<button class="aq-mini" data-action="remove" title="Remove">&times;</button>';
        html += '</div></div>';
      });
      html += '</div>';
    }
    body.innerHTML = html;
    wireQueueControls(body);
  }

  function statusOptions(current) {
    return ["current", "queued", "blocked", "paused"].map(function (s) {
      return '<option value="' + s + '"' + (s === current ? " selected" : "") + '>' + s + '</option>';
    }).join("");
  }

  function wireQueueControls(root) {
    $all(".aq-current [data-field]", root).forEach(function (el) {
      var id = $(".aq-current", root).dataset.id;
      el.addEventListener("change", function () { updateItem(id, mkPatch(el)); });
      el.addEventListener("input", function () { updateItem(id, mkPatch(el)); });
    });
    $all("[data-action]", root).forEach(function (btn) {
      btn.addEventListener("click", function () {
        var container = btn.closest("[data-id]");
        var id = container.dataset.id;
        var action = btn.dataset.action;
        if (action === "remove") {
          if (!removeFromQueue(id)) { alert("This item is pinned (held in the queue). Unpin it first, then remove."); return; }
        } else if (action === "pin") { togglePin(id); }
        else if (action === "up") { moveItem(id, -1); }
        else if (action === "down") { moveItem(id, 1); }
        else if (action === "top") { moveToTop(id); }
        renderQueue();
      });
    });
  }
  function mkPatch(el) {
    var patch = {};
    patch[el.dataset.field] = el.value;
    return patch;
  }

  function escapeHtml(s) { return String(s || "").replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function escapeAttr(s) { return escapeHtml(s); }

  // -- "Add from archive" dialog: live-fetches the real category pages --

  var archiveCache = null;
  function loadArchiveIndex() {
    if (archiveCache) return Promise.resolve(archiveCache);
    return Promise.all(ARCHIVE_PAGES.map(function (page) {
      return fetch(page.file).then(function (r) { return r.text(); }).then(function (html) {
        var doc = new DOMParser().parseFromString(html, "text/html");
        return $all("a.card", doc).map(function (a) {
          var name = $(".card-name", a);
          var desc = $(".card-desc", a);
          return {
            title: name ? name.textContent.trim() : a.textContent.trim().slice(0, 60),
            desc: desc ? desc.textContent.trim() : "",
            // href values inside build.html/command.html/etc. (e.g.
            // "toys/foo/") are already relative to web/, same as
            // index.html's own base -- no resolution needed.
            url: a.getAttribute("href") || page.file,
            parent: page.label,
          };
        });
      }).catch(function () { return []; });
    })).then(function (lists) {
      archiveCache = lists.reduce(function (a, b) { return a.concat(b); }, []);
      return archiveCache;
    });
  }

  function renderPicks(list, filter) {
    var picks = $("#aqPicks");
    var q = loadQueue();
    var term = (filter || "").toLowerCase();
    var filtered = list.filter(function (item) {
      return !term || item.title.toLowerCase().indexOf(term) !== -1 || item.desc.toLowerCase().indexOf(term) !== -1 || item.parent.toLowerCase().indexOf(term) !== -1;
    });
    if (!filtered.length) { picks.innerHTML = '<p class="aq-empty">No matches.</p>'; return; }
    picks.innerHTML = filtered.map(function (item) {
      var already = !!findItemByUrl(q, item.url);
      return '<div class="aq-pick"><div><div class="aq-pick-name">' + escapeHtml(item.title) + '</div><div class="aq-pick-parent">' + escapeHtml(item.parent) + '</div></div>' +
        '<button data-url="' + escapeAttr(item.url) + '" data-title="' + escapeAttr(item.title) + '" data-parent="' + escapeAttr(item.parent) + '"' + (already ? " disabled" : "") + '>' + (already ? "Queued" : "Add") + '</button></div>';
    }).join("");
    $all("#aqPicks button:not([disabled])").forEach(function (btn) {
      btn.addEventListener("click", function () {
        addToQueue({ title: btn.dataset.title, url: btn.dataset.url, parent: btn.dataset.parent });
        renderQueue();
        renderPicks(list, $("#aqSearch").value);
      });
    });
  }

  // A compact, all-items-at-once reorder/manage list -- reuses the same
  // dialog as "Add from archive" (different content), useful when the
  // queue has grown past what's comfortable to reorder via the inline
  // per-card controls, especially on a small screen.
  function renderManage() {
    var q = loadQueue();
    var items = sortedItems(q);
    var picks = $("#aqPicks");
    if (!items.length) { picks.innerHTML = '<p class="aq-empty">Queue is empty.</p>'; return; }
    picks.innerHTML = items.map(function (item, i) {
      return '<div class="aq-pick" data-id="' + item.id + '"><div><div class="aq-pick-name">' +
        (i === 0 ? "★ " : "") + escapeHtml(item.title) + (item.pinned ? " · held" : "") + '</div>' +
        '<div class="aq-pick-parent">' + escapeHtml(item.parent || "") + ' · ' + escapeHtml(item.active_status) + '</div></div>' +
        '<div class="aq-item-controls">' +
        '<button class="aq-mini" data-action="top" title="Move to top">&#8607;&#8607;</button>' +
        '<button class="aq-mini" data-action="up" title="Move up">&#8593;</button>' +
        '<button class="aq-mini" data-action="down" title="Move down">&#8595;</button>' +
        '<button class="aq-mini' + (item.pinned ? ' on' : '') + '" data-action="pin" title="Pin (hold in queue)">&#128204;</button>' +
        '<button class="aq-mini" data-action="remove" title="Remove">&times;</button></div></div>';
    }).join("");
    $all("[data-action]", picks).forEach(function (btn) {
      btn.addEventListener("click", function () {
        var id = btn.closest("[data-id]").dataset.id;
        var action = btn.dataset.action;
        if (action === "remove") { if (!removeFromQueue(id)) { alert("This item is pinned (held in the queue). Unpin it first, then remove."); return; } }
        else if (action === "pin") { togglePin(id); }
        else if (action === "up") { moveItem(id, -1); }
        else if (action === "down") { moveItem(id, 1); }
        else if (action === "top") { moveToTop(id); }
        renderQueue();
        renderManage();
      });
    });
  }

  function initHomepageQueue() {
    if (!$("#activeQueue")) return;
    renderQueue();

    var dialog = $("#aqDialog");
    $("#aqAddBtn").addEventListener("click", function () {
      dialog.showModal();
      $("#aqDialogTitle").textContent = "Add from archive";
      $("#aqSearch").hidden = false;
      $("#aqSearch").value = "";
      $("#aqPicks").innerHTML = '<p class="aq-empty">Loading archive&hellip;</p>';
      loadArchiveIndex().then(function (list) { renderPicks(list, ""); });
    });
    $("#aqSearch").addEventListener("input", function () {
      if ($("#aqDialogTitle").textContent !== "Add from archive") return;
      loadArchiveIndex().then(function (list) { renderPicks(list, $("#aqSearch").value); });
    });
    $("#aqDialogClose").addEventListener("click", function () { dialog.close(); });
    dialog.addEventListener("click", function (e) { if (e.target === dialog) dialog.close(); });

    $("#aqManageBtn").addEventListener("click", function () {
      dialog.showModal();
      $("#aqDialogTitle").textContent = "Manage queue";
      $("#aqSearch").hidden = true;
      renderManage();
    });
  }

  // -- injected "+ Queue" buttons on archive/category pages -----------

  function initCardButtons() {
    var cards = $all("a.card");
    if (!cards.length) return;
    var style = document.createElement("style");
    style.textContent =
      ".aq-card-wrap{position:relative}" +
      ".aq-card-add{position:absolute;top:10px;right:10px;z-index:5;font:10px/1 'JetBrains Mono',monospace;" +
      "background:#0d1420dd;border:1px solid #1E2C42;color:#9AACBF;padding:5px 8px;border-radius:5px;cursor:pointer;}" +
      ".aq-card-add:hover{border-color:#4FD1C5;color:#4FD1C5}" +
      ".aq-card-add.on{border-color:#4FD1C5;color:#4FD1C5;background:#0F2A2C}";
    document.head.appendChild(style);

    var pageLabel = (document.title || "").split(" — ")[0];
    var q = loadQueue();

    cards.forEach(function (card) {
      var wrap = document.createElement("div");
      wrap.className = "aq-card-wrap";
      card.parentNode.insertBefore(wrap, card);
      wrap.appendChild(card);

      var nameEl = $(".card-name", card);
      var title = nameEl ? nameEl.textContent.trim() : card.textContent.trim().slice(0, 60);
      var url = card.getAttribute("href");
      var btn = document.createElement("button");
      btn.className = "aq-card-add";
      btn.type = "button";
      function paint() {
        var already = !!findItemByUrl(loadQueue(), url);
        btn.textContent = already ? "✓ Queued" : "+ Queue";
        btn.classList.toggle("on", already);
      }
      btn.addEventListener("click", function (e) {
        e.preventDefault(); e.stopPropagation();
        addToQueue({ title: title, url: url, parent: pageLabel });
        paint();
      });
      paint();
      wrap.appendChild(btn);
    });
  }

  // -- homepage archive text filter -------------------------------------

  function initArchiveSearch() {
    var input = $("#archiveSearch");
    if (!input) return;
    input.addEventListener("input", function () {
      var term = input.value.toLowerCase();
      $all(".cat-card").forEach(function (card) {
        var text = card.textContent.toLowerCase();
        card.classList.toggle("aq-hidden", term.length > 0 && text.indexOf(term) === -1);
      });
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    initHomepageQueue();
    initCardButtons();
    initArchiveSearch();
  });
})();
