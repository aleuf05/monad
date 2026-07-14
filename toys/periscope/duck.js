// Phase 2: the fabricated Quacken / "Rubber Ducky" contact. Its FleetCore id
// (tools/mission-director/mission_director.py's DUCKY_ID) is the one stable
// identifying field -- the display name ("Quacken") is a derived, title-cased
// callsign and not something to match on.
//
// The GLB (web/assets/models/uss-rubber-ducky.glb) is ~29MB and uncompressed
// (no Draco pass in this repo yet). Loading it eagerly on page load would
// cost every Periscope session that download even when no duck is anywhere
// in world state, which is the common case. Instead: the contact always
// gets the normal sprite placeholder the instant it's sighted (scene.js's
// default path), and the model fetch only starts the first time a duck
// contact actually appears, swapping in once (if) it resolves. A slow
// mobile load is still slow -- this only avoids paying for it when there's
// no duck to see at all.

import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";

export const DUCK_CONTACT_ID = "contact.rubber-ducky";
const DUCK_MODEL_PATH = "../../web/assets/models/uss-rubber-ducky.glb";

let modelPromise = null;

function loadDuckModel() {
  if (!modelPromise) {
    modelPromise = new GLTFLoader().loadAsync(DUCK_MODEL_PATH).then((gltf) => gltf.scene);
  }
  return modelPromise;
}

export function resolveDuckContactVisual(contact) {
  if (contact.id !== DUCK_CONTACT_ID) return null;
  return { kind: "model", requestModel: loadDuckModel };
}
