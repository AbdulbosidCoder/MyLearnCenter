import { useEffect, useRef, useState } from "react";

import { Slider, fmt } from "./common";
import { THREE, createScene, cssColor } from "./three";

// Loss surface: a bowl with a gentle ripple, so the path is not a straight line.
const loss = (x: number, y: number) => 0.25 * x * x + 0.5 * y * y + 0.4 * Math.sin(1.5 * x);
const grad = (x: number, y: number) => [0.5 * x + 0.6 * Math.cos(1.5 * x), y];
const START = [-3.6, 2.6];
// Heights are drawn flatter than the real loss so the whole bowl fits on a phone screen.
const HEIGHT = 0.3;
const h = (x: number, y: number) => loss(x, y) * HEIGHT;

export default function GradientDescent3D({ params }: { params: { lr?: number } }) {
  const host = useRef<HTMLDivElement>(null);
  const [lr, setLr] = useState(params.lr ?? 0.1);
  const [path, setPath] = useState<number[][]>([START]);
  const [auto, setAuto] = useState(false);
  const ball = useRef<THREE.Mesh | null>(null);
  const trail = useRef<THREE.Line | null>(null);

  useEffect(() => {
    const el = host.current!;
    const { scene, cleanup } = createScene(el, () => {}, [8, 7, 8]);
    const size = 8;
    const geometry = new THREE.PlaneGeometry(size, size, 60, 60);
    geometry.rotateX(-Math.PI / 2);
    const pos = geometry.attributes.position;
    for (let i = 0; i < pos.count; i++) pos.setY(i, h(pos.getX(i), pos.getZ(i)));
    geometry.computeVertexNormals();
    const surface = new THREE.Mesh(
      geometry,
      new THREE.MeshStandardMaterial({ color: cssColor(el, "--series-1"), transparent: true, opacity: 0.55, side: THREE.DoubleSide }),
    );
    const wire = new THREE.LineSegments(new THREE.WireframeGeometry(geometry), new THREE.LineBasicMaterial({ color: cssColor(el, "--viz-grid-color"), transparent: true, opacity: 0.35 }));
    scene.add(surface, wire);

    ball.current = new THREE.Mesh(new THREE.SphereGeometry(0.18, 24, 24), new THREE.MeshStandardMaterial({ color: cssColor(el, "--series-2") }));
    scene.add(ball.current);
    trail.current = new THREE.Line(new THREE.BufferGeometry(), new THREE.LineBasicMaterial({ color: cssColor(el, "--series-2") }));
    scene.add(trail.current);
    return cleanup;
  }, []);

  // Move the ball and redraw the path whenever a step is taken.
  useEffect(() => {
    const [x, y] = path[path.length - 1];
    ball.current?.position.set(x, h(x, y) + 0.18, y);
    trail.current?.geometry.setFromPoints(path.map(([px, py]) => new THREE.Vector3(px, h(px, py) + 0.05, py)));
  }, [path]);

  const step = () =>
    setPath((p) => {
      const [x, y] = p[p.length - 1];
      const [gx, gy] = grad(x, y);
      const nx = Math.max(-4, Math.min(4, x - lr * gx));
      const ny = Math.max(-4, Math.min(4, y - lr * gy));
      return [...p, [nx, ny]];
    });

  useEffect(() => {
    if (!auto) return;
    const timer = setInterval(step, 250);
    return () => clearInterval(timer);
  });

  const [x, y] = path[path.length - 1];
  return (
    <div className="viz">
      <div ref={host} className="viz-3d" aria-label="Поверхность функции потерь в 3D и шарик градиентного спуска" />
      <p className="viz-readout">
        Шаг {path.length - 1}: потеря = <strong>{fmt(loss(x, y), 3)}</strong>. Поворачивайте поверхность пальцем.
      </p>
      <Slider label="Скорость обучения" value={lr} min={0.02} max={1.9} step={0.02} onChange={setLr} />
      <div className="viz-buttons">
        <button className="small" onClick={step}>
          Шаг
        </button>
        <button className="small" onClick={() => setAuto(!auto)}>
          {auto ? "Пауза" : "Авто"}
        </button>
        <button className="small chip" onClick={() => { setAuto(false); setPath([START]); }}>
          Сначала
        </button>
      </div>
      <p className="muted small">Попробуйте скорость больше 1.5: шарик начнёт прыгать через ямку.</p>
    </div>
  );
}
