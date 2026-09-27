import { useEffect, useMemo, useRef, useState } from "react";

import { Marker, gauss, rng } from "./common";
import { THREE, createScene, cssColor } from "./three";

const CENTERS = [
  [-2, 1.5, -1.5],
  [2, -1, 1.5],
  [0, 2, 2.5],
];

export default function Scatter3D({ params }: { params: { clusters?: number } }) {
  const host = useRef<HTMLDivElement>(null);
  const count = Math.max(2, Math.min(3, params.clusters ?? 3));
  const points = useMemo(() => {
    const rand = rng(5);
    return CENTERS.slice(0, count).flatMap((c, slot) =>
      Array.from({ length: 40 }, () => ({ slot, p: c.map((v) => gauss(rand, v, 0.7)) })),
    );
  }, [count]);
  const [flat, setFlat] = useState(false);
  const flatness = useRef(0);
  const target = useRef(0);
  target.current = flat ? 1 : 0;

  useEffect(() => {
    const el = host.current!;
    const meshes: { mesh: THREE.Mesh; p: number[] }[] = [];
    const { scene, cleanup } = createScene(el, () => {
      // Smoothly squash the height axis to zero: 3D becomes a 2D shadow.
      flatness.current += (target.current - flatness.current) * 0.08;
      for (const { mesh, p } of meshes) mesh.position.set(p[0], p[1] * (1 - flatness.current), p[2]);
    });
    const shapes = [new THREE.SphereGeometry(0.13, 14, 14), new THREE.BoxGeometry(0.22, 0.22, 0.22), new THREE.TetrahedronGeometry(0.18)];
    const colors = [1, 2, 3].map((i) => cssColor(el, `--series-${i}`));
    for (const { slot, p } of points) {
      const mesh = new THREE.Mesh(shapes[slot], new THREE.MeshStandardMaterial({ color: colors[slot] }));
      scene.add(mesh);
      meshes.push({ mesh, p });
    }
    const axisColor = cssColor(el, "--viz-grid-color");
    const axes = new THREE.AxesHelper(3.5);
    axes.setColors(axisColor, axisColor, axisColor);
    scene.add(axes, new THREE.GridHelper(8, 8, axisColor, axisColor));
    return cleanup;
  }, [points]);

  return (
    <div className="viz">
      <div ref={host} className="viz-3d" aria-label="Облако точек в трёх измерениях" />
      <div className="viz-legend">
        {Array.from({ length: count }, (_, i) => (
          <span key={i}>
            <svg width="14" height="14" viewBox="0 0 14 14" aria-hidden>
              <Marker x={7} y={7} slot={i} size={4.5} />
            </svg>
            Группа {i + 1}
          </span>
        ))}
      </div>
      <p className="viz-readout">
        {flat
          ? "Высоту убрали: осталось 2 признака. Видно, что часть групп наложилась, информация потерялась."
          : "У каждой точки 3 признака: x, y и высота. Поверните облако пальцем: группы видны лучше с одних сторон."}
      </p>
      <div className="viz-buttons">
        <button className="small" onClick={() => setFlat(!flat)}>
          {flat ? "Вернуть третье измерение" : "Сплющить в 2D"}
        </button>
      </div>
    </div>
  );
}
