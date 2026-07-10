const root = document.documentElement;

const fleetData = {
  Admiral: {
    brief: "Sets mission bearing, resolves strategic ambiguity, and keeps Campaign 0 pointed toward a durable fleet.",
    order: "Define the north star.",
    color: "Cyan"
  },
  Captains: {
    brief: "Lead active watches, translate mission intent into orders, and keep the bridge cadence intact.",
    order: "Coordinate the watch.",
    color: "Gold"
  },
  Helmsmen: {
    brief: "Run the loops, keep the ship moving, and carry working memory across execution.",
    order: "Move with discipline.",
    color: "Green"
  },
  Chronicler: {
    brief: "Preserves the story, protects the record, and makes every watch recoverable.",
    order: "Write what happened.",
    color: "Violet"
  },
  Comms: {
    brief: "Share the signal, connect the fleet, and keep context moving between stations.",
    order: "Transmit cleanly.",
    color: "Blue"
  },
  "Public Affairs": {
    brief: "Tell the story outward, shape the visible myth, and keep the crew inspired.",
    order: "Make the signal legible.",
    color: "Copper"
  }
};

const doctrineData = {
  remember: {
    title: "We remember.",
    brief: "Memory is the vessel. Every watch leaves a trace the next watch can inherit."
  },
  think: {
    title: "We think.",
    brief: "Cognition is rented, directed, and returned. The system keeps the useful shape."
  },
  evolve: {
    title: "We evolve.",
    brief: "The fleet is not finished. It revises itself through logs, state, doctrine, and pressure."
  },
  endure: {
    title: "We endure.",
    brief: "Agents come and go. The record persists, and the next watch can resume."
  },
  explore: {
    title: "We explore.",
    brief: "The mission is open. Every loop extends the map without pretending it is complete."
  }
};

const layerData = {
  Doctrine: "Persistent and canonical. Doctrine explains why the fleet exists and how it behaves under pressure.",
  Logs: "Append-only record. Logs preserve what happened, when it happened, and which watch saw it.",
  State: "Current working truth. State captures what the fleet believes right now.",
  Indexes: "Fast retrieval surfaces. Indexes help the crew find the right record at the right moment.",
  Cache: "Disposable acceleration. Cache can be rebuilt whenever truth needs a clean replay."
};

window.addEventListener("pointermove", (event) => {
  const x = Math.round((event.clientX / window.innerWidth) * 100);
  const y = Math.round((event.clientY / window.innerHeight) * 100);
  root.style.setProperty("--cursor-x", `${x}%`);
  root.style.setProperty("--cursor-y", `${y}%`);
});

document.querySelectorAll(".panel").forEach((panel) => {
  panel.addEventListener("pointermove", (event) => {
    const rect = panel.getBoundingClientRect();
    panel.style.setProperty("--panel-x", `${event.clientX - rect.left}px`);
    panel.style.setProperty("--panel-y", `${event.clientY - rect.top}px`);
  });
});

document.querySelectorAll("[data-jump]").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelector(button.dataset.jump)?.scrollIntoView({ behavior: "smooth", block: "start" });
  });
});

document.querySelectorAll(".priority-chip").forEach((chip) => {
  chip.addEventListener("click", () => {
    chip.classList.toggle("is-active");
    const active = [...document.querySelectorAll(".priority-chip.is-active")].map((item) => item.dataset.priority);
    const signal = document.querySelector("#watchSignal");
    signal.textContent = active.length
      ? `Active priorities: ${active.join(", ")}.`
      : "No active priorities. Watch requires new orders.";
  });
});

document.querySelectorAll(".fleet-card").forEach((card) => {
  card.addEventListener("click", () => {
    const role = card.dataset.role;
    const data = fleetData[role];
    document.querySelectorAll(".fleet-card").forEach((item) => item.classList.toggle("is-selected", item === card));
    document.querySelector("#roleTitle").textContent = role;
    document.querySelector("#roleBrief").textContent = data.brief;
    document.querySelector("#roleOrder").textContent = data.order;
    document.querySelector("#roleColor").textContent = data.color;
  });
});

document.querySelectorAll(".doctrine-button").forEach((button) => {
  button.addEventListener("click", () => {
    const data = doctrineData[button.dataset.doctrine];
    document.querySelectorAll(".doctrine-button").forEach((item) => item.classList.toggle("is-selected", item === button));
    document.querySelector("#doctrineTitle").textContent = data.title;
    document.querySelector("#doctrineBrief").textContent = data.brief;
  });
});

document.querySelectorAll(".hierarchy-step").forEach((step) => {
  step.addEventListener("click", () => {
    const layer = step.dataset.layer;
    document.querySelectorAll(".hierarchy-step").forEach((item) => item.classList.toggle("is-selected", item === step));
    document.querySelector("#layerTitle").textContent = layer;
    document.querySelector("#layerBrief").textContent = layerData[layer];
  });
});

document.querySelector("#logForm").addEventListener("submit", (event) => {
  event.preventDefault();
  const eventType = document.querySelector("#eventType").value;
  const status = document.querySelector("#eventStatus").value;
  const note = document.querySelector("#eventNote").value.trim() || "Manual bridge check";
  const now = new Date();
  const time = now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: false });
  const watch = String(document.querySelectorAll("#logBody tr").length + 1).padStart(4, "0");
  const row = document.createElement("tr");
  row.className = "is-new";
  row.innerHTML = `<td>${time}</td><td>${watch}</td><td>${eventType}: ${note}</td><td>${status}</td>`;
  document.querySelector("#logBody").prepend(row);
});
