import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";

export const KRAKEN_CONTACT_ID = "contact.kraken-tripo-v1";
const KRAKEN_MODEL_PATH = "../../web/assets/intake/kraken_tripo_v1.glb";

let modelPromise = null;

function loadKrakenModel() {
  if (!modelPromise) {
    modelPromise = new GLTFLoader().loadAsync(KRAKEN_MODEL_PATH).then((gltf) => {
      const model = gltf.scene;
      const bounds = new THREE.Box3().setFromObject(model);
      const center = bounds.getCenter(new THREE.Vector3());
      model.position.sub(center);
      return model;
    });
  }
  return modelPromise;
}

export function resolveKrakenContactVisual(contact) {
  if (contact.id !== KRAKEN_CONTACT_ID) return null;
  return { kind: "model", requestModel: loadKrakenModel };
}
