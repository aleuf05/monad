// Periscope three.js render layer. Consumes projected contacts from
// state.js and draws: a textured ocean cylinder (camera sits inside it, so
// bearing changes are real camera yaw -- no manual texture panning needed),
// billboarded per-class contact sprites with a simple wake mark, a
// selection/acquisition ring, and a 2D overlay canvas for the reticle
// graticule and contact labels (crisper as flat 2D than as WebGL text).
//
// Deliberate Mk IV simplifications vs. the old Canvas 2D renderer (noted in
// mk4/ENGINEERING_REPORT.md): no per-contact distance-blur/contrast-pocket
// filters, no horizon haze/glare/grain atmosphere layer, no ambient sea
// drift. The "optics glass" vignette/fresnel/chromatic look is Phase 1's
// job via a real EffectComposer pass, not reproduced here.

import * as THREE from "three";
import { ASSET_PATHS, HORIZON_RATIO, MAX_RANGE, clamp, formatBearing, shortestDelta } from "./state.js";
import { createOpticsEffects } from "./effects.js";

const OCEAN_RADIUS = 480;
const OCEAN_HEIGHT = 260;
const EYE_HEIGHT = 1.7;
const CAMERA_PITCH = -0.1;
const CONTACT_MIN_DISTANCE = 26;
const CONTACT_MAX_DISTANCE = 150;

function degToRad(deg) {
  return (deg * Math.PI) / 180;
}

function positionOnCircle(bearingDeg, radius, height) {
  const angle = degToRad(bearingDeg);
  return new THREE.Vector3(radius * Math.sin(angle), height, -radius * Math.cos(angle));
}

function makeRadialTexture(draw, size = 512) {
  const canvas = document.createElement("canvas");
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext("2d");
  draw(ctx, size);
  const texture = new THREE.CanvasTexture(canvas);
  texture.needsUpdate = true;
  return texture;
}

function makeWakeTexture() {
  return makeRadialTexture((ctx, size) => {
    const gradient = ctx.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
    gradient.addColorStop(0, "rgba(225, 236, 228, 0.55)");
    gradient.addColorStop(0.55, "rgba(148, 188, 185, 0.22)");
    gradient.addColorStop(1, "rgba(148, 188, 185, 0)");
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, size, size);
  });
}

function makeRingTexture(color) {
  return makeRadialTexture((ctx, size) => {
    const cx = size / 2;
    const cy = size / 2;
    ctx.strokeStyle = color;
    ctx.lineWidth = size * 0.045;
    ctx.setLineDash([size * 0.09, size * 0.07]);
    ctx.beginPath();
    ctx.arc(cx, cy, size * 0.4, 0, Math.PI * 2);
    ctx.stroke();
  });
}

