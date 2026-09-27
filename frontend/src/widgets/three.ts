import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

/** Reads a CSS colour variable, so 3D scenes follow the day and night theme like the 2D charts. */
export function cssColor(el: HTMLElement, name: string): THREE.Color {
  const probe = document.createElement("span");
  probe.style.color = `var(${name})`;
  el.appendChild(probe);
  const color = new THREE.Color(getComputedStyle(probe).color);
  probe.remove();
  return color;
}

/** A scene with a camera the student rotates with a finger; returns a cleanup function. */
export function createScene(host: HTMLElement, onFrame: () => void, cameraAt: [number, number, number] = [7, 6, 7]) {
  const width = host.clientWidth;
  const height = Math.round(width * 0.75);
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setSize(width, height);
  host.appendChild(renderer.domElement);

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 100);
  camera.position.set(...cameraAt);
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.enablePan = false;

  scene.add(new THREE.AmbientLight(0xffffff, 1.6));
  const sun = new THREE.DirectionalLight(0xffffff, 1.6);
  sun.position.set(5, 10, 4);
  scene.add(sun);

  let frame = 0;
  const loop = () => {
    frame = requestAnimationFrame(loop);
    onFrame();
    controls.update();
    renderer.render(scene, camera);
  };
  loop();

  const cleanup = () => {
    cancelAnimationFrame(frame);
    controls.dispose();
    renderer.dispose();
    renderer.domElement.remove();
  };
  return { scene, camera, cleanup };
}

export { THREE };
