const archiveList = document.querySelector("#archiveList");
const archiveSignal = document.querySelector("#archiveSignal");
const filterButtons = document.querySelectorAll("[data-log-filter]");

let archiveEntries = [];
let activeFilter = "all";

function setSignal(message) {
  archiveSignal.textContent = message;
}

function entryMatches(entry, filter) {
  return filter === "all" || entry.tags.includes(filter) || entry.station === filter;
}

function renderArchive() {
  const visibleEntries = archiveEntries.filter((entry) => entryMatches(entry, activeFilter));
  archiveList.innerHTML = "";

  if (!visibleEntries.length) {
    archiveList.innerHTML = '<article class="archive-card"><p>No matching logs on this channel.</p></article>';
    setSignal(`No entries found for ${activeFilter}.`);
    return;
  }

  visibleEntries.forEach((entry) => {
    const card = document.createElement("article");
    card.className = "archive-card";
    card.innerHTML = `
      <div class="archive-card-head">
        <div>
          <p class="label">${entry.date} / ${entry.station}</p>
          <h3>${entry.watch}</h3>
        </div>
      </div>
      <p>${entry.summary}</p>
      <p class="source-path">Source: <code>${entry.path}</code></p>
      <ul>
        ${entry.signals.map((signal) => `<li>${signal}</li>`).join("")}
      </ul>
      <div class="archive-tags">
        ${entry.tags.map((tag) => `<span>${tag}</span>`).join("")}
      </div>
    `;
    archiveList.append(card);
  });

  const noun = visibleEntries.length === 1 ? "entry" : "entries";
  setSignal(`${visibleEntries.length} ${noun} on channel ${activeFilter}.`);
}

filterButtons.forEach((button) => {
  button.addEventListener("click", () => {
    activeFilter = button.dataset.logFilter;
    filterButtons.forEach((item) => item.classList.toggle("is-active", item.dataset.logFilter === activeFilter));
    renderArchive();
  });
});

if (window.MONAD_WATCH_LOG) {
  archiveEntries = window.MONAD_WATCH_LOG;
  renderArchive();
} else {
  fetch("assets/data/watch-log.json")
    .then((response) => {
      if (!response.ok) {
        throw new Error(`Archive load failed: ${response.status}`);
      }
      return response.json();
    })
    .then((entries) => {
      archiveEntries = entries;
      renderArchive();
    })
    .catch((error) => {
      archiveList.innerHTML = '<article class="archive-card"><p>Archive data unavailable.</p></article>';
      setSignal(error.message);
    });
}