export function createPeriscopeScene({ canvas, overlayCanvas }) {
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: false });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(54, 1, 0.5, OCEAN_RADIUS * 1.2);
  camera.rotation.order = "YXZ";
  camera.position.set(0, EYE_HEIGHT, 0);

  const effects = createOpticsEffects({ renderer, scene, camera });

  const overlayCtx = overlayCanvas.getContext("2d");

  const textureLoader = new THREE.TextureLoader();
  const vesselTextureCache = new Map();
  let contactVisualResolver = () => null;

  // Ocean: a large cylinder wrapped once around 360 degrees with the sea
  // plate photo. The source image isn't a true seamless panorama (documented
  // in mk2/REQUIREMENTS.md), so there is one seam at the texture edge --
  // accepted, same tradeoff the old tiled-drawImage pan already had.
  const oceanMaterial = new THREE.MeshBasicMaterial({ color: 0x123138, side: THREE.BackSide, fog: false });
  const oceanGeometry = new THREE.CylinderGeometry(OCEAN_RADIUS, OCEAN_RADIUS, OCEAN_HEIGHT, 64, 1, true);
  const oceanMesh = new THREE.Mesh(oceanGeometry, oceanMaterial);
  oceanMesh.position.set(0, EYE_HEIGHT - OCEAN_HEIGHT * 0.05, 0);
  scene.add(oceanMesh);

  textureLoader.load(
    ASSET_PATHS.sea,
    (texture) => {
      texture.colorSpace = THREE.SRGBColorSpace;
      texture.wrapS = THREE.RepeatWrapping;
      oceanMaterial.map = texture;
      oceanMaterial.color.set(0xffffff);
      oceanMaterial.needsUpdate = true;
    },
    undefined,
    () => {
      // Left as the flat fallback color set above.
    }
  );

  const wakeTexture = makeWakeTexture();
  const selectionRingTexture = makeRingTexture("rgba(138, 215, 193, 0.85)");
  const acquisitionRingTexture = makeRingTexture("rgba(216, 180, 106, 0.85)");

  const selectionRing = new THREE.Sprite(new THREE.SpriteMaterial({ map: selectionRingTexture, transparent: true, depthWrite: false }));
  selectionRing.visible = false;
  scene.add(selectionRing);

  const acquisitionRing = new THREE.Sprite(new THREE.SpriteMaterial({ map: acquisitionRingTexture, transparent: true, depthWrite: false }));
  acquisitionRing.visible = false;
  scene.add(acquisitionRing);

  function vesselTexture(key) {
    if (!vesselTextureCache.has(key)) {
      const path = ASSET_PATHS.vessels[key] || ASSET_PATHS.vessels.scout;
      const entry = { texture: textureLoader.load(path), ready: false, aspect: 1.9 };
      entry.texture.colorSpace = THREE.SRGBColorSpace;
      entry.texture.onUpdate = () => {};
      const image = entry.texture.image;
      const markReady = () => {
        entry.ready = true;
        if (image && image.height) entry.aspect = image.width / image.height;
      };
      if (entry.texture.image && entry.texture.image.complete) markReady();
      else entry.texture.source.data && (entry.texture.source.data.onload = markReady);
      vesselTextureCache.set(key, entry);
    }
    return vesselTextureCache.get(key);
  }

  const contactPool = new Map();

  function distanceForRange(range) {
    const proximity = 1 - clamp(range / MAX_RANGE, 0, 1);
    return CONTACT_MAX_DISTANCE - Math.pow(proximity, 0.8) * (CONTACT_MAX_DISTANCE - CONTACT_MIN_DISTANCE);
  }

  function ensureContactVisual(contact) {
    let entry = contactPool.get(contact.id);
    if (entry) return entry;

    const group = new THREE.Group();
    const custom = contactVisualResolver(contact, contact.profile);
    const spriteMaterial = new THREE.SpriteMaterial({ transparent: true, depthWrite: false });
    const sprite = new THREE.Sprite(spriteMaterial);
    group.add(sprite);

    const wakeMaterial = new THREE.SpriteMaterial({ map: wakeTexture, transparent: true, depthWrite: false, opacity: 0.5 });
    const wake = new THREE.Sprite(wakeMaterial);
    wake.scale.set(6, 2, 1);
    group.add(wake);

    scene.add(group);
    entry = { group, sprite, wake, textureKey: null, customModel: custom };
    contactPool.set(contact.id, entry);
    return entry;
  }

  function syncContact(contact, now) {
    const entry = ensureContactVisual(contact);
    const distance = distanceForRange(contact.range);
    const pos = positionOnCircle(contact.bearing, distance, EYE_HEIGHT);
    entry.group.position.copy(pos);
    entry.group.lookAt(0, EYE_HEIGHT, 0);

    const textureKey = entry.customModel?.textureKey || contact.profile.sprite;
    if (entry.textureKey !== textureKey) {
      entry.textureKey = textureKey;
      const tex = vesselTexture(textureKey);
      entry.sprite.material.map = tex.texture;
      entry.sprite.material.needsUpdate = true;
      entry._texEntry = tex;
    }
    const tex = entry._texEntry;
    const aspect = tex?.ready ? tex.aspect : 1.9;
    const baseSize = distance * 0.34 * contact.profile.size;
    entry.sprite.scale.set(baseSize * aspect, baseSize, 1);
    entry.sprite.material.opacity = clamp(0.55 + (1 - contact.rangeRatio) * 0.4, 0.55, 1) * contact.profile.haze;

    const wakeStrength = clamp(contact.profile.wake * (1 - contact.rangeRatio * 0.6), 0.15, 1);
    entry.wake.material.opacity = wakeStrength * 0.6;
    entry.wake.scale.set(baseSize * 1.6, baseSize * 0.55, 1);
    entry.wake.position.set(-baseSize * 0.1, -baseSize * 0.42, 0);

    entry.lastSeen = now;
    return entry;
  }

  function pruneContacts(seenIds, now) {
    for (const [id, entry] of contactPool.entries()) {
      if (!seenIds.has(id)) {
        scene.remove(entry.group);
        entry.sprite.material.dispose();
        entry.wake.material.dispose();
        contactPool.delete(id);
      }
    }
  }

  function resizeToContainer() {
    const size = Math.round(canvas.getBoundingClientRect().width);
    const ratio = Math.min(window.devicePixelRatio || 1, 2);
    const target = Math.max(320, size);
    renderer.setSize(target, target, true);
    effects.setSize(target, target);
    overlayCanvas.width = Math.round(target * ratio);
    overlayCanvas.height = Math.round(target * ratio);
    camera.aspect = 1;
    camera.updateProjectionMatrix();
  }

  function drawReticle(w, h, optics) {
    const cx = w / 2;
    const cy = h / 2;
    const radius = w * 0.485;

    overlayCtx.strokeStyle = "rgba(229, 242, 238, 0.18)";
    overlayCtx.lineWidth = w * 0.002;
    const horizontalTicks = Math.round(2 * optics.reticleDensity);
    for (let i = -horizontalTicks; i <= horizontalTicks; i += 1) {
      const y = cy + (i * h * 0.092) / optics.reticleDensity;
      overlayCtx.beginPath();
      overlayCtx.moveTo(cx - radius * 0.5, y);
      overlayCtx.lineTo(cx + radius * 0.5, y);
      overlayCtx.stroke();
    }

    overlayCtx.strokeStyle = "rgba(229, 242, 238, 0.22)";
    overlayCtx.beginPath();
    overlayCtx.moveTo(cx, cy - radius * 0.48);
    overlayCtx.lineTo(cx, cy + radius * 0.48);
    overlayCtx.moveTo(cx - radius * 0.08, cy);
    overlayCtx.lineTo(cx + radius * 0.08, cy);
    overlayCtx.stroke();

    overlayCtx.fillStyle = "rgba(226, 240, 236, 0.68)";
    overlayCtx.font = `${Math.max(10, w * 0.012)}px Segoe UI, sans-serif`;
    overlayCtx.fillText(`${optics.magnification}x / ${optics.fov} deg FOV`, w * 0.075, h * 0.89);
  }

  function projectToScreen(worldPosition, w, h) {
    const vector = worldPosition.clone().project(camera);
    return { x: ((vector.x + 1) / 2) * w, y: ((1 - vector.y) / 2) * h };
  }

  function drawContactLabel(contact, screen, w, h, isSelected) {
    const labelWidth = Math.max(w * 0.19, 130);
    const labelHeight = 58;
    const labelX = clamp(screen.x - labelWidth * 0.5, 16, w - labelWidth - 24);
    const labelY = clamp(screen.y - labelHeight - 46, 58, h - labelHeight - 28);

    overlayCtx.fillStyle = isSelected ? "rgba(4, 13, 14, 0.82)" : "rgba(4, 9, 11, 0.68)";
    overlayCtx.strokeStyle = isSelected ? "rgba(138, 215, 193, 0.56)" : "rgba(226, 240, 236, 0.25)";
    overlayCtx.fillRect(labelX, labelY, labelWidth, labelHeight);
    overlayCtx.strokeRect(labelX, labelY, labelWidth, labelHeight);

    overlayCtx.fillStyle = contact.color || "#8ad7c1";
    overlayCtx.font = `${Math.max(11, w * 0.014)}px Segoe UI, sans-serif`;
    overlayCtx.fillText(contact.callsign, labelX + 10, labelY + 18);
    overlayCtx.fillStyle = "rgba(232, 240, 237, 0.9)";
    overlayCtx.font = `${Math.max(10, w * 0.012)}px Segoe UI, sans-serif`;
    overlayCtx.fillText(`${contact.profile?.label || "Vessel"} / ${formatBearing(contact.bearing)}`, labelX + 10, labelY + 35);
    overlayCtx.fillText(`Range ${contact.range.toFixed(1)} nm`, labelX + 10, labelY + 50);

    overlayCtx.strokeStyle = isSelected ? "rgba(138, 215, 193, 0.36)" : "rgba(226, 240, 236, 0.18)";
    overlayCtx.beginPath();
    overlayCtx.moveTo(clamp(screen.x, labelX + 12, labelX + labelWidth - 12), labelY + labelHeight);
    overlayCtx.lineTo(screen.x, screen.y);
    overlayCtx.stroke();
  }

  function render(periscope, contacts, now) {
    camera.rotation.x = CAMERA_PITCH;
    camera.rotation.y = -degToRad(periscope.bearing);
    camera.fov = periscope.optics.fov;
    camera.updateProjectionMatrix();

    const seenIds = new Set(contacts.map((contact) => contact.id));
    contacts.forEach((contact) => syncContact(contact, now));
    pruneContacts(seenIds, now);

    const selected = contacts.find((contact) => contact.id === periscope.selectedId);
    if (selected) {
      const entry = contactPool.get(selected.id);
      selectionRing.visible = true;
      selectionRing.position.copy(entry.group.position).add(new THREE.Vector3(0, entry.sprite.scale.y * 0.78, 0));
      selectionRing.scale.set(entry.sprite.scale.x * 0.26, entry.sprite.scale.x * 0.26, 1);
    } else {
      selectionRing.visible = false;
    }

    const cue = periscope.acquisitionCue;
    const cueContact = contacts.find((contact) => contact.id === cue.contactId);
    const cueAge = now - cue.startedAt;
    if (cueContact && cueAge >= 0 && cueAge < 1600) {
      const entry = contactPool.get(cueContact.id);
      acquisitionRing.visible = true;
      const pulse = 1 - cueAge / 1600;
      acquisitionRing.position.copy(entry.group.position).add(new THREE.Vector3(0, entry.sprite.scale.y * 0.78, 0));
      const ringScale = entry.sprite.scale.x * (0.26 + pulse * 0.12);
      acquisitionRing.scale.set(ringScale, ringScale, 1);
    } else {
      acquisitionRing.visible = false;
    }

    effects.render();

    const w = overlayCanvas.width;
    const h = overlayCanvas.height;
    overlayCtx.clearRect(0, 0, w, h);
    drawReticle(w, h, periscope.optics);
    contacts
      .filter((contact) => contact.visible)
      .forEach((contact) => {
        const entry = contactPool.get(contact.id);
        if (!entry) return;
        const screen = projectToScreen(entry.group.position, w, h);
        drawContactLabel(contact, screen, w, h, contact.id === periscope.selectedId);
      });
  }

  function hitTest(clientX, clientY) {
    const rect = canvas.getBoundingClientRect();
    const ndc = new THREE.Vector2(
      ((clientX - rect.left) / rect.width) * 2 - 1,
      -((clientY - rect.top) / rect.height) * 2 + 1
    );
    const raycaster = new THREE.Raycaster();
    raycaster.setFromCamera(ndc, camera);
    const sprites = Array.from(contactPool.values()).map((entry) => entry.sprite);
    const hits = raycaster.intersectObjects(sprites, false);
    if (!hits.length) return null;
    for (const [id, entry] of contactPool.entries()) {
      if (entry.sprite === hits[0].object) return id;
    }
    return null;
  }

  window.addEventListener("resize", resizeToContainer);
  resizeToContainer();

  return {
    render,
    hitTest,
    resize: resizeToContainer,
    setContactVisualResolver(fn) {
      contactVisualResolver = fn;
    },
  };
}
