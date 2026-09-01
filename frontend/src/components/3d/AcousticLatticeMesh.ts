import * as THREE from 'three';

/**
 * Creates a high-definition radial glow particle texture dynamically in memory.
 * Eliminates harsh square points and produces soft luminous biometric nodes.
 */
function createGlowParticleTexture(): THREE.CanvasTexture {
  const canvas = document.createElement('canvas');
  canvas.width = 64;
  canvas.height = 64;
  const ctx = canvas.getContext('2d');

  if (ctx) {
    const gradient = ctx.createRadialGradient(32, 32, 0, 32, 32, 32);
    gradient.addColorStop(0, 'rgba(255, 255, 255, 1)');
    gradient.addColorStop(0.2, 'rgba(52, 211, 153, 0.9)'); // Mint / Emerald
    gradient.addColorStop(0.5, 'rgba(5, 150, 105, 0.4)');
    gradient.addColorStop(1, 'rgba(0, 0, 0, 0)');

    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, 64, 64);
  }

  const texture = new THREE.CanvasTexture(canvas);
  texture.generateMipmaps = true;
  return texture;
}

/**
 * AcousticLatticeScene manages the multi-tier architectural 3D voice lattice,
 * 5-tier concentric gyroscope rings, geodesic core, and spectral particle constellation.
 */
export class AcousticLatticeScene {
  public group: THREE.Group;

  // 1. Primary Parametric Voice Ribbon
  private ribbonMesh: THREE.Mesh;
  private ribbonMaterial: THREE.MeshStandardMaterial;

  // 2. Inner Biometric Polyhedron Core
  private coreSphere: THREE.LineSegments;
  private coreMaterial: THREE.LineBasicMaterial;
  private innerIcosahedron: THREE.Mesh;
  private innerMaterial: THREE.MeshBasicMaterial;

  // 3. 5 Concentric Architectural Tier Gyroscope Rings (Ingestion, Signal, Models, Fusion, Policy)
  private tierRings: THREE.LineSegments[] = [];
  private ringMaterials: THREE.LineBasicMaterial[] = [];

  // 4. Spectral Biometric Particles
  private particleSystem: THREE.Points;
  private particlePositions: Float32Array;
  private particleInitialPositions: Float32Array;
  private particleCount: number = 550;
  private particleTexture: THREE.CanvasTexture;
  private particleMaterial: THREE.PointsMaterial;

  // Interactive smoothing buffers
  private currentMouseX = 0;
  private currentMouseY = 0;

