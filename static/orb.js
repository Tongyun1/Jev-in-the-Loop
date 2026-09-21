import * as THREE from "https://esm.sh/three@0.180.0";

const vertexShader = `
  uniform float uTime;
  uniform float uEnergy;
  uniform float uMotion;
  uniform float uShape;
  uniform float uDensity;
  varying vec3 vNormal;
  varying vec3 vPosition;
  float waves(vec3 p) {
    return sin(p.x * (4.6 + uShape) + uTime * .9) * sin(p.y * (4.1 + uShape * .7) - uTime * .7)
      + .5 * sin(p.z * (8.2 + uShape * 1.8) + p.x * 3.1 + uTime * 1.4)
      + .23 * sin(p.y * 15.0 - p.z * 7.0 - uTime * 1.8);
  }
  void main() {
    vec3 p = position;
    float densityDetail = sin(p.x * 18.0 + p.y * 9.0 - uTime * 1.7) * uDensity * .045;
    float deformation = waves(normalize(position)) * (.065 + uEnergy * .18 + uDensity * .13) * (.42 + uMotion) + densityDetail;
    p += normal * deformation;
    vNormal = normalize(normalMatrix * normal);
    vPosition = p;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(p, 1.0);
  }
`;

const fragmentShader = `
  uniform vec3 uBase;
  uniform vec3 uHighlight;
  uniform float uTime;
  uniform float uEnergy;
  uniform float uShell;
  varying vec3 vNormal;
  varying vec3 vPosition;
  void main() {
    vec3 n = normalize(vNormal);
    float rim = pow(1.0 - abs(dot(n, vec3(0.0, 0.0, 1.0))), 2.2);
    float veins = sin(vPosition.y * 12.0 + sin(vPosition.x * 8.0 + uTime) * 2.0 - uTime * 1.3);
    float glow = smoothstep(.35, 1.0, veins) * (.14 + uEnergy * .32);
    vec3 color = mix(uBase, uHighlight, .18 + rim * .72 + glow);
    color += uHighlight * rim * (.24 + uEnergy * .48);
    float alpha = uShell > .5 ? rim * .5 + glow * .25 : 1.0;
    gl_FragColor = vec4(color, alpha);
  }
`;

function material(shell = false) {
  return new THREE.ShaderMaterial({
    vertexShader, fragmentShader,
    uniforms: {
      uTime: { value: 0 }, uEnergy: { value: .1 }, uMotion: { value: .35 }, uShape: { value: 0 }, uDensity: { value: 0 },
      uBase: { value: new THREE.Color("#2b4d72") },
      uHighlight: { value: new THREE.Color("#80ceec") },
      uShell: { value: shell ? 1 : 0 },
    },
    transparent: shell,
    depthWrite: !shell,
    blending: shell ? THREE.AdditiveBlending : THREE.NormalBlending,
    side: shell ? THREE.BackSide : THREE.FrontSide,
  });
}

