const MAX_TERM = 1000000;
const MAX_LENGTH = 35;
const API = "/centaur-math-api/api/contributions";
const $ = (id) => document.getElementById(id);
let current = null;
let contributions = [];

function integer(value) { return Number.isInteger(Number(value)) ? Number(value) : null; }

// n is a Loesch number iff every prime p == 2 (mod 3) occurs to an even
// exponent. This gives an exact failure result before witness construction.
function isLoesch(n) {
  if (n === 0) return true;
  let remaining = n;
  for (let p = 2; p * p <= remaining; p += p === 2 ? 1 : 2) {
    if (remaining % p !== 0) continue;
    let exponent = 0;
    while (remaining % p === 0) { remaining /= p; exponent += 1; }
    if (p % 3 === 2 && exponent % 2 === 1) return false;
  }
  return !(remaining > 1 && remaining % 3 === 2);
}

function witness(n) {
  if (n === 0) return [0, 0];
  // For fixed x, y solves y² + xy + (x²-n)=0. Testing its exact
  // discriminant avoids the millions of blind x/y pairs a grid would need.
  const maxX = Math.floor(Math.sqrt((4 * n) / 3));
  for (let x = 0; x <= maxX; x += 1) {
    const discriminant = 4 * n - 3 * x * x;
    const root = Math.floor(Math.sqrt(discriminant));
    if (root * root !== discriminant) continue;
    if ((root - x) % 2 !== 0) continue;
    const y = (root - x) / 2;
    if (x * x + x * y + y * y === n) return [x, y];
  }
  return null;
}

function classify(n) {
  if (n < 0) return { state: "invalid", label: "invalid term", detail: "negative" };
  if (n > MAX_TERM) return { state: "limit", label: "beyond supported bound", detail: "endpoint limit" };
  if (!isLoesch(n)) return { state: "failure", label: "verified failure", detail: "not representable" };
  const pair = witness(n);
  return pair ? { state: "pass", label: "representable", pair } : { state: "limit", label: "witness not found", detail: "calculation bound" };
}

function readProgression() {
  const start = integer($("startValue").value);
  const step = integer($("stepValue").value);
  const length = integer($("lengthValue").value);
  if (start === null || step === null || length === null) throw new Error("Use whole numbers in all three fields.");
  if (start < 0) throw new Error("Start must be zero or positive.");
  if (step < 1) throw new Error("Step must be positive.");
  if (length < 1 || length > MAX_LENGTH) throw new Error("Length must be between 1 and 35.");
  const endpoint = start + (length - 1) * step;
  if (endpoint > MAX_TERM) throw new Error("This endpoint exceeds the toy’s supported bound of 1,000,000.");
  return { start, step, length, endpoint };
}

function renderProgression() {
  try {
    current = readProgression();
    $("validationMessage").textContent = "";
  } catch (error) {
    current = null;
    $("validationMessage").textContent = error.message;
    $("termRows").innerHTML = "";
    $("progressionSummary").innerHTML = "";
    return;
  }
  const rows = [];
  let passes = 0;
  for (let index = 0; index < current.length; index += 1) {
    const term = current.start + index * current.step;
    const result = classify(term);
    if (result.state === "pass") passes += 1;
    const resultClass = result.state === "pass" ? "cm-pass" : result.state === "failure" ? "cm-fail" : "cm-limit";
    const witnessText = result.pair ? `(${result.pair[0]}, ${result.pair[1]})` : result.detail;
    rows.push(`<tr><td class="term-value">${term}</td><td><span class="cm-badge ${resultClass}">${result.label}</span></td><td class="cm-witness">${witnessText}</td></tr>`);
  }
  $("termRows").innerHTML = rows.join("");
  $("progressionSummary").innerHTML = `<span>${passes}/${current.length} representable</span><span>endpoint: ${current.endpoint}</span>${current.length === 35 ? "<span>challenge view · endpoint is not proven optimal</span>" : ""}`;
  $("computeStatus").textContent = `exact arithmetic · ${current.length} term${current.length === 1 ? "" : "s"}`;
}

function candidatePayload() {
  return { attribution: $("attribution").value, kind: "candidate", note: $("note").value.trim(), ...current };
}

function renderContributions() {
  if (!contributions.length) {
    $("contributionList").innerHTML = '<p class="cm-muted">No shared contributions yet. Be the first curious hand.</p>';
    return;
  }
  $("contributionList").innerHTML = contributions.map((item) => {
    const candidate = item.kind === "candidate" ? ` · ${item.start_value} + ${item.step} × ${item.length - 1} = ${item.endpoint}` : "";
    const date = new Date(item.created_at).toLocaleString([], { dateStyle: "medium", timeStyle: "short" });
    return `<article class="cm-contribution"><div class="cm-contribution-head"><span>${item.attribution} · ${item.kind}</span><span>${candidate}</span></div><p class="cm-contribution-note">${escapeHtml(item.note)}</p><div class="cm-contribution-meta">${date}</div></article>`;
  }).join("");
}

function escapeHtml(value) { return String(value).replace(/[&<>"']/g, (char) => ({ "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;" }[char])); }

async function loadContributions() {
  try {
    const response = await fetch(API, { cache: "no-store" });
    if (!response.ok) throw new Error(`shared API HTTP ${response.status}`);
    contributions = (await response.json()).contributions || [];
    renderContributions();
    $("syncStatus").textContent = `shared · ${contributions.length} saved`;
  } catch (error) {
    $("syncStatus").textContent = `shared state unavailable · ${error.message}`;
  }
}

$("progressionForm").addEventListener("submit", (event) => { event.preventDefault(); renderProgression(); });
$("challengeButton").addEventListener("click", () => { $("lengthValue").value = 35; renderProgression(); });
$("kind").addEventListener("change", () => { $("note").placeholder = $("kind").value === "candidate" ? "What makes this candidate interesting?" : "What did you notice or leave unresolved?"; });
$("contributionForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const kind = $("kind").value;
  if (kind === "candidate" && !current) { $("saveMessage").textContent = "Check a valid progression first."; return; }
  const payload = kind === "candidate" ? candidatePayload() : { attribution: $("attribution").value, kind, note: $("note").value.trim() };
  if (!payload.note) { $("saveMessage").textContent = "Add a short note before saving."; return; }
  try {
    const response = await fetch(API, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "shared save failed");
    $("note").value = "";
    $("saveMessage").textContent = "Saved to the shared deck.";
    await loadContributions();
  } catch (error) { $("saveMessage").textContent = error.message; }
});
$("copySummary").addEventListener("click", async () => {
  const lines = ["Centaur Math: All Hands — Captain session summary", `Current progression: ${current ? `${current.start}, step ${current.step}, length ${current.length}, endpoint ${current.endpoint}` : "invalid or not checked"}`, "Saved contributions:", ...contributions.map((item) => `- ${item.attribution} · ${item.kind}: ${item.note}${item.endpoint == null ? "" : ` [${item.start_value}, ${item.step}, ${item.length}; endpoint ${item.endpoint}]`}`), "Unresolved: a valid candidate does not establish the smallest possible endpoint."];
  try { await navigator.clipboard.writeText(lines.join("\n")); $("copyStatus").textContent = "Copied."; } catch { $("copyStatus").textContent = "Copy unavailable; the live deck remains readable above."; }
});

renderProgression();
loadContributions();
setInterval(loadContributions, 6000);
