const fallbackFleet = {
  vessels: [
    {
      name: "GANTRY",
      hull: "FFG-01",
      role: "Development yard / workstation",
      status: "STANDBY",
      mission: "Builds repo changes and Codex tasks",
      signal: "Codex bounded"
    },
    {
      name: "GRANITE",
      hull: "DDG-02",
      role: "Engine-room server",
      status: "ONLINE",
      mission: "Serves Monad over LAN",
      signal: "Caddy verified / HTTP 200"
    },
    {
      name: "ROCK64",
      hull: "PG-03",
      role: "Public edge / harbor gate",
      status: "ONLINE",
      mission: "Publishes Monad to outside world",
      signal: "Public /monad confirmed"
    },
    {
      name: "SIGNAL",
      hull: "AUX-04",
      role: "Music workstation / audio deck",
      status: "DOCKED",
      mission: "Logic, music systems, future Flight Recorder Box",
      signal: "Awaiting tasking"
    },
    {
      name: "MONAD",
      hull: "FLAGSHIP",
      role: "Cognitive operations vessel",
      status: "FORMING",
      mission: "Coordinate human intent, machines, memory, agents, and artifacts",
      signal: "Public live"
    }
  ],
  missions: [
    "Public web check confirmed",
    "Gemini CLI read-only boarding trial",
    "Codex deploy-doctrine patch under review",
    "OpenClaw held as reference architecture only",
    "Admiral Bot / blog / Flight Recorder ideas in design space"
  ]
};

const statusClass = {
  ONLINE: "status-online",
  STANDBY: "status-standby",
  DOCKED: "status-docked",
  FORMING: "status-forming",
  WATCHLIST: "status-watchlist"
};

function badge(status) {
  return `<span class="status-badge ${statusClass[status] || ""}">${status}</span>`;
}

function renderFleet(data) {
  const plotGrid = document.querySelector("#plotGrid");
  const rosterBody = document.querySelector("#rosterBody");
  const missionList = document.querySelector("#missionList");

  plotGrid.innerHTML = data.vessels.map((vessel) => `
    <article class="vessel-marker" data-status="${vessel.status}">
      <p class="label">${vessel.hull}</p>
      <h3>${vessel.name}</h3>
      <p>${vessel.role}</p>
      ${badge(vessel.status)}
      <p><strong>Mission:</strong> ${vessel.mission}</p>
      <p><strong>Signal:</strong> ${vessel.signal}</p>
    </article>
  `).join("");

  rosterBody.innerHTML = data.vessels.map((vessel) => `
    <tr>
      <td>${vessel.name}</td>
      <td>${vessel.hull}</td>
      <td>${vessel.role}</td>
      <td>${badge(vessel.status)}</td>
      <td>${vessel.mission}</td>
      <td>${vessel.signal}</td>
    </tr>
  `).join("");

  missionList.innerHTML = data.missions.map((mission) => `<li>${mission}</li>`).join("");
}

fetch("status/fleet.json")
  .then((response) => {
    if (!response.ok) {
      throw new Error(`Fleet status unavailable: ${response.status}`);
    }
    return response.json();
  })
  .then(renderFleet)
  .catch(() => renderFleet(fallbackFleet));
