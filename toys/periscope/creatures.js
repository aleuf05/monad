import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";

const modelPromises = new Map();

function loadCenteredModel(path) {
  if (!modelPromises.has(path)) {
    modelPromises.set(path, new GLTFLoader().loadAsync(path).then((gltf) => {
      const model = gltf.scene;
      const center = new THREE.Box3().setFromObject(model).getCenter(new THREE.Vector3());
      model.position.sub(center);
      return model;
    }));
  }
  return modelPromises.get(path);
}

export async function loadCreatureManifest() {
  const response = await fetch("./creatures.json", { cache: "no-store" });
  if (!response.ok) throw new Error(`Creature manifest unavailable: HTTP ${response.status}`);
  const manifest = await response.json();
  return (manifest.creatures || []).filter((creature) => creature.enabled);
}

export function creatureContacts(creatures) {
  return creatures.map((creature) => ({
    id: creature.id,
    name: creature.display_name,
    callsign: creature.contact_label,
    mission: "Periscope creature manifest",
    status: "Presentation-staged 3D contact",
    report: "Rendered from the creature manifest; FleetCore ownership is deferred to Living Kraken.",
    bearing: creature.position.bearing,
    range: creature.position.range,
    vesselClass: "scout",
  }));
}

export function createCreatureVisualResolver(creatures) {
  const byId = new Map(creatures.map((creature) => [creature.id, creature]));
  return (contact) => {
    const creature = byId.get(contact.id);
    if (!creature) return null;
    return {
      kind: "model",
      requestModel: () => loadCenteredModel(creature.model_path),
      rotation: creature.rotation,
      scale: creature.scale,
    };
  };
}
