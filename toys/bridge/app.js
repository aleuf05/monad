(function () {
  "use strict";

  const FLEET_STATE_KEY = "monad.fleetMotion.state";
  const watchTime = document.querySelector("#watchTime");
  const shipStatus = document.querySelector("#shipStatus");
  const alertLevel = document.querySelector("#alertLevel");
  const conditionValue = document.querySelector("#conditionValue");
  const fleetStateValue = document.querySelector("#fleetStateValue");
  const fleetPositionValue = document.querySelector("#fleetPositionValue");
  const routeValue = document.querySelector("#routeValue");
  const commitValue = document.querySelector("#commitValue");

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
    try {
      const raw = localStorage.getItem(FLEET_STATE_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch (error) {
      return null;
    }
  }

  function updateSharedState() {
    const state = parseFleetState();
    if (!state) {
      shipStatus.textContent = "Standing watch";
      alertLevel.textContent = "Nominal";
      conditionValue.textContent = "Green";
      fleetStateValue.textContent = "Awaiting Fleet Motion";
      fleetPositionValue.textContent = "No state observed";
      routeValue.textContent = "No route observed";
      return;
    }

    const routeLegs = Array.isArray(state.navigation?.routeQueue) ? state.navigation.routeQueue.length : 0;
    const waypoints = Array.isArray(state.navigation?.waypoints) ? state.navigation.waypoints.length : 0;
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

    alertLevel.className = routeLegs > 0 ? "is-watch" : "";
    conditionValue.className = state.navigation?.lastNavigationMessage === "Clear" ? "is-watch" : "is-caution";
  }

  function tick() {
    watchTime.textContent = formatClock(new Date());
    updateSharedState();
  }

  window.addEventListener("storage", (event) => {
    if (event.key === FLEET_STATE_KEY) updateSharedState();
  });

  commitValue.textContent = "main / static runtime";
  tick();
  setInterval(tick, 1000);
})();