  constructor() {
    this.group = new THREE.Group();

    // -------------------------------------------------------------------------
    // 1. Primary Acoustic Ribbon Lattice (Parametric Torus Knot)
    // -------------------------------------------------------------------------
    const ribbonGeo = new THREE.TorusKnotGeometry(2.3, 0.4, 160, 32, 2, 3);
    this.ribbonMaterial = new THREE.MeshStandardMaterial({
      color: 0x27272a, // Subtle graphite zinc
      emissive: 0x059669, // Emerald radiance
      emissiveIntensity: 0.18,
      roughness: 0.3,
      metalness: 0.85,
      wireframe: true,
      transparent: true,
      opacity: 0.72,
    });
    this.ribbonMesh = new THREE.Mesh(ribbonGeo, this.ribbonMaterial);
    this.group.add(this.ribbonMesh);

    // -------------------------------------------------------------------------
    // 2. Inner Biometric Resonator Core (Dual Layer Geodesic)
    // -------------------------------------------------------------------------
    const coreGeo = new THREE.IcosahedronGeometry(1.2, 2);
    const coreWireframe = new THREE.WireframeGeometry(coreGeo);
    this.coreMaterial = new THREE.LineBasicMaterial({
      color: 0x10b981, // Crisp emerald
      transparent: true,
      opacity: 0.65,
    });
    this.coreSphere = new THREE.LineSegments(coreWireframe, this.coreMaterial);
    this.group.add(this.coreSphere);

    // Translucent inner core crystal
    const innerGeo = new THREE.DodecahedronGeometry(0.75, 0);
    this.innerMaterial = new THREE.MeshBasicMaterial({
      color: 0x059669,
      wireframe: true,
      transparent: true,
      opacity: 0.45,
    });
    this.innerIcosahedron = new THREE.Mesh(innerGeo, this.innerMaterial);
    this.group.add(this.innerIcosahedron);

    // -------------------------------------------------------------------------
    // 3. 5 Concentric Architectural Gyroscope Rings
    // Representing L1 Ingestion, L2 Signal, L3 Experts, L4 Fusion, L5 Policy
    // -------------------------------------------------------------------------
    const ringRadii = [2.9, 3.25, 3.6, 3.95, 4.3];
    const ringColors = [0x10b981, 0x71717a, 0x059669, 0xa1a1aa, 0x10b981];

    ringRadii.forEach((radius, i) => {
      const ringGeo = new THREE.TorusGeometry(radius, 0.015, 12, 96);
      const ringWireframe = new THREE.WireframeGeometry(ringGeo);
      const material = new THREE.LineBasicMaterial({
        color: ringColors[i],
        transparent: true,
        opacity: 0.3 - i * 0.04,
      });

      const ring = new THREE.LineSegments(ringWireframe, material);
      ring.rotation.x = Math.PI / 2 + (i * Math.PI) / 8;
      ring.rotation.y = (i * Math.PI) / 10;

      this.tierRings.push(ring);
      this.ringMaterials.push(material);
      this.group.add(ring);
    });

    // -------------------------------------------------------------------------
    // 4. Spectral Biometric Particles (Soft Glowing Node Constellation)
    // -------------------------------------------------------------------------
    this.particleTexture = createGlowParticleTexture();
    const particleGeo = new THREE.BufferGeometry();
    this.particlePositions = new Float32Array(this.particleCount * 3);
    this.particleInitialPositions = new Float32Array(this.particleCount * 3);
    const particleColors = new Float32Array(this.particleCount * 3);

    const emeraldColor = new THREE.Color(0x10b981);
    const mintColor = new THREE.Color(0x34d399);
    const slateColor = new THREE.Color(0x71717a);
    const darkColor = new THREE.Color(0x18181b);

    for (let i = 0; i < this.particleCount; i++) {
      const idx = i * 3;
      // Dual-shell spherical dispersion
      const radius = 1.6 + Math.pow(Math.random(), 0.8) * 3.4;
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(Math.random() * 2 - 1);

      const x = radius * Math.sin(phi) * Math.cos(theta);
      const y = radius * Math.sin(phi) * Math.sin(theta);
      const z = radius * Math.cos(phi);

      this.particlePositions[idx] = x;
      this.particlePositions[idx + 1] = y;
      this.particlePositions[idx + 2] = z;

      this.particleInitialPositions[idx] = x;
      this.particleInitialPositions[idx + 1] = y;
      this.particleInitialPositions[idx + 2] = z;

      // Color scheme
      const rand = Math.random();
      const chosenColor = rand > 0.6 ? emeraldColor : rand > 0.3 ? mintColor : rand > 0.1 ? slateColor : darkColor;

      particleColors[idx] = chosenColor.r;
      particleColors[idx + 1] = chosenColor.g;
      particleColors[idx + 2] = chosenColor.b;
    }

    particleGeo.setAttribute('position', new THREE.BufferAttribute(this.particlePositions, 3));
    particleGeo.setAttribute('color', new THREE.BufferAttribute(particleColors, 3));

    this.particleMaterial = new THREE.PointsMaterial({
      size: 0.12,
      map: this.particleTexture,
      vertexColors: true,
      transparent: true,
      opacity: 0.85,
      blending: THREE.NormalBlending,
      depthWrite: false,
    });

    this.particleSystem = new THREE.Points(particleGeo, this.particleMaterial);
    this.group.add(this.particleSystem);

    // Initial placement: gracefully placed on the right-hand hero quadrant
    this.group.position.set(1.6, 0.1, -0.6);
    this.group.scale.set(0.92, 0.92, 0.92);
  }

