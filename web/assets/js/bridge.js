const fallbackState = {
  watch: {
    name: "Watch state unavailable",
    local_time: "----",
    conn: "Unassigned",
    captain: "Unknown",
    mode: "Fallback"
  },
  mission: {
    title: "Bridge state unavailable",
    status: "Fallback",
    intent: "The Bridge could not load bridge-state.json. Confirm the file exists and serve web/ through a local HTTP server.",
    definition_of_done: "Restore bridge-state.json and reload this page."
  },
  current_task: "Recover the current operational state.",
  waiting_on: ["A readable bridge-state.json response"],
  artifacts: ["Static Bridge fallback display"],
  next_orders: [
    "Confirm bridge-state.json exists",
    "Check the local HTTP server",
    "Reload Bridge"
  ],
  ship_status: {
    ao: "Unknown",
    website: "State unavailable",
    deployment: "Unknown",
    cognition_mode: "Fallback"
  }
};

function setText(selector, value) {
  document.querySelector(selector).textContent = value;
}

function titleCase(value) {
  return value
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

function renderList(selector, entries) {
  const list = document.querySelector(selector);
  list.replaceChildren();
  entries.forEach((entry) => {
    const item = document.createElement("li");
    item.textContent = entry;
    list.append(item);
  });
}

function renderShipStatus(status) {
  const grid = document.querySelector("#shipStatusGrid");
  grid.replaceChildren();
  Object.entries(status).forEach(([key, value]) => {
    const group = document.createElement("div");
    const term = document.createElement("dt");
    const description = document.createElement("dd");
    term.textContent = titleCase(key);
    description.textContent = value;
    group.append(term, description);
    grid.append(group);
  });
}

function renderBridge(state, fallback = false) {
  setText("#connValue", state.watch.conn);
  setText("#watchValue", state.watch.name);
  setText("#missionValue", state.mission.title);
  setText("#modeValue", state.watch.mode);
  setText("#watchTime", state.watch.local_time);
  setText("#captainValue", state.watch.captain);
  setText("#missionStatus", state.mission.status);
  setText("#missionIntent", state.mission.intent);
  setText("#definitionValue", state.mission.definition_of_done);
  setText("#currentTask", state.current_task);

  renderList("#waitingList", state.waiting_on);
  renderList("#artifactList", state.artifacts);
  renderList("#ordersList", state.next_orders);
  renderShipStatus(state.ship_status);

  document
    .querySelector("#missionStatus")
    .classList.toggle("is-fallback", fallback);
}

fetch("bridge-state.json")
  .then((response) => {
    if (!response.ok) {
      throw new Error(`Bridge state unavailable: ${response.status}`);
    }
    return response.json();
  })
  .then((state) => renderBridge(state))
  .catch((error) => {
    const errorPanel = document.querySelector("#bridgeError");
    errorPanel.textContent = `${error.message} Showing fallback operational state.`;
    errorPanel.hidden = false;
    renderBridge(fallbackState, true);
  });
