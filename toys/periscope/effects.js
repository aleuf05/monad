// Mk IV optics post-processing. The pass now runs as GLSL 3 on WebGL2 and
// keeps all lens work in one fullscreen sample stage: mild barrel distortion,
// radial chromatic separation, horizon haze, edge glass, and animated grain.
// The restrained values keep labels/reticle crisp in their separate 2D overlay.

import * as THREE from "three";
import { EffectComposer } from "three/addons/postprocessing/EffectComposer.js";
import { RenderPass } from "three/addons/postprocessing/RenderPass.js";
import { ShaderPass } from "three/addons/postprocessing/ShaderPass.js";
import { OutputPass } from "three/addons/postprocessing/OutputPass.js";

const uniforms = {
  tDiffuse: { value: null },
  uResolution: { value: new THREE.Vector2(1, 1) },
  uTime: { value: 0 },
  uVignetteStrength: { value: 0.62 },
  uFresnelStrength: { value: 0.28 },
  uAberrationStrength: { value: 0.0028 },
  uDistortionStrength: { value: 0.018 },
  uSunScreenX: { value: -10 },
  uSunElevation: { value: 0 },
};

const vertexShader = `
  out vec2 vUv;

  void main() {
    vUv = uv;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`;

const fragmentShader = `
  uniform sampler2D tDiffuse;
  uniform vec2 uResolution;
  uniform float uTime;
  uniform float uVignetteStrength;
  uniform float uFresnelStrength;
  uniform float uAberrationStrength;
  uniform float uDistortionStrength;
  uniform float uSunScreenX;
  uniform float uSunElevation;

  in vec2 vUv;
  layout(location = 0) out vec4 fragColor;

  float hash21(vec2 point) {
    vec3 p3 = fract(vec3(point.xyx) * 0.1031);
    p3 += dot(p3, p3.yzx + 33.33);
    return fract((p3.x + p3.y) * p3.z);
  }

  void main() {
    vec2 centered = vUv - 0.5;
    float radius2 = dot(centered, centered);
    float distanceFromCenter = sqrt(radius2) * 1.41421356237;

    // A slight barrel curve reads as thick observation glass without making
    // contacts swim under the pointer. Clamp keeps all taps inside the frame.
    vec2 distortedUv = 0.5 + centered * (1.0 + radius2 * uDistortionStrength);

    // Water shimmer: a small time-varying UV wobble concentrated on the sea
    // half of the frame (seaMask), so the ocean visibly ripples while the
    // sky/reticle stay stable. Contacts float on the same water and pick up
    // the same wobble, which reads as gentle swell rather than a glitch.
    float seaMask = smoothstep(0.3, 0.66, vUv.y);
    vec2 ripple = vec2(
      sin(vUv.y * 42.0 + uTime * 1.7),
      sin(vUv.x * 58.0 - uTime * 1.3)
    ) * 0.0022 * seaMask;
    distortedUv += ripple;

    vec2 aberration = centered * uAberrationStrength * distanceFromCenter;
    vec2 redUv = clamp(distortedUv - aberration, vec2(0.001), vec2(0.999));
    vec2 greenUv = clamp(distortedUv, vec2(0.001), vec2(0.999));
    vec2 blueUv = clamp(distortedUv + aberration, vec2(0.001), vec2(0.999));

    vec3 color = vec3(
      texture(tDiffuse, redUv).r,
      texture(tDiffuse, greenUv).g,
      texture(tDiffuse, blueUv).b
    );

    // A narrow atmospheric band restores depth at the sea/sky boundary.
    float horizonBand = 1.0 - smoothstep(0.0, 0.13, abs(vUv.y - 0.55));
    color = mix(color, vec3(0.46, 0.66, 0.68), horizonBand * 0.075);

    // Sun glitter: a sparkling warm patch that sweeps across the horizon as
    // bearing turns past the (fixed, world-space) sun heading, scaled by how
    // high the day/night cycle has the sun above the horizon. uSunScreenX is
    // computed per-frame in scene.js from the bearing delta to the sun and
    // the current optics FOV, so it tracks correctly at every zoom tier.
    float sunDistX = vUv.x - uSunScreenX;
    float sunDistY = vUv.y - 0.52;
    float sparkle = hash21(floor(vUv * 240.0) + uTime * 2.6) * 0.8 + 0.5;
    float glitter = exp(-sunDistX * sunDistX * 30.0) * exp(-sunDistY * sunDistY * 150.0);
    color += glitter * sparkle * uSunElevation * vec3(1.0, 0.82, 0.5) * 0.6;

    float edge = smoothstep(0.42, 0.98, distanceFromCenter);
    float rim = smoothstep(0.70, 0.90, distanceFromCenter)
      * (1.0 - smoothstep(0.91, 1.04, distanceFromCenter));
    color += rim * uFresnelStrength * vec3(0.55, 0.78, 0.74);
    color *= mix(1.0, 1.0 - uVignetteStrength, edge);

    // Sub-pixel, time-varying grain breaks up perfectly clean digital color
    // bands. Resolution anchors the pattern to physical pixels as the scope
    // resizes; its amplitude stays intentionally below UI-text contrast.
    vec2 grainCell = floor(vUv * uResolution + vec2(uTime * 37.0, uTime * 19.0));
    float grain = hash21(grainCell) - 0.5;
    color += grain * 0.012 * (0.45 + edge * 0.55);

    fragColor = vec4(color, 1.0);
  }
`;

export function createOpticsEffects({ renderer, scene, camera }) {
  const composer = new EffectComposer(renderer);
  composer.addPass(new RenderPass(scene, camera));

  // ShaderPass only carries a shader object's uniforms/source into its own
  // material; constructing the material here is required to opt into GLSL 3.
  const opticsMaterial = new THREE.ShaderMaterial({
    name: "PeriscopeOpticsGLSL3",
    uniforms: THREE.UniformsUtils.clone(uniforms),
    vertexShader,
    fragmentShader,
    glslVersion: THREE.GLSL3,
  });
  const opticsPass = new ShaderPass(opticsMaterial);
  composer.addPass(opticsPass);
  composer.addPass(new OutputPass());

  return {
    render(now = 0, sun = {}) {
      opticsPass.uniforms.uTime.value = now * 0.001;
      opticsPass.uniforms.uSunScreenX.value = sun.screenX ?? -10;
      opticsPass.uniforms.uSunElevation.value = sun.elevation ?? 0;
      composer.render();
    },
    setSize(width, height) {
      composer.setSize(width, height);
      const pixelRatio = renderer.getPixelRatio();
      opticsPass.uniforms.uResolution.value.set(width * pixelRatio, height * pixelRatio);
    },
  };
}
