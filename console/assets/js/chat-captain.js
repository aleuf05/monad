(function () {
  "use strict";

  var API_BASE = "/chat-captain-api";
  var state = { project: null, messages: [], sending: false };

  var loginScreen = document.getElementById("loginScreen");
  var loginForm = document.getElementById("loginForm");
  var loginPassword = document.getElementById("loginPassword");
  var loginError = document.getElementById("loginError");
  var app = document.getElementById("app");
  var transcriptEl = document.getElementById("transcript");
  var chatForm = document.getElementById("chatForm");
  var chatInput = document.getElementById("chatInput");
  var sendBtn = document.getElementById("sendBtn");
  var modeSelect = document.getElementById("modeSelect");
  var projectSelect = document.getElementById("projectSelect");
  var projectPurpose = document.getElementById("projectPurpose");
  var projectNextAction = document.getElementById("projectNextAction");
  var newProjectBtn = document.getElementById("newProjectBtn");
  var lastBriefEl = document.getElementById("lastBrief");
  var harvestTrayEl = document.getElementById("harvestTray");
  var closeSessionBtn = document.getElementById("closeSessionBtn");
  var providerBadge = document.getElementById("providerBadge");
  var briefBtn = document.getElementById("briefBtn");
  var briefOverlay = document.getElementById("briefOverlay");
  var briefCard = document.getElementById("briefCard");
  var briefCloseBtn = document.getElementById("briefCloseBtn");
  var briefStamp = document.getElementById("briefStamp");
  var briefBody = document.getElementById("briefBody");

  function api(path, options) {
    options = options || {};
    options.headers = Object.assign({ "Content-Type": "application/json" }, options.headers || {});
    return fetch(API_BASE + path, options).then(function (response) {
      return response.json().then(function (body) {
        if (!response.ok) {
          var error = new Error(body.error || "request failed");
          error.status = response.status;
          error.body = body;
          throw error;
        }
        return body;
      });
    });
  }

  function post(path, payload) {
    return api(path, { method: "POST", body: JSON.stringify(payload || {}) });
  }

  function escapeHtml(text) {
    var div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  function renderMessage(role, content) {
    var bubble = document.createElement("div");
    bubble.className = "msg " + role;
    bubble.innerHTML = escapeHtml(content);
    transcriptEl.appendChild(bubble);
    transcriptEl.scrollTop = transcriptEl.scrollHeight;
  }

  function renderTranscript(messages) {
    transcriptEl.innerHTML = "";
    if (!messages.length) {
      renderMessage("system", "No messages yet in this session. Say hello to the Captain.");
      return;
    }
    messages.forEach(function (message) {
      renderMessage(message.role, message.content);
    });
  }

  function renderHarvestItems(items) {
    harvestTrayEl.innerHTML = "";
    if (!items.length) {
      harvestTrayEl.innerHTML = '<p class="harvest-empty">No candidates awaiting review.</p>';
      return;
    }
    items.forEach(function (item) {
      var card = document.createElement("div");
      card.className = "harvest-item";
      card.innerHTML =
        '<span class="harvest-type">' + escapeHtml(item.type) + "</span>" +
        '<div class="harvest-title">' + escapeHtml(item.title) + "</div>" +
        '<div class="harvest-summary">' + escapeHtml(item.summary) + "</div>" +
        '<div class="harvest-actions">' +
        '<button class="accept" data-id="' + item.id + '" data-action="accept">Accept</button>' +
        '<button class="reject" data-id="' + item.id + '" data-action="reject">Reject</button>' +
        "</div>";
      harvestTrayEl.appendChild(card);
    });
  }

  function loadHarvest() {
    return api("/api/harvest?status=candidate").then(function (body) {
      renderHarvestItems(body.items);
    });
  }

  function loadProjects() {
    // No dedicated list endpoint in v1 beyond selecting/creating; keep the
    // current project in the selector so it round-trips correctly.
    if (state.project) {
      var exists = Array.from(projectSelect.options).some(function (option) {
        return option.value === state.project.id;
      });
      if (!exists) {
        var option = document.createElement("option");
        option.value = state.project.id;
        option.textContent = state.project.title;
        projectSelect.appendChild(option);
      }
      projectSelect.value = state.project.id;
      projectPurpose.textContent = state.project.purpose || "";
      projectNextAction.textContent = state.project.next_action ? "Next: " + state.project.next_action : "";
    } else {
      projectSelect.value = "";
      projectPurpose.textContent = "";
      projectNextAction.textContent = "";
    }
  }

  function loadState() {
    return api("/api/state").then(function (body) {
      modeSelect.value = body.state.current_mode;
      providerBadge.textContent = (body.state.provider_name || "Codex") + " · " + (body.usage.remaining_turns) + " turns left today";
      lastBriefEl.textContent = body.state.last_session_brief || "None yet.";
      state.project = body.project;
      loadProjects();
      return api("/api/messages").then(function (messagesBody) {
        renderTranscript(messagesBody.messages);
      });
    });
  }

  function boot() {
    return loadState().then(function () {
      app.hidden = false;
      loginScreen.hidden = true;
      return loadHarvest();
    });
  }

  function renderList(container, items, emptyText) {
    if (!items || !items.length) {
      var empty = document.createElement("p");
      empty.className = "brief-empty";
      empty.textContent = emptyText;
      container.appendChild(empty);
      return;
    }
    var list = document.createElement("ul");
    items.forEach(function (item) {
      var li = document.createElement("li");
      li.textContent = item;
      list.appendChild(li);
    });
    container.appendChild(list);
  }

  function renderBriefSection(title, body) {
    var section = document.createElement("div");
    section.className = "brief-section";
    var heading = document.createElement("h3");
    heading.textContent = title;
    section.appendChild(heading);
    briefBody.appendChild(section);
    return section;
  }

  function renderBrief(brief) {
    briefBody.innerHTML = "";
    briefStamp.textContent = "Full access, executive-level projection · generated " +
      (brief.generated_at || "unknown time") +
      (brief.projection ? " · Context Steward projection, cited sources remain authoritative" : "");

    var course = brief.active_course || {};
    var missionSection = renderBriefSection("Mission", null);
    var missionP = document.createElement("p");
    missionP.textContent = course.mission || "Not recorded.";
    missionSection.appendChild(missionP);

    var goalSection = renderBriefSection("Active course", null);
    var goalP = document.createElement("p");
    goalP.textContent = course.goal || "Not recorded.";
    goalSection.appendChild(goalP);

    var nextSection = renderBriefSection("Next action", null);
    var nextP = document.createElement("p");
    nextP.textContent = course.next_action || "Not recorded.";
    nextSection.appendChild(nextP);

    var truthSection = renderBriefSection("Established truth", null);
    renderList(truthSection, brief.established_truth, "None recorded.");

    var decisionsSection = renderBriefSection("Decisions", null);
    renderList(decisionsSection, brief.decisions, "None recorded.");

    var defectsSection = renderBriefSection("Known defects", null);
    renderList(defectsSection, brief.defects, "None recorded.");
  }

  function openBrief() {
    briefOverlay.hidden = false;
    briefBody.innerHTML = '<p class="brief-empty">Loading…</p>';
    api("/api/brief")
      .then(function (body) {
        renderBrief(body.brief);
      })
      .catch(function (error) {
        briefBody.innerHTML = '<p class="brief-empty">Could not load brief: ' + escapeHtml(error.message || "request failed") + "</p>";
      });
  }

  function closeBrief() {
    briefOverlay.hidden = true;
  }

  briefBtn.addEventListener("click", openBrief);
  briefCloseBtn.addEventListener("click", closeBrief);
  briefOverlay.addEventListener("click", function (event) {
    if (event.target === briefOverlay) closeBrief();
  });
  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape" && !briefOverlay.hidden) closeBrief();
  });

  loginForm.addEventListener("submit", function (event) {
    event.preventDefault();
    loginError.hidden = true;
    post("/login", { password: loginPassword.value })
      .then(function () {
        loginPassword.value = "";
        return boot();
      })
      .then(function () {
        if (/(?:^|[?&])brief=1(?:&|$)/.test(window.location.search)) {
          openBrief();
        }
      })
      .catch(function (error) {
        loginError.textContent = error.status === 429 ? "Too many attempts, wait a minute." : "Incorrect password.";
        loginError.hidden = false;
      });
  });

  chatForm.addEventListener("submit", function (event) {
    event.preventDefault();
    if (state.sending) return;
    var text = chatInput.value.trim();
    if (!text) return;
    state.sending = true;
    sendBtn.disabled = true;
    renderMessage("user", text);
    chatInput.value = "";
    post("/api/chat", { message: text })
      .then(function (body) {
        renderMessage("assistant", body.reply);
        if (body.mode_suggestion && body.mode_suggestion !== modeSelect.value) {
          renderMessage("system", "Captain suggests mode: " + body.mode_suggestion + " (use the Mode selector to switch)");
        }
        if (body.safety_signal) {
          renderMessage("system", "Safety signal: " + body.safety_signal);
        }
        if (body.harvest_proposals && body.harvest_proposals.length) {
          loadHarvest();
        }
        providerBadge.textContent = body.provider + " · " + body.model;
      })
      .catch(function (error) {
        renderMessage("system", "Error: " + (error.message || "request failed"));
      })
      .finally(function () {
        state.sending = false;
        sendBtn.disabled = false;
      });
  });

  modeSelect.addEventListener("change", function () {
    post("/api/mode", { mode: modeSelect.value, reason: "operator changed mode" }).catch(function (error) {
      renderMessage("system", "Could not change mode: " + error.message);
    });
  });

  projectSelect.addEventListener("change", function () {
    if (!projectSelect.value) return;
    post("/api/project", { project_id: projectSelect.value }).then(function (body) {
      state.project = body.project;
      loadProjects();
    });
  });

  newProjectBtn.addEventListener("click", function () {
    var title = window.prompt("New project title:");
    if (!title) return;
    var purpose = window.prompt("Short purpose (optional):") || "";
    post("/api/project", { title: title, purpose: purpose }).then(function (body) {
      state.project = body.project;
      loadProjects();
    });
  });

  harvestTrayEl.addEventListener("click", function (event) {
    var button = event.target.closest("button[data-action]");
    if (!button) return;
    var id = button.getAttribute("data-id");
    var action = button.getAttribute("data-action");
    post("/api/harvest/" + id + "/" + action, {}).then(loadHarvest);
  });

  closeSessionBtn.addEventListener("click", function () {
    if (!window.confirm("Close this session and generate a brief?")) return;
    closeSessionBtn.disabled = true;
    post("/api/session/close", {})
      .then(function (body) {
        renderMessage("system", "Session closed. Brief: " + body.session.brief);
        return post("/api/session/new", {});
      })
      .then(function () {
        return loadState();
      })
      .finally(function () {
        closeSessionBtn.disabled = false;
      });
  });

  // If already authenticated (cookie still valid from a prior visit),
  // boot() succeeds immediately and we skip the login screen.
  boot()
    .then(function () {
      // console/index.html links here with ?brief=1 so the splash's
      // "Captain's Brief" affordance opens the popup the moment the
      // authenticated app is ready, instead of landing on the chat view.
      if (/(?:^|[?&])brief=1(?:&|$)/.test(window.location.search)) {
        openBrief();
      }
    })
    .catch(function () {
      loginScreen.hidden = false;
    });
})();
