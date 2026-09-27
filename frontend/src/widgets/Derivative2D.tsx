import { useState } from "react";

import { Axes, Plot, Slider, fmt, makeScale } from "./common";

const FUNCTIONS: Record<string, { label: string; f: (x: number) => number; d: (x: number) => number }> = {
  "x^2": { label: "x²", f: (x) => x * x, d: (x) => 2 * x },
  "x^3": { label: "x³ − 3x", f: (x) => x ** 3 - 3 * x, d: (x) => 3 * x * x - 3 },
  sin: { label: "3·sin x", f: (x) => 3 * Math.sin(x), d: (x) => 3 * Math.cos(x) },
};

export default function Derivative2D({ params }: { params: { fn?: string } }) {
  const [fn, setFn] = useState(params.fn && params.fn in FUNCTIONS ? params.fn : "x^2");
  const [x0, setX0] = useState(1);
  const { f, d, label } = FUNCTIONS[fn];
  const s = makeScale(-3, 3, -6, 9);
  const clampY = (v: number) => Math.max(-6, Math.min(9, v));

  const xs = Array.from({ length: 121 }, (_, i) => -3 + i * 0.05);
  const curve = xs.map((x, i) => `${i ? "L" : "M"}${s.x(x)},${s.y(clampY(f(x)))}`).join(" ");
  const slope = d(x0);
  const tangent = (x: number) => f(x0) + slope * (x - x0);

  return (
    <div className="viz">
      <Plot
        label={`График ${label} и касательная в точке x = ${fmt(x0)}`}
        onPointer={(px, _py, pressed) => pressed && setX0(Math.round(Math.max(-2.8, Math.min(2.8, s.invX(px))) * 20) / 20)}
      >
        <Axes s={s} xTicks={[-3, 0, 3]} yTicks={[-5, 0, 5]} />
        <path d={curve} className="viz-line" stroke="var(--series-1)" />
        <line x1={s.x(x0 - 1.2)} y1={s.y(clampY(tangent(x0 - 1.2)))} x2={s.x(x0 + 1.2)} y2={s.y(clampY(tangent(x0 + 1.2)))} className="viz-line" stroke="var(--series-2)" />
        <circle cx={s.x(x0)} cy={s.y(clampY(f(x0)))} r={7} fill="var(--series-2)" className="viz-ring" />
      </Plot>
      <p className="viz-readout">
        f({fmt(x0)}) = {fmt(f(x0))}. Наклон касательной (скорость изменения) f′ = <strong>{fmt(slope)}</strong>
        {Math.abs(slope) < 0.05 ? ": функция тут не растёт и не падает." : slope > 0 ? ": функция растёт." : ": функция убывает."}
      </p>
      <p className="muted small">Тяните точку по графику или двигайте ползунок.</p>
      <Slider label="Точка x" value={x0} min={-2.8} max={2.8} step={0.05} onChange={setX0} />
      <select value={fn} onChange={(e) => setFn(e.target.value)} aria-label="Функция">
        {Object.entries(FUNCTIONS).map(([key, v]) => (
          <option key={key} value={key}>
            f(x) = {v.label}
          </option>
        ))}
      </select>
    </div>
  );
}
