import { finalState, gainFactor, series, stateAt } from "./math.js";

const $ = (id) => document.getElementById(id);
const controls = { mi: $("mi"), mf: $("mf"), re: $("re"), burn: $("burn") };
const presets = {
  modest: { mi: 3, mf: 1, re: 160 },
  launch: { mi: 5, mf: 1, re: 160 },
  extreme: { mi: 100, mf: 1, re: 160 },
  mike: { mi: 10, mf: 1, re: 1 },
};
let playing = false;
let animationFrame = null;

function readUrl() {
  const q = new URLSearchParams(location.search);
  return {
    mi: Number(q.get("mi")) || 10,
    mf: Number(q.get("mf")) || 1,
    re: Number(q.get("re")) || 160,
    burn: Math.max(0, Math.min(1, Number(q.get("burn")) || 0)),
  };
}

function setValues(values) {
  controls.mi.value = values.mi;
  controls.mf.value = Math.min(values.mf, values.mi - 1);
  controls.re.value = values.re;
  controls.burn.value = Math.round((values.burn || 0) * 1000);
}

function values() {
  const mi = Number(controls.mi.value);
  const mf = Math.min(Number(controls.mf.value), mi - 0.01);
  return { mi, mf, re: Number(controls.re.value), fraction: Number(controls.burn.value) / 1000 };
}

function fmt(value) {
  if (Math.abs(value) >= 1000) return value.toLocaleString(undefined, { maximumFractionDigits: 0 });
  return value.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

function pathFor(points, selector, width = 600, height = 210) {
  const max = Math.max(...points.map(selector), Number.EPSILON);
  return points.map((p, i) => {
    const x = 26 + p.fraction * width;
    const y = 224 - selector(p) / max * height;
    return `${i ? "L" : "M"}${x.toFixed(2)},${y.toFixed(2)}`;
  }).join(" ");
}

function drawChart(svg, points, first, second, fraction) {
  const max = Math.max(...points.map(first), ...points.map(second), Number.EPSILON);
  const scaledPath = (selector) => points.map((p, i) => {
    const x = 26 + p.fraction * 600;
    const y = 224 - selector(p) / max * 210;
    return `${i ? "L" : "M"}${x.toFixed(2)},${y.toFixed(2)}`;
  }).join(" ");
  const cursorX = 26 + fraction * 600;
  svg.innerHTML = `
    <line class="axis" x1="26" y1="224" x2="626" y2="224"/>
    <line class="grid" x1="26" y1="119" x2="626" y2="119"/>
    <text x="26" y="248">start</text><text x="586" y="248">fuel spent</text>
    <path class="constant-line" d="${scaledPath(first)}"/>
    <path class="optimal-line" d="${scaledPath(second)}"/>
    <line class="cursor" x1="${cursorX}" y1="10" x2="${cursorX}" y2="224"/>
  `;
}

function updateUrl({ mi, mf, re, fraction }) {
  const q = new URLSearchParams({ mi, mf, re });
  if (fraction) q.set("burn", fraction.toFixed(3));
  history.replaceState(null, "", `${location.pathname}?${q}`);
}

function render() {
  const v = values();
  if (v.mf >= v.mi) {
    controls.mf.value = Math.max(1, v.mi - 1);
    return render();
  }
  controls.mf.max = Math.max(1, v.mi - 1);
  const now = stateAt(v.mi, v.mf, v.re, v.fraction);
  const end = finalState(v.mi, v.mf, v.re);
  const points = series(v.mi, v.mf, v.re);

  $("miOut").textContent = `${fmt(v.mi)} t`;
  $("mfOut").textContent = `${fmt(v.mf)} t`;
  $("reOut").textContent = `${fmt(v.re)} MJ/kg`;
  $("massOut").textContent = `${fmt(now.mass)} t`;
  $("constantDv").textContent = `${fmt(now.constantDv)} km/s`;
  $("optimalDv").textContent = `${fmt(now.optimalDv)} km/s`;
  $("constantVe").textContent = `${fmt(now.constantVe)} km/s`;
  $("optimalVe").textContent = `${fmt(now.optimalVe)} km/s`;
  $("gain").textContent = `${gainFactor(v.mi, v.mf).toFixed(3)}×`;
  $("energyReleased").textContent = `${Math.round(v.fraction * 100)}%`;

  const constantProgress = end.constantDv ? now.constantDv / end.constantDv : 0;
  const optimalProgress = end.optimalDv ? now.optimalDv / end.optimalDv : 0;
  $("constantGhost").style.left = `${12 + constantProgress * 64}%`;
  $("optimalGhost").style.left = `${12 + optimalProgress * 64}%`;
  $("rocket").style.transform = `translateX(${v.fraction * 18}px)`;
  $("exhaust").style.width = `${8 + v.fraction * 33}%`;

  drawChart($("dvChart"), points, p => p.constantDv, p => p.optimalDv, v.fraction);
  drawChart($("veChart"), points, p => p.constantVe, p => p.optimalVe, v.fraction);
  updateUrl(v);
}

function togglePlay() {
  playing = !playing;
  $("play").textContent = playing ? "❚❚ Pause" : "▶ Run burn";
  if (!playing) return cancelAnimationFrame(animationFrame);
  if (Number(controls.burn.value) >= 1000) controls.burn.value = 0;
  let previous = performance.now();
  function step(now) {
    if (!playing) return;
    const advance = (now - previous) / 5;
    previous = now;
    controls.burn.value = Math.min(1000, Number(controls.burn.value) + advance);
    render();
    if (Number(controls.burn.value) >= 1000) {
      playing = false;
      $("play").textContent = "↻ Run again";
      return;
    }
    animationFrame = requestAnimationFrame(step);
  }
  animationFrame = requestAnimationFrame(step);
}

Object.values(controls).forEach(control => control.addEventListener("input", render));
document.querySelectorAll("[data-preset]").forEach(button => button.addEventListener("click", () => {
  setValues({ ...presets[button.dataset.preset], burn: 0 });
  render();
}));
$("play").addEventListener("click", togglePlay);
$("share").addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(location.href);
    $("shareStatus").textContent = "Copied.";
  } catch {
    $("shareStatus").textContent = "URL is ready in the address bar.";
  }
});

$("shareRocketSource").addEventListener("click", async () => {
  const status = $("assetShareStatus");
  const sourceUrl = new URL("assets/mike-lab-rocket-tripo-phone-v2.jpg", location.href);
  status.textContent = "Preparing image…";
  try {
    const response = await fetch(sourceUrl);
    if (!response.ok) throw new Error(`image HTTP ${response.status}`);
    const blob = await response.blob();
    const file = new File([blob], "mike-lab-rocket-tripo-phone-v2.jpg", { type: "image/jpeg" });
    if (navigator.share && (!navigator.canShare || navigator.canShare({ files: [file] }))) {
      await navigator.share({
        title: "Mike Lab rocket source for Tripo",
        text: "Upload this source image to Tripo Image to 3D.",
        files: [file],
      });
      status.textContent = "Image shared. Next: open Tripo.";
      return;
    }
    const link = document.createElement("a");
    link.href = sourceUrl;
    link.download = file.name;
    link.click();
    status.textContent = "Image downloaded. Next: open Tripo.";
  } catch (error) {
    if (error?.name === "AbortError") {
      status.textContent = "Share cancelled; nothing changed.";
    } else {
      status.innerHTML = `Share unavailable. <a href="${sourceUrl}" download>Download the image directly.</a>`;
    }
  }
});

setValues(readUrl());
render();
