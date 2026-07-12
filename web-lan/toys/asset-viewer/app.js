// Manifest lives at web/assets/models/manifest.json (and its web-lan/
// mirror) -- a sibling of web/toys/, same relative-path relationship
// toys/fleet-motion/ already uses for toys/shared/fleet-state.js. This
// toy has no manifest of its own under toys/, so testing straight from
// the source tree always shows the empty state; it only shows real
// models once copied into web/toys/asset-viewer/ or
// web-lan/toys/asset-viewer/ alongside their sibling assets/ dirs.
const MANIFEST_URL = "../../assets/models/manifest.json";

const viewer = document.querySelector("#viewer");
const emptyNote = document.querySelector("#emptyNote");
const modelListEl = document.querySelector("#modelList");
const noModelsNote = document.querySelector("#noModelsNote");
const modelDetail = document.querySelector("#modelDetail");
const detailSource = document.querySelector("#detailSource");
const detailBackend = document.querySelector("#detailBackend");
const detailCreated = document.querySelector("#detailCreated");

function selectModel(entry, li) {
  document.querySelectorAll("#modelList li").forEach((el) => el.classList.remove("is-selected"));
  li.classList.add("is-selected");
  viewer.src = `../../${entry.glb_path.replace(/^web\//, "")}`;
  emptyNote.hidden = true;
  modelDetail.hidden = false;
  detailSource.textContent = entry.source_image || "—";
  detailBackend.textContent = entry.backend || "—";
  detailCreated.textContent = entry.created_at ? new Date(entry.created_at).toLocaleString() : "—";
}

function renderModelList(models) {
  modelListEl.innerHTML = "";
  if (!models.length) {
    noModelsNote.hidden = false;
    emptyNote.hidden = false;
    return;
  }
  noModelsNote.hidden = true;
  models.forEach((entry) => {
    const li = document.createElement("li");
    li.innerHTML = `<span class="model-name">${entry.name}</span><span class="model-meta">${entry.backend}</span>`;
    li.addEventListener("click", () => selectModel(entry, li));
    modelListEl.appendChild(li);
  });
  selectModel(models[0], modelListEl.firstElementChild);
}

fetch(MANIFEST_URL)
  .then((res) => (res.ok ? res.json() : { models: [] }))
  .then((manifest) => renderModelList(manifest.models || []))
  .catch(() => renderModelList([]));
