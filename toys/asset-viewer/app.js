// Manifest lives at web/assets/models/manifest.json -- a sibling of
// web/toys/, same relative-path relationship toys/fleet-motion/ already
// uses for toys/shared/fleet-state.js. This toy has no manifest of its
// own under toys/, so testing straight from the source tree always shows
// the empty state; it only shows real models once copied into
// web/toys/asset-viewer/ alongside its sibling assets/ dir.
const MANIFEST_URL = "../../assets/models/manifest.json";

const viewer = document.querySelector("#viewer");
const emptyNote = document.querySelector("#emptyNote");
const modelListEl = document.querySelector("#modelList");
const noModelsNote = document.querySelector("#noModelsNote");
const modelDetail = document.querySelector("#modelDetail");
const detailSource = document.querySelector("#detailSource");
const detailBackend = document.querySelector("#detailBackend");
const detailCreated = document.querySelector("#detailCreated");
const uploadForm = document.querySelector("#uploadForm");
const uploadInput = document.querySelector("#uploadInput");
const uploadNameInput = document.querySelector("#uploadNameInput");
const uploadButton = document.querySelector("#uploadButton");
const uploadStatus = document.querySelector("#uploadStatus");

// tools/img2asset/serve.py is a separate process on its own port (not
// something Caddy proxies) -- loopback-bound by default, same posture as
// fleetcore-serve, so this only works when Asset Viewer is opened on the
// same host serve.py is running on unless an operator deliberately ran it
// with --bind-all. ?pipelineServer= override mirrors the same query-param
// pattern the rest of this project already uses for fleetcoreServer.
// Generous enough for a real Replicate generation (verified real runs
// take roughly a minute or two), which is now the common case here again
// -- a .glb upload finishes almost instantly but is fine waiting on the
// same timeout.
const PIPELINE_TIMEOUT_MS = 240000;

function pipelineServerUrl() {
  const params = new URLSearchParams(window.location.search);
  return params.get("pipelineServer") || `${window.location.protocol}//${window.location.hostname}:8501`;
}

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

function renderModelList(models, selectName) {
  modelListEl.innerHTML = "";
  if (!models.length) {
    noModelsNote.hidden = false;
    emptyNote.hidden = false;
    return;
  }
  noModelsNote.hidden = true;
  models.forEach((entry) => {
    const li = document.createElement("li");
    const nameEl = document.createElement("span");
    nameEl.className = "model-name";
    nameEl.textContent = entry.name;
    const metaEl = document.createElement("span");
    metaEl.className = "model-meta";
    metaEl.textContent = entry.backend;
    li.appendChild(nameEl);
    li.appendChild(metaEl);
    li.addEventListener("click", () => selectModel(entry, li));
    modelListEl.appendChild(li);
  });
  const targetIndex = selectName ? models.findIndex((entry) => entry.name === selectName) : 0;
  const index = targetIndex === -1 ? 0 : targetIndex;
  selectModel(models[index], modelListEl.children[index]);
}

function loadManifest(selectName) {
  // Caddy sends no Cache-Control on manifest.json (just ETag/Last-Modified),
  // so a plain fetch() lets the browser apply heuristic caching and serve a
  // normal page reload straight from disk cache without even asking the
  // server -- only a hard refresh bypassed it. cache: "no-store" forces
  // every load (including a plain reload) to actually hit the server.
  return fetch(MANIFEST_URL, { cache: "no-store" })
    .then((res) => (res.ok ? res.json() : { models: [] }))
    .then((manifest) => renderModelList(manifest.models || [], selectName))
    .catch(() => renderModelList([]));
}

function setUploadStatus(text, kind) {
  uploadStatus.textContent = text;
  uploadStatus.className = `upload-status${kind ? ` is-${kind}` : ""}`;
}

uploadForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const file = uploadInput.files?.[0];
  if (!file) {
    setUploadStatus("Choose a file first.", "error");
    return;
  }
  const isGlb = file.name.toLowerCase().endsWith(".glb");
  const isImage = /\.(png|jpe?g|webp)$/i.test(file.name);
  if (!isGlb && !isImage) {
    setUploadStatus("Expected an image (to generate) or a .glb (to catalog).", "error");
    return;
  }

  uploadButton.disabled = true;
  setUploadStatus(
    isGlb
      ? "Uploading and cataloging…"
      : "Uploading and generating — this is a real, billed Replicate run, usually a minute or two…"
  );

  const formData = new FormData();
  formData.append("image", file);
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), PIPELINE_TIMEOUT_MS);

  try {
    const response = await fetch(`${pipelineServerUrl()}/generate`, {
      method: "POST",
      body: formData,
      headers: uploadNameInput.value.trim() ? { "X-Output-Name": uploadNameInput.value.trim() } : {},
      signal: controller.signal
    });
    const result = await response.json().catch(() => ({ ok: false, error: `unexpected response (${response.status})` }));
    if (!response.ok || !result.ok) {
      throw new Error(result.error || `pipeline failed (${response.status})`);
    }
    setUploadStatus(`${isGlb ? "Cataloged" : "Generated"} ${result.entry.name}.`, "success");
    uploadForm.reset();
    await loadManifest(result.entry.name);
  } catch (error) {
    // A fetch/network failure (server not running, wrong port, CORS) reads
    // very differently to an operator than a real pipeline error (e.g. the
    // documented ZeroGPU AppError) -- distinguish them rather than showing
    // one generic "failed" message for both.
    const isNetworkFailure = error.name === "AbortError" || error instanceof TypeError;
    setUploadStatus(
      isNetworkFailure
        ? `Pipeline server unreachable at ${pipelineServerUrl()} — is tools/img2asset/serve.py running?`
        : error.message,
      "error"
    );
  } finally {
    clearTimeout(timeout);
    uploadButton.disabled = false;
  }
});

loadManifest();
