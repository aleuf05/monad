(function () {
  "use strict";

  const FLEET_STATE_KEY = window.MonadFleetState?.storageKey || "monad.fleetMotion.state";
  const watchTime = document.querySelector("#watchTime");
  const shipStatus = document.querySelector("#shipStatus");
  const alertLevel = document.querySelector("#alertLevel");
  const conditionValue = document.querySelector("#conditionValue");
  const fleetStateValue = document.querySelector("#fleetStateValue");
  const dataSourceValue = document.querySelector("#dataSourceValue");
  const commandAuthorityValue = document.querySelector("#commandAuthorityValue");
  const fleetPositionValue = document.querySelector("#fleetPositionValue");
  const routeValue = document.querySelector("#routeValue");
  const contactValue = document.querySelector("#contactValue");
  const selectedVesselValue = document.querySelector("#selectedVesselValue");
  const contactRosterList = document.querySelector("#contactRosterList");
  const commandTokenForm = document.querySelector("#commandTokenForm");
  const commandTokenInput = document.querySelector("#commandTokenInput");
  const activeStationValue = document.querySelector("#activeStationValue");
  const commitValue = document.querySelector("#commitValue");
  const stationTabs = Array.from(document.querySelectorAll("[data-station]"));
  const stationPanels = Array.from(document.querySelectorAll("[data-station-panel]"));
  const liveInstruments = Array.from(document.querySelectorAll("[data-live-instrument]"));

  const stationLabels = {
    console: "Live Console",
    watchbook: "Watchbook"
  };

  // Fleet Motion (and, via the shared MonadFleetState contract it writes,
  // Periscope) and Radio Console each independently support an opt-in live
  // FleetCore feed -- see their own READMEs. Bridge composes those
  // instruments rather than reimplementing them: passing Bridge's own
  // `?live=1` (and optional `?fleetcoreServer=`, `?commandToken=`) straight
  // through to whichever embedded iframes declare a `data-instrument-src`.
  // Those iframes have no `src` in the HTML itself specifically so this is
  // the only load they ever do -- setting `.src` after an unparambed
  // default load would cause a visible reload flash. Periscope and
  // Watchbook keep a plain static `src` and are untouched by this:
  // Periscope takes no query params (it just reads whatever Fleet Motion
  // writes), and Watchbook has nothing to do with FleetCore at all.
  //
  // `commandToken` is the one param here that grants write access to the
  // shared FleetCore world (docs/architecture/fleetcore-api.md) -- Bridge
  // never stores or defaults it, purely forwards whatever the operator put
  // in its own URL, same as fleetcoreServer. No token is baked in anywhere
  // in this file for the same reason toys/fleet-motion/app.js doesn't bake
  // one into its own bundle: this page can be the public deployment too.
  const liveCapableIframes = Array.from(document.querySelectorAll("[data-instrument-src]"));
  if (liveCapableIframes.length) {
    const bridgeParams = new URLSearchParams(window.location.search);
    const passthrough = new URLSearchParams();
    if (bridgeParams.has("live")) passthrough.set("live", bridgeParams.get("live"));
    if (bridgeParams.has("fleetcoreServer")) passthrough.set("fleetcoreServer", bridgeParams.get("fleetcoreServer"));
    if (bridgeParams.has("commandToken")) passthrough.set("commandToken", bridgeParams.get("commandToken"));
    const query = passthrough.toString();
    liveCapableIframes.forEach((iframe) => {
      const baseSrc = iframe.dataset.instrumentSrc;
      iframe.src = query ? `${baseSrc}?${query}` : baseSrc;
    });
  }

  // Granting command authority today means editing the URL and reloading
  // all of Bridge, which is a bad fit for something billing itself as a
  // command console. This reloads only the Fleet Motion iframe -- Radio
  // Console also matches [data-instrument-src] above but ignores
  // commandToken entirely, and reloading it for no reason would cut off
  // whatever it's currently playing. Unlike the initial load above (which
  // deliberately avoids ever touching .src twice to prevent a load flash),
  // this reload is operator-triggered on submit, so it's expected.
  const fleetMotionIframe = document.querySelector("#liveFleetMotion iframe");

  function applyCommandToken(token) {
    if (!fleetMotionIframe) return;
    const currentSrc = fleetMotionIframe.src || fleetMotionIframe.dataset.instrumentSrc;
    if (!currentSrc) return;
    const nextSrc = new URL(currentSrc, window.location.href);
    if (token) {
      nextSrc.searchParams.set("commandToken", token);
    } else {
      nextSrc.searchParams.delete("commandToken");
    }
    fleetMotionIframe.src = nextSrc.toString();

    // Mirrors the token into Bridge's own URL (same exposure the existing
    // ?commandToken= passthrough already has) so a page refresh doesn't
    // silently drop authority the operator just granted.
    const pageUrl = new URL(window.location.href);
    if (token) {
      pageUrl.searchParams.set("commandToken", token);
    } else {
      pageUrl.searchParams.delete("commandToken");
    }
    window.history.replaceState(null, "", pageUrl);
  }

  if (commandTokenForm) {
    commandTokenForm.addEventListener("submit", (event) => {
      event.preventDefault();
      applyCommandToken(commandTokenInput.value.trim());
    });
  }

  let hasObservedSelection = false;
  let lastSelectedShipId = null;
  let syncCueTimeout = null;

  function pad(value) {
    return String(value).padStart(2, "0");
  }

  function formatClock(date) {
    return `${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`;
  }

  function formatPosition(position) {
    if (!position || typeof position.lat !== "number" || typeof position.lng !== "number") {
      return "No position observed";
    }
    return `${position.lat.toFixed(4)}, ${position.lng.toFixed(4)}`;
  }

  function parseFleetState() {
    if (window.MonadFleetState?.read) {
      return window.MonadFleetState.read();
    }
    try {
      const raw = localStorage.getItem(FLEET_STATE_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch (error) {
      return null;
    }
  }

  function selectStation(station, focusTab = false) {
    const nextTab = stationTabs.find((tab) => tab.dataset.station === station) || stationTabs[0];
    const nextStation = nextTab?.dataset.station;
    if (!nextStation) return;

    stationTabs.forEach((tab) => {
      const active = tab.dataset.station === nextStation;
      tab.classList.toggle("is-active", active);
      tab.setAttribute("aria-selected", String(active));
      tab.tabIndex = active ? 0 : -1;
    });

    stationPanels.forEach((panel) => {
      const active = panel.dataset.stationPanel === nextStation;
      panel.classList.toggle("is-active", active);
      panel.hidden = !active;
    });

    if (activeStationValue) {
      activeStationValue.textContent = stationLabels[nextStation] || nextStation;
    }
    if (focusTab) {
      nextTab.focus();
    }
  }

  function handleTabKeydown(event) {
    const currentIndex = stationTabs.indexOf(event.currentTarget);
    if (currentIndex === -1) return;

    let nextIndex = currentIndex;
    if (event.key === "ArrowRight" || event.key === "ArrowDown") {
      nextIndex = (currentIndex + 1) % stationTabs.length;
    } else if (event.key === "ArrowLeft" || event.key === "ArrowUp") {
      nextIndex = (currentIndex - 1 + stationTabs.length) % stationTabs.length;
    } else if (event.key === "Home") {
      nextIndex = 0;
    } else if (event.key === "End") {
      nextIndex = stationTabs.length - 1;
    } else {
      return;
    }

    event.preventDefault();
    selectStation(stationTabs[nextIndex].dataset.station, true);
  }

  function triggerSyncCue() {
    liveInstruments.forEach((panel) => panel.classList.remove("is-sync-pulse"));
    // Force reflow so re-adding the class restarts the CSS animation even if a
    // pulse is already mid-flight when a second selection change lands.
    void document.body.offsetWidth;
    liveInstruments.forEach((panel) => panel.classList.add("is-sync-pulse"));
    if (syncCueTimeout) clearTimeout(syncCueTimeout);
    syncCueTimeout = setTimeout(() => {
      liveInstruments.forEach((panel) => panel.classList.remove("is-sync-pulse"));
    }, 900);
  }

  // Additive write path into MonadFleetState.selection, same pattern
  // toys/periscope/app.js's own propagateSelection() already uses for a
  // contact picked directly on the scope: read the full shared state,
  // override only selection.selectedShipId, write the whole object back.
  // Bridge still never touches any other field. Fleet Motion and
  // Periscope each pick this up the normal way (Fleet Motion checks it
  // every frame, Periscope on its own poll) via the native `storage`
  // event, since they're separate browsing contexts (iframes) from
  // Bridge's own top-level document. That event does NOT fire back into
  // the document that made the write, though, so Bridge calls
  // updateSharedState() itself right after writing rather than waiting
  // on its own 1s tick() to notice -- that's also what lets the existing
  // sync-pulse logic (comparing against lastSelectedShipId) fire for a
  // roster click the same way it already does for an iframe-originated one.
  function selectContact(id) {
    const sharedState = window.MonadFleetState?.read?.();
    if (!sharedState || sharedState.selection?.selectedShipId === id) return;
    window.MonadFleetState.write({
      ...sharedState,
      selection: { ...sharedState.selection, selectedShipId: id }
    });
    updateSharedState();
  }

  function renderContactRoster(state, contacts) {
    if (!contactRosterList) return;
    contactRosterList.innerHTML = "";
    if (!state) {
      contactRosterList.innerHTML = '<li class="contact-roster-empty">No contacts observed</li>';
      return;
    }
    const selectedShipId = state.selection?.selectedShipId ?? null;
    const entries = [
      {
        id: "monad",
        name: "MONAD",
        classLabel: "Flagship",
        detail: formatPosition(state.flagship?.position)
      },
      ...contacts.map((contact) => ({
        id: contact.id,
        name: contact.callsign || contact.name,
        // contact.class carries the vessel's own role string (e.g. "civilian
        // dhow"), not the literal "passive-traffic" -- toys/shared/fleet-state.js's
        // toScoutContacts() already tags exactly this distinction onto
        // `source` ("fleet-motion-escort" vs "fleet-motion-passive-contact"),
        // so key off that instead of guessing from role text.
        classLabel: contact.source === "fleet-motion-passive-contact" ? "Local Traffic" : "Fleet Screen",
        detail: `BRG ${String(Math.round(contact.bearing)).padStart(3, "0")}° / RNG ${contact.range.toFixed(1)} nm`
      }))
    ];
    entries.forEach((entry) => {
      const li = document.createElement("li");
      const button = document.createElement("button");
      button.type = "button";
      const isSelected = selectedShipId === entry.id;
      button.className = `contact-roster-item${isSelected ? " is-selected" : ""}`;
      button.setAttribute("aria-pressed", String(isSelected));
      const nameEl = document.createElement("span");
      nameEl.className = "contact-roster-name";
      nameEl.textContent = entry.name;
      const metaEl = document.createElement("span");
      metaEl.className = "contact-roster-meta";
      metaEl.textContent = `${entry.classLabel} · ${entry.detail}`;
      button.appendChild(nameEl);
      button.appendChild(metaEl);
      button.addEventListener("click", () => selectContact(entry.id));
      li.appendChild(button);
      contactRosterList.appendChild(li);
    });
  }

  function updateSharedState() {
    const state = parseFleetState();
    const selectedShipId = state?.selection?.selectedShipId ?? null;
    if (hasObservedSelection && selectedShipId !== lastSelectedShipId) {
      triggerSyncCue();
    }
    lastSelectedShipId = selectedShipId;
    hasObservedSelection = true;

    if (!state) {
      shipStatus.textContent = "Standing watch";
      alertLevel.textContent = "Nominal";
      conditionValue.textContent = "Green";
      fleetStateValue.textContent = "Awaiting Fleet Motion";
      fleetPositionValue.textContent = "No state observed";
      routeValue.textContent = "No route observed";
      if (contactValue) contactValue.textContent = "No contacts observed";
      if (selectedVesselValue) selectedVesselValue.textContent = "No selection observed";
      if (dataSourceValue) {
        dataSourceValue.textContent = "Awaiting Fleet Motion";
        dataSourceValue.className = "";
      }
      if (commandAuthorityValue) {
        commandAuthorityValue.textContent = "Awaiting Fleet Motion";
        commandAuthorityValue.className = "";
      }
      renderContactRoster(null, []);
      return;
    }

    const routeLegs = Array.isArray(state.navigation?.routeQueue) ? state.navigation.routeQueue.length : 0;
    const waypoints = Array.isArray(state.navigation?.waypoints) ? state.navigation.waypoints.length : 0;
    const contacts = window.MonadFleetState?.toScoutContacts
      ? window.MonadFleetState.toScoutContacts(state)
      : Array.isArray(state.contacts?.ships)
        ? state.contacts.ships
        : [];
    const motion = state.time?.timeWarp === 0 ? "Paused" : `${state.time?.timeWarp || 1}x`;
    const speed = Number(state.flagship?.speedKmh || 0);
    const moving = speed > 0.5 && state.time?.timeWarp !== 0;
    const saved = state.savedAt ? new Date(state.savedAt) : null;

    shipStatus.textContent = moving ? "Underway" : "Holding";
    alertLevel.textContent = state.navigation?.lastNavigationMessage || "Nominal";
    conditionValue.textContent = state.navigation?.lastStatus || "Green";
    fleetStateValue.textContent = saved && !Number.isNaN(saved.getTime())
      ? `Observed ${saved.toLocaleTimeString()} / ${motion}`
      : `Observed / ${motion}`;
    fleetPositionValue.textContent = formatPosition(state.flagship?.position);
    routeValue.textContent = `${routeLegs} active leg${routeLegs === 1 ? "" : "s"} / ${waypoints} waypoint${waypoints === 1 ? "" : "s"}`;
    if (contactValue) {
      contactValue.textContent = `${contacts.length} shared contact${contacts.length === 1 ? "" : "s"}`;
    }
    if (selectedVesselValue) {
      const selectedShipId = state.selection?.selectedShipId;
      if (!selectedShipId) {
        selectedVesselValue.textContent = "No selection observed";
      } else if (selectedShipId === "monad") {
        selectedVesselValue.textContent = "Flagship Monad";
      } else {
        const selected = contacts.find((contact) => contact.id === selectedShipId);
        selectedVesselValue.textContent = selected ? selected.name : "No selection observed";
      }
    }
    renderContactRoster(state, contacts);

    alertLevel.className = routeLegs > 0 ? "is-watch" : "";
    conditionValue.className = state.navigation?.lastNavigationMessage === "Clear" ? "is-watch" : "is-caution";
    const isLive = state.dataSource === "fleetcore-live";
    if (dataSourceValue) {
      dataSourceValue.textContent = isLive ? "FleetCore Live" : "Fleet Motion (Local Sim)";
      dataSourceValue.className = isLive ? "is-live" : "";
    }
    // liveCommandAuthority only means anything once actually live -- Fleet
    // Motion's own var is false by default and never toggles true outside
    // a live "connected" message, but be explicit here too rather than
    // trust a local-sim state to always carry it as false.
    if (commandAuthorityValue) {
      if (!isLive) {
        commandAuthorityValue.textContent = "N/A (Local Sim)";
        commandAuthorityValue.className = "";
      } else if (state.liveCommandAuthority) {
        commandAuthorityValue.textContent = "Granted";
        commandAuthorityValue.className = "is-live";
      } else {
        commandAuthorityValue.textContent = "Read-Only";
        commandAuthorityValue.className = "is-caution";
      }
    }
  }

  function tick() {
    watchTime.textContent = formatClock(new Date());
    updateSharedState();
  }

  stationTabs.forEach((tab) => {
    tab.addEventListener("click", () => selectStation(tab.dataset.station));
    tab.addEventListener("keydown", handleTabKeydown);
  });

  window.addEventListener("storage", (event) => {
    if (event.key === FLEET_STATE_KEY) updateSharedState();
  });

  commitValue.textContent = "main / static runtime";
  selectStation("console");
  tick();
  setInterval(tick, 1000);
})();