export function createOrb(container, getAudio) {
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(36, 1, .1, 100);
  camera.position.z = 7.5;
  const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true, powerPreference: "high-performance" });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.setClearColor(0x000000, 0);
  container.appendChild(renderer.domElement);

  const coreMaterial = material();
  const shellMaterial = material(true);
  const core = new THREE.Mesh(new THREE.IcosahedronGeometry(1.47, 7), coreMaterial);
  const shell = new THREE.Mesh(new THREE.IcosahedronGeometry(1.57, 6), shellMaterial);
  scene.add(core, shell);

  const particleCount = 520;
  const positions = new Float32Array(particleCount * 3);
  for (let i = 0; i < particleCount; i += 1) {
    const y = 1 - (i / (particleCount - 1)) * 2;
    const radius = Math.sqrt(1 - y * y);
    const angle = i * Math.PI * (3 - Math.sqrt(5));
    const distance = 2.02 + (i % 9) * .035;
    positions[i * 3] = Math.cos(angle) * radius * distance;
    positions[i * 3 + 1] = y * distance;
    positions[i * 3 + 2] = Math.sin(angle) * radius * distance;
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  const particleMaterial = new THREE.PointsMaterial({ color: "#a5dafa", size: .032, transparent: true, opacity: .75, blending: THREE.AdditiveBlending, depthWrite: false });
  const particles = new THREE.Points(geometry, particleMaterial);
  scene.add(particles);

  const haloMaterial = new THREE.MeshBasicMaterial({ color: "#7ab9e4", transparent: true, opacity: .17, side: THREE.DoubleSide, blending: THREE.AdditiveBlending, depthWrite: false });
  const halo = new THREE.Mesh(new THREE.TorusGeometry(2.15, .013, 8, 180), haloMaterial);
  halo.rotation.x = .38;
  scene.add(halo);

  let targetHue = 205, targetMotion = .4, targetLight = .5, targetShape = 0, targetDensity = 0, energy = .12, notePulse = 0;
  let rhythmPulse = 0, rhythmStretch = 0, beatTarget = 0, stretchTarget = 0;
  let renderedHue = targetHue, renderedMotion = targetMotion, renderedLight = targetLight, renderedDensity = targetDensity;
  const clock = new THREE.Clock();
  const base = new THREE.Color(), highlight = new THREE.Color();
  function resize() {
    const width = container.clientWidth, height = container.clientHeight;
    if (!width || !height) return;
    renderer.setSize(width, height, false);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
  }
  const observer = new ResizeObserver(resize); observer.observe(container); resize();

  function frame() {
    const time = clock.getElapsedTime();
    const audio = getAudio();
    energy += ((audio.level || 0) + notePulse * .35 - energy) * .12;
    notePulse *= .92;
    rhythmPulse += (beatTarget - rhythmPulse) * .11;
    rhythmStretch += (stretchTarget - rhythmStretch) * .06;
    beatTarget *= .86;
    stretchTarget *= .955;
    // These rendered values keep a new Jev decision from snapping the orb back to a fresh state.
    const hueDistance = ((targetHue - renderedHue + 540) % 360) - 180;
    renderedHue = (renderedHue + hueDistance * .018 + 360) % 360;
    renderedMotion += (targetMotion - renderedMotion) * .025;
    renderedLight += (targetLight - renderedLight) * .025;
    renderedDensity += (targetDensity - renderedDensity) * .032;
    document.documentElement.style.setProperty("--mood-hue", renderedHue.toFixed(1));
    document.documentElement.style.setProperty("--visual-energy", Math.min(1, energy + renderedDensity * .4).toFixed(3));
    base.setHSL(renderedHue / 360, .72, .22 + renderedLight * .08);
    highlight.setHSL(((renderedHue + 26) % 360) / 360, .9, .56 + renderedLight * .14);
    for (const shader of [coreMaterial, shellMaterial]) {
      shader.uniforms.uTime.value = time;
      shader.uniforms.uEnergy.value = Math.min(1, energy);
      shader.uniforms.uMotion.value = renderedMotion;
      shader.uniforms.uDensity.value = renderedDensity;
      shader.uniforms.uShape.value += (targetShape - shader.uniforms.uShape.value) * .018;
      shader.uniforms.uBase.value.lerp(base, .022);
      shader.uniforms.uHighlight.value.lerp(highlight, .022);
    }
    const densityScale = 1 + renderedDensity * .13 + energy * .035;
    const moodEllipse = (renderedMotion - .42) * .22 + renderedDensity * .2;
    const sway = Math.sin(time * (1.1 + renderedMotion * 1.8)) * (.035 + renderedMotion * .09);
    const tall = 1 + moodEllipse + rhythmStretch * .075 + sway;
    const wide = 1 - moodEllipse * .3 + rhythmPulse * .05 - sway * .3;
    core.scale.set(densityScale * wide, densityScale * tall, densityScale * (1 - moodEllipse * .18));
    shell.scale.set((1 + renderedDensity * .18) * wide, (1 + renderedDensity * .18) * tall, 1 + energy * .05);
    core.rotation.y = time * (.12 + renderedMotion * .14);
    core.rotation.x = Math.sin(time * .17) * .2;
    shell.rotation.y = -time * (.08 + renderedMotion * .1);
    particles.rotation.y = time * (.08 + renderedMotion * .13);
    particles.rotation.z = Math.sin(time * .11) * .13;
    particleMaterial.color.lerp(highlight, .04);
    particleMaterial.size = .022 + energy * .032 + renderedDensity * .037;
    particleMaterial.opacity = .38 + energy * .2 + renderedDensity * .35;
    halo.rotation.z = time * (.12 + renderedMotion * .2);
    halo.scale.set((1 + energy * .08 + renderedDensity * .14) * wide, (1 + energy * .08 + renderedDensity * .14) * tall, 1);
    haloMaterial.color.lerp(highlight, .04);
    haloMaterial.opacity = .12 + energy * .16;
    renderer.render(scene, camera);
    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
  return {
    setMood({ hue, motion, light, shape = 0 }) { targetHue = hue; targetMotion = motion; targetLight = light; targetShape = shape; },
    setDensity(value = 0) { targetDensity = THREE.MathUtils.clamp(value, 0, 1); },
    pulse(strength = 1) { notePulse = Math.max(notePulse, strength); },
    beat(strength = 1, duration = .5) {
      beatTarget = Math.max(beatTarget, THREE.MathUtils.clamp(strength, 0, 1));
      stretchTarget = Math.max(stretchTarget, THREE.MathUtils.clamp(duration / 2.5, 0, 1));
      notePulse = Math.max(notePulse, strength * .4);
    },
  };
}
