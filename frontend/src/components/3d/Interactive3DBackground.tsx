import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { AcousticLatticeScene } from './AcousticLatticeMesh';
import { useScrollAndPointer } from './useScrollPhase';

export interface Interactive3DBackgroundProps {
  visible?: boolean;
  className?: string;
}

/**
 * Interactive 3D Background Canvas.
 *
 * Renders a high-performance procedural 3D voice lattice in the viewport background.
 * Seamlessly responds to user scroll depth and cursor interaction.
 */
export const Interactive3DBackground: React.FC<Interactive3DBackgroundProps> = ({
  visible = true,
  className = '',
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const stateRef = useScrollAndPointer();

  useEffect(() => {
    const container = containerRef.current;
    const canvas = canvasRef.current;
    if (!container || !canvas) return;

    // 1. Initialize Three.js Scene, Camera, Renderer
    const scene = new THREE.Scene();

    const width = container.clientWidth || window.innerWidth;
    const height = container.clientHeight || window.innerHeight;

    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 100);
    camera.position.set(0, 0, 7.5);

    let renderer: THREE.WebGLRenderer | null = null;
    try {
      renderer = new THREE.WebGLRenderer({
        canvas,
        alpha: true,
        antialias: true,
        powerPreference: 'high-performance',
      });
      renderer.setSize(width, height);
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
      renderer.toneMapping = THREE.ACESFilmicToneMapping;
      renderer.toneMappingExposure = 1.1;
    } catch (e) {
      console.warn('[Interactive3DBackground] WebGL initialization failed:', e);
      return;
    }

    // 2. Lighting Setup (Editorial Minimalist Palette)
    const ambientLight = new THREE.AmbientLight(0xffffff, 1.2);
    scene.add(ambientLight);

    const dirLight1 = new THREE.DirectionalLight(0x10b981, 2.5); // Emerald accent light
    dirLight1.position.set(5, 8, 4);
    scene.add(dirLight1);

    const dirLight2 = new THREE.DirectionalLight(0xffffff, 1.0); // Soft key light
    dirLight2.position.set(-5, -4, 2);
    scene.add(dirLight2);

    // 3. Instantiate 3D Object Group
    const latticeScene = new AcousticLatticeScene();
    scene.add(latticeScene.group);

    // 4. Handle Window Resizing
    const handleResize = () => {
      if (!container || !renderer) return;
      const newWidth = container.clientWidth || window.innerWidth;
      const newHeight = container.clientHeight || window.innerHeight;

      camera.aspect = newWidth / newHeight;
      camera.updateProjectionMatrix();

      renderer.setSize(newWidth, newHeight);
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    };

    window.addEventListener('resize', handleResize);

    // 5. Animation Render Loop with delta-time
    const clock = new THREE.Clock();
    let animationFrameId: number;
    let isRunning = true;

    const render = () => {
      if (!isRunning) return;

      const delta = clock.getDelta();
      const time = clock.getElapsedTime();

      const { scrollProgress, targetMouseX, targetMouseY, isReducedMotion } = stateRef.current;

      // Update 3D model transforms and particle physics
      latticeScene.update(time, delta, scrollProgress, targetMouseX, targetMouseY, isReducedMotion);

      if (renderer) {
        renderer.render(scene, camera);
      }

      animationFrameId = requestAnimationFrame(render);
    };

    render();

    // 6. Handle Document Visibility (pause render loop when tab is backgrounded)
    const handleVisibilityChange = () => {
      if (document.hidden) {
        isRunning = false;
        cancelAnimationFrame(animationFrameId);
      } else {
        if (!isRunning) {
          isRunning = true;
          clock.start();
          render();
        }
      }
    };
    document.addEventListener('visibilitychange', handleVisibilityChange);

    // 7. Cleanup
    return () => {
      isRunning = false;
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener('resize', handleResize);
      document.removeEventListener('visibilitychange', handleVisibilityChange);

      latticeScene.dispose();

      if (renderer) {
        renderer.dispose();
      }
    };
  }, []);

  return (
    <div
      ref={containerRef}
      aria-hidden="true"
      className={`pointer-events-none fixed inset-0 z-0 overflow-hidden transition-opacity duration-700 select-none ${
        visible ? 'opacity-100' : 'opacity-0'
      } ${className}`}
    >
      <canvas
        ref={canvasRef}
        className="w-full h-full block"
        style={{ pointerEvents: 'none' }}
      />
    </div>
  );
};