  /**
   * Section-linked dynamic morphing and continuous smooth physics.
   */
  public update(
    time: number,
    delta: number,
    scrollProgress: number,
    targetMouseX: number,
    targetMouseY: number,
    isReducedMotion: boolean
  ) {
    // Smooth pointer lerp
    this.currentMouseX += (targetMouseX - this.currentMouseX) * 0.055;
    this.currentMouseY += (targetMouseY - this.currentMouseY) * 0.055;

    const baseSpeed = isReducedMotion ? 0.05 : 0.22;

    // --- 1. Continuous Organic Rotations ---
    this.ribbonMesh.rotation.x += delta * baseSpeed * 0.75;
    this.ribbonMesh.rotation.y += delta * baseSpeed * 1.05;

    this.coreSphere.rotation.x -= delta * baseSpeed * 0.55;
    this.coreSphere.rotation.z += delta * baseSpeed * 0.85;

    this.innerIcosahedron.rotation.y += delta * baseSpeed * 1.4;
    this.innerIcosahedron.rotation.z -= delta * baseSpeed * 0.7;

    // Rotate concentric tier rings on independent axes
    this.tierRings.forEach((ring, i) => {
      const ringSpeed = (i % 2 === 0 ? 1 : -1) * (0.15 + i * 0.05);
      ring.rotation.z += delta * baseSpeed * ringSpeed;
    });

    // --- 2. Interactive Cursor Parallax ---
    const mouseTiltX = this.currentMouseY * 0.32;
    const mouseTiltY = this.currentMouseX * 0.42;

    // --- 3. High-Fidelity Section-Linked Choreography ---
    // Smoothly stages the 3D entity across the 6 editorial page blocks:
    //  0.00 - 0.15 -> Section 0: Hero (Right quadrant harmony)
    //  0.15 - 0.32 -> Section 1: Problem Landscape (Left background, synthetic perturbation)
    //  0.32 - 0.50 -> Section 2: Raw Signal Intake (Horizontal Fourier wave plane)
    //  0.50 - 0.68 -> Section 3: 5-Tier Architecture (Fanning out concentric rings)
    //  0.68 - 0.85 -> Section 4: Context & Policy (Geometric security convergence)
    //  0.85 - 1.00 -> Section 5: Live Detection & Closing (Ambient horizon lock)

    if (scrollProgress < 0.15) {
      // -------------------------------------------------------------
      // Section 0: HERO (Right-Hand Acoustic Presence)
      // -------------------------------------------------------------
      const t = scrollProgress / 0.15;
      const targetX = 1.6 - t * 0.6;
      const targetY = 0.1 + Math.sin(time * 0.8) * 0.12;
      const targetZ = -0.6 + t * 0.3;

      this.group.position.set(targetX, targetY, targetZ);
      this.group.rotation.x = mouseTiltX + t * 0.4;
      this.group.rotation.y = mouseTiltY + t * 0.8 + time * 0.05;

      const pulse = 0.92 + Math.sin(time * 1.4) * 0.03;
      this.group.scale.setScalar(pulse);

      this.ribbonMaterial.opacity = 0.72 - t * 0.15;
      this.ribbonMaterial.emissiveIntensity = 0.18 + Math.sin(time * 2) * 0.06;

      // Concentric rings aligned in gyro orbit
      this.tierRings.forEach((ring, i) => {
        ring.position.z = Math.sin(time * 1.5 + i) * 0.05;
      });

    } else if (scrollProgress < 0.32) {
      // -------------------------------------------------------------
      // Section 1: PROBLEM (Perturbed & Fragmented Threat Landscape)
      // -------------------------------------------------------------
      const t = (scrollProgress - 0.15) / 0.17;
      const targetX = 1.0 - t * 2.3; // Moves behind the left contrast cards
      const targetY = -0.15 + Math.cos(time * 1.1) * 0.15;
      const targetZ = -0.3 - t * 0.6;

      this.group.position.set(targetX, targetY, targetZ);
      this.group.rotation.x = mouseTiltX + 0.4 + t * 0.6;
      this.group.rotation.y = mouseTiltY + 0.8 + t * 1.2;

      // Synthetic voice perturbation jitter
      const jitter = isReducedMotion ? 0 : Math.sin(time * 22) * 0.02 * t;
      this.group.scale.set(0.98 + jitter, 0.98 - jitter, 0.98 + jitter);

      this.ribbonMaterial.opacity = 0.52 - t * 0.08;
      this.ribbonMaterial.emissiveIntensity = 0.24 + t * 0.15;

    } else if (scrollProgress < 0.50) {
      // -------------------------------------------------------------
      // Section 2: RAW SIGNAL (Horizontal Fourier Decomposition Plane)
      // -------------------------------------------------------------
      const t = (scrollProgress - 0.32) / 0.18;
      const targetX = -1.3 + t * 1.3; // Centers across the visualizer
      const targetY = -0.35 + Math.sin(time * 0.9) * 0.1;
      const targetZ = -0.9 - t * 0.4;

      this.group.position.set(targetX, targetY, targetZ);
      // Flatten into isometric horizontal plane
      this.group.rotation.x = mouseTiltX + 1.0 + t * 0.5;
      this.group.rotation.y = mouseTiltY + 2.0 + t * 0.8;

      this.group.scale.set(1.15 + t * 0.1, 0.85 - t * 0.1, 1.15 + t * 0.1);
      this.ribbonMaterial.opacity = 0.42;

    } else if (scrollProgress < 0.68) {
      // -------------------------------------------------------------
      // Section 3: HOW IT WORKS (5-Tier Concentric Gyro Stack)
      // -------------------------------------------------------------
      const t = (scrollProgress - 0.50) / 0.18;
      const targetX = 0.0 + t * 1.4; // Glides to the right side of the architecture matrix
      const targetY = 0.05 + Math.cos(time * 0.8) * 0.12;
      const targetZ = -1.3 + t * 0.4;

      this.group.position.set(targetX, targetY, targetZ);
      this.group.rotation.x = mouseTiltX + 1.5 + t * 0.7;
      this.group.rotation.y = mouseTiltY + 2.8 + t * 1.1;

      this.group.scale.setScalar(1.05 + t * 0.08);

      // Fan out the 5 tier rings along Z axis to visibly illustrate the 5 layers!
      this.tierRings.forEach((ring, i) => {
        ring.position.z = (i - 2) * 0.45 * t;
        ring.scale.setScalar(1.0 + t * (i * 0.08));
      });

      this.ribbonMaterial.opacity = 0.48;
      this.coreMaterial.opacity = 0.8;

    } else if (scrollProgress < 0.85) {
      // -------------------------------------------------------------
      // Section 4: CONTEXT & POLICY (Cryptographic Security Prism)
      // -------------------------------------------------------------
      const t = (scrollProgress - 0.68) / 0.17;
      const targetX = 1.4 - t * 2.7; // Shifts to left side behind decision matrix
      const targetY = 0.15 + Math.sin(time * 1.2) * 0.1;
      const targetZ = -0.9 - t * 0.3;

      this.group.position.set(targetX, targetY, targetZ);
      this.group.rotation.x = mouseTiltX + 2.2 + t * 0.6;
      this.group.rotation.y = mouseTiltY + 3.9 + t * 0.9;

      // Reconverge rings tightly into a locked protective gyro-sphere
      this.tierRings.forEach((ring, i) => {
        ring.position.z = (i - 2) * 0.45 * (1 - t);
        ring.scale.setScalar(1.0);
      });

      const defensePulse = 1.02 + Math.sin(time * 2.8) * 0.04;
      this.group.scale.setScalar(defensePulse);

      this.ribbonMaterial.opacity = 0.52;
      this.ribbonMaterial.emissiveIntensity = 0.35;
      this.coreMaterial.color.setHex(0x10b981);

    } else {
      // -------------------------------------------------------------
      // Section 5: LIVE DETECTION & CLOSING (Ambient Horizon Verification)
      // -------------------------------------------------------------
      const t = (scrollProgress - 0.85) / 0.15;
      const targetX = -1.3 + t * 1.3; // Restores to calm center
      const targetY = -0.1 + Math.sin(time * 0.6) * 0.08;
      const targetZ = -1.2 - t * 0.4;

      this.group.position.set(targetX, targetY, targetZ);
      this.group.rotation.x = mouseTiltX + 2.8 + t * 0.4;
      this.group.rotation.y = mouseTiltY + 4.8 + t * 0.6;

      const finalPulse = 0.96 + Math.sin(time * 1.2) * 0.02;
      this.group.scale.setScalar(finalPulse);

      this.ribbonMaterial.opacity = 0.58;
      this.ribbonMaterial.emissiveIntensity = 0.28;
    }

    // --- 4. Organic Particle Harmonic Wave Dynamics ---
    const positions = (this.particleSystem.geometry.attributes.position as THREE.BufferAttribute).array as Float32Array;
    const waveFreq = 1.8;
    const waveSpeed = time * 1.8;

    for (let i = 0; i < this.particleCount; i++) {
      const idx = i * 3;
      const initX = this.particleInitialPositions[idx];
      const initY = this.particleInitialPositions[idx + 1];
      const initZ = this.particleInitialPositions[idx + 2];

      const dist = Math.sqrt(initX * initX + initY * initY + initZ * initZ);
      // Dual harmonic sinusoidal ripple
      const wave = Math.sin(dist * waveFreq - waveSpeed) * 0.07 + Math.cos(initY * 2.5 + time) * 0.03;

      positions[idx] = initX + (initX / (dist + 0.001)) * wave;
      positions[idx + 1] = initY + (initY / (dist + 0.001)) * wave;
      positions[idx + 2] = initZ + (initZ / (dist + 0.001)) * wave;
    }
    this.particleSystem.geometry.attributes.position.needsUpdate = true;
  }

  /**
   * Complete memory cleanup for GPU resources.
   */
  public dispose() {
    this.ribbonMesh.geometry.dispose();
    this.ribbonMaterial.dispose();

    this.coreSphere.geometry.dispose();
    this.coreMaterial.dispose();

    this.innerIcosahedron.geometry.dispose();
    this.innerMaterial.dispose();

    this.tierRings.forEach((ring) => {
      ring.geometry.dispose();
    });
    this.ringMaterials.forEach((mat) => {
      mat.dispose();
    });

    this.particleSystem.geometry.dispose();
    this.particleMaterial.dispose();
    this.particleTexture.dispose();
  }
}
