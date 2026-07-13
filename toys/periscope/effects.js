// Phase 1: optical glass post-processing, layered over the Phase 0 scene via
// a real EffectComposer -- not baked into scene.js's geometry/materials, so
// further effects passes stay additive. One combined shader (vignette +
// fresnel-style edge falloff + chromatic aberration) rather than three
// separate passes, matching the old renderOpticsGlass()'s single-pass shape
// and keeping phone-GPU cost down.

import * as THREE from "three";
import { EffectComposer } from "three/addons/postprocessing/EffectComposer.js";
import { RenderPass } from "three/addons/postprocessing/RenderPass.js";
import { ShaderPass } from "three/addons/postprocessing/ShaderPass.js";
import { OutputPass } from "three/addons/postprocessing/OutputPass.js";

const OpticsGlassShader = {
  uniforms: {
    tDiffuse: { value: null },
    uVignetteStrength: { value: 0.62 },
    uFresnelStrength: { value: 0.28 },
    uAberrationStrength: { value: 0.0028 },
  },
  vertexShader: `
    varying vec2 vUv;
    void main() {
      vUv = uv;
      gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
    }
  `,
  fragmentShader: `
    uniform sampler2D tDiffuse;
    uniform float uVignetteStrength;
    uniform float uFresnelStrength;
    uniform float uAberrationStrength;
    varying vec2 vUv;

    void main() {
      vec2 centered = vUv - 0.5;
      float dist = length(centered) * 1.4142135;

      vec2 dir = centered * uAberrationStrength * dist;
      float r = texture2D(tDiffuse, vUv - dir).r;
      float g = texture2D(tDiffuse, vUv).g;
      float b = texture2D(tDiffuse, vUv + dir).b;
      vec4 color = vec4(r, g, b, 1.0);

      float edge = smoothstep(0.42, 0.98, dist);
      float rim = smoothstep(0.72, 0.92, dist) * (1.0 - smoothstep(0.92, 1.05, dist));
      color.rgb += rim * uFresnelStrength * vec3(0.55, 0.78, 0.74);
      color.rgb *= mix(1.0, 1.0 - uVignetteStrength, edge);

      gl_FragColor = color;
    }
  `,
};

export function createOpticsEffects({ renderer, scene, camera }) {
  const composer = new EffectComposer(renderer);
  composer.addPass(new RenderPass(scene, camera));
  const opticsPass = new ShaderPass(OpticsGlassShader);
  composer.addPass(opticsPass);
  composer.addPass(new OutputPass());

  return {
    render() {
      composer.render();
    },
    setSize(width, height) {
      composer.setSize(width, height);
    },
  };
}
