import { useState } from "react";

import { Axes, Plot, Slider, fmt, makeScale } from "./common";

const pdf = (x: number, m: number, sd: number) => Math.exp(-((x - m) ** 2) / (2 * sd * sd)) / (sd * Math.sqrt(2 * Math.PI));

export default function NormalDistribution2D({ params }: { params: { mean?: number; sd?: number } }) {
  const [mean, setMean] = useState(params.mean ?? 0);
  const [sd, setSd] = useState(params.sd ?? 1);
  const [hover, setHover] = useState<number | null>(null);
  const s = makeScale(-6, 6, 0, 0.8);

  const xs = Array.from({ length: 241 }, (_, i) => -6 + i * 0.05);
  const curve = xs.map((x, i) => `${i ? "L" : "M"}${s.x(x)},${s.y(Math.min(pdf(x, mean, sd), 0.8))}`).join(" ");
  const band = xs.filter((x) => Math.abs(x - mean) <= sd);
  const area =
    band.length > 1
      ? `M${s.x(band[0])},${s.y(0)} ` +
        band.map((x) => `L${s.x(x)},${s.y(Math.min(pdf(x, mean, sd), 0.8))}`).join(" ") +
        ` L${s.x(band[band.length - 1])},${s.y(0)}Z`
      : "";

  return (
    <div className="viz">
      <Plot
        label={`Нормальное распределение со средним ${mean} и отклонением ${sd}`}
        onPointer={(px) => setHover(Math.max(-6, Math.min(6, s.invX(px))))}
        onLeave={() => setHover(null)}
      >
        <Axes s={s} xTicks={[-6, -3, 0, 3, 6]} yTicks={[0, 0.4, 0.8]} />
        <path d={area} className="viz-area" />
        <path d={curve} className="viz-line" stroke="var(--series-1)" />
        <line x1={s.x(mean)} x2={s.x(mean)} y1={s.y(0)} y2={s.y(0.8)} className="viz-guide" />
        {hover !== null && (
          <g>
            <line x1={s.x(hover)} x2={s.x(hover)} y1={s.y(0)} y2={s.y(0.8)} className="viz-crosshair" />
            <circle cx={s.x(hover)} cy={s.y(Math.min(pdf(hover, mean, sd), 0.8))} r={4} fill="var(--series-1)" className="viz-ring" />
          </g>
        )}
      </Plot>
      <p className="viz-readout">
        {hover !== null
          ? `x = ${fmt(hover)}, плотность = ${fmt(pdf(hover, mean, sd), 3)}`
          : "Закрашено μ ± σ: здесь около 68% всех значений."}
      </p>
      <Slider label="Среднее μ" value={mean} min={-3} max={3} step={0.1} onChange={setMean} />
      <Slider label="Отклонение σ" value={sd} min={0.3} max={3} step={0.1} onChange={setSd} />
    </div>
  );
}
