(function () {
  "use strict";

  var STORAGE_KEY = "captains-desk-v1";

  var TOKENS = [
    { id: "pin", emoji: "📌", label: "Pin", meaning: "Preserve this thought", log: "Preserved for later." },
    { id: "holdfast", emoji: "⚓", label: "Hold Fast", meaning: "Don't overreact; remain grounded", log: "Staying grounded — no overreaction." },
    { id: "bearing", emoji: "🧭", label: "Bearing", meaning: "Recover direction", log: "Recovering direction." },
    { id: "reentry", emoji: "🔄", label: "Re-entry", meaning: "Feed output back into process", log: "Feeding this back into the process." },
    { id: "loopiness", emoji: "🌀", label: "Loopiness", meaning: "Interesting recursion discovered", log: "Interesting recursion noted." },
    { id: "reflexive", emoji: "🪞", label: "Reflexive Turn", meaning: "System examining itself", log: "System examining itself here." },
    { id: "genome", emoji: "🧬", label: "Context Genome", meaning: "Compact reusable context", log: "Compacted as reusable context." },
    { id: "fleshit", emoji: "🛠", label: "Flesh It", meaning: "Build it", log: "Opening implementation workspace." },
    { id: "lens", emoji: "🔬", label: "Chief's Lens", meaning: "Investigate rigorously", log: "Investigate this." },
    { id: "generative", emoji: "🌱", label: "Generative Condition", meaning: "What allows this to emerge?", log: "What allows this to emerge?" },
    { id: "hatch", emoji: "🚪", label: "Hatch", meaning: "Cross into implementation", log: "Crossing into implementation." },
    { id: "nightharbor", emoji: "🌙", label: "Night Harbor", meaning: "Suspend work safely", log: "Suspended safely." },
    { id: "triumph", emoji: "✨", label: "Quiet Triumph", meaning: "Genuine progress without fanfare", log: "Archived as completed." }
  ];

  var TOKENS_BY_ID = {};
  TOKENS.forEach(function (t) { TOKENS_BY_ID[t.id] = t; });

  var deskSurface = document.getElementById("deskSurface");
  var trayTokens = document.getElementById("trayTokens");
  var dragGhost = document.getElementById("dragGhost");
  var newCardBtn = document.getElementById("newCardBtn");
  var clearDeskBtn = document.getElementById("clearDeskBtn");

  var state = loadState();
  var uidCounter = 1;

  function uid(prefix) {
    return prefix + "-" + Date.now().toString(36) + "-" + (uidCounter++);
  }

  function loadState() {
    try {
      var raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return { cards: [], looseTokens: [] };
      var parsed = JSON.parse(raw);
      return {
        cards: Array.isArray(parsed.cards) ? parsed.cards : [],
        looseTokens: Array.isArray(parsed.looseTokens) ? parsed.looseTokens : []
      };
    } catch (err) {
      return { cards: [], looseTokens: [] };
    }
  }

  function saveState() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch (err) {
      // localStorage unavailable (private mode, quota) -- desk still works this session
    }
  }

  // ---- Tray rendering ----

  function renderTray() {
    trayTokens.innerHTML = "";
    TOKENS.forEach(function (token) {
      var el = document.createElement("div");
      el.className = "token";
      el.dataset.tokenId = token.id;
      el.setAttribute("role", "button");
      el.setAttribute("tabindex", "0");
      el.setAttribute("aria-label", token.label + " — " + token.meaning);
      el.textContent = token.emoji;

      var tip = document.createElement("div");
      tip.className = "token-tooltip";
      tip.textContent = token.label + " — " + token.meaning;
      el.appendChild(tip);

      el.addEventListener("pointerdown", function (ev) {
        startTrayDrag(ev, token);
      });
      trayTokens.appendChild(el);
    });
  }

  // ---- Desk rendering ----

  function renderDesk() {
    deskSurface.innerHTML = "";

    if (state.cards.length === 0 && state.looseTokens.length === 0) {
      var hint = document.createElement("div");
      hint.className = "desk-empty-hint";
      hint.textContent = "The desk is empty. Add a card, or drag a token straight onto the wood.";
      deskSurface.appendChild(hint);
    }

    state.cards.forEach(renderCard);
    state.looseTokens.forEach(renderLooseToken);
  }

  function renderCard(card) {
    var el = document.createElement("div");
    el.className = "desk-card";
    el.dataset.cardId = card.id;
    el.style.left = card.x + "px";
    el.style.top = card.y + "px";
    el.style.transform = "rotate(" + (card.tilt || 0) + "deg)";

    var del = document.createElement("button");
    del.className = "desk-card-delete";
    del.type = "button";
    del.textContent = "✕";
    del.title = "Remove card";
    del.addEventListener("pointerdown", function (ev) { ev.stopPropagation(); });
    del.addEventListener("click", function (ev) {
      ev.stopPropagation();
      state.cards = state.cards.filter(function (c) { return c.id !== card.id; });
      saveState();
      renderDesk();
    });
    el.appendChild(del);

    var text = document.createElement("div");
    text.className = "desk-card-text";
    text.contentEditable = "true";
    text.textContent = card.text || "";
    text.addEventListener("pointerdown", function (ev) { ev.stopPropagation(); });
    text.addEventListener("input", function () {
      card.text = text.textContent;
      saveState();
    });
    el.appendChild(text);

    if (card.tokens && card.tokens.length) {
      var badges = document.createElement("div");
      badges.className = "desk-card-badges";
      card.tokens.forEach(function (tokenId, idx) {
        var token = TOKENS_BY_ID[tokenId];
        if (!token) return;
        var badge = document.createElement("span");
        badge.className = "card-badge";
        badge.title = token.label + " — " + token.meaning;
        var remove = document.createElement("span");
        remove.className = "badge-remove";
        remove.textContent = "✕";
        remove.addEventListener("pointerdown", function (ev) { ev.stopPropagation(); });
        remove.addEventListener("click", function (ev) {
          ev.stopPropagation();
          card.tokens.splice(idx, 1);
          saveState();
          renderDesk();
        });
        badge.textContent = token.emoji + " ";
        badge.appendChild(remove);
        badges.appendChild(badge);
      });
      el.appendChild(badges);
    }

    if (card.log && card.log.length) {
      var log = document.createElement("div");
      log.className = "desk-card-log";
      card.log.slice(-5).forEach(function (line) {
        var d = document.createElement("div");
        d.textContent = line;
        log.appendChild(d);
      });
      el.appendChild(log);
    }

    el.addEventListener("pointerdown", function (ev) {
      startCardDrag(ev, card, el);
    });

    deskSurface.appendChild(el);
  }

  function renderLooseToken(loose) {
    var token = TOKENS_BY_ID[loose.tokenType];
    if (!token) return;
    var el = document.createElement("div");
    el.className = "loose-token";
    el.style.left = loose.x + "px";
    el.style.top = loose.y + "px";
    el.style.background = "radial-gradient(circle at 32% 28%, #f2d9a0, #b8863f 60%, #8a5f28 100%)";
    el.style.border = "2px solid #6b4720";
    el.style.boxShadow = "0 3px 0 #4a3115, 0 6px 10px rgba(0,0,0,0.5)";
    el.title = token.label + " — " + token.meaning;
    el.textContent = token.emoji;
    el.addEventListener("pointerdown", function (ev) {
      startLooseTokenDrag(ev, loose, el);
    });
    deskSurface.appendChild(el);
  }

  // ---- Dragging: new token from tray ----

  function startTrayDrag(ev, token) {
    ev.preventDefault();
    dragGhost.textContent = token.emoji;
    dragGhost.style.display = "flex";
    moveGhost(ev.clientX, ev.clientY);

    function onMove(mv) {
      moveGhost(mv.clientX, mv.clientY);
      highlightDropTarget(mv.clientX, mv.clientY);
    }

    function onUp(up) {
      document.removeEventListener("pointermove", onMove);
      document.removeEventListener("pointerup", onUp);
      dragGhost.style.display = "none";
      clearDropTargetHighlight();

      var cardEl = cardElementAtPoint(up.clientX, up.clientY);
      if (cardEl) {
        attachTokenToCard(cardEl.dataset.cardId, token.id);
        return;
      }
      var deskRect = deskSurface.getBoundingClientRect();
      if (pointInRect(up.clientX, up.clientY, deskRect)) {
        state.looseTokens.push({
          id: uid("loose"),
          tokenType: token.id,
          x: up.clientX - deskRect.left - 23,
          y: up.clientY - deskRect.top - 23
        });
        saveState();
        renderDesk();
      }
      // dropped outside the desk entirely (e.g. back over the tray) -- discard, no-op
    }

    document.addEventListener("pointermove", onMove);
    document.addEventListener("pointerup", onUp);
  }

  // ---- Dragging: existing loose token on the desk ----

  function startLooseTokenDrag(ev, loose, el) {
    ev.preventDefault();
    ev.stopPropagation();
    var deskRect = deskSurface.getBoundingClientRect();
    var offsetX = ev.clientX - (deskRect.left + loose.x);
    var offsetY = ev.clientY - (deskRect.top + loose.y);
    el.style.zIndex = "60";

    function onMove(mv) {
      loose.x = mv.clientX - deskRect.left - offsetX;
      loose.y = mv.clientY - deskRect.top - offsetY;
      el.style.left = loose.x + "px";
      el.style.top = loose.y + "px";
      highlightDropTarget(mv.clientX, mv.clientY);
    }

    function onUp(up) {
      document.removeEventListener("pointermove", onMove);
      document.removeEventListener("pointerup", onUp);
      clearDropTargetHighlight();

      var cardEl = cardElementAtPoint(up.clientX, up.clientY);
      if (cardEl) {
        state.looseTokens = state.looseTokens.filter(function (t) { return t.id !== loose.id; });
        attachTokenToCard(cardEl.dataset.cardId, loose.tokenType);
        return;
      }
      saveState();
    }

    document.addEventListener("pointermove", onMove);
    document.addEventListener("pointerup", onUp);
  }

  // ---- Dragging: existing card ----

  function startCardDrag(ev, card, el) {
    if (ev.target.closest(".desk-card-text") || ev.target.closest(".desk-card-delete") || ev.target.closest(".badge-remove")) {
      return;
    }
    ev.preventDefault();
    var deskRect = deskSurface.getBoundingClientRect();
    var offsetX = ev.clientX - (deskRect.left + card.x);
    var offsetY = ev.clientY - (deskRect.top + card.y);
    el.classList.add("dragging");

    function onMove(mv) {
      card.x = mv.clientX - deskRect.left - offsetX;
      card.y = mv.clientY - deskRect.top - offsetY;
      el.style.left = card.x + "px";
      el.style.top = card.y + "px";
    }

    function onUp() {
      document.removeEventListener("pointermove", onMove);
      document.removeEventListener("pointerup", onUp);
      el.classList.remove("dragging");
      saveState();
    }

    document.addEventListener("pointermove", onMove);
    document.addEventListener("pointerup", onUp);
  }

  // ---- Shared helpers ----

  function moveGhost(x, y) {
    dragGhost.style.left = x + "px";
    dragGhost.style.top = y + "px";
  }

  function cardElementAtPoint(x, y) {
    var el = document.elementFromPoint(x, y);
    return el ? el.closest(".desk-card") : null;
  }

  function highlightDropTarget(x, y) {
    clearDropTargetHighlight();
    var cardEl = cardElementAtPoint(x, y);
    if (cardEl) cardEl.classList.add("drop-target");
  }

  function clearDropTargetHighlight() {
    var highlighted = deskSurface.querySelectorAll(".drop-target");
    highlighted.forEach(function (el) { el.classList.remove("drop-target"); });
  }

  function pointInRect(x, y, rect) {
    return x >= rect.left && x <= rect.right && y >= rect.top && y <= rect.bottom;
  }

  function attachTokenToCard(cardId, tokenId) {
    var card = state.cards.find(function (c) { return c.id === cardId; });
    if (!card) return;
    var token = TOKENS_BY_ID[tokenId];
    if (!token) return;
    card.tokens = card.tokens || [];
    card.tokens.push(tokenId);
    card.log = card.log || [];
    card.log.push(token.emoji + " " + token.label + " → " + token.log);
    saveState();
    renderDesk();
  }

  // ---- Toolbar actions ----

  newCardBtn.addEventListener("click", function () {
    var deskRect = deskSurface.getBoundingClientRect();
    var count = state.cards.length;
    state.cards.push({
      id: uid("card"),
      text: "",
      x: 24 + (count % 4) * 40,
      y: 24 + (count % 5) * 34,
      tilt: (Math.random() * 4 - 2).toFixed(1),
      tokens: [],
      log: []
    });
    saveState();
    renderDesk();
  });

  clearDeskBtn.addEventListener("click", function () {
    if (!confirm("Clear the whole desk? This removes every card and token.")) return;
    state = { cards: [], looseTokens: [] };
    saveState();
    renderDesk();
  });

  renderTray();
  renderDesk();
})();
