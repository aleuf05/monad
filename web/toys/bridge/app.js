(function () {
  "use strict";

  const FLEET_STATE_KEY = window.MonadFleetState?.storageKey || "monad.fleetMotion.state";
  const watchTime = document.querySelector("#watchTime");
  const shipStatus = document.querySelector("#shipStatus");
  const alertLevel = document.querySelector("#alertLevel");
  const conditionValue = document.querySelector("#conditionValue");
  const fleetStateValue = document.querySelector("#fleetStateValue");
  const dataSourceValue = document.querySelector("#dataSourceValue");
  const fleetPositionValue = document.querySelector("#fleetPositionValue");
  const routeValue = document.querySelector("#routeValue");
  const contactValue = document.querySelector("#contactValue");
  const selectedVesselValue = document.querySelector("#selectedVesselValue");
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
  // Periscope) already supports an opt-in live FleetCore feed -- see
  // toys/fleet-motion/README.md. Bridge composes that instrument rather
  // than reimplementing it: passing Bridge's own `?live=1` (and optional
  // `?fleetcoreServer=`) straight through to the embedded iframe's src.
  // The iframe has no `src` in the HTML itself specifically so this is the
  // only load it ever does -- setting `.src` after an unparambed default
  // load would cause a visible reload flash.
  const fleetMotionIframe = document.querySelector('[data-instrument-src="../fleet-motion/"]');
  if (fleetMotionIframe) {
    const bridgeParams = new URLSearchParams(window.location.search);
    const baseSrc = fleetMotionIframe.dataset.instrumentSrc;
    if (bridgeParams.has("live") || bridgeParams.has("fleetcoreServer")) {
      const passthrough = new URLSearchParams();
      if (bridgeParams.has("live")) passthrough.set("live", bridgeParams.get("live"));
      if (bridgeParams.has("fleetcoreServer")) passthrough.set("fleetcoreServer", bridgeParams.get("fleetcoreServer"));
      fleetMotionIframe.src = `${baseSrc}?${passthrough.toString()}`;
    } else {
      fleetMotionIframe.src = baseSrc;
    }
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

    alertLevel.className = routeLegs > 0 ? "is-watch" : "";
    conditionValue.className = state.navigation?.lastNavigationMessage === "Clear" ? "is-watch" : "is-caution";
    if (dataSourceValue) {
      const isLive = state.dataSource === "fleetcore-live";
      dataSourceValue.textContent = isLive ? "FleetCore Live" : "Fleet Motion (Local Sim)";
      dataSourceValue.className = isLive ? "is-live" : "";
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
