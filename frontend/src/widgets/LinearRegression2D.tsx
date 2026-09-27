import { useMemo, useState } from "react";

import { Axes, Marker, Plot, Slider, fmt, gauss, makeScale, rng } from "./common";

export default function LinearRegression2D({ params }: { params: { points?: number; noise?: number } }) {
  const points = useMemo(() => {
    const rand = rng(7);
    return Array.from({ length: params.points ?? 20 }, () => {
      const x = rand() * 10;
      return { x, y: 0.8 * x + 1 + gauss(rand, 0, params.noise ?? 1.5) };
    });
  }, [params.points, params.noise]);
  const [slope, setSlope] = useState(0.2);
  const [intercept, setIntercept] = useState(4);
  const [hover, setHover] = useState<number | null>(null);
  const s = makeScale(0, 10, -2, 12);

  const mse = points.reduce((sum, p) => sum + (p.y - (slope * p.x + intercept)) ** 2, 0) / points.length;

  function bestFit() {
    const n = points.length;
    const mx = points.reduce((a, p) => a + p.x, 0) / n;
    const my = points.reduce((a, p) => a + p.y, 0) / n;
    const b = points.reduce((a, p) => a + (p.x - mx) * (p.y - my), 0) / points.reduce((a, p) => a + (p.x - mx) ** 2, 0);
    setSlope(Math.round(b * 100) / 100);
    setIntercept(Math.round((my - b * mx) * 100) / 100);
  }

  return (
    <div className="viz">
      <Plot
        label="Точки данных и линия, которую двигает студент"
        onPointer={(px, py) => {
          let best = -1;
          let dist = 14;
          points.forEach((p, i) => {
            const d = Math.hypot(s.x(p.x) - px, s.y(p.y) - py);
            if (d < dist) [best, dist] = [i, d];
          });
          setHover(best >= 0 ? best : null);
        }}
        onLeave={() => setHover(null)}
      >
        <Axes s={s} xTicks={[0, 5, 10]} yTicks={[0, 5, 10]} />
        {points.map((p, i) => (
          <line key={i} x1={s.x(p.x)} x2={s.x(p.x)} y1={s.y(p.y)} y2={s.y(slope * p.x + intercept)} className="viz-residual" />
        ))}
        <line x1={s.x(0)} y1={s.y(intercept)} x2={s.x(10)} y2={s.y(slope * 10 + intercept)} className="viz-line" stroke="var(--series-2)" />
        {points.map((p, i) => (
          <Marker key={i} x={s.x(p.x)} y={s.y(p.y)} slot={0} size={hover === i ? 6 : 4} />
        ))}
      </Plot>
      <p className="viz-readout">
        {hover !== null
          ? `Точка (${fmt(points[hover].x)}; ${fmt(points[hover].y)}), ошибка ${fmt(points[hover].y - (slope * points[hover].x + intercept))}`
          : `Средняя квадратичная ошибка (MSE): ${fmt(mse)}. Сделайте её как можно меньше.`}
      </p>
      <Slider label="Наклон" value={slope} min={-1} max={3} step={0.05} onChange={setSlope} />
      <Slider label="Сдвиг" value={intercept} min={-3} max={8} step={0.1} onChange={setIntercept} />
      <div className="viz-buttons">
        <button className="small" onClick={bestFit}>
          Показать лучшую линию
        </button>
      </div>
    </div>
  );
}
